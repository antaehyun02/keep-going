# Part 2 — 전처리 파이프라인 기획

AI Hub 08-14 안면부 피부질환 데이터셋 전처리 설계 및 구현 상세 문서.

---

## 1. 데이터셋 원천 구조

### 1-1. ZIP 파일 명명 규칙

```
TS_아토피_정면.zip
│└ ─────────────── 방향: 정면 → front / 측면 → side
│  └────────────── 클래스 (단축명 포함)
└───────────────── 접두사 2글자: [T/V/E][S/L]
                     T=Training, V=Validation, E=Evaluation
                     S=Source(원천),  L=Label(라벨)
```

| 접두사 | 의미 | 예시 |
|--------|------|------|
| `TS` | Training Source (원천 이미지) | `TS_건선_정면.zip` |
| `TL` | Training Label (JSON 라벨) | `TL_건선_정면.zip` |
| `VS` | Validation Source | `VS_건선_정면.zip` |
| `VL` | Validation Label | `VL_건선_정면.zip` |

ZIP명에 클래스 단축명이 사용되므로 정규화가 필요하다:
- `아토피` → `아토피피부염`
- `지루` → `지루피부염`

### 1-2. ZIP 내부 구조

원천 ZIP은 **flat 구조** — 서브디렉토리 없이 PNG가 루트에 위치하며, 내부 경로에 leading slash(`/`)가 포함된다.

```
TS_건선_정면.zip
  /H0_115010_P1_L1.png     ← leading slash 포함 (실측 확인)
  /H0_115010_P2_L0.png
  ...  (800개)
```

파일명 규칙: `H{지역코드}_{피험자ID}_P{카메라}_L{조명}.png`

라벨 ZIP은 JSON만 포함, PNG(병변 마스크)는 없다 — 전체 24개 라벨 ZIP 실측 확인 결과.

```
TL_건선_정면.zip
  H0_115010_P1_L1.json     ← 피험자 1인당 JSON 1개 (800개)
  ...
```

### 1-3. 라벨 JSON 구조 (클래스별 차이)

```json
{
  "annotations": [{
    "identifier": "H0_111445_P6_L0",
    "diagnosis_info": {
      "diagnosis_name": "아토피",
      "easi_score": {                       ← 아토피 전용
        "iga_grade": "Moderate"
      }
    },
    "generated_parameters": {
      "gender": "남", "age_range": "19-29", "race": "황인"
    },
    "bbox": {
      "lesion_area": "아토피/정면/lesion_area/H0_111445_P6_L0.png",
      "lesions": [                          ← 여드름 전용
        { "xpos": 394, "ypos": 167, "width": 17, "height": 17, "inflammatory": true }
      ]
    }
  }]
}
```

클래스별 JSON 필드 차이:

| 클래스 | 전용 필드 | 비고 |
|--------|-----------|------|
| 아토피피부염 | `diagnosis_info.easi_score.iga_grade` | Clear / Almost Clear / Mild / Moderate / Severe (IGA 5단계) |
| 여드름 | `bbox.lesions[].inflammatory` | 병변별 염증성 여부 (true/false) |
| 건선·주사·지루 | — | 공통 필드만 |
| 정상 | — | bbox 없음 |

### 1-4. 데이터셋 규모

| Split | 클래스 | 방향 | ZIP 수 | 이미지/ZIP | 총 이미지 |
|-------|--------|------|--------|-----------|-----------|
| Training | 6 | 정면·측면 | 12 | 800 | **9,600장** |
| Validation | 6 | 정면·측면 | 12 | 100 | **1,200장** |

- 원본 해상도: **1,024 × 1,024px**, 평균 **950KB/장**
- 전체 ZIP 용량: **9.78GB** (PNG 무손실이라 압축률 0% — 해제해도 동일 용량)
- 클래스 완전 균형: train 1,600장/클래스, val 200장/클래스

---

## 2. 전처리 파이프라인 상세 흐름

`python -m ai.preprocessing.aihub_preprocessor` 실행 시 `AIHubPreprocessor.run()`이 3단계로 동작한다.

### Step 1 — 디렉토리 스캔

```
data/dataset_14/Training/01_raw/   → TS_*.zip 12개 (sorted)
data/dataset_14/Validation/01_raw/ → VS_*.zip 12개 (sorted)
```

