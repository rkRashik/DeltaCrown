/* DeltaCrown Community — post card variants. */
(function () {
const { useState, useRef, useEffect } = React;

function initialsOf(name) {
  return (name || '').split(/\s+/).filter(Boolean).map(p => p[0]).slice(0, 2).join('').toUpperCase();
}

/* Strip inline Tailwind CSS variable styles and paste artifacts from user HTML */
function sanitizeHTML(raw) {
  if (!raw) return '';
  const div = document.createElement('div');
  div.innerHTML = raw
    .replace(/<!--(Start|End)Fragment-->/gi, '')
    .replace(/\s*style="[^"]*"/gi, '')
    .replace(/\s*class="[^"]*"/gi, '');
  return div.innerHTML.trim();
}

function PostBody({ html, plain }) {
  const [expanded, setExpanded] = useState(false);
  const content = html || plain || '';
  const isHTML = content.indexOf('<') >= 0;
  const cleaned = isHTML ? sanitizeHTML(content) : content;
  const isLong = cleaned.length > 600;
  const visible = isLong && !expanded ? cleaned.slice(0, 600) + '…' : cleaned;
  return (
    <div className="dc-post-body">
      {isHTML
        ? <div dangerouslySetInnerHTML={{ __html: visible }} />
        : <p className="whitespace-pre-wrap">{visible}</p>}
      {isLong && !expanded && (
        <button onClick={() => setExpanded(true)} className="text-xs mt-1 hover:underline" style={{ color: 'var(--dc-accent)' }}>
          Read more
        </button>
      )}
    </div>
  );
}

function Avatar({ user, size = 40, square = false }) {
  if (!user) user = { name: '?', color1: '#7B2BFF', color2: '#00E5FF' };
  const s = { width: size, height: size };
  const hasImg = !!user.avatar_url;
  const inner = hasImg ? (
    <img src={user.avatar_url} alt={user.name || ''}
         className="w-full h-full object-cover"
         style={{ borderRadius: square ? 11 : '50%' }}
         onError={(e) => { e.currentTarget.style.display = 'none'; }} />
  ) : (
    <div className="dc-avatar-ph w-full h-full text-sm"
         style={{ '--c1': user.color1 || '#7B2BFF', '--c2': user.color2 || '#00E5FF' }}>
      {initialsOf(user.name)}
    </div>
  );
  if (square) return <div className="dc-avatar-sq" style={s}>{inner}</div>;
  return <div className="dc-avatar" style={s}>{inner}</div>;
}

function GameHex({ game, size = 28 }) {
  if (!game || !game.logo) return null;
  return (
    <div className="dc-hex" style={{ '--size': `${size}px` }} title={game.name}>
      <img src={game.logo} alt={game.name} onError={(e) => { e.currentTarget.parentElement.style.display = 'none'; }} />
    </div>
  );
}

function VerifiedTick() {
  return (
    <span className="inline-grid place-items-center w-4 h-4 rounded-full bg-dc-cyan ml-1" title="Verified">
      <i className="fa-solid fa-check text-[8px] text-black"></i>
    </span>
  );
}

function StaffBadge() {
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md ml-1.5"
          style={{ background: 'rgba(255,209,102,0.12)', border: '1px solid rgba(255,209,102,0.3)' }}>
      <i className="fa-solid fa-shield-halved text-[9px] text-dc-gold"></i>
      <span className="text-[9px] font-bold tracking-wider text-dc-gold">STAFF</span>
    </span>
  );
}

/* ---- 3-dot post menu ---- */
function PostMenu({ post, onClose, isOwn }) {
  return (
    <div className="dc-post-menu" onClick={e => e.stopPropagation()}>
      <div className="dc-post-menu-label">Post options</div>
      <button className="dc-post-menu-item" onClick={onClose}>
        <i className="fa-regular fa-bookmark"></i> Save post
      </button>
      <button className="dc-post-menu-item" onClick={onClose}>
        <i className="fa-solid fa-link"></i> Copy link
      </button>
      <button className="dc-post-menu-item" onClick={() => {
        try { navigator.clipboard.writeText(window.location.origin + '/community/#post-' + post.id); } catch(e) {}
        onClose();
      }}>
        <i className="fa-solid fa-share-nodes"></i> Share
      </button>
      <div className="dc-post-menu-sep"></div>
      <button className="dc-post-menu-item" onClick={onClose}>
        <i className="fa-regular fa-flag"></i> Report
      </button>
      <button className="dc-post-menu-item" onClick={onClose}>
        <i className="fa-regular fa-eye-slash"></i> Not interested
      </button>
      {isOwn && (
        <>
          <div className="dc-post-menu-sep"></div>
          <button className="dc-post-menu-item is-danger" onClick={() => {
            const api = window.DC && window.DC.api;
            if (api && api.fetchJSON && window.DC.api.urls) {
              const url = (window.DC.api.urls.like || '').replace(/\/0\/like\/$/, '/' + post._pk + '/delete/');
              api.fetchJSON && api.fetchJSON(url, { method: 'POST', headers: api.headersJSON() }).catch(() => {});
            }
            onClose();
          }}>
            <i className="fa-regular fa-trash-can"></i> Delete post
          </button>
        </>
      )}
    </div>
  );
}

function PostHeader({ post, onMenuToggle, menuOpen, closeMenu }) {
  const u = post.author;
  const isOwn = window.DC_CONFIG && window.DC_CONFIG.isAuthenticated &&
    window.DC.ME && window.DC.ME.handle === u.handle;

  return (
    <div className="flex items-start gap-3">
      <Avatar user={u} size={42} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center flex-wrap gap-x-1 gap-y-0.5">
          <span className="font-semibold text-white truncate">{u.name}</span>
          {u.verified && <VerifiedTick />}
          {u.isStaff && <StaffBadge />}
          {post.team && post.team.name && (
            <span className="text-[11px] text-white/40 ml-1">· {post.team.name}</span>
          )}
        </div>
        <div className="flex items-center gap-2 text-[11px] text-white/35 mt-0.5">
          <span>@{u.handle}</span>
          <span className="w-0.5 h-0.5 rounded-full bg-white/30"></span>
          <span>{post.ago} ago</span>
          {post.game && (
            <>
              <span className="w-0.5 h-0.5 rounded-full bg-white/30"></span>
              <span className="flex items-center gap-1">
                {post.game.logo && <span className="w-3 h-3 rounded-sm overflow-hidden"><img src={post.game.logo} className="w-full h-full object-cover" alt="" /></span>}
                {post.game.name}
              </span>
            </>
          )}
          {post.tournament && (
            <span className="dc-source-badge ml-1">
              <i className="fa-solid fa-trophy"></i>{post.tournament.name}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1 -mr-1 relative">
        {post.pinned && (
          <span className="dc-hud-label text-dc-gold flex items-center gap-1 mr-1">
            <i className="fa-solid fa-thumbtack text-[10px]"></i>
            <span>PINNED</span>
          </span>
        )}
        <button className="w-8 h-8 rounded-lg hover:bg-white/5 text-white/35 hover:text-white" onClick={onMenuToggle} aria-label="More">
          <i className="fa-solid fa-ellipsis"></i>
        </button>
        {menuOpen && <PostMenu post={post} isOwn={isOwn} onClose={closeMenu} />}
      </div>
    </div>
  );
}

/* ---- Reactions ---- */
function ReactionPicker({ onPick }) {
  const reactions = [
    { id: 'fire', icon: '🔥', label: 'Fire' },
    { id: 'gold', icon: '👑', label: 'Crown' },
    { id: 'love', icon: '❤️', label: 'Love' },
    { id: 'wow', icon: '🤯', label: 'Mind blown' },
    { id: 'laugh', icon: '😂', label: 'Laugh' },
    { id: 'gg', icon: '🎯', label: 'GG' },
  ];
  return (
    <div className="dc-drop absolute bottom-full left-0 mb-2 flex gap-1 p-1.5" style={{ minWidth: 'auto' }}>
      {reactions.map(r => (
        <button key={r.id} onClick={() => onPick(r.id)}
                className="w-9 h-9 rounded-lg hover:bg-white/8 grid place-items-center text-lg hover:scale-110 transition" title={r.label}>
          {r.icon}
        </button>
      ))}
    </div>
  );
}

function PostActions({ post, onAct }) {
  const [showReactions, setShowReactions] = useState(false);
  const [popping, setPopping] = useState(false);
  const hideTimer = useRef(null);
  const reacted = post.reacted;
  const reactionIcon = { fire: '🔥', gold: '👑', love: '❤️', wow: '🤯', laugh: '😂', gg: '🎯' };
  const authed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);

  const openPicker  = () => { clearTimeout(hideTimer.current); setShowReactions(true); };
  const closePicker = () => { hideTimer.current = setTimeout(() => setShowReactions(false), 200); };

  const handleLike = (e) => {
    e.stopPropagation();
    if (!authed) { window.location.href = '/account/login/?next=' + encodeURIComponent(window.location.pathname); return; }
    setPopping(true); setTimeout(() => setPopping(false), 400); onAct('like');
  };

  return (
    <div className="flex items-center justify-between mt-1 pt-3 border-t border-white/[.05]">
      <div className="flex items-center gap-1 relative">
        <div className="relative">
          <button
            className={`dc-react ${reacted ? (reacted === 'gold' ? 'is-on-gold' : reacted === 'love' ? 'is-on-rose' : 'is-on') : ''} ${popping ? 'dc-pop' : ''}`}
            onClick={handleLike} onMouseEnter={openPicker} onMouseLeave={closePicker}>
            {reacted ? <span className="text-base leading-none">{reactionIcon[reacted]}</span> : <i className="fa-regular fa-heart"></i>}
            <span className="dc-mono">{(post.likes || 0).toLocaleString()}</span>
          </button>
          {showReactions && (
            <div onMouseEnter={openPicker} onMouseLeave={closePicker}>
              <ReactionPicker onPick={(r) => { onAct('react', r); setShowReactions(false); }} />
            </div>
          )}
        </div>
        <button className="dc-react" onClick={() => onAct('comment')}>
          <i className="fa-regular fa-comment"></i><span className="dc-mono">{post.comments || 0}</span>
        </button>
        <button className="dc-react" onClick={() => onAct('share')}>
          <i className="fa-solid fa-retweet"></i><span className="dc-mono">{post.shares || 0}</span>
        </button>
      </div>
      <div className="flex items-center gap-1">
        <button className={`dc-react ${post.saved ? 'is-on-gold' : ''}`} onClick={() => onAct('save')}>
          <i className={post.saved ? 'fa-solid fa-bookmark' : 'fa-regular fa-bookmark'}></i>
        </button>
        <button className="dc-react" onClick={() => onAct('link')} title="Copy link">
          <i className="fa-solid fa-link"></i>
        </button>
      </div>
    </div>
  );
}

/* ---- Comments block ---- */
/* Per-comment item with like + reaction */
function CommentItem({ comment: c }) {
  const [liked, setLiked]     = useState(false);
  const [likes, setLikes]     = useState(c.likeCount || 0);
  const [reaction, setReaction] = useState(null);
  const [showPicker, setShowPicker] = useState(false);
  const hideTimer = useRef(null);
  const isAuthed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);
  const reactionIcon = { fire: '🔥', gold: '👑', love: '❤️', wow: '🤯', laugh: '😂', gg: '🎯' };
  const reactions = [
    { id: 'fire', icon: '🔥' }, { id: 'gold', icon: '👑' },
    { id: 'love', icon: '❤️' }, { id: 'wow', icon: '🤯' },
    { id: 'laugh', icon: '😂' }, { id: 'gg', icon: '🎯' },
  ];
  const openPicker  = () => { clearTimeout(hideTimer.current); setShowPicker(true); };
  const closePicker = () => { hideTimer.current = setTimeout(() => setShowPicker(false), 200); };

  const handleLike = () => {
    if (!isAuthed) {
      window.location.href = '/account/login/?next=' + encodeURIComponent(window.location.pathname);
      return;
    }
    if (liked) { setLiked(false); setLikes(l => Math.max(0, l - 1)); setReaction(null); }
    else        { setLiked(true); setLikes(l => l + 1); if (!reaction) setReaction('love'); }
  };

  const pickReaction = (r) => {
    if (!isAuthed) return;
    const wasLiked = liked;
    setReaction(r); setLiked(true);
    if (!wasLiked) setLikes(l => l + 1);
    setShowPicker(false);
  };

  return (
    <div className="flex gap-2.5 dc-fade-in">
      <div className="shrink-0 mt-0.5"><Avatar user={c.author} size={30} /></div>
      <div className="flex-1 min-w-0">
        <div className="bg-white/[.04] rounded-2xl px-3 py-2 border border-white/[.05]">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-[12px] font-semibold text-white">{c.author.name}</span>
            {c.author.verified && <VerifiedTick />}
            {c.ago && <span className="text-[10px] text-white/30">{c.ago}</span>}
          </div>
          <div className="text-[13px] text-white/80 leading-relaxed whitespace-pre-wrap">{c.body}</div>
        </div>
        {/* Reaction bar */}
        <div className="flex items-center gap-3 mt-1 ml-1 relative">
          <div className="relative">
            <button
              className={`flex items-center gap-1 text-[11px] font-semibold transition ${liked ? 'text-dc-rose' : 'text-white/40 hover:text-white/70'}`}
              onClick={handleLike}
              onMouseEnter={openPicker} onMouseLeave={closePicker}>
              {reaction
                ? <span className="text-sm leading-none">{reactionIcon[reaction]}</span>
                : <i className="fa-regular fa-heart text-[10px]"></i>}
              {likes > 0 && <span className="dc-mono">{likes}</span>}
            </button>
            {showPicker && (
              <div className="dc-drop absolute bottom-full left-0 mb-1.5 flex gap-0.5 p-1"
                   style={{ minWidth: 'auto' }}
                   onMouseEnter={openPicker} onMouseLeave={closePicker}>
                {reactions.map(r => (
                  <button key={r.id} onClick={() => pickReaction(r.id)}
                          className="w-8 h-8 rounded-lg hover:bg-white/10 grid place-items-center text-base hover:scale-110 transition">
                    {r.icon}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button className="text-[11px] text-white/40 hover:text-white/70 font-semibold transition">Reply</button>
        </div>
      </div>
    </div>
  );
}

function CommentsBlock({ post, comments, onAddComment, loading }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);
  const isAuthed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);
  const submit = () => { if (!text.trim()) return; onAddComment(text.trim()); setText(''); };
  const autoResize = (e) => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'; };
  return (
    <div className="mt-4 pt-4 border-t border-white/[.06] dc-fade-in">
      {isAuthed ? (
        <div className="flex gap-2.5 items-start mb-4">
          <div className="shrink-0 mt-0.5"><Avatar user={window.DC.ME} size={30} /></div>
          <div className="flex-1 rounded-2xl bg-white/[.04] border border-white/[.08] overflow-hidden focus-within:border-dc-cyan/40 focus-within:bg-white/[.06] transition-all duration-200">
            <textarea ref={textareaRef} value={text}
              onChange={e => { setText(e.target.value); autoResize(e); }}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } }}
              placeholder="Write a comment… (Enter to send)"
              rows={1}
              className="w-full bg-transparent text-[13px] text-white/90 placeholder:text-white/30 outline-none px-3 pt-2.5 pb-1 resize-none leading-relaxed" />
            {text.trim() && (
              <div className="flex items-center justify-between px-3 pb-2 pt-1">
                <span className="text-[10px] text-white/25 dc-mono">{text.length}/500</span>
                <button onClick={submit}
                        className="text-[11px] font-bold text-black px-3 py-1 rounded-lg transition flex items-center gap-1.5"
                        style={{ background: 'linear-gradient(135deg, var(--dc-accent), var(--dc-accent-2))' }}>
                  <i className="fa-solid fa-paper-plane text-[9px]"></i>Reply
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        <a href="/account/login/?next=/community/"
           className="flex items-center gap-2 text-[12px] text-white/40 hover:text-dc-cyan mb-4 transition">
          <i className="fa-solid fa-arrow-right-to-bracket text-[10px]"></i>
          Sign in to join the discussion
        </a>
      )}
      {loading && (
        <div className="flex items-center gap-2 text-[12px] text-white/35 py-2">
          <div className="w-4 h-4 rounded-full border-2 border-dc-cyan/30 border-t-dc-cyan animate-spin"></div>
          Loading…
        </div>
      )}
      {!loading && comments.length === 0 && (
        <p className="text-[12px] text-white/30 py-2">No comments yet. Be the first.</p>
      )}
      <div className="space-y-3">
        {comments.map(c => <CommentItem key={c.id} comment={c} />)}
      </div>
    </div>
  );
}

/* ---- PostCard base wrapper ---- */
function PostCard({ post, children, extraClass = '' }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState([]);
  const [commentsLoaded, setCommentsLoaded] = useState(false);
  const [loadingComments, setLoadingComments] = useState(false);
  const [localPost, setLocalPost] = useState(post);

  useEffect(() => { setLocalPost(post); }, [post.id, post.likes, post.comments, post.reacted, post.saved]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const close = () => setMenuOpen(false);
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [menuOpen]);

  const api = (window.DC && window.DC.api) || null;
  const authed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);

  const normComment = (c) => ({
    id: 'c' + c.id, author: {
      name: c.author.display_name || c.author.username || 'User',
      handle: c.author.username || '',
      color1: '#7B2BFF', color2: '#00E5FF',
      avatar_url: c.author.avatar_url || null, verified: false,
    },
    ago: '', body: c.content,
  });

  const handleAct = (action, arg) => {
    if (action === 'like') {
      if (!authed) { window.location.href = '/account/login/?next=' + encodeURIComponent(window.location.pathname); return; }
      const was = !!localPost.reacted;
      setLocalPost(p => ({ ...p, likes: was ? p.likes - 1 : p.likes + 1, reacted: was ? null : 'fire' }));
      if (api && api.toggleLike && localPost._pk) {
        api.toggleLike(localPost._pk).then(r => {
          if (typeof r.likes_count === 'number') setLocalPost(p => ({ ...p, likes: r.likes_count, reacted: r.liked ? (p.reacted || 'fire') : null }));
        }).catch(() => setLocalPost(p => ({ ...p, likes: was ? p.likes + 1 : p.likes - 1, reacted: was ? 'fire' : null })));
      }
    } else if (action === 'react') {
      if (!authed) return;
      const was = !!localPost.reacted;
      setLocalPost(p => ({ ...p, likes: was ? p.likes : p.likes + 1, reacted: arg }));
      if (api && api.toggleLike && localPost._pk && !was) api.toggleLike(localPost._pk).catch(() => {});
    } else if (action === 'save') {
      setLocalPost(p => ({ ...p, saved: !p.saved }));
    } else if (action === 'comment') {
      const next = !showComments;
      setShowComments(next);
      if (next && !commentsLoaded && api && api.listComments && localPost._pk) {
        setLoadingComments(true);
        api.listComments(localPost._pk).then(d => {
          setComments((d.comments || []).map(normComment));
          setCommentsLoaded(true);
        }).catch(() => setCommentsLoaded(true)).finally(() => setLoadingComments(false));
      }
    } else if (action === 'share') {
      setLocalPost(p => ({ ...p, shares: (p.shares || 0) + 1 }));
    } else if (action === 'link') {
      try { navigator.clipboard.writeText(window.location.origin + '/community/#post-' + (localPost._pk || localPost.id)); } catch(e) {}
    }
  };

  const handleAddComment = (text) => {
    if (!authed || !api || !api.addComment || !localPost._pk) return;
    const tempId = 'tmp' + Date.now();
    setComments(c => [...c, { id: tempId, author: window.DC.ME, ago: 'now', body: text }]);
    setLocalPost(p => ({ ...p, comments: (p.comments || 0) + 1 }));
    api.addComment(localPost._pk, text).then(r => {
      if (r && r.comment) setComments(c => c.map(x => x.id === tempId ? normComment(r.comment) : x));
      if (r && typeof r.comments_count === 'number') setLocalPost(p => ({ ...p, comments: r.comments_count }));
    }).catch(() => {
      setComments(c => c.filter(x => x.id !== tempId));
      setLocalPost(p => ({ ...p, comments: Math.max(0, (p.comments || 1) - 1) }));
    });
  };

  return (
    <article id={`post-${localPost._pk || localPost.id}`}
             className={`dc-card ${localPost.pinned ? 'is-pinned' : ''} ${extraClass} dc-card-pad dc-fade-in`}>
      <PostHeader post={localPost}
        menuOpen={menuOpen}
        onMenuToggle={(e) => { e.stopPropagation(); setMenuOpen(o => !o); }}
        closeMenu={() => setMenuOpen(false)} />
      <div className="mt-3">
        {typeof children === 'function' ? children(localPost) : children}
      </div>
      <PostActions post={localPost} onAct={handleAct} />
      {showComments && <CommentsBlock post={localPost} comments={comments} loading={loadingComments} onAddComment={handleAddComment} />}
    </article>
  );
}

/* ---- Card variants ---- */
function AnnouncementCard({ post }) {
  return (
    <PostCard post={post} extraClass="dc-announcement dc-scanlines">
      {(p) => (
        <>
          <div className="flex items-center gap-2 mb-2">
            <span className="dc-hud-label text-dc-gold flex items-center gap-1.5">
              <i className="fa-solid fa-bullhorn text-[10px]"></i><span>ANNOUNCEMENT</span>
            </span>
          </div>
          {p.title && <h3 className="font-display text-xl sm:text-2xl font-bold text-white leading-tight mb-2">{p.title}</h3>}
          {p.body && <PostBody html={p.body.indexOf('<') >= 0 ? p.body : null} plain={p.body.indexOf('<') < 0 ? p.body : null} />}
          {p.cta && (
            <button className="dc-btn-accent mt-4 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm">
              <i className={`fa-solid fa-${p.cta.icon}`}></i><span>{p.cta.label}</span>
              <i className="fa-solid fa-arrow-right text-xs"></i>
            </button>
          )}
        </>
      )}
    </PostCard>
  );
}

function EventCard({ post }) {
  const ev = post.event || {};
  const pct = ev.slots ? Math.round((ev.slots.taken / ev.slots.total) * 100) : 0;
  return (
    <PostCard post={post} extraClass="dc-tournament">
      {(p) => (
        <>
          <div className="flex items-center gap-2 mb-2">
            <span className="dc-hud-label text-dc-cyan flex items-center gap-1.5">
              <i className="fa-solid fa-trophy text-[10px]"></i><span>TOURNAMENT</span>
            </span>
            {ev.mode && <span className="dc-hud-label text-white/40">{ev.mode}</span>}
          </div>
          {p.title && <h3 className="font-display text-xl font-bold text-white leading-tight mb-1">{p.title}</h3>}
          {p.body && <p className="text-[14px] text-white/65 mb-4">{p.body}</p>}
          {ev.prize && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
              <div className="rounded-xl bg-white/[.03] border border-white/[.06] p-3">
                <div className="dc-hud-label text-white/35">Prize Pool</div>
                <div className="dc-counter-num text-lg text-dc-gold mt-1">{ev.prize}</div>
              </div>
              {ev.starts && <div className="rounded-xl bg-white/[.03] border border-white/[.06] p-3">
                <div className="dc-hud-label text-white/35">Starts</div>
                <div className="text-[12px] font-semibold text-white mt-1">{ev.starts}</div>
              </div>}
              {ev.format && <div className="rounded-xl bg-white/[.03] border border-white/[.06] p-3">
                <div className="dc-hud-label text-white/35">Format</div>
                <div className="text-[12px] font-semibold text-white mt-1">{ev.format}</div>
              </div>}
              {ev.slots && <div className="rounded-xl bg-white/[.03] border border-white/[.06] p-3">
                <div className="dc-hud-label text-white/35">Slots</div>
                <div className="dc-mono text-[13px] font-semibold text-white mt-1">
                  {ev.slots.taken}<span className="text-white/40">/{ev.slots.total}</span>
                </div>
                <div className="h-1 mt-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full" style={{ width: `${pct}%`, background: 'linear-gradient(90deg, var(--dc-accent), var(--dc-accent-2))' }}></div>
                </div>
              </div>}
            </div>
          )}
          <div className="flex items-center gap-2">
            <button className="dc-btn-accent flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm">
              <i className="fa-solid fa-arrow-right-to-bracket"></i> Register Team
            </button>
            <button className="dc-btn-ghost px-4 py-2.5 rounded-xl text-sm">
              <i className="fa-regular fa-eye mr-1.5"></i> View Bracket
            </button>
          </div>
        </>
      )}
    </PostCard>
  );
}

function TextCard({ post }) {
  return (
    <PostCard post={post}>
      {(p) => (
        <>
          {p.title && <h3 className="font-display text-lg font-semibold text-white leading-snug mb-1.5">{p.title}</h3>}
          {p.body && <PostBody html={p.body.indexOf('<') >= 0 ? p.body : null} plain={p.body.indexOf('<') < 0 ? p.body : null} />}
        </>
      )}
    </PostCard>
  );
}

function ImageCard({ post }) {
  return (
    <PostCard post={post}>
      {(p) => (
        <>
          {p.body && <div className="mb-3"><PostBody html={p.body.indexOf('<') >= 0 ? p.body : null} plain={p.body.indexOf('<') < 0 ? p.body : null} /></div>}
          <div className="rounded-xl overflow-hidden border border-white/[.06] relative bg-black/30">
            {p.image && p.image.url
              ? <img src={p.image.url} alt={p.image.alt || ''} className="w-full max-h-[640px] object-contain"
                     onError={(e) => { e.currentTarget.style.display = 'none'; }} />
              : p.image && (
                <div style={{ aspectRatio: '16/10', background: `linear-gradient(135deg, ${p.image.color1 || '#7B2BFF'}, ${p.image.color2 || '#00E5FF'})` }}>
                  <div className="absolute inset-0 opacity-25" style={{ background: 'repeating-linear-gradient(135deg, rgba(255,255,255,0.06) 0 16px, transparent 16px 32px)' }}></div>
                  {p.image.label && <div className="absolute top-3 left-3 px-2.5 py-1 rounded-md bg-black/50 backdrop-blur-sm text-[10px] font-bold tracking-widest text-white">{p.image.label}</div>}
                </div>
              )}
          </div>
        </>
      )}
    </PostCard>
  );
}

function ClipCard({ post }) {
  const [playing, setPlaying] = useState(false);
  return (
    <PostCard post={post}>
      {(p) => (
        <>
          {p.body && <div className="mb-3"><PostBody html={p.body.indexOf('<') >= 0 ? p.body : null} plain={p.body.indexOf('<') < 0 ? p.body : null} /></div>}
          <div className="relative rounded-xl overflow-hidden border border-white/[.06] cursor-pointer group bg-black"
               style={{ aspectRatio: '16 / 9', background: p.clip && p.clip.thumbColor1 ? `linear-gradient(135deg, ${p.clip.thumbColor1}, ${p.clip.thumbColor2})` : undefined }}
               onClick={() => setPlaying(true)}>
            {playing && p.clip && p.clip.url ? (
              <video src={p.clip.url} className="w-full h-full" controls autoPlay playsInline />
            ) : (
              <>
                {p.clip && p.clip.url && <video src={p.clip.url} className="w-full h-full object-cover opacity-80" preload="metadata" muted />}
                <div className="absolute inset-0 opacity-30" style={{ background: 'repeating-linear-gradient(45deg, rgba(255,255,255,0.05) 0 12px, transparent 12px 24px)' }}></div>
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/60"></div>
                {p.game && (
                  <div className="absolute top-3 left-3 flex items-center gap-2">
                    <GameHex game={p.game} size={26} />
                    {p.clip && p.clip.caption && <div className="text-[10px] font-bold text-white tracking-wide">{p.clip.caption}</div>}
                  </div>
                )}
                {p.clip && p.clip.duration && (
                  <div className="absolute top-3 right-3 px-2 py-0.5 rounded-md bg-black/60 backdrop-blur-sm text-[10px] font-bold dc-mono text-white">{p.clip.duration}</div>
                )}
                <button className="dc-play-btn absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" aria-label="Play">
                  <i className="fa-solid fa-play text-xl text-white ml-1"></i>
                </button>
                {p.clip && typeof p.clip.views === 'number' && (
                  <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-[11px] text-white/80 font-semibold">
                      <i className="fa-regular fa-eye"></i><span className="dc-mono">{p.clip.views.toLocaleString()}</span>
                    </div>
                    <div className="px-2 py-0.5 rounded-md bg-white/15 backdrop-blur-md text-[10px] font-bold text-white border border-white/20">HIGHLIGHT</div>
                  </div>
                )}
              </>
            )}
          </div>
        </>
      )}
    </PostCard>
  );
}

function PollCard({ post }) {
  const api = (window.DC && window.DC.api) || null;
  const authed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);
  const initState = post.poll_data || post.poll || { options: [], total: 0, my_vote: null, voted: null };
  const [pollState, setPollState] = useState(initState);
  const myVote = pollState.my_vote || pollState.voted;
  const winner = (pollState.options || []).length ? (pollState.options).reduce((a, b) => (a.votes || 0) > (b.votes || 0) ? a : b, pollState.options[0]) : null;

  const vote = (optId) => {
    if (myVote) return;
    if (!authed) { window.location.href = '/account/login/?next=/community/'; return; }
    const prev = pollState;
    setPollState(s => ({
      ...s, total: (s.total || 0) + 1, my_vote: optId, voted: optId,
      options: (s.options || []).map(o => o.id === optId ? { ...o, votes: (o.votes || 0) + 1 } : o),
    }));
    if (api && api.votePoll && post._pk) {
      api.votePoll(post._pk, optId).then(r => {
        if (r && r.poll_data) setPollState(r.poll_data);
      }).catch(() => setPollState(prev));
    }
  };

  return (
    <PostCard post={post}>
      {(p) => (
        <>
          <div className="flex items-center gap-2 mb-2">
            <span className="dc-hud-label flex items-center gap-1.5" style={{ color: 'var(--dc-accent-2)' }}>
              <i className="fa-solid fa-square-poll-vertical text-[10px]"></i><span>POLL</span>
            </span>
          </div>
          {p.title && <h3 className="text-base sm:text-lg font-semibold text-white leading-snug mb-3">{p.title}</h3>}
          {p.body && !p.title && <p className="text-[14px] text-white/75 mb-3">{p.body}</p>}
          <div className="space-y-2">
            {(pollState.options || []).map(o => {
              const total = pollState.total || 0;
              const pct = total > 0 ? Math.round(((o.votes || 0) / total) * 100) : 0;
              const isVoted = myVote === o.id;
              const isWinner = !!myVote && winner && o.id === winner.id;
              return (
                <div key={o.id} onClick={() => vote(o.id)}
                     className={`dc-poll-bar ${myVote ? 'is-voted' : 'cursor-pointer'} ${isWinner ? 'is-winner' : ''}`}>
                  <div className="dc-poll-fill" style={{ width: myVote ? `${pct}%` : '0%' }}></div>
                  <div className="flex items-center justify-between relative z-10">
                    <div className="flex items-center gap-2">
                      {isVoted && <i className="fa-solid fa-circle-check text-xs" style={{ color: 'var(--dc-accent)' }}></i>}
                      <span className={`text-sm ${isVoted ? 'font-bold text-white' : 'text-white/80'}`}>{o.label}</span>
                      {isWinner && !!myVote && <span className="dc-hud-label text-[8px] ml-1" style={{ color: 'var(--dc-gold)' }}>LEADING</span>}
                    </div>
                    {!!myVote && <span className="dc-mono text-sm font-bold text-white/70">{pct}%</span>}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex items-center justify-between text-[12px] text-white/40">
            <span className="dc-mono"><i className="fa-solid fa-users text-[9px] mr-1"></i>{(pollState.total || 0).toLocaleString()} votes</span>
            <span style={{ color: 'var(--dc-accent)' }}>{!myVote ? 'Tap to vote' : 'Voted'}</span>
          </div>
        </>
      )}
    </PostCard>
  );
}

function InfoCell({ label, value, accent, mono }) {
  return (
    <div className="rounded-xl bg-white/[.03] border border-white/[.05] p-2.5">
      <div className="dc-hud-label text-white/35 mb-0.5">{label}</div>
      <div className={`text-[12px] font-semibold leading-snug ${accent ? 'text-dc-cyan' : 'text-white'} ${mono ? 'dc-mono' : ''}`}>{value}</div>
    </div>
  );
}

function LftCard({ post }) {
  const lft = post.lft_data || post.lft || {};
  const roles = Array.isArray(lft.roles) ? lft.roles : (lft.roles ? [lft.roles] : []);
  return (
    <PostCard post={post} extraClass="dc-lft">
      {(p) => (
        <>
          <div className="flex items-center gap-2 mb-2">
            <span className="dc-hud-label text-dc-emerald flex items-center gap-1.5">
              <i className="fa-solid fa-signal text-[10px]"></i><span>LOOKING FOR TEAM</span>
            </span>
            {p.game && <GameHex game={p.game} size={24} />}
          </div>
          {(p.title || p.body) && (
            <p className="text-[14.5px] text-white/85 mb-3">
              {p.title || ''}
              {p.body && !p.title && <PostBody html={p.body.indexOf('<') >= 0 ? p.body : null} plain={p.body.indexOf('<') < 0 ? p.body : null} />}
            </p>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {roles.length > 0 && <InfoCell label="Roles" value={roles.join(', ')} />}
            {lft.rank && <InfoCell label="Rank" value={lft.rank} accent />}
            {lft.hours && <InfoCell label="Hours" value={lft.hours} mono />}
            {lft.region && <InfoCell label="Region" value={lft.region} />}
          </div>
          {lft.availability && <div className="text-[12px] text-white/50 mt-2.5"><i className="fa-regular fa-clock mr-1.5"></i>{lft.availability}</div>}
          <div className="flex items-center gap-2 mt-3">
            <button className="dc-btn-accent inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm">
              <i className="fa-solid fa-envelope text-xs"></i> Invite to Team
            </button>
            <a href={p.author.profile_url || '#'} className="dc-btn-ghost px-4 py-2 rounded-xl text-sm inline-flex items-center gap-1.5">
              <i className="fa-regular fa-user"></i> Profile
            </a>
          </div>
        </>
      )}
    </PostCard>
  );
}

function RecruitCard({ post }) {
  const lft = post.lft_data || post.recruit || {};
  const team = post.team;
  const roles = Array.isArray(lft.roles) ? lft.roles : (lft.roles ? [lft.roles] : []);
  const perks = Array.isArray(lft.perks) ? lft.perks : (lft.perks ? [lft.perks] : []);
  return (
    <PostCard post={post} extraClass="dc-recruit">
      {(p) => (
        <>
          <div className="flex items-center gap-2 mb-2">
            <span className="dc-hud-label flex items-center gap-1.5" style={{ color: 'var(--dc-accent-2)' }}>
              <i className="fa-solid fa-user-plus text-[10px]"></i><span>RECRUITING</span>
            </span>
            {p.game && <GameHex game={p.game} size={24} />}
            {team && <span className="dc-hud-label text-white/40 text-[9px]">{team.tag || team.name}</span>}
          </div>
          {team && (
            <div className="flex items-center gap-2 mb-2">
              <div className="w-7 h-7 rounded-lg overflow-hidden ring-1 ring-white/10 bg-white/5 grid place-items-center text-[8px] font-bold text-white/50">
                {team.logo_url ? <img src={team.logo_url} alt={team.name} className="w-full h-full object-cover" /> : <span>{(team.tag || team.name || '?').slice(0, 3)}</span>}
              </div>
              <span className="text-sm font-semibold text-white">{team.name}</span>
            </div>
          )}
          {roles.length > 0 && (
            <p className="text-[14.5px] text-white/85 mb-3">
              {team ? <strong>{team.name}</strong> : 'Team'} is looking for:{' '}
              <span className="text-dc-cyan font-semibold">{roles.join(' · ')}</span>
            </p>
          )}
          {(p.title || p.body) && !roles.length && (
            <div className="mb-3"><PostBody html={p.body && p.body.indexOf('<') >= 0 ? p.body : null} plain={p.body && p.body.indexOf('<') < 0 ? p.body : null} /></div>
          )}
          {(lft.rank || lft.commitment) && (
            <div className="grid grid-cols-2 gap-2 mb-3">
              {lft.rank && <InfoCell label="Requirement" value={lft.rank} accent />}
              {lft.commitment && <InfoCell label="Commitment" value={lft.commitment} />}
            </div>
          )}
          {perks.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {perks.map(pk => (
                <span key={pk} className="dc-chip"><i className="fa-solid fa-check text-[8px]"></i>{pk}</span>
              ))}
            </div>
          )}
          <div className="flex items-center gap-2">
            <button className="dc-btn-accent inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm">
              <i className="fa-solid fa-paper-plane text-xs"></i> Apply Now
            </button>
            {team && (
              <a href={`/teams/${team.slug || ''}/`} className="dc-btn-ghost px-4 py-2 rounded-xl text-sm inline-flex items-center gap-1.5">
                <i className="fa-solid fa-users"></i> View Team
              </a>
            )}
          </div>
        </>
      )}
    </PostCard>
  );
}

function AchievementCard({ post }) {
  const ach = post.achievement || {};
  return (
    <PostCard post={post}>
      {(p) => (
        <div className="flex items-center gap-4 p-2 rounded-xl">
          <div className="w-14 h-14 rounded-2xl grid place-items-center text-2xl shrink-0"
               style={{ background: `linear-gradient(135deg, ${ach.color1 || '#FFD166'}, ${ach.color2 || '#FF4D6D'})` }}>
            <i className={`fa-solid fa-${ach.icon || 'trophy'} text-black`}></i>
          </div>
          <div className="flex-1 min-w-0">
            <div className="dc-hud-label text-dc-gold mb-0.5">
              <i className="fa-solid fa-medal text-[10px] mr-1"></i> ACHIEVEMENT UNLOCKED
            </div>
            <div className="font-display text-base font-bold text-white">{ach.title || p.title}</div>
            <div className="text-[12px] text-white/50 mt-0.5">{ach.sub || p.body}</div>
          </div>
          {p.game && <GameHex game={p.game} size={32} />}
        </div>
      )}
    </PostCard>
  );
}

function PostDispatcher({ post }) {
  switch (post.type) {
    case 'announcement': return <AnnouncementCard post={post} />;
    case 'event':        return <EventCard post={post} />;
    case 'clip':         return <ClipCard post={post} />;
    case 'poll':         return <PollCard post={post} />;
    case 'lft':          return <LftCard post={post} />;
    case 'recruit':      return <RecruitCard post={post} />;
    case 'image':        return <ImageCard post={post} />;
    case 'achievement':  return <AchievementCard post={post} />;
    case 'text':
    default:             return <TextCard post={post} />;
  }
}

Object.assign(window, {
  Avatar, GameHex, VerifiedTick, StaffBadge,
  PostHeader, PostActions, CommentsBlock, PostCard, PostDispatcher,
  PollCard, LftCard, RecruitCard,
});
})();
