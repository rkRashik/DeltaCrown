/**
 * TOC Rosters Module — Sprint 28 (redesigned)
 * Professional team card UI with player role badges, game IDs, check-in status,
 * search/filter, and change log. Reads lineup_snapshot via the fixed backend.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);
  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }
  function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
  function refreshIcons() { if (typeof lucide !== 'undefined') lucide.createIcons(); }

  let dashData = null;
  let searchQuery = '';
  let slotFilter = 'all';   // 'all' | 'starter' | 'sub'
  let statusFilter = 'all'; // 'all' | 'valid' | 'invalid'

  /* ─────────────────────────── Data fetch ─────────────────────────── */

  async function refresh() {
    const container = $('#rosters-teams-list');
    if (container) container.innerHTML = `
      <div class="flex items-center justify-center py-12 gap-2 text-dc-text opacity-60">
        <span class="inline-block w-4 h-4 border-2 border-theme border-t-transparent rounded-full animate-spin"></span>
        <span class="text-sm">Loading rosters…</span>
      </div>`;
    try {
      const data = await API.get('rosters/');
      dashData = data;
      renderAll(data);
    } catch (e) {
      console.error('[rosters] fetch error', e);
      if (container) container.innerHTML = `
        <div class="glass-box rounded-xl p-8 text-center">
          <p class="text-sm text-dc-danger">Failed to load rosters. Please refresh.</p>
        </div>`;
    }
  }

  function renderAll(data) {
    renderStats(data.summary || {});
    renderConfig(data.config || {});
    renderSearchBar();
    renderTeams(data.teams || []);
    renderSoloPlayers(data.solo_players || []);
    renderChangeLog(data.change_log || []);
    updateLockButtons(data.config?.locked);
  }

  /* ─────────────────────────── Stats bar ─────────────────────────── */

  function renderStats(s) {
    const el = (id, v) => { const e = $(`#rosters-stat-${id}`); if (e) e.textContent = v; };
    el('teams', s.total_teams ?? 0);
    el('players', s.total_players ?? 0);
    el('valid', s.valid_rosters ?? 0);
    el('invalid', s.invalid_rosters ?? 0);
    el('status', s.locked ? 'Locked' : 'Open');
    // New stats
    const gidEl = $(`#rosters-stat-game-ids`);
    if (gidEl) gidEl.textContent = s.players_with_game_ids ?? 0;
  }

  /* ─────────────────────────── Search / filter bar ───────────────── */

  function renderSearchBar() {
    const bar = $('#rosters-search-bar');
    if (!bar || bar.dataset.initialized) return;
    bar.dataset.initialized = '1';
    bar.innerHTML = `
      <div class="flex flex-wrap gap-2 items-center mb-4">
        <div class="relative flex-1 min-w-[180px]">
          <i data-lucide="search" class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-dc-text pointer-events-none"></i>
          <input id="rosters-search-input" type="text" placeholder="Search team or player…"
            class="w-full pl-8 pr-3 py-1.5 text-xs bg-dc-surface/60 border border-dc-border/50 rounded-lg text-white placeholder:text-dc-text/50 focus:outline-none focus:border-theme/50">
        </div>
        <div class="flex gap-1" id="rosters-filter-chips"></div>
      </div>`;
    refreshIcons();

    const input = $('#rosters-search-input');
    if (input) {
      input.addEventListener('input', () => {
        searchQuery = input.value.trim().toLowerCase();
        renderTeams(dashData?.teams || [], dashData?.solo_players || []);
      });
    }

    renderFilterChips();
  }

  function renderFilterChips() {
    const wrap = $('#rosters-filter-chips');
    if (!wrap) return;
    const chips = [
      { key: 'all', label: 'All' },
      { key: 'valid', label: 'Valid' },
      { key: 'invalid', label: 'Issues' },
    ];
    wrap.innerHTML = chips.map(c => `
      <button onclick="TOC.rosters._setFilter('${c.key}')"
        class="rosters-chip text-[11px] px-3 py-1 rounded-full border transition-colors ${statusFilter === c.key
          ? 'bg-theme text-black border-theme font-semibold'
          : 'bg-transparent text-dc-text border-dc-border/50 hover:border-theme/50'}"
        data-filter="${c.key}">${esc(c.label)}</button>
    `).join('');
  }

  /* ─────────────────────────── Team cards ─────────────────────────── */

  function renderTeams(teams) {
    const container = $('#rosters-teams-list');
    if (!container) return;

    // Apply search filter
    let filtered = teams;
    if (searchQuery) {
      filtered = teams.filter(t => {
        const nameMatch = (t.team_name || '').toLowerCase().includes(searchQuery)
          || (t.tag || '').toLowerCase().includes(searchQuery);
        const playerMatch = (t.players || []).some(p =>
          (p.display_name || p.username || '').toLowerCase().includes(searchQuery)
          || (p.game_id || '').toLowerCase().includes(searchQuery)
        );
        return nameMatch || playerMatch;
      });
    }
    if (statusFilter === 'valid') filtered = filtered.filter(t => t.roster_valid);
    if (statusFilter === 'invalid') filtered = filtered.filter(t => !t.roster_valid);

    if (!filtered.length) {
      container.innerHTML = `
        <div class="glass-box rounded-xl p-10 text-center">
          <i data-lucide="users-round" class="w-10 h-10 mx-auto mb-3 text-dc-text opacity-20"></i>
          <p class="text-sm text-dc-text">${searchQuery || statusFilter !== 'all' ? 'No teams match your filter' : 'No teams registered yet'}</p>
        </div>`;
      refreshIcons();
      return;
    }

    container.innerHTML = `<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">${filtered.map(t => buildTeamCard(t)).join('')}</div>`;
    refreshIcons();
  }

  function renderSoloPlayers(players) {
    const container = $('#rosters-solo-list');
    if (!container) return;
    if (!players.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-40">No solo players</p>';
      return;
    }
    const rows = players.map(p => {
      const avatarLetter = (p.display_name || p.username || '?')[0].toUpperCase();
      const gameIdHtml = p.game_id
        ? `<span class="font-mono text-[10px] text-emerald-300">${esc(p.game_id)}</span>`
        : `<span class="text-[10px] text-dc-text opacity-35 italic">—</span>`;
      return `
        <tr class="hover:bg-white/[.02] transition-colors">
          <td class="px-3 py-1.5">
            <div class="flex items-center gap-2">
              <span class="w-5 h-5 rounded-full bg-dc-surface/80 border border-dc-border/50 flex items-center justify-center text-[9px] font-bold text-dc-text">${esc(avatarLetter)}</span>
              <span class="text-white text-[11px]">${esc(p.display_name || p.username)}</span>
            </div>
          </td>
          <td class="px-3 py-1.5">${gameIdHtml}</td>
          <td class="px-3 py-1.5 text-right"><span class="text-[9px] text-dc-text">${p.checked_in ? '✓ In' : '—'}</span></td>
        </tr>`;
    }).join('');
    container.innerHTML = `
      <table class="w-full text-xs">
        <thead><tr class="border-b border-dc-border/30">
          <th class="text-left px-3 py-2 text-[10px] text-dc-text font-medium uppercase tracking-wide">Player</th>
          <th class="text-left px-3 py-2 text-[10px] text-dc-text font-medium uppercase tracking-wide">Game ID</th>
          <th class="text-right px-3 py-2 text-[10px] text-dc-text font-medium uppercase tracking-wide">Check-In</th>
        </tr></thead>
        <tbody class="divide-y divide-dc-border/20">${rows}</tbody>
      </table>`;
  }

  function buildTeamCard(t) {
    const accentColor = t.primary_color || '';
    const accentStyle = accentColor ? `style="border-color: ${accentColor}40; --team-accent: ${accentColor};"` : '';
    const initials = (t.tag || t.team_name || '?').slice(0, 3).toUpperCase();
    const logoHtml = t.logo_url
      ? `<img src="${esc(t.logo_url)}" alt="" class="w-10 h-10 rounded-lg object-cover">`
      : `<div class="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold text-white"
            style="background:${accentColor || 'var(--color-theme, #7c3aed)'}30; color:${accentColor || 'var(--color-theme, #7c3aed)'}">${esc(initials)}</div>`;

    const validBadge = t.roster_valid
      ? `<span class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-dc-success/15 text-dc-success border border-dc-success/20">
           <i data-lucide="check" class="w-2.5 h-2.5"></i>Valid
         </span>`
      : `<span class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-dc-danger/15 text-dc-danger border border-dc-danger/20">
           <i data-lucide="alert-triangle" class="w-2.5 h-2.5"></i>Issues
         </span>`;

    const ignsOk = t.has_game_ids
      ? `<span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">IDs ✓</span>`
      : `<span class="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">IDs missing</span>`;

    const checkinBadge = t.checked_in
      ? `<span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">Checked In</span>`
      : '';

    const captainLine = t.captain_name
      ? `<p class="text-[10px] text-dc-text mt-0.5">IGL: <span class="text-theme font-medium">${esc(t.captain_name)}</span></p>`
      : '';

    const playerRows = (t.players || []).map(p => buildPlayerRow(t, p)).join('');

    return `
      <div class="glass-box rounded-xl border border-dc-border/50 overflow-hidden flex flex-col" ${accentStyle}>
        <!-- Card header -->
        <div class="px-4 py-3 border-b border-dc-border/40 flex items-start justify-between gap-3"
             style="${accentColor ? `border-left: 3px solid ${accentColor};` : ''}">
          <div class="flex items-center gap-3 min-w-0">
            ${logoHtml}
            <div class="min-w-0">
              <p class="text-sm font-bold text-white leading-tight truncate">${esc(t.team_name)}</p>
              ${t.tag ? `<p class="text-[11px] text-dc-text">[${esc(t.tag)}] · ${t.size} player${t.size !== 1 ? 's' : ''}</p>` : `<p class="text-[11px] text-dc-text">${t.size} player${t.size !== 1 ? 's' : ''}</p>`}
              ${captainLine}
            </div>
          </div>
          <div class="flex flex-col items-end gap-1 shrink-0">
            ${validBadge}
            ${ignsOk}
            ${checkinBadge}
          </div>
        </div>

        <!-- Player table -->
        <div class="flex-1 overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-dc-border/30">
                <th class="text-left px-3 py-2 text-[10px] text-dc-text font-medium uppercase tracking-wide">Player</th>
                <th class="text-left px-3 py-2 text-[10px] text-dc-text font-medium uppercase tracking-wide">Role</th>
                <th class="text-left px-3 py-2 text-[10px] text-dc-text font-medium uppercase tracking-wide">Game ID</th>
                <th class="text-right px-3 py-2 text-[10px] text-dc-text font-medium uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-dc-border/20">
              ${playerRows || '<tr><td colspan="4" class="px-3 py-4 text-center text-dc-text opacity-50 text-xs">No players in snapshot</td></tr>'}
            </tbody>
          </table>
        </div>

        <!-- Card footer -->
        <div class="px-4 py-2 border-t border-dc-border/30 flex items-center justify-between">
          <span class="text-[10px] text-dc-text opacity-60">${t.registered_at ? 'Reg: ' + new Date(t.registered_at).toLocaleDateString() : ''}</span>
          <button onclick="TOC.rosters.addPlayer(${t.team_id})"
            class="inline-flex items-center gap-1 text-[10px] text-theme hover:underline">
            <i data-lucide="user-plus" class="w-3 h-3"></i>Add Player
          </button>
        </div>
      </div>`;
  }

  function buildPlayerRow(t, p) {
    // Role badge
    let roleBadge = '';
    if (p.is_igl) {
      roleBadge = `<span class="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded font-bold bg-theme/20 text-theme border border-theme/30">
        <i data-lucide="crown" class="w-2.5 h-2.5"></i>IGL</span>`;
    } else if (p.roster_slot === 'SUBSTITUTE') {
      roleBadge = `<span class="text-[9px] px-1.5 py-0.5 rounded bg-slate-500/20 text-slate-400 border border-slate-500/20">SUB</span>`;
    } else {
      roleBadge = `<span class="text-[9px] px-1.5 py-0.5 rounded bg-dc-surface/60 text-dc-text border border-dc-border/30">START</span>`;
    }

    // In-game role (e.g. "Duelist", "Controller") if populated
    const roleLabel = p.player_role
      ? `<span class="ml-1 text-[9px] text-dc-text opacity-70">${esc(p.player_role)}</span>` : '';

    // Player avatar initial
    const avatarLetter = (p.display_name || p.username || '?')[0].toUpperCase();
    const avatarHtml = p.avatar
      ? `<img src="${esc(p.avatar)}" alt="" class="w-5 h-5 rounded-full object-cover">`
      : `<span class="w-5 h-5 rounded-full bg-dc-surface/80 border border-dc-border/50 flex items-center justify-center text-[9px] font-bold text-dc-text">${esc(avatarLetter)}</span>`;

    // Game ID — monospace, muted if empty
    const gameIdHtml = p.game_id
      ? `<span class="font-mono text-[10px] text-emerald-300">${esc(p.game_id)}</span>`
      : `<span class="text-[10px] text-dc-text opacity-35 italic">—</span>`;

    // Check-in indicator
    const ciDot = p.checked_in
      ? `<span class="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" title="Checked in"></span>` : '';

    // Actions
    const setIglBtn = !p.is_igl
      ? `<button onclick="TOC.rosters.setCaptain(${t.team_id}, ${p.user_id ?? 0})"
           class="text-[9px] text-dc-text hover:text-theme transition-colors" title="Set as IGL">IGL</button>` : '';
    const removeBtn = `<button onclick="TOC.rosters.removePlayer(${t.team_id}, ${p.user_id ?? 0})"
       class="text-[9px] text-dc-danger hover:underline" title="Remove from roster">✕</button>`;

    return `
      <tr class="hover:bg-white/[.02] transition-colors">
        <td class="px-3 py-1.5">
          <div class="flex items-center gap-1.5">
            ${avatarHtml}
            <span class="text-white text-[11px] truncate max-w-[120px]">${esc(p.display_name || p.username || `User #${p.user_id}`)}</span>
            ${ciDot}
          </div>
        </td>
        <td class="px-3 py-1.5">
          <div class="flex items-center gap-1">
            ${roleBadge}${roleLabel}
          </div>
        </td>
        <td class="px-3 py-1.5">${gameIdHtml}</td>
        <td class="px-3 py-1.5 text-right">
          <div class="flex items-center justify-end gap-2">
            ${setIglBtn}
            ${removeBtn}
          </div>
        </td>
      </tr>`;
  }

  /* ─────────────────────────── Lock buttons ───────────────────────── */

  function updateLockButtons(locked) {
    const lockBtn = $('#rosters-lock-btn');
    const unlockBtn = $('#rosters-unlock-btn');
    if (locked) {
      lockBtn?.classList.add('hidden');
      unlockBtn?.classList.remove('hidden');
    } else {
      lockBtn?.classList.remove('hidden');
      unlockBtn?.classList.add('hidden');
    }
  }

  /* ─────────────────────────── Config form ────────────────────────── */

  function renderConfig(config) {
    const set = (id, val) => { const e = $(id); if (e) e.value = val; };
    const chk = (id, val) => { const e = $(id); if (e) e.checked = val; };
    set('#rosters-min-size', config.min_roster_size ?? 1);
    set('#rosters-max-size', config.max_roster_size ?? 10);
    chk('#rosters-allow-subs', config.allow_subs !== false);
    set('#rosters-max-subs', config.max_subs ?? 2);
  }

  /* ─────────────────────────── Change log ─────────────────────────── */

  function renderChangeLog(log) {
    const container = $('#rosters-change-log');
    if (!container) return;

    if (!log.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-40">No changes recorded yet</p>';
      return;
    }

    container.innerHTML = log.slice().reverse().map(entry => {
      const time = entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '';
      const icon = entry.action?.includes('lock') ? 'lock' : entry.action?.includes('captain') ? 'crown' : 'pencil';
      return `
        <div class="flex items-center gap-2 px-3 py-2 hover:bg-white/[.02] rounded transition-colors">
          <i data-lucide="${icon}" class="w-3 h-3 text-dc-text opacity-50 shrink-0"></i>
          <span class="text-[11px] text-white flex-1">${esc(entry.action)}</span>
          <span class="text-[10px] text-dc-text opacity-60 shrink-0">${esc(time)}</span>
        </div>`;
    }).join('');
    refreshIcons();
  }

  /* ─────────────────────────── Actions ────────────────────────────── */

  async function lockRosters() {
    if (!confirm('Lock all rosters? No more changes will be allowed.')) return;
    try { await API.post('rosters/lock/', {}); toast('Rosters locked', 'warning'); refresh(); }
    catch { toast('Failed to lock', 'error'); }
  }

  async function unlockRosters() {
    try { await API.post('rosters/unlock/', {}); toast('Rosters unlocked', 'success'); refresh(); }
    catch { toast('Failed to unlock', 'error'); }
  }

  async function setCaptain(teamId, userId) {
    if (!userId) { toast('No user ID', 'error'); return; }
    try { await API.post('rosters/captain/', { team_id: teamId, user_id: userId }); toast('IGL updated', 'success'); refresh(); }
    catch { toast('Failed', 'error'); }
  }

  async function removePlayer(teamId, userId) {
    if (!confirm('Remove this player from the roster?')) return;
    try { await API.post('rosters/remove-player/', { team_id: teamId, user_id: userId }); toast('Player removed', 'success'); refresh(); }
    catch { toast('Failed', 'error'); }
  }

  function addPlayer(teamId) {
    const userId = prompt('Enter User ID to add to this roster:');
    if (!userId || isNaN(+userId)) return;
    API.post('rosters/add-player/', { team_id: teamId, user_id: parseInt(userId) })
      .then(() => { toast('Player added', 'success'); refresh(); })
      .catch(() => toast('Failed to add player', 'error'));
  }

  async function checkEligibility(teamId) {
    try {
      const data = await API.get(`rosters/eligibility/${teamId}/`);
      if (data.eligible) toast('Team is eligible!', 'success');
      else toast(`Ineligible: ${(data.issues || []).join(', ')}`, 'warning');
    } catch { toast('Failed', 'error'); }
  }

  async function saveConfig() {
    const data = {
      min_roster_size: parseInt($('#rosters-min-size')?.value || '1'),
      max_roster_size: parseInt($('#rosters-max-size')?.value || '10'),
      allow_subs: $('#rosters-allow-subs')?.checked || false,
      max_subs: parseInt($('#rosters-max-subs')?.value || '2'),
    };
    try { await API.post('rosters/config/', data); toast('Config saved', 'success'); }
    catch { toast('Save failed', 'error'); }
  }

  function _setFilter(key) {
    statusFilter = key;
    renderFilterChips();
    renderTeams(dashData?.teams || [], dashData?.solo_players || []);
  }

  /* ─────────────────────────── Public API ─────────────────────────── */

  window.TOC = window.TOC || {};
  window.TOC.rosters = {
    refresh, lockRosters, unlockRosters,
    setCaptain, removePlayer, addPlayer,
    checkEligibility, saveConfig,
    _setFilter,
  };

  // Auto-load when tab is activated
  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail?.tab === 'rosters') refresh();
  });
})();
