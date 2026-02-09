"""
Unit Tests for TeamRankingAdapter

Phase 8, Epic 8.3: Team Stats & Ranking System
Tests for team ranking data access layer.
"""

import pytest
from datetime import datetime, timedelta
from django.utils import timezone

from apps.tournament_ops.adapters import TeamRankingAdapter
from apps.tournament_ops.dtos import TeamRankingDTO


@pytest.mark.django_db
class TestTeamRankingAdapter:
    """Test suite for TeamRankingAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return TeamRankingAdapter()
    
    @pytest.fixture
    def team(self):
        """Create test team."""
        from apps.organizations.models import Team
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        captain = User.objects.create_user(
            username="captain_rank",
            email="captain_rank@test.com",
            password="test123"
        )
        
        return Team.objects.create(
            name="Ranked Team",
            tag="RANK",
            captain=captain,
        )
    
    def test_get_team_ranking_not_found(self, adapter, team):
        """Test get_team_ranking returns None when ranking doesn't exist."""
        ranking_dto = adapter.get_team_ranking(team.id, "valorant")
        assert ranking_dto is None
    
    def test_get_team_ranking_existing(self, adapter, team):
        """Test get_team_ranking returns DTO when ranking exists."""
        from apps.leaderboards.models import TeamRanking
        
        TeamRanking.objects.create(
            team=team,
            game_slug="valorant",
            elo_rating=1350,
            peak_elo=1400,
            games_played=10,
            wins=7,
            losses=3,
        )
        
        ranking_dto = adapter.get_team_ranking(team.id, "valorant")
        
        assert ranking_dto is not None
        assert isinstance(ranking_dto, TeamRankingDTO)
        assert ranking_dto.team_id == team.id
        assert ranking_dto.elo_rating == 1350
    
    def test_update_elo_rating_creates_new_record(self, adapter, team):
        """Test update_elo_rating creates ranking if none exists."""
        from apps.leaderboards.models import TeamRanking
        
        assert TeamRanking.objects.filter(team=team, game_slug="valorant").count() == 0
        
        ranking_dto = adapter.update_elo_rating(
            team_id=team.id,
            game_slug="valorant",
            elo_change=50,
            is_winner=True,
            is_draw=False,
        )
        
        assert ranking_dto is not None
        assert ranking_dto.elo_rating == 1250  # 1200 default + 50
        assert ranking_dto.wins == 1
    
    def test_update_elo_rating_increments_wins(self, adapter, team):
        """Test update_elo_rating increments win counter."""
        from apps.leaderboards.models import TeamRanking
        
        TeamRanking.objects.create(
            team=team,
            game_slug="valorant",
            elo_rating=1300,
            wins=5,
            losses=3,
        )
        
        ranking_dto = adapter.update_elo_rating(
            team_id=team.id,
            game_slug="valorant",
            elo_change=30,
            is_winner=True,
            is_draw=False,
        )
        
        assert ranking_dto.elo_rating == 1330
        assert ranking_dto.wins == 6
        assert ranking_dto.losses == 3
    
    def test_update_elo_rating_increments_losses(self, adapter, team):
        """Test update_elo_rating increments loss counter."""
        from apps.leaderboards.models import TeamRanking
        
        TeamRanking.objects.create(
            team=team,
            game_slug="valorant",
            elo_rating=1300,
            wins=5,
            losses=3,
        )
        
        ranking_dto = adapter.update_elo_rating(
            team_id=team.id,
            game_slug="valorant",
            elo_change=-20,
            is_winner=False,
            is_draw=False,
        )
        
        assert ranking_dto.elo_rating == 1280
        assert ranking_dto.wins == 5
        assert ranking_dto.losses == 4
    
    def test_update_elo_rating_increments_draws(self, adapter, team):
        """Test update_elo_rating increments draw counter."""
        from apps.leaderboards.models import TeamRanking
        
        TeamRanking.objects.create(
            team=team,
            game_slug="valorant",
            elo_rating=1300,
            draws=2,
        )
        
        ranking_dto = adapter.update_elo_rating(
            team_id=team.id,
            game_slug="valorant",
            elo_change=5,
            is_winner=False,
            is_draw=True,
        )
        
        assert ranking_dto.elo_rating == 1305
        assert ranking_dto.draws == 3
    
    def test_update_elo_rating_updates_peak(self, adapter, team):
        """Test update_elo_rating updates peak_elo when rating exceeds it."""
        from apps.leaderboards.models import TeamRanking
        
        TeamRanking.objects.create(
            team=team,
            game_slug="valorant",
            elo_rating=1300,
            peak_elo=1350,
        )
        
        ranking_dto = adapter.update_elo_rating(
            team_id=team.id,
            game_slug="valorant",
            elo_change=100,  # Takes ELO to 1400
            is_winner=True,
            is_draw=False,
        )
        
        assert ranking_dto.elo_rating == 1400
        assert ranking_dto.peak_elo == 1400  # Updated
    
    def test_get_rankings_by_game(self, adapter):
        """Test get_rankings_by_game returns teams ordered by ELO."""
        from apps.organizations.models import Team
        from apps.leaderboards.models import TeamRanking
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        teams = []
        for i in range(3):
            captain = User.objects.create_user(
                username=f"rank_cap{i}",
                email=f"rank{i}@test.com",
                password="test123"
            )
            team = Team.objects.create(
                name=f"Rank Team {i}",
                tag=f"RT{i}",
                captain=captain,
            )
            teams.append(team)
        
        TeamRanking.objects.create(team=teams[0], game_slug="valorant", elo_rating=1400)
        TeamRanking.objects.create(team=teams[1], game_slug="valorant", elo_rating=1500)
        TeamRanking.objects.create(team=teams[2], game_slug="valorant", elo_rating=1300)
        
        rankings = adapter.get_rankings_by_game("valorant", limit=10)
        
        assert len(rankings) == 3
        assert rankings[0].elo_rating == 1500
        assert rankings[1].elo_rating == 1400
        assert rankings[2].elo_rating == 1300
    
    def test_create_or_update_ranking(self, adapter, team):
        """Test create_or_update_ranking creates new record."""
        ranking_dto = adapter.create_or_update_ranking(
            team_id=team.id,
            game_slug="valorant",
            elo_rating=1400,
        )
        
        assert ranking_dto.elo_rating == 1400
        assert ranking_dto.peak_elo == 1400
    
    def test_recalculate_ranks_for_game(self, adapter):
        """Test recalculate_ranks_for_game assigns ranks correctly."""
        from apps.organizations.models import Team
        from apps.leaderboards.models import TeamRanking
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        teams = []
        for i in range(3):
            captain = User.objects.create_user(
                username=f"recalc{i}",
                email=f"recalc{i}@test.com",
                password="test123"
            )
            team = Team.objects.create(
                name=f"Recalc Team {i}",
                tag=f"RC{i}",
                captain=captain,
            )
            teams.append(team)
        
        TeamRanking.objects.create(team=teams[0], game_slug="valorant", elo_rating=1400, rank=None)
        TeamRanking.objects.create(team=teams[1], game_slug="valorant", elo_rating=1500, rank=None)
        TeamRanking.objects.create(team=teams[2], game_slug="valorant", elo_rating=1300, rank=None)
        
        updated_count = adapter.recalculate_ranks_for_game("valorant")
        
        assert updated_count == 3
        
        # Verify ranks
        rankings = list(TeamRanking.objects.filter(game_slug="valorant").order_by("-elo_rating"))
        assert rankings[0].rank == 1  # 1500 ELO
        assert rankings[1].rank == 2  # 1400 ELO
        assert rankings[2].rank == 3  # 1300 ELO
