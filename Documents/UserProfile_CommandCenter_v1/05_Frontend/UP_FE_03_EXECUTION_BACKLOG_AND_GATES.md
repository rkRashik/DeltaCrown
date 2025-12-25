# UP-FE-03: EXECUTION BACKLOG AND VERIFICATION GATES

**Project:** DeltaCrown User Profile — Frontend Cleanup  
**Phase:** Implementation Planning (TEMPLATES-FIRST)  
**Date:** 2025-01-XX  
**Prerequisites:** UP_FE_01_FRONTEND_AUDIT.md + UP_FE_02_TARGET_UI_AND_CONTEXT_CONTRACTS.md completed

---

## 1. BACKLOG OVERVIEW

### 1.1 Implementation Phases
```
PHASE 0: Foundation       (1 item,  4-6 hours)   - Services + privacy helper
PHASE 1: Public Profile   (1 page,  8-10 hours)  - /profile/<public_id>/
PHASE 2: Owner Pages      (5 pages, 40-50 hours) - /me/, /me/settings/, /me/economy/, /me/activity/, /me/stats/
PHASE 3: Cleanup          (1 item,  4-6 hours)   - Delete legacy, update routing
PHASE 4: Testing          (1 item,  6-8 hours)   - Manual QA, security audit
```

**Total Estimated Effort:** 62-80 hours (split into 10-hour sprints = 6-8 sprints)

### 1.2 Priority Tiers
```
P0 (CRITICAL):    Foundation, Public Profile, Cleanup (required for launch)
P1 (HIGH):        /me/settings/, /me/economy/ (needed for user operations)
P2 (MEDIUM):      /me/, /me/activity/, /me/stats/ (nice-to-have dashboards)
P3 (LOW):         Dark mode polish, advanced filters, charts
```

---

## 2. PHASE 0: FOUNDATION (P0)

### 2.1 FE-000: Create Privacy Helper Service
**Epic:** Foundation  
**Priority:** P0 (CRITICAL)  
**Estimated:** 4-6 hours

#### Acceptance Criteria
- [ ] Create `apps/user_profile/services/privacy.py`
- [ ] Implement `get_visible_profile(user, viewer)` function
- [ ] Privacy rules enforced:
  - [ ] `is_private` hides all data except avatar/display_name/username
  - [ ] `show_email` controls email visibility
  - [ ] `show_phone` controls phone visibility
  - [ ] `show_socials` controls social links visibility
  - [ ] `show_real_name` controls real_full_name visibility
  - [ ] Wallet/transactions: owner-only always
- [ ] Write 10 tests in `tests/test_privacy_service.py`:
  - [ ] `test_private_profile_minimal_card()`
  - [ ] `test_private_profile_owner_sees_all()`
  - [ ] `test_show_email_false_hides_email()`
  - [ ] `test_show_email_true_shows_email()`
  - [ ] `test_show_socials_false_hides_links()`
  - [ ] `test_wallet_owner_only()`
  - [ ] `test_transactions_owner_only()`
  - [ ] `test_unauthenticated_viewer()`
  - [ ] `test_authenticated_viewer_not_owner()`
  - [ ] `test_superuser_sees_all()`
- [ ] All 10 tests passing

#### Implementation Notes
```python
# apps/user_profile/services/privacy.py
from django.contrib.auth.models import AnonymousUser

def get_visible_profile(user, viewer):
    """
    Return user profile filtered by privacy settings.
    
    Args:
        user: User object whose profile to display
        viewer: User object viewing the profile (or AnonymousUser)
    
    Returns:
        dict with filtered fields
    """
    profile = user.profile
    is_own_profile = viewer.is_authenticated and viewer == user
    
    # RULE 1: Private profile → Minimal card
    if profile.is_private and not is_own_profile:
        return {
            'profile': profile,
            'user': user,
            'is_private': True,
            'is_own_profile': False,
            'visible_fields': ['avatar', 'display_name', 'username'],
        }
    
    # RULE 2: Field-level filtering
    visible_fields = {
        'email': profile.show_email or is_own_profile,
        'phone': profile.show_phone or is_own_profile,
        'socials': profile.show_socials or is_own_profile,
        'real_name': profile.show_real_name or is_own_profile,
        'wallet': is_own_profile,
        'transactions': is_own_profile,
    }
    
    return {
        'profile': profile,
        'user': user,
        'is_private': False,
        'is_own_profile': is_own_profile,
        'visible_fields': visible_fields,
    }
```

