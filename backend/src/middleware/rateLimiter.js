const rateLimit = require('express-rate-limit');

// 일반 API용 Rate Limiter (분당 100회)
const apiLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1분
  max: 100, // 최대 100회 요청
  message: {
    success: false,
    message: '너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요.'
  },
  standardHeaders: true,
  legacyHeaders: false,
});

// 인증 API용 Rate Limiter (15분당 5회 - 로그인, 회원가입)
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15분
  max: 5, // 최대 5회 요청
  message: {
    success: false,
    message: '너무 많은 로그인 시도가 발생했습니다. 15분 후 다시 시도해주세요.'
  },
  standardHeaders: true,
  legacyHeaders: false,
});

// 게시글 작성용 Rate Limiter (1분당 3회)
const createPostLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1분
  max: 3, // 최대 3회
  message: {
    success: false,
    message: '게시글 작성 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.'
  },
  standardHeaders: true,
  legacyHeaders: false,
});

module.exports = {
  apiLimiter,
  authLimiter,
  createPostLimiter
};
