"""아토피피부염 병변 세그멘테이션 모델 학습 (DeeplabV3+).

사용법:
    python -m scin.model.aihub_classifier.train_seg
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

from .config import SegmentConfig
from .dataset import AihubSegDataset, get_transforms
from .model import build_segmentor, get_model_info
from ..utils import get_device, resolve_num_workers


def compute_iou(pred, target, num_classes=2):
    """IoU 계산."""
    ious = []
    for cls in range(num_classes):
        pred_cls = (pred == cls)
        target_cls = (target == cls)
        intersection = (pred_cls & target_cls).float().sum()
        union = (pred_cls | target_cls).float().sum()
        if union == 0:
            ious.append(float("nan"))
        else:
            ious.append((intersection / union).item())
    return ious


def compute_dice(pred, target):
    """Dice coefficient (병변 클래스=1)."""
    pred_1 = (pred == 1).float()
    target_1 = (target == 1).float()
    intersection = (pred_1 * target_1).sum()
    return (2 * intersection / (pred_1.sum() + target_1.sum() + 1e-8)).item()


def train_one_epoch(model, loader, criterion, aux_criterion, optimizer, device):
    """1 에폭 학습."""
    model.train()
    total_loss = 0.0
    num_batches = 0

    for images, masks in loader:
        images, masks = images.to(device), masks.to(device)

        optimizer.zero_grad()
        outputs = model(images)

        main_loss = criterion(outputs["out"], masks)
        loss = main_loss

        if "aux" in outputs:
            aux_loss = aux_criterion(outputs["aux"], masks)
            loss = main_loss + 0.4 * aux_loss

        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        num_batches += 1

    return total_loss / num_batches


@torch.no_grad()
def validate_seg(model, loader, criterion, device):
    """세그멘테이션 검증."""
    model.eval()
    total_loss = 0.0
    total_iou_lesion = 0.0
    total_dice = 0.0
    total_pixel_acc = 0.0
    num_batches = 0

    for images, masks in loader:
        images, masks = images.to(device), masks.to(device)
        outputs = model(images)["out"]

        loss = criterion(outputs, masks)
        preds = outputs.argmax(dim=1)

        ious = compute_iou(preds, masks, num_classes=2)
        dice = compute_dice(preds, masks)
        pixel_acc = (preds == masks).float().mean().item()

        total_loss += loss.item()
        total_iou_lesion += ious[1] if not torch.isnan(torch.tensor(ious[1])) else 0
        total_dice += dice
        total_pixel_acc += pixel_acc
        num_batches += 1

    return (
        total_loss / num_batches,
        total_iou_lesion / num_batches,
        total_dice / num_batches,
        total_pixel_acc / num_batches,
    )


def main():
    parser = argparse.ArgumentParser(description="아토피 세그멘테이션 학습")
    parser.add_argument("--num_epochs", type=int, default=None)
    parser.add_argument("--batch_size", type=int, default=None)
    parser.add_argument("--mask_dir", default="scin/data/processed_aihub/masks")
    args = parser.parse_args()

    config = SegmentConfig()
    if args.num_epochs:
        config.num_epochs = args.num_epochs
    if args.batch_size:
        config.batch_size = args.batch_size

    device = get_device()
    print("=" * 60)
    print(f"아토피피부염 세그멘테이션 학습 (DeeplabV3+)")
    print(f"  device : {device}")
    print(f"  epochs : {config.num_epochs}")
    print("=" * 60)

    data_dir = Path(config.data_dir)
    train_transform = get_transforms("train", config, task="segment")
    val_transform = get_transforms("val", config, task="segment")

    train_dataset = AihubSegDataset(str(data_dir / "train.csv"), args.mask_dir, transform=train_transform)
    val_dataset = AihubSegDataset(str(data_dir / "val.csv"), args.mask_dir, transform=val_transform)

    num_workers = resolve_num_workers(device, config.num_workers)

    train_loader = DataLoader(
        train_dataset, batch_size=config.batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=config.batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )

    print(f"\n  Train: {len(train_dataset)}건 (아토피)")
    print(f"  Val  : {len(val_dataset)}건")

    model = build_segmentor(config)
    get_model_info(model)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    aux_criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay,
    )

    ckpt_dir = Path(config.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    best_iou = 0.0
    history = []

    print("\n학습 시작...\n")

    for epoch in range(config.num_epochs):
        epoch_start = time.time()

        train_loss = train_one_epoch(model, train_loader, criterion, aux_criterion, optimizer, device)
        val_loss, val_iou, val_dice, val_pixel_acc = validate_seg(model, val_loader, criterion, device)

        elapsed = time.time() - epoch_start
        target_achieved = "✅" if val_iou >= config.target_iou else "❌"

        print(f"[Epoch {epoch+1:02d}/{config.num_epochs}] "
              f"Train Loss: {train_loss:.3f} | "
              f"Val IoU: {val_iou:.3f} | Val Dice: {val_dice:.3f} | "
              f"Pixel Acc: {val_pixel_acc:.3f}")
        print(f"{'':>20s}목표(IoU ≥ {config.target_iou}): {target_achieved} | 시간: {elapsed:.1f}s")

        history.append({
            "epoch": epoch + 1,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "val_iou": round(val_iou, 4),
            "val_dice": round(val_dice, 4),
            "val_pixel_acc": round(val_pixel_acc, 4),
        })

        if val_iou > best_iou:
            best_iou = val_iou
            torch.save({
                "epoch": epoch + 1,
                "model_state_dict": model.state_dict(),
                "best_iou": best_iou,
                "config": vars(config),
            }, ckpt_dir / "best_seg.pth")
            print(f"{'':>20s}🏆 Best 모델 저장 (IoU: {best_iou:.4f})")

        print()

    # 로그 저장
    log = {
        "config": vars(config),
        "best_iou": round(best_iou, 4),
        "target_achieved": best_iou >= config.target_iou,
        "history": history,
    }

    with open(ckpt_dir / "training_seg_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    # IoU 곡선 저장
    if history:
        fig, ax = plt.subplots(figsize=(8, 5))
        epochs = [h["epoch"] for h in history]
        ax.plot(epochs, [h["val_iou"] for h in history], "g-", label="Val IoU")
        ax.plot(epochs, [h["val_dice"] for h in history], "b-", label="Val Dice")
        ax.axhline(y=config.target_iou, color="orange", linestyle="--", label=f"Target ({config.target_iou})")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Score")
        ax.set_title("Segmentation Metrics")
        ax.legend()
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(ckpt_dir / "iou_curve.png", dpi=150)
        plt.close()

    print("=" * 60)
    print(f"학습 완료! Best IoU: {best_iou:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
