/**
 * Hub Prize Engine — public/participant prize tab loader.
 *
 * Hits /tournaments/<slug>/api/prizes/ via the URL stamped onto the
 * `#hub-prize-engine` root by the template, then renders:
 *   * Pool: total fiat + DeltaCoin
 *   * Placement tier cards (with winner names when finalized)
 *   * Special awards grid
 *
 * Lives as a static file so CSP doesn't refuse inline scripts.
 */
(function () {
  'use strict';

  function init() {
    var root = document.getElementById('hub-prize-engine');
    if (!root) return;
    var url = root.getAttribute('data-prize-overview-url');
    if (!url) return;

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

    function setHidden(id, hidden) {
      var el = document.getElementById(id);
      if (el) el.classList.toggle('hidden', !!hidden);
    }

    function renderPool(data) {
      var pool = document.getElementById('prize-engine-pool');
      if (!pool) return;
      pool.classList.remove('hidden');
      var fiatEl = document.getElementById('prize-engine-fiat');
      var currencyEl = document.getElementById('prize-engine-currency');
      var coinsEl = document.getElementById('prize-engine-coins');
      if (fiatEl) fiatEl.textContent = data.fiat_pool ? '৳' + fmt(data.fiat_pool) : 'TBA';
      if (currencyEl) currencyEl.textContent = data.currency || 'BDT';
      if (coinsEl) coinsEl.textContent = fmt(data.coin_pool || 0);
      setHidden('prize-engine-finalized', !data.finalized);
      setHidden('prize-engine-certs', !data.certificates_enabled);
    }

    function renderTiers(data) {
      var tiers = (data.placements || []).filter(function (t) { return t && t.rank; });
      if (!tiers.length) return;
      var wrap = document.getElementById('prize-engine-tiers-wrap');
      var grid = document.getElementById('prize-engine-tiers');
      if (wrap) wrap.classList.remove('hidden');
      if (!grid) return;
      grid.innerHTML = '';
      tiers.forEach(function (tier) {
        var isChamp = tier.rank === 1;
        var winnerHtml = tier.winner
          ? '<div class="text-xs text-[#FFB800] font-bold mt-2 truncate">' + esc(tier.winner.team_name || '') + '</div>'
          : '';
        var fiatLabel = tier.fiat ? '৳' + fmt(tier.fiat) : 'TBA';
        var coinsLabel = tier.coins ? fmt(tier.coins) + ' DC' : '';
        var card = document.createElement('div');
        card.className = 'rounded-xl border ' +
          (isChamp ? 'border-[#FFB800]/40 bg-[#FFB800]/5' : 'border-white/5 bg-black/20') +
          ' p-4';
        card.innerHTML =
          '<p class="text-[10px] font-black uppercase tracking-widest ' +
          (isChamp ? 'text-[#FFB800]' : 'text-gray-500') + ' mb-1">' + ordinal(tier.rank) + '</p>' +
          '<h4 class="text-base font-bold text-white mb-1 truncate">' + esc(tier.title || '') + '</h4>' +
          winnerHtml +
          '<div class="flex items-baseline gap-3 mt-3">' +
            '<span class="text-2xl font-black text-white" style="font-family:Outfit,sans-serif;">' + fiatLabel + '</span>' +
            (coinsLabel
              ? '<span class="text-xs font-bold text-[#00F0FF]">+' + coinsLabel + '</span>'
              : '') +
          '</div>';
        grid.appendChild(card);
      });
    }

    function renderAwards(data) {
      var awards = data.special_awards || [];
      if (!awards.length) return;
      var wrap = document.getElementById('prize-engine-awards-wrap');
      var aroot = document.getElementById('prize-engine-awards');
      if (wrap) wrap.classList.remove('hidden');
      if (!aroot) return;
      aroot.innerHTML = '';
      awards.forEach(function (a) {
        var fiatTxt = a.fiat ? '৳' + fmt(a.fiat) : '';
        var coinsTxt = a.coins ? fmt(a.coins) + ' DC' : '';
        var rewardTxt = a.reward_text ? esc(a.reward_text) : (fiatTxt || coinsTxt || 'Award');
        var card = document.createElement('div');
        card.className = 'rounded-xl border border-white/5 bg-black/20 p-4 flex items-start gap-3';
        card.innerHTML =
          '<div class="w-10 h-10 rounded-lg bg-[#FFB800]/10 border border-[#FFB800]/20 flex items-center justify-center text-[#FFB800] flex-shrink-0">' +
            '<i data-lucide="' + esc(a.icon || 'medal') + '" class="w-5 h-5"></i>' +
          '</div>' +
          '<div class="min-w-0 flex-1">' +
            '<div class="text-sm font-bold text-white">' + esc(a.title || '') + '</div>' +
            '<div class="text-xs text-gray-400 mt-1">' + esc(a.description || '') + '</div>' +
            '<div class="text-xs font-mono text-[#FFB800] mt-2">' + rewardTxt +
              (fiatTxt && coinsTxt ? ' · ' + coinsTxt : '') +
            '</div>' +
          '</div>';
        aroot.appendChild(card);
      });
    }

    function loadOnce() {
      // Idempotent: if already loaded, do nothing.
      if (root.dataset.prizeLoaded === '1') return;
      root.dataset.prizeLoaded = '1';

      fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
          var loader = document.getElementById('prize-engine-loading');
          if (loader) loader.classList.add('hidden');
          if (!data) return;
          renderPool(data);
          renderTiers(data);
          renderAwards(data);
          if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
          }
        })
        .catch(function () {
          var loader = document.getElementById('prize-engine-loading');
          if (loader) {
            loader.classList.remove('animate-pulse');
            loader.innerHTML = '<p class="text-xs text-gray-500">Prize information unavailable.</p>';
          }
          // Reset flag so a manual retry can re-enter.
          root.dataset.prizeLoaded = '';
        });
    }

    // Load on first paint AND whenever the Prizes tab activates so users
    // who navigate to it after page load still see the data.
    loadOnce();

    document.addEventListener('hub:tab-activated', function (e) {
      if (e && e.detail && e.detail.tab === 'prizes') {
        // Allow re-render if the engine root was rebuilt.
        if (!document.getElementById('prize-engine-pool') ||
            document.getElementById('prize-engine-pool').classList.contains('hidden')) {
          root.dataset.prizeLoaded = '';
          loadOnce();
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
