# UP-M1 Changelog: Public ID System

## Date: December 23, 2025

### Summary
Completed public ID migrations and verification. All code, migrations, tests, and management commands in place.

### Files Created
1. **apps/user_profile/tests/test_public_id.py** (9 tests)
   - Signal auto-assignment tests
   - Backfill tests
   - Format validation tests
   - Generator service tests

2. **apps/user_profile/management/commands/backfill_public_ids.py**
   - Dry-run mode: `--dry-run`
   - Limit mode: `--limit N`
   - Full backfill: no flags

### Migrations Applied
- **0015_alter_useractivity_event_type**: Fixed event_type field
- **0016_restore_publicidcounter**: Restored PublicIDCounter table (deleted in 0014, needed by public_id service)

### Test Results
```
pytest apps/user_profile/tests/ --tb=no
51 collected, 51 passed, 0 failed
```

**Breakdown:**
- UP-M0 tests: 0 (no M0 tests)
- UP-M1 tests: 9 (public_id system)
- UP-M2 tests: 31 (activity log, stats, backfill)
- UP-M3 tests: 11 (economy sync, signal, reconcile)

### Key Features
1. **Automatic assignment**: Signal assigns public_id on User creation
2. **Backfill support**: Signal assigns public_id to legacy profiles on next User.save()
3. **Idempotent**: Repeated saves don't change public_id
4. **Format**: DC-YY-NNNNNN (e.g., DC-25-000042)
5. **Thread-safe**: Atomic counter allocation with select_for_update()

### Management Commands
```bash
# Dry-run (no changes)
python manage.py backfill_public_ids --dry-run

# Backfill up to 100 profiles
python manage.py backfill_public_ids --limit 100

# Backfill all missing public_ids
python manage.py backfill_public_ids
```

### Notes
- PublicIDCounter table was accidentally deleted in migration 0014 (UP-M2)
- Migration 0016 restored it with proper schema
- All existing profiles in production will need backfill (run command before deployment)
- Signal handles auto-assignment for new users going forward
