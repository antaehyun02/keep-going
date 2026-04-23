const express = require('express');
const cors = require('cors');
require('dotenv').config();

const authRoutes = require('./routes/auth');

const app = express();

// ── 미들웨어 ──
app.use(cors());
app.use(express.json());

// ── 라우터 연결 ──
app.use('/api/auth', authRoutes);

// ── 서버 상태 확인 ──
app.get('/', (req, res) => {
  res.json({ message: 'SkinAI 서버 정상 작동 중 🟢' });
});

// ── 서버 실행 ──
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`✅ 서버 실행 중 → http://localhost:${PORT}`);
});