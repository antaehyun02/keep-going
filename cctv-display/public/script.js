let cctvList = [];
let map = null;
let currentMarker = null;
let warningLayer, trafficLayer, vmsLayer; 
let trafficChart = null;
let realTimeAvgSpeed = 0;

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
    getAIPrediction(0);

    setInterval(() => {
        const id = document.getElementById('cctv-selector')?.value || 0;
        getAIPrediction(id);
    }, 4000);
    setInterval(refreshIntegratedLog, 30000);
    setInterval(loadEvents, 60000);
    setInterval(loadTraffic, 60000);
}

// ----------------------------------------------------
// [핵심] AI 예측 (undefined 해결)
// ----------------------------------------------------
async function getAIPrediction(cctvId = 0) {
    try {
        const res = await fetch(`/api/predict?id=${cctvId}`);
        const data = await res.json();
        
        const speedEl = document.getElementById('ai-speed');
        const riskEl = document.getElementById('ai-risk');

        // ★ [수정] speed나 future_pred 둘 중 하나라도 있으면 표시
        const finalSpeed = data.speed || data.future_pred;

        if (data.status === 'success' && finalSpeed > 0) {
            speedEl.innerHTML = `
                <div style="font-size:0.7rem; color:#666; margin-bottom:4px;">${data.time_msg}</div>
                <span style="font-size:1.8rem; font-weight:bold;">${finalSpeed}</span> km/h
            `;
            riskEl.textContent = data.risk;
            
            riskEl.className = "value";
            if (data.risk.includes("정체")) {
                riskEl.style.color = "#ff3333";
                riskEl.classList.add("badge", "live");
            } else if (data.risk.includes("서행")) {
                riskEl.style.color = "#ff9900";
            } else {
                riskEl.style.color = "#28a745";
            }

            checkAnomaly(data.current_normal);
        } else {
            // 값이 없을 때
            speedEl.textContent = "-- km/h";
            riskEl.textContent = "데이터 부족";
            riskEl.style.color = "#aaa";
        }
    } catch (e) {
        console.error(e);
    }
}

// 이상 탐지
function checkAnomaly(aiNormalSpeed) {
    if (realTimeAvgSpeed === 0 || !aiNormalSpeed) return;
    const diff = aiNormalSpeed - realTimeAvgSpeed;
    if (diff > 30 && realTimeAvgSpeed < 50) {
        addLog(`🚨 [이상 징후] 평소보다 ${diff}km/h 느립니다!`, 'danger');
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

function changeCCTV() {
    const selector = document.getElementById('cctv-selector');
    const idx = selector.value;
    const cctv = cctvList[idx];
    if (!cctv) return;

    document.getElementById('video-container').innerHTML = 
        `<video src="${cctv.url}" autoplay muted playsinline controls 
            style="width:100%; height:100%; object-fit:fill; background:black;"
            onerror="alert('영상 신호 없음');"></video>`;
    
    updateMap(cctv.lat, cctv.lng, cctv.name);
    getAIPrediction(idx);
    setTimeout(() => analyzeVideoFrame(cctv.name), 2000);
}

// UI 함수들
function renderCCTVOptions(l){const s=document.getElementById('cctv-selector');s.innerHTML="";l.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.text=c.name;s.appendChild(o)})}
function filterCCTV(){const k=document.getElementById('cctv-search').value.toLowerCase();const s=document.getElementById('cctv-selector');s.innerHTML="";let f=-1;cctvList.forEach((c,i)=>{if(c.name.toLowerCase().includes(k)){const o=document.createElement('option');o.value=i;o.text=c.name;s.appendChild(o);if(f===-1)f=i}});if(f!==-1){s.value=f;changeCCTV()}}
function updateMap(lat,lng,n){if(!map)return;if(currentMarker)map.removeLayer(currentMarker);const i=L.divIcon({className:'cam-icon',html:'📷',iconSize:[30,30]});currentMarker=L.marker([lat,lng],{icon:i}).addTo(map).bindPopup(n).openPopup();map.setView([lat,lng],13)}
async function loadTraffic(){try{const r=await fetch('/api/traffic');const d=await r.json();if(d.success){trafficLayer.clearLayers();let sum=0,cnt=0;d.list.forEach(i=>{let k=i.speed<40?'red':(i.speed<80?'orange':'green');L.circleMarker([i.lat,i.lng],{radius:5,color:k,fillColor:k,fillOpacity:0.8}).bindPopup(`${i.name}:${i.speed}`).addTo(trafficLayer);if(i.speed>0){sum+=i.speed;cnt++}});if(cnt>0){realTimeAvgSpeed=parseInt(sum/cnt);updateChart(realTimeAvgSpeed)}}}catch{}}
async function loadVMS(){try{const r=await fetch('/api/vms');const d=await r.json();if(d.success){vmsLayer.clearLayers();d.list.forEach(i=>{const c=L.divIcon({className:'vms-marker',html:'📟',iconSize:[24,24]});L.marker([i.lat,i.lng],{icon:c}).bindPopup(`<div style="background:black;color:orange;padding:5px;">${i.msg}</div>`).addTo(vmsLayer)})}}catch{}}
async function loadWarnings(){try{const r=await fetch('/api/warnings');const d=await r.json();if(d.success){warningLayer.clearLayers();d.list.forEach(i=>{const c=L.divIcon({className:'warn-marker',html:'⚠️',iconSize:[24,24]});L.marker([i.lat,i.lng],{icon:c}).bindPopup(i.msg).addTo(warningLayer)})}}catch{}}
function toggleLayer(t){const c=document.getElementById(`${t}-toggle`);const l=t==='warn'?warningLayer:(t==='traffic'?trafficLayer:vmsLayer);if(c.checked)map.addLayer(l);else map.removeLayer(l)}
async function loadEvents(){try{const r=await fetch('/api/events');const d=await r.json();const b=document.getElementById('event-list-body');if(d.success&&d.list.length>0){b.innerHTML="";d.list.forEach(i=>{const t=document.createElement('tr');t.innerHTML=`<td>${i.type}</td><td>${i.time.substring(0,16)}</td><td>${i.road}</td><td>${i.msg}</td>`;b.appendChild(t)})}}catch{}}
const logBox=document.getElementById('log-box');function addLog(m,t='normal'){const d=document.createElement('div');d.className=`log-item ${t}`;d.innerHTML=`<span class="log-time">System</span>${m}`;logBox.prepend(d);}
async function refreshIntegratedLog(){ /* 생략 */ }
async function analyzeVideoFrame(n){try{const r=await fetch('/api/vision/analyze');const d=await r.json();if(d.status==='success'){const e=document.getElementById('ai-risk');if(!e.textContent.includes("대"))e.textContent+=` (${d.count}대)`}}catch{}}
function initChart(){trafficChart=new Chart(document.getElementById('trafficChart'),{type:'line',data:{labels:[],datasets:[{label:'평균속도',data:[],borderColor:'blue',fill:true}]},options:{responsive:true,maintainAspectRatio:false,scales:{x:{display:false},y:{min:0,max:120}}}})}
function updateChart(s){const n=new Date().toLocaleTimeString('ko-KR',{hour12:false});if(trafficChart.data.labels.length>15){trafficChart.data.labels.shift();trafficChart.data.datasets[0].data.shift()}trafficChart.data.labels.push(n);trafficChart.data.datasets[0].data.push(s);trafficChart.update()}

initSystem();