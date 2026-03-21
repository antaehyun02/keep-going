"""
SCIN 모델 평가 스크립트 - ResNet50

학습된 ResNet50 모델의 성능을 평가하고 시각화합니다.
- Top-1, Top-3, Top-5 Accuracy
- Per-class F1-Score
- 혼동 행렬
"""

import os
import sys
import json
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import torch
import torch.nn as nn
from sklearn.metrics import f1_score, precision_score, recall_score, classification_report
from tqdm import tqdm

# 상위 디렉토리에서 dataset import
sys.path.append(str(Path(__file__).parent.parent))
from dataset import get_data_loaders
from model import ResNet50Classifier


class ModelEvaluator:
    """모델 평가기"""

    def __init__(self, model, test_loader, device, metadata, output_dir):
        """
        Args:
            model: 평가할 모델
            test_loader: 테스트 DataLoader
            device: 디바이스
            metadata: 메타데이터 (label_to_idx 등)
            output_dir: 결과 저장 디렉토리
        """
        self.model = model.to(device)
        self.test_loader = test_loader
        self.device = device
        self.metadata = metadata
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.num_classes = metadata['num_classes']
        self.idx_to_label = {int(k): v for k, v in metadata['idx_to_label'].items()}

    def evaluate(self, threshold=0.5):
        """
        모델 평가

        Args:
            threshold: 이진 분류 임계값

        Returns:
            dict: 평가 결과
        """
        print(f"\n{'='*60}")
        print("모델 평가 시작 - ResNet50")
        print(f"{'='*60}\n")

        self.model.eval()

        all_outputs = []
        all_labels = []
        all_case_ids = []

        # 예측 수행
        with torch.no_grad():
            for batch in tqdm(self.test_loader, desc="평가 중"):
                images = batch['image'].to(self.device)
                labels = batch['label']
                case_ids = batch['case_id']

                outputs = self.model(images)
                probs = torch.sigmoid(outputs).cpu()

                all_outputs.append(probs)
                all_labels.append(labels)
                all_case_ids.extend(case_ids)

        all_outputs = torch.cat(all_outputs, dim=0)  # (N, C)
        all_labels = torch.cat(all_labels, dim=0)    # (N, C)

        # 메트릭 계산
        results = {}

        # 1. Top-K Accuracy
        results['top1_accuracy'] = self.calculate_topk_accuracy(all_outputs, all_labels, k=1)
        results['top3_accuracy'] = self.calculate_topk_accuracy(all_outputs, all_labels, k=3)
        results['top5_accuracy'] = self.calculate_topk_accuracy(all_outputs, all_labels, k=5)

        print(f"\n[Top-K Accuracy]")
        print(f"  Top-1: {results['top1_accuracy']:.2%}")
        print(f"  Top-3: {results['top3_accuracy']:.2%}")
        print(f"  Top-5: {results['top5_accuracy']:.2%}")

        # 2. 이진 예측 (threshold 적용)
        all_preds_binary = (all_outputs >= threshold).float()

        # 3. Per-class 메트릭
        results['per_class_metrics'] = self.calculate_per_class_metrics(
            all_preds_binary.numpy(),
            all_labels.numpy()
        )

        # 4. Overall 메트릭
        results['overall_f1'] = f1_score(
            all_labels.numpy(),
            all_preds_binary.numpy(),
            average='macro',
            zero_division=0
        )
        results['overall_precision'] = precision_score(
            all_labels.numpy(),
            all_preds_binary.numpy(),
            average='macro',
            zero_division=0
        )
        results['overall_recall'] = recall_score(
            all_labels.numpy(),
            all_preds_binary.numpy(),
            average='macro',
            zero_division=0
        )

        print(f"\n[Overall Metrics]")
        print(f"  F1-Score:  {results['overall_f1']:.4f}")
        print(f"  Precision: {results['overall_precision']:.4f}")
        print(f"  Recall:    {results['overall_recall']:.4f}")

        # 5. 시각화
        self.plot_per_class_f1(results['per_class_metrics'])
        self.plot_top_predictions(all_outputs, all_labels, all_case_ids)

        # 6. 결과 저장
        self.save_results(results)

        print(f"\n{'='*60}")
        print("평가 완료!")
        print(f"결과 저장: {self.output_dir}")
        print(f"{'='*60}\n")

        return results

    def calculate_topk_accuracy(self, outputs, labels, k=3):
        """
        Top-K Accuracy 계산

        Args:
            outputs: (N, C) 예측 확률
            labels: (N, C) 정답 라벨
            k: Top-K

        Returns:
            float: Accuracy
        """
        _, topk_indices = outputs.topk(k, dim=1)
        label_indices = [torch.where(label == 1)[0] for label in labels]

        correct = 0
        total = len(labels)

        for i in range(total):
            if len(label_indices[i]) > 0:
                if any(idx in topk_indices[i] for idx in label_indices[i]):
                    correct += 1

        return correct / total if total > 0 else 0.0

    def calculate_per_class_metrics(self, preds, labels):
        """
        클래스별 메트릭 계산

        Args:
            preds: (N, C) 이진 예측
            labels: (N, C) 정답 라벨

        Returns:
            dict: 클래스별 메트릭
        """
        per_class = {}

        for class_idx in range(self.num_classes):
            class_name = self.idx_to_label[class_idx]

            y_true = labels[:, class_idx]
            y_pred = preds[:, class_idx]

            # 해당 클래스가 정답으로 존재하는 경우만 평가
            if y_true.sum() > 0:
                f1 = f1_score(y_true, y_pred, zero_division=0)
                precision = precision_score(y_true, y_pred, zero_division=0)
                recall = recall_score(y_true, y_pred, zero_division=0)

                per_class[class_name] = {
                    'f1': f1,
                    'precision': precision,
                    'recall': recall,
                    'support': int(y_true.sum())
                }

        return per_class

    def plot_per_class_f1(self, per_class_metrics):
        """
        클래스별 F1-Score 시각화

        Args:
            per_class_metrics: 클래스별 메트릭
        """
        # F1-Score 기준 정렬
        sorted_classes = sorted(
            per_class_metrics.items(),
            key=lambda x: x[1]['f1'],
            reverse=True
        )

        class_names = [item[0] for item in sorted_classes[:20]]  # Top 20
        f1_scores = [item[1]['f1'] for item in sorted_classes[:20]]

        plt.figure(figsize=(12, 8))
        plt.barh(class_names, f1_scores, color='skyblue')
        plt.xlabel('F1-Score', fontsize=12)
        plt.ylabel('Disease Class', fontsize=12)
        plt.title('Per-Class F1-Score (Top 20) - ResNet50', fontsize=14)
        plt.xlim(0, 1)
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()

        output_path = self.output_dir / 'per_class_f1.png'
        plt.savefig(output_path, dpi=300)
        plt.close()

        print(f"[INFO] 클래스별 F1-Score 그래프 저장: {output_path}")

    def plot_top_predictions(self, outputs, labels, case_ids, num_samples=10):
        """
        예측 예시 시각화

        Args:
            outputs: (N, C) 예측 확률
            labels: (N, C) 정답 라벨
            case_ids: 케이스 ID 리스트
            num_samples: 출력할 샘플 수
        """
        results = []

        for i in range(min(num_samples, len(outputs))):
            pred_probs = outputs[i]
            true_labels = labels[i]

            # Top-5 예측
            top5_probs, top5_indices = pred_probs.topk(5)

            # 정답 라벨
            true_indices = torch.where(true_labels == 1)[0]

            results.append({
                'case_id': case_ids[i],
                'predictions': [
                    (self.idx_to_label[idx.item()], prob.item())
                    for idx, prob in zip(top5_indices, top5_probs)
                ],
                'ground_truth': [self.idx_to_label[idx.item()] for idx in true_indices]
            })

        # 텍스트 파일로 저장
        output_path = self.output_dir / 'sample_predictions.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, result in enumerate(results):
                f.write(f"\n{'='*60}\n")
                f.write(f"샘플 {i+1} (Case ID: {result['case_id']})\n")
                f.write(f"{'='*60}\n")
                f.write(f"정답: {', '.join(result['ground_truth'])}\n\n")
                f.write(f"Top-5 예측:\n")
                for rank, (disease, prob) in enumerate(result['predictions'], 1):
                    f.write(f"  {rank}. {disease}: {prob:.4f}\n")

        print(f"[INFO] 샘플 예측 결과 저장: {output_path}")

    def save_results(self, results):
        """
        평가 결과 저장

        Args:
            results: 평가 결과 딕셔너리
        """
        # JSON으로 저장 (per_class_metrics는 별도 저장)
        summary = {
            'top1_accuracy': results['top1_accuracy'],
            'top3_accuracy': results['top3_accuracy'],
            'top5_accuracy': results['top5_accuracy'],
            'overall_f1': results['overall_f1'],
            'overall_precision': results['overall_precision'],
            'overall_recall': results['overall_recall']
        }

        summary_path = self.output_dir / 'evaluation_summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print(f"[INFO] 평가 요약 저장: {summary_path}")

        # Per-class 메트릭 저장
        per_class_path = self.output_dir / 'per_class_metrics.json'
        with open(per_class_path, 'w', encoding='utf-8') as f:
            json.dump(results['per_class_metrics'], f, indent=2, ensure_ascii=False)

        print(f"[INFO] 클래스별 메트릭 저장: {per_class_path}")


