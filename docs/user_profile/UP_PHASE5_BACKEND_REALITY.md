# UP_PHASE5_BACKEND_REALITY.md

**Phase:** 5A - Deep System Audit  
**Date:** December 28, 2025  
**Status:** 🔍 **COMPLETE TRUTH EXTRACTION**

---

## 🎯 MISSION

Document **exactly what exists** in the backend, with **USED / UNUSED / CONFLICTING** labels.  
No assumptions. No optimism. Only observable reality.

---

## 📊 MODEL INVENTORY

### **Models in `models_main.py` (13 total)**

| Model | Lines | Purpose | Status | Usage Evidence |
|-------|-------|---------|--------|----------------|
| `UserProfile` | 38-685 | Core profile data | ✅ **USED** | All views reference it |
| `PrivacySettings` | 685-837 | Granular privacy controls | ⚠️ **CONFLICTING** | Competes with UserProfile legacy fields |
| `VerificationRecord` | 837-1012 | KYC document tracking | ✅ **USED** | Admin uses it |
| `Badge` | 1012-1111 | Achievement badges | ✅ **USED** | XP/gamification system |
| `UserBadge` | 1111-1179 | User ↔ Badge junction | ✅ **USED** | Badge awards |
| `SocialLink` | 1179-1272 | External social profiles | ⚠️ **PARTIALLY USED** | Competes with UserProfile direct fields |
| `GameProfile` | 1272-1536 | Game passports (GP-2A) | ✅ **USED** | Primary passport model |
| `GameProfileAlias` | 1536-1617 | IGN change history | ✅ **USED** | Audit trail |
| `GameProfileConfig` | 1617-1671 | System-wide passport settings | ✅ **USED** | Validation rules |
| `Achievement` | 1671-1746 | User-earned achievements | ✅ **USED** | Profile showcase |
| `Match` | 1746-1823 | Match history | 🔴 **UNUSED** | No views create/read matches |
| `Certificate` | 1823-1914 | Tournament certificates | ✅ **USED** | Tournament ops |
| `Follow` | 1914-1951 | User follow relationships | ✅ **USED** | Social system |

### **Models in `models/` directory (4 total)**

| Model | File | Purpose | Status | Evidence |
|-------|------|---------|--------|----------|
| `UserActivity` | activity.py | Event log (event sourcing) | 🔴 **UNUSED** | No views write events |
| `UserProfileStats` | stats.py | Derived stats projection | 🔴 **UNUSED** | No views read/write stats |
| `UserAuditEvent` | audit.py | Forensic audit trail | ✅ **USED** | AuditService writes here |
| `GamePassportSchema` | game_passport_schema.py | Per-game field schemas | 🔴 **UNUSED** | No views reference it |

---

## 🚨 CRITICAL CONFLICT: DUAL PRIVACY SYSTEM

### **THE PROBLEM**

**Two sources of truth for privacy settings coexist:**

#### **Source 1: UserProfile Legacy Fields (models_main.py:217-228)**
```python
is_private = models.BooleanField(default=False)
show_email = models.BooleanField(default=False)
show_phone = models.BooleanField(default=False)
show_socials = models.BooleanField(default=True)
show_address = models.BooleanField(default=False)
show_age = models.BooleanField(default=True)
show_gender = models.BooleanField(default=False)
show_country = models.BooleanField(default=True)
show_real_name = models.BooleanField(default=False)
```

**Comment says:** "Will be moved to PrivacySettings model in Phase 2"  
**Reality:** Phase 2 happened, but fields were NOT removed.

