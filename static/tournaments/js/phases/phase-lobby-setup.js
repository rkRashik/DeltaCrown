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

  // Read-only display card used by the guest view once credentials are published.
  function renderCredentialDisplay(c, field, credentials) {
    var row = c.asObject(field);
    var key = String(row.key || '').trim();
    if (!key) return '';
    var value = String(credentials[key] || '').trim();
    if (!value) return '';
    var label = String(row.label || c.credentialLabelForKey(key) || key);
    var copyId = 'copy-cred-' + c.esc(key);
    return '<div class="flex items-start justify-between gap-3 bg-black/35 border border-white/10 rounded-xl px-4 py-3">' +
      '<div class="min-w-0">' +
      '<p class="text-[10px] font-black uppercase tracking-wider text-gray-500 mb-0.5">' + c.esc(label) + '</p>' +
      '<p class="text-sm font-bold text-white break-all font-mono">' + c.esc(value) + '</p>' +
      '</div>' +
      '<button type="button" id="' + copyId + '" data-copy-value="' + c.esc(value) + '" ' +
      'class="shrink-0 mt-0.5 p-1.5 rounded-lg bg-white/6 border border-white/10 text-gray-400 hover:text-white hover:border-white/25 transition-colors active:scale-95" title="Copy">' +
      '<i data-lucide="copy" class="w-3.5 h-3.5 pointer-events-none"></i></button>' +
      '</div>';
  }

  window.MatchRoom.registerPhase('lobby_setup', {
    label: function () { return 'Lobby Setup'; },
    narrative: function () { return 'Host publishes lobby credentials. Join the room, then mark match live.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var creds = c.asObject(workflow.credentials);
      var me = c.asObject(c.state.room.me);
      var host = c.participantForSide(1);
      var hostName = String(host.name || 'Host');
      var schema = c.credentialSchema();
      var isHost = c.bool(me.is_host, false);
      var isStaff = c.bool(me.is_staff, false);
      // Staff (admins/organizers) can view & edit credentials on behalf of the host
      var canEdit = isHost || isStaff;
      var canStartLive = c.bool(isHost || me.is_staff, false);
      var disabled = c.waitingLocked() || c.state.requestBusy;

      // Detect if credentials have been published (any non-empty credential key)
      var hasCredentials = schema.some(function (f) {
        var k = String(c.asObject(f).key || '').trim();
        return k && String(creds[k] || '').trim().length > 0;
      });

      if (canEdit) {
        var fieldsHtml = schema.map(function (field) {
          return renderCredentialField(c, field, creds, false);
        }).join('');

        // If credentials already shared, show a "published" badge on the host view
        var publishedBadge = hasCredentials
          ? '<div class="flex items-center gap-2 mb-5 px-3 py-2 rounded-xl bg-emerald-500/12 border border-emerald-400/25">' +
            '<span class="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]"></span>' +
            '<span class="text-[11px] font-black text-emerald-300 uppercase tracking-wider">Credentials Published — Guests Can See Room Details</span>' +
            '</div>'
          : '';

        return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
          '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Host Broadcast</p>' +
          '<h3 class="text-xl md:text-2xl font-black text-white">Share Match Room Credentials</h3>' +
          '<p class="text-xs text-gray-400 mt-1 mb-4">You are Host (Side 1). Share room details so both players can join the same match instance.</p>' +
          publishedBadge +
          '<form id="credentials-form" class="mt-2 grid grid-cols-1 md:grid-cols-2 gap-3">' + fieldsHtml +
          '<div class="md:col-span-2 flex flex-wrap items-center justify-end gap-2 pt-1">' +
          '<button type="submit" class="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider ' + (disabled ? 'opacity-50 cursor-not-allowed' : 'active:scale-95') + '" ' + (disabled ? 'disabled' : '') + '>' +
          '<i data-lucide="send" class="w-3.5 h-3.5"></i>' + (hasCredentials ? 'Update &amp; Reshare' : 'Share With Opponent') + '</button>' +
          '<button type="button" data-action="start-live" class="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border text-xs font-bold uppercase tracking-wider ' +
          (hasCredentials ? 'border-emerald-400/40 bg-emerald-500/15 text-emerald-200 ' : 'border-white/25 bg-white/5 text-white ') +
          ((!canStartLive || disabled) ? 'opacity-50 cursor-not-allowed' : 'active:scale-95') + '" ' + ((!canStartLive || disabled) ? 'disabled' : '') + '>' +
          '<i data-lucide="flag" class="w-3.5 h-3.5"></i>Mark Match Live</button>' +
          '</div></form></section>';
      }

      // ── Guest view ────────────────────────────────────────────────────
      if (hasCredentials) {
        // Credentials received — show them in read-only card grid with copy buttons
        var credsHtml = schema.map(function (f) {
          return renderCredentialDisplay(c, f, creds);
        }).filter(Boolean).join('');

        return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-emerald-400/60">' +
          '<div class="flex items-center justify-between mb-5">' +
          '<div>' +
          '<div class="flex items-center gap-2 mb-1">' +
          '<span class="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]"></span>' +
          '<p class="text-[10px] font-black uppercase tracking-widest text-emerald-400">Room Ready</p>' +
          '</div>' +
          '<h3 class="text-xl md:text-2xl font-black text-white">Match Room Details</h3>' +
          '<p class="text-xs text-gray-400 mt-1">' + c.esc(hostName) + ' shared the room. Join the lobby, then come back to report your result.</p>' +
          '</div>' +
          '<div class="shrink-0 w-12 h-12 rounded-xl bg-emerald-500/15 border border-emerald-400/25 flex items-center justify-center">' +
          '<i data-lucide="door-open" class="w-6 h-6 text-emerald-300"></i>' +
          '</div>' +
          '</div>' +
          '<div class="space-y-2">' + credsHtml + '</div>' +
          '<p class="text-[10px] text-gray-600 mt-4 text-center">Once both players finish the game, return here to submit your result.</p>' +
          '</section>';
      }

      // No credentials yet — waiting for host  
      return '<section class="glass-panel rounded-2xl p-6 md:p-8 border-t-4 border-ac">' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Guest View</p>' +
        '<div class="flex flex-col items-center justify-center text-center py-4 md:py-8">' +
        '<div class="relative w-14 h-14 mb-5">' +
        '<div class="absolute inset-0 rounded-full border-4 border-white/10"></div>' +
        '<div class="absolute inset-0 rounded-full border-4 border-t-transparent animate-spin border-ac"></div>' +
        '<div class="absolute inset-0 flex items-center justify-center">' +
        '<i data-lucide="radar" class="w-5 h-5 text-ac animate-pulse"></i></div></div>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Awaiting Host Room Details</h3>' +
        '<p class="text-xs md:text-sm text-gray-400 mt-2 max-w-md">' + c.esc(hostName) + ' (Side 1) is setting up the room. Stay on this screen — details will appear automatically.</p>' +
        '</div></section>';
    },

    onAction: async function (action, trigger, c) {
      if (action === 'start-live') {
        await c.sendWorkflowAction('start_live', {});
        return true;
      }
      // Copy credential value to clipboard
      if (action === undefined && trigger && trigger.dataset && trigger.dataset.copyValue !== undefined) {
        var val = String(trigger.dataset.copyValue || '');
        if (navigator.clipboard && val) {
          navigator.clipboard.writeText(val).then(function () {
            c.showToast('Copied to clipboard!', 'success');
          }).catch(function () {
            c.showToast('Copy failed — select manually.', 'error');
          });
        }
        return true;
      }
      return false;
    }
  });

  // Delegate copy button clicks (they don't have data-action, use data-copy-value)
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('[data-copy-value]');
    if (!btn) return;
    var val = String(btn.getAttribute('data-copy-value') || '').trim();
    if (!val) return;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(val).then(function () {
        var ctx = window.MatchRoom && window.MatchRoom.ctx ? window.MatchRoom.ctx() : null;
        if (ctx) ctx.showToast('Copied!', 'success');
        // Brief visual flash on the button
        var prev = btn.innerHTML;
        btn.innerHTML = '<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400 pointer-events-none"></i>';
        if (window.lucide) window.lucide.createIcons({ nodes: [btn] });
        setTimeout(function () {
          btn.innerHTML = prev;
          if (window.lucide) window.lucide.createIcons({ nodes: [btn] });
        }, 1600);
      }).catch(function () { });
    }
  });
})();

