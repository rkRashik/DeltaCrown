/**
 * Public tournament detail — prize tab renderer.
 *
 * CSP-safe static file that hydrates #prize-distribution-panel with live
 * placement tiers and special awards from /tournaments/<slug>/api/prizes/.
 * Loaded via <script src> from templates/tournaments/detailPages/detail.html.
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
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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

        var placements = data.placements || [];
        if (placements.length) {
          var list = document.getElementById('prize-engine-placements');
          if (list) {
            list.innerHTML = '';
            placements.forEach(function (tier) {
              var winnerName = tier.winner ? esc(tier.winner.team_name || '') : '';
              var currPrefix = (data.currency === 'BDT' || !data.currency) ? '৳' : (data.currency + ' ');
              var fiatLabel = tier.fiat ? (currPrefix + fmt(tier.fiat)) : 'TBA';
              var coinsSpan = tier.coins
                ? '<span class="text-xs text-dc-cyan ml-2">+ ' + fmt(tier.coins) + ' DC</span>'
                : '';
              var row = document.createElement('div');
              row.className = 'flex items-center justify-between p-6 hover:bg-white/[0.02] transition-colors group';
              var winnerHtml = winnerName
                ? '<div class="text-xs text-dc-gold mt-1">' + winnerName + '</div>'
                : '';
              row.innerHTML = [
                '<div class="flex items-center gap-6">',
                '<div class="w-12 h-12 rounded-xl bg-black/50 border border-white/5 flex items-center justify-center font-display font-bold text-gray-400 text-lg">',
                ordinal(tier.rank),
                '</div>',
                '<div>',
                '<div class="font-bold text-white text-base">' + esc(tier.title || '') + '</div>',
                winnerHtml,
                '</div>',
                '</div>',
                '<div class="flex items-center gap-8">',
                '<span class="font-display font-bold text-2xl text-white">' + fiatLabel + '</span>',
                coinsSpan,
                '</div>',
              ].join('');
              list.appendChild(row);
            });
          }
        }

        if (data.finalized) {
          var badge = document.getElementById('prize-engine-finalized-badge');
          if (badge) badge.classList.remove('hidden');
        }

        var awards = data.special_awards || [];
        if (awards.length) {
          var awardsBlock = document.getElementById('prize-engine-special-awards');
          var awardsList = document.getElementById('prize-engine-special-list');
          if (awardsBlock && awardsList) {
            awardsList.innerHTML = '';
            awards.forEach(function (a) {
              var fiatTxt = a.fiat ? '৳' + fmt(a.fiat) : '';
              var coinsTxt = a.coins ? fmt(a.coins) + ' DC' : '';
              var rewardTxt = a.reward_text ? esc(a.reward_text) : (fiatTxt || coinsTxt || 'Award');
              var card = document.createElement('div');
              card.className = 'rounded-xl border border-white/10 bg-black/40 p-4';
              card.innerHTML = [
                '<div class="flex items-start gap-3">',
                '<div class="w-10 h-10 rounded-lg bg-dc-gold/10 border border-dc-gold/20 flex items-center justify-center text-dc-gold">',
                '<i data-lucide="' + esc(a.icon || 'medal') + '" class="w-5 h-5"></i>',
                '</div>',
                '<div class="min-w-0 flex-1">',
                '<div class="text-sm font-bold text-white">' + esc(a.title || '') + '</div>',
                '<div class="text-xs text-gray-400 mt-1">' + esc(a.description || '') + '</div>',
                '<div class="text-xs font-mono text-dc-gold mt-2">' + rewardTxt + (fiatTxt && coinsTxt ? ' · ' + coinsTxt : '') + '</div>',
                '</div>',
                '</div>',
              ].join('');
              awardsList.appendChild(card);
            });
            awardsBlock.classList.remove('hidden');
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
              window.lucide.createIcons();
            }
          }
        }
      })
      .catch(function () { /* static markup fallback remains */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
