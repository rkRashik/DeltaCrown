/**
 * TOC Schedule Module — Sprint 27 (Complete Rewrite)
 *
 * World-class schedule manager with:
 *  - 3 view modes: Timeline (Gantt), List (Table), Calendar (Day Grid)
 *  - Conflict detection with visual indicators
 *  - Inline reschedule per match
 *  - Advanced filters (group, round, state, date)
 *  - Smart stats (estimated completion, matches/day, conflicts)
 *  - Auto-schedule with smart defaults
 *  - Bulk shift & break insertion
 *  - Timezone-aware display
 *  - Keyboard shortcuts (Ctrl+1/2/3 for views)
 *
 * Inspired by: Toornament, start.gg, FACEIT scheduling UX
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel, ctx) => (ctx || document).querySelector(sel);
  const $$ = (sel, ctx) => [...((ctx || document).querySelectorAll(sel))];

  /* ═══════════════════════════════════════════════════════════════
   *  Constants & State
   * ═══════════════════════════════════════════════════════════════ */

  const MATCH_STATES = {
    scheduled:      { label: 'Scheduled',    icon: 'clock',          color: 'bg-dc-info/20 text-dc-info border-dc-info/30',         dot: 'bg-dc-info' },
    check_in:       { label: 'Check-in',     icon: 'user-check',     color: 'bg-dc-warning/20 text-dc-warning border-dc-warning/30', dot: 'bg-dc-warning' },
    ready:          { label: 'Ready',        icon: 'check-circle-2', color: 'bg-dc-success/20 text-dc-success border-dc-success/30', dot: 'bg-dc-success' },
    live:           { label: 'Live',         icon: 'play-circle',    color: 'bg-dc-success/20 text-dc-success border-dc-success/30', dot: 'bg-dc-success animate-pulse' },
    pending_result: { label: 'Pending',      icon: 'hourglass',      color: 'bg-dc-warning/20 text-dc-warning border-dc-warning/30', dot: 'bg-dc-warning' },
    completed:      { label: 'Completed',    icon: 'check',          color: 'bg-dc-text/10 text-dc-text border-dc-border',           dot: 'bg-dc-text/40' },
    disputed:       { label: 'Disputed',     icon: 'shield-alert',   color: 'bg-dc-danger/20 text-dc-danger border-dc-danger/30',   dot: 'bg-dc-danger' },
    forfeit:        { label: 'Forfeit',      icon: 'flag',           color: 'bg-dc-danger/10 text-dc-danger/60 border-dc-danger/20', dot: 'bg-dc-danger/40' },
    cancelled:      { label: 'Cancelled',    icon: 'x-circle',       color: 'bg-dc-danger/10 text-dc-text/50 border-dc-border',     dot: 'bg-dc-text/20' },
  };

  let state = {
    data: null,
    viewMode: 'timeline',   // timeline | list | calendar
    filters: {
      group: '',
      round: '',
      state: '',
      search: '',
      dateFrom: '',
      dateTo: '',
    },
    conflicts: [],
    conflictMatchIds: new Set(),
    sortKey: 'time',         // time | round | state | match
    sortAsc: true,
    showLocalTime: true,
  };

  const CACHE_TTL_MS = 20000;
  const AUTO_REFRESH_MS = 45000;
  const STAT_IDS = ['total-matches', 'scheduled', 'live', 'completed', 'conflicts', 'est-end'];

  let inflightPromise = null;
  let activeRequestId = 0;
  let lastFetchedAt = 0;
  let autoRefreshTimer = null;
  let _initialized = false;

  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }
  function _esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

  function isScheduleTabActive() {
    return (window.location.hash || '').replace('#', '') === 'schedule';
  }

  function hasFreshCache() {
    return !!state.data && (Date.now() - lastFetchedAt) < CACHE_TTL_MS;
  }

  function setSyncStatus(mode, note) {
    const el = $('#schedule-sync-status');
    if (!el) return;
    if (mode === 'loading') {
      el.className = 'text-[10px] font-mono text-dc-warning mt-1';
      el.textContent = note || 'Syncing schedule...';
      return;
    }
    if (mode === 'error') {
      el.className = 'text-[10px] font-mono text-dc-danger mt-1';
      el.textContent = note || 'Sync failed';
      return;
    }
    if (lastFetchedAt > 0) {
      el.className = 'text-[10px] font-mono text-dc-text mt-1';
      el.textContent = 'Last sync ' + new Date(lastFetchedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return;
    }
    el.className = 'text-[10px] font-mono text-dc-text mt-1';
    el.textContent = 'Not synced yet';
  }

  function setErrorBanner(message) {
    const el = $('#schedule-error-banner');
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
          <p class="text-xs font-bold text-white">Schedule request failed</p>
          <p class="text-[11px] text-dc-text mt-1">${_esc(message)}</p>
          <button type="button" class="mt-2 px-2.5 py-1 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" onclick="TOC.schedule.refresh({ force: true })">Retry now</button>
        </div>
      </div>`;
    _reinitIcons();
  }

  function setLoading(loading) {
    STAT_IDS.forEach((id) => {
      const el = $(`#sched-${id}`);
      if (!el) return;
      el.classList.toggle('toc-loading-value', loading);
    });
    const content = getScheduleContainer();
    if (content) {
      content.classList.toggle('toc-panel-loading', loading);
      if (loading) content.setAttribute('aria-busy', 'true');
      else content.removeAttribute('aria-busy');
    }
  }

  function getScheduleContainer() {
    const panel = $('[data-tab-content="schedule"]');
    if (!panel) return null;
    return $('#schedule-content', panel);
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Data Fetching
   * ═══════════════════════════════════════════════════════════════ */

  async function refresh(options) {
    const opts = options || {};
    const force = opts.force === true;
    const silent = opts.silent === true;

    if (state.data && !force) {
      renderAll();
      if (hasFreshCache()) return state.data;
    }

    if (inflightPromise && !force) return inflightPromise;

    if (!silent) {
      setLoading(true);
      setSyncStatus('loading', state.data ? 'Refreshing schedule...' : 'Loading schedule...');
    }

    const requestId = ++activeRequestId;
    inflightPromise = (async () => {
      try {
        const data = await API.get('schedule/');
        if (requestId !== activeRequestId) return state.data || data;
        state.data = data;
        lastFetchedAt = Date.now();

        // Build conflict lookup set
        state.conflicts = data.conflicts || [];
        state.conflictMatchIds = new Set();
        state.conflicts.forEach(c => {
          state.conflictMatchIds.add(c.match_a);
          state.conflictMatchIds.add(c.match_b);
        });

        renderAll();
        setLoading(false);
        setErrorBanner('');
        setSyncStatus('ok');
        return data;
      } catch (e) {
        if (requestId !== activeRequestId) return state.data;
        const detail = e && e.message ? String(e.message) : 'Request failed';
        console.error('[schedule] fetch error', e);
        setLoading(false);
        toast('Failed to load schedule', 'error');
        if (state.data) {
          setSyncStatus('error', `Using cached data (${detail})`);
          setErrorBanner(`Live refresh failed, showing cached schedule data. ${detail}`);
        } else {
          setSyncStatus('error', detail);
          setErrorBanner(detail);
        }
        return state.data;
      } finally {
        if (requestId === activeRequestId) inflightPromise = null;
      }
    })();

    return inflightPromise;
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Master Renderer
   * ═══════════════════════════════════════════════════════════════ */

  function renderAll() {
    if (!state.data) return;
    renderStats(state.data);
    renderViewModeButtons();
    renderFilters();

    const matches = getFilteredMatches();
    const container = getScheduleContainer();
    if (!container) return;

    switch (state.viewMode) {
      case 'list':     renderListView(container, matches); break;
      case 'calendar': renderCalendarView(container, matches); break;
      default:         renderTimelineView(container, matches); break;
    }

    _reinitIcons();
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Filtered Match List
   * ═══════════════════════════════════════════════════════════════ */

  function getAllMatches() {
    if (!state.data?.rounds) return [];
    const roundsRaw = state.data.rounds;
    if (Array.isArray(roundsRaw)) {
      return roundsRaw.flatMap(r => (r.matches || []).map(m => ({ ...m, _round: r.round })));
    }
    return Object.entries(roundsRaw).flatMap(([rn, ms]) => ms.map(m => ({ ...m, _round: parseInt(rn) })));
  }

  function getFilteredMatches() {
    let matches = getAllMatches();
    const f = state.filters;

    if (f.group) matches = matches.filter(m => (m.group_name || '').toLowerCase().includes(f.group.toLowerCase()));
    if (f.round) matches = matches.filter(m => String(m.round_number) === f.round);
    if (f.state) matches = matches.filter(m => m.state === f.state);
    if (f.search) {
      const q = f.search.toLowerCase();
      matches = matches.filter(m =>
        (m.participant1_name || '').toLowerCase().includes(q) ||
        (m.participant2_name || '').toLowerCase().includes(q) ||
        String(m.match_number).includes(q)
      );
    }
    if (f.dateFrom) {
      const from = new Date(f.dateFrom);
      matches = matches.filter(m => m.scheduled_time && new Date(m.scheduled_time) >= from);
    }
    if (f.dateTo) {
      const to = new Date(f.dateTo);
      to.setHours(23, 59, 59);
      matches = matches.filter(m => m.scheduled_time && new Date(m.scheduled_time) <= to);
    }

    // Sort
    matches.sort((a, b) => {
      let cmp = 0;
      switch (state.sortKey) {
        case 'round': cmp = (a.round_number || 0) - (b.round_number || 0); break;
        case 'state': cmp = (a.state || '').localeCompare(b.state || ''); break;
        case 'match': cmp = (a.match_number || 0) - (b.match_number || 0); break;
        default: // time
          const ta = a.scheduled_time ? new Date(a.scheduled_time).getTime() : Infinity;
          const tb = b.scheduled_time ? new Date(b.scheduled_time).getTime() : Infinity;
          cmp = ta - tb;
      }
      return state.sortAsc ? cmp : -cmp;
    });

    return matches;
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Stats Rendering (6 cards)
   * ═══════════════════════════════════════════════════════════════ */

  function renderStats(data) {
    const s = data.summary || {};
    _setText('#sched-total-matches', s.total ?? '—');
    _setText('#sched-scheduled', s.scheduled ?? '—');
    _setText('#sched-live', s.live ?? '—');
    _setText('#sched-completed', s.completed ?? '—');
    _setText('#sched-conflicts', s.conflicts ?? 0);

    // Estimated end
    if (s.estimated_end) {
      try {
        const d = new Date(s.estimated_end);
        _setText('#sched-est-end', d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) +
          ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }));
      } catch { _setText('#sched-est-end', '—'); }
    } else {
      _setText('#sched-est-end', '—');
    }

    // Conflict count badge styling
    const conflictEl = $('#sched-conflicts');
    if (conflictEl) {
      if ((s.conflicts || 0) > 0) {
        conflictEl.classList.add('text-dc-danger', 'drop-shadow-[0_0_10px_rgba(255,42,85,0.6)]');
      } else {
        conflictEl.classList.remove('text-dc-danger', 'drop-shadow-[0_0_10px_rgba(255,42,85,0.6)]');
        conflictEl.classList.add('text-dc-success');
      }
    }
  }

  /* ═══════════════════════════════════════════════════════════════
   *  View Mode Toggle
   * ═══════════════════════════════════════════════════════════════ */

  function renderViewModeButtons() {
    const btnTimeline = $('#btn-view-timeline');
    const btnList = $('#btn-view-list');
    const btnCalendar = $('#btn-view-calendar');

    [btnTimeline, btnList, btnCalendar].forEach(btn => {
      if (btn) {
        btn.classList.remove('bg-theme', 'text-dc-bg', 'border-theme');
        btn.classList.add('bg-dc-panel', 'text-dc-textBright', 'border-dc-border');
      }
    });

    const active = state.viewMode === 'timeline' ? btnTimeline :
                   state.viewMode === 'list' ? btnList : btnCalendar;
    if (active) {
      active.classList.remove('bg-dc-panel', 'text-dc-textBright', 'border-dc-border');
      active.classList.add('bg-theme', 'text-dc-bg', 'border-theme');
    }
  }

  function setViewMode(mode) {
    state.viewMode = mode;
    renderAll();
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Filter Bar
   * ═══════════════════════════════════════════════════════════════ */

  function renderFilters() {
    // Populate round dropdown from data
    const roundSelect = $('#sched-filter-round');
    if (roundSelect && roundSelect.options.length <= 1) {
      const rounds = (state.data?.rounds || []).map(r => r.round).sort((a, b) => a - b);
      rounds.forEach(rn => {
        const opt = document.createElement('option');
        opt.value = rn;
        opt.textContent = `Round ${rn}`;
        roundSelect.appendChild(opt);
      });
    }

    // Populate group dropdown from data
    const groupSelect = $('#sched-filter-group');
    if (groupSelect && groupSelect.options.length <= 1) {
      const groups = new Set();
      getAllMatches().forEach(m => { if (m.group_name) groups.add(m.group_name); });
      [...groups].sort().forEach(g => {
        const opt = document.createElement('option');
        opt.value = g;
        opt.textContent = g;
        groupSelect.appendChild(opt);
      });
    }
  }

  function updateFilter(key, value) {
    state.filters[key] = value;
    renderAll();
  }

  function clearFilters() {
    state.filters = { group: '', round: '', state: '', search: '', dateFrom: '', dateTo: '' };
    ['#sched-filter-group', '#sched-filter-round', '#sched-filter-state', '#sched-search', '#sched-date-from', '#sched-date-to'].forEach(sel => {
      const el = $(sel);
      if (el) el.value = '';
    });
    renderAll();
  }

  /* ═══════════════════════════════════════════════════════════════
   *  VIEW 1: Timeline (Round-Grouped Gantt-Style)
   * ═══════════════════════════════════════════════════════════════ */

  function renderTimelineView(container, matches) {
    const rounds = {};
    matches.forEach(m => {
      const rn = m.round_number || 0;
      if (!rounds[rn]) rounds[rn] = [];
      rounds[rn].push(m);
    });
    const roundKeys = Object.keys(rounds).sort((a, b) => parseInt(a) - parseInt(b));

    if (!roundKeys.length) {
      container.innerHTML = renderEmptyState();
      _reinitIcons();
      return;
    }

    container.innerHTML = roundKeys.map(rn => {
      const roundMatches = rounds[rn];
      const scheduled = roundMatches.filter(m => m.scheduled_time).length;
      const completed = roundMatches.filter(m => m.state === 'completed' || m.state === 'forfeit').length;
      const live = roundMatches.filter(m => m.state === 'live').length;
      const pct = roundMatches.length > 0 ? Math.round((completed / roundMatches.length) * 100) : 0;

      return `
        <div class="mb-8">
          <div class="flex items-center gap-4 mb-4">
            <div class="w-10 h-10 rounded-xl bg-theme/10 border border-theme/20 flex items-center justify-center shrink-0">
              <span class="text-xs font-mono font-black text-theme">R${rn}</span>
            </div>
            <div class="flex-1">
              <div class="flex items-center gap-3">
                <h4 class="text-sm font-bold text-white uppercase tracking-widest">Round ${rn}</h4>
                <span class="text-[10px] font-mono text-dc-text">${roundMatches.length} match${roundMatches.length !== 1 ? 'es' : ''}</span>
                ${live > 0 ? '<span class="text-[9px] font-bold text-dc-success bg-dc-success/15 px-2 py-0.5 rounded-full border border-dc-success/30 animate-pulse">' + live + ' LIVE</span>' : ''}
              </div>
              <div class="flex items-center gap-2 mt-1.5">
                <div class="flex-1 h-1 bg-dc-bg rounded-full overflow-hidden max-w-[200px]">
                  <div class="h-full bg-gradient-to-r from-theme to-dc-success rounded-full transition-all duration-500" style="width:${pct}%"></div>
                </div>
                <span class="text-[9px] font-mono text-dc-text">${pct}%</span>
              </div>
            </div>
            <div class="flex items-center gap-2 text-[9px] font-mono text-dc-text">
              ${scheduled > 0 ? '<span class="bg-dc-info/10 text-dc-info px-2 py-0.5 rounded border border-dc-info/20">' + scheduled + ' scheduled</span>' : ''}
              ${completed > 0 ? '<span class="bg-dc-text/5 text-dc-text px-2 py-0.5 rounded border border-dc-border">' + completed + ' done</span>' : ''}
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3 pl-14">
            ${roundMatches.map(m => renderTimelineCard(m)).join('')}
          </div>
        </div>`;
    }).join('');
  }

  function renderTimelineCard(m) {
    const si = MATCH_STATES[m.state] || MATCH_STATES.scheduled;
    const hasConflict = state.conflictMatchIds.has(m.id);
    const time = formatTime(m.scheduled_time);
    const duration = getDuration(m);
    const p1Win = m.winner_id && m.winner_id === m.participant1_id;
    const p2Win = m.winner_id && m.winner_id === m.participant2_id;

    return `
      <div class="bg-dc-bg border ${hasConflict ? 'border-dc-danger/60 shadow-[0_0_12px_rgba(255,42,85,0.15)]' : 'border-dc-border'} rounded-xl p-4 hover:border-dc-borderLight transition-all group relative" data-match-id="${m.id}">
        ${hasConflict ? '<div class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-dc-danger flex items-center justify-center z-10" title="Scheduling conflict"><i data-lucide="alert-triangle" class="w-3 h-3 text-white"></i></div>' : ''}
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <span class="text-[10px] font-mono font-bold text-dc-text">M${m.match_number || '—'}</span>
            ${m.group_name ? '<span class="text-[8px] font-bold text-theme bg-theme/10 px-1.5 py-0.5 rounded border border-theme/20">' + _esc(m.group_name) + '</span>' : ''}
          </div>
          <span class="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${si.color}">${si.label}</span>
        </div>
        <div class="space-y-1.5 mb-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2 min-w-0 flex-1">
              <div class="w-1.5 h-1.5 rounded-full ${p1Win ? 'bg-dc-success' : 'bg-dc-border'} shrink-0"></div>
              <span class="text-xs ${p1Win ? 'text-white font-bold' : 'text-dc-textBright'} truncate">${_esc(m.participant1_name || 'TBD')}</span>
            </div>
            <span class="text-sm font-mono font-black ${p1Win ? 'text-dc-success' : 'text-dc-text'} ml-2">${m.participant1_score ?? '—'}</span>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2 min-w-0 flex-1">
              <div class="w-1.5 h-1.5 rounded-full ${p2Win ? 'bg-dc-success' : 'bg-dc-border'} shrink-0"></div>
              <span class="text-xs ${p2Win ? 'text-white font-bold' : 'text-dc-textBright'} truncate">${_esc(m.participant2_name || 'TBD')}</span>
            </div>
            <span class="text-sm font-mono font-black ${p2Win ? 'text-dc-success' : 'text-dc-text'} ml-2">${m.participant2_score ?? '—'}</span>
          </div>
        </div>
        <div class="flex items-center justify-between pt-2 border-t border-dc-border/50">
          <div class="flex items-center gap-1.5 text-[9px] text-dc-text">
            <i data-lucide="clock" class="w-3 h-3"></i>
            <span class="font-mono">${time}</span>
            ${duration ? '<span class="text-dc-text/40">· ' + duration + '</span>' : ''}
          </div>
          <div class="flex items-center gap-1">
            ${m.stream_url ? '<a href="' + _esc(m.stream_url) + '" target="_blank" class="text-dc-danger hover:text-white transition-colors" title="Watch Stream"><i data-lucide="tv" class="w-3.5 h-3.5"></i></a>' : ''}
            ${canReschedule(m) && !m.scheduled_time ? '<button onclick="TOC.schedule.openManualSchedule(' + m.id + ')" class="text-[9px] text-green-400 hover:text-green-300 transition-colors opacity-0 group-hover:opacity-100" title="Schedule Match"><i data-lucide="calendar-plus" class="w-3.5 h-3.5"></i></button>' : ''}
            ${canReschedule(m) ? '<button onclick="TOC.schedule.openReschedule(' + m.id + ', \'' + (m.scheduled_time || '') + '\')" class="text-[9px] text-dc-text hover:text-theme transition-colors opacity-0 group-hover:opacity-100" title="Reschedule"><i data-lucide="calendar-clock" class="w-3.5 h-3.5"></i></button>' : ''}
          </div>
        </div>
      </div>`;
  }

  /* ═══════════════════════════════════════════════════════════════
   *  VIEW 2: List (Dense Sortable Table)
   * ═══════════════════════════════════════════════════════════════ */

  function renderListView(container, matches) {
    if (!matches.length) {
      container.innerHTML = renderEmptyState();
      _reinitIcons();
      return;
    }

    container.innerHTML = `
      <div class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-dc-borderLight">
              ${listHeader('match', '#', 'w-16')}
              ${listHeader('round', 'Round', 'w-20')}
              <th class="text-left text-[9px] font-bold text-dc-text uppercase tracking-widest px-3 py-3">Group</th>
              <th class="text-left text-[9px] font-bold text-dc-text uppercase tracking-widest px-3 py-3 min-w-[160px]">Team 1</th>
              <th class="text-center text-[9px] font-bold text-dc-text uppercase tracking-widest px-2 py-3 w-20">Score</th>
              <th class="text-left text-[9px] font-bold text-dc-text uppercase tracking-widest px-3 py-3 min-w-[160px]">Team 2</th>
              ${listHeader('state', 'Status', 'w-24')}
              ${listHeader('time', 'Scheduled', 'w-36')}
              <th class="text-center text-[9px] font-bold text-dc-text uppercase tracking-widest px-3 py-3 w-20">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-dc-border/30">
            ${matches.map(m => renderListRow(m)).join('')}
          </tbody>
        </table>
      </div>`;
  }

  function listHeader(sortKey, label, widthClass) {
    const isActive = state.sortKey === sortKey;
    const arrow = isActive ? (state.sortAsc ? '↑' : '↓') : '';
    return '<th class="text-left text-[9px] font-bold text-dc-text uppercase tracking-widest px-3 py-3 cursor-pointer hover:text-white transition-colors ' + widthClass + '" onclick="TOC.schedule.toggleSort(\'' + sortKey + '\')">' +
      label + ' <span class="text-theme">' + arrow + '</span></th>';
  }

  function renderListRow(m) {
    const si = MATCH_STATES[m.state] || MATCH_STATES.scheduled;
    const hasConflict = state.conflictMatchIds.has(m.id);
    const time = formatTime(m.scheduled_time);
    const p1Win = m.winner_id && m.winner_id === m.participant1_id;
    const p2Win = m.winner_id && m.winner_id === m.participant2_id;

    return `
      <tr class="hover:bg-white/[0.02] transition-colors ${hasConflict ? 'bg-dc-danger/5' : ''}" data-match-id="${m.id}">
        <td class="px-3 py-3">
          <div class="flex items-center gap-1.5">
            ${hasConflict ? '<i data-lucide="alert-triangle" class="w-3 h-3 text-dc-danger shrink-0"></i>' : ''}
            <span class="font-mono font-bold text-dc-textBright">${m.match_number || '—'}</span>
          </div>
        </td>
        <td class="px-3 py-3"><span class="bg-theme/10 text-theme font-mono font-bold px-2 py-0.5 rounded text-[10px]">R${m.round_number || '—'}</span></td>
        <td class="px-3 py-3 text-dc-text text-[10px]">${_esc(m.group_name || '—')}</td>
        <td class="px-3 py-3"><span class="${p1Win ? 'text-dc-success font-bold' : 'text-dc-textBright'}">${_esc(m.participant1_name || 'TBD')}</span></td>
        <td class="px-2 py-3 text-center">
          <span class="font-mono font-black ${p1Win ? 'text-dc-success' : 'text-dc-textBright'}">${m.participant1_score ?? '—'}</span>
          <span class="text-dc-text/40 mx-0.5">:</span>
          <span class="font-mono font-black ${p2Win ? 'text-dc-success' : 'text-dc-textBright'}">${m.participant2_score ?? '—'}</span>
        </td>
        <td class="px-3 py-3"><span class="${p2Win ? 'text-dc-success font-bold' : 'text-dc-textBright'}">${_esc(m.participant2_name || 'TBD')}</span></td>
        <td class="px-3 py-3"><span class="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${si.color}">${si.label}</span></td>
        <td class="px-3 py-3 font-mono text-[10px] text-dc-text">${time}</td>
        <td class="px-3 py-3 text-center">
          <div class="flex items-center justify-center gap-1">
            ${canReschedule(m) && !m.scheduled_time ? '<button onclick="TOC.schedule.openManualSchedule(' + m.id + ')" class="p-1 text-green-400 hover:text-green-300 transition-colors rounded" title="Schedule Match"><i data-lucide="calendar-plus" class="w-3.5 h-3.5"></i></button>' : ''}
            ${canReschedule(m) ? '<button onclick="TOC.schedule.openReschedule(' + m.id + ', \'' + (m.scheduled_time || '') + '\')" class="p-1 text-dc-text hover:text-theme transition-colors rounded" title="Reschedule"><i data-lucide="calendar-clock" class="w-3.5 h-3.5"></i></button>' : ''}
            ${m.stream_url ? '<a href="' + _esc(m.stream_url) + '" target="_blank" class="p-1 text-dc-text hover:text-dc-danger transition-colors" title="Stream"><i data-lucide="tv" class="w-3.5 h-3.5"></i></a>' : ''}
            <button onclick="TOC.navigate('matches')" class="p-1 text-dc-text hover:text-white transition-colors rounded" title="View Match Detail"><i data-lucide="external-link" class="w-3.5 h-3.5"></i></button>
          </div>
        </td>
      </tr>`;
  }

  function toggleSort(key) {
    if (state.sortKey === key) {
      state.sortAsc = !state.sortAsc;
    } else {
      state.sortKey = key;
      state.sortAsc = true;
    }
    renderAll();
  }

  /* ═══════════════════════════════════════════════════════════════
   *  VIEW 3: Calendar (Day-Based Grid)
   * ═══════════════════════════════════════════════════════════════ */

  function renderCalendarView(container, matches) {
    const days = {};
    const unscheduled = [];

    matches.forEach(m => {
      if (!m.scheduled_time) { unscheduled.push(m); return; }
      const d = new Date(m.scheduled_time);
      const dayKey = d.toISOString().split('T')[0];
      if (!days[dayKey]) days[dayKey] = [];
      days[dayKey].push(m);
    });

    const dayKeys = Object.keys(days).sort();

    if (!dayKeys.length && !unscheduled.length) {
      container.innerHTML = renderEmptyState();
      _reinitIcons();
      return;
    }

    const todayStr = new Date().toISOString().split('T')[0];

    container.innerHTML =
      dayKeys.map(dk => {
        const dayMatches = days[dk];
        const d = new Date(dk + 'T00:00:00');
        const dayLabel = d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
        const isToday = dk === todayStr;

        // Group by time slot (hour)
        const hourSlots = {};
        dayMatches.forEach(m => {
          const h = new Date(m.scheduled_time).getHours();
          const slotKey = String(h).padStart(2, '0') + ':00';
          if (!hourSlots[slotKey]) hourSlots[slotKey] = [];
          hourSlots[slotKey].push(m);
        });

        return `
          <div class="mb-8">
            <div class="flex items-center gap-3 mb-4 sticky top-0 z-10 bg-dc-surface/80 backdrop-blur-md py-2">
              <div class="w-10 h-10 rounded-xl ${isToday ? 'bg-theme' : 'bg-dc-panel'} border ${isToday ? 'border-theme' : 'border-dc-border'} flex items-center justify-center shrink-0">
                <span class="text-sm font-mono font-black ${isToday ? 'text-dc-bg' : 'text-dc-text'}">${d.getDate()}</span>
              </div>
              <div>
                <h4 class="text-sm font-bold text-white">${dayLabel}</h4>
                <span class="text-[10px] font-mono text-dc-text">${dayMatches.length} match${dayMatches.length !== 1 ? 'es' : ''}</span>
                ${isToday ? '<span class="text-[8px] font-bold text-theme bg-theme/10 px-2 py-0.5 rounded-full border border-theme/20 ml-2">TODAY</span>' : ''}
              </div>
            </div>
            <div class="space-y-4 pl-14">
              ${Object.entries(hourSlots).sort(([a], [b]) => a.localeCompare(b)).map(([slot, slotMatches]) => `
                <div>
                  <div class="flex items-center gap-2 mb-2">
                    <span class="text-[10px] font-mono font-bold text-dc-info bg-dc-info/10 px-2 py-0.5 rounded border border-dc-info/20">${slot}</span>
                    <div class="flex-1 h-px bg-dc-border"></div>
                    <span class="text-[9px] font-mono text-dc-text">${slotMatches.length} match${slotMatches.length !== 1 ? 'es' : ''}</span>
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
                    ${slotMatches.map(m => renderCalendarCard(m)).join('')}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>`;
      }).join('') +

      (unscheduled.length ? `
        <div class="mb-8">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 rounded-xl bg-dc-danger/10 border border-dc-danger/20 flex items-center justify-center">
              <i data-lucide="calendar-x" class="w-5 h-5 text-dc-danger"></i>
            </div>
            <div>
              <h4 class="text-sm font-bold text-dc-danger">Unscheduled</h4>
              <span class="text-[10px] font-mono text-dc-text">${unscheduled.length} match${unscheduled.length !== 1 ? 'es' : ''} without times</span>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2 pl-14">
            ${unscheduled.map(m => renderCalendarCard(m)).join('')}
          </div>
        </div>
      ` : '');
  }

  function renderCalendarCard(m) {
    const si = MATCH_STATES[m.state] || MATCH_STATES.scheduled;
    const hasConflict = state.conflictMatchIds.has(m.id);
    const timeOnly = m.scheduled_time ? new Date(m.scheduled_time).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : 'No time';

    return `
      <div class="bg-dc-bg border ${hasConflict ? 'border-dc-danger/60' : 'border-dc-border'} rounded-lg p-3 hover:border-dc-borderLight transition-all group relative">
        ${hasConflict ? '<div class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-dc-danger flex items-center justify-center"><i data-lucide="alert-triangle" class="w-2.5 h-2.5 text-white"></i></div>' : ''}
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-1.5">
            <span class="text-[9px] font-mono font-bold text-dc-text">M${m.match_number || '—'}</span>
            <span class="text-[8px] font-mono text-dc-text/50">R${m.round_number || '—'}</span>
          </div>
          <span class="text-[7px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full border ${si.color}">${si.label}</span>
        </div>
        <div class="flex items-center justify-between text-[10px] mb-1">
          <span class="text-dc-textBright truncate max-w-[100px]">${_esc(m.participant1_name || 'TBD')}</span>
          <span class="font-mono font-bold text-dc-text">${m.participant1_score ?? '—'} : ${m.participant2_score ?? '—'}</span>
          <span class="text-dc-textBright truncate max-w-[100px] text-right">${_esc(m.participant2_name || 'TBD')}</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-[9px] font-mono text-dc-text">${timeOnly}</span>
          ${canReschedule(m) && !m.scheduled_time ? '<button onclick="TOC.schedule.openManualSchedule(' + m.id + ')" class="text-[9px] text-green-400 hover:text-green-300 transition-colors opacity-0 group-hover:opacity-100" title="Schedule"><i data-lucide="calendar-plus" class="w-3 h-3"></i></button>' : ''}
          ${canReschedule(m) ? '<button onclick="TOC.schedule.openReschedule(' + m.id + ', \'' + (m.scheduled_time || '') + '\')" class="text-[9px] text-dc-text hover:text-theme transition-colors opacity-0 group-hover:opacity-100"><i data-lucide="edit-3" class="w-3 h-3"></i></button>' : ''}
        </div>
      </div>`;
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Empty State
   * ═══════════════════════════════════════════════════════════════ */

  function renderEmptyState() {
    const total = state.data?.summary?.total || 0;
    const hasMatches = total > 0;
    const hasBracket = state.data?.context?.has_bracket || false;
    const hasGroups  = state.data?.context?.has_groups  || false;
    const ready      = hasBracket || hasGroups; // structure exists

    if (!hasMatches) {
      if (ready) {
        // Bracket/groups exist but matches not yet generated
        const what = hasGroups ? 'groups have been seeded' : 'bracket has been generated';
        const action = hasGroups ? 'Use the <strong class="text-theme">Generate Matches</strong> action in the Groups sub-tab to create round-robin fixtures.' : 'Bracket nodes exist but match records have not been created yet. Try resetting and regenerating the bracket.';
        return `
        <div class="flex flex-col items-center justify-center py-16 text-center max-w-lg mx-auto">
          <div class="w-16 h-16 rounded-2xl bg-dc-panel border border-dc-border flex items-center justify-center mb-6">
            <i data-lucide="calendar-clock" class="w-8 h-8 text-dc-warning/50"></i>
          </div>
          <h3 class="text-lg font-display font-black text-white mb-2">Structure Ready — No Matches Yet</h3>
          <p class="text-sm text-dc-text mb-6">Your ${what}. ${action}</p>
          <div class="flex gap-3">
            <button onclick="TOC.navigate('brackets')" class="px-5 py-2.5 bg-theme text-dc-bg text-[10px] font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2">
              <i data-lucide="git-branch" class="w-4 h-4"></i> Go to Brackets
            </button>
            <button onclick="TOC.schedule.openUserGuide()" class="px-5 py-2.5 bg-dc-panel border border-dc-border text-dc-textBright text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-white/5 transition-colors flex items-center gap-2">
              <i data-lucide="book-open" class="w-4 h-4"></i> Guide
            </button>
          </div>
        </div>`;
      }

      // No matches and no bracket/groups — need to start from scratch
      return `
        <div class="flex flex-col items-center justify-center py-16 text-center max-w-lg mx-auto">
          <div class="w-16 h-16 rounded-2xl bg-dc-panel border border-dc-border flex items-center justify-center mb-6">
            <i data-lucide="calendar-x" class="w-8 h-8 text-dc-text/20"></i>
          </div>
          <h3 class="text-lg font-display font-black text-white mb-2">No Matches Yet</h3>
          <p class="text-sm text-dc-text mb-8">Matches are created when you generate brackets. Follow these steps:</p>

          <div class="w-full space-y-3 text-left mb-8">
            <div class="bg-dc-panel border border-dc-borderLight rounded-xl p-4 flex items-start gap-3">
              <span class="w-7 h-7 rounded-lg bg-theme/20 flex items-center justify-center text-xs font-black text-theme shrink-0">1</span>
              <div>
                <p class="text-xs font-bold text-white">Generate Brackets</p>
                <p class="text-[10px] text-dc-text mt-0.5">Go to the <strong class="text-theme">Brackets</strong> tab and generate groups/brackets from your registrations.</p>
              </div>
            </div>
            <div class="flex justify-center"><i data-lucide="chevron-down" class="w-4 h-4 text-dc-text/30"></i></div>
            <div class="bg-dc-panel border border-dc-borderLight rounded-xl p-4 flex items-start gap-3">
              <span class="w-7 h-7 rounded-lg bg-theme/20 flex items-center justify-center text-xs font-black text-theme shrink-0">2</span>
              <div>
                <p class="text-xs font-bold text-white">Auto-Schedule or Manual</p>
                <p class="text-[10px] text-dc-text mt-0.5">Come back here and use <strong class="text-theme">Auto-Schedule</strong> for automatic time assignment, or schedule each match manually.</p>
              </div>
            </div>
            <div class="flex justify-center"><i data-lucide="chevron-down" class="w-4 h-4 text-dc-text/30"></i></div>
            <div class="bg-dc-panel border border-dc-borderLight rounded-xl p-4 flex items-start gap-3">
              <span class="w-7 h-7 rounded-lg bg-theme/20 flex items-center justify-center text-xs font-black text-theme shrink-0">3</span>
              <div>
                <p class="text-xs font-bold text-white">Fine-Tune & Manage</p>
                <p class="text-[10px] text-dc-text mt-0.5">Use Bulk Shift, Add Break, and individual reschedule to perfect your tournament schedule.</p>
              </div>
            </div>
          </div>

          <div class="flex gap-3">
            <button onclick="TOC.navigate('brackets')" class="px-5 py-2.5 bg-theme text-dc-bg text-[10px] font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2">
              <i data-lucide="git-branch" class="w-4 h-4"></i> Go to Brackets
            </button>
            <button onclick="TOC.schedule.openUserGuide()" class="px-5 py-2.5 bg-dc-panel border border-dc-border text-dc-textBright text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-white/5 transition-colors flex items-center gap-2">
              <i data-lucide="book-open" class="w-4 h-4"></i> Guide
            </button>
          </div>
        </div>`;
    }

    // Has matches but none match current filters
    return `
      <div class="flex flex-col items-center justify-center py-16 text-center">
        <div class="w-16 h-16 rounded-2xl bg-dc-panel border border-dc-border flex items-center justify-center mb-4">
          <i data-lucide="search-x" class="w-8 h-8 text-dc-text/20"></i>
        </div>
        <h3 class="text-lg font-bold text-white mb-2">No Matches Found</h3>
        <p class="text-sm text-dc-text mb-6">${total} match${total !== 1 ? 'es' : ''} exist but none match your current filters.</p>
        <div class="flex gap-3">
          <button onclick="TOC.schedule.clearFilters()" class="px-4 py-2 bg-dc-panel border border-dc-border text-dc-textBright text-[10px] font-bold uppercase tracking-widest rounded-lg hover:bg-white/5 transition-colors flex items-center gap-1.5">
            <i data-lucide="filter-x" class="w-3.5 h-3.5"></i> Clear Filters
          </button>
          <button onclick="TOC.schedule.openAutoSchedule()" class="px-4 py-2 bg-theme text-dc-bg text-[10px] font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity flex items-center gap-1.5">
            <i data-lucide="sparkles" class="w-3.5 h-3.5"></i> Auto-Schedule
          </button>
        </div>
      </div>`;
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Inline Reschedule
   * ═══════════════════════════════════════════════════════════════ */

  function canReschedule(m) {
    return m.state !== 'completed' && m.state !== 'forfeit' && m.state !== 'cancelled';
  }

  function openReschedule(matchId, currentTime) {
    let defaultVal = '';
    if (currentTime) {
      try {
        const d = new Date(currentTime);
        defaultVal = d.getFullYear() + '-' +
          String(d.getMonth() + 1).padStart(2, '0') + '-' +
          String(d.getDate()).padStart(2, '0') + 'T' +
          String(d.getHours()).padStart(2, '0') + ':' +
          String(d.getMinutes()).padStart(2, '0');
      } catch { /* ignore */ }
    }

    const html = `
      <div class="p-6 space-y-4">
        <div class="flex items-center gap-3 mb-1">
          <div class="w-8 h-8 rounded-lg bg-theme/10 flex items-center justify-center">
            <i data-lucide="calendar-clock" class="w-4 h-4 text-theme"></i>
          </div>
          <h3 class="font-display font-black text-lg text-white">Reschedule Match</h3>
        </div>
        <p class="text-[10px] text-dc-text">Change the scheduled time for this match.</p>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">New Date & Time</label>
          <input id="rs-time" type="datetime-local" value="${defaultVal}" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-xs focus:border-theme outline-none">
        </div>
        <div class="flex gap-3">
          <button onclick="TOC.schedule.closeOverlay('reschedule-overlay')" class="flex-1 py-2.5 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-bold uppercase tracking-widest rounded-lg hover:bg-white/5 transition-colors">Cancel</button>
          <button onclick="TOC.schedule.confirmReschedule(${matchId})" class="flex-1 py-2.5 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Reschedule</button>
        </div>
      </div>`;
    showOverlay('reschedule-overlay', html);
  }

  async function confirmReschedule(matchId) {
    const val = $('#rs-time')?.value;
    if (!val) { toast('Please select a date and time', 'error'); return; }

    try {
      await API.post('schedule/' + matchId + '/reschedule/', {
        scheduled_time: new Date(val).toISOString(),
      });
      toast('Match rescheduled', 'success');
      closeOverlay('reschedule-overlay');
      refresh();
    } catch (e) {
      toast(e.message || 'Reschedule failed', 'error');
    }
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Manual Schedule (Per-Match)
   * ═══════════════════════════════════════════════════════════════ */

  function openManualSchedule(matchId) {
    const allMatches = getAllMatches();
    const match = allMatches.find(m => m.id === matchId);
    const label = match ? 'M' + (match.match_number || '?') + ' — ' + _esc(match.participant1_name || 'TBD') + ' vs ' + _esc(match.participant2_name || 'TBD') : 'Match #' + matchId;

    // Default: tomorrow 10:00 AM or next full hour
    const now = new Date();
    now.setMinutes(0, 0, 0);
    now.setHours(now.getHours() + 1);
    const defaultVal = now.getFullYear() + '-' +
      String(now.getMonth() + 1).padStart(2, '0') + '-' +
      String(now.getDate()).padStart(2, '0') + 'T' +
      String(now.getHours()).padStart(2, '0') + ':' +
      String(now.getMinutes()).padStart(2, '0');

    const html = `
      <div class="p-6 space-y-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-green-600/10 border border-green-600/20 flex items-center justify-center">
            <i data-lucide="calendar-plus" class="w-5 h-5 text-green-400"></i>
          </div>
          <div>
            <h3 class="font-display font-black text-lg text-white">Schedule Match</h3>
            <p class="text-[10px] text-dc-text font-mono">Manually set time for a specific match</p>
          </div>
        </div>
        <div class="bg-dc-panel border border-dc-borderLight rounded-lg p-3">
          <p class="text-[10px] text-white font-bold">${label}</p>
          ${match?.group_name ? '<p class="text-[9px] text-dc-text mt-0.5">Group: ' + _esc(match.group_name) + ' · Round ' + (match.round_number || '?') + '</p>' : ''}
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Date & Time</label>
          <input id="ms-time" type="datetime-local" value="${defaultVal}" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-xs focus:border-theme outline-none">
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Check-in Window (minutes before match)</label>
          <div class="relative">
            <input id="ms-checkin" type="number" value="15" min="0" max="120" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 pr-12 text-white text-xs focus:border-theme outline-none">
            <span class="absolute right-3 top-1/2 -translate-y-1/2 text-[9px] text-dc-text">min</span>
          </div>
          <p class="text-[9px] text-dc-text/60 mt-1">Set to 0 to skip check-in deadline</p>
        </div>
        <div class="flex gap-3">
          <button onclick="TOC.schedule.closeOverlay('manual-schedule-overlay')" class="flex-1 py-2.5 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-bold uppercase tracking-widest rounded-lg hover:bg-white/5 transition-colors">Cancel</button>
          <button onclick="TOC.schedule.confirmManualSchedule(${matchId})" class="flex-1 py-2.5 bg-green-600 text-white text-xs font-black uppercase tracking-widest rounded-lg hover:bg-green-500 transition-colors flex items-center justify-center gap-2">
            <i data-lucide="calendar-check" class="w-4 h-4"></i> Schedule
          </button>
        </div>
      </div>`;

    showOverlay('manual-schedule-overlay', html);
  }

  async function confirmManualSchedule(matchId) {
    const val = $('#ms-time')?.value;
    if (!val) { toast('Please select a date and time', 'error'); return; }

    const payload = {
      scheduled_time: new Date(val).toISOString(),
    };
    const checkin = parseInt($('#ms-checkin')?.value);
    if (checkin > 0) payload.check_in_minutes = checkin;

    try {
      await API.post('schedule/' + matchId + '/manual/', payload);
      toast('Match scheduled successfully', 'success');
      closeOverlay('manual-schedule-overlay');
      refresh();
    } catch (e) {
      toast(e.message || 'Scheduling failed', 'error');
    }
  }

  /* ═══════════════════════════════════════════════════════════════
   *  ICS Calendar Export
   * ═══════════════════════════════════════════════════════════════ */

  function exportICS() {
    // Trigger browser download via anchor click
    const url = API.url('schedule/export.ics');
    const a = document.createElement('a');
    a.href = url;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast('Downloading schedule as .ics calendar file…', 'success');
  }

  /* ═══════════════════════════════════════════════════════════════
   *  User Guide / Help Panel
   * ═══════════════════════════════════════════════════════════════ */

  function openUserGuide() {
    const html = `
      <div class="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-theme/10 border border-theme/20 flex items-center justify-center">
            <i data-lucide="book-open" class="w-5 h-5 text-theme"></i>
          </div>
          <div>
            <h3 class="font-display font-black text-lg text-white">Schedule Manager Guide</h3>
            <p class="text-[10px] text-dc-text font-mono">Everything you need to manage match times</p>
          </div>
        </div>

        <div class="space-y-4">
          <div class="bg-dc-panel border border-dc-borderLight rounded-xl p-4">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-6 h-6 rounded-lg bg-theme/20 flex items-center justify-center text-[10px] font-black text-theme">1</span>
              <h4 class="text-sm font-bold text-white">Generate Brackets First</h4>
            </div>
            <p class="text-[10px] text-dc-text leading-relaxed">Before scheduling, go to the <strong class="text-white">Brackets</strong> tab and generate your groups/brackets. This creates the matches that need scheduling.</p>
          </div>

          <div class="bg-dc-panel border border-dc-borderLight rounded-xl p-4">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-6 h-6 rounded-lg bg-theme/20 flex items-center justify-center text-[10px] font-black text-theme">2</span>
              <h4 class="text-sm font-bold text-white">Auto-Schedule (Recommended)</h4>
            </div>
            <p class="text-[10px] text-dc-text leading-relaxed">Click <strong class="text-theme">Auto-Schedule</strong> to automatically assign time slots. Configure match duration (default: 60min), break time between matches (15min), and round breaks (30min). The wizard shows a live preview of estimated duration.</p>
          </div>

          <div class="bg-dc-panel border border-dc-borderLight rounded-xl p-4">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-6 h-6 rounded-lg bg-theme/20 flex items-center justify-center text-[10px] font-black text-theme">3</span>
              <h4 class="text-sm font-bold text-white">Manual Scheduling</h4>
            </div>
            <p class="text-[10px] text-dc-text leading-relaxed">Click the <i data-lucide="calendar-plus" class="w-3 h-3 inline text-green-400"></i> icon on any match card to set a specific time. You can also set a check-in window so players get notified before the match.</p>
          </div>

          <div class="bg-dc-panel border border-dc-borderLight rounded-xl p-4">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-6 h-6 rounded-lg bg-theme/20 flex items-center justify-center text-[10px] font-black text-theme">4</span>
              <h4 class="text-sm font-bold text-white">Fine-Tune</h4>
            </div>
            <p class="text-[10px] text-dc-text leading-relaxed">Use <strong class="text-dc-warning">Bulk Shift</strong> to move all matches forward or backward. Use <strong class="text-purple-400">Add Break</strong> to insert pauses between rounds (e.g., lunch breaks). Reschedule individual matches by clicking the clock icon.</p>
          </div>

          <div class="bg-dc-panel border border-dc-borderLight rounded-xl p-4">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-6 h-6 rounded-lg bg-theme/20 flex items-center justify-center text-[10px] font-black text-theme">5</span>
              <h4 class="text-sm font-bold text-white">Views & Filters</h4>
            </div>
            <p class="text-[10px] text-dc-text leading-relaxed">Switch between <strong class="text-white">Timeline</strong> (round-based), <strong class="text-white">List</strong> (table with sorting), and <strong class="text-white">Calendar</strong> (day grid) views. Use filters to narrow by group, round, state, or date range. <span class="text-dc-info">Keyboard: Ctrl+1/2/3</span> for views, <span class="text-dc-info">R</span> to refresh.</p>
          </div>

          <div class="bg-dc-info/5 border border-dc-info/20 rounded-lg p-3">
            <p class="text-[9px] text-dc-info font-bold uppercase tracking-widest mb-1"><i data-lucide="lightbulb" class="w-3 h-3 inline mr-1"></i> Pro Tips</p>
            <ul class="text-[10px] text-dc-text space-y-1 ml-4 list-disc">
              <li>Red-bordered matches indicate <strong class="text-dc-danger">scheduling conflicts</strong> (overlapping times)</li>
              <li>Use "Reschedule existing" in Auto-Schedule to completely rebuild the schedule</li>
              <li>Set concurrent matches > 1 if you have multiple game stations/servers</li>
              <li>Check-in deadlines auto-notify players before their match time</li>
            </ul>
          </div>
        </div>

        <button onclick="TOC.schedule.closeOverlay('user-guide-overlay')" class="w-full py-2.5 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-bold uppercase tracking-widest rounded-lg hover:bg-white/5 transition-colors">Got it</button>
      </div>`;

    showOverlay('user-guide-overlay', html);
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Auto-Schedule (Enhanced with Smart Defaults)
   * ═══════════════════════════════════════════════════════════════ */

  function openAutoSchedule() {
    const total = state.data?.summary?.total || 0;
    const scheduled = state.data?.summary?.scheduled || 0;
    const completed = state.data?.summary?.completed || 0;
    const pendingCount = total - completed;
    const defaultConcurrent = total > 16 ? 2 : 1;

    // Default start: tomorrow at 10:00 AM
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const defaultStart = tomorrow.getFullYear() + '-' +
      String(tomorrow.getMonth() + 1).padStart(2, '0') + '-' +
      String(tomorrow.getDate()).padStart(2, '0') + 'T10:00';

    const rounds = (state.data?.rounds || []).map(r => r.round).sort((a, b) => a - b);
    const roundOptions = rounds.map(rn => '<option value="' + rn + '">Round ' + rn + ' only</option>').join('');

    const html = `
      <div class="p-6 space-y-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-theme/10 border border-theme/20 flex items-center justify-center">
            <i data-lucide="sparkles" class="w-5 h-5 text-theme"></i>
          </div>
          <div>
            <h3 class="font-display font-black text-lg text-white">Auto-Schedule Wizard</h3>
            <p class="text-[10px] text-dc-text font-mono">Intelligent match time assignment</p>
          </div>
        </div>

        <div class="bg-dc-info/5 border border-dc-info/20 rounded-lg p-3">
          <p class="text-[9px] text-dc-info font-bold uppercase tracking-widest mb-1"><i data-lucide="info" class="w-3 h-3 inline mr-1"></i> How Auto-Schedule Works</p>
          <ul class="text-[10px] text-dc-text space-y-0.5 ml-4 list-disc">
            <li>Matches are assigned time slots starting from your chosen start time</li>
            <li>Concurrent matches run in parallel (e.g., 2 matches at 10:00, 2 more at 11:00)</li>
            <li><strong class="text-white">Round breaks</strong> are automatically inserted between rounds</li>
            <li>Only unscheduled matches are affected (unless "Reschedule existing" is checked)</li>
          </ul>
        </div>

        ${total === 0 ? '<div class="bg-dc-danger/5 border border-dc-danger/20 rounded-lg p-3"><p class="text-[10px] text-dc-danger"><i data-lucide="alert-triangle" class="w-3 h-3 inline mr-1"></i> No matches exist yet. Generate a bracket first from the <strong>Brackets</strong> tab.</p></div>' : ''}

        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Start Date & Time</label>
          <input id="as-start" type="datetime-local" value="${defaultStart}" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-xs focus:border-theme outline-none">
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Match Duration</label>
            <div class="relative">
              <input id="as-duration" type="number" value="60" min="5" max="480" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 pr-12 text-white text-xs focus:border-theme outline-none">
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-[9px] text-dc-text">min</span>
            </div>
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Break Between</label>
            <div class="relative">
              <input id="as-break" type="number" value="15" min="0" max="120" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 pr-12 text-white text-xs focus:border-theme outline-none">
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-[9px] text-dc-text">min</span>
            </div>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Concurrent Matches</label>
            <input id="as-concurrent" type="number" value="${defaultConcurrent}" min="1" max="32" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-xs focus:border-theme outline-none">
            <p class="text-[9px] text-dc-text/60 mt-1">How many matches run at the same time</p>
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Round Break</label>
            <div class="relative">
              <input id="as-round-break" type="number" value="30" min="0" max="480" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 pr-12 text-white text-xs focus:border-theme outline-none">
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-[9px] text-dc-text">min</span>
            </div>
            <p class="text-[9px] text-dc-text/60 mt-1">Extra pause between rounds</p>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Round Filter</label>
            <select id="as-round" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-xs focus:border-theme outline-none">
              <option value="">All Rounds</option>
              ${roundOptions}
            </select>
          </div>
          <div class="flex items-end pb-1">
            <label class="flex items-center gap-2 cursor-pointer">
              <input id="as-reschedule-existing" type="checkbox" class="w-4 h-4 rounded bg-dc-bg border-dc-border accent-theme">
              <span class="text-[10px] text-dc-textBright">Reschedule existing</span>
            </label>
          </div>
        </div>
        <div class="bg-dc-panel border border-dc-borderLight rounded-xl p-4">
          <div class="flex items-center gap-3 mb-2">
            <div class="flex items-center gap-2">
              <i data-lucide="bar-chart-3" class="w-4 h-4 text-theme"></i>
              <span class="text-[9px] font-bold text-dc-text uppercase tracking-widest">Preview</span>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-3 text-center">
            <div>
              <p class="text-xs font-mono text-dc-text">Matches</p>
              <p id="as-est-matches" class="text-lg font-display font-black text-white">${pendingCount}</p>
            </div>
            <div>
              <p class="text-xs font-mono text-dc-text">Duration</p>
              <p id="as-est-duration" class="text-lg font-display font-black text-theme">—</p>
            </div>
            <div>
              <p class="text-xs font-mono text-dc-text">Ends</p>
              <p id="as-est-end" class="text-sm font-mono text-dc-textBright">—</p>
            </div>
          </div>
        </div>
        <button onclick="TOC.schedule.confirmAutoSchedule()" ${total === 0 ? 'disabled' : ''} class="w-full py-3 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed">
          <i data-lucide="sparkles" class="w-4 h-4"></i> Generate Schedule
        </button>
      </div>`;

    showOverlay('auto-schedule-overlay', html);

    // Live estimate calculator
    const updateEstimate = () => {
      const dur = parseInt($('#as-duration')?.value) || 60;
      const brk = parseInt($('#as-break')?.value) || 15;
      const conc = parseInt($('#as-concurrent')?.value) || 1;
      const roundBreak = parseInt($('#as-round-break')?.value) || 30;
      const roundVal = $('#as-round')?.value;
      const rescheduleExisting = $('#as-reschedule-existing')?.checked;
      let matchCount = 0;
      let roundCount = 0;
      if (roundVal) {
        const round = (state.data?.rounds || []).find(r => String(r.round) === roundVal);
        const ms = round ? (round.matches || []) : [];
        matchCount = rescheduleExisting ? ms.length : ms.filter(m => m.state === 'scheduled').length;
        roundCount = 1;
      } else {
        const ms = getAllMatches();
        matchCount = rescheduleExisting ? ms.filter(m => m.state !== 'completed' && m.state !== 'forfeit' && m.state !== 'cancelled').length : ms.filter(m => m.state === 'scheduled').length;
        roundCount = (state.data?.rounds || []).length;
      }
      const slots = Math.ceil(matchCount / conc);
      const totalMin = Math.max(0, slots * (dur + brk) - brk + (roundCount > 1 ? (roundCount - 1) * roundBreak : 0));
      const hours = Math.floor(totalMin / 60);
      const mins = totalMin % 60;
      _setText('#as-est-duration', hours + 'h ' + mins + 'm');
      _setText('#as-est-matches', String(matchCount));
      // Compute end time
      const startVal = $('#as-start')?.value;
      if (startVal && totalMin > 0) {
        const end = new Date(startVal);
        end.setMinutes(end.getMinutes() + totalMin);
        _setText('#as-est-end', end.toLocaleDateString(undefined, {month:'short',day:'numeric'}) + ' ' + end.toLocaleTimeString(undefined, {hour:'2-digit',minute:'2-digit'}));
      } else {
        _setText('#as-est-end', '—');
      }
    };

    setTimeout(() => {
      ['as-duration', 'as-break', 'as-concurrent', 'as-round', 'as-round-break', 'as-start', 'as-reschedule-existing'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updateEstimate);
        if (el) el.addEventListener('change', updateEstimate);
      });
      updateEstimate();
    }, 100);
  }

  async function confirmAutoSchedule() {
    const startVal = $('#as-start')?.value;
    if (!startVal) { toast('Start time required', 'error'); return; }

    const payload = {
      start_time: new Date(startVal).toISOString(),
      match_duration_minutes: parseInt($('#as-duration')?.value) || 60,
      break_minutes: parseInt($('#as-break')?.value) || 15,
      max_concurrent: parseInt($('#as-concurrent')?.value) || 1,
      round_break_minutes: parseInt($('#as-round-break')?.value) || 30,
      reschedule_existing: !!$('#as-reschedule-existing')?.checked,
    };

    const roundVal = $('#as-round')?.value;
    if (roundVal) payload.round_number = parseInt(roundVal);

    try {
      const result = await API.post('schedule/auto-generate/', payload);
      const msg = result.message || ((result.scheduled || 0) + ' matches scheduled');
      toast(msg, 'success');
      closeOverlay('auto-schedule-overlay');
      refresh();
    } catch (e) {
      toast(e.message || 'Scheduling failed', 'error');
    }
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Bulk Shift (Enhanced)
   * ═══════════════════════════════════════════════════════════════ */

  function openBulkShift() {
    const rounds = (state.data?.rounds || []).map(r => r.round).sort((a, b) => a - b);
    const roundOptions = rounds.map(rn => '<option value="' + rn + '">Round ' + rn + '</option>').join('');

    const html = `
      <div class="p-6 space-y-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-dc-warning/10 border border-dc-warning/20 flex items-center justify-center">
            <i data-lucide="clock" class="w-5 h-5 text-dc-warning"></i>
          </div>
          <div>
            <h3 class="font-display font-black text-lg text-white">Bulk Shift Schedule</h3>
            <p class="text-[10px] text-dc-text font-mono">Move matches forward or backward in time</p>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Minutes to Shift</label>
            <input id="bs-minutes" type="number" value="30" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-xs focus:border-theme outline-none" placeholder="e.g. 30 or -30">
            <p class="text-[9px] text-dc-text/60 mt-1">Positive = forward, negative = backward</p>
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Apply To</label>
            <select id="bs-round" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-xs focus:border-theme outline-none">
              <option value="">All Rounds</option>
              ${roundOptions}
            </select>
          </div>
        </div>
        <div class="flex gap-3">
          <button onclick="TOC.schedule.closeOverlay('bulk-shift-overlay')" class="flex-1 py-2.5 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-bold uppercase tracking-widest rounded-lg hover:bg-white/5 transition-colors">Cancel</button>
          <button onclick="TOC.schedule.confirmBulkShift()" class="flex-1 py-2.5 bg-dc-warning text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2">
            <i data-lucide="clock" class="w-4 h-4"></i> Apply Shift
          </button>
        </div>
      </div>`;

    showOverlay('bulk-shift-overlay', html);
  }

  async function confirmBulkShift() {
    const minutes = parseInt($('#bs-minutes')?.value);
    if (!minutes) { toast('Minutes required', 'error'); return; }
    const payload = { shift_minutes: minutes };
    const roundVal = $('#bs-round')?.value;
    if (roundVal) payload.round_number = parseInt(roundVal);

    try {
      const result = await API.post('schedule/bulk-shift/', payload);
      toast((result.shifted || 0) + ' matches shifted ' + (minutes > 0 ? '+' : '') + minutes + 'min', 'success');
      closeOverlay('bulk-shift-overlay');
      refresh();
    } catch (e) {
      toast(e.message || 'Shift failed', 'error');
    }
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Add Break (Enhanced)
   * ═══════════════════════════════════════════════════════════════ */

  function openAddBreak() {
    const rounds = (state.data?.rounds || []).map(r => r.round).sort((a, b) => a - b);
    const roundOptions = rounds.map(rn => '<option value="' + rn + '" ' + (rn === 1 ? 'selected' : '') + '>After Round ' + rn + '</option>').join('');

    const html = `
      <div class="p-6 space-y-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-purple-600/10 border border-purple-600/20 flex items-center justify-center">
            <i data-lucide="coffee" class="w-5 h-5 text-purple-400"></i>
          </div>
          <div>
            <h3 class="font-display font-black text-lg text-white">Insert Break</h3>
            <p class="text-[10px] text-dc-text font-mono">Add a break between rounds</p>
          </div>
        </div>
        <p class="text-[10px] text-dc-text/80">All matches after the selected round will be shifted forward by the break duration.</p>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Insert Break</label>
            <select id="ab-round" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-xs focus:border-theme outline-none">
              ${roundOptions}
            </select>
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Duration (min)</label>
            <input id="ab-minutes" type="number" value="30" min="5" max="480" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-xs focus:border-theme outline-none">
          </div>
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Label</label>
          <input id="ab-label" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-xs focus:border-theme outline-none" value="Break" placeholder="e.g. Lunch Break, Halftime">
        </div>
        <div class="flex gap-3">
          <button onclick="TOC.schedule.closeOverlay('add-break-overlay')" class="flex-1 py-2.5 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-bold uppercase tracking-widest rounded-lg hover:bg-white/5 transition-colors">Cancel</button>
          <button onclick="TOC.schedule.confirmAddBreak()" class="flex-1 py-2.5 bg-purple-600 text-white text-xs font-black uppercase tracking-widest rounded-lg hover:bg-purple-500 transition-colors flex items-center justify-center gap-2">
            <i data-lucide="coffee" class="w-4 h-4"></i> Insert Break
          </button>
        </div>
      </div>`;

    showOverlay('add-break-overlay', html);
  }

  async function confirmAddBreak() {
    try {
      const result = await API.post('schedule/add-break/', {
        after_round: parseInt($('#ab-round')?.value) || 1,
        break_minutes: parseInt($('#ab-minutes')?.value) || 30,
        label: $('#ab-label')?.value?.trim() || 'Break',
      });
      toast('Break inserted — ' + (result.matches_shifted || 0) + ' matches shifted', 'success');
      closeOverlay('add-break-overlay');
      refresh();
    } catch (e) {
      toast(e.message || 'Failed to insert break', 'error');
    }
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Overlay / Modal Helpers
   * ═══════════════════════════════════════════════════════════════ */

  function showOverlay(id, innerHtml) {
    const existing = document.getElementById(id);
    if (existing) existing.remove();
    const modal = document.createElement('div');
    modal.id = id;
    modal.className = 'fixed inset-0 z-[110] flex items-start sm:items-center justify-center p-3 sm:p-5';
    modal.innerHTML = `
      <div class="absolute inset-0 bg-black/80 backdrop-blur-md" onclick="TOC.schedule.closeOverlay('${id}')"></div>
      <div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-3xl max-h-[90vh] relative z-10 overflow-hidden flex flex-col">
        <div class="h-1 w-full bg-theme"></div>
        <div class="min-h-0 overflow-y-auto">${innerHtml}</div>
      </div>`;
    document.body.appendChild(modal);
    _reinitIcons();
  }

  function closeOverlay(id) {
    document.getElementById(id)?.remove();
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Utility Functions
   * ═══════════════════════════════════════════════════════════════ */

  function formatTime(iso) {
    if (!iso) return 'Not scheduled';
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) +
        ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
  }

  function getDuration(m) {
    if (!m.started_at || !m.completed_at) return '';
    try {
      const start = new Date(m.started_at);
      const end = new Date(m.completed_at);
      const mins = Math.round((end - start) / 60000);
      if (mins < 60) return mins + 'm';
      return Math.floor(mins / 60) + 'h ' + (mins % 60) + 'm';
    } catch { return ''; }
  }

  function _setText(sel, val) { const el = $(sel); if (el) el.textContent = val; }

  function _reinitIcons() {
    if (typeof lucide !== 'undefined') {
      try { lucide.createIcons(); } catch { /* ignore */ }
    }
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Keyboard Shortcuts
   * ═══════════════════════════════════════════════════════════════ */

  function handleKeyboard(e) {
    const panel = $('[data-tab-content="schedule"]');
    if (!panel || panel.classList.contains('hidden-view')) return;

    if (e.ctrlKey || e.metaKey) {
      if (e.key === '1') { e.preventDefault(); setViewMode('timeline'); }
      if (e.key === '2') { e.preventDefault(); setViewMode('list'); }
      if (e.key === '3') { e.preventDefault(); setViewMode('calendar'); }
    }

    if (e.key === 'r' && !e.ctrlKey && !e.metaKey && e.target.tagName !== 'INPUT' && e.target.tagName !== 'SELECT') {
      refresh();
    }
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Debounce helper for search input
   * ═══════════════════════════════════════════════════════════════ */

  let _searchTimer = null;
  function debouncedSearch(value) {
    clearTimeout(_searchTimer);
    _searchTimer = setTimeout(() => updateFilter('search', value), 250);
  }

  /* ═══════════════════════════════════════════════════════════════
   *  Init & Public API
   * ═══════════════════════════════════════════════════════════════ */

  function init() {
    if (!_initialized) {
      document.addEventListener('keydown', handleKeyboard);
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden && isScheduleTabActive() && !hasFreshCache()) {
          refresh({ silent: true });
        }
      });
      _initialized = true;
    }
    refresh();
    if (!autoRefreshTimer) {
      autoRefreshTimer = setInterval(() => {
        if (!isScheduleTabActive()) return;
        refresh({ silent: true });
      }, AUTO_REFRESH_MS);
    }
  }

  window.TOC = window.TOC || {};
  window.TOC.schedule = {
    init,
    refresh,
    setViewMode,
    updateFilter,
    clearFilters,
    debouncedSearch,
    toggleSort,
    openAutoSchedule,
    confirmAutoSchedule,
    openBulkShift,
    confirmBulkShift,
    openAddBreak,
    confirmAddBreak,
    openReschedule,
    confirmReschedule,
    openManualSchedule,
    confirmManualSchedule,
    openUserGuide,
    exportICS,
    closeOverlay,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'schedule') init();
  });
})();