def main():
    parser = argparse.ArgumentParser(description='SCIN 모델 평가 - ResNet50')
    parser.add_argument('--checkpoint', type=str, required=True, help='모델 체크포인트 경로')
    parser.add_argument('--data_dir', type=str, default='../../data/scin_processed', help='전처리 데이터 디렉토리')
    parser.add_argument('--image_root', type=str, default='../../data/scin_dataset', help='이미지 루트 디렉토리')
    parser.add_argument('--output_dir', type=str, default='./evaluation_results', help='결과 저장 디렉토리')
    parser.add_argument('--batch_size', type=int, default=32, help='배치 크기')
    parser.add_argument('--num_workers', type=int, default=4, help='DataLoader 워커 수')
    parser.add_argument('--threshold', type=float, default=0.15, help='이진 분류 임계값 (Focal Loss: 0.15 권장)')

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
        print(f"[INFO] 디바이스: CPU")

    # 메타데이터 로드
    with open(Path(args.data_dir) / 'metadata.json', 'r') as f:
        metadata = json.load(f)

    num_classes = metadata['num_classes']
    print(f"[INFO] 클래스 수: {num_classes}")

    # DataLoader 생성 (테스트 데이터만)
    data_loaders = get_data_loaders(
        data_dir=args.data_dir,
        image_root=args.image_root,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        augment=False
    )

    # 모델 생성 (ResNet50)
    print(f"[INFO] 모델 로드: {args.checkpoint}")
    model = ResNet50Classifier(num_classes=num_classes, pretrained=False)

    # 체크포인트 로드
    checkpoint = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])

    print(f"[INFO] 체크포인트 에포크: {checkpoint['epoch']}")
    print(f"[INFO] 최고 검증 손실: {checkpoint['best_val_loss']:.4f}")

    # 평가기 생성
    evaluator = ModelEvaluator(
        model=model,
        test_loader=data_loaders['test'],
        device=device,
        metadata=metadata,
        output_dir=args.output_dir
    )

    # 평가 수행
    results = evaluator.evaluate(threshold=args.threshold)

    print(f"✅ 평가 완료!")


if __name__ == '__main__':
    main()
