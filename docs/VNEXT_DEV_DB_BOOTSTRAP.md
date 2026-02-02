# Development Database Bootstrap Guide

**Purpose**: Set up a fresh development database using `DATABASE_URL_DEV` without touching production.

**Status**: ✅ Ready for use  
**Date**: 2025-01-XX  
**Context**: Replaces production database reconciliation strategy with clean dev database approach.

---

## Prerequisites

1. **Fresh Neon Database Branch**
   - Create new branch from production OR create new standalone database
   - Get connection string in format: `postgresql://user:password@host/database?sslmode=require`
   - Database should be **empty** or have only default PostgreSQL schemas

2. **Environment File**
   - `.env` file exists in project root
   - Has existing `DATABASE_URL` (production - DO NOT MODIFY)

---

## Environment Variables

### Production Database (Read-Only)
```ini
# DO NOT MODIFY - This is production
DATABASE_URL=postgresql://neondb_owner:PASSWORD@ep-lively-queen-a13dp7w6.ap-southeast-1.aws.neon.tech/deltacrown?sslmode=require
```

### Development Database (New)
```ini
# Add this line with your new Neon branch/database
DATABASE_URL_DEV=postgresql://neondb_owner:PASSWORD@ep-NEW-ENDPOINT.neon.tech/dev_deltacrown?sslmode=require
```

**Priority**: `DATABASE_URL_DEV` takes precedence over `DATABASE_URL` when both are set.

**Safety**: Production database (`deltacrown`) is protected by safety checks in management commands.

---

## Bootstrap Process

### Step 1: Verify Environment
```bash
# Check which database is active
python manage.py print_db_identity
```

**Expected Output**:
```
Source: [DEV]
Host: ep-NEW-ENDPOINT.neon.tech
Database: dev_deltacrown
✓ Connected to Neon cloud database
```

If you see `[PROD]` or `deltacrown`, STOP - `DATABASE_URL_DEV` is not set correctly.

---

### Step 2: Run Clean Migration
```bash
python manage.py verify_clean_migrate
```

**What This Does**:
1. Verifies database identity (shows host, database name, connection status)
2. Runs `python manage.py migrate` (applies all Django migrations)
3. Performs smoke checks:
   - `python manage.py check` (Django system check)
   - Verifies migration records exist
   - Confirms critical tables created

**Expected Output**:
```
================================================================================
CLEAN DATABASE MIGRATION VERIFICATION
================================================================================

1. DATABASE IDENTITY
--------------------------------------------------------------------------------
Source: [DEV]
Host: ep-NEW-ENDPOINT.neon.tech
Database: dev_deltacrown
✓ Connected to Neon cloud database
✓ Database identity verified

2. RUNNING MIGRATIONS
--------------------------------------------------------------------------------
Running: python manage.py migrate
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, organizations, teams, ...
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  [... more migrations ...]
✓ Migrations completed

3. SMOKE CHECKS
--------------------------------------------------------------------------------
Running: python manage.py check
✓ Django check passed

Checking migration status...
Total applied migrations: 150+
  organizations: 12 migrations
  teams: 5 migrations
  competition: 8 migrations
✓ Migration status verified

Verifying critical tables...
✓ django_content_type
✓ auth_user
✓ organizations_organization
✓ teams_team
✓ Critical tables verified

================================================================================
✓ ALL CHECKS PASSED
================================================================================

Database is ready for use.

Next steps:
  - Run setup commands (seed_game_ranking_configs, etc.)
  - Create superuser: python manage.py createsuperuser
  - Start server: python manage.py runserver
```

**Exit Code**: 0 on success, non-zero on failure (script stops at first error)

---

### Step 3: Seed Initial Data
```bash
# Seed game ranking configurations (competition app)
python manage.py seed_game_ranking_configs

# If other seed commands exist
python manage.py seed_tournaments  # (if exists)
python manage.py seed_games        # (if exists)
```

---

### Step 4: Run Automated Smoke Checks

```bash
python manage.py dev_bootstrap_smoke_check
```

**What This Does**:
1. Verifies database identity (host, database name, PostgreSQL version)
2. Runs Django system check
3. Runs automated smoke tests:
   - Admin interface accessible
   - Competition app registered
   - Competition models accessible
   - Ranking about page loads
   - Teams vnext hub loads
   - Rankings Policy link exists and points to correct URL

**No manual browser verification needed** - all checks are automated using Django test client.

**Expected Output**:
```
================================================================================
DEVELOPMENT BOOTSTRAP SMOKE CHECK
================================================================================

1. DATABASE IDENTITY
--------------------------------------------------------------------------------
Source: [DEV]
Host: ep-NEW-ENDPOINT.neon.tech
Database: neondb
...
[OK] Database identity verified

2. SYSTEM CHECK
--------------------------------------------------------------------------------
[OK] Django check passed

3. SMOKE TESTS
--------------------------------------------------------------------------------
Running smoke tests: apps.core.tests.test_smoke_dev_bootstrap
...
Ran 5 tests in X.XXXs
OK

[OK] All smoke tests passed

================================================================================
[OK] ALL SMOKE CHECKS PASSED
================================================================================
```

---

## Success Criteria

✅ **Database Connected**
- `print_db_identity` shows `[DEV]` and correct database name
- Connection is to Neon cloud (not localhost)

✅ **Migrations Applied**
- `verify_clean_migrate` exits code 0
- All migrations show `[X]` in `showmigrations`
- No unapplied migrations

✅ **Tables Created**
- Critical tables exist:
  - `organizations_organization`
  - `teams_team` (or `organizations_team` if resolved)
  - `competition_*` tables
  - Django core tables (auth, contenttypes, sessions)

