/**
 * TOC Check-in Module — Sprint 28
 * Check-in hub: open/close, force check-in, auto-DQ, config, participant list.
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
  let allParticipants = [];

  async function refresh() {
    try {
      const data = await API.get('checkin/');
      dashData = data;
      renderStats(data);
      renderConfig(data.config || {});
      renderParticipants(data.participants || []);
      allParticipants = data.participants || [];
    } catch (e) {
      console.error('[checkin] fetch error', e);
    }
  }

  function renderStats(data) {
    const s = data.summary || {};
    const el = (id, v) => { const e = $(`#checkin-stat-${id}`); if (e) e.textContent = v; };
    el('checked', s.checked_in || 0);
    el('pending', s.pending || 0);
    el('missing', s.not_checked_in || 0);
    el('total', s.total || 0);
    el('status', data.config?.open ? 'Open' : 'Closed');
  }

  function renderConfig(config) {
    const wm = $('#checkin-window-minutes');
    const adq = $('#checkin-auto-dq');
    const pr = $('#checkin-per-round');
    if (wm) wm.value = config.window_minutes || 15;
    if (adq) adq.checked = !!config.auto_dq;
    if (pr) pr.checked = !!config.per_round;
  }

  function renderParticipants(participants) {
    const container = $('#checkin-participants-list');
    if (!container) return;

    if (!participants.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No participants</p>';
      return;
    }

    let html = '';
    participants.forEach(p => {
      const checked = p.checked_in;
      const statusCls = checked ? 'bg-dc-success/20 text-dc-success border-dc-success/30' : 'bg-dc-warning/20 text-dc-warning border-dc-warning/30';
      const statusText = checked ? 'Checked In' : 'Pending';
      html += `
        <div class="flex items-center justify-between p-3 bg-dc-surface/50 rounded-lg border border-dc-border/50 hover:border-dc-border transition-colors" data-participant="${p.user_id}">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-theme/10 flex items-center justify-center text-xs font-bold text-theme">${esc((p.username || '?')[0].toUpperCase())}</div>
            <div>
              <p class="text-sm text-white font-medium">${esc(p.display_name || p.username)}</p>
              <p class="text-[10px] text-dc-text">${p.team_name ? esc(p.team_name) : 'Solo'}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] px-2 py-0.5 rounded-full border ${statusCls}">${statusText}</span>
            ${!checked ? `<button onclick="TOC.checkin.forceCheckin(${p.user_id})" class="text-[10px] text-theme hover:underline">Force</button>` : ''}
          </div>
        </div>`;
    });

    container.innerHTML = html;
  }

  function filterParticipants(query) {
    const q = (query || '').toLowerCase();
    const filtered = allParticipants.filter(p =>
      (p.username || '').toLowerCase().includes(q) ||
      (p.display_name || '').toLowerCase().includes(q) ||
      (p.team_name || '').toLowerCase().includes(q)
    );
    renderParticipants(filtered);
  }

  async function openCheckin() {
    const mins = parseInt($('#checkin-window-minutes')?.value || '15');
    try {
      await API.post('checkin/open/', { window_minutes: mins });
      toast('Check-in opened', 'success');
      refresh();
    } catch (e) {
      toast('Failed to open check-in', 'error');
    }
  }

  async function closeCheckin() {
    try {
      await API.post('checkin/close/', {});
      toast('Check-in closed', 'success');
      refresh();
    } catch (e) {
      toast('Failed to close check-in', 'error');
    }
  }

  async function forceCheckin(participantId) {
    try {
      await API.post('checkin/force/', { participant_id: participantId });
      toast('Participant checked in', 'success');
      refresh();
    } catch (e) {
      toast('Force check-in failed', 'error');
    }
  }

  async function autoDQ() {
    if (!confirm('Auto-DQ all participants who have not checked in?')) return;
    try {
      const res = await API.post('checkin/auto-dq/', {});
      toast(`${res.dq_count || 0} participants disqualified`, 'warning');
      refresh();
    } catch (e) {
      toast('Auto-DQ failed', 'error');
    }
  }

  async function saveConfig() {
    const data = {
      window_minutes: parseInt($('#checkin-window-minutes')?.value || '15'),
      auto_dq: $('#checkin-auto-dq')?.checked || false,
      per_round: $('#checkin-per-round')?.checked || false,
    };
    try {
      await API.post('checkin/config/', data);
      toast('Config saved', 'success');
    } catch (e) {
      toast('Save failed', 'error');
    }
  }

  window.TOC = window.TOC || {};
  window.TOC.checkin = { refresh, openCheckin, closeCheckin, forceCheckin, autoDQ, saveConfig, filterParticipants };

  // Auto-load when tab is activated
  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail && e.detail.tab === 'checkin') refresh();
  });
})();
