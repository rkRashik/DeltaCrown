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

  function isRoomOpenState(state) {
    var token = String(state || '').toLowerCase();
    return token !== 'completed' && token !== 'cancelled' && token !== 'forfeit';
  }

  function parseApiError(err) {
    if (!err) return 'Something went wrong. Please try again.';
    if (err.payload && typeof err.payload === 'object') {
      if (err.payload.error) return err.payload.error;
      var blocked = err.payload.details && Array.isArray(err.payload.details.blocked_groups)
        ? err.payload.details.blocked_groups
        : [];
      if (blocked.length && blocked[0] && blocked[0].reason) return blocked[0].reason;
      return err.payload.detail || err.payload.message || err.message || 'Something went wrong. Please try again.';
    }
    return err.message || 'Something went wrong. Please try again.';
  }

  function timeApi() {
    return window.TOC && window.TOC.time ? window.TOC.time : null;
  }

  function formatDateTime(value, options) {
    if (!value) return '';
    var t = timeApi();
    if (t && typeof t.formatDateTime === 'function') {
      return t.formatDateTime(value, options || {});
    }
    var dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return '';
    return dt.toLocaleString(undefined, options || {});
  }

  function formatClock(value, options) {
    if (!value) return '';
    var t = timeApi();
    if (t && typeof t.formatTime === 'function') {
      return t.formatTime(value, options || {});
    }
    var dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return '';
    return dt.toLocaleTimeString(undefined, options || {});
  }

  function toTimestamp(value) {
    if (!value) return 0;
    var dt = new Date(value);
    var ts = dt.getTime();
    return Number.isFinite(ts) ? ts : 0;
  }

  function compareByTimeProximity(a, b) {
    var now = Date.now();
    var ta = toTimestamp(a && a.scheduled_time);
    var tb = toTimestamp(b && b.scheduled_time);
    var hasA = ta > 0;
    var hasB = tb > 0;

    if (hasA && hasB) {
      var da = Math.abs(ta - now);
      var db = Math.abs(tb - now);
      if (da !== db) return da - db;
      if (ta !== tb) return ta - tb;
    } else if (hasA) {
      return -1;
    } else if (hasB) {
      return 1;
    }

    var ar = Number(a && a.round_number) || 0;
    var br = Number(b && b.round_number) || 0;
    if (ar !== br) return ar - br;
    return (Number(a && a.match_number) || 0) - (Number(b && b.match_number) || 0);
  }

  function nameInitials(name) {
    var text = String(name || '').trim();
    if (!text) return '??';
    var bits = text.split(/\s+/).filter(Boolean);
    if (!bits.length) return text.slice(0, 2).toUpperCase();
    if (bits.length === 1) return bits[0].slice(0, 2).toUpperCase();
    return (bits[0].slice(0, 1) + bits[1].slice(0, 1)).toUpperCase();
  }

  function renderParticipantIdentity(name, logoUrl, side, isWinner) {
    var label = name || 'TBD';
    var textClass = isWinner ? 'text-dc-success font-bold' : 'text-dc-textBright';
    var avatar = logoUrl
      ? '<span class="inline-flex h-6 w-6 items-center justify-center overflow-hidden rounded-full border border-white/15 bg-dc-bg shrink-0"><img src="' + esc(logoUrl) + '" alt="" class="h-full w-full object-cover"></span>'
      : '<span class="inline-flex h-6 w-6 items-center justify-center rounded-full border border-white/15 bg-dc-bg text-[10px] font-black text-dc-textBright shrink-0">' + esc(nameInitials(label)) + '</span>';

    if (side === 'left') {
      return '<span class="flex-1 min-w-0 flex items-center gap-2 justify-end">'
        + '<span class="text-sm ' + textClass + ' truncate text-right">' + esc(label) + '</span>'
        + avatar
        + '</span>';
    }

    return '<span class="flex-1 min-w-0 flex items-center gap-2 justify-start">'
      + avatar
      + '<span class="text-sm ' + textClass + ' truncate text-left">' + esc(label) + '</span>'
      + '</span>';
  }

  function isDrawAllowed(match) {
    if (!match) return false;
    if (match.draw_allowed === true) return true;
    return String(match.draw_allowed || '').toLowerCase() === 'true';
  }

  function normalizeWinnerSide(raw) {
    var token = String(raw || '').trim().toLowerCase();
    if (!token) return '';
    if (token === 'a' || token === '1' || token === 'p1' || token === 'participant1' || token === 'team1') return '1';
    if (token === 'b' || token === '2' || token === 'p2' || token === 'participant2' || token === 'team2') return '2';
    if (token === 'draw' || token === 'tie' || token === 'd') return 'draw';
    return '';
  }

  function syncWinnerSelectForMatch(match) {
    var winSel = $('#score-winner');
    var inputA = $('#score-input-a');
    var inputB = $('#score-input-b');
    if (!winSel || !inputA || !inputB) return;

    var drawAllowed = isDrawAllowed(match);
    var drawOpt = winSel.querySelector('option[value="draw"]');
    if (drawAllowed && !drawOpt) {
      drawOpt = document.createElement('option');
      drawOpt.value = 'draw';
      drawOpt.id = 'winner-opt-draw';
      drawOpt.textContent = 'Draw';
      winSel.appendChild(drawOpt);
    }
    if (!drawAllowed && drawOpt) {
      drawOpt.remove();
    }

    var p1 = parseInt(inputA.value, 10);
    var p2 = parseInt(inputB.value, 10);
    if (!Number.isFinite(p1) || !Number.isFinite(p2)) {
      winSel.value = '';
      return;
    }
    if (p1 > p2) {
      winSel.value = 'a';
    } else if (p2 > p1) {
      winSel.value = 'b';
    } else if (drawAllowed) {
      winSel.value = 'draw';
    } else {
      winSel.value = '';
    }
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
  let _lastRoundOptions = [];
  let selectedMatchDetail = null;
  let activeGroupFilter = '';
  let activeStageFilter = '';
  let _currentStage = null;
  let _debounceTimer = null;
  let _matchesInflight = null;
  let _matchesInflightQueryKey = '';
  let _matchesRequestId = 0;
  let _matchesLastFetchedAt = 0;
  let _matchesLastQueryKey = '';
  let _matchesAutoRefreshTimer = null;
  let _matchesFilterSignature = '';
  let _matchesStateCounts = {};

  let matchesPagination = {
    page: 1,
    page_size: 60,
    total_count: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  };

  const MATCHES_CACHE_TTL_MS = 15000;
  const MATCHES_AUTO_REFRESH_MS = 30000;
  const DEFAULT_PAGE_SIZE = 60;
  const MATCHES_STAT_IDS = ['total', 'live', 'pending', 'completed', 'disputed'];

  function isMatchesTabActive() {
    return (window.location.hash || '').replace('#', '') === 'matches';
  }

  function currentQueryKey() {
    const stateVal = $('#match-filter-state')?.value || '';
    const roundVal = $('#match-filter-round')?.value || '';
    const searchVal = $('#match-search')?.value || '';
    return [
      stateVal,
      roundVal,
      searchVal,
      matchesPagination.page,
      matchesPagination.page_size,
      activeGroupFilter,
      activeStageFilter,
    ].join('::');
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
      el.textContent = 'Last sync ' + formatClock(_matchesLastFetchedAt, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
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
          <button type="button" class="mt-2 px-2.5 py-1 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" data-click="TOC.matches.refresh" data-click-args="[{&quot;force&quot;:true}]">Retry now</button>
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

    if (typeof opts.page === 'number' && Number.isFinite(opts.page)) {
      matchesPagination.page = Math.max(1, Math.floor(opts.page));
    }
    if (typeof opts.pageSize === 'number' && Number.isFinite(opts.pageSize)) {
      matchesPagination.page_size = Math.max(10, Math.min(120, Math.floor(opts.pageSize)));
    }

    const state = $('#match-filter-state')?.value || '';
    const round = $('#match-filter-round')?.value || '';
    const search = $('#match-search')?.value || '';
    const filterSignature = [state, round, search].join('::');

    if (!opts.keepPage && filterSignature !== _matchesFilterSignature) {
      matchesPagination.page = 1;
    }
    _matchesFilterSignature = filterSignature;

    const queryKey = currentQueryKey();

    if (!force && hasFreshCache(queryKey)) {
      applyGroupFilter();
      renderStats(allMatches, _matchesStateCounts, matchesPagination.total_count);
      populateRoundFilter(allMatches, _lastRoundOptions);
      populateGroupPills(allMatches);
      renderPaginationControls();
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
        const data = await API.get(
          'matches/' +
          '?state=' + state +
          '&round=' + round +
          '&search=' + encodeURIComponent(search) +
          '&page=' + encodeURIComponent(matchesPagination.page) +
          '&page_size=' + encodeURIComponent(matchesPagination.page_size || DEFAULT_PAGE_SIZE) +
          (activeStageFilter ? '&stage=' + encodeURIComponent(activeStageFilter) : '')
        );
        if (requestId !== _matchesRequestId) return { matches: allMatches };

        allMatches = data.matches || [];
        _currentStage = data.current_stage || null;
        _matchesStateCounts = (data && typeof data.state_counts === 'object' && data.state_counts) ? data.state_counts : {};
        _lastRoundOptions = Array.isArray(data.round_options) ? data.round_options : [];

        const meta = (data && data.pagination && typeof data.pagination === 'object') ? data.pagination : {};
        matchesPagination.page = Number(meta.page || matchesPagination.page || 1);
        matchesPagination.page_size = Number(meta.page_size || matchesPagination.page_size || DEFAULT_PAGE_SIZE);
        matchesPagination.total_count = Number(
          meta.total_count != null ? meta.total_count : (data.total_count != null ? data.total_count : allMatches.length)
        );
        const inferredTotalPages = Math.max(1, Math.ceil((matchesPagination.total_count || 0) / (matchesPagination.page_size || DEFAULT_PAGE_SIZE)));
        matchesPagination.total_pages = Number(meta.total_pages || inferredTotalPages);
        matchesPagination.has_next = Boolean(meta.has_next != null ? meta.has_next : (matchesPagination.page < matchesPagination.total_pages));
        matchesPagination.has_prev = Boolean(meta.has_prev != null ? meta.has_prev : (matchesPagination.page > 1));

        _matchesLastFetchedAt = Date.now();
        _matchesLastQueryKey = queryKey;

        applyGroupFilter();
        renderStats(allMatches, _matchesStateCounts, matchesPagination.total_count);
        populateRoundFilter(allMatches, _lastRoundOptions);
        populateGroupPills(allMatches);
        renderStageTabs();
        renderPaginationControls();
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

  function renderPaginationControls() {
    var pageInfo = $('#match-page-info');
    var prevBtn = $('#match-page-prev');
    var nextBtn = $('#match-page-next');

    if (pageInfo) {
      var totalPages = Math.max(1, Number(matchesPagination.total_pages || 1));
      pageInfo.textContent = 'Page ' + (matchesPagination.page || 1) + ' / ' + totalPages;
    }

    if (prevBtn) {
      prevBtn.disabled = !matchesPagination.has_prev;
      prevBtn.classList.toggle('opacity-40', !matchesPagination.has_prev);
      prevBtn.classList.toggle('cursor-not-allowed', !matchesPagination.has_prev);
    }

    if (nextBtn) {
      nextBtn.disabled = !matchesPagination.has_next;
      nextBtn.classList.toggle('opacity-40', !matchesPagination.has_next);
      nextBtn.classList.toggle('cursor-not-allowed', !matchesPagination.has_next);
    }
  }

  function nextPage() {
    if (!matchesPagination.has_next) return;
    refresh({ page: (matchesPagination.page || 1) + 1, keepPage: true });
  }

  function prevPage() {
    if (!matchesPagination.has_prev) return;
    refresh({ page: Math.max(1, (matchesPagination.page || 1) - 1), keepPage: true });
  }

  function debouncedRefresh() {
    clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(refresh, 300);
  }

  /* --- Stage phase tabs (Group / Knockout) with context banner -- */
  function renderStageTabs() {
    var container = $('#match-stage-tabs');
    if (!container) return;
    var cfg = window.TOC_CONFIG || {};
    var fmt = (cfg.tournamentFormat || '').toLowerCase();
    var currentStage = (cfg.currentStage || '').toLowerCase();
    // Only show stage tabs for group_playoff format
    if (fmt !== 'group_playoff') { container.classList.add('hidden'); return; }
    container.classList.remove('hidden');

    // Stage context banner
    var bannerHtml = '';
    if (currentStage === 'knockout_stage') {
      bannerHtml = '<div class="flex items-center gap-2 px-3 py-2 mb-2 rounded-lg border border-theme/20 bg-theme/5">'
        + '<i data-lucide="trophy" class="w-3.5 h-3.5 text-theme"></i>'
        + '<span class="text-[10px] font-bold text-theme uppercase tracking-widest">Knockout Stage Active</span>'
        + '<span class="text-[10px] text-dc-text/50 ml-auto">Group stage completed</span></div>';
    } else if (currentStage === 'group_stage') {
      bannerHtml = '<div class="flex items-center gap-2 px-3 py-2 mb-2 rounded-lg border border-dc-info/20 bg-dc-info/5">'
        + '<i data-lucide="users" class="w-3.5 h-3.5 text-dc-info"></i>'
        + '<span class="text-[10px] font-bold text-dc-info uppercase tracking-widest">Group Stage Active</span></div>';
    }

    var tabs = [
      { key: '', label: 'All Matches' },
      { key: 'group_stage', label: 'Group Stage' },
      { key: 'knockout', label: 'Knockout' },
    ];
    container.innerHTML = bannerHtml + '<div class="flex items-center gap-2 flex-wrap">' + tabs.map(function(t) {
      var active = activeStageFilter === t.key;
      return '<button data-stage="' + t.key + '" class="' +
        (active ? 'bg-theme/15 text-theme border-theme/30' : 'bg-dc-bg text-dc-text border-dc-border hover:text-white') +
        ' px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all border" ' +
        'data-click="TOC.matches.filterStage" data-click-args="[&quot;' + t.key + '&quot;]" role="tab" aria-selected="' + active + '">' +
        t.label + '</button>';
    }).join('') + '</div>';
    if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [container] });
  }

  function filterStage(stage) {
    activeStageFilter = stage || '';
    activeGroupFilter = '';
    matchesPagination.page = 1;
    renderStageTabs();
    refresh({ force: true });
  }

  /* --- Group filter pills ---------------------------------- */
  function populateGroupPills(matches) {
    var container = $('#match-group-pills');
    if (!container) return;
    // Hide group pills during knockout filter
    if (activeStageFilter === 'knockout') { container.innerHTML = ''; return; }
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
      ' px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-widest transition-all border" data-click="TOC.matches.filterGroup" data-click-args="[&quot;&quot;]" role="radio" aria-checked="' + (activeGroupFilter === '' ? 'true' : 'false') + '">All</button>';
    groups.forEach(function (g) {
      var eg = esc(g);
      html += '<button data-group="' + eg + '" class="match-pill ' +
        (activeGroupFilter === g ? 'active bg-theme/15 text-theme border-theme/20' : 'bg-dc-bg text-dc-text border-dc-border hover:text-white') +
        ' px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-widest transition-all border" data-click="TOC.matches.filterGroup" data-click-args="[&quot;' + eg.replace(/"/g, '\\&quot;') + '&quot;]"  role="radio" aria-checked="' + (activeGroupFilter === g ? 'true' : 'false') + '">' + eg + '</button>';
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
    renderPaginationControls();
    if (selectedMatchId && !filteredMatches.find(function (m) { return m.id === selectedMatchId; })) {
      clearDetail();
    }
  }

  /* --- Stats ----------------------------------------------- */
  function renderStats(matches, stateCounts, totalCount) {
    var el = function (id, val) { var e = $('#matches-stat-' + id); if (e) e.textContent = val; };

    var counts = (stateCounts && typeof stateCounts === 'object') ? stateCounts : {};
    var fallback = {
      live: matches.filter(function (m) { return m.state === 'live'; }).length,
      pending_result: matches.filter(function (m) { return m.state === 'pending_result'; }).length,
      completed: matches.filter(function (m) { return m.state === 'completed'; }).length,
      forfeit: matches.filter(function (m) { return m.state === 'forfeit'; }).length,
      disputed: matches.filter(function (m) { return m.state === 'disputed'; }).length,
    };

    el('total', totalCount != null ? totalCount : matches.length);
    el('live', counts.live != null ? counts.live : fallback.live);
    el('pending', counts.pending_result != null ? counts.pending_result : fallback.pending_result);
    el('completed', Number(counts.completed != null ? counts.completed : fallback.completed) + Number(counts.forfeit != null ? counts.forfeit : fallback.forfeit));
    el('disputed', counts.disputed != null ? counts.disputed : fallback.disputed);
  }

  /* --- Round filter ----------------------------------------
     Prefers the canonical `round_options` payload from the matches API
     (which carries Quarterfinals/Semifinals/Final labels) and falls back
     to deriving labels from the loaded match cards on the current page.
  ---------------------------------------------------------- */
  function populateRoundFilter(matches, roundOptions) {
    var sel = $('#match-filter-round');
    if (!sel) return;

    var options = [];
    if (Array.isArray(roundOptions) && roundOptions.length) {
      options = roundOptions.map(function (o) {
        return { value: o.value, label: o.label || ('Round ' + o.value) };
      });
    } else {
      // Fallback: derive from loaded matches, prefer bracket_round_label.
      var labelByRound = {};
      (matches || []).forEach(function (m) {
        var rn = Number(m.round_number) || 0;
        if (!rn) return;
        if (!labelByRound[rn] && m.bracket_round_label) {
          labelByRound[rn] = m.bracket_round_label;
        } else if (!labelByRound[rn]) {
          labelByRound[rn] = 'Round ' + rn;
        }
      });
      Object.keys(labelByRound).map(Number).sort(function (a, b) { return a - b; })
        .forEach(function (r) { options.push({ value: r, label: labelByRound[r] }); });
    }

    var current = sel.value;
    sel.innerHTML = '<option value="">All Rounds</option>' +
      options.map(function (o) {
        return '<option value="' + o.value + '"'
          + (String(o.value) === current ? ' selected' : '')
          + '>' + o.label + '</option>';
      }).join('');
  }

  /* ============================================================
     LEFT PANEL: Match List (virtual-scrolled cards)
  ============================================================ */

  /* --- Virtual scroll state -------------------------------- */
  var _vsItems = [];       // sorted match array for current render
  var _vsRafId = 0;
  var _vsLastStart = -1;
  var _vsLastEnd = -1;
  var CARD_H = 92;         // estimated card height in px
  var VS_BUFFER = 4;       // extra items above/below viewport

  function _buildMatchCard(m) {
      var sc = stateConfig[m.state] || stateConfig.scheduled;
      var isSelected = m.id === selectedMatchId;
      var isWinner1 = m.winner_id && m.winner_id === m.participant1_id;
      var isWinner2 = m.winner_id && m.winner_id === m.participant2_id;
      var p1Logo = m.p1_logo_url || m.participant1_logo_url || m.participant1_logo || m.participant1_avatar_url || '';
      var p2Logo = m.p2_logo_url || m.participant2_logo_url || m.participant2_logo || m.participant2_avatar_url || '';
      var isLive = m.state === 'live';
      var canOpenRoom = isRoomOpenState(m.state);
      var liveDot = m.state === 'live' ? '<span class="w-2 h-2 rounded-full bg-dc-success animate-pulse inline-block"></span>' : '';
      var groupTag = m.group_label ? ' <span class="text-theme/70">&middot;</span> <span class="text-theme font-bold">' + esc(m.group_label) + '</span>' : '';
      var bracketTag = m.bracket_round_label ? ' <span class="text-amber-400/70">&middot;</span> <span class="text-amber-300 font-bold">' + esc(m.bracket_round_label) + '</span>' : '';
      var phaseTag = m.stage === 'knockout' ? bracketTag : groupTag;
      var disputedBorder = m.state === 'disputed' ? ' ring-1 ring-dc-danger/30' : '';
      var liveCard = isLive ? ' border border-emerald-400/35 shadow-[0_0_22px_rgba(16,185,129,0.24)] bg-emerald-500/[0.03]' : '';

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
      var roundLabel = m.bracket_round_label || '';
      var roundPrefix = roundLabel ? '' : (isSwissRound ? 'Swiss R' : 'R');
      var roundDisplay = roundLabel || (roundPrefix + m.round_number);
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
      var roomCtaClass = isLive
        ? 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-300/45 bg-gradient-to-r from-emerald-500/30 via-emerald-400/20 to-teal-300/25 text-emerald-100 text-[10px] font-black uppercase tracking-widest shadow-[0_0_18px_rgba(16,185,129,0.26)] animate-pulse hover:brightness-110 transition-all'
        : 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-theme/35 bg-gradient-to-r from-theme/25 via-theme/12 to-cyan-300/20 text-cyan-100 text-[10px] font-black uppercase tracking-widest shadow-[0_0_14px_rgba(34,211,238,0.18)] hover:brightness-110 transition-all';
      var liveCta = canOpenRoom
        ? '<a href="/tournaments/' + slug + '/matches/' + m.id + '/room/?admin=1" data-click="event.stopPropagation" class="' + roomCtaClass + '">' + (isLive ? 'LIVE - Enter Lobby' : 'Enter Lobby') + '</a>'
        : '';

      return '<div class="match-card px-4 py-3 cursor-pointer transition-all hover:bg-white/[0.03]' +
        (isSelected ? ' bg-theme/5 border-l-[3px] border-l-theme' : ' border-l-[3px] border-l-transparent') +
        disputedBorder + liveCard +
        '" data-click="TOC.matches.selectMatch" data-click-args="[' + m.id + ']" data-match-id="' + m.id + '"' +
        ' tabindex="0" role="option" aria-selected="' + (isSelected ? 'true' : 'false') + '"' +
        ' aria-label="Match ' + m.match_number + ': ' + esc(m.participant1_name || 'TBD') + ' vs ' + esc(m.participant2_name || 'TBD') + '">' +

        // Row 1: Round/match info + state badge
        '<div class="flex items-center justify-between mb-2">' +
        '<span class="text-xs font-mono text-dc-text">' + esc(roundDisplay) + ' &middot; #' + m.match_number + phaseTag + '</span>' +
        '<div class="flex items-center gap-2">' + checkinHtml + liveDot +
        '<span class="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ' + sc.cls + '">' + sc.label + '</span>' +
        (m.is_paused ? '<span class="text-xs font-bold text-dc-warning" title="Paused">&#x23F8;</span>' : '') +
        '</div></div>' +

        // Row 2: Teams + score
        '<div class="flex items-center gap-3">' +
  renderParticipantIdentity(m.participant1_name || 'TBD', p1Logo, 'left', isWinner1) +
        '<span class="font-mono font-black text-sm text-white px-3 py-1 rounded bg-dc-bg border border-dc-border min-w-[56px] text-center">' + boLabel + scoreA + ' \u2013 ' + scoreB + '</span>' +
  renderParticipantIdentity(m.participant2_name || 'TBD', p2Logo, 'right', isWinner2) +
        '</div>' +

        // Row 3: Time info (if scheduled)
        (m.scheduled_time ? '<div class="mt-1.5 text-xs text-dc-text/50 font-mono text-center">' +
        '<i data-lucide="clock" class="w-3 h-3 inline-block mr-1"></i>' +
  formatDateTime(m.scheduled_time, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) +
        '</div>' : '') +

        (canOpenRoom ? '<div class="mt-2 flex items-center justify-center">' + liveCta + '</div>' : '') +

        '</div>';
  }

  function _vsOnScroll() {
    cancelAnimationFrame(_vsRafId);
    _vsRafId = requestAnimationFrame(_vsRenderVisible);
  }

  function _vsRenderVisible() {
    var list = $('#match-list');
    if (!list || !_vsItems.length) return;
    var viewport = list.querySelector('#vs-viewport');
    if (!viewport) return;

    var scrollTop = list.scrollTop;
    var viewH = list.clientHeight;
    var total = _vsItems.length;

    var startIdx = Math.max(0, Math.floor(scrollTop / CARD_H) - VS_BUFFER);
    var endIdx = Math.min(total, Math.ceil((scrollTop + viewH) / CARD_H) + VS_BUFFER);

    // Skip re-render if visible window hasn't changed
    if (startIdx === _vsLastStart && endIdx === _vsLastEnd) return;
    _vsLastStart = startIdx;
    _vsLastEnd = endIdx;

    list.querySelector('#vs-top').style.height = (startIdx * CARD_H) + 'px';
    list.querySelector('#vs-bottom').style.height = ((total - endIdx) * CARD_H) + 'px';

    var html = '';
    for (var i = startIdx; i < endIdx; i++) {
      html += _buildMatchCard(_vsItems[i]);
    }
    viewport.innerHTML = html;

    if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [viewport] });
  }

  function renderMatchList(matches) {
    var list = $('#match-list');
    if (!list) return;

    var countEl = $('#match-list-count');
    if (countEl) {
      var totalCount = Number(matchesPagination.total_count || matches.length || 0);
      countEl.textContent = 'Showing ' + matches.length + ' of ' + totalCount + ' match' + (totalCount !== 1 ? 'es' : '');
    }

    if (!matches.length) {
      _vsItems = [];
      list.removeEventListener('scroll', _vsOnScroll);
      list.innerHTML =
        '<div class="flex items-center justify-center h-full min-h-[300px]">' +
        '<div class="text-center max-w-xs px-6">' +
        '<div class="w-16 h-16 rounded-2xl bg-dc-border/10 mx-auto mb-4 flex items-center justify-center">' +
        '<i data-lucide="swords" class="w-8 h-8 text-dc-border/50"></i></div>' +
        '<h3 class="text-sm font-bold text-dc-text/60 mb-2">No Matches Yet</h3>' +
        '<p class="text-xs text-dc-text/40 mb-5">Matches have not been generated for this tournament yet. Generate them here, then continue with scheduling.</p>' +
        '<div class="flex flex-col sm:flex-row items-center justify-center gap-2">' +
        '<button data-click="TOC.matches.generateMatchesFromEmptyState" class="px-4 py-2 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">' +
        '<i data-lucide="swords" class="w-3.5 h-3.5 inline-block mr-1.5"></i>Generate Matches</button>' +
        '<button data-click="TOC.navigate" data-click-args="[&quot;schedule&quot;]" class="px-4 py-2 bg-theme/10 border border-theme/20 text-theme text-xs font-bold uppercase tracking-widest rounded-lg hover:bg-theme/20 transition-colors">' +
        '<i data-lucide="calendar" class="w-3.5 h-3.5 inline-block mr-1.5"></i>Go to Schedule</button>' +
        '</div>' +
        '</div></div>';
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    _vsItems = matches.slice().sort(compareByTimeProximity);
    _vsLastStart = -1;
    _vsLastEnd = -1;

    // Scaffold virtual-scroll sentinel divs
    list.innerHTML =
      '<div id="vs-top" style="height:0"></div>' +
      '<div id="vs-viewport"></div>' +
      '<div id="vs-bottom" style="height:0"></div>';

    list.removeEventListener('scroll', _vsOnScroll);
    list.addEventListener('scroll', _vsOnScroll, { passive: true });

    // Initial render of visible window
    _vsRenderVisible();
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
    if (roundEl) {
      var detailRoundLabel = m.bracket_round_label || ('Round ' + m.round_number);
      roundEl.textContent = detailRoundLabel + (m.scheduled_time ? ' | ' + formatDateTime(m.scheduled_time) : '');
    }

    renderAvatar('detail-avatar-a', m.participant1_avatar_url || m.p1_logo_url || m.participant1_logo_url);
    renderAvatar('detail-avatar-b', m.participant2_avatar_url || m.p2_logo_url || m.participant2_logo_url);

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
    var roomOpen = isRoomOpenState(m.state);

    if (hasLobby || roomOpen) {
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
    var roomLinkAdmin = $('#detail-room-link-admin');
    var roomUrl = '/tournaments/' + slug + '/matches/' + m.id + '/room/';
    if (roomLink) {
      roomLink.href = roomUrl;
      roomLink.classList.toggle('hidden', !roomOpen);
    }
    if (roomLinkAdmin) {
      roomLinkAdmin.href = roomUrl + '?admin=1';
      roomLinkAdmin.classList.toggle('hidden', !roomOpen);
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

    syncWinnerSelectForMatch(m);
    if (inputA) {
      inputA.oninput = function () { syncWinnerSelectForMatch(m); };
    }
    if (inputB) {
      inputB.oninput = function () { syncWinnerSelectForMatch(m); };
    }

    // Football stats sub-form (eFootball / SPORTS only)
    renderFootballStatsEditor(m);

    // AI Score Extractor visibility — hide on BR lobby sessions (those use
    // the dedicated /br-score-screenshot/ endpoint with a leaderboard grid).
    // Also hide on 5v5 team games — the dedicated 5v5 grid takes over.
    var aiBlock = $('#ai-score-extractor');
    var team5v5Block = $('#team-5v5-grid');
    var isBRSession = !!(m && m.lobby_info && m.lobby_info.br_session);
    var is5v5 = is5v5TeamGame();

    if (aiBlock) {
      if (isBRSession || is5v5) {
        aiBlock.classList.add('hidden');
      } else {
        aiBlock.classList.remove('hidden');
      }
      // Reset transient state (file label + button) when match changes.
      var fileEl = $('#ai-score-file');
      if (fileEl) fileEl.value = '';
      var nameEl = $('#ai-score-filename');
      if (nameEl) nameEl.textContent = 'Choose result screenshot…';
      var btn = $('#ai-score-extract-btn');
      if (btn) {
        btn.disabled = false;
        btn.classList.remove('opacity-70', 'cursor-wait');
        var span = btn.querySelector('span');
        if (span) span.textContent = 'Extract';
      }
    }

    // 5v5 KDA Grid — shown for MOBA / tactical shooter games on non-BR matches.
    if (team5v5Block) {
      if (is5v5 && !isBRSession) {
        team5v5Block.classList.remove('hidden');
        // Reset transient extractor state.
        var f5 = $('#team-5v5-file');
        if (f5) f5.value = '';
        var fn5 = $('#team-5v5-filename');
        if (fn5) fn5.textContent = 'Choose scoreboard screenshot…';
        var b5 = $('#team-5v5-extract-btn');
        if (b5) {
          b5.disabled = false;
          b5.classList.remove('opacity-70', 'cursor-wait');
          var s5 = b5.querySelector('span');
          if (s5) s5.textContent = 'Extract';
        }
        // Kill any in-flight progress timer from a previous match — if the
        // admin switches mid-extract, the old progress bar should disappear.
        if (typeof _team5v5StopProgress === 'function') _team5v5StopProgress(false);
        var hint = $('#team-5v5-game-hint');
        if (hint) hint.textContent = team5v5GameLabel();
        // Render an empty grid immediately, then populate rosters async.
        renderTeam5v5Grid(m, { participant1_candidates: [], participant2_candidates: [] });
        fetchTeam5v5Rosters(m);
      } else {
        team5v5Block.classList.add('hidden');
      }
    }

    // Render series UI
    renderSeriesPanel(m);
  }

  /* ============================================================
     5v5 Team KDA Grid (MLBB / Valorant / CS2 / CoD)
  ============================================================ */
  function is5v5TeamGame() {
    var cfg = window.TOC_CONFIG || {};
    var slug = String(cfg.gameSlug || '').toLowerCase();
    var teamSlugs = [
      'mlbb', 'mobile-legends', 'mobilelegends',
      'valorant',
      'cs2', 'csgo', 'cs:go', 'counter-strike', 'counterstrike',
      'cod', 'callofduty', 'call-of-duty',
    ];
    if (teamSlugs.indexOf(slug) !== -1) return true;
    var cat = String(cfg.gameCategory || '').toUpperCase();
    return cat === 'MOBA' || cat === 'FPS' || cat === 'TACTICAL';
  }

  function team5v5GameLabel() {
    var slug = String((window.TOC_CONFIG || {}).gameSlug || '').toLowerCase();
    if (slug === 'mlbb' || slug.indexOf('mobile-legends') !== -1 || slug === 'mobilelegends') return 'MLBB';
    if (slug === 'valorant') return 'Valorant';
    if (slug.indexOf('cs') === 0 || slug.indexOf('counter') === 0) return 'CS2';
    if (slug === 'cod' || slug.indexOf('callofduty') !== -1 || slug.indexOf('call-of-duty') !== -1) return 'Call of Duty';
    return 'MOBA / Tactical';
  }

  function team5v5ScoreColumnLabel() {
    // Game-specific label for the per-player "score" column in the grid.
    var slug = String((window.TOC_CONFIG || {}).gameSlug || '').toLowerCase();
    if (slug === 'mlbb' || slug.indexOf('mobile-legends') !== -1 || slug === 'mobilelegends') return 'Gold';
    if (slug === 'valorant') return 'ACS';
    return 'Score';
  }

  function _team5v5Escape(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function _team5v5OptionsFor(candidates, lockedUserId) {
    // Build <option> set for a player-picker. V2.2 option-text format:
    //   - With Game Passport: "<passport_ign> (<platform_name>)"
    //                         e.g. "1W Pandaaa (Gunda)"
    //                         (parenthetical suppressed when they match,
    //                          to avoid noisy "Pandaaa (Pandaaa)")
    //   - Without Game Passport: just "<platform_name>"
    // The platform sub-line under the <select> still renders for locked rows
    // (see _team5v5BuildRow) — that's the per-row display, separate from the
    // dropdown text.
    var opts = '<option value="">— pick player —</option>';
    var seen = false;
    (candidates || []).forEach(function (c) {
      var sel = (lockedUserId != null && Number(c.user_id) === Number(lockedUserId)) ? ' selected' : '';
      if (sel) seen = true;
      var displayName;
      if (c.passport_ign) {
        var plat = (c.platform_name || '').trim();
        if (plat && plat.toLowerCase() !== c.passport_ign.toLowerCase()) {
          displayName = c.passport_ign + ' (' + plat + ')';
        } else {
          displayName = c.passport_ign;
        }
      } else {
        displayName = (c.platform_name || '').trim() || c.label || ('User #' + c.user_id);
      }
      opts += '<option value="' + Number(c.user_id) + '"' + sel + '>' + _team5v5Escape(displayName) + '</option>';
    });
    // Sub-swap edge case: locked user_id isn't on the listed starter roster.
    if (lockedUserId != null && !seen) {
      opts += '<option value="' + Number(lockedUserId) + '" selected>(locked: user #' + Number(lockedUserId) + ')</option>';
    }
    return opts;
  }

  function _team5v5FindCandidate(candidates, userId) {
    if (userId == null || !candidates) return null;
    for (var i = 0; i < candidates.length; i++) {
      if (Number(candidates[i].user_id) === Number(userId)) return candidates[i];
    }
    return null;
  }

  function _team5v5BuildRow(side, idx, candidates, lockedUserId, aiIgn, p) {
    // ``side`` ∈ {'a','b'} — which team panel this row belongs to.
    // ``lockedUserId`` non-null = AI mapped this row to a known user.
    // ``p`` is the AI-extracted player row (post-validation) when AI ran.
    var locked = lockedUserId != null;
    var agent = (p && p.agent   != null) ? p.agent   : '';
    var k     = (p && p.kills   != null) ? p.kills   : '';
    var d     = (p && p.deaths  != null) ? p.deaths  : '';
    var a     = (p && p.assists != null) ? p.assists : '';
    var acs   = (p && p.acs     != null) ? p.acs     : '';
    var econ  = (p && p.econ    != null) ? p.econ    : '';
    var fb    = (p && p.fb      != null) ? p.fb      : '';
    var plant = (p && p.plants  != null) ? p.plants  : '';
    var defu  = (p && p.defuses != null) ? p.defuses : '';

    var pickerCls = locked
      ? 'w-full bg-dc-panel border border-emerald-500/30 text-white text-xs rounded px-2 py-1.5 focus:border-theme outline-none'
      : 'w-full bg-dc-bg border border-amber-500/40 text-white text-xs rounded px-2 py-1.5 focus:border-theme outline-none';

    // Platform-name sub-line — shown under the picker when locked AND the
    // platform name differs from the Game Passport IGN (otherwise redundant).
    var platformSub = '';
    if (locked) {
      var lockedCand = _team5v5FindCandidate(candidates, lockedUserId);
      var platName = (lockedCand && lockedCand.platform_name) || (p && p.matched_platform_name) || '';
      var ignName  = (lockedCand && lockedCand.passport_ign)  || (p && p.matched_label)         || '';
      if (platName && platName.toLowerCase() !== (ignName || '').toLowerCase()) {
        platformSub = '<div class="text-[9px] text-dc-text/50 mt-0.5 truncate" title="Platform: ' + _team5v5Escape(platName) + '">Platform: <span class="text-dc-text/70">' + _team5v5Escape(platName) + '</span></div>';
      }
    }
    // AI raw IGN hint — shown only when no auto-match (admin needs context).
    var ignHint = (!locked && aiIgn)
      ? '<div class="text-[9px] font-mono text-amber-400/80 mt-0.5 truncate" title="' + _team5v5Escape(aiIgn) + '">Detected: ' + _team5v5Escape(aiIgn) + '</div>'
      : '';

    var numCell = function (val, statKey, ph, max) {
      return '<td class="px-1 py-2"><input type="number" min="0" max="' + max + '" value="' + _team5v5Escape(val) + '" data-team5v5-stat="' + statKey + '" class="w-12 bg-dc-bg border border-dc-border rounded px-1.5 py-1 text-white text-xs text-center focus:border-theme outline-none" placeholder="' + ph + '"></td>';
    };

    return '<tr class="border-t border-dc-border/30" data-team5v5-row data-team5v5-side="' + side + '" data-team5v5-idx="' + idx + '">'
      // Player column — wider, sticky-feeling so the IGN stays visible while scrolling stats
      + '<td class="px-2 py-2 align-top min-w-[180px]">'
      +   '<select class="' + pickerCls + '" data-team5v5-player>'
      +     _team5v5OptionsFor(candidates, lockedUserId)
      +   '</select>'
      +   platformSub
      +   ignHint
      + '</td>'
      // Agent column — short text input
      + '<td class="px-1 py-2 align-top min-w-[80px]">'
      +   '<input type="text" maxlength="24" value="' + _team5v5Escape(agent) + '" data-team5v5-stat="agent" class="w-full bg-dc-bg border border-dc-border rounded px-1.5 py-1 text-white text-xs focus:border-theme outline-none" placeholder="Agent">'
      + '</td>'
      // KDA + ACS
      + numCell(k,   'kills',   'K',   99)
      + numCell(d,   'deaths',  'D',   99)
      + numCell(a,   'assists', 'A',   99)
      + '<td class="px-1 py-2"><input type="number" min="0" max="200000" value="' + _team5v5Escape(acs) + '" data-team5v5-stat="acs" class="w-16 bg-dc-bg border border-dc-border rounded px-1.5 py-1 text-white text-xs text-center focus:border-theme outline-none" placeholder="0"></td>'
      // V2: Econ, FB, Plants, Defuses
      + numCell(econ,  'econ',    'Econ', 99)
      + numCell(fb,    'fb',      'FB',   99)
      + numCell(plant, 'plants',  'P',    99)
      + numCell(defu,  'defuses', 'D',    99)
      + '</tr>';
  }

  function _team5v5BuildPanel(side, teamName, candidates, players) {
    // ``players`` may be empty (initial render) or a 5-element AI mapping.
    var rows = '';
    var acsLabel = team5v5ScoreColumnLabel();
    for (var i = 0; i < 5; i++) {
      var p = (players && players[i]) || null;
      var lockedUserId = p ? p.user_id : null;
      var ign = p ? p.ign : '';
      rows += _team5v5BuildRow(side, i, candidates, lockedUserId, ign, p);
    }
    var emptyRosterBanner = (!candidates || !candidates.length)
      ? '<div class="px-3 py-1.5 text-[10px] text-amber-300 bg-amber-500/10 border-b border-amber-500/30">No locked roster — pick each player manually after extraction.</div>'
      : '';
    var headerSide = side === 'a' ? 'A' : 'B';
    // 10-column V2 header. The whole table scrolls horizontally inside its
    // overflow-x-auto parent on narrow viewports.
    return '<div class="px-3 py-2 bg-dc-panel/60 border-b border-dc-border/40 flex items-center justify-between">'
      +   '<div class="flex items-center gap-2">'
      +     '<span class="text-[9px] font-mono text-dc-text/60 uppercase tracking-widest">Team ' + headerSide + '</span>'
      +     '<span class="text-xs font-bold text-white truncate">' + _team5v5Escape(teamName || ('Team ' + headerSide)) + '</span>'
      +   '</div>'
      +   '<span class="text-[9px] font-mono text-dc-text/40">' + (candidates ? candidates.length : 0) + ' starter(s)</span>'
      + '</div>'
      + emptyRosterBanner
      + '<div class="overflow-x-auto"><table class="text-xs" style="min-width:100%;">'
      +   '<thead class="bg-dc-bg/50">'
      +     '<tr class="text-[9px] font-bold text-dc-text/70 uppercase tracking-widest">'
      +       '<th class="px-2 py-1.5 text-left">Player</th>'
      +       '<th class="px-1 py-1.5 text-center">Agent</th>'
      +       '<th class="px-1 py-1.5 text-center">K</th>'
      +       '<th class="px-1 py-1.5 text-center">D</th>'
      +       '<th class="px-1 py-1.5 text-center">A</th>'
      +       '<th class="px-1 py-1.5 text-center">' + _team5v5Escape(acsLabel) + '</th>'
      +       '<th class="px-1 py-1.5 text-center">Econ</th>'
      +       '<th class="px-1 py-1.5 text-center">FB</th>'
      +       '<th class="px-1 py-1.5 text-center">Plant</th>'
      +       '<th class="px-1 py-1.5 text-center">Defuse</th>'
      +     '</tr>'
      +   '</thead>'
      +   '<tbody>' + rows + '</tbody>'
      + '</table></div>';
  }

  function renderTeam5v5Grid(m, data) {
    // ``data`` shape: {participant1_candidates, participant2_candidates,
    //                  [participant1_players], [participant2_players]}
    if (!m) return;
    var panelA = $('#team-5v5-panel-a');
    var panelB = $('#team-5v5-panel-b');
    if (!panelA || !panelB) return;
    var nameA = m.participant1_name || 'Team A';
    var nameB = m.participant2_name || 'Team B';
    var candA = (data && data.participant1_candidates) || [];
    var candB = (data && data.participant2_candidates) || [];
    var playersA = (data && data.participant1_players) || null;
    var playersB = (data && data.participant2_players) || null;
    panelA.innerHTML = _team5v5BuildPanel('a', nameA, candA, playersA);
    panelB.innerHTML = _team5v5BuildPanel('b', nameB, candB, playersB);
  }

  // Cached rosters keyed by matchId so we don't re-fetch when the admin
  // re-selects the same match.
  var _team5v5RosterCache = {};

  async function fetchTeam5v5Rosters(m) {
    if (!m || !m.id) return;
    var cached = _team5v5RosterCache[m.id];
    if (cached) {
      renderTeam5v5Grid(m, cached);
      return;
    }
    try {
      var resp = await API.get('matches/' + m.id + '/team-5v5-rosters/');
      _team5v5RosterCache[m.id] = resp;
      // Only re-render if this match is still the selected one.
      if (selectedMatchId === m.id) renderTeam5v5Grid(m, resp);
    } catch (e) {
      // Non-fatal — admin can still run AI extract; mapping just won't auto-link.
      console.warn('[team-5v5] roster fetch failed', e);
    }
  }

  function onTeam5v5FilePicked() {
    var input = $('#team-5v5-file');
    var label = $('#team-5v5-filename');
    if (!input || !label) return;
    var f = input.files && input.files[0];
    label.textContent = f ? f.name : 'Choose scoreboard screenshot…';
  }

  // ─── AI extraction progress UI ────────────────────────────────────────
  // "Soft progress" bar — fills toward 95% based on elapsed time so the admin
  // sees the bar move during the ~60s Gemini call without us lying about
  // actual completion. Hits 100% only when the response actually lands.
  // Stage messages cycle to give the wait a sense of motion.
  var _team5v5ProgressTimer = null;
  var _team5v5ProgressStart = 0;
  var _team5v5Stages = [
    { at: 0,  msg: 'Uploading screenshot…' },
    { at: 4,  msg: 'Processing image…' },
    { at: 10, msg: 'Reading scoreboard layout…' },
    { at: 22, msg: 'Identifying teams by colour…' },
    { at: 35, msg: 'Extracting player KDA…' },
    { at: 50, msg: 'Reading agents + economy…' },
    { at: 65, msg: 'Matching roster IGNs…' },
    { at: 85, msg: 'Almost there…' },
  ];

  function _team5v5UpdateProgress() {
    var elapsedSec = (Date.now() - _team5v5ProgressStart) / 1000;
    // 0..60s → 0..85% linearly; 60..90s → 85..95% slowing; 90s+ stays at 95%.
    var pct;
    if (elapsedSec < 60)      pct = (elapsedSec / 60) * 85;
    else if (elapsedSec < 90) pct = 85 + ((elapsedSec - 60) / 30) * 10;
    else                       pct = 95;

    var fill  = $('#team-5v5-progress-fill');
    var pctEl = $('#team-5v5-progress-percent');
    var msgEl = $('#team-5v5-progress-message-text');

    if (fill)  fill.style.width = pct.toFixed(1) + '%';
    if (pctEl) pctEl.textContent = Math.floor(pct) + '%';

    if (msgEl) {
      var stage = _team5v5Stages[0];
      for (var i = _team5v5Stages.length - 1; i >= 0; i--) {
        if (elapsedSec >= _team5v5Stages[i].at) { stage = _team5v5Stages[i]; break; }
      }
      if (msgEl.textContent !== stage.msg) msgEl.textContent = stage.msg;
    }
  }

  function _team5v5StartProgress() {
    var wrap = $('#team-5v5-progress');
    if (!wrap) return;
    wrap.classList.remove('hidden');
    _team5v5ProgressStart = Date.now();
    if (_team5v5ProgressTimer) clearInterval(_team5v5ProgressTimer);
    _team5v5UpdateProgress();
    _team5v5ProgressTimer = setInterval(_team5v5UpdateProgress, 200);
  }

  function _team5v5StopProgress(success) {
    if (_team5v5ProgressTimer) {
      clearInterval(_team5v5ProgressTimer);
      _team5v5ProgressTimer = null;
    }
    var wrap  = $('#team-5v5-progress');
    var fill  = $('#team-5v5-progress-fill');
    var pctEl = $('#team-5v5-progress-percent');
    var msgEl = $('#team-5v5-progress-message-text');

    if (success && fill && pctEl) {
      // Jump to 100% with a satisfying "Complete!" beat, then hide.
      fill.style.width = '100%';
      pctEl.textContent = '100%';
      if (msgEl) msgEl.textContent = 'Complete!';
      setTimeout(function () {
        if (wrap)  wrap.classList.add('hidden');
        if (fill)  fill.style.width = '0%';
        if (pctEl) pctEl.textContent = '0%';
        if (msgEl) msgEl.textContent = 'Initialising…';
      }, 700);
    } else {
      // Error / abort / match switch — reset and hide silently.
      if (wrap)  wrap.classList.add('hidden');
      if (fill)  fill.style.width = '0%';
      if (pctEl) pctEl.textContent = '0%';
      if (msgEl) msgEl.textContent = 'Initialising…';
    }
  }

  async function extractTeam5v5AI() {
    if (!selectedMatchId) { toast('Select a match first.', 'error'); return; }
    var input = $('#team-5v5-file');
    var btn   = $('#team-5v5-extract-btn');
    if (!input || !btn) return;

    var f = input.files && input.files[0];
    if (!f) { toast('Choose a screenshot file first.', 'info'); return; }
    if (f.size > 8 * 1024 * 1024) {
      toast('Screenshot too large (max 8 MB).', 'error');
      return;
    }

    var span = btn.querySelector('span');
    var origText = span ? span.textContent : 'Extract';
    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-wait');
    if (span) span.textContent = 'Extracting…';
    var submitBtn = document.querySelector('[data-click="TOC.matches.submitScore"]');
    if (submitBtn) submitBtn.disabled = true;
    _team5v5StartProgress();

    try {
      var fd = new FormData();
      fd.append('match_id', String(selectedMatchId));
      fd.append('screenshot', f);
      // V2 Valorant extraction (10 players × full economy stats) routinely
      // takes 60-90s on Gemini Flash with the detailed prompt. We give it a
      // 2-minute window so a slow-but-correct response isn't aborted client-side.
      var resp = await API('brackets/team-5v5-score-screenshot/', {
        method:  'POST',
        body:    fd,
        timeout: 120000,
      });
      // Cache the rosters Gemini returned (they're authoritative for this run).
      _team5v5RosterCache[selectedMatchId] = {
        participant1_candidates: resp.participant1_candidates || [],
        participant2_candidates: resp.participant2_candidates || [],
      };
      _team5v5StopProgress(true);
      _applyTeam5v5AIResult(resp);
    } catch (e) {
      _team5v5StopProgress(false);
      toast('Scoreboard scan failed: ' + (e?.message || 'Unknown error'), 'error');
    } finally {
      btn.disabled = false;
      btn.classList.remove('opacity-70', 'cursor-wait');
      if (span) span.textContent = origText;
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  function _applyTeam5v5AIResult(resp) {
    if (!resp) { toast('Scan returned no data.', 'error'); return; }

    var m = allMatches.find(function (x) { return x.id === selectedMatchId; }) || {
      id: selectedMatchId,
      participant1_name: resp.participant1_name,
      participant2_name: resp.participant2_name,
    };

    // Re-render both panels with the AI-mapped players + freshly cached rosters.
    renderTeam5v5Grid(m, {
      participant1_candidates: resp.participant1_candidates || [],
      participant2_candidates: resp.participant2_candidates || [],
      participant1_players:    resp.participant1_players    || [],
      participant2_players:    resp.participant2_players    || [],
    });

    // V2: always populate team-score inputs. The banner numbers are read
    // reliably even when slot mapping (which team is participant1 vs 2) is
    // uncertain — we keep a SEPARATE warning toast for that case so the admin
    // verifies the slot order, not the digits.
    var inputA = $('#score-input-a');
    var inputB = $('#score-input-b');
    var p1Score = (resp.participant1_score != null) ? resp.participant1_score : resp.team_a_score;
    var p2Score = (resp.participant2_score != null) ? resp.participant2_score : resp.team_b_score;
    if (inputA && p1Score != null) {
      inputA.value = String(p1Score);
      inputA.dispatchEvent(new Event('input', { bubbles: true }));
    }
    if (inputB && p2Score != null) {
      inputB.value = String(p2Score);
      inputB.dispatchEvent(new Event('input', { bubbles: true }));
    }

    var teamConf = String(resp.team_mapping_confidence || 'none').toLowerCase();
    if (teamConf !== 'high') {
      var seenLabel = '';
      try {
        var ta = (resp.team_a && resp.team_a.team_name) || '';
        var tb = (resp.team_b && resp.team_b.team_name) || '';
        var sa = (resp.team_a_score != null) ? resp.team_a_score : (resp.team_a && resp.team_a.score);
        var sb = (resp.team_b_score != null) ? resp.team_b_score : (resp.team_b && resp.team_b.score);
        if (ta && tb) seenLabel = ' (Detected: ' + ta + ' ' + sa + '–' + sb + ' ' + tb + ')';
      } catch (_) { /* ignore */ }
      toast('Team detection confidence ' + teamConf + ' — verify which team is A vs B before submitting.' + seenLabel, 'warning');
    }

    // Player-level summary toast.
    var p1Players = Array.isArray(resp.participant1_players) ? resp.participant1_players : [];
    var p2Players = Array.isArray(resp.participant2_players) ? resp.participant2_players : [];
    var totalRows = p1Players.length + p2Players.length;
    var matched = p1Players.concat(p2Players).filter(function (r) {
      return r && r.user_id != null && r.mapping_confidence !== 'none';
    }).length;
    var needsCheck = totalRows - matched;
    var p1Count = (resp.participant1_candidates || []).length;
    var p2Count = (resp.participant2_candidates || []).length;

    if (p1Count === 0 || p2Count === 0) {
      // Edge case: no locked starter roster on at least one side.
      var which = (p1Count === 0 && p2Count === 0)
        ? 'both teams'
        : (p1Count === 0 ? (resp.participant1_name || 'Team A') : (resp.participant2_name || 'Team B'));
      toast(which + ' has no locked starter roster — pick each player manually before submitting.', 'warning');
    } else if (needsCheck === 0 && totalRows > 0) {
      toast('Auto-matched ' + matched + '/' + totalRows + ' players. Review and submit.', 'success');
    } else if (matched === 0) {
      toast('Couldn’t match any players to your roster — please pick each row manually.', 'warning');
    } else {
      toast('Auto-matched ' + matched + '/' + totalRows + ' players. ' + needsCheck + ' need manual verification.', 'warning');
    }
  }

  function _team5v5ReadSide(side) {
    // Read the live grid state for one side ('a' or 'b'). Empty player picks
    // are still included so the backend can skip them — keeps the UI a faithful
    // mirror of what would be saved.
    var rows = document.querySelectorAll('[data-team5v5-row][data-team5v5-side="' + side + '"]');
    var out = [];
    rows.forEach(function (tr) {
      var sel = tr.querySelector('[data-team5v5-player]');
      var uid = sel ? Number(sel.value || 0) : 0;
      var row = { user_id: uid > 0 ? uid : null };
      tr.querySelectorAll('[data-team5v5-stat]').forEach(function (inp) {
        var key = inp.getAttribute('data-team5v5-stat');
        if (!key) return;
        if (key === 'agent') {
          row[key] = inp.value || '';
        } else {
          row[key] = Number(inp.value || 0);
        }
      });
      out.push(row);
    });
    return out;
  }

  async function saveTeam5v5Stats() {
    if (!selectedMatchId) { toast('Select a match first.', 'error'); return; }
    var btn = $('#team-5v5-save-btn');
    var span = btn ? btn.querySelector('span') : null;
    var origText = span ? span.textContent : 'Save Player Stats';

    var payload = {
      participant1_players: _team5v5ReadSide('a'),
      participant2_players: _team5v5ReadSide('b'),
    };
    var totalPicked = payload.participant1_players.concat(payload.participant2_players)
      .filter(function (r) { return r.user_id != null; }).length;
    if (totalPicked === 0) {
      toast('Pick at least one player before saving.', 'info');
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.classList.add('opacity-70', 'cursor-wait');
      if (span) span.textContent = 'Saving…';
    }
    try {
      var resp = await API.post('matches/' + selectedMatchId + '/team-5v5-player-stats/', payload);
      toast('Saved ' + (resp.saved_count || 0) + ' player stat row(s).', 'success');
      // Refresh cached saved-stats so a subsequent match-reselect shows what
      // we just wrote (not the stale AI snapshot we cached after extract).
      delete _team5v5RosterCache[selectedMatchId];
    } catch (e) {
      toast('Save failed: ' + (parseApiError(e) || 'Unknown error'), 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.classList.remove('opacity-70', 'cursor-wait');
        if (span) span.textContent = origText;
      }
    }
  }


  /* ============================================================
     AI Score Extractor (Gemini Vision OCR for 1v1 sports screens)
  ============================================================ */
  function onSportsFilePicked() {
    var input = $('#ai-score-file');
    var label = $('#ai-score-filename');
    if (!input || !label) return;
    var f = input.files && input.files[0];
    label.textContent = f ? f.name : 'Choose result screenshot…';
  }

  async function extractScoreViaAI() {
    if (!selectedMatchId) { toast('Select a match first.', 'error'); return; }
    var input = $('#ai-score-file');
    var btn   = $('#ai-score-extract-btn');
    if (!input || !btn) return;

    var f = input.files && input.files[0];
    if (!f) { toast('Choose a screenshot file first.', 'info'); return; }

    // Cap upload at 8 MB to match the backend ceiling (avoids burning a
    // round-trip on a doomed request).
    if (f.size > 8 * 1024 * 1024) {
      toast('Screenshot too large (max 8 MB).', 'error');
      return;
    }

    var span = btn.querySelector('span');
    var origText = span ? span.textContent : 'Extract';
    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-wait');
    if (span) span.textContent = 'Extracting…';
    // Disable the score Submit while extracting so the admin can't race
    // a partial pre-fill into the API.
    var submitBtn = document.querySelector('[data-click="TOC.matches.submitScore"]');
    if (submitBtn) submitBtn.disabled = true;

    try {
      var fd = new FormData();
      fd.append('match_id', String(selectedMatchId));
      fd.append('screenshot', f);
      var resp = await API.post('brackets/sports-score-screenshot/', fd);
      _applySportsAIResult(resp);
    } catch (e) {
      toast('Scoreboard scan failed: ' + (e?.message || 'Unknown error'), 'error');
    } finally {
      btn.disabled = false;
      btn.classList.remove('opacity-70', 'cursor-wait');
      if (span) span.textContent = origText;
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  function _applySportsAIResult(resp) {
    if (!resp) {
      toast('Scan returned no data.', 'error');
      return;
    }
    var inputA = $('#score-input-a');
    var inputB = $('#score-input-b');
    if (!inputA || !inputB) return;

    var confidence = String(resp.mapping_confidence || 'none').toLowerCase();
    var p1 = resp.participant1_score;
    var p2 = resp.participant2_score;
    var hs = resp.home_score;
    var as = resp.away_score;
    var hName = resp.home_team || 'home';
    var aName = resp.away_team || 'away';

    if (confidence === 'high' && p1 != null && p2 != null) {
      // Confident slot mapping — pre-fill both inputs and let the admin
      // review without further prompting.
      inputA.value = String(p1);
      inputB.value = String(p2);
      inputA.dispatchEvent(new Event('input', { bubbles: true }));
      inputB.dispatchEvent(new Event('input', { bubbles: true }));
      toast('Scanned ' + p1 + '–' + p2 + '. Review and submit.', 'success');
      return;
    }

    // Low / none confidence — fill what we can but warn the admin to verify.
    // Strategy: if mapping returned anything, drop it in but flag it; else
    // just write home into A and away into B as a best guess.
    if (p1 != null && p2 != null) {
      inputA.value = String(p1);
      inputB.value = String(p2);
    } else if (hs != null && as != null) {
      inputA.value = String(hs);
      inputB.value = String(as);
    }
    inputA.dispatchEvent(new Event('input', { bubbles: true }));
    inputB.dispatchEvent(new Event('input', { bubbles: true }));

    var seenLabel = (hs != null && as != null)
      ? ' (Detected: ' + hName + ' ' + hs + '–' + as + ' ' + aName + ')'
      : '';
    toast('Detection confidence low — please verify scores manually before submitting.' + seenLabel, 'warning');
  }


  /* -- Football Stats Editor (eFootball / SPORTS games) -- */
  function isFootballGame() {
    var cfg = window.TOC_CONFIG || {};
    var slug = String(cfg.gameSlug || '').toLowerCase();
    if (['efootball', 'fifa', 'pes', 'football'].indexOf(slug) !== -1) return true;
    var cat = String(cfg.gameCategory || '').toUpperCase();
    return cat === 'SPORTS';
  }

  function renderFootballStatsEditor(m) {
    var section = document.getElementById('score-football-stats');
    if (!section) return;
    if (!isFootballGame()) { section.classList.add('hidden'); return; }
    section.classList.remove('hidden');

    var t1Name = m.participant1_name || 'Team A';
    var t2Name = m.participant2_name || 'Team B';
    ['pens', 'poss', 'shots', 'sot', 'passes', 'pass-acc'].forEach(function (key) {
      var l1 = document.getElementById('score-football-t1-label-' + key);
      var l2 = document.getElementById('score-football-t2-label-' + key);
      if (l1) l1.textContent = t1Name;
      if (l2) l2.textContent = t2Name;
    });

    var existing = ((m.lobby_info || {}).football_stats) || {};
    if (typeof existing !== 'object') existing = {};
    var et1 = (existing.team1 && typeof existing.team1 === 'object') ? existing.team1 : {};
    var et2 = (existing.team2 && typeof existing.team2 === 'object') ? existing.team2 : {};

    function setVal(id, value) {
      var el = document.getElementById(id);
      if (el) el.value = (value == null) ? '' : String(value);
    }
    setVal('score-football-t1-pens', et1.penalties);
    setVal('score-football-t2-pens', et2.penalties);
    setVal('score-football-t1-poss', et1.possession_pct);
    setVal('score-football-t2-poss', et2.possession_pct);
    setVal('score-football-t1-shots', et1.shots);
    setVal('score-football-t2-shots', et2.shots);
    setVal('score-football-t1-sot', et1.shots_on_target);
    setVal('score-football-t2-sot', et2.shots_on_target);
    setVal('score-football-t1-passes', et1.passes_completed);
    setVal('score-football-t2-passes', et2.passes_completed);
    setVal('score-football-t1-pass-acc', et1.pass_accuracy_pct);
    setVal('score-football-t2-pass-acc', et2.pass_accuracy_pct);

    var pensCheckbox = document.getElementById('score-football-has-pens');
    if (pensCheckbox) {
      pensCheckbox.checked = !!existing.has_penalties;
    }
  }

  function collectFootballStats(m) {
    if (!isFootballGame()) return null;
    function readInt(id) {
      var el = document.getElementById(id);
      if (!el || el.value === '' || el.value == null) return null;
      var n = parseInt(el.value, 10);
      return Number.isFinite(n) ? n : null;
    }
    function maybe(obj, key, value) { if (value !== null) obj[key] = value; }

    var t1 = { display_name: m.participant1_name || 'Team A' };
    var t2 = { display_name: m.participant2_name || 'Team B' };
    maybe(t1, 'penalties', readInt('score-football-t1-pens'));
    maybe(t2, 'penalties', readInt('score-football-t2-pens'));
    maybe(t1, 'possession_pct', readInt('score-football-t1-poss'));
    maybe(t2, 'possession_pct', readInt('score-football-t2-poss'));
    maybe(t1, 'shots', readInt('score-football-t1-shots'));
    maybe(t2, 'shots', readInt('score-football-t2-shots'));
    maybe(t1, 'shots_on_target', readInt('score-football-t1-sot'));
    maybe(t2, 'shots_on_target', readInt('score-football-t2-sot'));
    maybe(t1, 'passes_completed', readInt('score-football-t1-passes'));
    maybe(t2, 'passes_completed', readInt('score-football-t2-passes'));
    maybe(t1, 'pass_accuracy_pct', readInt('score-football-t1-pass-acc'));
    maybe(t2, 'pass_accuracy_pct', readInt('score-football-t2-pass-acc'));
    var pensCheckbox = document.getElementById('score-football-has-pens');
    var hasPens = pensCheckbox ? !!pensCheckbox.checked : false;
    return { team1: t1, team2: t2, has_penalties: hasPens };
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
      '<button data-click="TOC.matches.confirmAddGameScore" data-click-args="[' + nextGame + ']" class="flex-1 py-2.5 bg-dc-success/10 border border-dc-success/20 text-dc-success text-xs font-bold rounded-lg hover:bg-dc-success/20 transition-colors">Save Game ' + nextGame + '</button>' +
      '<button data-click="TOC.matches.closeGameScoreModal" class="px-4 py-2.5 bg-dc-panel border border-dc-border text-dc-text text-xs font-bold rounded-lg hover:bg-white/5 transition-colors">Cancel</button>' +
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
        '<span class="text-xs text-dc-text font-mono">' + (e.time ? formatDateTime(e.time) : '') + '</span>' +
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
    var selected = allMatches.find(function (x) { return x.id === selectedMatchId; });
    var drawAllowed = isDrawAllowed(selected);
    var winnerSide = normalizeWinnerSide(winner);

    if (p1 === p2) {
      if (drawAllowed) {
        winnerSide = 'draw';
      } else if (!winnerSide) {
        toast('Tie scores require selecting a winner for this format.', 'error');
        return;
      }
    } else if (winnerSide === 'draw') {
      toast('Draw can only be selected when scores are tied.', 'error');
      return;
    } else if (!winnerSide) {
      winnerSide = p1 > p2 ? '1' : '2';
    }

    if (winnerSide === 'draw' && !drawAllowed) {
      toast('Draw results are disabled for this match format.', 'error');
      return;
    }

    var body = { participant1_score: p1, participant2_score: p2 };
    if (winnerSide) body.winner_side = winnerSide;
    if (note) body.admin_note = note;

    var football = collectFootballStats(selected || {
      participant1_name: $('#score-label-a')?.textContent || 'Team A',
      participant2_name: $('#score-label-b')?.textContent || 'Team B',
    });
    if (football) body.football_stats = football;

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
      '<button data-click="TOC.matches.confirmReschedule" data-click-args="[' + mid + ']" class="w-full py-3 bg-dc-warning text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Request Reschedule</button></div>';
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
      '<button data-click="TOC.matches.confirmForfeit" data-click-args="[' + mid + ', ' + m.participant1_id + ']" class="py-3 bg-dc-danger/10 border border-dc-danger/30 text-dc-danger text-sm font-bold rounded-lg hover:bg-dc-danger/20 transition-colors">' + esc(m.participant1_name || 'Team A') + '</button>' +
      '<button data-click="TOC.matches.confirmForfeit" data-click-args="[' + mid + ', ' + m.participant2_id + ']" class="py-3 bg-dc-danger/10 border border-dc-danger/30 text-dc-danger text-sm font-bold rounded-lg hover:bg-dc-danger/20 transition-colors">' + esc(m.participant2_name || 'Team B') + '</button>' +
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
        evTabsHtml += '<button data-click="TOC.matches.switchEvidence" data-click-args="[' + i + ']" class="px-2.5 py-1 rounded text-xs font-bold transition-colors ' +
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
      evidenceHtml = '<img id="evidence-img" src="' + esc(evidenceSources[0].url) + '" alt="Evidence" class="max-w-none select-none" draggable="false" style="transform: scale(1) translate(0px, 0px); transition: transform 0.15s ease;" data-fallback="hide-show-next">' +
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
      '<button data-click="TOC.matches.closeOverlay" data-click-args="[&quot;verify-overlay&quot;]" class="w-8 h-8 rounded-lg bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="x" class="w-4 h-4 text-dc-text"></i></button></div></div>' +
      '<div class="mx-4 mt-4 p-3 rounded-lg border ' + b.cls + ' flex items-center gap-2"><span class="text-base">' + b.icon + '</span><div>' +
      '<span class="text-xs font-black uppercase tracking-widest">' + esc(vs.label || 'Pending') + '</span>' +
      '<span class="text-xs ml-2 opacity-80">' + esc(vs.detail || '') + '</span></div></div>' +
      '<div class="flex flex-1 overflow-hidden mt-4 mx-4 mb-4 gap-4" style="min-height:0">' +
      '<div class="flex-1 flex flex-col bg-dc-bg border border-dc-border rounded-xl overflow-hidden">' +
      '<div class="flex items-center justify-between p-3 border-b border-dc-border bg-dc-panel/50"><div class="flex items-center gap-2">' +
      '<i data-lucide="image" class="w-3.5 h-3.5 text-theme"></i><span class="text-xs font-bold text-white uppercase tracking-widest">Evidence Viewer</span>' + evTabsHtml + '</div>' +
      '<div class="flex items-center gap-1">' +
      '<button data-click="TOC.matches.zoomEvidence" data-click-args="[-1]" class="w-7 h-7 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="zoom-out" class="w-3.5 h-3.5 text-dc-text"></i></button>' +
      '<span id="verify-zoom-level" class="text-xs font-mono text-dc-text w-12 text-center">100%</span>' +
      '<button data-click="TOC.matches.zoomEvidence" data-click-args="[1]" class="w-7 h-7 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="zoom-in" class="w-3.5 h-3.5 text-dc-text"></i></button>' +
      '<button data-click="TOC.matches.resetZoom" class="w-7 h-7 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="maximize-2" class="w-3.5 h-3.5 text-dc-text"></i></button></div></div>' +
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
      '<button data-click="TOC.matches.verifyAction" data-click-args="[' + id + ',&quot;confirm&quot;]" class="w-full py-3 bg-dc-success text-dc-bg text-xs font-black uppercase tracking-widest rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2 ' +
      (m.state === 'completed' ? 'opacity-40 pointer-events-none' : '') + '">\u2705 Confirm & Finalize</button>' +
      '<button data-click="TOC.matches.verifyAction" data-click-args="[' + id + ',&quot;dispute&quot;]" class="w-full py-3 bg-dc-danger/20 border border-dc-danger/30 text-dc-danger text-xs font-black uppercase tracking-widest rounded-xl hover:bg-dc-danger/30 transition-colors flex items-center justify-center gap-2 ' +
      (m.state === 'disputed' ? 'opacity-40 pointer-events-none' : '') + '">\u274C Open Dispute</button>' +
      '<button data-click="TOC.matches.verifyAction" data-click-args="[' + id + ',&quot;note&quot;]" class="w-full py-3 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-black uppercase tracking-widest rounded-xl hover:bg-white/5 transition-colors flex items-center justify-center gap-2">\u{1F4DD} Add Admin Note</button>' +
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
    modal.innerHTML = '<div class="absolute inset-0 bg-black/80 backdrop-blur-md" data-click="TOC.matches.closeOverlay" data-click-args="[&quot;' + id + '&quot;]"></div>' +
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
    modal.innerHTML = '<div class="absolute inset-0 bg-black/80 backdrop-blur-md" data-click="TOC.matches.closeOverlay" data-click-args="[&quot;' + id + '&quot;]"></div>' +
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
            return '<button data-click="TOC.matches.doVetoAction" data-click-pass="dataset.map" data-map="' + _vetoEsc(mp.map_name) + '" '
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
        // Scroll virtual-scroll container to ensure card is visible
        var vsIdx = _vsItems.findIndex(function(m) { return m.id === filteredMatches[next].id; });
        if (vsIdx >= 0) {
          var list = $('#match-list');
          if (list) list.scrollTop = Math.max(0, vsIdx * CARD_H - list.clientHeight / 2);
        }
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
    if (!matchesPagination.page_size) {
      matchesPagination.page_size = DEFAULT_PAGE_SIZE;
    }
    // Default to knockout tab for group_playoff tournaments in knockout stage
    var cfg = window.TOC_CONFIG || {};
    var fmt = (cfg.tournamentFormat || '').toLowerCase();
    var stage = (cfg.currentStage || '').toLowerCase();
    if (fmt === 'group_playoff' && stage === 'knockout_stage' && !activeStageFilter) {
      activeStageFilter = 'knockout';
    }
    refresh({ keepPage: true });
    switchDetailTab('score');
    if (typeof lucide !== 'undefined') lucide.createIcons();
    if (!_matchesAutoRefreshTimer) {
      _matchesAutoRefreshTimer = setInterval(() => {
        if (!isMatchesTabActive()) return;
        refresh({ silent: true, keepPage: true });
      }, MATCHES_AUTO_REFRESH_MS);
    }
  }

  document.addEventListener('keydown', handleKeyboard);

  window.TOC = window.TOC || {};
  window.TOC.matches = {
    init: init, refresh: refresh, debouncedRefresh: debouncedRefresh,
    nextPage: nextPage, prevPage: prevPage,
    selectMatch: selectMatch, clearDetail: clearDetail, filterGroup: filterGroup, filterStage: filterStage,
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
    // AI Score Extractor (Gemini Vision OCR)
    onSportsFilePicked: onSportsFilePicked,
    extractScoreViaAI: extractScoreViaAI,
    // 5v5 Team KDA Grid (MOBA / Tactical Shooter OCR)
    onTeam5v5FilePicked: onTeam5v5FilePicked,
    extractTeam5v5AI: extractTeam5v5AI,
    saveTeam5v5Stats: saveTeam5v5Stats,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'matches') init();
  });

  document.addEventListener('toc:timeprefs-updated', function () {
    if (!allMatches.length) return;
    applyGroupFilter();
    if (selectedMatchDetail) {
      renderAuditTrail(selectedMatchDetail);
      if (selectedMatchDetail.match) {
        renderDetailHeader(selectedMatchDetail.match);
      }
    }
    setMatchesSyncStatus('ok');
  });

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden && isMatchesTabActive()) {
      const queryKey = currentQueryKey();
      if (!hasFreshCache(queryKey)) refresh({ silent: true, keepPage: true });
    }
  });
})();
