"""
P0 Tests — Tournament Engine Group Playoff Knockout Transition.

Verifies the three P0 fixes from TOURNAMENT_ENGINE_RECOVERY_PLAN.md:

P0-1: Knockout Match records have bracket FK set (not NULL).
P0-2: Knockout Match records have a non-NULL scheduled_time.
P0-3: transition_to_knockout_stage() acquires a row lock (select_for_update).

Tests are split into two categories:
- Mock-based (run anywhere, no DB needed via smoke settings)
- DB-based (marked ``integration``, require PostgreSQL via settings_test)
"""

from __future__ import annotations

import inspect
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock, PropertyMock, call

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone


# ---------------------------------------------------------------------------
# P0-3 Source Inspection (no DB required)
# ---------------------------------------------------------------------------

class TestP0_3_SourceInspection:
    """Verify transition_to_knockout_stage source code contains select_for_update."""

    def test_transition_uses_select_for_update(self):
        from apps.tournaments.services.tournament_service import TournamentService
        source = inspect.getsource(TournamentService.transition_to_knockout_stage)
        assert "select_for_update()" in source, (
            "transition_to_knockout_stage must call select_for_update() "
            "on the Tournament queryset"
        )

    def test_transition_is_atomic(self):
        from apps.tournaments.services.tournament_service import TournamentService
        source = inspect.getsource(TournamentService.transition_to_knockout_stage)
        assert "transaction.atomic" in source, (
            "transition_to_knockout_stage must be wrapped in transaction.atomic"
        )


# ---------------------------------------------------------------------------
# P0-1 Source Inspection (no DB required)
# ---------------------------------------------------------------------------

class TestP0_1_SourceInspection:
    """Verify create_matches_from_bracket passes bracket= to Match.objects.create."""

    def test_create_matches_sets_bracket(self):
        from apps.tournaments.services.bracket_service import BracketService
        source = inspect.getsource(BracketService.create_matches_from_bracket)
        assert "bracket=bracket" in source, (
            "create_matches_from_bracket must pass bracket=bracket to Match.objects.create"
        )

    def test_create_matches_sets_scheduled_time(self):
        from apps.tournaments.services.bracket_service import BracketService
        source = inspect.getsource(BracketService.create_matches_from_bracket)
        assert "scheduled_time=" in source, (
            "create_matches_from_bracket must pass scheduled_time= to Match.objects.create"
        )


# ---------------------------------------------------------------------------
# P0-1 Mock-based: bracket FK on knockout matches
# ---------------------------------------------------------------------------

