# DeltaCrown — Architecture Reference

**Last Updated:** 2026-03-16
**Purpose:** Technical architecture documentation for AI development sessions

---

## 1. Django Project Layout

```
deltacrown/           # Project package
  settings.py         # 1,761 lines — ALL config in one file
  celery.py           # Celery app + Beat schedule (18 tasks)
  urls.py             # Root URL routing
  asgi.py / wsgi.py   # Server entry points

apps/                 # All Django apps
  accounts/           # Auth (User model, Google OAuth, signals)
  user_profile/       # 18 model files, OAuth services, Game Passports
  players/            # Player bridge entity (User ↔ Game)
  games/              # Game definitions, identity configs
  tournaments/        # 42 model files (70 classes), services, tasks, admin, API
  tournament_ops/     # Match result submission + dispute pipeline
  organizations/      # vNext teams (org hierarchy, Discord sync)
  teams/              # Legacy teams (DEPRECATED)
  competition/        # Independent competition system
  challenges/         # 1v1/team challenges
  leaderboards/       # Ranking snapshots, materialized views
  economy/            # DeltaCrown virtual currency, wallets
  notifications/      # Email/Discord/in-app notifications
  moderation/         # Content moderation
  common/             # Event bus, API responses, game registry
  core/               # Service registry, health, plugin registry
  corelib/            # Brackets, utilities, idempotency
  siteui/             # Community (posts, likes, comments)
  corepages/          # Static/landing pages
  search/             # Search functionality
  dashboard/          # Admin dashboards
  shop/               # EMPTY
  ecommerce/          # EMPTY
  spectator/          # SKELETAL
  support/            # Support tickets
```

---

## 2. Database Architecture

### Key Models and Their Relationships

**User Identity Chain:**
```
accounts.User (Django auth model)
  └── user_profile.UserProfile (1:1, extended profile)
        ├── user_profile.GameProfile (1:N, one per game = Game Passport)
        │     └── user_profile.GameOAuthConnection (1:1, OAuth tokens)
        ├── user_profile.FollowRelationship (N:N, social follows)
        ├── user_profile.UserBadge (1:N, earned badges)
        └── user_profile.UserActivity (1:N, activity log)
```

**Tournament Model Hub (70 classes):**
```
tournaments.Tournament (THE god-model, ~40+ FKs point here)
  ├── tournaments.Registration (player/team signup)
  │     ├── tournaments.Payment (1:1, payment proof)
  │     └── tournaments.CheckIn (1:1, check-in status)
  ├── tournaments.Bracket (1:1, bracket structure)
  │     └── tournaments.BracketNode (tree, links to Match 1:1)
  ├── tournaments.Match (match lifecycle)
  │     ├── tournaments.MatchResultSubmission (result pipeline)
  │     │     ├── tournaments.ResultVerificationLog (audit trail)
  │     │     └── tournaments.DisputeRecord (disputes)
  │     ├── tournaments.MatchPlayerStat (per-player stats)
  │     └── tournaments.MatchVetoSession (map bans)
  ├── tournaments.TournamentResult (1:1, final placements)
  ├── tournaments.Certificate (PDF/PNG generation)
  ├── tournaments.TournamentStaffAssignment (staff roles)
  └── tournaments.GameMatchConfig (1:1, game rules)
```

**Cross-App Decoupling Pattern:**
Migration `0008_decouple_cross_app_fks` converted team FKs to IntegerFields:
- `Match.team1_id` / `team2_id` → IntegerField (was FK to teams.Team)
- `Registration.team_id` → IntegerField
- `GroupStanding.team_id` → IntegerField
This allows tournaments to operate without direct FK dependency on teams/organizations.

---

## 3. Match Result Architecture (Three Pipelines)

### Pipeline A: Direct Submission (MatchService)
```
Player → MatchService.submit_result()
  → Validates scores, sets winner/loser
  → Match.state = 'pending_result'
  → match.save() → post_save signals fire
  → Opponent notification sent

Opponent → MatchService.confirm_result()
  → Match.state = 'completed'
  → match.save() → post_save signals fire
  → BracketService.update_bracket_after_match()
  → Event bus: match.completed
```

### Pipeline B: Formal Submission (tournament_ops)
```
Player → ResultSubmissionService.submit_result()
  → Creates MatchResultSubmission (status='pending')
  → Schedules auto_confirm_submission_task (24h)

Opponent → opponent_response() → 'confirm' or 'dispute'

Confirmation → ResultVerificationService.finalize_submission_after_verification()
  → Validates payload schema
  → MatchAdapter.update_match_result() → match.save()
  → All post_save signals fire (same as Pipeline A)
  → Submission status = 'finalized'
```

### Pipeline C: Automated Ingestion (Riot API)
```
Celery: sync_all_active_riot_passports (every 20 min)
  → For each active Riot GameProfile:
    → Fetch recent Valorant matches from Riot API
    → Correlate to internal Match via lobby_info or time window
    → Deduplicate via ingestion_fingerprint
    → Create MatchResultSubmission (source='riot_api')
    → Immediately auto-confirm
    → Finalize via Pipeline B's verification service
    → Update GameProfile.metadata with aggregated stats
```

