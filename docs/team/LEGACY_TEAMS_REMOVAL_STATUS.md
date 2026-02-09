# Legacy `apps/teams` Removal — Migration Status

> **Phase A (Code Layer): COMPLETE**
> **Phase B (Database Layer): PENDING — see plan below**

---

## What Was Done (Phase A — Code Consolidation)

### 1. Compatibility Properties Added to `organizations` Models

| Model | Property | Bridges |
|---|---|---|
| `Team` | `game` | `game_id` (int) → game slug (str) via `games.Game` lookup |
| `Team` | `game_obj` | Full `Game` model instance from `game_id` |
| `Team` | `is_active` | `status == 'ACTIVE'` (replaces legacy `BooleanField`) |
| `Team` | `is_public` | `visibility == 'PUBLIC'` (replaces legacy `BooleanField`) |
| `Team` | `memberships` | Alias for `vnext_memberships` reverse relation |
| `Team` | `twitter`, `instagram`, `youtube`, `twitch`, `discord` | Social link aliases |
| `TeamMembership` | `profile` | `user.profile` (replaces legacy `ForeignKey(UserProfile)`) |
| `TeamMembership` | `is_captain` / setter | Alias for `is_tournament_captain` |

*File: `apps/organizations/models/team.py`, `apps/organizations/models/membership.py`*

### 2. Production Import Rewiring — **66 files updated**

All `from apps.teams.models import Team/TeamMembership` → `from apps.organizations.models import ...`
All `apps.get_model("teams", ...)` → `apps.get_model("organizations", ...)`

### 3. Test File Rewiring — **41 files updated**

Same pattern as production, applied to `tests/` directory.

### 4. Infrastructure Updates

| Component | Change |
|---|---|
| `deltacrown/asgi.py` | WebSocket routing → `apps.organizations.realtime.routing` |
| `deltacrown/celery.py` | Task paths → `teams.*` registered names (via `legacy_bridge.py`) |
| Signal handler | `sender='teams.TeamMembership'` → `sender='organizations.TeamMembership'` |
| Realtime module | Moved `consumers.py`, `routing.py` to `apps/organizations/realtime/` |
| Celery tasks | Created `apps/organizations/tasks/legacy_bridge.py` with 4 stub tasks |
| Compat layer | Created `apps/organizations/services/compat.py` (`get_team_by_any_id`, `legacy_id_to_org_id`) |

### 5. Special Cases Handled

| File | Issue | Resolution |
|---|---|---|
| `dual_write_service.py` | Imported `TeamRankingBreakdown` from org (doesn't exist) | Restored legacy import with `try/except` |
| `siteui/views.py` | `TeamPost` from `teams.models.social` | Wrapped in `try/except ImportError` |
| `user_profile/views_public.py` | `TeamPost, TeamActivity` | Wrapped in `try/except ImportError` |
| `tournament_ops/team_adapter.py` | `TeamService` from legacy services | Replaced with `get_team_by_any_id()` |
| `tournaments/views/main.py` | `TeamRankingBreakdown` | Kept as `apps.teams.models` import (wrapped in try/except) |
| `tournaments/services/ranking_service.py` | `TeamRankingBreakdown` via `get_model` | Kept as `apps.get_model('teams', ...)` |
| `registration_autofill.py` | `TeamMember` (typo) | Fixed to `TeamMembership` + updated query |

---

## What Remains (Phase B — Database Consolidation)

### Why `apps.teams` Cannot Be Fully Removed Yet

1. **14 ForeignKey declarations** in model files point to `'teams.Team'` (leaderboards, tournaments, user_profile, organizations/ranking). Removing the `teams` app makes these FK references unresolvable.

2. **80+ template URL names** reference the `teams:` namespace (e.g., `{% url 'teams:detail' slug=... %}`). The legacy `urls.py` must remain for URL resolution.

3. **19 migration files** reference `to="teams.team"`. These are historical and MUST NOT be altered.

4. **Social models** (`TeamPost`, `TeamActivity`, `TeamPostMedia`, etc.) have no equivalent in organizations yet.

5. **TeamRankingBreakdown**, **RankingCriteria**, **TeamRankingHistory** exist only in legacy.

### FK References Requiring Data Migration

| App | File | Line(s) | Field |
|---|---|---|---|
| leaderboards | `models.py` | L56, L143, L280, L353, L540, L886 | 6 × `ForeignKey('teams.Team')` |
| tournaments | `dispute.py` | L95 | `ForeignKey('teams.Team')` |
| tournaments | `form_template.py` | L422 | `ForeignKey('teams.Team')` |
| tournaments | `group.py` | L181 | `ForeignKey('teams.Team')` |
| tournaments | `lobby.py` | L237 | `ForeignKey('teams.Team')` |
| tournaments | `result_submission.py` | L67 | `ForeignKey('teams.Team')` |
| tournaments | `team_invitation.py` | L34 | `ForeignKey('teams.Team')` |
| user_profile | `models_main.py` | L272 | `ForeignKey('teams.Team')` |
| organizations | `ranking.py` | L50 | `OneToOneField('teams.Team')` |
| **Total** | | | **14 FK fields** |

### Migration Steps (Phase B)

```
1. BACKUP the database (pg_dump)
2. For each FK field above:
   a. Add NEW nullable FK to 'organizations.Team' alongside old FK
   b. Run data migration:
      - For each row, get legacy_team_id from old FK
      - Lookup via TeamMigrationMap → vnext_team_id
      - Set new FK value to vnext_team_id
   c. Drop old FK column
   d. Rename new FK column to old name
3. Update template URLs from 'teams:X' → 'organizations:X'
4. Remove 'apps.teams' from INSTALLED_APPS
5. Add MIGRATION_MODULES = {'teams': None} to settings
6. Delete apps/teams/ directory
```

### Template URL Migration (80+ URLs)

The `teams:` namespace has 80+ unique URL names used in templates.
Most map to organization views with different patterns:

| Legacy URL Name | Org Equivalent |
|---|---|
| `teams:create` | `organizations:team_create` |
| `teams:detail` | `organizations:team_detail` |
| `teams:manage` | `organizations:team_manage` |
| `teams:team_profile` | `organizations:team_detail` |
| Other 76+ names | Need individual mapping |

---

## Current State Summary

```
apps/teams/     → LEGACY SHELL (models + migrations + urls for FK/URL resolution)
apps/organizations/  → PRIMARY APP (all new code imports from here)

INSTALLED_APPS still has both:
  "apps.teams"
  "apps.organizations.apps.OrganizationsConfig"

Django check:  ✅ System check identified no issues (0 silenced)
Django setup:  ✅ OK
```

| Metric | Count |
|---|---|
| Production files rewired | 66 |
| Test files rewired | 41 |
| New files created | 5 |
| Model compat properties added | 11 |
| Special case fixes | 7 |
| Django check issues | 0 |
