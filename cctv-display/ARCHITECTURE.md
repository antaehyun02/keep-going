# 시스템 아키텍처

경부고속도로 실시간 교통정보 시스템의 전체 아키텍처 문서입니다.

## 목차
- [시스템 개요](#시스템-개요)
- [아키텍처 다이어그램](#아키텍처-다이어그램)
- [기술 스택](#기술-스택)
- [데이터 플로우](#데이터-플로우)
- [컴포넌트 설명](#컴포넌트-설명)
- [API 설계](#api-설계)
- [데이터베이스 구조](#데이터베이스-구조)
- [배포 구조](#배포-구조)

---

## 시스템 개요

### 시스템 목적
경부고속도로 수원-천안 구간의 실시간 교통 상황을 모니터링하고, AI 기반 예측을 통해 사용자에게 교통 정보를 제공하는 웹 기반 시스템

### 주요 특징
- **실시간 데이터**: ITS Open API를 통한 실시간 교통정보 수집
- **AI 예측**: XGBoost 기반 교통 속도 예측 모델
- **시각화**: 지도 기반 인터랙티브 UI
- **다중 데이터 소스**: 교통정보, CCTV, 안전정보 통합

---

## 아키텍처 다이어그램

### 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                         사용자 브라우저                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              프론트엔드 (Vanilla JavaScript)              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │  │
│  │  │  Leaflet   │  │  Chart.js  │  │   UI Components    │  │  │
│  │  │   (지도)    │  │  (차트)     │  │  (HTML/CSS/JS)     │  │  │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/HTTPS
                            │ REST API
┌───────────────────────────▼─────────────────────────────────────┐
│                      Node.js 서버 (Express)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API 라우터 계층                        │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐  │  │
│  │  │ Traffic │  │  CCTV   │  │  Safety │  │    AI     │  │  │
│  │  │   API   │  │   API   │  │   API   │  │   API     │  │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│  ┌─────────────────────────┼─────────────────────────────────┐ │
│  │      서비스 계층         │                                 │ │
│  │  ┌───────────────────┐  │  ┌────────────────────────┐    │ │
│  │  │ ITS API Connector │  │  │  Python AI 프로세스    │    │ │
│  │  │   (Axios + SSL)   │  │  │   (Child Process)      │    │ │
│  │  └───────────────────┘  │  └────────────────────────┘    │ │
│  └─────────────────────────┼─────────────────────────────────┘ │
└────────────────────────────┼───────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────────┐  ┌──────▼──────┐  ┌────────▼─────────┐
│  ITS Open API    │  │  Python AI   │  │  정적 데이터     │
│  - 교통속도       │  │  - XGBoost   │  │  - history.csv   │
│  - CCTV 영상     │  │  - scikit    │  │  - 취약구간.csv  │
│  - 돌발상황       │  │  - pandas    │  │                  │
│  - VMS           │  │              │  │                  │
└──────────────────┘  └──────────────┘  └──────────────────┘
```

---

## 기술 스택

### 프론트엔드
```
┌─────────────────────────────────────────┐
│           프론트엔드 레이어              │
├─────────────────────────────────────────┤
│ HTML5 + CSS3 + Vanilla JavaScript       │
├─────────────────────────────────────────┤
│ 라이브러리:                              │
│  - Leaflet.js v1.9.4 (지도)            │
│  - Chart.js v4.4.0 (차트)              │
│  - Pretendard (한글 폰트)              │
│  - Inter (숫자/영문 폰트)              │
└─────────────────────────────────────────┘
```

### 백엔드
```
┌─────────────────────────────────────────┐
│            백엔드 레이어                 │
├─────────────────────────────────────────┤
│ Node.js v14+ + Express.js v4.18        │
├─────────────────────────────────────────┤
│ 의존성:                                  │
│  - axios (HTTP 클라이언트)              │
│  - iconv-lite (인코딩 변환)            │
│  - https (SSL Agent)                   │
└─────────────────────────────────────────┘
```

### AI/ML
```
┌─────────────────────────────────────────┐
│            AI/ML 레이어                 │
├─────────────────────────────────────────┤
│ Python 3.7+                            │
├─────────────────────────────────────────┤
│ 라이브러리:                              │
│  - XGBoost v2.0+ (예측 모델)           │
│  - scikit-learn (전처리)               │
│  - pandas (데이터 처리)                │
│  - numpy (수치 연산)                   │
└─────────────────────────────────────────┘
```

---

## 데이터 플로우

### 1. 실시간 교통 정보 플로우

```
사용자 요청
    │
    ▼
[프론트엔드] 페이지 로드 → setInterval (30초마다)
    │
    ▼
GET /api/traffic
    │
    ▼
[백엔드] Express 라우터
    │
    ▼
Axios → ITS Open API (교통속도 조회)
    │         ↓
    │    HTTPS 요청 (SSL Agent)
    │         ↓
    │    EUC-KR → UTF-8 변환 (iconv-lite)
    │         ↓
    ▼    JSON 파싱
[백엔드] 응답 반환
    │
    ▼
[프론트엔드] 지도 업데이트 + UI 렌더링
```

### 2. AI 예측 플로우

```
사용자 CCTV 선택
    │
    ▼
GET /api/predict?id=섹션ID
    │
    ▼
[백엔드] Express 라우터
    │
    ▼
spawn Python 프로세스 → ai_server.py
    │                        ↓
    │                   history.csv 로드
    │                        ↓
    │                   XGBoost 모델 생성
    │                        ↓
    │                   요일/시간/섹션 입력
    │                        ↓
    │                   속도 예측 (km/h)
    │                        ↓
    │                   위험도 계산
    │                        ↓
    ▼                   JSON 출력
stdout 캡처 → JSON 파싱
    │
    ▼
[백엔드] 응답 반환
    │
    ▼
[프론트엔드] AI 분석 결과 표시
```

### 3. CCTV 스트리밍 플로우

```
사용자 CCTV 선택
    │
    ▼
GET /api/cctv/list
    │
    ▼
[백엔드] ITS API → CCTV 목록 조회
    │
    ▼
[프론트엔드] CCTV URL 받아서 <video> 태그에 삽입
    │
    ▼
브라우저 → ITS CCTV 서버 직접 스트리밍
    ↓
CORS 제한으로 일부 영상 재생 실패
```

---

## 컴포넌트 설명

### 1. 프론트엔드 컴포넌트

#### index.html
```
구조:
- <header>: 네비게이션 + 시계
- <main>
  ├── 홈 섹션: 현황 카드 + 차트
  ├── 교통 섹션: Leaflet 지도
  ├── CCTV 섹션: 비디오 + AI 분석
  └── 안전정보 섹션: 돌발상황 목록
- <footer>: 저작권 정보
```

#### script.js
```javascript
주요 함수:
- init(): 페이지 초기화
- loadTrafficData(): 교통 데이터 로드 (30초마다)
- loadCCTVList(): CCTV 목록 조회
- changeCCTV(): CCTV 변경 처리
- getAIPrediction(id): AI 예측 요청
- updateMap(): 지도 마커 업데이트
- updateChart(): Chart.js 업데이트
- loadWarnings(): 돌발상황 로드
```

#### style.css
```css
디자인 시스템:
- 색상: 검은색 (#000) + 흰색 (#FFF)
- 폰트: Pretendard (한글), Inter (숫자)
- 레이아웃: Flexbox + CSS Grid
- 반응형: @media 쿼리
```

### 2. 백엔드 컴포넌트

#### server.js
```javascript
Express 서버:

[정적 파일 서빙]
- app.use(express.static('public'))

[API 라우터]
- GET /api/traffic: 교통속도 조회
- GET /api/cctv/list: CCTV 목록
- GET /api/predict: AI 예측
- GET /api/warnings: 돌발상황
- GET /api/events: 이벤트
- GET /api/vms: VMS 전광판
- GET /api/dangerous: 위험물질 차량
- GET /api/vulnerable: 취약구간

[HTTPS Agent]
- SSL 인증서 검증 우회 (개발 환경)
```

#### ai_server.py
```python
XGBoost 예측 모델:

[입력]
- day_of_week: 요일 (0-6)
- hour: 시간대 (0-23)
- section_id: 구간 ID (0-2)

[처리]
1. history.csv 로드 (11,004건)
2. XGBoost 모델 학습
   - n_estimators=100
   - max_depth=5
   - learning_rate=0.1
3. 입력 데이터 예측
4. 위험도 계산 (정체/서행/원활)

[출력]
- JSON: { speed, risk, current_normal, ... }
```

---

## API 설계

### API 엔드포인트 상세

#### 1. GET /api/traffic
**설명**: 실시간 교통 속도 정보 조회

**요청**:
```http
GET /api/traffic HTTP/1.1
Host: localhost:3000
```

**응답**:
```json
{
  "success": true,
  "data": [
    {
      "routeId": "1010",
      "routeName": "경부고속도로",
      "speed": 95,
      "congestion": "원활",
      "startNode": "수원신갈IC",
      "endNode": "천안IC"
    }
  ]
}
```

#### 2. GET /api/predict?id={섹션ID}
**설명**: AI 기반 교통 예측

**요청**:
```http
GET /api/predict?id=2 HTTP/1.1
Host: localhost:3000
```

**파라미터**:
- `id` (number): 섹션 ID (0: 천안, 1: 입장, 2: 수원)

**응답**:
```json
{
  "status": "success",
  "speed": 85,
  "future_pred": 85,
  "risk": "원활",
  "current_normal": 92,
  "analysis": "평소보다 7km/h 느립니다"
}
```

#### 3. GET /api/cctv/list
**설명**: CCTV 목록 조회

**응답**:
```json
{
  "success": true,
  "list": [
    {
      "id": "C001",
      "name": "수원신갈IC",
      "url": "https://cctv.its.go.kr/...",
      "lat": 37.2833,
      "lng": 127.0522
    }
  ]
}
```

#### 4. GET /api/warnings
**설명**: 돌발상황 조회

**응답**:
```json
{
  "success": true,
  "list": [
    {
      "type": "주의",
      "msg": "차량 고장",
      "lat": 37.2500,
      "lng": 127.0800
    }
  ]
}
```

---

## 데이터베이스 구조

### CSV 파일 기반 데이터

#### history.csv
```
구조:
- 컬럼: 날짜, 시간, 구간, 속도, 교통량, 요일
- 레코드 수: 11,004건
- 용도: AI 모델 학습 데이터
```

```csv
날짜,시간,구간,속도,교통량,요일
2024-01-01,08:00,수원,45,250,월
2024-01-01,09:00,수원,62,180,월
...
```

#### 안개취약.csv
```
구조:
- 컬럼: 구간명, 위도, 경도, 위험도
- 용도: 안개 취약구간 표시
```

#### 행정안전부_상습 결빙구간.csv
```
구조:
- 컬럼: 도로명, 구간, 위도, 경도
- 용도: 결빙 취약구간 표시
```

---

## 배포 구조

### 개발 환경
```
로컬 개발 서버:
- Node.js: localhost:3000
- Python: Child Process로 실행
- 브라우저: http://localhost:3000
```

### 프로덕션 배포 (권장)
```
┌──────────────────────────────────────┐
│         CDN / 로드밸런서              │
│         (Cloudflare / AWS)           │
└────────────┬─────────────────────────┘
             │
┌────────────▼─────────────────────────┐
│       웹 서버 (Nginx/Apache)         │
│       - 정적 파일 서빙                │
│       - Reverse Proxy                │
└────────────┬─────────────────────────┘
             │
┌────────────▼─────────────────────────┐
│      Node.js 앱 서버 (PM2)           │
│      - Express 서버                  │
│      - 포트: 3000                    │
└────────────┬─────────────────────────┘
             │
┌────────────▼─────────────────────────┐
│      Python AI 서버                  │
│      - ai_server.py                  │
└──────────────────────────────────────┘
```

### 환경 변수 (권장)
```bash
# .env 파일
PORT=3000
ITS_API_KEY=your_api_key_here
NODE_ENV=production
PYTHON_PATH=/usr/bin/python3
```

---

## 성능 최적화

### 프론트엔드 최적화
- **Lazy Loading**: 섹션별 데이터 지연 로딩
- **Debouncing**: 지도 이동 시 API 요청 제한
- **Caching**: LocalStorage 활용 (CCTV 목록)

### 백엔드 최적화
- **Connection Pooling**: Keep-Alive 설정
- **Response Compression**: gzip 압축
- **Caching**: 메모리 캐시 (30초 TTL)

### AI 모델 최적화
- **모델 사전 로딩**: 서버 시작 시 모델 로드
- **배치 예측**: 여러 요청 묶어서 처리
- **경량 모델**: XGBoost (YOLOv8 제거)

---

## 보안

### 현재 구현된 보안
- HTTPS Agent (SSL 통신)
- CORS 정책 준수
- 환경 변수 분리 (API 키)

### 개선 필요 사항
- [ ] API Rate Limiting 추가
- [ ] JWT 인증 (관리자 기능)
- [ ] Input Validation 강화
- [ ] XSS/CSRF 방어
- [ ] SQL Injection 방어 (DB 도입 시)

---

## 모니터링 및 로깅

### 로깅 전략
```javascript
// 현재: console.log
console.log('API 요청:', endpoint);
console.error('에러 발생:', error);

// 권장: Winston 또는 Morgan
logger.info('API 요청', { endpoint, userId });
logger.error('에러 발생', { error, stack });
```

### 모니터링 (권장)
- **PM2**: 프로세스 관리 + 모니터링
- **New Relic**: APM 성능 모니터링
- **Sentry**: 에러 트래킹

---

## 확장성 고려사항

### 수평 확장 (Scale-Out)
```
┌─────────┐   ┌─────────┐   ┌─────────┐
│ Node.js │   │ Node.js │   │ Node.js │
│ Server1 │   │ Server2 │   │ Server3 │
└────┬────┘   └────┬────┘   └────┬────┘
     └─────────────┼─────────────┘
                   │
         ┌─────────▼──────────┐
         │   로드밸런서        │
         │   (Nginx/HAProxy)  │
         └────────────────────┘
```

### 수직 확장 (Scale-Up)
- CPU 코어 증가 → Node.js Cluster 모드
- 메모리 증가 → AI 모델 캐싱
- 디스크 I/O → SSD 사용

### 마이크로서비스 전환 (미래)
```
API Gateway
    ├── Traffic Service (교통정보)
    ├── AI Service (예측 모델)
    ├── CCTV Service (영상 스트리밍)
    └── Safety Service (안전정보)
```

---

## 트러블슈팅

### 일반적인 문제

#### 1. CCTV 영상 재생 안 됨
**원인**: ITS API CORS 정책
**해결**: 서버 사이드 프록시 구현

#### 2. AI 예측 느림
**원인**: Python 프로세스 매번 생성
**해결**: Python 서버를 별도 프로세스로 상시 실행

#### 3. 메모리 누수
**원인**: Interval 정리 안 됨
**해결**: 페이지 언마운트 시 clearInterval

---

## 참고 자료

### 공식 문서
- Node.js: https://nodejs.org/docs
- Express.js: https://expressjs.com
- XGBoost: https://xgboost.readthedocs.io
- Leaflet.js: https://leafletjs.com/reference.html

### API 문서
- ITS Open API: https://www.its.go.kr/openapi
- 공공데이터포털: https://www.data.go.kr

---

## 버전 히스토리

### v1.0.0 (현재)
- 실시간 교통 정보 조회
- AI 교통 예측 (XGBoost)
- CCTV 영상 스트리밍
- 안전정보 표시
- 지도 기반 UI

### 향후 계획
- v1.1.0: 모바일 반응형 개선
- v1.2.0: 실시간 알림 기능
- v2.0.0: LSTM 기반 고도화 AI 모델
- v2.1.0: 사용자 맞춤 경로 추천

---

마지막 업데이트: 2024
