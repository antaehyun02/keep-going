# SkinAI 시스템 아키텍처

## 개요

SkinAI는 **마이크로서비스 아키텍처** 기반의 피부 건강 관리 플랫폼입니다. Node.js Express 백엔드와 Flask AI 서비스가 독립적으로 운영되며, PostgreSQL 데이터베이스로 데이터를 영속적으로 관리합니다.

### 핵심 특징

#### 마이크로서비스 아키텍처
- **Node.js Backend** (:3000) - 사용자 인증, 게시판, AI 분석 요청 관리
- **Flask AI Service** (:5000) - PyTorch 모델 기반 피부 질환 예측
- **PostgreSQL Database** (:5432) - 영속적인 데이터 저장
- **독립적 배포 및 확장** - 각 서비스를 독립적으로 배포 가능

#### 강력한 보안
- **JWT 인증** - 토큰 기반 무상태 인증
- **Bcrypt 해싱** - 안전한 비밀번호 저장 (10 salt rounds)
- **Rate Limiting** - API 남용 방지 (분당 100회 제한)
- **입력 검증** - express-validator로 모든 입력값 검증

#### AI 피부 분석
- **PyTorch 딥러닝** - ResNet50, EfficientNet-B3 모델
- **50가지 피부 질환 분류** - SCIN 데이터셋 (10,407 이미지)
- **Top-5 예측** - 신뢰도 점수와 함께 상위 5개 질환 예측
- **Fallback 시스템** - Flask 서비스 다운 시 규칙 기반 분석 제공

#### 데이터 영속성
- **PostgreSQL** - 관계형 데이터베이스로 데이터 안전 보관
- **외래 키 제약조건** - CASCADE로 데이터 무결성 보장
- **JSONB 타입** - AI 분석 결과 유연하게 저장
- **트랜잭션 관리** - 데이터 일관성 보장

## 시스템 아키텍처 다이어그램

### 전체 시스템 구조 (마이크로서비스 아키텍처)

#### High-Level Architecture
```mermaid
graph LR
    USER["<b>사용자</b><br/>웹 브라우저"]

    FE["<b>프론트엔드</b><br/>HTML/CSS/JS<br/>Local Storage"]

    BACKEND["<b>Node.js Backend</b><br/>Port 3000<br/>Express + JWT<br/>미들웨어"]

    AI["<b>Flask AI Service</b><br/>Port 5000<br/>PyTorch<br/>ResNet50"]

    DB["<b>PostgreSQL</b><br/>Port 5432"]

    FS["<b>File System</b><br/>이미지 저장소<br/>/uploads/"]

    %% 데이터 흐름
    USER -->|HTTP/HTTPS| FE
    FE -->|REST API<br/>Bearer Token| BACKEND
    BACKEND -->|SQL Query| DB
    BACKEND -->|HTTP POST<br/>/predict| AI
    BACKEND -->|파일 저장| FS
    AI -->|이미지 로드| FS

    %% 스타일
    classDef userClass fill:#42A5F5,stroke:#0D47A1,stroke-width:4px,color:#000
    classDef frontClass fill:#81D4FA,stroke:#01579B,stroke-width:4px,color:#000
    classDef backClass fill:#FFB74D,stroke:#E65100,stroke-width:4px,color:#000
    classDef aiClass fill:#CE93D8,stroke:#4A148C,stroke-width:4px,color:#000
    classDef dataClass fill:#81C784,stroke:#1B5E20,stroke-width:4px,color:#000

    class USER userClass
    class FE frontClass
    class BACKEND backClass
    class AI aiClass
    class DB,FS dataClass
```

#### Detailed System Components
```mermaid
graph TB
    subgraph LAYER1["Presentation Layer"]
        direction LR
        UI1["로그인/회원가입"]
        UI2["게시판 CRUD"]
        UI3["AI 피부 분석"]
        UI4["프로필 관리"]
    end

    subgraph LAYER2["Security Layer"]
        direction LR
        SEC1["JWT 인증"]
        SEC2["Rate Limiting"]
        SEC3["입력값 검증"]
    end

    subgraph LAYER3["Application Layer"]
        direction LR
        APP1["인증 API<br/>/api/auth"]
        APP2["게시판 API<br/>/api/board"]
        APP3["AI API<br/>/api/ai"]
    end

    subgraph LAYER4["AI Service Layer"]
        direction LR
        AI1["Flask API<br/>:5000"]
        AI2["PyTorch 모델<br/>ResNet50"]
        AI3["추론 엔진<br/>Top-5 예측"]
    end

    subgraph LAYER5["Data Layer"]
        direction LR
        DATA1["PostgreSQL<br/>users, posts<br/>comments"]
        DATA2["File System<br/>이미지 저장"]
    end

    LAYER1 --> LAYER2
    LAYER2 --> LAYER3
    LAYER3 --> LAYER4
    LAYER3 --> LAYER5
    LAYER4 --> LAYER5

    style LAYER1 fill:#42A5F5,stroke:#0D47A1,stroke-width:3px,color:#000
    style LAYER2 fill:#FFF176,stroke:#F57F17,stroke-width:3px,color:#000
    style LAYER3 fill:#FFB74D,stroke:#E65100,stroke-width:3px,color:#000
    style LAYER4 fill:#CE93D8,stroke:#4A148C,stroke-width:3px,color:#000
    style LAYER5 fill:#81C784,stroke:#1B5E20,stroke-width:3px,color:#000
```

