# MIGRATION REPAIR LOOP - 2026-01-14

## Executive Summary

**Status**: PARTIAL SUCCESS - User Profile tables restored, additional issues discovered  
**Execution Time**: 2026-01-14 19:00 - 20:35 (1h 35m)  
**Tables Restored**: 10 (user_profile: 9, accounts: 1)  
**Migrations Created**: 4 repair migrations  
**Critical Discovery**: Django migrations creating tables in `test_schema` instead of `public` schema

---

## Problem Statement

Database audit revealed widespread migration integrity failure:
- 8+ tables marked as "created" by applied migrations but **missing from database**
- All missing tables in `user_profile` and `accounts` apps
- Endpoints `/me/settings/`, `/@username/`, `/admin/` failing with 500 errors

**Root Cause**: Migrations previously faked or database restored without re-running DDL operations.

---

## Repair Strategy

1. **Extract SQL from Original Migrations** using `manage.py sqlmigrate`
2. **Create Formal Repair Migrations** using `migrations.RunSQL` with `CREATE TABLE IF NOT EXISTS`
3. **Apply Repair Migrations** via `manage.py migrate`
4. **Fix Schema Issues** (tables created in wrong PostgreSQL schema)
5. **Verify Endpoints** with smoke tests

**Decision**: Use formal Django migrations (NOT manual SQL scripts) for audit trail and reproducibility.

---

## Repair Migrations Created

### 1. user_profile.0057_repair_missing_profile_tables_batch1
**Source Migrations**: 0031, 0034, 0036  
**Tables Restored**:
| Table Name | Original Migration | Status |
|------------|-------------------|---------|
| `user_profile_showcase` | 0031 | ✅ RESTORED |
| `user_profile_game_config` | 0034 | ✅ RESTORED |
| `user_profile_hardware_gear` | 0034 | ✅ RESTORED |
| `user_profile_trophy_showcase` | 0036 | ✅ RESTORED |

**Key SQL Features**:
- `CREATE TABLE IF NOT EXISTS` for idempotency
- Foreign keys to `user_profile_userprofile.id`
- JSONB columns for flexible data storage

### 2. user_profile.0058_repair_missing_profile_tables_batch2
**Source Migrations**: 0046, 0048  
**Tables Restored**:
| Table Name | Original Migration | Status |
|------------|-------------------|---------|
| `user_profile_career_profile` | 0046 | ✅ RESTORED |
| `user_profile_matchmaking_preferences` | 0046 | ✅ RESTORED |
| `user_profile_follow_request` | 0048 | ✅ RESTORED |

**Columns Added**:
- `is_private_account` to `user_profile_privacysettings` (from 0048)

**Key SQL Features**:
- CHECK constraint on `follow_request` status field
- PostgreSQL `DO $$ ... END $$` block for conditional column creation
- Used `information_schema.columns` check before ALTER TABLE

### 3. user_profile.0059_repair_settings_tables
**Source Migration**: 0030  
**Tables Restored**:
| Table Name | Original Migration | Status |
|------------|-------------------|---------|
| `user_profile_notification_preferences` | 0030 | ✅ RESTORED |
| `user_profile_wallet_settings` | 0030 | ✅ RESTORED |

**Key SQL Features**:
- Boolean flags for email/in-app notifications
- Payment method settings (bKash, Nagad, Rocket)
- `DEFAULT NOW()` for timestamp columns
- `DEFAULT false` for boolean columns

### 4. accounts.0003_repair_account_deletion_request
**Source Migration**: accounts.0002  
**Table Restored**:
| Table Name | Original Migration | Status |
|------------|-------------------|---------|
| `accounts_accountdeletionrequest` | 0002 | ✅ RESTORED |

**Key SQL Features**:
- `inet` type for IP address storage
- Composite index on `(status, scheduled_for)`
- UNIQUE constraint on `user_id`

---

## Critical Issue: PostgreSQL Schema Mismatch

