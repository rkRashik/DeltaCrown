# Match Canonicalization Deprecation and Consolidation Plan (Phase 10.1 Blueprint)

## 1. Objective

Consolidate all match result and dispute writes into one canonical pipeline:

- `MatchResultSubmission`
- `DisputeRecord`
- `ResultVerificationService`

Canonical orchestration layer: `apps/tournament_ops`

This document specifies:
- exact legacy files/models/routes to deprecate or reroute
- phased cutover strategy with rollback controls
- Riot ingestion path that creates `MatchResultSubmission` with `source='riot_api'` and auto-finalizes through `ResultVerificationService`

This is a blueprint only. No migrations or code deletions are executed in this phase.

## 2. Canonical Pipeline (Target)

Write path (all producers):
1. Producer submits evidence/result payload
2. Canonical creation in `MatchResultSubmission` (`status='pending'`, tagged source)
3. Opponent/organizer automation updates status (`confirmed` / `auto_confirmed` / `disputed`)
4. `ResultVerificationService.finalize_submission_after_verification(...)`
5. Match finalized and events emitted (`MatchResultFinalizedEvent`, `match.completed`)

Dispute path:
1. Create `DisputeRecord`
2. Resolve via `DisputeService`
3. Finalize with `ResultVerificationService`
4. Persist terminal dispute status from canonical contract

## 3. Legacy Surface Inventory and Action Plan

## 3.1 Tournaments API overlap (deprecate or reroute)

### A. Hard-deprecate direct match result/dispute write endpoints

Files:
- `apps/tournaments/api/matches.py`
- `apps/tournaments/api/result_views.py`
- `apps/tournaments/api/result_serializers.py`
- `apps/tournaments/api/serializers_matches.py`

Endpoints to stop owning business logic:
- `POST /api/tournaments/matches/{id}/submit-result/`
- `POST /api/tournaments/matches/{id}/confirm-result/`
- `POST /api/tournaments/matches/{id}/dispute/`
- `POST /api/tournaments/matches/{id}/report-dispute/`
- `POST /api/tournaments/matches/{id}/resolve-dispute/`
- Any equivalent result routes currently exposed under the `ResultViewSet` router namespace

Target behavior after reroute:
- Views become thin facades into TournamentOps services only.
- No direct write to `Match`/legacy `Dispute` from these API views.

### B. Keep match lifecycle endpoints that are not duplicate result/dispute pipelines

`start`/`cancel` style operational endpoints may remain, but they must not bypass canonical submission/finalization/dispute flow.

## 3.2 Tournaments web views overlap (reroute)

Files:
- `apps/tournaments/views/result_submission.py`
- `apps/tournaments/urls.py` (player-facing submit/dispute URLs)

Routes:
- `/tournaments/<slug>/matches/<match_id>/submit-result/`
- `/tournaments/<slug>/matches/<match_id>/report-dispute/`

Target behavior:
- Continue serving current UI routes, but backend action must call TournamentOps facade methods only.
- Remove direct calls to legacy `apps.tournaments.services.match_service` result/dispute mutation methods.

## 3.3 Legacy tournaments service/model stack (deprecate)

Files and models:
- `apps/tournaments/services/match_service.py` (result/dispute mutation paths)
- `apps/tournaments/models/match.py` -> legacy `Dispute` model
- `apps/tournaments/admin_match.py` and `apps/admin/api/tournament_ops.py` legacy `Dispute` usages
- tests directly asserting legacy `Dispute` write paths

Action:
- Freeze legacy `Dispute` to read-only compatibility.
- Route all new disputes to `DisputeRecord`.
- Move admin and dashboard queries to canonical `DisputeRecord`/submission views.

## 3.4 Competition parallel subsystem (sunset)

Files:
- `apps/competition/urls.py`
- `apps/competition/views.py`
- `apps/competition/models/match_report.py`
- `apps/competition/models/match_verification.py`
- `apps/competition/services/match_report_service.py`
- `apps/competition/services/verification_service.py`

Routes to retire from match verification ownership:
- `/competition/matches/report/`
- `/competition/matches/<match_id>/confirm/`
- `/competition/matches/<match_id>/dispute/`

Action:
- Mark competition reporting as legacy and route tournament-related reports into TournamentOps submission flow.
- Preserve read-only historical views until migration completes.

## 3.5 Schema and DTO drift (must align)

Files:
- `apps/api/schema/spectacular_extensions.py`
- `apps/tournament_ops/dtos/match.py`
- `apps/tournament_ops/adapters/match_adapter.py`
- `apps/tournament_ops/dtos/dispute.py`
- `apps/tournament_ops/services/dispute_service.py`

Action:
- Replace collapsed aliases (`pending`, `in_progress`) with explicit match states.
- Ensure dispute DTO/model/service all include canonical terminal statuses (`resolved_custom`, `dismissed`).
- Remove service writes to non-canonical statuses (`auto_resolved`, generic `resolved`, legacy `cancelled` for dispute state).

## 4. Phased Cutover Plan

## Phase 0: Guardrails and contract lock

- Freeze canonical enum definitions and transition tables from `match_state_contract.md`.
- Add feature flags (off by default):
  - `TOURNAMENTOPS_RESULTS_CANONICAL_ENABLED`
  - `TOURNAMENTOPS_LEGACY_RESULTS_WRITE_BLOCK`
  - `TOURNAMENTOPS_COMPETITION_BRIDGE_ENABLED`
  - `RIOT_RESULT_INGESTION_ENABLED`

