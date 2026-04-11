/*
 * TOC Logs Module
 * Dedicated smart log view for admin + main organizer.
 */
;(function () {
  'use strict';

  const NS = (window.TOC = window.TOC || {});
  const api = NS.api;

  const state = {
    rows: [],
    filteredRows: [],
    anomalySummary: null,
    live: false,
    liveTimer: null,
    liveIntervalMs: 8000,
    refreshInFlight: false,
  };

  const $ = (id) => document.getElementById(id);

  function isLogsTabActive() {
    return (window.location.hash || '').replace('#', '') === 'logs';
  }

  function canViewLogs() {
    return !!(window.TOC_CONFIG && window.TOC_CONFIG.canViewLogs);
  }

  function setSyncStatus(msg) {
    const el = $('logs-sync-status');
    if (el) el.textContent = msg;
  }

  function setLastFetch(ts) {
    const el = $('logs-last-fetch');
    if (!el) return;
    if (!ts) {
      el.textContent = 'Never';
      return;
    }
    const d = new Date(ts);
    el.textContent = 'Last sync ' + d.toLocaleTimeString();
  }

  function getFilters() {
    const action = ($('logs-filter-action')?.value || '').trim().toLowerCase();
    const user = ($('logs-filter-user')?.value || '').trim().toLowerCase();
    const tab = ($('logs-filter-tab')?.value || '').trim().toLowerCase();
    const since = ($('logs-filter-since')?.value || '').trim();
    const limit = parseInt(($('logs-filter-limit')?.value || '100'), 10) || 100;
    return { action, user, tab, since, limit };
  }

  function computeSinceIso(sinceValue) {
    if (!sinceValue) return '';
    const now = Date.now();
    const map = {
      '15m': 15 * 60 * 1000,
      '1h': 60 * 60 * 1000,
      '6h': 6 * 60 * 60 * 1000,
      '24h': 24 * 60 * 60 * 1000,
      '7d': 7 * 24 * 60 * 60 * 1000,
    };
    const delta = map[sinceValue];
    if (!delta) return '';
    return new Date(now - delta).toISOString();
  }

  function buildApiQuery(filters) {
    const params = new URLSearchParams();
    if (filters.action) params.set('action', filters.action);
    if (filters.tab) params.set('tab', filters.tab);
    if (filters.limit) params.set('limit', String(filters.limit));
    const sinceIso = computeSinceIso(filters.since);
    if (sinceIso) params.set('since', sinceIso);
    return params.toString();
  }

  function applyClientFilter(rows, filters) {
    return (rows || []).filter((row) => {
      const action = String(row.action || '').toLowerCase();
      const username = String(row.username || '').toLowerCase();
      const tab = String((row.detail && row.detail.tab) || '').toLowerCase();

      if (filters.action && !action.includes(filters.action)) return false;
      if (filters.user && !username.includes(filters.user)) return false;
      if (filters.tab && tab !== filters.tab) return false;
      return true;
    });
  }

  function classifyAction(action) {
    const a = String(action || '').toUpperCase();
    if (a.startsWith('POST')) return 'POST';
    if (a.startsWith('PUT')) return 'PUT';
    if (a.startsWith('PATCH')) return 'PATCH';
    if (a.startsWith('DELETE')) return 'DELETE';
    return 'OTHER';
  }

  function toRelativeTime(ts) {
    if (!ts) return '';
    const sec = Math.max(0, Math.floor((Date.now() - new Date(ts).getTime()) / 1000));
    if (sec < 60) return 'just now';
    if (sec < 3600) return Math.floor(sec / 60) + 'm ago';
    if (sec < 86400) return Math.floor(sec / 3600) + 'h ago';
    return Math.floor(sec / 86400) + 'd ago';
  }

  function esc(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function toneClassForTab(tab) {
    const t = String(tab || '').toLowerCase();
    if (t === 'participants') return 'text-dc-success bg-dc-success/10 border-dc-success/30';
    if (t === 'payments') return 'text-dc-warning bg-dc-warning/10 border-dc-warning/30';
    if (t === 'matches') return 'text-dc-info bg-dc-info/10 border-dc-info/30';
    if (t === 'settings') return 'text-dc-danger bg-dc-danger/10 border-dc-danger/30';
    if (t === 'disputes') return 'text-purple-300 bg-purple-400/10 border-purple-400/30';
    if (t === 'logs') return 'text-theme bg-theme/10 border-theme/30';
    return 'text-dc-text bg-dc-panel border-dc-border';
  }

  function renderRows() {
    const feed = $('logs-feed');
    if (!feed) return;

    const rows = state.filteredRows || [];
    if (!rows.length) {
      feed.innerHTML = '<p class="text-xs text-dc-text italic text-center py-8">No log events found for current filters.</p>';
      return;
    }

    feed.innerHTML = rows.map((row) => {
      const tab = (row.detail && row.detail.tab) || 'unknown';
      const toneClass = toneClassForTab(tab);
      const relative = toRelativeTime(row.created_at);
      const diffStr = row.diff ? JSON.stringify(row.diff) : '';

      return '' +
        '<div class="px-4 py-3 hover:bg-dc-panel/60 transition-colors">' +
          '<div class="flex items-start gap-3">' +
            '<div class="w-8 h-8 rounded-lg bg-dc-surface border border-dc-border flex items-center justify-center shrink-0 mt-0.5">' +
              '<i data-lucide="activity" class="w-4 h-4 text-theme"></i>' +
            '</div>' +
            '<div class="min-w-0 flex-1">' +
              '<div class="flex items-center gap-2 flex-wrap">' +
                '<span class="text-xs font-bold text-white">' + esc(row.username || 'system') + '</span>' +
                '<span class="text-[10px] font-mono text-dc-text">' + esc(row.action || '') + '</span>' +
                '<span class="text-[9px] uppercase px-1.5 py-0.5 rounded border ' + toneClass + '">' + esc(tab) + '</span>' +
                '<span class="ml-auto text-[10px] text-dc-text/60 font-mono">' + esc(relative) + '</span>' +
              '</div>' +
              (diffStr ? '<details class="mt-1.5"><summary class="text-[10px] text-dc-text cursor-pointer">payload</summary><pre class="mt-1 text-[10px] text-dc-textBright/80 bg-black/20 border border-dc-border rounded p-2 overflow-x-auto">' + esc(diffStr.slice(0, 1200)) + '</pre></details>' : '') +
            '</div>' +
          '</div>' +
        '</div>';
    }).join('');

    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }

  function renderKpis() {
    const rows = state.filteredRows || [];
    const kpi = {
      total: rows.length,
      write: 0,
      participants: 0,
      payments: 0,
      matches: 0,
      settings: 0,
      disputes: 0,
      system: 0,
    };

    rows.forEach((row) => {
      const kind = classifyAction(row.action);
      if (kind !== 'OTHER') kpi.write += 1;
      const tab = String((row.detail && row.detail.tab) || '').toLowerCase();
      if (tab === 'participants') kpi.participants += 1;
      else if (tab === 'payments') kpi.payments += 1;
      else if (tab === 'matches') kpi.matches += 1;
      else if (tab === 'settings') kpi.settings += 1;
      else if (tab === 'disputes') kpi.disputes += 1;
      else kpi.system += 1;
    });

    const setVal = (id, val) => { const el = $(id); if (el) el.textContent = String(val); };
    setVal('logs-kpi-total', kpi.total);
    setVal('logs-kpi-write', kpi.write);
    setVal('logs-kpi-participants', kpi.participants);
    setVal('logs-kpi-payments', kpi.payments);
    setVal('logs-kpi-matches', kpi.matches);
    setVal('logs-kpi-settings', kpi.settings);
    setVal('logs-kpi-disputes', kpi.disputes);
    setVal('logs-kpi-system', kpi.system);
  }

  function renderAnomalySummary() {
    const wrap = $('logs-anomaly-summary');
    const list = $('logs-anomaly-list');
    const stateEl = $('logs-anomaly-state');
    const summary = state.anomalySummary;

    if (!wrap || !list || !stateEl) return;
    if (!summary) {
      stateEl.textContent = 'No data';
      stateEl.className = 'text-[10px] font-mono px-2 py-0.5 rounded border border-dc-border text-dc-text';
      list.innerHTML = '<p class="text-dc-text/70">No anomaly scan results yet.</p>';
      if (typeof TOC.badge === 'function') TOC.badge('logs', 0);
      return;
    }

    const criticalCount = parseInt(summary.critical_count || 0, 10) || 0;
    if (criticalCount > 0) {
      stateEl.textContent = criticalCount + ' critical';
      stateEl.className = 'text-[10px] font-mono px-2 py-0.5 rounded border border-dc-danger/40 text-dc-danger bg-dc-danger/10';
    } else {
      stateEl.textContent = 'Clean';
      stateEl.className = 'text-[10px] font-mono px-2 py-0.5 rounded border border-dc-success/40 text-dc-success bg-dc-success/10';
    }

    const items = Array.isArray(summary.items) ? summary.items : [];
    if (!items.length) {
      list.innerHTML = '<p class="text-dc-success">No critical anomalies detected.</p>';
    } else {
      list.innerHTML = items.map((item) => {
        const sev = String(item.severity || '').toLowerCase();
        const tone = sev === 'critical'
          ? 'border-dc-danger/30 bg-dc-danger/10 text-dc-danger'
          : 'border-dc-warning/30 bg-dc-warning/10 text-dc-warning';
        const hasRepair = item.code === 'capacity_overflow';
        const repairBtn = hasRepair
          ? '<button data-click="TOC.logs.repairCapacityOverflow" data-click-args="[false]" class="px-2 py-1 rounded border border-dc-warning/30 text-dc-warning text-[10px] font-bold uppercase tracking-widest hover:bg-dc-warning/10 transition-colors">Dry-run fix</button>'
          : '';
        return '' +
          '<div class="rounded-lg border px-3 py-2 ' + tone + '">' +
            '<div class="flex items-center justify-between gap-2 flex-wrap">' +
              '<p class="font-bold text-xs text-white">' + esc(item.title || 'Anomaly') + '</p>' +
              '<div class="flex items-center gap-2">' + repairBtn + '<span class="text-[10px] font-mono">' + esc(String(item.count || 0)) + '</span></div>' +
            '</div>' +
            '<p class="mt-1 text-[11px] text-dc-textBright/90">' + esc(item.detail || '') + '</p>' +
          '</div>';
      }).join('');
    }

    if (typeof TOC.badge === 'function') {
      TOC.badge('logs', criticalCount);
    }
  }

  function applyAndRenderClientFilter() {
    const filters = getFilters();
    state.filteredRows = applyClientFilter(state.rows, filters);
    renderKpis();
    renderAnomalySummary();
    renderRows();
  }

  async function refreshAnomalyBadge() {
    if (!canViewLogs() || !api) return;
    try {
      const payload = await api.get('audit-log/?limit=1&include_summary=1');
      const summary = payload && payload.anomaly_summary ? payload.anomaly_summary : null;
      state.anomalySummary = summary;
      renderAnomalySummary();
    } catch (_e) {
      // Silent: badge refresh is opportunistic and must not interrupt UX.
    }
  }

  async function repairCapacityOverflow(apply) {
    if (!canViewLogs() || !api) return;
    let reason = 'Restored disqualification after accidental reactivation.';
    if (apply) {
      const userReason = window.prompt('Repair reason (required to apply):', reason);
      if (userReason == null) return;
      reason = String(userReason || '').trim();
      if (!reason) {
        if (window.TOC && typeof window.TOC.toast === 'function') {
          window.TOC.toast('Reason is required.', 'error');
        }
        return;
      }
    }

    try {
      const payload = await api.post('audit-log/repair-capacity-overflow/', {
        apply: !!apply,
        reason: reason,
      });
      const msg = payload && payload.message ? payload.message : (apply ? 'Repair applied.' : 'Dry-run complete.');
      showRepairReportModal(payload, apply);
      if (window.TOC && typeof window.TOC.toast === 'function') {
        window.TOC.toast(msg, apply ? 'success' : 'info');
      }
      await refresh();
    } catch (e) {
      if (window.TOC && typeof window.TOC.toast === 'function') {
        window.TOC.toast(e.message || 'Repair action failed.', 'error');
      }
    }
  }

  function showRepairReportModal(payload, applied) {
    const data = payload || {};
    const before = Number(data.before_active_count ?? data.active_count ?? 0);
    const after = Number(data.after_active_count ?? data.new_active_count ?? before);
    const repairedUsers = Array.isArray(data.repaired_usernames) ? data.repaired_usernames : [];
    const repairedCount = Number(data.repaired ?? data.overflow ?? repairedUsers.length ?? 0);

    const existing = document.getElementById('toc-repair-report-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'toc-repair-report-modal';
    modal.className = 'fixed inset-0 z-[140] flex items-center justify-center p-4';
    modal.innerHTML = '' +
      '<div class="absolute inset-0 bg-black/75 backdrop-blur-sm" data-repair-dismiss="1"></div>' +
      '<div class="relative w-full max-w-lg rounded-2xl border border-dc-border bg-dc-surface shadow-[0_20px_70px_rgba(0,0,0,0.75)] overflow-hidden">' +
        '<div class="px-5 py-4 border-b border-dc-border flex items-center justify-between gap-3">' +
          '<div class="min-w-0">' +
            '<p class="text-[10px] uppercase tracking-[0.2em] text-dc-text font-bold">Capacity Repair Report</p>' +
            '<h3 class="text-sm font-black text-white">' + (applied ? 'Repair Applied' : 'Dry-run Preview') + '</h3>' +
          '</div>' +
          '<button type="button" class="h-8 w-8 rounded-lg border border-dc-border text-dc-text hover:text-white hover:border-white/40" data-repair-dismiss="1">' +
            '<i data-lucide="x" class="w-4 h-4 mx-auto"></i>' +
          '</button>' +
        '</div>' +
        '<div class="p-5 space-y-4">' +
          '<div class="grid grid-cols-3 gap-2">' +
            '<div class="rounded-lg border border-dc-border bg-dc-panel/60 p-3 text-center"><p class="text-[9px] text-dc-text uppercase tracking-widest">Before</p><p class="text-lg font-black text-white">' + before + '</p></div>' +
            '<div class="rounded-lg border border-theme/35 bg-theme/10 p-3 text-center"><p class="text-[9px] text-theme uppercase tracking-widest">Repaired</p><p class="text-lg font-black text-theme">' + repairedCount + '</p></div>' +
            '<div class="rounded-lg border border-dc-success/35 bg-dc-success/10 p-3 text-center"><p class="text-[9px] text-dc-success uppercase tracking-widest">After</p><p class="text-lg font-black text-dc-success">' + after + '</p></div>' +
          '</div>' +
          '<div>' +
            '<p class="text-[10px] text-dc-text uppercase tracking-widest mb-2">Repaired Usernames</p>' +
            (repairedUsers.length
              ? '<div class="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">' + repairedUsers.map(function (username) {
                  return '<span class="px-2 py-1 rounded-md text-[10px] font-mono border border-dc-border bg-dc-bg text-dc-textBright">' + esc(username) + '</span>';
                }).join('') + '</div>'
              : '<p class="text-xs text-dc-text/80">No candidate usernames were returned.</p>') +
          '</div>' +
          '<p class="text-[11px] text-dc-text">' + esc(data.message || '') + '</p>' +
        '</div>' +
      '</div>';

    document.body.appendChild(modal);

    modal.querySelectorAll('[data-repair-dismiss="1"]').forEach(function (btn) {
      btn.addEventListener('click', function () { modal.remove(); });
    });

    if (typeof lucide !== 'undefined') {
      try { lucide.createIcons(); } catch (_e) { /* no-op */ }
    }
  }

  async function refresh() {
    if (!canViewLogs() || !isLogsTabActive() || !api) return;
    if (state.refreshInFlight) return;

    state.refreshInFlight = true;
    setSyncStatus('Syncing logs...');

    try {
      const filters = getFilters();
      const qs = buildApiQuery(filters);
      const fullQs = qs ? (qs + '&include_summary=1') : 'include_summary=1';
      const payload = await api.get('audit-log/?' + fullQs);
      if (Array.isArray(payload)) {
        state.rows = payload;
        state.anomalySummary = null;
      } else {
        state.rows = Array.isArray(payload && payload.rows) ? payload.rows : [];
        state.anomalySummary = payload && payload.anomaly_summary ? payload.anomaly_summary : null;
      }
      applyAndRenderClientFilter();
      const now = new Date().toISOString();
      setLastFetch(now);
      setSyncStatus('Last sync ' + new Date(now).toLocaleTimeString());
    } catch (e) {
      setSyncStatus('Sync failed');
      if (window.TOC && typeof window.TOC.toast === 'function') {
        window.TOC.toast(e.message || 'Failed to load logs', 'error');
      }
    } finally {
      state.refreshInFlight = false;
    }
  }

  function wireFilterInputs() {
    const ids = [
      'logs-filter-action',
      'logs-filter-user',
      'logs-filter-tab',
      'logs-filter-since',
      'logs-filter-limit',
    ];

    ids.forEach((id) => {
      const el = $(id);
      if (!el || el.dataset.logsBound === '1') return;
      const eventName = (id === 'logs-filter-action' || id === 'logs-filter-user') ? 'input' : 'change';
      el.addEventListener(eventName, () => {
        if (id === 'logs-filter-limit' || id === 'logs-filter-since') {
          refresh();
        } else {
          applyAndRenderClientFilter();
        }
      });
      el.dataset.logsBound = '1';
    });
  }

  function updateLiveToggleUi() {
    const btn = $('logs-live-toggle');
    if (!btn) return;
    btn.innerHTML = state.live
      ? '<i data-lucide="radio" class="w-3 h-3"></i> Live ON'
      : '<i data-lucide="radio" class="w-3 h-3"></i> Live OFF';
    btn.classList.toggle('bg-theme/10', state.live);
    btn.classList.toggle('border-theme/50', state.live);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function toggleLive() {
    state.live = !state.live;
    if (state.live) {
      state.liveTimer = window.setInterval(() => {
        if (!document.hidden && isLogsTabActive()) {
          refresh();
        }
      }, state.liveIntervalMs);
    } else if (state.liveTimer) {
      window.clearInterval(state.liveTimer);
      state.liveTimer = null;
    }
    updateLiveToggleUi();
  }

  function exportJson() {
    const rows = state.filteredRows || [];
    const blob = new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json' });
    const slug = (NS.slug || 'tournament').replace(/[^a-z0-9-_]/gi, '_');
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'toc_logs_' + slug + '_' + stamp + '.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  function onTabChanged(e) {
    if (e && e.detail && e.detail.tab === 'logs') {
      wireFilterInputs();
      refresh();
    }
  }

  function init() {
    if (!canViewLogs()) return;
    wireFilterInputs();
    updateLiveToggleUi();
    refreshAnomalyBadge();
    if (isLogsTabActive()) {
      refresh();
    }
    document.addEventListener('toc:tab-changed', onTabChanged);
  }

  NS.logs = {
    init,
    refresh,
    refreshAnomalyBadge,
    repairCapacityOverflow,
    toggleLive,
    exportJson,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
