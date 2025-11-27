// ============================================================
// 1. 전역 변수 및 설정
// ============================================================
let cctvList = [];
let map = null;
let currentMarker = null;
let warningLayer, trafficLayer, vmsLayer; 
let trafficChart = null;

const YOUTUBE_BACKUP = {
    default: "kYjC-89r5iM", // 수원신갈
    osan: "F13P5v64b24"     // 오산
};

// 시계 가동
setInterval(() => {
    document.getElementById('current-time').textContent = new Date().toLocaleTimeString();
}, 1000);

// ============================================================
// 2. 시스템 초기화
// ============================================================
async function initSystem() {
    // 지도 생성 (중심: 평택/안성 37.05, 127.12)
    map = L.map('map').setView([37.05, 127.12], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
    }).addTo(map);
    
    // 레이어 그룹 초기화
    warningLayer = L.layerGroup().addTo(map);
    trafficLayer = L.layerGroup().addTo(map);
    vmsLayer = L.layerGroup().addTo(map);

    // 차트 초기화
    initChart();

    // CCTV 목록 로드
    const selector = document.getElementById('cctv-selector');
    try {
        console.log("CCTV 목록 요청...");
        const res = await fetch('/api/cctv/list');
        const data = await res.json();
        
        if (data.success && data.list.length > 0) {
            cctvList = data.list; // 데이터 저장
            renderCCTVOptions(cctvList); // 드롭다운 렌더링
            
            // 초기 선택 (천안 또는 수원신갈)
            const initialIndex = cctvList.findIndex(c => c.name.includes("천안")) !== -1 
                ? cctvList.findIndex(c => c.name.includes("천안")) 
                : 0;
            
            selector.value = initialIndex;
            changeCCTV();
        } else {
            throw new Error("목록 없음");
        }
    } catch (e) {
        selector.innerHTML = "<option>연결 실패</option>";
        loadYoutube('default');
    }

    // 데이터 로드 실행
    loadWarnings();
    loadTraffic();
    loadVMS();
    loadEvents();
    refreshIntegratedLog();
    getAIPrediction();

    // 주기적 갱신 설정
    setInterval(getAIPrediction, 4000);
    setInterval(refreshIntegratedLog, 30000);
    setInterval(loadEvents, 60000);
    setInterval(loadTraffic, 60000); // 1분마다 소통정보 & 차트 갱신
}

// ============================================================
// 3. CCTV 기능 (검색 포함)
// ============================================================
// 검색창 필터링 함수
function filterCCTV() {
    const keyword = document.getElementById('cctv-search').value.toLowerCase();
    const selector = document.getElementById('cctv-selector');
    
    selector.innerHTML = ""; // 초기화

    cctvList.forEach((cctv, index) => {
        if (cctv.name.toLowerCase().includes(keyword)) {
            const option = document.createElement('option');
            option.value = index; // 원래 인덱스 유지
            option.text = cctv.name;
            selector.appendChild(option);
        }
    });

    // 검색 결과가 있으면 첫 번째 항목 선택
    if (selector.options.length > 0) {
        selector.selectedIndex = 0;
        changeCCTV();
    } else {
        selector.innerHTML = "<option>검색 결과 없음</option>";
    }
}

// 초기 옵션 렌더링 도우미
function renderCCTVOptions(list) {
    const selector = document.getElementById('cctv-selector');
    selector.innerHTML = "";
    list.forEach((cctv, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.text = cctv.name;
        selector.appendChild(option);
    });
}

function changeCCTV() {
    const selector = document.getElementById('cctv-selector');
    // 검색 결과 없음을 선택했을 때 방지
    if (selector.value === "" || isNaN(selector.value)) return;

    const index = selector.value;
    const cctv = cctvList[index];
    
    if (!cctv) return;

    const container = document.getElementById('video-container');
    container.innerHTML = `<video src="${cctv.url}" autoplay muted playsinline controls style="width:100%;height:100%;object-fit:fill;" onerror="handleVideoError('${cctv.name}')"></video>`;
    
    addLog(`🎥 [채널전환] ${cctv.name}`, 'normal');
    updateMap(cctv.lat, cctv.lng, cctv.name);
    setTimeout(() => analyzeVideoFrame(cctv.name), 2000);
}

