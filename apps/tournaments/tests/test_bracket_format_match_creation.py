"""
Phase 3 — Bracket format Match creation tests.

Acceptance criteria (per format):

Single Elimination
  * N players → floor(N/2) non-bye Round 1 Match rows, correct states.
  * BracketNodes for later rounds have no Match linked (TBD, waiting for winners).
  * TOC TOCBracketsService.generate_bracket() produces the same result.

Double Elimination
  * N players → winner-bracket Round 1 (non-bye) Match rows only.
  * Loser-bracket nodes have NO participants and NO Match at generation time
    (they receive participants as WB results propagate).
  * Grand Final / reset node have no Match.
  * TOC routing produces the same result.

Swiss
  * Even N → N/2 Round 1 Match rows, 0 byes.
  * Odd N  → floor(N/2) Round 1 Match rows + exactly 1 bye node.
  * Bye node (is_bye=True) has no Match linked.
  * All created Match rows are in SCHEDULED state.
  * TOC routing produces the same result.

Cross-format
  * After any bracket-format generation, Match.objects.filter(tournament=t,
    bracket__isnull=False) is non-empty — the "No Matches Yet" screen is gone.
"""

import math
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tournaments.models import Tournament, Registration, Match
from apps.brackets.models import Bracket, BracketNode
from apps.tournaments.services.format_strategy import (
    SingleEliminationStrategy,
    DoubleEliminationStrategy,
    SwissStrategy,
    get_strategy,
)

User = get_user_model()


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def game(db):
    from apps.tournaments.models import Game
    return Game.objects.create(
        name="Phase3 Test Game",
        slug="phase3-test-game",
        is_active=True,
    )


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username="p3_organizer",
        email="p3_org@test.com",
        password="pass123",
    )


def _make_tournament(db, game, organizer, fmt, n):
    """Create a tournament + n confirmed solo registrations."""
    t = Tournament.objects.create(
        name=f"P3 {fmt} {n}p",
        slug=f"p3-{fmt.replace('_', '-')}-{n}p-{id(db)}",
        description="Phase 3 test",
        game=game,
        organizer=organizer,
        format=fmt,
        participation_type=Tournament.SOLO,
        min_participants=2,
        max_participants=n + 4,
        status=Tournament.REGISTRATION_CLOSED,
        registration_start=timezone.now() - timezone.timedelta(days=5),
        registration_end=timezone.now() - timezone.timedelta(days=1),
        tournament_start=timezone.now() + timezone.timedelta(days=2),
    )
    for i in range(n):
        u = User.objects.create_user(
            username=f"p3_{fmt[:2]}_{n}p_u{i}_{id(t)}",
            email=f"p3_{i}_{id(t)}@t.com",
            password="x",
        )
        Registration.objects.create(tournament=t, user=u, status=Registration.CONFIRMED)
    return t


# ─── Single Elimination ────────────────────────────────────────────────────────

