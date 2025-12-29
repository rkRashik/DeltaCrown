# User Profile - Services Inventory

**Generated:** December 28, 2025  
**Purpose:** Document all services, their usage, and activation status

---

## Service Overview

| Service File | Primary Class/Functions | Status | Used By |
|-------------|------------------------|--------|---------|
| `profile_context.py` | `build_public_profile_context()` | ✅ **ACTIVE** | V2 views (fe_v2.py) |
| `game_passport_service.py` | `GamePassportService` | ✅ **ACTIVE** | Passport views, admin |
| `privacy_policy.py` | `ProfileVisibilityPolicy` | ✅ **ACTIVE** | profile_context, views |
| `privacy_settings_service.py` | `PrivacySettingsService` | ✅ **ACTIVE** | Settings views |
| `follow_service.py` | `FollowService` | ✅ **ACTIVE** | Follow views |
| `activity_service.py` | `UserActivityService` | ✅ **ACTIVE** | Event tracking |
| `stats_service.py` | `StatsUpdateService` | ✅ **ACTIVE** | Stats recomputation |
| `audit.py` | `AuditService` | ✅ **ACTIVE** | All mutation endpoints |
| `xp_service.py` | `XPService`, `award_xp()` | ✅ **ACTIVE** | Gamification |
| `achievement_service.py` | `award_achievement()`, checkers | ✅ **ACTIVE** | Gamification |
| `certificate_service.py` | Certificate generation | ✅ **ACTIVE** | Tournament system |
| `economy_sync.py` | Wallet sync functions | ✅ **ACTIVE** | Economy integration |
| `tournament_stats.py` | `TournamentStatsService` | ✅ **ACTIVE** | Tournament integration |
| `public_id.py` | `PublicIDGenerator` | ✅ **ACTIVE** | Profile creation |

---

## 1. `profile_context.py` - Profile Context Service

**File:** `services/profile_context.py` (451 lines)  
**Purpose:** Privacy-safe context builder for profile views

### Primary Function

```python
def build_public_profile_context(
    viewer: Optional[User],
    username: str,
    requested_sections: Optional[List[str]] = None,
    activity_page: int = 1,
    activity_per_page: int = 25
) -> Dict[str, Any]
```

### Used By

- ✅ `views/fe_v2.py:profile_public_v2` - Main public profile view
- ✅ `views/fe_v2.py:profile_activity_v2` - Activity feed view
- ✅ `views/fe_v2.py:profile_settings_v2` - Settings view (with owner_only section)
- ✅ `views/fe_v2.py:profile_privacy_v2` - Privacy settings view

### Key Features

- Returns ONLY safe primitives/JSON (NO raw ORM objects)
- Uses `ProfileVisibilityPolicy` for field filtering
- Paginated activity feed
- Lazy-loaded sections (basic, stats, activity, games, social, owner_only)
- Owner vs Public context separation

### Internal Helper Functions

| Function | Purpose |
|----------|---------|
| `_build_basic_profile_data()` | Build safe profile dict (display_name, bio, etc.) |
| `_build_stats_data()` | Get tournament/match stats from UserProfileStats |
| `_build_activity_feed()` | Paginated UserActivity feed |
| `_build_game_profiles_data()` | Get game passports (from JSON or GameProfile model) |
| `_build_social_links_data()` | Get social links (from fields or SocialLink model) |
| `_build_owner_data()` | Owner-only data (wallet, settings, edit actions) |

### Status

✅ **ACTIVE & CANONICAL** - This is the primary data service for V2 views

---

## 2. `game_passport_service.py` - Game Passport Service

**File:** `services/game_passport_service.py` (702 lines)  
**Purpose:** First-class game identity management

### Primary Class

