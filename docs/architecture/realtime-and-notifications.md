# Realtime and notifications

Purpose: how WebSockets, the SSE stream and the notification UI work, and what is actually switched on. Overview: [architecture](overview.md).

## WebSockets (Channels)

`deltacrown/asgi.py` builds `ProtocolTypeRouter({"http": Django, "websocket": ...})`. The WebSocket stack is:

`AllowedHostsOriginValidator` (origin must match `ALLOWED_HOSTS`) -> `AuthMiddlewareStack` (session user) -> `JWTAuthMiddleware` (a `?token=<access_token>` query parameter overrides the session user) -> `URLRouter(homepage + tournament + team routes)`. `RateLimitMiddleware` wraps it only when the setting `WS_RATE_ENABLED` is truthy; `settings.py` does not define it (only the SQLite test settings set it, to False), so WebSocket rate limiting is inactive unless a settings override adds it. With the optional ASGI lifecycle gate (`OWNLOBBY_ASGI_LIFECYCLE_ENABLED=1`) both apps are wrapped by `apps/common/asgi_lifecycle.py`.

| Route | Consumer | Purpose |
|---|---|---|
| `ws/homepage/live/` | `apps/siteui/consumers.py` `HomepageLiveConsumer` | Homepage live feed |
| `ws/tournament/<id>/` | `apps/tournaments/realtime/consumers.py` `TournamentConsumer` | Tournament updates |
| `ws/match/<id>/` | `apps/match_engine/consumers.py` `MatchConsumer` | Match room (declared in both the tournament and match-engine routing; the first match wins) |
| `ws/tournament/<id>/draw/` | `LiveDrawConsumer` | Live draw seed reveals |
| `ws/tournament/<id>/group-draw/` | `GroupDrawConsumer` | Group draw ceremony |
| `ws/teams/<team_id>/` | `apps/organizations/realtime/consumers.py` `TeamConsumer` | Team updates |

Not routed in the composed ASGI app: `TOCConsumer` (`apps/tournaments/api/toc/ws_consumer.py`, documents `ws/toc/<slug>/`) and the older `apps/tournaments/routing.py` patterns (`ws/tournaments/...`, used only by tests). Do not assume they are live.

Close codes used by the JWT middleware: 4002 token expired (refresh and reconnect), 4003 invalid token. Channel layer: Redis (`channels_redis`, database 3 of `REDIS_URL`) whenever `DEBUG` is off or `USE_REDIS_CHANNELS=1`; in-memory otherwise (single process only). Test WebSockets against Daphne, not `runserver`.

## Notifications

* **Model** (`apps/notifications/models.py`): `Notification` (recipient, type, category, title/body, `url`/`action_url`, `is_read`, priority), `NotificationPreference`, `NotificationDigest`. Categories: tournament, team, economy, social, system, warning.
* **Creation**: domain events (registration confirmed, match scheduled, result verified, check-in open, follow requests, team invites, payments) reach `apps/notifications/services.py` through event subscribers (`subscribers.py`) and signals (`signals.py`) registered at startup; `selectors.py` shapes the API payload.
* **HTTP API** (`apps/notifications/urls.py`, mounted at `notifications/`): `api/preview/` (nav popover and sheet), `api/nav-preview/`, `api/feed/` (inbox, paginated), `api/unread-count/`, `api/mark-read/`, `api/toggle-read/`, `api/delete/`, `api/clear/`, `clear-all/`, `mark-all-read/`, `api/action/<id>/`, `api/follow-request/<id>/accept|reject/`, `api/team-invite/<id>/accept|decline/`, and the inbox page at `notifications/`. Unread counts are cached (`NOTIFICATIONS_UNREAD_CACHE_TTL`), so a count can lag a few seconds behind a direct database change.
* **SSE** (`apps/notifications/sse.py`, `GET /notifications/stream/`, alias `/api/notifications/stream/`): streams `{unread_notifications, pending_follow_requests}` every 5 seconds, but only when `NOTIFICATIONS_SSE_ENABLED=1` (default off; otherwise it returns 204 so the browser does not reconnect in a loop). The production value is not verified.
* **Client**: `static/js/notifications_client.js` renders the desktop popover (`#dc-notif-menu`), the mobile bottom sheet (`#dc-mobile-notif-sheet`) and the inbox (`notifications/inbox.html`); `static/siteui/js/primary_navigation.js` owns popover open/close, focus return and Escape. Markup: `templates/partials/notifications/`. Styles: `static/css/notifications.css`.
* **Behaviour contracts** (tested in `apps/notifications/tests/test_notifications_ui_behavior.py`): tabs are real tabs, the popover is `inert` while closed, Escape closes and returns focus to the bell, the sheet traps focus and locks body scroll, loading/error/empty states, one preview request on load. Read/unread semantics and privacy are decided on the server; the client never invents categories.
* **Email**: `send_digests` command sends daily digests; `cleanup_notifications` removes old read notifications; `send_checkin_reminders` creates check-in reminders (scheduled via cron or Celery when enabled).
