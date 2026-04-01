/**
 * phase-server-assignment.js — BR Server Assignment (Phase 5)
 *
 * Archetype: Battle Royale.  After lobby distribution the host assigns
 * a game server / custom room code so all participants can join.
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  window.MatchRoom.registerPhase('server_assignment', {
    label: function () { return 'Server Assignment'; },
    narrative: function () { return 'The host assigns a game server and shares the custom room code.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var sa = c.asObject(workflow.server_assignment);
      var roomId = String(sa.room_id || '').trim();
      var password = String(sa.password || '').trim();
      var region = String(sa.region || '').trim();

      var staff = c.bool(c.asObject(c.state.room.me).is_staff, false);
      var locked = c.waitingLocked() || c.state.requestBusy;

      if (roomId) {
        return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
          '<div class="mb-4"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Battle Royale Pipeline</p>' +
          '<h3 class="text-xl md:text-2xl font-black text-white">Server Assigned</h3></div>' +
          '<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">' +
          '<div class="p-3 rounded-xl bg-black/40 border border-white/10"><p class="text-[10px] text-gray-500 mb-1">Room ID</p><p class="text-sm font-bold text-white">' + c.esc(roomId) + '</p></div>' +
          (password ? '<div class="p-3 rounded-xl bg-black/40 border border-white/10"><p class="text-[10px] text-gray-500 mb-1">Password</p><p class="text-sm font-bold text-white">' + c.esc(password) + '</p></div>' : '') +
          (region ? '<div class="p-3 rounded-xl bg-black/40 border border-white/10"><p class="text-[10px] text-gray-500 mb-1">Region</p><p class="text-sm font-bold text-white">' + c.esc(region) + '</p></div>' : '') +
          '</div></section>';
      }

      if (!staff) {
        return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
          '<div class="mb-4"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Battle Royale Pipeline</p>' +
          '<h3 class="text-xl md:text-2xl font-black text-white">Server Assignment</h3></div>' +
          '<p class="text-sm text-gray-400">Waiting for the host to assign a game server…</p></section>';
      }

      return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
        '<div class="mb-4"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Battle Royale Pipeline</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Assign Server</h3></div>' +
        '<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">' +
        '<div><label class="label text-[10px]">Room ID</label><input type="text" class="input" id="sa-room-id" placeholder="Custom Room ID"></div>' +
        '<div><label class="label text-[10px]">Password</label><input type="text" class="input" id="sa-password" placeholder="Room Password"></div>' +
        '</div>' +
        '<button type="button" class="btn-primary px-5 py-2 rounded-lg font-bold text-sm" data-action="assign-server"' +
        (locked ? ' disabled' : '') + '>Assign Server</button></section>';
    },

    onAction: async function (action, trigger, c) {
      if (action !== 'assign-server') return false;
      var roomId = (document.getElementById('sa-room-id') || {}).value || '';
      var password = (document.getElementById('sa-password') || {}).value || '';
      if (!roomId.trim()) return true;
      await c.sendWorkflowAction('assign_server', { room_id: roomId.trim(), password: password.trim() });
      return true;
    }
  });
})();
