# Local setup

Purpose: get a working OwnLobby on your machine, from nothing to a running site and a passing focused test. Next: [development workflow](workflow.md), [testing](../guides/testing.md), [troubleshooting](../reference/troubleshooting.md).

## Prerequisites

| Tool | Version / note |
|---|---|
| Python | 3.12 is the production target; CI runs 3.11.9 and 3.12. Newer local versions work but do not prove Linux parity |
| PostgreSQL | Required (PostgreSQL-specific schema). Any recent local server; you need two databases, one for development and one for tests |
| Node.js + npm | For `npm ci` and `npm run build` (Tailwind CSS, community JSX). Lockfile is committed |
| Git | Windows users: the repo uses LF in Git and CRLF warnings are normal |
| Redis | Optional. Without `REDIS_URL` the cache and channel layer fall back to in-process memory (fine for one process) |
| Cairo / fonts | Only for the certificate PDF pipeline (CairoSVG/ReportLab); skip unless you work on certificates |

## 1. Install dependencies

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1                 # Linux/macOS: source .venv/bin/activate
python scripts/build_twisted_backport.py   # builds the vendored Twisted wheel used by both requirements files
python -m pip install -r requirements.txt  # runtime + dev tools (production uses requirements-prod.txt)
npm ci --include=dev
npm run build                              # writes static/dist/ and static/community/build/ (both required)
```

## 2. Create the local databases

Create a role and two databases with your local PostgreSQL tools (names are examples):

```sql
CREATE ROLE ownlobby LOGIN PASSWORD 'choose-a-local-password';
CREATE DATABASE ownlobby_dev  OWNER ownlobby;
CREATE DATABASE ownlobby_test OWNER ownlobby;
```

The test database must be different from the development one. The settings refuse to start tests when `DATABASE_URL_TEST` equals `DATABASE_URL`, and `settings_brand_qa` only accepts a loopback database literally named `ownlobby_test`. Never put a production or Supabase URL in your local `.env`.

## 3. Configure the environment

`manage.py` loads `.env` from the repository root without overriding variables already set in your shell. Create it only if you do not have one (this never overwrites an existing file):

```powershell
if (!(Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath config/development.env.example -Destination .env }
```

```bash
[ -f .env ] || cp config/development.env.example .env
```

Then edit it for local values. The minimum you must set:

| Variable | Local value |
|---|---|
| `DJANGO_DEBUG` | `1`. The default is `0` (production behaviour: HTTPS redirect, strict hosts, real email backends) |
| `DJANGO_SECRET_KEY` | any long random string |
| `DATABASE_URL` | `postgresql://ownlobby:<password>@127.0.0.1:5432/ownlobby_dev` (the app refuses to start without it) |
| `DATABASE_URL_TEST` | `postgresql://ownlobby:<password>@127.0.0.1:5432/ownlobby_test` |
| `SITE_URL` | `http://127.0.0.1:8000` (must be an absolute origin; HTTPS in production) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` |

Everything else (Redis, Cloudinary, Google/Riot/Epic/Steam keys, Discord bot) is optional locally. With `DJANGO_DEBUG=1`, outgoing mail (signup OTP, password reset) prints to the `runserver` console. Full list of names: [environment reference](../reference/environment.md).

## 4. Migrate, seed and create an admin

```powershell
python manage.py migrate
python manage.py seed_games                    # 11 games
python manage.py seed_game_passport_schemas    # per-game in-game ID schemas
python manage.py seed_game_ranking_configs     # ranking configuration
python manage.py createsuperuser
```

Optional sample data: `python manage.py seed_full_tournament` (100 users, 40 teams, 3 organizations, 15 tournaments). Other commands: [management commands](../reference/management-commands.md).

## 5. Run

```powershell
python manage.py runserver 127.0.0.1:8000
# For WebSockets (match rooms, TOC, live draw) use the ASGI server instead:
python -m daphne -b 127.0.0.1 -p 8001 deltacrown.asgi:application
```

Open <http://127.0.0.1:8000/> and the admin at `/admin/`. Celery is not needed for normal development; if you need it, point `CELERY_BROKER_URL` at a local Redis and run `celery -A deltacrown worker --pool=solo --loglevel=info`. `start_dev.ps1` starts LAN-facing services and a Discord bot and is not the safe default.

## 6. Rebuild frontend assets

After changing Tailwind classes or `static/` sources run `npm run build`. Do not delete `static/dist/` or `static/community/build/`; deployments rely on them plus the rebuild in `render_build.sh`. `npm run watch-css` rebuilds CSS on change.

## 7. Run a focused test

```powershell
python -m pytest tests/accounts -q -p no:cacheprovider
```

More targets, the release verifier and browser tests: [testing guide](../guides/testing.md).
