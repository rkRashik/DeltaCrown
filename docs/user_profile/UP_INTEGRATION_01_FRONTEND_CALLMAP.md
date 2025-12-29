# UP_INTEGRATION_01: Frontend Call Map

**Generated:** December 28, 2025  
**Purpose:** Audit all frontend JavaScript for API calls and match to backend truth table

---

## Executive Summary

**CRITICAL FINDING:** ⚠️ **Frontend Has ZERO API Integration**

After comprehensive audit of all user_profile JavaScript files:
- ✅ **settings.js** (161 lines): UI interactions only, NO fetch() calls
- ✅ **profile.js** (247 lines): Navigation/utilities only, NO fetch() calls
- ✅ No other JS files in `static/user_profile/js/`

**Status:** Frontend is 100% UI-only with placeholder form handlers and console.logs

---

## Detailed Audit

### 1. static/user_profile/js/settings.js

**Purpose:** Settings page UI interactions (UP-UI-REBIRTH-01)

**Functions:**
- `initSectionNav()` - Tab navigation with hash support
- `initToggleSwitches()` - Toggle UI state (NO persistence)
- `initFormValidation()` - Form validation + preventDefault (NO submission)
- `showToast()` - Toast notifications

**API Calls:** **NONE** ❌

**Placeholder Code Found:**
```javascript
// Line 72: Form submit handler
form.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    console.log('Form submitted:', Object.fromEntries(formData));
    
    // Simulate save
    showToast('Settings saved successfully!');
});
```

```javascript
// Line 63: Toggle handler
toggle.addEventListener('click', function() {
    this.classList.toggle('active');
    const setting = this.getAttribute('data-toggle');
    const isActive = this.classList.contains('active');
    
    console.log(`Toggle ${setting}: ${isActive}`);
    
    // Here you would make an AJAX call to save the setting
    // For now, just show a toast
    showToast(`Setting ${isActive ? 'enabled' : 'disabled'}`);
});
```

**Expected Backend Routes (Not Wired):**
- `POST /me/settings/basic/` - Should handle basic info form
- `POST /me/settings/social/` - Should handle social links form
- `POST /me/settings/media/` - Should handle avatar/banner upload
- `POST /me/settings/privacy/save/` - Should handle privacy toggles
- `GET /me/settings/privacy/` - Should load privacy settings on init

---

### 2. static/user_profile/js/profile.js

**Purpose:** Profile page UI interactions (UP-UI-REBIRTH-01)

**Functions:**
- `initDashboardNav()` - Scroll navigation with Intersection Observer
- `initCollapsible()` - Expand/collapse "More Games" section
- `handleUrlHash()` - Deep linking support
- `initKeyboardShortcuts()` - Alt+1-8 quick navigation
- `copyToClipboard()` - Global utility
- `shareProfile()` - Web Share API wrapper

**API Calls:** **NONE** ❌

**Expected Backend Routes (Not Wired):**
- `POST /actions/follow-safe/<username>/` - Should handle follow button
- `POST /actions/unfollow-safe/<username>/` - Should handle unfollow button
- `POST /api/passports/toggle-lft/` - Should handle "Looking for Team" toggle
- `POST /api/passports/pin/` - Should handle passport pinning
- `DELETE /api/passports/<id>/delete/` - Should handle passport deletion

---

## Template Analysis

### templates/user_profile/profile/settings.html

**Form Structure (Expected):**

