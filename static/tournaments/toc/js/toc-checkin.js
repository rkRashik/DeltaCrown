/**
 * TOC Check-in Module — Sprint 29 (full redesign)
 *
 * Features:
 * - Progress ring with animated percentage
 * - Live countdown timer to deadline
 * - Enriched participant cards (team logos, player counts, colors)
 * - Search + filter chips (Checked In / Pending / All)
 * - Bulk force check-in
 * - Per-round match check-in display
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
  let allParticipants = [];
  let searchQuery = '';
  let filterMode = 'all';   // 'all' | 'checked' | 'pending'
  let countdownInterval = null;

  /* ─────────────────────────── Data fetch ─────────────────────────── */

  async function refresh() {
    try {
      const data = await API.get('checkin/');
      dashData = data;
      allParticipants = data.participants || [];
      renderAll(data);
    } catch (e) {
      console.error('[checkin] fetch error', e);
    }
  }

  function renderAll(data) {
    renderStats(data);
    renderConfig(data.config || {});
    renderProgressRing(data.summary || {});
    renderCountdown(data.summary || {}, data.config || {});
    renderFilterBar();
    renderParticipants(allParticipants);
    renderRoundCheckin(data.round_checkin || []);
    updateStatusButtons(data.config || {});
  }

  /* ─────────────────────────── Stats bar ──────────────────────────── */

  function renderStats(data) {
    const s = data.summary || {};
    const el = (id, v) => { const e = $(`#checkin-stat-${id}`); if (e) e.textContent = v; };
    el('checked', s.checked_in || 0);
    el('pending', s.pending || 0);
    el('missing', s.not_checked_in || 0);
    el('total', s.total || 0);
    if (data.config?.checkin_required === false) {
      el('status', 'Not Required');
    } else {
      el('status', data.config?.open ? 'Open' : 'Closed');
    }
  }

  /* ─────────────────────── Progress ring ──────────────────────────── */

  function renderProgressRing(summary) {
    const container = $('#checkin-progress-ring');
    if (!container) return;

    const pct = summary.pct || 0;
    const radius = 44;
    const circ = 2 * Math.PI * radius;
    const offset = circ - (pct / 100) * circ;
    const color = pct >= 80 ? 'var(--color-dc-success, #22c55e)' : pct >= 50 ? 'var(--color-dc-warning, #f59e0b)' : 'var(--color-dc-danger, #ef4444)';

    container.innerHTML = `
      <div class="flex items-center gap-4">
        <svg viewBox="0 0 100 100" class="w-20 h-20 shrink-0 -rotate-90">
          <circle cx="50" cy="50" r="${radius}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="8"/>
          <circle cx="50" cy="50" r="${radius}" fill="none" stroke="${color}" stroke-width="8"
            stroke-dasharray="${circ}" stroke-dashoffset="${offset}" stroke-linecap="round"
            class="transition-all duration-700"/>
        </svg>
        <div>
          <div class="text-2xl font-bold text-white">${pct}%</div>
          <div class="text-[11px] text-dc-text">${summary.checked_in || 0} / ${summary.total || 0} checked in</div>
        </div>
      </div>`;
  }

  /* ─────────────────────── Countdown timer ────────────────────────── */

  function renderCountdown(summary, config) {
    const container = $('#checkin-countdown');
    if (!container) return;

    if (countdownInterval) { clearInterval(countdownInterval); countdownInterval = null; }

    const rem = summary.time_remaining;
    if (!config.open || !rem || rem <= 0) {
      container.innerHTML = config.open
        ? `<div class="text-xs text-dc-warning">Check-in open · no deadline set</div>`
        : `<div class="text-xs text-dc-text opacity-50">Check-in closed</div>`;
      return;
    }

    let secondsLeft = rem;
    function tick() {
      if (secondsLeft <= 0) {
        container.innerHTML = `<div class="text-xs text-dc-danger font-bold">⏰ Deadline passed</div>`;
        clearInterval(countdownInterval);
        return;
      }
      const m = Math.floor(secondsLeft / 60);
      const s = secondsLeft % 60;
      container.innerHTML = `
        <div class="flex items-center gap-2">
          <i data-lucide="clock" class="w-4 h-4 text-dc-warning"></i>
          <span class="text-sm font-bold text-white font-mono">${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}</span>
          <span class="text-[10px] text-dc-text">remaining</span>
        </div>`;
      refreshIcons();
      secondsLeft--;
    }
    tick();
    countdownInterval = setInterval(tick, 1000);
  }

  /* ─────────────────────── Status buttons ─────────────────────────── */

  function updateStatusButtons(config) {
    const openBtn = $('[data-checkin-action="open"]');
    const closeBtn = $('[data-checkin-action="close"]');
    const required = config.checkin_required !== false;
    if (!required) {
      openBtn?.classList.add('opacity-50', 'pointer-events-none');
      closeBtn?.classList.add('opacity-50', 'pointer-events-none');
      return;
    }
    if (config.open) {
      openBtn?.classList.add('opacity-50', 'pointer-events-none');
      closeBtn?.classList.remove('opacity-50', 'pointer-events-none');
    } else {
      openBtn?.classList.remove('opacity-50', 'pointer-events-none');
      closeBtn?.classList.add('opacity-50', 'pointer-events-none');
    }
  }

  /* ─────────────────── Search + filter bar ─────────────────────────── */

  function renderFilterBar() {
    const bar = $('#checkin-filter-bar');
    if (!bar || bar.dataset.initialized) return;
    bar.dataset.initialized = '1';
    bar.innerHTML = `
      <div class="flex flex-wrap gap-2 items-center">
        <div class="relative flex-1 min-w-[180px]">
          <i data-lucide="search" class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-dc-text pointer-events-none"></i>
          <input id="checkin-search-input" type="text" placeholder="Search team or player…"
            class="w-full pl-8 pr-3 py-1.5 text-xs bg-dc-surface/60 border border-dc-border/50 rounded-lg text-white placeholder:text-dc-text/50 focus:outline-none focus:border-theme/50">
        </div>
        <div class="flex gap-1" id="checkin-filter-chips"></div>
      </div>`;
    refreshIcons();

    const input = $('#checkin-search-input');
    if (input) {
      input.addEventListener('input', () => {
        searchQuery = input.value.trim().toLowerCase();
        renderParticipants(allParticipants);
      });
    }
    renderFilterChips();
  }

  function renderFilterChips() {
    const wrap = $('#checkin-filter-chips');
    if (!wrap) return;
    const chips = [
      { key: 'all', label: 'All' },
      { key: 'checked', label: 'Checked In' },
      { key: 'pending', label: 'Pending' },
    ];
    wrap.innerHTML = chips.map(c => `
      <button onclick="TOC.checkin._setFilter('${c.key}')"
        class="text-[11px] px-3 py-1 rounded-full border transition-colors ${filterMode === c.key
          ? 'bg-theme text-black border-theme font-semibold'
          : 'bg-transparent text-dc-text border-dc-border/50 hover:border-theme/50'}">${esc(c.label)}</button>
    `).join('');
  }

  /* ──────────────────── Participants list ──────────────────────────── */

  function renderParticipants(participants) {
    const container = $('#checkin-participants-list');
    if (!container) return;

    // Filter
    let filtered = participants;
    if (searchQuery) {
      filtered = filtered.filter(p =>
        (p.display_name || '').toLowerCase().includes(searchQuery)
        || (p.username || '').toLowerCase().includes(searchQuery)
        || (p.team_name || '').toLowerCase().includes(searchQuery)
      );
    }
    if (filterMode === 'checked') filtered = filtered.filter(p => p.checked_in);
    if (filterMode === 'pending') filtered = filtered.filter(p => !p.checked_in);

    if (!filtered.length) {
      container.innerHTML = `<p class="text-xs text-dc-text text-center py-8 opacity-50">${searchQuery || filterMode !== 'all' ? 'No matches' : 'No participants'}</p>`;
      return;
    }

    container.innerHTML = filtered.map(p => buildParticipantCard(p)).join('');
    refreshIcons();
  }

  function buildParticipantCard(p) {
    const checked = p.checked_in;
    const isTeam = !!p.team_id;
    const accentColor = p.team_color || '';

    // Avatar/logo
    let avatarHtml;
    if (isTeam && p.team_logo) {
      avatarHtml = `<img src="${esc(p.team_logo)}" alt="" class="w-9 h-9 rounded-lg object-cover">`;
    } else {
      const initial = (p.display_name || p.username || '?')[0].toUpperCase();
      const bgColor = accentColor || 'var(--color-theme, #7c3aed)';
      avatarHtml = `<div class="w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold"
        style="background:${bgColor}20; color:${bgColor}">${esc(initial)}</div>`;
    }

    // Name with link
    const nameText = esc(p.display_name || p.username);
    const nameHtml = isTeam && p.team_slug
      ? `<a href="/teams/${esc(p.team_slug)}/" class="text-sm text-white font-medium hover:text-theme transition-colors" target="_blank">${nameText}</a>`
      : `<span class="text-sm text-white font-medium">${nameText}</span>`;

    // Subtitle
    let subtitle = '';
    if (isTeam) {
      subtitle = `<span class="text-[10px] text-dc-text">${p.team_tag ? `[${esc(p.team_tag)}]` : 'Team'}${p.player_count ? ` · ${p.player_count} players` : ''}</span>`;
    } else {
      subtitle = `<span class="text-[10px] text-dc-text">Solo</span>`;
    }

    // Checked-in time
    const timeStr = checked && p.checked_in_at
      ? `<span class="text-[9px] text-dc-text opacity-60">${new Date(p.checked_in_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>`
      : '';

    // Status badge
    const statusBadge = checked
      ? `<span class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-dc-success/15 text-dc-success border border-dc-success/20">
           <i data-lucide="check-circle" class="w-2.5 h-2.5"></i>Checked In</span>`
      : `<span class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-dc-warning/15 text-dc-warning border border-dc-warning/20">
           <i data-lucide="clock" class="w-2.5 h-2.5"></i>Pending</span>`;

    // Force button
    const forceBtn = !checked
      ? `<button onclick="TOC.checkin.forceCheckin(${p.id})" class="text-[10px] px-2 py-1 rounded bg-theme/10 text-theme border border-theme/20 hover:bg-theme/20 transition-colors">Force Check-in</button>`
      : '';

    return `
      <div class="flex items-center justify-between p-3 rounded-lg border transition-colors
        ${checked ? 'bg-dc-success/[.03] border-dc-success/15' : 'bg-dc-surface/50 border-dc-border/50 hover:border-dc-border'}"
        ${accentColor && !checked ? `style="border-left: 3px solid ${accentColor};"` : ''}>
        <div class="flex items-center gap-3 min-w-0">
          ${avatarHtml}
          <div class="min-w-0">
            ${nameHtml}
            <div class="flex items-center gap-2">${subtitle}${timeStr}</div>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          ${statusBadge}
          ${forceBtn}
        </div>
      </div>`;
  }

  /* ─────────────────── Round check-in matches ─────────────────────── */

  function renderRoundCheckin(matches) {
    const container = $('#checkin-round-matches');
    if (!container) return;
    if (!matches.length) {
      container.classList.add('hidden');
      return;
    }
    container.classList.remove('hidden');
    const matchCards = matches.map(m => {
      const p1Ok = m.p1_checked_in;
      const p2Ok = m.p2_checked_in;
      return `
        <div class="flex items-center gap-3 p-3 bg-dc-surface/50 rounded-lg border border-dc-border/50">
          <span class="text-[10px] text-dc-text opacity-60 w-8 shrink-0">M${m.match_number || m.match_id}</span>
          <div class="flex-1 flex items-center gap-2 justify-between">
            <div class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full ${p1Ok ? 'bg-dc-success' : 'bg-dc-warning'}"></span>
              <span class="text-xs text-white">${esc(m.p1_name)}</span>
              ${!p1Ok ? `<button onclick="TOC.checkin.forceMatchCheckin(${m.match_id},'p1')" class="text-[9px] text-theme hover:underline ml-1">Force</button>` : ''}
            </div>
            <span class="text-[10px] text-dc-text">vs</span>
            <div class="flex items-center gap-1.5">
              ${!p2Ok ? `<button onclick="TOC.checkin.forceMatchCheckin(${m.match_id},'p2')" class="text-[9px] text-theme hover:underline mr-1">Force</button>` : ''}
              <span class="text-xs text-white">${esc(m.p2_name)}</span>
              <span class="w-2 h-2 rounded-full ${p2Ok ? 'bg-dc-success' : 'bg-dc-warning'}"></span>
            </div>
          </div>
        </div>`;
    }).join('');

    container.innerHTML = `
      <h4 class="text-xs font-semibold text-dc-text uppercase tracking-wide mb-2">Round Check-in</h4>
      <div class="space-y-1.5">${matchCards}</div>`;
    refreshIcons();
  }

  /* ─────────────────────────── Config form ─────────────────────────── */

  function renderConfig(config) {
    const required = $('#checkin-required-toggle');
    const wm = $('#checkin-window-minutes');
    const closes = $('#checkin-closes-minutes-before');
    const adq = $('#checkin-auto-dq');
    const pr = $('#checkin-per-round');
    const note = $('#checkin-required-note');
    if (required) required.checked = config.checkin_required !== false;
    if (wm) wm.value = config.window_minutes || 15;
    if (closes) closes.value = config.check_in_closes_minutes_before || 0;
    if (adq) adq.checked = !!config.auto_dq;
    if (pr) pr.checked = !!config.per_round;
    if (note) {
      note.textContent = config.checkin_required === false
        ? 'Check-in is currently disabled in tournament settings.'
        : 'Check-in is required. Configure runtime behavior below.';
      note.className = config.checkin_required === false
        ? 'text-[10px] font-mono text-dc-warning mt-1'
        : 'text-[10px] font-mono text-dc-text mt-1';
    }
  }

  /* ─────────────────────────── Actions ────────────────────────────── */

  async function openCheckin() {
    if (dashData?.config?.checkin_required === false) {
      toast('Enable Check-In Required first in config/settings.', 'warning');
      return;
    }
    const mins = parseInt($('#checkin-window-minutes')?.value || '15');
    try {
      await API.post('checkin/open/', { window_minutes: mins });
      toast('Check-in opened', 'success');
      refresh();
    } catch (e) {
      toast('Failed to open check-in', 'error');
    }
  }

  async function closeCheckin() {
    try {
      await API.post('checkin/close/', {});
      toast('Check-in closed', 'success');
      refresh();
    } catch (e) {
      toast('Failed to close check-in', 'error');
    }
  }

  async function forceCheckin(participantId) {
    try {
      await API.post('checkin/force/', { participant_id: participantId });
      toast('Participant checked in', 'success');
      refresh();
    } catch (e) {
      toast('Force check-in failed', 'error');
    }
  }

  async function forceMatchCheckin(matchId, side) {
    try {
      await API.post('checkin/force-match/', { match_id: matchId, side });
      toast(`${side.toUpperCase()} checked in`, 'success');
      refresh();
    } catch (e) {
      toast('Force check-in failed', 'error');
    }
  }

  function autoDQ() {
    TOC.dangerConfirm({
      title: 'Auto-Disqualify No-Shows',
      message: 'All participants who have not checked in will be disqualified. This action is immediate.',
      confirmText: 'Auto-DQ Now',
      onConfirm: async function () {
        try {
          const res = await API.post('checkin/auto-dq/', {});
          toast(`${res.dq_count || 0} participants disqualified`, 'warning');
          refresh();
        } catch (e) {
          toast('Auto-DQ failed', 'error');
        }
      },
    });
  }

  function blastReminder() {
    TOC.dangerConfirm({
      title: 'Send Check-in Reminder',
      message: 'A notification will be sent to all participants who have not yet checked in.',
      confirmText: 'Send Reminder',
      variant: 'warning',
      onConfirm: async function () {
        try {
          const res = await API.post('checkin/blast-reminder/', {});
          toast(res.message || `Reminder sent to ${res.sent} participants`, 'success');
        } catch (e) {
          toast('Blast reminder failed', 'error');
        }
      },
    });
  }

  async function saveConfig() {
    const data = {
      checkin_required: $('#checkin-required-toggle')?.checked !== false,
      window_minutes: parseInt($('#checkin-window-minutes')?.value || '15'),
      check_in_closes_minutes_before: parseInt($('#checkin-closes-minutes-before')?.value || '0'),
      auto_dq: $('#checkin-auto-dq')?.checked || false,
      per_round: $('#checkin-per-round')?.checked || false,
    };
    try {
      const res = await API.post('checkin/config/', data);
      document.dispatchEvent(new CustomEvent('toc:checkin-config-updated', { detail: res?.config || data }));
      toast('Config saved', 'success');
      refresh();
    } catch (e) {
      toast('Save failed', 'error');
    }
  }

  function _setFilter(key) {
    filterMode = key;
    renderFilterChips();
    renderParticipants(allParticipants);
  }

  // Legacy compat — called from the old search input in HTML
  function filterParticipants(query) {
    searchQuery = (query || '').toLowerCase();
    renderParticipants(allParticipants);
  }

  /* ─────────────────────────── Public API ─────────────────────────── */

  window.TOC = window.TOC || {};
  window.TOC.checkin = {
    refresh, openCheckin, closeCheckin,
    forceCheckin, forceMatchCheckin,
    autoDQ, blastReminder, saveConfig, filterParticipants,
    _setFilter,
  };

  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail?.tab === 'checkin') refresh();
  });

  document.addEventListener('toc:checkin-config-updated', () => {
    if ((window.location.hash || '').replace('#', '') === 'checkin') {
      refresh();
    }
  });
})();
