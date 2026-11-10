# Development

## Requirements

* Python: production target 3.12 (Render); CI runs 3.11.9 and 3.12 on Ubuntu. Local work is often Windows/Python 3.13, which does not establish Linux parity.
* PostgreSQL (the schema uses PostgreSQL features). Use separate local development and disposable test databases. Never point development or tests at the Supabase production database.
* Node.js/npm for the frontend build (`npm ci --include=dev`, lockfile committed).
* Redis is optional locally (Channels/Celery integration); guarded tests use in-memory substitutes.
* Native Cairo/font libraries are needed only for the certificate pipeline (CairoSVG/ReportLab).

## Setup

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1              # Linux: source .venv/bin/activate
python scripts/build_twisted_backport.py  # builds the vendored Twisted wheel (see security.md)
python -m pip install -r requirements.txt
npm ci --include=dev
npm run build
Copy-Item config/development.env.example .env   # only if .env does not exist; edit for LOCAL values only
python manage.py migrate
python manage.py seed_games
python manage.py seed_game_passport_schemas
python manage.py seed_game_ranking_configs
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

`requirements-prod.txt` is what Render and Docker install; `requirements.txt` adds development tools. Use `python -m daphne -b 127.0.0.1 -p 8001 deltacrown.asgi:application` when testing WebSockets. Never copy production credentials into `.env`. `manage.py` loads `.env` without overriding variables already in the environment. `start_dev.ps1` starts LAN-facing services and a Discord bot; it is not the safe default.

Key variables (see `config/development.env.example`): `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DATABASE_URL_TEST`, `SITE_URL`, `ALLOWED_HOSTS`, `REDIS_URL`, `OWNLOBBY_MEDIA_MODE`, provider keys. The test configuration refuses to run when `DATABASE_URL_TEST` equals `DATABASE_URL`.

## Testing

Plain `pytest` collects a broad legacy suite with known failures; run explicit targets. `pytest.ini` uses `deltacrown.settings_test` and `--reuse-db`.

```powershell
$env:DATABASE_URL_TEST='postgresql://<local-user>@127.0.0.1:5432/ownlobby_test'
python -m pytest tests/accounts tests/ui apps/notifications -q            # example targeted run
python manage.py test <module> --settings=deltacrown.settings_brand_qa --keepdb --noinput
python scripts/verify_ownlobby.py --collect-static      # release verifier (needs DB named ownlobby_test, loopback only)
python scripts/check_documentation.py --all             # documentation links
python scripts/ops/check_repo_hygiene.py                # root placement policy
```

* `settings_brand_qa` requires a loopback database named `ownlobby_test`. `settings_media_qa`, `settings_smoke`, `settings_sqlite_test` and `settings_test_pg` are CI/local variants.
* Browser tests use Playwright (Chromium): follow the pattern in `apps/user_profile/tests/test_follow_js_behavior.py` and `apps/notifications/tests/test_notifications_ui_behavior.py` (serve real JS/templates in a harness, route API calls, count requests). They skip when Chromium is absent. On Windows the Proactor event loop policy is required.
* Login and password-reset views rate-limit per IP in the shared cache; tests that issue many requests must clear the cache.
* Known baseline failures: OTP brand-string test, notification nav-preview serialization tests, legacy template-existence tests, homepage-context-removal setup errors. Compare against master before blaming a change.

## CI

`.github/workflows/ownlobby-linux-smoke.yml` (PRs to master): migrations on a disposable DB, targeted tournament/registration/results/notification QA, reliability pytest set, `npm ci` + `npm run build`, `verify_ownlobby.py --collect-static`. `.github/workflows/asgi-shutdown.yml`: gated ASGI shutdown contracts on Python 3.11.9 and 3.12. Workflows run on pull requests; master itself has no separate run.

## Conventions

* Smallest correct diff; reuse existing helpers. Do not rename `deltacrown` packages, apps, models, tables, routes or currency identifiers.
* UI: use the OwnLobby foundation (`static/ownlobby/foundation.css`, tokens `--ol-*`), Lucide icons for new UI, accessible names on every control, 44 px touch targets, visible focus, no invented stats or claims. Inline scripts need `nonce="{{ request.csp_nonce }}"`.
* Templates that change `{% url %}` tags are guarded by `scripts/verify_ownlobby.py`; reviewed exceptions are listed there with a reason.
* Frontend build outputs `static/dist/` and `static/community/build/` are required by deploys; do not delete them. `staticfiles/` is collected output.
* Tracking work: `Documents/Development/` (STATUS, BACKLOG, DECISIONS). Update STATUS and BACKLOG in the PR that changes them.
