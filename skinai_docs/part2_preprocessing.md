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
| 아토피피부염 | `diagnosis_info.easi_score.iga_grade` | Mild / Moderate / Severe |
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

### 이슈 1 — 세그멘테이션 마스크 미제공 (Critical)

**현상**: 라벨 ZIP 24개 전체에 PNG 파일 0개. JSON의 `bbox.lesion_area` 필드에는 경로값이 기록돼 있으나 실제 파일은 존재하지 않음 (실측 확인).

**영향**: `AihubSegDataset`이 항상 `zeros(H, W)` 마스크를 반환 → 세그멘테이션 학습 완전 불가. 현재 `train_seg.py` 실행 시 모델이 배경만 예측하도록 학습됨.

**해결방안 (우선순위 순)**:

| 방법 | 비용 | 품질 |
|------|------|------|
| AI Hub 공식 마스크 재신청 | 시간 | 높음 |
| Meta SAM (Segment Anything) 자동 생성 | 중간 | 중간 |
| LabelMe 수동 어노테이션 | 노력 큼 | 높음 |

---

### 이슈 2 — ZIP 반복 개방 I/O 병목 (Performance)

**현상**: `__getitem__` 호출마다 `zipfile.ZipFile()` 을 열고 닫음. 이미지 1장 평균 로딩 **13.2ms** (실측).

**영향**: `num_workers=4` 기준 배치(32장) 로딩 **106ms** vs DenseNet121 GPU forward **~50ms** → 데이터 로딩이 학습 병목.

**해결방안 (단계별)**:

1. **즉시 적용** — `num_workers` 증가 (4 → 8)
   - 별도 코드 수정 없이 DataLoader 인자만 변경
   - 병렬 로딩으로 GPU 대기 시간 단축

2. **단기** — `worker_init_fn`으로 워커별 ZIP 핸들 캐싱
   - 각 워커 프로세스 시작 시 ZIP을 열어 전역 dict에 보관
   - `__getitem__`은 캐시에서 핸들을 재사용 → 반복 개방 제거
   - multiprocessing에서 안전 (워커별 독립 프로세스)

3. **장기** — 256px JPEG 사전 리사이즈 ZIP 생성
   - 원본 9.78GB → 256px JPEG 변환 시 약 2GB 추가
   - 로딩 속도 3~5배 향상 예상 (디스크 vs 속도 트레이드오프)

---

### 이슈 3 — 1,024px 원본 전체 로드 (Performance)

**현상**: `transform`의 `Resize(256)` 실행 전에 1,024×1,024 전체 이미지를 메모리에 적재. 장당 950KB를 올린 후 즉시 축소.

**영향**: 배치 32장 기준 약 30MB를 CPU 메모리에 순간 점유 후 해제. 대규모 배치나 메모리가 제한된 환경에서 OOM 위험.

**해결방안**: 이슈 2의 장기 해결방안(사전 리사이즈 ZIP 생성)으로 함께 해결.

---

## 8. 실행 명령 요약

```bash
# 전처리 실행 (data/dataset_14 → data/processed)
python -m ai.preprocessing.aihub_preprocessor

# 결과 검증 (CSV 무결성, 클래스 균형)
python -m ai.preprocessing.aihub_validate --processed_dir data/processed

# EDA 시각화 (data/processed/eda/*.png)
python -m ai.preprocessing.aihub_eda --processed_dir data/processed
```
