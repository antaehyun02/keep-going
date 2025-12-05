# 경부고속도로 실시간 교통정보 시스템

경부고속도로 수원-천안 구간의 실시간 교통 상황을 모니터링하고 AI 기반 예측을 제공하는 웹 애플리케이션입니다.

## 주요 기능

### 1. 실시간 교통 모니터링
- 수원-천안 구간의 실시간 교통 속도 정보
- Leaflet 기반 인터랙티브 지도 표시
- 구간별 소통 상태 (원활/서행/정체) 시각화

### 2. AI 교통 예측
- XGBoost 머신러닝 모델을 활용한 교통 속도 예측
- 11,004개의 실제 교통 데이터로 학습
- 요일 및 시간대별 패턴 분석
- 향후 12시간 교통 상황 예측

### 3. 실시간 CCTV
- ITS Open API를 통한 실시간 CCTV 영상 스트리밍
- 지도상에서 CCTV 위치 확인
- 구간별 CCTV 검색 기능

### 4. 안전정보 제공
- 실시간 돌발 상황 알림
- 위험물질 운송차량 위치 정보
- 취약구간 정보 (안개/결빙 구간)
- VMS 전광판 메시지 표시

## 기술 스택

### Backend
- **Node.js** + **Express.js** - 서버 프레임워크
- **Python 3.x** - AI 모델 실행
- **Axios** - HTTP 클라이언트
- **iconv-lite** - EUC-KR 인코딩 처리

### Frontend
- **Vanilla JavaScript** - 프론트엔드 로직
- **Leaflet.js** - 지도 라이브러리
- **Chart.js** - 데이터 시각화
- **Pretendard & Inter** - 폰트

### AI/ML
- **XGBoost** - 교통 예측 모델
- **scikit-learn** - 데이터 전처리
- **pandas** - 데이터 처리

### Data Source
- **ITS Open API** - 실시간 교통정보
- **행정안전부 공공데이터** - 취약구간 정보

## 프로젝트 구조

```
cctv-display/
├── server.js                          # Express 서버
├── ai_server.py                       # AI 교통 예측 서버
├── package.json                       # Node.js 의존성
├── data/
│   ├── history.csv                    # 교통 데이터 (11,004건)
│   ├── 안개취약.csv                   # 안개 취약구간
│   └── 행정안전부_상습 결빙구간.csv    # 결빙 취약구간
└── public/
    ├── index.html                     # 메인 HTML
    ├── script.js                      # 프론트엔드 로직
    └── style.css                      # 스타일시트
```

## 설치 및 실행

### 1. 필수 요구사항
- Node.js 14.x 이상
- Python 3.7 이상
- npm 또는 yarn

### 2. 의존성 설치

**Node.js 패키지 설치:**
```bash
npm install
```

**Python 패키지 설치:**
```bash
pip install xgboost scikit-learn pandas numpy
```

### 3. 환경 설정

`server.js` 파일에서 ITS Open API 키를 설정하세요:
```javascript
const MY_API_KEY = "YOUR_API_KEY_HERE";
```

### 4. 서버 실행

```bash
node server.js
```

서버가 정상적으로 실행되면:
```
🚀 시스템 정상 가동: http://localhost:3000
```

### 5. 브라우저 접속

웹 브라우저에서 `http://localhost:3000` 접속

## API 엔드포인트

### 교통 정보
- `GET /api/cctv/list` - CCTV 목록 조회
- `GET /api/traffic` - 실시간 교통 속도
- `GET /api/predict?id={섹션ID}` - AI 교통 예측

### 안전 정보
- `GET /api/warnings` - 돌발 상황 정보
- `GET /api/events` - 이벤트 정보
- `GET /api/dangerous` - 위험물질 차량 정보
- `GET /api/vulnerable` - 취약구간 정보
- `GET /api/vms` - VMS 전광판 정보

## AI 모델 상세

### XGBoost 교통 예측 모델
- **학습 데이터**: 11,004건의 실제 교통 데이터
- **입력 변수**: 요일, 시간대, 구간 ID
- **출력**: 1시간 후 예상 속도 (km/h)
- **모델 파라미터**:
  - n_estimators: 100
  - max_depth: 5
  - learning_rate: 0.1

### 예측 정확도
- 평균 정확도: 60-70%
- 출퇴근 시간대 패턴 반영
- 구간별 특성 고려

## 데이터 소스

### ITS Open API
- CCTV 영상 스트리밍
- 실시간 교통 속도
- 돌발 상황 정보
- VMS 전광판 메시지

### 공공데이터포털
- 안개 취약구간 (행정안전부)
- 결빙 취약구간 (행정안전부)

## 주요 섹션

### 🏠 홈
- 현재 도로 상황 요약
- 예상 소요시간
- 도로 안전 지수
- AI 교통 예측 차트

### 🚗 실시간 교통
- 인터랙티브 지도
- 구간별 소통 상태
- 실시간 속도 정보

### 📹 CCTV
- 실시간 CCTV 영상
- AI 분석 결과
- 평소 패턴 비교

### ⚠️ 안전정보
- 돌발 상황
- 위험물질 차량
- 취약구간 정보

## 브라우저 지원

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+


## 개발자

경부고속도로 교통정보 시스템 | AI 기반 실시간 분석


