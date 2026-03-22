/**
 * TOC Lobby Module — Sprint 28
 * Lobby & server management: server pool, lobby creation, match chat, config.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);
  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }
  function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
  function refreshIcons() { if (typeof lucide !== 'undefined') lucide.createIcons(); }

  const CACHE_TTL_MS = 20000;
  const AUTO_REFRESH_MS = 45000;
  const STAT_IDS = ['servers', 'active', 'pending', 'completed'];
  const PANEL_IDS = ['lobby-servers-list', 'lobby-matches-list', 'lobby-config-section'];

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

  function formatTime(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function setSyncStatus(state, note) {
    const el = $('#lobby-sync-status');
    if (!el) return;
    if (state === 'loading') {
      el.className = 'text-[10px] font-mono text-dc-warning mt-1';
      el.textContent = note || 'Syncing lobby...';
      return;
    }
    if (state === 'error') {
      el.className = 'text-[10px] font-mono text-dc-danger mt-1';
      el.textContent = note || 'Sync failed';
      return;
    }
    if (lastFetchedAt > 0) {
      el.className = 'text-[10px] font-mono text-dc-text mt-1';
      el.textContent = `Last sync ${formatTime(new Date(lastFetchedAt))}`;
      return;
    }
    el.className = 'text-[10px] font-mono text-dc-text mt-1';
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
          <p class="text-xs font-bold text-white">Lobby request failed</p>
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

  function renderDashboard(data) {
    const safe = data && typeof data === 'object' ? data : {};
    renderStats(safe);
    renderServers(Array.isArray(safe.servers) ? safe.servers : []);
    renderMatches(Array.isArray(safe.matches) ? safe.matches : []);
    renderConfig(safe.config && typeof safe.config === 'object' ? safe.config : {});
    setLoading(false);
    setErrorBanner('');
    setSyncStatus('ok');
  }

  function renderEmptyState(message) {
    const text = esc(message || 'No data available');
    const servers = $('#lobby-servers-list');
    const matches = $('#lobby-matches-list');
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
      setSyncStatus('loading', dashData ? 'Refreshing lobby...' : 'Loading lobby...');
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
          setErrorBanner(`Live refresh failed, showing cached lobby data. ${detail}`);
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

  function renderStats(data) {
    const s = data.summary || {};
    const el = (id, v) => { const e = $(`#lobby-stat-${id}`); if (e) e.textContent = v; };
    el('servers', s.total_servers || 0);
    el('active', s.active_lobbies || 0);
    el('pending', s.pending || 0);
    el('completed', s.completed || 0);
  }

  function renderServers(servers) {
    const container = $('#lobby-servers-list');
    if (!container) return;

    if (!servers.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No servers in pool</p>';
      return;
    }

    let html = '';
    servers.forEach(s => {
      const statusCls = s.status === 'available' ? 'text-dc-success' : s.status === 'in_use' ? 'text-dc-warning' : 'text-dc-text';
      html += `
        <div class="flex items-center justify-between p-3 bg-dc-surface/50 rounded-lg border border-dc-border/50">
          <div class="flex items-center gap-3">
            <i data-lucide="server" class="w-4 h-4 text-theme"></i>
            <div>
              <p class="text-sm text-white font-medium">${esc(s.name)}</p>
              <p class="text-[10px] text-dc-text">${esc(s.region || '')} — ${esc(s.ip || '')}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] ${statusCls}">${s.status || 'unknown'}</span>
            <button onclick="TOC.lobby.deleteServer('${s.id}')" class="text-[10px] text-dc-danger hover:underline">Remove</button>
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
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No match lobbies</p>';
      return;
    }

    let html = '';
    matches.forEach(m => {
      const lobby = m.lobby_info || {};
      const hasLobby = !!lobby.lobby_code;
      const statusCls = hasLobby ? 'bg-dc-success/20 text-dc-success' : 'bg-dc-text/10 text-dc-text';
      const statusText = hasLobby ? 'Active' : 'No Lobby';
      html += `
        <div class="flex items-center justify-between p-3 bg-dc-surface/50 rounded-lg border border-dc-border/50">
          <div>
            <p class="text-sm text-white">${esc(m.participant1_name || 'TBD')} vs ${esc(m.participant2_name || 'TBD')}</p>
            <p class="text-[10px] text-dc-text">Match #${m.match_id} — ${lobby.lobby_code ? 'Code: ' + lobby.lobby_code : 'No code'}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] px-2 py-0.5 rounded-full ${statusCls}">${statusText}</span>
            ${!hasLobby ? `<button onclick="TOC.lobby.createLobby(${m.match_id})" class="text-[10px] text-theme hover:underline">Create</button>` : ''}
            ${hasLobby ? `<button onclick="TOC.lobby.closeLobby(${m.match_id})" class="text-[10px] text-dc-danger hover:underline">Close</button>` : ''}
          </div>
        </div>`;
    });
    container.innerHTML = html;
  }

  function renderConfig(config) {
    const auto = $('#lobby-auto-create');
    const chat = $('#lobby-chat-enabled');
    const close = $('#lobby-auto-close');
    if (auto) auto.checked = !!config.auto_create;
    if (chat) chat.checked = config.chat_enabled !== false;
    if (close) close.value = config.auto_close_minutes || 0;
  }

  /* ─── Drawer helpers ─────────────────────── */
  const FIELD = 'w-full bg-dc-surface/50 border border-dc-border/50 rounded-lg px-3 py-2 text-sm text-white placeholder-dc-text/40 focus:outline-none focus:border-theme';
  const LABEL = 'block text-[10px] text-dc-text uppercase tracking-widest mb-1';

  function addServer() {
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Server Name *</label>
        <input id="lobby-srv-name" type="text" class="${FIELD}" placeholder="e.g. EU Match Server 1"></div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="${LABEL}">Region</label>
          <input id="lobby-srv-region" type="text" class="${FIELD}" placeholder="e.g. US-East"></div>
        <div><label class="${LABEL}">IP / Hostname</label>
          <input id="lobby-srv-ip" type="text" class="${FIELD}" placeholder="e.g. 192.168.1.1"></div>
      </div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button onclick="TOC.lobby._submitAddServer()" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Add Server</button>
      <button onclick="TOC.drawer.close()" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Add Server to Pool', body, footer);
    setTimeout(() => document.getElementById('lobby-srv-name')?.focus(), 50);
  }

  function _submitAddServer() {
    const name   = document.getElementById('lobby-srv-name')?.value.trim();
    const region = document.getElementById('lobby-srv-region')?.value.trim() || '';
    const ip     = document.getElementById('lobby-srv-ip')?.value.trim() || '';
    if (!name) { toast('Server name is required', 'error'); return; }
    API.post('lobby/servers/', { name, region, ip })
      .then(() => { toast('Server added', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteServer(serverId) {
    if (!confirm('Remove this server?')) return;
    API.delete(`lobby/servers/${serverId}/`)
      .then(() => { toast('Removed', 'success'); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function createLobby(matchId) {
    API.post('lobby/create/', { match_id: matchId })
      .then((res) => {
        const code = res.lobby_code || '';
        toast(`Lobby created: ${code}`, 'success');
        invalidate();
        refresh({ force: true });
      })
      .catch(() => toast('Failed', 'error'));
  }

  function closeLobby(matchId) {
    API.post('lobby/close/', { match_id: matchId })
      .then(() => { toast('Lobby closed', 'success'); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  async function saveConfig() {
    const data = {
      auto_create: $('#lobby-auto-create')?.checked || false,
      chat_enabled: $('#lobby-chat-enabled')?.checked || false,
      auto_close_minutes: parseInt($('#lobby-auto-close')?.value || '0'),
    };
    try {
      await API.post('lobby/config/', data);
      toast('Config saved', 'success');
      invalidate();
      refresh({ force: true });
    } catch (e) {
      toast('Save failed', 'error');
    }
  }

  window.TOC = window.TOC || {};
  window.TOC.lobby = { refresh, invalidate, addServer, _submitAddServer, deleteServer, createLobby, closeLobby, saveConfig };

  document.addEventListener('toc:tab-changed', onTabChange);
  document.addEventListener('visibilitychange', onVisibilityChange);

  if (isLobbyTabActive()) {
    refresh();
    startAutoRefresh();
  }
})();
