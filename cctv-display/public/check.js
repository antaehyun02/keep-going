const axios = require('axios');
const https = require('https');

// 🚨 가지고 있는 키를 모두 넣어보세요 (없으면 비워두세요)
const ITS_KEY = "dacf34d37c784ea0b9e9898b257e3e78"; 
const DATA_GO_KEY = "AgBXblXak6wS+O95/W87Cz//EWibnqETZR4NuqHiGgsoZ2etyAQHzEeajITHAVEm+mXLNfJAW4snSYa8GryHzA=="; 

const TEST_ID = "L00113"; // 군포IC

// 보안 무시 설정 (핫스팟 환경에서 필수일 수음)
const agent = new https.Agent({ rejectUnauthorized: false });

async function diagnose() {
    console.log("\n🕵️‍♂️ [핫스팟 환경] 연결 진단 시작...\n");

    // 1. ITS 서버 테스트
    console.log("👉 [테스트 1] ITS 서버 (openapi.its.go.kr)");
    try {
        const url = `https://openapi.its.go.kr/api/getCctvUrl?apiKey=${ITS_KEY}&cctvId=${TEST_ID}&cctvType=1&type=ex&getType=xml`;
        const res = await axios.get(url, { httpsAgent: agent, timeout: 5000 });
        
        if (res.data.includes("<cctvurl>")) {
            console.log("✅ [성공] ITS 키가 작동합니다! (IP 등록 완료됨)");
            console.log("   => server.js에 ITS 주소와 키를 쓰세요.");
            return;
        } else {
            console.log("❌ [실패] " + res.data.substring(0, 100));
        }
    } catch (e) { console.log("💀 [접속 불가] " + e.message); }

    console.log("------------------------------------------------");

    // 2. 공공데이터포털 서버 테스트 (IP 등록 필요 없음)
    console.log("👉 [테스트 2] 공공데이터포털 (apis.data.go.kr)");
    try {
        // 공공데이터포털은 Decoding된 키를 써야 할 수도 있습니다.
        const url = `http://apis.data.go.kr/1613000/CctvInfoService/getCctvUrl?serviceKey=${DATA_GO_KEY}&cctvId=${TEST_ID}&cctvType=1&type=ex`;
        const res = await axios.get(url, { timeout: 5000 });

        if (res.data.includes("<cctvurl>")) {
            console.log("✅ [성공] 공공데이터포털 키가 작동합니다!");
            console.log("   => server.js에 공공데이터 주소와 키를 쓰세요.");
            return;
        } else {
            console.log("❌ [실패] " + res.data.substring(0, 100));
        }
    } catch (e) { console.log("💀 [접속 불가] " + e.message); }

    console.log("\n😭 [진단 결과] 둘 다 안 됩니다.");
    console.log("   1. ITS 키라면: IP 재등록 후 30분 대기 필수.");
    console.log("   2. 공공데이터 키라면: '활용신청'이 안 된 상태.");
}

diagnose();