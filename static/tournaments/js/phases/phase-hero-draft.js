/**
 * phase-hero-draft.js — MOBA Hero Draft phase module (Phase 5 Archetype: MOBA)
 *
 * Sequence: Coin Toss → Hero Draft → Side Selection → Lobby Setup → Live → Results
 * Supports configurable ban/pick sequences from VetoConfiguration.
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  window.MatchRoom.registerPhase('hero_draft', {
    label: function () { return 'Hero Draft'; },
    narrative: function () { return 'Captains ban and pick heroes according to the draft sequence.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var draft = c.asObject(workflow.hero_draft);
      var sequence = c.asList(draft.sequence);
      var step = Math.max(0, c.toInt(draft.step, 0));
      var stepInfo = c.asObject(sequence[step]);
      var expectedSide = c.toInt(stepInfo.side, 0) || 1;
      var expectedAction = String(stepInfo.action || 'ban').toLowerCase() === 'pick' ? 'pick' : 'ban';
      var timer = c.toInt(draft.time_remaining, 0);

      var bans = {};
      c.asList(draft.bans).forEach(function (h) { var v = String(h || '').trim(); if (v) bans[v] = true; });
      var picks = {};
      c.asList(draft.picks).forEach(function (h) { var v = String(h || '').trim(); if (v) picks[v] = true; });
      var pool = c.asList(draft.hero_pool);
      if (!pool.length) pool = c.asList(workflow.hero_pool);

      var side = c.mySide();
      var staff = c.bool(c.asObject(c.state.room.me).is_staff, false);
      var myTurn = staff || side === expectedSide;
      var locked = c.waitingLocked() || c.state.requestBusy;

      var actionCopy = expectedAction === 'pick' ? 'Pick' : 'Ban';
      var statusCopy = step >= sequence.length
        ? 'Draft complete.'
        : 'Side ' + expectedSide + ' must ' + actionCopy.toLowerCase() + ' a hero.';

      var timerHtml = timer > 0
        ? '<span class="text-amber-300 font-mono text-lg">' + timer + 's</span>'
        : '';

      var cards = pool.map(function (heroName) {
        var h = String(heroName || '').trim();
        if (!h) return '';
        var isBanned = !!bans[h];
        var isPicked = !!picks[h];
        var selectable = !isBanned && !isPicked && step < sequence.length && myTurn && !locked;
        var tag = isPicked ? 'Picked' : (isBanned ? 'Banned' : 'Available');
        var cls = isPicked ? 'map-card picked' : (isBanned ? 'map-card banned' : 'map-card');
        var tagCls = isPicked ? 'text-ac' : (isBanned ? 'text-rose-300' : 'text-gray-400');
        var attr = selectable
          ? 'data-action="draft-hero" data-hero="' + encodeURIComponent(h) + '"'
          : 'disabled';
        return '<button type="button" class="' + cls + ' text-left" ' + attr + '>' +
          '<div class="flex items-center justify-between gap-2">' +
          '<span class="text-sm font-bold text-white">' + c.esc(h) + '</span>' +
          '<span class="text-[10px] uppercase tracking-widest ' + tagCls + '">' + c.esc(tag) + '</span></div></button>';
      }).join('');

      return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
        '<div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4"><div>' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">MOBA Pipeline</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Hero Draft</h3></div>' +
        '<div class="flex items-center gap-3">' + timerHtml +
        '<span class="text-xs ' + (myTurn ? 'text-ac' : 'text-rose-300') + ' font-bold uppercase tracking-wider">' + c.esc(statusCopy) + '</span></div></div>' +
        '<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">' +
        (cards || '<p class="text-xs text-gray-400">No heroes configured.</p>') + '</div></section>';
    },

    onAction: async function (action, trigger, c) {
      if (action !== 'draft-hero') return false;
      var raw = String(trigger.getAttribute('data-hero') || '');
      var hero = decodeURIComponent(raw);
      if (!hero) return true;
      var workflow = c.asObject(c.state.room.workflow);
      var draft = c.asObject(workflow.hero_draft);
      var sequence = c.asList(draft.sequence);
      var step = Math.max(0, c.toInt(draft.step, 0));
      var stepInfo = c.asObject(sequence[step]);
      var expectedAction = String(stepInfo.action || 'ban').toLowerCase() === 'pick' ? 'pick' : 'ban';
      await c.sendWorkflowAction('draft_hero', { hero: hero, action: expectedAction });
      return true;
    }
  });
})();
