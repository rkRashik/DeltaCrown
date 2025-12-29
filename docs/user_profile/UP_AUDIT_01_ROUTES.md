# User Profile - URL Routing Truth Table

**Generated:** December 28, 2025  
**Purpose:** Complete mapping of all URL routes to views, templates, and static resources

---

## Route Categories

### 1. V2 Public Profile Routes (@ prefix)

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `@<username>/` | `profile_public_v2` | `user_profile/profile/public.html` | Inline JS only | `views/fe_v2.py` | **ACTIVE** - Main public profile |
| `@<username>/` | `profile_public_v2` (alias) | `user_profile/profile/public.html` | Inline JS only | `views/fe_v2.py` | Alias for backward compatibility (name='profile') |
| `@<username>/activity/` | `profile_activity_v2` | `user_profile/profile/activity.html` | Inline JS only | `views/fe_v2.py` | **ACTIVE** - Activity feed page |
| `@<username>/followers/` | `followers_list` | TBD | TBD | `views/legacy_views.py` | **NEEDS VERIFICATION** |
| `@<username>/following/` | `following_list` | TBD | TBD | `views/legacy_views.py` | **NEEDS VERIFICATION** |

### 2. V2 Owner Pages (/me/ prefix)

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `me/settings/` | `profile_settings_v2` | `user_profile/profile/settings.html` | `user_profile/settings.js` | `views/fe_v2.py` | **ACTIVE** - Main settings page |
| `me/settings/` | `profile_settings_v2` (alias) | Same as above | Same as above | `views/fe_v2.py` | Alias for template compatibility (name='settings') |
| `me/privacy/` | `profile_privacy_v2` | `user_profile/profile/privacy.html` | TBD | `views/fe_v2.py` | **ACTIVE** - Privacy settings page |

### 3. V2 Settings Mutation Endpoints

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `me/settings/basic/` | `update_basic_info` | JSON response | N/A | `views/fe_v2.py` | POST only - Update display_name, bio, etc. |
| `me/settings/social/` | `update_social_links` | JSON response | N/A | `views/fe_v2.py` | POST only |
| `me/settings/media/` | `upload_media` | JSON response | N/A | `views/settings_api.py` | POST only - Upload avatar/banner |
| `me/settings/media/remove/` | `remove_media_api` | JSON response | N/A | `views/settings_api.py` | POST only |
| `me/settings/privacy/` | `get_privacy_settings` | JSON response | N/A | `views/settings_api.py` | GET only |
| `me/settings/privacy/save/` | `update_privacy_settings` | JSON response | N/A | `views/settings_api.py` | POST only |
| `me/settings/platform/` | `update_platform_settings` | JSON response | N/A | `views/settings_api.py` | POST only |

### 4. Game Passport API (GP-FE-MVP-01)

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `api/passports/toggle-lft/` | `toggle_lft` | JSON response | N/A | `views/passport_api.py` | POST only |
| `api/passports/set-visibility/` | `set_visibility` | JSON response | N/A | `views/passport_api.py` | POST only |
| `api/passports/pin/` | `pin_passport` | JSON response | N/A | `views/passport_api.py` | POST only |
| `api/passports/reorder/` | `reorder_passports` | JSON response | N/A | `views/passport_api.py` | POST only |
| `api/passports/create/` | `create_passport` | JSON response | N/A | `views/passport_create.py` | POST only |
| `api/passports/<int:passport_id>/delete/` | `delete_passport` | JSON response | N/A | `views/passport_api.py` | POST only |

### 5. Additional Settings API

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `api/social-links/` | `get_social_links` | JSON response | N/A | `views/settings_api.py` | GET only |
| `api/social-links/update/` | `update_social_links_api` | JSON response | N/A | `views/settings_api.py` | POST only |
| `api/platform-settings/` | `get_platform_settings` | JSON response | N/A | `views/settings_api.py` | GET only |
| `api/profile/data/` | `get_profile_data` | JSON response | N/A | `views/settings_api.py` | GET only |

### 6. Legacy Owner Pages

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `me/edit/` | `MyProfileUpdateView` | Redirects to `me/settings/` | N/A | `views_settings.py` | **REDIRECT ONLY** - GET redirects to settings |
| `me/tournaments/` | `my_tournaments_view` | TBD | TBD | `views/legacy_views.py` | **NEEDS VERIFICATION** |
| `me/kyc/upload/` | `kyc_upload_view` | TBD | TBD | `views/legacy_views.py` | **NEEDS VERIFICATION** |
| `me/kyc/status/` | `kyc_status_view` | TBD | TBD | `views/legacy_views.py` | **NEEDS VERIFICATION** |

### 7. Modal Action Endpoints (POST handlers)

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `actions/save-game-profiles/` | `save_game_profiles` | JSON response | N/A | `views/legacy_views.py` | POST only - **LEGACY** |
| `actions/update-bio/` | `update_bio` | JSON response | N/A | `views/legacy_views.py` | POST only - **LEGACY** |
| `actions/add-social-link/` | `add_social_link` | JSON response | N/A | `views/legacy_views.py` | POST only - **LEGACY** |
| `actions/add-game-profile/` | `add_game_profile` | JSON response | N/A | `views/legacy_views.py` | POST only - **LEGACY** |
| `actions/edit-game-profile/<int:profile_id>/` | `edit_game_profile` | JSON response | N/A | `views/legacy_views.py` | POST only - **LEGACY** |
| `actions/delete-game-profile/<int:profile_id>/` | `delete_game_profile` | JSON response | N/A | `views/legacy_views.py` | POST only - **LEGACY** |
| `actions/follow/<str:username>/` | `follow_user` | JSON response | N/A | `views/legacy_views.py` | POST only |
| `actions/unfollow/<str:username>/` | `unfollow_user` | JSON response | N/A | `views/legacy_views.py` | POST only |

