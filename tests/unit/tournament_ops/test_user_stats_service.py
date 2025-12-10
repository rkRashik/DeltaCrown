"""
Unit Tests for User Stats Service

Phase 8, Epic 8.2: User Stats Service
Tests for UserStatsService business logic layer.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from apps.tournament_ops.services.user_stats_service import UserStatsService
from apps.tournament_ops.dtos.user_stats import (
    UserStatsDTO,
    UserStatsSummaryDTO,
    MatchStatsUpdateDTO,
)
from apps.tournament_ops.exceptions import ValidationError


class TestUserStatsService:
    """Test UserStatsService business logic methods."""
    
    @pytest.fixture
    def mock_adapter(self):
        """Fixture for mock adapter."""
        return MagicMock()
    
    @pytest.fixture
    def service(self, mock_adapter):
        """Fixture for UserStatsService with mock adapter."""
        return UserStatsService(adapter=mock_adapter)
    
    @pytest.fixture
    def sample_stats_dto(self):
        """Fixture for sample UserStatsDTO."""
        return UserStatsDTO(
            user_id=101,
            game_slug="valorant",
            matches_played=10,
            matches_won=6,
            matches_lost=4,
            matches_drawn=0,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("60.00"),
            total_kills=100,
            total_deaths=80,
            kd_ratio=Decimal("1.25"),
            last_match_at=datetime(2025, 12, 10, tzinfo=timezone.utc),
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 10, tzinfo=timezone.utc),
        )
    
    def test_get_user_stats_success(self, service, mock_adapter, sample_stats_dto):
        """Test get_user_stats() returns DTO from adapter."""
        mock_adapter.get_user_stats.return_value = sample_stats_dto
        
        result = service.get_user_stats(user_id=101, game_slug="valorant")
        
        assert result == sample_stats_dto
        mock_adapter.get_user_stats.assert_called_once_with(
            user_id=101,
            game_slug="valorant"
        )
    
    def test_get_user_stats_not_found(self, service, mock_adapter):
        """Test get_user_stats() returns None when not found."""
        mock_adapter.get_user_stats.return_value = None
        
        result = service.get_user_stats(user_id=999, game_slug="valorant")
        
        assert result is None
    
    def test_get_user_stats_invalid_user_id(self, service):
        """Test get_user_stats() validates user_id."""
        with pytest.raises(ValidationError, match="user_id must be positive"):
            service.get_user_stats(user_id=0, game_slug="valorant")
    
    def test_get_user_stats_invalid_game_slug(self, service):
        """Test get_user_stats() validates game_slug."""
        with pytest.raises(ValidationError, match="game_slug cannot be empty"):
            service.get_user_stats(user_id=101, game_slug="")
    
    def test_get_all_user_stats(self, service, mock_adapter, sample_stats_dto):
        """Test get_all_user_stats() returns list of DTOs."""
        mock_adapter.get_all_user_stats.return_value = [sample_stats_dto]
        
        results = service.get_all_user_stats(user_id=101)
        
        assert len(results) == 1
        assert results[0] == sample_stats_dto
        mock_adapter.get_all_user_stats.assert_called_once_with(user_id=101)
    
    def test_update_stats_for_match_success(self, service, mock_adapter, sample_stats_dto):
        """Test update_stats_for_match() with valid MatchStatsUpdateDTO."""
        match_dto = MatchStatsUpdateDTO(
            user_id=101,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            kills=25,
            deaths=18,
            assists=10,
            mvp=True,
            match_id=1001,
        )
        
        mock_adapter.increment_stats_for_match.return_value = sample_stats_dto
        
        result = service.update_stats_for_match(match_dto)
        
        assert result == sample_stats_dto
        mock_adapter.increment_stats_for_match.assert_called_once_with(
            user_id=101,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            kills=25,
            deaths=18
        )
    
    def test_update_stats_for_match_validation_error(self, service):
        """Test update_stats_for_match() rejects invalid DTO."""
        invalid_dto = MatchStatsUpdateDTO(
            user_id=None,  # Invalid
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            kills=25,
            deaths=18,
            assists=10,
            mvp=False,
            match_id=1001,
        )
        
        with pytest.raises(ValidationError):
            service.update_stats_for_match(invalid_dto)
    
    def test_update_stats_for_match_batch(self, service, mock_adapter, sample_stats_dto):
        """Test update_stats_for_match_batch() updates multiple users."""
        match_dtos = [
            MatchStatsUpdateDTO(
                user_id=101,
                game_slug="valorant",
                is_winner=True,
                is_draw=False,
                kills=25,
                deaths=18,
                assists=10,
                mvp=True,
                match_id=1001,
            ),
            MatchStatsUpdateDTO(
                user_id=102,
                game_slug="valorant",
                is_winner=False,
                is_draw=False,
                kills=18,
                deaths=25,
                assists=5,
                mvp=False,
                match_id=1001,
            ),
        ]
        
        mock_adapter.increment_stats_for_match.return_value = sample_stats_dto
        
        results = service.update_stats_for_match_batch(match_dtos)
        
        assert len(results) == 2
        assert mock_adapter.increment_stats_for_match.call_count == 2
    
    def test_update_stats_for_match_batch_partial_success(self, service, mock_adapter, sample_stats_dto):
        """Test update_stats_for_match_batch() continues on individual errors."""
        match_dtos = [
            MatchStatsUpdateDTO(
                user_id=101,
                game_slug="valorant",
                is_winner=True,
                is_draw=False,
                kills=25,
                deaths=18,
                assists=10,
                mvp=True,
                match_id=1001,
            ),
            MatchStatsUpdateDTO(
                user_id=None,  # Invalid
                game_slug="valorant",
                is_winner=False,
                is_draw=False,
                kills=18,
                deaths=25,
                assists=5,
                mvp=False,
                match_id=1001,
            ),
        ]
        
        mock_adapter.increment_stats_for_match.return_value = sample_stats_dto
        
        results = service.update_stats_for_match_batch(match_dtos)
        
        # Only 1 valid update should succeed
        assert len(results) == 1
        assert results[0] == sample_stats_dto
    
    def test_get_top_stats_for_game(self, service, mock_adapter, sample_stats_dto):
        """Test get_top_stats_for_game() returns ordered leaderboard."""
        mock_adapter.get_stats_by_game.return_value = [sample_stats_dto]
        
        results = service.get_top_stats_for_game(game_slug="valorant", limit=100)
        
        assert len(results) == 1
        mock_adapter.get_stats_by_game.assert_called_once_with(
            game_slug="valorant",
            limit=100
        )
    
    def test_get_top_stats_for_game_invalid_limit(self, service):
        """Test get_top_stats_for_game() validates limit."""
        with pytest.raises(ValidationError, match="limit must be between 1 and 1000"):
            service.get_top_stats_for_game(game_slug="valorant", limit=0)
        
        with pytest.raises(ValidationError, match="limit must be between 1 and 1000"):
            service.get_top_stats_for_game(game_slug="valorant", limit=1001)
    
    def test_record_tournament_completion(self, service, mock_adapter, sample_stats_dto):
        """Test record_tournament_completion() updates tournament stats."""
        mock_adapter.increment_tournament_participation.return_value = sample_stats_dto
        
        result = service.record_tournament_completion(
            user_id=101,
            game_slug="valorant",
            is_winner=True
        )
        
        assert result == sample_stats_dto
        mock_adapter.increment_tournament_participation.assert_called_once_with(
            user_id=101,
            game_slug="valorant",
            is_winner=True
        )
    
    def test_get_user_summary_single_game(self, service, mock_adapter, sample_stats_dto):
        """Test get_user_summary() for single game."""
        mock_adapter.get_user_stats.return_value = sample_stats_dto
        
        summary = service.get_user_summary(user_id=101, game_slug="valorant")
        
        assert summary["user_id"] == 101
        assert summary["game_slug"] == "valorant"
        assert summary["total_matches"] == 10
        assert summary["total_wins"] == 6
        assert summary["win_rate"] == Decimal("60.00")
        assert summary["has_stats"] is True
    
    def test_get_user_summary_all_games(self, service, mock_adapter, sample_stats_dto):
        """Test get_user_summary() aggregates all games."""
        # Mock two different games
        stats_valorant = UserStatsDTO(
            user_id=101,
            game_slug="valorant",
            matches_played=10,
            matches_won=6,
            matches_lost=4,
            matches_drawn=0,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("60.00"),
            total_kills=100,
            total_deaths=80,
            kd_ratio=Decimal("1.25"),
            last_match_at=datetime(2025, 12, 10, tzinfo=timezone.utc),
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 10, tzinfo=timezone.utc),
        )
        
        stats_csgo = UserStatsDTO(
            user_id=101,
            game_slug="csgo",
            matches_played=20,
            matches_won=12,
            matches_lost=8,
            matches_drawn=0,
            tournaments_played=3,
            tournaments_won=1,
            win_rate=Decimal("60.00"),
            total_kills=200,
            total_deaths=160,
            kd_ratio=Decimal("1.25"),
            last_match_at=datetime(2025, 12, 10, tzinfo=timezone.utc),
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 10, tzinfo=timezone.utc),
        )
        
        mock_adapter.get_all_user_stats.return_value = [stats_valorant, stats_csgo]
        
        summary = service.get_user_summary(user_id=101)
        
        assert summary["user_id"] == 101
        assert summary["game_slug"] is None  # All games
        assert summary["total_matches"] == 30  # 10 + 20
        assert summary["total_wins"] == 18    # 6 + 12
        assert summary["total_tournaments"] == 5  # 2 + 3
        assert summary["games_played"] == 2
        assert summary["has_stats"] is True
    
    def test_get_user_summary_no_stats(self, service, mock_adapter):
        """Test get_user_summary() with no stats."""
        mock_adapter.get_all_user_stats.return_value = []
        
        summary = service.get_user_summary(user_id=999)
        
        assert summary["user_id"] == 999
        assert summary["has_stats"] is False
        assert summary["total_matches"] == 0
    
    def test_architecture_compliance_no_orm_imports(self):
        """Test UserStatsService has NO ORM imports."""
        import inspect
        from apps.tournament_ops.services import user_stats_service
        
        source = inspect.getsource(user_stats_service)
        
        # Verify no Django ORM imports
        assert "from django.db" not in source
        assert "from apps.leaderboards.models" not in source
        assert "from apps.core.models" not in source
        
        # Verify uses adapter pattern
        assert "UserStatsAdapter" in source or "adapter" in source
