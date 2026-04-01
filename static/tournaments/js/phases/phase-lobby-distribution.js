/**
 * phase-lobby-distribution.js — Battle Royale Lobby Distribution (Phase 5)
 *
 * Archetype: Battle Royale (PUBG / Free Fire).
 * Pipeline: Lobby Distribution → Server Assignment → Live → Matrix Results.
 *
 * Assigns multiple teams/squads to numbered lobby slots. The organiser
 * (host/staff) manages slot assignments; participants see their assignment.
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  window.MatchRoom.registerPhase('lobby_distribution', {
    label: function () { return 'Lobby Distribution'; },
    narrative: function () { return 'Teams are assigned to lobby slots before the Battle Royale match begins.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var dist = c.asObject(workflow.lobby_distribution);
      var slots = c.asList(dist.slots);
      var totalSlots = c.toInt(dist.total_slots, 0) || slots.length || 20;
      var side = c.mySide();
      var staff = c.bool(c.asObject(c.state.room.me).is_staff, false);
      var locked = c.waitingLocked() || c.state.requestBusy;

      var mySlot = null;
      var slotHtml = '';
      for (var i = 0; i < totalSlots; i++) {
        var s = c.asObject(slots[i]);
        var team = String(s.team_name || s.participant_name || '').trim();
        var slotNum = i + 1;
        if (s.participant_id && s.participant_id === c.toInt(c.asObject(c.state.room.me).participant_id, 0)) {
          mySlot = slotNum;
        }
        var cellCls = team
          ? 'bg-ac/10 border-ac/30 text-ac'
          : 'bg-black/40 border-white/10 text-gray-500';
        slotHtml += '<div class="p-2 rounded-lg border text-center text-xs font-bold ' + cellCls + '">' +
          '<span class="block text-[10px] text-gray-500">#' + slotNum + '</span>' +
          (team ? c.esc(team) : '—') + '</div>';
      }

      var statusCopy = mySlot
        ? 'You are assigned to Slot #' + mySlot + '.'
        : (staff ? 'Assign teams to lobby slots.' : 'Waiting for slot assignment…');

      var confirmBtn = staff && !locked
        ? '<div class="mt-4"><button type="button" class="btn-primary px-5 py-2 rounded-lg font-bold text-sm" data-action="confirm-distribution">Confirm Distribution</button></div>'
        : '';

      return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
        '<div class="mb-4"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Battle Royale Pipeline</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Lobby Distribution</h3></div>' +
        '<p class="text-sm text-gray-300 mb-4">' + c.esc(statusCopy) + '</p>' +
        '<div class="grid grid-cols-4 sm:grid-cols-5 gap-2">' + slotHtml + '</div>' +
        confirmBtn + '</section>';
    },

    onAction: async function (action, trigger, c) {
      if (action !== 'confirm-distribution') return false;
      await c.sendWorkflowAction('confirm_distribution', {});
      return true;
    }
  });
})();
