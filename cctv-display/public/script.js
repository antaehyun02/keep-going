// ============================================================
// 1. 전역 변수 설정
// ============================================================
let cctvList = [];
let map = null;
let currentMarker = null;
let warningLayer, trafficLayer, vmsLayer; 
let trafficChart = null;  // 실시간 차트
let forecastChart = null; // AI 예보 차트
let realTimeAvgSpeed = 0; // 실시간 도로 평균 속도 (초기값 0)

// 현재 시간 표시
setInterval(() => {
    document.getElementById('current-time').textContent = new Date().toLocaleTimeString();
}, 1000);

// ============================================================
// 2. 시스템 초기화
// ============================================================
async function initSystem() {
    // 1) 지도 생성
    map = L.map('map').setView([37.05, 127.12], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
    }).addTo(map);
    
    // 2) 레이어 그룹 생성
    warningLayer = L.layerGroup().addTo(map);
    trafficLayer = L.layerGroup().addTo(map);
    vmsLayer = L.layerGroup().addTo(map);

    // 3) 차트 초기화
    initCharts();

    // 4) CCTV 목록 로드
    await loadCCTVList();

    // 5) ★ [중요] 실시간 교통정보를 최우선으로 로드 (데이터 확보)
    await loadTraffic(); 

    // 6) 나머지 데이터 로드
    loadWarnings();
    loadVMS();
    
    // 7) AI 초기 실행 (실시간 데이터가 확보된 후 실행됨)
    getAIPrediction(0);

    // 8) 주기적 갱신
    setInterval(() => {
        const id = document.getElementById('cctv-selector')?.value || 0;
        getAIPrediction(id);
    }, 4000); 

    setInterval(loadTraffic, 60000); // 1분마다 실시간 정보 갱신
}

// ============================================================
// 3. CCTV 기능 (단순 재생)
// ============================================================
async function loadCCTVList() {
    const selector = document.getElementById('cctv-selector');
    try {
        console.log("📡 CCTV 목록 로딩...");
        const res = await fetch('/api/cctv/list');
        const data = await res.json();
        
        if (data.success && data.list.length > 0) {
            cctvList = data.list;
            renderCCTVOptions(cctvList);
            let idx = cctvList.findIndex(c => c.name.includes("천안"));
            if (idx === -1) idx = 0;
            selector.value = idx;
            changeCCTV(); 
        } else {
            throw new Error("목록 없음");
        }
    } catch (e) {
        selector.innerHTML = "<option>로딩 실패</option>";
    }
}

function changeCCTV() {
    const selector = document.getElementById('cctv-selector');
    const idx = selector.value;
    const cctv = cctvList[idx];
    if (!cctv) return;

    const container = document.getElementById('video-container');
    container.innerHTML = `
        <video src="${cctv.url}" autoplay muted playsinline controls 
            style="width:100%; height:100%; object-fit:fill; background:black;"
            onerror="alert('영상 신호 없음');">
        </video>`;
    
    updateMap(cctv.lat, cctv.lng, cctv.name);
    getAIPrediction(idx); // AI 재요청
    addLog(`🎥 [채널 변경] ${cctv.name}`, 'normal');
}

// ============================================================
// 4. [핵심] AI 예측 & 이상 탐지
// ============================================================
async function getAIPrediction(cctvId = 0) {
    try {
        const res = await fetch(`/api/predict?id=${cctvId}`);
        const data = await res.json();
        
        const speedEl = document.getElementById('ai-speed');
        const riskEl = document.getElementById('ai-risk');

        if (data.status === 'success') {
            const predSpeed = data.speed || data.future_pred;
            
            // 1. AI 예측값 표시
            speedEl.innerHTML = `
                <div style="font-size:0.7rem; color:#888; margin-bottom:3px;">${data.time_msg}</div>
                <span style="font-size:1.8rem; font-weight:bold;">${predSpeed}</span> km/h
            `;
            riskEl.textContent = data.risk;
            riskEl.className = `value ${data.risk.includes("정체") ? "live badge" : "safe"}`;
            if(data.risk.includes("정체")) riskEl.style.background = "#ff3333";

            // 2. 이상 탐지 실행 (AI 평소 vs 실시간)
            checkAnomaly(data.current_normal);

            // 3. 차트
            if (data.forecast) updateForecastChart(data.forecast);
        }
    } catch (e) { console.error("AI 에러"); }
}