### Step 2 — ZIP명 파싱 (`_parse_zip_name`)

```
"TS_아토피_정면.zip"
  stem = "TS_아토피_정면"
  parts = ["TS", "아토피", "정면"]
  prefix[0] = 'T'  →  split = "train"
  prefix[1] = 'S'  →  원천 파일 확인
  parts[1]  = "아토피"  →  CLASS_NAME_ALIASES  →  "아토피피부염"
  parts[2]  = "정면"   →  DIRECTION_MAP       →  "front"
```

### Step 3 — 라벨 ZIP 경로 추론 (`_label_zip_path`)

```
01_raw/TS_아토피_정면.zip
            ↓ (두 번째 글자 S→L, 상위 디렉토리 01_raw→02_label)
02_label/TL_아토피_정면.zip
```

### Step 4 — 라벨 JSON 인덱스 구축 (`_build_json_index`)

라벨 ZIP 전체를 한 번 순회해 메모리 인덱스 생성. 이후 원천 이미지 조회는 O(1).

```
TL_아토피_정면.zip 열기
→ namelist() 에서 *.json 800개 필터
→ 각 JSON 파싱:
    identifier = annotations[0]["identifier"]   # "H0_111445_P6_L0"
    gender     = generated_parameters["gender"]
    age_range  = generated_parameters["age_range"]
    race       = generated_parameters["race"]
    severity   = diagnosis_info.easi_score.iga_grade  # 아토피만
    lesion_type = bbox.lesions[0]["inflammatory"]      # 여드름만
→ index["H0_111445_P6_L0"] = {gender, age_range, race, severity, lesion_type}
```

### Step 5 — 원천 ZIP 이미지 파일명 수집

```
TS_아토피_정면.zip 열기
→ namelist() 에서 *.png 800개
→ "/H0_111445_P6_L0.png".lstrip("/") → "H0_111445_P6_L0.png"
→ stem = "H0_111445_P6_L0"
→ index.get("H0_111445_P6_L0", {})  → 메타데이터 O(1) 조회
```

### Step 6 — 레코드 조립 (이미지 1장 = CSV 1행)

```python
{
    "zip_path"   : "/abs/path/data/dataset_14/Training/01_raw/TS_아토피_정면.zip",
    "filename"   : "H0_111445_P6_L0.png",
    "class_name" : "아토피피부염",
    "class_idx"  : 1,
    "split"      : "train",
    "direction"  : "front",
    "gender"     : "남",
    "age_range"  : "19-29",
    "race"       : "황인",
    "severity"   : "Moderate",   # 아토피만, 나머지 ""
    "lesion_type": "",
}
```

---

## 3. 전처리 결과물 형식

### 3-1. CSV 파일 (`data/processed/train.csv`, `val.csv`)

실제 컬럼 및 예시 행:

```
zip_path,filename,class_idx,class_name,split,direction,gender,age_range,race,severity,lesion_type
/abs/.../TS_아토피_정면.zip,H0_111445_P6_L0.png,1,아토피피부염,train,front,남,19-29,황인,Moderate,
/abs/.../TS_여드름_정면.zip,H0_205860_P1_L2.png,2,여드름,train,front,여,30-39,황인,,True
/abs/.../TS_정상_정면.zip,H0_312400_P2_L0.png,5,정상,train,front,남,40-49,황인,,
```

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `zip_path` | str | 원천 ZIP 절대경로 (학습 시 직접 열기용) |
| `filename` | str | ZIP 내 파일명 (leading slash 제거됨) |
| `class_idx` | int | 0~5 |
| `class_name` | str | 정식 클래스명 |
| `split` | str | train / val |
| `direction` | str | front / side |
| `gender` | str | 남 / 여 |
| `age_range` | str | 10대 / 19-29 / 30-39 / 40-49 / 50-59 / 60대이상 |
| `race` | str | 황인 / 백인 / 흑인 |
| `severity` | str | Mild/Moderate/Severe (아토피만, 나머지 빈 문자열) |
| `lesion_type` | str | True/False (여드름만, 나머지 빈 문자열) |

### 3-2. metadata.json

전체 레코드 수집 완료 후 집계:

