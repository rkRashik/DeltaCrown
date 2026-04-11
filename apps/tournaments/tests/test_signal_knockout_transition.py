"""
Unit tests for ``sync_match_completion_progression`` signal handler.

Covers:
    BUG-001  Signal swallows knockout errors   → now logs at ERROR with exc_info
    BUG-002  Filter mismatch for group matches  → uses bracket__isnull=True
    BUG-003  Bracket existence too coarse        → checks bracket + matches

Pure mock-based — no database required.

Patch strategy:
  - ``Match`` is a module-level import in signals.py → patch at
    ``apps.tournaments.signals.Match``
  - ``Bracket`` and ``TournamentService`` are lazy (imported inside the
    function body) → patch at source:
      ``apps.tournaments.models.Bracket``
      ``apps.tournaments.services.tournament_service.TournamentService``
      ``apps.tournaments.services.bracket_service.BracketService``
      ``apps.tournaments.models.group.Group``
      ``apps.tournaments.models.group.GroupStage``
      ``apps.tournaments.services.group_stage_service.GroupStageService``
"""

import logging
from unittest.mock import patch, MagicMock

import pytest


# ── helpers ──────────────────────────────────────────────────────────

_SIG = "apps.tournaments.signals"
_TS = "apps.tournaments.services.tournament_service.TournamentService"
_BS = "apps.tournaments.services.bracket_service.BracketService"
_BRACKET_MODEL = "apps.tournaments.models.Bracket"
_GROUP_MODEL = "apps.tournaments.models.group.Group"
_GS_MODEL = "apps.tournaments.models.group.GroupStage"
_GS_SERVICE = "apps.tournaments.services.group_stage_service.GroupStageService"


def _match_stub(*, state="completed", old_state="scheduled", winner_id=1,
                tournament_id=10, bracket=None, lobby_info=None):
    m = MagicMock()
    m.id = 100
    m.pk = 100
    m.state = state
    m._original_state = old_state
    m.winner_id = winner_id
    m.tournament_id = tournament_id
    m.bracket = bracket
    m.lobby_info = lobby_info or {}
    m.is_deleted = False
    t = MagicMock()
    t.id = tournament_id
    t.pk = tournament_id
    t.format = "group_playoff"
    m.tournament = t
    return m


def _group_qs(all_finished=True):
    qs = MagicMock()
    qs.exists.return_value = True
    qs.exclude.return_value.exists.return_value = (not all_finished)
    return qs


# Shared patches that silence the group-standings block (section 2)
# and bracket-advance block (section 1).
_GROUP_PATCHES = [
    patch(f"{_GROUP_MODEL}.objects"),
    patch(f"{_GS_MODEL}.objects"),
    patch(f"{_GS_SERVICE}"),
    patch(f"{_BS}.update_bracket_after_match"),
]


# ── tests ────────────────────────────────────────────────────────────