```python
class GamePassportService:
    # CRUD Operations
    create_passport(user, game, ign, discriminator=None, platform=None, region='', ...)
    update_passport(user, game, updates, actor_user_id=None, ...)
    delete_passport(user, game, actor_user_id=None, ...)
    get_passport(user, game)
    get_all_passports(user)
    
    # Privacy & Display
    set_visibility(user, game, visibility, actor_user_id=None)
    set_lft(user, game, is_lft, actor_user_id=None)
    pin_passport(user, game, actor_user_id=None)
    unpin_passport(user, game, actor_user_id=None)
    reorder_passports(user, game_order, actor_user_id=None)
```

### Used By

- ✅ `views/passport_create.py:create_passport` - Create new passport
- ✅ `views/passport_api.py:toggle_lft` - Toggle looking-for-team
- ✅ `views/passport_api.py:set_visibility` - Change privacy
- ✅ `views/passport_api.py:pin_passport` - Pin/unpin
- ✅ `views/passport_api.py:reorder_passports` - Change order
- ✅ `views/passport_api.py:delete_passport` - Delete
- ✅ `views/fe_v2.py:profile_public_v2` - Display passports
- ✅ `admin/game_passports.py` - Admin operations

### Key Features

- Structured identity (IGN + discriminator + platform + region)
- Identity change cooldown enforcement (30 days)
- Alias history tracking (GameProfileAlias)
- Uniqueness validation (identity_key)
- Full audit trail (UserAuditEvent)
- Privacy controls (PUBLIC, FRIENDS_ONLY, PRIVATE)
- Pinning/ordering management (max 6 pinned)

### Architecture Notes

- ❌ **NO JSON writes** - All operations through GameProfile model
- ✅ **Validation** - Uses GamePassportSchemaValidator
- ✅ **Atomic** - All operations wrapped in @transaction.atomic
- ✅ **Audit** - Every operation logged to AuditService

### Status

✅ **ACTIVE & CRITICAL** - Core service for game identity management

---

## 3. `privacy_policy.py` - Profile Visibility Policy

**File:** `services/privacy_policy.py` (265 lines)  
**Purpose:** Centralized privacy enforcement

### Primary Class

```python
class ProfileVisibilityPolicy:
    # Field Sets
    PUBLIC_FIELDS: Set[str]          # display_name, bio, avatar, level, etc.
    OWNER_ONLY_FIELDS: Set[str]      # email, phone, address, DOB, etc.
    STAFF_ONLY_FIELDS: Set[str]      # internal_notes, moderation_flags
    
    # Methods
    can_view_profile(viewer, profile) -> bool
    get_visible_fields(viewer, profile) -> Set[str]
    filter_profile_data(viewer, profile, data) -> Dict[str, Any]
```

### Used By

- ✅ `services/profile_context.py` - Field filtering in context builder
- ✅ `views/fe_v2.py` - Privacy checks in views
- ✅ `views/passport_api.py` - Passport privacy
- ✅ `views/settings_api.py` - Settings visibility

### Field Categories

**Public Fields (Always Visible):**
- Identity: display_name, slug, avatar, banner, bio, pronouns
- Stats: level, xp, reputation_score, skill_rating
- Location: country, region (NOT city/address)
- Social: youtube_link, twitch_link, discord_id, etc.
- Games: game_profiles, preferred_games

**Owner-Only Fields (Private):**
- Contact: email, phone
- Location: city, postal_code, address
- Legal: real_full_name, date_of_birth, nationality, gender
- Emergency: emergency_contact_*
- Economy: deltacoin_balance, lifetime_earnings
- KYC: kyc_status, kyc_verified_at

### Privacy Roles

| Viewer Role | Visible Fields |
|------------|---------------|
| Anonymous | PUBLIC_FIELDS only |
| Authenticated (non-owner) | PUBLIC_FIELDS only |
| Owner (self) | ALL_FIELDS |
| Staff/Superuser | ALL_FIELDS |

### Status

✅ **ACTIVE & CRITICAL** - Enforces all privacy rules

---

## 4. `privacy_settings_service.py` - Privacy Settings Service

**File:** `services/privacy_settings_service.py`  
**Purpose:** Manage PrivacySettings model

### Primary Class

