# OwnLobby engineering roadmap

Baseline: 2026-10-29. Sequence is gate-driven, not a promised delivery calendar. [BACKLOG](BACKLOG.md) owns task status; [STATUS](STATUS.md) owns the dated snapshot.

| Phase / milestone | Priority and tasks | Dependencies | Exit gate |
|---|---|---|---|
| M0: Verify containment and security readiness | P0 OL-01; P0 OL-02 investigation | Owner-applied containment; privately scoped verification and runtime/CI evidence | External denial and compatibility documented; permanent hardening reviewed/applied/verified under separate approval; signing-key warning disposition supported; required CI actually runs |
| M1: Establish reliable performance baseline | P1 OL-03, OL-04, OL-05 | M0 takes priority; approved read-only measurement scope | Resource/error baseline and HTML/DB/cache/image breakdown; private-media boundary rechecked; numeric budgets agreed |
| M2: Make evidence-led delivery decisions | P2 OL-06 feasibility; P1 OL-07 if justified; P1 OL-08 design | OL-03/04/05; OL-06 only if provider change is considered | Owner selects affordable delivery/job design with rollback, capacity and cost controls. Implement only approved scope and verify against baseline |
| M3: Prove supported product journeys | P1 OL-09, OL-10, OL-11 | Isolated QA; OL-01/02 security gates; job behavior decision for async steps | eFootball/player/team/organizer/notification journey evidence, mobile/accessibility review, approved branding checks; no real financial smoke writes |
| M4: Public launch acceptance | P1 OL-12, OL-13 | M0 and required M1-M3 gates; owner/provider actions | Supported launch scope, signup/OAuth, privacy, performance, recovery and operational acceptance signed off; indexing state recorded without promises |

## Dependency rules

- Documentation upkeep never delays urgent approved security work. OL-01 verification is the immediate next task.
- OL-04 and OL-05 distinguish page-generation delay from media-transfer delay. Neither assumes R2 fixes both.
- OL-06 is optional research, not a launch prerequisite if existing providers meet the approved budget and performance gate. OL-07 can optimize current delivery without migrating providers.
- OL-08 investigation can proceed while Celery stays OFF. A lifecycle cron success does not prove all queued tasks execute.
- Isolated product QA may proceed alongside investigation, but public rollout cannot bypass security or privacy gates.
- OL-11 preserves identifiers and settings behavior. A settings redesign needs a separate explicit scope and the protected specification.
- OL-12 can prepare source checks early; owner-controlled Search Console/Google actions and verified public state are separate acceptance steps.

## Approval checkpoints

Owner approval is required for production changes, deployments, paid services, media publication/deletion or migrations. R2 quota safeguards, job architecture and numeric performance/recovery targets remain proposals until recorded in [DECISIONS](DECISIONS.md). Review staging evidence and rollback before requesting the concrete production action.

M0-M4 are incomplete. No roadmap milestone is completed merely because its source code or CI workflow exists. When a gate closes, link exact evidence in BACKLOG and append the dated milestone in [CHANGELOG](CHANGELOG.md).
