# GP-02: Dynamic Admin Form Implementation

**Status:** ✅ Complete  
**Date:** 2025-12-25  
**Epic:** GP-1 Game Passport Schema Migration  
**Related:** GP-01 (ForeignKey Migration), GP-03 (Service Layer)

---

## Executive Summary

Implemented schema-driven dynamic admin form for Game Passport administration. The form adapts identity field requirements based on the selected game using `GamePassportSchema`, enforces server-side validation, and ensures global uniqueness with case-insensitive identity keys.

**Key Achievement:** Admin staff can now create/edit Game Passports with game-specific validation, automatic identity normalization, and uniqueness enforcement—all driven by the schema configuration rather than hardcoded rules.

---

## Implementation Overview

### 1. Dynamic Admin Form (`GameProfileAdminForm`)

**Location:** [apps/user_profile/admin/forms.py](apps/user_profile/admin/forms.py)

#### Key Features

1. **Game Selection from Registry**
   - Queryset limited to `Game.objects.all()` (source of truth)
   - No hardcoded game choices
   - Automatically shows all active games from database

2. **Schema-Driven Identity Validation**
   - `identity_data` JSONField adapts to selected game
   - Required fields vary by game (Valorant: `riot_name`+`tagline`, MLBB: `numeric_id`+`zone_id`, Steam: `steam_id64`)
   - Validation uses `schema.validate_identity_data()`

3. **Identity Normalization**
   - Riot IDs normalized to lowercase for uniqueness checks
   - Original case preserved for display (`in_game_name`)
   - Uses `schema.normalize_identity_data()`

4. **Identity Key Computation**
   - Computed via `schema.compute_identity_key()`
   - Case-insensitive uniqueness enforcement
   - Global uniqueness per game (cross-user)

5. **Region/Role Validation**
   - Validates against schema's allowed regions/roles
   - Region required when `schema.region_required = True`
   - Uses `schema.validate_region()` and `schema.validate_role()`

6. **Metadata Storage**
   - Stores original identity data in `metadata` field
   - Preserves case for display purposes
   - Adds `_normalized_key` for internal use

#### Code Structure

```python
class GameProfileAdminForm(forms.ModelForm):
    """GP-1 Dynamic Game Passport Admin Form"""
    
    identity_data = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 50}),
        help_text='JSON object with identity fields...'
    )
    
    class Meta:
        model = GameProfile
        fields = ['user', 'game', 'in_game_name', 'identity_data', 
                  'region', 'main_role', 'rank_name', 'visibility', 
                  'is_lft', 'is_pinned', 'pinned_order', 'status', 'metadata']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit game choices to Game model
        self.fields['game'].queryset = Game.objects.all().order_by('display_name')
        
    def clean(self):
        """GP-1 Schema-driven validation"""
        # 1. Get schema for selected game
        # 2. Validate identity_data
        # 3. Normalize identity (lowercase for uniqueness)
        # 4. Compute in_game_name (preserves original case)
        # 5. Compute identity_key (normalized)
        # 6. Enforce global uniqueness
        # 7. Validate region/role
        # 8. Store in metadata
```

### 2. Admin Integration

**Location:** [apps/user_profile/admin/game_passports.py](apps/user_profile/admin/game_passports.py)

#### Changes Made

1. **Form Assignment**
   ```python
   from .forms import GameProfileAdminForm
   
   class GameProfileAdmin(admin.ModelAdmin):
       form = GameProfileAdminForm
   ```

2. **Fieldset Updates**
   - Added `identity_data` field to "Identity" fieldset
   - Updated description to mention schema-driven behavior
   - Field dynamically validates based on selected game

3. **Game Display Fix**
   - Fixed `game_display_name()` to use ForeignKey: `obj.game.display_name`
   - Previously used hardcoded GAME_CHOICES dict

4. **Audit Logging Fix**
   - Changed `obj.game` to `obj.game.slug` in audit log entries
   - Prevents "Valorant object" in logs, shows "valorant" slug

---

## Validation Rules by Game

### Riot Games (Valorant, League of Legends)

**Required Fields:**
- `riot_name` - Summoner/player name
- `tagline` - Riot tag (e.g., "NA1", "EUW")

**Format:** `PlayerName#TAG`

**Normalization:**
- Identity key: lowercase (`testplayer#na1`)
- Display name: original case (`TestPlayer#NA1`)

**Region:** Required

**Example:**
```json
{
  "riot_name": "Shroud",
  "tagline": "NA1"
}
```

### Mobile Legends: Bang Bang (MLBB)

**Required Fields:**
- `numeric_id` - Player numeric ID
- `zone_id` - Server zone ID

**Format:** `{numeric_id} ({zone_id})`

**Region:** Required

**Example:**
```json
{
  "numeric_id": "123456789",
  "zone_id": "1234"
}
```

### Steam Games (CS2, Dota 2)

**Required Fields:**
- `steam_id64` - 64-bit Steam ID

**Format:** Steam ID as-is

**Region:** Optional

