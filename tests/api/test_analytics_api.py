"""
Epic 8.5 API Tests - Analytics REST API endpoints.

Tests for UserAnalyticsView, TeamAnalyticsView, LeaderboardView,
LeaderboardRefreshView, CurrentSeasonView, SeasonsListView.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.games.models import Game
from apps.organizations.models import Team
from apps.leaderboards.models import (
    UserAnalyticsSnapshot,
    TeamAnalyticsSnapshot,
    LeaderboardEntry,
    Season,
)

User = get_user_model()


@pytest.mark.django_db
class TestAnalyticsAPI:
    """Test analytics API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create API client."""
        return APIClient()
    
    @pytest.fixture
    def user(self):
        """Create test user."""
        return User.objects.create_user(username="testuser", email="test@example.com", password="testpass")
    
    @pytest.fixture
    def staff_user(self):
        """Create staff user."""
        return User.objects.create_user(
            username="staff", email="staff@example.com", password="staffpass",
            is_staff=True,
        )
    
    @pytest.fixture
    def game(self):
        """Create test game."""
        return Game.objects.create(slug="valorant", name="Valorant")
    
    @pytest.fixture
    def team(self, game):
        """Create test team."""
        return Team.objects.create(name="Test Team", tag="TEST", game=game)
    
    def test_user_analytics_success(self, client, user, game):
        """Test GET /api/stats/v2/users/<id>/analytics/ success."""
        UserAnalyticsSnapshot.objects.create(
            user=user,
            game=game,
            elo_snapshot=1600,
            win_rate=Decimal("65.0"),
            kda_ratio=Decimal("1.5"),
            tier="gold",
            percentile_rank=Decimal("70.0"),
        )
        
        response = client.get(f"/api/stats/v2/users/{user.id}/analytics/?game_slug={game.slug}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == user.id
        assert data["game_slug"] == game.slug
        assert data["elo_snapshot"] == 1600
        assert data["tier"] == "gold"
    
    def test_user_analytics_missing_game_slug(self, client, user):
        """Test GET /api/stats/v2/users/<id>/analytics/ without game_slug."""
        response = client.get(f"/api/stats/v2/users/{user.id}/analytics/")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "game_slug" in response.json()["error"]
    
    def test_user_analytics_not_found(self, client, user, game):
        """Test GET /api/stats/v2/users/<id>/analytics/ with no snapshot."""
        response = client.get(f"/api/stats/v2/users/{user.id}/analytics/?game_slug={game.slug}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_team_analytics_success(self, client, team):
        """Test GET /api/stats/v2/teams/<id>/analytics/ success."""
        TeamAnalyticsSnapshot.objects.create(
            team=team,
            game=team.game,
            elo_snapshot=1800,
            win_rate=Decimal("60.0"),
            synergy_score=Decimal("75.0"),
            activity_score=Decimal("80.0"),
            tier="gold",
            percentile_rank=Decimal("65.0"),
        )
        
        response = client.get(f"/api/stats/v2/teams/{team.id}/analytics/?game_slug={team.game.slug}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["team_id"] == team.id
        assert data["elo_snapshot"] == 1800
        assert data["synergy_score"] == "75.0"
    
    def test_leaderboard_success(self, client, user, game):
        """Test GET /api/leaderboards/v2/<type>/ success."""
        LeaderboardEntry.objects.create(
            leaderboard_type="game_user",
            rank=1,
            reference_id=user.id,
            game_slug=game.slug,
            score=2000,
            wins=50,
            losses=10,
            win_rate=Decimal("83.33"),
            computed_at=timezone.now(),
        )
        
        response = client.get(f"/api/leaderboards/v2/game_user/?game_slug={game.slug}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["rank"] == 1
        assert data[0]["reference_id"] == user.id
        assert data[0]["score"] == 2000
    
    def test_leaderboard_filtering(self, client, user, game):
        """Test GET /api/leaderboards/v2/<type>/ with filters."""
        # Create multiple entries
        for i in range(5):
            LeaderboardEntry.objects.create(
                leaderboard_type="game_user",
                rank=i + 1,
                reference_id=user.id + i,
                game_slug=game.slug,
                score=2000 - (i * 100),
                computed_at=timezone.now(),
            )
        
        # Limit to 3
        response = client.get(f"/api/leaderboards/v2/game_user/?game_slug={game.slug}&limit=3")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert data[0]["rank"] == 1  # Top entry
    
    def test_leaderboard_refresh_unauthorized(self, client):
        """Test POST /api/leaderboards/v2/refresh/ without auth."""
        response = client.post("/api/leaderboards/v2/refresh/", {"leaderboard_type": "game_user"})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_leaderboard_refresh_forbidden_non_staff(self, client, user):
        """Test POST /api/leaderboards/v2/refresh/ as non-staff."""
        client.force_authenticate(user=user)
        response = client.post("/api/leaderboards/v2/refresh/", {"leaderboard_type": "game_user"})
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_leaderboard_refresh_success(self, client, staff_user):
        """Test POST /api/leaderboards/v2/refresh/ as staff."""
        client.force_authenticate(user=staff_user)
        response = client.post("/api/leaderboards/v2/refresh/", {"leaderboard_type": "game_user"})
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["message"] == "Leaderboard refresh queued"
    
    def test_current_season_success(self, client):
        """Test GET /api/seasons/current/ with active season."""
        Season.objects.create(
            season_id="S1-2024",
            name="Season 1 - 2024",
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now() + timedelta(days=60),
            is_active=True,
            decay_rules_json={"enabled": True, "decay_percentage": 5.0},
        )
        
        response = client.get("/api/seasons/current/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["season_id"] == "S1-2024"
        assert data["is_active"] is True
    
    def test_current_season_not_found(self, client):
        """Test GET /api/seasons/current/ with no active season."""
        response = client.get("/api/seasons/current/")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_seasons_list_all(self, client):
        """Test GET /api/seasons/ returns all seasons."""
        Season.objects.create(
            season_id="S1-2024",
            name="Season 1",
            start_date=timezone.now() - timedelta(days=90),
            end_date=timezone.now() - timedelta(days=1),
            is_active=False,
        )
        Season.objects.create(
            season_id="S2-2024",
            name="Season 2",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=90),
            is_active=True,
        )
        
        # All seasons
        response = client.get("/api/seasons/?include_inactive=true")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2
        
        # Only active
        response = client.get("/api/seasons/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["season_id"] == "S2-2024"