✅ **Smoke Tests Pass**
- `dev_bootstrap_smoke_check` exits code 0
- All 5 smoke tests pass:
  1. Admin interface accessible
  2. Competition app models accessible
  3. Competition ranking about page loads
  4. Teams vnext hub page loads
  5. Rankings Policy link exists and points correctly

✅ **Game Configs Seeded**
- 11 game ranking configs created
- No seed errors

---

## Troubleshooting

### Issue: `print_db_identity` shows `[PROD]`
**Cause**: `DATABASE_URL_DEV` not set or not loaded  
**Fix**:
1. Check `.env` file has `DATABASE_URL_DEV=...` line
2. Verify no typos in variable name
3. Restart terminal/shell (environment variables cached)
4. Verify `.env` is in project root (`g:\My Projects\WORK\DeltaCrown\.env`)

### Issue: `organizations_team does not exist`
**Cause**: Migration references wrong table name (architectural issue)  
**Fix**:
1. Check if error is from `competition` app migrations
2. May need to patch migrations to use `teams_team` instead
3. Or use `SeparateDatabaseAndState` to create table manually
4. See: `TEAM_SCHEMA_VERIFICATION_REPORT.md` for context

### Issue: `verify_clean_migrate` fails at migration step
**Cause**: Migration errors (model issues, dependency conflicts)  
**Fix**:
1. Check error output for specific migration file
2. Review migration file for issues
3. May need to edit migration to fix references
4. Run `python manage.py showmigrations` to see unapplied migrations
5. Run `python manage.py migrate --plan` to see migration plan

### Issue: Smoke tests fail
**Cause**: Application errors, URL routing issues, or missing templates  
**Fix**:
1. Check test output for specific failure
2. Run tests individually: `python manage.py test apps.core.tests.test_smoke_dev_bootstrap.DevBootstrapSmokeTests.test_smoke_admin_accessible`
3. Check URL configuration in `urls.py`
4. Verify templates exist for tested views
5. Check server logs for errors

---

## Commands Reference

### Database Identity
```bash
# Show which database is connected
python manage.py print_db_identity

# Exit code: 0 if Neon, 1 if localhost or wrong DB
```

### Full Bootstrap
```bash
# All-in-one verification (identity + migrate + checks)
python manage.py verify_clean_migrate

# Exit code: 0 if success, 1 if any step fails
```

### Automated Smoke Checks
```bash
# Run all smoke tests (identity + system check + tests)
python manage.py dev_bootstrap_smoke_check

# Exit code: 0 if success, 1 if any check fails
```

### Manual Steps (if verify_clean_migrate not used)
```bash
# Run migrations
python manage.py migrate

# Django system check
python manage.py check

# Show migration status
python manage.py showmigrations

# Show specific app migrations
python manage.py showmigrations organizations
python manage.py showmigrations teams
python manage.py showmigrations competition
```

### Seed Data
```bash
# Game ranking configurations
python manage.py seed_game_ranking_configs

# Check for other seed commands
python manage.py help | grep seed
```

### Run Individual Smoke Tests
```bash
# Run all smoke tests
python manage.py test apps.core.tests.test_smoke_dev_bootstrap

# Run specific test
python manage.py test apps.core.tests.test_smoke_dev_bootstrap.DevBootstrapSmokeTests.test_smoke_admin_accessible
```

---

## Safety Notes

1. **Production Protection**:
   - `db_migration_reconcile` command blocks on production database
   - Database name must contain "test" OR set `ALLOW_NONTEST_MIGRATION_RECONCILE=1`
   - This prevents accidental production modifications

2. **DATABASE_URL Priority**:
   - `DATABASE_URL_DEV` always wins if set
   - Set `DATABASE_URL_DEV` for dev work
   - Unset `DATABASE_URL_DEV` to use production (read-only operations)

3. **Fresh Database Assumption**:
   - `verify_clean_migrate` assumes fresh/empty database
   - Do not run on database with existing tables
   - Use `db_migration_reconcile` for existing databases

4. **Rollback**:
   - If bootstrap fails, easiest fix is to drop dev database and create new one
   - Neon branches can be deleted without affecting production
   - Never drop production `deltacrown` database

5. **No Hardcoded Credentials**:
   - Smoke tests create temporary test users in test database only
   - Test users are automatically cleaned up after tests
   - No credentials are stored in code or version control

---

## Architecture Notes

### Dual Team Model Issue
- `organizations.Team` model defines `db_table='organizations_team'`
- `teams.Team` model defines `db_table='teams_team'`
- Production has `teams_team` (62 related tables) but no `organizations_team`
- Some apps reference `organizations.Team` (expect organizations_team)
- May require migration patches or model resolution

**Resolution Strategy** (TBD):
1. Option A: Patch migrations to use `teams.Team` everywhere
2. Option B: Create `organizations_team` and migrate data
3. Option C: Remove `organizations.Team` model entirely

**Current Status**: Fresh database will follow model definitions, may create both tables.

---

## Related Documentation

- `TEAM_SCHEMA_VERIFICATION_REPORT.md` - Team model architecture audit
- `PLATFORM_ISSUES_AND_FIXES.md` - Known issues and fixes
- `MODEL_AUTHORITY_RESOLUTION.md` - Model conflict resolution strategies
- `ORG_NAVIGATION_FIX_SUMMARY.md` - Organization navigation issues

---

## Changelog

**2025-01-XX**: Initial version
- Created DATABASE_URL_DEV override support
- Created verify_clean_migrate command
- Documented bootstrap process
- Added troubleshooting section
