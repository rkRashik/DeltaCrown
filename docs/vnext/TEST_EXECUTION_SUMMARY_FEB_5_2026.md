# Journey Tests Execution Summary

**Date:** February 5, 2026  
**Database:** PostgreSQL (Docker container on port 5433)  
**Status:** Tests running; fixing model/URL mismatches

---

## Test Execution Results

### Overall Stats
- **Tests Run:** 37 total test methods
- **Passed:** 9 (24%)
- **Failed:** 8 (22%)
- **Errors:** 39 (errors during setup/teardown, counted per test + teardown)
- **Time:** 16.12s

---

## Issues Found & Fixes Needed

### 1. URL Name Mismatch (8 failures)
**Error:** `NoReverseMatch: Reverse for 'org_detail' not found`  
**Location:** `templates/organizations/org/org_manage.html`  
**Root Cause:** Template uses `{% url 'org_detail' organization.slug %}` but URL name is `'organization_detail'` (with "organization" prefix)  
**Fix:** Update template to use correct URL name `'organizations:organization_detail'`

### 2. Team Model - Missing `privacy` Field (12 errors)
**Error:** `TypeError: Team() got unexpected keyword arguments: 'privacy'`  
**Location:** `tests/test_journey2_team_detail_privacy_and_redirects.py`  
**Root Cause:** Test assumes `privacy='PUBLIC'/'PRIVATE'` field but Team model doesn't have this field  
**Fix:** Remove `privacy` parameter from Team.objects.create() or check model schema

### 3. Organization Model - Missing `primary_color` Field (8 errors)
**Error:** `TypeError: Organization() got unexpected keyword arguments: 'primary_color'`  
**Location:** `tests/test_journey5_org_detail_rendering.py`  
**Root Cause:** Test uses `primary_color='#FF5733'` but Organization model doesn't have this field  
**Fix:** Remove `primary_color` parameter or check Organization model schema

### 4. Login URL Path Mismatch (1 failure)
**Error:** `assert '/accounts/login/' in '/account/login/?next=/orgs/test-esports/manage/'`  
**Location:** `tests/test_journey6_org_manage_access.py::test_anonymous_redirected_to_login`  
**Root Cause:** Actual login URL is `/account/login/` (singular) not `/accounts/login/` (plural)  
**Fix:** Update test assertion to match actual URL

### 5. Team Creation Constraint Not Enforcing (1 failure)
**Error:** `assert 201 in [400, 409]` - API returned 201 (success) instead of conflict error  
**Location:** `tests/test_journey1_team_create_constraints.py::test_one_active_team_per_user_per_game_constraint`  
**Root Cause:** One ACTIVE team per user per game constraint is NOT enforced by API  
**Fix:** Either:
  - Add constraint validation to `create_team` API endpoint
  - Update test to match current API behavior (no constraint)

### 6. Protected FK Constraint on Teardown (39 errors)
**Error:** `ProtectedError: ("Cannot delete some instances of model 'User' because they are referenced through protected foreign keys: 'Organization.ceo'.", ...)`  
**Location:** All tests during teardown  
**Root Cause:** User has `on_delete=PROTECT` FK from Organization.ceo, preventing cascade delete  
**Fix:** Update test teardown to delete organizations before users, or use `on_delete=CASCADE`/`SET_NULL`

---

## Next Steps

1. ✅ **Fix template URL name** in [templates/organizations/org/org_manage.html](templates/organizations/org/org_manage.html)
2. ✅ **Remove invalid fields** from test fixtures (privacy, primary_color)
3. ✅ **Update login URL assertion** in Journey 6 tests
4. ⏳ **Investigate constraint enforcement** (may be intentional no-constraint)
5. ✅ **Fix test teardown order** to avoid ProtectedError

---

## Tests That Passed (9)

1. ✅ `test_journey1_team_create_constraints.py::test_team_create_page_renders`
2. ✅ `test_journey1_team_create_constraints.py::test_create_independent_team_success`
3. ✅ `test_journey1_team_create_constraints.py::test_create_org_owned_team_success`
4. ✅ `test_journey1_team_create_constraints.py::test_team_appears_on_hub_immediately`
5. ✅ `test_journey1_team_create_constraints.py::test_disbanded_team_allows_new_team_same_game`
6. ✅ `test_journey1_team_create_constraints.py::test_org_owned_team_nullable_organization`
7. ✅ `test_journey6_org_manage_access.py::test_scout_cannot_access_org_manage` (403 as expected)
8. ✅ `test_journey6_org_manage_access.py::test_outsider_cannot_access_org_manage` (403 as expected)
9. ✅ `test_journey6_org_manage_access.py::test_control_plane_alias_redirects` (302 redirect works)

---

## Command to Rerun Tests

```powershell
cd "G:/My Projects/WORK/DeltaCrown"
$env:DATABASE_URL_TEST="postgresql://dcadmin:dcpass123@localhost:5433/deltacrown_test"
& ".venv/Scripts/python.exe" -m pytest tests/test_journey1_team_create_constraints.py tests/test_journey2_team_detail_privacy_and_redirects.py tests/test_journey5_org_detail_rendering.py tests/test_journey6_org_manage_access.py -v
```
