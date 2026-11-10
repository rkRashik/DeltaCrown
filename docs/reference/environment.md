# Environment variable reference

Purpose: every environment variable the application reads, grouped by area, names only (never values). Names were collected from `deltacrown/settings.py`, `deltacrown/branding.py`, `apps/common`, `start.sh` and the apps; `config/development.env.example` is the local template. Production values are set in the Render dashboard and are **not verified in this repository**; "default" below means the default in code.

How variables load: `manage.py` calls `load_dotenv(.env, override=False)`, so a real environment variable always wins over `.env`. `DATABASE_URL` is mandatory. `DJANGO_DEBUG` defaults to `0` (production behaviour).

## Core

| Variable | Purpose |
|---|---|
| `DJANGO_SETTINGS_MODULE` | Settings module (default `deltacrown.settings`); QA variants: `settings_test`, `settings_brand_qa`, `settings_media_qa`, `settings_smoke` |
| `DJANGO_DEBUG` | `1` for development |
| `DJANGO_SECRET_KEY`, `DJANGO_SECRET_KEY_FALLBACKS` | Signing key and rotation fallbacks ([signing-key runbook](../runbooks/signing-key-rotation.md)) |
| `FIELD_ENCRYPTION_KEY`, `FIELD_ENCRYPTION_LEGACY_KEYS`, `FIELD_ENCRYPTION_LEGACY_SECRET_KEYS` | OAuth token encryption keys |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `WS_ALLOWED_ORIGINS`, `RENDER`, `RENDER_EXTERNAL_HOSTNAME` | Hosts and origins (the ASGI origin validator uses `ALLOWED_HOSTS`) |
| `SITE_URL`, `SITE_ID` | Canonical public origin (absolute, HTTPS in production); site id |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | HTTPS settings |
| `DEPLOYMENT_TIER`, `SENTRY_DSN`, `SENTRY_RELEASE`, `SENTRY_SEND_PII`, `SENTRY_TRACES_SAMPLE_RATE` | Deployment tier and Sentry |
| `ENABLE_ALLAUTH`, `ACCOUNT_ADAPTER`, `SOCIALACCOUNT_ADAPTER`, `ACCOUNT_EMAIL_VERIFICATION` | Optional allauth |
| `ENABLE_PROMETHEUS_METRICS`, `USE_JSON_LOGGING`, `DJANGO_LOG_LEVEL`, `DJANGO_REQUEST_LOG_LEVEL`, `DJANGO_SERVER_LOG_LEVEL`, `REQUEST_LOG_LEVEL`, `REQUEST_LOG_SLOW_MS`, `STARTUP_LOG_LEVEL`, `TOURNAMENTS_LOG_LEVEL`, `TOURNAMENTS_REALTIME_LOG_LEVEL`, `CERTIFICATE_SERVICE_LOG_LEVEL` | Metrics and logging |

## Database

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Main database (required) |
| `DATABASE_URL_TEST` | Test database; must differ from `DATABASE_URL` |
| `DATABASE_URL_DEV` | Optional alternate used by tooling (`verify_clean_migrate`) |
| `DB_CONNECT_TIMEOUT`, `DB_CONN_HEALTH_CHECKS`, `DB_CONN_MAX_AGE_DEFAULT`, `DB_CONN_MAX_AGE_POOLED`, `DB_CONN_MAX_AGE_SUPABASE_POOLER`, `DB_DISABLE_SERVER_SIDE_CURSORS`, `DB_FALLBACK_TO_TEST_ON_DNS_FAILURE` | Connection tuning (pooler-aware) |
| `SESSION_ENGINE`, `SESSION_CACHE_ALIAS` | Session backend (database-backed by default) |

## Redis, cache, Celery, scheduling