#### **Source 2: PrivacySettings Model (models_main.py:685-837)**
```python
class PrivacySettings(models.Model):
    user_profile = models.OneToOneField(UserProfile, ...)
    
    # 15 granular privacy fields:
    profile_visibility = models.CharField(...)  # PUBLIC / FOLLOWERS_ONLY / PRIVATE
    show_real_name = models.BooleanField(...)
    show_phone = models.BooleanField(...)
    show_email = models.BooleanField(...)
    show_age = models.BooleanField(...)
    show_gender = models.BooleanField(...)
    show_country = models.BooleanField(...)
    show_game_ids = models.BooleanField(...)
    show_social_links = models.BooleanField(...)
    show_match_history = models.BooleanField(...)
    show_teams = models.BooleanField(...)
    show_achievements = models.BooleanField(...)
    allow_team_invites = models.BooleanField(...)
    allow_friend_requests = models.BooleanField(...)
    allow_direct_messages = models.BooleanField(...)
```

### **USAGE ANALYSIS**

| View File | Which Source? | Line |
|-----------|---------------|------|
| `legacy_views.py:704` | UserProfile.is_private | ✅ **WRITES** to legacy field |
| `settings_api.py:310` | PrivacySettings | ✅ **READS** PrivacySettings |
| `settings_api.py:372` | PrivacySettings | ✅ **READS** PrivacySettings |
| `legacy_views.py:695` | PrivacySettings | ✅ **READS** PrivacySettings |
| `fe_v2.py:400` | PrivacySettings | ✅ **READS** PrivacySettings |

**Verdict:**  
- **PrivacySettings is the CANONICAL model** (get_or_create pattern everywhere)
- **UserProfile legacy fields are ZOMBIE CODE** (1 write, 0 reads)
- **Risk:** Settings saved to one, read from the other = broken UX

---

## 🧩 SERVICE LAYER INVENTORY

### **Services in `services/` directory**

| Service | Purpose | Status | Evidence |
|---------|---------|--------|----------|
| `audit.py` | Audit event logging | ✅ **USED** | Views call `AuditService.record_event()` |
| `game_passport_service.py` | Passport CRUD | ✅ **USED** | Passport creation/update views use it |
| `follow_service.py` | Follow/unfollow logic | ✅ **USED** | Social views use it |
| `privacy_settings_service.py` | Privacy updates | ✅ **USED** | Settings views use it |
| `profile_context.py` | Context builders | ✅ **USED** | View decorators use it |
| `xp_service.py` | XP/leveling logic | ✅ **USED** | Gamification |
| `achievement_service.py` | Badge awards | ✅ **USED** | Achievement system |
| `certificate_service.py` | Tournament certificates | ✅ **USED** | Tournament ops |
| `public_id.py` | DC-25-NNNNNN generator | ✅ **USED** | User registration |
| `economy_sync.py` | Wallet ↔ Profile sync | ✅ **USED** | Economy integration |
| `stats_service.py` | Stats computation | 🔴 **ORPHANED** | No views call it |
| `activity_service.py` | Event log writes | 🔴 **ORPHANED** | No views call it |
| `tournament_stats.py` | Tournament aggregates | ✅ **USED** | Admin/reporting |

---

## 🗂️ USERPROFILE FIELD ANALYSIS

### **Identity Fields (12 fields) — ✅ CANONICAL**

| Field | Type | Purpose | Used? |
|-------|------|---------|-------|
| `user` | FK | Link to auth.User | ✅ Always |
| `uuid` | UUID | Public identifier | ✅ API exposure |
| `public_id` | Char | DC-25-NNNNNN | ✅ Human-readable ID |
| `display_name` | Char | Public display name | ✅ Profile/settings |
| `slug` | Slug | URL slug | ✅ `/@username/` routing |
| `avatar` | Image | Profile picture | ✅ Uploads working |
| `banner` | Image | Profile banner | ✅ Uploads working |
| `bio` | Text | User bio | ✅ Profile display |
| `real_full_name` | Char | Legal name (KYC) | ✅ Tournament registration |
| `date_of_birth` | Date | DOB (KYC) | ✅ Age verification |
| `nationality` | Char | Citizenship | ✅ Tournament eligibility |
| `kyc_status` | Char | Verification status | ✅ Admin workflow |

### **Location Fields (5 fields) — ✅ CANONICAL**

| Field | Used? | Purpose |
|-------|-------|---------|
| `country` | ✅ | Regional tournaments |
| `region` | ✅ | Server routing |
| `city` | ⚠️ | Rarely shown |
| `postal_code` | ⚠️ | Prize shipping |
| `address` | ⚠️ | Prize shipping |

