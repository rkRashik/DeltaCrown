# User Profile - Django Admin Audit

**Generated:** December 28, 2025  
**Purpose:** Document Django admin registrations and configurations

---

## Admin Modules

### Primary Admin File

**File:** `admin.py` (1560 lines)

### Admin Package

**Directory:** `admin/`
- `forms.py` - Custom admin forms
- `game_passports.py` - Game passport admin
- `privacy.py` - Privacy settings admin
- `users.py` - User profile admin
- `exports.py` - Export utilities
- `game_profiles_field.py` - Custom field widgets

---

## Registered Models

Based on imports from `admin.py:7-42`:

| Model | Admin Class | Inlines | Status |
|-------|------------|---------|---------|
| `UserProfile` | `UserProfileAdmin` | PrivacySettings, SocialLink, GameProfile | ✅ **REGISTERED** |
| `PrivacySettings` | Inline only | N/A | ✅ **REGISTERED** (inline) |
| `VerificationRecord` | `VerificationRecordAdmin` | None | ✅ **REGISTERED** |
| `Badge` | `BadgeAdmin` | None | ✅ **REGISTERED** |
| `UserBadge` | `UserBadgeAdmin` | None | ✅ **REGISTERED** |
| `SocialLink` | Inline + standalone | None | ✅ **REGISTERED** |
| `GameProfile` | Inline + standalone | GameProfileAlias | ✅ **REGISTERED** |
| `GameProfileAlias` | Inline only | N/A | ✅ **REGISTERED** (inline) |
| `GameProfileConfig` | `GameProfileConfigAdmin` | None | ✅ **REGISTERED** |
| `Achievement` | `AchievementAdmin` | None | ✅ **REGISTERED** |
| `Match` | `MatchAdmin` | None | ✅ **REGISTERED** |
| `Certificate` | `CertificateAdmin` | None | ✅ **REGISTERED** |
| `UserActivity` | `UserActivityAdmin` | None | ✅ **REGISTERED** |
| `UserProfileStats` | `UserProfileStatsAdmin` | None | ✅ **REGISTERED** |
| `UserAuditEvent` | `UserAuditEventAdmin` | None | ✅ **REGISTERED** |

---

## Inline Admins

### `PrivacySettingsInline`

**Model:** `PrivacySettings`  
**Type:** StackedInline  
**Parent:** `UserProfile`

**Fields:**
```python
fields = [
    ('show_real_name', 'show_phone', 'show_email'),
    ('show_age', 'show_gender', 'show_country'),
    ('show_game_ids', 'show_social_links'),
    ('show_match_history', 'show_teams', 'show_achievements'),
    ('allow_team_invites', 'allow_friend_requests', 'allow_direct_messages'),
]
```

**Status:** ✅ **ACTIVE** - Inline privacy editor on UserProfile admin

---

### `SocialLinkInline`

**Model:** `SocialLink`  
**Type:** TabularInline  
**Parent:** `UserProfile`

**Fields:** `platform`, `url`, `handle`, `is_verified`

**Status:** ✅ **ACTIVE** - Inline social links editor

---

### `GameProfileInline`

**Model:** `GameProfile`  
**Type:** TabularInline  
**Parent:** `UserProfile`

**Fields:** `game`, `in_game_name`, `rank_name`, `main_role`, `matches_played`, `win_rate`, `updated_at`

**Status:** ✅ **ACTIVE** - Replaces legacy JSON `game_profiles` field

---

### `GameProfileAliasInline`

**Model:** `GameProfileAlias`  
**Type:** TabularInline  
**Parent:** `GameProfile`

**Fields:** `old_in_game_name`, `changed_at`, `changed_by_user_display`, `request_ip`, `reason`

**Permissions:** Read-only (no add/delete)

**Status:** ✅ **ACTIVE** - Shows identity change history

---

## Key Admin Features

### UserProfile Admin

**List Display:**
- User, Display Name, Public ID, Level, XP
- KYC Status, Region, Created At

**List Filters:**
- Region, KYC Status, Level Range, Is Private

**Search Fields:**
- Username, Email, Display Name, Public ID

