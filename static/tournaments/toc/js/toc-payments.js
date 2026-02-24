/**
 * TOC Payments Module — Sprint 4
 * Financial Operations: Payment verification, revenue analytics,
 * prize distribution, bounty management, KYC & refund workflows.
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

  /* ─── Revenue summary cards (S4-F4) ──────────────────────── */
  async function refreshRevenue() {
    try {
      const data = await API.get(`/api/toc/${slug}/payments/summary/`);
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

  /* ─── Payment list (S4-F1 / S4-F3) ──────────────────────── */
  async function refresh() {
    const status = $('#pay-filter-status')?.value || '';
    const method = $('#pay-filter-method')?.value || '';
    const search = $('#pay-filter-search')?.value || '';

    try {
      const qs = new URLSearchParams({ page: currentPage, page_size: pageSize });
      if (status) qs.set('status', status);
      if (method) qs.set('method', method);
      if (search) qs.set('search', search);

      const data = await API.get(`/api/toc/${slug}/payments/?${qs}`);
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
        <tr class="border-b border-dc-border/50 hover:bg-white/[0.015] transition-colors group" data-id="${p.id}">
          <td class="px-3 py-3">
            ${isCheckable ? `<input type="checkbox" class="toc-checkbox pay-row-cb" data-id="${p.id}" ${checked} onclick="TOC.payments.toggleRow('${p.id}', this)">` : ''}
          </td>
          <td class="px-3 py-3">
            <p class="text-dc-textBright font-semibold text-xs leading-tight">${p.participant_name || 'Unknown'}</p>
            <p class="text-[10px] text-dc-text font-mono mt-0.5">${p.team_name || ''}</p>
          </td>
          <td class="px-3 py-3 text-right font-mono text-dc-textBright font-bold">${money(p.amount, p.currency)}</td>
          <td class="px-3 py-3">
            <span class="text-[10px] font-bold uppercase text-dc-text">${(p.payment_method || '—').replace('_', ' ')}</span>
          </td>
          <td class="px-3 py-3">
            <span class="text-[10px] font-mono text-dc-text">${p.transaction_id || '—'}</span>
          </td>
          <td class="px-3 py-3">${badge(p.status)}</td>
          <td class="px-3 py-3 text-center">
            ${p.proof_url
              ? `<button onclick="TOC.payments.viewProof('${p.proof_url}')" class="inline-flex items-center gap-1 text-[10px] text-theme hover:text-white transition-colors"><i data-lucide="eye" class="w-3 h-3"></i></button>`
              : `<span class="text-[10px] text-dc-text/40">—</span>`
            }
          </td>
          <td class="px-3 py-3 text-[10px] text-dc-text font-mono">${fmtDate(p.submitted_at || p.created_at)}</td>
          <td class="px-3 py-3 text-right">
            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              ${p.status === 'submitted' || p.status === 'pending' ? `
                <button onclick="TOC.payments.verify('${p.id}')" title="Verify" class="w-7 h-7 rounded-lg bg-dc-success/10 text-dc-success border border-dc-success/20 flex items-center justify-center hover:bg-dc-success/20 transition-colors"><i data-lucide="check" class="w-3 h-3"></i></button>
                <button onclick="TOC.payments.reject('${p.id}')" title="Reject" class="w-7 h-7 rounded-lg bg-dc-danger/10 text-dc-danger border border-dc-danger/20 flex items-center justify-center hover:bg-dc-danger/20 transition-colors"><i data-lucide="x" class="w-3 h-3"></i></button>
              ` : ''}
              ${p.status === 'verified' ? `
                <button onclick="TOC.payments.openRefund('${p.id}', '${(p.participant_name||'').replace(/'/g,'')}', '${p.amount}')" title="Refund" class="w-7 h-7 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center justify-center hover:bg-purple-500/20 transition-colors"><i data-lucide="undo-2" class="w-3 h-3"></i></button>
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

    const total = data.count || 0;
    const pages = Math.ceil(total / pageSize) || 1;
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

  /* ─── Payment actions (S4-F3) ──────────────────────────────── */
  async function verify(id) {
    try {
      await API.post(`/api/toc/${slug}/payments/${id}/verify/`);
      toast('Payment verified', 'success');
      selectedIds.delete(id);
      refresh();
      refreshRevenue();
    } catch (e) {
      toast(e.message || 'Verify failed', 'error');
    }
  }

  async function reject(id) {
    const reason = prompt('Rejection reason:');
    if (!reason) return;
    try {
      await API.post(`/api/toc/${slug}/payments/${id}/reject/`, { reason });
      toast('Payment rejected', 'info');
      selectedIds.delete(id);
      refresh();
      refreshRevenue();
    } catch (e) {
      toast(e.message || 'Reject failed', 'error');
    }
  }

  async function bulkVerify() {
    if (!selectedIds.size) return;
    try {
      await API.post(`/api/toc/${slug}/payments/bulk-verify/`, { payment_ids: Array.from(selectedIds) });
      toast(`${selectedIds.size} payments verified`, 'success');
      selectedIds.clear();
      refresh();
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
      await API.post(`/api/toc/${slug}/payments/${id}/refund/`, { reason });
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
      const blob = await API.getRaw(`/api/toc/${slug}/payments/export/`);
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
      const data = await API.get(`/api/toc/${slug}/prize-pool/`);
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
      const data = await API.get(`/api/toc/${slug}/bounties/`);
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
      await API.post(`/api/toc/${slug}/bounties/`, { name, bounty_type, prize_amount, source, description, sponsor_name });
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
    const registrationId = prompt('Enter the registration ID of the winner:');
    if (!registrationId) return;
    const reason = prompt('Assignment reason (optional):') || '';
    assignBounty(bountyId, registrationId, reason);
  }

  async function assignBounty(bountyId, registrationId, reason) {
    try {
      await API.post(`/api/toc/${slug}/bounties/${bountyId}/assign/`, {
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
      await API.delete(`/api/toc/${slug}/bounties/${bountyId}/`);
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

  /* ─── Init ─────────────────────────────────────────────────── */
  function init() {
    refreshRevenue();
    refresh();
    refreshPrizePool();
    refreshBounties();
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
    openAssignBounty,
    deleteBounty,
    _searchDebounce,
  };

  /* Auto-init when payments tab is activated */
  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'payments') init();
  });

})();
