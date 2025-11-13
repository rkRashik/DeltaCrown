"""
Tests for Leaderboards API (Phase E).

Tests flag-gated behavior, authentication, authorization, and service layer integration.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.tournaments.models import Tournament
from apps.leaderboards.services import LeaderboardResponseDTO, PlayerHistoryDTO, LeaderboardEntryDTO


@pytest.mark.django_db
class TestLeaderboardAPIFlags:
    """Test API flag-gated behavior (LEADERBOARDS_API_ENABLED)."""
    
    @pytest.fixture
    def client(self):
        """Create API client."""
        return APIClient()
    
    @pytest.fixture
    def user(self):
        """Create authenticated user."""
        user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass123"
        )
        return user
    
    @override_settings(LEADERBOARDS_API_ENABLED=False)
    def test_tournament_leaderboard_api_disabled_returns_404(self, client, user):
        """If LEADERBOARDS_API_ENABLED=False, return 404."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-leaderboard', kwargs={'tournament_id': 123})
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "disabled" in response.data["detail"].lower()
    
    @override_settings(LEADERBOARDS_API_ENABLED=False)
    def test_player_history_api_disabled_returns_404(self, client, user):
        """If LEADERBOARDS_API_ENABLED=False, return 404."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:player-history', kwargs={'player_id': 456})
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "disabled" in response.data["detail"].lower()
    
    @override_settings(LEADERBOARDS_API_ENABLED=False)
    def test_scoped_leaderboard_api_disabled_returns_404(self, client, user):
        """If LEADERBOARDS_API_ENABLED=False, return 404."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:scoped-leaderboard', kwargs={'scope': 'all_time'})
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "disabled" in response.data["detail"].lower()


