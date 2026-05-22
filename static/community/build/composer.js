/* DeltaCrown Community — Smart composer modal */
(function () {
  const {
    useState: useStateC,
    useEffect: useEffectC,
    useRef: useRefC
  } = React;
  const Avatar = window.Avatar;
  const VerifiedTick = window.VerifiedTick;

  /* ---- Post type catalog ---- */
  const COMPOSE_TYPES = [{
    id: 'text',
    icon: 'pen-to-square',
    label: 'Post',
    hint: 'A discussion, tip, or update'
  }, {
    id: 'image',
    icon: 'image',
    label: 'Image',
    hint: 'Share photos or screenshots'
  }, {
    id: 'clip',
    icon: 'circle-play',
    label: 'Clip',
    hint: 'Highlight or gameplay clip'
  }, {
    id: 'poll',
    icon: 'square-poll-vertical',
    label: 'Poll',
    hint: 'Ask the community'
  }, {
    id: 'lft',
    icon: 'signal',
    label: 'LFT',
    hint: 'Looking for a team'
  }, {
    id: 'recruit',
    icon: 'user-plus',
    label: 'Recruit',
    hint: 'Open team positions'
  }];
  const POLL_TYPES = [{
    id: 'general',
    label: 'General',
    icon: 'comments',
    hint: 'Open community question'
  }, {
    id: 'game',
    label: 'Game',
    icon: 'gamepad',
    hint: 'Game-specific topic'
  }, {
    id: 'match',
    label: 'Match',
    icon: 'crosshairs',
    hint: 'Predict a match outcome'
  }, {
    id: 'tournament',
    label: 'Tournament',
    icon: 'trophy',
    hint: 'Tournament-related vote'
  }, {
    id: 'team',
    label: 'Team',
    icon: 'shield-halved',
    hint: 'Vote on a team'
  }];
  const VISIBILITY = [{
    id: 'public',
    icon: 'globe',
    label: 'Public'
  }, {
    id: 'followers',
    icon: 'user-check',
    label: 'Followers'
  }, {
    id: 'team',
    icon: 'shield',
    label: 'Team only'
  }];
  const ROLES_BY_GAME = {
    valorant: ['Duelist', 'Initiator', 'Sentinel', 'Controller', 'IGL', 'Flex'],
    cs2: ['Entry', 'AWPer', 'Support', 'Lurker', 'Rifler', 'IGL'],
    dota2: ['Carry', 'Mid', 'Offlane', 'Soft Support', 'Hard Support'],
    pubgm: ['IGL', 'Fragger', 'Scout', 'Support', 'Sniper'],
    freefire: ['IGL', 'Rusher', 'Sniper', 'Support'],
    mlbb: ['Jungler', 'Mid', 'Roamer', 'Gold Laner', 'EXP Laner'],
    codm: ['Slayer', 'Anchor', 'Objective', 'Flex'],
    rl: ['Striker', 'Defender', 'Hybrid', 'Rotation'],
    fc26: ['Striker', 'Midfielder', 'Defender', 'Goalkeeper', 'Flex'],
    efootball: ['Striker', 'Midfielder', 'Defender', 'Goalkeeper', 'Flex']
  };
  const RANKS_BY_GAME = {
    valorant: ['Iron', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Ascendant', 'Immortal', 'Radiant'],
    cs2: ['FACEIT 1', 'FACEIT 2-3', 'FACEIT 4-6', 'FACEIT 7-8', 'FACEIT 9', 'FACEIT 10'],
    dota2: ['Herald', 'Guardian', 'Crusader', 'Archon', 'Legend', 'Ancient', 'Divine', 'Immortal'],
    pubgm: ['Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Crown', 'Ace', 'Conqueror'],
    freefire: ['Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Heroic', 'Master', 'Grandmaster'],
    mlbb: ['Warrior', 'Elite', 'Master', 'Grandmaster', 'Epic', 'Legend', 'Mythic', 'Mythical Glory'],
    codm: ['Rookie', 'Veteran', 'Elite', 'Pro', 'Master', 'Grandmaster', 'Legendary'],
    rl: ['Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Champion', 'Grand Champion', 'SSL'],
    fc26: ['Div 10', 'Div 7-9', 'Div 4-6', 'Div 2-3', 'Elite', 'Top 100'],
    efootball: ['Amateur', 'Semi-Pro', 'Pro', 'World Class', 'Superstar', 'Legend']
  };

  /* ---- Rich text editor ---- */
  function RichEditor({
    value,
    onChange,
    placeholder
  }) {
    const ref = useRefC(null);
    const [active, setActive] = useStateC({});
    useEffectC(() => {
      if (ref.current && ref.current.innerHTML !== value) {
        ref.current.innerHTML = value || '';
      }
    }, [value]);
    const exec = (cmd, arg) => {
      document.execCommand(cmd, false, arg);
      ref.current && ref.current.focus();
      update();
    };
    const update = () => {
      if (!ref.current) return;
      onChange(ref.current.innerHTML);
      setActive({
        bold: document.queryCommandState('bold'),
        italic: document.queryCommandState('italic'),
        under: document.queryCommandState('underline'),
        ul: document.queryCommandState('insertUnorderedList'),
        ol: document.queryCommandState('insertOrderedList')
      });
    };
    const link = () => {
      const url = prompt('Link URL');
      if (url) exec('createLink', url);
    };
    return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      className: "dc-rt-toolbar"
    }, /*#__PURE__*/React.createElement("button", {
      className: `dc-rt-btn ${active.bold ? 'is-active' : ''}`,
      onMouseDown: e => {
        e.preventDefault();
        exec('bold');
      },
      title: "Bold"
    }, /*#__PURE__*/React.createElement("b", null, "B")), /*#__PURE__*/React.createElement("button", {
      className: `dc-rt-btn ${active.italic ? 'is-active' : ''}`,
      onMouseDown: e => {
        e.preventDefault();
        exec('italic');
      },
      title: "Italic"
    }, /*#__PURE__*/React.createElement("i", null, "I")), /*#__PURE__*/React.createElement("button", {
      className: `dc-rt-btn ${active.under ? 'is-active' : ''}`,
      onMouseDown: e => {
        e.preventDefault();
        exec('underline');
      },
      title: "Underline"
    }, /*#__PURE__*/React.createElement("u", null, "U")), /*#__PURE__*/React.createElement("div", {
      className: "dc-rt-sep"
    }), /*#__PURE__*/React.createElement("button", {
      className: "dc-rt-btn",
      onMouseDown: e => {
        e.preventDefault();
        exec('formatBlock', 'h2');
      },
      title: "Heading"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-[10px] font-bold"
    }, "H")), /*#__PURE__*/React.createElement("button", {
      className: "dc-rt-btn",
      onMouseDown: e => {
        e.preventDefault();
        exec('formatBlock', 'blockquote');
      },
      title: "Quote"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-quote-right text-[10px]"
    })), /*#__PURE__*/React.createElement("div", {
      className: "dc-rt-sep"
    }), /*#__PURE__*/React.createElement("button", {
      className: `dc-rt-btn ${active.ul ? 'is-active' : ''}`,
      onMouseDown: e => {
        e.preventDefault();
        exec('insertUnorderedList');
      },
      title: "Bullets"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-list-ul text-[10px]"
    })), /*#__PURE__*/React.createElement("button", {
      className: `dc-rt-btn ${active.ol ? 'is-active' : ''}`,
      onMouseDown: e => {
        e.preventDefault();
        exec('insertOrderedList');
      },
      title: "Numbered"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-list-ol text-[10px]"
    })), /*#__PURE__*/React.createElement("div", {
      className: "dc-rt-sep"
    }), /*#__PURE__*/React.createElement("button", {
      className: "dc-rt-btn",
      onMouseDown: e => {
        e.preventDefault();
        link();
      },
      title: "Link"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-link text-[10px]"
    })), /*#__PURE__*/React.createElement("button", {
      className: "dc-rt-btn",
      onMouseDown: e => {
        e.preventDefault();
        exec('insertHTML', '<code></code>');
      },
      title: "Code"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-code text-[10px]"
    })), /*#__PURE__*/React.createElement("div", {
      className: "ml-auto flex items-center gap-1"
    }, /*#__PURE__*/React.createElement("button", {
      className: "dc-rt-btn",
      title: "Mention"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-at text-[10px]"
    })), /*#__PURE__*/React.createElement("button", {
      className: "dc-rt-btn",
      title: "Hashtag"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-hashtag text-[10px]"
    })), /*#__PURE__*/React.createElement("button", {
      className: "dc-rt-btn",
      title: "Emoji"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-face-smile text-[11px]"
    })))), /*#__PURE__*/React.createElement("div", {
      ref: ref,
      className: "dc-rich",
      contentEditable: true,
      suppressContentEditableWarning: true,
      "data-placeholder": placeholder,
      onInput: update,
      onKeyUp: update,
      onMouseUp: update,
      style: {
        fontFamily: "'Noto Sans Bengali','Inter',sans-serif"
      }
    }));
  }

  /* ---- Tag picker (Tournament / Team / Match) ---- */
  function TagPicker({
    kind,
    value,
    onChange
  }) {
    const [open, setOpen] = useStateC(false);
    const myTournaments = window.DC.MY_TOURNAMENTS || [];
    const opts = kind === 'tournament' ? myTournaments.map(t => ({
      id: String(t.id),
      label: t.name,
      sub: t.slug
    })) : kind === 'team' ? (window.DC.TEAMS || []).map(t => ({
      id: t.id,
      label: t.name,
      sub: `${t.tag} · ${t.members || 0} players`
    })) : [];
    return /*#__PURE__*/React.createElement("div", {
      className: "relative"
    }, value ? /*#__PURE__*/React.createElement("div", {
      className: "dc-tag-pill"
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${kind === 'tournament' ? 'trophy' : kind === 'team' ? 'shield-halved' : 'crosshairs'} text-[10px]`
    }), value.label, /*#__PURE__*/React.createElement("button", {
      onClick: () => onChange(null)
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-xmark"
    }))) : /*#__PURE__*/React.createElement("button", {
      onClick: () => setOpen(o => !o),
      className: "dc-chip dc-chip-pick"
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${kind === 'tournament' ? 'trophy' : kind === 'team' ? 'shield-halved' : 'crosshairs'} text-[10px]`
    }), "Tag ", kind), open && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "fixed inset-0 z-30",
      onClick: () => setOpen(false)
    }), /*#__PURE__*/React.createElement("div", {
      className: "dc-post-menu",
      style: {
        top: 'calc(100% + 4px)',
        left: 0,
        right: 'auto',
        minWidth: 280
      }
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-post-menu-label"
    }, "Pick a ", kind), opts.length === 0 && /*#__PURE__*/React.createElement("div", {
      className: "px-3 py-2 text-[12px] text-white/40"
    }, "No ", kind, "s found."), opts.map(o => /*#__PURE__*/React.createElement("button", {
      key: o.id,
      className: "dc-post-menu-item",
      onClick: () => {
        onChange(o);
        setOpen(false);
      }
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-7 h-7 rounded-lg grid place-items-center shrink-0",
      style: {
        background: 'linear-gradient(135deg, var(--dc-accent), var(--dc-accent-2))'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${kind === 'tournament' ? 'trophy' : 'shield-halved'} text-[10px] text-black`
    })), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "font-semibold text-white text-[13px] truncate"
    }, o.label), /*#__PURE__*/React.createElement("div", {
      className: "text-[10.5px] text-white/45 truncate"
    }, o.sub)))))));
  }

  /* ---- Per-type forms ---- */
  function TextForm({
    data,
    setData
  }) {
    return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("input", {
      className: "dc-input",
      placeholder: "Title (optional)",
      value: data.title || '',
      onChange: e => setData({
        ...data,
        title: e.target.value
      })
    })), /*#__PURE__*/React.createElement(RichEditor, {
      value: data.body || '',
      onChange: v => setData({
        ...data,
        body: v
      }),
      placeholder: "Share an update, ask a question, talk strategy\u2026"
    }));
  }
  function ImageForm({
    data,
    setData
  }) {
    const fileRef = useRefC(null);
    /* data.files = File[] (real File objects for upload) */
    const files = data.files || [];
    /* Previews: array of {id, url, name} — url is an object URL */
    const previews = data.previews || [];
    const handleFiles = newFiles => {
      const added = Array.from(newFiles).slice(0, 4 - files.length);
      const newPreviews = added.map(f => ({
        id: Date.now() + Math.random(),
        url: URL.createObjectURL(f),
        name: f.name
      }));
      setData({
        ...data,
        files: [...files, ...added],
        previews: [...previews, ...newPreviews]
      });
    };
    const remove = (id, idx) => {
      /* Revoke object URL to avoid memory leak */
      const prev = previews.find(p => p.id === id);
      if (prev) URL.revokeObjectURL(prev.url);
      setData({
        ...data,
        files: files.filter((_, i) => i !== idx),
        previews: previews.filter(p => p.id !== id)
      });
    };
    const onDrop = e => {
      e.preventDefault();
      handleFiles(e.dataTransfer.files);
    };
    return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(RichEditor, {
      value: data.body || '',
      onChange: v => setData({
        ...data,
        body: v
      }),
      placeholder: "Caption your image\u2026"
    }), /*#__PURE__*/React.createElement("div", {
      className: "mt-3"
    }, /*#__PURE__*/React.createElement("input", {
      ref: fileRef,
      type: "file",
      accept: "image/*",
      multiple: true,
      className: "hidden",
      onChange: e => handleFiles(e.target.files)
    }), previews.length === 0 ? /*#__PURE__*/React.createElement("div", {
      className: "dc-dropzone w-full cursor-pointer",
      onClick: () => fileRef.current && fileRef.current.click(),
      onDragOver: e => e.preventDefault(),
      onDrop: onDrop
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-dropzone-icon"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-image"
    })), /*#__PURE__*/React.createElement("div", {
      className: "text-sm font-semibold text-white"
    }, "Click to select images, or drag & drop"), /*#__PURE__*/React.createElement("div", {
      className: "text-[11px] text-white/45 mt-0.5"
    }, "PNG, JPG, GIF, WebP \xB7 up to 10 MB each \xB7 max 4")) : /*#__PURE__*/React.createElement("div", {
      className: "rounded-xl border border-white/[.06] p-3 bg-white/[.02]"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center justify-between mb-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-white/45"
    }, previews.length, " image", previews.length !== 1 ? 's' : ''), previews.length < 4 && /*#__PURE__*/React.createElement("button", {
      onClick: () => fileRef.current && fileRef.current.click(),
      className: "text-[11px] text-dc-cyan font-semibold hover:underline"
    }, "+ Add another")), /*#__PURE__*/React.createElement("div", {
      className: "dc-media-grid"
    }, previews.map((img, idx) => /*#__PURE__*/React.createElement("div", {
      key: img.id,
      className: "dc-media-thumb"
    }, /*#__PURE__*/React.createElement("img", {
      src: img.url,
      alt: img.name,
      className: "w-full h-full object-cover"
    }), /*#__PURE__*/React.createElement("button", {
      className: "remove",
      onClick: () => remove(img.id, idx)
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-xmark"
    }))))))));
  }
  function parseClipUrl(url) {
    /* Returns {platform, embedId, thumbUrl} or null */
    if (!url) return null;
    const yt = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    if (yt) return {
      platform: 'youtube',
      id: yt[1],
      embedUrl: `https://www.youtube.com/embed/${yt[1]}`,
      thumbUrl: `https://img.youtube.com/vi/${yt[1]}/hqdefault.jpg`
    };
    const tw = url.match(/twitch\.tv\/(?:videos\/)?([a-zA-Z0-9_]+)/);
    if (tw) return {
      platform: 'twitch',
      id: tw[1],
      embedUrl: `https://player.twitch.tv/?video=${tw[1]}&parent=deltacrown.xyz`,
      thumbUrl: null
    };
    return null;
  }
  function ClipForm({
    data,
    setData
  }) {
    const [urlInput, setUrlInput] = useStateC(data.clipUrl || '');
    const [urlErr, setUrlErr] = useStateC('');
    const parsed = parseClipUrl(urlInput);
    const handleUrlChange = v => {
      setUrlInput(v);
      setUrlErr('');
      const p = parseClipUrl(v);
      if (v && !p) setUrlErr('Please enter a valid YouTube or Twitch clip URL.');
      setData({
        ...data,
        clipUrl: v,
        clipMeta: p
      });
    };
    return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-brands fa-youtube text-[#FF0000] mr-1.5"
    }), "YouTube or Twitch clip URL"), /*#__PURE__*/React.createElement("div", {
      className: "relative"
    }, /*#__PURE__*/React.createElement("input", {
      className: `dc-input ${urlErr ? 'border-dc-rose/60' : ''}`,
      placeholder: "https://www.youtube.com/watch?v=... or twitch.tv/...",
      value: urlInput,
      onChange: e => handleUrlChange(e.target.value)
    })), urlErr && /*#__PURE__*/React.createElement("p", {
      className: "text-[11px] text-dc-rose mt-1"
    }, urlErr), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-3 mt-1.5 text-[11px] text-white/35"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-brands fa-youtube text-red-500"
    }), " YouTube", /*#__PURE__*/React.createElement("i", {
      className: "fa-brands fa-twitch text-purple-400 ml-2"
    }), " Twitch")), parsed && /*#__PURE__*/React.createElement("div", {
      className: "rounded-xl border border-white/[.06] bg-white/[.02] p-3 mb-3 flex items-center gap-3 dc-fade-in"
    }, parsed.thumbUrl ? /*#__PURE__*/React.createElement("div", {
      className: "w-20 h-14 rounded-lg overflow-hidden shrink-0 bg-black"
    }, /*#__PURE__*/React.createElement("img", {
      src: parsed.thumbUrl,
      className: "w-full h-full object-cover",
      alt: ""
    })) : /*#__PURE__*/React.createElement("div", {
      className: "w-20 h-14 rounded-lg shrink-0 grid place-items-center",
      style: {
        background: 'linear-gradient(135deg, #9147ff, #6441a5)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-brands fa-twitch text-white text-xl"
    })), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-[13px] font-semibold text-white capitalize"
    }, parsed.platform, " clip"), /*#__PURE__*/React.createElement("div", {
      className: "text-[10.5px] text-white/45 truncate"
    }, urlInput)), /*#__PURE__*/React.createElement("button", {
      onClick: () => {
        setUrlInput('');
        setData({
          ...data,
          clipUrl: '',
          clipMeta: null
        });
      },
      className: "text-white/40 hover:text-dc-rose w-8 h-8 grid place-items-center rounded-md hover:bg-white/5 shrink-0"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-trash-can"
    }))), /*#__PURE__*/React.createElement("div", {
      className: "dc-field-row cols-3"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Map / Mode"), /*#__PURE__*/React.createElement("input", {
      className: "dc-input",
      placeholder: "e.g. Ascent \xB7 Defender",
      value: data.caption || '',
      onChange: e => setData({
        ...data,
        caption: e.target.value
      })
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Result"), /*#__PURE__*/React.createElement("select", {
      className: "dc-select",
      value: data.result || '',
      onChange: e => setData({
        ...data,
        result: e.target.value
      })
    }, /*#__PURE__*/React.createElement("option", {
      value: ""
    }, "\u2014"), /*#__PURE__*/React.createElement("option", {
      value: "win"
    }, "Win"), /*#__PURE__*/React.createElement("option", {
      value: "loss"
    }, "Loss"), /*#__PURE__*/React.createElement("option", {
      value: "clip"
    }, "Highlight only"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Skill"), /*#__PURE__*/React.createElement("select", {
      className: "dc-select",
      value: data.skill || '',
      onChange: e => setData({
        ...data,
        skill: e.target.value
      })
    }, /*#__PURE__*/React.createElement("option", {
      value: ""
    }, "\u2014"), /*#__PURE__*/React.createElement("option", null, "Ace"), /*#__PURE__*/React.createElement("option", null, "Clutch"), /*#__PURE__*/React.createElement("option", null, "Trickshot"), /*#__PURE__*/React.createElement("option", null, "Combo"), /*#__PURE__*/React.createElement("option", null, "Outplay")))), /*#__PURE__*/React.createElement("div", {
      className: "dc-field mt-1"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Caption"), /*#__PURE__*/React.createElement("textarea", {
      className: "dc-input",
      rows: "2",
      placeholder: "What happened? Tag teammates with @\u2026",
      value: data.body || '',
      onChange: e => setData({
        ...data,
        body: e.target.value
      })
    })));
  }
  function PollForm({
    data,
    setData
  }) {
    const [pollType, setPollType] = useStateC(data.pollType || 'general');
    const [taggedRef, setTaggedRef] = useStateC(data.taggedRef || null);
    useEffectC(() => {
      setData({
        ...data,
        pollType,
        taggedRef
      });
    }, [pollType, taggedRef]);
    const opts = data.options || [{
      id: 1,
      text: ''
    }, {
      id: 2,
      text: ''
    }];
    const updateOpt = (id, text) => setData({
      ...data,
      options: opts.map(o => o.id === id ? {
        ...o,
        text
      } : o)
    });
    const addOpt = () => setData({
      ...data,
      options: [...opts, {
        id: Date.now(),
        text: ''
      }]
    });
    const removeOpt = id => setData({
      ...data,
      options: opts.filter(o => o.id !== id)
    });
    const showTag = pollType === 'tournament' || pollType === 'team';
    return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Poll type"), /*#__PURE__*/React.createElement("div", {
      className: "grid grid-cols-2 sm:grid-cols-5 gap-2"
    }, POLL_TYPES.map(pt => /*#__PURE__*/React.createElement("button", {
      key: pt.id,
      onClick: () => setPollType(pt.id),
      className: `flex flex-col items-center gap-1 p-2.5 rounded-xl border transition ${pollType === pt.id ? 'bg-gradient-to-br from-[rgba(var(--dc-accent-rgb),0.18)] to-[rgba(var(--dc-accent-2-rgb),0.12)] border-[rgba(var(--dc-accent-rgb),0.45)] text-white' : 'bg-white/[.025] border-white/[.06] text-white/55 hover:text-white hover:bg-white/[.04]'}`
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${pt.icon} text-sm`
    }), /*#__PURE__*/React.createElement("span", {
      className: "text-[11px] font-bold"
    }, pt.label), /*#__PURE__*/React.createElement("span", {
      className: "text-[9px] text-white/40 text-center leading-tight"
    }, pt.hint))))), showTag && /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Tag the ", pollType), /*#__PURE__*/React.createElement(TagPicker, {
      kind: pollType,
      value: taggedRef,
      onChange: setTaggedRef
    })), /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Question"), /*#__PURE__*/React.createElement("input", {
      className: "dc-input",
      placeholder: "Ask the community something specific\u2026",
      value: data.title || '',
      onChange: e => setData({
        ...data,
        title: e.target.value
      })
    })), /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Options"), opts.map((o, i) => /*#__PURE__*/React.createElement("div", {
      key: o.id,
      className: "dc-poll-opt-row"
    }, /*#__PURE__*/React.createElement("span", {
      className: "num"
    }, String.fromCharCode(65 + i)), /*#__PURE__*/React.createElement("input", {
      className: "dc-input flex-1",
      placeholder: `Option ${i + 1}`,
      value: o.text,
      onChange: e => updateOpt(o.id, e.target.value)
    }), opts.length > 2 && /*#__PURE__*/React.createElement("button", {
      onClick: () => removeOpt(o.id),
      className: "text-white/40 hover:text-dc-rose w-9 h-9 rounded-md hover:bg-white/5 grid place-items-center shrink-0"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-xmark"
    })))), opts.length < 6 && /*#__PURE__*/React.createElement("button", {
      onClick: addOpt,
      className: "mt-1 text-[12px] text-dc-cyan font-semibold hover:underline"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-plus text-[10px] mr-1"
    }), " Add option")), /*#__PURE__*/React.createElement("div", {
      className: "dc-field-row cols-2"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Duration"), /*#__PURE__*/React.createElement("select", {
      className: "dc-select",
      value: data.duration || '1d',
      onChange: e => setData({
        ...data,
        duration: e.target.value
      })
    }, /*#__PURE__*/React.createElement("option", {
      value: "6h"
    }, "6 hours"), /*#__PURE__*/React.createElement("option", {
      value: "1d"
    }, "1 day"), /*#__PURE__*/React.createElement("option", {
      value: "3d"
    }, "3 days"), /*#__PURE__*/React.createElement("option", {
      value: "7d"
    }, "1 week"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Vote display"), /*#__PURE__*/React.createElement("select", {
      className: "dc-select",
      value: data.display || 'live',
      onChange: e => setData({
        ...data,
        display: e.target.value
      })
    }, /*#__PURE__*/React.createElement("option", {
      value: "live"
    }, "Show results live"), /*#__PURE__*/React.createElement("option", {
      value: "end"
    }, "Show only after vote ends"), /*#__PURE__*/React.createElement("option", {
      value: "voter"
    }, "Show only after I vote")))));
  }
  function LftForm({
    data,
    setData
  }) {
    /* Load game passports from the API via window.DC.MY_PASSPORTS */
    const passports = window.DC.MY_PASSPORTS || [];
    /* Fallback: if no passports, use the games list */
    const gameOptions = passports.length > 0 ? passports.map(p => ({
      id: p.game_slug,
      name: p.game_name,
      icon: p.game_icon,
      passport: p
    })) : (window.DC.GAMES || []).map(g => ({
      id: g.id,
      name: g.name,
      icon: g.logo,
      passport: null
    }));
    const selectedGameId = data.lftGame || gameOptions[0] && gameOptions[0].id || '';
    const selectedGameOpt = gameOptions.find(g => g.id === selectedGameId) || gameOptions[0];
    const selectedPassport = selectedGameOpt && selectedGameOpt.passport;

    /* When game changes, pre-fill from passport */
    const selectGame = gameId => {
      const opt = gameOptions.find(g => g.id === gameId);
      const p = opt && opt.passport;
      setData({
        ...data,
        lftGame: gameId,
        roles: p && p.main_role ? [p.main_role] : data.roles || [],
        rank: p && p.rank_name ? p.rank_name : data.rank || '',
        region: p && p.region ? p.region : data.region || 'BD / SEA',
        hours: p && p.hours ? String(p.hours) : data.hours || ''
      });
    };

    /* First mount: select first game */
    useEffectC(() => {
      if (!data.lftGame && gameOptions.length > 0) selectGame(gameOptions[0].id);
    }, []);
    const roles = ROLES_BY_GAME[selectedGameId] || ['Flex'];
    const ranks = RANKS_BY_GAME[selectedGameId] || ['Unranked'];
    const selected = data.roles || [];
    const toggleRole = r => setData({
      ...data,
      roles: selected.includes(r) ? selected.filter(x => x !== r) : [...selected, r]
    });
    return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Which game are you looking to play?"), passports.length === 0 && /*#__PURE__*/React.createElement("div", {
      className: "text-[11px] text-white/40 mb-2 p-2.5 rounded-lg bg-white/[.03] border border-white/[.05]"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-circle-info text-dc-cyan mr-1.5 text-[10px]"
    }), "Add Game Passports to your profile to get smarter LFT posts pre-filled with your rank and roles.", /*#__PURE__*/React.createElement("a", {
      href: "/profile/game-passports/",
      className: "text-dc-cyan hover:underline ml-1"
    }, "Set up \u2192")), /*#__PURE__*/React.createElement("div", {
      className: "flex flex-wrap gap-2"
    }, gameOptions.map(g => /*#__PURE__*/React.createElement("button", {
      key: g.id,
      onClick: () => selectGame(g.id),
      className: `flex items-center gap-2 px-3 py-2 rounded-xl border text-[13px] transition ${selectedGameId === g.id ? 'border-dc-cyan bg-dc-cyan/10 text-white' : 'border-white/[.08] text-white/55 hover:border-white/20 hover:text-white'}`
    }, g.icon && /*#__PURE__*/React.createElement("img", {
      src: g.icon,
      className: "w-5 h-5 rounded-sm object-cover",
      alt: g.name
    }), /*#__PURE__*/React.createElement("span", {
      className: "font-semibold"
    }, g.name), g.passport && g.passport.rank_name && /*#__PURE__*/React.createElement("span", {
      className: "text-[10px] text-dc-cyan dc-mono ml-1"
    }, g.passport.rank_name))))), selectedPassport && /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 p-2.5 rounded-xl bg-dc-cyan/5 border border-dc-cyan/15 text-[11.5px] text-white/65 mb-1 dc-fade-in"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-wand-magic-sparkles text-dc-cyan text-[10px]"
    }), "Pre-filled from your ", selectedPassport.game_name, " passport \u2014 IGN: ", /*#__PURE__*/React.createElement("strong", {
      className: "text-white"
    }, selectedPassport.ign || '–')), /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Roles you can play"), /*#__PURE__*/React.createElement("div", {
      className: "flex flex-wrap gap-1.5"
    }, roles.map(r => /*#__PURE__*/React.createElement("button", {
      key: r,
      onClick: () => toggleRole(r),
      className: `dc-chip dc-chip-pick ${selected.includes(r) ? 'is-active' : ''}`
    }, selected.includes(r) && /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-check text-[8px]"
    }), r)))), /*#__PURE__*/React.createElement("div", {
      className: "dc-field-row cols-2"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Current rank"), /*#__PURE__*/React.createElement("select", {
      className: "dc-select",
      value: data.rank || '',
      onChange: e => setData({
        ...data,
        rank: e.target.value
      })
    }, /*#__PURE__*/React.createElement("option", {
      value: ""
    }, "Pick rank\u2026"), ranks.map(r => /*#__PURE__*/React.createElement("option", {
      key: r,
      value: r
    }, r)))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Hours played"), /*#__PURE__*/React.createElement("input", {
      className: "dc-input",
      type: "number",
      placeholder: "e.g. 1200",
      value: data.hours || '',
      onChange: e => setData({
        ...data,
        hours: e.target.value
      })
    }))), /*#__PURE__*/React.createElement("div", {
      className: "dc-field-row cols-2"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Region"), /*#__PURE__*/React.createElement("select", {
      className: "dc-select",
      value: data.region || 'BD / SEA',
      onChange: e => setData({
        ...data,
        region: e.target.value
      })
    }, /*#__PURE__*/React.createElement("option", null, "BD / SEA"), /*#__PURE__*/React.createElement("option", null, "South Asia"), /*#__PURE__*/React.createElement("option", null, "SEA"), /*#__PURE__*/React.createElement("option", null, "EU"), /*#__PURE__*/React.createElement("option", null, "NA"), /*#__PURE__*/React.createElement("option", null, "Worldwide"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Availability"), /*#__PURE__*/React.createElement("input", {
      className: "dc-input",
      placeholder: "e.g. Daily \xB7 19:00\u201301:00",
      value: data.availability || '',
      onChange: e => setData({
        ...data,
        availability: e.target.value
      })
    }))), /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Tier of team you want"), /*#__PURE__*/React.createElement("div", {
      className: "flex gap-1.5 flex-wrap"
    }, ['Casual / Stack', 'Tier-3 amateur', 'Tier-2 semi-pro', 'Tier-1 / pro'].map(t => /*#__PURE__*/React.createElement("button", {
      key: t,
      onClick: () => setData({
        ...data,
        tier: t
      }),
      className: `dc-chip dc-chip-pick ${data.tier === t ? 'is-active' : ''}`
    }, t)))), /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Short pitch"), /*#__PURE__*/React.createElement("textarea", {
      className: "dc-input",
      rows: "3",
      placeholder: "Talk about your playstyle, recent results, what you're looking for\u2026",
      value: data.body || '',
      onChange: e => setData({
        ...data,
        body: e.target.value
      })
    })));
  }
  function PerkAdder({
    onAdd
  }) {
    const [val, setVal] = useStateC('');
    const SUGGEST = ['Sponsor support', 'In-house coach', 'Tournament slot', 'Paid travel', 'Streaming setup', 'Salary'];
    return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "flex gap-2"
    }, /*#__PURE__*/React.createElement("input", {
      className: "dc-input flex-1",
      placeholder: "Add a perk and press Enter\u2026",
      value: val,
      onChange: e => setVal(e.target.value),
      onKeyDown: e => {
        if (e.key === 'Enter' && val.trim()) {
          onAdd(val.trim());
          setVal('');
        }
      }
    }), /*#__PURE__*/React.createElement("button", {
      onClick: () => {
        if (val.trim()) {
          onAdd(val.trim());
          setVal('');
        }
      },
      className: "dc-btn-ghost px-4 rounded-lg text-xs whitespace-nowrap"
    }, "Add")), /*#__PURE__*/React.createElement("div", {
      className: "flex flex-wrap gap-1.5 mt-2"
    }, SUGGEST.map(p => /*#__PURE__*/React.createElement("button", {
      key: p,
      onClick: () => onAdd(p),
      className: "dc-chip dc-chip-pick text-[11px]"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-plus text-[8px]"
    }), p))));
  }
  function RecruitForm({
    data,
    setData,
    game
  }) {
    const myPostableTeams = (window.DC.MY_IDENTITIES || []).filter(i => i.kind === 'team' && i.canPost).map(i => ({
      ...(window.DC.TEAMS || []).find(t => t.id === i.teamId),
      role: i.role
    })).filter(Boolean);
    const selectedTeam = data.teamId ? (window.DC.TEAMS || []).find(t => t.id === data.teamId) : null;
    const inferredGame = selectedTeam ? selectedTeam.game : game;
    const roles = ROLES_BY_GAME[inferredGame] || ['Flex'];
    const selectedRoles = data.roles || [];
    const toggleRole = r => setData({
      ...data,
      roles: selectedRoles.includes(r) ? selectedRoles.filter(x => x !== r) : [...selectedRoles, r]
    });
    const perks = data.perks || [];
    return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Recruiting for which team? ", /*#__PURE__*/React.createElement("span", {
      className: "text-dc-rose"
    }, "*")), myPostableTeams.length === 0 ? /*#__PURE__*/React.createElement("div", {
      className: "rounded-xl border border-dashed border-white/10 p-4 text-center text-[12px] text-white/45"
    }, "You're not a captain or co-leader of any team. ", /*#__PURE__*/React.createElement("a", {
      className: "text-dc-cyan cursor-pointer",
      href: "/teams/create/"
    }, "Create a team \u2192")) : /*#__PURE__*/React.createElement("div", {
      className: "dc-team-pick"
    }, myPostableTeams.map(t => /*#__PURE__*/React.createElement("button", {
      key: t.id,
      onClick: () => setData({
        ...data,
        teamId: t.id
      }),
      className: `dc-team-card ${data.teamId === t.id ? 'is-selected' : ''}`
    }, /*#__PURE__*/React.createElement("div", {
      className: "crest",
      style: {
        background: `linear-gradient(135deg, ${t.color || '#7B2BFF'}, var(--dc-accent-2))`
      }
    }, t.logo_url ? /*#__PURE__*/React.createElement("img", {
      src: t.logo_url,
      alt: t.name,
      className: "w-full h-full object-cover"
    }) : /*#__PURE__*/React.createElement("div", {
      className: "dc-team-crest"
    }, t.tag)), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-[13px] font-semibold text-white truncate"
    }, t.name), /*#__PURE__*/React.createElement("div", {
      className: "text-[10.5px] text-white/45"
    }, t.role)), data.teamId === t.id && /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-circle-check text-dc-cyan"
    }))))), selectedTeam && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Roles needed"), /*#__PURE__*/React.createElement("div", {
      className: "flex flex-wrap gap-1.5"
    }, roles.map(r => /*#__PURE__*/React.createElement("button", {
      key: r,
      onClick: () => toggleRole(r),
      className: `dc-chip dc-chip-pick ${selectedRoles.includes(r) ? 'is-active' : ''}`
    }, selectedRoles.includes(r) && /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-check text-[8px]"
    }), r)))), /*#__PURE__*/React.createElement("div", {
      className: "dc-field-row cols-2"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Rank requirement"), /*#__PURE__*/React.createElement("input", {
      className: "dc-input",
      placeholder: "e.g. Diamond+ / FACEIT 8+",
      value: data.requirement || '',
      onChange: e => setData({
        ...data,
        requirement: e.target.value
      })
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Commitment"), /*#__PURE__*/React.createElement("input", {
      className: "dc-input",
      placeholder: "e.g. 4 nights/week + weekends",
      value: data.commitment || '',
      onChange: e => setData({
        ...data,
        commitment: e.target.value
      })
    }))), /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Perks (added one by one)"), /*#__PURE__*/React.createElement("div", {
      className: "flex flex-wrap gap-1.5 mb-2"
    }, perks.map((p, i) => /*#__PURE__*/React.createElement("span", {
      key: i,
      className: "dc-tag-pill"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-check text-[9px]"
    }), p, /*#__PURE__*/React.createElement("button", {
      onClick: () => setData({
        ...data,
        perks: perks.filter((_, j) => j !== i)
      })
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-xmark"
    }))))), /*#__PURE__*/React.createElement(PerkAdder, {
      onAdd: p => setData({
        ...data,
        perks: [...perks, p]
      })
    })), /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Description"), /*#__PURE__*/React.createElement("textarea", {
      className: "dc-input",
      rows: "3",
      placeholder: "Tell candidates what you're building, expectations, scrim schedule\u2026",
      value: data.body || '',
      onChange: e => setData({
        ...data,
        body: e.target.value
      })
    })), /*#__PURE__*/React.createElement("div", {
      className: "dc-field-row cols-2"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Apply via"), /*#__PURE__*/React.createElement("select", {
      className: "dc-select",
      value: data.applyVia || 'platform',
      onChange: e => setData({
        ...data,
        applyVia: e.target.value
      })
    }, /*#__PURE__*/React.createElement("option", {
      value: "platform"
    }, "DeltaCrown application form"), /*#__PURE__*/React.createElement("option", {
      value: "dm"
    }, "Direct message me"), /*#__PURE__*/React.createElement("option", {
      value: "discord"
    }, "Discord ticket"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Closes"), /*#__PURE__*/React.createElement("select", {
      className: "dc-select",
      value: data.closes || '7d',
      onChange: e => setData({
        ...data,
        closes: e.target.value
      })
    }, /*#__PURE__*/React.createElement("option", {
      value: "3d"
    }, "In 3 days"), /*#__PURE__*/React.createElement("option", {
      value: "7d"
    }, "In 1 week"), /*#__PURE__*/React.createElement("option", {
      value: "14d"
    }, "In 2 weeks"), /*#__PURE__*/React.createElement("option", {
      value: "open"
    }, "Open until filled"))))));
  }

  /* ---- ComposerModal ---- */
  function ComposerModal({
    open,
    onClose,
    identity,
    onSubmit,
    initialKind
  }) {
    /* ALL hooks MUST be before any early return — Rules of Hooks */
    const [kind, setKind] = useStateC(initialKind || 'text');
    const [game, setGame] = useStateC('valorant');
    const [vis, setVis] = useStateC('public');
    const [data, setData] = useStateC({});
    const [publishing, setPublishing] = useStateC(false);
    useEffectC(() => {
      if (open) {
        setKind(initialKind || 'text');
        setData({});
      }
    }, [open, initialKind]);
    useEffectC(() => {
      setData({});
    }, [kind]);
    if (!open) return null;
    const isTeam = identity && identity.kind === 'team';
    const team = isTeam ? (window.DC.TEAMS || []).find(t => t.id === identity.teamId) : null;
    const TypeForm = kind === 'image' ? ImageForm : kind === 'clip' ? ClipForm : kind === 'poll' ? PollForm : kind === 'lft' ? LftForm : kind === 'recruit' ? RecruitForm : TextForm;
    const canSubmit = kind === 'text' && (data.body || '').replace(/<[^>]*>/g, '').trim().length > 3 || kind === 'image' && (data.previews || []).length > 0 || kind === 'clip' && !!parseClipUrl(data.clipUrl) || kind === 'poll' && (data.title || '').trim() && (data.options || []).filter(o => o.text).length >= 2 || kind === 'lft' && (data.rank || '') && (data.roles || []).length > 0 || kind === 'recruit' && data.teamId && (data.roles || []).length > 0;
    const handlePublish = () => {
      if (!canSubmit || publishing) return;
      const api = window.DC && window.DC.api;
      if (!api) {
        onSubmit({
          kind,
          game,
          vis,
          data
        });
        onClose();
        return;
      }
      setPublishing(true);

      /* Build Django-compatible JSON payload */
      const payload = {
        post_type: kind,
        game,
        visibility: 'public'
      };
      if (isTeam && team && team._pk) payload.team_id = String(team._pk);
      if (data.taggedTournament) payload.tournament_id = String(data.taggedTournament.id);
      let fileList = null;
      if (kind === 'poll') {
        payload.title = (data.title || '').trim();
        payload.content = '';
        payload.poll_data = {
          options: (data.options || []).filter(o => o.text).map((o, i) => ({
            id: 'o' + i,
            label: o.text.trim()
          }))
        };
      } else if (kind === 'lft') {
        payload.content = data.body || '';
        payload.game = data.lftGame || game;
        payload.lft_data = {
          roles: data.roles || [],
          rank: data.rank || '',
          hours: data.hours || '',
          region: data.region || 'BD / SEA',
          availability: data.availability || '',
          tier: data.tier || '',
          looking_for: (data.body || '').slice(0, 200)
        };
      } else if (kind === 'recruit') {
        payload.content = data.body || '';
        const recTeam = (window.DC.TEAMS || []).find(t => t.id === data.teamId);
        if (recTeam && recTeam._pk) payload.team_id = String(recTeam._pk);
        payload.lft_data = {
          roles: data.roles || [],
          rank: data.requirement || '',
          commitment: data.commitment || '',
          perks: data.perks || [],
          applyVia: data.applyVia || 'platform'
        };
      } else if (kind === 'image') {
        payload.content = (data.body || '').replace(/<[^>]*>/g, '').trim() || data.body || '';
        payload.title = data.title || '';
        fileList = data.files || [];
      } else if (kind === 'clip') {
        const clipMeta = parseClipUrl(data.clipUrl);
        payload.content = [data.body || '', `[clip:${data.clipUrl}]`, data.caption ? `Map: ${data.caption}` : '', data.result ? `Result: ${data.result}` : '', data.skill ? `Skill: ${data.skill}` : ''].filter(Boolean).join('\n');
        payload.title = data.body || '';
      } else {
        payload.content = data.body || '';
        payload.title = data.title || '';
      }
      const doCreate = fileList && fileList.length > 0 ? api.createPostWithFiles(payload, fileList) : api.createPost(payload);
      doCreate.then(() => api.loadFeed({
        page: 1,
        tab: 'for-you',
        sort: 'latest'
      })).then(() => {
        onSubmit({
          kind,
          game,
          vis,
          data
        });
        onClose();
      }).catch(() => {
        onSubmit({
          kind,
          game,
          vis,
          data
        });
        onClose();
      }).finally(() => setPublishing(false));
    };
    const myTournaments = window.DC.MY_TOURNAMENTS || [];
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-modal-backdrop",
      onClick: onClose
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-modal",
      onClick: e => e.stopPropagation(),
      role: "dialog",
      "aria-modal": "true"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-modal-hd"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-3"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "font-display font-bold text-white text-base"
    }, "Create post"), /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-white/30"
    }, kind.toUpperCase())), /*#__PURE__*/React.createElement("button", {
      className: "w-9 h-9 rounded-lg hover:bg-white/5 text-white/40 hover:text-white grid place-items-center",
      onClick: onClose,
      "aria-label": "Close"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-xmark"
    }))), /*#__PURE__*/React.createElement("div", {
      className: "px-5 pt-4"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-type-tabs"
    }, COMPOSE_TYPES.map(tp => /*#__PURE__*/React.createElement("button", {
      key: tp.id,
      onClick: () => setKind(tp.id),
      className: `dc-type-tab ${kind === tp.id ? 'is-active' : ''}`,
      title: tp.hint
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${tp.icon}`
    }), /*#__PURE__*/React.createElement("span", null, tp.label)))), /*#__PURE__*/React.createElement("div", {
      className: "text-[11px] text-white/40 mt-2 text-center"
    }, (COMPOSE_TYPES.find(t => t.id === kind) || {}).hint)), /*#__PURE__*/React.createElement("div", {
      className: "dc-modal-bd"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-3 mb-4 p-2.5 rounded-xl bg-white/[.025] border border-white/[.05]"
    }, isTeam && team ? /*#__PURE__*/React.createElement("div", {
      className: "w-9 h-9 rounded-lg overflow-hidden shrink-0",
      style: {
        background: `linear-gradient(135deg, ${team.color || '#7B2BFF'}, var(--dc-accent-2))`
      }
    }, team.logo_url ? /*#__PURE__*/React.createElement("img", {
      src: team.logo_url,
      alt: team.name,
      className: "w-full h-full object-cover"
    }) : /*#__PURE__*/React.createElement("div", {
      className: "dc-team-crest"
    }, team.tag)) : Avatar && window.DC.ME ? /*#__PURE__*/React.createElement(Avatar, {
      user: window.DC.ME,
      size: 36
    }) : null, /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-[13px] font-semibold text-white flex items-center gap-1"
    }, isTeam && team ? team.name : window.DC.ME ? window.DC.ME.name : 'You', !isTeam && window.DC.ME && window.DC.ME.verified && VerifiedTick ? /*#__PURE__*/React.createElement(VerifiedTick, null) : null), /*#__PURE__*/React.createElement("div", {
      className: "text-[10.5px] text-white/45 flex items-center gap-1.5"
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${(VISIBILITY.find(v => v.id === vis) || {}).icon || 'globe'} text-[9px]`
    }), (VISIBILITY.find(v => v.id === vis) || {}).label, /*#__PURE__*/React.createElement("span", {
      className: "w-1 h-1 rounded-full bg-white/30"
    }), isTeam && team ? `Posting as ${identity.role}` : `@${window.DC.ME ? window.DC.ME.handle : 'you'}`)), /*#__PURE__*/React.createElement("select", {
      value: vis,
      onChange: e => setVis(e.target.value),
      className: "dc-select w-auto text-[12px] py-1.5 pr-7 pl-2.5"
    }, VISIBILITY.map(v => /*#__PURE__*/React.createElement("option", {
      key: v.id,
      value: v.id
    }, v.label)))), /*#__PURE__*/React.createElement(TypeForm, {
      data: data,
      setData: setData,
      identity: identity,
      game: game
    }), kind !== 'recruit' && kind !== 'lft' && /*#__PURE__*/React.createElement("div", {
      className: "dc-field-row cols-2 mt-2"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Game"), /*#__PURE__*/React.createElement("select", {
      className: "dc-select",
      value: game,
      onChange: e => setGame(e.target.value)
    }, (window.DC.GAMES || []).map(g => /*#__PURE__*/React.createElement("option", {
      key: g.id,
      value: g.id
    }, g.name)))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Mentions & hashtags"), /*#__PURE__*/React.createElement("input", {
      className: "dc-input",
      placeholder: "@player  #ShowdownS3",
      value: data.tags || '',
      onChange: e => setData({
        ...data,
        tags: e.target.value
      })
    }))), myTournaments.length > 0 && kind !== 'recruit' && /*#__PURE__*/React.createElement("div", {
      className: "dc-field"
    }, /*#__PURE__*/React.createElement("label", {
      className: "dc-input-label"
    }, "Tag a tournament (optional)"), /*#__PURE__*/React.createElement(TagPicker, {
      kind: "tournament",
      value: data.taggedTournament || null,
      onChange: v => setData({
        ...data,
        taggedTournament: v,
        tournament_id: v ? v.id : null
      })
    }))), /*#__PURE__*/React.createElement("div", {
      className: "dc-modal-ft"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1 text-white/40"
    }, /*#__PURE__*/React.createElement("button", {
      className: "w-8 h-8 rounded-lg hover:bg-white/5 hover:text-dc-cyan grid place-items-center",
      title: "Image",
      onClick: () => setKind('image')
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-image"
    })), /*#__PURE__*/React.createElement("button", {
      className: "w-8 h-8 rounded-lg hover:bg-white/5 hover:text-dc-cyan grid place-items-center",
      title: "Clip",
      onClick: () => setKind('clip')
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-circle-play"
    })), /*#__PURE__*/React.createElement("button", {
      className: "w-8 h-8 rounded-lg hover:bg-white/5 hover:text-dc-cyan grid place-items-center",
      title: "Poll",
      onClick: () => setKind('poll')
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-square-poll-vertical"
    })), /*#__PURE__*/React.createElement("button", {
      className: "w-8 h-8 rounded-lg hover:bg-white/5 hover:text-dc-cyan grid place-items-center",
      title: "GIF"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-film"
    })), /*#__PURE__*/React.createElement("button", {
      className: "w-8 h-8 rounded-lg hover:bg-white/5 hover:text-dc-cyan grid place-items-center",
      title: "Emoji"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-regular fa-face-smile"
    }))), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 ml-auto"
    }, /*#__PURE__*/React.createElement("button", {
      className: "dc-btn-ghost px-3 py-1.5 rounded-lg text-xs",
      onClick: onClose
    }, "Cancel"), /*#__PURE__*/React.createElement("button", {
      onClick: handlePublish,
      disabled: !canSubmit || publishing,
      className: "dc-btn-accent px-5 py-2 rounded-lg text-xs disabled:opacity-30 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
    }, publishing ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "w-3 h-3 border-2 border-black/40 border-t-black rounded-full animate-spin"
    }), "Publishing\u2026") : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-paper-plane text-[10px]"
    }), "Publish"))))));
  }

  /* ---- Inline trigger ---- */
  function ComposerTrigger({
    identity,
    onOpen,
    isAuthed
  }) {
    if (!isAuthed) {
      return /*#__PURE__*/React.createElement("a", {
        href: "/account/login/?next=/community/",
        className: "dc-compose mb-5 flex items-center gap-3 no-underline"
      }, /*#__PURE__*/React.createElement("div", {
        className: "w-10 h-10 rounded-full bg-white/[.06] border border-white/[.08] grid place-items-center text-white/30"
      }, /*#__PURE__*/React.createElement("i", {
        className: "fa-solid fa-user text-sm"
      })), /*#__PURE__*/React.createElement("span", {
        className: "text-sm text-white/35"
      }, /*#__PURE__*/React.createElement("span", {
        className: "text-dc-cyan font-semibold"
      }, "Sign in"), " to post, like, and join the discussion"));
    }
    const isTeam = identity && identity.kind === 'team';
    const team = isTeam ? (window.DC.TEAMS || []).find(t => t.id === identity.teamId) : null;
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-compose mb-5",
      onClick: () => onOpen('text')
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-3"
    }, isTeam && team ? /*#__PURE__*/React.createElement("div", {
      className: "shrink-0 w-10 h-10 rounded-xl overflow-hidden ring-1 ring-white/10",
      style: {
        background: `linear-gradient(135deg, ${team.color || '#7B2BFF'}, var(--dc-accent-2))`
      }
    }, team.logo_url ? /*#__PURE__*/React.createElement("img", {
      src: team.logo_url,
      alt: team.name,
      className: "w-full h-full object-cover"
    }) : /*#__PURE__*/React.createElement("div", {
      className: "dc-team-crest"
    }, team.tag)) : Avatar && window.DC.ME ? /*#__PURE__*/React.createElement(Avatar, {
      user: window.DC.ME,
      size: 40
    }) : null, /*#__PURE__*/React.createElement("div", {
      className: "flex-1 text-sm text-white/35"
    }, isTeam && team ? `Post as ${team.name}…` : 'Share a highlight, start a discussion, or post a clip…'), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1",
      onClick: e => e.stopPropagation()
    }, [['image', 'fa-regular fa-image', 'Image'], ['clip', 'fa-solid fa-circle-play', 'Clip'], ['poll', 'fa-solid fa-square-poll-vertical', 'Poll'], ['lft', 'fa-solid fa-signal', 'LFT'], ['recruit', 'fa-solid fa-user-plus', 'Recruit']].map(([k, ic, lb]) => /*#__PURE__*/React.createElement("button", {
      key: k,
      className: "w-9 h-9 rounded-lg hover:bg-white/5 text-white/35 hover:text-dc-cyan grid place-items-center",
      title: lb,
      onClick: () => onOpen(k)
    }, /*#__PURE__*/React.createElement("i", {
      className: ic
    }))))));
  }
  Object.assign(window, {
    ComposerModal,
    ComposerTrigger,
    COMPOSE_TYPES,
    POLL_TYPES
  });
})();
