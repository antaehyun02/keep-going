// ═══════════════════════════════════════════════════
//  record_detail.js  —  분석 결과 상세 UI
//
//  [순수 프론트 영역]
//    - 신뢰도 링 애니메이션
//    - 감별진단 바 애니메이션
//    - 북마크 토글
//    - 공유
//
//  [DB 팀 연동 필요 영역]
//    - loadRecordDetail() : URL 파라미터(id)로 기록 불러오기
//      → GET /api/records/:id
// ═══════════════════════════════════════════════════


// ── 신뢰도 링 애니메이션 ──────────────────────────────
(function animateRing() {
  const ring = document.getElementById('confRing');
  if (!ring) return;
  const circumference = 2 * Math.PI * 34; // r=34
  // ── DB 팀 연동 영역 ──────────────────────────────
  // TODO: 실제 신뢰도 값으로 교체
  // const conf = recordData.confidence; // 0~100
  const conf = 91;
  // ── DB 팀 연동 영역 끝 ──────────────────────────
  const offset = circumference * (1 - conf / 100);
  ring.style.strokeDasharray = circumference;
  ring.style.strokeDashoffset = circumference; // 시작값 (0%)
  setTimeout(() => { ring.style.strokeDashoffset = offset; }, 200);
})();


// ── 감별진단 바 애니메이션 ────────────────────────────
(function animateDiffBars() {
  const bars = document.querySelectorAll('.diff-bar');
  bars.forEach(bar => {
    const target = bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = target; }, 300);
  });
})();


// ── 북마크 토글 ──────────────────────────────────────
let bookmarked = false;
function bookmarkRecord() {
  bookmarked = !bookmarked;
  const btn = document.getElementById('bookmarkBtn');
  if (bookmarked) {
    btn.style.borderColor = '#f59e0b';
    btn.style.color = '#f59e0b';
    btn.style.background = '#fffbeb';
    showToast('북마크에 저장됐어요');
  } else {
    btn.style.borderColor = '';
    btn.style.color = '';
    btn.style.background = '';
    showToast('북마크가 해제됐어요');
  }
  // ── DB 팀 연동 영역 ──────────────────────────────
  // TODO: POST /api/records/:id/bookmark
  // ── DB 팀 연동 영역 끝 ──────────────────────────
}


// ── 공유 ──────────────────────────────────────────────
function shareRecord() {
  if (navigator.share) {
    navigator.share({ title: 'SkinAI 분석 결과', url: location.href });
  } else {
    navigator.clipboard.writeText(location.href).then(() => showToast('링크가 복사됐어요'));
  }
}


// ── 토스트 ───────────────────────────────────────────
let toastTimer = null;
function showToast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast' + (type ? ' ' + type : '') + ' show';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2800);
}
