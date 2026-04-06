/**
 * phase-direct-ready.js — Direct Ready Check phase module
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  function renderReadyChip(c, side, isReady) {
    var participant = c.participantForSide(side);
    var name = String(participant.name || 'Side ' + side);
    var cls = isReady
      ? 'bg-green-500/15 border border-green-400/30 text-green-300'
      : 'bg-amber-500/15 border border-amber-400/30 text-amber-200';
    return '<div class="p-3 rounded-xl border border-white/10 bg-black/40">' +
      '<p class="text-xs text-white font-semibold truncate">' + c.esc(name) + '</p>' +
      '<p class="mt-2 inline-flex px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ' + cls + '">' +
      (isReady ? 'Ready' : 'Pending') + '</p></div>';
  }

  window.MatchRoom.registerPhase('direct_ready', {
    label: function () { return 'Direct Ready'; },
    narrative: function () { return 'Both sides confirm ready status before host credentials unlock.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var ready = c.asObject(workflow.direct_ready);
      var ready1 = c.bool(ready['1'], false);
      var ready2 = c.bool(ready['2'], false);
      var side = c.mySide();
      var meReady = side === 1 ? ready1 : (side === 2 ? ready2 : false);
      var canReady = (side === 1 || side === 2) && !meReady && !c.state.requestBusy && !c.waitingLocked();
      var statusText = ready1 && ready2
        ? 'Both sides ready. Advancing to lobby setup.'
        : 'Waiting for both sides to confirm.';

      return '<section class="glass-panel rounded-2xl p-6 md:p-8 border-t-4 border-ac">' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">eFootball Pipeline</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Direct Ready Check</h3>' +
        '<p class="text-xs text-gray-400 mt-2">Both sides must confirm readiness before lobby credentials open.</p>' +
        '<div class="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3">' +
        renderReadyChip(c, 1, ready1) + renderReadyChip(c, 2, ready2) + '</div>' +
        '<div class="mt-5 flex items-center justify-between gap-3 flex-wrap">' +
        '<p class="text-xs text-gray-400">' + c.esc(statusText) + '</p>' +
        '<button type="button" data-action="direct-ready" class="px-5 py-3 rounded-xl bg-ac text-black text-xs font-black uppercase tracking-widest active:scale-95 transition-transform ' +
        (canReady ? '' : 'opacity-50 cursor-not-allowed') + '" ' + (canReady ? '' : 'disabled') + '>Mark Ready</button></div></section>';
    },

    onAction: async function (action, trigger, c) {
      if (action !== 'direct-ready') return false;
      await c.sendWorkflowAction('direct_ready', {});
      return true;
    }
  });
})();
