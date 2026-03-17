# DeltaCrown Platform — System Audit Log

**Audit Date:** 2026-03-16
**Auditor:** Claude Opus 4.6 (Incoming Development System)
**Scope:** Full technical audit of the DeltaCrown esports platform repository

---

## 1. Architecture Overview

### 1.1 Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Django | 5.2.8 |
| API | Django REST Framework | 3.16.1 |
| ASGI Server | Daphne | 4.2.1 |
| WebSockets | Django Channels + channels-redis | 4.3.1 / 4.3.0 |
| Task Queue | Celery | 5.5.3 |
| Database | PostgreSQL (Neon) | psycopg2-binary 2.9.11 |
| Cache/Broker | Redis (Upstash) | redis 7.0.1 |
| CSS | Tailwind CSS | 3.4.0 |
| Auth | django-allauth | 65.13.0 |
| Admin | django-unfold | 0.80.0 |
| Storage | Cloudinary + S3 (boto3) | cloudinary 1.40.0 |
| Monitoring | Sentry + Prometheus | sentry-sdk 2.43.0 |
| Deployment | Render | render.yaml |

### 1.2 Project Structure

The project is a monolithic Django application with 27 installed apps:

**Core Infrastructure:**
- `core` — Service registry, event bus re-exports, health checks, plugin registry
- `corelib` — Low-level utilities (brackets, healthz, admin utils, idempotency)
- `common` — Shared utilities, event bus, API responses, game registry, context processors
- `corepages` — Static/landing pages
- `siteui` — Community features (posts, likes, comments, shares)

**Identity & Users:**
- `accounts` — User authentication, Google OAuth, account deletion
- `user_profile` — Player profiles, Game Passport, OAuth integrations, badges, XP, achievements
- `players` — Player model connecting users to games (bridge entity)

**Competition:**
- `tournaments` — **Massive app** (42 model files, 34 migrations) — tournaments, matches, brackets, registrations, payments, prizes, certificates, lobbies, disputes, staffing
- `tournament_ops` — Match result submission & dispute resolution pipeline
- `competition` — Independent competition/challenge system (separate from tournaments)
- `challenges` — Another challenge system (1v1/team challenges)
- `leaderboards` — Ranking snapshots, materialized views

**Organizations:**
- `teams` — Legacy team system (being migrated)
- `organizations` — vNext team system with org hierarchy, memberships, rankings, Discord sync

**Economy:**
- `economy` — DeltaCrown virtual currency, wallets, transactions
- `shop` — Storefront (empty/skeletal)
- `ecommerce` — Another commerce system (empty/skeletal)

**Platform Services:**
- `games` — Game definitions, identity configs, passport schemas
- `notifications` — Email/Discord/in-app notifications, digest system
- `moderation` — Content moderation, reports
- `search` — Search functionality
- `dashboard` — Admin/analytics dashboards
- `spectator` — Spectator features
- `support` — Support tickets

### 1.3 Settings File

The main `deltacrown/settings.py` is **1,761 lines**, containing:
- All environment variable loading
- 18-layer middleware stack
- Celery configuration with memory-optimized worker settings
- Redis configuration for cache, channels, and Celery
- OAuth credentials for Riot, Steam, Epic
- Prometheus metrics configuration
- S3/Cloudinary storage configuration

---

## 2. App Relationship Map

```
accounts (auth) ──── user_profile (identity, passports, settings)
                         │
                         ├── players (game-specific player records)
                         │      │
                         │      └── games (game definitions, schemas)
                         │
                         ├── organizations/teams (team membership)
                         │      │
                         │      └── tournaments (registration, matches)
                         │             │
                         │             ├── tournament_ops (results, disputes)
                         │             ├── leaderboards (rankings)
                         │             └── economy (prizes, payments)
                         │
                         ├── notifications (cross-cutting)
                         └── siteui (community content)
```

---

## 3. Detected Problems

### 3.1 CRITICAL Issues

