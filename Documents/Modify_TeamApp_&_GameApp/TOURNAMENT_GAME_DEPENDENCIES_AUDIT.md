# Tournament App Game Dependencies Audit Report
**Date:** December 4, 2025  
**Focus:** Game-Related Code in Tournament App  
**Goal:** Identify dependencies for centralized Game app migration

---

## 📊 EXECUTIVE SUMMARY

The Tournament app currently has **HEAVY dependencies** on game-specific data scattered across multiple locations:

| Dependency Type | Locations Found | Severity | Migration Priority |
|----------------|-----------------|----------|-------------------|
| **Game Model** | `apps/tournaments/models/tournament.py` | 🟢 GOOD | ✅ Already database-backed |
| **Hardcoded Game Logic** | 15+ files | 🔴 CRITICAL | 1 - URGENT |
| **Game Registry Imports** | 12 files | 🟡 MEDIUM | 2 - HIGH |
| **Game Validators** | `apps/tournaments/games/validators.py` | 🟡 MEDIUM | 3 - MEDIUM |
| **Game Config Service** | `apps/tournaments/services/game_config_service.py` | 🟢 GOOD | ✅ Service layer ready |

**Key Finding:** Tournament app is in BETTER shape than Teams app regarding game management:
- ✅ Has database-backed `Game` model
- ✅ Has `game_config` JSONB field for flexibility
- ✅ Has `GameConfigService` for centralized logic
- ❌ BUT still has hardcoded game slugs in 15+ files
- ❌ Imports from deprecated `apps.common.game_registry`

---

## 1️⃣ GAME MODEL ANALYSIS

### Current Implementation (GOOD Foundation)

**Location:** `apps/tournaments/models/tournament.py` (Lines 35-146)

```python
class Game(models.Model):
    """
    Game definitions for supported tournament games.
    """
    # Basic Fields
    name = CharField(max_length=100, unique=True)
    slug = SlugField(max_length=120, unique=True, db_index=True)
    icon = ImageField(upload_to='games/icons/')
    
    # Team Structure
    default_team_size = PositiveIntegerField(
        choices=TEAM_SIZE_CHOICES,
        default=TEAM_SIZE_5V5
    )
    min_team_size = PositiveIntegerField(default=1)
    max_team_size = PositiveIntegerField(default=5)
    
    # Player Identity
    profile_id_field = CharField(
        max_length=50,
        help_text="Field name in UserProfile (e.g., 'riot_id', 'steam_id')"
    )
    
    # Result Type
    default_result_type = CharField(
        max_length=20,
        choices=RESULT_TYPE_CHOICES,
        default=MAP_SCORE
    )
    
    # JSONB Configuration
    game_config = JSONField(default=dict, blank=True)
    roster_rules = JSONField(default=dict, blank=True)
    roles = JSONField(default=list, blank=True)
    result_logic = JSONField(default=dict, blank=True)
    
    # Media
    banner = ImageField(upload_to='games/banners/', blank=True, null=True)
    card_image = ImageField(upload_to='games/cards/', blank=True, null=True)
    logo = ImageField(upload_to='games/logos/', blank=True, null=True)
    
    # Branding
    primary_color = CharField(max_length=20, blank=True, null=True)
    secondary_color = CharField(max_length=20, blank=True, null=True)
    
    # Metadata
    category = CharField(max_length=50, blank=True, null=True)
    platform = CharField(max_length=50, blank=True, null=True)
    
    # Status
    is_active = BooleanField(default=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
```

**✅ STRENGTHS:**
1. Database-backed (admin-editable)
2. JSONB fields for flexibility (game_config, roster_rules, roles, result_logic)
3. Comprehensive media fields (icon, banner, logo, card)
4. Branding support (colors)
5. Proper indexing (slug, is_active)

