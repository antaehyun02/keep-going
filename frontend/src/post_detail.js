// ═══════════════════════════════════════════════════
//  post_detail.js  —  커뮤니티 게시글 상세 UI
//
//  [순수 프론트 영역]
//    - 좋아요 / 북마크 토글
//    - 댓글 textarea 자동 높이
//    - 댓글 등록 버튼 활성화
//    - 답글 입력창 토글
//    - 댓글 좋아요 토글
//    - 공유
//
//  [DB 팀 연동 필요 영역]
//    - loadPost()         : GET /api/posts/:id
//    - submitComment()    : POST /api/posts/:id/comments
//    - toggleLike()       : POST /api/posts/:id/like
//    - toggleBookmark()   : POST /api/posts/:id/bookmark
// ═══════════════════════════════════════════════════


// ── 좋아요 토글 ──────────────────────────────────────
let liked = false;
function toggleLike() {
  liked = !liked;
  const btn = document.getElementById('likeBtn');
  const countEl = document.getElementById('likeCount');
  let count = parseInt(countEl.textContent);
  if (liked) {
    btn.classList.add('liked');
    countEl.textContent = count + 1;
    showToast('도움이 됐어요!');
  } else {
    btn.classList.remove('liked');
    countEl.textContent = count - 1;
  }
  // ── DB 팀 연동 영역 ──────────────────────────────
  // TODO: POST /api/posts/:id/like  { liked }
  // ── DB 팀 연동 영역 끝 ──────────────────────────
}


// ── 북마크 토글 ──────────────────────────────────────
let bookmarked = false;
function toggleBookmark() {
  bookmarked = !bookmarked;
  const btns = [document.getElementById('bookmarkBtn'), document.getElementById('bookmarkReactBtn')];
  btns.forEach(btn => {
    if (!btn) return;
    if (bookmarked) {
      btn.classList.add('bookmarked');
      btn.style.borderColor = '#f59e0b';
      btn.style.color = '#f59e0b';
      btn.style.background = '#fffbeb';
    } else {
      btn.classList.remove('bookmarked');
      btn.style.borderColor = '';
      btn.style.color = '';
      btn.style.background = '';
    }
  });
  showToast(bookmarked ? '북마크에 저장됐어요' : '북마크가 해제됐어요');
  // ── DB 팀 연동 영역 ──────────────────────────────
  // TODO: POST /api/posts/:id/bookmark  { bookmarked }
  // ── DB 팀 연동 영역 끝 ──────────────────────────
}


// ── 댓글 textarea 자동 높이 ───────────────────────────
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}


// ── 댓글 등록 버튼 활성화 ─────────────────────────────
function updateSubmitBtn() {
  const val = document.getElementById('commentInput').value.trim();
  document.getElementById('commentSubmitBtn').disabled = val.length === 0;
}


// ── 댓글 등록 ─────────────────────────────────────────
function submitComment() {
  const input = document.getElementById('commentInput');
  const text = input.value.trim();
  if (!text) return;

  // 새 댓글 DOM 생성
  const now = new Date();
  const dateStr = `${now.getFullYear()}.${String(now.getMonth()+1).padStart(2,'0')}.${String(now.getDate()).padStart(2,'0')} · ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  const item = document.createElement('div');
  item.className = 'comment-item';
  item.style.animation = 'pageFadeIn 0.3s ease';
  item.innerHTML = `
    <div class="comment-header">
      <div class="comment-author">
        <div class="comment-avatar">김</div>
        <div>
          <div class="comment-name">김OO <span class="role-badge badge-resident">전공의</span></div>
          <div class="comment-date">${dateStr}</div>
        </div>
      </div>
    </div>
    <div class="comment-text">${text.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>
    <div class="comment-actions">
      <button class="comment-action-btn" onclick="toggleCommentLike(this)">
        <svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
        0
      </button>
      <button class="comment-action-btn" onclick="showReplyInput(this)">
        <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        답글
      </button>
    </div>`;
  document.getElementById('commentList').appendChild(item);

  // 댓글 수 업데이트
  const totalEl = document.getElementById('commentTotal');
  totalEl.textContent = parseInt(totalEl.textContent) + 1;

  // 입력창 초기화
  input.value = '';
  input.style.height = 'auto';
  document.getElementById('commentSubmitBtn').disabled = true;
  showToast('댓글이 등록됐어요');

  // ── DB 팀 연동 영역 ──────────────────────────────
  // TODO: POST /api/posts/:id/comments  { content: text }
  // ── DB 팀 연동 영역 끝 ──────────────────────────
}


// ── 답글 입력창 토글 ──────────────────────────────────
function showReplyInput(btn) {
  const commentItem = btn.closest('.comment-item');
  const existing = commentItem.querySelector('.reply-write');
  if (existing) { existing.remove(); return; }

  const div = document.createElement('div');
  div.className = 'reply-write';
  div.style.cssText = 'margin-top:10px; padding-left:38px; display:flex; gap:8px; align-items:flex-start;';
  div.innerHTML = `
    <div class="write-avatar" style="width:26px;height:26px;font-size:10px;flex-shrink:0;">김</div>
    <div style="flex:1;">
      <textarea class="write-textarea" placeholder="답글을 입력하세요..." rows="1" style="font-size:12px;" oninput="autoResize(this)"></textarea>
      <div style="display:flex;justify-content:flex-end;margin-top:6px;gap:6px;">
        <button onclick="this.closest('.reply-write').remove()" style="padding:6px 12px;border-radius:8px;border:1px solid #e5e7eb;background:#fff;font-size:12px;font-weight:600;color:#6b7280;cursor:pointer;font-family:inherit;">취소</button>
        <button class="submit-btn" style="padding:6px 14px;font-size:12px;" onclick="submitReply(this)">등록</button>
      </div>
    </div>`;
  commentItem.appendChild(div);
  div.querySelector('textarea').focus();
}


// ── 답글 등록 ─────────────────────────────────────────
function submitReply(btn) {
  const wrap = btn.closest('.reply-write');
  const text = wrap.querySelector('textarea').value.trim();
  if (!text) return;

  const commentItem = wrap.closest('.comment-item');
  const now = new Date();
  const dateStr = `${now.getFullYear()}.${String(now.getMonth()+1).padStart(2,'0')}.${String(now.getDate()).padStart(2,'0')} · ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  const reply = document.createElement('div');
  reply.className = 'reply-item';
  reply.innerHTML = `
    <div class="comment-header">
      <div class="comment-author">
        <div class="comment-avatar" style="width:26px;height:26px;font-size:10px;">김</div>
        <div>
          <div class="comment-name" style="font-size:12px;">김OO <span class="role-badge badge-resident">전공의</span></div>
          <div class="comment-date">${dateStr}</div>
        </div>
      </div>
    </div>
    <div class="comment-text" style="font-size:12px;">${text.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>`;
  commentItem.insertBefore(reply, wrap);
  wrap.remove();
  showToast('답글이 등록됐어요');
}


// ── 댓글 좋아요 ───────────────────────────────────────
function toggleCommentLike(btn) {
  const isLiked = btn.dataset.liked === 'true';
  const count = parseInt(btn.textContent.trim()) || 0;
  btn.dataset.liked = !isLiked;
  btn.style.color = !isLiked ? '#ef4444' : '';
  const texts = btn.childNodes;
  texts[texts.length - 1].textContent = ' ' + (isLiked ? count - 1 : count + 1);
}


// ── 공유 ──────────────────────────────────────────────
function sharePost() {
  if (navigator.share) {
    navigator.share({ title: document.getElementById('postTitle').textContent, url: location.href });
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
