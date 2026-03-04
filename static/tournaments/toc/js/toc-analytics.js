/**
 * TOC Analytics Module — Sprint 28
 * Analytics & Insights tab: registration funnel, match analytics,
 * revenue, engagement, activity timeline, export.
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
      const data = await API.get('analytics/');
      dashData = data;
      renderOverviewStats(data);
      renderRegFunnel(data.registration || {});
      renderMatchAnalytics(data.matches || {});
      renderTimeline(data.timeline || []);
    } catch (e) {
      console.error('[analytics] fetch error', e);
    }
  }

  function renderOverviewStats(data) {
    const reg = data.registration || {};
    const mat = data.matches || {};
    const rev = data.revenue || {};
    const el = (id, v) => { const e = $(`#analytics-stat-${id}`); if (e) e.textContent = v; };
    el('participants', reg.total || 0);
    el('matches', mat.total || 0);
    el('revenue', rev.net_revenue != null ? `$${rev.net_revenue}` : '$0');
    const completionPct = mat.total > 0 ? Math.round((mat.completed || 0) / mat.total * 100) : 0;
    el('completion', completionPct + '%');
  }

  function renderRegFunnel(reg) {
    const container = $('#analytics-reg-funnel');
    if (!container) return;

    const funnel = reg.funnel || {};
    const total = funnel.total || reg.total || 0;
    const approved = funnel.approved || reg.approved || 0;
    const pending = funnel.pending || reg.pending || 0;
    const rejected = funnel.rejected || reg.rejected || 0;
    const capacity = reg.capacity || 0;
    const fillRate = reg.fill_rate || 0;

    const bars = [
      { label: 'Registered', count: total, color: 'bg-theme', pct: 100 },
      { label: 'Approved', count: approved, color: 'bg-dc-success', pct: total > 0 ? Math.round(approved / total * 100) : 0 },
      { label: 'Pending', count: pending, color: 'bg-dc-warning', pct: total > 0 ? Math.round(pending / total * 100) : 0 },
      { label: 'Rejected', count: rejected, color: 'bg-dc-danger', pct: total > 0 ? Math.round(rejected / total * 100) : 0 },
    ];

    let html = '<div class="space-y-3">';
    bars.forEach(b => {
      html += `
        <div class="space-y-1">
          <div class="flex items-center justify-between text-xs">
            <span class="text-dc-text">${b.label}</span>
            <span class="text-white font-bold">${b.count} <span class="text-dc-text font-normal">(${b.pct}%)</span></span>
          </div>
          <div class="h-2 bg-dc-surface rounded-full overflow-hidden">
            <div class="${b.color} h-full rounded-full transition-all" style="width: ${b.pct}%"></div>
          </div>
        </div>`;
    });

    if (capacity > 0) {
      html += `
        <div class="mt-3 pt-3 border-t border-dc-border flex items-center justify-between text-xs">
          <span class="text-dc-text">Capacity Fill Rate</span>
          <span class="text-theme font-bold">${fillRate}% <span class="text-dc-text font-normal">(${total}/${capacity})</span></span>
        </div>`;
    }
    html += '</div>';
    container.innerHTML = html;
  }

  function renderMatchAnalytics(mat) {
    const container = $('#analytics-matches-content');
    if (!container) return;

    const byState = mat.by_state || {};
    const avgDuration = mat.avg_duration_minutes || 0;
    const forfeitRate = mat.forfeit_rate || 0;
    const disputeRate = mat.dispute_rate || 0;

    let html = `
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-dc-success">${byState.completed || 0}</div>
          <div class="text-[10px] text-dc-text">Completed</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-theme">${byState.in_progress || 0}</div>
          <div class="text-[10px] text-dc-text">In Progress</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-dc-warning">${byState.scheduled || 0}</div>
          <div class="text-[10px] text-dc-text">Scheduled</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-dc-danger">${byState.forfeited || byState.cancelled || 0}</div>
          <div class="text-[10px] text-dc-text">Forfeited</div>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-3 mt-3">
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-white">${avgDuration}m</div>
          <div class="text-[10px] text-dc-text">Avg Duration</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-dc-warning">${forfeitRate}%</div>
          <div class="text-[10px] text-dc-text">Forfeit Rate</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-dc-danger">${disputeRate}%</div>
          <div class="text-[10px] text-dc-text">Dispute Rate</div>
        </div>
      </div>`;

    container.innerHTML = html;
  }

  function renderTimeline(timeline) {
    const container = $('#analytics-timeline');
    if (!container) return;

    if (!timeline.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No activity yet</p>';
      return;
    }

    let html = '';
    timeline.forEach(ev => {
      const iconMap = { match: 'swords', registration: 'user-plus', dispute: 'scale', announcement: 'megaphone' };
      const icon = iconMap[ev.type] || 'circle';
      const time = ev.timestamp ? new Date(ev.timestamp).toLocaleString() : '';
      html += `
        <div class="flex items-start gap-3 p-2 hover:bg-white/[.02] rounded-lg transition-colors">
          <div class="w-6 h-6 rounded-full bg-theme/10 flex items-center justify-center mt-0.5 shrink-0">
            <i data-lucide="${icon}" class="w-3 h-3 text-theme"></i>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs text-white">${esc(ev.description)}</p>
            <p class="text-[10px] text-dc-text">${time}</p>
          </div>
        </div>`;
    });
    container.innerHTML = html;
    refreshIcons();
  }

  async function exportReport() {
    try {
      const data = await API.get('analytics/export/');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `analytics_${slug}.json`; a.click();
      URL.revokeObjectURL(url);
      toast('Report exported', 'success');
    } catch (e) {
      toast('Export failed', 'error');
    }
  }

  window.TOC = window.TOC || {};
  window.TOC.analytics = { refresh, exportReport };

  // Auto-load when tab is activated
  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail && e.detail.tab === 'analytics') refresh();
  });
})();
