# User Profile - Model Inventory & Relationships

**Generated:** December 28, 2025  
**Purpose:** Complete mapping of all models, relationships, and key fields

---

## Model Location Map

| Model | File | Lines | Status |
|-------|------|-------|--------|
| `UserProfile` | `models_main.py` | 38-684 | ✅ **PRIMARY** |
| `PrivacySettings` | `models_main.py` | 685-836 | ✅ **ACTIVE** |
| `VerificationRecord` | `models_main.py` | 837-1011 | ✅ **ACTIVE** (KYC) |
| `Badge` | `models_main.py` | 1012-1110 | ✅ **ACTIVE** |
| `UserBadge` | `models_main.py` | 1111-1178 | ✅ **ACTIVE** |
| `SocialLink` | `models_main.py` | 1179-1271 | ✅ **ACTIVE** |
| `GameProfile` | `models_main.py` | 1272-1535 | ✅ **ACTIVE** (Game Passport) |
| `GameProfileAlias` | `models_main.py` | 1536-1616 | ✅ **ACTIVE** (Identity history) |
| `GameProfileConfig` | `models_main.py` | 1617-1670 | ✅ **ACTIVE** |
| `Achievement` | `models_main.py` | 1671-1745 | ✅ **ACTIVE** |
| `Match` | `models_main.py` | 1746-1822 | ✅ **ACTIVE** |
| `Certificate` | `models_main.py` | 1823-1913 | ✅ **ACTIVE** |
| `Follow` | `models_main.py` | 1914-1951 | ✅ **ACTIVE** (Social) |
| `UserActivity` | `models/activity.py` | 1-168 | ✅ **ACTIVE** (Event log) |
| `UserProfileStats` | `models/stats.py` | 1-273 | ✅ **ACTIVE** (Derived projection) |
| `UserAuditEvent` | `models/audit.py` | 1-193 | ✅ **ACTIVE** (Audit log) |
| `GamePassportSchema` | `models/game_passport_schema.py` | 1-301 | ✅ **ACTIVE** (Game config) |

---

## Core Model: `UserProfile`

**File:** `models_main.py:38-684`  
**Relationship:** OneToOne with `User` (related_name='profile')

### Key Fields by Category

#### System Identity (Immutable)
- `user` - FK to User (OneToOne)
- `uuid` - UUID field (unique, public identifier)
- `public_id` - CharField (15 chars, unique, DC-YY-NNNNNN format)
- `updated_at` - DateTimeField

#### Legal Identity (Locked after KYC)
- `real_full_name` - CharField(200)
- `date_of_birth` - DateField
- `nationality` - CharField(100)
- `kyc_status` - CharField (choices: unverified, pending, verified, rejected)
- `kyc_verified_at` - DateTimeField

#### Public Identity (User Customizable)
- `display_name` - CharField(80) ✅ **REQUIRED**
- `slug` - SlugField(64, unique) - Auto-generated from display_name
- `avatar` - ImageField (upload_to=user_avatar_path)
- `banner` - ImageField (upload_to=user_banner_path)
- `bio` - TextField

#### Location
- `country` - CharField(100)
- `region` - CharField(2, choices=REGION_CHOICES, default="BD")
- `city` - CharField(100)
- `postal_code` - CharField(20)
- `address` - TextField(300)

#### Demographics
- `gender` - CharField(20, choices=GENDER_CHOICES)
- `pronouns` - CharField(50)

#### Contact
- `phone` - CharField(20)

#### Emergency Contact (LAN Events)
- `emergency_contact_name` - CharField(200)
- `emergency_contact_phone` - CharField(20)
- `emergency_contact_relation` - CharField(50)

#### Competitive Career
- `reputation_score` - IntegerField(default=100)
- `skill_rating` - IntegerField(default=1000)

#### Gamification
- `level` - IntegerField(default=1)
- `xp` - IntegerField(default=0)
- `pinned_badges` - JSONField(default=list, max 5)
- `inventory_items` - JSONField(default=list)