class TestSignalKnockoutAutoTransition:

    def test_created_match_is_ignored(self):
        from apps.tournaments.signals import sync_match_completion_progression
        instance = _match_stub()
        with patch(f"{_TS}.transition_to_knockout_stage") as mock_t:
            sync_match_completion_progression(sender=None, instance=instance, created=True)
            mock_t.assert_not_called()

    def test_same_state_is_ignored(self):
        from apps.tournaments.signals import sync_match_completion_progression
        instance = _match_stub(state="completed", old_state="completed")
        with patch(f"{_TS}.transition_to_knockout_stage") as mock_t:
            sync_match_completion_progression(sender=None, instance=instance, created=False)
            mock_t.assert_not_called()

    def test_completing_last_group_match_triggers_knockout(self):
        """All group matches done + no bracket → transition called."""
        from apps.tournaments.signals import sync_match_completion_progression

        group_qs = _group_qs(all_finished=True)

        with (
            patch(f"{_SIG}.Match") as MockMatch,
            patch(f"{_TS}.transition_to_knockout_stage") as mock_transition,
            patch(f"{_BRACKET_MODEL}.objects") as mock_bracket_qs,
            patch(f"{_BS}.update_bracket_after_match"),
            patch(f"{_GROUP_MODEL}.objects") as mock_group_qs,
            patch(f"{_GS_MODEL}.objects"),
        ):
            MockMatch.COMPLETED = "completed"
            MockMatch.FORFEIT = "forfeit"
            MockMatch.CANCELLED = "cancelled"
            MockMatch.objects.filter.return_value = group_qs

            # Groups exist (required — the handler `return`s if no groups)
            # but match_group_id is None (lobby_info={}) so standings
            # recalc is skipped, falling through to section 3.
            mock_group_qs.filter.return_value.exists.return_value = True

            # No bracket
            mock_bracket_qs.filter.return_value.first.return_value = None

            instance = _match_stub()  # lobby_info={} → match_group_id=None
            sync_match_completion_progression(sender=None, instance=instance, created=False)

        mock_transition.assert_called_once_with(instance.tournament.id)

    def test_incomplete_group_matches_skip_transition(self):
        from apps.tournaments.signals import sync_match_completion_progression

        group_qs = _group_qs(all_finished=False)

        with (
            patch(f"{_SIG}.Match") as MockMatch,
            patch(f"{_TS}.transition_to_knockout_stage") as mock_transition,
            patch(f"{_BRACKET_MODEL}.objects"),
            patch(f"{_BS}.update_bracket_after_match"),
            patch(f"{_GROUP_MODEL}.objects") as mock_group_qs,
            patch(f"{_GS_MODEL}.objects"),
        ):
            MockMatch.COMPLETED = "completed"
            MockMatch.FORFEIT = "forfeit"
            MockMatch.CANCELLED = "cancelled"
            MockMatch.objects.filter.return_value = group_qs
            mock_group_qs.filter.return_value.exists.return_value = True

            instance = _match_stub()
            sync_match_completion_progression(sender=None, instance=instance, created=False)

        mock_transition.assert_not_called()

    def test_signal_logs_error_on_knockout_failure(self):
        """BUG-001: failure must be logged at ERROR with exc_info=True."""
        from apps.tournaments.signals import sync_match_completion_progression

        group_qs = _group_qs(all_finished=True)

        with (
            patch(f"{_SIG}.Match") as MockMatch,
            patch(f"{_TS}.transition_to_knockout_stage") as mock_transition,
            patch(f"{_BRACKET_MODEL}.objects") as mock_bracket_qs,
            patch(f"{_BS}.update_bracket_after_match"),
            patch(f"{_GROUP_MODEL}.objects") as mock_group_qs,
            patch(f"{_GS_MODEL}.objects"),
        ):
            MockMatch.COMPLETED = "completed"
            MockMatch.FORFEIT = "forfeit"
            MockMatch.CANCELLED = "cancelled"
            MockMatch.objects.filter.return_value = group_qs
            mock_group_qs.filter.return_value.exists.return_value = True
            mock_bracket_qs.filter.return_value.first.return_value = None
            mock_transition.side_effect = RuntimeError("boom")

            instance = _match_stub()
            with patch.object(
                logging.getLogger("apps.tournaments.signals"), "error"
            ) as mock_err:
                sync_match_completion_progression(sender=None, instance=instance, created=False)
                mock_err.assert_called_once()
                _, kwargs = mock_err.call_args
                assert kwargs.get("exc_info") is True

    def test_bracket_without_matches_allows_retry(self):
        """BUG-003: bracket with 0 knockout matches → allow re-trigger."""
        from apps.tournaments.signals import sync_match_completion_progression

        group_qs = _group_qs(all_finished=True)
        ko_qs = MagicMock()
        ko_qs.exists.return_value = False  # no matches in bracket

        with (
            patch(f"{_SIG}.Match") as MockMatch,
            patch(f"{_TS}.transition_to_knockout_stage") as mock_transition,
            patch(f"{_BRACKET_MODEL}.objects") as mock_bracket_qs,
            patch(f"{_BS}.update_bracket_after_match"),
            patch(f"{_GROUP_MODEL}.objects") as mock_group_qs,
            patch(f"{_GS_MODEL}.objects"),
        ):
            MockMatch.COMPLETED = "completed"
            MockMatch.FORFEIT = "forfeit"
            MockMatch.CANCELLED = "cancelled"

            def filter_side_effect(**kw):
                if kw.get("bracket__isnull") is True:
                    return group_qs
                return ko_qs

            MockMatch.objects.filter.side_effect = filter_side_effect
            mock_group_qs.filter.return_value.exists.return_value = True
            mock_bracket_qs.filter.return_value.first.return_value = MagicMock(id=99)

            instance = _match_stub()
            sync_match_completion_progression(sender=None, instance=instance, created=False)

        mock_transition.assert_called_once()

    def test_bracket_with_matches_skips_retry(self):
        """Bracket with existing knockout matches → do NOT re-trigger."""
        from apps.tournaments.signals import sync_match_completion_progression

        group_qs = _group_qs(all_finished=True)
        ko_qs = MagicMock()
        ko_qs.exists.return_value = True  # has matches

        with (
            patch(f"{_SIG}.Match") as MockMatch,
            patch(f"{_TS}.transition_to_knockout_stage") as mock_transition,
            patch(f"{_BRACKET_MODEL}.objects") as mock_bracket_qs,
            patch(f"{_BS}.update_bracket_after_match"),
            patch(f"{_GROUP_MODEL}.objects") as mock_group_qs,
            patch(f"{_GS_MODEL}.objects"),
        ):
            MockMatch.COMPLETED = "completed"
            MockMatch.FORFEIT = "forfeit"
            MockMatch.CANCELLED = "cancelled"

            def filter_side_effect(**kw):
                if kw.get("bracket__isnull") is True:
                    return group_qs
                return ko_qs

            MockMatch.objects.filter.side_effect = filter_side_effect
            mock_group_qs.filter.return_value.exists.return_value = True
            mock_bracket_qs.filter.return_value.first.return_value = MagicMock(id=99)

            instance = _match_stub()
            sync_match_completion_progression(sender=None, instance=instance, created=False)

        mock_transition.assert_not_called()
