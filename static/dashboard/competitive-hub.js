(function () {
  'use strict';

  const API = {
    contractsList:       '/api/v1/contracts/templates/',
    contractsEnroll:     (templateId) => `/api/v1/contracts/enroll/${templateId}/`,
    challengesList:      '/api/v1/challenges/',
    challengeCreate:     '/api/v1/challenges/',
    challengeAccept:     (challengeId) => `/api/v1/challenges/${challengeId}/accept/`,
    bountiesList:        '/api/v1/bounties/',
    bountyCreate:        '/api/v1/bounties/',
    bountyClaim:         (bountyId) => `/api/v1/bounties/${bountyId}/claim/`,
    royaleList:          '/api/v1/royale/lobbies/',
    royaleReserve:       (lobbyId) => `/api/v1/royale/lobbies/${lobbyId}/reserve/`,
  };

  function readHubContext() {
    const el = document.getElementById('hub-context');
    if (!el) return { my_teams: [], games: [] };
    try { return JSON.parse(el.textContent) || {}; }
    catch { return { my_teams: [], games: [] }; }
  }
  const HUB = readHubContext();

  // ── CSRF / fetch helpers ───────────────────────────────────────────

  function getCookie(name) {
    const cookies = (document.cookie || '').split(';');
    for (const c of cookies) {
      const v = c.trim();
      if (v.startsWith(name + '=')) return decodeURIComponent(v.substring(name.length + 1));
    }
    return '';
  }

  async function jsonFetch(url, options = {}) {
    const init = Object.assign(
      { method: 'GET', credentials: 'same-origin', headers: {} },
      options
    );
    init.headers = Object.assign(
      {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      init.headers || {}
    );
    if (init.method && init.method.toUpperCase() !== 'GET') {
      init.headers['X-CSRFToken'] = getCookie('csrftoken');
    }
    let res;
    try {
      res = await fetch(url, init);
    } catch (netErr) {
      throw { status: 0, body: { detail: 'Network error — please try again.' } };
    }
    let body = {};
    try { body = await res.json(); } catch { body = {}; }
    if (!res.ok) throw { status: res.status, body };
    return body;
  }

  // ── Toast shelf ────────────────────────────────────────────────────

  function toast(kind, message, ttlMs) {
    const shelf = document.getElementById('toast-shelf');
    if (!shelf) return;
    const node = document.createElement('div');
    node.className = `toast ${kind || 'info'}`;
    node.innerHTML = `
      <div class="text-sm font-semibold leading-snug">${escapeHtml(message)}</div>
    `;
    shelf.appendChild(node);
    setTimeout(() => {
      node.style.transition = 'opacity .25s ease, transform .25s ease';
      node.style.opacity = '0'; node.style.transform = 'translateX(20px)';
      setTimeout(() => node.remove(), 250);
    }, ttlMs || 4500);
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function handleApiError(err) {
    const code = err && err.body && err.body.code;
    const detail = (err && err.body && err.body.detail) || 'Something went wrong.';
    if (code === 'INSUFFICIENT_FUNDS') {
      toast('error', 'Not enough DeltaCoins. Please visit the Treasury to top up.', 6000);
      return;
    }
    if (err && err.status === 401) {
      toast('error', 'You need to log in to do that.');
      return;
    }
    if (err && err.status === 403) {
      toast('error', 'You do not have permission for this action.');
      return;
    }
    toast('error', detail);
  }

  // ── Confirmation modal ────────────────────────────────────────────

  let _modalDeferred = null;

  function openConfirm({ title, body, lockNote }) {
    return new Promise((resolve) => {
      _modalDeferred = resolve;
      document.getElementById('confirm-title').textContent = title || 'Confirm action';
      document.getElementById('confirm-body').textContent = body || '';
      document.getElementById('confirm-lock').textContent = lockNote || '';
      document.getElementById('confirm-modal').classList.remove('hidden');
    });
  }

  function closeConfirm(result) {
    document.getElementById('confirm-modal').classList.add('hidden');
    if (_modalDeferred) { _modalDeferred(!!result); _modalDeferred = null; }
  }

  function bindModal() {
    document.querySelectorAll('[data-action="cancel-modal"]').forEach((btn) => {
      btn.addEventListener('click', () => closeConfirm(false));
    });
    document.getElementById('confirm-go').addEventListener('click', () => closeConfirm(true));
    document.getElementById('confirm-modal').addEventListener('click', (e) => {
      if (e.target.id === 'confirm-modal') closeConfirm(false);
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && _modalDeferred) closeConfirm(false);
    });
  }

  // ── Tab switching ─────────────────────────────────────────────────

  function bindTabs() {
    const tabs = document.querySelectorAll('[data-tab]');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => activateTab(tab.dataset.tab));
    });
  }

  function activateTab(name) {
    document.querySelectorAll('[data-tab]').forEach((t) => {
      t.dataset.active = String(t.dataset.tab === name);
    });
    document.querySelectorAll('.arena-panel').forEach((p) => {
      const isMatch = p.id === `panel-${name}`;
      p.classList.toggle('hidden', !isMatch);
      p.dataset.active = String(isMatch);
    });
    if (!loaded[name]) {
      loaded[name] = true;
      LOADERS[name]();
    }
  }

  // ── Common card helpers ───────────────────────────────────────────

  function skeletonCard() {
    return `
      <div class="glass-card p-5 space-y-3">
        <div class="skeleton h-4 w-2/3"></div>
        <div class="skeleton h-3 w-1/2"></div>
        <div class="skeleton h-12 w-full mt-4"></div>
        <div class="skeleton h-9 w-32 mt-4"></div>
      </div>`;
  }

  const EMPTY_THEMES = {
    contracts: { tone: 'violet', icon: '<i class="fa-solid fa-scroll"></i>',     headline: 'No Active Missions',  subline: 'The Contract Board is quiet right now. Drop in for a self-challenge — pay a small entry fee, hit the goal, claim a bigger reward.', cta: 'Browse Contracts' },
    clash:     { tone: 'cyan',   icon: '<i class="fa-solid fa-bolt-lightning"></i>', headline: 'No Open Clashes',     subline: 'Issue a Crown Clash from your team page or wait for an opponent to drop a callout. Both stakes lock the moment the second side accepts.', cta: 'Issue a Clash' },
    hitlist:   { tone: 'neon',   icon: '<i class="fa-solid fa-crosshairs"></i>',  headline: 'No Bounties on The Hitlist', subline: 'The kings are quiet. Top teams: stake your reputation and dare anyone to take you down.', cta: 'Post a Bounty' },
    royale:    { tone: 'gold',   icon: '<i class="fa-solid fa-crown"></i>',       headline: 'No Royale Lobbies Scheduled', subline: 'Custom rooms drop on the schedule.  Reservations open ahead of match time, prize splits are fully transparent.', cta: 'Set Reminder' },
  };

  function emptyState(kind, fallbackMsg) {
    const theme = EMPTY_THEMES[kind] || { tone: 'violet', icon: '⌂', headline: 'Nothing here yet', subline: fallbackMsg || '', cta: 'Refresh' };
    return `
      <div class="col-span-full">
        <div class="empty-state ${theme.tone}">
          <div class="es-grid"></div>
          <div class="es-glow"></div>
          <div class="relative">
            <div class="es-icon">${theme.icon}</div>
            <h3 class="font-display font-black text-white text-xl mb-2">${escapeHtml(theme.headline)}</h3>
            <p class="text-sm text-dc-textMuted max-w-md mx-auto leading-relaxed mb-7">${escapeHtml(theme.subline)}</p>
            <button type="button" class="es-cta" data-empty-cta="${kind}">
              ${escapeHtml(theme.cta)}
              <i class="fa-solid fa-arrow-right text-[10px]"></i>
            </button>
          </div>
        </div>
      </div>`;
  }

  function errorState(message) {
    return `
      <div class="col-span-full">
        <div class="empty-state neon">
          <div class="es-grid"></div>
          <div class="es-glow"></div>
          <div class="relative">
            <div class="es-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
            <h3 class="font-display font-black text-white text-xl mb-2">Something went sideways</h3>
            <p class="text-sm text-rose-200/80 max-w-md mx-auto leading-relaxed mb-6">${escapeHtml(message)}</p>
            <button type="button" class="es-cta" onclick="window.location.reload()">
              Retry
              <i class="fa-solid fa-rotate-right text-[10px]"></i>
            </button>
          </div>
        </div>
      </div>`;
  }

  function closureHtml(item) {
    if (!item || !item.closure_reason) return '';
    const note = item.closure_note || item.closure_reason_display || item.closure_reason;
    const tone = pickClosureTone(item.closure_reason);
    return `
      <div class="closure-pill ${tone}" role="status" aria-live="polite">
        <span aria-hidden="true">●</span>
        <span>Closed: ${escapeHtml(note)}</span>
      </div>`;
  }

  function pickClosureTone(reason) {
    const r = String(reason || '').toUpperCase();
    if (r === 'NORMAL' || r === 'COMPLETED' || r === 'SETTLED_NORMAL' || r === 'CLAIMED') return 'neutral';
    if (r === 'EXPIRED' || r === 'CANCELLED_INSUFFICIENT' || r.endsWith('_NO_SHOW')) return 'amber';
    return ''; // default red tone
  }

  // ── 1. Crown Contracts ────────────────────────────────────────────

  async function loadContracts() {
    const grid = document.getElementById('contracts-grid');
    grid.innerHTML = Array.from({ length: 3 }).map(skeletonCard).join('');
    try {
      const items = await jsonFetch(API.contractsList);
      document.getElementById('contracts-count').textContent =
        items.length ? `${items.length} mission${items.length === 1 ? '' : 's'}` : '';
      grid.innerHTML = items.length
        ? items.map(renderContractCard).join('')
        : emptyState('contracts');
      grid.querySelectorAll('[data-enroll-id]').forEach((btn) => {
        btn.addEventListener('click', () => onEnrollContract(btn.dataset.enrollId, btn.dataset.fee));
      });
    } catch (err) {
      grid.innerHTML = errorState('Failed to load contracts.');
      handleApiError(err);
    }
  }

  function renderContractCard(t) {
    const closure = ''; // ContractTemplate has no closure (the enrollment does); none on listing
    const fee = Number(t.entry_fee_dc || 0);
    const reward = Number(t.reward_dc || 0);
    const duration = Number(t.duration_hours || 0);
    return `
      <article class="glass-card accent-violet p-6 flex flex-col gap-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-[0.65rem] uppercase tracking-[0.18em] text-indigo-300/80 font-bold">
              ${escapeHtml(t.game_short_code || 'CONTRACT')}
            </div>
            <h3 class="text-base font-black text-white mt-1 leading-tight">${escapeHtml(t.title)}</h3>
          </div>
          <span class="state-badge open">${escapeHtml(t.goal_type_display || 'MISSION')}</span>
        </div>
        ${closure}
        <p class="text-sm text-dc-textMuted leading-relaxed line-clamp-3">${escapeHtml(t.description || '')}</p>
        <div class="flex items-center gap-2 flex-wrap">
          <span class="dc-chip">⨯ ${fee.toLocaleString()} DC entry</span>
          <span class="dc-chip" style="color:#10B981; border-color:rgba(16,185,129,.30); background:linear-gradient(135deg, rgba(16,185,129,.15), rgba(16,185,129,.04))">
            ＋ ${reward.toLocaleString()} DC reward
          </span>
          ${duration ? `<span class="text-[0.65rem] text-dc-textMuted font-mono">⏱ ${duration}h window</span>` : ''}
          ${t.badge_slug ? `<span class="text-[0.65rem] text-amber-300 font-mono">🏆 ${escapeHtml(t.badge_slug)}</span>` : ''}
        </div>
        <div class="flex justify-end pt-1">
          <button class="btn-cta px-5 py-2 rounded-xl text-sm" data-enroll-id="${escapeHtml(t.id)}" data-fee="${fee}">
            Enroll
          </button>
        </div>
      </article>`;
  }

  async function onEnrollContract(templateId, fee) {
    const ok = await openConfirm({
      title: 'Enroll in this Crown Contract?',
      body: 'Your entry fee will be locked in our smart-lock vault and forfeited to the platform if you fail to meet the goal in time.',
      lockNote: `This will lock ${Number(fee).toLocaleString()} DC in escrow.`,
    });
    if (!ok) return;
    try {
      const enrollment = await jsonFetch(API.contractsEnroll(templateId), { method: 'POST', body: '{}' });
      toast('success', `Enrolled — reference ${enrollment.reference_code || ''}`);
    } catch (err) {
      handleApiError(err);
    }
  }

  // ── 2. Crown Clash ────────────────────────────────────────────────

  async function loadClash() {
    const grid = document.getElementById('clash-grid');
    grid.innerHTML = Array.from({ length: 2 }).map(skeletonCard).join('');
    try {
      const items = await jsonFetch(API.challengesList);
      // Only Crown Clashes (entry_fee_dc > 0)
      const clashes = (items || []).filter((c) => Number(c.entry_fee_dc || 0) > 0);
      document.getElementById('clash-count').textContent =
        clashes.length ? `${clashes.length} active` : '';
      grid.innerHTML = clashes.length
        ? clashes.map(renderClashCard).join('')
        : emptyState('clash');
      grid.querySelectorAll('[data-accept-id]').forEach((btn) => {
        btn.addEventListener('click', () =>
          onAcceptClash(btn.dataset.acceptId, btn.dataset.fee)
        );
      });
    } catch (err) {
      grid.innerHTML = errorState('Failed to load Crown Clashes.');
      handleApiError(err);
    }
  }

  function renderClashCard(c) {
    const fee = Number(c.entry_fee_dc || 0);
    const pot = Number(c.prize_pot_dc || fee * 2);
    const closed = !!c.closure_reason;
    const acceptable = !closed && c.status === 'OPEN';
    return `
      <article class="glass-card accent-cyan p-6 flex flex-col gap-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-[0.65rem] uppercase tracking-[0.18em] text-cyan-300/80 font-bold">
              ${escapeHtml(c.game_short_code || 'CLASH')} · BO${c.best_of || 1}
            </div>
            <h3 class="text-base font-black text-white mt-1 leading-tight">${escapeHtml(c.title || 'Crown Clash')}</h3>
          </div>
          <span class="state-badge ${closed ? '' : 'open'}">${escapeHtml(c.status_display || c.status)}</span>
        </div>
        ${closureHtml(c)}

        <div class="grid grid-cols-3 gap-3 items-center">
          <div class="text-right">
            <div class="text-xs text-dc-textMuted">Challenger</div>
            <div class="text-sm font-bold text-white truncate">${escapeHtml(c.challenger_team_name || '—')}</div>
          </div>
          <div class="text-center">
            <div class="text-[0.65rem] uppercase tracking-widest text-dc-textMuted mb-1">vs</div>
            <div class="dc-chip mx-auto">⚡ ${pot.toLocaleString()} DC pot</div>
          </div>
          <div class="text-left">
            <div class="text-xs text-dc-textMuted">Opponent</div>
            <div class="text-sm font-bold text-white truncate">${escapeHtml(c.challenged_team_name || 'Open Challenge')}</div>
          </div>
        </div>

        <div class="flex items-center justify-between pt-1">
          <span class="text-[0.7rem] font-mono text-dc-textMuted">Entry fee · ${fee.toLocaleString()} DC each side</span>
          <button class="btn-cta px-5 py-2 rounded-xl text-sm" ${acceptable ? '' : 'disabled'}
                  data-accept-id="${escapeHtml(c.id)}" data-fee="${fee}">
            Accept Clash
          </button>
        </div>
      </article>`;
  }

  async function onAcceptClash(challengeId, fee) {
    const ok = await openConfirm({
      title: 'Accept this Crown Clash?',
      body: 'Both sides lock their stakes simultaneously into our smart-lock vault. Winner takes the pot (minus a 5% platform fee). No-shows forfeit.',
      lockNote: `This will lock ${Number(fee).toLocaleString()} DC in escrow.`,
    });
    if (!ok) return;
    try {
      const updated = await jsonFetch(API.challengeAccept(challengeId), {
        method: 'POST', body: JSON.stringify({}),
      });
      toast('success', `Locked ${Number(fee).toLocaleString()} DC. Pot now ${Number(updated.prize_pot_dc || 0).toLocaleString()} DC.`);
      loaded.clash = false; activateTab('clash');
    } catch (err) {
      handleApiError(err);
    }
  }

  // ── 3. The Hitlist ────────────────────────────────────────────────

  async function loadHitlist() {
    const grid = document.getElementById('hitlist-grid');
    grid.innerHTML = Array.from({ length: 2 }).map(skeletonCard).join('');
    try {
      const items = await jsonFetch(API.bountiesList);
      const hits = (items || []).filter((b) => !!b.is_hitlist);
      document.getElementById('hitlist-count').textContent =
        hits.length ? `${hits.length} contract${hits.length === 1 ? '' : 's'}` : '';
      grid.innerHTML = hits.length
        ? hits.map(renderHitlistCard).join('')
        : emptyState('hitlist');
      grid.querySelectorAll('[data-claim-id]').forEach((btn) => {
        btn.addEventListener('click', () =>
          onClaimHitlist(btn.dataset.claimId, btn.dataset.fee)
        );
      });
    } catch (err) {
      grid.innerHTML = errorState('Failed to load Hitlist.');
      handleApiError(err);
    }
  }

  function renderHitlistCard(b) {
    const reward = Number(b.reward_amount_dc || 0);
    const entry  = Number(b.challenger_entry_fee_dc || 0);
    const closed = !!b.closure_reason;
    return `
      <article class="glass-card accent-neon p-6 flex flex-col gap-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-[0.65rem] uppercase tracking-[0.18em] text-rose-300/80 font-bold">
              ${escapeHtml(b.game_short_code || 'HITLIST')}
            </div>
            <h3 class="text-base font-black text-white mt-1 leading-tight">${escapeHtml(b.title || 'Beat The Kings')}</h3>
          </div>
          <span class="state-badge ${closed ? '' : 'open'}">${escapeHtml(b.status_display || b.status)}</span>
        </div>
        ${closureHtml(b)}

        <p class="text-sm text-dc-textMuted leading-relaxed line-clamp-3">${escapeHtml(b.description || '')}</p>

        <div class="flex flex-wrap items-center gap-2">
          <span class="dc-chip">👑 ${reward.toLocaleString()} DC bounty</span>
          <span class="dc-chip" style="color:#FCA5A5; border-color:rgba(244,63,94,.35); background:linear-gradient(135deg, rgba(244,63,94,.16), rgba(244,63,94,.04))">
            ⚔ ${entry.toLocaleString()} DC entry
          </span>
          <span class="text-[0.65rem] font-mono text-dc-textMuted">issued by ${escapeHtml(b.issuer_team_name || '—')}</span>
        </div>

        <div class="flex justify-end">
          <button class="btn-cta px-5 py-2 rounded-xl text-sm" ${closed || !b.is_claimable ? 'disabled' : ''}
                  data-claim-id="${escapeHtml(b.id)}" data-fee="${entry}">
            Hunt the Bounty
          </button>
        </div>
      </article>`;
  }

  async function onClaimHitlist(bountyId, fee) {
    const teamId = window.prompt('Enter your claiming team ID (or leave blank to use your captain team):');
    if (teamId === null) return;
    const ok = await openConfirm({
      title: 'Submit Hitlist claim?',
      body: 'Your entry fee will be locked in escrow. Beat the issuer to win the bounty (minus 5% fee). Lose, and your entry fee transfers to the issuer.',
      lockNote: `This will lock ${Number(fee).toLocaleString()} DC in escrow.`,
    });
    if (!ok) return;
    try {
      await jsonFetch(API.bountyClaim(bountyId), {
        method: 'POST',
        body: JSON.stringify({
          claiming_team_id: Number(teamId) || 0,
        }),
      });
      toast('success', 'Claim submitted. Your match lobby will appear shortly.');
      loaded.hitlist = false; activateTab('hitlist');
    } catch (err) {
      handleApiError(err);
    }
  }

  // ── 4. Crown Royale ───────────────────────────────────────────────

  async function loadRoyale() {
    const grid = document.getElementById('royale-grid');
    grid.innerHTML = Array.from({ length: 3 }).map(skeletonCard).join('');
    try {
      const items = await jsonFetch(API.royaleList);
      document.getElementById('royale-count').textContent =
        items.length ? `${items.length} lobb${items.length === 1 ? 'y' : 'ies'}` : '';
      grid.innerHTML = items.length
        ? items.map(renderRoyaleCard).join('')
        : emptyState('royale');
      grid.querySelectorAll('[data-reserve-id]').forEach((btn) => {
        btn.addEventListener('click', () =>
          onReserveRoyale(btn.dataset.reserveId, btn.dataset.fee)
        );
      });
    } catch (err) {
      grid.innerHTML = errorState('Failed to load Royale lobbies.');
      handleApiError(err);
    }
  }

  function renderRoyaleCard(l) {
    const fee = Number(l.entry_fee_per_slot_dc || 0);
    const max = Number(l.max_slots || 0);
    const reserved = Number(l.reserved_slots || 0);
    const remaining = Number(l.remaining_slots || Math.max(0, max - reserved));
    const closed = !!l.closure_reason;
    const sched = l.scheduled_at ? new Date(l.scheduled_at) : null;
    const schedText = sched ? sched.toLocaleString(undefined, {
      weekday: 'short', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    }) : '';
    const fillPct = max ? Math.min(100, Math.round((reserved / max) * 100)) : 0;
    const splits = (l.prize_distribution && l.prize_distribution.splits) || {};
    const mode = (l.prize_distribution && l.prize_distribution.mode) || 'PERCENT';
    const distributionParts = Object.keys(splits)
      .sort((a, b) => Number(a) - Number(b))
      .slice(0, 5)
      .map((k) => `<span class="font-mono text-[0.7rem] text-amber-300">#${k}: ${splits[k]}${mode === 'PERCENT' ? '%' : ' DC'}</span>`)
      .join('<span class="text-dc-textMuted">·</span>');

    return `
      <article class="glass-card accent-gold p-6 flex flex-col gap-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-[0.65rem] uppercase tracking-[0.18em] text-amber-300/80 font-bold">
              ${escapeHtml(l.game_short_code || 'ROYALE')}
            </div>
            <h3 class="text-base font-black text-white mt-1 leading-tight">${escapeHtml(l.title)}</h3>
          </div>
          <span class="state-badge ${closed ? '' : (l.status === 'LIVE' ? 'live' : 'open')}">${escapeHtml(l.status_display || l.status)}</span>
        </div>
        ${closureHtml(l)}

        ${closed ? '' : (sched ? `
          <div class="flex items-center gap-2 text-xs text-dc-textMuted font-mono">
            <span class="pulse-dot"></span>
            <span>Match: ${escapeHtml(schedText)}</span>
          </div>` : '')}

        <div>
          <div class="flex items-center justify-between text-[0.7rem] font-mono text-dc-textMuted mb-1.5">
            <span>${reserved}/${max} slots</span>
            <span>${remaining} left</span>
          </div>
          <div class="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
            <div class="h-full" style="width: ${fillPct}%; background: linear-gradient(90deg, #6366F1, #FBBF24); box-shadow: 0 0 8px rgba(99,102,241,.6)"></div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <span class="dc-chip">⨯ ${fee.toLocaleString()} DC / slot</span>
          ${distributionParts ? `<div class="flex items-center gap-1.5">${distributionParts}</div>` : ''}
        </div>

        <div class="flex justify-end">
          <button class="btn-cta px-5 py-2 rounded-xl text-sm" ${closed || remaining <= 0 ? 'disabled' : ''}
                  data-reserve-id="${escapeHtml(l.id)}" data-fee="${fee}">
            Reserve Slot
          </button>
        </div>
      </article>`;
  }

  async function onReserveRoyale(lobbyId, fee) {
    const ok = await openConfirm({
      title: 'Reserve a Crown Royale slot?',
      body: 'The entry fee will be locked in escrow. The custom-room ID & password are revealed at match start. No-shows forfeit; cancel before match start to refund.',
      lockNote: `This will lock ${Number(fee).toLocaleString()} DC in escrow.`,
    });
    if (!ok) return;
    try {
      const entry = await jsonFetch(API.royaleReserve(lobbyId), { method: 'POST', body: '{}' });
      toast('success', `Slot reserved (entry ${entry.id ? entry.id.slice(0, 8) : ''}). See you at match time!`);
      loaded.royale = false; activateTab('royale');
    } catch (err) {
      handleApiError(err);
    }
  }

  // ── Create-modal infrastructure ───────────────────────────────────

  function openFormModal(name, opts = {}) {
    const root = document.getElementById(`modal-${name}`);
    if (!root) return;
    root.classList.remove('hidden');
    if (name === 'create-clash')   resetClashForm(opts);
    if (name === 'create-hitlist') resetHitlistForm(opts);
    const firstInput = root.querySelector('input, select');
    if (firstInput) setTimeout(() => firstInput.focus(), 50);
  }

  function closeFormModal(name) {
    const root = document.getElementById(`modal-${name}`);
    if (!root) return;
    root.classList.add('hidden');
  }

  function bindFormModals() {
    document.querySelectorAll('[data-open-modal]').forEach((btn) => {
      btn.addEventListener('click', () => openFormModal(btn.dataset.openModal));
    });
    document.querySelectorAll('[data-close-modal]').forEach((btn) => {
      btn.addEventListener('click', () => closeFormModal(btn.dataset.closeModal));
    });
    ['create-clash', 'create-hitlist'].forEach((name) => {
      const root = document.getElementById(`modal-${name}`);
      if (!root) return;
      root.addEventListener('click', (e) => {
        if (e.target === root) closeFormModal(name);
      });
    });
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      ['create-clash', 'create-hitlist'].forEach((name) => {
        const root = document.getElementById(`modal-${name}`);
        if (root && !root.classList.contains('hidden')) closeFormModal(name);
      });
    });

    const clashForm = document.getElementById('form-create-clash');
    if (clashForm) clashForm.addEventListener('submit', onSubmitClash);
    const hitForm = document.getElementById('form-create-hitlist');
    if (hitForm) hitForm.addEventListener('submit', onSubmitHitlist);

    const clashFee = document.getElementById('clash-fee');
    if (clashFee) clashFee.addEventListener('input', updateClashPotHint);
  }

  function fillSelect(selectEl, options, { placeholder, selectedId } = {}) {
    if (!selectEl) return;
    const parts = [];
    if (placeholder !== undefined) {
      parts.push(`<option value="">${escapeHtml(placeholder)}</option>`);
    }
    options.forEach((opt) => {
      const sel = String(opt.id) === String(selectedId) ? ' selected' : '';
      parts.push(`<option value="${escapeHtml(opt.id)}"${sel}>${escapeHtml(opt.label)}</option>`);
    });
    selectEl.innerHTML = parts.join('');
  }

  function showFormError(formName, message) {
    const el = document.getElementById(`${formName}-form-error`);
    if (!el) return;
    el.textContent = message || '';
    el.classList.toggle('hidden', !message);
  }

  function setSubmitting(buttonId, isSubmitting, busyLabel) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    btn.disabled = !!isSubmitting;
    const label = btn.querySelector('.submit-label');
    if (!label) return;
    if (isSubmitting) {
      btn.dataset.originalLabel = label.textContent;
      label.textContent = busyLabel || 'Working…';
    } else if (btn.dataset.originalLabel) {
      label.textContent = btn.dataset.originalLabel;
      delete btn.dataset.originalLabel;
    }
  }

  // ── Clash creation flow ───────────────────────────────────────────

  function teamOptions() {
    return (HUB.my_teams || []).map((t) => ({
      id: t.id,
      label: t.tag ? `${t.name} [${t.tag}]` : t.name,
      game_id: t.game_id,
    }));
  }
  function gameOptions() {
    return (HUB.games || []).map((g) => ({
      id: g.id,
      label: g.short_code ? `${g.name} (${g.short_code})` : g.name,
    }));
  }

  function resetClashForm({ opponentId = '', opponentName = '' } = {}) {
    const myTeams = teamOptions();
    fillSelect(document.getElementById('clash-team'), myTeams,
      { placeholder: myTeams.length ? '— Select your team —' : 'No team with authority found' });
    fillSelect(document.getElementById('clash-game'), gameOptions(),
      { placeholder: '— Select game —' });

    const oppSel = document.getElementById('clash-opponent');
    const oppHint = document.getElementById('clash-opponent-hint');
    if (opponentId) {
      const label = opponentName || `Team #${opponentId}`;
      oppSel.innerHTML = `<option value="${escapeHtml(opponentId)}" selected>${escapeHtml(label)}</option>`;
      oppSel.disabled = true;
      if (oppHint) oppHint.textContent = `Pre-filled from ${escapeHtml(label)}.  This is a direct challenge.`;
    } else {
      oppSel.disabled = false;
      oppSel.innerHTML = '<option value="">— Open challenge (any team) —</option>';
      if (oppHint) oppHint.textContent = 'Leave blank to publish as an open challenge any team can accept.';
    }

    document.getElementById('form-create-clash').reset();
    if (opponentId) {
      oppSel.value = String(opponentId);
    }
    document.getElementById('clash-format').value = '3';
    showFormError('clash', '');
    updateClashPotHint();
  }

  function updateClashPotHint() {
    const v = Number(document.getElementById('clash-fee').value || 0);
    const hint = document.getElementById('clash-pot-hint');
    if (hint) hint.textContent = `Pot: ${(v * 2).toLocaleString()} DC (entry × 2)`;
  }

  async function onSubmitClash(e) {
    e.preventDefault();
    showFormError('clash', '');

    const teamSel = document.getElementById('clash-team');
    const oppSel  = document.getElementById('clash-opponent');
    const gameSel = document.getElementById('clash-game');
    const titleEl = document.getElementById('clash-title');
    const feeEl   = document.getElementById('clash-fee');
    const bestOf  = Number(document.getElementById('clash-format').value || 3);

    const teamId = teamSel.value;
    const oppId  = oppSel.value;
    const gameId = gameSel.value;
    const title  = (titleEl.value || '').trim();
    const fee    = Number(feeEl.value || 0);

    [teamSel, oppSel, gameSel, titleEl, feeEl].forEach((el) => el && el.classList.remove('is-invalid'));

    if (!teamId)         { teamSel.classList.add('is-invalid'); return showFormError('clash', 'Select your team.'); }
    if (!gameId)         { gameSel.classList.add('is-invalid'); return showFormError('clash', 'Select a game.'); }
    if (!title)          { titleEl.classList.add('is-invalid'); return showFormError('clash', 'Give the clash a title.'); }
    if (!fee || fee < 1) { feeEl.classList.add('is-invalid');   return showFormError('clash', 'Entry fee must be at least 1 DC.'); }
    if (fee > 1000)      { feeEl.classList.add('is-invalid');   return showFormError('clash', 'Entry fee exceeds the 1,000 DC anti-whale cap.'); }

    const ok = await openConfirm({
      title: 'Issue this Crown Clash?',
      body: 'Your stake locks immediately. The opponent locks their matching stake on accept. Refunded on decline / cancel / expire.',
      lockNote: `This will lock ${fee.toLocaleString()} DC in escrow now.`,
    });
    if (!ok) return;

    const payload = {
      challenger_team_id: Number(teamId),
      challenged_team_id: oppId ? Number(oppId) : null,
      game_id: Number(gameId),
      title: title,
      challenge_type: oppId ? 'DIRECT' : 'OPEN',
      best_of: bestOf,
      entry_fee_dc: fee,
      is_public: true,
    };

    try {
      setSubmitting('clash-submit', true, 'Locking…');
      await jsonFetch(API.challengeCreate, {
        method: 'POST', body: JSON.stringify(payload),
      });
      toast('success', `Crown Clash issued. ${fee.toLocaleString()} DC locked.`);
      closeFormModal('create-clash');
      loaded.clash = false;
      activateTab('clash');
    } catch (err) {
      const code = err && err.body && err.body.code;
      if (code === 'INSUFFICIENT_FUNDS') {
        showFormError('clash', err.body.detail || 'Insufficient DeltaCoins.');
      }
      handleApiError(err);
    } finally {
      setSubmitting('clash-submit', false);
    }
  }

  // ── Hitlist creation flow ─────────────────────────────────────────

  function resetHitlistForm() {
    const myTeams = teamOptions();
    fillSelect(document.getElementById('hitlist-team'), myTeams,
      { placeholder: myTeams.length ? '— Select your team —' : 'No team with authority found' });
    fillSelect(document.getElementById('hitlist-game'), gameOptions(),
      { placeholder: '— Select game —' });
    document.getElementById('form-create-hitlist').reset();
    showFormError('hitlist', '');
  }

  async function onSubmitHitlist(e) {
    e.preventDefault();
    showFormError('hitlist', '');

    const teamSel  = document.getElementById('hitlist-team');
    const gameSel  = document.getElementById('hitlist-game');
    const titleEl  = document.getElementById('hitlist-title');
    const rewardEl = document.getElementById('hitlist-reward');
    const entryEl  = document.getElementById('hitlist-entry');

    const teamId = teamSel.value;
    const gameId = gameSel.value;
    const title  = (titleEl.value || '').trim();
    const reward = Number(rewardEl.value || 0);
    const entry  = Number(entryEl.value || 0);

    [teamSel, gameSel, titleEl, rewardEl, entryEl].forEach((el) => el && el.classList.remove('is-invalid'));

    if (!teamId)         { teamSel.classList.add('is-invalid');  return showFormError('hitlist', 'Select your team.'); }
    if (!gameId)         { gameSel.classList.add('is-invalid');  return showFormError('hitlist', 'Select a game.'); }
    if (!title)          { titleEl.classList.add('is-invalid');  return showFormError('hitlist', 'Give the bounty a headline.'); }
    if (reward < 1)      { rewardEl.classList.add('is-invalid'); return showFormError('hitlist', 'Reward must be at least 1 DC.'); }
    if (entry < 1)       { entryEl.classList.add('is-invalid');  return showFormError('hitlist', 'Challenger entry fee must be at least 1 DC.'); }
    if (entry > 1000)    { entryEl.classList.add('is-invalid');  return showFormError('hitlist', 'Challenger entry fee exceeds the 1,000 DC anti-whale cap.'); }

    const ok = await openConfirm({
      title: 'Post this Hitlist Bounty?',
      body: 'Your reward locks immediately. Each challenger pays the entry fee per attempt. If you beat them, the entry fee transfers to you (5% fee). If they win, they take the reward.',
      lockNote: `This will lock ${reward.toLocaleString()} DC in escrow now.`,
    });
    if (!ok) return;

    const payload = {
      issuer_team_id: Number(teamId),
      game_id: Number(gameId),
      title: title,
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
      await jsonFetch(API.bountyCreate, {
        method: 'POST', body: JSON.stringify(payload),
      });
      toast('success', `Hitlist bounty posted. ${reward.toLocaleString()} DC locked.`);
      closeFormModal('create-hitlist');
      loaded.hitlist = false;
      activateTab('hitlist');
    } catch (err) {
      const code = err && err.body && err.body.code;
      if (code === 'INSUFFICIENT_FUNDS') {
        showFormError('hitlist', err.body.detail || 'Insufficient DeltaCoins.');
      }
      handleApiError(err);
    } finally {
      setSubmitting('hitlist-submit', false);
    }
  }

  // ── URL-param prefill (contextual deep-link) ──────────────────────

  function applyUrlPrefill() {
    let params;
    try { params = new URLSearchParams(window.location.search); }
    catch { return; }

    const challengeTeamId   = params.get('challenge_team_id');
    const challengeTeamName = params.get('challenge_team_name') || '';
    if (challengeTeamId) {
      activateTab('clash');
      openFormModal('create-clash', {
        opponentId: challengeTeamId,
        opponentName: challengeTeamName,
      });
      return;
    }

    const action = (params.get('action') || '').toLowerCase();
    if (action === 'create-clash')   { activateTab('clash');   openFormModal('create-clash'); }
    if (action === 'create-hitlist') { activateTab('hitlist'); openFormModal('create-hitlist'); }
  }

  // ── Loader registry & init ────────────────────────────────────────

  const loaded = { contracts: false, clash: false, hitlist: false, royale: false };
  const LOADERS = {
    contracts: loadContracts,
    clash:     loadClash,
    hitlist:   loadHitlist,
    royale:    loadRoyale,
  };

  function bindEmptyStateCTAs() {
    document.addEventListener('click', (e) => {
      const target = e.target instanceof Element ? e.target.closest('[data-empty-cta]') : null;
      if (!target) return;
      const kind = target.getAttribute('data-empty-cta');
      if (kind && LOADERS[kind]) {
        loaded[kind] = true;
        LOADERS[kind]();
      }
    });
  }

  function init() {
    bindModal();
    bindTabs();
    bindEmptyStateCTAs();
    bindFormModals();
    loaded.contracts = true;
    loadContracts();
    applyUrlPrefill();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