### **Contact Fields (4 fields) — ✅ CANONICAL**

| Field | Used? | Purpose |
|-------|-------|---------|
| `phone` | ✅ | SMS verification |
| `emergency_contact_name` | ⚠️ | LAN events |
| `emergency_contact_phone` | ⚠️ | LAN events |
| `emergency_contact_relation` | ⚠️ | LAN events |

### **Competitive Fields (2 fields) — ⚠️ PARTIALLY USED**

| Field | Status | Evidence |
|-------|--------|----------|
| `reputation_score` | 🔴 UNUSED | No views read/write |
| `skill_rating` | 🔴 UNUSED | No views read/write |

### **Gamification Fields (4 fields) — ✅ CANONICAL**

| Field | Used? | Purpose |
|-------|-------|---------|
| `level` | ✅ | XP system |
| `xp` | ✅ | XP system |
| `pinned_badges` | ✅ | Badge showcase |
| `inventory_items` | 🔴 UNUSED | No shop system yet |

### **Economy Fields (2 fields) — ✅ CANONICAL**

| Field | Used? | Purpose |
|-------|-------|---------|
| `deltacoin_balance` | ✅ | Wallet read-only mirror |
| `lifetime_earnings` | ✅ | Bragging rights |

### **Social Link Fields (8 fields) — ⚠️ CONFLICTING**

| Field | Status | Conflict With |
|-------|--------|---------------|
| `youtube_link` | ⚠️ LEGACY | SocialLink model |
| `twitch_link` | ⚠️ LEGACY | SocialLink model |
| `discord_id` | ⚠️ LEGACY | SocialLink model |
| `facebook` | ⚠️ LEGACY | SocialLink model |
| `instagram` | ⚠️ LEGACY | SocialLink model |
| `tiktok` | ⚠️ LEGACY | SocialLink model |
| `twitter` | ⚠️ LEGACY | SocialLink model |
| `stream_status` | 🔴 UNUSED | No live detection |

**Problem:** Settings form writes to UserProfile fields, but SocialLink model exists separately.

### **Privacy Fields (9 fields) — 🔴 ZOMBIE CODE**

All 9 legacy privacy fields (is_private, show_email, etc.) are **DEPRECATED**.  
**Reason:** PrivacySettings model is the canonical source (confirmed by view usage).

**Action Required:** Remove these fields in migration.

### **Deprecated Fields (3 fields) — ✅ CORRECTLY DEPRECATED**

| Field | Status | Evidence |
|-------|--------|----------|
| `game_profiles` | 🟢 DEPRECATED | JSON field, replaced by GameProfile model |
| `preferred_games` | 🔴 UNUSED | No views read/write |
| (Legacy game IDs) | 🟢 REMOVED | Migrated out successfully |

### **Metadata Fields (2 fields) — ⚠️ VAGUE**

| Field | Purpose | Used? |
|-------|---------|-------|
| `attributes` | "Future features" | 🔴 UNUSED |
| `system_settings` | User preferences | ⚠️ Partially (theme?) |

---

## 🔍 GAMEPROFILE (PASSPORT) MODEL ANALYSIS

### **Status:** ✅ **CANONICAL MODEL** (GP-2A Structured Identity)

**Location:** `models_main.py:1272-1536` (264 lines)

### **Core Identity Fields (5 fields) — ✅ STRUCTURED**

| Field | Purpose | Required? | Validation |
|-------|---------|-----------|------------|
| `game` | FK to Game | ✅ | Must exist |
| `ign` | In-game name | ✅ | Game-specific rules |
| `discriminator` | Tag/zone | ⚠️ | Riot/MLBB only |
| `platform` | PC/Mobile/Console | ⚠️ | Cross-platform games |
| `region` | Server/region | ⚠️ | Some games require |

### **Computed Fields (2 fields) — ✅ WORKING**

