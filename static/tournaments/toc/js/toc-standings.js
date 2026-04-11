/**
 * TOC Standings Module — Sprint 28
 * Standings/leaderboards tab: group standings, qualification tracker,
 * historical snapshots, export.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);

  const CACHE_TTL_MS = 25000;
  const AUTO_REFRESH_MS = 45000;
  const STAT_IDS = ['groups', 'teams', 'matches', 'leader'];
  const PANEL_IDS = ['standings-content', 'standings-qualification'];

  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }

  let dashboardData = null;
  let bracketStandingsData = null;
  let standingsStageFilter = '';  // '' | 'group' | 'knockout'
  let currentStage = null;
  let inflightPromise = null;
  let inflightGroupId = '';
  let activeRequestId = 0;
  let lastFetchedAt = 0;
  let lastGroupId = '';
  let autoRefreshTimer = null;

  function isStandingsTabActive() {
    return (window.location.hash || '').replace('#', '') === 'standings';
  }

  function hasFreshCache(groupId) {
    return !!dashboardData
      && (Date.now() - lastFetchedAt) < CACHE_TTL_MS
      && String(lastGroupId || '') === String(groupId || '');
  }

  function formatTime(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function setSyncStatus(state, note) {
    const el = $('#standings-sync-status');
    if (!el) return;

    if (state === 'loading') {
      el.className = 'text-[10px] font-mono text-dc-warning mt-1';
      el.textContent = note || 'Syncing standings...';
      return;
    }

    if (state === 'error') {
      el.className = 'text-[10px] font-mono text-dc-danger mt-1';
      el.textContent = note || 'Sync failed';
      return;
    }

    if (lastFetchedAt > 0) {
      el.className = 'text-[10px] font-mono text-dc-text mt-1';
      el.textContent = `Last sync ${formatTime(new Date(lastFetchedAt))}`;
      return;
    }

    el.className = 'text-[10px] font-mono text-dc-text mt-1';
    el.textContent = 'Not synced yet';
  }

  function setErrorBanner(message) {
    const el = $('#standings-error-banner');
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
          <p class="text-xs font-bold text-white">Standings request failed</p>
          <p class="text-[11px] text-dc-text mt-1">${esc(message)}</p>
          <button type="button" class="mt-2 px-2.5 py-1 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" data-click="TOC.standings.refresh" data-click-args="[{&quot;force&quot;:true}]">Retry now</button>
        </div>
      </div>`;
    refreshIcons();
  }

  function setLoading(loading) {
    STAT_IDS.forEach((id) => {
      const el = $(`#standings-stat-${id}`);
      if (!el) return;
      el.classList.toggle('toc-loading-value', loading);
    });

    PANEL_IDS.forEach((id) => {
      const el = $(`#${id}`);
      if (!el) return;
      el.classList.toggle('toc-panel-loading', loading);
      if (loading) el.setAttribute('aria-busy', 'true');
      else el.removeAttribute('aria-busy');
    });
  }

  function renderDashboard(data, qual) {
    const safe = data && typeof data === 'object' ? data : {};
    const safeQual = qual && typeof qual === 'object' ? qual : { groups: [] };

    renderStats(safe);
    renderStandingsStageTabs();

    if (standingsStageFilter === 'knockout') {
      renderBracketStandings(bracketStandingsData);
    } else if (standingsStageFilter === 'group') {
      renderStandings(safe);
    } else {
      // Show both if available
      renderStandings(safe);
      if (bracketStandingsData) renderBracketStandings(bracketStandingsData);
    }

    renderGroupFilter(Array.isArray(safe.groups) ? safe.groups : []);
    renderQualification(safeQual);

    setLoading(false);
    setErrorBanner('');
    setSyncStatus('ok');
  }

  function renderEmptyState(message) {
    const content = $('#standings-content');
    const qual = $('#standings-qualification');

    if (content) {
      content.innerHTML = `
        <div class="glass-box rounded-xl p-8 text-center">
          <p class="text-sm text-dc-danger">${esc(message || 'Standings are unavailable')}</p>
        </div>`;
    }

    if (qual) {
      qual.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No qualification data</p>';
    }

    setLoading(false);
  }

  /* ─── Fetch & render ─────────────────────────────────────── */
  async function refresh(options) {
    const opts = options || {};
    const force = opts.force === true;
    const silent = opts.silent === true;
    const groupId = $('#standings-group-filter')?.value || '';

    if (dashboardData && !force) {
      renderDashboard(dashboardData, dashboardData._qualification || { groups: [] });
      if (hasFreshCache(groupId)) {
        return dashboardData;
      }
    }

    if (inflightPromise && !force && String(inflightGroupId || '') === String(groupId || '')) return inflightPromise;

    if (!silent) {
      setLoading(true);
      setSyncStatus('loading', dashboardData ? 'Refreshing standings...' : 'Loading standings...');
    }

    const requestId = ++activeRequestId;
    inflightGroupId = groupId;
    inflightPromise = (async () => {
      try {
        const [data, qual] = await Promise.all([
          API.get(`standings/?group_id=${groupId}`),
          API.get('standings/qualification/'),
        ]);

        if (requestId !== activeRequestId) return dashboardData || data;

        dashboardData = data || {};
        dashboardData._qualification = qual || { groups: [] };
        bracketStandingsData = data.bracket_standings || null;
        currentStage = data.current_stage || null;
        lastFetchedAt = Date.now();
        lastGroupId = groupId;

        renderDashboard(dashboardData, dashboardData._qualification);
        return dashboardData;
      } catch (e) {
        if (requestId !== activeRequestId) return dashboardData;

        const detail = e && e.message ? String(e.message) : 'Request failed';
        console.error('[standings] fetch error', e);

        if (dashboardData) {
          setLoading(false);
          setSyncStatus('error', `Using cached data (${detail})`);
          setErrorBanner(`Live refresh failed, showing cached standings data. ${detail}`);
        } else {
          setSyncStatus('error', detail);
          setErrorBanner(detail);
          renderEmptyState('Failed to load standings data.');
        }
        return dashboardData;
      } finally {
        if (requestId === activeRequestId) {
          inflightPromise = null;
          inflightGroupId = '';
        }
      }
    })();

    return inflightPromise;
  }

  function invalidate() {
    lastFetchedAt = 0;
  }

  function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshTimer = setInterval(() => {
      if (!isStandingsTabActive()) return;
      refresh({ silent: true });
    }, AUTO_REFRESH_MS);
  }

  function stopAutoRefresh() {
    if (autoRefreshTimer) {
      clearInterval(autoRefreshTimer);
      autoRefreshTimer = null;
    }
  }

  function onTabChange(e) {
    if (e.detail?.tab === 'standings') {
      refresh();
      startAutoRefresh();
      return;
    }
    stopAutoRefresh();
  }

  function onVisibilityChange() {
    if (!document.hidden && isStandingsTabActive() && !hasFreshCache($('#standings-group-filter')?.value || '')) {
      refresh({ silent: true });
    }
  }

  function renderStats(data) {
    const s = data.summary || {};
    const el = (id, v) => { const e = $(`#standings-stat-${id}`); if (e) e.textContent = v; };
    el('groups', s.total_groups || data.groups?.length || 0);
    el('teams', s.total_teams || 0);
    el('matches', s.total_matches || 0);
    el('leader', s.leader || '-');
  }

  function renderGroupFilter(groups) {
    const sel = $('#standings-group-filter');
    if (!sel) return;
    const current = sel.value;
    const opts = ['<option value="">All Groups</option>'];
    groups.forEach(g => {
      opts.push(`<option value="${g.group_id}"${g.group_id == current ? ' selected' : ''}>${g.group_name || 'Group ' + g.group_id}</option>`);
    });
    sel.innerHTML = opts.join('');
  }

  function renderStandings(data) {
    const container = $('#standings-content');
    if (!container) return;

    const groups = data.groups || [];
    if (!groups.length) {
      container.innerHTML = `
        <div class="glass-box rounded-xl p-8 text-center">
          <i data-lucide="trophy" class="w-10 h-10 mx-auto mb-3 text-dc-text opacity-20"></i>
          <p class="text-sm text-dc-text">No standings data yet. Generate brackets and play some matches first.</p>
        </div>`;
      refreshIcons();
      return;
    }

    let html = '';
    groups.forEach(g => {
      const standings = g.standings || [];
      html += `
        <div class="glass-box rounded-xl overflow-hidden">
          <div class="p-4 border-b border-dc-border bg-dc-panel/50">
            <h3 class="font-display font-bold text-white text-sm">${esc(g.group_name || 'Group')}</h3>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-dc-border text-dc-text uppercase tracking-widest">
                  <th class="px-4 py-3 text-left">#</th>
                  <th class="px-4 py-3 text-left">Team</th>
                  <th class="px-4 py-3 text-center">W</th>
                  <th class="px-4 py-3 text-center">D</th>
                  <th class="px-4 py-3 text-center">L</th>
                  <th class="px-4 py-3 text-center">Pts</th>
                  <th class="px-4 py-3 text-center">Win%</th>
                  <th class="px-4 py-3 text-center">Form</th>
                </tr>
              </thead>
              <tbody>`;

      standings.forEach((s, idx) => {
        const isQualified = idx < (g.qualify_count || 2);
        const bgCls = isQualified ? 'bg-dc-success/5' : '';
        const rankCls = isQualified ? 'text-dc-success font-bold' : 'text-dc-text';
        const form = (s.form || []).map(f => {
          if (f === 'W') return '<span class="inline-block w-5 h-5 rounded text-[10px] font-bold bg-dc-success/20 text-dc-success flex items-center justify-center">W</span>';
          if (f === 'L') return '<span class="inline-block w-5 h-5 rounded text-[10px] font-bold bg-dc-danger/20 text-dc-danger flex items-center justify-center">L</span>';
          return '<span class="inline-block w-5 h-5 rounded text-[10px] font-bold bg-dc-text/10 text-dc-text flex items-center justify-center">D</span>';
        }).join('');

        html += `
                <tr class="border-b border-dc-border/50 hover:bg-white/[.02] ${bgCls}">
                  <td class="px-4 py-2.5 ${rankCls}">${s.rank || idx + 1}</td>
                  <td class="px-4 py-2.5 text-white font-medium">${esc(s.name)}</td>
                  <td class="px-4 py-2.5 text-center text-dc-success">${s.wins || 0}</td>
                  <td class="px-4 py-2.5 text-center text-dc-text">${s.draws || 0}</td>
                  <td class="px-4 py-2.5 text-center text-dc-danger">${s.losses || 0}</td>
                  <td class="px-4 py-2.5 text-center text-theme font-bold">${s.points || 0}</td>
                  <td class="px-4 py-2.5 text-center">${s.win_rate || '0'}%</td>
                  <td class="px-4 py-2.5"><div class="flex gap-0.5 justify-center">${form}</div></td>
                </tr>`;
      });

      html += `
              </tbody>
            </table>
          </div>
        </div>`;
    });

    container.innerHTML = html;
    refreshIcons();
  }

  /* --- Stage tabs for standings ----------------------------- */
  function renderStandingsStageTabs() {
    var container = document.querySelector('#standings-stage-tabs');
    if (!container) return;
    var cfg = window.TOC_CONFIG || {};
    var fmt = (cfg.tournamentFormat || '').toLowerCase();
    if (fmt !== 'group_playoff') { container.classList.add('hidden'); return; }
    container.classList.remove('hidden');

    var tabs = [
      { key: '', label: 'All' },
      { key: 'group', label: 'Group Stage' },
      { key: 'knockout', label: 'Knockout Bracket' },
    ];
    container.innerHTML = tabs.map(function(t) {
      var active = standingsStageFilter === t.key;
      return '<button data-stage="' + t.key + '" class="' +
        (active ? 'bg-theme/15 text-theme border-theme/30' : 'bg-dc-bg text-dc-text border-dc-border hover:text-white') +
        ' px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all border" ' +
        'data-click="TOC.standings.filterStage" data-click-args="[&quot;' + t.key + '&quot;]" role="tab" aria-selected="' + active + '">' +
        t.label + '</button>';
    }).join('');
  }

  function filterStandingsStage(stg) {
    standingsStageFilter = stg || '';
    if (dashboardData) renderDashboard(dashboardData, dashboardData._qualification || { groups: [] });
  }

  /* --- Bracket standings (knockout) ------------------------ */
  function renderBracketStandings(bs) {
    var container = document.querySelector('#standings-bracket');
    if (!container) { /* If container doesn't exist, append to main content */
      container = document.querySelector('#standings-content');
      if (!container) return;
    }
    if (!bs || !bs.rounds || !bs.rounds.length) {
      if (document.querySelector('#standings-bracket')) {
        document.querySelector('#standings-bracket').innerHTML = '';
      }
      return;
    }

    var html = '<div class="glass-box rounded-xl overflow-hidden mt-4">' +
      '<div class="p-4 border-b border-dc-border bg-dc-panel/50 flex items-center justify-between">' +
      '<div><h3 class="font-display font-bold text-white text-sm">Knockout Bracket</h3>' +
      '<p class="text-[10px] text-dc-text mt-0.5">' + esc(bs.format || 'Single Elimination') +
      ' &middot; ' + (bs.total_rounds || 0) + ' rounds &middot; ' +
      (bs.completion_pct || 0) + '% complete</p></div>' +
      (bs.is_finalized ? '<span class="text-[9px] font-bold text-dc-success bg-dc-success/15 px-2 py-0.5 rounded-full border border-dc-success/30">FINALIZED</span>' : '') +
      '</div>';

    bs.rounds.forEach(function(round) {
      html += '<div class="p-4 border-b border-dc-border/30">' +
        '<h4 class="text-xs font-bold text-amber-300 uppercase tracking-widest mb-3">' +
        esc(round.round_label || 'Round ' + round.round) + '</h4>' +
        '<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">';

      (round.matches || []).forEach(function(m) {
        var p1Class = m.winner === 'p1' ? 'text-dc-success font-bold' : 'text-dc-textBright';
        var p2Class = m.winner === 'p2' ? 'text-dc-success font-bold' : 'text-dc-textBright';
        var stateLabel = m.match_state === 'completed' ? 'Done' : m.match_state === 'live' ? 'LIVE' : m.match_state || 'Pending';
        var stateCls = m.match_state === 'completed' ? 'text-dc-text' : m.match_state === 'live' ? 'text-dc-success animate-pulse' : 'text-dc-warning';

        html += '<div class="bg-dc-bg border border-dc-border rounded-lg p-3">' +
          '<div class="flex items-center justify-between mb-2">' +
          '<span class="text-[9px] font-mono text-dc-text">' + esc(m.round_label || '') + '</span>' +
          '<span class="text-[8px] font-bold uppercase ' + stateCls + '">' + stateLabel + '</span>' +
          '</div>' +
          '<div class="space-y-1">' +
          '<div class="flex items-center justify-between"><span class="text-xs ' + p1Class + ' truncate">' + esc(m.participant1_name || 'TBD') + '</span>' +
          (m.winner === 'p1' ? '<i data-lucide="trophy" class="w-3 h-3 text-dc-success ml-1"></i>' : '') + '</div>' +
          '<div class="flex items-center justify-between"><span class="text-xs ' + p2Class + ' truncate">' + esc(m.participant2_name || 'TBD') + '</span>' +
          (m.winner === 'p2' ? '<i data-lucide="trophy" class="w-3 h-3 text-dc-success ml-1"></i>' : '') + '</div>' +
          '</div></div>';
      });

      html += '</div></div>';
    });

    html += '</div>';

    if (standingsStageFilter === 'knockout') {
      container.innerHTML = html;
    } else {
      container.insertAdjacentHTML('beforeend', html);
    }
    refreshIcons();
  }

  function renderQualification(data) {
    const container = $('#standings-qualification');
    if (!container) return;

    const groups = data.groups || [];
    if (!groups.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No qualification data</p>';
      return;
    }

    let html = '<div class="grid grid-cols-1 md:grid-cols-2 gap-3">';
    groups.forEach(g => {
      const qualified = g.qualified || [];
      html += `
        <div class="bg-dc-surface/50 rounded-lg p-3">
          <h4 class="text-xs font-bold text-white mb-2">${esc(g.group_name)}</h4>
          <div class="space-y-1">`;
      qualified.forEach(q => {
        html += `
            <div class="flex items-center justify-between text-xs">
              <span class="text-dc-textBright">${esc(q.name)}</span>
              <span class="text-dc-success text-[10px] font-bold">QUALIFIED</span>
            </div>`;
      });
      html += '</div></div>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  async function exportStandings() {
    try {
      const data = await API.get('standings/export/');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `standings_${slug}.json`; a.click();
      URL.revokeObjectURL(url);
      toast('Standings exported', 'success');
    } catch (e) {
      toast('Export failed', 'error');
    }
  }

  function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
  function refreshIcons() { if (typeof lucide !== 'undefined') lucide.createIcons(); }

  window.TOC = window.TOC || {};
  window.TOC.standings = { refresh, exportStandings, invalidate, filterStage: filterStandingsStage };

  document.addEventListener('toc:tab-changed', onTabChange);
  document.addEventListener('visibilitychange', onVisibilityChange);

  if (isStandingsTabActive()) {
    refresh();
    startAutoRefresh();
  }
})();
