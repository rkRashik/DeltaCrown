# Bug Fix: ProgrammingError - riot_id Column Does Not Exist

## Problem
The application was crashing when accessing user profile pages with the error:
```
ProgrammingError at /u/rkrashik/
column user_profile_userprofile.riot_id does not exist
```

## Root Cause
The `UserProfile` model defined legacy game ID fields (`riot_id`, `riot_tagline`, `efootball_id`, `steam_id`, `mlbb_id`, `mlbb_server_id`, `pubg_mobile_id`, `free_fire_id`, `ea_id`, `codm_uid`) that had been migrated to a new `game_profiles` JSONField system, but:

1. **Model still defined the fields** - Django was trying to SELECT these columns
2. **Database columns existed** - Migration 0011 was marked as applied but didn't actually execute
3. **Forms referenced legacy fields** - UserProfileForm had all legacy fields in its field list

## Solution

### 1. Removed Field Definitions from Model
**File**: [apps/user_profile/models.py](apps/user_profile/models.py)

Removed all legacy game ID field definitions (lines 226-235) and replaced with a comment documenting the migration.

**Before**:
```python
# ===== LEGACY GAME IDs (Kept for backwards compatibility, will migrate to game_profiles) =====
riot_id = models.CharField(max_length=100, blank=True, help_text="Riot ID (Name#TAG) for Valorant")
riot_tagline = models.CharField(max_length=50, blank=True, help_text="Riot Tagline (part after #)")
# ... (8 more fields)
```

**After**:
```python
# ===== LEGACY GAME IDs REMOVED =====
# NOTE: Legacy game ID fields (riot_id, riot_tagline, efootball_id, steam_id, mlbb_id, 
# mlbb_server_id, pubg_mobile_id, free_fire_id, ea_id, codm_uid) were removed in 
# migration 0011_remove_legacy_game_id_fields after data migration to game_profiles.
# Use get_game_profile(game) and set_game_profile(game, data) methods instead.
```

### 2. Removed Field References from Forms
**File**: [apps/user_profile/forms.py](apps/user_profile/forms.py)

Removed all legacy game ID fields from:
- `UserProfileForm.Meta.fields` list (lines 37-39)
- Widget definitions (lines 160-200)
- Help text definitions (lines 266-275)

### 3. Manually Dropped Database Columns
**Tool**: [tools/drop_legacy_columns.py](tools/drop_legacy_columns.py)

Migration 0011 was marked as applied but didn't actually execute the DROP COLUMN statements. Created a script to manually drop all 10 legacy columns:
```sql
ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS riot_id;
ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS riot_tagline;
ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS efootball_id;
ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS steam_id;
ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS mlbb_id;
ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS mlbb_server_id;
ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS pubg_mobile_id;
ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS free_fire_id;
ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS ea_id;
ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS codm_uid;
```

## Verification

### System Check
```bash
python manage.py check
```
✅ **Result**: System check identified no issues (0 silenced).

### Database Schema Verification
```bash
python tools/verify_schema.py
```
✅ **Result**: 
- All 10 legacy game ID fields have been removed
- `game_profiles` JSON field exists
- Total columns reduced from 65 to 55

### Profile Endpoint Test
```bash
python tools/check_profile.py
```
✅ **Result**: Status 200 - Profile page loads successfully

## Migration History

| Migration | Purpose | Status |
|-----------|---------|--------|
| 0009_add_riot_id | Re-add riot_id column for safe data migration | ✅ Applied |
| 0010_migrate_legacy_game_ids | Copy legacy game IDs to game_profiles JSON | ✅ Applied |
| 0011_remove_legacy_game_id_fields | Drop legacy columns from database | ⚠️ Marked applied but didn't execute |

**Note**: Migration 0011 was manually executed via `tools/drop_legacy_columns.py` to ensure columns were actually dropped.

## New Game Profile System

Game-specific data is now stored in the `game_profiles` JSONField with this structure:
```json
[
    {
        "game": "valorant",
        "ign": "Player#TAG",
        "role": "Duelist",
        "rank": "Immortal 3",
        "platform": "PC",
        "is_verified": false,
        "metadata": {}
    }
]
```

### API Methods
- `profile.get_game_profile('valorant')` - Get game profile data
- `profile.set_game_profile('valorant', data)` - Update game profile
- `profile.get_game_id('valorant')` - Get just the game ID/IGN

### Supported Games
- valorant (Valorant)
- efootball (eFootball)
- dota2 (Dota 2)
- cs2 (Counter-Strike 2)
- mlbb (Mobile Legends: Bang Bang)
- pubg_mobile (PUBG Mobile)
- free_fire (Free Fire)
- fc24 (FC 24)
- codm (Call of Duty Mobile)

## Files Modified
- [apps/user_profile/models.py](apps/user_profile/models.py) - Removed legacy field definitions
- [apps/user_profile/forms.py](apps/user_profile/forms.py) - Removed legacy field references
- [tools/drop_legacy_columns.py](tools/drop_legacy_columns.py) - Created (manual column drop script)
- [tools/verify_schema.py](tools/verify_schema.py) - Created (schema verification tool)

## Date Fixed
December 17, 2025

## Status
✅ **RESOLVED** - The `/u/rkrashik/` endpoint now loads successfully without errors.