```json
{
  "num_classes": 6,
  "class_map": {
    "건선": 0, "아토피피부염": 1, "여드름": 2,
    "주사": 3, "지루피부염": 4, "정상": 5
  },
  "splits": {
    "train": 9600,
    "val": 1200,
    "test": 0
  },
  "class_distribution": {
    "train": {
      "건선": 1600, "아토피피부염": 1600, "여드름": 1600,
      "주사": 1600, "지루피부염": 1600, "정상": 1600
    },
    "val": {
      "건선": 200, "아토피피부염": 200, "여드름": 200,
      "주사": 200, "지루피부염": 200, "정상": 200
    }
  },
  "processed_at": "2026-03-31T18:40:00"
}
```

---

## 4. dataset.py — 학습 단계 연계

전처리가 생성한 CSV를 DataLoader가 소비하는 흐름.

### 4-1. 이미지 로드 흐름 (`AihubFacialDataset.__getitem__`)

```
__getitem__(idx)
  1. df.iloc[idx]  →  zip_path, filename, class_idx

  2. zipfile.ZipFile(zip_path)  ← 매번 새 파일 핸들 생성 (multiprocessing safe)

  3. 파일명 탐색 (leading slash 이중 시도)
       1차: "H0_111445_P6_L0.png"
       2차: "/H0_111445_P6_L0.png"

  4. zf.open(target)
     → io.BytesIO(f.read())
     → PIL.Image.open().convert("RGB")

  5. transform(image)  →  Tensor (3, 224, 224) float32

  6. return (tensor, class_idx)
```

**Fallback 전략**: 로드 실패 시 인접 인덱스 +1~+10 순환 탐색. 전부 실패 시 `zeros(3, 224, 224)` 더미 반환으로 배치 크기 유지.

### 4-2. 증강 파이프라인 (`get_transforms`)

| 단계 | train | val / test |
|------|-------|------------|
| Resize | 256px | 256px |
| Crop | RandomCrop(224) | CenterCrop(224) |
| HorizontalFlip | p=0.5 | — |
| ColorJitter | brightness/contrast/saturation=0.2, hue=0.1 | — |
| Rotation | ±15° | — |
| Normalize | ImageNet mean/std | ImageNet mean/std |

1,024px 원본을 256으로 다운샘플 후 224로 크롭하는 2단계는 AI Hub 공식 가이드라인 값이다 (DenseNet121 기준 Top-1 85.17% 달성 조건).

---

## 5. 학습에서의 이점

### 5-1. 메타데이터 사전 결합

JSON 800개를 에폭마다 재파싱하는 대신, 전처리 시 1회 인덱싱해 CSV에 결합한다. 학습 중에는 CSV 1회 로드만으로 모든 메타데이터를 사용할 수 있다.

- 서브그룹 분석: gender / age_range별 클래스 정확도 비교 — 추가 전처리 없이 가능
- 중증도별 평가: 아토피 Mild/Moderate/Severe 각각의 예측 신뢰도 측정
- 외부 데이터 결합 시 클래스 불균형 감지 및 가중치 보정

### 5-2. 클래스 완전 균형

정면 기준 train 1,600장/클래스, val 200장/클래스로 완전 균형. WeightedRandomSampler나 focal loss 없이 균등 학습이 가능하며, Confusion Matrix가 정규화 없이도 직관적으로 해석된다.

### 5-3. direction 컬럼으로 학습 분기

정면 전용 모델과 정면+측면 통합 모델을 동일한 CSV에서 `direction` 필터 하나로 분기할 수 있다. 앙상블 시 두 모델을 조합해 촬영 방향에 따른 오분류를 줄인다.

---

## 6. 앙상블 전처리 전략

앙상블은 여러 모델의 softmax 확률 평균(Soft Voting)으로 최종 클래스를 결정한다. 전처리 설계가 앙상블을 직접 지원하는 지점은 다음과 같다.

### 6-1. 동일 CSV + 모델별 다른 transform

각 모델이 동일한 `train.csv`를 읽되, `get_transforms(config=model_config)`로 해상도와 증강 강도를 달리 적용한다. 모델별로 다른 스케일의 특징을 학습하게 되어 예측 다양성(diversity)이 확보된다.

| 모델 | image_size | crop_size | 특징 |
|------|------------|-----------|------|
| DenseNet121 | 256 | 224 | 기본 (AI Hub 공식값) |
| EfficientNet-B3 | 320 | 300 | 고해상도 — 미세 병변 포착 |
| ResNet50 | 256 | 224 | 경량 — 앙상블 다양성 보완 |

