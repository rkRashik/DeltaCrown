# Universal Bracket Engine

**Phase 3, Epic 3.1**: Pluggable Bracket Generators

## Overview

The Universal Bracket Engine provides a DTO-based, framework-light architecture for generating tournament brackets. It supports multiple tournament formats through a pluggable generator system, enabling safe rollout via feature flags and future extensibility.

**Key Design Principles**:
- **DTO-Only**: All generators work exclusively with DTOs (no ORM usage)
- **Framework-Light**: Pure Python functions, minimal Django dependencies
- **Protocol-Based**: Consistent interface via `BracketGenerator` protocol
- **Extensible**: Registry pattern allows adding new formats without modifying core code
- **Testable**: Isolated from database, easy to unit test

## Architecture

```
tournament_ops/services/bracket_generators/
├── base.py                    # BracketGenerator protocol + helpers
├── single_elimination.py      # Single elimination generator
├── double_elimination.py      # Double elimination generator
├── round_robin.py             # Round-robin generator
├── swiss.py                   # Swiss system generator
└── __init__.py                # Module exports

tournament_ops/services/
└── bracket_engine_service.py  # Orchestrator with format registry
```

**Integration Point**: `tournaments.services.BracketService.generate_bracket_universal_safe()` provides feature-flagged entry point.

## Supported Formats

### 1. Single Elimination

**Generator**: `SingleEliminationGenerator`

**Format Key**: `"single-elimination"` or `"single_elim"`

**Features**:
- Standard knockout bracket (winner advances, loser eliminated)
- Handles 2-256 participants
- Automatic bye placement for non-power-of-two counts (byes go to top seeds)
- Optional third-place match between losing semifinalists
- Standard seeding: 1 vs lowest, 2 vs 2nd-lowest, etc.

**Configuration**:
```python
stage = StageDTO(
    id=1,
    tournament_id=123,
    type="single-elimination",
    third_place_match=True,  # Optional
)
```

**Match Structure**:
- `round_number`: 1, 2, 3, ... (1 = first round, final round = log2(n))
- `match_number`: Sequential within round (1, 2, 3, ...)
- `stage_type`: `"main"` for all matches (or `"third_place"` for 3rd-place match)

**Examples**:
- 4 teams → 2 rounds (semifinals + finals) = 3 matches
- 6 teams → 8 slots with 2 byes → 5 matches
- 8 teams → 3 rounds = 7 matches

### 2. Double Elimination

**Generator**: `DoubleEliminationGenerator`

**Format Key**: `"double-elimination"` or `"double_elim"`

**Features**:
- Winners bracket (standard single-elimination structure)
- Losers bracket (teams from WB drop in, second chance)
- Grand finals (WB champion vs LB champion)
- Optional grand finals reset (if LB champion wins, play second match)
- Handles 4-128 participants

**Configuration**:
```python
stage = StageDTO(
    id=1,
    tournament_id=123,
    type="double-elimination",
    metadata={"grand_finals_reset": True},  # Optional
)
```

**Match Structure**:
- `stage_type`: `"winners"`, `"losers"`, `"grand_finals"`, or `"grand_finals_reset"`
- Winners bracket: Standard SE structure (rounds 1, 2, 3, ...)
- Losers bracket: 2*(WB_rounds - 1) rounds with interleaving
- Grand finals: Round number = max(WB rounds) + max(LB rounds) + 1

**Examples**:
- 4 teams → 6 matches (WB: 3, LB: 2, GF: 1)
- 8 teams → 14 matches (WB: 7, LB: 6, GF: 1)
- With reset: +1 match for grand finals reset

### 3. Round Robin

**Generator**: `RoundRobinGenerator`

**Format Key**: `"round-robin"` or `"round_robin"`

**Features**:
- Every team plays every other team exactly once
- Circle method algorithm for optimal scheduling
- Balanced rounds (each team plays once per round when possible)
- Supports 3-20 participants
- Total matches = N*(N-1)/2

**Configuration**:
```python
stage = StageDTO(
    id=1,
    tournament_id=123,
    type="round-robin",
)
```

