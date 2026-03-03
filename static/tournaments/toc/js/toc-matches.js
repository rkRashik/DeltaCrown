/**
 * TOC Matches Module — Sprint 25: The Control Room (Master-Detail)
 * Left panel: scrollable match list with group pills, state/round/search filters.
 * Right panel: match detail with inline Score Editor, Evidence Viewer, Audit Trail.
 * Persistent action row with Medic controls + Confirm/Dispute/Reset.
 * Preserves Sprint 9 verify overlay as full-screen power-user mode.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

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

  let allMatches = [];
  let filteredMatches = [];
  let selectedMatchId = null;
  let selectedMatchDetail = null;
  let activeGroupFilter = '';
  let _debounceTimer = null;

  /* --- Fetch & render -------------------------------------- */
  async function refresh() {
    const state = $('#match-filter-state')?.value || '';
    const round = $('#match-filter-round')?.value || '';
    const search = $('#match-search')?.value || '';
    try {
      const data = await API.get('matches/' +
        '?state=' + state + '&round=' + round + '&search=' + encodeURIComponent(search));
      allMatches = data.matches || [];
      applyGroupFilter();
      renderStats(allMatches);
      populateRoundFilter(allMatches);
      populateGroupPills(allMatches);
    } catch (e) {
      console.error('[matches] fetch error', e);
    }
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
    matches.forEach(function(m) {
      if (m.group_label && !seen[m.group_label]) {
        seen[m.group_label] = true;
        groups.push(m.group_label);
      }
    });
    groups.sort();
    if (groups.length <= 1) { container.innerHTML = ''; return; }

    var html = '<button data-group="" class="match-pill ' +
      (activeGroupFilter === '' ? 'active bg-theme/15 text-theme border-theme/20' : 'bg-dc-bg text-dc-text border-dc-border hover:text-white') +
      ' px-2.5 py-1 rounded-md text-[9px] font-bold uppercase tracking-widest transition-all border" onclick="TOC.matches.filterGroup(\'\')">All</button>';
    groups.forEach(function(g) {
      html += '<button data-group="' + g + '" class="match-pill ' +
        (activeGroupFilter === g ? 'active bg-theme/15 text-theme border-theme/20' : 'bg-dc-bg text-dc-text border-dc-border hover:text-white') +
        ' px-2.5 py-1 rounded-md text-[9px] font-bold uppercase tracking-widest transition-all border" onclick="TOC.matches.filterGroup(\'' + g + '\')">' + g + '</button>';
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
      ? allMatches.filter(function(m) { return m.group_label === activeGroupFilter; })
      : allMatches.slice();
    renderMatchList(filteredMatches);
    if (selectedMatchId && !filteredMatches.find(function(m) { return m.id === selectedMatchId; })) {
      clearDetail();
    }
  }

  /* --- Stats ----------------------------------------------- */
  function renderStats(matches) {
    var el = function(id, val) { var e = $('#matches-stat-' + id); if (e) e.textContent = val; };
    el('total', matches.length);
    el('live', matches.filter(function(m) { return m.state === 'live'; }).length);
    el('pending', matches.filter(function(m) { return m.state === 'pending_result'; }).length);
    el('completed', matches.filter(function(m) { return m.state === 'completed' || m.state === 'forfeit'; }).length);
    el('disputed', matches.filter(function(m) { return m.state === 'disputed'; }).length);
  }

  /* --- Round filter ---------------------------------------- */
  function populateRoundFilter(matches) {
    var sel = $('#match-filter-round');
    if (!sel) return;
    var roundSet = {};
    matches.forEach(function(m) { roundSet[m.round_number] = true; });
    var rounds = Object.keys(roundSet).map(Number).sort(function(a,b){return a-b;});
    var current = sel.value;
    sel.innerHTML = '<option value="">All Rounds</option>' +
      rounds.map(function(r) { return '<option value="' + r + '"' + (String(r) === current ? ' selected' : '') + '>Round ' + r + '</option>'; }).join('');
  }

  /* ============================================================
     LEFT PANEL: Match List (compact cards)
  ============================================================ */
  function renderMatchList(matches) {
    var list = $('#match-list');
    if (!list) return;

    var countEl = $('#match-list-count');
    if (countEl) countEl.textContent = matches.length + ' match' + (matches.length !== 1 ? 'es' : '');

    if (!matches.length) {
      list.innerHTML = '<div class="flex items-center justify-center h-40"><div class="text-center">' +
        '<i data-lucide="inbox" class="w-8 h-8 text-dc-border mx-auto mb-2"></i>' +
        '<p class="text-xs text-dc-text/50">No matches found</p></div></div>';
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    list.innerHTML = matches.map(function(m) {
      var sc = stateConfig[m.state] || stateConfig.scheduled;
      var isSelected = m.id === selectedMatchId;
      var isWinner1 = m.winner_id && m.winner_id === m.participant1_id;
      var isWinner2 = m.winner_id && m.winner_id === m.participant2_id;
      var liveDot = m.state === 'live' ? '<span class="w-1.5 h-1.5 rounded-full bg-dc-success animate-pulse inline-block"></span>' : '';
      var groupTag = m.group_label ? ' &middot; <span class="text-theme">' + m.group_label + '</span>' : '';

      return '<div class="match-card px-3 py-2.5 cursor-pointer transition-all hover:bg-white/[0.02] ' +
        (isSelected ? 'bg-theme/5 border-l-2 border-l-theme' : 'border-l-2 border-l-transparent') +
        '" onclick="TOC.matches.selectMatch(' + m.id + ')" data-match-id="' + m.id + '">' +
        '<div class="flex items-center justify-between mb-1.5">' +
        '<span class="text-[9px] font-mono text-dc-text">R' + m.round_number + ' &middot; #' + m.match_number + groupTag + '</span>' +
        '<div class="flex items-center gap-1.5">' + liveDot +
        '<span class="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full border ' + sc.cls + '">' + sc.label + '</span>' +
        (m.is_paused ? '<span class="text-[8px] font-bold text-dc-warning">&#x23F8;</span>' : '') +
        '</div></div>' +
        '<div class="flex items-center gap-2">' +
        '<span class="flex-1 text-right text-xs ' + (isWinner1 ? 'text-dc-success font-bold' : 'text-dc-textBright') + ' truncate">' + (m.participant1_name || 'TBD') + '</span>' +
        '<span class="font-mono font-bold text-xs text-white px-2 py-0.5 rounded bg-dc-bg border border-dc-border min-w-[48px] text-center">' + m.participant1_score + ' &#8211; ' + m.participant2_score + '</span>' +
        '<span class="flex-1 text-left text-xs ' + (isWinner2 ? 'text-dc-success font-bold' : 'text-dc-textBright') + ' truncate">' + (m.participant2_name || 'TBD') + '</span>' +
        '</div></div>';
    }).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* ============================================================
     RIGHT PANEL: Match Detail
  ============================================================ */
  async function selectMatch(id) {
    selectedMatchId = id;

    // Highlight selected card in list
    $$('.match-card').forEach(function(el) {
      var mid = parseInt(el.dataset.matchId);
      if (mid === id) {
        el.classList.add('bg-theme/5', 'border-l-theme');
        el.classList.remove('border-l-transparent');
      } else {
        el.classList.remove('bg-theme/5', 'border-l-theme');
        el.classList.add('border-l-transparent');
      }
    });

    // Show detail content, hide empty state
    var empty = $('#match-detail-empty');
    var content = $('#match-detail-content');
    if (empty) empty.classList.add('hidden');
    if (content) content.classList.remove('hidden');

    // Render basic header from list data
    var m = allMatches.find(function(x) { return x.id === id; });
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
      stateEl.className = 'text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-widest border ' + sc.cls;
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
  }

  function renderAvatar(containerId, url) {
    var el = $('#' + containerId);
    if (!el) return;
    if (url) {
      el.innerHTML = '<img src="' + url + '" alt="" class="w-full h-full object-cover">';
    } else {
      el.innerHTML = '<i data-lucide="user" class="w-5 h-5 text-dc-border"></i>';
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }
  }

  /* -- Medic Buttons -- */
  function updateMedicButtons(m) {
    if (!m) return;
    var btnLive   = $('#btn-medic-live');
    var btnPause  = $('#btn-medic-pause');
    var btnResume = $('#btn-medic-resume');
    var btnForce  = $('#btn-medic-force');

    [btnLive, btnPause, btnResume, btnForce].forEach(function(b) { if (b) b.classList.add('hidden'); });

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
  }

  /* -- Evidence Viewer Tab -- */
  function renderEvidence(data) {
    var container = $('#evidence-container');
    var split = $('#evidence-split');
    var mismatch = $('#evidence-mismatch');
    if (!container) return;

    var subs = data.submissions || [];
    var media = (data.media || []).filter(function(x) { return x.is_evidence; });
    var vs = data.verification_status;

    if (subs.length === 0 && media.length === 0) {
      container.innerHTML = '<div class="text-center py-8">' +
        '<i data-lucide="image-off" class="w-10 h-10 text-dc-border mx-auto mb-2"></i>' +
        '<p class="text-xs text-dc-text/50">No evidence submitted yet</p></div>';
      if (split) split.classList.add('hidden');
      if (mismatch) mismatch.classList.add('hidden');
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    container.innerHTML = subs.map(function(s, idx) {
      var statusCls = (s.status === 'confirmed' || s.status === 'finalized') ? 'bg-dc-success/20 text-dc-success' :
        s.status === 'disputed' ? 'bg-dc-danger/20 text-dc-danger' : 'bg-dc-warning/20 text-dc-warning';
      return '<div class="flex items-center gap-3 p-2.5 rounded-lg ' +
        (idx === 0 ? 'bg-blue-500/5 border border-blue-500/20' : 'bg-purple-500/5 border border-purple-500/20') + '">' +
        '<span class="text-[9px] font-bold uppercase tracking-widest ' +
        (idx === 0 ? 'text-blue-400' : 'text-purple-400') + ' w-14 shrink-0">' +
        (s.submitted_by_team_id ? (idx === 0 ? 'Capt. A' : 'Capt. B') : (s.submitted_by_name || 'Sub ' + (idx+1))) + '</span>' +
        '<span class="font-mono font-black text-white text-sm flex-1 text-center">' +
        ((s.raw_result_payload && s.raw_result_payload.score_p1 != null) ? s.raw_result_payload.score_p1 : '-') +
        ' - ' +
        ((s.raw_result_payload && s.raw_result_payload.score_p2 != null) ? s.raw_result_payload.score_p2 : '-') +
        '</span>' +
        '<span class="text-[8px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ' + statusCls + '">' + s.status + '</span></div>';
    }).join('');

    if (split) {
      var imgA = (subs[0] && subs[0].proof_screenshot_url) || (media[0] && media[0].url);
      var imgB = (subs[1] && subs[1].proof_screenshot_url) || (media[1] && media[1].url);
      if (imgA || imgB) {
        split.classList.remove('hidden');
        var eA = $('#evidence-img-a');
        var eB = $('#evidence-img-b');
        if (eA) eA.innerHTML = imgA ? '<img src="' + imgA + '" class="w-full h-full object-contain" alt="Evidence A">' : '<i data-lucide="image" class="w-8 h-8 text-dc-border"></i>';
        if (eB) eB.innerHTML = imgB ? '<img src="' + imgB + '" class="w-full h-full object-contain" alt="Evidence B">' : '<i data-lucide="image" class="w-8 h-8 text-dc-border"></i>';
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
    timeline.forEach(function(t) { entries.push({ time: t.created_at, type: 'event', icon: 'activity', color: 'text-theme', text: t.description || t.action }); });
    notes.forEach(function(n) { entries.push({ time: n.created_at, type: 'note', icon: 'message-square', color: 'text-dc-info', text: n.text, by: n.author }); });
    disputes.forEach(function(d) { entries.push({ time: d.created_at, type: 'dispute', icon: 'flag', color: 'text-dc-danger', text: d.reason_code + ': ' + d.description, by: d.filed_by }); });

    entries.sort(function(a, b) { return new Date(b.time) - new Date(a.time); });

    if (!entries.length) {
      container.innerHTML = '<div class="flex items-center justify-center py-10"><p class="text-xs text-dc-text/50 font-mono">No audit entries</p></div>';
      return;
    }

    container.innerHTML = entries.map(function(e) {
      return '<div class="flex gap-3 px-4 py-3">' +
        '<div class="w-6 h-6 rounded-full bg-dc-bg border border-dc-border flex items-center justify-center shrink-0 mt-0.5">' +
        '<i data-lucide="' + e.icon + '" class="w-3 h-3 ' + e.color + '"></i></div>' +
        '<div class="flex-1 min-w-0">' +
        '<p class="text-xs text-dc-textBright">' + e.text + '</p>' +
        '<div class="flex items-center gap-2 mt-0.5">' +
        '<span class="text-[9px] text-dc-text font-mono">' + (e.time ? new Date(e.time).toLocaleString() : '') + '</span>' +
        (e.by ? '<span class="text-[9px] text-dc-text">&middot; ' + e.by + '</span>' : '') +
        '</div></div></div>';
    }).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /* -- Detail Tab Switcher -- */
  function switchDetailTab(tab) {
    $$('.detail-tab').forEach(function(el) {
      var t = el.dataset.detailTab;
      if (t === tab) {
        el.classList.add('active', 'text-theme', 'border-b-theme');
        el.classList.remove('text-dc-text', 'border-transparent');
      } else {
        el.classList.remove('active', 'text-theme', 'border-b-theme');
        el.classList.add('text-dc-text', 'border-transparent');
      }
    });
    $$('.detail-tab-content').forEach(function(el) { el.classList.add('hidden'); });
    var target = $('#detail-tab-' + tab);
    if (target) target.classList.remove('hidden');
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

  async function forceComplete(id) {
    var matchId = id || selectedMatchId;
    if (!matchId) return;
    if (!confirm('Force-complete this match?')) return;
    try { await API.post('matches/' + matchId + '/force-complete/'); toast('Match force-completed', 'info'); refresh(); selectMatch(matchId); }
    catch (e) { toast(e.message || 'Failed', 'error'); }
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

  async function openDispute() {
    if (!selectedMatchId) { toast('No match selected', 'error'); return; }
    var reason = prompt('Dispute reason (brief):');
    if (!reason) return;
    try {
      await API.post('matches/' + selectedMatchId + '/verify/', {
        action: 'dispute',
        reason_code: 'admin_dispute',
        notes: reason,
        participant1_score: parseInt($('#score-input-a')?.value) || 0,
        participant2_score: parseInt($('#score-input-b')?.value) || 0,
      });
      toast('Dispute opened', 'warning');
      refresh();
      selectMatch(selectedMatchId);
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  async function resetMatch() {
    if (!selectedMatchId) { toast('No match selected', 'error'); return; }
    if (!confirm('Reset this match? Scores and state will be cleared.')) return;
    try {
      await API.post('matches/' + selectedMatchId + '/reset/');
      toast('Match reset', 'info');
      refresh();
      selectMatch(selectedMatchId);
    } catch (e) { toast(e.message || 'Failed', 'error'); }
  }

  /* --- Legacy overlay bridges (reschedule, forfeit) --------- */
  function openScoreDrawer(id) { selectMatch(id); switchDetailTab('score'); }
  function openDetailDrawer(id) { selectMatch(id); }

  function openRescheduleModal(id) {
    var mid = id || selectedMatchId;
    var m = allMatches.find(function(x) { return x.id === mid; });
    if (!m) return;
    var html = '<div class="p-6 space-y-4">' +
      '<h3 class="font-display font-black text-lg text-white">Reschedule Match #' + m.match_number + '</h3>' +
      '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">New Time</label>' +
      '<input id="rs-time" type="datetime-local" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none"></div>' +
      '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Reason</label>' +
      '<textarea id="rs-reason" rows="2" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none" placeholder="Optional reason..."></textarea></div>' +
      '<button onclick="TOC.matches.confirmReschedule(' + mid + ')" class="w-full py-2.5 bg-dc-warning text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Request Reschedule</button></div>';
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
    var m = allMatches.find(function(x) { return x.id === mid; });
    if (!m) return;
    var html = '<div class="p-6 space-y-4">' +
      '<h3 class="font-display font-black text-lg text-white">Declare Forfeit</h3>' +
      '<p class="text-xs text-dc-text">Select which participant is forfeiting:</p>' +
      '<div class="grid grid-cols-2 gap-3">' +
      '<button onclick="TOC.matches.confirmForfeit(' + mid + ', ' + m.participant1_id + ')" class="py-3 bg-dc-danger/10 border border-dc-danger/30 text-dc-danger text-xs font-bold rounded-lg hover:bg-dc-danger/20">' + (m.participant1_name || 'Team A') + '</button>' +
      '<button onclick="TOC.matches.confirmForfeit(' + mid + ', ' + m.participant2_id + ')" class="py-3 bg-dc-danger/10 border border-dc-danger/30 text-dc-danger text-xs font-bold rounded-lg hover:bg-dc-danger/20">' + (m.participant2_name || 'Team B') + '</button>' +
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

  /* --- Sprint 9: Full-screen Verification Overlay ----------- */
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
    subs.forEach(function(s, idx) {
      if (s.proof_screenshot_url) {
        evidenceSources.push({
          label: s.submitted_by_team_id ? ('Team ' + (idx === 0 ? 'A' : 'B')) : s.submitted_by_name,
          url: s.proof_screenshot_url,
          notes: s.submitter_notes,
        });
      }
    });
    media.filter(function(x) { return x.is_evidence; }).forEach(function(x) {
      evidenceSources.push({ label: x.description || x.media_type, url: x.url });
    });

    var bannerMap = {
      match:     { icon: String.fromCodePoint(0x1F7E2), cls: 'bg-dc-success/10 border-dc-success/30 text-dc-success' },
      mismatch:  { icon: String.fromCodePoint(0x1F534), cls: 'bg-dc-danger/10 border-dc-danger/30 text-dc-danger' },
      pending:   { icon: String.fromCodePoint(0x1F7E1), cls: 'bg-dc-warning/10 border-dc-warning/30 text-dc-warning' },
      finalized: { icon: String.fromCodePoint(0x2705), cls: 'bg-dc-text/10 border-dc-border text-dc-textBright' },
    };
    var b = bannerMap[vs.code] || bannerMap.pending;
    var sub0 = (subs[0] && subs[0].raw_result_payload) || {};

    var evTabsHtml = '';
    if (evidenceSources.length > 1) {
      evTabsHtml = '<div class="flex items-center gap-1 ml-3">';
      evidenceSources.forEach(function(ev, i) {
        evTabsHtml += '<button onclick="TOC.matches.switchEvidence(' + i + ')" class="px-2 py-0.5 rounded text-[9px] font-bold transition-colors ' +
          (i === 0 ? 'bg-theme text-dc-bg' : 'bg-dc-bg border border-dc-border text-dc-text hover:text-white') +
          '" id="ev-tab-' + i + '">' + ev.label + '</button>';
      });
      evTabsHtml += '</div>';
    }

    var subsHtml = '';
    if (subs.length > 0) {
      subs.forEach(function(s, idx) {
        var sCls = (s.status === 'confirmed' || s.status === 'finalized') ? 'bg-dc-success/20 text-dc-success' :
          s.status === 'disputed' ? 'bg-dc-danger/20 text-dc-danger' : 'bg-dc-warning/20 text-dc-warning';
        subsHtml += '<div class="flex items-center gap-3 p-2 rounded-lg ' +
          (idx === 0 ? 'bg-blue-500/5 border border-blue-500/20' : 'bg-purple-500/5 border border-purple-500/20') + '">' +
          '<span class="text-[9px] font-bold uppercase tracking-widest ' +
          (idx === 0 ? 'text-blue-400' : 'text-purple-400') + ' w-16">' +
          (s.submitted_by_team_id ? (idx === 0 ? 'Capt. A' : 'Capt. B') : s.submitted_by_name) + '</span>' +
          '<span class="font-mono font-black text-white text-sm flex-1 text-center">' +
          ((s.raw_result_payload && s.raw_result_payload.score_p1 != null) ? s.raw_result_payload.score_p1 : '-') + ' - ' +
          ((s.raw_result_payload && s.raw_result_payload.score_p2 != null) ? s.raw_result_payload.score_p2 : '-') + '</span>' +
          '<span class="text-[8px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ' + sCls + '">' + s.status + '</span></div>';
      });
    } else {
      subsHtml = '<p class="text-[10px] text-dc-text text-center py-2">No submissions yet</p>';
    }

    var evidenceHtml;
    if (evidenceSources.length > 0) {
      evidenceHtml = '<img id="evidence-img" src="' + evidenceSources[0].url + '" alt="Evidence" class="max-w-none select-none" draggable="false" style="transform: scale(1) translate(0px, 0px); transition: transform 0.15s ease;" onerror="this.style.display=\'none\'; document.getElementById(\'evidence-fallback\').style.display=\'flex\';">' +
        '<div id="evidence-fallback" class="hidden absolute inset-0 flex-col items-center justify-center text-dc-text gap-2"><i data-lucide="image-off" class="w-8 h-8 opacity-30"></i><span class="text-xs">Failed to load</span></div>';
    } else {
      evidenceHtml = '<div class="flex flex-col items-center justify-center text-dc-text gap-2"><i data-lucide="image-off" class="w-8 h-8 opacity-30"></i><span class="text-xs">No evidence submitted</span></div>';
    }

    var html = '<div class="flex flex-col h-full max-h-[90vh]">' +
      '<div class="flex items-center justify-between p-4 border-b border-dc-borderLight bg-dc-panel/80">' +
      '<div class="flex items-center gap-3"><div class="w-8 h-8 rounded-lg bg-theme/20 flex items-center justify-center"><i data-lucide="shield-check" class="w-4 h-4 text-theme"></i></div>' +
      '<div><h3 class="font-display font-black text-white text-sm">R' + m.round_number + ' Match #' + m.match_number + ' &mdash; Verification</h3>' +
      '<p class="text-[10px] text-dc-text">' + (m.participant1_name || 'TBD') + ' vs ' + (m.participant2_name || 'TBD') + '</p></div></div>' +
      '<div class="flex items-center gap-2"><span class="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ' + sc.cls + '">' + sc.label + '</span>' +
      '<button onclick="TOC.matches.closeOverlay(\'verify-overlay\')" class="w-8 h-8 rounded-lg bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="x" class="w-4 h-4 text-dc-text"></i></button></div></div>' +
      '<div class="mx-4 mt-4 p-3 rounded-lg border ' + b.cls + ' flex items-center gap-2"><span class="text-base">' + b.icon + '</span><div>' +
      '<span class="text-[10px] font-black uppercase tracking-widest">' + (vs.label || 'Pending') + '</span>' +
      '<span class="text-[10px] ml-2 opacity-80">' + (vs.detail || '') + '</span></div></div>' +
      '<div class="flex flex-1 overflow-hidden mt-4 mx-4 mb-4 gap-4" style="min-height:0">' +
      '<div class="flex-1 flex flex-col bg-dc-bg border border-dc-border rounded-xl overflow-hidden">' +
      '<div class="flex items-center justify-between p-3 border-b border-dc-border bg-dc-panel/50"><div class="flex items-center gap-2">' +
      '<i data-lucide="image" class="w-3.5 h-3.5 text-theme"></i><span class="text-[10px] font-bold text-white uppercase tracking-widest">Evidence Viewer</span>' + evTabsHtml + '</div>' +
      '<div class="flex items-center gap-1">' +
      '<button onclick="TOC.matches.zoomEvidence(-1)" class="w-6 h-6 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="zoom-out" class="w-3 h-3 text-dc-text"></i></button>' +
      '<span id="verify-zoom-level" class="text-[9px] font-mono text-dc-text w-10 text-center">100%</span>' +
      '<button onclick="TOC.matches.zoomEvidence(1)" class="w-6 h-6 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="zoom-in" class="w-3 h-3 text-dc-text"></i></button>' +
      '<button onclick="TOC.matches.resetZoom()" class="w-6 h-6 rounded bg-dc-bg border border-dc-border flex items-center justify-center hover:bg-white/5"><i data-lucide="maximize-2" class="w-3 h-3 text-dc-text"></i></button></div></div>' +
      '<div id="evidence-canvas" class="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing flex items-center justify-center bg-black/40" onmousedown="TOC.matches.startPan(event)" onmousemove="TOC.matches.doPan(event)" onmouseup="TOC.matches.endPan()" onmouseleave="TOC.matches.endPan()" onwheel="TOC.matches.wheelZoom(event)">' +
      evidenceHtml + '</div></div>' +
      '<div class="w-[380px] flex-shrink-0 flex flex-col gap-4 overflow-y-auto pr-1">' +
      '<div class="bg-dc-surface border border-dc-border rounded-xl overflow-hidden"><div class="p-3 border-b border-dc-border bg-dc-panel/50 flex items-center gap-2"><i data-lucide="git-compare" class="w-3.5 h-3.5 text-theme"></i><span class="text-[10px] font-bold text-white uppercase tracking-widest">Submitted Scores</span></div>' +
      '<div class="p-4 space-y-3">' + subsHtml + '</div></div>' +
      '<div class="bg-dc-surface border border-dc-border rounded-xl overflow-hidden"><div class="p-3 border-b border-dc-border bg-dc-panel/50 flex items-center gap-2"><i data-lucide="target" class="w-3.5 h-3.5 text-theme"></i><span class="text-[10px] font-bold text-white uppercase tracking-widest">Final Score</span></div>' +
      '<div class="p-4"><div class="grid grid-cols-2 gap-3"><div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">' + (m.participant1_name || 'Team A') + '</label>' +
      '<input id="verify-p1" type="number" value="' + (sub0.score_p1 != null ? sub0.score_p1 : m.participant1_score) + '" min="0" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-sm font-mono text-center font-bold focus:border-theme outline-none"></div>' +
      '<div><label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">' + (m.participant2_name || 'Team B') + '</label>' +
      '<input id="verify-p2" type="number" value="' + (sub0.score_p2 != null ? sub0.score_p2 : m.participant2_score) + '" min="0" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2.5 text-white text-sm font-mono text-center font-bold focus:border-theme outline-none"></div></div></div></div>' +
      '<textarea id="verify-notes" rows="2" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none" placeholder="Optional admin note ..."></textarea>' +
      '<div class="space-y-2">' +
      '<button onclick="TOC.matches.verifyAction(' + id + ', \'confirm\')" class="w-full py-3 bg-dc-success text-dc-bg text-xs font-black uppercase tracking-widest rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2 ' +
      (m.state === 'completed' ? 'opacity-40 pointer-events-none' : '') + '">' + String.fromCodePoint(0x2705) + ' Confirm & Finalize</button>' +
      '<button onclick="TOC.matches.verifyAction(' + id + ', \'dispute\')" class="w-full py-3 bg-dc-danger/20 border border-dc-danger/30 text-dc-danger text-xs font-black uppercase tracking-widest rounded-xl hover:bg-dc-danger/30 transition-colors flex items-center justify-center gap-2 ' +
      (m.state === 'disputed' ? 'opacity-40 pointer-events-none' : '') + '">' + String.fromCodePoint(0x274C) + ' Open Dispute</button>' +
      '<button onclick="TOC.matches.verifyAction(' + id + ', \'note\')" class="w-full py-3 bg-dc-panel border border-dc-border text-dc-textBright text-xs font-black uppercase tracking-widest rounded-xl hover:bg-white/5 transition-colors flex items-center justify-center gap-2">' + String.fromCodePoint(0x1F4DD) + ' Add Admin Note</button>' +
      '</div></div></div></div>';

    showFullOverlay('verify-overlay', html);
  }

  function switchEvidence(idx) {
    if (!_verifyDetail) return;
    var subs = _verifyDetail.submissions || [];
    var media = (_verifyDetail.media || []).filter(function(x) { return x.is_evidence; });
    var sources = [];
    subs.forEach(function(s) { if (s.proof_screenshot_url) sources.push(s); });
    media.forEach(function(x) { sources.push(x); });
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
    document.querySelectorAll('[id^="ev-tab-"]').forEach(function(el, i) {
      el.className = i === idx
        ? 'px-2 py-0.5 rounded text-[9px] font-bold transition-colors bg-theme text-dc-bg'
        : 'px-2 py-0.5 rounded text-[9px] font-bold transition-colors bg-dc-bg border border-dc-border text-dc-text hover:text-white';
    });
  }

  function zoomEvidence(dir) { _zoomScale = Math.max(0.25, Math.min(5, _zoomScale + dir * 0.25)); applyTransform(); }
  function resetZoom() { _zoomScale = 1; _panX = 0; _panY = 0; applyTransform(); }
  function wheelZoom(e) { e.preventDefault(); zoomEvidence(e.deltaY < 0 ? 1 : -1); }
  function startPan(e) { _isPanning = true; _panStartX = e.clientX - _panX; _panStartY = e.clientY - _panY; }
  function doPan(e) { if (!_isPanning) return; _panX = e.clientX - _panStartX; _panY = e.clientY - _panStartY; applyTransform(); }
  function endPan() { _isPanning = false; }

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

  /* --- Overlay helpers -------------------------------------- */
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

  /* --- Keyboard Navigation --------------------------------- */
  function handleKeyboard(e) {
    var matchesTab = $('#view-matches');
    if (!matchesTab || matchesTab.classList.contains('hidden-view')) return;

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
  }

  /* --- Init ------------------------------------------------ */
  function init() {
    refresh();
    switchDetailTab('score');
  }

  document.addEventListener('keydown', handleKeyboard);

  window.TOC = window.TOC || {};
  window.TOC.matches = {
    init: init, refresh: refresh, debouncedRefresh: debouncedRefresh,
    selectMatch: selectMatch, filterGroup: filterGroup,
    switchDetailTab: switchDetailTab,
    markLive: markLive, pause: pause, resume: resume, forceComplete: forceComplete,
    submitScore: submitScore, openDispute: openDispute, resetMatch: resetMatch,
    openScoreDrawer: openScoreDrawer, openDetailDrawer: openDetailDrawer,
    openRescheduleModal: openRescheduleModal, confirmReschedule: confirmReschedule,
    openForfeit: openForfeit, confirmForfeit: confirmForfeit,
    openVerifyScreen: openVerifyScreen, verifyAction: verifyAction,
    switchEvidence: switchEvidence, zoomEvidence: zoomEvidence, resetZoom: resetZoom, wheelZoom: wheelZoom,
    startPan: startPan, doPan: doPan, endPan: endPan,
    closeOverlay: closeOverlay,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'matches') init();
  });
})();