### 6-2. Test-Time Augmentation (TTA)

추론 시 동일 이미지에 flip / crop 위치 변형을 N회 적용하고 softmax 평균을 낸다. transform이 함수로 분리되어 있어 추론 코드에서 augment → predict → average 루프를 추가하는 것만으로 TTA를 적용할 수 있다.

### 6-3. 방향별 앙상블

```python
# 정면 전용 모델
dataset_front = AihubFacialDataset(csv, direction="front")

# 정면+측면 통합 모델
dataset_all = AihubFacialDataset(csv, direction=None)
```

두 모델을 학습한 뒤 추론 시 softmax 확률을 가중 평균하면 방향에 따른 오분류를 보완한다.

---

## 7. 현재 이슈 및 해결방안

### 이슈 1 — 세그멘테이션 마스크 별도 미제공

**현상**: 라벨 ZIP 24개 전체에 PNG 파일 0개 (실측 확인). JSON의 `bbox.lesion_area` 필드는 경로 문자열만 기록됨 — 실제 마스크 이미지는 포함되지 않음.

**배경**: AI Hub 08-14 데이터셋의 설계 방침으로 추정. 원천 PNG와 동일한 마스크가 라벨 ZIP에 별도 포함되는 구조가 아님. `AihubSegDataset`은 외부 `mask_dir` 경로를 받아 마스크를 로드하도록 설계되어 있으며, 파일이 없으면 `zeros(H, W)` 마스크를 반환한다.

**영향**: 현재 `train_seg.py` 실행 시 모든 픽셀이 배경으로 학습됨 → 세그멘테이션 학습 불가.

**해결방안 (우선순위 순)**:

| 방법 | 비용 | 품질 |
|------|------|------|
| AI Hub 공식 마스크 재신청 | 시간 | 높음 |
| Meta SAM (Segment Anything) 자동 생성 | 중간 | 중간 |
| LabelMe 수동 어노테이션 | 노력 큼 | 높음 |

---

### 이슈 2 — ZIP 반복 개방 I/O 병목 → 구현 완료

**현상**: `__getitem__` 호출마다 `zipfile.ZipFile()` 을 열고 닫음. 이미지 1장 평균 로딩 **13.2ms** (실측).

**영향**: `num_workers=4` 기준 배치(32장) 로딩 **106ms** vs DenseNet121 GPU forward **~50ms** → 데이터 로딩이 학습 병목.

**구현 내용** (`ai/dataset/dataset.py`):

워커 프로세스별 ZIP 핸들 캐시(`_WORKER_ZIP_CACHE`)를 도입. `_load_image_from_zip`이 매번 ZIP을 새로 열지 않고 캐시된 핸들을 재사용한다.

```python
# 워커 시작 시 1회 호출 — fork 상속 핸들 정리 및 캐시 초기화
def worker_init_fn(worker_id: int) -> None:
    global _WORKER_ZIP_CACHE
    _WORKER_ZIP_CACHE = {}

# 캐시 miss 시만 ZipFile 개방
def _get_cached_zip(zip_path: str) -> zipfile.ZipFile:
    if zip_path not in _WORKER_ZIP_CACHE:
        _WORKER_ZIP_CACHE[zip_path] = zipfile.ZipFile(zip_path, "r")
    return _WORKER_ZIP_CACHE[zip_path]
```

DataLoader에 적용:
```python
from ai.dataset.dataset import worker_init_fn

DataLoader(..., num_workers=8, worker_init_fn=worker_init_fn)
```

- `num_workers=0` (메인 프로세스)에서도 캐시가 동작해 반복 개방 비용 제거
- 워커 프로세스별 독립 메모리 공간이므로 동기화 불필요

---

### 이슈 3 — 1,024px 원본 전체 로드 → 구현 완료

**현상**: `transform`의 `Resize(256)` 실행 전에 1,024×1,024 전체를 메모리에 적재. 장당 950KB를 CPU 메모리에 올린 후 즉시 축소.

**영향**: 배치 32장 기준 ~30MB 순간 점유. 메모리 제한 환경에서 OOM 위험.

**구현 내용** (`ai/preprocessing/resize_zips.py`):

원본 ZIP을 읽어 이미지를 지정 크기로 리사이즈 후 JPEG로 인코딩해 새 ZIP에 저장하는 사전 변환 스크립트.

