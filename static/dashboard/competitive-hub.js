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
    activeTab: 'clash',
    gameFilter: 'ALL',
    searchQuery: '',
    data: { clashes: [], contracts: [], hitlist: [], royale: [], myOperations: [] },
    loaded: { clashes: false, contracts: false, hitlist: false, royale: false, myOperations: false },
    resultOperation: null,
  };

  const TAB_ALIASES = {
    clash: 'clash',
    showdowns: 'clash',
    showdown: 'clash',
    'crown-clash': 'clash',
    challenges: 'clash',
    contracts: 'contracts',
    contract: 'contracts',
    missions: 'contracts',
    mission: 'contracts',
    'contract-board': 'contracts',
    hitlist: 'hitlist',
    'the-hitlist': 'hitlist',
    bounty: 'hitlist',
    bounties: 'hitlist',
    royale: 'royale',
    'crown-royale': 'royale',
    dropzone: 'royale',
  };

  const TAB_HASH = {
    clash: 'showdown',
    contracts: 'missions',
    hitlist: 'bounty',
    royale: 'dropzone',
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

  function openSlideOver(name, opts = {}) {
    const backdrop = document.getElementById('slide-over-backdrop');
    const panel = document.getElementById(`slide-over-${name}`);
    if (!backdrop || !panel) return;
    if (name === 'create-clash') resetClashForm(opts);
    if (name === 'create-hitlist') resetHitlistForm(opts);
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
    setTimeout(() => backdrop.classList.add('hidden-spa'), 500);
  }

  // ── Hero / identity hydration ─────────────────────────────────────

  function hydrateLeftColumn() {
    const id = HUB.identity || {};
    const team = HUB.primary_team;
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
    document.getElementById('ctx-stat-2').textContent = HUB.can_issue ? 'CAPTAIN' : (team ? 'MEMBER' : 'SOLO');
  }

  function renderHero() {
    const titleEl = document.getElementById('hero-title');
    const descEl = document.getElementById('hero-desc');
    const actionsEl = document.getElementById('hero-actions');
    const visEl = document.getElementById('hero-visualizer');

    if (HUB.user_state === 'TEAM_CAPTAIN' && HUB.primary_team) {
      titleEl.innerHTML = `Command <span class="text-gradient-cyan">Center</span>`;
      descEl.innerHTML = `Operating as <strong class="text-white">${esc(HUB.primary_team.name)}</strong>. Create Showdowns with rival teams or manage Bounty challenges.`;
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
          <p class="font-display font-black text-3xl text-white relative z-10">${esc(HUB.primary_team.role || 'CAPTAIN')}</p>
          <p class="text-xs text-gray-400 mt-2 relative z-10">${esc(HUB.primary_team.name)}</p>
        </div>`;
    } else if (HUB.user_state === 'TEAM_MEMBER') {
      titleEl.innerHTML = `Roster <span class="text-gradient-cyan">Member</span>`;
      descEl.innerHTML = `You're on <strong class="text-white">${esc((HUB.primary_team && HUB.primary_team.name) || 'a team')}</strong>. Only captains and managers can create Showdowns - check the open radar below.`;
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

    if (HUB.can_issue) {
      clashBox.innerHTML = `
        <button type="button" data-open-slide="create-clash" class="bg-dc-cyan/10 hover:bg-dc-cyan text-dc-cyan hover:text-black border border-dc-cyan/30 px-5 py-2 font-bold text-xs uppercase tracking-widest rounded transition-all shadow-[0_0_15px_rgba(0,229,255,0.1)]">
          Create Showdown
        </button>`;
      hitlistBox.innerHTML = `
        <button type="button" data-open-slide="create-hitlist" class="btn-cyber bg-dc-neon/10 hover:bg-dc-neon text-dc-neon hover:text-white border border-dc-neon/30 px-5 py-2 font-bold text-xs uppercase tracking-widest rounded transition-all shadow-[0_0_15px_rgba(255,0,85,0.2)]">
          Post Bounty
        </button>`;
    } else {
      const reason = HUB.primary_team ? 'Captain authority required' : 'Team required';
      clashBox.innerHTML = `<button disabled title="${esc(reason)}" class="bg-white/5 border border-white/10 text-gray-500 px-5 py-2 font-bold text-xs uppercase tracking-widest rounded cursor-not-allowed"><i class="fa-solid fa-lock mr-1"></i> Create Showdown</button>`;
      hitlistBox.innerHTML = `<button disabled title="${esc(reason)}" class="bg-white/5 border border-white/10 text-gray-500 px-5 py-2 font-bold text-xs uppercase tracking-widest rounded cursor-not-allowed"><i class="fa-solid fa-lock mr-1"></i> Post Bounty</button>`;
    }
  }

  // ── Tab switching ─────────────────────────────────────────────────

  function normalizeTab(name) {
    const key = String(name || '').replace(/^#/, '').trim().toLowerCase();
    return TAB_ALIASES[key] || (['clash', 'contracts', 'hitlist', 'royale'].includes(key) ? key : 'clash');
  }

  function switchTab(name, opts = {}) {
    const tab = normalizeTab(name);
    STATE.activeTab = tab;
    document.querySelectorAll('.tab-trigger').forEach((t) => {
      t.classList.toggle('active', t.dataset.tab === tab);
    });
    document.querySelectorAll('.tab-content').forEach((c) => {
      c.classList.toggle('active', c.id === `tab-content-${tab}`);
    });
    if (opts.updateHash && TAB_HASH[tab]) {
      history.replaceState(null, '', `${window.location.pathname}${window.location.search}#${TAB_HASH[tab]}`);
    }
  }

  function setGameFilter(code) {
    STATE.gameFilter = code || 'ALL';
    document.querySelectorAll('.game-filter-btn').forEach((b) => {
      const active = b.dataset.game === STATE.gameFilter;
      b.classList.toggle('active', active);
      b.classList.toggle('bg-white/10', active);
      b.classList.toggle('text-white', active);
      b.classList.toggle('text-gray-500', !active);
    });
    renderAllFeeds();
  }

  function filterByGame(items) {
    if (STATE.gameFilter === 'ALL') return items;
    return items.filter((it) => {
      const code = String(it.game_short_code || (it.template && it.template.game_short_code) || '').toUpperCase();
      return code === STATE.gameFilter;
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
      <div class="glass-light rounded-xl p-10 text-center relative overflow-hidden">
        <div class="absolute inset-0 pointer-events-none opacity-[0.15]"
             style="background-image: linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px); background-size: 28px 28px; -webkit-mask-image: radial-gradient(circle at center, black 30%, transparent 75%); mask-image: radial-gradient(circle at center, black 30%, transparent 75%);"></div>
        <div class="relative">
          <i class="fa-solid ${icon} text-4xl text-gray-600 mb-3"></i>
          <p class="font-display text-xl font-black text-white mb-1">${esc(title)}</p>
          <p class="text-gray-400 text-sm max-w-md mx-auto leading-relaxed mb-5">${esc(sub)}</p>
          ${ctaText ? `<button type="button" data-go-tab="${esc(ctaTab || '')}" class="btn-cyber inline-flex items-center gap-2 bg-dc-cyan/15 border border-dc-cyan/40 text-dc-cyan hover:bg-dc-cyan hover:text-black px-5 py-2 text-xs font-bold uppercase tracking-widest transition-all">${esc(ctaText)} <i class="fa-solid fa-arrow-right text-[10px]"></i></button>` : ''}
        </div>
      </div>`;
  }

  // ── Feed renderers ────────────────────────────────────────────────

  function renderClashFeed() {
    const feed = document.getElementById('clash-feed');
    const list = applyFilters((STATE.data.clashes || []).filter((c) => Number(c.entry_fee_dc || 0) > 0));
    if (!list.length) {
      feed.innerHTML = emptyState({
        icon: 'fa-radar',
        title: 'Radar Silent',
        sub: 'No open Showdowns match your filters right now.',
        ctaText: HUB.can_issue ? 'Create Showdown' : null,
        ctaTab: null,
      });
      return;
    }
    feed.innerHTML = list.map((c) => {
      const pot = Number(c.prize_pot_dc || (c.entry_fee_dc * 2));
      const closed = !!c.closure_reason;
      const isHigh = Number(c.entry_fee_dc) >= 1000;
      const canAccept = HUB.can_issue && !closed && c.status === 'OPEN' && !c.challenged_team_id;
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
    const feed = document.getElementById('contracts-feed');
    const list = applyFilters(STATE.data.contracts);
    if (!list.length) {
      feed.innerHTML = `<div class="col-span-full">${emptyState({ icon: 'fa-scroll', title: 'No Missions Available', sub: 'Mission board is quiet. Check back when fresh objectives drop.' })}</div>`;
      return;
    }
    feed.innerHTML = list.map((t) => {
      const fee = Number(t.entry_fee_dc || 0);
      const reward = Number(t.reward_dc || 0);
      return `
        <div class="glass-heavy accent-violet rounded-2xl p-1 relative overflow-hidden group fade-enter border border-white/5 transition-all">
          <div class="absolute inset-0 bg-gradient-to-br from-dc-violet/10 to-transparent opacity-40 z-0"></div>
          <div class="bg-black/60 rounded-xl p-5 h-full flex flex-col relative z-10 border border-white/5">
            <div class="flex justify-between items-start mb-4">
              <div class="w-12 h-12 bg-dc-violet/20 rounded-xl flex items-center justify-center border border-dc-violet/30 text-dc-violet">
                <i class="fa-solid fa-scroll text-xl"></i>
              </div>
              <span class="bg-black/80 text-gray-300 text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded border border-white/10">${esc(t.goal_type_display || 'MISSION')}</span>
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
    const feed = document.getElementById('hitlist-feed');
    const list = applyFilters((STATE.data.hitlist || []).filter((b) => !!b.is_hitlist));
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
      const canHunt = HUB.can_issue && !closed && b.is_claimable;
      const btnState = canHunt ? '' : 'disabled';
      const btnClass = canHunt ? 'bg-dc-neon hover:bg-red-600 text-white shadow-[0_0_20px_rgba(255,0,85,0.3)]' : 'bg-black/40 border border-white/5 text-gray-600 cursor-not-allowed';
      const btnText = canHunt ? 'Claim Bounty' : (HUB.primary_team ? '<i class="fa-solid fa-lock mr-1"></i> Captain Only' : '<i class="fa-solid fa-lock mr-1"></i> Team Reqd');
      return `
        <div class="glass-heavy accent-neon rounded-2xl p-6 relative overflow-hidden group fade-enter border border-white/5 transition-all">
          <div class="absolute inset-0 bg-gradient-to-r from-dc-neon/10 to-transparent z-0 opacity-40"></div>
          <div class="relative z-10 flex flex-col md:flex-row gap-8 items-center">
            <div class="flex-shrink-0 text-center">
              <div class="relative inline-block mb-3">
                <div class="absolute inset-0 bg-dc-neon blur-[20px] opacity-40 rounded-full"></div>
                <div class="w-28 h-28 rounded-full border-2 border-dc-neon relative z-10 bg-gradient-to-br from-dc-neon/30 to-black flex items-center justify-center text-white font-display font-black text-2xl">
                  ${esc((b.issuer_team_name || '?').slice(0, 2).toUpperCase())}
                </div>
                <div class="absolute -bottom-2 left-1/2 transform -translate-x-1/2 bg-black text-dc-neon text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded border border-dc-neon whitespace-nowrap">Bounty</div>
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
    const feed = document.getElementById('royale-feed');
    const list = applyFilters(STATE.data.royale);
    if (!list.length) {
      feed.innerHTML = `<div class="col-span-full">${emptyState({ icon: 'fa-crown', title: 'No Lobbies Scheduled', sub: 'Custom rooms drop on the schedule. Check back soon.' })}</div>`;
      return;
    }
    feed.innerHTML = list.map((l) => {
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
      const splitChips = Object.keys(splits).sort((a, b) => +a - +b).slice(0, 5).map((k) =>
        `<span class="font-mono text-[10px] text-dc-gold">#${esc(k)}: ${esc(splits[k])}${mode === 'PERCENT' ? '%' : ' DC'}</span>`
      ).join('<span class="text-gray-700">&middot;</span>');
      const canReserve = !closed && remaining > 0;
      return `
        <div class="glass-heavy accent-gold rounded-2xl p-6 relative overflow-hidden group fade-enter border border-white/5 transition-all">
          <div class="absolute -top-12 -right-12 w-40 h-40 bg-dc-gold opacity-10 blur-3xl rounded-full pointer-events-none"></div>
          <div class="relative z-10">
            <div class="flex items-start justify-between gap-3 mb-3">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-widest text-dc-gold mb-1">${esc(l.game_short_code || 'DROPZONE')}</p>
                <h3 class="font-display font-black text-white text-2xl leading-tight">${esc(l.title)}</h3>
              </div>
              <span class="px-2 py-1 rounded bg-white/5 border border-white/10 text-[9px] font-bold uppercase tracking-widest text-gray-300">${esc(l.status_display || l.status)}</span>
            </div>
            ${closureHtml(l)}
            ${closed ? '' : (sched ? `<p class="text-xs text-gray-400 mb-3 font-mono"><i class="fa-solid fa-clock text-dc-cyan mr-1"></i> ${esc(schedText)}</p>` : '')}
            <div class="mb-3">
              <div class="flex items-center justify-between text-[10px] font-mono text-gray-500 mb-1.5">
                <span>${taken}/${max} slots</span>
                <span>${remaining} left</span>
              </div>
              <div class="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                <div class="h-full" style="width: ${fillPct}%; background: linear-gradient(90deg, #00e5ff, #ffd700); box-shadow: 0 0 8px rgba(0,229,255,.6)"></div>
              </div>
            </div>
            <div class="flex items-center gap-2 flex-wrap mb-4">
              <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-dc-gold/15 border border-dc-gold/30 text-dc-gold text-[11px] font-mono font-bold"><i class="fa-solid fa-coins"></i> ${fee} DC / slot</span>
              ${splitChips ? `<div class="flex items-center gap-1.5">${splitChips}</div>` : ''}
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <a href="${lobbyUrl}" class="inline-flex items-center justify-center rounded-lg border border-dc-gold/25 bg-dc-gold/10 px-3 py-3 text-xs font-black uppercase tracking-widest text-dc-gold hover:bg-dc-gold/20">
                View Lobby
              </a>
              <button ${canReserve ? '' : 'disabled'} data-reserve-royale="${esc(l.id)}" data-fee="${fee}"
                      class="btn-cyber w-full bg-dc-gold hover:bg-yellow-400 text-black font-black uppercase tracking-widest py-3 transition-all ${canReserve ? '' : 'opacity-50 cursor-not-allowed'}">
                Reserve Slot
              </button>
            </div>
          </div>
        </div>`;
    }).join('');
  }

  function renderActiveOps() {
    const box = document.getElementById('active-ops-container');
    const counter = document.getElementById('ops-count');
    if (!box) return;
    const operations = STATE.data.myOperations || [];
    if (counter) counter.textContent = `${operations.length} ACTIVE`;
    if (!operations.length) {
      box.innerHTML = `<div class="text-center py-6 px-3">
        <p class="text-xs font-bold uppercase tracking-widest text-gray-500 mb-2">No operations yet</p>
        <p class="text-[11px] leading-relaxed text-gray-600">Start a Mission, create a Showdown, claim a Bounty, or reserve a Dropzone slot.</p>
      </div>`;
      return;
    }
    box.innerHTML = operations.slice(0, 8).map((op) => {
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
      return `
        <div class="bg-black/40 rounded-lg p-3 border border-white/5 hover:border-white/15 transition group">
          <div class="flex items-start justify-between gap-2 mb-2">
            <div class="min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="w-1.5 h-1.5 rounded-full ${typeMeta.dot}"></span>
                <span class="text-[9px] font-black uppercase tracking-widest ${typeMeta.text}">${typeMeta.label}</span>
              </div>
              <p class="text-xs font-bold text-white truncate">${esc(op.title || typeMeta.label)}</p>
            </div>
            <span class="text-[9px] font-mono text-gray-500 uppercase">${esc(op.status || '')}</span>
          </div>
          <div class="flex items-center gap-2 flex-wrap text-[10px] font-mono text-gray-500 mb-3">
            <span>${esc(game)}</span>
            ${op.team_name ? `<span class="text-gray-700">&middot;</span><span>${esc(op.team_name)}</span>` : ''}
            ${scheduledText ? `<span class="text-gray-700">&middot;</span><span>${esc(scheduledText)}</span>` : ''}
            ${fee ? `<span class="text-gray-700">&middot;</span><span>${fee.toLocaleString()} DC entry</span>` : ''}
            ${reward ? `<span class="text-gray-700">&middot;</span><span class="text-dc-gold">${esc(reward)}</span>` : ''}
          </div>
          ${reviewLabel ? `<div class="mb-3 rounded-md border border-white/5 bg-white/[0.03] px-2.5 py-2 text-[10px] font-bold uppercase tracking-widest text-gray-400">${esc(reviewLabel)}</div>` : ''}
          ${isPrimarySubmit ? `
            <button type="button" data-submit-showdown-result="${esc(op.id)}" class="inline-flex items-center justify-center gap-2 w-full rounded-md border px-3 py-2 text-[10px] font-black uppercase tracking-widest ${actionClass}">
              <i class="fa-solid fa-flag-checkered"></i>
              Submit Result
            </button>
          ` : `
            <a href="${esc(actionUrl)}" class="inline-flex items-center justify-center gap-2 w-full rounded-md border px-3 py-2 text-[10px] font-black uppercase tracking-widest ${actionClass}">
              ${op.is_action_required ? '<i class="fa-solid fa-bolt"></i>' : '<i class="fa-solid fa-arrow-right"></i>'}
              ${esc(op.next_action_label || 'View Details')}
            </a>
          `}
          ${showDetailLink ? `
            <a href="${esc(detailUrl)}" class="mt-2 inline-flex items-center justify-center gap-2 w-full rounded-md border border-white/10 bg-white/[0.03] px-3 py-2 text-[10px] font-black uppercase tracking-widest text-gray-300 hover:text-white hover:border-dc-cyan/30">
              <i class="fa-solid fa-list-check"></i>
              View Detail Timeline
            </a>
          ` : ''}
          ${lobbyDetailUrl ? `
            <a href="${esc(lobbyDetailUrl)}" class="mt-2 inline-flex items-center justify-center gap-2 w-full rounded-md border border-dc-gold/20 bg-dc-gold/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-dc-gold hover:bg-dc-gold/20">
              <i class="fa-solid fa-map-location-dot"></i>
              View Lobby
            </a>
          ` : ''}
          ${canSecondarySubmit ? `
            <button type="button" data-submit-showdown-result="${esc(op.id)}" class="inline-flex items-center justify-center gap-2 w-full rounded-md border border-white/10 bg-white/[0.03] px-3 py-2 mt-2 text-[10px] font-black uppercase tracking-widest text-gray-300 hover:text-white hover:border-dc-cyan/30">
              <i class="fa-solid fa-flag-checkered"></i>
              Submit Result
            </button>
          ` : ''}
        </div>`;
    }).join('');
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
    try { STATE.data.clashes = await jsonFetch(API.challengesList); }
    catch { STATE.data.clashes = []; }
    STATE.loaded.clashes = true;
    renderClashFeed();
  }
  async function loadContracts() {
    try { STATE.data.contracts = await jsonFetch(API.contractsList); }
    catch { STATE.data.contracts = []; }
    STATE.loaded.contracts = true;
    renderContractsFeed();
  }
  async function loadHitlist() {
    try { STATE.data.hitlist = await jsonFetch(API.bountiesList); }
    catch { STATE.data.hitlist = []; }
    STATE.loaded.hitlist = true;
    renderHitlistFeed();
  }
  async function loadRoyale() {
    try { STATE.data.royale = await jsonFetch(API.royaleList); }
    catch { STATE.data.royale = []; }
    STATE.loaded.royale = true;
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
      selectedTeamId: choices.length === 1 ? choices[0].id : '',
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
    if (!HUB.primary_team) { toast('You need a team to claim bounties.', 'error'); return; }
    const ok = await openConfirm({
      title: 'Claim this Bounty?',
      body: 'Your entry fee locks in escrow. Beat the issuer under the posted rules to claim the Bounty reward.',
      lockNote: `This will lock ${Number(fee).toLocaleString()} DC in escrow.`,
    });
    if (!ok) return;
    try {
      await jsonFetch(API.bountyClaim(id), {
        method: 'POST',
        body: JSON.stringify({ claiming_team_id: HUB.primary_team.id }),
      });
      toast('Bounty claim submitted. Match room spawning.', 'success');
      await loadHitlist();
      await loadMyOperations();
    } catch (err) { handleApiError(err); }
  }

  async function onReserveRoyale(id, fee) {
    const ok = await openConfirm({
      title: 'Reserve a Dropzone slot?',
      body: 'The entry fee locks in escrow. Room ID drops at match start. Cancel before match start to refund.',
      lockNote: `This will lock ${Number(fee).toLocaleString()} DC in escrow.`,
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
    if (myTeams.length === 1) document.getElementById('clash-team').value = String(myTeams[0].id);
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
    if (myTeams.length === 1) document.getElementById('hitlist-team').value = String(myTeams[0].id);
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
      body: 'Your Bounty reward locks immediately. Each challenger pays the entry fee per attempt.',
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
    const teamId = params.get('challenge_team_id');
    const teamName = params.get('challenge_team_name') || '';
    if (teamId && HUB.can_issue) {
      switchTab('showdown', { updateHash: true });
      openSlideOver('create-clash', { opponentId: teamId, opponentName: teamName });
      return;
    }
    const action = (params.get('action') || '').toLowerCase();
    if (['create-clash', 'create-showdown', 'showdown'].includes(action) && HUB.can_issue) { switchTab('showdown', { updateHash: true }); openSlideOver('create-clash'); }
    if (['create-hitlist', 'create-bounty', 'bounty'].includes(action) && HUB.can_issue) { switchTab('bounty', { updateHash: true }); openSlideOver('create-hitlist'); }
  }

  // ── Event binding ─────────────────────────────────────────────────

  function bindEvents() {
    // Tab triggers (delegated)
    document.getElementById('tab-triggers').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-tab]');
      if (btn) switchTab(btn.dataset.tab, { updateHash: true });
    });

    // Game filter
    document.getElementById('game-filter-bar').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-game]');
      if (btn) setGameFilter(btn.dataset.game);
    });

    // Search
    const search = document.getElementById('global-search');
    if (search) {
      search.addEventListener('input', (e) => {
        STATE.searchQuery = e.target.value;
        renderAllFeeds();
      });
    }

    // Global delegated clicks for: open/close slide, go-tab, accept/hunt/reserve/enroll
    document.body.addEventListener('click', (e) => {
      const target = e.target;
      if (!(target instanceof Element)) return;

      const openSlide = target.closest('[data-open-slide]');
      if (openSlide) { openSlideOver(openSlide.dataset.openSlide); return; }

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
        const op = (STATE.data.myOperations || []).find((item) => item.id === resultBtn.dataset.submitShowdownResult);
        if (op && op.match_room_url) { window.location.href = op.match_room_url; return; }
        if (op) openResultModal(op);
        return;
      }

      const closeResult = target.closest('[data-close-result-modal]');
      if (closeResult) { closeResultModal(); return; }

      const cancelConfirm = target.closest('[data-cancel-confirm]');
      if (cancelConfirm) { closeConfirm(false); return; }
    });

    // Backdrop click to close slide
    const backdrop = document.getElementById('slide-over-backdrop');
    if (backdrop) {
      backdrop.addEventListener('click', () => {
        closeSlideOver('create-clash');
        closeSlideOver('create-hitlist');
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
    hydrateLeftColumn();
    renderHero();
    renderActionPermissions();
    bindEvents();
    switchTab(window.location.hash ? window.location.hash.slice(1) : 'showdown');
    window.addEventListener('hashchange', () => switchTab(window.location.hash.slice(1) || 'showdown'));
    // Fetch all in parallel
    Promise.all([loadClashes(), loadContracts(), loadHitlist(), loadRoyale(), loadMyOperations()])
      .then(() => applyUrlPrefill());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
