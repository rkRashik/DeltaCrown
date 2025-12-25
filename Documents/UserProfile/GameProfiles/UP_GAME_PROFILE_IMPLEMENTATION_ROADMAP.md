# UP-GAME-PROFILE-PHASE: Implementation Roadmap

**Phase:** Game Profile System Productization  
**Status:** Architecture Complete → Implementation Planning  
**Date:** 2024-12-24

---

## 📋 Architecture Documents (Completed)

✅ **UP_GAME_PROFILE_ARCHITECTURE.md** — Data model, migration plan, service layer  
✅ **UP_GAME_PROFILE_ADMIN_DESIGN.md** — Admin UX, inline forms, audit trail  
✅ **UP_GAME_PROFILE_FE_CONTRACT.md** — Frontend data contract, privacy, per-game rendering

---

## 🎯 Key Architectural Decisions

### ✅ Decision 1: Use Existing GameProfile Model (Normalized)

**What:** Promote existing `GameProfile` model as primary, deprecate `game_profiles` JSONField.

**Why:**
- Model already exists with proper foreign key relationship
- Django admin-native (TabularInline, filters, search)
- Query-friendly for stats/leaderboards
- Audit-ready (per-row change tracking)

**Impact:**
- No new model needed
- Need 3 new fields: `verified_at`, `verification_method`, `metadata` (JSONB)
- Migration to backfill from JSON → GameProfile rows

### ✅ Decision 2: Use `metadata` JSONField for Per-Game Flexibility

**What:** Add `metadata = JSONField(default=dict)` to GameProfile model.

**Why:**
- MLBB needs `server_id`
- PUBGM needs `tier_level`
- VALORANT needs `region`, `peak_episode`
- Avoid schema migrations for every game addition

**Example:**
```python
# MLBB profile
metadata = {'server_id': '1234', 'emblem_config': 'Marksman-Tank'}

# VALORANT profile
metadata = {'region': 'NA', 'peak_episode': 'E7A3'}
```

### ✅ Decision 3: Dual-Write During Transition (3 Months)

**What:** Write to both GameProfile model AND `game_profiles` JSONField during transition.

**Why:**
- Zero downtime migration
- Backward compatibility for existing code
- Safe rollback if issues arise
- Gradual cutover after validation

**Timeline:**
- Weeks 1-2: Backfill migration (JSON → GameProfile)
- Weeks 3-8: Dual-write period (validate parity)
- Week 9: Cutover (stop writing to JSON)
- Week 10+: Mark JSON deprecated (remove in 6 months)

### ✅ Decision 4: Per-Game Validation with Validator Classes

**What:** `GameValidators.get_validator(game).is_valid_ign(ign)`

**Why:**
- VALORANT: Must match `Name#TAG` format
- CS2: Must be 17-digit Steam ID starting with 7656
- MLBB: Must be 9-10 digits
- Centralized validation logic (DRY)

**Example:**
```python
class ValorantValidator:
    def is_valid_ign(self, ign):
        return bool(re.match(r'^[a-zA-Z0-9\s]{3,16}#[a-zA-Z0-9]{3,5}$', ign))
```

### ✅ Decision 5: Privacy-Filtered Context Builder

**What:** `GameProfileService.get_public_game_profiles(user, viewer)`

**Public Viewer:**
- ✅ See: game, ign, rank_name, main_role
- ❌ NO: matches_played, win_rate, kd_ratio, verification_method

**Owner:**
- ✅ See: ALL fields including stats, metadata, verification details

---

## 🚀 Implementation Phases

### **MISSION 1: Data Model + Service Layer** (Week 1)

**Goal:** Enhance GameProfile model, implement service layer with validators.

**Deliverables:**
1. Migration: Add 3 fields to GameProfile
   - `verified_at` (DateTimeField, null=True)
   - `verification_method` (CharField, blank=True)
   - `metadata` (JSONField, default=dict)
2. Migration: Add privacy field to UserProfile
   - `show_game_profiles` (BooleanField, default=True)
3. Create `GameValidators` module
   - 11 validator classes (one per game)
   - Unit tests for each validator
