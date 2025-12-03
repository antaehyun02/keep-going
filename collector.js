// collector.js (수정됨: 광범위 수집 모드)
const fs = require('fs');
const axios = require('axios');
const path = require('path');

// 🚨 API 키 확인
const MY_API_KEY = "dacf34d37c784ea0b9e9898b257e3e78"; 

// [수정 포인트] type=ex (고속도로) 유지하되, routeNo(노선번호) 제거
// 노선번호를 빼면 해당 좌표 안에 있는 모든 고속도로 정보를 다 가져옵니다.
const URL = `https://openapi.its.go.kr:9443/trafficInfo?apiKey=${MY_API_KEY}&type=ex&minX=127.00&maxX=127.30&minY=36.80&maxY=37.35&getType=json`;

const DATA_DIR = path.join(__dirname, 'data');
const FILE_PATH = path.join(DATA_DIR, 'history.csv');

// 폴더/파일 생성 로직
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR);
if (!fs.existsSync(FILE_PATH)) {
    fs.writeFileSync(FILE_PATH, 'date,day,hour,road_name,speed\n');
    console.log("📂 [Collector] 데이터 저장소(history.csv) 생성 완료.");
}

async function collect() {
    try {
        // HTTPS 보안 무시 옵션 (필수)
        const agent = new (require('https').Agent)({ rejectUnauthorized: false });
        const response = await axios.get(URL, { httpsAgent: agent });
        
        const items = response.data?.response?.data || [];

        if (items.length === 0) {
            console.log("⚠️ [Collector] API 응답은 왔으나 데이터가 비어있습니다. (좌표/키 확인 필요)");
            return;
        }

        const now = new Date();
        const dateStr = now.toISOString().split('T')[0];
        const day = now.getDay();
        const hour = now.getHours();

        let count = 0;
        let csvContent = "";

        items.forEach(item => {
            const name = item.roadSectionName || "이름없음";
            const speed = parseInt(item.speed);
            
            // 데이터 유효성 검사 (속도가 숫자인 경우만 저장)
            if (speed >= 0) {
                csvContent += `${dateStr},${day},${hour},${name},${speed}\n`;
                count++;
            }
        });

        if (count > 0) {
            fs.appendFileSync(FILE_PATH, csvContent);
            console.log(`💾 [${now.toLocaleTimeString()}] 성공! 데이터 ${count}건을 수집하여 저장했습니다.`);
        }

    } catch (e) {
        console.error("🔥 [Collector] 통신 에러:", e.message);
    }
}

// 시작 메시지
console.log("🚀 [Collector] 데이터 수집기 재가동 (조건 완화됨)");
collect(); // 즉시 1회 실행
setInterval(collect, 10 * 60 * 1000); // 10분마다 반복