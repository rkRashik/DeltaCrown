# Team Model Authority Resolution

**Date**: 2026-01-30  
**Task**: P4-T1.4 Model Authority Resolution

## Problem Statement

Two Team models exist in the codebase, both targeting the same database table (`teams_team`):

1. **`apps.teams.models.Team`** (Legacy)
2. **`apps.organizations.models.Team`** (vNext)

This created conflicts and import errors during Team Detail page development.

## Investigation Results

### Legacy Team (`apps.teams.models._legacy.Team`)
- **Status**: ACTIVE and WORKING
- **Table**: `teams_team`
- **Fields**: Complete schema with:
  - Social fields: `twitter`, `instagram`, `youtube`, `twitch`
  - All needed FK relationships work correctly
  - Compatible with existing data

### vNext Team (`apps.organizations.models.Team`)
- **Status**: NOT READY for production use
- **Table**: Configured for `teams_team` but has incompatible schema
- **Issues**:
  - Expects fields that don't exist: `organization_id`, `owner_id`, `game_id`, `status`, `visibility`
  - Missing fields that do exist: Many legacy fields
  - Cannot query database without errors

## Resolution Decision

**For Team Detail Page (and other read-only operations):**

Use **`apps.teams.models.Team`** (legacy) as the authoritative model.

### Implementation

1. **Context Builder** (`apps/organizations/services/team_detail_context.py`):
   ```python
   from apps.teams.models import Team  # Using legacy Team model
   ```

2. **Organizations Models** (`apps/organizations/models/__init__.py`):
   ```python
   from apps.teams.models import Team  # Re-export legacy Team
   ```

3. **Related Models FK Updates**:
   - `TeamRanking.team` → `'teams.Team'`
   - `TeamMembership.team` → `'teams.Team'` (related_name: `vnext_memberships`)
   - `TeamInvite.team` → `'teams.Team'` (related_name: `vnext_invites`)
   - `TeamActivityLog.team` → `'teams.Team'`

4. **Related Name Conflicts Resolved**:
   - organizations.TeamMembership uses `vnext_memberships` (legacy uses `memberships`)
   - organizations.TeamInvite uses `vnext_invites` (legacy uses `invites`)

5. **Adapters Updated**:
   - `team_adapter.py`: `VNextTeam = LegacyTeam` (temporary alias)

6. **Admin Adjustments**:
   - TeamRankingAdmin filters adjusted for legacy Team fields
   - vNext TeamAdmin commented out (conflicts with legacy TeamAdmin)

## FK Relationship Verification

**TeamSponsor** (`apps/teams/models/sponsorship.py`):
- ✅ Correctly references `'teams.Team'`
- ✅ Related name: `sponsors`
- ✅ ORM access works: `team.sponsors.all()`

**TeamJoinRequest** (`apps/teams/models/join_request.py`):
- ✅ Correctly references `'teams.Team'`
- ✅ Related name: `join_requests`
- ✅ ORM access works: `team.join_requests.all()`

**TeamInvite** (legacy - `apps/teams/models/invite.py`):
- ✅ References `'teams.Team'`
- ✅ Related name: `invites`
- ✅ ORM access works: `team.invites.all()`

## Social Fields Confirmation

Legacy Team model already has social fields:
- `twitter` (URLField)
- `instagram` (URLField)
- `youtube` (URLField)
- `twitch` (URLField)

**No schema migrations needed** - fields exist and are populated.

## System Check Results

```bash
python manage.py check
System check identified no issues (0 silenced).
```

## Migration Status

**No new migrations created or applied** for P4-T1.4.

The Gate 5 migrations created earlier (0008, 0009, 0099, 0100) were rolled back and are not needed because:
1. Social fields already exist in legacy Team
2. FK references were already correct (teams.Team)
3. The problem was the context builder importing the wrong model

## Next Steps

1. ✅ Wire real partners data using `team.sponsors.all()`
2. ✅ Wire real pending actions using `team.invites.filter(...)` and `team.join_requests.filter(...)`
3. ✅ Wire social links from `team.twitter`, `team.instagram`, etc.
4. ✅ Update tests to assert real data
5. ✅ Verify query budget ≤6

## Future Work (Phase 5+)

When ready to use vNext Team model:
1. Create migration to add missing fields to `teams_team` table
2. Backfill organization_id/owner_id from existing data
3. Update all imports to use vNext Team
4. Remove legacy Team model
5. Update all related_names to remove `vnext_` prefix

**Until then**: Continue using legacy Team model for all read operations.