class TestP0_1_BracketFKMock:
    """Verify create_matches_from_bracket calls Match.objects.create with bracket=bracket."""

    @staticmethod
    def _get_unwrapped():
        """Get create_matches_from_bracket without @transaction.atomic wrapper."""
        from apps.tournaments.services.bracket_service import BracketService
        fn = BracketService.create_matches_from_bracket
        return getattr(fn, '__wrapped__', fn)

    @staticmethod
    def _mock_qs(items):
        """Return a MagicMock that behaves like a QuerySet (iterable + .count())."""
        qs = MagicMock()
        qs.__iter__ = MagicMock(return_value=iter(items))
        qs.count.return_value = len(items)
        return qs

    @patch("apps.tournaments.services.bracket_service.BracketNode.objects")
    @patch("apps.tournaments.services.bracket_service.Match.objects")
    def test_match_create_receives_bracket_kwarg(self, mock_match_mgr, mock_node_mgr):
        # Setup mock bracket
        bracket = MagicMock()
        bracket.id = 42
        bracket.tournament.config = {}
        bracket.tournament.tournament_start = timezone.now()

        # Mock node
        node = MagicMock()
        node.round_number = 1
        node.match_number_in_round = 1
        node.participant1_id = 10
        node.participant2_id = 20

        # BracketNode.objects.filter(...).exclude(...) returns queryset-like [node]
        mock_node_mgr.filter.return_value.exclude.return_value = self._mock_qs([node])
        mock_node_mgr.filter.return_value.count.return_value = 1

        mock_match = MagicMock()
        mock_match.id = 99
        mock_match_mgr.create.return_value = mock_match

        self._get_unwrapped()(bracket)

        # Verify bracket= was passed
        create_kwargs = mock_match_mgr.create.call_args
        assert create_kwargs.kwargs.get("bracket") is bracket or \
            create_kwargs[1].get("bracket") is bracket, \
            f"Match.objects.create was not called with bracket=bracket. Got: {create_kwargs}"

    @patch("apps.tournaments.services.bracket_service.BracketNode.objects")
    @patch("apps.tournaments.services.bracket_service.Match.objects")
    def test_match_create_receives_scheduled_time(self, mock_match_mgr, mock_node_mgr):
        bracket = MagicMock()
        bracket.id = 42
        bracket.tournament.config = {}
        bracket.tournament.tournament_start = timezone.now() + timedelta(hours=5)

        node = MagicMock()
        node.round_number = 1
        node.match_number_in_round = 1
        node.participant1_id = 10
        node.participant2_id = 20

        mock_node_mgr.filter.return_value.exclude.return_value = self._mock_qs([node])
        mock_node_mgr.filter.return_value.count.return_value = 1
        mock_match_mgr.create.return_value = MagicMock(id=99)

        self._get_unwrapped()(bracket)

        create_kwargs = mock_match_mgr.create.call_args
        scheduled = create_kwargs.kwargs.get("scheduled_time") or create_kwargs[1].get("scheduled_time")
        assert scheduled is not None, (
            "Match.objects.create must receive a non-None scheduled_time"
        )

    @patch("apps.tournaments.services.bracket_service.BracketNode.objects")
    @patch("apps.tournaments.services.bracket_service.Match.objects")
    def test_scheduled_time_uses_tournament_start_fallback(self, mock_match_mgr, mock_node_mgr):
        expected_start = timezone.now() + timedelta(hours=3)
        bracket = MagicMock()
        bracket.id = 1
        bracket.tournament.config = {}  # No knockout_config
        bracket.tournament.tournament_start = expected_start

        node = MagicMock()
        node.round_number = 1
        node.match_number_in_round = 1
        node.participant1_id = 1
        node.participant2_id = 2

        mock_node_mgr.filter.return_value.exclude.return_value = self._mock_qs([node])
        mock_node_mgr.filter.return_value.count.return_value = 1
        mock_match_mgr.create.return_value = MagicMock(id=1)

        self._get_unwrapped()(bracket)

        create_kwargs = mock_match_mgr.create.call_args
        scheduled = create_kwargs.kwargs.get("scheduled_time") or create_kwargs[1].get("scheduled_time")
        assert scheduled == expected_start

    @patch("apps.tournaments.services.bracket_service.BracketNode.objects")
    @patch("apps.tournaments.services.bracket_service.Match.objects")
    def test_scheduled_time_prefers_knockout_config(self, mock_match_mgr, mock_node_mgr):
        ko_start = timezone.now() + timedelta(days=3)
        bracket = MagicMock()
        bracket.id = 1
        bracket.tournament.config = {
            "knockout_config": {"start_time": ko_start.isoformat()}
        }
        bracket.tournament.tournament_start = timezone.now()

        node = MagicMock()
        node.round_number = 1
        node.match_number_in_round = 1
        node.participant1_id = 1
        node.participant2_id = 2

        mock_node_mgr.filter.return_value.exclude.return_value = self._mock_qs([node])
        mock_node_mgr.filter.return_value.count.return_value = 1
        mock_match_mgr.create.return_value = MagicMock(id=1)

        self._get_unwrapped()(bracket)

        create_kwargs = mock_match_mgr.create.call_args
        scheduled = create_kwargs.kwargs.get("scheduled_time") or create_kwargs[1].get("scheduled_time")
        delta = abs((scheduled - ko_start).total_seconds())
        assert delta < 1, f"Expected knockout config start_time, got delta={delta}s"

    @patch("apps.tournaments.services.bracket_service.BracketNode.objects")
    @patch("apps.tournaments.services.bracket_service.Match.objects")
    def test_multiple_nodes_all_get_bracket_and_time(self, mock_match_mgr, mock_node_mgr):
        """All nodes in a multi-match bracket get bracket= and scheduled_time=."""
        bracket = MagicMock()
        bracket.id = 7
        bracket.tournament.config = {}
        bracket.tournament.tournament_start = timezone.now()

        nodes = []
        for i in range(4):
            n = MagicMock()
            n.round_number = 1
            n.match_number_in_round = i + 1
            n.participant1_id = i * 2 + 1
            n.participant2_id = i * 2 + 2
            nodes.append(n)

        mock_node_mgr.filter.return_value.exclude.return_value = self._mock_qs(nodes)
        mock_node_mgr.filter.return_value.count.return_value = 8

        call_count = 0
        def create_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(id=call_count)
        mock_match_mgr.create.side_effect = create_side_effect

        result = self._get_unwrapped()(bracket)
        assert len(result) == 4

        for c in mock_match_mgr.create.call_args_list:
            assert c.kwargs.get("bracket") is bracket
            assert c.kwargs.get("scheduled_time") is not None


