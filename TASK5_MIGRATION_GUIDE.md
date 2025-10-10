# Task 5: Database Migration Guide

## Overview

This guide explains the database changes for Task 5 (Tournament & Ranking Integration) and how to safely apply them.

---

## New Database Tables

### 1. `teams_tournament_registration`
**Purpose:** Tracks team registrations for tournaments

**Fields:**
```sql
CREATE TABLE teams_tournament_registration (
    id                      BIGSERIAL PRIMARY KEY,
    team_id                 INTEGER NOT NULL REFERENCES teams_team(id) ON DELETE CASCADE,
    tournament_id           INTEGER NOT NULL REFERENCES tournaments_tournament(id) ON DELETE CASCADE,
    registered_by_id        INTEGER NOT NULL REFERENCES user_profile_userprofile(id) ON DELETE PROTECT,
    status                  VARCHAR(16) DEFAULT 'pending',
    roster_snapshot         JSONB DEFAULT '{}',
    validation_passed       BOOLEAN DEFAULT FALSE,
    validation_errors       JSONB DEFAULT '[]',
    max_roster_size         INTEGER NULL,
    min_starters            INTEGER NULL,
    allowed_roles           JSONB DEFAULT '[]',
    is_roster_locked        BOOLEAN DEFAULT FALSE,
    locked_at               TIMESTAMP NULL,
    payment_reference       VARCHAR(100),
    payment_verified        BOOLEAN DEFAULT FALSE,
    payment_verified_at     TIMESTAMP NULL,
    payment_verified_by_id  INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
    admin_notes             TEXT,
    rejection_reason        TEXT,
    registered_at           TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_team_tournament_registration UNIQUE (team_id, tournament_id)
);

CREATE INDEX idx_reg_tournament_status ON teams_tournament_registration(tournament_id, status);
CREATE INDEX idx_reg_team_tournament ON teams_tournament_registration(team_id, tournament_id);
CREATE INDEX idx_reg_status_date ON teams_tournament_registration(status, registered_at DESC);
```

**Estimated Size:** ~500 bytes per row  
**Expected Growth:** 100-500 rows per month

---

### 2. `teams_tournament_participation`
**Purpose:** Tracks individual player participation in tournaments

**Fields:**
```sql
CREATE TABLE teams_tournament_participation (
    id                  BIGSERIAL PRIMARY KEY,
    registration_id     INTEGER NOT NULL REFERENCES teams_tournament_registration(id) ON DELETE CASCADE,
    player_id           INTEGER NOT NULL REFERENCES user_profile_userprofile(id) ON DELETE CASCADE,
    role                VARCHAR(16) NOT NULL,
    is_starter          BOOLEAN DEFAULT TRUE,
    matches_played      INTEGER DEFAULT 0,
    mvp_count           INTEGER DEFAULT 0,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_player_per_registration UNIQUE (registration_id, player_id)
);

CREATE INDEX idx_part_player_reg ON teams_tournament_participation(player_id, registration_id);
CREATE INDEX idx_part_registration_starter ON teams_tournament_participation(registration_id, is_starter);
```

**Estimated Size:** ~200 bytes per row  
**Expected Growth:** 5-7 rows per registration (500-700 rows per month)

---

### 3. `teams_tournament_roster_lock`
**Purpose:** Audit trail for roster lock/unlock events

**Fields:**
```sql
CREATE TABLE teams_tournament_roster_lock (
    id                      BIGSERIAL PRIMARY KEY,
    registration_id         INTEGER NOT NULL REFERENCES teams_tournament_registration(id) ON DELETE CASCADE,
    is_unlock               BOOLEAN DEFAULT FALSE,
    locked_by_system        BOOLEAN DEFAULT FALSE,
    unlocked_by_id          INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
    reason                  TEXT,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_lock_registration_date ON teams_tournament_roster_lock(registration_id, created_at DESC);
```

**Estimated Size:** ~150 bytes per row  
**Expected Growth:** 1-2 rows per registration (100-200 rows per month)

---

## Migration Steps

### 1. Pre-Migration Checklist

**Before running migration, verify:**

```bash
# Check current migration status
python manage.py showmigrations teams

# Check for pending migrations
python manage.py makemigrations --dry-run teams

# Verify database connection
python manage.py dbshell
# Type \q to exit
```

**Backup Database:**
```bash
# PostgreSQL
pg_dump -U <username> <database_name> > backup_before_task5.sql

# SQLite
cp db.sqlite3 db.sqlite3.backup

# MySQL
mysqldump -u <username> -p <database_name> > backup_before_task5.sql
```

---

### 2. Generate Migration

```bash
python manage.py makemigrations teams
```

