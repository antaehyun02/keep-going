const express = require('express');
const axios = require('axios');
const https = require('https');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const iconv = require('iconv-lite');
const app = express();
const PORT = 3000;

const MY_API_KEY = "dacf34d37c784ea0b9e9898b257e3e78"; 
const REGION_PARAMS = `minX=126.50&maxX=128.00&minY=36.00&maxY=37.80&getType=json`;

const URLS = {
    CCTV: `https://openapi.its.go.kr:9443/cctvInfo?apiKey=${MY_API_KEY}&type=ex&cctvType=1&${REGION_PARAMS}`,
    TRAFFIC: `https://openapi.its.go.kr:9443/trafficInfo?apiKey=${MY_API_KEY}&type=ex&routeNo=all&drcType=all&${REGION_PARAMS}`,
    WARNING: `https://openapi.its.go.kr:9443/posIncidentInfo?apiKey=${MY_API_KEY}&${REGION_PARAMS}`,
    EVENT: `https://openapi.its.go.kr:9443/eventInfo?apiKey=${MY_API_KEY}&eventType=all&${REGION_PARAMS}`,
    VMS: `https://openapi.its.go.kr:9443/vmsInfo?apiKey=${MY_API_KEY}&${REGION_PARAMS}`,
    DANGEROUS: `https://openapi.its.go.kr:9443/dangerousCarInfo?apiKey=${MY_API_KEY}&type=all&${REGION_PARAMS}`
};

app.use(express.static('public'));
app.use(express.json({ limit: '50mb' })); // Base64 이미지 처리를 위해 용량 증가
const agent = new https.Agent({ rejectUnauthorized: false });


// 취약 구간 정보 API (CSV 기반)
app.get('/api/vulnerable', (req, res) => {
    const list = [];

    // 1. 안개 취약 구간 읽기 (경부고속도로만)
    try {
        const fogPath = path.join(__dirname, 'data', '안개취약.csv');
        if (fs.existsSync(fogPath)) {
            // EUC-KR 인코딩으로 읽기
            const buffer = fs.readFileSync(fogPath);
            const content = iconv.decode(buffer, 'euc-kr');
            const lines = content.split('\n');

            for (let i = 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) continue;

                const parts = line.split(',');
                if (parts.length < 3) continue;

                const road = parts[0].trim();
                const kmRange = parts[1].trim();
                const section = parts[2].trim();

                // 경부고속도로만 필터링
                if (road.includes("경부고속도로") || road.includes("경부선")) {
                    // km 범위로 수원-천안 구간 필터링 
                    const kmMatch = kmRange.match(/(\d+)~/);
                    if (kmMatch) {
                        const startKm = parseInt(kmMatch[1]);
                        // 수원신갈 ~ 천안 구간
                        if (startKm >= 200 && startKm <= 320) {
                            list.push({
                                type: "안개",
                                road: "경부고속도로",
                                section: `${kmRange} (${section})`,
                                msg: "가시거리 주의"
                            });
                        }
                    }
                }
            }
        }
    } catch (e) {
        console.error("안개 파일 에러:", e.message);
    }

    // 2. 결빙 취약 구간 읽기 (경부고속도로 수원-천안 구간)
    try {
        const icePath = path.join(__dirname, 'data', '행정안전부_상습 결빙구간.csv');
        if (fs.existsSync(icePath)) {
            // EUC-KR 인코딩으로 읽기
            const buffer = fs.readFileSync(icePath);
            const content = iconv.decode(buffer, 'euc-kr');
            const lines = content.split('\n');

            for (let i = 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) continue;

                const parts = line.split(',');
                if (parts.length < 10) continue;

                try {
                    // 인덱스 6: 시작 위도, 7: 시작 경도
                    const lat = parseFloat(parts[6]);
                    const lng = parseFloat(parts[7]);

                    if (isNaN(lat) || isNaN(lng)) continue;

                    // ★ 경부고속도로 수원-천안 구간 (위도 36.8~37.3, 경도 127.0~127.2)
                    if (lat >= 36.8 && lat <= 37.3 && lng >= 126.9 && lng <= 127.3) {
                        const region = parts[3]?.trim() || "지역 미상";
                        const roadName = parts[4]?.trim() || "도로명 미상";

                        // 경부고속도로 관련 구간만
                        if (roadName.includes("경부") || roadName.includes("국도1호선") ||
                            region.includes("수원") || region.includes("용인") ||
                            region.includes("오산") || region.includes("평택") ||
                            region.includes("안성") || region.includes("천안")) {

                            list.push({
                                type: "결빙",
                                road: region,
                                section: roadName,
                                msg: "미끄럼 주의"
                            });

                            // 최대 50개로 제한
                            if (list.filter(item => item.type === "결빙").length >= 50) break;
                        }
                    }
                } catch (err) {
                    continue;
                }
            }
        }
    } catch (e) {
        console.error("결빙 파일 에러:", e.message);
    }

    res.json({ success: true, list: list });
});

