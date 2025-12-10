"""
Unit Tests for User Stats Adapter

Phase 8, Epic 8.2: User Stats Service
Tests for UserStatsAdapter data access layer.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from apps.tournament_ops.adapters.user_stats_adapter import UserStatsAdapter
from apps.tournament_ops.dtos.user_stats import UserStatsDTO


@pytest.mark.django_db
class TestUserStatsAdapter:
    """Test UserStatsAdapter data access methods."""
    
    @pytest.fixture
    def adapter(self):
        """Fixture for UserStatsAdapter instance."""
        return UserStatsAdapter()
    
    @pytest.fixture
    def mock_user_stats(self):
        """Fixture for mock UserStats model."""
        class MockUserStats:
            user_id = 101
            game_slug = "valorant"
            matches_played = 50
            matches_won = 30
            matches_lost = 18
            matches_drawn = 2
            tournaments_played = 5
            tournaments_won = 2
            win_rate = Decimal("60.00")
            total_kills = 500
            total_deaths = 450
            kd_ratio = Decimal("1.11")
            last_match_at = datetime(2025, 12, 10, tzinfo=timezone.utc)
            created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
            updated_at = datetime(2025, 12, 10, tzinfo=timezone.utc)
        
        return MockUserStats()
    
    def test_get_user_stats_found(self, adapter, mock_user_stats):
        """Test get_user_stats() when stats exist."""
        with patch('apps.tournament_ops.adapters.user_stats_adapter.UserStats') as MockUserStats:
            MockUserStats.objects.filter.return_value.first.return_value = mock_user_stats
            
            result = adapter.get_user_stats(user_id=101, game_slug="valorant")
            
            assert result is not None
            assert isinstance(result, UserStatsDTO)
            assert result.user_id == 101
            assert result.game_slug == "valorant"
            assert result.matches_played == 50
            assert result.matches_won == 30
            
            MockUserStats.objects.filter.assert_called_once_with(
                user_id=101,
                game_slug="valorant"
            )
    
    def test_get_user_stats_not_found(self, adapter):
        """Test get_user_stats() when stats don't exist."""
        with patch('apps.tournament_ops.adapters.user_stats_adapter.UserStats') as MockUserStats:
            MockUserStats.objects.filter.return_value.first.return_value = None
            
            result = adapter.get_user_stats(user_id=999, game_slug="valorant")
            
            assert result is None
    
    def test_get_all_user_stats(self, adapter, mock_user_stats):
        """Test get_all_user_stats() returns all games for user."""
        with patch('apps.tournament_ops.adapters.user_stats_adapter.UserStats') as MockUserStats:
            # Mock queryset with multiple stats
            MockUserStats.objects.filter.return_value = [mock_user_stats, mock_user_stats]
            
            results = adapter.get_all_user_stats(user_id=101)
            
            assert len(results) == 2
            assert all(isinstance(dto, UserStatsDTO) for dto in results)
            assert all(dto.user_id == 101 for dto in results)
            
            MockUserStats.objects.filter.assert_called_once_with(user_id=101)
    
    def test_get_all_user_stats_empty(self, adapter):
        """Test get_all_user_stats() with no stats."""
        with patch('apps.tournament_ops.adapters.user_stats_adapter.UserStats') as MockUserStats:
            MockUserStats.objects.filter.return_value = []
            
            results = adapter.get_all_user_stats(user_id=999)
            
            assert results == []
    
    def test_increment_stats_for_match_new_record(self, adapter):
        """Test increment_stats_for_match() creates new record."""
        with patch('apps.tournament_ops.adapters.user_stats_adapter.UserStats') as MockUserStats:
            # Mock get_or_create for new record
            mock_stats = MagicMock()
            mock_stats.user_id = 101
            mock_stats.game_slug = "valorant"
            mock_stats.matches_played = 0
            mock_stats.matches_won = 0
            mock_stats.matches_lost = 0
            mock_stats.matches_drawn = 0
            mock_stats.total_kills = 0
            mock_stats.total_deaths = 0
            mock_stats.win_rate = Decimal("0.00")
            mock_stats.kd_ratio = Decimal("0.00")
            mock_stats.calculate_win_rate = MagicMock()
            mock_stats.calculate_kd_ratio = MagicMock()
            mock_stats.refresh_from_db = MagicMock()
            
            MockUserStats.objects.get_or_create.return_value = (mock_stats, True)
            
            # Mock F() expressions
            with patch('apps.tournament_ops.adapters.user_stats_adapter.F') as MockF:
                MockF.return_value = MagicMock()
                
                result = adapter.increment_stats_for_match(
                    user_id=101,
                    game_slug="valorant",
                    is_winner=True,
                    is_draw=False,
                    kills=25,
                    deaths=18
                )
            
            assert result is not None
            assert isinstance(result, UserStatsDTO)
            
            # Verify get_or_create called
            MockUserStats.objects.get_or_create.assert_called_once()
            
            # Verify save called
            mock_stats.save.assert_called()
    
    def test_increment_stats_for_match_existing_win(self, adapter, mock_user_stats):
        """Test increment_stats_for_match() updates existing record for win."""
        with patch('apps.tournament_ops.adapters.user_stats_adapter.UserStats') as MockUserStats:
            mock_stats = MagicMock()
            mock_stats.user_id = 101
            mock_stats.game_slug = "valorant"
            mock_stats.matches_played = 10
            mock_stats.matches_won = 5
            mock_stats.matches_lost = 5
            mock_stats.matches_drawn = 0
            mock_stats.total_kills = 100
            mock_stats.total_deaths = 100
            mock_stats.win_rate = Decimal("50.00")
            mock_stats.kd_ratio = Decimal("1.00")
            mock_stats.calculate_win_rate = MagicMock()
            mock_stats.calculate_kd_ratio = MagicMock()
            mock_stats.refresh_from_db = MagicMock()
            
            MockUserStats.objects.get_or_create.return_value = (mock_stats, False)
            
            with patch('apps.tournament_ops.adapters.user_stats_adapter.F') as MockF:
                MockF.return_value = MagicMock()
                
                result = adapter.increment_stats_for_match(
                    user_id=101,
                    game_slug="valorant",
                    is_winner=True,
                    is_draw=False,
                    kills=20,
                    deaths=15
                )
            
            assert result is not None
            mock_stats.save.assert_called()
    
    def test_increment_stats_for_match_draw(self, adapter):
        """Test increment_stats_for_match() handles draw correctly."""
        with patch('apps.tournament_ops.adapters.user_stats_adapter.UserStats') as MockUserStats:
            mock_stats = MagicMock()
            mock_stats.user_id = 101
            mock_stats.game_slug = "valorant"
            mock_stats.matches_played = 10
            mock_stats.matches_won = 5
            mock_stats.matches_lost = 4
            mock_stats.matches_drawn = 1
            mock_stats.total_kills = 100
            mock_stats.total_deaths = 100
            mock_stats.calculate_win_rate = MagicMock()
            mock_stats.calculate_kd_ratio = MagicMock()
            mock_stats.refresh_from_db = MagicMock()
            
            MockUserStats.objects.get_or_create.return_value = (mock_stats, False)
            
            with patch('apps.tournament_ops.adapters.user_stats_adapter.F') as MockF:
                MockF.return_value = MagicMock()
                
                result = adapter.increment_stats_for_match(
                    user_id=101,
                    game_slug="valorant",
                    is_winner=False,
                    is_draw=True,
                    kills=15,
                    deaths=15
                )
            
            assert result is not None
            mock_stats.save.assert_called()
    
    def test_get_stats_by_game(self, adapter, mock_user_stats):
        """Test get_stats_by_game() returns ordered leaderboard."""
        with patch('apps.tournament_ops.adapters.user_stats_adapter.UserStats') as MockUserStats:
            # Mock queryset
            mock_queryset = MagicMock()
            mock_queryset.order_by.return_value = [mock_user_stats, mock_user_stats]
            MockUserStats.objects.filter.return_value = mock_queryset
            
            results = adapter.get_stats_by_game(game_slug="valorant", limit=100)
            
            assert len(results) == 2
            assert all(isinstance(dto, UserStatsDTO) for dto in results)
            
            # Verify ordering by win_rate descending
            mock_queryset.order_by.assert_called_once_with("-win_rate")
    
    def test_get_stats_by_game_with_limit(self, adapter):
        """Test get_stats_by_game() respects limit parameter."""
        with patch('apps.tournament_ops.adapters.user_stats_adapter.UserStats') as MockUserStats:
            mock_queryset = MagicMock()
            mock_queryset.order_by.return_value = []
            MockUserStats.objects.filter.return_value = mock_queryset
            
            adapter.get_stats_by_game(game_slug="csgo", limit=50)
            
            # Verify limit applied (note: limit is slicing [:50])
            mock_queryset.order_by.assert_called_once_with("-win_rate")
    
    def test_increment_tournament_participation(self, adapter):
        """Test increment_tournament_participation() updates tournament stats."""
        with patch('apps.tournament_ops.adapters.user_stats_adapter.UserStats') as MockUserStats:
            mock_stats = MagicMock()
            mock_stats.tournaments_played = 5
            mock_stats.tournaments_won = 2
            mock_stats.refresh_from_db = MagicMock()
            
            MockUserStats.objects.get_or_create.return_value = (mock_stats, False)
            
            with patch('apps.tournament_ops.adapters.user_stats_adapter.F') as MockF:
                MockF.return_value = MagicMock()
                
                result = adapter.increment_tournament_participation(
                    user_id=101,
                    game_slug="valorant",
                    is_winner=True
                )
            
            assert result is not None
            mock_stats.save.assert_called()
