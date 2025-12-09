"""
Organizer Staffing API Tests - Phase 7, Epic 7.3

Tests for organizer staffing management API endpoints.

Reference: Phase 7, Epic 7.3 - Staff & Referee Role System
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, Mock
from datetime import datetime

from apps.tournament_ops.dtos.staffing import (
    StaffRoleDTO,
    TournamentStaffAssignmentDTO,
    MatchRefereeAssignmentDTO,
    StaffLoadDTO,
)


@pytest.mark.django_db
class TestOrganizerStaffingAPI:
    """Test suite for organizer staffing API endpoints."""
    
    @pytest.fixture
    def api_client(self):
        """Create API client."""
        return APIClient()
    
    @pytest.fixture
    def auth_user(self, django_user_model):
        """Create authenticated user."""
        return django_user_model.objects.create_user(
            username="organizer",
            password="testpass123"
        )
    
    @pytest.fixture
    def auth_client(self, api_client, auth_user):
        """Create authenticated API client."""
        api_client.force_authenticate(user=auth_user)
        return api_client
    
    @pytest.fixture
    def sample_role_dto(self):
        """Sample StaffRoleDTO."""
        return StaffRoleDTO(
            role_id=1,
            name="Head Admin",
            code="HEAD_ADMIN",
            description="Main admin",
            capabilities={"can_schedule": True},
            is_referee_role=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    @pytest.fixture
    def sample_staff_assignment_dto(self, sample_role_dto):
        """Sample TournamentStaffAssignmentDTO."""
        return TournamentStaffAssignmentDTO(
            assignment_id=1,
            tournament_id=100,
            tournament_name="Test Tournament",
            user_id=50,
            username="staff_user",
            user_email="staff@test.com",
            role=sample_role_dto,
            is_active=True,
            stage_id=None,
            stage_name=None,
            assigned_by_user_id=1,
            assigned_by_username="organizer",
            assigned_at=datetime.now(),
            notes=""
        )
    
    # ========================================================================
    # Staff Roles Endpoint Tests
    # ========================================================================
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_get_staff_roles_success(self, mock_ops, auth_client, sample_role_dto):
        """Test GET /api/staffing/roles/ returns staff roles."""
        mock_ops.get_staff_roles.return_value = [sample_role_dto]
        
        response = auth_client.get('/api/staffing/roles/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['code'] == 'HEAD_ADMIN'
    
    def test_get_staff_roles_requires_auth(self, api_client):
        """Test GET /api/staffing/roles/ requires authentication."""
        response = api_client.get('/api/staffing/roles/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # ========================================================================
    # Tournament Staff Management Tests
    # ========================================================================
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_get_tournament_staff_success(
        self,
        mock_ops,
        auth_client,
        sample_staff_assignment_dto
    ):
        """Test GET /api/staffing/tournaments/staff/ returns staff."""
        mock_ops.get_tournament_staff.return_value = [sample_staff_assignment_dto]
        
        response = auth_client.get('/api/staffing/tournaments/staff/', {
            'tournament_id': 100
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['tournament_id'] == 100
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_get_tournament_staff_missing_tournament_id(self, mock_ops, auth_client):
        """Test GET /api/staffing/tournaments/staff/ requires tournament_id."""
        response = auth_client.get('/api/staffing/tournaments/staff/')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'tournament_id is required' in str(response.data)
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_assign_staff_success(
        self,
        mock_ops,
        auth_client,
        auth_user,
        sample_staff_assignment_dto
    ):
        """Test POST /api/staffing/tournaments/<id>/staff/assign/ creates assignment."""
        mock_ops.assign_tournament_staff.return_value = sample_staff_assignment_dto
        
        response = auth_client.post('/api/staffing/tournaments/100/staff/assign/', {
            'user_id': 50,
            'role_code': 'HEAD_ADMIN',
            'notes': 'Test assignment'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['assignment_id'] == 1
        assert response.data['role']['code'] == 'HEAD_ADMIN'
        
        # Verify service was called
        mock_ops.assign_tournament_staff.assert_called_once()
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_assign_staff_validation_error(self, mock_ops, auth_client):
        """Test POST /api/staffing/tournaments/<id>/staff/assign/ validates input."""
        response = auth_client.post('/api/staffing/tournaments/100/staff/assign/', {
            # Missing required fields
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_remove_staff_success(
        self,
        mock_ops,
        auth_client,
        sample_staff_assignment_dto
    ):
        """Test DELETE /api/staffing/staff/assignments/<id>/ removes staff."""
        sample_staff_assignment_dto.is_active = False
        mock_ops.remove_tournament_staff.return_value = sample_staff_assignment_dto
        
        response = auth_client.delete('/api/staffing/staff/assignments/1/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['assignment']['is_active'] is False
        assert 'removed' in response.data['message'].lower()
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_remove_staff_not_found(self, mock_ops, auth_client):
        """Test DELETE /api/staffing/staff/assignments/<id>/ handles not found."""
        mock_ops.remove_tournament_staff.side_effect = ValueError("Assignment not found")
        
        response = auth_client.delete('/api/staffing/staff/assignments/999/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    # ========================================================================
    # Match Referee Management Tests
    # ========================================================================
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_get_match_referees_success(self, mock_ops, auth_client):
        """Test GET /api/staffing/matches/<id>/referees/ returns referees."""
        ref_dto = Mock(
            assignment_id=10,
            match_id=200,
            tournament_id=100,
            stage_id=5,
            round_number=1,
            match_number=1,
            staff_assignment=Mock(
                assignment_id=1,
                user_id=50,
                username="referee_user"
            ),
            is_primary=True,
            assigned_by_user_id=1,
            assigned_by_username="organizer",
            assigned_at=datetime.now(),
            notes=""
        )
        
        mock_ops.get_match_referees.return_value = [ref_dto]
        
        response = auth_client.get('/api/staffing/matches/200/referees/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['match_id'] == 200
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_assign_referee_success(self, mock_ops, auth_client, auth_user):
        """Test POST /api/staffing/matches/<id>/referees/assign/ creates assignment."""
        ref_dto = Mock(
            assignment_id=10,
            match_id=200,
            tournament_id=100,
            stage_id=5,
            round_number=1,
            match_number=1,
            staff_assignment=Mock(assignment_id=2),
            is_primary=True,
            assigned_by_user_id=auth_user.id,
            assigned_by_username="organizer",
            assigned_at=datetime.now(),
            notes=""
        )
        
        mock_ops.assign_match_referee.return_value = (ref_dto, None)  # No warning
        
        response = auth_client.post('/api/staffing/matches/200/referees/assign/', {
            'staff_assignment_id': 2,
            'is_primary': True
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['assignment']['match_id'] == 200
        assert response.data['warning'] is None
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_assign_referee_with_warning(self, mock_ops, auth_client, auth_user):
        """Test POST /api/staffing/matches/<id>/referees/assign/ returns warning."""
        ref_dto = Mock(
            assignment_id=10,
            match_id=200,
            tournament_id=100,
            stage_id=5,
            round_number=1,
            match_number=1,
            staff_assignment=Mock(assignment_id=2),
            is_primary=True,
            assigned_by_user_id=auth_user.id,
            assigned_by_username="organizer",
            assigned_at=datetime.now(),
            notes=""
        )
        
        warning = "Warning: Referee is overloaded"
        mock_ops.assign_match_referee.return_value = (ref_dto, warning)
        
        response = auth_client.post('/api/staffing/matches/200/referees/assign/', {
            'staff_assignment_id': 2,
            'is_primary': True
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['warning'] == warning
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_unassign_referee_success(self, mock_ops, auth_client):
        """Test DELETE /api/staffing/referees/assignments/<id>/ removes referee."""
        mock_ops.unassign_match_referee.return_value = None
        
        response = auth_client.delete('/api/staffing/referees/assignments/10/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_unassign_referee_not_found(self, mock_ops, auth_client):
        """Test DELETE /api/staffing/referees/assignments/<id>/ handles not found."""
        mock_ops.unassign_match_referee.side_effect = ValueError("Not found")
        
        response = auth_client.delete('/api/staffing/referees/assignments/999/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    # ========================================================================
    # Staff Load Endpoint Tests
    # ========================================================================
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_get_staff_load_success(
        self,
        mock_ops,
        auth_client,
        sample_staff_assignment_dto
    ):
        """Test GET /api/staffing/tournaments/staff/load/ returns load data."""
        load_dto = StaffLoadDTO(
            staff_assignment=sample_staff_assignment_dto,
            total_matches_assigned=8,
            upcoming_matches=5,
            completed_matches=3,
            concurrent_matches=0,
            is_overloaded=False,
            load_percentage=80.0
        )
        
        mock_ops.calculate_staff_load.return_value = [load_dto]
        
        response = auth_client.get('/api/staffing/tournaments/staff/load/', {
            'tournament_id': 100
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['total_matches_assigned'] == 8
        assert response.data[0]['load_percentage'] == 80.0
    
    @patch('apps.api.views.organizer_staffing_views.tournament_ops')
    def test_get_staff_load_missing_tournament_id(self, mock_ops, auth_client):
        """Test GET /api/staffing/tournaments/staff/load/ requires tournament_id."""
        response = auth_client.get('/api/staffing/tournaments/staff/load/')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'tournament_id is required' in str(response.data)
