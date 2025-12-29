# UP_INTEGRATION_01: Backend Truth Table

**Generated:** December 28, 2025  
**Purpose:** Complete audit of all user_profile routes with method, auth, payload, and response specifications

---

## Route Categories

1. **V2 Profile Pages** (HTML responses)
2. **Settings API** (JSON responses)
3. **Game Passport API** (JSON responses)
4. **Legacy Endpoints** (mixed/redirects)
5. **Admin & Utility** (various)

---

## 1. V2 Profile Pages (HTML Responses)

### GET /@<username>/
- **Name:** `profile_public_v2` / `profile`
- **View:** `views.fe_v2.profile_public_v2`
- **Auth:** Optional (guest + logged-in)
- **Payload:** None (URL param: username)
- **Response:** HTML (renders `templates/user_profile/profile/public.html`)
- **Privacy:** Uses `ProfileVisibilityPolicy` based on viewer
- **Status:** ✅ Active (canonical)

### GET /@<username>/activity/
- **Name:** `profile_activity_v2`
- **View:** `views.fe_v2.profile_activity_v2`
- **Auth:** Optional
- **Payload:** None
- **Response:** HTML (renders `templates/user_profile/profile/activity.html`)
- **Status:** ✅ Active

### GET /me/settings/
- **Name:** `profile_settings_v2` / `settings`
- **View:** `views.fe_v2.profile_settings_v2`
- **Auth:** **Required** (`@login_required`)
- **Payload:** None
- **Response:** HTML (renders `templates/user_profile/profile/settings.html`)
- **Status:** ✅ Active (canonical)

### GET /me/privacy/
- **Name:** `profile_privacy_v2`
- **View:** `views.fe_v2.profile_privacy_v2`
- **Auth:** **Required**
- **Payload:** None
- **Response:** HTML (renders `templates/user_profile/profile/privacy.html`)
- **Status:** ✅ Active

---

## 2. Settings API (JSON Responses)

### POST /me/settings/basic/
- **Name:** `update_basic_info`
- **View:** `views.fe_v2.update_basic_info`
- **Auth:** **Required**
- **Method:** POST
- **Payload (FormData):**
  - `display_name` (string, required)
  - `bio` (string, optional)
  - `pronouns` (string, optional)
  - `country` (string, optional)
  - `city` (string, optional)
- **Response:** JSON `{success: bool, error?: string}`
- **Status:** ✅ Active

### POST /me/settings/social/
- **Name:** `update_social_links`
- **View:** `views.fe_v2.update_social_links`
- **Auth:** **Required**
- **Method:** POST
- **Payload (FormData):**
  - `youtube_link` (URL, optional)
  - `twitch_link` (URL, optional)
  - `discord_id` (string, optional)
  - `twitter` (string, optional)
  - `instagram` (string, optional)
  - `facebook` (URL, optional)
  - `tiktok` (string, optional)
- **Response:** JSON `{success: bool, message: string, error?: string}`
- **Status:** ✅ Active (but fields are legacy - uses old JSON model fields)

### POST /me/settings/media/
- **Name:** `upload_media`
- **View:** `views.settings_api.upload_media`
- **Auth:** **Required**
- **Method:** POST
- **Payload (multipart/form-data):**
  - `media_type` (string: 'avatar' | 'banner', required)
  - `file` (file, required)
- **Validation:**
  - Avatar: max 5MB, min 100x100px
  - Banner: max 10MB, min 1200x300px
  - Allowed types: JPEG, PNG, WebP
- **Response:** JSON `{success: bool, url: string, preview_url: string, error?: string}`
- **Status:** ✅ Active

### POST /me/settings/media/remove/
- **Name:** `remove_media`
- **View:** `views.settings_api.remove_media_api`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):**
  - `media_type` (string: 'avatar' | 'banner', required)
- **Response:** JSON `{success: bool, error?: string}`
- **Status:** ✅ Active

### GET /me/settings/privacy/
- **Name:** `get_privacy_settings`
- **View:** `views.settings_api.get_privacy_settings`
- **Auth:** **Required**
- **Method:** GET
- **Payload:** None
- **Response:** JSON with all privacy flags
  ```json
  {
    "show_real_name": bool,
    "show_phone": bool,
    "show_email": bool,
    "show_age": bool,
    "show_gender": bool,
    "show_country": bool,
    "show_game_ids": bool,
    "show_social_links": bool,
    "show_match_history": bool,
    "show_teams": bool,
    "show_achievements": bool,
    "allow_team_invites": bool,
    "allow_friend_requests": bool,
    "allow_direct_messages": bool
  }
  ```
- **Status:** ✅ Active

