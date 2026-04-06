# Part 3-A — DenseNet121 학습 기획안

AI Hub 08-14 안면부 피부질환 6종 분류, DenseNet121 기반 학습 전략 설계.

---

## 1. 목표

| 지표 | 기준값 | 근거 |
|------|--------|------|
| Top-1 Accuracy | ≥ 80% | AI Hub 공식 가이드라인 최소 기준 |
| Top-1 Accuracy (stretch) | ≥ 85% | AI Hub 공식 벤치마크 달성치 (85.17%) |
| Macro F1-Score | ≥ 0.78 | 6클래스 균형 데이터에서 Top-1 80% 달성 시 대응값 |
| Macro AUC | ≥ 0.95 | OvR 기준, 6클래스 피부질환 임상 유의 수준 |

---

## 2. 학습 환경

### 2-1. Colab Pro 사양

| 항목 | 사양 |
|------|------|
| GPU | NVIDIA T4 (16GB VRAM) 또는 A100 (40GB) |
| RAM | 25.5GB (Pro 기본) |
| 디스크 | ~225GB (Pro) |
| 세션 제한 | 최대 24시간, 비활성 90분 후 만료 |
| Python | 3.10+ |

### 2-2. 데이터 적재 전략

Colab 로컬 디스크(`/content/`)에 ZIP을 복사하여 Drive FUSE 병목을 제거한다.

```python
# Colab 셀 — 세션 시작 시 1회 실행
import shutil, os
SRC = "/content/drive/MyDrive/skin_ai"
DST = "/content/skin_ai"

# 필수 파일만 선별 복사 (전체 레포 복사 불필요)
for subdir in ["data/dataset_14", "data/processed", "ai"]:
    src_path = os.path.join(SRC, subdir)
    dst_path = os.path.join(DST, subdir)
    if os.path.exists(src_path) and not os.path.exists(dst_path):
        shutil.copytree(src_path, dst_path)
```

학습 명령:
```bash
cd /content/skin_ai
python -m ai.training.classifier.train --root_dir /content/skin_ai
```

체크포인트는 학습 종료 후 Drive로 복사:
```python
shutil.copytree(
    "/content/skin_ai/ai/checkpoints/aihub",
    "/content/drive/MyDrive/skin_ai/ai/checkpoints/aihub",
    dirs_exist_ok=True,
)
```

---

## 3. 모델 아키텍처

### 3-1. DenseNet121 구조

```
DenseNet121 (ImageNet pretrained, 7.98M params)
├── features: DenseBlock × 4 + Transition × 3
│   └── 각 블록 내 BN → ReLU → Conv(1×1) → BN → ReLU → Conv(3×3) dense 연결
├── Global Average Pooling
└── classifier (커스텀):
    ├── Dropout(0.5)
    └── Linear(1024 → 6)
```

| 항목 | 값 |
|------|-----|
| 총 파라미터 | ~7.98M |
| Trainable | ~7.98M (전체 fine-tuning) |
| 입력 크기 | 3 × 224 × 224 |
| 출력 | 6클래스 logits |

### 3-2. 왜 DenseNet121인가

- AI Hub 공식 가이드라인이 DenseNet121으로 벤치마크(85.17%)를 제시
- Dense 연결로 그래디언트 소실 완화 — 적은 데이터(클래스당 1,600장)에서도 안정적 학습
- 파라미터 효율성: ResNet50(25.6M) 대비 1/3 수준
- 피부 질환처럼 텍스처 패턴이 중요한 도메인에서 feature reuse가 유리

---

## 4. 학습 설정 (현행 코드 기반)

### 4-1. 하이퍼파라미터

| 파라미터 | 값 | 근거 |
|---------|-----|------|
| `image_size` | 256 | AI Hub 가이드라인 공식값 |
| `crop_size` | 224 | ImageNet 표준 + 가이드라인 |
| `batch_size` | 32 | T4 VRAM 16GB 기준 안전 범위 |
| `learning_rate` | 0.001 | Adam + CosineAnnealing 조합 |
| `weight_decay` | 1e-4 | L2 정규화 |
| `dropout_rate` | 0.5 | 최종 분류기 앞 |
| `num_epochs` | 30 | 조기 종료 patience=10으로 보호 |
| `optimizer` | Adam | 수렴 안정성 |
| `scheduler` | CosineAnnealingLR | warmup 3에폭 후 적용 |
| `num_workers` | 4 | Colab T4 기준 적정 |

