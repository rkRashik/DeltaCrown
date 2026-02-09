"""
Unit Tests for TeamStatsAdapter

Phase 8, Epic 8.3: Team Stats & Ranking System
Tests for team stats data access layer.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone

from apps.tournament_ops.adapters import TeamStatsAdapter
from apps.tournament_ops.dtos import TeamStatsDTO


@pytest.mark.django_db
class TestTeamStatsAdapter:
    """Test suite for TeamStatsAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return TeamStatsAdapter()
    
    @pytest.fixture
    def team(self):
        """Create test team."""
        from apps.organizations.models import Team
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        captain = User.objects.create_user(
            username="captain_test",
            email="captain@test.com",
            password="test123"
        )
        
        team = Team.objects.create(
            name="Test Team",
            tag="TEST",
            captain=captain,
        )
        return team
    
    def test_get_team_stats_not_found(self, adapter, team):
        """Test get_team_stats returns None when stats don't exist."""
        stats_dto = adapter.get_team_stats(team.id, "valorant")
        
        assert stats_dto is None
    
    def test_get_team_stats_existing(self, adapter, team):
        """Test get_team_stats returns DTO when stats exist."""
        from apps.leaderboards.models import TeamStats
        
        # Create stats record
        TeamStats.objects.create(
            team=team,
            game_slug="valorant",
            matches_played=10,
            matches_won=7,
            matches_lost=2,
            matches_drawn=1,
            win_rate=Decimal("70.00"),
        )
        
        stats_dto = adapter.get_team_stats(team.id, "valorant")
        
        assert stats_dto is not None
        assert isinstance(stats_dto, TeamStatsDTO)
        assert stats_dto.team_id == team.id
        assert stats_dto.game_slug == "valorant"
        assert stats_dto.matches_played == 10
        assert stats_dto.matches_won == 7
    
    def test_get_all_team_stats(self, adapter, team):
        """Test get_all_team_stats returns all games for team."""
        from apps.leaderboards.models import TeamStats
        
        # Create stats for multiple games
        TeamStats.objects.create(
            team=team,
            game_slug="valorant",
            matches_played=10,
            matches_won=7,
        )
        
        TeamStats.objects.create(
            team=team,
            game_slug="csgo",
            matches_played=5,
            matches_won=3,
        )
        
        stats_dtos = adapter.get_all_team_stats(team.id)
        
        assert len(stats_dtos) == 2
        assert all(isinstance(dto, TeamStatsDTO) for dto in stats_dtos)
        assert stats_dtos[0].game_slug == "csgo"  # Alphabetical order
        assert stats_dtos[1].game_slug == "valorant"
    
    def test_increment_stats_for_match_creates_new_record(self, adapter, team):
        """Test increment_stats_for_match creates stats if none exist."""
        from apps.leaderboards.models import TeamStats
        
        # No stats exist yet
        assert TeamStats.objects.filter(team=team, game_slug="valorant").count() == 0
        
        # Increment for a win
        stats_dto = adapter.increment_stats_for_match(
            team_id=team.id,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
        )
        
        # Stats should be created
        assert stats_dto is not None
        assert stats_dto.matches_played == 1
        assert stats_dto.matches_won == 1
        assert stats_dto.matches_lost == 0
        
        # Verify database record
        stats = TeamStats.objects.get(team=team, game_slug="valorant")
        assert stats.matches_played == 1
        assert stats.matches_won == 1
    
    def test_increment_stats_for_match_increments_wins(self, adapter, team):
        """Test increment_stats_for_match increments wins correctly."""
        from apps.leaderboards.models import TeamStats
        
        # Create initial stats
        TeamStats.objects.create(
            team=team,
            game_slug="valorant",
            matches_played=5,
            matches_won=3,
            matches_lost=2,
        )
        
        # Increment for a win
        stats_dto = adapter.increment_stats_for_match(
            team_id=team.id,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
        )
        
        assert stats_dto.matches_played == 6
        assert stats_dto.matches_won == 4
        assert stats_dto.matches_lost == 2
    
    def test_increment_stats_for_match_increments_losses(self, adapter, team):
        """Test increment_stats_for_match increments losses correctly."""
        from apps.leaderboards.models import TeamStats
        
        TeamStats.objects.create(
            team=team,
            game_slug="valorant",
            matches_played=5,
            matches_won=3,
            matches_lost=2,
        )
        
        # Increment for a loss
        stats_dto = adapter.increment_stats_for_match(
            team_id=team.id,
            game_slug="valorant",
            is_winner=False,
            is_draw=False,
        )
        
        assert stats_dto.matches_played == 6
        assert stats_dto.matches_won == 3
        assert stats_dto.matches_lost == 3
    
    def test_increment_stats_for_match_increments_draws(self, adapter, team):
        """Test increment_stats_for_match increments draws correctly."""
        from apps.leaderboards.models import TeamStats
        
        TeamStats.objects.create(
            team=team,
            game_slug="valorant",
            matches_played=5,
            matches_won=3,
            matches_lost=2,
            matches_drawn=0,
        )
        
        # Increment for a draw
        stats_dto = adapter.increment_stats_for_match(
            team_id=team.id,
            game_slug="valorant",
            is_winner=False,
            is_draw=True,
        )
        
        assert stats_dto.matches_played == 6
        assert stats_dto.matches_won == 3
        assert stats_dto.matches_lost == 2
        assert stats_dto.matches_drawn == 1
    
    def test_increment_stats_updates_last_match_at(self, adapter, team):
        """Test increment_stats_for_match updates last_match_at timestamp."""
        from apps.leaderboards.models import TeamStats
        
        old_time = timezone.now() - timedelta(hours=24)
        
        TeamStats.objects.create(
            team=team,
            game_slug="valorant",
            matches_played=1,
            last_match_at=old_time,
        )
        
        stats_dto = adapter.increment_stats_for_match(
            team_id=team.id,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
        )
        
        # last_match_at should be updated to recent time
        assert stats_dto.last_match_at > old_time
    
    def test_increment_stats_recalculates_win_rate(self, adapter, team):
        """Test increment_stats_for_match recalculates win_rate."""
        from apps.leaderboards.models import TeamStats
        
        TeamStats.objects.create(
            team=team,
            game_slug="valorant",
            matches_played=10,
            matches_won=5,
            win_rate=Decimal("50.00"),
        )
        
        # Add 2 more wins
        adapter.increment_stats_for_match(
            team_id=team.id,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
        )
        
        stats_dto = adapter.increment_stats_for_match(
            team_id=team.id,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
        )
        
        # 7 wins out of 12 matches = 58.33%
        assert stats_dto.matches_played == 12
        assert stats_dto.matches_won == 7
        assert stats_dto.win_rate == Decimal("58.33")
    
    def test_get_stats_by_game(self, adapter):
        """Test get_stats_by_game returns teams ordered by win rate."""
        from apps.organizations.models import Team
        from apps.leaderboards.models import TeamStats
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Create 3 teams
        teams = []
        for i in range(3):
            captain = User.objects.create_user(
                username=f"captain{i}",
                email=f"captain{i}@test.com",
                password="test123"
            )
            team = Team.objects.create(
                name=f"Team {i}",
                tag=f"T{i}",
                captain=captain,
            )
            teams.append(team)
        
        # Create stats with different win rates
        TeamStats.objects.create(
            team=teams[0],
            game_slug="valorant",
            matches_played=10,
            matches_won=8,
            win_rate=Decimal("80.00"),
        )
        
        TeamStats.objects.create(
            team=teams[1],
            game_slug="valorant",
            matches_played=10,
            matches_won=5,
            win_rate=Decimal("50.00"),
        )
        
        TeamStats.objects.create(
            team=teams[2],
            game_slug="valorant",
            matches_played=10,
            matches_won=9,
            win_rate=Decimal("90.00"),
        )
        
        stats_dtos = adapter.get_stats_by_game("valorant", limit=10)
        
        # Should be ordered by win_rate DESC
        assert len(stats_dtos) == 3
        assert stats_dtos[0].win_rate == Decimal("90.00")
        assert stats_dtos[1].win_rate == Decimal("80.00")
        assert stats_dtos[2].win_rate == Decimal("50.00")
    
    def test_increment_tournament_participation(self, adapter, team):
        """Test increment_tournament_participation increments counters."""
        from apps.leaderboards.models import TeamStats
        
        TeamStats.objects.create(
            team=team,
            game_slug="valorant",
            tournaments_played=1,
            tournaments_won=0,
        )
        
        # Increment participation (win)
        stats_dto = adapter.increment_tournament_participation(
            team_id=team.id,
            game_slug="valorant",
            is_winner=True,
        )
        
        assert stats_dto.tournaments_played == 2
        assert stats_dto.tournaments_won == 1
    
    def test_increment_tournament_participation_no_win(self, adapter, team):
        """Test increment_tournament_participation without win."""
        from apps.leaderboards.models import TeamStats
        
        TeamStats.objects.create(
            team=team,
            game_slug="valorant",
            tournaments_played=1,
            tournaments_won=0,
        )
        
        # Increment participation (no win)
        stats_dto = adapter.increment_tournament_participation(
            team_id=team.id,
            game_slug="valorant",
            is_winner=False,
        )
        
        assert stats_dto.tournaments_played == 2
        assert stats_dto.tournaments_won == 0
    
    def test_delete_stats(self, adapter, team):
        """Test delete_stats removes record."""
        from apps.leaderboards.models import TeamStats
        
        TeamStats.objects.create(
            team=team,
            game_slug="valorant",
            matches_played=10,
        )
        
        assert adapter.delete_stats(team.id, "valorant") is True
        
        # Verify deleted
        assert TeamStats.objects.filter(team=team, game_slug="valorant").count() == 0
    
    def test_delete_stats_not_found(self, adapter, team):
        """Test delete_stats returns False when stats don't exist."""
        assert adapter.delete_stats(team.id, "valorant") is False
