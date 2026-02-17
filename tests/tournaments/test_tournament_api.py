"""
Module 2.1 - Tournament API Integration Tests

Comprehensive API integration tests for Tournament CRUD endpoints.

Test Coverage:
- TestTournamentList: 3 tests (list all, filter by status, filter by game)
- TestTournamentCreate: 5 tests (authenticated, anonymous, invalid data, happy path, organizer auto-set)
- TestTournamentRetrieve: 2 tests (public access, detail serializer)
- TestTournamentUpdate: 6 tests (organizer success, non-organizer, staff, DRAFT only, partial updates)
- TestPublishAction: 2 tests (organizer success, status transition)
- TestCancelAction: 2 tests (organizer success, reason parameter)

Architecture Decisions:
- ADR-002: API Design Patterns - RESTful, DRF ViewSets
- ADR-006: Permission System - IsAuthenticatedOrReadOnly
- ADR-008: Security - IDs-only discipline, no PII exposure

Source Documents:
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (API Testing)
- Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md (API Standards)
"""

import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.tournaments.models.tournament import Tournament
from apps.games.models.game import Game
from apps.tournaments.services.tournament_service import TournamentService

User = get_user_model()

pytestmark = pytest.mark.django_db


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """DRF API client."""
    return APIClient()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='password123'
    )


@pytest.fixture
def staff_user():
    """Create a staff user."""
    return User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        password='password123',
        is_staff=True
    )


@pytest.fixture
def other_user():
    """Create another user."""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='password123'
    )


@pytest.fixture
def game():
    """Create a test game."""
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='map_score',
        is_active=True
    )


@pytest.fixture
def game2():
    """Create a second test game."""
    return Game.objects.create(
        name='CS:GO',
        slug='csgo',
        default_team_size=5,
        profile_id_field='steam_id',
        default_result_type='map_score',
        is_active=True
    )


@pytest.fixture
def draft_tournament(user, game):
    """Create a DRAFT tournament."""
    now = timezone.now()
    data = {
        'name': 'Draft Tournament',
        'description': 'Test draft tournament',
        'game_id': game.id,
        'format': Tournament.SINGLE_ELIM,
        'participation_type': Tournament.TEAM,
        'max_participants': 16,
        'min_participants': 4,
        'registration_start': now + timedelta(days=1),
        'registration_end': now + timedelta(days=7),
        'tournament_start': now + timedelta(days=10),
    }
    return TournamentService.create_tournament(organizer=user, data=data)


@pytest.fixture
def published_tournament(user, game):
    """Create a PUBLISHED tournament."""
    now = timezone.now()
    data = {
        'name': 'Published Tournament',
        'description': 'Test published tournament',
        'game_id': game.id,
        'format': Tournament.DOUBLE_ELIM,
        'participation_type': Tournament.TEAM,
        'max_participants': 32,
        'min_participants': 8,
        'registration_start': now + timedelta(days=2),
        'registration_end': now + timedelta(days=14),
        'tournament_start': now + timedelta(days=20),
    }
    tournament = TournamentService.create_tournament(organizer=user, data=data)
    TournamentService.publish_tournament(tournament_id=tournament.id, user=user)
    return tournament


# ============================================================================
# Test Tournament List
# ============================================================================

class TestTournamentList:
    """Test GET /api/tournaments/ - List tournaments."""
    
    def test_list_tournaments_public_access(self, api_client, published_tournament):
        """Anonymous users can list published tournaments."""
        url = reverse('tournaments_api:tournament-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == 'Published Tournament'
    
    def test_list_tournaments_filter_by_status(self, api_client, user, draft_tournament, published_tournament):
        """Filter tournaments by status."""
        # Authenticate to see draft tournament
        api_client.force_authenticate(user=user)
        
        # Filter by PUBLISHED
        url = reverse('tournaments_api:tournament-list')
        response = api_client.get(url, {'status': Tournament.PUBLISHED})
        
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) >= 1
        assert all(t['status'] in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN] for t in results)
    
    def test_list_tournaments_filter_by_game(self, api_client, user, game, game2):
        """Filter tournaments by game."""
        # Create tournaments with different games
        now = timezone.now()
        data1 = {
            'name': 'Valorant Tournament',
            'description': 'Test Valorant tournament',
            'game_id': game.id,
            'format': Tournament.SINGLE_ELIM,
            'max_participants': 16,
            'registration_start': now + timedelta(days=1),
            'registration_end': now + timedelta(days=7),
            'tournament_start': now + timedelta(days=10),
        }
        data2 = {
            'name': 'CS:GO Tournament',
            'description': 'Test CS:GO tournament',
            'game_id': game2.id,
            'format': Tournament.SINGLE_ELIM,
            'max_participants': 16,
            'registration_start': now + timedelta(days=1),
            'registration_end': now + timedelta(days=7),
            'tournament_start': now + timedelta(days=10),
        }
        
        t1 = TournamentService.create_tournament(organizer=user, data=data1)
        t2 = TournamentService.create_tournament(organizer=user, data=data2)
        TournamentService.publish_tournament(tournament_id=t1.id, user=user)
        TournamentService.publish_tournament(tournament_id=t2.id, user=user)
        
        # Filter by Valorant
        url = reverse('tournaments_api:tournament-list')
        response = api_client.get(url, {'game': game.id})
        
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) >= 1
        assert all(t['game_name'] == 'Valorant' for t in results)