**Match Structure**:
- `round_number`: 1 to N-1 (or N for odd counts)
- `match_number`: Sequential within round
- `stage_type`: `"main"`

**Examples**:
- 4 teams → 3 rounds, 6 matches
- 5 teams → 5 rounds, 10 matches
- 6 teams → 5 rounds, 15 matches

**Guarantees**:
- No self-matches (team never plays itself)
- All pairings unique (no duplicates)
- Balanced scheduling (minimizes idle teams per round)

### 4. Swiss System

**Generator**: `SwissSystemGenerator`

**Format Key**: `"swiss"`

**Features**:
- Fixed number of rounds (specified in `stage.metadata.rounds_count`)
- First round: Top half vs bottom half seeding (1v(N/2+1), 2v(N/2+2), etc.)
- Subsequent rounds: **STUB** (TODO: Epic 3.5 - standings-based pairing)
- Supports 4-64 participants
- No elimination (all teams play all rounds)

**Configuration**:
```python
stage = StageDTO(
    id=1,
    tournament_id=123,
    type="swiss",
    metadata={"rounds_count": 5},  # REQUIRED
)
```

**Match Structure**:
- `round_number`: 1 to `rounds_count`
- `match_number`: Sequential within round
- `stage_type`: `"main"`

**Current Limitations**:
- **First round only**: Full implementation of seeded pairing
- **Rounds 2+**: Stub returning simple/placeholder pairings
- **Future (Epic 3.5)**: Standings-based pairing with record grouping, tiebreakers, repeat avoidance

**Examples**:
- 8 teams, 5 rounds → First round: 1v5, 2v6, 3v7, 4v8
- Subsequent rounds: Simple pairings (to be replaced with standings-based)

## BracketGenerator Protocol

All generators implement the `BracketGenerator` protocol:

```python
from typing import Protocol, List, runtime_checkable
from apps.tournament_ops.dtos.tournament import TournamentDTO
from apps.tournament_ops.dtos.stage import StageDTO
from apps.tournament_ops.dtos.team import TeamDTO
from apps.tournament_ops.dtos.match import MatchDTO

@runtime_checkable
class BracketGenerator(Protocol):
    def generate_bracket(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participants: List[TeamDTO]
    ) -> List[MatchDTO]:
        """Generate bracket matches for the given stage."""
        ...
    
    def validate_configuration(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participants: List[TeamDTO]
    ) -> None:
        """
        Validate tournament configuration.
        Raises ValueError if configuration is invalid.
        """
        ...
    
    def supports_third_place_match(self) -> bool:
        """Return whether this generator supports third-place matches."""
        ...
```

## BracketEngineService

**File**: `tournament_ops/services/bracket_engine_service.py`

**Purpose**: Orchestrator that selects the appropriate generator based on format and delegates bracket generation.

### Usage

```python
from apps.tournament_ops.services.bracket_engine_service import BracketEngineService

# Create service instance
engine = BracketEngineService()

# Generate bracket
matches = engine.generate_bracket_for_stage(
    tournament=tournament_dto,
    stage=stage_dto,
    participants=team_dtos
)
```

### Format Selection

The service selects generators in this priority order:

1. **Stage type** (`stage.type`) - if present, overrides tournament format
2. **Tournament format** (`tournament.format`) - fallback if stage type not specified

**Registered Formats**:
- `"single-elimination"`, `"single_elim"` → `SingleEliminationGenerator`
- `"double-elimination"`, `"double_elim"` → `DoubleEliminationGenerator`
- `"round-robin"`, `"round_robin"` → `RoundRobinGenerator`
- `"swiss"` → `SwissSystemGenerator`

### Extensibility

Register custom generators at runtime:

```python
from apps.tournament_ops.services.bracket_generators.base import BracketGenerator

class CustomGenerator:
    def generate_bracket(self, tournament, stage, participants):
        # Custom implementation
        return [MatchDTO(...), ...]
    
    def validate_configuration(self, tournament, stage, participants):
        # Custom validation
        pass
    
    def supports_third_place_match(self) -> bool:
        return False

# Register custom format
engine = BracketEngineService()
engine.register_generator("custom-format", CustomGenerator())

# Use custom format
tournament_dto.format = "custom-format"
matches = engine.generate_bracket_for_stage(tournament_dto, stage_dto, teams)
```

