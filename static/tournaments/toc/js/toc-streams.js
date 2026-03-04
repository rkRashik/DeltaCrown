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

  function addStation() {
    const name = prompt('Station name:');
    if (!name) return;
    const platform = prompt('Platform (twitch/youtube/custom):') || 'twitch';
    const url = prompt('Stream URL:') || '';
    API.post('streams/stations/', { name, platform, url })
      .then(() => { toast('Station added', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function editStation(stationId) {
    const name = prompt('New station name:');
    if (!name) return;
    API.put(`streams/stations/${stationId}/`, { name })
      .then(() => { toast('Updated', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteStation(stationId) {
    if (!confirm('Delete this station?')) return;
    API.delete(`streams/stations/${stationId}/`)
      .then(() => { toast('Deleted', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function assignStream(matchId) {
    const url = prompt('Stream URL for this match:');
    if (!url) return;
    API.post('streams/assign/', { match_id: matchId, stream_url: url })
      .then(() => { toast('Stream assigned', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function addVod() {
    const title = prompt('VOD title:');
    if (!title) return;
    const url = prompt('VOD URL:') || '';
    const platform = prompt('Platform (youtube/twitch/other):') || 'youtube';
    API.post('streams/vods/', { title, url, platform })
      .then(() => { toast('VOD added', 'success'); refresh(); })
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
      prompt('Your overlay API key (copy it):', key);
      toast('Overlay key generated', 'success');
    } catch (e) {
      toast('Failed to generate key', 'error');
    }
  }

  window.TOC = window.TOC || {};
  window.TOC.streams = { refresh, addStation, editStation, deleteStation, assignStream, addVod, deleteVod, generateOverlayKey };

  // Auto-load when tab is activated
  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail && e.detail.tab === 'streams') refresh();
  });
})();