```html
<!-- Basic Info Section -->
<form id="basicInfoForm" method="POST" action="{% url 'user_profile:update_basic_info' %}">
    {% csrf_token %}
    <input name="display_name" type="text" ...>
    <textarea name="bio" ...></textarea>
    <input name="pronouns" type="text" ...>
    <input name="country" type="text" ...>
    <input name="city" type="text" ...>
    <button type="submit">Save Changes</button>
</form>

<!-- Social Links Section -->
<form id="socialLinksForm" method="POST" action="{% url 'user_profile:update_social_links' %}">
    {% csrf_token %}
    <input name="youtube_link" type="url" ...>
    <input name="twitch_link" type="url" ...>
    <input name="discord_id" type="text" ...>
    <input name="twitter" type="text" ...>
    <input name="instagram" type="text" ...>
    <input name="facebook" type="url" ...>
    <input name="tiktok" type="text" ...>
    <button type="submit">Update Links</button>
</form>

<!-- Privacy Settings Section -->
<div class="toggle-switch" data-toggle="show_real_name">...</div>
<div class="toggle-switch" data-toggle="show_email">...</div>
<!-- ... more toggles ... -->

<!-- Media Upload Section -->
<form id="avatarUploadForm" method="POST" action="{% url 'user_profile:upload_media' %}" enctype="multipart/form-data">
    {% csrf_token %}
    <input type="hidden" name="media_type" value="avatar">
    <input type="file" name="file" accept="image/*">
    <button type="submit">Upload Avatar</button>
</form>
```

**Current State:** Forms likely exist but JS prevents submission with `e.preventDefault()`

---

### templates/user_profile/profile/public.html

**Interactive Elements (Expected):**

```html
<!-- Follow Button -->
<button onclick="followUser('{{ profile.username }}')">Follow</button>

<!-- Game Passports -->
<div class="passport-card" data-passport-id="{{ passport.id }}">
    <button onclick="toggleLFT({{ passport.id }})">Looking for Team</button>
    <button onclick="pinPassport({{ passport.id }})">Pin</button>
    <button onclick="deletePassport({{ passport.id }})">Delete</button>
</div>

<!-- Add Passport Button -->
<button onclick="openPassportModal()">Add Game Profile</button>
```

**Current State:** No `followUser()`, `toggleLFT()`, `pinPassport()`, `deletePassport()` functions exist

---

## Missing API Call Functions

To wire frontend → backend, these functions must be implemented:

### 1. Settings API Client

```javascript
// settings.js additions needed

async function apiFetch(url, options = {}) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    const config = {
        headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest',
            ...options.headers
        },
        credentials: 'same-origin',
        ...options
    };
    
    const response = await fetch(url, config);
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error || 'Request failed');
    }
    
    return data;
}

async function saveBasicInfo(formData) {
    return await apiFetch('/me/settings/basic/', {
        method: 'POST',
        body: formData
    });
}

async function saveSocialLinks(formData) {
    return await apiFetch('/me/settings/social/', {
        method: 'POST',
        body: formData
    });
}

async function uploadMedia(formData) {
    return await apiFetch('/me/settings/media/', {
        method: 'POST',
        body: formData
    });
}

async function removeMedia(mediaType) {
    return await apiFetch('/me/settings/media/remove/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_type: mediaType })
    });
}

async function getPrivacySettings() {
    return await apiFetch('/me/settings/privacy/', {
        method: 'GET'
    });
}

async function savePrivacySettings(settings) {
    return await apiFetch('/me/settings/privacy/save/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    });
}
```

### 2. Passport API Client

```javascript
// profile.js additions needed

async function createPassport(passportData) {
    return await apiFetch('/api/passports/create/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(passportData)
    });
}

async function togglePassportLFT(passportId) {
    return await apiFetch('/api/passports/toggle-lft/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ passport_id: passportId })
    });
}

async function setPassportVisibility(passportId, visibility) {
    return await apiFetch('/api/passports/set-visibility/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ passport_id: passportId, visibility })
    });
}

async function pinPassport(passportId) {
    return await apiFetch('/api/passports/pin/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ passport_id: passportId })
    });
}

async function deletePassport(passportId) {
    return await apiFetch(`/api/passports/${passportId}/delete/`, {
        method: 'DELETE'
    });
}

async function reorderPassports(order) {
    return await apiFetch('/api/passports/reorder/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order })
    });
}
```

### 3. Follow API Client

```javascript
// profile.js additions needed

async function followUser(username) {
    return await apiFetch(`/actions/follow-safe/${username}/`, {
        method: 'POST'
    });
}

async function unfollowUser(username) {
    return await apiFetch(`/actions/unfollow-safe/${username}/`, {
        method: 'POST'
    });
}
```

