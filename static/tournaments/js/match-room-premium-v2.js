(function () {
  'use strict';

  const payloadNode = document.getElementById('match-room-payload');
  if (!payloadNode) {
    return;
  }

  let room = {};
  try {
    room = JSON.parse(payloadNode.textContent || '{}');
  } catch (_err) {
    room = {};
  }

  if (!room || !room.match || !room.urls || !room.workflow) {
    return;
  }

  const PHASE_ORDER = ['coin_toss', 'phase1', 'lobby_setup', 'live', 'results', 'completed'];
  const RESULT_FINAL_STATES = new Set(['verified', 'admin_overridden']);
  const RESULT_MISMATCH_STATES = new Set(['mismatch', 'tie_pending_review', 'admin_tie_pending_review']);

  const state = {
    ws: null,
    wsConnected: false,
    reconnectTimer: null,
    syncTimer: null,
    clockTimer: null,
    activeTab: 'chat',
    previewResults: false,
    proxyEnabled: false,
    proxySide: 1,
    chatSeen: new Set(),
    announcementSeen: new Set(),
    uploadedFiles: { 1: null, 2: null },
    toastHost: null,
    tossWinnerRendered: null,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(value) {
    const text = String(value == null ? '' : value);
    return text
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function toInt(value, fallback) {
    const parsed = Number.parseInt(String(value == null ? '' : value), 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function getCsrfToken() {
    const row = document.cookie.split('; ').find((chunk) => chunk.startsWith('csrftoken='));
    return row ? decodeURIComponent(row.slice('csrftoken='.length)) : '';
  }

  function getWorkflow() {
    const wf = room.workflow || {};
    if (!wf.result_submissions || typeof wf.result_submissions !== 'object') {
      wf.result_submissions = { '1': null, '2': null };
    }
    if (!wf.credentials || typeof wf.credentials !== 'object') {
      wf.credentials = {};
    }
    if (!wf.direct_ready || typeof wf.direct_ready !== 'object') {
      wf.direct_ready = { '1': false, '2': false };
    }
    return wf;
  }

  function currentPhase() {
    const wf = getWorkflow();
    const phase = String(wf.phase || 'coin_toss');
    return PHASE_ORDER.includes(phase) ? phase : 'coin_toss';
  }

  function currentMode() {
    const wf = getWorkflow();
    const mode = String(wf.mode || room.game?.phase_mode || 'veto').toLowerCase();
    if (mode === 'draft' || mode === 'direct') {
      return mode;
    }
    return 'veto';
  }

  function isStaffUser() {
    return !!(room.me && room.me.is_staff);
  }

  function isAdminMode() {
    return !!(room.me && room.me.admin_mode);
  }

  function mySide() {
    const side = Number(room.me && room.me.side);
    return side === 1 || side === 2 ? side : null;
  }

  function canSubmitForSide(side) {
    const own = mySide();
    if (own === side) {
      return true;
    }
    if (isStaffUser()) {
      return true;
    }
    return false;
  }

  function resolveActingSide(preferredSide) {
    const preferred = Number(preferredSide);
    if (isStaffUser()) {
      if (state.proxyEnabled) {
        return state.proxySide;
      }
      if (preferred === 1 || preferred === 2) {
        return preferred;
      }
      return 1;
    }

    const mine = mySide();
    if (mine === 1 || mine === 2) {
      return mine;
    }

    if (preferred === 1 || preferred === 2) {
      return preferred;
    }

    return 1;
  }

  function showToast(message, kind) {
    const host = ensureToastHost();
    const row = document.createElement('div');

    const tone = String(kind || 'normal');
    const classes = [
      'px-3.5',
      'py-2',
      'rounded-lg',
      'border',
      'text-xs',
      'font-bold',
      'uppercase',
      'tracking-wider',
      'shadow-xl',
      'backdrop-blur',
      'animate-[fadeIn_0.2s_ease-out]',
    ];

    if (tone === 'error') {
      classes.push('bg-red-500/15', 'text-red-200', 'border-red-400/40');
    } else if (tone === 'ok') {
      classes.push('bg-emerald-500/15', 'text-emerald-200', 'border-emerald-400/40');
    } else {
      classes.push('bg-white/10', 'text-white', 'border-white/15');
    }

    row.className = classes.join(' ');
    row.textContent = String(message || 'Updated');
    host.appendChild(row);

    window.setTimeout(() => {
      row.style.opacity = '0';
      row.style.transform = 'translateY(-4px)';
      row.style.transition = 'all 0.2s ease';
      window.setTimeout(() => {
        row.remove();
      }, 210);
    }, 2100);
  }

  function ensureToastHost() {
    if (state.toastHost) {
      return state.toastHost;
    }

    const host = document.createElement('div');
    host.className = 'fixed top-4 right-4 z-[130] flex flex-col gap-2 pointer-events-none';
    document.body.appendChild(host);
    state.toastHost = host;
    return host;
  }

  function toDisplayTime(iso) {
    if (!iso) {
      return '--:--';
    }

    try {
      const value = new Date(iso);
      if (Number.isNaN(value.getTime())) {
        return '--:--';
      }
      return value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (_err) {
      return '--:--';
    }
  }

  function teamLabel(side) {
    if (side === 1) {
      return room.match?.participant1?.name || 'Team A';
    }
    if (side === 2) {
      return room.match?.participant2?.name || 'Team B';
    }
    return 'Side';
  }

  function initials(name, fallback) {
    const text = String(name || '').trim();
    if (!text) {
      return fallback;
    }

    const parts = text.split(/\s+/).filter(Boolean);
    if (!parts.length) {
      return fallback;
    }

    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }

    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }

  function gameDataKey() {
    const slug = String(room.game?.slug || '').toLowerCase();
    if (!slug) {
      return 'valorant';
    }
    return slug.replaceAll(/[^a-z0-9]/g, '');
  }

  function hashText(text) {
    const safe = String(text || 'map');
    let hash = 0;
    for (let i = 0; i < safe.length; i += 1) {
      hash = ((hash << 5) - hash) + safe.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash);
  }

  function mapGradient(name) {
    const h = hashText(name) % 360;
    const h2 = (h + 45) % 360;
    return `radial-gradient(circle at 18% 18%, hsla(${h}, 90%, 60%, 0.45) 0%, transparent 42%), linear-gradient(140deg, #08080b 0%, hsl(${h2} 45% 13%) 100%)`;
  }

  function currentSelectedMap() {
    const wf = getWorkflow();
    const veto = wf.veto && typeof wf.veto === 'object' ? wf.veto : {};
    const creds = wf.credentials || {};

    const explicit = String(veto.selected_map || creds.map || room.lobby?.map || '').trim();
    if (explicit) {
      return explicit;
    }

    const picks = Array.isArray(veto.picks) ? veto.picks : [];
    if (picks.length) {
      return String(picks[picks.length - 1]);
    }

    return '';
  }

  function renderTheme() {
    const shell = byId('mr-shell');
    if (shell) {
      shell.setAttribute('data-game', gameDataKey());
    }

    const bgLayer = byId('bg-layer');
    if (bgLayer) {
      const mapName = currentSelectedMap() || room.game?.name || 'Arena';
      bgLayer.style.backgroundImage = mapGradient(mapName);
      bgLayer.style.opacity = '0.22';
    }
  }

  function renderHeader() {
    const p1 = room.match?.participant1 || {};
    const p2 = room.match?.participant2 || {};

    const teamAName = byId('team-a-name');
    const teamBName = byId('team-b-name');
    const teamALogo = byId('team-a-logo');
    const teamBLogo = byId('team-b-logo');
    const teamASub = byId('team-a-sub');
    const teamBSub = byId('team-b-sub');
    const teamAReadyName = byId('team-a-ready-name');
    const teamBReadyName = byId('team-b-ready-name');
    const matchFormat = byId('match-format');
    const navMatchId = byId('nav-match-id');
    const navTournament = byId('nav-tournament');

    if (teamAName) {
      teamAName.textContent = p1.name || 'Team A';
    }
    if (teamBName) {
      teamBName.textContent = p2.name || 'Team B';
    }

    if (teamALogo) {
      teamALogo.textContent = initials(p1.name, 'A');
    }
    if (teamBLogo) {
      teamBLogo.textContent = initials(p2.name, 'B');
    }

    if (teamASub) {
      teamASub.textContent = p1.checked_in ? 'Checked in' : 'Pending check-in';
    }
    if (teamBSub) {
      teamBSub.textContent = p2.checked_in ? 'Checked in' : 'Pending check-in';
    }

    if (teamAReadyName) {
      teamAReadyName.textContent = p1.name || 'Team A';
    }
    if (teamBReadyName) {
      teamBReadyName.textContent = p2.name || 'Team B';
    }

    if (matchFormat) {
      matchFormat.textContent = `BO${toInt(room.match?.best_of, 1)}`;
    }

    if (navMatchId) {
      navMatchId.textContent = `Match #${room.match?.id || '--'}`;
    }

    if (navTournament) {
      navTournament.textContent = room.tournament?.name || 'Tournament';
    }

    const coinA = byId('coin-a-face');
    const coinB = byId('coin-b-face');
    if (coinA) {
      coinA.textContent = initials(p1.name, 'A');
    }
    if (coinB) {
      coinB.textContent = initials(p2.name, 'B');
    }

    const resultLogoA = byId('result-logo-a');
    const resultLogoB = byId('result-logo-b');
    const resultNameA = byId('result-name-a');
    const resultNameB = byId('result-name-b');
    if (resultLogoA) {
      resultLogoA.textContent = initials(p1.name, 'A');
    }
    if (resultLogoB) {
      resultLogoB.textContent = initials(p2.name, 'B');
    }
    if (resultNameA) {
      resultNameA.textContent = p1.name || 'Team A';
    }
    if (resultNameB) {
      resultNameB.textContent = p2.name || 'Team B';
    }
  }

  function renderClock() {
    const target = byId('match-clock');
    if (!target) {
      return;
    }

    const phase = currentPhase();
    if (phase === 'live') {
      const startedAt = room.match?.started_at;
      if (startedAt) {
        const startMs = new Date(startedAt).getTime();
        if (Number.isFinite(startMs)) {
          const elapsed = Math.max(0, Math.floor((Date.now() - startMs) / 1000));
          const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
          const ss = String(elapsed % 60).padStart(2, '0');
          target.textContent = `${mm}:${ss}`;
          return;
        }
      }
      target.textContent = 'LIVE';
      return;
    }

    const scheduled = room.match?.scheduled_time;
    if (scheduled) {
      target.textContent = toDisplayTime(scheduled);
      return;
    }

    target.textContent = '--:--';
  }

  function phaseSegment(phase) {
    if (phase === 'coin_toss' || phase === 'phase1') {
      return 1;
    }
    if (phase === 'lobby_setup' || phase === 'live') {
      return 2;
    }
    return 3;
  }

  function applySegmentUI(segment) {
    const dot1 = byId('ph-dot-1');
    const dot2 = byId('ph-dot-2');
    const dot3 = byId('ph-dot-3');
    const wrap2 = byId('ph2-wrap');
    const wrap3 = byId('ph3-wrap');
    const bar1 = byId('ph-bar-1');
    const bar2 = byId('ph-bar-2');

    if (dot1) {
      dot1.classList.remove('phase-dot-active', 'phase-dot-done');
      dot1.classList.add(segment > 1 ? 'phase-dot-done' : 'phase-dot-active');
    }
    if (dot2) {
      dot2.classList.remove('phase-dot-active', 'phase-dot-done');
      dot2.classList.add(segment > 2 ? 'phase-dot-done' : (segment === 2 ? 'phase-dot-active' : ''));
    }
    if (dot3) {
      dot3.classList.remove('phase-dot-active', 'phase-dot-done');
      dot3.classList.add(segment === 3 ? 'phase-dot-active' : '');
    }

    if (wrap2) {
      wrap2.style.opacity = segment >= 2 ? '1' : '0.4';
    }
    if (wrap3) {
      wrap3.style.opacity = segment >= 3 ? '1' : '0.4';
    }

    if (bar1) {
      bar1.style.width = segment >= 2 ? '100%' : '0%';
    }
    if (bar2) {
      bar2.style.width = segment >= 3 ? '100%' : '0%';
    }
  }

  function hidePhaseBlocks() {
    ['ph-discord', 'ph-veto', 'ph-draft', 'ph-direct', 'ph-lobby', 'ph-server', 'ph-result'].forEach((id) => {
      const node = byId(id);
      if (node) {
        node.classList.add('hidden-state');
      }
    });
  }

  function showPhaseBlock(id) {
    const node = byId(id);
    if (node) {
      node.classList.remove('hidden-state');
    }
  }

  function renderPhaseLayout() {
    const phase = currentPhase();
    const mode = currentMode();

    applySegmentUI(phaseSegment(phase));
    hidePhaseBlocks();

    if (phase === 'coin_toss') {
      showPhaseBlock('ph-discord');
      return;
    }

    if (phase === 'phase1') {
      if (mode === 'draft') {
        showPhaseBlock('ph-draft');
      } else if (mode === 'direct') {
        showPhaseBlock('ph-direct');
      } else {
        showPhaseBlock('ph-veto');
      }
      return;
    }

    if (phase === 'lobby_setup') {
      showPhaseBlock('ph-lobby');
      return;
    }

    if (phase === 'live') {
      if (state.previewResults) {
        showPhaseBlock('ph-result');
      } else {
        showPhaseBlock('ph-server');
      }
      return;
    }

    showPhaseBlock('ph-result');
  }

  function canUsePhaseOneAction(expectedSide) {
    const phase = currentPhase();
    if (phase !== 'phase1') {
      return false;
    }

    const side = Number(expectedSide);
    if (side !== 1 && side !== 2) {
      return false;
    }

    if (isStaffUser()) {
      return true;
    }

    return mySide() === side;
  }

  function renderCoinToss() {
    const wf = getWorkflow();
    const coin = wf.coin_toss && typeof wf.coin_toss === 'object' ? wf.coin_toss : {};

    const winnerSide = Number(coin.winner_side);
    const winner = winnerSide === 1 || winnerSide === 2 ? winnerSide : null;

    const coinNode = byId('the-coin');
    const tossResult = byId('toss-result');
    const tossActions = byId('toss-actions');
    const tossWinnerText = byId('toss-winner-text');
    const tossSub = byId('toss-sub');
    const tossBtn = byId('btn-coin-toss');
    const proceedBtn = byId('btn-proceed-after-toss');

    if (tossWinnerText) {
      tossWinnerText.textContent = winner ? `${teamLabel(winner)} won first control.` : 'No toss result yet.';
    }

    if (tossSub) {
      tossSub.textContent = winner
        ? 'Turn order was resolved and synced to all match room viewers.'
        : 'Resolve first control priority for match setup.';
    }

    if (tossBtn) {
      tossBtn.disabled = !(currentPhase() === 'coin_toss' && (isStaffUser() || mySide() !== null));
    }

    const showResult = winner !== null;
    if (tossResult) {
      tossResult.classList.toggle('hidden-state', !showResult);
    }
    if (tossActions) {
      tossActions.classList.toggle('hidden-state', showResult);
    }

    if (proceedBtn) {
      proceedBtn.classList.toggle('hidden-state', !isAdminMode());
      proceedBtn.disabled = !isAdminMode();
    }

    if (coinNode && winner && state.tossWinnerRendered !== winner) {
      coinNode.classList.remove('flip');
      // force a layout pass so flip can restart cleanly.
      // eslint-disable-next-line no-unused-expressions
      coinNode.offsetWidth;
      coinNode.classList.add('flip');
      state.tossWinnerRendered = winner;
    }
  }

  function reconstructStepLog(sequence, bans, picks) {
    const rows = [];
    let banIndex = 0;
    let pickIndex = 0;

    const steps = Array.isArray(sequence) ? sequence : [];
    for (let i = 0; i < steps.length; i += 1) {
      const step = steps[i] || {};
      const action = String(step.action || 'ban').toLowerCase();
      const side = Number(step.side || 1) === 2 ? 2 : 1;

      if (action === 'pick') {
        const item = picks[pickIndex];
        if (!item) {
          continue;
        }
        pickIndex += 1;
        rows.push({ side, action: 'picked', item });
      } else {
        const item = bans[banIndex];
        if (!item) {
          continue;
        }
        banIndex += 1;
        rows.push({ side, action: 'banned', item });
      }
    }

    return rows;
  }

  function renderVeto() {
    const wf = getWorkflow();
    const veto = wf.veto && typeof wf.veto === 'object' ? wf.veto : {};

    const sequence = Array.isArray(veto.sequence) ? veto.sequence : [];
    const step = toInt(veto.step, 0);
    const nextStep = sequence[step] || null;

    const expectedSide = Number(nextStep && nextStep.side) || null;
    const expectedAction = String(nextStep && nextStep.action || 'ban').toLowerCase();

    const title = byId('veto-title');
    const instr = byId('veto-instr');
    const timer = byId('veto-timer');
    if (title) {
      title.textContent = 'Map Veto';
    }
    if (instr) {
      if (!nextStep) {
        instr.textContent = 'Veto completed. Locking map for live lobby.';
      } else {
        instr.textContent = `${teamLabel(expectedSide)} to ${expectedAction.toUpperCase()} next.`;
      }
    }
    if (timer) {
      timer.textContent = nextStep ? `${step + 1}/${sequence.length}` : 'DONE';
    }

    const bans = Array.isArray(veto.bans) ? veto.bans.slice() : [];
    const picks = Array.isArray(veto.picks) ? veto.picks.slice() : [];
    const selectedMap = String(veto.selected_map || '').trim();

    const pool = Array.isArray(veto.pool) && veto.pool.length
      ? veto.pool
      : (Array.isArray(room.game?.map_pool) ? room.game.map_pool : []);

    const grid = byId('map-grid');
    if (grid) {
      grid.innerHTML = '';
      const active = canUsePhaseOneAction(expectedSide);
      const used = new Set([...bans, ...picks]);

      pool.forEach((mapNameRaw) => {
        const mapName = String(mapNameRaw || '').trim();
        if (!mapName) {
          return;
        }

        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'map-card';

        const label = document.createElement('div');
        label.className = 'absolute left-3 bottom-2.5 z-[2] text-xs font-bold text-white';
        label.textContent = mapName;

        const bg = document.createElement('div');
        bg.className = 'map-bg';
        bg.style.background = mapGradient(mapName);

        const badge = document.createElement('span');
        badge.className = 'sb';

        if (bans.includes(mapName)) {
          card.classList.add('banned');
          badge.textContent = 'BAN';
        } else if (picks.includes(mapName) || selectedMap === mapName) {
          card.classList.add('picked');
          badge.textContent = 'PICK';
        } else if (!active || used.has(mapName) || !nextStep) {
          card.disabled = true;
        } else {
          card.addEventListener('click', () => {
            submitWorkflow('veto_action', {
              item: mapName,
              acting_side: resolveActingSide(expectedSide),
            });
          });
        }

        card.appendChild(bg);
        card.appendChild(label);
        card.appendChild(badge);
        grid.appendChild(card);
      });
    }

    const log = byId('veto-log');
    if (log) {
      log.innerHTML = '';
      const rows = reconstructStepLog(sequence, bans, picks);
      rows.forEach((entry) => {
        const li = document.createElement('li');
        li.innerHTML = `<span class="text-white">${esc(teamLabel(entry.side))}</span> ${esc(entry.action)} <span class="ac">${esc(entry.item)}</span>`;
        log.appendChild(li);
      });

      if (selectedMap) {
        const final = document.createElement('li');
        final.className = 'text-emerald-300';
        final.textContent = `Selected map: ${selectedMap}`;
        log.appendChild(final);
      }

      if (!rows.length && !selectedMap) {
        const pending = document.createElement('li');
        pending.className = 'text-gray-500';
        pending.textContent = 'No veto actions submitted yet.';
        log.appendChild(pending);
      }
    }
  }

  function renderDraft() {
    const wf = getWorkflow();
    const draft = wf.draft && typeof wf.draft === 'object' ? wf.draft : {};

    const sequence = Array.isArray(draft.sequence) ? draft.sequence : [];
    const step = toInt(draft.step, 0);
    const nextStep = sequence[step] || null;
    const expectedSide = Number(nextStep && nextStep.side) || null;
    const expectedAction = String(nextStep && nextStep.action || 'ban').toLowerCase();

    const instr = byId('draft-instr');
    if (instr) {
      if (!nextStep) {
        instr.textContent = 'Draft completed. Transitioning to lobby setup.';
      } else {
        instr.textContent = `${teamLabel(expectedSide)} to ${expectedAction.toUpperCase()} next.`;
      }
    }

    const draftStep = byId('draft-step');
    if (draftStep) {
      draftStep.textContent = `${Math.min(step, sequence.length)}/${sequence.length}`;
    }

    const bans = Array.isArray(draft.bans) ? draft.bans.slice() : [];
    const picksObj = draft.picks && typeof draft.picks === 'object' ? draft.picks : {};
    const picksA = Array.isArray(picksObj['1']) ? picksObj['1'].slice() : [];
    const picksB = Array.isArray(picksObj['2']) ? picksObj['2'].slice() : [];
    const used = new Set([...bans, ...picksA, ...picksB]);

    const heroPool = Array.isArray(draft.pool) && draft.pool.length
      ? draft.pool
      : (Array.isArray(room.game?.hero_pool) ? room.game.hero_pool : []);

    const heroGrid = byId('hero-grid');
    if (heroGrid) {
      heroGrid.innerHTML = '';
      const active = canUsePhaseOneAction(expectedSide);

      heroPool.forEach((heroRaw) => {
        const heroName = String(heroRaw || '').trim();
        if (!heroName) {
          return;
        }

        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'hero-card';
        card.title = heroName;
        card.textContent = heroName;

        if (bans.includes(heroName)) {
          card.classList.add('hban');
        } else if (picksA.includes(heroName)) {
          card.classList.add('ha');
        } else if (picksB.includes(heroName)) {
          card.classList.add('hb');
        } else if (!nextStep || !active || used.has(heroName)) {
          card.disabled = true;
        } else {
          card.addEventListener('click', () => {
            submitWorkflow('draft_action', {
              item: heroName,
              acting_side: resolveActingSide(expectedSide),
            });
          });
        }

        heroGrid.appendChild(card);
      });
    }

    const picksHostA = byId('picks-a');
    if (picksHostA) {
      picksHostA.innerHTML = picksA.length
        ? picksA.map((name) => `<span class="px-2 py-0.5 rounded text-[10px] ac ac-bg">${esc(name)}</span>`).join('')
        : '<span class="text-[10px] text-gray-500">No picks yet.</span>';
    }

    const picksHostB = byId('picks-b');
    if (picksHostB) {
      picksHostB.innerHTML = picksB.length
        ? picksB.map((name) => `<span class="px-2 py-0.5 rounded text-[10px] text-red-300 bg-red-500/15">${esc(name)}</span>`).join('')
        : '<span class="text-[10px] text-gray-500">No picks yet.</span>';
    }

    const bansDisplay = byId('bans-display');
    if (bansDisplay) {
      bansDisplay.innerHTML = bans.length
        ? bans.map((name) => `<span class="px-2 py-0.5 rounded text-[10px] text-gray-300 bg-white/5 line-through">${esc(name)}</span>`).join('')
        : '<span class="text-[10px] text-gray-500">No bans yet.</span>';
    }

    const log = byId('draft-log');
    if (log) {
      log.innerHTML = '';
      const rows = [];
      let banIndex = 0;
      let pickAIndex = 0;
      let pickBIndex = 0;

      sequence.forEach((stepDef) => {
        const action = String(stepDef?.action || 'ban').toLowerCase();
        const side = Number(stepDef?.side || 1) === 2 ? 2 : 1;

        if (action === 'pick') {
          const token = side === 1 ? picksA[pickAIndex] : picksB[pickBIndex];
          if (!token) {
            return;
          }
          if (side === 1) {
            pickAIndex += 1;
          } else {
            pickBIndex += 1;
          }
          rows.push(`${teamLabel(side)} picked ${token}`);
        } else {
          const token = bans[banIndex];
          if (!token) {
            return;
          }
          banIndex += 1;
          rows.push(`${teamLabel(side)} banned ${token}`);
        }
      });

      if (!rows.length) {
        const li = document.createElement('li');
        li.className = 'text-gray-500';
        li.textContent = 'No draft actions submitted yet.';
        log.appendChild(li);
      } else {
        rows.forEach((line) => {
          const li = document.createElement('li');
          li.textContent = line;
          log.appendChild(li);
        });
      }
    }
  }

  function renderDirectReady() {
    const wf = getWorkflow();
    const ready = wf.direct_ready && typeof wf.direct_ready === 'object' ? wf.direct_ready : { '1': false, '2': false };

    const r1 = !!ready['1'];
    const r2 = !!ready['2'];

    const boxA = byId('direct-ready-a');
    const boxB = byId('direct-ready-b');

    function applyReadyCard(node, ok, accent) {
      if (!node) {
        return;
      }
      const iconWrap = node.querySelector('div');
      const textRows = node.querySelectorAll('p');
      if (iconWrap) {
        iconWrap.textContent = ok ? 'OK' : '?';
        if (ok) {
          iconWrap.style.background = 'rgba(0,255,102,0.18)';
          iconWrap.style.borderColor = 'rgba(0,255,102,0.45)';
          iconWrap.style.color = '#00ff66';
        } else {
          iconWrap.style.background = accent;
          iconWrap.style.borderColor = '';
          iconWrap.style.color = '';
        }
      }
      if (textRows && textRows.length > 1) {
        textRows[1].textContent = ok ? 'Ready' : 'Waiting';
        textRows[1].className = `text-[10px] font-mono uppercase tracking-widest ${ok ? 'text-emerald-300' : 'text-gray-500'}`;
      }
    }

    applyReadyCard(boxA, r1, 'rgba(var(--ar),var(--ag),var(--ab),0.15)');
    applyReadyCard(boxB, r2, 'rgba(255,255,255,0.05)');

    const btn = byId('btn-direct-ready');
    const actingSide = resolveActingSide(mySide());
    if (btn) {
      btn.textContent = `Mark ${teamLabel(actingSide)} Ready`;
      const already = actingSide === 1 ? r1 : r2;
      btn.disabled = currentPhase() !== 'phase1' || already || (r1 && r2);
    }
  }

  function credentialSchema() {
    const base = [
      { key: 'lobby_code', label: 'Lobby Code', placeholder: 'Room code' },
      { key: 'password', label: 'Password', placeholder: 'Lobby password' },
      { key: 'map', label: 'Map', placeholder: 'Map name' },
      { key: 'server', label: 'Server', placeholder: 'Server / Region' },
      { key: 'game_mode', label: 'Game Mode', placeholder: 'Mode / Ruleset' },
      { key: 'notes', label: 'Extra Notes', placeholder: 'Optional notes', multiline: true },
    ];

    const mode = currentMode();
    if (mode === 'direct') {
      return base.filter((row) => row.key !== 'map');
    }

    return base;
  }

  function renderCredentialForm(canEdit) {
    const form = byId('cred-form');
    if (!form) {
      return;
    }

    const creds = getWorkflow().credentials || {};
    const fields = credentialSchema();

    form.innerHTML = fields.map((field) => {
      const value = String(creds[field.key] || room.lobby?.[field.key] || '');
      if (field.multiline) {
        return `
          <div>
            <label class="section-label">${esc(field.label)}</label>
            <textarea data-cred-key="${esc(field.key)}" class="compact-input" rows="3" placeholder="${esc(field.placeholder || '')}" ${canEdit ? '' : 'disabled'}>${esc(value)}</textarea>
          </div>
        `;
      }

      return `
        <div>
          <label class="section-label">${esc(field.label)}</label>
          <input data-cred-key="${esc(field.key)}" class="compact-input" value="${esc(value)}" placeholder="${esc(field.placeholder || '')}" ${canEdit ? '' : 'disabled'}>
        </div>
      `;
    }).join('');
  }

  function renderLobbyPhase() {
    const hostView = byId('lobby-host-view');
    const guestView = byId('lobby-guest-view');
    const hostSteps = byId('host-steps');

    const canEdit = !!(room.me && room.me.can_edit_credentials);

    if (hostView) {
      hostView.classList.toggle('hidden-state', !canEdit);
    }
    if (guestView) {
      guestView.classList.toggle('hidden-state', canEdit);
    }

    if (hostSteps) {
      const mode = currentMode();
      const rows = [];
      rows.push('1. Create a private lobby with tournament settings.');
      if (mode === 'veto') {
        rows.push('2. Confirm selected map and server region.');
      } else if (mode === 'draft') {
        rows.push('2. Lock drafted heroes and apply ruleset.');
      } else {
        rows.push('2. Verify both sides are marked ready.');
      }
      rows.push('3. Share lobby code and password with both teams.');
      rows.push('4. Start live phase after confirmations in chat.');
      hostSteps.innerHTML = rows.map((line) => `<div>${esc(line)}</div>`).join('');
    }

    renderCredentialForm(canEdit);

    const broadcastBtn = byId('btn-broadcast-creds');
    if (broadcastBtn) {
      broadcastBtn.disabled = !canEdit;
    }

    const startLiveBtn = byId('btn-start-live');
    if (startLiveBtn) {
      startLiveBtn.disabled = !(isStaffUser() || mySide() === 1 || mySide() === 2);
    }
  }

  function renderServerPhase() {
    const wf = getWorkflow();
    const creds = wf.credentials || {};
    const selectedMap = currentSelectedMap();

    const mapName = byId('server-map-name');
    if (mapName) {
      if (selectedMap) {
        mapName.textContent = selectedMap;
      } else {
        mapName.textContent = currentMode() === 'direct' ? 'Direct Match' : 'Live Lobby';
      }
    }

    const steps = byId('server-steps');
    if (steps) {
      const rows = [
        '1. Join lobby and verify team names.',
        '2. Play match using tournament settings only.',
        '3. On completion, both captains submit score proof.',
      ];
      steps.innerHTML = rows.map((line) => `<div>${esc(line)}</div>`).join('');
    }

    const credsView = byId('server-creds');
    if (credsView) {
      const keys = [
        ['Code', creds.lobby_code || room.lobby?.lobby_code],
        ['Password', creds.password || room.lobby?.password],
        ['Map', creds.map || room.lobby?.map],
        ['Server', creds.server || room.lobby?.server],
        ['Mode', creds.game_mode || room.lobby?.game_mode],
      ];

      const rows = keys.filter((entry) => String(entry[1] || '').trim());
      if (!rows.length) {
        credsView.innerHTML = '<p class="text-[10px] text-gray-500">Credentials will appear once host broadcasts lobby data.</p>';
      } else {
        credsView.innerHTML = rows.map((entry) => {
          return `
            <div class="flex items-center justify-between gap-2 border border-white/8 rounded-lg px-3 py-2 bg-white/5">
              <span class="text-[10px] uppercase tracking-widest text-gray-500 font-bold">${esc(entry[0])}</span>
              <span class="text-xs font-mono text-white text-right break-all">${esc(entry[1])}</span>
            </div>
          `;
        }).join('');
      }
    }

    const toResults = byId('btn-to-results');
    if (toResults) {
      if (room.me?.can_force_phase) {
        toResults.textContent = 'Force Phase -> Results';
        toResults.disabled = false;
      } else {
        toResults.textContent = 'Open Result Submission';
        toResults.disabled = false;
      }
    }
  }

  function statusForSubmission(side, sub, resultStatus) {
    if (!sub) {
      return { cls: 'pending', text: 'Pending' };
    }

    const subStatus = String(sub.status || '').toLowerCase();
    if (RESULT_MISMATCH_STATES.has(resultStatus) || subStatus === 'disputed') {
      return { cls: 'mismatch', text: 'Mismatch' };
    }

    if (subStatus === 'finalized' || subStatus === 'confirmed' || RESULT_FINAL_STATES.has(resultStatus)) {
      return { cls: 'done', text: 'Verified' };
    }

    if (subStatus === 'pending') {
      return { cls: 'done', text: 'Submitted' };
    }

    if (subStatus === 'rejected') {
      return { cls: 'mismatch', text: 'Rejected' };
    }

    return { cls: 'done', text: 'Submitted' };
  }

  function populateExtraResultFields(side, submission) {
    const suffix = side === 1 ? 'a' : 'b';
    const host = byId(`extra-fields-${suffix}`);
    if (!host) {
      return;
    }

    const note = String(submission?.note || '');
    const evidenceUrl = String(submission?.evidence_url || submission?.proof_screenshot_url || '');

    host.innerHTML = `
      <div>
        <p class="section-label mb-1">Evidence URL (optional)</p>
        <input id="evidence-url-${suffix}" type="text" class="compact-input" value="${esc(evidenceUrl)}" placeholder="https://...">
      </div>
      <div>
        <p class="section-label mb-1">Notes (optional)</p>
        <textarea id="note-${suffix}" rows="2" class="compact-input" placeholder="Round details, overtime, penalties...">${esc(note)}</textarea>
      </div>
    `;
  }

  function renderUploadZone(side, submission) {
    const suffix = side === 1 ? 'a' : 'b';
    const zone = byId(`upload-${suffix}`);
    if (!zone) {
      return;
    }

    const file = state.uploadedFiles[side];
    const existing = String(submission?.proof_screenshot_url || '');

    zone.classList.remove('done');
    if (file) {
      zone.classList.add('done');
      zone.innerHTML = `
        <i data-lucide="image" class="w-5 h-5 mx-auto text-emerald-300 mb-1"></i>
        <p class="text-xs font-bold text-emerald-200">${esc(file.name)}</p>
        <p class="text-[9px] text-emerald-400 mt-0.5">Selected for upload</p>
      `;
      return;
    }

    if (existing) {
      zone.classList.add('done');
      zone.innerHTML = `
        <i data-lucide="image" class="w-5 h-5 mx-auto text-emerald-300 mb-1"></i>
        <p class="text-xs font-bold text-emerald-200">Proof Uploaded</p>
        <a href="${esc(existing)}" target="_blank" rel="noopener noreferrer" class="text-[9px] text-emerald-300 mt-0.5 underline">View current proof</a>
      `;
      return;
    }

    zone.innerHTML = `
      <i data-lucide="image-plus" class="w-5 h-5 mx-auto text-gray-500 mb-1"></i>
      <p class="text-xs font-bold text-gray-400">Upload Screenshot / Proof</p>
      <p class="text-[9px] text-gray-600 mt-0.5">PNG or JPG, up to 10MB</p>
    `;
  }

  function renderResultPhase() {
    const wf = getWorkflow();
    const submissions = wf.result_submissions || { '1': null, '2': null };
    const subA = submissions['1'] && typeof submissions['1'] === 'object' ? submissions['1'] : null;
    const subB = submissions['2'] && typeof submissions['2'] === 'object' ? submissions['2'] : null;

    const resultStatus = String(wf.result_status || 'pending');
    const finalResult = wf.final_result && typeof wf.final_result === 'object' ? wf.final_result : null;

    const scoreA = byId('score-a');
    const scoreAOpp = byId('score-a-opp');
    const scoreB = byId('score-b');
    const scoreBOpp = byId('score-b-opp');

    if (scoreA) {
      scoreA.value = subA?.score_for != null ? String(subA.score_for) : '';
    }
    if (scoreAOpp) {
      scoreAOpp.value = subA?.score_against != null ? String(subA.score_against) : '';
    }
    if (scoreB) {
      scoreB.value = subB?.score_for != null ? String(subB.score_for) : '';
    }
    if (scoreBOpp) {
      scoreBOpp.value = subB?.score_against != null ? String(subB.score_against) : '';
    }

    populateExtraResultFields(1, subA);
    populateExtraResultFields(2, subB);

    renderUploadZone(1, subA);
    renderUploadZone(2, subB);

    const statA = statusForSubmission(1, subA, resultStatus);
    const statB = statusForSubmission(2, subB, resultStatus);

    const statusA = byId('sub-status-a');
    const statusB = byId('sub-status-b');
    if (statusA) {
      statusA.className = `sub-status ${statA.cls}`;
      statusA.innerHTML = `<span>●</span>${esc(statA.text)}`;
    }
    if (statusB) {
      statusB.className = `sub-status ${statB.cls}`;
      statusB.innerHTML = `<span>●</span>${esc(statB.text)}`;
    }

    const cardA = byId('result-card-a');
    const cardB = byId('result-card-b');
    if (cardA) {
      cardA.classList.toggle('submitted-ok', !!subA);
    }
    if (cardB) {
      cardB.classList.toggle('submitted-ok', !!subB);
    }

    const canA = canSubmitForSide(1);
    const canB = canSubmitForSide(2);
    const btnA = byId('submit-btn-a');
    const btnB = byId('submit-btn-b');
    if (btnA) {
      btnA.disabled = !canA;
    }
    if (btnB) {
      btnB.disabled = !canB;
    }

    [
      ['score-a', canA],
      ['score-a-opp', canA],
      ['evidence-url-a', canA],
      ['note-a', canA],
      ['score-b', canB],
      ['score-b-opp', canB],
      ['evidence-url-b', canB],
      ['note-b', canB],
    ].forEach((entry) => {
      const node = byId(entry[0]);
      if (node) {
        node.disabled = !entry[1];
      }
    });

    const verify = byId('result-verify');
    const verifyText = byId('verify-status-text');
    const success = byId('result-success');
    const finalScore = byId('final-score-display');

    if (success) {
      success.classList.add('hidden-state');
    }
    if (verify) {
      verify.classList.add('hidden-state');
    }

    if (RESULT_FINAL_STATES.has(resultStatus) || currentPhase() === 'completed') {
      if (success) {
        success.classList.remove('hidden-state');
      }
      if (finalScore) {
        const p1 = finalResult?.participant1_score != null ? finalResult.participant1_score : room.match?.participant1_score;
        const p2 = finalResult?.participant2_score != null ? finalResult.participant2_score : room.match?.participant2_score;
        finalScore.innerHTML = `<span>${esc(teamLabel(1))}</span><span>${esc(p1 ?? 0)} - ${esc(p2 ?? 0)}</span><span>${esc(teamLabel(2))}</span>`;
      }
    } else if (subA || subB) {
      if (verify) {
        verify.classList.remove('hidden-state');
      }
      if (verifyText) {
        if (RESULT_MISMATCH_STATES.has(resultStatus)) {
          verifyText.textContent = 'Score mismatch detected. Staff review or admin override required.';
        } else if (subA && !subB) {
          verifyText.textContent = `${teamLabel(1)} submitted. Waiting for ${teamLabel(2)}.`;
        } else if (!subA && subB) {
          verifyText.textContent = `${teamLabel(2)} submitted. Waiting for ${teamLabel(1)}.`;
        } else {
          verifyText.textContent = 'Both submissions received. Verifying score agreement.';
        }
      }
    }
  }

  function adminCapability() {
    return !!(
      room.me?.can_force_phase
      || room.me?.can_override_result
      || room.me?.can_broadcast_system
    );
  }

  function setTab(tab) {
    const target = ['chat', 'intel', 'voice', 'admin'].includes(tab) ? tab : 'chat';

    if (target === 'admin' && !adminCapability()) {
      state.activeTab = 'chat';
    } else {
      state.activeTab = target;
    }

    renderTabs();
  }

  function renderTabs() {
    const hasAdmin = adminCapability();

    const map = {
      chat: ['tab-chat-btn', 'view-chat'],
      intel: ['tab-intel-btn', 'view-intel'],
      voice: ['tab-voice-btn', 'view-voice'],
      admin: ['tab-admin-btn', 'view-admin'],
    };

    if (!hasAdmin && state.activeTab === 'admin') {
      state.activeTab = 'chat';
    }

    Object.keys(map).forEach((key) => {
      const btn = byId(map[key][0]);
      const view = byId(map[key][1]);
      if (!btn || !view) {
        return;
      }

      if (key === 'admin') {
        btn.classList.toggle('hidden-state', !hasAdmin);
      }

      const active = state.activeTab === key;
      view.classList.toggle('hidden-state', !active);

      btn.classList.toggle('text-white', active && key !== 'admin');
      btn.classList.toggle('ac', active && key === 'chat');
      btn.classList.toggle('text-gray-500', !active && key !== 'admin');
      btn.classList.toggle('text-amber-200', active && key === 'admin');

      if (active) {
        btn.style.borderBottomColor = key === 'admin' ? 'rgba(255,184,0,0.85)' : 'var(--ac)';
      } else {
        btn.style.borderBottomColor = 'transparent';
      }
    });

    renderAdminPanel();
  }

  function intelRow(label, value, tone) {
    let accent = 'text-gray-300';
    if (tone === 'ok') accent = 'text-emerald-300';
    if (tone === 'warn') accent = 'text-amber-300';
    return `<div class="flex items-center justify-between border border-white/6 rounded-lg px-3 py-2 bg-white/3"><span class="text-[10px] uppercase tracking-widest text-gray-500 font-bold">${esc(label)}</span><span class="text-[10px] font-mono ${accent}">${esc(value)}</span></div>`;
  }

  function renderIntelPanel() {
    const p1 = room.match?.participant1 || {};
    const p2 = room.match?.participant2 || {};

    const intelA = byId('intel-a');
    const intelB = byId('intel-b');

    if (intelA) {
      const rows = [
        intelRow('Name', p1.name || 'Team A'),
        intelRow('Check-in', p1.checked_in ? 'Checked In' : 'Pending', p1.checked_in ? 'ok' : 'warn'),
        intelRow('Score', String(room.match?.participant1_score ?? 0)),
        intelRow('Role', mySide() === 1 ? 'Your Side' : 'Opponent Side'),
      ];
      intelA.innerHTML = rows.join('');
    }

    if (intelB) {
      const rows = [
        intelRow('Name', p2.name || 'Team B'),
        intelRow('Check-in', p2.checked_in ? 'Checked In' : 'Pending', p2.checked_in ? 'ok' : 'warn'),
        intelRow('Score', String(room.match?.participant2_score ?? 0)),
        intelRow('Role', mySide() === 2 ? 'Your Side' : 'Opponent Side'),
      ];
      intelB.innerHTML = rows.join('');
    }

    const orgName = byId('org-name');
    if (orgName) {
      orgName.textContent = room.tournament?.name || 'Tournament Operations';
    }

    const rules = byId('match-rules');
    if (rules) {
      const rows = [];
      rows.push(`Format: BO${toInt(room.match?.best_of, 1)}`);

      const mode = currentMode();
      if (mode === 'veto') {
        rows.push('Phase One: Map veto from tournament-configured pool.');
      } else if (mode === 'draft') {
        rows.push('Phase One: Hero draft with server-side turn order.');
      } else {
        rows.push('Phase One: Direct ready check from both sides.');
      }

      rows.push('All actions are synced in realtime over match websocket.');
      rows.push('Result submissions require both sides for auto-verification.');

      rules.innerHTML = rows.map((line) => `<div>${esc(line)}</div>`).join('');
    }
  }

  function renderProxyControls() {
    const enabled = isStaffUser();

    const activateBtn = byId('btn-activate-proxy');
    const banner = byId('proxy-banner');
    const proxyA = byId('proxy-btn-a');
    const proxyB = byId('proxy-btn-b');

    if (activateBtn) {
      activateBtn.classList.toggle('hidden-state', !enabled);
      activateBtn.textContent = state.proxyEnabled ? 'Disable Proxy' : 'Proxy Mode';
    }

    if (banner) {
      banner.classList.toggle('hidden-state', !(enabled && state.proxyEnabled));
    }

    if (proxyA) {
      proxyA.classList.toggle('active-a', state.proxyEnabled && state.proxySide === 1);
      proxyA.classList.toggle('inactive', !(state.proxyEnabled && state.proxySide === 1));
    }

    if (proxyB) {
      proxyB.classList.toggle('active-b', state.proxyEnabled && state.proxySide === 2);
      proxyB.classList.toggle('inactive', !(state.proxyEnabled && state.proxySide === 2));
    }
  }

  function renderAdminPanel() {
    const adminView = byId('view-admin');
    if (!adminView) {
      return;
    }

    const canForce = !!room.me?.can_force_phase;
    const canOverride = !!room.me?.can_override_result;
    const canBroadcast = !!room.me?.can_broadcast_system;

    const btnNext = byId('btn-admin-next-phase');
    const btnOverride = byId('btn-admin-override');
    const btnApply = byId('btn-admin-apply-score');
    const btnMsg = byId('btn-admin-send-msg');

    if (btnNext) {
      btnNext.disabled = !canForce;
    }
    if (btnOverride) {
      btnOverride.disabled = !canOverride;
    }
    if (btnApply) {
      btnApply.disabled = !canOverride;
    }
    if (btnMsg) {
      btnMsg.disabled = !canBroadcast;
    }

    const credsView = byId('admin-creds-view');
    if (credsView) {
      const wf = getWorkflow();
      const creds = wf.credentials || {};
      const rows = [
        ['Code', creds.lobby_code || room.lobby?.lobby_code],
        ['Password', creds.password || room.lobby?.password],
        ['Map', creds.map || room.lobby?.map],
        ['Server', creds.server || room.lobby?.server],
        ['Mode', creds.game_mode || room.lobby?.game_mode],
      ];

      const validRows = rows.filter((row) => String(row[1] || '').trim());
      if (!validRows.length) {
        credsView.innerHTML = '<p class="section-label mb-2">Lobby Credentials (All Teams)</p><p class="text-[9px] text-gray-500">No credentials published yet.</p>';
      } else {
        credsView.innerHTML = `<p class="section-label mb-2">Lobby Credentials (All Teams)</p>${validRows.map((row) => {
          return `<div class="flex items-center justify-between text-[10px] border border-white/7 rounded px-2 py-1.5 bg-white/5 mb-1"><span class="text-gray-500 uppercase tracking-widest">${esc(row[0])}</span><span class="text-white font-mono">${esc(row[1])}</span></div>`;
        }).join('')}`;
      }
    }
  }

  function appendChatMessage(data, mode) {
    const win = byId('chat-window');
    if (!win || !data) {
      return;
    }

    const messageId = String(data.message_id || `${data.username || 'system'}:${data.timestamp || nowIso()}:${data.text || ''}`);
    if (state.chatSeen.has(messageId)) {
      return;
    }
    state.chatSeen.add(messageId);

    const wrap = document.createElement('div');
    const mine = mode === 'mine';
    const system = mode === 'system';

    wrap.className = `flex ${mine ? 'justify-end' : 'justify-start'}`;

    const bubble = document.createElement('div');
    bubble.className = system
      ? 'max-w-[92%] rounded-xl border border-amber-400/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100'
      : mine
        ? 'max-w-[92%] rounded-xl border border-cyan-300/30 bg-cyan-500/12 px-3 py-2 text-xs text-cyan-50'
        : 'max-w-[92%] rounded-xl border border-white/10 bg-white/6 px-3 py-2 text-xs text-gray-100';

    const who = system
      ? 'System'
      : `${data.username || 'User'}${data.side ? ` (${teamLabel(Number(data.side))})` : ''}${data.is_staff ? ' [Staff]' : ''}`;

    const ts = toDisplayTime(data.timestamp);

    bubble.innerHTML = `
      <div class="flex items-center justify-between gap-2 mb-1">
        <span class="uppercase tracking-widest text-[9px] ${system ? 'text-amber-300' : mine ? 'text-cyan-300' : 'text-gray-400'} font-bold">${esc(who)}</span>
        <span class="text-[9px] text-gray-500 font-mono">${esc(ts)}</span>
      </div>
      <div class="leading-relaxed">${esc(data.text || '')}</div>
    `;

    wrap.appendChild(bubble);
    win.appendChild(wrap);
    win.scrollTop = win.scrollHeight;
  }

  function renderAnnouncements() {
    const list = Array.isArray(room.announcements) ? room.announcements : [];
    list.forEach((item) => {
      if (!item || typeof item !== 'object') {
        return;
      }
      const key = `${item.at || ''}:${item.message || ''}`;
      if (state.announcementSeen.has(key)) {
        return;
      }
      state.announcementSeen.add(key);
      appendChatMessage({
        message_id: `announcement:${key}`,
        username: 'System',
        text: String(item.message || '').trim(),
        timestamp: item.at || nowIso(),
      }, 'system');
    });
  }

  async function submitWorkflow(action, payload, options) {
    const opts = options || {};
    const body = Object.assign({ action }, payload || {});

    try {
      let response;
      if (opts.multipart) {
        const fd = new FormData();
        Object.keys(body).forEach((key) => {
          const value = body[key];
          if (value == null || value === '') {
            return;
          }
          fd.append(key, value);
        });

        if (opts.file) {
          fd.append('evidence', opts.file);
        }

        response = await fetch(room.urls.workflow, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRFToken': getCsrfToken(),
          },
          body: fd,
        });
      } else {
        response = await fetch(room.urls.workflow, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
          },
          body: JSON.stringify(body),
        });
      }

      const data = await response.json();
      if (!response.ok || !data.success) {
        showToast(data.error || 'Action failed', 'error');
        return false;
      }

      room = data.room || room;
      if (action === 'submit_result') {
        const acting = Number(payload.acting_side);
        if (acting === 1 || acting === 2) {
          state.uploadedFiles[acting] = null;
        }
      }

      if (data.message) {
        showToast(data.message, 'ok');
      }
      if (action === 'submit_result') {
        state.previewResults = false;
      }

      renderAll();
      return true;
    } catch (_err) {
      showToast('Network error while updating workflow.', 'error');
      return false;
    }
  }

  async function syncRoom() {
    try {
      const response = await fetch(room.urls.workflow, {
        method: 'GET',
        credentials: 'same-origin',
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        return;
      }

      room = data.room || room;
      renderAll();
    } catch (_err) {
      // silent polling fallback
    }
  }

  async function submitDispute() {
    const reason = String(byId('dispute-reason')?.value || '').trim();
    const description = String(byId('dispute-description')?.value || '').trim();
    const evidenceUrl = String(byId('dispute-evidence-url')?.value || '').trim();

    if (!reason || !description) {
      showToast('Reason and explanation are required.', 'error');
      return;
    }

    const fd = new FormData();
    fd.append('reason', reason);
    fd.append('description', description);
    fd.append('evidence_video_url', evidenceUrl);

    try {
      const response = await fetch(room.urls.report_dispute, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': getCsrfToken(),
        },
        body: fd,
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        showToast(data.error || 'Unable to submit dispute.', 'error');
        return;
      }

      closeDisputeModal();
      showToast(data.message || 'Dispute submitted.', 'ok');
      appendChatMessage({
        message_id: `dispute:${Date.now()}`,
        username: 'System',
        text: 'A match dispute ticket was submitted for organizer review.',
        timestamp: nowIso(),
      }, 'system');
    } catch (_err) {
      showToast('Network error while submitting dispute.', 'error');
    }
  }

  function openDisputeModal() {
    const modal = byId('dispute-modal');
    if (!modal) {
      return;
    }
    modal.classList.remove('hidden-state');
    modal.classList.add('flex');
  }

  function closeDisputeModal() {
    const modal = byId('dispute-modal');
    if (!modal) {
      return;
    }
    modal.classList.add('hidden-state');
    modal.classList.remove('flex');
  }

  function handleFileSelect(side, file) {
    if (!file) {
      return;
    }

    const contentType = String(file.type || '').toLowerCase();
    if (contentType && !contentType.startsWith('image/')) {
      showToast('Only image files are allowed.', 'error');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      showToast('Proof image must be 10MB or smaller.', 'error');
      return;
    }

    state.uploadedFiles[side] = file;
    renderResultPhase();
    refreshIcons();
  }

  function sendChatMessage(text) {
    const msg = String(text || '').trim();
    if (!msg) {
      return;
    }

    if (!state.ws || state.ws.readyState !== window.WebSocket.OPEN) {
      showToast('Realtime channel is reconnecting. Try again shortly.', 'error');
      return;
    }

    try {
      state.ws.send(JSON.stringify({ type: 'chat_message', text: msg }));
    } catch (_err) {
      showToast('Chat send failed.', 'error');
    }
  }

  function handleWsMessage(raw) {
    let data = null;
    try {
      data = JSON.parse(raw || '{}');
    } catch (_err) {
      data = null;
    }

    if (!data || typeof data !== 'object') {
      return;
    }

    if (data.type === 'ping') {
      try {
        state.ws.send(JSON.stringify({ type: 'pong', timestamp: data.timestamp || nowIso() }));
      } catch (_err) {
        // no-op
      }
      return;
    }

    if (data.type === 'connection_established') {
      appendChatMessage({
        message_id: `ws:${Date.now()}`,
        username: 'System',
        text: 'Realtime channel connected.',
        timestamp: nowIso(),
      }, 'system');
      return;
    }

    if (data.type === 'match_chat') {
      const chat = data.data || {};
      const mine = Number(chat.user_id) === Number(room.me?.user_id);
      appendChatMessage(chat, mine ? 'mine' : 'peer');
      return;
    }

    if (data.type === 'match_room_event') {
      const payload = data.data && data.data.payload;
      if (payload && payload.room) {
        room = payload.room;
        state.previewResults = false;
        renderAll();
      }

      const message = payload && payload.message;
      if (message) {
        appendChatMessage({
          message_id: `room:${Date.now()}`,
          username: 'System',
          text: String(message),
          timestamp: nowIso(),
        }, 'system');
      }
      return;
    }

    if (data.type === 'match_state_changed') {
      syncRoom();
      return;
    }

    if (data.type === 'error') {
      showToast(data.message || 'Realtime error.', 'error');
    }
  }

  function connectWs() {
    if (!room.match?.id) {
      return;
    }

    if (state.ws) {
      try {
        state.ws.close();
      } catch (_err) {
        // ignore
      }
      state.ws = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    let wsUrl = `${protocol}://${window.location.host}/ws/match/${room.match.id}/`;

    let token = null;
    try {
      token = window.localStorage.getItem('access_token') || window.sessionStorage.getItem('access_token');
    } catch (_err) {
      token = null;
    }

    if (token) {
      wsUrl += `?token=${encodeURIComponent(token)}`;
    }

    state.ws = new window.WebSocket(wsUrl);

    state.ws.onopen = function () {
      state.wsConnected = true;
      if (state.reconnectTimer) {
        clearTimeout(state.reconnectTimer);
        state.reconnectTimer = null;
      }
      try {
        state.ws.send(JSON.stringify({ type: 'subscribe' }));
      } catch (_err) {
        // ignore
      }
    };

    state.ws.onmessage = function (event) {
      handleWsMessage(event.data);
    };

    state.ws.onclose = function () {
      state.wsConnected = false;
      if (!state.reconnectTimer) {
        state.reconnectTimer = window.setTimeout(connectWs, 3000);
      }
    };

    state.ws.onerror = function () {
      state.wsConnected = false;
    };
  }

  function collectCredentialPayload() {
    const form = byId('cred-form');
    if (!form) {
      return {};
    }

    const payload = {};
    const fields = form.querySelectorAll('[data-cred-key]');
    fields.forEach((node) => {
      const key = String(node.getAttribute('data-cred-key') || '').trim();
      if (!key) {
        return;
      }
      payload[key] = String(node.value || '').trim();
    });
    return payload;
  }

  async function submitResultFor(side) {
    if (!canSubmitForSide(side)) {
      showToast('You cannot submit for this side.', 'error');
      return;
    }

    const suffix = side === 1 ? 'a' : 'b';
    const scoreFor = byId(`score-${suffix}`)?.value;
    const scoreAgainst = byId(`score-${suffix}-opp`)?.value;

    const sf = toInt(scoreFor, NaN);
    const sa = toInt(scoreAgainst, NaN);

    if (!Number.isFinite(sf) || !Number.isFinite(sa) || sf < 0 || sa < 0) {
      showToast('Valid scores are required for submission.', 'error');
      return;
    }

    const payload = {
      score_for: sf,
      score_against: sa,
      note: String(byId(`note-${suffix}`)?.value || '').trim(),
      evidence_url: String(byId(`evidence-url-${suffix}`)?.value || '').trim(),
      acting_side: isStaffUser() ? resolveActingSide(side) : side,
    };

    await submitWorkflow('submit_result', payload, {
      multipart: true,
      file: state.uploadedFiles[side] || null,
    });
  }

  function bindStaticEvents() {
    const tossBtn = byId('btn-coin-toss');
    if (tossBtn) {
      tossBtn.addEventListener('click', () => {
        submitWorkflow('coin_toss', {});
      });
    }

    const proceedBtn = byId('btn-proceed-after-toss');
    if (proceedBtn) {
      proceedBtn.addEventListener('click', () => {
        if (!isAdminMode()) {
          return;
        }
        submitWorkflow('advance_phase', { phase: 'phase1' });
      });
    }

    const readyBtn = byId('btn-direct-ready');
    if (readyBtn) {
      readyBtn.addEventListener('click', () => {
        const side = resolveActingSide(mySide());
        submitWorkflow('direct_ready', {
          ready: true,
          acting_side: side,
        });
      });
    }

    const saveCredBtn = byId('btn-broadcast-creds');
    if (saveCredBtn) {
      saveCredBtn.addEventListener('click', (event) => {
        event.preventDefault();
        submitWorkflow('save_credentials', collectCredentialPayload());
      });
    }

    const liveBtn = byId('btn-start-live');
    if (liveBtn) {
      liveBtn.addEventListener('click', () => {
        submitWorkflow('start_live', {});
      });
    }

    const toResultsBtn = byId('btn-to-results');
    if (toResultsBtn) {
      toResultsBtn.addEventListener('click', () => {
        if (room.me?.can_force_phase) {
          submitWorkflow('advance_phase', { phase: 'results' });
        } else {
          state.previewResults = true;
          renderPhaseLayout();
          renderResultPhase();
          refreshIcons();
        }
      });
    }

    const submitA = byId('submit-btn-a');
    if (submitA) {
      submitA.addEventListener('click', () => submitResultFor(1));
    }

    const submitB = byId('submit-btn-b');
    if (submitB) {
      submitB.addEventListener('click', () => submitResultFor(2));
    }

    const inputA = byId('upload-input-a');
    if (inputA) {
      inputA.addEventListener('change', () => {
        handleFileSelect(1, inputA.files && inputA.files[0]);
      });
    }

    const inputB = byId('upload-input-b');
    if (inputB) {
      inputB.addEventListener('change', () => {
        handleFileSelect(2, inputB.files && inputB.files[0]);
      });
    }

    const zoneA = byId('upload-a');
    if (zoneA) {
      zoneA.addEventListener('click', () => {
        if (!canSubmitForSide(1)) {
          return;
        }
        byId('upload-input-a')?.click();
      });
    }

    const zoneB = byId('upload-b');
    if (zoneB) {
      zoneB.addEventListener('click', () => {
        if (!canSubmitForSide(2)) {
          return;
        }
        byId('upload-input-b')?.click();
      });
    }

    const tabChat = byId('tab-chat-btn');
    const tabIntel = byId('tab-intel-btn');
    const tabVoice = byId('tab-voice-btn');
    const tabAdmin = byId('tab-admin-btn');

    tabChat?.addEventListener('click', () => setTab('chat'));
    tabIntel?.addEventListener('click', () => setTab('intel'));
    tabVoice?.addEventListener('click', () => setTab('voice'));
    tabAdmin?.addEventListener('click', () => setTab('admin'));

    const activateProxy = byId('btn-activate-proxy');
    if (activateProxy) {
      activateProxy.addEventListener('click', () => {
        if (!isStaffUser()) {
          return;
        }
        state.proxyEnabled = !state.proxyEnabled;
        if (!state.proxyEnabled) {
          state.proxySide = 1;
        }
        renderProxyControls();
        renderDirectReady();
      });
    }

    const proxyA = byId('proxy-btn-a');
    const proxyB = byId('proxy-btn-b');
    proxyA?.addEventListener('click', () => {
      state.proxyEnabled = true;
      state.proxySide = 1;
      renderProxyControls();
      renderDirectReady();
    });
    proxyB?.addEventListener('click', () => {
      state.proxyEnabled = true;
      state.proxySide = 2;
      renderProxyControls();
      renderDirectReady();
    });

    const nextPhase = byId('btn-admin-next-phase');
    if (nextPhase) {
      nextPhase.addEventListener('click', () => {
        const idx = PHASE_ORDER.indexOf(currentPhase());
        const next = PHASE_ORDER[Math.min(idx + 1, PHASE_ORDER.length - 1)] || 'completed';
        submitWorkflow('advance_phase', { phase: next });
      });
    }

    const overrideBtn = byId('btn-admin-override');
    if (overrideBtn) {
      overrideBtn.addEventListener('click', () => {
        const scoreA = byId('admin-score-a')?.value;
        const scoreB = byId('admin-score-b')?.value;
        const p1 = toInt(scoreA, NaN);
        const p2 = toInt(scoreB, NaN);
        if (!Number.isFinite(p1) || !Number.isFinite(p2)) {
          showToast('Admin score override requires numeric scores.', 'error');
          return;
        }
        submitWorkflow('admin_override_result', {
          participant1_score: p1,
          participant2_score: p2,
          note: 'Admin override from Match Lobby V2.',
        });
      });
    }

    const applyScore = byId('btn-admin-apply-score');
    if (applyScore) {
      applyScore.addEventListener('click', () => {
        byId('btn-admin-override')?.click();
      });
    }

    const sendMsg = byId('btn-admin-send-msg');
    if (sendMsg) {
      sendMsg.addEventListener('click', () => {
        const msg = String(byId('admin-msg')?.value || '').trim();
        if (!msg) {
          showToast('Announcement text is required.', 'error');
          return;
        }
        submitWorkflow('system_announcement', { message: msg }).then((ok) => {
          if (ok && byId('admin-msg')) {
            byId('admin-msg').value = '';
          }
        });
      });
    }

    const openDispute = byId('btn-open-dispute');
    openDispute?.addEventListener('click', openDisputeModal);

    const closeDispute = byId('btn-close-dispute');
    closeDispute?.addEventListener('click', closeDisputeModal);

    const cancelDispute = byId('btn-dispute-cancel');
    cancelDispute?.addEventListener('click', closeDisputeModal);

    const submitDisputeBtn = byId('btn-dispute-submit');
    submitDisputeBtn?.addEventListener('click', submitDispute);

    const modal = byId('dispute-modal');
    if (modal) {
      modal.addEventListener('click', (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
          return;
        }
        if (target.dataset.closeDispute === '1') {
          closeDisputeModal();
        }
      });
    }

    const chatForm = byId('chat-form');
    if (chatForm) {
      chatForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const input = byId('chat-input');
        if (!input) {
          return;
        }
        const text = String(input.value || '').trim();
        if (!text) {
          return;
        }
        sendChatMessage(text);
        input.value = '';
      });
    }

    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        syncRoom();
      }
    });
  }

  function refreshIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  function renderAll() {
    renderTheme();
    renderHeader();
    renderClock();
    renderPhaseLayout();
    renderCoinToss();
    renderVeto();
    renderDraft();
    renderDirectReady();
    renderLobbyPhase();
    renderServerPhase();
    renderResultPhase();
    renderIntelPanel();
    renderProxyControls();
    renderTabs();
    renderAnnouncements();
    refreshIcons();
  }

  function bootstrap() {
    state.activeTab = 'chat';
    state.proxyEnabled = false;
    state.proxySide = 1;

    bindStaticEvents();
    renderAll();
    connectWs();

    if (state.syncTimer) {
      clearInterval(state.syncTimer);
    }
    state.syncTimer = window.setInterval(syncRoom, 20000);

    if (state.clockTimer) {
      clearInterval(state.clockTimer);
    }
    state.clockTimer = window.setInterval(renderClock, 1000);
  }

  bootstrap();
})();
