# Match State Contract (Phase 10.1 Blueprint)

## 1. Purpose

Define a single canonical state contract for match lifecycle, result submission lifecycle, and dispute lifecycle.

This contract is the source of truth for:
- ORM models
- TournamentOps DTOs
- TournamentOps services
- Public and internal API schemas
- Background workflows (including Riot ingestion)

This is a blueprint document only. No migrations or runtime refactors are included here.

## 2. Canonical Ownership

- Match lifecycle owner: `tournaments.Match.state`
- Submission lifecycle owner: `tournaments.MatchResultSubmission.status`
- Dispute lifecycle owner: `tournaments.DisputeRecord.status`

All adapters, DTOs, API serializers, and schema components must mirror these owners exactly.

## 3. Canonical Enums

### 3.1 MatchState (canonical)

Allowed values:
- `scheduled`
- `check_in`
- `ready`
- `live`
- `pending_result`
- `completed`
- `disputed`
- `forfeit`
- `cancelled`

### 3.2 ResultSubmissionState (canonical)

Allowed values:
- `pending`
- `confirmed`
- `disputed`
- `auto_confirmed`
- `finalized`
- `rejected`

### 3.3 DisputeState (canonical)

Allowed values:
- `open`
- `under_review`
- `escalated`
- `resolved_for_submitter`
- `resolved_for_opponent`
- `resolved_custom`
- `dismissed`

## 4. Canonical Transition Rules

### 4.1 MatchState transitions

- `scheduled -> check_in | ready | cancelled`
- `check_in -> ready | forfeit | cancelled`
- `ready -> live | cancelled`
- `live -> pending_result | forfeit | cancelled`
- `pending_result -> completed | disputed | cancelled`
- `disputed -> pending_result | completed | cancelled`
- `forfeit` is terminal
- `completed` is terminal
- `cancelled` is terminal

### 4.2 ResultSubmissionState transitions

- `pending -> confirmed | disputed | auto_confirmed | rejected`
- `confirmed -> finalized | rejected`
- `auto_confirmed -> finalized | rejected`
- `disputed -> finalized | rejected | pending` (pending only when dispute is dismissed)
- `finalized` is terminal
- `rejected` is terminal

### 4.3 DisputeState transitions

- `open -> under_review | escalated | resolved_for_submitter | resolved_for_opponent | resolved_custom | dismissed`
- `under_review -> escalated | resolved_for_submitter | resolved_for_opponent | resolved_custom | dismissed`
- `escalated -> resolved_for_submitter | resolved_for_opponent | resolved_custom | dismissed`
- `resolved_for_submitter` is terminal
- `resolved_for_opponent` is terminal
- `resolved_custom` is terminal
- `dismissed` is terminal

## 5. Required Alias Compatibility (Temporary)

Aliases are compatibility-only and must not remain as canonical persistence values.

| Legacy value | Canonical target | Scope | Sunset rule |
|---|---|---|---|
| `in_progress` | `live` or `pending_result` | DTO/API read layer | Remove after all consumers switch to explicit states |
| `pending` (MatchDTO) | `scheduled`/`check_in`/`ready` | DTO/API read layer | Remove after adapter and DTO align to MatchState |
| `cancelled` (DisputeState legacy) | `dismissed` | dispute APIs and DTOs | Remove once clients emit/consume `dismissed` |
| `resolved` (generic dispute) | `resolved_for_submitter` or `resolved_for_opponent` or `resolved_custom` | old dispute APIs | Remove after explicit ruling contract rollout |
| `auto_resolved` | `dismissed` | dispute service cleanup path | Remove after cleanup of close-related-disputes flow |

Alias policy:
- Write path must persist canonical values only.
- Read path may emit aliases only behind explicit compatibility flag.
- API docs must label aliases as deprecated from day one of rollout.

## 6. Current Drift to Eliminate

### 6.1 Match state drift

- `apps/tournament_ops/dtos/match.py` allows only `pending`, `in_progress`, `completed`, `disputed`.
- `apps/tournament_ops/adapters/match_adapter.py` collapses ORM states (`scheduled/check_in/ready/live/pending_result`) into DTO aliases.
- `apps/tournament_ops/services/match_service.py` and adjacent service logic still rely on collapsed DTO values.
- `apps/api/schema/spectacular_extensions.py` still publishes `in_progress` enum values.

### 6.2 Dispute state drift

- `apps/tournament_ops/services/dispute_service.py` writes statuses including `resolved_custom`, `dismissed`, and `auto_resolved`.
- `apps/tournament_ops/dtos/dispute.py` and `apps/tournaments/models/dispute.py` currently permit older status sets (`cancelled`-oriented) and do not consistently include all runtime values.

### 6.3 API contract drift

- `apps/tournaments/api/matches.py` and `apps/tournaments/api/result_views.py` both expose overlapping result/dispute endpoints with different semantics.
- API schemas document simplified states that do not reflect full Match and Dispute lifecycles.

## 7. Contract Application Matrix

Each layer must use the same enum source:

- ORM models: canonical values persisted.
- Adapters: no lossy state collapsing.
- DTO validators: canonical values only (aliases optional for parse-only, never store).
- Services: transition checks against canonical transitions in this document.
- API serializers/views: canonical values in requests and responses.
- OpenAPI schema: canonical enums with deprecation markers for temporary aliases.
- Metrics/events: payload values canonicalized before emit.

## 8. Non-Negotiable Invariants

- A `finalized` submission implies match state is `completed` or `forfeit`.
- A match in `disputed` must have at least one non-terminal dispute record.
- Dispute terminal states must set `resolved_at`.
- `dismissed` dispute must push related submission back to `pending` with a fresh auto-confirm deadline.
- No state alias may be persisted in canonical DB fields.

## 9. Implementation Guardrails (for later execution)

- Add centralized enum modules for MatchState, ResultSubmissionState, DisputeState.
- Replace string literals in DTO/service layers with enum constants.
- Add contract tests:
  - enum parity tests (ORM vs DTO vs schema)
  - transition table tests
  - alias parse-only tests
- Add schema snapshot tests to prevent reintroduction of alias-only enums.

## 10. Out of Scope (This Phase)

- Database migrations
- Runtime code deletions
- Endpoint removals
- Data backfill scripts

These will follow after approval of this contract and deprecation plan.
