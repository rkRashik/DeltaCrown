/**
 * phase-results.js — Results Submission phase module v20260405c
 *
 * Improved UX: visual score card, clear submission flow, live feedback.
 */
(function () {
  'use strict';
  if (!window.MatchRoom) return;

  function renderOpponentSubmission(c, submission) {
    if (!submission) {
      return '<div class="flex flex-col items-center justify-center py-6">' +
        '<div class="w-10 h-10 rounded-full bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-3 animate-pulse">' +
        '<i data-lucide="clock" class="w-5 h-5 text-gray-600"></i></div>' +
        '<p class="text-xs text-gray-500">Waiting for opponent to submit their score...</p></div>';
    }
    var row = c.asObject(submission);
    var proof = String(row.proof_screenshot_url || '').trim();
    if (c.bool(row.blind_masked, false)) {
      return '<div class="py-4 space-y-2 text-center">' +
        '<div class="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-2">' +
        '<i data-lucide="check" class="w-5 h-5 text-emerald-400"></i></div>' +
        '<p class="text-sm text-white font-semibold">Opponent submitted</p>' +
        '<p class="text-[10px] text-gray-500">Score hidden (blind mode) · ' + c.esc(c.shortClock(row.submitted_at)) + '</p></div>';
    }
    return '<div class="py-4 space-y-3 text-center">' +
      '<p class="text-3xl font-display font-black text-white tabular-nums">' + c.esc(String(row.score_for || 0)) + ' <span class="text-gray-600">-</span> ' + c.esc(String(row.score_against || 0)) + '</p>' +
      '<p class="text-[10px] text-gray-500">Submitted at ' + c.esc(c.shortClock(row.submitted_at)) + '</p>' +
      (proof ? '<a class="inline-flex items-center gap-1 text-[10px] text-ac hover:underline" href="' + c.esc(proof) + '" target="_blank" rel="noopener"><i data-lucide="image" class="w-3 h-3"></i> View proof</a>' : '') + '</div>';
  }

  function renderResultStatusBanner(c) {
    var workflow = c.asObject(c.state.room.workflow);
    var status = String(workflow.result_status || 'pending').toLowerCase();
    if (status === 'verified' || status === 'admin_overridden' || status === 'verified_draw' || status === 'admin_overridden_draw') {
      return '<div class="mt-4 flex items-center gap-2 px-3 py-2.5 rounded-lg bg-green-500/10 border border-green-500/20">' +
        '<i data-lucide="check-circle-2" class="w-4 h-4 text-green-400 shrink-0"></i>' +
        '<span class="text-xs text-green-300 font-bold uppercase tracking-wide">Result verified — match will finalize</span></div>';
    }
    if (status === 'mismatch' || status === 'tie_pending_review' || status === 'admin_tie_pending_review') {
      return '<div class="mt-4 flex items-center gap-2 px-3 py-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">' +
        '<i data-lucide="alert-triangle" class="w-4 h-4 text-amber-400 shrink-0"></i>' +
        '<span class="text-xs text-amber-200 font-bold uppercase tracking-wide">Score mismatch — awaiting staff review</span></div>';
    }
    return '<div class="mt-4 flex items-center gap-2 px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">' +
      '<i data-lucide="loader" class="w-4 h-4 text-gray-500 shrink-0 animate-spin"></i>' +
      '<span class="text-xs text-gray-400 font-bold uppercase tracking-wide">Pending validation — both sides must submit</span></div>';
  }

  window.MatchRoom.registerPhase('results', {
    label: function () { return 'Results'; },
    narrative: function (c) {
      if (c && c.requiresMatchEvidence && c.requiresMatchEvidence()) {
        return 'Submit your final score with required evidence. Score is blind until both submit.';
      }
      return 'Submit your final score. Score is blind until both sides submit.';
    },

    render: function (c) {
      var side = c.mySide();
      var me = c.asObject(c.state.room.me);
      var match = c.asObject(c.state.room.match);
      var p1 = c.asObject(match.participant1);
      var p2 = c.asObject(match.participant2);
      var canSubmit = c.bool(me.can_submit_result, false) && (side === 1 || side === 2);
      var submission = side ? c.workflowSubmission(side) : null;
      var oppSubmission = side ? c.workflowSubmission(c.opponentSide()) : null;
      var hasSubmitted = Boolean(submission && (submission.submission_id || submission.submitted_at));

      var scoreFor = submission ? c.toInt(submission.score_for, 0) : 0;
      var scoreAgainst = submission ? c.toInt(submission.score_against, 0) : 0;
      var note = submission ? String(submission.note || '') : '';
      var proof = submission ? String(submission.proof_screenshot_url || '') : '';
      var evidenceRequired = c.requiresMatchEvidence();
      var submitDisabled = !(canSubmit && !c.waitingLocked() && !c.state.requestBusy);

      // Step indicator
      var step1Done = hasSubmitted;
      var step2Done = Boolean(oppSubmission && (oppSubmission.submission_id || oppSubmission.submitted_at));
      var stepHtml =
        '<div class="flex items-center gap-3 mb-5">' +
        '<div class="flex items-center gap-2">' +
        '<div class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black ' +
        (step1Done ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-ac/15 text-ac border border-ac/30') + '">' +
        (step1Done ? '<i data-lucide="check" class="w-3 h-3"></i>' : '1') + '</div>' +
        '<span class="text-[10px] font-bold ' + (step1Done ? 'text-emerald-400' : 'text-white') + ' uppercase tracking-wider">You</span></div>' +
        '<div class="h-px flex-1 ' + (step1Done ? 'bg-emerald-500/30' : 'bg-white/10') + '"></div>' +
        '<div class="flex items-center gap-2">' +
        '<div class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black ' +
        (step2Done ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-white/[0.05] text-gray-500 border border-white/10') + '">' +
        (step2Done ? '<i data-lucide="check" class="w-3 h-3"></i>' : '2') + '</div>' +
        '<span class="text-[10px] font-bold ' + (step2Done ? 'text-emerald-400' : 'text-gray-500') + ' uppercase tracking-wider">Opponent</span></div>' +
        '<div class="h-px flex-1 ' + (step1Done && step2Done ? 'bg-emerald-500/30' : 'bg-white/10') + '"></div>' +
        '<div class="flex items-center gap-2">' +
        '<div class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black ' +
        (step1Done && step2Done ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-white/[0.05] text-gray-500 border border-white/10') + '">' +
        '<i data-lucide="shield-check" class="w-3 h-3"></i></div>' +
        '<span class="text-[10px] font-bold ' + (step1Done && step2Done ? 'text-emerald-400' : 'text-gray-500') + ' uppercase tracking-wider">Verify</span></div></div>';

      return '<section class="rounded-2xl p-5 md:p-7 border border-white/10">' +
        '<p class="text-[10px] font-black uppercase tracking-widest text-gray-500">Result Phase</p>' +
        '<h3 class="text-xl md:text-2xl font-black text-white mt-1">Submit Final Score</h3>' +
        '<p class="text-xs text-gray-500 mt-1">Blind submit — scores are hidden until both sides submit.</p>' +
        '<div class="mt-5">' + stepHtml + '</div>' +

        '<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">' +

        // My submission
        '<form id="result-submit-form" class="rounded-xl border border-white/[0.08] bg-black/30 p-4">' +
        '<div class="flex items-center justify-between mb-4">' +
        '<p class="text-xs font-bold text-white">Your Score Report</p>' +
        (hasSubmitted ? '<span class="text-[9px] uppercase tracking-widest font-black text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-full border border-emerald-500/20">Submitted</span>' : '<span class="text-[9px] uppercase tracking-widest font-black text-ac bg-ac/10 px-2 py-1 rounded-full border border-ac/20">Pending</span>') +
        '</div>' +

        // Score card
        '<div class="flex items-center justify-center gap-4 py-3 px-2 rounded-xl bg-white/[0.02] border border-white/[0.05]">' +
        '<div class="flex-1 text-center">' +
        '<p class="text-[9px] text-gray-500 uppercase tracking-wider mb-1">You</p>' +
        '<input id="result-score-for" type="number" min="0" value="' + c.esc(String(scoreFor)) + '" ' + (canSubmit ? '' : 'disabled') +
        ' class="w-16 mx-auto block text-center text-2xl font-display font-black text-white bg-transparent border-b-2 border-white/20 focus:border-ac outline-none pb-1 tabular-nums" /></div>' +
        '<span class="text-sm font-black text-gray-600 pt-4">vs</span>' +
        '<div class="flex-1 text-center">' +
        '<p class="text-[9px] text-gray-500 uppercase tracking-wider mb-1">Opponent</p>' +
        '<input id="result-score-against" type="number" min="0" value="' + c.esc(String(scoreAgainst)) + '" ' + (canSubmit ? '' : 'disabled') +
        ' class="w-16 mx-auto block text-center text-2xl font-display font-black text-white bg-transparent border-b-2 border-white/20 focus:border-ac outline-none pb-1 tabular-nums" /></div></div>' +

        // Evidence
        '<div class="mt-4 space-y-3">' +
        '<label class="block text-[10px] font-bold text-gray-400 uppercase tracking-wider">Evidence ' + (evidenceRequired ? '<span class="text-red-400">*</span>' : '') +
        '<input id="result-proof-file" type="file" accept="image/*" class="lobby-input mt-1.5 py-2" ' + (canSubmit ? (evidenceRequired ? 'required' : '') : 'disabled') + ' /></label>' +
        '<label class="block text-[10px] font-bold text-gray-400 uppercase tracking-wider">Proof URL' +
        '<input id="result-proof-url" class="lobby-input mt-1.5" placeholder="https://..." value="' + c.esc(proof) + '" ' + (canSubmit ? '' : 'disabled') + ' /></label>' +
        (proof ? '<p class="text-[10px] text-gray-500">Attached: <a class="text-ac hover:underline" href="' + c.esc(proof) + '" target="_blank" rel="noopener">View</a></p>' : '') +
        '<label class="block text-[10px] font-bold text-gray-400 uppercase tracking-wider">Note' +
        '<textarea id="result-note" class="lobby-input mt-1.5 min-h-[60px]" placeholder="Match details..." ' + (canSubmit ? '' : 'disabled') + '>' + c.esc(note) + '</textarea></label></div>' +

        (hasSubmitted ? '<p class="mt-3 text-[10px] text-amber-300/80 flex items-center gap-1.5"><i data-lucide="lock" class="w-3 h-3"></i> Score locked. Contact admin to change.</p>' : '') +
        '<div class="mt-4 flex justify-end">' +
        '<button type="submit" class="px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider transition-all ' +
        (hasSubmitted ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 cursor-default' : (submitDisabled ? 'bg-white/[0.05] text-gray-500 border border-white/10 cursor-not-allowed' : 'bg-ac text-black hover:bg-ac/90 active:scale-95')) + '" ' +
        (submitDisabled || hasSubmitted ? 'disabled' : '') + '>' +
        (hasSubmitted ? '<i data-lucide="check" class="w-3.5 h-3.5 inline mr-1"></i>Submitted' : 'Submit Score') + '</button></div></form>' +

        // Opponent panel
        '<div class="rounded-xl border border-white/[0.08] bg-black/30 p-4">' +
        '<div class="flex items-center justify-between mb-2">' +
        '<p class="text-xs font-bold text-white">Opponent Score Report</p>' +
        (step2Done ? '<span class="text-[9px] uppercase tracking-widest font-black text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-full border border-emerald-500/20">Submitted</span>' : '<span class="text-[9px] uppercase tracking-widest font-black text-gray-500 bg-white/[0.03] px-2 py-1 rounded-full border border-white/[0.06]">Waiting</span>') +
        '</div>' +
        renderOpponentSubmission(c, oppSubmission) +
        '</div></div>' +

        renderResultStatusBanner(c) +
        '</section>';
    },

    onAction: async function () { return false; }
  });
})();
