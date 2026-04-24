"""
Round-naming service unit tests.

Pure-function tests for `apps.tournaments.services.round_naming`. No DB.
"""

from apps.tournaments.services.round_naming import (
    knockout_round_label,
    double_elim_round_label,
    round_robin_round_label,
    swiss_round_label,
)


class TestKnockoutLabels:
    def test_final(self):
        assert knockout_round_label(3, 3) == 'Final'

    def test_semifinal(self):
        assert knockout_round_label(2, 3) == 'Semifinal'

    def test_quarterfinal(self):
        assert knockout_round_label(2, 4) == 'Quarterfinal'

    def test_round_of_16(self):
        assert knockout_round_label(1, 4) == 'Round of 16'

    def test_round_of_32(self):
        assert knockout_round_label(1, 5) == 'Round of 32'

    def test_long_form_pluralises_top_rounds(self):
        # The "long" form pluralises rounds with multiple matches.
        assert knockout_round_label(2, 4, long=True) == 'Quarterfinals'
        assert knockout_round_label(2, 3, long=True) == 'Semifinals'
        # Final is the same in both forms.
        assert knockout_round_label(3, 3, long=True) == 'Final'

    def test_zero_round_returns_empty(self):
        assert knockout_round_label(0, 5) == ''

    def test_unknown_total_falls_back_to_round_n(self):
        assert knockout_round_label(7, 0) == 'Round 7'

    def test_round_beyond_named_falls_back(self):
        # 8 rounds total, very early round → no named distance match.
        assert knockout_round_label(1, 9) == 'Round 1'


class TestDoubleElimLabels:
    def test_grand_final(self):
        assert double_elim_round_label('grand_final', 1, 3, 4) == 'Grand Final'
        assert double_elim_round_label('GF', 1, 3, 4) == 'Grand Final'

    def test_grand_final_reset(self):
        assert double_elim_round_label('grand_final_reset', 1, 3, 4) == 'Grand Final Reset'
        assert double_elim_round_label('gfr', 1, 3, 4) == 'Grand Final Reset'

    def test_wb_final(self):
        # WB has 3 rounds; round 3 is the WB Final.
        assert double_elim_round_label('main', 3, 3, 4) == 'WB Final'

    def test_wb_semifinal(self):
        # 4-round WB → round 3 is semi.
        assert double_elim_round_label('main', 3, 4, 5) == 'WB Semifinal'

    def test_lb_final(self):
        # LB last round.
        assert double_elim_round_label('lower', 4, 3, 4) == 'LB Final'

    def test_lb_round_n(self):
        assert double_elim_round_label('lower', 1, 3, 4) == 'LB R1'

    def test_unknown_bracket_type_falls_through(self):
        # Unknown bracket type is treated as WB — early round in a deep
        # bracket with no Q/S/F mapping falls back to "WB R{n}".
        out = double_elim_round_label('weird', 1, 6, 6)
        assert out == 'WB R1'


class TestRoundRobinAndSwiss:
    def test_round_robin(self):
        assert round_robin_round_label(3, 5) == 'Round 3'
        assert round_robin_round_label(0, 5) == ''

    def test_swiss_with_total(self):
        assert swiss_round_label(2, 5) == 'Swiss R2/5'

    def test_swiss_without_total(self):
        assert swiss_round_label(2, 0) == 'Swiss R2'

    def test_swiss_zero(self):
        assert swiss_round_label(0, 5) == ''