#### Verification Gates
- [ ] Code review: No direct ORM queries in service
- [ ] Test coverage: 100% (all branches covered)
- [ ] Manual test: Private profile, public profile, owner profile

---

## 3. PHASE 1: PUBLIC PROFILE (P0)

### 3.1 FE-101: Refactor Public Profile View
**Epic:** Public Profile  
**Priority:** P0 (CRITICAL)  
**Estimated:** 3-4 hours

#### Acceptance Criteria
- [ ] Create new view: `public_profile_view(request, public_id)` in `views.py`
- [ ] View logic:
  - [ ] Lookup user by `public_id` (not `username`)
  - [ ] Call `get_visible_profile(user, request.user)`
  - [ ] Write `PROFILE_VIEWED` audit event if authenticated
  - [ ] Render `user_profile/profile.html` or `user_profile/profile_private.html`
- [ ] Update URL: `path('profile/<str:public_id>/', views.public_profile_view, name='profile')`
- [ ] Deprecate old URLs:
  - [ ] `/@<username>/` redirects to `/profile/<public_id>/`
  - [ ] `/u/<username>/` redirects to `/profile/<public_id>/`
  - [ ] `/<username>/` redirects to `/profile/<public_id>/`
- [ ] Write 7 tests in `tests/test_public_profile_view.py`:
  - [ ] `test_public_profile_by_public_id()`
  - [ ] `test_private_profile_renders_minimal_card()`
  - [ ] `test_owner_sees_full_profile()`
  - [ ] `test_authenticated_user_sees_public_profile()`
  - [ ] `test_unauthenticated_user_sees_public_profile()`
  - [ ] `test_audit_event_written_if_authenticated()`
  - [ ] `test_legacy_url_redirects_to_public_id()`
- [ ] All 7 tests passing

#### Implementation Notes
```python
# apps/user_profile/views.py
from .services.privacy import get_visible_profile
from .services.audit import AuditService
from .models import UserProfile, UserAuditEvent

def public_profile_view(request, public_id):
    profile = get_object_or_404(UserProfile, public_id=public_id)
    user = profile.user
    
    # Privacy enforcement
    context = get_visible_profile(user, request.user)
    
    # Audit trail
    if request.user.is_authenticated:
        AuditService.write_event(
            user_profile=request.user.profile,
            event_type=UserAuditEvent.EventType.PROFILE_VIEWED,
            event_data={'viewed_profile': public_id},
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
    
    # Render appropriate template
    if context['is_private']:
        return render(request, 'user_profile/profile_private.html', context)
    else:
        return render(request, 'user_profile/profile.html', context)
```

#### Verification Gates
- [ ] Code review: Service layer used, no direct ORM
- [ ] Test coverage: All view branches covered
- [ ] Manual test: Public, private, owner views

---

### 3.2 FE-102: Create Profile Template Components
**Epic:** Public Profile  
**Priority:** P0 (CRITICAL)  
**Estimated:** 5-6 hours

#### Acceptance Criteria
- [ ] Create `templates/user_profile/profile.html` (main template, <200 lines)
- [ ] Create `templates/user_profile/profile_private.html` (minimal card, <50 lines)
- [ ] Create component partials:
  - [ ] `components/hero_banner.html` (avatar + banner + follow button)
  - [ ] `components/identity_card.html` (display_name + bio + metadata)
  - [ ] `components/stats_panel.html` (followers, matches, wins)
  - [ ] `components/game_profiles.html` (game IDs table)
  - [ ] `components/recent_activity.html` (last 5 activities)
  - [ ] `components/wallet_preview.html` (balance + currency, owner-only)
- [ ] Tailwind CSS used (no inline styles)
- [ ] Responsive design (mobile, tablet, desktop)
- [ ] SSR fallback (works without JS)
- [ ] CSRF token in AJAX actions
- [ ] Follow button uses real AJAX (not `setTimeout()` mock)