### 시스템 레이어 구조
```mermaid
graph LR
    subgraph "Layer 1: Presentation"
        UI["웹 브라우저<br/>HTML/CSS/JS"]
    end

    subgraph "Layer 2: Application"
        API["Express API<br/>:3000"]
        AI["Flask AI<br/>:5000"]
    end

    subgraph "Layer 3: Business Logic"
        AUTH["인증/인가"]
        BOARD["게시판"]
        ANALYSIS["AI 분석"]
    end

    subgraph "Layer 4: Data"
        DB["Local Storage"]
        FS["File System"]
    end

    UI --> API
    API --> AI
    API --> AUTH
    API --> BOARD
    API --> ANALYSIS
    AUTH --> DB
    BOARD --> DB
    ANALYSIS --> AI
    AI --> DB
    API --> FS
    AI --> FS

    style UI fill:#42A5F5,stroke:#01579B,stroke-width:2px
    style API fill:#FFB74D,color:#000,stroke:#EF6C00,stroke-width:2px
    style AI fill:#CE93D8,stroke:#4A148C,stroke-width:2px
    style AUTH fill:#FFF176,color:#000,stroke:#F57F17,stroke-width:2px
    style BOARD fill:#FFF176,stroke:#F57F17,stroke-width:2px
    style ANALYSIS fill:#FFF176,color:#000,stroke:#F57F17,stroke-width:2px
    style DB fill:#81C784,stroke:#1B5E20,stroke-width:2px
    style FS fill:#81C784,color:#000,stroke:#1B5E20,stroke-width:2px
```

### 상세 계층 구조

#### 1. 클라이언트 계층
```mermaid
graph TB
    subgraph PAGES["프론트엔드 페이지"]
        direction LR
        AUTH["<b>인증</b><br/>로그인<br/>회원가입"]
        BOARD["<b>게시판</b><br/>목록<br/>상세<br/>작성"]
        AI["<b>AI 분석</b><br/>업로드<br/>설문<br/>결과"]
        PROFILE["<b>프로필</b><br/>내정보<br/>내글<br/>내댓글"]
    end
    
    NAV["<b>공통 네비게이션</b><br/>common-nav.js"]
    STORAGE["<b>Local Storage</b><br/>JWT Token<br/>User Info"]
    
    NAV --> PAGES
    PAGES --> STORAGE

    style PAGES fill:#42A5F5,stroke:#01579B,stroke-width:2px,color:#000
    style AUTH fill:#81D4FA,stroke:#01579B,stroke-width:2px,color:#000
    style BOARD fill:#81D4FA,stroke:#01579B,stroke-width:2px,color:#000
    style AI fill:#81D4FA,stroke:#01579B,stroke-width:2px,color:#000
    style PROFILE fill:#81D4FA,stroke:#01579B,stroke-width:2px,color:#000
    style NAV fill:#42A5F5,stroke:#01579B,stroke-width:2px,color:#000
    style STORAGE fill:#42A5F5,stroke:#01579B,stroke-width:2px,color:#000
```

#### 2. 서버 계층
```mermaid
graph TB
    subgraph MW["미들웨어"]
        direction LR
        AUTH_MW["<b>JWT 인증</b><br/>auth.js"]
        RATE["<b>Rate Limiter</b><br/>분당 100회"]
        VALID["<b>Validator</b><br/>입력값 검증"]
    end

    subgraph API["API 라우터"]
        direction LR
        AUTH_API["<b>인증 API</b><br/>/api/auth/*"]
        BOARD_API["<b>게시판 API</b><br/>/api/board/*"]
        AI_API["<b>AI API</b><br/>/api/ai/*"]
    end

    subgraph LOGIC["비즈니스 로직"]
        direction LR
        USER_LOGIC["<b>사용자 관리</b><br/>회원가입<br/>로그인<br/>프로필"]
        BOARD_LOGIC["<b>게시판 관리</b><br/>CRUD<br/>좋아요<br/>댓글"]
        AI_LOGIC["<b>AI 분석</b><br/>이미지 업로드<br/>설문조사<br/>분석 엔진"]
    end

    MW --> API --> LOGIC

    style MW fill:#FFE0B2,stroke:#EF6C00,stroke-width:2px,color:#000
    style API fill:#FFB74D,stroke:#EF6C00,stroke-width:2px,color:#000
    style LOGIC fill:#FFB74D,stroke:#EF6C00,stroke-width:2px,color:#000
    
    style AUTH_MW fill:#FFD54F,stroke:#EF6C00,stroke-width:2px,color:#000
    style RATE fill:#FFD54F,stroke:#EF6C00,stroke-width:2px,color:#000
    style VALID fill:#FFD54F,stroke:#EF6C00,stroke-width:2px,color:#000
    style AUTH_API fill:#FFA000,stroke:#EF6C00,stroke-width:2px,color:#000
    style BOARD_API fill:#FFA000,stroke:#EF6C00,stroke-width:2px,color:#000
    style AI_API fill:#FFA000,stroke:#EF6C00,stroke-width:2px,color:#000
    style USER_LOGIC fill:#FFA000,stroke:#EF6C00,stroke-width:2px,color:#000
    style BOARD_LOGIC fill:#FFA000,stroke:#EF6C00,stroke-width:2px,color:#000
    style AI_LOGIC fill:#FFA000,stroke:#EF6C00,stroke-width:2px,color:#000
```