// ★ [수정됨] 이상 징후 감지 (데이터 0일 때 처리 추가)
function checkAnomaly(aiNormalSpeed) {
    const dispAi = document.getElementById('disp-ai-normal');
    const dispReal = document.getElementById('disp-real-speed');
    const resultBox = document.getElementById('analysis-result');

    // 1. AI 데이터 표시
    dispAi.innerText = aiNormalSpeed ? aiNormalSpeed : "--";

    // 2. 실시간 데이터가 아직 없으면 "수집 중" 표시하고 종료
    if (realTimeAvgSpeed === 0) {
        dispReal.innerText = "--";
        resultBox.style.background = "#f8f9fa";
        resultBox.style.border = "1px solid #ddd";
        resultBox.innerHTML = `
            <div style="font-weight:bold; color:#666;">⏳ 실시간 데이터 수집 중...</div>
            <div style="font-size:0.85rem;">잠시만 기다려주세요.</div>
        `;
        return;
    }

    // 3. 실시간 데이터가 있으면 표시 및 분석
    dispReal.innerText = realTimeAvgSpeed;
    const diff = aiNormalSpeed - realTimeAvgSpeed;

    if (Math.abs(diff) <= 15) {
        resultBox.style.background = "#e6fffa";
        resultBox.style.border = "1px solid #28a745";
        resultBox.innerHTML = `<div style="color:#28a745; font-weight:bold;">✅ 패턴 일치 (정상)</div><div style="font-size:0.85rem;">평소 데이터와 흐름이 비슷합니다.</div>`;
    } else if (diff > 25) { // 평소보다 25km/h 이상 느림
        resultBox.style.background = "#fff5f5";
        resultBox.style.border = "1px solid #ff3333";
        resultBox.innerHTML = `<div style="color:#ff3333; font-weight:bold;">🚨 이상 징후 감지</div><div style="font-size:0.85rem;">평소보다 <span style="font-weight:bold;">${diff}km/h</span> 느립니다!<br>사고 여부를 확인하세요.</div>`;
    } else if (diff < -20) { // 평소보다 훨씬 빠름
        resultBox.style.background = "#ebf8ff";
        resultBox.style.border = "1px solid #0066ff";
        resultBox.innerHTML = `<div style="color:#0066ff; font-weight:bold;">🚀 쾌속 질주 중</div><div style="font-size:0.85rem;">평소보다 흐름이 아주 좋습니다.</div>`;
    } else {
        resultBox.style.background = "#fffaf0";
        resultBox.style.border = "1px solid #ff9900";
        resultBox.innerHTML = `<div style="color:#ff9900; font-weight:bold;">⚠️ 약간의 변동</div><div style="font-size:0.85rem;">평소와 ${Math.abs(diff)}km/h 차이가 납니다.</div>`;
    }
}

// ============================================================
// 5. [수정됨] 실시간 교통정보 로드 (유효 데이터만 계산)
// ============================================================
async function loadTraffic() {
    try {
        const res = await fetch('/api/traffic');
        const data = await res.json();
        
        if (data.success && data.list.length > 0) {
            trafficLayer.clearLayers();
            let sum = 0, cnt = 0;
            
            data.list.forEach(i => {
                // 속도가 0인 데이터(통신오류 등)는 제외
                if (i.speed > 0) {
                    let color = i.speed < 40 ? '#ff3333' : (i.speed < 80 ? '#ff9900' : '#28a745');
                    L.circleMarker([i.lat, i.lng], {
                        radius: 5, color: color, fillColor: color, fillOpacity: 0.8
                    }).bindPopup(`<b>${i.name}</b><br>${i.speed} km/h`).addTo(trafficLayer);
                    
                    sum += i.speed;
                    cnt++;
                }
            });

            // 유효한 데이터가 있을 때만 평균 갱신
            if (cnt > 0) {
                realTimeAvgSpeed = parseInt(sum / cnt);
                updateTrafficChart(realTimeAvgSpeed);
                console.log(`✅ 실시간 평균 속도 갱신: ${realTimeAvgSpeed} km/h (샘플: ${cnt}개)`);
            } else {
                console.warn("⚠️ 유효한 교통 데이터가 없습니다. (전체 0km/h)");
            }
        }
    } catch (e) {
        console.error("교통정보 로드 실패");
    }
}