4. Enhance `GameProfileService`
   - `save_game_profile()` with validation + audit
   - `get_public_game_profiles()` with privacy filter
   - `delete_game_profile()` with audit
5. Write backfill migration script
   - JSON → GameProfile rows
   - Validation check (ensure 100% parity)
6. Unit tests (100% coverage)
   - Service methods
   - Validators
   - Privacy filtering

**Success Criteria:**
- ✅ Migrations run cleanly (0 errors)
- ✅ Backfill script: 100% parity (JSON vs model)
- ✅ Unit tests: 100% pass rate
- ✅ Django check: 0 issues

**Files Changed:**
- `apps/user_profile/migrations/0012_enhance_game_profile.py`
- `apps/user_profile/migrations/0013_add_game_profile_privacy.py`
- `apps/user_profile/migrations/0014_backfill_game_profiles.py`
- `apps/user_profile/models_main.py` (add 3 fields)
- `apps/user_profile/validators/game_validators.py` (NEW)
- `apps/user_profile/services/game_profile_service.py` (enhance)
- `apps/user_profile/tests/test_game_validators.py` (NEW)
- `apps/user_profile/tests/test_game_profile_service.py` (enhance)

**Estimated Time:** 3-4 days

---

### **MISSION 2: Admin UX Overhaul** (Week 2)

**Goal:** Replace JSON editor with intuitive inline forms + audit trail.

**Deliverables:**
1. Make `GameProfileInline` primary editing method
   - Show by default (not collapsed)
   - Add custom action buttons (Verify, Audit)
   - Real-time IGN validation (JavaScript)
2. Hide `game_profiles` JSONField
   - Mark as read-only in admin form
   - Add deprecation warning in docstring
3. Add bulk actions
   - "Normalize game profiles" action
   - "Bulk verify profiles" action
   - "Export audit trail" action (CSV)
4. Create audit trail view
   - `/admin/user_profile/gameprofile/{id}/audit/`
   - Show change history per profile
   - Filter by event type, date range
5. Add list filters
   - Filter by game, verified status, date
   - Search by IGN, username
6. Pre-save warnings
   - Warn if user has active tournaments
   - Block duplicate game entries
   - Validate IGN format before save
7. Admin tests (pytest)
   - Inline form rendering
   - Validation on save
   - Bulk actions
   - Audit trail view

**Success Criteria:**
- ✅ Admin can edit game profile in < 30 seconds
- ✅ IGN validation catches 95%+ errors
- ✅ Audit trail shows all changes
- ✅ Tests: 100% pass rate

**Files Changed:**
- `apps/user_profile/admin.py` (enhance GameProfileInline)
- `apps/user_profile/admin/game_profiles_field.py` (deprecate)
- `templates/admin/game_profile_audit.html` (NEW)
- `static/admin/js/game_profile_inline.js` (NEW)
- `apps/user_profile/tests/test_admin_game_profiles.py` (enhance)

**Estimated Time:** 3-4 days

---

### **MISSION 3: Frontend + Tournament Integration** (Week 3-4)

**Goal:** Update FE templates to use GameProfile model, fix tournament integration.

**Deliverables:**
1. Update context builders
   - `build_public_profile_context()` → use `GameProfileService.get_public_game_profiles()`
   - Remove JSON parsing logic
2. Update templates
   - `profile_public_v2.html` → render game profile cards
   - `profile_settings_v2.html` → add/edit/delete forms
   - Per-game styling (Tailwind classes)
3. Add settings mutation endpoints
   - `POST /me/settings/game-profiles/add`
   - `POST /me/settings/game-profiles/{game}/edit`
   - `POST /me/settings/game-profiles/{game}/delete`
   - Client-side + server-side validation
4. Update tournament integration
   - `apps/tournaments/views/registration_wizard.py` (remove hardcoded logic)
   - Use `GameProfileService.get_game_id(user, game_slug)`
5. Add validation API endpoint
   - `POST /api/validate-ign/`
   - Real-time validation for forms
6. Frontend tests (Playwright)
   - Add game profile flow
   - Edit game profile flow
   - Delete game profile flow
   - Privacy filtering (public vs owner)
