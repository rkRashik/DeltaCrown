"""
API Tests for Match History Endpoints

Phase 8, Epic 8.4: Match History Engine
Tests REST API endpoints for user and team match history retrieval.
"""

import pytest
from datetime import datetime, timedelta
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.tournament_ops.dtos.match_history import (
    UserMatchHistoryDTO,
    TeamMatchHistoryDTO,
    MatchHistoryEntryDTO
)


@pytest.mark.django_db
class TestUserMatchHistoryAPI:
    """Test GET /api/tournaments/v1/history/users/<user_id>/ endpoint."""
    
    @pytest.fixture
    def api_client(self):
        """Create API test client."""
        return APIClient()
    
    @pytest.fixture
    def sample_user(self, django_user_model):
        """Create test user."""
        return django_user_model.objects.create_user(
            username="testplayer",
            email="test@example.com"
        )
    
    @pytest.fixture
    def sample_history_entry(self, sample_user):
        """Create sample user match history entry."""
        from apps.leaderboards.models import UserMatchHistory
        return UserMatchHistory.objects.create(
            user_id=sample_user.id,
            match_id=1,
            tournament_id=1,
            game_slug="valorant",
            opponent_name="Opponent",
            score_summary="13-7",
            is_winner=True,
            kills=25,
            deaths=10,
            assists=8,
            completed_at=datetime.now()
        )
    
    def test_get_user_match_history_success(
        self, api_client, sample_user, sample_history_entry
    ):
        """Test successful retrieval of user match history."""
        url = reverse('api:match_history:user_match_history', kwargs={'user_id': sample_user.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert len(response.data["results"]) == 1
        
        # Verify entry structure
        entry = response.data["results"][0]
        assert entry["match_id"] == 1
        assert entry["game_slug"] == "valorant"
        assert entry["is_winner"] is True
        assert entry["kills"] == 25
        assert entry["deaths"] == 10
        assert entry["assists"] == 8
    
    def test_get_user_match_history_filter_by_game_slug(
        self, api_client, sample_user, sample_history_entry
    ):
        """Test filtering by game_slug."""
        # Create another entry for different game
        from apps.leaderboards.models import UserMatchHistory
        UserMatchHistory.objects.create(
            user_id=sample_user.id,
            match_id=2,
            tournament_id=1,
            game_slug="csgo",
            opponent_name="Other",
            score_summary="16-10",
            is_winner=False,
            kills=15,
            deaths=20,
            assists=5,
            completed_at=datetime.now()
        )
        
        url = reverse('api:match_history:user_match_history', kwargs={'user_id': sample_user.id})
        response = api_client.get(url, {"game_slug": "valorant"})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["game_slug"] == "valorant"
    
    def test_get_user_match_history_filter_by_date_range(
        self, api_client, sample_user
    ):
        """Test filtering by from_date and to_date."""
        from apps.leaderboards.models import UserMatchHistory
        
        # Create entries with different dates
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        UserMatchHistory.objects.create(
            user_id=sample_user.id,
            match_id=1,
            tournament_id=1,
            game_slug="valorant",
            opponent_name="Recent",
            score_summary="13-7",
            is_winner=True,
            kills=20,
            deaths=10,
            assists=5,
            completed_at=today
        )
        
        UserMatchHistory.objects.create(
            user_id=sample_user.id,
            match_id=2,
            tournament_id=1,
            game_slug="valorant",
            opponent_name="Old",
            score_summary="10-13",
            is_winner=False,
            kills=15,
            deaths=15,
            assists=3,
            completed_at=week_ago
        )
        
        url = reverse('api:match_history:user_match_history', kwargs={'user_id': sample_user.id})
        response = api_client.get(url, {
            "from_date": yesterday.date().isoformat(),
            "to_date": today.date().isoformat()
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["opponent_name"] == "Recent"
    
    def test_get_user_match_history_filter_only_wins(
        self, api_client, sample_user
    ):
        """Test filtering only wins with only_wins parameter."""
        from apps.leaderboards.models import UserMatchHistory
        
        # Create win and loss
        UserMatchHistory.objects.create(
            user_id=sample_user.id,
            match_id=1,
            tournament_id=1,
            game_slug="valorant",
            opponent_name="Win",
            score_summary="13-7",
            is_winner=True,
            kills=20,
            deaths=10,
            assists=5,
            completed_at=datetime.now()
        )
        
        UserMatchHistory.objects.create(
            user_id=sample_user.id,
            match_id=2,
            tournament_id=1,
            game_slug="valorant",
            opponent_name="Loss",
            score_summary="7-13",
            is_winner=False,
            kills=10,
            deaths=15,
            assists=2,
            completed_at=datetime.now()
        )
        
        url = reverse('api:match_history:user_match_history', kwargs={'user_id': sample_user.id})
        response = api_client.get(url, {"only_wins": "true"})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["is_winner"] is True
    
    def test_get_user_match_history_pagination(
        self, api_client, sample_user
    ):
        """Test pagination with limit and offset."""
        from apps.leaderboards.models import UserMatchHistory
        
        # Create multiple entries
        for i in range(15):
            UserMatchHistory.objects.create(
                user_id=sample_user.id,
                match_id=i+1,
                tournament_id=1,
                game_slug="valorant",
                opponent_name=f"Opponent {i}",
                score_summary="13-7",
                is_winner=True,
                kills=20,
                deaths=10,
                assists=5,
                completed_at=datetime.now() - timedelta(minutes=i)
            )
        
        url = reverse('api:match_history:user_match_history', kwargs={'user_id': sample_user.id})
        response = api_client.get(url, {"limit": 10, "offset": 0})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 15
        assert len(response.data["results"]) == 10
        assert response.data["has_next"] is True
        assert response.data["has_previous"] is False
        
        # Get next page
        response = api_client.get(url, {"limit": 10, "offset": 10})
        assert len(response.data["results"]) == 5
        assert response.data["has_next"] is False
        assert response.data["has_previous"] is True
    
    def test_get_user_match_history_invalid_user_id(
        self, api_client
    ):
        """Test error response for non-existent user."""
        url = reverse('api:match_history:user_match_history', kwargs={'user_id': 99999})
        response = api_client.get(url)
        
        # Should return empty results (not 404)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0
        assert len(response.data["results"]) == 0


@pytest.mark.django_db
class TestTeamMatchHistoryAPI:
    """Test GET /api/tournaments/v1/history/teams/<team_id>/ endpoint."""
    
    @pytest.fixture
    def api_client(self):
        """Create API test client."""
        return APIClient()
    
    @pytest.fixture
    def sample_user(self, django_user_model):
        """Create test user."""
        return django_user_model.objects.create_user(
            username="teamcaptain",
            email="captain@example.com"
        )
    
    @pytest.fixture
    def sample_team(self):
        """Create test team."""
        from apps.teams.models import Team
        return Team.objects.create(
            name="Test Team",
            tag="TST",
            game="valorant"
        )
    
    @pytest.fixture
    def sample_team_history_entry(self, sample_team):
        """Create sample team match history entry."""
        from apps.leaderboards.models import TeamMatchHistory
        return TeamMatchHistory.objects.create(
            team_id=sample_team.id,
            match_id=1,
            tournament_id=1,
            game_slug="valorant",
            opponent_name="Enemy Team",
            score_summary="13-10",
            is_winner=True,
            elo_before=1500,
            elo_after=1520,
            elo_change=20,
            completed_at=datetime.now()
        )
    
    def test_get_team_match_history_success(
        self, api_client, sample_team, sample_team_history_entry
    ):
        """Test successful retrieval of team match history."""
        url = reverse('api:match_history:team_match_history', kwargs={'team_id': sample_team.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert len(response.data["results"]) == 1
        
        # Verify entry structure with ELO
        entry = response.data["results"][0]
        assert entry["match_id"] == 1
        assert entry["game_slug"] == "valorant"
        assert entry["is_winner"] is True
        assert entry["elo_before"] == 1500
        assert entry["elo_after"] == 1520
        assert entry["elo_change"] == 20
    
    def test_get_team_match_history_filter_by_tournament(
        self, api_client, sample_team
    ):
        """Test filtering by tournament_id."""
        from apps.leaderboards.models import TeamMatchHistory
        
        # Create entries for different tournaments
        TeamMatchHistory.objects.create(
            team_id=sample_team.id,
            match_id=1,
            tournament_id=1,
            game_slug="valorant",
            opponent_name="Team A",
            score_summary="13-10",
            is_winner=True,
            elo_before=1500,
            elo_after=1520,
            elo_change=20,
            completed_at=datetime.now()
        )
        
        TeamMatchHistory.objects.create(
            team_id=sample_team.id,
            match_id=2,
            tournament_id=2,
            game_slug="valorant",
            opponent_name="Team B",
            score_summary="10-13",
            is_winner=False,
            elo_before=1520,
            elo_after=1500,
            elo_change=-20,
            completed_at=datetime.now()
        )
        
        url = reverse('api:match_history:team_match_history', kwargs={'team_id': sample_team.id})
        response = api_client.get(url, {"tournament_id": 1})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["tournament_id"] == 1
    
    def test_get_team_match_history_elo_progression(
        self, api_client, sample_team
    ):
        """Test ELO progression across multiple matches."""
        from apps.leaderboards.models import TeamMatchHistory
        
        # Create ELO progression
        entries = [
            (1500, 1520, 20, True),
            (1520, 1505, -15, False),
            (1505, 1530, 25, True),
        ]
        
        for i, (before, after, change, winner) in enumerate(entries):
            TeamMatchHistory.objects.create(
                team_id=sample_team.id,
                match_id=i+1,
                tournament_id=1,
                game_slug="valorant",
                opponent_name=f"Team {i}",
                score_summary="13-10",
                is_winner=winner,
                elo_before=before,
                elo_after=after,
                elo_change=change,
                completed_at=datetime.now() - timedelta(hours=3-i)
            )
        
        url = reverse('api:match_history:team_match_history', kwargs={'team_id': sample_team.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3
        
        # Verify chronological ordering (newest first)
        results = response.data["results"]
        assert results[0]["elo_after"] == 1530
        assert results[1]["elo_after"] == 1505
        assert results[2]["elo_after"] == 1520


@pytest.mark.django_db
class TestCurrentUserMatchHistoryAPI:
    """Test GET /api/tournaments/v1/history/me/ endpoint (authenticated user)."""
    
    @pytest.fixture
    def api_client(self):
        """Create API test client."""
        return APIClient()
    
    @pytest.fixture
    def authenticated_user(self, django_user_model):
        """Create and authenticate test user."""
        user = django_user_model.objects.create_user(
            username="authuser",
            email="auth@example.com",
            password="testpass123"
        )
        return user
    
    @pytest.fixture
    def sample_history_entry(self, authenticated_user):
        """Create sample match history for authenticated user."""
        from apps.leaderboards.models import UserMatchHistory
        return UserMatchHistory.objects.create(
            user_id=authenticated_user.id,
            match_id=1,
            tournament_id=1,
            game_slug="valorant",
            opponent_name="Opponent",
            score_summary="13-7",
            is_winner=True,
            kills=25,
            deaths=10,
            assists=8,
            completed_at=datetime.now()
        )
    
    def test_get_current_user_match_history_authenticated(
        self, api_client, authenticated_user, sample_history_entry
    ):
        """Test authenticated user can retrieve own match history."""
        api_client.force_authenticate(user=authenticated_user)
        url = reverse('api:match_history:current_user_match_history')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["match_id"] == 1
    
    def test_get_current_user_match_history_unauthenticated(
        self, api_client
    ):
        """Test unauthenticated request returns 401."""
        url = reverse('api:match_history:current_user_match_history')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_match_history_with_filters(
        self, api_client, authenticated_user
    ):
        """Test current user endpoint supports same filters."""
        from apps.leaderboards.models import UserMatchHistory
        
        # Create multiple entries
        UserMatchHistory.objects.create(
            user_id=authenticated_user.id,
            match_id=1,
            tournament_id=1,
            game_slug="valorant",
            opponent_name="Win",
            score_summary="13-7",
            is_winner=True,
            kills=20,
            deaths=10,
            assists=5,
            completed_at=datetime.now()
        )
        
        UserMatchHistory.objects.create(
            user_id=authenticated_user.id,
            match_id=2,
            tournament_id=1,
            game_slug="csgo",
            opponent_name="Loss",
            score_summary="10-16",
            is_winner=False,
            kills=15,
            deaths=20,
            assists=3,
            completed_at=datetime.now()
        )
        
        api_client.force_authenticate(user=authenticated_user)
        url = reverse('api:match_history:current_user_match_history')
        response = api_client.get(url, {"game_slug": "valorant", "only_wins": "true"})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["game_slug"] == "valorant"
        assert response.data["results"][0]["is_winner"] is True
