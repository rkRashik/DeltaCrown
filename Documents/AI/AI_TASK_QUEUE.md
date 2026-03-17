# DeltaCrown — AI Task Queue

**Last Updated:** 2026-03-17
**Purpose:** Prioritized, actionable task list for AI development sessions
**Convention:** Mark tasks [x] when complete, add date. New tasks go to bottom of their priority group.

---

## ACTIVE SPRINT — Phase 1: Critical Stability Fixes — COMPLETE

- [x] **TASK-001** Fix Celery blocking in `analytics_refresh.py` (2026-03-17)
  - Replaced `time.sleep(600)` with `self.apply_async(countdown=..., kwargs={'_jitter_done': True})`

- [x] **TASK-002** Fix Celery deadlock in `legacy_bridge.py` (2026-03-17)
  - Replaced `.apply().get(timeout=600)` with direct function call

- [x] **TASK-003** Stagger Celery Beat schedule (2026-03-17)
  - Daily tasks spread 1:00-3:00 AM with 30-min gaps, no collisions

- [x] **TASK-004** Squash user_profile migrations — PLAN PREPARED (2026-03-17)
  - Plan: `Documents/AI/MIGRATION_SQUASH_PLAN.md`
  - Recommend squash 0001-0034, keep 0035-0037 (OAuth chain)
  - 21/37 migrations are redundant VR AlterField no-ops
  - Execution deferred until founder approves

- [x] **TASK-005** Disable no-op scheduled tasks (2026-03-17)
  - Removed `expire-sponsors-daily` from base schedule
  - Removed `process-scheduled-promotions` from heavy schedule
  - Task functions kept in legacy_bridge.py for backward compat

## ACTIVE SPRINT — Phase 2: Security Fixes — COMPLETE

- [x] **TASK-006** Encrypt OAuth tokens at rest (2026-03-17)
  - Created: `apps/user_profile/fields.py` (EncryptedTextField using Fernet)
  - Updated: `apps/user_profile/models/oauth.py` (access_token, refresh_token)
  - Created: migration `0038_encrypt_oauth_tokens.py` (schema + data migration)
  - Added: `FIELD_ENCRYPTION_KEY` env var support in settings.py
  - Risk: MEDIUM

- [x] **TASK-007** Remove OTP from debug response (2026-03-17)
  - File: `apps/user_profile/views/game_passports_delete.py:174`
  - Fix: Removed `otp_code` from error response metadata entirely
  - Risk: LOW

- [x] **TASK-008** Secure Google OAuth (2026-03-17)
  - File: `apps/accounts/oauth.py`
  - Fix: Added error handling for HTTPError/URLError, sanitized error messages, added logging
  - Removed unused `os` import
  - Risk: LOW

- [x] **TASK-009** Add CSP headers (2026-03-17)
  - Created: `deltacrown/middleware/security_headers.py` (CSPMiddleware)
  - Updated: `deltacrown/settings.py` (added to MIDDLEWARE after SecurityMiddleware)
  - Policy: script/style 'unsafe-inline' + CDN allowlist, frame-src/object-src none
  - Risk: LOW

## ACTIVE SPRINT — Phase 3: Infrastructure Improvements — COMPLETE

- [x] **TASK-010** Implement Redis DB isolation (2026-03-17)
  - File: `deltacrown/settings.py`
  - Added `_redis_url_with_db()` helper, `_BASE_REDIS_URL` variable
  - Cache=DB0 (KEY_PREFIX="dc"), Broker=DB1, Results=DB2, Channels=DB3 (prefix="dc-ws")
  - Risk: MEDIUM

- [x] **TASK-011** Add Celery Beat to startup scripts (2026-03-17)
  - Files: `start.sh`, `bin/start_render.sh`
  - Added Beat process gated by `ENABLE_CELERY_BEAT` env var (default 0)
  - Updated cleanup handler in both scripts to kill BEAT_PID on shutdown
  - Risk: LOW

