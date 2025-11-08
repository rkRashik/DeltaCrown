# Implements: Documents/ExecutionPlan/PHASE_4_IMPLEMENTATION_PLAN.md#module-43
# Implements: Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md#section-3.4-match-app
# Implements: Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md#section-4.4-match-models
# Tests: Module 4.3 - Match Management & Scheduling API

"""
Test Suite for Module 4.3: Match Management & Scheduling API

Tests match API endpoints, serializers, permissions, state transitions,
scheduling, lobby management, and WebSocket integration.

Coverage targets:
- API views: ≥80%
- Serializers: ≥90%
- Permissions: ≥85%
- Overall API: ≥80%

Test count target: ≥20 tests (15 unit + 5 integration)

Endpoints Tested:
- GET /api/matches/ - List matches (filterable, paginated)
- GET /api/matches/{id}/ - Retrieve match detail
- PATCH /api/matches/{id}/ - Update match (schedule, stream_url)
- POST /api/matches/{id}/start/ - Start match (→ LIVE state)
- POST /api/matches/bulk-schedule/ - Bulk schedule matches
- POST /api/matches/{id}/assign-coordinator/ - Assign coordinator
- PATCH /api/matches/{id}/lobby/ - Update lobby info
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import json

from apps.tournaments.models import Tournament, Game, Bracket, Match, Registration

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    """Create API client for making requests."""
    return APIClient()


@pytest.fixture
def organizer_user(db):
    """Create organizer user."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@test.com',
        password='testpass123'
    )


@pytest.fixture
def participant1_user(db):
    """Create participant1 user."""
    return User.objects.create_user(
        username='participant1',
        email='participant1@test.com',
        password='testpass123'
    )


@pytest.fixture
def participant2_user(db):
    """Create participant2 user."""
    return User.objects.create_user(
        username='participant2',
        email='participant2@test.com',
        password='testpass123'
    )


@pytest.fixture
def coordinator_user(db):
    """Create coordinator user."""
    return User.objects.create_user(
        username='coordinator',
        email='coordinator@test.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    """Create admin user (superuser)."""
    from django.contrib.auth.hashers import make_password
    user = User.objects.create(
        username='admin',
        email='admin@test.com',
        password=make_password('testpass123'),
        is_superuser=True,
        is_staff=True
    )
    return user


@pytest.fixture
def game(db):
    """Create game for tournaments."""
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='map_score',
        is_active=True,
        description='5v5 tactical shooter'
    )