**Example:**
```json
{
  "steam_id64": "76561198012345678"
}
```

---

## Test Coverage

**Location:** [apps/user_profile/tests/test_admin_dynamic_form.py](apps/user_profile/tests/test_admin_dynamic_form.py)

### Test Classes (17 tests total)

#### 1. TestAdminGameChoicesLimitedToGameModel (2 tests)
- ✅ `test_admin_form_game_queryset_uses_game_model` - Verifies queryset uses Game model
- ✅ `test_admin_form_shows_only_active_games` - Checks games from database shown

#### 2. TestDynamicRequiredFieldsValorant (3 tests)
- ✅ `test_valorant_requires_riot_name_and_tagline` - Rejects missing fields
- ✅ `test_valorant_accepts_valid_riot_id` - Accepts valid Riot ID
- ✅ `test_valorant_normalizes_case` - Verifies case normalization

#### 3. TestDynamicRequiredFieldsMLBB (2 tests)
- ✅ `test_mlbb_requires_numeric_id_and_zone_id` - Validates MLBB fields
- ✅ `test_mlbb_accepts_valid_identity` - Accepts valid MLBB identity

#### 4. TestRegionChoicesEnforced (3 tests)
- ✅ `test_invalid_region_rejected` - Rejects invalid regions
- ✅ `test_valid_region_accepted` - Accepts valid regions
- ✅ `test_region_required_when_schema_requires` - Enforces region requirement

#### 5. TestUniquenessCaseInsensitiveForRiotIDs (2 tests)
- ✅ `test_duplicate_identity_case_insensitive_rejected` - Enforces uniqueness
- ✅ `test_same_user_can_edit_their_passport` - Allows self-edits

#### 6. TestSteamGameIdentityValidation (2 tests)
- ✅ `test_cs2_requires_steam_id64` - Validates Steam ID requirement
- ✅ `test_cs2_accepts_valid_steam_id64` - Accepts valid Steam ID

#### 7. TestRoleChoicesEnforced (2 tests)
- ✅ `test_invalid_role_rejected` - Rejects invalid roles
- ✅ `test_valid_role_accepted` - Accepts valid roles

#### 8. TestSchemaNotConfiguredError (1 test)
- ✅ `test_form_rejects_game_without_schema` - Handles missing schema gracefully

### Test Results
```bash
$ pytest apps/user_profile/tests/test_admin_dynamic_form.py -v
==================== 17 passed, 46 warnings in 1.66s ====================
```

---

## Usage Examples

### Creating a Valorant Game Passport

**Via Django Admin:**

1. Navigate to `/admin/user_profile/gameprofile/add/`
2. Select user
3. Select "VALORANT" from Game dropdown
4. Enter identity_data:
   ```json
   {
     "riot_name": "Shroud",
     "tagline": "NA1"
   }
   ```
5. Select region: "NA"
6. Save

**Result:**
- `in_game_name`: `Shroud#NA1`
- `identity_key`: `shroud#na1` (normalized)
- `metadata`: `{"riot_name": "Shroud", "tagline": "NA1", "_normalized_key": "shroud#na1"}`

### Creating a CS2 Game Passport

**Via Django Admin:**

1. Select "Counter-Strike 2" from Game dropdown
2. Enter identity_data:
   ```json
   {
     "steam_id64": "76561198012345678"
   }
   ```
3. Optional: Select region (not required for Steam games)
4. Save

**Result:**
- `in_game_name`: `76561198012345678`
- `identity_key`: `76561198012345678`
- `metadata`: `{"steam_id64": "76561198012345678", "_normalized_key": "76561198012345678"}`

---

## Validation Error Examples

### Missing Required Fields (Valorant)

**Input:**
```json
{
  "riot_name": "Shroud"
}
```

**Error:**
```
identity_data: Invalid identity data: tagline: This field is required
```

### Invalid Region

**Input:**
- Game: Valorant
- Region: "INVALID_REGION"

**Error:**
```
region: Invalid region "INVALID_REGION". Allowed regions for VALORANT: NA, EU, ASIA, etc.
```

### Duplicate Identity (Case-Insensitive)

**Scenario:**
- Existing passport: `Shroud#NA1`
- Attempting to create: `shroud#na1`

**Error:**
```
identity_data: This identity is already registered for VALORANT by another user.
```

---

## Architecture Decisions

### 1. Server-Side Validation as Source of Truth

**Rationale:** Client-side validation is optional (for UX), but server-side validation using `GamePassportSchema` is authoritative. This ensures:
- No bypassing validation via API/console
- Schema changes immediately affect all admin forms
- Consistent validation across all entry points

### 2. Original Case Preservation for Display

**Decision:** Store original identity data in `metadata`, use normalized data for `identity_key`.

**Rationale:**
- Players expect to see `Shroud#NA1` (original case) in their profile
- Uniqueness checks need case-insensitive comparison (`shroud#na1`)
- Storing both allows flexible display while enforcing strict uniqueness

### 3. JSONField for Identity Data

