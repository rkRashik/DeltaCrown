/**
 * TOC Brackets Module — Sprint 29 Rebuild
 * Context-aware sub-navigation: Group Stage · Playoff Bracket · Schedule · Qualifier Pipelines
 * State-aware button management, re-generation guards, reset groups, schedule view.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const stateColors = {
    scheduled:      'border-dc-border text-dc-text',
    live:           'border-dc-success text-dc-success',
    completed:      'border-dc-info text-dc-info',
    pending_result: 'border-dc-warning text-dc-warning',
    disputed:       'border-dc-danger text-dc-danger',
    forfeit:        'border-dc-text text-dc-text',
    cancelled:      'border-dc-danger/50 text-dc-danger/50',
  };

  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }

  /** Parse error body from API — returns human-readable message */
  function parseError(e) {
    if (e && e.body && e.body.error) return e.body.error;
    if (e && e.message) return e.message;
    return 'Unknown error';
  }

  /* --- State ------------------------------------------------ */
  let bracketData  = null;
  let groupsData   = null;
  let scheduleData = null;
  let activeSubTab = null;

  /* ================================================================
   *  SUB-NAVIGATION
   * ================================================================ */
  function switchSubTab(tab) {
    activeSubTab = tab;
    document.querySelectorAll('.brackets-pill').forEach(function(btn) {
      var t = btn.dataset.subtab;
      if (t === tab) {
        btn.classList.remove('border-dc-border', 'text-dc-text');
        btn.classList.add('bg-theme/15', 'border-theme/40', 'text-white');
      } else {
        btn.classList.remove('bg-theme/15', 'border-theme/40', 'text-white');
        btn.classList.add('border-dc-border', 'text-dc-text');
      }
    });
    document.querySelectorAll('.brackets-subview').forEach(function(v) { v.classList.add('hidden'); });
    var target = document.querySelector('#sub-' + tab);
    if (target) target.classList.remove('hidden');

    // Lazy-load schedule on first switch
    if (tab === 'schedule' && !scheduleData) refreshSchedule();
    if (tab === 'swiss') refreshSwiss();
  }

  function initSubNav() {
    var fmt = window.TOC_CONFIG?.tournamentFormat || '';
    var nav = document.querySelector('#brackets-subnav');
    if (!nav) return;

    var groupsPill = nav.querySelector('[data-subtab="groups"]');
    var swissPill  = nav.querySelector('[data-subtab="swiss"]');
    var hideGroups = ['single_elimination', 'double_elimination', 'swiss'].includes(fmt);
    if (groupsPill && hideGroups) groupsPill.classList.add('hidden');
    if (swissPill) {
      if (fmt === 'swiss') swissPill.classList.remove('hidden');
      else                 swissPill.classList.add('hidden');
    }

    if (fmt === 'swiss')        switchSubTab('swiss');
    else if (fmt === 'group_playoff') switchSubTab('groups');
    else if (hideGroups)        switchSubTab('bracket');
    else                        switchSubTab('groups');
  }

  /* ================================================================
   *  DATA FETCH
   * ================================================================ */
  async function refresh() {
    try {
      var fmt = window.TOC_CONFIG?.tournamentFormat || '';
      var isSwiss = fmt === 'swiss';
      var results = await Promise.all([
        API.get('brackets/').catch(function() { return null; }),
        isSwiss ? Promise.resolve(null) : API.get('groups/').catch(function() { return null; }),
        API.get('pipelines/').catch(function() { return []; }),
      ]);
      bracketData = results[0];
      groupsData  = results[1];
      renderGroupsView(groupsData);
      renderBracketView(bracketData, groupsData);
      renderPipelinesView(results[2]);
      updateBracketButtons();
      updateGroupButtons();
      if (isSwiss) refreshSwiss();
    } catch (e) {
      console.error('[brackets] fetch error', e);
    }
  }

  /* ================================================================
   *  TYPED CONFIRMATION MODAL — Professional Reset Safety
   * ================================================================ */
  function showTypedConfirmation(title, message, requiredWord) {
    return new Promise(function(resolve) {
      // Remove any existing confirmation overlay
      var existing = document.getElementById('toc-typed-confirm-overlay');
      if (existing) existing.remove();

      var overlay = document.createElement('div');
      overlay.id = 'toc-typed-confirm-overlay';
      overlay.className = 'fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm';
      overlay.innerHTML = ''
        + '<div class="bg-dc-panel border border-dc-border rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">'
        + '  <div class="px-6 pt-6 pb-4">'
        + '    <div class="flex items-center gap-3 mb-4">'
        + '      <div class="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">'
        + '        <i data-lucide="alert-triangle" class="w-5 h-5 text-red-400"></i>'
        + '      </div>'
        + '      <h3 class="text-lg font-bold text-white">' + title + '</h3>'
        + '    </div>'
        + '    <p class="text-sm text-dc-text mb-5">' + message + '</p>'
        + '    <div class="bg-red-500/5 border border-red-500/20 rounded-lg px-4 py-3 mb-4">'
        + '      <p class="text-xs text-red-400 mb-2">Type <strong class="text-white font-mono">' + requiredWord + '</strong> to confirm:</p>'
        + '      <input type="text" id="toc-confirm-input" autocomplete="off" spellcheck="false"'
        + '             class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-sm text-white font-mono'
        + '             focus:outline-none focus:border-red-500/50 placeholder-zinc-600"'
        + '             placeholder="Type ' + requiredWord + ' here...">'
        + '    </div>'
        + '  </div>'
        + '  <div class="px-6 py-4 border-t border-dc-border/50 flex items-center justify-end gap-3">'
        + '    <button id="toc-confirm-cancel" class="px-4 py-2 text-xs font-bold text-dc-text hover:text-white transition-colors rounded-lg border border-dc-border hover:border-dc-border/80">Cancel</button>'
        + '    <button id="toc-confirm-ok" disabled class="px-4 py-2 text-xs font-bold text-white bg-red-600/80 rounded-lg opacity-30 cursor-not-allowed transition-all">Confirm Reset</button>'
        + '  </div>'
        + '</div>';

      document.body.appendChild(overlay);
      if (typeof lucide !== 'undefined') lucide.createIcons();

      var input = document.getElementById('toc-confirm-input');
      var okBtn = document.getElementById('toc-confirm-ok');
      var cancelBtn = document.getElementById('toc-confirm-cancel');

      function cleanup(result) {
        overlay.remove();
        resolve(result);
      }

      input.addEventListener('input', function() {
        var match = input.value.trim() === requiredWord;
        okBtn.disabled = !match;
        if (match) {
          okBtn.classList.remove('opacity-30', 'cursor-not-allowed');
          okBtn.classList.add('hover:bg-red-600');
        } else {
          okBtn.classList.add('opacity-30', 'cursor-not-allowed');
          okBtn.classList.remove('hover:bg-red-600');
        }
      });

      input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !okBtn.disabled) cleanup(true);
        if (e.key === 'Escape') cleanup(false);
      });

      okBtn.addEventListener('click', function() { cleanup(true); });
      cancelBtn.addEventListener('click', function() { cleanup(false); });
      overlay.addEventListener('click', function(e) {
        if (e.target === overlay) cleanup(false);
      });

      setTimeout(function() { input.focus(); }, 100);
    });
  }

  /* ================================================================
   *  BUTTON STATE MANAGEMENT — Sprint 29 (HIDE instead of disable)
   * ================================================================ */
  function updateBracketButtons() {
    var genBtn  = document.querySelector('#btn-bracket-generate');
    var rstBtn  = document.querySelector('#btn-bracket-reset');
    var pubBtn  = document.querySelector('#btn-bracket-publish');

    var exists    = bracketData && bracketData.exists && bracketData.bracket;
    var published = exists && bracketData.bracket.is_finalized;

    if (genBtn) {
      // Hide Generate once bracket exists
      if (exists) {
        genBtn.classList.add('hidden');
      } else {
        genBtn.classList.remove('hidden');
        genBtn.disabled = false;
      }
    }
    if (rstBtn) {
      // Show Reset only when bracket exists
      if (!exists) {
        rstBtn.classList.add('hidden');
      } else {
        rstBtn.classList.remove('hidden');
        rstBtn.disabled = false;
      }
    }
    if (pubBtn) {
      // Hide Publish once already published; show only when unpublished bracket exists
      if (!exists || published) {
        pubBtn.classList.add('hidden');
      } else {
        pubBtn.classList.remove('hidden');
        pubBtn.disabled = false;
      }
    }
  }

  function updateGroupButtons() {
    var drawBtn   = document.querySelector('#btn-group-draw');
    var resetBtn  = document.querySelector('#btn-group-reset');
    var stageState = (groupsData && groupsData.stage) ? groupsData.stage.state : 'pending';
    var isDrawn   = stageState === 'active' || stageState === 'completed';

    if (drawBtn) {
      // Hide Draw once groups are drawn
      if (isDrawn) {
        drawBtn.classList.add('hidden');
      } else {
        drawBtn.classList.remove('hidden');
        drawBtn.disabled = false;
      }
    }
    if (resetBtn) {
      // Show Reset only when groups are drawn
      if (!isDrawn) {
        resetBtn.classList.add('hidden');
      } else {
        resetBtn.classList.remove('hidden');
      }
    }
  }

  /* ================================================================
   *  GROUP STAGE VIEW
   * ================================================================ */
  function renderGroupsView(data) {
    var container = document.querySelector('#groups-content');
    var meta      = document.querySelector('#groups-stage-meta');
    var cfg       = window.TOC_CONFIG || {};
    if (!container) return;

    if (!data || !data.exists || !data.groups || !data.groups.length) {
      if (meta) meta.textContent = '';
      container.innerHTML = '<div class="flex flex-col items-center justify-center py-20 text-center">'
        + '<div class="w-16 h-16 rounded-2xl bg-dc-panel border border-dc-border flex items-center justify-center mb-5">'
        + '<i data-lucide="layout-grid" class="w-8 h-8 text-dc-text/30"></i></div>'
        + '<h3 class="text-lg font-bold text-white mb-2">No Group Stage Configured</h3>'
        + '<p class="text-sm text-dc-text max-w-sm mb-6">Set up groups to organize ' + (cfg.isSolo ? 'players' : 'teams') + ' into pools for the ' + (cfg.format === 'group_playoff' ? 'group stage → playoff' : 'group stage') + ' format.</p>'
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
      meta.innerHTML = data.groups.length + ' Groups &middot; ' + (data.stage && data.stage.format ? data.stage.format.replace(/_/g, ' ') : 'Round Robin')
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
        + (totalPlayers > 0 ? '<span class="text-white font-bold">' + totalPlayers + '</span> participants' : data.groups.length + ' empty groups')
        + ' waiting to be drawn into <span class="text-white font-bold">' + data.groups.length + ' Groups</span></p>'
        + '<div class="flex items-center justify-center gap-4 flex-wrap">'
        + '<a href="/tournaments/' + slug + '/draw/director/" target="_blank" class="inline-flex items-center gap-2 px-6 py-3 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-xl hover:opacity-90 transition-opacity shadow-lg shadow-theme/20">'
        + '<i data-lucide="radio" class="w-4 h-4"></i> Start Live Draw</a>'
        + '<a href="/tournaments/' + slug + '/draw/live/" target="_blank" class="inline-flex items-center gap-2 px-6 py-3 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-bold uppercase tracking-widest rounded-xl hover:border-dc-borderLight transition-colors">'
        + '<i data-lucide="eye" class="w-4 h-4"></i> Spectator Link</a></div>'
        + '<button onclick="TOC.brackets.showDrawGuide()" class="mt-4 text-[10px] text-dc-text/50 hover:text-white transition cursor-pointer flex items-center justify-center gap-1 mx-auto">'
        + '<i data-lucide="help-circle" class="w-3 h-3"></i> How does the Live Draw work?</button></div>'
        + (data.groups.length > 0 ? '<div class="border-t border-dc-border/30 px-8 py-5">'
        + '<p class="text-[10px] font-mono text-dc-text/50 uppercase tracking-widest mb-3">Group Pool Overview</p>'
        + '<div class="flex flex-wrap gap-2">' + poolChips + '</div></div>' : '')
        + '</div>';
      iconsRefresh();
      return;
    }

    // POST-DRAW: Masonry grid
    var formatInfoHtml = buildFormatInfoPanel(data);
    var cols = data.groups.length <= 4 ? 2 : data.groups.length <= 6 ? 3 : 4;
    var colClass = 'grid grid-cols-1 md:grid-cols-2'
      + (cols >= 3 ? ' lg:grid-cols-3' : '')
      + (cols >= 4 ? ' xl:grid-cols-4' : '')
      + ' gap-4';
    var cardsHtml = data.groups.map(function(g) { return renderGroupCard(g, data.stage); }).join('');
    var extra = '';

    if (!allFinalized && bracketData && !bracketData.exists) {
      var finCount = data.groups.filter(function(g) { return g.is_finalized; }).length;
      extra += '<div class="mt-6 p-5 glass-box rounded-xl border border-dc-border text-center">'
        + '<p class="text-sm text-dc-text mb-3">All group matches must be completed before generating the playoff bracket.</p>'
        + '<div class="w-full bg-dc-bg rounded-full h-2 overflow-hidden mt-3"><div class="h-full bg-theme/60 rounded-full transition-all" style="width:' + Math.round(finCount / data.groups.length * 100) + '%"></div></div>'
        + '<div class="flex items-center justify-center gap-3 text-[10px] font-mono text-dc-text/50 mt-2">'
        + '<span>' + finCount + '/' + data.groups.length + ' groups finalized</span></div></div>';
    }
    if (allFinalized && (!bracketData || !bracketData.exists)) {
      extra += '<div class="mt-6 p-6 glass-box rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03] text-center">'
        + '<i data-lucide="check-circle" class="w-6 h-6 text-emerald-400 mx-auto mb-3"></i>'
        + '<h4 class="text-sm font-bold text-white mb-1">All Groups Finalized</h4>'
        + '<p class="text-xs text-dc-text mb-4">Switch to the <strong class="text-white">Playoff Bracket</strong> tab to generate the bracket from group standings.</p>'
        + '<button onclick="TOC.brackets.switchSubTab(\'bracket\')" class="px-5 py-2 bg-theme/15 border border-theme/30 text-theme text-xs font-bold rounded-lg hover:bg-theme/20 transition-colors">Go to Playoff Bracket &rarr;</button></div>';
    }

    // Draw Audit Hash
    var auditHtml = '';
    var drawAudit = data.stage && data.stage.draw_audit;
    if (drawAudit && drawAudit.seed_hash) {
      var hashDisplay = drawAudit.seed_hash.length > 20
        ? drawAudit.seed_hash.substring(0, 12) + '\u2026' + drawAudit.seed_hash.slice(-8)
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
    var pLabel = (window.TOC_CONFIG || {}).isSolo ? 'players' : 'teams';

    var header = '<div class="flex items-center justify-between px-4 py-3 bg-dc-panel/30 border-b border-dc-border/50">'
      + '<div class="flex items-center gap-2.5">'
      + '<div class="w-2 h-2 rounded-full ' + (group.is_finalized ? 'bg-emerald-400' : 'bg-amber-400') + '"></div>'
      + '<h4 class="text-sm font-bold text-white tracking-wide">' + group.name + '</h4></div>'
      + '<span class="text-[9px] font-mono text-dc-text">' + standings.length + ' ' + pLabel
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
          + '<td class="py-2 px-1 text-center font-mono text-white/70">' + (s.wins != null ? s.wins : 0) + '</td>'
          + '<td class="py-2 px-1 text-center font-mono text-white/40">' + (s.draws != null ? s.draws : 0) + '</td>'
          + '<td class="py-2 px-1 text-center font-mono text-white/40">' + (s.losses != null ? s.losses : 0) + '</td>'
          + '<td class="py-2 px-1 text-center font-mono text-dc-text/40">' + (s.goal_difference != null ? (s.goal_difference > 0 ? '+' : '') + s.goal_difference : '\u2014') + '</td>'
          + '<td class="py-2 px-1 text-center font-mono font-black ' + (inAdv ? 'text-white' : 'text-white/70') + '">' + (s.points != null ? s.points : 0) + '</td></tr>';
      }).join('');
      body = '<table class="w-full text-[10px]"><thead><tr class="text-dc-text/70 border-b border-dc-border/20 bg-dc-panel/10">'
        + '<th class="text-left py-2 px-3 w-8">#</th><th class="text-left py-2 px-3">Team</th>'
        + '<th class="text-center py-2 px-1 w-6">W</th><th class="text-center py-2 px-1 w-6">D</th>'
        + '<th class="text-center py-2 px-1 w-6">L</th><th class="text-center py-2 px-1 w-8">GD</th>'
        + '<th class="text-center py-2 px-1 w-8 font-black">Pts</th>'
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
    var container  = document.querySelector('#bracket-content');
    var infoBar    = document.querySelector('#bracket-info-bar');
    var seedEditor = document.querySelector('#seeding-editor');
    if (!container) return;

    var fmt = window.TOC_CONFIG ? window.TOC_CONFIG.tournamentFormat : '';
    var isGroupPlayoff = fmt === 'group_playoff';

    // No bracket yet
    if (!data || !data.exists || !data.bracket) {
      if (infoBar)    infoBar.classList.add('hidden');
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
          + '<p class="text-sm text-dc-text max-w-md mb-6">Complete the Group Stage to seed the top <span class="text-white font-bold">' + totalAdv + '</span> ' + ((window.TOC_CONFIG || {}).isSolo ? 'players' : 'teams') + ' into the playoff bracket.</p>'
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

    // Bracket exists — show info bar
    var b = data.bracket;
    if (infoBar) {
      infoBar.classList.remove('hidden');
      var fmtEl   = document.querySelector('#bracket-format');
      var rndEl   = document.querySelector('#bracket-rounds');
      var matchEl = document.querySelector('#bracket-matches');
      var seedEl  = document.querySelector('#bracket-seeding');
      var statEl  = document.querySelector('#bracket-status');
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
      container.innerHTML = '<p class="text-dc-text text-center py-12">Bracket generated but no match nodes found.</p>';
      return;
    }

    var hasLosers = nodes.some(function(n) { return n.bracket_type === 'losers'; });
    if (hasLosers) {
      var winnersNodes = nodes.filter(function(n) { return n.bracket_type !== 'losers'; });
      var losersNodes  = nodes.filter(function(n) { return n.bracket_type === 'losers'; });
      // Bridge annotation: LB Finals winner advances to GF slot 2
      var bridgeHtml = '<div class="flex items-center justify-center gap-3 py-3 px-5 border-y border-dc-border/20 bg-gradient-to-r from-transparent via-amber-500/[0.04] to-transparent">'
        + '<div class="h-px flex-1 bg-gradient-to-r from-transparent to-amber-500/30"></div>'
        + '<div class="flex items-center gap-2 text-[9px] font-bold text-amber-400/70 uppercase tracking-widest">'
        + '<i data-lucide="arrow-up" class="w-3 h-3"></i>'
        + 'LB Finals Winner → Grand Finals Slot 2'
        + '</div>'
        + '<div class="h-px flex-1 bg-gradient-to-l from-transparent to-amber-500/30"></div>'
        + '</div>';
      container.innerHTML = '<div class="glass-box rounded-xl overflow-hidden">'
        + '<div class="p-4 border-b border-dc-border/30">'
        + '<div class="flex items-center gap-2 mb-3"><div class="w-2.5 h-2.5 rounded-full bg-emerald-400"></div>'
        + '<h3 class="text-xs font-bold text-white uppercase tracking-widest">Winners Bracket</h3></div>'
        + '<div class="overflow-x-auto">' + buildBracketGrid(winnersNodes, 'winners') + '</div></div>'
        + bridgeHtml
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

    // Seeding editor (only if draft)
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
      rounds[rn].sort(function(a, b) { return (a.match_number || a.position || 0) - (b.match_number || b.position || 0); });
    });

    return '<div class="bracket-tree-wrap flex gap-0 min-w-max py-4 px-2" id="bracket-grid-' + gridId + '">'
      + sortedRounds.map(function(rn, idx) {
          var roundNodes = rounds[rn];
          var isGfRound  = roundNodes.some(function(n) { return n.is_gf; });
          var isGfrRound = roundNodes.some(function(n) { return n.is_gf_reset; });
          var isLbGrid  = gridId === 'losers';
          var roundLabel = isGfrRound ? '\u26A1 GF Reset'
            : isGfRound ? '\uD83D\uDC51 Grand Finals'
            : idx === totalRounds - 1 && totalRounds > 1 && !isLbGrid ? 'Final'
            : idx === totalRounds - 2 && totalRounds > 2 && !isLbGrid ? 'Semi-Finals'
            : isLbGrid ? 'LB Round ' + parseInt(rn)
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
    var nodeJsonAttr = JSON.stringify(node).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // Live pulse indicator
    var liveDot = state === 'live'
      ? '<span class="absolute top-1 right-1 flex h-2 w-2"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span></span>'
      : '';

    var defaultLogo = '/static/img/teams/default-logo.svg';
    var p1Logo = node.participant1_logo || '';
    var p2Logo = node.participant2_logo || '';
    var p1Name = _swissEsc(node.participant1_name || (isBye ? 'BYE' : 'TBD'));
    var p2Name = _swissEsc(node.participant2_name || 'TBD');
    var isTeam = typeof TOC_CONFIG !== 'undefined' && !TOC_CONFIG.isSolo;

    // Build logo or letter-avatar for each participant
    function teamAvatar(logo, name, hasId) {
      if (!isTeam || !hasId) return '';
      if (logo) {
        return '<img src="' + logo + '" alt="" class="w-5 h-5 rounded-full object-cover border border-dc-border/30 flex-shrink-0"'
          + ' onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">'
          + '<div class="w-5 h-5 rounded-full bg-theme-surface border border-theme-border items-center justify-center flex-shrink-0" style="display:none">'
          + '<span class="text-[8px] font-bold text-theme">' + (name || '?')[0].toUpperCase() + '</span></div>';
      }
      return '<div class="w-5 h-5 rounded-full bg-theme-surface border border-theme-border flex items-center justify-center flex-shrink-0">'
        + '<span class="text-[8px] font-bold text-theme">' + (name || '?')[0].toUpperCase() + '</span></div>';
    }
    var p1LogoHtml = teamAvatar(p1Logo, p1Name, node.participant1_id);
    var p2LogoHtml = teamAvatar(p2Logo, p2Name, node.participant2_id);

    // Series wins for BO3/BO5
    var bestOf = (m && m.best_of) ? m.best_of : 1;
    var gameScores = (m && m.game_scores) ? m.game_scores : [];
    var p1Wins = 0; var p2Wins = 0;
    gameScores.forEach(function(g) {
      if (g.p1_score > g.p2_score) p1Wins++; else if (g.p2_score > g.p1_score) p2Wins++;
    });
    var showSeries = bestOf > 1 && gameScores.length > 0;
    var p1Score = showSeries ? p1Wins : (m && m.participant1_score != null ? m.participant1_score : '\u2014');
    var p2Score = showSeries ? p2Wins : (m && m.participant2_score != null ? m.participant2_score : '\u2014');
    var boTag = bestOf > 1 ? '<span class="text-[8px] font-mono text-dc-text/40 ml-1">BO' + bestOf + '</span>' : '';

    // GF / GFR visual treatment
    var isGf  = !!node.is_gf;
    var isGfr = !!node.is_gf_reset;
    // GFR nodes have is_bye=true from backend but are conditional matches, not byes
    var byeClass    = (isBye && !isGfr) ? 'bracket-bye-card opacity-40' : '';
    var extraBorder = isGfr ? 'border-amber-500/40' : isGf ? 'border-amber-400/50' : '';
    // For GFR/GF show TBD with contextual labels (not 'BYE').
    // GF slot 2 is always the LB winner.  GF slot 1 is the WB winner.
    if (isGf) {
      if (!node.participant1_id) p1Name = '🏆 WB Winner';
      if (!node.participant2_id) p2Name = '🔴 LB Winner';
    }
    if (isGfr) {
      p1Name = node.participant1_name || 'TBD';
      p2Name = node.participant2_name || 'TBD';
    }
    var gfBanner  = isGf  ? '<div class="text-[8px] font-bold text-amber-400 uppercase tracking-widest text-center py-1 bg-amber-500/5 border-b border-amber-500/20">\uD83D\uDC51 Grand Finals</div>' : '';
    var gfrBanner = isGfr ? '<div class="text-[8px] font-bold text-amber-300/80 uppercase tracking-widest text-center py-1 bg-amber-500/[0.04] border-b border-amber-500/20">\u26A1 GF Reset \u00B7 If Needed</div>' : '';

    return '<div class="bracket-match-card relative bg-dc-bg border ' + sc + ' ' + extraBorder + ' rounded-lg overflow-hidden hover:border-dc-borderLight mx-2 my-1 cursor-pointer transition-colors ' + byeClass + '"'
      + ' data-node-id="' + nodeId + '" data-round="' + roundIdx + '" data-match="' + matchIdx + '"'
      + ' data-node="' + nodeJsonAttr + '">'
      + liveDot
      + gfBanner + gfrBanner
      + '<div class="flex items-center justify-between px-3 py-2 border-b border-dc-border/30 ' + (p1Win ? 'bg-emerald-500/[0.06]' : '') + '">'
      + '<div class="flex items-center gap-2 min-w-0 flex-1">' + p1LogoHtml
      + '<span class="text-xs ' + (p1Win ? 'text-white font-bold' : 'text-white/70') + ' truncate max-w-[120px]">' + p1Name + '</span></div>'
      + '<span class="text-xs font-mono font-bold ' + (p1Win ? 'text-emerald-400' : 'text-dc-text/50') + '">' + p1Score + boTag + '</span></div>'
      + '<div class="flex items-center justify-between px-3 py-2 ' + (p2Win ? 'bg-emerald-500/[0.06]' : '') + '">'
      + '<div class="flex items-center gap-2 min-w-0 flex-1">' + p2LogoHtml
      + '<span class="text-xs ' + (p2Win ? 'text-white font-bold' : 'text-white/70') + ' truncate max-w-[120px]">' + p2Name + '</span></div>'
      + '<span class="text-xs font-mono font-bold ' + (p2Win ? 'text-emerald-400' : 'text-dc-text/50') + '">' + p2Score + '</span></div></div>';
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
    path.setAttribute('stroke', 'rgba(255,255,255,0.15)');
    path.setAttribute('stroke-width', '1.5');
    path.setAttribute('fill', 'none');
    svg.appendChild(path);
  }

  /* --- Redraw connectors on window resize (debounced) -------- */
  var _resizeTimer = null;
  window.addEventListener('resize', function() {
    clearTimeout(_resizeTimer);
    _resizeTimer = setTimeout(function() {
      drawBracketConnectors('bracket-grid-winners');
      drawBracketConnectors('bracket-grid-losers');
      drawBracketConnectors('bracket-grid-main');
    }, 200);
  });

  /* --- Seeding editor ---------------------------------------- */
  function renderSeedList(nodes) {
    var container = document.querySelector('#seed-list');
    if (!container) return;
    var minRound = nodes.reduce(function(min, n) { return Math.min(min, n.round_number); }, 999);
    var round1 = nodes.filter(function(n) { return n.round_number === 1 || n.round_number === minRound; });
    var participants = [];
    var seen = {};
    round1.forEach(function(n) {
      [{ id: n.participant1_id, name: n.participant1_name, logo: n.participant1_logo || '' },
       { id: n.participant2_id, name: n.participant2_name, logo: n.participant2_logo || '' }].forEach(function(p) {
        if (p.id && !seen[p.id]) { seen[p.id] = true; participants.push(p); }
      });
    });

    var isTeam = typeof TOC_CONFIG !== 'undefined' && !TOC_CONFIG.isSolo;

    container.innerHTML = participants.map(function(p, i) {
      var logoHtml = '';
      if (isTeam) {
        if (p.logo) {
          logoHtml = '<img src="' + p.logo + '" alt="" class="w-6 h-6 rounded-full object-cover border border-dc-border/30 flex-shrink-0"'
            + ' onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">'
            + '<div class="w-6 h-6 rounded-full bg-theme-surface border border-theme-border items-center justify-center flex-shrink-0" style="display:none">'
            + '<span class="text-[9px] font-bold text-theme">' + (p.name || '?')[0].toUpperCase() + '</span></div>';
        } else {
          logoHtml = '<div class="w-6 h-6 rounded-full bg-theme-surface border border-theme-border flex items-center justify-center flex-shrink-0">'
            + '<span class="text-[9px] font-bold text-theme">' + (p.name || '?')[0].toUpperCase() + '</span></div>';
        }
      }
      return '<div class="flex items-center gap-3 bg-dc-bg border border-dc-border rounded-lg px-3 py-2 hover:border-dc-borderLight transition-colors cursor-move" data-reg-id="' + p.id + '" draggable="true">'
        + '<span class="w-6 h-6 rounded bg-dc-panel border border-dc-border flex items-center justify-center text-[10px] font-mono font-bold text-theme">' + (i + 1) + '</span>'
        + logoHtml
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
          if (fromIdx < toIdx) el.after(dragEl); else el.before(dragEl);
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
    } catch (e) { toast(parseError(e) || 'Failed to save seeds', 'error'); }
  }

  /* ================================================================
   *  BRACKET ACTIONS
   * ================================================================ */
  async function generate() {
    // Frontend guard + backend guard
    if (bracketData && bracketData.exists) {
      toast('A bracket already exists. Reset it before generating a new one.', 'error');
      return;
    }
    TOC.dangerConfirm({
      title: 'Generate Bracket',
      message: 'A bracket will be generated from the current confirmed registrations. You will not be able to edit seeding afterward without resetting.',
      confirmText: 'Generate Bracket',
      variant: 'warning',
      onConfirm: async function () {
        try {
          await API.post('brackets/generate/');
          toast('Bracket generated', 'success');
          refresh();
        } catch (e) { toast(parseError(e), 'error'); }
      },
    });
  }

  async function resetBracket() {
    if (!bracketData || !bracketData.exists) {
      toast('No bracket to reset.', 'error');
      return;
    }
    var confirmed = await showTypedConfirmation(
      'Reset Bracket',
      'This will permanently delete the current bracket, all matches, and all match data. This action CANNOT be undone.',
      'RESET'
    );
    if (!confirmed) return;
    try {
      await API.post('brackets/reset/');
      toast('Bracket reset', 'info');
      refresh();
    } catch (e) { toast(parseError(e), 'error'); }
  }

  async function publish() {
    if (!bracketData || !bracketData.exists) {
      toast('No bracket to publish.', 'error');
      return;
    }
    if (bracketData.bracket && bracketData.bracket.is_finalized) {
      toast('Bracket is already published.', 'error');
      return;
    }
    TOC.dangerConfirm({
      title: 'Publish Bracket',
      message: 'The bracket will become visible to all participants and the public. Changes will require a reset.',
      confirmText: 'Publish Bracket',
      variant: 'warning',
      onConfirm: async function () {
        try {
          await API.post('brackets/publish/');
          toast('Bracket published', 'success');
          refresh();
        } catch (e) { toast(parseError(e), 'error'); }
      },
    });
  }

  /* ================================================================
   *  PUBLIC BRACKET SHARING
   * ================================================================ */
  function shareBracket() {
    // Reuse module-level slug from window.TOC?.slug (defined at top of IIFE)
    const origin = window.location.origin;
    const publicUrl = `${origin}/tournaments/${slug}/bracket/`;
    const embedCode = `<iframe src="${publicUrl}" width="100%" height="700" frameborder="0" allowfullscreen style="border:none;border-radius:12px;"></iframe>`;

    const html = `
      <div class="p-6 space-y-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-theme/10 border border-theme/20 flex items-center justify-center">
            <i data-lucide="share-2" class="w-5 h-5 text-theme"></i>
          </div>
          <div>
            <h3 class="font-display font-black text-lg text-white">Share Bracket</h3>
            <p class="text-[10px] text-dc-text font-mono">Public link & embed code — no login required</p>
          </div>
        </div>

        <div class="space-y-4">
          <div class="space-y-2">
            <label class="text-[10px] font-bold text-dc-text uppercase tracking-widest">Public Bracket Link</label>
            <div class="flex gap-2">
              <input type="text" value="${publicUrl}" readonly
                class="flex-1 bg-dc-base border border-dc-border rounded-lg px-3 py-2 text-xs font-mono text-dc-textBright outline-none focus:border-theme/50"
                onclick="this.select()">
              <button onclick="navigator.clipboard.writeText('${publicUrl}').then(()=>TOC.toast('Link copied!','success'))"
                class="px-4 py-2 bg-theme text-dc-bg text-xs font-bold rounded-lg hover:opacity-90 transition-opacity flex items-center gap-1.5">
                <i data-lucide="copy" class="w-3.5 h-3.5"></i> Copy
              </button>
              <a href="${publicUrl}" target="_blank"
                class="px-4 py-2 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-bold rounded-lg hover:bg-white/5 transition-colors flex items-center gap-1.5">
                <i data-lucide="external-link" class="w-3.5 h-3.5"></i> Open
              </a>
            </div>
          </div>

          <div class="space-y-2">
            <label class="text-[10px] font-bold text-dc-text uppercase tracking-widest">Embed Code (iframe)</label>
            <div class="flex gap-2">
              <textarea id="bracket-share-embed" readonly rows="3"
                class="flex-1 bg-dc-base border border-dc-border rounded-lg px-3 py-2 text-xs font-mono text-dc-text outline-none focus:border-theme/50 resize-none"
                onclick="this.select()">${embedCode}</textarea>
              <button onclick="navigator.clipboard.writeText(document.querySelector('#bracket-share-embed').value).then(()=>TOC.toast('Embed code copied!','success'))"
                class="px-4 py-2 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-bold rounded-lg hover:bg-white/5 transition-colors flex items-center gap-1.5 self-start">
                <i data-lucide="copy" class="w-3.5 h-3.5"></i> Copy
              </button>
            </div>
          </div>

          <div class="bg-dc-panel/50 border border-dc-border/50 rounded-xl p-4 text-xs text-dc-text">
            <i data-lucide="info" class="w-3.5 h-3.5 inline-block text-dc-info mr-1 align-[-3px]"></i>
            The public bracket view is accessible to everyone without login.
            It shows the bracket in read-only mode with live match results.
          </div>
        </div>

        <div class="flex justify-end">
          <button onclick="TOC.brackets.closeOverlay('bracket-share-overlay')" class="px-4 py-2 bg-dc-panel border border-dc-border text-dc-text text-xs font-bold rounded-lg hover:bg-white/5 transition-colors">
            Close
          </button>
        </div>
      </div>`;

    showOverlay('bracket-share-overlay', html);
    if (typeof lucide !== 'undefined') {
      try { lucide.createIcons(); } catch (_) {}
    }
  }

  /* ================================================================
   *  GROUP STAGE ACTIONS
   * ================================================================ */
  async function refreshGroups() {
    try {
      var data = await API.get('groups/');
      groupsData = data;
      renderGroupsView(data);
      updateGroupButtons();
    } catch (e) { console.error('[brackets] groups error', e); }
  }

  async function recalcStandings() {
    try {
      toast('Recalculating standings\u2026', 'info');
      await API.get('groups/standings/');
      await refreshGroups();
      toast('Standings updated', 'success');
    } catch (e) { toast('Failed to recalculate standings', 'error'); }
  }

  function openGroupConfig() {
    // Pre-fill from current data if available
    var cur = groupsData && groupsData.stage ? groupsData.stage : {};
    var numG = cur.num_groups || 4;
    var gSize = cur.group_size || 4;
    var gFmt = cur.format || 'round_robin';
    var gAdv = cur.advancement_count_per_group || 2;

    var html = '<div class="p-6 space-y-4">'
      + '<h3 class="font-display font-black text-lg text-white">Configure Groups</h3>'
      + '<div class="grid grid-cols-2 gap-3">'
      + '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Groups</label>'
      + '<input id="gc-num-groups" type="number" value="' + numG + '" min="2" max="32" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none"></div>'
      + '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Group Size</label>'
      + '<input id="gc-group-size" type="number" value="' + gSize + '" min="2" max="16" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none"></div>'
      + '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Format</label>'
      + '<select id="gc-format" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">'
      + '<option value="round_robin"' + (gFmt === 'round_robin' ? ' selected' : '') + '>Round Robin</option>'
      + '<option value="double_round_robin"' + (gFmt === 'double_round_robin' ? ' selected' : '') + '>Double RR</option></select></div>'
      + '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Advance Per Group</label>'
      + '<input id="gc-advance" type="number" value="' + gAdv + '" min="1" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none"></div>'
      + '</div>'
      + '<button onclick="TOC.brackets.confirmGroupConfig()" class="w-full py-2.5 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Save Configuration</button>'
      + '</div>';
    showOverlay('group-config-overlay', html);
  }

  async function confirmGroupConfig() {
    try {
      var numGroups = document.querySelector('#gc-num-groups');
      var groupSize = document.querySelector('#gc-group-size');
      var gcFormat  = document.querySelector('#gc-format');
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
    } catch (e) { toast(parseError(e), 'error'); }
  }

  async function drawGroups() {
    // Frontend guard — backend also guards
    var stageState = (groupsData && groupsData.stage) ? groupsData.stage.state : 'pending';
    if (stageState === 'active' || stageState === 'completed') {
      toast('Groups already drawn. Reset first to re-draw.', 'error');
      return;
    }
    TOC.dangerConfirm({
      title: 'Execute Group Draw',
      message: 'Participants will be randomly assigned to groups. You can reset and re-draw if needed.',
      confirmText: 'Draw Groups',
      variant: 'warning',
      onConfirm: async function () {
        try {
          await API.post('groups/draw/', { method: 'random' });
          toast('Groups drawn successfully', 'success');
          refreshGroups();
        } catch (e) { toast(parseError(e), 'error'); }
      },
    });
  }

  async function resetGroups() {
    var confirmed = await showTypedConfirmation(
      'Reset Group Draw',
      'This will clear all group standings and match data, returning groups to pending state. This action CANNOT be undone.',
      'RESET'
    );
    if (!confirmed) return;
    try {
      await API.post('groups/reset/');
      toast('Group draw reset', 'info');
      refreshGroups();
    } catch (e) { toast(parseError(e), 'error'); }
  }

  function generatePlayoffs() {
    TOC.dangerConfirm({
      title: 'Generate Playoff Bracket',
      message: 'The playoff bracket will be seeded from current group standings. This will lock in group stage results.',
      confirmText: 'Generate Playoffs',
      variant: 'warning',
      onConfirm: async function () {
        try {
          toast('Generating playoff bracket…', 'info');
          await API.post('brackets/generate/', { seeding_method: 'group_standings' });
          toast('Playoff bracket generated!', 'success');
          switchSubTab('bracket');
          refresh();
        } catch (e) { toast(parseError(e), 'error'); }
      },
    });
  }

  function startLiveDraw() {
    window.open('/tournaments/' + slug + '/draw/director/', '_blank');
  }

  function buildGroupToKnockoutSeeding(groups, advancePerGroup) {
    var pairs = [];
    for (var i = 0; i < groups.length; i += 2) {
      var gA = groups[i]; var gB = groups[i + 1];
      if (!gB) break;
      var aL = (gA.name || '').replace('Group ', '');
      var bL = (gB.name || '').replace('Group ', '');
      pairs.push({ p1Label: aL + '1', p2Label: bL + '2' });
      if (advancePerGroup >= 2) pairs.push({ p1Label: bL + '1', p2Label: aL + '2' });
    }
    return pairs;
  }

  /* ================================================================
   *  SCHEDULE VIEW — Sprint 29
   * ================================================================ */
  async function refreshSchedule() {
    try {
      var data = await API.get('schedule/');
      scheduleData = data;
      renderScheduleView(data);
    } catch (e) {
      console.error('[brackets] schedule error', e);
      var c = document.querySelector('#schedule-content');
      if (c) c.innerHTML = '<p class="text-dc-text text-center py-12">Failed to load schedule.</p>';
    }
  }

  function renderScheduleView(data) {
    var container = document.querySelector('#schedule-content');
    if (!container) return;

    var matches = data && data.matches ? data.matches : [];
    var conflicts = data && data.conflicts ? data.conflicts : [];
    var summary = data && data.summary ? data.summary : {};

    if (!matches.length) {
      container.innerHTML = '<div class="flex flex-col items-center justify-center py-20 text-center">'
        + '<div class="w-16 h-16 rounded-2xl bg-dc-panel border border-dc-border flex items-center justify-center mb-5">'
        + '<i data-lucide="calendar" class="w-8 h-8 text-dc-text/30"></i></div>'
        + '<h3 class="text-lg font-bold text-white mb-2">No Matches Scheduled</h3>'
        + '<p class="text-sm text-dc-text max-w-sm mb-6">Generate a bracket first, then auto-schedule or manually set match times.</p></div>';
      iconsRefresh();
      return;
    }

    // Summary stats
    var statsHtml = '<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">';
    var statItems = [
      { label: 'Total', value: summary.total_matches || matches.length, icon: 'hash' },
      { label: 'Scheduled', value: summary.scheduled || matches.filter(function(m) { return m.scheduled_time; }).length, icon: 'calendar' },
      { label: 'Completed', value: summary.completed || matches.filter(function(m) { return m.state === 'completed'; }).length, icon: 'check-circle' },
      { label: 'Conflicts', value: conflicts.length, icon: 'alert-triangle' },
    ];
    statItems.forEach(function(s) {
      var isConflict = s.label === 'Conflicts' && s.value > 0;
      statsHtml += '<div class="glass-box rounded-xl p-4 border border-dc-border' + (isConflict ? ' border-dc-danger/30 bg-dc-danger/[0.03]' : '') + '">'
        + '<div class="flex items-center gap-2 mb-1"><i data-lucide="' + s.icon + '" class="w-3.5 h-3.5 ' + (isConflict ? 'text-dc-danger' : 'text-dc-text/40') + '"></i>'
        + '<span class="text-[9px] font-bold text-dc-text uppercase tracking-widest">' + s.label + '</span></div>'
        + '<p class="text-xl font-mono font-black ' + (isConflict ? 'text-dc-danger' : 'text-white') + '">' + s.value + '</p></div>';
    });
    statsHtml += '</div>';

    // Conflicts warning
    var conflictHtml = '';
    if (conflicts.length > 0) {
      conflictHtml = '<div class="mb-6 p-4 glass-box rounded-xl border border-dc-danger/20 bg-dc-danger/[0.03]">'
        + '<div class="flex items-center gap-2 mb-2"><i data-lucide="alert-triangle" class="w-4 h-4 text-dc-danger"></i>'
        + '<span class="text-xs font-bold text-dc-danger uppercase tracking-widest">Schedule Conflicts</span></div>'
        + '<div class="space-y-1">' + conflicts.slice(0, 5).map(function(c) {
          return '<p class="text-[10px] text-dc-text">Match #' + c.match_a + ' overlaps with Match #' + c.match_b
            + ' <span class="text-dc-text/40">(participant ' + c.participant_id + ')</span></p>';
        }).join('') + (conflicts.length > 5 ? '<p class="text-[10px] text-dc-text/50">\u2026and ' + (conflicts.length - 5) + ' more</p>' : '') + '</div></div>';
    }

    // Group by day
    var byDay = {};
    matches.forEach(function(m) {
      var day = m.scheduled_time ? new Date(m.scheduled_time).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }) : 'Unscheduled';
      if (!byDay[day]) byDay[day] = [];
      byDay[day].push(m);
    });

    var tableHtml = Object.keys(byDay).map(function(day) {
      var dayMatches = byDay[day];
      var rows = dayMatches.map(function(m) {
        var sc = stateColors[m.state] || stateColors.scheduled;
        var time = m.scheduled_time ? new Date(m.scheduled_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '\u2014';
        return '<tr class="border-b border-dc-border/10 hover:bg-white/[0.02] transition-colors">'
          + '<td class="py-2.5 px-3 text-[10px] font-mono text-dc-text/60">' + time + '</td>'
          + '<td class="py-2.5 px-3 text-[10px] font-mono text-dc-text/40">R' + (m.round_number || '\u2014') + ' M' + (m.match_number || '\u2014') + '</td>'
          + '<td class="py-2.5 px-3 text-xs text-white/80 font-medium">' + (m.participant1_name || 'TBD') + '</td>'
          + '<td class="py-2.5 px-1 text-center text-dc-text/20 text-[10px]">vs</td>'
          + '<td class="py-2.5 px-3 text-xs text-white/80 font-medium">' + (m.participant2_name || 'TBD') + '</td>'
          + '<td class="py-2.5 px-3 text-center"><span class="text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border ' + sc + '">' + (m.state || 'scheduled') + '</span></td>'
          + '<td class="py-2.5 px-3 text-center font-mono text-xs text-white/60">'
          + (m.participant1_score != null ? m.participant1_score + ' - ' + m.participant2_score : '\u2014') + '</td></tr>';
      }).join('');

      return '<div class="mb-4"><div class="text-[10px] font-bold text-dc-text/50 uppercase tracking-widest mb-2 px-1">' + day + '</div>'
        + '<div class="glass-box rounded-xl overflow-hidden border border-dc-border">'
        + '<table class="w-full text-[10px]"><thead><tr class="text-dc-text/60 border-b border-dc-border/30 bg-dc-panel/20">'
        + '<th class="text-left py-2 px-3 w-16">Time</th><th class="text-left py-2 px-3 w-16">ID</th>'
        + '<th class="text-left py-2 px-3">Home</th><th class="w-6"></th><th class="text-left py-2 px-3">Away</th>'
        + '<th class="text-center py-2 px-3 w-20">Status</th><th class="text-center py-2 px-3 w-16">Score</th>'
        + '</tr></thead><tbody>' + rows + '</tbody></table></div></div>';
    }).join('');

    container.innerHTML = statsHtml + conflictHtml + tableHtml;
    iconsRefresh();
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
    } catch (e) { toast(parseError(e), 'error'); }
  }

  async function deletePipeline(id) {
    TOC.dangerConfirm({
      title: 'Delete Pipeline',
      body: 'Are you sure you want to delete this pipeline? This cannot be undone.',
      confirmLabel: 'Delete',
      onConfirm: async function() {
        try {
          await API.delete('pipelines/' + id + '/');
          toast('Pipeline deleted', 'success');
          refreshPipelines();
        } catch (e) { toast(parseError(e), 'error'); }
      }
    });
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
    // GFR nodes start as is_bye=true until activated — still show info for them.
    if (!node || (node.is_bye && !node.is_gf_reset)) return;
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
      + '<p class="text-white font-mono font-bold mt-0.5">#' + (node.match_number || node.position || '\u2014') + '</p></div>'
      + (m && m.scheduled_time ? '<div class="bg-dc-bg rounded-lg p-2.5 border border-dc-border/50 col-span-2"><span class="text-dc-text/60">Scheduled</span>'
        + '<p class="text-white font-mono font-bold mt-0.5">' + new Date(m.scheduled_time).toLocaleString() + '</p></div>' : '')
      + '</div>';

    // Action buttons based on state
    if (m) {
      html += '<div class="flex gap-2 flex-wrap">';
      if (state === 'scheduled') {
        html += '<button onclick="TOC.matches && TOC.matches.markLive && TOC.matches.markLive(' + m.id + '); TOC.brackets.closeOverlay(\'bracket-match-detail\')" class="flex-1 py-2.5 bg-emerald-500/15 text-emerald-400 text-xs font-bold rounded-lg hover:bg-emerald-500/25 transition-colors">'
          + '<i data-lucide="play" class="w-3 h-3 inline mr-1"></i>Start</button>';
      }
      if (state === 'live') {
        html += '<button onclick="TOC.matches && TOC.matches.openScoreDrawer && TOC.matches.openScoreDrawer(' + m.id + ', \'' + p1Name.replace(/'/g, "\\'") + '\', \'' + p2Name.replace(/'/g, "\\'") + '\')" class="flex-1 py-2.5 bg-theme/15 text-theme text-xs font-bold rounded-lg hover:bg-theme/25 transition-colors">'
          + '<i data-lucide="edit-3" class="w-3 h-3 inline mr-1"></i>Score</button>';
      }
      if (state !== 'completed' && state !== 'forfeit' && state !== 'cancelled') {
        html += '<button onclick="TOC.brackets.forfeitFromBracket(' + m.id + ')" class="py-2.5 px-4 bg-dc-danger/10 border border-dc-danger/20 text-dc-danger text-xs font-bold rounded-lg hover:bg-dc-danger/20 transition-colors">'
          + '<i data-lucide="flag" class="w-3 h-3 inline mr-1"></i>Forfeit</button>';
      }
      html += '</div>';
    }
    html += '</div>';
    showOverlay('bracket-match-detail', html);
    iconsRefresh();
  }

  function forfeitFromBracket(matchId) {
    TOC.dangerConfirm({
      title: 'Declare Match Forfeit',
      message: 'You will be redirected to Match Operations to select the forfeiting side. Forfeits are permanent.',
      confirmText: 'Proceed to Forfeit',
      onConfirm: function () {
        closeOverlay('bracket-match-detail');
        if (window.TOC && window.TOC.switchTab) window.TOC.switchTab('matches');
        toast('Open Match #' + matchId + ' in Match Operations to select forfeit side.', 'info');
      },
    });
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
    if (tiebreakers.length > 0) items.push({ icon: 'scale', label: 'Tiebreakers', value: 'Points \u2192 ' + tbStr });
    if (pointsSys.win != null) items.push({ icon: 'hash', label: 'Points', value: 'W=' + (pointsSys.win || 3) + '  D=' + (pointsSys.draw != null ? pointsSys.draw : 1) + '  L=' + (pointsSys.loss != null ? pointsSys.loss : 0) });

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
  /* ================================================================
   *  SWISS STANDINGS
   * ================================================================ */
  var _swissData = null;

  async function refreshSwiss() {
    var container = document.querySelector('#swiss-standings-container');
    if (!container) return;
    try {
      var data = await API.get('swiss/standings/');
      _swissData = data;
      renderSwissView(data);
    } catch (e) {
      if (container) container.innerHTML = '<div class="flex flex-col items-center justify-center py-16">'
        + '<i data-lucide="info" class="w-8 h-8 text-dc-border mb-3"></i>'
        + '<p class="text-sm text-dc-text/50">No Swiss bracket generated yet.</p>'
        + '<button onclick="TOC.brackets.generate()" class="mt-4 px-5 py-2 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90">'
        + '<i data-lucide="zap" class="w-3.5 h-3.5 inline mr-1.5"></i>Generate Swiss Bracket</button></div>';
      iconsRefresh();
    }
  }

  function renderSwissView(data) {
    // Round info header
    var curEl   = document.querySelector('#swiss-current-round');
    var totEl   = document.querySelector('#swiss-total-rounds');
    var badge   = document.querySelector('#swiss-complete-badge');
    var advBtn  = document.querySelector('#btn-swiss-advance');
    var cur = data.current_round || 0;
    var tot = data.total_rounds  || 0;
    var done = cur >= tot;
    if (curEl) curEl.textContent = cur;
    if (totEl) totEl.textContent = tot;
    if (badge) { if (done) badge.classList.remove('hidden'); else badge.classList.add('hidden'); }
    if (advBtn) { if (done) advBtn.setAttribute('disabled', ''); else advBtn.removeAttribute('disabled'); }

    var standings = data.standings || [];
    var container = document.querySelector('#swiss-standings-container');
    if (!container) return;
    if (!standings.length) {
      container.innerHTML = '<p class="text-dc-text/50 text-sm text-center py-12">No standings data yet.</p>';
      return;
    }
    var isSolo = (window.TOC_CONFIG || {}).isSolo;
    var entityLabel = isSolo ? 'Player' : 'Team';
    var html = '<div class="glass-box rounded-xl overflow-hidden">'
      + '<div class="overflow-x-auto">'
      + '<table class="w-full text-xs">'
      + '<thead><tr class="border-b border-dc-border/40">'
      + '<th class="px-4 py-3 text-left font-bold text-dc-text uppercase tracking-widest w-10">#</th>'
      + '<th class="px-4 py-3 text-left font-bold text-dc-text uppercase tracking-widest">' + entityLabel + '</th>'
      + '<th class="px-4 py-3 text-center font-bold text-dc-success uppercase tracking-widest">W</th>'
      + '<th class="px-4 py-3 text-center font-bold text-dc-danger uppercase tracking-widest">L</th>'
      + '<th class="px-4 py-3 text-center font-bold text-dc-text uppercase tracking-widest">Bye</th>'
      + '<th class="px-4 py-3 text-center font-bold text-dc-text uppercase tracking-widest">Buchholz</th>'
      + '</tr></thead><tbody>';

    standings.forEach(function(s, i) {
      var isTop = i < 4;
      var rowClass = isTop ? 'border-b border-dc-border/20 bg-theme/5' : 'border-b border-dc-border/10 hover:bg-dc-surface/60 transition-colors';
      var rankClass = i === 0 ? 'text-amber-400 font-black' : i < 3 ? 'text-dc-textBright font-bold' : 'text-dc-text';
      html += '<tr class="' + rowClass + '">'
        + '<td class="px-4 py-3 font-mono ' + rankClass + '">' + (i + 1) + '</td>'
        + '<td class="px-4 py-3"><div class="flex items-center gap-2">'
        + (s.seed ? '<span class="text-[10px] font-mono text-dc-text/50 w-5">\u00b7' + s.seed + '</span>' : '<span class="w-5"></span>')
        + '<span class="font-bold text-white truncate max-w-[200px]">' + _swissEsc(s.name || 'TBD') + '</span>'
        + '</div></td>'
        + '<td class="px-4 py-3 text-center font-mono text-dc-success font-bold">' + (s.wins || 0) + '</td>'
        + '<td class="px-4 py-3 text-center font-mono text-dc-danger">' + (s.losses || 0) + '</td>'
        + '<td class="px-4 py-3 text-center font-mono text-dc-text">' + (s.byes || 0) + '</td>'
        + '<td class="px-4 py-3 text-center font-mono text-dc-textBright">' + (s.buchholz || 0) + '</td>'
        + '</tr>';
    });

    html += '</tbody></table></div></div>';
    container.innerHTML = html;
    iconsRefresh();
  }

  function _swissEsc(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  async function advanceSwissRound() {
    var btn = document.querySelector('#btn-swiss-advance');
    if (btn) btn.setAttribute('disabled', '');
    try {
      var data = await API.post('swiss/advance-round/', {});
      _swissData = data;
      renderSwissView(data);
      toast('Round advanced — new pairings created', 'success');
      // Refresh bracket nodes too so match list updates
      var bData = await API.get('brackets/').catch(function() { return null; });
      if (bData) { bracketData = bData; renderBracketView(bData, groupsData); }
    } catch (e) {
      toast(parseError(e), 'error');
      if (btn) btn.removeAttribute('disabled');
    }
  }

  function showDrawGuide() {
    var steps = [
      { title: 'Real-Time WebSocket Broadcast', desc: 'The draw is broadcast live to all connected spectators via WebSocket. Every draw action is instantly visible.' },
      { title: 'Lottery Spinner Animation', desc: 'Each participant is drawn with a cinematic spinning reel animation, scrolling through remaining participants before landing.' },
      { title: 'Spectator Link', desc: 'Share the spectator URL with players and fans. They see a polished waiting screen until the director starts the draw.' },
      { title: 'Cryptographic Audit Hash', desc: 'When finalized, a SHA-256 hash of all group assignments is stored, creating an immutable tamper-evident record.' },
      { title: 'Manual Pick Mode', desc: 'Directors can switch to Manual Pick to hand-select assignments, bypassing the spinner for seeded or invited players.' },
    ];
    var html = '<div class="p-6 space-y-5 max-w-lg">'
      + '<div class="flex items-center gap-3 mb-2">'
      + '<div class="w-10 h-10 rounded-xl bg-theme/10 border border-theme/20 flex items-center justify-center">'
      + '<i data-lucide="help-circle" class="w-5 h-5 text-theme/70"></i></div>'
      + '<h3 class="font-display font-black text-lg text-white">How does the Live Draw work?</h3></div>'
      + '<div class="space-y-3 text-sm text-dc-text leading-relaxed">'
      + steps.map(function(s, i) {
        return '<div class="flex gap-3">'
          + '<div class="w-6 h-6 rounded-full bg-theme/10 border border-theme/20 flex items-center justify-center flex-shrink-0 mt-0.5">'
          + '<span class="text-theme text-[10px] font-black">' + (i + 1) + '</span></div>'
          + '<div><span class="text-white font-semibold">' + s.title + '</span>'
          + '<p class="text-dc-text/70 text-xs mt-1">' + s.desc + '</p></div></div>';
      }).join('')
      + '</div></div>';
    showOverlay('draw-guide', html);
  }

  /* ================================================================
   *  EVENT DELEGATION — bracket match card clicks
   * ================================================================ */
  document.addEventListener('click', function(e) {
    var card = e.target.closest('.bracket-match-card');
    if (!card) return;
    var raw = card.getAttribute('data-node');
    if (!raw) return;
    try {
      var node = JSON.parse(raw);
      if (typeof onMatchCardClick === 'function') onMatchCardClick(node);
    } catch (_) { /* ignore malformed data */ }
  });

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
    shareBracket: shareBracket,
    saveSeedOrder: saveSeedOrder, refreshGroups: refreshGroups, recalcStandings: recalcStandings,
    openGroupConfig: openGroupConfig, confirmGroupConfig: confirmGroupConfig,
    drawGroups: drawGroups, resetGroups: resetGroups,
    generatePlayoffs: generatePlayoffs, startLiveDraw: startLiveDraw, switchSubTab: switchSubTab,
    refreshPipelines: refreshPipelines, openCreatePipeline: openCreatePipeline, confirmCreatePipeline: confirmCreatePipeline,
    deletePipeline: deletePipeline, closeOverlay: closeOverlay, onMatchCardClick: onMatchCardClick,
    forfeitFromBracket: forfeitFromBracket,
    showDrawGuide: showDrawGuide, refreshSchedule: refreshSchedule,
    // Swiss
    refreshSwiss: refreshSwiss, advanceSwissRound: advanceSwissRound,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail && e.detail.tab === 'brackets') init();
  });
})();
