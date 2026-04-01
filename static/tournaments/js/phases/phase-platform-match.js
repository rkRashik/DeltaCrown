/**
 * phase-platform-match.js — 1v1/Duel Platform Match phase (Phase 5)
 *
 * Archetype: 1v1 / Duel.
 * Pipeline: Direct Ready → Platform Match → Live → Results.
 *
 * The platform handles matchmaking — players just confirm they've
 * connected on the game platform and the match has started.
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  window.MatchRoom.registerPhase('platform_match', {
    label: function () { return 'Platform Match'; },
    narrative: function () { return 'Connect with your opponent on the game platform and confirm the match has started.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var pm = c.asObject(workflow.platform_match);
      var confirmed1 = c.bool(pm['1'], false);
      var confirmed2 = c.bool(pm['2'], false);
      var side = c.mySide();
      var myConfirmed = side === 1 ? confirmed1 : (side === 2 ? confirmed2 : false);
      var staff = c.bool(c.asObject(c.state.room.me).is_staff, false);
      var locked = c.waitingLocked() || c.state.requestBusy;

      var chip = function (s, ready) {
        var participant = c.participantForSide(s);
        var name = String(participant.name || 'Side ' + s);
        var cls = ready
          ? 'bg-green-500/15 border border-green-400/30 text-green-300'
          : 'bg-amber-500/15 border border-amber-400/30 text-amber-200';
        return '<div class="p-3 rounded-xl border border-white/10 bg-black/40">' +
          '<p class="text-xs text-white font-semibold truncate">' + c.esc(name) + '</p>' +
          '<p class="mt-2 inline-flex px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ' + cls + '">' +
          (ready ? 'Connected' : 'Pending') + '</p></div>';
      };

      var btn = (!myConfirmed && side > 0 && !locked)
        ? '<button type="button" class="btn-primary px-5 py-2 rounded-lg font-bold text-sm mt-4" data-action="confirm-platform">Confirm Connected</button>'
        : '';

      return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
        '<div class="mb-4"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500">1v1 Pipeline</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Platform Match</h3></div>' +
        '<p class="text-sm text-gray-300 mb-4">Connect with your opponent on the game platform, then confirm below.</p>' +
        '<div class="grid grid-cols-2 gap-3">' + chip(1, confirmed1) + chip(2, confirmed2) + '</div>' +
        btn + '</section>';
    },

    onAction: async function (action, trigger, c) {
      if (action !== 'confirm-platform') return false;
      await c.sendWorkflowAction('confirm_platform_match', {});
      return true;
    }
  });
})();
