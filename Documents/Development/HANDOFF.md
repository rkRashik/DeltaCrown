# OwnLobby conversation handoff

Snapshot: 2026-10-29. Start with [STATUS](STATUS.md) for evidence dates and [BACKLOG](BACKLOG.md) for canonical task state. This brief is not authorization to modify production.

## Current state

- Repository `rkRashik/DeltaCrown`, default `master`; last verified master `f1f8d18566723aa4e62875c20f7f6bc8dc4794e1`. Latest change is tournament lifecycle/mobile rich text/pass logo, not a Render repair.
- Owner-designated production is [ownlobby.com](https://ownlobby.com). Issue #37 last reports deployed `b7eb47f0d41e7baef447e65b1b0e15e91fe39981` on 2026-10-28; current live SHA is not verified here.
- Django/PostgreSQL, Daphne/Channels, Redis/Upstash, Cloudinary and private Supabase Storage. Database access is through Django PostgreSQL connections; Storage APIs are separate from the database Data API. No required database Data API consumer was found in inspected application code.
- **OL-01: containment configuration applied by owner, verification pending.** Owner reports Data API OFF in Overview and disabled in Settings. External denial, compatibility smoke and permanent privilege hardening remain pending. No confirmed sensitive-data extraction/exploitation. Do not re-enable Data API or modify RLS/grants without separate authorization.
- Celery remains OFF; earlier lifecycle cron success is not evidence that every background job executes. R2 is an unapproved candidate; free/low cost, private media and safe rollback remain mandatory.
- Older engineering/release reports contain pre-launch state. Preserve their evidence but use dated STATUS and newer issue/commit evidence for current planning.

## Next safe task and blockers

**Next: OL-01 bounded read-only containment and compatibility verification**, under an explicitly agreed verification scope, with owner-held private evidence. Do not read sensitive application rows or publish reproduction details. Then prepare permanent-hardening scope, acceptance tests and rollback for separate approval. Do not delay urgent approved work for documentation polish.

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
Immediate priority is OL-01: owner disabled the Data API on 2026-10-29;
external denial and compatibility verification plus permanent hardening remain
pending. Keep it disabled. Agree a bounded read-only verification scope and
keep detailed security evidence private. No sensitive-row extraction, grant/RLS
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
OL-01 has owner-applied Data API containment, with denial/compatibility checks
and permanent privilege hardening still pending. Do not mark it DONE or suggest
re-enabling it. Plan the next scoped verification task, distinguish proposals
from approved decisions, and preserve the existing task IDs and safety gates.
```