| Variable | Purpose |
|---|---|
| `REDIS_URL` | One URL; databases 0 (cache), 1/2 (Celery), 3 (channel layer) are derived |
| `USE_REDIS_CHANNELS` | Force the Redis channel layer in development (always on when debug is off) |
| `CACHE_REDIS_CONNECT_TIMEOUT`, `CACHE_REDIS_SOCKET_TIMEOUT`, `CACHE_REDIS_MAX_CONNECTIONS` | Cache tuning |
| `ENABLE_CELERY_WORKER`, `ENABLE_CELERY_BEAT`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_BROKER_*`, `CELERY_TASK_TIME_LIMIT`, `CELERY_TASK_SOFT_TIME_LIMIT`, `CELERY_MAX_TASKS_PER_CHILD`, `CELERY_RESULT_EXPIRES` | Celery (off in production) |
| `CRON_SECRET`, `CRON_LOCK_TTL`, `ENABLE_MEMORY_DIAGNOSTICS` | Bearer token for `api/lifecycle/cron/` (the endpoint answers an error when it is unset), single-run lock lifetime (default 240 s), optional RSS logging |
| `DISABLE_INPROCESS_MATCH_REMINDER` | Disable the in-process match reminder scheduler |
| `*_API_CACHE_TTL` (`ANALYTICS`, `DISCOVERY`, `LEADERBOARD`), `NOTIFICATIONS_UNREAD_CACHE_TTL` | Cache lifetimes |

## Server and WebSocket (`start.sh`, `settings.py`)

`PORT`, `ASGI_THREADS`, `MALLOC_ARENA_MAX`, `DAPHNE_HTTP_TIMEOUT`, `DAPHNE_WEBSOCKET_CONNECT_TIMEOUT`, `DAPHNE_WEBSOCKET_TIMEOUT`, `DAPHNE_PING_INTERVAL`, `DAPHNE_PING_TIMEOUT`, `DAPHNE_APPLICATION_CLOSE_TIMEOUT`, `DAPHNE_ACCESS_LOG`, `OWNLOBBY_ASGI_LIFECYCLE_ENABLED` (gate, `0`/`1`; when `1` it also requires `OWNLOBBY_HTTP_CAPACITY`, `OWNLOBBY_DRAIN_SECONDS`, `OWNLOBBY_CLEANUP_SECONDS`, `OWNLOBBY_DECLARED_HOST_SHUTDOWN_SECONDS`, `OWNLOBBY_WEBSOCKET_CAPACITY`, `OWNLOBBY_SATURATION_SECONDS`), `WS_MAX_PAYLOAD_BYTES`, `WS_RATE_*` (only effective if `WS_RATE_ENABLED` is set in settings), `OWNLOBBY_CUTOVER_LOCKDOWN`.

## Email

| Variable | Purpose |
|---|---|
| `RESEND_API_KEY` | When set and debug is off, mail goes through Resend SMTP (`smtp.resend.com:2587`, STARTTLS, user `resend`) |
| `DeltaCrownEmailAppPassword`, `EMAIL_HOST_USER` | Gmail SMTP path, used when no Resend key (and, in debug, only with `USE_SMTP_EMAIL_IN_DEBUG=1`) |
| `EMAIL_BACKEND`, `EMAIL_TIMEOUT`, `USE_SMTP_EMAIL_IN_DEBUG` | Backend override and timeouts |
| `DEFAULT_FROM_EMAIL` | Sender; the code default is `noreply@deltacrown.xyz` and this variable overrides it. The production value is unverified |
| `BRAND_SUPPORT_EMAIL`, `BRAND_FACEBOOK_URL`, `BRAND_INSTAGRAM_URL`, `BRAND_YOUTUBE_URL`, `BRAND_DISCORD_URL` | Public contact and social links |

If neither Resend nor Gmail is configured, mail falls back to the **console backend**: OTP and reset emails are printed, not delivered.

## Authentication and providers

| Variable | Purpose |
|---|---|
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (legacy `DeltaCrown_OAUTH_CLIENT_ID`, `DeltaCrown_OAUTH_CLIENT_SECRET`) | Google sign-in; button appears only when the client id is set |
| `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_BOT_TOKEN`, `DISCORD_APPLICATION_ID`, `DISCORD_GUILD_ID`, `DISCORD_LINKED_ROLE_ID`, `DISCORD_WEBHOOK_URL`, `DISCORD_MATCH_RESULTS_CHANNEL_ID`, `DISCORD_TOURNAMENT_ANNOUNCEMENTS_CHANNEL_ID`, `ENABLE_DISCORD_BOT` | Discord linking, bot and webhooks |
| `RIOT_CLIENT_ID`, `RIOT_CLIENT_SECRET`, `RIOT_REDIRECT_URI`, `RIOT_API_KEY`, `RIOT_OAUTH_SCOPES`, `RIOT_OAUTH_TIMEOUT_SECONDS`, `RIOT_ACCOUNT_API_CLUSTERS` | Riot RSO and account API |
| `EPIC_CLIENT_ID`, `EPIC_CLIENT_SECRET`, `STEAM_API_KEY` | Epic and Steam |
| `JWT_LEEWAY_SECONDS` | JWT clock leeway |
| `THROTTLE_ANON_RATE`, `THROTTLE_USER_RATE`, `THROTTLE_LOGIN_RATE`, `THROTTLE_PASSWORD_RESET_RATE`, `THROTTLE_DISCOVERY_READ_RATE`, `THROTTLE_ANALYTICS_READ_RATE`, `THROTTLE_LEADERBOARD_READ_RATE`, `THROTTLE_REGISTRATION_WRITE_RATE`, `THROTTLE_MATCH_OPS_READ_RATE`, `THROTTLE_MATCH_OPS_WRITE_RATE`, `THROTTLE_PAYOUT_WRITE_RATE`, `THROTTLE_RESULTS_INBOX_READ_RATE`, `THROTTLE_RESULTS_INBOX_WRITE_RATE` | DRF throttle rates |

## Media

| Variable | Purpose |
|---|---|
| `OWNLOBBY_MEDIA_MODE` | `legacy` (default), `local`, `s3`, `hybrid`; invalid values fail startup |
| `MEDIA_PRIVATE_BUCKET`, `MEDIA_PRIVATE_ENDPOINT_URL`, `MEDIA_PRIVATE_REGION`, `MEDIA_PRIVATE_ACCESS_KEY_ID`, `MEDIA_PRIVATE_SECRET_ACCESS_KEY` (and the same `MEDIA_PUBLIC_*` set) | Private/public S3-compatible storage (`apps/common/media/configuration.py`) |
| `CLOUDINARY_URL` | Cloudinary account (public artwork in hybrid mode, legacy default storage) |
| `REQUIRE_PERSISTENT_MEDIA`, `MEDIA_STORAGE_VERIFIED`, `MEDIA_RESTORE_VERIFIED`, `MEDIA_LEGACY_PRIVACY_VERIFIED` | Release gates; owner attestations, never set to silence a check |
| `OWNLOBBY_PUBLIC_DERIVATIVES`, `OWNLOBBY_PUBLIC_CDN`, `OWNLOBBY_CLOUDINARY_TRANSFORMS` | Optional features, each off unless set to `1` ([runbooks](../runbooks/README.md)) |
| `MEDIA_ORIGIN_CONCURRENCY`, `MEDIA_ORIGIN_SMALL_CONCURRENCY`, `MEDIA_ORIGIN_WAIT_SECONDS`, `MEDIA_ORIGIN_SMALL_WAIT_SECONDS`, `MEDIA_ORIGIN_MAX_HOLD_SECONDS`, `MEDIA_DERIVATIVE_CACHE_BYTES`, `MEDIA_PROXY_URL` | Origin governor and caches |
| `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `CERT_S3_DUAL_WRITE`, `CERT_S3_READ_PRIMARY`, `CERT_S3_BACKFILL_ENABLED` | Certificate storage in S3 |

