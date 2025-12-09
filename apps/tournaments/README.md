# Tournaments App - Epic 3.2 & 3.4 Implementation

## Overview

This document provides comprehensive documentation for the group stage system (Epic 3.2) and stage transition system (Epic 3.4) implementations. These features enable multi-stage tournament workflows with game-specific scoring, Swiss format support, and automated bracket generation.

## Group Stage System (Epic 3.2)

### Architecture

The group stage system provides round-robin tournament functionality with game-specific scoring integration.

**Key Components:**
- `GroupStageService`: Core business logic for group management
- `GameRulesEngine`: Game-specific scoring calculations
- `GameService`: Configuration and rule retrieval
- Models: `GroupStage`, `Group`, `GroupStanding`, `Match`

### Core Features

#### 1. Group Creation and Management

```python
from apps.tournaments.services.group_stage_service import GroupStageService

# Create groups for a tournament
stage = GroupStageService.create_groups(
    tournament_id=tournament.id,
    num_groups=4,
    group_size=4,
    advancement_count_per_group=2,
    config={'points_system': {'win': 3, 'draw': 1, 'loss': 0}}
)

# Auto-balance participants across groups
GroupStageService.auto_balance_groups(
    stage_id=stage.id,
    participant_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
    is_team=True
)

# Generate round-robin matches
match_count = GroupStageService.generate_group_matches(stage.id)
```

#### 2. Standings Calculation with GameRulesEngine Integration

The system integrates with `GameRulesEngine` to support game-specific scoring:

```python
# Calculate standings for all groups
standings = GroupStageService.calculate_group_standings(stage.id)
# Returns: {group_id: [{"participant_id": 1, "rank": 1, "points": 9, "wins": 3, ...}, ...]}
```

**Scoring Flow:**
1. Fetch game-specific scoring rules from `GameService`
2. For each completed match, call `GameRulesEngine.score_match()`
3. Apply points system (win/draw/loss)
4. Calculate tiebreakers: points → wins → goal differential → goals for
5. Rank participants and update `GroupStanding` records

**Match Schema:**
```python
Match.objects.create(
    tournament=tournament,
    round_number=1,
    match_number=1,
    participant1_id=team1.id,
    participant2_id=team2.id,
    participant1_score=2,
    participant2_score=1,
    winner_id=team1.id,
    loser_id=team2.id,
    state=Match.COMPLETED,
    lobby_info={"group_id": group.id}
)
```

**Key Fields:**
- `lobby_info`: JSONField storing `group_id`, `stage_id`, and game-specific data
- `participant1_score` / `participant2_score`: Direct score fields (NOT `result_data`)
- `winner_id` / `loser_id`: Participant identifiers for match outcome

#### 3. JSON Export for UI/API

Export standings in JSON format with proper numeric serialization:

```python
json_data = GroupStageService.export_standings(stage.id)
```

**Output Structure:**
```json
{
  "stage_id": 1,
  "num_groups": 4,
  "groups": [
    {
      "group_id": 1,
      "group_name": "Group A",
      "standings": [
        {
          "participant_id": 5,
          "rank": 1,
          "points": 9.0,
          "wins": 3,
          "draws": 0,
          "losses": 0,
          "goals_for": 8,
          "goals_against": 2,
          "goal_diff": 6
        }
      ]
    }
  ]
}
```

**Decimal Handling:** All `Decimal` fields are converted to `float` for JSON compatibility.

### Database Schema

**GroupStage:**
- `tournament`: ForeignKey to Tournament
- `config`: JSONField for points system and tiebreaker rules
- Relationships: `groups` (reverse FK)

**Group:**
- `tournament`: ForeignKey to Tournament
- `name`: CharField (e.g., "Group A")
- `capacity`: PositiveIntegerField
- Relationships: `standings` (reverse FK)

**GroupStanding:**
- `group`: ForeignKey to Group
- `team_id` / `user_id`: Participant identifiers
- `rank`, `points`, `wins`, `draws`, `losses`: Standing metrics
- `goals_for`, `goals_against`, `goal_diff`: Score differentials

**Match:**
- `tournament`: ForeignKey to Tournament
- `round_number`, `match_number`: PositiveIntegerFields
- `participant1_id`, `participant2_id`: PositiveIntegerFields
- `participant1_score`, `participant2_score`: PositiveIntegerFields
- `winner_id`, `loser_id`: PositiveIntegerFields (NULL for draws)
- `state`: CharField (choices: SCHEDULED, LIVE, COMPLETED, etc.)
- `lobby_info`: JSONField (stores `group_id`, `stage_id`)

