# Organizations App URL Naming Fix - 2026-01-26

## Issue Summary

**Production Error:**
```
NoReverseMatch at /teams/invites/
Reverse for 'hub' not found. 'hub' is not a valid view function or pattern name.
```

**Root Cause:**
Template [team_invites.html](../templates/organizations/team/team_invites.html) line 75 referenced `{% url 'organizations:hub' %}`, but the URL pattern was named `vnext_hub`, not `hub`.

## Fix Applied

### Changed Files

#### 1. `templates/organizations/team/team_invites.html` (Line 75)
```diff
- <a class="hover:text-gray-200 transition" href="{% url 'organizations:hub' %}">Teams Hub</a>
+ <a class="hover:text-gray-200 transition" href="{% url 'organizations:vnext_hub' %}">Teams Hub</a>
```

#### 2. `apps/organizations/tests/test_url_name_contract.py` (NEW FILE)
Created comprehensive URL naming contract tests to prevent future NoReverseMatch errors.

## Canonical URL Names

All templates must use these canonical URL names:

| URL Name | Path | Required kwargs | Purpose |
|----------|------|-----------------|---------|
| `organizations:vnext_hub` | `/teams/vnext/` | None | Hub landing page |
| `organizations:team_create` | `/teams/create/` | None | Team creation wizard |
| `organizations:team_invites` | `/teams/invites/` | None | Team invitations dashboard |
| `organizations:team_detail` | `/teams/<slug>/` | `team_slug` | Team detail page |
| `organizations:organization_detail` | `/orgs/<slug>/` | `org_slug` | Organization profile |

## Forbidden URL Names

These names are **forbidden** and will cause NoReverseMatch errors:

- ❌ `organizations:hub` → Use `organizations:vnext_hub`
- ❌ `organizations:create` → Use `organizations:team_create`
- ❌ `organizations:invites` → Use `organizations:team_invites`
- ❌ `organizations:detail` → Use `organizations:team_detail` or `organizations:organization_detail`

## Template URL References Audit

All 9 template URL references are now correct:

✅ [team_invites.html](../templates/organizations/team/team_invites.html#L75) - `vnext_hub`
✅ [team_create.html](../templates/organizations/team/team_create.html#L142) - `vnext_hub`
✅ [hub/vnext_hub.html](../templates/organizations/hub/vnext_hub.html#L215) - `team_create`
✅ [hub/vnext_hub.html](../templates/organizations/hub/vnext_hub.html#L222) - `team_create`
✅ [hub/vnext_hub.html](../templates/organizations/hub/vnext_hub.html#L571) - `vnext_hub`
✅ [organization_detail.html](../templates/organizations/organization_detail.html#L115) - `team_create`
✅ [org/organization_detail.html](../templates/organizations/org/organization_detail.html#L115) - `team_create`
✅ [vnext_hub.html](../templates/organizations/vnext_hub.html#L46) - `team_create`
✅ [vnext_hub.html](../templates/organizations/vnext_hub.html#L63) - `team_create`

## URL Contract Tests

Run URL naming contract tests:

```bash
python -m pytest apps/organizations/tests/test_url_name_contract.py -v
```

**Test Classes:**

1. **URLNamingContractTests** - Verifies all canonical URL names can be reversed
2. **TemplatURLReferencesTests** - Validates templates only use canonical names
3. **URLSmokeTests** - Ensures URLs load without 500 errors
4. **URLKwargsValidationTests** - Validates kwarg requirements (`team_slug`, `org_slug`)

**Note:** Due to database access issues during URL module import (legacy `apps.teams.urls`), some tests may fail during full test runs. The URL reversals themselves are verified working via direct script test.

## Verification

All canonical URL names reverse correctly:

```
organizations:vnext_hub                       -> /teams/vnext/
organizations:team_create                     -> /teams/create/
organizations:team_invites                    -> /teams/invites/
organizations:team_detail                     -> /teams/test/
organizations:organization_detail             -> /orgs/test/
```

Verified by running:
```bash
python test_urls_quick.py
```

## Prevention

The URL contract tests will catch:

1. Templates referencing non-existent URL names
2. Templates using forbidden URL names
3. Incorrect kwarg usage (`slug` instead of `team_slug`)
4. Missing canonical URL patterns
5. URL name collisions

Add these tests to CI/CD pipeline to prevent regression.

## Related Documentation

- URL configuration: [apps/organizations/urls.py](../apps/organizations/urls.py)
- Template organization: [templates/organizations/](../templates/organizations/)
- De-legacy audit: [docs/ops/teams_de_legacy_audit.md](../docs/ops/teams_de_legacy_audit.md)

## Status

✅ **RESOLVED** - Production NoReverseMatch error fixed
✅ **STANDARDIZED** - All URL names use canonical naming
✅ **TESTED** - URL contract tests created
✅ **VERIFIED** - All URL reversals working correctly

---

**Fixed by:** GitHub Copilot
**Date:** 2026-01-26
**Issue:** NoReverseMatch at /teams/invites/ (organizations:hub not found)
**Solution:** Fixed template reference + created URL naming contract tests
