# OwnLobby launch cutover — 2026-10-27

## State and scope

Local starting branch: `feature/ownlobby-free-hosting`, HEAD
`576d89cc5394bb4e5d37e87c9ed24d2893af81e9`, initially clean.
The changes described here remain local and uncommitted. No push, merge,
deployment, DNS change, provider ACL change, database write or verification-flag
change was performed.

Production rollback reference supplied by owner:
`903103708b1c85dec86a6d098019ea03f39b3790`. That object exists locally and is
an ancestor of the release. Local `master` currently points to
`8270018c536df41dcd869c3f4412c3c62a1d685b`; it is NOT the deployed SHA.
The current feature HEAD is 19 commits ahead of local master. Recheck the remote
after approval; do not assume the handoff's earlier 20-commit count is current.
No migration files differ between the recorded production SHA and feature HEAD,
and these changes add no model/schema migration.

## Completed local fixes

- `apps/common/media_urls.py`: governed media URLs cannot be replaced by a
  leftover local file's unrestricted `/media/` path.
- `apps/common/media/snapshots.py`, `apps/tournaments/views/hub.py`,
  `apps/tournaments/api/toc/participants_service.py`, and `rosters_service.py`:
  roster readers replace frozen avatar URLs with current profile field URLs in
  memory. One batch profile lookup per snapshot; missing users have no image.
  Identity, membership, IGN and stored snapshots remain unchanged. Governed
  download authorization still runs on every image request.
- `deltacrown/celery.py`: explicitly registers nested match-polling,
  result-confirmation, dispute and Riot-verification modules in the consumer.
  Adds a non-mutating `ownlobby.worker_probe` task.
- `apps/tournament_ops/tasks/match_polling.py`: bracket advancement calls the
  existing transactional `BracketService.update_bracket_after_match(match)`;
  the previous facade constructor/method was invalid. Import failures now retry
  instead of returning a misleading deferred success.
- `apps/tournament_ops/services/match_ingestion_service.py` and
  `apps/notifications/services.py`: publish after transaction commit, so an
  actual worker cannot race an uncommitted row. Publication errors stay logged.
- `apps/notifications/tasks.py`: email and Discord transport failures request up
  to three retries, 60 seconds apart, rather than returning successful Celery
  completion with an error dictionary.
- `scripts/render_processes.py`, `start.sh`, `bin/start_render.sh`, `render.yaml`:
  opt-in worker in the SAME container; prefork concurrency 1, prefetch 1,
  queues `celery` and `default` (Discord webhooks explicitly use `default`).
  Disables duplicate reminder threads in the worker. Supervises both process
  groups: a web/worker exit stops the other and exits nonzero for Render restart.
  SIGTERM shutdown has a 25-second grace period then kills remaining groups.
  No Beat, migrations, queue purge, eager execution or new service.
- `deltacrown/lifecycle_cron.py`: optional `?worker_probe=1` on the existing
  authenticated POST runs a broker/consumer/result round trip with a 10-second
  timeout. Eager execution cannot pass. A failure returns HTTP 500. Ordinary
  five-minute cron requests retain their existing behavior.

Worker default limits: 120-second soft / 200-second hard task timeout; explicit
task limits still apply. Recycle the prefork child after 50 tasks or 150,000 KB
RSS. **The memory setting recycles after a task; it is not a hard RAM cap.**
Prefork parent/child pages can be shared; summing their RSS is not the container
memory measurement. The new combined process layout has NOT been measured on
Render. It must fit before public promotion.

Existing notification publication is best-effort when the broker itself is
unavailable; this patch does not add a durable outbox. Delivery is at least once,
not exactly once: retries/restarts can duplicate an email or webhook. Monitor
publication failures and failed tasks; do not equate a Celery SUCCESS with an
actual delivered email. No existing queue was read, purged or consumed here.

## Focused verification