---

## Form Wiring Plan

### Basic Info Form

**Current:** `e.preventDefault()` → `console.log()` → fake toast  
**Target:** `e.preventDefault()` → `saveBasicInfo()` → real backend → toast with actual result

```javascript
// Replace initFormValidation() form submit handler
form.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const submitBtn = this.querySelector('button[type="submit"]');
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving...';
    
    try {
        const result = await saveBasicInfo(formData);
        showToast(result.message || 'Settings saved successfully!');
    } catch (error) {
        showToast(error.message || 'Failed to save settings', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Save Changes';
    }
});
```

### Privacy Toggles

**Current:** `classList.toggle('active')` → `console.log()` → fake toast  
**Target:** `classList.toggle('active')` → `savePrivacySettings()` → real backend → restore on failure

```javascript
// Replace initToggleSwitches() handler
toggle.addEventListener('click', async function() {
    const setting = this.getAttribute('data-toggle');
    const wasActive = this.classList.contains('active');
    const newValue = !wasActive;
    
    // Optimistic UI update
    this.classList.toggle('active');
    
    try {
        await savePrivacySettings({ [setting]: newValue });
        showToast(`Setting ${newValue ? 'enabled' : 'disabled'}`);
    } catch (error) {
        // Rollback on failure
        this.classList.toggle('active');
        showToast('Failed to update setting', 'error');
    }
});
```

### Media Upload

**Current:** No file upload wired  
**Target:** File input → `uploadMedia()` → preview + save

```javascript
// New handler for avatar/banner upload
const avatarInput = document.getElementById('avatarInput');
const bannerInput = document.getElementById('bannerInput');

async function handleMediaUpload(input, mediaType) {
    const file = input.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('media_type', mediaType);
    formData.append('file', file);
    
    try {
        const result = await uploadMedia(formData);
        
        // Update preview
        const previewImg = document.getElementById(`${mediaType}Preview`);
        previewImg.src = result.preview_url;
        
        showToast(`${mediaType} updated successfully!`);
    } catch (error) {
        showToast(error.message || 'Failed to upload image', 'error');
    }
}

avatarInput.addEventListener('change', () => handleMediaUpload(avatarInput, 'avatar'));
bannerInput.addEventListener('change', () => handleMediaUpload(bannerInput, 'banner'));
```

---

## Critical Gaps Identified

### 1. No apiFetch() Helper ❌
**Problem:** No centralized fetch wrapper with CSRF handling  
**Impact:** Every API call must manually handle CSRF tokens, error responses, auth failures  
**Fix Priority:** **HIGH** (implement first)

### 2. No Privacy Settings Loader ❌
**Problem:** Privacy toggles show default state, not user's actual settings  
**Impact:** User sees wrong toggle states, may accidentally toggle opposite of intent  
**Fix Priority:** **HIGH** (must load on page init)

### 3. No Form Error Handling ❌
**Problem:** Forms show success toast even if backend fails  
**Impact:** User thinks data saved but it didn't persist  
**Fix Priority:** **HIGH** (must check response.ok)

### 4. No Passport Modal Exists ❌
**Problem:** No UI to create/edit game passports  
**Impact:** Users cannot add game profiles from frontend  
**Fix Priority:** **CRITICAL** (must rebuild from scratch)

### 5. No Follow Button Handler ❌
**Problem:** Follow button does nothing  
**Impact:** Users cannot follow other players  
**Fix Priority:** **MEDIUM** (if follow feature is used)

### 6. No Passport Actions Wired ❌
**Problem:** LFT toggle, Pin, Delete buttons do nothing  
**Impact:** Users cannot manage their passports  
**Fix Priority:** **HIGH** (core feature)

---

## Wiring Checklist

### Phase C: Core API Integration

