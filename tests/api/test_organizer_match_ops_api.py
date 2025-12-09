"""
Tests for Match Operations API - Phase 7, Epic 7.4

Reference: Phase 7, Epic 7.4 - Match Operations Command Center
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.tournaments.models import Tournament, Stage, Match
from apps.tournaments.models.staffing import StaffRole, TournamentStaffAssignment

User = get_user_model()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(username='testuser', password='testpass')


@pytest.fixture
def admin_user(db):
    """Create admin user."""
    return User.objects.create_user(username='admin', password='testpass', is_staff=True)


@pytest.fixture
def tournament(db):
    """Create test tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        max_participants=16,
        status='OPEN'
    )


@pytest.fixture
def stage(tournament):
    """Create test stage."""
    return Stage.objects.create(
        tournament=tournament,
        name='Test Stage',
        stage_type='SINGLE_ELIMINATION',
        bracket_size=8
    )


@pytest.fixture
def match(stage):
    """Create test match."""
    return Match.objects.create(
        stage=stage,
        round_number=1,
        match_number=1,
        status='PENDING'
    )


@pytest.fixture
def staff_role(db):
    """Create admin staff role."""
    return StaffRole.objects.create(
        name='ADMIN',
        can_modify_matches=True,
        can_add_notes=True,
        can_assign_referees=True
    )


@pytest.fixture
def staff_assignment(tournament, admin_user, staff_role):
    """Assign admin user as tournament staff."""
    return TournamentStaffAssignment.objects.create(
        tournament=tournament,
        user_id=admin_user.id,
        role=staff_role
    )


@pytest.fixture
def api_client():
    """API client."""
    return APIClient()


class TestMarkMatchLive:
    """Tests for POST /api/match-ops/mark-live/."""
    
    def test_mark_match_live_success(self, api_client, admin_user, match, tournament, staff_assignment):
        """Test mark match live."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.post('/api/match-ops/mark-live/', {
            'match_id': match.id,
            'tournament_id': tournament.id
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['new_state'] == 'LIVE'
        
        # Verify match state
        match.refresh_from_db()
        assert match.status == 'LIVE'
    
    def test_mark_match_live_unauthenticated(self, api_client, match, tournament):
        """Test unauthenticated request."""
        response = api_client.post('/api/match-ops/mark-live/', {
            'match_id': match.id,
            'tournament_id': tournament.id
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_mark_match_live_no_permission(self, api_client, user, match, tournament):
        """Test user without permission."""
        api_client.force_authenticate(user=user)
        
        response = api_client.post('/api/match-ops/mark-live/', {
            'match_id': match.id,
            'tournament_id': tournament.id
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPauseMatch:
    """Tests for POST /api/match-ops/pause/."""
    
    def test_pause_match_with_reason(self, api_client, admin_user, match, tournament, staff_assignment):
        """Test pause match with reason."""
        # Set match to LIVE first
        match.status = 'LIVE'
        match.save()
        
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.post('/api/match-ops/pause/', {
            'match_id': match.id,
            'tournament_id': tournament.id,
            'reason': 'Technical issue'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['new_state'] == 'PAUSED'
        
        match.refresh_from_db()
        assert match.status == 'PAUSED'


class TestResumeMatch:
    """Tests for POST /api/match-ops/resume/."""
    
    def test_resume_match(self, api_client, admin_user, match, tournament, staff_assignment):
        """Test resume match."""
        # Set match to PAUSED
        match.status = 'PAUSED'
        match.save()
        
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.post('/api/match-ops/resume/', {
            'match_id': match.id,
            'tournament_id': tournament.id
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['new_state'] == 'LIVE'


class TestForceCompleteMatch:
    """Tests for POST /api/match-ops/force-complete/."""
    
    def test_force_complete_match(self, api_client, admin_user, match, tournament, staff_assignment):
        """Test force complete match."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.post('/api/match-ops/force-complete/', {
            'match_id': match.id,
            'tournament_id': tournament.id,
            'reason': 'No show',
            'result_data': {'winner': 'team1', 'reason': 'forfeit'}
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['new_state'] == 'COMPLETED'
        
        match.refresh_from_db()
        assert match.status == 'COMPLETED'
    
    def test_force_complete_missing_reason(self, api_client, admin_user, match, tournament, staff_assignment):
        """Test missing reason."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.post('/api/match-ops/force-complete/', {
            'match_id': match.id,
            'tournament_id': tournament.id
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAddMatchNote:
    """Tests for POST /api/match-ops/add-note/."""
    
    def test_add_match_note(self, api_client, admin_user, match, tournament, staff_assignment):
        """Test add moderator note."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.post('/api/match-ops/add-note/', {
            'match_id': match.id,
            'tournament_id': tournament.id,
            'content': 'Test moderator note'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['note_id'] > 0
        assert response.data['content'] == 'Test moderator note'


class TestGetMatchTimeline:
    """Tests for GET /api/match-ops/timeline/<match_id>/."""
    
    def test_get_match_timeline(self, api_client, admin_user, match, tournament, staff_assignment):
        """Test get match timeline."""
        # Create some operations first
        api_client.force_authenticate(user=admin_user)
        api_client.post('/api/match-ops/mark-live/', {
            'match_id': match.id,
            'tournament_id': tournament.id
        })
        
        # Get timeline
        response = api_client.get(f'/api/match-ops/timeline/{match.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) > 0
        assert response.data[0]['event_type'] == 'OPERATION'


class TestOverrideMatchResult:
    """Tests for POST /api/match-ops/override-result/."""
    
    def test_override_match_result(self, api_client, admin_user, match, tournament, staff_assignment):
        """Test override match result."""
        # Set initial result
        match.result_data = {'winner': 'team1'}
        match.save()
        
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.post('/api/match-ops/override-result/', {
            'match_id': match.id,
            'tournament_id': tournament.id,
            'new_result_data': {'winner': 'team2', 'reason': 'correction'},
            'reason': 'Admin correction due to scoring error'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        
        match.refresh_from_db()
        assert match.result_data['winner'] == 'team2'


class TestViewOperationsDashboard:
    """Tests for GET /api/match-ops/dashboard/<tournament_id>/."""
    
    def test_view_operations_dashboard(self, api_client, admin_user, match, tournament, staff_assignment):
        """Test view operations dashboard."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get(f'/api/match-ops/dashboard/{tournament.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) > 0
        assert response.data[0]['match_id'] == match.id
        assert response.data[0]['status'] == 'PENDING'
    
    def test_view_operations_dashboard_with_filter(self, api_client, admin_user, match, tournament, staff_assignment):
        """Test dashboard with status filter."""
        match.status = 'LIVE'
        match.save()
        
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get(f'/api/match-ops/dashboard/{tournament.id}/', {'status_filter': 'LIVE'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) > 0
        assert all(item['status'] == 'LIVE' for item in response.data)
