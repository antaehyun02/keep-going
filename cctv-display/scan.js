const axios = require('axios');

// 🚨🚨 님의 인증키를 여기에 넣으세요 🚨🚨
const MY_KEY = "dacf34d37c784ea0b9e9898b257e3e78"; 

// 테스트할 CCTV ID (군포IC)
const TEST_ID = "L00113"; 

// 대한민국 ITS가 사용하는 모든 주소 후보군
const domains = [
    "https://openapi.its.go.kr",   // 최신 (OpenAPI)
    "https://www.its.go.kr",       // 구형 (Web)
    "http://openapi.its.go.kr",    // 보안해제 (HTTP)
    "http://www.its.go.kr"         // 구형 (HTTP)
];

// 테스트할 기능 (영상주소 가져오기 vs 목록 가져오기)
const endpoints = [
    "/api/getCctvUrl",  // 영상 주소
    "/api/getCctvInfo"  // 정보 목록
];

async function scan() {
    console.log("\n🕵️‍♂️ [API 주소 스캐너] 작동 시작... (키 검증 중)\n");

    let successCount = 0;

    for (const domain of domains) {
        for (const endpoint of endpoints) {
            // 주소 조합
            let url = `${domain}${endpoint}?apiKey=${MY_KEY}&type=ex&cctvType=1&getType=xml`;
            
            // getCctvUrl일 때는 ID가 필요함
            if (endpoint.includes("Url")) {
                url += `&cctvId=${TEST_ID}`;
            } else {
                // getCctvInfo일 때는 범위 검색 (빠른 응답용)
                url += `&minX=127.0&maxX=127.1&minY=37.0&maxY=37.1`;
            }

            try {
                process.stdout.write(`👉 시도: ${domain}${endpoint} ... `);
                
                const response = await axios.get(url, { timeout: 3000 });
                const data = response.data;

                // 성공 판별 (XML 데이터가 정상적으로 왔는지)
                if (data.includes("<response>") && !data.includes("인증키가 유효하지")) {
                    console.log("✅ [성공!]");
                    console.log(`   🎉 정답 주소 발견: ${domain}${endpoint}`);
                    successCount++;
                    
                    // 성공한 내용을 조금 보여줌
                    if (data.includes("cctvurl")) {
                        console.log("   📺 영상 URL도 포함되어 있습니다! (완벽함)");
                    }
                } else if (data.includes("인증키가 유효하지")) {
                    console.log("❌ [실패] 인증키 오류 (키 값 확인 필요)");
                } else {
                    console.log("⚠️ [애매함] 응답은 왔으나 데이터가 없음");
                }

            } catch (error) {
                // 404 Not Found 등
                if (error.response) {
                    console.log(`🔥 [실패] 서버 응답 코드: ${error.response.status}`);
                } else {
                    console.log(`💀 [접속 불가] 도메인이 없거나 연결 실패`);
                }
            }
        }
    }

    console.log("\n------------------------------------------------");
    if (successCount > 0) {
        console.log("🎉 축하합니다! 위에서 '✅ [성공!]' 이라고 뜬 주소를 server.js에 쓰면 됩니다.");
    } else {
        console.log("😭 모든 시도가 실패했습니다.");
        console.log("   1. 인증키에 공백이 없는지 확인하세요.");
        console.log("   2. 혹시 '공공데이터포털' 키가 아닌지 다시 확인하세요.");
    }
    console.log("------------------------------------------------\n");
}

scan();