```bash
# 256px JPEG ZIP 생성 (9.78GB → 약 2GB)
python -m ai.preprocessing.resize_zips --resume

# EfficientNet-B3 전용 320px
python -m ai.preprocessing.resize_zips --dst data/dataset_320 --size 320

# 변환 후 전처리 재실행
python -m ai.preprocessing.aihub_preprocessor --data_root data/dataset_256
```

변환 ZIP의 내부 구조는 원본과 동일하고 파일명만 `.png` → `.jpg` 로 변경됨. `aihub_preprocessor`는 `.jpg`도 수집하므로 전처리·학습 파이프라인 수정 불필요.

| 항목 | 원본 (1,024px PNG) | 변환 후 (256px JPEG Q85) |
|------|--------------------|--------------------------|
| 총 용량 | 9.78 GB | ~2 GB |
| 장당 로드 크기 | 950 KB | ~40 KB |
| 예상 로딩 속도 | 13.2 ms/장 | 3~5 ms/장 |

---

## 8. 실행 명령 요약

전체 파이프라인은 두 가지 경로로 실행할 수 있다.

### 경로 A — 원본 1,024px 그대로 사용

```bash
# 1. 전처리 (ZIP 스캔 + 라벨 JSON 결합 → CSV)
python -m ai.preprocessing.aihub_preprocessor \
    --data_root data/dataset_14 \
    --output_dir data/processed

# 2. 검증 (CSV 무결성, 클래스 균형 확인)
python -m ai.preprocessing.aihub_validate --processed_dir data/processed

# 3. EDA 시각화 (data/processed/eda/*.png 저장)
python -m ai.preprocessing.aihub_eda --processed_dir data/processed
```

### 경로 B — 256px JPEG 사전 변환 후 사용 (권장)

```bash
# 1. 1,024px PNG → 256px JPEG ZIP 변환 (9.78GB → ~2GB, 이슈 2·3 해결)
python -m ai.preprocessing.resize_zips --resume

# EfficientNet-B3 전용 320px 변환이 필요한 경우
python -m ai.preprocessing.resize_zips --dst data/dataset_320 --size 320 --resume

# 2. 전처리
python -m ai.preprocessing.aihub_preprocessor \
    --data_root data/dataset_256 \
    --output_dir data/processed_256

# 3. 검증 · EDA
python -m ai.preprocessing.aihub_validate --processed_dir data/processed_256
python -m ai.preprocessing.aihub_eda --processed_dir data/processed_256
```

### 전처리 산출물

| 파일 | 내용 |
|------|------|
| `data/processed/train.csv` | 학습 이미지 레코드 9,600행 |
| `data/processed/val.csv` | 검증 이미지 레코드 1,200행 |
| `data/processed/metadata.json` | 클래스 분포, 처리 일시 |
| `data/processed/eda/*.png` | 클래스 분포 · 방향별 통계 차트 |

---

## 9. 전처리 결과 요약 (2026-04-06 실측)

### 9-1. 수집 결과

| Split | 총 레코드 | 클래스당 | 정면 | 측면 |
|-------|----------|---------|------|------|
| train | **9,600** | 1,600 | 800 | 800 |
| val   | **1,200** | 200    | 100 | 100 |

클래스·방향 모두 완전 균형 (min/max = 1.00). `WeightedRandomSampler` 불필요.

### 9-2. 메타데이터 결합 완성도

| 컬럼 | train | val | 비고 |
|------|-------|-----|------|
| `gender` | 100% | 100% | 전 클래스 |
| `age_range` | 100% | 100% | 전 클래스 |
| `race` | 100% | 100% | 전 클래스 (전원 황인) |
| `severity` | 100% | 100% | 아토피만, 나머지 공란 |
| `lesion_type` | 100% | 100% | 여드름만, 나머지 공란 |

### 9-3. 클래스별 특이 분포

**아토피 IGA Grade (train 1,600장)**

| Grade | 장수 | 비율 |
|-------|------|------|
| Moderate | 667 | 41.7% |
| Severe | 569 | 35.6% |
| Mild | 326 | 20.4% |
| Almost Clear | 35 | 2.2% |
| Clear | 3 | 0.2% |

문서 기술(3단계)과 달리 실제 IGA 5단계 전체가 사용됨. Almost Clear(35장)·Clear(3장)는 샘플 수가 극소수라 해당 서브그룹 분석 시 통계적 신뢰도 낮음.