- [ ] **C1:** Add `apiFetch()` helper to both settings.js and profile.js
- [ ] **C2:** Wire Basic Info form to `POST /me/settings/basic/`
- [ ] **C3:** Wire Social Links form to `POST /me/settings/social/`
- [ ] **C4:** Wire Avatar upload to `POST /me/settings/media/`
- [ ] **C5:** Wire Banner upload to `POST /me/settings/media/`
- [ ] **C6:** Add Privacy Settings loader on page init (`GET /me/settings/privacy/`)
- [ ] **C7:** Wire Privacy toggles to `POST /me/settings/privacy/save/`
- [ ] **C8:** Wire Follow button to `POST /actions/follow-safe/<username>/`
- [ ] **C9:** Wire Unfollow button to `POST /actions/unfollow-safe/<username>/`
- [ ] **C10:** Wire LFT toggle to `POST /api/passports/toggle-lft/`
- [ ] **C11:** Wire Pin passport to `POST /api/passports/pin/`
- [ ] **C12:** Wire Delete passport to `DELETE /api/passports/<id>/delete/`

### Phase D: Passport Modal Rebuild

- [ ] **D1:** Create passport creation modal UI
- [ ] **D2:** Load games list from `/api/games/` (TODO: verify endpoint exists)
- [ ] **D3:** Show game-specific fields (IGN, discriminator, platform, region, rank)
- [ ] **D4:** Wire modal submit to `POST /api/passports/create/`
- [ ] **D5:** Refresh passport list after creation
- [ ] **D6:** Add passport edit modal (requires new backend endpoint)

### Phase E: Social Links Redesign

- [ ] **E1:** Remove Facebook, Instagram, TikTok from UI
- [ ] **E2:** Keep only: YouTube, Twitch, Discord, Twitter
- [ ] **E3:** Update form to match backend `/me/settings/social/` payload
- [ ] **E4:** Add validation for URLs vs usernames

### Phase F: Privacy Settings Polish

- [ ] **F1:** Add privacy presets (Public, Friends Only, Private)
- [ ] **F2:** Group toggles into logical sections
- [ ] **F3:** Add descriptions for each setting
- [ ] **F4:** Ensure persistence (load on init, save on change)

---

## Backend → Frontend Response Mapping

### Success Response Pattern
```json
{
  "success": true,
  "message": "Settings saved successfully",
  "data": { ... }
}
```

### Error Response Pattern
```json
{
  "success": false,
  "error": "Invalid input",
  "details": { "field": "bio", "issue": "Too long" }
}
```

### Frontend Handling
```javascript
if (result.success) {
    showToast(result.message || 'Success!');
    // Update UI with result.data if needed
} else {
    showToast(result.error || 'Operation failed', 'error');
    // Show field-specific errors if result.details exists
}
```

---

## Security Considerations

### CSRF Protection
- ✅ All POST/PUT/PATCH/DELETE must include `X-CSRFToken` header
- ✅ Token must be read from hidden input or cookie
- ✅ Use `credentials: 'same-origin'` in fetch config

### Input Validation
- ⚠️ Frontend must validate before sending (save bandwidth)
- ✅ Backend must validate again (never trust client)
- ✅ Show specific error messages for validation failures

### File Upload Security
- ✅ Check file size before upload (5MB avatar, 10MB banner)
- ✅ Check file type (JPEG, PNG, WebP only)
- ✅ Show preview before sending to backend
- ✅ Backend validates again (PIL check for valid images)

---

## Summary

**Total API Calls Found:** 0 / ~20 expected  
**Wiring Completion:** 0%  
**Critical Blockers:** 6 identified  
**Estimated Effort:** 3-5 hours for full wiring

**Next Steps:**
1. Implement `apiFetch()` helper (30 min)
2. Wire all existing forms (1 hour)
3. Add privacy settings loader (30 min)
4. Wire passport actions (1 hour)
5. Build passport modal from scratch (2 hours)
6. Testing & polish (1 hour)

**Deliverable:** Working frontend that correctly reads/writes backend state with full persistence

---

**Generated:** December 28, 2025  
**Files Audited:** 2  
**API Calls Found:** 0  
**API Calls Needed:** 20+
