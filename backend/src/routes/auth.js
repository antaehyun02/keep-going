const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { body, validationResult } = require('express-validator');

const router = express.Router();

// board 데이터 접근을 위한 참조 (순환 참조 방지를 위해 동적 로드)
let boardData = null;
const getBoardData = () => {
  if (!boardData) {
    boardData = require('./board');
  }
  return boardData;
};

// 임시 사용자 저장소 (나중에 데이터베이스로 교체)
let users = [];

// JWT 토큰 생성 함수
const generateToken = (userId) => {
  return jwt.sign(
    { userId: userId },
    process.env.JWT_SECRET,
    { expiresIn: process.env.JWT_EXPIRE }
  );
};

// 회원가입 엔드포인트
router.post('/signup', [
  // 입력값 검증
  body('email').isEmail().withMessage('유효한 이메일을 입력해주세요'),
  body('password').isLength({ min: 6 }).withMessage('비밀번호는 최소 6자 이상이어야 합니다'),
  body('name').notEmpty().withMessage('이름을 입력해주세요')
], async (req, res) => {
  try {
    // 입력값 검증 결과 확인
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        success: false,
        message: '입력값 오류',
        errors: errors.array()
      });
    }

    const { email, password, name } = req.body;

    // 이미 존재하는 사용자인지 확인
    const existingUser = users.find(user => user.email === email);
    if (existingUser) {
      return res.status(400).json({
        success: false,
        message: '이미 존재하는 이메일입니다'
      });
    }

    // 비밀번호 해싱
    const saltRounds = 10;
    const hashedPassword = await bcrypt.hash(password, saltRounds);

    // 새 사용자 생성
    const newUser = {
      id: users.length + 1, // 임시 ID (나중에 DB auto increment로 변경)
      email,
      password: hashedPassword,
      name,
      createdAt: new Date().toISOString()
    };

    // 사용자 저장 (임시)
    users.push(newUser);

    // JWT 토큰 생성
    const token = generateToken(newUser.id);

    res.status(201).json({
      success: true,
      message: '회원가입이 완료되었습니다',
      data: {
        user: {
          id: newUser.id,
          email: newUser.email,
          name: newUser.name
        },
        token
      }
    });

  } catch (error) {
    console.error('회원가입 에러:', error);
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다'
    });
  }
});

// 로그인 엔드포인트
router.post('/login', [
  // 입력값 검증
  body('email').isEmail().withMessage('유효한 이메일을 입력해주세요'),
  body('password').notEmpty().withMessage('비밀번호를 입력해주세요')
], async (req, res) => {
  try {
    // 입력값 검증 결과 확인
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        success: false,
        message: '입력값 오류',
        errors: errors.array()
      });
    }

    const { email, password } = req.body;

    // 사용자 찾기
    const user = users.find(user => user.email === email);
    if (!user) {
      return res.status(400).json({
        success: false,
        message: '이메일 또는 비밀번호가 올바르지 않습니다'
      });
    }

    // 비밀번호 확인
    const isPasswordValid = await bcrypt.compare(password, user.password);
    if (!isPasswordValid) {
      return res.status(400).json({
        success: false,
        message: '이메일 또는 비밀번호가 올바르지 않습니다'
      });
    }

    // JWT 토큰 생성
    const token = generateToken(user.id);

    res.json({
      success: true,
      message: '로그인 성공',
      data: {
        user: {
          id: user.id,
          email: user.email,
          name: user.name
        },
        token
      }
    });

  } catch (error) {
    console.error('로그인 에러:', error);
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다'
    });
  }
});

// 로그아웃 엔드포인트
router.post('/logout', (req, res) => {
  // JWT는 stateless이므로 서버에서 특별히 할 일이 없음
  // 클라이언트에서 토큰을 삭제하도록 응답
  res.json({
    success: true,
    message: '로그아웃되었습니다. 클라이언트에서 토큰을 삭제해주세요.'
  });
});

// 현재 사용자 정보 조회 (토큰 검증 필요)
router.get('/me', (req, res) => {
  // 인증 미들웨어가 필요한 부분 (다음에 구현)
  res.json({
    success: true,
    message: '사용자 정보 조회 (인증 미들웨어 구현 예정)'
  });
});

// 프로필 조회 (GET /api/auth/profile?userId=1)
router.get('/profile', (req, res) => {
  try {
    const userId = req.query.userId;

    if (!userId) {
      return res.status(400).json({
        success: false,
        message: '사용자 정보가 필요합니다'
      });
    }

    const user = users.find(u => u.id === parseInt(userId));
    if (!user) {
      return res.status(404).json({
        success: false,
        message: '사용자를 찾을 수 없습니다'
      });
    }

    res.json({
      success: true,
      data: {
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt
      }
    });
  } catch (error) {
    console.error('프로필 조회 에러:', error);
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다'
    });
  }
});

