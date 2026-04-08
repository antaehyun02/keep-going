# Part 5 — VSCode Colab 확장 프로그램으로 학습 실행하기

SSH 원격연결 없이 VSCode에 설치된 **Google Colab 확장 프로그램**을 통해 Colab GPU 런타임에서 학습을 실행하는 방법.

> 기존 SSH 방식은 [part4_colab_vscode_setup.md](part4_colab_vscode_setup.md) 참고.

---

## 0. 사전 준비

### VSCode Colab 확장 프로그램 설치

VSCode 확장 탭에서 **"Colab"** (google.colab) 검색 후 설치.

### Colab 런타임 유형 설정

Colab 노트북 열기 → 상단 메뉴 **런타임 > 런타임 유형 변경** → **GPU (T4 이상)** 선택.

---

## 1. Google Drive 데이터 구조

Drive에 아래 구조로 데이터셋을 업로드한다.

```
MyDrive/
└── skin_ai/
    └── data/
        └── dataset_14/
            ├── Training/
            │   ├── 01_raw/     ← TS_건선_정면.zip, TS_아토피피부염_정면.zip, …
            │   └── 02_label/   ← TL_건선_정면.zip, … (JSON 메타데이터)
            └── Validation/
                ├── 01_raw/     ← VS_*.zip
                └── 02_label/   ← VL_*.zip
```

> 전처리 결과(`data/processed/`)는 Colab에서 생성하므로 업로드 불필요.

---

## 2. 소스코드 준비

### 방법 A: GitHub clone (권장)

로컬에서 소스코드를 push해 놓으면 Colab 셀에서 바로 clone할 수 있다.

```bash
# 로컬 터미널
git push origin main
```

### 방법 B: zip 압축 후 Drive 업로드

```bash
# 로컬 터미널 — 데이터/환경 파일 제외
zip -r skin_ai_src.zip . \
  --exclude "data/*" \
  --exclude ".env" \
  --exclude "ai/checkpoints/*" \
  --exclude ".venv/*" \
  --exclude "__pycache__/*" \
  --exclude "*.pyc"
```

압축 파일을 Drive `MyDrive/skin_ai/` 에 업로드.

---

## 3. Colab 노트북 구성

VSCode에서 `test.ipynb` (또는 새 노트북)을 열고 아래 셀을 순서대로 실행한다.

### 셀 1 — Drive 마운트

```python
from google.colab import drive
drive.mount('/content/drive')
```

### 셀 2 — 소스코드 준비

```python
# 방법 A: GitHub clone
!git clone https://github.com/<username>/skin_ai.git /content/skin_ai

# 방법 B: Drive에서 압축 해제 (방법 A 사용 시 이 셀 건너뜀)
# !unzip /content/drive/MyDrive/skin_ai/skin_ai_src.zip -d /content/skin_ai
```

### 셀 3 — 환경 설정

```python
import os
os.chdir('/content/skin_ai')  # 프로젝트 루트로 이동 — 필수

# Drive의 data/ 를 프로젝트 루트에서 접근 가능하게 심링크
!ln -sfn /content/drive/MyDrive/skin_ai/data data

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

### 셀 5A — 전처리 실행 (권장)

로컬에서 이미 전처리한 CSV가 없거나, 경로 문제를 피하고 싶을 때 사용.

```python
# Colab 절대경로 기준으로 train.csv / val.csv 새로 생성
# 완료 후 zip_path 가 /content/skin_ai/data/... 로 기록됨
!python -m ai.preprocessing.aihub_preprocessor \
    --data_root data/dataset_14 \
    --output_dir data/processed
```

> 소요 시간: 약 5~10분 (ZIP 파일 스캔 + JSON 메타 추출)

### 셀 5B — 로컬 CSV 재사용 (선택)

로컬에서 전처리한 CSV를 Drive에 올려 두고 쓰는 경우. 셀 5A 대신 사용.

```python
# 로컬에서 만든 CSV 를 Drive 에 올려 뒀을 때
!mkdir -p data/processed
!cp /content/drive/MyDrive/skin_ai/data/processed/train.csv data/processed/
!cp /content/drive/MyDrive/skin_ai/data/processed/val.csv   data/processed/

# 경로 재매핑 확인 (--root_dir 이 'data' 세그먼트 기준으로 자동 교체)
import pandas as pd
df = pd.read_csv('data/processed/train.csv')
print("원본 zip_path 예시:", df['zip_path'].iloc[0])
# 학습 시 --root_dir /content/skin_ai 지정하면 경로 자동 교체됨
```

### 셀 6 — 학습 실행

```python
# 셀 5A 실행한 경우 (전처리 재실행) — root_dir 불필요
!python -m ai.training.classifier.train \
    --backbone densenet121 \
    --num_epochs 30

# 셀 5B 실행한 경우 (로컬 CSV 재사용) — root_dir 지정
# !python -m ai.training.classifier.train \
#     --backbone densenet121 \
#     --num_epochs 30 \
#     --root_dir /content/skin_ai

# EfficientNet-B3 로 실행 시
# !python -m ai.training.classifier.train \
#     --backbone efficientnet_b3 \
#     --num_epochs 30
```

### 셀 7 — 체크포인트 Drive 저장

런타임 종료 전 반드시 실행.

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
# Drive 체크포인트를 로컬로 복사
!cp -r /content/drive/MyDrive/skin_ai/ai/checkpoints \
        /content/skin_ai/ai/

# best.pth 에서 재개
!python -m ai.training.classifier.train \
    --resume ai/checkpoints/aihub/best.pth
```

> 전처리를 재실행한 경우 셀 5A도 다시 실행 (CSV 경로 재생성).

---

## 5. GPU 확인 및 환경 점검

```python
import torch

print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

```bash
# 디스크 여유 공간 확인 (Colab 무료 약 70GB)
!df -h /content
```

---

## 6. 주요 설정 조정

| 상황 | 해결 방법 |
|------|-----------|
| CUDA 메모리 부족 | `--batch_size 16` (DenseNet) / `--batch_size 8` (EfficientNet) |
| `num_workers` 오류 | 셀에서 `os.environ['NUM_WORKERS'] = '2'` 설정 후 재실행 |
| 전처리 경로 오류 | `data/dataset_14/` 심링크 확인: `!ls -la data/` |
| 체크포인트 없음 | Drive에서 복사: 셀 4의 재개 절차 참고 |

---

## 7. 세션 재개 체크리스트

| 순서 | 작업 |
|------|------|
| 1 | 셀 1 — Drive 마운트 |
| 2 | 셀 2 — 소스코드 clone / unzip |
| 3 | 셀 3 — `os.chdir` + `data/` 심링크 |
| 4 | 셀 4 — pip install |
| 5 | Drive 체크포인트 복사 |
| 6 | 셀 5A (전처리 재실행 필요 시) |
| 7 | `--resume best.pth` 로 학습 재개 |

---

## 참고

- `_remap_zip_path()` 동작: [ai/dataset/dataset.py:138](../ai/dataset/dataset.py) — CSV의 `zip_path`에서 `data` 세그먼트를 찾아 `root_dir` 아래로 재조합
- 학습 파라미터 전체 목록: [ai/training/classifier/config.py](../ai/training/classifier/config.py)
- 기존 SSH 원격 연결 방식: [part4_colab_vscode_setup.md](part4_colab_vscode_setup.md)
