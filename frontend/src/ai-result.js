// API 기본 경로
const AI_API_URL = '/api/ai';

// DOM 요소
const messageBox = document.getElementById('message-box');
const userNameSpan = document.getElementById('user-name');
const profileButton = document.getElementById('profile-button');
const boardButton = document.getElementById('board-button');
const logoutButton = document.getElementById('logout-button');

const totalScore = document.getElementById('total-score');
const skinType = document.getElementById('skin-type');
const analysisDate = document.getElementById('analysis-date');

const moistureValue = document.getElementById('moisture-value');
const moistureBar = document.getElementById('moisture-bar');
const elasticityValue = document.getElementById('elasticity-value');
const elasticityBar = document.getElementById('elasticity-bar');
const poresValue = document.getElementById('pores-value');
const poresBar = document.getElementById('pores-bar');
const pigmentationValue = document.getElementById('pigmentation-value');
const pigmentationBar = document.getElementById('pigmentation-bar');

const summaryText = document.getElementById('summary-text');
const recommendationList = document.getElementById('recommendation-list');

const newAnalysisBtn = document.getElementById('new-analysis-btn');
const myAnalysesBtn = document.getElementById('my-analyses-btn');

// 현재 사용자 정보
let currentUser = null;

// 로그인 확인
function checkLogin() {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');

    if (!token || !user) {
        alert('로그인이 필요합니다.');
        window.location.href = '/index.html';
        return null;
    }

    return JSON.parse(user);
}

// 메시지 표시
function showMessage(message, type) {
    messageBox.textContent = message;
    messageBox.className = `message ${type}`;
    messageBox.style.display = 'block';
    setTimeout(() => {
        messageBox.textContent = '';
        messageBox.className = 'message';
        messageBox.style.display = 'none';
    }, 3000);
}

// API 요청 헬퍼
async function apiRequest(url, options = {}) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(url, {
            ...options,
            headers: {
                'Authorization': `Bearer ${token}`,
                ...options.headers
            }
        });
        return await response.json();
    } catch (error) {
        console.error('API 요청 에러:', error);
        return { success: false, message: '네트워크 오류가 발생했습니다.' };
    }
}

// 날짜 포맷팅
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 분석 결과 로드
async function loadAnalysis() {
    const urlParams = new URLSearchParams(window.location.search);
    const analysisId = urlParams.get('id');

    if (!analysisId) {
        showMessage('분석 ID가 없습니다.', 'error');
        setTimeout(() => {
            window.location.href = '/ai-analysis.html';
        }, 2000);
        return;
    }

    const result = await apiRequest(`${AI_API_URL}/analysis/${analysisId}`);

    if (result.success) {
        const analysis = result.data;
        displayAnalysis(analysis);
    } else {
        showMessage(result.message, 'error');
        setTimeout(() => {
            window.location.href = '/ai-analysis.html';
        }, 2000);
    }
}

// 분석 결과 표시
function displayAnalysis(analysis) {
    // 종합 점수
    totalScore.textContent = analysis.score;
    skinType.textContent = analysis.skinType;
    analysisDate.textContent = formatDate(analysis.createdAt);

    // 상세 분석 (애니메이션 효과)
    setTimeout(() => {
        updateBar(moistureValue, moistureBar, analysis.detailedAnalysis.moisture);
    }, 100);
    setTimeout(() => {
        updateBar(elasticityValue, elasticityBar, analysis.detailedAnalysis.elasticity);
    }, 300);
    setTimeout(() => {
        updateBar(poresValue, poresBar, analysis.detailedAnalysis.pores);
    }, 500);
    setTimeout(() => {
        updateBar(pigmentationValue, pigmentationBar, analysis.detailedAnalysis.pigmentation);
    }, 700);

    // 종합 의견
    summaryText.textContent = analysis.summary;

    // 추천 사항
    recommendationList.innerHTML = '';
    analysis.recommendations.forEach(rec => {
        const li = document.createElement('li');
        li.className = 'recommendation-item';
        li.textContent = rec;
        recommendationList.appendChild(li);
    });
}

// 바 업데이트
function updateBar(valueElement, barElement, value) {
    valueElement.textContent = `${value}%`;
    barElement.style.width = `${value}%`;
}

// 로그아웃
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    showMessage('로그아웃되었습니다.', 'success');
    setTimeout(() => {
        window.location.href = '/index.html';
    }, 1000);
}

// 이벤트 리스너
profileButton.addEventListener('click', () => window.location.href = '/profile.html');
boardButton.addEventListener('click', () => window.location.href = '/board.html');
logoutButton.addEventListener('click', logout);
newAnalysisBtn.addEventListener('click', () => window.location.href = '/ai-analysis.html');
myAnalysesBtn.addEventListener('click', () => window.location.href = '/profile.html'); // 프로필에서 분석 기록 보기

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    currentUser = checkLogin();
    if (currentUser) {
        userNameSpan.textContent = `${currentUser.name}님`;
        loadAnalysis();
    }
});