#### C1: Tournament App is Monolithic (42 model files)
The `tournaments` app contains 42 separate model files covering tournaments, matches, brackets, registrations, payments, prizes, certificates, disputes, lobbies, staffing, sponsors, KYC, free agents, stages, groups, qualifiers, and more. This is excessively large and violates single-responsibility principles.

**Files:** `apps/tournaments/models/*.py` (42 files)

#### C2: Duplicate Team Systems (Legacy + vNext)
Two complete, parallel team systems exist:
- `apps/teams/` — Legacy team models (6 migrations, being deprecated)
- `apps/organizations/` — vNext team models with org hierarchy (37 migrations)

The migration from legacy to vNext is incomplete. Some parts of the codebase reference `teams.Team` while others use `organizations.Team`. Leaderboards still reference the legacy system.

**Files:** `apps/teams/models.py`, `apps/organizations/models/team.py`

#### C3: Three Competing Match Result Pipelines
1. **Tournament signals** (`apps/tournaments/signals.py`) — `post_save` on Match triggers bracket advancement
2. **Tournament ops submission** (`apps/tournament_ops/`) — Formal result submission with evidence, opponent response, and dispute flow
3. **Riot canonical ingestion** (`apps/user_profile/tasks.py`) — Automated match result from Riot API

These three systems can potentially conflict or produce race conditions.

#### C4: Migration Bloat in user_profile
17 out of 37 migrations (46%) have the identical auto-generated name `alter_verificationrecord_id_document_back_and_more`. This suggests repeated `makemigrations` runs modifying the same fields. These need squashing.

**Path:** `apps/user_profile/migrations/`

#### C5: Single Redis Instance for Everything
Cache, Django Channels, Celery broker, Celery result backend, and WebSocket rate limiting all share a single Redis instance on database 0. Cache flushes could wipe Celery messages. On free-tier Upstash, this creates connection pool pressure.

### 3.2 HIGH-Severity Issues

#### H1: Plaintext OAuth Token Storage
`GameOAuthConnection` stores `access_token` and `refresh_token` as plaintext `TextField`. These are live OAuth tokens that grant API access to Riot and Epic accounts.

**File:** `apps/user_profile/models/oauth.py`

#### H2: No Token Refresh Implementation
Neither Riot nor Epic OAuth integrations implement token refresh. When access tokens expire (typically 1 hour), stored tokens become useless. The Riot background sync works around this by using the server-side API key instead.

#### H3: Duplicate Notification Preferences Models
Two models track notification preferences:
- `apps/notifications/models.py` → `NotificationPreference`
- `apps/user_profile/models/settings.py` → `NotificationPreferences`

#### H4: IntegerField-Instead-of-ForeignKey Anti-Pattern
Multiple models across tournaments, economy, moderation, and notifications use `IntegerField` for references that should be `ForeignKey`. This loses referential integrity and cascade behavior.

#### H5: Celery Worker Blocking Anti-Patterns
- `analytics_refresh.py` uses `time.sleep(600)` inside a Celery task, blocking the worker for up to 10 minutes
- `legacy_bridge.py` uses `.apply().get(timeout=600)` (synchronous blocking call within Celery), risking deadlocks

**Files:** `apps/tournaments/tasks/analytics_refresh.py`, `apps/organizations/tasks/legacy_bridge.py`

#### H6: Multiple post_save Receivers on Match
At least 3 separate receivers fire on `Match.save()`:
- `apps/tournaments/signals.py` — bracket advancement + Discord webhooks
- `apps/notifications/subscribers.py` — match completion notifications
- `apps/tournaments/consumers.py` — WebSocket broadcast

No guaranteed execution order. Could cause race conditions.

#### H7: Duplicate Bounty Models
- `apps/user_profile/models/bounties.py` → `Bounty`
- `apps/tournaments/models/bounty.py` → `Bounty`

Two separate bounty systems with different schemas.

### 3.3 MEDIUM-Severity Issues

#### M1: Duplicate Game Identity Configuration
- `apps/games/models.py` → `GamePlayerIdentityConfig`
- `apps/user_profile/models/game_passport_schema.py` → `GamePassportSchema`