## Helper Functions

### `calculate_bye_count(participant_count: int) -> int`

Calculate number of byes needed to reach next power of two.

```python
from apps.tournament_ops.services.bracket_generators import calculate_bye_count

bye_count = calculate_bye_count(6)  # Returns 2 (8 - 6 = 2)
```

### `next_power_of_two(n: int) -> int`

Find the next power of two greater than or equal to n.

```python
from apps.tournament_ops.services.bracket_generators import next_power_of_two

slots = next_power_of_two(6)  # Returns 8
```

### `seed_participants_with_byes(participants: List[TeamDTO], bye_count: int) -> List[Optional[TeamDTO]]`

Insert byes for top seeds in a seeded participant list.

```python
from apps.tournament_ops.services.bracket_generators import seed_participants_with_byes

# 6 teams, 2 byes needed
seeded = seed_participants_with_byes(teams, 2)
# Returns: [None, None, Team1, Team2, Team3, Team4, Team5, Team6]
# Top 2 seeds get byes (None placeholders)
```

### `generate_round_robin_pairings(participants: List[TeamDTO]) -> List[List[Tuple[TeamDTO, TeamDTO]]]`

Generate round-robin pairings using circle method.

```python
from apps.tournament_ops.services.bracket_generators import generate_round_robin_pairings

pairings = generate_round_robin_pairings(teams)
# Returns: [
#   [(Team1, Team4), (Team2, Team3)],  # Round 1
#   [(Team1, Team3), (Team2, Team4)],  # Round 2
#   [(Team1, Team2), (Team3, Team4)],  # Round 3
# ]
```

## Feature Flag Integration

**Flag**: `BRACKETS_USE_UNIVERSAL_ENGINE` in `deltacrown/settings.py`

**Default**: `False` (uses legacy implementation)

**Purpose**: Safe rollout of universal bracket engine

### Entry Point

```python
from apps.tournaments.services.bracket_service import BracketService

# Feature-flagged wrapper
bracket = BracketService.generate_bracket_universal_safe(
    tournament_id=123,
    bracket_format="single-elimination",
    participants=participant_list
)
```

### Behavior

- **Flag = False** (default): Uses legacy `generate_bracket()` implementation
- **Flag = True**: Uses universal `BracketEngineService` with DTO conversion

### Rollback

To revert to legacy implementation:

```python
# In settings.py or environment
BRACKETS_USE_UNIVERSAL_ENGINE = False
```

No data migration required - flag controls runtime behavior only.

**Reference**: `CLEANUP_AND_TESTING_PART_6.md` §4.5 (Safe Rollback)

## Integration with Other Epics

### Epic 3.3: Stage Transition Service

**TODO**: Wire match advancement logic

- Currently: `BracketNode` instances created without `next_match_id` wiring
- Future: `StageTransitionService` will handle match progression between rounds
- Match completion → update standings → determine next round opponents

### Epic 3.4: Bracket Editor Service

**TODO**: Replace direct service calls with `TournamentAdapter`

- Currently: `BracketService._generate_bracket_using_universal_engine()` fetches data directly
- Future: Use `TournamentAdapter.get_tournament()`, `TournamentAdapter.generate_bracket()`
- Isolates tournaments domain from tournament_ops completely

### Epic 3.5: Scoring and Leaderboards

**TODO**: Implement Swiss system subsequent rounds

- Currently: Swiss rounds 2+ are stubbed with simple pairings
- Future: Use standings from scoring system to pair teams by record
- Features: Record grouping, tiebreakers, repeat avoidance

## Testing

**Test File**: `apps/tournament_ops/tests/test_bracket_generators.py`

**Coverage**:
- Architecture tests (no cross-domain imports, DTO-only)
- Helper function tests
- Generator tests (all formats, edge cases, validation)
- BracketEngineService tests (format selection, extensibility)

