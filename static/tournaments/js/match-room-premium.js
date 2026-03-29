(function () {
  'use strict';

  const payloadNode = document.getElementById('match-room-payload');
  if (!payloadNode) return;

  let room = {};
  try {
    room = JSON.parse(payloadNode.textContent || '{}');
  } catch (_err) {
    room = {};
  }

  if (!room || !room.match || !room.urls) return;

  const phaseOrder = [
    { key: 'coin_toss', label: 'Coin Toss' },
    { key: 'phase1', label: 'Phase One' },
    { key: 'lobby_setup', label: 'Lobby Setup' },
    { key: 'live', label: 'Live' },
    { key: 'results', label: 'Results' },
    { key: 'completed', label: 'Complete' },
  ];

  let ws = null;
  let wsConnected = false;
  let reconnectTimer = null;
  let syncTimer = null;
  let toastTimer = null;

  const chatSeen = new Set();

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

  function getCsrfToken() {
    const row = document.cookie.split('; ').find((chunk) => chunk.startsWith('csrftoken='));
    return row ? decodeURIComponent(row.substring('csrftoken='.length)) : '';
  }

  function showToast(message) {
    const el = byId('mr-toast');
    if (!el) return;
    el.textContent = String(message || 'Updated');
    el.classList.add('show');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.classList.remove('show');
    }, 1800);
  }

  function formatTime(iso) {
    if (!iso) return '--';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (_err) {
      return '--';
    }
  }

  function stateBadgeClass(state) {
    const safe = String(state || '').toLowerCase();
    if (safe === 'live') return 'mr-badge live';
    if (safe === 'completed' || safe === 'forfeit' || safe === 'cancelled') return 'mr-badge done';
    return 'mr-badge';
  }

  function phaseIndex(phaseKey) {
    const idx = phaseOrder.findIndex((entry) => entry.key === phaseKey);
    return idx < 0 ? 0 : idx;
  }

  function isStaff() {
    return !!(room.me && room.me.is_staff);
  }

  function mySide() {
    return Number((room.me && room.me.side) || 0);
  }

  function canEditCredentials() {
    return !!(room.me && room.me.can_edit_credentials);
  }

  function canSubmitResultFor(side) {
    return isStaff() || mySide() === Number(side);
  }

  function currentWorkflow() {
    return room.workflow || {};
  }

  function ensureChatWindowHint() {
    const chatWin = byId('mr-chat-window');
    if (!chatWin) return;
    if (!chatWin.childElementCount) {
      appendChatMessage({
        username: 'System',
        text: 'Realtime chat channel initialized.',
        timestamp: new Date().toISOString(),
      }, 'system');
    }
  }

  function appendChatMessage(data, mode) {
    const chatWin = byId('mr-chat-window');
    if (!chatWin || !data) return;

    const msgId = data.message_id || `${data.username || 'system'}:${data.timestamp || Date.now()}:${data.text || ''}`;
    if (chatSeen.has(msgId)) return;
    chatSeen.add(msgId);

    const row = document.createElement('div');
    row.className = `mr-chat-msg ${mode === 'mine' ? 'mine' : ''} ${mode === 'system' ? 'system' : ''}`.trim();

    const head = document.createElement('div');
    head.className = 'mr-chat-head';
    const who = mode === 'system'
      ? 'System'
      : `${data.username || 'User'}${data.side ? ` (Side ${data.side})` : ''}${data.is_staff ? ' [Staff]' : ''}`;
    head.innerHTML = `<span>${esc(who)}</span><span>${esc(formatTime(data.timestamp))}</span>`;

    const body = document.createElement('div');
    body.innerHTML = esc(data.text || '');

    row.appendChild(head);
    row.appendChild(body);
    chatWin.appendChild(row);
    chatWin.scrollTop = chatWin.scrollHeight;
  }

  function renderHeader() {
    const subtitle = byId('mr-subtitle');
    const badge = byId('mr-state-badge');

    const p1 = room.match.participant1 || {};
    const p2 = room.match.participant2 || {};

    byId('mr-team-1-name').textContent = p1.name || 'TBD';
    byId('mr-team-2-name').textContent = p2.name || 'TBD';

    byId('mr-team-1-meta').textContent = p1.checked_in ? 'Checked in' : 'Not checked in';
    byId('mr-team-2-meta').textContent = p2.checked_in ? 'Checked in' : 'Not checked in';

    const s1 = Number(p1.score || 0);
    const s2 = Number(p2.score || 0);
    byId('mr-score-main').textContent = `${s1} - ${s2}`;
    byId('mr-score-sub').textContent = `Best of ${room.match.best_of || 1}`;

    if (subtitle) {
      subtitle.textContent = `${room.tournament.name} | Round ${room.match.round_number} Match ${room.match.match_number} | ${room.game.name}`;
    }

    if (badge) {
      badge.className = stateBadgeClass(room.match.state);
      badge.textContent = room.match.state_display || room.match.state || 'State';
    }
  }

  function renderPhaseTrack() {
    const host = byId('mr-phase-track');
    if (!host) return;

    const activeIndex = phaseIndex((currentWorkflow().phase || 'coin_toss'));
    host.innerHTML = phaseOrder
      .map((entry, idx) => {
        let cls = 'mr-phase-pill';
        if (idx < activeIndex) cls += ' complete';
        if (idx === activeIndex) cls += ' active';
        return `<div class="${cls}">${esc(entry.label)}</div>`;
      })
      .join('');
  }

  function renderCoinTossCard() {
    const card = byId('mr-coin-toss-card');
    const btn = byId('mr-coin-btn');
    const summary = byId('mr-coin-summary');
    if (!card || !btn || !summary) return;

    const wf = currentWorkflow();
    const phase = String(wf.phase || 'coin_toss');
    const coin = wf.coin_toss || {};
    const winner = Number(coin.winner_side || 0);

    if (winner === 1 || winner === 2) {
      summary.textContent = `Coin toss completed. Side ${winner} has first control.`;
      btn.textContent = 'Re-run Toss';
    } else {
      summary.textContent = 'Resolve side priority for phase one.';
      btn.textContent = 'Run Coin Toss';
    }

    const canRun = phase === 'coin_toss' || isStaff();
    btn.disabled = !canRun;
  }

  function renderPhaseOne() {
    const title = byId('mr-phase1-title');
    const turn = byId('mr-phase1-turn');
    const poolHost = byId('mr-phase1-pool');
    const log = byId('mr-phase1-log');
    if (!title || !turn || !poolHost || !log) return;

    const wf = currentWorkflow();
    const phase = String(wf.phase || 'coin_toss');
    const mode = String(wf.mode || room.game.phase_mode || 'veto');

    poolHost.innerHTML = '';
    log.textContent = '';

    if (mode === 'direct') {
      title.textContent = 'Phase One - Ready Confirmation';
      const ready = wf.direct_ready || {};
      const r1 = !!ready['1'];
      const r2 = !!ready['2'];
      turn.textContent = `Side 1: ${r1 ? 'Ready' : 'Waiting'} | Side 2: ${r2 ? 'Ready' : 'Waiting'}`;

      [1, 2].forEach((side) => {
        const card = document.createElement('div');
        card.className = 'mr-pool-item';

        const status = side === 1 ? (r1 ? 'Ready' : 'Not ready') : (r2 ? 'Ready' : 'Not ready');
        const canAct = isStaff() || mySide() === side;
        const disabled = !canAct || phase === 'live' || phase === 'results' || phase === 'completed';

        card.innerHTML = `<span>Side ${side}: ${esc(status)}</span>`;

        const btn = document.createElement('button');
        btn.textContent = 'Mark Ready';
        btn.disabled = disabled;
        btn.addEventListener('click', () => {
          submitWorkflow('direct_ready', {
            ready: true,
            acting_side: side,
          });
        });
        card.appendChild(btn);
        poolHost.appendChild(card);
      });

      return;
    }

    if (mode === 'draft') {
      title.textContent = 'Phase One - Hero Draft';
      const draft = wf.draft || {};
      const sequence = Array.isArray(draft.sequence) ? draft.sequence : [];
      const step = Number(draft.step || 0);
      const expected = sequence[step] || null;
      const expectedSide = expected ? Number(expected.side || 1) : 1;
      const expectedAction = expected ? String(expected.action || 'ban').toUpperCase() : 'DONE';
      const canAct = expected && (isStaff() || mySide() === expectedSide) && phase === 'phase1';

      turn.textContent = expected
        ? `Turn: Side ${expectedSide} ${expectedAction}`
        : 'Draft sequence completed.';

      const bans = Array.isArray(draft.bans) ? draft.bans : [];
      const picksObj = draft.picks || {};
      const picks1 = Array.isArray(picksObj['1']) ? picksObj['1'] : [];
      const picks2 = Array.isArray(picksObj['2']) ? picksObj['2'] : [];
      const used = new Set([...bans, ...picks1, ...picks2]);
      const pool = Array.isArray(draft.pool) ? draft.pool : (room.game.hero_pool || []);

      pool.forEach((item) => {
        const label = String(item || '').trim();
        if (!label) return;

        const row = document.createElement('div');
        row.className = 'mr-pool-item';

        const btn = document.createElement('button');
        btn.textContent = expectedAction;
        btn.disabled = !canAct || used.has(label);
        btn.addEventListener('click', () => {
          submitWorkflow('draft_action', {
            item: label,
            acting_side: expectedSide,
          });
        });

        row.innerHTML = `<span>${esc(label)}</span>`;
        row.appendChild(btn);
        poolHost.appendChild(row);
      });

      const picksText = `Side 1 picks: ${picks1.join(', ') || '-'} | Side 2 picks: ${picks2.join(', ') || '-'}`;
      const bansText = `Bans: ${bans.join(', ') || '-'}`;
      log.textContent = `${picksText}. ${bansText}.`;
      return;
    }

    title.textContent = 'Phase One - Map Veto';
    const veto = wf.veto || {};
    const sequence = Array.isArray(veto.sequence) ? veto.sequence : [];
    const step = Number(veto.step || 0);
    const expected = sequence[step] || null;
    const expectedSide = expected ? Number(expected.side || 1) : 1;
    const expectedAction = expected ? String(expected.action || 'ban').toUpperCase() : 'DONE';
    const canAct = expected && (isStaff() || mySide() === expectedSide) && phase === 'phase1';

    turn.textContent = expected
      ? `Turn: Side ${expectedSide} ${expectedAction}`
      : 'Veto sequence completed.';

    const bans = Array.isArray(veto.bans) ? veto.bans : [];
    const picks = Array.isArray(veto.picks) ? veto.picks : [];
    const pool = Array.isArray(veto.pool) ? veto.pool : (room.game.map_pool || []);
    const used = new Set([...bans, ...picks]);

    pool.forEach((item) => {
      const label = String(item || '').trim();
      if (!label) return;

      const row = document.createElement('div');
      row.className = 'mr-pool-item';

      const btn = document.createElement('button');
      btn.textContent = expectedAction;
      btn.disabled = !canAct || used.has(label);
      btn.addEventListener('click', () => {
        submitWorkflow('veto_action', {
          item: label,
          acting_side: expectedSide,
        });
      });

      row.innerHTML = `<span>${esc(label)}</span>`;
      row.appendChild(btn);
      poolHost.appendChild(row);
    });

    const selected = String(veto.selected_map || '').trim();
    const bansText = `Bans: ${bans.join(', ') || '-'}`;
    const picksText = `Picks: ${picks.join(', ') || '-'}`;
    log.textContent = `${bansText}. ${picksText}. ${selected ? `Selected map: ${selected}.` : ''}`;
  }

  function renderCredentials() {
    const wf = currentWorkflow();
    const creds = wf.credentials || {};

    const codeInput = byId('mr-cred-code');
    const passInput = byId('mr-cred-password');
    const mapInput = byId('mr-cred-map');
    const serverInput = byId('mr-cred-server');
    const modeInput = byId('mr-cred-mode');
    const notesInput = byId('mr-cred-notes');

    if (codeInput) codeInput.value = String(creds.lobby_code || room.lobby?.lobby_code || '');
    if (passInput) passInput.value = String(creds.password || room.lobby?.password || '');
    if (mapInput) mapInput.value = String(creds.map || room.lobby?.map || '');
    if (serverInput) serverInput.value = String(creds.server || room.lobby?.server || '');
    if (modeInput) modeInput.value = String(creds.game_mode || room.lobby?.game_mode || '');
    if (notesInput) notesInput.value = String(creds.notes || '');

    const editable = canEditCredentials();
    [codeInput, passInput, mapInput, serverInput, modeInput, notesInput].forEach((node) => {
      if (!node) return;
      node.disabled = !editable;
    });

    const saveBtn = byId('mr-save-credentials-btn');
    if (saveBtn) saveBtn.disabled = !editable;

    const startBtn = byId('mr-start-live-btn');
    if (startBtn) startBtn.disabled = !(room.me && room.me.can_submit_result);
  }

  function renderLobbySnapshot() {
    const target = byId('mr-lobby-snapshot');
    if (!target) return;

    const l = room.lobby || {};
    const rows = [];
    if (l.lobby_code) rows.push(`Code: ${esc(l.lobby_code)}`);
    if (l.password) rows.push(`Password: ${esc(l.password)}`);
    if (l.map) rows.push(`Map: ${esc(l.map)}`);
    if (l.server) rows.push(`Server: ${esc(l.server)}`);
    if (l.game_mode) rows.push(`Mode: ${esc(l.game_mode)}`);

    if (!rows.length) {
      target.textContent = 'No lobby credentials yet.';
      return;
    }

    target.innerHTML = rows.map((line) => `<div>${line}</div>`).join('');
  }

  function renderResultCards() {
    const host = byId('mr-result-grid');
    const statusNode = byId('mr-result-status');
    if (!host || !statusNode) return;

    const wf = currentWorkflow();
    const submissions = wf.result_submissions || { '1': null, '2': null };
    const resultStatus = String(wf.result_status || 'pending');
    const finalResult = wf.final_result || null;

    statusNode.textContent = `Result status: ${resultStatus.replaceAll('_', ' ')}`;
    if (finalResult && typeof finalResult === 'object') {
      const p1 = Number(finalResult.participant1_score || 0);
      const p2 = Number(finalResult.participant2_score || 0);
      statusNode.textContent = `Finalized: ${p1} - ${p2} (${resultStatus.replaceAll('_', ' ')})`;
    }

    host.innerHTML = '';

    [1, 2].forEach((side) => {
      const submission = submissions[String(side)] || {};
      const canSubmit = canSubmitResultFor(side);
      const p = side === 1 ? (room.match.participant1 || {}) : (room.match.participant2 || {});

      const card = document.createElement('div');
      card.className = 'mr-result-card';
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.45rem;">
          <strong style="font-size:0.83rem;">${esc(p.name || `Side ${side}`)}</strong>
          <span class="mr-muted">Side ${side}</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0.45rem;">
          <input class="mr-input" id="mr-side-${side}-for" type="number" min="0" placeholder="For" value="${esc(submission.score_for || '')}">
          <input class="mr-input" id="mr-side-${side}-against" type="number" min="0" placeholder="Against" value="${esc(submission.score_against || '')}">
        </div>
        <textarea class="mr-textarea" id="mr-side-${side}-note" placeholder="Optional note" style="margin-top:0.45rem;min-height:64px;">${esc(submission.note || '')}</textarea>
        <div class="mr-split-actions" style="margin-top:0.45rem;">
          <button class="mr-action-btn" id="mr-side-${side}-submit">Submit Side ${side}</button>
        </div>
      `;

      host.appendChild(card);

      const submitBtn = byId(`mr-side-${side}-submit`);
      if (submitBtn) {
        submitBtn.disabled = !canSubmit;
        submitBtn.addEventListener('click', () => {
          const scoreFor = byId(`mr-side-${side}-for`)?.value;
          const scoreAgainst = byId(`mr-side-${side}-against`)?.value;
          const note = byId(`mr-side-${side}-note`)?.value || '';

          submitWorkflow('submit_result', {
            score_for: scoreFor,
            score_against: scoreAgainst,
            note,
            acting_side: side,
          });
        });
      }
    });

    const adminWrap = byId('mr-admin-override');
    if (adminWrap) {
      adminWrap.style.display = isStaff() ? '' : 'none';
    }
  }

  function renderQuickActions() {
    const checkInBtn = byId('mr-checkin-btn');
    if (!checkInBtn) return;

    const p1 = room.match.participant1 || {};
    const p2 = room.match.participant2 || {};

    const alreadyCheckedIn = mySide() === 1 ? !!p1.checked_in : mySide() === 2 ? !!p2.checked_in : false;
    const canCheckIn = mySide() === 1 || mySide() === 2;

    checkInBtn.disabled = !canCheckIn || alreadyCheckedIn;
    checkInBtn.textContent = alreadyCheckedIn ? 'Checked In' : 'Check In';

    const note = byId('mr-quick-note');
    if (note) {
      note.textContent = wsConnected ? 'Realtime websocket is connected.' : 'Realtime websocket is reconnecting. Poll sync is active.';
    }
  }

  function renderAll() {
    renderHeader();
    renderPhaseTrack();
    renderCoinTossCard();
    renderPhaseOne();
    renderCredentials();
    renderLobbySnapshot();
    renderResultCards();
    renderQuickActions();
    ensureChatWindowHint();
  }

  async function submitWorkflow(action, payload) {
    const body = Object.assign({ action }, payload || {});
    try {
      const response = await fetch(room.urls.workflow, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        showToast(data.error || 'Action failed');
        return;
      }

      room = data.room || room;
      renderAll();
      if (data.message) showToast(data.message);
    } catch (_err) {
      showToast('Network error while updating workflow');
    }
  }

  async function submitCheckIn() {
    try {
      const response = await fetch(room.urls.check_in, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        showToast(data.error || 'Check-in failed');
        return;
      }

      if (data.room) {
        room = data.room;
      } else {
        await syncWorkflow();
      }
      renderAll();
      showToast('Check-in completed');
    } catch (_err) {
      showToast('Network error while checking in');
    }
  }

  async function syncWorkflow() {
    try {
      const response = await fetch(room.urls.workflow, {
        method: 'GET',
        credentials: 'same-origin',
      });
      const data = await response.json();
      if (!response.ok || !data.success) return;
      room = data.room || room;
      renderAll();
    } catch (_err) {
      // Silent sync failure.
    }
  }

  function onWebSocketMessage(parsed) {
    if (!parsed || typeof parsed !== 'object') return;

    if (parsed.type === 'match_room_event') {
      const payload = parsed.data && parsed.data.payload;
      if (payload && payload.room) {
        room = payload.room;
        renderAll();
      }
      const message = payload && payload.message;
      if (message) appendChatMessage({ username: 'System', text: message, timestamp: new Date().toISOString() }, 'system');
      return;
    }

    if (parsed.type === 'match_chat') {
      const chat = parsed.data || {};
      const mine = Number(chat.user_id || 0) === Number(room.me && room.me.user_id);
      appendChatMessage(chat, mine ? 'mine' : 'peer');
      return;
    }

    if (parsed.type === 'connection_established') {
      appendChatMessage({
        username: 'System',
        text: 'Realtime channel connected.',
        timestamp: new Date().toISOString(),
      }, 'system');
      return;
    }

    if (parsed.type === 'error') {
      showToast(parsed.message || 'Socket error');
    }
  }

  function connectWebSocket() {
    if (!room.match || !room.match.id) return;

    if (ws) {
      try {
        ws.close();
      } catch (_err) {
        // ignore
      }
      ws = null;
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

    ws = new window.WebSocket(wsUrl);

    ws.onopen = function () {
      wsConnected = true;
      renderQuickActions();
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      try {
        ws.send(JSON.stringify({ type: 'subscribe' }));
      } catch (_err) {
        // ignore
      }
    };

    ws.onmessage = function (event) {
      let parsed = null;
      try {
        parsed = JSON.parse(event.data || '{}');
      } catch (_err) {
        parsed = null;
      }
      onWebSocketMessage(parsed);
    };

    ws.onclose = function () {
      wsConnected = false;
      renderQuickActions();
      if (!reconnectTimer) {
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      }
    };

    ws.onerror = function () {
      wsConnected = false;
      renderQuickActions();
    };
  }

  function bindEvents() {
    const coinBtn = byId('mr-coin-btn');
    if (coinBtn) {
      coinBtn.addEventListener('click', () => submitWorkflow('coin_toss', {}));
    }

    const saveCredBtn = byId('mr-save-credentials-btn');
    if (saveCredBtn) {
      saveCredBtn.addEventListener('click', () => {
        submitWorkflow('save_credentials', {
          lobby_code: byId('mr-cred-code')?.value || '',
          password: byId('mr-cred-password')?.value || '',
          map: byId('mr-cred-map')?.value || '',
          server: byId('mr-cred-server')?.value || '',
          game_mode: byId('mr-cred-mode')?.value || '',
          notes: byId('mr-cred-notes')?.value || '',
        });
      });
    }

    const startLiveBtn = byId('mr-start-live-btn');
    if (startLiveBtn) {
      startLiveBtn.addEventListener('click', () => submitWorkflow('start_live', {}));
    }

    const checkInBtn = byId('mr-checkin-btn');
    if (checkInBtn) {
      checkInBtn.addEventListener('click', submitCheckIn);
    }

    const adminOverrideBtn = byId('mr-admin-override-btn');
    if (adminOverrideBtn) {
      adminOverrideBtn.addEventListener('click', () => {
        submitWorkflow('admin_override_result', {
          participant1_score: byId('mr-admin-score-1')?.value || 0,
          participant2_score: byId('mr-admin-score-2')?.value || 0,
        });
      });
    }

    const chatForm = byId('mr-chat-form');
    if (chatForm) {
      chatForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const input = byId('mr-chat-input');
        if (!input) return;
        const text = String(input.value || '').trim();
        if (!text) return;

        if (!ws || ws.readyState !== window.WebSocket.OPEN) {
          showToast('Realtime channel is not connected yet.');
          return;
        }

        try {
          ws.send(JSON.stringify({ type: 'chat_message', text }));
          input.value = '';
        } catch (_err) {
          showToast('Failed sending chat message');
        }
      });
    }
  }

  function bootstrap() {
    renderAll();
    bindEvents();
    connectWebSocket();

    if (syncTimer) clearInterval(syncTimer);
    syncTimer = setInterval(syncWorkflow, 20000);
  }

  bootstrap();
})();
