// API 기본 경로
const API_BASE_URL = '/api/board';

// DOM 요소
const postTitle = document.getElementById('post-title');
const postAuthor = document.getElementById('post-author');
const postDate = document.getElementById('post-date');
const postViews = document.getElementById('post-views');
const postContent = document.getElementById('post-content');
const postActions = document.getElementById('post-actions');
const likeButton = document.getElementById('like-button');
const likeCount = document.getElementById('like-count');
const commentCount = document.getElementById('comment-count');
const commentInput = document.getElementById('comment-input');
const commentsList = document.getElementById('comments-list');
const messageBox = document.getElementById('message-box');

let currentPost = null;
let currentUser = null;
let hasLiked = false;

// URL에서 게시글 ID 가져오기
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

// 날짜 포맷팅
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// HTML 이스케이프
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 게시글 불러오기
async function loadPost() {
    const postId = getPostId();
    if (!postId) {
        alert('잘못된 접근입니다.');
        window.location.href = '/board.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/free/posts/${postId}`);
        const result = await response.json();

        if (result.success) {
            currentPost = result.data;
            renderPost(currentPost);
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

// 게시글 렌더링
function renderPost(post) {
    postTitle.textContent = post.title;
    postAuthor.textContent = `작성자: ${post.authorName}`;
    postDate.textContent = `작성일: ${formatDate(post.createdAt)}`;
    postViews.textContent = `조회수: ${post.views}`;
    postContent.textContent = post.content;

    // 작성자인 경우 수정/삭제 버튼 표시
    if (currentUser && currentUser.id === post.authorId) {
        postActions.style.display = 'flex';
    }

    // 좋아요 수 표시
    likeCount.textContent = `${post.likeCount}명이 좋아합니다`;

    // 댓글 렌더링
    commentCount.textContent = post.commentCount;
    renderComments(post.comments);
}

// 댓글 렌더링
function renderComments(comments) {
    commentsList.innerHTML = '';

    if (!comments || comments.length === 0) {
        commentsList.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">첫 댓글을 작성해보세요!</p>';
        return;
    }

    comments.forEach(comment => {
        const commentDiv = document.createElement('div');
        commentDiv.className = 'comment-item';

        const isAuthor = currentUser && currentUser.id === comment.authorId;

        commentDiv.innerHTML = `
            <div class="comment-header">
                <span class="comment-author">${escapeHtml(comment.authorName)}</span>
                <span class="comment-date">${formatDate(comment.createdAt)}</span>
            </div>
            <div class="comment-content">${escapeHtml(comment.content)}</div>
            ${isAuthor ? `
                <div class="comment-actions">
                    <button class="danger small" onclick="deleteComment(${comment.id})">삭제</button>
                </div>
            ` : ''}
        `;

        commentsList.appendChild(commentDiv);
    });
}

// 좋아요
async function likePost() {
    if (hasLiked) {
        showMessage('이미 좋아요를 눌렀습니다.', 'error');
        return;
    }

    const postId = getPostId();

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/free/posts/${postId}/like`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ userId: currentUser.id })
        });

        const result = await response.json();

        if (result.success) {
            showMessage(result.message, 'success');
            hasLiked = true;
            likeButton.classList.add('liked');
            likeButton.textContent = '❤️ 좋아요 완료';
            likeCount.textContent = `${result.data.likeCount}명이 좋아합니다`;
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('좋아요 에러:', error);
        showMessage('좋아요를 누르는데 실패했습니다.', 'error');
    }
}

// 댓글 작성
async function submitComment() {
    const content = commentInput.value.trim();

    if (!content) {
        showMessage('댓글 내용을 입력해주세요.', 'error');
        return;
    }

    const postId = getPostId();

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/free/posts/${postId}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                content,
                authorId: currentUser.id,
                authorName: currentUser.name
            })
        });

        const result = await response.json();

        if (result.success) {
            showMessage(result.message, 'success');
            commentInput.value = '';
            loadPost(); // 게시글 다시 로드
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('댓글 작성 에러:', error);
        showMessage('댓글 작성에 실패했습니다.', 'error');
    }
}

// 댓글 삭제
async function deleteComment(commentId) {
    if (!confirm('댓글을 삭제하시겠습니까?')) {
        return;
    }

    const postId = getPostId();

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/free/posts/${postId}/comments/${commentId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ authorId: currentUser.id })
        });

        const result = await response.json();

        if (result.success) {
            showMessage(result.message, 'success');
            loadPost(); // 게시글 다시 로드
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('댓글 삭제 에러:', error);
        showMessage('댓글 삭제에 실패했습니다.', 'error');
    }
}

// 게시글 수정
function editPost() {
    window.location.href = `/post-write.html?id=${getPostId()}`;
}

// 게시글 삭제
async function deletePost() {
    if (!confirm('게시글을 삭제하시겠습니까?')) {
        return;
    }

    const postId = getPostId();

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/free/posts/${postId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ authorId: currentUser.id })
        });

        const result = await response.json();

        if (result.success) {
            showMessage(result.message, 'success');
            setTimeout(() => {
                window.location.href = '/board.html';
            }, 1000);
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('게시글 삭제 에러:', error);
        showMessage('게시글 삭제에 실패했습니다.', 'error');
    }
}

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    currentUser = checkLogin();
    if (currentUser) {
        loadPost();
    }
});
