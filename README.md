# 🚔 스마트 교통 AI 관제 시스템 (Smart Traffic AI Control)

![Project Status](https://img.shields.io/badge/Project-Active-green) ![License](https://img.shields.io/badge/License-MIT-blue)

**수원신갈IC ~ 천안IC (경부고속도로)** 구간의 실시간 교통 데이터를 수집하고, **3개월치 빅데이터를 학습한 AI**와 비교 분석하여 **교통 흐름의 이상 징후(사고/정체)**를 능동적으로 감지하는 지능형 웹 관제 플랫폼입니다.

---

## ✨ 핵심 기능 (Key Features)

### 1. 🧠 AI 기반 이상 징후 감지 (Anomaly Detection)
* **평소 패턴 vs 실시간 비교:** AI가 학습한 '해당 요일/시간의 평소 속도'와 '현재 실시간 속도'를 실시간으로 비교 분석합니다.
* **괴리율 분석:** 평소에는 원활해야 할 구간에서 급격한 속도 저하가 발생할 경우, 단순 정체가 아닌 **"사고 및 돌발 상황"**으로 판단하여 즉시 **🚨[이상 징후]** 경고 알림을 발생시킵니다.

### 2. 📈 향후 12시간 교통 흐름 예보
* **XGBoost 시계열 예측:** 2025년 8월~10월(3개월) 과거 데이터를 기반으로 학습된 머신러닝 모델이 현재 시점부터 **향후 12시간의 교통 흐름**을 예측합니다.
* **시각화:** 대시보드 하단에 막대그래프를 통해 시간대별 예상 혼잡도(원활/서행/정체)를 색상으로 구분하여 직관적으로 제공합니다.

### 3. 📹 실시간 CCTV 모니터링
* **ITS 공공데이터 연동:** 국가교통정보센터(ITS) API를 통해 수원~천안 구간의 고화질 CCTV 영상을 실시간으로 스트리밍합니다.
* **안정성 확보:** 호환성이 가장 뛰어난 MP4 방식을 적용하여 끊김 없는 영상 재생 환경을 제공합니다.

### 4. 🗺️ GIS 기반 통합 관제 대시보드
* **인터랙티브 맵:** `Leaflet.js`를 활용하여 CCTV 위치, 소통 정보(색상 점), 공사/사고 구간 등을 지도 위에 레이어로 시각화합니다.
* **AI 분석 패널:** 현재 관제 중인 구간의 **"AI 평소 패턴"**과 **"실시간 데이터"**를 한눈에 비교할 수 있는 전용 패널을 제공합니다.

---

## 🛠️ 기술 스택 (Tech Stack)

| 분류 | 기술 |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (Vanilla), Leaflet.js, Chart.js |
| **Backend** | Node.js (Express), Axios, Child Process |
| **AI / Data** | Python (Pandas, **XGBoost**, Scikit-learn, NumPy) |
| **API** | 국가교통정보센터 (ITS) Open API |

---

## 📂 프로젝트 구조 (Directory Structure)

```bash
Traffic-AI-Control/
├── public/                  # 프론트엔드 정적 파일
│   ├── index.html           # 메인 대시보드 (AI 패널 & 예보 차트 포함)
│   ├── script.js            # 클라이언트 로직 (이상 탐지, API 호출)
│   └── style.css            # 스타일 시트
├── data/                    # 데이터 폴더
│   ├── data_8.csv...        # 월별 원본 데이터 (8, 9, 10월)
│   └── history.csv          # 전처리 완료된 AI 학습용 통합 데이터
├── server.js                # 메인 백엔드 서버 (Node.js)
├── ai_server.py             # 속도 예측 및 이상 탐지 AI 모델 (XGBoost)
├── preprocess_all.py        # 데이터 전처리 및 통합 스크립트
└── README.md                # 프로젝트 설명서
```
## 🚀 설치 및 실행 (Getting Started)

### 1. 필수 요구사항
이 프로젝트를 실행하려면 다음 프로그램이 설치되어 있어야 합니다.
* **Node.js** (v14 이상)
* **Python** (3.8 이상)

### 2. 패키지 설치
터미널을 열고 다음 명령어를 순서대로 입력하세요.

# 1. Node.js 의존성 설치
```
npm init -y
npm install express axios
```

# 2. Python 라이브러리 설치
```
pip install pandas scikit-learn numpy ultralytics opencv-python
```

실행
```
node server.js
```

5. 접속
브라우저를 열고 아래 주소로 접속하세요.

http://localhost:3000

---
📊 데이터 출처
ITS 국가교통정보센터: 실시간 CCTV 영상 및 소통정보 API

한국도로공사 공공데이터포털: 과거 고속도로 통행 속도 데이터 (2025년 8~10월)
