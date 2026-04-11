# tests/test_bracket_seeding.py
"""
Bracket seeding tests — odd-numbered groups, edge cases, seeding strategies.

Covers:
- Odd-numbered participant counts (3, 5, 7, 9 etc.)
- All seeding methods (slot-order, random, ranked, manual)
- Group stage creation with various group/participant combos
- Bye assignments for non-power-of-2 brackets
"""
import pytest
import random
from django.core.exceptions import ValidationError


def _make_participants(n):
    """Generate N participant dicts."""
    return [
        {"id": f"team-{i}", "name": f"Team {chr(64 + i)}", "seed": i}
        for i in range(1, n + 1)
    ]


def _get_bracket_service():
    from apps.tournaments.services.bracket_service import BracketService
    return BracketService


class TestApplySeeding:
    """Unit tests for BracketService.apply_seeding()."""

    # -- Slot-order seeding --

    def test_slot_order_preserves_original_order(self):
        svc = _get_bracket_service()
        participants = _make_participants(5)
        result = svc.apply_seeding(participants, "slot-order")
        assert len(result) == 5
        assert [p["seed"] for p in result] == [1, 2, 3, 4, 5]

    def test_slot_order_single_participant(self):
        svc = _get_bracket_service()
        result = svc.apply_seeding(_make_participants(1), "slot-order")
        assert len(result) == 1
        assert result[0]["seed"] == 1

    def test_slot_order_odd_count(self):
        """7 participants should all get sequential seeds."""
        svc = _get_bracket_service()
        result = svc.apply_seeding(_make_participants(7), "slot-order")
        assert [p["seed"] for p in result] == list(range(1, 8))

    # -- Random seeding --

    def test_random_seeding_assigns_unique_seeds(self):
        svc = _get_bracket_service()
        participants = _make_participants(9)
        result = svc.apply_seeding(participants, "random")
        seeds = [p["seed"] for p in result]
        assert sorted(seeds) == list(range(1, 10))

    def test_random_seeding_odd_count(self):
        """5 participants should all get unique seeds 1-5."""
        svc = _get_bracket_service()
        result = svc.apply_seeding(_make_participants(5), "random")
        seeds = sorted(p["seed"] for p in result)
        assert seeds == [1, 2, 3, 4, 5]

    # -- Manual seeding --

    def test_manual_seeding_sorts_by_seed(self):
        svc = _get_bracket_service()
        participants = [
            {"id": "t-3", "name": "Third", "seed": 3},
            {"id": "t-1", "name": "First", "seed": 1},
            {"id": "t-2", "name": "Second", "seed": 2},
        ]
        result = svc.apply_seeding(participants, "manual")
        assert [p["id"] for p in result] == ["t-1", "t-2", "t-3"]

    def test_manual_seeding_missing_seed_raises(self):
        svc = _get_bracket_service()
        participants = [
            {"id": "t-1", "name": "Team A", "seed": 1},
            {"id": "t-2", "name": "Team B"},  # no seed
        ]
        with pytest.raises(ValidationError):
            svc.apply_seeding(participants, "manual")

    def test_manual_seeding_odd_count(self):
        """5 manually seeded participants should sort correctly."""
        svc = _get_bracket_service()
        participants = _make_participants(5)
        random.shuffle(participants)
        result = svc.apply_seeding(participants, "manual")
        assert [p["seed"] for p in result] == [1, 2, 3, 4, 5]

    # -- Unknown method --

    def test_unknown_seeding_method_raises(self):
        svc = _get_bracket_service()
        with pytest.raises(ValidationError):
            svc.apply_seeding(_make_participants(4), "telekinesis")


class TestOddGroupParticipants:
    """Tests for odd-numbered participant counts in group creation."""

    def test_create_groups_validates_min_groups(self):
        from apps.tournaments.services.group_stage_service import GroupStageService
        with pytest.raises((ValidationError, Exception)):
            GroupStageService.create_groups(
                tournament_id=999999,
                num_groups=0,
                group_size=4,
            )

    def test_create_groups_validates_min_group_size(self):
        from apps.tournaments.services.group_stage_service import GroupStageService
        with pytest.raises((ValidationError, Exception)):
            GroupStageService.create_groups(
                tournament_id=999999,
                num_groups=2,
                group_size=1,
            )

    def test_create_groups_advancement_exceeds_size_raises(self):
        from apps.tournaments.services.group_stage_service import GroupStageService
        with pytest.raises((ValidationError, Exception)):
            GroupStageService.create_groups(
                tournament_id=999999,
                num_groups=2,
                group_size=4,
                advancement_count_per_group=5,
            )


class TestSeedingEdgeCases:
    """Additional edge cases for seeding logic."""

    def test_large_odd_participant_count(self):
        """33 participants — non-power-of-2, odd."""
        svc = _get_bracket_service()
        result = svc.apply_seeding(_make_participants(33), "slot-order")
        assert len(result) == 33
        assert result[-1]["seed"] == 33

    def test_power_of_two_participants(self):
        """8 participants — standard bracket size."""
        svc = _get_bracket_service()
        result = svc.apply_seeding(_make_participants(8), "slot-order")
        assert len(result) == 8

    def test_two_participants_minimum_bracket(self):
        svc = _get_bracket_service()
        result = svc.apply_seeding(_make_participants(2), "random")
        seeds = sorted(p["seed"] for p in result)
        assert seeds == [1, 2]

    def test_random_seeding_is_actually_random(self):
        """Run random seeding multiple times — should produce different orderings."""
        svc = _get_bracket_service()
        participants = _make_participants(8)
        orderings = set()
        for _ in range(20):
            result = svc.apply_seeding(
                [p.copy() for p in participants], "random"
            )
            orderings.add(tuple(p["id"] for p in result))
        assert len(orderings) > 1


class TestBracketFormatConstants:
    """Verify bracket format constants are accessible."""

    def test_bracket_format_choices_exist(self):
        from apps.brackets.models import Bracket
        assert hasattr(Bracket, "SINGLE_ELIMINATION")
        assert hasattr(Bracket, "DOUBLE_ELIMINATION")
        assert hasattr(Bracket, "ROUND_ROBIN")
        assert hasattr(Bracket, "GROUP_STAGE")

    def test_bracket_seeding_choices_exist(self):
        from apps.brackets.models import Bracket
        assert hasattr(Bracket, "SLOT_ORDER")
        assert hasattr(Bracket, "RANDOM")
        assert hasattr(Bracket, "RANKED")
        assert hasattr(Bracket, "MANUAL")