// 기타 헬퍼 함수 (기존 동일)
function renderCCTVOptions(l){const s=document.getElementById('cctv-selector');s.innerHTML="";l.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.text=c.name;s.appendChild(o)})}
function filterCCTV(){const k=document.getElementById('cctv-search').value.toLowerCase();const s=document.getElementById('cctv-selector');s.innerHTML="";let f=-1;cctvList.forEach((c,i)=>{if(c.name.toLowerCase().includes(k)){const o=document.createElement('option');o.value=i;o.text=c.name;s.appendChild(o);if(f===-1)f=i}});if(f!==-1){s.value=f;changeCCTV()}}
function updateMap(lat,lng,n){if(!map)return;if(currentMarker)map.removeLayer(currentMarker);const i=L.divIcon({className:'cam-icon',html:'📷',iconSize:[30,30]});currentMarker=L.marker([lat,lng],{icon:i}).addTo(map).bindPopup(n).openPopup();map.setView([lat,lng],13)}
function toggleLayer(t){const c=document.getElementById(`${t}-toggle`);const l=t==='warn'?warningLayer:(t==='traffic'?trafficLayer:vmsLayer);if(c.checked)map.addLayer(l);else map.removeLayer(l)}
async function loadVMS(){try{const r=await fetch('/api/vms');const d=await r.json();if(d.success){vmsLayer.clearLayers();d.list.forEach(i=>{const c=L.divIcon({className:'vms-marker',html:'📟',iconSize:[24,24]});L.marker([i.lat,i.lng],{icon:c}).bindPopup(`<div style="background:black;color:orange;padding:5px;">${i.msg}</div>`).addTo(vmsLayer)})}}catch{}}
async function loadWarnings(){try{const r=await fetch('/api/warnings');const d=await r.json();if(d.success){warningLayer.clearLayers();d.list.forEach(i=>{const c=L.divIcon({className:'warn-marker',html:'⚠️',iconSize:[24,24]});L.marker([i.lat,i.lng],{icon:c}).bindPopup(i.msg).addTo(warningLayer)})}}catch{}}
const logBox = document.getElementById('log-box');
function addLog(msg, type = 'normal') {
    const div = document.createElement('div');
    div.className = `log-item ${type}`;
    div.innerHTML = `<span class="log-time">System</span><span class="log-msg">${msg}</span>`;
    logBox.prepend(div);
    if(logBox.children.length > 20) logBox.removeChild(logBox.lastChild);
}
function initCharts(){const c1=document.getElementById('trafficChart').getContext('2d');trafficChart=new Chart(c1,{type:'line',data:{labels:[],datasets:[{label:'실시간 평균',data:[],borderColor:'#0066ff',backgroundColor:'rgba(0,102,255,0.1)',fill:true,tension:0.4}]},options:{responsive:true,maintainAspectRatio:false,scales:{y:{min:0,max:120}},plugins:{legend:{display:false}}}});const c2=document.getElementById('forecastChart').getContext('2d');forecastChart=new Chart(c2,{type:'bar',data:{labels:[],datasets:[{label:'예측 속도',data:[],backgroundColor:'#28a745',borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false,scales:{y:{beginAtZero:true,max:120}},plugins:{legend:{display:false}}}})}
function updateTrafficChart(s){const n=new Date().toLocaleTimeString('ko-KR',{hour12:false,hour:'2-digit',minute:'2-digit'});if(trafficChart.data.labels.length>10){trafficChart.data.labels.shift();trafficChart.data.datasets[0].data.shift()}trafficChart.data.labels.push(n);trafficChart.data.datasets[0].data.push(s);trafficChart.update()}
function updateForecastChart(f){if(!forecastChart)return;const l=f.map(d=>d.time);const p=f.map(d=>d.speed);const c=p.map(s=>s<40?'#ff3333':(s<80?'#ff9900':'#28a745'));forecastChart.data.labels=l;forecastChart.data.datasets[0].data=p;forecastChart.data.datasets[0].backgroundColor=c;forecastChart.update()}

initSystem();