class TestSingleElimination:

    @pytest.mark.django_db
    def test_4_players_creates_2_round1_matches(self, game, organizer):
        """4 players → 2 WB-R1 Match rows (no byes)."""
        t = _make_tournament(None, game, organizer, Tournament.SINGLE_ELIM, 4)
        strategy = SingleEliminationStrategy()

        result = strategy.generate_fixtures(t, {})

        matches = Match.objects.filter(tournament=t, bracket__isnull=False, is_deleted=False)
        assert matches.count() == 2, f"Expected 2, got {matches.count()}"
        assert result["matches_created"] == 2
        assert result["byes"] == 0

    @pytest.mark.django_db
    def test_8_players_creates_4_round1_matches(self, game, organizer):
        """8 players → 4 Round 1 matches (no byes in power-of-2)."""
        t = _make_tournament(None, game, organizer, Tournament.SINGLE_ELIM, 8)
        result = SingleEliminationStrategy().generate_fixtures(t, {})

        matches = Match.objects.filter(tournament=t, bracket__isnull=False, is_deleted=False)
        assert matches.count() == 4
        assert result["matches_created"] == 4
        assert result["byes"] == 0

    @pytest.mark.django_db
    def test_3_players_bye_creates_1_match(self, game, organizer):
        """
        3 players: bracket size = 4.
        Round 1: 2 nodes — one real match, one bye.
        Created Match rows = 1 (bye node excluded).
        """
        t = _make_tournament(None, game, organizer, Tournament.SINGLE_ELIM, 3)
        result = SingleEliminationStrategy().generate_fixtures(t, {})

        matches = Match.objects.filter(tournament=t, bracket__isnull=False, is_deleted=False)
        assert matches.count() == 1
        assert result["matches_created"] == 1
        assert result["byes"] == 1

    @pytest.mark.django_db
    def test_all_matches_are_scheduled(self, game, organizer):
        """Newly created Match rows must start in SCHEDULED state."""
        t = _make_tournament(None, game, organizer, Tournament.SINGLE_ELIM, 4)
        SingleEliminationStrategy().generate_fixtures(t, {})

        non_scheduled = Match.objects.filter(
            tournament=t, bracket__isnull=False, is_deleted=False
        ).exclude(state=Match.SCHEDULED)
        assert non_scheduled.count() == 0

    @pytest.mark.django_db
    def test_later_round_nodes_have_no_match(self, game, organizer):
        """
        Round 2+ nodes are TBD (waiting for winners) and must have no
        linked Match immediately after generation.
        """
        t = _make_tournament(None, game, organizer, Tournament.SINGLE_ELIM, 4)
        SingleEliminationStrategy().generate_fixtures(t, {})

        bracket = Bracket.objects.get(tournament=t)
        later_nodes_with_match = BracketNode.objects.filter(
            bracket=bracket,
            round_number__gt=1,
            match__isnull=False,
        )
        assert later_nodes_with_match.count() == 0, (
            f"Round 2+ nodes should have no match yet, "
            f"but {later_nodes_with_match.count()} do."
        )

    @pytest.mark.django_db
    def test_toc_routes_to_strategy_and_creates_matches(self, game, organizer):
        """TOCBracketsService.generate_bracket() must produce Match rows for SE."""
        from apps.tournaments.api.toc.brackets_service import TOCBracketsService

        t = _make_tournament(None, game, organizer, Tournament.SINGLE_ELIM, 4)
        TOCBracketsService.generate_bracket(t, organizer)

        matches = Match.objects.filter(tournament=t, bracket__isnull=False, is_deleted=False)
        assert matches.count() == 2, (
            "TOC SE generation must create Match rows immediately. "
            f"Got {matches.count()}."
        )


# ─── Double Elimination ────────────────────────────────────────────────────────

class TestDoubleElimination:

    @pytest.mark.django_db
    def test_4_players_creates_wb_r1_matches(self, game, organizer):
        """
        4-player DE: WB size=4, WB-R1 has 2 matches.
        LB nodes are empty at generation (no participants).
        """
        t = _make_tournament(None, game, organizer, Tournament.DOUBLE_ELIM, 4)
        result = DoubleEliminationStrategy().generate_fixtures(t, {})

        matches = Match.objects.filter(tournament=t, bracket__isnull=False, is_deleted=False)
        assert matches.count() == 2, (
            f"Expected 2 WB-R1 matches, got {matches.count()}"
        )
        assert result["matches_created"] == 2

    @pytest.mark.django_db
    def test_lb_nodes_have_no_match_at_generation(self, game, organizer):
        """
        LB nodes are populated when WB results propagate.
        At generation time all LB nodes must have no Match linked.
        """
        t = _make_tournament(None, game, organizer, Tournament.DOUBLE_ELIM, 4)
        DoubleEliminationStrategy().generate_fixtures(t, {})

        bracket = Bracket.objects.get(tournament=t)
        lb_with_match = BracketNode.objects.filter(
            bracket=bracket,
            bracket_type=BracketNode.LOSERS,
            match__isnull=False,
        )
        assert lb_with_match.count() == 0, (
            f"LB nodes must have no match at generation; "
            f"{lb_with_match.count()} have one."
        )

    @pytest.mark.django_db
    def test_lb_nodes_have_no_participants_at_generation(self, game, organizer):
        """LB Round 1+ nodes must have no participants assigned at generation."""
        t = _make_tournament(None, game, organizer, Tournament.DOUBLE_ELIM, 4)
        DoubleEliminationStrategy().generate_fixtures(t, {})

        bracket = Bracket.objects.get(tournament=t)
        lb_with_participants = BracketNode.objects.filter(
            bracket=bracket,
            bracket_type=BracketNode.LOSERS,
        ).exclude(participant1_id__isnull=True)
        assert lb_with_participants.count() == 0, (
            f"LB nodes must have no participants; "
            f"{lb_with_participants.count()} do."
        )

    @pytest.mark.django_db
    def test_gf_node_has_no_match(self, game, organizer):
        """Grand Final and reset nodes must have no Match at generation time."""
        t = _make_tournament(None, game, organizer, Tournament.DOUBLE_ELIM, 4)
        DoubleEliminationStrategy().generate_fixtures(t, {})

        bracket = Bracket.objects.get(tournament=t)
        gf_with_match = BracketNode.objects.filter(
            bracket=bracket,
            bracket_type__in=[BracketNode.GRAND_FINAL, BracketNode.GRAND_FINAL_RESET],
            match__isnull=False,
        )
        assert gf_with_match.count() == 0

    @pytest.mark.django_db
    def test_8_players_creates_4_wb_r1_matches(self, game, organizer):
        """8 players → WB size=8 → 4 WB-R1 matches."""
        t = _make_tournament(None, game, organizer, Tournament.DOUBLE_ELIM, 8)
        result = DoubleEliminationStrategy().generate_fixtures(t, {})

        matches = Match.objects.filter(tournament=t, bracket__isnull=False, is_deleted=False)
        assert matches.count() == 4
        assert result["matches_created"] == 4
        assert result["lb_nodes_pending"] > 0

    @pytest.mark.django_db
    def test_toc_routes_to_strategy_and_creates_matches(self, game, organizer):
        """TOCBracketsService.generate_bracket() must produce WB-R1 Match rows for DE."""
        from apps.tournaments.api.toc.brackets_service import TOCBracketsService

        t = _make_tournament(None, game, organizer, Tournament.DOUBLE_ELIM, 4)
        TOCBracketsService.generate_bracket(t, organizer)

        matches = Match.objects.filter(tournament=t, bracket__isnull=False, is_deleted=False)
        assert matches.count() == 2, (
            "TOC DE generation must create WB-R1 Match rows immediately. "
            f"Got {matches.count()}."
        )


