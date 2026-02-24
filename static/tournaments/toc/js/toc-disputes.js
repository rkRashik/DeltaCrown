/**
 * TOC Disputes Module — Sprint 7
 * Dispute queue, detail drawer, resolution, escalation, staff assignment,
 * evidence management, nav badge.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);

  const severityConfig = {
    critical: { label: 'Critical', cls: 'bg-dc-danger text-white', order: 0 },
    high:     { label: 'High',     cls: 'bg-dc-danger/30 text-dc-danger border border-dc-danger/40', order: 1 },
    medium:   { label: 'Medium',   cls: 'bg-dc-warning/20 text-dc-warning border border-dc-warning/30', order: 2 },
    low:      { label: 'Low',      cls: 'bg-dc-text/10 text-dc-text border border-dc-border', order: 3 },
  };

  const statusConfig = {
    open:                    { label: 'Open',        cls: 'bg-dc-danger/20 text-dc-danger border-dc-danger/30' },
    under_review:            { label: 'Reviewing',   cls: 'bg-dc-warning/20 text-dc-warning border-dc-warning/30' },
    escalated:               { label: 'Escalated',   cls: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
    resolved_for_submitter:  { label: 'Resolved',    cls: 'bg-dc-success/20 text-dc-success border-dc-success/30' },
    resolved_for_opponent:   { label: 'Resolved',    cls: 'bg-dc-success/20 text-dc-success border-dc-success/30' },
    cancelled:               { label: 'Cancelled',   cls: 'bg-dc-text/10 text-dc-text border-dc-border' },
  };

  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }

  let allDisputes = [];
  let _debounceTimer = null;

  /* ─── Fetch & render ─────────────────────────────────────── */
  async function refresh() {
    const status = $('#dispute-filter-status')?.value || '';
    const search = $('#dispute-search')?.value || '';
    try {
      const data = await API.get(`/api/toc/${slug}/disputes/` +
        `?status=${status}&search=${encodeURIComponent(search)}`);
      allDisputes = data.disputes || [];
      renderQueue(allDisputes);
      renderCounters(allDisputes, data.open_count);
      updateNavBadge(data.open_count);
    } catch (e) {
      console.error('[disputes] fetch error', e);
    }
  }

  function debouncedRefresh() {
    clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(refresh, 300);
  }

  /* ─── Counters ───────────────────────────────────────────── */
  function renderCounters(disputes, openCount) {
    const el = (id, val) => { const e = $(`#disputes-${id}`); if (e) e.textContent = val; };
    el('open-count', openCount || 0);
    el('review-count', disputes.filter(d => d.status === 'under_review').length);
    el('escalated-count', disputes.filter(d => d.status === 'escalated').length);
  }

  /* ─── S7-F6: Nav badge ──────────────────────────────────── */
  function updateNavBadge(count) {
    const badge = document.querySelector('[data-tab="disputes"] .dispute-badge');
    if (badge) {
      badge.textContent = count;
      badge.classList.toggle('hidden', !count);
    }
    // Also try to add badge dynamically if not present
    const navBtn = document.querySelector('[data-tab="disputes"]');
    if (navBtn && !badge && count > 0) {
      const b = document.createElement('span');
      b.className = 'dispute-badge absolute -top-1 -right-1 w-4 h-4 bg-dc-danger text-white text-[8px] font-bold rounded-full flex items-center justify-center';
      b.textContent = count;
      navBtn.style.position = 'relative';
      navBtn.appendChild(b);
    }
  }

  /* ─── S7-F1: Dispute queue rendering ─────────────────────── */
  function renderQueue(disputes) {
    const container = $('#dispute-queue');
    if (!container) return;

    if (!disputes.length) {
      container.innerHTML = `
        <div class="flex items-center justify-center h-40 text-dc-text text-sm py-12">
          <div class="text-center">
            <i data-lucide="check-circle" class="w-12 h-12 text-dc-success/20 mx-auto mb-3"></i>
            <p>No disputes found</p>
          </div>
        </div>`;
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    // Sort by severity then date
    const sorted = [...disputes].sort((a, b) => {
      const sa = severityConfig[a.severity]?.order ?? 4;
      const sb = severityConfig[b.severity]?.order ?? 4;
      if (sa !== sb) return sa - sb;
      return new Date(b.opened_at) - new Date(a.opened_at);
    });

    container.innerHTML = sorted.map(d => {
      const sev = severityConfig[d.severity] || severityConfig.low;
      const st = statusConfig[d.status] || statusConfig.open;
      const timeAgo = relativeTime(d.opened_at);
      return `
        <div class="p-4 hover:bg-white/[0.02] transition-colors cursor-pointer flex items-start gap-4" onclick="TOC.disputes.openDetail(${d.id})">
          <div class="flex-shrink-0 mt-1">
            <span class="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${sev.cls}">${sev.label}</span>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xs font-bold text-white">Dispute #${d.id}</span>
              <span class="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${st.cls}">${st.label}</span>
              ${d.match_id ? `<span class="text-[9px] text-dc-text font-mono">Match #${d.match_id}</span>` : ''}
            </div>
            <p class="text-[10px] text-dc-text truncate">${d.reason_display}: ${d.description?.substring(0, 120) || ''}${d.description?.length > 120 ? '...' : ''}</p>
            <div class="flex items-center gap-3 mt-1 text-[9px] text-dc-text/60">
              <span>${timeAgo}</span>
              ${d.resolved_by_user_id ? `<span>Assigned: #${d.resolved_by_user_id}</span>` : ''}
            </div>
          </div>
          <div class="flex-shrink-0">
            <i data-lucide="chevron-right" class="w-4 h-4 text-dc-text/30"></i>
          </div>
        </div>`;
    }).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* ─── S7-F2: Dispute detail drawer ──────────────────────── */
  async function openDetail(id) {
    try {
      const d = await API.get(`/api/toc/${slug}/disputes/${id}/`);
      const sev = severityConfig[d.severity] || severityConfig.low;
      const st = statusConfig[d.status] || statusConfig.open;
      const isOpen = ['open', 'under_review', 'escalated'].includes(d.status);

      const html = `
        <div class="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
          <div class="flex items-center justify-between">
            <h3 class="font-display font-black text-lg text-white">Dispute #${d.id}</h3>
            <div class="flex items-center gap-2">
              <span class="text-[8px] font-bold uppercase px-2 py-0.5 rounded-full ${sev.cls}">${sev.label}</span>
              <span class="text-[8px] font-bold uppercase px-2 py-0.5 rounded-full border ${st.cls}">${st.label}</span>
            </div>
          </div>

          <div class="space-y-2 text-[10px]">
            <div class="flex justify-between text-dc-text"><span>Reason</span><span class="text-dc-textBright">${d.reason_display}</span></div>
            <div class="flex justify-between text-dc-text"><span>Match</span><span class="text-dc-textBright font-mono">#${d.match_id || '—'}</span></div>
            <div class="flex justify-between text-dc-text"><span>Opened By</span><span class="text-dc-textBright font-mono">User #${d.opened_by_user_id}</span></div>
            <div class="flex justify-between text-dc-text"><span>Opened</span><span class="text-dc-textBright font-mono">${d.opened_at ? new Date(d.opened_at).toLocaleString() : '—'}</span></div>
            ${d.resolved_at ? `<div class="flex justify-between text-dc-text"><span>Resolved</span><span class="text-dc-textBright font-mono">${new Date(d.resolved_at).toLocaleString()}</span></div>` : ''}
          </div>

          <div class="bg-dc-bg border border-dc-border rounded-lg p-3">
            <p class="text-[9px] font-bold text-dc-text uppercase tracking-widest mb-1">Description</p>
            <p class="text-xs text-dc-textBright leading-relaxed">${d.description || 'No description provided.'}</p>
          </div>

          ${d.resolution_notes ? `
          <div class="bg-dc-bg border border-dc-border rounded-lg p-3">
            <p class="text-[9px] font-bold text-dc-text uppercase tracking-widest mb-1">Resolution Notes</p>
            <p class="text-xs text-dc-textBright leading-relaxed">${d.resolution_notes}</p>
          </div>` : ''}

          ${d.evidence?.length ? `
          <div>
            <p class="text-[9px] font-bold text-dc-text uppercase tracking-widest mb-2">Evidence (${d.evidence.length})</p>
            <div class="space-y-2">
              ${d.evidence.map(e => `
                <a href="${e.url}" target="_blank" class="flex items-center gap-2 bg-dc-bg border border-dc-border rounded-lg p-2 hover:border-dc-borderLight transition-colors">
                  <i data-lucide="${e.evidence_type === 'video' ? 'video' : 'image'}" class="w-4 h-4 text-theme flex-shrink-0"></i>
                  <div class="flex-1 min-w-0">
                    <p class="text-[10px] text-dc-textBright truncate">${e.notes || e.evidence_type}</p>
                    <p class="text-[9px] text-dc-text/60 truncate">${e.url}</p>
                  </div>
                  <i data-lucide="external-link" class="w-3 h-3 text-dc-text/30 flex-shrink-0"></i>
                </a>
              `).join('')}
            </div>
          </div>` : ''}

          ${isOpen ? `
          <div class="border-t border-dc-border pt-4 space-y-3">
            <p class="text-[9px] font-bold text-dc-text uppercase tracking-widest">Actions</p>
            <div class="grid grid-cols-2 gap-2">
              <button onclick="TOC.disputes.openResolveForm(${d.id})" class="py-2.5 bg-dc-success/20 border border-dc-success/30 text-dc-success text-[10px] font-bold uppercase rounded-lg hover:bg-dc-success/30">Resolve</button>
              <button onclick="TOC.disputes.escalate(${d.id})" class="py-2.5 bg-purple-500/20 border border-purple-500/30 text-purple-400 text-[10px] font-bold uppercase rounded-lg hover:bg-purple-500/30">Escalate</button>
            </div>
            <div class="flex gap-2">
              <input id="assign-staff-id" type="number" placeholder="Staff User ID" class="flex-1 bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
              <button onclick="TOC.disputes.assign(${d.id})" class="px-4 py-2 bg-dc-panel border border-dc-border text-dc-textBright text-[10px] font-bold uppercase rounded-lg hover:bg-white/5">Assign</button>
            </div>
          </div>` : ''}
        </div>`;
      showOverlay('dispute-detail-overlay', html);
    } catch (e) {
      toast(e.message || 'Failed to load dispute', 'error');
    }
  }

  /* ─── S7-F3: Resolution form ────────────────────────────── */
  function openResolveForm(id) {
    closeOverlay('dispute-detail-overlay');
    const html = `
      <div class="p-6 space-y-4">
        <h3 class="font-display font-black text-lg text-white">Resolve Dispute #${id}</h3>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Ruling</label>
          <select id="resolve-ruling" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
            <option value="submitter_wins">Submitter Wins</option>
            <option value="opponent_wins">Opponent Wins</option>
            <option value="cancelled">Cancel Dispute</option>
          </select>
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Resolution Notes</label>
          <textarea id="resolve-notes" rows="3" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none" placeholder="Explain your ruling..."></textarea>
        </div>
        <button onclick="TOC.disputes.confirmResolve(${id})" class="w-full py-2.5 bg-dc-success text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Issue Ruling</button>
      </div>`;
    showOverlay('resolve-overlay', html);
  }

  async function confirmResolve(id) {
    try {
      await API.post(`/api/toc/${slug}/disputes/${id}/resolve/`, {
        ruling: $('#resolve-ruling')?.value || 'submitter_wins',
        resolution_notes: $('#resolve-notes')?.value || '',
      });
      toast('Dispute resolved', 'success');
      closeOverlay('resolve-overlay');
      refresh();
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  /* ─── S7-F4: Escalate ───────────────────────────────────── */
  async function escalate(id) {
    const reason = prompt('Escalation reason (optional):');
    if (reason === null) return;
    try {
      await API.post(`/api/toc/${slug}/disputes/${id}/escalate/`, { reason: reason || '' });
      toast('Dispute escalated', 'info');
      closeOverlay('dispute-detail-overlay');
      refresh();
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  /* ─── S7-F5: Staff assignment ───────────────────────────── */
  async function assign(id) {
    const staffId = $('#assign-staff-id')?.value;
    if (!staffId) { toast('Enter staff user ID', 'error'); return; }
    try {
      await API.post(`/api/toc/${slug}/disputes/${id}/assign/`, { staff_user_id: parseInt(staffId) });
      toast('Dispute assigned', 'success');
      closeOverlay('dispute-detail-overlay');
      refresh();
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  /* ─── Helpers ────────────────────────────────────────────── */
  function relativeTime(iso) {
    if (!iso) return '';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  function showOverlay(id, innerHtml) {
    document.getElementById(id)?.remove();
    const modal = document.createElement('div');
    modal.id = id;
    modal.className = 'fixed inset-0 z-[110] flex items-center justify-center';
    modal.innerHTML = `
      <div class="absolute inset-0 bg-black/80 backdrop-blur-md" onclick="TOC.disputes.closeOverlay('${id}')"></div>
      <div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-lg relative z-10 overflow-hidden">
        <div class="h-1 w-full bg-theme"></div>
        ${innerHtml}
      </div>`;
    document.body.appendChild(modal);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function closeOverlay(id) { document.getElementById(id)?.remove(); }

  /* ─── Init ───────────────────────────────────────────────── */
  function init() { refresh(); }

  window.TOC = window.TOC || {};
  window.TOC.disputes = {
    init, refresh, debouncedRefresh,
    openDetail, openResolveForm, confirmResolve,
    escalate, assign,
    closeOverlay,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'disputes') init();
  });
})();
