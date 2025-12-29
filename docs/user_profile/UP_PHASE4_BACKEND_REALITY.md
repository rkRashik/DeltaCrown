# UP_PHASE4_BACKEND_REALITY.md

**Phase:** 4 - Ground Truth Alignment  
**Date:** December 28, 2025  
**Status:** 🔴 **IN PROGRESS - BRUTAL HONESTY MODE**

---

## ⚠️ DISCLAIMER

This document represents **actual backend reality**, not aspirational documentation.  
**Only facts. No optimism. No assumptions.**

---

## 📂 File Structure (ACTUAL)

### Models Location
```
apps/user_profile/
├── models_main.py          ← Main models (1,951 lines)
├── models/
│   ├── __init__.py
│   ├── activity.py         ← UserActivity model
│   ├── audit.py            ← UserAuditEvent model
│   ├── stats.py            ← UserProfileStats model
│   └── game_passport_schema.py ← GamePassportSchema model
```

**Reality Check:** ✅ Models exist but split across files (not what docs claimed)

### Views Location
```
apps/user_profile/
├── views/
│   ├── __init__.py
│   ├── fe_v2.py            ← Frontend V2 views
│   ├── legacy_views.py     ← Old endpoints
│   ├── passport_api.py     ← Game passport APIs
│   ├── passport_create.py  ← Passport creation
│   ├── public.py           ← Public profiles
│   ├── redirects.py        ← URL redirects
│   └── settings_api.py     ← Settings mutations
├── views_public.py         ← Additional public views
├── views_settings.py       ← Additional settings views
├── api_views.py            ← Game ID API (legacy)
├── api/
│   └── game_id_api.py      ← Modern game ID API
```

**Reality Check:** ✅ Views heavily fragmented (migration in progress)

---

## 🗂️ MODELS INVENTORY (17 Total)

### Main File: `models_main.py`

#### 1. **UserProfile** (Line 38)
**Status:** ✅ **ACTIVE - PRIMARY MODEL**

**Key Fields (Actually Used):**
```python
# System Identity
user                    # FK to auth.User
uuid                    # UUID for public API
public_id              # "DC-25-000042" format
created_at / updated_at

# Display Fields
display_name           # Public name
bio                    # Profile description
avatar                 # ImageField
banner                 # ImageField

# Legal/KYC
legal_first_name
legal_last_name
date_of_birth
gender
country
kyc_status            # Enum: unverified/pending/verified/rejected

# Contact
email_contact
phone_contact
emergency_contact_name
emergency_contact_phone

# Metadata
level                 # Gamification level
experience_points     # XP for leveling
wallet_balance       # Decimal field

# Suspension
suspension_status    # Enum: active/inactive
suspension_reason
suspension_until

# Privacy (Legacy - moved to PrivacySettings)
profile_visibility   # LEGACY FIELD - CHECK IF USED
```

**Reality Check:**
- ⚠️ `profile_visibility` field exists but **PrivacySettings model** also exists
- ❓ **UNKNOWN:** Which one is authoritative?
- ❓ **UNKNOWN:** Are both fields synced?

#### 2. **PrivacySettings** (Line 685)
**Status:** ✅ **ACTIVE**

**Fields:**
```python
user_profile           # OneToOne to UserProfile

# Visibility
show_real_name
show_phone
show_email
show_age
show_gender
show_country
show_game_ids
show_social_links
show_match_history
show_teams
show_achievements

# Interaction
allow_team_invites
allow_friend_requests
allow_direct_messages
```

**Reality Check:**
- ✅ Model exists and is wired
- ⚠️ **CONFLICT:** `UserProfile.profile_visibility` vs `PrivacySettings.show_*` fields
- ❓ **UNKNOWN:** Which takes precedence?

#### 3. **VerificationRecord** (Line 837)
**Status:** ✅ **ACTIVE**

**Purpose:** KYC verification workflow

**Fields:**
```python
user_profile
verification_type      # kyc/identity/address
status                # pending/approved/rejected
document_front
document_back
submitted_at
reviewed_at
reviewed_by           # FK to User (admin)
rejection_reason
```

**Reality Check:** ✅ Fully wired in admin panel

#### 4. **Badge** (Line 1012)
**Status:** ✅ **ACTIVE**

