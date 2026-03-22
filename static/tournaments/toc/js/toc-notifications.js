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

  const CACHE_TTL_MS = 25000;
  const AUTO_REFRESH_MS = 45000;
  const STAT_IDS = ['templates', 'pending', 'total', 'auto'];
  const PANEL_IDS = ['notif-templates-list', 'notif-auto-rules', 'notif-channels', 'notif-log'];

  let dashData = null;
  let inflightPromise = null;
  let activeRequestId = 0;
  let lastFetchedAt = 0;
  let autoRefreshTimer = null;

  function isNotificationsTabActive() {
    return (window.location.hash || '').replace('#', '') === 'notifications';
  }

  function hasFreshCache() {
    return !!dashData && (Date.now() - lastFetchedAt) < CACHE_TTL_MS;
  }

  function formatTime(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function setSyncStatus(state, note) {
    const el = $('#notifications-sync-status');
    if (!el) return;
    if (state === 'loading') {
      el.className = 'text-[10px] font-mono text-dc-warning mt-1';
      el.textContent = note || 'Syncing notifications...';
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
    const el = $('#notifications-error-banner');
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
          <p class="text-xs font-bold text-white">Notifications request failed</p>
          <p class="text-[11px] text-dc-text mt-1">${esc(message)}</p>
          <button type="button" class="mt-2 px-2.5 py-1 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" onclick="TOC.notifications.refresh({ force: true })">Retry now</button>
        </div>
      </div>`;
    refreshIcons();
  }

  function setLoading(loading) {
    STAT_IDS.forEach((id) => {
      const el = $(`#notif-stat-${id}`);
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
    renderStats(safe.summary || {});
    renderTemplates(Array.isArray(safe.templates) ? safe.templates : []);
    renderAutoRules(Array.isArray(safe.auto_rules) ? safe.auto_rules : []);
    renderChannels(safe.channels && typeof safe.channels === 'object' ? safe.channels : {});
    renderLog(Array.isArray(safe.log) ? safe.log : []);
    setLoading(false);
    setErrorBanner('');
    setSyncStatus('ok');
  }

  function renderErrorEmpty(message) {
    const list = $('#notif-templates-list');
    if (list) {
      list.innerHTML = `
        <div class="glass-box rounded-xl p-8 text-center">
          <p class="text-sm text-dc-danger">${esc(message || 'Notifications unavailable')}</p>
        </div>`;
    }
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
      setSyncStatus('loading', dashData ? 'Refreshing notifications...' : 'Loading notifications...');
    }

    const requestId = ++activeRequestId;
    inflightPromise = (async () => {
      try {
        const data = await API.get('notifications/');
        if (requestId !== activeRequestId) return dashData || data;
        dashData = data;
        lastFetchedAt = Date.now();
        renderDashboard(data);
        return data;
      } catch (e) {
        if (requestId !== activeRequestId) return dashData;
        const detail = e && e.message ? String(e.message) : 'Request failed';
        console.error('[notifications] fetch error', e);
        if (dashData) {
          setLoading(false);
          setSyncStatus('error', `Using cached data (${detail})`);
          setErrorBanner(`Live refresh failed, showing cached notifications data. ${detail}`);
        } else {
          setSyncStatus('error', detail);
          setErrorBanner(detail);
          renderErrorEmpty('Failed to load notifications data.');
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
      if (!isNotificationsTabActive()) return;
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
    if (e.detail?.tab === 'notifications') {
      refresh();
      startAutoRefresh();
      return;
    }
    stopAutoRefresh();
  }

  function onVisibilityChange() {
    if (!document.hidden && isNotificationsTabActive() && !hasFreshCache()) {
      refresh({ silent: true });
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

  /* ─── Drawer helpers ─────────────────────── */
  const FIELD = 'w-full bg-dc-surface/50 border border-dc-border/50 rounded-lg px-3 py-2 text-sm text-white placeholder-dc-text/40 focus:outline-none focus:border-theme';
  const LABEL = 'block text-[10px] text-dc-text uppercase tracking-widest mb-1';
  const TRIGGERS = ['manual', 'match_ready', 'checkin_open', 'round_start', 'tournament_end'];
  function drawerFooter(submitCall, submitLabel) {
    return `<div class="flex gap-3 p-4 pt-0">
      <button onclick="${submitCall}" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">${submitLabel}</button>
      <button onclick="TOC.drawer.close()" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
  }

  /* ─── Actions ─────────────────────────────── */
  function createTemplate() {
    const triggerOpts = TRIGGERS.map(t => `<option value="${t}">${t}</option>`).join('');
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Template Name *</label>
        <input id="notif-tpl-name" type="text" class="${FIELD}" placeholder="e.g. Round Start Notification"></div>
      <div><label class="${LABEL}">Subject *</label>
        <input id="notif-tpl-subject" type="text" class="${FIELD}" placeholder="Subject line"></div>
      <div><label class="${LABEL}">Body * <span class="normal-case text-dc-text/60">({player}, {team}, {tournament} supported)</span></label>
        <textarea id="notif-tpl-body" rows="4" class="${FIELD} resize-none" placeholder="Message body..."></textarea></div>
      <div><label class="${LABEL}">Trigger Event</label>
        <select id="notif-tpl-trigger" class="${FIELD}">${triggerOpts}</select></div>
    </div>`;
    TOC.drawer.open('New Notification Template', body, drawerFooter("TOC.notifications._submitCreateTemplate()", 'Create Template'));
    setTimeout(() => document.getElementById('notif-tpl-name')?.focus(), 50);
  }

  function _submitCreateTemplate() {
    const name    = document.getElementById('notif-tpl-name')?.value.trim();
    const subject = document.getElementById('notif-tpl-subject')?.value.trim();
    const body    = document.getElementById('notif-tpl-body')?.value.trim();
    const trigger = document.getElementById('notif-tpl-trigger')?.value || 'manual';
    if (!name)    { toast('Template name is required', 'error'); return; }
    if (!subject) { toast('Subject is required', 'error'); return; }
    if (!body)    { toast('Body is required', 'error'); return; }
    API.post('notifications/templates/', { name, subject, body, trigger, enabled: true })
      .then(() => { toast('Template created', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function editTemplate(id) {
    if (!dashData?.templates) return;
    const t = dashData.templates.find((x, i) => (x.id || i) == id);
    if (!t) return;
    const triggerOpts = TRIGGERS.map(tr =>
      `<option value="${tr}" ${tr === t.trigger ? 'selected' : ''}>${tr}</option>`
    ).join('');
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Template Name *</label>
        <input id="notif-etpl-name" type="text" value="${esc(t.name)}" class="${FIELD}"></div>
      <div><label class="${LABEL}">Subject *</label>
        <input id="notif-etpl-subject" type="text" value="${esc(t.subject)}" class="${FIELD}"></div>
      <div><label class="${LABEL}">Body</label>
        <textarea id="notif-etpl-body" rows="4" class="${FIELD} resize-none">${esc(t.body)}</textarea></div>
      <div><label class="${LABEL}">Trigger Event</label>
        <select id="notif-etpl-trigger" class="${FIELD}">${triggerOpts}</select></div>
    </div>`;
    TOC.drawer.open('Edit Template', body, drawerFooter(`TOC.notifications._submitEditTemplate('${id}', ${!!t.enabled})`, 'Save Changes'));
  }

  function _submitEditTemplate(id, enabled) {
    const name    = document.getElementById('notif-etpl-name')?.value.trim();
    const subject = document.getElementById('notif-etpl-subject')?.value.trim();
    const body    = document.getElementById('notif-etpl-body')?.value.trim() || '';
    const trigger = document.getElementById('notif-etpl-trigger')?.value || 'manual';
    if (!name)    { toast('Name is required', 'error'); return; }
    if (!subject) { toast('Subject is required', 'error'); return; }
    API.put(`notifications/templates/${id}/`, { name, subject, body, trigger, enabled })
      .then(() => { toast('Template updated', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  async function deleteTemplate(id) {
    if (!confirm('Delete this template?')) return;
    try {
      await API.delete(`notifications/templates/${id}/`);
      toast('Template deleted', 'success');
      invalidate();
      refresh({ force: true });
    } catch (e) { toast('Failed', 'error'); }
  }

  function sendNotification() {
    const targetOpts = ['all', 'teams', 'staff'].map(t => `<option value="${t}">${t}</option>`).join('');
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Subject *</label>
        <input id="notif-send-subject" type="text" class="${FIELD}" placeholder="Notification subject"></div>
      <div><label class="${LABEL}">Message Body *</label>
        <textarea id="notif-send-body" rows="4" class="${FIELD} resize-none" placeholder="Notification message..."></textarea></div>
      <div><label class="${LABEL}">Target Audience</label>
        <select id="notif-send-target" class="${FIELD}">${targetOpts}</select></div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button onclick="TOC.notifications._submitSend()" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Send Now</button>
      <button onclick="TOC.drawer.close()" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Send Notification', body, footer);
    setTimeout(() => document.getElementById('notif-send-subject')?.focus(), 50);
  }

  function _submitSend() {
    const subject = document.getElementById('notif-send-subject')?.value.trim();
    const body    = document.getElementById('notif-send-body')?.value.trim();
    const target  = document.getElementById('notif-send-target')?.value || 'all';
    if (!subject) { toast('Subject is required', 'error'); return; }
    if (!body)    { toast('Message body is required', 'error'); return; }
    API.post('notifications/send/', { subject, body, target })
      .then(() => { toast('Notification sent!', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function scheduleNotification() {
    const targetOpts = ['all', 'teams', 'staff'].map(t => `<option value="${t}">${t}</option>`).join('');
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Subject *</label>
        <input id="notif-sched-subject" type="text" class="${FIELD}" placeholder="Notification subject"></div>
      <div><label class="${LABEL}">Message Body *</label>
        <textarea id="notif-sched-body" rows="4" class="${FIELD} resize-none" placeholder="Notification message..."></textarea></div>
      <div><label class="${LABEL}">Target Audience</label>
        <select id="notif-sched-target" class="${FIELD}">${targetOpts}</select></div>
      <div><label class="${LABEL}">Schedule For *</label>
        <input id="notif-sched-dt" type="datetime-local" class="${FIELD}"></div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button onclick="TOC.notifications._submitSchedule()" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Schedule</button>
      <button onclick="TOC.drawer.close()" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Schedule Notification', body, footer);
    setTimeout(() => document.getElementById('notif-sched-subject')?.focus(), 50);
  }

  function _submitSchedule() {
    const subject       = document.getElementById('notif-sched-subject')?.value.trim();
    const body          = document.getElementById('notif-sched-body')?.value.trim();
    const target        = document.getElementById('notif-sched-target')?.value || 'all';
    const scheduled_for = document.getElementById('notif-sched-dt')?.value;
    if (!subject)       { toast('Subject is required', 'error'); return; }
    if (!body)          { toast('Message body is required', 'error'); return; }
    if (!scheduled_for) { toast('Schedule date/time is required', 'error'); return; }
    API.post('notifications/schedule/', { subject, body, target, scheduled_for })
      .then(() => { toast('Notification scheduled', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function sendTeamMessage() {
    const teams = (dashData?.teams || []);
    const teamOpts = teams.length
      ? teams.map(t => `<option value="${t.id}">${esc(t.name)}</option>`).join('')
      : '<option value="">— enter team ID below —</option>';
    const body = `<div class="space-y-4 p-5">
      ${teams.length
        ? `<div><label class="${LABEL}">Team *</label>
            <select id="notif-team-id" class="${FIELD}">${teamOpts}</select></div>`
        : `<div><label class="${LABEL}">Team ID *</label>
            <input id="notif-team-id" type="number" class="${FIELD}" placeholder="Numeric team ID"></div>`}
      <div><label class="${LABEL}">Message *</label>
        <textarea id="notif-team-msg" rows="4" class="${FIELD} resize-none" placeholder="Message to team..."></textarea></div>
    </div>`;
    TOC.drawer.open('Send Team Message', body, drawerFooter("TOC.notifications._submitTeamMsg()", 'Send Message'));
    setTimeout(() => document.getElementById('notif-team-msg')?.focus(), 50);
  }

  function _submitTeamMsg() {
    const rawId  = document.getElementById('notif-team-id')?.value;
    const teamId = parseInt(rawId);
    const message = document.getElementById('notif-team-msg')?.value.trim();
    if (!teamId)  { toast('Team is required', 'error'); return; }
    if (!message) { toast('Message is required', 'error'); return; }
    API.post('notifications/team-message/', { team_id: teamId, message })
      .then(() => { toast('Message sent', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
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
      invalidate();
      refresh({ force: true });
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

  window.TOC = window.TOC || {};
  window.TOC.notifications = {
    refresh, invalidate,
    createTemplate, _submitCreateTemplate,
    editTemplate, _submitEditTemplate, deleteTemplate,
    sendNotification, _submitSend,
    scheduleNotification, _submitSchedule,
    sendTeamMessage, _submitTeamMsg,
    toggleAutoRule, saveChannels,
  };

  document.addEventListener('toc:tab-changed', onTabChange);
  document.addEventListener('visibilitychange', onVisibilityChange);

  if (isNotificationsTabActive()) {
    refresh();
    startAutoRefresh();
  }
})();
