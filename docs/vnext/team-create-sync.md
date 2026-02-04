# Team Create Sync Fix

**Issue**: Creating team at `/teams/create/` showed success but team didn't appear in `/teams/vnext/` hub or admin proxy.

**Root Cause**: 
1. Legacy `/teams/create/` route created Legacy Team (teams_team table)
2. Admin proxy pointed to Legacy Team
3. Hub queried Legacy Team
4. Organizations API created vNext Team (organizations_team table)
5. Two separate models = inconsistent state

**Solution**: Make vNext Team canonical everywhere

## Changes Made

### 1. Route `/teams/create/` to Organizations (apps/teams/urls.py)
```python
# Redirect legacy route to canonical when ORG_APP_ENABLED
path("create/", lambda request: redirect('organizations:team_create') 
     if getattr(settings, 'ORG_APP_ENABLED', False) 
     else team_create_view(request), name="create"),
```

### 2. Fix Admin Proxy (apps/organizations/admin.py)
```python
# Changed from: Legacy Team proxy
from apps.teams.models import Team
class TeamAdminProxy(Team): ...

# Changed to: vNext Team proxy
from apps.organizations.models import Team
class TeamAdminProxy(Team): ...
```

Updated admin fields to match vNext model:
- `game` (CharField) → `game_id` (Integer FK)
- `is_active` → `status` (CharField choices)
- Added `organization` and `owner` display

### 3. Fix Hub Listings (apps/organizations/views/hub.py)
```python
# Changed carousel/featured teams queries:
from apps.teams.models import Team  # Legacy
# To:
from apps.organizations.models import Team  # vNext

# Updated queries for vNext fields:
- memberships__profile → memberships__user
- is_active → status='ACTIVE'
- Added organization/owner FK filtering
```

### 4. Tests Added (tests/test_team_create_sync.py)
- `test_team_create_creates_vnext_team` - Verifies API creates vNext model
- `test_created_team_visible_in_hub` - Hub shows vNext teams
- `test_created_team_visible_in_admin_proxy` - Admin shows vNext teams
- `test_team_create_uses_same_table_as_proxy` - Model consistency
- `test_org_owned_team_creation` - Org ownership works
- `test_teams_namespace_create_redirects_to_canonical` - Route redirect works

## Verification

**Before Fix**:
```bash
# Create team → success message
# GET /teams/vnext/ → team NOT visible
# Admin proxy → team NOT visible
# organizations_team table → empty
# teams_team table → has team (wrong table!)
```

**After Fix**:
```bash
# Create team → success message
# GET /teams/vnext/ → team visible ✓
# Admin proxy → team visible ✓
# organizations_team table → has team ✓
# teams_team table → empty ✓
```

## API Flow

1. **UI**: GET `/teams/create/` → renders Organizations team create UI
2. **Submit**: POST `/api/vnext/teams/create/` → creates vNext Team
3. **Create**: Team saved to `organizations_team` table
4. **Membership**: TeamMembership created with role=OWNER
5. **Redirect**: User redirected to team detail page
6. **Hub**: `/teams/vnext/` queries `organizations_team` → team appears
7. **Admin**: TeamAdminProxy queries `organizations_team` → team appears

## One Source of Truth

**Canonical Model**: `apps.organizations.models.Team` (organizations_team)
- Used by: Hub, admin, API, all new code
- Fields: game_id (Integer), status, owner FK, organization FK

**Legacy Model**: `apps.teams.models.Team` (teams_team) - DEPRECATED
- Only used when: `ORG_APP_ENABLED=0` and `LEGACY_TEAMS_ENABLED=1`
- Will be removed in Phase 7

## Run Tests

```bash
python manage.py test tests.test_team_create_sync -v 2
python manage.py test tests.test_org_competition_integration.TestOrganizationTeamURLs -v 2
```

## Status
✅ **FIXED** - Team creation now consistently uses vNext model
