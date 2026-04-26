/**
 * Results & Achievements renderer.
 * Shared visual surface for public, HUB, and TOC. Static/CSP-safe.
 */
(function () {
  'use strict';

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fmt(value) {
    return (Number(value) || 0).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function ordinal(n) {
    n = Number(n) || 0;
    var v = n % 100;
    if (v >= 11 && v <= 13) return n + 'th';
    return n + ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] || 'th');
  }

  function money(data, amount) {
    amount = Number(amount) || 0;
    return amount ? (data.currency || 'BDT') + ' ' + fmt(amount) : 'TBA';
  }

  function winnerLabel(row) {
    if (row && row.winner && row.winner.team_name) return row.winner.team_name;
    if (row && row.team_name) return row.team_name;
    if (row && row.result_label) return row.result_label;
    return 'Pending';
  }

  function prizeLabel(data, prize) {
    prize = prize || {};
    var parts = [];
    if (Number(prize.fiat || 0)) parts.push(money(data, prize.fiat));
    if (Number(prize.coins || 0)) parts.push(fmt(prize.coins) + ' DC');
    return parts.length ? parts.join(' + ') : 'TBA';
  }

  function toneForRank(rank) {
    if (rank === 1) return 'border-[#FFD700]/45 bg-[#FFD700]/10 text-[#FFD700]';
    if (rank === 2) return 'border-slate-300/25 bg-slate-300/10 text-slate-200';
    if (rank === 3) return 'border-[#CD7F32]/35 bg-[#CD7F32]/10 text-[#CD7F32]';
    return 'border-white/10 bg-white/[0.03] text-slate-300';
  }

  function badge(text, tone) {
    var map = {
      gold: 'border-[#FFD700]/35 bg-[#FFD700]/10 text-[#FFD700]',
      cyan: 'border-[#00E5FF]/35 bg-[#00E5FF]/10 text-[#00E5FF]',
      green: 'border-emerald-400/35 bg-emerald-400/10 text-emerald-300',
      red: 'border-rose-400/35 bg-rose-400/10 text-rose-300',
      gray: 'border-white/10 bg-white/5 text-slate-300',
    };
    return '<span class="inline-flex items-center rounded-full border px-3 py-1 text-[10px] font-mono uppercase tracking-widest ' + (map[tone] || map.gray) + '">' + esc(text) + '</span>';
  }

  var PANEL = 'border border-white/10 bg-black/40 shadow-2xl backdrop-blur-xl';
  var BTN = 'inline-flex items-center gap-1.5 rounded-lg border border-[#00E5FF]/30 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-[#00E5FF] disabled:opacity-40 disabled:cursor-not-allowed';
  var BTN_WARN = 'inline-flex items-center gap-1.5 rounded-lg border border-[#FFB800]/35 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-[#FFB800] disabled:opacity-40 disabled:cursor-not-allowed';
  var BTN_DANGER = 'inline-flex items-center gap-1.5 rounded-lg border border-rose-400/35 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-rose-300 disabled:opacity-40 disabled:cursor-not-allowed';
  var BTN_GOOD = 'inline-flex items-center gap-1.5 rounded-lg border border-emerald-400/35 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-emerald-300 disabled:opacity-40 disabled:cursor-not-allowed';

  function apiFetch(url, options) {
    options = options || {};
    if (window.TOC && typeof window.TOC.fetch === 'function') {
      return window.TOC.fetch(url, options);
    }
    var fetchOptions = {
      method: options.method || 'GET',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    };
    if (options.body !== undefined) {
      fetchOptions.headers['Content-Type'] = 'application/json';
      fetchOptions.body = JSON.stringify(options.body || {});
    }
    return fetch(url, fetchOptions).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.error || 'Request failed.');
        return data;
      });
    });
  }

  function normalizePayload(data) {
    if (data && data.public_preview) {
      return Object.assign({}, data.public_preview, {
        operations: data.operations,
        config: data.config,
      });
    }
    return data || {};
  }

  function podiumHtml(data) {
    var podium = (data.placements || []).slice(0, 3);
    if (!podium.length) return '';
    var order = podium.length === 3 ? [1, 0, 2] : podium.map(function (_, i) { return i; });
    return [
      '<section class="' + PANEL + ' rounded-3xl p-6 lg:p-8">',
      '<div class="mb-8 flex items-center justify-between gap-4">',
      '<h3 class="font-display text-xl font-black text-white flex items-center gap-2"><i data-lucide="crown" class="h-5 w-5 text-[#FFD700]"></i> Championship Podium</h3>',
      data.result_status && data.result_status.completed ? badge('Completed', 'green') : badge('In progress', 'gray'),
      '</div>',
      '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 items-end">',
      order.map(function (idx) {
        var tier = podium[idx];
        if (!tier) return '';
        var rank = Number(tier.rank) || idx + 1;
        var champion = rank === 1;
        var unresolved = !!tier.placement_unresolved;
        return [
          '<div class="relative rounded-2xl border p-5 text-center transition ' + toneForRank(rank) + (champion ? ' md:-translate-y-5 shadow-[0_0_45px_rgba(255,215,0,0.14)]' : '') + '">',
          '<div class="absolute right-4 top-3 font-display text-6xl font-black text-white/5">' + rank + '</div>',
          '<div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-black/40">',
          '<i data-lucide="' + (champion ? 'crown' : rank === 2 ? 'medal' : 'award') + '" class="h-7 w-7"></i>',
          '</div>',
          '<p class="text-[10px] font-black uppercase tracking-[0.25em]">' + ordinal(rank) + '</p>',
          '<h4 class="mt-2 truncate font-display text-lg font-black text-white">' + esc(winnerLabel(tier)) + '</h4>',
          unresolved ? '<p class="mt-2 text-[10px] font-bold uppercase tracking-widest text-[#FFB800]">Placement unresolved</p>' : '',
          '<p class="mt-5 font-display text-2xl font-black text-white">' + money(data, tier.fiat) + '</p>',
          tier.coins ? '<p class="mt-1 text-xs font-mono text-[#00E5FF]">' + fmt(tier.coins) + ' DC</p>' : '',
          '</div>',
        ].join('');
      }).join(''),
      '</div>',
      '</section>',
    ].join('');
  }

  function standingsHtml(data) {
    var rows = data.standings && data.standings.length ? data.standings : (data.placements || []);
    if (!rows.length) return '';
    return [
      '<section class="' + PANEL + ' rounded-3xl overflow-hidden">',
      '<div class="border-b border-white/5 px-6 py-5 flex items-center justify-between">',
      '<h3 class="font-display text-lg font-black text-white">Detailed Standings</h3>',
      '<span class="text-[10px] font-mono uppercase tracking-widest text-slate-500">' + rows.length + ' rows</span>',
      '</div>',
      '<div class="divide-y divide-white/5">',
      rows.map(function (row) {
        var prize = row.prize || row;
        var rank = Number(row.rank || row.placement) || 0;
        var name = winnerLabel(row);
        return [
          '<div class="grid grid-cols-12 gap-3 px-6 py-4 items-center">',
          '<div class="col-span-2 sm:col-span-1 text-xs font-mono text-[#00E5FF]">' + esc(row.rank_label || ordinal(rank)) + '</div>',
          '<div class="col-span-10 sm:col-span-5 min-w-0">',
          '<p class="truncate text-sm font-bold text-white">' + esc(name) + '</p>',
          '<p class="mt-0.5 text-[10px] uppercase tracking-widest text-slate-500">' + esc(row.title || row.source || '') + '</p>',
          row.block_reason ? '<p class="mt-1 text-[10px] text-[#FFB800]">' + esc(row.block_reason) + '</p>' : '',
          '</div>',
          '<div class="col-span-6 sm:col-span-3 text-sm font-display font-black text-white">' + money(data, prize.fiat) + '</div>',
          '<div class="col-span-6 sm:col-span-3 text-right text-xs font-mono text-[#00E5FF]">' + fmt(prize.coins || 0) + ' DC</div>',
          '</div>',
        ].join('');
      }).join(''),
      '</div>',
      '</section>',
    ].join('');
  }

  function achievementsHtml(data, mode) {
    var rows = [];
    (data.derived_achievements || []).forEach(function (row) { rows.push({ row: row, awardIndex: null }); });
    (data.special_awards || []).forEach(function (row, idx) { rows.push({ row: row, awardIndex: idx }); });
    if (!rows.length) {
      (data.achievements || []).forEach(function (row) { rows.push({ row: row, awardIndex: null }); });
    }
    if (!rows.length) return '';
    return [
      '<section class="' + PANEL + ' rounded-3xl p-6">',
      '<div class="mb-5 flex items-center justify-between gap-4">',
      '<h3 class="font-display text-lg font-black text-white">Achievements & Special Awards</h3>',
      '<span class="text-[10px] font-mono uppercase tracking-widest text-slate-500">' + rows.length + ' awards</span>',
      '</div>',
      '<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">',
      rows.map(function (item) {
        var row = item.row || {};
        var reward = row.reward_text || (row.fiat ? money(data, row.fiat) : '') || (row.coins ? fmt(row.coins) + ' DC' : 'Award');
        var recipient = row.recipient_name || (row.awaiting_recipient ? 'Awaiting assignment' : '');
        return [
          '<article class="rounded-2xl border border-white/10 bg-black/30 p-5">',
          '<div class="flex items-start justify-between gap-3">',
          '<div class="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/5">',
          '<i data-lucide="' + esc(row.icon || 'award') + '" class="h-5 w-5 text-[#FFD700]"></i>',
          '</div>',
          mode === 'toc' && item.awardIndex !== null ? '<button data-ra-assign-award="' + item.awardIndex + '" class="rounded-lg border border-[#00E5FF]/30 px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-[#00E5FF]">Assign</button>' : '',
          '</div>',
          '<h4 class="mt-4 font-display text-base font-black text-white">' + esc(row.title || 'Achievement') + '</h4>',
          '<p class="mt-1 min-h-[34px] text-xs leading-relaxed text-slate-400">' + esc(row.description || '') + '</p>',
          '<p class="mt-4 text-xs font-mono text-[#00E5FF]">' + esc(reward) + '</p>',
          recipient ? '<p class="mt-2 text-[10px] font-bold uppercase tracking-widest text-[#FFD700]">' + esc(recipient) + '</p>' : '',
          '</article>',
        ].join('');
      }).join(''),
      '</div>',
      '</section>',
    ].join('');
  }

  function operationsHtml(data) {
    var ops = data.operations || {};
    var rows = ops.placements || [];
    if (!rows.length) return '';
    var resolution = (ops.status && ops.status.placement_resolution) || (data.result_status && data.result_status.placement_resolution) || {};
    return [
      '<section class="' + PANEL + ' rounded-3xl p-6">',
      '<div class="mb-5 flex items-center justify-between gap-4">',
      '<h3 class="font-display text-lg font-black text-white">Reward Operations</h3>',
      ops.status && ops.status.message ? '<span class="text-[10px] text-slate-500">' + esc(ops.status.message) + '</span>' : '',
      '</div>',
      resolution.message ? '<div class="mb-4 rounded-xl border border-[#FFB800]/25 bg-[#FFB800]/10 px-4 py-3 text-xs text-[#FFB800]"><i data-lucide="triangle-alert" class="mr-1 inline h-4 w-4"></i>' + esc(resolution.message) + '</div>' : '',
      '<div class="space-y-3">',
      rows.map(function (row) {
        var claim = row.claim || null;
        var payout = row.payout || {};
        var claimId = claim && claim.id ? claim.id : '';
        var rank = Number(row.rank || 0);
        var canAssignPlacement = rank === 3 || rank === 4 || !!row.placement_unresolved;
        var canCreateThirdPlace = !!(row.placement_unresolved && resolution.can_create_third_place_match);
        var thirdPlacePending = !!(row.placement_unresolved && resolution.third_place_match_exists && !resolution.third_place_match_completed);
        return [
          '<article class="rounded-2xl border border-white/10 bg-black/30 p-4">',
          '<div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">',
          '<div class="min-w-0">',
          '<p class="text-[10px] font-mono uppercase tracking-widest text-[#00E5FF]">' + esc(row.rank_label || ordinal(row.rank)) + '</p>',
          '<h4 class="mt-1 truncate font-display text-base font-black text-white">' + esc(winnerLabel(row)) + '</h4>',
          row.block_reason ? '<p class="mt-1 text-xs text-[#FFB800]">' + esc(row.block_reason) + '</p>' : '',
          '<div class="mt-3 flex flex-wrap gap-2">',
          badge(claim ? 'Claim ' + claim.status : 'No claim', claim && claim.status === 'paid' ? 'green' : 'gray'),
          badge('Payout ' + (payout.status || 'not_started'), payout.status === 'blocked' ? 'red' : 'cyan'),
          row.certificate ? badge('Certificate ' + row.certificate.status, 'green') : badge('Certificate pending', 'gray'),
          row.prize ? badge('Prize ' + prizeLabel(data, row.prize), 'gold') : '',
          '</div>',
          '</div>',
          '<div class="flex flex-wrap gap-2 lg:justify-end">',
          '<button class="' + BTN + ' opacity-60 cursor-not-allowed" disabled><i data-lucide="message-square" class="h-3 w-3"></i> Contact</button>',
          canCreateThirdPlace ? '<button data-ra-create-third-place class="' + BTN_WARN + '"><i data-lucide="medal" class="h-3 w-3"></i> Create Third Place Match</button>' : '',
          thirdPlacePending ? '<button class="' + BTN_WARN + ' opacity-60 cursor-not-allowed" disabled><i data-lucide="swords" class="h-3 w-3"></i> Play / Enter Result</button>' : '',
          canAssignPlacement ? '<button data-ra-assign-rank="' + row.rank + '" class="' + BTN + '"><i data-lucide="user-plus" class="h-3 w-3"></i> Manual Assign</button>' : '',
          '<button data-ra-claim="approve" data-claim-id="' + claimId + '" class="' + BTN + '" ' + (claimId ? '' : 'disabled') + '>Approve</button>',
          '<button data-ra-claim="reject" data-claim-id="' + claimId + '" class="' + BTN_DANGER + '" ' + (claimId ? '' : 'disabled') + '>Reject</button>',
          '<button data-ra-claim="mark_paid" data-claim-id="' + claimId + '" class="' + BTN_GOOD + '" ' + (claimId && !row.payout_blocked ? '' : 'disabled') + '>Mark Paid</button>',
          '</div>',
          '</div>',
          '</article>',
        ].join('');
      }).join(''),
      '</div>',
      '</section>',
    ].join('');
  }

  function hubOwnResultHtml(data) {
    if (!data.your_result && !data.your_prizes) return '';
    var result = data.your_result || {};
    var prizes = data.your_prizes || [];
    var claimable = prizes.filter(function (p) {
      return !p.claimed && (!p.status || p.status === 'pending' || p.status === 'completed');
    });
    return [
      '<section class="' + PANEL + ' rounded-3xl p-6 border-[#00E5FF]/25">',
      '<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">',
      '<div>',
      '<h3 class="font-display text-lg font-black text-white">Your Result</h3>',
      result.rank ? '<p class="mt-2 text-sm text-slate-300">' + esc(result.rank_label || ordinal(result.rank)) + ' - ' + esc(result.title || 'Placement') + '</p>' : '<p class="mt-2 text-sm text-slate-400">No prize placement recorded for your registration.</p>',
      '<div class="mt-4 flex flex-wrap gap-2">',
      result.claimable ? badge('Claim available', 'gold') : '',
      result.claim && result.claim.status ? badge('Claim ' + result.claim.status, 'gold') : '',
      result.payout && result.payout.status ? badge('Payout ' + result.payout.status, 'cyan') : '',
      result.certificate ? badge('Certificate available', 'green') : '',
      prizes.length ? badge(prizes.length + ' prize item(s)', 'gold') : '',
      '</div>',
      '</div>',
      '<div class="flex flex-wrap gap-2 lg:justify-end">',
      claimable.length ? claimable.map(function (p) {
        return '<button data-ra-claim-prize data-tx-id="' + esc(p.id) + '" data-amount="' + esc(p.amount || '') + '" data-placement="' + esc(p.placement_display || p.placement || '') + '" class="' + BTN_GOOD + '"><i data-lucide="wallet" class="h-3 w-3"></i> Claim Prize</button>';
      }).join('') : '<button class="' + BTN + ' opacity-60 cursor-not-allowed" disabled><i data-lucide="wallet" class="h-3 w-3"></i> Claim Status</button>',
      '<button class="' + BTN + ' opacity-60 cursor-not-allowed" disabled><i data-lucide="message-square" class="h-3 w-3"></i> Contact Organizer</button>',
      '</div>',
      '</div>',
      '</section>',
    ].join('');
  }

  function summaryHtml(data, mode) {
    var status = data.result_status || {};
    var resolution = status.placement_resolution || {};
    return [
      '<aside class="xl:col-span-3 space-y-4">',
      '<section class="' + PANEL + ' rounded-3xl p-6">',
      '<p class="text-[10px] font-black uppercase tracking-[0.3em] text-[#00E5FF]">Results Engine</p>',
      '<h2 class="mt-2 font-display text-3xl font-black text-white">Results & Achievements</h2>',
      '<p class="mt-3 text-sm leading-relaxed text-slate-400">Final placements, rewards, claims, payouts, certificates, and special awards.</p>',
      '<div class="mt-6 rounded-2xl border border-white/10 bg-black/35 p-4">',
      '<p class="text-[10px] uppercase tracking-widest text-slate-500">Prize Pool</p>',
      '<p class="mt-1 font-display text-3xl font-black text-white">' + money(data, data.fiat_pool) + '</p>',
      '<p class="text-xs font-mono text-[#00E5FF]">' + fmt(data.coin_pool || 0) + ' DC</p>',
      '</div>',
      '<div class="mt-4 flex flex-wrap gap-2">',
      status.completed ? badge('Completed', 'green') : badge('In progress', 'gray'),
      status.finalized ? badge('Finalized', 'gold') : badge('Not finalized', 'gray'),
      resolution.message ? badge('Placement action needed', 'red') : '',
      '</div>',
      mode === 'toc' ? '<div class="mt-5 rounded-xl border border-[#FFB800]/25 bg-[#FFB800]/10 p-3 text-xs text-[#FFB800]">Payment and prize-send controls are visible in TOC only. Contact is a placeholder until messaging is integrated.</div>' : '',
      '</section>',
      '</aside>',
    ].join('');
  }

  function render(root, data) {
    var mode = root.getAttribute('data-results-mode') || 'public';
    root.__raData = data;
    root.innerHTML = [
      '<div class="grid grid-cols-1 xl:grid-cols-12 gap-8">',
      summaryHtml(data, mode),
      '<main class="xl:col-span-9 space-y-8 min-w-0">',
      mode === 'hub' ? hubOwnResultHtml(data) : '',
      podiumHtml(data),
      standingsHtml(data),
      achievementsHtml(data, mode),
      mode === 'toc' ? operationsHtml(data) : '',
      '</main></div>',
    ].join('');
    if (window.lucide && typeof window.lucide.createIcons === 'function') window.lucide.createIcons();
  }

  function recipientModal(root, mode, meta) {
    var modal = document.getElementById('ra-recipient-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'ra-recipient-modal';
      modal.className = 'hidden fixed inset-0 z-[400] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm';
      modal.innerHTML = '<div class="w-full max-w-xl rounded-2xl border border-white/10 bg-[#12121A] p-5"><div class="flex items-center justify-between gap-3"><h3 class="font-display text-lg font-black text-white">Select Recipient</h3><button data-ra-close class="text-slate-400 hover:text-white"><i data-lucide="x" class="h-5 w-5"></i></button></div><input data-ra-search type="search" class="mt-4 w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none" placeholder="Search participant or team"><div data-ra-results class="mt-4 max-h-80 overflow-y-auto space-y-2"></div></div>';
      document.body.appendChild(modal);
    }
    modal.__root = root;
    modal.__mode = mode;
    modal.__meta = meta || {};
    modal.classList.remove('hidden');
    var search = modal.querySelector('[data-ra-search]');
    search.value = '';
    search.focus();
    searchRecipients(modal, '');
    modal.onclick = function (event) {
      if (event.target === modal || event.target.closest('[data-ra-close]')) modal.classList.add('hidden');
      var pick = event.target.closest('[data-ra-pick]');
      if (!pick) return;
      chooseRecipient(modal, Number(pick.getAttribute('data-id')), pick.getAttribute('data-name') || '');
    };
    search.oninput = debounce(function () { searchRecipients(modal, search.value); }, 180);
    if (window.lucide) window.lucide.createIcons();
  }

  function debounce(fn, delay) {
    var timer = null;
    return function () {
      var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(null, args); }, delay);
    };
  }

  function searchRecipients(modal, query) {
    var root = modal.__root;
    var base = root.getAttribute('data-api-base') || '';
    var results = modal.querySelector('[data-ra-results]');
    results.innerHTML = '<p class="text-xs text-slate-500">Searching...</p>';
    apiFetch(base + '/prizes/recipients/?q=' + encodeURIComponent(query || '')).then(function (data) {
      var rows = data.results || [];
      results.innerHTML = rows.length ? rows.map(function (row) {
        return '<button data-ra-pick data-id="' + row.registration_id + '" data-name="' + esc(row.name || '') + '" class="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-left hover:border-[#00E5FF]/40"><span class="block text-sm font-bold text-white">' + esc(row.name || '') + '</span><span class="block text-[10px] text-slate-500">' + esc(row.subtitle || '') + '</span></button>';
      }).join('') : '<p class="text-xs text-slate-500">No matching recipients.</p>';
    }).catch(function () {
      results.innerHTML = '<p class="text-xs text-rose-300">Recipient search failed.</p>';
    });
  }

  function chooseRecipient(modal, id, name) {
    var root = modal.__root;
    var base = root.getAttribute('data-api-base') || '';
    var meta = modal.__meta || {};
    var data = root.__raData || {};
    if (modal.__mode === 'rank') {
      apiFetch(base + '/prizes/placements/assign/', { method: 'POST', body: { rank: meta.rank, recipient_id: id } })
        .then(function (payload) { render(root, normalizePayload(payload)); modal.classList.add('hidden'); });
      return;
    }
    if (modal.__mode === 'award') {
      var cfg = data.config || {};
      var awards = cfg.special_awards || [];
      if (awards[meta.index]) {
        awards[meta.index].recipient_id = id;
        awards[meta.index].recipient_name = name;
      }
      apiFetch(base + '/prizes/save/', { method: 'POST', body: cfg })
        .then(function (payload) { render(root, normalizePayload(payload)); modal.classList.add('hidden'); });
    }
  }

  function wire(root) {
    root.addEventListener('click', function (event) {
      var base = root.getAttribute('data-api-base') || '';
      if (event.target.closest('[data-ra-create-third-place]')) {
        apiFetch(base + '/prizes/bronze/create/', { method: 'POST' }).then(function (payload) { render(root, normalizePayload(payload)); });
        return;
      }
      var hubClaim = event.target.closest('[data-ra-claim-prize]');
      if (hubClaim) {
        if (window.HubEngine && typeof window.HubEngine.openPrizeModal === 'function') {
          window.HubEngine.openPrizeModal(
            hubClaim.getAttribute('data-tx-id') || '',
            hubClaim.getAttribute('data-amount') || '',
            hubClaim.getAttribute('data-placement') || ''
          );
        }
        return;
      }
      var assign = event.target.closest('[data-ra-assign-rank]');
      if (assign) {
        recipientModal(root, 'rank', { rank: Number(assign.getAttribute('data-ra-assign-rank') || 0) });
        return;
      }
      var award = event.target.closest('[data-ra-assign-award]');
      if (award) {
        recipientModal(root, 'award', { index: Number(award.getAttribute('data-ra-assign-award') || 0) });
        return;
      }
      var claim = event.target.closest('[data-ra-claim]');
      if (claim && !claim.disabled) {
        apiFetch(base + '/prizes/claims/' + claim.getAttribute('data-claim-id') + '/action/', {
          method: 'POST',
          body: { action: claim.getAttribute('data-ra-claim') },
        }).then(function (payload) { render(root, normalizePayload(payload)); });
      }
    });
  }

  function load(root) {
    var url = root.getAttribute('data-results-url');
    if (!url) return;
    root.innerHTML = '<div class="' + PANEL + ' rounded-3xl p-8 text-sm text-slate-400">Loading results...</div>';
    apiFetch(url).then(function (data) {
      render(root, normalizePayload(data));
    }).catch(function (error) {
      root.innerHTML = '<div class="' + PANEL + ' rounded-3xl p-8 text-sm text-rose-300">' + esc(error.message || 'Results unavailable.') + '</div>';
    });
  }

  function init() {
    document.querySelectorAll('[data-results-achievements-engine]').forEach(function (root) {
      if (root.__raReady) return;
      root.__raReady = true;
      wire(root);
      load(root);
    });
  }

  document.addEventListener('DOMContentLoaded', init);
  document.addEventListener('toc:tab-changed', function (event) {
    if (event.detail && event.detail.tab === 'results-achievements') init();
  });
  document.addEventListener('hub:tab-activated', function (event) {
    if (event.detail && event.detail.tab === 'results-achievements') init();
  });
  if (document.readyState !== 'loading') init();
})();