@pytest.fixture
def tournament(db, organizer_user, game):
    """Create tournament for matches."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        description='Test tournament for match API',
        organizer=organizer_user,
        game=game,
        format='single_elimination',
        participation_type='solo',
        status='live',
        tournament_start=timezone.now(),
        registration_start=timezone.now() - timedelta(days=2),
        registration_end=timezone.now() - timedelta(hours=1),
        max_participants=8,
        min_participants=2,
        enable_check_in=True
    )


@pytest.fixture
def bracket(db, tournament):
    """Create bracket for matches."""
    return Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=3,
        total_matches=7,
        seeding_method=Bracket.SLOT_ORDER,
        is_finalized=False
    )


@pytest.fixture
def match_scheduled(db, tournament, bracket, participant1_user, participant2_user):
    """Create match in SCHEDULED state."""
    scheduled_time = timezone.now() + timedelta(hours=2)
    return Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        participant1_id=participant1_user.id,
        participant1_name=participant1_user.username,
        participant2_id=participant2_user.id,
        participant2_name=participant2_user.username,
        state=Match.SCHEDULED,
        scheduled_time=scheduled_time,
        check_in_deadline=scheduled_time - timedelta(minutes=30)
    )


@pytest.fixture
def match_ready(db, tournament, bracket, participant1_user, participant2_user):
    """Create match in READY state (both checked in)."""
    return Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=2,
        participant1_id=participant1_user.id,
        participant1_name=participant1_user.username,
        participant2_id=participant2_user.id,
        participant2_name=participant2_user.username,
        state=Match.READY,
        participant1_checked_in=True,
        participant2_checked_in=True,
        scheduled_time=timezone.now() + timedelta(hours=1)
    )


@pytest.fixture
def match_live(db, tournament, bracket, participant1_user, participant2_user):
    """Create match in LIVE state."""
    return Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=3,
        participant1_id=participant1_user.id,
        participant1_name=participant1_user.username,
        participant2_id=participant2_user.id,
        participant2_name=participant2_user.username,
        state=Match.LIVE,
        started_at=timezone.now(),
        scheduled_time=timezone.now()
    )


@pytest.fixture
def match_completed(db, tournament, bracket, participant1_user, participant2_user):
    """Create match in COMPLETED state."""
    return Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=4,
        participant1_id=participant1_user.id,
        participant1_name=participant1_user.username,
        participant2_id=participant2_user.id,
        participant2_name=participant2_user.username,
        state=Match.COMPLETED,
        participant1_score=13,
        participant2_score=11,
        winner_id=participant1_user.id,
        loser_id=participant2_user.id,
        started_at=timezone.now() - timedelta(hours=1),
        completed_at=timezone.now() - timedelta(minutes=30)
    )


# =============================================================================
# UNIT TESTS - List & Retrieve (4 tests)
# =============================================================================

@pytest.mark.django_db
class TestMatchListRetrieveAPI:
    """Test match list and retrieve endpoints."""
    
    def test_list_matches_success(self, api_client, match_scheduled, match_ready, match_live):
        """Test GET /api/matches/ lists all matches with pagination."""
        url = '/api/tournaments/matches/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # DRF pagination adds 'results' key
        if 'results' in response.data:
            assert len(response.data['results']) == 3
        else:
            assert len(response.data) == 3
    
    def test_list_matches_filter_by_tournament(self, api_client, match_scheduled, tournament):
        """Test filtering matches by tournament ID."""
        url = f'/api/tournaments/matches/?tournament={tournament.id}'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert all(match['tournament'] == tournament.id for match in results)
    
    def test_list_matches_filter_by_state(self, api_client, match_scheduled, match_ready, match_live):
        """Test filtering matches by state."""
        url = f'/api/tournaments/matches/?state={Match.LIVE}'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert all(match['state'] == Match.LIVE for match in results)
        assert len(results) == 1
    
    def test_retrieve_match_success(self, api_client, match_scheduled, participant1_user):
        """Test GET /api/matches/{id}/ retrieves match detail (participant authenticated)."""
        # Participant can view their own match
        api_client.force_authenticate(user=participant1_user)
        
        url = f'/api/tournaments/matches/{match_scheduled.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == match_scheduled.id
        assert response.data['state'] == Match.SCHEDULED
        assert 'lobby_info' in response.data
        assert 'scheduled_time' in response.data


# =============================================================================
# UNIT TESTS - Update Match (3 tests)
# =============================================================================

@pytest.mark.django_db
class TestMatchUpdateAPI:
    """Test match update endpoint (schedule, stream_url)."""
    
    def test_update_scheduled_time_success_organizer(
        self, api_client, match_scheduled, organizer_user
    ):
        """Test organizer can update scheduled_time."""
        api_client.force_authenticate(user=organizer_user)
        
        new_time = timezone.now() + timedelta(hours=4)
        url = f'/api/tournaments/matches/{match_scheduled.id}/'
        response = api_client.patch(url, {
            'scheduled_time': new_time.isoformat()
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        match_scheduled.refresh_from_db()
        assert match_scheduled.scheduled_time.replace(microsecond=0) == new_time.replace(microsecond=0)
    
    def test_update_stream_url_success(self, api_client, match_ready, organizer_user):
        """Test organizer can update stream_url."""
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/'
        response = api_client.patch(url, {
            'stream_url': 'https://twitch.tv/test_stream'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        match_ready.refresh_from_db()
        assert match_ready.stream_url == 'https://twitch.tv/test_stream'
    
    def test_update_match_forbidden_non_organizer(
        self, api_client, match_scheduled, participant1_user
    ):
        """Test non-organizer cannot update match."""
        api_client.force_authenticate(user=participant1_user)
        
        url = f'/api/tournaments/matches/{match_scheduled.id}/'
        response = api_client.patch(url, {
            'scheduled_time': timezone.now().isoformat()
        }, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# UNIT TESTS - Start Match (4 tests)
# =============================================================================

@pytest.mark.django_db
class TestMatchStartAPI:
    """Test match start endpoint (state transition to LIVE)."""
    
    @patch('apps.tournaments.services.match_service.broadcast_match_started')
    def test_start_match_success_organizer(
        self, mock_broadcast, api_client, match_ready, organizer_user
    ):
        """Test organizer can start match in READY state."""
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/start/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['state'] == Match.LIVE
        assert response.data['started_at'] is not None
        
        # Verify match updated in database
        match_ready.refresh_from_db()
        assert match_ready.state == Match.LIVE
        assert match_ready.started_at is not None
        
        # Verify WebSocket broadcast called
        mock_broadcast.assert_called_once()
    
    def test_start_match_invalid_state_scheduled(
        self, api_client, match_scheduled, organizer_user
    ):
        """Test cannot start match from SCHEDULED state (must be READY)."""
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/matches/{match_scheduled.id}/start/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Check for 'READY' in either 'detail' key or the full response data (serializer errors)
        response_str = str(response.data)
        assert 'READY' in response_str
    
    def test_start_match_invalid_state_completed(
        self, api_client, match_completed, organizer_user
    ):
        """Test cannot start already completed match."""
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/matches/{match_completed.id}/start/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_start_match_forbidden_participant(
        self, api_client, match_ready, participant1_user
    ):
        """Test participant cannot start match (organizer only)."""
        api_client.force_authenticate(user=participant1_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/start/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# UNIT TESTS - Bulk Schedule (4 tests)
# =============================================================================

@pytest.mark.django_db
class TestBulkScheduleAPI:
    """Test bulk match scheduling endpoint."""
    
    def test_bulk_schedule_success_organizer(
        self, api_client, match_scheduled, match_ready, organizer_user
    ):
        """Test organizer can bulk schedule multiple matches."""
        api_client.force_authenticate(user=organizer_user)
        
        new_time = timezone.now() + timedelta(hours=5)
        url = '/api/tournaments/matches/bulk-schedule/'
        response = api_client.post(url, {
            'match_ids': [match_scheduled.id, match_ready.id],
            'scheduled_time': new_time.isoformat()
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['scheduled_count'] == 2
        assert len(response.data['match_ids']) == 2
        
        # Verify matches updated
        match_scheduled.refresh_from_db()
        match_ready.refresh_from_db()
        assert match_scheduled.scheduled_time.replace(microsecond=0) == new_time.replace(microsecond=0)
        assert match_ready.scheduled_time.replace(microsecond=0) == new_time.replace(microsecond=0)
    
    def test_bulk_schedule_validation_past_time(
        self, api_client, match_scheduled, organizer_user
    ):
        """Test bulk schedule rejects past scheduled_time."""
        api_client.force_authenticate(user=organizer_user)
        
        past_time = timezone.now() - timedelta(hours=1)
        url = '/api/tournaments/matches/bulk-schedule/'
        response = api_client.post(url, {
            'match_ids': [match_scheduled.id],
            'scheduled_time': past_time.isoformat()
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_bulk_schedule_validation_duplicate_ids(
        self, api_client, match_scheduled, organizer_user
    ):
        """Test bulk schedule rejects duplicate match IDs."""
        api_client.force_authenticate(user=organizer_user)
        
        url = '/api/tournaments/matches/bulk-schedule/'
        response = api_client.post(url, {
            'match_ids': [match_scheduled.id, match_scheduled.id],
            'scheduled_time': timezone.now().isoformat()
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_bulk_schedule_forbidden_non_organizer(
        self, api_client, match_scheduled, participant1_user
    ):
        """Test non-organizer cannot bulk schedule matches."""
        api_client.force_authenticate(user=participant1_user)
        
        # Use future time to pass serializer validation (permission check happens after)
        future_time = timezone.now() + timedelta(hours=3)
        url = '/api/tournaments/matches/bulk-schedule/'
        response = api_client.post(url, {
            'match_ids': [match_scheduled.id],
            'scheduled_time': future_time.isoformat()
        }, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# UNIT TESTS - Coordinator Assignment (3 tests)
# =============================================================================

@pytest.mark.django_db
class TestCoordinatorAssignmentAPI:
    """Test coordinator assignment endpoint."""
    
    def test_assign_coordinator_success_organizer(
        self, api_client, match_ready, coordinator_user, organizer_user
    ):
        """Test organizer can assign coordinator to match."""
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/assign-coordinator/'
        response = api_client.post(url, {
            'coordinator_id': coordinator_user.id
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['lobby_info']['coordinator_id'] == coordinator_user.id
        
        # Verify match updated
        match_ready.refresh_from_db()
        assert match_ready.lobby_info['coordinator_id'] == coordinator_user.id
        assert 'coordinator_assigned_at' in match_ready.lobby_info
    
    def test_assign_coordinator_validation_nonexistent_user(
        self, api_client, match_ready, organizer_user
    ):
        """Test coordinator assignment rejects nonexistent user ID."""
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/assign-coordinator/'
        response = api_client.post(url, {
            'coordinator_id': 999999
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_assign_coordinator_forbidden_participant(
        self, api_client, match_ready, coordinator_user, participant1_user
    ):
        """Test participant cannot assign coordinator."""
        api_client.force_authenticate(user=participant1_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/assign-coordinator/'
        response = api_client.post(url, {
            'coordinator_id': coordinator_user.id
        }, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# UNIT TESTS - Lobby Info Management (4 tests)
# =============================================================================

@pytest.mark.django_db
class TestLobbyInfoAPI:
    """Test lobby info update endpoint."""
    
    def test_update_lobby_info_success_organizer(
        self, api_client, match_ready, organizer_user
    ):
        """Test organizer can update lobby_info."""
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/lobby/'
        response = api_client.patch(url, {
            'room_code': 'VAL123',
            'region': 'NA',
            'map': 'Bind'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['lobby_info']['room_code'] == 'VAL123'
        assert response.data['lobby_info']['region'] == 'NA'
        
        # Verify match updated
        match_ready.refresh_from_db()
        assert match_ready.lobby_info['room_code'] == 'VAL123'
        assert match_ready.lobby_info['region'] == 'NA'
        assert 'updated_at' in match_ready.lobby_info
    
    def test_update_lobby_info_merge_existing(
        self, api_client, match_ready, organizer_user
    ):
        """Test lobby info update merges with existing data."""
        # Set initial lobby info
        match_ready.lobby_info = {'existing_key': 'existing_value'}
        match_ready.save()
        
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/lobby/'
        response = api_client.patch(url, {
            'room_code': 'VAL456'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify merge (existing key preserved)
        match_ready.refresh_from_db()
        assert match_ready.lobby_info['existing_key'] == 'existing_value'
        assert match_ready.lobby_info['room_code'] == 'VAL456'
    
    def test_update_lobby_info_validation_no_identifiers(
        self, api_client, match_ready, organizer_user
    ):
        """Test lobby info update requires at least one identifier."""
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/lobby/'
        response = api_client.patch(url, {
            'notes': 'Just a note, no lobby ID'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_update_lobby_info_forbidden_participant(
        self, api_client, match_ready, participant1_user
    ):
        """Test participant cannot update lobby info."""
        api_client.force_authenticate(user=participant1_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/lobby/'
        response = api_client.patch(url, {
            'room_code': 'VAL789'
        }, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# INTEGRATION TESTS - Permissions (2 tests)
# =============================================================================

@pytest.mark.django_db
class TestMatchPermissions:
    """Test match permission enforcement across endpoints."""
    
    def test_admin_has_full_access(
        self, api_client, match_ready, admin_user
    ):
        """Test admin user has full access to all match endpoints."""
        api_client.force_authenticate(user=admin_user)
        
        # Start match
        url = f'/api/tournaments/matches/{match_ready.id}/start/'
        response = api_client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_200_OK
    
    def test_participant_read_only_access(
        self, api_client, match_ready, participant1_user
    ):
        """Test participant can read but not modify their match."""
        api_client.force_authenticate(user=participant1_user)
        
        # Can retrieve match
        url = f'/api/tournaments/matches/{match_ready.id}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        # Cannot update match
        response = api_client.patch(url, {
            'scheduled_time': timezone.now().isoformat()
        }, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# INTEGRATION TESTS - Audit Logging (1 test)
# =============================================================================

@pytest.mark.django_db
class TestMatchAuditLogging:
    """Test audit logging for sensitive match operations."""
    
    @patch('apps.tournaments.api.match_views.audit_event')
    def test_match_start_creates_audit_log(
        self, mock_audit, api_client, match_ready, organizer_user
    ):
        """Test match start creates audit log entry."""
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/matches/{match_ready.id}/start/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify audit_event called
        mock_audit.assert_called()
        call_kwargs = mock_audit.call_args[1]
        assert call_kwargs['user'] == organizer_user
        assert 'match_id' in call_kwargs['meta']


# =============================================================================
# Test Summary
# =============================================================================

"""
Test Summary for Module 4.3:

Total Tests: 23 tests
- List/Retrieve: 4 tests
- Update Match: 3 tests
- Start Match: 4 tests
- Bulk Schedule: 4 tests
- Coordinator Assignment: 3 tests
- Lobby Info: 4 tests
- Permissions Integration: 2 tests
- Audit Logging: 1 test

Coverage Areas:
✅ All 7 endpoints tested
✅ Permissions (organizer, participant, admin)
✅ Validation (state transitions, field guards)
✅ Filtering & pagination (list endpoint)
✅ State machine enforcement (start match)
✅ Bulk operations (bulk schedule)
✅ JSONB field management (lobby_info)
✅ Coordinator assignment
✅ WebSocket integration (mocked)
✅ Audit logging (mocked)

Expected Pass Rate: ≥95% (22-23/23 passing)
Expected Coverage: ≥80% for match API views and serializers
"""


