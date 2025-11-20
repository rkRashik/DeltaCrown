# Tournament App - Game Registry Integration

**Date:** 2025-11-20  
**Status:** ✅ COMPLETE  
**Component:** Tournament App (Admin, Forms, Services, Views)

## Overview

Successfully integrated the Game Registry into the Tournament app, matching the Teams app implementation. All tournament creation, editing, and game-related logic now uses canonical games from the unified Game Registry instead of legacy game choices or hardcoded lists.

**Key Achievement:** Database schema remains unchanged - only choice sources and validation logic were updated.

---

## Changes Made

### 1. Tournament Admin (`apps/tournaments/admin.py`)

#### Added Game Registry Imports
```python
from apps.common.game_registry import get_all_games, normalize_slug
```

#### Updated `TournamentAdmin.formfield_for_foreignkey()`
**What Changed:**
- Game dropdown now filters to **only canonical games** from Game Registry
- Display names use `GameSpec.display_name` (e.g., "Mobile Legends: Bang Bang" instead of "MLBB")
- Automatically matches Game model records to registry via slug + legacy aliases
- Organizer dropdown restricted to staff users (unchanged)

**Code:**
```python
elif db_field.name == 'game':
    # Filter to only show games that exist in Game Registry (canonical games)
    canonical_slugs = [spec.slug for spec in get_all_games()]
    # Normalize existing game slugs and filter
    game_ids = []
    for game in Game.objects.filter(is_active=True):
        normalized = normalize_slug(game.slug)
        if normalized in canonical_slugs:
            game_ids.append(game.id)
    kwargs['queryset'] = Game.objects.filter(id__in=game_ids, is_active=True)
    # Override label to show display_name from registry
    if 'widget' not in kwargs:
        from django import forms
        choices = [('', '---------')]
        for spec in get_all_games():
            matching_games = Game.objects.filter(
                slug__in=[spec.slug] + list(spec.legacy_aliases), 
                is_active=True
            )
            if matching_games.exists():
                game = matching_games.first()
                choices.append((game.id, spec.display_name))
        kwargs['widget'] = forms.Select(choices=choices)
```

**Result:**
- ✅ Organizers see only 9 canonical games: Valorant, CS2, Dota 2, eFootball, FC 26, MLBB, CODM, Free Fire, PUBG
- ✅ Display names are user-friendly ("Mobile Legends: Bang Bang" not "mlbb")
- ✅ Legacy Game records filtered out automatically

---

### 2. Game Admin (`apps/tournaments/admin.py`)

#### Added Registry Status Column
**What Changed:**
- New `registry_status` column shows whether game is **CANONICAL** (in registry) or **LEGACY** (not in registry)
- Visual indicators:
  - 🟢 **CANONICAL** - Green badge for games in Game Registry
  - 🟠 **LEGACY** - Orange badge for old/deprecated games

**Code:**
```python
def registry_status(self, obj):
    """Display whether game is in Game Registry (canonical)"""
    normalized = normalize_slug(obj.slug)
    canonical_slugs = [spec.slug for spec in get_all_games()]
    if normalized in canonical_slugs:
        return format_html(
            '<span style="background: #4CAF50; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">✓ CANONICAL</span>'
        )
    return format_html(
        '<span style="background: #FF9800; color: white; padding: 3px 8px; '
        'border-radius: 3px; font-size: 11px;">⚠ LEGACY</span>'
    )
```

**Result:**
- ✅ Admins can instantly see which games are canonical vs legacy
- ✅ Helps identify games needing migration/cleanup

---

### 3. Tournament Create Form (`apps/tournaments/forms/tournament_create.py`)

#### Replaced Legacy `GAME_DATA` Import
**Before:**
```python
from apps.common.game_assets import GAME_DATA
```

**After:**
```python
from apps.common.game_registry import get_all_games, get_game, normalize_slug
```

#### Updated Form Initialization
**What Changed:**
- Game dropdown populated from `get_all_games()` instead of `GAME_DATA`
- Matches Game model instances to registry specs via slug/aliases
- Shows `GameSpec.display_name` as labels

**Code:**
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Populate game choices from Game Registry (canonical games only)
    game_choices = [('', 'Select a game...')]
    
    # Get all canonical games from registry
    for spec in get_all_games():
        # Find matching Game model instance (by slug or legacy aliases)
        matching_games = Game.objects.filter(
            slug__in=[spec.slug] + list(spec.legacy_aliases),
            is_active=True
        )
        if matching_games.exists():
            game = matching_games.first()
            game_choices.append((game.id, spec.display_name))
    
    self.fields['game'].widget = forms.Select(
        choices=game_choices,
        attrs={'class': 'form-select'}
    )
