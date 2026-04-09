# Part 5 — VSCode Colab 확장 프로그램으로 학습 실행하기

SSH 원격연결 없이 VSCode에 설치된 **Google Colab 확장 프로그램**을 통해 Colab GPU 런타임에서 학습을 실행하는 방법.

> 기존 SSH 방식은 [part4_colab_vscode_setup.md](part4_colab_vscode_setup.md) 참고.

---

## 0. 사전 준비

VSCode 확장 탭에서 **"Colab"** (google.colab) 검색 후 설치.

Colab 노트북 열기 → 상단 메뉴 **런타임 > 런타임 유형 변경** → **GPU (T4 이상)** 선택.

---

## 1. 파일 역할 분담

| 파일 | 관리 위치 | 이유 |
|------|-----------|------|
| 소스코드 (`ai/`, 등) | **GitHub** | git clone으로 바로 사용 |
| 전처리 CSV (`data/processed/`) | **GitHub** | 용량 작음, 버전 관리 가능 |
| 이미지 ZIP (`data/dataset_14/`) | **Google Drive** | ~10GB — GitHub 업로드 불가 |
| 체크포인트 (`ai/checkpoints/`) | **Google Drive** | 런타임 종료 시 소실 방지 |

> **Drive에 올릴 것은 이미지 ZIP 파일만.** 소스코드와 CSV는 Drive 업로드 불필요.

---

## 2. Drive 구조

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

## 3. Colab 노트북 구성

VSCode에서 노트북 파일을 열고 아래 셀을 순서대로 실행한다.

### 셀 1 — Drive 마운트

이미지 ZIP 파일에 접근하기 위해 Drive를 마운트한다.

```python
from google.colab import drive
drive.mount('/content/drive')
```

### 셀 2 — 소스코드 clone

소스코드와 전처리 CSV를 GitHub에서 가져온다.

```python
!git clone https://github.com/<username>/skin_ai.git /content/skin_ai
```

### 셀 3 — 환경 설정

```python
import os
os.chdir('/content/skin_ai')  # 프로젝트 루트로 이동 — 필수

# Drive의 이미지 ZIP을 data/dataset_14/ 로 심링크
# data/processed/ (CSV)는 git clone으로 이미 존재하므로 덮어쓰지 않음
!mkdir -p data
!ln -sfn /content/drive/MyDrive/skin_ai/data/dataset_14 data/dataset_14

# 심링크 확인
!ls data/dataset_14/
```

### 셀 4 — 패키지 설치

```python
!pip install -q \
    torch torchvision \
    pandas pillow tqdm \
    matplotlib python-dotenv

# EfficientNet-B3 사용 시 추가
!pip install -q timm
```

### 셀 5 — 학습 실행

GitHub에서 받은 CSV의 `zip_path`는 로컬 절대경로(`/Users/kyoe/skin_ai/data/...`)로 기록되어 있으므로  
`--root_dir`로 Colab 경로에 맞게 재매핑한다.

```python
# DenseNet121 (기본)
!python -m ai.training.classifier.train \
    --backbone densenet121 \
    --num_epochs 30 \
    --root_dir /content/skin_ai

# EfficientNet-B3
# !python -m ai.training.classifier.train \
#     --backbone efficientnet_b3 \
#     --num_epochs 30 \
#     --root_dir /content/skin_ai
```

### 셀 6 — 체크포인트 Drive 저장

런타임 종료 전 실행. 저장하지 않으면 학습 결과가 소실된다.

```python
import shutil

shutil.copytree(
    'ai/checkpoints/aihub',
    '/content/drive/MyDrive/skin_ai/ai/checkpoints/aihub',
    dirs_exist_ok=True,
)
print("체크포인트 Drive 저장 완료")
```

---

## 4. 런타임 재시작 후 학습 재개

런타임이 끊기면 셀 1~4를 재실행한 뒤:

```python
# Drive에서 체크포인트 복원
!mkdir -p ai/checkpoints
!cp -r /content/drive/MyDrive/skin_ai/ai/checkpoints/aihub \
        ai/checkpoints/

# best.pth 에서 재개
!python -m ai.training.classifier.train \
    --resume ai/checkpoints/aihub/best.pth \
    --root_dir /content/skin_ai
```

---

## 5. GPU 확인

```python
import torch

print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

---

## 6. 트러블슈팅

| 상황 | 해결 방법 |
|------|-----------|
| `FileNotFoundError: dataset_14/...` | 셀 3 심링크 확인: `!ls -la data/` |
| CUDA 메모리 부족 | `--batch_size 16` (DenseNet) / `--batch_size 8` (EfficientNet) |
| `num_workers` 오류 | 셀에서 `os.environ['NUM_WORKERS'] = '2'` 후 재실행 |
| 체크포인트 없음 | 셀 4의 재개 절차로 Drive에서 복원 |

---

## 7. 세션 재개 체크리스트

| 순서 | 작업 |
|------|------|
| 1 | 셀 1 — Drive 마운트 |
| 2 | 셀 2 — GitHub clone |
| 3 | 셀 3 — `os.chdir` + `dataset_14/` 심링크 |
| 4 | 셀 4 — pip install |
| 5 | Drive 체크포인트 복원 후 `--resume` 으로 재개 |

---

## 참고

- `--root_dir` 동작 원리: [ai/dataset/dataset.py:138](../ai/dataset/dataset.py) — CSV `zip_path`의 `data` 세그먼트를 찾아 `root_dir` 아래로 재조합
- 학습 파라미터 전체 목록: [ai/training/classifier/config.py](../ai/training/classifier/config.py)
- 기존 SSH 원격 연결 방식: [part4_colab_vscode_setup.md](part4_colab_vscode_setup.md)