**Constraints:**
- COMPLETED matches MUST have `winner_id` and `loser_id` (database constraint)
- Draws not supported at COMPLETED state (use different state or declare winner)

## Stage Transition System (Epic 3.4)

### Architecture

The stage transition system manages multi-stage tournament workflows with advancement logic and bracket generation.

**Key Components:**
- `StageTransitionService`: Core transition logic
- `BracketEngineService`: Bracket generation delegation
- DTOs: `TeamDTO`, `TournamentDTO`, `StageDTO`, `MatchDTO`
- Models: `TournamentStage`, `Bracket`

### Core Features

#### 1. Advancement Calculation

```python
from apps.tournaments.services.stage_transition_service import StageTransitionService

# Calculate which participants advance
result = StageTransitionService.calculate_advancement(stage.id)
# Returns: {"advanced": [1, 2, 5, 6], "eliminated": [3, 4, 7, 8]}
```

**Advancement Criteria:**
- `TOP_N_PER_GROUP`: Top N from each group (e.g., top 2 from 4 groups = 8 advancing)
- `TOP_N`: Top N overall across all groups
- `ALL`: Everyone advances (for staging/preparation)

**Ranking Logic:**
1. Get standings from `GroupStageService.calculate_group_standings()`
2. Apply advancement criteria based on `TournamentStage.advancement_criteria`
3. Return lists of advancing and eliminated participant IDs

#### 2. Swiss Format Support

Swiss system tournaments use match-based ranking instead of groups:

```python
# Create Swiss stage
stage = TournamentStage.objects.create(
    tournament=tournament,
    format=TournamentStage.FORMAT_SWISS,
    advancement_criteria=TournamentStage.ADVANCEMENT_TOP_N,
    advancement_count=8
)

# Calculate advancement based on match results
result = StageTransitionService.calculate_advancement(stage.id)
```

**Swiss Ranking:**
- Participants ranked by match wins
- Tiebreakers: win count → score differential
- Matches filtered using `lobby_info__stage_id=stage.id`

####3. Bracket Generation with BracketEngineService Integration

```python
# Generate next stage (calls BracketEngineService internally)
next_stage = StageTransitionService.generate_next_stage(current_stage.id)
```

**Workflow:**
1. Calculate advancement from current stage
2. Create `TournamentStage` record for next stage
3. Convert to DTOs (`TournamentDTO`, `StageDTO`, `TeamDTO`)
4. Delegate to `BracketEngineService.generate_bracket_for_stage()`
5. Update stage states (current → COMPLETED, next → ACTIVE)

**BracketEngineService Contract:**
```python
def generate_bracket_for_stage(
    tournament: TournamentDTO,
    stage: StageDTO,
    teams: List[TeamDTO]
) -> Dict:
    """
    Generate bracket structure for elimination stage.
    
    Args:
        tournament: Tournament DTO with id, name, game
        stage: Stage DTO with format, order, state
        teams: List of advancing team DTOs
    
    Returns:
        {"bracket_id": int, "match_count": int, "rounds": int}
    """
```

**Match Generation:**
- Bracket service creates matches with `lobby_info__stage_id=next_stage.id`
- Matches use single-elimination seeding (1 vs 16, 2 vs 15, etc.)

### Database Schema

**TournamentStage:**
- `tournament`: ForeignKey to Tournament
- `name`: CharField (e.g., "Group Stage", "Quarterfinals")
- `order`: PositiveIntegerField (stage sequence)
- `format`: CharField (choices: ROUND_ROBIN, SINGLE_ELIM, DOUBLE_ELIM, SWISS)
- `advancement_criteria`: CharField (TOP_N_PER_GROUP, TOP_N, ALL)
- `advancement_count`: PositiveIntegerField
- `state`: CharField (choices: PENDING, ACTIVE, COMPLETED, CANCELLED)
- `group_stage`: OneToOneField to GroupStage (NULL for bracket stages)

**Bracket:**
- `tournament`: ForeignKey to Tournament
- `stage`: OneToOneField to TournamentStage
- `format`: CharField (SINGLE_ELIM, DOUBLE_ELIM)
- `participant_count`: PositiveIntegerField
- Relationships: `matches` (reverse FK)

## API/Serialization Layer

### Serializers

**StandingSerializer:**
```python
{
    "participant_id": 5,
    "rank": 1,
    "points": "9.00",
    "wins": 3,
    "draws": 0,
    "losses": 0,
    "goals_for": 8,
    "goals_against": 2,
    "goal_diff": 6
}
```

