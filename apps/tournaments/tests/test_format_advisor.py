"""
Format Advisor unit tests.

Verifies hard errors and soft warnings emitted by
`apps.tournaments.services.format_advisor.validate_format_participants`.

Pure-function tests — no DB, no Django setup needed beyond import.
"""

import pytest

from apps.tournaments.services.format_advisor import validate_format_participants


class TestHardErrors:
    def test_de_below_4_participants_errors(self):
        errs, warns = validate_format_participants('double_elimination', 2, 3)
        assert errs and 'Double Elimination needs at least 4' in errs[0]
        # Warnings suppressed when hard errors fire to keep messaging focused.
        assert warns == []

    def test_de_at_4_participants_no_error(self):
        errs, _ = validate_format_participants('double_elimination', 4, 4)
        assert errs == []

    def test_se_below_2_participants_errors(self):
        errs, _ = validate_format_participants('single_elimination', 1, 1)
        assert errs and 'at least 2 participants' in errs[0]

    def test_group_playoff_below_4_errors(self):
        errs, _ = validate_format_participants('group_playoff', 2, 3)
        assert errs and 'Group Stage + Playoff needs at least 4' in errs[0]


class TestSoftWarnings:
    def test_se_with_3_players_warns_recommend_round_robin(self):
        errs, warns = validate_format_participants('single_elimination', 2, 3)
        assert errs == []
        assert any('Round Robin' in w for w in warns)

    def test_se_non_power_of_two_warns_byes(self):
        errs, warns = validate_format_participants('single_elimination', 2, 6)
        assert errs == []
        assert any('not a power of two' in w for w in warns)
        # 6 -> next power of two = 8 -> 2 byes
        assert any('2 bye' in w for w in warns)

    def test_se_power_of_two_no_bye_warning(self):
        _, warns = validate_format_participants('single_elimination', 2, 8)
        assert not any('not a power of two' in w for w in warns)

    def test_de_small_bracket_warns_bye_heavy(self):
        _, warns = validate_format_participants('double_elimination', 4, 6)
        assert any('Small Double Elimination' in w for w in warns)

    def test_de_8_no_small_bracket_warning(self):
        _, warns = validate_format_participants('double_elimination', 4, 8)
        assert not any('Small Double Elimination' in w for w in warns)

    def test_swiss_below_4_warns(self):
        _, warns = validate_format_participants('swiss', 2, 3)
        assert any('Swiss' in w for w in warns)

    def test_round_robin_large_field_warns_match_count(self):
        _, warns = validate_format_participants('round_robin', 2, 20)
        # 20*19/2 = 190
        assert any('190' in w for w in warns)


class TestDegenerateInputs:
    def test_missing_format_returns_empty(self):
        assert validate_format_participants(None, 4, 8) == ([], [])
        assert validate_format_participants('', 4, 8) == ([], [])

    def test_missing_max_returns_empty(self):
        assert validate_format_participants('single_elimination', 4, None) == ([], [])

    def test_unknown_format_returns_empty(self):
        # Unknown format: no rules fire, no opinion offered.
        assert validate_format_participants('battle_royale', 2, 100) == ([], [])

    def test_string_inputs_are_coerced(self):
        errs, _ = validate_format_participants('double_elimination', '2', '3')
        assert errs and 'Double Elimination' in errs[0]
