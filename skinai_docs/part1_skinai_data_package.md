# Part 1: skinai-data 패키지 기획안

## 개요

Google Drive에 업로드된 AI Hub 08-14 합성 데이터셋을 PyTorch Dataset 형태로 스트리밍 로드하는 pip 설치 가능 패키지.

`scripts/build_manifest.py` 로 생성된 `manifest_zips.csv` 를 로컬에서 읽고, ZIP 내 이미지를 Drive에서 스트리밍 로드합니다.

---

## 목표

- Drive ZIP 파일 내 이미지를 스트리밍으로 로드
- 로컬 캐시를 통한 중복 다운로드 방지
- `torch.utils.data.DataLoader` 와 바로 연결되는 표준 Dataset 인터페이스
- 서버 환경(Service Account)과 개발 환경(OAuth2 브라우저) 모두 지원

---

## 패키지 구조

```
skinai_data/
├── __init__.py       # 공개 API export
├── __main__.py       # python -m skinai_data 진입점
├── auth.py           # Google Drive 인증
├── manifest.py       # manifest_zips.csv 로드
├── dataset.py        # SkinAIDataset (PyTorch Dataset)
└── loader.py         # get_dataloader(), prefetch()

scripts/
└── build_manifest.py # Drive 탐색 → manifest_zips.csv 생성
```

---

## 구성 요소 상세

### auth.py — Google Drive 인증

| 환경 | 인증 방식 |
|------|-----------|
| 서버 (학습 서버, headless) | `GOOGLE_APPLICATION_CREDENTIALS` Service Account JSON |
| 로컬 개발 | OAuth2 브라우저 플로우, 토큰 `~/.config/skinai_data/token.json` 캐싱 |

인증 파일 없으면 단계별 안내 출력:
```
[1/3] Google Cloud Console에서 OAuth2 자격증명을 생성하세요.
[2/3] credentials.json을 ~/.config/skinai_data/ 에 저장하세요.
[3/3] 브라우저 인증창이 열립니다...
```

```python
def get_drive_service():
    """Drive API Resource 반환 (서버/로컬 자동 분기)."""
```

---

### manifest.py — manifest_zips.csv 로드

로컬 CSV 파일을 읽어 DataFrame 반환. Drive 통신 없음.

**로드 순서:**
1. 환경변수 `MANIFEST_CSV_PATH` 가 있으면 해당 경로
2. 없으면 프로젝트 루트 `manifest_zips.csv` (기본값)

```python
def load_manifest() -> pd.DataFrame:
    """manifest_zips.csv 로드. 파일 없으면 FileNotFoundError."""
```

**컬럼:**

| 컬럼 | 설명 |
|------|------|
| `file_id` | Drive 원천 ZIP 파일 ID |
| `zip_name` | ZIP 파일명 (예: `TS_건선_정면.zip`) |
| `class_name` | 정규화된 클래스명 |
| `class_idx` | 클래스 인덱스 (0~5) |
| `split` | `train` / `val` / `test` |
| `direction` | `front` / `side` |
| `label_zip_name` | 대응 라벨 ZIP 파일명 |
| `label_file_id` | 라벨 ZIP Drive 파일 ID |

---

### dataset.py — SkinAIDataset

```python
CLASS_MAP = {
    "건선": 0, "아토피피부염": 1, "여드름": 2,
    "주사": 3, "지루피부염": 4, "정상": 5,
}

class SkinAIDataset(Dataset):
    def __getitem__(self, idx) -> tuple:
        """(image_tensor, label_int, meta_dict) 반환."""
```

- `split` + `direction='front'` 필터링
- 이미지 캐시: `~/.cache/skinai_data/images/{filename}`
- 손상 파일: `~/.cache/skinai_data/corrupt_files.txt` 자동 기록
- `meta_dict`: `class_name`, `gender`, `age_range`, `severity`, `lesion_type`

**기본 Transform:**

| split | transform |
|-------|-----------|
| train | `Resize(256) → RandomCrop(224) → RandomHorizontalFlip(0.5) → ColorJitter → RandomRotation(15) → Normalize` |
| val/test | `Resize(256) → CenterCrop(224) → Normalize` |

