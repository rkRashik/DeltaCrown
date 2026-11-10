# Current status

Snapshot 2026-11-10. Older dated entries (OL-INC-01 incident, OL-01 verification matrix, OL-04-B, OL-12, OL-13 sprints) were removed from this file in the documentation cleanup; they remain in Git history of `Documents/Development/STATUS.md` at master `7afd6f68` and earlier.

## Production

* LIVE on master `7afd6f68d37793a0ee376b3aaf4115c84230df88` (Render deploy `dep-dbpk6jbbc2fs73ae5m9g`, manual deploy, live 16:19 UTC 2026-11-10; verified read-only through the Render API). Auto-deploy is OFF.
* Rollback target: `044b9cfb836281868dd37d95c4e944babfcf1e4b` (PR #74, deploy `dep-dbop5b9srm7s73cma4c0`). No migrations, dependency or settings differences between the two. Procedure: [deployment.md](../../docs/deployment.md#rollback).
* Live content: PRs #72-#82 (branding/SEO, eFootball pilot readiness, release QA, Batch 0A route fixes, public UI/UX Sprint 1 Batches A-E including the login open-redirect and password-change 500 fixes).

## Open

* PR #77, wallet PIN (6-digit policy, verified changes, shared lockout): reviewed, mergeable, no migrations, **not live**. Residual wallet risk until it ships: withdrawal requests are reachable and processed by staff in the Django admin, so verify each request. The lockout in `withdraw_request` and `pin_verify` is not atomic even after #77 (follow-up needed). See [security.md](../../docs/security.md#wallet-and-coins).
* Draft PR #47 (inactive QA I/O deadline contracts): not live, leave untouched.
* Not verified at launch: a pre-deploy Supabase backup (confirm one exists), live Google OAuth callback and email delivery, Redis and memory behaviour under real traffic, real-device and non-Chromium QA.
* OL-13 formal launch acceptance and the OL-01 provider-side verification need owner evidence (see BACKLOG).

## Standing constraints

* Celery worker/beat OFF; scheduled work via the lifecycle cron endpoint. Render Free 512 MB.
* Supabase Data API stays disabled (OL-01). Direct Django PostgreSQL access is retained.
* Media: `OWNLOBBY_MEDIA_MODE` default `legacy`; do not switch modes or enable derivatives/CDN flags without an approved plan ([integrations.md](../../docs/integrations.md#media-storage)).
* Known baseline test failures (identical on master): OTP brand-string test, notification nav-preview serialization (11), legacy template-existence tests, homepage-context-removal setup errors.
* Tailwind runtime script still loaded; removal needs a full visual pass.
