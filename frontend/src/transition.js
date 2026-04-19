// SkinAI — 페이지 전환 애니메이션
(function () {
  // 페이드아웃 후 이동
  window.navigateTo = function (url) {
    if (!url || url === '#') return;
    document.body.style.transition = 'opacity 0.22s ease, transform 0.22s ease';
    document.body.style.opacity = '0';
    document.body.style.transform = 'translateY(6px)';
    setTimeout(function () { location.href = url; }, 230);
  };

  // <a href> 클릭 인터셉트
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href');
    if (!href || href === '#' || href.startsWith('javascript') || href.startsWith('mailto') || href.startsWith('http') || a.target === '_blank') return;
    e.preventDefault();
    navigateTo(href);
  });
})();
