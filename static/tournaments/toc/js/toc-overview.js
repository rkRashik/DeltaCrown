/**
 * TOC — Overview Tab (Command Center) JavaScript.
 *
 * Sprint 1: S1-F1 through S1-F9
 * Sprint 25: Action Queue, Tournament Progress, Quick Stats, Activity Log
 *
 * Loads from /api/toc/<slug>/overview/ and renders:
 *   - Lifecycle pipeline visualizer (S1-F2)
 *   - Vital stat hero cards by ID (S1-F1 + S1-F6, refactored S25)
 *   - Quick stats strip from overview payload (fallback /stats/) (S25)
 *   - Alerts panel (S1-F4)
 *   - Action Queue (S25, derived from actionable alerts)
 *   - Tournament Progress timeline (S25, derived from lifecycle)
 *   - Activity Log from overview payload (fallback /audit-log/) (S25)
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
  let _lastSyncAt = null;
  let _overviewFeedItems = [];
  let _overviewFeedFilter = 'all';
  let _overviewFeedSearch = '';
  let _overviewFeedDebounce = null;
  const OVERVIEW_CACHE_KEY = `toc-overview-cache-${CFG.tournamentSlug || 'default'}`;
  const OVERVIEW_CACHE_TTL_MS = 30000;

  const LOADING_IDS = [
    '#stat-participants', '#stat-revenue', '#stat-active-matches', '#stat-open-disputes',
    '#stat-completion', '#stat-avg-duration', '#stat-dq-rate', '#stat-checked-in', '#stat-in-progress', '#stat-forfeits',
    '#health-score-value', '#health-grade', '#health-label',
    '#hb-reg', '#hb-pay', '#hb-match', '#hb-disp', '#hb-alert',
  ];

  // ═══════════════════════════════════════════════════════════════
  //  Main fetch & render
  // ═══════════════════════════════════════════════════════════════

  async function load(options) {
    const opts = options || {};
    const showLoading = !opts.background;
    if (showLoading) {
      setOverviewLoading(true);
    }
    updateSyncStatus('loading');
    try {
      const data = await TOC.fetch(`${API}/overview/`);
      storeOverviewCache(data);
      render(data);
      _lastSyncAt = new Date();
      updateSyncStatus('ok');
    } catch (e) {
      console.error('[TOC:overview] Load failed:', e);
      updateSyncStatus('error', e && e.message ? String(e.message) : 'request failed');
      renderError(e);
      if (showLoading) {
        setOverviewLoading(false);
      }
    }
  }

  function storeOverviewCache(payload) {
    if (!payload) return;
    try {
      localStorage.setItem(OVERVIEW_CACHE_KEY, JSON.stringify({ ts: Date.now(), data: payload }));
    } catch (e) {
      // Ignore storage quota and serialization failures.
    }
  }

  function loadOverviewCache() {
    try {
      const raw = localStorage.getItem(OVERVIEW_CACHE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed || !parsed.ts || !parsed.data) return null;
      if ((Date.now() - parsed.ts) > OVERVIEW_CACHE_TTL_MS) return null;
      return parsed.data;
    } catch (e) {
      return null;
    }
  }

  function render(data) {
    const payload = data || {};
    const lifecycle = payload.lifecycle || { stages: [], progress_pct: 0 };
    const lifecycleStepper = payload.lifecycle_stepper || null;
    const transitions = Array.isArray(payload.transitions) ? payload.transitions : [];
    const alerts = Array.isArray(payload.alerts) ? payload.alerts : [];
    const events = Array.isArray(payload.events) ? payload.events : [];

    renderLifecycle(lifecycle, transitions, lifecycleStepper);
    renderStats(Array.isArray(payload.stats) ? payload.stats : []);
    renderAlerts(alerts);
    renderEvents(events);
    renderActionQueue(alerts);
    renderProgress(lifecycle);
    renderHealthScore(payload.health_score || null);
    renderUpcomingMatches(payload.upcoming_matches || []);
    renderGroupProgress(payload.group_progress || null);
    renderCountdowns(payload.countdowns || []);
    renderQuickStats(payload.quick_stats || null);
    renderActivityLog(payload.activity_log || []);
    renderTournamentFeed(payload.tournament_feed || []);
    updateGlobalStatus(payload);

    // Backward compatibility fallback when backend doesn't provide bundled data yet.
    if (!payload.quick_stats) loadQuickStats();
    if (!Array.isArray(payload.activity_log)) loadActivityLog();
    if (!Array.isArray(payload.tournament_feed)) loadTournamentFeed();

    setOverviewLoading(false);
  }

  function renderError(err) {
    const el = $('#overview-alerts');
    if (el) {
      const detail = err && err.message ? _esc(String(err.message)) : 'Could not load overview data. Retrying in 30s…';
      el.innerHTML = `
        <div class="flex items-center gap-3 p-4 bg-dc-dangerBg border border-dc-danger/30 rounded-lg">
          <i data-lucide="wifi-off" class="w-5 h-5 text-dc-danger shrink-0"></i>
          <div>
            <p class="text-sm font-bold text-white">Connection Error</p>
            <p class="text-xs text-dc-text mt-1">${detail}</p>
            <button class="mt-2 px-2.5 py-1.5 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" data-click="TOC.overview.load">Retry Now</button>
          </div>
        </div>`;
      _reinitIcons();
    }
  }

  function updateSyncStatus(state, note) {
    const el = $('#overview-sync-status');
    if (!el) return;

    if (state === 'loading') {
      el.className = 'text-[10px] font-mono text-dc-warning';
      el.textContent = 'Syncing overview...';
      return;
    }

    if (state === 'error') {
      el.className = 'text-[10px] font-mono text-dc-danger';
      el.textContent = `Sync failed${note ? `: ${note}` : ''}`;
      return;
    }

    if (_lastSyncAt) {
      el.className = 'text-[10px] font-mono text-dc-text';
      el.textContent = `Last sync ${_lastSyncAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  S1-F2: Lifecycle Pipeline
  // ═══════════════════════════════════════════════════════════════

  function renderLifecycle(lifecycle, transitions, lifecycleStepper) {
    const container = $('#lifecycle-stages');
    const nextActionEl = $('#lifecycle-next-action');
    if (!container) return;

    const stages = lifecycle.stages || [];
    const steps = Array.isArray(lifecycleStepper && lifecycleStepper.steps) ? lifecycleStepper.steps : [];
    const hasStepper = steps.length > 0;
    const hasTransitions = transitions && transitions.some(t => t.can_transition);
    const btnAdvance = $('#btn-transition');

    if (hasStepper) {
      const activeIndex = steps.findIndex((s) => s.status === 'active');

      container.innerHTML = `
        <div class="flex items-start min-w-full">
          ${steps.map((step, i) => {
            const status = step.status || 'pending';
            const isDone = status === 'done';
            const isActive = status === 'active';
            const markerClass = isDone
              ? 'bg-dc-success/20 border-dc-success/50 text-dc-success'
              : isActive
                ? 'bg-theme-surface border-theme text-theme shadow-[0_0_20px_var(--color-primary-muted)]'
                : 'bg-dc-bg border-dc-border text-dc-text';
            const labelClass = isDone
              ? 'text-dc-success'
              : isActive
                ? 'text-white font-black'
                : 'text-dc-text';
            const connectorDone = activeIndex >= 0 ? i < activeIndex : isDone;
            const connector = i < steps.length - 1
              ? `<div class="h-0.5 flex-1 mt-4 mx-2 ${connectorDone ? 'bg-dc-success/60' : 'bg-dc-border'}"></div>`
              : '';
            const iconName = isDone ? 'check' : (step.icon || 'circle');

            return `
              <div class="flex items-start ${i < steps.length - 1 ? 'flex-1' : ''}">
                <div class="flex flex-col items-center gap-2 min-w-[96px]">
                  <div class="w-8 h-8 rounded-xl border ${markerClass} flex items-center justify-center ${isActive ? 'animate-pulse' : ''}">
                    <i data-lucide="${_esc(iconName)}" class="w-4 h-4"></i>
                  </div>
                  <div class="text-center">
                    <p class="text-[9px] uppercase tracking-[0.18em] ${labelClass}">${_esc(step.label || step.key || '')}</p>
                    <p class="text-[8px] mt-0.5 font-mono uppercase tracking-widest ${isDone ? 'text-dc-success/80' : isActive ? 'text-theme' : 'text-dc-text/60'}">${_esc(status)}</p>
                  </div>
                </div>
                ${connector}
              </div>`;
          }).join('')}
        </div>`;

      if (nextActionEl) {
        const nextAction = lifecycleStepper && lifecycleStepper.next_action;
        if (nextAction && nextAction.label) {
          const tab = (nextAction.tab || '').trim();
          const tabLabel = _tabLabel(tab);
          nextActionEl.classList.remove('hidden');
          nextActionEl.innerHTML = `
            <div class="mt-4 rounded-xl border border-theme/25 bg-theme/5 px-4 py-3">
              <div class="flex items-start gap-3">
                <div class="w-7 h-7 rounded-lg bg-theme/20 border border-theme/35 text-theme flex items-center justify-center shrink-0">
                  <i data-lucide="move-right" class="w-4 h-4"></i>
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-[9px] uppercase tracking-[0.2em] text-theme font-black">Next Action</p>
                  <p class="text-xs text-white mt-1 leading-relaxed">${_esc(nextAction.label)}</p>
                </div>
                ${tab ? `<button class="shrink-0 px-3 py-1.5 rounded-lg bg-theme-surface border border-theme/40 text-[10px] font-black uppercase tracking-widest text-theme hover:bg-theme hover:text-dc-bg transition-colors" data-click="TOC.navigate" data-click-args="[&quot;${_attr(tab)}&quot;]">Open ${_esc(tabLabel)}</button>` : ''}
              </div>
            </div>`;
        } else {
          nextActionEl.classList.add('hidden');
          nextActionEl.innerHTML = '';
        }
      }
    } else {
      container.innerHTML = stages.map((s, i) => {
        const isActive = s.status === 'active';
        const isDone = s.status === 'done';
        const isCancelled = s.status === 'cancelled';

        let dotClass = 'bg-dc-border';
        let textClass = 'text-dc-text';

        if (isDone) { dotClass = 'bg-dc-success'; textClass = 'text-dc-success'; }
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

      if (nextActionEl) {
        nextActionEl.classList.add('hidden');
        nextActionEl.innerHTML = '';
      }
    }

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

  // ── Stat ID mapping (overview API key → HTML element ID prefix) ──
  const STAT_MAP = {
    registrations: { val: 'stat-participants', meta: 'stat-participants-meta' },
    payments:      { val: 'stat-revenue',      meta: 'stat-revenue-meta' },
    matches:       { val: 'stat-active-matches', meta: 'stat-active-meta' },
    disputes:      { val: 'stat-open-disputes', meta: 'stat-disputes-meta' },
  };

  function renderStats(stats) {
    if (!stats) return;
    stats.forEach(function (s) {
      const mapping = STAT_MAP[s.key];
      if (!mapping) return;
      const valEl = $('#' + mapping.val);
      const metaEl = $('#' + mapping.meta);
      if (valEl) {
        valEl.textContent = typeof s.value === 'number' ? s.value.toLocaleString() : s.value;
        // Danger pulse for disputes > 0
        if (s.key === 'disputes' && s.value > 0) {
          valEl.classList.add('text-dc-danger', 'drop-shadow-[0_0_10px_rgba(255,42,85,0.8)]');
        }
        if (s.key === 'matches') {
          valEl.classList.toggle('text-dc-success', Number(s.value || 0) > 0);
          valEl.classList.toggle('drop-shadow-[0_0_14px_rgba(16,185,129,0.6)]', Number(s.value || 0) > 0);
        }
      }
      if (metaEl && s.detail) metaEl.textContent = s.detail;
    });
  }

  // ═══════════════════════════════════════════════════════════════
  //  S1-F4: Alerts Panel
  // ═══════════════════════════════════════════════════════════════

  function renderAlerts(alerts) {
    const container = $('#overview-alerts');
    const counter = $('#alerts-count');
    if (!container) return;

    const safeAlerts = Array.isArray(alerts) ? alerts : [];
    const dismissed = getDismissed();
    const visible = safeAlerts.filter(a => !dismissed.includes(a.title));

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
              <button class="shrink-0 p-1 text-dc-text hover:text-white rounded opacity-0 group-hover:opacity-100 transition-opacity" data-click="TOC.overview.dismissAlert" data-click-args="[&quot;${_attr(a.title)}&quot;,&quot;${a.id}&quot;]" title="Dismiss">
                <i data-lucide="x" class="w-3.5 h-3.5"></i>
              </button>
            </div>
            <p class="text-[10px] text-dc-text mt-0.5 leading-relaxed">${_esc(a.description)}</p>
            ${a.link_tab ? `<button class="mt-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded text-[9px] font-bold uppercase tracking-widest ${sev.text} hover:bg-white/10 transition-colors" data-click="TOC.navigate" data-click-args="['${a.link_tab}']">${_esc(a.link_label || 'Go')} →</button>` : ''}
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
  //  Sprint 25: Action Queue (derived from alerts)
  // ═══════════════════════════════════════════════════════════════

  function renderActionQueue(alerts) {
    const container = $('#action-queue');
    const countBadge = $('#action-queue-count');
    if (!container) return;

    // Filter to actionable alerts (those with a link_tab)
    const actionable = (alerts || []).filter(function (a) { return !!a.link_tab; });

    if (countBadge) {
      countBadge.textContent = actionable.length;
      countBadge.classList.toggle('hidden', actionable.length === 0);
    }

    if (actionable.length === 0) {
      container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-32 text-center">
          <i data-lucide="inbox" class="w-8 h-8 text-dc-success mb-3 opacity-60"></i>
          <p class="text-sm font-bold text-white">No pending actions</p>
          <p class="text-xs text-dc-text mt-1">All clear — nothing needs attention.</p>
        </div>`;
      _reinitIcons();
      return;
    }

    container.innerHTML = actionable.map(function (a) {
      var sev = SEVERITY[a.severity] || SEVERITY.info;
      return `
        <button class="w-full flex items-center gap-3 p-3 rounded-lg ${sev.bg} border ${sev.border} hover:brightness-110 transition-all text-left group"
                data-click="TOC.navigate" data-click-args="['${a.link_tab}']">
          <div class="w-7 h-7 rounded-full ${sev.bg} border ${sev.border} flex items-center justify-center shrink-0">
            <i data-lucide="${sev.icon}" class="w-3.5 h-3.5 ${sev.text}"></i>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-bold text-white truncate">${_esc(a.title)}</p>
            <p class="text-[10px] text-dc-text mt-0.5 truncate">${_esc(a.description)}</p>
          </div>
          <i data-lucide="chevron-right" class="w-4 h-4 text-dc-text group-hover:text-white transition-colors shrink-0"></i>
        </button>`;
    }).join('');

    _reinitIcons();
  }

  // ═══════════════════════════════════════════════════════════════
  //  Sprint 25: Tournament Progress (derived from lifecycle)
  // ═══════════════════════════════════════════════════════════════

  function renderProgress(lifecycle) {
    const container = $('#tournament-progress');
    if (!container) return;

    var stages = (lifecycle && lifecycle.stages) || [];
    if (stages.length === 0) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-6">No lifecycle data.</p>';
      return;
    }

    var progressPct = lifecycle.progress_pct || 0;

    container.innerHTML = `
      <div class="mb-4">
        <div class="flex items-center justify-between mb-1.5">
          <span class="text-[10px] font-bold text-dc-text uppercase tracking-widest">Overall Progress</span>
          <span class="text-xs font-mono font-bold text-theme">${progressPct}%</span>
        </div>
        <div class="h-2 bg-dc-bg rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-theme to-dc-info rounded-full transition-all duration-700" style="width:${progressPct}%"></div>
        </div>
      </div>
      <div class="space-y-2">
        ${stages.map(function (s) {
          var isDone = s.status === 'done';
          var isActive = s.status === 'active';
          var isCancelled = s.status === 'cancelled';
          var iconName = isDone ? 'check-circle-2' : isActive ? 'circle-dot' : isCancelled ? 'x-circle' : 'circle';
          var iconColor = isDone ? 'text-dc-success' : isActive ? 'text-theme' : isCancelled ? 'text-dc-danger' : 'text-dc-text/40';
          var textColor = isDone ? 'text-dc-success' : isActive ? 'text-white font-bold' : isCancelled ? 'text-dc-danger line-through' : 'text-dc-text';
          return `
            <div class="flex items-center gap-2.5 ${isActive ? 'bg-theme-surface/30 -mx-2 px-2 py-1.5 rounded-lg border border-theme-border/30' : ''}">
              <i data-lucide="${iconName}" class="w-4 h-4 ${iconColor} shrink-0 ${isActive ? 'animate-pulse' : ''}"></i>
              <span class="text-xs ${textColor}">${_esc(s.name)}</span>
            </div>`;
        }).join('')}
      </div>`;

    _reinitIcons();
  }

  // ═══════════════════════════════════════════════════════════════
  //  Sprint 25: Quick Stats (prefer overview payload, fallback /stats/)
  // ═══════════════════════════════════════════════════════════════

  function renderQuickStats(data) {
    var m = (data && data.matches) || {};
    var p = (data && data.participants) || {};

    _setText('#stat-completion', m.completion_pct != null ? m.completion_pct + '%' : '—');
    _setText('#stat-avg-duration', m.avg_duration_minutes != null ? m.avg_duration_minutes + 'm' : '—');
    _setText('#stat-dq-rate', p.dq_rate_pct != null ? p.dq_rate_pct + '%' : '—');
    _setText('#stat-checked-in', p.checked_in != null ? p.checked_in : '—');
    _setText('#stat-in-progress', m.in_progress != null ? m.in_progress : '—');
    _setText('#stat-forfeits', m.forfeits != null ? m.forfeits : 0);
  }

  async function loadQuickStats() {
    try {
      var data = await TOC.fetch(API + '/stats/');
      renderQuickStats(data);
    } catch (e) {
      console.warn('[TOC:overview] Quick stats fetch failed:', e);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  Sprint 25: Activity Log (from /audit-log/ endpoint)
  // ═══════════════════════════════════════════════════════════════

  async function loadActivityLog() {
    try {
      var entries = await TOC.fetch(API + '/audit-log/?limit=25');
      renderActivityLog(entries);
    } catch (e) {
      console.warn('[TOC:overview] Activity log fetch failed:', e);
    }
  }

  async function loadTournamentFeed() {
    try {
      var data = await TOC.fetch(API + '/announcements/?search=&pinned=false');
      renderTournamentFeed(Array.isArray(data && data.announcements) ? data.announcements : []);
    } catch (e) {
      console.warn('[TOC:overview] Tournament feed fetch failed:', e);
    }
  }

  function wireTournamentFeedControls() {
    var search = $('#overview-feed-search');
    if (search && search.dataset.bound !== '1') {
      search.dataset.bound = '1';
      search.addEventListener('input', function () {
        clearTimeout(_overviewFeedDebounce);
        _overviewFeedDebounce = setTimeout(function () {
          _overviewFeedSearch = (search.value || '').trim().toLowerCase();
          renderTournamentFeed(_overviewFeedItems);
        }, 180);
      });
    }

    var filterWrap = $('#overview-feed-filters');
    if (filterWrap && filterWrap.dataset.bound !== '1') {
      filterWrap.dataset.bound = '1';
      filterWrap.querySelectorAll('[data-feed-filter]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          _overviewFeedFilter = btn.getAttribute('data-feed-filter') || 'all';
          renderTournamentFeed(_overviewFeedItems);
        });
      });
    }
  }

  function renderTournamentFeed(feedItems) {
    var container = $('#overview-tournament-feed');
    var countBadge = $('#overview-feed-count');
    if (!container) return;

    var items = Array.isArray(feedItems) ? feedItems : [];
    _overviewFeedItems = items;

    var filtered = items.filter(function (item) {
      if (_overviewFeedFilter === 'pinned' && !item.is_pinned) return false;
      if (_overviewFeedFilter === 'important' && !item.is_important) return false;
      if (_overviewFeedSearch) {
        var title = String(item.title || '').toLowerCase();
        var message = String(item.message || '').toLowerCase();
        if (!title.includes(_overviewFeedSearch) && !message.includes(_overviewFeedSearch)) return false;
      }
      return true;
    });

    if (countBadge) {
      countBadge.textContent = filtered.length;
      countBadge.classList.toggle('hidden', filtered.length === 0);
    }

    var filterWrap = $('#overview-feed-filters');
    if (filterWrap) {
      filterWrap.querySelectorAll('[data-feed-filter]').forEach(function (btn) {
        var isActive = btn.getAttribute('data-feed-filter') === _overviewFeedFilter;
        btn.classList.toggle('bg-theme/15', isActive);
        btn.classList.toggle('text-theme', isActive);
        btn.classList.toggle('border-theme/30', isActive);
        btn.classList.toggle('border-dc-border', !isActive);
        btn.classList.toggle('text-dc-text', !isActive);
      });
    }

    if (filtered.length === 0) {
      container.innerHTML = '' +
        '<div class="flex flex-col items-center justify-center h-32 text-center">' +
          '<i data-lucide="radio" class="w-8 h-8 text-dc-text mb-3 opacity-40"></i>' +
          '<p class="text-sm text-dc-text">No feed updates for this filter.</p>' +
        '</div>';
      _reinitIcons();
      return;
    }

    container.innerHTML = filtered.map(function (entry) {
      var created = entry.created_at ? new Date(entry.created_at) : null;
      var rel = created ? _timeAgo(created) : '';
      var visual = _feedVisual(entry);
      return '' +
        '<article class="px-4 py-3 hover:bg-white/[0.02] transition-colors">' +
          '<div class="flex items-start justify-between gap-3">' +
            '<div class="min-w-0">' +
              '<div class="flex items-center gap-1.5 mb-1 flex-wrap">' +
                '<span class="text-base leading-none">' + visual.symbol + '</span>' +
                '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ' + visual.tone + '">' + _esc(visual.label) + '</span>' +
                (entry.is_pinned ? '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-dc-warning/15 border border-dc-warning/25 text-dc-warning">Pinned</span>' : '') +
                (entry.is_important ? '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-dc-danger/15 border border-dc-danger/25 text-dc-danger">Important</span>' : '') +
                (entry.author ? '<span class="text-[10px] font-mono text-dc-text">' + _esc(entry.author) + '</span>' : '') +
              '</div>' +
              '<h4 class="text-sm text-white font-bold truncate flex items-center gap-1.5"><i data-lucide="' + _esc(visual.icon) + '" class="w-3.5 h-3.5 text-theme"></i><span>' + _esc(entry.title || 'Update') + '</span></h4>' +
              '<p class="text-xs text-dc-text mt-1 leading-relaxed">' + _esc(entry.message || '') + '</p>' +
            '</div>' +
            (rel ? '<span class="text-[10px] font-mono text-theme bg-theme/10 border border-theme/20 rounded px-2 py-0.5 shrink-0">' + rel + '</span>' : '') +
          '</div>' +
        '</article>';
    }).join('');

    _reinitIcons();
  }

  function renderActivityLog(entries) {
    var container = $('#activity-log');
    var countBadge = $('#activity-log-count');
    if (!container) return;

    var items = Array.isArray(entries) ? entries : [];

    if (countBadge) {
      countBadge.textContent = items.length;
      countBadge.classList.toggle('hidden', items.length === 0);
    }

    if (items.length === 0) {
      container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-32 text-center">
          <i data-lucide="scroll-text" class="w-8 h-8 text-dc-text mb-3 opacity-40"></i>
          <p class="text-sm text-dc-text">No activity recorded yet.</p>
        </div>`;
      _reinitIcons();
      return;
    }

    container.innerHTML = items.map(function (e) {
      var dt = new Date(e.created_at);
      var timeStr = dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      var dateStr = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      var detail = e.detail || {};
      var desc = detail.description || e.action || 'Action';
      var tab = detail.tab || '';
      var user = e.username || 'system';

      return `
        <div class="flex items-start gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors group">
          <div class="w-7 h-7 rounded-full bg-dc-surface border border-dc-border flex items-center justify-center shrink-0 mt-0.5">
            <i data-lucide="${_activityIcon(e.action)}" class="w-3.5 h-3.5 text-dc-text"></i>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs text-white">${_esc(desc)}</p>
            <div class="flex items-center gap-2 mt-1">
              <span class="text-[10px] text-dc-text font-mono">${_esc(user)}</span>
              ${tab ? `<span class="text-[9px] text-dc-text bg-dc-bg px-1.5 py-0.5 rounded">${_esc(tab)}</span>` : ''}
            </div>
          </div>
          <span class="text-[10px] text-dc-text font-mono whitespace-nowrap shrink-0">${dateStr} ${timeStr}</span>
        </div>`;
    }).join('');

    _reinitIcons();
  }

  function _activityIcon(action) {
    if (!action) return 'activity';
    var a = action.toLowerCase();
    if (a.includes('score') || a.includes('result')) return 'target';
    if (a.includes('dispute')) return 'shield-alert';
    if (a.includes('transition') || a.includes('lifecycle')) return 'arrow-right-circle';
    if (a.includes('freeze')) return 'snowflake';
    if (a.includes('match')) return 'swords';
    if (a.includes('approve') || a.includes('verify')) return 'check-circle-2';
    if (a.includes('reject') || a.includes('disqualify')) return 'x-circle';
    if (a.includes('payment')) return 'wallet';
    return 'activity';
  }

  // ═══════════════════════════════════════════════════════════════
  //  S1-F3: Transition Modal
  // ═══════════════════════════════════════════════════════════════

  // ═══════════════════════════════════════════════════════════════
  //  Sprint 27: Health Score Ring
  // ═══════════════════════════════════════════════════════════════

  function renderHealthScore(hs) {
    if (!hs) return;

    const scoreEl = $('#health-score-value');
    const gradeEl = $('#health-grade');
    const labelEl = $('#health-label');
    const ringEl = $('#health-ring-progress');
    const bgGlow = $('#health-bg-glow');

    if (scoreEl) scoreEl.textContent = hs.score;
    if (gradeEl) gradeEl.textContent = hs.grade;
    if (labelEl) labelEl.textContent = hs.label;

    // Animate ring progress (circumference = 2 * π * 42 ≈ 264)
    if (ringEl) {
      const offset = 264 - (264 * hs.score / 100);
      requestAnimationFrame(() => { ringEl.style.strokeDashoffset = offset; });

      // Color based on score
      ringEl.classList.remove('text-theme', 'text-dc-success', 'text-dc-warning', 'text-dc-danger');
      if (hs.score >= 75) ringEl.classList.add('text-dc-success');
      else if (hs.score >= 50) ringEl.classList.add('text-theme');
      else if (hs.score >= 30) ringEl.classList.add('text-dc-warning');
      else ringEl.classList.add('text-dc-danger');
    }

    // Background glow
    if (bgGlow) {
      if (hs.score >= 75) bgGlow.style.background = 'radial-gradient(circle at center, rgba(0,255,136,0.15) 0%, transparent 70%)';
      else if (hs.score >= 50) bgGlow.style.background = 'radial-gradient(circle at center, rgba(var(--color-primary-rgb,255,85,0),0.15) 0%, transparent 70%)';
      else bgGlow.style.background = 'radial-gradient(circle at center, rgba(255,42,85,0.15) 0%, transparent 70%)';
    }

    // Breakdown values
    var bd = hs.breakdown || {};
    _setText('#hb-reg', bd.registration != null ? bd.registration + '%' : '—');
    _setText('#hb-pay', bd.payments != null ? bd.payments + '%' : '—');
    _setText('#hb-match', bd.matches != null ? bd.matches + '%' : '—');
    _setText('#hb-disp', bd.disputes != null ? bd.disputes + '%' : '—');
    _setText('#hb-alert', bd.alerts != null ? bd.alerts + '%' : '—');
  }

  // ═══════════════════════════════════════════════════════════════
  //  Sprint 27: Upcoming Matches Widget
  // ═══════════════════════════════════════════════════════════════

  function renderUpcomingMatches(matches) {
    var container = $('#upcoming-matches');
    if (!container) return;

    if (!matches || matches.length === 0) {
      container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-24 text-center">
          <i data-lucide="calendar-check" class="w-6 h-6 text-dc-text/30 mb-2"></i>
          <p class="text-[10px] text-dc-text font-mono">No upcoming matches</p>
        </div>`;
      _reinitIcons();
      return;
    }

    container.innerHTML = matches.map(function (m) {
      var time = '—';
      var relative = '';
      var isLive = String(m.state || '').toLowerCase() === 'live';
      if (m.scheduled_time) {
        var d = new Date(m.scheduled_time);
        time = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' ' +
               d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
        relative = _relativeTime(d);
      }
      return `
        <div class="next-match-command-row ${isLive ? 'live' : ''} flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.05] transition-colors group cursor-pointer" data-click="TOC.navigate" data-click-args="[&quot;schedule&quot;]">
          <div class="w-7 h-7 rounded-lg bg-dc-info/10 border border-dc-info/20 flex items-center justify-center shrink-0">
            <span class="text-[9px] font-mono font-black text-dc-info">M${m.match_number || '?'}</span>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5">
              <span class="text-[10px] text-white font-bold truncate">${_esc(m.participant1_name)}</span>
              <span class="text-[9px] text-dc-text">vs</span>
              <span class="text-[10px] text-white font-bold truncate">${_esc(m.participant2_name)}</span>
            </div>
            <div class="flex items-center gap-2 mt-0.5">
              <span class="text-[9px] text-dc-text font-mono">${time}</span>
              <span class="text-[8px] text-theme bg-theme/10 px-1.5 py-0.5 rounded border border-theme/20 font-mono">R${m.round_number || '?'}</span>
            </div>
          </div>
          ${isLive
            ? '<a href="/tournaments/' + _attr(CFG.tournamentSlug || '') + '/matches/' + _attr(m.id || '') + '/room/?admin=1" data-click="event.stopPropagation" class="text-[9px] font-black uppercase tracking-widest text-emerald-200 bg-emerald-500/15 border border-emerald-400/35 px-2.5 py-1 rounded animate-pulse shrink-0">LIVE - Enter Lobby</a>'
            : (relative ? '<span class="text-[9px] font-mono text-dc-info bg-dc-info/10 px-2 py-0.5 rounded border border-dc-info/20 shrink-0">' + relative + '</span>' : '')}
        </div>`;
    }).join('');

    _reinitIcons();
  }

  // ═══════════════════════════════════════════════════════════════
  //  Sprint 27: Group Stage Progress
  // ═══════════════════════════════════════════════════════════════

  function renderGroupProgress(gp) {
    var container = $('#group-progress');
    var badge = $('#group-progress-badge');
    if (!container) return;

    if (!gp) {
      container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-24 text-center">
          <i data-lucide="layout-grid" class="w-6 h-6 text-dc-text/30 mb-2"></i>
          <p class="text-[10px] text-dc-text font-mono">No group stage configured</p>
        </div>`;
      if (badge) badge.classList.add('hidden');
      _reinitIcons();
      return;
    }

    if (badge) {
      badge.textContent = gp.completion_pct + '%';
      badge.classList.remove('hidden');
    }

    var stateLabel = (gp.state || 'unknown').replace(/_/g, ' ');
    var stateColor = gp.state === 'completed' ? 'text-dc-success' : gp.state === 'active' ? 'text-theme' : 'text-dc-text';

    container.innerHTML = `
      <div class="mb-3">
        <div class="flex items-center justify-between mb-1.5">
          <span class="text-[9px] font-bold text-dc-text uppercase tracking-widest">Group Stage</span>
          <span class="text-[9px] font-bold ${stateColor} uppercase tracking-widest">${_esc(stateLabel)}</span>
        </div>
        <div class="h-2 bg-dc-bg rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-purple-500 to-theme rounded-full transition-all duration-700" style="width:${gp.completion_pct || 0}%"></div>
        </div>
        <div class="flex items-center justify-between mt-1">
          <span class="text-[9px] font-mono text-dc-text">${gp.completed_matches || 0} / ${gp.total_matches || 0} matches</span>
          <span class="text-[9px] font-mono text-theme font-bold">${gp.completion_pct || 0}%</span>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-2">
        ${(gp.groups || []).map(function (g) {
          var gPct = g.matches_total > 0 ? Math.round((g.matches_completed / g.matches_total) * 100) : 0;
          var gLabel = g.matches_total > 0
            ? g.matches_completed + '/' + g.matches_total
            : (g.teams || 0) + ' teams';
          return '<div class="bg-dc-bg border border-dc-border rounded-lg p-2">' +
            '<div class="flex items-center justify-between mb-1">' +
            '<p class="text-[9px] font-bold text-white truncate">' + _esc(g.name) + '</p>' +
            '<span class="text-[8px] text-dc-text font-mono">' + gLabel + '</span></div>' +
            (g.matches_total > 0
              ? '<div class="h-1 bg-dc-panel rounded-full overflow-hidden"><div class="h-full bg-theme rounded-full transition-all" style="width:' + gPct + '%"></div></div>'
              : '') +
          '</div>';
        }).join('')}
      </div>
      <div class="mt-2 text-center">
        <button data-click="TOC.navigate" data-click-args="[&quot;brackets&quot;]" class="text-[9px] text-dc-text hover:text-theme transition-colors font-mono uppercase tracking-widest">
          View Groups → 
        </button>
      </div>`;

    _reinitIcons();
  }

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
  //  Finalize (organizer recovery path for LIVE-stuck tournaments)
  // ═══════════════════════════════════════════════════════════════

  function openFinalizeModal() {
    const modal = $('#modal-finalize');
    if (!modal) return;
    const forceCb = $('#finalize-force');
    if (forceCb) forceCb.checked = false;
    const btnConfirm = $('#btn-confirm-finalize');
    if (btnConfirm) {
      btnConfirm.disabled = false;
      btnConfirm.textContent = 'Confirm Finalize';
      btnConfirm.onclick = () => executeFinalize();
    }
    modal.classList.remove('hidden');
    _reinitIcons();
  }

  async function executeFinalize() {
    const forceCb = $('#finalize-force');
    const force = !!(forceCb && forceCb.checked);
    const btnConfirm = $('#btn-confirm-finalize');
    if (btnConfirm) { btnConfirm.disabled = true; btnConfirm.textContent = 'Processing…'; }

    try {
      const result = await TOC.fetch(`${API}/lifecycle/finalize/`, {
        method: 'POST',
        body: { force },
      });

      const modal = $('#modal-finalize');
      if (modal) modal.classList.add('hidden');
      TOC.toast(result.message || 'Tournament finalized.', 'success');
      load(); // Refresh overview + lifecycle
    } catch (e) {
      // API returns {finalized: false, reason} on guard block (400), {error} on 403/validation.
      // tocFetch picks up error/detail/message; reason lives on payload.
      const msg =
        (e && e.payload && e.payload.reason)
        || (e && e.message)
        || 'Finalize failed';
      TOC.toast(msg, 'error');
    } finally {
      if (btnConfirm) { btnConfirm.disabled = false; btnConfirm.textContent = 'Confirm Finalize'; }
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

    // Finalize button — only visible when tournament is LIVE and not frozen.
    // Non-superusers still see it; API enforces the guard. Force checkbox is
    // only rendered in the modal when request.user.is_superuser.
    const btnFinalize = $('#btn-finalize');
    if (btnFinalize) {
      const showFinalize = data.status === 'live' && !data.is_frozen;
      btnFinalize.classList.toggle('hidden', !showFinalize);
      btnFinalize.onclick = () => openFinalizeModal();
    }

    // ── Dynamic status pill styling ──
    const pill = $('#toc-status-pill');
    if (pill) {
      // Remove old color classes
      pill.className = pill.className.replace(/bg-\S+|text-\S+|border-\S+/g, '').trim();
      const statusColors = {
        draft:        'bg-dc-text/10 text-dc-text border border-dc-border',
        registration: 'bg-dc-info/15 text-dc-info border border-dc-info/30',
        published:    'bg-dc-info/15 text-dc-info border border-dc-info/30',
        registration_open: 'bg-dc-info/15 text-dc-info border border-dc-info/30',
        registration_closed: 'bg-dc-warning/15 text-dc-warning border border-dc-warning/30',
        check_in:     'bg-dc-warning/15 text-dc-warning border border-dc-warning/30',
        in_progress:  'bg-dc-success/15 text-dc-success border border-dc-success/30',
        live:         'bg-dc-success/15 text-dc-success border border-dc-success/30',
        completed:    'bg-dc-text/10 text-dc-textBright border border-dc-border',
        finalized:    'bg-dc-text/10 text-dc-textBright border border-dc-border',
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
        actionBtn.setAttribute('data-click', 'TOC.overview.executeUnfreeze');
      } else {
        actionBtn.innerHTML = '<i data-lucide="shield-alert" class="w-4 h-4"></i> Freeze';
        actionBtn.className = 'flex items-center gap-2 px-4 py-2 rounded-xl bg-dc-danger/20 text-dc-danger border border-dc-danger/30 text-sm font-bold hover:bg-dc-danger/30 transition-colors';
        actionBtn.setAttribute('data-click-show', 'modal-freeze');
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
    if (window.TOC && TOC.isTerminalStatus && TOC.isTerminalStatus()) return;
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
  function _setText(sel, val) { var el = $(sel); if (el) el.textContent = val; }

  function setOverviewLoading(isLoading) {
    LOADING_IDS.forEach(function (sel) {
      var el = $(sel);
      if (!el) return;
      el.classList.toggle('toc-loading-value', !!isLoading);
    });
  }

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

  function _timeAgo(date) {
    const diffMs = Date.now() - date.getTime();
    if (diffMs < 0) return _relativeTime(date);
    const sec = Math.floor(diffMs / 1000);
    if (sec < 60) return 'just now';
    if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
    return `${Math.floor(sec / 86400)}d ago`;
  }

  function _feedVisual(entry) {
    const text = String((entry && entry.title) || '') + ' ' + String((entry && entry.message) || '');
    const t = text.toLowerCase();
    if ((entry && entry.is_important) || t.includes('urgent') || t.includes('critical')) {
      return { symbol: '🚨', icon: 'siren', label: 'Urgent', tone: 'bg-dc-danger/10 text-dc-danger border border-dc-danger/20' };
    }
    if (t.includes('draw') || t.includes('schedule') || t.includes('time')) {
      return { symbol: '🗓️', icon: 'calendar-clock', label: 'Schedule', tone: 'bg-dc-warning/10 text-dc-warning border border-dc-warning/20' };
    }
    if (t.includes('stream') || t.includes('live')) {
      return { symbol: '📡', icon: 'radio', label: 'Live', tone: 'bg-dc-info/10 text-dc-info border border-dc-info/20' };
    }
    if (t.includes('result') || t.includes('winner') || t.includes('qualified')) {
      return { symbol: '🏆', icon: 'trophy', label: 'Result', tone: 'bg-dc-success/10 text-dc-success border border-dc-success/20' };
    }
    return { symbol: '📣', icon: 'megaphone', label: 'Update', tone: 'bg-theme/10 text-theme border border-theme/20' };
  }

  function _tabLabel(tab) {
    if (!tab) return 'Tab';
    return String(tab)
      .replace(/_/g, ' ')
      .replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  // ═══════════════════════════════════════════════════════════════
  //  Countdown Timers
  // ═══════════════════════════════════════════════════════════════

  let _countdownTimers = [];

  function renderCountdowns(countdowns) {
    const container = $('#overview-countdowns');
    if (!container) return;

    // Stop any existing tickers
    _countdownTimers.forEach(id => clearInterval(id));
    _countdownTimers = [];

    if (!countdowns || !countdowns.length) {
      container.classList.add('hidden');
      return;
    }

    container.classList.remove('hidden');
    container.innerHTML = '';

    // Map countdown types to colors
    const typeColor = {
      registration: 'text-dc-info border-dc-info/30 bg-dc-info/5',
      start: 'text-dc-success border-dc-success/30 bg-dc-success/5',
      match: 'text-theme border-theme/30 bg-theme/5',
      checkin: 'text-dc-warning border-dc-warning/30 bg-dc-warning/5',
    };
    const typeIcon = {
      registration: 'user-plus',
      start: 'play-circle',
      match: 'swords',
      checkin: 'user-check',
    };

    // Create card for each countdown
    countdowns.forEach((cd, idx) => {
      const cardId = `cd-card-${idx}`;
      const colorClass = typeColor[cd.type] || 'text-dc-text border-dc-border/30 bg-dc-surface/50';
      const icon = typeIcon[cd.type] || 'clock';

      const card = document.createElement('div');
      card.id = cardId;
      card.className = `flex items-center gap-3 px-4 py-3 rounded-xl border ${colorClass} min-w-[200px]`;
      card.innerHTML = `
        <i data-lucide="${icon}" class="w-4 h-4 shrink-0"></i>
        <div>
          <div class="text-[10px] uppercase tracking-widest opacity-70">${cd.label}</div>
          <div class="text-sm font-bold font-mono" id="cd-time-${idx}">--:--:--</div>
        </div>`;
      container.appendChild(card);

      // Live tick
      let seconds = cd.seconds_remaining;
      let timerId;
      function tick() {
        if (seconds <= 0) {
          const el = $(`#cd-time-${idx}`);
          if (el) el.textContent = 'Now!';
          if (timerId) clearInterval(timerId);
          return;
        }
        const d = Math.floor(seconds / 86400);
        const h = Math.floor((seconds % 86400) / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        const el = $(`#cd-time-${idx}`);
        if (el) {
          if (d > 0) {
            el.textContent = `${d}d ${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
          } else {
            el.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
          }
        }
        seconds--;
      }
      tick();
      timerId = setInterval(tick, 1000);
      _countdownTimers.push(timerId);
    });

    _reinitIcons();
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
    executeFinalize,
    openFinalizeModal,
    dismissAlert,
    refreshActionQueue: function () { load(); },
    refreshActivityLog: loadActivityLog,
    refreshQuickStats: loadQuickStats,
    refreshTournamentFeed: loadTournamentFeed,
  };

  // Auto-init when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _boot);
  } else {
    _boot();
  }

  function _init() {
    wireTournamentFeedControls();
    const cached = loadOverviewCache();
    if (cached) {
      render(cached);
      _lastSyncAt = new Date();
      updateSyncStatus('ok');
      load({ background: true });
    } else {
      load();
    }
    startAutoRefresh();
  }

  function _boot() {
    const activeTab = (window.location.hash || '#overview').replace('#', '') || 'overview';
    if (activeTab === 'overview') {
      _init();
    }

    document.addEventListener('toc:tab-changed', function (e) {
      if (e.detail && e.detail.tab === 'overview') {
        if (!_refreshTimer) {
          _init();
        }
      } else {
        stopAutoRefresh();
      }
    });
  }

})();
