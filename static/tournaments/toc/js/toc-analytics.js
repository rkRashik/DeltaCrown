/**
 * TOC Analytics Module — Sprint 29 (full redesign)
 *
 * Features:
 * - Registration funnel with trend sparkline
 * - Match analytics with round-by-round progress bars
 * - Revenue breakdown and profit margin
 * - Engagement metrics (stream coverage, views)
 * - Closest matches leaderboard
 * - Activity timeline with better icons and formatting
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);
  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }
  function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
  function refreshIcons() { if (typeof lucide !== 'undefined') lucide.createIcons(); }

  let dashData = null;

  /* ─────────────────────────── Data fetch ─────────────────────────── */

  async function refresh() {
    try {
      const data = await API.get('analytics/');
      dashData = data;
      renderOverviewStats(data);
      renderRegFunnel(data.registration || {});
      renderMatchAnalytics(data.matches || {});
      renderRoundsProgress(data.matches || {});
      renderRevenue(data.revenue || {});
      renderEngagement(data.engagement || {});
      renderClosestMatches(data.matches || {});
      renderTimeline(data.timeline || []);
    } catch (e) {
      console.error('[analytics] fetch error', e);
    }
  }

  /* ─────────────────── Overview stat cards ─────────────────────────── */

  function renderOverviewStats(data) {
    const reg = data.registration || {};
    const mat = data.matches || {};
    const rev = data.revenue || {};
    const el = (id, v) => { const e = $(`#analytics-stat-${id}`); if (e) e.textContent = v; };
    el('participants', reg.total || 0);
    el('matches', mat.total || 0);
    el('revenue', rev.net_revenue != null ? `$${rev.net_revenue.toLocaleString()}` : '$0');
    const completionPct = mat.total > 0 ? Math.round((mat.completed || 0) / mat.total * 100) : 0;
    el('completion', completionPct + '%');
  }

  /* ────────────────── Registration funnel ──────────────────────────── */

  function renderRegFunnel(reg) {
    const container = $('#analytics-reg-funnel');
    if (!container) return;

    const total = reg.total || 0;
    const approved = reg.approved || 0;
    const pending = reg.pending || 0;
    const rejected = reg.rejected || 0;
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
            <div class="${b.color} h-full rounded-full transition-all duration-500" style="width: ${b.pct}%"></div>
          </div>
        </div>`;
    });

    if (capacity > 0) {
      html += `
        <div class="mt-3 pt-3 border-t border-dc-border/30 flex items-center justify-between text-xs">
          <span class="text-dc-text">Capacity Fill Rate</span>
          <span class="text-theme font-bold">${fillRate}% <span class="text-dc-text font-normal">(${total}/${capacity})</span></span>
        </div>`;
    }

    // Trend sparkline (simple CSS bar chart)
    const trend = reg.trend || [];
    if (trend.length > 1) {
      const maxCount = Math.max(...trend.map(t => t.count), 1);
      html += `<div class="mt-4 pt-3 border-t border-dc-border/30">
        <p class="text-[10px] text-dc-text uppercase tracking-wide mb-2">Registration Trend</p>
        <div class="flex items-end gap-[2px] h-10">`;
      trend.forEach(t => {
        const h = Math.max(2, Math.round(t.count / maxCount * 100));
        html += `<div class="flex-1 bg-theme/40 rounded-t hover:bg-theme/70 transition-colors" style="height:${h}%" title="${t.date}: ${t.count}"></div>`;
      });
      html += `</div>
        <div class="flex justify-between mt-1">
          <span class="text-[9px] text-dc-text opacity-50">${trend[0]?.date || ''}</span>
          <span class="text-[9px] text-dc-text opacity-50">${trend[trend.length - 1]?.date || ''}</span>
        </div>
      </div>`;
    }

    html += '</div>';
    container.innerHTML = html;
  }

  /* ────────────────── Match analytics ──────────────────────────────── */

  function renderMatchAnalytics(mat) {
    const container = $('#analytics-matches-content');
    if (!container) return;

    const byState = mat.by_state || {};
    const avgDuration = mat.avg_duration_minutes || 0;
    const forfeitRate = mat.forfeit_rate || 0;
    const disputeRate = mat.dispute_rate || 0;

    container.innerHTML = `
      <div class="grid grid-cols-2 gap-2">
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-dc-success">${byState.completed || 0}</div>
          <div class="text-[10px] text-dc-text">Completed</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-theme">${byState.in_progress || byState.live || 0}</div>
          <div class="text-[10px] text-dc-text">In Progress</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-dc-warning">${byState.scheduled || 0}</div>
          <div class="text-[10px] text-dc-text">Scheduled</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-dc-danger">${byState.forfeited || byState.forfeit || 0}</div>
          <div class="text-[10px] text-dc-text">Forfeited</div>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-2 mt-3">
        <div class="bg-dc-surface/50 rounded-lg p-2.5 text-center">
          <div class="text-sm font-bold text-white">${avgDuration}m</div>
          <div class="text-[9px] text-dc-text">Avg Duration</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-2.5 text-center">
          <div class="text-sm font-bold text-dc-warning">${forfeitRate}%</div>
          <div class="text-[9px] text-dc-text">Forfeit Rate</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-2.5 text-center">
          <div class="text-sm font-bold text-dc-danger">${disputeRate}%</div>
          <div class="text-[9px] text-dc-text">Dispute Rate</div>
        </div>
      </div>`;
  }

  /* ────────────────── Round-by-round progress ─────────────────────── */

  function renderRoundsProgress(mat) {
    const container = $('#analytics-rounds-progress');
    if (!container) return;

    const rounds = mat.rounds || [];
    if (!rounds.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No rounds data</p>';
      return;
    }

    let html = '<div class="space-y-2">';
    rounds.forEach(r => {
      const pct = r.pct || 0;
      const color = pct >= 100 ? 'bg-dc-success' : pct >= 50 ? 'bg-theme' : 'bg-dc-warning';
      html += `
        <div class="space-y-0.5">
          <div class="flex items-center justify-between text-[11px]">
            <span class="text-dc-text">Round ${r.round}</span>
            <span class="text-white font-medium">${r.completed}/${r.total} <span class="text-dc-text font-normal">(${pct}%)</span></span>
          </div>
          <div class="h-1.5 bg-dc-surface rounded-full overflow-hidden">
            <div class="${color} h-full rounded-full transition-all duration-500" style="width:${pct}%"></div>
          </div>
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
  }

  /* ────────────────── Revenue ─────────────────────────────────────── */

  function renderRevenue(rev) {
    const container = $('#analytics-revenue-content');
    if (!container) return;

    const currency = rev.currency || 'USD';
    const fmt = (v) => `${currency === 'USD' ? '$' : currency + ' '}${(v || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 2})}`;

    container.innerHTML = `
      <div class="grid grid-cols-2 gap-2">
        <div class="bg-dc-surface/50 rounded-lg p-3">
          <div class="text-[10px] text-dc-text mb-0.5">Total Revenue</div>
          <div class="text-sm font-bold text-dc-success">${fmt(rev.total_revenue)}</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3">
          <div class="text-[10px] text-dc-text mb-0.5">Net Revenue</div>
          <div class="text-sm font-bold text-white">${fmt(rev.net_revenue)}</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3">
          <div class="text-[10px] text-dc-text mb-0.5">Refunds</div>
          <div class="text-sm font-bold text-dc-danger">${fmt(rev.refund_amount)} <span class="text-[10px] font-normal text-dc-text">(${rev.refund_count || 0})</span></div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3">
          <div class="text-[10px] text-dc-text mb-0.5">Prize Pool</div>
          <div class="text-sm font-bold text-theme">${fmt(rev.prize_pool)}</div>
        </div>
      </div>
      <div class="flex items-center justify-between mt-3 pt-3 border-t border-dc-border/30">
        <div class="text-[11px] text-dc-text">Entry Fee: <span class="text-white font-medium">${fmt(rev.entry_fee)}</span></div>
        <div class="text-[11px] text-dc-text">Margin: <span class="font-medium ${(rev.profit_margin || 0) >= 0 ? 'text-dc-success' : 'text-dc-danger'}">${rev.profit_margin || 0}%</span></div>
      </div>`;
  }

  /* ────────────────── Engagement ──────────────────────────────────── */

  function renderEngagement(eng) {
    const container = $('#analytics-engagement-content');
    if (!container) return;

    container.innerHTML = `
      <div class="grid grid-cols-2 gap-2">
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-theme">${eng.streamed_matches || 0}</div>
          <div class="text-[10px] text-dc-text">Streamed</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-white">${eng.stream_coverage || 0}%</div>
          <div class="text-[10px] text-dc-text">Coverage</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-white">${(eng.page_views || 0).toLocaleString()}</div>
          <div class="text-[10px] text-dc-text">Page Views</div>
        </div>
        <div class="bg-dc-surface/50 rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-white">${(eng.unique_visitors || 0).toLocaleString()}</div>
          <div class="text-[10px] text-dc-text">Unique Visitors</div>
        </div>
      </div>`;
  }

  /* ────────────────── Closest matches ────────────────────────────── */

  function renderClosestMatches(mat) {
    const container = $('#analytics-closest-matches');
    if (!container) return;

    const matches = mat.closest_matches || [];
    if (!matches.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No completed matches yet</p>';
      return;
    }

    const rows = matches.map((m, i) => `
      <div class="flex items-center gap-3 p-2 ${i % 2 === 0 ? 'bg-dc-surface/30' : ''} rounded-lg">
        <span class="text-[10px] text-dc-text opacity-60 w-6 shrink-0 text-center">#${m.match_number || m.match_id}</span>
        <span class="text-xs text-white flex-1 truncate">${esc(m.p1)}</span>
        <span class="text-xs font-mono font-bold text-theme px-2">${esc(m.score)}</span>
        <span class="text-xs text-white flex-1 truncate text-right">${esc(m.p2)}</span>
        <span class="text-[9px] px-1.5 py-0.5 rounded ${m.diff === 0 ? 'bg-dc-danger/20 text-dc-danger' : m.diff <= 1 ? 'bg-orange-500/20 text-orange-400' : 'bg-dc-surface/50 text-dc-text'}">${m.diff === 0 ? 'TIE' : `Δ${m.diff}`}</span>
      </div>`).join('');

    container.innerHTML = `<div class="space-y-0.5">${rows}</div>`;
  }

  /* ────────────────── Activity timeline ───────────────────────────── */

  function renderTimeline(timeline) {
    const container = $('#analytics-timeline');
    if (!container) return;

    if (!timeline.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No activity yet</p>';
      return;
    }

    const iconMap = {
      match: 'swords',
      registration: 'user-plus',
      dispute: 'scale',
      announcement: 'megaphone',
      checkin: 'user-check',
    };
    const colorMap = {
      match: 'text-dc-success bg-dc-success/10',
      registration: 'text-theme bg-theme/10',
      dispute: 'text-dc-danger bg-dc-danger/10',
      announcement: 'text-dc-warning bg-dc-warning/10',
      checkin: 'text-blue-400 bg-blue-400/10',
    };

    container.innerHTML = timeline.map(ev => {
      const icon = iconMap[ev.type] || 'circle';
      const colors = colorMap[ev.type] || 'text-dc-text bg-dc-surface/50';
      const time = ev.timestamp ? new Date(ev.timestamp).toLocaleString() : '';
      return `
        <div class="flex items-start gap-3 p-2 hover:bg-white/[.02] rounded-lg transition-colors">
          <div class="w-7 h-7 rounded-lg ${colors} flex items-center justify-center mt-0.5 shrink-0">
            <i data-lucide="${icon}" class="w-3.5 h-3.5"></i>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs text-white leading-snug">${esc(ev.title || ev.description)}</p>
            ${ev.detail ? `<p class="text-[10px] text-dc-text mt-0.5">${esc(ev.detail)}</p>` : ''}
            <p class="text-[9px] text-dc-text opacity-50 mt-0.5">${time}</p>
          </div>
        </div>`;
    }).join('');
    refreshIcons();
  }

  /* ────────────────── Export ──────────────────────────────────────── */

  async function exportReport() {
    try {
      const data = await API.get('analytics/export/');

      // Build CSV from report data
      const rows = [
        ['Tournament Report', data.tournament || ''],
        ['Generated', data.generated_at || ''],
        [],
        ['── Registration Summary ──'],
        ['Total Registrations', data.registration?.total_registrations ?? ''],
        ['Confirmed', data.registration?.confirmed ?? ''],
        ['Pending', data.registration?.pending ?? ''],
        ['Rejected', data.registration?.rejected ?? ''],
        ['Waitlisted', data.registration?.waitlisted ?? ''],
        [],
        ['── Match Summary ──'],
        ['Total Matches', data.matches?.total ?? ''],
        ['Completed', data.matches?.completed ?? ''],
        ['Forfeited', data.matches?.forfeited ?? ''],
        ['Pending', data.matches?.pending ?? ''],
        ['Disputed', data.matches?.disputed ?? ''],
        [],
        ['── Revenue Summary ──'],
        ['Total Entries', data.revenue?.total_entries ?? ''],
        ['Gross Revenue', data.revenue?.gross_revenue ?? ''],
        ['Prize Pool', data.revenue?.prize_pool ?? ''],
      ];

      const csv = rows.map(r => r.map(cell => {
        const s = String(cell ?? '');
        return s.includes(',') || s.includes('"') || s.includes('\n')
          ? `"${s.replace(/"/g, '""')}"` : s;
      }).join(',')).join('\r\n');

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics_${slug}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast('Report exported as CSV', 'success');
    } catch (e) {
      toast('Export failed', 'error');
    }
  }

  /* ────────────────── Public API ──────────────────────────────────── */

  window.TOC = window.TOC || {};
  window.TOC.analytics = { refresh, exportReport };

  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail?.tab === 'analytics') refresh();
  });
})();