# ---------------------------------------------------------------------------
# P0-3 Mock-based: transition idempotency
# ---------------------------------------------------------------------------

class TestP0_3_TransitionIdempotencyMock:
    """Verify transition guards via source inspection (DB tests in integration suite)."""

    def test_transition_has_format_guard(self):
        """transition_to_knockout_stage must check tournament.format == GROUP_PLAYOFF."""
        from apps.tournaments.services.tournament_service import TournamentService
        source = inspect.getsource(TournamentService.transition_to_knockout_stage)
        assert "GROUP_PLAYOFF" in source

    def test_transition_has_existing_bracket_check(self):
        """transition_to_knockout_stage must check for existing bracket with matches."""
        from apps.tournaments.services.tournament_service import TournamentService
        source = inspect.getsource(TournamentService.transition_to_knockout_stage)
        assert "knockout_match_count" in source or "already in knockout" in source


# ---------------------------------------------------------------------------
# Integration tests (require PostgreSQL — mark for selective running)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
class TestGroupPlayoffTransitionIntegration:
    """
    End-to-end DB tests. Require PostgreSQL (settings_test).
    Run with: pytest -m integration tests/test_p0_knockout_transition.py
    """

    @pytest.fixture
    def game(self, db):
        from apps.games.models.game import Game
        return Game.objects.create(
            name="P0 Integration Game",
            slug="p0-integration-game",
            is_active=True,
        )

    @pytest.fixture
    def organizer(self, db):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.create_user(
            username="p0-int-org",
            email="p0-int-org@test.com",
            password="pass123",
        )

    @pytest.fixture
    def players(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return [
            User.objects.create_user(
                username=f"p0-int-{i}",
                email=f"p0-int-{i}@test.com",
                password="pass123",
            )
            for i in range(1, 17)
        ]

    @pytest.fixture
    def gp_tournament(self, db, game, organizer):
        from apps.tournaments.models import Tournament
        now = timezone.now()
        return Tournament.objects.create(
            name="P0 Integration GP",
            slug="p0-integration-gp",
            organizer=organizer,
            game=game,
            format=Tournament.GROUP_PLAYOFF,
            participation_type=Tournament.SOLO,
            max_participants=16,
            min_participants=4,
            registration_start=now - timedelta(days=2),
            registration_end=now - timedelta(hours=6),
            tournament_start=now + timedelta(hours=1),
            tournament_end=now + timedelta(days=2),
            status=Tournament.LIVE,
        )

    @pytest.fixture
    def full_group_stage(self, db, gp_tournament, players):
        """Set up 4 groups, standings, registrations, and completed group matches."""
        from apps.tournaments.models import Match, Registration, Tournament
        from apps.tournaments.models.group import Group, GroupStanding, GroupStage

        for p in players:
            Registration.objects.create(
                tournament=gp_tournament, user=p,
                status=Registration.CONFIRMED, registration_data={},
            )

        group_stage = GroupStage.objects.create(
            tournament=gp_tournament, name="Group Stage",
            groups_count=4, advancement_count=2,
        )

        groups = []
        for gi, label in enumerate("ABCD"):
            grp = Group.objects.create(
                tournament=gp_tournament, name=f"Group {label}",
                display_order=gi, max_participants=4, advancement_count=2,
            )
            grp_players = players[gi * 4: (gi + 1) * 4]
            for rank_idx, p in enumerate(grp_players):
                GroupStanding.objects.create(
                    group=grp, user=p, rank=rank_idx + 1,
                    matches_played=3,
                    matches_won=3 - rank_idx if rank_idx < 3 else 0,
                    matches_lost=rank_idx if rank_idx < 3 else 3,
                    points=Decimal(str((3 - rank_idx) * 3)) if rank_idx < 3 else Decimal("0"),
                )

            match_num = 0
            for i in range(4):
                for j in range(i + 1, 4):
                    match_num += 1
                    p1, p2 = grp_players[i], grp_players[j]
                    Match.objects.create(
                        tournament=gp_tournament,
                        round_number=1,
                        match_number=gi * 6 + match_num,
                        participant1_id=p1.id,
                        participant1_name=p1.username,
                        participant2_id=p2.id,
                        participant2_name=p2.username,
                        state=Match.COMPLETED,
                        winner_id=p1.id,
                        loser_id=p2.id,
                        participant1_score=2,
                        participant2_score=0,
                        completed_at=timezone.now(),
                        scheduled_time=timezone.now() - timedelta(hours=1),
                        lobby_info={"group_id": grp.id, "group_name": grp.name},
                    )
            groups.append(grp)
        return groups, group_stage

    def test_full_transition_bracket_fk_and_time(self, gp_tournament, full_group_stage):
        """After transition, knockout matches have bracket FK and scheduled_time."""
        from apps.tournaments.models import Match
        from apps.tournaments.services.tournament_service import TournamentService

        bracket = TournamentService.transition_to_knockout_stage(gp_tournament.id)

        knockout = Match.objects.filter(tournament=gp_tournament, bracket=bracket)
        assert knockout.count() > 0
        for m in knockout:
            assert m.bracket_id == bracket.id
            assert m.scheduled_time is not None
            assert m.state == Match.SCHEDULED

    def test_stage_updated_after_transition(self, gp_tournament, full_group_stage):
        from apps.tournaments.models import Tournament
        from apps.tournaments.services.tournament_service import TournamentService

        TournamentService.transition_to_knockout_stage(gp_tournament.id)
        gp_tournament.refresh_from_db()
        assert gp_tournament.get_current_stage() == Tournament.STAGE_KNOCKOUT

    def test_second_transition_raises(self, gp_tournament, full_group_stage):
        from apps.tournaments.services.tournament_service import TournamentService

        TournamentService.transition_to_knockout_stage(gp_tournament.id)
        with pytest.raises(ValidationError, match="already in knockout"):
            TournamentService.transition_to_knockout_stage(gp_tournament.id)

    def test_knockout_visible_in_all_query_patterns(self, gp_tournament, full_group_stage):
        """Verify knockout matches appear in all view query patterns."""
        from apps.tournaments.models import Match
        from apps.tournaments.services.tournament_service import TournamentService

        bracket = TournamentService.transition_to_knockout_stage(gp_tournament.id)

        # TOC knockout filter
        assert Match.objects.filter(
            tournament=gp_tournament, bracket__isnull=False, is_deleted=False
        ).count() > 0

        # All matches have scheduled_time
        assert Match.objects.filter(
            tournament=gp_tournament, is_deleted=False, scheduled_time__isnull=True
        ).count() == 0

        # bracket= idempotency check
        assert Match.objects.filter(
            tournament=gp_tournament, bracket=bracket, is_deleted=False
        ).count() > 0

    def test_backfill_repairs_broken_matches(self, gp_tournament):
        """Simulate pre-fix data and verify backfill works."""
        from apps.brackets.models import Bracket, BracketNode
        from apps.tournaments.models import Match

        bracket = Bracket.objects.create(
            tournament=gp_tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=1, total_matches=1,
            seeding_method=Bracket.MANUAL,
        )
        # Pre-fix: match without bracket FK
        match = Match.objects.create(
            tournament=gp_tournament, round_number=1, match_number=1,
            participant1_id=1, participant2_id=2, state=Match.SCHEDULED,
        )
        BracketNode.objects.create(
            bracket=bracket, position=1, round_number=1,
            match_number_in_round=1, match=match,
            participant1_id=1, participant2_id=2,
        )
        assert match.bracket_id is None

        # Backfill
        for m in Match.objects.filter(bracket__isnull=True, bracket_node__isnull=False):
            m.bracket = m.bracket_node.bracket
            m.save(update_fields=["bracket"])

        match.refresh_from_db()
        assert match.bracket_id == bracket.id