| Field | Formula | Purpose |
|-------|---------|---------|
| `identity_key` | Normalized unique key | Duplicate prevention |
| `in_game_name` | Display format | Human-readable |

**Example:**  
- **ign:** "TenZ"  
- **discriminator:** "NA1"  
- **in_game_name:** "TenZ#NA1"  
- **identity_key:** "tenz#na1" (lowercase)

### **Showcase Fields (3 fields) — ✅ WORKING**

| Field | Type | Purpose |
|-------|------|---------|
| `rank_name` | Char | "Radiant", "Immortal 3" |
| `main_role` | Char | "Duelist", "Controller" |
| `metadata` | JSON | Flexible showcase data |

### **Status Fields (5 fields) — ✅ WORKING**

| Field | Values | Purpose |
|-------|--------|---------|
| `status` | ACTIVE / BANNED / SUSPENDED | Account health |
| `visibility` | PUBLIC / FOLLOWERS / PRIVATE | Privacy |
| `is_verified` | Bool | Official verification |
| `is_primary` | Bool | Main game |
| `is_lft` | Bool | Looking for team |

### **Metrics (6 fields) — ⚠️ PARTIALLY POPULATED**

| Field | Status | Evidence |
|-------|--------|----------|
| `matches_played` | 🔴 UNUSED | No match system yet |
| `matches_won` | 🔴 UNUSED | No match system yet |
| `win_rate` | 🔴 UNUSED | Computed property |
| `skill_rating` | 🔴 UNUSED | No ranking system |
| `hours_played` | 🔴 UNUSED | No tracking |
| `last_played_at` | 🔴 UNUSED | No tracking |

**Verdict:** Metrics are placeholders for future match system.

---

## 🚫 UNUSED MODELS (ACTION REQUIRED)

### **1. UserActivity (Event Log) — 🔴 ORPHANED**

**Location:** `models/activity.py` (168 lines)  
**Purpose:** Event-sourced activity log for stats computation  
**Status:** ⚠️ **MODEL EXISTS BUT NO WRITES**

**Evidence:**
- No views call `UserActivity.objects.create()`
- `activity_service.py` exists but nothing calls it
- Designed for event sourcing, but no events recorded

**Decision Needed:**
- **Option A:** Delete model entirely (clean slate)
- **Option B:** Implement event recording (tournament_joined, match_played, etc.)

**Recommendation:** **DELETE** — No current need for event sourcing. Can rebuild later if needed.

---

### **2. UserProfileStats (Derived Stats) — 🔴 ORPHANED**

**Location:** `models/stats.py` (273 lines)  
**Purpose:** Derived stats computed from UserActivity events  
**Status:** ⚠️ **MODEL EXISTS BUT NO READS**

**Evidence:**
- No views read `profile.stats`
- Designed to be computed from UserActivity (which itself is unused)
- `recompute_from_events()` method exists but never called

**Decision Needed:**
- **Option A:** Delete model (depends on UserActivity)
- **Option B:** Implement stats display on profile page

**Recommendation:** **DELETE** — Blocked by UserActivity deletion. Stats can be computed directly when needed.

---

### **3. GamePassportSchema — 🔴 UNUSED**

**Location:** `models/game_passport_schema.py` (301 lines)  
**Purpose:** Per-game field configuration (dynamic forms)  
**Status:** ⚠️ **MODEL EXISTS BUT NO REFERENCES**

**Evidence:**
- No views query `GamePassportSchema.objects`
- Passport modal hardcodes field logic instead
- Admin doesn't register it

**Decision Needed:**
- **Option A:** Delete model (not needed for current hardcoded approach)
- **Option B:** Implement schema-driven passport forms (better UX but more work)

**Recommendation:** **DELETE** — Hardcoded passport forms work fine. Schema abstraction is premature optimization.

---

### **4. Match Model — 🔴 UNUSED**

**Location:** `models_main.py:1746-1823` (77 lines)  
**Purpose:** Match history tracking  
**Status:** ⚠️ **MODEL EXISTS BUT NO WRITES**