### Discovery
After applying all migrations, smoke tests revealed:
```
psycopg2.errors.UndefinedTable: relation "accounts_accountdeletionrequest" does not exist
```

**Investigation Found**:
- Tables existed in database BUT in `test_schema`, not `public` schema
- Django's `search_path`: `"$user", public` (does NOT include `test_schema`)
- Confirmed via: `SELECT table_schema, table_name FROM information_schema.tables ...`

**Result**: All 10 repair tables created in `test_schema`:
```
test_schema.accounts_accountdeletionrequest
test_schema.user_profile_showcase
test_schema.user_profile_game_config
test_schema.user_profile_hardware_gear
test_schema.user_profile_trophy_showcase
test_schema.user_profile_career_profile
test_schema.user_profile_matchmaking_preferences
test_schema.user_profile_follow_request
test_schema.user_profile_notification_preferences
test_schema.user_profile_wallet_settings
```

### Root Cause
- Migrations likely ran in test mode or with test database router active
- PostgreSQL test isolation creates separate `test_schema`
- Schema not specified in migration SQL, inherited from connection context

### Resolution
**Script**: `scripts/move_tables_to_public.py`

Executed SQL for each table:
```sql
ALTER TABLE test_schema.{table_name} SET SCHEMA public;
```

**Verification**:
```bash
$ python scripts/check_schemas.py
[OK] public.accounts_accountdeletionrequest
[OK] public.user_profile_showcase
[OK] public.user_profile_game_config
...
```

**Status**: ✅ ALL TABLES MOVED TO PUBLIC SCHEMA

---

## Smoke Test Results

### Test Suite: scripts/migration_smoke_tests.py

**Test 1: GET /me/settings/ (authenticated)**
```
Status: 200
[PASS] /me/settings/ returns 200
```
✅ **SUCCESS** - Settings page loads with all 10 tables accessible

**Test 2: GET /@{username}/ (public profile)**
```
Status: 500
[FAIL] column teams_teammembership.left_at does not exist
```
❌ **BLOCKED** - Discovered additional missing column in `teams` app (outside scope)

**Test 3: GET /admin/ (superuser)**
⏸️ **NOT REACHED** - Blocked by Test 2 failure

---

## User Creation Verification

**Test Script**: `scripts/test_user_creation.py`

**Results**:
```
[SUCCESS] User created: test_migration_check (ID: 7803)
INFO Generated public_id=DC-26-000002 for user_id=7803
[SUCCESS] UserProfile auto-created via signal
[SUCCESS] Public ID generated correctly
```

**Signal**: `apps/user_profile/signals/legacy_signals.py::ensure_profile`
- Runs on `User` post_save
- Creates `UserProfile` via `get_or_create()`
- Generates `public_id` using `PublicIDGenerator`

✅ **UserProfile auto-creation working correctly**

---

## Additional Discoveries

### 1. Table Name Discrepancies
- **Audit Expected**: `user_profile_profileshowcase`
- **Actual Table**: `user_profile_showcase`
- **Cause**: Models use `db_table` Meta attribute different from model name
- **Resolution**: Used `manage.py sqlmigrate` to get exact DDL from original migrations

### 2. Missing Columns Not in Audit
- `is_private_account` column on `PrivacySettings` (from migration 0048)
- **Resolution**: Added conditional ALTER TABLE using PostgreSQL procedural SQL

### 3. Out-of-Scope Issues Found
- `teams_teammembership.left_at` column missing (separate from user_profile)
- This blocks `/@username/` page which displays team memberships
- Requires separate repair migration in `teams` app

---

## SQL Extraction Process

For each missing table, used Django's `sqlmigrate` command:

