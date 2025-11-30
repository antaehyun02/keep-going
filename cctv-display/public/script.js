// public/script.js (전체 덮어쓰기)

let cctvList = [];
let map = null;
let currentMarker = null;
let warningLayer, trafficLayer, vmsLayer; 
let trafficChart = null;

setInterval(() => { document.getElementById('current-time').textContent = new Date().toLocaleTimeString(); }, 1000);

async function initSystem() {
    map = L.map('map').setView([37.05, 127.12], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    
    warningLayer = L.layerGroup().addTo(map);
    trafficLayer = L.layerGroup().addTo(map);
    vmsLayer = L.layerGroup().addTo(map);

    initChart();
    await loadCCTVList();

    loadWarnings();
    loadTraffic();
    loadVMS();
    loadEvents();
    refreshIntegratedLog();
    
    // 초기 실행
    getAIPrediction(0);

    setInterval(() => {
        // 현재 선택된 CCTV ID 기준으로 AI 갱신
        const id = document.getElementById('cctv-selector').value || 0;
        getAIPrediction(id);
    }, 4000);

    setInterval(refreshIntegratedLog, 30000);
    setInterval(loadEvents, 60000);
    setInterval(loadTraffic, 60000);
}

// ----------------------------------------------------
// AI 예측 함수 (여기가 안 되면 화면에 안 뜸)
// ----------------------------------------------------
async function getAIPrediction(cctvId = 0) {
    try {
        const res = await fetch(`/api/predict?id=${cctvId}`);
        const data = await res.json();
        
        const speedEl = document.getElementById('ai-speed');
        const riskEl = document.getElementById('ai-risk');

        if (data.status === 'success' && data.speed > 0) {
            // 화면 업데이트
            speedEl.innerHTML = `
                <div style="font-size:0.7rem; color:#666; margin-bottom:4px;">${data.time_msg}</div>
                <span style="font-size:1.8rem;">${data.speed}</span> km/h
            `;
            riskEl.textContent = data.risk;
            
            // 색상 변경
            riskEl.className = "value";
            if (data.risk.includes("정체")) {
                riskEl.style.color = "#ff3333";
                riskEl.classList.add("badge", "live");
            } else if (data.risk.includes("서행")) {
                riskEl.style.color = "#ff9900";
            } else {
                riskEl.style.color = "#28a745";
            }
        } else {
            console.warn("AI 데이터 없음:", data);
            speedEl.textContent = "-- km/h";
            riskEl.textContent = "분석 대기 중";
        }
    } catch (e) {
        console.error("AI 통신 실패");
    }
}

// ----------------------------------------------------
// CCTV (기존 유지)
// ----------------------------------------------------
async function loadCCTVList() {
    const selector = document.getElementById('cctv-selector');
    try {
        const res = await fetch('/api/cctv/list');
        const data = await res.json();
        if (data.success && data.list.length > 0) {
            cctvList = data.list;
            renderCCTVOptions(cctvList);
            let idx = cctvList.findIndex(c => c.name.includes("천안"));
            if (idx === -1) idx = 0;
            selector.value = idx;
            changeCCTV();
        }
    } catch (e) { selector.innerHTML = "<option>로딩 실패</option>"; }
}

function renderCCTVOptions(list) {
    const sel = document.getElementById('cctv-selector');
    sel.innerHTML = "";
    list.forEach((c, i) => {
        const opt = document.createElement('option');
        opt.value = i; opt.text = c.name; sel.appendChild(opt);
    });
}

function filterCCTV() {
    const key = document.getElementById('cctv-search').value.toLowerCase();
    const sel = document.getElementById('cctv-selector');
    sel.innerHTML = "";
    let first = -1;
    cctvList.forEach((c, i) => {
        if (c.name.toLowerCase().includes(key)) {
            const opt = document.createElement('option');
            opt.value = i; opt.text = c.name; sel.appendChild(opt);
            if(first===-1) first=i;
        }
    });
    if(first!==-1) { sel.value = first; changeCCTV(); }
}

function changeCCTV() {
    const idx = document.getElementById('cctv-selector').value;
    const cctv = cctvList[idx];
    if (!cctv) return;

    document.getElementById('video-container').innerHTML = 
        `<video src="${cctv.url}" autoplay muted playsinline controls style="width:100%;height:100%;object-fit:fill;" onerror="alert('재생 불가')"></video>`;
    
    updateMap(cctv.lat, cctv.lng, cctv.name);
    
    // ★ CCTV 바꿀 때마다 AI도 즉시 갱신
    getAIPrediction(idx);
    
    setTimeout(() => analyzeVideoFrame(cctv.name), 2000);
}

function updateMap(lat, lng, name) {
    if (!map) return;
    if (currentMarker) map.removeLayer(currentMarker);
    const icon = L.divIcon({ className: 'cam-icon', html: '📷', iconSize: [30,30] });
    currentMarker = L.marker([lat, lng], { icon: icon }).addTo(map).bindPopup(name).openPopup();
    map.setView([lat, lng], 13);
}

// 기타 함수들 (기존 유지)
async function loadTraffic() { try { const res = await fetch('/api/traffic'); const data = await res.json(); if(data.success) { trafficLayer.clearLayers(); let sum=0, cnt=0; data.list.forEach(i => { let color = i.speed<40?'red':(i.speed<80?'orange':'green'); L.circleMarker([i.lat,i.lng],{radius:5,color:color,fillColor:color,fillOpacity:0.8}).bindPopup(`${i.name}: ${i.speed}km/h`).addTo(trafficLayer); if(i.speed>0) { sum+=i.speed; cnt++; } }); if(cnt>0) updateChart((sum/cnt).toFixed(1)); } } catch {} }
async function loadVMS() { try { const res = await fetch('/api/vms'); const data = await res.json(); if(data.success) { vmsLayer.clearLayers(); data.list.forEach(i => { const icon = L.divIcon({className:'vms-marker', html:'📟', iconSize:[24,24]}); L.marker([i.lat,i.lng],{icon:icon}).bindPopup(`<div style="background:black;color:orange;padding:5px;">${i.msg}</div>`).addTo(vmsLayer); }); } } catch {} }
async function loadWarnings() { try { const res = await fetch('/api/warnings'); const data = await res.json(); if(data.success) { warningLayer.clearLayers(); data.list.forEach(i => { const icon = L.divIcon({className:'warn-marker', html:'⚠️', iconSize:[24,24]}); L.marker([i.lat,i.lng],{icon:icon}).bindPopup(i.msg).addTo(warningLayer); }); } } catch {} }
function toggleLayer(type) { const chk = document.getElementById(`${type}-toggle`); const layer = type==='warn'?warningLayer:(type==='traffic'?trafficLayer:vmsLayer); if(chk.checked) map.addLayer(layer); else map.removeLayer(layer); }
async function loadEvents() { try { const res = await fetch('/api/events'); const data = await res.json(); const tb = document.getElementById('event-list-body'); if(data.success && data.list.length>0) { tb.innerHTML=""; data.list.forEach(i=>{ const tr=document.createElement('tr'); tr.innerHTML=`<td>${i.type}</td><td>${i.time.substring(0,16)}</td><td>${i.road}</td><td>${i.msg}</td>`; tb.appendChild(tr); }); } } catch {} }
async function refreshIntegratedLog() { const box = document.getElementById('log-box'); box.innerHTML=""; try { const eRes = await fetch('/api/events'); const eData = await eRes.json(); const wRes = await fetch('/api/warnings'); const wData = await wRes.json(); let items = []; if(eData.success) eData.list.forEach(i=>items.push({type:'event',msg:i.msg,lat:i.lat,lng:i.lng})); if(wData.success) wData.list.forEach(i=>items.push({type:'warn',msg:i.msg,lat:i.lat,lng:i.lng})); items.slice(0,20).forEach(i=>{ const d=document.createElement('div'); d.className=`log-item ${i.type==='event'?'danger':'warning'}`; d.style.cursor="pointer"; d.onclick=()=>{map.setView([i.lat,i.lng],14);L.popup().setLatLng([i.lat,i.lng]).setContent(i.msg).openOn(map);}; d.innerHTML=`<span class="log-time">${i.type==='event'?'🚧':'⚠️'}</span>${i.msg}`; box.appendChild(d); }); } catch {} }
async function analyzeVideoFrame(name) { try { const res = await fetch('/api/vision/analyze'); const data = await res.json(); if(data.status==='success') { const el = document.getElementById('ai-risk'); if(!el.textContent.includes("대")) el.textContent += ` (${data.count}대)`; } } catch {} }
function initChart() { trafficChart = new Chart(document.getElementById('trafficChart'), { type:'line', data:{labels:[],datasets:[{label:'구간 평균 속도',data:[],borderColor:'blue',fill:true}]}, options:{responsive:true, maintainAspectRatio:false, scales:{x:{display:false},y:{min:0,max:120}}} }); }
function updateChart(speed) { const now = new Date().toLocaleTimeString('ko-KR',{hour12:false}); if(trafficChart.data.labels.length>15){trafficChart.data.labels.shift();trafficChart.data.datasets[0].data.shift();} trafficChart.data.labels.push(now); trafficChart.data.datasets[0].data.push(speed); trafficChart.update(); }

initSystem();