const jwt = require('jsonwebtoken');

// JWT 인증 미들웨어
const authenticateToken = (req, res, next) => {
  try {
    // Authorization 헤더에서 토큰 추출
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1]; // "Bearer TOKEN" 형식

    if (!token) {
      return res.status(401).json({
        success: false,
        message: '인증 토큰이 필요합니다'
      });
    }

    // 토큰 검증
    jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
      if (err) {
        return res.status(403).json({
          success: false,
          message: '유효하지 않거나 만료된 토큰입니다'
        });
      }

      // 검증된 사용자 정보를 req.user에 저장
      req.user = user;
      next();
    });
  } catch (error) {
    console.error('인증 미들웨어 에러:', error);
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다'
    });
  }
};

// 선택적 인증 미들웨어 (토큰이 있으면 검증, 없어도 통과)
const optionalAuth = (req, res, next) => {
  try {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
      req.user = null;
      return next();
    }

    jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
      if (err) {
        req.user = null;
      } else {
        req.user = user;
      }
      next();
    });
  } catch (error) {
    console.error('선택적 인증 에러:', error);
    req.user = null;
    next();
  }
};

module.exports = {
  authenticateToken,
  optionalAuth
};