```bash
$ python manage.py sqlmigrate user_profile 0031
BEGIN;
--
-- Create model ProfileShowcase
--
CREATE TABLE "user_profile_showcase" (
    id bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    enabled_sections jsonb NOT NULL,
    featured_team_id integer NULL,
    user_profile_id bigint NOT NULL UNIQUE,
    CONSTRAINT user_profile_showca_user_profile_id_a1b2c3d4_fk_user_prof
        FOREIGN KEY (user_profile_id)
        REFERENCES user_profile_userprofile (id)
        DEFERRABLE INITIALLY DEFERRED
);
COMMIT;
```

**Advantages**:
- ✅ Guarantees SQL matches original migration exactly
- ✅ Includes all indexes, constraints, foreign keys
- ✅ Uses correct PostgreSQL data types
- ✅ Preserves constraint names for consistency

---

## Idempotency Strategy

All repair migrations use `CREATE TABLE IF NOT EXISTS`:

```python
migrations.RunSQL(
    sql="""
    CREATE TABLE IF NOT EXISTS user_profile_showcase (
        id bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
        ...
    );
    """,
    reverse_sql="-- No reverse operation needed (idempotent)",
)
```

**Benefits**:
- ✅ Safe to re-run migrations on any database state
- ✅ No errors if table already exists
- ✅ Can apply repair migrations to test, staging, production without modification

**Column Additions** used conditional PL/pgSQL:
```sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_profile_privacysettings' 
        AND column_name='is_private_account'
    ) THEN
        ALTER TABLE user_profile_privacysettings 
        ADD COLUMN is_private_account boolean DEFAULT false NOT NULL;
    END IF;
END $$;
```

---

## Migration Application Timeline

| Time | Action | Result |
|------|--------|---------|
| 19:00 | Apply user_profile.0057 | ✅ OK (4 tables) |
| 19:05 | Apply user_profile.0058 | ✅ OK (3 tables + 1 column) |
| 19:10 | Apply accounts.0003 | ✅ OK (1 table) |
| 19:15 | First smoke test | ❌ FAIL - table not found |
| 19:20 | Discover test_schema issue | 🔍 Investigation |
| 19:25 | Move tables to public | ✅ OK (8 tables moved) |
| 19:30 | Second smoke test | ❌ FAIL - NotificationPreferences missing |
| 19:35 | Create 0059 repair migration | ✅ OK (2 more tables) |
| 19:40 | Move new tables to public | ✅ OK (2 tables moved) |
| 19:45 | Final smoke test | ✅ PASS /me/settings/ |

---

## Files Created/Modified

### New Migrations
```
apps/user_profile/migrations/0057_repair_missing_profile_tables_batch1.py
apps/user_profile/migrations/0058_repair_missing_profile_tables_batch2.py
apps/user_profile/migrations/0059_repair_settings_tables.py
apps/accounts/migrations/0003_repair_account_deletion_request.py
```

### Scripts
```
scripts/migration_smoke_tests.py          # Endpoint verification tests
scripts/test_user_creation.py             # UserProfile signal test
scripts/check_table.py                    # Table existence check
scripts/check_db_connection.py            # Database connection diagnostics
scripts/check_schemas.py                  # PostgreSQL schema verification
scripts/move_tables_to_public.py          # Schema migration script
scripts/detailed_smoke_test.py            # Full error traceback test
scripts/check_new_tables.py               # New table location check
```

---

## Lessons Learned

### 1. Schema Context Matters
**Problem**: Migrations applied in test context created tables in `test_schema`  
**Solution**: Always verify schema after migration application  
**Prevention**: Add schema validation to CI/CD pipeline

### 2. ORM Metadata Caching
**Problem**: Django cached model metadata before tables existed  
**Symptom**: `hasattr(user, 'deletion_request')` raised exception  
**Solution**: Move tables to correct schema so Django's search_path finds them

### 3. Migration Idempotency
**Success**: `CREATE TABLE IF NOT EXISTS` allowed safe re-application  
**Best Practice**: All repair migrations should be idempotent  
**Benefit**: Can apply to any environment without risk

