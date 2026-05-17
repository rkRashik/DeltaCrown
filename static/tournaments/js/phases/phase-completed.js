/**
 * phase-completed.js — Completed phase module (RP-D)
 *
 * Premium result reveal:
 *   - Winner team panel (large, accent glow, animated entry).
 *   - Loser team panel (subdued).
 *   - Big score readout with monospaced tabular numerals.
 *   - BO3/BO5 awareness: shows series wins + per-game record.
 *   - Match report status badge.
 *   - Next-action CTAs: View Bracket / Back to Hub.
 *
 * Reads ``workflow.final_result``, ``workflow.series`` (P2.C),
 * ``match.participant1/2`` (with ``logo_url``), ``urls.bracket`` / ``urls.hub``.
 * Falls back to participant scores when final_result is absent.
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  function _participant(c, sideObj) {
    var p = c.asObject(sideObj);
    var name = String(p.name || p.team_name || p.username || '').trim();
    return {
      id: c.toInt(p.id, 0),
      name: name || 'Participant',
      logo: String(p.logo_url || '').trim(),
    };
  }

  function _initial(name) {
    return (String(name || '').trim().charAt(0) || '?').toUpperCase();
  }

  function _teamBlock(c, info, isWinner, isDraw) {
    var logoOrInitial = info.logo
      ? '<img src="' + c.esc(info.logo) + '" alt="' + c.esc(info.name) + '" class="w-full h-full object-cover" />'
      : '<span class="text-4xl font-black ' + (isWinner && !isDraw ? 'text-ac' : 'text-gray-600') + '">' + c.esc(_initial(info.name)) + '</span>';

    var frameCls = (isWinner && !isDraw)
      ? 'border-ac/60 shadow-[0_0_40px_rgba(var(--ar),var(--ag),var(--ab),0.3)]'
      : 'border-white/8 opacity-55';

    return '<div class="flex flex-col items-center gap-3 min-w-0 flex-1">' +
      '<div class="relative">' +
        '<div class="w-20 h-20 md:w-24 md:h-24 rounded-2xl overflow-hidden flex items-center justify-center bg-black/50 border-2 transition-all ' + frameCls + '">' +
          logoOrInitial +
        '</div>' +
        (isWinner && !isDraw
          ? '<div class="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-ac flex items-center justify-center border-2 border-black"><i data-lucide="crown" class="w-3.5 h-3.5 text-black pointer-events-none"></i></div>'
          : '') +
      '</div>' +
      '<div class="text-center min-w-0 w-full">' +
        '<p class="text-sm md:text-base font-black ' + (isWinner && !isDraw ? 'text-white' : 'text-gray-500') + ' truncate">' + c.esc(info.name) + '</p>' +
        (isDraw
          ? '<span class="text-[9px] uppercase tracking-widest font-bold text-amber-400/80">Draw</span>'
          : isWinner
          ? '<span class="text-[9px] uppercase tracking-widest font-black text-ac">Victory</span>'
          : '<span class="text-[9px] uppercase tracking-widest font-bold text-gray-600">Defeated</span>') +
      '</div>' +
    '</div>';
  }

  function _seriesGames(c, series, p1Name, p2Name) {
    var games = c.asList(series.games);
    if (!games.length) return '';
    var rows = games.map(function (g, i) {
      var ws = c.toInt(g.winner_slot, 0);
      var p1Win = ws === 1, p2Win = ws === 2;
      var mapName = String(g.map || ('Game ' + (i + 1)));
      var s1 = c.toInt(g.p1, 0), s2 = c.toInt(g.p2, 0);
      return '<div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-black/30 border border-white/[0.05]">' +
        '<span class="text-[9px] font-black text-gray-600 uppercase tracking-widest w-10 shrink-0">G' + (i+1) + '</span>' +
        '<span class="text-xs text-gray-400 flex-1 truncate">' + c.esc(mapName) + '</span>' +
        '<span class="text-xs font-black tabular-nums ' + (p1Win ? 'text-ac' : 'text-gray-500') + '">' + s1 + '</span>' +
        '<span class="text-[10px] text-gray-700 mx-1">–</span>' +
        '<span class="text-xs font-black tabular-nums ' + (p2Win ? 'text-ac' : 'text-gray-500') + '">' + s2 + '</span>' +
      '</div>';
    }).join('');
    return '<div class="mt-5 pt-4 border-t border-white/[0.06]">' +
      '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-2">Series Breakdown</p>' +
      '<div class="flex flex-col gap-1.5">' + rows + '</div>' +
    '</div>';
  }

  window.MatchRoom.registerPhase('completed', {
    label: function () { return 'Match Complete'; },
    narrative: function () { return 'Result archived. View bracket for your next match.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var finalResult = c.asObject(workflow.final_result);
      var series = c.asObject(workflow.series);
      var match = c.asObject(c.state.room.match);
      var urls = c.asObject(c.state.room.urls);
      var me = c.asObject(c.state.room.me);

      var p1 = _participant(c, match.participant1);
      var p2 = _participant(c, match.participant2);

      var p1Score = c.toInt(finalResult.participant1_score, c.toInt(c.asObject(match.participant1).score, 0));
      var p2Score = c.toInt(finalResult.participant2_score, c.toInt(c.asObject(match.participant2).score, 0));
      var bestOf = c.toInt(match.best_of, 1);

      var winnerSide = c.toInt(finalResult.winner_side, 0)
        || (c.toInt(match.winner_id, 0) === p1.id ? 1
            : (c.toInt(match.winner_id, 0) === p2.id ? 2 : 0));
      var isDraw = winnerSide === 0;
      var winnerName = winnerSide === 1 ? p1.name : (winnerSide === 2 ? p2.name : '');
      var mySide = c.mySide();
      var iAmWinner = !isDraw && mySide === winnerSide;
      var iAmLoser  = !isDraw && mySide > 0 && mySide !== winnerSide;

      // ── Personal outcome ribbon (only for match participants) ─────────
      var outcomeRibbon = '';
      if (mySide > 0) {
        if (iAmWinner) {
          outcomeRibbon = '<div class="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-ac/10 border border-ac/30 mb-5 reveal-pulse">' +
            '<i data-lucide="trophy" class="w-4 h-4 text-ac shrink-0"></i>' +
            '<p class="text-sm font-black text-ac">You won this match!</p>' +
          '</div>';
        } else if (iAmLoser) {
          outcomeRibbon = '<div class="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/8 mb-5">' +
            '<i data-lucide="shield" class="w-4 h-4 text-gray-500 shrink-0"></i>' +
            '<p class="text-sm font-bold text-gray-400">Match complete — ' + c.esc(winnerName) + ' advances.</p>' +
          '</div>';
        } else if (isDraw) {
          outcomeRibbon = '<div class="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-amber-500/8 border border-amber-400/20 mb-5">' +
            '<i data-lucide="minus-circle" class="w-4 h-4 text-amber-400 shrink-0"></i>' +
            '<p class="text-sm font-bold text-amber-300/90">Draw — check with the organizer for advancement.</p>' +
          '</div>';
        }
      }

      // ── Score architecture ────────────────────────────────────────────
      var winnerLabel = isDraw ? 'Draw'
        : (winnerSide === 1 ? p1.name + ' wins' : p2.name + ' wins');

      var boLabel = bestOf > 1 ? ' · BO' + bestOf : '';

      var scoreHtml =
        '<div class="flex flex-col items-center gap-1 shrink-0 px-3">' +
          '<p class="text-[9px] font-black uppercase tracking-widest text-gray-600 mb-1">Final Score' + c.esc(boLabel) + '</p>' +
          '<div class="flex items-baseline gap-2 font-display">' +
            '<span class="text-4xl md:text-6xl font-black tabular-nums ' + (winnerSide === 1 ? 'text-ac' : 'text-gray-500') + '" style="line-height:1">' + p1Score + '</span>' +
            '<span class="text-xl md:text-3xl text-gray-700 font-black">–</span>' +
            '<span class="text-4xl md:text-6xl font-black tabular-nums ' + (winnerSide === 2 ? 'text-ac' : 'text-gray-500') + '" style="line-height:1">' + p2Score + '</span>' +
          '</div>' +
          '<p class="text-[10px] font-black uppercase tracking-wider text-gray-500 mt-1">' + c.esc(winnerLabel) + '</p>' +
        '</div>';

      // ── CTAs ─────────────────────────────────────────────────────────
      var bracketHref = String(urls.bracket || urls.match_detail || '#');
      var hubHref = String(urls.hub || urls.match_detail || '#');
      var reportHref = String(urls.match_detail || bracketHref);

      var ctaHtml =
        '<div class="mt-6 flex flex-wrap items-center gap-2.5">' +
          '<a href="' + c.esc(bracketHref) + '" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-ac text-black text-xs font-black uppercase tracking-wider shadow-[0_0_16px_rgba(var(--ar),var(--ag),var(--ab),0.25)] hover:brightness-110 transition-all active:scale-95">' +
            '<i data-lucide="git-branch" class="w-3.5 h-3.5"></i>View Bracket' +
          '</a>' +
          '<a href="' + c.esc(hubHref) + '" class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-white/15 text-xs font-bold uppercase tracking-wider text-white/80 hover:bg-white/5 hover:border-white/25 transition-all active:scale-95">' +
            '<i data-lucide="house" class="w-3.5 h-3.5"></i>Tournament Hub' +
          '</a>' +
          (reportHref !== bracketHref
            ? '<a href="' + c.esc(reportHref) + '" class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-white/10 text-xs font-bold uppercase tracking-wider text-gray-400 hover:text-white hover:border-white/20 transition-all active:scale-95">' +
              '<i data-lucide="file-text" class="w-3.5 h-3.5"></i>Match Report</a>'
            : '') +
        '</div>';

      return '<section class="glass-panel rounded-2xl overflow-hidden border border-white/[0.07]" style="border-top:4px solid var(--ac);">' +
        // Hero strip with winner glow background
        '<div class="relative p-5 md:p-7 pb-6 overflow-hidden">' +
          (winnerSide > 0 && !isDraw
            ? '<div class="absolute ' + (winnerSide === 1 ? 'left-0' : 'right-0') + ' inset-y-0 w-1/2 pointer-events-none" style="background:linear-gradient(' + (winnerSide === 1 ? '90deg' : '270deg') + ',rgba(var(--ar),var(--ag),var(--ab),0.06) 0%,transparent 100%);"></div>'
            : '') +
          '<div class="relative z-10">' +
            outcomeRibbon +
            '<div class="flex items-center justify-between mb-5">' +
              '<div>' +
                '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Match Complete</p>' +
                '<h3 class="text-xl md:text-2xl font-black text-white mt-0.5">' +
                  (isDraw ? 'Match Drawn' : c.esc(winnerName) + ' Advances') +
                '</h3>' +
              '</div>' +
              '<div class="shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-full bg-ac/10 border border-ac/25">' +
                '<i data-lucide="shield-check" class="w-3.5 h-3.5 text-ac"></i>' +
                '<span class="text-[10px] font-black uppercase tracking-widest text-ac">Verified</span>' +
              '</div>' +
            '</div>' +
            '<div class="flex items-center gap-4 md:gap-6">' +
              _teamBlock(c, p1, winnerSide === 1, isDraw) +
              scoreHtml +
              _teamBlock(c, p2, winnerSide === 2, isDraw) +
            '</div>' +
          '</div>' +
        '</div>' +
        // Series + CTAs
        '<div class="px-5 md:px-7 pb-6">' +
          _seriesGames(c, series, p1.name, p2.name) +
          ctaHtml +
        '</div>' +
      '</section>';
    },

    onAction: async function () { return false; }
  });
})();
