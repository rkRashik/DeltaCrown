# OwnLobby conversation handoff

Snapshot: 2026-10-29 23:49 +06:00 (Asia/Dhaka). Start with [STATUS](STATUS.md) for evidence dates and [BACKLOG](BACKLOG.md) for canonical task state. This brief is not authorization to modify production.

## Current state

- Repository `rkRashik/DeltaCrown`, default `master`; verified/synchronized master `e1ef7372fcbd3552ff3b5df8caa852b96cfcf362`. PR #38 merged with four documentation commits, final head `418ec5d2`; original `330a9f63` is stale. Application source remains `f1f8d185` (tournament lifecycle/mobile rich text/pass logo).
- Owner-designated production is [ownlobby.com](https://ownlobby.com). An independent read-only [Render service](https://dashboard.render.com/web/srv-d6eubkngi27c738ieao0) deployment check on 2026-10-29 verified the current `live` deployment at **`f1f8d18566723aa4e62875c20f7f6bc8dc4794e1`**, completed 2026-10-29 12:46:51 +06:00. Issue #37's `b7eb47f0` deployment was older. This does NOT certify current functional acceptance, Data API external denial, storage behavior, or website latency.
- Django/PostgreSQL, Daphne/Channels, Redis/Upstash, Cloudinary and private Supabase Storage. Database access is through Django PostgreSQL connections; Storage APIs are separate from the database Data API. No required database Data API consumer was found in inspected application code.
- **OL-01 remains VERIFYING.** Owner reports Data API OFF/disabled. At 23:12 +06:00 both valid public credential types received HTTP 503 / API connection-schema-cache failure: refusal observed, disabled-specific cause not independently proven. Six public routes, two public images and a local-client constant-only read-only DB check passed. Owner-confirmed Render follow-up reconfirmed live `f1f8d185`, Free/auto-deploy OFF and no matching errors in the bounded log queries. Provider-state reinspection, authenticated/private-media checks and permanent hardening remain open. No confirmed sensitive-data extraction/exploitation. Keep Data API disabled; no RLS/grant changes.
- Celery remains OFF; earlier lifecycle cron success is not evidence that every background job executes. R2 is an unapproved candidate; free/low cost, private media and safe rollback remain mandatory.
- Older engineering/release reports contain pre-launch state. Preserve their evidence but use dated STATUS and newer issue/commit evidence for current planning.

## Next safe task and blockers

**Next: close OL-01 evidence gaps and review permanent hardening.** Obtain current disabled-state confirmation and have the owner manually check existing-account/authorized confidential-file behavior without creating or modifying records. Scoped Render log review is complete. [STATUS](STATUS.md#ol-01-verification-2026-10-29) records A-G results and limits; [BACKLOG](BACKLOG.md#ol-01-permanent-hardening-proposal-not-executed) contains minimal hardening, migration tests and rollback for separate approval. Keep detailed evidence private; do not repeat the original audit.

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
Immediate priority is OL-01: owner disabled Data API on 2026-10-29. Valid-key
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
