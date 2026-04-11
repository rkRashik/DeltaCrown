"""
Phase 6+7 Tests — Cross-Game Refactoring & Backend Code Quality

Tests for:
1. ScoringEvaluator service (dispatch table, all scoring types)
2. GameMapPool model (get_active_maps, get_active_maps_by_slug)
3. GamePipelineTemplate model (get_default_for_game)
4. Dashboard module split (helpers, command_center imports)
5. Match room _get_map_pool_for_game fallback chain

Run with:
  DJANGO_SETTINGS_MODULE=deltacrown.settings_smoke pytest tests/test_phase6_phase7.py -v --no-migrations
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ── Override session fixtures to avoid PostgreSQL dependency ────────────────
@pytest.fixture(scope='session')
def django_db_setup():
    """No-op override: these tests are pure mock tests, no DB needed."""
    pass

@pytest.fixture(scope='session', autouse=True)
def enforce_test_database():
    """No-op override: skip real DB setup."""
    yield

@pytest.fixture(scope='session', autouse=True)
def setup_test_schema():
    """No-op override: skip schema creation."""
    yield


# ═══════════════════════════════════════════════════════════════════════════
# 1. ScoringEvaluator Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestScoringEvaluator:
    """Verify the ScoringEvaluator dispatch-table replaces the old if/elif."""

    def _make_standing(self):
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

    def _get_evaluator(self):
        from apps.games.services.scoring_evaluator import ScoringEvaluator
        return ScoringEvaluator()

    def test_goals_scoring(self):
        ev = self._get_evaluator()
        s1, s2 = self._make_standing(), self._make_standing()
        data = {'participant1_score': 3, 'participant2_score': 1}
        ev.update_standings(s1, s2, data, 'GOALS')
        assert s1.goals_for == 3
        assert s1.goals_against == 1
        assert s1.goal_difference == 2
        assert s2.goals_for == 1
        assert s2.goals_against == 3
        assert s2.goal_difference == -2

    def test_rounds_scoring(self):
        ev = self._get_evaluator()
        s1, s2 = self._make_standing(), self._make_standing()
        data = {
            'participant1_rounds': 13, 'participant2_rounds': 7,
            'participant1_kills': 20, 'participant1_deaths': 15,
            'participant2_kills': 12, 'participant2_deaths': 18,
        }
        ev.update_standings(s1, s2, data, 'ROUNDS')
        assert s1.rounds_won == 13
        assert s1.rounds_lost == 7
        assert s1.round_difference == 6
        assert s1.total_kills == 20
        assert s1.total_deaths == 15
        assert s2.rounds_won == 7
        assert s2.rounds_lost == 13
        assert s2.total_kills == 12

    def test_placement_scoring(self):
        ev = self._get_evaluator()
        s1, s2 = self._make_standing(), self._make_standing()
        data = {
            'participant1_kills': 8,
            'participant1_placement_points': 12,
            'participant2_kills': 5,
            'participant2_placement_points': 6,
        }
        ev.update_standings(s1, s2, data, 'PLACEMENT')
        assert s1.total_kills == 8
        assert s1.placement_points == Decimal('12')
        assert s2.total_kills == 5
        assert s2.placement_points == Decimal('6')

    def test_kills_scoring_uses_br_handler(self):
        ev = self._get_evaluator()
        s1, s2 = self._make_standing(), self._make_standing()
        data = {
            'participant1_kills': 10,
            'participant1_placement_points': 8,
            'participant2_kills': 3,
            'participant2_placement_points': 2,
        }
        ev.update_standings(s1, s2, data, 'KILLS')
        assert s1.total_kills == 10
        assert s2.total_kills == 3

    def test_win_loss_moba(self):
        ev = self._get_evaluator()
        s1, s2 = self._make_standing(), self._make_standing()
        data = {
            'participant1_kills': 15, 'participant1_deaths': 5, 'participant1_assists': 10,
            'participant1_score': 100,
            'participant2_kills': 8, 'participant2_deaths': 12, 'participant2_assists': 6,
            'participant2_score': 60,
        }
        ev.update_standings(s1, s2, data, 'WIN_LOSS', game_category='MOBA')
        assert s1.total_kills == 15
        assert s1.total_deaths == 5
        assert s1.total_assists == 10
        s1.calculate_kda.assert_called_once()
        assert s1.total_score == 100
        assert s2.total_kills == 8
        assert s2.total_score == 60

    def test_win_loss_non_moba_noop(self):
        ev = self._get_evaluator()
        s1, s2 = self._make_standing(), self._make_standing()
        data = {'participant1_score': 5, 'participant2_score': 3}
        ev.update_standings(s1, s2, data, 'WIN_LOSS', game_category='FPS')
        # win_loss handler doesn't modify kills/rounds fields
        assert s1.total_kills == 0
        assert s1.rounds_won == 0

    def test_unknown_scoring_type_falls_back_to_win_loss(self):
        ev = self._get_evaluator()
        s1, s2 = self._make_standing(), self._make_standing()
        data = {'participant1_score': 5, 'participant2_score': 3}
        # Should not raise
        ev.update_standings(s1, s2, data, 'UNKNOWN_TYPE')
        assert s1.total_kills == 0

    def test_singleton_import(self):
        from apps.games.services.scoring_evaluator import scoring_evaluator
        assert scoring_evaluator is not None


# ═══════════════════════════════════════════════════════════════════════════
# 2. GameMapPool Model Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGameMapPoolModel:
    """Verify GameMapPool model structure and class methods."""

    def test_model_can_be_imported(self):
        from apps.games.models.map_pool import GameMapPool
        assert hasattr(GameMapPool, 'get_active_maps')
        assert hasattr(GameMapPool, 'get_active_maps_by_slug')

    def test_meta_table_name(self):
        from apps.games.models.map_pool import GameMapPool
        assert GameMapPool._meta.db_table == 'games_map_pool'

    def test_meta_ordering(self):
        from apps.games.models.map_pool import GameMapPool
        assert GameMapPool._meta.ordering == ['game', 'order', 'map_name']

    def test_unique_together(self):
        from apps.games.models.map_pool import GameMapPool
        ut = GameMapPool._meta.unique_together
        assert ('game', 'map_code') in ut


# ═══════════════════════════════════════════════════════════════════════════
# 3. GamePipelineTemplate Model Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGamePipelineTemplateModel:
    """Verify GamePipelineTemplate model structure."""

    def test_model_can_be_imported(self):
        from apps.games.models.pipeline_template import GamePipelineTemplate
        assert hasattr(GamePipelineTemplate, 'get_default_for_game')
        assert hasattr(GamePipelineTemplate, 'get_default_for_slug')

    def test_meta_table_name(self):
        from apps.games.models.pipeline_template import GamePipelineTemplate
        assert GamePipelineTemplate._meta.db_table == 'games_pipeline_template'

    def test_pipeline_mode_choices(self):
        from apps.games.models.pipeline_template import GamePipelineTemplate
        field = GamePipelineTemplate._meta.get_field('pipeline_mode')
        choice_keys = [c[0] for c in field.choices]
        assert 'veto' in choice_keys
        assert 'direct' in choice_keys

    def test_scoring_type_choices(self):
        from apps.games.models.pipeline_template import GamePipelineTemplate
        field = GamePipelineTemplate._meta.get_field('scoring_type')
        choice_keys = [c[0] for c in field.choices]
        assert 'GOALS' in choice_keys
        assert 'ROUNDS' in choice_keys
        assert 'WIN_LOSS' in choice_keys


# ═══════════════════════════════════════════════════════════════════════════
# 4. Dashboard Module Split Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDashboardModuleSplit:
    """Verify the dashboard God-class was properly split."""

    def test_helpers_module_imports(self):
        from apps.dashboard.helpers import _safe_model, _safe_qs, _safe_int
        from apps.dashboard.helpers import _build_game_lookup, _logo_url, _ts, _img_url
        from apps.dashboard.helpers import _avatar_fallback
        assert callable(_safe_model)
        assert callable(_avatar_fallback)

    def test_command_center_module_imports(self):
        from apps.dashboard.command_center import build_cc_data
        assert callable(build_cc_data)

    def test_views_imports_from_helpers(self):
        """Views module should import helpers rather than defining them inline."""
        import apps.dashboard.views as v
        # These should be imported from helpers, not defined locally
        assert hasattr(v, '_safe_model')
        assert hasattr(v, '_build_cc_data')

    def test_safe_model_returns_none_for_invalid(self):
        from apps.dashboard.helpers import _safe_model
        result = _safe_model("nonexistent.Model")
        assert result is None

    def test_safe_int_returns_default_on_error(self):
        from apps.dashboard.helpers import _safe_int
        result = _safe_int(lambda: 1 / 0, default=42)
        assert result == 42

    def test_safe_qs_returns_empty_on_error(self):
        from apps.dashboard.helpers import _safe_qs
        result = _safe_qs(lambda: 1 / 0)
        assert result == []

    def test_ts_returns_empty_for_none(self):
        from apps.dashboard.helpers import _ts
        from datetime import datetime
        assert _ts(None, datetime.now()) == ''

    def test_avatar_fallback_generates_url(self):
        from apps.dashboard.helpers import _avatar_fallback
        url = _avatar_fallback("Test User")
        assert 'ui-avatars.com' in url
        assert 'Test' in url

    def test_build_cc_data_basic_structure(self):
        """Verify build_cc_data returns the expected top-level keys."""
        from apps.dashboard.command_center import build_cc_data
        from datetime import datetime

        user = MagicMock()
        user.username = 'testuser'
        user.id = 1
        context = {
            'profile': {'display_name': 'Test', 'slug': 'test'},
            'wallet': {'balance': 100, 'has_wallet': True},
            'next_match_info': None,
            'imminent_lobby_alert': None,
            'pending_invites': [],
            'my_organizations': [],
            'my_teams': [],
            'active_tournaments': [],
            'recent_notifications': [],
            'recent_matches': [],
            'match_stats': {},
            'social_stats': {},
            'unread_notif_count': 0,
            'game_passports': [],
            'badges': [],
            'leaderboard_data': [],
            'recruitment_positions': [],
            'featured_product': None,
            'recent_orders': [],
            'support_tickets': [],
            'active_challenges': [],
            'active_bounties': [],
        }
        now = datetime.now()
        result = build_cc_data(context, user, now)

        assert 'user' in result
        assert 'wallet' in result
        assert 'teams' in result
        assert 'tournaments' in result
        assert 'inbox' in result
        assert 'matches' in result
        assert result['user']['username'] == 'testuser'
        assert result['wallet']['balance'] == 100


# ═══════════════════════════════════════════════════════════════════════════
# 5. Match Room Map Pool Fallback Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestMatchRoomMapPoolFallback:
    """Verify _get_map_pool_for_game falls back to legacy dict."""

    def test_legacy_fallback_for_valorant(self):
        from apps.tournaments.views.match_room import _get_map_pool_for_game
        # With no DB rows, should fall back to legacy pool
        with patch('apps.games.models.map_pool.GameMapPool.get_active_maps_by_slug', return_value=[]):
            maps = _get_map_pool_for_game('valorant')
            assert 'Ascent' in maps
            assert len(maps) == 7

    def test_legacy_fallback_for_cs2(self):
        from apps.tournaments.views.match_room import _get_map_pool_for_game
        with patch('apps.games.models.map_pool.GameMapPool.get_active_maps_by_slug', return_value=[]):
            maps = _get_map_pool_for_game('cs2')
            assert 'Mirage' in maps

    def test_db_maps_take_priority(self):
        from apps.tournaments.views.match_room import _get_map_pool_for_game
        db_maps = ['CustomMap1', 'CustomMap2']
        with patch('apps.games.models.map_pool.GameMapPool.get_active_maps_by_slug', return_value=db_maps):
            maps = _get_map_pool_for_game('valorant')
            assert maps == db_maps

    def test_unknown_game_returns_empty(self):
        from apps.tournaments.views.match_room import _get_map_pool_for_game
        with patch('apps.games.models.map_pool.GameMapPool.get_active_maps_by_slug', return_value=[]):
            maps = _get_map_pool_for_game('unknown-game')
            assert maps == []

    def test_db_exception_falls_back_safely(self):
        from apps.tournaments.views.match_room import _get_map_pool_for_game
        with patch('apps.games.models.map_pool.GameMapPool.get_active_maps_by_slug', side_effect=Exception("DB error")):
            maps = _get_map_pool_for_game('valorant')
            assert 'Ascent' in maps


# ═══════════════════════════════════════════════════════════════════════════
# 6. Database Index Existence Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDatabaseIndexes:
    """Verify new composite indexes exist in model Meta."""

    def test_match_tournament_state_sched_index(self):
        from apps.tournaments.models.match import Match
        index_names = [idx.name for idx in Match._meta.indexes]
        assert 'idx_match_tourn_state_sched' in index_names

    def test_match_state_del_sched_index(self):
        from apps.tournaments.models.match import Match
        index_names = [idx.name for idx in Match._meta.indexes]
        assert 'idx_match_state_del_sched' in index_names

    def test_group_standing_participant_index(self):
        from apps.tournaments.models.group import GroupStanding
        index_names = [idx.name for idx in GroupStanding._meta.indexes if idx.name]
        assert 'idx_standing_group_participant' in index_names


# ═══════════════════════════════════════════════════════════════════════════
# 7. Bare Except Refactoring Verification
# ═══════════════════════════════════════════════════════════════════════════

class TestBareExceptRefactored:
    """Verify bare except: blocks were replaced with except Exception:."""

    def test_leaderboards_no_bare_except(self):
        import inspect
        import apps.admin.api.leaderboards as mod
        source = inspect.getsource(mod)
        lines = source.split('\n')
        bare_excepts = [i for i, l in enumerate(lines) if l.strip() == 'except:']
        assert bare_excepts == [], f"Bare except found at source lines: {bare_excepts}"

    def test_backends_no_bare_except(self):
        import inspect
        import apps.accounts.backends as mod
        source = inspect.getsource(mod)
        lines = source.split('\n')
        bare_excepts = [i for i, l in enumerate(lines) if l.strip() == 'except:']
        assert bare_excepts == [], f"Bare except found at source lines: {bare_excepts}"


# ═══════════════════════════════════════════════════════════════════════════
# 8. Games Services __init__ Exports
# ═══════════════════════════════════════════════════════════════════════════

class TestGamesServicesInit:
    """Verify the games services __init__ exports the new modules."""

    def test_scoring_evaluator_exported(self):
        from apps.games.services import ScoringEvaluator, scoring_evaluator
        assert ScoringEvaluator is not None
        assert scoring_evaluator is not None

    def test_game_service_still_exported(self):
        from apps.games.services import GameService, game_service
        assert GameService is not None
        assert game_service is not None
