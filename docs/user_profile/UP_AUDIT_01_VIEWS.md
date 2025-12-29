# User Profile - View Modules Inventory

**Generated:** December 28, 2025  
**Purpose:** Audit all view modules, identify duplicates/overlaps, and determine mounted status

---

## View Files Overview

| File | Lines | Mounted Routes | Status |
|------|-------|---------------|---------|
| `views/fe_v2.py` | 658 | 7 routes | ✅ **ACTIVE & CANONICAL** |
| `views/passport_api.py` | 263 | 6 routes | ✅ **ACTIVE** |
| `views/passport_create.py` | 151 | 1 route | ✅ **ACTIVE** |
| `views/settings_api.py` | 599 | 10 routes | ✅ **ACTIVE** |
| `views/public.py` | ~100 | 0 routes | ⚠️ **NOT MOUNTED** (helper) |
| `views/legacy_views.py` | 1569 | 13+ routes | ⚠️ **MIXED** (some active, some deprecated) |
| `views_public.py` | 585 | 2 routes | ⚠️ **LEGACY** (catch-all API) |
| `views_settings.py` | 100 | 1 route (redirect) | ⚠️ **REDIRECT ONLY** |
| `api_views.py` | Unknown | 1 route (wrapper) | ⚠️ **LEGACY WRAPPER** |
| `api/game_id_api.py` | Unknown | 4 routes | ✅ **ACTIVE** |

---

## 1. `views/fe_v2.py` - Frontend V2 Views

**File:** `views/fe_v2.py` (658 lines)  
**Status:** ✅ **ACTIVE & CANONICAL** - Primary V2 views

### Mounted Routes (7 total)

| Function | Route | Method | Template | Status |
|----------|-------|--------|----------|---------|
| `profile_public_v2` | `@<username>/` | GET | `profile/public.html` | ✅ **CANONICAL** |
| `profile_activity_v2` | `@<username>/activity/` | GET | `profile/activity.html` | ✅ **CANONICAL** |
| `profile_settings_v2` | `me/settings/` | GET | `profile/settings.html` | ✅ **CANONICAL** |
| `profile_privacy_v2` | `me/privacy/` | GET | `profile/privacy.html` | ✅ **CANONICAL** |
| `update_basic_info` | `me/settings/basic/` | POST | JSON response | ✅ **ACTIVE** |
| `update_social_links` | `me/settings/social/` | POST | JSON response | ✅ **ACTIVE** |

### Architecture

- ✅ Uses `build_public_profile_context()` service
- ✅ Privacy-safe (NO raw ORM objects)
- ✅ Enforces ownership via `@login_required`
- ✅ Returns safe primitives/JSON only

### Dependencies

- `services/profile_context.py`
- `services/game_passport_service.py`
- `models.UserProfile`, `models.GameProfile`

### Verdict

✅ **PRIMARY VIEWS** - These are the current, canonical profile views. All other views are deprecated or auxiliary.

---

## 2. `views/passport_api.py` - Game Passport API

**File:** `views/passport_api.py` (263 lines)  
**Status:** ✅ **ACTIVE** - Game passport management endpoints

### Mounted Routes (6 total)

| Function | Route | Method | Purpose |
|----------|-------|--------|---------|
| `toggle_lft` | `api/passports/toggle-lft/` | POST | Toggle looking-for-team status |
| `set_visibility` | `api/passports/set-visibility/` | POST | Change privacy level |
| `pin_passport` | `api/passports/pin/` | POST | Pin/unpin passport |
| `reorder_passports` | `api/passports/reorder/` | POST | Change pinned order |
| `delete_passport` | `api/passports/<int:passport_id>/delete/` | POST | Delete passport |

### Architecture

- ✅ All use `GamePassportService` (NO JSON writes)
- ✅ CSRF protected
- ✅ Returns JSON responses
- ✅ Audit logging via service layer

### Verdict

✅ **ACTIVE & CRITICAL** - Core passport management API

---

## 3. `views/passport_create.py` - Passport Creation

**File:** `views/passport_create.py` (151 lines)  
**Status:** ✅ **ACTIVE** - Passport creation endpoint

