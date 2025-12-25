# UP-FE-01: USER PROFILE FRONTEND AUDIT

**Project:** DeltaCrown User Profile — Frontend Cleanup  
**Phase:** Audit & Analysis (TEMPLATES-FIRST)  
**Date:** 2025-01-XX  
**Backend Status:** ✅ 100% Complete (6/6 missions verified, 80/80 tests passing)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Audit Scope
- **URLs:** [apps/user_profile/urls.py](apps/user_profile/urls.py) (100 lines, 15+ profile routes)
- **Views:** [apps/user_profile/views.py](apps/user_profile/views.py) (1116 lines, monolithic), [apps/user_profile/views_public.py](apps/user_profile/views_public.py) (580 lines), [apps/user_profile/views_settings.py](apps/user_profile/views_settings.py) (60 lines)
- **Templates:** 5 profile templates found (2 active, 3 legacy/unused), 700+ line settings template
- **Static Assets:** 1 CSS file (core.css), 1 JS file (settings.js), Alpine.js CDN used, legacy JS in backups/

### 1.2 Critical Findings
1. **PRIVACY LEAK RISK:** Direct ORM queries in views (30+ instances of `.objects.get/.filter` without privacy checks)
2. **DEBUG CODE IN PRODUCTION:** Extensive `_debug_log()` calls throughout views (50+ lines in views.py alone)
3. **NO SERVICE LAYER:** Views bypass services (EconomySyncService, AuditService, TournamentStatsService never called)
4. **LEGACY ROUTING:** 3 different URL patterns for same profile (`@username`, `/u/username/`, `/<username>/`)
5. **TEMPLATE DUPLICATION:** Multiple profile edit templates (profile_edit.html, profile_edit_modern.html, account/profile.html)
6. **UNSAFE PROFILE ACCESS:** No use of `get_visible_profile()` helper (privacy settings ignored in 15+ places)
7. **NO AUDIT TRAIL:** Zero integration with UserAuditEvent system (changes untracked)

---

## 2. URL ROUTING AUDIT

### 2.1 Current Route Inventory
**File:** [apps/user_profile/urls.py](apps/user_profile/urls.py)

```
OWNER PAGES (7 routes):
  /me/edit/                     → MyProfileUpdateView (redirects to /me/settings/)
  /me/tournaments/              → my_tournaments_view
  /me/kyc/upload/               → kyc_upload_view
  /me/kyc/status/               → kyc_status_view
  /me/privacy/                  → privacy_settings_view
  /me/settings/                 → settings_view (NEW unified page)
  /actions/save-game-profiles/  → save_game_profiles (AJAX endpoint)

MODAL ACTIONS (5 routes):
  /actions/update-bio/          → update_bio_ajax
  /actions/add-social-link/     → add_social_link_ajax
  /actions/add-game-profile/    → add_game_profile_ajax
  /actions/edit-game-profile/   → edit_game_profile_ajax
  /actions/delete-game-profile/ → delete_game_profile_ajax

FOLLOW SYSTEM (4 routes):
  /follow/<username>/           → follow_user
  /unfollow/<username>/         → unfollow_user
  /followers/                   → followers_list
  /following/                   → following_list

API ENDPOINTS (7 routes):
  /api/profile/get-game-id/     → get_game_id_api
  /api/profile/update-game-id/  → update_game_id_api
  /api/profile/check-game-id/   → check_game_id_api
  /api/profile/save-game-id/    → save_game_id_api
  /api/profile/get-all-game-ids/ → get_all_game_ids_api
  /api/profile/delete-game-id/  → delete_game_id_api
  /api/profile/<profile_id>/    → profile_api

PUBLIC PROFILES (6 routes):
  /@<username>/                 → profile_view (MAIN, Phase 3)
  /@<username>/achievements/    → achievements_view (Phase 4)
  /@<username>/match-history/   → match_history_view (Phase 4)
  /@<username>/certificates/    → certificates_view (Phase 4)
  /u/<username>/                → profile_view (LEGACY ALIAS)
  /<username>/                  → profile_view (LEGACY ALIAS)
```

### 2.2 Routing Problems
1. **Legacy Pollution:** 3 URL patterns for same profile (`@username` is modern, others should redirect)
2. **Mixed Concerns:** AJAX actions (`/actions/*`) mixed with page routes
3. **Dual API Systems:** Both `/api/profile/*` and `/actions/*` for AJAX (no clear pattern)
4. **No Public ID:** All routes use `<username>` instead of `<public_id>` (privacy risk: username enumeration)
5. **Missing Routes:** No `/me/economy/`, `/me/activity/`, `/me/stats/` (backed by new models but no frontend)

