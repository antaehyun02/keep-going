# Part 3-B — EfficientNet-B3 학습 기획안

AI Hub 08-14 안면부 피부질환 6종 분류, EfficientNet-B3 기반 학습 전략 설계.
DenseNet121(Part 3-A)과 동일 데이터를 사용하되, 모델 특성에 맞게 하이퍼파라미터와 전략을 차별화.

---

## 1. 목표

DenseNet121 대비 고해상도 입력과 더 깊은 feature를 활용해 **미세 병변 분류 성능을 개선**하고, 앙상블 시 DenseNet121과 **상보적 예측 다양성**을 확보한다.

| 지표 | 기준값 | 비고 |
|------|--------|------|
| Top-1 Accuracy | ≥ 83% | DenseNet121(80%) 대비 +3% 기대 |
| Top-1 Accuracy (stretch) | ≥ 87% | 고해상도 입력 + compound scaling 이점 |
| Macro F1-Score | ≥ 0.81 | |
| Macro AUC | ≥ 0.96 | |

---

## 2. DenseNet121 대비 차별점 요약

| 항목 | DenseNet121 (Part 3-A) | EfficientNet-B3 (본 문서) |
|------|----------------------|--------------------------|
| 파라미터 | 7.98M | 12.23M |
| 입력 해상도 | 224×224 | 300×300 |
| image_size | 256 | 320 |
| Pretrained 출처 | ImageNet-1K | ImageNet-1K |
| 특징 | Dense 연결, feature reuse | Compound scaling (depth+width+resolution) |
| 장점 | 적은 데이터에 안정적 | 고해상도 미세 패턴 포착 |
| 약점 | 해상도 한계 | 파라미터 多 → 과적합 위험 |

---

## 3. 모델 아키텍처

### 3-1. EfficientNet-B3 구조

```
EfficientNet-B3 (ImageNet pretrained, 12.23M params)
├── features: MBConv 블록 × 26
│   └── Depthwise Separable Conv + Squeeze-and-Excitation
├── Global Average Pooling
└── classifier (커스텀):
    ├── Dropout(0.5)
    └── Linear(1536 → 6)
```

| 항목 | 값 |
|------|-----|
| 총 파라미터 | ~12.23M |
| 입력 크기 | 3 × 300 × 300 |
| 출력 | 6클래스 logits |
| SE ratio | 0.25 |

### 3-2. 왜 EfficientNet-B3인가

- **Compound Scaling**: depth, width, resolution을 균형 있게 확장 → 같은 연산량 대비 최고 정확도
- **고해상도 입력(300px)**: 건선 인설(scale) 패턴, 여드름 미세 구진 등 텍스처 디테일 보존
- **SE 블록**: 채널별 attention으로 질환 관련 feature에 가중치 부여
- **앙상블 다양성**: DenseNet121(224px)과 해상도·구조 모두 달라 예측 상관성이 낮음

---

## 4. 학습 설정

### 4-1. 하이퍼파라미터

DenseNet121과 동일한 값은 `=` 표시, 차별화된 값은 **굵게** 표시.

| 파라미터 | 값 | DenseNet121 | 변경 이유 |
|---------|-----|-------------|----------|
| `image_size` | **320** | 256 | EfficientNet-B3 공식 입력 크기 |
| `crop_size` | **300** | 224 | 해상도 이점 최대화 |
| `batch_size` | **16** | 32 | 300px 입력 → VRAM 사용량 증가 (T4 16GB) |
| `learning_rate` | **0.0005** | 0.001 | 파라미터 多 → 낮은 lr로 안정 학습 |
| `weight_decay` | **5e-4** | 1e-4 | 과적합 억제 강화 |
| `dropout_rate` | 0.5 | = | |
| `num_epochs` | 30 | = | |
| `optimizer` | Adam | = | |
| `scheduler` | CosineAnnealingLR | = | |
| `warmup_epochs` | **5** | 3 | 큰 모델 → 긴 warmup |
| `early_stopping_patience` | 10 | = | |
| `num_workers` | 4 | = | |

### 4-2. VRAM 예산 (T4 16GB)

```
모델 파라미터 (fp32):   12.23M × 4B = ~49MB
Gradients + Optimizer:  ~150MB
배치 입력 (16 × 3 × 300 × 300): ~16MB
Feature Maps (추정):    ~2~4GB
총 예상 사용량:         ~5~6GB (T4 안전 범위)
```

batch_size=16이면 T4에서 안전. A100 할당 시 batch_size=32로 증가 가능.

### 4-3. 데이터 증강 파이프라인

DenseNet121과 동일한 augmentation 종류를 사용하되 해상도만 변경:

| 단계 | train | val |
|------|-------|-----|
| Resize | **320px** | **320px** |
| Crop | **RandomCrop(300)** | **CenterCrop(300)** |
| HorizontalFlip | p=0.5 | — |
| ColorJitter | B/C/S=0.2, H=0.1 | — |
| RandomRotation | ±15° | — |
| Normalize | ImageNet mean/std | ImageNet mean/std |

### 4-4. 데이터 경로 선택

EfficientNet-B3는 320px 입력을 사용하므로 사전 리사이즈 ZIP의 이점이 줄어든다.

| 데이터 경로 | 설명 | 권장 |
|------------|------|------|
| `data/dataset_14` (원본 1024px) | 320px로 다운샘플 — 정보 손실 최소 | ✅ 권장 |
| `data/dataset_256` (256px JPEG) | 256→320 업스케일 필요 — 정보 손실 | ❌ 비권장 |
| `data/dataset_320` (320px JPEG) | 전용 리사이즈 필요 | △ 선택적 |

