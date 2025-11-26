// ============================================================
// 1. 기본 설정 및 전역 변수
// ============================================================

// 현재 시계 가동
setInterval(() => {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleTimeString();
}, 1000);

// 전역 변수 (데이터 저장용)
let cctvList = [];      // 서버에서 받아온 CCTV 목록
let map = null;         // 지도 객체
let currentMarker = null; // 지도 위에 찍힌 마커

// 유튜브 백업 링크 (영상 로딩 실패 시 사용)
const YOUTUBE_BACKUP = {
    default: "kYjC-89r5iM", // 수원신갈 (기본)
    osan: "F13P5v64b24"     // 오산
};

// ============================================================
// 2. 시스템 초기화 (페이지 로드 시 실행)
// ============================================================
async function initSystem() {
    // 1) 지도 생성 (초기 위치: 수원-오산 중간 지점)
    map = L.map('map').setView([37.20, 127.10], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
    }).addTo(map);

    const selector = document.getElementById('cctv-selector');
    
    try {
        console.log("📡 서버에 CCTV 목록 요청 중...");
        const res = await fetch('/api/cctv/list');
        const data = await res.json();

        if (data.success && data.list.length > 0) {
            cctvList = data.list; // 목록 저장
            
            // 2) 드롭다운 메뉴 채우기
            selector.innerHTML = "";
            cctvList.forEach((cctv, index) => {
                const option = document.createElement('option');
                option.value = index; // 배열 인덱스를 value로 사용
                option.text = cctv.name;
                
                // '수원신갈'을 기본 선택값으로 설정
                if (cctv.name.includes("수원신갈")) {
                    option.selected = true;
                }
                selector.appendChild(option);
            });

            // 3) 초기 CCTV 재생
            changeCCTV(); 
        } else {
            throw new Error("목록 없음");
        }
    } catch (e) {
        console.error(e);
        selector.innerHTML = "<option>⚠ 연결 실패 (유튜브 모드)</option>";
        loadYoutube('default'); // 실패 시 유튜브 재생
    }

    // 4) AI 예측 데이터 가져오기 시작
    getAIPrediction();
    setInterval(getAIPrediction, 4000); // 4초마다 갱신
}

// ============================================================
// 3. CCTV 변경 및 지도 연동 (핵심 기능)
// ============================================================
function changeCCTV() {
    const selector = document.getElementById('cctv-selector');
    const index = selector.value;
    const cctv = cctvList[index]; // 선택된 CCTV 데이터 가져오기
    
    if (!cctv) return;

    console.log(`🎥 채널 변경: ${cctv.name}`);

    // 1) 영상 플레이어 교체
    const container = document.getElementById('video-container');
    // muted, autoplay, playsinline은 자동재생 필수 속성
    container.innerHTML = `
        <video src="${cctv.url}" autoplay muted playsinline controls 
            style="width:100%; height:100%; object-fit:fill;"
            onerror="handleVideoError('${cctv.name}')"> 
        </video>`;
    
    // 2) 지도 위치 이동 및 마커 찍기
    updateMap(cctv.lat, cctv.lng, cctv.name);

    // 3) 로그 출력
    addLog(`🎥 [채널전환] ${cctv.name} 영상 수신 중...`, 'normal');
}

