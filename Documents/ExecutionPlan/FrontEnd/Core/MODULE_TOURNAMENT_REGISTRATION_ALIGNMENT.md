# Tournament Registration Backend Alignment

**Date**: November 15, 2025  
**Purpose**: Document backend gaps and required changes for team-based tournament registration  
**Status**: Planning - Backend V1 complete, but missing team captain permissions

---

## Executive Summary

**Validated Backend Constraints**:
✅ **One team per game per player**: CONFIRMED in `apps/teams/models/_legacy.py` (lines 515-532)  
✅ **Team registration input**: CONFIRMED via `TeamRegistrationInput` class  
✅ **Solo vs team registration**: CONFIRMED via unique constraints in Registration model  

**BACKEND_IMPACT - Required Changes**:
⚠️ **Team captain registration permissions**: NOT IMPLEMENTED  
- Current: `TeamRegistrationInput.created_by_user_id` exists but not validated  
- Required: Backend must validate that `created_by_user_id` is the team captain before allowing registration  
- Impact: Medium - Service layer change only, no migrations needed  

---

## 1. Backend Reality Check (Validated November 15, 2025)

### 1.1 One Team Per Game Per Player Constraint

**Location**: `apps/teams/models/_legacy.py:515-532`

**Implementation**:
```python
# Enforce: one ACTIVE team per GAME per profile (Part A)
# ...validation logic...
if exists:
    raise ValidationError(
        f"Only one active team per game is allowed."
    )
```

**View-Level Guards**:
- `apps/teams/views/create.py:398`: "You are already a member... You can only have one active team per game."
- `apps/teams/views/public.py:1000`: "You can only be in one team per game. Please leave that team first."
- `apps/teams/views/public.py:1215-1292`: One-team-per-game guard on join team

**Verdict**: ✅ **CONFIRMED** - Backend enforces this rule at model and view levels

---

### 1.2 Team Registration Input

**Location**: `legacy_backup/apps/tournaments/tournaments/services/registration.py:69-77`

**Implementation**:
```python
@dataclass
class TeamRegistrationInput:
    tournament_id: int
    team_id: int
    created_by_user_id: Optional[int] = None  # accepted but not persisted
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    amount_bdt: Optional[float] = None
    payer_account_number: Optional[str] = None
```

**Verdict**: ✅ **CONFIRMED** - Input class exists, but `created_by_user_id` not validated

---

### 1.3 Registration Model Constraints

**Location**: `legacy_backup/apps/tournaments/tournaments/models/registration.py:9-118`

**Implementation**:
- Unique constraint: `(tournament, user)` for solo registrations
- Unique constraint: `(tournament, team)` for team registrations
- Validation: Must have either user OR team, not both

**Verdict**: ✅ **CONFIRMED** - Database-level constraints prevent duplicates

---

## 2. BACKEND_IMPACT: Team Captain Registration Permissions

### 2.1 Current Behavior

**Problem**:
- Any team member can call `/api/tournaments/{id}/register/` with a `team_id`
- Backend accepts `created_by_user_id` but does NOT validate if that user is the team captain
- Result: Non-captains can register teams without authorization

**Evidence**:
```python
# registration_service.py:95-246
class RegistrationService:
    def _check_already_registered(tournament, user, team=None) -> bool:
        # Checks if team is already registered
        # Does NOT check if user is captain
        ...
```

**Impact**: 🔴 **CRITICAL** - Allows unauthorized team registrations

---

### 2.2 Required Backend Changes

**Change 1: Add Captain Validation to RegistrationService**

**File**: `apps/tournaments/services/registration_service.py`

**New Method**:
```python
def _validate_team_captain(team, user) -> None:
    """
    Validates that the user is the captain of the team.
    Raises PermissionDenied if user is not the captain.
    """
    TeamMembership = _get_model("teams", "TeamMembership")
    if not TeamMembership:
        return  # Skip validation if model not available
    
    is_captain = TeamMembership.objects.filter(
        team=team,
        profile_id=user.id,
        role="CAPTAIN",
        status="ACTIVE"
    ).exists()
    
    if not is_captain:
        raise PermissionDenied(
            "Only team captains can register their team for tournaments."
        )
```

