/**
 * SkinAI Analyze Page — AI Hub 08-14 6종 분류 결과 시각화
 */

(function () {
  'use strict';

  // ── DOM ─────────────────────────────────────────────────────
  const uploadZone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('file-input');
  const btnAnalyze = document.getElementById('btn-analyze');
  const spinner = document.getElementById('spinner');
  const imageResult = document.getElementById('image-result');
  const resultPlaceholder = document.getElementById('result-placeholder');
  const resultSection = document.getElementById('result-section');
  const btnSave = document.getElementById('btn-save');
  const toast = document.getElementById('toast');

  let selectedFile = null;
  let lastResult = null;
  let probChart = null;

  // ── Upload ──────────────────────────────────────────────────

  uploadZone.addEventListener('click', () => fileInput.click());

  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });

  uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
  });

  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
  });

  function handleFile(file) {
    const validTypes = ['image/jpeg', 'image/png'];
    if (!validTypes.includes(file.type)) {
      showToast('JPG 또는 PNG 파일만 업로드 가능합니다.', 'error');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showToast('파일 크기는 10MB 이하여야 합니다.', 'error');
      return;
    }

    selectedFile = file;
    const url = URL.createObjectURL(file);
    uploadZone.innerHTML = `<img src="${url}" alt="업로드 이미지">`;
    uploadZone.classList.add('has-image');
    btnAnalyze.disabled = false;

    // Reset results
    resultSection.classList.remove('visible');
    resultPlaceholder.style.display = 'block';
    imageResult.style.display = 'none';
  }

  // ── Analyze ─────────────────────────────────────────────────

  btnAnalyze.addEventListener('click', async () => {
    if (!selectedFile) return;

    const token = localStorage.getItem('token');
    if (!token) {
      showToast('로그인이 필요합니다.', 'error');
      window.location.href = 'login.html';
      return;
    }

    btnAnalyze.disabled = true;
    spinner.style.display = 'block';
    resultPlaceholder.style.display = 'none';
    resultSection.classList.remove('visible');

    try {
      const formData = new FormData();
      formData.append('image', selectedFile);

      const res = await fetch('/api/ai/predict', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || data.message || '분석에 실패했습니다.');
      }

      lastResult = data;
      renderResult(data);

    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      spinner.style.display = 'none';
      btnAnalyze.disabled = false;
    }
  });

  // ── Render Result ───────────────────────────────────────────

  function renderResult(data) {
    const { prediction, gradcam, clinical_ref, processing_time_ms } = data;

    // Images
    const originalUrl = URL.createObjectURL(selectedFile);
    document.getElementById('img-original').src = originalUrl;

    if (gradcam) {
      document.getElementById('img-gradcam').src = `data:image/png;base64,${gradcam}`;
    }
    imageResult.style.display = 'block';
    document.getElementById('processing-time').textContent =
      `분석 시간: ${processing_time_ms}ms`;

    // Prediction main
    const predMain = document.getElementById('prediction-main');
    document.getElementById('pred-class').textContent = prediction.class_name;
    document.getElementById('pred-conf').textContent =
      `${(prediction.confidence * 100).toFixed(1)}%`;

    if (prediction.uncertain) {
      predMain.classList.add('uncertain');
      document.getElementById('pred-conf').textContent += ' (신뢰도 부족)';
    } else {
      predMain.classList.remove('uncertain');
    }

    // Probability chart
    renderProbChart(prediction.top3);

    // Clinical ref
    renderClinicalRef(clinical_ref, prediction.class_name);

    // Show
    resultPlaceholder.style.display = 'none';
    resultSection.classList.add('visible');
  }

  function renderProbChart(top3) {
    const ctx = document.getElementById('prob-chart').getContext('2d');

    if (probChart) probChart.destroy();

    const labels = top3.map(t => t.class);
    const values = top3.map(t => (t.prob * 100).toFixed(1));
    const colors = top3.map((_, i) =>
      i === 0 ? '#4CAF50' : (i === 1 ? '#81C784' : '#C8E6C9')
    );

    probChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: colors,
          borderRadius: 6,
          barThickness: 36,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.raw}%`
            }
          }
        },
        scales: {
          x: {
            max: 100,
            ticks: { callback: (v) => v + '%' },
            grid: { display: false }
          },
          y: {
            grid: { display: false }
          }
        },
        animation: { duration: 800, easing: 'easeOutQuart' }
      }
    });
  }

  function renderClinicalRef(ref, className) {
    const section = document.getElementById('clinical-section');
    const container = document.getElementById('clinical-stats');

    if (!ref) {
      section.style.display = 'none';
      return;
    }

    let html = '';

    if (ref.gender_ratio) {
      html += '<div style="margin-bottom:12px;"><strong>성별 비율</strong></div>';
      for (const [k, v] of Object.entries(ref.gender_ratio)) {
        html += `<div class="stat-row"><span class="stat-label">${k}</span><span class="stat-value">${(v*100).toFixed(1)}%</span></div>`;
      }
    }

    if (ref.age_distribution) {
      html += '<div style="margin:12px 0 8px;"><strong>연령대 분포</strong></div>';
      for (const [k, v] of Object.entries(ref.age_distribution)) {
        html += `<div class="stat-row"><span class="stat-label">${k}</span><span class="stat-value">${(v*100).toFixed(1)}%</span></div>`;
      }
    }

    if (ref.severity_dist && className === '아토피피부염') {
      html += '<div style="margin:12px 0 8px;"><strong>중증도 분포</strong></div>';
      for (const [k, v] of Object.entries(ref.severity_dist)) {
        html += `<div class="stat-row"><span class="stat-label">${k}</span><span class="stat-value">${(v*100).toFixed(1)}%</span></div>`;
      }
    }

    container.innerHTML = html;
    section.style.display = html ? 'block' : 'none';
  }

  // ── Tabs ────────────────────────────────────────────────────

  document.querySelectorAll('.image-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.image-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-image').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
    });
  });

  // ── Save ────────────────────────────────────────────────────

  btnSave.addEventListener('click', async () => {
    if (!lastResult) return;

    const token = localStorage.getItem('token');
    if (!token) {
      showToast('로그인이 필요합니다.', 'error');
      return;
    }

    try {
      const res = await fetch('/api/ai/analyses', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          prediction: lastResult.prediction,
          gradcam: lastResult.gradcam,
          clinical_ref: lastResult.clinical_ref,
        }),
      });

      const data = await res.json();
      if (data.success) {
        showToast('결과가 저장되었습니다.', 'success');
      } else {
        throw new Error(data.message || '저장에 실패했습니다.');
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // ── Toast ───────────────────────────────────────────────────

  function showToast(message, type) {
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => { toast.classList.remove('show'); }, 3000);
  }

})();