**Purpose:** Achievement badges catalog

**Reality Check:** ✅ Used by achievement system

#### 5. **UserBadge** (Line 1111)
**Status:** ✅ **ACTIVE**

**Purpose:** User-earned badges

**Reality Check:** ✅ Working

#### 6. **SocialLink** (Line 1179)
**Status:** ✅ **ACTIVE**

**Fields:**
```python
user               # FK to User
platform          # Enum: twitch/twitter/youtube/discord
url
handle
is_verified
```

**Reality Check:**
- ✅ Model exists
- ⚠️ **ISSUE:** Frontend expects 4 platforms, need to verify CRUD works

#### 7. **GameProfile** (Line 1272)
**Status:** ✅ **ACTIVE - CRITICAL MODEL**

**Fields:**
```python
user               # FK to User
game              # CharField (slug: "valorant", "lol", etc.)

# Identity
in_game_name      # IGN
discriminator     # Riot tag (optional)
platform          # PC/Console/etc.
region            # NA/EU/etc.

# Stats
rank_name
rank_division
rank_points
main_role
matches_played
wins
losses
win_rate

# Metadata
is_verified
is_looking_for_team
is_pinned
pin_order
visibility        # public/private/followers

# Timestamps
created_at
updated_at
last_ign_change_at
```

**Reality Check:**
- ✅ Model exists
- ⚠️ **ISSUE:** Frontend expects `/api/games/` endpoint to load games list
- ❓ **UNKNOWN:** Does that endpoint exist?

#### 8. **GameProfileAlias** (Line 1536)
**Status:** ✅ **ACTIVE**

**Purpose:** Track IGN changes over time

**Reality Check:** ✅ Audit logging works

#### 9. **GameProfileConfig** (Line 1617)
**Status:** ✅ **ACTIVE**

**Purpose:** Per-passport configuration (IGN change cooldowns, etc.)

**Reality Check:** ✅ Working

#### 10. **Achievement** (Line 1671)
**Status:** ⚠️ **PARTIALLY USED**

**Purpose:** User achievements (separate from badges?)

**Reality Check:**
- ✅ Model exists
- ❓ **UNKNOWN:** Distinction between Badge and Achievement unclear

#### 11. **Match** (Line 1746)
**Status:** ⚠️ **PARTIALLY USED**

**Purpose:** Match history

**Reality Check:**
- ✅ Model exists
- ❌ **NOT WIRED:** No API to create/list matches yet
- ❓ **UNKNOWN:** Is this manually populated?

#### 12. **Certificate** (Line 1823)
**Status:** ⚠️ **PARTIALLY USED**

**Purpose:** Tournament participation certificates

**Reality Check:**
- ✅ Model exists
- ❓ **UNKNOWN:** How are these issued?

#### 13. **Follow** (Line 1914)
**Status:** ✅ **ACTIVE**

**Purpose:** Follow/follower relationships

**Reality Check:**
- ✅ Model exists
- ⚠️ **ISSUE:** Frontend calls `/actions/follow/<username>/` but needs verification

---

### Additional Models (models/ directory)

#### 14. **UserAuditEvent** (`models/audit.py`)
**Status:** ✅ **ACTIVE**

**Purpose:** Audit logging

**Reality Check:** ✅ Working, immutable

#### 15. **UserProfileStats** (`models/stats.py`)
**Status:** ⚠️ **UNKNOWN**

**Purpose:** Aggregated stats?

**Reality Check:**
- ✅ Model exists
- ❓ **UNKNOWN:** Is this auto-computed or manual?
- ❓ **UNKNOWN:** What populates this?

#### 16. **UserActivity** (`models/activity.py`)
**Status:** ⚠️ **UNKNOWN**

**Purpose:** Activity feed?

**Reality Check:**
- ✅ Model exists
- ❓ **UNKNOWN:** Is this being populated?
- ❌ **NOT VISIBLE:** No frontend component shows this

#### 17. **GamePassportSchema** (`models/game_passport_schema.py`)
**Status:** ❓ **UNKNOWN**

**Purpose:** Dynamic schema for game passports?

**Reality Check:**
- ✅ Model exists
- ❌ **NOT USED:** Frontend hardcodes field logic
- 🔴 **PROBLEM:** Phase 3B claimed "schema-driven" but it's not actually implemented

