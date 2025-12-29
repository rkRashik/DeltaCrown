# UP_PHASE5_FRONTEND_WIRING.md

**Phase:** 5A - Deep System Audit  
**Date:** December 28, 2025  
**Status:** 🔍 **FRONTEND ANALYSIS COMPLETE**

---

## 🎯 MISSION

Audit all frontend template/JS files to identify:
1. What data templates expect vs. what backend provides
2. Where updates are not reflecting
3. Missing bindings / stale state / broken assumptions
4. Why frontend ↔ backend sync is broken

---

## 📂 FILE INVENTORY

### **Templates**

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `profile.html` | 338 | Public profile page | ⚠️ Issues found |
| `settings.html` | 1,994 | Settings management | ⚠️ Issues found |
| `_passport_modal.html` | 350 | Passport creation modal | ✅ Working (Phase 4A fix) |

### **JavaScript**

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `profile.js` | 576 | Profile interactions | ✅ Working (Phase 3A) |
| `settings.js` | 383 | Settings interactions | ✅ Fixed (Phase 4A) |

---

## 🚨 CRITICAL ISSUE #1: STATIC FOLLOW BUTTON

### **Location:** `profile.html:64-77`

**Problem:** Follow button uses **Alpine.js local state** instead of real backend calls.

```django-html
x-data="{
    isFollowing: {{ is_following|yesno:"true,false" }},
    followLoading: false,
    ...
    toggleFollow() {
        if (this.followLoading) return;
        this.followLoading = true;
        // Simulate async request
        setTimeout(() => {
            this.isFollowing = !this.isFollowing;
            this.showToast(this.isFollowing ? 'Followed' : 'Unfollowed', ...);
            this.followLoading = false;
        }, 650);
        // TODO: Replace with real AJAX POST to follow/unfollow endpoint  ❌
    }
}
```

**Impact:**  
- Follow button LOOKS like it works (optimistic UI)
- But **NO backend request** is sent
- Refresh page → follow state reverts
- Database never updated

**Evidence:**
- Line 65-66: `setTimeout()` fake async (no `fetch()`)
- Line 72: TODO comment admits it's not wired
- `profile.js:266` has `window.followUser()` but template doesn't call it

**Fix Required:**
```javascript
toggleFollow() {
    if (this.followLoading) return;
    this.followLoading = true;
    
    const username = '{{ profile_user.username }}';
    const apiCall = this.isFollowing 
        ? window.unfollowUser(username) 
        : window.followUser(username);
    
    apiCall
        .then(() => {
            this.isFollowing = !this.isFollowing;
            this.showToast(this.isFollowing ? 'Followed' : 'Unfollowed');
        })
        .catch(() => {
            this.showToast('Failed to update', '❌');
        })
        .finally(() => {
            this.followLoading = false;
        });
}
```

---

## ⚠️ ISSUE #2: PROFILE PAGE VIEWER ROLE ADAPTATION

### **Location:** `profile.html` (entire file)

**Problem:** Template has **ZERO privacy/role checks** except `is_own_profile`.

**Template Conditionals:**
```django-html
{% if is_own_profile %}
    <!-- Owner sees: Settings button + Share button -->
{% else %}
    <!-- Visitor sees: Follow + Message + Share buttons -->
{% endif %}
```

**Missing Checks:**
- ❌ No `{% if profile.is_private %}` checks
- ❌ No follower-only content sections
- ❌ No privacy-aware wallet blurring
- ❌ No conditional game passport visibility
- ❌ No "This profile is private" message

**Example:** Line 80-85 shows banner/avatar with NO privacy check:
```django-html
{% if profile.banner %}
<img src="{{ profile.banner.url }}" ...>
{% else %}
<div class="...gradient..."></div>
{% endif %}
```