function updateMap(lat, lng, name) {
    if (!map) return;
    if (currentMarker) map.removeLayer(currentMarker);
    const icon = L.divIcon({ className: 'cam-icon', html: '<div style="font-size:30px; filter:drop-shadow(2px 2px 2px rgba(0,0,0,0.5));">📷</div>', iconSize: [30,30], iconAnchor: [15,15] });
    currentMarker = L.marker([lat, lng], { icon: icon }).addTo(map).bindPopup(`<b>${name}</b>`).openPopup();
    map.setView([lat, lng], 13);
}

function handleVideoError(name) {
    loadYoutube(name.includes("오산") ? 'osan' : 'default');
    addLog(`⚠ [신호손실] ${name} -> 백업망`, 'warning');
}
function loadYoutube(key) {
    const id = YOUTUBE_BACKUP[key];
    document.getElementById('video-container').innerHTML = `<iframe src="https://www.youtube.com/embed/${id}?autoplay=1&mute=1&controls=0&loop=1&playlist=${id}&showinfo=0&modestbranding=1" width="100%" height="100%" frameborder="0" style="pointer-events:none;"></iframe>`;
}

// ============================================================
// 4. 지도 레이어 데이터 로드
// ============================================================

// (1) 소통정보 (Traffic Info) -> 지도 마커 & 차트 업데이트
async function loadTraffic() {
    try {
        const res = await fetch('/api/traffic');
        const data = await res.json();
        if (data.success) {
            trafficLayer.clearLayers();
            let totalSpeed = 0, count = 0;

            data.list.forEach(i => {
                let color = "#28a745"; 
                if (i.speed < 40) color = "#ff3333";
                else if (i.speed < 80) color = "#ff9900";

                const marker = L.circleMarker([i.lat, i.lng], {
                    radius: 5, fillColor: color, color: "#fff", weight: 1, opacity: 1, fillOpacity: 0.8
                }).bindPopup(`<b>🚦 ${i.name}</b><br>속도: ${i.speed}km/h`);
                trafficLayer.addLayer(marker);

                if(i.speed > 0) { totalSpeed += i.speed; count++; }
            });

            // 차트 업데이트
            if (count > 0) updateChart((totalSpeed / count).toFixed(1));
        }
    } catch {}
}

// (2) VMS (전광판)
async function loadVMS() {
    try {
        const res = await fetch('/api/vms');
        const data = await res.json();
        if (data.success) {
            vmsLayer.clearLayers();
            data.list.forEach(i => {
                const icon = L.divIcon({ className: 'vms-marker', html: '📟', iconSize: [24,24] });
                const content = `<div style="background:black;color:orange;padding:5px;font-family:monospace;">${i.msg}</div>`;
                L.marker([i.lat, i.lng], { icon: icon }).bindPopup(content).addTo(vmsLayer);
            });
        }
    } catch {}
}

// (3) 주의구간
async function loadWarnings() {
    try {
        const res = await fetch('/api/warnings');
        const data = await res.json();
        if (data.success) {
            warningLayer.clearLayers();
            data.list.forEach(i => {
                const icon = L.divIcon({ className: 'warn-marker', html: '⚠️', iconSize: [24,24] });
                L.marker([i.lat, i.lng], { icon: icon }).bindPopup(`[${i.type}] ${i.msg}`).addTo(warningLayer);
            });
        }
    } catch {}
}

function toggleLayer(type) {
    const chk = document.getElementById(`${type}-toggle`);
    const layer = type === 'warn' ? warningLayer : (type === 'traffic' ? trafficLayer : vmsLayer);
    if(chk.checked) map.addLayer(layer); else map.removeLayer(layer);
}

// ============================================================
// 5. 하단 정보 및 차트
// ============================================================

