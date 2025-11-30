const express = require('express');
const axios = require('axios');
const https = require('https');
const { spawn } = require('child_process');
const app = express();
const PORT = 3000;

// ========================================================
// 🚨 [키 원복] 맨 처음 성공하셨던 그 키로 되돌렸습니다!
// ========================================================
const MY_API_KEY = "dacf34d37c784ea0b9e9898b257e3e78"; 

// 좌표: 수원~천안 (천안 포함되게 MinY 조정)
const BASE_PARAMS = `apiKey=${MY_API_KEY}&type=ex&minX=127.00&maxX=127.30&minY=36.80&maxY=37.35&getType=json`;

const URLS = {
    // MP4 방식 (가장 안정적)
    CCTV: `https://openapi.its.go.kr:9443/cctvInfo?${BASE_PARAMS}&cctvType=1`,
    TRAFFIC: `https://openapi.its.go.kr:9443/trafficInfo?${BASE_PARAMS}&routeNo=0010&drcType=all`,
    WARNING: `https://openapi.its.go.kr:9443/posIncidentInfo?${BASE_PARAMS}`,
    EVENT: `https://openapi.its.go.kr:9443/eventInfo?${BASE_PARAMS}&eventType=all`,
    VMS: `https://openapi.its.go.kr:9443/vmsInfo?${BASE_PARAMS}`
};

app.use(express.static('public'));
const agent = new https.Agent({ rejectUnauthorized: false });

// ----------------------------------------------------
// 1. CCTV 목록 API (무조건 성공해야 함)
// ----------------------------------------------------
app.get('/api/cctv/list', async (req, res) => {
    console.log(`📡 [Server] CCTV 목록 요청 (Key: ${MY_API_KEY.substring(0,5)}...)`);
    try {
        // 타임아웃 5초 설정 (무한 로딩 방지)
        const response = await axios.get(URLS.CCTV, { httpsAgent: agent, timeout: 5000 });
        
        if (response.data && response.data.response && response.data.response.data) {
            const rawList = response.data.response.data;
            // 필요한 데이터만 정제해서 보냄
            const list = rawList.map(i => ({
                name: i.cctvname,
                url: i.cctvurl,
                lat: i.coordy,
                lng: i.coordx
            }));
            console.log(`✅ [Server] CCTV ${list.length}개 로드 성공`);
            res.json({ success: true, list: list });
        } else {
            console.warn("⚠️ [Server] 응답은 왔으나 데이터가 비어있습니다.");
            res.json({ success: false, list: [] });
        }
    } catch (e) {
        // 401 에러 등이 나면 여기서 잡힘
        console.error(`🔥 [Server] CCTV 통신 실패: ${e.message}`);
        res.json({ success: false, list: [] });
    }
});

// ----------------------------------------------------
// 2. AI 예측 (CCTV 로딩과 무관하게 동작)
// ----------------------------------------------------
app.get('/api/predict', (req, res) => {
    const now = new Date();
    const cctvId = req.query.id || 0;
    
    // 파이썬 실행
    const python = spawn('python', ['ai_server.py', now.getDay(), now.getHours(), cctvId]);
    let result = '';
    
    python.stdout.on('data', d => result += d.toString());
    
    python.on('close', () => {
        try { 
            // 정상적인 JSON 응답
            res.json(JSON.parse(result)); 
        } catch { 
            // 파이썬 에러 시 죽지 않고 "데이터 없음" 보냄
            res.json({ status: "error", speed: 0, risk: "분석 대기" }); 
        }
    });
    
    // 파이썬 실행 자체가 실패했을 때 (파일 없음 등)
    python.on('error', () => {
        res.json({ status: "error", speed: 0, risk: "AI 오류" });
    });
});

// 3. Vision AI
app.get('/api/vision/analyze', (req, res) => {
    const python = spawn('python', ['vision_server.py']);
    let result = '';
    python.stdout.on('data', d => result += d.toString());
    python.on('close', () => {
        try { res.json(JSON.parse(result)); } catch { res.json({ count: 0 }); }
    });
});

// 나머지 API들 (트래픽, VMS 등) - 에러 나도 무시하고 빈 배열 보냄
app.get('/api/traffic', async (req, res) => { try { const r=await axios.get(URLS.TRAFFIC,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({name:i.roadSectionName,speed:parseInt(i.speed),lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });
app.get('/api/vms', async (req, res) => { try { const r=await axios.get(URLS.VMS,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({id:i.vmsId,msg:i.vmsMessage,lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });
app.get('/api/warnings', async (req, res) => { try { const r=await axios.get(URLS.WARNING,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({type:i.type||"주의",msg:i.message,lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });
app.get('/api/events', async (req, res) => { try { const r=await axios.get(URLS.EVENT,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({type:i.type||"알림",msg:i.eventDetail,road:i.roadName,time:i.startDate}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });

app.listen(PORT, () => {
    console.log(`\n🚀 시스템 재가동: http://localhost:${PORT}`);
    console.log(`🔑 적용된 키: ${MY_API_KEY}`);
});