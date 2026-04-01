/**
 * phase-side-selection.js — Side Selection phase module (Phase 5)
 *
 * Used by Tactical FPS and MOBA archetypes after map veto / hero draft.
 * The coin-toss winner (or designated captain) picks their preferred side.
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  window.MatchRoom.registerPhase('side_selection', {
    label: function () { return 'Side Selection'; },
    narrative: function () { return 'The designated captain selects their preferred starting side.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var ss = c.asObject(workflow.side_selection);
      var chooserSide = c.toInt(ss.chooser_side, 0);
      var selectedSide = String(ss.selected || '').trim();

      var side = c.mySide();
      var staff = c.bool(c.asObject(c.state.room.me).is_staff, false);
      var isChooser = staff || side === chooserSide;
      var locked = c.waitingLocked() || c.state.requestBusy || !!selectedSide;

      var sideName = function (key) {
        var k = String(key || '').toLowerCase();
        if (k === 'ct' || k === 'defence' || k === 'radiant') return 'Defence / Radiant / CT';
        if (k === 't' || k === 'attack' || k === 'dire') return 'Attack / Dire / T';
        return key;
      };

      var options = c.asList(ss.options);
      if (!options.length) options = ['attack', 'defence'];

      var buttons = options.map(function (opt) {
        var val = String(opt || '');
        var chosen = selectedSide && val === selectedSide;
        var cls = chosen
          ? 'btn-primary pointer-events-none'
          : (isChooser && !locked ? 'btn-secondary' : 'btn-secondary opacity-50 pointer-events-none');
        var attr = (!locked && isChooser)
          ? 'data-action="select-side" data-side="' + encodeURIComponent(val) + '"'
          : 'disabled';
        return '<button type="button" class="px-6 py-3 rounded-xl font-bold text-sm ' + cls + '" ' + attr + '>' +
          c.esc(sideName(val)) + (chosen ? ' ✓' : '') + '</button>';
      }).join('');

      var statusCopy = selectedSide
        ? 'Side locked: ' + sideName(selectedSide) + '.'
        : (chooserSide ? 'Side ' + chooserSide + ' is choosing…' : 'Waiting for side selection…');

      return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
        '<div class="mb-4"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Match Pipeline</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Side Selection</h3></div>' +
        '<p class="text-sm text-gray-300 mb-5">' + c.esc(statusCopy) + '</p>' +
        '<div class="flex flex-wrap gap-3">' + buttons + '</div></section>';
    },

    onAction: async function (action, trigger, c) {
      if (action !== 'select-side') return false;
      var raw = String(trigger.getAttribute('data-side') || '');
      var side = decodeURIComponent(raw);
      if (!side) return true;
      await c.sendWorkflowAction('select_side', { side: side });
      return true;
    }
  });
})();
