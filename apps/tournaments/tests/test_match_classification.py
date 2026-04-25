"""
Canonical match classification + round_naming — unit tests.

Covers `apps.tournaments.services.match_classification`. Single source of
truth used by TOC matches, TOC schedule, HUB matches, and public detail.
"""

from types import SimpleNamespace

import pytest

from apps.tournaments.services.match_classification import (
    classify_stage,
    compute_round_label,
    is_pure_knockout,
    stage_filter_q,
    PURE_KNOCKOUT_FORMATS,
    HYBRID_KNOCKOUT_FORMATS,
)


def _t(format_): return SimpleNamespace(format=format_)
def _m(round_number, *, bracket_id=None):
    return SimpleNamespace(round_number=round_number, bracket_id=bracket_id)


class TestIsPureKnockout:
    def test_se_de(self):
        assert is_pure_knockout('single_elimination')
        assert is_pure_knockout('double_elimination')

    def test_others(self):
        assert not is_pure_knockout('round_robin')
        assert not is_pure_knockout('swiss')
        assert not is_pure_knockout('group_playoff')
        assert not is_pure_knockout('')


class TestClassifyStage:
    def test_se_always_knockout(self):
        assert classify_stage(_t('single_elimination'), _m(1, bracket_id=None)) == 'knockout'
        assert classify_stage(_t('single_elimination'), _m(3, bracket_id=42)) == 'knockout'

    def test_de_always_knockout(self):
        assert classify_stage(_t('double_elimination'), _m(5, bracket_id=None)) == 'knockout'

    def test_round_robin_always_group_stage(self):
        assert classify_stage(_t('round_robin'), _m(1, bracket_id=99)) == 'group_stage'

    def test_swiss(self):
        assert classify_stage(_t('swiss'), _m(2, bracket_id=None)) == 'swiss'

    def test_group_playoff_uses_bracket_fk(self):
        assert classify_stage(_t('group_playoff'), _m(2, bracket_id=None)) == 'group_stage'
        assert classify_stage(_t('group_playoff'), _m(2, bracket_id=7)) == 'knockout'

    def test_format_constants_are_consistent(self):
        assert 'single_elimination' in PURE_KNOCKOUT_FORMATS
        assert 'double_elimination' in PURE_KNOCKOUT_FORMATS
        assert 'group_playoff' in HYBRID_KNOCKOUT_FORMATS
        assert PURE_KNOCKOUT_FORMATS.isdisjoint(HYBRID_KNOCKOUT_FORMATS)


class TestKnockoutLabelsCanonicalForRoundOptions:
    from apps.tournaments.services.round_naming import knockout_round_label

    def test_8_team_se_labels(self):
        from apps.tournaments.services.round_naming import knockout_round_label
        assert knockout_round_label(1, 3) == 'Quarterfinal'
        assert knockout_round_label(2, 3) == 'Semifinal'
        assert knockout_round_label(3, 3) == 'Final'

    def test_16_team_se_labels(self):
        from apps.tournaments.services.round_naming import knockout_round_label
        assert knockout_round_label(1, 4) == 'Round of 16'
        assert knockout_round_label(2, 4) == 'Quarterfinal'
        assert knockout_round_label(3, 4) == 'Semifinal'
        assert knockout_round_label(4, 4) == 'Final'

    def test_unknown_total_falls_back(self):
        from apps.tournaments.services.round_naming import knockout_round_label
        assert knockout_round_label(2, 0) == 'Round 2'


class TestStageFilterQ:
    def test_pure_knockout_includes_all_for_knockout_filter(self):
        q = stage_filter_q('single_elimination', 'knockout')
        from django.db.models import Q
        assert isinstance(q, Q)
        assert q.children == []

    def test_pure_knockout_group_stage_filter_matches_nothing(self):
        q = stage_filter_q('single_elimination', 'group_stage')
        assert any('pk__in' in str(c) for c in q.children)

    def test_round_robin_group_stage_matches_all(self):
        q = stage_filter_q('round_robin', 'group_stage')
        assert q.children == []

    def test_group_playoff_uses_bracket_isnull(self):
        q_group = stage_filter_q('group_playoff', 'group_stage')
        q_ko = stage_filter_q('group_playoff', 'knockout')
        assert any('bracket__isnull' in str(c) for c in q_group.children)
        assert any('bracket__isnull' in str(c) for c in q_ko.children)

    def test_empty_stage_returns_none(self):
        assert stage_filter_q('single_elimination', '') is None
        assert stage_filter_q('single_elimination', None) is None
