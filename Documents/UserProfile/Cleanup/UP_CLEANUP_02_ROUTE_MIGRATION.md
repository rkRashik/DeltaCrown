# UP-CLEANUP-02 — Route Migration + Deprecation Wrappers

**Date:** December 24, 2025  
**Status:** Phase A — Deprecation Wrappers (Non-Breaking)  
**Related:** UP_CLEANUP_01_REPORT.md

---

## Executive Summary

26 URL patterns in `apps/user_profile/urls.py` route to legacy views that bypass privacy enforcement and lack audit trails. This document details the migration plan to safely deprecate these routes without breaking existing functionality.

**Strategy:** Wrap legacy views with deprecation logic that:
1. Calls new privacy-enforced services internally
2. Logs deprecation warnings with route path + user_id
3. Records audit events for any mutations
4. Maintains backward compatibility during transition

---

## Route Migration Table

| Legacy Route | Legacy View | Replacement | Migration Strategy | Phase |
|--------------|-------------|-------------|-------------------|-------|
| `/me/edit/` | `views.MyProfileUpdateView` | `api.settings_api.update_profile` | Wrapper → audit events | A |
| `/me/tournaments/` | `views.my_tournaments_view` | Return empty list (disabled) | 410 GONE | A |
| `/me/kyc/upload/` | `views.kyc_upload_view` | Admin-only operation | Wrapper → audit events | A |
| `/me/kyc/status/` | `views.kyc_status_view` | `api.kyc_api.get_status` | Wrapper → no changes | A |
| `/me/privacy/` | `views.privacy_settings_view` | `api.settings_api.update_privacy` | Wrapper → audit events | A |
| `/me/settings/` | `views.settings_view` | `api.settings_api.*` | Wrapper → audit events | A |
| `/actions/save-game-profiles/` | `views.save_game_profiles` | `api.game_id_api.save_game_id_api` | Wrapper → audit events | A |
| `/actions/update-bio/` | `views.update_bio` | `api.settings_api.update_profile` | Wrapper → audit events | A |
| `/actions/add-social-link/` | `views.add_social_link` | `services.profile_service.add_social` | Wrapper → audit events | A |
| `/actions/add-game-profile/` | `views.add_game_profile` | `api.game_id_api.save_game_id_api` | Wrapper → audit events | A |
| `/actions/edit-game-profile/<id>/` | `views.edit_game_profile` | `api.game_id_api.save_game_id_api` | Wrapper → audit events | A |
| `/actions/delete-game-profile/<id>/` | `views.delete_game_profile` | `api.game_id_api.delete_game_id_api` | Wrapper → audit events | A |
| `/actions/follow/<username>/` | `views.follow_user` | `services.follow_service.follow` | Wrapper → audit events | A |
| `/actions/unfollow/<username>/` | `views.unfollow_user` | `services.follow_service.unfollow` | Wrapper → audit events | A |
| `/@<username>/followers/` | `views.followers_list` | `services.follow_service.get_followers` | Wrapper → privacy filter | A |
| `/@<username>/following/` | `views.following_list` | `services.follow_service.get_following` | Wrapper → privacy filter | A |
| `/api/profile/get-game-id/` | `api_views.get_game_id` | `api.game_id_api.get_all_game_ids_api` | 301 Redirect | A |
| `/api/profile/update-game-id/` | `api_views.update_game_id` | `api.game_id_api.save_game_id_api` | 301 Redirect | A |
| `/api/profile/<id>/` | `views_public.profile_api` | `views.public.ProfileDetailView` | Wrapper → privacy filter | A |
| `/@<username>/achievements/` | `views.achievements_view` | `services.achievement_service` | Wrapper → privacy filter | A |
| `/@<username>/match-history/` | `views.match_history_view` | Return empty (disabled) | Wrapper → privacy filter | A |
| `/@<username>/certificates/` | `views.certificates_view` | `services.certificate_service` | Wrapper → privacy filter | A |
| `/@<username>/` | `views.profile_view` | `views.public.ProfileDetailView` | Wrapper → privacy filter | A |
| `/u/<username>/` | `views_public.public_profile` | `views.public.ProfileDetailView` | 301 Redirect | A |
| `/<username>/` | `views.profile_view` | `views.public.ProfileDetailView` | Wrapper → privacy filter | A |

---

## Rollout Plan

### Phase A: Deprecation Wrappers (Current — Non-Breaking) ✅

**Goals:**
- Add deprecation wrappers around all legacy views
- Emit warning logs: `DEPRECATED_USER_PROFILE_ROUTE`
- Record audit events via `AuditService` for mutations
- Maintain 100% backward compatibility

**Implementation:**
1. Create `apps/user_profile/decorators.py::@deprecate_route` decorator
2. Wrap each legacy view with decorator
3. Decorator calls new service internally
4. Log deprecation warning with: route, user_id, replacement
5. Record audit events for mutations

**Tests:**
- 5 representative routes tested for:
  - No privacy bypass (uses PrivacyService)
  - No crashes (backward compatible)
  - Deprecation warning logged

**Rollback:** Remove decorator wrappers (views unchanged)

---

### Phase B: URLconf Updates (Staging — Q1 2026)

**Goals:**
- Update URLconf to route to new endpoints
- Keep legacy routes as 301 redirects
- Monitor 404s for unmapped routes

