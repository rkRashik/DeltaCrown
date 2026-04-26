/**
 * Public tournament detail - prize/results tab renderer.
 *
 * Hydrates the public Results & Rewards payload from the shared read model.
 * Static-file only so the tab remains CSP-safe.
 */
(function () {
  'use strict';

  function ordinal(n) {
    n = Number(n) || 0;
    var v = n % 100;
    if (v >= 11 && v <= 13) return n + 'th';
    var s = { 1: 'st', 2: 'nd', 3: 'rd' };
    return n + (s[n % 10] || 'th');
  }

  function fmt(n) {
    return (Number(n) || 0).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function money(data, amount) {
    amount = Number(amount) || 0;
    if (!amount) return 'TBA';
    return (data.currency || 'BDT') + ' ' + fmt(amount);
  }

  function isCompleted(data) {
    return !!(data.result_status && data.result_status.completed);
  }

  function winnerLabel(tier, data) {
    if (tier && tier.winner && tier.winner.team_name) return esc(tier.winner.team_name);
    if (tier && tier.result_label) return esc(tier.result_label);
    return isCompleted(data) ? 'Result pending' : 'Pending';
  }

  function show(id) {
    var el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
  }

  function reinitIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  function renderPodium(data) {
    var wrap = document.getElementById('prize-engine-podium-public-wrap');
    var grid = document.getElementById('prize-engine-podium-public');
    var podium = (data.placements || []).slice(0, 3);
    if (!wrap || !grid || !podium.length) return;
    var order = podium.length === 3 ? [1, 0, 2] : podium.map(function (_, i) { return i; });
    grid.innerHTML = order.map(function (slot) {
      var tier = podium[slot];
      if (!tier) return '';
      var winner = winnerLabel(tier, data);
      var cert = tier.certificate_badge && tier.certificate_badge.enabled
        ? '<div class="text-[10px] font-mono text-emerald-300 mt-3 uppercase tracking-widest">Certificate ' + esc(tier.certificate_badge.status || 'pending') + '</div>'
        : '';
      var accent = tier.rank === 1 ? 'border-dc-gold/40 bg-dc-gold/10' : 'border-white/10 bg-black/40';
      return [
        '<div class="rounded-2xl border ' + accent + ' p-5 text-center">',
        '<div class="text-[10px] uppercase tracking-[0.25em] text-gray-400">' + ordinal(tier.rank) + '</div>',
        '<div class="text-lg font-display font-black text-white mt-1">' + esc(tier.title || '') + '</div>',
        '<div class="text-sm text-dc-gold mt-2 truncate">' + winner + '</div>',
        '<div class="text-2xl font-display font-black text-white mt-4">' + money(data, tier.fiat) + '</div>',
        tier.coins ? '<div class="text-xs font-mono text-dc-cyan mt-1">' + fmt(tier.coins) + ' DC</div>' : '',
        cert,
        '</div>'
      ].join('');
    }).join('');
    wrap.classList.remove('hidden');
  }

  function renderPlacements(data) {
    var list = document.getElementById('prize-engine-placements');
    var placements = data.placements || [];
    if (!list || !placements.length) return;
    list.innerHTML = placements.map(function (tier) {
      var winnerName = winnerLabel(tier, data);
      var winnerTone = tier.winner && tier.winner.team_name ? 'text-dc-gold' : 'text-gray-500';
      var coinsSpan = tier.coins
        ? '<span class="text-xs text-dc-cyan ml-2">+ ' + fmt(tier.coins) + ' DC</span>'
        : '';
      return [
        '<div class="flex items-center justify-between gap-4 p-6 hover:bg-white/[0.02] transition-colors group">',
        '<div class="flex items-center gap-6 min-w-0">',
        '<div class="w-12 h-12 rounded-xl bg-black/50 border border-white/5 flex items-center justify-center font-display font-bold text-gray-400 text-lg">' + ordinal(tier.rank) + '</div>',
        '<div class="min-w-0">',
        '<div class="font-bold text-white text-base truncate">' + esc(tier.title || '') + '</div>',
        '<div class="text-xs ' + winnerTone + ' mt-1 truncate">' + winnerName + '</div>',
        '</div>',
        '</div>',
        '<div class="flex items-center gap-4 text-right shrink-0">',
        '<span class="font-display font-bold text-2xl text-white">' + money(data, tier.fiat) + '</span>',
        coinsSpan,
        '</div>',
        '</div>'
      ].join('');
    }).join('');
  }

  function renderStandings(data) {
    var wrap = document.getElementById('prize-engine-standings-wrap');
    var list = document.getElementById('prize-engine-standings');
    var standings = data.standings || [];
    if (!wrap || !list || !standings.length) return;
    list.innerHTML = standings.map(function (row) {
      var prize = row.prize || {};
      var cert = row.certificate_badge && row.certificate_badge.enabled
        ? '<span class="text-[10px] font-mono text-emerald-300 uppercase tracking-widest">Certificate ' + esc(row.certificate_badge.status || 'pending') + '</span>'
        : '';
      return [
        '<div class="flex items-center justify-between gap-4 p-5">',
        '<div class="flex items-center gap-4 min-w-0">',
        '<div class="w-10 h-10 rounded-full bg-black/50 border border-white/10 flex items-center justify-center text-xs font-mono text-gray-300">' + esc(row.rank_label || ordinal(row.rank)) + '</div>',
        '<div class="min-w-0">',
        '<div class="text-sm font-bold text-white truncate">' + esc(row.team_name || '') + '</div>',
        '<div class="text-[10px] uppercase tracking-widest text-gray-500 mt-0.5">' + esc(row.title || '') + '</div>',
        '</div>',
        '</div>',
        '<div class="text-right shrink-0">',
        '<div class="text-sm font-display font-bold text-white">' + money(data, prize.fiat) + '</div>',
        '<div class="text-[10px] font-mono text-dc-cyan">' + fmt(prize.coins || 0) + ' DC</div>',
        cert,
        '</div>',
        '</div>'
      ].join('');
    }).join('');
    wrap.classList.remove('hidden');
  }

  function renderAwards(data) {
    var awards = data.special_awards && data.special_awards.length
      ? data.special_awards
      : (data.achievements || data.derived_achievements || []);
    var awardsBlock = document.getElementById('prize-engine-special-awards');
    var awardsList = document.getElementById('prize-engine-special-list');
    if (!awardsBlock || !awardsList || !awards.length) return;
    awardsList.innerHTML = awards.map(function (a) {
      var fiatTxt = a.fiat ? money(data, a.fiat) : '';
      var coinsTxt = a.coins ? fmt(a.coins) + ' DC' : '';
      var rewardTxt = a.reward_text ? esc(a.reward_text) : (fiatTxt || coinsTxt || 'Award');
      var recipient = a.recipient_name
        ? '<div class="text-xs text-dc-gold mt-2">Recipient: ' + esc(a.recipient_name) + '</div>'
        : '<div class="text-xs text-gray-500 mt-2">Awaiting assignment</div>';
      return [
        '<div class="rounded-xl border border-white/10 bg-black/40 p-4">',
        '<div class="flex items-start gap-3">',
        '<div class="w-10 h-10 rounded-lg bg-dc-gold/10 border border-dc-gold/20 flex items-center justify-center text-dc-gold">',
        '<i data-lucide="' + esc(a.icon || 'medal') + '" class="w-5 h-5"></i>',
        '</div>',
        '<div class="min-w-0 flex-1">',
        '<div class="text-sm font-bold text-white">' + esc(a.title || '') + '</div>',
        '<div class="text-xs text-gray-400 mt-1">' + esc(a.description || '') + '</div>',
        '<div class="text-xs font-mono text-dc-gold mt-2">' + rewardTxt + (fiatTxt && coinsTxt ? ' - ' + coinsTxt : '') + '</div>',
        recipient,
        '</div>',
        '</div>',
        '</div>'
      ].join('');
    }).join('');
    awardsBlock.classList.remove('hidden');
  }

  function renderEmpty(data) {
    var states = data.empty_states || {};
    if (!states.no_placements && !states.no_prize_configured) return;
    var detail = document.getElementById('prize-engine-panel-empty-detail');
    if (detail && data.result_status) detail.textContent = data.result_status.message || detail.textContent;
    show('prize-engine-panel-empty');
  }

  function init() {
    var panel = document.getElementById('prize-distribution-panel');
    if (!panel) return;
    var url = panel.getAttribute('data-prize-overview-url');
    if (!url) return;

    fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        renderPodium(data);
        renderPlacements(data);
        renderStandings(data);
        renderAwards(data);
        renderEmpty(data);
        if (data.result_status && data.result_status.placements_published) {
          show('prize-engine-finalized-badge');
        }
        reinitIcons();
      })
      .catch(function () { /* static markup fallback remains */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
