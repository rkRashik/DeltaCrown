"""
Truth-consistency unit tests for the consistency repair pass.

These cover the pure-function paths only (so they don't need a live DB):
  * Stage classification rules in `TOCMatchesService._resolve_stage`
  * Round-label fallback logic via the round_naming canonical helpers
  * Format-aware classification matrix shared by TOC matches/schedule/HUB

Integration tests that exercise the matches API end-to-end live in
test_toc_matches_*.py (require DB).
"""

from types import SimpleNamespace

from apps.tournaments.api.toc.matches_service import (
    TOCMatchesService,
    _PURE_KNOCKOUT_FORMATS,
    _HYBRID_KNOCKOUT_FORMATS,
)
from apps.tournaments.services.round_naming import knockout_round_label


class TestStageClassificationContract:
    """The single contract every TOC surface must follow."""

    def _match(self, *, bracket_id=None):
        return SimpleNamespace(bracket_id=bracket_id)

    def test_single_elim_always_knockout(self):
        m_with = self._match(bracket_id=42)
        m_without = self._match(bracket_id=None)
        assert TOCMatchesService._resolve_stage(m_with, 'single_elimination') == 'knockout'
        assert TOCMatchesService._resolve_stage(m_without, 'single_elimination') == 'knockout'

    def test_double_elim_always_knockout(self):
        m_with = self._match(bracket_id=42)
        m_without = self._match(bracket_id=None)
        assert TOCMatchesService._resolve_stage(m_with, 'double_elimination') == 'knockout'
        assert TOCMatchesService._resolve_stage(m_without, 'double_elimination') == 'knockout'

    def test_round_robin_is_group_stage(self):
        assert TOCMatchesService._resolve_stage(
            self._match(bracket_id=None), 'round_robin'
        ) == 'group_stage'
        # Even if some legacy data attached a bracket_id, RR stays group.
        assert TOCMatchesService._resolve_stage(
            self._match(bracket_id=99), 'round_robin'
        ) == 'group_stage'

    def test_swiss_is_swiss_not_group(self):
        assert TOCMatchesService._resolve_stage(
            self._match(bracket_id=None), 'swiss'
        ) == 'swiss'

    def test_group_playoff_uses_bracket_id(self):
        # Group phase: no bracket_id → group_stage.
        assert TOCMatchesService._resolve_stage(
            self._match(bracket_id=None), 'group_playoff'
        ) == 'group_stage'
        # Playoff phase: bracket_id present → knockout.
        assert TOCMatchesService._resolve_stage(
            self._match(bracket_id=7), 'group_playoff'
        ) == 'knockout'

    def test_format_constants_are_consistent(self):
        # The two sets are documented + relied on by _resolve_stage.
        assert 'single_elimination' in _PURE_KNOCKOUT_FORMATS
        assert 'double_elimination' in _PURE_KNOCKOUT_FORMATS
        assert 'group_playoff' in _HYBRID_KNOCKOUT_FORMATS
        assert _PURE_KNOCKOUT_FORMATS.isdisjoint(_HYBRID_KNOCKOUT_FORMATS)


class TestKnockoutLabelsCanonicalForRoundOptions:
    """
    The round_options dropdown should surface canonical labels for an
    8-team SE bracket: Quarterfinal/Semifinal/Final (not just "Round N").
    """

    def test_8_team_se_labels(self):
        # 8 teams → 3 rounds. Round 1 = Quarterfinal, 2 = Semifinal, 3 = Final.
        assert knockout_round_label(1, 3) == 'Quarterfinal'
        assert knockout_round_label(2, 3) == 'Semifinal'
        assert knockout_round_label(3, 3) == 'Final'

    def test_16_team_se_labels(self):
        # 16 teams → 4 rounds. R1 = Round of 16, R2 = QF, R3 = SF, R4 = Final.
        assert knockout_round_label(1, 4) == 'Round of 16'
        assert knockout_round_label(2, 4) == 'Quarterfinal'
        assert knockout_round_label(3, 4) == 'Semifinal'
        assert knockout_round_label(4, 4) == 'Final'

    def test_32_team_se_labels(self):
        assert knockout_round_label(1, 5) == 'Round of 32'
        assert knockout_round_label(5, 5) == 'Final'

    def test_unknown_total_rounds_falls_back(self):
        # Unknown total → "Round N" so dropdown still shows something useful.
        assert knockout_round_label(2, 0) == 'Round 2'


class TestRoundOptionsBuilderShape:
    """`_build_round_options` output is the contract the JS depends on."""

    def test_signature_present(self):
        from apps.tournaments.api.toc.matches_service import TOCMatchesService
        assert callable(getattr(TOCMatchesService, '_build_round_options', None))

    def test_pure_knockout_uses_canonical_labels(self, monkeypatch):
        """8-team SE: dropdown should list Quarterfinal/Semifinal/Final, not Round 1/2/3."""
        from apps.tournaments.api.toc import matches_service as ms

        # Stub the Match queryset .values_list lookup with a deterministic set.
        class _FakeQS:
            def __init__(self, rows): self._rows = rows
            def filter(self, **kw): return self
            def exclude(self, **kw): return self
            def values_list(self, *a, **kw): return self
            def distinct(self): return self._rows
            def __iter__(self): return iter(self._rows)
            def __bool__(self): return bool(self._rows)
            def __len__(self): return len(self._rows)

        rows = [(1, None), (2, None), (3, None)]  # 8-team SE w/o bracket FK
        fake = _FakeQS(rows)

        class _FakeMatchModel:
            objects = None
        class _FakeManager:
            def filter(self, **kw): return fake
        _FakeMatchModel.objects = _FakeManager()

        monkeypatch.setattr(ms, 'Match', _FakeMatchModel)

        # No bracket present.
        options = ms.TOCMatchesService._build_round_options(
            tournament=type('T', (), {'pk': 1})(),
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

        options = ms.TOCMatchesService._build_round_options(
            tournament=type('T', (), {'pk': 1})(),
            tournament_format='round_robin',
            bracket=None,
            total_rounds=2,
        )
        assert all(o['stage'] == 'group_stage' for o in options)
