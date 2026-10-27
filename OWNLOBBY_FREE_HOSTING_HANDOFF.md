# OwnLobby free-hosting handoff

## 2026-10-27 focused media authorization update

Profile-media authorization now normalizes stored visibility presets: `PRIVATE`
cannot bypass the private avatar/banner rule, and `PUBLIC` GameProfile rank art
remains readable only when the parent profile permits it. Owners and approved
followers retain their existing access; nonpublic GameProfile visibility is not
broadened. Eight focused, database-free view/policy regressions pass, covering
GET/HEAD denial before origin I/O, owner/follower access, the private-account
flag, public-game inheritance, nonpublic game media, and inactive viewers.
Command: `python manage.py test apps.common.tests.test_media_profile_privacy
--settings=deltacrown.settings_brand_qa --noinput` with loopback-only test DSNs
and in-memory cache/broker. No production tests, storage writes or migration.

**Linux/native/startup evidence is now confirmed**, superseding the older
unverified statements below: [Linux release smoke run 40386647522](https://github.com/rkRashik/DeltaCrown/actions/runs/40386647522)
passed on `4620933989cd7c226952b5ac960b608c7dc6a4c7`, including Python 3.12,
native Cairo/PDF, dependency integrity, Django ASGI startup, Daphne HTTP/WS,
frontend and static checks. Native/dependency/startup inputs are unchanged from
that ancestor; reuse this result alongside the new focused security tests.
This is not a claim that the new fix ran in that historical CI job or that the
existing Render service's live configuration and peak memory were validated.

The owner accepts the unavailable optional badge as cosmetic and directs the
two archived evidence links to remain unavailable. No dispute/reference edits,
fabricated evidence or claim of dispute resolution are made. Portable backup
export remains owner-aware deferred work, not an added launch gate.

The 125-object migration and restore evidence were reused. Scoped evidence found
**zero currently restricted Cloudinary originals**, not 111 confidential leaks.
The exact 111 visibility-controlled legacy sources still need an approved
future-privacy/cache containment policy before hybrid activation; exclude the
two approved public organization-art objects. Account for existing embedded
avatar references before invalidation. Eleven recovered sensitive local-media
paths must not bypass authorized delivery. Exact identifiers/URLs are only in
the encrypted local containment manifest under ignored `Artifacts/media-audit/`.
No revocation, deletion or ACL change was performed.

**Remaining production No-Go:** verify/implement legacy containment and honest
media-gate attestations; confirm essential queued notifications/tasks actually
execute on the existing worker-disabled Free setup (HTTP lifecycle cron does
not drain the broker). Confirm actual start command, secrets/origins and canary
memory at the authorized release window. Do not enable eager execution or bypass
release checks as a workaround. No deploy, DNS, Render, database, verification
flag or domain changes accompany this security fix.

2026-10-27. Started clean at `3bcdd3131dd050207e5af55ea7fee91b6bd91db7`; local branch `feature/ownlobby-free-hosting`. **Local stabilization complete; production promotion remains No-Go pending the checks below.** No push, deployment, live connection, DNS/provider change, purchase or data migration.

## Fixes and evidence

- Enforce certificate **and hostname verification** for TLS Redis URLs across cache, Channels, Celery broker and result backend, including Celery's direct environment overrides. Preserve credentials, custom CA parameters and Upstash DB-0 routing. Fix DB-number rewriting so it preserves URL query parameters. No insecure fallback; actual Upstash handshake still needs an approved runtime check.
- Lifecycle cron now invokes task bodies synchronously without Celery eager tracing/result-backend initialization. Bound-task errors/retry requests return to the runner rather than recursively retrying inside the HTTP request; a later cron sweep retries still-eligible records. Task business logic, transactions, deadlines and notifications are retained. No application task-signal hooks were found on this path.
- Runner failures and nonzero returned error counts produce HTTP 500 after the other runners finish. Stale-submission failures are logged/countable rather than silently counted as confirmations. Missing/already-processed submissions are harmless skips. Successful responses remain HTTP 200, overlap HTTP 409, unauthorized HTTP 401. Internal service failures that are only logged still require log monitoring; this is not exactly-once execution.
- Stream no-show/lobby candidates, overdue payments and dispute IDs with `iterator(chunk_size=50)` instead of caching every ORM row. This does not cap or skip eligible work and changes no financial calculation.
- Both startup scripts retain one foreground Daphne process and default `ASGI_THREADS=2`, `MALLOC_ARENA_MAX=2` unless already configured. This limits the default executor/glibc arenas, **not all Django HTTP concurrency or task memory**. Worker recycling/time-limit settings do not constrain synchronous cron work inside Daphne.
- Blueprint now says `plan: free` and documents worker-disabled intent. It creates no worker/second staging service. Neither the actual live start command nor dashboard plan was queried or changed. The worker flag does not start/stop a separate service.
- S3 config explicitly uses path-style addressing for Supabase compatibility; private origins, delivery authorization and deployment gates remain unchanged.

**Executed:** 48 focused tests passed (TLS/config, cron auth/overlap/failure semantics, existing cron diagnostics and lifecycle tasks); five existing payment-expiry/unchanged-payment/waitlist/constraint tests passed on disposable loopback PostgreSQL. Enhanced async-Redis parser assertion passed separately as part of the same TLS test, not counted twice. Both shell scripts pass `bash -n`; Django system check has no errors and the existing filesystem-media warning. Logs: ignored `Artifacts/free-hosting/`. No failures/skips in these selected tests; two existing migration deprecation warnings in payment tests. Previous 377 passes were reused, not rerun. No fresh frontend build, Linux/Cairo/cloud test, load test or production memory measurement was claimed.

## Memory and automation conclusion

Checked-in startup is Daphne-only: no embedded Celery worker or Beat process. Django app startup starts one daemon match-reminder thread per eligible web process, default 60-second sweeps after eight seconds. Keep it: reminders are separate from lifecycle cron and use persisted notification markers. Task/service imports and rendering/font registration can add baseline memory; broad import refactoring was deliberately avoided.

The owner-reported ~306 MB RSS samples demonstrate sampled usage, not peak usage or a diagnosed leak. OOM can still occur during concurrent requests, images/PDFs, large catch-up work or completion-side effects. No production logs/heap trace were supplied to isolate the exact crash trigger. Measure peak RSS/startup and overlapping real workloads before declaring 512 MB safe; these changes reduce demonstrated avoidable overhead but do not establish an OOM cure.

Keep the **existing five-minute authenticated POST** to `/api/lifecycle/cron/` as the zero-cost starting schedule; no live schedule changed. It runs, sequentially: tournament date transitions, wrap-up, no-shows, expired lobbies, payment expiry/waitlist promotion, group/playoff reconciliation, overdue result confirmation (50 per tick), and dispute escalation. No separate broker worker is needed for these direct runner calls. Do not additionally run Beat for the same tasks. `ENABLE_CELERY_BEAT=0` gates heavy schedule entries; never start a Beat process just for its remaining base schedule.

Normal deadline-observation delay is up to five minutes plus request/runtime delay; this cannot promise exact-time transitions. Redis `cache.add` has a 240-second lease: a run longer than that can overlap a later request, and Beat/manual calls do not share this endpoint's lock. Monitor duration below the lease and investigate slow runs; do not enable aggressive concurrent retries. The in-process reminder thread stops during sleep/restart and cannot guarantee catch-up of missed reminder windows. Lifecycle sweeps re-evaluate persisted due state after wake-up; crashes can interrupt a run, and a later tick retries it. Do not shorten the live schedule without observed duration/quota evidence.

## Recommended zero-cost configuration

Use the **existing single Render Free web service**, `bash render_build.sh`, `bash start.sh`, Python 3.12.10 target, old hostname/domain, existing Supabase and Upstash. Keep Beat/bot/embedded-worker/startup migrations disabled; keep match reminders and persistent-media/security gates enabled. Retain existing Celery eager/async behavior until actual queued workloads are verified: do **not** globally enable eager mode to conceal an absent worker. Use temporary `ENABLE_MEMORY_DIAGNOSTICS=1` only for a few canary cron cycles, then disable it. Never bypass TLS verification if a trust-chain check fails; correct the runtime CA trust instead.

Five-minute inbound traffic generally keeps the service awake. Render grants **750 shared Free instance-hours/month**; one continuously active service uses up to 744 hours in a 31-day month, leaving little shared headroom. Do not add a second always-running Free staging service. Sleep/cold starts, restarts, outbound bandwidth and external-service traffic limits remain. Render also blocks common SMTP ports 25/465/587 on Free: test the existing provider's supported connection (the documented Resend setup uses 2587) without changing the live sender. [Render Free limitations](https://render.com/docs/free).

## Supabase Storage conclusion

**Code-compatible, not cloud-verified.** Both governed aliases can use the same project-issued HTTPS S3 endpoint ending `/storage/v1/s3`, the actual project region in `MEDIA_PUBLIC_REGION`/`MEDIA_PRIVATE_REGION` (**not the R2-style `auto` default**), and two distinct buckets with public access disabled. Names/keys and proxy delivery need no change; no mode was switched.

Generated Supabase S3 access keys bypass RLS and have cross-bucket project access. Two generated keys are **not independent bucket-level isolation**. Logical bucket separation and Django authorization remain useful, but compromise of either server key threatens other project buckets. Keep keys server-only, never expose them to browsers, and require explicit owner acceptance of that credential scope before using this option for confidential evidence. Supabase user-JWT/RLS S3 access is a different design, not automatically provided by Django users. [Authentication](https://supabase.com/docs/guides/storage/s3/authentication).

The Free plan currently lists **1 GB file storage, 5 GB egress and 5 GB cached egress**; actual remaining capacity was not inspected. S3 versioning is unsupported, so deletion is not a recovery strategy. Independent encrypted media backup/restore remains essential; do not assume a database backup includes object bytes. No bucket, key or account was created. [Quota](https://supabase.com/pricing), [S3 compatibility](https://supabase.com/docs/guides/storage/s3/compatibility).

## Remaining gates and precise owner sequence

1. Review this commit and approve the coordinated release validation; no dashboard change is needed just to review it. Verify actual Render-linked branch, start command, process list, current Celery eager/async settings and workspace hours before authorizing a push/deploy. Never merge/deploy automatically.
2. Use an existing approved disposable Linux/Python 3.12 runner or a time-limited validation window, **not a second always-on Render service**. Run the existing native Cairo/rendering instructions and a trusted Upstash TLS handshake; no production credentials in test logs.
3. Approve whether Supabase's project-wide credential risk and available Free quota are acceptable. Then, separately authorize two private buckets/credentials, synthetic write/read/delete, raw anonymous-denial and per-user authorization checks, restart persistence, manifest-backed legacy copy/containment and independent DB/media restore. Leave media verification flags false until actual evidence exists.
4. Verify every essential on-demand `.delay()`/`apply_async()` operation has a working execution path. The HTTP cron does **not** drain the Celery broker. A separate worker is not supplied by the Free web service, and task success logs from `.apply()` were not proof of one. Pending worker-dependent notifications/completion operations are a release gate; no silent disabling or unapproved inline workaround was introduced.
5. In the approved canary window, validate startup and peak RAM below 512 MB with headroom under representative requests plus cron/reminders; check cron JSON, HTTP 500 alerts, task errors, email, existing provider callbacks, queues and WebSockets. Reuse prior passed suites; investigate only new failures. Keep the old domain/canonical defaults throughout.
6. Only after those gates and explicit approval, follow the existing [domain/rollback runbook](OWNLOBBY_DOMAIN_MIGRATION.md). No DNS or provider switch now. Roll back reviewed code/settings without touching user/financial data; never restore insecure Redis TLS or public confidential storage as a workaround.

Implementation commit: `6116414856e178f0696b510196d3e1b07f78a127` (`fix: harden OwnLobby free-host automation and Redis TLS`). Its commit-reference follow-up is documentation-only; final HEAD/clean status are reported to the owner. Prior phases, database/schema contracts, all 69 approved assets, all 26 protected Documents files and production secrets are preserved. No paid service or new always-running infrastructure is required by this local change; neither a reliable promoted launch nor a zero-cost worker solution is claimed without the validation above.
