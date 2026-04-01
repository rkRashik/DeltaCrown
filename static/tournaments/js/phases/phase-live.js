/**
 * phase-live.js — Live Match phase module
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  function liveInfoCard(c, label, value) {
    return '<div class="p-3 rounded-xl border border-white/10 bg-black/40">' +
      '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">' + c.esc(label) + '</p>' +
      '<p class="text-sm text-white font-semibold mt-1 break-all">' + c.esc(value) + '</p></div>';
  }

  window.MatchRoom.registerPhase('live', {
    label: function () { return 'Live Match'; },
    narrative: function () { return 'Match is live. Finish gameplay, then move to result declaration.'; },

    render: function (c) {
      var lobby = c.asObject(c.state.room.lobby);
      var creds = c.asObject(c.asObject(c.state.room.workflow).credentials);
      var schema = c.credentialSchema().filter(function (field) {
        return String(c.asObject(field).key || '') !== 'notes';
      });

      var cards = schema.map(function (field) {
        var row = c.asObject(field);
        var key = String(row.key || '').trim();
        if (!key) return '';
        var label = String(row.label || c.credentialLabelForKey(key) || key);
        var value = String(lobby[key] || creds[key] || '');
        return liveInfoCard(c, label, value || 'Pending');
      }).filter(Boolean).join('');

      var gridClass = 'grid grid-cols-1 md:grid-cols-2 gap-3';
      if (schema.length >= 3) gridClass = 'grid grid-cols-1 md:grid-cols-3 gap-3';
      if (schema.length >= 4) gridClass = 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3';

      return '<section class="glass-panel rounded-2xl p-6 md:p-8 border-t-4 border-green-500">' +
        '<div class="flex flex-col md:flex-row md:items-center justify-between gap-3"><div>' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Match Runtime</p>' +
        '<h3 class="text-2xl md:text-3xl font-black text-white">Live Match In Progress</h3>' +
        '<p class="text-xs text-gray-400 mt-2">Play the match now. Result Desk unlocks for final score declaration in the next phase.</p></div>' +
        '<div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-green-400/30 bg-green-500/10 text-green-200 text-[10px] font-black uppercase tracking-widest">' +
        '<span class="live-pulse"></span>Match Live</div></div>' +
        '<div class="mt-5 ' + gridClass + '">' +
        (cards || liveInfoCard(c, 'Lobby Code', lobby.lobby_code || 'Pending')) + '</div></section>';
    },

    onAction: async function () { return false; }
  });
})();
