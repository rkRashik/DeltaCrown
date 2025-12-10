"""
API Tests for User Stats Endpoints

Phase 8, Epic 8.2: User Stats Service
Integration tests for User Stats REST API.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from apps.tournament_ops.dtos.user_stats import UserStatsDTO

User = get_user_model()


@pytest.mark.django_db
class TestUserStatsAPI:
    """Test User Stats API endpoints."""
    
    @pytest.fixture
    def api_client(self):
        """Fixture for DRF API client."""
        return APIClient()
    
    @pytest.fixture
    def user(self):
        """Fixture for test user."""
        return User.objects.create_user(
            username="testplayer",
            email="testplayer@example.com",
            password="password123"
        )
    
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
    
    def test_get_user_stats_success(self, api_client, sample_stats_dto):
        """Test GET /api/stats/v1/users/<id>/ returns stats."""
        with patch('apps.api.views.user_stats_views.get_tournament_ops_service') as mock_service:
            mock_facade = MagicMock()
            mock_facade.get_user_stats.return_value = sample_stats_dto
            mock_service.return_value = mock_facade
            
            url = f"/api/stats/v1/users/101/?game_slug=valorant"
            response = api_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user_id"] == 101
            assert data["game_slug"] == "valorant"
            assert data["matches_played"] == 10
            assert data["matches_won"] == 6
            
            mock_facade.get_user_stats.assert_called_once_with(
                user_id=101,
                game_slug="valorant"
            )
    
    def test_get_user_stats_not_found(self, api_client):
        """Test GET /api/stats/v1/users/<id>/ returns 404 when not found."""
        with patch('apps.api.views.user_stats_views.get_tournament_ops_service') as mock_service:
            mock_facade = MagicMock()
            mock_facade.get_user_stats.return_value = None
            mock_service.return_value = mock_facade
            
            url = f"/api/stats/v1/users/999/?game_slug=valorant"
            response = api_client.get(url)
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "error" in data
    
    def test_get_user_stats_missing_game_slug(self, api_client):
        """Test GET /api/stats/v1/users/<id>/ requires game_slug parameter."""
        url = f"/api/stats/v1/users/101/"
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "game_slug" in data["error"]
    
    def test_get_user_all_stats(self, api_client, sample_stats_dto):
        """Test GET /api/stats/v1/users/<id>/all/ returns all games."""
        with patch('apps.api.views.user_stats_views.get_tournament_ops_service') as mock_service:
            mock_facade = MagicMock()
            mock_facade.get_all_user_stats.return_value = [sample_stats_dto]
            mock_service.return_value = mock_facade
            
            url = f"/api/stats/v1/users/101/all/"
            response = api_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["user_id"] == 101
    
    def test_get_current_user_stats_authenticated(self, api_client, user, sample_stats_dto):
        """Test GET /api/stats/v1/me/ requires authentication."""
        with patch('apps.api.views.user_stats_views.get_tournament_ops_service') as mock_service:
            mock_facade = MagicMock()
            mock_facade.get_user_stats.return_value = sample_stats_dto
            mock_service.return_value = mock_facade
            
            api_client.force_authenticate(user=user)
            
            url = f"/api/stats/v1/me/?game_slug=valorant"
            response = api_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "user_id" in data
    
    def test_get_current_user_stats_unauthenticated(self, api_client):
        """Test GET /api/stats/v1/me/ returns 401 when not authenticated."""
        url = f"/api/stats/v1/me/?game_slug=valorant"
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_stats_all_games(self, api_client, user, sample_stats_dto):
        """Test GET /api/stats/v1/me/ returns all games when game_slug omitted."""
        with patch('apps.api.views.user_stats_views.get_tournament_ops_service') as mock_service:
            mock_facade = MagicMock()
            mock_facade.get_all_user_stats.return_value = [sample_stats_dto]
            mock_service.return_value = mock_facade
            
            api_client.force_authenticate(user=user)
            
            url = f"/api/stats/v1/me/"
            response = api_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
    
    def test_get_user_stats_summary(self, api_client):
        """Test GET /api/stats/v1/users/<id>/summary/ returns summary."""
        with patch('apps.api.views.user_stats_views.get_tournament_ops_service') as mock_service:
            mock_facade = MagicMock()
            mock_facade.get_user_stats_summary.return_value = {
                "user_id": 101,
                "game_slug": "valorant",
                "total_matches": 10,
                "total_wins": 6,
                "win_rate": Decimal("60.00"),
                "has_stats": True,
            }
            mock_service.return_value = mock_facade
            
            url = f"/api/stats/v1/users/101/summary/?game_slug=valorant"
            response = api_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user_id"] == 101
            assert data["total_matches"] == 10
    
    def test_get_game_leaderboard(self, api_client, sample_stats_dto):
        """Test GET /api/stats/v1/games/<slug>/leaderboard/ returns top users."""
        with patch('apps.api.views.user_stats_views.get_tournament_ops_service') as mock_service:
            mock_facade = MagicMock()
            mock_facade.get_top_stats_for_game.return_value = [sample_stats_dto]
            mock_service.return_value = mock_facade
            
            url = f"/api/stats/v1/games/valorant/leaderboard/"
            response = api_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["game_slug"] == "valorant"
            assert data["count"] == 1
            assert isinstance(data["results"], list)
            
            mock_facade.get_top_stats_for_game.assert_called_once_with(
                game_slug="valorant",
                limit=100
            )
    
    def test_get_game_leaderboard_with_limit(self, api_client, sample_stats_dto):
        """Test GET /api/stats/v1/games/<slug>/leaderboard/ respects limit parameter."""
        with patch('apps.api.views.user_stats_views.get_tournament_ops_service') as mock_service:
            mock_facade = MagicMock()
            mock_facade.get_top_stats_for_game.return_value = []
            mock_service.return_value = mock_facade
            
            url = f"/api/stats/v1/games/valorant/leaderboard/?limit=50"
            response = api_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            mock_facade.get_top_stats_for_game.assert_called_once_with(
                game_slug="valorant",
                limit=50
            )
    
    def test_architecture_compliance_views_use_facade(self):
        """Test API views use TournamentOpsService façade only (no direct service imports)."""
        import inspect
        from apps.api.views import user_stats_views
        
        source = inspect.getsource(user_stats_views)
        
        # Verify uses façade
        assert "get_tournament_ops_service" in source
        
        # Verify NO direct service imports
        assert "from apps.tournament_ops.services.user_stats_service import UserStatsService" not in source
        
        # Verify NO adapter imports
        assert "from apps.tournament_ops.adapters.user_stats_adapter" not in source
        
        # Verify NO ORM imports
        assert "from apps.leaderboards.models import UserStats" not in source
