# Dataset 15 통합 기획

## Context

Dataset 14(안면부 피부질환 6종)에 Dataset 15(피부종양 15종)가 추가되었다.  
두 데이터셋의 통합 방향, 전처리 호환성, 모델 설계를 결정해야 한다.  
기존 `skinai_docs/dataset_classification_strategy.md`에 멀티헤드 구조 설계안이 이미 존재하며, 본 기획은 그 실행 계획이다.

---

## 1. Dataset 15 구조 분석

```
data/dataset_15/
├── Training/
│   ├── 01_raw/    ← TS_{클래스명}.zip  (이미지, 15개)
│   └── 02_label/  ← TL_{클래스명}.zip  (JSON 라벨, 15개)
└── Validation/
    ├── 01_raw/    ← VS_{클래스명}.zip
    └── 02_label/  ← VL_{클래스명}.zip
```

**15개 클래스 (위험도별):**

| 위험도 | 클래스 |
|--------|--------|
| 악성 (3) | 악성흑색종, 기저세포암, 편평세포암 |
| 전암성 (2) | 보웬병, 광선각화증 |
| 추적 필요 (2) | 멜라닌세포모반, 흑색점 |
| 양성 (8) | 지루각화증, 사마귀, 피부섬유종, 혈관종, 화농 육아종, 표피낭종, 비립종, 피지샘증식증 |

**Dataset 14와의 구조적 차이:**

| 항목 | Dataset 14 | Dataset 15 |
|------|-----------|-----------|
| ZIP 파일명 | `TS_{클래스}_정면.zip` / `TS_{클래스}_측면.zip` | `TS_{클래스}.zip` (방향 없음) |
| 클래스 수 | 6 | 15 |
| 촬영 부위 | 안면 | 전신 |
| 악성 클래스 | 없음 | 3개 |
| 총 용량 | ~12GB (원천) | ~6.4GB (원천) |

---

## 2. 핵심 결정: 분리 학습 vs 통합 학습

### 결론: **1단계는 분리 학습, 2단계에서 멀티헤드 통합**

**분리 학습을 먼저 하는 이유:**
1. **도메인 갭**: DS14는 안면 중심, DS15는 전신 — 입력 분포가 다름
2. **임상 목적 분리**: 염증성 진단 vs 종양 위험도 분류는 서로 다른 임상 태스크
3. **악성 클래스 안전성**: 악성흑색종/기저세포암 등 악성 클래스가 DS14 데이터와 섞이면 False Negative 위험 증가
4. **검증 독립성**: 각 도메인 성능을 독립적으로 측정·검증 가능
5. **빠른 iteration**: 15-class 단독 모델로 먼저 기준 성능(baseline)을 확보

---

## 3. 전처리 — 기존 로직 재사용 여부

### 결론: **핵심 로직 재사용, ZIP 파싱 규칙만 수정**

기존 `AIHubPreprocessor` (`ai/preprocessing/aihub_preprocessor.py`)의 구조:
- ZIP 스캔 → JSON 라벨 파싱 → CSV 생성 → `metadata.json` 출력

**재사용 가능한 부분:**
- ZIP에서 이미지 파일 목록 추출 로직
- JSON 라벨 인덱싱 로직 (`identifier → metadata`)
- CSV 컬럼 구조 (`zip_path`, `filename`, `class_idx`, `class_name`, `split`)
- `AihubFacialDataset`의 ZIP 캐시 + `_load_image_from_zip()` 전체

**수정이 필요한 부분:**

| 항목 | 기존 DS14 | DS15 변경사항 |
|------|-----------|---------------|
| ZIP 파일명 파싱 | `{prefix}_{클래스}_{방향}.zip` | `{prefix}_{클래스}.zip` (방향 필드 제거) |
| `CLASS_MAP` | `CLASS_MAP` (6클래스) | `CLASS_MAP_15` (15클래스) |
| CSV `direction` 컬럼 | "front" / "side" | 없음 (또는 "N/A") |
| 출력 경로 | `data/processed/` | `data/processed_15/` |

**구현 방식:** `aihub_preprocessor.py`를 직접 수정하지 않고, `ai/preprocessing/aihub_preprocessor_15.py`를 새 파일로 작성해 공통 유틸을 import해 재사용한다.

---

## 4. DL 모델 — 기존 방식 재사용 여부

### 결론: **백본은 동일(DenseNet121/EfficientNet-B3), 헤드·손실함수 변경**

**재사용 가능한 부분:**
- `build_classifier()` 함수 구조 (`ai/training/classifier/model.py`)
- ImageNet pretrained 백본 + Dropout + Linear 헤드 패턴
- Adam + CosineAnnealingLR 스케줄러 조합
- `train.py` 학습 루프 전반 (epoch 루프, 체크포인트, 조기종료)
- `get_transforms()`, `worker_init_fn()` (`ai/dataset/dataset.py`)

**변경이 필요한 부분:**

| 항목 | DS14 설정 | DS15 설정 | 이유 |
|------|-----------|-----------|------|
| `num_classes` | 6 | 15 | 클래스 수 증가 |
| `CLASS_MAP` | 6개 | 15개 | 새 도메인 |
| 손실함수 | `CrossEntropyLoss` | **`FocalLoss`** | 악성 클래스(3개) 극심한 샘플 불균형 |
| 샘플러 | 기본 random | **`WeightedRandomSampler`** | 악성:양성 샘플 비율 불균형 보정 |
| `checkpoint_dir` | `ai/checkpoints/aihub/` | `ai/checkpoints/aihub_15/` | 분리 관리 |
| `loss_weight` | 없음 | 악성 클래스에 가중치 추가 | 임상적 중요도 반영 |

