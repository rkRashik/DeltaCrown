# DeltaCrown — Refactoring Plan

**Last Updated:** 2026-03-16
**Status:** APPROVED (Option A — Continue Development)
**Purpose:** Long-term refactoring strategy organized into safe, incremental phases

---

## Guiding Principles

1. **Never break working OAuth integrations** (Riot, Steam, Epic)
2. **Never break the Game Passport system** (manual + OAuth linking)
3. **Never break active tournament functionality** (bracket generation, match lifecycle)
4. **Maintain migration compatibility** (no destructive migration changes)
5. **Stay within Render 512 MB memory constraint**
6. **Each phase must be independently deployable**

---

## Phase 1 — Critical Stability Fixes

**Goal:** Eliminate operational hazards that could cause data loss or worker deadlocks.

**Systems affected:** Celery tasks, Redis configuration
**Estimated risk:** LOW (fixes anti-patterns without changing business logic)
**Order:** Execute FIRST, before any other work

### Tasks
- [ ] **P1.1** Replace `time.sleep(600)` in `tournaments/tasks/analytics_refresh.py` with `self.retry(countdown=600)` or `apply_async(countdown=600)` chain
- [ ] **P1.2** Replace `.apply().get(timeout=600)` in `organizations/tasks/legacy_bridge.py` with `.apply_async()` + callback pattern
- [ ] **P1.3** Remove or disable no-op scheduled tasks (`expire_sponsors_task`, `process_scheduled_promotions_task`) that delegate to stubs
- [ ] **P1.4** Stagger Celery Beat schedule to avoid 3-4 AM collision (spread tasks across 1-5 AM with 15-min gaps)
- [ ] **P1.5** Squash user_profile migrations (17 duplicates → single squashed migration)

### Validation
- Run full migration check (`python manage.py showmigrations`)
- Verify Celery worker starts and processes tasks without blocking
- Monitor memory usage stays under 150 MB per worker child

---

## Phase 2 — Security Fixes

**Goal:** Protect user data and close known security gaps.

**Systems affected:** OAuth token storage, user_profile views, settings.py
**Estimated risk:** MEDIUM (token encryption requires careful migration)
**Order:** Execute after Phase 1

### Tasks
- [ ] **P2.1** Encrypt OAuth tokens at rest in `GameOAuthConnection` using `django-fernet-fields` or custom `EncryptedTextField`
  - Write data migration to encrypt existing plaintext tokens
  - Update all read paths in services (Riot/Epic/Steam) to decrypt
- [ ] **P2.2** Remove OTP from debug response metadata in `game_passports_delete.py:174`
- [ ] **P2.3** Add `socket_timeout` + error handling to Google OAuth in `accounts/oauth.py`
- [ ] **P2.4** Add CSP headers via middleware or `django-csp`
- [ ] **P2.5** Audit and document all `IntegerField`-as-FK patterns for data integrity review

### Validation
- Verify OAuth linking still works for all three providers after encryption
- Verify token decryption works for Riot background sync
- Run security scan (no plaintext tokens in DB dumps)

---

## Phase 3 — Infrastructure Improvements

**Goal:** Isolate Redis subsystems and improve operational reliability.

**Systems affected:** `deltacrown/settings.py`, Redis configuration
**Estimated risk:** MEDIUM (Redis DB change requires coordinated deploy)
**Order:** Execute after Phase 2

### Tasks
- [ ] **P3.1** Implement Redis database isolation (see Redis Isolation Plan below)
- [ ] **P3.2** Add `KEY_PREFIX` to Django cache configuration
- [ ] **P3.3** Add `prefix` to Channel Layers configuration
- [ ] **P3.4** Add connection pool limits for Celery broker/backend
- [ ] **P3.5** Wire leaderboard tasks into Celery Beat schedule (currently defined but unscheduled)
- [ ] **P3.6** Ensure Celery Beat process is actually running (currently no Beat process in start.sh)

### Redis Isolation Plan

| Consumer | Redis DB | Env Var Override |
|----------|----------|-----------------|
| Django Cache + Sessions + Throttling | DB 0 | `REDIS_URL` (default) |
| Celery Broker | DB 1 | `CELERY_BROKER_URL` |
| Celery Result Backend | DB 2 | `CELERY_RESULT_BACKEND` |
| Channel Layers | DB 3 | `CHANNELS_REDIS_URL` |

**Implementation approach:**
1. Parse `REDIS_URL` base and append `/N` suffix for each consumer
2. Allow explicit env var override for each consumer
3. Add `KEY_PREFIX = "dc_cache:"` to CACHES config
4. Add `prefix: "dc_channels"` to CHANNEL_LAYERS CONFIG

**Settings.py changes:**
```python
_REDIS_BASE = os.getenv('REDIS_URL', 'redis://localhost:6379')
_REDIS_BASE = _REDIS_BASE.rstrip('/').rsplit('/', 1)[0]  # strip any existing /N

# Cache: DB 0
_CACHE_REDIS = os.getenv('CACHE_REDIS_URL', f'{_REDIS_BASE}/0')

# Celery Broker: DB 1
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', f'{_REDIS_BASE}/1')

# Celery Results: DB 2
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', f'{_REDIS_BASE}/2')

# Channels: DB 3
_REDIS_CHANNEL_URL = os.getenv('CHANNELS_REDIS_URL', f'{_REDIS_BASE}/3')
```

