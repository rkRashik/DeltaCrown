/* DeltaCrown Community — post card variants. */
(function () {
  const {
    useState,
    useRef,
    useEffect
  } = React;
  function initialsOf(name) {
    return (name || '').split(/\s+/).filter(Boolean).map(p => p[0]).slice(0, 2).join('').toUpperCase();
  }

  /* Strip inline Tailwind CSS variable styles and paste artifacts from user HTML */
  function sanitizeHTML(raw) {
    if (!raw) return '';
    const div = document.createElement('div');
    div.innerHTML = raw.replace(/<!--(Start|End)Fragment-->/gi, '').replace(/\s*style="[^"]*"/gi, '').replace(/\s*class="[^"]*"/gi, '');
    return div.innerHTML.trim();
  }
  function PostBody({
    html,
    plain
  }) {
    const [expanded, setExpanded] = useState(false);
    const content = html || plain || '';
    const isHTML = content.indexOf('<') >= 0;
    const cleaned = isHTML ? sanitizeHTML(content) : content;
    const isLong = cleaned.length > 600;
    const visible = isLong && !expanded ? cleaned.slice(0, 600) + '…' : cleaned;
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-post-body"
    }, isHTML ? /*#__PURE__*/React.createElement("div", {
      dangerouslySetInnerHTML: {
        __html: visible
      }
    }) : /*#__PURE__*/React.createElement("p", {
      className: "whitespace-pre-wrap"
    }, visible), isLong && !expanded && /*#__PURE__*/React.createElement("button", {
      onClick: () => setExpanded(true),
      className: "text-xs mt-1 hover:underline",
      style: {
        color: 'var(--dc-accent)'
      }
    }, "Read more"));
  }
  function Avatar({
    user,
    size = 40,
    square = false
  }) {
    if (!user) user = {
      name: '?',
      color1: '#7B2BFF',
      color2: '#00E5FF'
    };
    const s = {
      width: size,
      height: size
    };
    const hasImg = !!user.avatar_url;
    const inner = hasImg ? /*#__PURE__*/React.createElement("img", {
      src: user.avatar_url,
      alt: user.name || '',
      className: "w-full h-full object-cover",
      style: {
        borderRadius: square ? 11 : '50%'
      },
      onError: e => {
        e.currentTarget.style.display = 'none';
      }
    }) : /*#__PURE__*/React.createElement("div", {
      className: "dc-avatar-ph w-full h-full text-sm",
      style: {
        '--c1': user.color1 || '#7B2BFF',
        '--c2': user.color2 || '#00E5FF'
      }
    }, initialsOf(user.name));
    if (square) return /*#__PURE__*/React.createElement("div", {
      className: "dc-avatar-sq",
      style: s
    }, inner);
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-avatar",
      style: s
    }, inner);
  }
  function GameHex({
    game,
    size = 28
  }) {
    if (!game || !game.logo) return null;
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-hex",
      style: {
        '--size': `${size}px`
      },
      title: game.name
    }, /*#__PURE__*/React.createElement("img", {
      src: game.logo,
      alt: game.name,
      onError: e => {
        e.currentTarget.parentElement.style.display = 'none';
      }
    }));
  }
  function VerifiedTick() {
    return /*#__PURE__*/React.createElement("span", {
      className: "inline-grid place-items-center w-4 h-4 rounded-full bg-dc-cyan ml-1",
      title: "Verified"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-check text-[8px] text-black"
    }));
  }
  function StaffBadge() {
    return /*#__PURE__*/React.createElement("span", {
      className: "inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md ml-1.5",
      style: {
        background: 'rgba(255,209,102,0.12)',
        border: '1px solid rgba(255,209,102,0.3)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-shield-halved text-[9px] text-dc-gold"
    }), /*#__PURE__*/React.createElement("span", {
      className: "text-[9px] font-bold tracking-wider text-dc-gold"
    }, "STAFF"));
  }

  /* ---- 3-dot post menu ---- */
  function PostMenu({
    post,
    onClose,
    isOwn
  }) {
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-post-menu",
      onClick: e => e.stopPropagation()
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-post-menu-label"
    }, "Post options"), /*#__PURE__*/React.createElement("button", {
      className: "dc-post-menu-item",
      onClick: onClose
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-bookmark"
    }), " Save post"), /*#__PURE__*/React.createElement("button", {
      className: "dc-post-menu-item",
      onClick: onClose
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-link"
    }), " Copy link"), /*#__PURE__*/React.createElement("button", {
      className: "dc-post-menu-item",
      onClick: () => {
        try {
          navigator.clipboard.writeText(window.location.origin + '/community/#post-' + post.id);
        } catch (e) {}
        onClose();
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-share-nodes"
    }), " Share"), /*#__PURE__*/React.createElement("div", {
      className: "dc-post-menu-sep"
    }), /*#__PURE__*/React.createElement("button", {
      className: "dc-post-menu-item",
      onClick: onClose
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-flag"
    }), " Report"), /*#__PURE__*/React.createElement("button", {
      className: "dc-post-menu-item",
      onClick: onClose
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-eye-slash"
    }), " Not interested"), isOwn && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "dc-post-menu-sep"
    }), /*#__PURE__*/React.createElement("button", {
      className: "dc-post-menu-item is-danger",
      onClick: () => {
        const api = window.DC && window.DC.api;
        if (api && api.fetchJSON && window.DC.api.urls) {
          const url = (window.DC.api.urls.like || '').replace(/\/0\/like\/$/, '/' + post._pk + '/delete/');
          api.fetchJSON && api.fetchJSON(url, {
            method: 'POST',
            headers: api.headersJSON()
          }).catch(() => {});
        }
        onClose();
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-trash-can"
    }), " Delete post")));
  }
  function PostHeader({
    post,
    onMenuToggle,
    menuOpen,
    closeMenu
  }) {
    const u = post.author;
    const isOwn = window.DC_CONFIG && window.DC_CONFIG.isAuthenticated && window.DC.ME && window.DC.ME.handle === u.handle;
    return /*#__PURE__*/React.createElement("div", {
      className: "flex items-start gap-3"
    }, /*#__PURE__*/React.createElement(Avatar, {
      user: u,
      size: 42
    }), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center flex-wrap gap-x-1 gap-y-0.5"
    }, /*#__PURE__*/React.createElement("span", {
      className: "font-semibold text-white truncate"
    }, u.name), u.verified && /*#__PURE__*/React.createElement(VerifiedTick, null), u.isStaff && /*#__PURE__*/React.createElement(StaffBadge, null), post.team && post.team.name && /*#__PURE__*/React.createElement("span", {
      className: "text-[11px] text-white/40 ml-1"
    }, "\xB7 ", post.team.name)), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 text-[11px] text-white/35 mt-0.5"
    }, /*#__PURE__*/React.createElement("span", null, "@", u.handle), /*#__PURE__*/React.createElement("span", {
      className: "w-0.5 h-0.5 rounded-full bg-white/30"
    }), /*#__PURE__*/React.createElement("span", null, post.ago, " ago"), post.game && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
      className: "w-0.5 h-0.5 rounded-full bg-white/30"
    }), /*#__PURE__*/React.createElement("span", {
      className: "flex items-center gap-1"
    }, post.game.logo && /*#__PURE__*/React.createElement("span", {
      className: "w-3 h-3 rounded-sm overflow-hidden"
    }, /*#__PURE__*/React.createElement("img", {
      src: post.game.logo,
      className: "w-full h-full object-cover",
      alt: ""
    })), post.game.name)), post.tournament && /*#__PURE__*/React.createElement("span", {
      className: "dc-source-badge ml-1"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-trophy"
    }), post.tournament.name))), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1 -mr-1 relative"
    }, post.pinned && /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-dc-gold flex items-center gap-1 mr-1"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-thumbtack text-[10px]"
    }), /*#__PURE__*/React.createElement("span", null, "PINNED")), /*#__PURE__*/React.createElement("button", {
      className: "w-8 h-8 rounded-lg hover:bg-white/5 text-white/35 hover:text-white",
      onClick: onMenuToggle,
      "aria-label": "More"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-ellipsis"
    })), menuOpen && /*#__PURE__*/React.createElement(PostMenu, {
      post: post,
      isOwn: isOwn,
      onClose: closeMenu
    })));
  }

  /* ---- Reactions ---- */
  function ReactionPicker({
    onPick
  }) {
    const reactions = [{
      id: 'fire',
      icon: '🔥',
      label: 'Fire'
    }, {
      id: 'gold',
      icon: '👑',
      label: 'Crown'
    }, {
      id: 'love',
      icon: '❤️',
      label: 'Love'
    }, {
      id: 'wow',
      icon: '🤯',
      label: 'Mind blown'
    }, {
      id: 'laugh',
      icon: '😂',
      label: 'Laugh'
    }, {
      id: 'gg',
      icon: '🎯',
      label: 'GG'
    }];
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-drop absolute bottom-full left-0 mb-2 flex gap-1 p-1.5",
      style: {
        minWidth: 'auto'
      }
    }, reactions.map(r => /*#__PURE__*/React.createElement("button", {
      key: r.id,
      onClick: () => onPick(r.id),
      className: "w-9 h-9 rounded-lg hover:bg-white/8 grid place-items-center text-lg hover:scale-110 transition",
      title: r.label
    }, r.icon)));
  }
  function PostActions({
    post,
    onAct
  }) {
    const [showReactions, setShowReactions] = useState(false);
    const [popping, setPopping] = useState(false);
    const hideTimer = useRef(null);
    const reacted = post.reacted;
    const reactionIcon = {
      fire: '🔥',
      gold: '👑',
      love: '❤️',
      wow: '🤯',
      laugh: '😂',
      gg: '🎯'
    };
    const authed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);
    const openPicker = () => {
      clearTimeout(hideTimer.current);
      setShowReactions(true);
    };
    const closePicker = () => {
      hideTimer.current = setTimeout(() => setShowReactions(false), 200);
    };
    const handleLike = e => {
      e.stopPropagation();
      if (!authed) {
        window.location.href = '/account/login/?next=' + encodeURIComponent(window.location.pathname);
        return;
      }
      setPopping(true);
      setTimeout(() => setPopping(false), 400);
      onAct('like');
    };
    return /*#__PURE__*/React.createElement("div", {
      className: "flex items-center justify-between mt-1 pt-3 border-t border-white/[.05]"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1 relative"
    }, /*#__PURE__*/React.createElement("div", {
      className: "relative"
    }, /*#__PURE__*/React.createElement("button", {
      className: `dc-react ${reacted ? reacted === 'gold' ? 'is-on-gold' : reacted === 'love' ? 'is-on-rose' : 'is-on' : ''} ${popping ? 'dc-pop' : ''}`,
      onClick: handleLike,
      onMouseEnter: openPicker,
      onMouseLeave: closePicker
    }, reacted ? /*#__PURE__*/React.createElement("span", {
      className: "text-base leading-none"
    }, reactionIcon[reacted]) : /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-heart"
    }), /*#__PURE__*/React.createElement("span", {
      className: "dc-mono"
    }, (post.likes || 0).toLocaleString())), showReactions && /*#__PURE__*/React.createElement("div", {
      onMouseEnter: openPicker,
      onMouseLeave: closePicker
    }, /*#__PURE__*/React.createElement(ReactionPicker, {
      onPick: r => {
        onAct('react', r);
        setShowReactions(false);
      }
    }))), /*#__PURE__*/React.createElement("button", {
      className: "dc-react",
      onClick: () => onAct('comment')
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-comment"
    }), /*#__PURE__*/React.createElement("span", {
      className: "dc-mono"
    }, post.comments || 0)), /*#__PURE__*/React.createElement("button", {
      className: "dc-react",
      onClick: () => onAct('share')
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-retweet"
    }), /*#__PURE__*/React.createElement("span", {
      className: "dc-mono"
    }, post.shares || 0))), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1"
    }, /*#__PURE__*/React.createElement("button", {
      className: `dc-react ${post.saved ? 'is-on-gold' : ''}`,
      onClick: () => onAct('save')
    }, /*#__PURE__*/React.createElement("i", {
      className: post.saved ? 'fa-solid fa-bookmark' : 'fa-regular fa-bookmark'
    })), /*#__PURE__*/React.createElement("button", {
      className: "dc-react",
      onClick: () => onAct('link'),
      title: "Copy link"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-link"
    }))));
  }

  /* ---- Comments block ---- */
  /* Per-comment item with like + reaction */
  function CommentItem({
    comment: c,
    onReply
  }) {
    const [liked, setLiked] = useState(false);
    const [likes, setLikes] = useState(c.likeCount || 0);
    const [reaction, setReaction] = useState(null);
    const [showPicker, setShowPicker] = useState(false);
    const [showReply, setShowReply] = useState(false);
    const [replyText, setReplyText] = useState('');
    const hideTimer = useRef(null);
    const isAuthed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);
    const reactionIcon = {
      fire: '🔥',
      gold: '👑',
      love: '❤️',
      wow: '🤯',
      laugh: '😂',
      gg: '🎯'
    };
    const reactions = [{
      id: 'fire',
      icon: '🔥'
    }, {
      id: 'gold',
      icon: '👑'
    }, {
      id: 'love',
      icon: '❤️'
    }, {
      id: 'wow',
      icon: '🤯'
    }, {
      id: 'laugh',
      icon: '😂'
    }, {
      id: 'gg',
      icon: '🎯'
    }];
    const openPicker = () => {
      clearTimeout(hideTimer.current);
      setShowPicker(true);
    };
    const closePicker = () => {
      hideTimer.current = setTimeout(() => setShowPicker(false), 200);
    };
    const handleLike = () => {
      if (!isAuthed) {
        window.location.href = '/account/login/?next=' + encodeURIComponent(window.location.pathname);
        return;
      }
      if (liked) {
        setLiked(false);
        setLikes(l => Math.max(0, l - 1));
        setReaction(null);
      } else {
        setLiked(true);
        setLikes(l => l + 1);
        if (!reaction) setReaction('love');
      }
    };
    const pickReaction = r => {
      if (!isAuthed) return;
      const wasLiked = liked;
      setReaction(r);
      setLiked(true);
      if (!wasLiked) setLikes(l => l + 1);
      setShowPicker(false);
    };
    return /*#__PURE__*/React.createElement("div", {
      className: "flex gap-2.5 dc-fade-in"
    }, /*#__PURE__*/React.createElement("div", {
      className: "shrink-0 mt-0.5"
    }, /*#__PURE__*/React.createElement(Avatar, {
      user: c.author,
      size: 30
    })), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "bg-white/[.04] rounded-2xl px-3 py-2 border border-white/[.05]"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1.5 mb-0.5"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-[12px] font-semibold text-white"
    }, c.author.name), c.author.verified && /*#__PURE__*/React.createElement(VerifiedTick, null), c.ago && /*#__PURE__*/React.createElement("span", {
      className: "text-[10px] text-white/30"
    }, c.ago)), /*#__PURE__*/React.createElement("div", {
      className: "text-[13px] text-white/80 leading-relaxed whitespace-pre-wrap"
    }, c.body)), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-3 mt-1 ml-1 relative"
    }, /*#__PURE__*/React.createElement("div", {
      className: "relative"
    }, /*#__PURE__*/React.createElement("button", {
      className: `flex items-center gap-1 text-[11px] font-semibold transition ${liked ? 'text-dc-rose' : 'text-white/40 hover:text-white/70'}`,
      onClick: handleLike,
      onMouseEnter: openPicker,
      onMouseLeave: closePicker
    }, reaction ? /*#__PURE__*/React.createElement("span", {
      className: "text-sm leading-none"
    }, reactionIcon[reaction]) : /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-heart text-[10px]"
    }), likes > 0 && /*#__PURE__*/React.createElement("span", {
      className: "dc-mono"
    }, likes)), showPicker && /*#__PURE__*/React.createElement("div", {
      className: "dc-drop absolute bottom-full left-0 mb-1.5 flex gap-0.5 p-1",
      style: {
        minWidth: 'auto'
      },
      onMouseEnter: openPicker,
      onMouseLeave: closePicker
    }, reactions.map(r => /*#__PURE__*/React.createElement("button", {
      key: r.id,
      onClick: () => pickReaction(r.id),
      className: "w-8 h-8 rounded-lg hover:bg-white/10 grid place-items-center text-base hover:scale-110 transition"
    }, r.icon)))), /*#__PURE__*/React.createElement("button", {
      className: "text-[11px] text-white/40 hover:text-dc-cyan font-semibold transition",
      onClick: () => setShowReply(r => !r)
    }, "Reply")), showReply && /*#__PURE__*/React.createElement("div", {
      className: "flex gap-2 mt-2 ml-1 dc-fade-in"
    }, /*#__PURE__*/React.createElement("div", {
      className: "shrink-0 mt-0.5"
    }, window.DC.ME ? /*#__PURE__*/React.createElement(Avatar, {
      user: window.DC.ME,
      size: 24
    }) : null), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 bg-white/[.04] border border-white/[.07] rounded-2xl px-3 py-1.5 flex items-center gap-2 focus-within:border-dc-cyan/40 transition"
    }, /*#__PURE__*/React.createElement("input", {
      autoFocus: true,
      value: replyText,
      onChange: e => setReplyText(e.target.value),
      onKeyDown: e => {
        if (e.key === 'Enter' && replyText.trim()) {
          /* Post as comment with @mention prefix */
          const text = `@${c.author.name} ${replyText.trim()}`;
          if (typeof onReply === 'function') onReply(text);
          setReplyText('');
          setShowReply(false);
        }
        if (e.key === 'Escape') {
          setShowReply(false);
          setReplyText('');
        }
      },
      placeholder: `Reply to @${c.author.name}…`,
      className: "flex-1 bg-transparent text-[12.5px] text-white/90 placeholder:text-white/30 outline-none min-w-0"
    }), replyText.trim() && /*#__PURE__*/React.createElement("button", {
      onClick: () => {
        if (replyText.trim()) {
          const text = `@${c.author.name} ${replyText.trim()}`;
          if (typeof onReply === 'function') onReply(text);
          setReplyText('');
          setShowReply(false);
        }
      },
      className: "text-[11px] font-bold text-black px-2.5 py-1 rounded-lg flex-shrink-0",
      style: {
        background: 'linear-gradient(135deg, var(--dc-accent), var(--dc-accent-2))'
      }
    }, "Reply")))));
  }
  function CommentsBlock({
    post,
    comments,
    onAddComment,
    loading
  }) {
    const [text, setText] = useState('');
    const textareaRef = useRef(null);
    const isAuthed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);
    const submit = () => {
      if (!text.trim()) return;
      onAddComment(text.trim());
      setText('');
    };
    const autoResize = e => {
      e.target.style.height = 'auto';
      e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
    };
    return /*#__PURE__*/React.createElement("div", {
      className: "mt-4 pt-4 border-t border-white/[.06] dc-fade-in"
    }, isAuthed ? /*#__PURE__*/React.createElement("div", {
      className: "flex gap-2.5 items-start mb-4"
    }, /*#__PURE__*/React.createElement("div", {
      className: "shrink-0 mt-0.5"
    }, /*#__PURE__*/React.createElement(Avatar, {
      user: window.DC.ME,
      size: 30
    })), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 rounded-2xl bg-white/[.04] border border-white/[.08] overflow-hidden focus-within:border-dc-cyan/40 focus-within:bg-white/[.06] transition-all duration-200"
    }, /*#__PURE__*/React.createElement("textarea", {
      ref: textareaRef,
      value: text,
      onChange: e => {
        setText(e.target.value);
        autoResize(e);
      },
      onKeyDown: e => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          submit();
        }
      },
      placeholder: "Write a comment\u2026 (Enter to send)",
      rows: 1,
      className: "w-full bg-transparent text-[13px] text-white/90 placeholder:text-white/30 outline-none px-3 pt-2.5 pb-1 resize-none leading-relaxed"
    }), text.trim() && /*#__PURE__*/React.createElement("div", {
      className: "flex items-center justify-between px-3 pb-2 pt-1"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-[10px] text-white/25 dc-mono"
    }, text.length, "/500"), /*#__PURE__*/React.createElement("button", {
      onClick: submit,
      className: "text-[11px] font-bold text-black px-3 py-1 rounded-lg transition flex items-center gap-1.5",
      style: {
        background: 'linear-gradient(135deg, var(--dc-accent), var(--dc-accent-2))'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-paper-plane text-[9px]"
    }), "Reply")))) : /*#__PURE__*/React.createElement("a", {
      href: "/account/login/?next=/community/",
      className: "flex items-center gap-2 text-[12px] text-white/40 hover:text-dc-cyan mb-4 transition"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-arrow-right-to-bracket text-[10px]"
    }), "Sign in to join the discussion"), loading && /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 text-[12px] text-white/35 py-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-4 h-4 rounded-full border-2 border-dc-cyan/30 border-t-dc-cyan animate-spin"
    }), "Loading\u2026"), !loading && comments.length === 0 && /*#__PURE__*/React.createElement("p", {
      className: "text-[12px] text-white/30 py-2"
    }, "No comments yet. Be the first."), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3"
    }, comments.map(c => /*#__PURE__*/React.createElement(CommentItem, {
      key: c.id,
      comment: c,
      onReply: onAddComment
    }))));
  }

  /* ---- PostCard base wrapper ---- */
  function PostCard({
    post,
    children,
    extraClass = ''
  }) {
    const [menuOpen, setMenuOpen] = useState(false);
    const [showComments, setShowComments] = useState(false);
    const [comments, setComments] = useState([]);
    const [commentsLoaded, setCommentsLoaded] = useState(false);
    const [loadingComments, setLoadingComments] = useState(false);
    const [localPost, setLocalPost] = useState(post);

    /* Sync from prop on new post (id change) or server-updated comment count.
       Intentionally NOT syncing post.likes/reacted — toggling optimistically via
       handleAct + server confirmation is authoritative; polling would overwrite it. */
    useEffect(() => {
      setLocalPost(post);
    }, [post.id, post.comments]);
    useEffect(() => {
      if (!menuOpen) return undefined;
      const close = () => setMenuOpen(false);
      document.addEventListener('click', close);
      return () => document.removeEventListener('click', close);
    }, [menuOpen]);
    const api = window.DC && window.DC.api || null;
    const authed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);
    const normComment = c => ({
      id: 'c' + c.id,
      author: {
        name: c.author.display_name || c.author.username || 'User',
        handle: c.author.username || '',
        color1: '#7B2BFF',
        color2: '#00E5FF',
        avatar_url: c.author.avatar_url || null,
        verified: false
      },
      ago: '',
      body: c.content
    });
    const handleAct = (action, arg) => {
      if (action === 'like') {
        if (!authed) {
          window.location.href = '/account/login/?next=' + encodeURIComponent(window.location.pathname);
          return;
        }
        const was = !!localPost.reacted;
        setLocalPost(p => ({
          ...p,
          likes: was ? p.likes - 1 : p.likes + 1,
          reacted: was ? null : 'fire'
        }));
        if (api && api.toggleLike && localPost._pk) {
          api.toggleLike(localPost._pk).then(r => {
            if (typeof r.likes_count === 'number') setLocalPost(p => ({
              ...p,
              likes: r.likes_count,
              reacted: r.liked ? p.reacted || 'fire' : null
            }));
          }).catch(() => setLocalPost(p => ({
            ...p,
            likes: was ? p.likes + 1 : p.likes - 1,
            reacted: was ? 'fire' : null
          })));
        }
      } else if (action === 'react') {
        if (!authed) return;
        const was = !!localPost.reacted;
        setLocalPost(p => ({
          ...p,
          likes: was ? p.likes : p.likes + 1,
          reacted: arg
        }));
        if (api && api.toggleLike && localPost._pk && !was) api.toggleLike(localPost._pk).catch(() => {});
      } else if (action === 'save') {
        setLocalPost(p => ({
          ...p,
          saved: !p.saved
        }));
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
        setLocalPost(p => ({
          ...p,
          shares: (p.shares || 0) + 1
        }));
      } else if (action === 'link') {
        try {
          navigator.clipboard.writeText(window.location.origin + '/community/#post-' + (localPost._pk || localPost.id));
        } catch (e) {}
      }
    };
    const handleAddComment = text => {
      if (!authed || !api || !api.addComment || !localPost._pk) return;
      const tempId = 'tmp' + Date.now();
      setComments(c => [...c, {
        id: tempId,
        author: window.DC.ME,
        ago: 'now',
        body: text
      }]);
      setLocalPost(p => ({
        ...p,
        comments: (p.comments || 0) + 1
      }));
      api.addComment(localPost._pk, text).then(r => {
        if (r && r.comment) setComments(c => c.map(x => x.id === tempId ? normComment(r.comment) : x));
        if (r && typeof r.comments_count === 'number') setLocalPost(p => ({
          ...p,
          comments: r.comments_count
        }));
      }).catch(() => {
        setComments(c => c.filter(x => x.id !== tempId));
        setLocalPost(p => ({
          ...p,
          comments: Math.max(0, (p.comments || 1) - 1)
        }));
      });
    };
    return /*#__PURE__*/React.createElement("article", {
      id: `post-${localPost._pk || localPost.id}`,
      className: `dc-card ${localPost.pinned ? 'is-pinned' : ''} ${extraClass} dc-card-pad dc-fade-in`
    }, /*#__PURE__*/React.createElement(PostHeader, {
      post: localPost,
      menuOpen: menuOpen,
      onMenuToggle: e => {
        e.stopPropagation();
        setMenuOpen(o => !o);
      },
      closeMenu: () => setMenuOpen(false)
    }), /*#__PURE__*/React.createElement("div", {
      className: "mt-3"
    }, typeof children === 'function' ? children(localPost) : children), /*#__PURE__*/React.createElement(PostActions, {
      post: localPost,
      onAct: handleAct
    }), showComments && /*#__PURE__*/React.createElement(CommentsBlock, {
      post: localPost,
      comments: comments,
      loading: loadingComments,
      onAddComment: handleAddComment
    }));
  }

  /* ---- Card variants ---- */
  function AnnouncementCard({
    post
  }) {
    return /*#__PURE__*/React.createElement(PostCard, {
      post: post,
      extraClass: "dc-announcement dc-scanlines"
    }, p => /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 mb-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-dc-gold flex items-center gap-1.5"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-bullhorn text-[10px]"
    }), /*#__PURE__*/React.createElement("span", null, "ANNOUNCEMENT"))), p.title && /*#__PURE__*/React.createElement("h3", {
      className: "font-display text-xl sm:text-2xl font-bold text-white leading-tight mb-2"
    }, p.title), p.body && /*#__PURE__*/React.createElement(PostBody, {
      html: p.body.indexOf('<') >= 0 ? p.body : null,
      plain: p.body.indexOf('<') < 0 ? p.body : null
    }), p.cta && /*#__PURE__*/React.createElement("button", {
      className: "dc-btn-accent mt-4 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm"
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${p.cta.icon}`
    }), /*#__PURE__*/React.createElement("span", null, p.cta.label), /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-arrow-right text-xs"
    }))));
  }
  function EventCard({
    post
  }) {
    const ev = post.event || {};
    const pct = ev.slots ? Math.round(ev.slots.taken / ev.slots.total * 100) : 0;
    return /*#__PURE__*/React.createElement(PostCard, {
      post: post,
      extraClass: "dc-tournament"
    }, p => /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 mb-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-dc-cyan flex items-center gap-1.5"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-trophy text-[10px]"
    }), /*#__PURE__*/React.createElement("span", null, "TOURNAMENT")), ev.mode && /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-white/40"
    }, ev.mode)), p.title && /*#__PURE__*/React.createElement("h3", {
      className: "font-display text-xl font-bold text-white leading-tight mb-1"
    }, p.title), p.body && /*#__PURE__*/React.createElement("p", {
      className: "text-[14px] text-white/65 mb-4"
    }, p.body), ev.prize && /*#__PURE__*/React.createElement("div", {
      className: "grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4"
    }, /*#__PURE__*/React.createElement("div", {
      className: "rounded-xl bg-white/[.03] border border-white/[.06] p-3"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/35"
    }, "Prize Pool"), /*#__PURE__*/React.createElement("div", {
      className: "dc-counter-num text-lg text-dc-gold mt-1"
    }, ev.prize)), ev.starts && /*#__PURE__*/React.createElement("div", {
      className: "rounded-xl bg-white/[.03] border border-white/[.06] p-3"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/35"
    }, "Starts"), /*#__PURE__*/React.createElement("div", {
      className: "text-[12px] font-semibold text-white mt-1"
    }, ev.starts)), ev.format && /*#__PURE__*/React.createElement("div", {
      className: "rounded-xl bg-white/[.03] border border-white/[.06] p-3"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/35"
    }, "Format"), /*#__PURE__*/React.createElement("div", {
      className: "text-[12px] font-semibold text-white mt-1"
    }, ev.format)), ev.slots && /*#__PURE__*/React.createElement("div", {
      className: "rounded-xl bg-white/[.03] border border-white/[.06] p-3"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/35"
    }, "Slots"), /*#__PURE__*/React.createElement("div", {
      className: "dc-mono text-[13px] font-semibold text-white mt-1"
    }, ev.slots.taken, /*#__PURE__*/React.createElement("span", {
      className: "text-white/40"
    }, "/", ev.slots.total)), /*#__PURE__*/React.createElement("div", {
      className: "h-1 mt-1.5 bg-white/5 rounded-full overflow-hidden"
    }, /*#__PURE__*/React.createElement("div", {
      className: "h-full",
      style: {
        width: `${pct}%`,
        background: 'linear-gradient(90deg, var(--dc-accent), var(--dc-accent-2))'
      }
    })))), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2"
    }, /*#__PURE__*/React.createElement("button", {
      className: "dc-btn-accent flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-arrow-right-to-bracket"
    }), " Register Team"), /*#__PURE__*/React.createElement("button", {
      className: "dc-btn-ghost px-4 py-2.5 rounded-xl text-sm"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-eye mr-1.5"
    }), " View Bracket"))));
  }
  function TextCard({
    post
  }) {
    return /*#__PURE__*/React.createElement(PostCard, {
      post: post
    }, p => /*#__PURE__*/React.createElement(React.Fragment, null, p.title && /*#__PURE__*/React.createElement("h3", {
      className: "font-display text-lg font-semibold text-white leading-snug mb-1.5"
    }, p.title), p.body && /*#__PURE__*/React.createElement(PostBody, {
      html: p.body.indexOf('<') >= 0 ? p.body : null,
      plain: p.body.indexOf('<') < 0 ? p.body : null
    })));
  }
  function ImageCard({
    post
  }) {
    return /*#__PURE__*/React.createElement(PostCard, {
      post: post
    }, p => /*#__PURE__*/React.createElement(React.Fragment, null, p.body && /*#__PURE__*/React.createElement("div", {
      className: "mb-3"
    }, /*#__PURE__*/React.createElement(PostBody, {
      html: p.body.indexOf('<') >= 0 ? p.body : null,
      plain: p.body.indexOf('<') < 0 ? p.body : null
    })), /*#__PURE__*/React.createElement("div", {
      className: "rounded-xl overflow-hidden border border-white/[.06] relative bg-black/30"
    }, p.image && p.image.url ? /*#__PURE__*/React.createElement("img", {
      src: p.image.url,
      alt: p.image.alt || '',
      className: "w-full max-h-[640px] object-contain",
      onError: e => {
        e.currentTarget.style.display = 'none';
      }
    }) : p.image && /*#__PURE__*/React.createElement("div", {
      style: {
        aspectRatio: '16/10',
        background: `linear-gradient(135deg, ${p.image.color1 || '#7B2BFF'}, ${p.image.color2 || '#00E5FF'})`
      }
    }, /*#__PURE__*/React.createElement("div", {
      className: "absolute inset-0 opacity-25",
      style: {
        background: 'repeating-linear-gradient(135deg, rgba(255,255,255,0.06) 0 16px, transparent 16px 32px)'
      }
    }), p.image.label && /*#__PURE__*/React.createElement("div", {
      className: "absolute top-3 left-3 px-2.5 py-1 rounded-md bg-black/50 backdrop-blur-sm text-[10px] font-bold tracking-widest text-white"
    }, p.image.label)))));
  }
  function ClipCard({
    post
  }) {
    const [playing, setPlaying] = useState(false);
    return /*#__PURE__*/React.createElement(PostCard, {
      post: post
    }, p => /*#__PURE__*/React.createElement(React.Fragment, null, p.body && /*#__PURE__*/React.createElement("div", {
      className: "mb-3"
    }, /*#__PURE__*/React.createElement(PostBody, {
      html: p.body.indexOf('<') >= 0 ? p.body : null,
      plain: p.body.indexOf('<') < 0 ? p.body : null
    })), /*#__PURE__*/React.createElement("div", {
      className: "relative rounded-xl overflow-hidden border border-white/[.06] cursor-pointer group bg-black",
      style: {
        aspectRatio: '16 / 9',
        background: p.clip && p.clip.thumbColor1 ? `linear-gradient(135deg, ${p.clip.thumbColor1}, ${p.clip.thumbColor2})` : undefined
      },
      onClick: () => setPlaying(true)
    }, playing && p.clip && p.clip.url ? p.clip.isEmbed ? /*#__PURE__*/React.createElement("iframe", {
      src: p.clip.url,
      className: "w-full h-full",
      allow: "autoplay; fullscreen; picture-in-picture",
      allowFullScreen: true,
      style: {
        border: 'none'
      }
    }) : /*#__PURE__*/React.createElement("video", {
      src: p.clip.url,
      className: "w-full h-full",
      controls: true,
      autoPlay: true,
      playsInline: true
    }) : /*#__PURE__*/React.createElement(React.Fragment, null, p.clip && p.clip.url && !p.clip.isEmbed && /*#__PURE__*/React.createElement("video", {
      src: p.clip.url,
      className: "w-full h-full object-cover opacity-80",
      preload: "metadata",
      muted: true
    }), /*#__PURE__*/React.createElement("div", {
      className: "absolute inset-0 opacity-30",
      style: {
        background: 'repeating-linear-gradient(45deg, rgba(255,255,255,0.05) 0 12px, transparent 12px 24px)'
      }
    }), /*#__PURE__*/React.createElement("div", {
      className: "absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/60"
    }), p.game && /*#__PURE__*/React.createElement("div", {
      className: "absolute top-3 left-3 flex items-center gap-2"
    }, /*#__PURE__*/React.createElement(GameHex, {
      game: p.game,
      size: 26
    }), p.clip && p.clip.caption && /*#__PURE__*/React.createElement("div", {
      className: "text-[10px] font-bold text-white tracking-wide"
    }, p.clip.caption)), p.clip && p.clip.duration && /*#__PURE__*/React.createElement("div", {
      className: "absolute top-3 right-3 px-2 py-0.5 rounded-md bg-black/60 backdrop-blur-sm text-[10px] font-bold dc-mono text-white"
    }, p.clip.duration), /*#__PURE__*/React.createElement("button", {
      className: "dc-play-btn absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2",
      "aria-label": "Play"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-play text-xl text-white ml-1"
    })), p.clip && typeof p.clip.views === 'number' && /*#__PURE__*/React.createElement("div", {
      className: "absolute bottom-3 left-3 right-3 flex items-center justify-between"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 text-[11px] text-white/80 font-semibold"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-eye"
    }), /*#__PURE__*/React.createElement("span", {
      className: "dc-mono"
    }, p.clip.views.toLocaleString())), /*#__PURE__*/React.createElement("div", {
      className: "px-2 py-0.5 rounded-md bg-white/15 backdrop-blur-md text-[10px] font-bold text-white border border-white/20"
    }, "HIGHLIGHT"))))));
  }
  function PollCard({
    post
  }) {
    const api = window.DC && window.DC.api || null;
    const authed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);
    const initState = post.poll_data || post.poll || {
      options: [],
      total: 0,
      my_vote: null,
      voted: null
    };
    const [pollState, setPollState] = useState(initState);
    const myVote = pollState.my_vote || pollState.voted;
    const winner = (pollState.options || []).length ? pollState.options.reduce((a, b) => (a.votes || 0) > (b.votes || 0) ? a : b, pollState.options[0]) : null;
    const vote = optId => {
      if (myVote) return;
      if (!authed) {
        window.location.href = '/account/login/?next=/community/';
        return;
      }
      const prev = pollState;
      setPollState(s => ({
        ...s,
        total: (s.total || 0) + 1,
        my_vote: optId,
        voted: optId,
        options: (s.options || []).map(o => o.id === optId ? {
          ...o,
          votes: (o.votes || 0) + 1
        } : o)
      }));
      if (api && api.votePoll && post._pk) {
        api.votePoll(post._pk, optId).then(r => {
          if (r && r.poll_data) setPollState(r.poll_data);
        }).catch(() => setPollState(prev));
      }
    };
    return /*#__PURE__*/React.createElement(PostCard, {
      post: post
    }, p => /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 mb-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label flex items-center gap-1.5",
      style: {
        color: 'var(--dc-accent-2)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-square-poll-vertical text-[10px]"
    }), /*#__PURE__*/React.createElement("span", null, "POLL"))), p.title && /*#__PURE__*/React.createElement("h3", {
      className: "text-base sm:text-lg font-semibold text-white leading-snug mb-3"
    }, p.title), p.body && !p.title && /*#__PURE__*/React.createElement("p", {
      className: "text-[14px] text-white/75 mb-3"
    }, p.body), /*#__PURE__*/React.createElement("div", {
      className: "space-y-2"
    }, (pollState.options || []).map(o => {
      const total = pollState.total || 0;
      const pct = total > 0 ? Math.round((o.votes || 0) / total * 100) : 0;
      const isVoted = myVote === o.id;
      const isWinner = !!myVote && winner && o.id === winner.id;
      return /*#__PURE__*/React.createElement("div", {
        key: o.id,
        onClick: () => vote(o.id),
        className: `dc-poll-bar ${myVote ? 'is-voted' : 'cursor-pointer'} ${isWinner ? 'is-winner' : ''}`
      }, /*#__PURE__*/React.createElement("div", {
        className: "dc-poll-fill",
        style: {
          width: myVote ? `${pct}%` : '0%'
        }
      }), /*#__PURE__*/React.createElement("div", {
        className: "flex items-center justify-between relative z-10"
      }, /*#__PURE__*/React.createElement("div", {
        className: "flex items-center gap-2"
      }, isVoted && /*#__PURE__*/React.createElement("i", {
        className: "fa-solid fa-circle-check text-xs",
        style: {
          color: 'var(--dc-accent)'
        }
      }), /*#__PURE__*/React.createElement("span", {
        className: `text-sm ${isVoted ? 'font-bold text-white' : 'text-white/80'}`
      }, o.label), isWinner && !!myVote && /*#__PURE__*/React.createElement("span", {
        className: "dc-hud-label text-[8px] ml-1",
        style: {
          color: 'var(--dc-gold)'
        }
      }, "LEADING")), !!myVote && /*#__PURE__*/React.createElement("span", {
        className: "dc-mono text-sm font-bold text-white/70"
      }, pct, "%")));
    })), /*#__PURE__*/React.createElement("div", {
      className: "mt-3 flex items-center justify-between text-[12px] text-white/40"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-mono"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-users text-[9px] mr-1"
    }), (pollState.total || 0).toLocaleString(), " votes"), /*#__PURE__*/React.createElement("span", {
      style: {
        color: 'var(--dc-accent)'
      }
    }, !myVote ? 'Tap to vote' : 'Voted'))));
  }
  function InfoCell({
    label,
    value,
    accent,
    mono
  }) {
    return /*#__PURE__*/React.createElement("div", {
      className: "rounded-xl bg-white/[.03] border border-white/[.05] p-2.5"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/35 mb-0.5"
    }, label), /*#__PURE__*/React.createElement("div", {
      className: `text-[12px] font-semibold leading-snug ${accent ? 'text-dc-cyan' : 'text-white'} ${mono ? 'dc-mono' : ''}`
    }, value));
  }
  function LftCard({
    post
  }) {
    const lft = post.lft_data || post.lft || {};
    const roles = Array.isArray(lft.roles) ? lft.roles : lft.roles ? [lft.roles] : [];
    return /*#__PURE__*/React.createElement(PostCard, {
      post: post,
      extraClass: "dc-lft"
    }, p => /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 mb-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-dc-emerald flex items-center gap-1.5"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-signal text-[10px]"
    }), /*#__PURE__*/React.createElement("span", null, "LOOKING FOR TEAM")), p.game && /*#__PURE__*/React.createElement(GameHex, {
      game: p.game,
      size: 24
    })), (p.title || p.body) && /*#__PURE__*/React.createElement("p", {
      className: "text-[14.5px] text-white/85 mb-3"
    }, p.title || '', p.body && !p.title && /*#__PURE__*/React.createElement(PostBody, {
      html: p.body.indexOf('<') >= 0 ? p.body : null,
      plain: p.body.indexOf('<') < 0 ? p.body : null
    })), /*#__PURE__*/React.createElement("div", {
      className: "grid grid-cols-2 sm:grid-cols-4 gap-2.5"
    }, roles.length > 0 && /*#__PURE__*/React.createElement(InfoCell, {
      label: "Roles",
      value: roles.join(', ')
    }), lft.rank && /*#__PURE__*/React.createElement(InfoCell, {
      label: "Rank",
      value: lft.rank,
      accent: true
    }), lft.hours && /*#__PURE__*/React.createElement(InfoCell, {
      label: "Hours",
      value: lft.hours,
      mono: true
    }), lft.region && /*#__PURE__*/React.createElement(InfoCell, {
      label: "Region",
      value: lft.region
    })), lft.availability && /*#__PURE__*/React.createElement("div", {
      className: "text-[12px] text-white/50 mt-2.5"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-clock mr-1.5"
    }), lft.availability), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 mt-3"
    }, /*#__PURE__*/React.createElement("button", {
      className: "dc-btn-accent inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-envelope text-xs"
    }), " Invite to Team"), /*#__PURE__*/React.createElement("a", {
      href: p.author.profile_url || '#',
      className: "dc-btn-ghost px-4 py-2 rounded-xl text-sm inline-flex items-center gap-1.5"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-user"
    }), " Profile"))));
  }
  function RecruitCard({
    post
  }) {
    const lft = post.lft_data || post.recruit || {};
    const team = post.team;
    const roles = Array.isArray(lft.roles) ? lft.roles : lft.roles ? [lft.roles] : [];
    const perks = Array.isArray(lft.perks) ? lft.perks : lft.perks ? [lft.perks] : [];
    return /*#__PURE__*/React.createElement(PostCard, {
      post: post,
      extraClass: "dc-recruit"
    }, p => /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 mb-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label flex items-center gap-1.5",
      style: {
        color: 'var(--dc-accent-2)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-user-plus text-[10px]"
    }), /*#__PURE__*/React.createElement("span", null, "RECRUITING")), p.game && /*#__PURE__*/React.createElement(GameHex, {
      game: p.game,
      size: 24
    }), team && /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-white/40 text-[9px]"
    }, team.tag || team.name)), team && /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 mb-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-7 h-7 rounded-lg overflow-hidden ring-1 ring-white/10 bg-white/5 grid place-items-center text-[8px] font-bold text-white/50"
    }, team.logo_url ? /*#__PURE__*/React.createElement("img", {
      src: team.logo_url,
      alt: team.name,
      className: "w-full h-full object-cover"
    }) : /*#__PURE__*/React.createElement("span", null, (team.tag || team.name || '?').slice(0, 3))), /*#__PURE__*/React.createElement("span", {
      className: "text-sm font-semibold text-white"
    }, team.name)), roles.length > 0 && /*#__PURE__*/React.createElement("p", {
      className: "text-[14.5px] text-white/85 mb-3"
    }, team ? /*#__PURE__*/React.createElement("strong", null, team.name) : 'Team', " is looking for:", ' ', /*#__PURE__*/React.createElement("span", {
      className: "text-dc-cyan font-semibold"
    }, roles.join(' · '))), (p.title || p.body) && !roles.length && /*#__PURE__*/React.createElement("div", {
      className: "mb-3"
    }, /*#__PURE__*/React.createElement(PostBody, {
      html: p.body && p.body.indexOf('<') >= 0 ? p.body : null,
      plain: p.body && p.body.indexOf('<') < 0 ? p.body : null
    })), (lft.rank || lft.commitment) && /*#__PURE__*/React.createElement("div", {
      className: "grid grid-cols-2 gap-2 mb-3"
    }, lft.rank && /*#__PURE__*/React.createElement(InfoCell, {
      label: "Requirement",
      value: lft.rank,
      accent: true
    }), lft.commitment && /*#__PURE__*/React.createElement(InfoCell, {
      label: "Commitment",
      value: lft.commitment
    })), perks.length > 0 && /*#__PURE__*/React.createElement("div", {
      className: "flex flex-wrap gap-1.5 mb-3"
    }, perks.map(pk => /*#__PURE__*/React.createElement("span", {
      key: pk,
      className: "dc-chip"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-check text-[8px]"
    }), pk))), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2"
    }, /*#__PURE__*/React.createElement("button", {
      className: "dc-btn-accent inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-paper-plane text-xs"
    }), " Apply Now"), team && /*#__PURE__*/React.createElement("a", {
      href: `/teams/${team.slug || ''}/`,
      className: "dc-btn-ghost px-4 py-2 rounded-xl text-sm inline-flex items-center gap-1.5"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-users"
    }), " View Team"))));
  }
  function AchievementCard({
    post
  }) {
    const ach = post.achievement || {};
    return /*#__PURE__*/React.createElement(PostCard, {
      post: post
    }, p => /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-4 p-2 rounded-xl"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-14 h-14 rounded-2xl grid place-items-center text-2xl shrink-0",
      style: {
        background: `linear-gradient(135deg, ${ach.color1 || '#FFD166'}, ${ach.color2 || '#FF4D6D'})`
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${ach.icon || 'trophy'} text-black`
    })), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-dc-gold mb-0.5"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-medal text-[10px] mr-1"
    }), " ACHIEVEMENT UNLOCKED"), /*#__PURE__*/React.createElement("div", {
      className: "font-display text-base font-bold text-white"
    }, ach.title || p.title), /*#__PURE__*/React.createElement("div", {
      className: "text-[12px] text-white/50 mt-0.5"
    }, ach.sub || p.body)), p.game && /*#__PURE__*/React.createElement(GameHex, {
      game: p.game,
      size: 32
    })));
  }
  function PostDispatcher({
    post
  }) {
    switch (post.type) {
      case 'announcement':
        return /*#__PURE__*/React.createElement(AnnouncementCard, {
          post: post
        });
      case 'event':
        return /*#__PURE__*/React.createElement(EventCard, {
          post: post
        });
      case 'clip':
        return /*#__PURE__*/React.createElement(ClipCard, {
          post: post
        });
      case 'poll':
        return /*#__PURE__*/React.createElement(PollCard, {
          post: post
        });
      case 'lft':
        return /*#__PURE__*/React.createElement(LftCard, {
          post: post
        });
      case 'recruit':
        return /*#__PURE__*/React.createElement(RecruitCard, {
          post: post
        });
      case 'image':
        return /*#__PURE__*/React.createElement(ImageCard, {
          post: post
        });
      case 'achievement':
        return /*#__PURE__*/React.createElement(AchievementCard, {
          post: post
        });
      case 'text':
      default:
        return /*#__PURE__*/React.createElement(TextCard, {
          post: post
        });
    }
  }
  Object.assign(window, {
    Avatar,
    GameHex,
    VerifiedTick,
    StaffBadge,
    PostHeader,
    PostActions,
    CommentsBlock,
    PostCard,
    PostDispatcher,
    PollCard,
    LftCard,
    RecruitCard
  });
})();
