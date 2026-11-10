# Troubleshooting

Purpose: the problems new contributors actually hit, with the cause and the fix. Setup steps: [setup](../getting-started/setup.md). Test issues: [testing](../guides/testing.md).

## Startup and configuration

| Symptom | Cause / fix |
|---|---|
| `DATABASE_URL environment variable is required` | `manage.py` refuses to start without it. Create `.env` from `config/development.env.example` (without overwriting an existing one) and set a local URL |
| `Test database name must contain 'test'`, or "DATABASE_URL_TEST equals DATABASE_URL" | The guard in `settings_test.py`/`conftest.py`: the test URL must point at a different, test-named local database. Never use a production URL |
| `OwnLobby QA requires a LOCAL disposable database named ownlobby_test` | `settings_brand_qa` only accepts a loopback host and the literal database `ownlobby_test` |
| `SITE_URL must be an absolute public origin ...` | `SITE_URL` needs scheme and host, no path/query/credentials; HTTPS in production |
| `DisallowedHost` / 400 on the site | Add the host to `ALLOWED_HOSTS` (and `CSRF_TRUSTED_ORIGINS` for forms) |
| Redirected to HTTPS locally or secure-cookie problems | `DJANGO_DEBUG` is `0` by default; set `DJANGO_DEBUG=1` in `.env` |
| `OWNLOBBY_MEDIA_MODE must be legacy, local, s3 or hybrid` | Invalid value; unset it for the default |
| Missing styles, unstyled pages | Run `npm ci --include=dev` and `npm run build`; `static/dist/tailwind.css` must exist |
| `ModuleNotFoundError` for Twisted/Daphne wheel | Run `python scripts/build_twisted_backport.py` before installing requirements |
| Signup OTP / reset email "not arriving" locally | With `DJANGO_DEBUG=1` mail prints to the `runserver` console. In production without `RESEND_API_KEY` (or the Gmail password) mail also goes to the console backend |
| Login throttled ("Too many login attempts") while testing | Login allows 10 attempts per 60 s per IP and password reset 5; clear the cache (`python manage.py flush_cache` in your local environment only; on production it flushes Redis) or wait a minute |

## Running

| Symptom | Cause / fix |
|---|---|
| WebSocket features do nothing under `runserver` | Use Daphne: `python -m daphne -b 127.0.0.1 -p 8001 deltacrown.asgi:application`; check the origin matches `ALLOWED_HOSTS` and a JWT token or session is present (close codes 4002 expired, 4003 invalid) |
| Notification bell shows no live updates | The SSE stream is off unless `NOTIFICATIONS_SSE_ENABLED=1`; the popover still loads via the preview API on page load. Unread counts are cached (`NOTIFICATIONS_UNREAD_CACHE_TTL`) |
| Inline script blocked by CSP in the browser console | Add `nonce="{{ request.csp_nonce }}"` to the `<script>`/`<style>`; never cache a full response that carries a nonce; the 500 page is standalone for this reason |
| Page works on `runserver` but a `{% url %}` fails in CI | `scripts/verify_ownlobby.py` flags changed `{% url %}` tags and compiles all templates; run it with `--collect-static` locally ([testing](../guides/testing.md)) |
| `/api/docs/` returns 404 | The OpenAPI UI exists only when `DJANGO_DEBUG=1` |
| Windows: Playwright tests fail with `NotImplementedError` in the event loop | Set `asyncio.WindowsProactorEventLoopPolicy()` before starting Playwright (see existing browser tests) and `DJANGO_ALLOW_ASYNC_UNSAFE=true` for that module |
| Tournament stuck in a state | Check `status`, `registration_end`, `tournament_start`; `TournamentLifecycleService.auto_advance(t)` in a shell; production uses the cron endpoint, not Celery ([tournaments](../architecture/tournaments.md)) |

## Database

| Symptom | Cause / fix |
|---|---|
| Migration conflicts after switching branches | Do not edit applied migrations; create a merge migration (`makemigrations --merge`) on your branch. `db_migration_reconcile` compares tables and migration history read-only |
| Tests slow on first run | A fresh test database runs every migration (minutes); `--reuse-db` (default in `pytest.ini`) reuses it afterwards. Drop the test database if schema drift appears |
| Wallet balance mismatch | `recalc_all_wallets` / `reconcile_economy` (detect first, fix deliberately); the ledger is authoritative |

## Where to look next

Logs: `DJANGO_LOG_LEVEL`, `REQUEST_LOG_SLOW_MS` and `STARTUP_LOG_LEVEL` control verbosity; Sentry when `SENTRY_DSN` is set. Production incidents: [deployment](../operations/deployment.md), [runbooks](../runbooks/README.md). Known baseline test failures: [testing](../guides/testing.md#known-baseline-failures).