```

**Result:**
- ✅ Organizers creating tournaments see only canonical games
- ✅ Consistent with admin interface
- ✅ No more references to legacy `GAME_DATA` dict

---

### 4. Tournament Services (6 files updated)

#### `registration_service.py`
**What Changed:**
- Uses `get_game()` to fetch `profile_id_field` from registry
- Falls back to `tournament.game.profile_id_field` if not in registry

**Code:**
```python
# Get game-specific ID field from Game Registry
from apps.common.game_registry import get_game, normalize_slug
canonical_slug = normalize_slug(tournament.game.slug)
game_spec = get_game(canonical_slug)
game_id_field = game_spec.profile_id_field if game_spec else tournament.game.profile_id_field
game_id = getattr(profile, game_id_field, None)
```

#### `tournament_service.py`
**What Changed:**
- Game change logging uses `GameSpec.display_name` instead of `game.name`
- Normalizes slugs before comparison

**Code:**
```python
if 'game_id' in data:
    try:
        from apps.common.game_registry import get_game, normalize_slug
        new_game = Game.objects.get(id=data['game_id'], is_active=True)
        if tournament.game != new_game:
            # Use Game Registry display names if available
            old_slug = normalize_slug(tournament.game.slug)
            new_slug = normalize_slug(new_game.slug)
            old_spec = get_game(old_slug)
            new_spec = get_game(new_slug)
            old_name = old_spec.display_name if old_spec else tournament.game.name
            new_name = new_spec.display_name if new_spec else new_game.name
            changes.append(f"game: {old_name} → {new_name}")
            tournament.game = new_game
```

#### `leaderboard.py`
**What Changed:**
- Normalizes `tournament.game.slug` before use

**Code:**
```python
from apps.common.game_registry import normalize_slug
game_slug = normalize_slug(tournament.game.slug) if hasattr(tournament, 'game') and tournament.game else ''
```

#### `analytics_service.py`
**What Changed:**
- Normalizes game slug for analytics tracking

**Code:**
```python
from apps.common.game_registry import normalize_slug
game_slug = normalize_slug(reg.tournament.game.slug) if reg.tournament.game else ''
```

---

### 5. Tournament Views (3 files updated)

#### `group_stage.py`
**What Changed:**
- Normalizes game slug before passing to `GroupStageService.calculate_standings()`
- Updated stat column logic to use **canonical slugs** instead of legacy slugs
  - `pubg-mobile` → `pubg`
  - `free-fire` → `freefire`
  - `mobile-legends` → `mlbb`
  - `call-of-duty-mobile` → `codm`
  - `fifa`, `fc-mobile` → `fc26`
- Added `game_slug` to context (already normalized)

**Code:**
```python
from apps.common.game_registry import normalize_slug
canonical_slug = normalize_slug(tournament.game.slug)
standings = GroupStageService.calculate_standings(
    group_id=group.id,
    game_slug=canonical_slug
)

# Stat columns now use canonical slugs
if game_slug in ['efootball', 'fc26']:
    stat_columns = ['goals_for', 'goals_against', 'goal_difference']
elif game_slug in ['pubg', 'freefire']:
    stat_columns = ['total_kills', 'placement_points', 'average_placement']
elif game_slug == 'mlbb':
    stat_columns = ['total_kills', 'total_deaths', 'total_assists', 'kda_ratio']
elif game_slug == 'codm':
    stat_columns = ['total_kills', 'total_deaths', 'total_score']
```

#### `spectator.py`
**What Changed:**
- Normalizes slug before calling `GroupStageService._get_game_columns()`

**Code:**
```python
if context['has_groups'] and tournament.game:
    from apps.common.game_registry import normalize_slug
    canonical_slug = normalize_slug(tournament.game.slug)
    context['game_columns'] = GroupStageService._get_game_columns(canonical_slug)
```

#### `registration.py`
**What Changed:**
- Custom field labels use `GameSpec.display_name` instead of `tournament.game.name`
- Registration summary shows canonical game name
- Falls back to `tournament.game.name` if game not in registry

**Code:**
```python
# Custom fields step
from apps.common.game_registry import get_game, normalize_slug
canonical_slug = normalize_slug(tournament.game.slug)
game_spec = get_game(canonical_slug)
game_display_name = game_spec.display_name if game_spec else tournament.game.name

context['custom_fields'] = [
    {
        'name': 'in_game_id',
        'label': f'{game_display_name} In-Game ID',
        'type': 'text',
        'required': True,
        'help_text': 'Your player ID or username in the game',
        'current_value': custom_field_values.get('in_game_id', ''),
    }
]

