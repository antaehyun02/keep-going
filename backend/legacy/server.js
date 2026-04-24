const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const authRoutes = require('./routes/auth');

const app = express();

// ── 미들웨어 ──
app.use(cors());
app.use(express.json());

// ── 정적 파일 서빙 ──
app.use(express.static(path.join(__dirname, '../html')));
app.use(express.static(path.join(__dirname, '../src')));

// ── 라우터 연결 ──
app.use('/api/auth', authRoutes);

// ── 서버 실행 ──
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`✅ 서버 실행 중 → http://localhost:${PORT}`);
});