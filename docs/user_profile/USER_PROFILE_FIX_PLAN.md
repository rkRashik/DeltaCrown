# User Profile & Game System Fix Plan

## Issues Identified

### 1. Game Count Discrepancy ✅
- **Problem**: Old seed script `apps/games/management/commands/seed_default_games.py` has 9 games
- **Solution**: Use new script `scripts/Seed_Game/seed_2025_games.py` with 11 games as default
- **Games**: Valorant, CS2, Dota 2, EA FC 26, eFootball, PUBG Mobile, MLBB, Free Fire, CODM, Rocket League, Rainbow Six Siege

### 2. Legacy Game ID Fields ❌
- **Problem**: UserProfile has both `game_profiles` (JSONB) AND legacy fields (riot_id, steam_id, mlbb_id, etc.)
- **Current State**:
  ```python
  # GOOD (Modern):
  game_profiles = models.JSONField(default=list)  # Flexible, supports all games
  
  # BAD (Legacy):
  riot_id = models.CharField(...)
  steam_id = models.CharField(...)
  mlbb_id = models.CharField(...)
  pubg_mobile_id = models.CharField(...)
  free_fire_id = models.CharField(...)
  ea_id = models.CharField(...)
  codm_uid = models.CharField(...)
  efootball_id = models.CharField(...)
  mlbb_server_id = models.CharField(...)
  riot_tagline = models.CharField(...)
  ```

- **Solution**: Remove ALL legacy fields, use ONLY `game_profiles` JSONB array

### 3. Modern UI Requirements
- Easy to add/edit game IDs
- Dynamic form based on selected game
- Validation from GamePlayerIdentityConfig
- Support for all 11 games
- Clean, modern interface

## Implementation Plan

### Phase 1: Copy New Game Script ✅
- Copy `scripts/Seed_Game/seed_2025_games.py` to `apps/games/management/commands/seed_default_games.py`
- Update imports and paths
- Test execution

### Phase 2: Remove Legacy Fields ✅
- Create migration to remove legacy fields from UserProfile:
  - riot_id, riot_tagline
  - steam_id
  - mlbb_id, mlbb_server_id
  - pubg_mobile_id
  - free_fire_id
  - ea_id
  - codm_uid
  - efootball_id
- Remove legacy helper methods (`get_game_id`, `set_game_id`, etc.)
- Keep only `game_profiles` JSONB field

### Phase 3: Enhance game_profiles Structure ✅
```python
game_profiles = [
    {
        "game_slug": "valorant",           # Links to Game.slug
        "game_identity": {
            "riot_id": "Player#TAG",       # Dynamic based on GamePlayerIdentityConfig
        },
        "rank": "Immortal 3",              # Optional
        "role": "Duelist",                 # Optional, validates against GameRole
        "region": "SEA",                   # Optional
        "is_primary": True,                # One primary game per user
        "is_verified": False,              # Verification status
        "added_at": "2025-12-16T10:30:00Z",
        "metadata": {}                     # Extensible
    },
    {
        "game_slug": "cs2",
        "game_identity": {
            "steam_id": "76561198000000000"
        },
        "rank": "Global Elite",
        "role": "AWPer",
        "is_primary": False,
        "is_verified": False,
        "added_at": "2025-12-16T11:00:00Z",
        "metadata": {}
    }
]
```

### Phase 4: API & Forms ✅
- Create serializer for game profile management
- Create form that:
  1. Shows dropdown of all 11 games
  2. When game selected, shows appropriate identity fields based on GamePlayerIdentityConfig
  3. Validates input against validation_regex
  4. Allows adding multiple games
  5. Shows existing game profiles with edit/delete options
- Modern HTMX or Alpine.js UI

### Phase 5: Integration Points ✅
- Update team membership to read from game_profiles
- Update tournament registration to read from game_profiles
- Update player verification flows
- Update admin panel
- Update serializers
- Update all references to legacy fields

### Phase 6: Testing ✅
- Test adding game ID for each of 11 games
- Test validation (correct format rejection)
- Test team registration with new system
- Test tournament registration
- Ensure backward compatibility (if needed)

## File Changes Required

### 1. `apps/games/management/commands/seed_default_games.py`
- Replace with new 2025 script content
- Update imports for Django management command structure

### 2. `apps/user_profile/models.py`
- Remove all legacy game ID fields
- Keep only `game_profiles` JSONB
- Remove legacy helper methods
- Add new game profile helper methods with proper validation

### 3. `apps/user_profile/migrations/XXXX_remove_legacy_game_fields.py`
- New migration to remove legacy fields

### 4. `apps/user_profile/forms.py`
- Create GameProfileForm
- Dynamic field generation based on game selection

### 5. `apps/user_profile/serializers.py`
- Update UserProfileSerializer
- Add GameProfileSerializer

### 6. `apps/user_profile/views.py`
- Add game profile management views

### 7. `apps/user_profile/urls.py`
- Add game profile endpoints

### 8. Templates (if exists)
- Update profile edit template
- Add game profile management UI

### 9. `apps/teams/models.py` (if needed)
- Update references to game IDs

### 10. `apps/tournaments/models.py` (if needed)
- Update references to game IDs

## Success Criteria

✅ All 11 games from 2025 script are in database
✅ UserProfile has NO legacy game ID fields
✅ UserProfile.game_profiles works for all 11 games
✅ Users can easily add/edit game IDs via modern UI
✅ Validation works per game (Riot ID format for Valorant, Steam ID for CS2, etc.)
✅ Team registration reads from game_profiles
✅ Tournament registration reads from game_profiles
✅ All existing references updated
✅ Tests pass

## Rollback Plan

If issues arise:
1. Keep legacy fields in model (mark deprecated)
2. Dual-write to both legacy and game_profiles
3. Gradual migration over time
4. Final cutover after thorough testing

## Timeline

- Phase 1: 10 minutes (copy script)
- Phase 2: 15 minutes (migration)
- Phase 3: 20 minutes (enhance model)
- Phase 4: 30 minutes (forms/API)
- Phase 5: 45 minutes (integration)
- Phase 6: 30 minutes (testing)
- **Total**: ~2.5 hours

## Status: IN PROGRESS

Current Step: Phase 1 - Starting implementation
