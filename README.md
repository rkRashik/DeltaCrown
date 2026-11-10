# OwnLobby

**Your Lobby. Your Next Level.**

OwnLobby is a Bangladesh-first competitive gaming and esports platform built with Django: tournaments and match operations, teams and organizations, player profiles and Game Passports, Ranking Points rankings, a Coins utility wallet, notifications and community. Production: <https://ownlobby.com>.

The Python package, apps, models, tables and some infrastructure names keep the original `deltacrown` identifiers for compatibility; they are not rename targets.

## Documentation

Start at [docs/index.md](docs/index.md).

| Topic | Where |
|---|---|
| Local setup (PostgreSQL, environment, run, build, tests) | [docs/getting-started/setup.md](docs/getting-started/setup.md) |
| Feature development workflow | [docs/getting-started/workflow.md](docs/getting-started/workflow.md) |
| Architecture, data model, auth, tournaments, realtime | [docs/architecture/overview.md](docs/architecture/overview.md) |
| Product features | [docs/guides/features.md](docs/guides/features.md) |
| Testing and known baseline failures | [docs/guides/testing.md](docs/guides/testing.md) |
| API, environment variables, management commands, troubleshooting | [docs/reference/api.md](docs/reference/api.md) |
| Deploy, rollback, integrations, security | [docs/operations/deployment.md](docs/operations/deployment.md) |
| Runbooks | [docs/runbooks/](docs/runbooks/README.md) |
| Current status, tasks, decisions | [Documents/Development](Documents/Development/README.md) |
| Agent and contributor rules | [AGENTS.md](AGENTS.md) |

## Quick start

Full instructions: [docs/getting-started/setup.md](docs/getting-started/setup.md). Never point development or tests at the production database.

```powershell
python -m venv .venv; .venv/Scripts/Activate.ps1
python scripts/build_twisted_backport.py
python -m pip install -r requirements.txt
npm ci --include=dev; npm run build
# Create .env only if it does not exist (never overwrites an existing file), then edit it with LOCAL values:
if (!(Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath config/development.env.example -Destination .env }
python manage.py migrate; python manage.py seed_games
python manage.py runserver 127.0.0.1:8000
```

```bash
[ -f .env ] || cp config/development.env.example .env   # Linux/macOS equivalent
```

## Repository layout

| Path | Purpose |
|---|---|
| `apps/` | Django applications (see [architecture](docs/architecture/overview.md#application-modules-apps)) |
| `deltacrown/` | Settings, URL routing, ASGI, Celery, middleware |
| `templates/`, `static/` | Server-rendered pages; sources and required compiled outputs (`static/dist/`, `static/community/build/`) |
| `tests/` | Cross-application tests (app tests live in each app) |
| `scripts/`, `tools/` | Build, verification and operations utilities |
| `branding/`, `config/` | Approved asset provenance and inventories; configuration and repository policy |
| `vendor/twisted/` | Verified temporary Twisted security backport |
| `docs/` | Project documentation (getting-started, architecture, guides, reference, operations, runbooks) |
| `Documents/Development/` | Status, backlog, decisions, handoff |

`Documents/` (other than Development), `Artifacts/`, `media/` and other ignored local directories hold owner material, evidence and data; they are not disposable. `Documents/DELTACROWN/` is owner-protected.

## Contributing

Smallest correct change, targeted tests, no secrets in Git, no production operation without explicit owner approval. See [AGENTS.md](AGENTS.md) and [docs/getting-started/setup.md](docs/getting-started/workflow.md).
