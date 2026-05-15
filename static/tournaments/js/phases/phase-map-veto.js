/**
 * phase-map-veto.js — Map Veto phase module (RP.E)
 *
 * Premium veto board:
 *   - Map cards render real map IMAGES from apps/games (via
 *     ``workflow.map_pool_meta``) — when an image is missing for a game,
 *     a stylised name-only tile takes over so the layout never collapses.
 *   - Turn ownership shown as a coloured strip across the top: actor team
 *     logo + name + step counter + countdown ring + action verb in plain
 *     language ("Sentinels bans a map · 12s left").
 *   - Server-driven countdown reads ``step_expires_at``; <5s triggers an
 *     urgent state; sweeper (P2.B) enforces the timeout server-side.
 *   - Ban / pick states overlay on the IMAGE: ban → slash + dimmed; pick →
 *     glow border + shine animation. Disabled cards cannot be clicked.
 *   - Selected map (BO1) or current series map (BO3+) gets a "Locked"
 *     callout below the grid.
 *   - Veto history below the grid as a timeline with per-side colour.
 *
 * Data contract (all already in payload from RP.F):
 *   workflow.veto.{sequence, step, pool, bans, picks, selected_map,
 *                  step_expires_at, time_per_action_seconds, auto_random_on_timeout, last_action}
 *   workflow.map_pool_meta = [{name, code, image_url}, ...] (parallel to veto.pool)
 *   workflow.series.current_map = string (active map in BO3+ when in lobby_setup phase)
 *   match.participant1/2 = {name, logo_url, ...}
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  function _participantName(c, side) {
    var match = c.asObject(c.state.room.match);
    var p = c.asObject(match[side === 1 ? 'participant1' : 'participant2']);
    var n = String(p.name || p.team_name || p.username || '').trim();
    return n || 'Side ' + side;
  }

  function _secondsRemaining(iso) {
    if (!iso) return null;
    var t = Date.parse(iso);
    if (isNaN(t)) return null;
    return Math.max(0, Math.floor((t - Date.now()) / 1000));
  }

  function _renderTimer(remaining, total) {
    if (remaining === null || total <= 0) return '';
    var circumference = 2 * Math.PI * 22;
    var ratio = Math.max(0, Math.min(1, remaining / total));
    var dashOffset = (circumference * (1 - ratio)).toFixed(2);
    var urgent = remaining <= 5;
    return '<div class="veto-timer ' + (urgent ? 'is-urgent' : '') + '" data-veto-timer data-expires-total="' + total + '">' +
      '<svg viewBox="0 0 50 50">' +
        '<circle class="track" cx="25" cy="25" r="22"/>' +
        '<circle class="fill" cx="25" cy="25" r="22" stroke-dasharray="' + circumference.toFixed(2) + '" stroke-dashoffset="' + dashOffset + '" data-timer-fill/>' +
      '</svg>' +
      '<span class="timer-label" data-timer-label>' + remaining + '</span>' +
    '</div>';
  }

  // Build a map-name → meta object lookup from the parallel pool_meta list.
  function _mapMetaIndex(workflow) {
    var meta = (workflow && Array.isArray(workflow.map_pool_meta)) ? workflow.map_pool_meta : [];
    var idx = {};
    for (var i = 0; i < meta.length; i++) {
      var m = meta[i];
      if (m && m.name) idx[String(m.name).toLowerCase()] = m;
    }
    return idx;
  }

  function _mapCard(c, mapName, meta, isBanned, isPicked, selectable) {
    var image = meta && meta.image_url ? String(meta.image_url) : '';
    var code  = meta && meta.code      ? String(meta.code)      : '';
    var classes = ['map-card'];
    if (isPicked) classes.push('picked');
    else if (isBanned) classes.push('banned');

    var statusBadge;
    if (isPicked)      statusBadge = '<span class="text-[10px] uppercase tracking-widest font-black text-ac">Selected</span>';
    else if (isBanned) statusBadge = '<span class="text-[10px] uppercase tracking-widest font-black text-rose-300">Banned</span>';
    else if (selectable) statusBadge = '<span class="text-[10px] uppercase tracking-widest font-bold text-gray-400">Available</span>';
    else statusBadge = '<span class="text-[10px] uppercase tracking-widest font-bold text-gray-600">Locked</span>';

    // Visual surface: image on top (or gradient fallback), name + code below.
    var visual = image
      ? '<div class="absolute inset-0 bg-cover bg-center" style="background-image:url(' + JSON.stringify(image).slice(1, -1) + ');"></div>' +
        '<div class="absolute inset-0" style="background:linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.75) 100%);"></div>'
      : '<div class="absolute inset-0" style="background:linear-gradient(135deg, rgba(var(--ar),var(--ag),var(--ab),0.08) 0%, rgba(0,0,0,0.4) 100%);"></div>';

    var actionAttr = selectable
      ? 'data-action="veto-map" data-map="' + encodeURIComponent(mapName) + '"'
      : 'disabled';

    return '<button type="button" class="' + classes.join(' ') + '" style="padding:0; min-height:8.5rem; display:flex; flex-direction:column;" ' + actionAttr + '>' +
      '<div class="relative w-full" style="aspect-ratio:16/9; min-height:5rem;">' +
        visual +
        (code ? '<span class="absolute top-2 left-2 text-[9px] font-mono font-bold uppercase tracking-widest text-white/70 px-1.5 py-0.5 rounded bg-black/40">' + c.esc(code) + '</span>' : '') +
      '</div>' +
      '<div class="px-3 py-2 flex items-center justify-between gap-2 w-full">' +
        '<span class="text-sm font-black text-white truncate">' + c.esc(mapName) + '</span>' +
        statusBadge +
      '</div>' +
    '</button>';
  }

  function _historyHTML(c, workflow) {
    var veto = c.asObject(workflow.veto);
    var sequence = c.asList(veto.sequence);
    var bans = c.asList(veto.bans);
    var picks = c.asList(veto.picks);
    var step = Math.max(0, c.toInt(veto.step, 0));
    var lastAction = c.asObject(veto.last_action);
    var rows = '';
    var banI = 0, pickI = 0;
    for (var i = 0; i < step; i++) {
      var s = c.asObject(sequence[i]);
      var action = String(s.action || 'ban').toLowerCase();
      var item = action === 'pick' ? (picks[pickI++] || '') : (bans[banI++] || '');
      if (!item) continue;
      var side = parseInt(s.side, 10) || 1;
      var isAuto = (i === step - 1) && c.bool(lastAction.auto, false);
      rows += '<div class="veto-history-row">' +
        '<span class="step-num">' + (i + 1) + '</span>' +
        '<span class="action-tag ' + action + '">' + action + '</span>' +
        '<span class="map-name">' + c.esc(item) + '</span>' +
        '<span class="side-indicator side-' + (side === 1 ? 'a' : 'b') + '" style="padding:0.15rem 0.5rem; font-size:0.6rem;">' +
          c.esc(_participantName(c, side).slice(0, 18)) +
        '</span>' +
        (isAuto ? '<span class="auto-tag">(auto)</span>' : '') +
      '</div>';
    }
    return rows;
  }

  window.MatchRoom.registerPhase('map_veto', {
    label: function () { return 'Map Veto'; },
    narrative: function () { return 'Bans and picks resolve the final battleground.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var veto = c.asObject(workflow.veto);
      var sequence = c.asList(veto.sequence);
      var step = Math.max(0, c.toInt(veto.step, 0));
      var stepInfo = c.asObject(sequence[step]);
      var expectedSide = c.toInt(stepInfo.side, 0) || 1;
      var expectedAction = String(stepInfo.action || 'ban').toLowerCase() === 'pick' ? 'pick' : 'ban';

      var bansSet = {};
      c.asList(veto.bans).forEach(function (m) { var v = String(m || '').trim(); if (v) bansSet[v.toLowerCase()] = true; });
      var picksSet = {};
      c.asList(veto.picks).forEach(function (m) { var v = String(m || '').trim(); if (v) picksSet[v.toLowerCase()] = true; });
      var selectedMap = String(veto.selected_map || '').trim();
      var pool = c.mapPool();
      var metaIndex = _mapMetaIndex(workflow);

      var side = c.mySide();
      var staff = c.bool(c.asObject(c.state.room.me).is_staff, false);
      var myTurn = staff || side === expectedSide;
      var actionLocked = c.waitingLocked() || c.state.requestBusy;
      var sequenceDone = step >= sequence.length;

      var expectedSideName = _participantName(c, expectedSide);
      var actionVerb = expectedAction === 'pick' ? 'picks' : 'bans';
      var actionCopy = expectedAction === 'pick' ? 'Pick' : 'Ban';

      // Timer block.
      var totalSeconds = c.toInt(veto.time_per_action_seconds, 30);
      var remaining = _secondsRemaining(veto.step_expires_at);
      var timerHTML = (!sequenceDone && remaining !== null) ? _renderTimer(remaining, totalSeconds) : '';

      // Turn strip — the dominant visual element.
      var turnStrip;
      if (sequenceDone) {
        turnStrip = '<div class="flex items-center gap-3 p-3 md:p-4 rounded-xl bg-black/40 border border-ac/30 reveal-pulse">' +
          '<i data-lucide="check-circle-2" class="w-5 h-5 md:w-6 md:h-6 text-ac"></i>' +
          '<div class="flex-1 min-w-0">' +
            '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Veto Complete</p>' +
            '<p class="text-base md:text-lg font-black text-white">' +
              (selectedMap ? c.esc(selectedMap) + ' locked' : 'Sequence finished') +
            '</p>' +
          '</div>' +
        '</div>';
      } else {
        turnStrip = '<div class="flex items-center gap-3 p-3 md:p-4 rounded-xl bg-black/40 border border-white/10">' +
          '<span class="side-indicator side-' + (expectedSide === 1 ? 'a' : 'b') + ' is-active">' +
            '<span class="dot"></span>' + c.esc(expectedSideName) +
          '</span>' +
          '<div class="flex-1 min-w-0">' +
            '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Step ' + (step + 1) + ' of ' + sequence.length + '</p>' +
            '<p class="text-base md:text-lg font-black text-white">' +
              c.esc(expectedSideName) + ' ' + actionVerb + ' a map' +
              (myTurn ? ' <span class="text-ac">— your move</span>' : '') +
            '</p>' +
          '</div>' +
          timerHTML +
        '</div>';
      }

      // Map cards.
      var cards = pool.map(function (mapName) {
        var clean = String(mapName || '').trim();
        if (!clean) return '';
        var meta = metaIndex[clean.toLowerCase()] || null;
        var isBanned = !!bansSet[clean.toLowerCase()];
        var isPicked = !!picksSet[clean.toLowerCase()] || (selectedMap && clean === selectedMap);
        var selectable = !isBanned && !isPicked && !sequenceDone && myTurn && !actionLocked;
        return _mapCard(c, clean, meta, isBanned, isPicked, selectable);
      }).join('');

      var historyHTML = _historyHTML(c, workflow);

      return '' +
        '<section class="glass-panel rounded-2xl p-4 md:p-6 border-t-4 border-ac">' +
          '<div class="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-4">' +
            '<div>' +
              '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Map Veto</p>' +
              '<h3 class="text-xl md:text-2xl font-black text-white">Battle for the Map</h3>' +
              '<p class="text-[11px] text-gray-400 mt-1">' + (sequenceDone ? 'Lobby unlocks with the selected map.' : 'Resolve bans and picks to lock the battleground.') + '</p>' +
            '</div>' +
            '<span class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Pool: ' + pool.length + ' map' + (pool.length === 1 ? '' : 's') + '</span>' +
          '</div>' +
          turnStrip +
          '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">' +
            (cards || '<p class="text-xs text-gray-400">No maps configured for this game. Contact tournament staff.</p>') +
          '</div>' +
          (historyHTML
            ? '<div class="mt-5">' +
                '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-2">Veto History</p>' +
                '<div class="flex flex-col gap-1.5">' + historyHTML + '</div>' +
              '</div>'
            : '') +
        '</section>';
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
      await c.sendWorkflowAction('veto_action', { item: mapName, expected_action: expectedAction });
      return true;
    },

    // 1-second countdown tick — updates DOM in place without re-rendering.
    onTick: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var veto = c.asObject(workflow.veto);
      var iso = veto.step_expires_at;
      if (!iso) return;
      var remaining = _secondsRemaining(iso);
      if (remaining === null) return;
      var total = c.toInt(veto.time_per_action_seconds, 30) || 30;
      var ring = document.querySelector('[data-veto-timer]');
      if (!ring) return;
      var fill = ring.querySelector('[data-timer-fill]');
      var label = ring.querySelector('[data-timer-label]');
      if (label) label.textContent = String(remaining);
      if (fill) {
        var circumference = 2 * Math.PI * 22;
        var ratio = Math.max(0, Math.min(1, remaining / total));
        fill.setAttribute('stroke-dashoffset', (circumference * (1 - ratio)).toFixed(2));
      }
      if (remaining <= 5) ring.classList.add('is-urgent');
      else ring.classList.remove('is-urgent');
    }
  });
})();
