/* DeltaCrown Community — sidebars + widgets. */
(function () {
const { useState: useStateR, useEffect: useEffectR } = React;

/* Returns how many rail items to show based on viewport width.
   Right rail is visible at xl+ (1280px). Clamps to [min, 10]. */
function useRailCount(min = 3, max = 10) {
  const calc = () => {
    const w = typeof window !== 'undefined' ? window.innerWidth : 1280;
    if (w >= 1920) return 8;   // very large / 4K
    if (w >= 1536) return 6;   // 2xl
    return 5;                  // xl default
  };
  const [n, setN] = useStateR(calc);
  useEffectR(() => {
    const h = () => setN(calc());
    window.addEventListener('resize', h, { passive: true });
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
  const all         = window.DC.GAMES || [];
  const primarySlug = window.DC.PRIMARY_GAME_SLUG || '';
  const passports   = window.DC.MY_PASSPORTS || [];
  const pSlugs      = passports.map(p => p.game_slug).filter(s => s && s !== primarySlug);

  const primary      = primarySlug ? all.filter(g => g.id === primarySlug)            : [];
  const fromPassport = pSlugs.map(s => all.find(g => g.id === s)).filter(Boolean);
  const usedSlugs    = new Set([primarySlug, ...pSlugs].filter(Boolean));
  const rest         = all.filter(g => !usedSlugs.has(g.id));
  return [...primary, ...fromPassport, ...rest];
}
/* Pull card atoms exported by cards.js into this scope. */
const Avatar    = window.Avatar;
const VerifiedTick = window.VerifiedTick;
const GameHex   = window.GameHex;

function IdentityCard({ identity, setIdentity }) {
  const [open, setOpen] = useStateR(false);
  const ids = window.DC.MY_IDENTITIES || [];
  const teams = (window.DC.TEAMS || []).reduce((acc, t) => { acc[t.id] = t; return acc; }, {});

  const current = identity || ids[0];
  if (!current) return null;
  const isTeam = current.kind === 'team';
  const team = isTeam ? teams[current.teamId] : null;

  return (
    <div className="relative">
      <button className="dc-identity" onClick={() => setOpen(o => !o)}>
        {isTeam && team ? (
          <div className="shrink-0 w-10 h-10 rounded-xl overflow-hidden ring-1 ring-white/10"
               style={{ background: `linear-gradient(135deg, ${team.color}, var(--dc-accent-2))` }}>
            {team.logo_url
              ? <img src={team.logo_url} alt={team.name} className="w-full h-full object-cover" />
              : <div className="dc-team-crest">{team.tag}</div>}
          </div>
        ) : (
          <Avatar user={window.DC.ME} size={40} />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1">
            <span className="font-semibold text-sm text-white truncate">
              {isTeam && team ? team.name : window.DC.ME.name}
            </span>
            {!isTeam && window.DC.ME.verified && <VerifiedTick />}
          </div>
          <div className="text-[10.5px] text-white/45 truncate flex items-center gap-1">
            <span>{isTeam && team ? `Posting as ${team.name}` : `@${window.DC.ME.handle}`}</span>
            {isTeam && <span className="px-1 py-px rounded bg-white/10 text-[8px] font-bold text-white/70">{(current.role || '').toUpperCase()}</span>}
          </div>
        </div>
        <i className={`fa-solid fa-chevron-down text-[10px] text-white/30 transition ${open ? 'rotate-180' : ''}`}></i>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)}></div>
          <div className="dc-identity-pop absolute left-0 right-0 top-full mt-2 z-40 dc-fade-in">
            <div className="dc-hud-label text-white/35 px-2 py-1.5">Post as</div>
            {ids.map(opt => {
              const isOptTeam = opt.kind === 'team';
              const oTeam = isOptTeam ? teams[opt.teamId] : null;
              const isActive = opt.id === current.id;
              return (
                <button key={opt.id}
                        disabled={!opt.canPost}
                        onClick={() => { if (opt.canPost) { setIdentity(opt); setOpen(false); } }}
                        className={`dc-identity-opt ${isActive ? 'is-active' : ''} ${!opt.canPost ? 'is-disabled' : ''}`}>
                  {isOptTeam && oTeam ? (
                    <div className="shrink-0 w-9 h-9 rounded-lg overflow-hidden ring-1 ring-white/10"
                         style={{ background: `linear-gradient(135deg, ${oTeam.color}, var(--dc-accent-2))` }}>
                      {oTeam.logo_url
                        ? <img src={oTeam.logo_url} alt={oTeam.name} className="w-full h-full object-cover" />
                        : <div className="dc-team-crest">{oTeam.tag}</div>}
                    </div>
                  ) : (
                    <Avatar user={window.DC.ME} size={36} />
                  )}
                  <div className="flex-1 min-w-0 text-left">
                    <div className="flex items-center gap-1">
                      <span className="text-[13px] font-semibold text-white truncate">
                        {isOptTeam && oTeam ? oTeam.name : window.DC.ME.name}
                      </span>
                      {isActive && <i className="fa-solid fa-check text-dc-cyan text-[10px] ml-auto"></i>}
                    </div>
                    <div className="text-[10.5px] text-white/45 truncate">
                      {opt.canPost ? (
                        <span><span className="text-dc-emerald">●</span> {opt.role} · can post</span>
                      ) : (
                        <span><i className="fa-solid fa-lock text-[8px] mr-1"></i>{opt.role} · view only</span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
            <div className="px-2 mt-1 pt-2 border-t border-white/[.05] text-[11px] text-white/40">
              <i className="fa-solid fa-circle-info text-[10px] mr-1"></i> Team posts require captain or co-leader role.
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function LeftRail({ activeView, setActiveView, activeGame, setActiveGame, identity, setIdentity, setTab, setSort }) {
  /* Each item maps to: activeView (local), tab (API filter), sort (API sort) */
  const items = [
    { id: 'for-you',    label: 'For You',    icon: 'wand-magic-sparkles', tab: 'for-you',   sort: 'latest' },
    { id: 'following',  label: 'Following',  icon: 'user-group',          tab: 'following', sort: 'latest' },
    { id: 'trending',   label: 'Trending',   icon: 'fire',                tab: 'for-you',   sort: 'hot'    },
    { id: 'highlights', label: 'Highlights', icon: 'circle-play',         tab: 'highlights',sort: 'latest' },
    { id: 'lft',        label: 'LFT Board',  icon: 'signal',              tab: 'lft',       sort: 'latest' },
    { id: 'saved',      label: 'Saved',      icon: 'bookmark',            tab: 'for-you',   sort: 'latest' },
  ];
  const games        = orderedGames();
  const primarySlug  = window.DC.PRIMARY_GAME_SLUG || '';
  const passportSlugs = (window.DC.MY_PASSPORTS || []).map(p => p.game_slug).filter(s => s !== primarySlug);
  const authed = window.DC_CONFIG && window.DC_CONFIG.isAuthenticated;

  const handleNavClick = (it) => {
    setActiveView(it.id);
    if (setTab)  setTab(it.tab);
    if (setSort) setSort(it.sort);
  };

  return (
    <aside className="dc-col-left w-[240px] shrink-0 hidden lg:block">
      <div className="dc-rail-sticky space-y-5">

        {authed && <IdentityCard identity={identity} setIdentity={setIdentity} />}

        <div>
          <div className="dc-hud-label text-white/35 px-2 mb-2">Feed</div>
          <nav className="space-y-0.5">
            {items.map(it => (
              <button
                key={it.id}
                onClick={() => handleNavClick(it)}
                className={`dc-nav w-full ${activeView === it.id ? 'is-active' : ''}`}>
                <span className="dc-nav-ic"><i className={`fa-solid fa-${it.icon}`}></i></span>
                <span className="flex-1 text-left">{it.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {games.length > 0 && (
          <div>
            <div className="flex items-center justify-between px-2 mb-2">
              <span className="dc-hud-label text-white/35">Game Channels</span>
            </div>
            <nav className="space-y-0.5">
              <button
                onClick={() => setActiveGame(null)}
                className={`dc-nav w-full ${!activeGame ? 'is-active' : ''}`}>
                <span className="dc-nav-ic"><i className="fa-solid fa-grip"></i></span>
                <span className="flex-1 text-left">All Games</span>
              </button>
              {games.map((g, idx) => {
                const isPrimary  = primarySlug ? g.id === primarySlug : false;
                const isPassport = !isPrimary && passportSlugs.includes(g.id);
                return (
                  <button
                    key={g.id}
                    onClick={() => setActiveGame(g.id === activeGame ? null : g.id)}
                    className={`dc-nav w-full ${activeGame === g.id ? 'is-active' : ''}`}>
                    <span className="w-5 h-5 rounded-md overflow-hidden ring-1 ring-white/10 shrink-0 bg-white/5 relative">
                      {g.logo && <img src={g.logo} alt={g.name} className="w-full h-full object-cover" />}
                    </span>
                    <span className="flex-1 text-left truncate" title={g.name}>{g.name}</span>
                    {isPrimary ? (
                      <span className="shrink-0 text-[8px] font-black px-1 py-0.5 rounded leading-none"
                            style={{ background: 'rgba(0,229,255,0.15)', color: 'rgba(0,229,255,0.9)' }}>
                        MAIN
                      </span>
                    ) : isPassport ? (
                      <i className="fa-solid fa-id-card text-[8px] text-white/25 shrink-0" title="In your passport"></i>
                    ) : g.online > 0 ? (
                      <span className="flex items-center gap-1 text-[10px] text-white/40">
                        <span className="dc-online-dot"></span>
                        <span className="dc-mono">{Math.round(g.online/100)/10}k</span>
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </nav>
          </div>
        )}

      </div>
    </aside>
  );
}

function FeaturedTeamsCard() {
  const teams = window.DC.FEATURED_TEAMS || [];
  if (teams.length === 0) return null;
  return (
    <div className="dc-glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[.05] flex items-center justify-between">
        <span className="dc-stripe font-display font-bold text-sm text-white">Featured Teams</span>
        <a className="text-[10px] text-white/40 hover:text-white" href="/teams/">All teams</a>
      </div>
      <div className="p-2 space-y-1">
        {teams.slice(0, 6).map(t => (
          <a key={t.slug} href={`/teams/${t.slug}/`}
             className="flex items-center gap-2.5 p-2 rounded-xl hover:bg-white/[.04] transition cursor-pointer">
            <div className="shrink-0 w-9 h-9 rounded-lg overflow-hidden ring-1 ring-white/10 bg-white/5 grid place-items-center text-[10px] font-bold text-white/70">
              {t.logo_url
                ? <img src={t.logo_url} alt={t.name} className="w-full h-full object-cover" />
                : (t.tag || (t.name || '').slice(0, 3).toUpperCase())}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12.5px] font-semibold text-white truncate">{t.name}</div>
              <div className="text-[10.5px] text-white/45 truncate">
                {t.game ? <span>{t.game}</span> : null}
                {t.member_count ? <span> · <span className="dc-mono">{t.member_count}</span> members</span> : null}
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

function StatsCard() {
  const s = window.DC.SIDEBAR_STATS || {};
  if (!s.total_posts && !s.total_teams && !s.total_games) return null;
  return (
    <div className="dc-glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[.05] flex items-center gap-2">
        <span className="dc-stripe font-display font-bold text-sm text-white">Community Stats</span>
      </div>
      <div className="p-4 grid grid-cols-3 gap-2">
        <div className="text-center">
          <div className="dc-counter-num text-lg text-white">{(s.total_posts || 0).toLocaleString()}</div>
          <div className="dc-hud-label text-white/35 text-[9px]">Posts</div>
        </div>
        <div className="text-center">
          <div className="dc-counter-num text-lg text-white">{(s.total_teams || 0).toLocaleString()}</div>
          <div className="dc-hud-label text-white/35 text-[9px]">Teams</div>
        </div>
        <div className="text-center">
          <div className="dc-counter-num text-lg text-white">{(s.total_games || 0).toLocaleString()}</div>
          <div className="dc-hud-label text-white/35 text-[9px]">Games</div>
        </div>
      </div>
    </div>
  );
}

function DiscordCard() {
  return (
    <div className="dc-discord rounded-2xl p-4 relative overflow-hidden">
      <div className="absolute -top-4 -right-4 w-24 h-24 rounded-full" style={{ background: 'radial-gradient(circle, rgba(88,101,242,0.4), transparent 70%)' }}></div>
      <div className="relative">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-9 h-9 rounded-xl grid place-items-center" style={{ background: '#5865F2' }}>
            <i className="fa-brands fa-discord text-white text-lg"></i>
          </div>
          <div>
            <div className="text-sm font-bold text-white">DeltaCrown Discord</div>
            <div className="text-[10.5px] text-white/55">Voice channels, scrims, announcements.</div>
          </div>
        </div>
        <a href="https://discord.gg/deltacrown" target="_blank" rel="noopener"
           className="block w-full py-2 rounded-xl text-sm font-bold text-white text-center transition hover:brightness-110"
           style={{ background: '#5865F2' }}>
          <i className="fa-brands fa-discord mr-2"></i> Join Server
        </a>
      </div>
    </div>
  );
}

/* ---- Live Streams ---- */
function LiveStreamsCard({ count = 5 }) {
  const list = window.DC.LIVE_STREAMS || [];
  if (!list.length) return null;
  return (
    <div className="dc-glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[.05] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="dc-stripe font-display font-bold text-sm text-white">Live Now</span>
          <span className="dc-live-dot"></span>
          <span className="dc-mono text-[10px] text-dc-rose font-bold">{list.length}</span>
        </div>
        <a href="/arena/" className="text-[10px] text-white/40 hover:text-dc-cyan transition">
          Arena <i className="fa-solid fa-arrow-right text-[8px] ml-0.5"></i>
        </a>
      </div>
      <div className="p-2 space-y-0.5">
        {list.slice(0, count).map(s => (
          <a key={s.id} href={s.url || '/arena/'} target="_blank" rel="noopener"
             className="flex items-center gap-2.5 p-2 rounded-xl hover:bg-white/[.04] transition cursor-pointer group">
            <div className="relative shrink-0">
              <Avatar user={s.user || { name: s.channel || 'Stream', color1: '#7B2BFF', color2: '#00E5FF' }} size={36} />
              <span className="absolute -bottom-0.5 -right-0.5 px-1 py-0.5 rounded"
                    style={{ background: '#EF4444', color: 'white', fontSize: 7, fontWeight: 800, letterSpacing: '0.05em', lineHeight: 1.5 }}>
                LIVE
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12.5px] font-semibold text-white truncate group-hover:text-dc-cyan transition">
                {s.channel || s.title || 'Stream'}
              </div>
              <div className="text-[10.5px] text-white/50 truncate">{s.title || s.game || ''}</div>
              {s.viewers > 0 && (
                <div className="dc-mono text-[10px] text-white/35 mt-0.5 flex items-center gap-1">
                  <span className="dc-live-dot" style={{ width: 5, height: 5 }}></span>
                  {s.viewers.toLocaleString()} viewers
                </div>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

/* ---- Trending ---- */
function TrendingCard({ count = 5 }) {
  const list = window.DC.TRENDING || [];
  return (
    <div className="dc-glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[.05] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="dc-stripe font-display font-bold text-sm text-white">Trending</span>
          <i className="fa-solid fa-fire text-dc-rose text-xs"></i>
        </div>
        <span className="dc-hud-label text-white/30 text-[9px]">LAST 30 DAYS</span>
      </div>
      {list.length === 0 ? (
        <div className="flex flex-col items-center py-7 px-4 gap-2">
          <div className="w-10 h-10 rounded-xl grid place-items-center mb-1"
               style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)' }}>
            <i className="fa-solid fa-fire text-dc-rose/50"></i>
          </div>
          <p className="text-[11px] text-white/30 text-center leading-relaxed">
            Trending topics appear once community members start posting.
          </p>
          <a href="/community/" className="mt-1 text-[11px] text-dc-cyan font-semibold hover:underline transition">
            Be the first to post →
          </a>
        </div>
      ) : (
        <div className="p-2">
          {list.slice(0, count).map((t, i) => (
            <div key={t.tag || i}
                 className="flex items-center justify-between gap-3 px-2 py-2.5 rounded-xl hover:bg-white/[.04] transition cursor-pointer group">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-6 h-6 rounded-lg grid place-items-center shrink-0 text-[11px] font-black dc-mono"
                     style={{
                       background: i < 3 ? `linear-gradient(135deg, rgba(var(--dc-accent-rgb),0.18), rgba(var(--dc-accent-2-rgb),0.1))` : 'rgba(255,255,255,0.04)',
                       color: i < 3 ? 'var(--dc-accent)' : 'rgba(255,255,255,0.3)',
                     }}>
                  {i + 1}
                </div>
                <div className="min-w-0">
                  <div className="text-[13px] font-semibold text-white/90 group-hover:text-dc-cyan transition truncate">
                    #{t.tag}
                  </div>
                  <div className="dc-mono text-[10px] text-white/35">
                    {(t.posts || 0).toLocaleString()} posts
                  </div>
                </div>
              </div>
              {t.delta ? (
                <span className="dc-mono text-[10px] font-bold text-dc-emerald shrink-0">{t.delta}</span>
              ) : i < 3 ? (
                <i className="fa-solid fa-arrow-trend-up text-[10px] text-dc-emerald/60 shrink-0"></i>
              ) : null}
            </div>
          ))}
          <div className="mx-2 mt-1 pt-2 border-t border-white/[.04]">
            <a href="/community/?tab=for-you&sort=hot"
               className="flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-semibold text-white/40 hover:text-dc-cyan hover:bg-white/[.03] transition">
              Explore trending <i className="fa-solid fa-arrow-right text-[9px]"></i>
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Upcoming events ---- */
function UpcomingCard({ count = 5 }) {
  const list = window.DC.UPCOMING || [];
  return (
    <div className="dc-glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[.05] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="dc-stripe font-display font-bold text-sm text-white">Upcoming</span>
          <i className="fa-solid fa-calendar-days text-white/30 text-xs"></i>
        </div>
        <a href="/tournaments/" className="text-[10px] text-white/40 hover:text-dc-cyan transition">
          Calendar <i className="fa-solid fa-arrow-right text-[8px] ml-0.5"></i>
        </a>
      </div>

      {list.length === 0 ? (
        <div className="flex flex-col items-center py-7 px-4 gap-2">
          <div className="w-10 h-10 rounded-xl grid place-items-center mb-1"
               style={{ background: 'rgba(var(--dc-accent-rgb),0.08)', border: '1px solid rgba(var(--dc-accent-rgb),0.15)' }}>
            <i className="fa-solid fa-calendar-days text-dc-cyan/50"></i>
          </div>
          <p className="text-[11px] text-white/30 text-center leading-relaxed">
            No tournaments scheduled in the next 14 days.
          </p>
          <a href="/tournaments/" className="mt-1 text-[11px] text-dc-cyan font-semibold hover:underline transition">
            Browse all tournaments →
          </a>
        </div>
      ) : (
        <div className="p-2">
          {list.slice(0, count).map(e => (
            <a key={e.id} href={e.url || '/tournaments/'}
               className="flex items-center gap-3 px-2 py-3 rounded-xl hover:bg-white/[.04] transition cursor-pointer group">
              {/* Date badge */}
              <div className="w-11 shrink-0 rounded-xl overflow-hidden text-center"
                   style={{ border: '1px solid rgba(var(--dc-accent-rgb),0.2)' }}>
                <div className="py-1"
                     style={{ background: 'linear-gradient(180deg, rgba(var(--dc-accent-rgb),0.18) 0%, rgba(var(--dc-accent-rgb),0.06) 100%)' }}>
                  <div className="dc-mono text-[8px] font-bold tracking-widest"
                       style={{ color: 'var(--dc-accent)' }}>
                    {e.day || ''}
                  </div>
                </div>
                <div className="py-1.5 bg-white/[.02]">
                  <div className="dc-mono text-[12px] font-black text-white leading-none">{(e.date || '').split(' ')[1] || e.date || '—'}</div>
                  <div className="dc-mono text-[8px] text-white/40 mt-0.5 font-semibold">{(e.date || '').split(' ')[0] || ''}</div>
                </div>
              </div>
              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-semibold text-white leading-snug truncate group-hover:text-dc-cyan transition">
                  {e.title}
                </div>
                <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded dc-hud-label"
                        style={{ background: 'rgba(var(--dc-accent-2-rgb),0.12)', color: 'rgba(var(--dc-accent-2-rgb), 0.85)', border: '1px solid rgba(var(--dc-accent-2-rgb),0.2)' }}>
                    {e.kind || 'TOURNAMENT'}
                  </span>
                  {e.time && <span className="dc-mono text-[9px] text-white/35">{e.time}</span>}
                </div>
              </div>
              <i className="fa-solid fa-chevron-right text-[9px] text-white/20 group-hover:text-dc-cyan transition shrink-0"></i>
            </a>
          ))}
          {list.length > count && (
            <div className="px-2 pt-1">
              <a href="/tournaments/" className="flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-semibold text-white/40 hover:text-dc-cyan hover:bg-white/[.03] transition">
                {list.length - count} more <i className="fa-solid fa-arrow-right text-[9px]"></i>
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ---- LFT mini board ---- */
function LftMiniCard({ count = 5 }) {
  const allPosts = window.DC.POSTS || [];
  /* Distribute count across lft + recruit proportionally */
  const lftMax = Math.ceil(count * 0.6);
  const recMax = Math.floor(count * 0.4);
  const lftPosts  = allPosts.filter(p => p.type === 'lft').slice(0, lftMax);
  const recPosts  = allPosts.filter(p => p.type === 'recruit').slice(0, recMax);
  const total     = lftPosts.length + recPosts.length;
  const isAuthed  = !!(window.DC_CONFIG && window.DC_CONFIG.isAuthenticated);

  const openLft = (kind) => {
    if (typeof window.dcCommunityCompose === 'function') window.dcCommunityCompose(kind);
    else window.dispatchEvent(new CustomEvent('dc-community-compose', { detail: kind }));
  };

  return (
    <div className="dc-glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[.05] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="dc-stripe font-display font-bold text-sm text-white">LFT Board</span>
          {total > 0 && (
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md"
                  style={{ background: 'rgba(16,230,139,0.12)', color: '#10e68b', border: '1px solid rgba(16,230,139,0.25)' }}>
              {total}
            </span>
          )}
        </div>
        <button onClick={() => {
          if (typeof window.dispatchEvent === 'function')
            window.dispatchEvent(new CustomEvent('dc-community-tab', { detail: 'lft' }));
        }} className="text-[10px] text-white/40 hover:text-dc-cyan transition">
          View all <i className="fa-solid fa-arrow-right text-[8px] ml-0.5"></i>
        </button>
      </div>

      {total === 0 ? (
        <div className="flex flex-col items-center py-7 px-4 gap-2">
          <div className="w-10 h-10 rounded-xl grid place-items-center mb-1"
               style={{ background: 'rgba(16,230,139,0.08)', border: '1px solid rgba(16,230,139,0.15)' }}>
            <i className="fa-solid fa-signal text-dc-emerald/50"></i>
          </div>
          <p className="text-[11px] text-white/30 text-center leading-relaxed">
            No active LFT posts yet. Be the first to post!
          </p>
          {isAuthed && (
            <div className="flex gap-2 mt-1">
              <button onClick={() => openLft('lft')}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-bold text-dc-emerald transition hover:bg-dc-emerald/10"
                      style={{ border: '1px solid rgba(16,230,139,0.25)' }}>
                <i className="fa-solid fa-signal text-[9px]"></i> I'm LFT
              </button>
              <button onClick={() => openLft('recruit')}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-bold transition hover:bg-white/5 text-white/50"
                      style={{ border: '1px solid rgba(255,255,255,0.1)' }}>
                <i className="fa-solid fa-user-plus text-[9px]"></i> Recruit
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="p-2">
          {lftPosts.length > 0 && (
            <>
              <div className="dc-hud-label text-white/25 px-2 py-1.5 text-[9px]">LOOKING FOR TEAM</div>
              {lftPosts.map(p => {
                const lft = p.lft_data || {};
                const roles = Array.isArray(lft.roles) ? lft.roles.slice(0,2).join(', ') : (lft.roles || '');
                return (
                  <div key={p.id}
                       className="flex items-center gap-2.5 px-2 py-2.5 rounded-xl hover:bg-white/[.04] transition cursor-pointer group">
                    <Avatar user={p.author} size={32} />
                    <div className="flex-1 min-w-0">
                      <div className="text-[12.5px] font-semibold text-white truncate group-hover:text-dc-cyan transition">
                        {p.author.name}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                        {lft.rank && (
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded dc-mono"
                                style={{ background: 'rgba(0,229,255,0.1)', color: 'rgba(0,229,255,0.8)' }}>
                            {lft.rank}
                          </span>
                        )}
                        {roles && <span className="text-[10px] text-white/40 truncate">{roles}</span>}
                      </div>
                    </div>
                    {p.game && p.game.logo && (
                      <img src={p.game.logo} className="w-5 h-5 rounded shrink-0 opacity-60" alt="" onError={e => { e.currentTarget.style.display='none'; }} />
                    )}
                  </div>
                );
              })}
            </>
          )}
          {recPosts.length > 0 && (
            <>
              <div className="dc-hud-label text-white/25 px-2 py-1.5 text-[9px] mt-1">RECRUITING</div>
              {recPosts.map(p => {
                const lft = p.lft_data || {};
                const roles = Array.isArray(lft.roles) ? lft.roles.slice(0,2).join(', ') : (lft.roles || '');
                const teamName = p.team ? p.team.name : null;
                return (
                  <div key={p.id}
                       className="flex items-center gap-2.5 px-2 py-2.5 rounded-xl hover:bg-white/[.04] transition cursor-pointer group">
                    <Avatar user={p.author} size={32} />
                    <div className="flex-1 min-w-0">
                      <div className="text-[12.5px] font-semibold text-white truncate group-hover:text-dc-cyan transition">
                        {teamName || p.author.name}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                              style={{ background: 'rgba(108,0,255,0.15)', color: 'rgba(155,89,255,0.9)' }}>
                          Recruiting
                        </span>
                        {roles && <span className="text-[10px] text-white/40 truncate">{roles}</span>}
                      </div>
                    </div>
                    {p.game && p.game.logo && (
                      <img src={p.game.logo} className="w-5 h-5 rounded shrink-0 opacity-60" alt="" onError={e => { e.currentTarget.style.display='none'; }} />
                    )}
                  </div>
                );
              })}
            </>
          )}
          {isAuthed && (
            <div className="flex gap-2 px-2 mt-2 pt-2 border-t border-white/[.04]">
              <button onClick={() => openLft('lft')}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-bold text-dc-emerald hover:bg-dc-emerald/8 transition"
                      style={{ border: '1px solid rgba(16,230,139,0.2)' }}>
                <i className="fa-solid fa-signal text-[9px]"></i> I'm LFT
              </button>
              <button onClick={() => openLft('recruit')}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-bold text-white/50 hover:text-white hover:bg-white/5 transition"
                      style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
                <i className="fa-solid fa-user-plus text-[9px]"></i> Recruit
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ---- Right Rail ---- */
function RightRail() {
  const count = useRailCount(3, 10);   /* min 3 · responsive · max 10 */
  return (
    <aside className="dc-col-right w-[300px] shrink-0 hidden xl:block">
      <div className="dc-rail-sticky space-y-4">
        {/* Live Now — always on top when streams exist */}
        <LiveStreamsCard count={count} />
        {/* Primary widgets — always visible (with empty states) */}
        <TrendingCard count={count} />
        <LftMiniCard count={count} />
        <UpcomingCard count={count} />
        {/* Contextual widgets — only when data exists */}
        <FeaturedTeamsCard />
        <StatsCard />
        <DiscordCard />
        <div className="px-2 pb-2 text-[10px] text-white/25 flex items-center flex-wrap gap-x-3 gap-y-1">
          <a className="hover:text-white" href="/about/">About</a>
          <a className="hover:text-white" href="/legal/community-guidelines/">Guidelines</a>
          <a className="hover:text-white" href="/support/">Help</a>
          <span className="ml-auto">© DeltaCrown</span>
        </div>
      </div>
    </aside>
  );
}

Object.assign(window, {
  IdentityCard, LeftRail, RightRail,
  StatsCard, FeaturedTeamsCard, DiscordCard,
  LiveStreamsCard, TrendingCard, UpcomingCard, LftMiniCard,
});
})();
