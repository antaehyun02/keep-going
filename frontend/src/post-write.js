// API 기본 경로
const API_BASE_URL = '/api/board';

// DOM 요소
const pageTitle = document.getElementById('page-title');
const postForm = document.getElementById('post-form');
const categorySelect = document.getElementById('category');
const titleInput = document.getElementById('title');
const contentInput = document.getElementById('content');
const titleCount = document.getElementById('title-count');
const contentCount = document.getElementById('content-count');
const submitButton = document.getElementById('submit-button');
const successMessage = document.getElementById('success-message');
const messageBox = document.getElementById('message-box');

let currentUser = null;
let editMode = false;
let editPostId = null;

// URL에서 게시글 ID 가져오기 (수정 모드)
function getPostId() {
    const params = new URLSearchParams(window.location.search);
    return params.get('id');
}

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
    setTimeout(() => {
        messageBox.textContent = '';
        messageBox.className = 'message';
    }, 3000);
}

// 글자 수 업데이트
function updateCharCount() {
    const titleLength = titleInput.value.length;
    const contentLength = contentInput.value.length;

    titleCount.textContent = `${titleLength} / 100`;
    contentCount.textContent = `${contentLength}자`;
}

// 게시글 불러오기 (수정 모드)
async function loadPost() {
    const postId = getPostId();
    if (!postId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/free/posts/${postId}`);
        const result = await response.json();

        if (result.success) {
            const post = result.data;

            // 작성자 확인
            if (post.authorId !== currentUser.id) {
                alert('수정 권한이 없습니다.');
                window.location.href = '/board.html';
                return;
            }

            // 수정 모드 설정
            editMode = true;
            editPostId = postId;
            pageTitle.textContent = '글 수정';
            submitButton.textContent = '수정';

            // 폼에 데이터 채우기
            categorySelect.value = post.category || 'free';
            titleInput.value = post.title;
            contentInput.value = post.content;
            updateCharCount();
        } else {
            showMessage(result.message, 'error');
            setTimeout(() => {
                window.location.href = '/board.html';
            }, 2000);
        }
    } catch (error) {
        console.error('게시글 로딩 에러:', error);
        showMessage('게시글을 불러오는데 실패했습니다.', 'error');
    }
}

// 게시판 목록으로 이동
function goToBoard() {
    window.location.href = '/board.html';
}

// 게시글 작성
async function createPost(category, title, content) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/free/posts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                category,
                title,
                content,
                authorId: currentUser.id,
                authorName: currentUser.name
            })
        });

        const result = await response.json();

        if (result.success) {
            // 폼 숨기고 성공 메시지 표시
            postForm.style.display = 'none';
            successMessage.style.display = 'block';

            // 3초 후 자동으로 게시판으로 이동
            setTimeout(() => {
                window.location.href = '/board.html';
            }, 3000);
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('게시글 작성 에러:', error);
        showMessage('게시글 작성에 실패했습니다.', 'error');
    }
}

// 게시글 수정
async function updatePost(category, title, content) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/free/posts/${editPostId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                category,
                title,
                content,
                authorId: currentUser.id
            })
        });

        const result = await response.json();

        if (result.success) {
            showMessage(result.message, 'success');
            setTimeout(() => {
                window.location.href = `/post-detail.html?id=${editPostId}`;
            }, 1000);
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('게시글 수정 에러:', error);
        showMessage('게시글 수정에 실패했습니다.', 'error');
    }
}

// 폼 제출
postForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const category = categorySelect.value;
    const title = titleInput.value.trim();
    const content = contentInput.value.trim();

    if (!category) {
        showMessage('카테고리를 선택해주세요.', 'error');
        categorySelect.focus();
        return;
    }

    if (!title) {
        showMessage('제목을 입력해주세요.', 'error');
        titleInput.focus();
        return;
    }

    if (!content) {
        showMessage('내용을 입력해주세요.', 'error');
        contentInput.focus();
        return;
    }

    // 버튼 비활성화 (중복 제출 방지)
    submitButton.disabled = true;

    if (editMode) {
        await updatePost(category, title, content);
    } else {
        await createPost(category, title, content);
    }

    // 버튼 다시 활성화
    submitButton.disabled = false;
});

// 글자 수 카운터 이벤트 리스너
titleInput.addEventListener('input', updateCharCount);
contentInput.addEventListener('input', updateCharCount);

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    currentUser = checkLogin();
    if (currentUser) {
        loadPost(); // 수정 모드인 경우 게시글 로드
        updateCharCount();
    }
});
