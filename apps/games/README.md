# Game Configuration System

**Phase 2: Configuration-Driven Game Rules Engine**

This document describes the DeltaCrown Game Configuration System - a declarative, database-driven architecture for managing game-specific behavior without hardcoding.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Models](#models)
4. [Services](#services)
5. [Examples](#examples)
6. [Phase Roadmap](#phase-roadmap)

---

## Overview

### Purpose

The Game Configuration System replaces hardcoded game logic with declarative database configuration. This enables:

- **No Code Changes for New Games**: Add games via admin panel/migrations
- **Flexible Validation**: Define identity fields, match schemas, scoring rules per game
- **Testability**: Configuration is data, easily tested
- **Maintainability**: Changes don't require code deployments

### Key Concepts

- **Identity Configuration**: What fields identify a player (Riot ID, Steam ID, etc.)
- **Match Result Schema**: What fields are valid in match results (kills, rounds, placement)
- **Scoring Rules**: How matches are scored (win/loss, points, placement, time)
- **Tournament Config**: Registration requirements (team size, verification, regions)

---

## Architecture

### Configuration Flow

```
Admin creates configuration (models)
        ↓
Service reads configuration (GameService)
        ↓
Engine applies rules (GameRulesEngine, GameValidationService)
        ↓
Result (ValidationResultDTO, scoring dict)
```

### Core Principles

1. **Declarative over Imperative**: Define what, not how
2. **Data over Code**: Configuration in database, not Python modules
3. **Extensible**: New rule types can be added without changing existing code
4. **Lenient Defaults**: If no config exists, accept reasonable defaults

---

## Models

### GamePlayerIdentityConfig

**Location**: `apps/games/models/player_identity.py`

Defines player identity fields required for a game.

**Fields**:
- `game`: ForeignKey to Game
- `field_name`: Internal field name (e.g., `riot_id`)
- `display_label`: User-facing label (e.g., "Riot ID")
- `validation_regex`: Optional regex pattern for validation
- `is_required`: Whether field is mandatory
- `is_immutable`: Whether field can be changed after initial set
- `placeholder`: Example value for forms
- `help_text`: User guidance
- `order`: Display order

**Example** (Valorant):
```python
GamePlayerIdentityConfig.objects.create(
    game=valorant,
    field_name="riot_id",
    display_label="Riot ID",
    validation_regex=r"^[a-zA-Z0-9 ]+#[a-zA-Z0-9]+$",
    is_required=True,
    is_immutable=True,
    placeholder="PlayerName#1234",
    help_text="Your Riot ID (Name#Tag format)",
    order=1,
)
```

---

### GameMatchResultSchema

**Location**: `apps/games/models/rules.py`

Defines valid fields in match results.

**Fields**:
- `game`: ForeignKey to Game
- `field_name`: Internal field name (e.g., `kills`)
- `display_label`: User-facing label (e.g., "Kills")
- `field_type`: Data type (`integer`, `decimal`, `text`, `boolean`, `enum`, `json`)
- `validation`: JSONField with type-specific rules (`min`, `max`, `choices`, `max_length`)
- `is_required`: Whether field is mandatory
- `help_text`: Explanation

**Field Types**:
- **integer**: Whole numbers (kills, rounds)
- **decimal**: Precise decimals (KDA ratio, time)
- **text**: Strings (map name, notes)
- **boolean**: True/False (overtime, win)
- **enum**: Fixed choices (map names, game modes)
- **json**: Complex data (team composition)

**Example** (Valorant Match Schema):
```python
# Rounds won (required)
GameMatchResultSchema.objects.create(
    game=valorant,
    field_name="rounds_won",
    display_label="Rounds Won",
    field_type="integer",
    validation={"min": 0, "max": 25},
    is_required=True,
)

# Kills (optional)
GameMatchResultSchema.objects.create(
    game=valorant,
    field_name="total_kills",
    display_label="Total Kills",
    field_type="integer",
    validation={"min": 0},
    is_required=False,
)

# Map (enum)
GameMatchResultSchema.objects.create(
    game=valorant,
    field_name="map_name",
    display_label="Map",
    field_type="enum",
    validation={"choices": ["Haven", "Bind", "Split", "Ascent", "Icebox", "Breeze"]},
    is_required=True,
)
```

---

### GameScoringRule

**Location**: `apps/games/models/rules.py`

Defines how matches are scored.

**Fields**:
- `game`: ForeignKey to Game
- `rule_type`: Algorithm type (`win_loss`, `points_accumulation`, `placement_order`, `time_based`, `custom`)
- `config`: JSONField with algorithm parameters
- `description`: Human-readable explanation
- `is_active`: Whether rule is currently used
- `priority`: Ordering (highest priority used first)

**Rule Types**:

1. **win_loss**: Binary scoring (1 for win, 0 for loss)
   - Config: `{}` (no params)
   
2. **points_accumulation**: Sum field values with multipliers
   - Config: `{"point_fields": {"kills": 1, "assists": 0.5, "deaths": -0.25}}`
   
3. **placement_order**: Map placement rank to points
   - Config: `{"placement_points": [10, 6, 4, 2, 1]}` (1st place=10, 2nd=6, etc.)
   
4. **time_based**: Score = completion time (speedruns, racing)
   - Config: `{}` (no params)
   
5. **custom**: Reserved for future complex rules
   - Config: varies

**Example** (PUBG Mobile - Battle Royale Placement):
```python
GameScoringRule.objects.create(
    game=pubg_mobile,
    rule_type="placement_order",
    config={
        "placement_points": [10, 6, 5, 4, 3, 3, 2, 2, 1, 1]  # Top 10 placements
    },
    description="PMCO placement scoring system",
    is_active=True,
    priority=10,
)
```

**Example** (Valorant - Round-Based Scoring):
```python
GameScoringRule.objects.create(
    game=valorant,
    rule_type="win_loss",
    config={},
    description="Standard win/loss scoring",
    is_active=True,
    priority=10,
)
```

---

### GameTournamentConfig

**Location**: `apps/games/models/tournament_config.py`

Tournament-level configuration (match formats, registration requirements).

**Phase 2 Fields** (Registration Requirements):
- `min_team_size`: Minimum players (default: 1)
- `max_team_size`: Maximum players (default: 5)
- `allow_cross_region`: Mixed regions allowed (default: False)
- `require_verified_email`: Email verification required (default: True)
- `require_verified_phone`: Phone verification required (default: False)
- `identity_requirements`: JSONField for custom rules (e.g., `{"min_account_level": 30}`)

**Example** (Valorant Tournament):
```python
GameTournamentConfig.objects.create(
    game=valorant,
    min_team_size=5,
    max_team_size=5,
    allow_cross_region=False,
    require_verified_email=True,
    require_verified_phone=False,
    available_match_formats=["BO1", "BO3", "BO5"],
    default_match_format="BO3",
    default_scoring_type="ROUNDS",
)
```

---

## Services

### GameRulesEngine

**Location**: `apps/games/services/rules_engine.py`

Applies scoring rules and validates match results.

#### Methods

**`score_match(game_slug: str, match_payload: dict) -> dict`**

Applies configured scoring rule to match data.

```python
from apps.games.services.rules_engine import GameRulesEngine

engine = GameRulesEngine()

# Win/loss scoring
result = engine.score_match("valorant", {"is_win": True})
# {"total_score": 1, "breakdown": {"is_win": 1}, "rule_type": "win_loss"}

# Points accumulation
result = engine.score_match("valorant", {"kills": 23, "deaths": 15, "assists": 8})
# {"total_score": 27, "breakdown": {"kills": 23, "deaths": -3.75, "assists": 4}, "rule_type": "points_accumulation"}

# Placement order
result = engine.score_match("pubg-mobile", {"placement": 2})
# {"total_score": 6, "breakdown": {"placement": 2}, "rule_type": "placement_order"}
```

**`determine_winner(game_slug: str, match_payload: dict) -> int | None`**

Determines winning team from match data.

```python
# Explicit winner field
winner_id = engine.determine_winner("valorant", {"winner_team_id": 42})
# 42

# Score comparison
winner_id = engine.determine_winner("valorant", {
    "team_a_id": 10,
    "team_a_score": 13,
    "team_b_score": 9
})
# 10

# Draw
winner_id = engine.determine_winner("valorant", {
    "team_a_score": 12,
    "team_b_score": 12
})
# None
```

**`validate_result_schema(game_slug: str, match_payload: dict) -> ValidationResultDTO`**

Validates match result against configured schema.

```python
result = engine.validate_result_schema("valorant", {
    "rounds_won": 13,
    "total_kills": 65,
    "map_name": "Haven"
})
# ValidationResultDTO(is_valid=True, errors=[])

result = engine.validate_result_schema("valorant", {
    "rounds_won": "invalid",  # Wrong type
})
# ValidationResultDTO(is_valid=False, errors=["Field 'rounds_won' must be integer"])
```

---

### GameValidationService

**Location**: `apps/games/services/validation_service.py`

Validates player identities and registration eligibility.

#### Methods

**`validate_identity(game_slug: str, identity_payload: dict) -> ValidationResultDTO`**

Validates identity fields against regex and requirements.

```python
from apps.games.services.validation_service import GameValidationService

validator = GameValidationService()

result = validator.validate_identity("valorant", {
    "riot_id": "PlayerName#1234"
})
# ValidationResultDTO(is_valid=True, errors=[])

result = validator.validate_identity("valorant", {
    "riot_id": "Invalid Riot ID"  # No # symbol
})
# ValidationResultDTO(is_valid=False, errors=["Identity field 'Riot ID' has invalid format..."])
```

**`validate_registration(...) -> EligibilityResultDTO`**

Validates complete registration eligibility.

```python
from apps.common.dtos import UserProfileDTO, TeamDTO

user_dto = UserProfileDTO(
    user_id=1,
    username="player1",
    email="player@example.com",
    email_verified=False  # Not verified
)

team_dto = TeamDTO(
    team_id=1,
    name="My Team",
    member_ids=[1, 2, 3]  # 3 members
)

result = validator.validate_registration("valorant", user_dto, team_dto, {})
# EligibilityResultDTO(is_eligible=False, reason="Email address must be verified; Team size (3) below minimum (5)")
```

**`validate_match_result(game_slug: str, match_payload: dict) -> ValidationResultDTO`**

Delegates to GameRulesEngine for schema validation.

---

### GameService

**Location**: `apps/games/services/game_service.py`

Centralized configuration retrieval.

#### Phase 2 Methods

**`get_player_identity_config(game_slug: str) -> list[GamePlayerIdentityConfig]`**

```python
from apps.games.services.game_service import game_service

configs = game_service.get_player_identity_config("valorant")
for config in configs:
    print(f"{config.field_name}: required={config.is_required}")
```

**`get_scoring_rules(game_slug: str) -> list[GameScoringRule]`**

```python
rules = game_service.get_scoring_rules("pubg-mobile")
# Returns rules ordered by priority (highest first)
```

**`get_match_schema(game_slug: str) -> list[GameMatchResultSchema]`**

```python
schemas = game_service.get_match_schema("valorant")
for schema in schemas:
    print(f"{schema.field_name}: {schema.field_type}, required={schema.is_required}")
```

**`get_tournament_config_by_slug(game_slug: str) -> GameTournamentConfig`**

```python
config = game_service.get_tournament_config_by_slug("valorant")
print(f"Team size: {config.min_team_size}-{config.max_team_size}")
```

---

## Examples

### Complete Valorant Setup

```python
from apps.games.models import (
    Game,
    GamePlayerIdentityConfig,
    GameMatchResultSchema,
    GameScoringRule,
    GameTournamentConfig,
)

# 1. Create Game
valorant = Game.objects.create(
    slug="valorant",
    name="VALORANT",
    display_name="VALORANT",
    is_active=True,
    is_featured=True,
)

# 2. Identity Configuration
GamePlayerIdentityConfig.objects.create(
    game=valorant,
    field_name="riot_id",
    display_label="Riot ID",
    validation_regex=r"^[a-zA-Z0-9 ]+#[a-zA-Z0-9]+$",
    is_required=True,
    is_immutable=True,
    placeholder="PlayerName#1234",
    help_text="Your Riot ID in Name#Tag format",
    order=1,
)

# 3. Match Result Schema
schemas = [
    ("rounds_won", "Rounds Won", "integer", {"min": 0, "max": 25}, True),
    ("total_kills", "Total Kills", "integer", {"min": 0}, False),
    ("total_deaths", "Total Deaths", "integer", {"min": 0}, False),
    ("total_assists", "Total Assists", "integer", {"min": 0}, False),
    ("map_name", "Map", "enum", {"choices": ["Haven", "Bind", "Split", "Ascent"]}, True),
]

for field_name, label, field_type, validation, required in schemas:
    GameMatchResultSchema.objects.create(
        game=valorant,
        field_name=field_name,
        display_label=label,
        field_type=field_type,
        validation=validation,
        is_required=required,
    )

# 4. Scoring Rule
GameScoringRule.objects.create(
    game=valorant,
    rule_type="win_loss",
    config={},
    description="Standard win/loss scoring (best-of series)",
    is_active=True,
    priority=10,
)

# 5. Tournament Configuration
GameTournamentConfig.objects.create(
    game=valorant,
    min_team_size=5,
    max_team_size=5,
    allow_cross_region=False,
    require_verified_email=True,
    require_verified_phone=False,
    available_match_formats=["BO1", "BO3", "BO5"],
    default_match_format="BO3",
    default_scoring_type="ROUNDS",
)
```

### Complete PUBG Mobile Setup (Battle Royale)

```python
# 1. Create Game
pubg = Game.objects.create(
    slug="pubg-mobile",
    name="PUBG Mobile",
    display_name="PUBG MOBILE",
    is_active=True,
)

# 2. Identity Configuration
GamePlayerIdentityConfig.objects.create(
    game=pubg,
    field_name="pubg_id",
    display_label="PUBG ID",
    validation_regex=r"^\d{10,12}$",
    is_required=True,
    placeholder="5123456789",
    help_text="Your 10-12 digit PUBG ID",
    order=1,
)

# 3. Match Result Schema (Battle Royale)
schemas = [
    ("placement", "Placement", "integer", {"min": 1, "max": 20}, True),
    ("team_kills", "Team Kills", "integer", {"min": 0}, True),
    ("survival_time", "Survival Time (seconds)", "decimal", {"min": 0}, False),
]

for field_name, label, field_type, validation, required in schemas:
    GameMatchResultSchema.objects.create(
        game=pubg,
        field_name=field_name,
        display_label=label,
        field_type=field_type,
        validation=validation,
        is_required=required,
    )

# 4. Scoring Rule (Placement-based)
GameScoringRule.objects.create(
    game=pubg,
    rule_type="placement_order",
    config={
        "placement_points": [10, 6, 5, 4, 3, 3, 2, 2, 1, 1]  # PMCO scoring
    },
    description="PMCO placement scoring (top 10 get points)",
    is_active=True,
    priority=10,
)

# Optional: Add kill points
GameScoringRule.objects.create(
    game=pubg,
    rule_type="points_accumulation",
    config={
        "point_fields": {"team_kills": 1}  # 1 point per kill
    },
    description="Kill points (bonus scoring)",
    is_active=True,
    priority=5,  # Lower priority than placement
)

# 5. Tournament Configuration
GameTournamentConfig.objects.create(
    game=pubg,
    min_team_size=4,
    max_team_size=4,
    allow_cross_region=True,  # International tournaments
    require_verified_email=True,
    default_match_format="BR",  # Battle Royale
    default_scoring_type="PLACEMENT",
)
```

### Validating Match Results

```python
from apps.games.services.rules_engine import GameRulesEngine

engine = GameRulesEngine()

# Validate Valorant match
valorant_match = {
    "rounds_won": 13,
    "total_kills": 65,
    "total_deaths": 58,
    "total_assists": 42,
    "map_name": "Haven",
}

result = engine.validate_result_schema("valorant", valorant_match)
if result.is_valid:
    print("Match result valid!")
    score = engine.score_match("valorant", valorant_match)
    print(f"Score: {score['total_score']}")
else:
    print(f"Errors: {result.errors}")

# Validate PUBG match
pubg_match = {
    "placement": 2,
    "team_kills": 12,
    "survival_time": 1850.5,
}

result = engine.validate_result_schema("pubg-mobile", pubg_match)
if result.is_valid:
    score = engine.score_match("pubg-mobile", pubg_match)
    print(f"Placement score: {score['total_score']}")  # 6 points for 2nd place
```

---

## Phase Roadmap

### Phase 2 (Current) ✅

**Epic 2.1-2.3: Foundation**

- ✅ Game configuration models (identity, schema, scoring, tournament)
- ✅ Game Rules Engine (scoring, winner determination, validation)
- ✅ Game Validation Service (identity, registration)
- ✅ Configuration retrieval methods (GameService)
- ✅ Comprehensive test coverage
- ✅ Documentation

**Scope**: Backend models and services only, no UI or TournamentOps integration.

### Phase 3 (Upcoming)

**Epic 2.4-2.6: Integration**

- [ ] Integrate GameRulesEngine with TournamentOps services
- [ ] Bracket generation using configured scoring rules
- [ ] Match result submission with automatic validation
- [ ] Game-specific rules modules (ValorantRules, PUBGRules)
- [ ] Admin panel forms for configuration
- [ ] Seed data for 11 supported games

**Scope**: Connect rules engine to tournament operations, real match flows.

### Phase 4 (Future)

**Epic 3.x: Advanced Features**

- [ ] Complex scoring algorithms (multi-stage tournaments)
- [ ] Custom rule types (team composition bonuses)
- [ ] Region-specific configurations
- [ ] Historical data migration tools

### Phase 5 (Future)

**Epic 5.x: Smart Registration**

- [ ] Automatic eligibility checks using GameValidationService
- [ ] Real-time identity verification
- [ ] Intelligent error messages
- [ ] Registration wizard UI

---

## Migration Guide

### Adding a New Game

1. Create Game instance in admin
2. Add GamePlayerIdentityConfig (identity fields)
3. Add GameMatchResultSchema (result fields)
4. Add GameScoringRule (scoring algorithm)
5. Add GameTournamentConfig (tournament settings)
6. Test with GameRulesEngine and GameValidationService

### Updating Existing Game Configuration

Changes to models take effect immediately (database-driven). No code deployment required.

---

## Testing

Run Phase 2 tests:
```bash
pytest apps/games/tests/test_game_rules.py -v
```

Expected output:
```
apps/games/tests/test_game_rules.py::GameMatchResultSchemaModelTests::... PASSED
apps/games/tests/test_game_rules.py::GameScoringRuleModelTests::... PASSED
apps/games/tests/test_game_rules.py::GameRulesEngineTests::... PASSED
apps/games/tests/test_game_rules.py::GameValidationServiceTests::... PASSED
apps/games/tests/test_game_rules.py::GameServiceTests::... PASSED

===================== 30 passed in 1.58s =====================
```

---

## Phase 2 Completion Summary

### Status: ✅ COMPLETE

**Completion Date**: 2025-01-21  
**Test Results**: All 30 tests passing + 13 adapter integration tests passing

### Achievements

1. **Configuration-Driven Rules Engine**:
   - ✅ `GamePlayerIdentityConfig` model with `is_immutable` field
   - ✅ `GameRulesEngine` service for scoring logic
   - ✅ `GameValidationService` for identity and registration validation
   - ✅ `GameService` facade for unified game config access

2. **Cross-Domain Integration**:
   - ✅ `GameAdapter` wired to use Phase 2 services
   - ✅ No direct model imports in `tournament_ops` domain
   - ✅ DTOs properly map model fields to consumer expectations

3. **Field Naming Contracts** (Final):
   - Model field: `display_name` → DTO field: `display_label`
   - Model field: `validation_regex` → DTO field: `validation_pattern`
   - Model field: `is_immutable` (added in migration `0003`)

### Integration Example

```python
# GameAdapter delegates to Phase 2 services
from apps.tournament_ops.adapters.game_adapter import GameAdapter

adapter = GameAdapter()

# Get identity field config (returns list of dicts mapped from DTOs)
identity_fields = adapter.get_identity_fields(game_slug="valorant")
# [{'field_name': 'riot_id', 'display_label': 'Riot ID', 'is_required': True, ...}]

# Validate identity data
is_valid = adapter.validate_game_identity(
    game_slug="valorant",
    identity_payload={"riot_id": "Player#NA1"}
)
# True

# Get scoring rules
scoring_rules = adapter.get_scoring_rules(game_slug="valorant")
# {'rule_type': 'win_loss', 'config': {...}, 'priority': 1}
```

### Architecture Flow

```
GameAdapter (tournament_ops)
    ↓ imports
GameService (games.services.game_service)
    ↓ delegates to
GameRulesEngine (games.services.rules_engine)
GameValidationService (games.services.validation_service)
    ↓ query
GamePlayerIdentityConfig (games.models)
GameScoringRule (games.models)
    ↓ map to
GamePlayerIdentityConfigDTO (tournament_ops.dtos)
ValidationResult (tournament_ops.dtos.common)
```

### Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Models (GamePlayerIdentityConfig, GameScoringRule) | 10 | ✅ Pass |
| GameRulesEngine (scoring, validation) | 12 | ✅ Pass |
| GameValidationService (identity, registration) | 5 | ✅ Pass |
| GameService (facade methods) | 3 | ✅ Pass |
| **GameAdapter Integration** | **13** | ✅ **Pass** |
| **Total** | **43** | ✅ **100%** |

---

## Support

For questions or issues with the Game Configuration System:
- See `docs/teams/GAME_CONFIGURATION.md` for advanced examples
- Check `SMART_REG_AND_RULES_PART_3.md` for architecture details
- Contact platform engineering team

---

**Last Updated**: 2025-01-21 (Phase 2 Complete)  
**Version**: 2.0.0  
**Status**: ✅ Production Ready
