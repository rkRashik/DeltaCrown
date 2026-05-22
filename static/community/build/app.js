/* DeltaCrown Community — main app shell */
(function () {
  const {
    useState,
    useEffect,
    useRef,
    useMemo
  } = React;

  /* Error boundary — prevents blank page, shows the exact error in dev mode */
  class CommunityErrorBoundary extends React.Component {
    constructor(props) {
      super(props);
      this.state = {
        err: null
      };
    }
    static getDerivedStateFromError(e) {
      return {
        err: e
      };
    }
    componentDidCatch(e, info) {
      console.error('[Community] render error:', e, info.componentStack);
    }
    render() {
      if (!this.state.err) return this.props.children;
      return React.createElement('div', {
        style: {
          padding: '2rem',
          color: '#ccc',
          fontFamily: 'monospace',
          background: '#070712',
          minHeight: '100vh'
        }
      }, React.createElement('h3', {
        style: {
          color: '#EF4444',
          marginBottom: '1rem'
        }
      }, 'Community render error'), React.createElement('pre', {
        style: {
          whiteSpace: 'pre-wrap',
          fontSize: 12
        }
      }, String(this.state.err)), React.createElement('p', {
        style: {
          marginTop: '1rem',
          fontSize: 12,
          color: '#888'
        }
      }, 'Check the browser console for the full component stack.'));
    }
  }
  const Avatar = window.Avatar;
  const PostDispatcher = window.PostDispatcher;
  const LeftRail = window.LeftRail;
  const RightRail = window.RightRail;
  const useTweaks = window.useTweaks;
  const ComposerModal = window.ComposerModal;
  const ComposerTrigger = window.ComposerTrigger;
  const TWEAK_DEFAULTS = {
    accent: 'cyan',
    density: 'cozy',
    layout: '3col',
    background: 'aurora',
    showHero: true,
    showGameRail: true,
    animations: true,
    showFeedNav: false,
    /* secondary sticky feed-tabs bar (off by default; scroll transform handles it) */
    hideNavOnScroll: false /* completely hide nav on scroll-down (vs smart transform) */
  };
  const ACCENT_PALETTES = {
    cyan: {
      c1: '#00E5FF',
      c2: '#6C00FF',
      rgb1: '0, 229, 255',
      rgb2: '108, 0, 255'
    },
    violet: {
      c1: '#9B59FF',
      c2: '#FF4D9D',
      rgb1: '155, 89, 255',
      rgb2: '255, 77, 157'
    },
    gold: {
      c1: '#FFD700',
      c2: '#FF7A3B',
      rgb1: '255, 215, 0',
      rgb2: '255, 122, 59'
    },
    emerald: {
      c1: '#10B981',
      c2: '#00E5FF',
      rgb1: '16, 185, 129',
      rgb2: '0, 229, 255'
    },
    rose: {
      c1: '#EF4444',
      c2: '#6C00FF',
      rgb1: '239, 68, 68',
      rgb2: '108, 0, 255'
    },
    ice: {
      c1: '#7DD3FC',
      c2: '#C084FC',
      rgb1: '125, 211, 252',
      rgb2: '192, 132, 252'
    },
    magma: {
      c1: '#FF6B35',
      c2: '#FFD700',
      rgb1: '255, 107, 53',
      rgb2: '255, 215, 0'
    },
    arctic: {
      c1: '#A7F3D0',
      c2: '#7DD3FC',
      rgb1: '167, 243, 208',
      rgb2: '125, 211, 252'
    }
  };

  /* The community page uses the site's primary Django nav (customised for
     this route via dc_community_mode). The inline search input and "Post"
     button live in the Django nav and bridge to React via window events:
       dc-community-search   → updates `query` state
       dc-community-compose  → opens the compose modal
  */
  /* ============================================================
     Pulse strip
     ============================================================ */
  function PulseBand({
    identity,
    stats
  }) {
    const isTeam = identity && identity.kind === 'team';
    const team = isTeam ? (window.DC.TEAMS || []).find(t => t.id === identity.teamId) : null;
    const greetName = isTeam && team ? team.name : window.DC.ME && window.DC.ME.name ? window.DC.ME.name.split(' ')[0] : 'there';
    const hasStats = stats && (stats.total_posts || stats.total_teams);
    return /*#__PURE__*/React.createElement("section", {
      className: "dc-pulse-bar dc-fade-in dc-scanlines mb-5"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-corner-tick tl"
    }), /*#__PURE__*/React.createElement("div", {
      className: "dc-corner-tick tr"
    }), /*#__PURE__*/React.createElement("div", {
      className: "dc-corner-tick bl"
    }), /*#__PURE__*/React.createElement("div", {
      className: "dc-corner-tick br"
    }), /*#__PURE__*/React.createElement("div", {
      className: "px-4 sm:px-5 py-3.5 flex items-center gap-4 flex-wrap"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2.5 shrink-0"
    }, /*#__PURE__*/React.createElement("span", {
      className: "dc-live-dot"
    }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      className: "dc-hud-label text-dc-cyan text-[9px]"
    }, "PULSE \xB7 LIVE"), /*#__PURE__*/React.createElement("div", {
      className: "text-[13px] text-white/75 font-medium leading-tight"
    }, "Hi, ", /*#__PURE__*/React.createElement("span", {
      className: "text-white font-semibold"
    }, greetName), ' ', "\xB7 ", /*#__PURE__*/React.createElement("span", {
      className: "text-dc-emerald font-semibold"
    }, "welcome back")))), hasStats && /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 ml-auto flex-wrap"
    }, stats.total_posts > 0 && /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white/[.025] border border-white/[.05]"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-comment-dots text-[10px]",
      style: {
        color: 'var(--dc-accent)'
      }
    }), /*#__PURE__*/React.createElement("span", {
      className: "dc-counter-num text-sm text-white"
    }, stats.total_posts.toLocaleString()), /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-white/40 text-[8.5px]"
    }, "Posts")), stats.total_teams > 0 && /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white/[.025] border border-white/[.05]"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-users text-[10px]",
      style: {
        color: 'var(--dc-accent-2)'
      }
    }), /*#__PURE__*/React.createElement("span", {
      className: "dc-counter-num text-sm text-white"
    }, stats.total_teams.toLocaleString()), /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-white/40 text-[8.5px]"
    }, "Teams")), stats.total_games > 0 && /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white/[.025] border border-white/[.05]"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-gamepad text-[10px]",
      style: {
        color: 'var(--dc-gold)'
      }
    }), /*#__PURE__*/React.createElement("span", {
      className: "dc-counter-num text-sm text-white"
    }, stats.total_games), /*#__PURE__*/React.createElement("span", {
      className: "dc-hud-label text-white/40 text-[8.5px]"
    }, "Games")))));
  }

  /* ============================================================
     Game channel rail — uses banner/card images per design
     ============================================================ */
  function GameChannelRail({
    activeGame,
    setActiveGame
  }) {
    const allGames = window.DC.GAMES || [];
    const primarySlug = window.DC.PRIMARY_GAME_SLUG || '';
    const passports = window.DC.MY_PASSPORTS || [];
    /* Sort: 1. UserProfile.primary_game  2. passport games (no dupe)  3. others */
    const pSlugs = passports.map(p => p.game_slug).filter(s => s && s !== primarySlug);
    const primaryGame = primarySlug ? allGames.filter(g => g.id === primarySlug) : [];
    const pGames = pSlugs.map(s => allGames.find(g => g.id === s)).filter(Boolean);
    const used = new Set([primarySlug, ...pSlugs].filter(Boolean));
    const otherGames = allGames.filter(g => !used.has(g.id));
    const games = [...primaryGame, ...pGames, ...otherGames];
    if (games.length === 0) return null;
    return /*#__PURE__*/React.createElement("section", {
      className: "mt-6"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center justify-between mb-3"
    }, /*#__PURE__*/React.createElement("h2", {
      className: "dc-stripe font-display font-bold text-base text-white"
    }, "Game Channels")), /*#__PURE__*/React.createElement("div", {
      className: "dc-rail"
    }, games.map((g, idx) => {
      const isPrimary = primarySlug ? g.id === primarySlug : false;
      const isPassport = !isPrimary && pSlugs.includes(g.id);
      const banner = g.card_image_url || g.banner_url || g.logo;
      return /*#__PURE__*/React.createElement("button", {
        key: g.id,
        onClick: () => setActiveGame(g.id === activeGame ? null : g.id),
        className: `relative w-[200px] sm:w-[220px] rounded-2xl overflow-hidden border transition group ${activeGame === g.id ? 'border-dc-cyan shadow-[0_0_0_2px_rgba(0,229,255,0.2)]' : 'border-white/[.06] hover:border-white/[.15]'}`
      }, /*#__PURE__*/React.createElement("div", {
        className: "aspect-[5/3] relative overflow-hidden bg-white/[.03]"
      }, /*#__PURE__*/React.createElement("div", {
        className: "absolute inset-0",
        style: {
          background: `linear-gradient(135deg, ${g.color}25, ${g.color}05)`
        }
      }), banner && /*#__PURE__*/React.createElement("img", {
        src: banner,
        alt: g.name,
        className: "absolute inset-0 w-full h-full object-cover opacity-70 group-hover:opacity-90",
        style: {
          transition: 'transform .4s ease, opacity .3s'
        },
        onError: e => {
          e.currentTarget.style.display = 'none';
        }
      }), /*#__PURE__*/React.createElement("div", {
        className: "absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent"
      }), g.online > 0 && /*#__PURE__*/React.createElement("div", {
        className: "absolute top-2 right-2 px-2 py-0.5 rounded-md bg-black/55 backdrop-blur-sm text-[9px] font-bold flex items-center gap-1 text-white"
      }, /*#__PURE__*/React.createElement("span", {
        className: "dc-online-dot",
        style: {
          width: 5,
          height: 5
        }
      }), /*#__PURE__*/React.createElement("span", {
        className: "dc-mono"
      }, Math.round(g.online / 100) / 10 || 0, "k"))), /*#__PURE__*/React.createElement("div", {
        className: "px-3 py-2.5 text-left bg-dc-surface"
      }, /*#__PURE__*/React.createElement("div", {
        className: "flex items-center gap-1.5 mb-0.5"
      }, /*#__PURE__*/React.createElement("div", {
        className: "text-sm font-bold text-white truncate flex-1"
      }, g.name), isPrimary && /*#__PURE__*/React.createElement("span", {
        className: "shrink-0 text-[8px] font-black px-1.5 py-0.5 rounded-md leading-none",
        style: {
          background: 'rgba(0,229,255,0.15)',
          color: 'rgba(0,229,255,0.9)',
          border: '1px solid rgba(0,229,255,0.2)'
        }
      }, "MAIN"), isPassport && !isPrimary && /*#__PURE__*/React.createElement("i", {
        className: "fa-solid fa-id-card text-[9px] text-white/30 shrink-0",
        title: "In your passport"
      })), /*#__PURE__*/React.createElement("div", {
        className: "flex items-center justify-between"
      }, /*#__PURE__*/React.createElement("span", {
        className: "dc-mono text-[10px] text-white/45"
      }, (g.members || 0).toLocaleString(), " members"), /*#__PURE__*/React.createElement("span", {
        className: "text-[10px] text-dc-cyan group-hover:translate-x-0.5 transition-transform"
      }, activeGame === g.id ? 'Active' : 'Join', " ", /*#__PURE__*/React.createElement("i", {
        className: "fa-solid fa-arrow-right ml-1 text-[8px]"
      })))));
    })));
  }

  /* ============================================================
     Feed tabs — sticky flush below the nav (top: 80px = nav height).
     Must be the first child of main for zero gap.
     ============================================================ */
  function FeedTabs({
    tab,
    setTab,
    sort,
    setSort
  }) {
    const tabs = [{
      id: 'for-you',
      label: 'For You',
      icon: 'sparkles'
    }, {
      id: 'following',
      label: 'Following',
      icon: 'user-group'
    }, {
      id: 'highlights',
      label: 'Highlights',
      icon: 'circle-play'
    }, {
      id: 'lft',
      label: 'LFT Board',
      icon: 'signal'
    }];
    return /*#__PURE__*/React.createElement("div", {
      className: "flex items-center justify-between sticky z-20 -mx-4 sm:-mx-6 px-4 sm:px-6",
      style: {
        top: 80,
        borderRadius: 0,
        marginBottom: 20,
        background: 'rgba(5,5,16,0.97)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        backdropFilter: 'blur(20px)',
        height: 44
      }
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1 sm:gap-2 overflow-x-auto no-scrollbar h-full"
    }, tabs.map(t => /*#__PURE__*/React.createElement("button", {
      key: t.id,
      onClick: () => setTab(t.id),
      className: `dc-tab whitespace-nowrap flex items-center gap-1.5 text-[13px] h-full px-3 ${tab === t.id ? 'is-active' : ''}`
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${t.icon} text-[10px]`
    }), t.label))), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1 flex-shrink-0"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-[10px] text-white/30 hidden sm:block"
    }, "Sort:"), /*#__PURE__*/React.createElement("div", {
      className: "dc-seg"
    }, /*#__PURE__*/React.createElement("button", {
      className: sort === 'latest' ? 'is-active' : '',
      onClick: () => setSort('latest')
    }, "Latest"), /*#__PURE__*/React.createElement("button", {
      className: sort === 'top' ? 'is-active' : '',
      onClick: () => setSort('top')
    }, "Top"), /*#__PURE__*/React.createElement("button", {
      className: sort === 'hot' ? 'is-active' : '',
      onClick: () => setSort('hot')
    }, "Hot"))));
  }

  /* ============================================================
     Notifications drawer
     ============================================================ */
  function NotificationsDrawer({
    open,
    onClose
  }) {
    if (!open) return null;
    const items = window.DC.NOTIFICATIONS || [];
    return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "fixed inset-0 z-40 dc-overlay",
      onClick: onClose
    }), /*#__PURE__*/React.createElement("div", {
      className: "fixed top-0 right-0 bottom-0 w-full sm:w-[400px] z-[160] dc-glass-strong border-l border-white/[.06] dc-drawer flex flex-col"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center justify-between p-4 border-b border-white/[.06]"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h3", {
      className: "font-display font-bold text-white"
    }, "Notifications"), /*#__PURE__*/React.createElement("div", {
      className: "text-[11px] text-white/40 mt-0.5"
    }, items.filter(n => n.unread).length, " new")), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1"
    }, /*#__PURE__*/React.createElement("button", {
      className: "px-3 py-1.5 text-xs text-white/50 hover:text-white"
    }, "Mark all read"), /*#__PURE__*/React.createElement("button", {
      onClick: onClose,
      className: "w-9 h-9 rounded-lg hover:bg-white/5 text-white/50 grid place-items-center"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-xmark"
    })))), /*#__PURE__*/React.createElement("div", {
      className: "dc-seg mx-4 mt-3 self-start"
    }, /*#__PURE__*/React.createElement("button", {
      className: "is-active"
    }, "All"), /*#__PURE__*/React.createElement("button", null, "Mentions"), /*#__PURE__*/React.createElement("button", null, "Events")), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 overflow-y-auto p-3 space-y-1"
    }, items.length === 0 && /*#__PURE__*/React.createElement("div", {
      className: "text-center text-white/45 text-sm py-12"
    }, "You're all caught up."), items.map(n => /*#__PURE__*/React.createElement("div", {
      key: n.id,
      className: `flex items-start gap-3 p-3 rounded-xl cursor-pointer transition ${n.unread ? 'bg-dc-cyan/5' : 'hover:bg-white/[.03]'}`
    }, n.user ? /*#__PURE__*/React.createElement(Avatar, {
      user: n.user,
      size: 36
    }) : /*#__PURE__*/React.createElement("div", {
      className: "w-9 h-9 rounded-full bg-dc-gold/15 grid place-items-center text-dc-gold"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-trophy text-sm"
    })), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 min-w-0"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-[13px] leading-snug text-white"
    }, n.user && /*#__PURE__*/React.createElement("span", {
      className: "font-semibold"
    }, n.user.name, " "), /*#__PURE__*/React.createElement("span", {
      className: "text-white/65"
    }, n.text)), /*#__PURE__*/React.createElement("div", {
      className: "text-[10px] text-white/35 mt-1"
    }, n.ago)), n.unread && /*#__PURE__*/React.createElement("span", {
      className: "w-2 h-2 rounded-full bg-dc-cyan mt-2 shrink-0"
    }))))));
  }

  /* ============================================================
     Mobile nav drawer
     ============================================================ */
  function MobileNav({
    open,
    onClose,
    activeView,
    setActiveView,
    activeGame,
    setActiveGame,
    identity,
    setIdentity,
    setTab,
    setSort
  }) {
    if (!open) return null;
    return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "fixed inset-0 z-[155] dc-overlay",
      onClick: onClose
    }), /*#__PURE__*/React.createElement("div", {
      className: "fixed top-0 left-0 bottom-0 w-[280px] z-[160] dc-glass-strong border-r border-white/[.06] overflow-y-auto p-4"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center justify-between mb-4"
    }, /*#__PURE__*/React.createElement("span", {
      className: "font-display font-bold text-white"
    }, "Menu"), /*#__PURE__*/React.createElement("button", {
      onClick: onClose,
      className: "w-9 h-9 rounded-lg hover:bg-white/5 text-white/50 grid place-items-center"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-xmark"
    }))), /*#__PURE__*/React.createElement(LeftRail, {
      activeView: activeView,
      setActiveView: v => {
        setActiveView(v);
        onClose();
      },
      activeGame: activeGame,
      setActiveGame: g => {
        setActiveGame(g);
        onClose();
      },
      identity: identity,
      setIdentity: setIdentity,
      setTab: setTab,
      setSort: setSort
    })));
  }

  /* NavTabsPortal — renders the FeedTabs into the #cnav-tabs-portal slot in the
     Django-rendered primary nav. Shows when the nav is in scrolled/transform state.
     Uses ReactDOM.createPortal so React manages the tabs while they live in the nav. */
  function NavTabsPortal({
    tab,
    setTab,
    sort,
    setSort
  }) {
    const [slot, setSlot] = useState(null);
    useEffect(() => {
      setSlot(document.getElementById('cnav-tabs-portal'));
    }, []);
    if (!slot) return null;
    const tabs = [{
      id: 'for-you',
      label: 'For You',
      icon: 'sparkles'
    }, {
      id: 'following',
      label: 'Following',
      icon: 'user-group'
    }, {
      id: 'highlights',
      label: 'Highlights',
      icon: 'circle-play'
    }, {
      id: 'lft',
      label: 'LFT Board',
      icon: 'signal'
    }];
    /* Tabs only — no sort here (sort lives in the FeedTabs second bar or left rail).
       Centered with justify-content: center for clean alignment. */
    const content = /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '2px',
        height: '100%',
        width: '100%'
      }
    }, tabs.map(t => /*#__PURE__*/React.createElement("button", {
      key: t.id,
      onClick: () => setTab(t.id),
      className: `cnav-tab-btn${tab === t.id ? ' is-active' : ''}`
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${t.icon}`,
      style: {
        fontSize: 11
      }
    }), /*#__PURE__*/React.createElement("span", null, t.label))));
    return ReactDOM.createPortal(content, slot);
  }
  function EmptyState({
    title,
    sub,
    icon = 'inbox',
    cta
  }) {
    return /*#__PURE__*/React.createElement("div", {
      className: "dc-card dc-card-pad py-16 text-center dc-fade-in"
    }, /*#__PURE__*/React.createElement("div", {
      className: "w-16 h-16 rounded-2xl mx-auto mb-4 grid place-items-center",
      style: {
        background: 'linear-gradient(135deg, rgba(var(--dc-accent-rgb),0.1), rgba(var(--dc-accent-2-rgb),0.1))'
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: `fa-solid fa-${icon} text-2xl text-white/40`
    })), /*#__PURE__*/React.createElement("h3", {
      className: "font-display font-bold text-white"
    }, title), /*#__PURE__*/React.createElement("p", {
      className: "text-sm text-white/45 mt-1 mb-4 max-w-md mx-auto"
    }, sub), cta && /*#__PURE__*/React.createElement("button", {
      className: "dc-btn-accent inline-flex items-center gap-2 px-5 py-2 rounded-xl text-sm"
    }, cta));
  }
  function FeedSkeleton() {
    return /*#__PURE__*/React.createElement("div", {
      className: "space-y-4"
    }, [1, 2, 3].map(i => /*#__PURE__*/React.createElement("div", {
      key: i,
      className: "dc-card dc-card-pad"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-3 mb-3"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-skel rounded-full",
      style: {
        width: 42,
        height: 42
      }
    }), /*#__PURE__*/React.createElement("div", {
      className: "flex-1 space-y-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "dc-skel h-3 w-32"
    }), /*#__PURE__*/React.createElement("div", {
      className: "dc-skel h-2 w-20"
    }))), /*#__PURE__*/React.createElement("div", {
      className: "dc-skel h-3 w-full mb-2"
    }), /*#__PURE__*/React.createElement("div", {
      className: "dc-skel h-3 w-3/4"
    }))));
  }

  /* ============================================================
     Main App
     ============================================================ */
  function App() {
    const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
    const [identity, setIdentity] = useState(() => window.DC && window.DC.MY_IDENTITIES ? window.DC.MY_IDENTITIES[0] : null);
    const [activeView, setActiveView] = useState('for-you');
    const [activeGame, setActiveGame] = useState(null);
    const [tab, setTab] = useState('for-you');
    const [sort, setSort] = useState('latest');
    const [query, setQuery] = useState('');
    const [notifOpen, setNotifOpen] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [composeOpen, setComposeOpen] = useState(false);
    const [composeKind, setComposeKind] = useState('text');
    const [posts, setPosts] = useState([]);
    const [postsLoaded, setPostsLoaded] = useState(false);
    const [feedLoading, setFeedLoading] = useState(false);
    const [stats, setStats] = useState({});
    const [loadCount, setLoadCount] = useState(0);
    const [, forceUpdate] = useState(0);
    const refresh = () => forceUpdate(n => n + 1);
    const openCompose = kind => {
      setComposeKind(kind || 'text');
      setComposeOpen(true);
    };

    /* Expose globally so the Django nav "Post" button can call it directly */
    useEffect(() => {
      window.dcCommunityCompose = openCompose;
      return () => {
        if (window.dcCommunityCompose === openCompose) delete window.dcCommunityCompose;
      };
    }, []); // eslint-disable-line

    /* Apply tweaks to :root */
    useEffect(() => {
      const palette = ACCENT_PALETTES[t.accent] || ACCENT_PALETTES.cyan;
      const root = document.documentElement;
      root.style.setProperty('--dc-accent', palette.c1);
      root.style.setProperty('--dc-accent-2', palette.c2);
      root.style.setProperty('--dc-accent-rgb', palette.rgb1);
      root.style.setProperty('--dc-accent-2-rgb', palette.rgb2);
      root.setAttribute('data-density', t.density);
      root.setAttribute('data-layout', t.layout);
      const bg = t.background || 'aurora';
      document.body.setAttribute('data-bg', bg);
      const bgDiv = document.getElementById('dc-comm-bg');
      if (bgDiv) bgDiv.setAttribute('data-bg', bg);
      /* Expose scroll-behaviour flags to the DOM scroll handler */
      window.DC_HIDE_NAV_ON_SCROLL = !!t.hideNavOnScroll;
      /* showFeedNav is always false globally — 2nd bar permanently hidden */
      window.DC_SHOW_FEED_NAV = false;
    }, [t.accent, t.density, t.layout, t.background, t.hideNavOnScroll]);

    /* Boot */
    useEffect(() => {
      const api = window.DC && window.DC.api;
      if (!api) return;
      api.loadSidebar().catch(() => null).then(() => {
        setStats(window.DC.SIDEBAR_STATS || {});
        refresh();
      });
      api.loadUserTeams().catch(() => null).then(() => {
        if (window.DC.MY_IDENTITIES && window.DC.MY_IDENTITIES[0]) setIdentity(window.DC.MY_IDENTITIES[0]);
        refresh();
      });
      if (api.loadMyTournaments) api.loadMyTournaments().catch(() => null);
      if (api.loadMyPassports) api.loadMyPassports().catch(() => null);
      api.loadFeed({
        page: 1,
        tab,
        sort
      }).then(r => {
        setPosts(r.posts || []);
        setPostsLoaded(true);
      }).catch(() => setPostsLoaded(true));
    }, []);

    /* Reload on filter change */
    useEffect(() => {
      if (!postsLoaded) return;
      const api = window.DC && window.DC.api;
      if (!api) return;
      setLoadCount(0);
      setFeedLoading(true);
      api.loadFeed({
        page: 1,
        tab,
        sort,
        game: activeGame || '',
        q: query || ''
      }).then(r => {
        setPosts(r.posts || []);
        refresh();
      }).catch(() => {}).finally(() => setFeedLoading(false));
    }, [tab, sort, activeGame, query]);

    /* 30s polling */
    useEffect(() => {
      const api = window.DC && window.DC.api;
      if (!api) return undefined;
      const iv = setInterval(() => {
        if (document.hidden) return;
        api.loadFeed({
          page: 1,
          tab,
          sort,
          game: activeGame || '',
          q: query || ''
        }).then(r => setPosts(r.posts || [])).catch(() => {});
      }, 30000);
      return () => clearInterval(iv);
    }, [tab, sort, activeGame, query]);

    /* Bridge: Django nav elements → React state via window events */
    useEffect(() => {
      const onSearch = e => setQuery(e.detail || '');
      const onCompose = e => openCompose(e && e.detail || 'text');
      const onSort = e => setSort(e.detail || 'latest');
      window.addEventListener('dc-community-search', onSearch);
      window.addEventListener('dc-community-compose', onCompose);
      window.addEventListener('dc-community-sort', onSort);
      return () => {
        window.removeEventListener('dc-community-search', onSearch);
        window.removeEventListener('dc-community-compose', onCompose);
        window.removeEventListener('dc-community-sort', onSort);
      };
    }, []);

    /* Sync active state of the nav sort buttons back to the DOM */
    useEffect(() => {
      document.querySelectorAll('.cnav-sort-nav-btn').forEach(btn => {
        btn.classList.toggle('is-active', btn.dataset.sort === sort);
      });
    }, [sort]);
    const handleComposeSubmit = () => {
      const api = window.DC && window.DC.api;
      if (!api) return;
      api.loadFeed({
        page: 1,
        tab,
        sort,
        game: activeGame || ''
      }).then(r => {
        setPosts(r.posts || []);
        window.scrollTo({
          top: 0,
          behavior: 'smooth'
        });
      }).catch(() => {});
    };
    const filteredPosts = useMemo(() => {
      let list = activeView === 'saved' ? posts.filter(p => p.saved) : posts;
      if (sort === 'latest') list = [...list].sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));
      return list;
    }, [posts, activeView, sort]);
    const displayCount = 8 + loadCount * 4;
    const visible = filteredPosts.slice(0, displayCount);
    const authed = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);
    const notifCount = (window.DC.NOTIFICATIONS || []).filter(n => n.unread).length;
    return /*#__PURE__*/React.createElement("div", {
      className: "min-h-screen"
    }, /*#__PURE__*/React.createElement("div", {
      className: "max-w-[1640px] mx-auto px-4 sm:px-6 pt-0 pb-12 flex gap-6"
    }, /*#__PURE__*/React.createElement(LeftRail, {
      activeView: activeView,
      setActiveView: setActiveView,
      activeGame: activeGame,
      setActiveGame: setActiveGame,
      identity: identity,
      setIdentity: setIdentity,
      setTab: setTab,
      setSort: setSort
    }), /*#__PURE__*/React.createElement("main", {
      className: "flex-1 min-w-0"
    }, t.showHero && /*#__PURE__*/React.createElement(PulseBand, {
      identity: identity,
      stats: stats
    }), t.showGameRail && /*#__PURE__*/React.createElement(GameChannelRail, {
      activeGame: activeGame,
      setActiveGame: setActiveGame
    }), /*#__PURE__*/React.createElement("section", {
      className: "mt-5"
    }, activeGame && window.DC.GAME_BY_ID && window.DC.GAME_BY_ID[activeGame] && /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-2 mb-4 dc-fade-in flex-wrap"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-[11px] text-white/40"
    }, "Filtered by:"), /*#__PURE__*/React.createElement("span", {
      className: "dc-chip is-active"
    }, window.DC.GAME_BY_ID[activeGame].logo && /*#__PURE__*/React.createElement("span", {
      className: "w-3 h-3 rounded-sm overflow-hidden inline-block"
    }, /*#__PURE__*/React.createElement("img", {
      src: window.DC.GAME_BY_ID[activeGame].logo,
      className: "w-full h-full object-cover"
    })), window.DC.GAME_BY_ID[activeGame].name, /*#__PURE__*/React.createElement("button", {
      onClick: () => setActiveGame(null),
      className: "ml-1 text-white/60 hover:text-white"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-xmark text-[9px]"
    })))), /*#__PURE__*/React.createElement(NavTabsPortal, {
      tab: tab,
      setTab: setTab,
      sort: sort,
      setSort: setSort
    }), ComposerTrigger && /*#__PURE__*/React.createElement(ComposerTrigger, {
      identity: identity,
      onOpen: openCompose,
      isAuthed: authed
    }), !postsLoaded || feedLoading ? /*#__PURE__*/React.createElement(FeedSkeleton, null) : /*#__PURE__*/React.createElement("div", {
      className: "space-y-4 dc-fade-stagger"
    }, visible.length === 0 ? /*#__PURE__*/React.createElement(EmptyState, {
      title: "Nothing here yet",
      sub: authed ? 'Try a different filter or be the first to post.' : 'Sign in to post, like, and join the discussion.',
      icon: "ghost"
    }) : visible.map(p => /*#__PURE__*/React.createElement(PostDispatcher, {
      key: p.id,
      post: p
    }))), visible.length > 0 && visible.length < filteredPosts.length && /*#__PURE__*/React.createElement("div", {
      className: "mt-5 text-center"
    }, /*#__PURE__*/React.createElement("button", {
      onClick: () => setLoadCount(c => c + 1),
      className: "dc-btn-ghost px-5 py-2.5 rounded-xl text-sm inline-flex items-center gap-2"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-arrow-down text-xs"
    }), " Load more")))), /*#__PURE__*/React.createElement(RightRail, null)), authed && /*#__PURE__*/React.createElement("button", {
      className: "dc-fab sm:hidden",
      onClick: () => openCompose('text'),
      "aria-label": "Create post"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fa-solid fa-plus text-xl"
    })), ComposerModal && /*#__PURE__*/React.createElement(ComposerModal, {
      open: composeOpen,
      onClose: () => setComposeOpen(false),
      identity: identity,
      onSubmit: handleComposeSubmit,
      initialKind: composeKind
    }), /*#__PURE__*/React.createElement(NotificationsDrawer, {
      open: notifOpen,
      onClose: () => setNotifOpen(false)
    }), /*#__PURE__*/React.createElement(MobileNav, {
      open: mobileOpen,
      onClose: () => setMobileOpen(false),
      activeView: activeView,
      setActiveView: setActiveView,
      activeGame: activeGame,
      setActiveGame: setActiveGame,
      identity: identity,
      setIdentity: setIdentity,
      setTab: setTab,
      setSort: setSort
    }));
  }
  function mount() {
    if (!window.DC || !window.DC.MY_IDENTITIES) {
      setTimeout(mount, 30);
      return;
    }
    ReactDOM.createRoot(document.getElementById('dc-community-root')).render(/*#__PURE__*/React.createElement(CommunityErrorBoundary, null, /*#__PURE__*/React.createElement(App, null)));
  }
  mount();
})();
