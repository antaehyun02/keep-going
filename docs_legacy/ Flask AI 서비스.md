# SCIN 피부 질환 AI 분류 시스템

Google Research SCIN 데이터셋 기반 피부 질환 자동 분류 (50개 질환, ResNet50 모델)

---

## 📁 프로젝트 구조

```
scin/
├── data/              # 데이터셋 (SCIN)
├── checkpoints/       # 학습된 모델
├── model/
│   ├── resnet50/      # ResNet50 모델 학습/평가
│   ├── dataset.py     # 데이터 로더
│   └── loss.py        # Focal Loss
└── api/               # Flask AI 서비스 (추론 API)
```

---

## 🚀 빠른 시작

### 1. Flask AI 서비스 실행

```bash
# 의존성 설치
cd scin/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 서비스 시작
./start.sh
```

**API**: `http://localhost:5001`

### 2. 모델 재학습

```bash
cd scin/model/resnet50
./retrain_focal.sh
```

**상세 가이드**: [재학습_가이드.md](재학습_가이드.md)

---

## 📊 모델 성능

| 메트릭 | 값 |
|--------|-----|
| Top-5 Accuracy | 64.8% |
| F1-Score | 0.082 (개선 필요) |
| 모델 | ResNet50 + Focal Loss |
| 데이터셋 | SCIN (10,407 이미지, 50 질환) |

---

## 🔧 주요 파일

| 파일 | 설명 |
|------|------|
| `재학습_가이드.md` | 모델 재학습 방법 |
| `api/app.py` | Flask AI 서비스 |
| `api/inference.py` | 모델 추론 로직 |
| `model/resnet50/train.py` | 학습 스크립트 |
| `model/loss.py` | Focal Loss 구현 |

---

## 📖 API 사용법

### 이미지 분류 (POST /predict)

```bash
curl -X POST http://localhost:5001/predict \
  -F "image=@skin_image.jpg"
```

**응답:**
```json
{
  "success": true,
  "data": {
    "predictions": [
      {
        "disease": "Eczema",
        "disease_ko": "습진",
        "confidence": 0.85,
        "recommendations": ["피부과 상담 권장", "보습제 사용"]
      }
    ],
    "top_disease": "Eczema",
    "overall_confidence": 0.85
  }
}
```

---

## 🛠️ 개발 환경

- **Python**: 3.9+
- **PyTorch**: 2.0+
- **Flask**: 3.0+
- **디바이스**: GPU/MPS/CPU (자동 감지)

---

## 📚 참고 문서

- **데이터 분석**: [SCIN_데이터_모델_분석_리포트.md](../SCIN_데이터_모델_분석_리포트.md)
- **재학습 가이드**: [재학습_가이드.md](재학습_가이드.md)
- **SCIN 논문**: https://arxiv.org/abs/2111.07067
