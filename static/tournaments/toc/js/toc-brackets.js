/**
 * TOC Brackets Module — Rebuilt
 * Context-aware sub-navigation: Group Stage · Playoff Bracket · Qualifier Pipelines
 * Masonry grid groups, clean empty states, modern Tailwind UI.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);

  const stateColors = {
    scheduled: 'border-dc-border text-dc-text',
    live:      'border-dc-success text-dc-success',
    completed: 'border-dc-info text-dc-info',
    pending_result: 'border-dc-warning text-dc-warning',
    disputed:  'border-dc-danger text-dc-danger',
    forfeit:   'border-dc-text text-dc-text',
    cancelled: 'border-dc-danger/50 text-dc-danger/50',
  };

  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }

  /* --- State ------------------------------------------------ */
  let bracketData = null;
  let groupsData  = null;
  let activeSubTab = null;

  /* ================================================================
   *  SUB-NAVIGATION
   * ================================================================ */
  function switchSubTab(tab) {
    activeSubTab = tab;

    // Toggle pill active state
    document.querySelectorAll('.brackets-pill').forEach(btn => {
      const t = btn.dataset.subtab;
      if (t === tab) {
        btn.classList.remove('border-dc-border', 'text-dc-text');
        btn.classList.add('bg-theme/15', 'border-theme/40', 'text-white');
      } else {
        btn.classList.remove('bg-theme/15', 'border-theme/40', 'text-white');
        btn.classList.add('border-dc-border', 'text-dc-text');
      }
    });

    // Toggle sub-view visibility
    document.querySelectorAll('.brackets-subview').forEach(v => v.classList.add('hidden'));
    const target = document.querySelector('#sub-' + tab);
    if (target) target.classList.remove('hidden');
  }

  function initSubNav() {
    const fmt = window.TOC_CONFIG?.tournamentFormat || '';
    const nav = document.querySelector('#brackets-subnav');
    if (!nav) return;

    const groupsPill = nav.querySelector('[data-subtab="groups"]');

    // Format-aware visibility
    const hideGroups = ['single_elimination', 'double_elimination'].includes(fmt);
    if (groupsPill && hideGroups) groupsPill.classList.add('hidden');

    // Default active tab
    if (fmt === 'group_playoff') {
      switchSubTab('groups');
    } else if (hideGroups) {
      switchSubTab('bracket');
    } else {
      switchSubTab('groups');
    }
  }

  /* ================================================================
   *  DATA FETCH
   * ================================================================ */
  async function refresh() {
    try {
      const [bData, gData, pData] = await Promise.all([
        API.get('brackets/').catch(function() { return null; }),
        API.get('groups/').catch(function() { return null; }),
        API.get('pipelines/').catch(function() { return []; }),
      ]);
      bracketData = bData;
      groupsData  = gData;
      renderGroupsView(gData);
      renderBracketView(bData, gData);
      renderPipelinesView(pData);
    } catch (e) {
      console.error('[brackets] fetch error', e);
    }
  }

  /* ================================================================
   *  GROUP STAGE VIEW
   * ================================================================ */
  function renderGroupsView(data) {
    const container = document.querySelector('#groups-content');
    const meta      = document.querySelector('#groups-stage-meta');
    if (!container) return;

    // No group stage configured
    if (!data || !data.exists || !data.groups || !data.groups.length) {
      if (meta) meta.textContent = '';
      container.innerHTML = '<div class="flex flex-col items-center justify-center py-20 text-center">'
        + '<div class="w-16 h-16 rounded-2xl bg-dc-panel border border-dc-border flex items-center justify-center mb-5">'
        + '<i data-lucide="layout-grid" class="w-8 h-8 text-dc-text/30"></i></div>'
        + '<h3 class="text-lg font-bold text-white mb-2">No Group Stage Configured</h3>'
        + '<p class="text-sm text-dc-text max-w-sm mb-6">Set up groups to organize players into pools before the playoff bracket.</p>'
        + '<button onclick="TOC.brackets.openGroupConfig()" class="px-5 py-2.5 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">'
        + '<i data-lucide="plus" class="w-3.5 h-3.5 inline mr-1.5"></i>Configure Groups</button></div>';
      iconsRefresh();
      return;
    }

    var hasStandings = data.groups.some(function(g) { return g.standings && g.standings.length > 0; });
    var allFinalized = data.groups.every(function(g) { return g.is_finalized; });

    // Meta bar
    if (meta) {
      var stateLabel = data.stage && data.stage.state ? data.stage.state.toUpperCase() : 'SETUP';
      var stateClass = data.stage && data.stage.state === 'active' ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/5'
        : data.stage && data.stage.state === 'completed' ? 'border-sky-500/30 text-sky-400 bg-sky-500/5'
        : 'border-amber-500/30 text-amber-400 bg-amber-500/5';
      meta.innerHTML = data.groups.length + ' Groups &middot; ' + (data.stage && data.stage.format ? data.stage.format : 'Round Robin')
        + ' <span class="ml-3 px-2 py-0.5 rounded-full border text-[9px] font-mono font-bold ' + stateClass + '">' + stateLabel + '</span>';
    }

    // PRE-DRAW: Hero with Live Draw Director CTA
    if (!hasStandings) {
      var totalPlayers = data.groups.reduce(function(sum, g) { return sum + (g.member_count || (g.members ? g.members.length : 0) || 0); }, 0);
      var poolChips = data.groups.map(function(g) {
        return '<span class="px-3 py-1.5 bg-dc-bg border border-dc-border rounded-lg text-xs text-dc-textBright font-semibold">'
          + g.name + ' <span class="text-dc-text/50 font-mono ml-1">' + (g.member_count || (g.members ? g.members.length : 0) || 0) + '</span></span>';
      }).join('');
      container.innerHTML = '<div class="glass-box rounded-2xl border border-dc-border overflow-hidden">'
        + '<div class="px-8 py-14 text-center bg-gradient-to-b from-dc-panel/40 to-transparent">'
        + '<div class="w-20 h-20 rounded-2xl bg-theme/10 border border-theme/20 flex items-center justify-center mx-auto mb-6">'
        + '<i data-lucide="dice-5" class="w-10 h-10 text-theme/70"></i></div>'
        + '<h3 class="text-xl font-display font-black text-white mb-2">Groups Ready for Live Draw</h3>'
        + '<p class="text-sm text-dc-text max-w-lg mx-auto mb-8">'
        + (totalPlayers > 0 ? '<span class="text-white font-bold">' + totalPlayers + '</span> verified players' : data.groups.length + ' empty groups')
        + ' waiting to be drawn into <span class="text-white font-bold">' + data.groups.length + ' Groups</span></p>'
        + '<div class="flex items-center justify-center gap-4">'
        + '<a href="/tournaments/' + slug + '/draw/director/" target="_blank" class="inline-flex items-center gap-2 px-6 py-3 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-xl hover:opacity-90 transition-opacity shadow-lg shadow-theme/20">'
        + '<i data-lucide="radio" class="w-4 h-4"></i> Start Live Draw Director</a>'
        + '<a href="/tournaments/' + slug + '/draw/live/" target="_blank" class="inline-flex items-center gap-2 px-6 py-3 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-bold uppercase tracking-widest rounded-xl hover:border-dc-borderLight transition-colors">'
        + '<i data-lucide="eye" class="w-4 h-4"></i> Spectator Link</a></div>'
        + '<button onclick="TOC.brackets.showDrawGuide()" class="mt-4 text-[10px] text-dc-text/50 hover:text-white transition cursor-pointer flex items-center justify-center gap-1">'
        + '<i data-lucide="help-circle" class="w-3 h-3"></i> How does the Live Draw work?</button></div>'
        + (data.groups.length > 0 ? '<div class="border-t border-dc-border/30 px-8 py-5">'
        + '<p class="text-[10px] font-mono text-dc-text/50 uppercase tracking-widest mb-3">Group Pool Overview</p>'
        + '<div class="flex flex-wrap gap-2">' + poolChips + '</div></div>' : '')
        + '</div>';
      iconsRefresh();
      return;
    }

    // POST-DRAW: Masonry grid

    // Format Info Panel
    var formatInfoHtml = buildFormatInfoPanel(data);

    var cols = data.groups.length <= 4 ? 2 : data.groups.length <= 6 ? 3 : 4;
    var colClass = 'grid grid-cols-1 md:grid-cols-2'
      + (cols >= 3 ? ' lg:grid-cols-3' : '')
      + (cols >= 4 ? ' xl:grid-cols-4' : '')
      + ' gap-4';
    var cardsHtml = data.groups.map(function(g) { return renderGroupCard(g, data.stage); }).join('');
    var extra = '';

    if (!allFinalized && bracketData && !bracketData.exists) {
      extra += '<div class="mt-6 p-5 glass-box rounded-xl border border-dc-border text-center">'
        + '<p class="text-sm text-dc-text mb-3">All group matches must be completed before generating the playoff bracket.</p>'
        + '<div class="flex items-center justify-center gap-3 text-[10px] font-mono text-dc-text/50">'
        + '<span>' + data.groups.filter(function(g) { return g.is_finalized; }).length + '/' + data.groups.length + ' groups finalized</span></div></div>';
    }
    if (allFinalized && (!bracketData || !bracketData.exists)) {
      extra += '<div class="mt-6 p-6 glass-box rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03] text-center">'
        + '<i data-lucide="check-circle" class="w-6 h-6 text-emerald-400 mx-auto mb-3"></i>'
        + '<h4 class="text-sm font-bold text-white mb-1">All Groups Finalized</h4>'
        + '<p class="text-xs text-dc-text mb-4">Switch to the <strong class="text-white">Playoff Bracket</strong> tab to generate the bracket from group standings.</p>'
        + '<button onclick="TOC.brackets.switchSubTab(\'bracket\')" class="px-5 py-2 bg-theme/15 border border-theme/30 text-theme text-xs font-bold rounded-lg hover:bg-theme/20 transition-colors">Go to Playoff Bracket &rarr;</button></div>';
    }

    // Draw Audit Hash display (post-draw verification)
    var auditHtml = '';
    var drawAudit = data.stage && data.stage.draw_audit;
    if (drawAudit && drawAudit.seed_hash) {
      var hashDisplay = drawAudit.seed_hash.length > 20
        ? drawAudit.seed_hash.substring(0, 12) + '…' + drawAudit.seed_hash.slice(-8)
        : drawAudit.seed_hash;
      auditHtml = '<div class="mt-6 px-5 py-4 glass-box rounded-xl border border-dc-border/30 flex items-center justify-between">'
        + '<div class="flex items-center gap-3">'
        + '<i data-lucide="shield-check" class="w-4 h-4 text-dc-text/40 flex-shrink-0"></i>'
        + '<div>'
        + '<span class="text-[9px] text-dc-text/50 uppercase tracking-widest font-mono">Draw Verification Hash</span>'
        + '<div class="font-mono text-[11px] text-dc-text/80 mt-0.5 select-all cursor-text" title="' + drawAudit.seed_hash + '">' + hashDisplay + '</div>'
        + '</div></div>'
        + '<div class="relative group">'
        + '<i data-lucide="info" class="w-3.5 h-3.5 text-dc-text/30 cursor-help"></i>'
        + '<div class="absolute bottom-full right-0 mb-2 w-64 p-3 bg-dc-bg border border-dc-border rounded-lg text-[10px] text-dc-text/70 leading-relaxed'
        + ' opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity z-50 shadow-xl">'
        + 'This cryptographic hash proves the draw was mathematically random and untampered. '
        + 'The SHA-256 seed was generated at draw time and cannot be reverse-engineered.'
        + (drawAudit.drawn_at ? '<div class="mt-1.5 text-dc-text/40 font-mono">Drawn: ' + new Date(drawAudit.drawn_at).toLocaleString() + '</div>' : '')
        + '</div></div></div>';
    }

    container.innerHTML = formatInfoHtml + '<div class="' + colClass + '">' + cardsHtml + '</div>' + auditHtml + extra;
    iconsRefresh();
  }

  function renderGroupCard(group, stage) {
    var advanceCount = group.advancement_count || (stage ? stage.advancement_count_per_group : 0) || 2;
    var standings = group.standings || [];

    var header = '<div class="flex items-center justify-between px-4 py-3 bg-dc-panel/30 border-b border-dc-border/50">'
      + '<div class="flex items-center gap-2.5">'
      + '<div class="w-2 h-2 rounded-full ' + (group.is_finalized ? 'bg-emerald-400' : 'bg-amber-400') + '"></div>'
      + '<h4 class="text-sm font-bold text-white tracking-wide">' + group.name + '</h4></div>'
      + '<span class="text-[9px] font-mono text-dc-text">' + standings.length + ' players'
      + (group.is_finalized ? ' &middot; <span class="text-emerald-400 font-bold">Final</span>' : '') + '</span></div>';

    var body = '';
    if (standings.length) {
      var rows = standings.map(function(s, idx) {
        var inAdv = idx < advanceCount && !s.is_eliminated;
        var isElim = s.is_eliminated;
        return '<tr class="border-b border-dc-border/10 hover:bg-white/[0.015] transition-colors ' + (isElim ? 'opacity-35' : '') + '">'
          + '<td class="py-2 px-3"><div class="flex items-center gap-1.5">'
          + '<div class="w-0.5 h-4 rounded-full ' + (inAdv ? 'bg-amber-400' : 'bg-transparent') + '"></div>'
          + '<span class="font-mono font-bold text-dc-text/70">' + (s.rank || idx + 1) + '</span></div></td>'
          + '<td class="py-2 px-3 text-white/90 font-medium truncate max-w-[120px]">' + (s.team_name || s.player_name || s.user_id || '\u2014') + '</td>'
          + '<td class="py-2 px-1 text-center font-mono text-white/70">' + (s.wins != null ? s.wins : (s.matches_won != null ? s.matches_won : 0)) + '</td>'
          + '<td class="py-2 px-1 text-center font-mono text-white/40">' + (s.draws != null ? s.draws : (s.matches_drawn != null ? s.matches_drawn : 0)) + '</td>'
          + '<td class="py-2 px-1 text-center font-mono text-white/40">' + (s.losses != null ? s.losses : (s.matches_lost != null ? s.matches_lost : 0)) + '</td>'
          + '<td class="py-2 px-1 text-center font-mono font-black ' + (inAdv ? 'text-white' : 'text-white/70') + '">' + (s.points != null ? s.points : 0) + '</td></tr>';
      }).join('');
      body = '<table class="w-full text-[10px]"><thead><tr class="text-dc-text/70 border-b border-dc-border/20 bg-dc-panel/10">'
        + '<th class="text-left py-2 px-3 w-8">#</th><th class="text-left py-2 px-3">Player</th>'
        + '<th class="text-center py-2 px-1 w-6">W</th><th class="text-center py-2 px-1 w-6">D</th>'
        + '<th class="text-center py-2 px-1 w-6">L</th><th class="text-center py-2 px-1 w-8 font-black">Pts</th>'
        + '</tr></thead><tbody>' + rows + '</tbody></table>';
      if (advanceCount > 0) {
        body += '<div class="px-3 py-2 border-t border-dc-border/10">'
          + '<span class="text-[9px] text-dc-text/40 flex items-center gap-1">'
          + '<span class="inline-block w-2 h-2 rounded-full bg-amber-400/50"></span>Top ' + advanceCount + ' advance</span></div>';
      }
    } else {
      body = '<div class="py-8 text-center text-dc-text/30 text-[10px]">No standings yet</div>';
    }

    return '<div class="glass-box rounded-xl overflow-hidden border border-dc-border hover:border-dc-borderLight transition-colors">'
      + header + body + '</div>';
  }

  /* ================================================================
   *  PLAYOFF BRACKET VIEW
   * ================================================================ */
  function renderBracketView(data, gData) {
    var container = document.querySelector('#bracket-content');
    var infoBar   = document.querySelector('#bracket-info-bar');
    var seedEditor = document.querySelector('#seeding-editor');
    if (!container) return;

    var fmt = window.TOC_CONFIG ? window.TOC_CONFIG.tournamentFormat : '';
    var isGroupPlayoff = fmt === 'group_playoff';

    // No bracket yet
    if (!data || !data.exists || !data.bracket) {
      if (infoBar) infoBar.classList.add('hidden');
      if (seedEditor) seedEditor.classList.add('hidden');

      var groupsFinalized = gData && gData.groups && gData.groups.every(function(g) { return g.is_finalized; });
      var hasGroups = gData && gData.exists && gData.groups && gData.groups.length > 0;

      if (isGroupPlayoff && hasGroups && !groupsFinalized) {
        var advPerGroup = (gData.stage ? gData.stage.advancement_count_per_group : 0) || 2;
        var totalAdv = (gData.groups ? gData.groups.length : 0) * advPerGroup;
        var seedPairs = buildGroupToKnockoutSeeding(gData.groups, advPerGroup);
        var pairsHtml = seedPairs.length > 0 ? '<div class="max-w-md w-full"><p class="text-[9px] font-mono text-dc-text/40 uppercase tracking-widest mb-3">Projected Seeding (Cross-Match)</p><div class="grid grid-cols-2 gap-2">'
          + seedPairs.map(function(p) {
            return '<div class="flex items-center justify-between bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-xs">'
              + '<span class="text-white/80 font-semibold">' + p.p1Label + '</span>'
              + '<span class="text-dc-text/30 text-[9px] mx-1">vs</span>'
              + '<span class="text-white/80 font-semibold">' + p.p2Label + '</span></div>';
          }).join('') + '</div></div>' : '';

        container.innerHTML = '<div class="flex flex-col items-center justify-center py-16 text-center">'
          + '<div class="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-5">'
          + '<i data-lucide="clock" class="w-8 h-8 text-amber-400/60"></i></div>'
          + '<h3 class="text-lg font-bold text-white mb-2">Playoff Bracket Pending</h3>'
          + '<p class="text-sm text-dc-text max-w-md mb-6">Complete the Group Stage to seed the top <span class="text-white font-bold">' + totalAdv + '</span> players into the playoff bracket.</p>'
          + pairsHtml
          + '<button disabled class="mt-6 px-6 py-2.5 bg-dc-panel border border-dc-border text-dc-text text-xs font-bold uppercase tracking-widest rounded-lg opacity-50 cursor-not-allowed">'
          + '<i data-lucide="trophy" class="w-3.5 h-3.5 inline mr-1.5"></i>Generate Playoffs</button></div>';
      } else if (isGroupPlayoff && hasGroups && groupsFinalized) {
        container.innerHTML = '<div class="flex flex-col items-center justify-center py-16 text-center">'
          + '<div class="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-5">'
          + '<i data-lucide="zap" class="w-8 h-8 text-emerald-400/60"></i></div>'
          + '<h3 class="text-lg font-bold text-white mb-2">Group Stage Complete</h3>'
          + '<p class="text-sm text-dc-text max-w-md mb-6">All groups finalized. Generate the playoff bracket from group standings.</p>'
          + '<button onclick="TOC.brackets.generatePlayoffs()" class="px-6 py-3 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-xl hover:opacity-90 transition-opacity shadow-lg shadow-theme/20">'
          + '<i data-lucide="trophy" class="w-4 h-4 inline mr-2"></i>Generate Playoffs</button></div>';
      } else {
        container.innerHTML = '<div class="flex flex-col items-center justify-center py-16 text-center">'
          + '<div class="w-16 h-16 rounded-2xl bg-dc-panel border border-dc-border flex items-center justify-center mb-5">'
          + '<i data-lucide="git-branch" class="w-8 h-8 text-dc-text/20"></i></div>'
          + '<h3 class="text-lg font-bold text-white mb-2">No Bracket Generated</h3>'
          + '<p class="text-sm text-dc-text max-w-sm mb-6">Click <strong class="text-white">Generate</strong> above to create the bracket from current registrations.</p></div>';
      }
      iconsRefresh();
      return;
    }

    // Bracket exists
    var b = data.bracket;
    if (infoBar) {
      infoBar.classList.remove('hidden');
      var fmtEl = document.querySelector('#bracket-format');
      var rndEl = document.querySelector('#bracket-rounds');
      var matchEl = document.querySelector('#bracket-matches');
      var seedEl = document.querySelector('#bracket-seeding');
      var statEl = document.querySelector('#bracket-status');
      if (fmtEl)   fmtEl.textContent   = (b.format || '').replace(/[-_]/g, ' ');
      if (rndEl)   rndEl.textContent   = b.total_rounds || '\u2014';
      if (matchEl) matchEl.textContent = b.total_matches || '\u2014';
      if (seedEl)  seedEl.textContent  = (b.seeding_method || '').replace(/[-_]/g, ' ');
      if (statEl) {
        statEl.textContent = b.is_finalized ? 'Published' : 'Draft';
        statEl.className = b.is_finalized ? 'font-bold text-emerald-400' : 'font-bold text-amber-400';
      }
    }

    var nodes = data.nodes || [];
    if (!nodes.length) {
      container.innerHTML = '<p class="text-dc-text text-center py-12">Bracket generated but no nodes found.</p>';
      return;
    }

    var hasLosers = nodes.some(function(n) { return n.bracket_type === 'losers'; });
    if (hasLosers) {
      var winnersNodes = nodes.filter(function(n) { return n.bracket_type !== 'losers'; });
      var losersNodes  = nodes.filter(function(n) { return n.bracket_type === 'losers'; });
      container.innerHTML = '<div class="glass-box rounded-xl overflow-hidden">'
        + '<div class="p-4 border-b border-dc-border/30">'
        + '<div class="flex items-center gap-2 mb-3"><div class="w-2.5 h-2.5 rounded-full bg-emerald-400"></div>'
        + '<h3 class="text-xs font-bold text-white uppercase tracking-widest">Winners Bracket</h3></div>'
        + '<div class="overflow-x-auto">' + buildBracketGrid(winnersNodes, 'winners') + '</div></div>'
        + '<div class="p-4"><div class="flex items-center gap-2 mb-3">'
        + '<div class="w-2.5 h-2.5 rounded-full bg-red-400"></div>'
        + '<h3 class="text-xs font-bold text-white uppercase tracking-widest">Losers Bracket</h3></div>'
        + '<div class="overflow-x-auto">' + buildBracketGrid(losersNodes, 'losers') + '</div></div></div>';

      requestAnimationFrame(function() {
        drawBracketConnectors('bracket-grid-winners');
        drawBracketConnectors('bracket-grid-losers');
      });
    } else {
      container.innerHTML = '<div class="glass-box rounded-xl overflow-hidden">'
        + '<div class="p-4 overflow-x-auto">' + buildBracketGrid(nodes, 'main') + '</div></div>';
      requestAnimationFrame(function() { drawBracketConnectors('bracket-grid-main'); });
    }

    // Seeding editor
    if (seedEditor && !b.is_finalized && nodes.length) {
      seedEditor.classList.remove('hidden');
      renderSeedList(nodes);
    } else if (seedEditor) {
      seedEditor.classList.add('hidden');
    }
    iconsRefresh();
  }

  /* --- Bracket grid builder ---------------------------------- */
  function buildBracketGrid(nodes, gridId) {
    var rounds = {};
    nodes.forEach(function(n) {
      var rn = n.round_number || 0;
      if (!rounds[rn]) rounds[rn] = [];
      rounds[rn].push(n);
    });

    var sortedRounds = Object.keys(rounds).sort(function(a, b) { return a - b; });
    var totalRounds = sortedRounds.length;

    sortedRounds.forEach(function(rn) {
      rounds[rn].sort(function(a, b) { return (a.match_number_in_round || a.position || 0) - (b.match_number_in_round || b.position || 0); });
    });

    return '<div class="bracket-tree-wrap flex gap-0 min-w-max py-4 px-2" id="bracket-grid-' + gridId + '">'
      + sortedRounds.map(function(rn, idx) {
          var roundNodes = rounds[rn];
          var roundLabel = idx === totalRounds - 1 && totalRounds > 1 ? 'Final'
            : idx === totalRounds - 2 && totalRounds > 2 ? 'Semi-Finals'
            : 'Round ' + parseInt(rn);
          return '<div class="bracket-round" data-round="' + rn + '">'
            + '<div class="text-[9px] font-bold text-dc-text/50 uppercase tracking-widest text-center mb-3 pb-2 border-b border-dc-border/20 mx-2">' + roundLabel + '</div>'
            + roundNodes.map(function(n, mi) { return renderMatchCard(n, idx, mi); }).join('')
            + '</div>';
        }).join('')
      + '</div>';
  }

  function renderMatchCard(node, roundIdx, matchIdx) {
    var m = node.match;
    var state = m ? m.state || 'scheduled' : 'scheduled';
    var sc = stateColors[state] || stateColors.scheduled;
    var p1Win = node.winner_id && node.winner_id === node.participant1_id;
    var p2Win = node.winner_id && node.winner_id === node.participant2_id;
    var isBye = node.is_bye;
    var nodeId = node.id || (roundIdx + '-' + matchIdx);
    var nodeJson = JSON.stringify(node).replace(/"/g, '&quot;');

    return '<div class="bracket-match-card bg-dc-bg border ' + sc + ' rounded-lg overflow-hidden hover:border-dc-borderLight mx-2 my-1 cursor-pointer transition-colors ' + (isBye ? 'bracket-bye-card opacity-40' : '') + '"'
      + ' data-node-id="' + nodeId + '" data-round="' + roundIdx + '" data-match="' + matchIdx + '"'
      + ' onclick="TOC.brackets.onMatchCardClick && TOC.brackets.onMatchCardClick(' + nodeJson + ')">'
      + '<div class="flex items-center justify-between px-3 py-2 border-b border-dc-border/30 ' + (p1Win ? 'bg-emerald-500/[0.06]' : '') + '">'
      + '<span class="text-xs ' + (p1Win ? 'text-white font-bold' : 'text-white/70') + ' truncate max-w-[140px]">' + (node.participant1_name || (isBye ? 'BYE' : 'TBD')) + '</span>'
      + '<span class="text-xs font-mono font-bold ' + (p1Win ? 'text-emerald-400' : 'text-dc-text/50') + '">' + (m && m.participant1_score != null ? m.participant1_score : '\u2014') + '</span></div>'
      + '<div class="flex items-center justify-between px-3 py-2 ' + (p2Win ? 'bg-emerald-500/[0.06]' : '') + '">'
      + '<span class="text-xs ' + (p2Win ? 'text-white font-bold' : 'text-white/70') + ' truncate max-w-[140px]">' + (node.participant2_name || 'TBD') + '</span>'
      + '<span class="text-xs font-mono font-bold ' + (p2Win ? 'text-emerald-400' : 'text-dc-text/50') + '">' + (m && m.participant2_score != null ? m.participant2_score : '\u2014') + '</span></div></div>';
  }

  /* --- SVG bracket connector lines --------------------------- */
  function drawBracketConnectors(gridId) {
    var grid = document.getElementById(gridId);
    if (!grid) return;

    var oldSvg = grid.querySelector('svg.bracket-connectors');
    if (oldSvg) oldSvg.remove();

    var roundCols = grid.querySelectorAll('.bracket-round');
    if (roundCols.length < 2) return;

    var gridRect = grid.getBoundingClientRect();
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('bracket-connectors');
    svg.setAttribute('width', gridRect.width);
    svg.setAttribute('height', gridRect.height);
    svg.style.width = gridRect.width + 'px';
    svg.style.height = gridRect.height + 'px';

    for (var ri = 0; ri < roundCols.length - 1; ri++) {
      var curCards  = roundCols[ri].querySelectorAll('.bracket-match-card');
      var nextCards = roundCols[ri + 1].querySelectorAll('.bracket-match-card');

      for (var ni = 0; ni < nextCards.length; ni++) {
        var topCard  = curCards[ni * 2];
        var botCard  = curCards[ni * 2 + 1];
        var destCard = nextCards[ni];
        if (!destCard) continue;

        var destRect = destCard.getBoundingClientRect();
        var destY = destRect.top + destRect.height / 2 - gridRect.top;
        var destX = destRect.left - gridRect.left;

        if (topCard) {
          var r = topCard.getBoundingClientRect();
          drawConnector(svg, r.right - gridRect.left, r.top + r.height / 2 - gridRect.top, destX, destY);
        }
        if (botCard) {
          var r2 = botCard.getBoundingClientRect();
          drawConnector(svg, r2.right - gridRect.left, r2.top + r2.height / 2 - gridRect.top, destX, destY);
        }
      }
    }
    grid.prepend(svg);
  }

  function drawConnector(svg, x1, y1, x2, y2) {
    var midX = x1 + (x2 - x1) / 2;
    var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M ' + x1 + ' ' + y1 + ' H ' + midX + ' V ' + y2 + ' H ' + x2);
    svg.appendChild(path);
  }

  /* --- Seeding editor ---------------------------------------- */
  function renderSeedList(nodes) {
    var container = document.querySelector('#seed-list');
    if (!container) return;

    var minRound = nodes.reduce(function(min, n) { return Math.min(min, n.round_number); }, 999);
    var round1 = nodes.filter(function(n) { return n.round_number === 1 || n.round_number === minRound; });
    var participants = [];
    var seen = {};
    round1.forEach(function(n) {
      if (n.participant1_id && !seen[n.participant1_id]) {
        seen[n.participant1_id] = true;
        participants.push({ id: n.participant1_id, name: n.participant1_name });
      }
      if (n.participant2_id && !seen[n.participant2_id]) {
        seen[n.participant2_id] = true;
        participants.push({ id: n.participant2_id, name: n.participant2_name });
      }
    });

    container.innerHTML = participants.map(function(p, i) {
      return '<div class="flex items-center gap-3 bg-dc-bg border border-dc-border rounded-lg px-3 py-2 hover:border-dc-borderLight transition-colors cursor-move" data-reg-id="' + p.id + '" draggable="true">'
        + '<span class="w-6 h-6 rounded bg-dc-panel border border-dc-border flex items-center justify-center text-[10px] font-mono font-bold text-theme">' + (i + 1) + '</span>'
        + '<span class="text-xs text-white/80 font-semibold flex-1">' + (p.name || 'Unknown') + '</span>'
        + '<i data-lucide="grip-vertical" class="w-3 h-3 text-dc-text/20"></i></div>';
    }).join('');

    // Drag-and-drop
    var dragEl = null;
    container.querySelectorAll('[draggable]').forEach(function(el) {
      el.addEventListener('dragstart', function() { dragEl = el; el.classList.add('opacity-50'); });
      el.addEventListener('dragend', function() { if (dragEl) dragEl.classList.remove('opacity-50'); dragEl = null; });
      el.addEventListener('dragover', function(e) { e.preventDefault(); });
      el.addEventListener('drop', function(e) {
        e.preventDefault();
        if (dragEl && dragEl !== el) {
          var parent = el.parentNode;
          var children = Array.from(parent.children);
          var fromIdx = children.indexOf(dragEl);
          var toIdx = children.indexOf(el);
          if (fromIdx < toIdx) el.after(dragEl);
          else el.before(dragEl);
          parent.querySelectorAll('[data-reg-id]').forEach(function(row, i) {
            var badge = row.querySelector('span');
            if (badge) badge.textContent = i + 1;
          });
        }
      });
    });
    iconsRefresh();
  }

  async function saveSeedOrder() {
    var list = document.querySelector('#seed-list');
    if (!list) return;
    var seeds = Array.from(list.querySelectorAll('[data-reg-id]')).map(function(el, i) {
      return { registration_id: parseInt(el.dataset.regId), seed: i + 1 };
    });
    try {
      await API.put('brackets/seeds/', { seeds: seeds });
      toast('Seed order saved', 'success');
      refresh();
    } catch (e) {
      toast(e.message || 'Failed to save seeds', 'error');
    }
  }

  /* ================================================================
   *  BRACKET ACTIONS
   * ================================================================ */
  async function generate() {
    if (!confirm('Generate bracket from current registrations?')) return;
    try {
      await API.post('brackets/generate/');
      toast('Bracket generated', 'success');
      refresh();
    } catch (e) { toast(e.message || 'Generation failed', 'error'); }
  }

  async function resetBracket() {
    if (!confirm('RESET bracket? This deletes the current bracket and all matches. This cannot be undone.')) return;
    try {
      await API.post('brackets/reset/');
      toast('Bracket reset', 'info');
      refresh();
    } catch (e) { toast(e.message || 'Reset failed', 'error'); }
  }

  async function publish() {
    if (!confirm('Publish bracket? Participants will be able to see it.')) return;
    try {
      await API.post('brackets/publish/');
      toast('Bracket published', 'success');
      refresh();
    } catch (e) { toast(e.message || 'Publish failed', 'error'); }
  }

  /* ================================================================
   *  GROUP STAGE ACTIONS
   * ================================================================ */
  async function refreshGroups() {
    try {
      var data = await API.get('groups/');
      groupsData = data;
      renderGroupsView(data);
    } catch (e) { console.error('[brackets] groups error', e); }
  }

  async function recalcStandings() {
    try {
      toast('Recalculating standings...', 'info');
      await API.get('groups/standings/');
      await refreshGroups();
      toast('Standings updated', 'success');
    } catch (e) { toast('Failed to recalculate standings', 'error'); }
  }

  function openGroupConfig() {
    var html = '<div class="p-6 space-y-4">'
      + '<h3 class="font-display font-black text-lg text-white">Configure Groups</h3>'
      + '<div class="grid grid-cols-2 gap-3">'
      + '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Groups</label>'
      + '<input id="gc-num-groups" type="number" value="4" min="2" max="32" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none"></div>'
      + '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Group Size</label>'
      + '<input id="gc-group-size" type="number" value="4" min="2" max="16" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none"></div>'
      + '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Format</label>'
      + '<select id="gc-format" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">'
      + '<option value="round_robin">Round Robin</option><option value="double_round_robin">Double RR</option></select></div>'
      + '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Advance Per Group</label>'
      + '<input id="gc-advance" type="number" value="2" min="1" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none"></div>'
      + '</div>'
      + '<button onclick="TOC.brackets.confirmGroupConfig()" class="w-full py-2.5 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Save Configuration</button>'
      + '</div>';
    showOverlay('group-config-overlay', html);
  }

  async function confirmGroupConfig() {
    try {
      var numGroups = document.querySelector('#gc-num-groups');
      var groupSize = document.querySelector('#gc-group-size');
      var gcFormat = document.querySelector('#gc-format');
      var gcAdvance = document.querySelector('#gc-advance');
      await API.post('groups/configure/', {
        num_groups: parseInt(numGroups ? numGroups.value : 4) || 4,
        group_size: parseInt(groupSize ? groupSize.value : 4) || 4,
        format: gcFormat ? gcFormat.value : 'round_robin',
        advancement_count: parseInt(gcAdvance ? gcAdvance.value : 2) || 2,
      });
      toast('Groups configured', 'success');
      closeOverlay('group-config-overlay');
      refreshGroups();
    } catch (e) { toast(e.message || 'Config failed', 'error'); }
  }

  async function drawGroups() {
    if (!confirm('Execute group draw?')) return;
    try {
      await API.post('groups/draw/', { method: 'random' });
      toast('Groups drawn', 'success');
      refreshGroups();
    } catch (e) { toast(e.message || 'Draw failed', 'error'); }
  }

  async function generatePlayoffs() {
    if (!confirm('Generate playoff bracket from group standings?')) return;
    try {
      toast('Generating playoff bracket...', 'info');
      await API.post('brackets/generate/', { seeding_method: 'group_standings' });
      toast('Playoff bracket generated!', 'success');
      switchSubTab('bracket');
      refresh();
    } catch (e) { toast(e.message || 'Failed to generate playoffs', 'error'); }
  }

  function startLiveDraw() {
    window.open('/tournaments/' + slug + '/draw/director/', '_blank');
  }

  /* --- Group to Knockout seeding helper ---------------------- */
  function buildGroupToKnockoutSeeding(groups, advancePerGroup) {
    var pairs = [];
    for (var i = 0; i < groups.length; i += 2) {
      var gA = groups[i];
      var gB = groups[i + 1];
      if (!gB) break;
      var aLetter = (gA.name || '').replace('Group ', '');
      var bLetter = (gB.name || '').replace('Group ', '');
      pairs.push({ p1Label: aLetter + '1', p2Label: bLetter + '2' });
      if (advancePerGroup >= 2) {
        pairs.push({ p1Label: bLetter + '1', p2Label: aLetter + '2' });
      }
    }
    return pairs;
  }

  /* ================================================================
   *  PIPELINES VIEW
   * ================================================================ */
  function renderPipelinesView(list) {
    var container = document.querySelector('#pipelines-content');
    if (!container) return;

    if (!list || !list.length) {
      container.innerHTML = '<div class="flex flex-col items-center justify-center py-20 text-center">'
        + '<div class="w-16 h-16 rounded-2xl bg-dc-panel border border-dc-border flex items-center justify-center mb-5">'
        + '<i data-lucide="git-merge" class="w-8 h-8 text-dc-text/30"></i></div>'
        + '<h3 class="text-lg font-bold text-white mb-2">No Pipelines Configured</h3>'
        + '<p class="text-sm text-dc-text max-w-sm mb-6">Create qualifier pipelines to define multi-stage tournament paths.</p></div>';
      iconsRefresh();
      return;
    }

    container.innerHTML = list.map(function(p) {
      var stages = (p.stages || []).map(function(s, i) {
        return '<span class="text-[10px] bg-dc-bg border border-dc-border rounded-lg px-2.5 py-1 text-white/70 font-medium">' + s.name + '</span>'
          + (i < (p.stages || []).length - 1 ? '<i data-lucide="arrow-right" class="w-3 h-3 text-dc-text/20"></i>' : '');
      }).join('');
      return '<div class="glass-box rounded-xl p-5 border border-dc-border hover:border-dc-borderLight transition-colors group">'
        + '<div class="flex items-start justify-between mb-3"><div>'
        + '<h4 class="text-sm font-bold text-white">' + p.name + '</h4>'
        + '<span class="text-[9px] font-bold uppercase text-dc-text tracking-wider">' + p.status + '</span></div>'
        + '<button onclick="TOC.brackets.deletePipeline(\'' + p.id + '\')" class="opacity-0 group-hover:opacity-100 transition-opacity w-7 h-7 rounded-lg bg-red-500/10 text-red-400 flex items-center justify-center hover:bg-red-500/20">'
        + '<i data-lucide="trash-2" class="w-3.5 h-3.5"></i></button></div>'
        + (p.description ? '<p class="text-xs text-dc-text mb-3">' + p.description + '</p>' : '')
        + '<div class="flex items-center gap-1.5 flex-wrap">' + stages + '</div></div>';
    }).join('');
    iconsRefresh();
  }

  async function refreshPipelines() {
    try {
      var data = await API.get('pipelines/');
      renderPipelinesView(data);
    } catch (e) { console.error('[brackets] pipelines error', e); }
  }

  function openCreatePipeline() {
    var html = '<div class="p-6 space-y-4">'
      + '<h3 class="font-display font-black text-lg text-white">New Pipeline</h3>'
      + '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Name</label>'
      + '<input id="pl-name" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none" placeholder="e.g. Open Qualifier"></div>'
      + '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Description</label>'
      + '<textarea id="pl-desc" rows="2" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none" placeholder="Optional description..."></textarea></div>'
      + '<button onclick="TOC.brackets.confirmCreatePipeline()" class="w-full py-2.5 bg-purple-600 text-white text-xs font-black uppercase tracking-widest rounded-lg hover:bg-purple-500 transition-colors">Create Pipeline</button></div>';
    showOverlay('pipeline-create-overlay', html);
  }

  async function confirmCreatePipeline() {
    var nameEl = document.querySelector('#pl-name');
    var name = nameEl ? nameEl.value.trim() : '';
    if (!name) { toast('Name required', 'error'); return; }
    try {
      var descEl = document.querySelector('#pl-desc');
      await API.post('pipelines/', { name: name, description: descEl ? descEl.value.trim() : '' });
      toast('Pipeline created', 'success');
      closeOverlay('pipeline-create-overlay');
      refreshPipelines();
    } catch (e) { toast(e.message || 'Create failed', 'error'); }
  }

  async function deletePipeline(id) {
    if (!confirm('Delete this pipeline?')) return;
    try {
      await API.delete('pipelines/' + id + '/');
      toast('Pipeline deleted', 'success');
      refreshPipelines();
    } catch (e) { toast(e.message || 'Delete failed', 'error'); }
  }

  /* ================================================================
   *  OVERLAY HELPERS
   * ================================================================ */
  function showOverlay(id, innerHtml) {
    var existing = document.getElementById(id);
    if (existing) existing.remove();
    var modal = document.createElement('div');
    modal.id = id;
    modal.className = 'fixed inset-0 z-[110] flex items-center justify-center';
    modal.innerHTML = '<div class="absolute inset-0 bg-black/80 backdrop-blur-md" onclick="TOC.brackets.closeOverlay(\'' + id + '\')"></div>'
      + '<div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-md relative z-10 overflow-hidden">'
      + '<div class="h-1 w-full bg-theme"></div>' + innerHtml + '</div>';
    document.body.appendChild(modal);
  }

  function closeOverlay(id) {
    var el = document.getElementById(id);
    if (el) el.remove();
  }

  /* --- Match card interaction -------------------------------- */
  function onMatchCardClick(node) {
    if (!node || node.is_bye) return;
    var m = node.match;
    var state = m ? m.state || 'scheduled' : 'scheduled';
    var p1Name = node.participant1_name || 'TBD';
    var p2Name = node.participant2_name || 'TBD';
    var sc = stateColors[state] || 'border-dc-border text-dc-text';

    var html = '<div class="p-6 space-y-4">'
      + '<div class="flex items-center justify-between">'
      + '<h3 class="font-display font-black text-lg text-white">Match Details</h3>'
      + '<span class="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ' + sc + '">' + state + '</span></div>'
      + '<div class="bg-dc-bg rounded-xl border border-dc-border p-5">'
      + '<div class="flex items-center justify-between">'
      + '<div class="flex-1 text-center">'
      + '<p class="text-sm font-bold ' + (node.winner_id === node.participant1_id ? 'text-emerald-400' : 'text-white') + '">' + p1Name + '</p>'
      + '<p class="text-2xl font-mono font-black mt-1 ' + (node.winner_id === node.participant1_id ? 'text-emerald-400' : 'text-dc-text') + '">' + (m && m.participant1_score != null ? m.participant1_score : '\u2014') + '</p></div>'
      + '<div class="mx-4 text-dc-text/20 font-bold text-sm uppercase tracking-widest">vs</div>'
      + '<div class="flex-1 text-center">'
      + '<p class="text-sm font-bold ' + (node.winner_id === node.participant2_id ? 'text-emerald-400' : 'text-white') + '">' + p2Name + '</p>'
      + '<p class="text-2xl font-mono font-black mt-1 ' + (node.winner_id === node.participant2_id ? 'text-emerald-400' : 'text-dc-text') + '">' + (m && m.participant2_score != null ? m.participant2_score : '\u2014') + '</p></div></div></div>'
      + '<div class="grid grid-cols-2 gap-2 text-[10px]">'
      + '<div class="bg-dc-bg rounded-lg p-2.5 border border-dc-border/50"><span class="text-dc-text/60">Round</span>'
      + '<p class="text-white font-mono font-bold mt-0.5">' + (node.round_number || '\u2014') + '</p></div>'
      + '<div class="bg-dc-bg rounded-lg p-2.5 border border-dc-border/50"><span class="text-dc-text/60">Match</span>'
      + '<p class="text-white font-mono font-bold mt-0.5">#' + (node.match_number_in_round || node.position || '\u2014') + '</p></div>'
      + (m && m.scheduled_time ? '<div class="bg-dc-bg rounded-lg p-2.5 border border-dc-border/50 col-span-2"><span class="text-dc-text/60">Scheduled</span>'
        + '<p class="text-white font-mono font-bold mt-0.5">' + new Date(m.scheduled_time).toLocaleString() + '</p></div>' : '')
      + '</div>';

    if (m && state !== 'completed' && state !== 'forfeit') {
      html += '<div class="flex gap-2">';
      if (state === 'scheduled') {
        html += '<button onclick="TOC.matches && TOC.matches.markLive && TOC.matches.markLive(' + m.id + ')" class="flex-1 py-2.5 bg-emerald-500/15 text-emerald-400 text-xs font-bold rounded-lg hover:bg-emerald-500/25 transition-colors">Start Match</button>';
      }
      if (state === 'live') {
        html += '<button onclick="TOC.matches && TOC.matches.openScoreDrawer && TOC.matches.openScoreDrawer(' + m.id + ', \'' + p1Name.replace(/'/g, "\\'") + '\', \'' + p2Name.replace(/'/g, "\\'") + '\')" class="flex-1 py-2.5 bg-theme/15 text-theme text-xs font-bold rounded-lg hover:bg-theme/25 transition-colors">Enter Score</button>';
      }
      html += '</div>';
    }

    html += '</div>';
    showOverlay('bracket-match-detail', html);
  }

  /* --- Utility ----------------------------------------------- */
  function iconsRefresh() {
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* ================================================================
   *  FORMAT INFO PANEL
   * ================================================================ */
  function buildFormatInfoPanel(data) {
    if (!data || !data.stage) return '';
    var stage = data.stage;
    var format = stage.format || 'round_robin';
    var formatLabel = format === 'double_round_robin' ? 'Double Round-Robin'
      : format === 'round_robin' ? 'Round-Robin' : format.replace(/_/g, ' ');
    var advPerGroup = stage.advancement_count_per_group || 2;
    var config = stage.config || {};
    var pointsSys = config.points_system || {};
    var tiebreakers = config.tiebreaker_rules || ['head_to_head', 'goal_difference', 'goals_for'];
    var tiebreakerLabels = {
      head_to_head: 'Head-to-Head', goal_difference: 'Goal Difference',
      goals_for: 'Goals For', goals_against: 'Goals Against',
      wins: 'Wins', fair_play: 'Fair Play', drawing_of_lots: 'Drawing of Lots',
    };
    var tbStr = tiebreakers.map(function(t) { return tiebreakerLabels[t] || t.replace(/_/g, ' '); }).join(' \u2192 ');

    var items = [
      { icon: 'layout-grid', label: 'Format', value: formatLabel },
      { icon: 'trophy', label: 'Advancing', value: 'Top ' + advPerGroup + ' per group' },
    ];
    if (tiebreakers.length > 0) {
      items.push({ icon: 'scale', label: 'Tiebreakers', value: 'Points \u2192 ' + tbStr });
    }
    if (pointsSys.win != null) {
      items.push({ icon: 'hash', label: 'Points', value: 'W=' + (pointsSys.win || 3)
        + '  D=' + (pointsSys.draw != null ? pointsSys.draw : 1)
        + '  L=' + (pointsSys.loss != null ? pointsSys.loss : 0) });
    }

    var chips = items.map(function(it) {
      return '<div class="flex items-center gap-2 px-3 py-2 bg-dc-bg/50 border border-dc-border/30 rounded-lg">'
        + '<i data-lucide="' + it.icon + '" class="w-3 h-3 text-dc-text/40 flex-shrink-0"></i>'
        + '<span class="text-[10px] text-dc-text/60 font-bold uppercase tracking-widest">' + it.label + '</span>'
        + '<span class="text-[11px] text-white/80 font-medium">' + it.value + '</span></div>';
    }).join('');

    return '<div class="mb-5 p-4 glass-box rounded-xl border border-dc-border/30 bg-gradient-to-r from-dc-panel/20 to-transparent">'
      + '<div class="flex flex-wrap gap-2">' + chips + '</div></div>';
  }

  /* ================================================================
   *  DRAW GUIDE MODAL
   * ================================================================ */
  function showDrawGuide() {
    var html = '<div class="p-6 space-y-5 max-w-lg">'
      + '<div class="flex items-center gap-3 mb-2">'
      + '<div class="w-10 h-10 rounded-xl bg-theme/10 border border-theme/20 flex items-center justify-center">'
      + '<i data-lucide="help-circle" class="w-5 h-5 text-theme/70"></i></div>'
      + '<h3 class="font-display font-black text-lg text-white">How does the Live Draw work?</h3></div>'

      + '<div class="space-y-3 text-sm text-dc-text leading-relaxed">'

      + '<div class="flex gap-3">'
      + '<div class="w-6 h-6 rounded-full bg-theme/10 border border-theme/20 flex items-center justify-center flex-shrink-0 mt-0.5">'
      + '<span class="text-theme text-[10px] font-black">1</span></div>'
      + '<div><span class="text-white font-semibold">Real-Time WebSocket Broadcast</span>'
      + '<p class="text-dc-text/70 text-xs mt-1">The draw is broadcast live to all connected spectators via WebSocket. '
      + 'Every draw action is instantly visible to everyone watching.</p></div></div>'

      + '<div class="flex gap-3">'
      + '<div class="w-6 h-6 rounded-full bg-theme/10 border border-theme/20 flex items-center justify-center flex-shrink-0 mt-0.5">'
      + '<span class="text-theme text-[10px] font-black">2</span></div>'
      + '<div><span class="text-white font-semibold">CS:GO Lottery Spinner</span>'
      + '<p class="text-dc-text/70 text-xs mt-1">Each player is drawn with a cinematic CS:GO-style spinning reel animation. '
      + 'The spinner scrolls through all remaining players before landing on the selected one.</p></div></div>'

      + '<div class="flex gap-3">'
      + '<div class="w-6 h-6 rounded-full bg-theme/10 border border-theme/20 flex items-center justify-center flex-shrink-0 mt-0.5">'
      + '<span class="text-theme text-[10px] font-black">3</span></div>'
      + '<div><span class="text-white font-semibold">Spectator Link</span>'
      + '<p class="text-dc-text/70 text-xs mt-1">Share the spectator URL with players and fans. '
      + 'They\'ll see a polished waiting screen until the director starts the draw, then watch live.</p></div></div>'

      + '<div class="flex gap-3">'
      + '<div class="w-6 h-6 rounded-full bg-theme/10 border border-theme/20 flex items-center justify-center flex-shrink-0 mt-0.5">'
      + '<span class="text-theme text-[10px] font-black">4</span></div>'
      + '<div><span class="text-white font-semibold">Cryptographic Audit Hash</span>'
      + '<p class="text-dc-text/70 text-xs mt-1">When finalized, a SHA-256 hash of all group assignments is computed and stored. '
      + 'This creates an immutable, tamper-evident record proving the draw results were not altered.</p></div></div>'

      + '<div class="flex gap-3">'
      + '<div class="w-6 h-6 rounded-full bg-theme/10 border border-theme/20 flex items-center justify-center flex-shrink-0 mt-0.5">'
      + '<span class="text-theme text-[10px] font-black">5</span></div>'
      + '<div><span class="text-white font-semibold">Manual Pick Mode</span>'
      + '<p class="text-dc-text/70 text-xs mt-1">Directors can switch to Manual Pick mode to hand-select which player goes into which group, '
      + 'bypassing the spinner for seeded or invited players.</p></div></div>'

      + '</div></div>';
    showOverlay('draw-guide', html);
  }

  /* ================================================================
   *  INIT
   * ================================================================ */
  function init() {
    initSubNav();
    refresh();
  }

  window.TOC = window.TOC || {};
  window.TOC.brackets = {
    init: init, refresh: refresh, generate: generate, resetBracket: resetBracket, publish: publish,
    saveSeedOrder: saveSeedOrder, refreshGroups: refreshGroups, recalcStandings: recalcStandings,
    openGroupConfig: openGroupConfig, confirmGroupConfig: confirmGroupConfig, drawGroups: drawGroups,
    generatePlayoffs: generatePlayoffs, startLiveDraw: startLiveDraw, switchSubTab: switchSubTab,
    refreshPipelines: refreshPipelines, openCreatePipeline: openCreatePipeline, confirmCreatePipeline: confirmCreatePipeline,
    deletePipeline: deletePipeline, closeOverlay: closeOverlay, onMatchCardClick: onMatchCardClick,
    showDrawGuide: showDrawGuide,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail && e.detail.tab === 'brackets') init();
  });
})();
