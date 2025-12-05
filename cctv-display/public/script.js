// 전역 변수
let cctvList = [];
let map = null;
let currentMarker = null;
let trafficLayer, warningLayer, vmsLayer;
let homeForecastChart = null;
let homeSafetyChart = null;
let currentEvents = [];
let currentWarnings = [];
let currentAvgSpeed = 0;

// 시계 업데이트
setInterval(() => {
    const timeEl = document.getElementById('current-time');
    if (timeEl) {
        timeEl.textContent = new Date().toLocaleTimeString('ko-KR');
    }
}, 1000);

// 초기화
async function initSystem() {
    // 지도 초기화
    map = L.map('map').setView([37.05, 127.12], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
    }).addTo(map);

    trafficLayer = L.layerGroup().addTo(map);
    warningLayer = L.layerGroup().addTo(map);
    vmsLayer = L.layerGroup().addTo(map);

    // 차트 초기화
    initHomeCharts();

    // 데이터 로드
    await loadCCTVList();
    await loadTraffic();
    await loadEvents();
    await loadWarnings();

    // 주기적 갱신
    setInterval(loadTraffic, 60000);
    setInterval(() => {
        loadEvents();
        loadWarnings();
    }, 60000);

    // 홈 화면 데이터 갱신
    setInterval(updateHomeData, 5000);
}

// 섹션 전환
function showSection(sectionName) {
    // 모든 섹션 숨김
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });

    // 모든 네비게이션 링크 비활성화
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });

    // 선택한 섹션 표시
    const targetSection = document.getElementById(`${sectionName}-section`);
    if (targetSection) {
        targetSection.classList.add('active');
    }

    // 선택한 네비게이션 링크 활성화
    const targetLink = document.querySelector(`[onclick="showSection('${sectionName}')"]`);
    if (targetLink) {
        targetLink.classList.add('active');
    }

    // 지도 리사이즈
    if (sectionName === 'traffic' && map) {
        setTimeout(() => map.invalidateSize(), 100);
    }

    // CCTV 섹션일 경우 첫 CCTV 로드
    if (sectionName === 'cctv' && cctvList.length > 0) {
        changeCCTV();
    }

    // 안전정보 섹션일 경우 데이터 로드
    if (sectionName === 'info') {
        loadSafetyData();
        loadVulnerableData();
        renderIncidentList();
    }
}

