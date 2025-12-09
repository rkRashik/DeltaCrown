"""
Tests for bracket generators (Phase 3, Epic 3.1).

Validates all bracket generation algorithms:
- SingleEliminationGenerator
- DoubleEliminationGenerator
- RoundRobinGenerator
- SwissSystemGenerator
- BracketEngineService orchestrator

Architecture tests ensure no cross-domain imports (tournament_ops should not import tournaments.models).

Reference: Phase 3, Epic 3.1 - Pluggable Bracket Generators
"""

import pytest
from datetime import datetime
from typing import List
from apps.tournament_ops.services.bracket_generators import (
    BracketGenerator,
    SingleEliminationGenerator,
    DoubleEliminationGenerator,
    RoundRobinGenerator,
    SwissSystemGenerator,
    calculate_bye_count,
    next_power_of_two,
    seed_participants_with_byes,
    generate_round_robin_pairings,
)
from apps.tournament_ops.services.bracket_engine_service import BracketEngineService
from apps.tournament_ops.dtos.tournament import TournamentDTO
from apps.tournament_ops.dtos.stage import StageDTO
from apps.tournament_ops.dtos.team import TeamDTO
from apps.tournament_ops.dtos.match import MatchDTO


# ============================================================================
# TEST HELPERS - Factory functions for creating test DTOs
# ============================================================================

def make_tournament(id=1, name="Test Tournament", game_slug="test-game", **kwargs):
    """Create a minimal TournamentDTO for testing."""
    defaults = {
        "id": id,
        "name": name,
        "game_slug": game_slug,
        "stage": "registration",
        "team_size": 5,
        "max_teams": 16,
        "status": "draft",
        "start_time": datetime.now(),
        "ruleset": {},
    }
    defaults.update(kwargs)
    return TournamentDTO(**defaults)


def make_stage(id=1, tournament_id=1, type="single-elimination", **kwargs):
    """Create a minimal StageDTO for testing."""
    defaults = {
        "id": id,
        "tournament_id": tournament_id,
        "type": type,
        "third_place_match": False,
        "metadata": {},
    }
    defaults.update(kwargs)
    return StageDTO(**defaults)


def make_team(id=1, name="Team 1", **kwargs):
    """Create a minimal TeamDTO for testing."""
    defaults = {
        "id": id,
        "name": name,
        "captain_id": 100 + id,
        "captain_name": f"Captain {id}",
        "member_ids": [100 + id],
        "member_names": [f"Captain {id}"],
        "game": "test-game",
        "is_verified": True,
        "logo_url": None,
    }
    defaults.update(kwargs)
    return TeamDTO(**defaults)


def make_teams(count, **kwargs):
    """Create a list of TeamDTOs for testing."""
    return [make_team(id=i, name=f"Team {i}", **kwargs) for i in range(1, count + 1)]


# ============================================================================
# ARCHITECTURE TESTS - Ensure no cross-domain imports
# ============================================================================

def test_no_tournaments_model_imports():
    """
    Verify tournament_ops does not import from tournaments.models.
    
    This ensures proper domain boundary enforcement:
    - tournaments domain can import from tournament_ops
    - tournament_ops should never import from tournaments
    """
    import apps.tournament_ops.services.bracket_generators.base as base_module
    import apps.tournament_ops.services.bracket_generators.single_elimination as se_module
    import apps.tournament_ops.services.bracket_generators.double_elimination as de_module
    import apps.tournament_ops.services.bracket_generators.round_robin as rr_module
    import apps.tournament_ops.services.bracket_generators.swiss as swiss_module
    import apps.tournament_ops.services.bracket_engine_service as engine_module
    
    forbidden_imports = [
        "apps.tournaments.models",
        "tournaments.models",
        "django.db.models",  # Should not use ORM
    ]
    
    modules_to_check = [
        base_module,
        se_module,
        de_module,
        rr_module,
        swiss_module,
        engine_module,
    ]
    
    for module in modules_to_check:
        module_source = module.__file__
        with open(module_source, 'r') as f:
            content = f.read()
            for forbidden in forbidden_imports:
                assert forbidden not in content, (
                    f"Module {module.__name__} imports forbidden module: {forbidden}"
                )


def test_generators_are_dto_only():
    """
    Verify all generators accept only DTO parameters.
    
    Ensures framework-light architecture - no ORM dependencies.
    """
    generators = [
        SingleEliminationGenerator(),
        DoubleEliminationGenerator(),
        RoundRobinGenerator(),
        SwissSystemGenerator(),
    ]
    
    # Create sample DTOs
    tournament = make_tournament()
    stage = make_stage()
    teams = make_teams(4)
    
    # All generators should accept DTOs without errors
    for generator in generators:
        if isinstance(generator, SwissSystemGenerator):
            # Swiss requires rounds_count in metadata
            swiss_stage = make_stage(type="swiss", metadata={"rounds_count": 3})
            generator.validate_configuration(tournament, swiss_stage, teams)
        else:
            generator.validate_configuration(tournament, stage, teams)


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