### Shared Side Effects (on Match.state = 'completed')
All three pipelines converge at `match.save()` which triggers:
1. `handle_match_state_change` → in-app notification + Discord webhook
2. `sync_match_to_profile_history` → ProfileMatch records + achievements
3. `broadcast_match_update` → WebSocket to 4 channel groups
4. `match_events` → lightweight secondary notification listener

---

## 4. Celery Task System

### Worker Configuration
- **Concurrency:** 1 (single process)
- **Max memory:** 150 MB per child
- **Max tasks per child:** 50 (then recycle)
- **Hard time limit:** 30 minutes
- **Soft time limit:** 25 minutes
- **Prefetch multiplier:** 1

### Beat Schedule (18 tasks total)
**Always-on (4 tasks):**
- Rankings recompute (daily 2 AM)
- Digest emails (daily 8 AM)
- Clean expired invites (every 6h)
- Expire sponsors (daily 3 AM)

**Feature-flagged ENABLE_CELERY_BEAT=1 (14 tasks):**
- Auto-advance tournaments (every 5 min)
- Check no-show matches (every 2 min)
- Notify match ready (every 5 min)
- Expire overdue payments (every 15 min)
- Auto-confirm stale submissions (every 30 min)
- Riot passport sync (every 20 min)
- vNext team rankings (daily 3 AM)
- Inactivity decay (daily 3:30 AM)
- Org rankings (daily 4 AM)
- Tournament wrapup check (hourly :15)
- Auto-archive tournaments (daily 4 AM)
- Opponent response reminder (hourly :20)
- Dispute escalation (every 6h :45)
- Scheduled promotions (hourly)

### Known Anti-Patterns
- `analytics_refresh.py`: `time.sleep(600)` blocks worker for 10 minutes
- `legacy_bridge.py`: `.apply().get(timeout=600)` synchronous blocking call
- Schedule collisions at 3-4 AM (rankings, decay, archive all overlap)

---

## 5. Redis Usage (SINGLE DB — No Isolation)

All subsystems share `REDIS_URL` → same Redis DB 0:

| Consumer | Key Patterns | Library |
|----------|-------------|---------|
| Django Cache | `:1:*` (default prefix) | `django.core.cache.backends.redis.RedisCache` |
| Sessions | `:1:django.contrib.sessions.cache*` | via cached_db backend |
| DRF Throttling | via cache backend | DRF built-in |
| Channel Layers | `asgi:*`, `specific.*` | `channels_redis.core.RedisChannelLayer` |
| Celery Broker | `celery`, `_kombu.binding.*` | Kombu |
| Celery Results | `celery-task-meta-*` | Celery |
| Discord Bot Status | `discord_bot_online:*` | via cache |

**Risk:** `cache.clear()` or cache eviction could destroy Celery messages or channel state.

---

## 6. OAuth Token Storage

```
GameOAuthConnection (user_profile/models/oauth.py)
  ├── provider: CharField (riot, steam, epic)
  ├── access_token: TextField (PLAINTEXT)
  ├── refresh_token: TextField (PLAINTEXT, nullable)
  ├── token_expires_at: DateTimeField (nullable)
  ├── provider_account_id: CharField
  ├── last_synced_at: DateTimeField
  └── game_profile: ForeignKey(GameProfile)
```

**Security issue:** Tokens stored unencrypted.
**Functional issue:** No token refresh implementation for any provider.
**Workaround:** Riot background sync uses server-side API key, not user OAuth tokens.

---

## 7. Event Bus

```
common/events/event_bus.py → actual implementation
core/events/bus.py → re-exports from common (thin wrapper)
```

Events published:
- `match.completed` (from MatchService)
- `MatchResultSubmittedEvent`, `MatchResultConfirmedEvent`, `MatchResultAutoConfirmedEvent`
- `MatchResultDisputedEvent`, `MatchResultVerifiedEvent`, `MatchResultFinalizedEvent`
- `MatchForceCompletedEvent`, `MatchResultOverriddenEvent`
- `DisputeResolvedEvent`

---

## 8. Settings File Key Sections

| Section | Lines (approx) | Content |
|---------|----------------|---------|
| Environment variables | 1-130 | `DEPLOYMENT_TIER`, tier-based limits |
| Installed apps | 131-180 | 27 apps + third-party |
| Middleware | 181-220 | 18 middleware layers |
| Templates | 221-260 | Template configuration |
| Database | 261-300 | Neon PostgreSQL via `dj-database-url` |
| Cache/Redis | 399-435 | Tier-based max connections |
| REST Framework | 440-590 | DRF + JWT config |
| Allauth | 590-700 | Google OAuth |
| Channels | 938-964 | WebSocket config |
| Celery | 996-1050 | Broker, backend, serialization |
| OAuth credentials | ~700-900 | Riot, Steam, Epic client IDs/secrets |
| Sentry | 1050-1070 | Error tracking |
| Cloudinary/S3 | 1070-1150 | Storage backends |
| Prometheus | 1150-1180 | Metrics |
