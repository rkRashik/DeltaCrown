# Architecture

## Stack

| Layer | Technology |
|---|---|
| Web framework | Django 5.2 (server-rendered templates) plus Django REST Framework APIs |
| Server | Daphne (ASGI), Channels for WebSockets; `deltacrown/asgi.py` composes HTTP and WebSocket apps |
| Database | PostgreSQL (hosted on Supabase; direct Django connection through the pooler, no Supabase client/RLS identity) |
| Cache / channel layer | Redis when configured (`channels_redis` channel layer, Django Redis cache with key prefix `dc`); local-memory fallbacks for development and tests |
| Static files | WhiteNoise; Tailwind CSS compiled to `static/dist/`, community JSX built to `static/community/build/` (both required by deploys) |
| Background work | Celery code exists but the worker/beat are OFF in production; scheduled lifecycle work uses the cron endpoint `api/lifecycle/cron/` |
| Media | Pluggable storage via `OWNLOBBY_MEDIA_MODE` (`legacy` default, `local`, `s3`, `hybrid`), see [integrations.md](integrations.md) |
| Hosting | Render Free web service (512 MB), Singapore; see [deployment.md](deployment.md) |

## Request path

Browser -> Render proxy -> Daphne -> middleware (`deltacrown/settings.py` `MIDDLEWARE`): metrics, security headers and per-request CSP nonce (`deltacrown.middleware.security_headers.CSPMiddleware`), search-indexing headers, WhiteNoise, bot-probe shield, sessions, CSRF, auth, request logging, platform preferences, scheduled-deletion block, messages, clickjacking, TOC audit trail -> URL routing (`deltacrown/urls.py`) -> view -> templates. Context processors inject notification counts, brand identity, SEO and nav data. Templates use the per-request nonce for inline scripts, so full responses must never be cached.

WebSockets: `deltacrown/asgi.py` wraps `AllowedHostsOriginValidator` -> `AuthMiddlewareStack` -> JWT middleware -> URL router. Consumers: tournament updates, bracket, match and live draw (`apps/tournaments`), TOC operations (`apps/tournaments/api/toc/ws_consumer.py`), match rooms (`apps/match_engine`), team updates (`apps/organizations/realtime`), homepage live feed (`apps/siteui/consumers.py`). Notifications also have an SSE stream (`/api/notifications/stream/`).

## Application modules (`apps/`)

| App | Responsibility |
|---|---|
| `accounts` | Custom user, email/OTP signup and verification, login/logout, password reset, Google and Discord OAuth, scheduled account deletion |
| `user_profile` | Public profile (`/@username/`), Game Passports and game identities, privacy and settings, follow system, career, showcase, media, OAuth connections to game providers, public IDs |
| `organizations` | Organizations and teams (vNext), memberships, invites, join requests, roles, competitive settings, team hub, follower and recruitment features, realtime team channel, APIs under `api/vnext/` |
| `tournaments` | Tournament model and lifecycle, registration and payment flow, check-in, brackets, matches, disputes, results, TOC (tournament operations center) API, certificates, hub, spectator-facing pages, organizer tooling |
| `tournament_ops` | Service-layer orchestration around tournaments: bracket generators, game adapters, match operations |
| `brackets`, `match_engine` | Bracket models and generation; match room engine and consumer |
| `competition` | Multi-game ranking: global and per-game team ranking snapshots, game ranking config, match reports and verification, rankings pages |
| `leaderboards` | Leaderboard service and engine |
| `games` | Game registry and configuration (database-first): roles, rosters, rules, map pools, match pipelines, passport schemas |
| `economy` | Coin wallet, transactions (ledger), top-up/withdrawal/prize-claim requests, wallet PIN, daily rewards, inventory, staff approval views |
| `ecommerce`, `shop` | Store and orders |
| `notifications` | Notification model, preferences, digests, nav preview/feed APIs, SSE stream, inbox |
| `siteui` | Homepage, public information pages, community, navigation, Arena and shared UI (`static/ownlobby/foundation.css` design primitives) |
| `common` | Shared services: SEO and sitemaps, branding context, media storage and derivatives, game assets, security helpers, ASGI lifecycle server, health |
| `core`, `corelib` | Event bus, service registry, base utilities |
| `moderation`, `support` | Reports and sanctions; FAQ and contact |
| `challenges`, `contracts`, `royale`, `spectator`, `dashboard`, `search`, `players`, `corepages`, `admin` | Challenge hub, self-challenge contracts, paid Battle Royale lobbies, spectator views, player dashboard, search, small page/admin helpers |
| `api`, `mobile_api` | Cross-cutting REST endpoints (stats, match operations, staffing, audit log, help, analytics, system) and the mobile API v1 (`api/mobile/v1/`) |

`deltacrown/` holds settings (several test/QA variants), URL routing, ASGI/WSGI, Celery config, middleware, branding defaults, health and metrics.

## Data

Roughly: users and profiles (`accounts`, `user_profile`); teams, organizations and memberships (`organizations`); games and their configuration (`games`); tournaments, registrations, payments, brackets, matches, disputes (`tournaments`); wallets, ledger and requests (`economy`); rankings (`competition`); notifications. Soft-delete models are used for financial and request records. Migrations live in each app's `migrations/`; production migrations are a separate approved release step (the build runs `check --deploy`, never `migrate`).

## APIs

DRF with session and JWT authentication (`api/token/`, refresh, verify), throttle classes and rates configurable by environment, OpenAPI schema and Swagger/Redoc under `api/schema/`, `api/docs/`, `api/redoc/`. Main groups: `api/tournaments/`, `api/toc/` (organizer operations), `api/vnext/` (organizations), `api/stats/v1/`, `api/match-ops/`, `api/staffing/`, `api/audit-logs/`, `api/notifications/`, `api/mobile/v1/`, `api/v1/` (challenges, contracts, royale, preferences) and profile/wallet JSON endpoints.

## Frontend

Server-rendered Django templates with Tailwind (compiled bundle plus the Tailwind runtime script, still loaded; removal needs a full visual pass), Alpine (CSP build) for small interactions, Lucide/Phosphor icons, and plain JS under `static/`. Brand tokens: `static/ownlobby/brand.css` and `foundation.css` (canvas `#0B0C0C`, surface `#17181A`, ivory `#F6F1E7`, saffron `#E2B761`). Public pages use the foundation primitives; custom team branding is preserved.

## Known limitations (verified)

* Celery is off; scheduled work is cron-driven.
* Tailwind runtime script and a stale committed `static/dist/tailwind.css` (rebuilt on deploy by `render_build.sh`).
* Wallet PIN lockout in `withdraw_request` and `pin_verify` is not atomic (see [security.md](security.md)).
* The test suite has known pre-existing failures (OTP brand string, notification nav-preview serialization, legacy template-existence checks); run targeted suites, not plain `pytest`.
