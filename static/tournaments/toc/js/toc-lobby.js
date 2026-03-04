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

  let dashData = null;

  async function refresh() {
    try {
      const data = await API.get('lobby/');
      dashData = data;
      renderStats(data);
      renderServers(data.servers || []);
      renderMatches(data.matches || []);
      renderConfig(data.config || {});
    } catch (e) {
      console.error('[lobby] fetch error', e);
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

  function addServer() {
    const name = prompt('Server name:');
    if (!name) return;
    const region = prompt('Region (e.g. US-East):') || '';
    const ip = prompt('IP / hostname:') || '';
    API.post('lobby/servers/', { name, region, ip })
      .then(() => { toast('Server added', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteServer(serverId) {
    if (!confirm('Remove this server?')) return;
    API.delete(`lobby/servers/${serverId}/`)
      .then(() => { toast('Removed', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function createLobby(matchId) {
    API.post('lobby/create/', { match_id: matchId })
      .then((res) => {
        const code = res.lobby_code || '';
        toast(`Lobby created: ${code}`, 'success');
        refresh();
      })
      .catch(() => toast('Failed', 'error'));
  }

  function closeLobby(matchId) {
    API.post('lobby/close/', { match_id: matchId })
      .then(() => { toast('Lobby closed', 'success'); refresh(); })
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
    } catch (e) {
      toast('Save failed', 'error');
    }
  }

  window.TOC = window.TOC || {};
  window.TOC.lobby = { refresh, addServer, deleteServer, createLobby, closeLobby, saveConfig };

  // Auto-load when tab is activated
  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail && e.detail.tab === 'lobby') refresh();
  });
})();
