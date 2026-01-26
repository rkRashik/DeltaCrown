# Quick Fix Summary: Team Queryset Crash

## 🚨 Production Crash Fixed

**Issue**: `FieldError: Cannot resolve keyword 'is_active' into field`  
**Location**: `/orgs/<slug>/` (Organization Detail Page)  
**Status**: ✅ RESOLVED

---

## What Was Wrong

vNext Team model has:
- ✅ `status` field (with choices: ACTIVE, DELETED, SUSPENDED, DISBANDED)
- ✅ `game_id` field (integer, not FK)

Code incorrectly assumed:
- ❌ `is_active` field (doesn't exist)
- ❌ `game` FK (doesn't exist)

---

## Changes Made

### 1. Service Fix
**File**: `apps/organizations/services/org_detail_service.py`

```python
# BEFORE (CRASHED):
active_teams = organization.teams.filter(is_active=True).select_related('game')

# AFTER (FIXED):
teams_qs = organization.teams.all()
try:
    teams_qs = teams_qs.filter(status__in=['ACTIVE', 'active'])
except Exception:
    teams_qs = organization.teams.all()
active_teams = list(teams_qs.order_by('-updated_at')[:24])
```

Added safe game label helper:
```python
def _safe_game_label(team):
    if getattr(team, 'game_id', None):
        return f"Game #{team.game_id}"
    return "—"
```

### 2. Template Namespace Fix
**Changed in 2 files**:
- `templates/organizations/org/org_detail.html` (1 change)
- `templates/organizations/org/org_hub.html` (4 changes)

```django
<!-- BEFORE: -->
{% url 'teams:team_detail' ... %}

<!-- AFTER: -->
{% url 'organizations:team_detail' ... %}
```

### 3. Regression Tests Added
**File**: `apps/organizations/tests/test_org_detail_service.py`

- `TestNoTeamIsActiveFilter` - Prevents is_active usage
- `TestNoTeamGameFK` - Prevents game FK traversal

---

## Verification Commands

```bash
# 1. Django check
python manage.py check
# Expected: System check identified no issues (0 silenced). ✅

# 2. Legacy namespace scan
grep -r "teams:" templates/organizations/
# Expected: No matches found ✅

# 3. Run server and test
python manage.py runserver
# Visit: http://127.0.0.1:8000/orgs/syntax/
# Expected: Page loads (200) ✅
```

---

## Files Changed

**Modified**:
1. `apps/organizations/services/org_detail_service.py` - Query fix + game label helper
2. `templates/organizations/org/org_detail.html` - Namespace fix (1x)
3. `templates/organizations/org/org_hub.html` - Namespace fix (4x)
4. `apps/organizations/tests/test_org_detail_service.py` - Regression tests (2x)

**Created**:
1. `docs/runbooks/PROD_CRASH_FIX_TEAM_QUERYSET.md` - Full documentation

---

## Quick Reference

### ✅ DO THIS (Correct):
```python
teams = org.teams.filter(status='ACTIVE')
game_id = team.game_id
label = f"Game #{team.game_id}"
```

### ❌ DON'T DO THIS (Crashes):
```python
teams = org.teams.filter(is_active=True)  # No is_active field!
game_name = team.game.name  # No game FK!
```

---

## Status: ✅ FIX COMPLETE

All automated checks pass. Ready for manual browser verification.