### Mounted Routes (1 total)

| Function | Route | Method | Purpose |
|----------|-------|--------|---------|
| `create_passport` | `api/passports/create/` | POST | Create new game passport |

### Architecture

- ✅ Uses `GamePassportService.create_passport()`
- ✅ Validates game existence
- ✅ Prevents duplicates
- ✅ Audit logging

### Verdict

✅ **ACTIVE & ESSENTIAL** - Primary passport creation endpoint

---

## 4. `views/settings_api.py` - Settings API

**File:** `views/settings_api.py` (599 lines)  
**Status:** ✅ **ACTIVE** - Settings mutation endpoints

### Mounted Routes (10 total)

| Function | Route | Method | Purpose |
|----------|-------|--------|---------|
| `upload_media` | `me/settings/media/` | POST | Upload avatar/banner |
| `remove_media_api` | `me/settings/media/remove/` | POST | Remove avatar/banner |
| `get_privacy_settings` | `me/settings/privacy/` | GET | Get privacy settings |
| `update_privacy_settings` | `me/settings/privacy/save/` | POST | Update privacy settings |
| `get_social_links` | `api/social-links/` | GET | Get social links |
| `update_social_links_api` | `api/social-links/update/` | POST | Update social links |
| `get_platform_settings` | `api/platform-settings/` | GET | Get platform settings |
| `update_platform_settings` | `me/settings/platform/` | POST | Update platform settings |
| `get_profile_data` | `api/profile/data/` | GET | Get profile data for settings |

### Architecture

- ✅ CSRF protected
- ✅ Image validation (PIL)
- ✅ File size limits enforced
- ✅ Returns JSON responses

### Verdict

✅ **ACTIVE & ESSENTIAL** - Core settings API endpoints

---

## 5. `views/public.py` - Public Profile Helper

**File:** `views/public.py` (~100 lines)  
**Status:** ⚠️ **NOT MOUNTED** - Helper functions only

### Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `public_profile` | Render public profile | NOT MOUNTED (helper code) |
| `profile_api` | JSON API for profile | MOUNTED via `views_public.py` |

### Verdict

⚠️ **HELPER MODULE** - Contains reusable logic but not directly mounted

---

## 6. `views/legacy_views.py` - Legacy Views

**File:** `views/legacy_views.py` (1569 lines)  
**Status:** ⚠️ **MIXED** - Contains both active and deprecated views

### Mounted Views (Active)

| Function | Route | Status |
|----------|-------|---------|
| `my_tournaments_view` | `me/tournaments/` | 🟡 **MOUNTED** |
| `kyc_upload_view` | `me/kyc/upload/` | 🟡 **MOUNTED** |
| `kyc_status_view` | `me/kyc/status/` | 🟡 **MOUNTED** |
| `followers_list` | `@<username>/followers/` | 🟡 **MOUNTED** |
| `following_list` | `@<username>/following/` | 🟡 **MOUNTED** |
| `achievements_view` | `legacy/@<username>/achievements/` | 🟡 **MOUNTED** (legacy prefix) |
| `match_history_view` | `legacy/@<username>/match-history/` | 🟡 **MOUNTED** (legacy prefix) |
| `certificates_view` | `legacy/@<username>/certificates/` | 🟡 **MOUNTED** (legacy prefix) |
| `follow_user` | `actions/follow/<username>/` | 🟡 **MOUNTED** |
| `unfollow_user` | `actions/unfollow/<username>/` | 🟡 **MOUNTED** |
| `follow_user_safe` | `actions/follow-safe/<username>/` | ✅ **SAFE VERSION** |
| `unfollow_user_safe` | `actions/unfollow-safe/<username>/` | ✅ **SAFE VERSION** |

### NOT Mounted (Deprecated)

| Function | Original Route | Status |
|----------|---------------|---------|
| `profile_view` | `@<username>/` | ❌ **DEPRECATED** (marked with @deprecate_route) |
| `privacy_settings_view` | `me/privacy/` | ❌ **NOT MOUNTED** (commented out in urls.py) |
| `settings_view` | `me/settings/` | ❌ **NOT MOUNTED** (commented out in urls.py) |