// 홈 화면 차트 초기화
function initHomeCharts() {
    // 예측 차트
    const forecastCanvas = document.getElementById('home-forecast-chart');
    if (forecastCanvas) {
        homeForecastChart = new Chart(forecastCanvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '예측 속도',
                    data: [],
                    borderColor: '#4A90E2',
                    backgroundColor: 'rgba(74, 144, 226, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 120,
                        title: {
                            display: true,
                            text: 'km/h'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    // 안전 점수 차트
    const safetyCanvas = document.getElementById('home-safety-chart');
    if (safetyCanvas) {
        homeSafetyChart = new Chart(safetyCanvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['점수', '빈공간'],
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#ccc', '#f0f0f0'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                }
            }
        });
    }
}

// 홈 화면 데이터 업데이트
async function updateHomeData() {
    const section = document.getElementById('home-section');
    if (!section || !section.classList.contains('active')) return;

    // AI 예측 데이터 가져오기
    try {
        const res = await fetch('/api/predict?id=0');
        const data = await res.json();

        if (data.status === 'success' && data.forecast) {
            updateHomeForecastChart(data.forecast);
        }
    } catch (e) {
        console.error('예측 데이터 로드 실패:', e);
    }

    // 알림 개수 업데이트
    updateHomeAlertCount();
}

// 홈 화면 예측 차트 업데이트
function updateHomeForecastChart(forecast) {
    if (!homeForecastChart) return;

    const labels = forecast.map(f => f.time);
    const speeds = forecast.map(f => f.speed);

    homeForecastChart.data.labels = labels;
    homeForecastChart.data.datasets[0].data = speeds;
    homeForecastChart.update();
}

// 홈 화면 알림 개수 업데이트
function updateHomeAlertCount() {
    const countEl = document.querySelector('#home-alert-count .number');
    if (countEl) {
        const total = currentEvents.length + currentWarnings.length;
        countEl.textContent = total;
    }
}

// 홈 화면 상태 업데이트
function updateHomeStatus(avgSpeed) {
    currentAvgSpeed = avgSpeed;

    // 평균 속도 업데이트
    const speedNum = document.querySelector('#home-avg-speed .number');
    const statusText = document.getElementById('home-status');

    if (speedNum && statusText) {
        speedNum.textContent = avgSpeed || '--';

        if (avgSpeed >= 80) {
            statusText.textContent = '원활';
            statusText.style.color = '#28a745';
        } else if (avgSpeed >= 40) {
            statusText.textContent = '서행';
            statusText.style.color = '#FF9900';
        } else if (avgSpeed > 0) {
            statusText.textContent = '정체';
            statusText.style.color = '#FF3333';
        } else {
            statusText.textContent = '데이터 로딩 중...';
            statusText.style.color = '#7F8C8D';
        }
    }

    // 예상 소요시간 업데이트
    const timeNum = document.querySelector('#home-travel-time .number');
    const timeStatus = document.getElementById('home-travel-status');

    if (timeNum && timeStatus) {
        if (avgSpeed > 0) {
            const time = Math.floor((45 / Math.max(10, avgSpeed)) * 60);
            timeNum.textContent = time;

            if (avgSpeed >= 80) {
                timeStatus.textContent = '원활';
                timeStatus.style.color = '#28a745';
            } else if (avgSpeed >= 40) {
                timeStatus.textContent = '서행';
                timeStatus.style.color = '#FF9900';
            } else {
                timeStatus.textContent = '정체';
                timeStatus.style.color = '#FF3333';
            }
        } else {
            timeNum.textContent = '--';
            timeStatus.textContent = '계산 중...';
        }
    }

    // 안전 점수 업데이트
    const scoreNum = document.querySelector('#home-safety-score .number');
    if (scoreNum) {
        if (avgSpeed > 0) {
            let score = Math.min(100, Math.floor((avgSpeed / 100) * 100));
            if (avgSpeed < 30) score = Math.max(40, score);

            scoreNum.textContent = score;

            let color = '#28a745';
            if (score < 50) color = '#FF3333';
            else if (score < 70) color = '#FF9900';

            scoreNum.style.color = color;

            // 차트 업데이트
            if (homeSafetyChart) {
                homeSafetyChart.data.datasets[0].data = [score, 100 - score];
                homeSafetyChart.data.datasets[0].backgroundColor = [color, '#f0f0f0'];
                homeSafetyChart.update();
            }
        } else {
            scoreNum.textContent = '--';
        }
    }
}

// CCTV 목록 로드
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
        } else {
            selector.innerHTML = "<option>목록 없음</option>";
        }
    } catch (e) {
        selector.innerHTML = "<option>로딩 실패</option>";
    }
}

// CCTV 옵션 렌더링
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

// CCTV 필터링
function filterCCTV() {
    const keyword = document.getElementById('cctv-search').value.toLowerCase();
    const selector = document.getElementById('cctv-selector');
    selector.innerHTML = "";

    let firstIndex = -1;
    cctvList.forEach((cctv, index) => {
        if (cctv.name.toLowerCase().includes(keyword)) {
            const option = document.createElement('option');
            option.value = index;
            option.text = cctv.name;
            selector.appendChild(option);

            if (firstIndex === -1) firstIndex = index;
        }
    });

    if (firstIndex !== -1) {
        selector.value = firstIndex;
        changeCCTV();
    }
}