**Expected Output:**
```
Migrations for 'teams':
  apps/teams/migrations/00XX_tournament_integration.py
    - Create model TeamTournamentRegistration
    - Create model TournamentParticipation
    - Create model TournamentRosterLock
    - Create constraint unique_team_tournament_registration on model teamtournamentregistration
    - Create constraint unique_player_per_registration on model tournamentparticipation
    - Create index idx_reg_tournament_status on model teamtournamentregistration
    - Create index idx_part_player_reg on model tournamentparticipation
    - Create index idx_lock_registration_date on model tournamentrosterlock
```

---

### 3. Review Migration File

**Open:** `apps/teams/migrations/00XX_tournament_integration.py`

**Verify it contains:**
- ✅ All 3 model creations
- ✅ All foreign key relationships
- ✅ All unique constraints
- ✅ All indexes
- ✅ No data migrations (safe for production)

---

### 4. Test Migration (Recommended)

**On a copy of production data:**

```bash
# 1. Create test database
createdb deltacrown_test

# 2. Restore production backup
pg_restore -d deltacrown_test backup_before_task5.sql

# 3. Point settings to test database temporarily
# Edit settings.py or use environment variable
export DATABASE_URL=postgresql://user:pass@localhost/deltacrown_test

# 4. Run migration on test database
python manage.py migrate teams

# 5. Verify tables created
python manage.py dbshell
\dt teams_tournament*
```

---

### 5. Apply Migration (Production)

**During maintenance window or low-traffic period:**

```bash
# 1. Enable maintenance mode (optional)
# touch maintenance.flag

# 2. Apply migration
python manage.py migrate teams

# 3. Verify migration succeeded
python manage.py showmigrations teams
# All should have [X] marks

# 4. Check tables exist
python manage.py dbshell
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE 'teams_tournament%';
```

**Expected Output:**
```
 table_name
-----------------------------------
 teams_tournament_registration
 teams_tournament_participation
 teams_tournament_roster_lock
```

---

### 6. Post-Migration Verification

**Run system check:**
```bash
python manage.py check
```

**Test model imports:**
```bash
python manage.py shell

>>> from apps.teams.models import (
...     TeamTournamentRegistration,
...     TournamentParticipation,
...     TournamentRosterLock
... )
>>> print("All models imported successfully")
```

**Test database queries:**
```python
>>> # Check tables are accessible
>>> TeamTournamentRegistration.objects.count()
0  # Expected: 0 (no data yet)

>>> TournamentParticipation.objects.count()
0  # Expected: 0

>>> TournamentRosterLock.objects.count()
0  # Expected: 0

>>> # Test creating a record (then delete it)
>>> from apps.teams.models import Team
>>> from apps.tournaments.models import Tournament
>>> from apps.user_profile.models import UserProfile

>>> team = Team.objects.first()
>>> tournament = Tournament.objects.first()
>>> captain = team.captain

>>> if team and tournament and captain:
...     reg = TeamTournamentRegistration.objects.create(
...         team=team,
...         tournament=tournament,
...         registered_by=captain,
...         status='pending'
...     )
...     print(f"Test registration created: {reg.id}")
...     reg.delete()
...     print("Test registration deleted successfully")
```

---

## Rollback Plan

**If migration fails or causes issues:**

### Option 1: Reverse Migration (Clean Rollback)

```bash
# Rollback to previous migration
python manage.py migrate teams <previous_migration_number>

# Example:
# python manage.py migrate teams 0025_previous_migration
```

### Option 2: Restore from Backup

```bash
# 1. Drop affected tables
python manage.py dbshell
DROP TABLE teams_tournament_roster_lock;
DROP TABLE teams_tournament_participation;
DROP TABLE teams_tournament_registration;
\q

# 2. Restore database from backup
pg_restore -d deltacrown backup_before_task5.sql

# 3. Rollback Django migration state
python manage.py migrate teams <previous_migration_number> --fake
```

### Option 3: Manual Table Removal

```sql
-- Run in database shell
BEGIN;

-- Drop tables in reverse order (respecting foreign keys)
DROP TABLE IF EXISTS teams_tournament_roster_lock CASCADE;
DROP TABLE IF EXISTS teams_tournament_participation CASCADE;
DROP TABLE IF EXISTS teams_tournament_registration CASCADE;

COMMIT;
```

Then update Django migration state:
```bash
python manage.py migrate teams <previous_migration_number> --fake
```

---

## Data Population

### Initialize Ranking Criteria

**Required before system can calculate rankings:**

```python
# In Django shell or management command
from apps.teams.models import RankingCriteria

criteria = RankingCriteria.objects.create(
    tournament_participation=50,
    tournament_winner=500,
    tournament_runner_up=300,
    tournament_top_4=150,
    points_per_member=10,
    points_per_month_age=30,
    achievement_points=100,
    is_active=True
)

print(f"Created ranking criteria with ID: {criteria.id}")
```

