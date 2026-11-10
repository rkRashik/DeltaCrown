# API reference (overview)

Purpose: how the HTTP API is organised, how to authenticate, and where each group is implemented. Endpoint details live in each app's `urls.py` and serializers; this page is a map, not a catalogue. Authentication background: [auth and permissions](../architecture/auth-and-permissions.md).

## Authentication

| Client | How |
|---|---|
| Browser pages and their JSON calls | Django session cookie + CSRF token (`X-CSRFToken` header or form field) |
| Mobile and API clients | JWT: `POST /api/token/` (credentials -> access + refresh), `POST /api/token/refresh/`, `POST /api/token/verify/`; send `Authorization: Bearer <access>` |
| WebSocket | session cookie, or `?token=<access>` query parameter ([realtime](../architecture/realtime-and-notifications.md)) |
| Local development only | HTTP Basic is enabled in DRF when `DJANGO_DEBUG=1` |

Defaults (`REST_FRAMEWORK` in `deltacrown/settings.py`): JWT then session authentication, permission `IsAuthenticatedOrReadOnly`, anonymous 100/hour and user 1000/hour throttles plus scoped throttles; override rates with the `THROTTLE_*` variables ([environment](environment.md)). Many views set stricter permissions themselves (organizer, participant, staff).

Interactive OpenAPI (`/api/schema/`, `/api/docs/`, `/api/redoc/`, drf-spectacular) is mounted **only when `DJANGO_DEBUG=1`** (schema generation loads every serializer), so it does not exist in production.

## Route groups

| Prefix | Implemented in | Purpose |
|---|---|---|
| `api/tournaments/` | `apps/tournaments/api/urls.py` | Router: tournaments, discovery, games and game config, templates, registrations, payments, brackets, matches, results, leaderboards, custom fields; `checkin/`, leaderboards by tournament/player/scope, `<id>/payouts|refunds/`, certificate download and verification |
| `api/toc/<slug>/...` | `apps/tournaments/api/toc/urls.py` | Organizer console: participants, payments, brackets, matches, disputes, lobby, check-in, announcements, rosters, rules, staff and RBAC, analytics, audit. Organizer/staff only |
| `api/vnext/` | `apps/organizations/api/urls.py` | Organizations, teams, memberships, invites, hub endpoints |
| `api/stats/v1/`, `api/tournaments/v1/history/` | `apps/api/urls/` | User and team statistics, match history |
| `api/match-ops/`, `api/staffing/`, `api/audit-logs/`, `api/organizer/help/`, `api/system/`, `api/` (analytics) | `apps/api/urls/` | Match operations, tournament staffing, audit log, organizer help, system, analytics |
| `api/v1/` | `apps/api/urls/challenge_urls.py` | Challenges (wager matches, bounties) |
| `api/v1/contracts/`, `api/v1/royale/` | `apps/contracts/urls.py`, `apps/royale/urls.py` | Crown Contracts, Crown Royale |
| `api/v1/user/preferences/` | `deltacrown/urls.py` | Signed-in user preferences |
| `api/mobile/v1/` | `apps/mobile_api/urls.py` | Mobile chassis: `health/`, `me/`, `auth/`, plus profile, tournaments, teams, matches, notifications sub-APIs |
| `api/profile/<username>/follow|unfollow|follow/status|followers|following|mutual/` | `apps/user_profile/urls.py` | Follow system and lists (session auth) |
| `api/wallet/pin/...`, `api/wallet/requests/`, `api/daily-reward/...` | `apps/economy/urls.py` | Wallet PIN setup/verify/OTP, top-up and withdrawal requests, daily reward (session auth) |
| `fortress/api/...` | `apps/economy/urls.py` | Staff economy console: approvals, mint, airdrop, wallet reset, audit |
| `notifications/api/...`, `notifications/stream/` | `apps/notifications/urls.py` | Notification preview, feed, read state, actions, SSE |
| `api/oauth/{riot,epic,steam}/...` and `profile/api/oauth` aliases | `apps/user_profile` | Game-provider OAuth login and callbacks |
| `api/lifecycle/cron/` | `deltacrown/lifecycle_cron.py` | Scheduled lifecycle tick; requires `Authorization: Bearer <CRON_SECRET>` |
| `healthz/` | `deltacrown/fast_health.py` | Health check used by Render |
| `api/token/*` | `deltacrown/urls.py` | JWT |

Anything under `api/` that touches money or private data requires authentication; do not add anonymous write endpoints. Add new endpoints to the app's `urls.py` and keep serializers next to the view; new groups should be listed here.

## Example

```bash
curl -s -X POST http://127.0.0.1:8000/api/token/ -H 'Content-Type: application/json' \
     -d '{"username":"<user>","password":"<password>"}'
curl -s http://127.0.0.1:8000/api/tournaments/tournaments/ -H 'Authorization: Bearer <access>'
```

The tournament router registers `tournaments`, `tournament-discovery`, `games`, `tournament-templates`, `registrations`, `payments`, `brackets` and more under `api/tournaments/` (see `apps/tournaments/api/urls.py`), hence `api/tournaments/tournaments/`. To list every route of a running instance use `python manage.py shell -c "from django.urls import get_resolver; print(len(get_resolver().reverse_dict))"` for a count, or read the `urls.py` files; `python manage.py urls_audit` smoke-tests that named URLs reverse and render.