#### Economy
- `deltacoin_balance` - DecimalField(10, 2, default=0) - **READ-ONLY** (managed by wallet)
- `lifetime_earnings` - DecimalField(10, 2, default=0)

#### Social Links (Legacy Fields - being deprecated)
- `youtube_link` - URLField
- `twitch_link` - URLField
- `discord_id` - CharField(64)
- `facebook` - URLField
- `instagram` - URLField
- `tiktok` - URLField
- `twitter` - URLField
- `stream_status` - BooleanField(default=False)

#### Profile Customization
- `preferred_games` - JSONField(default=list)

#### Game Profiles (DEPRECATED - Use GameProfile model)
- `game_profiles` - JSONField(default=list) ⚠️ **DEPRECATED** (GP-CLEAN-02)
  - **Note:** Use `GamePassportService` instead of JSON field
  - Writes BLOCKED per GP-STABILIZE-01

#### Privacy Settings (Legacy - migrated to PrivacySettings model)
- `is_private` - BooleanField(default=False)
- `show_email` - BooleanField(default=False)
- `show_phone` - BooleanField(default=False)
- `show_socials` - BooleanField(default=True)
- `show_address` - BooleanField(default=False)
- `show_age` - BooleanField(default=True)
- `show_gender` - BooleanField(default=False)
- `show_country` - BooleanField(default=True)
- `show_real_name` - BooleanField(default=False)

#### Metadata
- `attributes` - JSONField(default=dict) - Future extensibility
- `system_settings` - JSONField(default=dict) - User preferences

### Computed Properties

| Property | Derived From | Type |
|----------|-------------|------|
| `age` | `date_of_birth` | int |
| `is_kyc_verified` | `kyc_status == 'verified'` | bool |
| `full_name` | `real_full_name` or `user.get_full_name()` | str |
| `xp_to_next_level` | `XPService.xp_to_next_level()` | int |
| `level_progress_percentage` | Calculated from XP curve | float (0-100) |
| `total_earnings` | `DeltaCrownWallet.lifetime_earnings` | Decimal |
| `wallet` | `DeltaCrownWallet` FK | object |