// CCTV 변경
function changeCCTV() {
    const selector = document.getElementById('cctv-selector');
    const idx = selector.value;

    if (!cctvList || !cctvList[idx]) return;

    const cctv = cctvList[idx];
    const container = document.getElementById('video-container');

    if (container) {
        container.innerHTML = `
            <video id="cctv-video"
                   src="${cctv.url}"
                   autoplay
                   muted
                   playsinline
                   controls
                   style="width:100%; height:100%; object-fit:cover; background:black;"
                   onerror="this.parentElement.innerHTML='<div style=\\'display:flex;align-items:center;justify-content:center;height:100%;color:white;\\'>영상 신호 없음</div>'">
            </video>
        `;
    }

    // 지도 업데이트
    updateMapMarker(cctv.lat, cctv.lng, cctv.name);

    // AI 분석 초기화
    const aiRisk = document.getElementById('ai-risk');
    const aiSpeed = document.getElementById('ai-speed');
    const aiNormal = document.getElementById('disp-ai-normal');
    const analysisResult = document.getElementById('analysis-result');

    if (aiRisk) aiRisk.textContent = '분석 중...';
    if (aiSpeed) aiSpeed.textContent = '-- km/h';
    if (aiNormal) aiNormal.textContent = '--';
    if (analysisResult) analysisResult.textContent = '패턴 분석 중...';

    // 섹션 ID 결정
    let sectionId = 0;
    if (cctv.name.includes("수원") || cctv.name.includes("신갈") || cctv.name.includes("남사")) {
        sectionId = 2;
    } else if (cctv.name.includes("입장") || cctv.name.includes("북천안")) {
        sectionId = 1;
    }

    // AI 분석 요청
    setTimeout(() => getAIPrediction(sectionId), 500);
}

// AI 예측 가져오기
async function getAIPrediction(cctvId = 0) {
    try {
        const res = await fetch(`/api/predict?id=${cctvId}`);
        const data = await res.json();

        if (data.status === 'success') {
            // 예측 속도
            const speed = data.speed || data.future_pred;
            const speedEl = document.getElementById('ai-speed');
            if (speedEl) {
                speedEl.textContent = `${speed} km/h`;
            }

            // 위험도
            const riskEl = document.getElementById('ai-risk');
            if (riskEl) {
                riskEl.textContent = data.risk;
                if (data.risk.includes("정체")) {
                    riskEl.style.color = '#FF3333';
                } else if (data.risk.includes("서행")) {
                    riskEl.style.color = '#FF9900';
                } else {
                    riskEl.style.color = '#28a745';
                }
            }

            // 평소 패턴
            updateAiPattern(data.current_normal);
        }
    } catch (e) {
        console.error('AI 예측 로드 실패:', e);
    }
}

// AI 패턴 업데이트
function updateAiPattern(normalSpeed) {
    const normalEl = document.getElementById('disp-ai-normal');
    const resultEl = document.getElementById('analysis-result');

    if (normalEl) {
        normalEl.textContent = normalSpeed || '--';
    }

    if (!resultEl || !normalSpeed) return;

    if (normalSpeed >= 80) {
        resultEl.style.background = '#e6fffa';
        resultEl.style.border = '1px solid #28a745';
        resultEl.style.color = '#28a745';
        resultEl.textContent = '평소 원활 구간 - 소통이 원활합니다';
    } else if (normalSpeed >= 40) {
        resultEl.style.background = '#fffaf0';
        resultEl.style.border = '1px solid #ff9900';
        resultEl.style.color = '#ff9900';
        resultEl.textContent = '평소 서행 구간 - 차량이 많아 서행합니다';
    } else {
        resultEl.style.background = '#fff5f5';
        resultEl.style.border = '1px solid #ff3333';
        resultEl.style.color = '#ff3333';
        resultEl.textContent = '평소 정체 구간 - 상습 정체 구간입니다';
    }
}

// 지도 마커 업데이트
function updateMapMarker(lat, lng, name) {
    if (!map) return;

    // 기존 마커 제거
    if (currentMarker) {
        map.removeLayer(currentMarker);
    }

    // 새 마커 추가
    const icon = L.divIcon({
        className: 'cam-icon',
        html: '📹',
        iconSize: [40, 40]
    });

    currentMarker = L.marker([lat, lng], { icon: icon })
        .addTo(map)
        .bindPopup(name)
        .openPopup();

    map.setView([lat, lng], 13);
}

// 교통 정보 로드
async function loadTraffic() {
    try {
        const res = await fetch('/api/traffic');
        const data = await res.json();

        if (data.success) {
            trafficLayer.clearLayers();

            let sum = 0;
            let count = 0;

            data.list.forEach(item => {
                const speed = parseInt(item.speed);
                if (speed > 0) {
                    let color = '#28a745';
                    if (speed < 40) color = '#ff3333';
                    else if (speed < 80) color = '#ff9900';

                    L.circleMarker([item.lat, item.lng], {
                        radius: 5,
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.8
                    })
                    .bindPopup(`<b>${item.name}</b><br>${speed} km/h`)
                    .addTo(trafficLayer);

                    sum += speed;
                    count++;
                }
            });

            // 평균 속도 계산
            if (count > 0) {
                const avgSpeed = parseInt(sum / count);
                updateHomeStatus(avgSpeed);
            } else {
                updateHomeStatus(0);
            }
        }
    } catch (e) {
        console.error('교통 정보 로드 실패:', e);
    }
}

