# OwnLobby

**Your Lobby. Your Next Level.**

OwnLobby is a Bangladesh-first competitive gaming and esports platform built with Django. The codebase includes tournaments and match operations, teams and organizations, player profiles and Game Passport, rankings, Coins wallets and escrow, community features, organizer/admin tools, and real-time updates. Showdown, Missions, Bounty and Dropzone have evolving workflows; availability depends on configuration and permissions.

**Current development and release status:** start with the [Development workspace](Documents/Development/README.md), [dated status](Documents/Development/STATUS.md) and [backlog](Documents/Development/BACKLOG.md). The [release handoff](OWNLOBBY_RELEASE_HANDOFF.md) and [production readiness](OWNLOBBY_PRODUCTION_READINESS.md) retain historical technical evidence; their earlier local-only release decisions are not a current deployment assessment. Live availability does not establish full launch acceptance.

Technical identifiers such as the `deltacrown` Python package, app/model/table names, internal currency fields, integration identities and infrastructure hostnames remain for compatibility. Public platform branding is OwnLobby. Do not rename these identifiers as cosmetic cleanup.

## Architecture and layout

Django renders templates and exposes REST APIs. Domain services coordinate tournament, team, ranking and economy behavior. Daphne/Channels serve ASGI and WebSockets; Redis supports caching/channel layers and Celery background work. Django manages PostgreSQL connections; Supabase, Upstash and Render are existing production dependencies, not services that development setup should modify.

| Path | Purpose |
|---|---|
| [apps/](apps/) | Domain applications, APIs, services, models, migrations, signals and app-level tests |
| [deltacrown/](deltacrown/) | Django settings, URL routing, ASGI, Celery and middleware |
| [templates/](templates/) | Server-rendered pages, includes and transactional messages |
| [static/](static/) | Source assets plus required compiled Tailwind/community outputs |
| [tests/](tests/) | Cross-application regression/integration tests |
| [scripts/](scripts/) and [tools/](tools/) | Build, validation, audit and development utilities |
| [branding/](branding/) | Approved asset provenance and public security/storage inventories |
| [vendor/twisted/](vendor/twisted/README.md) | Verified temporary upstream HTTP security backport |
| [config/](config/) | Feature/reference and repository documentation policy |
| [reference/](reference/README.md) | Preserved product-history snapshot and cleanup inventory |
| [Documents/Development/](Documents/Development/README.md) | Public development management, task backlog and conversation handoff |

`Documents/DELTACROWN/` is owner-protected and must remain in place. `Documents/`, `docs/`, `Artifacts/`, `media/` and other ignored local collections are not disposable merely because Git ignores them. See the [documentation guide](OWNLOBBY_DOCUMENTATION_GUIDE.md) before reorganizing anything.

## Requirements

- Python: production target **Linux/Python 3.12**; Render currently declares 3.12.10. Recent local validation uses Windows/Python 3.13.15. That does not establish Linux parity.
- PostgreSQL: required for the application's PostgreSQL-specific schema and tests. Use separate local development and disposable test databases. Do not use Supabase production for development/tests.
- Node.js/npm: required for locked frontend builds. No Node engine/version file is currently pinned; cleanup validation uses Node 24.19.0/npm 11.17.0.
- Native Cairo/font dependencies: needed for the complete CairoSVG/pycairo/cairocffi/ReportLab/svglib certificate pipeline. See [Linux parity](OWNLOBBY_LINUX_PARITY.md); a successful Python import alone is insufficient.
- Redis: needed for realistic local Channels/Celery integration. Guarded unit tests use memory substitutes; they do not validate live Upstash.

## Local development

