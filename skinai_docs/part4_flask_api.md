# Part 4: Flask 추론 API 기획안

## 개요

PyTorch 모델을 서빙하는 Flask 기반 AI 추론 서비스.

분류(DenseNet121) + 세그멘테이션(DeeplabV3+) 를 단일 엔드포인트에서 처리하며, Grad-CAM 시각화를 Base64 PNG로 반환합니다.

---

## 목표

- 단일 이미지 요청에 분류 + Grad-CAM + 세그멘테이션 결과 통합 반환
- 모델 없이도 서버 기동 가능 (graceful degradation)
- 클래스별 threshold 기반 불확실 예측 처리
- Docker 컨테이너 배포 지원

---

## API 명세

### GET /health

서비스 상태 확인.

**응답:**
```json
{
  "status": "healthy",
  "classifier_loaded": true,
  "segmentor_loaded": false,
  "thresholds_loaded": true,
  "device": "mps"
}
```

### POST /predict

이미지 추론.

**요청:** `multipart/form-data`
- `image`: 이미지 파일 (jpg, jpeg, png)
- 최대 크기: 10MB
- 최소 해상도: 100×100px

**응답:**
```json
{
  "top_predictions": [
    {"class": "아토피피부염", "confidence": 0.87, "class_idx": 1},
    {"class": "건선",        "confidence": 0.09, "class_idx": 0},
    {"class": "지루피부염",  "confidence": 0.03, "class_idx": 4}
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

`is_uncertain: true` — 최고 확률 예측이 해당 클래스 threshold 미만일 때.

`atopy_segment` — 최고 예측 클래스가 "아토피피부염" 일 때만 포함.

---

## 코드 구조 (scin/api/app.py)

### 모듈 레벨 상수

```python
NUM_CLASSES = 6
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
MIN_IMAGE_SIZE = 100
INFER_RESIZE = 256
INFER_CROP = 224
TOP_K = 3
ATOPY_CLASS = "아토피피부염"
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]
```

### 모듈 레벨 Transform (요청마다 재생성 방지)

```python
_infer_transform = transforms.Compose([
    transforms.Resize(INFER_RESIZE),
    transforms.CenterCrop(INFER_CROP),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])
```

### 헬퍼 함수

| 함수 | 역할 |
|------|------|
| `_build_model_from_checkpoint(backbone, ckpt)` | 체크포인트에서 모델 복원 |
| `_load_thresholds(path)` | thresholds.json 로드, 부재 시 None |
| `_validate_image(file)` | PIL 열기 + 크기 + 포맷 검증 |
| `_generate_gradcam(model, tensor, class_idx)` | Grad-CAM Base64 PNG 생성 |
| `_run_segmentation(image)` | DeeplabV3+ 병변 마스크 생성 |

### 서버 시작 시 초기화 (startup 순서)

1. `DEVICE` 환경변수로 디바이스 결정
2. `CLASSIFIER_CHECKPOINT` 로드 → 실패해도 서버 기동 (is_uncertain=true 반환)
3. `SEGMENTOR_CHECKPOINT` 로드 → 실패해도 서버 기동 (atopy_segment 생략)
4. `THRESHOLDS_PATH` 로드 → 실패해도 argmax fallback

---

## 에러 처리

| 상황 | HTTP 코드 | 응답 |
|------|-----------|------|
| 이미지 없음 | 400 | `{"error": "이미지를 업로드해주세요"}` |
| 잘못된 포맷 | 400 | `{"error": "지원하지 않는 이미지 형식입니다"}` |
| 파일 크기 초과 | 400 | `{"error": "파일 크기는 10MB 이하여야 합니다"}` |
| 해상도 부족 | 400 | `{"error": "이미지 해상도가 너무 낮습니다 (최소 100x100)"}` |
| 모델 미로드 | 503 | `{"error": "AI 모델이 로드되지 않았습니다"}` |
| 추론 오류 | 500 | `{"error": "추론 중 오류가 발생했습니다"}` |

예외 타입별 처리:
- `(OSError, UnidentifiedImageError)` — 이미지 검증
- `(RuntimeError, torch.cuda.CudaError)` — 추론 오류
- `(RuntimeError, AttributeError, TypeError)` — Grad-CAM 오류
- `ImportError` — `pytorch-grad-cam` 미설치 시 Grad-CAM skip

---

## Grad-CAM

`pytorch-grad-cam` 패키지 사용.

타겟 레이어:
- DenseNet121: `model.features.denseblock4`
- EfficientNet-B3: `model.features[-1]`

Base64 인코딩 후 반환: `data:image/png;base64,...`

`pytorch-grad-cam` 미설치 시 `gradcam_base64: null` 로 graceful degradation.

---

## Express 프록시 (backend/src/routes/ai.js)

| 메서드 | 경로 | 내부 동작 |
|--------|------|-----------|
| POST | `/api/ai/analyze` | 레거시 ResNet50 경로 유지 |
| POST | `/api/ai/predict` | Flask `/predict` 프록시 |
| POST | `/api/ai/analyses` | 분석 결과 DB 저장 |
| GET | `/api/ai/analyses` | 분석 이력 조회 |

`callFlaskPredict(filepath)` 헬퍼가 Flask 호출 로직을 캡슐화.

HTTP 상태 코드: `HTTP_STATUS` 상수 객체 사용.
에러 메시지: `ERROR_MESSAGES` 상수 객체 사용.

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `CLASSIFIER_CHECKPOINT` | `scin/checkpoints/aihub/best.pth` | 분류 모델 체크포인트 |
| `SEGMENTOR_CHECKPOINT` | `scin/checkpoints/aihub/best_seg.pth` | 세그멘테이션 체크포인트 |
| `THRESHOLDS_PATH` | `scin/checkpoints/aihub/thresholds.json` | 클래스별 threshold |
| `DEVICE` | `auto` | `auto`, `cuda`, `mps`, `cpu` |
| `FLASK_PORT` | `5001` | 서비스 포트 |
| `FLASK_HOST` | `0.0.0.0` | 바인드 주소 |

---

## Docker

```dockerfile
# docker/ai/Dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install torch torchvision flask gunicorn grad-cam
COPY scin/ /app/scin/
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5001", "scin.api.app:app"]
```

단일 워커(`-w 1`): PyTorch 모델은 멀티프로세스에서 공유 불가.

---

## 주요 설계 결정

- **모듈 레벨 초기화**: 모델과 transform 을 앱 시작 시 1회만 로드 — 요청마다 로드하면 레이턴시 수 초
- **Graceful degradation**: 체크포인트 없이도 서버 기동, 가능한 결과만 반환
- **Threshold fallback**: `thresholds.json` 없으면 argmax 사용 — 운영 환경 호환성 유지
- **로그에 이미지 경로 미포함**: 환자 개인정보 보호를 위해 파일명/경로 로그 제외
- **단일 워커**: PyTorch GPU 컨텍스트 공유 문제 방지
