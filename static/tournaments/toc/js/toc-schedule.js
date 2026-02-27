/**
 * TOC Schedule Module — Sprint 5
 * Match schedule timeline, auto-scheduling, bulk shift, break insertion.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);

  const matchStates = {
    scheduled: { label: 'Scheduled', color: 'bg-dc-info/20 text-dc-info border-dc-info/30' },
    check_in_open: { label: 'Check-in', color: 'bg-dc-warning/20 text-dc-warning border-dc-warning/30' },
    live: { label: 'Live', color: 'bg-dc-success/20 text-dc-success border-dc-success/30' },
    pending_result: { label: 'Pending', color: 'bg-dc-warning/20 text-dc-warning border-dc-warning/30' },
    completed: { label: 'Done', color: 'bg-dc-text/10 text-dc-text border-dc-border' },
    disputed: { label: 'Disputed', color: 'bg-dc-danger/20 text-dc-danger border-dc-danger/30' },
    cancelled: { label: 'Cancel', color: 'bg-dc-danger/10 text-dc-text/50 border-dc-border' },
    forfeit: { label: 'Forfeit', color: 'bg-dc-danger/10 text-dc-danger/60 border-dc-danger/20' },
    break: { label: 'Break', color: 'bg-dc-panel text-dc-text border-dc-border' },
  };

  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }

  /* ─── State ──────────────────────────────────────────────── */
  let scheduleData = null;

  async function refresh() {
    try {
      const data = await API.get('schedule/');
      scheduleData = data;
      renderSchedule(data);
      renderStats(data);
    } catch (e) {
      console.error('[schedule] fetch error', e);
    }
  }

  /* ─── Stats rendering ───────────────────────────────────── */
  function renderStats(data) {
    const roundsRaw = data.rounds || [];
    const matches = Array.isArray(roundsRaw)
      ? roundsRaw.flatMap(r => r.matches || [])
      : Object.values(roundsRaw).flat();
    const total = matches.length;
    const scheduled = matches.filter(m => m.state === 'scheduled' || m.state === 'check_in_open').length;
    const inProgress = matches.filter(m => m.state === 'live').length;
    const completed = matches.filter(m => m.state === 'completed' || m.state === 'forfeit').length;

    const el = (id, val) => { const e = $(`#${id}`); if (e) e.textContent = val; };
    el('sched-total-matches', total);
    el('sched-scheduled', scheduled);
    el('sched-live', inProgress);
    el('sched-completed', completed);
  }

  /* ─── Timeline rendering ─────────────────────────────────── */
  function renderSchedule(data) {
    const container = $('#schedule-timeline');
    if (!container) return;

    const roundsRaw = data.rounds || [];
    // API returns [{round, matches}, ...] — convert to dict keyed by round number
    const rounds = {};
    if (Array.isArray(roundsRaw)) {
      roundsRaw.forEach(r => { rounds[r.round] = r.matches || []; });
    } else {
      Object.assign(rounds, roundsRaw);
    }
    const roundKeys = Object.keys(rounds).sort((a, b) => parseInt(a) - parseInt(b));

    if (!roundKeys.length) {
      container.innerHTML = `
        <div class="flex items-center justify-center h-60 text-dc-text text-sm">
          <div class="text-center">
            <i data-lucide="calendar" class="w-12 h-12 text-dc-text/20 mx-auto mb-3"></i>
            <p>No matches scheduled</p>
            <p class="text-[10px] mt-1 text-dc-text/60">Generate a bracket first, then use Auto-Schedule</p>
          </div>
        </div>`;
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    container.innerHTML = roundKeys.map(rn => {
      const matches = rounds[rn];
      return `
        <div class="mb-6">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-8 h-8 rounded-lg bg-theme/10 flex items-center justify-center">
              <span class="text-[10px] font-mono font-black text-theme">R${rn}</span>
            </div>
            <h4 class="text-xs font-bold text-white uppercase tracking-widest">Round ${rn}</h4>
            <span class="text-[9px] text-dc-text font-mono">${matches.length} match${matches.length === 1 ? '' : 'es'}</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2 pl-11">
            ${matches.map(m => renderScheduleCard(m)).join('')}
          </div>
        </div>`;
    }).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function renderScheduleCard(m) {
    const stateInfo = matchStates[m.state] || matchStates.scheduled;
    const scheduledAt = m.scheduled_time ? formatTime(m.scheduled_time) : '—';

    return `
      <div class="bg-dc-bg border border-dc-border rounded-lg p-3 hover:border-dc-borderLight transition-colors">
        <div class="flex items-center justify-between mb-2">
          <span class="text-[10px] font-mono text-dc-text">Match #${m.match_number || '—'}</span>
          <span class="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${stateInfo.color}">${stateInfo.label}</span>
        </div>
        <div class="space-y-1 mb-2">
          <div class="flex items-center justify-between">
            <span class="text-xs text-dc-textBright font-semibold truncate max-w-[140px]">${m.participant1_name || 'TBD'}</span>
            <span class="text-xs font-mono font-bold ${m.winner === 'p1' ? 'text-dc-success' : 'text-dc-text'}">${m.participant1_score ?? '—'}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-xs text-dc-textBright font-semibold truncate max-w-[140px]">${m.participant2_name || 'TBD'}</span>
            <span class="text-xs font-mono font-bold ${m.winner === 'p2' ? 'text-dc-success' : 'text-dc-text'}">${m.participant2_score ?? '—'}</span>
          </div>
        </div>
        <div class="flex items-center gap-2 text-[9px] text-dc-text">
          <i data-lucide="clock" class="w-3 h-3"></i>
          <span>${scheduledAt}</span>
        </div>
      </div>`;
  }

  function formatTime(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
  }

  /* ─── Auto-schedule (S5-F6) ─────────────────────────────── */
  function openAutoSchedule() {
    const html = `
      <div class="p-6 space-y-4">
        <h3 class="font-display font-black text-lg text-white">Auto-Schedule</h3>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Start Date & Time</label>
          <input id="as-start" type="datetime-local" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Match Duration (min)</label>
            <input id="as-duration" type="number" value="60" min="5" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Break Between (min)</label>
            <input id="as-break" type="number" value="15" min="0" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
          </div>
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Concurrent Matches</label>
          <input id="as-concurrent" type="number" value="1" min="1" max="32" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
        </div>
        <button onclick="TOC.schedule.confirmAutoSchedule()" class="w-full py-2.5 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Generate Schedule</button>
      </div>`;
    showOverlay('auto-schedule-overlay', html);
  }

  async function confirmAutoSchedule() {
    const startVal = $('#as-start')?.value;
    if (!startVal) { toast('Start time required', 'error'); return; }
    try {
      await API.post('schedule/auto-generate/', {
        start_time: new Date(startVal).toISOString(),
        match_duration_minutes: parseInt($('#as-duration')?.value) || 60,
        break_minutes: parseInt($('#as-break')?.value) || 15,
        max_concurrent: parseInt($('#as-concurrent')?.value) || 1,
      });
      toast('Schedule generated', 'success');
      closeOverlay('auto-schedule-overlay');
      refresh();
    } catch (e) {
      toast(e.message || 'Scheduling failed', 'error');
    }
  }

  /* ─── Bulk shift ─────────────────────────────────────────── */
  function openBulkShift() {
    const html = `
      <div class="p-6 space-y-4">
        <h3 class="font-display font-black text-lg text-white">Bulk Shift Schedule</h3>
        <p class="text-[10px] text-dc-text">Shift all (or selected round) matches forward or backward in time.</p>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Minutes</label>
            <input id="bs-minutes" type="number" value="30" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Round (blank = all)</label>
            <input id="bs-round" type="number" min="1" placeholder="All" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
          </div>
        </div>
        <button onclick="TOC.schedule.confirmBulkShift()" class="w-full py-2.5 bg-dc-warning text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Apply Shift</button>
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
      await API.post('schedule/bulk-shift/', payload);
      toast(`Shifted ${minutes > 0 ? '+' : ''}${minutes} min`, 'success');
      closeOverlay('bulk-shift-overlay');
      refresh();
    } catch (e) {
      toast(e.message || 'Shift failed', 'error');
    }
  }

  /* ─── Add break ──────────────────────────────────────────── */
  function openAddBreak() {
    const html = `
      <div class="p-6 space-y-4">
        <h3 class="font-display font-black text-lg text-white">Insert Break</h3>
        <p class="text-[10px] text-dc-text">Insert a break after a specific round. Matches after will shift forward.</p>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">After Round</label>
            <input id="ab-round" type="number" value="1" min="1" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Duration (min)</label>
            <input id="ab-minutes" type="number" value="30" min="5" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
          </div>
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Label</label>
          <input id="ab-label" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none" value="Break" placeholder="e.g. Lunch Break">
        </div>
        <button onclick="TOC.schedule.confirmAddBreak()" class="w-full py-2.5 bg-purple-600 text-white text-xs font-black uppercase tracking-widest rounded-lg hover:bg-purple-500 transition-colors">Insert Break</button>
      </div>`;
    showOverlay('add-break-overlay', html);
  }

  async function confirmAddBreak() {
    try {
      await API.post('schedule/add-break/', {
        after_round: parseInt($('#ab-round')?.value) || 1,
        break_minutes: parseInt($('#ab-minutes')?.value) || 30,
        label: $('#ab-label')?.value?.trim() || 'Break',
      });
      toast('Break inserted', 'success');
      closeOverlay('add-break-overlay');
      refresh();
    } catch (e) {
      toast(e.message || 'Failed to insert break', 'error');
    }
  }

  /* ─── Overlay helpers ────────────────────────────────────── */
  function showOverlay(id, innerHtml) {
    const existing = document.getElementById(id);
    if (existing) existing.remove();
    const modal = document.createElement('div');
    modal.id = id;
    modal.className = 'fixed inset-0 z-[110] flex items-center justify-center';
    modal.innerHTML = `
      <div class="absolute inset-0 bg-black/80 backdrop-blur-md" onclick="TOC.schedule.closeOverlay('${id}')"></div>
      <div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-md relative z-10 overflow-hidden">
        <div class="h-1 w-full bg-theme"></div>
        ${innerHtml}
      </div>`;
    document.body.appendChild(modal);
  }

  function closeOverlay(id) {
    document.getElementById(id)?.remove();
  }

  /* ─── Init ───────────────────────────────────────────────── */
  function init() { refresh(); }

  window.TOC = window.TOC || {};
  window.TOC.schedule = {
    init, refresh,
    openAutoSchedule, confirmAutoSchedule,
    openBulkShift, confirmBulkShift,
    openAddBreak, confirmAddBreak,
    closeOverlay,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'schedule') init();
  });
})();
