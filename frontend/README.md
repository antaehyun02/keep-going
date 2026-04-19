# SkinAI — 안면부 피부질환 AI 분류 학습 플랫폼

> 피부과 전공의 · 의대생을 위한 안면부 피부질환 AI 분류 학습 및 실습 보조 플랫폼

---

## 프로젝트 소개

SkinAI는 안면부 피부질환 6종(건선, 아토피 피부염, 여드름, 주사, 지루성 피부염, 정상)을 대상으로 이미지를 업로드하면 AI가 질환을 분류하고, Claude API + RAG를 통해 감별진단 설명 및 학습 피드백을 제공하는 플랫폼입니다.

---

## 대상 질환 6종

| No | 질환명 (한글) | 질환명 (영문) |
|----|--------------|--------------|
| 1 | 건선 | Psoriasis |
| 2 | 아토피 피부염 | Atopic Dermatitis |
| 3 | 여드름 | Acne Vulgaris |
| 4 | 주사 | Rosacea |
| 5 | 지루성 피부염 | Seborrheic Dermatitis |
| 6 | 정상 | Normal |

---

## 프로젝트 구조

```
📁 skin_front/
├── 📄 README.md
│
├── 📁 AI analyze/
│   ├── 📄 guide
│   └── 📄 masking_guide.md          # 이미지 마스킹 & 저장 역할 분리 가이드
│
├── 📁 frontend/
│   └── 📁 src/
│       ├── 📄 login.html / login.js              # 로그인
│       ├── 📄 signup.html / signup.js            # 회원가입
│       ├── 📄 forgot_password.html / .js         # 비밀번호 찾기
│       ├── 📄 reset_password.html / .js          # 비밀번호 재설정
│       ├── 📄 dashboard.html / dashboard.js      # 메인 대시보드
│       ├── 📄 ai_analyze.html / ai_analyze.js    # 학습 AI - 이미지 분석
│       ├── 📄 my_analyze.html / my_analyze.js    # 내 분석 기록
│       ├── 📄 records.html                       # 학습 기록 조회
│       ├── 📄 record_detail.html / .js           # 학습 기록 상세
│       ├── 📄 community.html / community.js      # 학습 커뮤니티
│       ├── 📄 post_detail.html / post_detail.js  # 게시글 상세
│       ├── 📄 profile.html / profile.js          # 프로필
│       ├── 📄 withdraw.html / withdraw.js        # 회원 탈퇴
│       └── 📄 transition.js                      # 페이지 전환
│
└── 📁 SkinAi_DB/                                 # 백엔드 서버
    ├── 📄 server.js                              # 서버 진입점
    ├── 📄 .env                                   # 환경변수 (미공개)
    ├── 📄 .gitignore
    ├── 📄 package.json
    ├── 📁 config/
    │   └── 📄 supabase.js                        # Supabase 연결 설정
    ├── 📁 middleware/
    │   └── 📄 auth.js                            # JWT 인증 미들웨어
    └── 📁 routes/
        └── 📄 auth.js                            # 회원가입 / 로그인 API
```

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| Frontend | HTML5, CSS3, Vanilla JS |
| Backend | Node.js + Express |
| Database | Supabase (PostgreSQL) |
| 인증 | JWT (JSON Web Token) |
| 비밀번호 암호화 | bcrypt |
| AI 분석 | Claude API + RAG |
| 이미지 저장 | Supabase Storage |

---

## 시작하기

### 1. 저장소 클론

```bash
git clone https://github.com/habaekseo/skin_front.git
cd skin_front
```

### 2. 백엔드 패키지 설치

```bash
cd SkinAi_DB
npm install
```

### 3. 환경변수 설정

`SkinAi_DB/.env` 파일 생성 후 아래 내용 입력

```env
SUPABASE_URL=https://프로젝트ID.supabase.co
SUPABASE_KEY=anon_public_키
JWT_SECRET=skinai_secret_key_2025
PORT=3000
```

### 4. 서버 실행

```bash
node server.js
```

실행 성공 시
```
✅ 서버 실행 중 → http://localhost:3000
```

### 5. 프론트엔드 실행

VS Code에서 `frontend/src/login.html` 열고 Live Server로 실행

---

## API 명세

| Method | URL | 설명 |
|--------|-----|------|
| POST | /api/auth/signup | 회원가입 |
| POST | /api/auth/login | 로그인 |
| GET | /api/auth/check-email | 이메일 중복 확인 |

---

## 데이터베이스

Supabase (PostgreSQL) 사용

| 테이블 | 설명 |
|--------|------|
| users | 회원 정보 |
| analysis_records | AI 이미지 분석 기록 |

| Storage 버킷 | 설명 |
|-------------|------|
| skin-images | 마스킹 처리된 안면부 이미지 |
| conversations | Claude AI 대화 내용 |

---

## 화면 구성

| 화면 | 파일 | 설명 |
|------|------|------|
| 로그인 | login.html | 역할 선택 및 로그인 |
| 회원가입 | signup.html | 회원가입 폼 |
| 비밀번호 찾기 | forgot_password.html | 이메일로 재설정 링크 발송 |
| 대시보드 | dashboard.html | 학습 현황 요약 |
| 학습 AI | ai_analyze.html | 이미지 업로드 → AI 분류 결과 |
| 학습 기록 | records.html | 개인 학습 이력 및 통계 |
| 커뮤니티 | community.html | 케이스 공유 및 토론 |
| 프로필 | profile.html | 개인 정보 관리 |

---

## 개발 예정 기능

- [ ] 비밀번호 찾기 / 재설정 이메일 발송
- [ ] AI 이미지 분석 API 연동
- [ ] Claude API + RAG 대화 기능
- [ ] 학습 기록 대시보드
- [ ] 교수용 관리자 화면

---

## 라이선스

MIT License © 2025 SkinAI Team