#### Implementation Notes
```django
{# templates/user_profile/profile.html #}
{% extends "base.html" %}
{% load static %}

{% block title %}{{ profile.display_name }} (@{{ user.username }}) - Profile{% endblock %}

{% block content %}
<div class="container mx-auto px-4 md:px-6 lg:px-8 max-w-7xl">
    {% include "user_profile/components/hero_banner.html" %}
    {% include "user_profile/components/identity_card.html" %}
    {% include "user_profile/components/stats_panel.html" %}
    
    {% if visible_fields.socials %}
        {% include "user_profile/components/social_links.html" %}
    {% endif %}
    
    {% include "user_profile/components/game_profiles.html" %}
    {% include "user_profile/components/recent_activity.html" %}
    
    {% if is_own_profile %}
        {% include "user_profile/components/wallet_preview.html" %}
    {% endif %}
</div>
{% endblock %}
```

#### Verification Gates
- [ ] Code review: No inline styles, Tailwind only
- [ ] Manual test: Responsive (mobile, tablet, desktop)
- [ ] Manual test: Works without JS (SSR fallback)
- [ ] Lighthouse score: >90 (performance, accessibility, best practices)

---

### 3.3 FE-103: Implement Follow/Unfollow AJAX
**Epic:** Public Profile  
**Priority:** P0 (CRITICAL)  
**Estimated:** 2-3 hours

#### Acceptance Criteria
- [ ] Create `static/js/user_profile/profile.js` (Vanilla JS)
- [ ] Implement `toggleFollow(public_id)` function:
  - [ ] POST to `/api/profile/follow/` with CSRF token
  - [ ] Update button text (Follow ↔ Unfollow)
  - [ ] Update follower count
  - [ ] Show toast notification
- [ ] Include in `profile.html`: `<script src="{% static 'js/user_profile/profile.js' %}"></script>`
- [ ] Backend: Update `follow_user()` view to accept `public_id` instead of `username`
- [ ] Backend: Write `PROFILE_FOLLOWED` audit event
- [ ] Write 3 tests in `tests/test_follow_ajax.py`:
  - [ ] `test_follow_ajax_success()`
  - [ ] `test_unfollow_ajax_success()`
  - [ ] `test_follow_requires_authentication()`
- [ ] All 3 tests passing

#### Implementation Notes
```javascript
// static/js/user_profile/profile.js
async function toggleFollow(publicId) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const btn = document.querySelector('#follow-btn');
    const isFollowing = btn.textContent.trim() === 'Unfollow';
    
    try {
        const response = await fetch('/api/profile/follow/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ public_id: publicId, action: isFollowing ? 'unfollow' : 'follow' }),
        });
        
        const data = await response.json();
        if (data.success) {
            btn.textContent = data.is_following ? 'Unfollow' : 'Follow';
            document.querySelector('#follower-count').textContent = data.follower_count;
            showToast(data.is_following ? 'Followed' : 'Unfollowed');
        }
    } catch (error) {
        showToast('Error', 'error');
    }
}

function showToast(message, type = 'success') {
    // Toast notification implementation
}
```

#### Verification Gates
- [ ] Manual test: Follow/unfollow works
- [ ] Manual test: Follower count updates
- [ ] Manual test: Toast notification appears
- [ ] Audit event written (check admin)

---

## 4. PHASE 2: OWNER PAGES (P1-P2)

### 4.1 FE-201: Create Owner Dashboard (/me/)
**Epic:** Owner Pages  
**Priority:** P2 (MEDIUM)  
**Estimated:** 6-8 hours

#### Acceptance Criteria
- [ ] Create `owner_dashboard_view()` in `views.py`
- [ ] View logic:
  - [ ] Fetch `UserProfileStats` via `TournamentStatsService` (recompute if stale)
  - [ ] Fetch `DeltaCrownWallet` via `EconomySyncService.ensure_synced()`
  - [ ] Fetch recent `UserActivity` (last 10)
  - [ ] Fetch unread notifications count
  - [ ] Calculate profile completion (0-100%)
  - [ ] Write `DASHBOARD_VIEWED` audit event
- [ ] Create `templates/user_profile/dashboard.html`
- [ ] Create components:
  - [ ] `components/profile_completion_card.html`
  - [ ] `components/recent_activity_card.html`
  - [ ] `components/wallet_card.html`
  - [ ] `components/notifications_card.html`
- [ ] Write 5 tests in `tests/test_dashboard_view.py`:
  - [ ] `test_dashboard_requires_authentication()`
  - [ ] `test_dashboard_stats_displayed()`
  - [ ] `test_dashboard_wallet_synced()`
  - [ ] `test_dashboard_activity_displayed()`
  - [ ] `test_audit_event_written()`
