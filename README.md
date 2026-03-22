# SkinAI

AI 기반 안면 피부 질환 분류 의료 보조 서비스.

6개 클래스(건선, 아토피피부염, 여드름, 주사, 지루피부염, 정상) 를 AI Hub 08-14 합성 데이터셋으로 학습한 DenseNet121 분류 모델과 DeeplabV3+ 병변 세그멘테이션 모델을 기반으로 동작합니다.

---

## 프로젝트 구조

```
skin_ai/
├── skinai_data/          # Part 1: Google Drive DataLoader 패키지
├── scripts/              # Part 1-B: manifest 생성 스크립트
├── ai/
│   ├── preprocessing/    # Part 2: 전처리 파이프라인
│   ├── training/         # Part 3: 모델 학습
│   │   ├── classifier/   #   분류 + 세그멘테이션 학습 코드
│   │   └── utils.py      #   공유 유틸리티 (get_device 등)
│   └── inference/        # Part 4: Flask 추론 API
├── backend/              # Node.js / Express 백엔드 (port 3000)
├── frontend/             # Vanilla JS / HTML / CSS 프론트엔드
├── docker/               # Dockerfile (ai, backend)
├── docker-compose.yml    # 전체 스택 오케스트레이션
├── setup.py              # skinai-data pip 패키지 정의
└── CLAUDE.md             # 코딩 규칙 및 프로젝트 가이드
```

---

## 서비스 구성

| 서비스 | 기술 스택 | 포트 |
|--------|-----------|------|
| Backend | Node.js / Express | 3000 |
| AI Service | Python / Flask + PyTorch | 5001 |
| Frontend | Vanilla JS / HTML / CSS | (백엔드가 정적 파일 서빙) |
| Database | PostgreSQL (Docker) | 5432 |

### 요청 흐름

```
Browser → Frontend → Express (:3000) → Flask AI (:5001)
                           ↓
                      uploads/ (이미지)
                           ↓
                      PostgreSQL (분석 이력)
```

---

## 개발 환경 설정

### 필수 환경변수

루트 `.env` (`.env.example` 참고):

```
JWT_SECRET=your_jwt_secret
JWT_EXPIRE=24h
PORT=3000
FLASK_AI_SERVICE_URL=http://localhost:5001
FLASK_API_TIMEOUT=30000
```

`ai/inference/.env` (`.env.example` 참고):

```
CLASSIFIER_CHECKPOINT=ai/checkpoints/aihub/best.pth
SEGMENTOR_CHECKPOINT=ai/checkpoints/aihub/best_seg.pth
THRESHOLDS_PATH=ai/checkpoints/aihub/thresholds.json
DEVICE=auto
```

### Backend 실행

```bash
cd backend
npm install
npm start       # port 3000
```

### Flask AI 서비스 실행

```bash
cd ai/inference
python3 -m venv venv && source venv/bin/activate
pip install -r ../../requirements.txt
python app.py   # 개발
gunicorn -w 1 -b 0.0.0.0:5001 app:app   # 운영
```

### Docker Compose (전체 스택)

```bash
docker compose up --build
```

---

## Part 1: skinai-data 패키지

Drive에 업로드된 AI Hub ZIP 파일을 스트리밍 로드하는 PyTorch Dataset 패키지.
`manifest_zips.csv` 를 기준으로 동작하며, Drive 통신은 이미지 로드 시에만 발생합니다.

### 설치

```bash
pip install -e .
```

### 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `SKINAI_DRIVE_FOLDER_ID` | ✅ (build_manifest) | Drive 루트 폴더 ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | 서버만 | Service Account JSON 경로 |
| `MANIFEST_CSV_PATH` | ❌ | manifest CSV 경로 (기본: 프로젝트 루트 `manifest_zips.csv`) |
| `SKINAI_CACHE_DIR` | ❌ | 이미지 캐시 루트 (기본: `~/.cache/skinai_data`) |

### Manifest 생성 (1회)

```bash
export SKINAI_DRIVE_FOLDER_ID=1LvubOTjMvGLAhkYD-eML4MZwbxEq-ugg
python scripts/build_manifest.py
# → manifest_zips.csv 생성 완료 메시지 출력
```

### Drive 인증 (팀원 각자 1회)

```bash
python -m skinai_data.auth
```

### 사용법

```python
from skinai_data import get_dataloader

train_loader = get_dataloader("train", batch_size=32)
for images, labels, meta in train_loader:
    # images: (B, 3, 224, 224)  labels: (B,)  meta: dict
    ...
```

---

## Part 2: 데이터 전처리 파이프라인

AI Hub 08-14 원시 데이터를 학습 가능한 형태로 변환합니다.

### 전처리 실행

