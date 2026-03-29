/**
 * TOC Lobby Module — Sprint 28+ refresh
 * Centralized live-ops surface for server fleet and match lobby control.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);

  function toast(msg, type) {
    if (window.TOC?.toast) window.TOC.toast(msg, type);
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function refreshIcons() {
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function copyText(value) {
    const text = String(value || '');
    if (!text) return Promise.resolve(false);
    if (navigator.clipboard?.writeText) {
      return navigator.clipboard.writeText(text).then(() => true).catch(() => false);
    }

    const temp = document.createElement('textarea');
    temp.value = text;
    temp.setAttribute('readonly', 'readonly');
    temp.style.position = 'absolute';
    temp.style.left = '-9999px';
    document.body.appendChild(temp);
    temp.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch (_) {
      ok = false;
    }
    document.body.removeChild(temp);
    return Promise.resolve(ok);
  }

  const CACHE_TTL_MS = 20000;
  const AUTO_REFRESH_MS = 45000;
  const STAT_IDS = ['servers', 'active', 'pending', 'completed', 'online', 'idle'];
  const PANEL_IDS = ['lobby-priority-queue', 'lobby-servers-list', 'lobby-matches-list', 'lobby-config-section'];

  let dashData = null;
  let inflightPromise = null;
  let activeRequestId = 0;
  let lastFetchedAt = 0;
  let autoRefreshTimer = null;

  function isLobbyTabActive() {
    return (window.location.hash || '').replace('#', '') === 'lobby';
  }

  function hasFreshCache() {
    return !!dashData && (Date.now() - lastFetchedAt) < CACHE_TTL_MS;
  }

  function parseDate(raw) {
    if (!raw) return null;
    const dt = new Date(raw);
    return Number.isNaN(dt.getTime()) ? null : dt;
  }

  function formatClock(raw) {
    const dt = raw instanceof Date ? raw : parseDate(raw);
    if (!dt) return 'TBD';
    return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function formatDateTime(raw) {
    const dt = raw instanceof Date ? raw : parseDate(raw);
    if (!dt) return 'Schedule pending';
    return dt.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function minutesUntil(raw) {
    const dt = parseDate(raw);
    if (!dt) return null;
    return Math.floor((dt.getTime() - Date.now()) / 60000);
  }

  function stateMeta(state) {
    const s = String(state || '').toLowerCase();
    if (s === 'live') return { label: 'Live', cls: 'bg-dc-danger/20 border border-dc-danger/35 text-dc-danger' };
    if (s === 'ready') return { label: 'Ready', cls: 'bg-dc-success/15 border border-dc-success/35 text-dc-success' };
    if (s === 'check_in') return { label: 'Check-In', cls: 'bg-dc-warning/15 border border-dc-warning/35 text-dc-warning' };
    if (s === 'scheduled') return { label: 'Scheduled', cls: 'bg-theme/15 border border-theme/35 text-theme' };
    if (s === 'completed') return { label: 'Completed', cls: 'bg-white/10 border border-white/20 text-dc-textBright' };
    return { label: s ? s.replace(/_/g, ' ') : 'Unknown', cls: 'bg-white/10 border border-white/20 text-dc-textBright' };
  }

  function serverMeta(status) {
    const s = String(status || '').toLowerCase();
    if (s === 'online' || s === 'available' || s === 'ready') {
      return { label: 'Online', cls: 'bg-dc-success/15 border border-dc-success/35 text-dc-success' };
    }
    if (s === 'in_use' || s === 'busy' || s === 'active') {
      return { label: 'In Use', cls: 'bg-dc-warning/15 border border-dc-warning/35 text-dc-warning' };
    }
    if (s === 'idle') {
      return { label: 'Idle', cls: 'bg-theme/15 border border-theme/35 text-theme' };
    }
    return { label: s ? s.replace(/_/g, ' ') : 'Offline', cls: 'bg-dc-danger/15 border border-dc-danger/30 text-dc-danger' };
  }

  function lobbyMeta(match) {
    const info = (match && typeof match.lobby_info === 'object' && match.lobby_info) || {};
    const code = String(info.lobby_code || match?.lobby_code || '').trim();
    const status = String(info.status || match?.lobby_status || '').toLowerCase();
    const open = !!code && !['closed', 'completed', 'cancelled'].includes(status);
    return {
      code,
      status,
      open,
      region: String(info.region || match?.region || '').trim(),
      serverId: String(info.server_id || match?.server_id || '').trim(),
    };
  }

  function setSyncStatus(state, note) {
    const el = $('#lobby-sync-status');
    if (!el) return;

    if (state === 'loading') {
      el.className = 'text-[10px] font-mono text-dc-warning mt-2';
      el.textContent = note || 'Syncing lobby telemetry...';
      return;
    }
    if (state === 'error') {
      el.className = 'text-[10px] font-mono text-dc-danger mt-2';
      el.textContent = note || 'Sync failed';
      return;
    }
    if (lastFetchedAt > 0) {
      el.className = 'text-[10px] font-mono text-dc-text mt-2';
      el.textContent = `Last sync ${formatClock(new Date(lastFetchedAt))}`;
      return;
    }
    el.className = 'text-[10px] font-mono text-dc-text mt-2';
    el.textContent = 'Not synced yet';
  }

  function setErrorBanner(message) {
    const el = $('#lobby-error-banner');
    if (!el) return;

    if (!message) {
      el.classList.add('hidden');
      el.innerHTML = '';
      return;
    }

    el.classList.remove('hidden');
    el.innerHTML = `
      <div class="flex items-start gap-3">
        <i data-lucide="wifi-off" class="w-4 h-4 text-dc-danger shrink-0 mt-0.5"></i>
        <div class="min-w-0 flex-1">
          <p class="text-xs font-bold text-white">Lobby telemetry unavailable</p>
          <p class="text-[11px] text-dc-text mt-1">${esc(message)}</p>
          <button type="button" class="mt-2 px-2.5 py-1 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" onclick="TOC.lobby.refresh({ force: true })">Retry now</button>
        </div>
      </div>`;
    refreshIcons();
  }

  function setLoading(loading) {
    STAT_IDS.forEach((id) => {
      const el = $(`#lobby-stat-${id}`);
      if (!el) return;
      el.classList.toggle('toc-loading-value', loading);
    });

    PANEL_IDS.forEach((id) => {
      const el = $(`#${id}`);
      if (!el) return;
      el.classList.toggle('toc-panel-loading', loading);
      if (loading) el.setAttribute('aria-busy', 'true');
      else el.removeAttribute('aria-busy');
    });
  }

  function computePriority(matches) {
    const rows = (Array.isArray(matches) ? matches : []).map((m) => {
      const lobby = lobbyMeta(m);
      const state = String(m.state || '').toLowerCase();
      const mins = minutesUntil(m.scheduled_time);

      let score = 0;
      if (state === 'live') score += 500;
      if (state === 'ready' || state === 'check_in') score += 300;
      if (!lobby.code) score += 220;
      if (mins != null && mins <= 15) score += 180;
      if (mins != null && mins >= 0 && mins <= 5) score += 120;
      if (mins != null && mins < 0) score += 80;

      return {
        match: m,
        score,
        mins,
        lobby,
      };
    });

    return rows
      .filter((row) => row.score > 0)
      .sort((a, b) => {
        if (b.score !== a.score) return b.score - a.score;
        const at = parseDate(a.match.scheduled_time)?.getTime() || Number.MAX_SAFE_INTEGER;
        const bt = parseDate(b.match.scheduled_time)?.getTime() || Number.MAX_SAFE_INTEGER;
        return at - bt;
      })
      .slice(0, 6);
  }

  function renderStats(data) {
    const summary = data.summary || {};
    const servers = Array.isArray(data.servers) ? data.servers : [];

    const onlineCount = Number(summary.online_servers || 0)
      || servers.filter((s) => ['online', 'available', 'ready'].includes(String(s.status || '').toLowerCase())).length;
    const idleCount = Number(summary.idle_servers || 0)
      || servers.filter((s) => String(s.status || '').toLowerCase() === 'idle').length;
    const totalServers = Number(summary.total_servers || servers.length || 0);
    const activeLobbies = Number(summary.active_lobbies || 0);
    const utilization = totalServers > 0 ? Math.min(Math.round((activeLobbies / totalServers) * 100), 999) : 0;

    const set = (id, value) => {
      const el = $(`#lobby-stat-${id}`);
      if (el) el.textContent = String(value);
    };

    set('servers', totalServers);
    set('active', activeLobbies);
    set('pending', Number(summary.pending || 0));
    set('completed', Number(summary.completed || 0));
    set('online', onlineCount);
    set('idle', idleCount);

    const util = $('#lobby-server-utilization');
    if (util) util.textContent = `${utilization}% utilization`;
  }

  function renderPriorityQueue(matches) {
    const container = $('#lobby-priority-queue');
    if (!container) return;

    const rows = computePriority(matches);
    if (!rows.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-60">No urgent lobby actions right now.</p>';
      return;
    }

    let html = '';
    rows.forEach((row) => {
      const m = row.match;
      const lobby = row.lobby;
      const state = stateMeta(m.state);

      let timing = 'Schedule pending';
      if (row.mins != null) {
        if (row.mins < 0) timing = `${Math.abs(row.mins)} min overdue`;
        else if (row.mins === 0) timing = 'Starting now';
        else timing = `Starts in ${row.mins} min`;
      }

      const createBtn = !lobby.code
        ? `<button onclick="TOC.lobby.createLobby(${m.match_id})" class="px-2.5 py-1.5 rounded-md bg-theme text-black text-[10px] font-black uppercase tracking-wider hover:opacity-90 transition-opacity">Create Lobby</button>`
        : '';
      const closeBtn = lobby.open
        ? `<button onclick="TOC.lobby.closeLobby(${m.match_id})" class="px-2.5 py-1.5 rounded-md bg-dc-danger/15 border border-dc-danger/35 text-dc-danger text-[10px] font-black uppercase tracking-wider hover:bg-dc-danger/25 transition-colors">Close</button>`
        : '';

      html += `
        <div class="rounded-lg border border-dc-borderLight bg-dc-panel/45 px-3 py-3">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${state.cls}">${esc(state.label)}</span>
                <span class="text-[10px] text-dc-text font-mono">#${esc(m.match_id)} • R${esc(m.round || '-')}</span>
              </div>
              <p class="text-sm font-bold text-white mt-1 truncate">${esc(m.participant1_name || 'TBD')} vs ${esc(m.participant2_name || 'TBD')}</p>
              <p class="text-[10px] text-dc-text mt-0.5">${esc(timing)} • ${esc(formatDateTime(m.scheduled_time))}</p>
              <p class="text-[10px] text-dc-text mt-0.5">${lobby.code ? `Lobby ${esc(lobby.code)}` : 'Lobby not created yet'}</p>
            </div>
            <div class="flex items-center gap-1 shrink-0">
              ${createBtn}
              ${closeBtn}
            </div>
          </div>
        </div>`;
    });

    container.innerHTML = html;
  }

  function renderServers(servers) {
    const container = $('#lobby-servers-list');
    if (!container) return;

    if (!servers.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-5 opacity-60">No servers in fleet. Add your first node.</p>';
      return;
    }

    let html = '';
    servers.forEach((server) => {
      const status = serverMeta(server.status);
      const region = server.region ? esc(server.region) : 'Region TBD';
      const addr = server.ip ? esc(server.ip) : 'No endpoint';
      const cap = Number(server.capacity || 0);

      html += `
        <div class="rounded-lg border border-dc-border bg-dc-surface/50 px-3 py-3">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="text-sm font-bold text-white truncate">${esc(server.name || 'Unnamed Server')}</p>
              <p class="text-[10px] text-dc-text mt-0.5 font-mono truncate">${region} • ${addr}</p>
              <div class="mt-1 flex items-center gap-2 flex-wrap">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${status.cls}">${esc(status.label)}</span>
                <span class="text-[10px] text-dc-text">Capacity ${cap || 0}</span>
              </div>
            </div>
            <button onclick="TOC.lobby.deleteServer('${esc(server.id)}')" class="text-[10px] text-dc-danger hover:text-rose-300 font-bold uppercase tracking-wider transition-colors">Remove</button>
          </div>
        </div>`;
    });

    container.innerHTML = html;
    refreshIcons();
  }

  function renderMatches(matches) {
    const container = $('#lobby-matches-list');
    if (!container) return;

    if (!matches.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-6 opacity-60">No active match rooms in this window.</p>';
      return;
    }

    let html = '';
    matches.forEach((m) => {
      const lobby = lobbyMeta(m);
      const state = stateMeta(m.state);
      const mins = minutesUntil(m.scheduled_time);

      let eta = 'TBD';
      if (mins != null) {
        if (mins < 0) eta = `${Math.abs(mins)}m ago`;
        else if (mins === 0) eta = 'Now';
        else eta = `${mins}m`;
      }

      const lobbyPillCls = lobby.code
        ? (lobby.open
          ? 'bg-dc-success/15 border border-dc-success/35 text-dc-success'
          : 'bg-dc-warning/15 border border-dc-warning/35 text-dc-warning')
        : 'bg-white/10 border border-white/15 text-dc-text';
      const lobbyPillText = lobby.code ? (lobby.open ? 'Lobby Open' : 'Lobby Closed') : 'No Lobby';

      const createBtn = !lobby.code
        ? `<button onclick="TOC.lobby.createLobby(${m.match_id})" class="px-3 py-1.5 rounded-md bg-theme text-black text-[10px] font-black uppercase tracking-wider hover:opacity-90 transition-opacity">Create</button>`
        : '';
      const closeBtn = lobby.open
        ? `<button onclick="TOC.lobby.closeLobby(${m.match_id})" class="px-3 py-1.5 rounded-md border border-dc-danger/35 bg-dc-danger/15 text-dc-danger text-[10px] font-black uppercase tracking-wider hover:bg-dc-danger/25 transition-colors">Close</button>`
        : '';
      const copyBtn = lobby.code
        ? `<button onclick="TOC.lobby.copyLobbyCode('${esc(lobby.code)}')" class="px-3 py-1.5 rounded-md border border-dc-borderLight bg-dc-panel/60 text-dc-textBright text-[10px] font-black uppercase tracking-wider hover:border-theme/45 transition-colors">Copy Code</button>`
        : '';

      html += `
        <div class="rounded-lg border border-dc-border bg-dc-surface/45 px-3 py-3">
          <div class="flex flex-col lg:flex-row lg:items-center gap-3">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${state.cls}">${esc(state.label)}</span>
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${lobbyPillCls}">${esc(lobbyPillText)}</span>
                <span class="text-[10px] text-dc-text font-mono">Match #${esc(m.match_id)} • ETA ${esc(eta)}</span>
              </div>
              <p class="text-sm font-bold text-white mt-1 truncate">${esc(m.participant1_name || 'TBD')} vs ${esc(m.participant2_name || 'TBD')}</p>
              <div class="mt-1 text-[10px] text-dc-text font-mono flex items-center gap-2 flex-wrap">
                <span>${esc(formatDateTime(m.scheduled_time))}</span>
                <span class="text-white/25">•</span>
                <span>${lobby.code ? `Code ${esc(lobby.code)}` : 'No code assigned'}</span>
                ${lobby.region ? `<span class="text-white/25">•</span><span>${esc(lobby.region)}</span>` : ''}
                ${lobby.serverId ? `<span class="text-white/25">•</span><span>${esc(lobby.serverId)}</span>` : ''}
              </div>
            </div>
            <div class="flex items-center gap-1.5 shrink-0 flex-wrap">
              <button onclick="TOC.lobby.openMatchOps(${m.match_id})" class="px-3 py-1.5 rounded-md border border-theme/40 bg-theme/12 text-theme text-[10px] font-black uppercase tracking-wider hover:bg-theme/20 transition-colors">Score Ops</button>
              ${createBtn}
              ${copyBtn}
              ${closeBtn}
            </div>
          </div>
        </div>`;
    });

    container.innerHTML = html;
  }

  function renderConfig(config) {
    const setToggle = (id, value) => {
      const el = $(`#${id}`);
      if (el) el.checked = !!value;
    };
    const setValue = (id, value, fallback) => {
      const el = $(`#${id}`);
      if (el) el.value = value != null && value !== '' ? value : fallback;
    };

    setToggle('lobby-auto-create', config.auto_create);
    setToggle('lobby-chat-enabled', config.chat_enabled !== false);
    setToggle('lobby-anticheat-required', !!config.anticheat_required);

    setValue('lobby-auto-close', config.auto_close_minutes, 0);
    setValue('lobby-default-region', config.default_region, '');
    setValue('lobby-spectator-slots', config.spectator_slots_default, 2);
  }

  function renderDashboard(data) {
    const safe = data && typeof data === 'object' ? data : {};
    const matches = Array.isArray(safe.matches) ? safe.matches : [];
    const servers = Array.isArray(safe.servers) ? safe.servers : [];
    const config = safe.config && typeof safe.config === 'object' ? safe.config : {};

    renderStats(safe);
    renderPriorityQueue(matches);
    renderMatches(matches);
    renderServers(servers);
    renderConfig(config);

    setLoading(false);
    setErrorBanner('');
    setSyncStatus('ok');
    refreshIcons();
  }

  function renderEmptyState(message) {
    const text = esc(message || 'No data available');
    const priority = $('#lobby-priority-queue');
    const servers = $('#lobby-servers-list');
    const matches = $('#lobby-matches-list');

    if (priority) priority.innerHTML = `<p class="text-xs text-dc-text text-center py-4 opacity-60">${text}</p>`;
    if (servers) servers.innerHTML = `<p class="text-xs text-dc-text text-center py-4 opacity-60">${text}</p>`;
    if (matches) matches.innerHTML = `<p class="text-xs text-dc-text text-center py-4 opacity-60">${text}</p>`;
    setLoading(false);
  }

  async function refresh(options) {
    const opts = options || {};
    const force = opts.force === true;
    const silent = opts.silent === true;

    if (dashData && !force) {
      renderDashboard(dashData);
      if (hasFreshCache()) return dashData;
    }

    if (inflightPromise && !force) return inflightPromise;

    if (!silent) {
      setLoading(true);
      setSyncStatus('loading', dashData ? 'Refreshing lobby telemetry...' : 'Loading lobby telemetry...');
    }

    const requestId = ++activeRequestId;
    inflightPromise = (async () => {
      try {
        const data = await API.get('lobby/');
        if (requestId !== activeRequestId) return dashData || data;

        dashData = data;
        lastFetchedAt = Date.now();
        renderDashboard(data);
        return data;
      } catch (e) {
        if (requestId !== activeRequestId) return dashData;

        const detail = e && e.message ? String(e.message) : 'Request failed';
        console.error('[lobby] fetch error', e);
        if (dashData) {
          setLoading(false);
          setSyncStatus('error', `Using cached data (${detail})`);
          setErrorBanner(`Live refresh failed, showing cached lobby telemetry. ${detail}`);
        } else {
          setSyncStatus('error', detail);
          setErrorBanner(detail);
          renderEmptyState('Lobby data is unavailable right now.');
        }
        return dashData;
      } finally {
        if (requestId === activeRequestId) inflightPromise = null;
      }
    })();

    return inflightPromise;
  }

  function invalidate() {
    lastFetchedAt = 0;
  }

  function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshTimer = setInterval(() => {
      if (!isLobbyTabActive()) return;
      refresh({ silent: true });
    }, AUTO_REFRESH_MS);
  }

  function stopAutoRefresh() {
    if (autoRefreshTimer) {
      clearInterval(autoRefreshTimer);
      autoRefreshTimer = null;
    }
  }

  function onTabChange(e) {
    if (e.detail?.tab === 'lobby') {
      refresh();
      startAutoRefresh();
      return;
    }
    stopAutoRefresh();
  }

  function onVisibilityChange() {
    if (!document.hidden && isLobbyTabActive() && !hasFreshCache()) {
      refresh({ silent: true });
    }
  }

  const FIELD = 'w-full bg-dc-surface/50 border border-dc-border/50 rounded-lg px-3 py-2 text-sm text-white placeholder-dc-text/40 focus:outline-none focus:border-theme';
  const LABEL = 'block text-[10px] text-dc-text uppercase tracking-widest mb-1';

  function addServer() {
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Server Name *</label>
        <input id="lobby-srv-name" type="text" class="${FIELD}" placeholder="e.g. AP Lobby Node 01"></div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="${LABEL}">Region</label>
          <input id="lobby-srv-region" type="text" class="${FIELD}" placeholder="e.g. AP-SE"></div>
        <div><label class="${LABEL}">IP / Hostname</label>
          <input id="lobby-srv-ip" type="text" class="${FIELD}" placeholder="e.g. 10.2.8.10"></div>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="${LABEL}">Port</label>
          <input id="lobby-srv-port" type="text" class="${FIELD}" placeholder="e.g. 7777"></div>
        <div><label class="${LABEL}">Capacity</label>
          <input id="lobby-srv-capacity" type="number" min="1" value="10" class="${FIELD}"></div>
      </div>
    </div>`;

    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button onclick="TOC.lobby._submitAddServer()" class="flex-1 bg-theme hover:opacity-90 text-black text-sm font-bold py-2 rounded-lg transition">Add Server</button>
      <button onclick="TOC.drawer.close()" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;

    TOC.drawer.open('Add Server Node', body, footer);
    setTimeout(() => document.getElementById('lobby-srv-name')?.focus(), 60);
  }

  function _submitAddServer() {
    const name = document.getElementById('lobby-srv-name')?.value.trim();
    const region = document.getElementById('lobby-srv-region')?.value.trim() || '';
    const ip = document.getElementById('lobby-srv-ip')?.value.trim() || '';
    const port = document.getElementById('lobby-srv-port')?.value.trim() || '';
    const capacity = parseInt(document.getElementById('lobby-srv-capacity')?.value || '10', 10) || 10;

    if (!name) {
      toast('Server name is required', 'error');
      return;
    }

    API.post('lobby/servers/', { name, region, ip, port, capacity })
      .then(() => {
        toast('Server added', 'success');
        TOC.drawer.close();
        invalidate();
        refresh({ force: true });
      })
      .catch((e) => {
        toast(e?.message || 'Failed to add server', 'error');
      });
  }

  function deleteServer(serverId) {
    if (!confirm('Remove this server node from the fleet?')) return;
    API.delete(`lobby/servers/${serverId}/`)
      .then(() => {
        toast('Server removed', 'success');
        invalidate();
        refresh({ force: true });
      })
      .catch((e) => {
        toast(e?.message || 'Failed to remove server', 'error');
      });
  }

  function createLobby(matchId) {
    API.post('lobby/create/', { match_id: matchId })
      .then((res) => {
        const code = String(res?.lobby_code || res?.code || '').trim();
        toast(code ? `Lobby created: ${code}` : 'Lobby created', 'success');
        invalidate();
        refresh({ force: true });
      })
      .catch((e) => {
        toast(e?.message || 'Failed to create lobby', 'error');
      });
  }

  function closeLobby(matchId) {
    API.post('lobby/close/', { match_id: matchId })
      .then(() => {
        toast('Lobby closed', 'success');
        invalidate();
        refresh({ force: true });
      })
      .catch((e) => {
        toast(e?.message || 'Failed to close lobby', 'error');
      });
  }

  function openMatchOps(matchId) {
    if (typeof window.TOC?.navigate === 'function') {
      window.TOC.navigate('matches');
    }

    setTimeout(() => {
      try {
        if (window.TOC?.matches?.openScoreDrawer) {
          window.TOC.matches.openScoreDrawer(matchId);
          return;
        }
        if (window.TOC?.matches?.openDetailDrawer) {
          window.TOC.matches.openDetailDrawer(matchId);
        }
      } catch (err) {
        console.warn('[lobby] failed to open match ops drawer', err);
      }
    }, 140);
  }

  function copyLobbyCode(code) {
    copyText(code).then((ok) => {
      toast(ok ? 'Lobby code copied' : 'Unable to copy code', ok ? 'success' : 'warning');
    });
  }

  async function saveConfig() {
    const data = {
      auto_create: $('#lobby-auto-create')?.checked || false,
      chat_enabled: $('#lobby-chat-enabled')?.checked || false,
      anticheat_required: $('#lobby-anticheat-required')?.checked || false,
      auto_close_minutes: parseInt($('#lobby-auto-close')?.value || '0', 10) || 0,
      default_region: ($('#lobby-default-region')?.value || '').trim(),
      spectator_slots_default: parseInt($('#lobby-spectator-slots')?.value || '2', 10) || 0,
    };

    try {
      await API.post('lobby/config/', data);
      toast('Lobby rules saved', 'success');
      invalidate();
      refresh({ force: true });
    } catch (e) {
      toast(e?.message || 'Save failed', 'error');
    }
  }

  window.TOC = window.TOC || {};
  window.TOC.lobby = {
    refresh,
    invalidate,
    addServer,
    _submitAddServer,
    deleteServer,
    createLobby,
    closeLobby,
    openMatchOps,
    copyLobbyCode,
    saveConfig,
  };

  document.addEventListener('toc:tab-changed', onTabChange);
  document.addEventListener('visibilitychange', onVisibilityChange);

  if (isLobbyTabActive()) {
    refresh();
    startAutoRefresh();
  }
})();