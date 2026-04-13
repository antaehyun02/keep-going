# Part 5 — VSCode Colab 확장 프로그램으로 학습 실행하기

SSH 원격연결 없이 VSCode에 설치된 **Google Colab 확장 프로그램**을 통해 Colab GPU 런타임에서 학습을 실행하는 방법.

> 기존 SSH 방식은 [part4_colab_vscode_setup.md](part4_colab_vscode_setup.md) 참고.

---

## 0. 사전 준비

VSCode 확장 탭에서 **"Colab"** (google.colab) 검색 후 설치.

Colab 노트북 열기 → 상단 메뉴 **런타임 > 런타임 유형 변경** → **GPU (T4 이상)** 선택.

---

## 1. 경로 구조 개요

| 환경 | 프로젝트 루트 | 데이터 위치 |
|------|-------------|-----------|
| **로컬** | `/Users/kyoe/skin_ai` (실제 레포) | `data/dataset_14/` (상대경로) |
| **Colab 런타임** | `/content/colab_skin_ai` (임시 복사본) | `/content/drive/MyDrive/skin_ai/data/dataset_14` 심링크 |

> Colab 런타임의 `/content/`는 **세션 종료 시 전부 소실**된다.  
> 소스코드와 체크포인트는 각각 GitHub / Google Drive로 영속 보관한다.

---

## 2. 파일 역할 분담

| 파일 | 보관 위치 | 이유 |
|------|-----------|------|
| 소스코드 (`ai/`, 등) | **GitHub** | git clone으로 Colab 런타임에 내려받음 |
| 전처리 CSV (`data/processed/`) | **GitHub** | 용량 작음, 버전 관리 가능 |
| 이미지 ZIP (`data/dataset_14/`) | **Google Drive** | ~10GB — GitHub 업로드 불가 |
| 체크포인트 (`ai/checkpoints/`) | **Google Drive** | 런타임 종료 시 소실 방지 |

> **Drive에 올릴 것은 이미지 ZIP 파일만.** 소스코드와 CSV는 Drive 업로드 불필요.

---

## 3. Google Drive 구조

Drive에 이미지 ZIP 파일(`01_raw/`)만 업로드한다.  
라벨 ZIP(`02_label/`)은 전처리 재실행이 필요한 경우가 아니면 불필요.

```
MyDrive/
└── skin_ai/
    └── data/
        └── dataset_14/
            ├── Training/
            │   └── 01_raw/     ← TS_건선_정면.zip, TS_아토피피부염_정면.zip, …
            └── Validation/
                └── 01_raw/     ← VS_건선_정면.zip, VS_아토피피부염_정면.zip, …
```

---

## 4. Colab 노트북 구성

프로젝트 루트의 `train.ipynb`를 사용한다.  
노트북은 **Colab / 로컬 환경을 자동 감지**하므로 경로를 직접 수정할 필요 없다.

### 셀 1 — 환경 감지

실행 환경을 판별하고 경로 변수를 설정한다.

```python
import os
from pathlib import Path

try:
    import google.colab
    IS_COLAB = True
    # Colab 런타임 임시 경로 (세션 종료 시 소실)
    COLAB_ROOT = "/content/colab_skin_ai"
    PROJECT_ROOT = COLAB_ROOT
except ImportError:
    IS_COLAB = False
    # 로컬: 노트북이 위치한 레포 루트 그대로 사용
    LOCAL_ROOT = str(Path.cwd())
    PROJECT_ROOT = LOCAL_ROOT

print(f"환경       : {'Google Colab' if IS_COLAB else '로컬'}")
print(f"PROJECT_ROOT: {PROJECT_ROOT}")
```

### 셀 2 — Drive 마운트 (Colab 전용)

```python
if IS_COLAB:
    from google.colab import drive
    drive.mount('/content/drive')
    # Drive 마운트 경로 (Colab 런타임 전용)
    DRIVE_ROOT = "/content/drive/MyDrive/skin_ai"
else:
    print("로컬 환경 — Drive 마운트 건너뜀")
```

### 셀 3 — 소스코드 clone (Colab 전용)

**공개 레포:**
```python
if IS_COLAB:
    if not Path(COLAB_ROOT).exists():
        !git clone https://github.com/<username>/skin_ai.git {COLAB_ROOT}
    else:
        print(f"이미 존재 — 클론 건너뜀: {COLAB_ROOT}")
else:
    print("로컬 환경 — 클론 건너뜀")
```

**비공개 레포 (GitHub PAT 필요):**
```python
if IS_COLAB:
    if not Path(COLAB_ROOT).exists():
        # Colab Secrets에 GITHUB_TOKEN 등록 권장
        # (좌측 패널 자물쇠 아이콘 → GITHUB_TOKEN 추가)
        from google.colab import userdata
        GITHUB_TOKEN = userdata.get("GITHUB_TOKEN")
        GITHUB_USER = "<username>"
        !git clone https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/skin_ai.git {COLAB_ROOT}
    else:
        print(f"이미 존재 — 클론 건너뜀: {COLAB_ROOT}")
else:
    print("로컬 환경 — 클론 건너뜀")
```

> PAT 발급: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → `Contents: Read` 권한으로 생성

### 셀 4 — 프로젝트 루트 이동 + 데이터 경로 설정

