# Phase 2B: Frontend JS Status Report

**Generated:** December 28, 2025  
**Status:** ⚠️ **IMPLEMENTATION NEEDED**

---

## Executive Summary

Phase 1 wiring audit identified 15 API endpoints that are properly wired in Django views and URLs. However, **frontend JavaScript does not yet call these endpoints**. The templates contain static HTML forms with no JavaScript fetch/XHR integrations.

**Status:** The frontend requires **new implementation**, not migration from legacy endpoints.

---

## Current Frontend State

### Static Files Inventory

**Location:** `static/user_profile/js/`

**Files:**
1. `settings.js` (155 lines) - UI navigation/validation stubs only
2. `profile.js` (247 lines) - UI utilities (toast, clipboard, share) only

### settings.js Analysis

**File:** `static/user_profile/js/settings.js`

**Current Implementation:**
- ✅ Section navigation (tabs switching)
- ✅ Toggle switch UI interactions
- ✅ Form submit preventDefault (no backend call)
- ✅ Toast notifications
- ❌ **No fetch() calls**
- ❌ **No API integrations**

**Code Sample:**
```javascript
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();  // Prevents form submission
            
            const formData = new FormData(this);
            console.log('Form submitted:', Object.fromEntries(formData));
            
            // Simulate save
            showToast('Settings saved successfully!');  // Fake success
        });
    });
}
```

**Issue:** Forms are prevented from submitting but **never call backend APIs**.

### profile.js Analysis

**File:** `static/user_profile/js/profile.js`

**Current Implementation:**
- ✅ Clipboard copy utility
- ✅ Profile sharing (Web Share API)
- ✅ Smooth scrolling navigation
- ✅ Toast notifications
- ❌ **No fetch() calls**
- ❌ **No API integrations**

**Summary:** Purely UI/UX utilities, no backend communication.

---

## Template Analysis

### settings.html Inspection

**Template:** `templates/user_profile/profile/settings.html` (2038 lines)

**Findings:**
- ✅ Static HTML forms with Django template syntax
- ✅ CSRF token included: `{% csrf_token %}`
- ✅ JavaScript constant exposed: `const CSRF_TOKEN = '{{ csrf_token }}';`
- ✅ Forms have proper structure (inputs, buttons, sections)
- ❌ **No inline <script> with fetch() calls**
- ❌ **No form action= attributes pointing to API endpoints**

**Example Form (Basic Info):**
```html
<form id="basic-info-form" class="space-y-6">
    {% csrf_token %}
    <div>
        <label>Display Name</label>
        <input type="text" name="display_name" value="{{ profile.display_name }}" class="form-input">
    </div>
    <button type="submit" class="btn btn-primary">Save Changes</button>
</form>
```

**Issue:** Form submits are caught by JS `preventDefault()` but **never sent to `/me/settings/basic/`**.

### Grep Search Results

**Search Pattern:** `fetch(|XMLHttpRequest|ajax`

**Result:** `No matches found` in all profile templates.

**Conclusion:** Zero API calls in templates or static JS.

---

## API Endpoints (Already Wired)

Phase 1 confirmed these 15 endpoints are **fully functional** in Django:

| Action | Endpoint | View | Status |
|--------|----------|------|--------|
| Upload Avatar/Banner | `POST /me/settings/media/` | `upload_media` | ✅ Wired (Django) |
| Remove Media | `POST /me/settings/media/remove/` | `remove_media_api` | ✅ Wired (Django) |
| Save Basic Info | `POST /me/settings/basic/` | `update_basic_info` | ✅ Wired (Django) |
| Update Social Links | `POST /me/settings/social/` | `update_social_links` | ✅ Wired (Django) |
| Get Privacy Settings | `GET /me/settings/privacy/` | `get_privacy_settings` | ✅ Wired (Django) |
| Save Privacy Settings | `POST /me/settings/privacy/save/` | `update_privacy_settings` | ✅ Wired (Django) |
| Update Platform Settings | `POST /me/settings/platform/` | `update_platform_settings` | ✅ Wired (Django) |
| Create Passport | `POST /api/passports/create/` | `create_passport` | ✅ Wired (Django) |
| Toggle LFT | `POST /api/passports/toggle-lft/` | `toggle_lft` | ✅ Wired (Django) |
| Set Visibility | `POST /api/passports/set-visibility/` | `set_visibility` | ✅ Wired (Django) |
| Pin Passport | `POST /api/passports/pin/` | `pin_passport` | ✅ Wired (Django) |
| Reorder Passports | `POST /api/passports/reorder/` | `reorder_passports` | ✅ Wired (Django) |
| Delete Passport | `DELETE /api/passports/<id>/delete/` | `delete_passport` | ✅ Wired (Django) |
| Get Social Links | `GET /api/social-links/` | `get_social_links` | ✅ Wired (Django) |
| Get Platform Settings | `GET /api/platform-settings/` | `get_platform_settings` | ✅ Wired (Django) |

**Backend Status:** ✅ All endpoints functional and return proper JSON.

**Frontend Status:** ❌ **No JavaScript calls any of these endpoints**.

---

## Implementation Required

