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

  let dashData = null;

  async function refresh() {
    try {
      const data = await API.get('streams/');
      dashData = data;
      renderStats(data);
      renderStations(data.stations || []);
      renderSchedule(data.live || [], data.upcoming || []);
      renderVods(data.vods || []);
    } catch (e) {
      console.error('[streams] fetch error', e);
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
            <button onclick="TOC.streams.editStation('${s.id}')" class="text-[10px] text-theme hover:underline">Edit</button>
            <button onclick="TOC.streams.deleteStation('${s.id}')" class="text-[10px] text-dc-danger hover:underline">Delete</button>
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
            <button onclick="TOC.streams.assignStream(${m.match_id})" class="text-[10px] text-theme hover:underline">Assign</button>
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
            <button onclick="TOC.streams.deleteVod('${v.id}')" class="text-[10px] text-dc-danger hover:underline">Delete</button>
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
      <button onclick="TOC.streams._submitAddStation()" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Add Station</button>
      <button onclick="TOC.drawer.close()" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
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
      .then(() => { toast('Station added', 'success'); TOC.drawer.close(); refresh(); })
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
      <button onclick="TOC.streams._submitEditStation('${stationId}')" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Save Changes</button>
      <button onclick="TOC.drawer.close()" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Edit Station', body, footer);
  }

  function _submitEditStation(stationId) {
    const name     = document.getElementById('streams-est-name')?.value.trim();
    const platform = document.getElementById('streams-est-platform')?.value || 'twitch';
    const url      = document.getElementById('streams-est-url')?.value.trim() || '';
    if (!name) { toast('Station name is required', 'error'); return; }
    API.put(`streams/stations/${stationId}/`, { name, platform, url })
      .then(() => { toast('Updated', 'success'); TOC.drawer.close(); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteStation(stationId) {
    if (!confirm('Delete this station?')) return;
    API.delete(`streams/stations/${stationId}/`)
      .then(() => { toast('Deleted', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function assignStream(matchId) {
    const body = `<div class="space-y-4 p-5">
      <p class="text-xs text-dc-text">Enter the stream URL to assign to Match #${matchId}.</p>
      <div><label class="${LABEL}">Stream URL *</label>
        <input id="streams-assign-url" type="url" class="${FIELD}" placeholder="https://twitch.tv/..."></div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button onclick="TOC.streams._submitAssign(${matchId})" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Assign Stream</button>
      <button onclick="TOC.drawer.close()" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Assign Stream', body, footer);
    setTimeout(() => document.getElementById('streams-assign-url')?.focus(), 50);
  }

  function _submitAssign(matchId) {
    const url = document.getElementById('streams-assign-url')?.value.trim();
    if (!url) { toast('Stream URL is required', 'error'); return; }
    API.post('streams/assign/', { match_id: matchId, stream_url: url })
      .then(() => { toast('Stream assigned', 'success'); TOC.drawer.close(); refresh(); })
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
      <button onclick="TOC.streams._submitAddVod()" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Add VOD</button>
      <button onclick="TOC.drawer.close()" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
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
      .then(() => { toast('VOD added', 'success'); TOC.drawer.close(); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteVod(vodId) {
    if (!confirm('Delete this VOD?')) return;
    API.delete(`streams/vods/${vodId}/`)
      .then(() => { toast('Deleted', 'success'); refresh(); })
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
            <button onclick="navigator.clipboard.writeText('${esc(key)}').then(()=>TOC.toast('Copied!','success'))" class="shrink-0 px-3 bg-theme/20 hover:bg-theme/40 text-theme text-xs rounded-lg transition">Copy</button>
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
    refresh,
    addStation, _submitAddStation,
    editStation, _submitEditStation, deleteStation,
    assignStream, _submitAssign,
    addVod, _submitAddVod, deleteVod,
    generateOverlayKey,
  };

  // Auto-load when tab is activated
  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail && e.detail.tab === 'streams') refresh();
  });
})();