### POST /me/settings/privacy/save/
- **Name:** `update_privacy_settings`
- **View:** `views.settings_api.update_privacy_settings`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):** Any subset of privacy flags (same keys as GET)
- **Response:** JSON `{success: bool, message: string, error?: string}`
- **Status:** ✅ Active

### POST /me/settings/platform/
- **Name:** `update_platform_settings`
- **View:** `views.settings_api.update_platform_settings`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):**
  - `language` (string, optional)
  - `timezone` (string, optional)
  - `theme` (string, optional)
  - `notifications_enabled` (bool, optional)
- **Response:** JSON `{success: bool, message: string, error?: string}`
- **Status:** ✅ Active

### GET /api/social-links/
- **Name:** `get_social_links`
- **View:** `views.settings_api.get_social_links`
- **Auth:** **Required**
- **Method:** GET
- **Payload:** None
- **Response:** JSON with social links object
- **Status:** ✅ Active

### POST /api/social-links/update/
- **Name:** `update_social_links_api`
- **View:** `views.settings_api.update_social_links_api`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):** Social links object
- **Response:** JSON `{success: bool, error?: string}`
- **Status:** ✅ Active (duplicate of `/me/settings/social/`)

### GET /api/platform-settings/
- **Name:** `get_platform_settings`
- **View:** `views.settings_api.get_platform_settings`
- **Auth:** **Required**
- **Method:** GET
- **Payload:** None
- **Response:** JSON with platform settings
- **Status:** ✅ Active

### GET /api/profile/data/
- **Name:** `get_profile_data`
- **View:** `views.settings_api.get_profile_data`
- **Auth:** **Required**
- **Method:** GET
- **Payload:** None
- **Response:** JSON with profile data
- **Status:** ✅ Active

---

## 3. Game Passport API (JSON Responses)

### POST /api/passports/create/
- **Name:** `passport_create`
- **View:** `views.passport_create.create_passport`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):**
  ```json
  {
    "game_id": number (required),
    "ign": string (required),
    "discriminator": string (optional),
    "platform": string (optional),
    "region": string (optional),
    "metadata": {
      "rank": string (optional),
      "current_rank": string (optional),
      "peak_rank": string (optional),
      "display_name": string (optional),
      "playstyle": string (optional)
    }
  }
  ```
- **Response:** JSON `{success: bool, passport: object, error?: string}`
- **Service:** Uses `GamePassportService.create_passport()`
- **Status:** ✅ Active

### POST /api/passports/toggle-lft/
- **Name:** `passport_toggle_lft`
- **View:** `views.passport_api.toggle_lft`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):**
  - `passport_id` (number, required)
- **Response:** JSON `{success: bool, looking_for_team: bool, error?: string}`
- **Status:** ✅ Active

### POST /api/passports/set-visibility/
- **Name:** `passport_set_visibility`
- **View:** `views.passport_api.set_visibility`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):**
  - `passport_id` (number, required)
  - `visibility` (string: 'public'|'private'|'friends', required)
- **Response:** JSON `{success: bool, visibility: string, error?: string}`
- **Status:** ✅ Active

### POST /api/passports/pin/
- **Name:** `passport_pin`
- **View:** `views.passport_api.pin_passport`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):**
  - `passport_id` (number, required)
- **Response:** JSON `{success: bool, is_pinned: bool, error?: string}`
- **Status:** ✅ Active

### POST /api/passports/reorder/
- **Name:** `passport_reorder`
- **View:** `views.passport_api.reorder_passports`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):**
  - `order` (array of passport IDs, required)
- **Response:** JSON `{success: bool, error?: string}`
- **Status:** ✅ Active

### DELETE /api/passports/<int:passport_id>/delete/
- **Name:** `passport_delete`
- **View:** `views.passport_api.delete_passport`
- **Auth:** **Required**
- **Method:** DELETE
- **Payload:** None (passport_id in URL)
- **Response:** JSON `{success: bool, error?: string}`
- **Status:** ✅ Active

---

## 4. Legacy Endpoints (Mixed Status)

### POST /actions/save-game-profiles/
- **Name:** `save_game_profiles`
- **View:** `views.save_game_profiles`
- **Auth:** **Required**
- **Method:** POST
- **Payload:** Game profiles JSON
- **Response:** HTML redirect or JSON
- **Status:** ⚠️ **LEGACY** (use `/api/passports/create/` instead)
- **Issue:** Uses old JSON field, not structured GameProfile model

### POST /actions/update-bio/
- **Name:** `update_bio`
- **View:** `views.update_bio`
- **Auth:** **Required**
- **Method:** POST
- **Payload:** `bio` field
- **Response:** Redirect
- **Status:** ⚠️ **LEGACY** (use `/me/settings/basic/` instead)

