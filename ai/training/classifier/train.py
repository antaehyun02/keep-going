"""AI Hub 08-14 분류 모델 학습.

사용법:
    python -m ai.training.classifier.train
    python -m ai.training.classifier.train --backbone efficientnet_b3
    python -m ai.training.classifier.train --resume ai/checkpoints/aihub/epoch_10.pth
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .config import ClassifyConfig
from .model import build_classifier, get_model_info
from ..utils import get_device, resolve_num_workers, topk_accuracy
from ...dataset.dataset import AihubFacialDataset, get_transforms, worker_init_fn


def train_one_epoch(model, loader, criterion, optimizer, device):
    """1 에폭 학습."""
    model.train()
    total_loss = 0.0
    total_top1 = 0.0
    num_batches = 0

    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        top1, _ = topk_accuracy(outputs, labels, topk=(1, 3))
        total_loss += loss.item()
        total_top1 += top1.item()
        num_batches += 1

    return total_loss / num_batches, total_top1 / num_batches


@torch.no_grad()
def validate(model, loader, criterion, device):
    """검증."""
    model.eval()
    total_loss = 0.0
    total_top1 = 0.0
    total_top3 = 0.0
    num_batches = 0

    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        outputs = model(images)
        loss = criterion(outputs, labels)

        top1, top3 = topk_accuracy(outputs, labels, topk=(1, 3))
        total_loss += loss.item()
        total_top1 += top1.item()
        total_top3 += top3.item()
        num_batches += 1

    return (
        total_loss / num_batches,
        total_top1 / num_batches,
        total_top3 / num_batches,
    )


def plot_training_curves(history: list, save_path: str):
    """학습 곡선 시각화."""
    epochs = [h["epoch"] for h in history]
    train_loss = [h["train_loss"] for h in history]
    val_loss = [h["val_loss"] for h in history]
    val_top1 = [h["val_top1"] for h in history]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax1.plot(epochs, train_loss, "b-", label="Train Loss")
    ax1.plot(epochs, val_loss, "r-", label="Val Loss")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Loss")
    ax1.set_title("Loss Curve")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.plot(epochs, val_top1, "g-", label="Val Top-1 Acc")
    ax2.axhline(y=0.80, color="orange", linestyle="--", label="Target (80%)")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Accuracy")
    ax2.set_title("Top-1 Accuracy")
    ax2.legend()
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="AI Hub 분류 모델 학습")
    parser.add_argument("--backbone", default="densenet121", choices=["densenet121", "efficientnet_b3"])
    parser.add_argument("--experiment_name", default=None)
    parser.add_argument("--num_epochs", type=int, default=None)
    parser.add_argument("--batch_size", type=int, default=None)
    parser.add_argument("--learning_rate", type=float, default=None)
    parser.add_argument("--resume", default=None, help="체크포인트 경로")
    args = parser.parse_args()

    config = ClassifyConfig()
    config.backbone = args.backbone
    if args.experiment_name:
        config.experiment_name = args.experiment_name
    if args.num_epochs:
        config.num_epochs = args.num_epochs
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.learning_rate:
        config.learning_rate = args.learning_rate

    device = get_device()
    print("=" * 60)
    print(f"AI Hub 08-14 분류 모델 학습")
    print(f"  backbone : {config.backbone}")
    print(f"  device   : {device}")
    print(f"  epochs   : {config.num_epochs}")
    print(f"  batch    : {config.batch_size}")
    print(f"  lr       : {config.learning_rate}")
    print("=" * 60)

    # 데이터 로드
    data_dir = Path(config.data_dir)
    train_transform = get_transforms("train", config)
    val_transform = get_transforms("val", config)

    train_dataset = AihubFacialDataset(str(data_dir / "train.csv"), transform=train_transform)
    val_dataset = AihubFacialDataset(str(data_dir / "val.csv"), transform=val_transform)

    num_workers = resolve_num_workers(device, config.num_workers)

    train_loader = DataLoader(
        train_dataset, batch_size=config.batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=True,
        worker_init_fn=worker_init_fn,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=config.batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
        worker_init_fn=worker_init_fn,
    )

    print(f"\n  Train: {len(train_dataset)}건")
    print(f"  Val  : {len(val_dataset)}건")

    # 모델 생성
    model = build_classifier(config)
    get_model_info(model)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=config.num_epochs - config.warmup_epochs,
    )

    # 체크포인트에서 이어서 학습
    start_epoch = 0
    best_val_top1 = 0.0
    history = []

    if args.resume:
        checkpoint = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        start_epoch = checkpoint.get("epoch", 0)
        best_val_top1 = checkpoint.get("best_val_top1", 0.0)
        history = checkpoint.get("history", [])
        print(f"\n  이어서 학습: epoch {start_epoch}, best_top1={best_val_top1:.4f}")

    # 저장 디렉토리
    ckpt_dir = Path(config.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # 학습 루프
    no_improve = 0
    print("\n학습 시작...\n")

    for epoch in range(start_epoch, config.num_epochs):
        epoch_start = time.time()

        train_loss, train_top1 = train_one_epoch(model, train_loader, criterion, optimizer, device)

        if epoch >= config.warmup_epochs:
            scheduler.step()

        val_loss, val_top1, val_top3 = validate(model, val_loader, criterion, device)

        elapsed = time.time() - epoch_start
        target_achieved = "✅" if val_top1 >= config.target_top1_acc else "❌"

        print(f"[Epoch {epoch+1:02d}/{config.num_epochs}] "
              f"Train Loss: {train_loss:.3f} | Train Top-1: {train_top1*100:.1f}%")
        print(f"{'':>20s}"
              f"Val   Loss: {val_loss:.3f} | Val   Top-1: {val_top1*100:.1f}% | "
              f"Val Top-3: {val_top3*100:.1f}%")
        print(f"{'':>20s}"
              f"목표(80%) 달성: {target_achieved} | "
              f"시간: {elapsed:.1f}s | LR: {optimizer.param_groups[0]['lr']:.6f}")

        epoch_log = {
            "epoch": epoch + 1,
            "train_loss": round(train_loss, 4),
            "train_top1": round(train_top1, 4),
            "val_loss": round(val_loss, 4),
            "val_top1": round(val_top1, 4),
            "val_top3": round(val_top3, 4),
            "lr": optimizer.param_groups[0]["lr"],
        }
        history.append(epoch_log)

        # Best 모델 저장
        if val_top1 > best_val_top1:
            best_val_top1 = val_top1
            no_improve = 0
            torch.save({
                "epoch": epoch + 1,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "best_val_top1": best_val_top1,
                "config": vars(config),
                "history": history,
            }, ckpt_dir / "best.pth")
            print(f"{'':>20s}🏆 Best 모델 저장 (Top-1: {best_val_top1*100:.2f}%)")
        else:
            no_improve += 1

        # 주기적 체크포인트
        if (epoch + 1) % config.save_every_n_epochs == 0:
            torch.save({
                "epoch": epoch + 1,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "best_val_top1": best_val_top1,
                "config": vars(config),
                "history": history,
            }, ckpt_dir / f"epoch_{epoch+1}.pth")

        # Early stopping
        if no_improve >= config.early_stopping_patience:
            print(f"\n⏹ Early stopping: {config.early_stopping_patience} 에폭 동안 개선 없음")
            break

        print()

    # 학습 로그 저장
    training_log = {
        "config": vars(config),
        "best_epoch": max(history, key=lambda x: x["val_top1"])["epoch"] if history else 0,
        "best_val_top1": round(best_val_top1, 4),
        "target_achieved": best_val_top1 >= config.target_top1_acc,
        "guideline_target": config.target_top1_acc,
        "device": str(device),
        "started_at": datetime.now().isoformat(),
        "history": history,
    }

    log_path = ckpt_dir / "training_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(training_log, f, ensure_ascii=False, indent=2)

    # 학습 곡선 저장
    if history:
        plot_training_curves(history, str(ckpt_dir / "loss_curve.png"))

    print("\n" + "=" * 60)
    print(f"학습 완료!")
    print(f"  Best Top-1 Acc : {best_val_top1*100:.2f}%")
    print(f"  가이드라인 목표 : {'✅ 달성' if best_val_top1 >= config.target_top1_acc else '❌ 미달'}")
    print(f"  체크포인트     : {ckpt_dir}/best.pth")
    print(f"  학습 로그      : {log_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
