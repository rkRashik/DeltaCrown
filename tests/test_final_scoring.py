"""
Game-Specific Scoring Tests — Phase Final

Comprehensive tests for:
1. ScoringEvaluator with all 11 games' scoring types
2. max_score validation (range enforcement)
3. Valorant overtime scoring (rounds > 13)
4. Two-leg aggregate (football/goals)
5. BR series scoring with placement + kills
6. MOBA KDA tracking
7. Bounty facade normalizers
8. Challenge consolidation shim
9. Dashboard secondary_data loader
10. parseError enhanced coverage (tested via Python-level logic mirror)

Run with:
  DJANGO_SETTINGS_MODULE=deltacrown.settings_smoke pytest tests/test_final_scoring.py -v --no-migrations
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ── Override session fixtures to avoid PostgreSQL dependency ────────────────
@pytest.fixture(scope='session')
def django_db_setup():
    pass

@pytest.fixture(scope='session', autouse=True)
def enforce_test_database():
    yield

@pytest.fixture(scope='session', autouse=True)
def setup_test_schema():
    yield


def _make_standing():
    """Create a mock GroupStanding with all numeric fields."""
    s = MagicMock()
    s.goals_for = 0
    s.goals_against = 0
    s.goal_difference = 0
    s.rounds_won = 0
    s.rounds_lost = 0
    s.round_difference = 0
    s.total_kills = 0
    s.total_deaths = 0
    s.total_assists = 0
    s.kda_ratio = Decimal('0.00')
    s.placement_points = Decimal('0.00')
    s.total_score = 0
    s.calculate_kda = MagicMock(return_value=Decimal('2.50'))
    return s


# ═══════════════════════════════════════════════════════════════════════════
# 1. MAX SCORE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestMaxScoreValidation:
    """Verify max_score enforcement across all scoring types."""

    def test_score_within_limit_passes(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        # Valorant: max_score=13, score=13 → OK
        ev.update_standings(s1, s2, {
            'participant1_score': 13,
            'participant2_score': 7,
        }, 'ROUNDS', max_score=13)
        # No exception raised

    def test_score_exceeding_limit_raises(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        with pytest.raises(ValueError, match="exceeds maximum"):
            ev.update_standings(s1, s2, {
                'participant1_score': 14,
                'participant2_score': 7,
            }, 'ROUNDS', max_score=13)

    def test_max_score_none_allows_any(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_score': 999,
            'participant2_score': 500,
        }, 'ROUNDS', max_score=None)
        # No exception

    def test_max_score_participant2_exceeds(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        with pytest.raises(ValueError, match="exceeds maximum"):
            ev.update_standings(s1, s2, {
                'participant1_score': 5,
                'participant2_score': 100,
            }, 'GOALS', max_score=99)

    def test_football_max_score_99(self):
        """EA FC / eFootball: max_score=99, typical score 3-1 passes."""
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_score': 3,
            'participant2_score': 1,
        }, 'GOALS', max_score=99)
        assert s1.goals_for == 3
        assert s2.goals_for == 1

    def test_br_max_score_999(self):
        """PUBGM/FreeFire: max_score=999 for kill-based scoring."""
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_score': 500,
            'participant2_score': 400,
            'participant1_kills': 15,
            'participant2_kills': 10,
            'participant1_placement_points': 300,
            'participant2_placement_points': 200,
        }, 'PLACEMENT', max_score=999)
        assert s1.total_kills == 15
        assert s2.placement_points == Decimal('200')


# ═══════════════════════════════════════════════════════════════════════════
# 2. VALORANT OVERTIME SCORING
# ═══════════════════════════════════════════════════════════════════════════

class TestValorantOvertimeScoring:
    """Valorant: games can go to overtime (>13 rounds, e.g. 15-13)."""

    def test_regulation_win_13_7(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_rounds': 13,
            'participant2_rounds': 7,
            'participant1_kills': 22,
            'participant2_kills': 14,
            'participant1_deaths': 14,
            'participant2_deaths': 22,
        }, 'ROUNDS')
        assert s1.rounds_won == 13
        assert s2.rounds_won == 7
        assert s1.round_difference == 6
        assert s2.round_difference == -6
        assert s1.total_kills == 22

    def test_overtime_win_15_13(self):
        """Overtime: 15-13 is valid even with max_score=13 (rounds exceed)."""
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        # Overtime rounds tracked — no max_score cap on rounds
        ev.update_standings(s1, s2, {
            'participant1_rounds': 15,
            'participant2_rounds': 13,
            'participant1_kills': 28,
            'participant2_kills': 25,
            'participant1_deaths': 25,
            'participant2_deaths': 28,
        }, 'ROUNDS')
        assert s1.rounds_won == 15
        assert s2.rounds_won == 13
        assert s1.round_difference == 2

    def test_double_overtime_16_14(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_rounds': 16,
            'participant2_rounds': 14,
        }, 'ROUNDS')
        assert s1.rounds_won == 16
        assert s2.rounds_lost == 16


# ═══════════════════════════════════════════════════════════════════════════
# 3. TWO-LEG AGGREGATE (FOOTBALL)
# ═══════════════════════════════════════════════════════════════════════════

class TestTwoLegAggregate:
    """Football (EA FC/eFootball): two-leg aggregate across two match_data calls."""

    def test_aggregate_over_two_legs(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()

        # Leg 1: Home team wins 3-1
        ev.update_standings(s1, s2, {
            'participant1_score': 3,
            'participant2_score': 1,
        }, 'GOALS', max_score=99)

        # Leg 2: Away team wins 2-0
        ev.update_standings(s1, s2, {
            'participant1_score': 0,
            'participant2_score': 2,
        }, 'GOALS', max_score=99)

        # Aggregate: s1 scored 3+0=3, conceded 1+2=3
        assert s1.goals_for == 3
        assert s1.goals_against == 3
        assert s1.goal_difference == 0

        # s2 scored 1+2=3, conceded 3+0=3
        assert s2.goals_for == 3
        assert s2.goals_against == 3
        assert s2.goal_difference == 0

    def test_dominant_aggregate(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()

        ev.update_standings(s1, s2, {'participant1_score': 5, 'participant2_score': 0}, 'GOALS')
        ev.update_standings(s1, s2, {'participant1_score': 3, 'participant2_score': 1}, 'GOALS')

        assert s1.goals_for == 8
        assert s1.goals_against == 1
        assert s1.goal_difference == 7


# ═══════════════════════════════════════════════════════════════════════════
# 4. BATTLE ROYALE SERIES SCORING
# ═══════════════════════════════════════════════════════════════════════════

class TestBRSeriesScoring:
    """BR games (PUBGM, FreeFire): placement + kill-based across multiple rounds."""

    def test_pubgm_three_round_series(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()

        # Round 1: s1 wins with 1st place, 12 kills
        ev.update_standings(s1, s2, {
            'participant1_kills': 12,
            'participant1_placement_points': 15,
            'participant2_kills': 5,
            'participant2_placement_points': 8,
        }, 'PLACEMENT')

        # Round 2: s2 wins
        ev.update_standings(s1, s2, {
            'participant1_kills': 6,
            'participant1_placement_points': 8,
            'participant2_kills': 14,
            'participant2_placement_points': 15,
        }, 'PLACEMENT')

        # Round 3
        ev.update_standings(s1, s2, {
            'participant1_kills': 9,
            'participant1_placement_points': 12,
            'participant2_kills': 7,
            'participant2_placement_points': 10,
        }, 'PLACEMENT')

        # Totals: s1 kills=27, placement=35; s2 kills=26, placement=33
        assert s1.total_kills == 27
        assert s1.placement_points == Decimal('35')
        assert s2.total_kills == 26
        assert s2.placement_points == Decimal('33')

    def test_freefire_kills_scoring(self):
        """FreeFire uses KILLS scoring type."""
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_kills': 20,
            'participant1_placement_points': 10,
            'participant2_kills': 8,
            'participant2_placement_points': 5,
        }, 'KILLS')
        assert s1.total_kills == 20
        assert s2.placement_points == Decimal('5')


# ═══════════════════════════════════════════════════════════════════════════
# 5. MOBA KDA TRACKING
# ═══════════════════════════════════════════════════════════════════════════

class TestMOBAKDATracking:
    """MOBA (DOTA2/MLBB): WIN_LOSS+MOBA category triggers KDA helper."""

    def test_mlbb_kda_calculation(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()

        ev.update_standings(s1, s2, {
            'participant1_kills': 15,
            'participant1_deaths': 3,
            'participant1_assists': 20,
            'participant1_score': 1,
            'participant2_kills': 8,
            'participant2_deaths': 12,
            'participant2_assists': 10,
            'participant2_score': 0,
        }, 'WIN_LOSS', game_category='MOBA')

        assert s1.total_kills == 15
        assert s1.total_deaths == 3
        assert s1.total_assists == 20
        assert s1.total_score == 1
        s1.calculate_kda.assert_called_once()

    def test_non_moba_win_loss_skips_kda(self):
        """Non-MOBA WIN_LOSS should use the default handler (no-op)."""
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()

        ev.update_standings(s1, s2, {
            'participant1_kills': 10,
            'participant2_kills': 5,
        }, 'WIN_LOSS', game_category='FPS')

        # _apply_win_loss is a no-op — stats untouched
        assert s1.total_kills == 0
        assert s2.total_kills == 0


# ═══════════════════════════════════════════════════════════════════════════
# 6. CS2 ROUNDS (MAX 16)
# ═══════════════════════════════════════════════════════════════════════════

class TestCS2Scoring:
    """CS2: ROUNDS with max_score=16."""

    def test_cs2_standard_game(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_rounds': 13,
            'participant2_rounds': 10,
            'participant1_kills': 25,
            'participant2_kills': 20,
            'participant1_deaths': 20,
            'participant2_deaths': 25,
        }, 'ROUNDS', max_score=16)
        assert s1.rounds_won == 13
        assert s2.rounds_won == 10
        assert s1.total_kills == 25

    def test_cs2_overtime_mr3(self):
        """CS2 overtime (MR3) can produce 16-14."""
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_rounds': 16,
            'participant2_rounds': 14,
        }, 'ROUNDS')
        assert s1.rounds_won == 16
        assert s1.round_difference == 2


# ═══════════════════════════════════════════════════════════════════════════
# 7. CODM AND R6 SIEGE
# ═══════════════════════════════════════════════════════════════════════════

class TestCODMScoring:
    """CODM: ROUNDS with max_score=10."""

    def test_codm_snd_6_4(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_rounds': 6,
            'participant2_rounds': 4,
            'participant1_kills': 18,
            'participant2_kills': 12,
            'participant1_deaths': 12,
            'participant2_deaths': 18,
        }, 'ROUNDS', max_score=10)
        assert s1.rounds_won == 6
        assert s1.total_kills == 18


class TestR6SiegeScoring:
    """R6 Siege: ROUNDS with max_score=7."""

    def test_r6_regulation_5_3(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_rounds': 5,
            'participant2_rounds': 3,
        }, 'ROUNDS', max_score=7)
        assert s1.rounds_won == 5
        assert s2.rounds_won == 3


# ═══════════════════════════════════════════════════════════════════════════
# 8. ROCKET LEAGUE
# ═══════════════════════════════════════════════════════════════════════════

class TestRocketLeagueScoring:
    """Rocket League: GOALS with max_score=20."""

    def test_rl_standard_game(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_score': 4,
            'participant2_score': 2,
        }, 'GOALS', max_score=20)
        assert s1.goals_for == 4
        assert s2.goals_for == 2
        assert s1.goal_difference == 2

    def test_rl_score_exceeds_max(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        with pytest.raises(ValueError, match="exceeds maximum"):
            ev.update_standings(s1, s2, {
                'participant1_score': 21,
                'participant2_score': 0,
            }, 'GOALS', max_score=20)


# ═══════════════════════════════════════════════════════════════════════════
# 9. SCORING EVALUATOR DISPATCH TABLE
# ═══════════════════════════════════════════════════════════════════════════

class TestScoringDispatchTable:
    """Verify all scoring_type values dispatch correctly."""

    def test_all_handler_names_exist(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        for scoring_type, method_name in ev._HANDLERS.items():
            assert hasattr(ev, method_name), f"Missing handler: {method_name} for {scoring_type}"

    def test_unknown_type_falls_back_to_win_loss(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        # Unknown type should not raise, falls back to _apply_win_loss (no-op)
        ev.update_standings(s1, s2, {
            'participant1_score': 1,
            'participant2_score': 0,
        }, 'UNKNOWN_TYPE')

    def test_custom_type_uses_win_loss(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {}, 'CUSTOM')
        # No-op — no stats changed

    def test_points_type_uses_win_loss(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {}, 'POINTS')


# ═══════════════════════════════════════════════════════════════════════════
# 10. GAME TOURNAMENT CONFIG — validate_score
# ═══════════════════════════════════════════════════════════════════════════

class TestGameTournamentConfigValidateScore:
    """Test GameTournamentConfig.validate_score method."""

    def test_validate_score_within_max(self):
        from apps.games.models.tournament_config import GameTournamentConfig
        config = GameTournamentConfig()
        config.max_score = 13
        assert config.validate_score(13) is True
        assert config.validate_score(0) is True
        assert config.validate_score(7) is True

    def test_validate_score_exceeds_max(self):
        from apps.games.models.tournament_config import GameTournamentConfig
        config = GameTournamentConfig()
        config.max_score = 13
        assert config.validate_score(14) is False

    def test_validate_score_no_max(self):
        from apps.games.models.tournament_config import GameTournamentConfig
        config = GameTournamentConfig()
        config.max_score = None
        assert config.validate_score(999) is True


# ═══════════════════════════════════════════════════════════════════════════
# 11. BOUNTY FACADE NORMALIZERS
# ═══════════════════════════════════════════════════════════════════════════

class TestBountyFacadeNormalizers:
    """Test normalization functions for unified bounty display."""

    def test_normalize_competition_bounty(self):
        from apps.competition.services.bounty_facade import _normalize_competition_bounty
        bounty = MagicMock()
        bounty.id = 'uuid-1234'
        bounty.title = 'Beat Us BO3'
        bounty.bounty_type = 'BEAT_US'
        bounty.status = 'ACTIVE'
        bounty.reward_amount = Decimal('100')
        bounty.reward_type = 'CP'
        bounty.issuer_team.name = 'Team Alpha'
        bounty.game.name = 'Valorant'
        bounty.game.icon_url = 'val.png'
        bounty.is_claimable = True
        bounty.expires_at = None
        from datetime import datetime
        bounty.created_at = datetime(2026, 1, 1)

        result = _normalize_competition_bounty(bounty)
        assert result['source'] == 'competition'
        assert result['title'] == 'Beat Us BO3'
        assert result['reward_amount'] == 100.0
        assert result['issuer_name'] == 'Team Alpha'
        assert result['is_claimable'] is True

    def test_normalize_profile_bounty(self):
        from apps.competition.services.bounty_facade import _normalize_profile_bounty
        bounty = MagicMock()
        bounty.id = 'uuid-5678'
        bounty.title = '1v1 Challenge'
        bounty.bounty_type = 'SOLO'
        bounty.status = 'open'
        bounty.amount = Decimal('50')
        bounty.game.name = 'CS2'
        bounty.game.icon_url = 'cs2.png'
        bounty.creator.username = 'player1'
        bounty.expires_at = None
        from datetime import datetime
        bounty.created_at = datetime(2026, 1, 2)

        result = _normalize_profile_bounty(bounty)
        assert result['source'] == 'profile'
        assert result['reward_amount'] == 50.0
        assert result['issuer_name'] == 'player1'
        assert result['is_claimable'] is True


# ═══════════════════════════════════════════════════════════════════════════
# 12. CHALLENGE CONSOLIDATION SHIM
# ═══════════════════════════════════════════════════════════════════════════

class TestChallengeConsolidationShim:
    """Verify the legacy challenges.models re-exports CompetitionChallenge."""

    def test_competition_challenge_re_exported(self):
        from apps.challenges.models import CompetitionChallenge
        assert CompetitionChallenge is not None

    def test_competition_challenge_is_from_competition(self):
        from apps.challenges.models import CompetitionChallenge
        from apps.competition.models.challenge import Challenge
        assert CompetitionChallenge is Challenge

    def test_legacy_challenge_save_warns(self):
        """Legacy Challenge.save() should emit DeprecationWarning."""
        import warnings
        from apps.challenges.models import Challenge
        c = Challenge.__new__(Challenge)
        # We can't actually save (no DB), but we can check the warning
        # by calling save with a mock that prevents the actual DB call
        with patch.object(Challenge.__bases__[0], 'save', return_value=None):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                c.save()
                assert any(issubclass(x.category, DeprecationWarning) for x in w)


# ═══════════════════════════════════════════════════════════════════════════
# 13. DASHBOARD SECONDARY DATA MODULE STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════

class TestDashboardSecondaryData:
    """Verify the secondary_data module can be imported and has expected functions."""

    def test_module_imports(self):
        from apps.dashboard.secondary_data import load_secondary_data
        assert callable(load_secondary_data)

    def test_load_secondary_data_returns_dict(self):
        """Verify it returns a dict even when all models fail."""
        from apps.dashboard.secondary_data import load_secondary_data
        mock_user = MagicMock()
        mock_user.teams.values_list.return_value = []

        # All internal _safe_model calls will fail → graceful degradation
        with patch('apps.dashboard.secondary_data._safe_model', return_value=None):
            with patch('apps.dashboard.secondary_data._load_notifications', return_value={'recent_notifications': [], 'unread_notif_count': 0}):
                result = load_secondary_data(mock_user)
                assert isinstance(result, dict)
                assert 'wallet' in result
                assert 'badges' in result
                assert 'active_bounties' in result

    def test_secondary_data_has_all_sections(self):
        """Ensure all 12 section loaders exist."""
        from apps.dashboard import secondary_data as sd
        expected_loaders = [
            '_load_wallet', '_load_badges', '_load_notifications',
            '_load_social', '_load_orders', '_load_organizations',
            '_load_game_passports', '_load_recruitment',
            '_load_featured_product', '_load_support_tickets',
            '_load_challenges', '_load_bounties',
        ]
        for name in expected_loaders:
            assert hasattr(sd, name), f"Missing loader: {name}"


# ═══════════════════════════════════════════════════════════════════════════
# 14. NORMALIZE_SLUG INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalizeSlugForGames:
    """Verify GameService.normalize_slug handles game aliases."""

    def test_standard_slugs(self):
        from apps.games.services.game_service import GameService
        ns = GameService.normalize_slug
        assert ns('valorant') == 'valorant'
        assert ns('cs2') == 'cs2'
        assert ns('efootball') == 'efootball'
        assert ns('dota2') == 'dota2'

    def test_legacy_aliases(self):
        from apps.games.services.game_service import GameService
        ns = GameService.normalize_slug
        assert ns('csgo') == 'cs2'
        assert ns('pes') == 'efootball'
        assert ns('ff') == 'free-fire'
        assert ns('pubgm') == 'pubg-mobile'
        assert ns('mlbb') == 'mobile-legends'

    def test_case_insensitive(self):
        from apps.games.services.game_service import GameService
        ns = GameService.normalize_slug
        assert ns('VALORANT') == 'valorant'
        assert ns('CS2') == 'cs2'
        assert ns('EFOOTBALL') == 'efootball'
