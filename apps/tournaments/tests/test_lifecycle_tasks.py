"""
Unit tests for tournament lifecycle Celery tasks.

Covers:
    - check_tournament_wrapup: terminal state list (forfeit included)
    - reconcile_group_playoff_transitions: detect and fix stuck GP tournaments

Pure mock-based — no database required.

These tasks do lazy imports inside their function bodies, so we patch
at the source module level.
"""

import logging
from unittest.mock import patch, MagicMock

import pytest


_TOURNAMENT_MODEL = "apps.tournaments.models.tournament.Tournament"
_MATCH_MODEL = "apps.tournaments.models.match.Match"
_BRACKET_MODEL = "apps.brackets.models.Bracket"
_LIFECYCLE_SVC = "apps.tournaments.services.lifecycle_service.TournamentLifecycleService"
_TOURNAMENT_SVC = "apps.tournaments.services.tournament_service.TournamentService"


# ── check_tournament_wrapup ──────────────────────────────────────────

class TestCheckTournamentWrapup:

    @patch(_LIFECYCLE_SVC)
    @patch(_MATCH_MODEL)
    @patch(_TOURNAMENT_MODEL)
    def test_all_forfeits_counts_as_terminal(self, MockTournament, MockMatch, MockService):
        """'forfeit' must be in the terminal list so all-forfeit tournaments complete."""
        from apps.tournaments.tasks.lifecycle import check_tournament_wrapup

        t = MagicMock(id=1, name="T1")
        MockTournament.LIVE = "live"
        MockTournament.COMPLETED = "completed"
        MockTournament.objects.filter.return_value.iterator.return_value = iter([t])

        # total=2, incomplete=0
        MockMatch.objects.filter.return_value.count.return_value = 2
        MockMatch.objects.filter.return_value.exclude.return_value.count.return_value = 0

        result = check_tournament_wrapup()
        MockService.transition.assert_called_once()
        assert result == {"completed": 1}

    @patch(_LIFECYCLE_SVC)
    @patch(_MATCH_MODEL)
    @patch(_TOURNAMENT_MODEL)
    def test_incomplete_matches_block_wrapup(self, MockTournament, MockMatch, MockService):
        from apps.tournaments.tasks.lifecycle import check_tournament_wrapup

        t = MagicMock(id=2, name="T2")
        MockTournament.LIVE = "live"
        MockTournament.COMPLETED = "completed"
        MockTournament.objects.filter.return_value.iterator.return_value = iter([t])

        MockMatch.objects.filter.return_value.count.return_value = 3
        MockMatch.objects.filter.return_value.exclude.return_value.count.return_value = 1

        result = check_tournament_wrapup()
        MockService.transition.assert_not_called()
        assert result == {"completed": 0}

    @patch(_LIFECYCLE_SVC)
    @patch(_MATCH_MODEL)
    @patch(_TOURNAMENT_MODEL)
    def test_zero_matches_skip_wrapup(self, MockTournament, MockMatch, MockService):
        from apps.tournaments.tasks.lifecycle import check_tournament_wrapup

        t = MagicMock(id=3, name="T3")
        MockTournament.LIVE = "live"
        MockTournament.COMPLETED = "completed"
        MockTournament.objects.filter.return_value.iterator.return_value = iter([t])

        MockMatch.objects.filter.return_value.count.return_value = 0

        result = check_tournament_wrapup()
        MockService.transition.assert_not_called()
        assert result == {"completed": 0}


# ── reconcile_group_playoff_transitions ──────────────────────────────

