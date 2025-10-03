# Admin Reorganization Plan

**Date**: Current Session  
**Status**: In Progress  
**Estimated Time**: 2-3 hours

## Executive Summary

Reorganize the tournament admin interface to improve maintainability, remove UI-preference models from admin, fix any naming issues, and create a professional, logically-grouped admin experience.

## Current State Analysis

### Admin Structure

**Old Monolithic File**:
- `apps/tournaments/admin.py` (811 lines)
- Contains Phase 1 inline and standalone admin classes
- Phase 1 models: Schedule, Capacity, Finance, Media, Rules, Archive
- Well-structured with fieldsets and readonly fields

**New Modular Structure**:
- `apps/tournaments/admin/` folder with separate modules:
  - `__init__.py` - Import hub
  - `matches.py` - MatchAdmin ✅ (registered via @admin.register)
  - `brackets.py` - BracketAdmin (form + admin class)
  - `disputes.py` - MatchDisputeAdmin ✅ (registered)
  - `attendance.py` - MatchAttendanceAdmin ✅ (registered)
  - `payments.py` - PaymentVerification admin ✅ (registered)
  - `registrations.py` - Empty file
  - `userprefs.py` - ❌ UI preferences (should be removed)
  - `components.py` - Inlines and filters
  - `hooks.py` - Extra wiring
  - `base.py` - Safe extensions

### Models Currently in Admin

**Core Tournament Models**:
- ✅ Tournament (with 6 Phase 1 inlines)
- ✅ TournamentSchedule (Phase 1)
- ✅ TournamentCapacity (Phase 1)
- ✅ TournamentFinance (Phase 1)
- ✅ TournamentMedia (Phase 1)
- ✅ TournamentRules (Phase 1)
- ✅ TournamentArchive (Phase 1)

**Competition Models**:
- ✅ Match (admin/matches.py)
- ✅ Bracket (admin/brackets.py)
- ✅ MatchDispute (admin/disputes.py)
- ✅ MatchAttendance (admin/attendance.py)

**Participant Models**:
- ⏳ Registration (admin/registrations.py is empty - need to check if registered elsewhere)
- ⏳ RegistrationRequest
- ⏳ CaptainApproval

**Finance Models**:
- ✅ PaymentVerification (admin/payments.py)

**UI Preference Models** ❌ (SHOULD NOT BE IN ADMIN):
- ❌ CalendarFeedToken (userprefs.py)
- ❌ SavedMatchFilter (userprefs.py)
- ❌ PinnedTournament (userprefs.py)

### Issues Identified

1. **UI Preferences in Admin** ❌
   - `CalendarFeedToken`, `SavedMatchFilter`, `PinnedTournament` are user interface preferences
   - These should be managed via API/frontend, not Django admin
   - Need to remove from admin registration

2. **Empty Registration Admin**:
   - `admin/registrations.py` is empty
   - Need to check if Registration has admin elsewhere
   - May need to create proper admin

3. **Duplicate Admin Files**:
   - Old monolithic `admin.py` (811 lines)
   - New modular `admin/` folder
   - Need to deprecate old file, keep modular structure

4. **No Admin for Some Models**:
   - RegistrationRequest
   - CaptainApproval
   - Evidence (match evidence)
   - Events (tournament events)

## Reorganization Strategy

### Phase 1: Remove UI Preference Models (30 minutes)

**Action**: Remove CalendarFeedToken, SavedMatchFilter, PinnedTournament from admin

**Files to Modify**:
- `apps/tournaments/admin/userprefs.py` - DELETE or comment out registrations
- `apps/tournaments/admin/__init__.py` - Remove userprefs import

**Rationale**:
- These are user preferences, not tournament data
- Should be managed via frontend/API, not admin panel
- Clutters admin with non-administrative models

### Phase 2: Create Missing Admin Classes (1 hour)

**Registration Admin** (admin/registrations.py):
```python
@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'user', 'team', 'status', 'created_at', 'payment_status')
    list_filter = ('status', 'tournament', 'created_at')
    search_fields = ('user__username', 'team__name', 'tournament__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Registration Info', {
            'fields': ('tournament', 'user', 'team', 'status')
        }),
        ('Payment', {
            'fields': ('payment_status', 'payment_verified_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
```

**RegistrationRequest Admin** (admin/registrations.py):
```python
@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'user', 'status', 'requested_at', 'approved_by')
    list_filter = ('status', 'tournament')
    search_fields = ('user__username', 'tournament__name')
    actions = ['approve_requests', 'reject_requests']
```

**CaptainApproval Admin** (admin/registrations.py):
```python
@admin.register(CaptainApproval)
class CaptainApprovalAdmin(admin.ModelAdmin):
    list_display = ('registration', 'player', 'status', 'created_at')
    list_filter = ('status', 'registration__tournament')
    search_fields = ('player__username', 'registration__team__name')
```

