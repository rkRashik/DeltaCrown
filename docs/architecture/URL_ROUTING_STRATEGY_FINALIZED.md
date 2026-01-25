# URL Routing Strategy - Phase C+ Finalization

**Document Status:** FROZEN (Phase C+)  
**Version:** 1.0  
**Last Updated:** 2026-01-26 16:00  
**Breaking Changes:** Deferred to Phase D

---

## Current Routing Rules (LOCKED FOR PHASE C+)

### Team Detail URLs

**Current Implementation:**
```python
# apps/organizations/models/team.py
def get_absolute_url(self):
    """Return canonical URL for team detail page."""
    return reverse('organizations:team_detail', kwargs={'team_slug': self.slug})
```

**Resolves to:**
```
/organizations/teams/<slug>/
```

**Applies to:**
- ✅ Independent teams (no organization)
- ✅ Organization-owned teams
- ✅ All team types (competitive, casual, etc.)

### Why All Teams Use Same Route (Phase C+)

**Technical Reason:**
- Single route simplifies Phase C+ implementation
- Avoids template conditional logic for URL generation
- Ensures all team cards/links work identically
- Reduces risk of NoReverseMatch errors

**User Experience:**
- URL is still human-readable: `/organizations/teams/team-alpha/`
- Organization branding visible on team page (logo, colors, context)
- No user-facing functionality lost

**Phase D Plan:**
- Organization-scoped URLs will be introduced: `/orgs/<org>/teams/<slug>/`
- Requires routing adapter pattern (URL rewriting based on team.organization)
- Requires updated `get_absolute_url()` with conditional logic
- Requires template updates to handle both URL patterns

---

## Routing Adapter Status

### Current State (Phase C+)

**Feature Flag:**
```python
# deltacrown/settings.py
TEAM_VNEXT_ROUTING_MODE = os.getenv('TEAM_VNEXT_ROUTING_MODE', 'vnext_only')
```

**Possible Values:**
- `'legacy_only'` - All routes point to legacy `/teams/` system
- `'vnext_only'` - All routes point to vNext `/organizations/` system (CURRENT)
- `'hybrid'` - Routes conditionally resolve based on adapter logic (FUTURE - Phase D)

**Current Behavior (vnext_only):**
```python
# Example: Team.get_absolute_url()
# Independent team: /organizations/teams/solo-squad/
# Org-owned team:   /organizations/teams/ace-esports-alpha/  (same pattern)
```

### Phase D Enhancement (DEFERRED)

**Planned Behavior (hybrid mode):**
```python
# Example: Team.get_absolute_url() with routing adapter
# Independent team:  /organizations/teams/solo-squad/
# Org-owned team:    /orgs/ace-esports/teams/alpha/
```

**Implementation Plan (Phase D):**
1. Add routing adapter utility: `apps/organizations/adapters/routing.py`
2. Update `Team.get_absolute_url()` to use adapter
3. Add organization-scoped URL pattern: `path('orgs/<org_slug>/teams/<team_slug>/', ...)`
4. Add URL rewriting middleware (optional, for legacy URL compat)
5. Update all templates to use `get_absolute_url()` (already done in Phase C+)

---

## URL Patterns Reference

### Current URL Patterns (Phase C+)

```python
# apps/organizations/urls.py (app_name='organizations')

# Hub & navigation
path('hub/', views.vnext_hub, name='vnext_hub')
path('teams/create/', views.team_create, name='team_create')

# Team detail (ALL teams, regardless of organization)
path('teams/<slug:team_slug>/', views.team_detail, name='team_detail')

# Organization detail
path('orgs/<slug:org_slug>/', views.org_detail, name='org_detail')
```

**Full URLs:**
- Hub: `/organizations/hub/`
- Team create: `/organizations/teams/create/`
- Team detail: `/organizations/teams/<slug>/`
- Org detail: `/organizations/orgs/<slug>/`

### Phase D URL Patterns (PLANNED)

