let cctvList = [], map = null, currentMarker = null;
let trafficLayer; // 경고 레이어 제거됨
let forecastChart = null;
let realTimeAvgSpeed = 0; 

// 전역 변수로 돌발상황 데이터 저장 (병합용)
let currentEvents = [];
let currentWarnings = [];

setInterval(() => {
    const timeEl = document.getElementById('current-time');
    if(timeEl) timeEl.textContent = new Date().toLocaleTimeString();
}, 1000);

async function initSystem() {
    map = L.map('map').setView([37.05, 127.12], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(map);
    
    // 소통정보 레이어만 추가
    trafficLayer = L.layerGroup().addTo(map);

    initCharts();
    
    updateAiPanel(0); // 초기화

    await loadCCTVList();
    await loadTraffic();

    // 돌발 및 주의 정보 로드 (지도 표시 X, 하단 리스트 O)
    loadEvents();
    loadWarnings();
    
    getAIPrediction(0);

    setInterval(() => {
        const id = document.getElementById('cctv-selector')?.value || 0;
        getAIPrediction(id);
    }, 4000); 

    setInterval(loadTraffic, 60000);
    setInterval(() => { loadEvents(); loadWarnings(); }, 60000); // 1분마다 갱신
}

// ----------------------------------------------------
// ★ 돌발상황 & 주의구간 데이터 로드 및 리스트 통합 표시
// ----------------------------------------------------
async function loadEvents() {
    try {
        const res = await fetch('/api/events');
        const data = await res.json();
        currentEvents = data.success ? data.list : [];
        renderIncidentList(); // 화면 갱신
    } catch { currentEvents = []; }
}

async function loadWarnings() {
    try {
        const res = await fetch('/api/warnings');
        const data = await res.json();
        currentWarnings = data.success ? data.list : [];
        renderIncidentList(); // 화면 갱신
    } catch { currentWarnings = []; }
}

// ★ 하단 리스트 렌더링 함수 (핵심)
function renderIncidentList() {
    const listEl = document.getElementById('incident-list');
    if (!listEl) return;

    // 두 데이터 병합
    const allIncidents = [...currentEvents, ...currentWarnings];
    listEl.innerHTML = "";

    if (allIncidents.length === 0) {
        listEl.innerHTML = `<li style="text-align: center; color: #888; padding: 20px;">✅ 현재 돌발/주의 구간이 없습니다.</li>`;
        return;
    }

    allIncidents.forEach(item => {
        const li = document.createElement('li');
        li.style.cssText = "background: white; border-left: 4px solid #ff5e62; padding: 10px; margin-bottom: 8px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: flex; align-items: center;";
        
        let icon = '⚠️';
        let typeClass = '주의';
        let title = item.msg || "정보 없음";
        
        // 타입 구분
        if (item.type && item.type.includes("공사")) { icon = '🚧'; typeClass = '공사'; }
        else if (item.type && item.type.includes("사고")) { icon = '🚗💥'; typeClass = '사고'; }
        
        // 주의운전구간일 경우
        if (item.msg && item.msg.includes("주의")) { icon = '🛑'; typeClass = '주의'; }

        li.innerHTML = `
            <div style="font-size: 1.5rem; margin-right: 15px;">${icon}</div>
            <div style="flex: 1;">
                <div style="font-weight: bold; color: #333;">
                    <span style="color: #d63031;">[${typeClass}]</span> ${item.road || "구간 정보"}
                </div>
                <div style="font-size: 0.9rem; color: #666; margin-top: 2px;">${title}</div>
            </div>
        `;
        listEl.appendChild(li);
    });
}

// ----------------------------------------------------
// CCTV (기존 로직 유지)
// ----------------------------------------------------
async function loadCCTVList() {
    const selector = document.getElementById('cctv-selector');
    try {
        const res = await fetch('/api/cctv/list');
        const data = await res.json();
        if (data.success && data.list.length > 0) {
            const keywords = ["수원", "신갈", "기흥", "남사", "오산", "안성", "천안", "입장", "망향", "북천안"];
            let filtered = data.list.filter(c => keywords.some(k => c.name.includes(k)));
            if (filtered.length === 0) filtered = data.list;
            cctvList = filtered;
            renderCCTVOptions(cctvList);
            let idx = cctvList.findIndex(c => c.name.includes("천안"));
            if (idx === -1) idx = 0;
            selector.value = idx;
            changeCCTV();
        } else { selector.innerHTML = "<option>목록 없음</option>"; }
    } catch { selector.innerHTML = "<option>로딩 실패</option>"; }
}

function changeCCTV() {
    const selector = document.getElementById('cctv-selector');
    const idx = selector.value;
    const cctv = cctvList[idx];
    if (!cctv) return;

    document.getElementById('video-container').innerHTML = 
        `<video src="${cctv.url}" autoplay muted playsinline controls style="width:100%; height:100%; object-fit:fill; background:black;" onerror="alert('영상 신호 없음');"></video>`;
    
    updateMap(cctv.lat, cctv.lng, cctv.name);
    
    const aiSpeed = document.getElementById('ai-speed');
    if(aiSpeed) aiSpeed.innerHTML = '<span style="font-size:1rem; color:#888;">분석 중...</span>';
    
    const dispAi = document.getElementById('disp-ai-normal');
    if(dispAi) dispAi.innerText = "--";
    
    const resultBox = document.getElementById('analysis-result');
    if(resultBox) {
        resultBox.style.background = "#f8f9fa";
        resultBox.innerHTML = `<div style="color:#666;">🔄 AI 분석 중...</div>`;
    }

    let sectionId = 0;
    if (cctv.name.includes("수원") || cctv.name.includes("신갈") || cctv.name.includes("남사")) sectionId = 2;
    else if (cctv.name.includes("입장") || cctv.name.includes("북천안")) sectionId = 1;
    else sectionId = 0;

    setTimeout(() => { getAIPrediction(sectionId); }, 500); 
}

// ----------------------------------------------------
// AI 예측 (평소 패턴만)
// ----------------------------------------------------
async function getAIPrediction(cctvId = 0) {
    try {
        const res = await fetch(`/api/predict?id=${cctvId}`);
        const data = await res.json();
        
        if (data.status === 'success') {
            const speed = data.speed || data.future_pred;
            const speedEl = document.getElementById('ai-speed');
            if(speedEl) speedEl.innerHTML = `<div style="font-size:0.7rem; color:#888; margin-bottom:3px;">${data.time_msg}</div><span style="font-size:1.8rem; font-weight:bold;">${speed}</span> km/h`;
            
            const riskEl = document.getElementById('ai-risk');
            if(riskEl) {
                riskEl.textContent = data.risk;
                riskEl.className = `value ${data.risk.includes("정체") ? "live badge" : "safe"}`;
                riskEl.style.background = data.risk.includes("정체") ? "#ff3333" : "";
            }

            updateAiPanel(data.current_normal);
            if (data.forecast) updateForecastChart(data.forecast);
        }
    } catch {}
}

function updateAiPanel(aiNormalSpeed) {
    const dispAi = document.getElementById('disp-ai-normal');
    const resultBox = document.getElementById('analysis-result');
    if(dispAi) dispAi.innerText = aiNormalSpeed || "--";
    if (!resultBox || !aiNormalSpeed) return;

    if (aiNormalSpeed >= 80) {
        resultBox.style.background = "#e6fffa";
        resultBox.style.border = "1px solid #28a745";
        resultBox.innerHTML = `<div style="color:#28a745; font-weight:bold;">✅ 평소 원활 구간</div><div style="font-size:0.85rem;">이 시간대에는 보통 소통이 원활합니다.</div>`;
    } else if (aiNormalSpeed >= 40) {
        resultBox.style.background = "#fffaf0";
        resultBox.style.border = "1px solid #ff9900";
        resultBox.innerHTML = `<div style="color:#ff9900; font-weight:bold;">⚠️ 평소 서행 구간</div><div style="font-size:0.85rem;">차량이 많아 서행하는 시간대입니다.</div>`;
    } else {
        resultBox.style.background = "#fff5f5";
        resultBox.style.border = "1px solid #ff3333";
        resultBox.innerHTML = `<div style="color:#ff3333; font-weight:bold;">🚨 평소 정체 구간</div><div style="font-size:0.85rem;">상습 정체가 발생하는 시간대입니다.</div>`;
    }
}

// ----------------------------------------------------
// 실시간 소통정보 (지도 표시용)
// ----------------------------------------------------
async function loadTraffic() {
    try {
        const res = await fetch('/api/traffic');
        const data = await res.json();
        if (data.success) {
            trafficLayer.clearLayers();
            data.list.forEach(i => {
                const spd = parseInt(i.speed);
                if (!isNaN(spd) && spd > 0) {
                    let color = spd < 40 ? '#ff3333' : (spd < 80 ? '#ff9900' : '#28a745');
                    L.circleMarker([i.lat, i.lng], {
                        radius: 5, color: color, fillColor: color, fillOpacity: 0.8
                    }).bindPopup(`<b>${i.name}</b><br>${spd} km/h`).addTo(trafficLayer);
                }
            });
        }
    } catch {}
}

// 헬퍼 함수
function renderCCTVOptions(l){const s=document.getElementById('cctv-selector');s.innerHTML="";l.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.text=c.name;s.appendChild(o)})}
function filterCCTV(){const k=document.getElementById('cctv-search').value.toLowerCase();const s=document.getElementById('cctv-selector');s.innerHTML="";let f=-1;cctvList.forEach((c,i)=>{if(c.name.toLowerCase().includes(k)){const o=document.createElement('option');o.value=i;o.text=c.name;s.appendChild(o);if(f===-1)f=i}});if(f!==-1){s.value=f;changeCCTV()}}
function updateMap(lat,lng,n){if(!map)return;if(currentMarker)map.removeLayer(currentMarker);const i=L.divIcon({className:'cam-icon',html:'📷',iconSize:[30,30]});currentMarker=L.marker([lat,lng],{icon:i}).addTo(map).bindPopup(n).openPopup();map.setView([lat,lng],13)}
function toggleLayer(t){const c=document.getElementById(`${t}-toggle`);if(t==='traffic'){if(c.checked)map.addLayer(trafficLayer);else map.removeLayer(trafficLayer)}}
function initCharts(){const c1=document.getElementById('forecastChart').getContext('2d');forecastChart=new Chart(c1,{type:'bar',data:{labels:[],datasets:[{label:'예측 속도',data:[],backgroundColor:'#28a745',borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false,scales:{y:{beginAtZero:true,max:120}},plugins:{legend:{display:false}}}})}
function updateForecastChart(f){if(!forecastChart)return;const l=f.map(d=>d.time);const p=f.map(d=>d.speed);const c=p.map(s=>s<40?'#ff3333':(s<80?'#ff9900':'#28a745'));forecastChart.data.labels=l;forecastChart.data.datasets[0].data=p;forecastChart.data.datasets[0].backgroundColor=c;forecastChart.update()}

initSystem();