```python
class PrivacySettingsService:
    get_or_create(user_profile) -> PrivacySettings
    update_settings(user_profile, settings_dict) -> PrivacySettings
    apply_preset(user_profile, preset) -> PrivacySettings  # PUBLIC, PROTECTED, PRIVATE
    get_privacy_context(user_profile) -> Dict
```

### Used By

- ✅ `views/fe_v2.py:profile_privacy_v2` - Privacy settings page
- ✅ `views/settings_api.py:get_privacy_settings` - API endpoint
- ✅ `views/settings_api.py:update_privacy_settings` - API endpoint
- ✅ `views/legacy_views.py:privacy_settings_save_safe` - Safe mutation endpoint

### Features

- Get/create PrivacySettings for user
- Update individual toggles
- Apply privacy presets (PUBLIC, PROTECTED, PRIVATE)
- Return context dict for templates

### Status

✅ **ACTIVE** - Used by V2 privacy views

---

## 5. `follow_service.py` - Follow System Service

**File:** `services/follow_service.py`  
**Purpose:** Manage Follow relationships

### Primary Class

```python
class FollowService:
    follow_user(follower, followed) -> Follow
    unfollow_user(follower, followed) -> bool
    is_following(follower, followed) -> bool
    get_followers(user) -> QuerySet
    get_following(user) -> QuerySet
    get_follower_count(user) -> int
    get_following_count(user) -> int
```

### Used By

- ✅ `views/legacy_views.py:follow_user` - Follow action
- ✅ `views/legacy_views.py:unfollow_user` - Unfollow action
- ✅ `views/legacy_views.py:follow_user_safe` - Safe follow with audit
- ✅ `views/legacy_views.py:unfollow_user_safe` - Safe unfollow with audit
- ✅ `views/legacy_views.py:followers_list` - Followers modal
- ✅ `views/legacy_views.py:following_list` - Following modal

### Features

- Create/delete Follow relationships
- Query followers/following lists
- Check follow status
- Prevent self-follows
- Duplicate follow prevention

### Status

✅ **ACTIVE** - Used by follow views

---

## 6. `activity_service.py` - User Activity Service

**File:** `services/activity_service.py`  
**Purpose:** Event log management

### Primary Class

```python
class UserActivityService:
    record_event(user, event_type, metadata=None, source_model=None, source_id=None)
    get_user_activity(user, event_types=None, limit=50)
    get_recent_activity(user, days=30)
    get_tournament_activity(user, tournament_id)
```

### Used By

- ✅ `services/stats_service.py` - Stats recomputation reads from UserActivity
- ✅ `services/profile_context.py` - Activity feed display
- ✅ Tournament registration/completion handlers
- ✅ Match result handlers
- ✅ Economy transaction handlers

### Event Types

**Tournament:** registered, joined, completed, won, runner_up, top4, placed  
**Match:** played, won, lost  
**Economy:** coins_earned, coins_spent  
**Achievement:** unlocked  
**Team:** created, joined, left

### Architecture

- ✅ **Append-only** - No updates/deletes allowed
- ✅ **Event-sourced** - Source of truth for UserProfileStats
- ✅ **Indexed** - Fast queries by user, event_type, timestamp

### Status

✅ **ACTIVE & CRITICAL** - Core event logging system

---

## 7. `stats_service.py` - Stats Update Service

**File:** `services/stats_service.py`  
**Purpose:** Recompute UserProfileStats from UserActivity

### Primary Class

```python
class StatsUpdateService:
    recompute_stats(user_id) -> UserProfileStats
    recompute_all_stats() -> int  # Batch recomputation
    is_stale(user_profile_stats, max_age_hours=24) -> bool
```

### Used By

- ✅ Admin command: `python manage.py recompute_profile_stats`
- ✅ Periodic celery task (if configured)
- ✅ Manual trigger from admin panel

### Features

- Rebuild UserProfileStats from scratch
- Aggregate tournament/match/economy events
- Update timestamps (first/last tournament/match)
- Staleness detection

