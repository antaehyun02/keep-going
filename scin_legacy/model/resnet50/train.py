"""
SCIN 피부 질환 분류 모델 학습 스크립트 - ResNet50

ResNet50 전이 학습 - 다중 라벨 분류
"""

import os
import sys
import json
import argparse
from pathlib import Path
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

# 상위 디렉토리에서 dataset, loss import
sys.path.append(str(Path(__file__).parent.parent))
from dataset import get_data_loaders
from model import ResNet50Classifier
from loss import get_loss_function


class Trainer:
    """모델 학습 관리자"""

    def __init__(self, model, train_loader, val_loader, criterion, optimizer, scheduler,
                 device, checkpoint_dir, log_dir, patience=10, start_epoch=0):
        """
        Args:
            model: 학습할 모델
            train_loader: 학습 DataLoader
            val_loader: 검증 DataLoader
            criterion: 손실 함수
            optimizer: 옵티마이저
            scheduler: Learning rate scheduler
            device: 디바이스 (cuda/cpu)
            checkpoint_dir: 체크포인트 저장 디렉토리
            log_dir: TensorBoard 로그 디렉토리
            patience: Early stopping patience
            start_epoch: 시작 에포크 (체크포인트 재개 시 사용)
        """
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.criterion = criterion
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.device = device

        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.writer = SummaryWriter(log_dir)

        self.patience = patience
        self.best_val_loss = float('inf')
        self.epochs_without_improvement = 0
        self.start_epoch = start_epoch

        self.train_losses = []
        self.val_losses = []

    def train_epoch(self, epoch):
        """
        1 에포크 학습

        Args:
            epoch: 현재 에포크 번호

        Returns:
            float: 평균 학습 손실
        """
        self.model.train()
        total_loss = 0.0
        num_batches = len(self.train_loader)

        pbar = tqdm(self.train_loader, desc=f"Epoch {epoch} [Train]")

        for batch_idx, batch in enumerate(pbar):
            images = batch['image'].to(self.device)
            labels = batch['label'].to(self.device)

            # Forward
            self.optimizer.zero_grad()
            outputs = self.model(images)
            loss = self.criterion(outputs, labels)

            # Backward
            loss.backward()
            self.optimizer.step()

            # 통계
            total_loss += loss.item()
            avg_loss = total_loss / (batch_idx + 1)

            pbar.set_postfix({'loss': f'{avg_loss:.4f}'})

            # TensorBoard 로그
            global_step = epoch * num_batches + batch_idx
            self.writer.add_scalar('Loss/train_batch', loss.item(), global_step)

        avg_loss = total_loss / num_batches
        self.train_losses.append(avg_loss)
        self.writer.add_scalar('Loss/train_epoch', avg_loss, epoch)

        return avg_loss

    def validate(self, epoch):
        """
        검증

        Args:
            epoch: 현재 에포크 번호

        Returns:
            float: 평균 검증 손실
        """
        self.model.eval()
        total_loss = 0.0
        num_batches = len(self.val_loader)

        all_outputs = []
        all_labels = []

        with torch.no_grad():
            pbar = tqdm(self.val_loader, desc=f"Epoch {epoch} [Val]")

            for batch in pbar:
                images = batch['image'].to(self.device)
                labels = batch['label'].to(self.device)

                outputs = self.model(images)
                loss = self.criterion(outputs, labels)

                total_loss += loss.item()
                avg_loss = total_loss / (len(all_outputs) + 1)

                pbar.set_postfix({'loss': f'{avg_loss:.4f}'})

                all_outputs.append(torch.sigmoid(outputs).cpu())
                all_labels.append(labels.cpu())

        avg_loss = total_loss / num_batches
        self.val_losses.append(avg_loss)
        self.writer.add_scalar('Loss/val_epoch', avg_loss, epoch)

        # 추가 메트릭 계산 (예: Top-K Accuracy)
        all_outputs = torch.cat(all_outputs, dim=0)
        all_labels = torch.cat(all_labels, dim=0)

        top1_acc = self.calculate_topk_accuracy(all_outputs, all_labels, k=1)
        top3_acc = self.calculate_topk_accuracy(all_outputs, all_labels, k=3)
        top5_acc = self.calculate_topk_accuracy(all_outputs, all_labels, k=5)

        self.writer.add_scalar('Accuracy/top1', top1_acc, epoch)
        self.writer.add_scalar('Accuracy/top3', top3_acc, epoch)
        self.writer.add_scalar('Accuracy/top5', top5_acc, epoch)

        print(f"\n[Validation] Loss: {avg_loss:.4f}, Top-1: {top1_acc:.2%}, Top-3: {top3_acc:.2%}, Top-5: {top5_acc:.2%}")

        return avg_loss

    def calculate_topk_accuracy(self, outputs, labels, k=3):
        """
        Top-K Accuracy 계산 (다중 라벨)

        Args:
            outputs: (N, C) 예측 확률
            labels: (N, C) 정답 라벨 (이진)
            k: Top-K

        Returns:
            float: Top-K Accuracy
        """
        # 각 샘플의 Top-K 예측
        _, topk_indices = outputs.topk(k, dim=1)

        # 정답 라벨 인덱스
        label_indices = [torch.where(label == 1)[0] for label in labels]

        correct = 0
        total = len(labels)

        for i in range(total):
            # Top-K 중에 정답이 하나라도 있으면 정답
            if len(label_indices[i]) > 0:
                if any(idx in topk_indices[i] for idx in label_indices[i]):
                    correct += 1

        return correct / total if total > 0 else 0.0

    def save_checkpoint(self, epoch, is_best=False):
        """
        체크포인트 저장

        Args:
            epoch: 현재 에포크
            is_best: 최고 성능 모델 여부
        """
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict() if self.scheduler else None,
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'best_val_loss': self.best_val_loss
        }

        # 최신 체크포인트
        latest_path = self.checkpoint_dir / 'checkpoint_latest.pth'
        torch.save(checkpoint, latest_path)

        # 최고 성능 체크포인트
        if is_best:
            best_path = self.checkpoint_dir / 'checkpoint_best.pth'
            torch.save(checkpoint, best_path)
            print(f"[INFO] 최고 성능 모델 저장: {best_path}")

        # 주기적 체크포인트 (10 에포크마다)
        if (epoch + 1) % 10 == 0:
            epoch_path = self.checkpoint_dir / f'checkpoint_epoch_{epoch+1}.pth'
            torch.save(checkpoint, epoch_path)

    def train(self, num_epochs):
        """
        전체 학습 루프

        Args:
            num_epochs: 총 에포크 수
        """
        print(f"\n{'='*60}")
        print(f"학습 시작 - ResNet50")
        print(f"{'='*60}")
        print(f"디바이스: {self.device}")
        print(f"시작 에포크: {self.start_epoch}")
        print(f"종료 에포크: {num_epochs - 1}")
        print(f"체크포인트: {self.checkpoint_dir}")
        print(f"TensorBoard: {self.writer.log_dir}")
        print(f"{'='*60}\n")

        start_time = time.time()

        for epoch in range(self.start_epoch, num_epochs):
            epoch_start = time.time()

            # 학습
            train_loss = self.train_epoch(epoch)

            # 검증
            val_loss = self.validate(epoch)

            # Learning rate scheduler 업데이트
            if self.scheduler:
                self.scheduler.step(val_loss)
                current_lr = self.optimizer.param_groups[0]['lr']
                self.writer.add_scalar('Learning_Rate', current_lr, epoch)

            # 체크포인트 저장
            is_best = val_loss < self.best_val_loss
            if is_best:
                self.best_val_loss = val_loss
                self.epochs_without_improvement = 0
            else:
                self.epochs_without_improvement += 1

            self.save_checkpoint(epoch, is_best=is_best)

            epoch_time = time.time() - epoch_start
            print(f"Epoch {epoch} 완료 (소요 시간: {epoch_time:.2f}초)\n")

            # Early stopping
            if self.epochs_without_improvement >= self.patience:
                print(f"\n[INFO] Early stopping: {self.patience} 에포크 동안 개선 없음")
                break

        total_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"학습 완료!")
        print(f"{'='*60}")
        print(f"총 소요 시간: {total_time/60:.2f}분")
        print(f"최고 검증 손실: {self.best_val_loss:.4f}")
        print(f"체크포인트: {self.checkpoint_dir}")
        print(f"{'='*60}\n")

        self.writer.close()


