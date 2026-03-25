# 데이터셋 준비 가이드

PM과 팀원 모두 **각자 로컬에서** Drive에서 직접 다운로드합니다.
PM은 Drive 폴더에 팀원 Google 계정을 **뷰어**로 추가해주세요.

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
python scripts/download_dataset.py --output-dir data/raw --resume

# 특정 split만
python scripts/download_dataset.py --output-dir data/raw --split train --resume

# 라벨 JSON ZIP도 포함
python scripts/download_dataset.py --output-dir data/raw --include-labels --resume
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

## 압축 해제 후 폴더 구조

```
data/raw/
├── train/
│   ├── 건선/
│   │   └── 정면/
│   │       ├── P2_건선_001.png
│   │       ├── P2_건선_002.png
│   │       └── ...
│   ├── 아토피피부염/
│   │   └── 정면/
│   ├── 여드름/
│   │   └── 정면/
│   ├── 주사/
│   │   └── 정면/
│   ├── 지루피부염/
│   │   └── 정면/
│   └── 정상/
│       └── 정면/
└── val/
    └── (동일 구조)
```

### 확인

```bash
find data/raw/train -name "*.png" | wc -l
find data/raw/val   -name "*.png" | wc -l
```

정상 다운로드 시 train 약 8,400장 / val 약 2,400장 (정면 기준).