**새 config 파일:** `ai/training/classifier/config_15.py` (ClassifyConfig를 상속 또는 복사)

---

## 5. Colab G4 (VRAM ~96GB) 학습 파라미터 권장값

G4는 VRAM이 96GB급으로, 현재 코드의 기본값이 이 스펙에 크게 못 미친다.

### DS14 현재 학습 (DenseNet121)

| 파라미터 | 기본값 | G4 권장값 | 이유 |
|----------|--------|-----------|------|
| `batch_size` | 32 | **256** | VRAM 96GB → DenseNet121 224px 기준 OOM 전혀 없음 |
| `num_workers` | 4 | **4** | Colab CPU 코어 수 기준 유지 |
| `image_size/crop_size` | 256/224 | 유지 | 모델 공식 입력 크기. 키워도 정확도 이득 없음 |

```python
# DS14 G4 권장 실행 명령
!python -m ai.training.classifier.train \
    --backbone densenet121 \
    --num_epochs 50 \
    --batch_size 256 \
    --root_dir {PROJECT_ROOT}
```

### DS14 EfficientNet-B3 비교 런

| 파라미터 | 기본값 | G4 권장값 |
|----------|--------|-----------|
| `batch_size` | 16 | **128** |
| `image_size/crop_size` | 320/300 | 유지 |

### DS15 학습 (Phase 2 — 아래 구현 계획 기반)

DS15도 동일하게 `batch_size 256` 기준으로 설계. FocalLoss + WeightedRandomSampler는 batch가 클수록 클래스 분포 안정성이 높아져 더 유리함.

---

## 6. 구현 계획

### Phase 1 — Dataset 15 전처리

**신규 파일:** `ai/preprocessing/aihub_preprocessor_15.py`

1. `CLASS_MAP_15` 정의 (15클래스, `ai/dataset/dataset.py`에 추가)
2. ZIP 파일명 파싱: `TS_{클래스}.zip` → class_name 추출 (방향 없음)
3. JSON 라벨 파싱 로직 재사용 (기존 `_build_json_index()` 패턴)
4. 출력: `data/processed_15/train.csv`, `val.csv`, `metadata.json`

**실행:**
```bash
python -m ai.preprocessing.aihub_preprocessor_15 \
  --data_root data/dataset_15 \
  --output_dir data/processed_15
```

### Phase 2 — Dataset 15 단독 모델 학습

**신규/수정 파일:**
- `ai/dataset/dataset.py` — `CLASS_MAP_15` 상수 추가, `AihubTumorDataset` 클래스 추가 (or `dataset` 파라미터로 분기)
- `ai/training/classifier/config_15.py` — `ClassifyConfig` 상속, DS15 전용 설정 오버라이드
- `ai/training/classifier/train_15.py` — `FocalLoss`, `WeightedRandomSampler` 적용

**학습 설정 (DS15):**
```python
num_classes     = 15
loss_fn         = FocalLoss(gamma=2.0, alpha=malignant_weights)
sampler         = WeightedRandomSampler(class_weights, num_samples)
checkpoint_dir  = "ai/checkpoints/aihub_15"
target_top1_acc = 0.75   # 15-class이므로 DS14보다 낮게 설정
```

**실행:**
```bash
python -m ai.training.classifier.train_15
python -m ai.training.classifier.train_15 --backbone efficientnet_b3
```

### Phase 3 — 멀티헤드 통합 (후속 작업)

`dataset_classification_strategy.md` §3 설계안대로 진행:
- Shared Backbone (EfficientNet-B3) + Domain Router (3-class) + DS14 Head (5-class) + DS15 Head (15-class)
- 학습 3단계: 백본 freeze → 헤드별 학습 → 전체 fine-tuning

---

## 7. 검증 계획

```bash
# 전처리 결과 확인
python -m ai.preprocessing.aihub_validate --processed_dir data/processed_15

# 학습 실행 및 체크포인트 확인
python -m ai.training.classifier.train_15
ls ai/checkpoints/aihub_15/

# 평가 (수정 필요: evaluate.py가 num_classes=15 지원하도록)
python -m ai.testing.evaluate --checkpoint ai/checkpoints/aihub_15/best.pth

# 혼동 행렬에서 중점 확인
# - 악성흑색종 ↔ 멜라닌세포모반 (가장 중요)
# - 기저세포암 ↔ 지루각화증
# - 지루피부염(DS14명칭 혼동 주의) vs 지루각화증(DS15)
```

---

## 8. 수정 대상 파일 목록

| 파일 | 작업 유형 | 내용 |
|------|-----------|------|
| `ai/dataset/dataset.py` | 수정 | `CLASS_MAP_15` 상수 추가, `AihubTumorDataset` 추가 |
| `ai/preprocessing/aihub_preprocessor_15.py` | 신규 | DS15 전처리 파이프라인 |
| `ai/training/classifier/config_15.py` | 신규 | DS15 전용 ClassifyConfig |
| `ai/training/classifier/train_15.py` | 신규 | FocalLoss + WeightedRandomSampler 적용 학습 |
| `ai/testing/evaluate.py` | 수정 | `num_classes` 파라미터화 (현재 6 고정 여부 확인) |