### Key Methods (Active)

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_avatar_url()` | Get avatar URL or None | str or None |
| `get_banner_url()` | Get banner URL or None | str or None |
| `get_active_teams()` | Get active team memberships | list |
| `is_team_member(team)` | Check team membership | bool |
| `is_team_captain(team)` | Check if captain of team | bool |
| `add_xp(amount, reason)` | Award XP | dict |
| `earn_badge(badge_slug)` | Award badge | UserBadge |
| `pin_badge(badge)` | Pin badge to showcase | bool |
| `unpin_badge(badge)` | Unpin badge | bool |

### Deprecated Methods (DO NOT USE)

| Method | Replacement | Status |
|--------|-------------|--------|
| `get_game_profile(game_code)` | `GamePassportService.get_passport()` | ⚠️ **DEPRECATED** |
| `set_game_profile(game_code, data)` | `GamePassportService.create/update_passport()` | ❌ **BLOCKED** |
| `add_game_profile(...)` | `GamePassportService.create_passport()` | ❌ **BLOCKED** |
| `remove_game_profile(game_code)` | `GamePassportService.delete_passport()` | ❌ **BLOCKED** |

---

## Model: `PrivacySettings`

**File:** `models_main.py:685-836`  
**Relationship:** OneToOne with `UserProfile` (related_name='privacy_settings')

### Key Fields

#### Visibility Preset
- `visibility_preset` - CharField (choices: PUBLIC, PROTECTED, PRIVATE)

#### Profile Visibility
- `show_real_name` - BooleanField(default=False)
- `show_phone` - BooleanField(default=False)
- `show_email` - BooleanField(default=False)
- `show_age` - BooleanField(default=True)
- `show_gender` - BooleanField(default=False)
- `show_country` - BooleanField(default=True)
- `show_address` - BooleanField(default=False)

#### Gaming & Activity
- `show_game_ids` - BooleanField(default=True)
- `show_match_history` - BooleanField(default=True)
- `show_teams` - BooleanField(default=True)
- `show_achievements` - BooleanField(default=True)
- `show_activity_feed` - BooleanField(default=True)
- `show_tournaments` - BooleanField(default=True)

#### Economy
- `show_inventory_value` - BooleanField(default=False)
- `show_level_xp` - BooleanField(default=True)

#### Social
- `show_social_links` - BooleanField(default=True)

#### Interaction Permissions
- `allow_team_invites` - BooleanField(default=True)
- `allow_friend_requests` - BooleanField(default=True)
- `allow_direct_messages` - BooleanField(default=True)

### Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `allows_viewing(viewer, field_name)` | Check if viewer can see field | bool |

---

## Model: `GameProfile` (Game Passport)

**File:** `models_main.py:1272-1535`  
**Relationships:**
- FK to `User` (related_name='game_profiles')
- FK to `Game` (related_name='player_profiles')

### Key Fields

#### Identity (Core)
- `user` - FK to User
- `game` - FK to Game (apps.games.models.Game)
- `in_game_name` - CharField(100) ✅ **REQUIRED**
- `discriminator` - CharField(20, nullable) - e.g., #NA1
- `platform` - CharField(50) - e.g., PC, Mobile, Console
- `region` - CharField(50) - e.g., NA, EU, ASIA

#### Identity Composite (Normalized)
- `identity_key` - CharField(200, unique) - Normalized composite key
- `identity_display` - CharField(200) - Human-readable display

#### Showcase Data (Non-identity)
- `rank_name` - CharField(100)
- `rank_tier` - IntegerField(default=0)
- `main_role` - CharField(100)
- `matches_played` - IntegerField(default=0)
- `win_rate` - DecimalField(5, 2, default=0)
- `metadata` - JSONField(default=dict) - Game-specific stats

#### Visibility & Status
- `visibility` - CharField (choices: PUBLIC, FRIENDS_ONLY, PRIVATE)
- `is_pinned` - BooleanField(default=False)
- `pin_order` - IntegerField(default=0)
- `is_lft` - BooleanField(default=False) - Looking for team
- `is_primary` - BooleanField(default=False) - Main game

#### Audit
- `created_at` - DateTimeField
- `updated_at` - DateTimeField

### Constants

- `MAX_PINNED_GAMES = 6`
- `VISIBILITY_CHOICES = [('PUBLIC', 'Public'), ('FRIENDS_ONLY', 'Friends Only'), ('PRIVATE', 'Private')]`

### Computed Properties

| Property | Returns |
|----------|---------|
| `full_identity` | Composite identity string (IGN + discriminator) |

---

## Model: `GameProfileAlias` (Identity History)

**File:** `models_main.py:1536-1616`  
**Relationship:** FK to `GameProfile` (related_name='aliases')

### Key Fields

- `game_profile` - FK to GameProfile
- `old_in_game_name` - CharField(100)
- `old_discriminator` - CharField(20, nullable)
- `old_platform` - CharField(50, nullable)
- `old_region` - CharField(50, nullable)
- `changed_at` - DateTimeField
- `changed_by` - FK to User (nullable)
- `request_ip` - GenericIPAddressField
- `reason` - TextField

**Purpose:** Immutable audit trail of all identity changes

---

## Model: `SocialLink`

**File:** `models_main.py:1179-1271`  
**Relationship:** FK to `User` (related_name='social_links')

### Key Fields

- `user` - FK to User
- `platform` - CharField (choices: twitch, youtube, twitter, discord, etc.)
- `url` - URLField
- `handle` - CharField(100) - Username/handle
- `is_verified` - BooleanField(default=False)
- `is_primary` - BooleanField(default=False)

### Platform Choices

**Streaming:** twitch, youtube, kick, facebook_gaming  
**Social:** twitter, discord, instagram, tiktok, facebook  
**Gaming:** steam, riot, epic, ea, battlenet

---

## Model: `UserActivity` (Event Log)

**File:** `models/activity.py:1-168`  
**Relationship:** FK to `User` (related_name='activities')

### Key Fields

- `user` - FK to User
- `event_type` - CharField (choices: tournament_registered, match_won, etc.)
- `timestamp` - DateTimeField (auto_now_add)
- `metadata` - JSONField (event-specific data)
- `source_model` - CharField(50) - Origin model name
- `source_id` - IntegerField - Origin model PK

### Event Types

**Tournament:** registered, joined, completed, won, runner_up, top4, placed  
**Match:** played, won, lost  
**Economy:** coins_earned, coins_spent  
**Achievement:** unlocked  
**Team:** created, joined, left

### Design Principles

- ✅ **Append-only** - No updates/deletes
- ✅ **Event-sourced** - Stats derived from this ledger
- ✅ **Auditable** - Complete history for GDPR compliance

---

## Model: `UserProfileStats` (Derived Projection)

**File:** `models/stats.py:1-273`  
**Relationship:** OneToOne with `UserProfile` (related_name='stats')

### Key Fields

#### Tournament Stats (Derived from UserActivity)
- `tournaments_played` - IntegerField(default=0)
- `tournaments_won` - IntegerField(default=0)
- `tournaments_top3` - IntegerField(default=0)

#### Match Stats
- `matches_played` - IntegerField(default=0)
- `matches_won` - IntegerField(default=0)

#### Economy Stats
- `total_earnings` - DecimalField(12, 2, default=0)
- `total_spent` - DecimalField(12, 2, default=0)

#### Timestamps
- `first_tournament_at` - DateTimeField(nullable)
- `last_tournament_at` - DateTimeField(nullable)
- `last_match_at` - DateTimeField(nullable)
- `computed_at` - DateTimeField (auto_now)

### Computed Properties

| Property | Formula |
|----------|---------|
| `win_rate` | matches_won / matches_played |
| `net_earnings` | total_earnings - total_spent |

### Key Methods

| Method | Purpose |
|--------|---------|
| `is_stale(max_age_hours=24)` | Check if recompute needed |
| `recompute_from_events(user_id)` | Rebuild stats from UserActivity |

---

## Model: `UserAuditEvent` (Audit Log)

**File:** `models/audit.py:1-193`  
**Relationships:**
- FK to `User` (actor) - related_name='audit_actions_performed'
- FK to `User` (subject) - related_name='audit_events'

### Key Fields

- `actor_user` - FK to User (nullable for system actions)
- `subject_user` - FK to User (whose data was affected)
- `event_type` - CharField (choices: profile_updated, privacy_changed, etc.)
- `source_app` - CharField(50)
- `object_type` - CharField(100) - Model name
- `object_id` - BigIntegerField - Model PK
- `request_id` - CharField(100, nullable)
- `idempotency_key` - CharField(100, nullable)
- `ip_address` - GenericIPAddressField
- `user_agent` - CharField(500)
- `before_snapshot` - JSONField (privacy-safe)
- `after_snapshot` - JSONField (privacy-safe)

### Event Types

**Public ID:** assigned, backfilled  
**Economy:** sync, drift_corrected  
**Stats:** recomputed, backfilled  
**Profile:** created, updated  
**Privacy:** settings_changed  
**Game Profiles:** created, updated, deleted  
**Social:** follow_created, follow_deleted  
**Admin:** override, system_reconcile

---

## Relationship Diagram

```
User (Django Auth)
  ├─ OneToOne → UserProfile
  │              ├─ OneToOne → PrivacySettings
  │              ├─ OneToOne → VerificationRecord (KYC)
  │              ├─ OneToOne → UserProfileStats (Derived)
  │              └─ FK ← GameProfile (1:N)
  │                       └─ FK ← GameProfileAlias (1:N, History)
  ├─ FK ← UserActivity (1:N, Event Log)
  ├─ FK ← UserAuditEvent (1:N, Audit)
  ├─ FK ← SocialLink (1:N)
  ├─ FK ← UserBadge (1:N)
  │         └─ FK → Badge (N:1)
  ├─ FK ← Achievement (1:N)
  ├─ FK ← Match (1:N)
  ├─ FK ← Certificate (1:N)
  └─ M2M → Follow (Self-referential, Followers/Following)

