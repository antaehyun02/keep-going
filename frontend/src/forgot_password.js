document.addEventListener('DOMContentLoaded', () => {

  function showError(msg) {
    document.getElementById('errorText').textContent = msg;
    document.getElementById('errorMsg').classList.add('show');
  }
  function hideError() {
    document.getElementById('errorMsg').classList.remove('show');
  }

  async function handleSubmit() {
    const email = document.getElementById('emailInput').value.trim();
    const btn   = document.getElementById('submitBtn');

    hideError();

    if (!email) { showError('이메일을 입력해주세요.'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showError('올바른 이메일 형식을 입력해주세요.');
      return;
    }

    btn.classList.add('loading');
    btn.disabled = true;

    try {
      const res  = await fetch('/api/auth/forgot-password', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email }),
      });
      const data = await res.json();

      if (!res.ok) {
        showError(data.message || '오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        return;
      }

      document.getElementById('formSection').style.display = 'none';
      document.getElementById('successDesc').innerHTML =
        `<strong>${email}</strong> 으로<br>비밀번호 재설정 링크를 발송했습니다.<br><br>` +
        `메일함(스팸 포함)을 확인하고<br>링크를 클릭하세요. (15분 유효)`;
      document.getElementById('successSection').classList.add('show');

    } catch {
      showError('서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      btn.classList.remove('loading');
      btn.disabled = false;
    }
  }

  document.getElementById('submitBtn').addEventListener('click', handleSubmit);
  document.getElementById('emailInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') handleSubmit();
  });

});