**여드름 병변 유형 (train 1,600장)**

| 유형 | 장수 | 비율 |
|------|------|------|
| 염증성 (True) | 969 | 60.6% |
| 비염증성 (False) | 631 | 39.4% |

### 9-4. 검증 결과 (`aihub_validate`)

| 항목 | 결과 |
|------|------|
| train.csv / val.csv 존재 | ✅ |
| 클래스 균형 | ✅ |
| 이미지 열기 (10% 샘플) | ✅ |
| label 범위 (0~5) | ✅ |
| 필수 컬럼 null | ✅ |
| test.csv | ⚠️ 없음 (AI Hub 미제공 — 정상) |

### 9-5. 참고 이미지

`data/processed/eda/` 에 6종 차트 생성됨:

| 파일 | 내용 |
|------|------|
| `class_distribution.png` | split별 클래스 분포 막대 그래프 |
| `gender_distribution.png` | 전체 및 클래스별 성별 분포 |
| `age_distribution.png` | 전체 및 클래스별 연령대 분포 |
| `atopy_severity.png` | IGA Grade 5단계 분포 |
| `acne_lesion_type.png` | 염증성/비염증성 파이 차트 |
| `sample_grid.png` | 클래스별 샘플 이미지 6×6 그리드 |

### 9-6. 학습 단계 예상 이슈 및 해결방안 (Colab 환경 기준)

---

#### ① zip_path 절대경로 불일치 — **구현 완료**

**문제**: `aihub_preprocessor`가 `zip_path`를 전처리 시점의 로컬 절대경로로 저장한다.

```
# 로컬 Mac에서 전처리 시 생성됨
/Users/kyoe/skin_ai/data/dataset_14/Training/01_raw/TS_건선_정면.zip

# Colab에서의 실제 경로 (Drive 마운트 시)
/content/drive/MyDrive/skin_ai/data/dataset_14/Training/01_raw/TS_건선_정면.zip
```

경로 불일치로 DataLoader의 `zipfile.ZipFile(zip_path)` 호출이 `FileNotFoundError`로 실패한다.

**구현 내용** (`ai/dataset/dataset.py`):

`zip_path`에서 `data/` 세그먼트를 앵커로 상대경로를 추출한 뒤 `root_dir` 아래에 재조합하는 `_remap_zip_path()`를 추가했다. `AihubFacialDataset` 초기화 시 `root_dir`을 전달하면 DataFrame 전체에 일괄 적용된다.

```python
# Colab에서 Drive 마운트 후 사용
dataset = AihubFacialDataset(
    csv_path="data/processed/train.csv",
    root_dir="/content/drive/MyDrive/skin_ai",
)

# Colab 로컬 디스크로 복사한 경우
dataset = AihubFacialDataset(
    csv_path="data/processed/train.csv",
    root_dir="/content/skin_ai",
)
```

CLI로도 전달 가능:

```bash
python -m ai.training.classifier.train \
    --root_dir /content/drive/MyDrive/skin_ai
```

---

#### ② Google Drive I/O 병목 — **해결방안**

**문제**: Drive 마운트 방식은 ZIP을 읽을 때마다 Drive FUSE 계층을 경유해 로컬 NVMe 대비 읽기 속도가 5~10배 느리다. T4 GPU의 forward 50ms에 비해 배치 로딩이 병목이 된다.

**해결**: 학습 시작 전 Colab 로컬 디스크(`/content/`)에 ZIP을 복사한다. 표준 Colab은 약 78GB 디스크를 제공하므로 전체 9.78GB ZIP과 2GB 리사이즈 ZIP을 동시에 저장 가능하다.

```python
# Colab 셀 — 학습 전 1회 실행 (약 5~10분 소요)
import shutil
shutil.copytree(
    "/content/drive/MyDrive/skin_ai/data/dataset_14",
    "/content/dataset_14",
)

# 256px 리사이즈 변환본이 있는 경우
shutil.copytree(
    "/content/drive/MyDrive/skin_ai/data/dataset_256",
    "/content/dataset_256",
)
```

이후 학습:

```bash
python -m ai.training.classifier.train \
    --root_dir /content
```

