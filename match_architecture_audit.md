# Match Architecture Audit

Date: 2026-03-14
Scope: Existing match, tournament result, dispute, and stats architecture across tournaments, tournament_ops, competition, leaderboards, and user_profile.
Constraint: Audit-only. No code or migration changes.

## Executive Summary

The codebase currently has three active/overlapping match-result ecosystems:

1. Tournament match lifecycle + legacy dispute path
2. TournamentOps submission/verification/review-inbox pipeline
3. Competition self-reported match report workflow

All three can represent manual verification, but they use different status vocabularies, evidence schemas, and service entry points. This creates integration risk for Phase 10 Riot sync unless one canonical write path is selected.

Recommended canonical target for future automated ingestion:
- Use TournamentOps pipeline for verified tournament match finalization:
  - MatchResultSubmission
  - DisputeRecord / DisputeEvidence
  - ResultVerificationService finalization
  - Event-driven updates to leaderboards stats/history
- Keep GameProfile as profile/passport projection, not the canonical match result system.

## 1) Match Models and Locations

### A. Canonical tournament match lifecycle models

- apps/tournaments/models/match.py
  - Match
  - Core state machine: scheduled, check_in, ready, live, pending_result, completed, disputed, forfeit, cancelled
  - Core fields: participant1_id, participant2_id, participant1_score, participant2_score, winner_id, loser_id, lobby_info, started_at, completed_at, best_of, game_scores

- apps/tournaments/models/result_submission.py
  - MatchResultSubmission
  - Submission/verification queue around a Match
  - Statuses: pending, confirmed, disputed, auto_confirmed, finalized, rejected
  - Raw payload + proof fields + timing fields for opponent confirmation and organizer review

- apps/tournaments/models/dispute.py
  - DisputeRecord
  - Newer dispute record tied to MatchResultSubmission
  - Statuses: open, under_review, resolved_for_submitter, resolved_for_opponent, cancelled, escalated

- apps/tournaments/models/match.py
  - Dispute (legacy)
  - Deprecated in model docstring but still used by active service/API paths
  - Statuses: open, under_review, resolved, escalated

- apps/tournaments/models/result.py
  - TournamentResult
  - Final tournament placement/winner-level result object (post-match progression outcome)

### B. Parallel/adjacent match systems

- apps/competition/models/match_report.py
  - MatchReport (self-reported team-vs-team match records)

- apps/competition/models/match_verification.py
  - MatchVerification (confirmation/dispute/admin moderation for MatchReport)

- apps/user_profile/models_main.py
  - Match (legacy profile match-history model)
  - Separate from tournaments Match and leaderboards UserMatchHistory

## 2) Player Stats Models and Locations

### A. Match-level player performance (detailed)

- apps/tournaments/models/match_player_stats.py
  - MatchPlayerStat (per-player aggregated match stats)
  - MatchMapPlayerStat (per-player per-map stats)
  - Includes FPS metrics (kills/deaths/assists, ACS, ADR, HS%, etc.)

### B. Aggregated stats and ranking projections

- apps/leaderboards/models.py
  - UserStats (per-user per-game aggregates)
  - TeamStats (per-team per-game aggregates)
  - TeamRanking (ELO/rank snapshots)
  - UserMatchHistory (timeline entries for users)
  - TeamMatchHistory (timeline entries for teams)

- apps/user_profile/models/stats.py
  - UserProfileStats (event-derived profile projection from activity events)

### C. Passport-level sync projection (current Riot Phase 10 target)

- apps/user_profile/models_main.py
  - GameProfile stores compact identity/rank/stats fields plus metadata JSON projection

- apps/user_profile/tasks.py
  - Riot sync currently updates GameProfile.metadata live_stats and summary columns (matches_played, win_rate, kd_ratio, main_role)
  - Does not currently write canonical tournament match/result/dispute/stats tables

## 3) Manual Verification Workflows (Statuses + Evidence)

### Workflow 1: TournamentOps submission + organizer inbox (queue-style moderation)

Primary files:
- apps/tournament_ops/services/result_submission_service.py
- apps/tournament_ops/services/result_verification_service.py
- apps/tournament_ops/services/review_inbox_service.py
- apps/tournaments/models/result_submission.py
- apps/tournaments/models/dispute.py

Statuses in use:
- MatchResultSubmission: pending, confirmed, disputed, auto_confirmed, finalized, rejected
- DisputeRecord: open, under_review, resolved_for_submitter, resolved_for_opponent, cancelled, escalated

Evidence fields:
- MatchResultSubmission.proof_screenshot_url
- MatchResultSubmission.proof_screenshot
- DisputeEvidence.url
- DisputeEvidence.evidence_file
- DisputeEvidence.notes
- ResultVerificationLog.details (JSON audit trail)