Use a fresh checkout or deliberately chosen isolated virtual environment. Preserve existing local environments and `.env` files. Commands below assume the repository root and PowerShell; on Linux activate the equivalent `.venv/bin/activate` environment.

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python scripts/build_twisted_backport.py
python -m pip install -r requirements.txt
npm ci --include=dev
npm run build
```

If activation is unavailable, invoke the environment's Python executable directly; changing machine-wide PowerShell policy is unnecessary. `requirements-prod.txt` is authoritative for Render/Docker runtime installation. `requirements.txt` includes runtime pins plus broader development tools. The local Twisted wheel is intentional; do not replace it with an unreviewed prerelease or install plain 26.4.0 to bypass a failure.

Create a blank local environment file only if one does not exist:

```powershell
if (!(Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath config/development.env.example -Destination .env
}
```

Edit the new file for **local-only** PostgreSQL/Redis and a local signing key. The ignored root `.env.example` is an older owner-owned file and is not the supported setup template. Do not copy production credentials, SMTP senders, bot tokens or provider secrets. `manage.py` loads `.env` without overriding explicit environment variables; `DATABASE_URL_DEV` takes precedence for ordinary development settings.

Create dedicated local databases/roles using your local PostgreSQL administration workflow. The example's URI placeholders must be replaced with local credentials; they are not working accounts. Development DB and test DB must differ. Never point the test configuration at real users or financial records.

### Database migrations

With the connection confirmed local and dedicated to development:

```powershell
python manage.py migrate --plan
python manage.py migrate
python manage.py check
```

For intentional future model work, generate/review migrations and validate them on disposable data before any approved release step. Repository cleanup introduces no schema migration. Build scripts do not authorize production migrations; deployment/restore procedures remain separate reviewed operations.

### Django, Daphne and background work

```powershell
python manage.py runserver 127.0.0.1:8000
# Alternative ASGI entry point, in a separate terminal:
python -m daphne -b 127.0.0.1 -p 8001 deltacrown.asgi:application
```

Use the ASGI entry point for real WebSocket tests. Asset build/collection and media delivery remain separate concerns. Only start Celery against a dedicated local/sandbox broker and local data when needed:

```powershell
celery -A deltacrown worker --pool=solo --loglevel=info
```

The legacy `start_dev.ps1` starts LAN-facing Django, Celery and a Discord bot. It is not the default safe setup path; review all destinations first. Importing `riot_test.py` is now inert, but explicitly running that legacy manual probe performs provider requests and requires separate authorization/configuration.

## Safe tests

Configure a disposable local PostgreSQL database named **ownlobby_test**. Guarded `deltacrown.settings_brand_qa` rejects non-loopback hosts and other DB names. Replace the example role with your local test role; never substitute production URLs. Port 55432 is the local validation setup, not a required production port.

```powershell
$env:DATABASE_URL='postgresql://ownlobby_qa@127.0.0.1:55432/ownlobby_unused'
$env:DATABASE_URL_DEV=$env:DATABASE_URL
$env:DATABASE_URL_TEST='postgresql://ownlobby_qa@127.0.0.1:55432/ownlobby_test'
$env:COMPETITION_APP_ENABLED='1'
$env:S3_TESTS='0'
$env:SENTRY_DSN=''
$env:AWS_EC2_METADATA_DISABLED='true'
python manage.py test apps.common.tests.test_release_readiness apps.common.tests.test_dependency_compatibility --settings=deltacrown.settings_brand_qa --keepdb --noinput
python -m pytest tests/integration/test_websocket_realtime.py --ds=deltacrown.settings_brand_qa
```

The exact larger suites and baseline limits are recorded in [security closure](OWNLOBBY_SECURITY_CLOSURE.md), [OAuth reliability](OWNLOBBY_OAUTH_RELIABILITY.md) and [cleanup handoff](OWNLOBBY_CLEANUP_HANDOFF.md). Plain `pytest` has a broad legacy collection configuration; use explicit safe targets/settings rather than assuming every old helper is isolated.

Checks that need no application database:

```powershell
python scripts/build_twisted_backport.py
python -m unittest apps.common.tests.test_http_transport_security tests.test_repository_tools
python scripts/ops/check_repo_hygiene.py
python scripts/check_documentation.py --all --output Artifacts/repository-cleanup/documentation-links.json
```

The dependency auditor requires separate pip-audit tooling and audits the upstream base as well as the installed local version. Its nonzero exit for six base findings is deliberate; five unused-protocol findings remain and the HTTP item has the reviewed backport. A scanner skip is not clearance.

## Frontend, static and media

`npm run build` builds community JSX through esbuild and Tailwind CSS. `npm ci --include=dev` uses the committed lockfile. Keep `static/dist/` and `static/community/build/`: deployment requires their outputs. They are generated but not disposable deployment inputs.

```powershell
npm run build
# In the guarded local test environment:
python scripts/verify_ownlobby.py --collect-static
```

`staticfiles/` is collected output; `static/` contains required source and deployment assets. `media/` contains local uploads/evidence and must not be treated as static output or deleted as cleanup. All 69 approved OwnLobby assets are hash-protected by [asset provenance](branding/approved-assets.json).

[Final media implementation and release steps](OWNLOBBY_FINAL_ENGINEERING_HANDOFF.md) describe the opt-in `OWNLOBBY_MEDIA_MODE=local|s3` architecture. Default `legacy` preserves existing local data until a reviewed backfill; it is blocked for a persistent-media production release. Do not enable split storage before copying/verifying existing keys, or enable public access on either bucket. No provider credentials are needed for `deltacrown.settings_media_qa` synthetic tests.

[Media architecture](OWNLOBBY_MEDIA_ARCHITECTURE.md) inventories 53 concrete upload fields plus rich-text uploads. Public and confidential files currently share the default backend. Cloudinary/S3 helper presence does not prove private ACLs, persistence or recovery. Provider selection, file migration and restore tests need a separate approved workstream. `siteui.E001` intentionally blocks an ephemeral-media production release; do not silence it.

## Development and production boundaries

Production commands/settings are documented in the [domain migration runbook](OWNLOBBY_DOMAIN_MIGRATION.md), [technical SEO guide](OWNLOBBY_TECHNICAL_SEO.md) and [release handoff](OWNLOBBY_RELEASE_HANDOFF.md). Live Render branch/auto-deploy configuration is not established by checked-in YAML. No push, merge, deployment, DNS change, canonical switch, secret rotation or infrastructure rename is authorized by local setup or repository cleanup.

Keep old-domain compatibility and canonical migration flags at their reviewed defaults. Provider callbacks, email sender verification, durable private media and backup recovery must be proven before production cutover. Cleanup does not close these gates.

## Documentation, security and contribution

Use the [documentation guide](OWNLOBBY_DOCUMENTATION_GUIDE.md) for active sources, historical evidence, app ADRs and protected owner collections. The former product-oriented README is preserved verbatim in [product history](reference/README_PRODUCT_HISTORY.md); historical claims/contact/license text are not current engineering guarantees.

Read [AGENTS.md](AGENTS.md) before editing. In particular, settings-page DOM/form/URL/CSRF contracts are protected. Preserve API/model/table identities, financial calculations, migrations, private file authorization and approved brand assets. Use a feature branch and local checkpoint, scoped changes, appropriate regression tests and reviewed diffs. Record blockers accurately; never remove a test or suppress security checks to improve counters.

Do not commit `.env`, credentials, database/media exports, private evidence or QA runtime artifacts. Report potential secrets privately without reproducing their values; do not rotate or rewrite history during cleanup. `config/repository-policy.json` defines reviewed navigation/root placement and distinguishes Git hygiene from owner disk cleanup.

There is no standalone repository-wide LICENSE file in the tracked root. Existing package metadata and historical README licensing text disagree; confirm redistribution terms with the maintainer. Vendored components and assets retain their own licenses/provenance. This README does not grant a new license.
