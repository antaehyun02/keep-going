# Part 3: AI 모델 학습 기획안

## 개요

AI Hub 08-14 합성 데이터셋으로 두 가지 모델을 학습합니다:

1. **분류 모델**: DenseNet121 / EfficientNet-B3 — 6-class 피부 질환 분류
2. **세그멘테이션 모델**: DeeplabV3+ ResNet101 — 아토피피부염 병변 마스크 생성

---

## 목표 지표

| 모델 | 지표 | 목표 | Stretch |
|------|------|------|---------|
| 분류 | Top-1 Accuracy | ≥ 80% | ≥ 85% |
| 분류 | Macro F1 | ≥ 0.75 | — |
| 세그멘테이션 | IoU (병변) | ≥ 0.65 | — |
| 세그멘테이션 | Dice | ≥ 0.75 | — |

---

## 코드 구조

```
scin/model/
├── utils.py                        # 공유 유틸리티
└── aihub_classifier/
    ├── config.py                   # 하이퍼파라미터 데이터클래스
    ├── dataset.py                  # AihubFacialDataset, AihubSegDataset
    ├── model.py                    # build_classifier(), build_segmentor()
    ├── train.py                    # 분류 모델 학습
    ├── train_seg.py                # 세그멘테이션 모델 학습
    ├── evaluate.py                 # 분류 모델 평가
    └── threshold_opt.py            # 클래스별 threshold 최적화
```

---

## 공유 유틸리티 (scin/model/utils.py)

모든 학습 스크립트에서 공통으로 사용하는 함수:

```python
def get_device() -> torch.device:
    """CUDA → MPS → CPU 순서 자동 선택."""

def resolve_num_workers(device: torch.device, requested: int = 4) -> int:
    """MPS 환경에서 num_workers=0 강제 (DataLoader 데드락 방지)."""

def topk_accuracy(output, target, topk=(1, 3)) -> list[float]:
    """Top-k Accuracy 배치 계산."""
```

---

## 하이퍼파라미터 (config.py)

AI Hub 08-14 공식 권장 파라미터 기반:

```python
@dataclass
class ClassifyConfig:
    backbone: str = "densenet121"
    image_size: int = 256        # AI Hub 공식 권장
    crop_size: int = 224
    batch_size: int = 32         # AI Hub 공식 권장
    learning_rate: float = 0.001 # AI Hub 공식 권장
    dropout_rate: float = 0.5    # AI Hub 공식 권장
    num_epochs: int = 30
    optimizer: str = "adam"      # AI Hub 공식 권장
    num_classes: int = 6
    target_top1_acc: float = 0.80
    stretch_top1_acc: float = 0.85
    early_stopping_patience: int = 7

@dataclass
class SegmentConfig:
    image_size: int = 256
    batch_size: int = 16
    learning_rate: float = 0.001
    num_epochs: int = 30
    target_iou: float = 0.65
```

---

## 분류 모델 (train.py)

### 모델 아키텍처

**DenseNet121** (기본):
- ImageNet 사전학습 가중치
- 마지막 classifier: `Dropout(0.5) → Linear(1024, 6)`

**EfficientNet-B3** (선택):
- ImageNet 사전학습 가중치
- 마지막 classifier: `Dropout(0.5) → Linear(1536, 6)`

### 학습 루프

```
에폭마다:
  train_one_epoch() → train loss, top1/top3 acc
  validate()        → val loss, top1/top3 acc, macro F1

val_top1 > best → best.pth 저장
patience 초과 → early stopping
```

### 저장 파일

```
scin/checkpoints/aihub/
├── best.pth                # 최고 val Top-1 기준 체크포인트
├── epoch_{N}.pth           # 5 에폭마다 저장
├── training_log.json       # 에폭별 지표 이력
└── loss_curve.png          # Loss / Accuracy 그래프
```

### 실행

```bash
python -m scin.model.aihub_classifier.train
python -m scin.model.aihub_classifier.train --backbone efficientnet_b3
python -m scin.model.aihub_classifier.train --num_epochs 50 --batch_size 16
```