40 tests passed: 37 Django tests and 3 supervisor tests. Coverage includes real
in-memory broker consumption and retry completion with eager disabled, nested
task registration, bracket dispatch/retry, publish-after-commit, SMTP/Discord
failure retries, authenticated canary failure propagation, cron auth/overlap/error
semantics, hybrid gates, URL preservation, snapshots, and the eight existing
profile authorization regressions. No database was created/accessed by these
SimpleTestCase tests; QA DSNs were explicitly disposable loopback-only.

Commands:

```powershell
# Supply LOCAL QA DSNs first, as in settings_media_qa; never production values.
.venv/Scripts/python.exe manage.py test apps.common.tests.test_launch_execution apps.common.tests.test_media_profile_privacy apps.common.tests.test_hybrid_media apps.common.tests.test_free_hosting.CronChecks --settings=deltacrown.settings_media_qa --noinput
.venv/Scripts/python.exe -m unittest tests.test_render_processes
```

Both startup scripts passed `bash -n`; `git diff --check` passed. The initial
sandbox could not create Daphne's loopback socket pair; tests passed when local
sockets were permitted. One test import was corrected. A hybrid test invocation
using brand-only QA lacked storage aliases; the final combined run used the
existing governed-media QA settings and all passed. Log:
`Artifacts/media-audit/launch-focused-tests.log` (ignored).

Reused the prior Linux/Python 3.12/Cairo/Daphne evidence and completed 125-object,
109,908,333-byte copy/checksum evidence, 750 denials and isolated backup restore.
No migration or recovery exercise was repeated. Windows solo-pool transport
tests are NOT proof of Linux prefork operation or Render peak memory.

## Exact remaining containment action — approval required

Prepared locally, without provider connections:
`Artifacts/media-audit/launch-containment-plan-20261027.json.enc`.
Plaintext-plan SHA-256:
`1c8c5099b628aabade5fe07266d77521b0af66bacd8b57a81a2623ad64695141`.
It uses the existing backup encryption key; keep it confidential and out of Git.
Preparation script: `Artifacts/media-audit/prepare_launch_containment.py`.
It contains exactly **111 source operations, two public exclusions and 60
embedded avatar occurrences**. Those avatars occur in registration
`lineup_snapshot`, not notification records. Exact source IDs/URLs are encrypted.