**Run Tests**:
```bash
pytest apps/tournament_ops/tests/test_bracket_generators.py -v
```

**Feature Flag Tests**: `apps/tournaments/tests/test_bracket_feature_flag.py`

```bash
pytest apps/tournaments/tests/test_bracket_feature_flag.py -v
```

## Examples

### Single Elimination (8 Teams)

```python
from apps.tournament_ops.services.bracket_engine_service import BracketEngineService
from apps.tournament_ops.dtos.tournament import TournamentDTO
from apps.tournament_ops.dtos.stage import StageDTO
from apps.tournament_ops.dtos.team import TeamDTO

tournament = TournamentDTO(id=1, name="Test Tournament", format="single-elimination")
stage = StageDTO(id=1, tournament_id=1, type="single-elimination", third_place_match=True)
teams = [TeamDTO(id=i, name=f"Team {i}", metadata={"seed": i}) for i in range(1, 9)]

engine = BracketEngineService()
matches = engine.generate_bracket_for_stage(tournament, stage, teams)

# Results:
# - 7 main matches (quarterfinals: 4, semifinals: 2, finals: 1)
# - 1 third-place match
# - Total: 8 matches
```

### Double Elimination (4 Teams)

```python
tournament = TournamentDTO(id=1, name="Test Tournament", format="double-elimination")
stage = StageDTO(
    id=1,
    tournament_id=1,
    type="double-elimination",
    metadata={"grand_finals_reset": True}
)
teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 5)]

engine = BracketEngineService()
matches = engine.generate_bracket_for_stage(tournament, stage, teams)

# Results:
# - Winners bracket: 3 matches (semifinals + finals)
# - Losers bracket: 2 matches
# - Grand finals: 1 match
# - Grand finals reset: 1 match (if LB champ wins GF)
# - Total: 7 matches (6 guaranteed + 1 conditional)
```

### Round Robin (5 Teams)

```python
tournament = TournamentDTO(id=1, name="Test Tournament", format="round-robin")
stage = StageDTO(id=1, tournament_id=1, type="round-robin")
teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 6)]

engine = BracketEngineService()
matches = engine.generate_bracket_for_stage(tournament, stage, teams)

# Results:
# - 5 rounds (each team plays once per round)
# - 10 total matches (5*4/2)
# - All unique pairings, no self-matches
```

### Swiss System (8 Teams, 5 Rounds)

```python
tournament = TournamentDTO(id=1, name="Test Tournament", format="swiss")
stage = StageDTO(id=1, tournament_id=1, type="swiss", metadata={"rounds_count": 5})
teams = [TeamDTO(id=i, name=f"Team {i}", metadata={"seed": i}) for i in range(1, 9)]

engine = BracketEngineService()
matches = engine.generate_bracket_for_stage(tournament, stage, teams)

# Results (current implementation):
# - Round 1: 4 matches (1v5, 2v6, 3v7, 4v8)
# - Rounds 2-5: Simple pairings (stub, to be replaced in Epic 3.5)
```

## Future Enhancements

### Planned (Phase 3)

- **Epic 3.3**: Match advancement wiring via `StageTransitionService`
- **Epic 3.4**: Bracket editing support via `BracketEditorService`
- **Epic 3.5**: Swiss rounds 2+ with standings-based pairing

### Potential Extensions

- **Multi-stage tournaments**: Chain multiple stages (group stage → playoffs)
- **Custom seeding algorithms**: Allow pluggable seeding strategies
- **Constraint-based scheduling**: Avoid conflicts, optimize for venues/times
- **Bracket balancing**: Automatic bracket rebalancing after dropouts
- **Third-party format support**: Import/export from external systems

## References

- **Phase 3, Epic 3.1**: Pluggable Bracket Generators (this document)
- **CLEANUP_AND_TESTING_PART_6.md** §4.5: Safe Rollback
- **DEV_PROGRESS_TRACKER.md**: Implementation status and progress logs
- **Source Code**: `apps/tournament_ops/services/bracket_generators/`
- **Tests**: `apps/tournament_ops/tests/test_bracket_generators.py`