app.get('/api/cctv/list', async (req, res) => {
    try {
        const response = await axios.get(URLS.CCTV, { httpsAgent: agent, timeout: 10000 });
        if (response.data?.response?.data) {
            const list = response.data.response.data.map(i => ({ name: i.cctvname, url: i.cctvurl, lat: i.coordy, lng: i.coordx }));
            res.json({ success: true, list });
        } else { res.json({ success: false, list: [] }); }
    } catch { res.json({ success: false, list: [] }); }
});
app.get('/api/dangerous', async (req, res) => {
    try {
        const response = await axios.get(URLS.DANGEROUS, { httpsAgent: agent, timeout: 5000 });
        const list = response.data?.response?.data?.map(i => ({ road: i.roadName || "미상", speed: parseInt(i.speed), x: i.coordx, y: i.coordy })) || [];
        res.json({ success: true, list });
    } catch { res.json({ success: false, list: [] }); }
});
app.get('/api/traffic', async (req, res) => {
    const csvPath = path.join(__dirname, 'data', 'history.csv');
    const now = new Date();
    const sectionSpeeds = { 0: [], 1: [], 2: [] };
    try {
        if (fs.existsSync(csvPath)) {
            const lines = fs.readFileSync(csvPath, 'utf-8').split('\n');
            for (let i = 1; i < lines.length; i++) {
                const p = lines[i].trim().split(',');
                if (p.length < 5) continue;
                if (parseInt(p[2]) === now.getDay() && parseInt(p[3]) === now.getHours()) {
                    if (sectionSpeeds[parseInt(p[0])]) sectionSpeeds[parseInt(p[0])].push(parseInt(p[4]));
                }
            }
        }
        const final = {};
        for (let s in sectionSpeeds) final[s] = sectionSpeeds[s].length > 0 ? Math.floor(sectionSpeeds[s].reduce((a,b)=>a+b,0)/sectionSpeeds[s].length) : 95;
        const list = [
            { name: "안성IC", lat: 37.003, lng: 127.145, speed: final[0] }, { name: "북천안IC", lat: 36.915, lng: 127.168, speed: final[0] },
            { name: "천안IC", lat: 36.845, lng: 127.182, speed: final[0] }, { name: "입장휴게소", lat: 36.935, lng: 127.170, speed: final[1] },
            { name: "수원신갈IC", lat: 37.255, lng: 127.105, speed: final[2] }, { name: "기흥IC", lat: 37.215, lng: 127.110, speed: final[2] },
            { name: "오산IC", lat: 37.145, lng: 127.095, speed: final[2] }
        ];
        res.json({ success: true, list });
    } catch { res.json({ success: true, list: [] }); }
});
app.get('/api/predict', (req, res) => {
    const python = spawn(process.platform === 'win32'?'python':'python3', ['ai_server.py', new Date().getDay(), new Date().getHours(), req.query.id||0]);
    let result = ''; python.stdout.on('data', d => result += d.toString());
    python.on('close', () => { try { res.json(JSON.parse(result)); } catch { res.json({ status: "error" }); } });
});
app.get('/api/vision/analyze', (req, res) => {
    const python = spawn(process.platform === 'win32'?'python':'python3', ['vision_server.py']);
    let result = ''; python.stdout.on('data', d => result += d.toString());
    python.on('close', () => { try { res.json(JSON.parse(result)); } catch { res.json({ count: 0 }); } });
});

app.post('/api/vision/detect', (req, res) => {
    const base64Image = req.body.frame;

    if (!base64Image) {
        return res.json({ status: 'error', message: '이미지 데이터가 필요합니다', vehicle_count: 0, congestion: { level: '분석 실패', emoji: '⚪' } });
    }

    const python = spawn(process.platform === 'win32'?'python':'python3', ['vision_detector_base64.py', base64Image]);
    let result = '';

    python.stdout.on('data', d => result += d.toString());
    python.stderr.on('data', d => console.error('YOLO stderr:', d.toString()));

    python.on('close', (code) => {
        try {
            // JSON 라인만 필터링
            const jsonLines = result.split('\n').filter(l => l.trim().startsWith('{'));
            if (jsonLines.length === 0) {
                throw new Error('No JSON output');
            }
            const parsed = JSON.parse(jsonLines[jsonLines.length - 1]);
            res.json(parsed);
        } catch (e) {
            console.error('YOLO 파싱 에러:', e.message);
            res.json({
                status: 'error',
                vehicle_count: 0,
                congestion: { level: '분석 실패', color: 'smooth', emoji: '⚪' },
                detections: []
            });
        }
    });
});
app.get('/api/vms', async (req, res) => { try { const r=await axios.get(URLS.VMS,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({id:i.vmsId,msg:i.vmsMessage,lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });
app.get('/api/warnings', async (req, res) => { try { const r=await axios.get(URLS.WARNING,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({type:"주의",msg:i.incidentMsg,lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });
app.get('/api/events', async (req, res) => { try { const r=await axios.get(URLS.EVENT,{httpsAgent:agent}); const l=r.data?.response?.data?.map(i=>({type:i.eventType,msg:i.eventDetail,road:i.roadName,lat:i.coordy,lng:i.coordx}))||[]; res.json({success:true,list:l}); } catch{res.json({success:false,list:[]});} });

app.listen(PORT, () => console.log(`\n🚀 시스템 정상 가동: http://localhost:${PORT}`));