### 4-2. 데이터 증강 파이프라인

| 단계 | train | val |
|------|-------|-----|
| Resize | 256px | 256px |
| Crop | RandomCrop(224) | CenterCrop(224) |
| HorizontalFlip | p=0.5 | — |
| ColorJitter | B/C/S=0.2, H=0.1 | — |
| RandomRotation | ±15° | — |
| Normalize | ImageNet mean/std | ImageNet mean/std |

### 4-3. 체크포인트 전략

| 저장 조건 | 파일명 | 내용 |
|----------|--------|------|
| val_top1 갱신 | `best.pth` | 모델 + optimizer + epoch + history |
| 매 5에폭 | `epoch_N.pth` | 동일 |
| 학습 종료 | `training_log.json` | config + 전체 history |

`--resume ai/checkpoints/aihub/best.pth` 로 세션 만료 후 재개 가능.

---

## 5. 학습 전략 비교

### 5-1. 기본 전략 — Full Fine-Tuning (현행)

ImageNet pretrained 가중치 전체를 학습률 0.001로 fine-tuning.

| 장점 | 단점 |
|------|------|
| 구현 간단 (현행 코드 그대로) | 클래스당 1,600장에서 과적합 위험 |
| 가이드라인 벤치마크 재현 가능 | 초기 에폭에서 pretrained feature 파괴 가능 |

### 5-2. 대안 1 — Gradual Unfreezing

초기에 분류기만 학습한 뒤 단계적으로 backbone 레이어를 해제.

```
Phase 1 (에폭 1~5):  features 동결, classifier만 학습 (lr=0.001)
Phase 2 (에폭 6~15): DenseBlock 3~4 해제 (lr=0.0001)
Phase 3 (에폭 16~30): 전체 해제 (lr=0.00001)
```

| 장점 | 단점 |
|------|------|
| 저수준 feature(에지, 텍스처) 보존 | 구현 복잡도 증가 |
| 적은 데이터에서 과적합 억제 | Phase별 최적 lr 탐색 필요 |

### 5-3. 대안 2 — Knowledge Distillation (KD)

더 큰 teacher 모델(EfficientNet-B3 또는 ConvNeXt)의 soft label로 DenseNet121을 학습.

```
Loss = α × CE(student, hard_label) + (1-α) × KL(student_soft, teacher_soft)
```

| 장점 | 단점 |
|------|------|
| student 모델 크기 유지하면서 성능 향상 | teacher 모델 사전 학습 필요 |
| 추론 속도 DenseNet121 수준 유지 | 학습 파이프라인 2단계로 분리 |
| 앙상블 효과를 단일 모델에 압축 | |

### 5-4. 대안 3 — MixUp / CutMix 증강

데이터 레벨에서 두 이미지를 선형 보간(MixUp) 또는 영역 교체(CutMix)하여 학습 샘플을 다양화.

```python
# MixUp 예시
λ = Beta(0.4, 0.4).sample()
mixed_image = λ * image_a + (1-λ) * image_b
mixed_label = λ * label_a + (1-λ) * label_b
```

| 장점 | 단점 |
|------|------|
| 추가 데이터 없이 정규화 효과 | 의료 이미지에서 혼합 비율 민감 |
| 과적합 억제 + 일반화 향상 | soft label로 loss 계산 수정 필요 |
| 클래스 경계가 부드러워져 오분류 감소 | |

### 5-5. 전략 비교 요약

| 전략 | 예상 성능 | 구현 난이도 | 학습 시간 | 권장 |
|------|----------|-----------|----------|------|
| Full Fine-Tuning | 80~83% | ★☆☆ | 기본 | ✅ 1순위 (베이스라인) |
| Gradual Unfreezing | 82~85% | ★★☆ | ×1.0 | 2순위 (과적합 시) |
| MixUp / CutMix | 82~85% | ★★☆ | ×1.0 | 2순위 (과적합 시) |
| Knowledge Distillation | 83~86% | ★★★ | ×2.0 | 3순위 (앙상블 후) |

**권장 실행 순서**: Full Fine-Tuning → 결과 확인 → 과적합 시 MixUp 추가 → 성능 한계 시 KD 검토

---

## 6. 앙상블 전략

### 6-1. 앙상블 구성

