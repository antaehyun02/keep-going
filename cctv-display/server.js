const express = require('express');
const axios = require('axios');
const https = require('https');
const { spawn } = require('child_process');
const app = express();
const PORT = 3000;

// 🚨 API 키 (확인됨)
const MY_API_KEY = "dacf34d37c784ea0b9e9898b257e3e78"; 

// 좌표: 수원~천안
const BASE_PARAMS = `apiKey=${MY_API_KEY}&type=ex&minX=127.00&maxX=127.30&minY=36.80&maxY=37.35&getType=json`;

const URLS = {
    // ★ cctvType=1 (MP4) 설정: 님이 성공했던 방식
    CCTV: `https://openapi.its.go.kr:9443/cctvInfo?${BASE_PARAMS}&cctvType=1`,
    TRAFFIC: `https://openapi.its.go.kr:9443/trafficInfo?${BASE_PARAMS}&routeNo=0010&drcType=all`,
    WARNING: `https://openapi.its.go.kr:9443/posIncidentInfo?${BASE_PARAMS}`,
    EVENT: `https://openapi.its.go.kr:9443/eventInfo?${BASE_PARAMS}&eventType=all`,
    VMS: `https://openapi.its.go.kr:9443/vmsInfo?${BASE_PARAMS}`
};

app.use(express.static('public'));
const agent = new https.Agent({ rejectUnauthorized: false });

// 1. CCTV 목록
app.get('/api/cctv/list', async (req, res) => {
    try {
        const response = await axios.get(URLS.CCTV, { httpsAgent: agent, timeout: 5000 });
        if (response.data?.response?.data) {
            const list = response.data.response.data.map(i => ({
                name: i.cctvname, url: i.cctvurl, lat: i.coordy, lng: i.coordx
            }));
            console.log(`📦 CCTV ${list.length}개 로드됨`);
            res.json({ success: true, list });
        } else {
            res.json({ success: false, list: [] });
        }
    } catch (e) {
        console.error("CCTV 에러:", e.message);
        res.json({ success: false, list: [] });
    }
});

// 2. AI 예측
app.get('/api/predict', (req, res) => {
    const now = new Date();
    const cctvId = req.query.id || 0;
    
    const python = spawn('python', ['ai_server.py', now.getDay(), now.getHours(), cctvId]);
    let result = '';
    
    python.stdout.on('data', d => result += d.toString());
    python.on('close', () => {
        try { res.json(JSON.parse(result)); } 
        catch { res.json({ status: "error", speed: 0, risk: "데이터 없음" }); }
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

// 기타 API
app.get('/api/traffic', async (req, res) => { try { const r=await axios.get(URLS.TRAFFIC,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({name:i.roadSectionName,speed:parseInt(i.speed),lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });
app.get('/api/vms', async (req, res) => { try { const r=await axios.get(URLS.VMS,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({id:i.vmsId,msg:i.vmsMessage,lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });
app.get('/api/warnings', async (req, res) => { try { const r=await axios.get(URLS.WARNING,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({type:i.type||"주의",msg:i.message,lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });
app.get('/api/events', async (req, res) => { try { const r=await axios.get(URLS.EVENT,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({type:i.type||"알림",msg:i.eventDetail,road:i.roadName,time:i.startDate}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });

app.listen(PORT, () => console.log(`\n🚀 시스템 가동: http://localhost:${PORT}`));