- [x] **TASK-012** Wire leaderboard tasks into Beat (2026-03-17)
  - File: `deltacrown/celery.py`
  - Added 8 tasks to `_heavy_schedule` (gated by ENABLE_CELERY_BEAT=1):
    - `snapshot-active-tournaments` (every 30 min)
    - `snapshot-all-time-global` (daily 03:30 UTC)
    - `hourly-leaderboard-refresh` (every hour at :45)
    - `mark-inactive-players` (daily 04:00 UTC)
    - `compact-old-snapshots` (weekly Sunday 04:30 UTC)
    - `nightly-user-analytics-refresh` (daily 05:00 UTC)
    - `nightly-team-analytics-refresh` (daily 05:30 UTC)
    - `seasonal-rollover` (monthly 00:00 UTC on 1st)
  - Risk: LOW

---

## ACTIVE SPRINT — Phase 4: Architecture Refactoring (IN PROGRESS)

- [x] **TASK-013** Fix stale notification endpoint bug (2026-03-17)
  - Removed: `update_notification_preferences` + `get_notification_preferences` from `settings_api.py`
    → these used wrong field names (e.g. `email_tournament_reminders`) → always returned 500
  - Removed: their imports + URL registrations from `user_profile/urls.py`
  - Active endpoints: `notifications_settings_get` / `notifications_settings_save` (settings_notifications_api.py)
  - Note: `user_profile.NotificationPreferences` (enforcement) and `notifications.NotificationPreference` (dispatch)
    are parallel models with different FK targets and schemas — full merge deferred (complex)
  - Risk: LOW

- [x] **TASK-014** Rename `GamePassportSchema` → `GameChoiceConfig` across all production code (2026-03-17)
  - Renamed class in `apps/user_profile/models/game_passport_schema.py`; `db_table` pinned to prevent migration
  - Added backward-compat alias `GamePassportSchema = GameChoiceConfig` in model file and `models/__init__.py`
  - Updated all 23 files: services, admin, views, validators, tests, fixtures, JS
  - Note: Full model consolidation into `GamePlayerIdentityConfig` (games app) is a separate future task

- [ ] **TASK-015** Complete team migration (legacy → vNext) — DEFERRED (complex)
  - Audit all `teams.Team` references
  - Update leaderboards
  - Migrate Celery tasks from legacy bridge to direct calls
  - Status: Needs scoping session before attempting

- [x] **TASK-016** Remove dead code (2026-03-17)
  - Removed: `apps/core/api_gateway/` (208 lines — never imported anywhere)
  - Removed: 11 dev management commands (test_xp_system, test_follow_system,
    test_fresh_migration, migration_truth_test, test_query_budget, seed_org,
    dev_bootstrap_smoke_check, seed_sample_data, seed_registration_data,
    seed_demo_environment, seed_demo_tournaments)
  - Kept: `shop/`, `ecommerce/`, `staff.py` (all actively used — initial audit incorrect)
  - Kept: Operational seeds (seed_game_passport_schemas, seed_full_tournament, etc.)
  - Risk: LOW

---

## BACKLOG — Phase 5: Feature Completion

- [x] **TASK-017** Implement Riot token refresh (2026-03-17)
  - Added `refresh_riot_access_token(conn)` to `oauth_riot_service.py`
  - Handles 400/401 → status 401, 5xx → 502, network → 504
  - Updates access_token, refresh_token (if rotated), expires_at, last_synced_at

- [x] **TASK-018** Implement Epic token refresh (2026-03-17)
  - Added `refresh_epic_access_token(conn)` to `oauth_epic_service.py`
  - Same pattern as Riot; handles Epic-specific `errorCode`/`errorMessage` keys

- [x] **TASK-019** Design + implement unified match result orchestrator (2026-03-17)
  - Implemented `_maybe_finalize_result()` in `ResultSubmissionService`
    → Instantiates `ResultVerificationService` + `MatchService` and calls `finalize_submission_after_verification()`
    → Errors logged; submission stays in CONFIRMED/AUTO_CONFIRMED for organizer inbox on failure
  - Fixed `dismiss_dispute` reschedule gap in `DisputeService._resolve_dismiss_dispute()`
    → Now schedules `auto_confirm_submission_task` with `eta=new_deadline`
  - Updated `auto_confirm_submission_task` to pass `DisputeAdapter` so auto-finalization runs

