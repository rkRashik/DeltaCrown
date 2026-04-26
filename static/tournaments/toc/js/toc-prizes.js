/**
 * TOC — Prizes & Awards tab.
 *
 * Loads /api/toc/<slug>/prizes/ for the editor + public preview,
 * persists via /save/, recomputes placements via /publish/.
 */

;(function () {
  'use strict';

  const CFG = window.TOC_CONFIG || {};
  const API = CFG.apiBase || '';
  const $ = (s, ctx) => (ctx || document).querySelector(s);

  // ── Local editor state ──
  let state = {
    currency: 'BDT',
    fiat_pool: 0,
    coin_pool: 0,
    placements: [],
    special_awards: [],
    certificates_enabled: true,
  };
  let lastPreview = null;
  let lastOperations = null;
  let recipientPicker = { mode: '', awardIndex: -1, rank: 0 };

  function ordinal(n) {
    const v = n % 100;
    if (v >= 11 && v <= 13) return `${n}th`;
    const s = { 1: 'st', 2: 'nd', 3: 'rd' };
    return `${n}${s[n % 10] || 'th'}`;
  }

  function formatNum(n) {
    n = Number(n) || 0;
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function resultStatus(payload) {
    return (payload && payload.result_status) ||
      (payload && payload.status) ||
      {};
  }

  function resultLabel(row, completed) {
    const name = row && row.team_name ? row.team_name :
      row && row.winner && row.winner.team_name ? row.winner.team_name : '';
    if (name) return name;
    if (row && row.result_label) return row.result_label;
    return completed ? 'Result pending' : 'Pending';
  }

  function achievementRows(payload) {
    return (payload && (
      payload.achievements ||
      payload.derived_achievements ||
      payload.special_awards
    )) || [];
  }

  function renderAchievements(containerId, payload) {
    const container = $(containerId);
    if (!container) return;
    const rows = achievementRows(payload).slice(0, 6);
    container.innerHTML = '';
    container.classList.toggle('hidden', !rows.length);
    rows.forEach((a) => {
      const card = document.createElement('div');
      card.className = 'rounded-lg border border-dc-border bg-dc-surface/30 px-3 py-2';
      card.innerHTML = `
        <div class="flex items-start gap-2">
          <i data-lucide="${escapeAttr(a.icon || 'award')}" class="w-3.5 h-3.5 text-theme mt-0.5"></i>
          <div class="min-w-0">
            <div class="text-xs font-bold text-white truncate">${escapeHtml(a.title || 'Achievement')}</div>
            <div class="text-[10px] text-dc-text truncate">${escapeHtml(a.recipient_name || (a.awaiting_recipient ? 'Awaiting assignment' : a.description || ''))}</div>
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  }

  function updatePctTotal() {
    const total = (state.placements || []).reduce(
      (acc, p) => acc + (Number(p.percent) || 0), 0,
    );
    const el = $('#prizes-pct-total');
    if (!el) return;
    el.textContent = `${total}%`;
    el.classList.toggle('text-dc-success', total === 100);
    el.classList.toggle('text-dc-warning', total !== 100 && total !== 0);
  }

  function syncFromPercent(idx) {
    const tier = state.placements[idx];
    if (!tier) return;
    const pct = Number(tier.percent) || 0;
    if (state.fiat_pool > 0) tier.fiat = Math.round(state.fiat_pool * pct / 100);
    if (state.coin_pool > 0) tier.coins = Math.round(state.coin_pool * pct / 100);
    renderTiers();
  }

  function renderTiers() {
    const list = $('#prizes-tier-list');
    if (!list) return;
    list.innerHTML = '';
    (state.placements || []).forEach((tier, idx) => {
      const row = document.createElement('div');
      row.className = 'grid grid-cols-12 gap-2 items-center px-2 py-2 rounded-lg border border-dc-border bg-dc-surface/30';
      row.innerHTML = `
        <div class="col-span-1 font-mono text-xs text-dc-textBright">${ordinal(tier.rank)}</div>
        <div class="col-span-4">
          <input data-prize-tier-title="${idx}" type="text" maxlength="80" value="${escapeAttr(tier.title || '')}"
            class="w-full bg-transparent border-b border-dc-border focus:border-theme/60 px-1 py-0.5 text-xs text-white outline-none">
        </div>
        <div class="col-span-2">
          <input data-prize-tier-pct="${idx}" type="number" min="0" max="100" value="${tier.percent || 0}"
            class="w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-center text-white outline-none focus:border-theme/40">
        </div>
        <div class="col-span-2">
          <input data-prize-tier-fiat="${idx}" type="number" min="0" value="${tier.fiat || 0}"
            class="w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-right text-white outline-none focus:border-theme/40">
        </div>
        <div class="col-span-2">
          <input data-prize-tier-coins="${idx}" type="number" min="0" value="${tier.coins || 0}"
            class="w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-right text-white outline-none focus:border-theme/40">
        </div>
        <div class="col-span-1 text-right">
          <button data-prize-tier-remove="${idx}" class="text-dc-text hover:text-dc-danger transition-colors">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      `;
      list.appendChild(row);
    });
    if (window.lucide) window.lucide.createIcons();
    updatePctTotal();
  }

  function renderAwards() {
    const list = $('#prizes-award-list');
    if (!list) return;
    list.innerHTML = '';
    const empty = $('#prizes-award-empty');
    if (empty) empty.classList.toggle('hidden', (state.special_awards || []).length > 0);
    (state.special_awards || []).forEach((a, idx) => {
      const card = document.createElement('div');
      card.className = 'rounded-xl border border-dc-border bg-[linear-gradient(145deg,rgba(18,18,26,0.86),rgba(6,6,10,0.95))] p-4 space-y-3';
      card.innerHTML = `
        <div class="flex items-start gap-2">
          <input data-prize-award-title="${idx}" type="text" maxlength="120" value="${escapeAttr(a.title || '')}"
            class="flex-1 bg-transparent border-b border-dc-border focus:border-theme/60 px-1 py-0.5 text-sm text-white outline-none" placeholder="Award title">
          <button data-prize-award-remove="${idx}" class="text-dc-text hover:text-dc-danger transition-colors px-1">
            <i data-lucide="x" class="w-3.5 h-3.5"></i>
          </button>
        </div>
        <input data-prize-award-desc="${idx}" type="text" maxlength="240" value="${escapeAttr(a.description || '')}"
          class="w-full bg-transparent border-b border-dc-border focus:border-theme/60 px-1 py-0.5 text-xs text-dc-textBright outline-none" placeholder="Criteria / description">
        <div class="grid grid-cols-2 gap-2">
          <label class="text-[10px] text-dc-text">Type
            <select data-prize-award-type="${idx}" class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-white outline-none">
              <option value="cash" ${a.type === 'cash' ? 'selected' : ''}>Cash</option>
              <option value="hardware" ${a.type === 'hardware' ? 'selected' : ''}>Hardware</option>
              <option value="digital" ${a.type === 'digital' ? 'selected' : ''}>Digital code</option>
            </select>
          </label>
          <label class="text-[10px] text-dc-text">Icon
            <input data-prize-award-icon="${idx}" type="text" maxlength="40" value="${escapeAttr(a.icon || 'medal')}"
              class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-white outline-none" placeholder="medal">
          </label>
          <label class="text-[10px] text-dc-text">Fiat
            <input data-prize-award-fiat="${idx}" type="number" min="0" value="${a.fiat || 0}"
              class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-right text-white outline-none">
          </label>
          <label class="text-[10px] text-dc-text">Coins
            <input data-prize-award-coins="${idx}" type="number" min="0" value="${a.coins || 0}"
              class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-right text-white outline-none">
          </label>
        </div>
        <input data-prize-award-text="${idx}" type="text" maxlength="240" value="${escapeAttr(a.reward_text || '')}"
          class="w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-white outline-none" placeholder="Reward detail (e.g. 'Logitech G Pro X')">
        <label class="hidden text-[10px] text-dc-text mt-1">Recipient (name or team — optional)
          <input data-prize-award-recipient="${idx}" type="text" maxlength="120" value="${escapeAttr(a.recipient_name || '')}"
            class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-white outline-none" placeholder="Awaiting assignment">
        </label>
        <label class="hidden text-[10px] text-dc-text mt-1">Recipient Registration ID (optional)
          <input data-prize-award-recipient-id="${idx}" type="number" min="0" value="${a.recipient_id || ''}"
            class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-white outline-none" placeholder="Registration ID">
        </label>
        <div class="flex items-center justify-between gap-3 rounded-lg border border-dc-border bg-dc-surface/50 px-3 py-2">
          <div class="min-w-0">
            <p class="text-[10px] uppercase tracking-widest text-dc-text">Selected recipient</p>
            <p class="text-sm font-bold ${a.recipient_name ? 'text-theme' : 'text-dc-warning'} truncate">${escapeHtml(a.recipient_name || 'Awaiting assignment')}</p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button data-prize-award-pick-recipient="${idx}" class="px-3 py-1.5 rounded-lg border border-theme/30 text-theme text-[10px] font-bold uppercase tracking-wider hover:bg-theme/10 transition-colors">
              <i data-lucide="search" class="w-3 h-3 inline-block mr-1"></i> Select
            </button>
            <button data-prize-award-clear-recipient="${idx}" class="px-3 py-1.5 rounded-lg border border-dc-border text-dc-text text-[10px] font-bold uppercase tracking-wider hover:text-white hover:border-white/30 transition-colors">
              Clear
            </button>
          </div>
        </div>
      `;
      list.appendChild(card);
    });
    if (window.lucide) window.lucide.createIcons();
  }

  function renderPreview(payload) {
    lastPreview = payload || lastPreview;
    if (!payload) return;
    const statusState = resultStatus(payload);
    const completed = !!statusState.completed;
    const standingsCount = (payload.standings || []).length;
    const placementWinnerCount = (payload.placements || []).filter((p) => p.winner && p.winner.team_name).length;
    const status = $('#prizes-preview-status');
    if (status) {
      if (statusState.placements_published) {
        status.textContent = `Published - ${standingsCount || placementWinnerCount} placement(s)`;
      } else if (completed) {
        status.textContent = `Completed - ${standingsCount || placementWinnerCount} result(s) available`;
      } else {
        status.textContent = 'Setup mode - results appear after completion';
      }
    }
    const podium = $('#prizes-preview-podium');
    if (podium) {
      podium.innerHTML = '';
      const top3 = (payload.placements || []).slice(0, 3);
      const order = [1, 0, 2]; // 2nd | 1st | 3rd visual order
      order.forEach((slot) => {
        const tier = top3[slot];
        if (!tier) return;
        const cell = document.createElement('div');
        const isChamp = tier.rank === 1;
        cell.className = `rounded-xl p-3 text-center border ${isChamp ? 'border-yellow-500/50 bg-yellow-500/10' : 'border-dc-border bg-dc-surface/40'}`;
        const name = resultLabel(tier, completed);
        const nameTone = tier.winner && tier.winner.team_name ? 'text-theme' : 'text-dc-text';
        cell.innerHTML = `
          <div class="text-[10px] uppercase tracking-widest text-dc-text">${ordinal(tier.rank)}</div>
          <div class="text-sm text-white font-bold mt-1 truncate">${escapeHtml(tier.title || '')}</div>
          <div class="text-[10px] ${nameTone} mt-1 truncate">${escapeHtml(name)}</div>
          <div class="text-xs font-mono text-dc-textBright mt-2">${payload.currency || 'BDT'} ${formatNum(tier.fiat)}</div>
          <div class="text-[10px] font-mono text-theme">${formatNum(tier.coins)} DC</div>
        `;
        podium.appendChild(cell);
      });
    }
    const list = $('#prizes-preview-list');
    if (list) {
      list.innerHTML = '';
      (payload.placements || []).slice(3).forEach((tier) => {
        const row = document.createElement('div');
        row.className = 'flex items-center justify-between text-xs px-2 py-1 rounded border border-dc-border bg-dc-surface/30';
        const name = resultLabel(tier, completed);
        row.innerHTML = `
          <span class="text-dc-textBright min-w-0 truncate">${ordinal(tier.rank)} - ${escapeHtml(tier.title || '')} - ${escapeHtml(name)}</span>
          <span class="font-mono text-dc-textBright shrink-0">${payload.currency || 'BDT'} ${formatNum(tier.fiat)} - ${formatNum(tier.coins)} DC</span>
        `;
        list.appendChild(row);
      });
    }
    renderAchievements('#prizes-preview-achievements', payload);
  }

  function opBadge(text, tone) {
    const colors = {
      green: 'border-dc-success/30 bg-dc-success/10 text-dc-success',
      red: 'border-dc-danger/30 bg-dc-dangerBg text-dc-danger',
      gold: 'border-dc-warning/30 bg-dc-warning/10 text-dc-warning',
      cyan: 'border-theme/30 bg-theme/10 text-theme',
      gray: 'border-dc-border bg-dc-surface/40 text-dc-text',
    };
    return `<span class="inline-flex items-center px-2 py-0.5 rounded border text-[10px] font-mono uppercase tracking-wider ${colors[tone] || colors.gray}">${escapeHtml(text || 'pending')}</span>`;
  }

  function renderOperations(ops) {
    lastOperations = ops || lastOperations;
    ops = lastOperations;
    const status = $('#prizes-ops-status');
    const empty = $('#prizes-ops-empty');
    const table = $('#prizes-ops-table');
    if (!table) return;
    const rows = (ops && ops.placements) || [];
    const state = (ops && ops.status) || {};
    const completed = !!state.completed;
    if (status) {
      if (state.placements_published) {
        status.textContent = `Published - ${rows.length} placement(s)`;
      } else if (completed && rows.length) {
        status.textContent = `Completed - ${rows.length} placement(s)`;
      } else {
        status.textContent = state.message || 'Not published';
      }
    }
    if (!rows.length) {
      table.innerHTML = '';
      if (empty) {
        empty.textContent = completed
          ? (state.message || 'Completed result exists, but no reward operation rows are available yet.')
          : (state.message || 'No final standings are available yet. Publish placements after completion.');
        empty.classList.remove('hidden');
      }
      return;
    }
    if (empty) empty.classList.add('hidden');
    table.innerHTML = rows.map((row) => {
      const prize = row.prize || {};
      const claim = row.claim || null;
      const payout = row.payout || {};
      const cert = row.certificate || null;
      const claimTone = !claim ? 'gray' : claim.status === 'paid' ? 'green' : claim.status === 'rejected' ? 'red' : 'gold';
      const payoutTone = payout.status === 'paid' || payout.status === 'completed' ? 'green' : payout.status === 'rejected' || payout.status === 'failed' ? 'red' : 'cyan';
      const certTone = cert && cert.status === 'available' ? 'green' : 'gray';
      const claimId = claim && claim.id ? claim.id : '';
      const canReview = row.actions && row.actions.can_review_claim;
      const canMarkPaid = row.actions && row.actions.can_mark_paid;
      const recipientName = resultLabel(row, completed);
      const blockReason = row.payout_blocked && row.block_reason
        ? `<p class="text-[10px] text-dc-warning mt-1">${escapeHtml(row.block_reason)}</p>`
        : '';
      const contactReason = 'Messaging integration pending.';
      const claimReason = claimId ? 'Prize claim permission is required.' : 'No prize claim has been submitted yet.';
      const paidReason = row.payout_blocked
        ? (row.block_reason || 'Payout is blocked for this placement.')
        : claimReason;
      return `
        <div class="rounded-lg border border-dc-border bg-dc-surface/30 p-3 space-y-3">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-mono text-theme">${escapeHtml(row.rank_label || ordinal(row.rank))}</span>
                <span class="text-sm font-bold text-white truncate">${escapeHtml(recipientName)}</span>
              </div>
              <p class="text-[10px] uppercase tracking-widest text-dc-text mt-0.5">${escapeHtml(row.title || '')}</p>
              ${blockReason}
            </div>
            <div class="text-right shrink-0">
              <div class="text-xs font-mono text-white">${escapeHtml((lastPreview && lastPreview.currency) || 'BDT')} ${formatNum(prize.fiat || 0)}</div>
              <div class="text-[10px] font-mono text-theme">${formatNum(prize.coins || 0)} DC</div>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div>${opBadge(claim ? `Claim ${claim.status}` : 'No claim', claimTone)}</div>
            <div>${opBadge(`Payout ${payout.status || 'not_started'}`, payoutTone)}</div>
            <div>${opBadge(cert ? `Certificate ${cert.status}` : 'Certificate pending', certTone)}</div>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <button class="px-2 py-1 rounded border border-dc-border text-[10px] text-dc-text cursor-not-allowed opacity-60" disabled title="${escapeAttr(contactReason)}">
              <i data-lucide="message-square" class="w-3 h-3 inline-block mr-1"></i> Contact pending
            </button>
            ${row.placement_unresolved ? `<button data-prize-create-bronze class="px-2 py-1 rounded border border-dc-warning/30 text-[10px] text-dc-warning hover:bg-dc-warning/10">
              <i data-lucide="medal" class="w-3 h-3 inline-block mr-1"></i> Create Third Place Match
            </button>` : ''}
            <button data-prize-assign-rank="${row.rank}" class="px-2 py-1 rounded border border-theme/30 text-[10px] text-theme hover:bg-theme/10">
              <i data-lucide="user-plus" class="w-3 h-3 inline-block mr-1"></i> Manual Assign
            </button>
            <button data-prize-claim-action="approve" data-claim-id="${claimId}" data-cap-require="approve_payments"
              title="${escapeAttr(canReview ? 'Approve claim for processing.' : claimReason)}"
              class="px-2 py-1 rounded border border-dc-warning/30 text-[10px] text-dc-warning hover:bg-dc-warning/10 disabled:opacity-40 disabled:cursor-not-allowed" ${canReview ? '' : 'disabled'}>
              Approve
            </button>
            <button data-prize-claim-action="reject" data-claim-id="${claimId}" data-cap-require="approve_payments"
              title="${escapeAttr(canReview ? 'Reject this claim.' : claimReason)}"
              class="px-2 py-1 rounded border border-dc-danger/30 text-[10px] text-dc-danger hover:bg-dc-dangerBg disabled:opacity-40 disabled:cursor-not-allowed" ${canReview ? '' : 'disabled'}>
              Reject
            </button>
            <button data-prize-claim-action="mark_paid" data-claim-id="${claimId}" data-cap-require="approve_payments"
              title="${escapeAttr(canMarkPaid && !row.payout_blocked ? 'Record manual payout as paid.' : paidReason)}"
              class="px-2 py-1 rounded border border-dc-success/30 text-[10px] text-dc-success hover:bg-dc-success/10 disabled:opacity-40 disabled:cursor-not-allowed" ${canMarkPaid && !row.payout_blocked ? '' : 'disabled'}>
              Mark Paid
            </button>
            ${cert && cert.download_url ? `<a href="${escapeAttr(cert.download_url)}" class="px-2 py-1 rounded border border-theme/30 text-[10px] text-theme hover:bg-theme/10">Certificate</a>` : ''}
          </div>
        </div>`;
    }).join('');
    if (window.lucide) window.lucide.createIcons();
  }

  function escapeAttr(s) {
    return String(s == null ? '' : s).replace(/"/g, '&quot;').replace(/</g, '&lt;');
  }
  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // ── API ──

  function debounce(fn, delay) {
    let timer = null;
    return function () {
      const args = arguments;
      window.clearTimeout(timer);
      timer = window.setTimeout(() => fn.apply(null, args), delay);
    };
  }

  function ensureRecipientModal() {
    let modal = $('#prize-recipient-picker-modal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'prize-recipient-picker-modal';
    modal.className = 'hidden fixed inset-0 z-[300] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4';
    modal.innerHTML = `
      <div class="w-full max-w-xl rounded-2xl border border-dc-borderLight bg-dc-panel shadow-2xl overflow-hidden">
        <div class="p-5 border-b border-dc-border flex items-center justify-between gap-3">
          <div>
            <h3 id="prize-recipient-picker-title" class="text-lg font-display font-black text-white">Select Recipient</h3>
            <p class="text-xs text-dc-text mt-1">Search confirmed tournament participants and teams.</p>
          </div>
          <button data-prize-recipient-close class="p-2 rounded-lg text-dc-text hover:text-white hover:bg-white/10 transition-colors">
            <i data-lucide="x" class="w-5 h-5"></i>
          </button>
        </div>
        <div class="p-5 space-y-4">
          <label class="block">
            <span class="text-[10px] uppercase tracking-widest text-dc-text">Participant / Team</span>
            <input id="prize-recipient-search" type="search" autocomplete="off"
              class="mt-2 w-full bg-dc-bg border border-dc-border rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-theme"
              placeholder="Search by player, team, or email">
          </label>
          <div id="prize-recipient-results" class="max-h-[360px] overflow-y-auto space-y-2"></div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
      if (e.target === modal || e.target.closest('[data-prize-recipient-close]')) closeRecipientPicker();
      const pick = e.target.closest('[data-prize-recipient-pick]');
      if (pick) {
        selectRecipient({
          id: Number(pick.getAttribute('data-recipient-id') || 0),
          name: pick.getAttribute('data-recipient-name') || '',
        });
      }
    });
    const search = $('#prize-recipient-search', modal);
    if (search) search.addEventListener('input', debounce(() => searchRecipients(search.value), 180));
    return modal;
  }

  function openRecipientPicker(mode, options) {
    recipientPicker = Object.assign({ mode, awardIndex: -1, rank: 0 }, options || {});
    const modal = ensureRecipientModal();
    const title = $('#prize-recipient-picker-title', modal);
    if (title) title.textContent = mode === 'placement' ? `Assign ${ordinal(recipientPicker.rank)} recipient` : 'Assign special award recipient';
    const search = $('#prize-recipient-search', modal);
    if (search) search.value = '';
    modal.classList.remove('hidden');
    searchRecipients('');
    window.setTimeout(() => { if (search) search.focus(); }, 30);
    if (window.lucide) window.lucide.createIcons();
  }

  function closeRecipientPicker() {
    const modal = $('#prize-recipient-picker-modal');
    if (modal) modal.classList.add('hidden');
  }

  async function searchRecipients(query) {
    const results = $('#prize-recipient-results');
    if (!results) return;
    results.innerHTML = '<div class="text-xs text-dc-text px-2 py-3">Searching...</div>';
    try {
      const data = await TOC.fetch(`${API}/prizes/recipients/?q=${encodeURIComponent(query || '')}`);
      const rows = data.results || [];
      if (!rows.length) {
        results.innerHTML = '<div class="text-xs text-dc-text px-2 py-3">No matching tournament participants.</div>';
        return;
      }
      results.innerHTML = rows.map((r) => `
        <button data-prize-recipient-pick data-recipient-id="${r.registration_id}" data-recipient-name="${escapeAttr(r.name || '')}"
          class="w-full text-left rounded-xl border border-dc-border bg-dc-surface/70 px-4 py-3 hover:border-theme/40 hover:bg-theme/10 transition-colors">
          <span class="block text-sm font-bold text-white">${escapeHtml(r.name || '')}</span>
          <span class="block text-[10px] text-dc-text mt-1">${escapeHtml(r.subtitle || '')}</span>
        </button>
      `).join('');
    } catch (e) {
      results.innerHTML = '<div class="text-xs text-dc-danger px-2 py-3">Recipient search failed.</div>';
    }
  }

  async function selectRecipient(recipient) {
    if (!recipient.id) return;
    if (recipientPicker.mode === 'award') {
      const award = state.special_awards[recipientPicker.awardIndex];
      if (award) {
        award.recipient_id = recipient.id;
        award.recipient_name = recipient.name;
        renderAwards();
        await save();
        TOC.toast('Special award recipient assigned.', 'success');
      }
      closeRecipientPicker();
      return;
    }
    if (recipientPicker.mode === 'placement') {
      try {
        const data = await TOC.fetch(`${API}/prizes/placements/assign/`, {
          method: 'POST',
          body: { rank: recipientPicker.rank, recipient_id: recipient.id },
        });
        Object.assign(state, data.config || state);
        renderPreview(data.public_preview);
        renderOperations(data.operations);
        TOC.toast('Placement recipient assigned.', 'success');
        closeRecipientPicker();
      } catch (e) {
        TOC.toast((e && e.message) || 'Assignment failed.', 'error');
      }
    }
  }

  async function load() {
    const status = $('#prizes-sync-status');
    if (status) status.textContent = 'Loading…';
    try {
      const data = await TOC.fetch(`${API}/prizes/`);
      Object.assign(state, data.config || {});
      if (!Array.isArray(state.placements)) state.placements = [];
      if (!Array.isArray(state.special_awards)) state.special_awards = [];
      renderEditor();
      renderPreview(data.public_preview);
      renderOperations(data.operations);
      if (status) status.textContent = `Loaded · ${state.placements.length} tiers`;
    } catch (e) {
      const banner = $('#prizes-error-banner');
      if (banner) {
        banner.textContent = (e && e.message) || 'Failed to load prizes.';
        banner.classList.remove('hidden');
      }
      if (status) status.textContent = 'Load failed';
    }
  }

  async function save() {
    const status = $('#prizes-sync-status');
    if (status) status.textContent = 'Saving…';
    try {
      const data = await TOC.fetch(`${API}/prizes/save/`, {
        method: 'POST', body: state,
      });
      Object.assign(state, data.config || {});
      renderEditor();
      renderPreview(data.public_preview);
      renderOperations(data.operations);
      TOC.toast('Prize configuration saved.', 'success');
      if (status) status.textContent = 'Saved';
    } catch (e) {
      TOC.toast((e && e.message) || 'Save failed.', 'error');
      if (status) status.textContent = 'Save failed';
    }
  }

  async function publish() {
    const status = $('#prizes-sync-status');
    if (status) status.textContent = 'Publishing…';
    try {
      const data = await TOC.fetch(`${API}/prizes/publish/`, { method: 'POST' });
      renderPreview(data.public_preview);
      renderOperations(data.operations);
      TOC.toast('Placements published.', 'success');
      if (status) status.textContent = 'Published';
    } catch (e) {
      TOC.toast((e && e.message) || 'Publish failed.', 'error');
      if (status) status.textContent = 'Publish failed';
    }
  }

  // ── Editor wiring ──

  async function createBronzeMatch() {
    const status = $('#prizes-sync-status');
    if (status) status.textContent = 'Creating Third Place Match...';
    try {
      const data = await TOC.fetch(`${API}/prizes/bronze/create/`, { method: 'POST' });
      renderPreview(data.public_preview);
      renderOperations(data.operations);
      TOC.toast('Third Place Match created from semifinal losers.', 'success');
      if (status) status.textContent = 'Third Place Match created';
    } catch (e) {
      TOC.toast((e && e.message) || 'Could not create Third Place Match.', 'error');
      if (status) status.textContent = 'Third Place Match creation failed';
    }
  }

  async function claimAction(claimId, action) {
    if (!claimId) return;
    let notes = '';
    if (action === 'reject') {
      notes = window.prompt('Optional rejection note for this claim:', '') || '';
    } else if (action === 'mark_paid') {
      const ok = window.confirm('Mark this claim as manually paid? This does not run an automated payout.');
      if (!ok) return;
      notes = 'Manual payout marked paid from TOC prize operations.';
    }
    try {
      const data = await TOC.fetch(`${API}/prizes/claims/${claimId}/action/`, {
        method: 'POST',
        body: { action, notes },
      });
      renderPreview(data.public_preview);
      renderOperations(data.operations);
      TOC.toast('Prize claim updated.', 'success');
    } catch (e) {
      TOC.toast((e && e.message) || 'Claim update failed.', 'error');
    }
  }

  function renderEditor() {
    const cur = $('#prizes-currency'); if (cur) cur.value = state.currency || 'BDT';
    const fp = $('#prizes-fiat-pool'); if (fp) fp.value = state.fiat_pool || 0;
    const cp = $('#prizes-coin-pool'); if (cp) cp.value = state.coin_pool || 0;
    const ce = $('#prizes-certificates-enabled');
    if (ce) ce.checked = state.certificates_enabled !== false;
    renderTiers();
    renderAwards();
  }

  function bindEditorEvents() {
    $('#prizes-currency')?.addEventListener('change', (e) => { state.currency = (e.target.value || 'BDT').toUpperCase().slice(0, 10); });
    $('#prizes-fiat-pool')?.addEventListener('change', (e) => { state.fiat_pool = Number(e.target.value) || 0; state.placements.forEach((_, i) => syncFromPercent(i)); });
    $('#prizes-coin-pool')?.addEventListener('change', (e) => { state.coin_pool = Number(e.target.value) || 0; state.placements.forEach((_, i) => syncFromPercent(i)); });
    $('#prizes-certificates-enabled')?.addEventListener('change', (e) => { state.certificates_enabled = !!e.target.checked; });

    $('#prizes-tier-list')?.addEventListener('input', (e) => {
      const t = e.target;
      const idx = (a) => Number(t.getAttribute(a));
      if (t.hasAttribute('data-prize-tier-title')) state.placements[idx('data-prize-tier-title')].title = t.value;
      else if (t.hasAttribute('data-prize-tier-pct')) {
        state.placements[idx('data-prize-tier-pct')].percent = Math.max(0, Math.min(100, Number(t.value) || 0));
        syncFromPercent(idx('data-prize-tier-pct'));
      } else if (t.hasAttribute('data-prize-tier-fiat')) state.placements[idx('data-prize-tier-fiat')].fiat = Math.max(0, Number(t.value) || 0);
      else if (t.hasAttribute('data-prize-tier-coins')) state.placements[idx('data-prize-tier-coins')].coins = Math.max(0, Number(t.value) || 0);
      updatePctTotal();
    });
    $('#prizes-tier-list')?.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-prize-tier-remove]');
      if (!btn) return;
      const i = Number(btn.getAttribute('data-prize-tier-remove'));
      state.placements.splice(i, 1);
      // Renumber ranks.
      state.placements.forEach((p, idx) => { p.rank = idx + 1; });
      renderTiers();
    });
    $('#prizes-add-tier-btn')?.addEventListener('click', () => {
      const next = (state.placements.length || 0) + 1;
      state.placements.push({ rank: next, title: ordinal(next), percent: 0, fiat: 0, coins: 0 });
      renderTiers();
    });

    $('#prizes-award-list')?.addEventListener('input', (e) => {
      const t = e.target;
      const i = (a) => Number(t.getAttribute(a));
      if (t.hasAttribute('data-prize-award-title')) state.special_awards[i('data-prize-award-title')].title = t.value;
      else if (t.hasAttribute('data-prize-award-desc')) state.special_awards[i('data-prize-award-desc')].description = t.value;
      else if (t.hasAttribute('data-prize-award-icon')) state.special_awards[i('data-prize-award-icon')].icon = t.value;
      else if (t.hasAttribute('data-prize-award-fiat')) state.special_awards[i('data-prize-award-fiat')].fiat = Math.max(0, Number(t.value) || 0);
      else if (t.hasAttribute('data-prize-award-coins')) state.special_awards[i('data-prize-award-coins')].coins = Math.max(0, Number(t.value) || 0);
      else if (t.hasAttribute('data-prize-award-text')) state.special_awards[i('data-prize-award-text')].reward_text = t.value;
      else if (t.hasAttribute('data-prize-award-recipient')) state.special_awards[i('data-prize-award-recipient')].recipient_name = t.value;
      else if (t.hasAttribute('data-prize-award-recipient-id')) state.special_awards[i('data-prize-award-recipient-id')].recipient_id = Math.max(0, Number(t.value) || 0) || null;
    });
    $('#prizes-award-list')?.addEventListener('change', (e) => {
      const t = e.target;
      if (t.hasAttribute('data-prize-award-type')) {
        const i = Number(t.getAttribute('data-prize-award-type'));
        state.special_awards[i].type = t.value;
      }
    });
    $('#prizes-award-list')?.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-prize-award-remove]');
      const pick = e.target.closest('[data-prize-award-pick-recipient]');
      const clear = e.target.closest('[data-prize-award-clear-recipient]');
      if (pick) {
        openRecipientPicker('award', {
          awardIndex: Number(pick.getAttribute('data-prize-award-pick-recipient')),
        });
        return;
      }
      if (clear) {
        const i = Number(clear.getAttribute('data-prize-award-clear-recipient'));
        if (state.special_awards[i]) {
          state.special_awards[i].recipient_id = null;
          state.special_awards[i].recipient_name = '';
          renderAwards();
        }
        return;
      }
      if (!btn) return;
      const i = Number(btn.getAttribute('data-prize-award-remove'));
      state.special_awards.splice(i, 1);
      renderAwards();
    });
    $('#prizes-add-award-btn')?.addEventListener('click', () => {
      state.special_awards.push({
        id: '', title: 'New Award', description: '', type: 'cash',
        icon: 'medal', fiat: 0, coins: 0, reward_text: '',
        recipient_name: '', recipient_id: null,
      });
      renderAwards();
    });

    $('#prizes-ops-table')?.addEventListener('click', (e) => {
      const bronze = e.target.closest('[data-prize-create-bronze]');
      if (bronze) {
        createBronzeMatch();
        return;
      }
      const assign = e.target.closest('[data-prize-assign-rank]');
      if (assign) {
        openRecipientPicker('placement', {
          rank: Number(assign.getAttribute('data-prize-assign-rank')),
        });
        return;
      }
      const btn = e.target.closest('[data-prize-claim-action]');
      if (!btn || btn.disabled) return;
      claimAction(
        btn.getAttribute('data-claim-id'),
        btn.getAttribute('data-prize-claim-action'),
      );
    });

    $('#prizes-refresh-btn')?.addEventListener('click', load);
    $('#prizes-create-bronze-btn')?.addEventListener('click', createBronzeMatch);
    $('#prizes-save-btn')?.addEventListener('click', save);
    $('#prizes-publish-btn')?.addEventListener('click', publish);

    $('#prizes-apply-template-btn')?.addEventListener('click', () => {
      const sel = $('#prizes-smart-template');
      if (!sel) return;
      const key = sel.value;
      const tpl = SMART_TEMPLATES[key];
      if (!tpl) {
        TOC.toast('Pick a template from the dropdown first.', 'info');
        return;
      }
      state.special_awards = tpl.map((a, i) => Object.assign({
        id: '', title: '', description: '', type: 'cash', icon: 'medal',
        fiat: 0, coins: 0, reward_text: '',
      }, a, { id: `tpl-${key}-${i}` }));
      renderAwards();
      TOC.toast(`Loaded ${tpl.length} award template(s). Remember to Save.`, 'success');
    });
  }

  // Smart Engine templates — seed awards only, never overwrites placements.
  const SMART_TEMPLATES = {
    valorant: [
      { title: 'Match MVP', description: 'Highest ACS in the Grand Final series.',
        type: 'cash', icon: 'medal', fiat: 1500, coins: 1000 },
      { title: 'Headshot Machine', description: 'Highest overall HS% (min 50 kills total).',
        type: 'digital', icon: 'crosshair', reward_text: '1000 VP Riot Code' },
      { title: 'Clutch Minister', description: 'Most 1vX rounds won.',
        type: 'cash', icon: 'shield', coins: 1500 },
    ],
    efootball: [
      { title: 'Golden Boot', description: 'Top scorer of the tournament.',
        type: 'cash', icon: 'crosshair', fiat: 2000, coins: 500 },
      { title: 'Golden Glove', description: 'Most clean sheets kept.',
        type: 'cash', icon: 'shield', fiat: 1000, coins: 500 },
      { title: 'Goal of the Tournament', description: 'Community voted best goal.',
        type: 'digital', icon: 'zap', coins: 2000, reward_text: 'Premium Pack' },
    ],
    pubgm: [
      { title: 'Terminator', description: 'Player with the highest total frags.',
        type: 'cash', icon: 'crosshair', fiat: 3000 },
      { title: 'Lone Survivor', description: 'Highest average survival time.',
        type: 'cash', icon: 'shield', coins: 2000 },
    ],
    dota2: [
      { title: 'The Aegis MVP', description: 'Overall most impactful player.',
        type: 'cash', icon: 'medal', fiat: 5000 },
      { title: 'Master Support', description: 'Highest average assists + healing.',
        type: 'cash', icon: 'shield', fiat: 1500, coins: 1500 },
    ],
    generic: [
      { title: 'Tournament MVP', description: 'Selected by panel for outstanding performance.',
        type: 'cash', icon: 'medal', coins: 2500 },
      { title: 'Fan Favorite', description: 'Community-voted most exciting player.',
        type: 'cash', icon: 'zap', fiat: 1000 },
    ],
  };

  // ── Tab activation ──

  function isActive() {
    const view = document.querySelector('#view-prizes');
    return view && !view.classList.contains('hidden-view');
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (!document.querySelector('#view-prizes')) return;
    bindEditorEvents();
    if (isActive()) load();
  });

  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail && e.detail.tab === 'prizes') load();
  });

  window.TOC = window.TOC || {};
  window.TOC.prizes = { load, save, publish, createBronzeMatch };
})();
