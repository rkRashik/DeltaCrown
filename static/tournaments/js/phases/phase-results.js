/**
 * phase-results.js — Results Submission phase module
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  function renderOpponentSubmission(c, submission) {
    if (!submission) return '<p class="text-xs text-gray-400 mt-4">Waiting for opponent submission.</p>';
    var row = c.asObject(submission);
    var proof = String(row.proof_screenshot_url || '').trim();
    if (c.bool(row.blind_masked, false)) {
      return '<div class="mt-4 space-y-2">' +
        '<p class="text-sm text-white font-semibold">Opponent has submitted.</p>' +
        '<p class="text-xs text-gray-400">Score is hidden for participants. Only admin can view opponent score.</p>' +
        '<p class="text-xs text-gray-500">Submitted at ' + c.esc(c.shortClock(row.submitted_at)) + '</p></div>';
    }
    return '<div class="mt-4 space-y-2">' +
      '<p class="text-sm text-white font-semibold">Score: ' + c.esc(String(row.score_for || 0)) + ' - ' + c.esc(String(row.score_against || 0)) + '</p>' +
      '<p class="text-xs text-gray-400">Submitted at ' + c.esc(c.shortClock(row.submitted_at)) + '</p>' +
      (proof ? '<p class="text-xs text-gray-400">Proof: <a class="text-ac underline" href="' + c.esc(proof) + '" target="_blank" rel="noopener">Open image</a></p>' : '') + '</div>';
  }

  function renderResultStatusBanner(c) {
    var workflow = c.asObject(c.state.room.workflow);
    var status = String(workflow.result_status || 'pending').toLowerCase();
    if (status === 'verified' || status === 'admin_overridden' || status === 'verified_draw' || status === 'admin_overridden_draw') {
      return '<p class="mt-4 px-3 py-2 rounded-lg bg-green-500/15 border border-green-400/30 text-xs text-green-300 font-bold uppercase tracking-wide">Result verified.</p>';
    }
    if (status === 'mismatch' || status === 'tie_pending_review' || status === 'admin_tie_pending_review') {
      return '<p class="mt-4 px-3 py-2 rounded-lg bg-amber-500/15 border border-amber-400/30 text-xs text-amber-200 font-bold uppercase tracking-wide">Awaiting staff review.</p>';
    }
    return '<p class="mt-4 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs text-gray-300 font-bold uppercase tracking-wide">Pending validation.</p>';
  }

  window.MatchRoom.registerPhase('results', {
    label: function () { return 'Results'; },
    narrative: function (c) {
      if (c && c.requiresMatchEvidence && c.requiresMatchEvidence()) {
        return 'Blind-submit your scoreline with required image evidence, then wait for verification.';
      }
      return 'Blind-submit your scoreline with optional proof and wait for verification.';
    },

    render: function (c) {
      var side = c.mySide();
      var me = c.asObject(c.state.room.me);
      var visibility = c.workflowResultVisibility();
      var canSubmit = c.bool(me.can_submit_result, false) && (side === 1 || side === 2);
      var submission = side ? c.workflowSubmission(side) : null;
      var oppSubmission = side ? c.workflowSubmission(c.opponentSide()) : null;
      var hasSubmitted = Boolean(submission && (submission.submission_id || submission.submitted_at));

      var scoreFor = submission ? c.toInt(submission.score_for, 0) : 0;
      var scoreAgainst = submission ? c.toInt(submission.score_against, 0) : 0;
      var note = submission ? String(submission.note || '') : '';
      var proof = submission ? String(submission.proof_screenshot_url || '') : '';
      var evidenceRequired = c.requiresMatchEvidence();

      var blindCopy = c.bool(visibility.opponent_revealed, false)
        ? 'Admin view active. Opponent submission details are visible here.'
        : 'Blind mode is active. Opponent score is hidden from participants and visible to admins only.';
      var evidenceCopy = evidenceRequired
        ? 'Organizer policy requires an evidence image upload before score submission.'
        : 'Attach an evidence image if available. External proof URL is optional.';

      var myStatus = submission ? String(submission.status || 'submitted') : 'pending';
      var oppStatus = oppSubmission ? String(oppSubmission.status || 'submitted') : 'pending';
      var submitDisabled = !(canSubmit && !c.waitingLocked() && !c.state.requestBusy);
      var lockHint = hasSubmitted
        ? '<p class="mt-3 text-[11px] text-amber-200">Your result is locked after first submission. Contact admin for corrections.</p>'
        : '';

      return '<section class="glass-panel rounded-2xl p-5 md:p-7 border-t-4 border-ac">' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Result Desk</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white">Result Submission</h3>' +
        '<p class="text-xs text-gray-400 mt-2">' + c.esc(blindCopy) + '</p>' +
        '<p class="text-[11px] text-gray-500 mt-1">' + c.esc(evidenceCopy) + '</p>' +
        '<div class="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-4">' +

        // My submission form
        '<form id="result-submit-form" class="rounded-xl border border-white/10 bg-black/45 p-4">' +
        '<div class="flex items-center justify-between">' +
        '<p class="text-xs font-bold text-white">Your Submission</p>' +
        '<span class="text-[10px] uppercase tracking-widest text-ac">' + c.esc(myStatus) + '</span></div>' +
        '<div class="mt-4 flex items-center gap-3">' +
        '<label class="text-xs text-gray-400 flex-1">Your Score' +
        '<input id="result-score-for" type="number" min="0" class="score-input mt-1" value="' + c.esc(String(scoreFor)) + '" ' + (canSubmit ? '' : 'disabled') + ' /></label>' +
        '<label class="text-xs text-gray-400 flex-1">Opponent Score' +
        '<input id="result-score-against" type="number" min="0" class="score-input mt-1" value="' + c.esc(String(scoreAgainst)) + '" ' + (canSubmit ? '' : 'disabled') + ' /></label></div>' +
        '<label class="block text-xs text-gray-400 mt-3">Evidence Image ' + (evidenceRequired ? '(required)' : '(optional)') +
        '<input id="result-proof-file" type="file" accept="image/*" class="lobby-input mt-1 py-2.5" ' + (canSubmit ? (evidenceRequired ? 'required' : '') : 'disabled') + ' /></label>' +
        '<label class="block text-xs text-gray-400 mt-3">Proof URL (optional)' +
        '<input id="result-proof-url" class="lobby-input mt-1" value="' + c.esc(proof) + '" ' + (canSubmit ? '' : 'disabled') + ' /></label>' +
        (proof ? '<p class="mt-2 text-[11px] text-gray-400">Current proof: <a class="text-ac underline" href="' + c.esc(proof) + '" target="_blank" rel="noopener">Open image</a></p>' : '') +
        '<label class="block text-xs text-gray-400 mt-3">Note' +
        '<textarea id="result-note" class="lobby-input mt-1 min-h-[72px]" ' + (canSubmit ? '' : 'disabled') + '>' + c.esc(note) + '</textarea></label>' +
        lockHint +
        '<div class="mt-4 flex justify-end">' +
        '<button type="submit" class="px-4 py-2.5 rounded-lg bg-ac text-black text-xs font-black uppercase tracking-wider ' + (submitDisabled ? 'opacity-50 cursor-not-allowed' : '') + '" ' + (submitDisabled ? 'disabled' : '') + '>' +
        (hasSubmitted ? 'Submitted' : 'Submit Result') + '</button></div></form>' +

        // Opponent submission panel
        '<div class="rounded-xl border border-white/10 bg-black/45 p-4">' +
        '<div class="flex items-center justify-between">' +
        '<p class="text-xs font-bold text-white">Opponent Submission</p>' +
        '<span class="text-[10px] uppercase tracking-widest text-amber-300">' + c.esc(oppStatus) + '</span></div>' +
        renderOpponentSubmission(c, oppSubmission) +
        renderResultStatusBanner(c) + '</div></div></section>';
    },

    onAction: async function () { return false; }
  });
})();