```python
# TODO (Phase D): Add organization-scoped team URLs

# Independent team (no org)
path('teams/<slug:team_slug>/', views.team_detail, name='team_detail')
# Example: /organizations/teams/solo-squad/

# Organization-owned team
path('orgs/<slug:org_slug>/teams/<slug:team_slug>/', views.org_team_detail, name='org_team_detail')
# Example: /organizations/orgs/ace-esports/teams/alpha/

# Routing adapter logic determines which view to use based on team.organization
```

---

## Template URL Generation (CANONICAL PATTERN)

### ✅ CORRECT: Use `get_absolute_url()`

```django
{# ALWAYS use this pattern #}
<a href="{{ team.get_absolute_url }}">{{ team.name }}</a>

{# Works for: #}
{# - Independent teams #}
{# - Org-owned teams #}
{# - Future org-scoped URLs (Phase D) #}
```

**Why This Is Canonical:**
- Single source of truth (model method)
- Adapts automatically when routing strategy changes (Phase D)
- No template updates needed when URLs change
- No conditional logic in templates

### ❌ INCORRECT: Hardcoded URLs

```django
{# NEVER do this - breaks in Phase D #}
<a href="/organizations/teams/{{ team.slug }}/">{{ team.name }}</a>

{# NEVER do this - breaks if org-scoped URLs added #}
<a href="{% url 'organizations:team_detail' team.slug %}">{{ team.name }}</a>
```

**Why This Is Wrong:**
- Breaks when routing strategy changes
- Requires template updates in Phase D
- Hardcodes Phase C+ routing decision
- May produce wrong URL for org-owned teams (Phase D)

### Reverse URL Resolution (Python Code)

```python
# ✅ CORRECT: Use model method
team_url = team.get_absolute_url()

# ✅ CORRECT: Use reverse() with current route name
from django.urls import reverse
team_url = reverse('organizations:team_detail', kwargs={'team_slug': team.slug})

# ❌ INCORRECT: Hardcoded string
team_url = f'/organizations/teams/{team.slug}/'  # Breaks in Phase D
```

---

## Routing Strategy Decision Log

### Why Not Org-Scoped URLs in Phase C+?

**Decision:** Defer to Phase D

**Reasons:**
1. **Reduces Phase C+ complexity**: Single route pattern simpler to implement and test
2. **Avoids premature optimization**: Org-scoped URLs require routing adapter (not yet built)
3. **No UX loss**: Organization branding still visible on team page
4. **Faster rollout**: Can ship Phase C+ hub without waiting for adapter
5. **Safer migration**: Phase D can add org-scoped URLs without breaking Phase C+ links

### Why `get_absolute_url()` Is Now Canonical

**Previous State (Phase 2):**
- `get_absolute_url()` had conditional logic: check if org-owned, return org-scoped URL
- Logic was complex and error-prone
- Created NoReverseMatch errors when org-scoped route didn't exist

**Current State (Phase C+):**
- `get_absolute_url()` simplified to single route
- No conditional logic, no errors
- Defer org-scoped logic to Phase D routing adapter

**Phase D State (Planned):**
- `get_absolute_url()` delegates to routing adapter
- Adapter returns org-scoped URL if team.organization exists
- Adapter returns independent URL if team.organization is None
- Conditional logic centralized in adapter (not scattered in templates)

---

## Migration Path to Phase D

### What Changes in Phase D

**Code Changes:**
1. Add `apps/organizations/adapters/routing.py` (routing adapter utility)
2. Update `Team.get_absolute_url()` to use adapter
3. Add new URL pattern: `path('orgs/<org_slug>/teams/<team_slug>/', ...)`
4. Add view: `org_team_detail()` (handles org-scoped team pages)
5. Update `settings.TEAM_VNEXT_ROUTING_MODE` to `'hybrid'`

**No Template Changes Required:**
- All templates already use `{{ team.get_absolute_url }}`
- Adapter automatically returns correct URL

**Backward Compatibility:**
- Old URLs (`/organizations/teams/<slug>/`) continue working
- New URLs (`/orgs/<org>/teams/<slug>/`) work for org-owned teams
- URL rewriting middleware (optional) redirects old → new

### What Doesn't Change in Phase D

**Guaranteed Stability:**
- `team.get_absolute_url()` method signature (no parameters)
- Return type: string (absolute path)
- No exceptions raised
- No breaking changes to template usage