class TestReconcileGroupPlayoffTransitions:

    @patch(_TOURNAMENT_SVC)
    @patch(_MATCH_MODEL)
    @patch(_BRACKET_MODEL)
    @patch(_TOURNAMENT_MODEL)
    def test_stuck_tournament_gets_fixed(self, MockTournament, MockBracket, MockMatch, MockService):
        from apps.tournaments.tasks.lifecycle import reconcile_group_playoff_transitions

        t = MagicMock(id=10, name="Stuck GP")
        MockTournament.LIVE = "live"
        MockTournament.GROUP_PLAYOFF = "group_playoff"
        MockTournament.objects.filter.return_value.iterator.return_value = iter([t])

        # No bracket
        MockBracket.objects.filter.return_value.first.return_value = None

        # Group matches: exist, all terminal
        group_qs = MagicMock()
        group_qs.exists.return_value = True
        group_qs.exclude.return_value.count.return_value = 0
        MockMatch.objects.filter.return_value = group_qs

        result = reconcile_group_playoff_transitions()
        MockService.transition_to_knockout_stage.assert_called_once_with(t.id)
        assert result == {"fixed": 1}

    @patch(_TOURNAMENT_SVC)
    @patch(_MATCH_MODEL)
    @patch(_BRACKET_MODEL)
    @patch(_TOURNAMENT_MODEL)
    def test_incomplete_group_not_touched(self, MockTournament, MockBracket, MockMatch, MockService):
        from apps.tournaments.tasks.lifecycle import reconcile_group_playoff_transitions

        t = MagicMock(id=11, name="IncGP")
        MockTournament.LIVE = "live"
        MockTournament.GROUP_PLAYOFF = "group_playoff"
        MockTournament.objects.filter.return_value.iterator.return_value = iter([t])

        MockBracket.objects.filter.return_value.first.return_value = None
        group_qs = MagicMock()
        group_qs.exists.return_value = True
        group_qs.exclude.return_value.count.return_value = 2
        MockMatch.objects.filter.return_value = group_qs

        result = reconcile_group_playoff_transitions()
        MockService.transition_to_knockout_stage.assert_not_called()
        assert result == {"fixed": 0}

    @patch(_TOURNAMENT_SVC)
    @patch(_MATCH_MODEL)
    @patch(_BRACKET_MODEL)
    @patch(_TOURNAMENT_MODEL)
    def test_bracket_with_matches_skipped(self, MockTournament, MockBracket, MockMatch, MockService):
        from apps.tournaments.tasks.lifecycle import reconcile_group_playoff_transitions

        t = MagicMock(id=12, name="HasBracket")
        MockTournament.LIVE = "live"
        MockTournament.GROUP_PLAYOFF = "group_playoff"
        MockTournament.objects.filter.return_value.iterator.return_value = iter([t])

        bracket = MagicMock()
        MockBracket.objects.filter.return_value.first.return_value = bracket

        ko_qs = MagicMock()
        ko_qs.exists.return_value = True  # has matches
        MockMatch.objects.filter.return_value = ko_qs

        result = reconcile_group_playoff_transitions()
        MockService.transition_to_knockout_stage.assert_not_called()
        assert result == {"fixed": 0}

    @patch(_TOURNAMENT_SVC)
    @patch(_MATCH_MODEL)
    @patch(_BRACKET_MODEL)
    @patch(_TOURNAMENT_MODEL)
    def test_transition_failure_logged(self, MockTournament, MockBracket, MockMatch, MockService):
        from apps.tournaments.tasks.lifecycle import reconcile_group_playoff_transitions

        t = MagicMock(id=13, name="BoomGP")
        MockTournament.LIVE = "live"
        MockTournament.GROUP_PLAYOFF = "group_playoff"
        MockTournament.objects.filter.return_value.iterator.return_value = iter([t])

        MockBracket.objects.filter.return_value.first.return_value = None
        group_qs = MagicMock()
        group_qs.exists.return_value = True
        group_qs.exclude.return_value.count.return_value = 0
        MockMatch.objects.filter.return_value = group_qs

        MockService.transition_to_knockout_stage.side_effect = RuntimeError("fail")

        with patch.object(
            logging.getLogger("apps.tournaments.tasks.lifecycle"), "error"
        ) as mock_err:
            result = reconcile_group_playoff_transitions()
            mock_err.assert_called_once()

        assert result == {"fixed": 0}
