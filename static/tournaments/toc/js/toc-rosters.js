/**
 * TOC Rosters Module — Sprint 29 (full redesign)
 *
 * Features:
 * - Dynamic game_id_label from game model (e.g. "Riot ID")
 * - Player grouping: Starters, Substitutes, Coach/Manager
 * - Clickable team → /teams/{slug}/, player → /u/{profile_slug}/
 * - Coordinator vs IGL distinction
 * - Communication channels display
 * - Enhanced actions: Set IGL, Remove, View Profile, Message
 * - Team social links (Discord, Twitter, Website)
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

  const CACHE_TTL_MS = 25000;
  const AUTO_REFRESH_MS = 45000;
  const STAT_IDS = ['teams', 'players', 'valid', 'invalid', 'game-ids', 'status'];
  const PANEL_IDS = ['rosters-teams-list', 'rosters-solo-list', 'rosters-change-log', 'rosters-config-section'];

  let dashData = null;
  let searchQuery = '';
  let statusFilter = 'all';
  let gameIdLabel = 'Game ID';   // dynamic from backend
  let inflightPromise = null;
  let activeRequestId = 0;
  let lastFetchedAt = 0;
  let autoRefreshTimer = null;

  function isRostersTabActive() {
    return (window.location.hash || '').replace('#', '') === 'rosters';
  }

  function hasFreshCache() {
    return !!dashData && (Date.now() - lastFetchedAt) < CACHE_TTL_MS;
  }

  function formatTime(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function setSyncStatus(state, note) {
    const el = $('#rosters-sync-status');
    if (!el) return;
    if (state === 'loading') {
      el.className = 'text-[10px] font-mono text-dc-warning mt-1';
      el.textContent = note || 'Syncing rosters...';
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
    const el = $('#rosters-error-banner');
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
          <p class="text-xs font-bold text-white">Rosters request failed</p>
          <p class="text-[11px] text-dc-text mt-1">${esc(message)}</p>
          <button type="button" class="mt-2 px-2.5 py-1 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" data-click="TOC.rosters.refresh" data-click-args="[{&quot;force&quot;:true}]">Retry now</button>
        </div>
      </div>`;
    refreshIcons();
  }

  function setLoading(loading) {
    STAT_IDS.forEach((id) => {
      const el = $(`#rosters-stat-${id}`);
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

  function renderErrorEmpty(message) {
    const container = $('#rosters-teams-list');
    if (container) {
      container.innerHTML = `
        <div class="glass-box rounded-xl p-8 text-center">
          <p class="text-sm text-dc-danger">${esc(message || 'Failed to load rosters')}</p>
        </div>`;
    }
    setLoading(false);
  }

  function renderDashboard(data) {
    const safe = data && typeof data === 'object' ? data : {};
    gameIdLabel = safe.game_meta?.game_id_label || 'Game ID';
    renderAll(safe);
    setLoading(false);
    setErrorBanner('');
    setSyncStatus('ok');
  }

  /* ─────────────────────────── Data fetch ─────────────────────────── */

  async function refresh(options) {
    const opts = options || {};
    const force = opts.force === true;
    const silent = opts.silent === true;

    if (dashData && !force) {
      renderDashboard(dashData);
      if (hasFreshCache()) return dashData;
    }

    if (inflightPromise && !force) return inflightPromise;

    if (!silent) {
      setLoading(true);
      setSyncStatus('loading', dashData ? 'Refreshing rosters...' : 'Loading rosters...');
    }

    const requestId = ++activeRequestId;
    inflightPromise = (async () => {
      try {
        const data = await API.get('rosters/');
        if (requestId !== activeRequestId) return dashData || data;
        dashData = data;
        lastFetchedAt = Date.now();
        renderDashboard(data);
        return data;
      } catch (e) {
        if (requestId !== activeRequestId) return dashData;
        const detail = e && e.message ? String(e.message) : 'Request failed';
        console.error('[rosters] fetch error', e);
        if (dashData) {
          setLoading(false);
          setSyncStatus('error', `Using cached data (${detail})`);
          setErrorBanner(`Live refresh failed, showing cached rosters data. ${detail}`);
        } else {
          setSyncStatus('error', detail);
          setErrorBanner(detail);
          renderErrorEmpty('Failed to load rosters. Please refresh.');
        }
        return dashData;
      } finally {
        if (requestId === activeRequestId) inflightPromise = null;
      }
    })();

    return inflightPromise;
  }

  function invalidate() {
    lastFetchedAt = 0;
  }

  function startAutoRefresh() {
    stopAutoRefresh();
    if (window.TOC && TOC.isTerminalStatus && TOC.isTerminalStatus()) return;
    autoRefreshTimer = setInterval(() => {
      if (!isRostersTabActive()) return;
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
    if (e.detail?.tab === 'rosters') {
      refresh();
      startAutoRefresh();
      return;
    }
    stopAutoRefresh();
  }

  function onVisibilityChange() {
    if (!document.hidden && isRostersTabActive() && !hasFreshCache()) {
      refresh({ silent: true });
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
          <input id="rosters-search-input" type="text" placeholder="Search team, player, or ${gameIdLabel}…"
            class="w-full pl-8 pr-3 py-1.5 text-xs bg-dc-surface/60 border border-dc-border/50 rounded-lg text-white placeholder:text-dc-text/50 focus:outline-none focus:border-theme/50">
        </div>
        <div class="flex gap-1" id="rosters-filter-chips"></div>
      </div>`;
    refreshIcons();

    const input = $('#rosters-search-input');
    if (input) {
      input.addEventListener('input', () => {
        searchQuery = input.value.trim().toLowerCase();
        renderTeams(dashData?.teams || []);
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
      <button data-click="TOC.rosters._setFilter" data-click-args="['${c.key}']"
        class="rosters-chip text-[11px] px-3 py-1 rounded-full border transition-colors ${statusFilter === c.key
          ? 'bg-theme text-black border-theme font-semibold'
          : 'bg-transparent text-dc-text border-dc-border/50 hover:border-theme/50'}"
        data-filter="${c.key}">${esc(c.label)}</button>
    `).join('');
  }

  /* ────────────────────── Helpers: group players ──────────────────── */

  function groupPlayers(players) {
    const starters = [], subs = [], staff = [];
    for (const p of players) {
      const slot = (p.roster_slot || 'STARTER').toUpperCase();
      if (slot === 'SUBSTITUTE') subs.push(p);
      else if (slot === 'COACH' || slot === 'MANAGER') staff.push(p);
      else starters.push(p);
    }
    return { starters, subs, staff };
  }

  /* ─────────────────────────── Team cards ─────────────────────────── */

  function renderTeams(teams) {
    const container = $('#rosters-teams-list');
    if (!container) return;

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

    // Attach dropdown listeners
    container.querySelectorAll('[data-action-toggle]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const dd = btn.nextElementSibling;
        // Close all other open dropdowns
        container.querySelectorAll('.roster-action-dd.active').forEach(d => { if (d !== dd) d.classList.remove('active'); });
        dd?.classList.toggle('active');
      });
    });
    // Close dropdowns on outside click
    document.addEventListener('click', () => {
      container.querySelectorAll('.roster-action-dd.active').forEach(d => d.classList.remove('active'));
    }, { once: true });
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
      const nameHtml = p.profile_slug
        ? `<a href="/u/${esc(p.profile_slug)}/" class="text-white text-[11px] hover:text-theme transition-colors">${esc(p.display_name || p.username)}</a>`
        : `<span class="text-white text-[11px]">${esc(p.display_name || p.username)}</span>`;
      const gameIdHtml = p.game_id
        ? `<span class="font-mono text-[10px] text-emerald-300">${esc(p.game_id)}</span>`
        : `<span class="text-[10px] text-dc-text opacity-35 italic">—</span>`;
      return `
        <tr class="hover:bg-white/[.02] transition-colors">
          <td class="px-3 py-1.5">
            <div class="flex items-center gap-2">
              <span class="w-5 h-5 rounded-full bg-dc-surface/80 border border-dc-border/50 flex items-center justify-center text-[9px] font-bold text-dc-text">${esc(avatarLetter)}</span>
              ${nameHtml}
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
          <th class="text-left px-3 py-2 text-[10px] text-dc-text font-medium uppercase tracking-wide">${esc(gameIdLabel)}</th>
          <th class="text-right px-3 py-2 text-[10px] text-dc-text font-medium uppercase tracking-wide">Check-In</th>
        </tr></thead>
        <tbody class="divide-y divide-dc-border/20">${rows}</tbody>
      </table>`;
  }

  /* ─────────────────────── Build team card ─────────────────────── */

  function buildTeamCard(t) {
    const accentColor = t.primary_color || '';
    const accentVar = accentColor || 'var(--color-theme, #7c3aed)';
    const initials = (t.tag || t.team_name || '?').slice(0, 3).toUpperCase();
    const logoHtml = t.logo_url
      ? `<img src="${esc(t.logo_url)}" alt="" class="w-10 h-10 rounded-lg object-cover">`
      : `<div class="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold text-white"
            style="background:${accentVar}30; color:${accentVar}">${esc(initials)}</div>`;

    // ── Team name — clickable if slug exists ──
    const teamNameHtml = t.slug
      ? `<a href="/teams/${esc(t.slug)}/" class="text-sm font-bold text-white leading-tight truncate hover:text-theme transition-colors" target="_blank">${esc(t.team_name)}</a>`
      : `<p class="text-sm font-bold text-white leading-tight truncate">${esc(t.team_name)}</p>`;

    // ── Organization badge ──
    let orgBadgeHtml = '';
    if (t.organization && t.organization.name) {
      const orgLink = t.organization.slug ? `/orgs/${esc(t.organization.slug)}/` : '';
      const orgLogoHtml = t.organization.logo_url
        ? `<img src="${esc(t.organization.logo_url)}" alt="" class="w-3.5 h-3.5 rounded-sm object-cover">`
        : '';
      const verifiedIcon = t.organization.is_verified
        ? `<i data-lucide="badge-check" class="w-3 h-3 text-blue-400 shrink-0"></i>`
        : '';
      const orgInner = `${orgLogoHtml}<span>${esc(t.organization.name)}</span>${verifiedIcon}`;
      orgBadgeHtml = orgLink
        ? `<a href="${orgLink}" target="_blank" class="inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-theme/5 border border-theme/15 text-theme/80 hover:text-theme hover:border-theme/30 transition-colors">${orgInner}</a>`
        : `<span class="inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-theme/5 border border-theme/15 text-theme/80">${orgInner}</span>`;
    }

    // ── Status badges ──
    const validBadge = t.roster_valid
      ? `<span class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-dc-success/15 text-dc-success border border-dc-success/20">
           <i data-lucide="check" class="w-2.5 h-2.5"></i>Valid</span>`
      : `<span class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-dc-danger/15 text-dc-danger border border-dc-danger/20">
           <i data-lucide="alert-triangle" class="w-2.5 h-2.5"></i>Issues</span>`;

    const ignsOk = t.has_game_ids
      ? `<span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">IDs ✓</span>`
      : `<span class="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">IDs missing</span>`;

    const checkinBadge = t.checked_in
      ? `<span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">Checked In</span>`
      : '';

    // ── Coordinator / IGL info line ──
    let leaderLine = '';
    if (t.coordinator_name && t.coordinator_id !== t.captain_id) {
      // Show coordinator + IGL separately
      const coordLabel = (t.coordinator_role || 'Coordinator').replace(/_/g, ' ');
      leaderLine = `<p class="text-[10px] text-dc-text mt-0.5">
        <i data-lucide="shield" class="inline w-2.5 h-2.5 text-amber-400"></i>
        <span class="capitalize">${esc(coordLabel)}</span>: <span class="text-amber-400 font-medium">${esc(t.coordinator_name)}</span>`;
      if (t.captain_name) {
        leaderLine += ` · <i data-lucide="crown" class="inline w-2.5 h-2.5 text-theme"></i> IGL: <span class="text-theme font-medium">${esc(t.captain_name)}</span>`;
      }
      leaderLine += `</p>`;
    } else if (t.captain_name) {
      leaderLine = `<p class="text-[10px] text-dc-text mt-0.5">
        <i data-lucide="crown" class="inline w-2.5 h-2.5 text-theme"></i>
        IGL: <span class="text-theme font-medium">${esc(t.captain_name)}</span></p>`;
    }

    // ── Communication channels row ──
    const commChannels = t.communication_channels || {};
    const channelIcons = { discord: 'message-circle', whatsapp: 'phone', messenger: 'message-square', telegram: 'send', email: 'mail' };
    let commHtml = '';
    const channelEntries = Object.entries(commChannels).filter(([, v]) => v);
    if (channelEntries.length) {
      commHtml = `<div class="flex items-center gap-2 mt-1">`
        + channelEntries.map(([key, val]) => {
          const icon = channelIcons[key] || 'link';
          const isUrl = typeof val === 'string' && (val.startsWith('http') || val.startsWith('//'));
          return isUrl
            ? `<a href="${esc(val)}" target="_blank" class="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded bg-dc-surface/50 text-dc-text border border-dc-border/30 hover:border-theme/40 hover:text-theme transition-colors" title="${esc(key)}">
                <i data-lucide="${icon}" class="w-2.5 h-2.5"></i>${esc(key)}</a>`
            : `<span class="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded bg-dc-surface/50 text-dc-text border border-dc-border/30" title="${esc(String(val))}">
                <i data-lucide="${icon}" class="w-2.5 h-2.5"></i>${esc(key)}: ${esc(String(val))}</span>`;
        }).join('')
        + `</div>`;
    }

    // ── Team social links ──
    let socialHtml = '';
    const socialLinks = [];
    if (t.discord_invite_url) socialLinks.push(`<a href="${esc(t.discord_invite_url)}" target="_blank" class="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20 transition-colors inline-flex items-center gap-0.5"><i data-lucide="message-circle" class="w-2.5 h-2.5"></i>Discord</a>`);
    if (t.twitter_url) socialLinks.push(`<a href="${esc(t.twitter_url)}" target="_blank" class="text-[9px] px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 hover:bg-sky-500/20 transition-colors inline-flex items-center gap-0.5"><i data-lucide="twitter" class="w-2.5 h-2.5"></i>Twitter</a>`);
    if (t.website_url) socialLinks.push(`<a href="${esc(t.website_url)}" target="_blank" class="text-[9px] px-1.5 py-0.5 rounded bg-dc-surface/40 text-dc-text border border-dc-border/30 hover:border-theme/40 transition-colors inline-flex items-center gap-0.5"><i data-lucide="globe" class="w-2.5 h-2.5"></i>Website</a>`);
    if (socialLinks.length) {
      socialHtml = `<div class="flex items-center gap-1 mt-1">${socialLinks.join('')}</div>`;
    }

    // ── Player sections: grouped by role ──
    const groups = groupPlayers(t.players || []);
    let playerSections = '';

    if (groups.starters.length) {
      playerSections += buildPlayerSection('Starters', groups.starters, t, 'shield');
    }
    if (groups.subs.length) {
      playerSections += buildPlayerSection('Substitutes', groups.subs, t, 'repeat');
    }
    if (groups.staff.length) {
      playerSections += buildPlayerSection('Staff', groups.staff, t, 'briefcase');
    }
    if (!groups.starters.length && !groups.subs.length && !groups.staff.length) {
      playerSections = `<div class="px-4 py-6 text-center text-dc-text opacity-50 text-xs">No players in roster</div>`;
    }

    // ── Size chips ──
    const sizeInfo = `<span class="text-[10px] text-dc-text">
      ${t.starter_count || 0} starter${(t.starter_count || 0) !== 1 ? 's' : ''}${t.sub_count ? ` · ${t.sub_count} sub${t.sub_count !== 1 ? 's' : ''}` : ''}
    </span>`;

    return `
      <div class="glass-box rounded-xl border border-dc-border/50 overflow-hidden flex flex-col"
           style="${accentColor ? `border-left: 3px solid ${accentColor}; --team-accent: ${accentColor};` : ''}">
        <!-- Card header -->
        <div class="px-4 py-3 border-b border-dc-border/40">
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-center gap-3 min-w-0">
              ${logoHtml}
              <div class="min-w-0">
                ${teamNameHtml}
                <div class="flex items-center gap-2 flex-wrap">
                  ${t.tag ? `<span class="text-[10px] text-dc-text">[${esc(t.tag)}]</span>` : ''}
                  ${orgBadgeHtml}
                  ${sizeInfo}
                </div>
                ${leaderLine}
              </div>
            </div>
            <div class="flex flex-col items-end gap-1 shrink-0">
              ${validBadge}
              ${ignsOk}
              ${checkinBadge}
            </div>
          </div>
          ${commHtml}
          ${socialHtml}
        </div>

        <!-- Player sections -->
        <div class="flex-1 overflow-x-auto">
          ${playerSections}
        </div>

        <!-- Card footer -->
        <div class="px-4 py-2 border-t border-dc-border/30 flex items-center justify-between gap-2">
          <span class="text-[10px] text-dc-text opacity-60">${t.registered_at ? 'Reg: ' + new Date(t.registered_at).toLocaleDateString() : ''}</span>
          <div class="flex items-center gap-2">
            ${t.discord_invite_url ? `<a href="${esc(t.discord_invite_url)}" target="_blank" class="inline-flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300 transition-colors"><i data-lucide="send" class="w-3 h-3"></i>Message</a>` : ''}
            <button data-click="TOC.rosters.addPlayer" data-click-args="[${t.team_id}]"
              class="inline-flex items-center gap-1 text-[10px] text-theme hover:underline">
              <i data-lucide="user-plus" class="w-3 h-3"></i>Add Player
            </button>
          </div>
        </div>
      </div>`;
  }

  /* ────────────────── Player section (grouped table) ──────────────── */

  function buildPlayerSection(label, players, team, icon) {
    const rows = players.map(p => buildPlayerRow(team, p)).join('');
    return `
      <div class="border-b border-dc-border/20 last:border-b-0">
        <div class="flex items-center gap-1.5 px-3 py-1.5 bg-dc-surface/30">
          <i data-lucide="${icon}" class="w-3 h-3 text-dc-text opacity-60"></i>
          <span class="text-[10px] font-semibold text-dc-text uppercase tracking-wide">${esc(label)}</span>
          <span class="text-[10px] text-dc-text opacity-50">(${players.length})</span>
        </div>
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-dc-border/20">
              <th class="text-left px-3 py-1.5 text-[10px] text-dc-text font-medium uppercase tracking-wide">Player</th>
              <th class="text-left px-3 py-1.5 text-[10px] text-dc-text font-medium uppercase tracking-wide">Role</th>
              <th class="text-left px-3 py-1.5 text-[10px] text-dc-text font-medium uppercase tracking-wide">${esc(gameIdLabel)}</th>
              <th class="text-right px-3 py-1.5 text-[10px] text-dc-text font-medium uppercase tracking-wide w-16">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-dc-border/10">${rows}</tbody>
        </table>
      </div>`;
  }

  /* ────────────────────── Build player row ────────────────────────── */

  function buildPlayerRow(t, p) {
    // Role badge
    let roleBadge = '';
    if (p.is_igl) {
      roleBadge = `<span class="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded font-bold bg-theme/20 text-theme border border-theme/30">
        <i data-lucide="crown" class="w-2.5 h-2.5"></i>IGL</span>`;
    } else if (p.is_coordinator && !p.is_igl) {
      roleBadge = `<span class="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
        <i data-lucide="shield" class="w-2.5 h-2.5"></i>COORD</span>`;
    } else if ((p.roster_slot || '').toUpperCase() === 'SUBSTITUTE') {
      roleBadge = `<span class="text-[9px] px-1.5 py-0.5 rounded bg-slate-500/20 text-slate-400 border border-slate-500/20">SUB</span>`;
    } else if ((p.roster_slot || '').toUpperCase() === 'COACH') {
      roleBadge = `<span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/20">COACH</span>`;
    } else if ((p.roster_slot || '').toUpperCase() === 'MANAGER') {
      roleBadge = `<span class="text-[9px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-400 border border-violet-500/20">MGR</span>`;
    } else {
      roleBadge = `<span class="text-[9px] px-1.5 py-0.5 rounded bg-dc-surface/60 text-dc-text border border-dc-border/30">START</span>`;
    }

    // In-game role (Duelist, Controller, etc.)
    const roleLabel = p.player_role
      ? `<span class="ml-1 text-[9px] text-dc-text opacity-60">${esc(p.player_role)}</span>` : '';

    // Avatar
    const avatarLetter = (p.display_name || p.username || '?')[0].toUpperCase();
    const avatarHtml = p.avatar
      ? `<img src="${esc(p.avatar)}" alt="" class="w-5 h-5 rounded-full object-cover">`
      : `<span class="w-5 h-5 rounded-full bg-dc-surface/80 border border-dc-border/50 flex items-center justify-center text-[9px] font-bold text-dc-text">${esc(avatarLetter)}</span>`;

    // Player name — clickable if profile_slug
    const displayName = p.display_name || p.username || `User #${p.user_id}`;
    const nameHtml = p.profile_slug
      ? `<a href="/u/${esc(p.profile_slug)}/" class="text-white text-[11px] truncate max-w-[120px] hover:text-theme transition-colors" target="_blank">${esc(displayName)}</a>`
      : `<span class="text-white text-[11px] truncate max-w-[120px]">${esc(displayName)}</span>`;

    // Game ID
    const gameIdHtml = p.game_id
      ? `<span class="font-mono text-[10px] text-emerald-300">${esc(p.game_id)}</span>`
      : `<span class="text-[10px] text-dc-text opacity-35 italic">—</span>`;

    // Check-in dot
    const ciDot = p.checked_in
      ? `<span class="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" title="Checked in"></span>` : '';

    // Actions dropdown
    const uid = p.user_id ?? 0;
    const profileItem = p.profile_slug
      ? `<a href="/u/${esc(p.profile_slug)}/" target="_blank" class="block w-full text-left px-3 py-1.5 text-[10px] text-dc-text hover:bg-white/[.04] hover:text-white transition-colors"><i data-lucide="user" class="inline w-3 h-3 mr-1 opacity-60"></i>View Profile</a>` : '';
    const setIglItem = !p.is_igl
      ? `<button data-click="TOC.rosters.setCaptain" data-click-args="[${t.team_id}, ${uid}]" class="block w-full text-left px-3 py-1.5 text-[10px] text-dc-text hover:bg-white/[.04] hover:text-theme transition-colors"><i data-lucide="crown" class="inline w-3 h-3 mr-1 opacity-60"></i>Set as IGL</button>` : '';
    const removeItem = `<button data-click="TOC.rosters.removePlayer" data-click-args="[${t.team_id}, ${uid}]" class="block w-full text-left px-3 py-1.5 text-[10px] text-dc-danger hover:bg-white/[.04] transition-colors"><i data-lucide="user-minus" class="inline w-3 h-3 mr-1 opacity-60"></i>Remove</button>`;

    return `
      <tr class="hover:bg-white/[.02] transition-colors group">
        <td class="px-3 py-1.5">
          <div class="flex items-center gap-1.5">
            ${avatarHtml}
            ${nameHtml}
            ${ciDot}
          </div>
        </td>
        <td class="px-3 py-1.5">
          <div class="flex items-center gap-1">${roleBadge}${roleLabel}</div>
        </td>
        <td class="px-3 py-1.5">${gameIdHtml}</td>
        <td class="px-3 py-1.5 text-right">
          <div class="relative inline-block">
            <button data-action-toggle class="p-0.5 rounded hover:bg-white/[.06] text-dc-text opacity-0 group-hover:opacity-100 transition-all">
              <i data-lucide="more-vertical" class="w-3.5 h-3.5"></i>
            </button>
            <div class="roster-action-dd hidden absolute right-0 top-full mt-1 w-36 bg-dc-surface border border-dc-border/50 rounded-lg shadow-xl z-50 py-1 overflow-hidden">
              ${profileItem}${setIglItem}${removeItem}
            </div>
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

  function lockRosters() {
    TOC.dangerConfirm({
      title: 'Lock All Rosters',
      message: 'Players will no longer be able to join or leave any team. This cannot be undone without admin action.',
      confirmText: 'Lock Rosters',
      variant: 'warning',
      onConfirm: async function () {
        try { await API.post('rosters/lock/', {}); toast('Rosters locked', 'warning'); invalidate(); refresh({ force: true }); }
        catch { toast('Failed to lock', 'error'); }
      },
    });
  }

  async function unlockRosters() {
    try { await API.post('rosters/unlock/', {}); toast('Rosters unlocked', 'success'); invalidate(); refresh({ force: true }); }
    catch { toast('Failed to unlock', 'error'); }
  }

  async function setCaptain(teamId, userId) {
    if (!userId) { toast('No user ID', 'error'); return; }
    try { await API.post('rosters/captain/', { team_id: teamId, user_id: userId }); toast('IGL updated', 'success'); invalidate(); refresh({ force: true }); }
    catch { toast('Failed', 'error'); }
  }

  async function removePlayer(teamId, userId) {
    if (!confirm('Remove this player from the roster?')) return;
    try { await API.post('rosters/remove-player/', { team_id: teamId, user_id: userId }); toast('Player removed', 'success'); invalidate(); refresh({ force: true }); }
    catch { toast('Failed', 'error'); }
  }

  function addPlayer(teamId) {
    const FIELD = 'w-full bg-dc-surface/50 border border-dc-border/50 rounded-lg px-3 py-2 text-sm text-white placeholder-dc-text/40 focus:outline-none focus:border-theme';
    const body = `<div class="space-y-4 p-5">
      <div>
        <label class="block text-[10px] text-dc-text uppercase tracking-widest mb-1">User ID *</label>
        <input id="roster-add-uid" type="number" class="${FIELD}" placeholder="Numeric user ID"></div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button data-click="TOC.rosters._submitAddPlayer" data-click-args="[${teamId}]" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Add Player</button>
      <button data-click="TOC.drawer.close" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Add Player to Roster', body, footer);
    setTimeout(() => document.getElementById('roster-add-uid')?.focus(), 50);
  }

  function _submitAddPlayer(teamId) {
    const userId = parseInt(document.getElementById('roster-add-uid')?.value || '');
    if (!userId || isNaN(userId)) { toast('Valid user ID is required', 'error'); return; }
    API.post('rosters/add-player/', { team_id: teamId, user_id: userId })
      .then(() => { toast('Player added', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
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
    try { await API.post('rosters/config/', data); toast('Config saved', 'success'); invalidate(); refresh({ force: true }); }
    catch { toast('Save failed', 'error'); }
  }

  function _setFilter(key) {
    statusFilter = key;
    renderFilterChips();
    renderTeams(dashData?.teams || []);
  }

  /* ─────────────────────────── Public API ─────────────────────────── */

  window.TOC = window.TOC || {};
  window.TOC.rosters = {
    refresh, lockRosters, unlockRosters,
    setCaptain, removePlayer, addPlayer, _submitAddPlayer,
    checkEligibility, saveConfig,
    invalidate,
    _setFilter,
  };

  document.addEventListener('toc:tab-changed', onTabChange);
  document.addEventListener('visibilitychange', onVisibilityChange);

  if (isRostersTabActive()) {
    refresh();
    startAutoRefresh();
  }

  /* ── Dropdown CSS (injected once) ── */
  const style = document.createElement('style');
  style.textContent = `.roster-action-dd.active { display: block !important; }`;
  document.head.appendChild(style);
})();