Which values are actually set in production is **unverified here**; check the Render dashboard before relying on defaults (for example, the code default is `legacy` media mode).

## Domain and SEO

`OWNLOBBY_DOMAIN_ENABLED`, `PUBLIC_DOMAIN_REDIRECTS_ENABLED` (both default off), `SITE_URL`.

## Feature flags

`NOTIFICATIONS_SSE_ENABLED` (default off), `LEADERBOARDS_API_ENABLED`, `LEADERBOARDS_CACHE_ENABLED`, `LEADERBOARDS_COMPUTE_ENABLED`, `COMPETITION_APP_ENABLED`, `ORG_APP_ENABLED`, `TEAM_VNEXT_ADAPTER_ENABLED`, `TEAM_VNEXT_FORCE_LEGACY`, `TEAM_VNEXT_ROUTING_MODE`, `LEGACY_TEAMS_ENABLED`, `USER_PROFILE_INTEGRATION_ENABLED`, `SETTINGS_CONTROL_DECK_ENABLED`, `BRACKETS_USE_UNIVERSAL_ENGINE`, `BOT_PROBE_SHIELD_ENABLED`, `MODERATION_ENFORCEMENT_ENABLED`, `MODERATION_ENFORCEMENT_PURCHASE`, `MODERATION_ENFORCEMENT_WS`, `MODERATION_OBSERVABILITY_ENABLED`, `MODERATION_OBSERVABILITY_SAMPLE_RATE`, `MODERATION_POLICY_CACHE_ENABLED`, `VNEXT_FLAGS_CONTEXT_DEBUG`. Reference for flag semantics: `config/flags.md`.
