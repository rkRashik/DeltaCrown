/* DeltaCrown Community — sidebars + widgets. */
(function () {
  const {
    useState: useStateR,
    useEffect: useEffectR
  } = React;

  /* Returns how many rail items to show based on viewport width.
     Right rail is visible at xl+ (1280px). Clamps to [min, 10]. */
  function useRailCount(min = 3, max = 10) {
    const calc = () => {
      const w = typeof window !== 'undefined' ? window.innerWidth : 1280;
      if (w >= 1920) return 8; // very large / 4K
      if (w >= 1536) return 6; // 2xl
      return 5; // xl default
    };
    const [n, setN] = useStateR(calc);
    useEffectR(() => {
      const h = () => setN(calc());
      window.addEventListener('resize', h, {
        passive: true
      });
      return () => window.removeEventListener('resize', h);
    }, []);
    return Math.max(min, Math.min(max, n));
  }

  /* Reorder games:
     1. UserProfile.primary_game (signature game from settings)
     2. Games from game passports (in passport sort order, skip duplicates)
     3. All remaining games
  */
  function orderedGames() {
    const all = window.DC.GAMES || [];
    const primarySlug = window.DC.PRIMARY_GAME_SLUG || '';
    const passports = window.DC.MY_PASSPORTS || [];
    const pSlugs = passports.map(p => p.game_slug).filter(s => s && s !== primarySlug);
    const primary = primarySlug ? all.filter(g => g.id === primarySlug) : [];
    const fromPassport = pSlugs.map(s => all.find(g => g.id === s)).filter(Boolean);
    const usedSlugs = new Set([primarySlug, ...pSlugs].filter(Boolean));
    const rest = all.filter(g => !usedSlugs.has(g.id));
    return [...primary, ...fromPassport, ...rest];
  }
  /* Pull card atoms exported by cards.js into this scope. */
  const Avatar = window.Avatar;
  const VerifiedTick = window.VerifiedTick;
  const GameHex = window.GameHex;
  function IdentityCard({
    identity,
    setIdentity
  }) {
    const [open, setOpen] = useStateR(false);
    const ids = window.DC.MY_IDENTITIES || [];
    const teams = (window.DC.TEAMS || []).reduce((acc, t) => {
      acc[t.id] = t;
      return acc;
    }, {});
    const current = identity || ids[0];
    if (!current) return null;
    const isTeam = current.kind === 'team';
    const team = isTeam ? teams[current.teamId] : null;
    return /*#__PURE__*/React.createElement("div", {
      className: "relative"
    }, /*#__PURE__*/React.createElement("button", {
      className: "dc-identity",
      onClick: () => setOpen(o => !o)
    }, isTeam && team ? /*#__PURE__*/React.createElement("div", {
      className: "shrink-0 w-10 h-10 rounded-xl overflow-hidden ring-1 ring-white/10",
      style: {
        background: `linear-gradient(135deg, ${team.color}, var(--dc-accent-2))`
      }
    }, team.logo_url ? /*#__PURE__*/React.createElement("img", {
      src: team.logo_url,
      alt: team.name,
      className: "w-full h-full object-cover"
    }) : /*#__PURE__*/React.createElement("div", {
      className: "dc-team-crest"
    }, team.tag)) : /*#__PURE__*/React.createElement(Avatar, {
      user: window.DC.ME,
      size: 40
    }), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1"
    }, /*#__PURE__*/React.createElement("span", {
      className: "font-semibold text-sm text-white truncate"
    }, isTeam && team ? team.name : window.DC.ME.name), !isTeam && window.DC.ME.verified && /*#__PURE__*/React.createElement(VerifiedTick, null)), /*#__PURE__*/React.createElement("div", {
      className: "text-[10.5px] text-white/45 truncate flex items-center gap-1"
    }, /*#__PURE__*/React.createElement("span", null, isTeam && team ? `Posting as ${team.name}` : `@${window.DC.ME.handle}`), isTeam && /*#__PURE__*/React.createElement("span", {
      className: "px-1 py-px rounded bg-white/10 text-[8px] font-bold text-white/70"
    }, (current.role || '').toUpperCase()))), /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-chevron-down text-[10px] text-white/30 transition ${open ? 'rotate-180' : ''}`
    })), open && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "fixed inset-0 z-30",
      onClick: () => setOpen(false)
    }), /*#__PURE__*/React.createElement("div", {
      className: "dc-identity-pop absolute left-0 right-0 top-full mt-2 z-40 dc-fade-in"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/35 px-2 py-1.5"
    }, "Post as"), ids.map(opt => {
      const isOptTeam = opt.kind === 'team';
      const oTeam = isOptTeam ? teams[opt.teamId] : null;
      const isActive = opt.id === current.id;
      return /*#__PURE__*/React.createElement("button", {
        key: opt.id,
        disabled: !opt.canPost,
        onClick: () => {
          if (opt.canPost) {
            setIdentity(opt);
            setOpen(false);
          }
        },
        className: `dc-identity-opt ${isActive ? 'is-active' : ''} ${!opt.canPost ? 'is-disabled' : ''}`
      }, isOptTeam && oTeam ? /*#__PURE__*/React.createElement("div", {
        className: "shrink-0 w-9 h-9 rounded-lg overflow-hidden ring-1 ring-white/10",
        style: {
          background: `linear-gradient(135deg, ${oTeam.color}, var(--dc-accent-2))`
        }
      }, oTeam.logo_url ? /*#__PURE__*/React.createElement("img", {
        src: oTeam.logo_url,
        alt: oTeam.name,
        className: "w-full h-full object-cover"
      }) : /*#__PURE__*/React.createElement("div", {
        className: "dc-team-crest"
      }, oTeam.tag)) : /*#__PURE__*/React.createElement(Avatar, {
        user: window.DC.ME,
        size: 36
      }), /*#__PURE__*/React.createElement("div", {
        className: "flex-1 min-w-0 text-left"
      }, /*#__PURE__*/React.createElement("div", {
        className: "flex items-center gap-1"
      }, /*#__PURE__*/React.createElement("span", {
        className: "text-[13px] font-semibold text-white truncate"
      }, isOptTeam && oTeam ? oTeam.name : window.DC.ME.name), isActive && /*#__PURE__*/React.createElement("i", {
        className: "fa-solid fa-check text-dc-cyan text-[10px] ml-auto"
      })), /*#__PURE__*/React.createElement("div", {
        className: "text-[10.5px] text-white/45 truncate"
      }, opt.canPost ? /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("span", {
        className: "text-dc-emerald"
      }, "\u25CF"), " ", opt.role, " \xB7 can post") : /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("i", {
        className: "fa-solid fa-lock text-[8px] mr-1"
      }), opt.role, " \xB7 view only"))));
    }), /*#__PURE__*/React.createElement("div", {
      className: "px-2 mt-1 pt-2 border-t border-white/[.05] text-[11px] text-white/40"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-circle-info text-[10px] mr-1"
    }), " Team posts require captain or co-leader role."))));
  }
  function LeftRail({
    activeView,
    setActiveView,
    activeGame,
    setActiveGame,
    identity,
    setIdentity,
    setTab,
    setSort
  }) {
    /* Each item maps to: activeView (local), tab (API filter), sort (API sort) */
    const items = [{
      id: 'for-you',
      label: 'For You',
      icon: 'wand-magic-sparkles',
      tab: 'for-you',
      sort: 'latest'
    }, {
      id: 'following',
      label: 'Following',
      icon: 'user-group',
      tab: 'following',
      sort: 'latest'
    }, {
      id: 'trending',
      label: 'Trending',
      icon: 'fire',
      tab: 'for-you',
      sort: 'hot'
    }, {
      id: 'highlights',
      label: 'Highlights',
      icon: 'circle-play',
      tab: 'highlights',
      sort: 'latest'
    }, {
      id: 'lft',
      label: 'LFT Board',
      icon: 'signal',
      tab: 'lft',
      sort: 'latest'
    }, {
      id: 'saved',
      label: 'Saved',
      icon: 'bookmark',
      tab: 'for-you',
      sort: 'latest'
    }];
    const games = orderedGames();
    const primarySlug = window.DC.PRIMARY_GAME_SLUG || '';
    const passportSlugs = (window.DC.MY_PASSPORTS || []).map(p => p.game_slug).filter(s => s !== primarySlug);
    const authed = window.DC_CONFIG && window.DC_CONFIG.isAuthenticated;
    const handleNavClick = it => {
      setActiveView(it.id);
      if (setTab) setTab(it.tab);
      if (setSort) setSort(it.sort);
    };
    return /*#__PURE__*/React.createElement("aside", {
      className: "dc-col-left w-[240px] shrink-0 hidden lg:block"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-rail-sticky space-y-5"
    }, authed && /*#__PURE__*/React.createElement(IdentityCard, {
      identity: identity,
      setIdentity: setIdentity
    }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/35 px-2 mb-2"
    }, "Feed"), /*#__PURE__*/React.createElement("nav", {
      className: "space-y-0.5"
    }, items.map(it => /*#__PURE__*/React.createElement("button", {
      key: it.id,
      onClick: () => handleNavClick(it),
      className: `dc-nav w-full ${activeView === it.id ? 'is-active' : ''}`
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-nav-ic"
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${it.icon}`
    })), /*#__PURE__*/React.createElement("span", {
      className: "flex-1 text-left"
    }, it.label))))), games.length > 0 && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center justify-between px-2 mb-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-white/35"
    }, "Game Channels")), /*#__PURE__*/React.createElement("nav", {
      className: "space-y-0.5"
    }, /*#__PURE__*/React.createElement("button", {
      onClick: () => setActiveGame(null),
      className: `dc-nav w-full ${!activeGame ? 'is-active' : ''}`
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-nav-ic"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-grip"
    })), /*#__PURE__*/React.createElement("span", {
      className: "flex-1 text-left"
    }, "All Games")), games.map((g, idx) => {
      const isPrimary = primarySlug ? g.id === primarySlug : false;
      const isPassport = !isPrimary && passportSlugs.includes(g.id);
      return /*#__PURE__*/React.createElement("button", {
        key: g.id,
        onClick: () => setActiveGame(g.id === activeGame ? null : g.id),
        className: `dc-nav w-full ${activeGame === g.id ? 'is-active' : ''}`
      }, /*#__PURE__*/React.createElement("span", {
        className: "w-5 h-5 rounded-md overflow-hidden ring-1 ring-white/10 shrink-0 bg-white/5 relative"
      }, g.logo && /*#__PURE__*/React.createElement("img", {
        src: g.logo,
        alt: g.name,
        className: "w-full h-full object-cover"
      })), /*#__PURE__*/React.createElement("span", {
        className: "flex-1 text-left truncate",
        title: g.name
      }, g.name), isPrimary ? /*#__PURE__*/React.createElement("span", {
        className: "shrink-0 text-[8px] font-black px-1 py-0.5 rounded leading-none",
        style: {
          background: 'rgba(0,229,255,0.15)',
          color: 'rgba(0,229,255,0.9)'
        }
      }, "MAIN") : isPassport ? /*#__PURE__*/React.createElement("i", {
        className: "fa-solid fa-id-card text-[8px] text-white/25 shrink-0",
        title: "In your passport"
      }) : g.online > 0 ? /*#__PURE__*/React.createElement("span", {
        className: "flex items-center gap-1 text-[10px] text-white/40"
      }, /*#__PURE__*/React.createElement("span", {
        className: "dc-online-dot"
      }), /*#__PURE__*/React.createElement("span", {
        className: "dc-mono"
      }, Math.round(g.online / 100) / 10, "k")) : null);
    })))));
  }
  function FeaturedTeamsCard() {
    const teams = window.DC.FEATURED_TEAMS || [];
    if (teams.length === 0) return null;
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-glass rounded-2xl overflow-hidden"
    }, /*#__PURE__*/React.createElement("div", {
      className: "px-4 py-3 border-b border-white/[.05] flex items-center justify-between"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-stripe font-display font-bold text-sm text-white"
    }, "Featured Teams"), /*#__PURE__*/React.createElement("a", {
      className: "text-[10px] text-white/40 hover:text-white",
      href: "/teams/"
    }, "All teams")), /*#__PURE__*/React.createElement("div", {
      className: "p-2 space-y-1"
    }, teams.slice(0, 6).map(t => /*#__PURE__*/React.createElement("a", {
      key: t.slug,
      href: `/teams/${t.slug}/`,
      className: "flex items-center gap-2.5 p-2 rounded-xl hover:bg-white/[.04] transition cursor-pointer"
    }, /*#__PURE__*/React.createElement("div", {
      className: "shrink-0 w-9 h-9 rounded-lg overflow-hidden ring-1 ring-white/10 bg-white/5 grid place-items-center text-[10px] font-bold text-white/70"
    }, t.logo_url ? /*#__PURE__*/React.createElement("img", {
      src: t.logo_url,
      alt: t.name,
      className: "w-full h-full object-cover"
    }) : t.tag || (t.name || '').slice(0, 3).toUpperCase()), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-[12.5px] font-semibold text-white truncate"
    }, t.name), /*#__PURE__*/React.createElement("div", {
      className: "text-[10.5px] text-white/45 truncate"
    }, t.game ? /*#__PURE__*/React.createElement("span", null, t.game) : null, t.member_count ? /*#__PURE__*/React.createElement("span", null, " \xB7 ", /*#__PURE__*/React.createElement("span", {
      className: "dc-mono"
    }, t.member_count), " members") : null))))));
  }
  function StatsCard() {
    const s = window.DC.SIDEBAR_STATS || {};
    if (!s.total_posts && !s.total_teams && !s.total_games) return null;
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-glass rounded-2xl overflow-hidden"
    }, /*#__PURE__*/React.createElement("div", {
      className: "px-4 py-3 border-b border-white/[.05] flex items-center gap-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-stripe font-display font-bold text-sm text-white"
    }, "Community Stats")), /*#__PURE__*/React.createElement("div", {
      className: "p-4 grid grid-cols-3 gap-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-center"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-counter-num text-lg text-white"
    }, (s.total_posts || 0).toLocaleString()), /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/35 text-[9px]"
    }, "Posts")), /*#__PURE__*/React.createElement("div", {
      className: "text-center"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-counter-num text-lg text-white"
    }, (s.total_teams || 0).toLocaleString()), /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/35 text-[9px]"
    }, "Teams")), /*#__PURE__*/React.createElement("div", {
      className: "text-center"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-counter-num text-lg text-white"
    }, (s.total_games || 0).toLocaleString()), /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/35 text-[9px]"
    }, "Games"))));
  }
  function DiscordCard() {
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-discord rounded-2xl p-4 relative overflow-hidden"
    }, /*#__PURE__*/React.createElement("div", {
      className: "absolute -top-4 -right-4 w-24 h-24 rounded-full",
      style: {
        background: 'radial-gradient(circle, rgba(88,101,242,0.4), transparent 70%)'
      }
    }), /*#__PURE__*/React.createElement("div", {
      className: "relative"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2.5 mb-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-9 h-9 rounded-xl grid place-items-center",
      style: {
        background: '#5865F2'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-brands fa-discord text-white text-lg"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      className: "text-sm font-bold text-white"
    }, "DeltaCrown Discord"), /*#__PURE__*/React.createElement("div", {
      className: "text-[10.5px] text-white/55"
    }, "Voice channels, scrims, announcements."))), /*#__PURE__*/React.createElement("a", {
      href: "https://discord.gg/deltacrown",
      target: "_blank",
      rel: "noopener",
      className: "block w-full py-2 rounded-xl text-sm font-bold text-white text-center transition hover:brightness-110",
      style: {
        background: '#5865F2'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-brands fa-discord mr-2"
    }), " Join Server")));
  }

  /* ---- Live Streams ---- */
  function LiveStreamsCard({
    count = 5
  }) {
    const list = window.DC.LIVE_STREAMS || [];
    if (!list.length) return null;
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-glass rounded-2xl overflow-hidden"
    }, /*#__PURE__*/React.createElement("div", {
      className: "px-4 py-3 border-b border-white/[.05] flex items-center justify-between"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-stripe font-display font-bold text-sm text-white"
    }, "Live Now"), /*#__PURE__*/React.createElement("span", {
      className: "dc-live-dot"
    }), /*#__PURE__*/React.createElement("span", {
      className: "dc-mono text-[10px] text-dc-rose font-bold"
    }, list.length)), /*#__PURE__*/React.createElement("a", {
      href: "/arena/",
      className: "text-[10px] text-white/40 hover:text-dc-cyan transition"
    }, "Arena ", /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-arrow-right text-[8px] ml-0.5"
    }))), /*#__PURE__*/React.createElement("div", {
      className: "p-2 space-y-0.5"
    }, list.slice(0, count).map(s => /*#__PURE__*/React.createElement("a", {
      key: s.id,
      href: s.url || '/arena/',
      target: "_blank",
      rel: "noopener",
      className: "flex items-center gap-2.5 p-2 rounded-xl hover:bg-white/[.04] transition cursor-pointer group"
    }, /*#__PURE__*/React.createElement("div", {
      className: "relative shrink-0"
    }, /*#__PURE__*/React.createElement(Avatar, {
      user: s.user || {
        name: s.channel || 'Stream',
        color1: '#7B2BFF',
        color2: '#00E5FF'
      },
      size: 36
    }), /*#__PURE__*/React.createElement("span", {
      className: "absolute -bottom-0.5 -right-0.5 px-1 py-0.5 rounded",
      style: {
        background: '#EF4444',
        color: 'white',
        fontSize: 7,
        fontWeight: 800,
        letterSpacing: '0.05em',
        lineHeight: 1.5
      }
    }, "LIVE")), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-[12.5px] font-semibold text-white truncate group-hover:text-dc-cyan transition"
    }, s.channel || s.title || 'Stream'), /*#__PURE__*/React.createElement("div", {
      className: "text-[10.5px] text-white/50 truncate"
    }, s.title || s.game || ''), s.viewers > 0 && /*#__PURE__*/React.createElement("div", {
      className: "dc-mono text-[10px] text-white/35 mt-0.5 flex items-center gap-1"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-live-dot",
      style: {
        width: 5,
        height: 5
      }
    }), s.viewers.toLocaleString(), " viewers"))))));
  }

  /* ---- Trending ---- */
  function TrendingCard({
    count = 5
  }) {
    const list = window.DC.TRENDING || [];
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-glass rounded-2xl overflow-hidden"
    }, /*#__PURE__*/React.createElement("div", {
      className: "px-4 py-3 border-b border-white/[.05] flex items-center justify-between"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-stripe font-display font-bold text-sm text-white"
    }, "Trending"), /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-fire text-dc-rose text-xs"
    })), /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-white/30 text-[9px]"
    }, "LAST 30 DAYS")), list.length === 0 ? /*#__PURE__*/React.createElement("div", {
      className: "flex flex-col items-center py-7 px-4 gap-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-10 h-10 rounded-xl grid place-items-center mb-1",
      style: {
        background: 'rgba(239,68,68,0.08)',
        border: '1px solid rgba(239,68,68,0.15)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-fire text-dc-rose/50"
    })), /*#__PURE__*/React.createElement("p", {
      className: "text-[11px] text-white/30 text-center leading-relaxed"
    }, "Trending topics appear once community members start posting."), /*#__PURE__*/React.createElement("a", {
      href: "/community/",
      className: "mt-1 text-[11px] text-dc-cyan font-semibold hover:underline transition"
    }, "Be the first to post \u2192")) : /*#__PURE__*/React.createElement("div", {
      className: "p-2"
    }, list.slice(0, count).map((t, i) => /*#__PURE__*/React.createElement("div", {
      key: t.tag || i,
      className: "flex items-center justify-between gap-3 px-2 py-2.5 rounded-xl hover:bg-white/[.04] transition cursor-pointer group"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-3 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-6 h-6 rounded-lg grid place-items-center shrink-0 text-[11px] font-black dc-mono",
      style: {
        background: i < 3 ? `linear-gradient(135deg, rgba(var(--dc-accent-rgb),0.18), rgba(var(--dc-accent-2-rgb),0.1))` : 'rgba(255,255,255,0.04)',
        color: i < 3 ? 'var(--dc-accent)' : 'rgba(255,255,255,0.3)'
      }
    }, i + 1), /*#__PURE__*/React.createElement("div", {
      className: "min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-[13px] font-semibold text-white/90 group-hover:text-dc-cyan transition truncate"
    }, "#", t.tag), /*#__PURE__*/React.createElement("div", {
      className: "dc-mono text-[10px] text-white/35"
    }, (t.posts || 0).toLocaleString(), " posts"))), t.delta ? /*#__PURE__*/React.createElement("span", {
      className: "dc-mono text-[10px] font-bold text-dc-emerald shrink-0"
    }, t.delta) : i < 3 ? /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-arrow-trend-up text-[10px] text-dc-emerald/60 shrink-0"
    }) : null)), /*#__PURE__*/React.createElement("div", {
      className: "mx-2 mt-1 pt-2 border-t border-white/[.04]"
    }, /*#__PURE__*/React.createElement("a", {
      href: "/community/?tab=for-you&sort=hot",
      className: "flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-semibold text-white/40 hover:text-dc-cyan hover:bg-white/[.03] transition"
    }, "Explore trending ", /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-arrow-right text-[9px]"
    })))));
  }

  /* ---- Upcoming events ---- */
  function UpcomingCard({
    count = 5
  }) {
    const list = window.DC.UPCOMING || [];
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-glass rounded-2xl overflow-hidden"
    }, /*#__PURE__*/React.createElement("div", {
      className: "px-4 py-3 border-b border-white/[.05] flex items-center justify-between"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-stripe font-display font-bold text-sm text-white"
    }, "Upcoming"), /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-calendar-days text-white/30 text-xs"
    })), /*#__PURE__*/React.createElement("a", {
      href: "/tournaments/",
      className: "text-[10px] text-white/40 hover:text-dc-cyan transition"
    }, "Calendar ", /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-arrow-right text-[8px] ml-0.5"
    }))), list.length === 0 ? /*#__PURE__*/React.createElement("div", {
      className: "flex flex-col items-center py-7 px-4 gap-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-10 h-10 rounded-xl grid place-items-center mb-1",
      style: {
        background: 'rgba(var(--dc-accent-rgb),0.08)',
        border: '1px solid rgba(var(--dc-accent-rgb),0.15)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-calendar-days text-dc-cyan/50"
    })), /*#__PURE__*/React.createElement("p", {
      className: "text-[11px] text-white/30 text-center leading-relaxed"
    }, "No tournaments scheduled in the next 14 days."), /*#__PURE__*/React.createElement("a", {
      href: "/tournaments/",
      className: "mt-1 text-[11px] text-dc-cyan font-semibold hover:underline transition"
    }, "Browse all tournaments \u2192")) : /*#__PURE__*/React.createElement("div", {
      className: "p-2"
    }, list.slice(0, count).map(e => /*#__PURE__*/React.createElement("a", {
      key: e.id,
      href: e.url || '/tournaments/',
      className: "flex items-center gap-3 px-2 py-3 rounded-xl hover:bg-white/[.04] transition cursor-pointer group"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-11 shrink-0 rounded-xl overflow-hidden text-center",
      style: {
        border: '1px solid rgba(var(--dc-accent-rgb),0.2)'
      }
    }, /*#__PURE__*/React.createElement("div", {
      className: "py-1",
      style: {
        background: 'linear-gradient(180deg, rgba(var(--dc-accent-rgb),0.18) 0%, rgba(var(--dc-accent-rgb),0.06) 100%)'
      }
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-mono text-[8px] font-bold tracking-widest",
      style: {
        color: 'var(--dc-accent)'
      }
    }, e.day || '')), /*#__PURE__*/React.createElement("div", {
      className: "py-1.5 bg-white/[.02]"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-mono text-[12px] font-black text-white leading-none"
    }, (e.date || '').split(' ')[1] || e.date || '—'), /*#__PURE__*/React.createElement("div", {
      className: "dc-mono text-[8px] text-white/40 mt-0.5 font-semibold"
    }, (e.date || '').split(' ')[0] || ''))), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-[12.5px] font-semibold text-white leading-snug truncate group-hover:text-dc-cyan transition"
    }, e.title), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1.5 mt-1 flex-wrap"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-[9px] font-bold px-1.5 py-0.5 rounded dc-hud-label",
      style: {
        background: 'rgba(var(--dc-accent-2-rgb),0.12)',
        color: 'rgba(var(--dc-accent-2-rgb), 0.85)',
        border: '1px solid rgba(var(--dc-accent-2-rgb),0.2)'
      }
    }, e.kind || 'TOURNAMENT'), e.time && /*#__PURE__*/React.createElement("span", {
      className: "dc-mono text-[9px] text-white/35"
    }, e.time))), /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-chevron-right text-[9px] text-white/20 group-hover:text-dc-cyan transition shrink-0"
    }))), list.length > count && /*#__PURE__*/React.createElement("div", {
      className: "px-2 pt-1"
    }, /*#__PURE__*/React.createElement("a", {
      href: "/tournaments/",
      className: "flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-semibold text-white/40 hover:text-dc-cyan hover:bg-white/[.03] transition"
    }, list.length - count, " more ", /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-arrow-right text-[9px]"
    })))));
  }

  /* ---- LFT mini board ---- */
  function LftMiniCard({
    count = 5
  }) {
    const allPosts = window.DC.POSTS || [];
    /* Distribute count across lft + recruit proportionally */
    const lftMax = Math.ceil(count * 0.6);
    const recMax = Math.floor(count * 0.4);
    const lftPosts = allPosts.filter(p => p.type === 'lft').slice(0, lftMax);
    const recPosts = allPosts.filter(p => p.type === 'recruit').slice(0, recMax);
    const total = lftPosts.length + recPosts.length;
    const isAuthed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);
    const openLft = kind => {
      if (typeof window.dcCommunityCompose === 'function') window.dcCommunityCompose(kind);else window.dispatchEvent(new CustomEvent('dc-community-compose', {
        detail: kind
      }));
    };
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-glass rounded-2xl overflow-hidden"
    }, /*#__PURE__*/React.createElement("div", {
      className: "px-4 py-3 border-b border-white/[.05] flex items-center justify-between"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-stripe font-display font-bold text-sm text-white"
    }, "LFT Board"), total > 0 && /*#__PURE__*/React.createElement("span", {
      className: "text-[10px] font-bold px-1.5 py-0.5 rounded-md",
      style: {
        background: 'rgba(16,230,139,0.12)',
        color: '#10e68b',
        border: '1px solid rgba(16,230,139,0.25)'
      }
    }, total)), /*#__PURE__*/React.createElement("button", {
      onClick: () => {
        if (typeof window.dispatchEvent === 'function') window.dispatchEvent(new CustomEvent('dc-community-tab', {
          detail: 'lft'
        }));
      },
      className: "text-[10px] text-white/40 hover:text-dc-cyan transition"
    }, "View all ", /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-arrow-right text-[8px] ml-0.5"
    }))), total === 0 ? /*#__PURE__*/React.createElement("div", {
      className: "flex flex-col items-center py-7 px-4 gap-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-10 h-10 rounded-xl grid place-items-center mb-1",
      style: {
        background: 'rgba(16,230,139,0.08)',
        border: '1px solid rgba(16,230,139,0.15)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-signal text-dc-emerald/50"
    })), /*#__PURE__*/React.createElement("p", {
      className: "text-[11px] text-white/30 text-center leading-relaxed"
    }, "No active LFT posts yet. Be the first to post!"), isAuthed && /*#__PURE__*/React.createElement("div", {
      className: "flex gap-2 mt-1"
    }, /*#__PURE__*/React.createElement("button", {
      onClick: () => openLft('lft'),
      className: "flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-bold text-dc-emerald transition hover:bg-dc-emerald/10",
      style: {
        border: '1px solid rgba(16,230,139,0.25)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-signal text-[9px]"
    }), " I'm LFT"), /*#__PURE__*/React.createElement("button", {
      onClick: () => openLft('recruit'),
      className: "flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-bold transition hover:bg-white/5 text-white/50",
      style: {
        border: '1px solid rgba(255,255,255,0.1)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-user-plus text-[9px]"
    }), " Recruit"))) : /*#__PURE__*/React.createElement("div", {
      className: "p-2"
    }, lftPosts.length > 0 && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/25 px-2 py-1.5 text-[9px]"
    }, "LOOKING FOR TEAM"), lftPosts.map(p => {
      const lft = p.lft_data || {};
      const roles = Array.isArray(lft.roles) ? lft.roles.slice(0, 2).join(', ') : lft.roles || '';
      return /*#__PURE__*/React.createElement("div", {
        key: p.id,
        className: "flex items-center gap-2.5 px-2 py-2.5 rounded-xl hover:bg-white/[.04] transition cursor-pointer group"
      }, /*#__PURE__*/React.createElement(Avatar, {
        user: p.author,
        size: 32
      }), /*#__PURE__*/React.createElement("div", {
        className: "flex-1 min-w-0"
      }, /*#__PURE__*/React.createElement("div", {
        className: "text-[12.5px] font-semibold text-white truncate group-hover:text-dc-cyan transition"
      }, p.author.name), /*#__PURE__*/React.createElement("div", {
        className: "flex items-center gap-1.5 mt-0.5 flex-wrap"
      }, lft.rank && /*#__PURE__*/React.createElement("span", {
        className: "text-[9px] font-bold px-1.5 py-0.5 rounded dc-mono",
        style: {
          background: 'rgba(0,229,255,0.1)',
          color: 'rgba(0,229,255,0.8)'
        }
      }, lft.rank), roles && /*#__PURE__*/React.createElement("span", {
        className: "text-[10px] text-white/40 truncate"
      }, roles))), p.game && p.game.logo && /*#__PURE__*/React.createElement("img", {
        src: p.game.logo,
        className: "w-5 h-5 rounded shrink-0 opacity-60",
        alt: "",
        onError: e => {
          e.currentTarget.style.display = 'none';
        }
      }));
    })), recPosts.length > 0 && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-white/25 px-2 py-1.5 text-[9px] mt-1"
    }, "RECRUITING"), recPosts.map(p => {
      const lft = p.lft_data || {};
      const roles = Array.isArray(lft.roles) ? lft.roles.slice(0, 2).join(', ') : lft.roles || '';
      const teamName = p.team ? p.team.name : null;
      return /*#__PURE__*/React.createElement("div", {
        key: p.id,
        className: "flex items-center gap-2.5 px-2 py-2.5 rounded-xl hover:bg-white/[.04] transition cursor-pointer group"
      }, /*#__PURE__*/React.createElement(Avatar, {
        user: p.author,
        size: 32
      }), /*#__PURE__*/React.createElement("div", {
        className: "flex-1 min-w-0"
      }, /*#__PURE__*/React.createElement("div", {
        className: "text-[12.5px] font-semibold text-white truncate group-hover:text-dc-cyan transition"
      }, teamName || p.author.name), /*#__PURE__*/React.createElement("div", {
        className: "flex items-center gap-1.5 mt-0.5"
      }, /*#__PURE__*/React.createElement("span", {
        className: "text-[9px] font-bold px-1.5 py-0.5 rounded",
        style: {
          background: 'rgba(108,0,255,0.15)',
          color: 'rgba(155,89,255,0.9)'
        }
      }, "Recruiting"), roles && /*#__PURE__*/React.createElement("span", {
        className: "text-[10px] text-white/40 truncate"
      }, roles))), p.game && p.game.logo && /*#__PURE__*/React.createElement("img", {
        src: p.game.logo,
        className: "w-5 h-5 rounded shrink-0 opacity-60",
        alt: "",
        onError: e => {
          e.currentTarget.style.display = 'none';
        }
      }));
    })), isAuthed && /*#__PURE__*/React.createElement("div", {
      className: "flex gap-2 px-2 mt-2 pt-2 border-t border-white/[.04]"
    }, /*#__PURE__*/React.createElement("button", {
      onClick: () => openLft('lft'),
      className: "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-bold text-dc-emerald hover:bg-dc-emerald/8 transition",
      style: {
        border: '1px solid rgba(16,230,139,0.2)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-signal text-[9px]"
    }), " I'm LFT"), /*#__PURE__*/React.createElement("button", {
      onClick: () => openLft('recruit'),
      className: "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-bold text-white/50 hover:text-white hover:bg-white/5 transition",
      style: {
        border: '1px solid rgba(255,255,255,0.08)'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-user-plus text-[9px]"
    }), " Recruit"))));
  }

  /* ---- Right Rail ---- */
  function RightRail() {
    const count = useRailCount(3, 10); /* min 3 · responsive · max 10 */
    return /*#__PURE__*/React.createElement("aside", {
      className: "dc-col-right w-[300px] shrink-0 hidden xl:block"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-rail-sticky space-y-4"
    }, /*#__PURE__*/React.createElement(LiveStreamsCard, {
      count: count
    }), /*#__PURE__*/React.createElement(TrendingCard, {
      count: count
    }), /*#__PURE__*/React.createElement(LftMiniCard, {
      count: count
    }), /*#__PURE__*/React.createElement(UpcomingCard, {
      count: count
    }), /*#__PURE__*/React.createElement(FeaturedTeamsCard, null), /*#__PURE__*/React.createElement(StatsCard, null), /*#__PURE__*/React.createElement(DiscordCard, null), /*#__PURE__*/React.createElement("div", {
      className: "px-2 pb-2 text-[10px] text-white/25 flex items-center flex-wrap gap-x-3 gap-y-1"
    }, /*#__PURE__*/React.createElement("a", {
      className: "hover:text-white",
      href: "/about/"
    }, "About"), /*#__PURE__*/React.createElement("a", {
      className: "hover:text-white",
      href: "/legal/community-guidelines/"
    }, "Guidelines"), /*#__PURE__*/React.createElement("a", {
      className: "hover:text-white",
      href: "/support/"
    }, "Help"), /*#__PURE__*/React.createElement("span", {
      className: "ml-auto"
    }, "\xA9 DeltaCrown"))));
  }
  Object.assign(window, {
    IdentityCard,
    LeftRail,
    RightRail,
    StatsCard,
    FeaturedTeamsCard,
    DiscordCard,
    LiveStreamsCard,
    TrendingCard,
    UpcomingCard,
    LftMiniCard
  });
})();