### 8. Safe Mutation Endpoints (UP-CLEANUP-04 Phase C)

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `actions/privacy-settings/save/` | `privacy_settings_save_safe` | JSON response | N/A | `views/legacy_views.py` | POST only - With audit trail |
| `actions/follow-safe/<str:username>/` | `follow_user_safe` | JSON response | N/A | `views/legacy_views.py` | POST only - With audit |
| `actions/unfollow-safe/<str:username>/` | `unfollow_user_safe` | JSON response | N/A | `views/legacy_views.py` | POST only - With audit |
| `actions/game-profiles/save/` | `save_game_profiles_safe` | JSON response | N/A | `views/legacy_views.py` | POST only - With validation + audit |
| `api/profile/update-game-id-safe/` | `update_game_id_safe` | JSON response | N/A | `views/legacy_views.py` | POST only - Safe game ID update |

### 9. Game ID API Endpoints

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `api/profile/get-game-id/` | `redirect_get_game_id` | **301 REDIRECT** | N/A | `urls.py` (inline) | Redirects to `api/profile/game-ids/` |
| `api/profile/update-game-id/` | `update_game_id` | JSON response | N/A | `api_views.py` | POST only - **WRAPPER** (will migrate) |
| `api/profile/check-game-id/<str:game_code>/` | `check_game_id_api` | JSON response | N/A | `api/game_id_api.py` | GET only |
| `api/profile/save-game-id/<str:game_code>/` | `save_game_id_api` | JSON response | N/A | `api/game_id_api.py` | POST only |
| `api/profile/game-ids/` | `get_all_game_ids_api` | JSON response | N/A | `api/game_id_api.py` | GET only |
| `api/profile/delete-game-id/<str:game_code>/` | `delete_game_id_api` | JSON response | N/A | `api/game_id_api.py` | POST only |

### 10. Catch-all Profile API

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `api/profile/<str:profile_id>/` | `profile_api` | JSON response | N/A | `views_public.py` | GET only - **MUST BE AFTER SPECIFIC ROUTES** |

### 11. Legacy Public Profile Pages

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `legacy/@<username>/achievements/` | `achievements_view` | TBD | TBD | `views/legacy_views.py` | **LEGACY PREFIX** - Still active |
| `legacy/@<username>/match-history/` | `match_history_view` | TBD | TBD | `views/legacy_views.py` | **LEGACY PREFIX** - Still active |
| `legacy/@<username>/certificates/` | `certificates_view` | TBD | TBD | `views/legacy_views.py` | **LEGACY PREFIX** - Still active |

### 12. Legacy Compatibility Routes (301 Redirects)

| Route Pattern | View Function | Template | Static JS | View File | Notes |
|--------------|---------------|----------|-----------|-----------|-------|
| `u/<username>/` | `redirect_to_modern_profile` | **301 REDIRECT** | N/A | `urls.py` (inline) | Redirects to `@<username>/` |
| `<username>/` | `redirect_to_modern_profile` | **301 REDIRECT** | N/A | `urls.py` (inline) | Redirects to `@<username>/` |

---

## Summary Statistics

- **Total Routes:** 53
- **Active View Routes (HTML):** 5
- **API Endpoints (JSON):** 35
- **Redirects (301):** 3
- **Legacy Routes (marked for review):** 10

---

## Critical Findings

### ✅ Properly Configured

1. **V2 routes** (`profile_public_v2`, `profile_settings_v2`, `profile_privacy_v2`) are the **current canonical routes**
2. **Template wiring** confirmed:
   - `public.html` used by `profile_public_v2`
   - `settings.html` used by `profile_settings_v2`
   - `privacy.html` used by `profile_privacy_v2`
3. **Static JS** correctly loaded:
   - `settings.html` loads `user_profile/settings.js`
   - `public.html` uses inline JS only (no external file)

### ⚠️ Needs Investigation

1. **Legacy view functions** imported in urls.py but may not be actively used:
   - `profile_view` (deprecated, replaced by `profile_public_v2`)
   - `my_tournaments_view`, `kyc_upload_view`, `kyc_status_view`
   - `privacy_settings_view`, `settings_view` (both commented out in urls.py!)

2. **Duplicate mutation endpoints:**
   - Old: `save_game_profiles` vs New: `save_game_profiles_safe`
   - Old: `follow_user` vs New: `follow_user_safe`
   - Need to verify which are actually used by frontend

3. **Missing template references:**
   - `followers_list`, `following_list`, `achievements_view`, `match_history_view`, `certificates_view` templates not yet identified

### 🔴 Code Smell

1. **views/legacy_views.py** has 1569 lines - contains many functions that may be dead code
2. **Commented out routes** in urls.py (lines 126-127) suggest incomplete migration:
   ```python
   # path("me/privacy/", privacy_settings_view, name="privacy_settings"),  # Replaced by profile_privacy_v2
   # path("me/settings/", settings_view, name="settings"),  # Replaced by profile_settings_v2
   ```

---

## Next Steps (Phase A2)

1. Search for all template references in views to build complete template wiring map
2. Verify which static JS files are loaded by each template
3. Check for orphaned templates (not rendered by any mounted view)

---

**Document Status:** ✅ Phase A1 Complete