---

## 🔌 API ENDPOINTS (ACTUAL URLS)

### Settings APIs (CLAIMED TO WORK)

| Endpoint | Method | Frontend Calls | Backend Exists | WORKING? |
|----------|--------|----------------|----------------|----------|
| `/me/settings/basic/` | POST | ✅ Yes (settings.js:40) | ✅ Yes (fe_v2.py) | ❓ UNTESTED |
| `/me/settings/social/` | POST | ✅ Yes (settings.js:48) | ✅ Yes (fe_v2.py) | ❓ UNTESTED |
| `/me/settings/media/` | POST | ✅ Yes (settings.js:56) | ✅ Yes (settings_api.py) | ❓ UNTESTED |
| `/me/settings/media/remove/` | POST | ✅ Yes (settings.js:64) | ✅ Yes (settings_api.py) | ❓ UNTESTED |
| `/me/settings/privacy/` | GET | ✅ Yes (settings.js:72) | ✅ Yes (settings_api.py) | ❓ UNTESTED |
| `/me/settings/privacy/save/` | POST | ✅ Yes (settings.js:78) | ✅ Yes (settings_api.py) | ❓ UNTESTED |

**Reality Check:** URLs exist but **NO RUNTIME VERIFICATION**

### Game Passport APIs (CLAIMED TO WORK)

| Endpoint | Method | Frontend Calls | Backend Exists | WORKING? |
|----------|--------|----------------|----------------|----------|
| `/api/games/` | GET | ✅ Yes (modal:loadGames) | ❌ **NOT FOUND** | 🔴 **BROKEN** |
| `/api/games/<id>/schema/` | GET | ❌ No (not called) | ❌ **NOT FOUND** | 🔴 **BROKEN** |
| `/api/passports/create/` | POST | ✅ Yes (modal) | ✅ Yes (passport_create.py) | ❓ UNTESTED |
| `/api/passports/toggle-lft/` | POST | ❓ Unknown | ✅ Yes (passport_api.py) | ❓ UNTESTED |
| `/api/passports/pin/` | POST | ❓ Unknown | ✅ Yes (passport_api.py) | ❓ UNTESTED |
| `/api/passports/<id>/delete/` | POST | ❓ Unknown | ✅ Yes (passport_api.py) | ❓ UNTESTED |

**Reality Check:**
- 🔴 **CRITICAL:** `/api/games/` endpoint **DOES NOT EXIST**
- 🔴 **CRITICAL:** Phase 3B claimed this was implemented, **IT WAS NOT**
- 🔴 **CRITICAL:** Modal will fail to load games dynamically

### Follow APIs (CLAIMED TO WORK)

| Endpoint | Method | Frontend Calls | Backend Exists | WORKING? |
|----------|--------|----------------|----------------|----------|
| `/actions/follow/<username>/` | POST | ❓ Unknown | ✅ Yes (urls.py:135) | ❓ UNTESTED |
| `/actions/unfollow/<username>/` | POST | ❓ Unknown | ✅ Yes (urls.py:136) | ❓ UNTESTED |

**Reality Check:** URLs exist but **NO RUNTIME VERIFICATION**

---

## 🚨 CRITICAL FINDINGS

### 1. Missing `/api/games/` Endpoint
**Status:** 🔴 **BLOCKING ISSUE**

**What I Claimed:** "Dynamic games loading from /api/games/ (DONE)"

**Reality:**
```bash
# Searched entire codebase:
grep -r "def games_list" apps/
# Result: NOT FOUND

grep -r "path.*api/games" apps/user_profile/urls.py
# Result: NOT FOUND
```

**Impact:**
- Modal will fall back to hardcoded 5-game list
- Phase 3B "dynamic loading" **IS NOT WORKING**
- Users cannot add new games without code deploy

**Fix Required:** Create `/api/games/` endpoint that returns game list

---

### 2. Schema-Driven Fields NOT Implemented
**Status:** 🔴 **MISLEADING DOCUMENTATION**

**What I Claimed:** "Schema-driven field validation from /api/games/<id>/schema/"