// 프로필 수정 (PUT /api/auth/profile)
router.put('/profile', [
  body('userId').notEmpty().withMessage('사용자 정보가 필요합니다'),
  body('name').optional().notEmpty().withMessage('이름은 비어있을 수 없습니다'),
  body('currentPassword').optional().notEmpty().withMessage('현재 비밀번호를 입력해주세요'),
  body('newPassword').optional().isLength({ min: 6 }).withMessage('새 비밀번호는 최소 6자 이상이어야 합니다')
], async (req, res) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        success: false,
        message: '입력값 오류',
        errors: errors.array()
      });
    }

    const { userId, name, currentPassword, newPassword } = req.body;

    const userIndex = users.findIndex(u => u.id === parseInt(userId));
    if (userIndex === -1) {
      return res.status(404).json({
        success: false,
        message: '사용자를 찾을 수 없습니다'
      });
    }

    const user = users[userIndex];

    // 비밀번호 변경 요청이 있는 경우
    if (currentPassword && newPassword) {
      const isPasswordValid = await bcrypt.compare(currentPassword, user.password);
      if (!isPasswordValid) {
        return res.status(400).json({
          success: false,
          message: '현재 비밀번호가 올바르지 않습니다'
        });
      }

      const hashedPassword = await bcrypt.hash(newPassword, 10);
      users[userIndex].password = hashedPassword;
    }

    // 이름 변경
    if (name) {
      users[userIndex].name = name;
    }

    res.json({
      success: true,
      message: '프로필이 수정되었습니다',
      data: {
        id: users[userIndex].id,
        email: users[userIndex].email,
        name: users[userIndex].name,
        createdAt: users[userIndex].createdAt
      }
    });
  } catch (error) {
    console.error('프로필 수정 에러:', error);
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다'
    });
  }
});

// 디버깅용: 현재 저장된 사용자 목록 (개발 중에만 사용)
router.get('/users', (req, res) => {
  res.json({
    success: true,
    data: users.map(user => ({
      id: user.id,
      email: user.email,
      name: user.name,
      createdAt: user.createdAt
    }))
  });
});

// 회원탈퇴 엔드포인트
router.delete('/delete', [
  // 입력값 검증
  body('email').isEmail().withMessage('유효한 이메일을 입력해주세요'),
  body('password').notEmpty().withMessage('비밀번호를 입력해주세요')
], async (req, res) => {
  try {
    // 입력값 검증 결과 확인
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        success: false,
        message: '입력값 오류',
        errors: errors.array()
      });
    }

    const { email, password } = req.body;

    // 사용자 찾기
    const userIndex = users.findIndex(user => user.email === email);
    if (userIndex === -1) {
      return res.status(400).json({
        success: false,
        message: '해당 이메일의 사용자를 찾을 수 없습니다'
      });
    }

    const user = users[userIndex];

    // 비밀번호 확인
    const isPasswordValid = await bcrypt.compare(password, user.password);
    if (!isPasswordValid) {
      return res.status(400).json({
        success: false,
        message: '비밀번호가 올바르지 않습니다'
      });
    }

    // 사용자 삭제
    users.splice(userIndex, 1);

    res.json({
      success: true,
      message: '회원탈퇴가 완료되었습니다',
      data: {
        deletedUser: {
          id: user.id,
          email: user.email,
          name: user.name
        },
        deletedAt: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('회원탈퇴 에러:', error);
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다'
    });
  }
});

// 내가 쓴 글 조회 (GET /api/auth/my-posts?userId=1)
router.get('/my-posts', (req, res) => {
  try {
    const userId = req.query.userId;

    if (!userId) {
      return res.status(400).json({
        success: false,
        message: '사용자 정보가 필요합니다'
      });
    }

    const board = getBoardData();

    // 사용자가 작성한 게시글 필터링
    const userPosts = board.posts.filter(post => post.authorId === parseInt(userId));

    // 최신순으로 정렬
    const sortedPosts = userPosts.sort((a, b) =>
      new Date(b.createdAt) - new Date(a.createdAt)
    );

    res.json({
      success: true,
      data: sortedPosts
    });
  } catch (error) {
    console.error('내가 쓴 글 조회 에러:', error);
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다'
    });
  }
});

// 내가 쓴 댓글 조회 (GET /api/auth/my-comments?userId=1)
router.get('/my-comments', (req, res) => {
  try {
    const userId = req.query.userId;

    if (!userId) {
      return res.status(400).json({
        success: false,
        message: '사용자 정보가 필요합니다'
      });
    }

    const board = getBoardData();

    // 모든 댓글에서 사용자가 작성한 댓글 찾기
    const userComments = [];
    Object.keys(board.comments).forEach(postId => {
      const postComments = board.comments[postId].filter(
        comment => comment.authorId === parseInt(userId)
      );

      // 게시글 정보 추가
      postComments.forEach(comment => {
        const post = board.posts.find(p => p.id === parseInt(postId));
        userComments.push({
          ...comment,
          postTitle: post ? post.title : '(삭제된 게시글)'
        });
      });
    });

    // 최신순으로 정렬
    const sortedComments = userComments.sort((a, b) =>
      new Date(b.createdAt) - new Date(a.createdAt)
    );

    res.json({
      success: true,
      data: sortedComments
    });
  } catch (error) {
    console.error('내가 쓴 댓글 조회 에러:', error);
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다'
    });
  }
});

// 브라우저 테스트용: Auth 라우터 연결 확인
router.get('/test', (req, res) => {
  res.json({
    success: true,
    message: 'Auth 라우터가 정상적으로 연결되었습니다!',
    info: {
      currentUsers: users.length,
      availableRoutes: {
        browserTestable: [
          'GET /api/auth/test (현재 라우트)',
          'GET /api/auth/users (사용자 목록)'
        ],
        postmanOrRestClient: [
          'POST /api/auth/signup (회원가입)',
          'POST /api/auth/login (로그인)',
          'POST /api/auth/logout (로그아웃)',
          'DELETE /api/auth/delete (회원탈퇴)',
          'GET /api/auth/profile (프로필 조회)',
          'PUT /api/auth/profile (프로필 수정)',
          'GET /api/auth/my-posts (내가 쓴 글)',
          'GET /api/auth/my-comments (내가 쓴 댓글)'
        ]
      }
    },
    timestamp: new Date().toISOString()
  });
});

module.exports = router;
module.exports.users = users;