#### 3. 데이터 계층

**데이터베이스 ER 다이어그램**
```mermaid
erDiagram
    USERS ||--o{ POSTS : "작성"
    USERS ||--o{ COMMENTS : "작성"
    USERS ||--o{ AI_ANALYSES : "분석 요청"
    USERS ||--o{ POST_LIKES : "좋아요"
    POSTS ||--o{ COMMENTS : "댓글 포함"
    POSTS ||--o{ POST_LIKES : "좋아요 받음"

    USERS {
        int id PK
        varchar email UK "UNIQUE"
        varchar password
        varchar name
        timestamp created_at
        timestamp updated_at
    }

    POSTS {
        int id PK
        varchar category "자유게시판/질문/정보공유"
        varchar title
        text content
        int author_id FK
        varchar author_name
        int views "기본값 0"
        int likes "기본값 0"
        timestamp created_at
        timestamp updated_at
    }

    COMMENTS {
        int id PK
        int post_id FK
        text content
        int author_id FK
        varchar author_name
        timestamp created_at
    }

    AI_ANALYSES {
        int id PK
        int user_id FK
        varchar image_url
        int score
        jsonb results "Top-5 예측 결과"
        jsonb survey_answers
        timestamp created_at
    }

    SURVEY_QUESTIONS {
        int id PK
        text question
        varchar type "radio/checkbox/text"
        jsonb options
        boolean required
        timestamp created_at
    }

    POST_LIKES {
        int id PK
        int post_id FK
        int user_id FK
        timestamp created_at
    }
```

**스토리지 구조**
```mermaid
graph TB
    subgraph STORAGE["데이터 저장소"]
        direction TB
        POSTGRES["<b>PostgreSQL</b><br/>데이터 영속성 확보<br/>포트: 5432"]
        FILES["<b>파일 시스템</b><br/> /backend/uploads/<br/> /scin/api/uploads/"]
    end

    subgraph TABLES["PostgreSQL 테이블"]
        direction LR
        USERS["<b>users</b><br/>사용자 정보"]
        POSTS["<b>posts</b><br/>게시글"]
        COMMENTS["<b>comments</b><br/>댓글"]
        ANALYSES["<b>ai_analyses</b><br/>AI 분석 결과"]
        SURVEYS["<b>survey_questions</b><br/>설문 질문"]
        LIKES["<b>post_likes</b><br/>게시글 좋아요"]
    end

    TABLES --> POSTGRES
    FILES -.->|"이미지 저장"| ANALYSES

    style STORAGE fill:#C8E6C9,stroke:#1B5E20,stroke-width:2px,color:#000
    style TABLES fill:#81C784,stroke:#1B5E20,stroke-width:2px,color:#000
    style POSTGRES fill:#81C784,stroke:#1B5E20,stroke-width:2px,color:#000
    style FILES fill:#81C784,stroke:#1B5E20,stroke-width:2px,color:#000
    style USERS fill:#81C784,stroke:#1B5E20,stroke-width:2px,color:#000
    style POSTS fill:#81C784,stroke:#1B5E20,stroke-width:2px,color:#000
    style COMMENTS fill:#81C784,stroke:#1B5E20,stroke-width:2px,color:#000
    style ANALYSES fill:#81C784,stroke:#1B5E20,stroke-width:2px,color:#000
    style SURVEYS fill:#81C784,stroke:#1B5E20,stroke-width:2px,color:#000
    style LIKES fill:#81C784,stroke:#1B5E20,stroke-width:2px,color:#000
```

