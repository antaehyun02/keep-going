// 공통 네비게이션 초기화 함수
function initializeNavigation(currentPage = '') {
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    const navUserName = document.getElementById('nav-user-name');
    const navUserIcon = document.getElementById('nav-user-icon');

    // 로그인 상태에 따른 사용자 정보 표시
    if (user) {
        navUserName.textContent = user.name;
        navUserIcon.onclick = () => {
            window.location.href = 'profile.html';
        };

        // 로그인 상태일 때 회원가입 메뉴 숨기기
        const signupMenuItem = document.querySelector('a[href="signup.html"]');
        if (signupMenuItem && signupMenuItem.parentElement) {
            signupMenuItem.parentElement.style.display = 'none';
        }
    } else {
        navUserName.textContent = '로그인';
        navUserIcon.onclick = () => {
            window.location.href = 'login.html';
        };
    }

    // 현재 페이지에 active 클래스 설정
    if (currentPage) {
        const navLinks = document.querySelectorAll('.nav-menu a');
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === currentPage) {
                link.classList.add('active');
            }
        });
    }
}