- [ ] All 5 tests passing

#### Verification Gates
- [ ] Code review: Services used, no direct ORM
- [ ] Manual test: All widgets display correct data
- [ ] Manual test: Profile completion accurate

---

### 4.2 FE-202: Refactor Settings Page (/me/settings/)
**Epic:** Owner Pages  
**Priority:** P1 (HIGH)  
**Estimated:** 10-12 hours

#### Acceptance Criteria
- [ ] Refactor `settings_view()` in `views_settings.py`
- [ ] Split 700-line template into:
  - [ ] `templates/user_profile/settings.html` (main, <150 lines)
  - [ ] `templates/user_profile/settings/sidebar.html`
  - [ ] `templates/user_profile/settings/section_profile.html`
  - [ ] `templates/user_profile/settings/section_privacy.html`
  - [ ] `templates/user_profile/settings/section_games.html`
  - [ ] `templates/user_profile/settings/section_socials.html`
  - [ ] `templates/user_profile/settings/section_kyc.html`
- [ ] All form submissions write audit events:
  - [ ] Profile update → `PROFILE_UPDATED`
  - [ ] Privacy flags → `PRIVACY_UPDATED`
  - [ ] Game ID add/edit/delete → `GAME_ID_ADDED/UPDATED/REMOVED`
  - [ ] Social link add/edit/delete → `SOCIAL_LINK_ADDED/UPDATED/REMOVED`
- [ ] Client-side validation (Vanilla JS)
- [ ] Write 12 tests in `tests/test_settings_view.py`:
  - [ ] `test_settings_requires_authentication()`
  - [ ] `test_profile_form_submission()`
  - [ ] `test_privacy_form_submission()`
  - [ ] `test_game_id_add()`
  - [ ] `test_game_id_edit()`
  - [ ] `test_game_id_delete()`
  - [ ] `test_social_link_add()`
  - [ ] `test_audit_events_written()` (for each mutation)
- [ ] All 12 tests passing

#### Verification Gates
- [ ] Code review: No template >300 lines
- [ ] Code review: All mutations audit-aware
- [ ] Manual test: All sections functional
- [ ] Manual test: Form validation works

---

### 4.3 FE-203: Create Economy Page (/me/economy/)
**Epic:** Owner Pages  
**Priority:** P1 (HIGH)  
**Estimated:** 8-10 hours

#### Acceptance Criteria
- [ ] Create `economy_view()` in `views.py`
- [ ] View logic:
  - [ ] Call `EconomySyncService.ensure_synced(profile)`
  - [ ] Fetch paginated transactions (25 per page)
  - [ ] Calculate summary stats (deposits, withdrawals, earnings, fees)
  - [ ] Write `WALLET_VIEWED` audit event
- [ ] Create `templates/user_profile/economy.html`
- [ ] Create components:
  - [ ] `components/wallet_header.html`
  - [ ] `components/sync_status_alert.html`
  - [ ] `components/transaction_filters.html`
  - [ ] `components/transaction_table.html`
  - [ ] `components/pagination.html`
- [ ] Filters: transaction type, date range, amount range
- [ ] Write 6 tests in `tests/test_economy_view.py`:
  - [ ] `test_economy_requires_authentication()`
  - [ ] `test_wallet_synced_before_display()`
  - [ ] `test_transactions_paginated()`
  - [ ] `test_filters_work()`
  - [ ] `test_summary_stats_correct()`
  - [ ] `test_audit_event_written()`
- [ ] All 6 tests passing

#### Verification Gates
- [ ] Code review: `EconomySyncService` called
- [ ] Manual test: Sync status alert works
- [ ] Manual test: Pagination works
- [ ] Manual test: Filters work

---

### 4.4 FE-204: Create Activity Log Page (/me/activity/)
**Epic:** Owner Pages  
**Priority:** P2 (MEDIUM)  
**Estimated:** 6-8 hours

#### Acceptance Criteria
- [ ] Create `activity_view()` in `views.py`
- [ ] View logic:
  - [ ] Fetch paginated `UserActivity` (50 per page)
  - [ ] Calculate activity stats (total logins, profile updates, etc)
  - [ ] Write `ACTIVITY_VIEWED` audit event