Operational capability:
- Supports queue/inbox review and bulk organizer actions
- Supports auto-confirm deadlines and dispute workflows
- Supports explicit verification log trail

### Workflow 2: Direct tournament match service + legacy dispute

Primary files:
- apps/tournaments/services/match_service.py
- apps/tournaments/api/result_views.py
- apps/tournaments/models/match.py (legacy Dispute)

Statuses in use:
- Match.state transitions through pending_result/completed/disputed
- Legacy Dispute: open, under_review, resolved, escalated

Evidence fields:
- Result submission endpoint accepts evidence_url and notes
- Legacy Dispute stores evidence_screenshot and evidence_video_url

Operational capability:
- End-to-end participant submit -> confirm/dispute -> organizer resolution path exists
- Legacy but still actively routed and used

### Workflow 3: Competition self-reported report verification

Primary files:
- apps/competition/models/match_report.py
- apps/competition/models/match_verification.py
- apps/competition/services/match_report_service.py
- apps/competition/services/verification_service.py

Statuses in use:
- MatchVerification: PENDING, CONFIRMED, DISPUTED, ADMIN_VERIFIED, REJECTED

Evidence fields:
- MatchReport.evidence_url
- MatchReport.evidence_notes
- MatchVerification.dispute_reason
- MatchVerification.admin_notes

Operational capability:
- Independent report verification subsystem with confidence weighting

### API exposure confirms overlap

- apps/tournaments/api/urls.py currently routes both:
  - matches (MatchViewSet path)
  - results (ResultViewSet path)
  - organizer results inbox endpoints

This means multiple result/dispute paradigms are simultaneously reachable.

## 4) Integration Strategy for Phase 10 Riot Celery Sync

Goal: Integrate API-ingested Riot data into existing ecosystem without creating another parallel source of truth.

### A. Canonical target architecture

Use this canonical write path for tournament matches:

1. Candidate match correlation to an existing tournaments Match
2. Submission creation in MatchResultSubmission (source tagged as riot_api)
3. Verification/finalization via ResultVerificationService
4. Match finalization via tournament_ops MatchService.accept_match_result
5. Event-driven projection to leaderboards stats/history
6. Optional detailed per-player map stats in MatchPlayerStat / MatchMapPlayerStat

Keep this as projection-only:
- GameProfile.metadata live stats (for profile display and passport-centric UX)

### B. Recommended ingestion flow (no code yet; blueprint only)

1. Fetch and normalize Riot payload in current Celery task
2. Resolve platform identity (Riot PUUID -> local user/team linkage)
3. Correlate to an existing match in scope (tournament, participants, time window, game)
4. If correlated:
   - submit into TournamentOps result pipeline
   - attach provenance/evidence reference (riot match id/url and payload hash)
   - auto-verify/finalize under system actor policy
5. If not correlated:
   - keep in GameProfile projection only
   - enqueue for organizer/manual linking workflow (do not write canonical match completion)
6. On finalization, rely on existing event handlers to update UserStats/TeamStats/history

### C. Guardrails required before enabling automated canonical writes

1. Unify status vocabulary and state mapping between tournament_ops DTO layer and tournaments ORM state machine.
2. Resolve dispute status drift between service-level statuses and persisted DisputeRecord status choices.
3. Choose one canonical API/service path for result submission/finalization and deprecate overlapping entry points.
4. Enforce idempotency keying by external match id to prevent duplicate submissions/finalizations.
5. Define reconciliation policy when external Riot result conflicts with already-finalized local result.

### D. High-risk integration drifts observed

1. State mapping drift in tournament_ops:
   - MatchAdapter maps ORM live/pending_result -> DTO in_progress
   - ResultSubmissionService checks for DTO state values live/pending_result
   - This can block expected submission flow in tournament_ops path.

2. Dispute status drift:
   - DisputeService uses statuses such as resolved_custom, dismissed, auto_resolved
   - DisputeRecord and DisputeDTO validation currently define a narrower status set
   - This creates workflow inconsistency and potential validation/query mismatches.

3. Facade/signature drift:
   - TournamentOpsService has methods whose dispute-resolution signatures/documentation diverge from current DisputeService shape.

4. Parallel dispute models:
   - Legacy Dispute and newer DisputeRecord coexist and are used by different service/API paths.

## Suggested Canonicalization Plan (Architecture-Only)

1. Pick a single canonical result/dispute domain for tournament matches:
   - Recommended: MatchResultSubmission + DisputeRecord + ResultVerificationService.
2. Treat legacy Dispute and competition MatchReport flows as adapters or separate product tracks, not co-equal canonical tournament result systems.
3. Define one event contract for match completion consumed by stats/history services.
4. Make GameProfile sync explicitly read-model/projection, with optional backfill into canonical match domain only when correlation is strong.

## Deliverable Notes

- This document is audit-only.
- No code edits, migrations, or schema changes were applied as part of this report.