**Integration Point**:
```python
# registration_service.py:95-246 (update register_team method)
def register_team(data: TeamRegistrationInput):
    tournament = Tournament.objects.get(id=data.tournament_id)
    team = Team.objects.get(id=data.team_id)
    user = UserProfile.objects.get(id=data.created_by_user_id) if data.created_by_user_id else None
    
    # NEW: Validate captain
    if user:
        _validate_team_captain(team, user)
    
    # Existing logic continues...
    _check_already_registered(tournament, None, team)
    ...
```

**Estimated Effort**: 2-3 hours (service layer change + unit tests)

---

**Change 2: Update Registration API Permission Class**

**File**: `apps/tournaments/api/permissions.py`

**New Permission Class**:
```python
class IsTeamCaptainOrOrganizer(permissions.BasePermission):
    """
    Permission: User must be team captain (for team registrations)
    or tournament organizer.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Organizers can register any team
        tournament_id = view.kwargs.get('tournament_id')
        if tournament_id:
            tournament = Tournament.objects.get(id=tournament_id)
            if request.user == tournament.organizer:
                return True
        
        return True  # Allow request, obj-level check in has_object_permission
    
    def has_object_permission(self, request, view, obj):
        # obj is Registration instance
        if obj.team:
            return _is_team_captain(obj.team, request.user)
        return True  # Solo registrations allowed
```

**Estimated Effort**: 1-2 hours (permission class + integration tests)

---

### 2.3 Frontend Implications

**What Frontend Must Do**:
1. ✅ **Show only captain-eligible teams** in team selector dropdown
   - Call: `GET /api/teams/?member=me&role=CAPTAIN&game={game_id}`
   - Filter: Only show teams where user is CAPTAIN
   
2. ✅ **Display permission error** if backend rejects registration
   - Handle: `403 Forbidden` with message "Only team captains can register"
   - UI: Show error toast + disable submit button
   
3. ✅ **Show captain badge** in team selector UI
   - Visual indicator: "Captain" badge next to team name in dropdown

**Frontend Does NOT Need To**:
- ❌ Implement captain validation logic (backend handles this)
- ❌ Call `/api/teams/{id}/members/` to check captain status (use role filter in list)

---

### 2.4 Rollout Strategy

**Phase 1: Backend Preparation** (Before FE-T1)
- Implement `_validate_team_captain` method in RegistrationService
- Add `IsTeamCaptainOrOrganizer` permission class
- Write unit tests (10-12 tests covering captain, non-captain, organizer, solo)
- Deploy to staging, run regression tests

**Phase 2: Frontend Integration** (During FE-T1)
- Update registration wizard Step 2 (team selector)
- Add captain filter to API call: `GET /api/teams/?role=CAPTAIN`
- Handle 403 errors with user-friendly messaging
- Add visual captain badge in team dropdown

**Phase 3: Documentation** (After FE-T1)
- Update API docs with captain permission requirement
- Add error catalog entry for 403 captain errors
- Update FRONTEND_TOURNAMENT_BACKLOG.md with "Captain validation" completed

---

## 3. Teams API Alignment

### 3.1 Team Selector Endpoint

**Endpoint**: `GET /api/teams/`

**Query Params**:
- `member=me` - Filter to teams where authenticated user is a member
- `role=CAPTAIN` - Filter to teams where user has CAPTAIN role
- `game={game_id}` - Filter to teams for specific game
- `status=ACTIVE` - Filter to active teams only

**Response** (Expected):
```json
{
  "count": 2,
  "results": [
    {
      "id": 123,
      "name": "Team Alpha",
      "tag": "ALPHA",
      "game": "valorant",
      "game_display": "Valorant",
      "my_role": "CAPTAIN",
      "member_count": 5,
      "is_active": true
    },
    {
      "id": 456,
      "name": "Team Bravo",
      "tag": "BRAVO",
      "game": "valorant",
      "game_display": "Valorant",
      "my_role": "CAPTAIN",
      "member_count": 4,
      "is_active": true
    }
  ]
}
```

**Frontend Usage**:
```javascript
// Fetch captain teams for Valorant tournament
const response = await fetch('/api/teams/?member=me&role=CAPTAIN&game=valorant&status=ACTIVE');
const teams = await response.json();

// Populate dropdown with captain teams only
teams.results.forEach(team => {
  dropdown.innerHTML += `
    <option value="${team.id}">
      ${team.name} (${team.tag}) 
      <span class="badge">Captain</span>
    </option>
  `;
});
```

