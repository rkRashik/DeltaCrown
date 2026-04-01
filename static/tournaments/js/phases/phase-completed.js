/**
 * phase-completed.js — Completed phase module
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  window.MatchRoom.registerPhase('completed', {
    label: function () { return 'Completed'; },
    narrative: function () { return 'Result finalized. Jump to hub or bracket for the next assignment.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var finalResult = c.asObject(workflow.final_result);
      var match = c.asObject(c.state.room.match);
      var urls = c.asObject(c.state.room.urls);
      var p1 = c.asObject(match.participant1);
      var p2 = c.asObject(match.participant2);

      var p1Score = c.toInt(finalResult.participant1_score, c.toInt(p1.score, 0));
      var p2Score = c.toInt(finalResult.participant2_score, c.toInt(p2.score, 0));
      var winnerSide = c.toInt(finalResult.winner_side, 0)
        || (c.toInt(match.winner_id, 0) === c.toInt(p1.id, -1) ? 1 : (c.toInt(match.winner_id, 0) === c.toInt(p2.id, -1) ? 2 : 0));

      var winnerText = winnerSide === 1
        ? (p1.name || 'Side 1') + ' wins'
        : (winnerSide === 2 ? (p2.name || 'Side 2') + ' wins' : 'Match ended in a draw');

      var bracketHref = String(urls.bracket || urls.match_detail || '#');
      var hubHref = String(urls.hub || urls.match_detail || '#');

      return '<section class="rounded-2xl p-5 md:p-7 border border-white/10 bg-gradient-to-br from-white/[0.08] via-white/[0.03] to-transparent backdrop-blur-xl">' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Completed</p>' +
        '<h3 class="text-2xl md:text-3xl font-black text-white">Result Locked</h3>' +
        '<p class="text-xs text-gray-300 mt-2">' + c.esc(winnerText) + '</p>' +
        '<div class="mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-green-400/30 bg-green-500/12 text-green-200 text-[10px] font-black uppercase tracking-widest">' +
        '<i data-lucide="sparkles" class="w-3.5 h-3.5"></i>Match report archived</div>' +
        '<div class="mt-5 grid grid-cols-3 gap-2 items-center max-w-md">' +
        '<div class="p-3 rounded-xl bg-black/45 border border-white/10 text-center">' +
        '<p class="text-[10px] text-gray-500 uppercase tracking-widest">' + c.esc(String(p1.name || 'P1')) + '</p>' +
        '<p class="text-2xl font-black text-white mt-1">' + c.esc(String(p1Score)) + '</p></div>' +
        '<div class="text-center text-gray-500 font-black">VS</div>' +
        '<div class="p-3 rounded-xl bg-black/45 border border-white/10 text-center">' +
        '<p class="text-[10px] text-gray-500 uppercase tracking-widest">' + c.esc(String(p2.name || 'P2')) + '</p>' +
        '<p class="text-2xl font-black text-white mt-1">' + c.esc(String(p2Score)) + '</p></div></div>' +
        '<div class="mt-6 flex flex-wrap items-center gap-2">' +
        '<a href="' + c.esc(bracketHref) + '" class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider hover:opacity-90 transition-opacity">' +
        '<i data-lucide="git-branch" class="w-4 h-4"></i>View Bracket</a>' +
        '<a href="' + c.esc(hubHref) + '" class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg border border-white/25 text-xs font-bold uppercase tracking-wider text-white hover:bg-white/10 transition-colors">' +
        '<i data-lucide="house" class="w-4 h-4"></i>Back To Hub</a></div></section>';
    },

    onAction: async function () { return false; }
  });
})();