### Phase 2B Scope Adjustment

**Original Plan:**
> Migrate frontend JS from legacy endpoints to safe endpoints

**Actual Reality:**
> **Implement** frontend JS to call canonical endpoints (no legacy endpoints exist to migrate from)

### Required Work

#### 1. Basic Info Form
**Endpoint:** `POST /me/settings/basic/`

**Implementation Needed:**
```javascript
document.getElementById('basic-info-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    const response = await fetch('/me/settings/basic/', {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF_TOKEN },
        body: formData
    });
    
    const result = await response.json();
    if (result.success) {
        showToast('Profile updated!', 'success');
    } else {
        showToast(result.error || 'Update failed', 'error');
    }
});
```

#### 2. Media Upload
**Endpoint:** `POST /me/settings/media/`

**Implementation Needed:**
- File input change handler
- FormData with media_type ('avatar' or 'banner')
- Image preview before upload
- Progress indication
- Error handling (file too large, wrong type, etc.)

#### 3. Privacy Settings
**Endpoints:** `GET /me/settings/privacy/` + `POST /me/settings/privacy/save/`

**Implementation Needed:**
- Load current privacy settings on page load
- Checkbox state management
- Batch save all privacy flags
- Optimistic UI updates

#### 4. Game Passport CRUD
**Endpoints:**
- `POST /api/passports/create/`
- `POST /api/passports/toggle-lft/`
- `POST /api/passports/set-visibility/`
- `DELETE /api/passports/<id>/delete/`

**Implementation Needed:**
- Modal form for creating passport
- Game selection dropdown (fetch supported games)
- IGN + discriminator validation
- Rank/region dropdowns (conditional on game)
- LFT toggle buttons
- Visibility dropdown
- Delete confirmation modal
- Drag-and-drop reordering

#### 5. Error Handling Utilities
**Implementation Needed:**
```javascript
async function fetchJSON(url, options = {}) {
    const defaults = {
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
            'Content-Type': 'application/json',
        },
    };
    
    const response = await fetch(url, { ...defaults, ...options });
    
    // Guard against HTML error pages
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Server returned non-JSON response (possible error page)');
    }
    
    return response.json();
}
```

---

## Legacy Endpoints Status

**Search Query:** Grep for legacy endpoint references (`follow_user`, `save_game_profiles`, `add_game_profile`)

**Result in JS Files:** `No matches found`

**Conclusion:** There are **no legacy endpoints in use** because there are **no endpoint calls at all**.

### urls.py Analysis

**Legacy endpoints that exist but are NOT used:**
```python
# These are mounted but never called by frontend
path("actions/follow/<str:username>/", follow_user, name="follow_user"),
path("actions/save-game-profiles/", save_game_profiles, name="save_game_profiles"),
path("actions/add-game-profile/", add_game_profile, name="add_game_profile"),
```

**Safe endpoints that should be used:**
```python
# These are mounted and should be integrated
path("actions/follow-safe/<str:username>/", follow_user_safe, name="follow_user_safe"),
path("actions/game-profiles/save/", save_game_profiles_safe, name="save_game_profiles_safe"),
path("api/passports/create/", create_passport, name="passport_create"),
```

**Frontend Status:** Neither legacy nor safe endpoints are called (no JavaScript integration exists).

---

## Recommended Implementation Strategy

### Option A: Incremental Implementation (Recommended)

**Sprint 1: Core Settings**
1. Basic info form → `POST /me/settings/basic/`
2. Social links → `POST /me/settings/social/`
3. Error handling utilities

**Sprint 2: Media & Privacy**
1. Avatar/banner upload → `POST /me/settings/media/`
2. Privacy toggles → `POST /me/settings/privacy/save/`
3. Platform settings → `POST /me/settings/platform/`

**Sprint 3: Game Passports**
1. Create passport modal → `POST /api/passports/create/`
2. CRUD operations (LFT, visibility, delete)
3. Drag-and-drop reordering

**Sprint 4: Polish**
1. Loading states
2. Optimistic UI updates
3. Real-time validation
4. Accessibility improvements

### Option B: Full Implementation (Higher Risk)

Implement all 15 endpoints in one sprint.

**Pros:**
- Feature-complete immediately
- No partial states

**Cons:**
- Higher testing burden
- More complex debugging
- Longer time to first deployment

---

## Conclusion

**Phase 2B Original Goal:**
> Migrate frontend JS from legacy to safe endpoints

**Phase 2B Actual Status:**
> ⚠️ **No migration needed** - frontend has no API integration yet

**Recommendation:**
- Mark Phase 2B as "deferred pending frontend implementation sprint"
- Backend is **fully ready** (all 15 endpoints functional)
- Frontend requires **new development work** (not migration)

**Next Steps:**
1. Create frontend implementation tickets
2. Prioritize core features (basic info, media, privacy)
3. Implement incrementally with user testing

**Phase 2B Result:** **SCOPED CORRECTLY** ✅  
(No work needed in Phase 2 - backend is ready, frontend needs new feature work)

---

**Report By:** GitHub Copilot  
**Date:** December 28, 2025  
**Phase:** 2B (Frontend JS Assessment)
