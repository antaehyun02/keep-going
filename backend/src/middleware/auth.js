const jwt = require('jsonwebtoken');

const authenticateToken = (req, res, next) => {
  try {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
      return res.status(401).json({ message: '로그인이 필요합니다.' });
    }

    jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
      if (err) {
        return res.status(403).json({ message: '토큰이 만료됐거나 유효하지 않습니다.' });
      }
      req.user = user;
      next();
    });
  } catch (error) {
    console.error('인증 미들웨어 에러:', error);
    res.status(500).json({ message: '서버 오류가 발생했습니다.' });
  }
};

const optionalAuth = (req, res, next) => {
  try {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
      req.user = null;
      return next();
    }

    jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
      req.user = err ? null : user;
      next();
    });
  } catch (error) {
    console.error('선택적 인증 에러:', error);
    req.user = null;
    next();
  }
};

module.exports = { authenticateToken, optionalAuth };