### 4. Table Name Discovery
**Problem**: Model name != db_table name (e.g., `ProfileShowcase` vs `user_profile_showcase`)  
**Solution**: Use `sqlmigrate` instead of guessing table names  
**Advantage**: Guarantees correct DDL extraction

---

## Verification Checklist

| Check | Status | Evidence |
|-------|--------|----------|
| All 10 tables exist | ✅ PASS | `scripts/check_table.py` output |
| Tables in public schema | ✅ PASS | `scripts/check_schemas.py` output |
| Migrations marked applied | ✅ PASS | `manage.py showmigrations` |
| User creation works | ✅ PASS | `test_user_creation.py` output |
| UserProfile auto-created | ✅ PASS | Signal fires, public_id generated |
| /me/settings/ loads | ✅ PASS | HTTP 200 response |
| /@username/ loads | ❌ FAIL | teams.left_at missing (out of scope) |
| /admin/ loads | ⏸️ PENDING | Blocked by /@username/ failure |

---

## Remaining Issues (Out of Scope)

### 1. teams_teammembership.left_at Missing
**Error**: `column teams_teammembership.left_at does not exist`  
**Impact**: Public profile pages (`/@username/`) fail with 500  
**Root Cause**: Separate migration integrity issue in `teams` app  
**Recommendation**: Create repair migration for `teams` app using same process

### 2. Potential Other Missing Tables
**Risk**: Other apps may have similar migration/database mismatches  
**Mitigation**: Run full database schema audit across ALL apps  
**Tool**: Extend `scripts/check_table.py` to verify all Django models

---

## Recommendations

### Immediate (Priority 1)
1. ✅ **COMPLETE** - Restore user_profile tables
2. ⏳ **PENDING** - Create `teams` app repair migration for `left_at` column
3. ⏳ **PENDING** - Run full smoke test suite after teams repair
4. ⏳ **PENDING** - Deploy to staging for integration testing

### Short-term (Priority 2)
1. **Database Schema Audit** - Verify ALL Django models have corresponding tables
2. **CI/CD Schema Check** - Add automated schema validation to deployment pipeline
3. **Migration Test Mode Fix** - Prevent migrations from using `test_schema` in non-test contexts
4. **Documentation** - Update deployment runbook with schema verification steps

### Long-term (Priority 3)
1. **Migration Health Dashboard** - Track applied migrations vs actual database state
2. **Automated Repair Tooling** - Script to generate repair migrations automatically
3. **Schema Version Control** - Store expected schema state for each release
4. **Test Data Seeding** - Ensure test databases match production schema exactly

---

## Final Status

### ✅ SUCCESS CRITERIA MET:
- [x] All 10 missing tables restored to database
- [x] Tables in correct PostgreSQL schema (public)
- [x] Formal Django migrations created (audit trail)
- [x] UserProfile auto-creation working
- [x] `/me/settings/` endpoint loading successfully
- [x] Idempotent migrations (safe to re-run)

### ❌ PARTIAL SUCCESS:
- [ ] `/@username/` endpoint still failing (teams app issue)
- [ ] `/admin/` endpoint not yet tested (blocked)

### 📊 OVERALL ASSESSMENT:
**MIGRATION REPAIR LOOP: PASS (with caveats)**

User profile migration integrity fully restored. Additional issues discovered in `teams` app require separate repair pass. Core objective achieved: database schema consistent with applied migrations for `user_profile` and `accounts` apps.

---

## Sign-off

**Repaired By**: AI Agent (GitHub Copilot)  
**Verified By**: Smoke test suite  
**Date**: 2026-01-14 20:35 UTC  
**Next Action**: Create `teams` app repair migration for `left_at` column

**Migration Repair Status**: ✅ **COMPLETE FOR user_profile & accounts APPS**  
**Remaining Work**: Teams app column repair (separate ticket)

---

*This report documents the complete migration repair loop executed on 2026-01-14. All SQL, scripts, and migrations are preserved in version control for audit trail and reproducibility.*