**Should Be:**
```django-html
{% if can_view_banner %}  <!-- Backend should compute this -->
    {% if profile.banner %}
    <img src="{{ profile.banner.url }}" ...>
    {% else %}
    <div class="...gradient..."></div>
    {% endif %}
{% else %}
    <div class="locked-content">🔒 Private Profile</div>
{% endif %}
```

**Root Cause:** Backend views don't pass `can_view_*` permissions to template context.

---

## ⚠️ ISSUE #3: SETTINGS PAGE DATA LOADING

### **Location:** `settings.html:1-1994`

**Problem:** Settings page is **1,994 lines of static HTML** with NO data binding.

**Evidence:**
```django-html
<input type="text" 
       id="display_name" 
       name="display_name" 
       class="form-input" 
       value="{{ profile.display_name }}"  ← Static Django template
       placeholder="Your public display name">
```

**Issues:**
1. **No real-time validation** - JS validates on blur/submit, but backend errors not shown
2. **No unsaved changes indicator works** - `settings.js:296-328` tries to detect dirty state, but form reloads wipe state
3. **No success feedback beyond toast** - User must check profile page to verify changes
4. **Social links conflict** - Form writes to UserProfile fields, but SocialLink model exists

**Settings Form Endpoints Called:**
| Form ID | JavaScript Function | Backend Endpoint | Status |
|---------|---------------------|------------------|--------|
| basicInfoForm | `saveBasicInfo()` | `/me/settings/basic/` | ✅ Fixed (Phase 4A) |
| socialLinksForm | `saveSocialLinks()` | `/me/settings/social/` | ✅ Fixed (Phase 4A) |
| (Media upload) | `uploadMedia()` | `/me/settings/media/` | ✅ Working |
| (Privacy toggles) | `savePrivacySettings()` | `/me/settings/privacy/save/` | ✅ Working |

**Improvement Needed:**  
Settings page should use **Alpine.js reactive state** or **Vue/React** instead of jQuery-style form handling.

---

## 🔍 ISSUE #4: PRIVACY SETTINGS UI ↔ BACKEND MISMATCH

### **Location:** `settings.html` Privacy Section

**Problem:** Settings UI might show legacy UserProfile fields instead of PrivacySettings model.

**Backend Reality:**
- `PrivacySettings` model is canonical (15 fields)
- `UserProfile` has 9 legacy fields (should be removed)

**Settings UI:**
Need to verify which fields are shown in settings form:
```django-html
<!-- Are these in settings.html? -->
<input name="is_private" ...>  ← Legacy (should NOT exist)
<input name="show_email" ...>  ← Duplicate?
<input name="profile_visibility" ...>  ← New (should exist)
```

**Action Required:** Audit settings.html line-by-line to confirm privacy form matches PrivacySettings model, not legacy fields.

---

## ✅ VERIFIED WORKING: PROFILE.JS

### **API Calls (Phase 3A Implementation)**

| Function | Endpoint | Status | Evidence |
|----------|----------|--------|----------|
| `createPassport()` | `/api/passports/create/` | ✅ | Line 42, JSON body |
| `togglePassportLFT()` | `/api/passports/toggle-lft/` | ✅ | Line 50, JSON body |
| `pinPassport()` | `/api/passports/pin/` | ✅ | Line 66, JSON body |
| `deletePassport()` | `/api/passports/<id>/delete/` | ✅ | Line 74, POST |
| `followUser()` | `/actions/follow-safe/<username>/` | ✅ | Line 90, POST |
| `unfollowUser()` | `/actions/unfollow-safe/<username>/` | ✅ | Line 96, POST |

**Optimistic UI Rollback:** ✅ Implemented (Lines 147-180, 182-217, 266-300, 302-338)

**Global Functions:** All passport/follow functions exposed via `window.*` for template access.

---

## ✅ VERIFIED WORKING: SETTINGS.JS

### **API Calls (Phase 4A Fix Applied)**

