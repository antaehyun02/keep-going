const express = require('express');
const axios = require('axios');
const https = require('https');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const app = express();
const PORT = 3000;

// 🚨 API 키
const MY_API_KEY = "dacf34d37c784ea0b9e9898b257e3e78"; 

// 좌표 범위 (수원~천안 광범위 설정)
const REGION_PARAMS = `minX=126.80&maxX=127.60&minY=36.50&maxY=37.60&getType=json`;

const URLS = {
    // 1. CCTV
    CCTV: `https://openapi.its.go.kr:9443/cctvInfo?apiKey=${MY_API_KEY}&type=ex&cctvType=1&${REGION_PARAMS}`,
    
    // 2. 소통정보
    TRAFFIC: `https://openapi.its.go.kr:9443/trafficInfo?apiKey=${MY_API_KEY}&type=ex&routeNo=all&drcType=all&${REGION_PARAMS}`,
    
    // 3. ★ [핵심] 돌발상황 (공사, 사고 등) - type=all로 변경하여 국도 포함 조회
    EVENT: `https://openapi.its.go.kr:9443/eventInfo?apiKey=${MY_API_KEY}&type=all&eventType=all&${REGION_PARAMS}`,
    
    // 4. 주의구간 (결빙 등)
    WARNING: `https://openapi.its.go.kr:9443/posIncidentInfo?apiKey=${MY_API_KEY}&${REGION_PARAMS}`,
    VMS: `https://openapi.its.go.kr:9443/vmsInfo?apiKey=${MY_API_KEY}&${REGION_PARAMS}`
};

app.use(express.static('public'));
const agent = new https.Agent({ rejectUnauthorized: false });

// ----------------------------------------------------
// 1. 돌발상황(공사/사고) API - 핵심 수정
// ----------------------------------------------------
app.get('/api/events', async (req, res) => {
    console.log("📡 [Server] 돌발상황(공사/사고) 정보 요청...");
    try {
        const response = await axios.get(URLS.EVENT, { httpsAgent: agent, timeout: 5000 });
        
        if (response.data && response.data.response && response.data.response.data) {
            const rawList = response.data.response.data;
            
            const list = rawList.map(i => ({
                type: i.eventType,       // 공사, 사고 등
                msg: i.eventDetail,      // 상세 내용 (ex: 1차로 차단 공사)
                road: i.roadName,        // 도로명
                lat: i.coordy,
                lng: i.coordx,
                time: i.startDate        // 시작 시간
            }));

            console.log(`🚧 [Server] 돌발상황 ${list.length}건 발견!`);
            res.json({ success: true, list: list });
        } else {
            console.log("✅ [Server] 현재 돌발상황 없음");
            res.json({ success: true, list: [] });
        }
    } catch (e) {
        console.error("🔥 돌발상황 API 에러:", e.message);
        res.json({ success: false, list: [] });
    }
});

// 2. CCTV 목록
app.get('/api/cctv/list', async (req, res) => {
    try {
        const response = await axios.get(URLS.CCTV, { httpsAgent: agent, timeout: 3000 });
        if (response.data?.response?.data) {
            const list = response.data.response.data.map(i => ({
                name: i.cctvname, url: i.cctvurl, lat: i.coordy, lng: i.coordx
            }));
            res.json({ success: true, list });
        } else { res.json({ success: false, list: [] }); }
    } catch (e) { res.json({ success: false, list: [] }); }
});

// 3. 실시간 교통정보 (CSV 기반)
app.get('/api/traffic', (req, res) => {
    const csvPath = path.join(__dirname, 'data', 'history.csv');
    const now = new Date();
    const currentHour = now.getHours();
    const currentDay = now.getDay();

    const sectionSpeeds = { 0: [], 1: [], 2: [] };

    try {
        if (fs.existsSync(csvPath)) {
            const fileContent = fs.readFileSync(csvPath, 'utf-8');
            const lines = fileContent.split('\n');
            for (let i = 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) continue;
                const parts = line.split(',');
                if (parts.length < 5) continue;
                const section = parseInt(parts[0]);
                const day = parseInt(parts[2]);
                const hour = parseInt(parts[3]);
                const speed = parseInt(parts[4]);
                if (day === currentDay && hour === currentHour) {
                    if (sectionSpeeds[section]) sectionSpeeds[section].push(speed);
                }
            }
        }
        const finalSpeeds = {};
        for (let sec in sectionSpeeds) {
            const speeds = sectionSpeeds[sec];
            finalSpeeds[sec] = speeds.length > 0 ? Math.floor(speeds.reduce((a, b) => a + b, 0) / speeds.length) : 90;
        }
        
        // 가상 좌표 매핑
        const trafficList = [
            { name: "안성IC", lat: 37.003, lng: 127.145, speed: finalSpeeds[0] },
            { name: "북천안IC", lat: 36.915, lng: 127.168, speed: finalSpeeds[0] },
            { name: "천안IC", lat: 36.845, lng: 127.182, speed: finalSpeeds[0] },
            { name: "입장휴게소", lat: 36.935, lng: 127.170, speed: finalSpeeds[1] },
            { name: "수원신갈IC", lat: 37.255, lng: 127.105, speed: finalSpeeds[2] },
            { name: "기흥IC", lat: 37.215, lng: 127.110, speed: finalSpeeds[2] },
            { name: "오산IC", lat: 37.145, lng: 127.095, speed: finalSpeeds[2] }
        ];
        res.json({ success: true, list: trafficList });
    } catch (e) {
        res.json({ success: true, list: [{ name: "로딩중", lat: 37.05, lng: 127.12, speed: 80 }] });
    }
});

// 4. AI 예측
app.get('/api/predict', (req, res) => {
    const now = new Date();
    const cctvId = req.query.id || 0;
    const cmd = process.platform === 'win32' ? 'python' : 'python3';
    const python = spawn(cmd, ['ai_server.py', now.getDay(), now.getHours(), cctvId]);
    let result = '';
    python.stdout.on('data', d => result += d.toString());
    python.on('close', () => {
        try { res.json(JSON.parse(result)); } 
        catch { res.json({ status: "error", speed: 0 }); }
    });
});

// 기타 API
app.get('/api/vision/analyze', (req, res) => {
    const python = spawn(process.platform === 'win32' ? 'python' : 'python3', ['vision_server.py']);
    let result = '';
    python.stdout.on('data', d => result += d.toString());
    python.on('close', () => { try { res.json(JSON.parse(result)); } catch { res.json({ count: 0 }); } });
});
app.get('/api/vms', async (req, res) => { try { const r=await axios.get(URLS.VMS,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({id:i.vmsId,msg:i.vmsMessage,lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });
app.get('/api/warnings', async (req, res) => { try { const r=await axios.get(URLS.WARNING,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({type:i.type||"주의",msg:i.message,lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });

app.listen(PORT, () => console.log(`\n🚀 시스템 가동: http://localhost:${PORT}`));