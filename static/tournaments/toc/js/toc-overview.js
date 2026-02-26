/**
 * TOC — Overview Tab (Command Center) JavaScript.
 *
 * Sprint 1: S1-F1 through S1-F9
 * Loads from /api/toc/<slug>/overview/ and renders:
 *   - Lifecycle pipeline visualizer (S1-F2)
 *   - 4-column stat cards (S1-F1 + S1-F6)
 *   - Alerts panel (S1-F4)
 *   - Upcoming events timeline (S1-F7)
 *   - Transition modal (S1-F3)
 *   - Freeze / Unfreeze (S1-F5)
 *   - Auto-refresh every 30s (S1-F9)
 */

;(function () {
  'use strict';

  const CFG = window.TOC_CONFIG || {};
  const API = CFG.apiBase || '';
  const $ = (s, ctx) => (ctx || document).querySelector(s);
  const $$ = (s, ctx) => [...(ctx || document).querySelectorAll(s)];

  // ── Severity config ──
  const SEVERITY = {
    critical: { icon: 'shield-alert', bg: 'bg-dc-dangerBg', border: 'border-dc-danger/30', text: 'text-dc-danger', dot: 'bg-dc-danger' },
    warning:  { icon: 'alert-triangle', bg: 'bg-dc-warningBg', border: 'border-dc-warning/30', text: 'text-dc-warning', dot: 'bg-dc-warning' },
    info:     { icon: 'info', bg: 'bg-dc-infoBg', border: 'border-dc-info/30', text: 'text-dc-info', dot: 'bg-dc-info' },
  };

  // ── Stat card icon map ──
  const STAT_ICONS = {
    registrations: 'users',
    payments: 'wallet',
    matches: 'crosshair',
    disputes: 'shield-alert',
  };

  const STAT_COLORS = {
    theme:   { iconBg: 'bg-theme-surface', iconBorder: 'border-theme-border', iconText: 'text-theme', hoverBorder: 'hover:border-theme' },
    success: { iconBg: 'bg-dc-successBg', iconBorder: 'border-dc-success/30', iconText: 'text-dc-success', hoverBorder: 'hover:border-dc-success' },
    danger:  { iconBg: 'bg-dc-dangerBg', iconBorder: 'border-dc-danger/30', iconText: 'text-dc-danger', hoverBorder: 'hover:border-dc-danger' },
    warning: { iconBg: 'bg-dc-warningBg', iconBorder: 'border-dc-warning/30', iconText: 'text-dc-warning', hoverBorder: 'hover:border-dc-warning' },
  };

  // Track dismissed alerts (client-side for Sprint 1)
  const DISMISSED_KEY = `toc-dismissed-${CFG.tournamentSlug}`;
  function getDismissed() {
    try { return JSON.parse(localStorage.getItem(DISMISSED_KEY) || '[]'); } catch { return []; }
  }
  function addDismissed(title) {
    const d = getDismissed();
    if (!d.includes(title)) { d.push(title); localStorage.setItem(DISMISSED_KEY, JSON.stringify(d)); }
  }

  let _refreshTimer = null;
  let _selectedTransition = null;

  // ═══════════════════════════════════════════════════════════════
  //  Main fetch & render
  // ═══════════════════════════════════════════════════════════════

  async function load() {
    try {
      const data = await TOC.fetch(`${API}/overview/`);
      render(data);
      // Hide stale data banner on success
      const staleBanner = $('#toc-stale-banner');
      if (staleBanner) staleBanner.classList.add('hidden');
    } catch (e) {
      console.error('[TOC:overview] Load failed:', e);
      renderError();
      // Show stale data banner on failure
      const staleBanner = $('#toc-stale-banner');
      if (staleBanner) staleBanner.classList.remove('hidden');
    }
  }

  function render(data) {
    renderLifecycle(data.lifecycle, data.transitions);
    renderStats(data.stats);
    renderAlerts(data.alerts);
    renderEvents(data.events);
    updateGlobalStatus(data);
  }

  function renderError() {
    const el = $('#overview-alerts');
    if (el) {
      el.innerHTML = `
        <div class="flex items-center gap-3 p-4 bg-dc-dangerBg border border-dc-danger/30 rounded-lg">
          <i data-lucide="wifi-off" class="w-5 h-5 text-dc-danger shrink-0"></i>
          <div>
            <p class="text-sm font-bold text-white">Connection Error</p>
            <p class="text-xs text-dc-text mt-1">Could not load overview data. Retrying in 30s…</p>
          </div>
        </div>`;
      _reinitIcons();
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  S1-F2: Lifecycle Pipeline
  // ═══════════════════════════════════════════════════════════════

  function renderLifecycle(lifecycle, transitions) {
    const container = $('#lifecycle-stages');
    if (!container) return;

    const stages = lifecycle.stages || [];
    const hasTransitions = transitions && transitions.some(t => t.can_transition);
    const btnAdvance = $('#btn-transition');

    container.innerHTML = stages.map((s, i) => {
      const isActive = s.status === 'active';
      const isDone = s.status === 'done';
      const isCancelled = s.status === 'cancelled';

      let dotClass = 'bg-dc-border';
      let textClass = 'text-dc-text';
      let lineClass = 'bg-dc-border';

      if (isDone) { dotClass = 'bg-dc-success'; textClass = 'text-dc-success'; lineClass = 'bg-dc-success'; }
      else if (isActive) { dotClass = 'bg-theme shadow-[0_0_10px_var(--color-primary)]'; textClass = 'text-theme font-bold'; }
      else if (isCancelled) { dotClass = 'bg-dc-danger'; textClass = 'text-dc-danger'; }

      const connector = i < stages.length - 1
        ? `<div class="flex-1 h-0.5 ${isDone ? 'bg-dc-success' : 'bg-dc-border'} mx-1"></div>`
        : '';

      return `
        <div class="flex items-center ${i < stages.length - 1 ? 'flex-1' : ''}">
          <div class="flex flex-col items-center gap-1.5 min-w-[60px]">
            <div class="w-3 h-3 rounded-full ${dotClass} ${isActive ? 'animate-pulse' : ''} shrink-0"></div>
            <span class="text-[9px] ${textClass} uppercase tracking-widest whitespace-nowrap">${s.name}</span>
          </div>
          ${connector}
        </div>`;
    }).join('');

    // Show/hide Advance button
    if (btnAdvance) {
      btnAdvance.classList.toggle('hidden', !hasTransitions);
      btnAdvance.onclick = () => openTransitionModal(transitions);
    }

    _reinitIcons();
  }

  // ═══════════════════════════════════════════════════════════════
  //  S1-F1 + S1-F6: Stat Cards
  // ═══════════════════════════════════════════════════════════════

  function renderStats(stats) {
    const container = $('#overview-stats');
    if (!container) return;

    container.innerHTML = stats.map(s => {
      const icon = STAT_ICONS[s.key] || 'bar-chart-3';
      const c = STAT_COLORS[s.color] || STAT_COLORS.theme;
      const isDanger = s.color === 'danger';

      return `
        <div class="glass-box rounded-xl p-5 group ${c.hoverBorder} transition-colors ${isDanger ? 'border-dc-danger/30 bg-gradient-to-br from-dc-dangerBg to-transparent' : ''}">
          <i data-lucide="${icon}" class="ghost-icon w-24 h-24 -right-4 -bottom-4 group-hover:opacity-10 transition-all"></i>
          <div class="flex justify-between items-start mb-4 relative z-10">
            <span class="text-[10px] font-bold ${isDanger ? 'text-dc-danger' : 'text-dc-text'} uppercase tracking-widest">${_esc(s.label)}</span>
            <div class="p-1.5 ${c.iconBg} rounded-md border ${c.iconBorder}">
              <i data-lucide="${icon}" class="w-3.5 h-3.5 ${c.iconText}"></i>
            </div>
          </div>
          <div class="flex items-baseline gap-2 relative z-10">
            <span class="font-display font-black text-4xl ${isDanger && s.value > 0 ? 'text-dc-danger drop-shadow-[0_0_10px_rgba(255,42,85,0.8)]' : 'text-white'}">${s.value}</span>
            ${s.detail ? `<span class="text-xs text-dc-text font-mono">${_esc(s.detail)}</span>` : ''}
          </div>
        </div>`;
    }).join('');

    _reinitIcons();
  }

  // ═══════════════════════════════════════════════════════════════
  //  S1-F4: Alerts Panel
  // ═══════════════════════════════════════════════════════════════

  function renderAlerts(alerts) {
    const container = $('#overview-alerts');
    const counter = $('#alerts-count');
    if (!container) return;

    const dismissed = getDismissed();
    const visible = alerts.filter(a => !dismissed.includes(a.title));

    if (counter) {
      counter.textContent = visible.length;
      counter.classList.toggle('hidden', visible.length === 0);
    }

    if (visible.length === 0) {
      container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-32 text-center">
          <i data-lucide="check-circle-2" class="w-8 h-8 text-dc-success mb-3"></i>
          <p class="text-sm font-bold text-white">All Clear</p>
          <p class="text-xs text-dc-text mt-1">No active alerts for this tournament.</p>
        </div>`;
      _reinitIcons();
      return;
    }

    container.innerHTML = visible.map(a => {
      const sev = SEVERITY[a.severity] || SEVERITY.info;
      return `
        <div class="flex gap-3 group" data-alert-title="${_attr(a.title)}">
          <div class="w-6 h-6 rounded-full ${sev.bg} border ${sev.border} ${sev.text} flex items-center justify-center shrink-0 mt-0.5">
            <i data-lucide="${sev.icon}" class="w-3.5 h-3.5"></i>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-start justify-between gap-2">
              <p class="text-sm font-bold text-white">${_esc(a.title)}</p>
              <button class="shrink-0 p-1 text-dc-text hover:text-white rounded opacity-0 group-hover:opacity-100 transition-opacity" onclick="TOC.overview.dismissAlert('${_attr(a.title)}', ${a.id})" title="Dismiss">
                <i data-lucide="x" class="w-3.5 h-3.5"></i>
              </button>
            </div>
            <p class="text-[10px] text-dc-text mt-0.5 leading-relaxed">${_esc(a.description)}</p>
            ${a.link_tab ? `<button class="mt-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded text-[9px] font-bold uppercase tracking-widest ${sev.text} hover:bg-white/10 transition-colors" onclick="TOC.navigate('${a.link_tab}')">${_esc(a.link_label || 'Go')} →</button>` : ''}
          </div>
        </div>`;
    }).join('');

    _reinitIcons();
  }

  // ═══════════════════════════════════════════════════════════════
  //  S1-F7: Upcoming Events
  // ═══════════════════════════════════════════════════════════════

  function renderEvents(events) {
    const container = $('#overview-events');
    if (!container) return;

    if (!events || events.length === 0) {
      container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-32 text-center">
          <i data-lucide="calendar-check" class="w-8 h-8 text-dc-text mb-3 opacity-50"></i>
          <p class="text-sm text-dc-text">No upcoming events.</p>
        </div>`;
      _reinitIcons();
      return;
    }

    container.innerHTML = events.map(ev => {
      const dt = new Date(ev.datetime);
      const relative = _relativeTime(dt);
      const formatted = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' at ' + dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

      return `
        <div class="flex items-start gap-3 group">
          <div class="w-8 h-8 rounded-lg bg-theme-surface border border-theme-border flex items-center justify-center shrink-0">
            <i data-lucide="${ev.icon || 'calendar'}" class="w-4 h-4 text-theme"></i>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-bold text-white">${_esc(ev.label)}</p>
            <p class="text-[10px] text-dc-text mt-0.5 font-mono">${formatted}</p>
          </div>
          <span class="text-[9px] font-mono text-theme bg-theme-surface px-2 py-0.5 rounded border border-theme-border whitespace-nowrap">${relative}</span>
        </div>`;
    }).join('');

    _reinitIcons();
  }

  // ═══════════════════════════════════════════════════════════════
  //  S1-F3: Transition Modal
  // ═══════════════════════════════════════════════════════════════

  function openTransitionModal(transitions) {
    const modal = $('#modal-transition');
    const container = $('#transition-options');
    const btnConfirm = $('#btn-confirm-transition');
    if (!modal || !container) return;

    _selectedTransition = null;
    if (btnConfirm) btnConfirm.disabled = true;

    container.innerHTML = transitions.map(t => {
      const canTransition = t.can_transition;
      return `
        <label class="flex items-center gap-3 p-3 rounded-lg border ${canTransition ? 'border-dc-borderLight hover:border-theme cursor-pointer' : 'border-dc-border opacity-40 cursor-not-allowed'} transition-colors ${canTransition ? 'group' : ''}">
          <input type="radio" name="transition_target" value="${t.to_status}" ${canTransition ? '' : 'disabled'} class="hidden peer">
          <div class="w-4 h-4 rounded-full border-2 border-dc-borderLight peer-checked:border-theme peer-checked:bg-theme shrink-0 transition-colors"></div>
          <div class="flex-1 min-w-0">
            <span class="text-xs font-bold text-white">${_esc(t.label)}</span>
            ${t.reason ? `<p class="text-[9px] text-dc-danger mt-0.5">${_esc(t.reason)}</p>` : ''}
          </div>
        </label>`;
    }).join('');

    // Bind radio clicks
    $$('input[name="transition_target"]', container).forEach(radio => {
      radio.addEventListener('change', () => {
        _selectedTransition = radio.value;
        if (btnConfirm) btnConfirm.disabled = false;
        // Visual active state
        $$('label', container).forEach(l => l.classList.remove('border-theme', 'bg-theme-surface'));
        radio.closest('label').classList.add('border-theme', 'bg-theme-surface');
      });
    });

    if (btnConfirm) {
      btnConfirm.onclick = () => executeTransition();
    }

    modal.classList.remove('hidden');
  }

  async function executeTransition() {
    if (!_selectedTransition) return;

    const reason = ($('#transition-reason') || {}).value || '';
    const btnConfirm = $('#btn-confirm-transition');
    if (btnConfirm) { btnConfirm.disabled = true; btnConfirm.textContent = 'Processing…'; }

    try {
      const result = await TOC.fetch(`${API}/lifecycle/transition/`, {
        method: 'POST',
        body: { to_status: _selectedTransition, reason },
      });

      $('#modal-transition').classList.add('hidden');
      TOC.toast(result.message || 'Transition successful', 'success');
      load(); // Refresh overview
    } catch (e) {
      TOC.toast(e.message || 'Transition failed', 'error');
    } finally {
      if (btnConfirm) { btnConfirm.disabled = false; btnConfirm.textContent = 'Confirm Transition'; }
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  S1-F5: Freeze / Unfreeze
  // ═══════════════════════════════════════════════════════════════

  async function executeFreeze() {
    const reason = ($('#freeze-reason') || {}).value || '';
    if (!reason || reason.length < 3) {
      TOC.toast('Please provide a reason (at least 3 characters)', 'warning');
      return;
    }

    try {
      const result = await TOC.fetch(`${API}/lifecycle/freeze/`, {
        method: 'POST',
        body: { reason },
      });

      $('#modal-freeze').classList.add('hidden');
      $('#toc-freeze-banner').classList.remove('hidden');
      TOC.toast(result.message || 'Tournament frozen', 'warning');
      load(); // Refresh
    } catch (e) {
      TOC.toast(e.message || 'Freeze failed', 'error');
    }
  }

  async function executeUnfreeze() {
    try {
      const result = await TOC.fetch(`${API}/lifecycle/unfreeze/`, {
        method: 'POST',
        body: { reason: 'Manual unfreeze from TOC' },
      });

      $('#toc-freeze-banner').classList.add('hidden');
      TOC.toast(result.message || 'Tournament unfrozen', 'success');
      load(); // Refresh
    } catch (e) {
      TOC.toast(e.message || 'Unfreeze failed', 'error');
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  Global status sync
  // ═══════════════════════════════════════════════════════════════

  function updateGlobalStatus(data) {
    const label = $('#toc-status-label');
    if (label) label.textContent = data.status_display;

    const banner = $('#toc-freeze-banner');
    if (banner) banner.classList.toggle('hidden', !data.is_frozen);

    // ── Dynamic status pill styling ──
    const pill = $('#toc-status-pill');
    if (pill) {
      // Remove old color classes
      pill.className = pill.className.replace(/bg-\S+|text-\S+|border-\S+/g, '').trim();
      const statusColors = {
        draft:        'bg-dc-text/10 text-dc-text border border-dc-border',
        registration: 'bg-dc-info/15 text-dc-info border border-dc-info/30',
        check_in:     'bg-dc-warning/15 text-dc-warning border border-dc-warning/30',
        live:         'bg-dc-success/15 text-dc-success border border-dc-success/30',
        completed:    'bg-dc-text/10 text-dc-textBright border border-dc-border',
        cancelled:    'bg-dc-danger/15 text-dc-danger border border-dc-danger/30',
      };
      const colorClasses = statusColors[data.status] || statusColors.draft;
      pill.className += ` inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold uppercase tracking-wider ${colorClasses}`;
    }

    // ── Dynamic action button (Freeze/Resume) ──
    const actionBtn = $('#toc-action-btn');
    if (actionBtn) {
      if (data.is_frozen) {
        actionBtn.innerHTML = '<i data-lucide="play" class="w-4 h-4"></i> Resume';
        actionBtn.className = 'flex items-center gap-2 px-4 py-2 rounded-xl bg-dc-success/20 text-dc-success border border-dc-success/30 text-sm font-bold hover:bg-dc-success/30 transition-colors';
        actionBtn.setAttribute('onclick', "TOC.overview.executeUnfreeze()");
      } else {
        actionBtn.innerHTML = '<i data-lucide="shield-alert" class="w-4 h-4"></i> Freeze';
        actionBtn.className = 'flex items-center gap-2 px-4 py-2 rounded-xl bg-dc-danger/20 text-dc-danger border border-dc-danger/30 text-sm font-bold hover:bg-dc-danger/30 transition-colors';
        actionBtn.setAttribute('onclick', "document.getElementById('modal-freeze').classList.remove('hidden')");
      }
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    // Update badge for alerts
    const alertCount = (data.alerts || []).length;
    if (typeof TOC.badge === 'function') {
      TOC.badge('overview', alertCount > 0 ? alertCount : 0);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  S1-F9: Auto-refresh (30s poll)
  // ═══════════════════════════════════════════════════════════════

  function startAutoRefresh() {
    stopAutoRefresh();
    _refreshTimer = setInterval(() => {
      // Only refresh if overview tab is visible
      const panel = $('[data-tab-content="overview"]');
      if (panel && !panel.classList.contains('hidden-view')) {
        load();
      }
    }, 30000);
  }

  function stopAutoRefresh() {
    if (_refreshTimer) { clearInterval(_refreshTimer); _refreshTimer = null; }
  }

  // ═══════════════════════════════════════════════════════════════
  //  Alert dismiss
  // ═══════════════════════════════════════════════════════════════

  async function dismissAlert(title, alertId) {
    addDismissed(title);
    // Fire-and-forget server dismiss
    TOC.fetch(`${API}/alerts/${alertId}/dismiss/`, { method: 'POST' }).catch(() => {});
    // Re-render alerts from last data
    const el = $(`[data-alert-title="${CSS.escape(title)}"]`);
    if (el) { el.style.opacity = '0'; el.style.transform = 'translateX(20px)'; setTimeout(() => el.remove(), 200); }
    // Update counter
    const counter = $('#alerts-count');
    if (counter) {
      const current = parseInt(counter.textContent) || 0;
      const next = Math.max(0, current - 1);
      counter.textContent = next;
      if (next === 0) counter.classList.add('hidden');
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  Helpers
  // ═══════════════════════════════════════════════════════════════

  function _esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
  function _attr(s) { return (s || '').replace(/'/g, "\\'").replace(/"/g, '&quot;'); }

  function _relativeTime(date) {
    const now = new Date();
    const diff = date - now;
    if (diff < 0) return 'Passed';
    const hours = Math.floor(diff / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    if (hours > 24) return `${Math.floor(hours / 24)}d`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  }

  function _reinitIcons() {
    if (typeof lucide !== 'undefined') {
      try { lucide.createIcons(); } catch (e) { /* ignore */ }
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  Public API — attach to window.TOC.overview
  // ═══════════════════════════════════════════════════════════════

  window.TOC = window.TOC || {};
  window.TOC.overview = {
    load,
    startAutoRefresh,
    stopAutoRefresh,
    executeFreeze,
    executeUnfreeze,
    dismissAlert,
  };

  // Auto-init when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }

  function _init() {
    load();
    startAutoRefresh();

    // Bind stale banner dismiss button
    const staleDismiss = $('#toc-stale-dismiss');
    if (staleDismiss) {
      staleDismiss.addEventListener('click', () => {
        const banner = $('#toc-stale-banner');
        if (banner) banner.classList.add('hidden');
      });
    }
  }

})();
