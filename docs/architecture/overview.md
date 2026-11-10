# Architecture overview

Purpose: the map of the system: stack, request lifecycle, Django apps and what each owns. Detail pages: [data model](data-model.md), [auth and permissions](auth-and-permissions.md), [tournaments](tournaments.md), [realtime and notifications](realtime-and-notifications.md). Hosting and runtime config: [deployment](../operations/deployment.md).

## Stack

| Layer | Technology | Source |
|---|---|---|
| Web framework | Django 5.2, server-rendered templates + Django REST Framework | `deltacrown/settings.py`, `deltacrown/urls.py` |
| Server | Daphne (ASGI) with Channels for WebSockets | `deltacrown/asgi.py`, `start.sh` |
| Database | PostgreSQL, hosted on Supabase; Django connects directly through the pooler (no Supabase client, no Data API, no RLS identity) | `deltacrown/settings.py` (`DATABASES`) |
| Cache / channel layer | Django Redis cache (key prefix `dc`) and `channels_redis` when `REDIS_URL` is set; in-memory fallbacks otherwise. The channel layer defaults to Redis whenever `DEBUG` is off | `settings.py` (`CACHES`, `CHANNEL_LAYERS`) |
| Static files | WhiteNoise; Tailwind CSS built to `static/dist/`, community JSX built to `static/community/build/` | `package.json`, `render_build.sh` |
| Background work | Celery code exists; worker and beat are OFF in production. Scheduled lifecycle work is driven by the cron endpoint `api/lifecycle/cron/` (needs `Authorization: Bearer <CRON_SECRET>`) | `deltacrown/celery.py`, `deltacrown/lifecycle_cron.py` |
| Media | Pluggable storage chosen by `OWNLOBBY_MEDIA_MODE` | `apps/common/media/configuration.py`, [integrations](../operations/integrations.md#media-storage) |
| Hosting | Render Free web service (512 MB), Singapore | [deployment](../operations/deployment.md) |

## Request / response lifecycle

1. **Proxy -> Daphne.** Render terminates TLS; Daphne runs with `--proxy-headers`.
2. **Middleware** (order in `MIDDLEWARE`, `settings.py`): metrics -> `SecurityMiddleware` -> `CSPMiddleware` (per-request nonce) -> search-indexing headers -> WhiteNoise -> media proxy (dev) -> CORS -> bot-probe shield -> sessions -> common -> CSRF -> authentication -> request logging -> platform preferences -> scheduled-deletion block -> messages -> clickjacking -> TOC audit trail.
3. **URL routing** (`deltacrown/urls.py`): each app mounts its own `urls.py` (for example `account/`, `tournaments/`, `teams/`, `orgs/`, `competition/`, `notifications/`, `api/...`).
4. **View** calls services (`apps/<app>/services/`) which hold business rules and talk to models; views stay thin. Class-based DRF views handle `api/` routes.
5. **Template rendering.** Context processors add notification counts, brand identity, SEO data and navigation (`apps/notifications/context_processors.py`, `apps/common/brand_context.py`, `apps/siteui/nav_context.py`, ...). Inline scripts use `request.csp_nonce`, so full pages carrying a nonce must never be cached.
6. **Response headers**: CSP, HSTS, `X-Frame-Options: DENY`, noindex for private routes.

WebSocket path: `AllowedHostsOriginValidator` -> `AuthMiddlewareStack` (session user) -> JWT middleware (token users) -> URL router (`deltacrown/asgi.py`). Details: [realtime and notifications](realtime-and-notifications.md).

## Application modules (`apps/`)

| App | Responsibility |
|---|---|
| `accounts` | Custom user, signup/OTP verification, login, password reset, Google and Discord OAuth, scheduled account deletion |
| `user_profile` | Public profile (`/@username/`), Game Passports and game identities, privacy/settings, follow system, career, showcase, media, game-provider OAuth connections, public IDs |
| `organizations` | Organizations and teams (vNext), memberships, invites, join requests, roles, recruitment, team hub, followers, realtime team channel, APIs under `api/vnext/` |
| `tournaments` | Tournament model and lifecycle, registration, payment, check-in, brackets, matches, disputes, results, TOC organizer API, certificates, hub, spectator pages |
| `tournament_ops` | Orchestration services: bracket generators, game adapters, match operations |
| `brackets`, `match_engine` | Bracket models and generation; match room engine and consumer |
| `competition` | Multi-game rankings: team ranking snapshots, game ranking config, match reports and verification, `rankings/` and `leaderboards/` pages |
| `leaderboards` | Leaderboard service and engine; seasons |
| `games` | Game registry and configuration: roles, rosters, rules, map pools, match pipelines, passport schemas |
| `economy` | Coin wallet, transaction ledger, top-up/withdrawal/prize-claim requests, wallet PIN, daily rewards, inventory, staff approval console (`fortress/`) |
| `ecommerce`, `shop` | Store, products, orders |
| `notifications` | Notification model, preferences, digests, nav preview/feed APIs, SSE stream, inbox |
| `siteui` | Homepage, information pages, community, navigation, Arena; shared UI |
| `common` | SEO and sitemaps, brand context, media storage and derivatives, game assets, security helpers, ASGI lifecycle server, health |
| `core`, `corelib` | Event bus, service registry, base utilities |
| `moderation`, `support` | Reports and sanctions; FAQ and contact |
| `challenges`, `contracts`, `royale`, `spectator`, `dashboard`, `search`, `players`, `corepages`, `admin` | Challenge hub and bounties, self-challenge contracts, paid battle-royale lobbies, spectator views, player dashboard, search and small helpers |
| `api`, `mobile_api` | Cross-cutting REST endpoints (stats, match operations, staffing, audit log, help, analytics, system) and mobile API v1 |

`deltacrown/` holds settings (plus CI/QA variants), URLs, ASGI/WSGI, Celery config, middleware, branding defaults, health and metrics.

## Frontend

Server-rendered templates with the compiled Tailwind bundle (the Tailwind runtime script is still loaded; removing it needs a full visual pass), Alpine.js loaded only by some page bases (`templates/tournaments/base.html`, `templates/spectator/base.html`, the command center) and plain JS under `static/` elsewhere, Lucide and Phosphor icons. Design tokens and primitives: `static/ownlobby/brand.css` and `foundation.css` (`--ol-canvas`, `--ol-surface`, `--ol-ivory`, `--ol-saffron`, `.ol-btn`, `.ol-card`, ...). Custom team branding on public team pages is preserved.

## Known limitations

* Celery is off; scheduled work is cron-driven.
* Stale committed `static/dist/tailwind.css` (rebuilt by `render_build.sh` on every deploy).
* Wallet PIN hardening is in open PR #77 and the lockout in `withdraw_request`/`pin_verify` is not atomic ([security](../operations/security.md#wallet-and-coins)).
* Known baseline test failures: [testing guide](../guides/testing.md#known-baseline-failures).