7. Mobile responsiveness
   - Test 3 breakpoints (phone, tablet, desktop)
   - Touch gestures (swipe to delete)

**Success Criteria:**
- ✅ FE reads from GameProfile model (not JSON)
- ✅ Tournament registration auto-fills IGN correctly
- ✅ Privacy filtering works (public vs owner)
- ✅ Mobile usability: 85+ score
- ✅ E2E tests: 100% pass rate

**Files Changed:**
- `apps/user_profile/views/fe_v2.py` (add mutation endpoints)
- `apps/user_profile/services/profile_context.py` (use GameProfileService)
- `templates/user_profile/v2/profile_public.html` (render cards)
- `templates/user_profile/v2/profile_settings.html` (add forms)
- `templates/user_profile/v2/_game_profile_card.html` (NEW)
- `static/css/game_profiles.css` (NEW)
- `static/js/game_profile_forms.js` (NEW)
- `apps/tournaments/views/registration_wizard.py` (fix integration)
- `apps/user_profile/urls.py` (add endpoints)
- `tests/e2e/game_profiles.spec.js` (NEW)

**Estimated Time:** 6-7 days

---

## 📊 Success Metrics

### Data Quality
- ✅ 100% parity between JSON and GameProfile model
- ✅ 0 duplicate game entries per user
- ✅ 95%+ IGNs pass format validation

### Admin Efficiency
- ✅ Edit time: < 30 seconds (vs 2-3 min before)
- ✅ Error rate: < 2% (vs 15% before)
- ✅ Support tickets: < 2/month (vs 10/month before)

### User Experience
- ✅ Mobile usability: 85+ score
- ✅ Accessibility: 90+ (Lighthouse)
- ✅ Page load time: < 2 seconds

### Technical Health
- ✅ Test coverage: 100% (service + validators)
- ✅ Django check: 0 issues
- ✅ E2E tests: 100% pass rate
- ✅ Performance: < 50ms game profile queries

---

## 🔄 Rollback Plan

**If Issues Arise:**

1. **Revert to JSON as primary** (feature flag)
   ```bash
   python manage.py set_feature_flag USE_JSON_GAME_PROFILES true
   ```
2. Keep GameProfile model for new entries only
3. Dual-read during recovery period
4. Fix issues, re-attempt cutover

**Rollback SLA:** < 5 minutes (feature flag toggle)

---

## 📝 Pre-Implementation Checklist

**Before Starting Mission 1:**
- [ ] Architecture documents reviewed by RK Rashik
- [ ] Database backup created
- [ ] Feature flag system ready (`USE_JSON_GAME_PROFILES`)
- [ ] Monitoring setup (track game profile queries)
- [ ] Staging environment tested

**Before Cutover (End of Mission 3):**
- [ ] Backfill validation: 100% parity
- [ ] All tests passing (unit + E2E)
- [ ] Performance benchmarks met
- [ ] Mobile responsiveness verified
- [ ] Accessibility audit passed
- [ ] Admin trained on new UX
- [ ] User documentation updated

---

## 🎯 Timeline Summary

**Week 1:** Mission 1 (Data Model + Service)  
**Week 2:** Mission 2 (Admin UX)  
**Week 3-4:** Mission 3 (Frontend + Tournament Integration)  

**Total Duration:** 3-4 weeks  
**Team:** 1 developer (full-time)  
**Dependencies:** Architecture approval

---

## 📚 Documentation Links

- [Architecture](UP_GAME_PROFILE_ARCHITECTURE.md)
- [Admin Design](UP_GAME_PROFILE_ADMIN_DESIGN.md)
- [FE Contract](UP_GAME_PROFILE_FE_CONTRACT.md)
- [Games Constants](../../apps/games/constants.py)
- [Audit Service](../../apps/user_profile/services/audit.py)

---

**Status:** ✅ READY FOR IMPLEMENTATION  
**Next Action:** Review architecture docs → Approve → Start Mission 1  
**Owner:** RK Rashik (approval) + AI Agent (implementation)