// 레이어 토글
function toggleLayer(type) {
    const checkbox = document.getElementById(`${type}-toggle`);
    if (type === 'traffic') {
        if (checkbox.checked) {
            map.addLayer(trafficLayer);
        } else {
            map.removeLayer(trafficLayer);
        }
    }
}

// 돌발 정보 로드
async function loadEvents() {
    try {
        const res = await fetch('/api/events');
        const data = await res.json();
        currentEvents = data.success ? data.list : [];
        renderIncidentList();
        updateHomeAlertCount();
    } catch (e) {
        currentEvents = [];
    }
}

// 경고 정보 로드
async function loadWarnings() {
    try {
        const res = await fetch('/api/warnings');
        const data = await res.json();
        currentWarnings = data.success ? data.list : [];
        renderIncidentList();
        updateHomeAlertCount();
    } catch (e) {
        currentWarnings = [];
    }
}

// 돌발 정보 렌더링
function renderIncidentList() {
    const listEl = document.getElementById('incident-list');
    if (!listEl) return;

    const allIncidents = [...currentEvents, ...currentWarnings];

    if (allIncidents.length === 0) {
        listEl.innerHTML = '<li class="loading">현재 돌발 정보 없음</li>';
        return;
    }

    listEl.innerHTML = '';
    allIncidents.forEach(incident => {
        const li = document.createElement('li');
        li.innerHTML = `
            <div>
                <div style="font-weight: bold;">${incident.road || '구간'}</div>
                <div style="font-size: 0.9rem; color: #666;">${incident.msg}</div>
            </div>
        `;
        listEl.appendChild(li);
    });
}

// 안전 데이터 로드 (위험물질 운송차량)
async function loadSafetyData() {
    const tbody = document.getElementById('dangerous-table-body');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;">데이터 갱신 중...</td></tr>';

    try {
        const res = await fetch('/api/dangerous');
        const data = await res.json();

        if (data.success && data.list.length > 0) {
            tbody.innerHTML = '';
            data.list.forEach(item => {
                const tr = document.createElement('tr');
                const speedColor = item.speed > 80 ? 'red' : 'black';
                tr.innerHTML = `
                    <td>${item.road}</td>
                    <td style="font-weight:bold; color:${speedColor}">${item.speed} km/h</td>
                    <td>(${item.y.toFixed(4)}, ${item.x.toFixed(4)})</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:20px;">현재 운행 중인 위험 차량이 없습니다.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:red;">데이터 로드 실패</td></tr>';
    }
}

// 취약구간 데이터 로드 (안개취약, 상습결빙구간)
async function loadVulnerableData() {
    const tbody = document.getElementById('vulnerable-table-body');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">데이터 갱신 중...</td></tr>';

    try {
        const res = await fetch('/api/vulnerable');
        const data = await res.json();

        if (data.success && data.list.length > 0) {
            tbody.innerHTML = '';
            data.list.forEach(item => {
                const tr = document.createElement('tr');

                // 유형별 뱃지 스타일
                let badgeClass = 'badge-ice';
                let badgeIcon = '❄️';
                let badgeText = '결빙주의';

                if (item.type === '안개') {
                    badgeClass = 'badge-fog';
                    badgeIcon = '🌫️';
                    badgeText = '안개주의';
                }

                tr.innerHTML = `
                    <td>${item.road || '-'}</td>
                    <td>${item.section || '-'}</td>
                    <td><span class="${badgeClass}">${badgeIcon} ${badgeText}</span></td>
                    <td>${item.msg || '안전운전 요망'}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px;">현재 취약구간 정보가 없습니다.</td></tr>';
        }
    } catch (e) {
        console.error('취약구간 데이터 로드 실패:', e);
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:red;">데이터 로드 실패</td></tr>';
    }
}

// 시스템 초기화 실행
initSystem();