def test_calculate_bye_count():
    """Test bye calculation for non-power-of-two participant counts."""
    assert calculate_bye_count(2) == 0
    assert calculate_bye_count(3) == 1  # 4 - 3 = 1
    assert calculate_bye_count(4) == 0
    assert calculate_bye_count(5) == 3  # 8 - 5 = 3
    assert calculate_bye_count(6) == 2  # 8 - 6 = 2
    assert calculate_bye_count(7) == 1  # 8 - 7 = 1
    assert calculate_bye_count(8) == 0
    assert calculate_bye_count(9) == 7  # 16 - 9 = 7


def test_next_power_of_two():
    """Test next power of two calculation."""
    assert next_power_of_two(1) == 1
    assert next_power_of_two(2) == 2
    assert next_power_of_two(3) == 4
    assert next_power_of_two(4) == 4
    assert next_power_of_two(5) == 8
    assert next_power_of_two(8) == 8
    assert next_power_of_two(9) == 16
    assert next_power_of_two(16) == 16
    assert next_power_of_two(17) == 32


def test_seed_participants_with_byes():
    """Test seeding with bye insertion for top seeds."""
    teams = make_teams(6)
    
    # 6 teams -> 2 byes needed (to make 8)
    seeded = seed_participants_with_byes(teams, 2)
    
    assert len(seeded) == 8
    # First two slots should be byes (top seeds get byes)
    assert seeded[0] is None
    assert seeded[1] is None
    # Remaining should be teams
    assert seeded[2].id == 1
    assert seeded[3].id == 2


def test_generate_round_robin_pairings():
    """Test round-robin pairing generation (circle method)."""
    teams = make_teams(4)
    
    pairings = generate_round_robin_pairings(teams)
    
    # 4 teams -> 3 rounds, 2 matches per round, 6 total matches
    assert len(pairings) == 3  # 3 rounds
    total_matches = sum(len(round_pairings) for round_pairings in pairings)
    assert total_matches == 6  # 4*(4-1)/2 = 6
    
    # Verify all pairings are unique
    all_matchups = set()
    for round_pairings in pairings:
        for team1, team2 in round_pairings:
            matchup = tuple(sorted([team1.id, team2.id]))
            assert matchup not in all_matchups, f"Duplicate matchup: {matchup}"
            all_matchups.add(matchup)
    
    # Verify no self-matches
    for round_pairings in pairings:
        for team1, team2 in round_pairings:
            assert team1.id != team2.id, "Self-match detected"


# ============================================================================
# SINGLE ELIMINATION GENERATOR TESTS
# ============================================================================

def test_single_elimination_2_teams():
    """Test single elimination with 2 teams (1 match)."""
    generator = SingleEliminationGenerator()
    tournament = make_tournament()
    stage = make_stage()
    teams = make_teams(2)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    assert len(matches) == 1
    assert matches[0].round_number == 1
    assert matches[0].match_number == 1
    assert matches[0].team1_id == 1
    assert matches[0].team2_id == 2
    assert matches[0].stage_type == "main"


def test_single_elimination_4_teams():
    """Test single elimination with 4 teams (power of 2)."""
    generator = SingleEliminationGenerator()
    tournament = make_tournament()
    stage = make_stage()
    teams = make_teams(4)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # 4 teams -> 2 rounds (semifinals + finals)
    # Semifinals: 2 matches, Finals: 1 match = 3 total
    assert len(matches) == 3
    
    # Check round structure
    round1_matches = [m for m in matches if m.round_number == 1]
    round2_matches = [m for m in matches if m.round_number == 2]
    assert len(round1_matches) == 2
    assert len(round2_matches) == 1


def test_single_elimination_6_teams_with_byes():
    """Test single elimination with 6 teams (requires 2 byes)."""
    generator = SingleEliminationGenerator()
    tournament = make_tournament()
    stage = make_stage()
    teams = make_teams(6)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # 6 teams -> 8 slots (2 byes)
    # Round 1: 4 matches (but 2 are byes, so only 2 real matches)
    # Round 2: 2 matches (semifinals)
    # Round 3: 1 match (finals)
    # Total real matches: 2 + 2 + 1 = 5
    assert len(matches) == 5
    
    # Verify no matches have None participants
    for match in matches:
        assert match.team1_id is not None or match.team2_id is not None


def test_single_elimination_third_place_match():
    """Test single elimination with third-place match."""
    generator = SingleEliminationGenerator()
    tournament = make_tournament()
    stage = make_stage(third_place_match=True)
    teams = make_teams(4)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # 4 teams: semifinals (2) + finals (1) + 3rd place (1) = 4 matches
    assert len(matches) == 4
    
    # Find third-place match (should be in final round with stage_type="third_place")
    third_place_matches = [m for m in matches if m.stage_type == "third_place"]
    assert len(third_place_matches) == 1