### Action Endpoints (Legacy Mutation)

| Function | Route | Replacement |
|----------|-------|------------|
| `save_game_profiles` | `actions/save-game-profiles/` | ⚠️ Use `save_game_profiles_safe` |
| `update_bio` | `actions/update-bio/` | ⚠️ Use V2 `update_basic_info` |
| `add_social_link` | `actions/add-social-link/` | ⚠️ Use V2 `update_social_links_api` |
| `add_game_profile` | `actions/add-game-profile/` | ⚠️ Use `create_passport` |
| `edit_game_profile` | `actions/edit-game-profile/<int>/` | ⚠️ Use `GamePassportService.update_passport()` |
| `delete_game_profile` | `actions/delete-game-profile/<int>/` | ⚠️ Use `delete_passport` |

### Verdict

⚠️ **NEEDS CLEANUP** - This file is 1569 lines with:
- Mix of active and deprecated code
- Duplicate mutation endpoints (old vs safe versions)
- Should split into smaller modules
- Deprecate old mutation endpoints

---

## 7. `views_public.py` - Legacy Public Profile

**File:** `views_public.py` (585 lines)  
**Status:** ⚠️ **LEGACY** - Catch-all API only

### Mounted Routes (2 total)

| Function | Route | Purpose |
|----------|-------|---------|
| `public_profile` | NOT MOUNTED | Helper function |
| `profile_api` | `api/profile/<str:profile_id>/` | Catch-all JSON API |

### Architecture

- ⚠️ Renders old `profile.html` template
- ⚠️ Direct ORM access (NOT privacy-safe)
- ⚠️ Deprecated by `profile_public_v2`

### Verdict

⚠️ **LEGACY CATCH-ALL** - Only `profile_api` is mounted (catch-all endpoint)

---

## 8. `views_settings.py` - Legacy Settings

**File:** `views_settings.py` (100 lines)  
**Status:** ⚠️ **REDIRECT ONLY**

### Mounted Routes (1 total)

| Class/Function | Route | Behavior |
|---------------|-------|----------|
| `MyProfileUpdateView.get()` | `me/edit/` | **301 Redirect** to `me/settings/` |

### Verdict

⚠️ **REDIRECT WRAPPER** - No actual functionality, just redirects

---

## 9. `api_views.py` - Legacy Game ID API

**File:** `api_views.py`  
**Status:** ⚠️ **LEGACY WRAPPER**

### Mounted Routes (2 total)

| Function | Route | Purpose |
|----------|-------|---------|
| `get_game_id` | NOT MOUNTED (301 redirect in urls.py) | Redirect to `get_all_game_ids_api` |
| `update_game_id` | `api/profile/update-game-id/` | Legacy wrapper (will migrate) |

### Verdict

⚠️ **LEGACY WRAPPER** - Will be replaced by modern API

---

## 10. `api/game_id_api.py` - Modern Game ID API

**File:** `api/game_id_api.py`  
**Status:** ✅ **ACTIVE** - Modern game ID endpoints

### Mounted Routes (4 total)

| Function | Route | Method | Purpose |
|----------|-------|--------|---------|
| `check_game_id_api` | `api/profile/check-game-id/<str:game_code>/` | GET | Check if game ID exists |
| `save_game_id_api` | `api/profile/save-game-id/<str:game_code>/` | POST | Save game ID |
| `get_all_game_ids_api` | `api/profile/game-ids/` | GET | Get all game IDs for user |
| `delete_game_id_api` | `api/profile/delete-game-id/<str:game_code>/` | POST | Delete game ID |

### Verdict

✅ **ACTIVE & MODERN** - Replacement for legacy game ID API

---

## View Duplication Analysis

### Profile View Duplication

| View | File | Route | Status |
|------|------|-------|---------|
| `profile_public_v2` | `views/fe_v2.py` | `@<username>/` | ✅ **CANONICAL** |
| `profile_view` | `views/legacy_views.py` | NOT MOUNTED | ❌ **DEPRECATED** |
| `public_profile` | `views_public.py` | NOT MOUNTED | ❌ **DEPRECATED** |