def main():
    parser = argparse.ArgumentParser(description='SCIN 모델 학습 - ResNet50')
    parser.add_argument('--data_dir', type=str, required=True, help='전처리 데이터 디렉토리')
    parser.add_argument('--image_root', type=str, required=True, help='이미지 루트 디렉토리')
    parser.add_argument('--checkpoint_dir', type=str, default='./checkpoints', help='체크포인트 저장 디렉토리')
    parser.add_argument('--log_dir', type=str, default='./logs', help='TensorBoard 로그 디렉토리')

    # 모델 하이퍼파라미터
    parser.add_argument('--pretrained', action='store_true', default=True, help='ImageNet pretrained 사용')
    parser.add_argument('--dropout', type=float, default=0.5, help='Dropout 비율')

    # 학습 하이퍼파라미터
    parser.add_argument('--batch_size', type=int, default=32, help='배치 크기')
    parser.add_argument('--num_epochs', type=int, default=50, help='총 에포크 수')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-4, help='Weight decay')
    parser.add_argument('--patience', type=int, default=10, help='Early stopping patience')

    # 손실 함수 설정
    parser.add_argument('--loss_type', type=str, default='focal', choices=['focal', 'asymmetric', 'bce'],
                        help='손실 함수 타입 (focal: Focal Loss, asymmetric: Asymmetric Loss, bce: BCE Loss)')
    parser.add_argument('--focal_alpha', type=float, default=0.25, help='Focal Loss alpha 파라미터 (0~1)')
    parser.add_argument('--focal_gamma', type=float, default=2.0, help='Focal Loss gamma 파라미터 (focusing parameter)')

    # DataLoader 설정
    parser.add_argument('--num_workers', type=int, default=0, help='DataLoader 워커 수 (Apple Silicon은 0 권장)')
    parser.add_argument('--augment', action='store_true', default=True, help='데이터 증강 사용')

    # 체크포인트 재개
    parser.add_argument('--resume', type=str, default=None, help='체크포인트 경로 (학습 재개 시)')

    args = parser.parse_args()

    # 디바이스 설정 (Apple Silicon MPS 백엔드 우선 사용)
    if torch.backends.mps.is_available():
        device = torch.device('mps')
        print(f"[INFO] 디바이스: MPS (Metal Performance Shaders) - Apple Silicon 최적화")
    elif torch.cuda.is_available():
        device = torch.device('cuda')
        print(f"[INFO] 디바이스: CUDA")
    else:
        device = torch.device('cpu')
        print(f"[WARN] 디바이스: CPU - 학습 속도가 매우 느릴 수 있습니다")

    print(f"[INFO] 사용 중인 디바이스: {device}")

    # 메타데이터 로드
    with open(Path(args.data_dir) / 'metadata.json', 'r') as f:
        metadata = json.load(f)
    num_classes = metadata['num_classes']

    print(f"[INFO] 클래스 수: {num_classes}")

    # DataLoader 생성
    data_loaders = get_data_loaders(
        data_dir=args.data_dir,
        image_root=args.image_root,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        augment=args.augment
    )

    # 모델 생성 (ResNet50)
    print(f"\n[INFO] 모델 생성: ResNet50 (pretrained={args.pretrained})")
    model = ResNet50Classifier(
        num_classes=num_classes,
        pretrained=args.pretrained,
        dropout=args.dropout
    )

    # 손실 함수 (다중 라벨 분류)
    if args.loss_type == 'focal':
        criterion = get_loss_function('focal', alpha=args.focal_alpha, gamma=args.focal_gamma)
        print(f"[INFO] 손실 함수: Focal Loss (alpha={args.focal_alpha}, gamma={args.focal_gamma})")
    elif args.loss_type == 'asymmetric':
        criterion = get_loss_function('asymmetric')
        print(f"[INFO] 손실 함수: Asymmetric Loss")
    else:
        # BCEWithLogitsLoss with class weights
        class_weights_dict = metadata.get('class_weights', {})
        class_weights = torch.tensor([class_weights_dict.get(str(i), 1.0) for i in range(num_classes)])
        class_weights = class_weights.to(device)
        criterion = nn.BCEWithLogitsLoss(pos_weight=class_weights)
        print(f"[INFO] 손실 함수: BCEWithLogitsLoss (클래스 가중치 적용)")

    # 옵티마이저
    optimizer = optim.Adam(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay
    )

    # Scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode='min',
        factor=0.5,
        patience=5
    )

    # 체크포인트에서 재개
    start_epoch = 0
    if args.resume:
        print(f"\n[INFO] 체크포인트 로드: {args.resume}")
        checkpoint = torch.load(args.resume, map_location=device)

        # 모델 가중치 로드
        model.load_state_dict(checkpoint['model_state_dict'])

        # 옵티마이저 상태 로드
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

        # 옵티마이저 내부 텐서를 현재 디바이스로 이동 (CPU→MPS 호환성)
        for state in optimizer.state.values():
            for k, v in state.items():
                if isinstance(v, torch.Tensor):
                    state[k] = v.to(device)

        # 스케줄러 상태 로드
        if checkpoint.get('scheduler_state_dict') and scheduler:
            scheduler.load_state_dict(checkpoint['scheduler_state_dict'])

        # 시작 에포크 설정
        start_epoch = checkpoint['epoch'] + 1

        print(f"[INFO] Epoch {checkpoint['epoch']}에서 재개")
        print(f"[INFO] 이전 최고 검증 손실: {checkpoint.get('best_val_loss', 'N/A')}")
        print(f"[INFO] 다음 에포크부터 시작: {start_epoch}")

    # Trainer 생성
    trainer = Trainer(
        model=model,
        train_loader=data_loaders['train'],
        val_loader=data_loaders['val'],
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        checkpoint_dir=args.checkpoint_dir,
        log_dir=args.log_dir,
        patience=args.patience,
        start_epoch=start_epoch
    )

    # 학습 시작
    trainer.train(num_epochs=args.num_epochs)

    print(f"✅ 학습 완료!")
    print(f"다음 단계: python evaluate.py --checkpoint {args.checkpoint_dir}/checkpoint_best.pth")


if __name__ == '__main__':
    main()