def test_single_elimination_validation():
    """Test single elimination validation errors."""
    generator = SingleEliminationGenerator()
    tournament = make_tournament()
    stage = make_stage()
    
    # Too few participants
    with pytest.raises(ValueError, match="at least 2 participants"):
        generator.validate_configuration(tournament, stage, make_teams(1))
    
    # Too many participants
    teams_too_many = make_teams(300)
    with pytest.raises(ValueError, match="maximum of 256 participants"):
        generator.validate_configuration(tournament, stage, teams_too_many)


# ============================================================================
# DOUBLE ELIMINATION GENERATOR TESTS
# ============================================================================

def test_double_elimination_4_teams():
    """Test double elimination with 4 teams."""
    generator = DoubleEliminationGenerator()
    tournament = make_tournament()
    stage = make_stage(type="double-elimination")
    teams = make_teams(4)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # Winners bracket: 2 rounds (2 + 1 = 3 matches)
    # Losers bracket: 2*(2-1) = 2 rounds (1 + 1 = 2 matches)
    # Grand finals: 1 match
    # Total: 3 + 2 + 1 = 6 matches
    assert len(matches) == 6
    
    # Check stage types
    winners_matches = [m for m in matches if m.stage_type == "winners"]
    losers_matches = [m for m in matches if m.stage_type == "losers"]
    gf_matches = [m for m in matches if m.stage_type == "grand_finals"]
    
    assert len(winners_matches) == 3
    assert len(losers_matches) == 2
    assert len(gf_matches) == 1


def test_double_elimination_8_teams():
    """Test double elimination with 8 teams."""
    generator = DoubleEliminationGenerator()
    tournament = make_tournament()
    stage = make_stage(type="double-elimination")
    teams = make_teams(8)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # Winners bracket: 3 rounds (4 + 2 + 1 = 7 matches)
    # Losers bracket: 2*(3-1) = 4 rounds (2 + 2 + 1 + 1 = 6 matches)
    # Grand finals: 1 match
    # Total: 7 + 6 + 1 = 14 matches
    assert len(matches) == 14
    
    winners_matches = [m for m in matches if m.stage_type == "winners"]
    losers_matches = [m for m in matches if m.stage_type == "losers"]
    
    assert len(winners_matches) == 7
    assert len(losers_matches) == 6


def test_double_elimination_grand_finals_reset():
    """Test double elimination with grand finals reset."""
    generator = DoubleEliminationGenerator()
    tournament = make_tournament()
    stage = make_stage(type="double-elimination", metadata={"grand_finals_reset": True})
    teams = make_teams(4)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # Standard 4-team structure + 1 extra for reset
    # 6 matches + 1 reset = 7 matches
    gf_matches = [m for m in matches if "grand_finals" in m.stage_type]
    assert len(gf_matches) == 2  # Grand finals + reset
    
    # One should be "grand_finals", one should be "grand_finals_reset"
    assert any(m.stage_type == "grand_finals" for m in gf_matches)
    assert any(m.stage_type == "grand_finals_reset" for m in gf_matches)


def test_double_elimination_validation():
    """Test double elimination validation errors."""
    generator = DoubleEliminationGenerator()
    tournament = make_tournament()
    stage = make_stage(type="double-elimination")
    
    # Too few participants
    teams_too_few = make_teams(3)
    with pytest.raises(ValueError, match="at least 4 participants"):
        generator.validate_configuration(tournament, stage, teams_too_few)
    
    # Too many participants
    teams_too_many = make_teams(130)
    with pytest.raises(ValueError, match="maximum of 128 participants"):
        generator.validate_configuration(tournament, stage, teams_too_many)


# ============================================================================
# ROUND ROBIN GENERATOR TESTS
# ============================================================================

def test_round_robin_4_teams():
    """Test round-robin with 4 teams."""
    generator = RoundRobinGenerator()
    tournament = make_tournament()
    stage = make_stage(type="round-robin")
    teams = make_teams(4)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # 4 teams -> 4*(4-1)/2 = 6 matches
    assert len(matches) == 6
    
    # Verify all pairings are unique
    matchups = set()
    for match in matches:
        matchup = tuple(sorted([match.team1_id, match.team2_id]))
        assert matchup not in matchups, "Duplicate matchup found"
        matchups.add(matchup)
    
    # Verify expected number of rounds
    rounds = set(m.round_number for m in matches)
    assert len(rounds) == 3  # 4-1 = 3 rounds


