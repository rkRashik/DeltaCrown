/**
 * phase-map-veto.js — Map Veto phase module
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  window.MatchRoom.registerPhase('map_veto', {
    label: function () { return 'Map Veto'; },
    narrative: function () { return 'Run bans and picks in order to lock the final battleground.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var veto = c.asObject(workflow.veto);
      var sequence = c.asList(veto.sequence);
      var step = Math.max(0, c.toInt(veto.step, 0));
      var stepInfo = c.asObject(sequence[step]);
      var expectedSide = c.toInt(stepInfo.side, 0) || 1;
      var expectedAction = String(stepInfo.action || 'ban').toLowerCase() === 'pick' ? 'pick' : 'ban';

      var bansSet = {};
      c.asList(veto.bans).forEach(function (item) { var v = String(item || '').trim(); if (v) bansSet[v] = true; });
      var picksSet = {};
      c.asList(veto.picks).forEach(function (item) { var v = String(item || '').trim(); if (v) picksSet[v] = true; });
      var selectedMap = String(veto.selected_map || '').trim();
      var pool = c.mapPool();

      var side = c.mySide();
      var staff = c.bool(c.asObject(c.state.room.me).is_staff, false);
      var myTurn = staff || side === expectedSide;
      var actionLocked = c.waitingLocked() || c.state.requestBusy;

      var actionCopy = expectedAction === 'pick' ? 'Pick' : 'Ban';
      var statusCopy = step >= sequence.length
        ? (selectedMap ? 'Veto complete. Selected map: ' + selectedMap + '.' : 'Veto sequence complete.')
        : 'Turn: Side ' + expectedSide + ' must ' + actionCopy.toLowerCase() + ' a map.';

      var cards = pool.map(function (mapName) {
        var clean = String(mapName || '').trim();
        if (!clean) return '';
        var isBanned = !!bansSet[clean];
        var isPicked = !!picksSet[clean] || (selectedMap && clean === selectedMap);
        var selectable = !isBanned && !isPicked && step < sequence.length && myTurn && !actionLocked;
        var statusTag = isPicked ? 'Picked' : (isBanned ? 'Banned' : 'Available');
        var className = isPicked ? 'map-card picked' : (isBanned ? 'map-card banned' : 'map-card');
        var statusClass = isPicked ? 'text-ac' : (isBanned ? 'text-rose-300' : 'text-gray-400');
        var actionAttr = selectable
          ? 'data-action="veto-map" data-map="' + encodeURIComponent(clean) + '"'
          : 'disabled';
        return '<button type="button" class="' + className + ' text-left" ' + actionAttr + '>' +
          '<div class="flex items-center justify-between gap-2">' +
          '<span class="text-sm font-bold text-white">' + c.esc(clean) + '</span>' +
          '<span class="text-[10px] uppercase tracking-widest ' + statusClass + '">' + c.esc(statusTag) + '</span></div></button>';
      }).join('');

      var lastAction = c.asObject(veto.last_action);
      var lastActionText = lastAction.item
        ? 'Last: Side ' + c.toInt(lastAction.side, '?') + ' ' + c.esc(String(lastAction.action || '').toLowerCase()) + 'ed ' + c.esc(lastAction.item) + '.'
        : 'No veto actions recorded yet.';

      return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
        '<div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4"><div>' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Valorant Pipeline</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Map Veto</h3></div>' +
        '<span class="text-xs ' + (myTurn ? 'text-ac' : 'text-rose-300') + ' font-bold uppercase tracking-wider">' + c.esc(statusCopy) + '</span></div>' +
        '<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">' +
        (cards || '<p class="text-xs text-gray-400">No maps configured.</p>') + '</div>' +
        '<div class="mt-4 p-3 rounded-xl bg-black/40 border border-white/10">' +
        '<p class="text-[11px] text-gray-300">' + lastActionText + '</p></div></section>';
    },

    onAction: async function (action, trigger, c) {
      if (action !== 'veto-map') return false;
      var rawMap = String(trigger.getAttribute('data-map') || '');
      var mapName = decodeURIComponent(rawMap);
      if (!mapName) return true;
      var workflow = c.asObject(c.state.room.workflow);
      var veto = c.asObject(workflow.veto);
      var sequence = c.asList(veto.sequence);
      var step = Math.max(0, c.toInt(veto.step, 0));
      var stepInfo = c.asObject(sequence[step]);
      var expectedAction = String(stepInfo.action || 'ban').toLowerCase() === 'pick' ? 'pick' : 'ban';
      await c.sendWorkflowAction('veto_map', { map: mapName, action: expectedAction });
      return true;
    }
  });
})();
