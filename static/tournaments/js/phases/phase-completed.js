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

  function _teamCard(c, info, isWinner) {
    var logoOrInitial = info.logo
      ? '<img src="' + c.esc(info.logo) + '" alt="' + c.esc(info.name) + '" class="w-full h-full object-cover" />'
      : '<span class="text-3xl md:text-4xl font-black ' + (isWinner ? 'text-ac' : 'text-gray-500') + '">' + c.esc(_initial(info.name)) + '</span>';

    var frameCls = isWinner
      ? 'border-ac/70 shadow-[0_0_36px_rgba(var(--ar),var(--ag),var(--ab),0.35)] reveal-pulse'
      : 'border-white/10 opacity-70';
    var nameCls = isWinner ? 'text-white' : 'text-gray-400';
    var statusText = isWinner ? 'Winner' : 'Defeated';
    var statusCls = isWinner
      ? 'text-ac font-black'
      : 'text-gray-500 font-bold';

    return '<div class="flex-1 min-w-0 flex flex-col items-center gap-2.5">' +
      '<div class="w-20 h-20 md:w-24 md:h-24 rounded-2xl overflow-hidden flex items-center justify-center bg-black/40 border-2 ' + frameCls + '">' +
        logoOrInitial +
      '</div>' +
      '<p class="text-base md:text-lg font-black ' + nameCls + ' text-center truncate w-full" title="' + c.esc(info.name) + '">' + c.esc(info.name) + '</p>' +
      '<span class="text-[10px] uppercase tracking-widest ' + statusCls + '">' + statusText + '</span>' +
    '</div>';
  }

  function _seriesGames(c, series) {
    var games = c.asList(series.games);
    if (!games.length) return '';
    var pills = games.map(function (g, i) {
      var ws = c.toInt(g.winner_slot, 0);
      var cls = ws === 1 ? 'won-side-1' : (ws === 2 ? 'won-side-2' : 'upcoming');
      var map = c.esc(String(g.map || ('Game ' + (i + 1))));
      var score = c.toInt(g.p1, 0) + '–' + c.toInt(g.p2, 0);
      return '<div class="series-game-pill ' + cls + '">' +
        '<span class="game-num">GAME ' + (i + 1) + '</span>' +
        '<span class="map-name">' + map + '</span>' +
        '<span class="game-score">' + c.esc(score) + '</span>' +
      '</div>';
    }).join('');
    return '<div class="mt-5">' +
      '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-2">Per-Game Record</p>' +
      '<div class="flex gap-2">' + pills + '</div>' +
    '</div>';
  }

  window.MatchRoom.registerPhase('completed', {
    label: function () { return 'Match Complete'; },
    narrative: function () { return 'Result archived. View bracket for the next match.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var finalResult = c.asObject(workflow.final_result);
      var series = c.asObject(workflow.series);
      var match = c.asObject(c.state.room.match);
      var urls = c.asObject(c.state.room.urls);

      var p1 = _participant(c, match.participant1);
      var p2 = _participant(c, match.participant2);

      var p1Score = c.toInt(finalResult.participant1_score, c.toInt(c.asObject(match.participant1).score, 0));
      var p2Score = c.toInt(finalResult.participant2_score, c.toInt(c.asObject(match.participant2).score, 0));
      var bestOf = c.toInt(match.best_of, 1);

      var winnerSide = c.toInt(finalResult.winner_side, 0)
        || (c.toInt(match.winner_id, 0) === p1.id ? 1
            : (c.toInt(match.winner_id, 0) === p2.id ? 2 : 0));
      var isDraw = winnerSide === 0;

      // Status badge — winner / draw / pending depending on data.
      var statusBadge;
      if (isDraw) {
        statusBadge = '<div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-amber-400/30 bg-amber-500/12 text-amber-200 text-[10px] font-black uppercase tracking-widest">' +
          '<i data-lucide="minus-circle" class="w-3.5 h-3.5"></i>Drawn Result' +
        '</div>';
      } else {
        statusBadge = '<div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-ac/40 bg-ac/12 text-ac text-[10px] font-black uppercase tracking-widest">' +
          '<i data-lucide="trophy" class="w-3.5 h-3.5"></i>Result Verified' +
        '</div>';
      }

      var bracketHref = String(urls.bracket || urls.match_detail || '#');
      var hubHref = String(urls.hub || urls.match_detail || '#');

      // Header copy adapts to result type.
      var headerTitle = isDraw ? 'Match Drawn'
                              : (winnerSide === 1 ? c.esc(p1.name) + ' Wins' : c.esc(p2.name) + ' Wins');
      var headerSub  = bestOf > 1
        ? 'Best of ' + bestOf + ' — final score ' + p1Score + '–' + p2Score
        : 'Match report archived';

      return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
        '<div class="flex flex-col gap-2 mb-5">' +
          statusBadge +
          '<h3 class="text-2xl md:text-3xl font-black text-white reveal-pulse" style="line-height:1.15;">' + headerTitle + '</h3>' +
          '<p class="text-xs md:text-sm text-gray-400">' + c.esc(headerSub) + '</p>' +
        '</div>' +
        '<div class="flex items-center gap-3 md:gap-5">' +
          _teamCard(c, p1, winnerSide === 1) +
          '<div class="flex flex-col items-center gap-1 shrink-0">' +
            '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Final</p>' +
            '<p class="font-mono font-black text-3xl md:text-5xl text-white tabular-nums">' +
              '<span class="' + (winnerSide === 1 ? 'text-ac' : '') + '">' + p1Score + '</span>' +
              '<span class="text-gray-600 mx-1.5">–</span>' +
              '<span class="' + (winnerSide === 2 ? 'text-ac' : '') + '">' + p2Score + '</span>' +
            '</p>' +
            (bestOf > 1
              ? '<p class="text-[10px] font-bold uppercase tracking-widest text-gray-500 mt-0.5">' + (c.toInt(series.wins_needed, 0) || (Math.floor(bestOf/2)+1)) + ' to win</p>'
              : '<p class="text-[10px] font-bold uppercase tracking-widest text-gray-500 mt-0.5">Best of 1</p>') +
          '</div>' +
          _teamCard(c, p2, winnerSide === 2) +
        '</div>' +
        _seriesGames(c, series) +
        '<div class="mt-6 flex flex-wrap items-center gap-2">' +
          '<a href="' + c.esc(bracketHref) + '" class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider hover:opacity-90 transition-opacity active:scale-95">' +
            '<i data-lucide="git-branch" class="w-4 h-4"></i>View Bracket' +
          '</a>' +
          '<a href="' + c.esc(hubHref) + '" class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg border border-white/25 text-xs font-bold uppercase tracking-wider text-white hover:bg-white/10 transition-colors active:scale-95">' +
            '<i data-lucide="house" class="w-4 h-4"></i>Back to Hub' +
          '</a>' +
        '</div>' +
      '</section>';
    },

    onAction: async function () { return false; }
  });
})();
