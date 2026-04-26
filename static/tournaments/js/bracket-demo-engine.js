/**
 * DeltaCrown bracket renderer inspired by Bracket_demo.html.
 * Static/CSP-safe. Used by HUB and TOC renderers; public detail can also
 * delegate to it when the bracket API is available.
 */
(function () {
  'use strict';

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function safeId(prefix, value) {
    return prefix + '-' + String(value == null ? '' : value).replace(/[^A-Za-z0-9_-]/g, '-');
  }

  function isThirdPlaceMatch(match) {
    var label = String(match.round_name || match.round_label || match.title || '').toLowerCase();
    var type = String(match.bracket_type || match.node_type || '').toLowerCase();
    return !!(
      match.is_third_place_match ||
      match.third_place_match ||
      type === 'third-place' ||
      type === 'third_place' ||
      type === 'thirdplace' ||
      label.indexOf('third place') >= 0 ||
      label.indexOf('bronze') >= 0
    );
  }

  function roundName(totalTeamsInRound, fallback) {
    if (fallback && !/^round\s+\d+$/i.test(String(fallback))) return fallback;
    if (totalTeamsInRound === 2) return 'Grand Final';
    if (totalTeamsInRound === 4) return 'Semifinals';
    if (totalTeamsInRound === 8) return 'Quarterfinals';
    if (totalTeamsInRound === 16) return 'Round of 16';
    if (totalTeamsInRound === 32) return 'Round of 32';
    return fallback || 'Round';
  }

  function participantLogo(name, logo) {
    if (logo) {
      return '<img src="' + esc(logo) + '" alt="" class="w-5 h-5 rounded-md mr-2.5 shadow-sm border border-slate-600/50 object-cover">';
    }
    var initial = String(name || '?').trim().slice(0, 1).toUpperCase() || '?';
    return '<div class="w-5 h-5 rounded-md mr-2.5 bg-slate-800 border border-slate-700 flex items-center justify-center"><span class="text-[8px] text-slate-400 font-black">' + esc(initial) + '</span></div>';
  }

  function teamRow(participant, isWinner, isBottom, isDone) {
    var p = participant || {};
    var name = p.name || 'TBD';
    var hasParticipant = name !== 'TBD' || p.id;
    var score = p.score != null && (isDone || p.score) ? p.score : '-';
    return [
      '<div class="flex items-center px-3 py-2.5 ' + (isBottom ? '' : 'border-b border-slate-700/50') + (isWinner ? ' bg-cyan-500/5' : '') + '">',
      participantLogo(name, p.logo_url || p.logo || ''),
      '<span class="text-xs font-semibold truncate flex-1 ' + (hasParticipant ? (isWinner ? 'text-white' : 'text-slate-400') : 'text-slate-600 italic') + '">' + esc(name) + '</span>',
      '<span class="text-xs font-bold font-mono ml-3 ' + (isWinner ? 'text-cyan-400' : 'text-slate-500') + '">' + esc(score) + '</span>',
      '</div>',
    ].join('');
  }

  function stateBadge(match, isFinal, isThird) {
    var state = String(match.state || '').toLowerCase();
    if (state === 'live') return '<span class="text-[9px] text-red-400 animate-pulse font-bold tracking-wider">LIVE</span>';
    if (state === 'completed' || state === 'forfeit') return '<span class="text-[9px] text-cyan-500 font-bold tracking-wider">DONE</span>';
    if (isThird) return '<span class="text-[9px] text-amber-400 font-bold tracking-wider">PENDING</span>';
    return '<span class="text-[9px] text-slate-500 font-bold tracking-wider">' + esc((match.state_display || state || 'TBD').toUpperCase()) + '</span>';
  }

  function matchCard(match, options) {
    options = options || {};
    var id = safeId(options.prefix || 'match', match.render_id || match.id || match.match_number || Math.random());
    var next = match.next_id ? safeId(options.prefix || 'match', match.next_id) : '';
    var side = match.side || options.side || 'left';
    var p1 = match.participant1 || {};
    var p2 = match.participant2 || {};
    var isDone = ['completed', 'forfeit'].indexOf(String(match.state || '').toLowerCase()) >= 0;
    var p1Win = !!p1.is_winner;
    var p2Win = !!p2.is_winner;
    var isFinal = !!match.is_final;
    var isThird = isThirdPlaceMatch(match);
    var nodeAttr = match.node_json ? ' data-node="' + esc(match.node_json) + '"' : '';
    var header = isFinal
      ? '<span class="text-[9px] font-bold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded flex items-center gap-1"><i data-lucide="trophy" class="w-3 h-3"></i> GRAND FINAL</span>'
      : isThird
        ? '<span class="text-[9px] font-bold text-slate-200 bg-slate-700/50 px-2 py-0.5 rounded">THIRD PLACE MATCH</span>'
        : '<span class="text-[9px] font-semibold text-slate-500">MATCH ' + esc(match.match_number || match.render_label || '') + '</span>';
    return [
      '<div class="match-wrapper w-56 my-3 relative" id="' + id + '" data-next="' + next + '" data-side="' + esc(side) + '">',
      '<div class="match-card bracket-match-card bg-[#111827] border border-slate-700/60 rounded-xl flex flex-col overflow-hidden shadow-xl"' + nodeAttr + '>',
      '<div class="px-3 py-2 bg-[#151d2c] border-b border-slate-700/60 flex justify-between items-center">',
      header,
      stateBadge(match, isFinal, isThird),
      '</div>',
      teamRow(p1, p1Win, false, isDone),
      teamRow(p2, p2Win, true, isDone),
      '</div>',
      '</div>',
    ].join('');
  }

  function normalizeHub(data) {
    var rounds = (data.rounds || []).map(function (round) {
      return {
        round_number: Number(round.round_number || 0),
        round_name: round.round_name || round.round_label || '',
        matches: (round.matches || []).map(function (m, idx) {
          var out = Object.assign({}, m);
          out.round_name = round.round_name || round.round_label || '';
          out.render_id = 'h-' + (round.round_number || 0) + '-' + (m.match_number || idx + 1) + '-' + (m.id || idx);
          return out;
        }),
      };
    });
    return {
      format: data.format || '',
      format_display: data.format_display || '',
      total_matches: Number(data.total_matches || 0),
      total_rounds: Number(data.total_rounds || rounds.length || 0),
      rounds: rounds,
    };
  }

  function normalizeToc(data) {
    var nodeRounds = {};
    (data.nodes || []).forEach(function (node, idx) {
      var rn = Number(node.round_number || 0);
      if (!nodeRounds[rn]) nodeRounds[rn] = [];
      var m = node.match || {};
      var winnerId = node.winner_id || m.winner_id;
      var p1Id = node.participant1_id || m.participant1_id;
      var p2Id = node.participant2_id || m.participant2_id;
      var nodeJson = JSON.stringify(node);
      nodeRounds[rn].push({
        id: m.id || node.match_id || node.id,
        match_number: node.match_number || node.match_number_in_round || m.match_number || idx + 1,
        render_id: 't-' + rn + '-' + (node.match_number || node.match_number_in_round || idx + 1) + '-' + node.id,
        state: m.state || node.state || 'scheduled',
        state_display: m.state_display || '',
        bracket_type: node.bracket_type || '',
        is_third_place_match: isThirdPlaceMatch(node),
        node_json: nodeJson,
        participant1: {
          id: p1Id,
          name: node.participant1_name || m.participant1_name || 'TBD',
          score: m.participant1_score,
          is_winner: !!(winnerId && p1Id && winnerId === p1Id),
          logo_url: node.participant1_logo || '',
        },
        participant2: {
          id: p2Id,
          name: node.participant2_name || m.participant2_name || 'TBD',
          score: m.participant2_score,
          is_winner: !!(winnerId && p2Id && winnerId === p2Id),
          logo_url: node.participant2_logo || '',
        },
      });
    });
    var rounds = Object.keys(nodeRounds).sort(function (a, b) { return Number(a) - Number(b); }).map(function (rn) {
      var matches = nodeRounds[rn].sort(function (a, b) { return Number(a.match_number || 0) - Number(b.match_number || 0); });
      return {
        round_number: Number(rn),
        round_name: roundName(matches.length * 2, 'Round ' + rn),
        matches: matches,
      };
    });
    return {
      format: data.bracket && data.bracket.format || '',
      format_display: data.bracket && data.bracket.format || '',
      total_matches: data.bracket && data.bracket.total_matches || 0,
      total_rounds: data.bracket && data.bracket.total_rounds || rounds.length,
      rounds: rounds,
    };
  }

  function splitThirdPlace(rounds) {
    var third = [];
    var main = [];
    rounds.forEach(function (round) {
      var mainMatches = [];
      (round.matches || []).forEach(function (match) {
        if (isThirdPlaceMatch(match)) third.push(match);
        else mainMatches.push(match);
      });
      if (mainMatches.length) {
        main.push(Object.assign({}, round, { matches: mainMatches }));
      }
    });
    return { main: main, third: third };
  }

  function estimateTeams(rounds) {
    var first = rounds[0];
    return first ? Math.max(2, (first.matches || []).length * 2) : 0;
  }

  function assignStandardNext(rounds, prefix) {
    rounds.forEach(function (round, ri) {
      round.matches.forEach(function (match, mi) {
        match.render_id = match.render_id || (prefix + '-' + ri + '-' + mi);
        match.side = 'left';
        match.is_final = ri === rounds.length - 1;
        if (ri < rounds.length - 1) {
          var next = rounds[ri + 1].matches[Math.floor(mi / 2)];
          if (next) {
            next.render_id = next.render_id || (prefix + '-' + (ri + 1) + '-' + Math.floor(mi / 2));
            match.next_id = next.render_id;
          }
        }
      });
    });
  }

  function columnHtml(round, label, side, prefix) {
    return [
      '<div class="flex flex-col justify-center gap-2 relative min-w-[14rem]">',
      '<div class="absolute -top-8 ' + (side === 'right' ? 'right-0' : 'left-0') + ' text-[10px] font-bold text-slate-500 uppercase tracking-widest whitespace-nowrap">' + esc(label) + '</div>',
      (round.matches || []).map(function (match) { return matchCard(match, { prefix: prefix, side: side }); }).join(''),
      '</div>',
    ].join('');
  }

  function standardHtml(rounds, prefix) {
    assignStandardNext(rounds, prefix);
    return '<div class="dc-bracket-container relative flex items-center gap-12 lg:gap-20 mx-auto min-w-max">' +
      rounds.map(function (round) {
        return columnHtml(round, round.round_name || roundName((round.matches || []).length * 2), 'left', prefix);
      }).join('') +
      '</div>';
  }

  function splitHtml(rounds, prefix) {
    var finalRound = rounds[rounds.length - 1] || { matches: [] };
    var finalMatch = (finalRound.matches || [])[0] || null;
    var wingRounds = rounds.slice(0, -1);
    var left = [];
    var right = [];
    wingRounds.forEach(function (round, ri) {
      var half = Math.ceil((round.matches || []).length / 2);
      left.push(Object.assign({}, round, { matches: round.matches.slice(0, half) }));
      right.push(Object.assign({}, round, { matches: round.matches.slice(half) }));
      left[ri].matches.forEach(function (m, mi) {
        m.render_id = m.render_id || (prefix + '-l-' + ri + '-' + mi);
        m.side = 'left';
        var next = ri === wingRounds.length - 1 ? finalMatch : left[ri + 1] && left[ri + 1].matches[Math.floor(mi / 2)];
        if (next) {
          next.render_id = next.render_id || (ri === wingRounds.length - 1 ? prefix + '-final' : prefix + '-l-' + (ri + 1) + '-' + Math.floor(mi / 2));
          m.next_id = next.render_id;
        }
      });
      right[ri].matches.forEach(function (m, mi) {
        m.render_id = m.render_id || (prefix + '-r-' + ri + '-' + mi);
        m.side = 'right';
        var next = ri === wingRounds.length - 1 ? finalMatch : right[ri + 1] && right[ri + 1].matches[Math.floor(mi / 2)];
        if (next) {
          next.render_id = next.render_id || (ri === wingRounds.length - 1 ? prefix + '-final' : prefix + '-r-' + (ri + 1) + '-' + Math.floor(mi / 2));
          m.next_id = next.render_id;
        }
      });
    });
    if (finalMatch) {
      finalMatch.render_id = finalMatch.render_id || (prefix + '-final');
      finalMatch.is_final = true;
      finalMatch.side = 'center';
    }
    return [
      '<div class="dc-bracket-container relative flex items-center gap-12 lg:gap-20 mx-auto min-w-max">',
      '<div class="flex gap-12 lg:gap-20">',
      left.map(function (round) { return columnHtml(round, round.round_name || roundName((round.matches || []).length * 4), 'left', prefix); }).join(''),
      '</div>',
      '<div class="flex flex-col justify-center items-center relative z-20">',
      '<div class="absolute -top-8 text-[10px] font-bold text-amber-500/80 uppercase tracking-widest whitespace-nowrap">Grand Final</div>',
      '<div class="mb-6 w-12 h-12 rounded-full bg-gradient-to-tr from-amber-500 to-yellow-300 p-[1px] shadow-[0_0_30px_rgba(245,158,11,0.2)]"><div class="w-full h-full bg-[#05080f] rounded-full flex items-center justify-center"><i data-lucide="trophy" class="w-6 h-6 text-amber-400"></i></div></div>',
      finalMatch ? matchCard(finalMatch, { prefix: prefix, side: 'center' }) : '',
      '</div>',
      '<div class="flex flex-row-reverse gap-12 lg:gap-20">',
      right.map(function (round) { return columnHtml(round, round.round_name || roundName((round.matches || []).length * 4), 'right', prefix); }).join(''),
      '</div>',
      '</div>',
    ].join('');
  }

  function placementHtml(matches, prefix) {
    if (!matches.length) return '';
    matches.forEach(function (m, idx) {
      m.render_id = m.render_id || (prefix + '-third-' + idx);
      m.is_third_place_match = true;
      m.side = 'center';
    });
    return [
      '<section class="mt-8 rounded-2xl border border-slate-700/60 bg-[#0a0e17]/80 p-5">',
      '<div class="mb-4 flex items-center gap-3">',
      '<div class="w-8 h-8 rounded-lg bg-amber-400/10 border border-amber-400/20 flex items-center justify-center"><i data-lucide="medal" class="w-4 h-4 text-amber-300"></i></div>',
      '<div><h3 class="text-sm font-black uppercase tracking-widest text-white">Placement Match</h3><p class="text-[10px] text-slate-500">Third Place Match is separate from the championship path.</p></div>',
      '</div>',
      '<div class="flex flex-wrap gap-4">',
      matches.map(function (match) { return matchCard(match, { prefix: prefix, side: 'center' }); }).join(''),
      '</div>',
      '</section>',
    ].join('');
  }

  function renderBracket(root, data, options) {
    options = options || {};
    if (!root) return;
    var normalized = options.kind === 'toc' ? normalizeToc(data || {}) : normalizeHub(data || {});
    var split = splitThirdPlace(normalized.rounds || []);
    var rounds = split.main;
    if (!rounds.length) {
      root.innerHTML = '<div class="rounded-2xl border border-slate-800 bg-[#0a0e17] p-10 text-center text-sm text-slate-500">Bracket is not generated yet.</div>';
      return;
    }
    var fmt = String(normalized.format || '').toLowerCase();
    var hasDouble = fmt.indexOf('double') >= 0 || rounds.some(function (r) {
      return /lower|lb|grand final|gf/i.test(r.round_name || '');
    });
    var prefix = options.prefix || ('dc-bk-' + Math.floor(Math.random() * 100000));
    var teams = estimateTeams(rounds);
    var bracketHtml;
    if (!hasDouble && teams >= 16 && rounds.length >= 3) bracketHtml = splitHtml(rounds, prefix);
    else bracketHtml = standardHtml(rounds, prefix);
    root.innerHTML = [
      '<div class="dc-bracket-shell overflow-auto custom-scrollbar bg-[#05080f] rounded-2xl border border-slate-800 p-8">',
      '<div class="mb-8 sticky left-0 z-20">',
      '<h3 class="text-2xl font-black text-white tracking-tight">Championship Bracket</h3>',
      '<p class="mt-1 text-xs text-cyan-400 font-mono uppercase tracking-widest">' + esc(normalized.format_display || normalized.format || 'Single Elimination') + '</p>',
      '</div>',
      '<div class="w-full min-w-max p-2 flex items-center">',
      bracketHtml,
      '</div>',
      placementHtml(split.third, prefix),
      '</div>',
    ].join('');
    window.requestAnimationFrame(function () { drawConnectors(root); });
    if (window.lucide && typeof window.lucide.createIcons === 'function') window.lucide.createIcons();
  }

  function drawConnectors(root) {
    var containers = root.querySelectorAll('.dc-bracket-container');
    containers.forEach(function (container) {
      var old = container.querySelector('svg.bracket-connectors');
      if (old) old.remove();
      var rect = container.getBoundingClientRect();
      var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.classList.add('bracket-connectors');
      svg.setAttribute('width', rect.width);
      svg.setAttribute('height', rect.height);
      svg.style.width = rect.width + 'px';
      svg.style.height = rect.height + 'px';
      container.querySelectorAll('.match-wrapper').forEach(function (match) {
        var nextId = match.getAttribute('data-next');
        if (!nextId) return;
        var escapedNextId = window.CSS && CSS.escape ? CSS.escape(nextId) : nextId.replace(/([ #;?%&,.+*~':"!^$[\]()=>|/@])/g, '\\$1');
        var next = container.querySelector('#' + escapedNextId);
        if (!next) return;
        var side = match.getAttribute('data-side');
        var mr = match.querySelector('.match-card').getBoundingClientRect();
        var nr = next.querySelector('.match-card').getBoundingClientRect();
        var startX = side === 'right' ? mr.left - rect.left : mr.right - rect.left;
        var startY = mr.top + (mr.height / 2) - rect.top;
        var endX = side === 'right' ? nr.right - rect.left : nr.left - rect.left;
        var endY = nr.top + (nr.height / 2) - rect.top;
        var midX = startX + (endX - startX) / 2;
        var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M ' + startX + ' ' + startY + ' C ' + midX + ' ' + startY + ', ' + midX + ' ' + endY + ', ' + endX + ' ' + endY);
        path.setAttribute('stroke', '#334155');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke-linecap', 'round');
        svg.appendChild(path);
      });
      container.prepend(svg);
    });
  }

  window.DCBracketRenderer = {
    renderHub: function (root, data, options) {
      renderBracket(root, data, Object.assign({ kind: 'hub' }, options || {}));
    },
    renderToc: function (root, data, options) {
      renderBracket(root, data, Object.assign({ kind: 'toc' }, options || {}));
    },
    redraw: drawConnectors,
  };
})();
