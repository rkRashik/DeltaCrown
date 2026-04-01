/**
 * phase-matrix-results.js — Battle Royale Matrix Results (Phase 5)
 *
 * Archetype: Battle Royale (PUBG / Free Fire).
 * Displays a placement + kills scoring matrix instead of the standard
 * 1v1 score submission used by other archetypes.
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  window.MatchRoom.registerPhase('matrix_results', {
    label: function () { return 'Matrix Results'; },
    narrative: function () { return 'Submit placement and kill counts for Battle Royale scoring.'; },

    render: function (c) {
      var workflow = c.asObject(c.state.room.workflow);
      var mx = c.asObject(workflow.matrix_results);
      var submitted = c.bool(mx.submitted, false);
      var results = c.asList(mx.results);
      var staff = c.bool(c.asObject(c.state.room.me).is_staff, false);
      var locked = c.waitingLocked() || c.state.requestBusy || submitted;

      if (submitted && results.length) {
        var rows = results.map(function (r, idx) {
          var row = c.asObject(r);
          return '<tr class="border-b border-white/5">' +
            '<td class="px-3 py-2 text-sm text-white">#' + (idx + 1) + '</td>' +
            '<td class="px-3 py-2 text-sm text-white font-semibold">' + c.esc(String(row.team_name || row.participant_name || '—')) + '</td>' +
            '<td class="px-3 py-2 text-sm text-ac">' + c.toInt(row.placement, 0) + '</td>' +
            '<td class="px-3 py-2 text-sm text-amber-300">' + c.toInt(row.kills, 0) + '</td>' +
            '<td class="px-3 py-2 text-sm text-white font-bold">' + c.toInt(row.total_points, 0) + '</td></tr>';
        }).join('');

        return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
          '<div class="mb-4"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Battle Royale Pipeline</p>' +
          '<h3 class="text-xl md:text-2xl font-black text-white">Results Matrix</h3></div>' +
          '<div class="overflow-x-auto"><table class="w-full text-left">' +
          '<thead><tr class="text-[10px] uppercase tracking-wider text-gray-500">' +
          '<th class="px-3 py-2">#</th><th class="px-3 py-2">Team</th>' +
          '<th class="px-3 py-2">Place</th><th class="px-3 py-2">Kills</th>' +
          '<th class="px-3 py-2">Points</th></tr></thead><tbody>' + rows + '</tbody></table></div></section>';
      }

      // Submission form (staff only for BR)
      if (!staff) {
        return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
          '<div class="mb-4"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Battle Royale Pipeline</p>' +
          '<h3 class="text-xl md:text-2xl font-black text-white">Results Matrix</h3></div>' +
          '<p class="text-sm text-gray-400">Waiting for the organizer to submit placement & kill results…</p></section>';
      }

      // Staff form: placement + kills per team
      var side = c.mySide();
      return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
        '<div class="mb-4"><p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Battle Royale Pipeline</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Submit Results</h3></div>' +
        '<p class="text-sm text-gray-300 mb-4">Enter placement and kill counts. Final points are auto-calculated.</p>' +
        '<div class="grid grid-cols-1 gap-3 mb-4" id="mx-entries">' +
        '<div class="grid grid-cols-3 gap-2">' +
        '<div><label class="label text-[10px]">Team Name</label><input type="text" class="input" data-mx="team" placeholder="Team/Player"></div>' +
        '<div><label class="label text-[10px]">Placement</label><input type="number" class="input" data-mx="placement" min="1" placeholder="1"></div>' +
        '<div><label class="label text-[10px]">Kills</label><input type="number" class="input" data-mx="kills" min="0" placeholder="0"></div>' +
        '</div></div>' +
        '<div class="flex gap-2">' +
        '<button type="button" class="btn-secondary px-4 py-2 rounded-lg text-sm" data-action="mx-add-row">+ Add Row</button>' +
        '<button type="button" class="btn-primary px-5 py-2 rounded-lg font-bold text-sm" data-action="mx-submit"' +
        (locked ? ' disabled' : '') + '>Submit Matrix</button></div></section>';
    },

    onAction: async function (action, trigger, c) {
      if (action === 'mx-add-row') {
        var container = document.getElementById('mx-entries');
        if (!container) return true;
        var row = document.createElement('div');
        row.className = 'grid grid-cols-3 gap-2';
        row.innerHTML =
          '<div><input type="text" class="input" data-mx="team" placeholder="Team/Player"></div>' +
          '<div><input type="number" class="input" data-mx="placement" min="1" placeholder="1"></div>' +
          '<div><input type="number" class="input" data-mx="kills" min="0" placeholder="0"></div>';
        container.appendChild(row);
        return true;
      }

      if (action === 'mx-submit') {
        var entries = document.getElementById('mx-entries');
        if (!entries) return true;
        var rows = entries.querySelectorAll('.grid');
        var results = [];
        rows.forEach(function (r) {
          var team = (r.querySelector('[data-mx="team"]') || {}).value || '';
          var placement = parseInt((r.querySelector('[data-mx="placement"]') || {}).value || '0', 10);
          var kills = parseInt((r.querySelector('[data-mx="kills"]') || {}).value || '0', 10);
          if (team.trim() || placement > 0) {
            results.push({ team_name: team.trim(), placement: placement, kills: kills });
          }
        });
        if (!results.length) return true;
        await c.sendWorkflowAction('submit_matrix_results', { results: results });
        return true;
      }

      return false;
    }
  });
})();
