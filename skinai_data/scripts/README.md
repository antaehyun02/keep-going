# 데이터셋 준비 가이드

PM과 팀원 모두 **각자 로컬에서** Drive에서 직접 다운로드합니다.
PM은 Drive 폴더에 팀원 Google 계정을 **뷰어**로 추가해주세요.

---

## 스크립트 구조

```
skinai_data/scripts/
├── build_manifest.py    # [PM 전용] Drive 폴더 재귀 탐색 → 원천 ZIP 목록 수집
│                        #   └─ manifest_zips.csv 생성 (file_id, class, split, direction)
│                        #   └─ SKINAI_DRIVE_FOLDER_ID 환경변수 필요
│
├── download_dataset.py  # [전원] manifest_zips.csv 기반 ZIP 다운로드 + 압축 해제
│                        #   └─ Drive 인증 후 file_id로 각 ZIP fetch
│                        #   └─ data/raw/{split}/ 에 압축 해제
│                        #   └─ --resume 으로 중단 재개 가능
│
└── upload_to_drive.py   # [PM 전용] 로컬 원본 데이터 → Drive 업로드
                         #   └─ 이미 완료된 경우 재실행 불필요
```

---

## 1단계: Drive 인증 (최초 1회)

```bash
python -m skinai_data.auth
```

브라우저 인증창이 열리고, 완료 시 `~/.config/skinai_data/token.json`이 저장됩니다.
이후 재인증 불필요.

---

## 2단계: ZIP 다운로드 + 압축 해제

```bash
# 정면 전체 (train + val) — 기본
python skinai_data/scripts/download_dataset.py --output-dir data/raw --resume

# 특정 split만
python skinai_data/scripts/download_dataset.py --output-dir data/raw --split train --resume

# 라벨 JSON ZIP도 포함
python skinai_data/scripts/download_dataset.py --output-dir data/raw --include-labels --resume
```

`--resume` 플래그를 붙이면 이미 다운로드된 항목은 건너뛰어 중단 후 재실행이 안전합니다.

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--split` | `train` / `val` / `test` | 전체 |
| `--direction` | `front` / `side` / `all` | `front` |
| `--include-labels` | 라벨 JSON ZIP 포함 | 미포함 |
| `--resume` | 이미 완료된 항목 건너뜀 | 비활성 |
| `--output-dir` | 압축 해제 경로 | `data/raw/` |

---

## 데이터 디렉토리 구조

```
data/
├── raw/                              # ZIP 압축 해제 원본 (gitignored)
│   ├── train/
│   │   ├── 1.원천데이터/
│   │   │   ├── 건선/
│   │   │   │   ├── 정면/             # P2_*.png  ← 학습에 사용 (정면)
│   │   │   │   └── 측면/             # P1_*.png
│   │   │   ├── 아토피피부염/
│   │   │   ├── 여드름/
│   │   │   ├── 주사/
│   │   │   ├── 지루피부염/
│   │   │   └── 정상/
│   │   └── 2.라벨링데이터/            # 동일 구조, *.json (임상 메타데이터)
│   └── val/
│       └── (동일 구조)
│
└── processed/                        # 전처리 결과 (git 추적)
    ├── train.csv
    ├── val.csv
    ├── test.csv
    └── metadata.json
```

### 이미지 수 확인

```bash
find data/raw/train -name "*.png" | wc -l
find data/raw/val   -name "*.png" | wc -l
```

정상 다운로드 시 train 약 8,400장 / val 약 2,400장 (정면 기준).

### 3단계: 전처리 (라벨 ZIP 포함 다운로드 후)

```bash
python -m ai.preprocessing.aihub_preprocessor   # data/dataset_14 → data/processed (기본값)
```

결과물이 `data/processed/train.csv`, `val.csv`, `test.csv` 로 저장됩니다.
