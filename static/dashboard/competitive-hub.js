(function () {
  'use strict';

  const API = {
    contractsList:       '/api/v1/contracts/templates/',
    contractsEnroll:     (id) => `/api/v1/contracts/enroll/${id}/`,
    myOperations:        '/api/v1/competitive/my-operations/',
    challengesList:      '/api/v1/challenges/',
    challengeCreate:     '/api/v1/challenges/',
    challengeAccept:     (id) => `/api/v1/challenges/${id}/accept/`,
    challengeResult:     (id) => `/api/v1/challenges/${id}/result/`,
    bountiesList:        '/api/v1/bounties/',
    bountyCreate:        '/api/v1/bounties/',
    bountyClaim:         (id) => `/api/v1/bounties/${id}/claim/`,
    royaleList:          '/api/v1/royale/lobbies/',
    royaleReserve:       (id) => `/api/v1/royale/lobbies/${id}/reserve/`,
  };

  function readHubContext() {
    const el = document.getElementById('hub-context');
    if (!el) return { user_state: 'SOLO', can_issue: false, identity: {}, primary_team: null, wallet: {}, my_teams: [], games: [] };
    try { return JSON.parse(el.textContent) || {}; }
    catch { return { user_state: 'SOLO', can_issue: false, identity: {}, primary_team: null, wallet: {}, my_teams: [], games: [] }; }
  }
  const HUB = readHubContext();

  const STATE = {
    activeTab: 'showdown',
    gameFilter: 'ALL',
    gameManuallySelected: false,
    searchQuery: '',
    operatingTeamId: String((HUB.primary_team && HUB.primary_team.id) || ((HUB.my_teams || [])[0] && (HUB.my_teams || [])[0].id) || ''),
    targetOpponent: null,
    data: { showdown: [], missions: [], bounty: [], dropzone: [], myOperations: [] },
    loaded: { showdown: false, missions: false, bounty: false, dropzone: false, myOperations: false },
    resultOperation: null,
  };

  const TAB_ALIASES = {
    clash: 'showdown',
    showdowns: 'showdown',
    showdown: 'showdown',
    'crown-clash': 'showdown',
    challenges: 'showdown',
    contracts: 'missions',
    contract: 'missions',
    missions: 'missions',
    mission: 'missions',
    'contract-board': 'missions',
    hitlist: 'bounty',
    'the-hitlist': 'bounty',
    bounty: 'bounty',
    bounties: 'bounty',
    royale: 'dropzone',
    'crown-royale': 'dropzone',
    dropzone: 'dropzone',
    operations: 'showdown',
    operation: 'showdown',
    'my-operations': 'showdown',
    ops: 'showdown',
    review: 'showdown',
    reviews: 'showdown',
    disputes: 'showdown',
  };

  const TAB_HASH = {
    showdown: 'showdown',
    missions: 'missions',
    bounty: 'bounty',
    dropzone: 'dropzone',
  };

  // ── CSRF / fetch helpers ──────────────────────────────────────────

  function getCookie(name) {
    const cookies = (document.cookie || '').split(';');
    for (const c of cookies) {
      const v = c.trim();
      if (v.startsWith(name + '=')) return decodeURIComponent(v.substring(name.length + 1));
    }
    return '';
  }

  async function jsonFetch(url, options = {}) {
    const init = Object.assign({ method: 'GET', credentials: 'same-origin', headers: {} }, options);
    init.headers = Object.assign({
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    }, init.headers || {});
    if (init.method && init.method.toUpperCase() !== 'GET') {
      init.headers['X-CSRFToken'] = getCookie('csrftoken');
    }
    let res;
    try { res = await fetch(url, init); }
    catch { throw { status: 0, body: { detail: 'Network error.' } }; }
    let body = {};
    try { body = await res.json(); } catch { body = {}; }
    if (!res.ok) throw { status: res.status, body };
    return body;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function cleanBountyLogoUrl(value) {
    const url = String(value || '').trim();
    if (!url || /default-logo|placeholder/i.test(url)) return '';
    return url;
  }

  // ── Toast ─────────────────────────────────────────────────────────

  function toast(message, type) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const node = document.createElement('div');
    const colorClass = type === 'error' ? 'border-dc-neon' : (type === 'info' ? 'border-dc-cyan' : 'border-dc-success');
    const bgGlow = type === 'error' ? 'bg-dc-neon/10' : (type === 'info' ? 'bg-dc-cyan/10' : 'bg-dc-success/10');
    const icon = type === 'error' ? 'fa-xmark text-dc-neon' : (type === 'info' ? 'fa-info text-dc-cyan' : 'fa-check text-dc-success');
    node.className = `glass-heavy border-l-4 ${colorClass} ${bgGlow} rounded-xl p-4 shadow-2xl flex items-center gap-4 max-w-sm pointer-events-auto fade-enter`;
    node.innerHTML = `
      <div class="w-8 h-8 rounded-full border border-current flex items-center justify-center flex-shrink-0">
        <i class="fa-solid ${icon} text-sm"></i>
      </div>
      <p class="text-sm text-white font-medium leading-snug">${esc(message)}</p>`;
    container.appendChild(node);
    setTimeout(() => {
      node.style.transition = 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
      node.style.transform = 'translateX(120%)';
      node.style.opacity = '0';
      setTimeout(() => node.remove(), 420);
    }, 4500);
  }

  function handleApiError(err) {
    const code = err && err.body && err.body.code;
    const detail = (err && err.body && err.body.detail) || 'Something went wrong.';
    if (code === 'INSUFFICIENT_FUNDS') {
      toast('Not enough DeltaCoins. Please visit the Treasury to top up.', 'error');
      return;
    }
    if (err && err.status === 403) { toast('Captain authority required.', 'error'); return; }
    if (err && err.status === 401) { toast('You need to log in.', 'error'); return; }
    toast(detail, 'error');
  }

  // ── Confirmation modal ────────────────────────────────────────────

  let _confirmDeferred = null;
  let _confirmConfig = {};

  function openConfirm({ title, body, lockNote, teamChoices = [], selectedTeamId = '' }) {
    return new Promise((resolve) => {
      _confirmDeferred = resolve;
      _confirmConfig = { teamChoices };
      document.getElementById('confirm-title').textContent = title || 'Confirm action';
      document.getElementById('confirm-body').textContent = body || '';
      document.getElementById('confirm-lock').textContent = lockNote || '';
      const teamWrap = document.getElementById('confirm-team-wrap');
      const teamSelect = document.getElementById('confirm-team-select');
      if (teamWrap && teamSelect) {
        if (teamChoices.length > 1) {
          fillSelect(teamSelect, teamChoices, { placeholder: '-- Select accepting team --', selectedId: selectedTeamId });
          teamWrap.classList.remove('hidden-spa');
        } else {
          teamSelect.innerHTML = '';
          teamWrap.classList.add('hidden-spa');
        }
      }
      const m = document.getElementById('confirm-modal');
      m.classList.remove('hidden-spa');
    });
  }

  function closeConfirm(result) {
    let value = !!result;
    if (result && (_confirmConfig.teamChoices || []).length > 1) {
      const teamSelect = document.getElementById('confirm-team-select');
      const teamId = teamSelect ? teamSelect.value : '';
      if (!teamId) {
        toast('Select the team that will accept this Showdown.', 'error');
        return;
      }
      value = { confirmed: true, teamId };
    }
    document.getElementById('confirm-modal').classList.add('hidden-spa');
    if (_confirmDeferred) { _confirmDeferred(value); _confirmDeferred = null; }
    _confirmConfig = {};
  }

  // ── Slide-over helpers ────────────────────────────────────────────

  function activeDrawerPanels() {
    return Array.from(document.querySelectorAll('#slide-over-create-clash, #slide-over-create-hitlist'))
      .filter((el) => el instanceof HTMLElement && !el.classList.contains('translate-x-full'));
  }

  function isGuideOpen() {
    const guide = document.getElementById('guide-modal');
    return !!guide && !guide.classList.contains('hidden-spa');
  }

  function lockPageScroll() {
    document.body.classList.add('overflow-hidden');
  }

  function unlockPageScrollIfIdle() {
    if (!activeDrawerPanels().length && !isGuideOpen()) {
      document.body.classList.remove('overflow-hidden');
    }
  }

  function closeGuideModal() {
    const guide = document.getElementById('guide-modal');
    if (guide) guide.classList.add('hidden-spa');
    unlockPageScrollIfIdle();
  }

  function openSlideOver(name, opts = {}) {
    const backdrop = document.getElementById('slide-over-backdrop');
    const panel = document.getElementById(`slide-over-${name}`);
    if (!backdrop || !panel) return;
    if (name === 'create-clash') resetClashForm(opts);
    if (name === 'create-hitlist') resetHitlistForm(opts);
    lockPageScroll();
    backdrop.classList.remove('hidden-spa');
    requestAnimationFrame(() => {
      backdrop.classList.remove('opacity-0');
      panel.classList.remove('translate-x-full');
    });
    const firstInput = panel.querySelector('input:not([type=hidden]), select');
    if (firstInput) setTimeout(() => firstInput.focus(), 250);
  }

  function closeSlideOver(name) {
    const backdrop = document.getElementById('slide-over-backdrop');
    const panel = document.getElementById(`slide-over-${name}`);
    if (!backdrop || !panel) return;
    backdrop.classList.add('opacity-0');
    panel.classList.add('translate-x-full');
    setTimeout(() => {
      if (!activeDrawerPanels().length) backdrop.classList.add('hidden-spa');
      unlockPageScrollIfIdle();
    }, 500);
  }

  // ── Hero / identity hydration ─────────────────────────────────────

  function selectedTeam() {
    const teams = (HUB.all_teams && HUB.all_teams.length) ? HUB.all_teams : (HUB.my_teams || []);
    return teams.find((t) => String(t.id) === String(STATE.operatingTeamId)) || HUB.primary_team || null;
  }

  function canIssueSelectedTeam() {
    const team = selectedTeam();
    if (!team) return false;
    return (HUB.my_teams || []).some((t) => String(t.id) === String(team.id));
  }

  function syncOpenTeamSelects() {
    ['clash-team', 'hitlist-team'].forEach((id) => {
      const el = document.getElementById(id);
      if (!el || !STATE.operatingTeamId) return;
      if (Array.from(el.options).some((opt) => String(opt.value) === String(STATE.operatingTeamId))) {
        el.value = String(STATE.operatingTeamId);
      }
    });
  }

  function setOperatingTeam(teamId) {
    STATE.operatingTeamId = String(teamId || '');
    const team = selectedTeam();
    if (team) HUB.primary_team = team;
    renderHero();
    hydrateLeftColumn();
    renderActionPermissions();
    renderActiveOps();
    renderAllFeeds();
    syncOpenTeamSelects();
    if (!STATE.gameManuallySelected) {
      setGameFilter(defaultGameForSelectedTeam(), { manual: false });
    }
    const hint = document.getElementById('operating-team-hint');
    if (hint) hint.textContent = team ? `${team.name} scopes team-based Showdown, Bounty, and operations. Missions remain solo.` : 'Choose the team context for team-based operations. Missions remain solo.';
  }

  function hydrateTeamSwitcher() {
    const wrap = document.getElementById('operating-team-switcher');
    const select = document.getElementById('operating-team-select');
    const hint = document.getElementById('operating-team-hint');
    const teams = ((HUB.all_teams && HUB.all_teams.length) ? HUB.all_teams : (HUB.my_teams || [])).map((t) => ({
      id: t.id,
      label: `${t.tag ? `${t.name} [${t.tag}]` : t.name}${t.can_issue ? '' : ' - member'}`,
    }));
    if (!wrap || !select || teams.length < 2) return;
    if (!STATE.operatingTeamId && teams[0]) STATE.operatingTeamId = String(teams[0].id);
    fillSelect(select, teams, { selectedId: STATE.operatingTeamId });
    wrap.classList.remove('hidden-spa');
    const team = selectedTeam();
    if (hint) {
      hint.textContent = team
        ? `${team.name || team.label} scopes team-based Showdown, Bounty, and operations. Missions remain solo.`
        : 'Choose the team context for team-based operations. Missions remain solo.';
    }
  }

  function hydrateLeftColumn() {
    const id = HUB.identity || {};
    const team = selectedTeam();
    const wallet = HUB.wallet || {};

    const avatarBox = document.getElementById('ctx-avatar');
    if (avatarBox) {
      if (id.avatar_url) {
        avatarBox.innerHTML = `<img src="${esc(id.avatar_url)}" alt="${esc(id.display_name || '')}" class="w-full h-full object-cover rounded-lg">`;
      } else {
        const initials = String(id.display_name || id.username || '?').trim().slice(0, 2).toUpperCase();
        const fb = document.getElementById('ctx-avatar-fallback');
        if (fb) fb.textContent = initials;
      }
    }
    document.getElementById('ctx-name').textContent = id.name || id.display_name || '—';
    document.getElementById('ctx-role').textContent = id.role_label || 'Agent';

    document.getElementById('wallet-type-label').textContent = team ? `${team.name} - Team authority` : 'Personal Wallet';
    document.getElementById('wallet-balance').textContent = (Number(wallet.cached_balance || 0)).toLocaleString();
    document.getElementById('wallet-escrow').textContent = `${Number(wallet.escrow_locked_dc || 0).toLocaleString()} DC`;

    document.getElementById('ctx-stat-1').textContent = '—';
    document.getElementById('ctx-stat-2').textContent = canIssueSelectedTeam() ? 'CAPTAIN' : (team ? 'MEMBER' : 'SOLO');
  }

  function renderHero() {
    const titleEl = document.getElementById('hero-title');
    const descEl = document.getElementById('hero-desc');
    const actionsEl = document.getElementById('hero-actions');
    const visEl = document.getElementById('hero-visualizer');
    const team = selectedTeam();

    if (team && canIssueSelectedTeam()) {
      titleEl.innerHTML = `Command <span class="text-gradient-cyan">Center</span>`;
      descEl.innerHTML = `Operating as <strong class="text-white">${esc(team.name)}</strong>. Create Showdowns with rival teams or post Bounties for challengers to claim.`;
      actionsEl.innerHTML = `
        <button type="button" data-open-slide="create-clash" class="btn-cyber bg-dc-cyan hover:bg-cyan-400 text-black px-8 py-3.5 font-bold uppercase tracking-widest shadow-[0_0_20px_rgba(0,229,255,0.4)] flex items-center gap-2">
          <i class="fa-solid fa-bolt"></i> Create Showdown
        </button>
        <button type="button" data-go-tab="bounty" class="glass-light text-white px-8 py-3.5 rounded-lg font-bold uppercase tracking-wider hover:bg-white/10 transition-colors border border-white/20">
          View Bounties
        </button>`;
      visEl.innerHTML = `
        <div class="glass-light rounded-xl p-4 border border-dc-cyan/30 w-full relative overflow-hidden group">
          <div class="absolute inset-0 bg-dc-cyan opacity-10 blur-xl group-hover:opacity-20 transition-opacity"></div>
          <p class="text-[10px] text-dc-cyan uppercase font-bold tracking-widest mb-1 relative z-10">Team Authority</p>
          <p class="font-display font-black text-3xl text-white relative z-10">${esc(team.role || 'CAPTAIN')}</p>
          <p class="text-xs text-gray-400 mt-2 relative z-10">${esc(team.name)}</p>
        </div>`;
    } else if (HUB.user_state === 'TEAM_MEMBER') {
      titleEl.innerHTML = `Roster <span class="text-gradient-cyan">Member</span>`;
      descEl.innerHTML = `You're on <strong class="text-white">${esc((team && team.name) || 'a team')}</strong>. Only captains and managers can create team reward operations. Missions remain available as the solo path.`;
      actionsEl.innerHTML = `
        <button type="button" disabled class="glass-heavy text-gray-500 px-8 py-3.5 rounded-lg font-bold uppercase tracking-widest cursor-not-allowed border border-white/5 flex items-center gap-2">
          <i class="fa-solid fa-lock text-xs"></i> Showdown Locked
        </button>
        <button type="button" data-go-tab="missions" class="glass-light text-white px-8 py-3.5 rounded-lg font-bold uppercase tracking-wider hover:bg-white/10 transition-colors border border-white/20">
          Browse Missions
        </button>`;
      visEl.innerHTML = '';
    } else {
      titleEl.innerHTML = `Solo <span class="text-gradient-violet">Operative</span>`;
      descEl.innerHTML = `Welcome, Agent. Start Missions from the database, complete objectives in-game, and earn DC straight to your wallet.`;
      actionsEl.innerHTML = `
        <button type="button" data-go-tab="missions" class="btn-cyber bg-dc-violet hover:bg-purple-500 text-white px-8 py-3.5 font-bold uppercase tracking-widest shadow-[0_0_20px_rgba(138,43,226,0.5)] flex items-center gap-2">
          <i class="fa-solid fa-scroll"></i> Browse Missions
        </button>`;
      visEl.innerHTML = `
        <div class="glass-light rounded-xl p-4 border border-dc-violet/30 w-full relative overflow-hidden">
          <div class="absolute inset-0 bg-dc-violet opacity-10 blur-xl"></div>
          <p class="text-[10px] text-dc-violet uppercase font-bold tracking-widest mb-1 relative z-10">Status</p>
          <p class="font-display font-black text-3xl text-white relative z-10">Independent</p>
        </div>`;
    }
  }

  function renderActionPermissions() {
    const clashBox = document.getElementById('clash-action-container');
    const hitlistBox = document.getElementById('hitlist-action-container');
    const dockCreate = document.getElementById('dock-create-showdown');
    const team = selectedTeam();

    if (canIssueSelectedTeam()) {
      if (dockCreate) {
        dockCreate.removeAttribute('aria-disabled');
        dockCreate.classList.remove('opacity-50', 'cursor-not-allowed');
        dockCreate.title = 'Create a Showdown from your authorized team.';
      }
      clashBox.innerHTML = `
        <button type="button" data-open-slide="create-clash" class="bg-dc-cyan/10 hover:bg-dc-cyan text-dc-cyan hover:text-black border border-dc-cyan/30 px-5 py-2 font-bold text-xs uppercase tracking-widest rounded transition-all shadow-[0_0_15px_rgba(0,229,255,0.1)]">
          Create Showdown
        </button>`;
      hitlistBox.innerHTML = `
        <button type="button" data-open-slide="create-hitlist" class="btn-cyber bg-dc-neon/10 hover:bg-dc-neon text-dc-neon hover:text-white border border-dc-neon/30 px-5 py-2 font-bold text-xs uppercase tracking-widest rounded transition-all shadow-[0_0_15px_rgba(255,0,85,0.2)]">
          Post Bounty
        </button>`;
    } else {
      const reason = team ? 'Team authority required: owner, manager, or captain only' : 'Team authority required to post or claim Bounties';
      if (dockCreate) {
        dockCreate.setAttribute('aria-disabled', 'true');
        dockCreate.classList.add('opacity-50', 'cursor-not-allowed');
        dockCreate.title = reason;
        const sub = dockCreate.querySelector('p:last-child');
        if (sub) sub.textContent = reason;
      }
      clashBox.innerHTML = `<button disabled title="${esc(reason)}" class="bg-white/5 border border-white/10 text-gray-500 px-5 py-2 font-bold text-xs uppercase tracking-widest rounded cursor-not-allowed"><i class="fa-solid fa-lock mr-1"></i> Create Showdown</button>`;
      hitlistBox.innerHTML = `
        <div class="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
          <button disabled title="${esc(reason)}" class="w-full bg-white/5 border border-white/10 text-gray-500 px-5 py-2 font-bold text-xs uppercase tracking-widest rounded cursor-not-allowed">
            <i class="fa-solid fa-lock mr-1"></i> Post Bounty
          </button>
          <p class="mt-2 text-[10px] leading-relaxed text-gray-500">Bounty is team-based. A team posts a Bounty on itself for other teams to claim.</p>
        </div>`;
    }
  }

  // ── Tab switching ─────────────────────────────────────────────────

  function normalizeTab(name) {
    const key = String(name || '').replace(/^#/, '').trim().toLowerCase();
    return TAB_ALIASES[key] || (['showdown', 'missions', 'bounty', 'dropzone'].includes(key) ? key : 'showdown');
  }

  function switchTab(name, opts = {}) {
    const tab = normalizeTab(name);
    STATE.activeTab = tab;
    document.querySelectorAll('.tab-trigger').forEach((t) => {
      const active = normalizeTab(t.dataset.tab) === tab;
      t.classList.toggle('active', active);
      t.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    document.querySelectorAll('.tab-content').forEach((c) => {
      c.classList.toggle('active', c.id === `tab-content-${tab}`);
    });
    if (opts.updateHash && TAB_HASH[tab]) {
      history.replaceState(null, '', `${window.location.pathname}${window.location.search}#${TAB_HASH[tab]}`);
    }
  }

  function gameList() {
    return HUB.games || [];
  }

  function gameByCode(code) {
    const wanted = String(code || '').toUpperCase();
    return gameList().find((g) => String(g.short_code || '').toUpperCase() === wanted) || null;
  }

  function gameById(id) {
    const wanted = String(id || '');
    return gameList().find((g) => String(g.id) === wanted) || null;
  }

  function defaultGameForSelectedTeam() {
    const team = selectedTeam();
    const teamGame = team && team.game_id ? gameById(team.game_id) : null;
    return teamGame ? String(teamGame.short_code || '').toUpperCase() : (gameList()[0] ? String(gameList()[0].short_code || '').toUpperCase() : 'ALL');
  }

  function smartDefaultGameCode() {
    try {
      const sticky = localStorage.getItem('dc_competitive_game_filter');
      if (sticky === 'ALL' || gameByCode(sticky)) return String(sticky).toUpperCase();
    } catch {}
    const preferred = HUB.preferred_game_id ? gameById(HUB.preferred_game_id) : null;
    if (preferred) return String(preferred.short_code || '').toUpperCase();
    return defaultGameForSelectedTeam();
  }

  function gameIconHtml(game, fallbackCode) {
    const code = fallbackCode || (game && game.short_code) || 'ALL';
    const url = game && (game.icon_url || game.logo_url);
    if (url) return `<img src="${esc(url)}" alt="${esc(code)}" class="h-9 w-9 rounded-xl object-cover border border-white/10 shadow-[0_10px_24px_-18px_rgba(0,229,255,.8)]">`;
    return `<span class="h-9 w-9 rounded-xl border border-white/10 bg-white/[0.06] grid place-items-center text-[10px] font-black uppercase text-white">${esc(code === 'ALL' ? 'All' : code)}</span>`;
  }

  function updateGameSelectorUI() {
    const game = STATE.gameFilter === 'ALL' ? null : gameByCode(STATE.gameFilter);
    const icon = document.getElementById('selected-game-icon');
    const name = document.getElementById('selected-game-name');
    const code = document.getElementById('selected-game-code');
    if (icon) icon.innerHTML = gameIconHtml(game, STATE.gameFilter);
    if (name) name.textContent = game ? (game.name || game.short_code || 'Game') : 'All Games';
    if (code) code.textContent = game ? (game.short_code || 'Game') : 'Global filter';
    document.querySelectorAll('.game-option').forEach((b) => {
      const active = String(b.dataset.gameCode || 'ALL').toUpperCase() === String(STATE.gameFilter || 'ALL').toUpperCase();
      b.classList.toggle('bg-dc-cyan/10', active);
      b.classList.toggle('border-l-2', active);
      b.classList.toggle('border-dc-cyan', active);
      b.classList.toggle('text-white', active);
      b.setAttribute('aria-selected', active ? 'true' : 'false');
    });
  }

  function closeGameSelector() {
    const menu = document.getElementById('game-selector-menu');
    const trigger = document.getElementById('game-selector-trigger');
    if (menu) menu.classList.remove('is-open');
    if (menu) menu.setAttribute('aria-hidden', 'true');
    if (trigger) trigger.setAttribute('aria-expanded', 'false');
  }

  function setGameFilter(code, opts = {}) {
    STATE.gameFilter = code || 'ALL';
    if (opts.manual) STATE.gameManuallySelected = true;
    if (opts.manual) {
      try { localStorage.setItem('dc_competitive_game_filter', String(STATE.gameFilter || 'ALL').toUpperCase()); } catch {}
    }
    updateGameSelectorUI();
    renderAllFeeds();
  }

  function filterByGame(items) {
    if (STATE.gameFilter === 'ALL') return items;
    const selected = String(STATE.gameFilter || '').toUpperCase();
    return items.filter((it) => {
      const code = String(it.game_short_code || (it.template && it.template.game_short_code) || '').toUpperCase();
      return code === selected;
    });
  }

  function filterBySearch(items) {
    const q = (STATE.searchQuery || '').trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => JSON.stringify(it).toLowerCase().includes(q));
  }

  function applyFilters(items) {
    return filterBySearch(filterByGame(items || []));
  }

  // ── Empty / closure helpers ───────────────────────────────────────

  function closureHtml(item) {
    if (!item || !item.closure_reason) return '';
    const note = item.closure_note || item.closure_reason_display || item.closure_reason;
    const isAmber = /EXPIRED|NO_SHOW|CANCELLED_INSUFFICIENT/i.test(item.closure_reason);
    const colors = isAmber
      ? 'bg-dc-warning/10 border-dc-warning/40 text-dc-warning'
      : 'bg-dc-neon/10 border-dc-neon/40 text-dc-neon';
    return `
      <div class="mt-3 inline-flex items-center gap-2 px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-widest border ${colors}">
        <span class="w-1.5 h-1.5 rounded-full bg-current"></span>
        Closed: ${esc(note)}
      </div>`;
  }

  function emptyState({ icon, title, sub, ctaText, ctaTab }) {
    return `
      <div class="dcx-empty surface-card rounded-3xl p-8 sm:p-10 text-center relative overflow-hidden">
        <div class="absolute inset-0 pointer-events-none opacity-[0.12]"
             style="background-image: linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px); background-size: 30px 30px; -webkit-mask-image: radial-gradient(circle at center, black 24%, transparent 74%); mask-image: radial-gradient(circle at center, black 24%, transparent 74%);"></div>
        <div class="relative">
          <div class="mx-auto mb-4 h-16 w-16 rounded-3xl border border-white/10 bg-white/[0.045] grid place-items-center shadow-[0_18px_50px_-34px_rgba(0,229,255,.8)]">
            <i class="fa-solid ${icon} text-2xl text-gray-400"></i>
          </div>
          <p class="font-display text-xl font-black text-white mb-1">${esc(title)}</p>
          <p class="text-gray-400 text-sm max-w-md mx-auto leading-relaxed mb-5">${esc(sub)}</p>
          ${ctaText ? `<button type="button" data-go-tab="${esc(ctaTab || '')}" class="interactive-lift inline-flex items-center gap-2 rounded-xl bg-dc-cyan/15 border border-dc-cyan/35 text-dc-cyan hover:bg-dc-cyan hover:text-black px-5 py-2.5 text-xs font-bold uppercase tracking-widest transition-all">${esc(ctaText)} <i class="fa-solid fa-arrow-right text-[10px]"></i></button>` : ''}
        </div>
      </div>`;
  }

  // ── Feed renderers ────────────────────────────────────────────────

  function renderClashFeed() {
    const feed = document.getElementById('showdown-feed');
    const list = applyFilters((STATE.data.showdown || []).filter((c) => Number(c.entry_fee_dc || 0) > 0));
    if (!list.length) {
      feed.innerHTML = emptyState({
        icon: 'fa-radar',
        title: 'Radar Silent',
        sub: 'No open Showdowns match your filters right now.',
        ctaText: canIssueSelectedTeam() ? 'Create Showdown' : null,
        ctaTab: null,
      });
      return;
    }
    feed.innerHTML = list.map((c) => {
      const pot = Number(c.prize_pot_dc || (c.entry_fee_dc * 2));
      const closed = !!c.closure_reason;
      const isHigh = Number(c.entry_fee_dc) >= 1000;
      const canAccept = canIssueSelectedTeam() && !closed && c.status === 'OPEN' && !c.challenged_team_id;
      const btnState = canAccept ? '' : 'disabled';
      const btnClass = canAccept
        ? 'bg-white/10 hover:bg-dc-cyan hover:text-black border-white/20 hover:border-dc-cyan text-white'
        : 'bg-black/40 border-white/5 text-gray-600 cursor-not-allowed';
      const btnText = canAccept
        ? 'Accept Match'
        : (HUB.primary_team ? '<i class="fa-solid fa-lock text-[10px]"></i> Captain Only' : '<i class="fa-solid fa-lock text-[10px]"></i> Team Reqd');

      return `
        <div class="glass-heavy ${isHigh ? 'accent-gold' : 'accent-cyan'} rounded-2xl p-4 flex flex-col lg:flex-row items-center justify-between gap-5 group relative overflow-hidden fade-enter border border-white/5 transition-all">
          <div class="flex items-center gap-4 flex-1 w-full relative z-10">
            <div class="relative flex-shrink-0 w-14 h-14 rounded-xl border ${isHigh ? 'border-dc-gold/50 shadow-[0_0_15px_rgba(255,215,0,0.3)]' : 'border-white/10'} bg-gradient-to-br from-gray-800 to-black flex items-center justify-center text-white font-bold">
              ${esc((c.challenger_team_tag || c.challenger_team_name || '?').slice(0, 2).toUpperCase())}
            </div>
            <div>
              <div class="flex items-center gap-2 mb-0.5">
                <h3 class="font-bold text-white text-xl leading-tight">${esc(c.challenger_team_name || 'Team')}</h3>
                ${isHigh ? `<span class="bg-dc-gold/20 text-dc-gold text-[9px] px-1.5 py-0.5 rounded font-black uppercase tracking-widest border border-dc-gold/30">Featured</span>` : ''}
              </div>
              <p class="text-xs text-gray-400 font-medium">${esc(c.game_short_code || '')} &bull; ${esc(c.challenged_team_name || 'Open Radar')}</p>
              ${closureHtml(c)}
            </div>
          </div>
          <div class="flex items-center gap-6 lg:px-8 lg:border-x border-white/10 flex-shrink-0 w-full lg:w-auto justify-between lg:justify-center bg-black/30 lg:bg-transparent p-4 lg:p-0 rounded-xl relative z-10">
            <div class="text-center">
              <p class="text-[10px] uppercase font-bold text-gray-500 tracking-widest mb-1">Format</p>
              <span class="inline-block px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-xs font-bold text-white">BO${c.best_of || 1}</span>
            </div>
            <div class="text-center">
              <p class="text-[10px] uppercase font-bold ${isHigh ? 'text-dc-gold' : 'text-gray-500'} tracking-widest mb-1">Reward Pool</p>
              <p class="font-display font-black text-2xl ${isHigh ? 'text-dc-gold' : 'text-white'} leading-none">
                <i class="fa-solid fa-coins text-sm mr-1 ${isHigh ? '' : 'text-dc-gold'}"></i>${pot.toLocaleString()}
              </p>
            </div>
          </div>
          <div class="flex-shrink-0 w-full lg:w-auto relative z-10">
            <button ${btnState} data-accept-clash="${esc(c.id)}" data-fee="${Number(c.entry_fee_dc)}" data-challenger-team="${esc(c.challenger_team_id || '')}"
                    class="w-full lg:w-auto ${btnClass} border px-8 py-3 rounded-xl text-sm font-bold uppercase tracking-wider transition-all">
              ${btnText} <span class="ml-1 opacity-70">(${Number(c.entry_fee_dc).toLocaleString()} DC)</span>
            </button>
          </div>
        </div>`;
    }).join('');
  }

  function renderContractsFeed() {
    const feed = document.getElementById('missions-feed');
    const list = applyFilters(STATE.data.missions);
    if (!list.length) {
      feed.innerHTML = `<div class="col-span-full">${emptyState({ icon: 'fa-scroll', title: 'No Missions Available', sub: 'Mission board is quiet. Check back when fresh objectives drop.' })}</div>`;
      return;
    }
    feed.innerHTML = list.map((t) => {
      const fee = Number(t.entry_fee_dc || 0);
      const reward = Number(t.reward_dc || 0);
      const missionText = `${t.title || ''} ${t.goal_type_display || ''} ${t.reset_period || ''} ${t.frequency || ''}`.toLowerCase();
      const cadence = missionText.includes('daily') ? 'Daily' : (missionText.includes('weekly') ? 'Weekly' : 'Admin Curated');
      return `
        <div class="glass-heavy accent-violet rounded-2xl p-1 relative overflow-hidden group fade-enter border border-white/5 transition-all">
          <div class="absolute inset-0 bg-gradient-to-br from-dc-violet/10 to-transparent opacity-40 z-0"></div>
          <div class="bg-black/60 rounded-xl p-5 h-full flex flex-col relative z-10 border border-white/5">
            <div class="flex justify-between items-start mb-4">
              <div class="w-12 h-12 bg-dc-violet/20 rounded-xl flex items-center justify-center border border-dc-violet/30 text-dc-violet">
                <i class="fa-solid fa-scroll text-xl"></i>
              </div>
              <div class="flex flex-col items-end gap-1">
                <span class="bg-dc-violet/10 text-dc-violet text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded border border-dc-violet/25">${esc(cadence)}</span>
                <span class="bg-black/80 text-gray-300 text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded border border-white/10">${esc(t.goal_type_display || 'MISSION')}</span>
              </div>
            </div>
            <h3 class="font-display text-2xl font-bold text-white mb-2 group-hover:text-dc-violet transition-colors">${esc(t.title)}</h3>
            <p class="text-sm text-gray-400 mb-6 flex-grow leading-relaxed font-medium line-clamp-3">${esc(t.description || '')}</p>
            <div class="bg-black/50 rounded-xl p-3 border border-white/5 flex justify-between items-center mb-3">
              <div>
                <p class="text-[9px] uppercase font-bold text-gray-500 mb-0.5 tracking-widest">Entry</p>
                <p class="font-bold text-white text-sm"><i class="fa-solid fa-coins text-dc-gold text-[10px] mr-1"></i> ${fee.toLocaleString()}</p>
              </div>
              <i class="fa-solid fa-arrow-right text-gray-600 text-xs"></i>
              <div class="text-right">
                <p class="text-[9px] uppercase font-bold text-dc-gold mb-0.5 tracking-widest">Reward</p>
                <p class="font-bold text-dc-gold text-xl leading-none"><i class="fa-solid fa-coins text-[10px] mr-1"></i> ${reward.toLocaleString()}</p>
              </div>
            </div>
            <button type="button" data-enroll-contract="${esc(t.id)}" data-fee="${fee}"
                    class="w-full bg-white/5 hover:bg-white text-white hover:text-black border border-white/10 hover:border-white py-2.5 rounded-lg text-xs font-bold uppercase tracking-widest transition-all">
              Start Mission
            </button>
          </div>
        </div>`;
    }).join('');
  }

  function renderHitlistFeed() {
    const feed = document.getElementById('bounty-feed');
    const list = applyFilters((STATE.data.bounty || []).filter((b) => !!b.is_hitlist));
    if (!list.length) {
      feed.innerHTML = emptyState({
        icon: 'fa-skull',
        title: 'No Bounties Open',
        sub: 'No open Bounty challenges match your filters right now.',
      });
      return;
    }
    feed.innerHTML = list.map((b) => {
      const reward = Number(b.reward_amount_dc || 0);
      const entry = Number(b.challenger_entry_fee_dc || 0);
      const closed = !!b.closure_reason;
      const team = selectedTeam();
      const isOwnBounty = team && b.issuer_team_id && String(b.issuer_team_id) === String(team.id);
      const canHunt = canIssueSelectedTeam() && !closed && b.is_claimable && !isOwnBounty;
      const btnState = canHunt ? '' : 'disabled';
      const btnClass = canHunt ? 'bg-dc-neon hover:bg-red-600 text-white shadow-[0_0_20px_rgba(255,0,85,0.3)]' : 'bg-black/40 border border-white/5 text-gray-600 cursor-not-allowed';
      const btnText = canHunt ? 'Claim Bounty' : (isOwnBounty ? '<i class="fa-solid fa-shield-halved mr-1"></i> Your Bounty' : (selectedTeam() ? '<i class="fa-solid fa-lock mr-1"></i> Captain Only' : '<i class="fa-solid fa-lock mr-1"></i> Team Reqd'));
      const teamLogo = cleanBountyLogoUrl(b.issuer_team_logo_url);
      const teamInitials = esc((b.issuer_team_name || '?').slice(0, 2).toUpperCase());
      const avatarHtml = teamLogo
        ? `<img src="${esc(teamLogo)}" alt="${esc(b.issuer_team_name || 'Team')}" data-bounty-logo class="block"><span class="hidden">${teamInitials}</span>`
        : `<span>${teamInitials}</span>`;
      return `
        <div class="glass-heavy accent-neon rounded-2xl p-6 relative overflow-hidden group fade-enter border border-white/5 transition-all">
          <div class="absolute inset-0 bg-gradient-to-r from-dc-neon/10 to-transparent z-0 opacity-40"></div>
          <div class="relative z-10 flex flex-col md:flex-row gap-8 items-center">
            <div class="flex-shrink-0 text-center">
              <div class="relative inline-block mb-3">
                <div class="absolute inset-[-6px] bg-dc-neon blur-[26px] opacity-20 rounded-[2.25rem]"></div>
                <div class="bounty-team-mark relative z-10 overflow-hidden ${teamLogo ? '' : 'is-fallback'}" data-has-logo="${teamLogo ? 'true' : 'false'}">
                  ${avatarHtml}
                </div>
              </div>
              <div class="mb-2 flex justify-center">
                <span class="inline-flex items-center gap-1.5 rounded-full border border-dc-neon/35 bg-dc-neon/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-dc-neon">
                  <i class="fa-solid fa-crosshairs text-[9px]"></i> Bounty
                </span>
              </div>
              <h3 class="font-bold text-2xl text-white">${esc(b.issuer_team_name || 'Team')}</h3>
              <p class="text-xs font-bold text-dc-cyan uppercase tracking-widest mt-1">${esc(b.game_short_code || '')}</p>
            </div>
            <div class="flex-grow w-full bg-black/60 rounded-2xl p-6 border border-white/5 relative">
              <i class="fa-solid fa-quote-left absolute top-5 left-5 text-4xl text-white/5"></i>
              <p class="text-base text-gray-300 italic mb-6 relative z-10 pl-8 border-l-2 border-dc-neon/50 leading-relaxed font-medium">"${esc(b.title || 'Beat us.')}"</p>
              ${closureHtml(b)}
              <div class="flex flex-col sm:flex-row items-center justify-between gap-5 border-t border-white/10 pt-5 mt-2">
                <div class="flex gap-8">
                  <div>
                    <p class="text-[10px] uppercase font-bold text-gray-500 tracking-widest mb-1">Challenger Entry</p>
                    <p class="font-bold text-white text-lg"><i class="fa-solid fa-coins text-dc-gold text-sm mr-1"></i> ${entry.toLocaleString()} DC</p>
                  </div>
                  <div>
                    <p class="text-[10px] uppercase font-black text-dc-neon tracking-widest mb-1">Bounty Reward</p>
                    <p class="font-display font-black text-3xl text-white leading-none drop-shadow-[0_0_15px_rgba(255,0,85,0.5)]">
                      <i class="fa-solid fa-coins text-dc-gold text-xl mr-1"></i> ${reward.toLocaleString()}
                    </p>
                  </div>
                </div>
                <button ${btnState} data-hunt-bounty="${esc(b.id)}" data-fee="${entry}"
                        class="w-full sm:w-auto ${btnClass} px-10 py-3.5 rounded-xl font-bold text-sm uppercase tracking-widest transition-all">
                  ${btnText}
                </button>
              </div>
            </div>
          </div>
        </div>`;
    }).join('');
  }

  function renderRoyaleFeed() {
    const feed = document.getElementById('dropzone-feed');
    const list = applyFilters(STATE.data.dropzone);
    if (!list.length) {
      feed.innerHTML = `<div class="col-span-full">${emptyState({ icon: 'fa-crown', title: 'No Lobbies Scheduled', sub: 'Custom rooms drop on the schedule. Check back soon.' })}</div>`;
      return;
    }
    feed.innerHTML = list.map((l, idx) => {
      const fee = Number(l.entry_fee_per_slot_dc || 0);
      const max = Number(l.max_slots || 0);
      const taken = Number(l.reserved_slots || 0);
      const remaining = Number(l.remaining_slots || Math.max(0, max - taken));
      const closed = !!l.closure_reason;
      const sched = l.scheduled_at ? new Date(l.scheduled_at) : null;
      const schedText = sched ? sched.toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
      const fillPct = max ? Math.min(100, Math.round((taken / max) * 100)) : 0;
      const splits = (l.prize_distribution && l.prize_distribution.splits) || {};
      const mode = (l.prize_distribution && l.prize_distribution.mode) || 'PERCENT';
      const lobbyUrl = `/dashboard/competitive/dropzone/lobbies/${esc(l.id)}/`;
      const status = String(l.status || '').toUpperCase();
      const phase = status.includes('SETTLED') || status.includes('SCORED') ? 5 : status.includes('SCOR') || status.includes('LIVE') ? 4 : status.includes('READY') || status.includes('REVEAL') ? 3 : taken > 0 ? 2 : 1;
      const featured = idx === 0 || fillPct >= 70;
      const splitChips = Object.keys(splits).sort((a, b) => +a - +b).slice(0, 5).map((k) =>
        `<span class="font-mono text-[10px] text-dc-gold">#${esc(k)}: ${esc(splits[k])}${mode === 'PERCENT' ? '%' : ' DC'}</span>`
      ).join('<span class="text-gray-700">&middot;</span>');
      const canReserve = !closed && remaining > 0;
      const urgency = canReserve && remaining <= Math.max(3, Math.ceil(max * 0.12));
      return `
        <div class="glass-heavy accent-gold rounded-3xl p-5 md:p-6 relative overflow-hidden group fade-enter border border-white/5 transition-all ${featured ? 'md:col-span-2' : ''}">
          <div class="absolute inset-0 opacity-60 pointer-events-none" style="background: linear-gradient(135deg, rgba(255,215,0,.10), transparent 38%), radial-gradient(circle at 86% 18%, rgba(0,229,255,.08), transparent 32%);"></div>
          <div class="relative z-10 grid ${featured ? 'lg:grid-cols-[1.15fr_.85fr]' : 'grid-cols-1'} gap-5">
            <div>
              <div class="flex items-start justify-between gap-3 mb-4">
                <div>
                  <div class="flex items-center gap-2 mb-2">
                    <span class="px-2.5 py-1 rounded-full bg-dc-gold/15 border border-dc-gold/30 text-dc-gold text-[9px] font-black uppercase tracking-widest">${esc(l.game_short_code || 'DROPZONE')}</span>
                    ${featured ? '<span class="px-2.5 py-1 rounded-full bg-dc-cyan/10 border border-dc-cyan/25 text-dc-cyan text-[9px] font-black uppercase tracking-widest">Featured Lobby</span>' : ''}
                    ${urgency ? '<span class="px-2.5 py-1 rounded-full bg-dc-neon/10 border border-dc-neon/25 text-dc-neon text-[9px] font-black uppercase tracking-widest">Filling Fast</span>' : ''}
                  </div>
                  <h3 class="font-display font-black text-white text-3xl leading-tight">${esc(l.title)}</h3>
                </div>
                <span class="px-2 py-1 rounded bg-white/5 border border-white/10 text-[9px] font-bold uppercase tracking-widest text-gray-300">${esc(l.status_display || l.status)}</span>
              </div>
            ${closureHtml(l)}
              ${closed ? '' : (sched ? `<p class="text-xs text-gray-400 mb-4 font-mono"><i class="fa-solid fa-clock text-dc-cyan mr-1"></i> ${esc(schedText)}</p>` : '')}
              <div class="status-rail text-dc-gold mb-4" aria-label="Dropzone lifecycle">
                ${[1, 2, 3, 4, 5].map((i) => `<span class="${i <= phase ? 'is-on' : ''}"></span>`).join('')}
              </div>
              <div class="grid grid-cols-3 gap-2 mb-4">
                <div class="rounded-2xl border border-white/[0.08] bg-black/30 p-3">
                  <p class="text-[9px] uppercase tracking-widest text-gray-500 font-black">Slots</p>
                  <p class="font-display text-2xl font-black text-white">${taken}<span class="text-sm text-gray-500">/${max}</span></p>
                </div>
                <div class="rounded-2xl border border-white/[0.08] bg-black/30 p-3">
                  <p class="text-[9px] uppercase tracking-widest text-gray-500 font-black">Left</p>
                  <p class="font-display text-2xl font-black text-dc-cyan">${remaining}</p>
                </div>
                <div class="rounded-2xl border border-dc-gold/20 bg-dc-gold/10 p-3">
                  <p class="text-[9px] uppercase tracking-widest text-dc-gold/70 font-black">Entry</p>
                  <p class="font-display text-2xl font-black text-dc-gold">${fee}</p>
                </div>
              </div>
              <div class="mb-4">
                <div class="flex items-center justify-between text-[10px] font-mono text-gray-500 mb-1.5">
                  <span>Capacity</span>
                  <span>${fillPct}% filled</span>
                </div>
                <div class="h-2 rounded-full bg-white/[0.06] overflow-hidden">
                  <div class="h-full" style="width: ${fillPct}%; background: linear-gradient(90deg, #00e5ff, #ffd700); box-shadow: 0 0 12px rgba(255,215,0,.55)"></div>
                </div>
              </div>
              <div class="flex items-center gap-2 flex-wrap">
                ${splitChips ? `<div class="flex items-center gap-1.5 flex-wrap">${splitChips}</div>` : '<span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold">Reward distribution pending</span>'}
              </div>
            </div>
            <div class="flex flex-col justify-between rounded-3xl border border-white/[0.08] bg-black/35 p-4">
              <div>
                <p class="text-[10px] uppercase tracking-widest text-gray-500 font-black mb-2">Room Reveal</p>
                <p class="text-sm text-gray-300 leading-relaxed">${status.includes('LIVE') || status.includes('READY') ? 'Room details may be available to reserved entrants on the detail page.' : 'Room credentials stay hidden until the configured reveal window.'}</p>
                <div class="mt-4 grid grid-cols-2 gap-2">
                  <div class="rounded-2xl border border-white/[0.08] bg-black/30 p-3">
                    <p class="text-[9px] uppercase tracking-widest text-gray-500 font-black">Queue State</p>
                    <p class="mt-1 text-xs font-black uppercase ${urgency ? 'text-dc-neon' : 'text-dc-cyan'}">${urgency ? 'Filling Fast' : (canReserve ? 'Open' : 'Closed')}</p>
                  </div>
                  <div class="rounded-2xl border border-white/[0.08] bg-black/30 p-3">
                    <p class="text-[9px] uppercase tracking-widest text-gray-500 font-black">Launch</p>
                    <p class="mt-1 text-xs font-black text-white">${schedText ? esc(schedText) : 'TBA'}</p>
                  </div>
                </div>
                <div class="mt-4 rounded-2xl border border-white/[0.08] bg-white/[0.03] p-3">
                  <p class="text-[10px] uppercase tracking-widest text-gray-500 font-black">Results Preview</p>
                  <p class="text-xs text-gray-400 mt-1">${phase >= 4 ? 'Scoring/review is in progress or complete. Open lobby details for standings.' : 'Leaderboard appears after scoring starts.'}</p>
                </div>
              </div>
              <div class="grid grid-cols-1 gap-2 mt-5">
                <a href="${lobbyUrl}" class="inline-flex items-center justify-center rounded-xl border border-dc-gold/25 bg-dc-gold/10 px-3 py-3 text-xs font-black uppercase tracking-widest text-dc-gold hover:bg-dc-gold/20">
                  View Lobby
                </a>
                <button ${canReserve ? '' : 'disabled'} data-reserve-royale="${esc(l.id)}" data-fee="${fee}"
                        class="btn-cyber w-full bg-dc-gold hover:bg-yellow-400 text-black font-black uppercase tracking-widest py-3 transition-all ${canReserve ? '' : 'opacity-50 cursor-not-allowed'}">
                  Reserve Slot
                </button>
              </div>
            </div>
          </div>
        </div>`;
    }).join('');
  }

  function isTeamOp(op) {
    return ['scrim', 'tryout', 'practice', 'vod_review'].includes(String(op.type || ''));
  }

  function isReviewOp(op) {
    const haystack = `${op.status || ''} ${op.next_action_label || ''} ${op.review_state_label || ''}`.toLowerCase();
    return op.is_action_required || /review|dispute|proof|confirmation|rejected|conflict/.test(haystack);
  }

  function isTerminalOp(op) {
    return /SETTLED|COMPLETED|PAID|REJECTED|REFUNDED|VOIDED|CANCELLED|EXPIRED|SIGNED|DECLINED/i.test(op.status || '');
  }

  function hasMatchRoomReady(op) {
    const label = `${op.status || ''} ${op.next_action_label || ''}`.toLowerCase();
    return !!op.match_room_url || /match room|room details|enter/.test(label);
  }

  function operationMatchesSelectedTeam(op) {
    if (!STATE.operatingTeamId) return true;
    if (['mission', 'dropzone'].includes(String(op.type || ''))) return true;
    const team = selectedTeam();
    const selectedName = team && team.name ? String(team.name).toLowerCase() : '';
    const selectedId = String(STATE.operatingTeamId);
    if (op.team_id != null && String(op.team_id) === selectedId) return true;
    if (op.issuer_team_id != null && String(op.issuer_team_id) === selectedId) return true;
    if (op.claiming_team_id != null && String(op.claiming_team_id) === selectedId) return true;
    if (op.challenger_team_id != null && String(op.challenger_team_id) === selectedId) return true;
    if (op.challenged_team_id != null && String(op.challenged_team_id) === selectedId) return true;
    if (selectedName && op.team_name && String(op.team_name).toLowerCase() === selectedName) return true;
    return false;
  }

  function scopedOperations() {
    return (STATE.data.myOperations || []).filter(operationMatchesSelectedTeam);
  }

  function renderCommandMetrics() {
    const operations = scopedOperations();
    const now = Date.now();
    const upcoming = operations.filter((op) => {
      const dt = op.scheduled_at || op.starts_at;
      return dt && new Date(dt).getTime() >= now;
    }).length;
    const review = operations.filter(isReviewOp).length;
    const teamOps = operations.filter(isTeamOp).length;
    const rewards = operations.reduce((sum, op) => sum + Number(op.reward_dc || 0), 0);
    const set = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
    set('metric-active-ops', operations.length.toLocaleString());
    set('metric-upcoming', upcoming.toLocaleString());
    set('metric-review', review.toLocaleString());
    set('metric-team-ops', teamOps.toLocaleString());
    set('metric-rewards', rewards ? `${rewards.toLocaleString()}` : '0');
    set('ctx-stat-1', operations.length ? operations.length.toLocaleString() : '0');
    renderGuidance();
    renderEcosystemFlow();
    renderTelemetry();
  }

  function guidanceItems() {
    const ops = scopedOperations();
    const reviews = ops.filter(isReviewOp);
    const needsAction = ops.filter((op) => !!op.is_action_required);
    const openShowdowns = (STATE.data.showdown || []).filter((c) => Number(c.entry_fee_dc || 0) > 0 && c.status === 'OPEN');
    const openBounties = (STATE.data.bounty || []).filter((b) => !!b.is_hitlist && b.is_claimable);
    const dropzones = STATE.data.dropzone || [];
    const reservableDropzone = dropzones.find((l) => {
      const max = Number(l.capacity || l.max_slots || 0);
      const taken = Number(l.reserved_count || l.entries_count || 0);
      const status = String(l.status || '').toUpperCase();
      return max > taken && !/SETTLED|CANCELLED|CLOSED|COMPLETED/.test(status);
    });
    const items = [];

    if (needsAction.length) {
      items.push({
        type: 'action',
        icon: 'fa-bolt',
        color: 'text-dc-cyan',
        title: `${needsAction.length} operation${needsAction.length === 1 ? '' : 's'} need action`,
        body: 'Result, proof, room, or offer steps are waiting in My Operations.',
        tab: 'operations',
      });
    }
    if (reviews.length) {
      items.push({
        type: 'review',
        icon: 'fa-shield-halved',
        color: 'text-dc-neon',
        title: 'Review state detected',
        body: 'Proof, confirmation, or dispute items are being tracked in the review layer.',
        tab: 'review',
      });
    }
    if (!ops.some((op) => op.type === 'showdown')) {
      items.push({
        type: 'showdown',
        icon: 'fa-bolt',
        color: 'text-dc-cyan',
        title: 'You do not have an active Showdown',
        body: canIssueSelectedTeam() ? 'Create one from your authorized team or accept an open radar match.' : 'Captain or manager authority is required for Showdowns.',
        tab: 'showdown',
      });
    }
    if (canIssueSelectedTeam() && openBounties.length) {
      items.push({
        type: 'bounty',
        icon: 'fa-crosshairs',
        color: 'text-dc-neon',
        title: 'Bounty board has claimable rewards',
        body: 'Your team can claim an open Bounty if the rules and entry fee fit.',
        tab: 'bounty',
      });
    }
    if (reservableDropzone) {
      items.push({
        type: 'dropzone',
        icon: 'fa-map-location-dot',
        color: 'text-dc-gold',
        title: 'Dropzone reservations are open',
        body: `${reservableDropzone.title || 'A lobby'} still has slots available.`,
        tab: 'dropzone',
      });
    }
    if (!HUB.primary_team) {
      items.push({
        type: 'mission',
        icon: 'fa-scroll',
        color: 'text-dc-violet',
        title: 'Solo path available',
        body: 'Missions are the fastest way to participate without team authority.',
        tab: 'missions',
      });
    }
    if (!items.length) {
      items.push({
        type: 'ready',
        icon: 'fa-circle-check',
        color: 'text-dc-success',
        title: 'Command state is clear',
        body: openShowdowns.length ? 'Open Showdowns are available if you want the next match.' : 'Browse Missions, Bounty, or Dropzone to start a new operation.',
        tab: openShowdowns.length ? 'showdown' : 'missions',
      });
    }
    return items.slice(0, 4);
  }

  function renderGuidance() {
    const feed = document.getElementById('guidance-feed');
    const side = document.getElementById('objectives-feed');
    const items = guidanceItems();
    const html = items.map((item) => `
      <button type="button" data-go-tab="${esc(item.tab)}" class="guidance-card ${item.color} text-left p-4 hover:bg-white/[0.045] transition group">
        <div class="flex items-start gap-3">
          <div class="h-9 w-9 rounded-xl border border-white/10 bg-white/[0.04] grid place-items-center shrink-0">
            <i class="fa-solid ${item.icon} text-sm"></i>
          </div>
          <div class="min-w-0">
            <p class="text-sm font-black text-white leading-snug">${esc(item.title)}</p>
            <p class="mt-1 text-[11px] leading-relaxed text-gray-400">${esc(item.body)}</p>
          </div>
          <i class="fa-solid fa-arrow-right text-[10px] text-gray-600 group-hover:text-white ml-auto mt-1"></i>
        </div>
      </button>`).join('');
    if (feed) feed.innerHTML = html;
    if (side) side.innerHTML = items.slice(0, 3).map((item) => `
      <button type="button" data-go-tab="${esc(item.tab)}" class="interactive-lift w-full text-left rounded-2xl border border-white/[0.08] bg-white/[0.03] p-3 hover:bg-white/[0.06] hover:border-white/[0.15] transition">
        <div class="flex items-center gap-3">
          <span class="h-9 w-9 rounded-xl border border-white/10 bg-black/25 grid place-items-center shrink-0"><i class="fa-solid ${item.icon} ${item.color}"></i></span>
          <div class="min-w-0">
            <p class="text-xs font-bold text-white truncate">${esc(item.title)}</p>
            <p class="text-[10px] text-gray-500 truncate">${esc(item.body)}</p>
          </div>
        </div>
      </button>`).join('');
  }

  function renderEcosystemFlow() {
    const el = document.getElementById('ecosystem-flow');
    if (!el) return;
    const flows = [
      { tab: 'showdown', icon: 'fa-bolt', color: 'text-dc-cyan', label: 'Showdown', steps: ['Create', 'Match Room', 'Result', 'Review', 'Settled'] },
      { tab: 'missions', icon: 'fa-scroll', color: 'text-dc-violet', label: 'Missions', steps: ['Start', 'Progress', 'Proof', 'Review', 'Reward'] },
      { tab: 'bounty', icon: 'fa-crosshairs', color: 'text-dc-neon', label: 'Bounty', steps: ['Place', 'Claim', 'Match Room', 'Verify', 'Settle'] },
      { tab: 'dropzone', icon: 'fa-map-location-dot', color: 'text-dc-gold', label: 'Dropzone', steps: ['Reserve', 'Reveal', 'Lobby', 'Scoring', 'Results'] },
    ];
    el.innerHTML = flows.map((flow) => `
      <button type="button" data-go-tab="${esc(flow.tab)}" class="w-full flow-node hover:border-white/20 transition text-left">
        <div class="flex flex-col sm:flex-row sm:items-center gap-3">
          <div class="flex items-center gap-2 w-32 shrink-0">
            <i class="fa-solid ${flow.icon} ${flow.color}"></i>
            <span class="text-xs font-black text-white uppercase tracking-widest">${esc(flow.label)}</span>
          </div>
          <div class="flex-1 grid grid-cols-5 gap-1.5">
            ${flow.steps.map((step, index) => `
              <span class="rounded-lg border border-white/[0.08] bg-white/[0.035] px-2 py-1.5 text-center text-[9px] font-bold uppercase tracking-wider ${index === 0 ? flow.color : 'text-gray-500'}">${esc(step)}</span>
            `).join('')}
          </div>
        </div>
      </button>`).join('');
  }

  function renderTelemetry() {
    const el = document.getElementById('telemetry-list');
    if (!el) return;
    const ops = scopedOperations().slice(0, 6);
    const recent = ops.length ? ops : [
      { type: 'showdown', title: 'Showdown flow ready', next_action_label: 'Open Radar', status: 'READY' },
      { type: 'mission', title: 'Mission proof/review available', next_action_label: 'Browse Missions', status: 'READY' },
      { type: 'dropzone', title: 'Dropzone lobby browser online', next_action_label: 'View Dropzone', status: 'READY' },
    ];
    el.innerHTML = recent.map((op) => {
      const meta = operationTypeMeta(op.type);
      return `
        <div class="relative pl-5 pb-4 border-l border-white/10 last:pb-0">
          <span class="absolute -left-1.5 top-1 h-3 w-3 rounded-full ${meta.dot} shadow-[0_0_12px_currentColor]"></span>
          <p class="text-xs font-bold text-white">${esc(op.next_action_label || op.status || 'Updated')}</p>
          <p class="text-[11px] text-gray-500 mt-0.5">${esc(op.title || meta.label)}</p>
        </div>`;
    }).join('');
  }

  function operationProgressIndex(op) {
    const label = `${op.status || ''} ${op.next_action_label || ''} ${op.review_state_label || ''}`.toLowerCase();
    if (/settled|completed|signed|accepted|view result|confirmed/.test(label)) return 5;
    if (/review|dispute|proof|confirmation|scoring/.test(label)) return 4;
    if (/match room|scheduled|room details|awaiting results/.test(label)) return 3;
    if (/accepted|reserved|active|track/.test(label)) return 2;
    return 1;
  }

  function operationStatusClass(op) {
    const label = `${op.status || ''} ${op.next_action_label || ''} ${op.review_state_label || ''}`.toLowerCase();
    if (/dispute|conflict/.test(label)) return 'dcx-status-disputed';
    if (/review|proof|confirmation|scoring/.test(label)) return 'dcx-status-review';
    if (/settled|completed|signed|accepted|view result|confirmed/.test(label)) return 'dcx-status-completed';
    if (/refund|void|cancel/.test(label)) return 'dcx-status-refunded';
    if (/fail|reject|not selected|expired/.test(label)) return 'dcx-status-failed';
    if (/match room|room details|ready|live|submit result/.test(label)) return 'dcx-status-live';
    if (/waiting|pending|scheduled|reserved|active|track/.test(label)) return 'dcx-status-waiting';
    return 'dcx-status-ready';
  }

  function renderOperationCard(op, { compact = false } = {}) {
    const typeMeta = operationTypeMeta(op.type);
    const actionUrl = op.next_action_url || op.match_room_url || op.detail_url || '#';
    const opStatus = String(op.status || '').toUpperCase();
    const isPrimarySubmit = op.type === 'showdown' && op.next_action_label === 'Submit Result';
    const canSecondarySubmit = op.type === 'showdown' && !op.match_room_url && ['ACCEPTED', 'SCHEDULED', 'IN_PROGRESS'].includes(opStatus);
    const game = op.game && (op.game.short_code || op.game.name) ? (op.game.short_code || op.game.name) : 'ANY';
    const scheduled = op.scheduled_at || op.starts_at;
    const scheduledText = scheduled ? new Date(scheduled).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
    const fee = Number(op.entry_fee_dc || 0);
    const reward = op.reward_dc != null ? `${Number(op.reward_dc || 0).toLocaleString()} DC reward` : (op.reward_summary || '');
    const actionClass = op.is_action_required ? 'text-dc-cyan border-dc-cyan/30 bg-dc-cyan/10' : 'text-gray-300 border-white/10 bg-white/5';
    const detailUrl = op.detail_url || '';
    const showDetailLink = detailUrl && detailUrl !== actionUrl;
    const lobbyDetailUrl = op.lobby_detail_url || '';
    const reviewLabel = op.review_state_label || '';
    const progress = operationProgressIndex(op);
    const pad = compact ? 'p-3' : 'p-5';
    const titleSize = compact ? 'text-xs' : 'text-base';
    return `
      <div class="premium-card rounded-2xl ${pad} transition-all group relative overflow-hidden hover:-translate-y-0.5">
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
        <div class="flex items-start justify-between gap-3 mb-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="w-2 h-2 rounded-full ${typeMeta.dot} ${op.is_action_required ? 'animate-pulse' : ''}"></span>
              <span class="text-[9px] font-black uppercase tracking-widest ${typeMeta.text}">${typeMeta.label}</span>
              ${isTeamOp(op) ? '<span class="text-[9px] px-2 py-0.5 rounded-full border border-emerald-400/20 bg-emerald-400/10 text-emerald-300 font-black uppercase tracking-widest">Team Ops</span>' : ''}
            </div>
            <p class="${titleSize} font-bold text-white truncate">${esc(op.title || typeMeta.label)}</p>
          </div>
          <span class="dcx-chip ${operationStatusClass(op)} shrink-0">${esc(op.status || 'READY')}</span>
        </div>
        <div class="status-rail ${typeMeta.text} mb-3" aria-hidden="true">
          ${[1, 2, 3, 4, 5].map((i) => `<span class="${i <= progress ? 'is-on' : ''}"></span>`).join('')}
        </div>
        <div class="flex items-center gap-2 flex-wrap text-[10px] font-mono text-gray-500 mb-3">
          <span>${esc(game)}</span>
          ${op.team_name ? `<span class="text-gray-700">&middot;</span><span>${esc(op.team_name)}</span>` : ''}
          ${scheduledText ? `<span class="text-gray-700">&middot;</span><span>${esc(scheduledText)}</span>` : ''}
          ${fee ? `<span class="text-gray-700">&middot;</span><span>${fee.toLocaleString()} DC entry</span>` : ''}
          ${reward ? `<span class="text-gray-700">&middot;</span><span class="text-dc-gold">${esc(reward)}</span>` : ''}
        </div>
        ${reviewLabel ? `<div class="mb-3 rounded-xl border border-white/5 bg-white/[0.035] px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-gray-400">${esc(reviewLabel)}</div>` : ''}
        ${isPrimarySubmit ? `
          <button type="button" data-submit-showdown-result="${esc(op.id)}" class="interactive-lift inline-flex items-center justify-center gap-2 w-full rounded-xl border px-3 py-2.5 text-[10px] font-black uppercase tracking-widest ${actionClass}">
            <i class="fa-solid fa-flag-checkered"></i> Submit Result
          </button>
        ` : `
          <a href="${esc(actionUrl)}" class="interactive-lift inline-flex items-center justify-center gap-2 w-full rounded-xl border px-3 py-2.5 text-[10px] font-black uppercase tracking-widest ${actionClass}">
            ${op.is_action_required ? '<i class="fa-solid fa-bolt"></i>' : '<i class="fa-solid fa-arrow-right"></i>'}
            ${esc(op.next_action_label || 'View Details')}
          </a>
        `}
        ${showDetailLink ? `<a href="${esc(detailUrl)}" class="mt-2 inline-flex items-center justify-center gap-2 w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-[10px] font-black uppercase tracking-widest text-gray-300 hover:text-white hover:border-dc-cyan/30"><i class="fa-solid fa-list-check"></i> View Detail Timeline</a>` : ''}
        ${lobbyDetailUrl ? `<a href="${esc(lobbyDetailUrl)}" class="mt-2 inline-flex items-center justify-center gap-2 w-full rounded-xl border border-dc-gold/20 bg-dc-gold/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-dc-gold hover:bg-dc-gold/20"><i class="fa-solid fa-map-location-dot"></i> View Lobby</a>` : ''}
        ${canSecondarySubmit ? `<button type="button" data-submit-showdown-result="${esc(op.id)}" class="inline-flex items-center justify-center gap-2 w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 mt-2 text-[10px] font-black uppercase tracking-widest text-gray-300 hover:text-white hover:border-dc-cyan/30"><i class="fa-solid fa-flag-checkered"></i> Submit Result</button>` : ''}
      </div>`;
  }

  function renderActiveOps() {
    const box = document.getElementById('active-ops-container');
    const counter = document.getElementById('ops-count');
    const operations = scopedOperations();
    if (counter) counter.textContent = `${operations.length} ACTIVE`;
    renderCommandMetrics();
    renderOperationsWorkspace();
    renderReviewWorkspace();
    renderReviewAlert();
    if (!box) return;
    if (!operations.length) {
      box.innerHTML = `<div class="rounded-2xl border border-white/10 bg-white/[0.025] text-center py-7 px-4">
        <div class="mx-auto mb-3 h-11 w-11 rounded-2xl border border-white/10 bg-white/[0.04] grid place-items-center text-gray-500"><i class="fa-solid fa-satellite-dish"></i></div>
        <p class="text-xs font-bold uppercase tracking-widest text-gray-400 mb-2">No operations yet</p>
        <p class="text-[11px] leading-relaxed text-gray-600">Start a Mission, create a Showdown, claim a Bounty, or reserve a Dropzone slot.</p>
      </div>`;
      return;
    }
    const groups = [
      { label: 'Needs Action', list: operations.filter((op) => !!op.is_action_required) },
      { label: 'Match Room Ready', list: operations.filter((op) => !op.is_action_required && !isReviewOp(op) && !isTerminalOp(op) && hasMatchRoomReady(op)) },
      { label: 'Waiting', list: operations.filter((op) => !op.is_action_required && !isReviewOp(op) && !isTerminalOp(op) && !hasMatchRoomReady(op)) },
      { label: 'Under Review', list: operations.filter((op) => !op.is_action_required && !isTerminalOp(op) && isReviewOp(op)) },
      { label: 'Completed', list: operations.filter(isTerminalOp).slice(0, 3) },
    ].filter((group) => group.list.length);
    box.innerHTML = groups.map((group) => `
      <div class="rounded-2xl border border-white/[0.055] bg-black/20 p-2.5">
        <div class="mb-2.5 flex items-center justify-between">
          <p class="text-[9px] font-black uppercase tracking-[0.18em] text-gray-400">${esc(group.label)}</p>
          <span class="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[9px] font-mono text-gray-500">${group.list.length}</span>
        </div>
        <div class="space-y-2">${group.list.slice(0, 4).map((op) => renderOperationCard(op, { compact: true })).join('')}</div>
      </div>`).join('');
  }

  function renderReviewAlert() {
    const alert = document.getElementById('review-alert');
    if (!alert) return;
    const reviewOps = scopedOperations().filter(isReviewOp);
    if (!reviewOps.length) {
      alert.classList.add('hidden-spa');
      alert.innerHTML = '';
      return;
    }
    alert.classList.remove('hidden-spa');
    alert.innerHTML = `
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div class="flex items-start gap-3">
          <div class="h-10 w-10 rounded-xl border border-dc-neon/25 bg-dc-neon/10 grid place-items-center text-dc-neon shrink-0">
            <i class="fa-solid fa-shield-halved"></i>
          </div>
          <div>
            <p class="text-sm font-black text-white">${reviewOps.length} item${reviewOps.length === 1 ? '' : 's'} under review</p>
            <p class="text-xs text-gray-400 mt-0.5">Proof, result confirmation, or dispute progress is available from your operations rail.</p>
          </div>
        </div>
        <a href="/dashboard/competitive/disputes/" class="inline-flex items-center justify-center rounded-xl border border-dc-neon/25 bg-dc-neon/10 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-dc-neon hover:bg-dc-neon/20">
          Open Disputes
        </a>
      </div>`;
  }

  function renderOperationsWorkspace() {
    const box = document.getElementById('operations-workspace');
    if (!box) return;
    const operations = scopedOperations();
    if (!operations.length) {
      box.innerHTML = `<div class="xl:col-span-2">${emptyState({ icon: 'fa-layer-group', title: 'No Operations Running', sub: 'Start a Mission, create a Showdown, claim a Bounty, reserve a Dropzone slot, or schedule team ops to build your command feed.' })}</div>`;
      return;
    }
    const groups = [
      { key: 'needs', label: 'Needs Action', list: operations.filter((op) => !!op.is_action_required) },
      { key: 'rooms', label: 'Live / Match Room Ready', list: operations.filter((op) => !op.is_action_required && !isReviewOp(op) && !isTerminalOp(op) && hasMatchRoomReady(op)) },
      { key: 'waiting', label: 'Waiting', list: operations.filter((op) => !op.is_action_required && !isReviewOp(op) && !isTerminalOp(op) && !hasMatchRoomReady(op)) },
      { key: 'review', label: 'Under Review', list: operations.filter((op) => !op.is_action_required && !isTerminalOp(op) && isReviewOp(op)) },
      { key: 'closed', label: 'Completed', list: operations.filter(isTerminalOp) },
    ].filter((group) => group.list.length);
    box.innerHTML = groups.map((group) => `
      <div class="xl:col-span-2">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-[10px] uppercase tracking-[0.24em] font-black text-gray-500">${esc(group.label)}</h3>
          <span class="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[9px] font-mono text-gray-500">${group.list.length}</span>
        </div>
        <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">${group.list.map((op) => renderOperationCard(op)).join('')}</div>
      </div>
    `).join('');
  }

  function renderReviewWorkspace() {
    const box = document.getElementById('review-workspace');
    if (!box) return;
    const reviewOps = scopedOperations().filter(isReviewOp);
    if (!reviewOps.length) {
      box.innerHTML = emptyState({
        icon: 'fa-shield-halved',
        title: 'Review Queue Clear',
        sub: 'No visible proof, confirmation, or dispute items need your action right now.',
      });
      return;
    }
    box.innerHTML = reviewOps.map((op) => renderOperationCard(op)).join('');
  }

  function operationTypeMeta(type) {
    const map = {
      showdown: { label: 'Showdown', dot: 'bg-dc-cyan', text: 'text-dc-cyan' },
      mission: { label: 'Missions', dot: 'bg-dc-violet', text: 'text-dc-violet' },
      bounty: { label: 'Bounty', dot: 'bg-dc-neon', text: 'text-dc-neon' },
      dropzone: { label: 'Dropzone', dot: 'bg-dc-gold', text: 'text-dc-gold' },
      scrim: { label: 'Scrim', dot: 'bg-emerald-400', text: 'text-emerald-300' },
      tryout: { label: 'Tryout', dot: 'bg-blue-400', text: 'text-blue-300' },
      practice: { label: 'Practice', dot: 'bg-cyan-400', text: 'text-cyan-300' },
      vod_review: { label: 'VOD Review', dot: 'bg-purple-400', text: 'text-purple-300' },
    };
    return map[type] || { label: 'Operation', dot: 'bg-gray-500', text: 'text-gray-400' };
  }

  function renderAllFeeds() {
    renderClashFeed();
    renderContractsFeed();
    renderHitlistFeed();
    renderRoyaleFeed();
  }

  // ── Data fetchers ─────────────────────────────────────────────────

  async function loadClashes() {
    try { STATE.data.showdown = await jsonFetch(API.challengesList); }
    catch { STATE.data.showdown = []; }
    STATE.loaded.showdown = true;
    renderClashFeed();
  }
  async function loadContracts() {
    try { STATE.data.missions = await jsonFetch(API.contractsList); }
    catch { STATE.data.missions = []; }
    STATE.loaded.missions = true;
    renderContractsFeed();
  }
  async function loadHitlist() {
    try { STATE.data.bounty = await jsonFetch(API.bountiesList); }
    catch { STATE.data.bounty = []; }
    STATE.loaded.bounty = true;
    renderHitlistFeed();
  }
  async function loadRoyale() {
    try { STATE.data.dropzone = await jsonFetch(API.royaleList); }
    catch { STATE.data.dropzone = []; }
    STATE.loaded.dropzone = true;
    renderRoyaleFeed();
  }
  async function loadMyOperations() {
    try {
      const body = await jsonFetch(API.myOperations);
      STATE.data.myOperations = Array.isArray(body) ? body : (body.results || []);
    }
    catch { STATE.data.myOperations = []; }
    STATE.loaded.myOperations = true;
    renderActiveOps();
  }

  // ── Action handlers ───────────────────────────────────────────────

  async function onAcceptClash(id, fee, challengerTeamId) {
    const choices = authorityTeamOptions(challengerTeamId);
    if (!choices.length) {
      toast('No eligible managed team can accept this Showdown.', 'error');
      return;
    }
    const ok = await openConfirm({
      title: 'Accept this Showdown?',
      body: 'Your selected team entry fee locks on accept. Settlement follows the verified match result.',
      lockNote: `This will lock ${Number(fee).toLocaleString()} DC in escrow.`,
      teamChoices: choices,
      selectedTeamId: choices.some((team) => String(team.id) === String(STATE.operatingTeamId)) ? STATE.operatingTeamId : (choices.length === 1 ? choices[0].id : ''),
    });
    if (!ok) return;
    const acceptingTeamId = choices.length === 1 ? choices[0].id : ok.teamId;
    if (!acceptingTeamId) {
      toast('Select an accepting team before confirming.', 'error');
      return;
    }
    try {
      const updated = await jsonFetch(API.challengeAccept(id), {
        method: 'POST',
        body: JSON.stringify({ accepting_team_id: Number(acceptingTeamId) }),
      });
      toast(`Locked ${Number(fee).toLocaleString()} DC. Reward pool now ${Number(updated.prize_pot_dc || 0).toLocaleString()} DC. Match room spawned.`, 'success');
      await loadClashes();
      await loadMyOperations();
    } catch (err) { handleApiError(err); }
  }

  async function onHuntBounty(id, fee) {
    const team = selectedTeam();
    if (!team) { toast('You need a team to claim Bounties.', 'error'); return; }
    const ok = await openConfirm({
      title: 'Claim this Bounty?',
      body: `${team.name} will challenge the issuer under the posted rules. Your entry fee locks for verification.`,
      lockNote: `This will lock ${Number(fee).toLocaleString()} DC in escrow.`,
    });
    if (!ok) return;
    try {
      await jsonFetch(API.bountyClaim(id), {
        method: 'POST',
        body: JSON.stringify({ claiming_team_id: team.id }),
      });
      toast('Bounty claim submitted. Match room spawning.', 'success');
      await loadHitlist();
      await loadMyOperations();
    } catch (err) { handleApiError(err); }
  }

  async function onReserveRoyale(id, fee) {
    const ok = await openConfirm({
      title: 'Reserve a Dropzone slot?',
      body: 'Your entry fee is locked for the event. Room ID drops at match start. Cancel before match start to refund.',
      lockNote: `This will lock ${Number(fee).toLocaleString()} DC as the event entry.`,
    });
    if (!ok) return;
    try {
      await jsonFetch(API.royaleReserve(id), { method: 'POST', body: '{}' });
      toast('Slot reserved. See you at match time.', 'success');
      await loadRoyale();
      await loadMyOperations();
    } catch (err) { handleApiError(err); }
  }

  async function onEnrollContract(id, fee) {
    const ok = await openConfirm({
      title: 'Start this Mission?',
      body: 'Entry fee locks in escrow. Complete the objective before the deadline to claim the reward.',
      lockNote: `This will lock ${Number(fee).toLocaleString()} DC in escrow.`,
    });
    if (!ok) return;
    try {
      await jsonFetch(API.contractsEnroll(id), { method: 'POST', body: '{}' });
      toast('Enrolled. Goal active.', 'success');
      await loadMyOperations();
    } catch (err) { handleApiError(err); }
  }

  function openResultModal(op) {
    STATE.resultOperation = op;
    const modal = document.getElementById('showdown-result-modal');
    if (!modal) return;
    document.getElementById('result-showdown-title').textContent = op.title || 'Showdown Result';
    const challenger = op.challenger_team_name || 'Challenger';
    const challenged = op.challenged_team_name || 'Opponent';
    const resultSel = document.getElementById('showdown-result-result');
    resultSel.innerHTML = `
      <option value="">-- Select result --</option>
      <option value="CHALLENGER_WIN">${esc(challenger)} won</option>
      <option value="CHALLENGED_WIN">${esc(challenged)} won</option>
      <option value="DRAW">Draw</option>`;
    document.getElementById('showdown-result-challenger-label').textContent = challenger;
    document.getElementById('showdown-result-challenged-label').textContent = challenged;
    document.getElementById('showdown-result-challenger-score').value = '';
    document.getElementById('showdown-result-challenged-score').value = '';
    document.getElementById('showdown-result-evidence').value = '';
    showFormError('showdown-result', '');
    modal.classList.remove('hidden-spa');
  }

  function closeResultModal() {
    const modal = document.getElementById('showdown-result-modal');
    if (modal) modal.classList.add('hidden-spa');
    STATE.resultOperation = null;
  }

  async function onSubmitShowdownResult(e) {
    e.preventDefault();
    const op = STATE.resultOperation;
    if (!op) return;
    showFormError('showdown-result', '');

    const resultEl = document.getElementById('showdown-result-result');
    const challengerScoreEl = document.getElementById('showdown-result-challenger-score');
    const challengedScoreEl = document.getElementById('showdown-result-challenged-score');
    const evidenceEl = document.getElementById('showdown-result-evidence');

    const result = resultEl.value;
    const challengerScore = challengerScoreEl.value === '' ? null : Number(challengerScoreEl.value);
    const challengedScore = challengedScoreEl.value === '' ? null : Number(challengedScoreEl.value);
    const evidenceUrl = (evidenceEl.value || '').trim();

    if (!result) return showFormError('showdown-result', 'Select the result.');
    if (challengerScore == null || challengedScore == null || Number.isNaN(challengerScore) || Number.isNaN(challengedScore)) {
      return showFormError('showdown-result', 'Enter both team scores.');
    }

    try {
      await jsonFetch(API.challengeResult(op.id), {
        method: 'POST',
        body: JSON.stringify({
          submitting_team_id: op.team_id || undefined,
          result,
          score_details: {
            challenger: challengerScore,
            challenged: challengedScore,
          },
          evidence_url: evidenceUrl,
        }),
      });
      toast('Showdown result submitted.', 'success');
      closeResultModal();
      await loadClashes();
      await loadMyOperations();
    } catch (err) {
      handleApiError(err);
      const detail = err && err.body && err.body.detail;
      showFormError('showdown-result', detail || 'Could not submit result.');
    }
  }

  // ── Create-clash form ─────────────────────────────────────────────

  function fillSelect(el, options, { placeholder, selectedId } = {}) {
    if (!el) return;
    const parts = [];
    if (placeholder !== undefined) parts.push(`<option value="">${esc(placeholder)}</option>`);
    options.forEach((opt) => {
      const sel = String(opt.id) === String(selectedId) ? ' selected' : '';
      parts.push(`<option value="${esc(opt.id)}"${sel}>${esc(opt.label)}</option>`);
    });
    el.innerHTML = parts.join('');
  }

  function teamOptions() {
    return (HUB.my_teams || []).map((t) => ({
      id: t.id,
      label: t.tag ? `${t.name} [${t.tag}]` : t.name,
    }));
  }

  function authorityTeamOptions(excludeTeamId = '') {
    const excluded = String(excludeTeamId || '');
    return (HUB.my_teams || [])
      .filter((t) => !excluded || String(t.id) !== excluded)
      .sort((a, b) => {
        if (String(a.id) === String(STATE.operatingTeamId)) return -1;
        if (String(b.id) === String(STATE.operatingTeamId)) return 1;
        return 0;
      })
      .map((t) => ({
        id: t.id,
        label: t.tag ? `${t.name} [${t.tag}]` : t.name,
      }));
  }
  function gameOptions() {
    return (HUB.games || []).map((g) => ({
      id: g.id,
      label: g.short_code ? `${g.name} (${g.short_code})` : g.name,
    }));
  }

  function showFormError(name, message) {
    const el = document.getElementById(`${name}-form-error`);
    if (!el) return;
    el.textContent = message || '';
    el.classList.toggle('hidden', !message);
  }

  function setSubmitting(buttonId, busy, busyLabel) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    btn.disabled = !!busy;
    const label = btn.querySelector('.submit-label');
    if (!label) return;
    if (busy) {
      btn.dataset.originalLabel = label.innerHTML;
      label.textContent = busyLabel || 'Working…';
    } else if (btn.dataset.originalLabel) {
      label.innerHTML = btn.dataset.originalLabel;
      delete btn.dataset.originalLabel;
    }
  }

  function updateClashPot() {
    const v = Number(document.getElementById('clash-fee').value || 0);
    document.getElementById('clash-pot-display').innerHTML = `<i class="fa-solid fa-coins text-sm mr-1"></i>${(v * 2).toLocaleString()}`;
    const amt = document.getElementById('submit-btn-amt');
    if (amt) amt.textContent = v.toLocaleString();
  }

  function resetClashForm({ opponentId = '', opponentName = '' } = {}) {
    const myTeams = teamOptions();
    fillSelect(document.getElementById('clash-team'), myTeams, {
      placeholder: myTeams.length ? '— Select your team —' : 'No authority team found',
    });
    fillSelect(document.getElementById('clash-game'), gameOptions(), { placeholder: '— Select game —' });

    const oppSel = document.getElementById('clash-opponent');
    const oppHint = document.getElementById('clash-opponent-hint');
    if (opponentId) {
      const label = opponentName || `Team #${opponentId}`;
      oppSel.innerHTML = `<option value="${esc(opponentId)}" selected>${esc(label)}</option>`;
      oppSel.disabled = true;
      if (oppHint) oppHint.textContent = `Pre-filled from ${label}. Direct challenge.`;
    } else {
      oppSel.disabled = false;
      oppSel.innerHTML = '<option value="">-- Open Showdown (any team may accept) --</option>';
      if (oppHint) oppHint.textContent = 'Leave blank to broadcast on the open radar.';
    }

    document.getElementById('form-create-clash').reset();
    if (opponentId) oppSel.value = String(opponentId);
    document.getElementById('clash-format').value = '3';
    document.getElementById('clash-fee').value = '300';
    document.getElementById('clash-title').value = '';
    const selectedId = STATE.operatingTeamId && myTeams.some((t) => String(t.id) === String(STATE.operatingTeamId)) ? STATE.operatingTeamId : '';
    if (selectedId) document.getElementById('clash-team').value = String(selectedId);
    else if (myTeams.length === 1) document.getElementById('clash-team').value = String(myTeams[0].id);
    document.getElementById('so-acting-as').textContent = `Acting as: ${HUB.primary_team ? HUB.primary_team.name : '—'}`;
    document.getElementById('so-wallet-bal').textContent = `Bal: ${Number((HUB.wallet || {}).cached_balance || 0).toLocaleString()} DC`;
    showFormError('clash', '');
    updateClashPot();
  }

  async function onSubmitClash(e) {
    e.preventDefault();
    showFormError('clash', '');
    const teamSel = document.getElementById('clash-team');
    const oppSel = document.getElementById('clash-opponent');
    const gameSel = document.getElementById('clash-game');
    const titleEl = document.getElementById('clash-title');
    const feeEl = document.getElementById('clash-fee');
    const bestOf = Number(document.getElementById('clash-format').value || 3);

    [teamSel, oppSel, gameSel, titleEl, feeEl].forEach((el) => el && el.classList.remove('is-invalid'));

    const teamId = teamSel.value;
    const oppId = oppSel.value;
    const gameId = gameSel.value;
    const title = (titleEl.value || '').trim();
    const fee = Number(feeEl.value || 0);

    if (!teamId)        { teamSel.classList.add('is-invalid');  return showFormError('clash', 'Select your team.'); }
    if (!gameId)        { gameSel.classList.add('is-invalid');  return showFormError('clash', 'Select a game.'); }
    if (!title)         { titleEl.classList.add('is-invalid');  return showFormError('clash', 'Give the Showdown a title.'); }
    if (!fee || fee < 1){ feeEl.classList.add('is-invalid');    return showFormError('clash', 'Entry fee must be at least 1 DC.'); }
    if (fee > 1000)     { feeEl.classList.add('is-invalid');    return showFormError('clash', 'Anti-whale cap: max 1,000 DC.'); }

    const ok = await openConfirm({
      title: 'Create this Showdown?',
      body: 'Your entry fee locks immediately. Opponent matches on accept. Refunded on decline, cancel, or expiry.',
      lockNote: `This will lock ${fee.toLocaleString()} DC in escrow now.`,
    });
    if (!ok) return;

    const payload = {
      challenger_team_id: Number(teamId),
      challenged_team_id: oppId ? Number(oppId) : null,
      game_id: Number(gameId),
      title,
      challenge_type: oppId ? 'DIRECT' : 'OPEN',
      best_of: bestOf,
      entry_fee_dc: fee,
      is_public: true,
    };

    try {
      setSubmitting('clash-submit', true, 'Locking…');
      await jsonFetch(API.challengeCreate, { method: 'POST', body: JSON.stringify(payload) });
      toast(`Showdown created. ${fee.toLocaleString()} DC locked.`, 'success');
      closeSlideOver('create-clash');
      await loadClashes();
      await loadMyOperations();
    } catch (err) {
      const code = err && err.body && err.body.code;
      if (code === 'INSUFFICIENT_FUNDS') showFormError('clash', err.body.detail || 'Not enough DeltaCoins.');
      handleApiError(err);
    } finally {
      setSubmitting('clash-submit', false);
    }
  }

  // ── Create-hitlist form ───────────────────────────────────────────

  function resetHitlistForm() {
    const myTeams = teamOptions();
    fillSelect(document.getElementById('hitlist-team'), myTeams, {
      placeholder: myTeams.length ? '— Select your team —' : 'No authority team found',
    });
    fillSelect(document.getElementById('hitlist-game'), gameOptions(), { placeholder: '— Select game —' });
    document.getElementById('form-create-hitlist').reset();
    document.getElementById('hitlist-reward').value = '1000';
    document.getElementById('hitlist-entry').value = '200';
    const selectedId = STATE.operatingTeamId && myTeams.some((t) => String(t.id) === String(STATE.operatingTeamId)) ? STATE.operatingTeamId : '';
    if (selectedId) document.getElementById('hitlist-team').value = String(selectedId);
    else if (myTeams.length === 1) document.getElementById('hitlist-team').value = String(myTeams[0].id);
    showFormError('hitlist', '');
  }

  async function onSubmitHitlist(e) {
    e.preventDefault();
    showFormError('hitlist', '');
    const teamSel = document.getElementById('hitlist-team');
    const gameSel = document.getElementById('hitlist-game');
    const titleEl = document.getElementById('hitlist-title');
    const rewardEl = document.getElementById('hitlist-reward');
    const entryEl = document.getElementById('hitlist-entry');
    [teamSel, gameSel, titleEl, rewardEl, entryEl].forEach((el) => el && el.classList.remove('is-invalid'));

    const teamId = teamSel.value;
    const gameId = gameSel.value;
    const title = (titleEl.value || '').trim();
    const reward = Number(rewardEl.value || 0);
    const entry = Number(entryEl.value || 0);

    if (!teamId)     { teamSel.classList.add('is-invalid');   return showFormError('hitlist', 'Select your team.'); }
    if (!gameId)     { gameSel.classList.add('is-invalid');   return showFormError('hitlist', 'Select a game.'); }
    if (!title)      { titleEl.classList.add('is-invalid');   return showFormError('hitlist', 'Give the bounty a headline.'); }
    if (reward < 1)  { rewardEl.classList.add('is-invalid');  return showFormError('hitlist', 'Reward must be at least 1 DC.'); }
    if (entry < 1)   { entryEl.classList.add('is-invalid');   return showFormError('hitlist', 'Entry fee must be at least 1 DC.'); }
    if (entry > 1000){ entryEl.classList.add('is-invalid');   return showFormError('hitlist', 'Anti-whale cap: max 1,000 DC entry.'); }

    const ok = await openConfirm({
      title: 'Place this Bounty?',
      body: 'Your selected team posts this Bounty for challengers to claim. The Bounty reward locks immediately.',
      lockNote: `This will lock ${reward.toLocaleString()} DC in escrow now.`,
    });
    if (!ok) return;

    const payload = {
      issuer_team_id: Number(teamId),
      game_id: Number(gameId),
      title,
      bounty_type: 'BEAT_US',
      reward_type: 'CP',
      reward_amount_dc: reward,
      challenger_entry_fee_dc: entry,
      max_claims: 1,
      is_hitlist: true,
      is_public: true,
    };

    try {
      setSubmitting('hitlist-submit', true, 'Locking…');
      await jsonFetch(API.bountyCreate, { method: 'POST', body: JSON.stringify(payload) });
      toast(`Bounty posted. ${reward.toLocaleString()} DC locked.`, 'success');
      closeSlideOver('create-hitlist');
      await loadHitlist();
      await loadMyOperations();
    } catch (err) {
      const code = err && err.body && err.body.code;
      if (code === 'INSUFFICIENT_FUNDS') showFormError('hitlist', err.body.detail || 'Not enough DeltaCoins.');
      handleApiError(err);
    } finally {
      setSubmitting('hitlist-submit', false);
    }
  }

  // ── URL prefill ───────────────────────────────────────────────────

  function applyUrlPrefill() {
    let params;
    try { params = new URLSearchParams(window.location.search); } catch { return; }
    const teamId = params.get('target_team_id') || params.get('challenge_team_id');
    const teamName = params.get('target_team_name') || params.get('challenge_team_name') || '';
    if (teamId) STATE.targetOpponent = { opponentId: teamId, opponentName: teamName };
    const banner = document.getElementById('target-context-banner');
    if (teamId && banner) {
      banner.classList.remove('hidden-spa');
      banner.innerHTML = `
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <span><strong class="text-white">Challenging ${esc(teamName || `Team #${teamId}`)}</strong> through Showdown. Select your operating team, then create the match.</span>
          <button type="button" data-open-slide="create-clash" class="inline-flex items-center justify-center rounded-xl border border-dc-cyan/30 bg-dc-cyan/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-dc-cyan hover:bg-dc-cyan hover:text-black">Create Showdown</button>
        </div>`;
    }
    if (teamId && canIssueSelectedTeam()) {
      switchTab('showdown', { updateHash: true });
      openSlideOver('create-clash', { opponentId: teamId, opponentName: teamName });
      return;
    }
    const action = (params.get('action') || '').toLowerCase();
    if (['create-clash', 'create-showdown', 'showdown'].includes(action) && canIssueSelectedTeam()) { switchTab('showdown', { updateHash: true }); openSlideOver('create-clash'); }
    if (['create-hitlist', 'create-bounty', 'bounty'].includes(action) && canIssueSelectedTeam()) { switchTab('bounty', { updateHash: true }); openSlideOver('create-hitlist'); }
  }

  // ── Event binding ─────────────────────────────────────────────────

  function bindEvents() {
    document.addEventListener('error', (e) => {
      const img = e.target;
      if (!(img instanceof HTMLImageElement) || !img.matches('[data-bounty-logo]')) return;
      const mark = img.closest('.bounty-team-mark');
      const fallback = img.nextElementSibling;
      img.classList.add('hidden');
      if (fallback) fallback.classList.remove('hidden');
      if (mark) {
        mark.classList.add('is-fallback');
        mark.dataset.hasLogo = 'false';
      }
    }, true);

    // Tab triggers (delegated)
    document.getElementById('tab-triggers').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-tab]');
      if (btn) switchTab(btn.dataset.tab, { updateHash: true });
    });

    // Game selector
    const gameTrigger = document.getElementById('game-selector-trigger');
    const gameMenu = document.getElementById('game-selector-menu');
    if (gameTrigger && gameMenu) {
      gameTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = gameMenu.classList.toggle('is-open');
        gameMenu.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
        gameTrigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      });
    }

    // Search
    const search = document.getElementById('global-search');
    if (search) {
      search.addEventListener('input', (e) => {
        STATE.searchQuery = e.target.value;
        renderAllFeeds();
      });
    }

    const teamSwitcher = document.getElementById('operating-team-select');
    if (teamSwitcher) {
      teamSwitcher.addEventListener('change', (e) => setOperatingTeam(e.target.value));
    }

    // Global delegated clicks for: open/close slide, go-tab, accept/hunt/reserve/enroll
    document.body.addEventListener('click', (e) => {
      const target = e.target;
      if (!(target instanceof Element)) return;

      const gameOption = target.closest('.game-option');
      if (gameOption) {
        setGameFilter(String(gameOption.dataset.gameCode || 'ALL').toUpperCase(), { manual: true });
        closeGameSelector();
        return;
      }

      const openSlide = target.closest('[data-open-slide]');
      if (openSlide) {
        const slide = openSlide.dataset.openSlide;
        if ((slide === 'create-clash' || slide === 'create-hitlist') && !canIssueSelectedTeam()) {
          toast(selectedTeam() ? 'Captain or manager authority is required.' : 'Join or create a team before starting team reward operations.', 'error');
          return;
        }
        const opts = slide === 'create-clash' && STATE.targetOpponent ? STATE.targetOpponent : {};
        openSlideOver(slide, opts);
        return;
      }

      const openGuide = target.closest('[data-open-guide]');
      if (openGuide) {
        const guide = document.getElementById('guide-modal');
        if (guide) {
          guide.classList.remove('hidden-spa');
          lockPageScroll();
        }
        return;
      }

      const closeGuide = target.closest('[data-close-guide]');
      if (closeGuide) {
        closeGuideModal();
        return;
      }

      const guideMode = target.closest('[data-guide-mode]');
      if (guideMode) {
        const mode = guideMode.dataset.guideMode || 'showdown';
        document.querySelectorAll('[data-guide-mode]').forEach((btn) => {
          btn.classList.toggle('is-active', btn === guideMode);
        });
        document.querySelectorAll('[data-guide-panel]').forEach((panel) => {
          panel.classList.toggle('is-active', panel.dataset.guidePanel === mode);
        });
        return;
      }

      const closeSlide = target.closest('[data-close-slide]');
      if (closeSlide) { closeSlideOver(closeSlide.dataset.closeSlide); return; }

      const goTab = target.closest('[data-go-tab]');
      if (goTab && goTab.dataset.goTab) { switchTab(goTab.dataset.goTab, { updateHash: true }); return; }

      const accept = target.closest('[data-accept-clash]');
      if (accept && !accept.disabled) { onAcceptClash(accept.dataset.acceptClash, accept.dataset.fee, accept.dataset.challengerTeam); return; }

      const hunt = target.closest('[data-hunt-bounty]');
      if (hunt && !hunt.disabled) { onHuntBounty(hunt.dataset.huntBounty, hunt.dataset.fee); return; }

      const reserve = target.closest('[data-reserve-royale]');
      if (reserve && !reserve.disabled) { onReserveRoyale(reserve.dataset.reserveRoyale, reserve.dataset.fee); return; }

      const enroll = target.closest('[data-enroll-contract]');
      if (enroll) { onEnrollContract(enroll.dataset.enrollContract, enroll.dataset.fee); return; }

      const resultBtn = target.closest('[data-submit-showdown-result]');
      if (resultBtn) {
        const op = scopedOperations().find((item) => item.id === resultBtn.dataset.submitShowdownResult);
        if (op && op.match_room_url) { window.location.href = op.match_room_url; return; }
        if (op) openResultModal(op);
        return;
      }

      const closeResult = target.closest('[data-close-result-modal]');
      if (closeResult) { closeResultModal(); return; }

      const cancelConfirm = target.closest('[data-cancel-confirm]');
      if (cancelConfirm) { closeConfirm(false); return; }
    });

    document.addEventListener('click', (e) => {
      const target = e.target;
      if (target instanceof Element && target.closest('#game-selector')) return;
      closeGameSelector();
    });

    // Backdrop click to close slide
    const backdrop = document.getElementById('slide-over-backdrop');
    if (backdrop) {
      backdrop.addEventListener('click', () => {
        closeSlideOver('create-clash');
        closeSlideOver('create-hitlist');
      });
    }

    const guideModal = document.getElementById('guide-modal');
    if (guideModal) {
      guideModal.addEventListener('click', (e) => {
        if (e.target === guideModal) {
          closeGuideModal();
        }
      });
    }

    // Confirm modal
    document.getElementById('confirm-go').addEventListener('click', () => closeConfirm(true));
    document.getElementById('confirm-modal').addEventListener('click', (e) => {
      if (e.target.id === 'confirm-modal') closeConfirm(false);
    });

    // ESC
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      if (_confirmDeferred) { closeConfirm(false); return; }
      if (STATE.resultOperation) { closeResultModal(); return; }
      if (isGuideOpen()) { closeGuideModal(); return; }
      closeSlideOver('create-clash');
      closeSlideOver('create-hitlist');
    });

    // Forms
    const clashForm = document.getElementById('form-create-clash');
    if (clashForm) clashForm.addEventListener('submit', onSubmitClash);
    const hitForm = document.getElementById('form-create-hitlist');
    if (hitForm) hitForm.addEventListener('submit', onSubmitHitlist);
    const resultForm = document.getElementById('form-showdown-result');
    if (resultForm) resultForm.addEventListener('submit', onSubmitShowdownResult);

    // Live pot calc
    const fee = document.getElementById('clash-fee');
    if (fee) fee.addEventListener('input', updateClashPot);
  }

  // ── Init ──────────────────────────────────────────────────────────

  function init() {
    document.body.classList.remove('overflow-hidden');
    hydrateTeamSwitcher();
    setGameFilter(smartDefaultGameCode(), { manual: false });
    hydrateLeftColumn();
    renderHero();
    renderActionPermissions();
    bindEvents();
    switchTab(window.location.hash ? window.location.hash.slice(1) : 'showdown');
    window.addEventListener('hashchange', () => switchTab(window.location.hash.slice(1) || 'showdown'));
    // Fetch all in parallel
    Promise.all([loadClashes(), loadContracts(), loadHitlist(), loadRoyale(), loadMyOperations()])
      .then(() => { renderGuidance(); renderEcosystemFlow(); renderTelemetry(); applyUrlPrefill(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