Both define how game identities are structured. Should be consolidated.

#### M2: Empty/Skeletal Apps
- `apps/shop/` — Empty storefront
- `apps/ecommerce/` — Empty commerce system
- `apps/spectator/` — Minimal
- `apps/core/api_gateway/` — Empty `__init__.py` only

#### M3: Three Color Systems in Tailwind
- `delta.*` (legacy)
- `dc.*` (unified design system)
- `theme.*` (CSS variable-based game-specific)

#### M4: No-Op Scheduled Tasks
`expire_sponsors_task` and `process_scheduled_promotions_task` are scheduled in Celery Beat but are stubs that delegate to organization tasks that may not have real work.

#### M5: Schedule Collisions
Multiple heavy Celery tasks scheduled for the same time (3 AM, 4 AM) on a single-worker deployment.

#### M6: Duplicate KYC Models
KYC/verification fields exist in both `user_profile` (VerificationRecord) and `tournaments` (KYCRecord).

#### M7: Test Commands as Management Commands
Several test scripts registered as management commands instead of being in `tests/` directories: `test_xp_system.py`, `test_follow_system.py`, `test_fresh_migration.py`, `test_query_budget.py`.

#### M8: No Steam/Epic Background Sync
Only Riot has Celery-based periodic stat sync. Steam and Epic have no background data fetching.

#### M9: Duplicate Wallet Data
`DeltaCrownWallet` and `WalletSettings` both store mobile banking numbers.

---

## 4. Duplicate Systems Inventory

| System | Location A | Location B | Notes |
|--------|-----------|-----------|-------|
| Teams | `apps/teams/` | `apps/organizations/` | Legacy vs vNext, migration incomplete |
| Bounties | `user_profile/models/bounties.py` | `tournaments/models/bounty.py` | Different schemas |
| Notification Prefs | `notifications/models.py` | `user_profile/models/settings.py` | Two models |
| Game Identity Config | `games/models.py` | `user_profile/models/game_passport_schema.py` | Overlapping schemas |
| KYC/Verification | `user_profile/models/audit.py` | `tournaments/models/kyc.py` | Domain overlap |
| Challenge System | `competition/` app | `challenges/` app | Two separate challenge systems |
| Match Results | `tournaments/signals.py` | `tournament_ops/` | Two paths for recording results |
| Color Systems | `delta.*` | `dc.*` / `theme.*` | Three Tailwind configs |
| Event Bus Import | `core/events/bus.py` | `common/events/event_bus.py` | core re-exports common |
| Wallet Numbers | `economy/DeltaCrownWallet` | `economy/WalletSettings` | Duplicate field |
| Staffing | `tournaments/models/staffing.py` | `tournaments/models/staff.py` | Two staffing models |

---

## 5. Incomplete Implementations

| Feature | Status | Location | Notes |
|---------|--------|----------|-------|
| Shop/Storefront | Empty | `apps/shop/` | No models or views |
| Ecommerce | Empty | `apps/ecommerce/` | No implementation |
| API Gateway | Skeleton | `apps/core/api_gateway/` | Only `__init__.py` |
| Spectator Features | Minimal | `apps/spectator/` | Basic structure only |
| Token Refresh (Riot/Epic) | Missing | `user_profile/services/` | Tokens expire, no refresh |
| Steam Background Sync | Missing | — | Only Riot has periodic sync |
| Epic Background Sync | Missing | — | Only Riot has periodic sync |
| Plugin System | Skeleton | `apps/core/plugins/` | Registry exists but no plugins |
| Frontend SDK Tests | Missing | `frontend_sdk/` | "No tests configured yet" |

---

## 6. Technical Risks

### 6.1 Scalability Risks
- Single Redis instance for all subsystems (cache + broker + channels + rate limiting)
- 42-model tournament app with no decomposition
- No database index separation for Redis databases
- Free-tier infrastructure with strict memory/connection limits