# ─── Swiss ─────────────────────────────────────────────────────────────────────

class TestSwiss:

    @pytest.mark.django_db
    def test_even_4_players_creates_2_matches_no_byes(self, game, organizer):
        """4 players (even) → 2 Round 1 matches, 0 byes."""
        t = _make_tournament(None, game, organizer, Tournament.SWISS, 4)
        result = SwissStrategy().generate_fixtures(t, {})

        matches = Match.objects.filter(tournament=t, bracket__isnull=False, is_deleted=False)
        assert matches.count() == 2
        assert result["matches_created"] == 2
        assert result["byes"] == 0

    @pytest.mark.django_db
    def test_odd_5_players_creates_2_matches_1_bye(self, game, organizer):
        """5 players (odd) → 2 Round 1 matches + 1 bye node, no Match for bye."""
        t = _make_tournament(None, game, organizer, Tournament.SWISS, 5)
        result = SwissStrategy().generate_fixtures(t, {})

        bracket = Bracket.objects.get(tournament=t)
        real_matches = Match.objects.filter(
            tournament=t, bracket__isnull=False, is_deleted=False
        )
        bye_nodes = BracketNode.objects.filter(
            bracket=bracket, is_bye=True, round_number=1
        )

        assert real_matches.count() == 2, (
            f"Expected 2 non-bye matches, got {real_matches.count()}"
        )
        assert bye_nodes.count() == 1, f"Expected 1 bye node, got {bye_nodes.count()}"
        assert result["matches_created"] == 2
        assert result["byes"] == 1

    @pytest.mark.django_db
    def test_bye_node_has_no_match(self, game, organizer):
        """The bye BracketNode must not have a Match linked to it."""
        t = _make_tournament(None, game, organizer, Tournament.SWISS, 5)
        SwissStrategy().generate_fixtures(t, {})

        bracket = Bracket.objects.get(tournament=t)
        bye_nodes_with_match = BracketNode.objects.filter(
            bracket=bracket, is_bye=True, round_number=1, match__isnull=False
        )
        assert bye_nodes_with_match.count() == 0, (
            "Bye nodes must have no Match linked — the bye player advances "
            "automatically without a match."
        )

    @pytest.mark.django_db
    def test_all_swiss_matches_are_scheduled(self, game, organizer):
        """All Round 1 Swiss matches must start in SCHEDULED state."""
        t = _make_tournament(None, game, organizer, Tournament.SWISS, 4)
        SwissStrategy().generate_fixtures(t, {})

        non_scheduled = Match.objects.filter(
            tournament=t, bracket__isnull=False, is_deleted=False
        ).exclude(state=Match.SCHEDULED)
        assert non_scheduled.count() == 0

    @pytest.mark.django_db
    def test_total_rounds_set_on_bracket(self, game, organizer):
        """
        Swiss bracket must record the configured total_rounds.
        Default = ceil(log2(n)) for n participants.
        """
        n = 8
        t = _make_tournament(None, game, organizer, Tournament.SWISS, n)
        result = SwissStrategy().generate_fixtures(t, {})

        bracket = Bracket.objects.get(tournament=t)
        expected_rounds = math.ceil(math.log2(n))
        assert bracket.total_rounds == expected_rounds, (
            f"Expected total_rounds={expected_rounds}, got {bracket.total_rounds}"
        )
        assert result["total_rounds"] == expected_rounds

    @pytest.mark.django_db
    def test_toc_routes_to_strategy_and_creates_matches(self, game, organizer):
        """TOCBracketsService.generate_bracket() must produce Round 1 Match rows for Swiss."""
        from apps.tournaments.api.toc.brackets_service import TOCBracketsService

        t = _make_tournament(None, game, organizer, Tournament.SWISS, 4)
        TOCBracketsService.generate_bracket(t, organizer)

        matches = Match.objects.filter(tournament=t, bracket__isnull=False, is_deleted=False)
        assert matches.count() == 2, (
            "TOC Swiss generation must create Round 1 Match rows immediately. "
            f"Got {matches.count()}."
        )