---

## 3. VIEW LAYER AUDIT

### 3.1 [apps/user_profile/views.py](apps/user_profile/views.py) (1116 lines)
**Role:** Main profile display + edit + game profiles + follow system

#### Bad Patterns Found
**Lines 93, 152, 172-173, 176, 203, 205, 224, 237, 248, 261, 272, 291, 299, 316, 327:** Direct ORM queries without privacy checks
```python
# Example: Line 93 - Unsafe update
UserProfile.objects.filter(user_id=request.user.id).update(...)

# Example: Line 172-173 - No privacy check on follow counts
follower_count = Follow.objects.filter(following=profile_user).count()
following_count = Follow.objects.filter(follower=profile_user).count()

# Example: Line 224 - Exposes social links without privacy check
social_links = SocialLink.objects.filter(user=profile_user).order_by('platform')

# Example: Line 291 - Direct wallet access (should use EconomySyncService)
wallet, created = DeltaCrownWallet.objects.get_or_create(profile=profile)
```

**Lines 115-164:** `profile_view()` function
- ✅ Uses `@login_required` decorator
- ❌ 50+ lines of debug logging (`_debug_log()` calls on almost every line)
- ❌ Directly queries `UserProfile.objects.create()` (line 152) instead of using service
- ❌ No audit event written when viewing profiles
- ❌ No privacy check helper (should use `get_visible_profile()` from services)

**Lines 57-104:** `MyProfileUpdateView`
- ✅ Uses `LoginRequiredMixin`
- ❌ GET redirects to settings (line 102), but URL still exists (confusing UX)
- ❌ Privacy flag updates (lines 86-98) don't write audit events
- ❌ Direct ORM update via `.filter().update()` (line 93) bypasses model save signals

#### Services NEVER Called
```python
# THESE EXIST BUT ARE NEVER USED IN VIEWS:
from apps.user_profile.services.economy_sync import EconomySyncService      # 0 usages
from apps.user_profile.services.tournament_stats import TournamentStatsService  # 0 usages
from apps.user_profile.services.audit import AuditService                   # 0 usages
```

**Why This Is Bad:**
- Economy sync can drift (wallet vs profile.cash mismatch)
- Tournament stats never displayed (backend ready, frontend missing)
- Audit trail empty (compliance failure)

### 3.2 [apps/user_profile/views_public.py](apps/user_profile/views_public.py) (580 lines)
**Role:** Public-facing profile view

#### Bad Patterns Found
**Lines 50-580:** `public_profile()` function
- ❌ 30+ lines of debug logging at start (lines 63-66)
- ✅ Privacy check exists (line 73: `is_private = bool(getattr(profile, "is_private", False))`)
- ❌ BUT: No per-field privacy checks (lines 224, 237, 248, 261, 272, 291, 299, 316 in main views.py)
- ❌ Duplicates logic from `profile_view()` (both functions do same thing)

**Lines 37-48:** `_get_profile()` helper
- Tries `user.profile` then `UserProfile.objects.filter(user=user).first()`
- ❌ No privacy enforcement (should be `get_visible_profile(user, viewer)`)

### 3.3 [apps/user_profile/views_settings.py](apps/user_profile/views_settings.py) (60 lines)
**Role:** Settings page view

#### Bad Patterns Found
**Lines 16-24:** `_get_profile_for()` helper
- Supports both `.profile` and `.userprofile` (good for backward compat)
- ❌ But creates profile via `UserProfile.objects.get_or_create()` (should use service)
- ❌ No audit event written

**Lines 26-60:** `MyProfileUpdateView` class
- ✅ Uses `LoginRequiredMixin`
- ❌ POST handler (lines 43-58) writes privacy flags via direct ORM update (line 93 in main views.py)
- ❌ No audit trail

---

## 4. TEMPLATE AUDIT

### 4.1 Active Templates
**[templates/user_profile/profile.html](templates/user_profile/profile.html)** (338 lines)
- **Tech Stack:** Alpine.js (CDN), Tailwind CSS, Django Templates
- **Purpose:** Main public profile display
- **Good:**
  - Clean Alpine.js state management (`x-data`, `x-show`, `x-on:click`)
  - Responsive Tailwind layout
  - Toast notifications system
  - Modular sections (hero banner, stats, game profiles, wallet)
