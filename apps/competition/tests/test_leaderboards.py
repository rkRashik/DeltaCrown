"""Tests for leaderboard views (Phase 3A-E)."""
import pytest
from django.urls import reverse
from django.test import override_settings


@pytest.mark.django_db
class TestLeaderboardViews:
    """Test leaderboard views."""
    
    @override_settings(COMPETITION_APP_ENABLED=False)
    def test_leaderboard_global_disabled(self, client):
        """Should show unavailable message when feature disabled."""
        response = client.get(reverse('competition:leaderboard_global'))
        assert response.status_code == 200
        assert b'temporarily unavailable' in response.content.lower()
    
    @override_settings(COMPETITION_APP_ENABLED=True)
    def test_leaderboard_global_enabled(self, client):
        """Should show leaderboard when feature enabled."""
        response = client.get(reverse('competition:leaderboard_global'))
        assert response.status_code == 200
        assert b'global leaderboard' in response.content.lower()
    
    @override_settings(COMPETITION_APP_ENABLED=True)
    def test_leaderboard_global_tier_filter(self, client):
        """Should accept tier filter parameter."""
        response = client.get(reverse('competition:leaderboard_global') + '?tier=DIAMOND')
        assert response.status_code == 200
    
    @override_settings(COMPETITION_APP_ENABLED=True)
    def test_leaderboard_global_verified_only(self, client):
        """Should accept verified_only parameter."""
        response = client.get(reverse('competition:leaderboard_global') + '?verified_only=1')
        assert response.status_code == 200
    
    @override_settings(COMPETITION_APP_ENABLED=False)
    def test_leaderboard_game_disabled(self, client):
        """Should show unavailable message when feature disabled."""
        response = client.get(reverse('competition:leaderboard_game', kwargs={'game_id': 'LOL'}))
        assert response.status_code == 200
        assert b'temporarily unavailable' in response.content.lower()
