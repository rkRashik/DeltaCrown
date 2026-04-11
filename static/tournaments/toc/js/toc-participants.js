/**
 * TOC — Participants Tab (toc-participants.js)
 *
 * Tier-1 Esports Organizer UX
 * - Semantic status badges (FACEIT-style)
 * - System verification checks column
 * - Quick Review inline panel (zero-drawer verification fast-lane)
 * - Drawer overhaul with card-based layout
 * - Destructive action safety confirmations (custom modal, reason required)
 * - Optimistic UI (instant DOM updates, zero reloads)
 * - Rich CSV export (registration answers, txn IDs, phone numbers)
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
  let systemChecks = {};       // { regId: [flags] }  — cached per tab load
  let systemChecksLoadedAt = 0;
  let systemChecksPromise = null;
  let expandedQuickReview = null; // currently expanded row id (or null)
  const SYSTEM_CHECKS_TTL_MS = 25000;

  /* ── Semantic Status Badges ────────────────────────────────────── */
  const STATUS_CONFIG = {
    payment_submitted:  { bg: 'bg-amber-500/10',    border: 'border-amber-500/20',   text: 'text-amber-400',   label: 'Awaiting Verification', icon: 'clock' },
    submitted:          { bg: 'bg-amber-500/10',    border: 'border-amber-500/20',   text: 'text-amber-400',   label: 'Awaiting Verification', icon: 'clock' },
    needs_review:       { bg: 'bg-amber-500/10',    border: 'border-amber-500/20',   text: 'text-amber-400',   label: 'Awaiting Verification', icon: 'clock' },
    confirmed:          { bg: 'bg-emerald-500/10',  border: 'border-emerald-500/20', text: 'text-emerald-400', label: 'Ready to Play', icon: 'check-circle' },
    auto_approved:      { bg: 'bg-emerald-500/10',  border: 'border-emerald-500/20', text: 'text-emerald-400', label: 'Ready to Play', icon: 'check-circle' },
    pending:            { bg: 'bg-orange-500/10',   border: 'border-orange-500/20',  text: 'text-orange-400',  label: 'Action Required', icon: 'alert-circle' },
    waitlisted:         { bg: 'bg-purple-500/10',   border: 'border-purple-500/20',  text: 'text-purple-400',  label: 'Waitlist', icon: 'clock-3' },
    rejected:           { bg: 'bg-red-500/10',      border: 'border-red-500/20',     text: 'text-red-400',     label: 'Disqualified', icon: 'x-circle' },
    cancelled:          { bg: 'bg-zinc-500/10',     border: 'border-zinc-500/20',    text: 'text-zinc-400',    label: 'Cancelled', icon: 'minus-circle' },
    no_show:            { bg: 'bg-red-500/10',      border: 'border-red-500/20',     text: 'text-red-400',     label: 'Disqualified', icon: 'x-circle' },
    draft:              { bg: 'bg-zinc-500/10',     border: 'border-zinc-500/20',    text: 'text-zinc-400',    label: 'Draft', icon: 'file-edit' },
  };

  const PAYMENT_CONFIG = {
    Verified: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', text: 'text-emerald-400' },
    Pending:  { bg: 'bg-amber-500/10',   border: 'border-amber-500/20',   text: 'text-amber-400' },
    Rejected: { bg: 'bg-red-500/10',     border: 'border-red-500/20',     text: 'text-red-400'  },
    None:     { bg: 'bg-zinc-500/5',     border: 'border-zinc-500/10',    text: 'text-zinc-500' },
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
          <tr><td colspan="9" class="px-6 py-12 text-center">
            <p class="text-red-400 text-sm">Failed to load participants.</p>
            <button data-click="TOC.participants.load" class="mt-3 text-theme text-xs underline">Retry</button>
          </td></tr>`;
      }
    }
  }

  /** Fetch system checks in background and patch visible check icons */
  async function loadSystemChecks(options) {
    const opts = options || {};
    const now = Date.now();
    if (!opts.force && systemChecksLoadedAt > 0 && (now - systemChecksLoadedAt) < SYSTEM_CHECKS_TTL_MS) {
      return;
    }
    if (systemChecksPromise) {
      return systemChecksPromise;
    }

    systemChecksPromise = (async function () {
    try {
      const data = await TOC.fetch(`${TOC.config.apiBase}/participants/system-checks/`);
      systemChecks = data.per_registration || {};
      systemChecksLoadedAt = Date.now();
      // Re-render check icons for visible rows
      if (currentData) {
        currentData.results.forEach(row => {
          const cell = document.querySelector(`[data-checks-id="${row.id}"]`);
          if (cell) cell.innerHTML = renderCheckIcon(row.id);
        });
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    } catch (e) {
      console.warn('[TOC.participants] system checks load error:', e);
    } finally {
      systemChecksPromise = null;
    }
    })();

    return systemChecksPromise;
  }

  /* ── Render Grid ────────────────────────────────────────────────── */

  function render(data) {
    // Dynamic column header for IGL/Game ID column
    var thIgl = document.getElementById('th-igl-gameid');
    if (thIgl) {
      var cfg = window.TOC_CONFIG || {};
      if (cfg.isSolo) {
        thIgl.textContent = cfg.gameIdLabel || 'Game ID';
        thIgl.title = 'Player game-specific identifier';
      } else {
        thIgl.textContent = 'IGL';
        thIgl.title = 'In-Game Leader / Captain';
      }
    }
    renderRows(data.results);
    renderPagination(data);
    selectedIds.clear();
    expandedQuickReview = null;
    updateBulkBar();
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function renderRows(rows) {
    const tbody = $('#participants-tbody');
    if (!tbody) return;

    if (!rows || rows.length === 0) {
      tbody.innerHTML = `
        <tr><td colspan="9" class="px-6 py-16 text-center">
          <div class="flex flex-col items-center gap-3">
            <i data-lucide="inbox" class="w-10 h-10 text-zinc-600"></i>
            <p class="text-zinc-400 text-sm">No participants found.</p>
            <p class="text-zinc-500 text-xs">Adjust filters or wait for registrations.</p>
          </div>
        </td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map(row => {
      const scBase = STATUS_CONFIG[row.status] || STATUS_CONFIG.draft;
      const sc = row.is_hard_blocked
        ? { bg: 'bg-red-600/10', border: 'border-red-600/30', text: 'text-red-300', label: 'Blocked', icon: 'ban' }
        : scBase;
      const pc = PAYMENT_CONFIG[row.payment_status] || PAYMENT_CONFIG.None;
      const checked = selectedIds.has(row.id) ? 'checked' : '';
      const isAwaitingVerification = ['payment_submitted', 'submitted', 'needs_review'].includes(row.status);

      let html = `
        <tr class="border-b border-dc-border/30 hover:bg-white/[0.02] transition-colors cursor-pointer group"
            data-reg-id="${row.id}">
          <td class="px-3 py-2.5" data-click="event.stopPropagation">
            <input type="checkbox" class="toc-checkbox row-select" value="${row.id}" ${checked}
                   data-change="TOC.participants.toggleSelect" data-change-args="[${row.id}, this.checked]">
          </td>
          <td class="px-3 py-2.5" data-click="TOC.participants.openDetail" data-click-args="[${row.id}]">
            <div class="flex items-center gap-2.5">
              ${(row.team_logo_url || row.profile_avatar_url)
                ? `<img src="${esc(row.team_logo_url || row.profile_avatar_url)}" alt="" class="w-7 h-7 rounded-lg object-cover flex-shrink-0"
                       data-fallback="hide-show-next">
                   <div class="w-7 h-7 rounded-lg bg-theme-surface border border-theme-border items-center justify-center flex-shrink-0" style="display:none">
                     <span class="text-[10px] font-bold text-theme">${(row.participant_name || '?')[0].toUpperCase()}</span>
                   </div>`
                : `<div class="w-7 h-7 rounded-lg bg-theme-surface border border-theme-border flex items-center justify-center flex-shrink-0">
                     <span class="text-[10px] font-bold text-theme">${(row.participant_name || '?')[0].toUpperCase()}</span>
                   </div>`}
              <div class="min-w-0">
                <div class="flex items-center gap-1.5">
                  <p class="text-white text-xs font-semibold truncate max-w-[160px]">${esc(row.participant_name)}</p>
                  ${row.team_tag ? `<span class="text-[8px] px-1 py-0.5 rounded bg-theme/10 text-theme border border-theme/20 font-bold leading-none">${esc(row.team_tag)}</span>` : ''}
                </div>
                <p class="text-zinc-500 text-[10px] font-mono truncate">${esc(row.registration_number || row.username || '')}</p>
              </div>
              ${row.is_guest_team ? '<span class="px-1.5 py-0.5 bg-purple-500/10 border border-purple-500/20 text-purple-400 text-[8px] font-bold uppercase tracking-widest rounded">Guest</span>' : ''}
            </div>
          </td>
          <td class="px-3 py-2.5" data-click="TOC.participants.openDetail" data-click-args="[${row.id}]">
            <span class="inline-flex items-center gap-1 px-2 py-0.5 ${sc.bg} border ${sc.border} ${sc.text} text-[9px] font-bold uppercase tracking-widest rounded-md">
              <i data-lucide="${sc.icon}" class="w-2.5 h-2.5"></i>
              ${esc(sc.label)}
            </span>
          </td>
          <td class="px-3 py-2.5" data-click="TOC.participants.openDetail" data-click-args="[${row.id}]">
            <span class="inline-flex px-2 py-0.5 ${pc.bg} border ${pc.border} ${pc.text} text-[9px] font-bold uppercase tracking-widest rounded-md">
              ${esc(row.payment_status)}
            </span>
          </td>
          <td class="px-3 py-2.5 text-center" data-checks-id="${row.id}">
            ${renderCheckIcon(row.id)}
          </td>
          <td class="px-3 py-2.5 text-center" data-click="event.stopPropagation">
            <button data-click="TOC.participants.toggleCheckin" data-click-args="[${row.id}]"
                    class="w-8 h-5 rounded-full border transition-all relative ${
                      row.checked_in
                        ? 'bg-emerald-500/20 border-emerald-500/40'
                        : 'bg-dc-panel border-dc-border'
                    }">
              <span class="absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all ${
                row.checked_in
                  ? 'left-[14px] bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.4)]'
                  : 'left-0.5 bg-zinc-500'
              }"></span>
            </button>
          </td>
          <td class="px-3 py-2.5 text-center font-mono text-white text-xs" data-click="TOC.participants.openDetail" data-click-args="[${row.id}]">
            ${row.seed != null ? row.seed : '<span class="text-zinc-600">—</span>'}
          </td>
          <td class="px-3 py-2.5 font-mono text-zinc-400 text-[10px]" data-click="TOC.participants.openDetail" data-click-args="[${row.id}]">
            ${row.team_id
              ? (row.coordinator
                  ? `<div class="flex flex-col"><span class="text-theme text-[10px] not-italic">${esc(row.coordinator)}</span>${row.coordinator_game_id ? `<span class="text-zinc-500 text-[9px] font-mono">${esc(row.coordinator_game_id)}</span>` : ''}</div>`
                  : '<span class="text-zinc-600">—</span>')
              : esc(row.game_id || '—')}
          </td>
          <td class="px-3 py-2.5 text-right" data-click="event.stopPropagation">
            <div class="flex items-center justify-end gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
              ${isAwaitingVerification ? `
                <button data-click="TOC.participants.toggleQuickReview" data-click-args="[${row.id}]"
                  title="Quick Review" class="w-7 h-7 rounded-lg border border-theme/20 bg-theme/5 hover:bg-theme/15 flex items-center justify-center transition-colors">
                  <i data-lucide="scan-eye" class="w-3 h-3 text-theme"></i>
                </button>` : ''}
              ${actionButton(row, 'approve', 'check', 'emerald-400', 'Approve')}
              ${actionButton(row, 'reject', 'x', 'red-400', 'Reject')}
              ${actionButton(row, 'dq', 'shield-off', 'amber-400', 'DQ')}
              ${actionButton(row, 'promote_waitlist', 'arrow-up-circle', 'violet-400', 'Promote')}
              ${actionButton(row, 'notify', 'megaphone', 'sky-400', 'Alert')}
              ${actionButton(row, 'hard_block', 'ban', 'rose-400', 'Block')}
              ${actionButton(row, 'unblock', 'shield-check', 'emerald-300', 'Unblock')}
              ${actionButton(row, 'verify', 'badge-check', 'sky-400', 'Verify Pay')}
            </div>
          </td>
        </tr>`;

      // Quick Review inline panel (collapses below the row)
      if (expandedQuickReview === row.id && isAwaitingVerification) {
        html += renderQuickReviewPanel(row);
      }

      return html;
    }).join('');
  }

  /* ── System Check Icon (per row) ────────────────────────────────── */

  function renderCheckIcon(regId) {
    const flags = systemChecks[String(regId)] || systemChecks[regId];
    if (!flags || flags.length === 0) {
      return `<span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-500/10" title="All checks passed">
                <i data-lucide="check" class="w-3 h-3 text-emerald-400"></i>
              </span>`;
    }
    const hasCritical = flags.some(f => f.severity === 'critical');
    const color = hasCritical ? 'red' : 'amber';
    const tooltip = flags.map(f => `${f.severity.toUpperCase()}: ${f.message}`).join('&#10;');
    return `<span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-${color}-500/10 cursor-help"
                  title="${tooltip}">
              <i data-lucide="alert-triangle" class="w-3 h-3 text-${color}-400"></i>
            </span>`;
  }

  /* ── Quick Review Inline Panel ──────────────────────────────────── */

  function toggleQuickReview(id) {
    expandedQuickReview = (expandedQuickReview === id) ? null : id;
    if (currentData) {
      renderRows(currentData.results);
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }
  }

  function renderQuickReviewPanel(row) {
    const qp = row.quick_payment;
    if (!qp) {
      return `<tr class="quick-review-row border-b border-theme/20 bg-theme/[0.03]" data-qr-id="${row.id}">
        <td colspan="9" class="px-6 py-4">
          <p class="text-zinc-400 text-xs italic">No payment data found for this registration.</p>
        </td>
      </tr>`;
    }
    return `<tr class="quick-review-row border-b border-theme/20 bg-theme/[0.03]" data-qr-id="${row.id}">
      <td colspan="9" class="px-4 py-3">
        <div class="flex items-start gap-6 max-w-3xl">
          <div class="flex-1 space-y-2 text-xs">
            <div class="flex items-center gap-2 mb-2">
              <i data-lucide="scan-eye" class="w-3.5 h-3.5 text-theme"></i>
              <span class="text-[9px] font-bold text-theme uppercase tracking-widest">Quick Review</span>
            </div>
            <div class="grid grid-cols-2 gap-x-6 gap-y-1.5">
              <div><span class="text-zinc-500 text-[10px]">Transaction ID</span><p class="text-white font-mono text-xs font-bold">${esc(qp.transaction_id || '—')}</p></div>
              <div><span class="text-zinc-500 text-[10px]">Sender Phone</span><p class="text-white font-mono text-xs font-bold">${esc(qp.payer_account_number || '—')}</p></div>
              <div><span class="text-zinc-500 text-[10px]">Amount</span><p class="text-white font-mono text-xs">${qp.amount_bdt ? '৳' + esc(qp.amount_bdt) : '—'}</p></div>
              <div><span class="text-zinc-500 text-[10px]">Method</span><p class="text-white text-xs">${esc(qp.method || '—')}</p></div>
            </div>
          </div>
          <div class="flex-shrink-0">
            ${qp.proof_url
              ? `<img src="${qp.proof_url}" alt="Payment proof"
                      data-click="window.open" data-click-args="['${qp.proof_url}', &quot;_blank&quot;]"
                      class="w-20 h-20 object-cover rounded-lg border border-dc-border cursor-zoom-in hover:opacity-80 hover:border-theme/40 transition-all" />`
              : `<div class="w-20 h-20 rounded-lg border border-dc-border bg-dc-panel flex items-center justify-center">
                   <i data-lucide="image-off" class="w-5 h-5 text-zinc-600"></i>
                 </div>`}
          </div>
          <div class="flex flex-col gap-2 flex-shrink-0 pt-2">
            <button data-click="TOC.participants.rowAction" data-click-args="[&quot;verify&quot;, ${row.id}]" data-cap-require="approve_payments"
                    class="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-emerald-500/20 transition-colors flex items-center gap-1.5">
              <i data-lucide="check-circle" class="w-3 h-3"></i> Verify
            </button>
            <button data-click="TOC.participants.rowAction" data-click-args="[&quot;reject&quot;, ${row.id}]" data-cap-require="manage_registrations"
                    class="px-4 py-2 bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-red-500/20 transition-colors flex items-center gap-1.5">
              <i data-lucide="x-circle" class="w-3 h-3"></i> Reject
            </button>
          </div>
        </div>
      </td>
    </tr>`;
  }

  function actionButton(row, action, icon, color, title) {
    const showApprove = ['pending', 'needs_review', 'submitted'].includes(row.status);
    const showReject = ['pending', 'needs_review', 'submitted', 'payment_submitted'].includes(row.status);
    const showDQ = row.status === 'confirmed' || row.status === 'auto_approved';
    const showPromote = row.status === 'waitlisted';
    const showNotify = ['waitlisted', 'pending', 'needs_review', 'submitted', 'payment_submitted', 'confirmed', 'auto_approved', 'rejected'].includes(row.status);
    const showHardBlock = !row.is_hard_blocked;
    const showUnblock = !!row.is_hard_blocked;
    const showVerify = row.payment_status === 'Pending';

    if (action === 'approve' && !showApprove) return '';
    if (action === 'reject' && !showReject) return '';
    if (action === 'dq' && !showDQ) return '';
    if (action === 'promote_waitlist' && !showPromote) return '';
    if (action === 'notify' && !showNotify) return '';
    if (action === 'hard_block' && !showHardBlock) return '';
    if (action === 'unblock' && !showUnblock) return '';
    if (action === 'verify' && !showVerify) return '';

    // Map actions to capabilities for RBAC gating
    var capMap = {
      approve: 'manage_registrations',
      reject: 'manage_registrations',
      dq: 'manage_registrations',
      promote_waitlist: 'manage_registrations',
      notify: 'manage_registrations',
      hard_block: 'manage_registrations',
      unblock: 'manage_registrations',
      verify: 'approve_payments',
    };
    var capAttr = capMap[action] ? ' data-cap-require="' + capMap[action] + '"' : '';

    return `<button data-click="TOC.participants.rowAction" data-click-args="['${action}', ${row.id}]"
              title="${title}"${capAttr}
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
    html += `<button ${data.page <= 1 ? 'disabled' : ''} data-click="TOC.participants.goPage" data-click-args="[${data.page - 1}]"
              class="w-7 h-7 rounded border border-dc-border text-zinc-400 hover:text-white hover:border-dc-borderLight disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center transition-colors text-xs">
              <i data-lucide="chevron-left" class="w-3 h-3"></i></button>`;

    // Page numbers (show up to 7: first ... middle ... last)
    const pages = buildPageNumbers(data.page, data.pages);
    for (const p of pages) {
      if (p === '...') {
        html += `<span class="px-1 text-zinc-600 text-[10px]">…</span>`;
      } else {
        const active = p === data.page;
        html += `<button data-click="TOC.participants.goPage" data-click-args="[${p}]"
                  class="w-7 h-7 rounded border text-[10px] font-bold flex items-center justify-center transition-colors
                    ${active
                      ? 'border-theme bg-theme/10 text-theme'
                      : 'border-dc-border text-zinc-400 hover:text-white hover:border-dc-borderLight'
                    }">${p}</button>`;
      }
    }

    // Next
    html += `<button ${data.page >= data.pages ? 'disabled' : ''} data-click="TOC.participants.goPage" data-click-args="[${data.page + 1}]"
              class="w-7 h-7 rounded border border-dc-border text-zinc-400 hover:text-white hover:border-dc-borderLight disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center transition-colors text-xs">
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
      reason = await promptReason(`Reason for bulk ${action}?`, action === 'reject');
      if (reason === null) return; // cancelled
    }

    try {
        const result = await TOC.fetch(`${TOC.config.apiBase}/participants/bulk-action/`, {
        method: 'POST',
        body: JSON.stringify({ action, ids, reason }),
      });
        TOC.toast(`Done: ${result.processed}/${result.total_requested} participants updated.`, 'success');
      if (result.errors && result.errors.length > 0) {
          TOC.toast(`Completed with ${result.errors.length} issue(s).`, 'warning');
        console.warn('[TOC.participants] Bulk errors:', result.errors);
      }
      selectedIds.clear();
      load();
    } catch (err) {
          TOC.toast((err && err.message) ? err.message : 'Could not complete the bulk action. Please try again.', 'error');
    }
  }

  /* ── Inline Row Actions — Optimistic UI ───────────────────────── */

  async function rowAction(action, id) {
    let endpoint = '';
    let body = {};

    switch (action) {
      case 'approve':
        endpoint = `${TOC.config.apiBase}/participants/${id}/approve/`;
        break;
      case 'reject': {
        const reason = await promptReason('Rejection reason:', true);
        if (reason === null) return;
        endpoint = `${TOC.config.apiBase}/participants/${id}/reject/`;
        body = { reason };
        break;
      }
      case 'dq': {
        const reason = await promptReason('Disqualification reason (required):', false);
        if (reason === null) return;
        if (!reason.trim()) {
          TOC.toast('A reason is required for disqualification.', 'warning');
          return;
        }
        const autoRefund = window.confirm('Refund this participant payment now?');
        endpoint = `${TOC.config.apiBase}/participants/${id}/disqualify/`;
        body = { reason, auto_refund: autoRefund };
        break;
      }
      case 'verify':
        endpoint = `${TOC.config.apiBase}/participants/${id}/verify-payment/`;
        break;
      case 'promote_waitlist':
        endpoint = `${TOC.config.apiBase}/participants/${id}/promote-waitlist/`;
        break;
      case 'notify': {
        const message = await promptReason('Participant alert/message:', false);
        if (message === null) return;
        if (!message.trim()) {
          TOC.toast('Message is required.', 'warning');
          return;
        }
        endpoint = `${TOC.config.apiBase}/participants/${id}/notify/`;
        body = { subject: 'TOC Alert', message: message.trim() };
        break;
      }
      case 'hard_block': {
        const reason = await promptReason('Permanent block reason (required):', false);
        if (reason === null) return;
        if (!reason.trim()) {
          TOC.toast('A block reason is required.', 'warning');
          return;
        }
        const autoRefund = window.confirm('Refund this participant payment now?');
        endpoint = `${TOC.config.apiBase}/participants/${id}/hard-block/`;
        body = { reason: reason.trim(), auto_refund: autoRefund };
        break;
      }
      case 'unblock': {
        const note = await promptReason('Unblock note (optional):', true);
        if (note === null) return;
        endpoint = `${TOC.config.apiBase}/participants/${id}/unblock/`;
        body = { reason: (note || '').trim() };
        break;
      }
      default:
        return;
    }

    // Optimistic: dim the row during API call
    const tr = document.querySelector(`tr[data-reg-id="${id}"]`);
    if (tr) tr.style.opacity = '0.5';

    try {
      const result = await TOC.fetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(body),
      });
      const isSuccess = (typeof result.ok === 'boolean') ? result.ok : !result.error;
      if (isSuccess) {
        TOC.toast(result.message || 'Done: action completed successfully.', 'success');
        // Optimistic DOM update — splice the new row data in
        if (result.participant && currentData) {
          const idx = currentData.results.findIndex(r => r.id === id);
          if (idx !== -1) {
            currentData.results[idx] = result.participant;
            if (expandedQuickReview === id) expandedQuickReview = null;
            renderRows(currentData.results);
            if (typeof lucide !== 'undefined') lucide.createIcons();
          } else {
            load();
          }
        } else {
          load();
        }
      } else {
        if (tr) tr.style.opacity = '1';
        TOC.toast(result.error || 'Could not complete this action. Please try again.', 'error');
      }
    } catch (err) {
      if (tr) tr.style.opacity = '1';
      const msg = (err && err.message) ? err.message : 'Could not complete the action. Please try again.';
      TOC.toast(msg, 'error');
    }
  }

  /* ── Destructive Action Confirmation Modal ──────────────────────── */

  /**
   * Custom confirmation modal — replaces native prompt() / confirm().
   * Returns entered reason string, or null if cancelled.
   * @param {string} question - label above the textarea
   * @param {boolean} optional - if true, empty reason is accepted
   */
  function promptReason(question, optional) {
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm';
      overlay.style.animation = 'fadeIn 0.15s ease-out';
      overlay.innerHTML = `
        <div class="bg-dc-bg border border-dc-border rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
          <div class="p-6 space-y-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                <i data-lucide="alert-triangle" class="w-5 h-5 text-red-400"></i>
              </div>
              <div>
                <h3 class="text-white font-bold text-sm">Confirm Action</h3>
                <p class="text-zinc-400 text-xs">This action cannot be easily undone.</p>
              </div>
            </div>
            <div>
              <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block mb-1.5">${esc(question)}</label>
              <textarea id="confirm-reason-input" rows="3"
                        placeholder="${optional ? 'Optional reason...' : 'Enter reason (required)...'}"
                        class="w-full bg-dc-panel border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none placeholder:text-zinc-600"></textarea>
            </div>
          </div>
          <div class="flex border-t border-dc-border">
            <button id="confirm-cancel" class="flex-1 py-3 text-zinc-400 text-xs font-bold uppercase tracking-widest hover:bg-white/5 transition-colors">Cancel</button>
            <button id="confirm-ok" class="flex-1 py-3 text-red-400 text-xs font-bold uppercase tracking-widest hover:bg-red-500/10 transition-colors border-l border-dc-border">Confirm</button>
          </div>
        </div>`;

      document.body.appendChild(overlay);
      if (typeof lucide !== 'undefined') lucide.createIcons();

      const input = overlay.querySelector('#confirm-reason-input');
      const cancel = overlay.querySelector('#confirm-cancel');
      const ok = overlay.querySelector('#confirm-ok');

      setTimeout(() => input?.focus(), 50);

      const cleanup = (val) => { overlay.remove(); resolve(val); };

      cancel.onclick = () => cleanup(null);
      ok.onclick = () => cleanup(input.value || '');
      overlay.addEventListener('click', (e) => { if (e.target === overlay) cleanup(null); });
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); cleanup(input.value || ''); }
        if (e.key === 'Escape') cleanup(null);
      });
    });
  }

  /* ── Check-in Toggle (Optimistic) ─────────────────────────────── */

  async function toggleCheckin(id) {
    // Optimistic: flip the toggle immediately in the UI
    if (currentData) {
      const idx = currentData.results.findIndex(r => r.id === id);
      if (idx !== -1) {
        currentData.results[idx] = { ...currentData.results[idx], checked_in: !currentData.results[idx].checked_in };
        renderRows(currentData.results);
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    }

    try {
      const result = await TOC.fetch(`${TOC.config.apiBase}/participants/${id}/toggle-checkin/`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (result.ok) {
        const state = result.participant?.checked_in ? 'checked in' : 'checked out';
        TOC.toast(`Done: participant ${state}.`, 'success');
        // Merge server truth back into state
        if (result.participant && currentData) {
          const idx = currentData.results.findIndex(r => r.id === id);
          if (idx !== -1) {
            currentData.results[idx] = result.participant;
            renderRows(currentData.results);
            if (typeof lucide !== 'undefined') lucide.createIcons();
          }
        }
      } else {
        TOC.toast(result.error || 'Could not complete the check-in toggle.', 'error');
        load(); // revert on failure
      }
    } catch (err) {
        TOC.toast((err && err.message) ? err.message : 'Could not complete the check-in action.', 'error');
      load(); // revert on failure
    }
  }

  /* ── Participant Detail Drawer — Card-based Layout ────────────── */

  async function openDetail(id) {
    TOC.drawer.open('Loading...', '<div class="flex items-center justify-center h-40"><div class="w-5 h-5 border-2 border-theme border-t-transparent rounded-full animate-spin"></div></div>');

    try {
      const d = await TOC.fetch(`${TOC.config.apiBase}/participants/${id}/`);
      const sc = STATUS_CONFIG[d.status] || STATUS_CONFIG.draft;
      const ti = d.team_info || {};
      const gm = d.game_meta || {};
      const gameIdLabel = gm.game_id_label || 'Game ID';

      // Team avatar — with onerror fallback for broken/missing logos
      const initials = (d.participant_name || '?')[0].toUpperCase();
      const avatarFallback = `<div class="w-10 h-10 rounded-xl bg-theme-surface border border-theme-border flex items-center justify-center flex-shrink-0">
            <span class="text-base font-bold text-theme">${initials}</span>
          </div>`;
      const avatarSrc = ti.logo_url || d.profile_avatar_url || '';
      const avatarHtml = avatarSrc
        ? `<img src="${esc(avatarSrc)}" alt="" class="w-10 h-10 rounded-xl object-cover border border-dc-border/50"
               data-fallback="hide-show-next">
           <div class="w-10 h-10 rounded-xl bg-theme-surface border border-theme-border items-center justify-center flex-shrink-0" style="display:none">
            <span class="text-base font-bold text-theme">${initials}</span>
           </div>`
        : avatarFallback;

      // ━━ Card 1: Identity ━━
      const identityCard = `
        <div class="bg-dc-panel border border-dc-border rounded-xl overflow-hidden">
          <div class="px-4 py-2.5 border-b border-dc-border/50 bg-dc-bg/50">
            <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest">${d.team_id ? 'Team' : 'Player'} Identity</span>
          </div>
          <div class="p-4 space-y-2.5 text-xs">
            <div class="flex items-center gap-3 mb-3">
              ${avatarHtml}
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  ${d.team_slug ? `<a href="/teams/${esc(d.team_slug)}/" target="_blank" class="text-white font-bold text-sm hover:text-theme transition-colors">${esc(d.participant_name)}</a>` : `<h3 class="text-white font-bold text-sm">${esc(d.participant_name)}</h3>`}
                  ${ti.tag ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-dc-surface border border-dc-border/50 text-dc-text font-mono">[${esc(ti.tag)}]</span>` : ''}
                </div>
                <p class="text-zinc-500 text-[10px] font-mono">${esc(d.registration_number || '')}</p>
              </div>
            </div>
            ${d.username ? `<div class="flex justify-between"><span class="text-zinc-500">Username</span><span class="text-white">@${esc(d.username)}</span></div>` : ''}
            <div class="flex justify-between"><span class="text-zinc-500">Status</span>
              <span class="inline-flex items-center gap-1 px-2 py-0.5 ${sc.bg} border ${sc.border} ${sc.text} text-[9px] font-bold uppercase tracking-widest rounded-md">
                <i data-lucide="${sc.icon}" class="w-2.5 h-2.5"></i> ${esc(sc.label)}
              </span>
            </div>
            <div class="flex justify-between"><span class="text-zinc-500">Check-In</span>
              <span class="${d.checked_in ? 'text-emerald-400 font-bold' : 'text-zinc-600'}">${d.checked_in ? '✓ Checked In' : 'Not checked in'}</span>
            </div>
            ${d.seed != null ? `<div class="flex justify-between"><span class="text-zinc-500">Seed</span><span class="text-white font-mono font-bold">#${d.seed}</span></div>` : ''}
            ${d.slot_number != null ? `<div class="flex justify-between"><span class="text-zinc-500">Slot</span><span class="text-white font-mono">${d.slot_number}</span></div>` : ''}
            ${d.waitlist_position != null ? `<div class="flex justify-between"><span class="text-zinc-500">Waitlist</span><span class="text-white font-mono">#${d.waitlist_position}</span></div>` : ''}
            ${d.is_guest_team ? '<div class="flex justify-between"><span class="text-zinc-500">Guest Team</span><span class="text-purple-400 font-bold">Yes</span></div>' : ''}
            <div class="flex justify-between"><span class="text-zinc-500">Registered</span><span class="text-white font-mono text-[10px]">${formatDate(d.registered_at)}</span></div>
          </div>
        </div>`;

      // ━━ Card 1b: Coordinator / IGL ━━
      let coordinatorCard = '';
      const coord = d.coordinator;
      if (coord && coord.display_name) {
        coordinatorCard = `
          <div class="bg-dc-panel border border-dc-border rounded-xl overflow-hidden">
            <div class="px-4 py-2.5 border-b border-dc-border/50 bg-dc-bg/50 flex items-center gap-2">
              <i data-lucide="crown" class="w-3 h-3 text-amber-400"></i>
              <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest">IGL / Coordinator</span>
            </div>
            <div class="p-4 space-y-2 text-xs">
              <div class="flex justify-between">
                <span class="text-zinc-500">Name</span>
                ${coord.profile_slug
                  ? `<a href="/u/${esc(coord.profile_slug)}/" target="_blank" class="text-theme hover:underline font-medium">${esc(coord.display_name)}</a>`
                  : `<span class="text-white font-medium">${esc(coord.display_name)}</span>`}
              </div>
              <div class="flex justify-between"><span class="text-zinc-500">Role</span><span class="text-amber-400 text-[10px] font-bold">${esc(coord.role || 'IGL')}</span></div>
              ${coord.game_id ? `<div class="flex justify-between"><span class="text-zinc-500">${esc(gameIdLabel)}</span><span class="text-emerald-300 font-mono text-[10px]">${esc(coord.game_id)}</span></div>` : ''}
            </div>
          </div>`;
      }

      // ━━ Card 1c: Communication Channels ━━
      let commCard = '';
      const channels = d.communication_channels || [];
      if (channels.length > 0) {
        const iconMap = { discord: 'message-circle', whatsapp: 'phone', phone: 'phone', messenger: 'message-square', email: 'mail', telegram: 'send' };
        commCard = `
          <div class="bg-dc-panel border border-dc-border rounded-xl overflow-hidden">
            <div class="px-4 py-2.5 border-b border-dc-border/50 bg-dc-bg/50">
              <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest">Communication</span>
            </div>
            <div class="p-4 space-y-2 text-xs">
              ${channels.map(ch => {
                const icon = iconMap[(ch.key || '').toLowerCase()] || 'globe';
                const val = ch.value || '—';
                return `<div class="flex items-center justify-between">
                  <span class="flex items-center gap-1.5 text-zinc-500"><i data-lucide="${icon}" class="w-3 h-3"></i>${esc(ch.label)}</span>
                  <span class="text-white font-mono text-[10px]">${esc(val)}</span>
                </div>`;
              }).join('')}
            </div>
          </div>`;
      }

      // ━━ Card 2: Automated Checks ━━
      const regFlags = systemChecks[String(d.id)] || systemChecks[d.id] || [];
      const checksCard = `
        <div class="bg-dc-panel border border-dc-border rounded-xl overflow-hidden">
          <div class="px-4 py-2.5 border-b border-dc-border/50 bg-dc-bg/50">
            <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest">Automated Checks</span>
          </div>
          <div class="p-4 text-xs">
            ${regFlags.length === 0
              ? `<div class="flex items-center gap-2 text-emerald-400">
                   <i data-lucide="check-circle" class="w-4 h-4"></i>
                   <span class="font-bold">All system checks passed</span>
                 </div>`
              : `<div class="space-y-2">${regFlags.map(f => {
                  const c = f.severity === 'critical' ? 'red' : f.severity === 'warning' ? 'amber' : 'sky';
                  return `<div class="flex items-start gap-2 p-2 rounded-lg bg-${c}-500/5 border border-${c}-500/10">
                    <i data-lucide="${f.severity === 'info' ? 'info' : 'alert-triangle'}" class="w-3.5 h-3.5 text-${c}-400 flex-shrink-0 mt-0.5"></i>
                    <div>
                      <span class="text-[9px] font-bold text-${c}-400 uppercase tracking-widest">${esc(f.severity)}</span>
                      <p class="text-zinc-300 text-xs mt-0.5">${esc(f.message)}</p>
                      ${f.details ? `<p class="text-zinc-500 text-[10px] mt-0.5">${esc(f.details)}</p>` : ''}
                    </div>
                  </div>`;
                }).join('')}</div>`
            }
          </div>
        </div>`;

      // ━━ Card 3: Payment Details ━━
      let paymentCard = '';
      if (d.payment) {
        const ppc = PAYMENT_CONFIG[d.payment.status_display] || PAYMENT_CONFIG.None;
        paymentCard = `
          <div class="bg-dc-panel border border-dc-border rounded-xl overflow-hidden">
            <div class="px-4 py-2.5 border-b border-dc-border/50 bg-dc-bg/50">
              <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest">Payment Details</span>
            </div>
            <div class="p-4 space-y-2 text-xs">
              <div class="flex justify-between"><span class="text-zinc-500">Status</span><span class="${ppc.text} font-bold">${esc(d.payment.status_display)}</span></div>
              ${d.payment.method ? `<div class="flex justify-between"><span class="text-zinc-500">Method</span><span class="text-white">${esc(d.payment.method)}</span></div>` : ''}
              ${d.payment.amount_bdt ? `<div class="flex justify-between"><span class="text-zinc-500">Amount</span><span class="text-white font-mono font-bold">৳${esc(d.payment.amount_bdt)}</span></div>` : ''}
              ${d.payment.transaction_id ? `<div class="flex justify-between"><span class="text-zinc-500">Transaction ID</span><span class="text-white font-mono text-[10px]">${esc(d.payment.transaction_id)}</span></div>` : ''}
              ${d.payment.payer_account_number ? `<div class="flex justify-between"><span class="text-zinc-500">Sender Phone</span><span class="text-white font-mono text-[10px]">${esc(d.payment.payer_account_number)}</span></div>` : ''}
              ${d.payment.reference_number ? `<div class="flex justify-between"><span class="text-zinc-500">Reference</span><span class="text-white font-mono text-[10px]">${esc(d.payment.reference_number)}</span></div>` : ''}
              ${d.payment.verified_by ? `<div class="flex justify-between"><span class="text-zinc-500">Verified By</span><span class="text-white">${esc(d.payment.verified_by)}</span></div>` : ''}
              ${d.payment.reject_reason ? `<div class="flex justify-between"><span class="text-zinc-500">Reject Reason</span><span class="text-red-400">${esc(d.payment.reject_reason)}</span></div>` : ''}
              ${d.payment.proof_image ? `
                <div class="mt-2 pt-2 border-t border-dc-border/30">
                  <p class="text-[9px] text-zinc-500 uppercase tracking-widest mb-2">Payment Proof</p>
                  <img src="${d.payment.proof_image}" alt="Payment proof"
                       data-click="window.open" data-click-args="['${d.payment.proof_image}', &quot;_blank&quot;]"
                       class="w-full max-h-48 object-contain rounded-lg border border-dc-border cursor-zoom-in hover:opacity-80 transition-opacity" />
                </div>` : ''}
            </div>
          </div>`;
      }

      // ━━ Card 4: Registration Answers ━━
      let regAnswersCard = '';
      const regDataFiltered = Object.entries(d.registration_data || {}).filter(([k]) => k !== 'communication_channels');
      if (regDataFiltered.length > 0) {
        regAnswersCard = `
          <div class="bg-dc-panel border border-dc-border rounded-xl overflow-hidden">
            <div class="px-4 py-2.5 border-b border-dc-border/50 bg-dc-bg/50">
              <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest">Registration Answers</span>
            </div>
            <div class="p-4 space-y-2 text-xs">
              ${regDataFiltered.map(([k, v]) => `
                <div class="flex justify-between gap-3">
                  <span class="text-zinc-500 shrink-0">${esc(k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()))}</span>
                  <span class="text-white text-right font-mono text-[10px] break-all">${esc(typeof v === 'object' ? JSON.stringify(v) : String(v))}</span>
                </div>
              `).join('')}
            </div>
          </div>`;
      }

      // ━━ Card 5: Roster with Game IDs ━━
      let lineupCard = '';
      if (d.lineup_snapshot && d.lineup_snapshot.length > 0) {
        const roleIcon = (p) => {
          if (p.role === 'OWNER' || p.is_igl || p.is_tournament_captain) return `<span class="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded font-bold bg-amber-500/20 text-amber-400"><i data-lucide="crown" class="w-2.5 h-2.5"></i>IGL</span>`;
          if (p.roster_slot === 'SUBSTITUTE') return `<span class="text-[9px] px-1.5 py-0.5 rounded bg-slate-500/20 text-slate-400">SUB</span>`;
          return `<span class="text-[9px] px-1.5 py-0.5 rounded bg-dc-surface/60 text-dc-text border border-dc-border/30">START</span>`;
        };
        lineupCard = `
          <div class="bg-dc-panel border border-dc-border rounded-xl overflow-hidden">
            <div class="px-4 py-2.5 border-b border-dc-border/50 bg-dc-bg/50">
              <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest">Roster (${d.lineup_snapshot.length})</span>
            </div>
            <table class="w-full text-[10px]">
              <thead><tr class="border-b border-dc-border/30 text-zinc-500">
                <th class="text-left px-4 py-1.5">Player</th>
                <th class="text-left px-2 py-1.5">Role</th>
                <th class="text-left px-2 py-1.5">${esc(gameIdLabel)}</th>
              </tr></thead>
              <tbody class="divide-y divide-dc-border/20">
                ${d.lineup_snapshot.map(p => {
                  const name = p.display_name || p.username || 'Unknown';
                  const profileLink = p.profile_slug ? `<a href="/u/${esc(p.profile_slug)}/" target="_blank" class="text-white hover:text-theme transition-colors">${esc(name)}</a>` : `<span class="text-white">${esc(name)}</span>`;
                  const gid = p.game_id ? `<span class="font-mono text-emerald-300">${esc(p.game_id)}</span>` : `<span class="text-zinc-600 italic">—</span>`;
                  return `<tr class="hover:bg-white/[.02]">
                    <td class="px-4 py-1.5">${profileLink}</td>
                    <td class="px-2 py-1.5">${roleIcon(p)}</td>
                    <td class="px-2 py-1.5">${gid}</td>
                  </tr>`;
                }).join('')}
              </tbody>
            </table>
          </div>`;
      }

      // ━━ Team links ━━
      let teamLinksCard = '';
      if (ti.discord_invite_url || ti.twitter_url || ti.website_url) {
        teamLinksCard = `
          <div class="bg-dc-panel border border-dc-border rounded-xl overflow-hidden">
            <div class="px-4 py-2.5 border-b border-dc-border/50 bg-dc-bg/50">
              <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest">Team Links</span>
            </div>
            <div class="p-4 flex flex-wrap gap-2">
              ${ti.discord_invite_url ? `<a href="${esc(ti.discord_invite_url)}" target="_blank" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#5865F2]/10 border border-[#5865F2]/20 text-[#7289DA] text-[10px] font-medium hover:bg-[#5865F2]/20"><i data-lucide="message-circle" class="w-3 h-3"></i>Discord</a>` : ''}
              ${ti.twitter_url ? `<a href="${esc(ti.twitter_url)}" target="_blank" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 text-[10px] font-medium hover:bg-sky-500/20"><i data-lucide="twitter" class="w-3 h-3"></i>Twitter</a>` : ''}
              ${ti.website_url ? `<a href="${esc(ti.website_url)}" target="_blank" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-dc-surface border border-dc-border/50 text-dc-text text-[10px] font-medium hover:border-dc-borderLight"><i data-lucide="globe" class="w-3 h-3"></i>Website</a>` : ''}
            </div>
          </div>`;
      }

      // ━━ Timestamps ━━
      const timestampsHtml = `
        <div class="pt-3 border-t border-dc-border/30 text-[10px] text-zinc-600 space-y-1">
          <p>Created: ${formatDate(d.created_at)}</p>
          <p>Updated: ${formatDate(d.updated_at)}</p>
        </div>`;

      const html = `<div class="space-y-3">${identityCard}${coordinatorCard}${commCard}${checksCard}${paymentCard}${regAnswersCard}${lineupCard}${teamLinksCard}${timestampsHtml}</div>`;

      // ━━ Footer: contextual actions with safety friction ━━
      let footerActions = [];
      if (['pending', 'needs_review', 'submitted', 'payment_submitted'].includes(d.status)) {
        footerActions.push(`
          <button data-click="TOC.participants.rowAction" data-click-args="[&quot;approve&quot;, ${d.id}]" data-click-also="TOC.drawer.close"
                  class="flex-1 py-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-emerald-500/20 transition-colors flex items-center justify-center gap-1.5">
            <i data-lucide="check-circle" class="w-3.5 h-3.5"></i> Approve
          </button>`);
        footerActions.push(`
          <button data-click="TOC.participants.rowAction" data-click-args="[&quot;reject&quot;, ${d.id}]" data-click-also="TOC.drawer.close"
                  class="flex-1 py-2.5 bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-red-500/20 transition-colors flex items-center justify-center gap-1.5">
            <i data-lucide="x-circle" class="w-3.5 h-3.5"></i> Reject
          </button>`);
      }
      if (d.status === 'confirmed' || d.status === 'auto_approved') {
        footerActions.push(`
          <button data-click="TOC.participants.rowAction" data-click-args="[&quot;dq&quot;, ${d.id}]" data-click-also="TOC.drawer.close"
                  class="flex-1 py-2.5 bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-red-500/20 transition-colors flex items-center justify-center gap-1.5">
            <i data-lucide="shield-off" class="w-3.5 h-3.5"></i> Disqualify
          </button>`);
      }
      if (d.status === 'waitlisted') {
        footerActions.push(`
          <button data-click="TOC.participants.rowAction" data-click-args="[&quot;promote_waitlist&quot;, ${d.id}]" data-click-also="TOC.drawer.close"
                  class="flex-1 py-2.5 bg-violet-500/10 border border-violet-500/20 text-violet-300 text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-violet-500/20 transition-colors flex items-center justify-center gap-1.5">
            <i data-lucide="arrow-up-circle" class="w-3.5 h-3.5"></i> Promote Waitlist
          </button>`);
      }
      footerActions.push(`
        <button data-click="TOC.participants.rowAction" data-click-args="[&quot;notify&quot;, ${d.id}]" data-click-also="TOC.drawer.close"
                class="flex-1 py-2.5 bg-sky-500/10 border border-sky-500/20 text-sky-400 text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-sky-500/20 transition-colors flex items-center justify-center gap-1.5">
          <i data-lucide="megaphone" class="w-3.5 h-3.5"></i> Send Alert
        </button>`);
      if (d.is_hard_blocked) {
        footerActions.push(`
          <button data-click="TOC.participants.rowAction" data-click-args="[&quot;unblock&quot;, ${d.id}]" data-click-also="TOC.drawer.close"
                  class="flex-1 py-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-emerald-500/20 transition-colors flex items-center justify-center gap-1.5">
            <i data-lucide="shield-check" class="w-3.5 h-3.5"></i> Remove Block
          </button>`);
      } else {
        footerActions.push(`
          <button data-click="TOC.participants.rowAction" data-click-args="[&quot;hard_block&quot;, ${d.id}]" data-click-also="TOC.drawer.close"
                  class="flex-1 py-2.5 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-rose-500/20 transition-colors flex items-center justify-center gap-1.5">
            <i data-lucide="ban" class="w-3.5 h-3.5"></i> Hard Block
          </button>`);
      }
      if (d.payment && d.payment.status_display === 'Pending') {
        footerActions.push(`
          <button data-click="TOC.participants.rowAction" data-click-args="[&quot;verify&quot;, ${d.id}]" data-click-also="TOC.drawer.close"
                  class="flex-1 py-2.5 bg-sky-500/10 border border-sky-500/20 text-sky-400 text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-sky-500/20 transition-colors flex items-center justify-center gap-1.5">
            <i data-lucide="badge-check" class="w-3.5 h-3.5"></i> Verify Payment
          </button>`);
      }

      // Send message to team IGL
      if (d.team_id && coord && coord.display_name) {
        footerActions.push(`
          <button data-click="TOC.notifications.teamMessage" data-click-args="[${d.team_id}]"
                  class="flex-1 py-2.5 bg-theme/10 border border-theme/20 text-theme text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-theme/20 transition-colors flex items-center justify-center gap-1.5">
            <i data-lucide="send" class="w-3.5 h-3.5"></i> Message Team
          </button>`);
      }

      const footerHtml = footerActions.length > 0
        ? `<div class="flex gap-2 flex-wrap">${footerActions.join('')}</div>`
        : '';

      TOC.drawer.open(d.participant_name, html, footerHtml);
      if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (err) {
      TOC.drawer.open('Error', `<p class="text-red-400 text-sm p-4">Failed to load participant details.</p>`);
    }
  }

  /* ── S2-F9: CSV Export ──────────────────────────────────────────── */

  function exportCSV() {
    const url = `${TOC.config.apiBase}/participants/export/`;
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

  function init() {
    load();
    loadSystemChecks(); // background — non-blocking
  }

  // Bind to TOC tab system — load when participants tab is shown
  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'participants') init();
  });

  // First-time load if we land directly on participants tab
  if (window.location.hash === '#participants') {
    setTimeout(init, 100);
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
    refresh: load,
    init,
    goPage,
    toggleSelect,
    toggleSelectAll,
    bulkAction,
    rowAction,
    toggleCheckin,
    openDetail,
    exportCSV,
    toggleQuickReview,
    loadSystemChecks,
  };

})();