### Status

✅ **ACTIVE** - Critical for stats integrity

---

## 8. `audit.py` - Audit Service

**File:** `services/audit.py`  
**Purpose:** Centralized audit logging

### Primary Class

```python
class AuditService:
    record_event(
        subject_user_id,
        event_type,
        source_app,
        object_type,
        object_id,
        actor_user_id=None,
        request_id=None,
        ip_address=None,
        before_snapshot=None,
        after_snapshot=None
    ) -> UserAuditEvent
```

### Used By

- ✅ `services/game_passport_service.py` - All passport operations
- ✅ `services/economy_sync.py` - Economy sync operations
- ✅ `services/public_id.py` - Public ID generation
- ✅ `views/legacy_views.py` - Safe mutation endpoints
- ✅ `admin/` - Admin actions

### Event Types

**Public ID:** assigned, backfilled  
**Economy:** sync, drift_corrected  
**Stats:** recomputed, backfilled  
**Profile:** created, updated  
**Privacy:** settings_changed  
**Game Profiles:** created, updated, deleted  
**Social:** follow_created, follow_deleted  
**Admin:** override, system_reconcile

### Status

✅ **ACTIVE & CRITICAL** - All mutations must be audited

---

## 9. `xp_service.py` - XP Service

**File:** `services/xp_service.py`  
**Purpose:** XP and level management

### Primary Class

```python
class XPService:
    award_xp(user, amount, reason='', context=None) -> dict
    check_level_up(user) -> dict
    xp_for_level(level) -> int  # XP curve
    xp_to_next_level(current_xp, current_level) -> int
    
# Convenience functions
def award_xp(user, amount, reason='', context=None)
def check_level_up(user)
```

### Used By

- ✅ Tournament completion handlers
- ✅ Achievement unlocks
- ✅ Badge awards
- ✅ Economy rewards

### XP Curve

| Level | XP Required | XP to Next |
|-------|-------------|------------|
| 1 | 0 | 100 |
| 2 | 100 | 150 |
| 5 | 625 | 225 |
| 10 | 2475 | 350 |

### Status

✅ **ACTIVE** - Gamification system

---

## 10. `achievement_service.py` - Achievement Service

**File:** `services/achievement_service.py`  
**Purpose:** Badge/achievement management

### Key Functions

```python
def award_achievement(user, name, description, emoji, rarity, context=None)
def check_tournament_achievements(user)
def check_social_achievements(user)
def check_profile_achievements(user)
def check_economic_achievements(user)
def check_special_achievements(user)
def check_all_achievements(user)
def get_achievement_progress(user)
```

### Achievement Categories

**Tournament:** First Victory, Tournament Champion, Perfect Run, etc.  
**Social:** Community Builder, Influencer, etc.  
**Profile:** Profile Master, Verified Player, etc.  
**Economic:** Big Spender, Millionaire, etc.  
**Special:** Early Adopter, Beta Tester, etc.

### Used By

- ✅ Post-tournament completion hooks
- ✅ Post-match completion hooks
- ✅ Profile milestones
- ✅ Economy milestones

### Status

✅ **ACTIVE** - Gamification system

---

## 11. `certificate_service.py` - Certificate Service

**File:** `services/certificate_service.py`  
**Purpose:** Tournament certificate generation

### Key Functions

```python
def generate_verification_code() -> str
def create_certificate_image(user, tournament, placement, prize_amount=None)
def generate_tournament_certificate(user, tournament, placement, prize_amount=None)
def send_certificate_email(user, certificate, tournament, placement)
def auto_generate_certificates_for_tournament(tournament)
```

### Used By

- ✅ Tournament completion webhooks
- ✅ Admin panel manual generation
- ✅ User profile certificate display

### Features

- Generate PDF/image certificates
- Verification codes
- Email delivery
- Certificate storage

### Status

✅ **ACTIVE** - Used by tournament system

---

## 12. `economy_sync.py` - Economy Sync Service

