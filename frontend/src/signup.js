// DOM 요소 가져오기
const signupForm = document.getElementById('signup-form');
const messageBox = document.getElementById('message-box');

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

// 회원가입 폼 제출 이벤트 처리
signupForm.addEventListener('submit', async (e) => {
    e.preventDefault(); // 폼 기본 동작(새로고침) 방지
    const name = document.getElementById('signup-name').value;
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const passwordConfirm = document.getElementById('signup-password-confirm').value;

    // 비밀번호 확인 검증
    if (password !== passwordConfirm) {
        showMessage('비밀번호가 일치하지 않습니다.', 'error');
        return;
    }

    // 비밀번호 길이 검증
    if (password.length < 6) {
        showMessage('비밀번호는 최소 6자 이상이어야 합니다.', 'error');
        return;
    }

    const result = await apiRequest('/signup', 'POST', { name, email, password });
    if (result && result.success) {
        // 회원가입 성공 시 토큰과 사용자 정보 저장
        localStorage.setItem('token', result.data.token);
        localStorage.setItem('user', JSON.stringify(result.data.user));

        signupForm.reset();
        showMessage('회원가입 성공! 게시판으로 이동합니다...', 'success');

        // 게시판으로 리다이렉트
        setTimeout(() => {
            window.location.href = '/board.html';
        }, 1000);
    }
});