// ══════════════════════════════════════════
//  분석 가능 질환 목록 (API 연결 전 기준)
//  API 연결 시 서버에서 내려오는 목록으로 교체 예정
// ══════════════════════════════════════════
const VALID_DISEASES = [
  { key: 'psoriasis',          nameKo: '건선',         nameEn: 'Psoriasis' },
  { key: 'atopic_dermatitis',  nameKo: '아토피 피부염', nameEn: 'Atopic Dermatitis' },
  { key: 'rosacea',            nameKo: '주사',          nameEn: 'Rosacea' },
  { key: 'seborrheic',         nameKo: '지루성 피부염', nameEn: 'Seborrheic Dermatitis' },
  { key: 'acne',               nameKo: '여드름',        nameEn: 'Acne Vulgaris' },
  { key: 'normal',             nameKo: '정상',          nameEn: 'Normal' },
];

// ──────────────────────────────────────────
//  DOM 참조
// ──────────────────────────────────────────
const fileInput        = document.getElementById('fileInput');
const changeInput      = document.getElementById('changeInput');
const uploadZone       = document.getElementById('uploadZone');
const uploadPlaceholder = document.getElementById('uploadPlaceholder');
const previewWrap      = document.getElementById('previewWrap');
const previewImg       = document.getElementById('previewImg');
const previewName      = document.getElementById('previewName');
const clearBtn         = document.getElementById('clearBtn');
const analyzeBtn       = document.getElementById('analyzeBtn');
const loadingCard      = document.getElementById('loadingCard');
const resultCard       = document.getElementById('resultCard');
const errorCard        = document.getElementById('errorCard');
const preprocessStatus = document.getElementById('preprocessStatus');
const preprocessTitle  = document.getElementById('preprocessTitle');
const preprocessItems  = document.getElementById('preprocessItems');

// 현재 분석에 사용할 클린 이미지 blob
let currentCleanBlob = null;
// 마지막 API 결과 저장 (기록 저장 시 사용)
let lastApiResult = null;

// ──────────────────────────────────────────
//  사이드바 질환 목록 렌더링
// ──────────────────────────────────────────
function renderSidebarDiseases() {
  const el = document.getElementById('sidebarDiseaseList');
  el.innerHTML = VALID_DISEASES.map((d, i) => `
    <div class="guide-item" style="${i === VALID_DISEASES.length - 1 ? 'border-bottom:none;padding-bottom:0' : ''}">
      <div class="guide-num" style="background:#f5f3ff;color:#7c3aed;">${i + 1}</div>
      <div class="guide-text"><strong>${d.nameKo}</strong> <span style="color:#c4cad4;">${d.nameEn}</span></div>
    </div>`).join('');
}

// 에러 카드 질환 칩 렌더링
function renderErrorDiseaseChips() {
  document.getElementById('errorDiseaseChips').innerHTML =
    VALID_DISEASES.map(d => `<span class="error-disease-chip">${d.nameKo}</span>`).join('');
}

// ──────────────────────────────────────────
//  이미지 전처리 (메타데이터 제거 + 마스킹)
// ──────────────────────────────────────────
async function stripAndMask(file) {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);

      // 상단 8% 식별 영역 마스킹
      const maskH = Math.floor(img.height * 0.08);
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, img.width, maskH);

      URL.revokeObjectURL(url);
      canvas.toBlob((blob) => {
        const cleanFile = new File([blob], 'image_clean.png', { type: 'image/png' });
        resolve({ blob, cleanFile, dataUrl: canvas.toDataURL('image/png') });
      }, 'image/png');
    };
    img.src = url;
  });
}

function showPreprocessSteps(steps) {
  preprocessItems.innerHTML = steps.map((s, i) =>
    `<div class="preprocess-item" id="pitem${i}">
      <div class="preprocess-item-dot pending" id="pdot${i}"></div>
      <span>${s}</span>
    </div>`).join('');
}

function tickStep(i) {
  const dot = document.getElementById(`pdot${i}`);
  if (dot) dot.style.background = '#16a34a';
}

