"""
Unit Tests for Team Stats DTOs

Phase 8, Epic 8.3: Team Stats & Ranking System
Tests for TeamStatsDTO, TeamRankingDTO, TeamStatsSummaryDTO, TeamMatchStatsUpdateDTO
"""

import pytest
from datetime import datetime
from decimal import Decimal

from apps.tournament_ops.dtos import (
    TeamStatsDTO,
    TeamRankingDTO,
    TeamStatsSummaryDTO,
    TeamMatchStatsUpdateDTO,
)
from apps.tournament_ops.exceptions import ValidationError


class MockTeamStats:
    """Mock TeamStats model for from_model() tests."""
    
    def __init__(self):
        self.team_id = 42
        self.game_slug = "valorant"
        self.matches_played = 25
        self.matches_won = 18
        self.matches_lost = 5
        self.matches_drawn = 2
        self.tournaments_played = 3
        self.tournaments_won = 1
        self.win_rate = Decimal("72.00")
        self.last_match_at = datetime(2025, 1, 15, 10, 30)
        self.created_at = datetime(2024, 12, 1, 8, 0)
        self.updated_at = datetime(2025, 1, 15, 10, 30)


class MockTeamRanking:
    """Mock TeamRanking model for from_model() tests."""
    
    def __init__(self):
        self.team_id = 42
        self.game_slug = "valorant"
        self.elo_rating = 1450
        self.peak_elo = 1480
        self.games_played = 25
        self.wins = 18
        self.losses = 5
        self.draws = 2
        self.rank = 12
        self.last_updated = datetime(2025, 1, 15, 10, 30)
        self.created_at = datetime(2024, 12, 1, 8, 0)


# ============================================================================
# TeamStatsDTO Tests
# ============================================================================