**❌ WEAKNESSES:**
1. Missing `display_name` field (only has `name`)
2. Missing `short_code` field (e.g., 'VAL', 'CS2')
3. No `regions` field
4. No `tournament_config` JSONB (tournament-specific settings separate from game_config)
5. No version tracking for spec changes
6. Roles stored as simple JSON list (no GameRole model)

**🔄 COMPARISON WITH TEAMS APP:**

| Feature | Tournament Game Model | Teams game_config.py | Recommended |
|---------|----------------------|---------------------|-------------|
| Database-backed | ✅ YES | ❌ Hardcoded | ✅ Database |
| Admin-editable | ✅ YES | ❌ Code only | ✅ Admin |
| Roles | ✅ JSON field | ✅ Hardcoded list | 🔄 GameRole model |
| Regions | ❌ Missing | ✅ Hardcoded tuples | ✅ Add field |
| Roster rules | ✅ JSON field | ✅ Hardcoded config | ✅ JSON + validation |
| Result logic | ✅ JSON field | ❌ Not defined | ✅ Keep JSON |

**Verdict:** Tournament's Game model is a GOOD foundation, needs minor enhancements.

---

## 2️⃣ HARDCODED GAME LOGIC (CRITICAL ISSUE)

### Locations of Hardcoded Game Slugs

**15+ files with hardcoded game-specific logic:**

#### **A. Bracket Service** (`apps/tournaments/services/bracket_service.py`)

**Lines 263-300:** Group stage advancement sorting

```python
# HARDCODED GAME SLUGS
if game_slug in ['efootball', 'fc-mobile', 'fifa']:
    advancer["goal_difference"] = standing.goal_difference
    advancer["goals_for"] = standing.goals_for
elif game_slug in ['valorant', 'cs2']:
    advancer["round_difference"] = standing.round_difference
    advancer["rounds_won"] = standing.rounds_won
elif game_slug in ['pubg-mobile', 'free-fire']:
    advancer["placement_points"] = float(standing.placement_points or 0)
    advancer["total_kills"] = standing.total_kills
elif game_slug == 'mobile-legends':
    advancer["kda_ratio"] = float(standing.kda_ratio or 0)
    advancer["total_kills"] = standing.total_kills
elif game_slug == 'call-of-duty-mobile':
    advancer["total_score"] = standing.total_score
    advancer["total_kills"] = standing.total_kills
```

**Lines 288-300:** Sorting advancers

```python
if game_slug in ['efootball', 'fc-mobile', 'fifa']:
    advancers.sort(key=lambda x: (
        x["group_position"],
        -x["points"],
        -x.get("goal_difference", 0),
        -x.get("goals_for", 0)
    ))
elif game_slug in ['valorant', 'cs2']:
    advancers.sort(key=lambda x: (
        x["group_position"],
        -x["points"],
        -x.get("round_difference", 0),
        -x.get("rounds_won", 0)
    ))
# ... etc for each game
```

**Problem:** 
- Every new game requires code changes
- Sorting logic duplicated
- Difficult to test
- Cannot be configured by admin

**Solution:**
```python
# Store in Game.result_logic JSONB
{
  "group_stage": {
    "tiebreaker_fields": [
      {"field": "goal_difference", "order": "desc"},
      {"field": "goals_for", "order": "desc"}
    ]
  }
}
```

#### **B. Group Stage Views** (`apps/tournaments/views/group_stage.py`)

**Lines 294-300:** Result stat fields

```python
if game_slug in ['efootball', 'fc26']:
    stat_fields = ['goal_difference', 'goals_for', 'goals_against']
elif game_slug in ['valorant', 'cs2']:
    stat_fields = ['round_difference', 'rounds_won', 'rounds_lost']
elif game_slug in ['pubg', 'freefire']:
    stat_fields = ['placement_points', 'total_kills', 'total_damage']
```

**Problem:** Same as above - hardcoded game logic

#### **C. Registration Wizard** (`apps/tournaments/views/registration_wizard.py`)

**Lines 465-478:** Auto-fill game IDs