def test_round_robin_no_self_matches():
    """Test that round-robin never creates self-matches."""
    generator = RoundRobinGenerator()
    tournament = make_tournament()
    stage = make_stage(type="round-robin")
    teams = make_teams(6)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    for match in matches:
        assert match.team1_id != match.team2_id, "Self-match detected"


def test_round_robin_unique_pairings():
    """Test that each team plays every other team exactly once."""
    generator = RoundRobinGenerator()
    tournament = make_tournament()
    stage = make_stage(type="round-robin")
    teams = make_teams(5)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # 5 teams -> 5*(5-1)/2 = 10 matches
    assert len(matches) == 10
    
    # Build adjacency map (team_id -> set of opponents)
    opponents_map = {i: set() for i in range(1, 6)}
    for match in matches:
        opponents_map[match.team1_id].add(match.team2_id)
        opponents_map[match.team2_id].add(match.team1_id)
    
    # Each team should face all 4 other teams exactly once
    for team_id, opponents in opponents_map.items():
        assert len(opponents) == 4, f"Team {team_id} has wrong number of opponents"
        assert team_id not in opponents, f"Team {team_id} faces itself"


def test_round_robin_validation():
    """Test round-robin validation errors."""
    generator = RoundRobinGenerator()
    tournament = make_tournament()
    stage = make_stage(type="round-robin")
    
    # Too few participants
    teams_too_few = make_teams(2)
    with pytest.raises(ValueError, match="at least 3 participants"):
        generator.validate_configuration(tournament, stage, teams_too_few)
    
    # Too many participants
    teams_too_many = make_teams(25)
    with pytest.raises(ValueError, match="maximum of 20 participants"):
        generator.validate_configuration(tournament, stage, teams_too_many)


# ============================================================================
# SWISS SYSTEM GENERATOR TESTS
# ============================================================================

def test_swiss_first_round_pairing():
    """Test Swiss system first-round pairing (top half vs bottom half)."""
    generator = SwissSystemGenerator()
    tournament = make_tournament()
    stage = make_stage(type="swiss", metadata={"rounds_count": 3})
    teams = make_teams(8)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # First round only: 8 teams -> 4 matches
    first_round_matches = [m for m in matches if m.round_number == 1]
    assert len(first_round_matches) == 4
    
    # Verify pairing structure: 1v5, 2v6, 3v7, 4v8
    pairings = {(m.team1_id, m.team2_id) for m in first_round_matches}
    expected = {(1, 5), (2, 6), (3, 7), (4, 8)}
    assert pairings == expected


def test_swiss_subsequent_rounds_stub():
    """Test Swiss system subsequent rounds (stub implementation)."""
    generator = SwissSystemGenerator()
    tournament = make_tournament()
    stage = make_stage(type="swiss", metadata={"rounds_count": 3})
    teams = make_teams(8)
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # Current implementation: only first round is complete
    # Subsequent rounds return placeholder/simple pairings
    # This will be replaced in Epic 3.5 with standings-based pairing
    assert len(matches) >= 4  # At least first round


def test_swiss_validation():
    """Test Swiss system validation errors."""
    generator = SwissSystemGenerator()
    tournament = make_tournament()
    
    # Missing rounds_count in metadata
    stage_no_rounds = make_stage(type="swiss")
    teams = make_teams(8)
    with pytest.raises(ValueError, match="rounds_count"):
        generator.validate_configuration(tournament, stage_no_rounds, teams)
    
    # Too few participants
    stage = make_stage(type="swiss", metadata={"rounds_count": 3})
    teams_too_few = make_teams(2)
    with pytest.raises(ValueError, match="at least 4 participants"):
        generator.validate_configuration(tournament, stage, teams_too_few)


# ============================================================================
# BRACKET ENGINE SERVICE TESTS
# ============================================================================

def test_bracket_engine_format_selection():
    """Test BracketEngineService selects correct generator for format."""
    engine = BracketEngineService()
    tournament = make_tournament()
    stage = make_stage()
    teams = make_teams(4)
    
    matches = engine.generate_bracket_for_stage(tournament, stage, teams)
    
    # Should use SingleEliminationGenerator
    assert len(matches) == 3  # 4 teams -> 3 matches (semifinals + finals)


def test_bracket_engine_stage_type_override():
    """Test BracketEngineService uses stage.type if present."""
    engine = BracketEngineService()
    tournament = make_tournament()
    # Stage overrides tournament format
    stage = make_stage(type="double-elimination")
    teams = make_teams(4)
    
    matches = engine.generate_bracket_for_stage(tournament, stage, teams)
    
    # Should use DoubleEliminationGenerator (6 matches for 4 teams)
    assert len(matches) == 6


def test_bracket_engine_unknown_format():
    """Test BracketEngineService raises error for unknown format."""
    engine = BracketEngineService()
    tournament = make_tournament()
    stage = make_stage(type="unknown-format")
    teams = make_teams(4)
    
    with pytest.raises(ValueError, match="Unknown bracket format"):
        engine.generate_bracket_for_stage(tournament, stage, teams)