### Phase 3: Deprecate Old admin.py (15 minutes)

**Action**: Convert old `admin.py` to simple import hub

**New content**:
```python
"""
Django Admin Configuration for Tournament Models

DEPRECATED: This file is deprecated. All admin classes have been moved to
the apps/tournaments/admin/ modular structure.

This file now serves only as an import hub for backward compatibility.
"""

import warnings

warnings.warn(
    "apps/tournaments/admin.py is deprecated. "
    "Import from apps.tournaments.admin.* modules instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import all admin classes from modular structure
from .admin.tournaments import TournamentAdmin  # noqa
from .admin.matches import MatchAdmin  # noqa
from .admin.brackets import BracketAdmin  # noqa
from .admin.disputes import MatchDisputeAdmin  # noqa
from .admin.attendance import MatchAttendanceAdmin  # noqa
from .admin.registrations import *  # noqa
from .admin.payments import *  # noqa

__all__ = [
    'TournamentAdmin',
    'MatchAdmin',
    'BracketAdmin',
    'MatchDisputeAdmin',
    'MatchAttendanceAdmin',
]
```

### Phase 4: Create tournaments.py in admin/ folder (30 minutes)

**Action**: Move Phase 1 admin classes from old admin.py to admin/tournaments.py

**Files to Create**:
- `apps/tournaments/admin/tournaments.py` (copy from old admin.py, lines 1-320)

**Content**: All inline and standalone Phase 1 admin classes

### Phase 5: Verify and Test (30 minutes)

**Actions**:
1. Run Django system check
2. Start Django server
3. Access admin interface
4. Verify all models appear correctly
5. Test inline functionality
6. Verify model grouping

## Expected Admin Structure After Reorganization

### TOURNAMENTS Section
- **Tournaments** (with 6 Phase 1 inlines)
  - Schedule
  - Capacity
  - Finance
  - Media
  - Rules
  - Archive

### PARTICIPANTS & REGISTRATION Section
- **Registrations**
- **Registration Requests**
- **Captain Approvals**

### COMPETITION MANAGEMENT Section
- **Matches**
- **Brackets**
- **Match Disputes**
- **Match Attendance**

### FINANCE Section
- **Payment Verifications**

### REMOVED FROM ADMIN
- ❌ Calendar Feed Tokens (user preference)
- ❌ Saved Match Filters (user preference)
- ❌ Pinned Tournaments (user preference)

## Benefits

1. **Cleaner Admin Interface**
   - Only administrative data, no UI preferences
   - Logical grouping of related models
   - Professional presentation

2. **Better Maintainability**
   - Modular structure (one file per concern)
   - Easy to find and edit specific admin classes
   - Clear separation of concerns

3. **Improved Developer Experience**
   - Clear import paths
   - No 811-line monolithic files
   - Easy to add new admin classes

4. **Better UX**
   - Tournament admins see relevant models only
   - Logical grouping reduces cognitive load
   - Fast access to frequently-used models

## Migration Path

1. **Immediate** (this session):
   - Remove UI preference models from admin
   - Create missing admin classes
   - Move Phase 1 classes to admin/tournaments.py
   - Deprecate old admin.py

2. **Future** (optional):
   - Add custom admin actions (bulk operations)
   - Add admin dashboard widgets
   - Add export functionality
   - Add import functionality

## Files to Modify

### Delete/Deprecate
- ❌ `apps/tournaments/admin/userprefs.py` (delete or disable)
- ⚠️ `apps/tournaments/admin.py` (deprecate, convert to import hub)

### Create
- ✅ `apps/tournaments/admin/tournaments.py` (Phase 1 classes)

### Modify
- ✅ `apps/tournaments/admin/__init__.py` (remove userprefs import)
- ✅ `apps/tournaments/admin/registrations.py` (add admin classes)

## Success Criteria

- [ ] UI preference models removed from admin
- [ ] All relevant tournament models have admin classes
- [ ] Old admin.py deprecated with clear warning
- [ ] Admin interface loads without errors
- [ ] All inlines work correctly
- [ ] Models grouped logically
- [ ] System check passes (0 issues)
- [ ] Documentation updated

## Timeline

- Phase 1 (Remove UI prefs): 30 minutes
- Phase 2 (Create missing admins): 1 hour
- Phase 3 (Deprecate old file): 15 minutes
- Phase 4 (Create tournaments.py): 30 minutes
- Phase 5 (Test): 30 minutes
- **Total**: ~2.75 hours

## Next Steps After Completion

1. Model Cleanup (4-6 hours)
2. UI/UX Improvements (4-6 hours)
3. Deployment (1 hour)

---

**Status**: Ready to begin implementation  
**Priority**: High (user-requested enhancement before deployment)  
**Risk**: Low (isolated admin changes, no model migrations needed)
