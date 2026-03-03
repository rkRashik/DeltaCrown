/**
 * TOC Matches Module — Sprint 6 + Sprint 9 (Match Verification Split-Screen)
 * Match grid, scoring, Match Medic (live/pause/resume/force-complete),
 * reschedule, forfeit, notes, media, broadcast stations,
 * and Sprint 9 verify split-screen with evidence viewer + mismatch detection.
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
      const data = await API.get(`matches/` +
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
              <button onclick="TOC.matches.openScoreDrawer(${m.id})" title="Score" data-cap-require="manage_brackets" class="w-6 h-6 rounded bg-dc-panel border border-dc-border flex items-center justify-center hover:bg-white/5">
                <i data-lucide="edit-3" class="w-3 h-3 text-dc-text"></i>
              </button>
              <button onclick="TOC.matches.openVerifyScreen(${m.id})" title="Verify" data-cap-require="manage_brackets" class="w-6 h-6 rounded bg-theme/10 border border-theme/30 flex items-center justify-center hover:bg-theme/20">
                <i data-lucide="shield-check" class="w-3 h-3 text-theme"></i>
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
      btns.push(`<button onclick="TOC.matches.markLive(${m.id})" title="Start" data-cap-require="manage_brackets" class="w-6 h-6 rounded bg-dc-success/20 border border-dc-success/30 flex items-center justify-center hover:bg-dc-success/30"><i data-lucide="play" class="w-3 h-3 text-dc-success"></i></button>`);
    }
    if (m.state === 'live' && !m.is_paused) {
      btns.push(`<button onclick="TOC.matches.pause(${m.id})" title="Pause" data-cap-require="manage_brackets" class="w-6 h-6 rounded bg-dc-warning/20 border border-dc-warning/30 flex items-center justify-center hover:bg-dc-warning/30"><i data-lucide="pause" class="w-3 h-3 text-dc-warning"></i></button>`);
    }
    if (m.state === 'live' && m.is_paused) {
      btns.push(`<button onclick="TOC.matches.resume(${m.id})" title="Resume" data-cap-require="manage_brackets" class="w-6 h-6 rounded bg-dc-success/20 border border-dc-success/30 flex items-center justify-center hover:bg-dc-success/30"><i data-lucide="play" class="w-3 h-3 text-dc-success"></i></button>`);
    }
    if (m.state === 'live') {
      btns.push(`<button onclick="TOC.matches.forceComplete(${m.id})" title="Force Complete" data-cap-require="manage_brackets" class="w-6 h-6 rounded bg-dc-danger/20 border border-dc-danger/30 flex items-center justify-center hover:bg-dc-danger/30"><i data-lucide="square" class="w-3 h-3 text-dc-danger"></i></button>`);
    }
    return btns.join('');
  }

  /* ─── Quick actions ──────────────────────────────────────── */
  async function markLive(id) {
    try { await API.post(`matches/${id}/mark-live/`); toast('Match started', 'success'); refresh(); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  async function pause(id) {
    try { await API.post(`matches/${id}/pause/`); toast('Match paused', 'info'); refresh(); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  async function resume(id) {
    try { await API.post(`matches/${id}/resume/`); toast('Match resumed', 'success'); refresh(); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  async function forceComplete(id) {
    if (!confirm('Force-complete this match?')) return;
    try { await API.post(`matches/${id}/force-complete/`); toast('Match force-completed', 'info'); refresh(); }
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
      await API.post(`matches/${id}/score/`, {
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
      await API.post(`matches/${id}/reschedule/`, {
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
      await API.post(`matches/${matchId}/forfeit/`, { forfeiter_id: forfeiterId });
      toast('Forfeit declared', 'info');
      closeOverlay('forfeit-overlay');
      refresh();
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  /* ─── S9: Verification Split-Screen ───────────────────────── */

  let _verifyDetail = null;       // Cached detail for current match
  let _evidenceIndex = 0;         // 0 = Captain A, 1 = Captain B
  let _zoomScale = 1;
  let _panX = 0, _panY = 0;
  let _isPanning = false, _panStartX = 0, _panStartY = 0;

  async function openVerifyScreen(id) {
    try {
      const data = await API.get(`matches/${id}/detail/`);
      _verifyDetail = data;
      _evidenceIndex = 0;
      _zoomScale = 1;
      _panX = 0;
      _panY = 0;
      renderVerifyScreen(id, data);
    } catch (e) {
      toast(e.message || 'Failed to load match detail', 'error');
    }
  }

  function renderVerifyScreen(id, data) {
    const m = data.match;
    const vs = data.verification_status;
    const subs = data.submissions || [];
    const media = data.media || [];
    const notes = data.notes || [];
    const disputes = data.disputes || [];
    const sc = stateConfig[m.state] || stateConfig.scheduled;

    // Determine evidence sources (submissions with proof or media with is_evidence)
    const evidenceSources = [];
    subs.forEach((s, idx) => {
      if (s.proof_screenshot_url) {
        evidenceSources.push({
          label: s.submitted_by_team_id ? `Team ${idx === 0 ? 'A' : 'B'}` : s.submitted_by_name,
          url: s.proof_screenshot_url,
          type: 'submission',
          payload: s.raw_result_payload,
          notes: s.submitter_notes,
        });
      }
    });
    media.filter(x => x.is_evidence).forEach(x => {
      evidenceSources.push({
        label: x.description || x.media_type,
        url: x.url,
        type: 'media',
      });
    });

    // Verification banner
    const bannerMap = {
      match:     { icon: '🟢', cls: 'bg-dc-success/10 border-dc-success/30 text-dc-success' },
      mismatch:  { icon: '🔴', cls: 'bg-dc-danger/10 border-dc-danger/30 text-dc-danger' },
      pending:   { icon: '🟡', cls: 'bg-dc-warning/10 border-dc-warning/30 text-dc-warning' },
      finalized: { icon: '✅', cls: 'bg-dc-text/10 border-dc-border text-dc-textBright' },
    };
    const b = bannerMap[vs.code] || bannerMap.pending;

    // Sub scores for right panel
    const sub0 = subs[0]?.raw_result_payload || {};
    const sub1 = subs[1]?.raw_result_payload || {};

    const html = `
      <div class="flex flex-col h-full max-h-[90vh]">
        {/* Header bar */}
        <div class="flex items-center justify-between p-4 border-b border-dc-borderLight bg-dc-panel/80">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-theme/20 flex items-center justify-center">
              <i data-lucide="shield-check" class="w-4 h-4 text-theme"></i>
            </div>
            <div>
              <h3 class="font-display font-black text-white text-sm">R${m.round_number} Match #${m.match_number} — Verification</h3>
              <p class="text-[10px] text-dc-text">${m.participant1_name || 'TBD'} vs ${m.participant2_name || 'TBD'}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${sc.cls}">${sc.label}</span>
            <button onclick="TOC.matches.closeOverlay('verify-overlay')" class="w-8 h-8 rounded-lg bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5">
              <i data-lucide="x" class="w-4 h-4 text-dc-text"></i>
            </button>
          </div>
        </div>

        {/* Mismatch detection banner */}
        <div class="mx-4 mt-4 p-3 rounded-lg border ${b.cls} flex items-center gap-2">
          <span class="text-base">${b.icon}</span>
          <div>
            <span class="text-[10px] font-black uppercase tracking-widest">${vs.label}</span>
            <span class="text-[10px] ml-2 opacity-80">${vs.detail}</span>
          </div>
        </div>

        {/* Split panels */}
        <div class="flex flex-1 overflow-hidden mt-4 mx-4 mb-4 gap-4" style="min-height:0">

          {/* ── LEFT: Evidence Viewer ── */}
          <div class="flex-1 flex flex-col bg-dc-bg border border-dc-border rounded-xl overflow-hidden">
            {/* Evidence toolbar */}
            <div class="flex items-center justify-between p-3 border-b border-dc-border bg-dc-panel/50">
              <div class="flex items-center gap-2">
                <i data-lucide="image" class="w-3.5 h-3.5 text-theme"></i>
                <span class="text-[10px] font-bold text-white uppercase tracking-widest">Evidence Viewer</span>
                ${evidenceSources.length > 1 ? `
                  <div class="flex items-center gap-1 ml-3">
                    ${evidenceSources.map((ev, i) => `
                      <button onclick="TOC.matches.switchEvidence(${i})"
                        class="px-2 py-0.5 rounded text-[9px] font-bold transition-colors
                        ${i === 0 ? 'bg-theme text-dc-bg' : 'bg-dc-bg border border-dc-border text-dc-text hover:text-white'}"
                        id="ev-tab-${i}">${ev.label}</button>
                    `).join('')}
                  </div>
                ` : ''}
              </div>
              <div class="flex items-center gap-1">
                <button onclick="TOC.matches.zoomEvidence(-1)" title="Zoom out" class="w-6 h-6 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5">
                  <i data-lucide="zoom-out" class="w-3 h-3 text-dc-text"></i>
                </button>
                <span id="verify-zoom-level" class="text-[9px] font-mono text-dc-text w-10 text-center">100%</span>
                <button onclick="TOC.matches.zoomEvidence(1)" title="Zoom in" class="w-6 h-6 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5">
                  <i data-lucide="zoom-in" class="w-3 h-3 text-dc-text"></i>
                </button>
                <button onclick="TOC.matches.resetZoom()" title="Reset" class="w-6 h-6 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5">
                  <i data-lucide="maximize-2" class="w-3 h-3 text-dc-text"></i>
                </button>
              </div>
            </div>
            {/* Image canvas */}
            <div id="evidence-canvas"
                 class="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing flex items-center justify-center bg-black/40"
                 onmousedown="TOC.matches.startPan(event)"
                 onmousemove="TOC.matches.doPan(event)"
                 onmouseup="TOC.matches.endPan()"
                 onmouseleave="TOC.matches.endPan()"
                 onwheel="TOC.matches.wheelZoom(event)">
              ${evidenceSources.length > 0
                ? `<img id="evidence-img" src="${evidenceSources[0].url}" alt="Evidence"
                     class="max-w-none select-none" draggable="false"
                     style="transform: scale(1) translate(0px, 0px); transition: transform 0.15s ease;"
                     onerror="this.style.display='none'; document.getElementById('evidence-fallback').style.display='flex';">
                   <div id="evidence-fallback" class="hidden absolute inset-0 flex-col items-center justify-center text-dc-text gap-2">
                     <i data-lucide="image-off" class="w-8 h-8 opacity-30"></i>
                     <span class="text-xs">Failed to load image</span>
                   </div>`
                : `<div class="flex flex-col items-center justify-center text-dc-text gap-2">
                     <i data-lucide="image-off" class="w-8 h-8 opacity-30"></i>
                     <span class="text-xs">No evidence submitted</span>
                   </div>`}
            </div>
            ${evidenceSources.length > 0 && evidenceSources[0].notes ? `
              <div class="p-3 border-t border-dc-border text-[10px] text-dc-text">
                <span class="font-bold text-dc-textBright">Submitter notes:</span> ${evidenceSources[0].notes}
              </div>
            ` : ''}
          </div>

          {/* ── RIGHT: Score Entry & Actions ── */}
          <div class="w-[380px] flex-shrink-0 flex flex-col gap-4 overflow-y-auto pr-1">

            {/* Submitted scores comparison */}
            <div class="bg-dc-surface border border-dc-border rounded-xl overflow-hidden">
              <div class="p-3 border-b border-dc-border bg-dc-panel/50 flex items-center gap-2">
                <i data-lucide="git-compare" class="w-3.5 h-3.5 text-theme"></i>
                <span class="text-[10px] font-bold text-white uppercase tracking-widest">Submitted Scores</span>
              </div>
              <div class="p-4 space-y-3">
                ${subs.length > 0 ? subs.map((s, idx) => `
                  <div class="flex items-center gap-3 p-2 rounded-lg ${idx === 0 ? 'bg-blue-500/5 border border-blue-500/20' : 'bg-purple-500/5 border border-purple-500/20'}">
                    <span class="text-[9px] font-bold uppercase tracking-widest ${idx === 0 ? 'text-blue-400' : 'text-purple-400'} w-16">
                      ${s.submitted_by_team_id ? (idx === 0 ? 'Capt. A' : 'Capt. B') : s.submitted_by_name}
                    </span>
                    <span class="font-mono font-black text-white text-sm flex-1 text-center">
                      ${(s.raw_result_payload?.score_p1 ?? '—')} – ${(s.raw_result_payload?.score_p2 ?? '—')}
                    </span>
                    <span class="text-[8px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider
                      ${s.status === 'confirmed' || s.status === 'finalized' ? 'bg-dc-success/20 text-dc-success' :
                        s.status === 'disputed' ? 'bg-dc-danger/20 text-dc-danger' :
                        'bg-dc-warning/20 text-dc-warning'}">${s.status}</span>
                  </div>
                `).join('') : `
                  <p class="text-[10px] text-dc-text text-center py-2">No submissions yet</p>
                `}
              </div>
            </div>

            {/* Final score entry */}
            <div class="bg-dc-surface border border-dc-border rounded-xl overflow-hidden">
              <div class="p-3 border-b border-dc-border bg-dc-panel/50 flex items-center gap-2">
                <i data-lucide="target" class="w-3.5 h-3.5 text-theme"></i>
                <span class="text-[10px] font-bold text-white uppercase tracking-widest">Final Score</span>
              </div>
              <div class="p-4">
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">${m.participant1_name || 'Team A'}</label>
                    <input id="verify-p1" type="number" value="${vs.code === 'match' ? (sub0.score_p1 ?? m.participant1_score) : m.participant1_score}" min="0"
                      class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-sm font-mono text-center font-bold focus:border-theme outline-none">
                  </div>
                  <div>
                    <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">${m.participant2_name || 'Team B'}</label>
                    <input id="verify-p2" type="number" value="${vs.code === 'match' ? (sub0.score_p2 ?? m.participant2_score) : m.participant2_score}" min="0"
                      class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-sm font-mono text-center font-bold focus:border-theme outline-none">
                  </div>
                </div>
              </div>
            </div>

            {/* Admin note input */}
            <div class="bg-dc-surface border border-dc-border rounded-xl overflow-hidden">
              <div class="p-3 border-b border-dc-border bg-dc-panel/50 flex items-center gap-2">
                <i data-lucide="message-square" class="w-3.5 h-3.5 text-theme"></i>
                <span class="text-[10px] font-bold text-white uppercase tracking-widest">Admin Notes</span>
              </div>
              <div class="p-4">
                <textarea id="verify-notes" rows="2"
                  class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none"
                  placeholder="Optional admin note ..."></textarea>
              </div>
            </div>

            {/* Quick action buttons */}
            <div class="space-y-2">
              <button onclick="TOC.matches.verifyAction(${id}, 'confirm')"
                class="w-full py-3 bg-dc-success text-dc-bg text-xs font-black uppercase tracking-widest rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2
                  ${m.state === 'completed' ? 'opacity-40 pointer-events-none' : ''}">
                <span>✅</span> Confirm & Finalize
              </button>
              <button onclick="TOC.matches.verifyAction(${id}, 'dispute')"
                class="w-full py-3 bg-dc-danger/20 border border-dc-danger/30 text-dc-danger text-xs font-black uppercase tracking-widest rounded-xl hover:bg-dc-danger/30 transition-colors flex items-center justify-center gap-2
                  ${m.state === 'disputed' ? 'opacity-40 pointer-events-none' : ''}">
                <span>❌</span> Open Dispute
              </button>
              <button onclick="TOC.matches.verifyAction(${id}, 'note')"
                class="w-full py-3 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-black uppercase tracking-widest rounded-xl hover:bg-white/5 transition-colors flex items-center justify-center gap-2">
                <span>📝</span> Add Admin Note
              </button>
            </div>

            {/* Existing notes */}
            ${notes.length > 0 ? `
              <div class="bg-dc-surface border border-dc-border rounded-xl overflow-hidden">
                <div class="p-3 border-b border-dc-border bg-dc-panel/50">
                  <span class="text-[10px] font-bold text-white uppercase tracking-widest">Note History (${notes.length})</span>
                </div>
                <div class="p-3 space-y-2 max-h-32 overflow-y-auto">
                  ${notes.map(n => `
                    <div class="text-[10px] p-2 rounded bg-dc-bg border border-dc-border">
                      <span class="text-dc-text">${n.created_at ? new Date(n.created_at).toLocaleString() : ''}</span>
                      <p class="text-dc-textBright mt-0.5">${n.text}</p>
                    </div>
                  `).join('')}
                </div>
              </div>
            ` : ''}

            {/* Disputes */}
            ${disputes.length > 0 ? `
              <div class="bg-dc-surface border border-dc-danger/20 rounded-xl overflow-hidden">
                <div class="p-3 border-b border-dc-danger/20 bg-dc-danger/5">
                  <span class="text-[10px] font-bold text-dc-danger uppercase tracking-widest">Active Disputes (${disputes.length})</span>
                </div>
                <div class="p-3 space-y-2 max-h-32 overflow-y-auto">
                  ${disputes.map(d => `
                    <div class="text-[10px] p-2 rounded bg-dc-bg border border-dc-danger/20">
                      <div class="flex items-center justify-between">
                        <span class="font-bold text-dc-danger">${d.reason_code}</span>
                        <span class="text-[8px] px-1.5 py-0.5 rounded bg-dc-danger/10 text-dc-danger font-bold uppercase">${d.status}</span>
                      </div>
                      <p class="text-dc-text mt-1">${d.description}</p>
                    </div>
                  `).join('')}
                </div>
              </div>
            ` : ''}

          </div>
        </div>
      </div>`;

    showFullOverlay('verify-overlay', html);
  }

  /* ── Evidence toggle ─── */
  function switchEvidence(idx) {
    if (!_verifyDetail) return;
    const subs = _verifyDetail.submissions || [];
    const media = (_verifyDetail.media || []).filter(x => x.is_evidence);
    const sources = [];
    subs.forEach((s, i) => { if (s.proof_screenshot_url) sources.push(s); });
    media.forEach(x => sources.push(x));
    if (idx < 0 || idx >= sources.length) return;

    _evidenceIndex = idx;
    _zoomScale = 1; _panX = 0; _panY = 0;

    const img = document.getElementById('evidence-img');
    if (img) {
      const src = sources[idx].proof_screenshot_url || sources[idx].url;
      img.src = src;
      img.style.transform = `scale(1) translate(0px, 0px)`;
      img.style.display = '';
      const fb = document.getElementById('evidence-fallback');
      if (fb) fb.style.display = 'none';
    }

    // Update tab pills
    document.querySelectorAll('[id^="ev-tab-"]').forEach((el, i) => {
      if (i === idx) {
        el.className = el.className.replace(/bg-dc-bg border border-dc-border text-dc-text hover:text-white/g, '').replace(/bg-theme text-dc-bg/g, '') + ' bg-theme text-dc-bg';
      } else {
        el.className = el.className.replace(/bg-theme text-dc-bg/g, '') + ' bg-dc-bg border border-dc-border text-dc-text hover:text-white';
      }
    });
  }

  /* ── Zoom / Pan helpers ─── */
  function zoomEvidence(dir) {
    _zoomScale = Math.max(0.25, Math.min(5, _zoomScale + dir * 0.25));
    applyTransform();
  }

  function resetZoom() {
    _zoomScale = 1; _panX = 0; _panY = 0;
    applyTransform();
  }

  function wheelZoom(e) {
    e.preventDefault();
    const dir = e.deltaY < 0 ? 1 : -1;
    zoomEvidence(dir);
  }

  function startPan(e) { _isPanning = true; _panStartX = e.clientX - _panX; _panStartY = e.clientY - _panY; }
  function doPan(e) {
    if (!_isPanning) return;
    _panX = e.clientX - _panStartX;
    _panY = e.clientY - _panStartY;
    applyTransform();
  }
  function endPan() { _isPanning = false; }

  function applyTransform() {
    const img = document.getElementById('evidence-img');
    if (img) img.style.transform = `scale(${_zoomScale}) translate(${_panX / _zoomScale}px, ${_panY / _zoomScale}px)`;
    const lvl = document.getElementById('verify-zoom-level');
    if (lvl) lvl.textContent = `${Math.round(_zoomScale * 100)}%`;
  }

  /* ── Verify action dispatch ─── */
  async function verifyAction(id, action) {
    const p1 = parseInt(document.getElementById('verify-p1')?.value) || 0;
    const p2 = parseInt(document.getElementById('verify-p2')?.value) || 0;
    const notes = document.getElementById('verify-notes')?.value || '';

    if (action === 'note' && !notes.trim()) {
      toast('Please enter a note', 'error'); return;
    }

    const body = { action, participant1_score: p1, participant2_score: p2, notes };
    if (action === 'dispute') body.reason_code = 'score_mismatch';

    try {
      const res = await API.post(`matches/${id}/verify/`, body);
      const labels = { confirmed: 'Match confirmed & finalized', disputed: 'Dispute opened', noted: 'Admin note added' };
      toast(labels[res.status] || 'Action completed', res.status === 'disputed' ? 'warning' : 'success');
      closeOverlay('verify-overlay');
      refresh();
    } catch (e) {
      toast(e.message || 'Verification failed', 'error');
    }
  }

  /* ── Full-screen overlay (wider than standard modal) ─── */
  function showFullOverlay(id, innerHtml) {
    document.getElementById(id)?.remove();
    const modal = document.createElement('div');
    modal.id = id;
    modal.className = 'fixed inset-0 z-[110] flex items-center justify-center p-4';
    modal.innerHTML = `
      <div class="absolute inset-0 bg-black/80 backdrop-blur-md" onclick="TOC.matches.closeOverlay('${id}')"></div>
      <div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-2xl w-full max-w-7xl relative z-10 overflow-hidden" style="height:90vh">
        <div class="h-1 w-full bg-theme"></div>
        ${innerHtml}
      </div>`;
    document.body.appendChild(modal);
    if (typeof lucide !== 'undefined') lucide.createIcons();
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
    // Sprint 9: Verification Split-Screen
    openVerifyScreen, verifyAction,
    switchEvidence, zoomEvidence, resetZoom, wheelZoom,
    startPan, doPan, endPan,
    closeOverlay,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'matches') init();
  });
})();