#### 4. 보안 계층
```mermaid
graph LR
    JWT["<b>JWT</b><br/>토큰 생성/검증<br/>만료시간: 24h"]
    BCRYPT["<b>Bcrypt</b><br/>비밀번호 해싱<br/>10 salt rounds"]
    MULTER["<b>Multer</b><br/>파일 업로드<br/>최대 5MB"]

    style JWT fill:#EF9A9A,stroke:#B71C1C,stroke-width:2px,color:#000
    style BCRYPT fill:#EF9A9A,stroke:#B71C1C,stroke-width:2px,color:#000
    style MULTER fill:#EF9A9A,stroke:#B71C1C,stroke-width:2px,color:#000
```

## 주요 컴포넌트 설명

### 1. 클라이언트 계층 

#### 프론트엔드 페이지
- **랜딩 페이지** (`index.html`): 서비스 소개 및 Hero 섹션
- **인증 페이지**: 로그인, 회원가입
- **게시판**: 메인 목록, 상세보기, 글쓰기/수정
- **프로필**: 사용자 정보 관리 (4개 탭 시스템)
- **AI 분석**: 피부 분석, 분석 기록, 결과 상세

#### 공통 기능
- **공통 네비게이션** (`common-nav.js`): 모든 페이지 통합 네비게이션
- **Local Storage**: JWT 토큰 및 사용자 정보 저장

### 2. 서버 계층 

#### Express 서버 (포트 3000)
Node.js 기반의 백엔드 서버로 모든 API 요청을 처리합니다.

#### 미들웨어
- **JWT 인증** (`auth.js`): 토큰 검증 및 사용자 인증
- **Rate Limiter** (`rateLimiter.js`): API 남용 방지
  - 일반 API: 분당 100회
  - 인증 API: 15분당 5회
  - 게시글 작성: 분당 3회
- **Validator**: `express-validator`를 통한 입력값 검증

#### API 엔드포인트 상세

**1. 인증 API** (`/api/auth/*`)

| Method | Endpoint | 인증 필요 | 설명 |
|--------|----------|---------|------|
| POST | `/signup` |  | 회원가입 |
| POST | `/login` |  | 로그인 |
| POST | `/logout` |  | 로그아웃 (클라이언트 처리) |
| GET | `/profile` |  | 프로필 조회 |
| PUT | `/profile` |  | 프로필 수정 (이름, 비밀번호) |
| DELETE | `/delete` |  | 회원탈퇴 |
| GET | `/my-posts` |  | 내가 쓴 글 목록 |
| GET | `/my-comments` |  | 내가 쓴 댓글 목록 |

**2. 게시판 API** (`/api/board/free/*`)

| Method | Endpoint | 인증 필요 | 설명 |
|--------|----------|---------|------|
| GET | `/posts` |  | 게시글 목록 조회 (검색, 카테고리 필터링) |
| POST | `/posts` |  | 게시글 작성 |
| GET | `/posts/:id` |  | 게시글 상세 조회 (조회수 증가) |
| PUT | `/posts/:id` |  | 게시글 수정 (작성자 확인) |
| DELETE | `/posts/:id` |  | 게시글 삭제 (작성자 확인) |
| POST | `/posts/:id/like` |  | 게시글 좋아요 (중복 방지) |
| POST | `/posts/:id/comments` |  | 댓글 작성 |
| DELETE | `/posts/:postId/comments/:commentId` |  | 댓글 삭제 (작성자 확인) |

**3. AI 분석 API** (`/api/ai/*`)

| Method | Endpoint | 인증 필요 | 설명 |
|--------|----------|---------|------|
| POST | `/image-upload` |  | 이미지 업로드 (5MB, JPG/PNG) |
| GET | `/survey/questions` |  | 설문 질문 목록 조회 |
| POST | `/survey/questions` |  | 설문 질문 추가 (관리자) |
| PUT | `/survey/questions/:id` |  | 설문 질문 수정 (관리자) |
| DELETE | `/survey/questions/:id` |  | 설문 질문 삭제 (관리자) |
| POST | `/survey` |  | 설문 제출 및 AI 분석 요청 |
| GET | `/analysis/:id` |  | AI 분석 결과 조회 (본인만) |
| GET | `/my-analyses` |  | 내 AI 분석 기록 목록 |