| Function | Endpoint | Content-Type | Status |
|----------|----------|--------------|--------|
| `saveBasicInfo()` | `/me/settings/basic/` | `application/json` | ✅ Fixed |
| `saveSocialLinks()` | `/me/settings/social/` | `application/json` | ✅ Fixed |
| `uploadMedia()` | `/me/settings/media/` | `multipart/form-data` | ✅ Working |
| `removeMedia()` | `/me/settings/media/remove/` | `application/json` | ✅ Working |
| `savePrivacySettings()` | `/me/settings/privacy/save/` | `application/json` | ✅ Working |

**CSRF Protection:** ✅ All requests include `X-CSRFToken` header (Line 12)

**Error Handling:** ✅ Try-catch with toast notifications (Lines 26-34)

---

## 🔍 ISSUE #5: PROFILE CONTEXT FROM BACKEND

### **What Templates Expect:**

`profile.html` expects these context variables:

| Variable | Type | Used For | Passed by Backend? |
|----------|------|----------|-------------------|
| `profile` | UserProfile | Display data | ✅ Yes |
| `profile_user` | User | Username, auth | ✅ Yes |
| `is_own_profile` | Bool | Owner detection | ✅ Yes |
| `is_following` | Bool | Follow button state | ✅ Yes |
| `current_teams` | QuerySet | Team badges | ✅ Yes |
| `game_profiles` | QuerySet | Passport cards | ✅ Yes |

**Missing Privacy Permissions:**

| Variable | Purpose | Status |
|----------|---------|--------|
| `can_view_profile` | Private profile check | ❌ NOT PASSED |
| `can_view_game_passports` | Passport visibility | ❌ NOT PASSED |
| `can_view_achievements` | Achievement visibility | ❌ NOT PASSED |
| `can_view_match_history` | Match privacy | ❌ NOT PASSED |
| `can_send_message` | DM permissions | ❌ NOT PASSED |
| `can_view_wallet` | Economy visibility | ❌ NOT PASSED |

**Root Cause:** Backend view (likely `profile_view_v2` in `fe_v2.py`) doesn't compute privacy permissions.

**Required Fix:** Use `ProfileContextService` or build permission dict in view.

---

## 🔍 ISSUE #6: WALLET VISIBILITY BROKEN

### **Location:** `profile.html` (wallet section)

**Current Behavior:**
```django-html
<div x-data="{ walletBlurred: true }">
    <!-- Wallet always starts blurred on page load -->
    <!-- Toggle button switches local Alpine state -->
    <!-- NO backend privacy check -->
</div>
```

**Problems:**
1. **Wallet is ALWAYS visible in HTML** (just CSS blurred)
2. **No server-side privacy enforcement** - Inspect element → see balance
3. **No PrivacySettings.show_wallet_balance check**

**Should Be:**
```django-html
{% if can_view_wallet %}
    <div x-data="{ walletBlurred: {{ is_own_profile|yesno:'false,true' }} }">
        <!-- Wallet data -->
    </div>
{% else %}
    <div class="locked">🔒 Wallet Private</div>
{% endif %}
```

---

## 🔍 ISSUE #7: STREAM STATUS INDICATOR

### **Location:** `profile.html:105-120`

**Feature:** Live streaming indicator (red "LIVE" badge)

**Status:** 🔴 **NON-FUNCTIONAL**

**Evidence:**
```django-html
{% if profile.stream_status %}
<div class="...animate-pulse...">🔴 LIVE</div>
{% endif %}
```

**Backend Field:** `UserProfile.stream_status` (BooleanField, default=False)

**Problem:**
- Field exists but NO automation
- No Twitch/YouTube API integration
- Must be manually toggled in admin
- Comment says "Automatically indicates if user is currently live" ← LIE

**Decision Required:**
- **Option A:** Remove feature (not implemented)
- **Option B:** Implement Twitch/YouTube webhooks (Phase 6)

**Recommendation:** Remove from UI until webhooks implemented.

---

## 🔍 ISSUE #8: SOCIAL LINKS RENDERING

### **Location:** `profile.html` (social links section - not in excerpt)