async function loadEvents() {
    try {
        const res = await fetch('/api/events');
        const data = await res.json();
        const tbody = document.getElementById('event-list-body');
        if (data.success && data.list.length > 0) {
            tbody.innerHTML = "";
            data.list.forEach(i => {
                const row = document.createElement('tr');
                let color = i.type.includes("사고") ? "#ff3333" : (i.type.includes("공사") ? "#ff9900" : "#666");
                row.innerHTML = `<td><span class="event-badge" style="background:${color}">${i.type}</span></td><td>${i.time.substring(0,16)}</td><td>${i.road}</td><td style="text-align:left;">${i.msg}</td>`;
                tbody.appendChild(row);
            });
        } else { tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#999;">현재 돌발상황 없음</td></tr>'; }
    } catch {}
}

function initChart() {
    const ctx = document.getElementById('trafficChart').getContext('2d');
    trafficChart = new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: [{ label: '구간 평균 속도 (km/h)', data: [], borderColor: '#0066ff', backgroundColor: 'rgba(0,102,255,0.1)', fill: true, tension: 0.4 }] },
        options: { responsive: true, maintainAspectRatio: false, scales: { x: { display: false }, y: { min: 0, max: 120 } }, plugins: { legend: { display: true } } }
    });
}

function updateChart(speed) {
    const now = new Date().toLocaleTimeString('ko-KR', { hour12: false });
    if (trafficChart.data.labels.length > 15) {
        trafficChart.data.labels.shift();
        trafficChart.data.datasets[0].data.shift();
    }
    trafficChart.data.labels.push(now);
    trafficChart.data.datasets[0].data.push(speed);
    trafficChart.update();
}

// ============================================================
// 6. 로그 및 AI
// ============================================================
const logBox = document.getElementById('log-box');
function addLog(msg, type='normal') {
    const div = document.createElement('div');
    div.className = `log-item ${type}`;
    div.innerHTML = `<span class="log-time">[${new Date().toLocaleTimeString('ko-KR',{hour12:false})}]</span><span>${msg}</span>`;
    logBox.prepend(div);
    if(logBox.children.length > 30) logBox.removeChild(logBox.lastChild);
}

async function refreshIntegratedLog() {
    try {
        const eRes = await fetch('/api/events'); const eData = await eRes.json();
        const wRes = await fetch('/api/warnings'); const wData = await wRes.json();
        let items = [];
        if(eData.success) eData.list.forEach(i=>items.push({type:'event', msg:i.msg, lat:i.lat, lng:i.lng}));
        if(wData.success) wData.list.forEach(i=>items.push({type:'warn', msg:`[${i.type}] ${i.msg}`, lat:i.lat, lng:i.lng}));
        
        logBox.innerHTML = "";
        items.slice(0,20).forEach(item => {
            const div = document.createElement('div');
            div.className = `log-item ${item.type==='event'?'danger':'warning'}`;
            div.style.cursor='pointer';
            div.onclick = () => { map.setView([item.lat, item.lng], 13); L.popup().setLatLng([item.lat, item.lng]).setContent(item.msg).openOn(map); };
            div.innerHTML = `<span class="log-time">${item.type==='event'?'🚧':'⚠️'}</span><span class="log-msg">${item.msg}</span>`;
            logBox.appendChild(div);
        });
        if(items.length===0) addLog("특이사항 없음", "normal");
    } catch {}
}

async function getAIPrediction() {
    try {
        const res = await fetch('/api/predict');
        const data = await res.json();
        if (data.speed) {
            document.getElementById('ai-speed').textContent = `${data.speed} km/h`;
            const el = document.getElementById('ai-risk');
            el.textContent = data.speed < 40 ? "정체" : (data.speed < 80 ? "서행" : "원활");
            el.className = `value ${data.speed < 40 ? 'danger' : 'safe'}`;
        }
    } catch {}
}

async function analyzeVideoFrame(name) {
    try {
        const res = await fetch('/api/vision/analyze');
        const data = await res.json();
        if (data.status === 'success') {
            document.getElementById('ai-risk').textContent += ` (${data.count}대)`;
        }
    } catch {}
}

initSystem();