---

## Routing Adapter Pattern (Phase D Preview)

**Conceptual Example (NOT YET IMPLEMENTED):**

```python
# apps/organizations/adapters/routing.py (Phase D)

from django.urls import reverse
from django.conf import settings

def get_team_url(team):
    """
    Routing adapter: Returns canonical URL for team based on routing mode.
    
    Args:
        team: Team object
    
    Returns:
        str: Absolute path to team detail page
    """
    routing_mode = getattr(settings, 'TEAM_VNEXT_ROUTING_MODE', 'vnext_only')
    
    if routing_mode == 'legacy_only':
        # Route to legacy teams app
        return reverse('teams:team_detail', kwargs={'slug': team.legacy_slug})
    
    elif routing_mode == 'hybrid':
        # Phase D: Org-scoped routing
        if team.organization:
            return reverse('organizations:org_team_detail', kwargs={
                'org_slug': team.organization.slug,
                'team_slug': team.slug
            })
        else:
            return reverse('organizations:team_detail', kwargs={'team_slug': team.slug})
    
    else:  # 'vnext_only' (Phase C+ default)
        return reverse('organizations:team_detail', kwargs={'team_slug': team.slug})


# apps/organizations/models/team.py (Phase D)

def get_absolute_url(self):
    """Return canonical URL for team detail page (routing adapter)."""
    from apps.organizations.adapters.routing import get_team_url
    return get_team_url(self)
```

---

## TODO Markers for Phase D

**In Code:**

```python
# apps/organizations/models/team.py
def get_absolute_url(self):
    """
    Return canonical URL for team detail page.
    
    TODO (Phase D): Implement routing adapter for org-scoped URLs.
    When Phase D is ready:
    1. Add apps/organizations/adapters/routing.py
    2. Implement get_team_url(team) with hybrid routing logic
    3. Update this method to use adapter
    4. Add URL pattern: path('orgs/<org>/teams/<slug>/', ...)
    5. Update TEAM_VNEXT_ROUTING_MODE to 'hybrid'
    """
    return reverse('organizations:team_detail', kwargs={'team_slug': self.slug})
```

**In Templates:**

```django
{# templates/teams/vnext_hub.html #}
{# TODO (Phase D): When org-scoped URLs added, these links will automatically adapt #}
<a href="{{ team.get_absolute_url }}">{{ team.name }}</a>
```

---

## Verification Checklist

**Phase C+ Routing Compliance:**

- [x] All teams use single route: `/organizations/teams/<slug>/`
- [x] `Team.get_absolute_url()` returns canonical URL
- [x] No hardcoded URLs in templates
- [x] No conditional logic for org-owned vs independent teams
- [x] All team cards/links use `{{ team.get_absolute_url }}`
- [x] Django `check` passes (no URL configuration errors)
- [x] No NoReverseMatch errors in logs

**Phase D Readiness:**

- [x] All templates use `get_absolute_url()` (ready for adapter)
- [x] TODO markers added in code
- [ ] Routing adapter design documented (this document)
- [ ] URL pattern design finalized (Phase D task)
- [ ] Migration plan documented (Phase D task)

---

## Summary

**Current State (Phase C+):**
- ✅ All teams resolve to `/organizations/teams/<slug>/`
- ✅ Single route pattern (no conditional logic)
- ✅ `get_absolute_url()` is canonical (templates compliant)
- ✅ Routing strategy frozen until Phase D

**Future State (Phase D):**
- ⏸️ Org-scoped URLs: `/orgs/<org>/teams/<slug>/`
- ⏸️ Routing adapter delegates URL generation
- ⏸️ Hybrid routing mode with backward compatibility
- ⏸️ No template changes required (already using `get_absolute_url()`)

**Breaking Change Policy:**
- Routing strategy is FROZEN for Phase C+
- Any URL pattern changes require Phase D approval
- `get_absolute_url()` signature is STABLE (no parameters, returns string)

---

**END OF ROUTING STRATEGY FINALIZATION**

**Next Review:** Phase D (when routing adapter is implemented)
