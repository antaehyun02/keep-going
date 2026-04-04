# 데이터셋 준비 가이드

PM이 Drive에 업로드한 AI Hub ZIP 파일을 팀원 각자 로컬에 다운로드합니다.
PM은 Drive 폴더에 팀원 Google 계정을 **뷰어**로 추가해주세요.

---

## 스크립트 구조

```
skinai_data/scripts/
├── build_manifest.py    # [PM 전용] Drive 폴더 탐색 → manifest_zips.csv 생성
│                        #   └─ SKINAI_DRIVE_FOLDER_ID 환경변수 필요
│                        #   └─ 출력: skinai_data/scripts/manifest_zips.csv
│
├── download_dataset.py  # [전원] manifest_zips.csv 기반 ZIP 다운로드
│                        #   └─ --save-zip : ZIP을 data/dataset_14/ 구조로 저장 (권장)
│                        #   └─ 기본값    : ZIP 압축 해제 → data/raw/ 아래 PNG
│                        #   └─ --resume 으로 중단 재개 가능
│
├── upload_to_drive.py   # [PM 전용] 로컬 원본 데이터 → Drive 업로드
│                        #   └─ 최초 1회만 실행 (이미 완료된 경우 불필요)
│
└── manifest_zips.csv    # build_manifest.py 실행 후 생성 (git 추적)
```

---

## 1단계: Drive 인증 (최초 1회)

```bash
python -m skinai_data.auth
```

브라우저 인증창이 열리고, 완료 시 `~/.config/skinai_data/token.json`이 저장됩니다.
이후 재인증 불필요. 토큰 초기화: `rm ~/.config/skinai_data/token.json`

---

## 2단계: ZIP 다운로드

두 가지 저장 방식 중 선택합니다.

### 방법 A — ZIP 직접 저장 (권장: 전처리기 바로 사용 가능)

```bash
# 정면 원천 + 라벨 ZIP 저장 (전처리기용)
python skinai_data/scripts/download_dataset.py --save-zip --include-labels --resume

# 측면 원천 + 라벨 ZIP 저장
python skinai_data/scripts/download_dataset.py --save-zip --direction side --include-labels --resume

# 정면 + 측면 전체 (원천 + 라벨)
python skinai_data/scripts/download_dataset.py --save-zip --direction all --include-labels --resume

# 정면만 (라벨 없이)
python skinai_data/scripts/download_dataset.py --save-zip --resume
```

저장 위치:
```
data/dataset_14/
├── Training/
│   ├── 01_raw/    # TS_{클래스}_{방향}.zip
│   └── 02_label/  # TL_{클래스}_{방향}.zip
└── Validation/
    ├── 01_raw/    # VS_{클래스}_{방향}.zip
    └── 02_label/  # VL_{클래스}_{방향}.zip
```

→ 이 구조로 저장하면 `aihub_preprocessor`가 **바로** 사용 가능합니다.

### 방법 B — 압축 해제 (PNG로 저장)

```bash
# 정면 전체 (train + val)
python skinai_data/scripts/download_dataset.py --resume

# 측면 전체
python skinai_data/scripts/download_dataset.py --direction side --resume

# 정면 + 측면 전체
python skinai_data/scripts/download_dataset.py --direction all --resume

# 특정 split만
python skinai_data/scripts/download_dataset.py --split train --resume

# 라벨(JSON) ZIP도 포함
python skinai_data/scripts/download_dataset.py --include-labels --resume
```

저장 위치: `data/raw/{split}/` 아래 PNG 파일로 압축 해제

> ⚠️ 방법 B는 현재 `aihub_preprocessor`와 호환되지 않습니다 (preprocessor는 ZIP 직접 로드 방식).
> 향후 파일 시스템 기반 전처리기 구현 시 사용 예정.

---

### 공통 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--save-zip` | ZIP 파일을 data/dataset_14/ 구조로 저장 | 미지정 시 압축 해제 |
| `--split` | `train` / `val` / `test` | 전체 |
| `--direction` | `front` / `side` / `all` | `front` |
| `--include-labels` | 라벨 JSON ZIP 포함 | 미포함 |
| `--resume` | 이미 존재하는 파일 건너뜀 | 비활성 |
| `--output-dir` | 압축 해제 경로 (방법 B만 해당) | `data/raw/` |

---

## 3단계: 전처리 (방법 A 이후)

```bash
python -m ai.preprocessing.aihub_preprocessor
# data/dataset_14 → data/processed (기본값)
```

결과물: `data/processed/train.csv`, `val.csv`, `metadata.json`

---

## 이미지 수 확인

```bash
# 방법 A — ZIP 파일 수 확인
ls data/dataset_14/Training/01_raw/*.zip | wc -l    # 12개 정상

# 방법 B — 압축 해제된 PNG 수 확인
find data/raw/train -name "*.png" | wc -l    # 약 9,600장 (정면 기준)
find data/raw/val   -name "*.png" | wc -l    # 약 1,200장
```
