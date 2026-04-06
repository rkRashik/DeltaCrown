/**
 * phase-live.js — Live Match phase module  v20260405b
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  // Tick handle so we don't leak timers on re-render
  var _liveTimerHandle = null;

  function liveInfoCard(c, label, value) {
    return '<div class="p-3 rounded-xl border border-white/10 bg-black/40">' +
      '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">' + c.esc(label) + '</p>' +
      '<p class="text-sm text-white font-semibold mt-1 break-all">' + c.esc(value) + '</p></div>';
  }

  function formatElapsed(seconds) {
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    var s = seconds % 60;
    if (h > 0) return h + 'hr ' + (m < 10 ? '0' : '') + m + 'min';
    return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
  }

  function startLiveTimer(startedAt) {
    if (_liveTimerHandle) window.clearInterval(_liveTimerHandle);
    var el = document.getElementById('live-elapsed-timer');
    if (!el) return;
    var base = startedAt ? Date.parse(startedAt) : Date.now();
    function tick() {
      var el2 = document.getElementById('live-elapsed-timer');
      if (!el2) { window.clearInterval(_liveTimerHandle); _liveTimerHandle = null; return; }
      var elapsed = Math.max(0, Math.floor((Date.now() - base) / 1000));
      el2.textContent = formatElapsed(elapsed);
    }
    tick();
    _liveTimerHandle = window.setInterval(tick, 1000);
  }

  window.MatchRoom.registerPhase('live', {
    label: function () { return 'Live Match'; },
    narrative: function () { return 'Match is live. Finish gameplay, then move to result declaration.'; },

    render: function (c) {
      var lobby = c.asObject(c.state.room.lobby);
      var creds = c.asObject(c.asObject(c.state.room.workflow).credentials);
      var match = c.asObject(c.state.room.match);
      var me = c.asObject(c.state.room.me);
      var side = c.mySide();
      var isParticipant = side === 1 || side === 2;
      var busy = c.bool(c.state.requestBusy, false);

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

      var startedAt = String(match.started_at || '');

      // Proceed-to-results CTA — visible to both participants
      var proceedBtn = '';
      if (isParticipant) {
        var btnDisabled = busy || c.waitingLocked();
        proceedBtn = '<div class="mt-6 border-t border-white/8 pt-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">' +
          '<div>' +
          '<p class="text-xs font-bold text-white">Match finished?</p>' +
          '<p class="text-[11px] text-gray-400 mt-0.5">Tap below once gameplay is done. Both players can trigger this.</p>' +
          '</div>' +
          '<button data-action="proceed-to-results" ' +
          'class="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-ac text-black text-xs font-black uppercase tracking-wider hover:opacity-90 active:scale-95 transition-all ' +
          (btnDisabled ? 'opacity-50 pointer-events-none' : '') + '" ' +
          (btnDisabled ? 'disabled' : '') + '>' +
          '<i data-lucide="flag-triangle-right" class="w-4 h-4"></i>' +
          (busy ? 'Please wait…' : 'Game Done — Submit Results') +
          '</button></div>';
      }

      var html = '<section class="glass-panel rounded-2xl p-6 md:p-8 border-t-4 border-green-500">' +
        '<div class="flex flex-col md:flex-row md:items-center justify-between gap-3"><div>' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Match Runtime</p>' +
        '<h3 class="text-2xl md:text-3xl font-black text-white">Live Match In Progress</h3>' +
        '<div class="flex items-center gap-4 mt-2">' +
        '<p class="text-xs text-gray-400">Play the match now — Result Desk unlocks when you click the button below.</p>' +
        '</div></div>' +
        '<div class="flex items-center gap-3 shrink-0">' +
        (startedAt ? '<div class="text-center"><p class="text-[9px] font-black text-gray-500 uppercase tracking-widest">Elapsed</p><p id="live-elapsed-timer" class="font-mono font-black text-lg text-white tabular-nums">00:00</p></div>' : '') +
        '<div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-green-400/30 bg-green-500/10 text-green-200 text-[10px] font-black uppercase tracking-widest">' +
        '<span class="live-pulse"></span>Match Live</div></div></div>' +
        '<div class="mt-5 ' + gridClass + '">' +
        (cards || liveInfoCard(c, 'Lobby Code', lobby.lobby_code || 'Pending')) + '</div>' +
        proceedBtn + '</section>';

      // Start timer after render (next tick)
      if (startedAt) window.setTimeout(function () { startLiveTimer(startedAt); }, 0);

      return html;
    },

    onAction: async function (action, _trigger, c) {
      if (action === 'proceed-to-results') {
        await c.sendWorkflowAction('start_results', {});
        return true;
      }
      return false;
    }
  });
})();