**GroupSerializer:**
```python
{
    "group_id": 1,
    "group_name": "Group A",
    "standings": [...]  # List of StandingSerializer
}
```

**GroupStageSerializer:**
```python
{
    "stage_id": 1,
    "num_groups": 4,
    "groups": [...]  # List of GroupSerializer
}
```

### Usage Example

```python
from apps.tournaments.serializers import GroupStageSerializer

# Serialize group stage data
stage_data = GroupStageService.export_standings(stage.id)
serializer = GroupStageSerializer(data=stage_data)
serializer.is_valid()
return Response(serializer.data)
```

## Complete Workflow Example

### Group Stage → Playoffs Pipeline

```python
from apps.tournaments.services.group_stage_service import GroupStageService
from apps.tournaments.services.stage_transition_service import StageTransitionService

# 1. Create group stage
group_stage = GroupStageService.create_groups(
    tournament_id=tournament.id,
    num_groups=4,
    group_size=4,
    advancement_count_per_group=2
)

# 2. Assign participants
GroupStageService.auto_balance_groups(
    stage_id=group_stage.id,
    participant_ids=list(range(1, 17)),
    is_team=True
)

# 3. Generate matches
GroupStageService.generate_group_matches(group_stage.id)

# 4. Simulate match results (in production, matches are completed via match management)
for match in Match.objects.filter(tournament=tournament):
    match.participant1_score = 2
    match.participant2_score = 1
    match.winner_id = match.participant1_id
    match.loser_id = match.participant2_id
    match.state = Match.COMPLETED
    match.save()

# 5. Calculate standings
standings = GroupStageService.calculate_group_standings(group_stage.id)

# 6. Export for UI
json_data = GroupStageService.export_standings(group_stage.id)

# 7. Create stage models for transition
stage1 = TournamentStage.objects.create(
    tournament=tournament,
    name="Group Stage",
    order=1,
    format=TournamentStage.FORMAT_ROUND_ROBIN,
    advancement_criteria=TournamentStage.ADVANCEMENT_TOP_N_PER_GROUP,
    state=TournamentStage.STATE_COMPLETED,
    group_stage=group_stage
)

stage2 = TournamentStage.objects.create(
    tournament=tournament,
    name="Quarterfinals",
    order=2,
    format=TournamentStage.FORMAT_SINGLE_ELIM,
    state=TournamentStage.STATE_PENDING
)

# 8. Calculate advancement
advancement = StageTransitionService.calculate_advancement(stage1.id)
# advancement = {"advanced": [1, 2, 5, 6, 9, 10, 13, 14], "eliminated": [...]}

# 9. Generate playoff bracket
next_stage = StageTransitionService.generate_next_stage(stage1.id)

# 10. Verify bracket created
playoff_matches = Match.objects.filter(
    tournament=tournament,
    lobby_info__stage_id=stage2.id
)
# Should have 4 quarterfinal matches
```

## Testing

### Test Files

- `apps/tournaments/tests/test_group_stage_service.py`: Group stage tests
- `apps/tournaments/tests/test_stage_transition_service.py`: Transition tests
- `apps/tournaments/tests/test_e2e_group_to_playoffs.py`: End-to-end pipeline tests
- `apps/tournaments/tests/test_group_stage_serializers.py`: Serializer tests

### Test Requirements

**Match Fixtures:**
- Must create real `Team` objects (cannot use fake IDs)
- Must include `round_number` and `match_number` (NOT NULL)
- Must use `lobby_info` JSONField (NOT `config`)
- Must use `participant1_score` / `participant2_score` (NOT `result_data`)
- COMPLETED matches must have `winner_id` and `loser_id`

**Example:**
```python
from apps.teams.models import Team

team1 = Team.objects.create(name="Team A", tag="TA", game="test-game")
team2 = Team.objects.create(name="Team B", tag="TB", game="test-game")

Match.objects.create(
    tournament=tournament,
    round_number=1,
    match_number=1,
    participant1_id=team1.id,
    participant2_id=team2.id,
    participant1_score=2,
    participant2_score=1,
    winner_id=team1.id,
    loser_id=team2.id,
    state=Match.COMPLETED,
    lobby_info={"group_id": group.id}
)
```

## Architecture Boundaries

### Layer Separation

