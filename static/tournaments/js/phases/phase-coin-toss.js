/**
 * phase-coin-toss.js — Coin Toss phase module
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  window.MatchRoom.registerPhase('coin_toss', {
    label: function () { return 'Coin Toss'; },
    narrative: function () { return 'Resolve first control so both sides can start with a fair edge.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var toss = c.asObject(workflow.coin_toss);
      var winnerSide = c.toInt(toss.winner_side, 0);
      var winnerLabel = (winnerSide === 1 || winnerSide === 2)
        ? 'Side ' + winnerSide + ' won toss control.'
        : 'Toss not resolved yet.';
      var side = c.mySide();
      var me = c.asObject(c.state.room.me);
      var canAct = (side === 1 || c.bool(me.is_staff, false))
        && !c.waitingLocked()
        && !c.state.requestBusy;

      return '<section class="glass-panel rounded-2xl p-6 md:p-8 border-t-4 border-ac">' +
        '<div class="flex flex-col md:flex-row md:items-center justify-between gap-4"><div>' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Valorant Pipeline</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Coin Toss</h3>' +
        '<p class="text-xs text-gray-400 mt-2">Resolve first control before map veto starts.</p></div>' +
        '<button type="button" data-action="coin-toss" class="px-5 py-3 rounded-xl bg-white text-black text-xs font-black uppercase tracking-widest active:scale-95 transition-transform ' + (canAct ? '' : 'opacity-50 cursor-not-allowed') + '" ' + (canAct ? '' : 'disabled') + '>Resolve Toss</button></div>' +
        '<div class="mt-5 p-4 rounded-xl bg-black/40 border border-white/10">' +
        '<p class="text-xs text-ac font-bold uppercase tracking-wide">' + c.esc(winnerLabel) + '</p>' +
        '<p class="text-[11px] text-gray-400 mt-1">' + c.esc(toss.performed_at ? 'Updated ' + c.shortClock(toss.performed_at) : 'Waiting for toss execution.') + '</p></div></section>';
    },

    onAction: async function (action, trigger, c) {
      if (action !== 'coin-toss') return false;
      await c.sendWorkflowAction('coin_toss', {});
      return true;
    }
  });
})();