```python
os.chdir(PROJECT_ROOT)
print(f"현재 디렉토리: {os.getcwd()}")

if IS_COLAB:
    # Colab 런타임: Drive에 있는 dataset_14를 심링크로 연결
    os.makedirs("data", exist_ok=True)
    DRIVE_DATASET = f"{DRIVE_ROOT}/data/dataset_14"
    if Path(DRIVE_DATASET).exists():
        !ln -sfn {DRIVE_DATASET} data/dataset_14
        print("data/dataset_14 심링크 생성 완료")
    else:
        print(f"경고: Drive 데이터셋 없음 — {DRIVE_DATASET}")
else:
    # 로컬: data/dataset_14 존재 여부만 확인
    if not Path("data/dataset_14").exists():
        print("경고: data/dataset_14/ 없음 — AI Hub 데이터를 먼저 배치하세요")
    else:
        print("data/dataset_14/ 확인 완료")

!ls data/
```

### 셀 5 — 패키지 설치

```python
!pip install -q \
    torch torchvision \
    pandas pillow tqdm \
    numpy matplotlib python-dotenv scikit-learn

# Grad-CAM (추론 서버 사용 시)
# !pip install -q pytorch-grad-cam
```

### 셀 6 — 학습 실행

GitHub에서 받은 CSV의 `zip_path`는 로컬 절대경로(`/Users/kyoe/skin_ai/data/...`)로 기록되어 있다.  
`--root_dir {PROJECT_ROOT}` 인자가 이를 실행 환경 경로로 자동 재매핑한다.

```python
# DenseNet121 (기본)
!python -m ai.training.classifier.train \
    --backbone densenet121 \
    --num_epochs 30 \
    --root_dir {PROJECT_ROOT}

# EfficientNet-B3 (비교)
# !python -m ai.training.classifier.train \
#     --backbone efficientnet_b3 \
#     --num_epochs 30 \
#     --root_dir {PROJECT_ROOT}
```

### 셀 7 — 평가 + Threshold 최적화

```python
# 평가
!python -m ai.testing.evaluate \
    --checkpoint ai/checkpoints/aihub/best.pth \
    --root_dir {PROJECT_ROOT}

# Threshold 최적화
!python -m ai.testing.threshold_opt \
    --checkpoint ai/checkpoints/aihub/best.pth \
    --root_dir {PROJECT_ROOT}
```

### 셀 8 — 체크포인트 Drive 저장 (Colab 전용)

런타임 종료 전 반드시 실행. 저장하지 않으면 학습 결과가 소실된다.

```python
if IS_COLAB:
    import shutil
    CKPT_SRC = f"{COLAB_ROOT}/ai/checkpoints/aihub"
    CKPT_DST = f"{DRIVE_ROOT}/ai/checkpoints/aihub"
    shutil.copytree(CKPT_SRC, CKPT_DST, dirs_exist_ok=True)
    print(f"체크포인트 저장 완료: {CKPT_DST}")
else:
    print("로컬 환경 — 체크포인트 이미 로컬에 저장됨")
```

---

## 5. 런타임 재시작 후 학습 재개

런타임이 끊기면 셀 1~5를 재실행한 뒤:

```python
# Drive에서 체크포인트를 Colab 런타임으로 복원
CKPT_DRIVE = f"{DRIVE_ROOT}/ai/checkpoints/aihub"
!mkdir -p ai/checkpoints
!cp -r {CKPT_DRIVE} ai/checkpoints/

# best.pth 에서 재개 (backbone은 저장 당시와 동일하게 명시)
!python -m ai.training.classifier.train \
    --backbone densenet121 \
    --resume ai/checkpoints/aihub/best.pth \
    --root_dir {PROJECT_ROOT}
```

---

## 6. GPU 확인

```python
import torch

print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

---

## 7. 트러블슈팅

| 상황 | 원인 | 해결 방법 |
|------|------|-----------|
| `FileNotFoundError: /content/colab_skin_ai` | 셀 1이 실행되지 않음 | 셀 1부터 순서대로 재실행 |
| `fatal: could not read Username` (git clone) | private repo 인증 없음 | 셀 3의 비공개 레포 방식 (PAT 토큰) 사용 |
| `FileNotFoundError: dataset_14/...` | 심링크 미생성 | 셀 4 재실행: `!ls -la data/` 로 확인 |
| CUDA 메모리 부족 | 배치 크기 과다 | `--batch_size 16` (DenseNet) / `--batch_size 8` (EfficientNet) |
| `num_workers` 오류 | 워커 수 과다 | `os.environ['NUM_WORKERS'] = '2'` 후 재실행 |
| 체크포인트 없음 | 런타임 재시작으로 소실 | 섹션 5의 재개 절차로 Drive에서 복원 |
| 로컬 `data/dataset_14` 없음 | AI Hub 데이터 미배치 | AI Hub ZIP을 `data/dataset_14/` 하위에 배치 |

---

## 8. 세션 재개 체크리스트

| 순서 | 셀 | 작업 |
|------|----|------|
| 1 | 셀 1 | 환경 감지 — `IS_COLAB`, `PROJECT_ROOT` 확인 |
| 2 | 셀 2 | Drive 마운트 (Colab만) |
| 3 | 셀 3 | GitHub clone (Colab만, 이미 있으면 건너뜀) |
| 4 | 셀 4 | `os.chdir` + `dataset_14/` 심링크 확인 |
| 5 | 셀 5 | pip install |
| 6 | — | Drive 체크포인트 복원 후 `--resume` 으로 재개 |

---

## 참고

- `--root_dir` 동작 원리: [ai/dataset/dataset.py](../ai/dataset/dataset.py) — CSV `zip_path`의 `data` 세그먼트를 찾아 `root_dir` 아래로 재조합
- 학습 파라미터 전체 목록 및 환경변수: [ai/training/classifier/config.py](../ai/training/classifier/config.py)
- 기존 SSH 원격 연결 방식: [part4_colab_vscode_setup.md](part4_colab_vscode_setup.md)
