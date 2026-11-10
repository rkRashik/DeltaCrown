# OwnLobby

**Your Lobby. Your Next Level.**

OwnLobby is a Bangladesh-first competitive gaming and esports platform built with Django: tournaments and match operations, teams and organizations, player profiles and Game Passports, Ranking Points rankings, a Coins utility wallet, notifications and community. Production: <https://ownlobby.com>.

The Python package, apps, models, tables and some infrastructure names keep the original `deltacrown` identifiers for compatibility; they are not rename targets.

## Documentation

| Topic | Where |
|---|---|
| Overview and document map | [docs/index.md](docs/index.md) |
| Architecture and app modules | [docs/architecture.md](docs/architecture.md) |
| Product features and workflows | [docs/features.md](docs/features.md) |
| Local setup, tests, conventions, CI | [docs/development.md](docs/development.md) |
| Deploy, rollback, environment, domain/SEO | [docs/deployment.md](docs/deployment.md) |
| Supabase, Redis, email, OAuth, media | [docs/integrations.md](docs/integrations.md) |
| Authentication, permissions, CSP, wallet safety, dependencies | [docs/security.md](docs/security.md) |
| Runbooks | [docs/runbooks/](docs/runbooks/README.md) |
| Current status, tasks, decisions | [Documents/Development](Documents/Development/README.md) |
| Agent and contributor rules | [AGENTS.md](AGENTS.md) |

## Quick start

```powershell
python -m venv .venv; .venv/Scripts/Activate.ps1
python scripts/build_twisted_backport.py
python -m pip install -r requirements.txt
npm ci --include=dev; npm run build
Copy-Item config/development.env.example .env      # edit with LOCAL values only
python manage.py migrate; python manage.py seed_games
python manage.py runserver 127.0.0.1:8000
```

Full instructions, safe test commands and database rules: [docs/development.md](docs/development.md). Never point development or tests at the production database.

## Repository layout

| Path | Purpose |
|---|---|
| `apps/` | Django applications (see [architecture](docs/architecture.md#application-modules-apps)) |
| `deltacrown/` | Settings, URL routing, ASGI, Celery, middleware |
| `templates/`, `static/` | Server-rendered pages; sources and required compiled outputs (`static/dist/`, `static/community/build/`) |
| `tests/` | Cross-application tests (app tests live in each app) |
| `scripts/`, `tools/` | Build, verification and operations utilities |
| `branding/`, `config/` | Approved asset provenance and inventories; configuration and repository policy |
| `vendor/twisted/` | Verified temporary Twisted security backport |
| `docs/` | Project documentation (this table's links) |
| `Documents/Development/` | Status, backlog, decisions, handoff |

`Documents/` (other than Development), `Artifacts/`, `media/` and other ignored local directories hold owner material, evidence and data; they are not disposable. `Documents/DELTACROWN/` is owner-protected.

## Contributing

Smallest correct change, targeted tests, no secrets in Git, no production operation without explicit owner approval. See [AGENTS.md](AGENTS.md) and [docs/development.md](docs/development.md#conventions).