async function loadFile(file) {
  preprocessStatus.className = 'preprocess-status processing show';
  preprocessTitle.textContent = '전처리 중...';
  preprocessTitle.style.color = '';

  const steps = ['EXIF 메타데이터 제거', '촬영 위치·기기 정보 삭제', '상단 식별 영역 마스킹', '클린 이미지 생성'];
  showPreprocessSteps(steps);

  setTimeout(() => tickStep(0), 150);
  setTimeout(() => tickStep(1), 350);

  const result = await stripAndMask(file);
  currentCleanBlob = result.blob;

  tickStep(2);
  setTimeout(() => tickStep(3), 150);

  setTimeout(() => {
    preprocessStatus.className = 'preprocess-status show';
    preprocessTitle.textContent = '전처리 완료 — 메타데이터 제거 및 식별 데이터 마스킹 완료';
    preprocessTitle.style.color = '#15803d';
  }, 500);

  previewImg.src = result.dataUrl;
  previewName.textContent = `${file.name} · 전처리 완료`;
  uploadPlaceholder.style.display = 'none';
  previewWrap.style.display = 'block';
  uploadZone.classList.add('has-image');
  analyzeBtn.disabled = false;
  resultCard.style.display = 'none';
  errorCard.style.display = 'none';
  loadingCard.style.display = 'none';
  lastApiResult = null;
}

fileInput.addEventListener('change', () => { if (fileInput.files[0]) loadFile(fileInput.files[0]); });
changeInput.addEventListener('change', () => { if (changeInput.files[0]) loadFile(changeInput.files[0]); });
clearBtn.addEventListener('click', e => { e.stopPropagation(); resetAll(); });

uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault(); uploadZone.classList.remove('drag');
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('image/')) loadFile(f);
});

function resetAll() {
  previewWrap.style.display = 'none';
  uploadPlaceholder.style.display = 'block';
  uploadZone.classList.remove('has-image');
  fileInput.value = '';
  analyzeBtn.disabled = true;
  preprocessStatus.className = 'preprocess-status';
  resultCard.style.display = 'none';
  errorCard.style.display = 'none';
  loadingCard.style.display = 'none';
  currentCleanBlob = null;
  lastApiResult = null;
}

// ══════════════════════════════════════════
//  AI 분석 API 호출
//  실제 API 연결 시 이 함수만 교체하면 됩니다.
//
//  API 응답 형식 (예시):
//  성공: {
//    valid: true,
//    primary: { key, nameKo, nameEn, confidence },
//    others: [{ key, nameKo, nameEn, confidence }, ...],
//    findings: ['소견1', '소견2', ...]
//  }
//  실패: {
//    valid: false,
//    reason: '에러 메시지'
//  }
// ══════════════════════════════════════════
async function callAnalyzeAPI(imageBlob) {
  // TODO: 실제 API 엔드포인트로 교체
  // const formData = new FormData();
  // formData.append('image', imageBlob, 'image_clean.png');
  // const res = await fetch('/api/analyze', { method: 'POST', body: formData });
  // return await res.json();

  // ── API 연결 전 임시 응답 ──
  // 실제 API가 연결되면 아래 throw 줄을 제거하고 위 fetch 코드를 활성화하세요.
  throw new Error('API_NOT_CONNECTED');
}

// ──────────────────────────────────────────
//  분석 시작
// ──────────────────────────────────────────
async function startAnalyze() {
  analyzeBtn.disabled = true;
  resultCard.style.display = 'none';
  errorCard.style.display = 'none';
  loadingCard.style.display = 'block';

  await runLoadingSteps();

  try {
    const apiResult = await callAnalyzeAPI(currentCleanBlob);

    loadingCard.style.display = 'none';

    if (!apiResult.valid) {
      showError(apiResult.reason || '분석 가능한 안면부 피부 질환 이미지가 아닙니다.');
    } else {
      lastApiResult = apiResult;
      renderResult(apiResult);
    }
  } catch (err) {
    loadingCard.style.display = 'none';

    if (err.message === 'API_NOT_CONNECTED') {
      showError('현재 AI 분석 서버가 연결되지 않았습니다. API 연결 후 이용해 주세요.');
    } else {
      showError('분석 중 오류가 발생했습니다. 다시 시도해 주세요.');
    }
  }

  analyzeBtn.disabled = false;
}