**Backend Conflict:**  
UserProfile has direct fields (`youtube_link`, `twitch_link`, etc.) but SocialLink model also exists.

**Template Likely Does:**
```django-html
{% if profile.youtube_link %}
<a href="{{ profile.youtube_link }}">YouTube</a>
{% endif %}
{% if profile.twitch_link %}
<a href="{{ profile.twitch_link }}">Twitch</a>
{% endif %}
<!-- etc. -->
```

**Issues:**
1. **Hardcoded platforms** - Can't add custom links
2. **Direct field access** - Ignores SocialLink model
3. **No verification badges** - SocialLink has `is_verified` field (unused)

**Decision from Backend Audit:** Keep UserProfile fields, delete SocialLink model.

**Template Fix Required:** Ensure template reads from UserProfile fields only.

---

## 🔍 ISSUE #9: GAME PASSPORT CARDS

### **Location:** `profile.html` (passport section - not in excerpt)

**Backend Status:** GameProfile model is canonical (GP-2A).

**Template Should Show:**
- Game icon/logo
- `in_game_name` (computed display name)
- `rank_name` (if set)
- `main_role` (if set)
- LFT badge (if `is_lft` = True)
- Pin indicator (if `is_primary` = True)
- Verified badge (if `is_verified` = True)

**Privacy Enforcement:**
```django-html
{% for passport in game_profiles %}
    {% if passport.visibility == 'PUBLIC' or can_view_passports %}
        <!-- Show passport card -->
    {% else %}
        <!-- Skip or show locked -->
    {% endif %}
{% endfor %}
```

**Current State:** Need to verify if visibility is checked.

---

## 🔍 ISSUE #10: ACHIEVEMENTS & BADGES

### **Location:** `profile.html` (achievements section - not in excerpt)

**Models:**
- `Badge` (system-defined achievements)
- `UserBadge` (user ↔ badge junction)
- `Achievement` (user-specific achievements?)

**Confusion:** Backend audit found both Badge and Achievement models. What's the difference?

**Template Should Show:**
```django-html
{% for user_badge in profile.userbadge_set.all %}
    <div class="badge">
        {{ user_badge.badge.emoji }} {{ user_badge.badge.name }}
    </div>
{% endfor %}
```

**Privacy:** Should respect `PrivacySettings.show_achievements`.

---

## 📊 DATA FLOW ANALYSIS

### **Settings → Profile Data Flow**

| Step | System | Status | Evidence |
|------|--------|--------|----------|
| 1. User edits display_name | Settings form | ✅ | Input field exists |
| 2. Form submits JSON | `settings.js` | ✅ | Phase 4A fix |
| 3. Backend saves to DB | `/me/settings/basic/` | ✅ | fe_v2.py:411 |
| 4. Backend returns success | JSON response | ✅ | Line 567-572 |
| 5. Frontend shows toast | Toast notification | ✅ | settings.js:33 |
| 6. **Profile page updates?** | **???** | ❌ **UNKNOWN** | **NO SYNC MECHANISM** |

**Missing Link:** Settings save does NOT trigger profile page refresh or real-time update.

**User Experience:**
1. User changes name in settings
2. Toast says "Success!"
3. User clicks profile link
4. **Name is updated** ✅ (because profile page queries DB fresh)

**BUT:**  
If profile page is open in another tab → **stale data until manual refresh**.

**Solution Options:**
- **Option A:** Add "View Profile" button after save (redirects to profile)
- **Option B:** Implement WebSocket/SSE for real-time updates (overkill)
- **Option C:** Settings page shows live preview of profile (complex)

**Recommendation:** Option A (simple, effective).

---

## 🔍 ISSUE #11: FOLLOW COUNTS NOT LIVE

### **Location:** `profile.html` Followers/Following display

**Current State:**
```django-html
<div>{{ follower_count }} Followers</div>
<div>{{ following_count }} Following</div>
```

