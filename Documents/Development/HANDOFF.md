# OwnLobby conversation handoff

Snapshot: 2026-11-05 21:05 +06:00 (Asia/Dhaka), OL-INC-01-A **BLOCKED**. Start with [STATUS](STATUS.md) for evidence dates and [BACKLOG](BACKLOG.md) for canonical task state. **Do not deploy master.** This brief is not authorization to modify production.

## Current state

- Repository `rkRashik/DeltaCrown`, default `master`; verified/synchronized baseline **`bec5a17b572c25e2d6e30d348c755332ea9e5ae2`**, merged PR #42 including follow-ups. Master contains PR #41's homepage optimization. Task branch `fix/ol-inc-01-a-asgi-cancellation`, [PR #43](https://github.com/rkRashik/DeltaCrown/pull/43), updates only asgiref to 3.12.1 plus synthetic tests/CI/docs; not merged/deployed.
- Production [ownlobby.com](https://ownlobby.com) is independently verified on rollback artifact **`f1f8d18566723aa4e62875c20f7f6bc8dc4794e1`** via read-only [Render](https://dashboard.render.com/web/srv-d6eubkngi27c738ieao0), deploy `dep-dbhufde7bikc738137sg`, completed 2026-10-30 06:42:19 +06:00. Owner reports navigation recovered. Master and production intentionally differ; no deploy/rollback was performed by this investigation.
- **New read-only evidence after the original incident review:** On 2026-10-30 evening, while the rollback artifact was still live, multiple routes showed Daphne shutdown-timeout warnings around 19:51 +06:00, then a Render TCP port timeout at 19:56:15 with recovery at 19:56:58. The [STATUS addendum](STATUS.md#evening-recurrence-on-the-rolled-back-release-read-only-follow-up-2026-10-30) records what is confirmed and remains uncertain. Keep master undeployed; prioritize the shared ASGI cancellation fix with Linux/Python 3.11 and memory/thread regression gates.
- Django/PostgreSQL, Daphne/Channels, Redis/Upstash, Cloudinary and private Supabase Storage. Database access is through Django PostgreSQL connections; Storage APIs are separate from the database Data API. No required database Data API consumer was found in inspected application code.
- **OL-01 remains VERIFYING.** Owner reports Data API OFF/disabled. At 23:12 +06:00 both valid public credential types received HTTP 503 / API connection-schema-cache failure: refusal observed, disabled-specific cause not independently proven. Six public routes, two public images and a local-client constant-only read-only DB check passed. Owner-confirmed Render follow-up reconfirmed live `f1f8d185`, Free/auto-deploy OFF and no matching errors in the bounded log queries. Provider-state reinspection, authenticated/private-media checks and permanent hardening remain open. No confirmed sensitive-data extraction/exploitation. Keep Data API disabled; no RLS/grant changes.
- Celery remains OFF; earlier lifecycle cron success is not evidence that every background job executes. R2 is an unapproved candidate; free/low cost, private media and safe rollback remain mandatory.
- Older engineering/release reports contain pre-launch state. Preserve their evidence but use dated STATUS and newer issue/commit evidence for current planning.

## Next safe task and blockers

**Next safe task: owner review of the connection-cleanup blocker, then separately scope a focused cancellation/connection-lifetime correction.** [Implementation evidence](STATUS.md#ol-inc-01-a-implementation-2026-11-05): Windows candidate passes, but Linux Python 3.12 candidate and Python 3.11 old control retain three child-tagged DB connections after 8 s. Threads/request executors are gone. Candidate Python 3.11 and later functional/security suites were skipped. Do not relax assertions, force GC or add a speculative view/DB workaround. PR #43 remains draft/BLOCKED; release planning remains blocked. November 3/4 production recurrences are independently confirmed, while exact production causality remains moderate-confidence.

OL-INC-01 and OL-04 remain VERIFYING; OL-03 stays IN_PROGRESS. Historical OL-04-B local tests and final pre-merge Linux run #62 passed, but did not exercise this cancellation scenario. Preserve [OL-04-B evidence](STATUS.md#ol-04-b-isolated-verification-2026-10-30) and [OL-03/04-A](tasks/OL-03-04-A.md); neither certifies current production acceptance. CI correction `a9a87bc6` remains useful and does not resolve OL-02's key warning. Rollback options are in [BACKLOG](BACKLOG.md#ol-04); even live `f1f8d185` contains the shared ASGI risk. No broad cleanup: the three baseline root-placement findings remain future OL-14 candidates only, not approval to move/delete records.

**OL-01 remains urgent independently:** obtain current disabled-state confirmation and owner-driven existing-account/private-file checks, then separately approve permanent hardening. The [A-G matrix](STATUS.md#ol-01-verification-2026-10-29) and [proposal](BACKLOG.md#ol-01-permanent-hardening-proposal-not-executed) remain authoritative; do not repeat the security audit or re-enable Data API.

Other open work: signing-key warning/CI coverage, Render resource and homepage/image measurements, supported async jobs, complete eFootball QA, mobile/accessibility, rebrand review, Search Console/public Google actions and full launch acceptance. Exact dependencies and criteria are in BACKLOG; roadmap milestones are gates rather than delivery-date promises.

## Operating constraints

- Read [AGENTS](../../AGENTS.md); preserve settings IDs/forms/CSRF/AJAX and read the protected settings specification before any redesign. Never publish owner documents to satisfy a broken link.
- Public Git must contain no secrets, sensitive inventories, raw private logs, exploit examples or user/media evidence. An approved private OL-01 evidence URL has not been supplied; request it privately if needed.
- Isolated local/CI tests only. No production migrations, deployments, configuration changes, media publication/deletion or paid service activation from this handoff.
- Keep existing auth, financial, technical-ID and media privacy boundaries. Never roll back to public confidential-media delivery or set verification flags merely to clear a gate.
- R2 research must compare current delivery/costs and evaluate 8/9 GB warning thresholds, blocking below the free allowance, operation charges and ongoing billing. No provider hard cap is assumed.

## Copyable continuation: Codex

```text
Continue OwnLobby from Documents/Development/README.md, STATUS.md, HANDOFF.md
and BACKLOG.md. Read AGENTS.md and repository policy first. Inspect actual
branch/HEAD, working tree, current master and relevant Issue #37/PR evidence.
Preserve the stable OL task IDs and all owner-protected documents.
PR #42 is merged: baseline master bec5a17b. Production remains f1f8d185.
DO NOT DEPLOY MASTER. Read OL-INC-01 evidence in STATUS and BACKLOG first.
The shared ASGI cancellation stall reproduced locally in both releases;
production attribution remains moderate-confidence, not a proven homepage bug.
OL-INC-01-A is implemented in PR #43 (fix/ol-inc-01-a-asgi-cancellation).
Read STATUS's implementation evidence and verify the reviewed SHA's Linux
3.11.9/3.12 checks and the precise three-connection cleanup failure in runs
#66/#67. PR #43 is draft/BLOCKED. Candidate 3.11 and later security suites did
not execute; skipped is not PASS. Next: scoped connection-lifetime follow-up
after owner review. No deployment or production changes are authorized.
Keep raw diagnostics/private evidence outside public Git. Do not repeat audits.
OL-01 also remains open: owner disabled Data API on 2026-10-29. Valid-key
requests were refused; public smoke/direct DB checks and bounded Render log
review passed. Provider-state/private-browser evidence and hardening remain open.
Read the STATUS A-G matrix before selecting further checks. Keep Data API
disabled and evidence private. No sensitive-row extraction, grant/RLS
changes, deployments, migrations or provider/media changes without separate
authorization. Do not infer production success from source or historical CI.
For completed work update BACKLOG, STATUS, CHANGELOG, relevant DECISIONS and
HANDOFF in the same reviewed PR. Stage explicit public paths only.
```

## Copyable continuation: ChatGPT

```text
Use the latest OwnLobby Development workspace from rkRashik/DeltaCrown as the
planning record. Read README, STATUS, BACKLOG and HANDOFF before proposing work.
If repository/private evidence is unavailable, request the latest sanitized
documents and state that you cannot verify live status. Do not ask for secrets.
OL-01 has owner-applied containment, observed refusal and public smoke evidence;
provider-state/private-browser checks and permanent hardening remain open.
Do not mark it DONE or suggest
re-enabling it. Plan the next scoped verification task, distinguish proposals
from approved decisions, and preserve the existing task IDs and safety gates.
```