class TestTeamStatsDTO:
    """Test suite for TeamStatsDTO."""
    
    def test_create_dto_with_valid_data(self):
        """Test creating DTO with all valid fields."""
        dto = TeamStatsDTO(
            team_id=1,
            game_slug="valorant",
            matches_played=10,
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("70.00"),
            last_match_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        assert dto.team_id == 1
        assert dto.game_slug == "valorant"
        assert dto.matches_played == 10
        assert dto.matches_won == 7
        assert dto.win_rate == Decimal("70.00")
    
    def test_from_model(self):
        """Test creating DTO from mock model instance."""
        mock_stats = MockTeamStats()
        dto = TeamStatsDTO.from_model(mock_stats)
        
        assert dto.team_id == 42
        assert dto.game_slug == "valorant"
        assert dto.matches_played == 25
        assert dto.matches_won == 18
        assert dto.win_rate == Decimal("72.00")
    
    def test_validate_success(self):
        """Test validation passes for valid data."""
        dto = TeamStatsDTO(
            team_id=1,
            game_slug="valorant",
            matches_played=10,
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("70.00"),
            last_match_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        # Should not raise
        dto.validate()
    
    def test_validate_fails_for_invalid_team_id(self):
        """Test validation fails when team_id is invalid."""
        dto = TeamStatsDTO(
            team_id=0,  # Invalid
            game_slug="valorant",
            matches_played=10,
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("70.00"),
            last_match_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        with pytest.raises(ValidationError, match="team_id is required"):
            dto.validate()
    
    def test_validate_fails_for_empty_game_slug(self):
        """Test validation fails when game_slug is empty."""
        dto = TeamStatsDTO(
            team_id=1,
            game_slug="",  # Invalid
            matches_played=10,
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("70.00"),
            last_match_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        with pytest.raises(ValidationError, match="game_slug cannot be empty"):
            dto.validate()
    
    def test_validate_fails_for_negative_matches(self):
        """Test validation fails for negative match counts."""
        dto = TeamStatsDTO(
            team_id=1,
            game_slug="valorant",
            matches_played=-1,  # Invalid
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("70.00"),
            last_match_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        with pytest.raises(ValidationError, match="matches_played must be >= 0"):
            dto.validate()
    
    def test_validate_fails_for_invalid_win_rate(self):
        """Test validation fails for win_rate out of range."""
        dto = TeamStatsDTO(
            team_id=1,
            game_slug="valorant",
            matches_played=10,
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("150.00"),  # Invalid (> 100)
            last_match_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        with pytest.raises(ValidationError, match="win_rate must be between 0.00 and 100.00"):
            dto.validate()
    
    def test_to_dict(self):
        """Test serialization to dict."""
        now = datetime.now()
        dto = TeamStatsDTO(
            team_id=1,
            game_slug="valorant",
            matches_played=10,
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("70.00"),
            last_match_at=now,
            created_at=now,
            updated_at=now,
        )
        
        data = dto.to_dict()
        
        assert data["team_id"] == 1
        assert data["game_slug"] == "valorant"
        assert data["matches_played"] == 10
        assert data["win_rate"] == Decimal("70.00")
    
    def test_immutability(self):
        """Test DTO is frozen (immutable)."""
        dto = TeamStatsDTO(
            team_id=1,
            game_slug="valorant",
            matches_played=10,
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("70.00"),
            last_match_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        with pytest.raises(AttributeError):
            dto.team_id = 999  # Should raise due to frozen=True


# ============================================================================
# TeamRankingDTO Tests
# ============================================================================

class TestTeamRankingDTO:
    """Test suite for TeamRankingDTO."""
    
    def test_create_dto_with_valid_data(self):
        """Test creating DTO with all valid fields."""
        dto = TeamRankingDTO(
            team_id=1,
            game_slug="valorant",
            elo_rating=1350,
            peak_elo=1400,
            games_played=20,
            wins=12,
            losses=6,
            draws=2,
            rank=15,
            last_updated=datetime.now(),
            created_at=datetime.now(),
        )
        
        assert dto.team_id == 1
        assert dto.elo_rating == 1350
        assert dto.peak_elo == 1400
        assert dto.rank == 15
    
    def test_from_model(self):
        """Test creating DTO from mock model instance."""
        mock_ranking = MockTeamRanking()
        dto = TeamRankingDTO.from_model(mock_ranking)
        
        assert dto.team_id == 42
        assert dto.game_slug == "valorant"
        assert dto.elo_rating == 1450
        assert dto.peak_elo == 1480
        assert dto.rank == 12
    
    def test_validate_success(self):
        """Test validation passes for valid data."""
        dto = TeamRankingDTO(
            team_id=1,
            game_slug="valorant",
            elo_rating=1350,
            peak_elo=1400,
            games_played=20,
            wins=12,
            losses=6,
            draws=2,
            rank=15,
            last_updated=datetime.now(),
            created_at=datetime.now(),
        )
        
        dto.validate()  # Should not raise
    
    def test_validate_fails_for_negative_elo(self):
        """Test validation fails for negative ELO."""
        dto = TeamRankingDTO(
            team_id=1,
            game_slug="valorant",
            elo_rating=-100,  # Invalid
            peak_elo=1400,
            games_played=20,
            wins=12,
            losses=6,
            draws=2,
            rank=15,
            last_updated=datetime.now(),
            created_at=datetime.now(),
        )
        
        with pytest.raises(ValidationError, match="elo_rating must be >= 0"):
            dto.validate()
    
    def test_validate_fails_for_invalid_rank(self):
        """Test validation fails when rank < 1."""
        dto = TeamRankingDTO(
            team_id=1,
            game_slug="valorant",
            elo_rating=1350,
            peak_elo=1400,
            games_played=20,
            wins=12,
            losses=6,
            draws=2,
            rank=0,  # Invalid
            last_updated=datetime.now(),
            created_at=datetime.now(),
        )
        
        with pytest.raises(ValidationError, match="rank must be >= 1"):
            dto.validate()
    
    def test_to_dict(self):
        """Test serialization to dict."""
        now = datetime.now()
        dto = TeamRankingDTO(
            team_id=1,
            game_slug="valorant",
            elo_rating=1350,
            peak_elo=1400,
            games_played=20,
            wins=12,
            losses=6,
            draws=2,
            rank=15,
            last_updated=now,
            created_at=now,
        )
        
        data = dto.to_dict()
        
        assert data["team_id"] == 1
        assert data["elo_rating"] == 1350
        assert data["rank"] == 15


# ============================================================================
# TeamStatsSummaryDTO Tests
# ============================================================================

class TestTeamStatsSummaryDTO:
    """Test suite for TeamStatsSummaryDTO."""
    
    def test_from_team_stats_dto(self):
        """Test creating summary from full TeamStatsDTO."""
        stats_dto = TeamStatsDTO(
            team_id=1,
            game_slug="valorant",
            matches_played=10,
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("70.00"),
            last_match_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        ranking_dto = TeamRankingDTO(
            team_id=1,
            game_slug="valorant",
            elo_rating=1350,
            peak_elo=1400,
            games_played=10,
            wins=7,
            losses=2,
            draws=1,
            rank=15,
            last_updated=datetime.now(),
            created_at=datetime.now(),
        )
        
        summary = TeamStatsSummaryDTO.from_team_stats_dto(stats_dto, ranking_dto)
        
        assert summary.team_id == 1
        assert summary.total_matches == 10
        assert summary.total_wins == 7
        assert summary.elo_rating == 1350
        assert summary.rank == 15
    
    def test_from_team_stats_dto_without_ranking(self):
        """Test creating summary without ranking data."""
        stats_dto = TeamStatsDTO(
            team_id=1,
            game_slug="valorant",
            matches_played=10,
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            tournaments_played=2,
            tournaments_won=1,
            win_rate=Decimal("70.00"),
            last_match_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        summary = TeamStatsSummaryDTO.from_team_stats_dto(stats_dto, ranking=None)
        
        assert summary.team_id == 1
        assert summary.total_matches == 10
        assert summary.elo_rating is None
        assert summary.rank is None


# ============================================================================
# TeamMatchStatsUpdateDTO Tests
# ============================================================================

class TestTeamMatchStatsUpdateDTO:
    """Test suite for TeamMatchStatsUpdateDTO."""
    
    def test_create_dto_for_winner(self):
        """Test creating update DTO for winning team."""
        dto = TeamMatchStatsUpdateDTO(
            team_id=1,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            opponent_team_id=2,
            opponent_elo=1300,
            match_id=100,
        )
        
        assert dto.team_id == 1
        assert dto.is_winner is True
        assert dto.is_draw is False
    
    def test_validate_fails_when_both_winner_and_draw(self):
        """Test validation fails if both winner and draw flags are true."""
        dto = TeamMatchStatsUpdateDTO(
            team_id=1,
            game_slug="valorant",
            is_winner=True,
            is_draw=True,  # Invalid combination
            opponent_team_id=2,
            opponent_elo=1300,
            match_id=100,
        )
        
        with pytest.raises(ValidationError, match="Cannot be both winner and draw"):
            dto.validate()
    
    def test_validate_fails_for_invalid_opponent_elo(self):
        """Test validation fails for negative opponent ELO."""
        dto = TeamMatchStatsUpdateDTO(
            team_id=1,
            game_slug="valorant",
            is_winner=False,
            is_draw=False,
            opponent_team_id=2,
            opponent_elo=-50,  # Invalid
            match_id=100,
        )
        
        with pytest.raises(ValidationError, match="opponent_elo must be >= 0"):
            dto.validate()
    
    def test_to_dict(self):
        """Test serialization to dict."""
        dto = TeamMatchStatsUpdateDTO(
            team_id=1,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            opponent_team_id=2,
            opponent_elo=1300,
            match_id=100,
        )
        
        data = dto.to_dict()
        
        assert data["team_id"] == 1
        assert data["is_winner"] is True
        assert data["opponent_elo"] == 1300