**4. Flask AI 서비스 API** (`:5000`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/predict` | 이미지 분석 (Top-5 질환 예측) |
| GET | `/health` | 서비스 상태 확인 |

### 3. 데이터 계층 

#### PostgreSQL 데이터베이스
 **데이터 영속성 확보**: PostgreSQL을 사용하여 모든 데이터가 안전하게 저장되며, 서버 재시작 후에도 유지됩니다.

#### 데이터베이스 테이블 스키마

**users** - 사용자 정보
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**posts** - 게시글
```sql
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    author_name VARCHAR(100) NOT NULL,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**comments** - 댓글
```sql
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    author_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    author_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**ai_analyses** - AI 분석 결과
```sql
CREATE TABLE ai_analyses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    score INTEGER NOT NULL,
    results JSONB NOT NULL,
    survey_answers JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**survey_questions** - 설문 질문
```sql
CREATE TABLE survey_questions (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    options JSONB,
    required BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**post_likes** - 게시글 좋아요 (다대다 관계)
```sql
CREATE TABLE post_likes (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(post_id, user_id)
);
```

#### 파일 시스템
- 업로드된 이미지는 `/backend/uploads/` 디렉토리에 로컬 저장
- 향후 AWS S3 또는 Cloudinary와 같은 클라우드 스토리지로 마이그레이션 예정

### 4. 보안 계층 

- **JWT**: JSON Web Token 기반 인증 (만료시간: 24시간)
- **Bcrypt**: 비밀번호 해싱 (10 salt rounds)
- **Multer**: 파일 업로드 제한 (최대 5MB, JPG/PNG만 허용)

## 주요 데이터 흐름

### 1. 인증 흐름
```mermaid
sequenceDiagram
    participant User as 사용자
    participant FE as 프론트엔드
    participant BE as Node.js Backend
    participant DB as PostgreSQL
    participant LS as Local Storage

    User->>FE: 회원가입/로그인
    FE->>BE: POST /api/auth/signup or /login<br/>{email, password, name}
    BE->>DB: SELECT * FROM users WHERE email = ?

    alt 로그인
        DB-->>BE: 사용자 정보 반환
        BE->>BE: bcrypt.compare(password, hashedPassword)
    else 회원가입
        BE->>BE: bcrypt.hash(password)
        BE->>DB: INSERT INTO users
        DB-->>BE: 새 사용자 ID 반환
    end

    BE->>BE: jwt.sign({userId, userType})
    BE-->>FE: {success: true, user, token}
    FE->>LS: 저장 token & user
    FE->>User: 게시판으로 리다이렉트
```

### 2. 인증이 필요한 API 호출 흐름
```mermaid
sequenceDiagram
    participant User as 사용자
    participant FE as 프론트엔드
    participant LS as Local Storage
    participant BE as Node.js Backend
    participant MW as Auth Middleware
    participant DB as PostgreSQL

    Note over User,DB: 예시: 게시글 작성/좋아요/댓글 작성

    User->>FE: 게시글 작성 클릭
    FE->>LS: token 조회
    LS-->>FE: JWT token
    FE->>BE: POST /api/board/free/posts<br/>Authorization: Bearer {token}
    BE->>MW: JWT 검증 요청

    alt 토큰 유효
        MW->>MW: jwt.verify(token, SECRET)
        MW->>BE: req.user = {userId, userType}
        BE->>DB: INSERT INTO posts (author_id, title, content)
        DB-->>BE: 새 게시글 ID 반환
        BE-->>FE: {success: true, data: post}
        FE->>User: 게시글 작성 완료
    else 토큰 없음/만료/유효하지 않음
        MW-->>FE: {success: false, message: "인증 필요"}
        FE->>User: 로그인 페이지로 리다이렉트
    end
```

### 3. AI 피부 분석 흐름 (마이크로서비스 통신)
```mermaid
sequenceDiagram
    participant User as 사용자
    participant FE as 프론트엔드
    participant BE as Node.js Backend<br/>:3000
    participant FS as File System
    participant FLASK as Flask AI Service<br/>:5000
    participant MODEL as PyTorch Model
    participant DB as PostgreSQL

    Note over User,DB: AI 피부 분석 전체 흐름

    User->>FE: 1. 피부 이미지 업로드
    FE->>BE: POST /api/ai/image-upload<br/>(multipart/form-data)
    BE->>BE: multer로 파일 검증 (5MB, JPG/PNG)
    BE->>FS: 이미지 저장 /backend/uploads/
    FS-->>BE: 파일 경로 반환
    BE-->>FE: {success: true, filename}

    User->>FE: 2. 설문조사 작성
    FE->>BE: GET /api/ai/survey/questions
    BE->>DB: SELECT * FROM survey_questions
    DB-->>BE: 질문 목록
    BE-->>FE: {questions}
    FE->>User: 설문지 표시

    User->>FE: 3. 설문 제출 및 분석 요청
    FE->>BE: POST /api/ai/survey<br/>{imageFilename, answers}

    Note over BE,FLASK: 마이크로서비스 통신 시작

    BE->>FLASK: POST http://localhost:5000/predict<br/>{image_path}
    FLASK->>FS: 이미지 로드
    FS-->>FLASK: 이미지 데이터
    FLASK->>MODEL: 이미지 전처리 & 추론
    MODEL->>MODEL: ResNet50/EfficientNet 예측
    MODEL-->>FLASK: Top-5 질환 + 신뢰도 점수
    FLASK-->>BE: {predictions, recommendations}

    Note over BE,DB: 분석 결과 저장

    BE->>BE: 설문 점수 + AI 예측 통합
    BE->>DB: INSERT INTO ai_analyses<br/>(user_id, image_url, results, survey_answers)
    DB-->>BE: 분석 ID 반환
    BE-->>FE: {success: true, analysisId}

    FE->>User: 4. 결과 페이지로 이동
    User->>FE: 결과 확인
    FE->>BE: GET /api/ai/analysis/:id
    BE->>DB: SELECT * FROM ai_analyses WHERE id = ?
    DB-->>BE: 분석 결과 데이터
    BE-->>FE: {analysis}
    FE->>User: AI 분석 결과 표시<br/>(질환 예측, 차트, 권장사항)

    Note over User,DB:  Flask 서비스 다운 시<br/>Node.js에서 fallback 분석 수행
```

### 4. 게시판 게시글 작성 및 조회 흐름
```mermaid
sequenceDiagram
    participant User as 사용자
    participant FE as 프론트엔드
    participant BE as Node.js Backend
    participant DB as PostgreSQL

    Note over User,DB: 게시글 작성

    User->>FE: 글쓰기 버튼 클릭
    FE->>BE: POST /api/board/free/posts<br/>{category, title, content}<br/>Authorization: Bearer {token}
    BE->>BE: JWT에서 userId 추출
    BE->>DB: INSERT INTO posts<br/>(category, title, content, author_id)
    DB-->>BE: 새 게시글 ID
    BE-->>FE: {success: true, post}
    FE->>User: 게시글 목록으로 이동

    Note over User,DB: 게시글 조회

    User->>FE: 게시글 클릭
    FE->>BE: GET /api/board/free/posts/:id
    BE->>DB: UPDATE posts SET views = views + 1 WHERE id = ?
    BE->>DB: SELECT posts.*, COUNT(comments.id)<br/>FROM posts LEFT JOIN comments
    DB-->>BE: 게시글 데이터 + 댓글 수
    BE-->>FE: {success: true, post}
    FE->>User: 게시글 상세 표시
```

## 프로젝트 디렉토리 구조

### 전체 구조
```
SkinAI/
├── frontend/                    #  프론트엔드 (Vanilla JS)
│   └── src/
│       ├── index.html           # 랜딩 페이지
│       ├── script.js
│       ├── login.html           # 로그인
│       ├── signup.html          # 회원가입
│       ├── signup.js
│       ├── board.html           # 게시판 메인
│       ├── board.js
│       ├── post-detail.html     # 게시글 상세
│       ├── post-detail.js
│       ├── post-write.html      # 글쓰기/수정
│       ├── post-write.js
│       ├── profile.html         # 프로필 (4개 탭)
│       ├── profile.js
│       ├── ai-analysis.html     # AI 분석
│       ├── ai-analysis.js
│       ├── ai-result.html       # AI 결과 상세
│       ├── ai-result.js
│       ├── my-analyses.html     # AI 분석 기록
│       ├── common-nav.js        # 공통 네비게이션
│       └── style.css            # 전역 스타일
│
├── backend/                     #  Node.js 백엔드
│   ├── src/
│   │   ├── server.js            # Express 서버 진입점
│   │   ├── config/              # 설정 파일
│   │   │   ├── database.js      # PostgreSQL 연결
│   │   │   └── constants.js     # 상수 정의
│   │   ├── models/              # 데이터 모델
│   │   │   ├── user.js
│   │   │   ├── post.js
│   │   │   ├── comment.js
│   │   │   └── analysis.js
│   │   ├── middleware/          # 미들웨어
│   │   │   ├── auth.js          # JWT 인증
│   │   │   └── rateLimiter.js   # Rate limiting
│   │   └── routes/              # API 라우터
│   │       ├── auth.js          # /api/auth/*
│   │       ├── board.js         # /api/board/*
│   │       └── ai.js            # /api/ai/*
│   ├── uploads/                 # 이미지 저장소
│   ├── .env                     # 환경 변수  git 제외
│   ├── package.json
│   └── node_modules/
│
├── scin/                        #  AI 모델 시스템
│   ├── api/                     # Flask AI 서비스
│   │   ├── app.py               # Flask 서버 진입점
│   │   ├── config.py            # AI 설정
│   │   ├── inference.py         # 모델 추론
│   │   ├── start.sh             # 개발 서버 시작
│   │   ├── start_prod.sh        # 프로덕션 서버 시작
│   │   ├── uploads/             # AI 분석용 이미지
│   │   └── requirements.txt     # Python 의존성
│   ├── model/                   # 딥러닝 모델
│   │   ├── resnet50/            # ResNet50 모델
│   │   │   ├── model.py
│   │   │   ├── train.py
│   │   │   └── evaluate.py
│   │   └── efficientnet_b3/     # EfficientNet-B3 모델
│   │       ├── model.py
│   │       ├── train.py
│   │       └── evaluate.py
│   ├── data/                    # 데이터셋
│   │   ├── download.py          # SCIN 데이터셋 다운로드
│   │   ├── preprocess.py        # 데이터 전처리
│   │   └── scin_processed/      # 전처리된 데이터
│   ├── checkpoints/             # 학습된 모델 체크포인트
│   │   └── checkpoint_best.pth  # 최적 모델
│   └── logs/                    # 학습 로그
│
├── database/                    #  데이터베이스 (추가 예정)
│   ├── migrations/              # 스키마 마이그레이션
│   ├── seeds/                   # 초기 데이터
│   └── schema.sql               # PostgreSQL 스키마
│
├── README.md                    # 프로젝트 문서
├── Architecture.md              # 시스템 아키텍처 (현재 파일)
├── CLAUDE.md                    # Claude Code 가이드
└── package.json                 # 루트 패키지 설정
```

### 주요 디렉토리 설명

#### `frontend/src/` - 프론트엔드
- **정적 파일**: Express가 이 디렉토리를 정적으로 서빙
- **Vanilla JavaScript**: 프레임워크 없이 순수 JS 사용
- **공통 네비게이션**: `common-nav.js`로 모든 페이지 통합
- **Local Storage**: JWT 토큰 및 사용자 정보 저장

#### `backend/src/` - Node.js 백엔드
- **server.js**: Express 서버 진입점, 포트 3000
- **config/**: 데이터베이스 연결 및 상수 관리
- **models/**: PostgreSQL 테이블과 매핑되는 데이터 모델
- **middleware/**: JWT 인증, Rate limiting 등
- **routes/**: RESTful API 엔드포인트 정의

#### `scin/` - AI 모델 시스템
- **api/**: Flask 기반 AI 추론 서비스 (포트 5000)
- **model/**: PyTorch 기반 딥러닝 모델 (ResNet50, EfficientNet)
- **data/**: SCIN 데이터셋 다운로드 및 전처리 스크립트
- **checkpoints/**: 학습된 모델 가중치 파일

#### `database/` - 데이터베이스 관리 (추가 예정)
- **migrations/**: 데이터베이스 스키마 버전 관리
- **seeds/**: 초기 샘플 데이터
- **schema.sql**: PostgreSQL 테이블 정의

## 기술 스택

### 백엔드
- **Node.js**: 서버 런타임
- **Express**: 웹 프레임워크
- **PostgreSQL**: 관계형 데이터베이스
- **pg**: PostgreSQL 클라이언트 라이브러리
- **bcryptjs**: 비밀번호 해싱
- **jsonwebtoken**: JWT 토큰 생성 및 검증
- **express-validator**: 입력값 검증
- **express-rate-limit**: Rate limiting
- **multer**: 파일 업로드
- **dotenv**: 환경 변수 관리
- **axios**: HTTP 클라이언트 (Flask AI 서비스 통신)

### AI 서비스 (Flask)
- **Python 3.8+**: AI 서비스 런타임
- **Flask**: 경량 웹 프레임워크
- **PyTorch 2.0+**: 딥러닝 프레임워크
- **torchvision**: 이미지 변환 및 모델
- **Pillow**: 이미지 처리
- **Gunicorn**: 프로덕션 WSGI 서버

### 프론트엔드
- **Vanilla JavaScript**: 순수 자바스크립트
- **HTML5/CSS3**: 마크업 및 스타일링
- **Fetch API**: 서버 통신

## 보안 기능

### 구현됨 
- JWT 인증 미들웨어
- 모든 Board API 및 AI API 인증 적용
- Rate Limiting (API 남용 방지)
- 비밀번호 bcrypt 해싱
- 입력값 검증 (express-validator)
- 중복 이메일 체크
- 에러 메시지 일반화
- 파일 업로드 제한 (5MB, JPG/PNG)

### 미구현 
- CORS 설정
- HTTPS 지원
- 파일 업로드 악성코드 검사
- 세션 관리
- 비밀번호 재설정
- 이메일 인증

## 알려진 제한사항

> **경고**: 이 프로젝트는 학습/프로토타입 목적입니다. 프로덕션 환경에 배포하지 마세요.

1. **데이터베이스 최적화**
   - 데이터베이스 인덱스 최적화 필요
   - 쿼리 성능 튜닝 필요
   - 커넥션 풀 크기 조정 필요

2. **성능 이슈**
   - 페이지네이션 없음 (모든 게시글 한번에 로드)
   - 로컬 이미지 저장 (클라우드 스토리지 미사용)
   - Flask AI 서비스와 HTTP 통신 오버헤드

3. **AI 분석 제한**
   - Flask 서비스 다운 시 fallback 분석만 가능
   - 이미지 파일 크기 제한 (최대 5MB)
   - 실시간 분석 속도 개선 필요

## 개선 로드맵

### Phase 1: 보안 강화  완료
- [x] JWT 인증 미들웨어 구현
- [x] 모든 API 인증 적용
- [x] Rate limiting 추가

### Phase 2: UI/UX 개선  완료
- [x] 현대적인 랜딩 페이지
- [x] 통합 네비게이션 시스템
- [x] 프로필 페이지 탭 시스템
- [x] 게시판 카테고리 시스템
- [x] 반응형 디자인

### Phase 3: AI 모델 통합  완료
- [x] 이미지 업로드
- [x] AI 피부 분석 시스템
- [x] Flask AI 서비스 마이크로서비스 아키텍처
- [x] PyTorch 기반 ResNet50/EfficientNet-B3 모델 통합
- [x] 50가지 피부 질환 분류 시스템

### Phase 4: 데이터베이스 연동  진행 중
- [x] PostgreSQL 연동
- [x] 데이터 영속성 확보
- [ ] 데이터베이스 스키마 마이그레이션
- [ ] 인덱싱 추가 및 쿼리 최적화
- [ ] 커넥션 풀 설정
- [ ] 클라우드 이미지 스토리지

### Phase 5: 기능 확장
- [x] 게시글 검색
- [ ] 페이지네이션
- [ ] 비밀번호 재설정
- [ ] 이메일 인증
- [ ] 알림 시스템

### Phase 6: 프로덕션 준비
- [ ] HTTPS & CORS 설정
- [ ] 로깅 & 모니터링 시스템
- [ ] 배포 자동화 (Docker, CI/CD)
- [ ] 성능 최적화 및 캐싱
- [ ] 부하 테스트

## 시스템 요약

### 서비스 포트 및 URL

| 서비스 | 포트 | URL | 설명 |
|--------|------|-----|------|
| **프론트엔드** | 3000 | http://localhost:3000 | Express 정적 파일 서빙 |
| **Node.js Backend** | 3000 | http://localhost:3000/api/* | RESTful API |
| **Flask AI Service** | 5000 | http://localhost:5000 | AI 추론 서비스 |
| **PostgreSQL** | 5432 | localhost:5432 | 데이터베이스 |

### 주요 기술 스택 요약

```
┌─────────────────────────────────────────────────────────────┐
│  프론트엔드: Vanilla JavaScript + HTML5/CSS3                │
├─────────────────────────────────────────────────────────────┤
│  백엔드 API: Node.js + Express + JWT                        │
├─────────────────────────────────────────────────────────────┤
│  AI 서비스: Flask + PyTorch + ResNet50/EfficientNet         │
├─────────────────────────────────────────────────────────────┤
│  데이터베이스: PostgreSQL 14+                                │
├─────────────────────────────────────────────────────────────┤
│  보안: JWT + Bcrypt + Rate Limiting                         │
└─────────────────────────────────────────────────────────────┘
```

### 데이터베이스 테이블 요약

- **users** - 사용자 정보 (인증, 프로필)
- **posts** - 게시글 (자유게시판, 질문, 정보공유)
- **comments** - 댓글 (게시글에 대한 댓글)
- **post_likes** - 게시글 좋아요 (다대다 관계)
- **ai_analyses** - AI 분석 결과 (JSONB)
- **survey_questions** - 동적 설문 질문 (JSONB)

### 주요 데이터 흐름 요약

1. **인증**: 사용자 → Frontend → Backend → PostgreSQL → JWT 발급
2. **게시판**: 사용자 → Frontend → Backend (JWT 검증) → PostgreSQL
3. **AI 분석**: 사용자 → Frontend → Backend → Flask AI → PyTorch → PostgreSQL

### 보안 체계

```mermaid
graph LR
    A[사용자 요청] --> B{JWT 검증}
    B -->|유효| C[Rate Limit 검사]
    B -->|무효| D[401 Unauthorized]
    C -->|통과| E[입력값 검증]
    C -->|초과| F[429 Too Many Requests]
    E -->|성공| G[비즈니스 로직 실행]
    E -->|실패| H[400 Bad Request]
    G --> I[PostgreSQL]
    I --> J[응답 반환]

    style B fill:#FFD54F,stroke:#EF6C00
    style C fill:#FFD54F,stroke:#EF6C00
    style E fill:#FFD54F,stroke:#EF6C00
    style I fill:#81C784,stroke:#1B5E20
```

## 참고 문서
- [README.md](./README.md): 프로젝트 전체 문서 및 빠른 시작 가이드
- [CLAUDE.md](./CLAUDE.md): Claude Code 개발 가이드 및 Clean Code 규칙
- [SCIN_데이터_모델_분석_리포트.md](./SCIN_데이터_모델_분석_리포트.md): AI 모델 분석 리포트

---

**문서 버전**: 2.0
**마지막 업데이트**: 2024-11-26
**작성자**: SkinAI Development Team
