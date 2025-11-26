const express = require('express');
const axios = require('axios');
const https = require('https');
const { spawn } = require('child_process');
const app = express();
const PORT = 3000;

// 🚨 인증키 입력 🚨
const MY_API_KEY = "dacf34d37c784ea0b9e9898b257e3e78"; 

app.use(express.static('public'));
const agent = new https.Agent({ rejectUnauthorized: false });

// 수원~오산 좌표
const TARGET_URL = `https://openapi.its.go.kr:9443/cctvInfo?apiKey=${MY_API_KEY}&type=ex&cctvType=1&minX=127.00&maxX=127.20&minY=37.10&maxY=37.35&getType=json`;

// 1. CCTV 목록 조회 API (좌표 추가됨!)
app.get('/api/cctv/list', async (req, res) => {
    console.log("[서버] CCTV 목록(좌표 포함) 요청 중...");
    try {
        const response = await axios.get(TARGET_URL, { httpsAgent: agent, timeout: 5000 });
        const data = response.data;
        
        if (data?.response?.data) {
            const rawList = data.response.data;
            
            // ★ 핵심 수정: 좌표(coordy=위도, coordx=경도) 추가!
            const cleanList = rawList.map(item => ({
                name: item.cctvname,
                url: item.cctvurl,
                lat: item.coordy, // 위도
                lng: item.coordx  // 경도
            }));

            console.log(`✅ ${cleanList.length}개 CCTV 데이터 전송 완료`);
            res.json({ success: true, list: cleanList });
        } else {
            throw new Error("데이터 없음");
        }
    } catch (error) {
        console.error("🔥 목록 실패:", error.message);
        res.json({ success: false, list: [] });
    }
});

// 2. AI 예측 API (기존 동일)
app.get('/api/predict', (req, res) => {
    const now = new Date();
    const python = spawn('python', ['ai_server.py', now.getDay(), now.getHours()]);
    let result = '';
    python.stdout.on('data', (data) => { result += data.toString(); });
    python.on('close', () => {
        try { res.json(JSON.parse(result)); } 
        catch { res.json({ status: "error", speed: 90, risk: "분석 중..." }); }
    });
});

app.listen(PORT, () => {
    console.log(`\n🚀 지도 연동 관제 서버 가동: http://localhost:${PORT}\n`);
});