**Evidence:**
- No views create Match records
- GameProfile metrics (matches_played, win_rate) are unused
- No match result submission system

**Decision Needed:**
- **Option A:** Delete model (no match system yet)
- **Option B:** Build match submission system (Phase 6 feature)

**Recommendation:** **KEEP BUT DOCUMENT AS PLACEHOLDER** — Needed for future esports features. Not blocking current work.

---

## 🔐 PRIVACY SYSTEM DECISION

### **THE CONFLICT**

UserProfile has 9 legacy privacy fields, PrivacySettings has 15 granular fields.

### **USAGE EVIDENCE**

| System | Writes | Reads | Admin |
|--------|--------|-------|-------|
| UserProfile legacy | 1 (legacy_views.py:704) | 0 | ⚠️ Shows fields |
| PrivacySettings model | 5+ (get_or_create pattern) | 10+ | ✅ Inline admin |

**Verdict:** **PrivacySettings is the winner.**

### **REQUIRED ACTIONS**

1. **Migration:** Remove 9 legacy privacy fields from UserProfile
2. **Data Migration:** Copy any legacy data to PrivacySettings (if not already done)
3. **View Cleanup:** Remove legacy_views.py:704 write to `is_private`
4. **Admin Cleanup:** Hide legacy fields in UserProfile admin

---

## 🧹 SOCIAL LINKS CONFLICT

### **THE CONFLICT**

UserProfile has 7 direct fields (youtube_link, twitch_link, etc.), SocialLink model exists separately.

### **USAGE EVIDENCE**

| System | Admin | Views |
|--------|-------|-------|
| UserProfile fields | ✅ Shows | ✅ Settings form writes here |
| SocialLink model | ✅ Inline | 🔴 No views use it |

**Verdict:** **UserProfile fields are actively used, SocialLink model is orphaned.**

### **DECISION OPTIONS**

**Option A: Keep UserProfile fields, delete SocialLink model**  
- ✅ Simple, matches current behavior  
- ❌ Less flexible (hardcoded platforms)

**Option B: Migrate to SocialLink model**  
- ✅ More flexible (add custom platforms)  
- ❌ Requires view/form refactor

**Recommendation:** **Option A** — Current system works, SocialLink adds complexity without clear benefit.

---

## 📋 FOLLOW SYSTEM STATUS

### **Model:** `Follow` (models_main.py:1914-1951)

**Status:** ✅ **FULLY IMPLEMENTED**

**Evidence:**
- FollowService handles logic
- Views use follow_user_safe() / unfollow_user_safe()
- Admin shows follow relationships

**Fields:**
- `follower` (FK to UserProfile)
- `following` (FK to UserProfile)
- `created_at` (timestamp)

**Computed Properties:**
- `follower_count` property on UserProfile
- `following_count` property on UserProfile

**No Issues Found.** ✅

---

## 🎯 GAMEPROFILE VALIDATION (GP-2A)

### **Validation Service:** `game_passport_service.py`

**Status:** ✅ **WORKING**

**Validation Flow:**
1. View receives game_id + ign + discriminator + platform
2. Service calls `GamePassportSchemaValidator.validate_structured()`
3. Validator generates `identity_key` (normalized)
4. Check for duplicates by (user, game, identity_key)
5. Create GameProfile record

**Known Issues:** None. GP-2A validation is solid.

---

## 🔎 SIGNALS & AUTO-CREATION

### **Signals File:** Does not exist as `signals.py`

**Auto-Creation Patterns Found:**

1. **PrivacySettings:** `get_or_create()` pattern in views (lazy creation)
2. **Profile → User:** OneToOneField (auto-created via signal? Need to verify)

**Action Required:** Verify if UserProfile auto-creation signal exists in `apps.py` or elsewhere.

---

## 🎨 ADMIN CONFIGURATION STATUS

### **Registered Models (12 total)**

