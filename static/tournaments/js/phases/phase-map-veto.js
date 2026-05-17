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
      var stepsRemaining = sequenceDone ? 0 : (sequence.length - step);

      var expectedSideName = _participantName(c, expectedSide);
      var mySideName = side ? _participantName(c, side) : '';

      // Timer
      var totalSeconds = c.toInt(veto.time_per_action_seconds, 30);
      var remaining = _secondsRemaining(veto.step_expires_at);
      var timedOut = remaining !== null && remaining === 0;
      var timerHTML = (!sequenceDone && remaining !== null) ? _renderTimer(remaining, totalSeconds) : '';

      // ── Premium turn strip ────────────────────────────────────────────
      var turnStrip;
      if (sequenceDone) {
        var lockedMapImg = selectedMap && metaIndex[selectedMap.toLowerCase()] && metaIndex[selectedMap.toLowerCase()].image_url
          ? metaIndex[selectedMap.toLowerCase()].image_url : '';
        turnStrip =
          '<div class="veto-turn-strip veto-turn-done">' +
            '<div class="flex items-center gap-3">' +
              (lockedMapImg
                ? '<div class="w-10 h-10 rounded-lg overflow-hidden shrink-0 border border-ac/40"><img src="' + c.esc(lockedMapImg) + '" class="w-full h-full object-cover"></div>'
                : '<div class="w-10 h-10 rounded-full bg-ac/15 border border-ac/30 flex items-center justify-center shrink-0"><i data-lucide="check-circle-2" class="w-5 h-5 text-ac"></i></div>') +
              '<div class="min-w-0">' +
                '<p class="text-[10px] font-black uppercase tracking-widest text-ac/70">Map Locked</p>' +
                '<p class="text-base md:text-lg font-black text-white truncate">' + (selectedMap ? c.esc(selectedMap) : 'Sequence complete') + '</p>' +
              '</div>' +
            '</div>' +
            '<span class="shrink-0 px-3 py-1 rounded-full bg-ac/15 border border-ac/30 text-[10px] font-black text-ac uppercase tracking-widest">Veto Complete</span>' +
          '</div>';
      } else if (timedOut) {
        turnStrip =
          '<div class="veto-turn-strip veto-turn-pending">' +
            '<div class="flex items-center gap-2.5">' +
              '<span class="w-2 h-2 rounded-full bg-amber-300 animate-pulse shrink-0"></span>' +
              '<div class="min-w-0">' +
                '<p class="text-[10px] font-black uppercase tracking-widest text-amber-400/80">Timer Expired</p>' +
                '<p class="text-sm md:text-base font-black text-white">Waiting for system auto-pick…</p>' +
                '<p class="text-[10px] text-gray-500 mt-0.5">The server will auto-ban a random available map shortly.</p>' +
              '</div>' +
            '</div>' +
          '</div>';
      } else if (myTurn && !actionLocked) {
        var banExplain = expectedAction === 'ban'
          ? 'Select a map to remove it from the pool permanently.'
          : 'Select the map you want to play on.';
        turnStrip =
          '<div class="veto-turn-strip veto-turn-mine">' +
            '<div class="flex items-center gap-3">' +
              '<span class="side-indicator side-' + (expectedSide === 1 ? 'a' : 'b') + ' is-active shrink-0"><span class="dot"></span>' + c.esc(expectedSideName) + '</span>' +
              '<div class="min-w-0 flex-1">' +
                '<p class="text-[10px] font-black uppercase tracking-widest text-ac/80">Your Turn — Step ' + (step + 1) + ' of ' + sequence.length + '</p>' +
                '<p class="text-sm md:text-base font-black text-white">' + (expectedAction === 'ban' ? 'Ban a map' : 'Pick your map') + '</p>' +
                '<p class="text-[11px] text-gray-400 mt-0.5">' + c.esc(banExplain) + '</p>' +
              '</div>' +
            '</div>' +
            timerHTML +
          '</div>';
      } else {
        var waitExplain = myTurn ? 'Waiting for opponent to respond…' : c.esc(expectedSideName) + (expectedAction === 'ban' ? ' is banning a map.' : ' is picking the map.');
        turnStrip =
          '<div class="veto-turn-strip veto-turn-wait">' +
            '<div class="flex items-center gap-3">' +
              '<span class="side-indicator side-' + (expectedSide === 1 ? 'a' : 'b') + ' shrink-0"><span class="dot"></span>' + c.esc(expectedSideName) + '</span>' +
              '<div class="min-w-0 flex-1">' +
                '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Step ' + (step + 1) + ' of ' + sequence.length + ' · ' + stepsRemaining + ' step' + (stepsRemaining === 1 ? '' : 's') + ' left</p>' +
                '<p class="text-sm md:text-base font-black text-gray-300">' + (side === 0 || !side ? c.esc(expectedSideName) + (expectedAction === 'ban' ? ' is banning' : ' is picking') : waitExplain) + '</p>' +
              '</div>' +
            '</div>' +
            timerHTML +
          '</div>';
      }

      // ── Helper copy ───────────────────────────────────────────────────
      var helperNote = '';
      if (!sequenceDone && !timedOut) {
        var totalBans = sequence.filter(function(s) { return String(s.action||'ban').toLowerCase() === 'ban'; }).length;
        var totalPicks = sequence.filter(function(s) { return String(s.action||'ban').toLowerCase() === 'pick'; }).length;
        var doneBans = c.asList(veto.bans).length;
        var donePicks = c.asList(veto.picks).length;
        var parts = [];
        if (totalBans > doneBans) parts.push((totalBans - doneBans) + ' ban' + (totalBans - doneBans > 1 ? 's' : '') + ' remaining');
        if (totalPicks > donePicks) parts.push((totalPicks - donePicks) + ' pick' + (totalPicks - donePicks > 1 ? 's' : '') + ' remaining');
        if (parts.length) {
          helperNote = '<div class="flex items-center gap-2 mt-3 mb-1 text-[10px] text-gray-500">' +
            '<i data-lucide="info" class="w-3 h-3 shrink-0"></i>' +
            '<span>' + c.esc(parts.join(' · ')) +
            (veto.auto_random_on_timeout !== false ? ' · Auto-pick after ' + totalSeconds + 's timeout' : '') +
            '</span></div>';
        }
      }

      // Map cards.
      var cards = pool.map(function (mapName) {
        var clean = String(mapName || '').trim();
        if (!clean) return '';
        var meta = metaIndex[clean.toLowerCase()] || null;
        var isBanned = !!bansSet[clean.toLowerCase()];
        var isPicked = !!picksSet[clean.toLowerCase()] || (selectedMap && clean === selectedMap);
        var selectable = !isBanned && !isPicked && !sequenceDone && myTurn && !actionLocked && !timedOut;
        return _mapCard(c, clean, meta, isBanned, isPicked, selectable);
      }).join('');

      var historyHTML = _historyHTML(c, workflow);

      return '' +
        '<section class="glass-panel rounded-2xl p-4 md:p-6 border-t-4 border-ac">' +
          '<div class="flex items-start justify-between gap-3 mb-4">' +
            '<div>' +
              '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-0.5">Phase · Map Veto</p>' +
              '<h3 class="text-xl md:text-2xl font-black text-white leading-tight">Lock the Battleground</h3>' +
            '</div>' +
            '<div class="text-right shrink-0">' +
              '<p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">' + pool.length + ' map' + (pool.length !== 1 ? 's' : '') + ' in pool</p>' +
              (sequenceDone ? '' : '<p class="text-[10px] text-gray-600 mt-0.5">' + stepsRemaining + ' step' + (stepsRemaining !== 1 ? 's' : '') + ' left</p>') +
            '</div>' +
          '</div>' +
          turnStrip +
          helperNote +
          '<div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mt-4">' +
            (cards || '<div class="col-span-3 py-10 text-center text-xs text-gray-500 border border-dashed border-white/10 rounded-xl">No maps configured — contact tournament staff.</div>') +
          '</div>' +
          (historyHTML
            ? '<div class="mt-5 pt-4 border-t border-white/[0.06]">' +
                '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-2.5">Veto Log</p>' +
                '<div class="flex flex-col gap-1">' + historyHTML + '</div>' +
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
