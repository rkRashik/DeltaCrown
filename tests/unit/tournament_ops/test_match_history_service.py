"""
Unit Tests for MatchHistoryService

Phase 8, Epic 8.4: Match History Engine
Tests business logic with mocked adapter (no ORM dependencies).
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta

from apps.tournament_ops.services.match_history_service import MatchHistoryService
from apps.tournament_ops.dtos import (
    UserMatchHistoryDTO,
    TeamMatchHistoryDTO,
    MatchHistoryFilterDTO,
)
from apps.tournament_ops.exceptions import ValidationError


class TestMatchHistoryService:
    """Test MatchHistoryService business logic with mocked adapter."""
    
    @pytest.fixture
    def mock_adapter(self):
        """Provide mocked adapter."""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_adapter):
        """Provide service with mocked adapter."""
        return MatchHistoryService(adapter=mock_adapter)
    
    # ========================================================================
    # User Match History Recording Tests
    # ========================================================================
    
    def test_record_user_match_history_calls_adapter_with_correct_params(
        self, service, mock_adapter
    ):
        """Test service delegates to adapter with validated parameters."""
        completed_at = datetime.now()
        
        # Mock adapter response
        mock_adapter.record_user_match_history.return_value = UserMatchHistoryDTO(
            user_id=101,
            username="TestPlayer",
            match_id=123,
            tournament_id=456,
            tournament_name="Test Tournament",
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            score_summary="13-7",
            opponent_user_id=102,
            opponent_name="Opponent",
            kills=25,
            deaths=15,
            assists=10,
            had_dispute=False,
            is_forfeit=False,
            completed_at=completed_at,
        )
        
        result = service.record_user_match_history(
            user_id=101,
            match_id=123,
            tournament_id=456,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            opponent_user_id=102,
            opponent_name="Opponent",
            score_summary="13-7",
            kills=25,
            deaths=15,
            assists=10,
            had_dispute=False,
            is_forfeit=False,
            completed_at=completed_at,
        )
        
        # Verify adapter called
        mock_adapter.record_user_match_history.assert_called_once()
        call_kwargs = mock_adapter.record_user_match_history.call_args[1]
        assert call_kwargs["user_id"] == 101
        assert call_kwargs["match_id"] == 123
        assert call_kwargs["game_slug"] == "valorant"
        assert call_kwargs["kills"] == 25
        
        # Verify result
        assert result.user_id == 101
        assert result.kills == 25
    
    def test_record_user_match_history_validates_user_id(
        self, service, mock_adapter
    ):
        """Test service raises ValidationError for invalid user_id."""
        with pytest.raises(ValidationError, match="user_id must be a positive integer"):
            service.record_user_match_history(
                user_id=0,  # Invalid
                match_id=123,
                tournament_id=456,
                game_slug="valorant",
                is_winner=True,
                is_draw=False,
                opponent_user_id=None,
                opponent_name="Opponent",
                score_summary="",
                completed_at=datetime.now(),
            )
        
        # Adapter should not be called
        mock_adapter.record_user_match_history.assert_not_called()
    
    def test_record_user_match_history_validates_negative_stats(
        self, service, mock_adapter
    ):
        """Test service raises ValidationError for negative kills/deaths/assists."""
        with pytest.raises(ValidationError, match="kills, deaths, and assists must be non-negative"):
            service.record_user_match_history(
                user_id=101,
                match_id=123,
                tournament_id=456,
                game_slug="valorant",
                is_winner=True,
                is_draw=False,
                opponent_user_id=None,
                opponent_name="Opponent",
                score_summary="",
                kills=-5,  # Invalid
                deaths=10,
                assists=0,
                completed_at=datetime.now(),
            )
    
    def test_record_user_match_history_defaults_completed_at(
        self, service, mock_adapter
    ):
        """Test service defaults completed_at to now if not provided."""
        mock_adapter.record_user_match_history.return_value = Mock()
        
        service.record_user_match_history(
            user_id=101,
            match_id=123,
            tournament_id=456,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            opponent_user_id=None,
            opponent_name="Opponent",
            score_summary="",
            # completed_at not provided
        )
        
        # Verify adapter called with completed_at
        call_kwargs = mock_adapter.record_user_match_history.call_args[1]
        assert "completed_at" in call_kwargs
        assert call_kwargs["completed_at"] is not None
    
    # ========================================================================
    # Team Match History Recording Tests
    # ========================================================================
    
    def test_record_team_match_history_calls_adapter_with_elo(
        self, service, mock_adapter
    ):
        """Test service delegates team history recording with ELO tracking."""
        completed_at = datetime.now()
        
        mock_adapter.record_team_match_history.return_value = TeamMatchHistoryDTO(
            team_id=201,
            team_name="Test Team",
            match_id=123,
            tournament_id=456,
            tournament_name="Test Tournament",
            game_slug="csgo",
            is_winner=True,
            is_draw=False,
            score_summary="16-10",
            opponent_team_id=202,
            opponent_team_name="Opponent Team",
            elo_before=1500,
            elo_after=1520,
            elo_change=20,
            had_dispute=False,
            is_forfeit=False,
            completed_at=completed_at,
        )
        
        result = service.record_team_match_history(
            team_id=201,
            match_id=123,
            tournament_id=456,
            game_slug="csgo",
            is_winner=True,
            is_draw=False,
            opponent_team_id=202,
            opponent_team_name="Opponent Team",
            score_summary="16-10",
            elo_before=1500,
            elo_after=1520,
            elo_change=20,
            had_dispute=False,
            is_forfeit=False,
            completed_at=completed_at,
        )
        
        # Verify adapter called
        mock_adapter.record_team_match_history.assert_called_once()
        call_kwargs = mock_adapter.record_team_match_history.call_args[1]
        assert call_kwargs["team_id"] == 201
        assert call_kwargs["elo_before"] == 1500
        assert call_kwargs["elo_after"] == 1520
        
        # Verify result
        assert result.team_id == 201
        assert result.elo_change == 20
    
    def test_record_team_match_history_validates_elo_range(
        self, service, mock_adapter
    ):
        """Test service validates ELO values are in valid range."""
        with pytest.raises(ValidationError, match="elo_before must be between 400 and 3000"):
            service.record_team_match_history(
                team_id=201,
                match_id=123,
                tournament_id=456,
                game_slug="csgo",
                is_winner=True,
                is_draw=False,
                opponent_team_id=None,
                opponent_team_name="Opponent",
                score_summary="",
                elo_before=300,  # Too low
                elo_after=1500,
                elo_change=0,
                completed_at=datetime.now(),
            )
    
    # ========================================================================
    # User Match History Retrieval Tests
    # ========================================================================
    
    def test_get_user_match_history_returns_list_and_count(
        self, service, mock_adapter
    ):
        """Test service returns list of DTOs and total count."""
        # Mock adapter responses
        mock_history_dto = UserMatchHistoryDTO(
            user_id=101,
            username="TestPlayer",
            match_id=123,
            tournament_id=456,
            tournament_name="Test Tournament",
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            score_summary="13-7",
            opponent_user_id=None,
            opponent_name="Opponent",
            kills=25,
            deaths=15,
            assists=10,
            had_dispute=False,
            is_forfeit=False,
            completed_at=datetime.now(),
        )
        
        mock_adapter.list_user_history.return_value = [mock_history_dto]
        mock_adapter.get_user_history_count.return_value = 1
        
        results, total_count = service.get_user_match_history(
            user_id=101,
            game_slug="valorant",
            limit=20,
            offset=0,
        )
        
        assert len(results) == 1
        assert total_count == 1
        assert results[0].user_id == 101
        
        # Verify adapter calls
        mock_adapter.list_user_history.assert_called_once()
        mock_adapter.get_user_history_count.assert_called_once()
    
    def test_get_user_match_history_validates_filter_dto(
        self, service, mock_adapter
    ):
        """Test service validates filter parameters via DTO."""
        with pytest.raises(ValidationError):
            # Invalid: both only_wins and only_losses
            service.get_user_match_history(
                user_id=101,
                only_wins=True,
                only_losses=True,
                limit=20,
                offset=0,
            )
    
    def test_get_user_match_history_passes_filters_to_adapter(
        self, service, mock_adapter
    ):
        """Test service passes all filters to adapter correctly."""
        mock_adapter.list_user_history.return_value = []
        mock_adapter.get_user_history_count.return_value = 0
        
        from_date = datetime.now() - timedelta(days=30)
        to_date = datetime.now()
        
        service.get_user_match_history(
            user_id=101,
            game_slug="valorant",
            tournament_id=456,
            from_date=from_date,
            to_date=to_date,
            only_wins=True,
            limit=50,
            offset=10,
        )
        
        # Verify filter DTO passed to adapter
        call_arg = mock_adapter.list_user_history.call_args[0][0]
        assert isinstance(call_arg, MatchHistoryFilterDTO)
        assert call_arg.user_id == 101
        assert call_arg.game_slug == "valorant"
        assert call_arg.tournament_id == 456
        assert call_arg.only_wins is True
        assert call_arg.limit == 50
        assert call_arg.offset == 10
    
    # ========================================================================
    # Team Match History Retrieval Tests
    # ========================================================================
    
    def test_get_team_match_history_returns_list_and_count(
        self, service, mock_adapter
    ):
        """Test service returns team history with pagination metadata."""
        mock_history_dto = TeamMatchHistoryDTO(
            team_id=201,
            team_name="Test Team",
            match_id=123,
            tournament_id=456,
            tournament_name="Test Tournament",
            game_slug="csgo",
            is_winner=True,
            is_draw=False,
            score_summary="16-10",
            opponent_team_id=None,
            opponent_team_name="Opponent",
            elo_before=1500,
            elo_after=1520,
            elo_change=20,
            had_dispute=False,
            is_forfeit=False,
            completed_at=datetime.now(),
        )
        
        mock_adapter.list_team_history.return_value = [mock_history_dto]
        mock_adapter.get_team_history_count.return_value = 1
        
        results, total_count = service.get_team_match_history(
            team_id=201,
            game_slug="csgo",
            limit=20,
            offset=0,
        )
        
        assert len(results) == 1
        assert total_count == 1
        assert results[0].team_id == 201
        assert results[0].elo_change == 20
    
    def test_get_team_match_history_filters_by_date_range(
        self, service, mock_adapter
    ):
        """Test service passes date range filters to adapter."""
        mock_adapter.list_team_history.return_value = []
        mock_adapter.get_team_history_count.return_value = 0
        
        from_date = datetime.now() - timedelta(days=7)
        to_date = datetime.now()
        
        service.get_team_match_history(
            team_id=201,
            from_date=from_date,
            to_date=to_date,
            limit=20,
            offset=0,
        )
        
        # Verify filter DTO
        call_arg = mock_adapter.list_team_history.call_args[0][0]
        assert call_arg.team_id == 201
        assert call_arg.from_date == from_date
        assert call_arg.to_date == to_date