**tournaments → games:**
- ✅ ALLOWED: Import from `apps.games.services`
- ✅ ALLOWED: Use `GameRulesEngine`, `GameService`
- ❌ FORBIDDEN: Import from `apps.games.models` directly

**tournaments → tournament_ops:**
- ✅ ALLOWED: Import `BracketEngineService`
- ✅ ALLOWED: Use DTO classes for data transfer
- ❌ FORBIDDEN: Import models or utilities

**tournaments → teams:**
- ✅ ALLOWED: Import `Team` model for test fixtures
- ⚠️ CAUTION: Minimize coupling, use IDs where possible

### DTO Usage

DTOs decouple `tournaments` from `tournament_ops` implementation details:

```python
from apps.tournament_ops.services.dto import TeamDTO, TournamentDTO, StageDTO

# Convert database models to DTOs
team_dto = TeamDTO(id=team.id, name=team.name, tag=team.tag, game=team.game)
tournament_dto = TournamentDTO(id=tournament.id, name=tournament.name, game=tournament.game.slug)
stage_dto = StageDTO(id=stage.id, format=stage.format, order=stage.order, state=stage.state)

# Pass to BracketEngineService
bracket_result = BracketEngineService.generate_bracket_for_stage(
    tournament=tournament_dto,
    stage=stage_dto,
    teams=[team_dto1, team_dto2, ...]
)
```

## Configuration

### GameTournamentConfig

Game-specific configurations are stored in `GameTournamentConfig.config`:

```python
{
    "points_system": {
        "win": 3,
        "draw": 1,
        "loss": 0
    },
    "tiebreaker_rules": [
        "points",
        "wins",
        "head_to_head",  # TODO: Epic 3.5
        "goal_difference",
        "goals_for"
    ],
    "min_participants": 8,
    "max_participants": 64,
    "formats": ["round_robin", "single_elimination", "swiss"]
}
```

### Points System Fallback

If `GameService` cannot retrieve scoring rules:
1. Try `GameTournamentConfig.config['points_system']`
2. Fall back to `GroupStage.config.get('points_system')`
3. Default: `{'win': 3, 'draw': 1, 'loss': 0}`

## Known Issues and Limitations

### Current Status

**Completed:**
- ✅ GroupStageService implementation
- ✅ StageTransitionService implementation
- ✅ GameRulesEngine integration
- ✅ BracketEngineService integration
- ✅ Swiss format support
- ✅ JSON export with Decimal handling
- ✅ UI/API serializers
- ✅ Match schema updates (lobby_info, score fields)

**Partially Complete:**
- ⚠️ Test fixtures (some tests still use fake participant IDs)
- ⚠️ Test constants (TournamentStage.ADVANCEMENT_* constants missing)
- ⚠️ Draw support (database constraint prevents COMPLETED draws)

**Not Implemented:**
- ❌ Head-to-head tiebreaker logic (Epic 3.5)
- ❌ Multi-round Swiss progression
- ❌ Double elimination bracket generation

### Test Failures

Some tests require additional fixes:
1. Tests using `participant_ids=[1, 2, 3]` need real Team objects
2. Tests using `Match.PENDING` should use `Match.SCHEDULED`
3. Tests using `TournamentStage.ADVANCEMENT_TOP_N` need model constants added
4. E2E tests need complete 16-team fixtures with proper Team creation

### Database Constraints

**Match Model:**
- COMPLETED state requires non-NULL `winner_id` and `loser_id`
- Draws not supported with COMPLETED state (use `PENDING_RESULT` or declare winner)
- `round_number` and `match_number` are NOT NULL

## Future Enhancements

1. **Head-to-Head Tiebreaker (Epic 3.5):** Calculate h2h records for tied participants
2. **Swiss Pairing Algorithm:** Intelligent opponent matching based on standings
3. **Draw Support:** Add `DRAW` state or relax COMPLETED constraint
4. **Bracket Visualization:** Generate bracket trees for UI rendering
5. **Live Updates:** WebSocket integration for real-time standings
6. **Multi-Game Support:** Per-game tiebreaker configuration
7. **Seeding System:** Advanced seeding algorithms for bracket generation

## References

- Epic 3.2: Group Stage System
- Epic 3.4: Stage Transition and Bracket Integration
- GameRulesEngine: `apps/games/services/rules_engine.py`
- BracketEngineService: `apps/tournament_ops/services/bracket_engine_service.py`
- Match Model: `apps/tournaments/models/match.py`
- GroupStage Model: `apps/tournaments/models/group.py`
- TournamentStage Model: `apps/tournaments/models/stage.py`
