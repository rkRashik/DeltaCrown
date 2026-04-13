/**
 * TOC Streams & Media Module — Sprint 28
 * Broadcast stations, stream assignment, VOD library, OBS overlay keys.
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
  const STAT_IDS = ['live', 'stations', 'upcoming', 'vods'];
  const PANEL_IDS = ['streams-stations-list', 'streams-schedule-list', 'streams-vods-list'];

  let dashData = null;
  let inflightPromise = null;
  let activeRequestId = 0;
  let lastFetchedAt = 0;
  let autoRefreshTimer = null;

  function isStreamsTabActive() {
    return (window.location.hash || '').replace('#', '') === 'streams';
  }

  function hasFreshCache() {
    return !!dashData && (Date.now() - lastFetchedAt) < CACHE_TTL_MS;
  }

  function formatTime(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function setSyncStatus(state, note) {
    const el = $('#streams-sync-status');
    if (!el) return;
    if (state === 'loading') {
      el.className = 'text-[10px] font-mono text-dc-warning mt-1';
      el.textContent = note || 'Syncing streams...';
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
    const el = $('#streams-error-banner');
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
          <p class="text-xs font-bold text-white">Streams request failed</p>
          <p class="text-[11px] text-dc-text mt-1">${esc(message)}</p>
          <button type="button" class="mt-2 px-2.5 py-1 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" data-click="TOC.streams.refresh" data-click-args="[{&quot;force&quot;:true}]">Retry now</button>
        </div>
      </div>`;
    refreshIcons();
  }

  function setLoading(loading) {
    STAT_IDS.forEach((id) => {
      const el = $(`#streams-stat-${id}`);
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
    renderStations(Array.isArray(safe.stations) ? safe.stations : []);
    renderSchedule(Array.isArray(safe.live) ? safe.live : [], Array.isArray(safe.upcoming) ? safe.upcoming : []);
    renderVods(Array.isArray(safe.vods) ? safe.vods : []);
    setLoading(false);
    setErrorBanner('');
    setSyncStatus('ok');
  }

  function renderEmptyState(message) {
    const text = esc(message || 'No data available');
    const stations = $('#streams-stations-list');
    const schedule = $('#streams-schedule-list');
    const vods = $('#streams-vods-list');
    if (stations) stations.innerHTML = `<p class="text-xs text-dc-text text-center py-4 opacity-60">${text}</p>`;
    if (schedule) schedule.innerHTML = `<p class="text-xs text-dc-text text-center py-4 opacity-60">${text}</p>`;
    if (vods) vods.innerHTML = `<p class="text-xs text-dc-text text-center py-4 opacity-60">${text}</p>`;
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
      setSyncStatus('loading', dashData ? 'Refreshing streams...' : 'Loading streams...');
    }

    const requestId = ++activeRequestId;
    inflightPromise = (async () => {
      try {
        const data = await API.get('streams/');
        if (requestId !== activeRequestId) return dashData || data;
        dashData = data;
        lastFetchedAt = Date.now();
        renderDashboard(data);
        return data;
      } catch (e) {
        if (requestId !== activeRequestId) return dashData;
        const detail = e && e.message ? String(e.message) : 'Request failed';
        console.error('[streams] fetch error', e);
        if (dashData) {
          setLoading(false);
          setSyncStatus('error', `Using cached data (${detail})`);
          setErrorBanner(`Live refresh failed, showing cached streams data. ${detail}`);
        } else {
          setSyncStatus('error', detail);
          setErrorBanner(detail);
          renderEmptyState('Streams data is unavailable right now.');
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
    if (window.TOC && TOC.isTerminalStatus && TOC.isTerminalStatus()) return;
    autoRefreshTimer = setInterval(() => {
      if (!isStreamsTabActive()) return;
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
    if (e.detail?.tab === 'streams') {
      refresh();
      startAutoRefresh();
      return;
    }
    stopAutoRefresh();
  }

  function onVisibilityChange() {
    if (!document.hidden && isStreamsTabActive() && !hasFreshCache()) {
      refresh({ silent: true });
    }
  }

  function renderStats(data) {
    const s = data.summary || {};
    const el = (id, v) => { const e = $(`#streams-stat-${id}`); if (e) e.textContent = v; };
    el('live', s.live || 0);
    el('stations', s.total_stations || 0);
    el('upcoming', s.upcoming || 0);
    el('vods', s.total_vods || 0);
  }

  function renderStations(stations) {
    const container = $('#streams-stations-list');
    if (!container) return;

    if (!stations.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No broadcast stations configured</p>';
      return;
    }

    let html = '';
    stations.forEach(s => {
      const statusCls = s.status === 'live' ? 'bg-dc-success/20 text-dc-success' : 'bg-dc-text/10 text-dc-text';
      html += `
        <div class="flex items-center justify-between p-3 bg-dc-surface/50 rounded-lg border border-dc-border/50">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-theme/10 flex items-center justify-center">
              <i data-lucide="radio" class="w-4 h-4 text-theme"></i>
            </div>
            <div>
              <p class="text-sm text-white font-medium">${esc(s.name)}</p>
              <p class="text-[10px] text-dc-text">${esc(s.platform || '')} — ${esc(s.url || '')}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] px-2 py-0.5 rounded-full ${statusCls}">${s.status || 'offline'}</span>
            <button data-click="TOC.streams.editStation" data-click-args="['${s.id}']" class="text-[10px] text-theme hover:underline">Edit</button>
            <button data-click="TOC.streams.deleteStation" data-click-args="['${s.id}']" class="text-[10px] text-dc-danger hover:underline">Delete</button>
          </div>
        </div>`;
    });
    container.innerHTML = html;
    refreshIcons();
  }

  function renderSchedule(live, upcoming) {
    const container = $('#streams-schedule-list');
    if (!container) return;

    const all = [...live, ...upcoming];
    if (!all.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No scheduled streams</p>';
      return;
    }

    let html = '';
    all.forEach(m => {
      const isLive = m.state === 'in_progress';
      const badge = isLive
        ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-dc-danger text-white animate-pulse">LIVE</span>'
        : '<span class="text-[10px] px-2 py-0.5 rounded-full bg-dc-text/10 text-dc-text">Upcoming</span>';
      html += `
        <div class="flex items-center justify-between p-3 bg-dc-surface/50 rounded-lg border border-dc-border/50">
          <div>
            <p class="text-sm text-white">${esc(m.participant1_name || 'TBD')} vs ${esc(m.participant2_name || 'TBD')}</p>
            <p class="text-[10px] text-dc-text">Round ${m.round_number || '?'} — Match #${m.match_id || '?'}</p>
          </div>
          <div class="flex items-center gap-2">
            ${badge}
            <button data-click="TOC.streams.assignStream" data-click-args="[${m.match_id}]" class="text-[10px] text-theme hover:underline">Assign</button>
          </div>
        </div>`;
    });
    container.innerHTML = html;
    refreshIcons();
  }

  function renderVods(vods) {
    const container = $('#streams-vods-list');
    if (!container) return;

    if (!vods.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No VODs yet</p>';
      return;
    }

    let html = '';
    vods.forEach(v => {
      html += `
        <div class="flex items-center justify-between p-2 bg-dc-surface/30 rounded-lg">
          <div>
            <p class="text-xs text-white">${esc(v.title)}</p>
            <p class="text-[10px] text-dc-text">${esc(v.platform || '')} — ${v.duration || ''}</p>
          </div>
          <div class="flex items-center gap-2">
            <a href="${esc(v.url)}" target="_blank" class="text-[10px] text-theme hover:underline">Watch</a>
            <button data-click="TOC.streams.deleteVod" data-click-args="['${v.id}']" class="text-[10px] text-dc-danger hover:underline">Delete</button>
          </div>
        </div>`;
    });
    container.innerHTML = html;
  }

  /* ─── Drawer helpers ─────────────────────── */
  const FIELD = 'w-full bg-dc-surface/50 border border-dc-border/50 rounded-lg px-3 py-2 text-sm text-white placeholder-dc-text/40 focus:outline-none focus:border-theme';
  const LABEL = 'block text-[10px] text-dc-text uppercase tracking-widest mb-1';
  const PLATFORMS = ['twitch', 'youtube', 'custom'];

  function addStation() {
    const platOpts = PLATFORMS.map(p => `<option value="${p}">${p}</option>`).join('');
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Station Name *</label>
        <input id="streams-st-name" type="text" class="${FIELD}" placeholder="e.g. Main Stream"></div>
      <div><label class="${LABEL}">Platform</label>
        <select id="streams-st-platform" class="${FIELD}">${platOpts}</select></div>
      <div><label class="${LABEL}">Stream URL</label>
        <input id="streams-st-url" type="url" class="${FIELD}" placeholder="https://twitch.tv/..."></div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button data-click="TOC.streams._submitAddStation" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Add Station</button>
      <button data-click="TOC.drawer.close" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Add Broadcast Station', body, footer);
    setTimeout(() => document.getElementById('streams-st-name')?.focus(), 50);
  }

  function _submitAddStation() {
    const name     = document.getElementById('streams-st-name')?.value.trim();
    const platform = document.getElementById('streams-st-platform')?.value || 'twitch';
    const url      = document.getElementById('streams-st-url')?.value.trim() || '';
    if (!name) { toast('Station name is required', 'error'); return; }
    API.post('streams/stations/', { name, platform, url })
      .then(() => { toast('Station added', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function editStation(stationId) {
    const s = (dashData?.stations || []).find(x => x.id == stationId);
    const platOpts = PLATFORMS.map(p =>
      `<option value="${p}" ${p === s?.platform ? 'selected' : ''}>${p}</option>`
    ).join('');
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Station Name *</label>
        <input id="streams-est-name" type="text" value="${esc(s?.name || '')}" class="${FIELD}"></div>
      <div><label class="${LABEL}">Platform</label>
        <select id="streams-est-platform" class="${FIELD}">${platOpts}</select></div>
      <div><label class="${LABEL}">Stream URL</label>
        <input id="streams-est-url" type="url" value="${esc(s?.url || '')}" class="${FIELD}"></div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button data-click="TOC.streams._submitEditStation" data-click-args="['${stationId}']" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Save Changes</button>
      <button data-click="TOC.drawer.close" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Edit Station', body, footer);
  }

  function _submitEditStation(stationId) {
    const name     = document.getElementById('streams-est-name')?.value.trim();
    const platform = document.getElementById('streams-est-platform')?.value || 'twitch';
    const url      = document.getElementById('streams-est-url')?.value.trim() || '';
    if (!name) { toast('Station name is required', 'error'); return; }
    API.put(`streams/stations/${stationId}/`, { name, platform, url })
      .then(() => { toast('Updated', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteStation(stationId) {
    if (!confirm('Delete this station?')) return;
    API.delete(`streams/stations/${stationId}/`)
      .then(() => { toast('Deleted', 'success'); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function assignStream(matchId) {
    const body = `<div class="space-y-4 p-5">
      <p class="text-xs text-dc-text">Enter the stream URL to assign to Match #${matchId}.</p>
      <div><label class="${LABEL}">Stream URL *</label>
        <input id="streams-assign-url" type="url" class="${FIELD}" placeholder="https://twitch.tv/..."></div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button data-click="TOC.streams._submitAssign" data-click-args="[${matchId}]" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Assign Stream</button>
      <button data-click="TOC.drawer.close" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Assign Stream', body, footer);
    setTimeout(() => document.getElementById('streams-assign-url')?.focus(), 50);
  }

  function _submitAssign(matchId) {
    const url = document.getElementById('streams-assign-url')?.value.trim();
    if (!url) { toast('Stream URL is required', 'error'); return; }
    API.post('streams/assign/', { match_id: matchId, stream_url: url })
      .then(() => { toast('Stream assigned', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function addVod() {
    const platOpts = ['youtube', 'twitch', 'other'].map(p => `<option value="${p}">${p}</option>`).join('');
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">VOD Title *</label>
        <input id="streams-vod-title" type="text" class="${FIELD}" placeholder="e.g. Grand Finals Game 1"></div>
      <div><label class="${LABEL}">URL</label>
        <input id="streams-vod-url" type="url" class="${FIELD}" placeholder="https://youtube.com/..."></div>
      <div><label class="${LABEL}">Platform</label>
        <select id="streams-vod-platform" class="${FIELD}">${platOpts}</select></div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button data-click="TOC.streams._submitAddVod" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Add VOD</button>
      <button data-click="TOC.drawer.close" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Add VOD', body, footer);
    setTimeout(() => document.getElementById('streams-vod-title')?.focus(), 50);
  }

  function _submitAddVod() {
    const title    = document.getElementById('streams-vod-title')?.value.trim();
    const url      = document.getElementById('streams-vod-url')?.value.trim() || '';
    const platform = document.getElementById('streams-vod-platform')?.value || 'youtube';
    if (!title) { toast('VOD title is required', 'error'); return; }
    API.post('streams/vods/', { title, url, platform })
      .then(() => { toast('VOD added', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteVod(vodId) {
    if (!confirm('Delete this VOD?')) return;
    API.delete(`streams/vods/${vodId}/`)
      .then(() => { toast('Deleted', 'success'); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  async function generateOverlayKey() {
    try {
      const data = await API.post('streams/overlay-key/', {});
      const key = data.overlay_key || '';
      const body = `<div class="space-y-4 p-5">
        <p class="text-xs text-dc-text">Your OBS overlay API key has been generated. Copy it now — it will not be shown again.</p>
        <div>
          <label class="${LABEL}">Overlay API Key</label>
          <div class="flex gap-2">
            <input id="streams-overlay-key" type="text" readonly value="${esc(key)}" class="${FIELD} font-mono text-xs text-theme cursor-text select-all">
            <button data-click-copy="${esc(key)}" class="shrink-0 px-3 bg-theme/20 hover:bg-theme/40 text-theme text-xs rounded-lg transition">Copy</button>
          </div>
        </div>
      </div>`;
      TOC.drawer.open('Overlay API Key', body);
      toast('Overlay key generated', 'success');
      setTimeout(() => document.getElementById('streams-overlay-key')?.select(), 100);
    } catch (e) {
      toast('Failed to generate key', 'error');
    }
  }

  window.TOC = window.TOC || {};
  window.TOC.streams = {
    refresh, invalidate,
    addStation, _submitAddStation,
    editStation, _submitEditStation, deleteStation,
    assignStream, _submitAssign,
    addVod, _submitAddVod, deleteVod,
    generateOverlayKey,
  };

  document.addEventListener('toc:tab-changed', onTabChange);
  document.addEventListener('visibilitychange', onVisibilityChange);

  if (isStreamsTabActive()) {
    refresh();
    startAutoRefresh();
  }
})();
