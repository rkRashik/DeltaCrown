"""
Unit Tests for Match History DTOs

Phase 8, Epic 8.4: Match History Engine
Tests DTO validation, construction, and serialization without ORM dependencies.
"""

import pytest
from datetime import datetime, timedelta
from apps.tournament_ops.dtos.match_history import (
    MatchHistoryEntryDTO,
    UserMatchHistoryDTO,
    TeamMatchHistoryDTO,
    MatchHistoryFilterDTO,
)


class TestMatchHistoryEntryDTO:
    """Test base MatchHistoryEntryDTO validation and construction."""
    
    def test_validate_happy_path(self):
        """Test successful validation with all required fields."""
        dto = MatchHistoryEntryDTO.validate(
            match_id=123,
            tournament_id=456,
            tournament_name="Test Tournament",
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            score_summary="13-7",
            opponent_id=789,
            opponent_name="Opponent Team",
            had_dispute=False,
            is_forfeit=False,
            completed_at=datetime.now(),
        )
        
        assert dto.match_id == 123
        assert dto.tournament_id == 456
        assert dto.game_slug == "valorant"
        assert dto.is_winner is True
        assert dto.opponent_name == "Opponent Team"
    
    def test_validate_defaults_opponent_name_if_empty(self):
        """Test that empty opponent_name defaults to 'Unknown'."""
        dto = MatchHistoryEntryDTO.validate(
            match_id=123,
            tournament_id=456,
            tournament_name="Test Tournament",
            game_slug="csgo",
            is_winner=False,
            is_draw=False,
            score_summary="",
            opponent_id=None,
            opponent_name="",
            had_dispute=False,
            is_forfeit=False,
            completed_at=datetime.now(),
        )
        
        assert dto.opponent_name == "Unknown"
    
    def test_validate_raises_on_invalid_match_id(self):
        """Test validation fails with invalid match_id."""
        with pytest.raises(ValueError, match="match_id must be a positive integer"):
            MatchHistoryEntryDTO.validate(
                match_id=0,
                tournament_id=456,
                tournament_name="Test",
                game_slug="valorant",
                is_winner=True,
                is_draw=False,
                score_summary="",
                opponent_id=None,
                opponent_name="",
                had_dispute=False,
                is_forfeit=False,
                completed_at=datetime.now(),
            )
    
    def test_validate_raises_on_empty_game_slug(self):
        """Test validation fails with empty game_slug."""
        with pytest.raises(ValueError, match="game_slug cannot be empty"):
            MatchHistoryEntryDTO.validate(
                match_id=123,
                tournament_id=456,
                tournament_name="Test",
                game_slug="",
                is_winner=True,
                is_draw=False,
                score_summary="",
                opponent_id=None,
                opponent_name="",
                had_dispute=False,
                is_forfeit=False,
                completed_at=datetime.now(),
            )


