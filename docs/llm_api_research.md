# LLM API 통합 가이드

> 작성일: 2026-04-15  
> 목적: skin_ai PyTorch 분류 모델과 LLM API를 실제로 연동하는 실전 가이드

---

## 1. 현재 흐름과 LLM 연동 지점

현재 프로젝트는 **순수 Computer Vision 시스템**으로 LLM이 전혀 없음.

```
[현재]
이미지 → PyTorch 분류 (DenseNet121/EfficientNet-B3) → 하드코딩 추천문구 출력

[LLM 연동 후]
이미지 → PyTorch 분류 → { class_name, confidence, clinical_ref }
                                    ↓
                          Claude Sonnet API 호출
                                    ↓
                    자연어 진단 리포트 + 생활 관리 조언 출력
```

`/predict` 엔드포인트가 이미 `class_name`, `confidence`, `top3`, `clinical_ref`를 반환하므로,  
**이 JSON을 그대로 Claude에 넘기면 바로 연동 가능** — 이미지를 LLM에 직접 보낼 필요 없음.

---

## 2. 주요 LLM API 목록

### 상용 API (유료, 고성능)

| 제공사 | 대표 모델 | 비전 지원 | 특징 |
|---|---|---|---|
| **Anthropic** | Claude Sonnet 4.6 / Haiku 4.5 | ✅ | 안전성·한국어 품질 우수, Prompt Caching으로 비용 절감 |
| **Google** | Gemini 2.5 Flash / Flash-Lite | ✅ | 멀티모달 비용 효율 우수, 이미지도 텍스트와 동일 요금 |
| **Mistral AI** | Mistral Large / Small | ❌ | 유럽 데이터 규정 준수, 텍스트 생성 특화 |
| **Cohere** | Command R+ | ❌ | RAG·검색 증강에 특화 |

### 무료 / 오픈소스 API

| 제공사 | 대표 모델 | 특징 |
|---|---|---|
| **Groq** | Llama 3.3 70B, Gemma 2 9B 등 | 무료 티어 있음, 응답 속도 매우 빠름 (LPU 기반) |
| **Together AI** | Llama 3, Mistral, Qwen 등 | 오픈소스 모델 호스팅, 무료 크레딧 제공 |
| **Hugging Face Inference API** | Llama, Mistral 등 수백 종 | 무료 티어 있음, 모델 선택 폭 넓음 |
| **Ollama (로컬)** | Llama 3, Gemma, Mistral 등 | 완전 무료, 로컬 실행 — 인터넷 불필요, 개인정보 안전 |
| **OpenRouter** | 다수 모델 통합 | 단일 API로 여러 제공사 모델 사용 가능, 일부 무료 모델 포함 |
| **Cerebras** | Llama 3.3 70B 등 | 무료 티어 있음, 추론 속도 세계 최고 수준 |

> **MVP 추천 전략**: 개발 단계에서는 **Groq 무료 티어** 또는 **Ollama 로컬**로 비용 없이 테스트 → 프로덕션 전환 시 **Claude Sonnet**으로 교체

---

## 3. 우리 모델과 Claude Sonnet 연동 방법

### 3-1. API 키 발급