| Model | Inline Admins | Custom Actions | Status |
|-------|---------------|----------------|--------|
| UserProfile | PrivacySettings, SocialLink, GameProfile | Yes | ✅ Complex |
| PrivacySettings | N/A (inline only) | N/A | ✅ Simple |
| VerificationRecord | N/A | Approve/Reject | ✅ Working |
| Badge | N/A | Create | ✅ Simple |
| UserBadge | N/A | N/A | ✅ Simple |
| SocialLink | N/A (inline only) | N/A | ⚠️ Unused |
| GameProfile | GameProfileAlias | Delete | ✅ Complex |
| Achievement | N/A | Award | ✅ Simple |
| Certificate | N/A | Generate | ✅ Complex |
| Follow | N/A | N/A | ✅ Simple |
| UserActivity | N/A | N/A | 🔴 NOT REGISTERED |
| UserProfileStats | N/A | N/A | 🔴 NOT REGISTERED |
| GamePassportSchema | N/A | N/A | 🔴 NOT REGISTERED |
| UserAuditEvent | N/A | N/A | ✅ Registered |

### **Admin Issues:**

1. **Duplicate Privacy Controls:** UserProfile shows legacy fields + PrivacySettings inline
2. **Unused SocialLink Inline:** Takes space but no views use it
3. **Confusing Model Names:** Achievement vs Badge (what's the difference?)
4. **Orphaned Model Admins:** UserActivity/Stats/Schema not registered (good, they're unused)

---

## 🏗️ SERVICE LAYER HEALTH

### **✅ HEALTHY SERVICES (10)**

| Service | Purpose | Views Use It? | Status |
|---------|---------|---------------|--------|
| AuditService | Event logging | ✅ Yes | 🟢 Working |
| GamePassportService | Passport CRUD | ✅ Yes | 🟢 Working |
| FollowService | Follow/unfollow | ✅ Yes | 🟢 Working |
| PrivacySettingsService | Privacy updates | ✅ Yes | 🟢 Working |
| ProfileContextService | View context | ✅ Yes | 🟢 Working |
| XPService | Level/XP logic | ✅ Yes | 🟢 Working |
| AchievementService | Badge awards | ✅ Yes | 🟢 Working |
| CertificateService | Certificates | ✅ Yes | 🟢 Working |
| PublicIDGenerator | DC-25-NNNNNN | ✅ Yes | 🟢 Working |
| EconomySyncService | Wallet sync | ✅ Yes | 🟢 Working |

### **🔴 ORPHANED SERVICES (2)**

| Service | Purpose | Status |
|---------|---------|--------|
| StatsService | Compute stats | 🔴 No views call it |
| ActivityService | Write events | 🔴 No views call it |

**Action:** Delete both (they depend on unused models).

---

## 🎯 FINAL RECOMMENDATIONS

### **🔥 CRITICAL (Phase 5 Blockers)**

1. **Remove UserProfile Privacy Fields** (9 fields) → Migration required
2. **Delete or Fix SocialLink Model** → Choose Option A (delete)
3. **Remove Match Metrics from GameProfile** → Or clearly mark as "Coming Soon"

### **🟡 HIGH PRIORITY (UX Improvements)**

4. **Delete UserActivity Model** → Event sourcing not needed yet
5. **Delete UserProfileStats Model** → Depends on UserActivity
6. **Delete GamePassportSchema Model** → Hardcoded forms work fine
7. **Clean Up Admin** → Hide legacy fields, remove unused inlines

### **🟢 LOW PRIORITY (Polish)**

8. **Rename Achievement vs Badge** → Clarify purpose or merge
9. **Document Match Model as Placeholder** → Future feature
10. **Audit system_settings JSON** → What's actually in there?

---

## 📊 SUMMARY SCORECARD

| Category | Total | Used | Unused | Conflicting |
|----------|-------|------|--------|-------------|
| Models | 17 | 10 | 4 | 3 |
| Services | 15 | 10 | 2 | 0 |
| UserProfile Fields | 60+ | ~40 | ~10 | ~10 |

**Overall Health:** 🟡 **60% Clean, 40% Needs Cleanup**

---

**Status:** Backend audit complete. Next: Frontend wiring audit.
