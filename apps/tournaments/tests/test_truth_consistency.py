"""
Truth-consistency unit tests — status, round labels, stage classification.
"""

from types import SimpleNamespace
import pytest


# ── Stage classifier ──────────────────────────────────────────────────────

from apps.tournaments.api.toc.matches_service import (
    TOCMatchesService,
    _PURE_KNOCKOUT_FORMATS,
    _HYBRID_KNOCKOUT_FORMATS,
)
from apps.tournaments.services.round_naming import knockout_round_label


class TestStageClassificationContract:

    def _match(self, *, bracket_id=None):
        return SimpleNamespace(bracket_id=bracket_id)

    def test_single_elim_always_knockout(self):
        for bid in (None, 42):
            assert TOCMatchesService._resolve_stage(
                self._match(bracket_id=bid), 'single_elimination'
            ) == 'knockout'

    def test_double_elim_always_knockout(self):
        for bid in (None, 42):
            assert TOCMatchesService._resolve_stage(
                self._match(bracket_id=bid), 'double_elimination'
            ) == 'knockout'

    def test_round_robin_is_group_stage(self):
        for bid in (None, 99):
            assert TOCMatchesService._resolve_stage(
                self._match(bracket_id=bid), 'round_robin'
            ) == 'group_stage'

    def test_swiss_is_swiss(self):
        assert TOCMatchesService._resolve_stage(
            self._match(bracket_id=None), 'swiss'
        ) == 'swiss'

    def test_group_playoff_uses_bracket_id(self):
        assert TOCMatchesService._resolve_stage(
            self._match(bracket_id=None), 'group_playoff'
        ) == 'group_stage'
        assert TOCMatchesService._resolve_stage(
            self._match(bracket_id=7), 'group_playoff'
        ) == 'knockout'

    def test_format_constants_consistent(self):
        assert 'single_elimination' in _PURE_KNOCKOUT_FORMATS
        assert 'double_elimination' in _PURE_KNOCKOUT_FORMATS
        assert 'group_playoff' in _HYBRID_KNOCKOUT_FORMATS
        assert _PURE_KNOCKOUT_FORMATS.isdisjoint(_HYBRID_KNOCKOUT_FORMATS)


class TestKnockoutLabels:

    def test_8_team_se_labels(self):
        assert knockout_round_label(1, 3) == 'Quarterfinal'
        assert knockout_round_label(2, 3) == 'Semifinal'
        assert knockout_round_label(3, 3) == 'Final'

    def test_16_team_se_labels(self):
        assert knockout_round_label(1, 4) == 'Round of 16'
        assert knockout_round_label(2, 4) == 'Quarterfinal'
        assert knockout_round_label(3, 4) == 'Semifinal'
        assert knockout_round_label(4, 4) == 'Final'

    def test_32_team_labels(self):
        assert knockout_round_label(1, 5) == 'Round of 32'
        assert knockout_round_label(5, 5) == 'Final'

    def test_unknown_total_falls_back(self):
        assert knockout_round_label(2, 0) == 'Round 2'


class TestRoundOptionsBuilderShape:

    def test_signature_present(self):
        assert callable(getattr(TOCMatchesService, '_build_round_options', None))

    def test_pure_knockout_uses_canonical_labels(self, monkeypatch):
        from apps.tournaments.api.toc import matches_service as ms
        from apps.tournaments.services import match_classification as mc

        class _FakeQS:
            def __init__(self, rows): self._rows = rows
            def filter(self, **kw): return self
            def exclude(self, **kw): return self
            def values_list(self, *a, **kw): return self
            def distinct(self): return self._rows
            def __iter__(self): return iter(self._rows)
            def __bool__(self): return bool(self._rows)
            def __len__(self): return len(self._rows)

        rows = [(1, None), (2, None), (3, None)]
        fake = _FakeQS(rows)

        class _FakeMatchModel:
            class objects:
                @staticmethod
                def filter(**kw): return fake

        monkeypatch.setattr(ms, 'Match', _FakeMatchModel)
        monkeypatch.setattr(mc, 'tournament_total_rounds', lambda t, bracket=None: 3)

        options = ms.TOCMatchesService._build_round_options(
            tournament=type('T', (), {'pk': 1, 'format': 'single_elimination'})(),
            tournament_format='single_elimination',
            bracket=None,
            total_rounds=3,
        )
        labels = [o['label'] for o in options]
        assert labels == ['Quarterfinal', 'Semifinal', 'Final']
        for o in options:
            assert o['stage'] == 'knockout'

    def test_round_robin_marks_group_stage(self, monkeypatch):
        from apps.tournaments.api.toc import matches_service as ms
        from apps.tournaments.services import match_classification as mc

        class _FakeQS(list):
            def filter(self, **kw): return self
            def exclude(self, **kw): return self
            def values_list(self, *a, **kw): return self
            def distinct(self): return self

        rows = _FakeQS([(1, None), (2, None)])
        class _FakeMatchModel:
            class objects:
                @staticmethod
                def filter(**kw): return rows
        monkeypatch.setattr(ms, 'Match', _FakeMatchModel)
        monkeypatch.setattr(mc, 'tournament_total_rounds', lambda t, bracket=None: 2)

        options = ms.TOCMatchesService._build_round_options(
            tournament=type('T', (), {'pk': 1, 'format': 'round_robin'})(),
            tournament_format='round_robin',
            bracket=None,
            total_rounds=2,
        )
        assert all(o['stage'] == 'group_stage' for o in options)


class TestEffectiveStatusWithTournamentResult:
    """
    Tournament.get_effective_status() must return COMPLETED when a
    TournamentResult with winner_id exists, even if persisted status is LIVE.
    """

    def test_completed_when_result_winner_exists(self, monkeypatch):
        from apps.tournaments.models.tournament import Tournament

        t = Tournament.__new__(Tournament)
        t.pk = 99
        t.status = Tournament.LIVE
        t.format = Tournament.SINGLE_ELIM

        # Monkeypatch the TournamentResult query to return True.
        import apps.tournaments.models.tournament as t_mod
        class _FakeTR:
            class objects:
                @staticmethod
                def filter(**kw):
                    class _QS:
                        def exclude(self, **kw2): return self
                        def exists(self): return True
                    return _QS()
        monkeypatch.setattr(t_mod, 'TournamentResult', _FakeTR, raising=False)

        # Patch the import inside get_effective_status.
        import sys
        import types as _types
        fake_result_mod = _types.ModuleType('apps.tournaments.models.result')
        fake_result_mod.TournamentResult = _FakeTR
        monkeypatch.setitem(sys.modules, 'apps.tournaments.models.result',
                            fake_result_mod)

        effective = t.get_effective_status()
        assert effective == Tournament.COMPLETED

    def test_live_when_no_result(self, monkeypatch):
        from apps.tournaments.models.tournament import Tournament
        import sys, types as _types

        t = Tournament.__new__(Tournament)
        t.pk = 99
        t.status = Tournament.LIVE
        t.format = Tournament.SINGLE_ELIM
        t.config = {}

        class _FakeTR:
            class objects:
                @staticmethod
                def filter(**kw):
                    class _QS:
                        def exclude(self, **kw2): return self
                        def exists(self): return False
                    return _QS()
        fake_result_mod = _types.ModuleType('apps.tournaments.models.result')
        fake_result_mod.TournamentResult = _FakeTR
        monkeypatch.setitem(sys.modules, 'apps.tournaments.models.result',
                            fake_result_mod)

        effective = t.get_effective_status()
        assert effective == Tournament.LIVE