# ============================================================================
# Test Tournament Create
# ============================================================================

class TestTournamentCreate:
    """Test POST /api/tournaments/ - Create tournament."""
    
    def test_create_tournament_authenticated(self, api_client, user, game):
        """Authenticated user can create tournament."""
        api_client.force_authenticate(user=user)
        
        now = timezone.now()
        data = {
            'name': 'New Tournament',
            'description': 'Test tournament',
            'game_id': game.id,
            'format': Tournament.SINGLE_ELIM,
            'participation_type': Tournament.TEAM,
            'max_participants': 16,
            'min_participants': 4,
            'registration_start': (now + timedelta(days=1)).isoformat(),
            'registration_end': (now + timedelta(days=7)).isoformat(),
            'tournament_start': (now + timedelta(days=10)).isoformat(),
        }
        
        url = reverse('tournaments_api:tournament-list')
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Tournament'
        assert response.data['status'] == Tournament.DRAFT
        assert response.data['organizer_username'] == user.username
        
        # Verify tournament created in database
        tournament = Tournament.objects.get(id=response.data['id'])
        assert tournament.organizer == user
    
    def test_create_tournament_anonymous_denied(self, api_client, game):
        """Anonymous users cannot create tournaments."""
        now = timezone.now()
        data = {
            'name': 'Anonymous Tournament',
            'description': 'Test anonymous tournament',
            'game_id': game.id,
            'format': Tournament.SINGLE_ELIM,
            'max_participants': 16,
            'registration_start': (now + timedelta(days=1)).isoformat(),
            'registration_end': (now + timedelta(days=7)).isoformat(),
            'tournament_start': (now + timedelta(days=10)).isoformat(),
        }
        
        url = reverse('tournaments_api:tournament-list')
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_tournament_invalid_data(self, api_client, user, game):
        """Validation error: Invalid dates."""
        api_client.force_authenticate(user=user)
        
        now = timezone.now()
        data = {
            'name': 'Invalid Tournament',
            'description': 'Test invalid tournament',
            'game_id': game.id,
            'format': Tournament.SINGLE_ELIM,
            'max_participants': 16,
            'registration_start': (now + timedelta(days=10)).isoformat(),
            'registration_end': (now + timedelta(days=5)).isoformat(),  # Before start
            'tournament_start': (now + timedelta(days=15)).isoformat(),
        }
        
        url = reverse('tournaments_api:tournament-list')
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'registration_end' in response.data
    
    def test_create_tournament_organizer_auto_set(self, api_client, user, game):
        """Organizer is auto-set from request.user (not from request body)."""
        api_client.force_authenticate(user=user)
        
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='password123'
        )
        
        now = timezone.now()
        data = {
            'name': 'Organizer Test',
            'description': 'Test organizer auto-set',
            'game_id': game.id,
            'format': Tournament.SINGLE_ELIM,
            'max_participants': 16,
            'registration_start': (now + timedelta(days=1)).isoformat(),
            'registration_end': (now + timedelta(days=7)).isoformat(),
            'tournament_start': (now + timedelta(days=10)).isoformat(),
            'organizer_id': other_user.id,  # Try to set organizer (should be ignored)
        }
        
        url = reverse('tournaments_api:tournament-list')
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['organizer_username'] == user.username  # Request user, not other_user
        
        tournament = Tournament.objects.get(id=response.data['id'])
        assert tournament.organizer == user
    
    def test_create_tournament_missing_required_fields(self, api_client, user):
        """Validation error: Missing required fields."""
        api_client.force_authenticate(user=user)
        
        data = {
            'name': 'Incomplete Tournament',
            'description': 'Test incomplete tournament',
            # Missing: game_id, format, max_participants, dates
        }
        
        url = reverse('tournaments_api:tournament-list')
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'game_id' in response.data or 'format' in response.data


# ============================================================================
# Test Tournament Retrieve
# ============================================================================