- [x] **TASK-020** Implement Steam background sync (2026-03-17)
  - Added `sync_all_active_steam_passports` task to `apps/user_profile/tasks.py`
  - Fetches fresh persona name + avatars via `fetch_player_summary(steam_id)`
  - Updates `passport.ign`, `passport.in_game_name`, `passport.metadata`, `conn.last_synced_at`
  - Wired into Beat: every 4 hours at :10 past (conservative for Steam API rate limits)

- [x] **TASK-021** Implement Epic background sync (2026-03-17)
  - Added `sync_all_active_epic_passports` task to `apps/user_profile/tasks.py`
  - Proactively refreshes Epic OAuth tokens expiring within 30-min window
  - Handles `status_code=401` (requires_reauth list) vs transient failures (errors list)
  - Wired into Beat: every hour at :50 (Epic tokens expire every 4h)

---

## BACKLOG — Phase 6: Game API Automation — COMPLETE

- [x] **TASK-022** Build GameAPIProvider abstraction layer (2026-03-17)
  - Created `apps/user_profile/services/base_game_api.py`
  - `GameAPIError` dataclass + `GameAPIProvider` Protocol (runtime_checkable)
- [x] **TASK-023** Steam CS2 stats fetcher (2026-03-17)
  - Created `apps/user_profile/services/steam_cs2_stats_service.py`
  - `fetch_cs2_stats(steam_id)` — uses `ISteamUserStats/GetUserStatsForGame/v2/?appid=730`
  - Returns normalized dict: `kd_ratio`, `win_rate`, `headshot_rate`, `total_time_played_seconds`, etc.
  - Note: No per-match CS2 history via public Steam Web API — aggregate stats only
- [x] **TASK-024** Epic profile fetcher (2026-03-17)
  - Created `apps/user_profile/services/epic_rl_stats_service.py`
  - `fetch_epic_profile(conn)` — OpenID userinfo endpoint, auto-refreshes token
  - Note: `basic_profile` scope cannot access Rocket League match history
- [x] **TASK-025** Per-provider rate limiting (2026-03-17)
  - Created `apps/user_profile/services/rate_limiter.py`
  - Redis-backed token bucket: `RateLimiter(provider, rate_per_second, burst)`
  - `try_acquire()` (non-blocking) + `acquire(timeout_seconds)` (blocking)
- [x] **TASK-026** Circuit breaker for API failures (2026-03-17)
  - Created `apps/user_profile/services/circuit_breaker.py`
  - Redis-backed; states: CLOSED → OPEN → HALF_OPEN → CLOSED
  - `CircuitBreaker(provider, failure_threshold=5, cooldown_seconds=120)`
- [x] **TASK-027** Update Active Roster UI for Steam/Epic stats (2026-03-17)
  - Updated `sync_all_active_steam_passports` in `tasks.py`
  - CS2 stats now written back to `GameProfile.kd_ratio`, `win_rate`, `hours_played` columns
  - Template `_roster_card.html` already reads these columns — no template change needed

---

## COMPLETED TASKS

