# 🚔 스마트 교통 AI 관제 시스템 (Smart Traffic AI Control)

**수원신갈IC ~ 천안IC** 구간의 고속도로 CCTV 영상을 실시간으로 분석하여 교통 흐름, 돌발 상황, 위험도를 시각화하는 지능형 웹 관제 플랫폼입니다. ITS 공공 데이터와 YOLOv8 Vision AI 기술을 융합하여 개발되었습니다.

---

## ✨ 주요 기능 (Key Features)

* **📹 실시간 CCTV 모니터링**
    * 수원~천안 구간 내 경부고속도로 CCTV 전체 조회 및 검색 기능.
    * 영상 로딩 실패 시 유튜브 백업 영상 자동 전환 (Fail-over).

* **🧠 AI 기반 정밀 분석**
    * **속도 예측 (AI Prediction):** 과거 데이터 기반 구간별 예상 속도 및 혼잡도(원활/서행/정체) 분석.
    * **객체 인식 (Vision AI):** YOLOv8 모델을 활용하여 영상 내 차량(승용차, 버스, 트럭) 실시간 카운팅.

* **🗺️ GIS 기반 통합 관제**
    * **다중 레이어 지원:** 소통정보(색상), VMS(전광판), 주의구간(결빙/안개) 시각화.
    * **인터랙티브 맵:** 마커 클릭 시 세부 정보 팝업 및 해당 CCTV 자동 연결.
    * **제어 스위치:** 지도 정보를 원하는 대로 ON/OFF 가능.

* **🚨 실시간 돌발 알림**
    * 사고, 공사, 행사 등 돌발 상황 실시간 로그 및 하단 상세 리스트 제공.
    * 로그 클릭 시 해당 위치로 지도 자동 이동.

---

## 🛠️ 기술 스택 (Tech Stack)

| 분류 | 기술 |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (Vanilla), Leaflet.js, Chart.js |
| **Backend** | Node.js (Express), Axios |
| **AI / Data** | Python (OpenCV, YOLOv8, Scikit-learn, Pandas) |
| **API** | 국가교통정보센터 (ITS) Open API |

---

## 📂 프로젝트 구조 (Directory Structure)

```bash
Traffic-AI-Control/
├── public/                  # 프론트엔드 정적 파일
│   ├── index.html           # 메인 대시보드 화면
│   ├── script.js            # 클라이언트 로직 (지도, 차트, API 호출)
│   └── style.css            # 스타일 시트
├── data/                    # 데이터 폴더
│   ├── demo.mp4             # Vision AI 분석용 데모 영상 (필수)
│   └── *.csv                # 학습용 데이터
├── server.js                # 메인 백엔드 서버 (Node.js)
├── ai_server.py             # 속도 예측 AI 모델
├── vision_server.py         # 객체 인식 Vision AI 모델
└── README.md                # 프로젝트 설명서```bash

## 🚀 설치 및 실행 (Getting Started)

### 1. 필수 요구사항
이 프로젝트를 실행하려면 다음 프로그램이 설치되어 있어야 합니다.
* **Node.js** (v14 이상)
* **Python** (3.8 이상)

### 2. 패키지 설치
터미널을 열고 다음 명령어를 순서대로 입력하세요.

bash
# 1. Node.js 의존성 설치
```bashnpm init -y
npm install express axios```bash

# 2. Python 라이브러리 설치
```bashpip install pandas scikit-learn numpy ultralytics opencv-python```bash

실행
```bashnode server.js```bash

5. 접속
브라우저를 열고 아래 주소로 접속하세요.

http://localhost:3000