- [ ] Create `templates/user_profile/activity.html`
- [ ] Create components:
  - [ ] `components/activity_header.html`
  - [ ] `components/activity_filters.html`
  - [ ] `components/activity_timeline.html`
- [ ] Filters: event_type, date range
- [ ] Write 5 tests in `tests/test_activity_view.py`:
  - [ ] `test_activity_requires_authentication()`
  - [ ] `test_activity_paginated()`
  - [ ] `test_filters_work()`
  - [ ] `test_stats_correct()`
  - [ ] `test_audit_event_written()`
- [ ] All 5 tests passing

#### Verification Gates
- [ ] Manual test: Timeline displays correctly
- [ ] Manual test: Filters work
- [ ] Manual test: Pagination works

---

### 4.5 FE-205: Create Stats Page (/me/stats/)
**Epic:** Owner Pages  
**Priority:** P2 (MEDIUM)  
**Estimated:** 8-10 hours

#### Acceptance Criteria
- [ ] Create `stats_view()` in `views.py`
- [ ] View logic:
  - [ ] Fetch `UserProfileStats` via `TournamentStatsService.recompute()` if stale
  - [ ] Calculate computed properties (win_rate, avg_placement, rank)
  - [ ] Prepare time series data (monthly earnings, monthly matches)
  - [ ] Write `STATS_VIEWED` audit event
- [ ] Create `templates/user_profile/stats.html`
- [ ] Create components:
  - [ ] `components/stats_header.html`
  - [ ] `components/stats_grid.html`
  - [ ] `components/stats_charts.html` (use Chart.js or simple Tailwind bars)
  - [ ] `components/tournament_breakdown.html`
- [ ] Write 5 tests in `tests/test_stats_view.py`:
  - [ ] `test_stats_requires_authentication()`
  - [ ] `test_stats_recomputed_if_stale()`
  - [ ] `test_computed_properties_correct()`
  - [ ] `test_time_series_data_correct()`
  - [ ] `test_audit_event_written()`
- [ ] All 5 tests passing

#### Verification Gates
- [ ] Code review: `TournamentStatsService` called
- [ ] Manual test: Stats accurate
- [ ] Manual test: Charts render (if used)

---

## 5. PHASE 3: CLEANUP (P0)

### 5.1 FE-301: Delete Legacy Code
**Epic:** Cleanup  
**Priority:** P0 (CRITICAL)  
**Estimated:** 2-3 hours

#### Acceptance Criteria
- [ ] Delete dead templates:
  - [ ] `templates/users/profile_edit.html`
  - [ ] `templates/users/profile_edit_modern.html`
  - [ ] `templates/account/profile.html`
  - [ ] `backups/user_profile_legacy_v1/templates/profile.html`
- [ ] Delete dead static assets:
  - [ ] `backups/user_profile_legacy_v1/static/js/profile.js`
- [ ] Delete dead directories:
  - [ ] `templates/user_profile/components_old/`
- [ ] Remove debug code:
  - [ ] Delete all `_debug_log()` calls in `views.py` and `views_public.py` (50+ lines)
  - [ ] Delete `_should_debug()` helper (unless wrapped in `if settings.DEBUG`)
- [ ] Consolidate routing:
  - [ ] Keep `@<username>/` URLs as legacy redirects (DO NOT DELETE, just redirect to `/profile/<public_id>/`)
  - [ ] Update all internal links to use `/profile/<public_id>/`

#### Verification Gates
- [ ] Code review: No references to deleted files
- [ ] Grep search: No `_debug_log` calls (except in `if settings.DEBUG` blocks)
- [ ] Manual test: Legacy URLs redirect correctly

---

### 5.2 FE-302: Update URL Routing
**Epic:** Cleanup  
**Priority:** P0 (CRITICAL)  
**Estimated:** 2-3 hours

#### Acceptance Criteria
- [ ] Update `apps/user_profile/urls.py`:
  - [ ] Add `path('profile/<str:public_id>/', views.public_profile_view, name='profile')`
  - [ ] Redirect `/@<username>/` → `/profile/<public_id>/` (301 permanent)
  - [ ] Redirect `/u/<username>/` → `/profile/<public_id>/` (301 permanent)
  - [ ] Redirect `/<username>/` → `/profile/<public_id>/` (301 permanent)
  - [ ] Redirect `/me/edit/` → `/me/settings/` (301 permanent)