# Summary step
context['summary'] = {
    'game': game_display_name,
    # ... other fields
}
```

---

## Files Modified

### Admin & Forms
1. `apps/tournaments/admin.py` - TournamentAdmin game filtering, GameAdmin status column
2. `apps/tournaments/forms/tournament_create.py` - Game choices from registry

### Services
3. `apps/tournaments/services/registration_service.py` - Game profile field lookup
4. `apps/tournaments/services/tournament_service.py` - Game change logging
5. `apps/tournaments/services/leaderboard.py` - Slug normalization
6. `apps/tournaments/services/analytics_service.py` - Slug normalization

### Views
7. `apps/tournaments/views/group_stage.py` - Standings calculation, stat columns
8. `apps/tournaments/views/spectator.py` - Game columns
9. `apps/tournaments/views/registration.py` - Custom fields, summary display

**Total:** 9 files modified

---

## Old Logic Removed

### Hardcoded Game Lists/References Eliminated:
1. ❌ `from apps.common.game_assets import GAME_DATA` (tournament_create.py)
2. ❌ Direct `tournament.game.slug` comparisons without normalization
3. ❌ Legacy slug patterns:
   - `pubg-mobile` → now `pubg`
   - `free-fire` → now `freefire`
   - `mobile-legends` → now `mlbb`
   - `call-of-duty-mobile` → now `codm`
   - `fifa`, `fc-mobile` → now `fc26`

### Replaced With:
- ✅ `from apps.common.game_registry import get_all_games, get_game, normalize_slug`
- ✅ `normalize_slug(tournament.game.slug)` before all comparisons
- ✅ `GameSpec.display_name` for user-facing labels
- ✅ `GameSpec.profile_id_field` for game-specific logic

---

## Organizer Experience Changes

### Before Integration:
- Tournament admin showed all games in database (including legacy/inactive)
- Game names inconsistent (sometimes "MLBB", sometimes "Mobile Legends")
- No visual indicator of which games were supported
- Hardcoded game logic scattered across files

### After Integration:
- **Admin Interface:**
  - Only 9 canonical games shown in dropdown
  - Display names: "Mobile Legends: Bang Bang", "Counter-Strike 2", etc.
  - GameAdmin shows CANONICAL/LEGACY badges

- **Organizer Console:**
  - Tournament creation form shows same 9 canonical games
  - Consistent naming across all interfaces
  - User-friendly labels instead of slugs

- **Game Logic:**
  - All slug comparisons use normalized values
  - Profile ID fields pulled from registry
  - Stat columns automatically match game type

---

## Database Impact

**IMPORTANT:** No database schema changes made.

- ✅ `Tournament.game` FK remains unchanged
- ✅ `Game` model fields unchanged
- ✅ Existing tournaments still load correctly
- ✅ Legacy Game records filtered from choices (not deleted)

### Migration Path:
If you want to clean up legacy games:
1. Identify LEGACY games via GameAdmin (orange badge)
2. Check if any tournaments reference them
3. Update/migrate those tournaments to canonical games
4. Optionally soft-delete or archive legacy Game records

---

## Backwards Compatibility

All changes include fallback logic:

```python
# Example: registration_service.py
game_spec = get_game(canonical_slug)
game_id_field = game_spec.profile_id_field if game_spec else tournament.game.profile_id_field
```

**If a game is NOT in the registry:**
- Uses `tournament.game.name` instead of `GameSpec.display_name`
- Uses `tournament.game.profile_id_field` instead of registry field
- Still displays in admin with LEGACY badge
- Still works for existing tournaments

---

## Testing Results

### Django System Check:
```bash
python manage.py check
# System check identified no issues (0 silenced).
```

### Manual Verification:
- ✅ TournamentAdmin game dropdown shows 9 canonical games
- ✅ GameAdmin shows CANONICAL/LEGACY status
- ✅ TournamentCreateForm shows correct game choices
- ✅ All imports resolve correctly
- ✅ No Python syntax errors
- ✅ All services import Game Registry successfully

---

## Canonical Game Slugs

The Tournament app now recognizes these 9 games from the registry:

| Canonical Slug | Display Name | Legacy Aliases |
|----------------|--------------|----------------|
| `valorant` | Valorant | - |
| `cs2` | Counter-Strike 2 | csgo, counter-strike, cs:go |
| `dota2` | Dota 2 | dota, dota-2 |
| `efootball` | eFootball | pes, pro-evolution-soccer |
| `fc26` | FC 26 | fifa, fc-mobile, fifa-26 |
| `mlbb` | Mobile Legends: Bang Bang | mobile-legends, mobile-legends-bang-bang |
| `codm` | Call of Duty: Mobile | call-of-duty-mobile, cod-mobile |
| `freefire` | Free Fire | free-fire, garena-free-fire |
| `pubg` | PUBG | pubg-mobile, battlegrounds, playerunknown-battlegrounds |

---

## Related Documentation

- [Game Registry Package](apps/common/game_registry/README.md)
- [Teams App Integration](TEAM_CREATE_V2_COMPLETE.md)
- [Tournament View Integration](TOURNAMENT_HERO_GAME_REGISTRY_INTEGRATION.md)

---

## Next Steps (Optional)

### Recommended:
1. **Audit Existing Tournaments:**
   - Run report to find tournaments using legacy game slugs
   - Bulk update to canonical slugs if needed

2. **Clean Up Legacy Games:**
   - Review LEGACY games in GameAdmin
   - Migrate/archive unused legacy Game records

3. **Update Documentation:**
   - Organizer guide showing new canonical game names
   - Admin guide for managing games

### Future Enhancements:
- Use `GameSpec.colors` for dynamic tournament theming
- Use `GameSpec.regions` for regional tournament filtering
- Use `GameSpec.roles` in registration forms
- Use `GameSpec.min_team_size`/`max_team_size` for validation

---

**Completion Status:** ✅ All tournament admin, forms, services, and views now use Game Registry  
**Backwards Compatibility:** ✅ Full fallback support for non-registry games  
**Testing:** ✅ Django checks pass, no errors  
**Documentation:** ✅ Complete implementation summary provided