def test_bracket_engine_extensibility():
    """Test BracketEngineService can be extended with custom generators."""
    # Create a minimal custom generator
    class CustomGenerator:
        def generate_bracket(self, tournament, stage, participants):
            return [
                MatchDTO(
                    id=0,
                    stage_id=stage.id,
                    round_number=1,
                    match_number=1,
                    team1_id=participants[0].id,
                    team2_id=participants[1].id,
                    stage_type="custom",
                )
            ]
        
        def validate_configuration(self, tournament, stage, participants):
            if len(participants) < 2:
                raise ValueError("Need at least 2 participants")
        
        def supports_third_place_match(self) -> bool:
            return False
    
    engine = BracketEngineService()
    engine.register_generator("custom-format", CustomGenerator())
    
    tournament = make_tournament()
    stage = make_stage(type="custom-format")
    teams = make_teams(4)
    
    matches = engine.generate_bracket_for_stage(tournament, stage, teams)
    
    assert len(matches) == 1
    assert matches[0].stage_type == "custom"


def test_bracket_engine_validation_delegation():
    """Test BracketEngineService delegates validation to generators."""
    engine = BracketEngineService()
    tournament = make_tournament()
    stage = make_stage()
    teams_too_few = make_teams(1)  # Only 1 team
    
    with pytest.raises(ValueError, match="at least 2 participants"):
        engine.generate_bracket_for_stage(tournament, stage, teams_too_few)



# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

def test_calculate_bye_count():
    """Test bye calculation for non-power-of-two participant counts."""
    assert calculate_bye_count(2) == 0
    assert calculate_bye_count(3) == 1  # 4 - 3 = 1
    assert calculate_bye_count(4) == 0
    assert calculate_bye_count(5) == 3  # 8 - 5 = 3
    assert calculate_bye_count(6) == 2  # 8 - 6 = 2
    assert calculate_bye_count(7) == 1  # 8 - 7 = 1
    assert calculate_bye_count(8) == 0
    assert calculate_bye_count(9) == 7  # 16 - 9 = 7


def test_next_power_of_two():
    """Test next power of two calculation."""
    assert next_power_of_two(1) == 1
    assert next_power_of_two(2) == 2
    assert next_power_of_two(3) == 4
    assert next_power_of_two(4) == 4
    assert next_power_of_two(5) == 8
    assert next_power_of_two(8) == 8
    assert next_power_of_two(9) == 16
    assert next_power_of_two(16) == 16
    assert next_power_of_two(17) == 32


def test_seed_participants_with_byes():
    """Test seeding with bye insertion for top seeds."""
    teams = [
        TeamDTO(id=1, name="Team 1", metadata={"seed": 1}),
        TeamDTO(id=2, name="Team 2", metadata={"seed": 2}),
        TeamDTO(id=3, name="Team 3", metadata={"seed": 3}),
        TeamDTO(id=4, name="Team 4", metadata={"seed": 4}),
        TeamDTO(id=5, name="Team 5", metadata={"seed": 5}),
        TeamDTO(id=6, name="Team 6", metadata={"seed": 6}),
    ]
    
    # 6 teams -> 2 byes needed (to make 8)
    seeded = seed_participants_with_byes(teams, 2)
    
    assert len(seeded) == 8
    # First two slots should be byes (top seeds get byes)
    assert seeded[0] is None
    assert seeded[1] is None
    # Remaining should be teams
    assert seeded[2].id == 1
    assert seeded[3].id == 2


def test_generate_round_robin_pairings():
    """Test round-robin pairing generation (circle method)."""
    teams = [
        TeamDTO(id=1, name="Team 1"),
        TeamDTO(id=2, name="Team 2"),
        TeamDTO(id=3, name="Team 3"),
        TeamDTO(id=4, name="Team 4"),
    ]
    
    pairings = generate_round_robin_pairings(teams)
    
    # 4 teams -> 3 rounds, 2 matches per round, 6 total matches
    assert len(pairings) == 3  # 3 rounds
    total_matches = sum(len(round_pairings) for round_pairings in pairings)
    assert total_matches == 6  # 4*(4-1)/2 = 6
    
    # Verify all pairings are unique
    all_matchups = set()
    for round_pairings in pairings:
        for team1, team2 in round_pairings:
            matchup = tuple(sorted([team1.id, team2.id]))
            assert matchup not in all_matchups, f"Duplicate matchup: {matchup}"
            all_matchups.add(matchup)
    
    # Verify no self-matches
    for round_pairings in pairings:
        for team1, team2 in round_pairings:
            assert team1.id != team2.id, "Self-match detected"


# ============================================================================
# SINGLE ELIMINATION GENERATOR TESTS
# ============================================================================