- **Bad:**
  - Alpine.js loaded from CDN (should be bundled/self-hosted for offline)
  - No SSR fallback (if JS disabled, page is broken)
  - Wallet toggle client-side only (`walletBlurred: true`) — no server-side privacy check
  - Follow button uses `setTimeout()` mock (line 62-67) instead of real AJAX
  - No CSRF token in follow/share actions

**[templates/user_profile/settings.html](templates/user_profile/settings.html)** (700 lines)
- **Tech Stack:** Vanilla JS, Custom CSS (settings.css)
- **Purpose:** Unified settings page (/me/settings/)
- **Good:**
  - Comprehensive form (avatar, banner, bio, KYC, game IDs, social links, privacy)
  - Sidebar navigation for sections
  - File upload previews
- **Bad:**
  - 700 lines in ONE file (should be split into components)
  - Custom JS (settings.js) loaded (line 698) — check if it's audit-aware
  - No client-side validation (relies on backend only)
  - Form posts to multiple endpoints (confusing routing)

### 4.2 Legacy/Unused Templates
**[templates/users/profile_edit.html](templates/users/profile_edit.html)**
- Referenced by `MyProfileUpdateView.template_name` but GET redirects away (line 102 in views.py)
- ❌ Dead template (never rendered)

**[templates/users/profile_edit_modern.html](templates/users/profile_edit_modern.html)**
- Was `template_name` in `MyProfileUpdateView` before redirect was added
- ❌ Dead template (never rendered)

**[templates/account/profile.html](templates/account/profile.html)**
- Appears to be from `django-allauth` or accounts app
- ❌ Unused (user_profile app has own templates)

**[backups/user_profile_legacy_v1/templates/profile.html](backups/user_profile_legacy_v1/templates/profile.html)**
- Archived template from legacy system
- ❌ Should be deleted (in backups/)

### 4.3 Template Component Structure
```
templates/user_profile/
├── profile.html             ✅ ACTIVE (338 lines, Alpine.js)
├── settings.html            ✅ ACTIVE (700 lines, too large)
├── privacy_settings.html    ❓ Purpose unclear (not referenced in audit)
├── followers_modal.html     ❓ Modal component (check if used)
├── following_modal.html     ❓ Modal component (check if used)
├── components/              ✅ Good structure (check contents)
├── components_old/          ❌ Dead code (should be deleted)
├── profile/                 ❓ Subdirectory (check contents)
└── settings/                ❓ Subdirectory (check contents)
```

**Missing Templates:**
- `/me/economy/` page (no template found)
- `/me/activity/` page (no template found)
- `/me/stats/` page (no template found)
- Error pages (404 profile not found, 403 private profile)

---

## 5. STATIC ASSETS AUDIT

### 5.1 CSS
**[static/css/user_profile/core.css](static/css/user_profile/core.css)**
- ✅ Exists (referenced in profile.html line 7)
- ❓ Contents unknown (need to read file)
- ❓ Tailwind integration unknown (is it custom CSS or Tailwind @apply rules?)

**Missing CSS:**
- `/me/economy/` page styles
- `/me/activity/` page styles
- `/me/stats/` page styles

### 5.2 JavaScript
**[static/js/settings.js](static/js/settings.js)**
- ✅ Exists (referenced in settings.html line 698)
- ❓ Contents unknown (need to read file)
- ❌ Likely NOT audit-aware (no evidence of AuditService integration)

**[backups/user_profile_legacy_v1/static/js/profile.js](backups/user_profile_legacy_v1/static/js/profile.js)**
- ❌ Legacy JS in backups (should be deleted)

**Alpine.js (CDN):**
- Loaded from `https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js` (profile.html line 336)
- ❌ External dependency (offline-first platform should bundle)

**Missing JavaScript:**
- AJAX handlers for follow/unfollow (currently mocked with `setTimeout()`)
- Audit-aware form submissions
- CSRF token handling for AJAX

---

## 6. DATA FLOW AUDIT

