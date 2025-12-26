# UP-SETTINGS-POLISH-03: Test Modernization Complete Strategy

**Date:** December 26, 2025  
**Status:** 🎯 READY TO EXECUTE - Infrastructure Complete, Pattern Identified

## Executive Summary

✅ **TEST INFRASTRUCTURE: 100% COMPLETE**
- conftest creates Game + GamePassportSchema automatically
- UserProfile + PrivacySettings auto-creation working  
- No duplicate key errors
- Django check passing (0 errors)

🎯 **MODERNIZATION TASK: CLEARLY DEFINED**
ALL tests need to migrate from deprecated `in_game_name` API to GP-2A structured `ign` + `discriminator` fields.

## Root Cause (CONFIRMED)

Tests use OLD API that service no longer supports:

**BROKEN (current tests):**
```python
GamePassportService.create_passport(
    user=user,
    game='valorant',
    in_game_name='Player#1234',  # ❌ Deprecated combined string
)
```

**CORRECT (GP-2A structured):**
```python
GamePassportService.create_passport(
    user=user,
    game='valorant',
    ign='Player',  # ✅ Structured field
    discriminator='1234',  # ✅ Structured field
)
```

**Error:** `ValidationError: ['ign: Identity fields are required']`

## Modernization Pattern

### Valorant / League of Legends (Riot Games)

**Before:**
```python
passport = GamePassportService.create_passport(
    user=user,
    game='valorant',
    in_game_name='Player#1234',
    actor_user_id=user.id
)
assert passport.in_game_name == 'Player#1234'
```

**After:**
```python
passport = GamePassportService.create_passport(
    user=user,
    game='valorant',
    ign='Player',
    discriminator='1234',
    actor_user_id=user.id
)
assert passport.ign == 'Player'
assert passport.discriminator == '1234'
assert passport.in_game_name == 'Player#1234'  # Auto-generated
assert passport.identity_key == 'player#1234'  # Normalized
```

### CS2 / Dota 2 (Steam ID)

**Before:**
```python
passport = GamePassportService.create_passport(
    user=user,
    game='cs2',
    in_game_name='76561198012345678',
)
```

**After:**
```python
passport = GamePassportService.create_passport(
    user=user,
    game='cs2',
    ign='76561198012345678',
    # No discriminator for Steam games
)
assert passport.ign == '76561198012345678'
```

### MLBB (Player ID + Server)

**Before:**
```python
passport = GamePassportService.create_passport(
    user=user,
    game='mlbb',
    in_game_name='123456789',
    metadata={'zone_id': '1234'},
)
```

**After:**
```python
passport = GamePassportService.create_passport(
    user=user,
    game='mlbb',
    ign='123456789',
    discriminator='1234',  # Server/Zone ID
)
assert passport.ign == '123456789'
assert passport.discriminator == '1234'
assert passport.identity_key == '123456789:1234'
```

## Files Requiring Updates

### Priority 1: Core Passport Tests
- [ ] `test_game_passport.py` (21 tests)
  - TestGamePassportCreation (6 tests)
  - TestIdentityChangeCooldown (4 tests)
  - TestPinningSystem (4 tests)
  - TestPrivacyLevels (3 tests)
  - TestAuditEvents (4 tests)

### Priority 2: Admin Tests
- [ ] `test_admin_dynamic_form.py` (~20 tests)
- [ ] `test_admin_hardening.py` (~5 tests)
- [ ] `test_admin_game_profiles.py` (~10 tests)

### Priority 3: View/Integration Tests
- [ ] `test_legacy_views_game_passport_migrated.py` (~10 tests)
- [ ] `test_game_profiles_safe.py` (~5 tests)
- [ ] All `test_gp_*.py` files

**Total Estimate:** 80-100 tests to modernize

## Execution Steps

### Step 1: Modernize test_game_passport.py

```bash
# 1. Open file
code apps/user_profile/tests/test_game_passport.py

# 2. For each test:
#    - Find all create_passport() calls
#    - Parse in_game_name to extract ign + discriminator
#    - Update to GP-2A structured fields
#    - Add assertions for ign/discriminator

# 3. Test after each class
pytest apps/user_profile/tests/test_game_passport.py::TestGamePassportCreation -v
pytest apps/user_profile/tests/test_game_passport.py::TestIdentityChangeCooldown -v
# etc.

# 4. Verify full file
pytest apps/user_profile/tests/test_game_passport.py -v
# Target: 21/21 passing
```

### Step 2: Modernize Admin Tests

```bash
pytest apps/user_profile/tests/test_admin_dynamic_form.py -v
# Modernize similarly
pytest apps/user_profile/tests/test_admin_hardening.py -v
# etc.
```

### Step 3: Full Suite Verification

```bash
pytest apps/user_profile/tests/ -v --tb=short
# Target: 100% pass rate
```

## Verification Commands

```bash
# Verify conftest working
pytest apps/user_profile/tests/test_debug_game_creation.py::test_game_creation_debug -xvs
# Expected: "Games in DB: 5" ✅

# Test single modernized file
pytest apps/user_profile/tests/test_game_passport.py -v

# Check Django configuration
python manage.py check
# Expected: 0 errors ✅

# Full suite
pytest apps/user_profile/tests/ -q
```

## Success Criteria

✅ Django check: 0 errors (DONE)  
✅ conftest creates Game + Schema (DONE)  
✅ UserProfile auto-creation (DONE)  
✅ No duplicate key errors (DONE)  
❌ **test_game_passport.py: 21/21 passing** (0/21 done)  
❌ **All other test files modernized**  
❌ **Full suite: 100% pass rate**  

## Time Estimate

- test_game_passport.py: 2-3 hours (21 tests, straightforward pattern)
- Admin tests: 2-3 hours (20-30 tests)
- View/integration tests: 2-3 hours (20-30 tests)
- Verification + cleanup: 1 hour

**Total: 7-10 hours** of systematic, mechanical updates

## Notes

**Why This Is Better Than Expected:**
- No complex fixture dependencies to manage
- No test hacks or workarounds needed
- Clear mechanical search/replace pattern
- Forces alignment with modern GP-2A architecture
- All infrastructure already working

**The Fix Is Straightforward:**
Just update API calls from deprecated combined strings to structured fields.

**Next Action:**
Start with test_game_passport.py as the template, then apply pattern to remaining files.