// 로딩 스텝 순차 실행 (Promise 반환)
function runLoadingSteps() {
  return new Promise((resolve) => {
    const steps = [
      { id: 'step1', duration: 900,  progress: 33  },
      { id: 'step2', duration: 1400, progress: 66  },
      { id: 'step3', duration: 1100, progress: 100 },
    ];
    const bar = document.getElementById('progressBar');
    const label = document.getElementById('progressLabel');
    let current = 0;

    ['step1', 'step2', 'step3'].forEach(id => {
      const el = document.getElementById(id);
      el.classList.remove('active', 'done');
      el.querySelector('.step-num').textContent = id.replace('step', '');
      el.querySelector('.step-num').style.display = 'flex';
    });
    bar.style.width = '0%'; label.textContent = '0%';

    function runStep(i) {
      if (i >= steps.length) { resolve(); return; }
      const s = steps[i];
      const el = document.getElementById(s.id);
      if (i > 0) {
        const prev = document.getElementById(steps[i - 1].id);
        prev.classList.remove('active'); prev.classList.add('done');
        prev.querySelector('.step-spinner').style.display = 'none';
        const num = prev.querySelector('.step-num');
        num.style.display = 'flex'; num.textContent = '✓';
      }
      el.classList.add('active');
      const start = current, end = s.progress, startTime = Date.now();
      function animProg() {
        const pct = Math.min((Date.now() - startTime) / s.duration, 1);
        current = Math.round(start + (end - start) * pct);
        bar.style.width = current + '%'; label.textContent = current + '%';
        if (pct < 1) requestAnimationFrame(animProg);
      }
      animProg();
      setTimeout(() => runStep(i + 1), s.duration);
    }
    setTimeout(() => runStep(0), 200);
  });
}

// ──────────────────────────────────────────
//  에러 카드 표시
// ──────────────────────────────────────────
function showError(msg) {
  document.getElementById('errorMsg').textContent = msg;
  renderErrorDiseaseChips();
  errorCard.style.display = 'block';
  errorCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ──────────────────────────────────────────
//  결과 카드 동적 렌더링 (API 응답 기반)
// ──────────────────────────────────────────
function renderResult(data) {
  const confPct = Math.round(data.primary.confidence * 100);
  document.getElementById('resultConfPill').textContent = `신뢰도 ${confPct}%`;

  document.getElementById('diagName').textContent = data.primary.nameEn;
  document.getElementById('diagNameKo').textContent = data.primary.nameKo;
  document.getElementById('diagPctLabel').textContent = `${confPct}%`;
  document.getElementById('diagBar').style.width = `${confPct}%`;

  const othersEl = document.getElementById('otherDiagnoses');
  const diffLabel = document.getElementById('diffDiagLabel');
  if (data.others && data.others.length > 0) {
    diffLabel.style.display = '';
    othersEl.innerHTML = data.others.map(o => {
      const pct = Math.round(o.confidence * 100);
      return `<div class="other-diag">
        <div class="other-diag-name">${o.nameEn} (${o.nameKo})</div>
        <div class="other-bar-bg"><div class="other-bar" style="width:${pct}%"></div></div>
        <div class="other-diag-pct">${pct}%</div>
      </div>`;
    }).join('');
  } else {
    diffLabel.style.display = 'none';
    othersEl.innerHTML = '';
  }

  document.getElementById('findingList').innerHTML = (data.findings || []).map(f =>
    `<div class="finding-item"><div class="finding-dot"></div>${f}</div>`
  ).join('');

  resultCard.style.display = 'block';
  resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ──────────────────────────────────────────
//  기록 저장 (my_analyze.html 연동 예정)
// ──────────────────────────────────────────
function saveRecord() {
  if (!lastApiResult) return;
  // TODO: localStorage 또는 API로 기록 저장
  // const records = JSON.parse(localStorage.getItem('skinai_records') || '[]');
  // records.unshift({ id: Date.now(), ...lastApiResult, date: new Date().toISOString().slice(0, 10) });
  // localStorage.setItem('skinai_records', JSON.stringify(records));
  alert('기록 저장 기능은 API 연결 후 활성화됩니다.');
}

// ──────────────────────────────────────────
//  초기화
// ──────────────────────────────────────────
renderSidebarDiseases();
renderErrorDiseaseChips();