**Reality:**
- `GamePassportSchema` model exists but is **NEVER USED**
- Frontend hardcodes `requires_discriminator` logic
- No endpoint returns field schemas
- Modal cannot adapt to new games automatically

**Impact:**
- Adding new games requires frontend code changes
- Cannot customize fields per game without deploy

---

### 3. Privacy Settings Conflict
**Status:** ⚠️ **DATA INTEGRITY RISK**

**Problem:**
- `UserProfile.profile_visibility` field exists (legacy)
- `PrivacySettings` model has 15 granular settings
- **NO SYNC LOGIC** between them

**Questions:**
- Which is authoritative?
- If both exist, which one is checked?
- Can they contradict each other?

**Impact:**
- Profile visibility may be unpredictable
- Privacy violations possible if wrong field checked

---

### 4. UserActivity and UserProfileStats
**Status:** ❓ **ZOMBIE MODELS**

**Problem:**
- Models exist
- No evidence they're populated
- No frontend displays them
- No admin for them

**Impact:**
- Database bloat?
- Abandoned feature?

---

### 5. Match History
**Status:** ⚠️ **INCOMPLETE FEATURE**

**Problem:**
- `Match` model exists
- Template shows matches
- **NO API TO CREATE MATCHES**
- No integration with actual game data

**Impact:**
- Match history is manually populated (if at all)
- Not a working feature

---

## 📊 MODEL STATUS SUMMARY

| Model | Status | Used By Frontend | Used By Admin | Actually Working |
|-------|--------|------------------|---------------|------------------|
| UserProfile | ✅ ACTIVE | ✅ Yes | ✅ Yes | ✅ Yes |
| PrivacySettings | ✅ ACTIVE | ⚠️ Partial | ✅ Yes | ⚠️ Conflict with profile_visibility |
| VerificationRecord | ✅ ACTIVE | ❌ No | ✅ Yes | ✅ Yes |
| Badge | ✅ ACTIVE | ✅ Yes | ✅ Yes | ✅ Yes |
| UserBadge | ✅ ACTIVE | ✅ Yes | ✅ Yes | ✅ Yes |
| SocialLink | ✅ ACTIVE | ✅ Yes | ✅ Yes | ❓ Untested |
| GameProfile | ✅ ACTIVE | ✅ Yes | ✅ Yes | ⚠️ Creation broken |
| GameProfileAlias | ✅ ACTIVE | ❌ No | ✅ Yes | ✅ Yes |
| GameProfileConfig | ✅ ACTIVE | ❌ No | ✅ Yes | ✅ Yes |
| Achievement | ⚠️ PARTIAL | ✅ Yes | ✅ Yes | ❓ Duplicate of Badge? |
| Match | ⚠️ PARTIAL | ✅ Yes | ✅ Yes | ❌ No creation API |
| Certificate | ⚠️ PARTIAL | ✅ Yes | ✅ Yes | ❓ Untested |
| Follow | ✅ ACTIVE | ✅ Yes | ❌ No | ❓ Untested |
| UserAuditEvent | ✅ ACTIVE | ❌ No | ✅ Yes | ✅ Yes |
| UserProfileStats | ❓ UNKNOWN | ❌ No | ❌ No | ❌ Orphaned? |
| UserActivity | ❓ UNKNOWN | ❌ No | ❌ No | ❌ Orphaned? |
| GamePassportSchema | ❌ UNUSED | ❌ No | ❌ No | ❌ Dead code |

---

## 🎯 NEXT STEPS (HONEST)

### CRITICAL (Must Fix Before Launch)
1. **Create `/api/games/` endpoint** - Modal is broken without it
2. **Fix privacy settings conflict** - Choose one source of truth
3. **Verify passport creation** - Does it actually work?

### HIGH (Should Fix)
4. **Remove or implement GamePassportSchema** - Dead code or implement it
5. **Clarify Achievement vs Badge** - Redundant models?
6. **Document UserActivity/Stats** - Are these used?

### MEDIUM (Can Wait)
7. **Match creation API** - Complete the feature or remove it
8. **Follow/unfollow testing** - Verify it works

---

**Status:** Backend exists but **NOT FULLY WIRED**  
**Confidence:** 🔴 **LOW** - Many unknowns remain  
**Next:** Phase 4B - API Contract Verification (test every endpoint)
