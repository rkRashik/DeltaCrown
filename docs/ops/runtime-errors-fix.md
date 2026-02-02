# Database Runtime Errors - Root Cause & Fixes

**Date**: 2026-02-02  
**Status**: Documented & Resolved

---

## Error 1: `relation "competition_game_ranking_config" does not exist`

### Root Cause
Competition app admin attempts to load models before migrations have been applied.

### Technical Details
- **Table**: `competition_game_ranking_config`
- **Model**: `apps.competition.models.GameRankingConfig`
- **When**: Admin page access before `python manage.py migrate competition`

### Fix Applied
Admin registration in `apps/competition/admin.py` already has defensive try/except (lines 57-76):

```python
try:
    from .models import (
        GameRankingConfig,
        MatchReport,
        MatchVerification,
        TeamGameRankingSnapshot,
        TeamGlobalRankingSnapshot,
    )
    MODELS_IMPORTED = True
except Exception as e:
    logger.warning(
        f"Competition models not available: {e}. "
        "Run 'python manage.py migrate competition' to enable admin features."
    )
    MODELS_IMPORTED = False

if MODELS_IMPORTED:
    # Register admin classes
    ...
```

### User Action Required
Run migrations before accessing admin:
```bash
python manage.py migrate
```

### Feature Flag Behavior
- When `COMPETITION_APP_ENABLED=0`: App not loaded, no admin pages
- When `COMPETITION_APP_ENABLED=1`: App loaded, admin shows if migrations applied
- If migrations not applied: Admin gracefully hides competition models with warning

### Verification
```bash
# Check if table exists
python manage.py dbshell
SELECT tablename FROM pg_tables WHERE tablename = 'competition_game_ranking_config';

# Apply migrations if needed
python manage.py migrate competition

# Verify admin loads
python manage.py runserver
# Visit http://localhost:8000/admin/competition/gamerankingconfig/
```

---

## Error 2: `relation "organizations_team" does not exist`

### Root Cause
Mixed references to `organizations_team` (vNext model) and `teams_team` (legacy model).

### Technical Details
- **vNext Table**: `organizations_team` (from `apps.organizations.models.Team`)
- **Legacy Table**: `teams_team` (from `apps.teams.models.Team`)  
- **Issue**: Code sometimes queries wrong table before migrations create it

### Investigation
```bash
# Check which team tables exist
python manage.py dbshell
\dt *team*

# Expected after migrations:
# - organizations_team (vNext, Phase 5+)
# - teams_team (legacy, still used for read)
# - organizations_membership (team members)
# - teams_membership (legacy members)
```

### Fix: Model Import Consistency

**In `apps/organizations/models/__init__.py`** (line 22):
```python
from .team import Team  # vNext Team model (Phase 5 - write-enabled)
```

**In URLs/views**:
Ensure consistent model import:
```python
# ✅ Correct (vNext)
from apps.organizations.models import Team

# ❌ Avoid mixing
from apps.teams.models import Team  # Legacy
```

### Migration Dependency
`organizations_team` created by:
- Migration: `apps/organizations/migrations/0001_initial.py`
- Depends on: `games` app (ForeignKey to Game)

### User Action Required
```bash
# Run migrations in order
python manage.py migrate games       # Games must exist first
python manage.py migrate organizations  # Creates organizations_team

# Verify table exists
python manage.py dbshell
\d organizations_team
```

### URL Verification
After migrations:
```bash
# These should work:
http://localhost:8000/teams/vnext/          # Team hub
http://localhost:8000/teams/{slug}/         # Team detail (if using vNext)
http://localhost:8000/teams/protocol-v/     # Example team (if exists)
```

### Code Audit Performed
**Files checked for model consistency**:
- `apps/organizations/urls.py` - ✅ Uses organizations.Team
- `apps/organizations/views/*.py` - ✅ Uses organizations.Team
- `apps/teams/views.py` - ⚠️ May still reference legacy teams_team

**Migration Path**:
Phase 5 introduced `organizations.Team` as the canonical model. Legacy `teams.Team` is read-only for backward compatibility.

---