**Or via admin:**
1. Navigate to `/admin/teams/rankingcriteria/`
2. Click "Add Ranking Criteria"
3. Fill in point values
4. Check "Is active"
5. Save

---

### Recalculate Existing Rankings

**After migration, recalculate points for existing teams:**

```python
from apps.teams.services.ranking_calculator import TeamRankingCalculator

# Recalculate all teams
result = TeamRankingCalculator.recalculate_all_teams()

print(f"Processed: {result['processed']} teams")
print(f"Updated: {result['updated']} teams")
print(f"Unchanged: {result['unchanged']} teams")

if result['errors']:
    print(f"Errors: {len(result['errors'])}")
    for error in result['errors']:
        print(f"  - {error['team_name']}: {error['error']}")
```

---

## Performance Considerations

### Index Usage

**The migration creates indexes for common queries:**

- `idx_reg_tournament_status` - Fast filtering by tournament and status
- `idx_reg_team_tournament` - Fast lookup by team/tournament pair
- `idx_part_player_reg` - Fast player participation lookup
- `idx_lock_registration_date` - Fast lock history retrieval

### Query Optimization

**Models use select_related/prefetch_related:**

```python
# Good: Uses select_related
registrations = TeamTournamentRegistration.objects.filter(
    tournament=tournament
).select_related('team', 'registered_by')

# Good: Prefetch participations
registration = TeamTournamentRegistration.objects.prefetch_related(
    'participations__player'
).get(id=123)
```

### Database Size Estimates

**Expected growth per 1000 teams:**
- Registrations: ~500KB (avg 5 tournaments per team)
- Participations: ~2MB (avg 6 players per team)
- Lock history: ~150KB (avg 1-2 locks per registration)

**Total: ~2.65MB per 1000 teams**

---

## Monitoring

### Health Checks

**After deployment, monitor:**

```sql
-- Check table row counts
SELECT 
    'teams_tournament_registration' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('teams_tournament_registration')) as size
FROM teams_tournament_registration
UNION ALL
SELECT 
    'teams_tournament_participation',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('teams_tournament_participation'))
FROM teams_tournament_participation
UNION ALL
SELECT 
    'teams_tournament_roster_lock',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('teams_tournament_roster_lock'))
FROM teams_tournament_roster_lock;
```

### Query Performance

**Monitor slow queries:**

```sql
-- PostgreSQL: Enable query logging
ALTER DATABASE deltacrown SET log_min_duration_statement = 1000;

-- Check for slow queries involving new tables
SELECT query, mean_time, calls
FROM pg_stat_statements
WHERE query LIKE '%teams_tournament%'
ORDER BY mean_time DESC
LIMIT 10;
```

---

## Troubleshooting

### Migration Fails: "relation already exists"

**Cause:** Tables partially created from failed previous attempt

**Solution:**
```bash
python manage.py migrate teams --fake <migration_number>
# Or manually drop tables and retry
```

---

### Migration Fails: "foreign key constraint"

**Cause:** Missing referenced tables (Team, Tournament, UserProfile)

**Solution:**
```bash
# Ensure all apps are migrated first
python manage.py migrate user_profile
python manage.py migrate tournaments
python manage.py migrate teams
```

---

### Migration Slow on Large Database

**Cause:** Creating indexes on large tables takes time

**Solution:**
- Run during maintenance window
- Use CONCURRENTLY for index creation (PostgreSQL):
  ```sql
  CREATE INDEX CONCURRENTLY idx_name ON table_name(column);
  ```
- Consider batching for very large datasets

---

## Migration Checklist

**Pre-Migration:**
- [ ] Database backup created
- [ ] Test environment migration successful
- [ ] Migration file reviewed
- [ ] Rollback plan prepared
- [ ] Maintenance window scheduled (if needed)

**During Migration:**
- [ ] Migration applied without errors
- [ ] All tables created successfully
- [ ] All indexes created
- [ ] All constraints enforced
- [ ] No foreign key errors

**Post-Migration:**
- [ ] System check passes
- [ ] Models import successfully
- [ ] Test queries execute
- [ ] Ranking criteria created
- [ ] Existing rankings recalculated
- [ ] Admin interface accessible
- [ ] Frontend pages load correctly

---

## Support

**If you encounter issues:**

1. **Check logs:** `python manage.py migrate teams --verbosity 3`
2. **Review migration file:** Look for syntax errors
3. **Verify dependencies:** Ensure other apps migrated
4. **Check database:** Verify connection and permissions
5. **Consult docs:** `TASK5_IMPLEMENTATION_COMPLETE.md`

---

*Database Migration Guide for Task 5 - Tournament & Ranking Integration*
