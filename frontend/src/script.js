// DOM 요소 가져오기
const loginForm = document.getElementById('login-form');
const deleteForm = document.getElementById('delete-form');
const logoutButton = document.getElementById('logout-button');
const messageBox = document.getElementById('message-box');
const authSection = document.getElementById('auth-section');
const userSection = document.getElementById('user-section');
const welcomeMessage = document.getElementById('welcome-message');

// API 기본 경로
const API_BASE_URL = '/api/auth';

/**
 * 서버에 API 요청을 보내는 함수
 * @param {string} endpoint - API 엔드포인트 (예: '/signup')
 * @param {string} method - HTTP 메소드 ('POST', 'DELETE' 등)
 * @param {object} body - 요청 본문 데이터
 */
const apiRequest = async (endpoint, method, body) => {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        // 응답 데이터를 JSON 형태로 파싱
        const result = await response.json();

        // 성공 여부에 따라 메시지 박스 스타일 변경
        if (result.success) {
            showMessage(result.message, 'success');
        } else {
            // 에러가 배열 형태일 경우, 첫 번째 메시지만 보여줌
            const errorMessage = Array.isArray(result.errors) ? result.errors[0].msg : result.message;
            showMessage(errorMessage, 'error');
        }
        return result;

    } catch (error) {
        console.error('API 요청 에러:', error);
        showMessage('클라이언트 측 에러가 발생했습니다.', 'error');
    }
};

// 사용자에게 메시지를 보여주는 함수
const showMessage = (message, type) => {
    messageBox.textContent = message;
    messageBox.className = `message ${type}`; // 'message success' 또는 'message error'
};

// UI 상태를 변경하는 함수 (로그인/로그아웃)
const updateUI = (isLoggedIn) => {
    if (isLoggedIn) {
        authSection.classList.add('hidden');
        userSection.classList.remove('hidden');
        const user = JSON.parse(localStorage.getItem('user'));
        welcomeMessage.textContent = `${user.name}님, 환영합니다!`;
    } else {
        authSection.classList.remove('hidden');
        userSection.classList.add('hidden');
        welcomeMessage.textContent = '';
    }
};

// 로그인 폼 제출 이벤트 처리
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    const result = await apiRequest('/login', 'POST', { email, password });
    if (result && result.success) {
        // 로그인 성공 시 토큰과 사용자 정보를 로컬 스토리지에 저장
        localStorage.setItem('token', result.data.token);
        localStorage.setItem('user', JSON.stringify(result.data.user));
        loginForm.reset();

        // 게시판 페이지로 리다이렉트
        showMessage('로그인 성공! 게시판으로 이동합니다...', 'success');
        setTimeout(() => {
            window.location.href = '/board.html';
        }, 1000);
    }
});

// 로그아웃 버튼 클릭 이벤트 처리
logoutButton.addEventListener('click', () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    showMessage('로그아웃 되었습니다.', 'success');
    updateUI(false); // 로그아웃 상태 UI로 변경
});

// 회원탈퇴 폼 제출 이벤트 처리
deleteForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('delete-email').value;
    const password = document.getElementById('delete-password').value;

    const confirmDelete = confirm('정말로 계정을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.');
    if (confirmDelete) {
        const result = await apiRequest('/delete', 'DELETE', { email, password });
        if (result && result.success) {
            // 회원탈퇴 성공 시 로그아웃 처리
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            updateUI(false);
        }
    }
});

// 페이지 로드 시 로그인 상태 확인
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (token) {
        // 이미 로그인된 상태면 게시판으로 리다이렉트
        window.location.href = '/board.html';
    } else {
        updateUI(false);
    }
});