def test_single_elimination_2_teams():
    """Test single elimination with 2 teams (1 match)."""
    generator = SingleEliminationGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="single-elimination")
    stage = StageDTO(id=1, tournament_id=1, type="single-elimination")
    teams = [
        TeamDTO(id=1, name="Team 1"),
        TeamDTO(id=2, name="Team 2"),
    ]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    assert len(matches) == 1
    assert matches[0].round_number == 1
    assert matches[0].match_number == 1
    assert matches[0].team1_id == 1
    assert matches[0].team2_id == 2
    assert matches[0].stage_type == "main"


def test_single_elimination_4_teams():
    """Test single elimination with 4 teams (power of 2)."""
    generator = SingleEliminationGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="single-elimination")
    stage = StageDTO(id=1, tournament_id=1, type="single-elimination")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 5)]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # 4 teams -> 2 rounds (semifinals + finals)
    # Semifinals: 2 matches, Finals: 1 match = 3 total
    assert len(matches) == 3
    
    # Check round structure
    round1_matches = [m for m in matches if m.round_number == 1]
    round2_matches = [m for m in matches if m.round_number == 2]
    assert len(round1_matches) == 2
    assert len(round2_matches) == 1


def test_single_elimination_6_teams_with_byes():
    """Test single elimination with 6 teams (requires 2 byes)."""
    generator = SingleEliminationGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="single-elimination")
    stage = StageDTO(id=1, tournament_id=1, type="single-elimination")
    teams = [TeamDTO(id=i, name=f"Team {i}", metadata={"seed": i}) for i in range(1, 7)]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # 6 teams -> 8 slots (2 byes)
    # Round 1: 4 matches (but 2 are byes, so only 2 real matches)
    # Round 2: 2 matches (semifinals)
    # Round 3: 1 match (finals)
    # Total real matches: 2 + 2 + 1 = 5
    assert len(matches) == 5
    
    # Verify no matches have None participants
    for match in matches:
        assert match.team1_id is not None or match.team2_id is not None


def test_single_elimination_third_place_match():
    """Test single elimination with third-place match."""
    generator = SingleEliminationGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="single-elimination")
    stage = StageDTO(id=1, tournament_id=1, type="single-elimination", third_place_match=True)
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 5)]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # 4 teams: semifinals (2) + finals (1) + 3rd place (1) = 4 matches
    assert len(matches) == 4
    
    # Find third-place match (should be in final round with stage_type="third_place")
    third_place_matches = [m for m in matches if m.stage_type == "third_place"]
    assert len(third_place_matches) == 1


def test_single_elimination_validation():
    """Test single elimination validation errors."""
    generator = SingleEliminationGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="single-elimination")
    stage = StageDTO(id=1, tournament_id=1, type="single-elimination")
    
    # Too few participants
    with pytest.raises(ValueError, match="at least 2 participants"):
        generator.validate_configuration(tournament, stage, [TeamDTO(id=1, name="Team 1")])
    
    # Too many participants
    teams_too_many = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 300)]
    with pytest.raises(ValueError, match="maximum of 256 participants"):
        generator.validate_configuration(tournament, stage, teams_too_many)


# ============================================================================
# DOUBLE ELIMINATION GENERATOR TESTS
# ============================================================================

def test_double_elimination_4_teams():
    """Test double elimination with 4 teams."""
    generator = DoubleEliminationGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="double-elimination")
    stage = StageDTO(id=1, tournament_id=1, type="double-elimination")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 5)]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # Winners bracket: 2 rounds (2 + 1 = 3 matches)
    # Losers bracket: 2*(2-1) = 2 rounds (1 + 1 = 2 matches)
    # Grand finals: 1 match
    # Total: 3 + 2 + 1 = 6 matches
    assert len(matches) == 6
    
    # Check stage types
    winners_matches = [m for m in matches if m.stage_type == "winners"]
    losers_matches = [m for m in matches if m.stage_type == "losers"]
    gf_matches = [m for m in matches if m.stage_type == "grand_finals"]
    
    assert len(winners_matches) == 3
    assert len(losers_matches) == 2
    assert len(gf_matches) == 1


def test_double_elimination_8_teams():
    """Test double elimination with 8 teams."""
    generator = DoubleEliminationGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="double-elimination")
    stage = StageDTO(id=1, tournament_id=1, type="double-elimination")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 9)]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # Winners bracket: 3 rounds (4 + 2 + 1 = 7 matches)
    # Losers bracket: 2*(3-1) = 4 rounds (2 + 2 + 1 + 1 = 6 matches)
    # Grand finals: 1 match
    # Total: 7 + 6 + 1 = 14 matches
    assert len(matches) == 14
    
    winners_matches = [m for m in matches if m.stage_type == "winners"]
    losers_matches = [m for m in matches if m.stage_type == "losers"]
    
    assert len(winners_matches) == 7
    assert len(losers_matches) == 6


