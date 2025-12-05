# 🎯 DELTACROWN MASTER IMPLEMENTATION BACKLOG
**Created:** December 5, 2025  
**Status:** Ready for Approval  
**Approach:** Fix Current System First → Then Add New Features

---

## 📋 TABLE OF CONTENTS

1. [Overview & Principles](#overview--principles)
2. [Phase 1: Critical System Fixes (Weeks 1-8)](#phase-1-critical-system-fixes-weeks-1-8)
3. [Phase 2: High Priority Improvements (Weeks 9-14)](#phase-2-high-priority-improvements-weeks-9-14)
4. [Phase 3: Game Architecture Centralization (Weeks 15-24)](#phase-3-game-architecture-centralization-weeks-15-24)
5. [Phase 4: Missing Team Features (Weeks 25-40)](#phase-4-missing-team-features-weeks-25-40)
6. [Testing & Quality Assurance Strategy](#testing--quality-assurance-strategy)
7. [Risk Management & Rollback Plans](#risk-management--rollback-plans)

---

## 📊 OVERVIEW & PRINCIPLES

### Project Goals

**Primary Objective:** Stabilize and perfect the current system without breaking production

**Secondary Objective:** Implement missing features to achieve industry parity

### Core Principles

✅ **Zero Breaking Changes** - All changes must be backward compatible  
✅ **Incremental Testing** - Test after each task, not at the end  
✅ **Production Safety** - Never deploy untested code  
✅ **Clear Rollback Path** - Every change must be reversible  
✅ **Documentation First** - Document before implementing  

### Source Audit Reports

This backlog consolidates findings from **FIVE** comprehensive audit reports:

1. ✅ **TEAM_APP_AUDIT_REPORT.md** - Backend/frontend code quality (12 CRITICAL, 18 HIGH issues)
2. ✅ **TEAM_FOCUSED_AUDIT_REPORT.md** - Ranking, game specs, roles (3 CRITICAL areas)
3. ✅ **TOURNAMENT_GAME_DEPENDENCIES_AUDIT.md** - 15+ hardcoded game logic files
4. ✅ **TEAMS_MISSING_FEATURES_ANALYSIS.md** - 65% feature completeness vs industry
5. ✅ **COMPLETE_IMPLEMENTATION_TASKLIST.md** - Original implementation plan

### Timeline Summary

| Phase | Focus | Duration | Priority |
|-------|-------|----------|----------|
| Phase 1 | Critical System Fixes | 8 weeks | 🔴 CRITICAL |
| Phase 2 | High Priority Improvements | 6 weeks | 🟠 HIGH |
| Phase 3 | Game Architecture | 10 weeks | 🔴 CRITICAL |
| Phase 4 | Missing Features | 16 weeks | 🟡 MEDIUM |
| **TOTAL** | **Complete Overhaul** | **40 weeks** | **~10 months** |

---

## 🔴 PHASE 1: CRITICAL SYSTEM FIXES (Weeks 1-8)

**Goal:** Fix architectural issues that cause bugs, performance problems, and maintenance nightmares

**Success Criteria:**
- Zero code duplication for core functions
- Single source of truth for all validations
- Page load times < 1 second
- No N+1 query problems
- All circular imports resolved

---

### 🎯 SPRINT 1: Code Consolidation (Week 1-2)

#### **TASK 1.1: Consolidate Team Creation Functions** 
**Priority:** 🔴 CRITICAL  
**Effort:** 16 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #1

**Problem:**
- 6 different team creation implementations scattered across codebase
- Different validation rules in each (name length: 50, 80, 100 chars)
- Bug fixes must be applied to 6 different locations
- Users get inconsistent error messages

**Current Locations:**
1. `apps/teams/views/public.py::create_team_view()` (lines 980-1120)
2. `apps/teams/views.py::create_team_with_roster()` (lines 140-280)
3. `apps/teams/views/advanced_form.py::create_team_advanced_view()` (lines 13-180)
4. `apps/teams/views/public.py::create_team_resume_view()` (lines 1972-2050)
5. `apps/teams/views/create.py::team_create_view()` (lines 38-623) - Modern wizard
6. `apps/teams/services/team_service.py::create_team_with_validation()` (lines 45-150)

**What to Do:**

1. **Keep These 3 Functions:**
   - `apps/teams/services/team_service.py::create_team()` - Core business logic (single source)
   - `apps/teams/views/create.py::team_create_view()` - Web UI wizard
   - `apps/teams/api/views.py::TeamCreateAPIView` - REST API endpoint

2. **Refactor Service Layer:**
   - Extract all validation logic to service
   - Implement transaction handling
   - Add comprehensive error handling
   - Create audit trail for team creation

3. **Update Web & API Views:**
   - Both views call `team_service.create_team()`
   - Views only handle HTTP request/response
   - No business logic in views

4. **Delete Deprecated Functions:**
   - Delete `public.py::create_team_view`
   - Delete `views.py::create_team_with_roster`
   - Delete `advanced_form.py::create_team_advanced_view`
   - Delete `public.py::create_team_resume_view`

5. **Update All Callers:**
   - Find all places importing old functions
   - Update to use new service layer
   - Test each caller individually

**Testing:**
- Create team via web UI ✓
- Create team via API ✓
- Create team with minimum fields ✓
- Create team with all optional fields ✓
- Verify validation errors show correctly ✓
- Check team creation audit log ✓

**Rollback Plan:**
- Keep old functions as `_legacy_create_team_view()` for 1 sprint
- If issues found, temporarily route back to legacy
- Delete legacy after 2 weeks of stability

**Expected Outcome:**
- -800 lines of duplicate code
- Single validation logic
- Consistent user experience
- Easier maintenance

---

#### **TASK 1.2: Fix Conflicting Permission Systems**
**Priority:** 🔴 CRITICAL  
**Effort:** 12 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #2

**Problem:**
- TWO `TeamPermissions` classes with SAME name
- `apps/teams/permissions.py` - Modern, cached, efficient
- `apps/teams/utils/security.py` - Legacy, database-heavy, has bugs
- 46 files import one or the other - developer confusion
- Permission checks fail intermittently depending on import

**What to Do:**

1. **Rename Legacy Class:**
   - `apps/teams/utils/security.py::TeamPermissions` → `LegacyTeamPermissions`
   - Add `@deprecated` decorator with migration warning
   - Add docstring explaining why deprecated

2. **Find All Legacy Imports:**
   ```bash
   grep -r "from apps.teams.utils.security import TeamPermissions" apps/
   ```
   - Create list of all files importing legacy version
   - Estimate ~46 files need updates

3. **Replace Legacy with Modern:**
   - Update all 46 files to use `apps.teams.permissions.TeamPermissions`
   - Test each file after update
   - Verify permission checks work correctly

4. **Add Integration Tests:**
   - Test all permission scenarios:
     - `can_edit_team()`
     - `can_invite_members()`
     - `can_manage_roster()`
     - `can_delete_team()`
   - Test with different roles (owner, captain, manager, player)

5. **Delete Legacy File:**
   - After 2 weeks of successful operation
   - Remove `apps/teams/utils/security.py` entirely
   - Remove from git history (optional, for cleanup)

**Testing:**
- Owner can edit team settings ✓
- Captain can manage roster ✓
- Manager can invite members ✓
- Player cannot edit team ✓
- Non-member cannot access team ✓
- Permission checks use cache (verify in logs) ✓

**Expected Outcome:**
- Single permission system
- Consistent permission checks
- Better performance (cached vs DB queries)
- Clear developer experience

---

#### **TASK 1.3: Create Single Validation Source**
**Priority:** 🔴 CRITICAL  
**Effort:** 10 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #3

**Problem:**
- Team name/tag validation in 8 different places
- Different max lengths: 50, 80, 100 characters
- Different regex patterns for tags
- API allows names that web form rejects

**Locations:**
1. `apps/teams/models/_legacy.py::Team.clean()` (lines 45-60)
2. `apps/teams/forms.py::TeamCreationForm` (lines 22-50)
3. `apps/teams/validators.py::validate_team_name()` (lines 45-70)
4. `apps/teams/views/create.py` - AJAX validation (lines 280-310)
5. `apps/teams/views/ajax.py::check_team_name_unique()` (lines 50-80)
6. `apps/teams/api/views.py` - API serializer (lines 120-145)
7. `apps/teams/services/team_service.py` (lines 180-200)
8. `apps/teams/views/public.py` - Inline validation (lines 1100-1120)

**What to Do:**

1. **Define Constants in `apps/teams/constants.py` (NEW FILE):**
   ```python
   # Team Name Rules
   TEAM_NAME_MIN_LENGTH = 3
   TEAM_NAME_MAX_LENGTH = 100
   TEAM_NAME_PATTERN = r'^[a-zA-Z0-9\s\-_]{3,100}$'
   TEAM_NAME_HELP_TEXT = "3-100 characters. Letters, numbers, spaces, hyphens, underscores allowed."
   
   # Team Tag Rules
   TEAM_TAG_MIN_LENGTH = 2
   TEAM_TAG_MAX_LENGTH = 10
   TEAM_TAG_PATTERN = r'^[A-Z0-9]{2,10}$'
   TEAM_TAG_HELP_TEXT = "2-10 uppercase letters and numbers only."
   
   # Roster Limits
   MAX_ROSTER_SIZE = 8
   MIN_ROSTER_SIZE = 1
   
   # Other Constants
   INVITE_EXPIRY_DAYS = 7
   DRAFT_TTL_MINUTES = 30
   TEAM_CACHE_TTL = 300  # 5 minutes
   ```

2. **Create Canonical Validators in `apps/teams/validators.py`:**
   ```python
   from apps.teams.constants import *
   
   def validate_team_name(value):
       """THE canonical team name validator - use everywhere."""
       if len(value) < TEAM_NAME_MIN_LENGTH:
           raise ValidationError(f"Minimum {TEAM_NAME_MIN_LENGTH} characters")
       if len(value) > TEAM_NAME_MAX_LENGTH:
           raise ValidationError(f"Maximum {TEAM_NAME_MAX_LENGTH} characters")
       if not re.match(TEAM_NAME_PATTERN, value):
           raise ValidationError("Only letters, numbers, spaces, hyphens, underscores")
       if Team.objects.filter(name__iexact=value).exists():
           raise ValidationError("Team name already taken")
   
   def validate_team_tag(value):
       """THE canonical team tag validator - use everywhere."""
       # Similar structure
   ```

3. **Use Validators Everywhere:**
   - Model: `name = CharField(max_length=100, validators=[validate_team_name])`
   - Form: `name = CharField(validators=[validate_team_name])`
   - API Serializer: `validators=[validate_team_name]`
   - AJAX: Call `validate_team_name()` directly

4. **Delete All Other Validation Code:**
   - Remove inline validation from views
   - Remove duplicate validators
   - Keep ONLY canonical validators

5. **Update Frontend:**
   - Update JavaScript validation to match backend rules
   - Use constants for max length attributes
   - Add helpful error messages matching backend

**Testing:**
- Valid team name accepted (web, API, AJAX) ✓
- Too short name rejected everywhere ✓
- Too long name rejected everywhere ✓
- Invalid characters rejected everywhere ✓
- Duplicate name rejected everywhere ✓
- Tag validation consistent everywhere ✓

**Expected Outcome:**
- Single source of truth for validation
- Consistent validation across web/API
- Easy to update rules (change constants only)
- Better user experience

---

#### **TASK 1.4: Split Massive Files**
**Priority:** 🟠 HIGH  
**Effort:** 14 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #4

**Problem:**
- `apps/teams/views/public.py` - 2,050 lines (unmaintainable)
- `apps/teams/models/_legacy.py` - 1,137 lines
- `apps/teams/api_views.py` - 982 lines
- `apps/teams/admin.py` - 856 lines
- Difficult to navigate, slow IDE, merge conflicts

**What to Do:**

**1. Split `public.py` into logical modules:**

Create new structure:
```
apps/teams/views/
├── list.py          - team_list_view, filtering, search
├── detail.py        - team_detail_view, profile display
├── settings.py      - team_settings_view, configuration
├── invites.py       - invite management (already exists, enhance)
├── join.py          - join requests, applications
├── legacy.py        - deprecated views (temporary)
└── utils.py         - shared helper functions
```

**Steps:**
- Extract each view function to appropriate file
- Update URL imports
- Update all internal imports
- Keep `public.py` as import facade for backward compatibility (temporary)
- After 1 sprint, remove `public.py` facade

**2. Split `models/_legacy.py`:**

```
apps/teams/models/
├── team.py              - Core Team model
├── membership.py        - TeamMembership, roles
├── invitation.py        - TeamInvitation
├── analytics.py         - TeamAnalytics (already exists)
├── ranking.py           - Ranking models (already exists)
└── legacy.py            - Deprecated models (mark for deletion)
```

**3. Split `api_views.py`:**

```
apps/teams/api/views/
├── team_views.py        - Team CRUD operations
├── membership_views.py  - Member management
├── roster_views.py      - Roster operations
├── stats_views.py       - Analytics/statistics
└── search_views.py      - Search/filter endpoints
```

**4. Split `admin.py`:**

```
apps/teams/admin/
├── team_admin.py        - TeamAdmin
├── membership_admin.py  - MembershipAdmin
├── ranking_admin.py     - RankingAdmin
└── __init__.py          - Register all admins
```

**Testing After Each Split:**
- All URLs still work ✓
- Admin interface loads correctly ✓
- No import errors ✓
- All views render correctly ✓

**Expected Outcome:**
- Files < 300 lines each (manageable)
- Better organization
- Easier code review
- Faster IDE performance
- Fewer merge conflicts

---

### 🎯 SPRINT 2: Performance Optimization (Week 3-4)

#### **TASK 2.1: Fix N+1 Query Problems**
**Priority:** 🔴 CRITICAL  
**Effort:** 12 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #7

**Problem:**
- Team list view: 81 queries for 20 teams
- Team detail view: 15 queries per page
- Analytics view: 30+ queries
- Page load time: 3-5 seconds (unacceptable)

**What to Do:**

**1. Optimize `team_list_view()`:**

Current (BAD):
```python
teams = Team.objects.filter(is_public=True)  # Query 1
for team in teams:
    captain_name = team.captain.display_name  # Query 2-21
    member_count = team.memberships.filter(status='ACTIVE').count()  # Query 22-41
    # etc... 81 total queries
```

New (GOOD):
```python
teams = Team.objects.filter(is_public=True).select_related(
    'captain',
    'captain__user',
).prefetch_related(
    Prefetch('memberships', queryset=TeamMembership.objects.filter(status='ACTIVE')),
    'achievements',
    'followers',
).annotate(
    member_count=Count('memberships', filter=Q(memberships__status='ACTIVE')),
    follower_count=Count('followers'),
    is_following=Exists(
        TeamFollow.objects.filter(team=OuterRef('pk'), user=request.user)
    )
)
# Now: 3 queries total!
```

**2. Optimize `team_detail_view()`:**
- Add `select_related()` for ForeignKey lookups
- Add `prefetch_related()` for reverse ForeignKeys
- Use `annotate()` for counts/aggregates
- Target: < 5 queries per page

**3. Optimize `team_analytics_view()`:**
- Prefetch match history with tournament data
- Annotate statistics instead of calculating in Python
- Use database aggregation functions
- Target: < 8 queries per page

**4. Add Django Debug Toolbar (Dev Environment):**
```python
# settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```
- Monitor query counts in development
- Set up alerts if queries > threshold

**5. Document Query Optimization Patterns:**
- Create `docs/development/query-optimization.md`
- Document common patterns (list views, detail views)
- Add to developer onboarding

**Testing:**
- Run Django Debug Toolbar on each view ✓
- Verify query count reduction ✓
- Load test with 100 teams (should handle easily) ✓
- Check page load time < 1 second ✓

**Expected Outcome:**
- 81 queries → 3 queries (team list)
- 15 queries → 4 queries (team detail)
- Page load time: 3-5s → < 1s
- Better scalability

---

#### **TASK 2.2: Add Database Indexes**
**Priority:** 🟠 HIGH  
**Effort:** 8 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #8

**Problem:**
- Common queries not indexed (table scans on 10k+ rows)
- `game` column has NO index but queried 1000+ times/day
- Slow queries: 250ms+ for simple filters

**What to Do:**

**1. Analyze Current Query Patterns:**
```sql
-- Most common queries (from logs/APM):
-- 1. Team listing by game
SELECT * FROM teams_team WHERE game = 'valorant' AND is_public = true ORDER BY created_at DESC;

-- 2. Regional team search
SELECT * FROM teams_team WHERE game = 'valorant' AND region = 'NA' AND is_active = true;

-- 3. Captain lookup
SELECT * FROM teams_team WHERE captain_id = 123 AND is_active = true;

-- 4. Ranking order
SELECT * FROM teams_team WHERE is_active = true ORDER BY total_points DESC;
```

**2. Add Indexes to Team Model:**
```python
class Team(models.Model):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            # Team listing (most common query)
            models.Index(fields=['game', 'is_public', 'is_active'], 
                        name='team_listing_idx'),
            
            # Regional search
            models.Index(fields=['game', 'region', 'is_active'], 
                        name='team_region_idx'),
            
            # Captain lookup
            models.Index(fields=['captain', 'is_active'], 
                        name='team_captain_idx'),
            
            # Ranking queries
            models.Index(fields=['-total_points'], 
                        name='team_points_idx'),
            
            # Chronological sorting
            models.Index(fields=['-created_at'], 
                        name='team_created_idx'),
            
            # Search by slug (should already exist, verify)
            # models.Index(fields=['slug'], name='team_slug_idx'),
        ]
```

**3. Add Indexes to TeamMembership:**
```python
class TeamMembership(models.Model):
    class Meta:
        indexes = [
            # Active members lookup
            models.Index(fields=['team', 'status', 'role'], 
                        name='membership_active_idx'),
            
            # User's teams
            models.Index(fields=['user', 'status'], 
                        name='membership_user_idx'),
        ]
```

**4. Create Migration:**
```bash
python manage.py makemigrations teams --name add_performance_indexes
python manage.py sqlmigrate teams 0XXX  # Review SQL
python manage.py migrate teams
```

**5. Analyze Query Performance Before/After:**
```sql
-- PostgreSQL
EXPLAIN ANALYZE SELECT * FROM teams_team 
WHERE game = 'valorant' AND is_public = true 
ORDER BY created_at DESC LIMIT 20;

-- Before: Seq Scan (250ms)
-- After: Index Scan (15ms) ✓
```

**Testing:**
- Run EXPLAIN ANALYZE on common queries ✓
- Verify index usage (should see "Index Scan") ✓
- Load test: 10k teams, queries < 50ms ✓
- Monitor database CPU (should decrease) ✓

**Expected Outcome:**
- Query time: 250ms → 15ms (16x faster)
- Database CPU usage reduced
- Better scalability for large datasets

---

#### **TASK 2.3: Resolve Circular Imports**
**Priority:** 🟠 HIGH  
**Effort:** 16 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #5

**Problem:**
- 46 files use inline imports (code smell)
- Indicates circular dependency issues
- Slow module loading
- Import errors when refactoring

**Pattern:**
```python
# Inline import to avoid circular dependency (BAD)
def my_view(request):
    from apps.teams.models import Team  # Should be at top!
    team = Team.objects.get(id=1)
```

**What to Do:**

**1. Identify Circular Dependencies:**
```bash
# Find all inline imports
grep -r "^\s*from apps.teams" apps/teams/ | grep -v "^from apps.teams"

# Use import analyzer
pip install importlab
importlab --tree apps/teams/
```

**2. Apply Proper Layering:**

**Layer 1: Models** (NO imports from views/forms/services)
```python
# apps/teams/models/team.py
from django.db import models
# ✅ Can import from django, common utils
# ❌ Cannot import from views, forms, services
```

**Layer 2: Forms, Validators** (import from models only)
```python
# apps/teams/forms.py
from apps.teams.models import Team
from apps.teams.validators import validate_team_name
# ✅ Can import models, validators
# ❌ Cannot import from views, services
```

**Layer 3: Services** (import from models, forms)
```python
# apps/teams/services/team_service.py
from apps.teams.models import Team
from apps.teams.forms import TeamCreationForm
# ✅ Can import models, forms
# ❌ Cannot import from views
```

**Layer 4: Views, API** (import from all lower layers)
```python
# apps/teams/views/create.py
from apps.teams.models import Team
from apps.teams.forms import TeamCreationForm
from apps.teams.services import team_service
# ✅ Can import everything
```

**Layer 5: Signals, Tasks** (import from all layers - careful!)

**3. Use TYPE_CHECKING for Type Hints:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.teams.models import Team  # Only for type checker
    
def process_team(team: 'Team') -> None:  # String reference
    # Actual import when needed
    from apps.teams.models import Team
```

**4. Use String References for ForeignKey:**
```python
class TeamMembership(models.Model):
    team = models.ForeignKey('teams.Team', on_delete=CASCADE)  # String ref
    user = models.ForeignKey('user_profile.UserProfile', on_delete=CASCADE)
```

**5. Move Related Logic:**
- If models import from views for `related_name`, refactor
- Extract shared code to separate utils module
- Break tight coupling

**6. Fix All Inline Imports:**
- Move imports to top of file
- If circular error occurs, apply above solutions
- Document why certain patterns used

**Testing:**
- All modules import successfully ✓
- No inline imports remain (verify with grep) ✓
- Import speed test (should be faster) ✓
- No circular import errors ✓

**Expected Outcome:**
- Clean import structure
- Better architecture
- Faster module loading
- Easier refactoring

---

### 🎯 SPRINT 3: Code Quality & Standards (Week 5-6)

#### **TASK 3.1: Standardize Error Handling**
**Priority:** 🟠 HIGH  
**Effort:** 10 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #9

**Problem:**
- Mix of exceptions, messages, redirects, JSON responses
- Inconsistent user experience
- API consumers confused

**What to Do:**

**1. Define Error Handling Standards:**

**For Web Views:**
```python
# Use Django messages framework
def team_edit_view(request, team_id):
    try:
        team = Team.objects.get(id=team_id)
        # ... validation ...
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('teams:edit', team_id=team_id)
    except Team.DoesNotExist:
        messages.error(request, "Team not found")
        return redirect('teams:list')
    
    messages.success(request, "Team updated successfully")
    return redirect('teams:detail', team_id=team_id)
```

**For API Views (DRF):**
```python
from rest_framework.exceptions import ValidationError, NotFound

class TeamAPIView(APIView):
    def post(self, request):
        try:
            team = create_team(request.data)
        except ValidationError as e:
            return Response({
                'success': False,
                'errors': e.detail,
                'code': 'VALIDATION_ERROR'
            }, status=400)
        except PermissionDenied:
            return Response({
                'success': False,
                'errors': {'detail': 'Permission denied'},
                'code': 'PERMISSION_DENIED'
            }, status=403)
        
        return Response({
            'success': True,
            'data': TeamSerializer(team).data
        }, status=201)
```

**For AJAX Views:**
```python
def check_team_name_ajax(request):
    try:
        validate_team_name(request.GET.get('name'))
    except ValidationError as e:
        return JsonResponse({
            'ok': False,
            'error': str(e),
            'field': 'name'
        })
    
    return JsonResponse({'ok': True})
```

**2. Create Error Handler Decorators:**
```python
# apps/teams/decorators.py

def handle_team_errors(view_func):
    """Decorator for consistent error handling in team views."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Team.DoesNotExist:
            messages.error(request, "Team not found")
            return redirect('teams:list')
        except PermissionDenied:
            messages.error(request, "You don't have permission")
            return redirect('teams:detail', team_id=kwargs.get('team_id'))
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect(request.path)
    return wrapper

# Usage:
@handle_team_errors
def team_edit_view(request, team_id):
    team = Team.objects.get(id=team_id)  # Can raise DoesNotExist
    # ... rest of view
```

**3. Update All Views:**
- Web views: Use messages framework + decorators
- API views: Standardize JSON response structure
- AJAX views: Consistent `{ok: bool, error: str}` format

**4. Create Custom Exception Classes:**
```python
# apps/teams/exceptions.py

class TeamException(Exception):
    """Base exception for team-related errors."""
    pass

class TeamFullError(TeamException):
    """Raised when team roster is full."""
    default_message = "Team roster is full"

class InviteExpiredError(TeamException):
    """Raised when trying to use expired invite."""
    default_message = "This invite has expired"
```

**Testing:**
- Web view errors show in messages ✓
- API errors return standard JSON ✓
- AJAX errors return consistent format ✓
- Error pages user-friendly ✓

**Expected Outcome:**
- Consistent error handling
- Better user experience
- Easier API integration
- Clear error messages

---

#### **TASK 3.2: Remove Duplicate Forms**
**Priority:** 🟠 HIGH  
**Effort:** 4 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #6

**Problem:**
- `TeamEditForm` defined in TWO places with different fields
- `apps/teams/forms.py` - 8 fields
- `apps/teams/views/manage_console.py` - 6 fields (different!)

**What to Do:**

**1. Compare Both Forms:**
- Identify which fields are in both
- Identify unique fields
- Determine canonical field list

**2. Create Single Canonical Form:**
```python
# apps/teams/forms.py - KEEP THIS ONE

class TeamEditForm(forms.ModelForm):
    """THE canonical team edit form."""
    
    class Meta:
        model = Team
        fields = [
            'name',
            'tag', 
            'description',
            'logo',
            'banner',
            'region',
            'twitter',
            'instagram',
            'is_recruiting',
            'show_roster_publicly',
        ]  # All fields from both forms
        
    def clean_name(self):
        # Unified validation
        name = self.cleaned_data['name']
        validate_team_name(name)
        return name
```

**3. Delete Duplicate Form:**
- Remove `TeamEditForm` from `views/manage_console.py`
- Update imports in manage_console.py
- Test manage console still works

**4. Update All Uses:**
```bash
# Find all uses
grep -r "TeamEditForm" apps/teams/

# Update imports
from apps.teams.forms import TeamEditForm
```

**Testing:**
- Team edit page loads ✓
- All fields present ✓
- Form submission works ✓
- Validation works ✓

**Expected Outcome:**
- Single source of truth for team edit form
- Consistent editing experience
- -30 lines of duplicate code

---

#### **TASK 3.3: Add Type Hints to Core Functions**
**Priority:** 🟡 MEDIUM  
**Effort:** 12 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #11

**Problem:**
- 90% of code lacks type annotations
- No IDE autocomplete
- Difficult to understand function signatures

**What to Do:**

**1. Install Type Checking Tools:**
```bash
pip install mypy django-stubs djangorestframework-stubs
```

**2. Add Types to Service Layer (High Impact):**

Before:
```python
def get_team_members(team, status=None, role=None):
    qs = team.memberships.all()
    if status:
        qs = qs.filter(status=status)
    if role:
        qs = qs.filter(role=role)
    return qs
```

After:
```python
from typing import Optional
from django.db.models import QuerySet

def get_team_members(
    team: Team,
    status: Optional[str] = None,
    role: Optional[str] = None
) -> QuerySet[TeamMembership]:
    """
    Get team members filtered by status and/or role.
    
    Args:
        team: Team instance
        status: Membership status ('ACTIVE', 'PENDING', 'KICKED', 'LEFT')
        role: Member role ('owner', 'captain', 'manager', 'player', 'substitute')
    
    Returns:
        QuerySet of TeamMembership objects
        
    Example:
        >>> team = Team.objects.get(slug='my-team')
        >>> active_players = get_team_members(team, status='ACTIVE', role='player')
    """
    qs: QuerySet[TeamMembership] = team.memberships.all()
    if status:
        qs = qs.filter(status=status)
    if role:
        qs = qs.filter(role=role)
    return qs
```

**3. Priority Order:**
- ✅ Service layer functions (highest impact)
- ✅ Public API endpoints
- ✅ Form validation methods
- ✅ View functions (signatures only)
- ✅ Model methods

**4. Configure mypy:**
```ini
# mypy.ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False  # Start lenient
ignore_missing_imports = True

[mypy-apps.teams.services.*]
disallow_untyped_defs = True  # Strict for services
```

**5. Add to CI Pipeline:**
```bash
# Run mypy in CI
mypy apps/teams/services/ apps/teams/api/
```

**Testing:**
- mypy runs without errors ✓
- IDE autocomplete works ✓
- Type hints accurate ✓

**Expected Outcome:**
- Better IDE support
- Catch type errors before runtime
- Improved code documentation
- Easier onboarding

---

#### **TASK 3.4: Clean Up Dead Code**
**Priority:** 🟡 MEDIUM  
**Effort:** 8 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issues #15, #16, #17

**Problem:**
- Deprecated models still in use (8 places)
- 40+ files with unused imports
- 80+ blocks of commented-out code
- Mixed quote styles

**What to Do:**

**1. Remove Deprecated Code:**

Find:
```python
# apps/teams/models/_legacy.py
# DEPRECATED: Use TeamAnalytics instead
class LegacyTeamStats(models.Model):
    # ... 200 lines ...
```

Check usage:
```bash
grep -r "LegacyTeamStats" apps/
# Found in 8 files
```

**If still used:**
- Create migration plan to TeamAnalytics
- Update 8 files to use new model
- Add data migration script
- Delete LegacyTeamStats model

**If NOT used:**
- Create migration to drop table
- Delete model class
- Remove from admin

**2. Remove Unused Imports (Automated):**
```bash
pip install autoflake

# Remove unused imports
autoflake --remove-all-unused-imports --in-place apps/teams/**/*.py

# Review changes
git diff apps/teams/

# Commit if looks good
```

**3. Delete Commented Code:**
```bash
# Find commented code blocks
grep -r "^\s*#.*TODO\|^\s*# Old code" apps/teams/

# Manual review (don't auto-delete - might be important)
# Delete if:
# - Older than 6 months
# - No TODO with action item
# - Redundant with current implementation
```

**4. Standardize Quote Style:**
```bash
# Use Black formatter (automatically fixes)
pip install black
black apps/teams/

# Enforces single quotes and PEP 8
```

**Testing:**
- All tests still pass ✓
- No unused imports (verify with flake8) ✓
- Code formatted consistently ✓

**Expected Outcome:**
- -800 lines of dead code
- Cleaner codebase
- Consistent formatting
- Easier navigation

---

### 🎯 SPRINT 4: Documentation & Testing (Week 7-8)

#### **TASK 4.1: Add Docstrings to All Public Functions**
**Priority:** 🟡 MEDIUM  
**Effort:** 16 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #13

**Problem:**
- 156 functions, only 23 have docstrings (15%)
- 133 functions undocumented (85%)
- Difficult to understand code purpose

**What to Do:**

**1. Use Google Style Docstrings:**
```python
def calculate_team_rank_score(team: Team, criteria: dict) -> int:
    """
    Calculate team ranking score based on multiple criteria.
    
    The score is calculated using the team's total points multiplied by
    a configurable multiplier, plus bonuses from achievements.
    
    Args:
        team: Team instance to calculate score for
        criteria: Dictionary with 'multiplier' key (default: 1.0)
            Example: {'multiplier': 1.5, 'bonus_enabled': True}
    
    Returns:
        Integer score representing team rank
        
    Raises:
        ValueError: If team.total_points is negative
        
    Example:
        >>> team = Team.objects.get(slug='my-team')
        >>> criteria = {'multiplier': 1.5}
        >>> score = calculate_team_rank_score(team, criteria)
        >>> print(score)
        7500
        
    Note:
        Achievement bonus is capped at 1000 points
    """
    if team.total_points < 0:
        raise ValueError("Team points cannot be negative")
        
    base = team.total_points or 0
    multiplier = criteria.get('multiplier', 1.0)
    bonus = min(get_achievement_bonus(team), 1000)  # Cap at 1000
    return int((base * multiplier) + bonus)
```

**2. Priority Order:**
```
1. Service layer (business logic) - CRITICAL
2. API views (external interface) - HIGH  
3. Form validation methods - HIGH
4. Model methods - MEDIUM
5. View functions - MEDIUM
6. Utility functions - LOW
```

**3. Docstring Template:**
```python
"""
Brief one-line description.

Detailed multi-line description if needed. Explain what, why, and how.
Include algorithm explanation for complex logic.

Args:
    param1: Description with type and constraints
    param2: Description with default value if applicable

Returns:
    Description of return value and type

Raises:
    ExceptionType: When this exception is raised
    
Example:
    >>> # Simple usage example
    >>> result = function(param1, param2)
    
Note:
    Any important caveats or side effects
    
See Also:
    related_function: Related functionality
"""
```

**4. Generate Docstring Report:**
```bash
# Check current coverage
pydocstyle apps/teams/services/ --count

# Goal: 100% coverage for services/
```

**5. Add to CI Pipeline:**
```bash
# Fail CI if missing docstrings in services/
pydocstyle apps/teams/services/ --count || exit 1
```

**Testing:**
- All public functions documented ✓
- Docstrings follow Google style ✓
- Examples in docstrings work ✓
- pydocstyle passes ✓

**Expected Outcome:**
- Self-documenting code
- Better onboarding
- Easier maintenance
- API documentation generated automatically

---

#### **TASK 4.2: Increase Test Coverage to 70%**
**Priority:** 🟠 HIGH  
**Effort:** 20 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Code Metrics

**Current Coverage:**
- Overall: 42%
- Models: 65% (good)
- Services: 55% (needs work)
- Views: 25% (poor)
- API: 30% (poor)

**Goal: 70% Overall**

**What to Do:**

**1. Set Up Coverage Tracking:**
```bash
pip install coverage pytest-cov

# Run tests with coverage
pytest --cov=apps.teams --cov-report=html --cov-report=term

# View report
open htmlcov/index.html
```

**2. Write Missing Tests (Priority Order):**

**Services (55% → 85%):**
```python
# tests/services/test_team_service.py

def test_create_team_success():
    """Test successful team creation."""
    data = {
        'name': 'Test Team',
        'tag': 'TT',
        'game': 'valorant',
        'region': 'NA',
    }
    team = team_service.create_team(user=user, data=data)
    
    assert team.name == 'Test Team'
    assert team.tag == 'TT'
    assert team.captain == user
    assert TeamMembership.objects.filter(team=team, user=user).exists()

def test_create_team_duplicate_name():
    """Test team creation fails with duplicate name."""
    Team.objects.create(name='Existing Team', ...)
    
    with pytest.raises(ValidationError) as exc:
        team_service.create_team(user=user, data={'name': 'Existing Team'})
    
    assert 'already taken' in str(exc.value)

def test_create_team_invalid_tag():
    """Test team creation fails with invalid tag."""
    with pytest.raises(ValidationError):
        team_service.create_team(user=user, data={'tag': 'invalid_tag'})
```

**Views (25% → 70%):**
```python
# tests/views/test_team_views.py

def test_team_list_view(client):
    """Test team list view renders correctly."""
    Team.objects.create(name='Team 1', is_public=True)
    Team.objects.create(name='Team 2', is_public=True)
    
    response = client.get(reverse('teams:list'))
    
    assert response.status_code == 200
    assert 'Team 1' in response.content.decode()
    assert 'Team 2' in response.content.decode()

def test_team_create_view_requires_login(client):
    """Test team creation requires authentication."""
    response = client.get(reverse('teams:create'))
    assert response.status_code == 302  # Redirect to login

def test_team_edit_requires_permission(client, team, user):
    """Test non-captain cannot edit team."""
    client.force_login(user)  # User not in team
    response = client.post(reverse('teams:edit', args=[team.id]), {})
    assert response.status_code == 403  # Permission denied
```

**API (30% → 70%):**
```python
# tests/api/test_team_api.py

def test_create_team_api(api_client, user):
    """Test team creation via API."""
    api_client.force_authenticate(user=user)
    
    data = {
        'name': 'API Team',
        'tag': 'API',
        'game': 'valorant',
    }
    
    response = api_client.post('/api/teams/', data)
    
    assert response.status_code == 201
    assert response.data['success'] is True
    assert Team.objects.filter(name='API Team').exists()

def test_create_team_api_validation_error(api_client, user):
    """Test API returns validation errors."""
    api_client.force_authenticate(user=user)
    
    response = api_client.post('/api/teams/', {'name': 'A'})  # Too short
    
    assert response.status_code == 400
    assert response.data['success'] is False
    assert 'errors' in response.data
```

**3. Coverage Goals by Module:**
- `services/`: 85%+
- `models/`: 80%+
- `api/`: 70%+
- `views/`: 70%+
- `forms/`: 80%+
- `validators/`: 90%+

**4. Add Coverage to CI:**
```yaml
# .github/workflows/tests.yml
- name: Run tests with coverage
  run: |
    pytest --cov=apps.teams --cov-fail-under=70
```

**Testing:**
- Coverage >= 70% overall ✓
- All critical paths tested ✓
- Edge cases covered ✓
- Tests pass in CI ✓

**Expected Outcome:**
- 42% → 70% coverage
- Fewer production bugs
- Confident refactoring
- Regression prevention

---

**END OF PHASE 1**

**Phase 1 Summary:**
- ✅ 12 critical issues fixed
- ✅ Code duplication reduced by 35%
- ✅ Performance improved (page load < 1s)
- ✅ Test coverage 42% → 70%
- ✅ Clean, maintainable codebase

**Ready for Phase 2: High Priority Improvements** →

