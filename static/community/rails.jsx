/* DeltaCrown Community — sidebars + widgets. */
(function () {
const { useState: useStateR } = React;
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
  const games = window.DC.GAMES || [];
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
              {games.map(g => (
                <button
                  key={g.id}
                  onClick={() => setActiveGame(g.id === activeGame ? null : g.id)}
                  className={`dc-nav w-full ${activeGame === g.id ? 'is-active' : ''}`}>
                  <span className="w-5 h-5 rounded-md overflow-hidden ring-1 ring-white/10 shrink-0 bg-white/5">
                    {g.logo && <img src={g.logo} alt={g.name} className="w-full h-full object-cover" />}
                  </span>
                  <span className="flex-1 text-left truncate">{g.short}</span>
                  {g.online > 0 && (
                    <span className="flex items-center gap-1 text-[10px] text-white/40">
                      <span className="dc-online-dot"></span>
                      <span className="dc-mono">{Math.round(g.online/100)/10}k</span>
                    </span>
                  )}
                </button>
              ))}
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
function LiveStreamsCard() {
  const list = window.DC.LIVE_STREAMS || [];
  if (!list.length) return null;
  return (
    <div className="dc-glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[.05] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="dc-stripe font-display font-bold text-sm text-white">Live Now</span>
          <span className="dc-live-dot"></span>
        </div>
        <button className="text-[10px] text-white/40 hover:text-white">See all</button>
      </div>
      <div className="p-2 space-y-1">
        {list.slice(0,4).map(s => (
          <a key={s.id} className="flex items-center gap-2.5 p-2 rounded-xl hover:bg-white/[.04] transition cursor-pointer group">
            <div className="relative shrink-0">
              <Avatar user={s.user || { name: s.channel || 'Stream', color1: '#7B2BFF', color2: '#00E5FF' }} size={36} />
              <span className="absolute -bottom-0.5 -right-0.5 px-1 py-0.5 rounded bg-dc-rose text-[8px] font-bold leading-none text-white tracking-wider">LIVE</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12.5px] font-semibold text-white truncate">{s.channel || s.title || 'Stream'}</div>
              <div className="text-[11px] text-white/50 truncate">{s.title || s.game || ''}</div>
              {s.viewers > 0 && (
                <div className="text-[10px] text-white/35 dc-mono mt-0.5">{(s.viewers).toLocaleString()} viewers</div>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

/* ---- Trending ---- */
function TrendingCard() {
  const list = window.DC.TRENDING || [];
  if (!list.length) return null;
  return (
    <div className="dc-glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[.05] flex items-center gap-2">
        <span className="dc-stripe font-display font-bold text-sm text-white">Trending</span>
        <i className="fa-solid fa-fire text-dc-rose text-xs"></i>
      </div>
      <div className="p-3 space-y-2.5">
        {list.slice(0,6).map((t, i) => (
          <a key={t.tag || i} className="flex items-center justify-between gap-2 p-2 -mx-1 rounded-lg hover:bg-white/[.03] transition cursor-pointer group">
            <div className="flex items-center gap-3 min-w-0">
              <span className="dc-mono text-[11px] text-white/30 w-4">{String(i + 1).padStart(2, '0')}</span>
              <div className="min-w-0">
                <div className="text-[13px] font-semibold text-white truncate group-hover:text-dc-cyan">#{t.tag}</div>
                <div className="dc-mono text-[10px] text-white/35">{(t.posts || 0).toLocaleString()} posts</div>
              </div>
            </div>
            {t.delta && <span className="dc-mono text-[10px] font-bold text-dc-emerald shrink-0">{t.delta}</span>}
          </a>
        ))}
      </div>
    </div>
  );
}

/* ---- Upcoming events ---- */
function UpcomingCard() {
  const list = window.DC.UPCOMING || [];
  if (!list.length) return null;
  return (
    <div className="dc-glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[.05] flex items-center justify-between">
        <span className="dc-stripe font-display font-bold text-sm text-white">Upcoming</span>
        <a href="/tournaments/" className="text-[10px] text-white/40 hover:text-white">Calendar</a>
      </div>
      <div className="p-3 space-y-2.5">
        {list.slice(0,3).map(e => (
          <a key={e.id} href={e.url || `/tournaments/`} className="flex items-center gap-3 p-2 -mx-1 rounded-lg hover:bg-white/[.03] transition cursor-pointer">
            <div className="w-12 shrink-0 text-center rounded-lg overflow-hidden border border-white/[.06]">
              <div className="text-[8px] font-bold tracking-wider py-0.5"
                   style={{ background: 'linear-gradient(180deg, rgba(0,229,255,0.18), rgba(0,229,255,0.05))', color: 'var(--dc-accent)' }}>
                {e.day || 'TUE'}
              </div>
              <div className="py-1">
                <div className="dc-mono text-[10px] font-bold text-white leading-tight">{e.date}</div>
                <div className="dc-mono text-[9px] text-white/40">{e.time || ''}</div>
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12.5px] font-semibold text-white leading-tight">{e.title}</div>
              <div className="flex items-center gap-1.5 mt-1 text-[10px] text-white/45">
                <span className="px-1.5 py-0.5 rounded bg-white/[.05] text-white/60 font-semibold">{e.kind || 'Tournament'}</span>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

/* ---- LFT mini board ---- */
function LftMiniCard() {
  const posts = (window.DC.POSTS || []).filter(p => p.type === 'lft' || p.type === 'recruit').slice(0,3);
  if (!posts.length) return null;
  return (
    <div className="dc-glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[.05] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="dc-stripe font-display font-bold text-sm text-white">LFT Board</span>
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-dc-emerald/15 text-dc-emerald border border-dc-emerald/30">{posts.length}</span>
        </div>
        <button className="text-[10px] text-white/40 hover:text-white">View all</button>
      </div>
      <div className="p-3 space-y-2">
        {posts.map(p => (
          <a key={p.id} className="flex items-center gap-3 p-2 -mx-1 rounded-lg hover:bg-white/[.03] transition cursor-pointer">
            <Avatar user={p.author} size={32} />
            <div className="flex-1 min-w-0">
              <div className="text-[12.5px] font-semibold text-white truncate">{p.author.name}</div>
              <div className="text-[10.5px] text-white/45">
                {p.lft_data && p.lft_data.rank ? p.lft_data.rank : (p.lft_data && p.lft_data.roles ? p.lft_data.roles.slice(0,1).join('') : '')}
                {' · '}{p.type === 'recruit' ? 'Recruiting' : 'Looking for team'}
              </div>
            </div>
            <i className="fa-solid fa-signal text-dc-emerald text-[10px] opacity-60"></i>
          </a>
        ))}
        <button className="w-full mt-1 text-xs text-dc-cyan hover:bg-dc-cyan/5 py-2 rounded-lg transition font-semibold">
          + Post an LFT
        </button>
      </div>
    </div>
  );
}

/* ---- Right Rail ---- */
function RightRail() {
  return (
    <aside className="dc-col-right w-[320px] shrink-0 hidden xl:block">
      <div className="dc-rail-sticky space-y-5">
        <LiveStreamsCard />
        <TrendingCard />
        <FeaturedTeamsCard />
        <LftMiniCard />
        <UpcomingCard />
        <DiscordCard />
        <div className="px-2 pb-2 text-[10px] text-white/25 flex items-center gap-3">
          <a className="hover:text-white cursor-pointer" href="/about/">About</a>
          <a className="hover:text-white cursor-pointer" href="/legal/community-guidelines/">Guidelines</a>
          <a className="hover:text-white cursor-pointer" href="/support/">Help</a>
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