class TestUserMatchHistoryDTO:
    """Test UserMatchHistoryDTO validation and serialization."""
    
    def test_validate_happy_path(self):
        """Test successful validation with user-specific stats."""
        dto = UserMatchHistoryDTO.validate(
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
            completed_at=datetime.now(),
        )
        
        assert dto.user_id == 101
        assert dto.username == "TestPlayer"
        assert dto.kills == 25
        assert dto.deaths == 15
        assert dto.assists == 10
    
    def test_validate_raises_on_negative_stats(self):
        """Test validation fails with negative kills/deaths/assists."""
        with pytest.raises(ValueError, match="kills, deaths, and assists must be non-negative"):
            UserMatchHistoryDTO.validate(
                user_id=101,
                username="TestPlayer",
                match_id=123,
                tournament_id=456,
                tournament_name="Test",
                game_slug="valorant",
                is_winner=True,
                is_draw=False,
                score_summary="",
                opponent_user_id=None,
                opponent_name="",
                kills=-5,
                deaths=10,
                assists=0,
                had_dispute=False,
                is_forfeit=False,
                completed_at=datetime.now(),
            )
    
    def test_to_dict_serialization(self):
        """Test to_dict() produces correct structure."""
        completed_at = datetime.now()
        dto = UserMatchHistoryDTO.validate(
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
        
        result = dto.to_dict()
        
        assert result["user_id"] == 101
        assert result["username"] == "TestPlayer"
        assert result["kills"] == 25
        assert result["completed_at"] == completed_at.isoformat()


class TestTeamMatchHistoryDTO:
    """Test TeamMatchHistoryDTO validation and ELO tracking."""
    
    def test_validate_happy_path_with_elo(self):
        """Test successful validation with ELO tracking."""
        dto = TeamMatchHistoryDTO.validate(
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
            completed_at=datetime.now(),
        )
        
        assert dto.team_id == 201
        assert dto.team_name == "Test Team"
        assert dto.elo_before == 1500
        assert dto.elo_after == 1520
        assert dto.elo_change == 20
    
    def test_validate_calculates_elo_change(self):
        """Test that elo_change is calculated from elo_before/after."""
        dto = TeamMatchHistoryDTO.validate(
            team_id=201,
            team_name="Test Team",
            match_id=123,
            tournament_id=456,
            tournament_name="Test Tournament",
            game_slug="csgo",
            is_winner=False,
            is_draw=False,
            score_summary="10-16",
            opponent_team_id=202,
            opponent_team_name="Opponent Team",
            elo_before=1500,
            elo_after=1480,
            elo_change=0,  # Will be recalculated
            had_dispute=False,
            is_forfeit=False,
            completed_at=datetime.now(),
        )
        
        assert dto.elo_change == -20
    
    def test_validate_raises_on_invalid_elo_range(self):
        """Test validation fails with ELO outside valid range."""
        with pytest.raises(ValueError, match="elo_before must be between 400 and 3000"):
            TeamMatchHistoryDTO.validate(
                team_id=201,
                team_name="Test Team",
                match_id=123,
                tournament_id=456,
                tournament_name="Test",
                game_slug="csgo",
                is_winner=True,
                is_draw=False,
                score_summary="",
                opponent_team_id=None,
                opponent_team_name="",
                elo_before=300,  # Too low
                elo_after=1500,
                elo_change=0,
                had_dispute=False,
                is_forfeit=False,
                completed_at=datetime.now(),
            )


class TestMatchHistoryFilterDTO:
    """Test MatchHistoryFilterDTO validation and filter logic."""
    
    def test_validate_happy_path_user_filter(self):
        """Test successful validation for user history filter."""
        dto = MatchHistoryFilterDTO.validate(
            user_id=101,
            game_slug="valorant",
            tournament_id=456,
            from_date=datetime.now() - timedelta(days=30),
            to_date=datetime.now(),
            only_wins=False,
            only_losses=False,
            limit=20,
            offset=0,
        )
        
        assert dto.user_id == 101
        assert dto.team_id is None
        assert dto.game_slug == "valorant"
        assert dto.limit == 20
    
    def test_validate_raises_on_both_user_and_team_id(self):
        """Test validation fails when both user_id and team_id provided."""
        with pytest.raises(ValueError, match="Cannot filter by both user_id and team_id"):
            MatchHistoryFilterDTO.validate(
                user_id=101,
                team_id=201,  # Cannot have both
                limit=20,
                offset=0,
            )
    
    def test_validate_raises_on_neither_user_nor_team_id(self):
        """Test validation fails when neither user_id nor team_id provided."""
        with pytest.raises(ValueError, match="Either user_id or team_id must be provided"):
            MatchHistoryFilterDTO.validate(
                game_slug="valorant",
                limit=20,
                offset=0,
            )
    
    def test_validate_raises_on_invalid_limit(self):
        """Test validation fails with limit outside valid range."""
        with pytest.raises(ValueError, match="limit must be between 1 and 100"):
            MatchHistoryFilterDTO.validate(
                user_id=101,
                limit=150,  # Too high
                offset=0,
            )
    
    def test_validate_raises_on_invalid_date_range(self):
        """Test validation fails when from_date > to_date."""
        now = datetime.now()
        with pytest.raises(ValueError, match="from_date must be before to_date"):
            MatchHistoryFilterDTO.validate(
                user_id=101,
                from_date=now,
                to_date=now - timedelta(days=1),  # Invalid: from > to
                limit=20,
                offset=0,
            )
    
    def test_validate_raises_on_both_wins_and_losses_filter(self):
        """Test validation fails when both only_wins and only_losses are True."""
        with pytest.raises(ValueError, match="only_wins and only_losses cannot both be True"):
            MatchHistoryFilterDTO.validate(
                user_id=101,
                only_wins=True,
                only_losses=True,
                limit=20,
                offset=0,
            )
    
    def test_validate_team_filter(self):
        """Test successful validation for team history filter."""
        dto = MatchHistoryFilterDTO.validate(
            team_id=201,
            game_slug="csgo",
            only_wins=True,
            limit=50,
            offset=10,
        )
        
        assert dto.team_id == 201
        assert dto.user_id is None
        assert dto.only_wins is True
        assert dto.limit == 50
        assert dto.offset == 10
