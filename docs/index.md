# OwnLobby documentation

OwnLobby is a Bangladesh-first competitive gaming platform (tournaments, teams, player identity, rankings, community, a coin wallet) built with Django and served by Daphne on Render, with PostgreSQL on Supabase. Production: <https://ownlobby.com>. The Python package, apps, models and tables keep the original `deltacrown` identifiers for compatibility; do not rename them.

## New here? Read in this order

1. [Local setup](getting-started/setup.md): prerequisites, local PostgreSQL, `.env`, run Django and Daphne, build the frontend, first test.
2. [Architecture overview](architecture/overview.md): stack, request lifecycle, what each Django app owns.
3. [Feature development workflow](getting-started/workflow.md) and [testing](guides/testing.md).
4. Pick the deep dive for your area below.

## Map

| Section | Page | Use it to |
|---|---|---|
| Getting started | [setup](getting-started/setup.md) | Get a working local environment |
| | [workflow](getting-started/workflow.md) | Go from idea to PR with the repo's checks |
| Architecture | [overview](architecture/overview.md) | Stack, lifecycle, apps |
| | [data model](architecture/data-model.md) | How the main entities relate |
| | [auth and permissions](architecture/auth-and-permissions.md) | Login, OTP, sessions, JWT, who may do what |
| | [tournaments](architecture/tournaments.md) | Lifecycle, registration, matches, results |
| | [realtime and notifications](architecture/realtime-and-notifications.md) | WebSockets, SSE, notification UI |
| Guides | [features](guides/features.md) | What each product area does |
| | [testing](guides/testing.md) | Test commands, harnesses, known baseline failures |
| Reference | [API](reference/api.md) | Authentication and route groups |
| | [environment variables](reference/environment.md) | Every variable name by area |
| | [management commands](reference/management-commands.md) | What each `manage.py` command does |
| | [troubleshooting](reference/troubleshooting.md) | Common errors and fixes |
| Operations | [deployment](operations/deployment.md) | Build, release, rollback, domain/SEO |
| | [integrations](operations/integrations.md) | Supabase, Redis, email, OAuth, media |
| | [security](operations/security.md) | Browser protections, wallet safety, dependencies, incident constraints |
| Runbooks | [runbooks](runbooks/README.md) | Signing-key rotation, image derivatives, CDN delivery, origin governor |

Current status, open tasks and decisions: [Documents/Development](../Documents/Development/README.md). Contributor and agent rules: [AGENTS.md](../AGENTS.md).

## How these docs are kept

* One topic, one page; link instead of copying. Facts that live in code are described as contracts with a source-file pointer.
* "Unverified" marks anything the repository cannot prove (production environment values, provider consoles, live behaviour). Dated state (what is deployed, what is open) lives only in `Documents/Development/STATUS.md`.
* Only the reviewed files listed in `.gitignore` are tracked in `docs/`; private notes stay local. `Documents/DELTACROWN/` holds protected owner originals.
* Check links and placement: `python scripts/check_documentation.py --all` and `python scripts/ops/check_repo_hygiene.py`.