def test_double_elimination_grand_finals_reset():
    """Test double elimination with grand finals reset."""
    generator = DoubleEliminationGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="double-elimination")
    stage = StageDTO(
        id=1,
        tournament_id=1,
        type="double-elimination",
        metadata={"grand_finals_reset": True}
    )
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 5)]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # Standard 4-team structure + 1 extra for reset
    # 6 matches + 1 reset = 7 matches
    gf_matches = [m for m in matches if "grand_finals" in m.stage_type]
    assert len(gf_matches) == 2  # Grand finals + reset
    
    # One should be "grand_finals", one should be "grand_finals_reset"
    assert any(m.stage_type == "grand_finals" for m in gf_matches)
    assert any(m.stage_type == "grand_finals_reset" for m in gf_matches)


def test_double_elimination_validation():
    """Test double elimination validation errors."""
    generator = DoubleEliminationGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="double-elimination")
    stage = StageDTO(id=1, tournament_id=1, type="double-elimination")
    
    # Too few participants
    teams_too_few = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 4)]
    with pytest.raises(ValueError, match="at least 4 participants"):
        generator.validate_configuration(tournament, stage, teams_too_few)
    
    # Too many participants
    teams_too_many = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 130)]
    with pytest.raises(ValueError, match="maximum of 128 participants"):
        generator.validate_configuration(tournament, stage, teams_too_many)


# ============================================================================
# ROUND ROBIN GENERATOR TESTS
# ============================================================================

def test_round_robin_4_teams():
    """Test round-robin with 4 teams."""
    generator = RoundRobinGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="round-robin")
    stage = StageDTO(id=1, tournament_id=1, type="round-robin")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 5)]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # 4 teams -> 4*(4-1)/2 = 6 matches
    assert len(matches) == 6
    
    # Verify all pairings are unique
    matchups = set()
    for match in matches:
        matchup = tuple(sorted([match.team1_id, match.team2_id]))
        assert matchup not in matchups, "Duplicate matchup found"
        matchups.add(matchup)
    
    # Verify expected number of rounds
    rounds = set(m.round_number for m in matches)
    assert len(rounds) == 3  # 4-1 = 3 rounds


def test_round_robin_no_self_matches():
    """Test that round-robin never creates self-matches."""
    generator = RoundRobinGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="round-robin")
    stage = StageDTO(id=1, tournament_id=1, type="round-robin")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 7)]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    for match in matches:
        assert match.team1_id != match.team2_id, "Self-match detected"


def test_round_robin_unique_pairings():
    """Test that each team plays every other team exactly once."""
    generator = RoundRobinGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="round-robin")
    stage = StageDTO(id=1, tournament_id=1, type="round-robin")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 6)]  # 5 teams
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # 5 teams -> 5*(5-1)/2 = 10 matches
    assert len(matches) == 10
    
    # Build adjacency map (team_id -> set of opponents)
    opponents_map = {i: set() for i in range(1, 6)}
    for match in matches:
        opponents_map[match.team1_id].add(match.team2_id)
        opponents_map[match.team2_id].add(match.team1_id)
    
    # Each team should face all 4 other teams exactly once
    for team_id, opponents in opponents_map.items():
        assert len(opponents) == 4, f"Team {team_id} has wrong number of opponents"
        assert team_id not in opponents, f"Team {team_id} faces itself"


def test_round_robin_validation():
    """Test round-robin validation errors."""
    generator = RoundRobinGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="round-robin")
    stage = StageDTO(id=1, tournament_id=1, type="round-robin")
    
    # Too few participants
    teams_too_few = [TeamDTO(id=1, name="Team 1"), TeamDTO(id=2, name="Team 2")]
    with pytest.raises(ValueError, match="at least 3 participants"):
        generator.validate_configuration(tournament, stage, teams_too_few)
    
    # Too many participants
    teams_too_many = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 25)]
    with pytest.raises(ValueError, match="maximum of 20 participants"):
        generator.validate_configuration(tournament, stage, teams_too_many)


# ============================================================================
# SWISS SYSTEM GENERATOR TESTS
# ============================================================================

def test_swiss_first_round_pairing():
    """Test Swiss system first-round pairing (top half vs bottom half)."""
    generator = SwissSystemGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="swiss")
    stage = StageDTO(id=1, tournament_id=1, type="swiss", metadata={"rounds_count": 3})
    teams = [TeamDTO(id=i, name=f"Team {i}", metadata={"seed": i}) for i in range(1, 9)]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # First round only: 8 teams -> 4 matches
    first_round_matches = [m for m in matches if m.round_number == 1]
    assert len(first_round_matches) == 4
    
    # Verify pairing structure: 1v5, 2v6, 3v7, 4v8
    pairings = {(m.team1_id, m.team2_id) for m in first_round_matches}
    expected = {(1, 5), (2, 6), (3, 7), (4, 8)}
    assert pairings == expected