**원본 1024px에서 320px로 런타임 다운샘플이 가장 정보 보존이 좋다.** I/O 최적화가 필요한 경우 전용 320px ZIP을 생성:

```bash
python -m ai.preprocessing.resize_zips --dst data/dataset_320 --size 320 --resume
python -m ai.preprocessing.aihub_preprocessor --data_root data/dataset_320 --output_dir data/processed_320
```

---

## 5. 학습 전략 비교 (EfficientNet-B3 특화)

### 5-1. 기본 전략 — Full Fine-Tuning

DenseNet121과 동일하게 전체 파라미터를 학습. 다만 12.23M 파라미터에 클래스당 1,600장은 과적합 위험이 더 높다.

**예상**: Top-1 81~84%. 10에폭 부근에서 val loss 상승 시작 가능.

### 5-2. 권장 전략 — Feature Extractor + Fine-Tuning (2-Stage)

```
Stage 1 (에폭 1~5):
    - features 전체 동결 (requires_grad=False)
    - classifier만 학습 (lr=0.001)
    - 목적: 분류 헤드를 6클래스에 적응

Stage 2 (에폭 6~30):
    - 전체 해제 (requires_grad=True)
    - lr=0.0005, CosineAnnealing
    - 목적: 피부질환 도메인에 backbone 적응
```

| 장점 | 단점 |
|------|------|
| ImageNet feature 보존 후 점진 적응 | Stage 전환 시점 수동 결정 |
| 과적합 억제 효과 | Stage 1에서 성능 정체 느낌 |

**예상**: Top-1 83~86%.

### 5-3. 대안 — EMA (Exponential Moving Average)

학습 중 모델 파라미터의 지수이동평균을 별도 유지. 평가 시 EMA 모델을 사용하면 noise가 줄어 일반화 성능이 향상된다.

```python
# EMA 업데이트 (매 step)
ema_params = decay * ema_params + (1 - decay) * model_params
```

| 장점 | 단점 |
|------|------|
| 추론 시 안정적 예측 | 학습 메모리 ~2배 (모델 복사본) |
| 추가 학습 시간 미미 | T4 VRAM에서 tight |

### 5-4. 전략 비교

| 전략 | 예상 Top-1 | 과적합 방어 | 구현 난이도 |
|------|-----------|-----------|-----------|
| Full Fine-Tuning | 81~84% | 낮음 | ★☆☆ |
| **2-Stage Freeze→Unfreeze** | **83~86%** | **높음** | **★★☆** |
| MixUp / CutMix 추가 | 83~86% | 높음 | ★★☆ |
| EMA | +0.5~1% | 중간 | ★★☆ |

**권장**: 2-Stage Freeze→Unfreeze를 기본으로, val loss 모니터링 후 MixUp 추가 여부 결정.

---

## 6. 앙상블에서의 역할

### 6-1. DenseNet121과의 상보성

```
DenseNet121 (224px):
  - 저해상도 전역 패턴 (클래스 간 색조·분포 차이)
  - Dense 연결 → 다양한 스케일 feature 혼합

EfficientNet-B3 (300px):
  - 고해상도 미세 패턴 (인설 질감, 구진 형태, 모세혈관 패턴)
  - SE 블록 → 질환 관련 채널에 집중
```

두 모델의 입력 해상도와 구조가 다르므로 **예측 오류가 겹칠 확률이 낮다** — 앙상블 효과가 극대화된다.

### 6-2. 앙상블 조합 예상 성능

| 조합 | 예상 Top-1 |
|------|-----------|
| DenseNet121 단일 | 80~83% |
| EfficientNet-B3 단일 | 83~86% |
| **두 모델 Soft Voting** | **85~88%** |
| + TTA(7) | 87~90% |

---

## 7. 학습 CLI 명령

```bash
# EfficientNet-B3 학습
python -m ai.training.classifier.train \
    --backbone efficientnet_b3 \
    --root_dir /content/skin_ai \
    --batch_size 16 \
    --learning_rate 0.0005 \
    --experiment_name effnet_b3_baseline

# 세션 만료 후 재개
python -m ai.training.classifier.train \
    --backbone efficientnet_b3 \
    --root_dir /content/skin_ai \
    --batch_size 16 \
    --resume ai/checkpoints/aihub/best.pth
```

---

## 8. DenseNet121과 비교 종합

| 항목 | DenseNet121 | EfficientNet-B3 |
|------|------------|-----------------|
| 파라미터 | 7.98M | 12.23M (+53%) |
| 입력 해상도 | 224×224 | 300×300 (+80% 픽셀) |
| batch_size (T4) | 32 | 16 |
| 에폭당 학습 시간 | ~5분 | ~8분 |
| 전체 학습 시간 (30에폭) | ~2.5시간 | ~4시간 |
| 예상 Top-1 (단일) | 80~83% | 83~86% |
| 앙상블 기여 | 전역 패턴 | 미세 패턴 |
| 추론 속도 (1장) | ~50ms | ~70ms |
| 과적합 위험 | 중간 | 높음 |
| 권장 전략 | Full Fine-Tuning | 2-Stage Freeze→Unfreeze |

---

## 9. 예상 학습 시간 (T4 GPU)

| 단계 | 소요 시간 |
|------|----------|
| 데이터 로컬 복사 | ~5분 |
| EfficientNet-B3 학습 (30에폭) | ~3.5~4시간 |
| 평가 + threshold 최적화 | ~15분 |
| 총 | ~4.5시간 |

Colab Pro 24시간 세션 내 DenseNet121 학습과 순차 실행 가능 (총 ~7.5시간).