### POST /actions/add-social-link/
- **Name:** `add_social_link`
- **View:** `views.add_social_link`
- **Auth:** **Required**
- **Method:** POST
- **Payload:** Social link data
- **Response:** Redirect
- **Status:** ⚠️ **LEGACY** (use `/me/settings/social/` instead)

### POST /actions/add-game-profile/
- **Name:** `add_game_profile`
- **View:** `views.add_game_profile`
- **Auth:** **Required**
- **Method:** POST
- **Payload:** Game profile data
- **Response:** Redirect
- **Status:** ⚠️ **LEGACY** (use `/api/passports/create/` instead)

### POST /actions/edit-game-profile/<int:profile_id>/
- **Name:** `edit_game_profile`
- **View:** `views.edit_game_profile`
- **Auth:** **Required**
- **Method:** POST
- **Payload:** Game profile updates
- **Response:** Redirect
- **Status:** ⚠️ **LEGACY** (no V2 equivalent - needs implementation)

### DELETE /actions/delete-game-profile/<int:profile_id>/
- **Name:** `delete_game_profile`
- **View:** `views.delete_game_profile`
- **Auth:** **Required**
- **Method:** DELETE
- **Payload:** None
- **Response:** Redirect
- **Status:** ⚠️ **LEGACY** (use `/api/passports/<id>/delete/` instead)

### POST /actions/follow/<str:username>/
- **Name:** `follow_user`
- **View:** `views.follow_user`
- **Auth:** **Required**
- **Method:** POST
- **Payload:** None (username in URL)
- **Response:** Redirect
- **Status:** ⚠️ **LEGACY** (use `/actions/follow-safe/<username>/` instead)

### POST /actions/unfollow/<str:username>/
- **Name:** `unfollow_user`
- **View:** `views.unfollow_user`
- **Auth:** **Required**
- **Method:** POST
- **Payload:** None
- **Response:** Redirect
- **Status:** ⚠️ **LEGACY** (use `/actions/unfollow-safe/<username>/` instead)

---

## 5. Safe Mutation Endpoints (Recommended)

### POST /actions/privacy-settings/save/
- **Name:** `privacy_settings_save_safe`
- **View:** `views.privacy_settings_save_safe`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):** Privacy settings
- **Response:** JSON with audit trail
- **Status:** ✅ Active (safe version)

### POST /actions/follow-safe/<str:username>/
- **Name:** `follow_user_safe`
- **View:** `views.follow_user_safe`
- **Auth:** **Required**
- **Method:** POST
- **Payload:** None
- **Response:** JSON with audit
- **Status:** ✅ Active (safe version)

### POST /actions/unfollow-safe/<str:username>/
- **Name:** `unfollow_user_safe`
- **View:** `views.unfollow_user_safe`
- **Auth:** **Required**
- **Method:** POST
- **Payload:** None
- **Response:** JSON with audit
- **Status:** ✅ Active (safe version)

### POST /actions/game-profiles/save/
- **Name:** `save_game_profiles_safe`
- **View:** `views.save_game_profiles_safe`
- **Auth:** **Required**
- **Method:** POST
- **Payload (JSON):** Batch game profiles
- **Response:** JSON with validation + audit
- **Status:** ✅ Active (safe version)

---

## 6. Utility & Admin Endpoints

### GET /me/edit/
- **Name:** `edit`
- **View:** `MyProfileUpdateView.as_view()`
- **Auth:** **Required**
- **Method:** GET/POST
- **Response:** HTML form (Django Class-Based View)
- **Status:** ⚠️ **LEGACY** (use `/me/settings/` instead)

### GET /me/tournaments/
- **Name:** `my_tournaments`
- **View:** `views.my_tournaments_view`
- **Auth:** **Required**
- **Method:** GET
- **Response:** HTML
- **Status:** ✅ Active

### POST /me/kyc/upload/
- **Name:** `kyc_upload`
- **View:** `views.kyc_upload_view`
- **Auth:** **Required**
- **Method:** POST
- **Payload:** KYC documents
- **Response:** Redirect
- **Status:** ✅ Active

### GET /me/kyc/status/
- **Name:** `kyc_status`
- **View:** `views.kyc_status_view`
- **Auth:** **Required**
- **Method:** GET
- **Response:** HTML
- **Status:** ✅ Active

### GET /@<username>/followers/
- **Name:** `followers_list`
- **View:** `views.followers_list`
- **Auth:** Optional
- **Method:** GET
- **Response:** HTML
- **Status:** ✅ Active

### GET /@<username>/following/
- **Name:** `following_list`
- **View:** `views.following_list`
- **Auth:** Optional
- **Method:** GET
- **Response:** HTML
- **Status:** ✅ Active

