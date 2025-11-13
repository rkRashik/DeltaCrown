"""
API tests for Milestone E: Leaderboard & Standings.

Tests the REST API endpoints for leaderboards, series summaries, and placement overrides.

Endpoints Tested:
- GET /api/tournaments/{id}/leaderboard/ - BR leaderboard
- GET /api/tournaments/{id}/series/{match_id}/ - Series summary
- POST /api/tournaments/{id}/override-placement/ - Staff override

Test Coverage:
- Request validation (missing/invalid parameters)
- Permission checks (authentication, staff-only)
- Service integration (LeaderboardService delegation)
- Response format (serializers)
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.tournaments.models import Game, Tournament, Registration

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create regular user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def staff_user(db):
    """Create staff user."""
    return User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        password='staffpass123',
        is_staff=True
    )


@pytest.fixture
def tournament(db, staff_user):
    """Create a tournament."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.utils import timezone
    
    # Create game
    fake_icon = SimpleUploadedFile(
        name='test.png',
        content=b'fake-image-content',
        content_type='image/png'
    )
    
    game = Game.objects.create(
        name='Test Game',
        slug='test-game',
        icon=fake_icon,
        default_team_size=Game.TEAM_SIZE_5V5,
        profile_id_field='game_id',
        default_result_type=Game.MAP_SCORE,
    )
    
    now = timezone.now()
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        description='Test Description',
        game=game,
        organizer=staff_user,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.TEAM,
        tournament_start=now,
        registration_start=now - timezone.timedelta(days=7),
        registration_end=now - timezone.timedelta(days=1),
        min_participants=4,
        max_participants=16,
        status=Tournament.LIVE
    )


@pytest.mark.django_db
class TestBRLeaderboardAPI:
    """Test BR leaderboard endpoint."""
    
    def test_br_leaderboard_requires_auth(self, api_client, tournament):
        """Unauthenticated request returns 401."""
        url = reverse('tournaments_api:leaderboard-br-leaderboard', args=[tournament.id])
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_br_leaderboard_requires_match_ids(self, api_client, user, tournament):
        """Missing match_ids parameter returns 400."""
        api_client.force_authenticate(user=user)
        url = reverse('tournaments_api:leaderboard-br-leaderboard', args=[tournament.id])
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'match_ids' in response.data['error']
    
    def test_br_leaderboard_invalid_game_type(self, api_client, user, tournament):
        """Non-BR game returns 400."""
        api_client.force_authenticate(user=user)
        url = reverse('tournaments_api:leaderboard-br-leaderboard', args=[tournament.id])
        response = api_client.get(url, {'match_ids': '1,2,3'})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'not a BR game' in response.data['error']


@pytest.mark.django_db
class TestSeriesSummaryAPI:
    """Test series summary endpoint."""
    
    def test_series_summary_requires_auth(self, api_client, tournament):
        """Unauthenticated request returns 401."""
        url = reverse('tournaments_api:leaderboard-series-summary', args=[tournament.id, 1])
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_series_summary_empty_matches(self, api_client, user, tournament):
        """No completed matches returns 400."""
        api_client.force_authenticate(user=user)
        url = reverse('tournaments_api:leaderboard-series-summary', args=[tournament.id, 99999])
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'No completed matches' in response.data['error']


@pytest.mark.django_db
class TestPlacementOverrideAPI:
    """Test placement override endpoint."""
    
    def test_override_requires_auth(self, api_client, tournament):
        """Unauthenticated request returns 401."""
        url = reverse('tournaments_api:leaderboard-override-placement', args=[tournament.id])
        response = api_client.post(url, {
            'registration_id': 1,
            'new_rank': 1,
            'reason': 'Test reason that is long enough'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_override_requires_staff(self, api_client, user, tournament):
        """Non-staff user returns 403."""
        api_client.force_authenticate(user=user)
        url = reverse('tournaments_api:leaderboard-override-placement', args=[tournament.id])
        response = api_client.post(url, {
            'registration_id': 1,
            'new_rank': 1,
            'reason': 'Test reason that is long enough'
        }, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_override_missing_reason(self, api_client, staff_user, tournament):
        """Missing reason returns 400."""
        api_client.force_authenticate(user=staff_user)
        url = reverse('tournaments_api:leaderboard-override-placement', args=[tournament.id])
        response = api_client.post(url, {
            'registration_id': 1,
            'new_rank': 1,
            'reason': ''
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_override_short_reason(self, api_client, staff_user, tournament):
        """Short reason (<10 chars) returns 400."""
        api_client.force_authenticate(user=staff_user)
        url = reverse('tournaments_api:leaderboard-override-placement', args=[tournament.id])
        response = api_client.post(url, {
            'registration_id': 1,
            'new_rank': 1,
            'reason': 'short'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'at least 10 characters' in str(response.data)
    
    def test_override_invalid_rank(self, api_client, staff_user, tournament):
        """Rank < 1 returns 400."""
        api_client.force_authenticate(user=staff_user)
        url = reverse('tournaments_api:leaderboard-override-placement', args=[tournament.id])
        response = api_client.post(url, {
            'registration_id': 1,
            'new_rank': 0,
            'reason': 'Test reason that is long enough'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_override_nonexistent_registration(self, api_client, staff_user, tournament):
        """Nonexistent registration returns 404."""
        api_client.force_authenticate(user=staff_user)
        url = reverse('tournaments_api:leaderboard-override-placement', args=[tournament.id])
        response = api_client.post(url, {
            'registration_id': 99999,
            'new_rank': 1,
            'reason': 'Test reason that is long enough'
        }, format='json')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_override_success(self, api_client, staff_user, tournament):
        """Valid override returns 200 with audit trail."""
        # Create a registration
        registration = Registration.objects.create(
            tournament=tournament,
            user=staff_user,
            status=Registration.CONFIRMED
        )
        
        api_client.force_authenticate(user=staff_user)
        url = reverse('tournaments_api:leaderboard-override-placement', args=[tournament.id])
        response = api_client.post(url, {
            'registration_id': registration.id,
            'new_rank': 1,
            'reason': 'Manual correction after dispute resolution'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['new_rank'] == 1
        assert response.data['override_actor_id'] == staff_user.id
        assert 'override_timestamp' in response.data
        assert 'result_id' in response.data


@pytest.mark.django_db
class TestLeaderboardAPIIntegration:
    """Integration tests for leaderboard API."""
    
    def test_all_endpoints_registered(self, api_client, user, tournament):
        """Verify all endpoints are registered."""
        api_client.force_authenticate(user=user)
        
        # BR leaderboard
        url = reverse('tournaments_api:leaderboard-br-leaderboard', args=[tournament.id])
        assert url is not None
        
        # Series summary
        url = reverse('tournaments_api:leaderboard-series-summary', args=[tournament.id, 1])
        assert url is not None
        
        # Override placement
        url = reverse('tournaments_api:leaderboard-override-placement', args=[tournament.id])
        assert url is not None
