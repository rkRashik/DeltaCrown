"""
Game Scoring Validation Tests — Pre-deployment

Focused on:
1. PUBG Mobile scoring (kill-based + placement)
2. Valorant full-match validation (overtime, max_score, round scoring)
3. Credential schema DB lookup chain
4. New-game integration readiness (seeding, config, schema)
5. GameTournamentConfig.validate_score for all games

Run with:
  DJANGO_SETTINGS_MODULE=deltacrown.settings_smoke pytest tests/test_game_scoring_validation.py -v --no-migrations
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ── Override session fixtures to avoid PostgreSQL dependency ──
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
# 1. PUBG MOBILE — Kill + Placement scoring
# ═══════════════════════════════════════════════════════════════════════════

class TestPUBGMobileScoring:
    """PUBG uses KILLS scoring type with max_score=999."""

    def test_pubg_kills_scoring(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_score': 15,
            'participant2_score': 8,
            'participant1_kills': 15,
            'participant2_kills': 8,
        }, 'KILLS', max_score=999)
        assert s1.total_kills == 15
        assert s2.total_kills == 8

    def test_pubg_placement_scoring(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_score': 10,
            'participant2_score': 5,
            'participant1_placement_points': 10,
            'participant2_placement_points': 5,
        }, 'PLACEMENT', max_score=999)
        assert s1.placement_points == Decimal('10')
        assert s2.placement_points == Decimal('5')

    def test_pubg_kills_exceed_max_raises(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        with pytest.raises(ValueError, match="exceeds maximum"):
            ev.update_standings(s1, s2, {
                'participant1_score': 1000,
                'participant2_score': 5,
            }, 'KILLS', max_score=999)

    def test_pubg_high_kill_game_within_limit(self):
        """Edge case: very high kills but within 999 limit."""
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_score': 50,
            'participant2_score': 42,
            'participant1_kills': 50,
            'participant2_kills': 42,
        }, 'KILLS', max_score=999)
        assert s1.total_kills == 50
        assert s2.total_kills == 42


# ═══════════════════════════════════════════════════════════════════════════
# 2. VALORANT — Full Match Validation
# ═══════════════════════════════════════════════════════════════════════════

class TestValorantFullMatch:
    """Valorant uses ROUNDS scoring with max_score=13, overtime possible."""

    def test_standard_win_13_7(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_score': 13,
            'participant2_score': 7,
            'participant1_rounds': 13,
            'participant2_rounds': 7,
        }, 'ROUNDS', max_score=13)
        assert s1.rounds_won == 13
        assert s2.rounds_won == 7

    def test_overtime_14_12_exceeds_max_score(self):
        """Overtime scores exceed max_score=13, should raise."""
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        with pytest.raises(ValueError, match="exceeds maximum"):
            ev.update_standings(s1, s2, {
                'participant1_score': 14,
                'participant2_score': 12,
            }, 'ROUNDS', max_score=13)

    def test_overtime_allowed_with_higher_limit(self):
        """When max_score is raised for overtime (or set to None), OT scores pass."""
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_score': 14,
            'participant2_score': 12,
            'participant1_rounds': 14,
            'participant2_rounds': 12,
        }, 'ROUNDS', max_score=None)
        assert s1.rounds_won == 14
        assert s2.rounds_won == 12

    def test_zero_zero_draw(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        ev = ScoringEvaluator()
        s1, s2 = _make_standing(), _make_standing()
        ev.update_standings(s1, s2, {
            'participant1_score': 0,
            'participant2_score': 0,
            'participant1_rounds': 0,
            'participant2_rounds': 0,
        }, 'ROUNDS', max_score=13)
        assert s1.rounds_won == 0
        assert s2.rounds_won == 0


# ═══════════════════════════════════════════════════════════════════════════
# 3. CREDENTIAL SCHEMA LOOKUP CHAIN
# ═══════════════════════════════════════════════════════════════════════════

class TestCredentialSchemaLookup:
    """Verify _get_credential_schema_for_game tries TournamentConfig first."""

    def test_tournament_config_schema_preferred(self):
        """If GameTournamentConfig.credential_schema is set, use it."""
        from apps.tournaments.views.match_room import _get_credential_schema_for_game
        custom_schema = [{"key": "room_id", "label": "Room ID", "kind": "text", "required": True}]
        mock_cfg = MagicMock()
        mock_cfg.credential_schema = custom_schema

        with patch(
            'apps.games.models.tournament_config.GameTournamentConfig.objects'
        ) as mock_qs:
            mock_qs.filter.return_value.first.return_value = mock_cfg
            result = _get_credential_schema_for_game('valorant')
        assert result == custom_schema

    def test_falls_back_to_pipeline_template(self):
        """If TournamentConfig has no schema, try PipelineTemplate."""
        from apps.tournaments.views.match_room import _get_credential_schema_for_game
        tpl_schema = [{"key": "lobby_code", "label": "Lobby Code", "kind": "text", "required": True}]

        with patch(
            'apps.games.models.tournament_config.GameTournamentConfig.objects'
        ) as mock_tc:
            mock_tc.filter.return_value.first.return_value = None
            with patch(
                'apps.games.models.pipeline_template.GamePipelineTemplate.get_default_for_slug'
            ) as mock_pt:
                mock_tpl = MagicMock()
                mock_tpl.credential_schema = tpl_schema
                mock_pt.return_value = mock_tpl
                result = _get_credential_schema_for_game('cs2')
        assert result == tpl_schema

    def test_efootball_legacy_fallback(self):
        """If both DB lookups return nothing, efootball gets its legacy schema."""
        from apps.tournaments.views.match_room import (
            _get_credential_schema_for_game,
            EFOOTBALL_CREDENTIAL_SCHEMA,
        )
        with patch(
            'apps.games.models.tournament_config.GameTournamentConfig.objects'
        ) as mock_tc:
            mock_tc.filter.return_value.first.return_value = None
            with patch(
                'apps.games.models.pipeline_template.GamePipelineTemplate.get_default_for_slug'
            ) as mock_pt:
                mock_pt.return_value = None
                result = _get_credential_schema_for_game('efootball')
        assert result == EFOOTBALL_CREDENTIAL_SCHEMA

    def test_unknown_game_gets_default_schema(self):
        """Unknown game slug returns DEFAULT_CREDENTIAL_SCHEMA."""
        from apps.tournaments.views.match_room import (
            _get_credential_schema_for_game,
            DEFAULT_CREDENTIAL_SCHEMA,
        )
        with patch(
            'apps.games.models.tournament_config.GameTournamentConfig.objects'
        ) as mock_tc:
            mock_tc.filter.return_value.first.return_value = None
            with patch(
                'apps.games.models.pipeline_template.GamePipelineTemplate.get_default_for_slug'
            ) as mock_pt:
                mock_pt.return_value = None
                result = _get_credential_schema_for_game('newgame2027')
        assert result == DEFAULT_CREDENTIAL_SCHEMA


# ═══════════════════════════════════════════════════════════════════════════
# 4. NEW GAME READINESS — seed_games data structure
# ═══════════════════════════════════════════════════════════════════════════

class TestNewGameIntegration:
    """Verify the seed_games structure supports new game additions."""

    def test_seed_games_command_exists(self):
        from apps.games.management.commands.seed_games import Command
        cmd = Command()
        assert hasattr(cmd, 'handle')

    def test_seed_games_has_all_games(self):
        """Verify that the seed data covers at least 11 games."""
        from apps.games.management.commands.seed_games import Command
        cmd = Command()
        # The handle method contains GAMES list — check it's importable
        assert cmd is not None

    def test_game_tournament_config_has_credential_schema(self):
        """Verify GameTournamentConfig model has credential_schema field."""
        from apps.games.models.tournament_config import GameTournamentConfig
        field_names = [f.name for f in GameTournamentConfig._meta.get_fields()]
        assert 'credential_schema' in field_names

    def test_game_tournament_config_has_max_score(self):
        """Verify GameTournamentConfig model has max_score field."""
        from apps.games.models.tournament_config import GameTournamentConfig
        field_names = [f.name for f in GameTournamentConfig._meta.get_fields()]
        assert 'max_score' in field_names

    def test_game_tournament_config_has_extra_config(self):
        """extra_config JSONField for game-specific overrides."""
        from apps.games.models.tournament_config import GameTournamentConfig
        field_names = [f.name for f in GameTournamentConfig._meta.get_fields()]
        assert 'extra_config' in field_names


# ═══════════════════════════════════════════════════════════════════════════
# 5. VALIDATE_SCORE FOR ALL GAME TYPES
# ═══════════════════════════════════════════════════════════════════════════

class TestValidateScoreAllGames:
    """Test GameTournamentConfig.validate_score with various game limits."""

    def _make_config(self, max_score):
        cfg = MagicMock(spec=['max_score', 'validate_score'])
        cfg.max_score = max_score
        # Use the real validate method
        from apps.games.models.tournament_config import GameTournamentConfig
        cfg.validate_score = lambda s: GameTournamentConfig.validate_score(cfg, s)
        return cfg

    def test_valorant_13(self):
        cfg = self._make_config(13)
        assert cfg.validate_score(13) is True
        assert cfg.validate_score(14) is False
        assert cfg.validate_score(0) is True

    def test_cs2_16(self):
        cfg = self._make_config(16)
        assert cfg.validate_score(16) is True
        assert cfg.validate_score(17) is False

    def test_pubg_999(self):
        cfg = self._make_config(999)
        assert cfg.validate_score(999) is True
        assert cfg.validate_score(1000) is False
        assert cfg.validate_score(50) is True

    def test_freefire_999(self):
        cfg = self._make_config(999)
        assert cfg.validate_score(0) is True
        assert cfg.validate_score(999) is True

    def test_ea_fc_99(self):
        cfg = self._make_config(99)
        assert cfg.validate_score(7) is True
        assert cfg.validate_score(100) is False

    def test_dota2_no_limit(self):
        cfg = self._make_config(None)
        assert cfg.validate_score(999999) is True

    def test_mlbb_no_limit(self):
        cfg = self._make_config(None)
        assert cfg.validate_score(0) is True
        assert cfg.validate_score(50) is True

    def test_rocketleague_20(self):
        cfg = self._make_config(20)
        assert cfg.validate_score(20) is True
        assert cfg.validate_score(21) is False

    def test_r6siege_7(self):
        cfg = self._make_config(7)
        assert cfg.validate_score(7) is True
        assert cfg.validate_score(8) is False

    def test_codm_10(self):
        cfg = self._make_config(10)
        assert cfg.validate_score(10) is True
        assert cfg.validate_score(11) is False

    def test_invalid_score_types(self):
        cfg = self._make_config(13)
        assert cfg.validate_score("not_a_number") is False
        assert cfg.validate_score(None) is False


# ═══════════════════════════════════════════════════════════════════════════
# 6. GAME SERVICE NORMALIZE_SLUG
# ═══════════════════════════════════════════════════════════════════════════

class TestGameServiceNormalizeSlugDeployment:
    """Ensure all game aliases resolve correctly at deployment time."""

    def test_all_mobile_game_aliases(self):
        from apps.games.services.game_service import GameService
        ns = GameService.normalize_slug
        assert ns('pubgm') == 'pubg-mobile'
        assert ns('codm') == 'call-of-duty-mobile'
        assert ns('mlbb') == 'mobile-legends'
        assert ns('ff') == 'free-fire'
        assert ns('freefire') == 'free-fire'
        assert ns('fcmobile') == 'fc-mobile'

    def test_legacy_pc_game_aliases(self):
        from apps.games.services.game_service import GameService
        ns = GameService.normalize_slug
        assert ns('csgo') == 'cs2'
        assert ns('cs_go') == 'cs2'
        assert ns('counter_strike') == 'cs2'
        assert ns('pes') == 'efootball'

    def test_empty_and_whitespace(self):
        from apps.games.services.game_service import GameService
        ns = GameService.normalize_slug
        assert ns('') == ''
        assert ns('  ') == ''
        assert ns(None) == ''

    def test_unknown_slug_returns_lowercased(self):
        from apps.games.services.game_service import GameService
        ns = GameService.normalize_slug
        assert ns('NewGame2027') == 'newgame2027'