For each approved source, first revalidate its asset ID, public ID, resource type,
version and copied bytes against the existing evidence. The proposed operation
is the Cloudinary SDK `uploader.rename(public_id, public_id,
resource_type=<recorded type>, type='upload', to_type='authenticated',
overwrite=False, invalidate=True)`. Preserve the bytes and public ID; do not
delete or overwrite. Exclude BOTH deliberately public organization assets.
Do not use deprecated `access_mode` or `private` delivery, which is insufficient
for protecting derived images. See [delivery types](https://cloudinary.com/documentation/control_access_to_media),
[rename](https://cloudinary.com/documentation/image_upload_api_reference#rename_public_id),
and [invalidation coverage](https://cloudinary.com/documentation/invalidate_cached_media_assets_on_the_cdn).

Changing originals alone is insufficient: confirm invalidation coverage for the
actual versioned, versionless and transformed URLs in this account. If coverage
requires a provider setting or support action, complete that exact action before
attesting privacy. After propagation, require anonymous GET/HEAD denial for old
original, transformed and embedded URLs and unsigned authenticated delivery.
Confirm both excluded organization assets remain public. External browser or
third-party copies already downloaded cannot be erased or certified absent.

Coordinate source containment immediately with hybrid deployment: old legacy
code will lose CDN artwork after source containment. Before this window, reconcile
uploads/references added since the verified copy; copy only a demonstrated delta
if separately approved. Do not rerun the completed migration wholesale. An upload
freeze or access restriction needs an explicitly approved mechanism; this patch
does not invent a maintenance flag or silently block production users.

Verify all eleven recovered sensitive `/media/` paths have no raw delivery
bypass; their bytes stay in private Supabase and use record-authorized routes.
The two unavailable evidence links and optional badge retain the previously
accepted unavailable state. Never fabricate or clear their records.

`MEDIA_LEGACY_PRIVACY_VERIFIED` remains false until these checks and coverage
reconciliation are accepted. The storage/restore flags also remain unchanged;
accept the existing evidence explicitly, including actual persistence proof,
rather than simply setting them because a deploy check fails.

## Environment — save only after approval, activate with reviewed deployment

Keep Auto-Deploy OFF; keep the existing service, `bash render_build.sh`,
`bash start.sh`, empty pre-deploy command, existing database, Redis, secrets and
OAuth client identity. Record current values securely outside Git/chat before
changing them. Do not resync the blueprint or recreate the service.

| Variable | Release value / timing |
|---|---|
| `OWNLOBBY_DOMAIN_ENABLED` | `1`, coordinated release |
| `SITE_URL` | `https://ownlobby.com`, coordinated release |
| `DEFAULT_FROM_EMAIL` | `OwnLobby <noreply@ownlobby.com>`; already saved, preserve |
| `BRAND_SUPPORT_EMAIL` | `support@ownlobby.com`; already saved, preserve |
| `RESEND_API_KEY` | Already saved restricted key; preserve, never print |
| `ALLOWED_HOSTS` | Preserve current accepted hosts; ensure exact `ownlobby.com,www.ownlobby.com,deltacrown.onrender.com`. The domain flag also adds new apex/www |
| `CSRF_TRUSTED_ORIGINS` | Preserve existing trusted origins; ensure `https://ownlobby.com,https://www.ownlobby.com`. Domain flag also adds these |
| `WS_ALLOWED_ORIGINS` | If explicitly nonempty, retain required existing origins and add `https://ownlobby.com,https://www.ownlobby.com`; never `*` |
| `OWNLOBBY_MEDIA_MODE` | `hybrid` only with approved coverage/containment evidence |
| `MEDIA_PRIVATE_BUCKET`, `MEDIA_PRIVATE_ENDPOINT_URL`, `MEDIA_PRIVATE_REGION`, `MEDIA_PRIVATE_ACCESS_KEY_ID`, `MEDIA_PRIVATE_SECRET_ACCESS_KEY` | Exact existing VERIFIED Supabase S3 values; HTTPS S3 endpoint, actual region, private bucket; never substitute API keys |
| `CLOUDINARY_URL` | Existing secret and account, unchanged |
| `MEDIA_PUBLIC_*` | Unused in hybrid; no change or public Supabase bucket needed |
| `REQUIRE_PERSISTENT_MEDIA` | `1` throughout |
| `MEDIA_STORAGE_VERIFIED`, `MEDIA_RESTORE_VERIFIED` | `1` ONLY after owner acceptance of corresponding existing evidence and any unresolved persistence requirement |
| `MEDIA_LEGACY_PRIVACY_VERIFIED` | `1` ONLY after the exact containment/denial/coverage checks above pass |
| `ENABLE_CELERY_WORKER` | `1` for approved combined-process canary; consumes existing queues immediately |
| `CELERY_TASK_ALWAYS_EAGER`, `CELERY_LOCAL_FALLBACK_SYNC` | `0` |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Preserve reviewed Upstash TLS/DB-0 credentials and routing; no localhost/memory transport in production |
| `ENABLE_CELERY_BEAT`, `ENABLE_DISCORD_BOT`, `ENABLE_MIGRATIONS_ON_START` | `0` |
| `ASGI_THREADS`, `MALLOC_ARENA_MAX` | `2`, `2` unless an existing reviewed setting is stricter |
| `DJANGO_DEBUG` | `0` |
| `ENABLE_MEMORY_DIAGNOSTICS` | Temporarily `1` for canary cron RSS samples; then `0`. Web-process RSS alone is NOT total container peak |
| `PUBLIC_DOMAIN_REDIRECTS_ENABLED` | Keep existing `0`; www redirect already works upstream |

Keep Django SMTP backend `django.core.mail.backends.smtp.EmailBackend` if an
explicit `EMAIL_BACKEND` override exists. With DEBUG off and the saved Resend key,
code selects `smtp.resend.com:2587`, STARTTLS, username `resend`, the existing key
as password, and a 10-second timeout. No new email DNS setup is needed. API
success does NOT prove this SMTP path works on Render.

Preserve configured social destinations; do not invent new handles. Confirm
branding on those owned accounts or separately approve hiding an obsolete link.

## Owner-approved release steps

1. Approve the exact source-containment plan and coordinated canary window.
   Separately approve the reviewed code, environment changes and GitHub promotion.
   Record the actual currently deployed SHA and previous environment securely;
   verify Auto-Deploy remains OFF. If it differs from the supplied rollback SHA,
   stop and record the newer known-working reference.
2. Review `git diff` and the new files listed above plus the two test files.
   Commit ONLY the reviewed code/runbook on the feature branch, excluding all
   `Artifacts`, credentials and media. Record the resulting SHA. No commit has
   been created by this handoff.

   ```powershell
   git add apps/common/media_urls.py apps/common/media/snapshots.py apps/common/tests/test_launch_execution.py
   git add apps/notifications/services.py apps/notifications/tasks.py
   git add apps/tournament_ops/services/match_ingestion_service.py apps/tournament_ops/tasks/match_polling.py
   git add apps/tournaments/views/hub.py apps/tournaments/api/toc/participants_service.py apps/tournaments/api/toc/rosters_service.py
   git add deltacrown/celery.py deltacrown/lifecycle_cron.py scripts/render_processes.py tests/test_render_processes.py
   git add start.sh bin/start_render.sh render.yaml OWNLOBBY_LAUNCH_CUTOVER.md
   git diff --cached --stat
   git commit -m "fix: prepare OwnLobby private media and free-tier task execution"
   git rev-parse HEAD
   ```
3. After explicit GitHub approval, use the following. Fetch does not deploy; the
   merge must preserve history. Stop for unexpected branch divergence/conflicts.

   ```powershell
   git fetch origin
   git switch master
   git merge --ff-only origin/master
   git merge --no-ff feature/ownlobby-free-hosting -m "Merge reviewed OwnLobby production release"
   git rev-parse HEAD
   # Review/record this MERGE SHA before the authorized push:
   git push origin master
   ```

4. Execute approved containment, reconcile the delta and wait for anonymous-denial
   evidence. Save the coordinated environment above without deploying old code.
   Verification flags require accepted evidence. Do not disable `siteui.E002`,
   `E005`, `E007` or `REQUIRE_PERSISTENT_MEDIA` to get a build through.
   Before enabling the worker, inspect existing `celery`/`default` backlog task
   names/counts without printing payloads or removing messages. Review pending
   cleanup/purge jobs and other delayed mutations explicitly: enabling a consumer
   can execute these too. Do not purge, discard unregistered tasks or silently
   acknowledge a backlog. This production broker inspection was not performed.
5. In the existing Render DeltaCrown service choose **Manual Deploy → Deploy a
   specific commit**, select the recorded MERGE SHA, and confirm the deployed SHA.
   Build must pass its existing `check --deploy` gate. No database restore,
   migrations or DNS change is part of this release.
6. Run the canary checks below immediately. This is a controlled production canary,
   not permission to begin public promotion. If memory or core behavior fails,
   contain access and use a reviewed compatible rollback; do not disable the
   worker and pretend queued work is functioning.

## Live canary checklist

- `/healthz/` returns 200; confirm Render's running SHA and logs show both Daphne
  and the registered prefork worker READY. Health alone checks neither database
  nor broker. Verify real Supabase/Upstash TLS connectivity without dumping URLs.
- In the existing cron provider, manually test an authenticated POST to
  `https://ownlobby.com/api/lifecycle/cron/?worker_probe=1`, using its existing
  secret header. Require HTTP 200 and `results.worker_probe.ok=true`, plus the
  matching task ID succeeding in worker logs. No Render shell is required.
  Then keep the ordinary five-minute URL without the probe query. Check several
  normal responses, error counters and durations below the 240-second lock lease.
  A probe timeout under backlog is a failed/unfinished check, not success.
- Observe TOTAL Render container memory during cold start, worker child recycling,
  simultaneous page/media requests, WebSockets, cron and representative queued
  OCR/Riot/notification work. Require at least 64 MB headroom under 512 MB
  (target peak <=448 MB), without OOM/restart loops. Capture Render memory metrics
  or container cgroup peak; lifecycle RSS samples alone are insufficient.
- Using owner-approved test accounts, verify password login/logout and CSRF form
  submission; reject missing/untrusted CSRF. Complete registration verification
  and password-reset email flows and receive both in the actual inbox. Inspect
  OwnLobby sender, templates and ownlobby.com links. Test actual queued notification
  delivery and Discord only if already configured/enabled; inspect retry/failure
  outcomes and compare queue backlog before/after, without exposing job payloads.
- While Google remains Testing, add/use an authorized test user on the existing
  client; test `/account/google/` through the exact new callback, preserving the
  linked account identity. Check consent brand/home/privacy/terms. Publish the
  existing OAuth app only after the public branding pages and flow are verified;
  then test with an eligible non-test user. Do not create a replacement client.
- Complete an owner-approved nonfinancial tournament fixture through registration,
  check-in, bracket/match creation, result confirmation and next-round progression.
  Verify a queued ingestion-advancement task actually changes the expected bracket;
  a SUCCESS log alone is insufficient. Check permitted WebSocket updates and
  unauthorized/untrusted-origin denial. Do not perform real payouts for a smoke test.
- Test authorized media GET/HEAD as owner/reviewer and denial as anonymous/another
  user, including PRIVATE profile artwork, payment/evidence files and old raw URLs.
  Check all eleven sensitive legacy paths and all planned Cloudinary denial probes.
  Confirm public organization artwork and current roster avatars render.
- Review homepage/navigation, login/signup, verification/reset messages, settings,
  support contact, favicon/social preview, privacy/terms, canonical metadata and
  sitemap on the actual new release. Reuse existing static/branding evidence;
  investigate only observed new failures. Never fake a social destination.
- The existing Steam result-fetch task is explicitly a stub; a worker cannot
  implement it. Keep automatic Steam result fetching unadvertised/disabled and use
  existing manual results. No polling schedule/Beat was enabled here. OCR/Riot
  provider capability and quota must be verified before advertising automation.
- After passing critical checks, publish OAuth as appropriate, submit
  `https://ownlobby.com/sitemap.xml` in the verified Search Console property and
  confirm its response/canonical URLs. Public promotion follows these checks.

## Rollback

The supplied old production SHA is preserved as a historical code reference,
NOT certified media-compatible after containment. Its legacy URLs can fail after
source access changes. Do not turn sources public, point confidential uploads back
to public Cloudinary, set false verification attestations, or restore the database
to make that SHA work.

Before the window, approve a rollback code/configuration that retains governed
private media and all intervening user data. If the combined worker layout fails,
hold public promotion; do not claim a free-tier fit. Reducing optional automation
requires a specific feature decision and remeasurement, not silent task loss.
For a reviewed compatible release use Render's manual deployment/rollback UI to
deploy that exact SHA with its recorded approved environment, Auto-Deploy OFF.
If no compatible rollback exists, restrict access via an explicitly approved
mechanism while repairing the canary. No database rollback, media deletion,
financial reversal, DNS rollback or OAuth identity replacement is authorized.