---

## 7. Redirects (301 Permanent)

### GET /u/<username>/
- **Name:** `public_profile`
- **Redirect:** → `/@<username>/`
- **Status:** ✅ Active (redirect only)

### GET /<username>/
- **Name:** `profile_legacy`
- **Redirect:** → `/@<username>/`
- **Status:** ✅ Active (redirect only)

### GET /api/profile/get-game-id/
- **Name:** `get_game_id_legacy`
- **Redirect:** → `/api/profile/game-ids/`
- **Status:** ✅ Active (redirect only)

---

## Issues & Duplications Identified

### 1. Duplicate Social Links Endpoints ⚠️

**Problem:** Two endpoints for same functionality
- `/me/settings/social/` (FormData)
- `/api/social-links/update/` (JSON)

**Recommendation:** Standardize on `/me/settings/social/` and deprecate `/api/social-links/update/`

### 2. Legacy Game Profile Endpoints Still Mounted ⚠️

**Problem:** Old endpoints still active but unmaintained
- `/actions/add-game-profile/` → Should use `/api/passports/create/`
- `/actions/edit-game-profile/<id>/` → No V2 equivalent (needs implementation)
- `/actions/delete-game-profile/<id>/` → Should use `/api/passports/<id>/delete/`

**Recommendation:** Add deprecation warnings or remove from urls.py

### 3. Follow System Has Old + Safe Versions ⚠️

**Problem:** Confusion between legacy and safe endpoints
- `/actions/follow/<username>/` (legacy, returns redirect)
- `/actions/follow-safe/<username>/` (safe, returns JSON)

**Recommendation:** Frontend should use `-safe` versions only

### 4. Missing Edit Passport Endpoint ❌

**Problem:** No API endpoint to **edit** existing passports
- Can create: `/api/passports/create/`
- Can delete: `/api/passports/<id>/delete/`
- **Cannot edit:** Missing endpoint

**Recommendation:** Add `PATCH /api/passports/<id>/update/` endpoint

### 5. Game ID API Inconsistency ⚠️

**Problem:** Multiple overlapping endpoints
- `/api/profile/update-game-id/` (legacy wrapper)
- `/api/profile/update-game-id-safe/` (safe version)
- `/api/profile/save-game-id/<game_code>/` (new style)

**Recommendation:** Deprecate old versions, use new style

---

## Canonical Endpoints Summary

**For Frontend Integration (Use These):**

**Profile Pages:**
- `GET /@<username>/` - Public profile
- `GET /@<username>/activity/` - Activity feed
- `GET /me/settings/` - Settings page
- `GET /me/privacy/` - Privacy page

**Settings Mutations:**
- `POST /me/settings/basic/` - Update basic info
- `POST /me/settings/social/` - Update social links
- `POST /me/settings/media/` - Upload avatar/banner
- `POST /me/settings/media/remove/` - Remove media
- `POST /me/settings/privacy/save/` - Save privacy settings
- `GET /me/settings/privacy/` - Get privacy settings

**Game Passports:**
- `POST /api/passports/create/` - Create passport
- `POST /api/passports/toggle-lft/` - Toggle LFT
- `POST /api/passports/set-visibility/` - Set visibility
- `POST /api/passports/pin/` - Pin passport
- `POST /api/passports/reorder/` - Reorder passports
- `DELETE /api/passports/<id>/delete/` - Delete passport
- **Missing:** `PATCH /api/passports/<id>/update/` - Edit passport ❌

**Follow System:**
- `POST /actions/follow-safe/<username>/` - Follow user
- `POST /actions/unfollow-safe/<username>/` - Unfollow user

---

## Response Type Consistency

### HTML Responses (Templates)
- All `GET` profile/settings/privacy pages
- Legacy `/me/edit/`, `/me/tournaments/`

### JSON Responses (API)
- All `/me/settings/*` POST mutations
- All `/api/passports/*` endpoints
- All `/actions/*-safe/` endpoints

### Redirects
- All legacy routes (`/u/<username>/`, `/<username>/`)
- Some legacy mutation endpoints (should be deprecated)

---

## Authentication Matrix

| Route Pattern | Auth Required | Redirect on Failure |
|---------------|---------------|---------------------|
| `/@<username>/` | Optional | N/A |
| `/me/*` | **Required** | Yes → `/accounts/login/` |
| `/api/passports/*` | **Required** | 403 JSON |
| `/actions/*` | **Required** | Varies (legacy: redirect, safe: JSON) |

---

**Generated:** December 28, 2025  
**Total Routes Audited:** 53  
**Canonical API Endpoints:** 18  
**Legacy Endpoints:** 12  
**Issues Identified:** 5 major