---

## 세그멘테이션 모델 (train_seg.py)

### 대상 데이터

아토피피부염 클래스만 사용 (`AihubSegDataset`).
마스크 디렉토리: `scin/data/processed_aihub/masks/`

### 모델 아키텍처

DeeplabV3+ ResNet101:
- 백본: ResNet101 (ImageNet 사전학습)
- 출력: 2-class (배경/병변)
- 보조 loss: `total_loss = main_loss + 0.4 * aux_loss`

### 평가 지표

```python
def compute_iou(pred, target, num_classes=2) -> list[float]:
def compute_dice(pred, target) -> float:
```

### 저장 파일

```
scin/checkpoints/aihub/
├── best_seg.pth
├── training_seg_log.json
└── iou_curve.png
```

### 실행

```bash
python -m scin.model.aihub_classifier.train_seg \
    --mask_dir scin/data/processed_aihub/masks
```

---

## 평가 (evaluate.py)

test.csv 기준 종합 평가:

| 지표 | 설명 |
|------|------|
| Top-1 / Top-3 Accuracy | 전체 정확도 |
| Macro F1 | 클래스 균등 가중 F1 |
| Weighted F1 | 샘플 수 비례 가중 F1 |
| Per-class AUC | 클래스별 ROC-AUC (OvR) |
| Confusion Matrix | 오분류 패턴 시각화 |

저장: `evaluation_results.json`, `confusion_matrix.png`, `roc_curves.png`

```bash
python -m scin.model.aihub_classifier.evaluate \
    --checkpoint scin/checkpoints/aihub/best.pth
```

---

## Threshold 최적화 (threshold_opt.py)

Argmax 단독 예측 대신 클래스별 softmax 확률 threshold 를 최적화하여 불확실한 예측을 "판단 불가" 로 처리.

### 모드

| 모드 | 설명 |
|------|------|
| `f1_max` | 클래스별 F1을 최대화하는 threshold |
| `precision` | 지정 precision (기본 0.75) 보장 하에 F1 최대화 |

### 탐색 범위

`np.arange(0.30, 0.96, 0.05)` — 0.30 ~ 0.95, 간격 0.05

### 출력

```json
{
  "건선": 0.55,
  "아토피피부염": 0.60,
  "여드름": 0.50,
  "주사": 0.65,
  "지루피부염": 0.55,
  "정상": 0.50,
  "_meta": {
    "mode": "f1_max",
    "val_macro_f1_before": 0.7823,
    "val_macro_f1_after": 0.8104,
    "uncertain_ratio": 0.0312
  }
}
```

저장: `scin/checkpoints/aihub/thresholds.json`

---

## 데이터 증강

### 분류 모델 (train split)

```python
RandomResizedCrop(224, scale=(0.7, 1.0))
RandomHorizontalFlip()
ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2)
RandomGrayscale(p=0.05)
ToTensor()
Normalize(IMAGENET_MEAN, IMAGENET_STD)
```

### 세그멘테이션 (albumentations, 이미지+마스크 동기)

```python
HorizontalFlip(p=0.5)
RandomBrightnessContrast(p=0.3)
ShiftScaleRotate(shift_limit=0.1, scale_limit=0.2, rotate_limit=15, p=0.5)
```

---

## 주요 설계 결정

- **DRY**: `get_device()` / `resolve_num_workers()` / `topk_accuracy()` 를 `utils.py` 로 중앙화 — 4개 스크립트에 중복 정의했던 문제 해결
- **MPS 호환성**: `resolve_num_workers()` 가 MPS 디바이스에서 자동으로 `num_workers=0` 반환
- **Threshold fallback**: `thresholds.json` 부재 시 argmax 로 자동 fallback — 모델 없이도 API 서버 기동 가능
- **Aux loss**: DeeplabV3+ 의 auxiliary classifier 를 `0.4` 가중치로 활용하여 학습 안정화
