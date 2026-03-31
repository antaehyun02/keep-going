# SkinAI

AI 기반 안면 피부 질환 분류 의료 보조 서비스.

6개 클래스(건선, 아토피피부염, 여드름, 주사, 지루피부염, 정상)를 AI Hub 08-14 합성 데이터셋으로 학습한 DenseNet121 모델 기반.

---

## 프로젝트 구조

```
skin_ai/
├── ai/                       # AI 핵심 모듈
│   ├── dataset/              #   데이터셋 클래스 (PyTorch Dataset)
│   ├── preprocessing/        #   전처리 파이프라인
│   ├── training/             #   모델 학습
│   │   ├── classifier/       #     분류 + 세그멘테이션 학습
│   │   └── utils.py          #     공유 유틸리티
│   ├── testing/              #   평가 + 임계값 최적화
│   └── inference/            #   Flask 추론 API
│
├── skinai_data/              # Google Drive DataLoader 패키지
│   ├── scripts/              #   Drive 관리 스크립트
│   │   ├── build_manifest.py #     Drive 탐색 → manifest_zips.csv 생성
│   │   ├── download_dataset.py #   ZIP 다운로드 (--save-zip / 압축 해제)
│   │   ├── upload_to_drive.py  #   [PM 전용] 로컬 데이터 → Drive 업로드
│   │   └── manifest_zips.csv #     Drive ZIP 파일 목록 (git 추적)
│   ├── auth.py               #   Drive API 인증
│   ├── manifest.py           #   manifest CSV 로드
│   ├── dataset.py            #   Drive 스트리밍 Dataset
│   └── loader.py             #   DataLoader 래퍼
│
├── skinai_docs/              # 기획 문서
│
├── backend/                  # Node.js / Express (port 3000)
├── frontend/                 # Vanilla JS / HTML / CSS
├── scin_legacy/              # 레거시 SCIN ResNet50 (유지만)
│
├── data/                     # 데이터 (대부분 gitignored)
│   ├── dataset_14/           #   AI Hub ZIP 원본 (gitignored)
│   │   ├── Training/
│   │   │   ├── 01_raw/       #     TS_{클래스}_{방향}.zip × 12
│   │   │   └── 02_label/     #     TL_{클래스}_{방향}.zip × 12
│   │   └── Validation/
│   │       ├── 01_raw/       #     VS_{클래스}_{방향}.zip × 12
│   │       └── 02_label/     #     VL_{클래스}_{방향}.zip × 12
│   ├── raw/                  #   ZIP 압축 해제 원본 (gitignored, Drive 경유)
│   └── processed/            #   전처리 CSV — train.csv / val.csv (git 추적)
│
└── setup.py                  # skinai-data pip 패키지 정의
```

---

## 서비스 구성

| 서비스 | 기술 스택 | 포트 |
|--------|-----------|------|
| Backend | Node.js / Express | 3000 |
| AI Service | Python / Flask + PyTorch | 5001 |
| Frontend | Vanilla JS / HTML / CSS | (백엔드 서빙) |

```
Browser → Frontend → Express (:3000) → Flask AI (:5001)
```

---

## 개발 환경 설정

### Backend

```bash
cd backend && npm install && npm start   # port 3000
```

### Flask AI 서비스

```bash
cd ai/inference
pip install -r requirements.txt
python app.py          # 개발 (port 5001)
```

### skinai-data 패키지 설치

```bash
pip install -e .
```

---

## 데이터 파이프라인

### 1. Drive 인증 (최초 1회)

```bash
python -m skinai_data.auth
```

### 2. ZIP 다운로드

```bash
# 방법 A — ZIP 그대로 저장 (전처리기 직접 호환, 권장)
python skinai_data/scripts/download_dataset.py --save-zip --include-labels --resume

# 방법 B — 압축 해제하여 PNG 저장
python skinai_data/scripts/download_dataset.py --resume
```

자세한 설명: [skinai_data/scripts/README.md](skinai_data/scripts/README.md)

### 3. 전처리 (CSV 생성)

```bash
python -m ai.preprocessing.aihub_preprocessor   # data/dataset_14 → data/processed (기본값)
```

### 3. 학습

```bash
python -m ai.training.classifier.train               # DenseNet121
python -m ai.training.classifier.train_seg            # 세그멘테이션 (아토피)
```

### 4. 평가

```bash
python -m ai.testing.evaluate \
    --checkpoint ai/checkpoints/aihub/best.pth
python -m ai.testing.threshold_opt \
    --checkpoint ai/checkpoints/aihub/best.pth
```

---

## 클래스 정의

| class_idx | 클래스 | 영문 |
|-----------|--------|------|
| 0 | 건선 | Psoriasis |
| 1 | 아토피피부염 | Atopic Dermatitis |
| 2 | 여드름 | Acne |
| 3 | 주사 | Rosacea |
| 4 | 지루피부염 | Seborrheic Dermatitis |
| 5 | 정상 | Normal |

---

## 현재 제한사항

- 인메모리 저장소: 게시판 데이터 재시작 시 초기화 (PostgreSQL 마이그레이션 예정)
- 체크포인트 미포함: `.pth` 파일은 gitignore — 별도 학습 필요
- 학습 데이터 미포함: AI Hub 라이선스로 인해 별도 신청 필요
