🚔 스마트 교통 AI 관제 시스템 (Smart Traffic AI Control System)
수원신갈IC ~ 천안IC 구간의 실시간 교통 상황을 모니터링하고, AI 기술을 활용하여 교통 흐름과 위험도를 예측하는 통합 관제 웹 플랫폼입니다. 국가교통정보센터(ITS)의 공공 데이터를 활용하며, Computer Vision 및 머신러닝 기술이 적용되었습니다.

✨ 주요 기능 (Key Features)
1. 📹 실시간 CCTV 모니터링
수원~천안 구간의 모든 고속도로 CCTV를 드롭다운 목록에서 선택하여 시청 가능.

검색 기능: "오산", "안성" 등 키워드 검색을 통해 원하는 CCTV를 즉시 필터링.

영상 로딩 실패 시 유튜브 백업 영상으로 자동 전환되는 Fail-over 시스템 구축.

2. 🧠 AI 기반 분석 (Python 연동)
속도 예측 (Prediction AI): 과거 주행 패턴 데이터를 기반으로 현재 시간대의 예상 속도와 정체 위험도(원활/서행/정체)를 분석.

객체 인식 (Vision AI): YOLOv8 모델을 활용하여 영상 내 차량(자동차, 버스, 트럭) 개수를 실시간으로 카운팅하여 혼잡도 판단.

3. 🗺️ GIS 기반 위치 관제 (Leaflet.js)
다중 레이어 지원: * 📷 CCTV: 카메라 위치 표시.

⚠️ 주의구간: 결빙, 안개, 사고 다발 구간 표시.

🚦 소통정보: 도로 흐름(원활/서행/정체)을 색상 점으로 시각화.

📟 VMS: 도로전광표지 위치 및 실시간 메시지 팝업 표시.

우측 상단 토글 스위치를 통해 원하는 정보만 선택적으로 조회 가능.

4. 🚨 실시간 돌발상황 알림
API를 통해 수집된 사고, 공사, 행사 정보를 실시간 로그 및 하단 테이블로 제공.

로그 클릭 시 해당 지도 위치로 자동 이동하여 신속한 상황 파악 가능.

🛠️ 기술 스택 (Tech Stack)
Frontend: HTML5, CSS3, JavaScript (Vanilla)

Library: Leaflet.js (지도), Chart.js (데이터 시각화)

Backend: Node.js (Express.js)

Role: API Proxy, Python 프로세스 관리, 데이터 전처리

AI & Data Analysis: Python 3.x

Library: Ultralytics (YOLOv8), OpenCV, Scikit-learn, Pandas, NumPy

Traffic-AI-Control/
├── public/                  # 프론트엔드 정적 파일
│   ├── index.html           # 메인 대시보드 화면
│   ├── script.js            # 프론트엔드 로직 (지도, 차트, API 호출)
│   └── style.css            # 스타일 시트 (다크/라이트 테마, 레이아웃)
├── data/                    # 데이터 폴더
│   ├── demo.mp4             # Vision AI 분석용 데모 영상 (필수)
│   └── *.csv                # (선택) 학습용 과거 데이터
├── server.js                # 메인 백엔드 서버 (Node.js)
├── ai_server.py             # 속도 예측 AI 모델
├── vision_server.py         # 차량 인식 Vision AI 모델
├── package.json             # Node.js 의존성 정보
└── README.md                # 프로젝트 설명서

Open API: ITS 국가교통정보센터 (CCTV, 돌발, VDS, VMS 정보)

네, 지금까지 개발한 **[수원~천안 구간 스마트 교통 AI 관제 시스템]**을 위한 완벽한 README.md 문서를 작성해 드립니다.

이 파일을 프로젝트 폴더 최상단에 README.md라는 이름으로 저장하시면 됩니다. 깃허브(GitHub)나 포트폴리오 제출 시 그대로 사용하셔도 손색없는 퀄리티입니다.

🚔 스마트 교통 AI 관제 시스템 (Smart Traffic AI Control System)
수원신갈IC ~ 천안IC 구간의 실시간 교통 상황을 모니터링하고, AI 기술을 활용하여 교통 흐름과 위험도를 예측하는 통합 관제 웹 플랫폼입니다. 국가교통정보센터(ITS)의 공공 데이터를 활용하며, Computer Vision 및 머신러닝 기술이 적용되었습니다.