### Validation
- Verify each Redis consumer writes to isolated DB
- `redis-cli -n 0 KEYS '*'` should show only cache keys
- `redis-cli -n 1 KEYS '*'` should show only Celery broker keys
- Ensure no data loss during migration (deploy during low traffic)

---

## Phase 4 — Architecture Refactoring

**Goal:** Consolidate duplicate systems and simplify the model graph.

**Systems affected:** Multiple apps with duplicate models
**Estimated risk:** HIGH (requires careful migration and FK reassignment)
**Order:** Execute after Phase 3, one sub-task at a time

### Tasks

#### P4.1 — Consolidate Duplicate Models
- [ ] **P4.1a** Merge `NotificationPreferences` (user_profile) into `NotificationPreference` (notifications) — single source of truth
- [ ] **P4.1b** Merge `GamePassportSchema` (user_profile) into `GamePlayerIdentityConfig` (games) — games app owns identity config
- [ ] **P4.1c** Designate canonical Bounty model (tournament's `TournamentBounty` or user_profile's `Bounty`) and deprecate the other
- [ ] **P4.1d** Remove duplicate wallet data between `DeltaCrownWallet` and `WalletSettings`

#### P4.2 — Complete Team Migration (Legacy → vNext)
- [ ] **P4.2a** Audit all remaining references to `teams.Team` across codebase
- [ ] **P4.2b** Update leaderboards to reference `organizations.Team` instead of legacy
- [ ] **P4.2c** Migrate legacy bridge Celery tasks to call organizations tasks directly
- [ ] **P4.2d** Once all references resolved, mark `teams/` app as DEPRECATED (do not remove yet)

#### P4.3 — Remove Dead Code
- [ ] **P4.3a** Remove empty apps: `shop/`, `ecommerce/`, `core/api_gateway/`
- [ ] **P4.3b** Remove deprecated tournament models: `TournamentStaffRole`, `TournamentStaff` (staff.py)
- [ ] **P4.3c** Remove legacy `Dispute` model from `match.py` (replaced by `DisputeRecord` in dispute.py)
- [ ] **P4.3d** Move test management commands to proper tests/ directories

### Validation
- Full migration check after each model consolidation
- Run all existing tests after each change
- Verify no broken imports or FK references

---

## Phase 5 — Feature Completion

**Goal:** Complete partially-built features and fill functional gaps.

**Systems affected:** OAuth services, tournament ops, leaderboards
**Estimated risk:** MEDIUM (new code, but isolated from existing flows)
**Order:** Execute after Phase 4

### Tasks
- [ ] **P5.1** Implement OAuth token refresh for Riot (using stored refresh_token)
- [ ] **P5.2** Implement OAuth token refresh for Epic Games
- [ ] **P5.3** Design and implement Steam match data ingestion (see Game API Automation Strategy)
- [ ] **P5.4** Design and implement Epic match data ingestion
- [ ] **P5.5** Wire leaderboard snapshot tasks into production Beat schedule
- [ ] **P5.6** Implement unified match result orchestrator (see Unified Match Architecture)

### Validation
- Token refresh tested with expired tokens
- Background sync verified for each provider
- Match result convergence tested with all three pipelines

---

## Phase 6 — Game API Automation

**Goal:** Full automated stat ingestion for all supported games.

**Systems affected:** user_profile services/tasks, tournament_ops
**Estimated risk:** MEDIUM (external API dependencies)
**Order:** Execute after Phase 5

### Tasks
- [ ] **P6.1** Build provider abstraction layer (`GameAPIProvider` base class)
- [ ] **P6.2** Implement Steam match history fetcher (CS2 via Steam Web API)
- [ ] **P6.3** Implement Epic match history fetcher (Rocket League via Epic API)
- [ ] **P6.4** Add rate limiting for all providers (token bucket per provider)
- [ ] **P6.5** Add circuit breaker pattern for API failures
- [ ] **P6.6** Implement per-provider Celery sync tasks with backoff
- [ ] **P6.7** Update Active Roster UI to show stats for Steam/Epic games

### Validation
- End-to-end test: link account → sync stats → display in UI
- Rate limit compliance verified per provider
- Failure recovery tested (API down, token expired, rate limited)

---

## Phase Summary

| Phase | Goal | Risk | Dependencies |
|-------|------|------|-------------|
| 1 | Critical Stability | LOW | None |
| 2 | Security | MEDIUM | Phase 1 |
| 3 | Infrastructure | MEDIUM | Phase 2 |
| 4 | Architecture | HIGH | Phase 3 |
| 5 | Feature Completion | MEDIUM | Phase 4 |
| 6 | Game API Automation | MEDIUM | Phase 5 |

**Estimated total work:** Phases 1-3 are small (1-2 days each). Phase 4 is moderate (3-5 days). Phases 5-6 are substantial (1-2 weeks each).
