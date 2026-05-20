/**
 * phase-coin-toss.js — Coin Toss phase module (RP.D)
 *
 * Premium competitive toss ritual:
 *   - Both teams shown with logo + name + side label, separated by VS.
 *   - 3D coin (existing .coin-wrap CSS) with both faces visible — A face
 *     uses the per-game accent (--ac), B face uses the canonical rival
 *     rose tone. Coin lives between the team panels.
 *   - Hero CTA explains purpose ("First pick in map veto").
 *   - On resolve: flip animation runs, winner panel gets reveal-pulse +
 *     emphasised colour, follow-up explainer surfaces the winner's
 *     reward ("picks first ban / map control").
 *   - Non-actor side sees a clear "waiting on opponent" state instead of
 *     a disabled placeholder.
 *
 * No backend changes. Reads ``workflow.coin_toss``, ``match.participant1/2``
 * (including ``logo_url``), and ``workflow.game_branding`` for theming.
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  function _participant(c, side) {
    var match = c.asObject(c.state.room.match);
    var p = c.asObject(match[side === 1 ? 'participant1' : 'participant2']);
    var name = String(p.name || p.team_name || p.username || '').trim();
    return {
      name: name || ('Side ' + side),
      logo: String(p.logo_url || '').trim(),
      checkedIn: c.bool(p.checked_in, false),
    };
  }

  function _initial(name) {
    var s = String(name || '').trim();
    return (s.charAt(0) || '?').toUpperCase();
  }

  // Render a team panel (logo / monogram fallback + name + state badge).
  function _teamPanel(c, side, info, isWinner, isPending) {
    var sideClass = side === 1 ? 'side-a' : 'side-b';
    var stateBadge = '';
    if (isWinner) {
      stateBadge = '<span class="text-[10px] font-black uppercase tracking-widest text-ac mt-1">Won the Toss</span>';
    } else if (isPending) {
      stateBadge = '<span class="text-[10px] font-bold uppercase tracking-widest text-gray-500 mt-1">' +
        (info.checkedIn ? 'Checked In' : 'Pre-Match') + '</span>';
    } else {
      stateBadge = '<span class="text-[10px] font-bold uppercase tracking-widest text-gray-500 mt-1">Lost the Toss</span>';
    }

    var logoOrInitial = info.logo
      ? '<img src="' + c.esc(info.logo) + '" alt="' + c.esc(info.name) + '" class="w-full h-full object-cover" />'
      : '<span class="text-2xl md:text-3xl font-black ' + (side === 1 ? 'text-ac' : 'text-rose-300') + '">' +
        c.esc(_initial(info.name)) + '</span>';

    var ring = isWinner
      ? 'border-ac shadow-[0_0_30px_rgba(var(--ar),var(--ag),var(--ab),0.45)] reveal-pulse'
      : (side === 1 ? 'border-white/15' : 'border-white/15');

    return '<div class="flex-1 flex flex-col items-center gap-2 min-w-0">' +
      '<div class="w-16 h-16 md:w-20 md:h-20 rounded-2xl overflow-hidden flex items-center justify-center bg-black/40 border-2 ' + ring + '">' +
        logoOrInitial +
      '</div>' +
      '<span class="side-indicator ' + sideClass + (isWinner ? ' is-active' : '') + '" style="padding:0.2rem 0.6rem; font-size:0.6rem;">' +
        '<span class="dot"></span>SIDE ' + side +
      '</span>' +
      '<p class="text-sm md:text-base font-black text-white text-center truncate w-full" title="' + c.esc(info.name) + '">' + c.esc(info.name) + '</p>' +
      stateBadge +
    '</div>';
  }

  window.MatchRoom.registerPhase('coin_toss', {
    label: function () { return 'Coin Toss'; },
    narrative: function () { return 'Resolve first map veto control. Winner picks first.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var toss = c.asObject(workflow.coin_toss);
      var winnerSide = c.toInt(toss.winner_side, 0);
      var isResolved = winnerSide === 1 || winnerSide === 2;

      var me = c.asObject(c.state.room.me);
      var staff = c.bool(me.is_staff, false);
      var side = c.mySide();
      // Toss is historically side-1-triggered; staff may also resolve.
      var canAct = (side === 1 || staff) && !c.waitingLocked() && !c.state.requestBusy && !isResolved;

      var p1 = _participant(c, 1);
      var p2 = _participant(c, 2);
      var winnerName = winnerSide === 1 ? p1.name : (winnerSide === 2 ? p2.name : '');

      // Coin shell — two faces use crown + shield icons to look like a real
      // competitive coin. Fixed dimensions + inline color override so the
      // visual works even if theme CSS variables fail to load.
      var crownSvg = '<svg viewBox="0 0 24 24" width="44" height="44" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><path d="M2 20h20M4 20l2-8 4 4 2-8 2 8 4-4 2 8"/></svg>';
      var shieldSvg = '<svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>';
      var coinShellHTML =
        '<div class="coin-wrap" style="width:96px;height:96px;perspective:800px;margin:0 auto;">' +
          '<div class="coin" id="toss-coin" style="width:100%;height:100%;position:relative;transform-style:preserve-3d;">' +
            '<div class="coin-face coin-a" style="color:#00f0ff;">' + crownSvg + '</div>' +
            '<div class="coin-face coin-b" style="color:#ff5577;">' + shieldSvg + '</div>' +
          '</div>' +
        '</div>';

      // Action / status block under the coin.
      var actionHTML;
      if (isResolved) {
        actionHTML =
          '<div class="reveal-pulse mt-1 text-center">' +
            '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">First Veto Pick</p>' +
            '<p class="text-base md:text-lg font-black mt-1">' +
              '<span class="text-ac">' + c.esc(winnerName) + '</span>' +
              ' <span class="text-white">selects the opening ban</span>' +
            '</p>' +
            '<p class="text-[11px] text-gray-400 mt-1.5">' +
              (toss.performed_at ? 'Resolved ' + c.esc(c.shortClock(toss.performed_at)) : 'Resolved.') +
            '</p>' +
          '</div>';
      } else if (canAct) {
        actionHTML =
          '<div class="mt-1 text-center">' +
            '<button type="button" data-action="coin-toss" ' +
              'class="px-8 py-3.5 rounded-xl bg-white text-black text-xs font-black uppercase tracking-widest hover:bg-gray-200 active:scale-95 transition-all">' +
              'Resolve Coin Toss' +
            '</button>' +
            '<p class="text-[10px] text-gray-500 mt-3 tracking-wide">Random fair toss — winner picks first ban in map veto.</p>' +
          '</div>';
      } else {
        var waitingFor = side === 2 ? p1.name : 'tournament staff';
        actionHTML =
          '<div class="mt-1 text-center">' +
            '<div class="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-black/40 border border-white/10">' +
              '<span class="w-2 h-2 rounded-full bg-amber-300 animate-pulse"></span>' +
              '<span class="text-xs font-bold uppercase tracking-widest text-gray-300">Waiting on ' + c.esc(waitingFor) + '</span>' +
            '</div>' +
            '<p class="text-[10px] text-gray-500 mt-3 tracking-wide">Coin toss determines first map veto pick.</p>' +
          '</div>';
      }

      return '' +
        '<section class="glass-panel rounded-2xl p-5 md:p-8 border-t-4 border-ac">' +
          '<div class="text-center mb-5">' +
            '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Match Ritual</p>' +
            '<h3 class="text-xl md:text-2xl font-black text-white mt-1">Coin Toss</h3>' +
          '</div>' +
          '<div class="flex items-center gap-3 md:gap-5">' +
            _teamPanel(c, 1, p1, winnerSide === 1, !isResolved) +
            '<div class="flex flex-col items-center gap-2 shrink-0">' +
              coinShellHTML +
              '<span class="text-[10px] font-black tracking-widest text-gray-600">VS</span>' +
            '</div>' +
            _teamPanel(c, 2, p2, winnerSide === 2, !isResolved) +
          '</div>' +
          actionHTML +
        '</section>';
    },

    onAction: async function (action, trigger, c) {
      if (action !== 'coin-toss') return false;
      // Disable CTA and start flip animation before the network round-trip.
      var btn = document.querySelector('[data-action="coin-toss"]');
      if (btn) { btn.disabled = true; btn.textContent = 'Flipping…'; }
      try {
        var coin = document.getElementById('toss-coin');
        if (coin) {
          coin.classList.remove('flip');
          void coin.offsetWidth;
          coin.classList.add('flip');
        }
      } catch (_) { /* animation is best-effort */ }
      await c.sendWorkflowAction('coin_toss', {});
      return true;
    }
  });
})();