✨ 주요 기능 (Key Features)
1. 📹 실시간 CCTV 모니터링
수원~천안 구간의 모든 고속도로 CCTV를 드롭다운 목록에서 선택하여 시청 가능.

검색 기능: "오산", "안성" 등 키워드 검색을 통해 원하는 CCTV를 즉시 필터링.

영상 로딩 실패 시 유튜브 백업 영상으로 자동 전환되는 Fail-over 시스템 구축.

2. 🧠 AI 기반 분석 (Python 연동)
속도 예측 (Prediction AI): 과거 주행 패턴 데이터를 기반으로 현재 시간대의 예상 속도와 정체 위험도(원활/서행/정체)를 분석.

객체 인식 (Vision AI): YOLOv8 모델을 활용하여 영상 내 차량(자동차, 버스, 트럭) 개수를 실시간으로 카운팅하여 혼잡도 판단.

3. 🗺️ GIS 기반 위치 관제 (Leaflet.js)
다중 레이어 지원: * 📷 CCTV: 카메라 위치 표시.

⚠️ 주의구간: 결빙, 안개, 사고 다발 구간 표시.

🚦 소통정보: 도로 흐름(원활/서행/정체)을 색상 점으로 시각화.

📟 VMS: 도로전광표지 위치 및 실시간 메시지 팝업 표시.

우측 상단 토글 스위치를 통해 원하는 정보만 선택적으로 조회 가능.

4. 🚨 실시간 돌발상황 알림
API를 통해 수집된 사고, 공사, 행사 정보를 실시간 로그 및 하단 테이블로 제공.

로그 클릭 시 해당 지도 위치로 자동 이동하여 신속한 상황 파악 가능.

🛠️ 기술 스택 (Tech Stack)
Frontend: HTML5, CSS3, JavaScript (Vanilla)

Library: Leaflet.js (지도), Chart.js (데이터 시각화)

Backend: Node.js (Express.js)

Role: API Proxy, Python 프로세스 관리, 데이터 전처리

AI & Data Analysis: Python 3.x

Library: Ultralytics (YOLOv8), OpenCV, Scikit-learn, Pandas, NumPy

Open API: ITS 국가교통정보센터 (CCTV, 돌발, VDS, VMS 정보)

📂 프로젝트 구조 (Directory Structure)
Bash

Traffic-AI-Control/
├── public/                  # 프론트엔드 정적 파일
│   ├── index.html           # 메인 대시보드 화면
│   ├── script.js            # 프론트엔드 로직 (지도, 차트, API 호출)
│   └── style.css            # 스타일 시트 (다크/라이트 테마, 레이아웃)
├── data/                    # 데이터 폴더
│   ├── demo.mp4             # Vision AI 분석용 데모 영상 (필수)
│   └── *.csv                # (선택) 학습용 과거 데이터
├── server.js                # 메인 백엔드 서버 (Node.js)
├── ai_server.py             # 속도 예측 AI 모델
├── vision_server.py         # 차량 인식 Vision AI 모델
├── package.json             # Node.js 의존성 정보
└── README.md                # 프로젝트 설명서
🚀 설치 및 실행 방법 (Installation & Usage)
1. 필수 프로그램 설치
이 프로젝트를 실행하려면 컴퓨터에 다음 프로그램들이 설치되어 있어야 합니다.

Node.js (v14 이상 권장)

Python (3.8 이상 권장)

2. 프로젝트 다운로드 및 설정
터미널(CMD, PowerShell, VS Code 터미널)을 열고 다음 명령어들을 순서대로 입력하세요.

1) Node.js 패키지 설치
npm init -y
npm install express axios

2) Python 라이브러리 설치
pip install pandas scikit-learn numpy ultralytics opencv-python

3. 서버 실행
node server.js

4. 접속
웹 브라우저를 열고 다음 주소로 접속하세요. 👉 http://localhost:3000

📜 라이선스 및 출처
데이터 출처: 국가교통정보센터(ITS) Open API

지도 데이터: © OpenStreetMap contributors

개발: [안태현]