### 6.2 Security Risks
- Plaintext OAuth token storage (Riot, Epic)
- OTP exposed in debug mode response metadata (game_passports_delete.py line 174)
- No CSP (Content Security Policy) headers configured
- Google OAuth (`accounts/oauth.py`) uses `urllib.request` with no timeout/error handling

### 6.3 Data Integrity Risks
- IntegerField instead of ForeignKey in multiple models (no referential integrity)
- Multiple post_save receivers on Match with undefined execution order
- Incomplete legacy-to-vNext team migration leaves orphaned references
- Three competing match result pipelines with potential race conditions

### 6.4 Operational Risks
- `time.sleep(600)` in Celery task blocks the worker
- Legacy bridge `.apply().get()` can deadlock
- Single-worker deployment runs 18+ scheduled tasks with timing collisions
- 17 duplicate user_profile migrations need squashing

---

## 7. Game Integration Status

| Provider | Protocol | Games | OAuth Flow | Background Sync | Rate Limiting | Status |
|----------|----------|-------|------------|-----------------|---------------|--------|
| Riot Games | OAuth 2.0 (RSO) | Valorant | Complete | Yes (Celery) | Yes (429 + Retry-After) | **Production-Ready** |
| Steam | OpenID 2.0 | CS2, Dota 2 | Complete | No | No | **Functional** |
| Epic Games | OAuth 2.0 | Rocket League | Complete | No | No | **Functional** |
| Google | OAuth 2.0 | N/A (account auth) | Complete | N/A | No | **Functional (separate)** |

All three game integrations are actively wired and functional. No hardcoded secrets found. All credentials loaded from environment variables.

---

## 8. Game Passport System Status

The Game Passport system exists and is operational:

**Models:**
- `GameProfile` (`user_profile/models/__init__.py`) — Stores game identity per user per game
- `GameOAuthConnection` (`user_profile/models/oauth.py`) — OAuth tokens linked to GameProfile
- `GamePassportSchema` (`user_profile/models/game_passport_schema.py`) — Defines ID field structure per game
- `GamePlayerIdentityConfig` (`games/models.py`) — Overlapping identity config (should be consolidated)

**Features:**
- Manual game ID entry via form with schema-driven validation
- OAuth-based linking for Riot, Steam, Epic
- OTP-verified deletion flow with team/tournament participation checks
- Active Roster UI with live stats (Riot only)
- Game Library UI for adding new passports
- Disconnect confirmation with OTP verification

**Gaps:**
- Only Riot has automated stat sync; Steam/Epic are link-only
- No token refresh for Riot/Epic OAuth
- Duplicate configuration systems (GamePassportSchema vs GamePlayerIdentityConfig)

---

## 9. Match & Tournament System Status

**Tournament Lifecycle:**
1. Creation → Configuration → Registration Open → Registration Closed → In Progress → Completed → Archived
2. Bracket generation (single elimination, round-robin) via `corelib/brackets.py`
3. Match scheduling, no-show detection (2-min Celery checks), auto-advancement (5-min Celery)
4. Payment verification system for paid tournaments
5. Certificate generation with S3 storage

**Match Result Flow:**
1. **Manual submission** via `tournament_ops` — evidence upload, opponent response, auto-confirm after 24h
2. **Signal-based** via `tournaments/signals.py` — auto bracket advancement, Discord webhooks
3. **Automated ingestion** via Riot match API — canonical result correlation

**Leaderboard System:**
- Snapshot-based rankings (tournament, season, all-time)
- Materialized view refresh tasks
- Cold storage compaction for old snapshots

---

## 10. Infrastructure Status

**Deployment:**
- Single Render container runs Daphne + Celery Worker + Discord Bot
- Feature-flagged via environment variables
- Memory-optimized for 512 MB (Render Starter plan)
- Docker config exists for staging + test environments

**Celery Beat Schedule:**
- 4 always-on tasks + 14 feature-flagged tasks
- Configurable via `ENABLE_CELERY_BEAT` env var
- Some schedule collisions at 3 AM / 4 AM

**Monitoring:**
- Prometheus metrics middleware
- Sentry error tracking
- cron-job.org for keep-alive pings

---

*End of Audit Log*
