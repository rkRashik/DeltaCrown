/**
 * TOC — Participants Tab (toc-participants.js)
 *
 * Sprint 2: S2-F1 through S2-F9
 * PRD: §3.1–§3.9
 *
 * Dense data grid with filtering, sorting, pagination,
 * inline actions, bulk operations, detail drawer, and CSV export.
 */
;(function () {
  'use strict';

  const $ = (s, c) => (c || document).querySelector(s);
  const $$ = (s, c) => [...(c || document).querySelectorAll(s)];

  /* ── State ─────────────────────────────────────────────────────── */
  let currentPage = 1;
  let currentData = null;     // latest API response
  let selectedIds = new Set();
  let currentOrdering = '-registered_at';
  let debounceTimer = null;

  /* ── Status → badge config ─────────────────────────────────────── */
  const STATUS_CONFIG = {
    confirmed:          { bg: 'bg-dc-success/10', border: 'border-dc-success/20', text: 'text-dc-success',  label: 'Confirmed' },
    auto_approved:      { bg: 'bg-dc-success/10', border: 'border-dc-success/20', text: 'text-dc-success',  label: 'Auto-Approved' },
    pending:            { bg: 'bg-dc-warning/10', border: 'border-dc-warning/20', text: 'text-dc-warning',  label: 'Pending' },
    submitted:          { bg: 'bg-dc-info/10',    border: 'border-dc-info/20',    text: 'text-dc-info',     label: 'Submitted' },
    needs_review:       { bg: 'bg-dc-warning/10', border: 'border-dc-warning/20', text: 'text-dc-warning',  label: 'Review' },
    payment_submitted:  { bg: 'bg-dc-info/10',    border: 'border-dc-info/20',    text: 'text-dc-info',     label: 'Pay Submitted' },
    waitlisted:         { bg: 'bg-purple-500/10',  border: 'border-purple-500/20', text: 'text-purple-400',  label: 'Waitlisted' },
    rejected:           { bg: 'bg-dc-danger/10',  border: 'border-dc-danger/20',  text: 'text-dc-danger',   label: 'Rejected' },
    cancelled:          { bg: 'bg-dc-text/10',    border: 'border-dc-text/20',    text: 'text-dc-text',     label: 'Cancelled' },
    no_show:            { bg: 'bg-dc-danger/10',  border: 'border-dc-danger/20',  text: 'text-dc-danger',   label: 'No-Show' },
    draft:              { bg: 'bg-dc-text/10',    border: 'border-dc-text/20',    text: 'text-dc-text',     label: 'Draft' },
  };

  const PAYMENT_CONFIG = {
    Verified: { bg: 'bg-dc-success/10', border: 'border-dc-success/20', text: 'text-dc-success' },
    Pending:  { bg: 'bg-dc-warning/10', border: 'border-dc-warning/20', text: 'text-dc-warning' },
    Rejected: { bg: 'bg-dc-danger/10',  border: 'border-dc-danger/20',  text: 'text-dc-danger'  },
    None:     { bg: 'bg-dc-text/5',     border: 'border-dc-text/10',    text: 'text-dc-text/50' },
  };

  /* ── Load ───────────────────────────────────────────────────────── */

  async function load() {
    const params = new URLSearchParams();
    params.set('page', currentPage);
    params.set('ordering', currentOrdering);

    const status = $('#filter-status')?.value;
    const payment = $('#filter-payment')?.value;
    const checkin = $('#filter-checkin')?.value;
    const search = $('#filter-search')?.value?.trim();

    if (status) params.set('status', status);
    if (payment) params.set('payment', payment);
    if (checkin) params.set('checkin', checkin);
    if (search) params.set('search', search);

    try {
      const data = await TOC.fetch(`${TOC.config.apiBase}/participants/?${params}`);
      currentData = data;
      render(data);
      updateBadge(data.total);
    } catch (err) {
      console.error('[TOC.participants] load error:', err);
      const tbody = $('#participants-tbody');
      if (tbody) {
        tbody.innerHTML = `
          <tr><td colspan="8" class="px-6 py-12 text-center">
            <p class="text-dc-danger text-sm">Failed to load participants.</p>
            <button onclick="TOC.participants.load()" class="mt-3 text-theme text-xs underline">Retry</button>
          </td></tr>`;
      }
    }
  }

  /* ── Render Grid ────────────────────────────────────────────────── */

  function render(data) {
    renderRows(data.results);
    renderPagination(data);
    selectedIds.clear();
    updateBulkBar();
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function renderRows(rows) {
    const tbody = $('#participants-tbody');
    if (!tbody) return;

    if (!rows || rows.length === 0) {
      tbody.innerHTML = `
        <tr><td colspan="8" class="px-6 py-16 text-center">
          <div class="flex flex-col items-center gap-3">
            <i data-lucide="inbox" class="w-10 h-10 text-dc-text/30"></i>
            <p class="text-dc-text text-sm">No participants found.</p>
            <p class="text-dc-text/50 text-xs">Adjust filters or wait for registrations.</p>
          </div>
        </td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map(row => {
      const sc = STATUS_CONFIG[row.status] || STATUS_CONFIG.draft;
      const pc = PAYMENT_CONFIG[row.payment_status] || PAYMENT_CONFIG.None;
      const checked = selectedIds.has(row.id) ? 'checked' : '';

      return `
        <tr class="border-b border-dc-border/30 hover:bg-white/[0.02] transition-colors cursor-pointer group"
            data-reg-id="${row.id}">
          <td class="px-3 py-2.5" onclick="event.stopPropagation()">
            <input type="checkbox" class="toc-checkbox row-select" value="${row.id}" ${checked}
                   onchange="TOC.participants.toggleSelect(${row.id}, this.checked)">
          </td>
          <td class="px-3 py-2.5" onclick="TOC.participants.openDetail(${row.id})">
            <div class="flex items-center gap-2.5">
              <div class="w-7 h-7 rounded-lg bg-theme-surface border border-theme-border flex items-center justify-center flex-shrink-0">
                <span class="text-[10px] font-bold text-theme">${(row.participant_name || '?')[0].toUpperCase()}</span>
              </div>
              <div class="min-w-0">
                <p class="text-white text-xs font-semibold truncate max-w-[180px]">${esc(row.participant_name)}</p>
                <p class="text-dc-text text-[10px] font-mono truncate">${esc(row.registration_number || row.username || '')}</p>
              </div>
              ${row.is_guest_team ? '<span class="px-1.5 py-0.5 bg-purple-500/10 border border-purple-500/20 text-purple-400 text-[8px] font-bold uppercase tracking-widest rounded">Guest</span>' : ''}
            </div>
          </td>
          <td class="px-3 py-2.5" onclick="TOC.participants.openDetail(${row.id})">
            <span class="inline-flex px-2 py-0.5 ${sc.bg} border ${sc.border} ${sc.text} text-[9px] font-bold uppercase tracking-widest rounded-md">
              ${esc(sc.label)}
            </span>
          </td>
          <td class="px-3 py-2.5" onclick="TOC.participants.openDetail(${row.id})">
            <span class="inline-flex px-2 py-0.5 ${pc.bg} border ${pc.border} ${pc.text} text-[9px] font-bold uppercase tracking-widest rounded-md">
              ${esc(row.payment_status)}
            </span>
          </td>
          <td class="px-3 py-2.5 text-center" onclick="event.stopPropagation()">
            <button onclick="TOC.participants.toggleCheckin(${row.id})"
                    class="w-8 h-5 rounded-full border transition-all relative ${
                      row.checked_in
                        ? 'bg-dc-success/20 border-dc-success/40'
                        : 'bg-dc-panel border-dc-border'
                    }">
              <span class="absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all ${
                row.checked_in
                  ? 'left-[14px] bg-dc-success shadow-[0_0_6px_rgba(0,255,102,0.4)]'
                  : 'left-0.5 bg-dc-text/50'
              }"></span>
            </button>
          </td>
          <td class="px-3 py-2.5 text-center font-mono text-dc-textBright text-xs" onclick="TOC.participants.openDetail(${row.id})">
            ${row.seed != null ? row.seed : '<span class="text-dc-text/30">—</span>'}
          </td>
          <td class="px-3 py-2.5 font-mono text-dc-text text-[10px]" onclick="TOC.participants.openDetail(${row.id})">
            ${esc(row.game_id || '—')}
          </td>
          <td class="px-3 py-2.5 text-right" onclick="event.stopPropagation()">
            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              ${actionButton(row, 'approve', 'check', 'dc-success', 'Approve')}
              ${actionButton(row, 'reject', 'x', 'dc-danger', 'Reject')}
              ${actionButton(row, 'dq', 'shield-off', 'dc-warning', 'DQ')}
              ${actionButton(row, 'verify', 'badge-check', 'dc-info', 'Verify Pay')}
            </div>
          </td>
        </tr>`;
    }).join('');
  }

  function actionButton(row, action, icon, color, title) {
    // Show contextual buttons based on status
    const showApprove = ['pending', 'needs_review', 'submitted'].includes(row.status);
    const showReject = ['pending', 'needs_review', 'submitted', 'payment_submitted'].includes(row.status);
    const showDQ = row.status === 'confirmed';
    const showVerify = row.payment_status === 'Pending';

    if (action === 'approve' && !showApprove) return '';
    if (action === 'reject' && !showReject) return '';
    if (action === 'dq' && !showDQ) return '';
    if (action === 'verify' && !showVerify) return '';

    return `<button onclick="TOC.participants.rowAction('${action}', ${row.id})"
              title="${title}"
              class="w-7 h-7 rounded-lg border border-${color}/20 bg-${color}/5 hover:bg-${color}/15 flex items-center justify-center transition-colors">
              <i data-lucide="${icon}" class="w-3 h-3 text-${color}"></i>
            </button>`;
  }

  /* ── Pagination ─────────────────────────────────────────────────── */

  function renderPagination(data) {
    const info = $('#pagination-info');
    const controls = $('#pagination-controls');
    if (!info || !controls) return;

    const start = (data.page - 1) * data.page_size + 1;
    const end = Math.min(data.page * data.page_size, data.total);
    info.textContent = data.total > 0
      ? `${start}–${end} of ${data.total}`
      : 'No results';

    if (data.pages <= 1) {
      controls.innerHTML = '';
      return;
    }

    let html = '';
    // Prev
    html += `<button ${data.page <= 1 ? 'disabled' : ''} onclick="TOC.participants.goPage(${data.page - 1})"
              class="w-7 h-7 rounded border border-dc-border text-dc-text hover:text-white hover:border-dc-borderLight disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center transition-colors text-xs">
              <i data-lucide="chevron-left" class="w-3 h-3"></i></button>`;

    // Page numbers (show up to 7: first ... middle ... last)
    const pages = buildPageNumbers(data.page, data.pages);
    for (const p of pages) {
      if (p === '...') {
        html += `<span class="px-1 text-dc-text/40 text-[10px]">…</span>`;
      } else {
        const active = p === data.page;
        html += `<button onclick="TOC.participants.goPage(${p})"
                  class="w-7 h-7 rounded border text-[10px] font-bold flex items-center justify-center transition-colors
                    ${active
                      ? 'border-theme bg-theme/10 text-theme'
                      : 'border-dc-border text-dc-text hover:text-white hover:border-dc-borderLight'
                    }">${p}</button>`;
      }
    }

    // Next
    html += `<button ${data.page >= data.pages ? 'disabled' : ''} onclick="TOC.participants.goPage(${data.page + 1})"
              class="w-7 h-7 rounded border border-dc-border text-dc-text hover:text-white hover:border-dc-borderLight disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center transition-colors text-xs">
              <i data-lucide="chevron-right" class="w-3 h-3"></i></button>`;

    controls.innerHTML = html;
  }

  function buildPageNumbers(current, total) {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages = [];
    pages.push(1);
    if (current > 3) pages.push('...');
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
      pages.push(i);
    }
    if (current < total - 2) pages.push('...');
    pages.push(total);
    return pages;
  }

  /* ── Selection & Bulk ───────────────────────────────────────────── */

  function toggleSelect(id, checked) {
    if (checked) selectedIds.add(id);
    else selectedIds.delete(id);
    updateBulkBar();
  }

  function toggleSelectAll(checkbox) {
    const rows = $$('.row-select');
    if (checkbox.checked) {
      rows.forEach(r => { r.checked = true; selectedIds.add(parseInt(r.value)); });
    } else {
      rows.forEach(r => { r.checked = false; });
      selectedIds.clear();
    }
    updateBulkBar();
  }

  function updateBulkBar() {
    const bar = $('#bulk-action-bar');
    const count = $('#bulk-count');
    if (!bar) return;

    if (selectedIds.size > 0) {
      bar.classList.remove('hidden');
      bar.classList.add('flex');
      if (count) count.textContent = `${selectedIds.size} selected`;
    } else {
      bar.classList.add('hidden');
      bar.classList.remove('flex');
    }
  }

  async function bulkAction(action) {
    if (selectedIds.size === 0) return;
    const ids = [...selectedIds];

    let reason = '';
    if (action === 'reject' || action === 'disqualify') {
      reason = prompt(`Reason for ${action}?`) || '';
    }

    try {
      const result = await TOC.fetch(`${TOC.config.apiBase}/participants/bulk-action/`, {
        method: 'POST',
        body: JSON.stringify({ action, ids, reason }),
      });
      TOC.toast(`${result.processed}/${result.total_requested} ${action}d successfully.`, 'success');
      if (result.errors && result.errors.length > 0) {
        TOC.toast(`${result.errors.length} failed — check console.`, 'warning');
        console.warn('[TOC.participants] Bulk errors:', result.errors);
      }
      selectedIds.clear();
      load();
    } catch (err) {
      TOC.toast(`Bulk ${action} failed: ${err.message || err}`, 'error');
    }
  }

  /* ── Inline Row Actions ─────────────────────────────────────────── */

  async function rowAction(action, id) {
    let endpoint = '';
    let body = {};

    switch (action) {
      case 'approve':
        endpoint = `${TOC.config.apiBase}/participants/${id}/approve/`;
        break;
      case 'reject': {
        const reason = prompt('Rejection reason (optional):') || '';
        endpoint = `${TOC.config.apiBase}/participants/${id}/reject/`;
        body = { reason };
        break;
      }
      case 'dq': {
        const reason = prompt('DQ reason:') || '';
        endpoint = `${TOC.config.apiBase}/participants/${id}/disqualify/`;
        body = { reason };
        break;
      }
      case 'verify':
        endpoint = `${TOC.config.apiBase}/participants/${id}/verify-payment/`;
        break;
      default:
        return;
    }

    try {
      const result = await TOC.fetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(body),
      });
      if (result.ok) {
        TOC.toast(result.message || 'Action completed.', 'success');
        // Update row in-place
        if (result.participant && currentData) {
          const idx = currentData.results.findIndex(r => r.id === id);
          if (idx !== -1) {
            currentData.results[idx] = result.participant;
            renderRows(currentData.results);
            if (typeof lucide !== 'undefined') lucide.createIcons();
          } else {
            load();
          }
        } else {
          load();
        }
      } else {
        TOC.toast(result.error || 'Action failed.', 'error');
      }
    } catch (err) {
      TOC.toast(`Action failed: ${err.message || err}`, 'error');
    }
  }

  /* ── S2-F7: Check-in Toggle ─────────────────────────────────────── */

  async function toggleCheckin(id) {
    try {
      const result = await TOC.fetch(`${TOC.config.apiBase}/participants/${id}/toggle-checkin/`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (result.ok) {
        const state = result.participant?.checked_in ? 'checked in' : 'checked out';
        TOC.toast(`Participant ${state}.`, 'success');
        if (result.participant && currentData) {
          const idx = currentData.results.findIndex(r => r.id === id);
          if (idx !== -1) {
            currentData.results[idx] = result.participant;
            renderRows(currentData.results);
            if (typeof lucide !== 'undefined') lucide.createIcons();
          } else {
            load();
          }
        }
      } else {
        TOC.toast(result.error || 'Check-in toggle failed.', 'error');
      }
    } catch (err) {
      TOC.toast(`Check-in failed: ${err.message || err}`, 'error');
    }
  }

  /* ── S2-F5: Participant Detail Drawer ───────────────────────────── */

  async function openDetail(id) {
    // Show loading drawer immediately
    TOC.drawer.open('Loading...', '<div class="flex items-center justify-center h-40"><div class="w-5 h-5 border-2 border-theme border-t-transparent rounded-full animate-spin"></div></div>');

    try {
      const d = await TOC.fetch(`${TOC.config.apiBase}/participants/${id}/`);
      const sc = STATUS_CONFIG[d.status] || STATUS_CONFIG.draft;

      let paymentHtml = '';
      if (d.payment) {
        const ppc = PAYMENT_CONFIG[d.payment.status_display] || PAYMENT_CONFIG.None;
        paymentHtml = `
          <div class="mt-5">
            <h4 class="text-[9px] font-bold text-dc-text uppercase tracking-widest mb-3">Payment</h4>
            <div class="bg-dc-panel border border-dc-border rounded-lg p-3 space-y-2 text-xs">
              <div class="flex justify-between"><span class="text-dc-text">Status</span><span class="${ppc.text} font-bold">${esc(d.payment.status_display)}</span></div>
              ${d.payment.method ? `<div class="flex justify-between"><span class="text-dc-text">Method</span><span class="text-dc-textBright">${esc(d.payment.method)}</span></div>` : ''}
              ${d.payment.amount_bdt ? `<div class="flex justify-between"><span class="text-dc-text">Amount</span><span class="text-dc-textBright font-mono">৳${esc(d.payment.amount_bdt)}</span></div>` : ''}
              ${d.payment.transaction_id ? `<div class="flex justify-between"><span class="text-dc-text">Transaction</span><span class="text-dc-textBright font-mono text-[10px]">${esc(d.payment.transaction_id)}</span></div>` : ''}
              ${d.payment.verified_by ? `<div class="flex justify-between"><span class="text-dc-text">Verified By</span><span class="text-dc-textBright">${esc(d.payment.verified_by)}</span></div>` : ''}
              ${d.payment.reject_reason ? `<div class="flex justify-between"><span class="text-dc-text">Reject Reason</span><span class="text-dc-danger">${esc(d.payment.reject_reason)}</span></div>` : ''}
              ${d.payment.proof_image ? `<a href="${d.payment.proof_image}" target="_blank" class="text-theme text-[10px] underline">View Payment Proof →</a>` : ''}
            </div>
          </div>`;
      }

      let lineupHtml = '';
      if (d.lineup_snapshot && d.lineup_snapshot.length > 0) {
        lineupHtml = `
          <div class="mt-5">
            <h4 class="text-[9px] font-bold text-dc-text uppercase tracking-widest mb-3">Roster (${d.lineup_snapshot.length})</h4>
            <div class="bg-dc-panel border border-dc-border rounded-lg divide-y divide-dc-border/50">
              ${d.lineup_snapshot.map(p => `
                <div class="px-3 py-2 flex items-center gap-2 text-xs">
                  <span class="text-dc-textBright font-medium">${esc(p.username || p.game_id || 'Unknown')}</span>
                  ${p.role ? `<span class="text-dc-text text-[10px]">${esc(p.role)}</span>` : ''}
                  ${p.game_id ? `<span class="text-dc-text font-mono text-[10px] ml-auto">${esc(p.game_id)}</span>` : ''}
                </div>
              `).join('')}
            </div>
          </div>`;
      }

      const html = `
        <div class="space-y-5">
          {# Header #}
          <div class="flex items-center gap-3 mb-4">
            <div class="w-12 h-12 rounded-xl bg-theme-surface border border-theme-border flex items-center justify-center flex-shrink-0">
              <span class="text-lg font-bold text-theme">${(d.participant_name || '?')[0].toUpperCase()}</span>
            </div>
            <div>
              <h3 class="text-white font-bold text-base">${esc(d.participant_name)}</h3>
              <p class="text-dc-text text-[10px] font-mono">${esc(d.registration_number || '')}</p>
            </div>
          </div>

          {# Status + Meta #}
          <div class="bg-dc-panel border border-dc-border rounded-lg p-3 space-y-2 text-xs">
            <div class="flex justify-between"><span class="text-dc-text">Status</span>
              <span class="inline-flex px-2 py-0.5 ${sc.bg} border ${sc.border} ${sc.text} text-[9px] font-bold uppercase tracking-widest rounded-md">${esc(sc.label)}</span>
            </div>
            ${d.username ? `<div class="flex justify-between"><span class="text-dc-text">Username</span><span class="text-dc-textBright">@${esc(d.username)}</span></div>` : ''}
            ${d.team_id ? `<div class="flex justify-between"><span class="text-dc-text">Team ID</span><span class="text-dc-textBright font-mono">${d.team_id}</span></div>` : ''}
            <div class="flex justify-between"><span class="text-dc-text">Checked In</span><span class="${d.checked_in ? 'text-dc-success' : 'text-dc-text/50'}">${d.checked_in ? 'Yes' : 'No'}</span></div>
            ${d.checked_in_at ? `<div class="flex justify-between"><span class="text-dc-text">Checked In At</span><span class="text-dc-textBright font-mono text-[10px]">${formatDate(d.checked_in_at)}</span></div>` : ''}
            ${d.seed != null ? `<div class="flex justify-between"><span class="text-dc-text">Seed</span><span class="text-dc-textBright font-mono">#${d.seed}</span></div>` : ''}
            ${d.slot_number != null ? `<div class="flex justify-between"><span class="text-dc-text">Slot</span><span class="text-dc-textBright font-mono">${d.slot_number}</span></div>` : ''}
            ${d.waitlist_position != null ? `<div class="flex justify-between"><span class="text-dc-text">Waitlist</span><span class="text-dc-textBright font-mono">#${d.waitlist_position}</span></div>` : ''}
            ${d.is_guest_team ? '<div class="flex justify-between"><span class="text-dc-text">Guest Team</span><span class="text-purple-400 font-bold">Yes</span></div>' : ''}
            <div class="flex justify-between"><span class="text-dc-text">Registered</span><span class="text-dc-textBright font-mono text-[10px]">${formatDate(d.registered_at)}</span></div>
          </div>

          ${paymentHtml}
          ${lineupHtml}

          {# Registration Data (expandable) #}
          ${Object.keys(d.registration_data || {}).length > 0 ? `
          <div class="mt-5">
            <details class="group">
              <summary class="text-[9px] font-bold text-dc-text uppercase tracking-widest cursor-pointer hover:text-white transition-colors">
                Registration Data ▸
              </summary>
              <div class="mt-2 bg-dc-panel border border-dc-border rounded-lg p-3">
                <pre class="text-[10px] text-dc-text font-mono whitespace-pre-wrap break-all">${esc(JSON.stringify(d.registration_data, null, 2))}</pre>
              </div>
            </details>
          </div>` : ''}

          {# Timestamps #}
          <div class="mt-5 pt-4 border-t border-dc-border/50 text-[10px] text-dc-text/50 space-y-1">
            <p>Created: ${formatDate(d.created_at)}</p>
            <p>Updated: ${formatDate(d.updated_at)}</p>
          </div>
        </div>`;

      // Footer with action buttons
      const footerHtml = `
        <div class="flex gap-2">
          ${['pending', 'needs_review', 'submitted'].includes(d.status) ? `
            <button onclick="TOC.participants.rowAction('approve', ${d.id}); TOC.drawer.close();"
                    class="flex-1 py-2 bg-dc-success/10 border border-dc-success/20 text-dc-success text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-dc-success/20 transition-colors">Approve</button>
            <button onclick="TOC.participants.rowAction('reject', ${d.id}); TOC.drawer.close();"
                    class="flex-1 py-2 bg-dc-danger/10 border border-dc-danger/20 text-dc-danger text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-dc-danger/20 transition-colors">Reject</button>
          ` : ''}
          ${d.status === 'confirmed' ? `
            <button onclick="TOC.participants.rowAction('dq', ${d.id}); TOC.drawer.close();"
                    class="flex-1 py-2 bg-dc-warning/10 border border-dc-warning/20 text-dc-warning text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-dc-warning/20 transition-colors">Disqualify</button>
          ` : ''}
        </div>`;

      TOC.drawer.open(d.participant_name, html, footerHtml);
      if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (err) {
      TOC.drawer.open('Error', `<p class="text-dc-danger text-sm p-4">Failed to load participant details.</p>`);
    }
  }

  /* ── S2-F9: CSV Export ──────────────────────────────────────────── */

  function exportCSV() {
    const url = `${TOC.config.apiBase}/participants/export/`;
    // Direct download — open in new tab
    window.open(url, '_blank');
  }

  /* ── Sorting ────────────────────────────────────────────────────── */

  function handleSort(e) {
    const btn = e.target.closest('.sort-header');
    if (!btn) return;
    const field = btn.dataset.sort;
    if (!field) return;

    if (currentOrdering === field) {
      currentOrdering = `-${field}`;
    } else if (currentOrdering === `-${field}`) {
      currentOrdering = field;
    } else {
      currentOrdering = field;
    }
    currentPage = 1;
    load();
  }

  /* ── Filter Bindings ────────────────────────────────────────────── */

  function bindFilters() {
    const filters = ['#filter-status', '#filter-payment', '#filter-checkin'];
    filters.forEach(sel => {
      const el = $(sel);
      if (el) {
        el.addEventListener('change', () => {
          currentPage = 1;
          load();
        });
      }
    });

    const searchInput = $('#filter-search');
    if (searchInput) {
      searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          currentPage = 1;
          load();
        }, 350);
      });
    }

    // Sort headers
    const thead = $('table.data-grid thead');
    if (thead) {
      thead.addEventListener('click', handleSort);
    }
  }

  /* ── Navigation ─────────────────────────────────────────────────── */

  function goPage(p) {
    currentPage = p;
    load();
    // Scroll to top of grid
    const grid = $('[data-tab-content="participants"]');
    if (grid) grid.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /* ── Badge Update ───────────────────────────────────────────────── */

  function updateBadge(total) {
    if (typeof TOC.badge === 'function') {
      TOC.badge('participants', total || 0);
    }
  }

  /* ── Helpers ────────────────────────────────────────────────────── */

  function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  }

  function formatDate(isoStr) {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  }

  /* ── Init ───────────────────────────────────────────────────────── */

  // Bind to TOC tab system — load when participants tab is shown
  const origNavigate = TOC.navigate;
  if (origNavigate) {
    TOC.navigate = function (tabId) {
      origNavigate.call(TOC, tabId);
      if (tabId === 'participants') {
        load();
      }
    };
  }

  // First-time load if we land directly on participants tab
  if (window.location.hash === '#participants') {
    setTimeout(load, 100);
  }

  // Bind filters after DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindFilters);
  } else {
    bindFilters();
  }

  /* ── Public API ─────────────────────────────────────────────────── */
  window.TOC = window.TOC || {};
  window.TOC.participants = {
    load,
    goPage,
    toggleSelect,
    toggleSelectAll,
    bulkAction,
    rowAction,
    toggleCheckin,
    openDetail,
    exportCSV,
  };

})();
