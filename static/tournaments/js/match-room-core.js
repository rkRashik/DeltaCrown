/**
 * match-room-core.js — Lightweight Match Room Orchestrator
 *
 * Responsibilities:
 *   1. Bootstrap: parse payload, init state, cache DOM elements
 *   2. WebSocket lifecycle: connect, reconnect, heartbeat, close-code mapping
 *   3. Phase registry: dynamic phase-module loading via MatchRoom.registerPhase()
 *   4. Targeted re-rendering: selective DOM updates per event type
 *   5. Timer lifecycle: beforeunload / pagehide cleanup
 *
 * Phase modules register themselves via:
 *   window.MatchRoom.registerPhase('coin_toss', { render, onAction, label, narrative });
 *
 * The orchestrator invokes the active phase module's render() and routes
 * engine click/submit events to the active module's onAction().
 */
(function () {
  'use strict';

  // ── Bootstrap ──────────────────────────────────────────────────────────
  var payloadNode = document.getElementById('match-room-payload');
  if (!payloadNode) return;

  var parsedPayload;
  try { parsedPayload = JSON.parse(payloadNode.textContent || '{}'); } catch (_) { return; }
  if (!parsedPayload || typeof parsedPayload !== 'object' || !parsedPayload.match || !parsedPayload.urls) return;

  // ── Constants ──────────────────────────────────────────────────────────
  var PHASE_FALLBACK = ['coin_toss', 'phase1', 'lobby_setup', 'live', 'results', 'completed'];
  var VALID_PHASES = new Set(PHASE_FALLBACK);
  var MOBILE_TABS = ['engine', 'chat', 'intel'];
  var ALLOWED_CREDENTIAL_KEYS = new Set(['lobby_code', 'password', 'map', 'server', 'game_mode', 'notes']);
  var DEFAULT_TIMEZONE = 'Asia/Dhaka';
  var DEFAULT_TIME_FORMAT = '12h';

  var WS_CLOSE_MESSAGES = {
    4000: 'Invalid match reference.',
    4001: 'Authentication required.',
    4003: 'Connection rejected: invalid origin.',
    4004: 'Match voided or not found.',
    4008: 'Rate limited. Reconnecting shortly.',
    1006: 'Connection lost, retrying…',
    1001: 'Server shutting down, retrying…',
    1011: 'Unexpected server error.',
    1000: 'Connection closed normally.',
  };

  var THEME_PRESETS = {
    valorant: { accent: '#00f0ff', rgb: [0, 240, 255], bg: "url('https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=2850')" },
    efootball: { accent: '#00ff66', rgb: [0, 255, 102], bg: "url('https://images.unsplash.com/photo-1518605368461-1e1e38ce7058?q=80&w=2850')" },
  };

  var timePrefs = { timezone: DEFAULT_TIMEZONE, timeFormat: DEFAULT_TIME_FORMAT };
  var timePrefsPromise = null;

  // ── Phase Registry ─────────────────────────────────────────────────────
  var phaseRegistry = {};

  // ── State ──────────────────────────────────────────────────────────────
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
    _rafRender: null,
  };

  // ── DOM Element Cache ──────────────────────────────────────────────────
  var elements = {
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
    navTournamentName: byId('nav-tournament-name'),
    navP1Logo: byId('nav-p1-logo'),
    navP2Logo: byId('nav-p2-logo'),
    navP1Name: byId('nav-p1-name'),
    navP2Name: byId('nav-p2-name'),
    navP1Score: byId('nav-p1-score'),
    navP2Score: byId('nav-p2-score'),
    navP1Dot: byId('nav-p1-dot'),
    navP2Dot: byId('nav-p2-dot'),
    navBestOf: byId('nav-best-of'),
    navFormatBadge: byId('nav-format-badge'),
    navGameBadge: byId('nav-game-badge'),
    navMeta: byId('nav-meta'),
    socketPill: byId('socket-pill'),
    helpSignalBtn: byId('help-signal-btn'),
    phaseTracker: byId('phase-tracker'),
    engineContainer: byId('engine-container'),
    mainScroll: byId('main-scroll'),
    sideChat: byId('side-chat'),
    sideIntel: byId('side-intel'),
    sideAdmin: byId('side-admin'),
    dtTabChat: byId('dt-tab-chat'),
    dtTabIntel: byId('dt-tab-intel'),
    dtTabAdmin: byId('dt-tab-admin'),
    mobTabEngine: byId('mob-tab-engine'),
    mobTabChat: byId('mob-tab-chat'),
    mobTabIntel: byId('mob-tab-intel'),
    chatWindow: byId('chat-window'),
    chatForm: byId('chat-form'),
    chatInput: byId('chat-input'),
    roomToast: byId('room-toast'),
    overrideModal: byId('admin-override-modal'),
    overrideP1: byId('override-p1'),
    overrideP2: byId('override-p2'),
    overrideNote: byId('override-note'),
    overrideClose: byId('override-close'),
    overrideCancel: byId('override-cancel'),
    overrideApply: byId('override-apply'),
    adminForceNext: byId('admin-force-next'),
    adminOpenOverride: byId('admin-open-override'),
    adminBroadcast: byId('admin-broadcast'),
    mobilePanelOverlay: byId('mobile-panel-overlay'),
    mobilePanelContent: byId('mobile-panel-content'),
    rulesList: byId('rules-list'),
  };

  // =====================================================================
  //  UTILITY FUNCTIONS
  // =====================================================================
  function byId(id) { return document.getElementById(id); }

  function esc(value) {
    var text = String(value == null ? '' : value);
    return text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
  }

  function asObject(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
  function asList(value) { return Array.isArray(value) ? value : []; }

  function toInt(value, fallback) {
    var parsed = Number.parseInt(String(value == null ? '' : value), 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function bool(value, fallback) {
    if (value == null) return !!fallback;
    if (typeof value === 'boolean') return value;
    if (typeof value === 'number') return value !== 0;
    var token = String(value).trim().toLowerCase();
    if (token === '1' || token === 'true' || token === 'yes' || token === 'y' || token === 'on') return true;
    if (token === '0' || token === 'false' || token === 'no' || token === 'n' || token === 'off' || token === '') return false;
    return !!fallback;
  }

  function nowMs() { return Date.now(); }

  function sanitizeCsrfToken(value) {
    var raw = String(value || '').trim();
    if (!raw) return '';
    return raw.replace(/^['\"]|['\"]$/g, '');
  }

  function getCookie(name) {
    var chunks = String(document.cookie || '').split(';');
    var prefix = String(name || '') + '=';
    for (var i = 0; i < chunks.length; i++) {
      var item = chunks[i].trim();
      if (!item.startsWith(prefix)) continue;
      return decodeURIComponent(item.slice(prefix.length));
    }
    return '';
  }

  function normalizeTimeFormat(value) {
    var token = String(value || '').trim().toLowerCase();
    return (token === '24' || token === '24h') ? '24h' : '12h';
  }

  function normalizeTimezone(value) {
    var tz = String(value || '').trim();
    return tz || DEFAULT_TIMEZONE;
  }

  function timeFormatOptions(options, includeTime) {
    var next = (options && typeof options === 'object') ? Object.assign({}, options) : {};
    if (!next.timeZone) next.timeZone = timePrefs.timezone;
    if (includeTime && next.hour12 === undefined && next.hourCycle === undefined) {
      next.hour12 = timePrefs.timeFormat !== '24h';
    }
    return next;
  }

  function formatDateTimeWithPrefs(value, options) {
    var dt = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(dt.getTime())) return 'N/A';
    try { return dt.toLocaleString(undefined, timeFormatOptions(options, true)); }
    catch (_) { return dt.toLocaleString(); }
  }

  function formatTimeWithPrefs(value, options) {
    var dt = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(dt.getTime())) return 'N/A';
    try { return dt.toLocaleTimeString(undefined, timeFormatOptions(options, true)); }
    catch (_) { return dt.toLocaleTimeString(); }
  }

  function formatLocalTime(isoString) {
    if (!isoString) return 'N/A';
    var dt = new Date(isoString);
    if (Number.isNaN(dt.getTime())) return 'N/A';
    return formatDateTimeWithPrefs(dt, { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  function shortClock(isoString) {
    if (!isoString) return 'now';
    var dt = new Date(isoString);
    if (Number.isNaN(dt.getTime())) return 'now';
    return formatTimeWithPrefs(dt, { hour: '2-digit', minute: '2-digit' });
  }

  function parseTimestamp(value) {
    if (!value) return 0;
    var dt = new Date(value);
    var ts = dt.getTime();
    return Number.isFinite(ts) ? ts : 0;
  }

  function initials(name) {
    var text = String(name || '').trim();
    if (!text) return '?';
    var chunks = text.split(/\s+/).filter(Boolean);
    if (!chunks.length) return text.slice(0, 1).toUpperCase();
    if (chunks.length === 1) return chunks[0].slice(0, 2).toUpperCase();
    return (chunks[0].slice(0, 1) + chunks[1].slice(0, 1)).toUpperCase();
  }

  function valueOf(id) {
    var node = byId(id);
    return node ? String(node.value || '').trim() : '';
  }

  function maybeRunIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') window.lucide.createIcons();
  }

  function getCsrfToken() {
    var payloadToken = sanitizeCsrfToken(parsedPayload && parsedPayload.csrf_token ? parsedPayload.csrf_token : '');
    if (payloadToken) return payloadToken;
    var explicitToken = sanitizeCsrfToken(byId('match-room-csrf-token') ? byId('match-room-csrf-token').value : '');
    if (explicitToken) return explicitToken;
    var hiddenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    var hiddenToken = sanitizeCsrfToken(hiddenInput ? hiddenInput.value : '');
    if (hiddenToken) return hiddenToken;
    var meta = document.querySelector('meta[name="csrf-token"], meta[name="csrfmiddlewaretoken"]');
    var metaToken = sanitizeCsrfToken(meta ? meta.getAttribute('content') : '');
    if (metaToken) return metaToken;
    return sanitizeCsrfToken(getCookie('csrftoken'));
  }

  function loadTimePreferences() {
    if (timePrefsPromise) return timePrefsPromise;
    var endpoint = '/api/v1/user/preferences/';
    timePrefsPromise = fetch(endpoint, { method: 'GET', credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (resp) { return resp.ok ? resp.json().catch(function () { return {}; }) : {}; })
      .then(function (payload) {
        var prefs = (payload && typeof payload === 'object' && payload.preferences) ? payload.preferences : {};
        timePrefs = { timezone: normalizeTimezone(prefs.timezone || prefs.timezone_pref), timeFormat: normalizeTimeFormat(prefs.time_format) };
        return Object.assign({}, timePrefs);
      })
      .catch(function () { return Object.assign({}, timePrefs); });
    return timePrefsPromise;
  }

  function parseJsonResponse(response) {
    return response.text().then(function (text) {
      try { return JSON.parse(text || '{}'); } catch (_) { return {}; }
    });
  }

  // =====================================================================
  //  ROOM STATE ACCESSORS
  // =====================================================================
  function activeRoom() { return (state && state.room && typeof state.room === 'object') ? state.room : asObject(parsedPayload); }

  function canonicalGameKey() {
    var game = asObject(activeRoom().game);
    var key = String(game.pipeline_game_key || game.slug || '').trim().toLowerCase();
    if (key.includes('efootball')) return 'efootball';
    if (key.includes('valorant')) return 'valorant';
    return key || 'valorant';
  }

  function canonicalMode() {
    var key = canonicalGameKey();
    if (key === 'efootball') return 'direct';
    if (key === 'valorant') return 'veto';
    var room = activeRoom();
    var mode = String(asObject(room.workflow).mode || asObject(room.game).phase_mode || '').toLowerCase();
    return (mode === 'direct' || mode === 'veto') ? mode : 'veto';
  }

  function phase1Kind() {
    if (canonicalMode() === 'direct') return 'direct';
    var room = activeRoom();
    var kind = String(asObject(room.workflow).phase1_kind || asObject(room.pipeline).phase1_kind || '').toLowerCase();
    return kind === 'direct' ? 'direct' : 'veto';
  }

  function mySide() {
    var side = toInt(asObject(state.room.me).side, 0);
    return (side === 1 || side === 2) ? side : null;
  }

  function opponentSide() {
    var side = mySide();
    return side === 1 ? 2 : (side === 2 ? 1 : null);
  }

  function participantForSide(side) {
    if (side === 1) return asObject(state.room.match.participant1);
    if (side === 2) return asObject(state.room.match.participant2);
    return {};
  }

  function sideOnline(side) {
    if (side !== 1 && side !== 2) return false;
    var row = asObject(asObject(state.room.presence)[String(side)]);
    return bool(row.online, false);
  }

  function sideCheckedIn(side) {
    if (side !== 1 && side !== 2) return false;
    return bool(participantForSide(side).checked_in, false);
  }

  function bothSidesOnline() { return sideOnline(1) && sideOnline(2); }

  function hasSubmittedResultForSide(side) {
    var row = workflowSubmission(side);
    return !!(row && typeof row === 'object' && (row.submission_id || row.submitted_at));
  }

  function workflowSubmission(side) {
    var submissions = asObject(asObject(state.room.workflow).result_submissions);
    var row = submissions[String(side)];
    return (row && typeof row === 'object') ? row : null;
  }

  function workflowResultVisibility() { return asObject(asObject(state.room.workflow).result_visibility); }

  function effectivePolicy() {
    var workflowPolicy = asObject(asObject(state.room.workflow).policy);
    var pipelinePolicy = asObject(asObject(state.room.pipeline).policy);
    return asObject(workflowPolicy.effective || pipelinePolicy.effective);
  }

  function requiresMatchEvidence() { return bool(asObject(effectivePolicy()).require_match_evidence, false); }

  function bypassPresenceLock() {
    var me = asObject(state.room.me);
    if (bool(me.admin_mode, false)) return true;
    if (bool(me.is_staff, false)) return true;
    var matchState = String(asObject(state.room.match).state || '');
    return matchState === 'completed' || matchState === 'forfeit' || matchState === 'cancelled';
  }

  function waitingLocked() {
    if (bypassPresenceLock()) return false;
    var side = mySide();
    if (side !== 1 && side !== 2) return false;
    return !bothSidesOnline() && !state.wsConnected;
  }

  function actionRequiresPresence(action) {
    return action !== 'check_in' && action !== 'admin_override_result' && action !== 'system_announcement' && action !== 'advance_phase';
  }

  function defaultPhaseOrder() {
    return canonicalMode() === 'direct'
      ? ['phase1', 'lobby_setup', 'live', 'results', 'completed']
      : ['coin_toss', 'phase1', 'lobby_setup', 'live', 'results', 'completed'];
  }

  function phaseOrder() {
    var wfOrder = asList(asObject(state.room.workflow).phase_order)
      .map(function (p) { return String(p || '').trim(); })
      .filter(function (p) { return VALID_PHASES.has(p); });
    return wfOrder.length ? wfOrder : defaultPhaseOrder();
  }

  function currentPhase() {
    var workflow = asObject(state.room.workflow);
    var order = phaseOrder();
    var current = String(workflow.phase || '').trim();
    return order.includes(current) ? current : (order[0] || 'phase1');
  }

  function phaseLabel(phase) {
    var mod = phaseRegistry[phase];
    if (mod && typeof mod.label === 'function') return mod.label();
    if (phase === 'coin_toss') return 'Coin Toss';
    if (phase === 'phase1') return phase1Kind() === 'direct' ? 'Direct Ready' : 'Map Veto';
    if (phase === 'lobby_setup') return 'Lobby Setup';
    if (phase === 'live') return 'Live Match';
    if (phase === 'results') return 'Results';
    if (phase === 'completed') return 'Completed';
    return phase;
  }

  function phaseNarrative(phase) {
    var mod = phaseRegistry[phase];
    if (mod && typeof mod.narrative === 'function') return mod.narrative();
    if (phase === 'coin_toss') return 'Resolve first control so both sides can start with a fair edge.';
    if (phase === 'phase1') return phase1Kind() === 'direct'
      ? 'Both sides confirm ready status before host credentials unlock.'
      : 'Run bans and picks in order to lock the final battleground.';
    if (phase === 'lobby_setup') return 'Host publishes lobby credentials and both teams sync in one room.';
    if (phase === 'live') return 'Match is live. Finish gameplay, then move to result declaration.';
    if (phase === 'results') return requiresMatchEvidence()
      ? 'Blind-submit your scoreline with required image evidence, then wait for verification.'
      : 'Blind-submit your scoreline with optional proof and wait for verification.';
    if (phase === 'completed') return 'Result finalized. Jump to hub or bracket for the next assignment.';
    return 'Realtime sync in progress. Refresh if this panel stalls.';
  }

  function mapPool() {
    var workflowPool = asList(asObject(state.room.workflow).veto.pool)
      .map(function (row) { return String(row || '').trim(); }).filter(Boolean);
    if (workflowPool.length) return workflowPool;
    return asList(asObject(state.room.game).map_pool).map(function (row) { return String(row || '').trim(); }).filter(Boolean);
  }

  function credentialLabelForKey(key) {
    if (key === 'lobby_code') return canonicalGameKey() === 'efootball' ? 'Room Number' : 'Lobby Code';
    if (key === 'password') return 'Password';
    if (key === 'map') return 'Map';
    if (key === 'server') return 'Server';
    if (key === 'game_mode') return 'Game Mode';
    if (key === 'notes') return 'Notes';
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
    var normalized = [];
    asList(rows).forEach(function (entry) {
      var row = asObject(entry);
      var key = String(row.key || row.name || '').trim().toLowerCase();
      if (key === 'room_number') key = 'lobby_code';
      if (!ALLOWED_CREDENTIAL_KEYS.has(key)) return;
      var kindToken = String(row.kind || row.type || '').trim().toLowerCase();
      var kind = (kindToken === 'textarea' || key === 'notes') ? 'textarea' : 'text';
      var label = String(row.label || row.title || credentialLabelForKey(key) || '').trim() || credentialLabelForKey(key);
      normalized.push({ key: key, label: label, kind: kind, required: bool(row.required, false) });
    });
    return normalized.length ? normalized : fallbackCredentialSchema();
  }

  function credentialSchema() { return normalizeCredentialSchema(asObject(activeRoom().game).credentials_schema); }
  function credentialInputId(key) { return 'cred-' + String(key || '').trim().toLowerCase().replaceAll('_', '-'); }

  // =====================================================================
  //  PRESENCE
  // =====================================================================
  function resolvePresence(input, matchValue) {
    var source = asObject(input);
    var match = asObject(matchValue);
    var p1 = asObject(match.participant1);
    var p2 = asObject(match.participant2);
    var sides = { '1': normalizePresenceSide(source['1']), '2': normalizePresenceSide(source['2']) };
    sides['1'].checked_in = bool(p1.checked_in, false);
    sides['2'].checked_in = bool(p2.checked_in, false);
    return sides;
  }

  function normalizePresenceSide(raw) {
    var row = asObject(raw);
    var status = String(row.status || '').toLowerCase();
    var online = bool(row.online, status === 'online' || status === 'away');
    return { status: online ? (status === 'away' ? 'away' : 'online') : 'offline', online: online, last_seen: row.last_seen || null, user_id: row.user_id || null, username: row.username || null, checked_in: bool(row.checked_in, false) };
  }

  function mergePresenceSnapshots(baseValue, overrideValue) {
    var base = resolvePresence(baseValue, state.room.match);
    var override = resolvePresence(overrideValue, state.room.match);
    return { '1': mergePresenceSide(base['1'], override['1']), '2': mergePresenceSide(base['2'], override['2']) };
  }

  function mergePresenceSide(baseSide, overrideSide) {
    var base = normalizePresenceSide(baseSide);
    var override = normalizePresenceSide(overrideSide);
    if (!override.online && !override.user_id && !override.last_seen) return base;
    return { status: override.status || base.status, online: bool(override.online, false), last_seen: override.last_seen || base.last_seen || null, user_id: override.user_id || base.user_id || null, username: override.username || base.username || null, checked_in: bool(override.checked_in, base.checked_in) };
  }

  function applyLocalPresenceHold(snapshotValue) {
    var snapshot = resolvePresence(snapshotValue, state.room.match);
    var side = mySide();
    if (side !== 1 && side !== 2) return snapshot;
    var key = String(side);
    var row = asObject(snapshot[key]);
    if (bool(row.online, false)) { state.localPresenceHoldUntilMs = 0; return snapshot; }
    var shouldHold = state.wsConnected && nowMs() <= state.localPresenceHoldUntilMs;
    if (!shouldHold) return snapshot;
    snapshot[key] = Object.assign({}, row, { online: true, status: document.hidden ? 'away' : 'online', user_id: row.user_id || asObject(state.room.me).user_id || null, last_seen: new Date().toISOString() });
    return snapshot;
  }

  function updatePresenceLocal(side, online, status) {
    if (side !== 1 && side !== 2) return;
    if (online) state.localPresenceHoldUntilMs = Math.max(state.localPresenceHoldUntilMs, nowMs() + 10000);
    var key = String(side);
    if (!state.socketPresence || typeof state.socketPresence !== 'object') {
      state.socketPresence = { '1': normalizePresenceSide({}), '2': normalizePresenceSide({}) };
    }
    var socketRow = asObject(state.socketPresence[key]);
    socketRow.online = !!online;
    socketRow.status = online ? (status === 'away' ? 'away' : 'online') : 'offline';
    socketRow.last_seen = new Date().toISOString();
    socketRow.checked_in = sideCheckedIn(side);
    state.socketPresence[key] = socketRow;
    var roomRow = asObject(state.room.presence[key]);
    roomRow.online = !!online;
    roomRow.status = online ? (status === 'away' ? 'away' : 'online') : 'offline';
    roomRow.last_seen = new Date().toISOString();
    state.room.presence[key] = roomRow;
    state.room.workflow.presence[key] = roomRow;
  }

  // =====================================================================
  //  ROOM SHAPE / APPLY
  // =====================================================================
  function ensureRoomShape(roomValue) {
    var room = asObject(roomValue);
    room.match = asObject(room.match);
    room.match.participant1 = asObject(room.match.participant1);
    room.match.participant2 = asObject(room.match.participant2);
    room.tournament = asObject(room.tournament);
    room.game = asObject(room.game);
    room.game.credentials_schema = asList(room.game.credentials_schema).map(function (r) { return asObject(r); });
    room.game.match_rules = asList(room.game.match_rules).map(function (r) { return asObject(r); });
    room.game.pipeline_phases = asList(room.game.pipeline_phases);
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
    room.workflow.phase_order = asList(room.workflow.phase_order).map(function (p) { return String(p || '').trim(); }).filter(function (p) { return VALID_PHASES.has(p); });
    if (!room.workflow.phase_order.length) room.workflow.phase_order = defaultPhaseOrder();
    if (!VALID_PHASES.has(String(room.workflow.phase || ''))) {
      room.workflow.phase = room.workflow.phase_order[0] || defaultPhaseOrder()[0];
    }
    return room;
  }

  function applyRoom(nextRoom) {
    var normalized = ensureRoomShape(nextRoom);
    if (state.socketPresence && typeof state.socketPresence === 'object') {
      normalized.presence = mergePresenceSnapshots(normalized.presence, state.socketPresence);
      normalized.workflow.presence = mergePresenceSnapshots(normalized.workflow.presence, state.socketPresence);
    }
    state.room = normalized;
    ensureNoShowTicker();
    scheduleRender('full');
  }

  // =====================================================================
  //  TARGETED RE-RENDERING (RAF-batched)
  // =====================================================================
  var _pendingRenders = new Set();

  function scheduleRender(target) {
    _pendingRenders.add(target || 'full');
    if (state._rafRender) return;
    state._rafRender = window.requestAnimationFrame(function () {
      state._rafRender = null;
      flushRenders();
    });
  }

  function flushRenders() {
    var targets = Array.from(_pendingRenders);
    _pendingRenders.clear();

    if (targets.includes('full')) {
      renderAll();
      return;
    }

    targets.forEach(function (t) {
      if (t === 'presence') renderPresence();
      else if (t === 'chat') renderChat();
      else if (t === 'engine') renderEngine();
      else if (t === 'header') renderHeader();
      else if (t === 'socket') updateSocketPill();
      else if (t === 'waiting') updateWaitingOverlay();
      else if (t === 'phase_tracker') renderPhaseTracker();
    });
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

  function renderPresence() {
    renderHeaderPresenceMeta();
    renderCheckInPresenceChips();
    updateWaitingOverlay();
    var nextWaitingLocked = waitingLocked();
    if (nextWaitingLocked !== state.lastWaitingLocked) {
      state.lastWaitingLocked = nextWaitingLocked;
      renderEngine();
    }
    state.lastWaitingLocked = nextWaitingLocked;
  }

  function renderChat() {
    // Chat is append-only — no full re-render needed.
    // This hook exists for mobile mirror sync.
    syncMobileMirror();
  }

  // =====================================================================
  //  THEME
  // =====================================================================
  function applyTheme() {
    if (!elements.shell) return;
    var key = canonicalGameKey();
    var preset = THEME_PRESETS[key] || THEME_PRESETS.valorant;
    var game = asObject(activeRoom().game);
    var accentHex = String(game.primary_color || preset.accent || '#00f0ff');
    var rgb = preset.rgb || [0, 240, 255];
    elements.shell.style.setProperty('--ac', accentHex);
    elements.shell.style.setProperty('--ac-r', String(rgb[0]));
    elements.shell.style.setProperty('--ac-g', String(rgb[1]));
    elements.shell.style.setProperty('--ac-b', String(rgb[2]));
    elements.shell.setAttribute('data-game', key);
  }

  // =====================================================================
  //  HEADER
  // =====================================================================
  function renderHeader() {
    var match = asObject(state.room.match);
    var tournament = asObject(state.room.tournament);
    var p1 = asObject(match.participant1);
    var p2 = asObject(match.participant2);
    if (elements.navMatchId) elements.navMatchId.textContent = 'M-' + String(match.id || '?');
    if (elements.navTournamentName) elements.navTournamentName.textContent = String(tournament.name || '');
    if (elements.navP1Name) elements.navP1Name.textContent = String(p1.name || 'TBD');
    if (elements.navP2Name) elements.navP2Name.textContent = String(p2.name || 'TBD');
    if (elements.navP1Score) elements.navP1Score.textContent = String(toInt(p1.score, 0));
    if (elements.navP2Score) elements.navP2Score.textContent = String(toInt(p2.score, 0));
    if (elements.navBestOf) elements.navBestOf.textContent = 'BO' + String(toInt(match.best_of, 1));
    if (elements.navGameBadge) elements.navGameBadge.textContent = String(asObject(state.room.game).name || canonicalGameKey()).toUpperCase();
    if (elements.navBackLink) elements.navBackLink.setAttribute('href', String(asObject(state.room.urls).hub || '#'));
    renderLogo(elements.navP1Logo, p1, 1);
    renderLogo(elements.navP2Logo, p2, 2);
    renderHeaderCommandBadges();
    renderHeaderPresenceMeta();
  }

  function renderHeaderCommandBadges() {
    if (elements.navFormatBadge) {
      var label = phase1Kind() === 'direct' ? 'DIRECT' : 'VETO';
      elements.navFormatBadge.textContent = label;
    }
  }

  function renderHeaderPresenceMeta() {
    if (elements.navP1Dot) {
      var p1On = sideOnline(1) || (mySide() === 1 && state.wsConnected);
      elements.navP1Dot.className = 'w-2 h-2 rounded-full ' + (p1On ? 'bg-emerald-400' : 'bg-gray-600');
    }
    if (elements.navP2Dot) {
      var p2On = sideOnline(2) || (mySide() === 2 && state.wsConnected);
      elements.navP2Dot.className = 'w-2 h-2 rounded-full ' + (p2On ? 'bg-emerald-400' : 'bg-gray-600');
    }
    if (elements.navMeta) {
      var phase = currentPhase();
      elements.navMeta.textContent = phaseLabel(phase);
    }
  }

  function renderLogo(node, participant, side) {
    if (!node) return;
    var url = String(participant.logo_url || '').trim();
    if (url) {
      node.innerHTML = '<img src="' + esc(url) + '" alt="' + esc(String(participant.name || '')) + '" class="w-full h-full object-cover" loading="lazy" />';
    } else {
      var tone = side === 1 ? 'bg-cyan-500/20 text-cyan-200' : 'bg-rose-500/20 text-rose-200';
      node.innerHTML = '<span class="text-xs font-bold ' + tone + '">' + esc(initials(participant.name)) + '</span>';
    }
  }

  // =====================================================================
  //  RULES
  // =====================================================================
  function renderRules() {
    if (!elements.rulesList) return;
    var rules = asList(asObject(state.room.game).match_rules);
    if (!rules.length) { elements.rulesList.innerHTML = ''; return; }
    elements.rulesList.innerHTML = rules.map(function (item) {
      var r = asObject(item);
      return '<div class="p-3 rounded-xl bg-white/5 border border-white/10"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-1">' + esc(r.title) + '</p><p class="text-xs text-white leading-relaxed break-words">' + esc(r.value) + '</p></div>';
    }).join('');
  }

  // =====================================================================
  //  ADMIN VISIBILITY
  // =====================================================================
  function renderAdminVisibility() {
    var adminMode = bool(asObject(state.room.me).admin_mode, false);
    if (elements.dtTabAdmin) {
      if (adminMode) elements.dtTabAdmin.classList.remove('hidden-state');
      else elements.dtTabAdmin.classList.add('hidden-state');
    }
    if (!adminMode && state.activeDesktopTab === 'admin') { setDesktopTab('chat'); return; }
    setDesktopTab(state.activeDesktopTab);
  }

  // =====================================================================
  //  PHASE TRACKER
  // =====================================================================
  function renderPhaseTracker() {
    if (!elements.phaseTracker) return;
    var order = phaseOrder();
    var activePhase = currentPhase();
    var activeIndex = Math.max(0, order.indexOf(activePhase));
    var html = '';
    order.forEach(function (phase, index) {
      var done = index < activeIndex;
      var active = index === activeIndex;
      var dotClass = done ? 'phase-dot done' : (active ? 'phase-dot active' : 'phase-dot');
      var textClass = done ? 'text-[10px] font-bold text-green-300 uppercase tracking-wide' : (active ? 'text-[10px] font-bold text-white uppercase tracking-wide' : 'text-[10px] font-bold text-gray-500 uppercase tracking-wide');
      html += '<div class="flex flex-col items-center gap-1 min-w-[58px]"><div class="' + dotClass + '">' + (done ? '<i data-lucide="check" class="w-4 h-4"></i>' : esc(String(index + 1))) + '</div><span class="' + textClass + '">' + esc(phaseLabel(phase)) + '</span></div>';
      if (index < order.length - 1) {
        var lineClass = index < activeIndex ? 'phase-line done flex-1 max-w-[72px]' : (index === activeIndex ? 'phase-line active flex-1 max-w-[72px]' : 'phase-line flex-1 max-w-[72px]');
        html += '<div class="' + lineClass + '"><span></span></div>';
      }
    });
    elements.phaseTracker.innerHTML = html;
  }

  // =====================================================================
  //  ENGINE RENDERER — delegates to phase modules
  // =====================================================================
  function renderEngine() {
    if (!elements.engineContainer) return;
    var phase = currentPhase();
    var blocks = [];
    var showCheckInGate = phase === 'coin_toss' || phase === 'phase1' || phase === 'lobby_setup';
    if (showCheckInGate) blocks.push(renderCheckInBlock());

    var actionBody = renderPhaseBlock(phase);
    var actionTitle = phaseLabel(phase);
    var actionNarrative = phaseNarrative(phase);

    blocks.push(
      '<section class="phase-morph-shell glass-panel rounded-2xl p-4 md:p-5 border border-white/10" data-active-phase="' + esc(phase) + '">' +
      '<div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3"><div>' +
      '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Dynamic Action Card</p>' +
      '<h3 class="text-lg md:text-xl font-black text-white">' + esc(actionTitle) + '</h3>' +
      '<p class="text-xs text-gray-400 mt-1">' + esc(actionNarrative) + '</p></div>' +
      '<span class="phase-chip">' + (phase === 'live' ? '<span class="live-pulse"></span>' : '') + esc(actionTitle) + '</span></div>' +
      '<div class="mt-4 md:mt-5">' + actionBody + '</div></section>'
    );

    elements.engineContainer.innerHTML = blocks.join('');
    state.lastWaitingLocked = waitingLocked();
    maybeRunIcons();
  }

  function renderPhaseBlock(phase) {
    // Check registry for a dynamically loaded phase module
    var mod = phaseRegistry[phase];
    if (mod && typeof mod.render === 'function') {
      return mod.render(ctx());
    }

    // Legacy fallback for phase1 (coin_toss, veto, direct handled by modules)
    if (phase === 'phase1') {
      mod = phase1Kind() === 'direct' ? phaseRegistry['direct_ready'] : phaseRegistry['map_veto'];
      if (mod && typeof mod.render === 'function') return mod.render(ctx());
    }

    return renderFallbackBlock();
  }

  function renderFallbackBlock() {
    return '<section class="glass-panel rounded-2xl p-6 md:p-8 border border-white/10"><h3 class="text-lg font-bold text-white">Lobby state unavailable</h3><p class="text-sm text-gray-400 mt-2">Refresh or wait for realtime sync to resume.</p><button type="button" data-action="refresh-room" class="mt-4 px-4 py-2 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider">Refresh</button></section>';
  }

  function renderCheckInBlock() {
    var checkIn = asObject(state.room.check_in);
    var required = bool(checkIn.required, false);
    var side = mySide();
    var p1Ready = sideCheckedIn(1);
    var p2Ready = sideCheckedIn(2);
    var meReady = side === 1 ? p1Ready : (side === 2 ? p2Ready : false);
    var statusText = 'Check-in optional for this match.';
    if (required) {
      if (bool(checkIn.is_pending, false)) statusText = 'Window opens ' + formatLocalTime(checkIn.opens_at) + '.';
      else if (bool(checkIn.is_closed, false)) statusText = 'Window closed ' + formatLocalTime(checkIn.closes_at) + '.';
      else if (bool(checkIn.is_open, false)) statusText = 'Window open until ' + formatLocalTime(checkIn.closes_at) + '.';
      else statusText = 'Check-in required before phase actions.';
    }
    var canCheckIn = required && (side === 1 || side === 2) && !meReady && bool(checkIn.is_open, false) && !state.requestBusy;
    var buttonHtml = canCheckIn ? '<button type="button" data-action="check-in" class="px-4 py-2 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider active:scale-95 transition-transform">Check In</button>' : '';
    return '<section class="glass-card rounded-2xl p-4 md:p-5 border border-white/10"><div class="flex flex-col md:flex-row md:items-center justify-between gap-4"><div><p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-1">Entry Gate</p><h3 class="text-sm md:text-base font-bold text-white">Participant Check-In</h3><p class="text-xs text-gray-400 mt-1">' + esc(statusText) + '</p></div>' + buttonHtml + '</div><div class="mt-4 grid grid-cols-2 gap-3">' + renderCheckInChip(1, p1Ready, sideOnline(1)) + renderCheckInChip(2, p2Ready, sideOnline(2)) + '</div></section>';
  }

  function renderCheckInChip(side, checkedIn, online) {
    var participant = participantForSide(side);
    var name = String(participant.name || 'Side ' + side);
    var isLocalConnected = side === mySide() && state.wsConnected;
    var effectiveOnline = Boolean(online || isLocalConnected);
    var checkedText = checkedIn ? 'Ready' : (effectiveOnline ? 'Online' : 'Pending');
    var checkedClass = checkedIn ? 'text-green-300 border-green-400/30 bg-green-500/10' : (effectiveOnline ? 'text-cyan-200 border-cyan-400/25 bg-cyan-500/10' : 'text-amber-200 border-amber-400/20 bg-amber-500/10');
    var onlineClass = effectiveOnline ? 'bg-emerald-400' : 'bg-gray-600';
    return '<div class="rounded-xl border border-white/10 bg-black/35 p-3" data-check-chip-side="' + esc(String(side)) + '"><div class="flex items-center justify-between"><p class="text-xs font-semibold text-white truncate">' + esc(name) + '</p><span data-check-chip-dot="' + esc(String(side)) + '" class="w-2.5 h-2.5 rounded-full ' + onlineClass + '"></span></div><p data-check-chip-label="' + esc(String(side)) + '" class="mt-2 inline-flex px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ' + checkedClass + '">' + checkedText + '</p></div>';
  }

  function renderCheckInPresenceChips() {
    [1, 2].forEach(function (side) {
      var root = document.querySelector('[data-check-chip-side="' + side + '"]');
      if (!root) return;
      var checkedIn = sideCheckedIn(side);
      var online = sideOnline(side) || (side === mySide() && state.wsConnected);
      var label = checkedIn ? 'Ready' : (online ? 'Online' : 'Pending');
      var dotNode = root.querySelector('[data-check-chip-dot="' + side + '"]');
      var labelNode = root.querySelector('[data-check-chip-label="' + side + '"]');
      if (dotNode) dotNode.className = 'w-2.5 h-2.5 rounded-full ' + (online ? 'bg-emerald-400' : 'bg-gray-600');
      if (labelNode) {
        var cls = checkedIn ? 'text-green-300 border-green-400/30 bg-green-500/10' : (online ? 'text-cyan-200 border-cyan-400/25 bg-cyan-500/10' : 'text-amber-200 border-amber-400/20 bg-amber-500/10');
        labelNode.className = 'mt-2 inline-flex px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ' + cls;
        labelNode.textContent = label;
      }
    });
  }

  // =====================================================================
  //  WAITING OVERLAY & SOCKET PILL
  // =====================================================================
  function updateWaitingOverlay() {
    if (!elements.waitingOverlay) return;
    var side = mySide();
    var oppSide = opponentSide();
    if (!((side === 1 && oppSide === 2) || (side === 2 && oppSide === 1))) {
      elements.waitingOverlay.classList.add('overlay-hidden');
      return;
    }
    if (bypassPresenceLock()) { elements.waitingOverlay.classList.add('overlay-hidden'); return; }
    var meOnline = sideOnline(side) || state.wsConnected;
    var oppOnline = sideOnline(oppSide);
    var bothOnline = meOnline && oppOnline;
    var opponent = participantForSide(oppSide);
    ensureNoShowTicker();
    if (elements.waitingYouDot) elements.waitingYouDot.className = 'w-2.5 h-2.5 rounded-full ' + (meOnline ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.65)]' : 'bg-gray-600');
    if (elements.waitingOpponentDot) elements.waitingOpponentDot.className = 'w-2.5 h-2.5 rounded-full ' + (oppOnline ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.65)]' : 'bg-gray-600');
    if (elements.waitingOpponentName) elements.waitingOpponentName.textContent = String(opponent.name || 'Opponent');
    if (elements.waitingCopy) {
      if (bothOnline) elements.waitingCopy.textContent = 'Both sides online. Lobby unlocked.';
      else if (!meOnline) elements.waitingCopy.textContent = 'Connecting your websocket presence...';
      else elements.waitingCopy.textContent = 'Waiting for opponent websocket presence.';
    }
    if (bothOnline) elements.waitingOverlay.classList.add('overlay-hidden');
    else elements.waitingOverlay.classList.remove('overlay-hidden');
  }

  function updateSocketPill() {
    if (!elements.socketPill) return;
    var base = 'inline-flex items-center justify-center h-5 w-5 rounded-full border';
    if (state.wsConnected) {
      elements.socketPill.className = base + ' bg-green-500/10 border-green-400/30';
      elements.socketPill.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>';
      elements.socketPill.setAttribute('title', 'Socket live');
      elements.socketPill.setAttribute('aria-label', 'Socket live');
    } else if (state.reconnectTimer) {
      elements.socketPill.className = base + ' bg-amber-500/10 border-amber-400/35';
      elements.socketPill.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-amber-300 animate-pulse"></span>';
      elements.socketPill.setAttribute('title', 'Socket reconnecting');
      elements.socketPill.setAttribute('aria-label', 'Socket reconnecting');
    } else {
      elements.socketPill.className = base + ' bg-red-500/10 border-red-400/35';
      elements.socketPill.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-red-300"></span>';
      elements.socketPill.setAttribute('title', 'Socket offline');
      elements.socketPill.setAttribute('aria-label', 'Socket offline');
    }
  }

  // =====================================================================
  //  TIMERS & NO-SHOW
  // =====================================================================
  function resolveNoShowDeadlineMs() {
    var checkIn = asObject(state.room.check_in);
    var checkInClose = parseTimestamp(checkIn.closes_at);
    if (checkInClose > 0) return checkInClose;
    var scheduled = parseTimestamp(asObject(state.room.match).scheduled_time);
    if (scheduled > 0) return scheduled + (15 * 60 * 1000);
    return nowMs() + (15 * 60 * 1000);
  }

  function formatCountdown(msRemaining) {
    var safe = Math.max(0, msRemaining);
    var totalSeconds = Math.ceil(safe / 1000);
    var hours = Math.floor(totalSeconds / 3600);
    var minutes = Math.floor((totalSeconds % 3600) / 60);
    var seconds = totalSeconds % 60;
    if (hours > 0) return String(hours).padStart(2, '0') + ':' + String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
    return String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
  }

  function renderNoShowTimer() {
    if (!elements.waitingNoShowTimer) return;
    var deadline = state.noShowDeadlineMs || resolveNoShowDeadlineMs();
    elements.waitingNoShowTimer.textContent = formatCountdown(Math.max(0, deadline - nowMs()));
  }

  function ensureNoShowTicker() {
    var nextDeadline = resolveNoShowDeadlineMs();
    if (!state.noShowDeadlineMs || Math.abs(state.noShowDeadlineMs - nextDeadline) > 5000) state.noShowDeadlineMs = nextDeadline;
    if (!state.noShowTimer) state.noShowTimer = window.setInterval(renderNoShowTimer, 1000);
    renderNoShowTimer();
  }

  // =====================================================================
  //  MOBILE / LAYOUT
  // =====================================================================
  function updateMobileOverlayTopOffset() {
    if (!elements.mobilePanelOverlay || !elements.topNav) return;
    if (window.innerWidth >= 1024) { elements.mobilePanelOverlay.style.top = '64px'; return; }
    var navHeight = state.navHidden ? 0 : Math.max(0, Math.round(elements.topNav.getBoundingClientRect().height || 56));
    elements.mobilePanelOverlay.style.top = navHeight + 'px';
  }

  function updateShellViewportHeight() {
    if (!elements.shell) return;
    var rect = elements.shell.getBoundingClientRect();
    var topOffset = Math.max(0, Math.round(rect.top || 0));
    var viewportHeight = window.visualViewport && Number.isFinite(window.visualViewport.height) ? Math.round(window.visualViewport.height) : Math.round(window.innerHeight || 0);
    elements.shell.style.setProperty('--room-shell-height', Math.max(420, viewportHeight - topOffset) + 'px');
  }

  function setMobileTopNavHidden(hidden) {
    if (!elements.topNav) return;
    var shouldHide = Boolean(hidden) && window.innerWidth < 1024;
    state.navHidden = shouldHide;
    elements.topNav.classList.toggle('nav-hidden', shouldHide);
    updateMobileOverlayTopOffset();
  }

  function handleMainScrollForNav() {
    if (!elements.mainScroll || window.innerWidth >= 1024) { setMobileTopNavHidden(false); return; }
    var current = Math.max(0, elements.mainScroll.scrollTop || 0);
    var delta = current - state.lastMainScrollTop;
    if (current <= 8) setMobileTopNavHidden(false);
    else if (delta > 6) setMobileTopNavHidden(true);
    else if (delta < -6) setMobileTopNavHidden(false);
    state.lastMainScrollTop = current;
  }

  function initMobileTopNavBehavior() {
    if (!elements.mainScroll || !elements.topNav) return;
    elements.mainScroll.addEventListener('scroll', handleMainScrollForNav, { passive: true });
    window.addEventListener('resize', function () { updateShellViewportHeight(); if (window.innerWidth >= 1024) setMobileTopNavHidden(false); updateMobileOverlayTopOffset(); }, { passive: true });
    if (window.visualViewport) window.visualViewport.addEventListener('resize', function () { updateShellViewportHeight(); updateMobileOverlayTopOffset(); }, { passive: true });
    updateShellViewportHeight();
    updateMobileOverlayTopOffset();
  }

  function syncMobileMirror() {
    // Placeholder — mobile chat/intel sync happens via tab switch render.
  }

  function setDesktopTab(tab) {
    var allowed = ['chat', 'intel', 'admin'];
    var next = allowed.includes(tab) ? tab : 'chat';
    if (next === 'admin' && !bool(asObject(state.room.me).admin_mode, false)) next = 'chat';
    state.activeDesktopTab = next;
    var configs = [
      { key: 'chat', panel: elements.sideChat, button: elements.dtTabChat, adminStyle: false },
      { key: 'intel', panel: elements.sideIntel, button: elements.dtTabIntel, adminStyle: false },
      { key: 'admin', panel: elements.sideAdmin, button: elements.dtTabAdmin, adminStyle: true },
    ];
    configs.forEach(function (cfg) {
      if (cfg.panel) cfg.panel.classList.add('hidden-state');
      if (cfg.button) { cfg.button.classList.remove('text-ac', 'text-yellow-300', 'border-ac'); cfg.button.classList.add('text-gray-500'); cfg.button.style.borderBottomColor = 'transparent'; }
    });
    var active = configs.find(function (cfg) { return cfg.key === next; });
    if (active) {
      if (active.panel) active.panel.classList.remove('hidden-state');
      if (active.button) { active.button.classList.remove('text-gray-500'); active.button.classList.add(active.adminStyle ? 'text-yellow-300' : 'text-ac'); active.button.style.borderBottomColor = active.adminStyle ? '#fcd34d' : 'var(--ac)'; }
    }
  }

  function setMobileTab(tab) {
    var target = MOBILE_TABS.includes(tab) ? tab : 'engine';
    state.activeMobileTab = target;
    MOBILE_TABS.forEach(function (key) { var btn = byId('mob-tab-' + key); if (btn) { btn.classList.remove('text-ac'); btn.classList.add('text-gray-500'); } });
    var activeBtn = byId('mob-tab-' + target);
    if (activeBtn) { activeBtn.classList.remove('text-gray-500'); activeBtn.classList.add('text-ac'); }
    if (target === 'engine') {
      if (elements.mobilePanelOverlay) elements.mobilePanelOverlay.classList.add('hidden-state');
      if (elements.mainScroll) elements.mainScroll.style.display = '';
      setMobileTopNavHidden(false);
      return;
    }
    if (elements.mainScroll) elements.mainScroll.style.display = 'none';
    if (elements.mobilePanelOverlay) elements.mobilePanelOverlay.classList.remove('hidden-state');
    updateMobileOverlayTopOffset();
    if (elements.mobilePanelContent) {
      if (target === 'chat') renderMobileChat();
      else renderMobileIntel();
    }
    maybeRunIcons();
  }

  function renderMobileChat() {
    if (!elements.mobilePanelContent) return;
    var desktopHtml = elements.chatWindow ? elements.chatWindow.innerHTML : '';
    elements.mobilePanelContent.innerHTML =
      '<div class="flex-1 flex flex-col h-full"><div id="mobile-chat-window" class="flex-1 overflow-y-auto p-5 space-y-4 hide-scroll">' + desktopHtml + '</div>' +
      '<div class="p-4 bg-black/50 border-t border-white/10"><form id="mobile-chat-form" class="relative">' +
      '<input id="mobile-chat-input" type="text" placeholder="Message opponent..." class="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-4 pr-12 text-sm text-white focus:outline-none focus:border-ac" />' +
      '<button type="submit" class="absolute right-2 top-2 p-1.5 bg-ac-subtle text-ac rounded-lg"><i data-lucide="send" class="w-4 h-4"></i></button>' +
      '</form></div></div>';
    var form = byId('mobile-chat-form');
    if (form) form.addEventListener('submit', function (e) { e.preventDefault(); submitChat(byId('mobile-chat-input')); });
  }

  function renderMobileIntel() {
    if (!elements.mobilePanelContent) return;
    var match = asObject(state.room.match);
    var game = asObject(state.room.game);
    var tournament = asObject(state.room.tournament);
    elements.mobilePanelContent.innerHTML =
      '<div class="p-5 space-y-4">' +
      '<div class="glass-card rounded-xl p-4"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-2">Match Info</p>' +
      '<p class="text-xs text-white">Match #' + esc(String(match.id || '')) + ' · Round ' + esc(String(match.round_number || '')) + '</p>' +
      '<p class="text-xs text-gray-400 mt-1">' + esc(String(tournament.name || '')) + '</p>' +
      '<p class="text-xs text-gray-400 mt-1">Game: ' + esc(String(game.name || canonicalGameKey())) + '</p></div></div>';
  }

  // =====================================================================
  //  CHAT
  // =====================================================================
  function appendChatBubble(payload) {
    var data = asObject(payload);
    var msgId = String(data.id || data.message_id || '');
    if (msgId && state.chatIds.has(msgId)) return;
    if (msgId) state.chatIds.add(msgId);
    clearChatEmptyState();
    var side = toInt(data.side, 0);
    var mine = side === mySide();
    var isOfficial = bool(data.is_official, false);
    var sideToken = side === 1 ? 'p1' : (side === 2 ? 'p2' : 'system');
    var align = mine ? 'items-end' : 'items-start';
    var bubbleClass = mine ? 'bg-ac-subtle text-white rounded-2xl rounded-br-md' : (isOfficial ? 'bg-amber-500/10 text-amber-100 rounded-2xl rounded-bl-md border border-amber-300/20' : 'bg-white/5 text-white rounded-2xl rounded-bl-md');
    var html =
      '<div class="flex flex-col gap-1 ' + align + '">' +
      '<div class="flex items-end gap-2 ' + (mine ? 'flex-row-reverse' : '') + '">' +
      renderChatAvatar(data, mine, sideToken, isOfficial) +
      '<div class="max-w-[260px] ' + bubbleClass + ' px-4 py-2.5">' +
      '<p class="text-[11px] font-bold mb-1 ' + (isOfficial ? 'text-amber-200' : 'text-ac') + '">' + esc(String(data.username || 'Unknown')) + '</p>' +
      '<p class="text-sm leading-relaxed break-words">' + esc(String(data.text || data.message || '')) + '</p></div></div>' +
      '<span class="text-[9px] text-gray-600 px-10">' + (data.timestamp ? shortClock(data.timestamp) : 'now') + '</span></div>';
    if (elements.chatWindow) {
      elements.chatWindow.insertAdjacentHTML('beforeend', html);
      elements.chatWindow.scrollTop = elements.chatWindow.scrollHeight;
    }
    var mobileChatWindow = byId('mobile-chat-window');
    if (mobileChatWindow) {
      mobileChatWindow.insertAdjacentHTML('beforeend', html);
      mobileChatWindow.scrollTop = mobileChatWindow.scrollHeight;
    }
  }

  function renderChatAvatar(payload, mine, sideToken, isOfficial) {
    var side = toInt(payload.side, 0);
    var avatarUrl = String(payload.avatar_url || '').trim();
    if (isOfficial) return '<div class="w-8 h-8 rounded-lg border border-amber-300/45 bg-amber-500/15 text-amber-200 flex items-center justify-center shrink-0"><i data-lucide="shield-check" class="w-4 h-4"></i></div>';
    if (avatarUrl) return '<div class="w-8 h-8 rounded-lg overflow-hidden border border-white/20 shrink-0"><img src="' + esc(avatarUrl) + '" alt="' + esc(String(payload.username || 'Participant')) + '" class="w-full h-full object-cover" loading="lazy" /></div>';
    var tone = mine ? 'bg-ac-subtle text-ac border-ac-subtle' : (side === 1 ? 'bg-cyan-500/20 text-cyan-200 border-cyan-400/30' : 'bg-rose-500/20 text-rose-200 border-rose-400/30');
    return '<div class="w-8 h-8 rounded-lg border flex items-center justify-center shrink-0 ' + tone + '"><span class="text-[10px] font-bold">' + esc(initials(payload.username)) + '</span></div>';
  }

  function appendSystemChat(text) {
    clearChatEmptyState();
    var html = '<div class="flex items-center gap-2 px-2"><div class="h-px flex-1 bg-white/10"></div><span class="text-[10px] text-gray-500 font-semibold uppercase tracking-widest whitespace-nowrap">' + esc(text) + '</span><div class="h-px flex-1 bg-white/10"></div></div>';
    if (elements.chatWindow) elements.chatWindow.insertAdjacentHTML('beforeend', html);
    var mobileChatWindow = byId('mobile-chat-window');
    if (mobileChatWindow) mobileChatWindow.insertAdjacentHTML('beforeend', html);
  }

  function clearChatEmptyState() {
    document.querySelectorAll('#chat-empty-state').forEach(function (node) { if (node && node.parentNode) node.parentNode.removeChild(node); });
  }

  function submitChat(inputNode) {
    if (!inputNode) return;
    var text = String(inputNode.value || '').trim();
    if (!text) return;
    if (!state.wsConnected) { showToast('Socket is offline. Cannot send chat right now.', 'error'); return; }
    sendSocket({ type: 'chat_message', text: text });
    inputNode.value = '';
  }

  function processAnnouncements() {
    var announcements = asList(asObject(state.room.workflow).announcements);
    if (!announcements.length) return;
    announcements.forEach(function (item) {
      var row = asObject(item);
      var key = String(row.at || '') + ':' + String(row.message || '');
      if (!key || state.seenAnnouncements.has(key)) return;
      state.seenAnnouncements.add(key);
      appendSystemChat(String(row.message || 'System announcement'));
    });
  }

  // =====================================================================
  //  WEBSOCKET
  // =====================================================================
  function connectSocket() {
    var path = String(asObject(state.room.websocket).path || '');
    if (!path) return;
    var protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    var url = protocol + '://' + window.location.host + path;
    clearReconnectTimer();
    try { state.ws = new window.WebSocket(url); } catch (_) { scheduleReconnect(); return; }

    state.ws.addEventListener('open', function () {
      state.wsConnected = true;
      state.reconnectAttempts = 0;
      state.localPresenceHoldUntilMs = nowMs() + 12000;
      scheduleRender('socket');
      sendSocket({ type: 'subscribe' });
      sendSocket({ type: 'presence_ping', status: document.hidden ? 'away' : 'online' });
      updatePresenceLocal(mySide(), true, 'online');
      scheduleRender('presence');
      showToast('Socket connected.', 'success');
    });

    state.ws.addEventListener('message', function (event) {
      var data;
      try { data = JSON.parse(event.data || '{}'); } catch (_) { data = {}; }
      handleSocketMessage(data);
    });

    state.ws.addEventListener('close', function (event) {
      state.wsConnected = false;
      var code = event && event.code ? event.code : 0;
      var msg = WS_CLOSE_MESSAGES[code] || 'Connection closed (code ' + code + ').';
      scheduleRender('socket');
      updatePresenceLocal(mySide(), false, 'offline');
      scheduleRender('presence');
      // Non-normal, non-voided closes get retried
      if (code !== 4004 && code !== 4001 && code !== 4003) {
        showToast(msg, code === 1000 ? 'info' : 'error');
        scheduleReconnect();
      } else {
        showToast(msg, 'error');
      }
    });

    state.ws.addEventListener('error', function () { /* close handler manages reconnect */ });
  }

  function sendSocket(payload) {
    if (!state.ws || state.ws.readyState !== window.WebSocket.OPEN) return;
    try { state.ws.send(JSON.stringify(payload)); } catch (_) { /* rely on reconnect */ }
  }

  function handleSocketMessage(message) {
    var type = String(message.type || '');
    if (type === 'ping') { sendSocket({ type: 'pong', timestamp: message.timestamp || null }); return; }
    if (type === 'connection_established' || type === 'presence_synced') return;

    if (type === 'match_presence') {
      var payload = asObject(message.data);
      var sides = asObject(payload.sides);
      var normalized = applyLocalPresenceHold(resolvePresence(sides, state.room.match));
      state.socketPresence = normalized;
      state.room.presence = normalized;
      state.room.workflow.presence = normalized;
      scheduleRender('presence');
      return;
    }

    if (type === 'match_room_event') {
      var data = asObject(message.data);
      var eventPayload = asObject(data.payload);
      if (eventPayload.room && typeof eventPayload.room === 'object') applyRoom(eventPayload.room);
      if (eventPayload.message) { appendSystemChat(String(eventPayload.message)); showToast(String(eventPayload.message), 'info'); }
      return;
    }

    if (type === 'match_chat') {
      appendChatBubble(asObject(message.data));
      scheduleRender('chat');
      return;
    }

    if (type === 'error') {
      showToast(String(message.message || message.code || 'Socket error'), 'error');
    }
  }

  function scheduleReconnect() {
    if (state.reconnectTimer) return;
    state.reconnectAttempts += 1;
    var delayMs = Math.min(20000, 1000 * Math.max(1, state.reconnectAttempts));
    state.reconnectTimer = window.setTimeout(function () { state.reconnectTimer = null; connectSocket(); }, delayMs);
    scheduleRender('socket');
  }

  function clearReconnectTimer() {
    if (!state.reconnectTimer) return;
    window.clearTimeout(state.reconnectTimer);
    state.reconnectTimer = null;
  }

  function startPresenceHeartbeat() {
    if (state.presenceTimer) window.clearInterval(state.presenceTimer);
    state.presenceTimer = window.setInterval(function () {
      if (state.wsConnected) sendSocket({ type: 'presence_ping', status: document.hidden ? 'away' : 'online' });
    }, 15000);
  }

  function startFallbackSync() {
    if (state.fallbackSyncTimer) window.clearInterval(state.fallbackSyncTimer);
    state.fallbackSyncTimer = window.setInterval(function () { if (!state.wsConnected) refreshRoom(); }, 20000);
  }

  // =====================================================================
  //  NETWORK ACTIONS
  // =====================================================================
  async function handleCheckIn() {
    if (state.requestBusy) return;
    var endpoint = String(asObject(state.room.urls).check_in || '');
    if (!endpoint) { showToast('Check-in endpoint unavailable.', 'error'); return; }
    state.requestBusy = true;
    try {
      var response = await fetch(endpoint, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' } });
      var data = await parseJsonResponse(response);
      if (!response.ok || !bool(data.success, false)) throw new Error(String(data.error || 'Check-in failed.'));
      if (data.room && typeof data.room === 'object') applyRoom(data.room);
      if (bool(data.checked_in, false)) showToast('Check-in complete.', 'success');
      else if (bool(data.already_checked_in, false)) showToast('Already checked in.', 'info');
    } catch (error) { showToast(String(error && error.message ? error.message : 'Check-in failed.'), 'error'); }
    finally { state.requestBusy = false; scheduleRender('engine'); }
  }

  async function sendWorkflowAction(action, payload) {
    if (state.requestBusy) return;
    if (actionRequiresPresence(action) && waitingLocked() && action !== 'presence_ping') { showToast('Waiting for opponent websocket presence.', 'info'); return; }
    var endpoint = String(asObject(state.room.urls).workflow || '');
    if (!endpoint) { showToast('Workflow endpoint unavailable.', 'error'); return; }
    state.requestBusy = true;
    try {
      var response = await fetch(endpoint, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' }, body: JSON.stringify(Object.assign({ action: action }, asObject(payload))) });
      var data = await parseJsonResponse(response);
      if (!response.ok || !bool(data.success, false)) throw new Error(String(data.error || 'Action failed.'));
      if (data.room && typeof data.room === 'object') applyRoom(data.room);
      if (data.message) { appendSystemChat(String(data.message)); showToast(String(data.message), 'success'); }
    } catch (error) { showToast(String(error && error.message ? error.message : 'Action failed.'), 'error'); }
    finally { state.requestBusy = false; scheduleRender('engine'); }
  }

  async function sendWorkflowMultipartAction(formData) {
    if (state.requestBusy) return;
    var action = String(formData.get('action') || '').trim().toLowerCase();
    if (actionRequiresPresence(action) && waitingLocked()) { showToast('Waiting for opponent websocket presence.', 'info'); return; }
    var endpoint = String(asObject(state.room.urls).workflow || '');
    if (!endpoint) { showToast('Workflow endpoint unavailable.', 'error'); return; }
    state.requestBusy = true;
    try {
      var response = await fetch(endpoint, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' }, body: formData });
      var data = await parseJsonResponse(response);
      if (!response.ok || !bool(data.success, false)) throw new Error(String(data.error || 'Action failed.'));
      if (data.room && typeof data.room === 'object') applyRoom(data.room);
      if (data.message) { appendSystemChat(String(data.message)); showToast(String(data.message), 'success'); }
    } catch (error) { showToast(String(error && error.message ? error.message : 'Action failed.'), 'error'); }
    finally { state.requestBusy = false; scheduleRender('engine'); }
  }

  async function refreshRoom() {
    var endpoint = String(asObject(state.room.urls).workflow || '');
    if (!endpoint) return;
    try {
      var response = await fetch(endpoint, { method: 'GET', credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      var data = await parseJsonResponse(response);
      if (response.ok && bool(data.success, false) && data.room && typeof data.room === 'object') applyRoom(data.room);
    } catch (_) { /* silent fallback */ }
  }

  async function signalReferee() {
    if (bool(asObject(state.room.me).is_staff, false)) { showToast('Use TOC verification panel for organizer dispute actions.', 'info'); return; }
    var summaryRaw = window.prompt('SOS headline', 'Opponent disconnected / technical issue');
    if (summaryRaw === null) return;
    var summary = String(summaryRaw || '').trim();
    if (summary.length < 3) { showToast('SOS headline must be at least 3 characters.', 'error'); return; }
    var descriptionRaw = window.prompt('Describe the issue for TOC support (minimum 10 characters).');
    if (descriptionRaw === null) return;
    var description = String(descriptionRaw || '').trim();
    if (description.length < 10) { showToast('Description must be at least 10 characters.', 'error'); return; }
    var matchRef = String(asObject(state.room.match).id || '');
    var supportSent = false, supportMessage = 'Support alert sent.';
    try { supportMessage = await submitSupportTicket(summary, description, matchRef); supportSent = true; } catch (_) { supportSent = false; }
    var disputeFallbackSent = false;
    if (!supportSent) disputeFallbackSent = await notifyDisputeFallback(summary, description);
    if (supportSent || disputeFallbackSent) { showToast(supportSent ? supportMessage : 'Support alert sent via dispute channel.', 'success'); appendSystemChat('SOS alert sent to tournament support.'); return; }
    showToast('Failed to notify support. Please retry.', 'error');
  }

  async function submitSupportTicket(summary, description, matchRef) {
    var supportUrl = String(asObject(state.room.urls).support || '');
    if (!supportUrl) throw new Error('Support channel unavailable.');
    var matchId = matchRef || String(asObject(state.room.match).id || 'N/A');
    var response = await fetch(supportUrl, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' }, body: JSON.stringify({ category: 'technical', subject: 'SOS Match ' + matchId + ': ' + summary, message: description, match_ref: String(matchId) }) });
    var data = await parseJsonResponse(response);
    if (!response.ok) throw new Error(String(data.error || 'Support request failed.'));
    return String(data.message || 'Support ticket sent to TOC.');
  }

  async function notifyDisputeFallback(summary, description) {
    var reportUrl = String(asObject(state.room.urls).report_dispute || '');
    if (!reportUrl) return false;
    var body = new URLSearchParams();
    body.set('reason', deriveDisputeReason(summary));
    body.set('description', description);
    try {
      var response = await fetch(reportUrl, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' }, body: body.toString() });
      var data = await parseJsonResponse(response);
      return response.ok && bool(data.success, false);
    } catch (_) { return false; }
  }

  function deriveDisputeReason(summary) {
    var token = String(summary || '').toLowerCase();
    if (token.includes('score') || token.includes('mismatch') || token.includes('result')) return 'score_mismatch';
    if (token.includes('disconnect') || token.includes('lag') || token.includes('tech')) return 'technical_issue';
    return 'other';
  }

  // =====================================================================
  //  ADMIN ACTIONS
  // =====================================================================
  async function handleAdminForceNext() {
    if (!bool(asObject(state.room.me).admin_mode, false)) { showToast('Admin mode required.', 'error'); return; }
    var order = phaseOrder();
    var index = order.indexOf(currentPhase());
    if (index < 0 || index + 1 >= order.length) { showToast('No next phase available.', 'info'); return; }
    await sendWorkflowAction('advance_phase', { phase: order[index + 1] });
  }

  async function handleAdminBroadcast() {
    if (!bool(asObject(state.room.me).admin_mode, false)) { showToast('Admin mode required.', 'error'); return; }
    var message = window.prompt('System announcement message:');
    if (!message || !String(message).trim()) return;
    await sendWorkflowAction('system_announcement', { message: String(message).trim() });
  }

  function openOverrideModal() {
    if (!bool(asObject(state.room.me).admin_mode, false)) { showToast('Admin mode required.', 'error'); return; }
    var match = asObject(state.room.match);
    if (elements.overrideP1) elements.overrideP1.value = String(toInt(asObject(match.participant1).score, 0));
    if (elements.overrideP2) elements.overrideP2.value = String(toInt(asObject(match.participant2).score, 0));
    if (elements.overrideNote) elements.overrideNote.value = '';
    if (elements.overrideModal) { elements.overrideModal.classList.remove('hidden-state'); elements.overrideModal.classList.add('flex'); }
  }

  function closeOverrideModal() {
    if (!elements.overrideModal) return;
    elements.overrideModal.classList.add('hidden-state');
    elements.overrideModal.classList.remove('flex');
  }

  async function applyOverrideResult() {
    var p1 = toInt(elements.overrideP1 ? elements.overrideP1.value : '', -1);
    var p2 = toInt(elements.overrideP2 ? elements.overrideP2.value : '', -1);
    if (p1 < 0 || p2 < 0) { showToast('Override scores must be >= 0.', 'error'); return; }
    var note = elements.overrideNote ? String(elements.overrideNote.value || '').trim() : '';
    await sendWorkflowAction('admin_override_result', { participant1_score: p1, participant2_score: p2, note: note });
    closeOverrideModal();
  }

  // =====================================================================
  //  TOAST
  // =====================================================================
  function showToast(message, kind) {
    if (!elements.roomToast) return;
    var text = String(message || '').trim();
    if (!text) return;
    var now = nowMs();
    if (state.lastToastText === text && now - state.lastToastAt < 1500) return;
    state.lastToastText = text;
    state.lastToastAt = now;
    var color = kind === 'error' ? 'border-red-400/40 text-red-100' : (kind === 'success' ? 'border-green-400/40 text-green-100' : 'border-white/20 text-white');
    var toast = document.createElement('div');
    toast.className = 'opacity-0 translate-y-2 transition-all duration-300 ' + color;
    toast.innerHTML = '<div class="rounded-xl px-4 py-3 bg-black/85 border ' + color + ' text-sm font-semibold">' + esc(text) + '</div>';
    elements.roomToast.appendChild(toast);
    window.requestAnimationFrame(function () { toast.classList.remove('opacity-0', 'translate-y-2'); });
    window.setTimeout(function () { toast.classList.add('opacity-0', 'translate-y-2'); window.setTimeout(function () { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 280); }, 3200);
  }

  // =====================================================================
  //  EVENT BINDING
  // =====================================================================
  function bindStaticEvents() {
    if (elements.chatForm) elements.chatForm.addEventListener('submit', function (e) { e.preventDefault(); submitChat(elements.chatInput); });
    if (elements.dtTabChat) elements.dtTabChat.addEventListener('click', function () { setDesktopTab('chat'); });
    if (elements.dtTabIntel) elements.dtTabIntel.addEventListener('click', function () { setDesktopTab('intel'); });
    if (elements.dtTabAdmin) elements.dtTabAdmin.addEventListener('click', function () { setDesktopTab('admin'); });
    if (elements.mobTabEngine) elements.mobTabEngine.addEventListener('click', function () { setMobileTab('engine'); });
    if (elements.mobTabChat) elements.mobTabChat.addEventListener('click', function () { setMobileTab('chat'); });
    if (elements.mobTabIntel) elements.mobTabIntel.addEventListener('click', function () { setMobileTab('intel'); });
    if (elements.adminForceNext) elements.adminForceNext.addEventListener('click', handleAdminForceNext);
    if (elements.adminOpenOverride) elements.adminOpenOverride.addEventListener('click', openOverrideModal);
    if (elements.adminBroadcast) elements.adminBroadcast.addEventListener('click', handleAdminBroadcast);
    if (elements.overrideClose) elements.overrideClose.addEventListener('click', closeOverrideModal);
    if (elements.overrideCancel) elements.overrideCancel.addEventListener('click', closeOverrideModal);
    if (elements.overrideApply) elements.overrideApply.addEventListener('click', applyOverrideResult);
    if (elements.helpSignalBtn) elements.helpSignalBtn.addEventListener('click', function () { signalReferee(); });

    // Engine delegated events — route to active phase module or built-in handlers
    if (elements.engineContainer) {
      elements.engineContainer.addEventListener('click', handleEngineClick);
      elements.engineContainer.addEventListener('submit', handleEngineSubmit);
    }

    // Presence visibility
    document.addEventListener('visibilitychange', function () {
      if (state.wsConnected) sendSocket({ type: 'presence_ping', status: document.hidden ? 'away' : 'online' });
    });
  }

  async function handleEngineClick(event) {
    var trigger = event.target.closest('[data-action]');
    if (!trigger) return;
    var action = String(trigger.getAttribute('data-action') || '');
    if (!action) return;

    // Check phase module first
    var phase = currentPhase();
    var mod = phaseRegistry[phase];
    if (!mod && phase === 'phase1') mod = phase1Kind() === 'direct' ? phaseRegistry['direct_ready'] : phaseRegistry['map_veto'];
    if (mod && typeof mod.onAction === 'function') {
      var handled = await mod.onAction(action, trigger, ctx());
      if (handled) return;
    }

    // Built-in handlers
    if (action === 'check-in') { await handleCheckIn(); return; }
    if (action === 'refresh-room') { await refreshRoom(); return; }
  }

  async function handleEngineSubmit(event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement)) return;

    // Check phase module
    var phase = currentPhase();
    var mod = phaseRegistry[phase];
    if (!mod && phase === 'phase1') mod = phase1Kind() === 'direct' ? phaseRegistry['direct_ready'] : phaseRegistry['map_veto'];
    if (mod && typeof mod.onSubmit === 'function') {
      event.preventDefault();
      await mod.onSubmit(form, ctx());
      return;
    }

    // Built-in form handlers
    if (form.id === 'credentials-form') { event.preventDefault(); await handleSaveCredentials(); return; }
    if (form.id === 'result-submit-form') { event.preventDefault(); await handleSubmitResult(); return; }
  }

  async function handleSaveCredentials() {
    var payload = {};
    credentialSchema().forEach(function (field) {
      var key = String(asObject(field).key || '').trim();
      if (key) payload[key] = valueOf(credentialInputId(key));
    });
    await sendWorkflowAction('save_credentials', payload);
  }

  async function handleSubmitResult() {
    var scoreFor = toInt(valueOf('result-score-for'), -1);
    var scoreAgainst = toInt(valueOf('result-score-against'), -1);
    if (scoreFor < 0 || scoreAgainst < 0) { showToast('Scores must be non-negative integers.', 'error'); return; }
    var proofFileInput = byId('result-proof-file');
    var proofFile = proofFileInput && proofFileInput.files && proofFileInput.files.length ? proofFileInput.files[0] : null;
    var proofUrl = valueOf('result-proof-url');
    if (requiresMatchEvidence() && !proofFile) { showToast('Evidence image is required before submitting.', 'error'); return; }
    if (proofFile && !String(proofFile.type || '').toLowerCase().startsWith('image/')) { showToast('Only image files are allowed for evidence upload.', 'error'); return; }
    if (proofFile && Number(proofFile.size || 0) > (10 * 1024 * 1024)) { showToast('Evidence image exceeds 10MB limit.', 'error'); return; }
    var formData = new FormData();
    formData.append('action', 'submit_result');
    formData.append('score_for', String(scoreFor));
    formData.append('score_against', String(scoreAgainst));
    formData.append('note', valueOf('result-note'));
    if (proofUrl) formData.append('proof_screenshot_url', proofUrl);
    if (proofFile) formData.append('proof', proofFile);
    await sendWorkflowMultipartAction(formData);
  }

  // =====================================================================
  //  TIMER LIFECYCLE — cleanly tear down on unload / pagehide
  // =====================================================================
  function teardownTimers() {
    if (state.noShowTimer) { window.clearInterval(state.noShowTimer); state.noShowTimer = null; }
    if (state.presenceTimer) { window.clearInterval(state.presenceTimer); state.presenceTimer = null; }
    if (state.fallbackSyncTimer) { window.clearInterval(state.fallbackSyncTimer); state.fallbackSyncTimer = null; }
    if (state.reconnectTimer) { window.clearTimeout(state.reconnectTimer); state.reconnectTimer = null; }
    if (state._rafRender) { window.cancelAnimationFrame(state._rafRender); state._rafRender = null; }
    if (state.ws) {
      try { state.ws.close(1000, 'page_unload'); } catch (_) { /* ignore */ }
      state.ws = null;
    }
    state.wsConnected = false;
  }

  window.addEventListener('beforeunload', function () {
    setGlobalFocusMode(false);
    teardownTimers();
  });

  window.addEventListener('pagehide', function () {
    teardownTimers();
  });

  function setGlobalFocusMode(enabled) {
    var body = document.body;
    if (body) body.classList.toggle('match-room-focus-mode', Boolean(enabled));
  }

  // =====================================================================
  //  CONTEXT OBJECT — passed to phase modules
  // =====================================================================
  function ctx() {
    return {
      state: state,
      elements: elements,
      esc: esc,
      asObject: asObject,
      asList: asList,
      toInt: toInt,
      bool: bool,
      nowMs: nowMs,
      mySide: mySide,
      opponentSide: opponentSide,
      participantForSide: participantForSide,
      sideOnline: sideOnline,
      sideCheckedIn: sideCheckedIn,
      bothSidesOnline: bothSidesOnline,
      waitingLocked: waitingLocked,
      currentPhase: currentPhase,
      phaseOrder: phaseOrder,
      phase1Kind: phase1Kind,
      canonicalGameKey: canonicalGameKey,
      mapPool: mapPool,
      credentialSchema: credentialSchema,
      credentialInputId: credentialInputId,
      credentialLabelForKey: credentialLabelForKey,
      workflowSubmission: workflowSubmission,
      workflowResultVisibility: workflowResultVisibility,
      requiresMatchEvidence: requiresMatchEvidence,
      hasSubmittedResultForSide: hasSubmittedResultForSide,
      effectivePolicy: effectivePolicy,
      formatLocalTime: formatLocalTime,
      shortClock: shortClock,
      valueOf: valueOf,
      showToast: showToast,
      sendWorkflowAction: sendWorkflowAction,
      sendWorkflowMultipartAction: sendWorkflowMultipartAction,
      applyRoom: applyRoom,
      appendSystemChat: appendSystemChat,
      scheduleRender: scheduleRender,
      maybeRunIcons: maybeRunIcons,
      byId: byId,
    };
  }

  // =====================================================================
  //  GLOBAL API — phase modules register via window.MatchRoom
  // =====================================================================
  window.MatchRoom = {
    registerPhase: function (key, mod) {
      if (!key || !mod) return;
      phaseRegistry[key] = mod;
    },
    ctx: ctx,
  };

  // =====================================================================
  //  INIT
  // =====================================================================
  function init() {
    setGlobalFocusMode(true);
    state.lastWaitingLocked = waitingLocked();
    bindStaticEvents();
    updateShellViewportHeight();
    ensureNoShowTicker();
    renderAll();
    loadTimePreferences().then(function () { scheduleRender('full'); }).catch(function () { });
    initMobileTopNavBehavior();
    connectSocket();
    startPresenceHeartbeat();
    startFallbackSync();
  }

  // Wait for phase modules to register, then init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
