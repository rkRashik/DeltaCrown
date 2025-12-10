"""
Unit Tests for User Stats DTOs

Phase 8, Epic 8.2: User Stats Service
Tests for UserStatsDTO, UserStatsSummaryDTO, MatchStatsUpdateDTO.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from apps.tournament_ops.dtos.user_stats import (
    UserStatsDTO,
    UserStatsSummaryDTO,
    MatchStatsUpdateDTO,
)
from apps.tournament_ops.exceptions import ValidationError


class TestUserStatsDTO:
    """Test UserStatsDTO validation and conversion methods."""
    
    def test_from_model_success(self):
        """Test UserStatsDTO.from_model() with valid UserStats model."""
        # Mock UserStats model object
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
            last_match_at = datetime(2025, 12, 10, 12, 0, 0, tzinfo=timezone.utc)
            created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
            updated_at = datetime(2025, 12, 10, tzinfo=timezone.utc)
        
        mock_stats = MockUserStats()
        dto = UserStatsDTO.from_model(mock_stats)
        
        assert dto.user_id == 101
        assert dto.game_slug == "valorant"
        assert dto.matches_played == 50
        assert dto.matches_won == 30
        assert dto.win_rate == Decimal("60.00")
        assert dto.kd_ratio == Decimal("1.11")
    
    def test_validate_success(self):
        """Test UserStatsDTO.validate() with valid data."""
        dto = UserStatsDTO(
            user_id=101,
            game_slug="csgo",
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
            last_match_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Should not raise
        dto.validate()
    
    def test_validate_missing_user_id(self):
        """Test UserStatsDTO.validate() with missing user_id."""
        dto = UserStatsDTO(
            user_id=None,  # Invalid
            game_slug="valorant",
            matches_played=5,
            matches_won=3,
            matches_lost=2,
            matches_drawn=0,
            tournaments_played=1,
            tournaments_won=0,
            win_rate=Decimal("60.00"),
            total_kills=50,
            total_deaths=40,
            kd_ratio=Decimal("1.25"),
            last_match_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        with pytest.raises(ValidationError, match="user_id is required"):
            dto.validate()
    
    def test_validate_negative_stats(self):
        """Test UserStatsDTO.validate() with negative match counts."""
        dto = UserStatsDTO(
            user_id=101,
            game_slug="valorant",
            matches_played=-5,  # Invalid
            matches_won=3,
            matches_lost=2,
            matches_drawn=0,
            tournaments_played=1,
            tournaments_won=0,
            win_rate=Decimal("60.00"),
            total_kills=50,
            total_deaths=40,
            kd_ratio=Decimal("1.25"),
            last_match_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        with pytest.raises(ValidationError, match="matches_played must be >= 0"):
            dto.validate()
    
    def test_to_dict(self):
        """Test UserStatsDTO.to_dict() serialization."""
        now = datetime(2025, 12, 10, 12, 0, 0, tzinfo=timezone.utc)
        dto = UserStatsDTO(
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
            last_match_at=now,
            created_at=now,
            updated_at=now,
        )
        
        data = dto.to_dict()
        
        assert data["user_id"] == 101
        assert data["game_slug"] == "valorant"
        assert data["matches_played"] == 10
        assert data["win_rate"] == Decimal("60.00")
        assert data["kd_ratio"] == Decimal("1.25")
        assert data["last_match_at"] == now


class TestUserStatsSummaryDTO:
    """Test UserStatsSummaryDTO lightweight summary."""
    
    def test_from_user_stats_dto(self):
        """Test UserStatsSummaryDTO.from_user_stats_dto() conversion."""
        full_dto = UserStatsDTO(
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
            last_match_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        summary = UserStatsSummaryDTO.from_user_stats_dto(full_dto)
        
        assert summary.user_id == 101
        assert summary.game_slug == "valorant"
        assert summary.total_matches == 10
        assert summary.total_wins == 6
        assert summary.win_rate == Decimal("60.00")
        assert summary.total_tournaments == 2
    
    def test_validate_success(self):
        """Test UserStatsSummaryDTO.validate() with valid data."""
        dto = UserStatsSummaryDTO(
            user_id=101,
            game_slug="csgo",
            total_matches=20,
            total_wins=12,
            win_rate=Decimal("60.00"),
            total_tournaments=3,
            kd_ratio=Decimal("1.5"),
            last_played=datetime.now(timezone.utc),
        )
        
        dto.validate()  # Should not raise
    
    def test_to_dict(self):
        """Test UserStatsSummaryDTO.to_dict() serialization."""
        now = datetime(2025, 12, 10, tzinfo=timezone.utc)
        dto = UserStatsSummaryDTO(
            user_id=101,
            game_slug="valorant",
            total_matches=10,
            total_wins=6,
            win_rate=Decimal("60.00"),
            total_tournaments=2,
            kd_ratio=Decimal("1.25"),
            last_played=now,
        )
        
        data = dto.to_dict()
        
        assert data["user_id"] == 101
        assert data["total_matches"] == 10
        assert data["win_rate"] == Decimal("60.00")


class TestMatchStatsUpdateDTO:
    """Test MatchStatsUpdateDTO for event-driven updates."""
    
    def test_validate_success_win(self):
        """Test MatchStatsUpdateDTO.validate() with winner."""
        dto = MatchStatsUpdateDTO(
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
        
        dto.validate()  # Should not raise
    
    def test_validate_success_loss(self):
        """Test MatchStatsUpdateDTO.validate() with loser."""
        dto = MatchStatsUpdateDTO(
            user_id=102,
            game_slug="valorant",
            is_winner=False,
            is_draw=False,
            kills=15,
            deaths=22,
            assists=5,
            mvp=False,
            match_id=1001,
        )
        
        dto.validate()  # Should not raise
    
    def test_validate_conflict_winner_and_draw(self):
        """Test MatchStatsUpdateDTO.validate() rejects both winner and draw."""
        dto = MatchStatsUpdateDTO(
            user_id=101,
            game_slug="valorant",
            is_winner=True,  # Conflict
            is_draw=True,    # Conflict
            kills=20,
            deaths=20,
            assists=8,
            mvp=False,
            match_id=1001,
        )
        
        with pytest.raises(ValidationError, match="Cannot be both winner and draw"):
            dto.validate()
    
    def test_validate_negative_kills(self):
        """Test MatchStatsUpdateDTO.validate() rejects negative kills."""
        dto = MatchStatsUpdateDTO(
            user_id=101,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            kills=-5,  # Invalid
            deaths=18,
            assists=10,
            mvp=False,
            match_id=1001,
        )
        
        with pytest.raises(ValidationError, match="kills must be >= 0"):
            dto.validate()
    
    def test_to_dict(self):
        """Test MatchStatsUpdateDTO.to_dict() serialization."""
        dto = MatchStatsUpdateDTO(
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
        
        data = dto.to_dict()
        
        assert data["user_id"] == 101
        assert data["is_winner"] is True
        assert data["kills"] == 25
        assert data["mvp"] is True
