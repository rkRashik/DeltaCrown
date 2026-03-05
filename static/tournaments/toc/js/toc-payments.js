/**
 * TOC Payments Module — Sprint 5 "Rapid Verification Factory"
 * Financial Operations: Payment verification, revenue analytics,
 * prize distribution, bounty management, KYC & refund workflows.
 *
 * Sprint 5 changes:
 *  - Local currentRows state for O(1) optimistic splice
 *  - Inline proof thumbnails for submitted/pending rows
 *  - Post-verify auto-hide with slide-out animation
 *  - Auto-advance highlighting to next pending row
 *  - Custom reject modal (replaces native prompt())
 *  - Search auto-focus on tab activation
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  /* ─── state ───────────────────────────────────────────────── */
  let currentPage = 1;
  const pageSize = 20;
  let selectedIds = new Set();
  let _searchTimer = null;
  let currentRows = [];           // S5: local shallow copy for optimistic ops
  let _lastPaginationData = null; // S5: cache for re-rendering pagination

  /* ─── helpers ─────────────────────────────────────────────── */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const statusColors = {
    pending:   'bg-dc-warning/10 text-dc-warning border-dc-warning/20',
    submitted: 'bg-dc-info/10 text-dc-info border-dc-info/20',
    verified:  'bg-dc-success/10 text-dc-success border-dc-success/20',
    rejected:  'bg-dc-danger/10 text-dc-danger border-dc-danger/20',
    refunded:  'bg-purple-500/10 text-purple-400 border-purple-500/20',
    waived:    'bg-dc-text/10 text-dc-text border-dc-text/20',
    expired:   'bg-dc-text/10 text-dc-text border-dc-text/20',
  };

  const bountyTypeLabels = {
    mvp: 'MVP', stat_leader: 'Stat Leader', community_vote: 'Community Vote',
    special_achievement: 'Special Achievement', custom: 'Custom',
  };

  function badge(status) {
    const c = statusColors[status] || statusColors.pending;
    return `<span class="inline-flex items-center px-2 py-0.5 rounded border text-[9px] font-bold uppercase tracking-widest ${c}">${status}</span>`;
  }

  function money(amount, currency) {
    const c = currency || 'BDT';
    return `<span class="font-mono text-dc-textBright">৳${Number(amount || 0).toLocaleString()}</span>`;
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: '2-digit' });
  }

  function toast(msg, type) {
    if (window.TOC?.toast) window.TOC.toast(msg, type);
  }

  /* ─── S5: Inline proof thumbnail helper ────────────────────── */
  function proofThumb(url) {
    if (!url) return `<span class="text-[10px] text-dc-text/40">—</span>`;
    const isPdf = url.toLowerCase().endsWith('.pdf');
    if (isPdf) {
      return `<button onclick="TOC.payments.viewProof('${url}')" class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-dc-info/10 border border-dc-info/20 text-dc-info hover:bg-dc-info/20 transition-colors" title="View PDF proof">
        <i data-lucide="file-text" class="w-3 h-3"></i><span class="text-[9px] font-bold">PDF</span>
      </button>`;
    }
    return `<button onclick="TOC.payments.viewProof('${url}')" class="group/proof relative" title="Click to enlarge">
      <img src="${url}" alt="Proof" class="w-10 h-10 object-cover rounded border border-dc-border group-hover/proof:border-theme transition-colors" loading="lazy" onerror="this.parentElement.innerHTML='<span class=\\'text-[10px] text-dc-text/40\\'>err</span>'">
    </button>`;
  }

  /* ─── S5: Custom reject modal ──────────────────────────────── */
  function promptRejectReason() {
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'fixed inset-0 z-[120] flex items-center justify-center';
      overlay.innerHTML = `
        <div class="absolute inset-0 bg-black/80 backdrop-blur-md" data-dismiss></div>
        <div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-md relative z-10 overflow-hidden">
          <div class="h-1 w-full bg-dc-danger"></div>
          <div class="p-6">
            <h3 class="font-display font-black text-lg text-white mb-1">Reject Payment</h3>
            <p class="text-xs text-dc-text mb-4">Provide a reason for rejection. The participant will be notified.</p>
            <textarea id="reject-reason-input" rows="3" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-dc-danger focus:ring-1 focus:ring-dc-danger/40 outline-none resize-none placeholder-dc-text/50" placeholder="e.g. Blurry screenshot, wrong amount, duplicate submission…" autofocus></textarea>
            <div class="flex items-center justify-end gap-2 mt-4">
              <button data-dismiss class="px-4 py-2 text-xs font-bold text-dc-text hover:text-white transition-colors">Cancel</button>
              <button id="reject-confirm-btn" class="px-4 py-2 bg-dc-danger/20 text-dc-danger border border-dc-danger/30 text-xs font-black uppercase tracking-widest rounded-lg hover:bg-dc-danger/30 transition-colors">Reject</button>
            </div>
          </div>
        </div>`;

      function cleanup(value) { overlay.remove(); resolve(value); }

      overlay.querySelectorAll('[data-dismiss]').forEach(el =>
        el.addEventListener('click', () => cleanup(null))
      );
      overlay.querySelector('#reject-confirm-btn').addEventListener('click', () => {
        const val = overlay.querySelector('#reject-reason-input').value.trim();
        cleanup(val || null);
      });
      // Enter submits, Escape cancels
      overlay.querySelector('#reject-reason-input').addEventListener('keydown', (e) => {
        if (e.key === 'Escape') cleanup(null);
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          const val = overlay.querySelector('#reject-reason-input').value.trim();
          cleanup(val || null);
        }
      });

      document.body.appendChild(overlay);
      // Auto-focus the textarea after append
      requestAnimationFrame(() => overlay.querySelector('#reject-reason-input')?.focus());
    });
  }

  /* ─── S5: Auto-advance — highlight next pending row ────────── */
  function highlightNextPending(removedId) {
    // Clear any existing highlights
    $$('.pay-row-highlight').forEach(el => el.classList.remove('pay-row-highlight', 'ring-2', 'ring-theme/50'));

    const next = currentRows.find(r =>
      String(r.id) !== String(removedId) && (r.status === 'pending' || r.status === 'submitted')
    );
    if (!next) return;

    const row = $(`#payments-tbody tr[data-id="${next.id}"]`);
    if (row) {
      row.classList.add('pay-row-highlight', 'ring-2', 'ring-theme/50');
      row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      // Auto-clear highlight after 3s
      setTimeout(() => row.classList.remove('pay-row-highlight', 'ring-2', 'ring-theme/50'), 3000);
    }
  }

  /* ─── Revenue summary cards (S4-F4) ──────────────────────── */
  async function refreshRevenue() {
    try {
      const data = await API.get('payments/summary/');
      renderRevenueCards(data);
    } catch (e) {
      console.error('[payments] revenue fetch error', e);
    }
  }

  function renderRevenueCards(d) {
    const container = $('#revenue-cards');
    if (!container) return;

    const cards = [
      { label: 'Total Revenue',  value: d.total_amount,    count: d.total_count,    icon: 'wallet',       color: 'text-theme' },
      { label: 'Verified',       value: d.verified_amount, count: d.verified_count,  icon: 'check-circle', color: 'text-dc-success' },
      { label: 'Pending',        value: d.pending_amount,  count: d.pending_count,   icon: 'clock',        color: 'text-dc-warning' },
      { label: 'Refunded',       value: d.refunded_amount, count: d.refunded_count,  icon: 'undo-2',       color: 'text-dc-danger' },
    ];

    container.innerHTML = cards.map(c => `
      <div class="glass-box rounded-xl p-5 hover:border-dc-borderLight transition-colors group">
        <div class="flex items-start justify-between mb-4">
          <p class="text-[9px] font-bold text-dc-text uppercase tracking-widest">${c.label}</p>
          <div class="w-9 h-9 bg-dc-bg border border-dc-border rounded-xl flex items-center justify-center group-hover:border-dc-borderLight transition-colors">
            <i data-lucide="${c.icon}" class="w-4 h-4 ${c.color}"></i>
          </div>
        </div>
        <p class="font-mono font-black text-2xl text-white mb-1">৳${Number(c.value || 0).toLocaleString()}</p>
        <p class="text-[10px] text-dc-text font-mono">${c.count || 0} payment${(c.count||0) === 1 ? '' : 's'}</p>
      </div>
    `).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* ─── Payment list (S4-F1 / S4-F3 + S5 optimistic state) ──── */
  async function refresh() {
    const status = $('#pay-filter-status')?.value || '';
    const method = $('#pay-filter-method')?.value || '';
    const search = $('#pay-filter-search')?.value || '';

    try {
      const qs = new URLSearchParams({ page: currentPage, page_size: pageSize });
      if (status) qs.set('status', status);
      if (method) qs.set('method', method);
      if (search) qs.set('search', search);

      const data = await API.get(`payments/?${qs}`);
      currentRows = data.results || [];       // S5: cache locally
      _lastPaginationData = data;              // S5: cache pagination
      renderPayments(data);
    } catch (e) {
      console.error('[payments] list fetch error', e);
    }
  }

  function renderPayments(data) {
    const tbody = $('#payments-tbody');
    if (!tbody) return;

    const rows = data.results || [];
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="9" class="px-6 py-16 text-center text-dc-text text-sm">No payments found</td></tr>`;
      renderPagination(data);
      return;
    }

    tbody.innerHTML = rows.map(p => {
      const isCheckable = ['pending', 'submitted'].includes(p.status);
      const checked = selectedIds.has(p.id) ? 'checked' : '';
      return `
        <tr class="border-b border-dc-border/50 hover:bg-white/[0.015] transition-all group" data-id="${p.id}" data-status="${p.status}">
          <td class="px-3 py-3">
            ${isCheckable ? `<input type="checkbox" class="toc-checkbox pay-row-cb" data-id="${p.id}" ${checked} onclick="TOC.payments.toggleRow('${p.id}', this)">` : ''}
          </td>
          <td class="px-3 py-3">
            <p class="text-dc-textBright font-semibold text-xs leading-tight">${p.participant_name || 'Unknown'}</p>
            <p class="text-[10px] text-dc-text font-mono mt-0.5">${p.team_name || ''}</p>
          </td>
          <td class="px-3 py-3 text-right font-mono text-dc-textBright font-bold">${money(p.amount, p.currency)}</td>
          <td class="px-3 py-3">
            <span class="text-[10px] font-bold uppercase text-dc-text">${(p.method || '—').replace('_', ' ')}</span>
          </td>
          <td class="px-3 py-3">
            <span class="text-[10px] font-mono text-dc-text">${p.transaction_id || '—'}</span>
          </td>
          <td class="px-3 py-3">${badge(p.status)}</td>
          <td class="px-3 py-3 text-center">${proofThumb(p.proof_url)}</td>
          <td class="px-3 py-3 text-[10px] text-dc-text font-mono">${fmtDate(p.submitted_at)}</td>
          <td class="px-3 py-3 text-right">
            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              ${p.status === 'submitted' || p.status === 'pending' ? `
                <button onclick="TOC.payments.verify('${p.id}')" title="Verify" data-cap-require="approve_payments" class="w-7 h-7 rounded-lg bg-dc-success/10 text-dc-success border border-dc-success/20 flex items-center justify-center hover:bg-dc-success/20 transition-colors"><i data-lucide="check" class="w-3 h-3"></i></button>
                <button onclick="TOC.payments.reject('${p.id}')" title="Reject" data-cap-require="approve_payments" class="w-7 h-7 rounded-lg bg-dc-danger/10 text-dc-danger border border-dc-danger/20 flex items-center justify-center hover:bg-dc-danger/20 transition-colors"><i data-lucide="x" class="w-3 h-3"></i></button>
              ` : ''}
              ${p.status === 'verified' ? `
                <button onclick="TOC.payments.openRefund('${p.id}', '${(p.participant_name||'').replace(/'/g,'')}', '${p.amount}')" title="Refund" data-cap-require="approve_payments" class="w-7 h-7 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center justify-center hover:bg-purple-500/20 transition-colors"><i data-lucide="undo-2" class="w-3 h-3"></i></button>
              ` : ''}
            </div>
          </td>
        </tr>`;
    }).join('');

    renderPagination(data);
    updateBulkBar();
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function renderPagination(data) {
    const info = $('#pay-pagination-info');
    const controls = $('#pay-pagination-controls');
    if (!info || !controls) return;

    const total = data.total || 0;
    const pages = data.pages || Math.ceil(total / pageSize) || 1;
    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, total);

    info.textContent = total > 0 ? `${start}–${end} of ${total}` : 'No results';

    let html = '';
    if (currentPage > 1) {
      html += `<button onclick="TOC.payments.goPage(${currentPage - 1})" class="w-7 h-7 rounded bg-dc-panel border border-dc-border text-dc-text hover:text-white flex items-center justify-center"><i data-lucide="chevron-left" class="w-3 h-3"></i></button>`;
    }
    for (let i = 1; i <= pages && i <= 5; i++) {
      const active = i === currentPage ? 'bg-theme/10 text-theme border-theme/20' : 'bg-dc-panel text-dc-text border-dc-border hover:text-white';
      html += `<button onclick="TOC.payments.goPage(${i})" class="w-7 h-7 rounded border text-[10px] font-bold flex items-center justify-center ${active}">${i}</button>`;
    }
    if (currentPage < pages) {
      html += `<button onclick="TOC.payments.goPage(${currentPage + 1})" class="w-7 h-7 rounded bg-dc-panel border border-dc-border text-dc-text hover:text-white flex items-center justify-center"><i data-lucide="chevron-right" class="w-3 h-3"></i></button>`;
    }
    controls.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function goPage(p) {
    currentPage = p;
    refresh();
  }

  /* ─── Row selection & bulk ─────────────────────────────────── */
  function toggleRow(id, cb) {
    if (cb.checked) selectedIds.add(id); else selectedIds.delete(id);
    updateBulkBar();
  }

  function toggleSelectAll(cb) {
    $$('.pay-row-cb').forEach(el => {
      el.checked = cb.checked;
      if (cb.checked) selectedIds.add(el.dataset.id); else selectedIds.delete(el.dataset.id);
    });
    updateBulkBar();
  }

  function updateBulkBar() {
    const bar = $('#pay-bulk-bar');
    const cnt = $('#pay-bulk-count');
    if (!bar) return;
    if (selectedIds.size > 0) {
      bar.classList.remove('hidden');
      bar.classList.add('flex');
      if (cnt) cnt.textContent = `${selectedIds.size} selected`;
    } else {
      bar.classList.add('hidden');
      bar.classList.remove('flex');
    }
  }

  /* ─── Payment actions (S4-F3 + S5 optimistic ops) ───────────── */

  /** S5: Optimistic splice-out with slide animation + auto-advance */
  async function verify(id) {
    // Optimistic: slide row out immediately
    const row = $(`#payments-tbody tr[data-id="${id}"]`);
    if (row) {
      row.style.transition = 'opacity 0.25s ease, transform 0.25s ease, max-height 0.3s ease';
      row.style.opacity = '0';
      row.style.transform = 'translateX(40px)';
      row.style.maxHeight = row.offsetHeight + 'px';
      row.style.overflow = 'hidden';
      setTimeout(() => { row.style.maxHeight = '0'; row.style.padding = '0'; }, 150);
    }

    try {
      await API.post(`payments/${id}/verify/`);
      toast('Payment verified', 'success');
      // Splice from local state
      selectedIds.delete(id);
      currentRows = currentRows.filter(r => String(r.id) !== String(id));
      // Remove DOM row after animation
      setTimeout(() => { if (row) row.remove(); }, 350);
      // Auto-advance to next pending
      highlightNextPending(id);
      refreshRevenue();
    } catch (e) {
      toast(e.message || 'Verify failed', 'error');
      // Rollback: restore row visibility
      if (row) {
        row.style.transition = 'opacity 0.15s ease, transform 0.15s ease, max-height 0.15s ease';
        row.style.opacity = '1';
        row.style.transform = 'translateX(0)';
        row.style.maxHeight = '';
        row.style.overflow = '';
        row.style.padding = '';
      }
    }
  }

  /** S5: Custom reject modal (replaces native prompt) */
  async function reject(id) {
    const reason = await promptRejectReason();
    if (!reason) return;

    // Optimistic: fade row out
    const row = $(`#payments-tbody tr[data-id="${id}"]`);
    if (row) {
      row.style.transition = 'opacity 0.25s ease, transform 0.25s ease, max-height 0.3s ease';
      row.style.opacity = '0';
      row.style.transform = 'translateX(-40px)';
      row.style.maxHeight = row.offsetHeight + 'px';
      row.style.overflow = 'hidden';
      setTimeout(() => { row.style.maxHeight = '0'; row.style.padding = '0'; }, 150);
    }

    try {
      await API.post(`payments/${id}/reject/`, { reason });
      toast('Payment rejected', 'info');
      selectedIds.delete(id);
      currentRows = currentRows.filter(r => String(r.id) !== String(id));
      setTimeout(() => { if (row) row.remove(); }, 350);
      highlightNextPending(id);
      refreshRevenue();
    } catch (e) {
      toast(e.message || 'Reject failed', 'error');
      if (row) {
        row.style.transition = 'opacity 0.15s ease';
        row.style.opacity = '1';
        row.style.transform = 'translateX(0)';
        row.style.maxHeight = '';
        row.style.overflow = '';
        row.style.padding = '';
      }
    }
  }

  async function bulkVerify() {
    if (!selectedIds.size) return;
    const ids = Array.from(selectedIds);
    try {
      await API.post('payments/bulk-verify/', { ids: ids });
      toast(`${ids.length} payments verified`, 'success');
      // Optimistic: remove all verified rows
      ids.forEach(id => {
        const row = $(`#payments-tbody tr[data-id="${id}"]`);
        if (row) {
          row.style.transition = 'opacity 0.2s ease';
          row.style.opacity = '0';
          setTimeout(() => row.remove(), 250);
        }
      });
      currentRows = currentRows.filter(r => !ids.includes(String(r.id)) && !ids.includes(r.id));
      selectedIds.clear();
      updateBulkBar();
      refreshRevenue();
    } catch (e) {
      toast(e.message || 'Bulk verify failed', 'error');
    }
  }

  /* ─── Refund modal (S4-F6) ─────────────────────────────────── */
  function openRefund(id, name, amount) {
    $('#refund-payment-id').value = id;
    $('#refund-modal-info').textContent = `Refund ৳${Number(amount).toLocaleString()} to ${name}`;
    $('#refund-reason').value = '';
    $('#modal-refund').classList.remove('hidden');
  }

  async function confirmRefund() {
    const id = $('#refund-payment-id').value;
    const reason = $('#refund-reason').value.trim();
    if (!reason) { toast('Reason is required', 'error'); return; }
    try {
      await API.post(`payments/${id}/refund/`, { reason });
      toast('Refund processed', 'success');
      $('#modal-refund').classList.add('hidden');
      refresh();
      refreshRevenue();
    } catch (e) {
      toast(e.message || 'Refund failed', 'error');
    }
  }

  /* ─── Proof viewer (S4-F2) ─────────────────────────────────── */
  function viewProof(url) {
    // Open in a new lightbox overlay
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 z-[120] flex items-center justify-center bg-black/90 backdrop-blur-md cursor-pointer';
    overlay.onclick = () => overlay.remove();

    if (url.toLowerCase().endsWith('.pdf')) {
      overlay.innerHTML = `<iframe src="${url}" class="w-[90vw] h-[90vh] rounded-xl border border-dc-borderLight"></iframe>`;
    } else {
      overlay.innerHTML = `<img src="${url}" class="max-w-[90vw] max-h-[90vh] rounded-xl border border-dc-borderLight shadow-2xl" alt="Payment proof">`;
    }
    document.body.appendChild(overlay);
  }

  /* ─── CSV export ────────────────────────────────────────────── */
  async function exportCSV() {
    try {
      const res = await API.getRaw('payments/export/');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `payments_${slug}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast('Export downloaded', 'success');
    } catch (e) {
      // Fallback: open in new tab
      window.open(`/api/toc/${slug}/payments/export/`, '_blank');
    }
  }

  /* ─── Prize Distribution (S4-F5) ───────────────────────────── */
  async function refreshPrizePool() {
    try {
      const data = await API.get('prize-pool/');
      renderPrizePool(data);
    } catch (e) {
      console.error('[payments] prize-pool error', e);
      $('#prize-pool-panel').innerHTML = `<p class="text-dc-text text-sm text-center py-8">Unable to load prize pool data</p>`;
    }
  }

  function renderPrizePool(d) {
    const container = $('#prize-pool-panel');
    if (!container) return;

    const placements = d.placement_amounts || {};
    const placementRows = Object.entries(placements).map(([k, v]) => {
      const ordinal = k === '1' ? '1st' : k === '2' ? '2nd' : k === '3' ? '3rd' : `${k}th`;
      const barPct = d.net_distributable > 0 ? ((v / d.net_distributable) * 100) : 0;
      return `
        <div class="flex items-center gap-3 group">
          <span class="text-[10px] font-bold text-dc-text uppercase w-10 shrink-0">${ordinal}</span>
          <div class="flex-1 bg-dc-bg rounded-full h-3 overflow-hidden border border-dc-border">
            <div class="h-full rounded-full ${k === '1' ? 'bg-dc-warning' : k === '2' ? 'bg-dc-text' : 'bg-dc-warning/40'}" style="width: ${barPct}%"></div>
          </div>
          <span class="text-xs font-mono font-bold text-dc-textBright w-20 text-right">৳${Number(v).toLocaleString()}</span>
        </div>`;
    }).join('');

    container.innerHTML = `
      <div class="grid grid-cols-2 gap-4 mb-4">
        <div class="bg-dc-bg border border-dc-border rounded-lg p-3 text-center">
          <p class="text-[9px] font-bold text-dc-text uppercase tracking-widest mb-1">Gross Pool</p>
          <p class="font-mono font-black text-lg text-white">৳${Number(d.gross_prize_pool || 0).toLocaleString()}</p>
        </div>
        <div class="bg-dc-bg border border-dc-border rounded-lg p-3 text-center">
          <p class="text-[9px] font-bold text-dc-text uppercase tracking-widest mb-1">Net Distributable</p>
          <p class="font-mono font-black text-lg text-dc-success">৳${Number(d.net_distributable || 0).toLocaleString()}</p>
        </div>
      </div>

      <div class="flex flex-wrap gap-3 mb-4">
        <div class="bg-dc-panel border border-dc-border rounded-lg px-3 py-2 text-center flex-1">
          <p class="text-[9px] text-dc-text font-bold uppercase">Platform Fee</p>
          <p class="font-mono text-xs text-dc-textBright">৳${Number(d.platform_fee || 0).toLocaleString()}</p>
        </div>
        <div class="bg-dc-panel border border-dc-border rounded-lg px-3 py-2 text-center flex-1">
          <p class="text-[9px] text-dc-text font-bold uppercase">Organizer Fee</p>
          <p class="font-mono text-xs text-dc-textBright">৳${Number(d.organizer_fee || 0).toLocaleString()}</p>
        </div>
        <div class="bg-dc-panel border border-dc-border rounded-lg px-3 py-2 text-center flex-1">
          <p class="text-[9px] text-dc-text font-bold uppercase">Bounties</p>
          <p class="font-mono text-xs text-dc-warning">৳${Number(d.bounty_total || 0).toLocaleString()}</p>
        </div>
      </div>

      ${placementRows ? `<div class="space-y-2">${placementRows}</div>` : '<p class="text-dc-text text-xs text-center">No prize distribution configured</p>'}
    `;
  }

  /* ─── Bounties (S4-F7) ─────────────────────────────────────── */
  async function refreshBounties() {
    try {
      const data = await API.get('bounties/');
      renderBounties(data.results || data);
    } catch (e) {
      console.error('[payments] bounties error', e);
    }
  }

  function renderBounties(list) {
    const container = $('#bounties-panel');
    const counter = $('#bounty-count');
    if (!container) return;

    if (counter) {
      counter.textContent = list.length;
      counter.classList.toggle('hidden', list.length === 0);
    }

    if (!list.length) {
      container.innerHTML = `
        <div class="flex flex-col items-center justify-center py-8 text-center">
          <i data-lucide="target" class="w-10 h-10 text-dc-text/20 mb-3"></i>
          <p class="text-sm text-dc-text">No bounties yet</p>
          <p class="text-[10px] text-dc-text/60 mt-1">Create custom bounties to reward exceptional plays</p>
        </div>`;
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    container.innerHTML = list.map(b => `
      <div class="bg-dc-bg border border-dc-border rounded-xl p-4 hover:border-dc-borderLight transition-colors group">
        <div class="flex items-start justify-between mb-2">
          <div>
            <h4 class="text-sm font-bold text-white leading-tight">${b.name}</h4>
            <span class="text-[9px] font-bold uppercase tracking-widest text-dc-text">${bountyTypeLabels[b.bounty_type] || b.bounty_type}</span>
          </div>
          <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            ${!b.is_assigned ? `
              <button onclick="TOC.payments.openAssignBounty('${b.id}')" title="Assign winner" class="w-7 h-7 rounded-lg bg-dc-success/10 text-dc-success border border-dc-success/20 flex items-center justify-center hover:bg-dc-success/20 transition-colors"><i data-lucide="user-check" class="w-3 h-3"></i></button>
              <button onclick="TOC.payments.deleteBounty('${b.id}')" title="Delete" class="w-7 h-7 rounded-lg bg-dc-danger/10 text-dc-danger border border-dc-danger/20 flex items-center justify-center hover:bg-dc-danger/20 transition-colors"><i data-lucide="trash-2" class="w-3 h-3"></i></button>
            ` : `
              <span class="text-[9px] font-bold text-dc-success uppercase">Assigned</span>
            `}
          </div>
        </div>
        ${b.description ? `<p class="text-[10px] text-dc-text line-clamp-2 mb-2">${b.description}</p>` : ''}
        <div class="flex items-center justify-between mt-2">
          <span class="font-mono font-bold text-theme">${money(b.prize_amount, b.prize_currency)}</span>
          <div class="flex items-center gap-2">
            <span class="text-[9px] text-dc-text uppercase">${b.source || ''}</span>
            ${b.is_assigned && b.assigned_to_name ? `<span class="text-[10px] text-dc-textBright font-semibold">→ ${b.assigned_to_name}</span>` : ''}
          </div>
        </div>
      </div>
    `).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function openCreateBountyDrawer() {
    const html = `
      <div class="p-6 space-y-4">
        <h3 class="font-display font-black text-lg text-white mb-1">Create Bounty</h3>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Name</label>
          <input id="bounty-name" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none" placeholder="e.g. MVP Award">
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Type</label>
          <select id="bounty-type" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
            <option value="mvp">MVP</option>
            <option value="stat_leader">Stat Leader</option>
            <option value="community_vote">Community Vote</option>
            <option value="special_achievement">Special Achievement</option>
            <option value="custom">Custom</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Amount</label>
            <input id="bounty-amount" type="number" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none" placeholder="0">
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Source</label>
            <select id="bounty-source" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
              <option value="prize_pool">Prize Pool</option>
              <option value="sponsor">Sponsor</option>
              <option value="platform">Platform</option>
            </select>
          </div>
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Description</label>
          <textarea id="bounty-desc" rows="2" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none" placeholder="Optional description..."></textarea>
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Sponsor Name <span class="text-dc-text/40">(if applicable)</span></label>
          <input id="bounty-sponsor" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none" placeholder="Sponsor name">
        </div>
        <button onclick="TOC.payments.confirmCreateBounty()" class="w-full py-2.5 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity mt-2">Create Bounty</button>
      </div>`;

    if (window.TOC?.openDrawer) {
      window.TOC.openDrawer(html);
    } else {
      // fallback: inline modal
      const modal = document.createElement('div');
      modal.id = 'bounty-create-overlay';
      modal.className = 'fixed inset-0 z-[110] flex items-center justify-center';
      modal.innerHTML = `
        <div class="absolute inset-0 bg-black/80 backdrop-blur-md" onclick="document.getElementById('bounty-create-overlay').remove()"></div>
        <div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-md relative z-10 overflow-hidden">
          <div class="h-1 w-full bg-theme"></div>
          ${html}
        </div>`;
      document.body.appendChild(modal);
    }
  }

  async function confirmCreateBounty() {
    const name = $('#bounty-name')?.value?.trim();
    const bounty_type = $('#bounty-type')?.value;
    const prize_amount = parseFloat($('#bounty-amount')?.value) || 0;
    const source = $('#bounty-source')?.value;
    const description = $('#bounty-desc')?.value?.trim() || '';
    const sponsor_name = $('#bounty-sponsor')?.value?.trim() || '';

    if (!name) { toast('Name is required', 'error'); return; }
    if (prize_amount <= 0) { toast('Amount must be positive', 'error'); return; }

    try {
      await API.post('bounties/', { name, bounty_type, prize_amount, source, description, sponsor_name });
      toast('Bounty created', 'success');
      // Close drawer / overlay
      if (window.TOC?.closeDrawer) window.TOC.closeDrawer();
      const overlay = document.getElementById('bounty-create-overlay');
      if (overlay) overlay.remove();
      refreshBounties();
      refreshPrizePool();
    } catch (e) {
      toast(e.message || 'Create failed', 'error');
    }
  }

  function openAssignBounty(bountyId) {
    const FIELD = 'w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none';
    const body = `<div class="space-y-4 p-5">
      <div>
        <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Registration ID *</label>
        <input id="assign-reg-id" type="text" class="${FIELD}" placeholder="e.g. 42"></div>
      <div>
        <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Reason <span class="text-dc-text/40">(optional)</span></label>
        <input id="assign-reg-reason" type="text" class="${FIELD}" placeholder="e.g. Tournament MVP"></div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button onclick="TOC.payments._submitAssignBounty('${bountyId}')" class="flex-1 bg-theme hover:opacity-90 text-dc-bg text-xs font-black uppercase tracking-widest py-2 rounded-lg transition">Assign Bounty</button>
      <button onclick="TOC.drawer.close()" class="text-dc-text text-xs py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Assign Bounty', body, footer);
    setTimeout(() => document.getElementById('assign-reg-id')?.focus(), 50);
  }

  function _submitAssignBounty(bountyId) {
    const registrationId = document.getElementById('assign-reg-id')?.value.trim();
    const reason = document.getElementById('assign-reg-reason')?.value.trim() || '';
    if (!registrationId) { TOC.toast('Registration ID is required', 'error'); return; }
    TOC.drawer.close();
    assignBounty(bountyId, registrationId, reason);
  }

  async function assignBounty(bountyId, registrationId, reason) {
    try {
      await API.post(`bounties/${bountyId}/assign/`, {
        registration_id: registrationId,
        reason: reason,
      });
      toast('Bounty assigned', 'success');
      refreshBounties();
    } catch (e) {
      toast(e.message || 'Assign failed', 'error');
    }
  }

  async function deleteBounty(bountyId) {
    if (!confirm('Delete this bounty?')) return;
    try {
      await API.delete(`bounties/${bountyId}/`);
      toast('Bounty deleted', 'success');
      refreshBounties();
      refreshPrizePool();
    } catch (e) {
      toast(e.message || 'Delete failed', 'error');
    }
  }

  /* ─── Search debounce ──────────────────────────────────────── */
  function _searchDebounce() {
    clearTimeout(_searchTimer);
    _searchTimer = setTimeout(() => { currentPage = 1; refresh(); }, 350);
  }

  /* ─── Smart Quick Verify ──────────────────────────────────── */
  let _qvTimer = null;
  let _qvCurrentPayment = null;

  function _qvDebounce() {
    clearTimeout(_qvTimer);
    _qvTimer = setTimeout(() => qvSearch(), 400);
  }

  async function qvSearch() {
    const input = $('#qv-input');
    const resultBox = $('#qv-result');
    const query = (input?.value || '').trim();

    if (!query || query.length < 3) {
      if (resultBox) { resultBox.classList.add('hidden'); resultBox.innerHTML = ''; }
      _qvCurrentPayment = null;
      return;
    }

    try {
      // Use the existing payments API with search — it already supports txn_id and phone lookup
      const qs = new URLSearchParams({ search: query, page_size: 5 });
      const data = await API.get(`payments/?${qs}`);
      const matches = (data.results || []).filter(p =>
        p.status === 'pending' || p.status === 'submitted'
      );

      if (!resultBox) return;
      resultBox.classList.remove('hidden');

      if (!matches.length) {
        _qvCurrentPayment = null;
        resultBox.innerHTML = `
          <div class="bg-dc-bg border border-dc-border rounded-xl p-4 flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-dc-danger/10 border border-dc-danger/20 flex items-center justify-center shrink-0">
              <i data-lucide="search-x" class="w-5 h-5 text-dc-danger"></i>
            </div>
            <div>
              <p class="text-xs font-bold text-dc-textBright">No pending payment found</p>
              <p class="text-[10px] text-dc-text mt-0.5">No unverified payment matches "<span class="text-dc-textBright font-mono">${query}</span>". Check the ID or number and try again.</p>
            </div>
          </div>`;
        if (typeof lucide !== 'undefined') lucide.createIcons();
        return;
      }

      // If only one match, auto-select it
      if (matches.length === 1) {
        _qvCurrentPayment = matches[0];
        renderQvCard(matches[0], resultBox);
      } else {
        // Multiple matches — show a picker
        _qvCurrentPayment = null;
        resultBox.innerHTML = `
          <div class="bg-dc-bg border border-dc-border rounded-xl overflow-hidden">
            <div class="px-4 py-2 border-b border-dc-border/50 bg-dc-panel/30">
              <p class="text-[10px] font-bold text-dc-text uppercase tracking-widest">${matches.length} pending matches found — select one</p>
            </div>
            <div class="divide-y divide-dc-border/30 max-h-[200px] overflow-y-auto">
              ${matches.map(p => `
                <button onclick="TOC.payments._qvSelect(${p.id})" class="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors text-left">
                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-bold text-dc-textBright truncate">${p.participant_name || 'Unknown'}</p>
                    <p class="text-[10px] text-dc-text font-mono">${p.transaction_id || '—'} · ${(p.method || '—').replace('_', ' ')}</p>
                  </div>
                  <div class="text-right shrink-0">
                    ${money(p.amount, p.currency)}
                    <div class="mt-0.5">${badge(p.status)}</div>
                  </div>
                </button>
              `).join('')}
            </div>
          </div>`;
      }

      if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (e) {
      console.error('[payments] quick verify search error', e);
      toast('Lookup failed', 'error');
    }
  }

  function _qvSelect(paymentId) {
    // Find from last search results by re-fetching (we don't cache multi-match)
    // Instead just call the single API with that id's search
    const match = currentRows.find(r => r.id === paymentId || String(r.id) === String(paymentId));
    if (match) {
      _qvCurrentPayment = match;
      const resultBox = $('#qv-result');
      if (resultBox) renderQvCard(match, resultBox);
      return;
    }
    // Fallback: search again by ID
    API.get(`payments/?search=${paymentId}&page_size=1`).then(data => {
      const p = (data.results || [])[0];
      if (p) {
        _qvCurrentPayment = p;
        const resultBox = $('#qv-result');
        if (resultBox) renderQvCard(p, resultBox);
      }
    });
  }

  function renderQvCard(p, container) {
    const proofHtml = p.proof_url
      ? (p.proof_url.toLowerCase().endsWith('.pdf')
          ? `<div class="w-full bg-dc-bg rounded-xl border border-dc-border p-4 flex flex-col items-center gap-2">
               <i data-lucide="file-text" class="w-8 h-8 text-dc-info"></i>
               <a href="${p.proof_url}" target="_blank" class="text-xs text-dc-info underline">View PDF Proof</a>
             </div>`
          : `<div class="relative group/qvproof">
               <img src="${p.proof_url}" alt="Payment proof" class="w-full max-h-[280px] object-contain rounded-xl border border-dc-border bg-dc-bg cursor-pointer"
                    onclick="TOC.payments.viewProof('${p.proof_url}')" loading="lazy"
                    onerror="this.parentElement.innerHTML='<p class=\\'text-[10px] text-dc-text/40 text-center py-4\\'>Failed to load proof image</p>'">
               <div class="absolute top-2 right-2 opacity-0 group-hover/qvproof:opacity-100 transition-opacity">
                 <button onclick="TOC.payments.viewProof('${p.proof_url}')" class="w-7 h-7 rounded-lg bg-black/60 backdrop-blur text-white flex items-center justify-center hover:bg-black/80 transition-colors" title="Enlarge">
                   <i data-lucide="maximize-2" class="w-3.5 h-3.5"></i>
                 </button>
               </div>
             </div>`)
      : `<div class="w-full bg-dc-bg rounded-xl border border-dc-border p-6 flex flex-col items-center gap-2">
           <i data-lucide="image-off" class="w-8 h-8 text-dc-text/20"></i>
           <p class="text-[10px] text-dc-text/50">No proof submitted</p>
         </div>`;

    container.innerHTML = `
      <div class="bg-dc-bg border border-dc-border rounded-xl overflow-hidden">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-0">
          <div class="p-5 space-y-4 border-r border-dc-border/50">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-sm font-bold text-white">${p.participant_name || 'Unknown'}</p>
                <p class="text-[10px] text-dc-text font-mono mt-0.5">${p.username || ''}</p>
              </div>
              ${badge(p.status)}
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div class="bg-dc-panel/50 border border-dc-border/50 rounded-lg p-2.5">
                <p class="text-[8px] font-bold text-dc-text uppercase tracking-widest">Amount</p>
                <p class="font-mono font-bold text-base text-white mt-0.5">৳${Number(p.amount || 0).toLocaleString()}</p>
              </div>
              <div class="bg-dc-panel/50 border border-dc-border/50 rounded-lg p-2.5">
                <p class="text-[8px] font-bold text-dc-text uppercase tracking-widest">Method</p>
                <p class="text-xs font-bold text-dc-textBright mt-0.5 uppercase">${(p.method || '—').replace('_', ' ')}</p>
              </div>
            </div>

            <div class="space-y-2">
              <div class="flex items-center justify-between py-1.5 border-b border-dc-border/30">
                <span class="text-[9px] font-bold text-dc-text uppercase tracking-widest">TXN ID</span>
                <span class="text-xs font-mono text-dc-textBright">${p.transaction_id || '—'}</span>
              </div>
              <div class="flex items-center justify-between py-1.5 border-b border-dc-border/30">
                <span class="text-[9px] font-bold text-dc-text uppercase tracking-widest">Reg #</span>
                <span class="text-xs font-mono text-dc-textBright">${p.registration_number || '—'}</span>
              </div>
              <div class="flex items-center justify-between py-1.5 border-b border-dc-border/30">
                <span class="text-[9px] font-bold text-dc-text uppercase tracking-widest">Submitted</span>
                <span class="text-xs font-mono text-dc-text">${fmtDate(p.submitted_at)}</span>
              </div>
              ${p.payer_account_number ? `
              <div class="flex items-center justify-between py-1.5 border-b border-dc-border/30">
                <span class="text-[9px] font-bold text-dc-text uppercase tracking-widest">Sender #</span>
                <span class="text-xs font-mono text-dc-textBright">${p.payer_account_number}</span>
              </div>` : ''}
            </div>

            <div class="flex items-center gap-2 pt-2">
              <button onclick="TOC.payments.qvVerify()" data-cap-require="approve_payments" class="flex-1 py-2.5 bg-dc-success/10 border border-dc-success/20 text-dc-success text-xs font-black uppercase tracking-widest rounded-lg hover:bg-dc-success/20 transition-colors flex items-center justify-center gap-2">
                <i data-lucide="check-circle" class="w-4 h-4"></i> Verify
              </button>
              <button onclick="TOC.payments.qvReject()" data-cap-require="approve_payments" class="flex-1 py-2.5 bg-dc-danger/10 border border-dc-danger/20 text-dc-danger text-xs font-black uppercase tracking-widest rounded-lg hover:bg-dc-danger/20 transition-colors flex items-center justify-center gap-2">
                <i data-lucide="x-circle" class="w-4 h-4"></i> Reject
              </button>
            </div>
          </div>

          <div class="p-5 flex flex-col">
            <p class="text-[9px] font-bold text-dc-text uppercase tracking-widest mb-3">Payment Proof</p>
            ${proofHtml}
          </div>
        </div>
      </div>`;

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /** Quick Verify — verify the currently selected payment */
  async function qvVerify() {
    if (!_qvCurrentPayment) { toast('No payment selected', 'error'); return; }
    const id = _qvCurrentPayment.id;

    try {
      await API.post(`payments/${id}/verify/`);
      toast(`Payment #${_qvCurrentPayment.registration_number || id} verified`, 'success');

      // Reset quick verify panel
      _qvCurrentPayment = null;
      const input = $('#qv-input');
      const resultBox = $('#qv-result');
      if (input) { input.value = ''; input.focus(); }
      if (resultBox) { resultBox.classList.add('hidden'); resultBox.innerHTML = ''; }

      // Splice from table if visible
      currentRows = currentRows.filter(r => String(r.id) !== String(id));
      const row = $(`#payments-tbody tr[data-id="${id}"]`);
      if (row) {
        row.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
        row.style.opacity = '0';
        row.style.transform = 'translateX(40px)';
        setTimeout(() => row.remove(), 300);
      }

      refreshRevenue();
    } catch (e) {
      toast(e.message || 'Verify failed', 'error');
    }
  }

  /** Quick Verify — reject the currently selected payment */
  async function qvReject() {
    if (!_qvCurrentPayment) { toast('No payment selected', 'error'); return; }
    const id = _qvCurrentPayment.id;
    const reason = await promptRejectReason();
    if (!reason) return;

    try {
      await API.post(`payments/${id}/reject/`, { reason });
      toast(`Payment #${_qvCurrentPayment.registration_number || id} rejected`, 'info');

      // Reset quick verify panel
      _qvCurrentPayment = null;
      const input = $('#qv-input');
      const resultBox = $('#qv-result');
      if (input) { input.value = ''; input.focus(); }
      if (resultBox) { resultBox.classList.add('hidden'); resultBox.innerHTML = ''; }

      // Splice from table if visible
      currentRows = currentRows.filter(r => String(r.id) !== String(id));
      const row = $(`#payments-tbody tr[data-id="${id}"]`);
      if (row) {
        row.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
        row.style.opacity = '0';
        row.style.transform = 'translateX(-40px)';
        setTimeout(() => row.remove(), 300);
      }

      refreshRevenue();
    } catch (e) {
      toast(e.message || 'Reject failed', 'error');
    }
  }

  /* ─── Init ─────────────────────────────────────────────────── */
  function init() {
    refreshRevenue();
    refresh();
    refreshPrizePool();
    refreshBounties();
    // S5: Auto-focus search field for rapid keyboard-driven workflow
    setTimeout(() => {
      const searchInput = $('#pay-filter-search');
      if (searchInput) searchInput.focus();
    }, 80);
  }

  /* ─── export ───────────────────────────────────────────────── */
  window.TOC = window.TOC || {};
  window.TOC.payments = {
    init,
    refresh,
    refreshRevenue,
    refreshPrizePool,
    refreshBounties,
    goPage,
    verify,
    reject,
    openRefund,
    confirmRefund,
    bulkVerify,
    exportCSV,
    viewProof,
    toggleRow,
    toggleSelectAll,
    openCreateBountyDrawer,
    confirmCreateBounty,
    openAssignBounty, _submitAssignBounty,
    deleteBounty,
    highlightNextPending,
    _searchDebounce,
    // Smart Quick Verify
    qvSearch,
    qvVerify,
    qvReject,
    _qvDebounce,
    _qvSelect,
  };

  /* Auto-init when payments tab is activated */
  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'payments') init();
  });

})();
