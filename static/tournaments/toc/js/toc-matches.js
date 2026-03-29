/**
 * TOC Matches Module — Sprint 26: Full Control Room Rebuild
 *
 * Left panel: scrollable match list with group pills, state/round/search filters.
 * Right panel: match detail with inline Score Editor, Evidence Viewer, Audit Trail.
 * Lobby info panel, check-in indicators, match room link.
 * Persistent action row with Medic controls + Confirm/Dispute/Reset.
 * Custom dispute modal (replaces prompt()), lobby editor overlay.
 * Full keyboard navigation & accessibility.
 * XSS protection on all user-generated content.
 *
 * Preserves Sprint 9 verify overlay as full-screen power-user mode.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  /* --- XSS-safe HTML escaping ------------------------------ */
  const _escEl = document.createElement('div');
  function esc(s) {
    _escEl.textContent = s || '';
    return _escEl.innerHTML;
  }

  /* --- State Config ---------------------------------------- */
  const stateConfig = {
    scheduled:      { label: 'Scheduled',  cls: 'bg-dc-info/20 text-dc-info border-dc-info/30' },
    check_in:       { label: 'Check-in',   cls: 'bg-dc-warning/20 text-dc-warning border-dc-warning/30' },
    ready:          { label: 'Ready',       cls: 'bg-dc-success/20 text-dc-success border-dc-success/30' },
    live:           { label: 'Live',        cls: 'bg-dc-success/20 text-dc-success border-dc-success/30' },
    pending_result: { label: 'Pending',     cls: 'bg-dc-warning/20 text-dc-warning border-dc-warning/30' },
    completed:      { label: 'Completed',   cls: 'bg-dc-text/10 text-dc-text border-dc-border' },
    disputed:       { label: 'Disputed',    cls: 'bg-dc-danger/20 text-dc-danger border-dc-danger/30' },
    forfeit:        { label: 'Forfeit',     cls: 'bg-dc-danger/10 text-dc-danger/60 border-dc-danger/20' },
    cancelled:      { label: 'Cancelled',   cls: 'bg-dc-danger/10 text-dc-text/50 border-dc-border' },
  };

  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }

  function parseApiError(err) {
    if (!err) return 'Something went wrong. Please try again.';
    if (err.payload && typeof err.payload === 'object') {
      return err.payload.error || err.payload.detail || err.payload.message || err.message || 'Something went wrong. Please try again.';
    }
    return err.message || 'Something went wrong. Please try again.';
  }

  function groupsAreDrawn(groupsPayload) {
    var stageState = (groupsPayload && groupsPayload.stage && groupsPayload.stage.state)
      ? String(groupsPayload.stage.state).toLowerCase()
      : '';
    if (stageState === 'active' || stageState === 'completed') return true;
    var groups = (groupsPayload && groupsPayload.groups) ? groupsPayload.groups : [];
    return groups.some(function (g) {
      var standings = g && g.standings ? g.standings : [];
      return standings.length > 0 || !!(g && (g.is_drawn || g.is_finalized));
    });
  }

  function getGroupMatchStats(groupsPayload) {
    var groups = (groupsPayload && groupsPayload.groups) ? groupsPayload.groups : [];
    var total = 0;
    groups.forEach(function (g) {
      total += parseInt(g && g.matches_total != null ? g.matches_total : 0, 10) || 0;
    });
    return { total: total };
  }

  async function generateMatchesFromEmptyState() {
    try {
      toast('Checking group stage state...', 'info');
      var groupsPayload = await API.get('groups/');
      if (!groupsPayload || !groupsPayload.exists || !(groupsPayload.groups || []).length) {
        toast('No group stage is configured yet. Open Competition to configure groups first.', 'error');
        if (window.TOC && typeof window.TOC.navigate === 'function') window.TOC.navigate('brackets');
        return;
      }

      if (!groupsAreDrawn(groupsPayload)) {
        toast('Groups are not drawn yet. Draw groups first, then generate matches.', 'error');
        if (window.TOC && typeof window.TOC.navigate === 'function') window.TOC.navigate('brackets');
        return;
      }

      var rounds = (groupsPayload.stage && groupsPayload.stage.format === 'double_round_robin') ? 2 : 1;
      var stats = getGroupMatchStats(groupsPayload);
      var payload = { rounds: rounds };
      if (stats.total > 0) payload.allow_regenerate = true;

      toast(stats.total > 0 ? 'Re-generating group matches...' : 'Generating group matches...', 'info');
      var data = await API.post('groups/generate-matches/', payload);
      var generated = (data && data.generated_matches) ? data.generated_matches : 0;
      toast((generated ? generated + ' group matches generated.' : 'Group matches generated.') + ' Refreshing matches...', 'success');

      await refresh({ force: true });
      if (window.TOC && window.TOC.brackets && typeof window.TOC.brackets.refreshGroups === 'function') {
        window.TOC.brackets.refreshGroups();
      }
    } catch (e) {
      toast(parseApiError(e), 'error');
    }
  }

  let allMatches = [];
  let filteredMatches = [];
  let selectedMatchId = null;
  let selectedMatchDetail = null;
  let activeGroupFilter = '';
  let _debounceTimer = null;
  let _matchesInflight = null;
  let _matchesInflightQueryKey = '';
  let _matchesRequestId = 0;
  let _matchesLastFetchedAt = 0;
  let _matchesLastQueryKey = '';
  let _matchesAutoRefreshTimer = null;

  const MATCHES_CACHE_TTL_MS = 15000;
  const MATCHES_AUTO_REFRESH_MS = 30000;
  const MATCHES_STAT_IDS = ['total', 'live', 'pending', 'completed', 'disputed'];

  function isMatchesTabActive() {
    return (window.location.hash || '').replace('#', '') === 'matches';
  }

  function currentQueryKey() {
    const stateVal = $('#match-filter-state')?.value || '';
    const roundVal = $('#match-filter-round')?.value || '';
    const searchVal = $('#match-search')?.value || '';
    return [stateVal, roundVal, searchVal].join('::');
  }

  function hasFreshCache(queryKey) {
    return allMatches.length > 0
      && queryKey === _matchesLastQueryKey
      && (Date.now() - _matchesLastFetchedAt) < MATCHES_CACHE_TTL_MS;
  }

  function setMatchesSyncStatus(mode, note) {
    const el = $('#matches-sync-status');
    if (!el) return;

    if (mode === 'loading') {
      el.className = 'text-[10px] font-mono text-dc-warning mt-1';
      el.textContent = note || 'Syncing matches...';
      return;
    }

    if (mode === 'error') {
      el.className = 'text-[10px] font-mono text-dc-danger mt-1';
      el.textContent = note || 'Sync failed';
      return;
    }

    if (_matchesLastFetchedAt > 0) {
      el.className = 'text-[10px] font-mono text-dc-text mt-1';
      el.textContent = 'Last sync ' + new Date(_matchesLastFetchedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return;
    }

    el.className = 'text-[10px] font-mono text-dc-text mt-1';
    el.textContent = 'Not synced yet';
  }

  function setMatchesErrorBanner(message) {
    const el = $('#matches-error-banner');
    if (!el) return;

    if (!message) {
      el.classList.add('hidden');
      el.innerHTML = '';
      return;
    }

    el.classList.remove('hidden');
    el.innerHTML = `
      <div class="flex items-start gap-3">
        <i data-lucide="wifi-off" class="w-4 h-4 text-dc-danger shrink-0 mt-0.5"></i>
        <div class="min-w-0 flex-1">
          <p class="text-xs font-bold text-white">Matches request failed</p>
          <p class="text-[11px] text-dc-text mt-1">${esc(message)}</p>
          <button type="button" class="mt-2 px-2.5 py-1 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" onclick="TOC.matches.refresh({ force: true })">Retry now</button>
        </div>
      </div>`;
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function setMatchesLoading(loading) {
    MATCHES_STAT_IDS.forEach((id) => {
      const el = $(`#matches-stat-${id}`);
      if (!el) return;
      el.classList.toggle('toc-loading-value', loading);
    });
    const list = $('#match-list');
    if (list) {
      list.classList.toggle('toc-panel-loading', loading);
      if (loading) list.setAttribute('aria-busy', 'true');
      else list.removeAttribute('aria-busy');
    }
  }

  /* ============================================================
     FETCH & RENDER
  ============================================================ */
  async function refresh(options) {
    const opts = options || {};
    const force = opts.force === true;
    const silent = opts.silent === true;

    const state = $('#match-filter-state')?.value || '';
    const round = $('#match-filter-round')?.value || '';
    const search = $('#match-search')?.value || '';
    const queryKey = currentQueryKey();

    if (!force && hasFreshCache(queryKey)) {
      applyGroupFilter();
      renderStats(allMatches);
      populateRoundFilter(allMatches);
      populateGroupPills(allMatches);
      setMatchesSyncStatus('ok');
      return { matches: allMatches };
    }

    if (_matchesInflight && !force && _matchesInflightQueryKey === queryKey) return _matchesInflight;

    if (!silent) {
      setMatchesLoading(true);
      setMatchesSyncStatus('loading', allMatches.length ? 'Refreshing matches...' : 'Loading matches...');
    }

    const requestId = ++_matchesRequestId;
    _matchesInflightQueryKey = queryKey;
    _matchesInflight = (async () => {
      try {
        const data = await API.get('matches/' +
          '?state=' + state + '&round=' + round + '&search=' + encodeURIComponent(search));
        if (requestId !== _matchesRequestId) return { matches: allMatches };

        allMatches = data.matches || [];
        _matchesLastFetchedAt = Date.now();
        _matchesLastQueryKey = queryKey;

        applyGroupFilter();
        renderStats(allMatches);
        populateRoundFilter(allMatches);
        populateGroupPills(allMatches);
        setMatchesLoading(false);
        setMatchesErrorBanner('');
        setMatchesSyncStatus('ok');
        return data;
      } catch (e) {
        if (requestId !== _matchesRequestId) return { matches: allMatches };
        const detail = e && e.message ? String(e.message) : 'Request failed';
        console.error('[matches] fetch error', e);
        toast('Failed to load matches', 'error');
        setMatchesLoading(false);
        if (allMatches.length) {
          setMatchesSyncStatus('error', `Using cached data (${detail})`);
          setMatchesErrorBanner(`Live refresh failed, showing cached matches data. ${detail}`);
        } else {
          setMatchesSyncStatus('error', detail);
          setMatchesErrorBanner(detail);
        }
        return { matches: allMatches };
      } finally {
        if (requestId === _matchesRequestId) {
          _matchesInflight = null;
          _matchesInflightQueryKey = '';
        }
      }
    })();

    return _matchesInflight;
  }

  function debouncedRefresh() {
    clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(refresh, 300);
  }

  /* --- Group filter pills ---------------------------------- */
  function populateGroupPills(matches) {
    var container = $('#match-group-pills');
    if (!container) return;
    var groups = [];
    var seen = {};
    matches.forEach(function (m) {
      if (m.group_label && !seen[m.group_label]) {
        seen[m.group_label] = true;
        groups.push(m.group_label);
      }
    });
    groups.sort();
    if (groups.length <= 1) { container.innerHTML = ''; return; }

    var html = '<button data-group="" class="match-pill ' +
      (activeGroupFilter === '' ? 'active bg-theme/15 text-theme border-theme/20' : 'bg-dc-bg text-dc-text border-dc-border hover:text-white') +
      ' px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-widest transition-all border" onclick="TOC.matches.filterGroup(\'\')" role="radio" aria-checked="' + (activeGroupFilter === '' ? 'true' : 'false') + '">All</button>';
    groups.forEach(function (g) {
      var eg = esc(g);
      html += '<button data-group="' + eg + '" class="match-pill ' +
        (activeGroupFilter === g ? 'active bg-theme/15 text-theme border-theme/20' : 'bg-dc-bg text-dc-text border-dc-border hover:text-white') +
        ' px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-widest transition-all border" onclick="TOC.matches.filterGroup(\'' + eg.replace(/'/g, "\\'") + '\')" role="radio" aria-checked="' + (activeGroupFilter === g ? 'true' : 'false') + '">' + eg + '</button>';
    });
    container.innerHTML = html;
  }

  function filterGroup(group) {
    activeGroupFilter = group;
    applyGroupFilter();
    populateGroupPills(allMatches);
  }

  function applyGroupFilter() {
    filteredMatches = activeGroupFilter
      ? allMatches.filter(function (m) { return m.group_label === activeGroupFilter; })
      : allMatches.slice();
    renderMatchList(filteredMatches);
    if (selectedMatchId && !filteredMatches.find(function (m) { return m.id === selectedMatchId; })) {
      clearDetail();
    }
  }

  /* --- Stats ----------------------------------------------- */
  function renderStats(matches) {
    var el = function (id, val) { var e = $('#matches-stat-' + id); if (e) e.textContent = val; };
    el('total', matches.length);
    el('live', matches.filter(function (m) { return m.state === 'live'; }).length);
    el('pending', matches.filter(function (m) { return m.state === 'pending_result'; }).length);
    el('completed', matches.filter(function (m) { return m.state === 'completed' || m.state === 'forfeit'; }).length);
    el('disputed', matches.filter(function (m) { return m.state === 'disputed'; }).length);
  }

  /* --- Round filter ---------------------------------------- */
  function populateRoundFilter(matches) {
    var sel = $('#match-filter-round');
    if (!sel) return;
    var roundSet = {};
    matches.forEach(function (m) { roundSet[m.round_number] = true; });
    var rounds = Object.keys(roundSet).map(Number).sort(function (a, b) { return a - b; });
    var current = sel.value;
    sel.innerHTML = '<option value="">All Rounds</option>' +
      rounds.map(function (r) { return '<option value="' + r + '"' + (String(r) === current ? ' selected' : '') + '>Round ' + r + '</option>'; }).join('');
  }

  /* ============================================================
     LEFT PANEL: Match List (redesigned cards)
  ============================================================ */
  function renderMatchList(matches) {
    var list = $('#match-list');
    if (!list) return;

    var countEl = $('#match-list-count');
    if (countEl) countEl.textContent = matches.length + ' match' + (matches.length !== 1 ? 'es' : '');

    if (!matches.length) {
      list.innerHTML =
        '<div class="flex items-center justify-center h-full min-h-[300px]">' +
        '<div class="text-center max-w-xs px-6">' +
        '<div class="w-16 h-16 rounded-2xl bg-dc-border/10 mx-auto mb-4 flex items-center justify-center">' +
        '<i data-lucide="swords" class="w-8 h-8 text-dc-border/50"></i></div>' +
        '<h3 class="text-sm font-bold text-dc-text/60 mb-2">No Matches Yet</h3>' +
        '<p class="text-xs text-dc-text/40 mb-5">Matches have not been generated for this tournament yet. Generate them here, then continue with scheduling.</p>' +
        '<div class="flex flex-col sm:flex-row items-center justify-center gap-2">' +
        '<button onclick="TOC.matches.generateMatchesFromEmptyState()" class="px-4 py-2 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">' +
        '<i data-lucide="swords" class="w-3.5 h-3.5 inline-block mr-1.5"></i>Generate Matches</button>' +
        '<button onclick="TOC.navigate && TOC.navigate(\'schedule\')" class="px-4 py-2 bg-theme/10 border border-theme/20 text-theme text-xs font-bold uppercase tracking-widest rounded-lg hover:bg-theme/20 transition-colors">' +
        '<i data-lucide="calendar" class="w-3.5 h-3.5 inline-block mr-1.5"></i>Go to Schedule</button>' +
        '</div>' +
        '</div></div>';
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    list.innerHTML = matches.map(function (m) {
      var sc = stateConfig[m.state] || stateConfig.scheduled;
      var isSelected = m.id === selectedMatchId;
      var isWinner1 = m.winner_id && m.winner_id === m.participant1_id;
      var isWinner2 = m.winner_id && m.winner_id === m.participant2_id;
      var liveDot = m.state === 'live' ? '<span class="w-2 h-2 rounded-full bg-dc-success animate-pulse inline-block"></span>' : '';
      var groupTag = m.group_label ? ' <span class="text-theme/70">&middot;</span> <span class="text-theme font-bold">' + esc(m.group_label) + '</span>' : '';
      var disputedBorder = m.state === 'disputed' ? ' ring-1 ring-dc-danger/30' : '';

      // Check-in dots
      var checkinHtml = '';
      if (m.state === 'check_in' || m.state === 'ready') {
        var c1 = m.participant1_checked_in ? 'bg-dc-success' : 'bg-dc-border';
        var c2 = m.participant2_checked_in ? 'bg-dc-success' : 'bg-dc-border';
        checkinHtml = '<span class="flex items-center gap-0.5 text-xs text-dc-text" title="Check-in: P1 ' + (m.participant1_checked_in ? '\u2713' : '\u2717') + ', P2 ' + (m.participant2_checked_in ? '\u2713' : '\u2717') + '">' +
          '<span class="w-1.5 h-1.5 rounded-full ' + c1 + '"></span>' +
          '<span class="w-1.5 h-1.5 rounded-full ' + c2 + '"></span></span>';
      }

      // Swiss round label + BO series vars for card display
      var isSwissRound = (window.TOC_CONFIG || {}).tournamentFormat === 'swiss';
      var roundPrefix = isSwissRound ? 'Swiss R' : 'R';
      var bestOf = m.best_of || 1;
      var rawGs = m.game_scores || [];
      if (typeof rawGs === 'string') { try { rawGs = JSON.parse(rawGs); } catch (_e) { rawGs = []; } }
      if (rawGs && typeof rawGs === 'object' && !Array.isArray(rawGs) && Array.isArray(rawGs.maps)) {
        rawGs = rawGs.maps.map(function(mp, i) {
          return { game: i+1, p1_score: mp.team1_rounds||0, p2_score: mp.team2_rounds||0, map_name: mp.map_name||'' };
        });
      }
      var gameScores = Array.isArray(rawGs) ? rawGs : [];
      var sp1 = 0; var sp2 = 0;
      gameScores.forEach(function(g) { if ((g.p1_score||0) > (g.p2_score||0)) sp1++; else if ((g.p2_score||0) > (g.p1_score||0)) sp2++; });
      var showSeries = bestOf > 1 && gameScores.length > 0;
      var scoreA = showSeries ? sp1 : (m.participant1_score != null ? m.participant1_score : '-');
      var scoreB = showSeries ? sp2 : (m.participant2_score != null ? m.participant2_score : '-');
      var boLabel = bestOf > 1 ? '<span class="text-[8px] font-mono text-dc-text/40">BO' + bestOf + '</span> ' : '';

      return '<div class="match-card px-4 py-3 cursor-pointer transition-all hover:bg-white/[0.03]' +
        (isSelected ? ' bg-theme/5 border-l-[3px] border-l-theme' : ' border-l-[3px] border-l-transparent') +
        disputedBorder +
        '" onclick="TOC.matches.selectMatch(' + m.id + ')" data-match-id="' + m.id + '"' +
        ' tabindex="0" role="option" aria-selected="' + (isSelected ? 'true' : 'false') + '"' +
        ' aria-label="Match ' + m.match_number + ': ' + esc(m.participant1_name || 'TBD') + ' vs ' + esc(m.participant2_name || 'TBD') + '">' +

        // Row 1: Round/match info + state badge
        '<div class="flex items-center justify-between mb-2">' +
        '<span class="text-xs font-mono text-dc-text">' + roundPrefix + m.round_number + ' &middot; #' + m.match_number + groupTag + '</span>' +
        '<div class="flex items-center gap-2">' + checkinHtml + liveDot +
        '<span class="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ' + sc.cls + '">' + sc.label + '</span>' +
        (m.is_paused ? '<span class="text-xs font-bold text-dc-warning" title="Paused">&#x23F8;</span>' : '') +
        '</div></div>' +

        // Row 2: Teams + score
        '<div class="flex items-center gap-3">' +
        '<span class="flex-1 text-right text-sm ' + (isWinner1 ? 'text-dc-success font-bold' : 'text-dc-textBright') + ' truncate">' + esc(m.participant1_name || 'TBD') + '</span>' +
        '<span class="font-mono font-black text-sm text-white px-3 py-1 rounded bg-dc-bg border border-dc-border min-w-[56px] text-center">' + boLabel + scoreA + ' \u2013 ' + scoreB + '</span>' +
        '<span class="flex-1 text-left text-sm ' + (isWinner2 ? 'text-dc-success font-bold' : 'text-dc-textBright') + ' truncate">' + esc(m.participant2_name || 'TBD') + '</span>' +
        '</div>' +

        // Row 3: Time info (if scheduled)
        (m.scheduled_time ? '<div class="mt-1.5 text-xs text-dc-text/50 font-mono text-center">' +
        '<i data-lucide="clock" class="w-3 h-3 inline-block mr-1"></i>' +
        new Date(m.scheduled_time).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) +
        '</div>' : '') +

        '</div>';
    }).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* ============================================================
     RIGHT PANEL: Match Detail
  ============================================================ */
  async function selectMatch(id) {
    selectedMatchId = id;

    // Highlight selected card in list
    $$('.match-card').forEach(function (el) {
      var mid = parseInt(el.dataset.matchId);
      if (mid === id) {
        el.classList.add('bg-theme/5', 'border-l-theme');
        el.classList.remove('border-l-transparent');
        el.setAttribute('aria-selected', 'true');
      } else {
        el.classList.remove('bg-theme/5', 'border-l-theme');
        el.classList.add('border-l-transparent');
        el.setAttribute('aria-selected', 'false');
      }
    });

    // Show detail content, hide empty state
    var empty = $('#match-detail-empty');
    var content = $('#match-detail-content');
    if (empty) empty.classList.add('hidden');
    if (content) content.classList.remove('hidden');

    // Render basic header from list data
    var m = allMatches.find(function (x) { return x.id === id; });
    if (m) {
      renderDetailHeader(m);
      updateMedicButtons(m);
    }

    // Fetch extended detail (timeline, evidence, submissions)
    try {
      var data = await API.get('matches/' + id + '/detail/');
      selectedMatchDetail = data;
      if (m) Object.assign(m, data.match || {});
      renderDetailHeader(data.match || m);
      renderScoreEditor(data.match || m, data.submissions || []);
      renderEvidence(data);
      renderAuditTrail(data);
      updateMedicButtons(data.match || m);
    } catch (e) {
      console.error('[matches] detail fetch error', e);
      toast('Failed to load match details', 'error');
      if (m) {
        renderScoreEditor(m, []);
        renderEvidence({ match: m, submissions: [], media: [] });
        renderAuditTrail({ match: m, notes: [], disputes: [], timeline: [] });
      }
    }
  }

  function clearDetail() {
    selectedMatchId = null;
    selectedMatchDetail = null;
    var empty = $('#match-detail-empty');
    var content = $('#match-detail-content');
    if (empty) empty.classList.remove('hidden');
    if (content) content.classList.add('hidden');
  }

  /* -- Detail Header -- */
  function renderDetailHeader(m) {
    if (!m) return;
    var sc = stateConfig[m.state] || stateConfig.scheduled;

    var matchIdEl = $('#detail-match-id');
    if (matchIdEl) matchIdEl.textContent = 'Match #' + m.match_number;

    var stateEl = $('#detail-match-state');
    if (stateEl) {
      stateEl.textContent = sc.label;
      stateEl.className = 'text-xs font-bold px-3 py-1 rounded-full uppercase tracking-widest border ' + sc.cls;
    }

    var teamA = $('#detail-team-a');
    if (teamA) teamA.textContent = m.participant1_name || 'TBD';

    var teamAMeta = $('#detail-team-a-meta');
    if (teamAMeta) teamAMeta.textContent = m.group_label ? m.group_label + ' | Seed ' + (m.participant1_seed || '-') : 'Seed ' + (m.participant1_seed || '-');

    var teamB = $('#detail-team-b');
    if (teamB) teamB.textContent = m.participant2_name || 'TBD';

    var teamBMeta = $('#detail-team-b-meta');
    if (teamBMeta) teamBMeta.textContent = m.group_label ? m.group_label + ' | Seed ' + (m.participant2_seed || '-') : 'Seed ' + (m.participant2_seed || '-');

    var scoreA = $('#detail-score-a');
    if (scoreA) scoreA.textContent = m.participant1_score != null ? m.participant1_score : '-';

    var scoreB = $('#detail-score-b');
    if (scoreB) scoreB.textContent = m.participant2_score != null ? m.participant2_score : '-';

    var roundEl = $('#detail-round');
    if (roundEl) roundEl.textContent = 'Round ' + m.round_number + (m.scheduled_time ? ' | ' + new Date(m.scheduled_time).toLocaleString() : '');

    renderAvatar('detail-avatar-a', m.participant1_avatar_url);
    renderAvatar('detail-avatar-b', m.participant2_avatar_url);

    // Lobby info row
    renderLobbyRow(m);

    // Check-in indicators
    renderCheckinIndicators(m);
  }

  function renderAvatar(containerId, url) {
    var el = $('#' + containerId);
    if (!el) return;
    if (url) {
      el.innerHTML = '<img src="' + esc(url) + '" alt="" class="w-full h-full object-cover">';
    } else {
      el.innerHTML = '<i data-lucide="user" class="w-5 h-5 text-dc-border"></i>';
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }
  }

  /* -- Lobby Info Row -- */
  function renderLobbyRow(m) {
    var row = $('#detail-lobby-row');
    if (!row) return;

    var li = m.lobby_info || {};
    var hasLobby = li.lobby_code || li.map || li.server;

    if (hasLobby || m.state === 'check_in' || m.state === 'ready' || m.state === 'live') {
      row.classList.remove('hidden');
    } else {
      row.classList.add('hidden');
      return;
    }

    // Lobby code
    var codeEl = $('#detail-lobby-code');
    if (codeEl) {
      if (li.lobby_code) {
        codeEl.classList.remove('hidden');
        var strong = codeEl.querySelector('strong');
        if (strong) strong.textContent = li.lobby_code;
      } else {
        codeEl.classList.add('hidden');
      }
    }

    // Map
    var mapEl = $('#detail-lobby-map');
    if (mapEl) {
      if (li.map) {
        mapEl.classList.remove('hidden');
        var span = mapEl.querySelector('span.text-dc-textBright');
        if (span) span.textContent = li.map;
      } else {
        mapEl.classList.add('hidden');
      }
    }

    // Server
    var serverEl = $('#detail-lobby-server');
    if (serverEl) {
      if (li.server) {
        serverEl.classList.remove('hidden');
        var sSpan = serverEl.querySelector('span.text-dc-textBright');
        if (sSpan) sSpan.textContent = li.server;
      } else {
        serverEl.classList.add('hidden');
      }
    }

    // Match room link
    var roomLink = $('#detail-room-link');
    if (roomLink) {
      roomLink.href = '/tournaments/' + slug + '/matches/' + m.id + '/room/';
      roomLink.classList.remove('hidden');
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* -- Check-in Indicators -- */
  function renderCheckinIndicators(m) {
    var p1El = $('#detail-checkin-p1');
    var p2El = $('#detail-checkin-p2');
    if (!p1El || !p2El) return;

    var dot1 = p1El.querySelector('span.rounded-full');
    var dot2 = p2El.querySelector('span.rounded-full');

    if (dot1) {
      dot1.className = 'w-2 h-2 rounded-full ' + (m.participant1_checked_in ? 'bg-dc-success' : 'bg-dc-border');
    }
    if (dot2) {
      dot2.className = 'w-2 h-2 rounded-full ' + (m.participant2_checked_in ? 'bg-dc-success' : 'bg-dc-border');
    }

    // Deadline countdown
    if (m.check_in_deadline && (m.state === 'check_in')) {
      var deadline = new Date(m.check_in_deadline);
      var now = new Date();
      var diff = Math.max(0, Math.round((deadline - now) / 1000 / 60));
      p1El.title = 'Check-in deadline: ' + diff + 'min remaining';
      p2El.title = p1El.title;
    }
  }

  /* -- Copy Lobby Code -- */
  function copyLobbyCode() {
    var m = allMatches.find(function (x) { return x.id === selectedMatchId; });
    if (!m || !m.lobby_info?.lobby_code) return;
    navigator.clipboard.writeText(m.lobby_info.lobby_code).then(function () {
      toast('Lobby code copied', 'success');
    });
  }

  /* -- Medic Buttons -- */
  function updateMedicButtons(m) {
    if (!m) return;
    var btnLive = $('#btn-medic-live');
    var btnPause = $('#btn-medic-pause');
    var btnResume = $('#btn-medic-resume');
    var btnForce = $('#btn-medic-force');

    [btnLive, btnPause, btnResume, btnForce].forEach(function (b) { if (b) b.classList.add('hidden'); });

    if (['scheduled', 'check_in', 'ready'].includes(m.state)) {
      if (btnLive) btnLive.classList.remove('hidden');
    }
    if (m.state === 'live' && !m.is_paused) {
      if (btnPause) btnPause.classList.remove('hidden');
      if (btnForce) btnForce.classList.remove('hidden');
    }
    if (m.state === 'live' && m.is_paused) {
      if (btnResume) btnResume.classList.remove('hidden');
      if (btnForce) btnForce.classList.remove('hidden');
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* -- Score Editor Tab -- */
  function renderScoreEditor(m, submissions) {
    var labelA = $('#score-label-a');
    var labelB = $('#score-label-b');
    var inputA = $('#score-input-a');
    var inputB = $('#score-input-b');
    var winnerA = $('#winner-opt-a');
    var winnerB = $('#winner-opt-b');
    var winSel = $('#score-winner');

    if (labelA) labelA.textContent = m.participant1_name || 'Team A';
    if (labelB) labelB.textContent = m.participant2_name || 'Team B';
    if (inputA) inputA.value = m.participant1_score || 0;
    if (inputB) inputB.value = m.participant2_score || 0;
    if (winnerA) winnerA.textContent = m.participant1_name || 'Team A';
    if (winnerB) winnerB.textContent = m.participant2_name || 'Team B';
    if (winSel) winSel.value = '';
    var noteEl = $('#score-note');
    if (noteEl) noteEl.value = '';

    // Render series UI
    renderSeriesPanel(m);
  }

  /* -- Series Panel (BO3/BO5) -- */
  function renderSeriesPanel(m) {
    var bestOf = (m && m.best_of) || 1;
    var _rawGs2 = (m && m.game_scores) || [];
    if (typeof _rawGs2 === 'string') { try { _rawGs2 = JSON.parse(_rawGs2); } catch (_e) { _rawGs2 = []; } }
    if (_rawGs2 && typeof _rawGs2 === 'object' && !Array.isArray(_rawGs2) && Array.isArray(_rawGs2.maps)) {
      _rawGs2 = _rawGs2.maps.map(function(mp, i) {
        return { game: i+1, p1_score: mp.team1_rounds||0, p2_score: mp.team2_rounds||0, map_name: mp.map_name||'' };
      });
    }
    var games = Array.isArray(_rawGs2) ? _rawGs2 : [];

    // Update BO buttons
    [1, 3, 5].forEach(function (bo) {
      var btn = $('#bo-btn-' + bo);
      if (!btn) return;
      if (bo === bestOf) {
        btn.classList.add('border-theme', 'text-theme', 'bg-theme/10');
        btn.classList.remove('border-dc-border', 'text-dc-text', 'bg-dc-surface');
      } else {
        btn.classList.remove('border-theme', 'text-theme', 'bg-theme/10');
        btn.classList.add('border-dc-border', 'text-dc-text', 'bg-dc-surface');
      }
    });

    var scorecard = $('#series-scorecard');
    var bo1Inputs = $('#bo1-score-inputs');
    var progressLabel = $('#series-progress-label');

    if (bestOf === 1) {
      if (scorecard) scorecard.classList.add('hidden');
      if (bo1Inputs) bo1Inputs.classList.remove('hidden');
      if (progressLabel) progressLabel.classList.add('hidden');
      return;
    }

    // BO3 or BO5
    if (scorecard) scorecard.classList.remove('hidden');
    if (bo1Inputs) bo1Inputs.classList.add('hidden');

    var winsNeeded = Math.floor(bestOf / 2) + 1;
    var p1Wins = games.filter(function (g) { return g.winner_slot === 1; }).length;
    var p2Wins = games.filter(function (g) { return g.winner_slot === 2; }).length;

    if (progressLabel) {
      progressLabel.classList.remove('hidden');
      progressLabel.textContent = 'BO' + bestOf + ' | ' + p1Wins + '–' + p2Wins;
    }

    var gamesList = $('#series-games-list');
    if (!gamesList) return;

    if (!games.length) {
      gamesList.innerHTML = '<p class="text-xs text-dc-text/50 text-center py-2">No games recorded yet</p>';
      return;
    }

    var p1Name = (m && m.participant1_name) || 'Team A';
    var p2Name = (m && m.participant2_name) || 'Team B';

    gamesList.innerHTML = games.map(function (g) {
      var w1 = g.winner_slot === 1;
      var w2 = g.winner_slot === 2;
      return '<div class="flex items-center gap-3 px-3 py-2 rounded-lg bg-dc-bg border border-dc-border/40">' +
        '<span class="text-xs text-dc-text/50 font-mono w-12 shrink-0">G' + g.game + '</span>' +
        '<span class="flex-1 text-right text-xs ' + (w1 ? 'text-dc-success font-bold' : 'text-dc-textBright') + ' truncate">' + esc(p1Name) + '</span>' +
        '<span class="font-mono font-black text-sm text-white px-3 py-0.5 rounded bg-dc-panel border border-dc-border">' + g.p1 + ' – ' + g.p2 + '</span>' +
        '<span class="flex-1 text-left text-xs ' + (w2 ? 'text-dc-success font-bold' : 'text-dc-textBright') + ' truncate">' + esc(p2Name) + '</span>' +
        '</div>';
    }).join('');
  }

  async function setBestOf(bo) {
    if (!selectedMatchId) return;
    try {
      await API('matches/' + selectedMatchId + '/series/', { method: 'PATCH', body: JSON.stringify({ best_of: bo }), headers: { 'Content-Type': 'application/json' } });
      var m = allMatches.find(function (x) { return x.id === selectedMatchId; });
      if (m) { m.best_of = bo; renderSeriesPanel(m); }
      toast('Series format set to BO' + bo, 'success');
    } catch (e) { toast(e.message || 'Failed to set format', 'error'); }
  }

  function openAddGameScore() {
    if (!selectedMatchId) return;
    var m = allMatches.find(function (x) { return x.id === selectedMatchId; });
    var _rawGs3 = (m && m.game_scores) || [];
    if (typeof _rawGs3 === 'string') { try { _rawGs3 = JSON.parse(_rawGs3); } catch (_e) { _rawGs3 = []; } }
    if (_rawGs3 && typeof _rawGs3 === 'object' && !Array.isArray(_rawGs3) && Array.isArray(_rawGs3.maps)) {
      _rawGs3 = _rawGs3.maps.map(function(mp, i) {
        return { game: i+1, p1_score: mp.team1_rounds||0, p2_score: mp.team2_rounds||0, map_name: mp.map_name||'' };
      });
    }
    var games = Array.isArray(_rawGs3) ? _rawGs3 : [];
    var nextGame = games.length + 1;
    var p1Name = (m && m.participant1_name) || 'Team A';
    var p2Name = (m && m.participant2_name) || 'Team B';

    var html = '<div class="bg-dc-panel border border-dc-border rounded-xl p-6 max-w-sm w-full mx-4 space-y-4">' +
      '<h3 class="text-base font-bold text-white">Record Game ' + nextGame + '</h3>' +
      '<div class="grid grid-cols-2 gap-3">' +
      '<div><label class="text-xs text-dc-text uppercase tracking-widest block mb-1.5">' + esc(p1Name) + '</label>' +
      '<input id="add-game-p1" type="number" min="0" value="0" class="w-full bg-dc-bg border border-dc-border text-white text-2xl font-mono text-center rounded-lg px-3 py-3 focus:border-theme outline-none"></div>' +
      '<div><label class="text-xs text-dc-text uppercase tracking-widest block mb-1.5">' + esc(p2Name) + '</label>' +
      '<input id="add-game-p2" type="number" min="0" value="0" class="w-full bg-dc-bg border border-dc-border text-white text-2xl font-mono text-center rounded-lg px-3 py-3 focus:border-theme outline-none"></div>' +
      '</div>' +
      '<div class="flex gap-2 pt-2">' +
      '<button onclick="TOC.matches.confirmAddGameScore(' + nextGame + ')" class="flex-1 py-2.5 bg-dc-success/10 border border-dc-success/20 text-dc-success text-xs font-bold rounded-lg hover:bg-dc-success/20 transition-colors">Save Game ' + nextGame + '</button>' +
      '<button onclick="TOC.matches.closeGameScoreModal()" class="px-4 py-2.5 bg-dc-panel border border-dc-border text-dc-text text-xs font-bold rounded-lg hover:bg-white/5 transition-colors">Cancel</button>' +
      '</div></div>';

    var backdrop = document.createElement('div');
    backdrop.id = 'game-score-modal';
    backdrop.className = 'fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-sm';
    backdrop.innerHTML = html;
    backdrop.addEventListener('click', function (e) { if (e.target === backdrop) closeGameScoreModal(); });
    document.body.appendChild(backdrop);
    setTimeout(function () { var inp = document.getElementById('add-game-p1'); if (inp) inp.focus(); }, 50);
  }

  function closeGameScoreModal() {
    var el = document.getElementById('game-score-modal');
    if (el) el.remove();
  }

  async function confirmAddGameScore(gameNumber) {
    var p1Input = document.getElementById('add-game-p1');
    var p2Input = document.getElementById('add-game-p2');
    if (!p1Input || !p2Input) return;
    var p1 = parseInt(p1Input.value, 10) || 0;
    var p2 = parseInt(p2Input.value, 10) || 0;
    if (p1 === p2) { toast('Game cannot end in a tie', 'error'); return; }
    closeGameScoreModal();
    try {
      var result = await API('matches/' + selectedMatchId + '/series/game/', {
        method: 'POST',
        body: JSON.stringify({ game_number: gameNumber, participant1_score: p1, participant2_score: p2 }),
        headers: { 'Content-Type': 'application/json' }
      });
      var m = allMatches.find(function (x) { return x.id === selectedMatchId; });
      if (m) {
        m.best_of = result.best_of;
        m.game_scores = result.games;
        m.participant1_score = result.p1_wins;
        m.participant2_score = result.p2_wins;
        renderSeriesPanel(m);
        renderDetailHeader(m);
      }
      if (result.is_complete) {
        toast('Series complete! Refreshing…', 'success');
        await refresh();
        selectMatch(selectedMatchId);
      } else {
        toast('Game ' + gameNumber + ' recorded', 'success');
      }
    } catch (e) { toast(e.message || 'Failed to record game', 'error'); }
  }

  /* -- Evidence Viewer Tab -- */
  function renderEvidence(data) {
    var container = $('#evidence-container');
    var split = $('#evidence-split');
    var mismatch = $('#evidence-mismatch');
    if (!container) return;

    var subs = data.submissions || [];
    var media = (data.media || []).filter(function (x) { return x.is_evidence; });
    var vs = data.verification_status;

    if (subs.length === 0 && media.length === 0) {
      container.innerHTML = '<div class="text-center py-8">' +
        '<i data-lucide="image-off" class="w-10 h-10 text-dc-border mx-auto mb-2"></i>' +
        '<p class="text-sm text-dc-text/50">No evidence submitted yet</p></div>';
      if (split) split.classList.add('hidden');
      if (mismatch) mismatch.classList.add('hidden');
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    container.innerHTML = subs.map(function (s, idx) {
      var statusCls = (s.status === 'confirmed' || s.status === 'finalized') ? 'bg-dc-success/20 text-dc-success' :
        s.status === 'disputed' ? 'bg-dc-danger/20 text-dc-danger' : 'bg-dc-warning/20 text-dc-warning';
      return '<div class="flex items-center gap-3 p-3 rounded-lg ' +
        (idx === 0 ? 'bg-blue-500/5 border border-blue-500/20' : 'bg-purple-500/5 border border-purple-500/20') + '">' +
        '<span class="text-xs font-bold uppercase tracking-widest ' +
        (idx === 0 ? 'text-blue-400' : 'text-purple-400') + ' w-16 shrink-0">' +
        (s.submitted_by_team_id ? (idx === 0 ? 'Capt. A' : 'Capt. B') : esc(s.submitted_by_name || 'Sub ' + (idx + 1))) + '</span>' +
        '<span class="font-mono font-black text-white text-base flex-1 text-center">' +
        ((s.raw_result_payload && s.raw_result_payload.score_p1 != null) ? s.raw_result_payload.score_p1 : '-') +
        ' - ' +
        ((s.raw_result_payload && s.raw_result_payload.score_p2 != null) ? s.raw_result_payload.score_p2 : '-') +
        '</span>' +
        '<span class="text-[11px] px-2 py-0.5 rounded font-bold uppercase tracking-wider ' + statusCls + '">' + esc(s.status) + '</span></div>';
    }).join('');

    if (split) {
      var imgA = (subs[0] && subs[0].proof_screenshot_url) || (media[0] && media[0].url);
      var imgB = (subs[1] && subs[1].proof_screenshot_url) || (media[1] && media[1].url);
      if (imgA || imgB) {
        split.classList.remove('hidden');
        var eA = $('#evidence-img-a');
        var eB = $('#evidence-img-b');
        if (eA) eA.innerHTML = imgA ? '<img src="' + esc(imgA) + '" class="w-full h-full object-contain" alt="Evidence A">' : '<i data-lucide="image" class="w-8 h-8 text-dc-border"></i>';
        if (eB) eB.innerHTML = imgB ? '<img src="' + esc(imgB) + '" class="w-full h-full object-contain" alt="Evidence B">' : '<i data-lucide="image" class="w-8 h-8 text-dc-border"></i>';
      } else {
        split.classList.add('hidden');
      }
    }

    if (mismatch && vs) {
      if (vs.code === 'mismatch') {
        mismatch.classList.remove('hidden');
        var detail = $('#evidence-mismatch-detail');
        if (detail) detail.textContent = vs.detail || 'Scores do not match between submissions';
      } else {
        mismatch.classList.add('hidden');
      }
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* -- Audit Trail Tab -- */
  function renderAuditTrail(data) {
    var container = $('#audit-trail');
    if (!container) return;

    var timeline = data.timeline || [];
    var notes = data.notes || [];
    var disputes = data.disputes || [];

    var entries = [];
    timeline.forEach(function (t) { entries.push({ time: t.created_at, type: 'event', icon: 'activity', color: 'text-theme', text: t.description || t.action }); });
    notes.forEach(function (n) { entries.push({ time: n.created_at, type: 'note', icon: 'message-square', color: 'text-dc-info', text: n.text, by: n.author || ('User #' + (n.user_id || '?')) }); });
    disputes.forEach(function (d) { entries.push({ time: d.opened_at || d.created_at, type: 'dispute', icon: 'flag', color: 'text-dc-danger', text: (d.reason_code || 'dispute') + ': ' + (d.description || ''), by: d.opened_by_name || d.filed_by }); });

    entries.sort(function (a, b) { return new Date(b.time) - new Date(a.time); });

    if (!entries.length) {
      container.innerHTML = '<div class="flex items-center justify-center py-10"><p class="text-sm text-dc-text/50 font-mono">No audit entries</p></div>';
      return;
    }

    container.innerHTML = entries.map(function (e) {
      return '<div class="flex gap-3 px-4 py-3">' +
        '<div class="w-7 h-7 rounded-full bg-dc-bg border border-dc-border flex items-center justify-center shrink-0 mt-0.5">' +
        '<i data-lucide="' + e.icon + '" class="w-3.5 h-3.5 ' + e.color + '"></i></div>' +
        '<div class="flex-1 min-w-0">' +
        '<p class="text-sm text-dc-textBright">' + esc(e.text) + '</p>' +
        '<div class="flex items-center gap-2 mt-0.5">' +
        '<span class="text-xs text-dc-text font-mono">' + (e.time ? new Date(e.time).toLocaleString() : '') + '</span>' +
        (e.by ? '<span class="text-xs text-dc-text">&middot; ' + esc(e.by) + '</span>' : '') +
        '</div></div></div>';
    }).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* -- Detail Tab Switcher -- */
  function switchDetailTab(tab) {
    $$('.detail-tab').forEach(function (el) {
      var t = el.dataset.detailTab;
      if (t === tab) {
        el.classList.add('active', 'text-theme', 'border-b-theme');
        el.classList.remove('text-dc-text', 'border-transparent');
        el.setAttribute('aria-selected', 'true');
      } else {
        el.classList.remove('active', 'text-theme', 'border-b-theme');
        el.classList.add('text-dc-text', 'border-transparent');
        el.setAttribute('aria-selected', 'false');
      }
    });
    $$('.detail-tab-content').forEach(function (el) { el.classList.add('hidden'); });
    var target = $('#detail-tab-' + tab);
    if (target) target.classList.remove('hidden');
    if (tab === 'veto') loadVetoTab();
  }

  /* ============================================================
     ACTIONS -- Medic + Score + Dispute + Reset
  ============================================================ */
  async function markLive(id) {
    var matchId = id || selectedMatchId;
    if (!matchId) return;
    try { await API.post('matches/' + matchId + '/mark-live/'); toast('Match started', 'success'); refresh(); selectMatch(matchId); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  async function pause(id) {
    var matchId = id || selectedMatchId;
    if (!matchId) return;
    try { await API.post('matches/' + matchId + '/pause/'); toast('Match paused', 'info'); refresh(); selectMatch(matchId); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  async function resume(id) {
    var matchId = id || selectedMatchId;
    if (!matchId) return;
    try { await API.post('matches/' + matchId + '/resume/'); toast('Match resumed', 'success'); refresh(); selectMatch(matchId); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  function forceComplete(id) {
    var matchId = id || selectedMatchId;
    if (!matchId) return;
    TOC.dangerConfirm({
      title: 'Force-Complete Match',
      message: 'The match outcome will be finalized immediately. This cannot be undone.',
      confirmText: 'Force Complete',
      onConfirm: async function () {
        try { await API.post('matches/' + matchId + '/force-complete/'); toast('Match force-completed', 'info'); refresh(); selectMatch(matchId); }
        catch (e) { toast(e.message || 'Failed', 'error'); }
      },
    });
  }

  async function submitScore() {
    if (!selectedMatchId) { toast('No match selected', 'error'); return; }
    var p1 = parseInt($('#score-input-a')?.value) || 0;
    var p2 = parseInt($('#score-input-b')?.value) || 0;
    var winner = $('#score-winner')?.value || '';
    var note = $('#score-note')?.value || '';

    var body = { participant1_score: p1, participant2_score: p2 };
    if (winner) body.winner_side = winner;
    if (note) body.admin_note = note;

    try {
      await API.post('matches/' + selectedMatchId + '/score/', body);
      toast('Score submitted', 'success');
      refresh();
      selectMatch(selectedMatchId);
    } catch (e) {
      toast(e.message || 'Failed to submit score', 'error');
    }
  }

  /* -- Dispute Modal (replaces prompt()) -- */
  function openDispute() {
    if (!selectedMatchId) { toast('No match selected', 'error'); return; }
    var modal = $('#dispute-modal');
    if (modal) {
      modal.classList.remove('hidden');
      var desc = $('#dispute-description');
      if (desc) { desc.value = ''; desc.focus(); }
      var code = $('#dispute-reason-code');
      if (code) code.value = 'score_mismatch';
    }
  }

  function closeDisputeModal() {
    var modal = $('#dispute-modal');
    if (modal) modal.classList.add('hidden');
  }

  async function confirmDispute() {
    if (!selectedMatchId) return;
    var reasonCode = $('#dispute-reason-code')?.value || 'other';
    var description = $('#dispute-description')?.value || '';
    if (!description.trim()) { toast('Please describe the issue', 'error'); return; }

    try {
      await API.post('matches/' + selectedMatchId + '/verify/', {
        action: 'dispute',
        reason_code: reasonCode,
        notes: description,
        participant1_score: parseInt($('#score-input-a')?.value) || 0,
        participant2_score: parseInt($('#score-input-b')?.value) || 0,
      });
      toast('Dispute opened', 'warning');
      closeDisputeModal();
      refresh();
      selectMatch(selectedMatchId);
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  function resetMatch() {
    if (!selectedMatchId) { toast('No match selected', 'error'); return; }
    var matchId = selectedMatchId;
    TOC.dangerConfirm({
      title: 'Reset Match',
      message: 'Scores and match state will be cleared completely. This cannot be undone.',
      confirmText: 'Reset Match',
      onConfirm: async function () {
        try {
          await API.post('matches/' + matchId + '/reset/');
          toast('Match reset', 'info');
          refresh();
          selectMatch(matchId);
        } catch (e) { toast(e.message || 'Failed', 'error'); }
      },
    });
  }

  /* ============================================================
     LOBBY EDITOR
  ============================================================ */
  function openLobbyEditor() {
    if (!selectedMatchId) { toast('No match selected', 'error'); return; }
    var m = allMatches.find(function (x) { return x.id === selectedMatchId; });
    var li = (m && m.lobby_info) || {};

    var modal = $('#lobby-editor-modal');
    if (!modal) return;

    var codeInput = $('#lobby-code-input');
    var passInput = $('#lobby-password-input');
    var mapInput = $('#lobby-map-input');
    var serverInput = $('#lobby-server-input');
    var gmInput = $('#lobby-gamemode-input');

    if (codeInput) codeInput.value = li.lobby_code || '';
    if (passInput) passInput.value = li.password || '';
    if (mapInput) mapInput.value = li.map || '';
    if (serverInput) serverInput.value = li.server || '';
    if (gmInput) gmInput.value = li.game_mode || '';

    modal.classList.remove('hidden');
    if (codeInput) codeInput.focus();
  }

  function closeLobbyEditor() {
    var modal = $('#lobby-editor-modal');
    if (modal) modal.classList.add('hidden');
  }

  async function saveLobbyInfo() {
    if (!selectedMatchId) return;
    var lobbyData = {
      lobby_code: $('#lobby-code-input')?.value || '',
      password: $('#lobby-password-input')?.value || '',
      map: $('#lobby-map-input')?.value || '',
      server: $('#lobby-server-input')?.value || '',
      game_mode: $('#lobby-gamemode-input')?.value || '',
    };

    try {
      await API.post('matches/' + selectedMatchId + '/add-note/', {
        text: '[LOBBY_UPDATE] ' + JSON.stringify(lobbyData),
      });
      toast('Lobby info saved', 'success');
      closeLobbyEditor();
      refresh();
      selectMatch(selectedMatchId);
    } catch (e) { toast(e.message || 'Failed to save lobby info', 'error'); }
  }

  /* --- Legacy overlay bridges (reschedule, forfeit) --------- */
  function openScoreDrawer(id) { selectMatch(id); switchDetailTab('score'); }
  function openDetailDrawer(id) { selectMatch(id); }

  function openRescheduleModal(id) {
    var mid = id || selectedMatchId;
    var m = allMatches.find(function (x) { return x.id === mid; });
    if (!m) return;
    var html = '<div class="p-6 space-y-4">' +
      '<h3 class="font-display font-black text-lg text-white">Reschedule Match #' + m.match_number + '</h3>' +
      '<div><label class="text-xs font-bold text-dc-text uppercase tracking-widest block mb-1.5">New Time</label>' +
      '<input id="rs-time" type="datetime-local" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-sm focus:border-theme outline-none"></div>' +
      '<div><label class="text-xs font-bold text-dc-text uppercase tracking-widest block mb-1.5">Reason</label>' +
      '<textarea id="rs-reason" rows="2" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-sm focus:border-theme outline-none resize-none" placeholder="Optional reason..."></textarea></div>' +
      '<button onclick="TOC.matches.confirmReschedule(' + mid + ')" class="w-full py-3 bg-dc-warning text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Request Reschedule</button></div>';
    showOverlay('reschedule-overlay', html);
  }

  async function confirmReschedule(id) {
    var time = $('#rs-time')?.value;
    if (!time) { toast('Time required', 'error'); return; }
    try {
      await API.post('matches/' + id + '/reschedule/', {
        new_time: new Date(time).toISOString(),
        reason: $('#rs-reason')?.value || '',
      });
      toast('Reschedule requested', 'success');
      closeOverlay('reschedule-overlay');
      refresh();
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  function openForfeit(id) {
    var mid = id || selectedMatchId;
    var m = allMatches.find(function (x) { return x.id === mid; });
    if (!m) return;
    var html = '<div class="p-6 space-y-4">' +
      '<h3 class="font-display font-black text-lg text-white">Declare Forfeit</h3>' +
      '<p class="text-sm text-dc-text">Select which participant is forfeiting:</p>' +
      '<div class="grid grid-cols-2 gap-3">' +
      '<button onclick="TOC.matches.confirmForfeit(' + mid + ', ' + m.participant1_id + ')" class="py-3 bg-dc-danger/10 border border-dc-danger/30 text-dc-danger text-sm font-bold rounded-lg hover:bg-dc-danger/20 transition-colors">' + esc(m.participant1_name || 'Team A') + '</button>' +
      '<button onclick="TOC.matches.confirmForfeit(' + mid + ', ' + m.participant2_id + ')" class="py-3 bg-dc-danger/10 border border-dc-danger/30 text-dc-danger text-sm font-bold rounded-lg hover:bg-dc-danger/20 transition-colors">' + esc(m.participant2_name || 'Team B') + '</button>' +
      '</div></div>';
    showOverlay('forfeit-overlay', html);
  }

  async function confirmForfeit(matchId, forfeiterId) {
    try {
      await API.post('matches/' + matchId + '/forfeit/', { forfeiter_id: forfeiterId });
      toast('Forfeit declared', 'info');
      closeOverlay('forfeit-overlay');
      refresh();
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  /* ============================================================
     Sprint 9: Full-screen Verification Overlay
  ============================================================ */
  var _verifyDetail = null;
  var _evidenceIndex = 0;
  var _zoomScale = 1;
  var _panX = 0, _panY = 0;
  var _isPanning = false, _panStartX = 0, _panStartY = 0;

  async function openVerifyScreen(id) {
    var mid = id || selectedMatchId;
    if (!mid) return;
    try {
      var data = await API.get('matches/' + mid + '/detail/');
      _verifyDetail = data;
      _evidenceIndex = 0;
      _zoomScale = 1;
      _panX = 0; _panY = 0;
      renderVerifyScreen(mid, data);
    } catch (e) {
      toast(e.message || 'Failed to load match detail', 'error');
    }
  }

  function renderVerifyScreen(id, data) {
    var m = data.match;
    var vs = data.verification_status || {};
    var subs = data.submissions || [];
    var media = data.media || [];
    var sc = stateConfig[m.state] || stateConfig.scheduled;

    var evidenceSources = [];
    subs.forEach(function (s, idx) {
      if (s.proof_screenshot_url) {
        evidenceSources.push({
          label: s.submitted_by_team_id ? ('Team ' + (idx === 0 ? 'A' : 'B')) : (s.submitted_by_name || 'Sub ' + (idx + 1)),
          url: s.proof_screenshot_url,
          notes: s.submitter_notes,
        });
      }
    });
    media.filter(function (x) { return x.is_evidence; }).forEach(function (x) {
      evidenceSources.push({ label: x.description || x.media_type, url: x.url });
    });

    var bannerMap = {
      match: { icon: '\u{1F7E2}', cls: 'bg-dc-success/10 border-dc-success/30 text-dc-success' },
      mismatch: { icon: '\u{1F534}', cls: 'bg-dc-danger/10 border-dc-danger/30 text-dc-danger' },
      pending: { icon: '\u{1F7E1}', cls: 'bg-dc-warning/10 border-dc-warning/30 text-dc-warning' },
      finalized: { icon: '\u2705', cls: 'bg-dc-text/10 border-dc-border text-dc-textBright' },
    };
    var b = bannerMap[vs.code] || bannerMap.pending;
    var sub0 = (subs[0] && subs[0].raw_result_payload) || {};

    var evTabsHtml = '';
    if (evidenceSources.length > 1) {
      evTabsHtml = '<div class="flex items-center gap-1 ml-3">';
      evidenceSources.forEach(function (ev, i) {
        evTabsHtml += '<button onclick="TOC.matches.switchEvidence(' + i + ')" class="px-2.5 py-1 rounded text-xs font-bold transition-colors ' +
          (i === 0 ? 'bg-theme text-dc-bg' : 'bg-dc-bg border border-dc-border text-dc-text hover:text-white') +
          '" id="ev-tab-' + i + '">' + esc(ev.label) + '</button>';
      });
      evTabsHtml += '</div>';
    }

    var subsHtml = '';
    if (subs.length > 0) {
      subs.forEach(function (s, idx) {
        var sCls = (s.status === 'confirmed' || s.status === 'finalized') ? 'bg-dc-success/20 text-dc-success' :
          s.status === 'disputed' ? 'bg-dc-danger/20 text-dc-danger' : 'bg-dc-warning/20 text-dc-warning';
        subsHtml += '<div class="flex items-center gap-3 p-3 rounded-lg ' +
          (idx === 0 ? 'bg-blue-500/5 border border-blue-500/20' : 'bg-purple-500/5 border border-purple-500/20') + '">' +
          '<span class="text-xs font-bold uppercase tracking-widest ' +
          (idx === 0 ? 'text-blue-400' : 'text-purple-400') + ' w-16">' +
          (s.submitted_by_team_id ? (idx === 0 ? 'Capt. A' : 'Capt. B') : esc(s.submitted_by_name || 'Unknown')) + '</span>' +
          '<span class="font-mono font-black text-white text-base flex-1 text-center">' +
          ((s.raw_result_payload && s.raw_result_payload.score_p1 != null) ? s.raw_result_payload.score_p1 : '-') + ' - ' +
          ((s.raw_result_payload && s.raw_result_payload.score_p2 != null) ? s.raw_result_payload.score_p2 : '-') + '</span>' +
          '<span class="text-[11px] px-2 py-0.5 rounded font-bold uppercase tracking-wider ' + sCls + '">' + esc(s.status) + '</span></div>';
      });
    } else {
      subsHtml = '<p class="text-xs text-dc-text text-center py-2">No submissions yet</p>';
    }

    var evidenceHtml;
    if (evidenceSources.length > 0) {
      evidenceHtml = '<img id="evidence-img" src="' + esc(evidenceSources[0].url) + '" alt="Evidence" class="max-w-none select-none" draggable="false" style="transform: scale(1) translate(0px, 0px); transition: transform 0.15s ease;" onerror="this.style.display=\'none\'; document.getElementById(\'evidence-fallback\').style.display=\'flex\';">' +
        '<div id="evidence-fallback" class="hidden absolute inset-0 flex-col items-center justify-center text-dc-text gap-2"><i data-lucide="image-off" class="w-8 h-8 opacity-30"></i><span class="text-sm">Failed to load</span></div>';
    } else {
      evidenceHtml = '<div class="flex flex-col items-center justify-center text-dc-text gap-2"><i data-lucide="image-off" class="w-8 h-8 opacity-30"></i><span class="text-sm">No evidence submitted</span></div>';
    }

    var html = '<div class="flex flex-col h-full max-h-[90vh]">' +
      '<div class="flex items-center justify-between p-4 border-b border-dc-borderLight bg-dc-panel/80">' +
      '<div class="flex items-center gap-3"><div class="w-8 h-8 rounded-lg bg-theme/20 flex items-center justify-center"><i data-lucide="shield-check" class="w-4 h-4 text-theme"></i></div>' +
      '<div><h3 class="font-display font-black text-white text-sm">R' + m.round_number + ' Match #' + m.match_number + ' &mdash; Verification</h3>' +
      '<p class="text-xs text-dc-text">' + esc(m.participant1_name || 'TBD') + ' vs ' + esc(m.participant2_name || 'TBD') + '</p></div></div>' +
      '<div class="flex items-center gap-2"><span class="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border ' + sc.cls + '">' + sc.label + '</span>' +
      '<button onclick="TOC.matches.closeOverlay(\'verify-overlay\')" class="w-8 h-8 rounded-lg bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="x" class="w-4 h-4 text-dc-text"></i></button></div></div>' +
      '<div class="mx-4 mt-4 p-3 rounded-lg border ' + b.cls + ' flex items-center gap-2"><span class="text-base">' + b.icon + '</span><div>' +
      '<span class="text-xs font-black uppercase tracking-widest">' + esc(vs.label || 'Pending') + '</span>' +
      '<span class="text-xs ml-2 opacity-80">' + esc(vs.detail || '') + '</span></div></div>' +
      '<div class="flex flex-1 overflow-hidden mt-4 mx-4 mb-4 gap-4" style="min-height:0">' +
      '<div class="flex-1 flex flex-col bg-dc-bg border border-dc-border rounded-xl overflow-hidden">' +
      '<div class="flex items-center justify-between p-3 border-b border-dc-border bg-dc-panel/50"><div class="flex items-center gap-2">' +
      '<i data-lucide="image" class="w-3.5 h-3.5 text-theme"></i><span class="text-xs font-bold text-white uppercase tracking-widest">Evidence Viewer</span>' + evTabsHtml + '</div>' +
      '<div class="flex items-center gap-1">' +
      '<button onclick="TOC.matches.zoomEvidence(-1)" class="w-7 h-7 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="zoom-out" class="w-3.5 h-3.5 text-dc-text"></i></button>' +
      '<span id="verify-zoom-level" class="text-xs font-mono text-dc-text w-12 text-center">100%</span>' +
      '<button onclick="TOC.matches.zoomEvidence(1)" class="w-7 h-7 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="zoom-in" class="w-3.5 h-3.5 text-dc-text"></i></button>' +
      '<button onclick="TOC.matches.resetZoom()" class="w-7 h-7 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="maximize-2" class="w-3.5 h-3.5 text-dc-text"></i></button></div></div>' +
      '<div id="evidence-canvas" class="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing flex items-center justify-center bg-black/40" onmousedown="TOC.matches.startPan(event)" onmousemove="TOC.matches.doPan(event)" onmouseup="TOC.matches.endPan()" onmouseleave="TOC.matches.endPan()" onwheel="TOC.matches.wheelZoom(event)" ontouchstart="TOC.matches.startTouch(event)" ontouchmove="TOC.matches.doTouch(event)" ontouchend="TOC.matches.endPan()">' +
      evidenceHtml + '</div></div>' +
      '<div class="w-[380px] flex-shrink-0 flex flex-col gap-4 overflow-y-auto pr-1">' +
      '<div class="bg-dc-surface border border-dc-border rounded-xl overflow-hidden"><div class="p-3 border-b border-dc-border bg-dc-panel/50 flex items-center gap-2"><i data-lucide="git-compare" class="w-3.5 h-3.5 text-theme"></i><span class="text-xs font-bold text-white uppercase tracking-widest">Submitted Scores</span></div>' +
      '<div class="p-4 space-y-3">' + subsHtml + '</div></div>' +
      '<div class="bg-dc-surface border border-dc-border rounded-xl overflow-hidden"><div class="p-3 border-b border-dc-border bg-dc-panel/50 flex items-center gap-2"><i data-lucide="target" class="w-3.5 h-3.5 text-theme"></i><span class="text-xs font-bold text-white uppercase tracking-widest">Final Score</span></div>' +
      '<div class="p-4"><div class="grid grid-cols-2 gap-3"><div><label class="text-xs font-bold text-dc-text uppercase tracking-widest block mb-1.5">' + esc(m.participant1_name || 'Team A') + '</label>' +
      '<input id="verify-p1" type="number" value="' + (sub0.score_p1 != null ? sub0.score_p1 : m.participant1_score) + '" min="0" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-base font-mono text-center font-bold focus:border-theme outline-none"></div>' +
      '<div><label class="text-xs font-bold text-dc-text uppercase tracking-widest block mb-1.5">' + esc(m.participant2_name || 'Team B') + '</label>' +
      '<input id="verify-p2" type="number" value="' + (sub0.score_p2 != null ? sub0.score_p2 : m.participant2_score) + '" min="0" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-base font-mono text-center font-bold focus:border-theme outline-none"></div></div></div></div>' +
      '<textarea id="verify-notes" rows="2" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-sm focus:border-theme outline-none resize-none" placeholder="Optional admin note ..."></textarea>' +
      '<div class="space-y-2">' +
      '<button onclick="TOC.matches.verifyAction(' + id + ', \'confirm\')" class="w-full py-3 bg-dc-success text-dc-bg text-xs font-black uppercase tracking-widest rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2 ' +
      (m.state === 'completed' ? 'opacity-40 pointer-events-none' : '') + '">\u2705 Confirm & Finalize</button>' +
      '<button onclick="TOC.matches.verifyAction(' + id + ', \'dispute\')" class="w-full py-3 bg-dc-danger/20 border border-dc-danger/30 text-dc-danger text-xs font-black uppercase tracking-widest rounded-xl hover:bg-dc-danger/30 transition-colors flex items-center justify-center gap-2 ' +
      (m.state === 'disputed' ? 'opacity-40 pointer-events-none' : '') + '">\u274C Open Dispute</button>' +
      '<button onclick="TOC.matches.verifyAction(' + id + ', \'note\')" class="w-full py-3 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-black uppercase tracking-widest rounded-xl hover:bg-white/5 transition-colors flex items-center justify-center gap-2">\u{1F4DD} Add Admin Note</button>' +
      '</div></div></div></div>';

    showFullOverlay('verify-overlay', html);
  }

  function switchEvidence(idx) {
    if (!_verifyDetail) return;
    var subs = _verifyDetail.submissions || [];
    var media = (_verifyDetail.media || []).filter(function (x) { return x.is_evidence; });
    var sources = [];
    subs.forEach(function (s) { if (s.proof_screenshot_url) sources.push(s); });
    media.forEach(function (x) { sources.push(x); });
    if (idx < 0 || idx >= sources.length) return;
    _evidenceIndex = idx;
    _zoomScale = 1; _panX = 0; _panY = 0;
    var img = document.getElementById('evidence-img');
    if (img) {
      img.src = sources[idx].proof_screenshot_url || sources[idx].url;
      img.style.transform = 'scale(1) translate(0px, 0px)';
      img.style.display = '';
      var fb = document.getElementById('evidence-fallback');
      if (fb) fb.style.display = 'none';
    }
    document.querySelectorAll('[id^="ev-tab-"]').forEach(function (el, i) {
      el.className = i === idx
        ? 'px-2.5 py-1 rounded text-xs font-bold transition-colors bg-theme text-dc-bg'
        : 'px-2.5 py-1 rounded text-xs font-bold transition-colors bg-dc-bg border border-dc-border text-dc-text hover:text-white';
    });
  }

  function zoomEvidence(dir) { _zoomScale = Math.max(0.25, Math.min(5, _zoomScale + dir * 0.25)); applyTransform(); }
  function resetZoom() { _zoomScale = 1; _panX = 0; _panY = 0; applyTransform(); }
  function wheelZoom(e) { e.preventDefault(); zoomEvidence(e.deltaY < 0 ? 1 : -1); }
  function startPan(e) { _isPanning = true; _panStartX = e.clientX - _panX; _panStartY = e.clientY - _panY; }
  function doPan(e) { if (!_isPanning) return; _panX = e.clientX - _panStartX; _panY = e.clientY - _panStartY; applyTransform(); }
  function endPan() { _isPanning = false; }

  // Touch support for evidence pan/zoom
  var _lastTouchDist = 0;
  function startTouch(e) {
    if (e.touches.length === 1) {
      _isPanning = true;
      _panStartX = e.touches[0].clientX - _panX;
      _panStartY = e.touches[0].clientY - _panY;
    } else if (e.touches.length === 2) {
      _lastTouchDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
    }
  }
  function doTouch(e) {
    e.preventDefault();
    if (e.touches.length === 1 && _isPanning) {
      _panX = e.touches[0].clientX - _panStartX;
      _panY = e.touches[0].clientY - _panStartY;
      applyTransform();
    } else if (e.touches.length === 2) {
      var dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      if (_lastTouchDist > 0) {
        var delta = (dist - _lastTouchDist) / 100;
        _zoomScale = Math.max(0.25, Math.min(5, _zoomScale + delta));
        applyTransform();
      }
      _lastTouchDist = dist;
    }
  }

  function applyTransform() {
    var img = document.getElementById('evidence-img');
    if (img) img.style.transform = 'scale(' + _zoomScale + ') translate(' + (_panX / _zoomScale) + 'px, ' + (_panY / _zoomScale) + 'px)';
    var lvl = document.getElementById('verify-zoom-level');
    if (lvl) lvl.textContent = Math.round(_zoomScale * 100) + '%';
  }

  async function verifyAction(id, action) {
    var p1 = parseInt(document.getElementById('verify-p1')?.value) || 0;
    var p2 = parseInt(document.getElementById('verify-p2')?.value) || 0;
    var notes = document.getElementById('verify-notes')?.value || '';
    if (action === 'note' && !notes.trim()) { toast('Please enter a note', 'error'); return; }
    var body = { action: action, participant1_score: p1, participant2_score: p2, notes: notes };
    if (action === 'dispute') body.reason_code = 'score_mismatch';
    try {
      var res = await API.post('matches/' + id + '/verify/', body);
      var labels = { confirmed: 'Match confirmed & finalized', disputed: 'Dispute opened', noted: 'Admin note added' };
      toast(labels[res.status] || 'Action completed', res.status === 'disputed' ? 'warning' : 'success');
      closeOverlay('verify-overlay');
      refresh();
    } catch (e) { toast(e.message || 'Verification failed', 'error'); }
  }

  /* ============================================================
     OVERLAY HELPERS
  ============================================================ */
  function showFullOverlay(id, innerHtml) {
    var existing = document.getElementById(id);
    if (existing) existing.remove();
    var modal = document.createElement('div');
    modal.id = id;
    modal.className = 'fixed inset-0 z-[110] flex items-center justify-center p-4';
    modal.innerHTML = '<div class="absolute inset-0 bg-black/80 backdrop-blur-md" onclick="TOC.matches.closeOverlay(\'' + id + '\')"></div>' +
      '<div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-2xl w-full max-w-7xl relative z-10 overflow-hidden" style="height:90vh">' +
      '<div class="h-1 w-full bg-theme"></div>' + innerHtml + '</div>';
    document.body.appendChild(modal);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function showOverlay(id, innerHtml) {
    var existing = document.getElementById(id);
    if (existing) existing.remove();
    var modal = document.createElement('div');
    modal.id = id;
    modal.className = 'fixed inset-0 z-[110] flex items-center justify-center';
    modal.innerHTML = '<div class="absolute inset-0 bg-black/80 backdrop-blur-md" onclick="TOC.matches.closeOverlay(\'' + id + '\')"></div>' +
      '<div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-md relative z-10 overflow-hidden">' +
      '<div class="h-1 w-full bg-theme"></div>' + innerHtml + '</div>';
    document.body.appendChild(modal);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function closeOverlay(id) { var el = document.getElementById(id); if (el) el.remove(); }

  /* ============================================================
     MAP VETO
  ============================================================ */
  var _vetoSession    = null;
  var _vetoMapPool    = [];
  var _vetoGameConfig = null;

  async function loadVetoTab() {
    if (!selectedMatchId) return;
    var badge = $('#veto-status-badge');
    if (badge) badge.textContent = 'Loading\u2026';
    try {
      var results = await Promise.all([
        API('settings/veto/' + selectedMatchId + '/').catch(function () { return null; }),
        API('settings/map-pool/').catch(function () { return []; }),
        API('settings/game-config/').catch(function () { return {}; }),
      ]);
      var sessionData = results[0]; var mapPool = results[1]; var gameConfig = results[2];
      _vetoSession    = (sessionData && sessionData.id) ? sessionData : null;
      _vetoMapPool    = Array.isArray(mapPool) ? mapPool.filter(function (mp) { return mp.is_active; }) : [];
      _vetoGameConfig = gameConfig || {};
      _renderVetoState();
    } catch (e) { toast('Failed to load veto data', 'error'); }
  }

  function _renderVetoState() {
    var enabled = !!(_vetoGameConfig && _vetoGameConfig.enable_veto);
    var notCfg    = $('#veto-not-configured');
    var createBtn = $('#veto-create-btn');
    var resetBtn  = $('#veto-reset-btn');
    var seqOverview  = $('#veto-sequence-overview');
    var activeStep   = $('#veto-active-step');
    var picksSection = $('#veto-picks-section');
    var badge      = $('#veto-status-badge');
    var stepLabel  = $('#veto-step-label');

    if (!enabled) {
      if (notCfg)    notCfg.classList.remove('hidden');
      if (createBtn) createBtn.classList.add('hidden');
      if (resetBtn)  resetBtn.classList.add('hidden');
      if (seqOverview)  seqOverview.classList.add('hidden');
      if (activeStep)   activeStep.classList.add('hidden');
      if (picksSection) picksSection.classList.add('hidden');
      if (badge) { badge.textContent = 'Disabled'; badge.className = 'text-xs font-bold px-3 py-1 rounded-full uppercase tracking-widest bg-dc-surface border border-dc-border text-dc-text'; }
      return;
    }
    if (notCfg) notCfg.classList.add('hidden');

    var vs = _vetoSession;
    if (!vs) {
      if (badge) { badge.textContent = 'No Session'; badge.className = 'text-xs font-bold px-3 py-1 rounded-full uppercase tracking-widest bg-dc-surface border border-dc-border text-dc-text'; }
      if (stepLabel)  stepLabel.classList.add('hidden');
      if (createBtn)  createBtn.classList.remove('hidden');
      if (resetBtn)   resetBtn.classList.add('hidden');
      if (seqOverview)  seqOverview.classList.add('hidden');
      if (activeStep)   activeStep.classList.add('hidden');
      if (picksSection) picksSection.classList.add('hidden');
      return;
    }

    if (createBtn) createBtn.classList.add('hidden');
    if (resetBtn)  resetBtn.classList.remove('hidden');

    var statusColors = {
      pending:     'bg-dc-warning/20 text-dc-warning border-dc-warning/30',
      in_progress: 'bg-theme/20 text-theme border-theme/30',
      completed:   'bg-dc-success/20 text-dc-success border-dc-success/30',
      cancelled:   'bg-dc-danger/20 text-dc-danger border-dc-border',
    };
    var sc = statusColors[vs.status] || 'bg-dc-surface border-dc-border text-dc-text';
    if (badge) { badge.textContent = vs.status.replace('_', ' '); badge.className = 'text-xs font-bold px-3 py-1 rounded-full uppercase tracking-widest border ' + sc; }

    // Sequence overview pills
    var seq = vs.sequence || [];
    if (seqOverview && seq.length) {
      seqOverview.classList.remove('hidden');
      var stepsContainer = $('#veto-sequence-steps');
      if (stepsContainer) {
        stepsContainer.innerHTML = seq.map(function (s, i) {
          var completed = i < vs.current_step;
          var active    = i === vs.current_step && vs.status !== 'completed';
          var actionClass = s.action === 'ban' ? 'bg-dc-danger/20 text-dc-danger border-dc-danger/30'
            : s.action === 'pick' ? 'bg-dc-success/20 text-dc-success border-dc-success/30'
            : 'bg-dc-warning/20 text-dc-warning border-dc-warning/30';
          var completedPick = (vs.picks || []).find(function (p) { return p.step === i; });
          var label    = completedPick ? _vetoEsc(completedPick.map || '?') : _vetoEsc(s.action);
          var ringClass = active ? ' ring-2 ring-theme ring-offset-1 ring-offset-dc-bg' : '';
          var opClass   = (completed || active) ? '' : ' opacity-40';
          return '<span class="text-[11px] font-bold px-2 py-1 rounded-lg border ' + actionClass + ringClass + opClass + '" title="Step ' + (i + 1) + ': ' + _vetoEsc(s.action) + ' (' + _vetoEsc(s.team || '') + ')">' + label + '</span>';
        }).join('');
      }
    } else if (seqOverview) {
      seqOverview.classList.add('hidden');
    }

    // Active step panel (pending or in_progress)
    if (vs.status === 'in_progress' || vs.status === 'pending') {
      var currentStepDef = seq[vs.current_step];
      if (currentStepDef && activeStep) {
        activeStep.classList.remove('hidden');
        var m = allMatches.find(function (x) { return x.id === selectedMatchId; });
        var teamName    = _resolveVetoTeam(currentStepDef.team, m);
        var actionLabel = $('#veto-action-label');
        var teamLabel   = $('#veto-team-label');
        var stepCounter = $('#veto-step-counter');
        var mapGrid     = $('#veto-map-grid');
        if (actionLabel) actionLabel.textContent = currentStepDef.action === 'ban' ? 'Ban' : currentStepDef.action === 'pick' ? 'Pick' : 'Decider';
        if (teamLabel)   teamLabel.textContent = teamName + '\u2019s turn';
        if (stepCounter) stepCounter.textContent = 'Step ' + (vs.current_step + 1) + ' / ' + seq.length;
        // Map grid — exclude already used maps
        var usedMaps = (vs.picks || []).map(function (p) { return (p.map || '').toLowerCase(); });
        var available = _vetoMapPool.filter(function (mp) { return !usedMaps.includes((mp.map_name || '').toLowerCase()); });
        if (!available.length) available = _vetoMapPool;
        if (mapGrid) {
          mapGrid.innerHTML = available.map(function (mp) {
            return '<button onclick="TOC.matches.doVetoAction(this.dataset.map)" data-map="' + _vetoEsc(mp.map_name) + '" '
              + 'class="px-3 py-2 rounded-lg border border-dc-border bg-dc-surface text-xs font-bold text-dc-textBright hover:border-theme/60 hover:bg-theme/10 hover:text-white transition-colors truncate text-left">'
              + _vetoEsc(mp.map_name) + '</button>';
          }).join('');
        }
      } else if (activeStep) { activeStep.classList.add('hidden'); }
      if (stepLabel) stepLabel.classList.add('hidden');
    } else {
      if (activeStep) activeStep.classList.add('hidden');
      if (stepLabel) { stepLabel.classList.remove('hidden'); stepLabel.textContent = vs.status === 'completed' ? 'All steps complete' : ''; }
    }

    // Picks list
    var picks = vs.picks || [];
    if (picksSection && picks.length) {
      picksSection.classList.remove('hidden');
      var picksList = $('#veto-picks-list');
      if (picksList) {
        picksList.innerHTML = picks.map(function (p) {
          var ac = p.action === 'ban' ? 'text-dc-danger bg-dc-danger/10' : p.action === 'pick' ? 'text-dc-success bg-dc-success/10' : 'text-dc-warning bg-dc-warning/10';
          return '<div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-dc-surface/50 border border-dc-border">'
            + '<span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded ' + ac + '">' + _vetoEsc(p.action || '?') + '</span>'
            + '<span class="flex-1 text-xs font-bold text-white truncate">' + _vetoEsc(p.map || '\u2014') + '</span>'
            + '<span class="text-[10px] font-mono text-dc-text">' + _vetoEsc(p.team || '') + '</span>'
            + '</div>';
        }).join('');
      }
    } else if (picksSection) { picksSection.classList.add('hidden'); }
  }

  function _resolveVetoTeam(teamKey, match) {
    if (!match) return teamKey || 'TBD';
    if (teamKey === 'higher_seed' || teamKey === 'team_a') return match.participant1_name || 'Team A';
    if (teamKey === 'lower_seed'  || teamKey === 'team_b') return match.participant2_name || 'Team B';
    return teamKey || 'TBD';
  }

  function _vetoEsc(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  async function createVetoSession() {
    if (!selectedMatchId) return;
    var seq = (_vetoGameConfig && _vetoGameConfig.veto_sequence) ? _vetoGameConfig.veto_sequence : [];
    if (!seq.length) { toast('No veto sequence defined. Configure it in Settings \u203a Game Config.', 'error'); return; }
    var vetoType = (_vetoGameConfig && _vetoGameConfig.veto_type) || 'standard';
    try {
      await API('settings/veto/' + selectedMatchId + '/', { method: 'POST', body: JSON.stringify({ veto_type: vetoType, sequence: seq }), headers: { 'Content-Type': 'application/json' } });
      var sessionData = await API('settings/veto/' + selectedMatchId + '/').catch(function () { return null; });
      _vetoSession = (sessionData && sessionData.id) ? sessionData : null;
      _renderVetoState();
      toast('Veto session started', 'success');
    } catch (e) { toast(e.message || 'Failed to create session', 'error'); }
  }

  async function resetVetoSession() {
    if (!selectedMatchId) return;
    var seq = (_vetoGameConfig && _vetoGameConfig.veto_sequence) ? _vetoGameConfig.veto_sequence : [];
    var vetoType = (_vetoGameConfig && _vetoGameConfig.veto_type) || 'standard';
    try {
      await API('settings/veto/' + selectedMatchId + '/', { method: 'POST', body: JSON.stringify({ veto_type: vetoType, sequence: seq }), headers: { 'Content-Type': 'application/json' } });
      var sessionData = await API('settings/veto/' + selectedMatchId + '/').catch(function () { return null; });
      _vetoSession = (sessionData && sessionData.id) ? sessionData : null;
      _renderVetoState();
      toast('Veto session reset', 'success');
    } catch (e) { toast(e.message || 'Failed to reset', 'error'); }
  }

  async function doVetoAction(mapName) {
    if (!selectedMatchId || !_vetoSession) return;
    var vs  = _vetoSession;
    var seq = vs.sequence || [];
    var step = seq[vs.current_step];
    if (!step) return;
    try {
      var result = await API('settings/veto/' + selectedMatchId + '/advance/', {
        method: 'POST',
        body: JSON.stringify({ action: step.action, team: step.team, map: mapName }),
        headers: { 'Content-Type': 'application/json' },
      });
      _vetoSession = Object.assign({}, vs, { current_step: result.current_step, status: result.status, picks: result.picks });
      _renderVetoState();
      if (result.status === 'completed') toast('Veto complete!', 'success');
    } catch (e) { toast(e.message || 'Failed to advance veto', 'error'); }
  }

  /* ============================================================
     KEYBOARD NAVIGATION
  ============================================================ */
  function handleKeyboard(e) {
    var matchesTab = $('#view-matches');
    if (!matchesTab || matchesTab.classList.contains('hidden-view')) return;

    // Don't intercept when inside inputs/textareas/selects
    var tag = (e.target?.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      var idx = -1;
      for (var i = 0; i < filteredMatches.length; i++) {
        if (filteredMatches[i].id === selectedMatchId) { idx = i; break; }
      }
      var next;
      if (e.key === 'ArrowDown') {
        next = idx < filteredMatches.length - 1 ? idx + 1 : 0;
      } else {
        next = idx > 0 ? idx - 1 : filteredMatches.length - 1;
      }
      if (filteredMatches[next]) {
        selectMatch(filteredMatches[next].id);
        var card = document.querySelector('.match-card[data-match-id="' + filteredMatches[next].id + '"]');
        if (card) card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }

    // Enter/Space to select focused match card
    if ((e.key === 'Enter' || e.key === ' ') && e.target?.classList?.contains('match-card')) {
      e.preventDefault();
      var mid = parseInt(e.target.dataset.matchId);
      if (mid) selectMatch(mid);
    }

    // Escape to clear detail or close modals
    if (e.key === 'Escape') {
      var disputeModal = $('#dispute-modal');
      var lobbyModal = $('#lobby-editor-modal');
      if (disputeModal && !disputeModal.classList.contains('hidden')) { closeDisputeModal(); return; }
      if (lobbyModal && !lobbyModal.classList.contains('hidden')) { closeLobbyEditor(); return; }
      var verify = document.getElementById('verify-overlay');
      if (verify) { closeOverlay('verify-overlay'); return; }
      clearDetail();
    }

    // Tab switching: 1=Score, 2=Evidence, 3=Audit, 4=Veto
    if (e.key === '1' && selectedMatchId) { switchDetailTab('score'); }
    if (e.key === '2' && selectedMatchId) { switchDetailTab('evidence'); }
    if (e.key === '3' && selectedMatchId) { switchDetailTab('audit'); }
    if (e.key === '4' && selectedMatchId) { switchDetailTab('veto'); }

    // Quick actions (with no modifier)
    if (e.key === 's' || e.key === 'S') { if (selectedMatchId) { switchDetailTab('score'); $('#score-input-a')?.focus(); } }
    if (e.key === 'd' || e.key === 'D') { if (selectedMatchId) openDispute(); }
    if (e.key === 'n' || e.key === 'N') { if (selectedMatchId) { switchDetailTab('score'); $('#score-note')?.focus(); } }
    if (e.key === 'v' || e.key === 'V') { if (selectedMatchId) openVerifyScreen(); }
    if (e.key === 'l' || e.key === 'L') { if (selectedMatchId) openLobbyEditor(); }
  }

  /* ============================================================
     INIT
  ============================================================ */
  function init() {
    refresh();
    switchDetailTab('score');
    if (typeof lucide !== 'undefined') lucide.createIcons();
    if (!_matchesAutoRefreshTimer) {
      _matchesAutoRefreshTimer = setInterval(() => {
        if (!isMatchesTabActive()) return;
        refresh({ silent: true });
      }, MATCHES_AUTO_REFRESH_MS);
    }
  }

  document.addEventListener('keydown', handleKeyboard);

  window.TOC = window.TOC || {};
  window.TOC.matches = {
    init: init, refresh: refresh, debouncedRefresh: debouncedRefresh,
    selectMatch: selectMatch, clearDetail: clearDetail, filterGroup: filterGroup,
    generateMatchesFromEmptyState: generateMatchesFromEmptyState,
    switchDetailTab: switchDetailTab,
    markLive: markLive, pause: pause, resume: resume, forceComplete: forceComplete,
    submitScore: submitScore,
    openDispute: openDispute, closeDisputeModal: closeDisputeModal, confirmDispute: confirmDispute,
    resetMatch: resetMatch,
    openLobbyEditor: openLobbyEditor, closeLobbyEditor: closeLobbyEditor, saveLobbyInfo: saveLobbyInfo,
    copyLobbyCode: copyLobbyCode,
    openScoreDrawer: openScoreDrawer, openDetailDrawer: openDetailDrawer,
    openRescheduleModal: openRescheduleModal, confirmReschedule: confirmReschedule,
    openForfeit: openForfeit, confirmForfeit: confirmForfeit,
    openVerifyScreen: openVerifyScreen, verifyAction: verifyAction,
    switchEvidence: switchEvidence, zoomEvidence: zoomEvidence, resetZoom: resetZoom, wheelZoom: wheelZoom,
    startPan: startPan, doPan: doPan, endPan: endPan,
    startTouch: startTouch, doTouch: doTouch,
    closeOverlay: closeOverlay,
    // Series (BO3/BO5)
    setBestOf: setBestOf,
    openAddGameScore: openAddGameScore, closeGameScoreModal: closeGameScoreModal, confirmAddGameScore: confirmAddGameScore,
    // Map Veto
    createVetoSession: createVetoSession, resetVetoSession: resetVetoSession, doVetoAction: doVetoAction,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'matches') init();
  });

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden && isMatchesTabActive()) {
      const queryKey = currentQueryKey();
      if (!hasFreshCache(queryKey)) refresh({ silent: true });
    }
  });
})();