**File:** `services/economy_sync.py`  
**Purpose:** Sync wallet data to UserProfile

### Key Functions

```python
def sync_wallet_to_profile(wallet_id: int) -> dict
def sync_profile_by_user_id(user_id: int) -> Optional[dict]
def get_balance_drift(wallet_id: int) -> dict
def recompute_lifetime_earnings(wallet_id: int) -> int
```

### Used By

- ✅ `apps.economy` - After wallet transactions
- ✅ Admin command: `python manage.py sync_economy`
- ✅ Periodic celery task (if configured)

### Features

- Sync DeltaCrownWallet.cached_balance → UserProfile.deltacoin_balance
- Detect balance drift
- Recompute lifetime earnings
- Audit logging

### Status

✅ **ACTIVE** - Critical for economy integration

---

## 13. `tournament_stats.py` - Tournament Stats Service

**File:** `services/tournament_stats.py`  
**Purpose:** Tournament participation tracking

### Primary Class

```python
class TournamentStatsService:
    record_tournament_participation(user, tournament, placement, prize_amount=None)
    get_tournament_count(user) -> int
    get_wins_count(user) -> int
    get_top3_count(user) -> int
    get_lifetime_earnings(user) -> Decimal
```

### Used By

- ✅ Tournament completion handlers
- ✅ Profile stats display
- ✅ Leaderboards

### Status

✅ **ACTIVE** - Used by tournament system

---

## 14. `public_id.py` - Public ID Generator

**File:** `services/public_id.py`  
**Purpose:** Generate unique public IDs (DC-YY-NNNNNN)

### Primary Class

```python
class PublicIDGenerator:
    generate(user_id: int, created_at: datetime = None) -> str
    validate_format(public_id: str) -> bool
    parse(public_id: str) -> dict
```

### Format

`DC-YY-NNNNNN` (e.g., `DC-25-000042`)
- DC: DeltaCrown prefix
- YY: Year (2-digit)
- NNNNNN: Sequential counter (6 digits, zero-padded)

### Used By

- ✅ UserProfile model save signal (auto-generation)
- ✅ Migration 0014 (backfill existing profiles)
- ✅ Admin display

### Status

✅ **ACTIVE** - Auto-assigned to all profiles

---

## Service Dependency Map

```
Views (fe_v2.py, passport_api.py, settings_api.py)
  ├─ profile_context.py
  │    ├─ privacy_policy.py
  │    ├─ game_passport_service.py
  │    ├─ activity_service.py
  │    └─ stats_service.py
  │
  ├─ game_passport_service.py
  │    ├─ audit.py
  │    └─ validators/
  │
  ├─ privacy_settings_service.py
  │
  ├─ follow_service.py
  │    └─ audit.py
  │
  ├─ economy_sync.py
  │    └─ audit.py
  │
  └─ xp_service.py / achievement_service.py
       └─ audit.py
```

---

## Dead/Unused Services

🔍 **TO INVESTIGATE:** No obviously dead services found. All services in `services/` directory are referenced by views, admin, or management commands.

---

## Critical Findings

### ✅ Well-Architected Services

1. **Separation of Concerns** - Each service has a clear, focused responsibility
2. **Privacy-First** - All data access goes through `ProfileVisibilityPolicy`
3. **Audit Trail** - All mutations logged via `AuditService`
4. **Event Sourcing** - `UserActivity` → `UserProfileStats` (derived projection)

### ⚠️ Service Gaps

1. **No verification service** - Game passport verification removed in GP-0
2. **Missing integrations** - Some services ready but not fully wired to tournament/economy systems

### 🔴 Technical Debt

1. **profile_context.py** uses both JSON `game_profiles` and `GameProfile` model
   - Should fully migrate to GameProfile model
   - Remove JSON fallback logic

2. **Mixed social link sources**:
   - Fields on UserProfile (legacy)
   - SocialLink model (new)
   - Service needs to consolidate

---

**Document Status:** ✅ Phase B2 Complete