```python
if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id or ''
elif game_slug == 'pubg-mobile':
    auto_filled['game_id'] = profile.pubg_mobile_id or ''
elif game_slug == 'mobile-legends':
    auto_filled['game_id'] = profile.mlbb_id or ''
elif game_slug == 'dota-2' or game_slug == 'cs2':
    auto_filled['game_id'] = profile.steam_id or ''
elif game_slug == 'efootball' or game_slug == 'ea-fc':
    auto_filled['game_id'] = profile.efootball_id or profile.ea_id or ''
```

**Problem:**
- Hardcoded mapping of game slugs to profile fields
- Should use `Game.profile_id_field` from database!

**Solution:**
```python
# Already have profile_id_field in Game model!
game = Game.objects.get(slug=game_slug)
profile_field = game.profile_id_field
auto_filled['game_id'] = getattr(profile, profile_field, '') or ''
```

#### **D. Match Views API** (`apps/tournaments/api/match_views.py`)

**Lines 546-569:** Example room details per game

```python
# HARDCODED EXAMPLES
if game_slug == 'valorant':
    example = {
        "server": "South Asia",
        "room_id": "VAL-SA-12345",
        "map": "Haven"
    }
elif game_slug == 'efootball':
    example = {
        "platform": "PlayStation",
        "room_id": "EFB-123456"
    }
elif game_slug == 'pubg-mobile':
    example = {
        "room_id": "123456",
        "room_password": "pubg123",
        "map": "Erangel"
    }
```

**Problem:** Examples should be in Game.game_config or admin-editable

#### **E. API Registrations** (`apps/tournaments/api/registrations.py`)

**Lines 16-17, 103, 186:** Hardcoded registration functions

```python
# Separate functions for each game!
from apps.tournaments.services.registration_service import (
    register_efootball_player,
    register_valorant_team,
)

# Then used like:
registration = register_efootball_player(input_data)
registration = register_valorant_team(input_data)
```

**Problem:** Should be ONE generic registration function

---

### Summary of Hardcoded Locations

| File | Lines | Issue | Fix Complexity |
|------|-------|-------|---------------|
| `bracket_service.py` | 263-300 | Game-specific sorting logic | MEDIUM - Move to JSONB |
| `group_stage.py` | 294-300 | Stat field selection | EASY - Use JSONB |
| `registration_wizard.py` | 465-478 | Profile field mapping | EASY - Use Game.profile_id_field |
| `match_views.py` | 546-569 | Example room details | EASY - Admin-editable examples |
| `registrations.py` | 16-186 | Separate registration functions | MEDIUM - Unify functions |
| `validators.py` | Full file | Game-specific ID validators | KEEP - Good design |

---

## 3️⃣ GAME REGISTRY IMPORTS

### Files Importing from `apps.common.game_registry`

**12 files found:**

1. `apps/tournaments/services/registration_service.py:325`
2. `apps/tournaments/views/group_stage.py:273`
3. `apps/tournaments/views/group_stage.py:291`
4. `apps/tournaments/views/main.py:27`
5. `apps/tournaments/views/main.py:167`
6. `apps/tournaments/views/registration.py:255`
7. `apps/tournaments/views/registration.py:384`
8. `apps/tournaments/views/spectator.py:78`
9. `apps/tournaments/services/analytics_service.py:468`
10. `apps/tournaments/services/leaderboard.py:107`
11. `apps/tournaments/services/tournament_service.py:361`
12. `apps/tournaments/forms/tournament_create.py:9`
13. `apps/tournaments/admin.py:34`

**Common Imports:**
```python
from apps.common.game_registry import get_game, normalize_slug, get_all_games
```

**Problem:**
- Importing from deprecated `game_registry` module
- Should import from centralized Game app API

**Solution:**
```python
# After Game app created
from apps.games.services import GameService

# Replace:
game_spec = get_game(slug)
# With:
game_spec = GameService.get_game_spec(slug)
```

---

## 4️⃣ GAME VALIDATORS (GOOD DESIGN)