Game (apps.games.models.Game)
  ├─ OneToOne → GamePassportSchema (Config)
  └─ FK ← GameProfile (1:N)
```

---

## Foreign Key Map

| Model | FK Field | Points To | Related Name | On Delete |
|-------|----------|-----------|--------------|-----------|
| `UserProfile` | `user` | `User` | `profile` | CASCADE |
| `PrivacySettings` | `user_profile` | `UserProfile` | `privacy_settings` | CASCADE |
| `VerificationRecord` | `user_profile` | `UserProfile` | `verification_record` | CASCADE |
| `UserProfileStats` | `user_profile` | `UserProfile` | `stats` | CASCADE |
| `UserActivity` | `user` | `User` | `activities` | PROTECT |
| `UserAuditEvent` | `actor_user` | `User` | `audit_actions_performed` | SET_NULL |
| `UserAuditEvent` | `subject_user` | `User` | `audit_events` | CASCADE |
| `GameProfile` | `user` | `User` | `game_profiles` | CASCADE |
| `GameProfile` | `game` | `Game` | `player_profiles` | CASCADE |
| `GameProfileAlias` | `game_profile` | `GameProfile` | `aliases` | CASCADE |
| `SocialLink` | `user` | `User` | `social_links` | CASCADE |
| `UserBadge` | `user` | `User` | `user_badges` | CASCADE |
| `UserBadge` | `badge` | `Badge` | `earned_by` | CASCADE |

---

## Indexes & Performance

### UserProfile
- `Index(fields=["region"])`
- `Index(fields=["public_id"], name='idx_profile_public_id')`

### UserActivity
- `Index(fields=['user', '-timestamp'])`
- `Index(fields=['event_type', '-timestamp'])`
- `Index(fields=['user', 'event_type'])`
- `Index(fields=['source_model', 'source_id'])`

### GameProfile
- `Index(fields=['user', '-created_at'])`
- `Index(fields=['game', '-created_at'])`
- `Unique(fields=['identity_key'])` - **Critical for uniqueness**

---

## Critical Findings

### ✅ Well-Designed Architecture

1. **Event-Sourced Stats** - `UserActivity` → `UserProfileStats` is append-only ledger
2. **Audit Trail** - `UserAuditEvent` captures all profile mutations
3. **Identity History** - `GameProfileAlias` tracks IGN changes
4. **Privacy Layer** - Separate `PrivacySettings` model for granular control

### ⚠️ Migration Required

1. **Deprecated JSON fields** on `UserProfile`:
   - `game_profiles` (JSONField) → Should migrate all data to `GameProfile` model
   - Social link fields → Should migrate to `SocialLink` model

2. **Duplicate privacy fields**:
   - Privacy flags on `UserProfile` AND `PrivacySettings`
   - Need to consolidate and deprecate one

### 🔴 Schema Debt

1. **UserProfile is 1951 lines** - Contains many concerns:
   - Core identity
   - Privacy settings (should be in PrivacySettings)
   - Social links (should be in SocialLink)
   - Game profiles (deprecated JSON field)
   - Gamification (XP, badges, inventory)

2. **Mixed concerns** - Legal identity + public identity + privacy all in one model

---

## Next Steps (Phase B2)

- Document all services and their usage
- Map which models are accessed by which services
- Identify unused/dead model fields

---

**Document Status:** ✅ Phase B1 Complete
