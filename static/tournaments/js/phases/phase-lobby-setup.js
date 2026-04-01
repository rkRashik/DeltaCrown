/**
 * phase-lobby-setup.js — Lobby Setup phase module
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  function renderCredentialField(c, field, credentials, readonly) {
    var row = c.asObject(field);
    var key = String(row.key || '').trim();
    if (!key) return '';
    var id = c.credentialInputId(key);
    var label = String(row.label || c.credentialLabelForKey(key) || key);
    var value = String(credentials[key] || '');
    var multiline = String(row.kind || '').toLowerCase() === 'textarea' || key === 'notes';
    if (multiline) {
      return '<label class="text-xs text-gray-400 md:col-span-2">' + c.esc(label) +
        '<textarea id="' + c.esc(id) + '" class="lobby-input mt-1 min-h-[84px]" ' + (readonly ? 'readonly' : '') + '>' + c.esc(value) + '</textarea></label>';
    }
    return '<label class="text-xs text-gray-400">' + c.esc(label) +
      '<input id="' + c.esc(id) + '" class="lobby-input mt-1" value="' + c.esc(value) + '" ' + (readonly ? 'readonly' : '') + ' /></label>';
  }

  window.MatchRoom.registerPhase('lobby_setup', {
    label: function () { return 'Lobby Setup'; },
    narrative: function () { return 'Host publishes lobby credentials and both teams sync in one room.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var creds = c.asObject(workflow.credentials);
      var me = c.asObject(c.state.room.me);
      var host = c.participantForSide(1);
      var hostName = String(host.name || 'Host');
      var schema = c.credentialSchema();
      var isHost = c.bool(me.is_host, false);
      var canStartLive = c.bool(isHost || me.is_staff, false);
      var disabled = c.waitingLocked() || c.state.requestBusy;

      if (isHost) {
        var fieldsHtml = schema.map(function (field) {
          return renderCredentialField(c, field, creds, false);
        }).join('');

        return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
          '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Host Broadcast</p>' +
          '<h3 class="text-xl md:text-2xl font-black text-white">Share Match Room Credentials</h3>' +
          '<p class="text-xs text-gray-400 mt-2">You are Host (Side 1). Share room details when ready so both sides join the same match instance.</p>' +
          '<form id="credentials-form" class="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">' + fieldsHtml +
          '<div class="md:col-span-2 flex flex-wrap items-center justify-end gap-2 pt-1">' +
          '<button type="submit" class="px-4 py-2.5 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider ' + (disabled ? 'opacity-50 cursor-not-allowed' : '') + '" ' + (disabled ? 'disabled' : '') + '>Share With Opponent</button>' +
          '<button type="button" data-action="start-live" class="px-4 py-2.5 rounded-lg border border-white/25 text-xs font-bold uppercase tracking-wider text-white ' + ((!canStartLive || disabled) ? 'opacity-50 cursor-not-allowed' : '') + '" ' + ((!canStartLive || disabled) ? 'disabled' : '') + '>Mark Match Live</button>' +
          '</div></form></section>';
      }

      return '<section class="glass-panel rounded-2xl p-6 md:p-8 border-t-4 border-ac">' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Guest View</p>' +
        '<div class="flex flex-col items-center justify-center text-center py-4 md:py-8">' +
        '<div class="relative w-14 h-14 mb-5">' +
        '<div class="absolute inset-0 rounded-full border-4 border-white/10"></div>' +
        '<div class="absolute inset-0 rounded-full border-4 border-t-transparent animate-spin border-ac"></div>' +
        '<div class="absolute inset-0 flex items-center justify-center">' +
        '<i data-lucide="radar" class="w-5 h-5 text-ac animate-pulse"></i></div></div>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Awaiting Host Room Details</h3>' +
        '<p class="text-xs md:text-sm text-gray-400 mt-2 max-w-md">' + c.esc(hostName) + ' (Side 1) is setting up the room. Stay on this screen and details will appear automatically.</p>' +
        '</div></section>';
    },

    onAction: async function (action, trigger, c) {
      if (action === 'start-live') {
        await c.sendWorkflowAction('start_live', {});
        return true;
      }
      return false;
    }
  });
})();
