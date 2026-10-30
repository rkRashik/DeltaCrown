# OwnLobby conversation handoff

Snapshot: 2026-10-30 16:15 +06:00 (Asia/Dhaka), OL-INC-01. Start with [STATUS](STATUS.md) for evidence dates and [BACKLOG](BACKLOG.md) for canonical task state. **Do not deploy master.** This brief is not authorization to modify production.

## Current state

- Repository `rkRashik/DeltaCrown`, default `master`; verified/synchronized baseline **`7e07d6835f92a39a7cc4fb9ef3666f008a241b12`**, merged [PR #41](https://github.com/rkRashik/DeltaCrown/pull/41). It contains the homepage optimization. Incident documentation branch: `docs/ol-inc-01-navigation-hang-20261030`. PR #38's original head and earlier PR #41 heads are historical.
- Production [ownlobby.com](https://ownlobby.com) is independently verified on rollback artifact **`f1f8d18566723aa4e62875c20f7f6bc8dc4794e1`** via read-only [Render](https://dashboard.render.com/web/srv-d6eubkngi27c738ieao0), deploy `dep-dbhufde7bikc738137sg`, completed 2026-10-30 06:42:19 +06:00. Owner reports navigation recovered. Master and production intentionally differ; no deploy/rollback was performed by this investigation.
- Django/PostgreSQL, Daphne/Channels, Redis/Upstash, Cloudinary and private Supabase Storage. Database access is through Django PostgreSQL connections; Storage APIs are separate from the database Data API. No required database Data API consumer was found in inspected application code.
- **OL-01 remains VERIFYING.** Owner reports Data API OFF/disabled. At 23:12 +06:00 both valid public credential types received HTTP 503 / API connection-schema-cache failure: refusal observed, disabled-specific cause not independently proven. Six public routes, two public images and a local-client constant-only read-only DB check passed. Owner-confirmed Render follow-up reconfirmed live `f1f8d185`, Free/auto-deploy OFF and no matching errors in the bounded log queries. Provider-state reinspection, authenticated/private-media checks and permanent hardening remain open. No confirmed sensitive-data extraction/exploitation. Keep Data API disabled; no RLS/grant changes.
- Celery remains OFF; earlier lifecycle cron success is not evidence that every background job executes. R2 is an unapproved candidate; free/low cost, private media and safe rollback remain mandatory.
- Older engineering/release reports contain pre-launch state. Preserve their evidence but use dated STATUS and newer issue/commit evidence for current planning.

## Next safe task and blockers

**Next safe task: review OL-INC-01, then authorize OL-INC-01-A dependency/cancellation regression work.** [Incident evidence](STATUS.md#ol-inc-01-incident-investigation-2026-10-30): `/teams/` shutdown warning, platform restart, same-release availability/rendering before owner rollback. Both releases reproduce ASGI loop blockage under a synthetic slow-work/disconnect diagnostic; ordinary sequential/concurrent requests pass. A separately installed asgiref 3.12.1 candidate avoids that isolated stall. Production root-cause confidence is moderate: original DB/Redis wait and thread stack are missing. No direct homepage regression is proven and no application/dependency fix was applied. Review the narrow proposal and Linux/resource/security acceptance gates before implementation; keep master undeployed.

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
PR #41 is merged: master 7e07d683. Production was owner-rolled-back to f1f8d185.
DO NOT DEPLOY MASTER. Read OL-INC-01 evidence in STATUS and BACKLOG first.
The shared ASGI cancellation stall reproduced locally in both releases;
production attribution remains moderate-confidence, not a proven homepage bug.
Next proposal: OL-INC-01-A, scoped asgiref correction and bounded cancellation
tests, with Linux parity, resource cleanup and security regressions. Obtain
owner implementation approval; deployment remains a separate explicit gate.
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
