const jwt = require('jsonwebtoken');

module.exports = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer 토큰

  if (!token) {
    return res.status(401).json({ message: '로그인이 필요합니다.' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded; // user_id, role 담김
    next();
  } catch (err) {
    return res.status(403).json({ message: '토큰이 만료됐거나 유효하지 않습니다.' });
  }
};