// 지도 업데이트 함수
function updateMap(lat, lng, name) {
    if (!map) return;

    // 기존 마커 삭제 (하나만 깔끔하게 유지)
    if (currentMarker) {
        map.removeLayer(currentMarker);
    }

    // 카메라 이모지 아이콘 만들기
    const cameraIcon = L.divIcon({
        className: 'custom-camera-icon',
        html: `<div style="font-size:30px; filter: drop-shadow(3px 3px 2px rgba(0,0,0,0.3));">📷</div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });

    // 새 마커 찍기
    currentMarker = L.marker([lat, lng], { icon: cameraIcon }).addTo(map);
    
    // 마커 위에 말풍선 띄우기
    currentMarker.bindPopup(`<b>📍 ${name}</b>`).openPopup();

    // 지도를 해당 위치로 부드럽게 이동 (Zoom 레벨 14)
    map.flyTo([lat, lng], 14, {
        animate: true,
        duration: 1.5 // 1.5초 동안 이동
    });
}

// 영상 에러 처리 (유튜브 백업)
function handleVideoError(cctvName) {
    console.warn(`영상 재생 실패 (${cctvName}) -> 유튜브 전환`);
    
    // 이름에 '오산'이 있으면 오산 영상, 아니면 수원 영상 틀기
    const key = cctvName.includes("오산") ? "osan" : "default";
    loadYoutube(key);
    
    addLog(`⚠ [신호손실] ${cctvName} -> 백업망 전환`, 'warning');
}

function loadYoutube(key) {
    const id = YOUTUBE_BACKUP[key] || YOUTUBE_BACKUP.default;
    document.getElementById('video-container').innerHTML = 
        `<iframe src="https://www.youtube.com/embed/${id}?autoplay=1&mute=1&controls=0&loop=1&playlist=${id}&showinfo=0&modestbranding=1" width="100%" height="100%" frameborder="0" style="pointer-events:none;"></iframe>`;
}

// ============================================================
// 4. AI 데이터 처리 및 로그 시스템
// ============================================================
const logBox = document.getElementById('log-box');

// 로그 추가 함수
function addLog(msg, type='normal') {
    const div = document.createElement('div');
    div.className = `log-item ${type}`;
    const time = new Date().toLocaleTimeString('ko-KR', { hour12: false });
    div.innerHTML = `<span class="log-time">[${time}]</span><span class="log-msg">${msg}</span>`;
    
    logBox.prepend(div); // 최신 로그를 위로
    
    // 로그가 20개 넘으면 오래된 것 삭제 (메모리 관리)
    if (logBox.children.length > 20) {
        logBox.removeChild(logBox.lastChild);
    }
}

// AI 예측 데이터 가져오기
async function getAIPrediction() {
    try {
        const res = await fetch('/api/predict');
        const data = await res.json();
        
        const speedEl = document.getElementById('ai-speed');
        const riskEl = document.getElementById('ai-risk');

        // 데이터가 정상적일 때만 업데이트
        if (data.speed) {
            speedEl.textContent = `${data.speed} km/h`;
            riskEl.textContent = data.risk;
            
            // 현재 선택된 CCTV 이름 가져오기 (로그용)
            const selector = document.getElementById('cctv-selector');
            const currentName = selector.options[selector.selectedIndex]?.text || "현재 구간";

            // 위험도에 따른 스타일 및 로그 처리
            if (data.speed < 40) {
                // 정체 (위험)
                riskEl.style.color = "#ff3333"; 
                addLog(`🚨 [AI 경고] ${currentName} 정체 발생! (${data.speed}km/h)`, 'danger');
            } else if (data.speed < 80) {
                // 서행 (주의)
                riskEl.style.color = "orange";
                // 너무 자주 뜨지 않게 확률 조정
                if (Math.random() > 0.7) addLog(`🐢 [AI 분석] ${currentName} 차량 증가 중`, 'warning');
            } else {
                // 원활 (안전)
                riskEl.style.color = "#28a745";
                if (Math.random() > 0.85) addLog(`✅ [AI 분석] ${currentName} 소통 원활`, 'normal');
            }
        }
    } catch (e) {
        console.error("AI 통신 실패");
    }
}

// ============================================================
// 5. 차트 설정 (Chart.js)
// ============================================================
const ctx = document.getElementById('trafficChart').getContext('2d');
new Chart(ctx, {
    type: 'line',
    data: {
        labels: ['14:00', '14:10', '14:20', '14:30', '14:40', '14:50'],
        datasets: [{
            label: '실시간 교통량 (대/시)',
            data: [3200, 3400, 3100, 4500, 4100, 3900], // 시연용 데이터
            borderColor: '#0066ff',
            backgroundColor: 'rgba(0, 102, 255, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4 // 곡선 부드럽게
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            y: { grid: { color: '#eee' } },
            x: { grid: { display: false } }
        }
    }
});

// 시스템 시작!
initSystem();