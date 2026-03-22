# Part 5: 프론트엔드 기획안

## 개요

피부 분석 결과를 시각적으로 표시하는 `analyze.html` 페이지 구현.

기존 SkinAI 프론트엔드(Vanilla JS / HTML / CSS, 빌드 단계 없음) 스타일을 유지하며 Chart.js와 Grad-CAM 탭을 추가합니다.

---

## 목표

- 이미지 업로드 → AI 분석 → 결과 시각화 전체 흐름 단일 페이지에서 완결
- Chart.js 수평 막대로 예측 확률 직관적 표시
- Grad-CAM 오버레이로 모델 판단 근거 시각화
- 임상 참고 통계로 의학적 맥락 제공
- 분석 결과 저장 기능

---

## 페이지 레이아웃 (analyze.html)

2열 구조:

```
┌──────────────────┬──────────────────┐
│   왼쪽 패널      │   오른쪽 패널    │
│                  │                  │
│  이미지 업로드   │  예측 결과       │
│  드래그&드롭     │  (Chart.js)      │
│  미리보기        │                  │
│                  │  Grad-CAM 탭     │
│                  │  세그멘테이션 탭  │
│                  │                  │
│                  │  임상 참고 통계  │
│                  │                  │
│                  │  [저장] 버튼     │
└──────────────────┴──────────────────┘
```

---

## 기능 명세 (analyze.js)

### 이미지 업로드

- 파일 선택 (`<input type="file">`)
- 드래그&드롭 (`dragover`, `drop` 이벤트)
- 미리보기: `FileReader.readAsDataURL()`
- 클라이언트 사이드 사전 검증:
  - 파일 타입: `image/jpeg`, `image/png`
  - 파일 크기: 10MB 이하

### 분석 요청

```javascript
// POST /api/ai/predict (JWT 인증)
const formData = new FormData();
formData.append('image', file);

const response = await fetch('/api/ai/predict', {
  method: 'POST',
  headers: { Authorization: `Bearer ${token}` },
  body: formData,
});
```

로딩 상태: 버튼 비활성화 + 스피너 표시.

### 예측 결과 — Chart.js

수평 막대 그래프:
- X축: 확률 (0 ~ 1)
- Y축: 클래스명 (한국어)
- 색상: 예측 1위 강조 (파란색), 나머지 회색
- `is_uncertain: true` 시 "판단 불가" 배너 표시

```javascript
new Chart(ctx, {
  type: 'bar',
  options: { indexAxis: 'y', ... }
});
```

### Grad-CAM 탭

- 탭 1: 원본 이미지
- 탭 2: Grad-CAM 오버레이 (`gradcam_base64`)
- 탭 3: 세그멘테이션 마스크 (`atopy_segment.mask_base64`, 아토피일 때만 활성화)

`gradcam_base64` 가 null이면 탭 2 비활성화.

### 임상 참고 통계

서버 시작 시 pre-compute된 통계를 정적으로 표시 (API 호출 없음):

| 항목 | 내용 |
|------|------|
| 전체 발병률 | 질환별 인구 유병률 |
| 성별 분포 | 남/여 발병 비율 |
| 연령대 분포 | 10대~60대 발병률 |

데이터 소스: AI Hub 데이터셋 통계 기반 (연구용 참고치).

### 결과 저장

```javascript
// POST /api/ai/analyses (JWT 인증)
await fetch('/api/ai/analyses', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    top_class: prediction.top_predictions[0].class,
    confidence: prediction.top_predictions[0].confidence,
    is_uncertain: prediction.is_uncertain,
    full_result: prediction,
  }),
});
```

저장 성공 시 버튼 비활성화 + "저장됨" 표시.

---

## 공통 컴포넌트

`common-nav.js` — 기존 네비게이션 바 (변경 없음).

Auth 상태: `localStorage.getItem('token')` — JWT 없으면 로그인 페이지로 리다이렉트.

---

## 에러 처리 (UI)

| 상황 | 처리 |
|------|------|
| 파일 타입 오류 | 인라인 에러 메시지 |
| 파일 크기 초과 | 인라인 에러 메시지 |
| 네트워크 오류 | toast 알림 |
| AI 서비스 불가 | "분석 서비스가 일시적으로 불가합니다" toast |
| 미인증 | 로그인 페이지 리다이렉트 |

---

## 의료 면책 고지

결과 화면 하단에 면책 문구 표시:

> "본 서비스는 의료 진단을 대체하지 않습니다. 정확한 진단은 전문의와 상담하세요."

---

## 주요 설계 결정

- **빌드 단계 없음**: 기존 프로젝트와 일관성 유지 — Vanilla JS, CDN Chart.js
- **클라이언트 사전 검증**: 불필요한 서버 요청 방지 (파일 타입/크기)
- **탭 구조**: Grad-CAM 과 원본을 같은 공간에서 비교 — UX 최적화
- **임상 통계 정적 표시**: 매 요청마다 통계 API 호출 없이 UI에 하드코딩 — 응답 속도 향상
- **저장 중복 방지**: 저장 완료 후 버튼 비활성화