def test_swiss_subsequent_rounds_stub():
    """Test Swiss system subsequent rounds (stub implementation)."""
    generator = SwissSystemGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="swiss")
    stage = StageDTO(id=1, tournament_id=1, type="swiss", metadata={"rounds_count": 3})
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 9)]
    
    matches = generator.generate_bracket(tournament, stage, teams)
    
    # Current implementation: only first round is complete
    # Subsequent rounds return placeholder/simple pairings
    # This will be replaced in Epic 3.5 with standings-based pairing
    assert len(matches) >= 4  # At least first round


def test_swiss_validation():
    """Test Swiss system validation errors."""
    generator = SwissSystemGenerator()
    tournament = TournamentDTO(id=1, name="Test", format="swiss")
    
    # Missing rounds_count in metadata
    stage_no_rounds = StageDTO(id=1, tournament_id=1, type="swiss")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 9)]
    with pytest.raises(ValueError, match="rounds_count"):
        generator.validate_configuration(tournament, stage_no_rounds, teams)
    
    # Too few participants
    stage = StageDTO(id=1, tournament_id=1, type="swiss", metadata={"rounds_count": 3})
    teams_too_few = [TeamDTO(id=1, name="Team 1"), TeamDTO(id=2, name="Team 2")]
    with pytest.raises(ValueError, match="at least 4 participants"):
        generator.validate_configuration(tournament, stage, teams_too_few)


# ============================================================================
# BRACKET ENGINE SERVICE TESTS
# ============================================================================

def test_bracket_engine_format_selection():
    """Test BracketEngineService selects correct generator for format."""
    engine = BracketEngineService()
    tournament = TournamentDTO(id=1, name="Test", format="single-elimination")
    stage = StageDTO(id=1, tournament_id=1, type="single-elimination")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 5)]
    
    matches = engine.generate_bracket_for_stage(tournament, stage, teams)
    
    # Should use SingleEliminationGenerator
    assert len(matches) == 3  # 4 teams -> 3 matches (semifinals + finals)


def test_bracket_engine_stage_type_override():
    """Test BracketEngineService uses stage.type if present."""
    engine = BracketEngineService()
    tournament = TournamentDTO(id=1, name="Test", format="single-elimination")
    # Stage overrides tournament format
    stage = StageDTO(id=1, tournament_id=1, type="double-elimination")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 5)]
    
    matches = engine.generate_bracket_for_stage(tournament, stage, teams)
    
    # Should use DoubleEliminationGenerator (6 matches for 4 teams)
    assert len(matches) == 6


def test_bracket_engine_unknown_format():
    """Test BracketEngineService raises error for unknown format."""
    engine = BracketEngineService()
    tournament = TournamentDTO(id=1, name="Test", format="unknown-format")
    stage = StageDTO(id=1, tournament_id=1, type="unknown-format")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 5)]
    
    with pytest.raises(ValueError, match="Unknown bracket format"):
        engine.generate_bracket_for_stage(tournament, stage, teams)


def test_bracket_engine_extensibility():
    """Test BracketEngineService can be extended with custom generators."""
    # Create a minimal custom generator
    class CustomGenerator:
        def generate_bracket(self, tournament, stage, participants):
            return [
                MatchDTO(
                    id=0,
                    stage_id=stage.id,
                    round_number=1,
                    match_number=1,
                    team1_id=participants[0].id,
                    team2_id=participants[1].id,
                    stage_type="custom",
                )
            ]
        
        def validate_configuration(self, tournament, stage, participants):
            if len(participants) < 2:
                raise ValueError("Need at least 2 participants")
        
        def supports_third_place_match(self) -> bool:
            return False
    
    engine = BracketEngineService()
    engine.register_generator("custom-format", CustomGenerator())
    
    tournament = TournamentDTO(id=1, name="Test", format="custom-format")
    stage = StageDTO(id=1, tournament_id=1, type="custom-format")
    teams = [TeamDTO(id=i, name=f"Team {i}") for i in range(1, 5)]
    
    matches = engine.generate_bracket_for_stage(tournament, stage, teams)
    
    assert len(matches) == 1
    assert matches[0].stage_type == "custom"


def test_bracket_engine_validation_delegation():
    """Test BracketEngineService delegates validation to generators."""
    engine = BracketEngineService()
    tournament = TournamentDTO(id=1, name="Test", format="single-elimination")
    stage = StageDTO(id=1, tournament_id=1, type="single-elimination")
    teams_too_few = [TeamDTO(id=1, name="Team 1")]  # Only 1 team
    
    with pytest.raises(ValueError, match="at least 2 participants"):
        engine.generate_bracket_for_stage(tournament, stage, teams_too_few)