@pytest.mark.django_db
class TestTournamentLeaderboardAPI:
    """Test GET /api/tournaments/leaderboards/tournament/{id}/"""
    
    @pytest.fixture
    def client(self):
        """Create API client."""
        return APIClient()
    
    @pytest.fixture
    def user(self):
        """Create authenticated user."""
        return User.objects.create_user(
            username="player1",
            email="player1@example.com",
            password="pass123"
        )
    
    @pytest.fixture
    def tournament(self):
        """Create test tournament."""
        return Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="in_progress"
        )
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    def test_unauthenticated_request_returns_401(self, client, tournament):
        """Unauthenticated requests should return 401."""
        url = reverse('tournaments_api:tournament-leaderboard', kwargs={'tournament_id': tournament.id})
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    @patch('apps.tournaments.api.leaderboard_views.get_tournament_leaderboard')
    def test_authenticated_request_returns_200(self, mock_service, client, user, tournament):
        """Authenticated requests should return 200 with leaderboard data."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-leaderboard', kwargs={'tournament_id': tournament.id})
        
        # Mock service response
        mock_dto = LeaderboardResponseDTO(
            scope="tournament",
            entries=[
                LeaderboardEntryDTO(
                    rank=1,
                    player_id=10,
                    team_id=5,
                    points=3000,
                    wins=15,
                    losses=2,
                    win_rate=88.24,
                    last_updated="2025-11-13T14:30:00Z"
                )
            ],
            metadata={
                "tournament_id": tournament.id,
                "count": 1,
                "cache_hit": False,
            }
        )
        mock_service.return_value = mock_dto
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["scope"] == "tournament"
        assert len(response.data["entries"]) == 1
        assert response.data["entries"][0]["rank"] == 1
        assert response.data["metadata"]["tournament_id"] == tournament.id
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    def test_nonexistent_tournament_returns_404(self, client, user):
        """Request for nonexistent tournament should return 404."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-leaderboard', kwargs={'tournament_id': 99999})
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @override_settings(LEADERBOARDS_API_ENABLED=True, LEADERBOARDS_COMPUTE_ENABLED=False)
    @patch('apps.tournaments.api.leaderboard_views.get_tournament_leaderboard')
    def test_compute_disabled_returns_empty_list(self, mock_service, client, user, tournament):
        """If COMPUTE_ENABLED=False, service returns empty list."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-leaderboard', kwargs={'tournament_id': tournament.id})
        
        # Mock service response (empty with metadata)
        mock_dto = LeaderboardResponseDTO(
            scope="tournament",
            entries=[],
            metadata={
                "tournament_id": tournament.id,
                "count": 0,
                "cache_hit": False,
                "computation_enabled": False,
            }
        )
        mock_service.return_value = mock_dto
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["entries"] == []
        assert response.data["metadata"]["computation_enabled"] is False


@pytest.mark.django_db
class TestPlayerHistoryAPI:
    """Test GET /api/tournaments/leaderboards/player/{id}/history/"""
    
    @pytest.fixture
    def client(self):
        """Create API client."""
        return APIClient()
    
    @pytest.fixture
    def user(self):
        """Create authenticated user."""
        return User.objects.create_user(
            username="player2",
            email="player2@example.com",
            password="pass456"
        )
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    def test_unauthenticated_request_returns_401(self, client):
        """Unauthenticated requests should return 401."""
        url = reverse('tournaments_api:player-history', kwargs={'player_id': 123})
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    @patch('apps.tournaments.api.leaderboard_views.get_player_leaderboard_history')
    def test_authenticated_request_returns_200(self, mock_service, client, user):
        """Authenticated requests should return 200 with history data."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:player-history', kwargs={'player_id': 456})
        
        # Mock service response
        mock_dto = PlayerHistoryDTO(
            player_id=456,
            snapshots=[
                {
                    "date": "2025-11-13",
                    "rank": 5,
                    "points": 2600,
                    "leaderboard_type": "season"
                },
                {
                    "date": "2025-11-12",
                    "rank": 6,
                    "points": 2400,
                    "leaderboard_type": "season"
                },
            ]
        )
        mock_service.return_value = mock_dto
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["player_id"] == 456
        assert response.data["count"] == 2
        assert len(response.data["history"]) == 2
        assert response.data["history"][0]["rank"] == 5
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    @patch('apps.tournaments.api.leaderboard_views.get_player_leaderboard_history')
    def test_nonexistent_player_returns_empty_history(self, mock_service, client, user):
        """Request for nonexistent player should return empty history."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:player-history', kwargs={'player_id': 99999})
        
        # Mock service response (empty)
        mock_dto = PlayerHistoryDTO(player_id=99999, snapshots=[])
        mock_service.return_value = mock_dto
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["history"] == []
        assert response.data["count"] == 0


@pytest.mark.django_db
class TestScopedLeaderboardAPI:
    """Test GET /api/tournaments/leaderboards/{scope}/"""
    
    @pytest.fixture
    def client(self):
        """Create API client."""
        return APIClient()
    
    @pytest.fixture
    def user(self):
        """Create authenticated user."""
        return User.objects.create_user(
            username="player3",
            email="player3@example.com",
            password="pass789"
        )
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    def test_unauthenticated_request_returns_401(self, client):
        """Unauthenticated requests should return 401."""
        url = reverse('tournaments_api:scoped-leaderboard', kwargs={'scope': 'all_time'})
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    def test_invalid_scope_returns_400(self, client, user):
        """Invalid scope should return 400."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:scoped-leaderboard', kwargs={'scope': 'invalid_scope'})
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid scope" in response.data["error"]
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    def test_season_scope_without_season_id_returns_400(self, client, user):
        """scope='season' without season_id query param should return 400."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:scoped-leaderboard', kwargs={'scope': 'season'})
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "season_id" in response.data["error"].lower()
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    @patch('apps.tournaments.api.leaderboard_views.get_scoped_leaderboard')
    def test_season_scope_with_season_id_returns_200(self, mock_service, client, user):
        """Valid season scope with season_id should return 200."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:scoped-leaderboard', kwargs={'scope': 'season'})
        url += '?season_id=2025_S1&game_code=valorant'
        
        # Mock service response
        mock_dto = LeaderboardResponseDTO(
            scope="season",
            entries=[
                LeaderboardEntryDTO(
                    rank=1,
                    player_id=789,
                    team_id=None,
                    points=5000,
                    wins=30,
                    losses=5,
                    win_rate=85.71,
                    last_updated="2025-11-13T12:00:00Z"
                )
            ],
            metadata={
                "scope": "season",
                "game_code": "valorant",
                "season_id": "2025_S1",
                "count": 1,
                "cache_hit": False,
            }
        )
        mock_service.return_value = mock_dto
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["scope"] == "season"
        assert response.data["metadata"]["game_code"] == "valorant"
        assert response.data["metadata"]["season_id"] == "2025_S1"
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    @patch('apps.tournaments.api.leaderboard_views.get_scoped_leaderboard')
    def test_all_time_scope_returns_200(self, mock_service, client, user):
        """Valid all-time scope should return 200."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:scoped-leaderboard', kwargs={'scope': 'all_time'})
        
        # Mock service response
        mock_dto = LeaderboardResponseDTO(
            scope="all_time",
            entries=[
                LeaderboardEntryDTO(
                    rank=1,
                    player_id=123,
                    team_id=45,
                    points=10000,
                    wins=60,
                    losses=10,
                    win_rate=85.71,
                    last_updated="2025-11-13T10:00:00Z"
                ),
                LeaderboardEntryDTO(
                    rank=2,
                    player_id=456,
                    team_id=67,
                    points=9500,
                    wins=58,
                    losses=12,
                    win_rate=82.86,
                    last_updated="2025-11-13T10:00:00Z"
                ),
            ],
            metadata={
                "scope": "all_time",
                "game_code": None,
                "season_id": None,
                "count": 2,
                "cache_hit": True,
            }
        )
        mock_service.return_value = mock_dto
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["scope"] == "all_time"
        assert len(response.data["entries"]) == 2
        assert response.data["entries"][0]["rank"] == 1
        assert response.data["entries"][1]["rank"] == 2
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    @patch('apps.tournaments.api.leaderboard_views.get_scoped_leaderboard')
    def test_all_time_scope_with_game_filter_returns_200(self, mock_service, client, user):
        """All-time scope with game_code filter should return 200."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:scoped-leaderboard', kwargs={'scope': 'all_time'})
        url += '?game_code=cs2'
        
        # Mock service response
        mock_dto = LeaderboardResponseDTO(
            scope="all_time",
            entries=[
                LeaderboardEntryDTO(
                    rank=1,
                    player_id=888,
                    team_id=None,
                    points=7500,
                    wins=45,
                    losses=8,
                    win_rate=84.91,
                    last_updated="2025-11-13T11:00:00Z"
                )
            ],
            metadata={
                "scope": "all_time",
                "game_code": "cs2",
                "season_id": None,
                "count": 1,
                "cache_hit": False,
            }
        )
        mock_service.return_value = mock_dto
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["metadata"]["game_code"] == "cs2"