- [x] **2026-03-16** Full repository audit (9 phases)
- [x] **2026-03-16** Created SYSTEM_AUDIT_LOG.md
- [x] **2026-03-16** Created AI_DEVELOPMENT_TRACKER.md
- [x] **2026-03-16** Created AI_SYSTEM_MAP.md
- [x] **2026-03-16** Created AI_ARCHITECTURE.md
- [x] **2026-03-16** Created AI_REFACTOR_PLAN.md
- [x] **2026-03-16** Created AI_TASK_QUEUE.md (this file)
- [x] **2026-03-16** Designed unified match result architecture
- [x] **2026-03-16** Designed Redis isolation plan
- [x] **2026-03-16** Designed game API automation strategy
- [x] **2026-03-16** Designed tournament decomposition plan
- [x] **2026-03-17** TASK-001: Fixed Celery blocking in analytics_refresh.py
- [x] **2026-03-17** TASK-002: Fixed Celery deadlock in legacy_bridge.py
- [x] **2026-03-17** TASK-003: Staggered Celery Beat schedule (1:00-3:00 AM)
- [x] **2026-03-17** TASK-004: Prepared migration squash plan (MIGRATION_SQUASH_PLAN.md)
- [x] **2026-03-17** TASK-005: Disabled no-op scheduled tasks
- [x] **2026-03-17** Phase 1 complete — all Critical Stability Fixes done
- [x] **2026-03-17** TASK-007: Removed OTP leak from game_passports_delete.py
- [x] **2026-03-17** TASK-008: Secured Google OAuth error handling in accounts/oauth.py
- [x] **2026-03-17** TASK-009: Added CSP headers middleware (security_headers.py)
- [x] **2026-03-17** TASK-006: Encrypted OAuth tokens at rest (EncryptedTextField + migration 0038)
- [x] **2026-03-17** Phase 2 complete — all Security Fixes done
- [x] **2026-03-17** TASK-010: Redis DB isolation (Cache=DB0, Broker=DB1, Results=DB2, Channels=DB3)
- [x] **2026-03-17** TASK-011: Added Celery Beat to start.sh + bin/start_render.sh with graceful shutdown
- [x] **2026-03-17** TASK-012: Wired 8 leaderboard tasks into Beat heavy schedule (staggered 03:30–05:30)
- [x] **2026-03-17** Phase 3 complete — all Infrastructure Improvements done
- [x] **2026-03-17** TASK-013: Fixed stale notification endpoint bug (removed 2 broken views + URL entries)
- [x] **2026-03-17** TASK-016: Removed dead code (api_gateway + 11 dev management commands)
- [x] **2026-03-17** TASK-017: Implemented refresh_riot_access_token() in oauth_riot_service.py
- [x] **2026-03-17** TASK-018: Implemented refresh_epic_access_token() in oauth_epic_service.py
- [x] **2026-03-17** TASK-019: Wired auto-finalization orchestrator (ResultVerificationService) + fixed dismiss_dispute reschedule gap
- [x] **2026-03-17** TASK-020: Steam background sync (every 4h, persona name/avatar refresh)
- [x] **2026-03-17** TASK-021: Epic background sync (hourly token refresh, proactive 30-min window)
- [x] **2026-03-17** Phase 5 complete — all Feature Completion tasks done
- [x] **2026-03-17** TASK-022: GameAPIProvider Protocol abstraction (base_game_api.py)
- [x] **2026-03-17** TASK-023: Steam CS2 aggregate stats fetcher (steam_cs2_stats_service.py)
- [x] **2026-03-17** TASK-024: Epic profile fetcher with token auto-refresh (epic_rl_stats_service.py)
- [x] **2026-03-17** TASK-025: Redis token-bucket rate limiter (rate_limiter.py)
- [x] **2026-03-17** TASK-026: Redis circuit breaker (circuit_breaker.py)
- [x] **2026-03-17** TASK-027: CS2 stats written back to GameProfile columns (kd_ratio/win_rate/hours_played)
- [x] **2026-03-17** Phase 6 complete — all Game API Automation tasks done
- [x] **2026-03-17** TASK-014: Renamed GamePassportSchema → GameChoiceConfig across 23 files (class rename, db_table pinned, backward-compat alias)

---

## AI SESSION RULES

When starting a new AI session on this project:

1. **READ FIRST:** `Documents/AI/AI_SYSTEM_MAP.md` (architecture overview)
2. **CHECK:** `Documents/AI/AI_TASK_QUEUE.md` (this file — current tasks)
3. **REFERENCE:** `Documents/AI/AI_ARCHITECTURE.md` (technical details)
4. **FOLLOW:** `Documents/AI/AI_REFACTOR_PLAN.md` (phase ordering)
5. **UPDATE:** This file after completing tasks
6. **BATCH:** Multiple dev tasks per session for efficiency
7. **NEVER:** Skip phases or implement features before stability fixes
8. **NEVER:** Break OAuth integrations, Game Passports, or active tournament features