**Verdict:** ✅ Duplication resolved - Only V2 is mounted

### Settings View Duplication

| View | File | Route | Status |
|------|------|-------|---------|
| `profile_settings_v2` | `views/fe_v2.py` | `me/settings/` | ✅ **CANONICAL** |
| `settings_view` | `views/legacy_views.py` | NOT MOUNTED | ❌ **DEPRECATED** |
| `MyProfileUpdateView` | `views_settings.py` | `me/edit/` (redirect) | ⚠️ **REDIRECT ONLY** |

**Verdict:** ✅ Duplication resolved - Only V2 is mounted

### Privacy View Duplication

| View | File | Route | Status |
|------|------|-------|---------|
| `profile_privacy_v2` | `views/fe_v2.py` | `me/privacy/` | ✅ **CANONICAL** |
| `privacy_settings_view` | `views/legacy_views.py` | NOT MOUNTED | ❌ **DEPRECATED** |

**Verdict:** ✅ Duplication resolved - Only V2 is mounted

### Mutation Endpoint Duplication

| Old Endpoint | New Endpoint | Status |
|-------------|--------------|---------|
| `follow_user` | `follow_user_safe` | ⚠️ Both mounted |
| `unfollow_user` | `unfollow_user_safe` | ⚠️ Both mounted |
| `save_game_profiles` | `save_game_profiles_safe` | ⚠️ Both mounted |
| `add_game_profile` | `create_passport` | ⚠️ Both mounted |

**Verdict:** ⚠️ **NEEDS CLEANUP** - Old endpoints should be deprecated and frontend migrated to safe versions

---

## Critical Findings

### ✅ Properly Migrated to V2

1. **Profile views** - `profile_public_v2` is canonical, old views deprecated
2. **Settings views** - `profile_settings_v2` is canonical
3. **Privacy views** - `profile_privacy_v2` is canonical
4. **Passport API** - Modern service-based endpoints

### ⚠️ Needs Attention

1. **Duplicate mutation endpoints**:
   - Old: `follow_user`, `save_game_profiles`, `add_game_profile`
   - Safe: `follow_user_safe`, `save_game_profiles_safe`, `create_passport`
   - **Action:** Deprecate old versions, migrate frontend

2. **Legacy views still mounted**:
   - `my_tournaments_view`, `kyc_*_view`, `followers/following_list`
   - **Action:** Verify if still used, potentially migrate to V2 pattern

3. **Legacy component pages**:
   - `achievements_view`, `match_history_view`, `certificates_view` (under `/legacy/` prefix)
   - **Action:** Determine if these should be integrated into main profile or deprecated

### 🔴 Code Smell

1. **`legacy_views.py` is 1569 lines** - Contains too many concerns:
   - Deprecated views (commented out routes)
   - Active views (KYC, tournaments, follow)
   - Duplicate mutation endpoints
   - Helper functions
   - **Action:** Split into multiple focused modules

2. **Inconsistent architecture**:
   - V2 views use `profile_context` service ✅
   - Legacy views use direct ORM access ❌
   - **Action:** Refactor legacy views to use services

---

## Recommended Actions

### Phase 1: Frontend Migration
1. Update frontend to use safe mutation endpoints
2. Verify no usage of old mutation endpoints
3. Remove old mutation endpoints from urls.py

### Phase 2: Legacy View Refactor
1. Split `legacy_views.py` into:
   - `views/kyc.py` - KYC verification views
   - `views/tournaments.py` - Tournament views
   - `views/social.py` - Follow system views
   - `views/profile_components.py` - Achievements, match history, certificates
2. Migrate to service-based architecture
3. Add deprecation warnings

### Phase 3: Dead Code Removal
1. Delete deprecated functions:
   - `profile_view` (in legacy_views.py)
   - `privacy_settings_view` (in legacy_views.py)
   - `settings_view` (in legacy_views.py)
2. Delete unused helper views in `views/public.py`

---

**Document Status:** ✅ Phase B3 Complete