- [ ] Update all templates to use `{% url 'user_profile:profile' public_id=profile.public_id %}`
- [ ] Update all views to use `reverse('user_profile:profile', kwargs={'public_id': profile.public_id})`
- [ ] Write 4 tests in `tests/test_url_routing.py`:
  - [ ] `test_legacy_username_url_redirects()`
  - [ ] `test_public_id_url_works()`
  - [ ] `test_edit_url_redirects_to_settings()`
  - [ ] `test_all_internal_links_use_public_id()`
- [ ] All 4 tests passing

#### Verification Gates
- [ ] Code review: No hardcoded URLs in templates/views
- [ ] Manual test: Legacy URLs redirect correctly
- [ ] Grep search: No `/@<username>` or `/u/<username>` hardcoded

---

## 6. PHASE 4: TESTING (P0)

### 6.1 FE-401: Manual QA Testing
**Epic:** Testing  
**Priority:** P0 (CRITICAL)  
**Estimated:** 4-5 hours

#### Test Matrix
```
USER TYPE          | PUBLIC PROFILE | OWNER PAGES | SETTINGS | ECONOMY | ACTIVITY | STATS
-------------------|----------------|-------------|----------|---------|----------|-------
Unauthenticated    | ✓              | ✗           | ✗        | ✗       | ✗        | ✗
Authenticated      | ✓              | ✓           | ✓        | ✓       | ✓        | ✓
Owner (self)       | ✓              | ✓           | ✓        | ✓       | ✓        | ✓
Superuser          | ✓              | ✓           | ✓        | ✓       | ✓        | ✓

PRIVACY SETTING    | PUBLIC PROFILE | SOCIAL LINKS | EMAIL | WALLET | TRANSACTIONS
-------------------|----------------|--------------|-------|--------|-------------
is_private=True    | Minimal card   | Hidden       | Hidden| Hidden | Hidden
is_private=False   | Full profile   | show_socials | show_email | Owner-only | Owner-only
```

#### Acceptance Criteria
- [ ] Test all 24 scenarios (6 pages × 4 user types)
- [ ] Test all 5 privacy settings (2 is_private × 3 show_* flags)
- [ ] Test follow/unfollow (authenticated)
- [ ] Test form submissions (all settings sections)
- [ ] Test pagination (economy, activity)
- [ ] Test filters (economy, activity)
- [ ] Test responsive (mobile, tablet, desktop)
- [ ] Test SSR fallback (disable JS in browser)
- [ ] Document all bugs in `bugs.md`

#### Verification Gates
- [ ] All bugs documented
- [ ] All critical bugs fixed (P0/P1)
- [ ] All pages work without JS (SSR fallback)

---

### 6.2 FE-402: Security Audit
**Epic:** Testing  
**Priority:** P0 (CRITICAL)  
**Estimated:** 2-3 hours

#### Security Checklist
```
PRIVACY LEAKS:
□ No direct ORM queries in views (use services)
□ No user.email in public context (unless show_email=True)
□ No profile.phone unless show_phone=True
□ No social_links unless show_socials=True
□ No wallet/transactions unless is_own_profile=True
□ No game_profiles without privacy check
□ No matches/achievements without privacy check

CSRF PROTECTION:
□ All forms have {% csrf_token %}
□ All AJAX requests include X-CSRFToken header

AUDIT TRAIL:
□ PROFILE_VIEWED written when viewing profiles
□ PROFILE_UPDATED written when updating profile
□ PRIVACY_UPDATED written when changing privacy flags
□ GAME_ID_ADDED/UPDATED/REMOVED written for game IDs
□ SOCIAL_LINK_ADDED written for social links
□ WALLET_VIEWED written when viewing wallet
□ All audit events have IP + user agent

AUTHENTICATION:
□ All /me/* pages require authentication (@login_required)
□ All API endpoints require authentication
□ Follow/unfollow requires authentication

AUTHORIZATION:
□ Users can only edit own profile
□ Users can only view own wallet/transactions
□ Admins cannot edit other users' profiles via frontend (admin-only)
```

#### Acceptance Criteria
- [ ] All 22 security checks pass
- [ ] No privacy leaks found (manual test)
- [ ] No CSRF vulnerabilities (manual test)
- [ ] All audit events written (check admin)