**Fieldsets:**
```
1. System Identity (read-only: user, uuid, public_id)
2. Legal Identity (real_full_name, DOB, nationality, KYC)
3. Public Identity (display_name, avatar, banner, bio)
4. Location (country, region, city)
5. Contact (phone, email)
6. Emergency Contact (LAN events)
7. Competitive (reputation_score, skill_rating)
8. Gamification (level, XP, badges)
9. Economy (deltacoin_balance, lifetime_earnings)
10. Social Links (legacy fields - deprecated)
11. Privacy Settings (legacy fields - deprecated)
```

**Admin Actions:**
- Export selected profiles
- Sync economy data
- Recompute stats
- Verify KYC (bulk)

**Status:** ✅ **ACTIVE & COMPREHENSIVE**

---

### Game Passport Admin

**Features:**
- View all game profiles per user
- Identity change history (via inline)
- Cooldown enforcement visibility
- Audit trail links

**Status:** ✅ **ACTIVE** - Professional game passport management

---

### Audit Admin

**UserAuditEvent Admin:**
- **List Display:** Event Type, Subject User, Actor User, Object Type, Created At
- **List Filters:** Event Type, Source App, Created At
- **Search:** Subject User, Actor User, Request ID
- **Read-Only:** All fields (append-only model)

**Status:** ✅ **ACTIVE** - Full audit trail visibility

---

## Admin Security

### Permissions

All admins respect Django's standard permission system:
- `view_*` - View permission
- `add_*` - Create permission
- `change_*` - Edit permission
- `delete_*` - Delete permission

### Restricted Operations

**UserAuditEvent:**
- ❌ No add/change/delete - Append-only model

**GameProfileAlias:**
- ❌ No add/delete - Created by service only

---

## Admin Custom Forms

### `UserProfileAdminForm`

**File:** `admin/forms.py`

**Custom Validations:**
- Public ID format validation
- Age validation (DOB not in future)
- Phone format validation
- Emergency contact completeness

**Status:** ✅ **ACTIVE**

---

## Admin Actions

### Profile Actions

1. **Export Profiles** - CSV export with selected fields
2. **Sync Economy** - Sync DeltaCrownWallet → UserProfile
3. **Recompute Stats** - Rebuild UserProfileStats from events
4. **Verify KYC** - Bulk KYC approval

### Game Passport Actions

1. **Export Game Profiles** - CSV export
2. **Validate Identity Keys** - Check uniqueness

---

## Critical Findings

### ✅ Well-Configured Admin

1. **Comprehensive coverage** - All models registered
2. **Inline editors** - Privacy, social, game passports
3. **Audit visibility** - Full event log access
4. **Security** - Proper permissions, read-only audit logs
5. **Professional UX** - Fieldsets, list filters, search

### ⚠️ Minor Issues

1. **Legacy fields visible** - `game_profiles` JSON field still in fieldset
   - Should hide after full migration to GameProfile model

2. **Dual privacy UI** - Privacy fields on UserProfile AND PrivacySettings inline
   - Confusing for admins
   - Should consolidate to PrivacySettings only

### 🔍 Recommendations

1. **Hide deprecated fields:**
   - `game_profiles` (JSON) - Use GameProfile model instead
   - Social link fields on UserProfile - Use SocialLink model instead

2. **Add admin documentation:**
   - Inline help text for complex fields
   - Links to documentation

3. **Add bulk actions:**
   - Bulk public ID assignment (for backfill)
   - Bulk stats recomputation

---

## Admin URLs

| URL | Purpose |
|-----|---------|
| `/admin/user_profile/userprofile/` | User profiles list |
| `/admin/user_profile/gameprofile/` | Game passports list |
| `/admin/user_profile/userauditevent/` | Audit log |
| `/admin/user_profile/useractivity/` | Activity events |
| `/admin/user_profile/userprofilestats/` | Profile stats |
| `/admin/user_profile/privacysettings/` | Privacy settings |
| `/admin/user_profile/badge/` | Badges |
| `/admin/user_profile/userbadge/` | User badge assignments |

---

**Document Status:** ✅ Phase C Complete
