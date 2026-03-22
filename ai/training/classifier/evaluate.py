"""분류 모델 평가.

사용법:
    python -m scin.model.aihub_classifier.evaluate \
        --checkpoint scin/checkpoints/aihub/best.pth \
        --output_dir scin/model/aihub_classifier/eval_results
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
    f1_score,
)

from .config import ClassifyConfig
from .dataset import AihubFacialDataset, get_transforms, CLASS_MAP, IDX_TO_CLASS
from .model import build_classifier
from ..utils import get_device, resolve_num_workers


@torch.no_grad()
def collect_predictions(model, loader, device):
    """테스트셋 전체 예측 수집."""
    model.eval()
    all_probs = []
    all_labels = []

    for images, labels in loader:
        images = images.to(device)
        outputs = model(images)
        probs = torch.softmax(outputs, dim=1).cpu()
        all_probs.append(probs)
        all_labels.append(labels)

    return torch.cat(all_probs), torch.cat(all_labels)


def plot_confusion_matrix(cm, class_names, save_path):
    """Confusion Matrix 시각화."""
    import platform
    if platform.system() == "Darwin":
        plt.rcParams["font.family"] = "AppleGothic"
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)

    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           xticklabels=class_names,
           yticklabels=class_names,
           ylabel="실제 (True)",
           xlabel="예측 (Predicted)",
           title="Confusion Matrix")

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], "d"),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def plot_roc_curves(all_labels, all_probs, class_names, save_path):
    """ROC 곡선 시각화."""
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]

    for i, (name, color) in enumerate(zip(class_names, colors)):
        binary_labels = (all_labels == i).numpy().astype(int)
        if binary_labels.sum() == 0:
            continue
        fpr, tpr, _ = roc_curve(binary_labels, all_probs[:, i].numpy())
        auc = roc_auc_score(binary_labels, all_probs[:, i].numpy())
        ax.plot(fpr, tpr, color=color, lw=2, label=f"{name} (AUC={auc:.3f})")

    ax.plot([0, 1], [0, 1], "k--", lw=1)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="분류 모델 평가")
    parser.add_argument("--checkpoint", required=True, help="체크포인트 경로")
    parser.add_argument("--output_dir", default="scin/model/aihub_classifier/eval_results")
    parser.add_argument("--data_dir", default=None)
    args = parser.parse_args()

    device = get_device()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 체크포인트 로드
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    ckpt_config = checkpoint.get("config", {})

    config = ClassifyConfig()
    config.backbone = ckpt_config.get("backbone", "densenet121")
    if args.data_dir:
        config.data_dir = args.data_dir

    model = build_classifier(config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)

    # 테스트 데이터
    data_dir = Path(config.data_dir)
    test_transform = get_transforms("test", config)
    test_dataset = AihubFacialDataset(str(data_dir / "test.csv"), transform=test_transform)

    num_workers = resolve_num_workers(device, config.num_workers)
    test_loader = DataLoader(
        test_dataset, batch_size=config.batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )

    print(f"평가 데이터: {len(test_dataset)}건")

    # 예측 수집
    all_probs, all_labels = collect_predictions(model, test_loader, device)
    all_preds = all_probs.argmax(dim=1)

    class_names = config.class_names
    labels_np = all_labels.numpy()
    preds_np = all_preds.numpy()

    # Top-1, Top-3 Accuracy
    top1_acc = (all_preds == all_labels).float().mean().item()
    _, top3_preds = all_probs.topk(3, dim=1)
    top3_correct = sum(
        all_labels[i] in top3_preds[i] for i in range(len(all_labels))
    )
    top3_acc = top3_correct / len(all_labels)

    # Classification Report
    report = classification_report(labels_np, preds_np, target_names=class_names, output_dict=True)
    macro_f1 = f1_score(labels_np, preds_np, average="macro")
    weighted_f1 = f1_score(labels_np, preds_np, average="weighted")

    # AUC
    try:
        macro_auc = roc_auc_score(labels_np, all_probs.numpy(), multi_class="ovr", average="macro")
    except ValueError:
        macro_auc = 0.0

    per_class_auc = {}
    for i, name in enumerate(class_names):
        binary = (labels_np == i).astype(int)
        if binary.sum() > 0:
            per_class_auc[name] = roc_auc_score(binary, all_probs[:, i].numpy())
        else:
            per_class_auc[name] = 0.0

    # 출력
    target_mark = "✅" if top1_acc >= config.target_top1_acc else "❌"

    print("\n" + "=" * 60)
    print(f" SkinAI 분류 모델 평가 결과 (AI Hub 08-14)")
    print(f" 모델: {config.backbone}")
    print("-" * 60)
    print(f" Top-1 Accuracy : {top1_acc*100:.2f}%  {target_mark} 가이드라인 목표(80%)")
    print(f" Top-3 Accuracy : {top3_acc*100:.2f}%")
    print(f" Macro F1-Score : {macro_f1:.4f}")
    print(f" Macro AUC      : {macro_auc:.4f}")
    print("-" * 60)
    print(f" {'클래스':12s} {'Prec':>8s} {'Recall':>8s} {'F1':>8s} {'AUC':>8s}")
    print("-" * 60)
    for name in class_names:
        r = report.get(name, {})
        auc_val = per_class_auc.get(name, 0)
        print(f" {name:12s} {r.get('precision',0):8.4f} {r.get('recall',0):8.4f} "
              f"{r.get('f1-score',0):8.4f} {auc_val:8.4f}")
    print("=" * 60)

    # Confusion Matrix
    cm = confusion_matrix(labels_np, preds_np)
    plot_confusion_matrix(cm, class_names, str(output_dir / "confusion_matrix.png"))
    print(f"→ confusion_matrix.png 저장")

    # ROC Curves
    plot_roc_curves(all_labels, all_probs, class_names, str(output_dir / "roc_curves.png"))
    print(f"→ roc_curves.png 저장")

    # JSON 결과 저장
    results = {
        "backbone": config.backbone,
        "test_samples": len(test_dataset),
        "top1_accuracy": round(top1_acc, 4),
        "top3_accuracy": round(top3_acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "macro_auc": round(macro_auc, 4),
        "target_achieved": top1_acc >= config.target_top1_acc,
        "per_class": {
            name: {
                "precision": round(report[name]["precision"], 4),
                "recall": round(report[name]["recall"], 4),
                "f1": round(report[name]["f1-score"], 4),
                "auc": round(per_class_auc.get(name, 0), 4),
                "support": int(report[name]["support"]),
            }
            for name in class_names if name in report
        },
        "confusion_matrix": cm.tolist(),
    }

    with open(output_dir / "evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"→ evaluation_results.json 저장")


if __name__ == "__main__":
    main()
