# Deployment and operations

Purpose: how production is hosted, built, released and rolled back, and which environment variables must exist. Related: [integrations](integrations.md), [security](security.md), [environment reference](../reference/environment.md), [runbooks](../runbooks/README.md).

## Environments

| | Production |
|---|---|
| Host | Render web service `DeltaCrown` (Python runtime, **Free plan**, 1 instance, Singapore) |
| URLs | <https://ownlobby.com> (canonical), `deltacrown.onrender.com` (service hostname, kept for health monitoring) |
| Branch | `master`; **auto-deploy is OFF** (Render reports `autoDeploy: no`). A deploy happens only when the owner triggers it, either with **Manual Deploy in the Render dashboard** or through the **Render API** (the deploy history shows `trigger: api` for recent releases). Both build the commit you name; neither is started by a merge |
| Health check | `/healthz/` |
| Build | `bash render_build.sh` |
| Start | `bash start.sh` |
| Database | Supabase PostgreSQL (pooler); sessions are database-backed |

Current deployed commit and rollback target are recorded in `Documents/Development/STATUS.md`.

## Build (`render_build.sh`)

1. `npm ci --include=dev` and `npm run build` (Tailwind and community JSX), then removes `node_modules` (`NODE_OPTIONS=--max-old-space-size=256` for the 512 MB builder).
2. Builds the vendored Twisted wheel and `pip install -r requirements-prod.txt`.
3. `python manage.py collectstatic --noinput`.
4. `python manage.py check --deploy --fail-level ERROR`. The build never runs `migrate`; migrations are a separate reviewed step.

## Start (`start.sh`)

Runs Daphne on `$PORT` with proxy headers, HTTP timeout, WebSocket connect timeout and ping settings from environment variables, `ASGI_THREADS=2` and `MALLOC_ARENA_MAX=2` defaults for the 512 MB limit. Optional gates: `ENABLE_CELERY_WORKER=1` (off in production), `OWNLOBBY_ASGI_LIFECYCLE_ENABLED=1` (gated ASGI shutdown server, `apps/common/daphne_server.py`, default off). Free instances spin down when idle; the first request after idle is slow.

## Release procedure

1. Confirm CI green on the PR head (smoke and ASGI contracts), then merge to `master`.
2. Confirm a recent Supabase backup or point-in-time recovery point exists and note its timestamp. Check the diff for migrations, dependency or settings changes; none means the deploy is a pure code swap.
3. Confirm required environment variables exist (names in [Environment](#environment-variables); values are never recorded in Git).
4. Trigger the deploy of the exact `master` commit: Render dashboard -> DeltaCrown -> Manual Deploy (Deploy a specific commit), or the equivalent Render API call. Watch the build log; expect about 3 minutes.
5. Post-deploy checks: `/healthz/` 200 on both hostnames; `/`, `/tournaments/`, `/teams/`, `/competition/rankings/`, a 404 page; response headers (nonce CSP, HSTS); login with `?next=/teams/` lands on `/teams/` and an external `next` does not leave the site; signup -> OTP email -> verify; password reset email and link (single use); Google sign-in with a test account; free registration in a test tournament; notifications on a phone; wallet pages load (do not move real money). Watch Render memory and logs for 30 minutes.

## Rollback

No migrations means the previous commit can be redeployed without data changes. In Render: Deploys -> Rollback to the previous live deploy (dashboard), or deploy the previous commit SHA through the dashboard or the API (about 3 minutes). Verify `/healthz/`, login and `/tournaments/`. Do not revert Git on `master` during an incident; fix forward on a branch. If a release included migrations or wallet PIN changes, review compatibility before rolling back past them. Triggers: failing health check, repeated 5xx, broken login/OTP/reset/registration, memory exhaustion, CSP breakage.

## Environment variables

The full list of names, grouped by area, is in the [environment reference](../reference/environment.md). Production values live in the Render dashboard and are **not verified from this repository**. Before a release confirm these exist (values are never written to Git):

* Core: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL` (canonical origin, HTTPS), `RENDER_EXTERNAL_HOSTNAME`.
* Google sign-in: `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`; the redirect URI is `SITE_URL` + `/account/google/callback/` and must be an authorised redirect in the Google console.
* Email: `RESEND_API_KEY` (otherwise the Gmail fallback, otherwise the console backend, which sends nothing); `DEFAULT_FROM_EMAIL` if the default `noreply@deltacrown.xyz` is not wanted; `BRAND_SUPPORT_EMAIL`.
* Scheduling: `CRON_SECRET` for `api/lifecycle/cron/`. The endpoint is meant to be called every 2-5 minutes by an external scheduler (a free cron service or a Render cron job); whether one is configured in production is unverified.
* Redis (`REDIS_URL`), media (`OWNLOBBY_MEDIA_MODE` and storage keys), provider keys and flags as needed.

Code defaults differ from production in places (for example `OWNLOBBY_MEDIA_MODE` defaults to `legacy`, `NOTIFICATIONS_SSE_ENABLED` to off); check the dashboard for the real values.

## Domain and SEO

`SITE_URL` is the only canonical origin used for canonical links, sitemaps, notifications and the Google OAuth redirect; it cannot be inferred from the request Host. `OWNLOBBY_DOMAIN_ENABLED=1` adds `ownlobby.com` and `www` to allowed hosts and HTTPS CSRF origins while keeping old-domain hosts. `PUBLIC_DOMAIN_REDIRECTS_ENABLED=1` redirects anonymous GET/HEAD of public HTML from the old domain and from `www` to the apex; POSTs, APIs, callbacks, private pages, WebSockets and the Render hostname are never redirected. Keep old provider callbacks registered (Google, Discord, Riot, Epic, Steam) when adding the new ones: `/account/google/callback/`, `/account/discord/callback/`, `/api/oauth/riot/callback/`, `/api/oauth/epic/callback/`, `/api/oauth/steam/callback/`. Sessions cannot be shared across different registrable domains; do not weaken cookies. Sitemaps: `/sitemap.xml` index with paginated sections (1,000 rows per page, deterministic ordering); `robots.txt` advertises it and blocks private routes. Do not block old-domain crawling during a migration.

## Resource limits and operations notes

* 512 MB memory: keep worker count and threads low; Celery stays off; heavy tasks are gated by environment flags. Measure before scaling.
* The Render hostname and `/healthz/` stay available for monitoring regardless of domain changes.
* Scheduled lifecycle work runs through `api/lifecycle/cron/` (requires `Authorization: Bearer <CRON_SECRET>`), not Celery beat.
* Backups: Supabase backups/PITR (confirm plan and timestamp before each release). Restore procedure: restore into a scratch database first, compare row counts, never overwrite production without an approved plan.