# ─── Cross-format: "No Matches Yet" screen eliminated ──────────────────────────

@pytest.mark.parametrize("fmt,n", [
    (Tournament.SINGLE_ELIM, 4),
    (Tournament.DOUBLE_ELIM, 4),
    (Tournament.SWISS, 4),
])
@pytest.mark.django_db
def test_all_formats_have_matches_after_generation(fmt, n, game, organizer):
    """
    After generation for any bracket format, at least one Match must exist.
    This is the direct fix for the 'No Matches Yet' TOC screen.
    """
    t = _make_tournament(None, game, organizer, fmt, n)
    get_strategy(fmt).generate_fixtures(t, {})

    matches = Match.objects.filter(
        tournament=t,
        bracket__isnull=False,
        is_deleted=False,
    )
    assert matches.count() > 0, (
        f"Format '{fmt}' with {n} players produced 0 Match rows after "
        f"generate_fixtures() — 'No Matches Yet' screen would still appear."
    )


@pytest.mark.parametrize("fmt,n", [
    (Tournament.SINGLE_ELIM, 4),
    (Tournament.DOUBLE_ELIM, 4),
    (Tournament.SWISS, 4),
])
@pytest.mark.django_db
def test_toc_generate_bracket_all_formats_produce_matches(fmt, n, game, organizer):
    """
    TOCBracketsService.generate_bracket() for all bracket formats must
    leave Match rows in the DB immediately after generation.
    """
    from apps.tournaments.api.toc.brackets_service import TOCBracketsService

    t = _make_tournament(None, game, organizer, fmt, n)
    TOCBracketsService.generate_bracket(t, organizer)

    matches = Match.objects.filter(
        tournament=t,
        bracket__isnull=False,
        is_deleted=False,
    )
    assert matches.count() > 0, (
        f"TOC generate_bracket for format '{fmt}' produced 0 Match rows."
    )


# ─── Participant name quality ──────────────────────────────────────────────────

@pytest.mark.parametrize("fmt,n", [
    (Tournament.SINGLE_ELIM, 4),
    (Tournament.DOUBLE_ELIM, 4),
    (Tournament.SWISS, 4),
])
@pytest.mark.django_db
def test_bracket_match_participant_names_not_tba(fmt, n, game, organizer):
    """
    Participant names in bracket Match rows must not be TBA / empty.
    Validates that seeding resolves real usernames, not placeholder text.
    """
    tba = {"tba", "tbd", "pending", "to be decided", "to be announced", ""}
    t = _make_tournament(None, game, organizer, fmt, n)
    get_strategy(fmt).generate_fixtures(t, {})

    for match in Match.objects.filter(tournament=t, bracket__isnull=False, is_deleted=False):
        p1 = (match.participant1_name or "").strip().lower()
        p2 = (match.participant2_name or "").strip().lower()
        assert p1 not in tba, (
            f"Match {match.id} [{fmt}] participant1_name is TBA: '{match.participant1_name}'"
        )
        assert p2 not in tba, (
            f"Match {match.id} [{fmt}] participant2_name is TBA: '{match.participant2_name}'"
        )
