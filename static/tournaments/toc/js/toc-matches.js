/**
 * TOC Matches Module — Sprint 6
 * Match grid, scoring, Match Medic (live/pause/resume/force-complete),
 * reschedule, forfeit, notes, media, broadcast stations.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);

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

  let allMatches = [];
  let _debounceTimer = null;

  /* ─── Fetch & render ─────────────────────────────────────── */
  async function refresh() {
    const state = $('#match-filter-state')?.value || '';
    const round = $('#match-filter-round')?.value || '';
    const search = $('#match-search')?.value || '';
    try {
      const data = await API.get(`/api/toc/${slug}/matches/` +
        `?state=${state}&round=${round}&search=${encodeURIComponent(search)}`);
      allMatches = data.matches || [];
      renderStats(allMatches);
      renderGrid(allMatches);
      populateRoundFilter(allMatches);
    } catch (e) {
      console.error('[matches] fetch error', e);
    }
  }

  function debouncedRefresh() {
    clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(refresh, 300);
  }

  /* ─── Stats ──────────────────────────────────────────────── */
  function renderStats(matches) {
    const el = (id, val) => { const e = $(`#matches-stat-${id}`); if (e) e.textContent = val; };
    el('total', matches.length);
    el('scheduled', matches.filter(m => ['scheduled','check_in','ready'].includes(m.state)).length);
    el('live', matches.filter(m => m.state === 'live').length);
    el('completed', matches.filter(m => ['completed','forfeit'].includes(m.state)).length);
    el('disputed', matches.filter(m => m.state === 'disputed').length);
  }

  /* ─── Round filter ───────────────────────────────────────── */
  function populateRoundFilter(matches) {
    const sel = $('#match-filter-round');
    if (!sel) return;
    const rounds = [...new Set(matches.map(m => m.round_number))].sort((a, b) => a - b);
    const current = sel.value;
    sel.innerHTML = '<option value="">All Rounds</option>' +
      rounds.map(r => `<option value="${r}" ${String(r) === current ? 'selected' : ''}>Round ${r}</option>`).join('');
  }

  /* ─── Grid rendering (S6-F1) ─────────────────────────────── */
  function renderGrid(matches) {
    const tbody = $('#match-grid-body');
    if (!tbody) return;

    if (!matches.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="py-12 text-center text-dc-text">No matches found</td></tr>';
      return;
    }

    tbody.innerHTML = matches.map(m => {
      const sc = stateConfig[m.state] || stateConfig.scheduled;
      const isWinner1 = m.winner_id && m.winner_id === m.participant1_id;
      const isWinner2 = m.winner_id && m.winner_id === m.participant2_id;
      return `
        <tr class="border-b border-dc-border/50 hover:bg-white/[0.02] transition-colors">
          <td class="py-3 px-4 font-mono font-bold text-dc-text">R${m.round_number}</td>
          <td class="py-3 px-4 font-mono text-dc-textBright">#${m.match_number}</td>
          <td class="py-3 px-4">
            <span class="${isWinner1 ? 'text-dc-success font-bold' : 'text-dc-textBright'}">${m.participant1_name || 'TBD'}</span>
          </td>
          <td class="py-3 px-4 text-center font-mono font-bold text-white">${m.participant1_score} — ${m.participant2_score}</td>
          <td class="py-3 px-4">
            <span class="${isWinner2 ? 'text-dc-success font-bold' : 'text-dc-textBright'}">${m.participant2_name || 'TBD'}</span>
          </td>
          <td class="py-3 px-4 text-center">
            <span class="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${sc.cls}">${sc.label}</span>
            ${m.is_paused ? '<span class="ml-1 text-[8px] font-bold text-dc-warning">⏸</span>' : ''}
          </td>
          <td class="py-3 px-4 text-center">
            <div class="flex items-center justify-center gap-1">
              ${renderMedicButtons(m)}
              <button onclick="TOC.matches.openScoreDrawer(${m.id})" title="Score" class="w-6 h-6 rounded bg-dc-panel border border-dc-border flex items-center justify-center hover:bg-white/5">
                <i data-lucide="edit-3" class="w-3 h-3 text-dc-text"></i>
              </button>
              <button onclick="TOC.matches.openDetailDrawer(${m.id})" title="Details" class="w-6 h-6 rounded bg-dc-panel border border-dc-border flex items-center justify-center hover:bg-white/5">
                <i data-lucide="info" class="w-3 h-3 text-dc-text"></i>
              </button>
            </div>
          </td>
        </tr>`;
    }).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* ─── S6-F2: Match Medic inline controls ─────────────────── */
  function renderMedicButtons(m) {
    const btns = [];
    if (['scheduled','check_in','ready'].includes(m.state)) {
      btns.push(`<button onclick="TOC.matches.markLive(${m.id})" title="Start" class="w-6 h-6 rounded bg-dc-success/20 border border-dc-success/30 flex items-center justify-center hover:bg-dc-success/30"><i data-lucide="play" class="w-3 h-3 text-dc-success"></i></button>`);
    }
    if (m.state === 'live' && !m.is_paused) {
      btns.push(`<button onclick="TOC.matches.pause(${m.id})" title="Pause" class="w-6 h-6 rounded bg-dc-warning/20 border border-dc-warning/30 flex items-center justify-center hover:bg-dc-warning/30"><i data-lucide="pause" class="w-3 h-3 text-dc-warning"></i></button>`);
    }
    if (m.state === 'live' && m.is_paused) {
      btns.push(`<button onclick="TOC.matches.resume(${m.id})" title="Resume" class="w-6 h-6 rounded bg-dc-success/20 border border-dc-success/30 flex items-center justify-center hover:bg-dc-success/30"><i data-lucide="play" class="w-3 h-3 text-dc-success"></i></button>`);
    }
    if (m.state === 'live') {
      btns.push(`<button onclick="TOC.matches.forceComplete(${m.id})" title="Force Complete" class="w-6 h-6 rounded bg-dc-danger/20 border border-dc-danger/30 flex items-center justify-center hover:bg-dc-danger/30"><i data-lucide="square" class="w-3 h-3 text-dc-danger"></i></button>`);
    }
    return btns.join('');
  }

  /* ─── Quick actions ──────────────────────────────────────── */
  async function markLive(id) {
    try { await API.post(`/api/toc/${slug}/matches/${id}/mark-live/`); toast('Match started', 'success'); refresh(); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  async function pause(id) {
    try { await API.post(`/api/toc/${slug}/matches/${id}/pause/`); toast('Match paused', 'info'); refresh(); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  async function resume(id) {
    try { await API.post(`/api/toc/${slug}/matches/${id}/resume/`); toast('Match resumed', 'success'); refresh(); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  async function forceComplete(id) {
    if (!confirm('Force-complete this match?')) return;
    try { await API.post(`/api/toc/${slug}/matches/${id}/force-complete/`); toast('Match force-completed', 'info'); refresh(); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  /* ─── S6-F3: Score drawer ───────────────────────────────── */
  function openScoreDrawer(id) {
    const m = allMatches.find(x => x.id === id);
    if (!m) return;
    const html = `
      <div class="p-6 space-y-4">
        <h3 class="font-display font-black text-lg text-white">Submit Score</h3>
        <p class="text-xs text-dc-text">R${m.round_number} Match #${m.match_number}: ${m.participant1_name || 'TBD'} vs ${m.participant2_name || 'TBD'}</p>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">${m.participant1_name || 'Team A'}</label>
            <input id="sd-p1" type="number" value="${m.participant1_score}" min="0" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs font-mono text-center focus:border-theme outline-none">
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">${m.participant2_name || 'Team B'}</label>
            <input id="sd-p2" type="number" value="${m.participant2_score}" min="0" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs font-mono text-center focus:border-theme outline-none">
          </div>
        </div>
        <button onclick="TOC.matches.submitScore(${id})" class="w-full py-2.5 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Submit Score</button>
      </div>`;
    showOverlay('score-overlay', html);
  }

  async function submitScore(id) {
    try {
      await API.post(`/api/toc/${slug}/matches/${id}/score/`, {
        participant1_score: parseInt($('#sd-p1')?.value) || 0,
        participant2_score: parseInt($('#sd-p2')?.value) || 0,
      });
      toast('Score submitted', 'success');
      closeOverlay('score-overlay');
      refresh();
    } catch (e) {
      toast(e.message || 'Failed', 'error');
    }
  }

  /* ─── S6-F4: Reschedule modal ────────────────────────────── */
  function openRescheduleModal(id) {
    const html = `
      <div class="p-6 space-y-4">
        <h3 class="font-display font-black text-lg text-white">Reschedule Match</h3>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">New Time</label>
          <input id="rs-time" type="datetime-local" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Reason</label>
          <textarea id="rs-reason" rows="2" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none" placeholder="Optional reason..."></textarea>
        </div>
        <button onclick="TOC.matches.confirmReschedule(${id})" class="w-full py-2.5 bg-dc-warning text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Request Reschedule</button>
      </div>`;
    showOverlay('reschedule-overlay', html);
  }

  async function confirmReschedule(id) {
    const time = $('#rs-time')?.value;
    if (!time) { toast('Time required', 'error'); return; }
    try {
      await API.post(`/api/toc/${slug}/matches/${id}/reschedule/`, {
        new_time: new Date(time).toISOString(),
        reason: $('#rs-reason')?.value || '',
      });
      toast('Reschedule requested', 'success');
      closeOverlay('reschedule-overlay');
      refresh();
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  /* ─── S6-F5: Match detail drawer ─────────────────────────── */
  function openDetailDrawer(id) {
    const m = allMatches.find(x => x.id === id);
    if (!m) return;
    const sc = stateConfig[m.state] || stateConfig.scheduled;
    const html = `
      <div class="p-6 space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="font-display font-black text-lg text-white">Match #${m.match_number}</h3>
          <span class="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${sc.cls}">${sc.label}</span>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="text-center bg-dc-bg border border-dc-border rounded-lg p-3">
            <p class="text-xs text-dc-textBright font-bold">${m.participant1_name || 'TBD'}</p>
            <p class="font-mono font-black text-2xl text-white mt-1">${m.participant1_score}</p>
          </div>
          <div class="text-center bg-dc-bg border border-dc-border rounded-lg p-3">
            <p class="text-xs text-dc-textBright font-bold">${m.participant2_name || 'TBD'}</p>
            <p class="font-mono font-black text-2xl text-white mt-1">${m.participant2_score}</p>
          </div>
        </div>
        <div class="space-y-2 text-[10px]">
          <div class="flex justify-between text-dc-text"><span>Round</span><span class="text-dc-textBright font-mono">${m.round_number}</span></div>
          <div class="flex justify-between text-dc-text"><span>Scheduled</span><span class="text-dc-textBright font-mono">${m.scheduled_time ? new Date(m.scheduled_time).toLocaleString() : '—'}</span></div>
          <div class="flex justify-between text-dc-text"><span>Started</span><span class="text-dc-textBright font-mono">${m.started_at ? new Date(m.started_at).toLocaleString() : '—'}</span></div>
          <div class="flex justify-between text-dc-text"><span>Completed</span><span class="text-dc-textBright font-mono">${m.completed_at ? new Date(m.completed_at).toLocaleString() : '—'}</span></div>
          <div class="flex justify-between text-dc-text"><span>Stream</span><span class="text-dc-textBright font-mono">${m.stream_url || '—'}</span></div>
          <div class="flex justify-between text-dc-text"><span>Notes</span><span class="text-dc-textBright font-mono">${m.notes_count}</span></div>
        </div>
        <div class="flex gap-2">
          <button onclick="TOC.matches.openScoreDrawer(${id}); TOC.matches.closeOverlay('detail-overlay');" class="flex-1 py-2 bg-theme text-dc-bg text-[10px] font-bold uppercase rounded-lg">Score</button>
          <button onclick="TOC.matches.openRescheduleModal(${id}); TOC.matches.closeOverlay('detail-overlay');" class="flex-1 py-2 bg-dc-panel border border-dc-border text-dc-textBright text-[10px] font-bold uppercase rounded-lg">Reschedule</button>
          <button onclick="TOC.matches.openForfeit(${id}); TOC.matches.closeOverlay('detail-overlay');" class="flex-1 py-2 bg-dc-danger/20 border border-dc-danger/30 text-dc-danger text-[10px] font-bold uppercase rounded-lg">Forfeit</button>
        </div>
      </div>`;
    showOverlay('detail-overlay', html);
  }

  /* ─── Forfeit ────────────────────────────────────────────── */
  function openForfeit(id) {
    const m = allMatches.find(x => x.id === id);
    if (!m) return;
    const html = `
      <div class="p-6 space-y-4">
        <h3 class="font-display font-black text-lg text-white">Declare Forfeit</h3>
        <p class="text-xs text-dc-text">Select which participant is forfeiting:</p>
        <div class="grid grid-cols-2 gap-3">
          <button onclick="TOC.matches.confirmForfeit(${id}, ${m.participant1_id})" class="py-3 bg-dc-danger/10 border border-dc-danger/30 text-dc-danger text-xs font-bold rounded-lg hover:bg-dc-danger/20">${m.participant1_name || 'Team A'}</button>
          <button onclick="TOC.matches.confirmForfeit(${id}, ${m.participant2_id})" class="py-3 bg-dc-danger/10 border border-dc-danger/30 text-dc-danger text-xs font-bold rounded-lg hover:bg-dc-danger/20">${m.participant2_name || 'Team B'}</button>
        </div>
      </div>`;
    showOverlay('forfeit-overlay', html);
  }

  async function confirmForfeit(matchId, forfeiterId) {
    try {
      await API.post(`/api/toc/${slug}/matches/${matchId}/forfeit/`, { forfeiter_id: forfeiterId });
      toast('Forfeit declared', 'info');
      closeOverlay('forfeit-overlay');
      refresh();
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  /* ─── Overlay helpers ────────────────────────────────────── */
  function showOverlay(id, innerHtml) {
    document.getElementById(id)?.remove();
    const modal = document.createElement('div');
    modal.id = id;
    modal.className = 'fixed inset-0 z-[110] flex items-center justify-center';
    modal.innerHTML = `
      <div class="absolute inset-0 bg-black/80 backdrop-blur-md" onclick="TOC.matches.closeOverlay('${id}')"></div>
      <div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-md relative z-10 overflow-hidden">
        <div class="h-1 w-full bg-theme"></div>
        ${innerHtml}
      </div>`;
    document.body.appendChild(modal);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function closeOverlay(id) { document.getElementById(id)?.remove(); }

  /* ─── Init ───────────────────────────────────────────────── */
  function init() { refresh(); }

  window.TOC = window.TOC || {};
  window.TOC.matches = {
    init, refresh, debouncedRefresh,
    markLive, pause, resume, forceComplete,
    openScoreDrawer, submitScore,
    openDetailDrawer,
    openRescheduleModal, confirmReschedule,
    openForfeit, confirmForfeit,
    closeOverlay,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'matches') init();
  });
})();