```bash
# 전처리 (train/val/test CSV 생성)
python -m ai.preprocessing.aihub_preprocessor

# 유효성 검증
python -m ai.preprocessing.aihub_validate

# EDA 시각화 생성
python -m ai.preprocessing.aihub_eda
```

### 출력 파일

```
ai/preprocessing/processed_aihub/
├── train.csv        # 학습 데이터 (약 70%)
├── val.csv          # 검증 데이터 (약 15%)
├── test.csv         # 테스트 데이터 (약 15%)
├── metadata.json    # 데이터셋 통계
├── corrupt_files.txt
└── eda/             # 시각화 PNG
```

---

## Part 3: AI 모델 학습

### 분류 모델 (DenseNet121 / EfficientNet-B3)

```bash
# DenseNet121 (기본)
python -m ai.training.classifier.train

# EfficientNet-B3
python -m ai.training.classifier.train --backbone efficientnet_b3

# 하이퍼파라미터 오버라이드
python -m ai.training.classifier.train \
    --num_epochs 50 \
    --batch_size 16
```

목표: Top-1 Accuracy ≥ 80%, Stretch Goal ≥ 85%

### 세그멘테이션 모델 (DeeplabV3+ ResNet101, 아토피 병변)

```bash
python -m ai.training.classifier.train_seg \
    --mask_dir ai/preprocessing/processed_aihub/masks
```

목표: IoU ≥ 0.65

### 평가

```bash
python -m ai.training.classifier.evaluate \
    --checkpoint ai/checkpoints/aihub/best.pth
```

### Threshold 최적화

```bash
# F1 최대화 모드
python -m ai.training.classifier.threshold_opt \
    --checkpoint ai/checkpoints/aihub/best.pth

# Precision 보장 모드
python -m ai.training.classifier.threshold_opt \
    --checkpoint ai/checkpoints/aihub/best.pth \
    --mode precision --min_precision 0.75
```

결과는 `ai/checkpoints/aihub/thresholds.json` 에 저장됩니다.

### 학습 파라미터 (AI Hub 공식 권장값)

| 파라미터 | 값 |
|----------|-----|
| batch_size | 32 |
| learning_rate | 0.001 |
| optimizer | Adam |
| dropout | 0.5 |
| image_size | 256 → crop 224 |
| num_epochs | 30 |

---

## Part 4: Flask 추론 API

### 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서비스 상태 확인 |
| POST | `/predict` | 이미지 추론 (분류 + Grad-CAM) |

### `/predict` 요청

```bash
curl -X POST http://localhost:5001/predict \
  -F "image=@skin_photo.jpg"
```

### `/predict` 응답 예시

```json
{
  "top_predictions": [
    {"class": "아토피피부염", "confidence": 0.87, "class_idx": 1},
    {"class": "건선", "confidence": 0.09, "class_idx": 0}
  ],
  "is_uncertain": false,
  "gradcam_base64": "data:image/png;base64,...",
  "atopy_segment": {
    "lesion_ratio": 0.23,
    "mask_base64": "data:image/png;base64,..."
  },
  "model_info": {
    "backbone": "densenet121",
    "thresholds_loaded": true
  }
}
```

### Express → Flask 프록시 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/ai/analyze` | 레거시 분석 (ResNet50) |
| POST | `/api/ai/predict` | 신규 분석 (DenseNet121) |
| POST | `/api/ai/analyses` | 분석 결과 저장 |
| GET | `/api/ai/analyses` | 분석 이력 조회 |

---

## Part 5: 프론트엔드

`frontend/src/analyze.html` — 피부 분석 페이지:

- 이미지 드래그&드롭 / 파일 선택 업로드
- Chart.js 수평 막대 그래프 (예측 확률)
- Grad-CAM 오버레이 탭
- 임상 참고 통계 (성별/연령/인종별 발병률)
- 분석 결과 저장 버튼

---

## 클래스 정의

| 클래스 | 설명 | class_idx |
|--------|------|-----------|
| 건선 | Psoriasis | 0 |
| 아토피피부염 | Atopic Dermatitis | 1 |
| 여드름 | Acne | 2 |
| 주사 | Rosacea | 3 |
| 지루피부염 | Seborrheic Dermatitis | 4 |
| 정상 | Normal | 5 |

---

## 현재 제한사항

- **인메모리 저장소**: 게시판 데이터는 재시작 시 초기화됨 (PostgreSQL 마이그레이션 예정)
- **체크포인트 미포함**: `.pth` 파일은 gitignore — 별도 학습 필요
- **학습 데이터 미포함**: AI Hub 라이선스로 인해 별도 신청 필요
- **Grad-CAM**: `pytorch-grad-cam` 패키지 설치 필요 (`pip install grad-cam`)

---

## 라이선스

본 프로젝트는 연구/교육 목적으로 작성되었습니다. AI Hub 데이터셋 사용 시 해당 라이선스 정책을 준수하세요.
