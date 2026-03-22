# Part 2: 데이터 전처리 파이프라인 기획안

## 개요

AI Hub 08-14 합성 피부 데이터셋 원시 파일을 학습/검증/테스트 CSV로 변환하는 전처리 파이프라인.

전처리 결과는 Part 3 학습 코드의 입력으로 사용됩니다.

---

## 목표

- 안면 정면(front) 이미지만 필터링
- 손상/불량 이미지 자동 탐지 및 제거
- JSON 메타데이터에서 임상 정보 추출
- 클래스 균형을 고려한 train/val/test 분할
- EDA를 통한 데이터 품질 시각적 확인

---

## 파이프라인 구조

```
scin/data/
├── aihub_preprocessor.py  # 7단계 전처리 파이프라인
├── aihub_validate.py       # 6단계 유효성 검증
└── aihub_eda.py            # EDA 시각화
```

---

## 전처리 단계 (aihub_preprocessor.py)

`AIHubPreprocessor.run()` 이 7단계를 순서대로 실행합니다.

### 1단계: load_manifest

`skinai_data.load_manifest()` 를 통해 Drive manifest.csv 로드.

필수 컬럼 존재 여부 확인:
```
file_id, filename, storage_path, class_name, class_idx,
split, direction, gender, age_range, race, severity, lesion_type
```

### 2단계: filter_front

정면 이미지만 남기는 이중 필터:
1. `direction == 'front'` 컬럼 필터
2. 파일명 패턴 검증: `P2_` 포함 여부 (AI Hub 촬영 방향 코드)

```python
df = df[df["direction"] == "front"]
df = df[df["filename"].str.contains("P2_", na=False)]
```

### 3단계: validate_images

PIL로 이미지 열기 시도 → 실패 시 손상 파일로 기록:
- 최소 해상도: 100×100px 미만 제거
- 손상 파일 목록: `processed_aihub/corrupt_files.txt`
- Drive에서 직접 스트리밍 검증 (전체 다운로드 불필요)

### 4단계: parse_json_meta

AI Hub JSON 라벨 파일에서 임상 메타데이터 추출:

| 필드 | 설명 |
|------|------|
| `gender` | 성별 (남성/여성) |
| `age_range` | 연령대 (10대, 20대, ...) |
| `race` | 인종 |
| `severity` | 중증도 (아토피: 경증/중증/중증도) |
| `lesion_type` | 병변 유형 (여드름: 면포성/구진성/낭포성) |

### 5단계: encode_labels

`class_name` → `class_idx` (0~5) 매핑 확인 및 보정.

```python
CLASS_MAP = {
    "건선": 0, "아토피피부염": 1, "여드름": 2,
    "주사": 3, "지루피부염": 4, "정상": 5,
}
```

### 6단계: split_dataset

Stratified Split (클래스 비율 유지):
- Train: 70%
- Val: 15%
- Test: 15%

`sklearn.model_selection.train_test_split` 사용, `stratify=class_idx`.

### 7단계: save_csv

출력:
```
processed_aihub/
├── train.csv
├── val.csv
├── test.csv
├── metadata.json    # 건수, 클래스별 분포, 분할 비율
└── corrupt_files.txt
```

---

## 유효성 검증 (aihub_validate.py)

전처리 완료 후 실행하여 CSV 품질 보증.

### 6단계 검증

| 단계 | 검증 내용 |
|------|-----------|
| 1 | train/val/test CSV 파일 존재 여부 |
| 2 | 클래스 균형 비율 (최대 클래스 / 최소 클래스 ≤ 3.0) |
| 3 | 이미지 10% 무작위 샘플 PIL.open() 가능 여부 |
| 4 | class_idx 범위 0~5 |
| 5 | 필수 컬럼 null 없음 |
| 6 | train/val/test 중복 file_id 없음 |

결과: `processed_aihub/validation_report.json`

---

## EDA 시각화 (aihub_eda.py)

학습 데이터의 분포를 시각적으로 확인하기 위한 6개 플롯 생성.

| 플롯 | 내용 |
|------|------|
| class_distribution.png | 클래스별 이미지 수 막대 그래프 |
| gender_distribution.png | 성별 분포 |
| age_distribution.png | 연령대 분포 |
| atopy_severity.png | 아토피 중증도 분포 |
| acne_lesion_type.png | 여드름 병변 유형 분포 |
| sample_grid.png | 클래스별 샘플 이미지 그리드 |

한국어 폰트 자동 감지:
- macOS: AppleGothic
- Linux: NanumGothic (설치 필요)

출력: `processed_aihub/eda/`

---

## 실행 순서

```bash
# 1. 전처리
python -m scin.data.aihub_preprocessor

# 2. 검증
python -m scin.data.aihub_validate

# 3. EDA
python -m scin.data.aihub_eda
```

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `MANIFEST_FILE_ID` | — | Drive manifest.csv ID (필수) |
| `SKINAI_DATA_DIR` | `scin/data/processed_aihub` | 출력 디렉토리 |

---

## 주요 설계 결정

- **정면 이중 필터**: direction 컬럼 단독으로는 데이터 오염 가능성 → 파일명 패턴 보조 검증
- **Drive 스트리밍 검증**: 이미지 손상 검사를 위해 전체 다운로드 없이 PIL seek 활용
- **Stratified Split**: 클래스 불균형 데이터셋에서 분할 후 비율 왜곡 방지
