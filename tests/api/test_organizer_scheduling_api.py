"""
API Tests for Organizer Scheduling Endpoints - Phase 7, Epic 7.2

Tests for DRF views handling organizer manual scheduling.

Test Coverage:
- GET /api/tournaments/v1/organizer/scheduling/ (list matches)
- POST /api/tournaments/v1/organizer/scheduling/ (assign match)
- POST /api/tournaments/v1/organizer/scheduling/bulk-shift/ (bulk shift)
- GET /api/tournaments/v1/organizer/scheduling/slots/ (generate slots)
- Permission checks
- Input validation
- Error handling

Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.tournament_ops.dtos.scheduling import (
    MatchSchedulingItemDTO,
    SchedulingSlotDTO,
    SchedulingConflictDTO,
    BulkShiftResultDTO,
)

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def organizer_user(db):
    """Create organizer user."""
    user = User.objects.create_user(
        username='organizer',
        email='organizer@test.com',
        password='testpass123'
    )
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def regular_user(db):
    """Create regular user (not organizer)."""
    return User.objects.create_user(
        username='player',
        email='player@test.com',
        password='testpass123'
    )


@pytest.fixture
def sample_matches():
    """Create sample MatchSchedulingItemDTO objects."""
    return [
        MatchSchedulingItemDTO(
            match_id=101,
            tournament_id=1,
            tournament_name="Summer Championship",
            stage_id=10,
            stage_name="Finals",
            round_number=1,
            match_number=1,
            participant1_id=201,
            participant1_name="Team Alpha",
            participant2_id=202,
            participant2_name="Team Beta",
            scheduled_time=None,
            estimated_duration_minutes=60,
            state="pending",
            lobby_info={},
            conflicts=[],
            can_reschedule=True
        ),
        MatchSchedulingItemDTO(
            match_id=102,
            tournament_id=1,
            tournament_name="Summer Championship",
            stage_id=10,
            stage_name="Finals",
            round_number=1,
            match_number=2,
            participant1_id=203,
            participant1_name="Team Gamma",
            participant2_id=204,
            participant2_name="Team Delta",
            scheduled_time=datetime(2025, 12, 15, 14, 0, 0, tzinfo=timezone.utc),
            estimated_duration_minutes=60,
            state="scheduled",
            lobby_info={},
            conflicts=["Team Gamma has overlapping match"],
            can_reschedule=True
        ),
    ]


@pytest.fixture
def sample_slots():
    """Create sample SchedulingSlotDTO objects."""
    return [
        SchedulingSlotDTO(
            slot_start=datetime(2025, 12, 15, 9, 0, 0, tzinfo=timezone.utc),
            slot_end=datetime(2025, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
            duration_minutes=60,
            is_available=True,
            conflicts=[],
            suggested_matches=[101]
        ),
        SchedulingSlotDTO(
            slot_start=datetime(2025, 12, 15, 10, 15, 0, tzinfo=timezone.utc),
            slot_end=datetime(2025, 12, 15, 11, 15, 0, tzinfo=timezone.utc),
            duration_minutes=60,
            is_available=False,
            conflicts=["Occupied by match 102"],
            suggested_matches=[]
        ),
    ]


@pytest.mark.django_db
class TestOrganizerSchedulingListView:
    """Tests for GET /api/tournaments/v1/organizer/scheduling/."""
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_list_matches_success(
        self,
        mock_service_class,
        api_client,
        organizer_user,
        sample_matches
    ):
        """Test successful listing of matches for scheduling."""
        # Mock service
        mock_service = Mock()
        mock_service.list_matches_for_scheduling.return_value = sample_matches
        mock_service_class.return_value = mock_service
        
        # Authenticate
        api_client.force_authenticate(user=organizer_user)
        
        # Make request
        response = api_client.get('/api/tournaments/v1/organizer/scheduling/')
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'matches' in response.data
        assert response.data['count'] == 2
        assert len(response.data['matches']) == 2
        
        # Verify service called correctly
        mock_service.list_matches_for_scheduling.assert_called_once()
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_list_matches_with_filters(
        self,
        mock_service_class,
        api_client,
        organizer_user,
        sample_matches
    ):
        """Test listing matches with query parameter filters."""
        mock_service = Mock()
        mock_service.list_matches_for_scheduling.return_value = [sample_matches[0]]
        mock_service_class.return_value = mock_service
        
        api_client.force_authenticate(user=organizer_user)
        
        # Request with filters
        response = api_client.get(
            '/api/tournaments/v1/organizer/scheduling/',
            {
                'tournament_id': 1,
                'stage_id': 10,
                'unscheduled_only': 'true',
                'with_conflicts': 'false'
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify service called with correct params
        call_args = mock_service.list_matches_for_scheduling.call_args
        assert call_args.kwargs['tournament_id'] == 1
        assert call_args.kwargs['stage_id'] == 10
        assert call_args.kwargs['filters']['unscheduled_only'] is True
        assert call_args.kwargs['filters']['with_conflicts'] is False
    
    def test_list_matches_unauthenticated(self, api_client):
        """Test listing matches without authentication."""
        response = api_client.get('/api/tournaments/v1/organizer/scheduling/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_list_matches_non_organizer(
        self,
        mock_service_class,
        api_client,
        regular_user
    ):
        """Test listing matches as non-organizer user."""
        api_client.force_authenticate(user=regular_user)
        
        response = api_client.get('/api/tournaments/v1/organizer/scheduling/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'Must be tournament organizer' in str(response.data)
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_list_matches_invalid_params(
        self,
        mock_service_class,
        api_client,
        organizer_user
    ):
        """Test listing matches with invalid query parameters."""
        api_client.force_authenticate(user=organizer_user)
        
        response = api_client.get(
            '/api/tournaments/v1/organizer/scheduling/',
            {'tournament_id': 'invalid'}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestOrganizerSchedulingAssignView:
    """Tests for POST /api/tournaments/v1/organizer/scheduling/."""
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_assign_match_success(
        self,
        mock_service_class,
        api_client,
        organizer_user,
        sample_matches
    ):
        """Test successful manual match assignment."""
        scheduled_time = datetime(2025, 12, 15, 14, 0, 0, tzinfo=timezone.utc)
        
        # Mock service response
        mock_service = Mock()
        mock_service.schedule_match_manually.return_value = {
            'match': sample_matches[0],
            'conflicts': [],
            'was_rescheduled': False
        }
        mock_service_class.return_value = mock_service
        
        api_client.force_authenticate(user=organizer_user)
        
        # Make request
        response = api_client.post(
            '/api/tournaments/v1/organizer/scheduling/',
            {
                'match_id': 101,
                'scheduled_time': scheduled_time.isoformat(),
                'skip_conflict_check': False
            },
            format='json'
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert 'match' in response.data
        assert 'conflicts' in response.data
        assert 'was_rescheduled' in response.data
        assert response.data['was_rescheduled'] is False
        
        # Verify service called
        mock_service.schedule_match_manually.assert_called_once_with(
            match_id=101,
            scheduled_time=scheduled_time,
            assigned_by_user_id=organizer_user.id,
            skip_conflict_check=False
        )
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_assign_match_with_conflicts(
        self,
        mock_service_class,
        api_client,
        organizer_user,
        sample_matches
    ):
        """Test match assignment with conflicts (soft validation)."""
        scheduled_time = datetime(2025, 12, 15, 14, 0, 0, tzinfo=timezone.utc)
        
        conflict = SchedulingConflictDTO(
            conflict_type='team_conflict',
            severity='warning',
            message='Team has overlapping match',
            affected_match_ids=[101, 102],
            suggested_resolution='Reschedule to avoid overlap'
        )
        
        mock_service = Mock()
        mock_service.schedule_match_manually.return_value = {
            'match': sample_matches[0],
            'conflicts': [conflict],
            'was_rescheduled': False
        }
        mock_service_class.return_value = mock_service
        
        api_client.force_authenticate(user=organizer_user)
        
        response = api_client.post(
            '/api/tournaments/v1/organizer/scheduling/',
            {
                'match_id': 101,
                'scheduled_time': scheduled_time.isoformat()
            },
            format='json'
        )
        
        # Verify assignment succeeded despite conflicts
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['conflicts']) == 1
        assert response.data['conflicts'][0]['severity'] == 'warning'
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_assign_match_not_found(
        self,
        mock_service_class,
        api_client,
        organizer_user
    ):
        """Test assigning non-existent match."""
        mock_service = Mock()
        mock_service.schedule_match_manually.side_effect = ValueError("Match 999 not found")
        mock_service_class.return_value = mock_service
        
        api_client.force_authenticate(user=organizer_user)
        
        response = api_client.post(
            '/api/tournaments/v1/organizer/scheduling/',
            {
                'match_id': 999,
                'scheduled_time': datetime.now(timezone.utc).isoformat()
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_assign_match_invalid_data(self, api_client, organizer_user):
        """Test assigning match with invalid request data."""
        api_client.force_authenticate(user=organizer_user)
        
        # Missing required fields
        response = api_client.post(
            '/api/tournaments/v1/organizer/scheduling/',
            {'match_id': 101},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestOrganizerBulkShiftView:
    """Tests for POST /api/tournaments/v1/organizer/scheduling/bulk-shift/."""
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_bulk_shift_success(
        self,
        mock_service_class,
        api_client,
        organizer_user
    ):
        """Test successful bulk shift operation."""
        result = BulkShiftResultDTO(
            shifted_count=5,
            failed_count=0,
            conflicts_detected=[],
            failed_match_ids=[],
            error_messages={}
        )
        
        mock_service = Mock()
        mock_service.bulk_shift_matches.return_value = result
        mock_service_class.return_value = mock_service
        
        api_client.force_authenticate(user=organizer_user)
        
        response = api_client.post(
            '/api/tournaments/v1/organizer/scheduling/bulk-shift/',
            {
                'stage_id': 10,
                'delta_minutes': 30
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['shifted_count'] == 5
        assert response.data['failed_count'] == 0
        
        # Verify service called
        mock_service.bulk_shift_matches.assert_called_once_with(
            stage_id=10,
            delta_minutes=30,
            assigned_by_user_id=organizer_user.id
        )
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_bulk_shift_with_conflicts(
        self,
        mock_service_class,
        api_client,
        organizer_user
    ):
        """Test bulk shift detecting conflicts."""
        conflict = SchedulingConflictDTO(
            conflict_type='team_conflict',
            severity='warning',
            message='Team has overlapping matches',
            affected_match_ids=[101, 102],
            suggested_resolution='Manual review required'
        )
        
        result = BulkShiftResultDTO(
            shifted_count=5,
            failed_count=0,
            conflicts_detected=[conflict],
            failed_match_ids=[],
            error_messages={}
        )
        
        mock_service = Mock()
        mock_service.bulk_shift_matches.return_value = result
        mock_service_class.return_value = mock_service
        
        api_client.force_authenticate(user=organizer_user)
        
        response = api_client.post(
            '/api/tournaments/v1/organizer/scheduling/bulk-shift/',
            {
                'stage_id': 10,
                'delta_minutes': -60
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['conflicts_detected']) == 1
    
    def test_bulk_shift_invalid_delta(self, api_client, organizer_user):
        """Test bulk shift with invalid delta_minutes."""
        api_client.force_authenticate(user=organizer_user)
        
        # Delta too large (> 1 week)
        response = api_client.post(
            '/api/tournaments/v1/organizer/scheduling/bulk-shift/',
            {
                'stage_id': 10,
                'delta_minutes': 20000  # > 10080
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestOrganizerSchedulingSlotsView:
    """Tests for GET /api/tournaments/v1/organizer/scheduling/slots/."""
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_generate_slots_success(
        self,
        mock_service_class,
        api_client,
        organizer_user,
        sample_slots
    ):
        """Test successful slot generation."""
        mock_service = Mock()
        mock_service.generate_scheduling_slots.return_value = sample_slots
        mock_service_class.return_value = mock_service
        
        api_client.force_authenticate(user=organizer_user)
        
        response = api_client.get(
            '/api/tournaments/v1/organizer/scheduling/slots/',
            {
                'stage_id': 10,
                'slot_duration_minutes': 60,
                'interval_minutes': 15
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'slots' in response.data
        assert response.data['count'] == 2
        assert len(response.data['slots']) == 2
        
        # Verify service called
        mock_service.generate_scheduling_slots.assert_called_once_with(
            stage_id=10,
            slot_duration_minutes=60,
            interval_minutes=15
        )
    
    @patch('apps.api.views.organizer_scheduling_views.TournamentOpsService')
    def test_generate_slots_default_duration(
        self,
        mock_service_class,
        api_client,
        organizer_user,
        sample_slots
    ):
        """Test slot generation with default duration."""
        mock_service = Mock()
        mock_service.generate_scheduling_slots.return_value = sample_slots
        mock_service_class.return_value = mock_service
        
        api_client.force_authenticate(user=organizer_user)
        
        response = api_client.get(
            '/api/tournaments/v1/organizer/scheduling/slots/',
            {'stage_id': 10}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify called with None for slot_duration_minutes (uses game default)
        call_args = mock_service.generate_scheduling_slots.call_args
        assert call_args.kwargs['slot_duration_minutes'] is None
        assert call_args.kwargs['interval_minutes'] == 15
    
    def test_generate_slots_missing_stage_id(self, api_client, organizer_user):
        """Test slot generation without required stage_id."""
        api_client.force_authenticate(user=organizer_user)
        
        response = api_client.get('/api/tournaments/v1/organizer/scheduling/slots/')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'stage_id is required' in str(response.data)
    
    def test_generate_slots_invalid_params(self, api_client, organizer_user):
        """Test slot generation with invalid parameters."""
        api_client.force_authenticate(user=organizer_user)
        
        response = api_client.get(
            '/api/tournaments/v1/organizer/scheduling/slots/',
            {
                'stage_id': 'invalid',
                'slot_duration_minutes': 'abc'
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
