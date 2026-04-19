# SkinAI — 데이터베이스 구축 및 실행 가이드

> 안면부 피부질환 AI 분류 학습 플랫폼 — DB 구축부터 회원가입 연동까지

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| DB 플랫폼 | Supabase (PostgreSQL) |
| 백엔드 | Node.js + Express |
| 인증 | JWT (JSON Web Token) |
| 비밀번호 암호화 | bcrypt |

---

## 전체 흐름

```
[프론트엔드]          [백엔드 서버]            [Supabase DB]
signup.html   →   /api/auth/signup     →   users 테이블 저장
login.html    →   /api/auth/login      →   users 테이블 조회
```

---

## 프로젝트 구조

```
📁 SkinAi_DB/
├── 📁 config/
│   └── 📄 supabase.js       # Supabase 연결 설정
├── 📁 middleware/
│   └── 📄 auth.js           # JWT 인증 미들웨어
├── 📁 node_modules/
├── 📁 routes/
│   └── 📄 auth.js           # 회원가입 / 로그인 API
├── 📄 .env                  # 환경변수 (Supabase 키, JWT 시크릿)
├── 📄 .gitignore            # Git 제외 파일
├── 📄 package.json
├── 📄 package-lock.json
└── 📄 server.js             # 서버 진입점
```

---

## Supabase DB 구축

### 1. Supabase 프로젝트 생성
1. [supabase.com](https://supabase.com) 접속 후 로그인
2. New Project 클릭 → 프로젝트 생성

### 2. SQL Editor에서 아래 스크립트 실행
Supabase 대시보드 → SQL Editor → New query → 아래 코드 붙여넣고 Run

```sql
-- ENUM 타입
CREATE TYPE user_role AS ENUM ('resident', 'student', 'professor');
CREATE TYPE analysis_status AS ENUM ('pending', 'completed', 'failed');

-- users 테이블
CREATE TABLE users (
  user_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  name             VARCHAR(20)  NOT NULL,
  email            VARCHAR(100) NOT NULL UNIQUE,
  password_hash    TEXT         NOT NULL,
  role             user_role    NOT NULL,
  affiliation      VARCHAR(50)  NOT NULL,
  year             VARCHAR(10),
  created_at       TIMESTAMP    NOT NULL DEFAULT now(),
  updated_at       TIMESTAMP    NOT NULL DEFAULT now()
);

-- analysis_records 테이블
CREATE TABLE analysis_records (
  record_id          UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            UUID             NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  image_url          TEXT             NOT NULL,
  image_filename     VARCHAR(100)     NOT NULL,
  is_masked          BOOLEAN          NOT NULL DEFAULT true,
  primary_diagnosis  VARCHAR(100),
  confidence         FLOAT            CHECK (confidence >= 0.0 AND confidence <= 1.0),
  differential       JSONB,
  ai_findings        TEXT,
  user_answer        VARCHAR(100),
  is_correct         BOOLEAN,
  conversation_url   TEXT,
  status             analysis_status  NOT NULL DEFAULT 'pending',
  created_at         TIMESTAMP        NOT NULL DEFAULT now()
);

-- 인덱스
CREATE INDEX idx_analysis_user_id ON analysis_records(user_id);
CREATE INDEX idx_analysis_status  ON analysis_records(status);
CREATE INDEX idx_analysis_created ON analysis_records(created_at DESC);

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Storage 버킷
INSERT INTO storage.buckets (id, name, public)
VALUES ('skin-images', 'skin-images', false);

INSERT INTO storage.buckets (id, name, public)
VALUES ('conversations', 'conversations', false);
```

---

## 백엔드 서버 세팅

### 1. 패키지 설치

```bash
npm install express @supabase/supabase-js bcryptjs jsonwebtoken dotenv cors
```

### 2. 환경변수 설정

`.env` 파일에 아래 내용 입력

```env
SUPABASE_URL=https://hrihwlhbgjlbqpxexuaz.supabase.co
SUPABASE_KEY=sb_publishable_VKLZT4fzayA5iVYF1hwGVQ_qwFGwRmX
JWT_SECRET=skinai_secret_key_2025
PORT=3000
```

> ⚠️ `.env` 파일은 `.gitignore`에 포함되어 있어 GitHub에 업로드되지 않습니다.

Supabase 대시보드
```
https://supabase.com/dashboard/project/hrihwlhbgjlbqpxexuaz/settings/api
```

### 3. .gitignore 설정

`.gitignore` 파일에 아래 내용 입력 (GitHub에 키 노출 방지)

```
node_modules/
.env
```

---

## API 명세

### 회원가입
| 항목 | 내용 |
|------|------|
| Method | POST |
| URL | /api/auth/signup |
| Body | name, email, password, role, affiliation, year |
| 성공 응답 | 201 + token + user 정보 |
| 실패 응답 | 409 (이메일 중복) / 400 (필수값 누락) |

### 이메일 중복 확인
| 항목 | 내용 |
|------|------|
| Method | GET |
| URL | /api/auth/check-email?email= |
| 성공 응답 | { exists: true/false } |

### 로그인
| 항목 | 내용 |
|------|------|
| Method | POST |
| URL | /api/auth/login |
| Body | email, password |
| 성공 응답 | 200 + token + user 정보 |
| 실패 응답 | 401 (이메일/비밀번호 불일치) |

---

## 서버 실행

```bash
node server.js
```

실행 성공 시
```
✅ 서버 실행 중 → http://localhost:3000
```

브라우저에서 확인
```
http://localhost:3000
→ { "message": "SkinAI 서버 정상 작동 중 🟢" }
```

---

## 프론트엔드 연동

`signup.js`, `login.js` 에서 API 주소 설정

```javascript
// 개발 환경 (현재)
const API_BASE = 'http://localhost:3000';

// 엔드포인트
POST http://localhost:3000/api/auth/signup
POST http://localhost:3000/api/auth/login
GET  http://localhost:3000/api/auth/check-email?email=

// 서버 상태 확인
GET  http://localhost:3000
→ { "message": "SkinAI 서버 정상 작동 중 🟢" }

// 배포 환경 (추후)
https://yourdomain.com/api/auth/signup
https://yourdomain.com/api/auth/login
https://yourdomain.com/api/auth/check-email
```

---

## 동작 확인

회원가입 성공 후 Supabase에서 데이터 확인

```
Supabase 대시보드
→ Table Editor
→ users 테이블
→ 가입한 데이터 확인
  - user_id: UUID 자동 생성
  - password_hash: bcrypt 해시값 ($2b$10$...)
  - created_at: 가입 시간 자동 저장
```

---

## 완료 체크리스트

- [x] Supabase 프로젝트 생성
- [x] users 테이블 생성
- [x] analysis_records 테이블 생성
- [x] Storage 버킷 생성 (skin-images, conversations)
- [x] Node.js + Express 서버 세팅
- [x] 환경변수 (.env) 설정
- [x] 회원가입 API 구현 및 DB 연동 확인
- [x] 비밀번호 bcrypt 해시 저장 확인
- [x] JWT 토큰 발급 확인
- [ ] 로그인 API 연동 확인
- [ ] 이미지 분석 API 연동 (추후)
