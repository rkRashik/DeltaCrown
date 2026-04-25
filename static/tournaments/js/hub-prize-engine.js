/**
 * Hub Prize Engine — premium public/HUB prize tab renderer.
 *
 * Reads the URL stamped onto `#hub-prize-engine` (data-prize-overview-url)
 * and renders:
 *   * Hero: total fiat + DeltaCoin pool
 *   * Podium: top-3 cards (Champion centered + elevated)
 *   * All placements list (rank 4..N)
 *   * Special accolades grid
 *
 * CSP-safe: lives as a static file, no inline script. Loaded via
 * <script src> from templates/tournaments/hub/hub.html.
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
    function show(id) { setHidden(id, false); }

    function renderPool(data) {
      show('prize-engine-pool');
      var fiatEl = document.getElementById('prize-engine-fiat');
      var currencyEl = document.getElementById('prize-engine-currency');
      var coinsEl = document.getElementById('prize-engine-coins');
      if (fiatEl) fiatEl.textContent = data.fiat_pool ? '৳' + fmt(data.fiat_pool) : 'TBA';
      if (currencyEl) currencyEl.textContent = data.currency || 'BDT';
      if (coinsEl) coinsEl.textContent = fmt(data.coin_pool || 0);
      if (data.finalized) show('prize-engine-finalized');
      if (data.certificates_enabled) show('prize-engine-certs');
    }

    var podiumStyles = [
      { iconBg: 'bg-gradient-to-br from-yellow-300 to-[#FFB800]',
        iconColor: 'text-black', icon: 'crown',
        ringClass: 'border-[#FFB800]/40 shadow-[0_10px_60px_rgba(255,184,0,0.2)]',
        labelColor: 'text-[#FFB800]',
        elevation: 'md:-translate-y-4' },
      { iconBg: 'bg-gradient-to-br from-gray-200 to-gray-400',
        iconColor: 'text-black', icon: 'medal',
        ringClass: 'border-white/10',
        labelColor: 'text-gray-300',
        elevation: '' },
      { iconBg: 'bg-gradient-to-br from-[#CD7F32] to-[#8B5A2B]',
        iconColor: 'text-white', icon: 'award',
        ringClass: 'border-[#CD7F32]/30',
        labelColor: 'text-[#CD7F32]',
        elevation: '' },
    ];

    function podiumCard(tier, idx, currency) {
      var style = podiumStyles[idx] || podiumStyles[2];
      var winner = tier.winner ? esc(tier.winner.team_name || '') : '';
      var fiatLabel = tier.fiat ? '৳' + fmt(tier.fiat) : 'TBA';
      var coinsLabel = tier.coins ? '+ ' + fmt(tier.coins) + ' DC' : '';
      var winnerHtml = winner
        ? '<p class="text-sm font-bold text-white truncate mt-1">' + winner + '</p>'
        : '<p class="text-xs text-gray-500 mt-1">Awaiting winner</p>';
      var coinsHtml = coinsLabel
        ? '<div class="inline-flex items-center gap-1.5 px-3 py-1 mt-3 rounded-lg bg-[#00F0FF]/10 border border-[#00F0FF]/20 text-xs font-bold text-[#00F0FF]"><i data-lucide="coins" class="w-3 h-3"></i><span>' + coinsLabel + '</span></div>'
        : '';
      var parts = [
        '<div class="relative overflow-hidden rounded-3xl hub-glass border ' + style.ringClass + ' p-6 md:p-8 ' + style.elevation + ' transition-all">',
        '<div class="absolute top-2 right-3 font-black opacity-10 text-7xl text-white pointer-events-none" style="font-family:Outfit,sans-serif;">' + (idx + 1) + '</div>',
        '<div class="relative z-10 space-y-4">',
        '<div class="w-14 h-14 rounded-2xl ' + style.iconBg + ' flex items-center justify-center shadow-lg">',
        '<i data-lucide="' + style.icon + '" class="w-7 h-7 ' + style.iconColor + '"></i>',
        '</div>',
        '<div>',
        '<p class="text-[10px] font-bold uppercase tracking-[0.2em] ' + style.labelColor + ' mb-1">' + ordinal(tier.rank) + ' · ' + esc(tier.title || '') + '</p>',
        winnerHtml,
        '</div>',
        '<div>',
        '<h4 class="text-3xl md:text-4xl font-black text-white tracking-tight" style="font-family:Outfit,sans-serif;">' + fiatLabel + '</h4>',
        coinsHtml,
        '</div>',
        '</div>',
        '</div>'
      ];
      return parts.join('');
    }

    function renderPodium(data) {
      var top3 = (data.placements || []).slice(0, 3);
      if (!top3.length) return;
      var podium = document.getElementById('prize-engine-podium');
      var wrap = document.getElementById('prize-engine-podium-wrap');
      if (wrap) wrap.classList.remove('hidden');
      if (!podium) return;
      // Visual order: silver / gold / bronze on desktop; rank order on mobile.
      var visualOrder = top3.length === 3 ? [1, 0, 2] : top3.map(function (_, i) { return i; });
      var html = visualOrder.map(function (i) {
        var tier = top3[i];
        if (!tier) return '';
        return podiumCard(tier, i, data.currency);
      }).join('');
      podium.innerHTML = html;
    }

    function renderExtendedTiers(data) {
      var rest = (data.placements || []).slice(3);
      if (!rest.length) return;
      var wrap = document.getElementById('prize-engine-tiers-wrap');
      var list = document.getElementById('prize-engine-tiers');
      if (wrap) wrap.classList.remove('hidden');
      if (!list) return;
      list.innerHTML = rest.map(function (tier) {
        var winner = tier.winner ? esc(tier.winner.team_name || '') : '';
        var fiatTxt = tier.fiat ? '৳' + fmt(tier.fiat) : '—';
        var coinsTxt = tier.coins ? fmt(tier.coins) + ' DC' : '';
        return ''
          + '<div class="flex items-center justify-between p-5 hover:bg-white/[0.02] transition-colors">'
          +   '<div class="flex items-center gap-5">'
          +     '<div class="w-10 h-10 rounded-full bg-black/40 border border-white/5 flex items-center justify-center font-mono font-bold text-gray-400 text-sm">' + ordinal(tier.rank) + '</div>'
          +     '<div>'
          +       '<p class="text-sm font-bold text-white">' + esc(tier.title || '') + '</p>'
          +       (winner ? '<p class="text-xs text-[#FFB800] mt-0.5">' + winner + '</p>' : '')
          +     '</div>'
          +   '</div>'
          +   '<div class="text-right">'
          +     '<p class="text-xl font-black text-white" style="font-family:Outfit,sans-serif;">' + fiatTxt + '</p>'
          +     (coinsTxt ? '<p class="text-[10px] font-mono text-[#00F0FF] mt-0.5">' + coinsTxt + '</p>' : '')
          +   '</div>'
          + '</div>';
      }).join('');
    }

    function renderAwards(data) {
      var awards = data.special_awards || [];
      if (!awards.length) return;
      var wrap = document.getElementById('prize-engine-awards-wrap');
      var grid = document.getElementById('prize-engine-awards');
      if (wrap) wrap.classList.remove('hidden');
      if (!grid) return;
      grid.innerHTML = awards.map(function (a) {
        var fiatTxt = a.fiat ? '৳' + fmt(a.fiat) : '';
        var coinsTxt = a.coins ? fmt(a.coins) + ' DC' : '';
        var rewardTxt = a.reward_text ? esc(a.reward_text) : (fiatTxt || coinsTxt || 'Award');
        var typeBadge = (a.type || 'cash').toUpperCase();
        var bonusHtml = coinsTxt
          ? '<div class="text-right"><p class="text-[9px] font-bold text-[#00F0FF] uppercase tracking-widest">Bonus</p><p class="text-xs font-bold text-[#00F0FF]">' + coinsTxt + '</p></div>'
          : '';
        var parts = [
          '<div class="rounded-2xl hub-glass border border-white/5 p-5 group hover:border-[#7000FF]/30 transition-all">',
          '<div class="flex items-start justify-between mb-4">',
          '<div class="w-11 h-11 rounded-xl bg-gradient-to-br from-gray-800 to-black border border-white/10 flex items-center justify-center group-hover:border-[#7000FF]/40 transition-colors">',
          '<i data-lucide="' + esc(a.icon || 'medal') + '" class="w-5 h-5 text-gray-300 group-hover:text-[#C99CFF] transition-colors"></i>',
          '</div>',
          '<span class="px-2 py-1 bg-white/5 border border-white/10 rounded text-[9px] font-bold uppercase tracking-widest text-gray-400">' + esc(typeBadge) + '</span>',
          '</div>',
          '<h4 class="text-base font-bold text-white mb-1" style="font-family:Outfit,sans-serif;">' + esc(a.title || '') + '</h4>',
          '<p class="text-xs text-gray-400 leading-relaxed mb-4 min-h-[36px]">' + esc(a.description || '') + '</p>',
          '<div class="p-3 rounded-xl bg-black/40 border border-white/5 flex items-center justify-between">',
          '<div>',
          '<p class="text-[9px] font-bold text-gray-500 uppercase tracking-widest">Reward</p>',
          '<p class="text-sm font-bold text-white mt-0.5">' + rewardTxt + '</p>',
          '</div>',
          bonusHtml,
          '</div>',
          '</div>'
        ];
        return parts.join('');
      }).join('');
    }

    function reinitIcons() {
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        try { window.lucide.createIcons(); } catch (_) { /* noop */ }
      }
    }

    function loadOnce() {
      if (root.dataset.prizeLoaded === '1') return;
      root.dataset.prizeLoaded = '1';

      fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
          var loader = document.getElementById('prize-engine-loading');
          if (loader) loader.classList.add('hidden');
          if (!data) return;
          var hasAnything = (data.fiat_pool || data.coin_pool ||
                             (data.placements || []).length ||
                             (data.special_awards || []).length);
          if (!hasAnything) {
            show('prize-engine-empty');
            return;
          }
          renderPool(data);
          renderPodium(data);
          renderExtendedTiers(data);
          renderAwards(data);
          reinitIcons();
        })
        .catch(function () {
          var loader = document.getElementById('prize-engine-loading');
          if (loader) {
            loader.classList.remove('animate-pulse');
            loader.innerHTML = '<p class="text-xs text-gray-500">Prize information unavailable.</p>';
          }
          root.dataset.prizeLoaded = '';
        });
    }

    loadOnce();

    document.addEventListener('hub:tab-activated', function (e) {
      if (e && e.detail && e.detail.tab === 'prizes') {
        // Re-render if engine got rebuilt by tab navigation.
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