### 6.1 Context Data Passed to Templates
**From [profile_view()](apps/user_profile/views.py#L115):**
```python
context = {
    'public_user': profile_user,           # User object (exposes email, is_staff, is_superuser)
    'profile': profile,                    # UserProfile object (all fields exposed)
    'is_own_profile': is_own_profile,
    'follower_count': follower_count,
    'following_count': following_count,
    'is_following': is_following,
    'wallet': wallet,                      # DeltaCrownWallet (balance, currency exposed)
    'recent_transactions': recent_transactions,
    'social_links': social_links,          # ❌ NO PRIVACY CHECK
    'achievements': achievements,
    'game_profiles': game_profiles,
    'matches': matches,
    'active_memberships': active_memberships,
    'certificates': certificates,
    'unread_notification_count': unread_notification_count,
}
```

**Privacy Violations:**
- `public_user` object exposes `email`, `is_staff`, `is_superuser` to template (line 172)
- `social_links` fetched without checking `profile.show_socials` (line 224)
- `wallet` exposed without checking if viewer has permission (line 291)
- `recent_transactions` visible to anyone (should be owner-only)

### 6.2 Services Available (But Not Used)
```python
# FROM apps/user_profile/services/
✅ PublicIDGenerator       # Used in migration, NOT in views
✅ EconomySyncService      # NEVER called in views (drift risk)
✅ TournamentStatsService  # NEVER called in views (stats missing)
✅ AuditService            # NEVER called in views (no audit trail)

# FROM apps/economy/services/
✅ WalletService           # Should be used, but views use DeltaCrownWallet.objects directly
```

**What This Means:**
- Frontend bypasses all business logic
- Data integrity rules not enforced
- Compliance requirements ignored

---

## 7. PRIVACY & SECURITY AUDIT

### 7.1 Privacy Settings Model Fields
**From [apps/user_profile/models/models_main.py](apps/user_profile/models/models_main.py):**
```python
# Privacy flags on UserProfile model:
is_private = models.BooleanField(default=False)
show_email = models.BooleanField(default=False)
show_phone = models.BooleanField(default=False)
show_socials = models.BooleanField(default=True)
show_real_name = models.BooleanField(default=False)
show_age = models.BooleanField(default=False)
show_gender = models.BooleanField(default=False)
show_country = models.BooleanField(default=True)
show_address = models.BooleanField(default=False)
```

### 7.2 Where Privacy Is Checked
✅ **Line 73 in [views_public.py](apps/user_profile/views_public.py#L73):**
```python
is_private = bool(getattr(profile, "is_private", False))
if is_private:
    return render(request, "user_profile/profile.html", {
        "public_user": user,
        "profile": profile,
        "is_private": True,
    })
```

### 7.3 Where Privacy Is IGNORED (LEAKS)
❌ **Line 224 in [views.py](apps/user_profile/views.py#L224):** Social links fetched without `show_socials` check
❌ **Line 237:** Achievements fetched without any privacy flag
❌ **Line 248:** Game profiles fetched without privacy flag
❌ **Line 261:** Match history fetched without privacy flag
❌ **Line 272:** Team memberships fetched without privacy flag
❌ **Line 291:** Wallet fetched without ownership check
❌ **Line 299:** Transactions fetched without ownership check
❌ **Line 316:** Certificates fetched without privacy flag
❌ **Template:** `public_user.email` available in template context (exposes email to anyone with template access)

### 7.4 CSRF Protection Audit
✅ **Forms:** `{% csrf_token %}` present in settings.html
❌ **AJAX:** No evidence of CSRF token in Alpine.js follow/share actions (profile.html line 62-67)

---

## 8. INTEGRATION AUDIT

### 8.1 Backend Models vs Frontend Pages
| Backend Model/Service       | Frontend Page        | Status |
|-----------------------------|----------------------|--------|
| UserProfile                 | /@username/          | ✅ Active |
| UserActivity                | /me/activity/        | ❌ Missing |
| UserProfileStats            | /me/stats/           | ❌ Missing |
| DeltaCrownWallet (economy)  | /me/economy/         | ❌ Missing |
| UserAuditEvent              | (admin only)         | ✅ N/A |
| EconomySyncService          | (backend job)        | ❌ Never called |
| TournamentStatsService      | (backend job)        | ❌ Never called |
| AuditService                | (all mutations)      | ❌ Never called |

### 8.2 Missing Integrations
1. **No Audit Trail:** Zero `AuditService.write_event()` calls in views
2. **No Economy Sync:** Views directly query `DeltaCrownWallet` instead of using `EconomySyncService`
3. **No Tournament Stats:** `TournamentStatsService` exists but data never displayed
4. **No Activity Log:** `UserActivity` model exists but no frontend page
5. **No Stats Page:** `UserProfileStats` model exists but no frontend page

---

## 9. TECHNICAL DEBT INVENTORY

### 9.1 High Priority (Security/Compliance)
1. **Privacy Leaks** (10+ locations): Social links, achievements, matches, wallet exposed without permission checks
2. **No Audit Trail** (100% coverage gap): Zero audit events written from frontend mutations
3. **Unsafe ORM Access** (30+ locations): Direct `.objects.get/.filter` without service layer
4. **CSRF Missing** (AJAX): Follow/share buttons use Alpine.js without CSRF token

### 9.2 Medium Priority (UX/Performance)
5. **Debug Code** (50+ lines): `_debug_log()` calls in production code
6. **Legacy Routing** (3 URL patterns): `@username`, `/u/username/`, `/<username>/` all active
7. **Template Duplication** (3 files): Multiple profile edit templates (2 never rendered)
8. **700-Line Settings Template**: Should be split into components
9. **No SSR Fallback**: Alpine.js pages broken without JavaScript

### 9.3 Low Priority (Code Quality)
10. **Service Layer Ignored** (0% usage): `EconomySyncService`, `TournamentStatsService` never called
11. **Dead Code** (5+ files): `components_old/`, legacy templates, backup JS
12. **Missing Pages** (3 pages): `/me/activity/`, `/me/stats/`, `/me/economy/`
13. **CDN Dependency** (Alpine.js): Should be bundled for offline-first
14. **No Client Validation**: Settings form relies on backend only

---

## 10. RECOMMENDATIONS

### 10.1 Immediate Actions (Before Frontend Rebuild)
1. **STOP THE BLEEDING:** Add privacy checks to lines 224, 237, 248, 261, 272, 291, 299, 316 in views.py
2. **AUDIT TRAIL:** Wrap all profile mutations in `AuditService.write_event()` calls
3. **REMOVE DEBUG CODE:** Delete all `_debug_log()` calls (or wrap in `if settings.DEBUG`)
4. **CONSOLIDATE ROUTING:** Redirect `/u/<username>/` and `/<username>/` to `/@<username>/`

### 10.2 Frontend Rebuild Strategy
1. **TEMPLATES-FIRST:** Keep Django Templates + Tailwind + Vanilla JS (NO React/Next/Vue)
2. **SERVICE LAYER ENFORCEMENT:** Views must call services, never ORM directly
3. **PRIVACY BY DEFAULT:** Use `get_visible_profile(user, viewer)` helper everywhere
4. **AUDIT-AWARE FORMS:** All mutations write audit events
5. **COMPONENT SPLIT:** Break 700-line settings.html into partials
6. **SSR FALLBACK:** Ensure pages work without JavaScript (progressive enhancement)
7. **OFFLINE-FIRST:** Bundle Alpine.js, no CDN dependencies
8. **PUBLIC_ID ROUTING:** Migrate from `<username>` to `<public_id>` in URLs

### 10.3 New Pages to Build
1. `/profile/<public_id>/` → Public profile (migrated from `/@username/`)
2. `/me/` → Owner dashboard (new)
3. `/me/settings/` → Unified settings (refactor existing)
4. `/me/economy/` → Wallet + transactions (new)
5. `/me/activity/` → Activity log (new)
6. `/me/stats/` → Computed stats (new)

---

## 11. CONCLUSION

**Current State:** Frontend is **UNSAFE and INCOMPLETE**. Privacy leaks everywhere, no audit trail, services ignored.

**Severity:**
- 🔴 **CRITICAL:** Privacy violations (10+ leaks), no CSRF on AJAX, direct ORM bypass
- 🟡 **HIGH:** Debug code in production, legacy routing, template duplication
- 🟢 **MEDIUM:** Missing pages (/me/activity/, /me/stats/, /me/economy/), dead code

**Next Steps:**
1. Create UP_FE_02_TARGET_UI_AND_CONTEXT_CONTRACTS.md (define new architecture)
2. Create UP_FE_03_EXECUTION_BACKLOG_AND_GATES.md (implementation plan)
3. Get user approval before starting any code changes

**Estimated Effort:** 40-60 hours (6 pages × 8-10 hours each, assuming no shortcuts)

---

**END OF AUDIT REPORT**