1. [console.anthropic.com](https://console.anthropic.com) 접속 → 로그인
2. **API Keys** 메뉴 → **Create Key**
3. 생성된 키 복사 (`sk-ant-...` 형태)

### 3-2. 환경변수 설정

[ai/inference/.env.example](ai/inference/.env.example)을 복사해서 `.env`로 사용:

```bash
cp ai/inference/.env.example ai/inference/.env
```

[ai/inference/.env](ai/inference/.env)에 LLM 관련 항목 추가:

```env
# ── 기존 설정 (변경 없음) ─────────────────────────────────────
FLASK_ENV=development
FLASK_PORT=5001
FLASK_DEBUG=0
MODEL_PATH=ai/checkpoints/aihub/best.pth
MODEL_BACKBONE=densenet121
THRESHOLD_PATH=ai/checkpoints/aihub/thresholds.json
DATA_CSV=data/processed/train.csv
DEVICE=auto
GRADCAM_ALPHA=0.4

# ── LLM 연동 추가 항목 ───────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-여기에_실제_키_입력
LLM_MODEL=claude-sonnet-4-6            # 리포트 생성 (품질 우선)
LLM_MODEL_CHAT=claude-haiku-4-5-20251001  # 챗봇 후속 질문 (속도 우선)
LLM_MAX_TOKENS=1024
LLM_ENABLED=true                       # false 로 끄면 LLM 없이 동작
```

> **주의**: `.env` 파일은 절대 git 커밋 금지. `.gitignore`에 포함 여부 확인.

### 3-3. 패키지 설치

```bash
pip install anthropic
```

### 3-4. Flask `/predict`에 연동하는 함수

[ai/inference/app.py](ai/inference/app.py)의 `/predict`는 이미 `prediction`과 `clinical_ref`를 반환함.  
아래 함수를 추가하고 `/predict` 응답 직전에 호출:

```python
import anthropic

def _generate_report(prediction: dict, clinical_ref: dict | None) -> str:
    """분류 결과를 Claude에 넘겨 자연어 리포트를 생성한다.
    LLM_ENABLED=false 이거나 API 키 없으면 빈 문자열 반환 (서버 다운 없음).
    """
    if os.environ.get("LLM_ENABLED", "false").lower() != "true":
        return ""

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("[LLM] ANTHROPIC_API_KEY 미설정 — 리포트 생략")
        return ""

    client = anthropic.Anthropic(api_key=api_key)

    # 임상 참고 데이터를 읽기 쉽게 변환
    clinical_text = ""
    if clinical_ref:
        if clinical_ref.get("age_distribution"):
            top_age = max(clinical_ref["age_distribution"], key=clinical_ref["age_distribution"].get)
            clinical_text += f"- 주 발병 연령대: {top_age}\n"
        if clinical_ref.get("gender_ratio"):
            top_gender = max(clinical_ref["gender_ratio"], key=clinical_ref["gender_ratio"].get)
            clinical_text += f"- 주 발병 성별: {top_gender}\n"
        if clinical_ref.get("severity_dist"):
            top_sev = max(clinical_ref["severity_dist"], key=clinical_ref["severity_dist"].get)
            clinical_text += f"- 주 중증도: {top_sev}\n"

    top3_text = "\n".join(
        f"  {i+1}. {item['class']} ({item['prob']*100:.1f}%)"
        for i, item in enumerate(prediction.get("top3", []))
    )

    # 시스템 프롬프트에 cache_control → 반복 호출 시 입력 비용 최대 90% 절감
    system_prompt = """당신은 피부과 전문 AI 어시스턴트입니다.
딥러닝 모델의 피부 분류 결과를 바탕으로 사용자가 이해하기 쉬운 설명을 제공합니다.
반드시 아래 원칙을 따르세요:
1. 이 분석은 참고용이며, 정확한 진단은 피부과 전문의 상담이 필요합니다.
2. 존재하지 않는 약품명이나 치료법은 절대 언급하지 않습니다.
3. 3~4 문단 이내로 작성합니다: 결과 요약 → 일반적 특징 → 생활 관리 조언 → 전문의 상담 권유."""

    user_message = f"""피부 AI 분석 결과입니다.

예측 결과: {prediction['class_name']} (신뢰도 {prediction['confidence']*100:.1f}%)
상위 3개 후보:
{top3_text}

임상 참고 정보:
{clinical_text if clinical_text else '(데이터 없음)'}

위 결과를 바탕으로 사용자에게 설명해주세요."""

    try:
        response = client.messages.create(
            model=os.environ.get("LLM_MODEL", "claude-sonnet-4-6"),
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "1024")),
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}  # 프롬프트 캐싱
            }],
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except anthropic.APIError as e:
        logger.error(f"[LLM] Claude API 오류: {e}")
        return ""
```

`/predict` 응답에 `report` 필드 추가:

```python
report = _generate_report(prediction, clinical_ref)

return jsonify({
    "success": True,
    "prediction": prediction,
    "gradcam": gradcam_b64,
    "clinical_ref": clinical_ref,
    "report": report,            # 추가
    "processing_time_ms": elapsed_ms,
})
```

---

## 4. LLM 질의응답 테스트 방법

### 4-1. Claude 단독 테스트 (PyTorch 모델 없이 바로 확인)

`ai/testing/test_llm.py`로 저장 후 실행:

```python
"""Claude API 단독 테스트 — PyTorch 없이 LLM 응답 품질만 검증"""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv("ai/inference/.env")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# 가짜 분류 결과로 프롬프트 테스트
fake_prediction = {
    "class_name": "아토피피부염",
    "confidence": 0.91,
    "top3": [
        {"class": "아토피피부염", "prob": 0.91},
        {"class": "건선",        "prob": 0.06},
        {"class": "지루피부염",  "prob": 0.02},
    ]
}

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="당신은 피부과 전문 AI 어시스턴트입니다. 분석 결과를 친절하게 설명하고, 전문의 상담을 권유하세요.",
    messages=[{
        "role": "user",
        "content": f"예측: {fake_prediction['class_name']} (신뢰도 {fake_prediction['confidence']*100:.0f}%). 설명해주세요."
    }]
)

print("=== Claude 응답 ===")
print(response.content[0].text)
print(f"\n입력 토큰: {response.usage.input_tokens}")
print(f"출력 토큰: {response.usage.output_tokens}")
```

```bash
python ai/testing/test_llm.py
```

### 4-2. Flask 서버 통합 테스트 (실제 이미지로)

```bash
# 1. 서버 구동 (LLM_ENABLED=true 상태)
python ai/inference/app.py

# 2. 다른 터미널에서 실제 이미지로 요청
curl -X POST http://localhost:5001/predict \
  -F "image=@테스트이미지.jpg" \
  | python -m json.tool

# 응답에 "report" 필드가 채워지면 연동 성공
```

### 4-3. 프롬프트 품질 검증 체크리스트

테스트할 때 아래 케이스를 순서대로 확인:

| 테스트 케이스 | 확인 포인트 |
|---|---|
| `class_name`을 6종 모두 순회 | 각 질병별 설명이 맥락에 맞는지 |
| `confidence`를 0.55로 낮춤 | 불확실할 때 더 조심스러운 어조인지 |
| `clinical_ref=None`으로 호출 | 오류 없이 graceful fallback 동작하는지 |
| `LLM_ENABLED=false`로 설정 후 호출 | `report`가 빈 문자열로 반환되는지 |
| 시스템 프롬프트 문구 수정 | 전문의 권유 문구가 자연스럽게 포함되는지 |

---

## 5. 시나리오별 적용 방안

### 시나리오 A: 진단 리포트 자동 생성 ⭐ 가장 현실적

- PyTorch 분류 결과 → Claude가 자연어 리포트 생성
- 이미지를 LLM에 안 넘겨도 됨 → 개인정보 이슈 없음, 비용 절감
- **추천 모델**: `Claude Sonnet 4.6` (품질) 또는 `Claude Haiku 4.5` (속도·비용)

### 시나리오 B: 이미지 + 분류 결과 함께 전달

- Grad-CAM 이미지 + 예측 결과를 함께 LLM에 넘겨 더 풍부한 설명 생성
- 피부 이미지를 외부 서버에 전송하므로 **개인정보처리방침 갱신 필수**
- **추천 모델**: `Gemini 2.5 Pro` 또는 `Claude Sonnet 4.6`

### 시나리오 C: 챗봇 후속 질문 응답

- 진단 결과 후 사용자가 추가 질문 가능한 대화 흐름
- **추천 모델**: `Claude Haiku 4.5` (저비용 + 빠른 응답)

---

## 6. 이슈 체크리스트

### 기술적 이슈

- [ ] **API 키 관리**: 환경변수(.env)로 분리, 클라이언트 코드에 노출 금지
- [ ] **응답 지연**: LLM 호출은 1~5초 소요 → 프론트엔드 로딩 UX 처리 필요
- [ ] **스트리밍 응답**: 긴 리포트는 stream 방식으로 UX 개선 가능
- [ ] **에러 핸들링**: API rate limit, timeout 시 `report: ""` fallback 처리
- [ ] **프롬프트 인젝션 방어**: 사용자 입력이 프롬프트에 직접 포함되지 않도록

### 의료/법적 이슈

- [ ] **면책 조항**: 모든 LLM 출력에 "의료 진단 대체 불가" 문구 필수
- [ ] **개인정보**: 이미지를 LLM에 전송하는 경우 개인정보처리방침 갱신 필요
- [ ] **할루시네이션**: 존재하지 않는 약품명·치료법 생성 가능 → 프롬프트로 범위 제한

### 운영 이슈

- [ ] **모델 버전 고정**: `LLM_MODEL=claude-sonnet-4-6` 처럼 버전 명시 (업데이트 시 출력 변화 방지)
- [ ] **비용 한도 알림**: Anthropic Console → Billing → Usage Limits 에서 월 한도 설정
- [ ] **로깅**: LLM 입출력 로그 저장 (디버깅 및 품질 모니터링용)

---

## 7. 참고 자료

- [Anthropic API 문서 — Messages](https://docs.anthropic.com/en/api/messages)
- [Prompt Caching 가이드](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Ensemble Deep Learning and LLM-Assisted Reporting](https://arxiv.org/html/2510.06260v1)
- [SkinGPT-4 | Nature Communications](https://www.nature.com/articles/s41467-024-50043-3)
- [Claude 3 Opus & GPT-4 in Dermoscopic Analysis | PubMed](https://pubmed.ncbi.nlm.nih.gov/39106482/)
- [Application of LLMs in Dermatology | ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2667102625000919)