복사 후 로컬 디스크 I/O로 전환되므로 Drive 마운트 병목이 완전히 제거된다. **단, Colab 세션 종료 시 `/content/` 데이터는 삭제**되므로 매 세션마다 복사가 필요하다.

---

#### ③ Colab 세션 만료 — **현행 코드로 대응 가능**

**문제**: Colab 표준 세션은 90분 비활성 또는 최대 12시간 후 만료된다. 30에폭 전체 학습은 T4 기준 약 3~5시간이 소요될 수 있어 세션 중 만료 위험이 존재한다.

**현행 `train.py` 체크포인트 전략**:

| 저장 시점 | 파일명 | 내용 |
|----------|--------|------|
| val_top1 갱신 시 | `best.pth` | 최고 성능 모델 |
| 매 5에폭 | `epoch_N.pth` | 중간 체크포인트 |

`best.pth`는 `ai/checkpoints/aihub/` 아래 저장된다. 세션 만료 전에 Drive로 복사해두면 재개가 가능하다.

```python
# Colab 셀 — 학습 완료 후 또는 주기적으로 실행
import shutil
shutil.copy(
    "ai/checkpoints/aihub/best.pth",
    "/content/drive/MyDrive/skin_ai/ai/checkpoints/aihub/best.pth",
)
```

세션 만료 후 재개:

```bash
python -m ai.training.classifier.train \
    --root_dir /content \
    --resume ai/checkpoints/aihub/best.pth
```

`--resume` 옵션은 epoch 번호, optimizer 상태, best_val_top1, history를 모두 복원한다.

---

#### ④ 클래스당 1,600장 — 과적합 위험

**문제**: 6클래스 분류에서 클래스당 1,600장은 대규모 pretrained 모델 기준으로 적은 편이다. 특히 EfficientNet-B3(12M 파라미터)는 빠르게 과적합될 수 있다.

**현행 완화 장치**:

| 장치 | 설정값 | 위치 |
|------|--------|------|
| RandomHorizontalFlip | p=0.5 | `get_transforms` |
| ColorJitter | brightness/contrast/saturation=0.2, hue=0.1 | `get_transforms` |
| RandomRotation | ±15° | `get_transforms` |
| Dropout | 0.5 | `build_classifier` |
| Weight Decay | 1e-4 | `ClassifyConfig` |
| Early Stopping | patience=10 | `ClassifyConfig` |

train loss는 낮아지는데 val loss가 상승하기 시작하는 에폭을 기준으로 조기 종료가 작동한다(`patience=10`). 추가로 과적합이 심한 경우 `--learning_rate 0.0001` 또는 EfficientNet 하위 레이어 freeze를 검토한다.

---

#### ⑤ 단일 인종 데이터 — 일반화 한계

**문제**: 전체 10,800장이 황인 피험자로만 구성되어 있다.

**영향**: 백인·흑인 피부의 피부질환은 색조 특성이 다르므로 모델이 이를 올바르게 분류하지 못할 가능성이 높다.

**대응**: 현재로서는 데이터 한계를 모델 카드에 명시하고 임상 배포 시 대상 인종을 한정하는 것이 현실적이다. 추후 타 인종 데이터(SCIN 데이터셋 등)와 도메인 적응(Domain Adaptation)을 통해 보완할 수 있다.

---

#### ⑥ 학습 기획 과정에서 발견한 코드 이슈

학습 기획안(Part 3-A, 3-B) 작성 중 전처리 데이터와 학습 코드 사이에서 발견된 불일치:

| 이슈 | 파일 | 내용 |
|------|------|------|
| `evaluate.py`가 `test.csv` 참조 | `ai/testing/evaluate.py:134` | test split 미제공 데이터셋에서 FileNotFoundError 발생. `val.csv` fallback 또는 `--split` 인자 필요 |
| `evaluate.py` output_dir 구버전 경로 | `ai/testing/evaluate.py:110` | `scin/model/aihub_classifier/eval_results` → `ai/testing/eval_results` 로 수정 필요 |
| EfficientNet-B3 해상도 미분기 | `ai/training/classifier/config.py` | `ClassifyConfig`가 image_size=256, crop_size=224 고정. backbone별 해상도 설정 추가 필요 |
| evaluate.py, threshold_opt.py에 `root_dir` 미적용 | `ai/testing/*.py` | Colab 환경에서 평가 시에도 zip_path 경로 불일치 동일 발생 |