#### Verification Gates
- [ ] Security checklist 100% complete
- [ ] Penetration test: Try to access other user's wallet (should fail)
- [ ] Penetration test: Try to bypass is_private flag (should fail)

---

## 7. BACKLOG SUMMARY

### 7.1 All Backlog Items (Priority Order)
```
PHASE 0: FOUNDATION (P0)
  FE-000: Create Privacy Helper Service                 [4-6h]  ✅ MUST DO

PHASE 1: PUBLIC PROFILE (P0)
  FE-101: Refactor Public Profile View                  [3-4h]  ✅ MUST DO
  FE-102: Create Profile Template Components            [5-6h]  ✅ MUST DO
  FE-103: Implement Follow/Unfollow AJAX                [2-3h]  ✅ MUST DO

PHASE 2: OWNER PAGES (P1-P2)
  FE-202: Refactor Settings Page (/me/settings/)        [10-12h] ✅ MUST DO (P1)
  FE-203: Create Economy Page (/me/economy/)            [8-10h]  ✅ MUST DO (P1)
  FE-201: Create Owner Dashboard (/me/)                 [6-8h]   ⚠️ SHOULD DO (P2)
  FE-204: Create Activity Log Page (/me/activity/)      [6-8h]   ⚠️ SHOULD DO (P2)
  FE-205: Create Stats Page (/me/stats/)                [8-10h]  ⚠️ SHOULD DO (P2)

PHASE 3: CLEANUP (P0)
  FE-301: Delete Legacy Code                            [2-3h]  ✅ MUST DO
  FE-302: Update URL Routing                            [2-3h]  ✅ MUST DO

PHASE 4: TESTING (P0)
  FE-401: Manual QA Testing                             [4-5h]  ✅ MUST DO
  FE-402: Security Audit                                [2-3h]  ✅ MUST DO
```

### 7.2 Minimal Viable Product (MVP)
**If time-constrained, deliver only P0+P1 items:**
```
1. FE-000: Privacy Helper Service           [4-6h]
2. FE-101: Refactor Public Profile View     [3-4h]
3. FE-102: Profile Template Components      [5-6h]
4. FE-103: Follow/Unfollow AJAX             [2-3h]
5. FE-202: Refactor Settings Page           [10-12h]
6. FE-203: Create Economy Page              [8-10h]
7. FE-301: Delete Legacy Code               [2-3h]
8. FE-302: Update URL Routing               [2-3h]
9. FE-401: Manual QA Testing                [4-5h]
10. FE-402: Security Audit                  [2-3h]

TOTAL MVP EFFORT: 42-55 hours (5-7 sprints @ 8h each)
```

**Defer to later:**
- FE-201: Owner Dashboard (/me/)
- FE-204: Activity Log Page (/me/activity/)
- FE-205: Stats Page (/me/stats/)

---

## 8. DEFINITION OF DONE (PER ITEM)

### 8.1 Code Quality
- [ ] No direct ORM queries in views (use services)
- [ ] All mutations write audit events
- [ ] Privacy checked via `get_visible_profile()`
- [ ] No inline styles (Tailwind only)
- [ ] No debug code (`_debug_log()` removed)
- [ ] No dead code (legacy templates deleted)

### 8.2 Testing
- [ ] Unit tests written (per acceptance criteria)
- [ ] All tests passing (new + existing)
- [ ] Manual test: Public, private, owner views
- [ ] Manual test: Responsive (mobile, tablet, desktop)
- [ ] Manual test: SSR fallback (works without JS)

### 8.3 Documentation
- [ ] Code comments for complex logic
- [ ] Docstrings for all new functions
- [ ] Template comments for sections
- [ ] Update UP_TRACKER_STATUS.md (mark item VERIFIED)

