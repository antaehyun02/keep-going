// API 기본 경로
const AI_API_URL = '/api/ai';
const AUTH_API_URL = '/api/auth';

// DOM 요소
const messageBox = document.getElementById('message-box');
const userNameSpan = document.getElementById('user-name');
const profileButton = document.getElementById('profile-button');
const boardButton = document.getElementById('board-button');
const logoutButton = document.getElementById('logout-button');

const step1 = document.getElementById('step-1');
const step2 = document.getElementById('step-2');

const uploadArea = document.getElementById('upload-area');
const imageInput = document.getElementById('image-input');
const previewContainer = document.getElementById('preview-container');
const previewImage = document.getElementById('preview-image');
const uploadButton = document.getElementById('upload-button');

const surveyForm = document.getElementById('survey-form');
const surveyQuestionsDiv = document.getElementById('survey-questions');
const backButton = document.getElementById('back-button');

const loadingOverlay = document.getElementById('loading-overlay');

// 현재 사용자 정보
let currentUser = null;
let uploadedImageFilename = null;
let selectedFile = null;
let surveyQuestions = [];

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

// 로딩 표시
function showLoading() {
    loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
}

// 이미지 업로드 영역 이벤트
uploadArea.addEventListener('click', () => {
    imageInput.click();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFileSelect(file);
    }
});

// 파일 선택 처리
function handleFileSelect(file) {
    // 파일 유효성 검사
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
        showMessage('JPG 또는 PNG 파일만 업로드 가능합니다.', 'error');
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        showMessage('파일 크기는 5MB 이하여야 합니다.', 'error');
        return;
    }

    selectedFile = file;

    // 미리보기 표시
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        previewContainer.style.display = 'block';
        uploadButton.disabled = false;
    };
    reader.readAsDataURL(file);
}

// 이미지 업로드
uploadButton.addEventListener('click', async () => {
    if (!selectedFile) {
        showMessage('이미지를 선택해주세요.', 'error');
        return;
    }

    showLoading();

    const formData = new FormData();
    formData.append('image', selectedFile);

    const token = localStorage.getItem('token');
    try {
        const response = await fetch(`${AI_API_URL}/image-upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const result = await response.json();
        hideLoading();

        if (result.success) {
            uploadedImageFilename = result.data.filename;
            showMessage('이미지가 업로드되었습니다.', 'success');

            // Step 2로 이동
            step1.classList.add('step-hidden');
            step2.classList.remove('step-hidden');

            // 설문지 로드
            await loadSurveyQuestions();
        } else {
            showMessage(result.message || '이미지 업로드에 실패했습니다.', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('업로드 에러:', error);
        showMessage('이미지 업로드 중 오류가 발생했습니다.', 'error');
    }
});

// 설문지 질문 로드
async function loadSurveyQuestions() {
    const result = await apiRequest(`${AI_API_URL}/survey/questions`);

    if (result.success) {
        surveyQuestions = result.data;
        renderSurveyQuestions();
    } else {
        showMessage(result.message, 'error');
    }
}

// 설문지 렌더링
function renderSurveyQuestions() {
    surveyQuestionsDiv.innerHTML = '';

    surveyQuestions.forEach((q, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'survey-question';

        const questionText = document.createElement('div');
        questionText.className = 'question-text';
        questionText.innerHTML = `${index + 1}. ${q.question}${q.required ? ' <span class="required">*</span>' : ''}`;
        questionDiv.appendChild(questionText);

        if (q.type === 'radio') {
            const optionGroup = document.createElement('div');
            optionGroup.className = 'option-group';

            q.options.forEach((option, optIndex) => {
                const label = document.createElement('label');
                label.className = 'option-label';

                const input = document.createElement('input');
                input.type = 'radio';
                input.name = `question-${q.id}`;
                input.value = option;
                input.required = q.required;

                label.appendChild(input);
                label.appendChild(document.createTextNode(option));
                optionGroup.appendChild(label);
            });

            questionDiv.appendChild(optionGroup);
        } else if (q.type === 'checkbox') {
            const optionGroup = document.createElement('div');
            optionGroup.className = 'option-group';

            q.options.forEach((option, optIndex) => {
                const label = document.createElement('label');
                label.className = 'option-label';

                const input = document.createElement('input');
                input.type = 'checkbox';
                input.name = `question-${q.id}`;
                input.value = option;

                label.appendChild(input);
                label.appendChild(document.createTextNode(option));
                optionGroup.appendChild(label);
            });

            questionDiv.appendChild(optionGroup);
        } else if (q.type === 'text') {
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'text-input';
            input.name = `question-${q.id}`;
            input.placeholder = '답변을 입력하세요';
            input.required = q.required;

            questionDiv.appendChild(input);
        }

        surveyQuestionsDiv.appendChild(questionDiv);
    });
}

// 설문지 제출
surveyForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const answers = [];

    surveyQuestions.forEach(q => {
        if (q.type === 'radio') {
            const selected = document.querySelector(`input[name="question-${q.id}"]:checked`);
            answers.push(selected ? selected.value : null);
        } else if (q.type === 'checkbox') {
            const checked = Array.from(document.querySelectorAll(`input[name="question-${q.id}"]:checked`));
            answers.push(checked.map(c => c.value));
        } else if (q.type === 'text') {
            const input = document.querySelector(`input[name="question-${q.id}"]`);
            answers.push(input ? input.value : '');
        }
    });

    showLoading();

    const result = await apiRequest(`${AI_API_URL}/survey`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            imageFilename: uploadedImageFilename,
            answers: answers
        })
    });

    hideLoading();

    if (result.success) {
        showMessage('분석이 완료되었습니다!', 'success');
        // 분석 결과 페이지로 이동
        setTimeout(() => {
            window.location.href = `/ai-result.html?id=${result.data.analysisId}`;
        }, 1000);
    } else {
        showMessage(result.message || '설문 제출에 실패했습니다.', 'error');
    }
});

// 이전 버튼
backButton.addEventListener('click', () => {
    step2.classList.add('step-hidden');
    step1.classList.remove('step-hidden');
});

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

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    currentUser = checkLogin();
    if (currentUser) {
        userNameSpan.textContent = `${currentUser.name}님`;
    }
});