---

### loader.py — DataLoader 팩토리

```python
def get_dataloader(
    split: str,
    batch_size: int = 32,
    num_workers: int = 4,
    transform=None,
    use_cache: bool = True,
) -> DataLoader:
    """split별 DataLoader 반환."""

def prefetch(split: Optional[str] = None, max_workers: int = 8) -> None:
    """Drive 이미지를 백그라운드에서 로컬 캐시에 미리 다운로드."""
```

- `pin_memory=True` (GPU 학습 가속)
- 커스텀 collate: `(images, labels, meta_dicts)` 튜플 배치
- `split='train'` 이면 `shuffle=True` 자동 적용

---

## Part 1-B: Manifest 생성 스크립트

### scripts/build_manifest.py

Drive 폴더를 재귀 탐색해 원천 ZIP 목록을 수집하고 `manifest_zips.csv` 를 로컬에 저장.

**Drive 폴더 구조:**
```
루트 폴더(SKINAI_DRIVE_FOLDER_ID)
└── 3.개방데이터/
    └── 1.데이터/
        ├── Training/
        │   ├── 01.원천데이터/   TS_{클래스}_{방향}.zip
        │   └── 02.라벨링데이터/ TL_{클래스}_{방향}.zip
        ├── Validation/
        │   ├── 01.원천데이터/   VS_{클래스}_{방향}.zip
        │   └── 02.라벨링데이터/ VL_{클래스}_{방향}.zip
        └── Test/
            ├── 01.원천데이터/   ES_{클래스}_{방향}.zip
            └── 02.라벨링데이터/ EL_{클래스}_{방향}.zip
```

**파일명 파싱 규칙:**

| 위치 | 의미 |
|------|------|
| 접두사 첫 글자 `T/V/E` | train / val / test |
| 접두사 두 번째 글자 `S/L` | 원천(source) / 라벨(label) |
| 두 번째 세그먼트 | 클래스명 (`아토피`→`아토피피부염` 자동 정규화) |
| 세 번째 세그먼트 | `정면`→`front`, `측면`→`side` |

**실행:**
```bash
export SKINAI_DRIVE_FOLDER_ID=1LvubOTjMvGLAhkYD-eML4MZwbxEq-ugg
python scripts/build_manifest.py
```

**출력:**
```
✅ manifest_zips.csv 생성 완료
총 N개 ZIP (train: N / val: N / test: N)
저장 경로: /path/to/skin_ai/manifest_zips.csv
```

Drive 업로드 없이 로컬 저장만 수행합니다.

---

## 환경변수 목록

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `SKINAI_DRIVE_FOLDER_ID` | ✅ (build_manifest) | — | Drive 루트 폴더 ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | 서버만 | — | Service Account JSON 경로 |
| `MANIFEST_CSV_PATH` | ❌ | 프로젝트 루트 `manifest_zips.csv` | manifest CSV 경로 오버라이드 |
| `SKINAI_CACHE_DIR` | ❌ | `~/.cache/skinai_data` | 이미지 캐시 루트 |

> `MANIFEST_FILE_ID`, `SKINAI_MANIFEST_TTL` 환경변수는 제거되었습니다.

---

## 사용 예시

```bash
# 1. 설치
pip install -e .

# 2. manifest 생성 (1회)
export SKINAI_DRIVE_FOLDER_ID=1LvubOTjMvGLAhkYD-eML4MZwbxEq-ugg
python scripts/build_manifest.py

# 3. Drive 인증 (팀원 각자 1회)
python -m skinai_data.auth
```

```python
from skinai_data import get_dataloader

train_loader = get_dataloader(split="train", batch_size=32)
val_loader   = get_dataloader(split="val",   batch_size=32)

for images, labels, meta in train_loader:
    # images: (B, 3, 224, 224) float32
    # labels: (B,) int64, 0~5
    # meta: {"class_name": [...], "gender": [...], ...}
    pass
```
