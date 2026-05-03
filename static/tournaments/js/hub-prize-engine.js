/**
 * Hub Prize Engine - results/rewards renderer.
 *
 * CSP-safe static file. Uses the participant rewards endpoint when present
 * and falls back to the public prize overview for read-only contexts.
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

  function setHidden(id, hidden) {
    var el = document.getElementById(id);
    if (el) el.classList.toggle('hidden', !!hidden);
  }

  function show(id) {
    setHidden(id, false);
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
    return ''; // No winner published yet — show nothing
  }

  function achievementRows(data) {
    return data.derived_achievements || data.achievements || data.special_awards || [];
  }

  function reinitIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      try { window.lucide.createIcons(); } catch (_) { /* noop */ }
    }
  }

  function renderPool(data) {
    show('prize-engine-pool');
    var fiatEl = document.getElementById('prize-engine-fiat');
    var currencyEl = document.getElementById('prize-engine-currency');
    var coinsEl = document.getElementById('prize-engine-coins');
    var statusEl = document.getElementById('prize-tournament-status');
    if (fiatEl) fiatEl.textContent = data.fiat_pool ? fmt(data.fiat_pool) : 'TBA';
    if (currencyEl) currencyEl.textContent = data.currency || 'BDT';
    if (coinsEl) coinsEl.textContent = fmt(data.coin_pool || 0);
    if (data.result_status && data.result_status.placements_published) {
      show('prize-engine-finalized');
    }
    if (data.certificates_enabled) show('prize-engine-certs');
    if (statusEl) {
      statusEl.textContent = data.result_status && data.result_status.completed
        ? 'Completed'
        : (data.tournament_status || 'Pending');
    }
  }

  var podiumStyles = [
    {
      iconBg: 'bg-gradient-to-br from-yellow-300 to-[#FFB800]',
      iconColor: 'text-black',
      icon: 'crown',
      ringClass: 'border-[#FFB800]/40 shadow-[0_10px_60px_rgba(255,184,0,0.2)]',
      labelColor: 'text-[#FFB800]',
      elevation: 'md:-translate-y-4'
    },
    {
      iconBg: 'bg-gradient-to-br from-gray-200 to-gray-400',
      iconColor: 'text-black',
      icon: 'medal',
      ringClass: 'border-white/10',
      labelColor: 'text-gray-300',
      elevation: ''
    },
    {
      iconBg: 'bg-gradient-to-br from-[#CD7F32] to-[#8B5A2B]',
      iconColor: 'text-white',
      icon: 'award',
      ringClass: 'border-[#CD7F32]/30',
      labelColor: 'text-[#CD7F32]',
      elevation: ''
    }
  ];

  function podiumCard(tier, idx, data) {
    var style = podiumStyles[idx] || podiumStyles[2];
    var winner = winnerLabel(tier, data);
    var winnerTone = tier.winner && tier.winner.team_name ? 'text-white' : 'text-gray-500';
    var coinsLabel = tier.coins ? '+ ' + fmt(tier.coins) + ' DC' : '';
    var cert = tier.certificate_badge || {};
    var winnerHtml = winner
      ? '<p class="text-sm font-bold ' + winnerTone + ' truncate mt-1">' + winner + '</p>'
      : '';
    var coinsHtml = coinsLabel
      ? '<div class="inline-flex items-center gap-1.5 px-3 py-1 mt-3 rounded-lg bg-[#00F0FF]/10 border border-[#00F0FF]/20 text-xs font-bold text-[#00F0FF]"><i data-lucide="coins" class="w-3 h-3"></i><span>' + coinsLabel + '</span></div>'
      : '';
    var certHtml = cert.enabled
      ? '<p class="text-[10px] font-mono text-emerald-300 mt-3 uppercase tracking-widest">Certificate ' + esc(cert.status || 'pending') + '</p>'
      : '';
    return [
      '<div class="relative overflow-hidden rounded-3xl hub-glass border ' + style.ringClass + ' p-6 md:p-8 ' + style.elevation + ' transition-all">',
      '<div class="absolute top-2 right-3 font-black opacity-10 text-7xl text-white pointer-events-none" style="font-family:Outfit,sans-serif;">' + (idx + 1) + '</div>',
      '<div class="relative z-10 space-y-4">',
      '<div class="w-14 h-14 rounded-2xl ' + style.iconBg + ' flex items-center justify-center shadow-lg">',
      '<i data-lucide="' + style.icon + '" class="w-7 h-7 ' + style.iconColor + '"></i>',
      '</div>',
      '<div>',
      '<p class="text-[10px] font-bold uppercase tracking-[0.2em] ' + style.labelColor + ' mb-1">' + ordinal(tier.rank) + ' - ' + esc(tier.title || '') + '</p>',
      winnerHtml,
      '</div>',
      '<div>',
      '<h4 class="text-3xl md:text-4xl font-black text-white tracking-tight" style="font-family:Outfit,sans-serif;">' + money(data, tier.fiat) + '</h4>',
      coinsHtml,
      certHtml,
      '</div>',
      '</div>',
      '</div>'
    ].join('');
  }

  function renderPodium(data) {
    // Only show the championship podium when tournament is completed and results are available.
    // For in-progress tournaments, the prize structure is shown via renderExtendedTiers instead.
    if (!isCompleted(data)) return;
    var top3 = (data.placements || []).slice(0, 3);
    if (!top3.length) return;
    var podium = document.getElementById('prize-engine-podium');
    if (!podium) return;
    show('prize-engine-podium-wrap');
    var visualOrder = top3.length === 3 ? [1, 0, 2] : top3.map(function (_, i) { return i; });
    podium.innerHTML = visualOrder.map(function (i) {
      return top3[i] ? podiumCard(top3[i], i, data) : '';
    }).join('');
  }

  function renderExtendedTiers(data) {
    var rest = (data.placements || []).slice(3);
    if (!rest.length) return;
    var list = document.getElementById('prize-engine-tiers');
    if (!list) return;
    show('prize-engine-tiers-wrap');
    list.innerHTML = rest.map(function (tier) {
      var winner = winnerLabel(tier, data);
      var coinsTxt = tier.coins ? fmt(tier.coins) + ' DC' : '';
      return [
        '<div class="flex items-center justify-between gap-4 p-5 hover:bg-white/[0.02] transition-colors">',
        '<div class="flex items-center gap-5 min-w-0">',
        '<div class="w-10 h-10 rounded-full bg-black/40 border border-white/5 flex items-center justify-center font-mono font-bold text-gray-400 text-sm shrink-0">' + ordinal(tier.rank) + '</div>',
        '<div class="min-w-0">',
        '<p class="text-sm font-bold text-white truncate">' + esc(tier.title || '') + '</p>',
        winner ? '<p class="text-xs text-[#FFB800] mt-0.5 truncate">' + winner + '</p>' : '',
        '</div>',
        '</div>',
        '<div class="text-right shrink-0">',
        '<p class="text-xl font-black text-white" style="font-family:Outfit,sans-serif;">' + money(data, tier.fiat) + '</p>',
        coinsTxt ? '<p class="text-[10px] font-mono text-[#00F0FF] mt-0.5">' + coinsTxt + '</p>' : '',
        '</div>',
        '</div>'
      ].join('');
    }).join('');
  }

  function renderAwards(data) {
    var awards = data.special_awards || [];
    var grid = document.getElementById('prize-engine-awards');
    if (!awards.length || !grid) return;
    show('prize-engine-awards-wrap');
    grid.innerHTML = awards.map(function (a) {
      var fiatTxt = a.fiat ? money(data, a.fiat) : '';
      var coinsTxt = a.coins ? fmt(a.coins) + ' DC' : '';
      var rewardTxt = a.reward_text ? esc(a.reward_text) : (fiatTxt || coinsTxt || 'Award');
      var recipient = a.recipient_name
        ? '<p class="text-[10px] text-[#FFB800] mt-3 uppercase tracking-widest">Recipient: ' + esc(a.recipient_name) + '</p>'
        : '<p class="text-[10px] text-gray-500 mt-3 uppercase tracking-widest">Awaiting assignment</p>';
      return [
        '<div class="rounded-2xl hub-glass border border-white/5 p-5 group hover:border-[#7000FF]/30 transition-all">',
        '<div class="flex items-start justify-between mb-4">',
        '<div class="w-11 h-11 rounded-xl bg-gradient-to-br from-gray-800 to-black border border-white/10 flex items-center justify-center group-hover:border-[#7000FF]/40 transition-colors">',
        '<i data-lucide="' + esc(a.icon || 'medal') + '" class="w-5 h-5 text-gray-300 group-hover:text-[#C99CFF] transition-colors"></i>',
        '</div>',
        '<span class="px-2 py-1 bg-white/5 border border-white/10 rounded text-[9px] font-bold uppercase tracking-widest text-gray-400">' + esc((a.type || 'cash').toUpperCase()) + '</span>',
        '</div>',
        '<h4 class="text-base font-bold text-white mb-1" style="font-family:Outfit,sans-serif;">' + esc(a.title || '') + '</h4>',
        '<p class="text-xs text-gray-400 leading-relaxed mb-4 min-h-[36px]">' + esc(a.description || '') + '</p>',
        '<div class="p-3 rounded-xl bg-black/40 border border-white/5 flex items-center justify-between gap-3">',
        '<div>',
        '<p class="text-[9px] font-bold text-gray-500 uppercase tracking-widest">Reward</p>',
        '<p class="text-sm font-bold text-white mt-0.5">' + rewardTxt + '</p>',
        '</div>',
        coinsTxt ? '<div class="text-right"><p class="text-[9px] font-bold text-[#00F0FF] uppercase tracking-widest">Bonus</p><p class="text-xs font-bold text-[#00F0FF]">' + coinsTxt + '</p></div>' : '',
        '</div>',
        recipient,
        '</div>'
      ].join('');
    }).join('');
  }

  function renderAchievements(data) {
    var rows = achievementRows(data);
    var grid = document.getElementById('prize-engine-achievements');
    if (!rows.length || !grid) return;
    show('prize-engine-achievements-wrap');
    grid.innerHTML = rows.map(function (a) {
      var recipient = a.recipient_name
        ? '<p class="text-[10px] text-[#FFB800] mt-2 uppercase tracking-widest">' + esc(a.recipient_name) + '</p>'
        : (a.awaiting_recipient ? '<p class="text-[10px] text-gray-500 mt-2 uppercase tracking-widest">Awaiting assignment</p>' : '');
      return [
        '<div class="rounded-2xl hub-glass border border-white/5 p-5">',
        '<div class="flex items-start gap-3">',
        '<div class="w-11 h-11 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">',
        '<i data-lucide="' + esc(a.icon || 'award') + '" class="w-5 h-5 text-[#FFB800]"></i>',
        '</div>',
        '<div class="min-w-0 flex-1">',
        '<h4 class="text-base font-bold text-white" style="font-family:Outfit,sans-serif;">' + esc(a.title || 'Achievement') + '</h4>',
        '<p class="text-xs text-gray-400 mt-1">' + esc(a.description || '') + '</p>',
        a.reward_text ? '<p class="text-xs font-mono text-[#00F0FF] mt-2">' + esc(a.reward_text) + '</p>' : '',
        recipient,
        '</div>',
        '</div>',
        '</div>'
      ].join('');
    }).join('');
  }

  function badge(label, tone) {
    var classes = {
      gold: 'bg-[#FFB800]/10 border-[#FFB800]/25 text-[#FFB800]',
      cyan: 'bg-[#00F0FF]/10 border-[#00F0FF]/25 text-[#00F0FF]',
      green: 'bg-emerald-500/10 border-emerald-500/25 text-emerald-300',
      red: 'bg-[#FF2A55]/10 border-[#FF2A55]/25 text-[#FF2A55]',
      gray: 'bg-white/5 border-white/10 text-gray-300'
    };
    return '<span class="inline-flex items-center px-3 py-1 rounded-full border text-[10px] font-mono uppercase tracking-widest ' + (classes[tone] || classes.gray) + '">' + esc(label) + '</span>';
  }

  function renderYourResult(data) {
    var section = document.getElementById('your-result-section');
    if (!section) return;
    var result = data.your_result;
    var title = document.getElementById('your-result-title');
    var detail = document.getElementById('your-result-detail');
    var status = document.getElementById('your-result-status');
    if (result) {
      if (title) title.textContent = (result.rank_label || ordinal(result.rank)) + ' - ' + (result.title || 'Placement');
      if (detail) {
        var prize = result.prize || {};
        detail.textContent = 'Prize: ' + money(data, prize.fiat) + ' / ' + fmt(prize.coins || 0) + ' DC';
      }
      if (status) {
        var parts = [];
        (result.achievement_badges || []).forEach(function (a) {
          parts.push(badge(a.title || 'Achievement', a.source === 'placement' ? 'gold' : 'cyan'));
        });
        if (result.claim && result.claim.status) {
          parts.push(badge('Claim ' + result.claim.status, result.claim.status === 'rejected' ? 'red' : 'gold'));
        } else if (result.claimable) {
          parts.push(badge('Claim available', 'gold'));
        } else if (result.has_prize) {
          parts.push(badge('Claim pending', 'gray'));
        }
        if (result.payout && result.payout.status) parts.push(badge('Payout ' + result.payout.status, 'cyan'));
        if (result.certificate) parts.push(badge('Certificate available', 'green'));
        else if (data.certificates_enabled) parts.push(badge('Certificate pending', 'gray'));
        status.innerHTML = parts.join('');
      }
      section.classList.remove('hidden');
      return;
    }
    if (data.result_status && data.result_status.completed && data.viewer) {
      if (title) title.textContent = 'No prize earned';
      if (detail) detail.textContent = 'Tournament completed. Your placement did not receive a configured prize.';
      if (status) status.innerHTML = badge('Completed', 'gray');
      section.classList.remove('hidden');
    }
  }

  function renderYourPrizes(data) {
    var prizes = data.your_prizes || [];
    var section = document.getElementById('your-prizes-section');
    var list = document.getElementById('your-prizes-list');
    if (!section || !list || !prizes.length) return;
    list.innerHTML = prizes.map(function (p) {
      var claim = p.claim || {};
      var payout = p.payout || {};
      var canClaim = p.id && !p.claimed && !data.claim_actions_locked &&
        (p.status === 'pending' || p.status === 'completed');
      var amount = fmt(parseFloat(p.amount || 0));
      var btn = canClaim
        ? '<button class="prize-claim-btn" data-click="HubEngine.openPrizeModal" data-click-args="[&quot;' + esc(p.id) + '&quot;,&quot;' + esc(amount) + '&quot;,&quot;' + esc(p.placement_display || p.placement || '') + '&quot;]">Claim Prize</button>'
        : '';
      var cert = p.certificate && p.certificate.download_url
        ? '<a href="' + esc(p.certificate.download_url) + '" class="px-3 py-1.5 rounded-lg border border-emerald-500/25 text-emerald-300 text-[10px] font-bold uppercase tracking-widest">Certificate</a>'
        : '';
      return [
        '<div class="prize-your-card">',
        '<div>',
        '<p class="text-sm font-bold text-white">' + esc(p.placement_display || p.placement || 'Prize') + '</p>',
        '<p class="text-xs text-gray-400 mt-0.5">Amount: <span class="text-[#FFB800] font-bold">' + amount + '</span></p>',
        '</div>',
        '<div class="flex items-center gap-3 flex-wrap justify-end">',
        claim.status ? badge('Claim ' + claim.status, claim.status === 'rejected' ? 'red' : 'gold') : '',
        payout.status ? badge('Payout ' + payout.status, 'cyan') : '',
        cert,
        btn,
        '</div>',
        '</div>'
      ].join('');
    }).join('');
    section.classList.remove('hidden');
  }

  function renderEmptyStates(data) {
    if (data.empty_states && data.empty_states.no_prize_configured) {
      show('prize-engine-empty');
      return;
    }
    if (data.empty_states && data.empty_states.no_placements && data.result_status) {
      var empty = document.getElementById('prize-engine-empty');
      if (empty) {
        empty.classList.remove('hidden');
        var lines = empty.getElementsByTagName('p');
        if (lines.length > 0) lines[0].textContent = data.result_status.message || 'Placements are not published yet';
      }
    }
  }

  function render(data) {
    var loader = document.getElementById('prize-engine-loading');
    if (loader) loader.classList.add('hidden');
    if (!data) return;
    var hasAnything = data.fiat_pool || data.coin_pool ||
      (data.placements || []).length ||
      (data.special_awards || []).length ||
      (data.standings || []).length;
    if (!hasAnything) {
      show('prize-engine-empty');
      return;
    }
    renderPool(data);
    renderPodium(data);
    renderExtendedTiers(data);
    renderAchievements(data);
    renderAwards(data);
    renderYourResult(data);
    renderYourPrizes(data);
    renderEmptyStates(data);
    reinitIcons();
  }

  function init() {
    var root = document.getElementById('hub-prize-engine');
    if (!root) return;
    var url = root.getAttribute('data-hub-rewards-url') ||
      root.getAttribute('data-prize-overview-url');
    if (!url) return;

    function loadOnce() {
      if (root.dataset.prizeLoaded === '1') return;
      root.dataset.prizeLoaded = '1';
      fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(render)
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