**Implementation:**
1. Update `apps/user_profile/urls.py`:
   - Primary routes → new services
   - Legacy routes → 301 redirects
2. Add monitoring for redirect usage
3. Document replacement URLs in API docs

**Tests:**
- Integration tests for new routes
- Redirect tests for legacy routes

**Rollback:** Revert URLconf changes

---

### Phase C: Hard Deprecation (Production — Q2 2026)

**Goals:**
- Replace 301 redirects with 410 GONE
- Remove legacy view functions
- Delete unused templates

**Implementation:**
1. Replace redirects with 410 responses
2. Monitor error rates for 2 weeks
3. Remove legacy files if no errors

**Tests:**
- 410 response tests

**Rollback:** Restore legacy views from git

---

### Phase D: Cleanup (Production — Q3 2026)

**Goals:**
- Remove all legacy code
- Update documentation
- Remove deprecation wrappers

**Implementation:**
1. Delete files:
   - `apps/user_profile/views.py` (1116 lines)
   - `apps/user_profile/views_public.py` (580 lines)
   - `apps/user_profile/views_settings.py` (~200 lines)
   - `apps/user_profile/api_views.py` (~150 lines)
2. Remove legacy URLconf patterns
3. Update developer documentation

**Tests:**
- Full regression suite

**Rollback:** N/A (files deleted)

---

## Migration Safety Checklist

Before each phase:

### Pre-Migration
- [ ] Run full test suite: `pytest apps/user_profile/ -v`
- [ ] Check for import references: `grep -r "from apps.user_profile.views import" apps/`
- [ ] Verify no production traffic to legacy routes (last 7 days)
- [ ] Create database backup
- [ ] Document rollback procedure

### Post-Migration
- [ ] Monitor error rates (target: <0.1% increase)
- [ ] Monitor deprecation logs (target: identify high-traffic routes)
- [ ] Check 404s for unmapped routes
- [ ] Verify audit events recorded correctly
- [ ] Performance check (target: <50ms latency increase)

---

## Replacement Architecture

### Legacy View (UNSAFE):
```python
# apps/user_profile/views.py
def profile_view(request, username):
    profile = UserProfile.objects.get(user__username=username)
    # ❌ No privacy filtering
    # ❌ No audit trail
    # ❌ Direct model access
    return render(request, 'profile.html', {'profile': profile})
```

### Phase A: Wrapped (SAFE + BACKWARD COMPATIBLE):
```python
# apps/user_profile/views.py (wrapped)
from .decorators import deprecate_route
from .services.privacy import PrivacyService

@deprecate_route(replacement="/@{username}/", reason="Uses new privacy service")
def profile_view(request, username):
    # ✅ Log deprecation
    logger.warning("DEPRECATED_USER_PROFILE_ROUTE", extra={
        "route": request.path,
        "user_id": request.user.id,
        "replacement": f"/@{username}/"
    })
    
    # ✅ Use new privacy service
    profile = UserProfile.objects.get(user__username=username)
    visible_data = PrivacyService.filter_visible_fields(
        profile=profile,
        viewer=request.user,
        requested_fields=['display_name', 'bio', 'avatar', 'game_profiles']
    )
    
    # ✅ Backward compatible response
    return render(request, 'profile.html', {'profile': visible_data})
```

### Phase B: New Route (SAFE + MODERN):
```python
# apps/user_profile/views/public.py
from apps.user_profile.services.privacy import PrivacyService
from apps.user_profile.services.audit import AuditService

class ProfileDetailView(DetailView):
    def get(self, request, username):
        # ✅ Privacy enforcement
        profile = get_object_or_404(UserProfile, user__username=username)
        visible_data = PrivacyService.filter_visible_fields(
            profile=profile,
            viewer=request.user,
            requested_fields=request.GET.getlist('fields')
        )
        
        # ✅ Audit trail (read-only, no event needed)
        # ✅ Modern API response
        return JsonResponse(visible_data)
```

---

## Verification Commands

### Phase A (Current):
```bash
# Check Django configuration
python manage.py check

# Run legacy route tests
pytest apps/user_profile/tests/test_legacy_profile_routes.py -v --tb=no

# Run admin tests
pytest apps/user_profile/tests/test_admin*.py -v --tb=no

# Search for deprecation warnings in logs
grep "DEPRECATED_USER_PROFILE_ROUTE" logs/*.log
```

### Phase B (Staging):
```bash
# Test new routes
pytest apps/user_profile/tests/test_api/ -v

# Test redirects
pytest apps/user_profile/tests/test_redirects.py -v

# Monitor redirect usage
grep "301.*user_profile" logs/access.log | wc -l
```

### Phase C (Production):
```bash
# Test 410 responses
pytest apps/user_profile/tests/test_deprecation.py -v

# Monitor error rates
grep "410.*user_profile" logs/access.log | wc -l
```

---

## Status: Phase A Implementation ✅

**Completed:**
- ✅ Migration table created
- ✅ Rollout plan documented
- ✅ Safety checklist defined
- ⏳ Deprecation decorator (next step)
- ⏳ Wrapper views (next step)
- ⏳ Tests (next step)

**Next Actions:**
1. Implement `@deprecate_route` decorator
2. Wrap 5 representative legacy views
3. Create `test_legacy_profile_routes.py`
4. Verify: no privacy bypass, no crashes, logs warnings