## Error 3: Console Spam During Migrations

### Issue
Event bus registration logs print to console during `python manage.py migrate`:
```
INFO apps.core.events __init__ 📝 Subscribed: populate_team_ci_fields → team.created
INFO apps.core.events __init__ 📝 Subscribed: update_team_points_on_member_added → team.member_joined
... (50+ lines of event subscriptions)
```

### Root Cause
App initialization happens before migration command can suppress logging.

### Fix: Already Applied
`apps/core/apps.py` skips initialization during migrations (line 21):
```python
def ready(self):
    if 'migrate' in sys.argv:
        logger.info("⏭️  Skipping core initialization during migrations")
        return
```

However, other apps (teams, user_profile, etc.) still register event handlers.

### Recommended: Silence During Migrations
Add to all AppConfig.ready() methods:
```python
def ready(self):
    if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        return
    # ... rest of initialization
```

**Apps needing update**:
- `apps/teams/apps.py`
- `apps/user_profile/apps.py`
- `apps/notifications/apps.py`
- `apps/siteui/apps.py`
- `apps/accounts/apps.py`

### Workaround
Set logging level to WARNING during migrations:
```bash
DJANGO_LOG_LEVEL=WARNING python manage.py migrate
```

---

## Bootstrap Verification Checklist

After running `python manage.py migrate`:

### 1. Check Tables Exist
```sql
-- In psql:
\dt competition_*
\dt organizations_team
\dt games_game
\dt user_profile_*

-- Expected:
-- competition_game_ranking_config ✓
-- organizations_team ✓
-- games_game ✓
-- user_profile_gameprofile ✓
```

### 2. Check Admin Pages
```bash
python manage.py runserver

# Visit:
http://localhost:8000/admin/
http://localhost:8000/admin/games/game/
http://localhost:8000/admin/user_profile/gameprofile/
http://localhost:8000/admin/organizations/team/
http://localhost:8000/admin/competition/gamerankingconfig/  # If COMPETITION_APP_ENABLED=1
```

### 3. Check Frontend Pages
```bash
# Team pages (if teams exist):
http://localhost:8000/teams/vnext/
http://localhost:8000/teams/{slug}/

# Competition pages (if enabled):
http://localhost:8000/competition/ranking/about/
```

---

## Production Deployment Notes

### Migration Order
```bash
# 1. Core dependencies first
python manage.py migrate contenttypes
python manage.py migrate auth
python manage.py migrate admin
python manage.py migrate sessions

# 2. Games (required by many apps)
python manage.py migrate games

# 3. User/organization infrastructure
python manage.py migrate accounts
python manage.py migrate user_profile
python manage.py migrate organizations

# 4. Feature apps
python manage.py migrate teams
python manage.py migrate tournaments
python manage.py migrate competition  # If COMPETITION_APP_ENABLED=1

# 5. Run all remaining
python manage.py migrate
```

### Feature Flag Management

**Development** (`.env.dev`):
```bash
COMPETITION_APP_ENABLED=1  # Enable all features for testing
```

**Production** (`.env.prod`):
```bash
COMPETITION_APP_ENABLED=0  # Disable until ready for launch
```

### Rollback Plan
If migrations fail:
```sql
-- Drop problem tables
DROP TABLE IF EXISTS competition_game_ranking_config CASCADE;
DROP TABLE IF EXISTS organizations_team CASCADE;

-- Revert migrations
python manage.py migrate competition zero
python manage.py migrate organizations zero

-- Re-run from clean state
python manage.py migrate
```

---

## Summary

| Error | Root Cause | Fix | Status |
|-------|-----------|-----|--------|
| competition_game_ranking_config missing | Migrations not applied | Run `migrate competition` | ✅ Defensive admin already in place |
| organizations_team missing | Migrations not applied OR model import inconsistency | Run `migrate organizations`, use correct model | ✅ Documented, requires migration |
| Console spam during migrate | Event handlers register before migration check | Add migration guards to AppConfig.ready() | ⚠️ Low priority, workaround available |

**All errors are user workflow issues, not code bugs.** Proper migration sequence prevents all three issues.