### 8.4 Security
- [ ] CSRF token in all forms/AJAX
- [ ] Privacy leaks checked (no exposure of sensitive fields)
- [ ] Authentication required for /me/* pages
- [ ] Authorization checked (owner-only for wallet/transactions)

---

## 9. SPRINT PLANNING (8-HOUR SPRINTS)

### Sprint 1: Foundation + Public Profile Start
```
FE-000: Privacy Helper Service          [4-6h]
FE-101: Public Profile View (start)     [2h of 3-4h]
```

### Sprint 2: Public Profile Complete
```
FE-101: Public Profile View (finish)    [1-2h remaining]
FE-102: Profile Template Components     [5-6h]
```

### Sprint 3: Follow System + Cleanup Start
```
FE-103: Follow/Unfollow AJAX            [2-3h]
FE-301: Delete Legacy Code              [2-3h]
FE-302: Update URL Routing              [2-3h]
```

### Sprint 4: Settings Page Start
```
FE-202: Refactor Settings Page (start)  [8h of 10-12h]
```

### Sprint 5: Settings Page Complete
```
FE-202: Refactor Settings Page (finish) [2-4h remaining]
FE-203: Economy Page (start)            [4-6h of 8-10h]
```

### Sprint 6: Economy Page Complete
```
FE-203: Economy Page (finish)           [2-4h remaining]
FE-401: Manual QA Testing (start)       [4-6h]
```

### Sprint 7: Testing + Launch
```
FE-401: Manual QA Testing (finish)      [0-1h remaining]
FE-402: Security Audit                  [2-3h]
Bug fixes                               [3-5h]
```

**Total MVP: 7 sprints × 8 hours = 56 hours**

---

## 10. RISK ASSESSMENT

### 10.1 High Risk
1. **Privacy Leaks:** Extensive refactoring needed, high chance of missing checks
   - Mitigation: Use `get_visible_profile()` everywhere, write 10+ privacy tests
2. **Audit Trail Gaps:** Easy to forget audit events in new views
   - Mitigation: Code review checklist, grep search for `AuditService` calls
3. **Legacy URL Breakage:** Redirects might break existing links
   - Mitigation: Keep legacy URLs as redirects (301), test all old URLs

### 10.2 Medium Risk
4. **Template Refactor Scope Creep:** 700-line settings.html could balloon to 1000+ lines if not careful
   - Mitigation: Strict 300-line limit per template, enforce via code review
5. **Service Integration Complexity:** Views never called services before, might introduce bugs
   - Mitigation: Write service tests first, then view tests
6. **CSRF Missing:** Easy to forget CSRF token in AJAX
   - Mitigation: Security checklist, manual test all AJAX endpoints

### 10.3 Low Risk
7. **SSR Fallback:** Alpine.js dependency might break fallback
   - Mitigation: Test with JS disabled, use progressive enhancement
8. **Performance:** Pagination might be slow with large datasets
   - Mitigation: Add database indexes, limit query size (25/50 per page)

---

## 11. SUCCESS METRICS

### 11.1 Code Quality Metrics
- [ ] Test coverage: >90% (new code)
- [ ] No direct ORM queries in views (100% service layer usage)
- [ ] No privacy leaks (100% `get_visible_profile()` usage)
- [ ] No audit gaps (100% mutation coverage)
- [ ] No templates >300 lines (enforced via code review)

### 11.2 User Experience Metrics
- [ ] Lighthouse score: >90 (all pages)
- [ ] Mobile-friendly: Yes (responsive design)
- [ ] Works without JS: Yes (SSR fallback)
- [ ] Page load time: <2s (95th percentile)

### 11.3 Security Metrics
- [ ] 0 privacy leaks found in penetration test
- [ ] 0 CSRF vulnerabilities found
- [ ] 100% audit trail coverage
- [ ] 100% authentication/authorization coverage

---

## 12. HANDOFF TO IMPLEMENTATION

**Before Starting Coding:**
1. Get user approval on this backlog (priorities, scope, MVP)
2. Create GitHub issues for each backlog item (FE-000 through FE-402)
3. Set up branch: `feature/user-profile-frontend-cleanup`
4. Review UP_FE_01_FRONTEND_AUDIT.md + UP_FE_02_TARGET_UI_AND_CONTEXT_CONTRACTS.md

**During Implementation:**
1. Mark issues as in-progress in GitHub
2. Follow Definition of Done checklist (per item)
3. Write tests BEFORE views (TDD approach)
4. Update UP_TRACKER_STATUS.md after each item complete

**After Implementation:**
1. Run full test suite (all 80+ tests should pass)
2. Run security audit (FE-402 checklist)
3. Create UP_FE_FINAL_SUMMARY.md (completion report)
4. Demo to user (showcase all 6 pages + privacy enforcement)

---

**END OF EXECUTION BACKLOG**
