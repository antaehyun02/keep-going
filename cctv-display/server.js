const express = require('express');
const axios = require('axios');
const https = require('https');
const { spawn } = require('child_process');
const app = express();
const PORT = 3000;

// 🚨 제공해주신 API 키 적용
const MY_API_KEY = "dacf34d37c784ea0b9e9898b257e3e78"; 

app.use(express.static('public'));
const agent = new https.Agent({ rejectUnauthorized: false });

// 1. CCTV 목록 URL (수원 ~ 천안 전체 구간)
// 좌표: MinY를 36.80까지 내려서 천안을 포함시켰습니다.
const TARGET_URL = `https://openapi.its.go.kr:9443/cctvInfo?apiKey=${MY_API_KEY}&type=ex&cctvType=1&minX=127.00&maxX=127.30&minY=36.80&maxY=37.35&getType=json`;

// 2. 주의운전구간 URL
const WARNING_URL = `https://openapi.its.go.kr:9443/posIncidentInfo?apiKey=${MY_API_KEY}&minX=127.00&maxX=127.30&minY=36.80&maxY=37.35&getType=json`;

// 3. 돌발상황정보 URL
const EVENT_URL = `https://openapi.its.go.kr:9443/eventInfo?apiKey=${MY_API_KEY}&type=ex&eventType=all&minX=127.00&maxX=127.30&minY=36.80&maxY=37.35&getType=json`;

// --- API 라우터 ---

app.get('/api/cctv/list', async (req, res) => {
    console.log("[서버] 수원~천안 CCTV 목록 요청...");
    try {
        const response = await axios.get(TARGET_URL, { httpsAgent: agent, timeout: 5000 });
        const data = response.data;
        
        if (data?.response?.data) {
            const rawList = data.response.data;
            console.log(`📦 검색된 CCTV: ${rawList.length}개`);
            
            // 필터링 없이 전체 목록 전송 (프론트에서 선택 가능하게)
            const list = rawList.map(item => ({
                name: item.cctvname,
                url: item.cctvurl,
                lat: item.coordy,
                lng: item.coordx
            }));
            res.json({ success: true, list: list });
        } else {
            throw new Error("데이터 없음");
        }
    } catch (error) {
        console.error("🔥 CCTV 에러:", error.message);
        res.json({ success: false, list: [] });
    }
});

app.get('/api/warnings', async (req, res) => {
    try {
        const response = await axios.get(WARNING_URL, { httpsAgent: agent, timeout: 5000 });
        const items = response.data?.response?.data || [];
        const list = items.map(i => ({
            type: i.type || "주의",
            msg: i.message || "구간 정보",
            lat: i.coordy,
            lng: i.coordx
        }));
        res.json({ success: true, list: list });
    } catch (e) { res.json({ success: false, list: [] }); }
});

app.get('/api/events', async (req, res) => {
    try {
        const response = await axios.get(EVENT_URL, { httpsAgent: agent, timeout: 5000 });
        const items = response.data?.response?.data || [];
        const list = items.map(i => ({
            type: i.type || "알림",
            msg: i.eventDetail || i.message || "내용 없음",
            road: i.roadName || "도로명 미상",
            time: i.startDate || new Date().toLocaleTimeString()
        }));
        res.json({ success: true, list: list });
    } catch (e) { res.json({ success: false, list: [] }); }
});

// AI 예측 (파이썬 연동)
app.get('/api/predict', (req, res) => {
    const now = new Date();
    // ai_server.py가 없으면 에러가 날 수 있으니 예외처리 필수
    const python = spawn('python', ['ai_server.py', now.getDay(), now.getHours()]);
    let result = '';
    python.stdout.on('data', (data) => { result += data.toString(); });
    python.on('close', () => {
        try { res.json(JSON.parse(result)); } 
        catch { res.json({ status: "fallback", speed: 90, risk: "분석 중..." }); }
    });
});

app.listen(PORT, () => {
    console.log(`\n🚀 수원~천안 통합 관제 가동: http://localhost:${PORT}`);
});