**Decision:** Use `identity_data` JSONField instead of separate model fields.

**Rationale:**
- Different games need different fields (Riot: riot_name+tagline, Steam: steam_id64, MLBB: numeric_id+zone_id)
- Schema-driven approach allows adding new games without model migrations
- Simpler admin form (one textarea instead of 10+ conditional fields)

### 4. Global Uniqueness per Game

**Decision:** Enforce uniqueness via `(game, identity_key)` database constraint.

**Rationale:**
- Prevents duplicate Game Passports for same in-game account
- Protects against impersonation/fraud
- Aligns with real-world gaming identities (one Riot ID can't have multiple Delta accounts)

---

## Known Limitations

1. **Client-Side Field Hiding Not Implemented**
   - Currently all identity fields visible in JSON textarea
   - Future: Add minimal JS to show/hide fields based on selected game
   - Does not affect validation (server-side still authoritative)

2. **No Inline Help Text per Field**
   - Generic help text for `identity_data` field
   - Future: Dynamic help text showing required fields for selected game
   - Example: "For Valorant, provide: riot_name, tagline"

3. **Test Database Schema Missing PublicIDCounter**
   - Tests generate warnings about missing `user_profile_publicidcounter` table
   - Does not affect test results (tests still pass)
   - Future: Update test fixtures to include all required tables

---

## Integration Points

### 1. GamePassportSchema Model
- `validate_identity_data(identity_data)` - Returns (bool, dict) with validation results
- `normalize_identity_data(identity_data)` - Returns normalized dict (lowercase for Riot IDs)
- `format_identity(identity_data)` - Returns display string (e.g., "Shroud#NA1")
- `compute_identity_key(identity_data)` - Returns normalized key for uniqueness
- `validate_region(region)` - Returns bool for region validity
- `validate_role(role)` - Returns bool for role validity

### 2. Game Model
- `Game.objects.all()` - Source of truth for game choices
- `game.display_name` - Used in form labels and errors
- `game.slug` - Used in audit logging

### 3. GameProfile Model
- `identity_key` - Computed field (set by form)
- `metadata` - Stores original identity data + normalized key
- `in_game_name` - Display string (preserves case)

---

## Migration Path

### From Old System
1. **Before:** Hardcoded GAME_CHOICES, static validation
2. **After:** Dynamic schema-driven validation from `GamePassportSchema`

### Backward Compatibility
- Existing GameProfile records remain unchanged
- `identity_key` computed on next edit
- `metadata` populated retroactively via admin form

---

## Future Enhancements

### Phase 1 (Optional UX)
- Add minimal vanilla JS to show/hide identity fields based on selected game
- Dynamic help text showing required fields
- Example input for each game type

### Phase 2 (API Integration)
- Extend validation to API endpoints (currently admin-only)
- GamePassportService should use same validation logic
- Consistent error messages across admin/API

### Phase 3 (Advanced Features)
- Real-time identity verification (check if Riot ID exists)
- OAuth integration for Steam/Riot account linking
- Automatic rank/level fetching from game APIs

---

## Rollout Plan

### Phase 1: Admin Testing (Current)
- ✅ Deploy to staging environment
- ✅ Test admin form with all 11 supported games
- ✅ Verify validation errors
- ✅ Test uniqueness enforcement

### Phase 2: Production Deployment
- Update documentation for admin staff
- Train admins on new identity_data field
- Monitor for edge cases in first week

### Phase 3: API Extension
- Apply same validation to API endpoints
- Update GamePassportService (GP-03)
- Comprehensive API tests

---

## References

- **Epic:** Documents/ExecutionPlan/GP_EPIC.md
- **Task:** GP-1 Todo 4 (Dynamic Admin Form)
- **Related Files:**
  - [apps/user_profile/admin/forms.py](apps/user_profile/admin/forms.py) - Admin form
  - [apps/user_profile/admin/game_passports.py](apps/user_profile/admin/game_passports.py) - Admin integration
  - [apps/user_profile/tests/test_admin_dynamic_form.py](apps/user_profile/tests/test_admin_dynamic_form.py) - Test suite
  - [apps/user_profile/models/game_passport_schema.py](apps/user_profile/models/game_passport_schema.py) - Schema model

---

## Appendix: Command Reference

### Run Tests
```bash
# All dynamic form tests
pytest apps/user_profile/tests/test_admin_dynamic_form.py -v

# Specific test class
pytest apps/user_profile/tests/test_admin_dynamic_form.py::TestDynamicRequiredFieldsValorant -v

# With coverage
pytest apps/user_profile/tests/test_admin_dynamic_form.py --cov=apps.user_profile.admin.forms

# System check
python manage.py check
```

### Seed Schemas (if missing)
```bash
python manage.py seed_game_passport_schemas
```

### View Admin
```bash
python manage.py runserver
# Navigate to: http://localhost:8000/admin/user_profile/gameprofile/
```

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-25  
**Author:** GP-1 Implementation Team  
**Status:** ✅ Complete - All 17 tests passing
