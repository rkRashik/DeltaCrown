(function () {
  'use strict';

  const payloadNode = document.getElementById('match-room-payload');
  if (!payloadNode) {
    return;
  }

  let parsedPayload = {};
  try {
    parsedPayload = JSON.parse(payloadNode.textContent || '{}');
  } catch (_err) {
    return;
  }

  if (!parsedPayload || typeof parsedPayload !== 'object' || !parsedPayload.match || !parsedPayload.urls) {
    return;
  }

  const PHASE_FALLBACK = ['coin_toss', 'phase1', 'lobby_setup', 'live', 'results', 'completed'];
  const VALID_PHASES = new Set(PHASE_FALLBACK);
  const MOBILE_TABS = ['engine', 'chat', 'intel'];
  const ALLOWED_CREDENTIAL_KEYS = new Set(['lobby_code', 'password', 'map', 'server', 'game_mode', 'notes']);

  const THEME_PRESETS = {
    valorant: {
      accent: '#00f0ff',
      rgb: [0, 240, 255],
      bg: "url('https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=2850')",
    },
    efootball: {
      accent: '#00ff66',
      rgb: [0, 255, 102],
      bg: "url('https://images.unsplash.com/photo-1518605368461-1e1e38ce7058?q=80&w=2850')",
    },
  };

  var state = {
    room: ensureRoomShape(parsedPayload),
    socketPresence: resolvePresence(parsedPayload.presence || asObject(parsedPayload.workflow).presence, parsedPayload.match),
    ws: null,
    wsConnected: false,
    reconnectAttempts: 0,
    reconnectTimer: null,
    presenceTimer: null,
    fallbackSyncTimer: null,
    noShowDeadlineMs: 0,
    noShowTimer: null,
    navHidden: false,
    lastMainScrollTop: 0,
    activeDesktopTab: 'chat',
    activeMobileTab: 'engine',
    chatIds: new Set(),
    seenAnnouncements: new Set(),
    requestBusy: false,
    lastToastAt: 0,
    lastToastText: '',
    localPresenceHoldUntilMs: 0,
    lastWaitingLocked: false,
  };

  const elements = {
    shell: byId('match-room-shell'),
    waitingOverlay: byId('waiting-overlay'),
    waitingCopy: byId('waiting-copy'),
    waitingYouDot: byId('waiting-you-dot'),
    waitingOpponentDot: byId('waiting-opponent-dot'),
    waitingOpponentName: byId('waiting-opponent-name'),
    waitingNoShowTimer: byId('waiting-noshow-timer'),
    topNav: byId('room-top-nav'),
    navBackLink: byId('nav-back-link'),
    navMatchId: byId('nav-match-id'),
    navTourneyName: byId('nav-tourney-name'),
    navKickoffBadge: byId('nav-kickoff-badge'),
    navFormatBadge: byId('nav-format-badge'),
    navFlowBadge: byId('nav-flow-badge'),
    socketPill: byId('socket-pill'),
    helpSignalBtn: byId('help-signal-btn'),
    heroTeamALogo: byId('hero-team-a-logo'),
    heroTeamAName: byId('hero-team-a-name'),
    heroTeamAMeta: byId('hero-team-a-meta'),
    heroTeamBLogo: byId('hero-team-b-logo'),
    heroTeamBName: byId('hero-team-b-name'),
    heroTeamBMeta: byId('hero-team-b-meta'),
    heroFormatLabel: byId('hero-format-label'),
    phaseTracker: byId('phase-tracker'),
    engineContainer: byId('engine-container'),
    rulesList: byId('rules-list'),
    chatWindow: byId('chat-window'),
    chatForm: byId('chat-form'),
    chatInput: byId('chat-input'),
    sideChat: byId('side-chat'),
    sideIntel: byId('side-intel'),
    sideAdmin: byId('side-admin'),
    dtTabChat: byId('dt-tab-chat'),
    dtTabIntel: byId('dt-tab-intel'),
    dtTabAdmin: byId('dt-tab-admin'),
    mobTabEngine: byId('mob-tab-engine'),
    mobTabChat: byId('mob-tab-chat'),
    mobTabIntel: byId('mob-tab-intel'),
    mainScroll: byId('main-scroll'),
    mobilePanelOverlay: byId('mobile-panel-overlay'),
    mobilePanelContent: byId('mobile-panel-content'),
    adminForceNext: byId('admin-force-next'),
    adminOpenOverride: byId('admin-open-override'),
    adminBroadcast: byId('admin-broadcast'),
    overrideModal: byId('override-modal'),
    overrideClose: byId('override-close'),
    overrideCancel: byId('override-cancel'),
    overrideApply: byId('override-apply'),
    overrideP1: byId('override-p1'),
    overrideP2: byId('override-p2'),
    overrideNote: byId('override-note'),
    roomToast: byId('room-toast'),
  };

  init();

  function init() {
    setGlobalFocusMode(true);
    state.lastWaitingLocked = waitingLocked();
    bindStaticEvents();
    updateShellViewportHeight();
    ensureNoShowTicker();
    renderAll();
    initMobileTopNavBehavior();
    connectSocket();
    startPresenceHeartbeat();
    startFallbackSync();
  }

  function setGlobalFocusMode(enabled) {
    const body = document.body;
    if (!body) {
      return;
    }
    body.classList.toggle('match-room-focus-mode', Boolean(enabled));
  }

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

  function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  }

  function asList(value) {
    return Array.isArray(value) ? value : [];
  }

  function toInt(value, fallback) {
    const parsed = Number.parseInt(String(value == null ? '' : value), 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function bool(value, fallback) {
    if (value == null) {
      return !!fallback;
    }
    if (typeof value === 'boolean') {
      return value;
    }
    if (typeof value === 'number') {
      return value !== 0;
    }
    const token = String(value).trim().toLowerCase();
    if (token === '1' || token === 'true' || token === 'yes' || token === 'y' || token === 'on') {
      return true;
    }
    if (token === '0' || token === 'false' || token === 'no' || token === 'n' || token === 'off' || token === '') {
      return false;
    }
    return !!fallback;
  }

  function nowMs() {
    return Date.now();
  }

  function getCsrfToken() {
    const row = document.cookie
      .split('; ')
      .find((chunk) => chunk.startsWith('csrftoken='));
    return row ? decodeURIComponent(row.slice('csrftoken='.length)) : '';
  }

  function maybeRunIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  function formatLocalTime(isoString) {
    if (!isoString) {
      return 'N/A';
    }
    const dt = new Date(isoString);
    if (Number.isNaN(dt.getTime())) {
      return 'N/A';
    }
    return dt.toLocaleString([], {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function shortClock(isoString) {
    if (!isoString) {
      return 'now';
    }
    const dt = new Date(isoString);
    if (Number.isNaN(dt.getTime())) {
      return 'now';
    }
    return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function parseTimestamp(value) {
    if (!value) {
      return 0;
    }
    const dt = new Date(value);
    const ts = dt.getTime();
    return Number.isFinite(ts) ? ts : 0;
  }

  function resolveNoShowDeadlineMs() {
    const checkIn = asObject(state.room.check_in);
    const checkInClose = parseTimestamp(checkIn.closes_at);
    if (checkInClose > 0) {
      return checkInClose;
    }

    const match = asObject(state.room.match);
    const scheduled = parseTimestamp(match.scheduled_time);
    if (scheduled > 0) {
      return scheduled + (15 * 60 * 1000);
    }

    return nowMs() + (15 * 60 * 1000);
  }

  function formatCountdown(msRemaining) {
    const safe = Math.max(0, msRemaining);
    const totalSeconds = Math.ceil(safe / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hours > 0) {
      return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  function renderNoShowTimer() {
    if (!elements.waitingNoShowTimer) {
      return;
    }

    const deadline = state.noShowDeadlineMs || resolveNoShowDeadlineMs();
    const msRemaining = Math.max(0, deadline - nowMs());
    elements.waitingNoShowTimer.textContent = formatCountdown(msRemaining);
  }

  function ensureNoShowTicker() {
    const nextDeadline = resolveNoShowDeadlineMs();

    if (!state.noShowDeadlineMs || Math.abs(state.noShowDeadlineMs - nextDeadline) > 5000) {
      state.noShowDeadlineMs = nextDeadline;
    }

    if (!state.noShowTimer) {
      state.noShowTimer = window.setInterval(function () {
        renderNoShowTimer();
      }, 1000);
    }

    renderNoShowTimer();
  }

  function updateMobileOverlayTopOffset() {
    if (!elements.mobilePanelOverlay || !elements.topNav) {
      return;
    }

    if (window.innerWidth >= 1024) {
      elements.mobilePanelOverlay.style.top = '64px';
      return;
    }

    const navHeight = state.navHidden
      ? 0
      : Math.max(0, Math.round(elements.topNav.getBoundingClientRect().height || 56));
    elements.mobilePanelOverlay.style.top = `${navHeight}px`;
  }

  function updateShellViewportHeight() {
    if (!elements.shell) {
      return;
    }

    const rect = elements.shell.getBoundingClientRect();
    const topOffset = Math.max(0, Math.round(rect.top || 0));
    const viewportHeight = window.visualViewport && Number.isFinite(window.visualViewport.height)
      ? Math.round(window.visualViewport.height)
      : Math.round(window.innerHeight || 0);

    const shellHeight = Math.max(420, viewportHeight - topOffset);
    elements.shell.style.setProperty('--room-shell-height', `${shellHeight}px`);
  }

  function setMobileTopNavHidden(hidden) {
    if (!elements.topNav) {
      return;
    }

    const shouldHide = Boolean(hidden) && window.innerWidth < 1024;
    state.navHidden = shouldHide;
    elements.topNav.classList.toggle('nav-hidden', shouldHide);
    updateMobileOverlayTopOffset();
  }

  function handleMainScrollForNav() {
    if (!elements.mainScroll || window.innerWidth >= 1024) {
      setMobileTopNavHidden(false);
      return;
    }

    const current = Math.max(0, elements.mainScroll.scrollTop || 0);
    const delta = current - state.lastMainScrollTop;

    if (current <= 8) {
      setMobileTopNavHidden(false);
    } else if (delta > 6) {
      setMobileTopNavHidden(true);
    } else if (delta < -6) {
      setMobileTopNavHidden(false);
    }

    state.lastMainScrollTop = current;
  }

  function initMobileTopNavBehavior() {
    if (!elements.mainScroll || !elements.topNav) {
      return;
    }

    elements.mainScroll.addEventListener('scroll', handleMainScrollForNav, { passive: true });

    window.addEventListener('resize', function () {
      updateShellViewportHeight();
      if (window.innerWidth >= 1024) {
        setMobileTopNavHidden(false);
      }
      updateMobileOverlayTopOffset();
    }, { passive: true });

    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', function () {
        updateShellViewportHeight();
        updateMobileOverlayTopOffset();
      }, { passive: true });
    }

    updateShellViewportHeight();
    updateMobileOverlayTopOffset();
  }

  function initials(name) {
    const text = String(name || '').trim();
    if (!text) {
      return '?';
    }
    const chunks = text.split(/\s+/).filter(Boolean);
    if (!chunks.length) {
      return text.slice(0, 1).toUpperCase();
    }
    if (chunks.length === 1) {
      return chunks[0].slice(0, 2).toUpperCase();
    }
    return `${chunks[0].slice(0, 1)}${chunks[1].slice(0, 1)}`.toUpperCase();
  }

  function activeRoom() {
    if (state && state.room && typeof state.room === 'object') {
      return state.room;
    }
    return asObject(parsedPayload);
  }

  function canonicalGameKey() {
    const game = asObject(activeRoom().game);
    const key = String(game.pipeline_game_key || game.slug || '').trim().toLowerCase();
    if (key.includes('efootball')) {
      return 'efootball';
    }
    if (key.includes('valorant')) {
      return 'valorant';
    }
    return key || 'valorant';
  }

  function canonicalMode() {
    const key = canonicalGameKey();
    if (key === 'efootball') {
      return 'direct';
    }
    if (key === 'valorant') {
      return 'veto';
    }

    const room = activeRoom();
    const game = asObject(room.game);
    const workflow = asObject(room.workflow);
    const mode = String(workflow.mode || game.phase_mode || '').toLowerCase();
    if (mode === 'direct' || mode === 'veto') {
      return mode;
    }
    return 'veto';
  }

  function phase1Kind() {
    const mode = canonicalMode();
    if (mode === 'direct') {
      return 'direct';
    }

    const room = activeRoom();
    const workflow = asObject(room.workflow);
    const pipeline = asObject(room.pipeline);
    const kind = String(workflow.phase1_kind || pipeline.phase1_kind || '').toLowerCase();
    if (kind === 'direct') {
      return 'direct';
    }
    return 'veto';
  }

  function credentialLabelForKey(key) {
    if (key === 'lobby_code') {
      return canonicalGameKey() === 'efootball' ? 'Room Number' : 'Lobby Code';
    }
    if (key === 'password') {
      return 'Password';
    }
    if (key === 'map') {
      return 'Map';
    }
    if (key === 'server') {
      return 'Server';
    }
    if (key === 'game_mode') {
      return 'Game Mode';
    }
    if (key === 'notes') {
      return 'Notes';
    }
    return key;
  }

  function fallbackCredentialSchema() {
    if (canonicalGameKey() === 'efootball') {
      return [
        { key: 'lobby_code', label: 'Room Number', kind: 'text', required: true },
        { key: 'password', label: 'Password', kind: 'text', required: false },
      ];
    }

    return [
      { key: 'lobby_code', label: 'Lobby Code', kind: 'text', required: true },
      { key: 'password', label: 'Password', kind: 'text', required: false },
      { key: 'map', label: 'Map', kind: 'text', required: false },
      { key: 'server', label: 'Server', kind: 'text', required: false },
      { key: 'game_mode', label: 'Game Mode', kind: 'text', required: false },
      { key: 'notes', label: 'Notes', kind: 'textarea', required: false },
    ];
  }

  function normalizeCredentialSchema(rows) {
    const normalized = [];

    asList(rows).forEach(function (entry) {
      const row = asObject(entry);
      let key = String(row.key || row.name || '').trim().toLowerCase();
      if (key === 'room_number') {
        key = 'lobby_code';
      }
      if (!ALLOWED_CREDENTIAL_KEYS.has(key)) {
        return;
      }

      const kindToken = String(row.kind || row.type || '').trim().toLowerCase();
      const kind = (kindToken === 'textarea' || key === 'notes') ? 'textarea' : 'text';
      const label = String(row.label || row.title || credentialLabelForKey(key) || '').trim() || credentialLabelForKey(key);

      normalized.push({
        key,
        label,
        kind,
        required: bool(row.required, false),
      });
    });

    if (normalized.length) {
      return normalized;
    }

    return fallbackCredentialSchema();
  }

  function credentialSchema() {
    const game = asObject(activeRoom().game);
    return normalizeCredentialSchema(game.credentials_schema);
  }

  function credentialInputId(key) {
    return `cred-${String(key || '').trim().toLowerCase().replaceAll('_', '-')}`;
  }

  function resolvePresence(input, matchValue) {
    const source = asObject(input);
    const match = asObject(matchValue);
    const p1 = asObject(match.participant1);
    const p2 = asObject(match.participant2);

    const sides = {
      '1': normalizePresenceSide(source['1']),
      '2': normalizePresenceSide(source['2']),
    };

    sides['1'].checked_in = bool(p1.checked_in, false);
    sides['2'].checked_in = bool(p2.checked_in, false);
    return sides;
  }

  function normalizePresenceSide(raw) {
    const row = asObject(raw);
    const status = String(row.status || '').toLowerCase();
    const online = bool(row.online, status === 'online' || status === 'away');

    return {
      status: online ? (status === 'away' ? 'away' : 'online') : 'offline',
      online,
      last_seen: row.last_seen || null,
      user_id: row.user_id || null,
      username: row.username || null,
      checked_in: bool(row.checked_in, false),
    };
  }

  function ensureRoomShape(roomValue) {
    const room = asObject(roomValue);

    room.match = asObject(room.match);
    room.match.participant1 = asObject(room.match.participant1);
    room.match.participant2 = asObject(room.match.participant2);
    room.tournament = asObject(room.tournament);
    room.game = asObject(room.game);
    room.game.credentials_schema = asList(room.game.credentials_schema).map((row) => asObject(row));
    room.game.match_rules = asList(room.game.match_rules).map((row) => asObject(row));
    room.lobby = asObject(room.lobby);
    room.pipeline = asObject(room.pipeline);
    room.workflow = asObject(room.workflow);
    room.check_in = asObject(room.check_in);
    room.me = asObject(room.me);
    room.urls = asObject(room.urls);
    room.websocket = asObject(room.websocket);

    room.workflow.coin_toss = asObject(room.workflow.coin_toss);
    room.workflow.veto = asObject(room.workflow.veto);
    room.workflow.veto.sequence = asList(room.workflow.veto.sequence);
    room.workflow.veto.pool = asList(room.workflow.veto.pool);
    room.workflow.veto.bans = asList(room.workflow.veto.bans);
    room.workflow.veto.picks = asList(room.workflow.veto.picks);
    room.workflow.direct_ready = asObject(room.workflow.direct_ready);
    room.workflow.credentials = asObject(room.workflow.credentials);
    room.workflow.result_submissions = asObject(room.workflow.result_submissions);
    room.workflow.result_visibility = asObject(room.workflow.result_visibility);
    room.workflow.announcements = asList(room.workflow.announcements);

    room.presence = resolvePresence(room.presence || room.workflow.presence, room.match);
    room.workflow.presence = resolvePresence(room.workflow.presence || room.presence, room.match);

    room.workflow.phase_order = asList(room.workflow.phase_order)
      .map((phase) => String(phase || '').trim())
      .filter((phase) => VALID_PHASES.has(phase));

    if (!room.workflow.phase_order.length) {
      room.workflow.phase_order = defaultPhaseOrder();
    }

    if (!VALID_PHASES.has(String(room.workflow.phase || ''))) {
      room.workflow.phase = room.workflow.phase_order[0] || defaultPhaseOrder()[0];
    }

    return room;
  }

  function defaultPhaseOrder() {
    const mode = canonicalMode();
    if (mode === 'direct') {
      return ['phase1', 'lobby_setup', 'live', 'results', 'completed'];
    }
    return ['coin_toss', 'phase1', 'lobby_setup', 'live', 'results', 'completed'];
  }

  function mySide() {
    const side = toInt(asObject(state.room.me).side, 0);
    return side === 1 || side === 2 ? side : null;
  }

  function opponentSide() {
    const side = mySide();
    if (side === 1) {
      return 2;
    }
    if (side === 2) {
      return 1;
    }
    return null;
  }

  function participantForSide(side) {
    if (side === 1) {
      return asObject(state.room.match.participant1);
    }
    if (side === 2) {
      return asObject(state.room.match.participant2);
    }
    return {};
  }

  function sideOnline(side) {
    if (side !== 1 && side !== 2) {
      return false;
    }
    const row = asObject(asObject(state.room.presence)[String(side)]);
    return bool(row.online, false);
  }

  function sideCheckedIn(side) {
    if (side !== 1 && side !== 2) {
      return false;
    }
    const participant = participantForSide(side);
    return bool(participant.checked_in, false);
  }

  function bothSidesOnline() {
    return sideOnline(1) && sideOnline(2);
  }

  function hasSubmittedResultForSide(side) {
    if (side !== 1 && side !== 2) {
      return false;
    }
    const row = workflowSubmission(side);
    if (!row || typeof row !== 'object') {
      return false;
    }
    return Boolean(row.submission_id || row.submitted_at);
  }

  function bypassPresenceLock() {
    const side = mySide();
    if (side !== 1 && side !== 2) {
      return true;
    }
    if (bool(asObject(state.room.me).admin_mode, false)) {
      return true;
    }
    const phase = currentPhase();
    if (phase === 'completed') {
      return true;
    }
    return hasSubmittedResultForSide(side);
  }

  function waitingLocked() {
    const side = mySide();
    if (side !== 1 && side !== 2) {
      return false;
    }
    if (bypassPresenceLock()) {
      return false;
    }
    return !bothSidesOnline();
  }

  function phaseOrder() {
    const wfOrder = asList(asObject(state.room.workflow).phase_order)
      .map((phase) => String(phase || '').trim())
      .filter((phase) => VALID_PHASES.has(phase));

    if (wfOrder.length) {
      return wfOrder;
    }

    return defaultPhaseOrder();
  }

  function currentPhase() {
    const workflow = asObject(state.room.workflow);
    const order = phaseOrder();
    const current = String(workflow.phase || '').trim();
    if (order.includes(current)) {
      return current;
    }
    return order[0] || 'phase1';
  }

  function effectivePolicy() {
    const workflowPolicy = asObject(asObject(state.room.workflow).policy);
    const pipelinePolicy = asObject(asObject(state.room.pipeline).policy);
    return asObject(workflowPolicy.effective || pipelinePolicy.effective);
  }

  function requiresMatchEvidence() {
    return bool(asObject(effectivePolicy()).require_match_evidence, false);
  }

  function phaseLabel(phase) {
    if (phase === 'coin_toss') {
      return 'Coin Toss';
    }
    if (phase === 'phase1') {
      return phase1Kind() === 'direct' ? 'Direct Ready' : 'Map Veto';
    }
    if (phase === 'lobby_setup') {
      return 'Lobby Setup';
    }
    if (phase === 'live') {
      return 'Live Match';
    }
    if (phase === 'results') {
      return 'Results';
    }
    if (phase === 'completed') {
      return 'Completed';
    }
    return phase;
  }

  function mapPool() {
    const workflowPool = asList(asObject(state.room.workflow).veto.pool)
      .map((row) => String(row || '').trim())
      .filter(Boolean);

    if (workflowPool.length) {
      return workflowPool;
    }

    return asList(asObject(state.room.game).map_pool)
      .map((row) => String(row || '').trim())
      .filter(Boolean);
  }

  function workflowSubmission(side) {
    const submissions = asObject(asObject(state.room.workflow).result_submissions);
    const row = submissions[String(side)];
    return row && typeof row === 'object' ? row : null;
  }

  function workflowResultVisibility() {
    return asObject(asObject(state.room.workflow).result_visibility);
  }

  function applyRoom(nextRoom) {
    const normalized = ensureRoomShape(nextRoom);

    if (state.socketPresence && typeof state.socketPresence === 'object') {
      normalized.presence = mergePresenceSnapshots(normalized.presence, state.socketPresence);
      normalized.workflow.presence = mergePresenceSnapshots(normalized.workflow.presence, state.socketPresence);
    }

    state.room = normalized;
    ensureNoShowTicker();
    renderAll();
  }

  function mergePresenceSnapshots(baseValue, overrideValue) {
    const base = resolvePresence(baseValue, state.room.match);
    const override = resolvePresence(overrideValue, state.room.match);

    return {
      '1': mergePresenceSide(base['1'], override['1']),
      '2': mergePresenceSide(base['2'], override['2']),
    };
  }

  function mergePresenceSide(baseSide, overrideSide) {
    const base = normalizePresenceSide(baseSide);
    const override = normalizePresenceSide(overrideSide);

    if (!override.online && !override.user_id && !override.last_seen) {
      return base;
    }

    return {
      status: override.status || base.status,
      online: bool(override.online, false),
      last_seen: override.last_seen || base.last_seen || null,
      user_id: override.user_id || base.user_id || null,
      username: override.username || base.username || null,
      checked_in: bool(override.checked_in, base.checked_in),
    };
  }

  function renderAll() {
    applyTheme();
    renderHeader();
    renderRules();
    renderAdminVisibility();
    renderPhaseTracker();
    renderEngine();
    processAnnouncements();
    updateWaitingOverlay();
    updateSocketPill();
    syncMobileMirror();
    maybeRunIcons();
  }

  function applyTheme() {
    const key = canonicalGameKey();
    const shell = elements.shell;
    if (!shell) {
      return;
    }

    const preset = THEME_PRESETS[key] || THEME_PRESETS.valorant;
    shell.setAttribute('data-game', key);
    shell.style.setProperty('--ac', preset.accent);
    shell.style.setProperty('--ar', String(preset.rgb[0]));
    shell.style.setProperty('--ag', String(preset.rgb[1]));
    shell.style.setProperty('--ab', String(preset.rgb[2]));
    shell.style.setProperty('--bg-img', preset.bg);

    if (elements.mainScroll) {
      elements.mainScroll.style.display = state.activeMobileTab === 'engine' ? '' : 'none';
    }
  }

  function renderHeader() {
    const match = asObject(state.room.match);
    const tournament = asObject(state.room.tournament);
    const p1 = asObject(match.participant1);
    const p2 = asObject(match.participant2);

    if (elements.navMatchId) {
      const roundText = Number.isFinite(Number(match.round_number)) ? `R${match.round_number}` : 'R?';
      const matchText = Number.isFinite(Number(match.match_number)) ? `M${match.match_number}` : `M${match.id || '?'}`;
      elements.navMatchId.textContent = `Match ${roundText} ${matchText}`;
    }

    if (elements.navTourneyName) {
      elements.navTourneyName.textContent = String(tournament.name || 'Tournament');
    }

    if (elements.navBackLink) {
      elements.navBackLink.setAttribute('href', String(asObject(state.room.urls).hub || asObject(state.room.urls).match_detail || '#'));
    }

    renderHeaderCommandBadges();

    if (elements.heroTeamAName) {
      elements.heroTeamAName.textContent = String(p1.name || 'Participant A');
    }
    if (elements.heroTeamBName) {
      elements.heroTeamBName.textContent = String(p2.name || 'Participant B');
    }

    if (elements.heroTeamALogo) {
      renderLogo(elements.heroTeamALogo, p1, 1);
    }
    if (elements.heroTeamBLogo) {
      renderLogo(elements.heroTeamBLogo, p2, 2);
    }

    if (elements.heroFormatLabel) {
      const bestOf = toInt(match.best_of, 1);
      const flowLabel = canonicalMode() === 'direct' ? 'Direct Setup' : 'Map Veto';
      elements.heroFormatLabel.textContent = `Bo${bestOf} - ${flowLabel}`;
    }

    renderHeaderPresenceMeta();
  }

  function renderHeaderCommandBadges() {
    const match = asObject(state.room.match);
    const bestOf = Math.max(1, toInt(match.best_of, 1));
    const scheduledToken = String(match.scheduled_time || '').trim();
    const roundText = Number.isFinite(Number(match.round_number)) ? `R${match.round_number}` : 'R?';
    const kickoffText = scheduledToken ? `${roundText} • ${shortClock(scheduledToken)}` : `${roundText} • TBD`;
    const formatText = `Bo${bestOf} • ${phaseLabel(currentPhase())}`;

    const policy = effectivePolicy();
    const requiresCheckIn = bool(policy.require_check_in, false);
    const evidenceRequired = bool(policy.require_match_evidence, false);
    const flowText = `${requiresCheckIn ? 'Check-In Req' : 'Check-In Opt'} • ${evidenceRequired ? 'Evidence Req' : 'Evidence Opt'}`;

    setCommandBadgeText(elements.navKickoffBadge, kickoffText);
    setCommandBadgeText(elements.navFormatBadge, formatText);
    setCommandBadgeText(elements.navFlowBadge, flowText);
  }

  function setCommandBadgeText(node, text) {
    if (!node) {
      return;
    }
    const labelNode = node.querySelector('span');
    if (labelNode) {
      labelNode.textContent = String(text || '');
      return;
    }
    node.textContent = String(text || '');
  }

  function renderHeaderPresenceMeta() {
    if (elements.heroTeamAMeta) {
      const onlineA = sideOnline(1) ? 'Online' : 'Offline';
      elements.heroTeamAMeta.textContent = `Side 1 - ${onlineA}`;
    }
    if (elements.heroTeamBMeta) {
      const onlineB = sideOnline(2) ? 'Online' : 'Offline';
      elements.heroTeamBMeta.textContent = `Side 2 - ${onlineB}`;
    }
  }

  function renderLogo(node, participant, side) {
    const logoUrl = String(participant.logo_url || '').trim();
    if (logoUrl) {
      node.innerHTML = `<img src="${esc(logoUrl)}" alt="${esc(participant.name || 'Participant')}" class="w-full h-full object-cover rounded-xl md:rounded-2xl" loading="lazy" />`;
      return;
    }

    const token = initials(participant.name || (side === 1 ? 'A' : 'B'));
    node.textContent = token;
  }

  function renderRules() {
    if (!elements.rulesList) {
      return;
    }

    const room = state.room;
    const match = asObject(room.match);
    const checkIn = asObject(room.check_in);
    const mode = canonicalMode();
    const p1 = asObject(match.participant1);
    const p2 = asObject(match.participant2);
    const maps = mapPool();

    const backendCards = asList(asObject(room.game).match_rules)
      .map((entry) => {
        const row = asObject(entry);
        return {
          title: String(row.title || '').trim(),
          value: String(row.value || '').trim(),
        };
      })
      .filter((entry) => entry.title && entry.value);

    const cards = backendCards.length
      ? backendCards
      : [
        {
          title: 'Match Configuration',
          value: 'This match has no published configuration yet. Ask the organizer to save it from TOC Rules & Info.',
        },
      ];

    elements.rulesList.innerHTML = cards
      .map((item) => {
        return `
          <div class="p-3 rounded-xl bg-white/5 border border-white/10">
            <p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-1">${esc(item.title)}</p>
            <p class="text-xs text-white leading-relaxed break-words">${esc(item.value)}</p>
          </div>
        `;
      })
      .join('');
  }

  function renderAdminVisibility() {
    const adminMode = bool(asObject(state.room.me).admin_mode, false);

    if (elements.dtTabAdmin) {
      if (adminMode) {
        elements.dtTabAdmin.classList.remove('hidden-state');
      } else {
        elements.dtTabAdmin.classList.add('hidden-state');
      }
    }

    if (!adminMode && state.activeDesktopTab === 'admin') {
      setDesktopTab('chat');
      return;
    }

    setDesktopTab(state.activeDesktopTab);
  }

  function renderPhaseTracker() {
    if (!elements.phaseTracker) {
      return;
    }

    const order = phaseOrder();
    const activePhase = currentPhase();
    const activeIndex = Math.max(0, order.indexOf(activePhase));

    let html = '';

    order.forEach((phase, index) => {
      const done = index < activeIndex;
      const active = index === activeIndex;

      const dotClass = done ? 'phase-dot done' : (active ? 'phase-dot active' : 'phase-dot');
      const textClass = done
        ? 'text-[10px] font-bold text-green-300 uppercase tracking-wide'
        : (active
          ? 'text-[10px] font-bold text-white uppercase tracking-wide'
          : 'text-[10px] font-bold text-gray-500 uppercase tracking-wide');

      html += `
        <div class="flex flex-col items-center gap-1 min-w-[58px]">
          <div class="${dotClass}">${done ? '<i data-lucide="check" class="w-4 h-4"></i>' : esc(String(index + 1))}</div>
          <span class="${textClass}">${esc(phaseLabel(phase))}</span>
        </div>
      `;

      if (index < order.length - 1) {
        const lineClass = index < activeIndex ? 'phase-line done flex-1 max-w-[72px]' : (index === activeIndex ? 'phase-line active flex-1 max-w-[72px]' : 'phase-line flex-1 max-w-[72px]');
        html += `<div class="${lineClass}"><span></span></div>`;
      }
    });

    elements.phaseTracker.innerHTML = html;
  }

  function renderEngine() {
    if (!elements.engineContainer) {
      return;
    }

    const phase = currentPhase();
    const actionTitle = phaseLabel(phase);
    const actionNarrative = phaseNarrative(phase);
    const actionBody = renderPhaseCoreBlock(phase);
    const showCheckInGate = phase === 'coin_toss' || phase === 'phase1' || phase === 'lobby_setup';

    const blocks = [];
    if (showCheckInGate) {
      blocks.push(renderCheckInBlock());
    }

    blocks.push(`
      <section class="phase-morph-shell glass-panel rounded-2xl p-4 md:p-5 border border-white/10" data-active-phase="${esc(phase)}">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Dynamic Action Card</p>
            <h3 class="text-lg md:text-xl font-black text-white">${esc(actionTitle)}</h3>
            <p class="text-xs text-gray-400 mt-1">${esc(actionNarrative)}</p>
          </div>
          <span class="phase-chip">${phase === 'live' ? '<span class="live-pulse"></span>' : ''}${esc(actionTitle)}</span>
        </div>
        <div class="mt-4 md:mt-5">${actionBody}</div>
      </section>
    `);

    elements.engineContainer.innerHTML = blocks.join('');
    state.lastWaitingLocked = waitingLocked();
    maybeRunIcons();
  }

  function phaseNarrative(phase) {
    if (phase === 'coin_toss') {
      return 'Resolve first control so both sides can start with a fair edge.';
    }
    if (phase === 'phase1') {
      return phase1Kind() === 'direct'
        ? 'Both sides confirm ready status before host credentials unlock.'
        : 'Run bans and picks in order to lock the final battleground.';
    }
    if (phase === 'lobby_setup') {
      return 'Host publishes lobby credentials and both teams sync in one room.';
    }
    if (phase === 'live') {
      return 'Match is live. Finish gameplay, then move to result declaration.';
    }
    if (phase === 'results') {
      if (requiresMatchEvidence()) {
        return 'Blind-submit your scoreline with required image evidence, then wait for verification.';
      }
      return 'Blind-submit your scoreline with optional proof and wait for verification.';
    }
    if (phase === 'completed') {
      return 'Result finalized. Jump to hub or bracket for the next assignment.';
    }
    return 'Realtime sync in progress. Refresh if this panel stalls.';
  }

  function renderPhaseCoreBlock(phase) {
    if (phase === 'coin_toss') {
      return renderCoinTossBlock();
    }
    if (phase === 'phase1') {
      return phase1Kind() === 'direct' ? renderDirectReadyBlock() : renderVetoBlock();
    }
    if (phase === 'lobby_setup') {
      return renderLobbySetupBlock();
    }
    if (phase === 'live') {
      return renderLiveBlock();
    }
    if (phase === 'results') {
      return renderResultsBlock(false);
    }
    if (phase === 'completed') {
      return renderCompletedBlock();
    }
    return renderFallbackBlock();
  }

  function renderCheckInBlock() {
    const checkIn = asObject(state.room.check_in);
    const required = bool(checkIn.required, false);
    const side = mySide();

    const p1Ready = sideCheckedIn(1);
    const p2Ready = sideCheckedIn(2);
    const meReady = side === 1 ? p1Ready : (side === 2 ? p2Ready : false);

    let statusText = 'Check-in optional for this match.';
    if (required) {
      if (bool(checkIn.is_pending, false)) {
        statusText = `Window opens ${formatLocalTime(checkIn.opens_at)}.`;
      } else if (bool(checkIn.is_closed, false)) {
        statusText = `Window closed ${formatLocalTime(checkIn.closes_at)}.`;
      } else if (bool(checkIn.is_open, false)) {
        statusText = `Window open until ${formatLocalTime(checkIn.closes_at)}.`;
      } else {
        statusText = 'Check-in required before phase actions.';
      }
    }

    const canCheckIn = required
      && (side === 1 || side === 2)
      && !meReady
      && bool(checkIn.is_open, false)
      && !state.requestBusy;

    const buttonHtml = canCheckIn
      ? '<button type="button" data-action="check-in" class="px-4 py-2 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider active:scale-95 transition-transform">Check In</button>'
      : '';

    return `
      <section class="glass-card rounded-2xl p-4 md:p-5 border border-white/10">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-1">Entry Gate</p>
            <h3 class="text-sm md:text-base font-bold text-white">Participant Check-In</h3>
            <p class="text-xs text-gray-400 mt-1">${esc(statusText)}</p>
          </div>
          ${buttonHtml}
        </div>
        <div class="mt-4 grid grid-cols-2 gap-3">
          ${renderCheckInChip(1, p1Ready, sideOnline(1))}
          ${renderCheckInChip(2, p2Ready, sideOnline(2))}
        </div>
      </section>
    `;
  }

  function renderCheckInChip(side, checkedIn, online) {
    const participant = participantForSide(side);
    const name = String(participant.name || `Side ${side}`);
    const isLocalConnected = side === mySide() && state.wsConnected;
    const effectiveOnline = Boolean(online || isLocalConnected);
    const checkedText = checkedIn ? 'Ready' : (effectiveOnline ? 'Online' : 'Pending');
    const checkedClass = checkedIn
      ? 'text-green-300 border-green-400/30 bg-green-500/10'
      : (effectiveOnline
        ? 'text-cyan-200 border-cyan-400/25 bg-cyan-500/10'
        : 'text-amber-200 border-amber-400/20 bg-amber-500/10');
    const onlineClass = effectiveOnline ? 'bg-emerald-400' : 'bg-gray-600';

    return `
      <div class="rounded-xl border border-white/10 bg-black/35 p-3" data-check-chip-side="${esc(String(side))}">
        <div class="flex items-center justify-between">
          <p class="text-xs font-semibold text-white truncate">${esc(name)}</p>
          <span data-check-chip-dot="${esc(String(side))}" class="w-2.5 h-2.5 rounded-full ${onlineClass}"></span>
        </div>
        <p data-check-chip-label="${esc(String(side))}" class="mt-2 inline-flex px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${checkedClass}">${checkedText}</p>
      </div>
    `;
  }

  function refreshPresenceSurfaces() {
    renderHeaderPresenceMeta();
    renderCheckInPresenceChips();
    updateWaitingOverlay();

    const nextWaitingLocked = waitingLocked();
    if (nextWaitingLocked !== state.lastWaitingLocked) {
      state.lastWaitingLocked = nextWaitingLocked;
      renderEngine();
      return;
    }

    state.lastWaitingLocked = nextWaitingLocked;
  }

  function renderCheckInPresenceChips() {
    [1, 2].forEach(function (side) {
      const root = document.querySelector(`[data-check-chip-side="${side}"]`);
      if (!root) {
        return;
      }

      const checkedIn = sideCheckedIn(side);
      const online = sideOnline(side) || (side === mySide() && state.wsConnected);
      const label = checkedIn ? 'Ready' : (online ? 'Online' : 'Pending');
      const dotNode = root.querySelector(`[data-check-chip-dot="${side}"]`);
      const labelNode = root.querySelector(`[data-check-chip-label="${side}"]`);

      if (dotNode) {
        dotNode.className = `w-2.5 h-2.5 rounded-full ${online ? 'bg-emerald-400' : 'bg-gray-600'}`;
      }

      if (labelNode) {
        const checkedClass = checkedIn
          ? 'text-green-300 border-green-400/30 bg-green-500/10'
          : (online
            ? 'text-cyan-200 border-cyan-400/25 bg-cyan-500/10'
            : 'text-amber-200 border-amber-400/20 bg-amber-500/10');
        labelNode.className = `mt-2 inline-flex px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${checkedClass}`;
        labelNode.textContent = label;
      }
    });
  }

  function renderCoinTossBlock() {
    const workflow = asObject(state.room.workflow);
    const toss = asObject(workflow.coin_toss);
    const winnerSide = toInt(toss.winner_side, 0);
    const winnerLabel = winnerSide === 1 || winnerSide === 2 ? `Side ${winnerSide} won toss control.` : 'Toss not resolved yet.';

    const side = mySide();
    const canAct = (side === 1 || bool(asObject(state.room.me).is_staff, false))
      && !waitingLocked()
      && !state.requestBusy;

    return `
      <section class="glass-panel rounded-2xl p-6 md:p-8 border-t-4 border-ac">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Valorant Pipeline</p>
            <h3 class="text-xl md:text-2xl font-black text-white">Coin Toss</h3>
            <p class="text-xs text-gray-400 mt-2">Resolve first control before map veto starts.</p>
          </div>
          <button type="button" data-action="coin-toss" class="px-5 py-3 rounded-xl bg-white text-black text-xs font-black uppercase tracking-widest active:scale-95 transition-transform ${canAct ? '' : 'opacity-50 cursor-not-allowed'}" ${canAct ? '' : 'disabled'}>
            Resolve Toss
          </button>
        </div>
        <div class="mt-5 p-4 rounded-xl bg-black/40 border border-white/10">
          <p class="text-xs text-ac font-bold uppercase tracking-wide">${esc(winnerLabel)}</p>
          <p class="text-[11px] text-gray-400 mt-1">${esc(toss.performed_at ? `Updated ${shortClock(toss.performed_at)}` : 'Waiting for toss execution.')}</p>
        </div>
      </section>
    `;
  }

  function renderVetoBlock() {
    const workflow = asObject(state.room.workflow);
    const veto = asObject(workflow.veto);
    const sequence = asList(veto.sequence);
    const step = Math.max(0, toInt(veto.step, 0));
    const stepInfo = asObject(sequence[step]);
    const expectedSide = toInt(stepInfo.side, 0) || 1;
    const expectedAction = String(stepInfo.action || 'ban').toLowerCase() === 'pick' ? 'pick' : 'ban';

    const bans = new Set(asList(veto.bans).map((item) => String(item || '').trim()).filter(Boolean));
    const picks = new Set(asList(veto.picks).map((item) => String(item || '').trim()).filter(Boolean));
    const selectedMap = String(veto.selected_map || '').trim();
    const pool = mapPool();

    const side = mySide();
    const staff = bool(asObject(state.room.me).is_staff, false);
    const myTurn = staff || side === expectedSide;
    const actionLocked = waitingLocked() || state.requestBusy;

    const actionCopy = expectedAction === 'pick' ? 'Pick' : 'Ban';
    const statusCopy = step >= sequence.length
      ? (selectedMap ? `Veto complete. Selected map: ${selectedMap}.` : 'Veto sequence complete.')
      : `Turn: Side ${expectedSide} must ${actionCopy.toLowerCase()} a map.`;

    const cards = pool
      .map((mapName) => {
        const clean = String(mapName || '').trim();
        if (!clean) {
          return '';
        }

        const isBanned = bans.has(clean);
        const isPicked = picks.has(clean) || (selectedMap && clean === selectedMap);
        const selectable = !isBanned && !isPicked && step < sequence.length && myTurn && !actionLocked;

        const statusTag = isPicked ? 'Picked' : (isBanned ? 'Banned' : 'Available');
        const className = isPicked
          ? 'map-card picked'
          : (isBanned ? 'map-card banned' : 'map-card');

        const actionAttr = selectable
          ? `data-action="veto-map" data-map="${encodeURIComponent(clean)}"`
          : 'disabled';

        return `
          <button type="button" class="${className} text-left" ${actionAttr}>
            <div class="flex items-center justify-between gap-2">
              <span class="text-sm font-bold text-white">${esc(clean)}</span>
              <span class="text-[10px] uppercase tracking-widest ${isPicked ? 'text-ac' : (isBanned ? 'text-rose-300' : 'text-gray-400')}">${esc(statusTag)}</span>
            </div>
          </button>
        `;
      })
      .join('');

    const lastAction = asObject(veto.last_action);
    const lastActionText = lastAction.item
      ? `Last: Side ${toInt(lastAction.side, '?')} ${esc(String(lastAction.action || '').toLowerCase())}ed ${esc(lastAction.item)}.`
      : 'No veto actions recorded yet.';

    return `
      <section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
          <div>
            <p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Valorant Pipeline</p>
            <h3 class="text-xl md:text-2xl font-black text-white">Map Veto</h3>
          </div>
          <span class="text-xs ${myTurn ? 'text-ac' : 'text-rose-300'} font-bold uppercase tracking-wider">${esc(statusCopy)}</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          ${cards || '<p class="text-xs text-gray-400">No maps configured.</p>'}
        </div>

        <div class="mt-4 p-3 rounded-xl bg-black/40 border border-white/10">
          <p class="text-[11px] text-gray-300">${lastActionText}</p>
        </div>
      </section>
    `;
  }

  function renderDirectReadyBlock() {
    const workflow = asObject(state.room.workflow);
    const ready = asObject(workflow.direct_ready);
    const ready1 = bool(ready['1'], false);
    const ready2 = bool(ready['2'], false);

    const side = mySide();
    const meReady = side === 1 ? ready1 : (side === 2 ? ready2 : false);
    const canReady = (side === 1 || side === 2)
      && !meReady
      && !waitingLocked()
      && !state.requestBusy;

    return `
      <section class="glass-panel rounded-2xl p-6 md:p-8 border-t-4 border-ac">
        <p class="text-[10px] font-black uppercase tracking-widest text-gray-500">eFootball Pipeline</p>
        <h3 class="text-xl md:text-2xl font-black text-white">Direct Ready Check</h3>
        <p class="text-xs text-gray-400 mt-2">Both sides must confirm readiness before lobby credentials open.</p>

        <div class="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
          ${renderReadyChip(1, ready1)}
          ${renderReadyChip(2, ready2)}
        </div>

        <div class="mt-5 flex items-center justify-between gap-3 flex-wrap">
          <p class="text-xs text-gray-400">${ready1 && ready2 ? 'Both sides ready. Advancing to lobby setup.' : 'Waiting for both sides to confirm.'}</p>
          <button type="button" data-action="direct-ready" class="px-5 py-3 rounded-xl bg-ac text-black text-xs font-black uppercase tracking-widest active:scale-95 transition-transform ${canReady ? '' : 'opacity-50 cursor-not-allowed'}" ${canReady ? '' : 'disabled'}>
            Mark Ready
          </button>
        </div>
      </section>
    `;
  }

  function renderReadyChip(side, isReady) {
    const participant = participantForSide(side);
    const name = String(participant.name || `Side ${side}`);

    return `
      <div class="p-3 rounded-xl border border-white/10 bg-black/40">
        <p class="text-xs text-white font-semibold truncate">${esc(name)}</p>
        <p class="mt-2 inline-flex px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${isReady ? 'bg-green-500/15 border border-green-400/30 text-green-300' : 'bg-amber-500/15 border border-amber-400/30 text-amber-200'}">
          ${isReady ? 'Ready' : 'Pending'}
        </p>
      </div>
    `;
  }

  function renderLobbySetupBlock() {
    const workflow = asObject(state.room.workflow);
    const creds = asObject(workflow.credentials);
    const me = asObject(state.room.me);
    const host = participantForSide(1);
    const hostName = String(host.name || 'Host');
    const schema = credentialSchema();

    const isHost = bool(me.is_host, false);
    const canBroadcast = isHost;
    const canStartLive = bool(isHost || me.is_staff, false);
    const disabled = waitingLocked() || state.requestBusy;
    const fieldsHtml = schema
      .map((field) => renderCredentialField(field, creds, !canBroadcast))
      .join('');

    if (canBroadcast) {
      return `
        <section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">
          <p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Host Broadcast</p>
          <h3 class="text-xl md:text-2xl font-black text-white">Share Match Room Credentials</h3>
          <p class="text-xs text-gray-400 mt-2">You are Host (Side 1). Share room details when ready so both sides join the same match instance.</p>

          <form id="credentials-form" class="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">
            ${fieldsHtml}

            <div class="md:col-span-2 flex flex-wrap items-center justify-end gap-2 pt-1">
              <button type="submit" class="px-4 py-2.5 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider ${disabled ? 'opacity-50 cursor-not-allowed' : ''}" ${disabled ? 'disabled' : ''}>Share With Opponent</button>
              <button type="button" data-action="start-live" class="px-4 py-2.5 rounded-lg border border-white/25 text-xs font-bold uppercase tracking-wider text-white ${(!canStartLive || disabled) ? 'opacity-50 cursor-not-allowed' : ''}" ${(!canStartLive || disabled) ? 'disabled' : ''}>Mark Match Live</button>
            </div>
          </form>
        </section>
      `;
    }

    return `
      <section class="glass-panel rounded-2xl p-6 md:p-8 border-t-4 border-ac">
        <p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Guest View</p>
        <div class="flex flex-col items-center justify-center text-center py-4 md:py-8">
          <div class="relative w-14 h-14 mb-5">
            <div class="absolute inset-0 rounded-full border-4 border-white/10"></div>
            <div class="absolute inset-0 rounded-full border-4 border-t-transparent animate-spin border-ac"></div>
            <div class="absolute inset-0 flex items-center justify-center">
              <i data-lucide="radar" class="w-5 h-5 text-ac animate-pulse"></i>
            </div>
          </div>
          <h3 class="text-xl md:text-2xl font-black text-white">Awaiting Host Room Details</h3>
          <p class="text-xs md:text-sm text-gray-400 mt-2 max-w-md">${esc(hostName)} (Side 1) is setting up the room. Stay on this screen and details will appear automatically.</p>
        </div>
      </section>
    `;
  }

  function renderCredentialField(field, credentials, readonly) {
    const row = asObject(field);
    const key = String(row.key || '').trim();
    if (!key) {
      return '';
    }

    const id = credentialInputId(key);
    const label = String(row.label || credentialLabelForKey(key) || key);
    const value = String(credentials[key] || '');
    const multiline = String(row.kind || '').toLowerCase() === 'textarea' || key === 'notes';

    if (multiline) {
      return `
        <label class="text-xs text-gray-400 md:col-span-2">${esc(label)}
          <textarea id="${esc(id)}" class="lobby-input mt-1 min-h-[84px]" ${readonly ? 'readonly' : ''}>${esc(value)}</textarea>
        </label>
      `;
    }

    return `
      <label class="text-xs text-gray-400">${esc(label)}
        <input id="${esc(id)}" class="lobby-input mt-1" value="${esc(value)}" ${readonly ? 'readonly' : ''} />
      </label>
    `;
  }

  function renderLiveBlock() {
    const lobby = asObject(state.room.lobby);
    const creds = asObject(asObject(state.room.workflow).credentials);
    const schema = credentialSchema().filter((field) => String(asObject(field).key || '') !== 'notes');

    const cards = schema
      .map((field) => {
        const row = asObject(field);
        const key = String(row.key || '').trim();
        if (!key) {
          return '';
        }
        const label = String(row.label || credentialLabelForKey(key) || key);
        const value = String(lobby[key] || creds[key] || '');
        return liveInfoCard(label, value || 'Pending');
      })
      .filter(Boolean)
      .join('');

    let gridClass = 'grid grid-cols-1 md:grid-cols-2 gap-3';
    if (schema.length >= 3) {
      gridClass = 'grid grid-cols-1 md:grid-cols-3 gap-3';
    }
    if (schema.length >= 4) {
      gridClass = 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3';
    }

    return `
      <section class="glass-panel rounded-2xl p-6 md:p-8 border-t-4 border-green-500">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Match Runtime</p>
            <h3 class="text-2xl md:text-3xl font-black text-white">Live Match In Progress</h3>
            <p class="text-xs text-gray-400 mt-2">Play the match now. Result Desk unlocks for final score declaration in the next phase.</p>
          </div>
          <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-green-400/30 bg-green-500/10 text-green-200 text-[10px] font-black uppercase tracking-widest">
            <span class="live-pulse"></span>
            Match Live
          </div>
        </div>

        <div class="mt-5 ${gridClass}">
          ${cards || liveInfoCard('Lobby Code', lobby.lobby_code || 'Pending')}
        </div>
      </section>
    `;
  }

  function liveInfoCard(label, value) {
    return `
      <div class="p-3 rounded-xl border border-white/10 bg-black/40">
        <p class="text-[10px] font-black uppercase tracking-widest text-gray-500">${esc(label)}</p>
        <p class="text-sm text-white font-semibold mt-1 break-all">${esc(value)}</p>
      </div>
    `;
  }

  function renderResultsBlock(inlineAfterLive) {
    const side = mySide();
    const me = asObject(state.room.me);
    const visibility = workflowResultVisibility();
    const canSubmit = bool(me.can_submit_result, false) && (side === 1 || side === 2);
    const submission = side ? workflowSubmission(side) : null;
    const oppSubmission = side ? workflowSubmission(opponentSide()) : null;
    const hasSubmitted = Boolean(submission && (submission.submission_id || submission.submitted_at));

    const scoreFor = submission ? toInt(submission.score_for, 0) : 0;
    const scoreAgainst = submission ? toInt(submission.score_against, 0) : 0;
    const note = submission ? String(submission.note || '') : '';
    const proof = submission ? String(submission.proof_screenshot_url || '') : '';
    const evidenceRequired = requiresMatchEvidence();

    const prefix = inlineAfterLive ? 'Live Follow-up' : 'Result Desk';
    const header = inlineAfterLive ? 'Submit Result When Match Ends' : 'Result Submission';
    const blindCopy = bool(visibility.opponent_revealed, false)
      ? 'Admin view active. Opponent submission details are visible here.'
      : 'Blind mode is active. Opponent score is hidden from participants and visible to admins only.';
    const evidenceCopy = evidenceRequired
      ? 'Organizer policy requires an evidence image upload before score submission.'
      : 'Attach an evidence image if available. External proof URL is optional.';

    const myStatus = submission ? String(submission.status || 'submitted') : 'pending';
    const oppStatus = oppSubmission ? String(oppSubmission.status || 'submitted') : 'pending';
    const submitDisabled = !(canSubmit && !waitingLocked() && !state.requestBusy);
    const lockHint = hasSubmitted
      ? '<p class="mt-3 text-[11px] text-amber-200">Your result is locked after first submission. Contact admin for corrections.</p>'
      : '';

    return `
      <section class="glass-panel rounded-2xl p-5 md:p-7 ${inlineAfterLive ? 'border border-white/10' : 'border-t-4 border-ac'}">
        <p class="text-[10px] font-black uppercase tracking-widest text-gray-500">${esc(prefix)}</p>
        <h3 class="text-xl md:text-2xl font-black text-white">${esc(header)}</h3>
        <p class="text-xs text-gray-400 mt-2">${esc(blindCopy)}</p>
        <p class="text-[11px] text-gray-500 mt-1">${esc(evidenceCopy)}</p>

        <div class="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-4">
          <form id="result-submit-form" class="rounded-xl border border-white/10 bg-black/45 p-4">
            <div class="flex items-center justify-between">
              <p class="text-xs font-bold text-white">Your Submission</p>
              <span class="text-[10px] uppercase tracking-widest text-ac">${esc(myStatus)}</span>
            </div>

            <div class="mt-4 flex items-center gap-3">
              <label class="text-xs text-gray-400 flex-1">Your Score
                <input id="result-score-for" type="number" min="0" class="score-input mt-1" value="${esc(String(scoreFor))}" ${canSubmit ? '' : 'disabled'} />
              </label>
              <label class="text-xs text-gray-400 flex-1">Opponent Score
                <input id="result-score-against" type="number" min="0" class="score-input mt-1" value="${esc(String(scoreAgainst))}" ${canSubmit ? '' : 'disabled'} />
              </label>
            </div>

            <label class="block text-xs text-gray-400 mt-3">Evidence Image ${evidenceRequired ? '(required)' : '(optional)'}
              <input id="result-proof-file" type="file" accept="image/*" class="lobby-input mt-1 py-2.5" ${canSubmit ? (evidenceRequired ? 'required' : '') : 'disabled'} />
            </label>

            <label class="block text-xs text-gray-400 mt-3">Proof URL (optional)
              <input id="result-proof-url" class="lobby-input mt-1" value="${esc(proof)}" ${canSubmit ? '' : 'disabled'} />
            </label>

            ${proof ? `<p class="mt-2 text-[11px] text-gray-400">Current proof: <a class="text-ac underline" href="${esc(proof)}" target="_blank" rel="noopener">Open image</a></p>` : ''}

            <label class="block text-xs text-gray-400 mt-3">Note
              <textarea id="result-note" class="lobby-input mt-1 min-h-[72px]" ${canSubmit ? '' : 'disabled'}>${esc(note)}</textarea>
            </label>

            ${lockHint}

            <div class="mt-4 flex justify-end">
              <button type="submit" class="px-4 py-2.5 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider ${submitDisabled ? 'opacity-50 cursor-not-allowed' : ''}" ${submitDisabled ? 'disabled' : ''}>
                ${hasSubmitted ? 'Submitted' : 'Submit Result'}
              </button>
            </div>
          </form>

          <div class="rounded-xl border border-white/10 bg-black/45 p-4">
            <div class="flex items-center justify-between">
              <p class="text-xs font-bold text-white">Opponent Submission</p>
              <span class="text-[10px] uppercase tracking-widest text-amber-300">${esc(oppStatus)}</span>
            </div>
            ${renderOpponentSubmission(oppSubmission)}
            ${renderResultStatusBanner()}
          </div>
        </div>
      </section>
    `;
  }

  function renderOpponentSubmission(submission) {
    if (!submission) {
      return '<p class="text-xs text-gray-400 mt-4">Waiting for opponent submission.</p>';
    }

    const row = asObject(submission);
    const proof = String(row.proof_screenshot_url || '').trim();
    if (bool(row.blind_masked, false)) {
      return `
        <div class="mt-4 space-y-2">
          <p class="text-sm text-white font-semibold">Opponent has submitted.</p>
          <p class="text-xs text-gray-400">Score is hidden for participants. Only admin can view opponent score.</p>
          <p class="text-xs text-gray-500">Submitted at ${esc(shortClock(row.submitted_at))}</p>
        </div>
      `;
    }

    return `
      <div class="mt-4 space-y-2">
        <p class="text-sm text-white font-semibold">Score: ${esc(String(row.score_for || 0))} - ${esc(String(row.score_against || 0))}</p>
        <p class="text-xs text-gray-400">Submitted at ${esc(shortClock(row.submitted_at))}</p>
        ${proof ? `<p class="text-xs text-gray-400">Proof: <a class="text-ac underline" href="${esc(proof)}" target="_blank" rel="noopener">Open image</a></p>` : ''}
      </div>
    `;
  }

  function renderResultStatusBanner() {
    const workflow = asObject(state.room.workflow);
    const status = String(workflow.result_status || 'pending').toLowerCase();

    if (status === 'verified' || status === 'admin_overridden') {
      return '<p class="mt-4 px-3 py-2 rounded-lg bg-green-500/15 border border-green-400/30 text-xs text-green-300 font-bold uppercase tracking-wide">Result verified.</p>';
    }

    if (status === 'mismatch' || status === 'tie_pending_review' || status === 'admin_tie_pending_review') {
      return '<p class="mt-4 px-3 py-2 rounded-lg bg-amber-500/15 border border-amber-400/30 text-xs text-amber-200 font-bold uppercase tracking-wide">Awaiting staff review.</p>';
    }

    return '<p class="mt-4 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs text-gray-300 font-bold uppercase tracking-wide">Pending validation.</p>';
  }

  function renderCompletedBlock() {
    const workflow = asObject(state.room.workflow);
    const finalResult = asObject(workflow.final_result);
    const match = asObject(state.room.match);
    const urls = asObject(state.room.urls);

    const p1 = asObject(match.participant1);
    const p2 = asObject(match.participant2);

    const p1Score = toInt(finalResult.participant1_score, toInt(p1.score, 0));
    const p2Score = toInt(finalResult.participant2_score, toInt(p2.score, 0));
    const winnerSide = toInt(finalResult.winner_side, 0)
      || (toInt(match.winner_id, 0) === toInt(p1.id, -1) ? 1 : (toInt(match.winner_id, 0) === toInt(p2.id, -1) ? 2 : 0));

    const winnerText = winnerSide === 1
      ? `${p1.name || 'Side 1'} wins`
      : (winnerSide === 2 ? `${p2.name || 'Side 2'} wins` : 'Tie pending review');

    const bracketHref = String(urls.bracket || urls.match_detail || '#');
    const hubHref = String(urls.hub || urls.match_detail || '#');

    return `
      <section class="rounded-2xl p-5 md:p-7 border border-white/10 bg-gradient-to-br from-white/[0.08] via-white/[0.03] to-transparent backdrop-blur-xl">
        <p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Completed</p>
        <h3 class="text-2xl md:text-3xl font-black text-white">Result Locked</h3>
        <p class="text-xs text-gray-300 mt-2">${esc(winnerText)}</p>

        <div class="mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-green-400/30 bg-green-500/12 text-green-200 text-[10px] font-black uppercase tracking-widest">
          <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
          Match report archived
        </div>

        <div class="mt-5 grid grid-cols-3 gap-2 items-center max-w-md">
          <div class="p-3 rounded-xl bg-black/45 border border-white/10 text-center">
            <p class="text-[10px] text-gray-500 uppercase tracking-widest">${esc(String(p1.name || 'P1'))}</p>
            <p class="text-2xl font-black text-white mt-1">${esc(String(p1Score))}</p>
          </div>
          <div class="text-center text-gray-500 font-black">VS</div>
          <div class="p-3 rounded-xl bg-black/45 border border-white/10 text-center">
            <p class="text-[10px] text-gray-500 uppercase tracking-widest">${esc(String(p2.name || 'P2'))}</p>
            <p class="text-2xl font-black text-white mt-1">${esc(String(p2Score))}</p>
          </div>
        </div>

        <div class="mt-6 flex flex-wrap items-center gap-2">
          <a href="${esc(bracketHref)}" class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider hover:opacity-90 transition-opacity">
            <i data-lucide="git-branch" class="w-4 h-4"></i>
            View Bracket
          </a>
          <a href="${esc(hubHref)}" class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg border border-white/25 text-xs font-bold uppercase tracking-wider text-white hover:bg-white/10 transition-colors">
            <i data-lucide="house" class="w-4 h-4"></i>
            Back To Hub
          </a>
        </div>
      </section>
    `;
  }

  function renderFallbackBlock() {
    return `
      <section class="glass-panel rounded-2xl p-6 md:p-8 border border-white/10">
        <h3 class="text-lg font-bold text-white">Lobby state unavailable</h3>
        <p class="text-sm text-gray-400 mt-2">Refresh or wait for realtime sync to resume.</p>
        <button type="button" data-action="refresh-room" class="mt-4 px-4 py-2 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider">Refresh</button>
      </section>
    `;
  }

  function updateWaitingOverlay() {
    if (!elements.waitingOverlay) {
      return;
    }

    const side = mySide();
    const oppSide = opponentSide();

    if (side !== 1 || oppSide !== 2) {
      if (side !== 2 || oppSide !== 1) {
        elements.waitingOverlay.classList.add('overlay-hidden');
        return;
      }
    }

    if (bypassPresenceLock()) {
      elements.waitingOverlay.classList.add('overlay-hidden');
      return;
    }

    const meOnline = sideOnline(side) || state.wsConnected;
    const oppOnline = sideOnline(oppSide);
    const bothOnline = meOnline && oppOnline;
    const opponent = participantForSide(oppSide);

    ensureNoShowTicker();

    if (elements.waitingYouDot) {
      elements.waitingYouDot.className = `w-2.5 h-2.5 rounded-full ${meOnline ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.65)]' : 'bg-gray-600'}`;
    }

    if (elements.waitingOpponentDot) {
      elements.waitingOpponentDot.className = `w-2.5 h-2.5 rounded-full ${oppOnline ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.65)]' : 'bg-gray-600'}`;
    }

    if (elements.waitingOpponentName) {
      elements.waitingOpponentName.textContent = String(opponent.name || 'Opponent');
    }

    if (elements.waitingCopy) {
      if (bothOnline) {
        elements.waitingCopy.textContent = 'Both sides online. Lobby unlocked.';
      } else if (!meOnline) {
        elements.waitingCopy.textContent = 'Connecting your websocket presence...';
      } else {
        elements.waitingCopy.textContent = 'Waiting for opponent websocket presence.';
      }
    }

    if (bothOnline) {
      elements.waitingOverlay.classList.add('overlay-hidden');
    } else {
      elements.waitingOverlay.classList.remove('overlay-hidden');
    }
  }

  function updateSocketPill() {
    if (!elements.socketPill) {
      return;
    }

    const base = 'inline-flex items-center justify-center h-5 w-5 rounded-full border';

    if (state.wsConnected) {
      elements.socketPill.className = `${base} bg-green-500/10 border-green-400/30`;
      elements.socketPill.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>';
      elements.socketPill.setAttribute('title', 'Socket live');
      elements.socketPill.setAttribute('aria-label', 'Socket live');
      return;
    }

    if (state.reconnectTimer) {
      elements.socketPill.className = `${base} bg-amber-500/10 border-amber-400/35`;
      elements.socketPill.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-amber-300 animate-pulse"></span>';
      elements.socketPill.setAttribute('title', 'Socket reconnecting');
      elements.socketPill.setAttribute('aria-label', 'Socket reconnecting');
      return;
    }

    elements.socketPill.className = `${base} bg-red-500/10 border-red-400/35`;
    elements.socketPill.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-red-300"></span>';
    elements.socketPill.setAttribute('title', 'Socket offline');
    elements.socketPill.setAttribute('aria-label', 'Socket offline');
  }

  function bindStaticEvents() {
    if (elements.chatForm) {
      elements.chatForm.addEventListener('submit', function (event) {
        event.preventDefault();
        submitChat(elements.chatInput);
      });
    }

    if (elements.dtTabChat) {
      elements.dtTabChat.addEventListener('click', function () {
        setDesktopTab('chat');
      });
    }
    if (elements.dtTabIntel) {
      elements.dtTabIntel.addEventListener('click', function () {
        setDesktopTab('intel');
      });
    }
    if (elements.dtTabAdmin) {
      elements.dtTabAdmin.addEventListener('click', function () {
        setDesktopTab('admin');
      });
    }

    if (elements.mobTabEngine) {
      elements.mobTabEngine.addEventListener('click', function () {
        setMobileTab('engine');
      });
    }
    if (elements.mobTabChat) {
      elements.mobTabChat.addEventListener('click', function () {
        setMobileTab('chat');
      });
    }
    if (elements.mobTabIntel) {
      elements.mobTabIntel.addEventListener('click', function () {
        setMobileTab('intel');
      });
    }

    if (elements.adminForceNext) {
      elements.adminForceNext.addEventListener('click', handleAdminForceNext);
    }
    if (elements.adminOpenOverride) {
      elements.adminOpenOverride.addEventListener('click', openOverrideModal);
    }
    if (elements.adminBroadcast) {
      elements.adminBroadcast.addEventListener('click', handleAdminBroadcast);
    }

    if (elements.overrideClose) {
      elements.overrideClose.addEventListener('click', closeOverrideModal);
    }
    if (elements.overrideCancel) {
      elements.overrideCancel.addEventListener('click', closeOverrideModal);
    }
    if (elements.overrideApply) {
      elements.overrideApply.addEventListener('click', applyOverrideResult);
    }

    if (elements.helpSignalBtn) {
      elements.helpSignalBtn.addEventListener('click', function () {
        signalReferee();
      });
    }

    if (elements.engineContainer) {
      elements.engineContainer.addEventListener('click', handleEngineClick);
      elements.engineContainer.addEventListener('submit', handleEngineSubmit);
    }

    document.addEventListener('visibilitychange', function () {
      if (state.wsConnected) {
        sendSocket({ type: 'presence_ping', status: document.hidden ? 'away' : 'online' });
      }
    });

    window.addEventListener('beforeunload', function () {
      setGlobalFocusMode(false);
    });
  }

  function setDesktopTab(tab) {
    const allowed = ['chat', 'intel', 'admin'];
    let next = allowed.includes(tab) ? tab : 'chat';

    if (next === 'admin' && !bool(asObject(state.room.me).admin_mode, false)) {
      next = 'chat';
    }

    state.activeDesktopTab = next;

    const configs = [
      { key: 'chat', panel: elements.sideChat, button: elements.dtTabChat, adminStyle: false },
      { key: 'intel', panel: elements.sideIntel, button: elements.dtTabIntel, adminStyle: false },
      { key: 'admin', panel: elements.sideAdmin, button: elements.dtTabAdmin, adminStyle: true },
    ];

    configs.forEach(function (cfg) {
      if (cfg.panel) {
        cfg.panel.classList.add('hidden-state');
      }
      if (cfg.button) {
        cfg.button.classList.remove('text-ac', 'text-yellow-300', 'border-ac');
        cfg.button.classList.add('text-gray-500');
        cfg.button.style.borderBottomColor = 'transparent';
      }
    });

    const active = configs.find((cfg) => cfg.key === next);
    if (active) {
      if (active.panel) {
        active.panel.classList.remove('hidden-state');
      }
      if (active.button) {
        active.button.classList.remove('text-gray-500');
        active.button.classList.add(active.adminStyle ? 'text-yellow-300' : 'text-ac');
        active.button.style.borderBottomColor = active.adminStyle ? '#fcd34d' : 'var(--ac)';
      }
    }
  }

  function setMobileTab(tab) {
    const target = MOBILE_TABS.includes(tab) ? tab : 'engine';
    state.activeMobileTab = target;

    MOBILE_TABS.forEach(function (key) {
      const btn = byId(`mob-tab-${key}`);
      if (!btn) {
        return;
      }
      btn.classList.remove('text-ac');
      btn.classList.add('text-gray-500');
    });

    const active = byId(`mob-tab-${target}`);
    if (active) {
      active.classList.remove('text-gray-500');
      active.classList.add('text-ac');
    }

    if (target === 'engine') {
      if (elements.mobilePanelOverlay) {
        elements.mobilePanelOverlay.classList.add('hidden-state');
      }
      if (elements.mainScroll) {
        elements.mainScroll.style.display = '';
      }
      setMobileTopNavHidden(false);
      return;
    }

    if (elements.mainScroll) {
      elements.mainScroll.style.display = 'none';
    }

    if (elements.mobilePanelOverlay) {
      elements.mobilePanelOverlay.classList.remove('hidden-state');
    }

    updateMobileOverlayTopOffset();

    if (!elements.mobilePanelContent) {
      return;
    }

    if (target === 'chat') {
      renderMobileChat();
    } else {
      renderMobileIntel();
    }

    maybeRunIcons();
  }

  function renderMobileChat() {
    if (!elements.mobilePanelContent) {
      return;
    }

    const desktopHtml = elements.chatWindow ? elements.chatWindow.innerHTML : '';

    elements.mobilePanelContent.innerHTML = `
      <div class="flex-1 flex flex-col h-full">
        <div id="mobile-chat-window" class="flex-1 overflow-y-auto p-5 space-y-4 hide-scroll">${desktopHtml}</div>
        <div class="p-4 bg-black/50 border-t border-white/10">
          <form id="mobile-chat-form" class="relative">
            <input id="mobile-chat-input" type="text" placeholder="Message opponent..." class="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-4 pr-12 text-sm text-white focus:outline-none focus:border-ac" />
            <button type="submit" class="absolute right-2 top-2 p-1.5 bg-ac-subtle text-ac rounded-lg"><i data-lucide="send" class="w-4 h-4"></i></button>
          </form>
        </div>
      </div>
    `;

    const form = byId('mobile-chat-form');
    const input = byId('mobile-chat-input');
    if (form) {
      form.addEventListener('submit', function (event) {
        event.preventDefault();
        submitChat(input);
      });
    }

    syncMobileMirror();
  }

  function renderMobileIntel() {
    if (!elements.mobilePanelContent) {
      return;
    }
    const intelHtml = elements.rulesList ? elements.rulesList.innerHTML : '';

    elements.mobilePanelContent.innerHTML = `
      <div class="flex-1 overflow-y-auto p-5 hide-scroll">
        <h3 class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-4">Match Rules</h3>
        <div class="space-y-3">${intelHtml}</div>
      </div>
    `;
  }

  function syncMobileMirror() {
    if (state.activeMobileTab !== 'chat') {
      return;
    }

    const desktop = elements.chatWindow;
    const mobile = byId('mobile-chat-window');
    if (!desktop || !mobile) {
      return;
    }

    mobile.innerHTML = desktop.innerHTML;
    mobile.scrollTop = mobile.scrollHeight;
  }

  async function handleEngineClick(event) {
    const trigger = event.target.closest('[data-action]');
    if (!trigger) {
      return;
    }

    const action = String(trigger.getAttribute('data-action') || '');
    if (!action) {
      return;
    }

    if (action === 'check-in') {
      await handleCheckIn();
      return;
    }

    if (action === 'coin-toss') {
      await sendWorkflowAction('coin_toss', {});
      return;
    }

    if (action === 'veto-map') {
      const encoded = String(trigger.getAttribute('data-map') || '');
      const mapName = encoded ? decodeURIComponent(encoded) : '';
      if (!mapName) {
        return;
      }
      await sendWorkflowAction('veto_action', { item: mapName });
      return;
    }

    if (action === 'direct-ready') {
      await sendWorkflowAction('direct_ready', { ready: true });
      return;
    }

    if (action === 'start-live') {
      await sendWorkflowAction('start_live', {});
      return;
    }

    if (action === 'refresh-room') {
      await refreshRoom();
    }
  }

  async function handleEngineSubmit(event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }

    if (form.id === 'credentials-form') {
      event.preventDefault();
      await handleSaveCredentials();
      return;
    }

    if (form.id === 'result-submit-form') {
      event.preventDefault();
      await handleSubmitResult();
    }
  }

  async function handleSaveCredentials() {
    const payload = {};
    credentialSchema().forEach(function (field) {
      const row = asObject(field);
      const key = String(row.key || '').trim();
      if (!key) {
        return;
      }
      payload[key] = valueOf(credentialInputId(key));
    });

    await sendWorkflowAction('save_credentials', payload);
  }

  async function handleSubmitResult() {
    const scoreForRaw = valueOf('result-score-for');
    const scoreAgainstRaw = valueOf('result-score-against');

    const scoreFor = toInt(scoreForRaw, -1);
    const scoreAgainst = toInt(scoreAgainstRaw, -1);

    if (scoreFor < 0 || scoreAgainst < 0) {
      showToast('Scores must be non-negative integers.', 'error');
      return;
    }

    const proofFileInput = byId('result-proof-file');
    const proofFile = proofFileInput && proofFileInput.files && proofFileInput.files.length
      ? proofFileInput.files[0]
      : null;
    const proofUrl = valueOf('result-proof-url');

    if (requiresMatchEvidence() && !proofFile) {
      showToast('Evidence image is required before submitting.', 'error');
      return;
    }

    if (proofFile && !String(proofFile.type || '').toLowerCase().startsWith('image/')) {
      showToast('Only image files are allowed for evidence upload.', 'error');
      return;
    }

    if (proofFile && Number(proofFile.size || 0) > (10 * 1024 * 1024)) {
      showToast('Evidence image exceeds 10MB limit.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('action', 'submit_result');
    formData.append('score_for', String(scoreFor));
    formData.append('score_against', String(scoreAgainst));
    formData.append('note', valueOf('result-note'));
    if (proofUrl) {
      formData.append('proof_screenshot_url', proofUrl);
    }
    if (proofFile) {
      formData.append('proof', proofFile);
    }

    await sendWorkflowMultipartAction(formData);
  }

  function valueOf(id) {
    const node = byId(id);
    if (!node) {
      return '';
    }
    return String(node.value || '').trim();
  }

  async function handleCheckIn() {
    if (state.requestBusy) {
      return;
    }

    const endpoint = String(asObject(state.room.urls).check_in || '');
    if (!endpoint) {
      showToast('Check-in endpoint unavailable.', 'error');
      return;
    }

    state.requestBusy = true;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      const data = await parseJsonResponse(response);
      if (!response.ok || !bool(data.success, false)) {
        throw new Error(String(data.error || 'Check-in failed.'));
      }

      if (data.room && typeof data.room === 'object') {
        applyRoom(data.room);
      }

      if (bool(data.checked_in, false)) {
        showToast('Check-in complete.', 'success');
      } else if (bool(data.already_checked_in, false)) {
        showToast('Already checked in.', 'info');
      }
    } catch (error) {
      showToast(String(error && error.message ? error.message : 'Check-in failed.'), 'error');
    } finally {
      state.requestBusy = false;
      renderEngine();
    }
  }

  async function signalReferee() {
    if (bool(asObject(state.room.me).is_staff, false)) {
      showToast('Use TOC verification panel for organizer dispute actions.', 'info');
      return;
    }

    const summaryRaw = window.prompt('SOS headline', 'Opponent disconnected / technical issue');
    if (summaryRaw === null) {
      return;
    }

    const summary = String(summaryRaw || '').trim();
    if (summary.length < 3) {
      showToast('SOS headline must be at least 3 characters.', 'error');
      return;
    }

    const descriptionRaw = window.prompt('Describe the issue for TOC support (minimum 10 characters).');
    if (descriptionRaw === null) {
      return;
    }

    const description = String(descriptionRaw || '').trim();
    if (description.length < 10) {
      showToast('Description must be at least 10 characters.', 'error');
      return;
    }

    const matchRef = String(asObject(state.room.match).id || '');
    let supportSent = false;
    let supportMessage = 'Support alert sent.';

    try {
      supportMessage = await submitSupportTicket(summary, description, matchRef);
      supportSent = true;
    } catch (_err) {
      supportSent = false;
    }

    let disputeFallbackSent = false;
    if (!supportSent) {
      disputeFallbackSent = await notifyDisputeFallback(summary, description);
    }

    if (supportSent || disputeFallbackSent) {
      showToast(supportSent ? supportMessage : 'Support alert sent via dispute channel.', 'success');
      appendSystemChat('SOS alert sent to tournament support.');
      return;
    }

    showToast('Failed to notify support. Please retry.', 'error');
  }

  async function submitSupportTicket(summary, description, matchRef) {
    const supportUrl = String(asObject(state.room.urls).support || '');
    if (!supportUrl) {
      throw new Error('Support channel unavailable.');
    }

    const matchId = matchRef || String(asObject(state.room.match).id || 'N/A');
    const body = {
      category: 'technical',
      subject: `SOS Match ${matchId}: ${summary}`,
      message: description,
      match_ref: String(matchId),
    };

    const response = await fetch(supportUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(body),
    });

    const data = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(String(data.error || 'Support request failed.'));
    }

    return String(data.message || 'Support ticket sent to TOC.');
  }

  async function notifyDisputeFallback(summary, description) {
    const reportUrl = String(asObject(state.room.urls).report_dispute || '');
    if (!reportUrl) {
      return false;
    }

    const body = new URLSearchParams();
    body.set('reason', deriveDisputeReason(summary));
    body.set('description', description);

    try {
      const response = await fetch(reportUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: body.toString(),
      });

      const data = await parseJsonResponse(response);
      if (!response.ok || !bool(data.success, false)) {
        return false;
      }

      return true;
    } catch (_error) {
      return false;
    }
  }

  function deriveDisputeReason(summary) {
    const token = String(summary || '').toLowerCase();
    if (token.includes('score') || token.includes('mismatch') || token.includes('result')) {
      return 'score_mismatch';
    }
    if (token.includes('disconnect') || token.includes('lag') || token.includes('tech')) {
      return 'technical_issue';
    }
    return 'other';
  }

  async function sendWorkflowAction(action, payload) {
    if (state.requestBusy) {
      return;
    }

    if (waitingLocked() && action !== 'presence_ping') {
      showToast('Waiting for opponent websocket presence.', 'info');
      return;
    }

    const endpoint = String(asObject(state.room.urls).workflow || '');
    if (!endpoint) {
      showToast('Workflow endpoint unavailable.', 'error');
      return;
    }

    state.requestBusy = true;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify(Object.assign({ action }, asObject(payload))),
      });

      const data = await parseJsonResponse(response);
      if (!response.ok || !bool(data.success, false)) {
        throw new Error(String(data.error || 'Action failed.'));
      }

      if (data.room && typeof data.room === 'object') {
        applyRoom(data.room);
      }

      if (data.message) {
        appendSystemChat(String(data.message));
        showToast(String(data.message), 'success');
      }
    } catch (error) {
      showToast(String(error && error.message ? error.message : 'Action failed.'), 'error');
    } finally {
      state.requestBusy = false;
      renderEngine();
    }
  }

  async function sendWorkflowMultipartAction(formData) {
    if (state.requestBusy) {
      return;
    }

    if (waitingLocked()) {
      showToast('Waiting for opponent websocket presence.', 'info');
      return;
    }

    const endpoint = String(asObject(state.room.urls).workflow || '');
    if (!endpoint) {
      showToast('Workflow endpoint unavailable.', 'error');
      return;
    }

    state.requestBusy = true;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: formData,
      });

      const data = await parseJsonResponse(response);
      if (!response.ok || !bool(data.success, false)) {
        throw new Error(String(data.error || 'Action failed.'));
      }

      if (data.room && typeof data.room === 'object') {
        applyRoom(data.room);
      }

      if (data.message) {
        appendSystemChat(String(data.message));
        showToast(String(data.message), 'success');
      }
    } catch (error) {
      showToast(String(error && error.message ? error.message : 'Action failed.'), 'error');
    } finally {
      state.requestBusy = false;
      renderEngine();
    }
  }

  async function refreshRoom() {
    const endpoint = String(asObject(state.room.urls).workflow || '');
    if (!endpoint) {
      return;
    }

    try {
      const response = await fetch(endpoint, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      const data = await parseJsonResponse(response);
      if (!response.ok || !bool(data.success, false)) {
        return;
      }

      if (data.room && typeof data.room === 'object') {
        applyRoom(data.room);
      }
    } catch (_err) {
      // Keep fallback sync silent.
    }
  }

  function parseJsonResponse(response) {
    return response
      .text()
      .then(function (text) {
        try {
          return JSON.parse(text || '{}');
        } catch (_err) {
          return {};
        }
      });
  }

  function connectSocket() {
    const path = String(asObject(state.room.websocket).path || '');
    if (!path) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${protocol}://${window.location.host}${path}`;

    clearReconnectTimer();

    try {
      state.ws = new window.WebSocket(url);
    } catch (_err) {
      scheduleReconnect();
      return;
    }

    state.ws.addEventListener('open', function () {
      state.wsConnected = true;
      state.reconnectAttempts = 0;
      state.localPresenceHoldUntilMs = nowMs() + 12000;
      updateSocketPill();
      sendSocket({ type: 'subscribe' });
      sendSocket({ type: 'presence_ping', status: document.hidden ? 'away' : 'online' });
      updatePresenceLocal(mySide(), true, 'online');
      renderHeaderPresenceMeta();
      refreshPresenceSurfaces();
      showToast('Socket connected.', 'success');
    });

    state.ws.addEventListener('message', function (event) {
      let data = {};
      try {
        data = JSON.parse(event.data || '{}');
      } catch (_err) {
        data = {};
      }

      handleSocketMessage(data);
    });

    state.ws.addEventListener('close', function () {
      state.wsConnected = false;
      updateSocketPill();
      updatePresenceLocal(mySide(), false, 'offline');
      renderHeaderPresenceMeta();
      refreshPresenceSurfaces();
      scheduleReconnect();
    });

    state.ws.addEventListener('error', function () {
      // close handler manages reconnect flow.
    });
  }

  function sendSocket(payload) {
    if (!state.ws || state.ws.readyState !== window.WebSocket.OPEN) {
      return;
    }

    try {
      state.ws.send(JSON.stringify(payload));
    } catch (_err) {
      // swallow and rely on reconnect path
    }
  }

  function handleSocketMessage(message) {
    const type = String(message.type || '');

    if (type === 'ping') {
      sendSocket({ type: 'pong', timestamp: message.timestamp || null });
      return;
    }

    if (type === 'connection_established') {
      return;
    }

    if (type === 'presence_synced') {
      return;
    }

    if (type === 'match_presence') {
      const payload = asObject(message.data);
      const sides = asObject(payload.sides);
      const normalized = applyLocalPresenceHold(resolvePresence(sides, state.room.match));
      state.socketPresence = normalized;
      state.room.presence = normalized;
      state.room.workflow.presence = normalized;
      refreshPresenceSurfaces();
      return;
    }

    if (type === 'match_room_event') {
      const data = asObject(message.data);
      const payload = asObject(data.payload);

      if (payload.room && typeof payload.room === 'object') {
        applyRoom(payload.room);
      }

      if (payload.message) {
        appendSystemChat(String(payload.message));
        showToast(String(payload.message), 'info');
      }
      return;
    }

    if (type === 'match_chat') {
      const data = asObject(message.data);
      appendChatBubble(data);
      return;
    }

    if (type === 'error') {
      const code = String(message.code || 'error');
      const text = String(message.message || code || 'Socket error');
      showToast(text, 'error');
    }
  }

  function applyLocalPresenceHold(snapshotValue) {
    const snapshot = resolvePresence(snapshotValue, state.room.match);
    const side = mySide();
    if (side !== 1 && side !== 2) {
      return snapshot;
    }

    const key = String(side);
    const row = asObject(snapshot[key]);
    if (bool(row.online, false)) {
      state.localPresenceHoldUntilMs = 0;
      return snapshot;
    }

    const shouldHold = state.wsConnected && nowMs() <= state.localPresenceHoldUntilMs;
    if (!shouldHold) {
      return snapshot;
    }

    snapshot[key] = Object.assign({}, row, {
      online: true,
      status: document.hidden ? 'away' : 'online',
      user_id: row.user_id || asObject(state.room.me).user_id || null,
      last_seen: new Date().toISOString(),
    });

    return snapshot;
  }

  function updatePresenceLocal(side, online, status) {
    if (side !== 1 && side !== 2) {
      return;
    }
    if (online) {
      state.localPresenceHoldUntilMs = Math.max(state.localPresenceHoldUntilMs, nowMs() + 10000);
    }
    const key = String(side);
    if (!state.socketPresence || typeof state.socketPresence !== 'object') {
      state.socketPresence = { '1': normalizePresenceSide({}), '2': normalizePresenceSide({}) };
    }
    const socketRow = asObject(state.socketPresence[key]);
    socketRow.online = !!online;
    socketRow.status = online ? (status === 'away' ? 'away' : 'online') : 'offline';
    socketRow.last_seen = new Date().toISOString();
    socketRow.checked_in = sideCheckedIn(side);
    state.socketPresence[key] = socketRow;

    const row = asObject(state.room.presence[key]);
    row.online = !!online;
    row.status = online ? (status === 'away' ? 'away' : 'online') : 'offline';
    row.last_seen = new Date().toISOString();
    state.room.presence[key] = row;
    state.room.workflow.presence[key] = row;
  }

  function scheduleReconnect() {
    if (state.reconnectTimer) {
      return;
    }

    state.reconnectAttempts += 1;
    const delayMs = Math.min(20000, 1000 * Math.max(1, state.reconnectAttempts));

    state.reconnectTimer = window.setTimeout(function () {
      state.reconnectTimer = null;
      connectSocket();
    }, delayMs);

    updateSocketPill();
  }

  function clearReconnectTimer() {
    if (!state.reconnectTimer) {
      return;
    }
    window.clearTimeout(state.reconnectTimer);
    state.reconnectTimer = null;
  }

  function startPresenceHeartbeat() {
    if (state.presenceTimer) {
      window.clearInterval(state.presenceTimer);
    }

    state.presenceTimer = window.setInterval(function () {
      if (state.wsConnected) {
        sendSocket({ type: 'presence_ping', status: document.hidden ? 'away' : 'online' });
      }
    }, 15000);
  }

  function startFallbackSync() {
    if (state.fallbackSyncTimer) {
      window.clearInterval(state.fallbackSyncTimer);
    }

    state.fallbackSyncTimer = window.setInterval(function () {
      if (!state.wsConnected) {
        refreshRoom();
      }
    }, 20000);
  }

  function submitChat(inputNode) {
    const input = inputNode;
    if (!input) {
      return;
    }

    const text = String(input.value || '').trim();
    if (!text) {
      return;
    }

    if (!state.wsConnected) {
      showToast('Socket is offline. Cannot send chat right now.', 'error');
      return;
    }

    sendSocket({ type: 'chat_message', text });
    input.value = '';
  }

  function clearChatEmptyState() {
    const rows = document.querySelectorAll('#chat-empty-state');
    rows.forEach(function (node) {
      if (node && node.parentNode) {
        node.parentNode.removeChild(node);
      }
    });
  }

  function renderChatAvatar(payload, mine, sideToken, isOfficial) {
    const side = toInt(payload.side, 0);
    const avatarUrl = String(payload.avatar_url || '').trim();

    if (isOfficial) {
      return '<div class="w-8 h-8 rounded-lg border border-amber-300/45 bg-amber-500/15 text-amber-200 flex items-center justify-center shrink-0"><i data-lucide="shield-check" class="w-4 h-4"></i></div>';
    }

    if (avatarUrl) {
      return `<div class="w-8 h-8 rounded-lg overflow-hidden border border-white/20 shrink-0"><img src="${esc(avatarUrl)}" alt="${esc(String(payload.username || 'Participant'))}" class="w-full h-full object-cover" loading="lazy" /></div>`;
    }

    const tone = mine
      ? 'bg-ac-subtle text-ac border-ac-subtle'
      : (side === 1
        ? 'bg-cyan-500/20 text-cyan-200 border-cyan-400/30'
        : 'bg-rose-500/20 text-rose-200 border-rose-400/30');

    return `<div class="w-8 h-8 rounded-lg ${tone} border flex items-center justify-center text-xs font-black shrink-0">${esc(sideToken)}</div>`;
  }

  function appendChatBubble(payload) {
    if (!elements.chatWindow) {
      return;
    }

    const messageId = String(payload.message_id || `${payload.user_id || 'u'}:${payload.timestamp || nowMs()}`);
    if (state.chatIds.has(messageId)) {
      return;
    }
    state.chatIds.add(messageId);

    const mine = toInt(payload.user_id, -1) === toInt(asObject(state.room.me).user_id, -2);
    const isOfficial = bool(payload.is_staff, false) || String(payload.persona || '').toLowerCase() === 'organizer';
    const username = String(payload.display_name || payload.username || (isOfficial ? 'Organizer' : 'Player'));
    const text = String(payload.text || '').trim();
    if (!text) {
      return;
    }

    clearChatEmptyState();

    const sideToken = initials(username);
    const stamp = shortClock(payload.timestamp);
    const avatar = renderChatAvatar(payload, mine, sideToken, isOfficial);
    const staffTag = isOfficial
      ? '<span class="inline-flex items-center gap-1 ml-1 px-1.5 py-0.5 rounded-full border border-amber-300/35 bg-amber-500/12 text-[8px] font-black uppercase tracking-widest text-amber-200"><i data-lucide="shield-check" class="w-2.5 h-2.5"></i>Organizer</span>'
      : '';

    const bubbleToneMine = isOfficial
      ? 'bg-amber-500/15 border border-amber-300/35 text-amber-50'
      : 'bg-white/10 border border-white/10 text-white';
    const bubbleToneOther = isOfficial
      ? 'bg-amber-500/12 border border-amber-300/30 text-amber-50'
      : 'bg-black/55 border border-white/10 text-white';

    const bubble = mine
      ? `
        <div class="flex gap-3 flex-row-reverse text-right" data-chat-entry="1">
          ${avatar}
          <div class="max-w-[85%] flex flex-col items-end">
            <span class="text-[9px] font-bold text-gray-500 mb-1">${esc(username)}${staffTag} - ${esc(stamp)}</span>
            <p class="text-sm px-4 py-2.5 rounded-2xl rounded-tr-sm break-words ${bubbleToneMine}">${esc(text)}</p>
          </div>
        </div>
      `
      : `
        <div class="flex gap-3" data-chat-entry="1">
          ${avatar}
          <div class="max-w-[85%] flex flex-col items-start">
            <span class="text-[9px] font-bold text-gray-500 mb-1">${esc(username)}${staffTag} - ${esc(stamp)}</span>
            <p class="text-sm px-4 py-2.5 rounded-2xl rounded-tl-sm break-words ${bubbleToneOther}">${esc(text)}</p>
          </div>
        </div>
      `;

    elements.chatWindow.insertAdjacentHTML('beforeend', bubble);
    elements.chatWindow.scrollTop = elements.chatWindow.scrollHeight;
    maybeRunIcons();
    syncMobileMirror();
  }

  function appendSystemChat(text) {
    if (!elements.chatWindow) {
      return;
    }

    const content = String(text || '').trim();
    if (!content) {
      return;
    }

    clearChatEmptyState();

    elements.chatWindow.insertAdjacentHTML(
      'beforeend',
      `<div class="flex justify-center my-2" data-chat-system="1"><span class="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[9px] font-black uppercase tracking-widest text-ac text-center">${esc(content)}</span></div>`
    );

    elements.chatWindow.scrollTop = elements.chatWindow.scrollHeight;
    syncMobileMirror();
  }

  function processAnnouncements() {
    const announcements = asList(asObject(state.room.workflow).announcements);
    if (!announcements.length) {
      return;
    }

    announcements.forEach(function (item) {
      const row = asObject(item);
      const key = `${String(row.at || '')}:${String(row.message || '')}`;
      if (!key || state.seenAnnouncements.has(key)) {
        return;
      }

      state.seenAnnouncements.add(key);
      appendSystemChat(String(row.message || 'System announcement'));
    });
  }

  async function handleAdminForceNext() {
    const me = asObject(state.room.me);
    if (!bool(me.admin_mode, false)) {
      showToast('Admin mode required.', 'error');
      return;
    }

    const order = phaseOrder();
    const current = currentPhase();
    const index = order.indexOf(current);

    if (index < 0 || index + 1 >= order.length) {
      showToast('No next phase available.', 'info');
      return;
    }

    await sendWorkflowAction('advance_phase', { phase: order[index + 1] });
  }

  async function handleAdminBroadcast() {
    const me = asObject(state.room.me);
    if (!bool(me.admin_mode, false)) {
      showToast('Admin mode required.', 'error');
      return;
    }

    const message = window.prompt('System announcement message:');
    if (!message || !String(message).trim()) {
      return;
    }

    await sendWorkflowAction('system_announcement', { message: String(message).trim() });
  }

  function openOverrideModal() {
    const me = asObject(state.room.me);
    if (!bool(me.admin_mode, false)) {
      showToast('Admin mode required.', 'error');
      return;
    }

    const match = asObject(state.room.match);

    if (elements.overrideP1) {
      elements.overrideP1.value = String(toInt(asObject(match.participant1).score, 0));
    }
    if (elements.overrideP2) {
      elements.overrideP2.value = String(toInt(asObject(match.participant2).score, 0));
    }
    if (elements.overrideNote) {
      elements.overrideNote.value = '';
    }

    if (elements.overrideModal) {
      elements.overrideModal.classList.remove('hidden-state');
      elements.overrideModal.classList.add('flex');
    }
  }

  function closeOverrideModal() {
    if (!elements.overrideModal) {
      return;
    }
    elements.overrideModal.classList.add('hidden-state');
    elements.overrideModal.classList.remove('flex');
  }

  async function applyOverrideResult() {
    const p1 = toInt(elements.overrideP1 ? elements.overrideP1.value : '', -1);
    const p2 = toInt(elements.overrideP2 ? elements.overrideP2.value : '', -1);

    if (p1 < 0 || p2 < 0) {
      showToast('Override scores must be >= 0.', 'error');
      return;
    }

    const note = elements.overrideNote ? String(elements.overrideNote.value || '').trim() : '';

    await sendWorkflowAction('admin_override_result', {
      participant1_score: p1,
      participant2_score: p2,
      note,
    });

    closeOverrideModal();
  }

  function showToast(message, kind) {
    if (!elements.roomToast) {
      return;
    }

    const text = String(message || '').trim();
    if (!text) {
      return;
    }

    const now = nowMs();
    if (state.lastToastText === text && now - state.lastToastAt < 1500) {
      return;
    }

    state.lastToastText = text;
    state.lastToastAt = now;

    const color = kind === 'error'
      ? 'border-red-400/40 text-red-100'
      : (kind === 'success'
        ? 'border-green-400/40 text-green-100'
        : 'border-white/20 text-white');

    const toast = document.createElement('div');
    toast.className = `opacity-0 translate-y-2 transition-all duration-300 ${color}`;
    toast.innerHTML = `<div class="rounded-xl px-4 py-3 bg-black/85 border ${color} text-sm font-semibold">${esc(text)}</div>`;

    elements.roomToast.appendChild(toast);

    window.requestAnimationFrame(function () {
      toast.classList.remove('opacity-0', 'translate-y-2');
    });

    window.setTimeout(function () {
      toast.classList.add('opacity-0', 'translate-y-2');
      window.setTimeout(function () {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 280);
    }, 3200);
  }
})();
