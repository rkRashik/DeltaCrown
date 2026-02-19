"""
Tests for bracket generators (Phase 3, Epic 3.1).

Validates all bracket generation algorithms:
- SingleEliminationGenerator
- DoubleEliminationGenerator
- RoundRobinGenerator
- SwissSystemGenerator
- BracketEngineService orchestrator

Architecture tests ensure no cross-domain imports (tournament_ops should not
import tournaments.models).

Reference: Phase 3, Epic 3.1 — Pluggable Bracket Generators
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
# TEST HELPERS — Factory functions for test DTOs
# ============================================================================

def make_tournament(id=1, name="Test Tournament", game_slug="test-game", **kw):
    """Create a minimal TournamentDTO for testing."""
    defaults = dict(
        id=id, name=name, game_slug=game_slug,
        stage="registration", team_size=5, max_teams=16,
        status="draft", start_time=datetime.now(), ruleset={},
    )
    defaults.update(kw)
    return TournamentDTO(**defaults)


def make_stage(id=1, type="single_elim", **kw):
    """Create a minimal StageDTO for testing.

    Accepts ``third_place_match`` shorthand and moves it into ``config``.
    """
    third = kw.pop("third_place_match", False)
    config = kw.pop("config", {})
    if third:
        config["third_place_match"] = True
    defaults = dict(
        id=id, name="Test Stage", type=type, order=1,
        config=config, metadata=kw.pop("metadata", None),
    )
    defaults.update(kw)
    return StageDTO(**defaults)


def make_team(id=1, name="Team 1", **kw):
    """Create a minimal TeamDTO for testing."""
    defaults = dict(
        id=id, name=name, captain_id=100 + id,
        captain_name=f"Captain {id}", member_ids=[100 + id],
        member_names=[f"Captain {id}"], game="test-game",
        is_verified=True, logo_url=None,
    )
    defaults.update(kw)
    return TeamDTO(**defaults)


def make_teams(count, **kw):
    """Create *count* TeamDTOs (ids 1..count)."""
    return [make_team(id=i, name=f"Team {i}", **kw) for i in range(1, count + 1)]


# ============================================================================
# ARCHITECTURE TESTS
# ============================================================================

def test_no_tournaments_model_imports():
    """tournament_ops modules must not import tournaments.models."""
    import apps.tournament_ops.services.bracket_generators.base as base_mod
    import apps.tournament_ops.services.bracket_generators.single_elimination as se_mod
    import apps.tournament_ops.services.bracket_generators.double_elimination as de_mod
    import apps.tournament_ops.services.bracket_generators.round_robin as rr_mod
    import apps.tournament_ops.services.bracket_generators.swiss as sw_mod
    import apps.tournament_ops.services.bracket_engine_service as eng_mod

    forbidden = ["apps.tournaments.models", "tournaments.models", "django.db.models"]

    for mod in [base_mod, se_mod, de_mod, rr_mod, sw_mod, eng_mod]:
        with open(mod.__file__, "r") as fh:
            src = fh.read()
        for f in forbidden:
            assert f not in src, f"{mod.__name__} imports {f}"


def test_generators_are_dto_only():
    """All generators accept DTOs and validate without errors."""
    tournament = make_tournament()
    teams = make_teams(4)

    cases = [
        (SingleEliminationGenerator(), make_stage(type="single_elim")),
        (DoubleEliminationGenerator(), make_stage(type="double_elim")),
        (RoundRobinGenerator(), make_stage(type="round_robin")),
        (SwissSystemGenerator(), make_stage(type="swiss", metadata={"rounds_count": 3})),
    ]
    for gen, stg in cases:
        ok, errs = gen.validate_configuration(tournament, stg, len(teams))
        assert ok, f"{gen.__class__.__name__}: {errs}"


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

def test_calculate_bye_count():
    assert calculate_bye_count(2) == 0
    assert calculate_bye_count(3) == 1
    assert calculate_bye_count(4) == 0
    assert calculate_bye_count(5) == 3
    assert calculate_bye_count(6) == 2
    assert calculate_bye_count(7) == 1
    assert calculate_bye_count(8) == 0
    assert calculate_bye_count(9) == 7


def test_next_power_of_two():
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
    """Top seeds get byes; result length = next power of two."""
    teams = make_teams(6)
    seeded = seed_participants_with_byes(teams, 2)

    assert len(seeded) == 8
    assert seeded[0] is None  # bye
    assert seeded[1] is None  # bye
    assert seeded[2].id == 1
    assert seeded[3].id == 2


def test_generate_round_robin_pairings():
    """generate_round_robin_pairings(N) → list of (idx, idx) tuples."""
    pairings = generate_round_robin_pairings(4)

    assert len(pairings) == 6  # C(4,2)
    unique = set()
    for a, b in pairings:
        assert a != b, "Self-match"
        unique.add(tuple(sorted([a, b])))
    assert len(unique) == 6


# ============================================================================
# SINGLE ELIMINATION
# ============================================================================

def test_single_elimination_2_teams():
    gen = SingleEliminationGenerator()
    matches = gen.generate_bracket(make_tournament(), make_stage(), make_teams(2))

    assert len(matches) == 1
    assert matches[0].round_number == 1
    assert matches[0].team_a_id == 1
    assert matches[0].team_b_id == 2


def test_single_elimination_4_teams():
    """4 teams: only Round 1 has assigned teams → later rounds skipped."""
    gen = SingleEliminationGenerator()
    matches = gen.generate_bracket(make_tournament(), make_stage(), make_teams(4))

    assert len(matches) == 2  # Round 1 only (Round 2 is all-TBD)
    assert all(m.round_number == 1 for m in matches)


def test_single_elimination_6_teams_with_byes():
    """6 teams → 8 slots (2 byes). One pair is (None,None) → skipped."""
    gen = SingleEliminationGenerator()
    matches = gen.generate_bracket(make_tournament(), make_stage(), make_teams(6))

    assert len(matches) == 3  # 3 real first-round matches


def test_single_elimination_third_place_match():
    gen = SingleEliminationGenerator()
    stage = make_stage(third_place_match=True)
    matches = gen.generate_bracket(make_tournament(), stage, make_teams(4))

    # 2 semifinals + 1 third-place (finals round TBD → skipped)
    assert len(matches) == 3
    tp = [m for m in matches if m.stage == "Third Place"]
    assert len(tp) == 1


def test_single_elimination_validation():
    gen = SingleEliminationGenerator()
    t, s = make_tournament(), make_stage()

    ok, errs = gen.validate_configuration(t, s, 1)
    assert not ok and any("2" in e for e in errs)

    ok, errs = gen.validate_configuration(t, s, 300)
    assert not ok and any("256" in e for e in errs)


# ============================================================================
# DOUBLE ELIMINATION
# ============================================================================

def test_double_elimination_4_teams():
    gen = DoubleEliminationGenerator()
    matches = gen.generate_bracket(
        make_tournament(), make_stage(type="double_elim"), make_teams(4)
    )

    assert len(matches) == 5
    assert len([m for m in matches if m.stage_type == "winners"]) == 2
    assert len([m for m in matches if m.stage_type == "losers"]) == 1
    assert len([m for m in matches if m.stage_type == "grand_finals"]) == 1
    assert len([m for m in matches if m.stage_type == "grand_finals_reset"]) == 1


def test_double_elimination_8_teams():
    gen = DoubleEliminationGenerator()
    matches = gen.generate_bracket(
        make_tournament(), make_stage(type="double_elim"), make_teams(8)
    )

    assert len(matches) == 10
    assert len([m for m in matches if m.stage_type == "winners"]) == 4
    assert len([m for m in matches if m.stage_type == "losers"]) == 4


def test_double_elimination_grand_finals_reset():
    gen = DoubleEliminationGenerator()
    stage = make_stage(type="double_elim", metadata={"grand_finals_reset": True})
    matches = gen.generate_bracket(make_tournament(), stage, make_teams(4))

    gf = [m for m in matches if m.stage_type and "grand_finals" in m.stage_type]
    assert len(gf) == 2
    assert {m.stage_type for m in gf} == {"grand_finals", "grand_finals_reset"}


def test_double_elimination_no_reset():
    gen = DoubleEliminationGenerator()
    stage = make_stage(type="double_elim", metadata={"grand_finals_reset": False})
    matches = gen.generate_bracket(make_tournament(), stage, make_teams(4))

    gf = [m for m in matches if m.stage_type and "grand_finals" in m.stage_type]
    assert len(gf) == 1
    assert gf[0].stage_type == "grand_finals"


def test_double_elimination_validation():
    gen = DoubleEliminationGenerator()
    t, s = make_tournament(), make_stage(type="double_elim")

    ok, errs = gen.validate_configuration(t, s, 3)
    assert not ok and any("4" in e for e in errs)

    ok, errs = gen.validate_configuration(t, s, 130)
    assert not ok and any("128" in e for e in errs)


# ============================================================================
# ROUND ROBIN
# ============================================================================

def test_round_robin_4_teams():
    gen = RoundRobinGenerator()
    matches = gen.generate_bracket(
        make_tournament(), make_stage(type="round_robin"), make_teams(4)
    )

    assert len(matches) == 6
    pairs = set()
    for m in matches:
        pair = tuple(sorted([m.team_a_id, m.team_b_id]))
        assert pair not in pairs
        pairs.add(pair)
    assert len(set(m.round_number for m in matches)) == 3


def test_round_robin_no_self_matches():
    gen = RoundRobinGenerator()
    matches = gen.generate_bracket(
        make_tournament(), make_stage(type="round_robin"), make_teams(6)
    )
    for m in matches:
        assert m.team_a_id != m.team_b_id


def test_round_robin_unique_pairings():
    gen = RoundRobinGenerator()
    matches = gen.generate_bracket(
        make_tournament(), make_stage(type="round_robin"), make_teams(5)
    )
    assert len(matches) == 10

    opp = {i: set() for i in range(1, 6)}
    for m in matches:
        opp[m.team_a_id].add(m.team_b_id)
        opp[m.team_b_id].add(m.team_a_id)
    for tid, os_ in opp.items():
        assert len(os_) == 4
        assert tid not in os_


def test_round_robin_validation():
    gen = RoundRobinGenerator()
    t, s = make_tournament(), make_stage(type="round_robin")

    ok, errs = gen.validate_configuration(t, s, 2)
    assert not ok and any("3" in e for e in errs)

    ok, errs = gen.validate_configuration(t, s, 25)
    assert not ok and any("20" in e for e in errs)


# ============================================================================
# SWISS SYSTEM
# ============================================================================

def test_swiss_first_round_pairing():
    gen = SwissSystemGenerator()
    stage = make_stage(type="swiss", metadata={"rounds_count": 3})
    matches = gen.generate_bracket(make_tournament(), stage, make_teams(8))

    r1 = [m for m in matches if m.round_number == 1]
    assert len(r1) == 4
    pairings = {(m.team_a_id, m.team_b_id) for m in r1}
    assert pairings == {(1, 5), (2, 6), (3, 7), (4, 8)}


def test_swiss_subsequent_rounds_stub():
    gen = SwissSystemGenerator()
    stage = make_stage(type="swiss", metadata={"rounds_count": 3})
    matches = gen.generate_bracket(make_tournament(), stage, make_teams(8))
    assert len(matches) >= 4


def test_swiss_validation():
    gen = SwissSystemGenerator()
    t = make_tournament()

    # Missing rounds_count
    ok, errs = gen.validate_configuration(t, make_stage(type="swiss"), 8)
    assert not ok and any("rounds_count" in e for e in errs)

    # Too few participants
    ok, errs = gen.validate_configuration(
        t, make_stage(type="swiss", metadata={"rounds_count": 3}), 2
    )
    assert not ok and any("4" in e for e in errs)


# ============================================================================
# BRACKET ENGINE SERVICE
# ============================================================================

def test_bracket_engine_format_selection():
    engine = BracketEngineService()
    matches = engine.generate_bracket_for_stage(
        make_tournament(), make_stage(type="single_elim"), make_teams(2)
    )
    assert len(matches) == 1


def test_bracket_engine_stage_type_override():
    engine = BracketEngineService()
    matches = engine.generate_bracket_for_stage(
        make_tournament(), make_stage(type="double_elim"), make_teams(4)
    )
    assert len(matches) == 5


def test_bracket_engine_long_format_aliases():
    """Long format names like 'single_elimination' also resolve."""
    engine = BracketEngineService()
    matches = engine.generate_bracket_for_stage(
        make_tournament(), make_stage(type="single_elimination"), make_teams(2)
    )
    assert len(matches) == 1


def test_bracket_engine_unknown_format():
    engine = BracketEngineService()
    with pytest.raises((ValueError, KeyError)):
        engine.generate_bracket_for_stage(
            make_tournament(), make_stage(type="unknown_format"), make_teams(4)
        )


def test_bracket_engine_extensibility():
    class CustomGen:
        def generate_bracket(self, tournament, stage, participants):
            return [MatchDTO(
                tournament_id=tournament.id, round_number=1,
                team_a_id=participants[0].id, team_b_id=participants[1].id,
                stage_type="custom",
            )]

        def validate_configuration(self, tournament, stage, participant_count):
            return (participant_count >= 2, [] if participant_count >= 2 else ["Need >= 2"])

        def supports_third_place_match(self):
            return False

    engine = BracketEngineService()
    engine.register_generator("custom_format", CustomGen())
    matches = engine.generate_bracket_for_stage(
        make_tournament(), make_stage(type="custom_format"), make_teams(4)
    )
    assert len(matches) == 1
    assert matches[0].stage_type == "custom"


def test_bracket_engine_validation_delegation():
    engine = BracketEngineService()
    with pytest.raises(ValueError, match="Invalid bracket configuration"):
        engine.generate_bracket_for_stage(
            make_tournament(), make_stage(type="single_elim"), make_teams(1)
        )