**Problem:**
- Counts are static (rendered server-side)
- Follow/unfollow actions don't update counts in UI
- `profile.js:followUser()` has optimistic UI but no count update

**Fix Required:**
```javascript
window.followUser = async function(username) {
    // Existing optimistic UI...
    const result = await followUser(username);
    
    // Update follower count
    const followerCountEl = document.querySelector('.follower-count');
    if (followerCountEl) {
        const current = parseInt(followerCountEl.textContent);
        followerCountEl.textContent = current + 1;
    }
};
```

---

## 📋 TEMPLATE CONTEXT REQUIREMENTS

### **profile_view_v2 Should Pass:**

```python
context = {
    # Identity
    'profile': profile,
    'profile_user': user,
    'is_own_profile': request.user == user,
    
    # Social
    'is_following': FollowService.is_following(request.user, user),
    'follower_count': profile.follower_count,
    'following_count': profile.following_count,
    
    # Content
    'game_profiles': GameProfile.objects.filter(user=user, status='ACTIVE'),
    'current_teams': user.active_teams(),
    'achievements': user.achievements.all(),
    'certificates': user.certificates.all(),
    
    # Privacy Permissions (MISSING!)
    'can_view_profile': privacy_checker.can_view_profile(),
    'can_view_game_passports': privacy_checker.can_view_passports(),
    'can_view_achievements': privacy_checker.can_view_achievements(),
    'can_view_match_history': privacy_checker.can_view_matches(),
    'can_view_wallet': privacy_checker.can_view_wallet(),
    'can_send_message': privacy_checker.can_send_dm(),
    
    # Viewer role (for analytics/tracking)
    'viewer_role': 'owner' | 'follower' | 'visitor' | 'anonymous',
}
```

---

## 🎯 SUMMARY OF ISSUES

| # | Issue | Severity | Blocking? | Fix Complexity |
|---|-------|----------|-----------|----------------|
| 1 | Follow button not wired | 🔴 CRITICAL | ✅ YES | Easy |
| 2 | No privacy role checks | 🔴 CRITICAL | ✅ YES | Medium |
| 3 | Settings 1,994 lines static HTML | 🟡 HIGH | ❌ NO | Hard |
| 4 | Privacy UI/backend mismatch | 🟡 HIGH | ⚠️ MAYBE | Medium |
| 5 | Missing permission context vars | 🔴 CRITICAL | ✅ YES | Medium |
| 6 | Wallet visibility broken | 🟡 HIGH | ⚠️ MAYBE | Easy |
| 7 | Stream status non-functional | 🟢 LOW | ❌ NO | Hard (webhooks) |
| 8 | Social links conflict | 🟡 HIGH | ❌ NO | Easy |
| 9 | Game passport privacy unclear | 🟡 HIGH | ⚠️ MAYBE | Easy |
| 10 | Achievement/Badge confusion | 🟢 LOW | ❌ NO | Medium |
| 11 | Follow counts not live | 🟡 HIGH | ❌ NO | Easy |

**Blocking Issues:** 3 (Follow button, Privacy checks, Permission context)

**Critical Path:** Fix Issues #1, #2, #5 before launch.

---

## 🔥 IMMEDIATE ACTIONS REQUIRED

### **Priority 1: Fix Follow Button (Issue #1)**
- Replace `setTimeout()` fake async with real `window.followUser()` call
- Test follow/unfollow persists after refresh

### **Priority 2: Add Privacy Context (Issue #5)**
- Build permission checker in backend view
- Pass `can_view_*` flags to template
- Wire privacy checks in template

### **Priority 3: Fix Profile View Adaptation (Issue #2)**
- Add `{% if can_view_profile %}` checks
- Show "Private Profile" message when locked
- Hide sensitive sections based on permissions

### **Priority 4: Update Follow Counts (Issue #11)**
- Update follower/following counts after follow action
- Make counts dynamic in UI

---

**Status:** Frontend wiring audit complete. Next: Admin panel audit.
