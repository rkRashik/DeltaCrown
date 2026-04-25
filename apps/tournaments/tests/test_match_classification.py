"""
Canonical match classification — unit tests.

Covers `apps.tournaments.services.match_classification`. The module is the
single source of truth used by TOC matches, TOC schedule, TOC brackets,
HUB bracket, HUB matches, and public detail Matches tab. If any of those
surfaces drift, it should be because they bypass this module.
"""

from types import SimpleNamespace

import pytest

from apps.tournaments.services.match_classification import (
    classify_stage,
    compute_round_label,
    is_pure_knockout,
    stage_filter_q,
    PURE_KNOCKOUT_FORMATS,
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


class TestComputeRoundLabel:
    def test_8_team_se(self):
        t = _t('single_elimination')
        assert compute_round_label(t, _m(1), total_rounds=3) == 'Quarterfinal'
        assert compute_round_label(t, _m(2), total_rounds=3) == 'Semifinal'
        assert compute_round_label(t, _m(3), total_rounds=3) == 'Final'

    def test_16_team_se(self):
        t = _t('single_elimination')
        assert compute_round_label(t, _m(1), total_rounds=4) == 'Round of 16'
        assert compute_round_label(t, _m(2), total_rounds=4) == 'Quarterfinal'
        assert compute_round_label(t, _m(3), total_rounds=4) == 'Semifinal'
        assert compute_round_label(t, _m(4), total_rounds=4) == 'Final'

    def test_de_uses_canonical(self):
        # DE: same canonical labeller, total_rounds drives it.
        assert compute_round_label(_t('double_elimination'), _m(3), total_rounds=3) == 'Final'

    def test_round_robin_generic(self):
        assert compute_round_label(_t('round_robin'), _m(2), total_rounds=5) == 'Round 2'

    def test_swiss_generic(self):
        assert compute_round_label(_t('swiss'), _m(3), total_rounds=5) == 'Round 3'

    def test_zero_round_returns_empty(self):
        assert compute_round_label(_t('single_elimination'), _m(0), total_rounds=3) == ''


class TestStageFilterQ:
    def test_pure_knockout_includes_all_for_knockout_filter(self):
        # SE/DE knockout filter should match every match (no bracket FK condition).
        q = stage_filter_q('single_elimination', 'knockout')
        from django.db.models import Q
        assert isinstance(q, Q)
        # An empty Q() is "match all" — should not contain bracket__isnull.
        assert q.children == []

    def test_pure_knockout_group_stage_filter_matches_nothing(self):
        # SE has no group stage; selecting "Group Stage" should return 0 matches.
        q = stage_filter_q('single_elimination', 'group_stage')
        # Q(pk__in=[]) — children should reflect that
        assert any('pk__in' in str(c) for c in q.children)

    def test_round_robin_group_stage_matches_all(self):
        q = stage_filter_q('round_robin', 'group_stage')
        assert q.children == []

    def test_round_robin_knockout_filter_matches_nothing(self):
        q = stage_filter_q('round_robin', 'knockout')
        assert any('pk__in' in str(c) for c in q.children)

    def test_group_playoff_uses_bracket_isnull(self):
        q_group = stage_filter_q('group_playoff', 'group_stage')
        q_ko = stage_filter_q('group_playoff', 'knockout')
        # Each should include `bracket__isnull` filter logic.
        assert any('bracket__isnull' in str(c) for c in q_group.children)
        assert any('bracket__isnull' in str(c) for c in q_ko.children)

    def test_empty_stage_returns_none(self):
        assert stage_filter_q('single_elimination', '') is None
        assert stage_filter_q('single_elimination', None) is None