@pytest.mark.django_db
class TestAPIResponses:
    """Test API response structure and PII compliance."""
    
    @pytest.fixture
    def client(self):
        """Create API client."""
        return APIClient()
    
    @pytest.fixture
    def user(self):
        """Create authenticated user."""
        return User.objects.create_user(
            username="player4",
            email="player4@example.com",
            password="pass000"
        )
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    @patch('apps.tournaments.api.leaderboard_views.get_tournament_leaderboard')
    def test_tournament_leaderboard_response_contains_no_pii(self, mock_service, client, user):
        """Tournament leaderboard responses should contain IDs only (no usernames, emails)."""
        client.force_authenticate(user=user)
        tournament = Tournament.objects.create(name="Test", game="lol", status="completed")
        url = reverse('tournaments_api:tournament-leaderboard', kwargs={'tournament_id': tournament.id})
        
        # Mock service response
        mock_dto = LeaderboardResponseDTO(
            scope="tournament",
            entries=[
                LeaderboardEntryDTO(
                    rank=1,
                    player_id=123,
                    team_id=45,
                    points=2000,
                    wins=10,
                    losses=1,
                    win_rate=90.91,
                    last_updated="2025-11-13T14:00:00Z"
                )
            ],
            metadata={"tournament_id": tournament.id, "count": 1, "cache_hit": False}
        )
        mock_service.return_value = mock_dto
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Verify only IDs present (no usernames, emails, full names)
        entry = response.data["entries"][0]
        assert "player_id" in entry
        assert "team_id" in entry
        assert "username" not in entry
        assert "email" not in entry
        assert "full_name" not in entry
    
    @override_settings(LEADERBOARDS_API_ENABLED=True)
    @patch('apps.tournaments.api.leaderboard_views.get_player_leaderboard_history')
    def test_player_history_response_contains_no_pii(self, mock_service, client, user):
        """Player history responses should contain IDs only."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:player-history', kwargs={'player_id': 456})
        
        # Mock service response
        mock_dto = PlayerHistoryDTO(
            player_id=456,
            snapshots=[
                {"date": "2025-11-13", "rank": 5, "points": 2600, "leaderboard_type": "season"}
            ]
        )
        mock_service.return_value = mock_dto
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Verify only player_id present
        assert "player_id" in response.data
        assert response.data["player_id"] == 456
        assert "username" not in response.data
        assert "email" not in response.data