## Phase 1: Reroute without removing routes

- Existing legacy API/web endpoints remain available.
- Internals switch to TournamentOps facades for submission/dispute/finalization.
- Start emitting deprecation headers and structured logs for legacy entrypoints.

## Phase 2: Write freeze on legacy stores

- Block direct legacy writes in:
  - legacy `Dispute` model write paths
  - competition verification write paths for tournament flows
- Keep read APIs intact for compatibility.

## Phase 3: Consumer migration and schema cleanup

- Update OpenAPI to canonical enums only (aliases marked deprecated then removed).
- Move admin/reporting dashboards to canonical models.
- Migrate tests to canonical flows.

## Phase 4: Physical deprecation removal

- Remove legacy endpoint handlers and duplicate services.
- Remove legacy model usage once data migration/backfill is approved and complete.

## 5. Kill Switch and Rollback Strategy

If canonical path has runtime issues:
- Disable `TOURNAMENTOPS_RESULTS_CANONICAL_ENABLED` to route requests back to legacy handlers.
- Keep read-only compatibility for both stores during rollback window.
- Preserve idempotency keys and event logs to prevent double finalization on re-enable.

Rollback constraints:
- Rollback is valid only while dual-write is disabled.
- If dual-write is introduced later, rollback must reconcile divergence before reopening writes.

## 6. Riot Ingestion Blueprint (Celery -> Canonical Submission -> Auto Finalization)

## 6.1 Current entrypoints and constraints

Current Riot polling task surface:
- `apps/user_profile/tasks.py` (`sync_single_riot_passport`, `sync_all_active_riot_passports`)

Current constraint:
- `MatchResultSubmission` model does not yet have explicit `source` column.
- `ResultSubmissionService.submit_result(...)` expects participant user/team inputs and currently has participant-oriented validation.

Blueprint requirement:
- Introduce canonical ingestion path that persists source as `riot_api` and finalizes via `ResultVerificationService`.

## 6.2 Target ingestion sequence

1. Riot fetch
- Celery task pulls match list and details from Riot API.

2. Deterministic correlation to internal match
- Match candidate lookup by:
  - game slug (`valorant`)
  - participant team/player identity mapping (Riot PUUID to registered participant identity)
  - time window overlap against scheduled/started time
  - optional tournament context markers in match metadata
- If no reliable correlation, do not create submission.

3. Idempotency and dedupe
- Build ingestion fingerprint:
  - `provider=riot`
  - `region`
  - `riot_match_id`
  - `internal_match_id`
- If fingerprint already processed, return success-noop.

4. Canonical submission create
- Create `MatchResultSubmission` with:
  - `status='pending'`
  - source tag `source='riot_api'`
  - system actor identity (service user id)
  - normalized payload in `raw_result_payload`
  - ingestion metadata (riot ids, shard, fetched_at, fingerprint)

5. Auto-confirm path
- Set status to `auto_confirmed` for trusted Riot ingestion flow (or `confirmed` if policy requires explicit confidence gate).

6. Verification + finalization
- Call `ResultVerificationService.finalize_submission_after_verification(submission_id, resolved_by_user_id=SYSTEM_ACTOR_ID)`.
- Service validates schema, computes winner/loser, finalizes match, resolves open disputes if applicable.

7. Eventing and observability
- Emit `MatchResultSubmittedEvent` with source metadata.
- Emit `MatchResultFinalizedEvent` and `match.completed` via existing canonical publishers.
- Structured logs include correlation confidence, fingerprint, and submission id.

8. Failure handling
- If verification fails: keep submission in non-finalized state (`rejected` or `disputed` based on policy), push to organizer inbox for manual review.
- If correlation fails: write unmatched ingestion record and skip submission creation.

## 6.3 New internal components (to implement after approval)

- `RiotResultIngestionService` (new, in `apps/tournament_ops/services`)
  - responsibility: correlate + dedupe + create canonical submission + finalize
- `RiotMatchCorrelationAdapter` (new, in `apps/tournament_ops/adapters`)
  - responsibility: deterministic mapping from Riot payload to internal `Match`
- `RiotIngestionRepository` or equivalent dedupe store
  - responsibility: fingerprint persistence and replay safety

## 6.4 Required schema-level changes (future migration phase, not now)

Planned additions for canonical ingestion traceability:
- `MatchResultSubmission.source` (`manual`, `riot_api`, `admin_override`, ...)
- `MatchResultSubmission.ingestion_fingerprint` (unique for provider+match correlation)
- Optional `MatchResultSubmission.ingested_at`

No migration scripts are part of this phase.

## 7. Test and Telemetry Requirements for Cutover

Contract tests:
- enum parity (ORM vs DTO vs schema)
- transition legality for match/submission/dispute

Integration tests:
- legacy endpoints reroute into TournamentOps and no longer mutate legacy `Dispute`
- dispute resolution writes canonical terminal statuses
- riot ingestion creates `source='riot_api'` submission and auto-finalizes deterministically

Telemetry:
- counters by entrypoint (`legacy_api`, `tournament_ops_api`, `riot_ingestion`)
- state transition counters
- finalization failure rate and reason codes
- unmatched Riot correlation count
- duplicate ingestion no-op count

## 8. Exit Criteria

Canonicalization is complete when:
- all tournament and competition result/dispute writes go through TournamentOps canonical services
- OpenAPI publishes canonical enums only
- legacy `Dispute` and competition verification stack are read-only or removed
- Riot ingestion uses canonical submission + verification flow with idempotent dedupe
