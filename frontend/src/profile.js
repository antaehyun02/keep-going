// API 기본 경로
const AUTH_API_URL = '/api/auth';

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
    const messageBox = document.getElementById('message-box');
    if (messageBox) {
        messageBox.textContent = message;
        messageBox.className = `message ${type}`;
        messageBox.style.display = 'block';
        setTimeout(() => {
            messageBox.textContent = '';
            messageBox.className = 'message';
            messageBox.style.display = 'none';
        }, 3000);
    }
}

// API 요청 헬퍼
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
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

// 프로필 정보 로드
async function loadProfile() {
    const result = await apiRequest(`${AUTH_API_URL}/profile?userId=${currentUser.id}`, {
        method: 'GET'
    });

    if (result.success) {
        const profile = result.data;

        // 헤더 업데이트
        const userNameDisplay = document.getElementById('user-name-display');
        const userEmailDisplay = document.getElementById('user-email-display');
        const profileAvatar = document.getElementById('profile-avatar');

        if (userNameDisplay) userNameDisplay.textContent = profile.name;
        if (userEmailDisplay) userEmailDisplay.textContent = profile.email;
        if (profileAvatar) profileAvatar.textContent = profile.name.charAt(0).toUpperCase();

        // 프로필 정보 탭 업데이트
        const profileEmail = document.getElementById('profile-email');
        const profileCreated = document.getElementById('profile-created');
        const editNameInput = document.getElementById('edit-name');

        if (profileEmail) profileEmail.textContent = profile.email;
        if (profileCreated) profileCreated.textContent = formatDate(profile.createdAt);
        if (editNameInput) editNameInput.value = profile.name;
    } else {
        showMessage(result.message, 'error');
    }
}

// 프로필 수정
async function updateProfile(e) {
    e.preventDefault();

    const editNameInput = document.getElementById('edit-name');
    const currentPasswordInput = document.getElementById('current-password');
    const newPasswordInput = document.getElementById('new-password');

    const name = editNameInput?.value.trim();
    const currentPassword = currentPasswordInput?.value;
    const newPassword = newPasswordInput?.value;

    // 이름도 비밀번호도 변경하지 않는 경우
    if (!name && !currentPassword && !newPassword) {
        showMessage('변경할 내용을 입력해주세요.', 'error');
        return;
    }

    // 비밀번호 변경 시 검증
    if ((currentPassword && !newPassword) || (!currentPassword && newPassword)) {
        showMessage('현재 비밀번호와 새 비밀번호를 모두 입력해주세요.', 'error');
        return;
    }

    const data = {
        userId: currentUser.id
    };

    if (name) data.name = name;
    if (currentPassword) data.currentPassword = currentPassword;
    if (newPassword) data.newPassword = newPassword;

    const result = await apiRequest(`${AUTH_API_URL}/profile`, {
        method: 'PUT',
        body: JSON.stringify(data)
    });

    if (result.success) {
        showMessage(result.message, 'success');

        // localStorage 업데이트
        const updatedUser = {
            ...currentUser,
            name: result.data.name
        };
        localStorage.setItem('user', JSON.stringify(updatedUser));
        currentUser = updatedUser;

        // 폼 초기화
        if (currentPasswordInput) currentPasswordInput.value = '';
        if (newPasswordInput) newPasswordInput.value = '';

        // 프로필 다시 로드
        await loadProfile();
    } else {
        showMessage(result.message || '프로필 수정에 실패했습니다.', 'error');
    }
}

// AI 분석 기록 로드
async function loadMyAnalyses() {
    const result = await apiRequest(`/api/ai/my-analyses`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    });

    const analysesList = document.getElementById('analyses-list');
    const analysesEmpty = document.getElementById('analyses-empty');

    if (result.success) {
        const analyses = result.data;

        if (analyses.length === 0) {
            if (analysesList) analysesList.style.display = 'none';
            if (analysesEmpty) analysesEmpty.style.display = 'block';
        } else {
            if (analysesList) analysesList.style.display = 'grid';
            if (analysesEmpty) analysesEmpty.style.display = 'none';
            renderMyAnalyses(analyses);
        }
    } else {
        showMessage(result.message, 'error');
    }
}

// AI 분석 기록 렌더링
function renderMyAnalyses(analyses) {
    const analysesList = document.getElementById('analyses-list');
    if (!analysesList) return;

    analysesList.innerHTML = '';

    analyses.forEach(analysis => {
        const card = document.createElement('div');
        card.className = 'analysis-card';
        card.onclick = () => {
            window.location.href = `/ai-result.html?id=${analysis.id}`;
        };

        card.innerHTML = `
            <div class="analysis-image">
                <img src="/uploads/${escapeHtml(analysis.imageFilename)}" alt="피부 사진">
            </div>
            <div class="analysis-info">
                <div class="analysis-date">${formatDate(analysis.createdAt)}</div>
                <div class="analysis-result">피부 타입: ${escapeHtml(analysis.skinType || '분석 중')}</div>
            </div>
        `;

        analysesList.appendChild(card);
    });
}

