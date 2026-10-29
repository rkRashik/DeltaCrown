# OwnLobby conversation handoff

Snapshot: 2026-10-30 04:35 +06:00 (Asia/Dhaka), OL-04-B. Start with [STATUS](STATUS.md) for evidence dates and [BACKLOG](BACKLOG.md) for canonical task state. This brief is not authorization to modify production.

## Current state

- Repository `rkRashik/DeltaCrown`, default `master`; verified/synchronized baseline `f6a27d7cb3dc6f12938d30868f36bb187723d368`, merged PR #40. PR #38's original `330a9f63` is stale. Master/last verified production application remains `f1f8d185`. Unmerged [PR #41](https://github.com/rkRashik/DeltaCrown/pull/41), branch `perf/ol04-b-remove-legacy-home-context-20261030`, implements the owner-authorized legacy view-context removal; no deployment.
- Owner-designated production is [ownlobby.com](https://ownlobby.com). An independent read-only [Render service](https://dashboard.render.com/web/srv-d6eubkngi27c738ieao0) deployment check on 2026-10-29 verified the current `live` deployment at **`f1f8d18566723aa4e62875c20f7f6bc8dc4794e1`**, completed 2026-10-29 12:46:51 +06:00. Issue #37's `b7eb47f0` deployment was older. This does NOT certify current functional acceptance, Data API external denial, storage behavior, or website latency.
- Django/PostgreSQL, Daphne/Channels, Redis/Upstash, Cloudinary and private Supabase Storage. Database access is through Django PostgreSQL connections; Storage APIs are separate from the database Data API. No required database Data API consumer was found in inspected application code.
- **OL-01 remains VERIFYING.** Owner reports Data API OFF/disabled. At 23:12 +06:00 both valid public credential types received HTTP 503 / API connection-schema-cache failure: refusal observed, disabled-specific cause not independently proven. Six public routes, two public images and a local-client constant-only read-only DB check passed. Owner-confirmed Render follow-up reconfirmed live `f1f8d185`, Free/auto-deploy OFF and no matching errors in the bounded log queries. Provider-state reinspection, authenticated/private-media checks and permanent hardening remain open. No confirmed sensitive-data extraction/exploitation. Keep Data API disabled; no RLS/grant changes.
- Celery remains OFF; earlier lifecycle cron success is not evidence that every background job executes. R2 is an unapproved candidate; free/low cost, private media and safe rollback remain mandatory.
- Older engineering/release reports contain pre-launch state. Preserve their evidence but use dated STATUS and newer issue/commit evidence for current planning.

## Next safe task and blockers

**Next safe task: owner review PR #41/current checks, then seek explicit deployment approval.** OL-04-B changes only `home()` application behavior: new request-local dictionary, no legacy import/builder. Extras, sections, personalized hero, presentation, SEO, `never_cache` and media/security boundaries remain. Legacy helper/CMS/admin/global processor remain. **161 local PostgreSQL/security tests PASS**; actual-baseline HTML comparisons match for empty/populated data and five roles, cold queries drop by 14 empty / 16 populated, warm query counts match. **Linux run #61 PASS** at code head `c1c6325d`, including 114 homepage tests; inspect current PR checks after this docs-only update. See [STATUS evidence](STATUS.md#ol-04-b-isolated-verification-2026-10-30). A started/skipped run is not PASS. A stale existing copy test was reproduced against the baseline then corrected without changing templates. No production SQL time, Redis hit rate or whole-request percentile has been measured; no production improvement is claimed.

OL-04 remains VERIFYING; OL-03 stays IN_PROGRESS. CI branch coverage correction is separately committed (`a9a87bc6`); it does not resolve OL-02's signing-key warning. Application rollback commits/order are in [BACKLOG](BACKLOG.md#ol-04); no DB/cache/media/secret/worker operations are needed. Keep the [OL-03/04-A report](tasks/OL-03-04-A.md) as historical investigation evidence. Later common-processor retirement and extras/navbar consolidation require separate scope and tests. No broad cleanup; the three baseline root-placement findings are future OL-14 cleanup candidates only, not approval to move/delete owner records or reserve a new task ID.

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
Current performance implementation is OL-04-B in unmerged PR #41. Read STATUS's
local evidence and verify CI on the reviewed head; do not repeat the diagnosis
or claim deployment. The owner approved this scoped code change, not deployment.
Next: review/approve PR, then obtain deployment approval and bounded live checks.
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