class TestTournamentRetrieve:
    """Test GET /api/tournaments/{id}/ - Retrieve tournament detail."""
    
    def test_retrieve_tournament_public_access(self, api_client, published_tournament):
        """Anonymous users can view published tournament details."""
        url = reverse('tournaments_api:tournament-detail', kwargs={'pk': published_tournament.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == published_tournament.id
        assert response.data['name'] == 'Published Tournament'
        assert 'description' in response.data
        assert 'game' in response.data
        assert 'prize_pool' in response.data
    
    def test_retrieve_tournament_draft_owner_access(self, api_client, user, draft_tournament):
        """Organizer can view their own DRAFT tournament."""
        api_client.force_authenticate(user=user)
        
        url = reverse('tournaments_api:tournament-detail', kwargs={'pk': draft_tournament.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == draft_tournament.id
        assert response.data['status'] == Tournament.DRAFT


# ============================================================================
# Test Tournament Update
# ============================================================================

class TestTournamentUpdate:
    """Test PATCH /api/tournaments/{id}/ - Update tournament."""
    
    def test_update_tournament_organizer_success(self, api_client, user, draft_tournament):
        """Organizer can update their DRAFT tournament."""
        api_client.force_authenticate(user=user)
        
        data = {
            'name': 'Updated Name',
            'description': 'Updated description',
            'max_participants': 32,
        }
        
        url = reverse('tournaments_api:tournament-detail', kwargs={'pk': draft_tournament.id})
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Name'
        assert response.data['description'] == 'Updated description'
        assert response.data['max_participants'] == 32
    
    def test_update_tournament_non_organizer_denied(self, api_client, other_user, draft_tournament):
        """Non-organizer cannot update tournament."""
        api_client.force_authenticate(user=other_user)
        
        data = {'name': 'Hacked Name'}
        
        url = reverse('tournaments_api:tournament-detail', kwargs={'pk': draft_tournament.id})
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_update_tournament_staff_success(self, api_client, staff_user, draft_tournament):
        """Staff can update any DRAFT tournament."""
        api_client.force_authenticate(user=staff_user)
        
        data = {'name': 'Staff Updated'}
        
        url = reverse('tournaments_api:tournament-detail', kwargs={'pk': draft_tournament.id})
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Staff Updated'
    
    def test_update_tournament_non_draft_denied(self, api_client, user, published_tournament):
        """Cannot update non-DRAFT tournament."""
        api_client.force_authenticate(user=user)
        
        data = {'name': 'Should Fail'}
        
        url = reverse('tournaments_api:tournament-detail', kwargs={'pk': published_tournament.id})
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Only DRAFT tournaments can be edited' in str(response.data)
    
    def test_update_tournament_partial_fields(self, api_client, user, draft_tournament):
        """Partial update: Only provided fields are updated."""
        api_client.force_authenticate(user=user)
        
        original_description = draft_tournament.description
        
        data = {'name': 'Partial Update Only'}
        
        url = reverse('tournaments_api:tournament-detail', kwargs={'pk': draft_tournament.id})
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Partial Update Only'
        assert response.data['description'] == original_description  # Unchanged
    
    def test_update_tournament_invalid_data(self, api_client, user, draft_tournament):
        """Validation error: Invalid participant count."""
        api_client.force_authenticate(user=user)
        
        data = {'min_participants': 100}  # Greater than max (16)
        
        url = reverse('tournaments_api:tournament-detail', kwargs={'pk': draft_tournament.id})
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Test Publish Action
# ============================================================================

class TestPublishAction:
    """Test POST /api/tournaments/{id}/publish/ - Publish tournament."""
    
    def test_publish_tournament_organizer_success(self, api_client, user, draft_tournament):
        """Organizer can publish their DRAFT tournament."""
        api_client.force_authenticate(user=user)
        
        url = reverse('tournaments_api:tournament-publish', kwargs={'pk': draft_tournament.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'published successfully' in response.data['message'].lower()
        assert response.data['tournament']['status'] in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN]
        
        # Verify tournament status changed
        draft_tournament.refresh_from_db()
        assert draft_tournament.status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN]
        assert draft_tournament.published_at is not None
    
    def test_publish_tournament_status_transition(self, api_client, user, draft_tournament):
        """Verify correct status transition (DRAFT → PUBLISHED/REGISTRATION_OPEN)."""
        api_client.force_authenticate(user=user)
        
        # Set registration_start to future → should be PUBLISHED
        now = timezone.now()
        draft_tournament.registration_start = now + timedelta(days=2)
        draft_tournament.save()
        
        url = reverse('tournaments_api:tournament-publish', kwargs={'pk': draft_tournament.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['tournament']['status'] == Tournament.PUBLISHED


# ============================================================================
# Test Cancel Action
# ============================================================================

class TestCancelAction:
    """Test POST /api/tournaments/{id}/cancel/ - Cancel tournament."""
    
    def test_cancel_tournament_organizer_success(self, api_client, user, draft_tournament):
        """Organizer can cancel their tournament."""
        api_client.force_authenticate(user=user)
        
        data = {'reason': 'Changed plans'}
        
        url = reverse('tournaments_api:tournament-cancel', kwargs={'pk': draft_tournament.id})
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'cancelled successfully' in response.data['message'].lower()
        assert response.data['tournament']['status'] == Tournament.CANCELLED
        
        # Verify tournament status changed
        draft_tournament.refresh_from_db()
        assert draft_tournament.status == Tournament.CANCELLED
        assert draft_tournament.is_deleted is True
    
    def test_cancel_tournament_reason_parameter(self, api_client, user, draft_tournament):
        """Cancel with reason parameter (audit trail)."""
        api_client.force_authenticate(user=user)
        
        reason = 'Organizer personal emergency'
        data = {'reason': reason}
        
        url = reverse('tournaments_api:tournament-cancel', kwargs={'pk': draft_tournament.id})
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify reason in audit version
        from apps.tournaments.models.tournament import TournamentVersion
        version = TournamentVersion.objects.filter(tournament=draft_tournament).order_by('-version_number').first()
        assert reason in version.change_summary