// 내가 쓴 글 로드
async function loadMyPosts() {
    const result = await apiRequest(`${AUTH_API_URL}/my-posts?userId=${currentUser.id}`, {
        method: 'GET'
    });

    const myPostsList = document.getElementById('my-posts-list');
    const postsEmpty = document.getElementById('posts-empty');

    if (result.success) {
        const posts = result.data;

        if (posts.length === 0) {
            if (myPostsList) myPostsList.style.display = 'none';
            if (postsEmpty) postsEmpty.style.display = 'block';
        } else {
            if (myPostsList) myPostsList.style.display = 'block';
            if (postsEmpty) postsEmpty.style.display = 'none';
            renderMyPosts(posts);
        }
    } else {
        showMessage(result.message, 'error');
    }
}

// 내가 쓴 글 렌더링
function renderMyPosts(posts) {
    const myPostsList = document.getElementById('my-posts-list');
    if (!myPostsList) return;

    myPostsList.innerHTML = '';

    // 카테고리 한글 매핑
    const categoryNames = {
        'free': '자유게시판',
        'question': '질문',
        'info': '정보공유'
    };

    posts.forEach(post => {
        const li = document.createElement('li');
        li.className = 'activity-item';
        li.onclick = () => {
            window.location.href = `/post-detail.html?id=${post.id}`;
        };

        const categoryName = categoryNames[post.category] || '자유게시판';

        li.innerHTML = `
            <div class="activity-title">
                <span class="category-badge">${categoryName}</span>
                ${escapeHtml(post.title)}
            </div>
            <div class="activity-content">${escapeHtml(post.content)}</div>
            <div class="activity-meta">조회 ${post.views} · ${formatDate(post.createdAt)}</div>
        `;

        myPostsList.appendChild(li);
    });
}

// 내가 쓴 댓글 로드
async function loadMyComments() {
    const result = await apiRequest(`${AUTH_API_URL}/my-comments?userId=${currentUser.id}`, {
        method: 'GET'
    });

    const myCommentsList = document.getElementById('my-comments-list');
    const commentsEmpty = document.getElementById('comments-empty');

    if (result.success) {
        const comments = result.data;

        if (comments.length === 0) {
            if (myCommentsList) myCommentsList.style.display = 'none';
            if (commentsEmpty) commentsEmpty.style.display = 'block';
        } else {
            if (myCommentsList) myCommentsList.style.display = 'block';
            if (commentsEmpty) commentsEmpty.style.display = 'none';
            renderMyComments(comments);
        }
    } else {
        showMessage(result.message, 'error');
    }
}

// 내가 쓴 댓글 렌더링
function renderMyComments(comments) {
    const myCommentsList = document.getElementById('my-comments-list');
    if (!myCommentsList) return;

    myCommentsList.innerHTML = '';

    comments.forEach(comment => {
        const li = document.createElement('li');
        li.className = 'activity-item';
        li.onclick = () => {
            window.location.href = `/post-detail.html?id=${comment.postId}`;
        };

        li.innerHTML = `
            <div class="activity-title">게시글: ${escapeHtml(comment.postTitle)}</div>
            <div class="activity-content">${escapeHtml(comment.content)}</div>
            <div class="activity-meta">${formatDate(comment.createdAt)}</div>
        `;

        myCommentsList.appendChild(li);
    });
}

// HTML 이스케이프 (XSS 방지)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 탭 전환
function switchTab(tabName) {
    // 모든 탭 비활성화
    document.querySelectorAll('.profile-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // 선택한 탭 활성화
    const selectedTab = document.querySelector(`.profile-tab[data-tab="${tabName}"]`);
    const selectedContent = document.getElementById(`${tabName}-content`);

    if (selectedTab) selectedTab.classList.add('active');
    if (selectedContent) selectedContent.classList.add('active');

    // 데이터 로드
    if (tabName === 'analyses') {
        loadMyAnalyses();
    } else if (tabName === 'posts') {
        loadMyPosts();
    } else if (tabName === 'comments') {
        loadMyComments();
    }
}

// 회원 탈퇴
async function deleteAccount() {
    const confirmed = confirm('정말로 회원 탈퇴하시겠습니까?\n모든 데이터가 영구적으로 삭제됩니다.');
    if (!confirmed) return;

    const password = prompt('비밀번호를 입력하세요:');
    if (!password) {
        showMessage('비밀번호를 입력해야 합니다.', 'error');
        return;
    }

    const result = await apiRequest(`${AUTH_API_URL}/delete`, {
        method: 'DELETE',
        body: JSON.stringify({
            email: currentUser.email,
            password: password
        })
    });

    if (result.success) {
        alert('회원 탈퇴가 완료되었습니다.');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/index.html';
    } else {
        showMessage(result.message || '회원 탈퇴에 실패했습니다.', 'error');
    }
}

// 로그아웃
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/index.html';
}

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    currentUser = checkLogin();
    if (currentUser) {
        loadProfile();
        // 첫 번째 탭(내 정보)이 기본으로 활성화되어 있으므로 추가 로드 불필요
    }

    // 이벤트 리스너
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', updateProfile);
    }

    document.querySelectorAll('.profile-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.dataset.tab);
        });
    });

    const deleteAccountBtn = document.getElementById('delete-account-btn');
    if (deleteAccountBtn) {
        deleteAccountBtn.addEventListener('click', deleteAccount);
    }

    // 로그아웃 버튼
    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', logout);
    }
});