### `apps/tournaments/games/validators.py`

**Purpose:** Validate game-specific player ID formats

**Validators Implemented:**
1. `validate_riot_id()` - Valorant (username#TAG)
2. `validate_steam_id()` - CS2, Dota 2 (17-digit)
3. `validate_mlbb_uid_zone()` - Mobile Legends (UID|Zone)
4. `validate_ea_id()` - EA FC (alphanumeric)
5. `validate_konami_id()` - eFootball (numeric)
6. `validate_mobile_ign()` - PUBG, COD, Free Fire

**✅ VERDICT: KEEP AS IS**

**Rationale:**
- Well-designed, testable functions
- Each validator returns `(is_valid: bool, error_message: str | None)`
- Can be referenced in Game.game_config:

```python
# Game.game_config JSONB
{
  "player_id_validator": "validate_riot_id",
  "player_id_pattern": "^[a-zA-Z0-9 ]+#[A-Z0-9]{3,5}$"
}
```

**Recommendation:** Move to `apps.games.validators` module

---

## 5️⃣ GAME CONFIG SERVICE (EXCELLENT)

### `apps/tournaments/services/game_config_service.py`

**Purpose:** Manage game-specific configurations stored in Game.game_config JSONB

**✅ STRENGTHS:**

1. **Service Layer Pattern** - Business logic separated from models
2. **JSONB Schema Validation** - Validates config structure
3. **Deep Merge** - Updates configs without overwriting entire structure
4. **Audit Trail** - Tracks who changed what
5. **Default Schema** - Provides sensible defaults

**Example Schema:**
```python
DEFAULT_SCHEMA = {
    "schema_version": "1.0",
    "allowed_formats": [
        "single_elimination",
        "double_elimination",
        "round_robin",
        "swiss",
        "group_playoff"
    ],
    "team_size_range": [1, 5],
    "custom_field_schemas": [],
    "match_settings": {
        "default_best_of": 1,
        "available_maps": []
    }
}
```

**Public Methods:**
- `GameConfigService.get_config(game_id)` - Retrieve config
- `GameConfigService.create_or_update_config(game_id, config_data, user)` - Update config
- `GameConfigService._validate_config(config)` - Validate structure

**✅ VERDICT: MIGRATE TO GAME APP**

**Action:**
- Move to `apps/games/services/game_config_service.py`
- Keep all logic intact
- Update imports across codebase

---

## 6️⃣ TOURNAMENT-GAME INTEGRATION POINTS

### How Tournaments Use Game Data

**A. Tournament Model**
```python
# apps/tournaments/models/tournament.py
class Tournament(models.Model):
    game = ForeignKey(Game, on_delete=PROTECT)  # ✅ Database relation
    # ... tournament fields
```

**B. Registration Model**
```python
class Registration(models.Model):
    tournament = ForeignKey(Tournament)
    # Inherits game via tournament.game
```

**C. Match Model**
```python
class Match(models.Model):
    tournament = ForeignKey(Tournament)
    # Inherits game via tournament.game
```

**D. Bracket Service**
```python
# Uses game for sorting logic (currently hardcoded)
tournament = Tournament.objects.select_related('game').get(id=tournament_id)
game_slug = tournament.game.slug

# Should use:
game_config = tournament.game.result_logic
tiebreaker_fields = game_config['group_stage']['tiebreaker_fields']
```

**E. Registration Wizard**
```python
# Uses game for profile field mapping
game = tournament.game
profile_field = game.profile_id_field  # ✅ Already exists!
```

---

## 7️⃣ MIGRATION IMPACT ASSESSMENT

### What Works WITHOUT Changes

✅ **Database Relations:**
- `Tournament.game` FK already exists
- No changes needed to models

✅ **GameConfigService:**
- Already uses service layer pattern
- Just needs to move to Game app

✅ **Game Validators:**
- Self-contained validation functions
- Move to `apps.games.validators`

### What Needs Changes

🔄 **Hardcoded Game Logic:**
- 15+ files with `if game_slug == 'valorant'` patterns
- **Solution:** Move to JSONB configs
- **Complexity:** MEDIUM
- **Timeline:** 2-3 weeks

🔄 **game_registry Imports:**
- 12 files importing from `apps.common.game_registry`
- **Solution:** Update imports to `apps.games.services`
- **Complexity:** EASY
- **Timeline:** 1 week

🔄 **Registration Functions:**
- Separate functions per game (register_efootball_player, register_valorant_team)
- **Solution:** Single generic function with game-specific config
- **Complexity:** MEDIUM
- **Timeline:** 1-2 weeks

### What Needs Addition

➕ **Missing Game Model Fields:**
- `display_name` (e.g., "VALORANT" vs "Valorant")
- `short_code` (e.g., "VAL", "CS2")
- `regions` JSONB
- `tournament_config` JSONB (separate from game_config)

➕ **GameRole Model:**
- Currently roles are just JSON list
- Should be proper model with descriptions, icons, constraints

➕ **GameVersion Model:**
- Track changes to game specs over time
- Audit trail for configuration changes

---

## 8️⃣ DEPENDENCIES ON OTHER APPS

### Tournament App Dependencies

**Depends On:**
1. ✅ `apps.common.models.Game` - Already using it
2. ❌ `apps.common.game_registry` - DEPRECATED, needs migration
3. ✅ `apps.user_profile.UserProfile` - For player IDs (riot_id, steam_id, etc.)
4. ✅ `apps.teams.Team` - For team tournaments

**Does NOT Depend On:**
- ❌ `apps.teams.game_config` - Separate configs (good!)
- ❌ `apps.common.game_assets` - Not used in tournaments

### Reverse Dependencies (Who Depends on Tournament)

**Apps Using Tournament Models:**
1. `apps.teams` - TeamAnalytics tracks tournament participation
2. `apps.leaderboards` - Tournament results for rankings
3. `apps.economy` - Tournament entry fees
4. `apps.notifications` - Tournament reminders

**Impact:** Low - Tournament migrations won't break other apps

---

## 9️⃣ COMPARISON: TOURNAMENT vs TEAMS GAME MANAGEMENT

| Aspect | Tournament App | Teams App | Winner |
|--------|---------------|-----------|---------|
| **Database Model** | ✅ Has Game model | ❌ Uses hardcoded config | 🏆 Tournament |
| **Admin Editable** | ✅ Yes (Game admin) | ❌ Code only | 🏆 Tournament |
| **JSONB Flexibility** | ✅ game_config field | ❌ None | 🏆 Tournament |
| **Service Layer** | ✅ GameConfigService | ❌ None | 🏆 Tournament |
| **Hardcoded Logic** | 🔴 15+ files | 🔴 30+ files | 🤝 Both bad |
| **game_registry Import** | 🟡 12 files | 🟡 8 files | 🤝 Both bad |
| **Validators** | ✅ Dedicated module | ❌ Scattered | 🏆 Tournament |
| **Roles** | 🟡 JSON list | 🟡 Hardcoded | 🤝 Both okay |

**Verdict:** Tournament app is **AHEAD** of Teams app in game management architecture.

---

## 🔟 RECOMMENDATIONS

### Priority 1: Create Centralized Game App (URGENT)

**Action Items:**
1. Create `apps/games/` module
2. **MIGRATE** Tournament's Game model to `apps.games.models.Game`
   - Keep ALL existing fields
   - Add missing fields (display_name, short_code, regions)
3. **MIGRATE** GameConfigService to `apps.games.services.GameConfigService`
4. Create GameRole model
5. Create GameVersion model (audit trail)
6. Create REST API for game data

**Timeline:** 2 weeks

**Benefits:**
- Single source of truth for game data
- Teams + Tournaments both use same Game model
- Admin-editable configurations
- No code changes for new games

### Priority 2: Eliminate Hardcoded Game Logic (HIGH)

**Action Items:**
1. **Bracket Service:** Move sorting logic to Game.result_logic JSONB
2. **Group Stage:** Use JSONB for stat fields
3. **Registration:** Use Game.profile_id_field (already exists!)
4. **Match Views:** Move examples to admin-editable
5. **Unify registration functions** into single generic function

**Timeline:** 3 weeks

**Benefits:**
- Add new games without code changes
- Admin can configure game-specific rules
- Easier to test
- Reduced code duplication

### Priority 3: Update game_registry Imports (MEDIUM)

**Action Items:**
1. Create `apps.games.services.GameService` as replacement
2. Update 12 files to import from new location
3. Deprecate `apps.common.game_registry` module
4. Add deprecation warnings

**Timeline:** 1 week

**Benefits:**
- Clean import structure
- No deprecated module dependencies
- Future-proof architecture

### Priority 4: Enhance Game Model (NICE TO HAVE)

**Action Items:**
1. Add `display_name` field
2. Add `short_code` field
3. Add `regions` JSONB field
4. Add `tournament_config` JSONB field (separate from game_config)
5. Create GameRole model with proper constraints
6. Create GameVersion model for audit trail

**Timeline:** 2 weeks

**Benefits:**
- Complete game metadata
- Proper role management
- Configuration change tracking
- Better admin UX

---

## 📋 MIGRATION CHECKLIST

### Phase 1: Foundation (Week 1-2)
- [ ] Create `apps/games/` directory structure
- [ ] Migrate Game model from `apps/tournaments` to `apps/games`
- [ ] Create migrations (careful with FK updates!)
- [ ] Migrate GameConfigService
- [ ] Create GameRole model
- [ ] Create GameVersion model
- [ ] Create Django admin interfaces
- [ ] Seed database with existing games

### Phase 2: Service Layer (Week 3)
- [ ] Create `apps/games/services/GameService`
- [ ] Create REST API endpoints
- [ ] Add caching layer (Redis)
- [ ] Write API documentation
- [ ] Add comprehensive tests

### Phase 3: Tournament App Updates (Week 4-5)
- [ ] Update imports: `apps.common.game_registry` → `apps.games.services`
- [ ] Replace hardcoded game logic with JSONB configs
- [ ] Unify registration functions
- [ ] Update validators to reference Game configs
- [ ] Test all tournament flows

### Phase 4: Teams App Updates (Week 6-7)
- [ ] Update imports to use `apps.games.services`
- [ ] Replace `game_config.py` with Game API calls
- [ ] Update roster validation to use Game configs
- [ ] Update role management to use GameRole model
- [ ] Test all team flows

### Phase 5: Deprecation (Week 8-9)
- [ ] Mark `apps.common.game_registry` as deprecated
- [ ] Mark `apps.common.game_assets` as deprecated
- [ ] Remove deprecated imports
- [ ] Update all documentation
- [ ] Final cleanup

### Phase 6: Verification (Week 10)
- [ ] Run full test suite
- [ ] Manual testing of all game flows
- [ ] Load testing
- [ ] Security audit
- [ ] Documentation review
- [ ] Deploy to staging
- [ ] Production deployment

---

## 🎯 SUCCESS METRICS

**Game App Migration Success Criteria:**

✅ **Zero hardcoded game configs in code**
- All game logic configurable via admin
- No `if game_slug ==` patterns in code

✅ **Single source of truth**
- One Game model used by Teams + Tournaments
- All apps import from `apps.games.services`

✅ **Admin can add new games**
- No code changes required
- Game config via Django admin
- Immediate availability

✅ **Performance maintained**
- < 100ms API response time (cached)
- No database N+1 queries
- Proper indexing

✅ **Backward compatibility**
- All existing games work unchanged
- All existing tournaments unaffected
- Zero downtime migration

---

**Report Completed:** December 4, 2025  
**Next Steps:** Review recommendations, proceed to Teams missing features analysis