| 모델 | 역할 | 입력 | 특징 |
|------|------|------|------|
| DenseNet121 (정면 전용) | 메인 분류기 | direction="front" | 정면 특화 feature |
| DenseNet121 (전체) | 보조 분류기 | direction=None | 정면+측면 통합 |
| EfficientNet-B3 | 고해상도 보조 | 320px 입력 | 미세 병변 감지 |

### 6-2. Soft Voting

```python
# 추론 시 각 모델의 softmax 확률을 가중 평균
probs_final = w1 * probs_dense_front + w2 * probs_dense_all + w3 * probs_eff
pred = probs_final.argmax()
```

가중치 w1, w2, w3는 val set에서 각 모델의 Macro F1을 기준으로 비례 할당:
```python
w_i = f1_i / sum(f1_all)
```

### 6-3. Test-Time Augmentation (TTA)

추론 시 동일 이미지에 N가지 변형을 적용하고 softmax 평균을 내어 예측 안정성을 높인다.

| 변형 | 설명 |
|------|------|
| 원본 | CenterCrop(224) |
| 좌우 반전 | HorizontalFlip |
| 5-Crop | 상하좌우 코너 + 중앙 224×224 |

```python
# TTA 추론 흐름
augments = [original, flip, crop_tl, crop_tr, crop_bl, crop_br, crop_center]
probs = [model(aug) for aug in augments]
final_prob = mean(probs)
```

### 6-4. 앙상블 성능 기대치

| 구성 | 예상 Top-1 | 추론 시간 (1장) |
|------|-----------|----------------|
| DenseNet121 단일 | 80~83% | ~50ms |
| DenseNet121 + TTA(7) | 82~85% | ~350ms |
| DenseNet121 + EfficientNet-B3 Soft Voting | 84~87% | ~120ms |
| 3모델 앙상블 + TTA | 85~88% | ~800ms |

---

## 7. 평가 체계

### 7-1. 평가 지표

| 지표 | 의미 | 사용 시점 |
|------|------|----------|
| Top-1 Accuracy | 최고 확률 클래스가 정답인 비율 | 주 평가 |
| Top-3 Accuracy | 상위 3개에 정답 포함 비율 | 보조 (임상 참고) |
| Macro F1 | 클래스별 F1의 산술평균 | 균형 성능 |
| Macro AUC (OvR) | 클래스별 ROC AUC 평균 | 분류 경계 품질 |
| Confusion Matrix | 클래스 간 오분류 패턴 | 오분류 진단 |
| Per-Class AUC | 개별 클래스 판별력 | 약점 클래스 식별 |

### 7-2. 평가 파이프라인 (현행 코드)

```bash
# 1. 모델 평가
python -m ai.testing.evaluate --checkpoint ai/checkpoints/aihub/best.pth

# 2. 클래스별 threshold 최적화
python -m ai.testing.threshold_opt --checkpoint ai/checkpoints/aihub/best.pth
```

평가 결과물:
- `eval_results/confusion_matrix.png`
- `eval_results/roc_curves.png`
- `eval_results/evaluation_results.json`
- `ai/checkpoints/aihub/thresholds.json`

### 7-3. 주의: 현행 evaluate.py가 test.csv를 참조

현재 `evaluate.py`는 `data_dir / "test.csv"` 를 읽도록 되어 있다. AI Hub 데이터셋에는 test split이 없으므로, val.csv를 사용하거나 별도 test split을 생성해야 한다.

---

## 8. Colab 실행 체크리스트

```
[ ] 1. Drive 마운트 및 로컬 복사
[ ] 2. pip install 필수 패키지 (torch, torchvision, pandas, tqdm, Pillow, matplotlib, sklearn)
[ ] 3. python -m ai.training.classifier.train --root_dir /content/skin_ai
[ ] 4. 학습 완료 후 체크포인트 Drive 복사
[ ] 5. python -m ai.testing.evaluate --checkpoint ai/checkpoints/aihub/best.pth
[ ] 6. python -m ai.testing.threshold_opt --checkpoint ai/checkpoints/aihub/best.pth
[ ] 7. 앙상블 전략 적용 (단일 모델 성능 확인 후)
```

---

## 9. 예상 학습 시간 (T4 GPU)

| 단계 | 소요 시간 |
|------|----------|
| 데이터 로컬 복사 | ~5분 |
| DenseNet121 학습 (30에폭) | ~2~3시간 |
| 평가 + threshold 최적화 | ~10분 |
| 총 | ~3시간 |

Colab Pro 24시간 세션 내 충분히 완료 가능.
