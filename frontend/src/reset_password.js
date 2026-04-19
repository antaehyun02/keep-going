document.addEventListener('DOMContentLoaded', async () => {

  const token = new URLSearchParams(window.location.search).get('token');

  function showSection(id) {
    ['loadingSection', 'formSection', 'invalidSection', 'successSection'].forEach(s => {
      const el = document.getElementById(s);
      el.style.display = 'none';
      el.classList.remove('show');
    });
    const target = document.getElementById(id);
    target.style.display = id === 'formSection' ? 'block' : (id === 'loadingSection' ? 'block' : 'flex');
    target.classList.add('show');
  }

  // ── 토큰 유효성 확인 ──
  if (!token) {
    showSection('invalidSection');
    return;
  }

  try {
    const res = await fetch(`http://localhost:3000/api/auth/verify-reset-token?token=${token}`);
    const data = await res.json();
    if (!res.ok || !data.valid) {
      showSection('invalidSection');
      return;
    }
  } catch {
    showSection('invalidSection');
    return;
  }

  showSection('formSection');

  // ── 비밀번호 강도 ──
  function calcStrength(pw) {
    let score = 0;
    if (pw.length >= 8)  score++;
    if (pw.length >= 12) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return score;
  }

  function updateStrength(pw) {
    const fill  = document.getElementById('strengthFill');
    const label = document.getElementById('strengthLabel');
    if (!pw) { fill.style.width = '0'; label.textContent = ''; return; }
    const levels = [
      { pct: '20%', color: '#ef4444', text: '매우 약함' },
      { pct: '40%', color: '#f97316', text: '약함' },
      { pct: '60%', color: '#eab308', text: '보통' },
      { pct: '80%', color: '#22c55e', text: '강함' },
      { pct: '100%', color: '#059669', text: '매우 강함' },
    ];
    const lv = levels[Math.min(calcStrength(pw), 4)];
    fill.style.width  = lv.pct;
    fill.style.background = lv.color;
    label.textContent = lv.text;
    label.style.color = lv.color;
  }

  function togglePw(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon  = document.getElementById(iconId);
    if (input.type === 'password') {
      input.type = 'text';
      icon.innerHTML = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>`;
    } else {
      input.type = 'password';
      icon.innerHTML = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>`;
    }
  }

  document.getElementById('pwInput').addEventListener('input', e => updateStrength(e.target.value));
  document.getElementById('pwToggle1').addEventListener('click', () => togglePw('pwInput',   'eyeIcon1'));
  document.getElementById('pwToggle2').addEventListener('click', () => togglePw('pwConfirm', 'eyeIcon2'));

  function showError(msg) {
    document.getElementById('errorText').textContent = msg;
    document.getElementById('errorMsg').classList.add('show');
  }
  function hideError() {
    document.getElementById('errorMsg').classList.remove('show');
  }

  // ── 비밀번호 변경 제출 ──
  async function handleSubmit() {
    const pw      = document.getElementById('pwInput').value;
    const confirm = document.getElementById('pwConfirm').value;
    const btn     = document.getElementById('submitBtn');

    hideError();

    if (!pw)           { showError('새 비밀번호를 입력해주세요.'); return; }
    if (pw.length < 8) { showError('비밀번호는 8자 이상이어야 합니다.'); return; }
    if (pw !== confirm) { showError('비밀번호가 일치하지 않습니다.'); return; }

    btn.classList.add('loading');
    btn.disabled = true;

    try {
      const res  = await fetch('http://localhost:3000/api/auth/reset-password', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ token, password: pw }),
      });
      const data = await res.json();

      if (!res.ok) {
        if (res.status === 400 && data.message.includes('만료')) {
          showSection('invalidSection');
          return;
        }
        showError(data.message || '오류가 발생했습니다.');
        return;
      }

      showSection('successSection');

    } catch {
      showError('서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      btn.classList.remove('loading');
      btn.disabled = false;
    }
  }

  document.getElementById('submitBtn').addEventListener('click', handleSubmit);
  document.addEventListener('keydown', e => { if (e.key === 'Enter') handleSubmit(); });

});