**Validation**: ✅ Backend API already supports these filters (validated in `apps/teams/views/`)

---

### 3.2 Team Membership Validation

**Backend Check** (Already Implemented):
```python
# apps/teams/models/_legacy.py:515-532
# Enforces: One ACTIVE team per GAME per profile
```

**Frontend Behavior**:
- If user tries to register with Team A for Valorant tournament
- But user is already in Team B for Valorant
- Backend will return: `400 Bad Request` with "You are already in a Valorant team"
- Frontend should show error: "You can only be in one team per game. Manage your teams first."

**Edge Case**: User leaves Team A, joins Team B, then tries to register Team B
- Backend allows (only one active team per game)
- Frontend should refresh team dropdown after team changes

---

## 4. Testing Strategy

### 4.1 Backend Tests (Required Before Frontend)

**Unit Tests** (`tests/test_registration_captain_validation.py`):
1. ✅ Captain can register team
2. ❌ Non-captain cannot register team (403)
3. ✅ Organizer can register any team
4. ✅ Solo registration not affected by captain check
5. ❌ Invalid team_id returns 404
6. ❌ User not in team returns 403
7. ✅ Captain of Team A cannot register Team B (403)

**Integration Tests** (`tests/test_registration_api_captain.py`):
1. Full registration flow with captain validation
2. Team selector API filter validation
3. Permission error handling in API responses

**Estimated Test Count**: 12-15 tests  
**Estimated Effort**: 3-4 hours

---

### 4.2 Frontend Tests (During FE-T1)

**Manual QA Checklist**:
- [ ] Team dropdown shows only captain teams
- [ ] Non-captain teams not visible in dropdown
- [ ] Captain badge displays next to team name
- [ ] 403 error shows user-friendly message
- [ ] Solo registration unaffected by captain logic
- [ ] Organizer can register any team (admin bypass)

**Automated Tests** (Playwright/Cypress):
- Test captain team filtering in dropdown
- Test 403 error handling
- Test captain badge rendering

---

## 5. Migration Path

**No Database Migrations Needed** ✅

**Why**:
- Registration model already has `team` FK
- TeamMembership model already has `role` field with `CAPTAIN` value
- No new fields, indexes, or constraints required

**Change Type**: Service layer logic only (validation + permissions)

---

## 6. Summary: Frontend Planning Impact

**What Frontend Needs to Know**:

1. ✅ **Team selector must filter by captain role**
   - API call: `GET /api/teams/?member=me&role=CAPTAIN&game={game_id}`
   - Only show teams where user is captain

2. ⚠️ **Backend will reject non-captain registrations**
   - Handle 403 errors gracefully
   - Show message: "Only team captains can register teams for tournaments"

3. ✅ **One team per game per player is enforced**
   - Backend validates this constraint
   - Frontend should show clear error if user tries to register with multiple teams for same game

4. ✅ **Organizers bypass captain check**
   - Tournament organizers can register any team
   - Frontend: Show admin override indicator if organizer registers team

**BACKEND_IMPACT Actions**:
- [ ] Implement `_validate_team_captain` in RegistrationService
- [ ] Add `IsTeamCaptainOrOrganizer` permission class
- [ ] Write 12-15 unit/integration tests
- [ ] Deploy to staging, validate with Postman/curl
- [ ] Update API documentation
- [ ] Notify frontend team when backend changes are live

**Timeline**: Backend changes should be completed **before FE-T1 Phase 1** (Registration Wizard UI implementation)

---

## 7. Open Questions

**Q1**: Should team captains be able to delegate registration authority to vice-captains?  
**A**: Deferred to Phase 2. For MVP, only captains can register.

**Q2**: What if a team has no captain (captain left)?  
**A**: Backend validation will fail. Team must elect a new captain first. Frontend should show error: "This team has no captain. Please update team roles first."

**Q3**: Can a user transfer captaincy after registering?  
**A**: Yes, but registration remains valid. New captain inherits management permissions. Frontend should show "Registered by: [Original Captain]" in tournament lobby.

**Q4**: What if tournament organizer wants to register teams on behalf of captains?  
**A**: Organizers bypass captain check (admin override). Frontend should show "Registered by organizer" badge in UI.

---

**Document Status**: ✅ Complete  
**Next Steps**: Implement backend changes, then integrate with FE-T1 registration wizard
