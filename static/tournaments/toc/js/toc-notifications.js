/**
 * TOC Notifications Module — Sprint 28
 * Notification management: templates, send/schedule, auto-rules,
 * delivery channels, team messaging, notification log.
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
      const data = await API.get('notifications/');
      dashData = data;
      renderStats(data.summary || {});
      renderTemplates(data.templates || []);
      renderAutoRules(data.auto_rules || []);
      renderChannels(data.channels || {});
      renderLog(data.log || []);
    } catch (e) {
      console.error('[notifications] fetch error', e);
    }
  }

  function renderStats(s) {
    const el = (id, v) => { const e = $(`#notif-stat-${id}`); if (e) e.textContent = v; };
    el('total', s.total_sent || 0);
    el('pending', s.scheduled_pending || 0);
    el('templates', s.template_count || 0);
    el('auto', s.auto_rules_active || 0);
  }

  function renderTemplates(templates) {
    const container = $('#notif-templates-list');
    if (!container) return;

    if (!templates.length) {
      container.innerHTML = `
        <div class="glass-box rounded-xl p-8 text-center">
          <i data-lucide="mail" class="w-10 h-10 mx-auto mb-3 text-dc-text opacity-20"></i>
          <p class="text-sm text-dc-text">No templates. Click "New Template" to create one.</p>
        </div>`;
      refreshIcons();
      return;
    }

    let html = '';
    templates.forEach((t, i) => {
      const enabledBadge = t.enabled
        ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-dc-success/20 text-dc-success">On</span>'
        : '<span class="text-[10px] px-2 py-0.5 rounded-full bg-dc-text/20 text-dc-text">Off</span>';

      html += `
        <div class="glass-box rounded-xl p-4 space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-theme/10 flex items-center justify-center">
                <i data-lucide="file-text" class="w-4 h-4 text-theme"></i>
              </div>
              <div>
                <p class="text-sm text-white font-bold">${esc(t.name)}</p>
                <p class="text-[10px] text-dc-text">${esc(t.trigger)} • ${esc(t.channel || 'platform')}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              ${enabledBadge}
              <button onclick="TOC.notifications.editTemplate('${esc(t.id || i)}')" class="text-[10px] text-theme hover:underline">Edit</button>
              <button onclick="TOC.notifications.deleteTemplate('${esc(t.id || i)}')" class="text-[10px] text-dc-danger hover:underline">Delete</button>
            </div>
          </div>
          <div class="text-[11px] text-dc-text bg-dc-surface/20 rounded-lg p-2">
            <p><span class="text-dc-text/70">Subject:</span> ${esc(t.subject)}</p>
            <p class="mt-1 line-clamp-2"><span class="text-dc-text/70">Body:</span> ${esc(t.body)}</p>
          </div>
        </div>`;
    });

    container.innerHTML = html;
    refreshIcons();
  }

  function renderAutoRules(rules) {
    const container = $('#notif-auto-rules');
    if (!container) return;

    if (!rules.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No auto-notification rules configured</p>';
      return;
    }

    let html = '';
    rules.forEach(r => {
      const status = r.enabled
        ? '<span class="w-2 h-2 rounded-full bg-dc-success inline-block"></span>'
        : '<span class="w-2 h-2 rounded-full bg-dc-text/30 inline-block"></span>';

      html += `
        <div class="flex items-center justify-between p-3 bg-dc-surface/20 rounded-lg">
          <div class="flex items-center gap-2">
            ${status}
            <span class="text-xs text-white">${esc(r.name || r.event)}</span>
            <span class="text-[10px] text-dc-text">→ ${esc(r.event)}</span>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" ${r.enabled ? 'checked' : ''} onchange="TOC.notifications.toggleAutoRule('${esc(r.id || r.event)}', this.checked)" class="sr-only peer">
            <div class="w-7 h-4 bg-dc-surface rounded-full peer peer-checked:bg-theme transition"></div>
          </label>
        </div>`;
    });

    container.innerHTML = html;
  }

  function renderChannels(channels) {
    const container = $('#notif-channels');
    if (!container) return;

    const ch = {
      platform: channels.platform !== false,
      email: channels.email === true,
      discord: channels.discord === true,
      webhook: channels.webhook === true,
    };

    let html = '';
    Object.entries(ch).forEach(([name, enabled]) => {
      html += `
        <div class="flex items-center justify-between p-3 bg-dc-surface/20 rounded-lg">
          <div class="flex items-center gap-2">
            <i data-lucide="${name === 'platform' ? 'bell' : name === 'email' ? 'mail' : name === 'discord' ? 'hash' : 'webhook'}" class="w-4 h-4 text-theme"></i>
            <span class="text-xs text-white capitalize">${name}</span>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" ${enabled ? 'checked' : ''} data-channel="${name}" class="sr-only peer notif-channel-toggle">
            <div class="w-7 h-4 bg-dc-surface rounded-full peer peer-checked:bg-theme transition"></div>
          </label>
        </div>`;
    });

    container.innerHTML = html;
    refreshIcons();
  }

  function renderLog(log) {
    const container = $('#notif-log');
    if (!container) return;

    if (!log.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No notifications sent yet</p>';
      return;
    }

    let html = '';
    log.slice(0, 50).forEach(entry => {
      const time = entry.sent_at ? new Date(entry.sent_at).toLocaleString() : '';
      const typeCls = entry.type === 'auto' ? 'bg-blue-500/20 text-blue-400' : 'bg-theme/20 text-theme';

      html += `
        <div class="flex items-center justify-between p-2 hover:bg-white/[.02] rounded">
          <div class="flex items-center gap-2">
            <span class="text-[10px] px-1.5 py-0.5 rounded ${typeCls}">${esc(entry.type || 'manual')}</span>
            <span class="text-xs text-white">${esc(entry.subject || entry.message || 'Notification')}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] text-dc-text">${esc(entry.target || 'all')}</span>
            <span class="text-[10px] text-dc-text/50">${time}</span>
          </div>
        </div>`;
    });

    container.innerHTML = html;
  }

  /* ─── Actions ─────────────────────────────── */
  function createTemplate() {
    const name = prompt('Template name:');
    if (!name) return;
    const subject = prompt('Subject line:');
    if (!subject) return;
    const body = prompt('Message body (use {player}, {team}, {tournament} as variables):');
    if (!body) return;
    const trigger = prompt('Trigger event (manual, match_ready, checkin_open, round_start, tournament_end):') || 'manual';

    API.post('notifications/templates/', { name, subject, body, trigger, enabled: true })
      .then(() => { toast('Template created', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function editTemplate(id) {
    if (!dashData?.templates) return;
    const t = dashData.templates.find((t, i) => (t.id || i) == id);
    if (!t) return;

    const name = prompt('Template name:', t.name);
    if (name === null) return;
    const subject = prompt('Subject:', t.subject);
    if (subject === null) return;
    const body = prompt('Body:', t.body);
    if (body === null) return;

    API.put(`notifications/templates/${id}/`, { name, subject, body, trigger: t.trigger, enabled: t.enabled })
      .then(() => { toast('Template updated', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  async function deleteTemplate(id) {
    if (!confirm('Delete this template?')) return;
    try {
      await API.delete(`notifications/templates/${id}/`);
      toast('Template deleted', 'success');
      refresh();
    } catch (e) { toast('Failed', 'error'); }
  }

  function sendNotification() {
    const subject = prompt('Subject:');
    if (!subject) return;
    const body = prompt('Message body:');
    if (!body) return;
    const target = prompt('Target (all, teams, staff, or specific user ID):') || 'all';

    API.post('notifications/send/', { subject, body, target })
      .then(() => { toast('Notification sent!', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function scheduleNotification() {
    const subject = prompt('Subject:');
    if (!subject) return;
    const body = prompt('Message body:');
    if (!body) return;
    const target = prompt('Target (all, teams, staff):') || 'all';
    const scheduled_for = prompt('Schedule for (YYYY-MM-DD HH:MM):');
    if (!scheduled_for) return;

    API.post('notifications/schedule/', { subject, body, target, scheduled_for })
      .then(() => { toast('Notification scheduled', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  async function toggleAutoRule(ruleId, enabled) {
    try {
      const rules = (dashData?.auto_rules || []).map(r => {
        if ((r.id || r.event) == ruleId) return { ...r, enabled };
        return r;
      });
      await API.post('notifications/auto-rules/', { rules });
      toast('Auto rule updated', 'success');
      refresh();
    } catch (e) { toast('Failed', 'error'); }
  }

  async function saveChannels() {
    const toggles = document.querySelectorAll('.notif-channel-toggle');
    const channels = {};
    toggles.forEach(t => { channels[t.dataset.channel] = t.checked; });
    try {
      await API.post('notifications/channels/', channels);
      toast('Channels saved', 'success');
    } catch (e) { toast('Save failed', 'error'); }
  }

  function sendTeamMessage() {
    const teamId = prompt('Team ID:');
    if (!teamId) return;
    const message = prompt('Message to team:');
    if (!message) return;

    API.post('notifications/team-message/', { team_id: parseInt(teamId), message })
      .then(() => { toast('Message sent', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  window.TOC = window.TOC || {};
  window.TOC.notifications = {
    refresh, createTemplate, editTemplate, deleteTemplate,
    sendNotification, scheduleNotification, toggleAutoRule,
    saveChannels, sendTeamMessage
  };

  // Auto-load when tab is activated
  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail && e.detail.tab === 'notifications') refresh();
  });
})();
