"""
API Tests for Audit Log Endpoints

Phase 7, Epic 7.5: Audit Log System
Tests for organizer audit log API views.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework import status
from apps.api.views.organizer_audit_log_views import (
    AuditLogListView,
    TournamentAuditTrailView,
    MatchAuditTrailView,
    UserAuditTrailView,
    AuditLogExportView,
    RecentActivityView,
)
from apps.tournament_ops.dtos import AuditLogDTO

User = get_user_model()


@pytest.fixture
def factory():
    """Fixture providing request factory."""
    return RequestFactory()


@pytest.fixture
def mock_user():
    """Fixture providing mock authenticated user."""
    user = Mock(spec=User)
    user.id = 5
    user.username = "admin"
    user.is_authenticated = True
    user.is_staff = True
    return user


@pytest.fixture
def sample_audit_log_dto():
    """Fixture providing sample audit log DTO."""
    return AuditLogDTO(
        log_id=1,
        user_id=5,
        username="admin",
        action="result_finalized",
        timestamp=datetime.now(),
        tournament_id=10,
        match_id=42,
        before_state={"status": "PENDING"},
        after_state={"status": "FINALIZED"},
        metadata={"submission_id": 99}
    )


class TestAuditLogListView:
    """Tests for AuditLogListView."""
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_list_audit_logs_success(self, mock_get_service, factory, mock_user, sample_audit_log_dto):
        """Test listing audit logs with filters."""
        mock_service = Mock()
        mock_service.get_audit_logs.return_value = [sample_audit_log_dto]
        mock_service.count_audit_logs.return_value = 1
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/?user_id=5&limit=50')
        request.user = mock_user
        
        view = AuditLogListView.as_view()
        response = view(request)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'count' in response.data
        assert len(response.data['results']) == 1
        assert response.data['count'] == 1
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_list_audit_logs_with_action_filter(self, mock_get_service, factory, mock_user, sample_audit_log_dto):
        """Test listing logs filtered by action."""
        mock_service = Mock()
        mock_service.get_audit_logs.return_value = [sample_audit_log_dto]
        mock_service.count_audit_logs.return_value = 1
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/?action=result_finalized')
        request.user = mock_user
        
        view = AuditLogListView.as_view()
        response = view(request)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_list_audit_logs_with_date_range(self, mock_get_service, factory, mock_user, sample_audit_log_dto):
        """Test listing logs with date range."""
        mock_service = Mock()
        mock_service.get_audit_logs.return_value = [sample_audit_log_dto]
        mock_service.count_audit_logs.return_value = 1
        mock_get_service.return_value = mock_service
        
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        request = factory.get(f'/api/audit-logs/?start_date={start.isoformat()}&end_date={end.isoformat()}')
        request.user = mock_user
        
        view = AuditLogListView.as_view()
        response = view(request)
        
        assert response.status_code == status.HTTP_200_OK
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_list_audit_logs_pagination(self, mock_get_service, factory, mock_user, sample_audit_log_dto):
        """Test audit log pagination."""
        mock_service = Mock()
        mock_service.get_audit_logs.return_value = [sample_audit_log_dto] * 50
        mock_service.count_audit_logs.return_value = 150
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/?limit=50&offset=50')
        request.user = mock_user
        
        view = AuditLogListView.as_view()
        response = view(request)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 150
        assert len(response.data['results']) == 50
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_list_audit_logs_empty(self, mock_get_service, factory, mock_user):
        """Test listing logs returns empty result."""
        mock_service = Mock()
        mock_service.get_audit_logs.return_value = []
        mock_service.count_audit_logs.return_value = 0
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/')
        request.user = mock_user
        
        view = AuditLogListView.as_view()
        response = view(request)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0


class TestTournamentAuditTrailView:
    """Tests for TournamentAuditTrailView."""
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_get_tournament_audit_trail(self, mock_get_service, factory, mock_user, sample_audit_log_dto):
        """Test getting tournament audit trail."""
        mock_service = Mock()
        mock_service.get_tournament_audit_trail.return_value = [sample_audit_log_dto]
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/tournament/10/')
        request.user = mock_user
        
        view = TournamentAuditTrailView.as_view()
        response = view(request, tournament_id=10)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['tournament_id'] == 10
        
        mock_service.get_tournament_audit_trail.assert_called_once_with(
            tournament_id=10,
            limit=100
        )
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_get_tournament_audit_trail_with_limit(self, mock_get_service, factory, mock_user, sample_audit_log_dto):
        """Test tournament trail with custom limit."""
        mock_service = Mock()
        mock_service.get_tournament_audit_trail.return_value = [sample_audit_log_dto]
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/tournament/10/?limit=50')
        request.user = mock_user
        
        view = TournamentAuditTrailView.as_view()
        response = view(request, tournament_id=10)
        
        mock_service.get_tournament_audit_trail.assert_called_once_with(
            tournament_id=10,
            limit=50
        )


class TestMatchAuditTrailView:
    """Tests for MatchAuditTrailView."""
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_get_match_audit_trail(self, mock_get_service, factory, mock_user, sample_audit_log_dto):
        """Test getting match audit trail."""
        mock_service = Mock()
        mock_service.get_match_audit_trail.return_value = [sample_audit_log_dto]
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/match/42/')
        request.user = mock_user
        
        view = MatchAuditTrailView.as_view()
        response = view(request, match_id=42)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['match_id'] == 42


class TestUserAuditTrailView:
    """Tests for UserAuditTrailView."""
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_get_user_audit_trail(self, mock_get_service, factory, mock_user, sample_audit_log_dto):
        """Test getting user audit trail."""
        mock_service = Mock()
        mock_service.get_user_audit_trail.return_value = [sample_audit_log_dto]
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/user/5/')
        request.user = mock_user
        
        view = UserAuditTrailView.as_view()
        response = view(request, user_id=5)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['user_id'] == 5


class TestAuditLogExportView:
    """Tests for AuditLogExportView (CSV export)."""
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_export_audit_logs_csv(self, mock_get_service, factory, mock_user):
        """Test exporting audit logs as CSV."""
        mock_service = Mock()
        csv_row = {
            'Log ID': 1,
            'User': 'admin',
            'Action': 'result_finalized',
            'Timestamp': datetime.now().isoformat(),
            'Tournament ID': 10,
            'Match ID': 42
        }
        mock_service.export_audit_logs.return_value = [csv_row]
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/export/?tournament_id=10')
        request.user = mock_user
        
        view = AuditLogExportView.as_view()
        response = view(request)
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'text/csv'
        assert 'Content-Disposition' in response
        assert 'attachment' in response['Content-Disposition']
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_export_audit_logs_csv_content(self, mock_get_service, factory, mock_user):
        """Test CSV export contains correct headers and data."""
        mock_service = Mock()
        csv_row = {
            'Log ID': 1,
            'User': 'admin',
            'Action': 'result_finalized'
        }
        mock_service.export_audit_logs.return_value = [csv_row]
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/export/')
        request.user = mock_user
        
        view = AuditLogExportView.as_view()
        response = view(request)
        
        content = response.content.decode('utf-8')
        assert 'Log ID' in content
        assert 'User' in content
        assert 'Action' in content
        assert 'admin' in content


class TestRecentActivityView:
    """Tests for RecentActivityView."""
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_get_recent_activity_default(self, mock_get_service, factory, mock_user, sample_audit_log_dto):
        """Test getting recent activity (default 24 hours)."""
        mock_service = Mock()
        mock_service.get_recent_audit_activity.return_value = [sample_audit_log_dto]
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/activity/')
        request.user = mock_user
        
        view = RecentActivityView.as_view()
        response = view(request)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        
        mock_service.get_recent_audit_activity.assert_called_once_with(
            hours=24,
            limit=50
        )
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_get_recent_activity_custom_hours(self, mock_get_service, factory, mock_user, sample_audit_log_dto):
        """Test getting recent activity with custom hours."""
        mock_service = Mock()
        mock_service.get_recent_audit_activity.return_value = [sample_audit_log_dto]
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/activity/?hours=48&limit=100')
        request.user = mock_user
        
        view = RecentActivityView.as_view()
        response = view(request)
        
        mock_service.get_recent_audit_activity.assert_called_once_with(
            hours=48,
            limit=100
        )


class TestAuditLogAPIPermissions:
    """Tests for API permissions."""
    
    @patch('apps.api.views.organizer_audit_log_views.get_tournament_ops_service')
    def test_audit_log_requires_authentication(self, mock_get_service, factory):
        """Test that unauthenticated requests are rejected."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        
        request = factory.get('/api/audit-logs/')
        request.user = Mock(is_authenticated=False)
        
        view = AuditLogListView.as_view()
        response = view(request)
        
        # Should return 403 or redirect to login
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


class TestAuditLogAPIArchitecture:
    """Architecture compliance tests for API layer."""
    
    def test_views_use_facade_only(self):
        """Verify views use TournamentOpsService façade, not adapters/ORM."""
        import apps.api.views.organizer_audit_log_views as views_module
        import inspect
        
        source = inspect.getsource(views_module)
        
        # Should import get_tournament_ops_service (façade)
        assert 'get_tournament_ops_service' in source
        
        # Should NOT import adapters or ORM models
        assert 'AuditLogAdapter' not in source
        assert 'from apps.tournaments.models' not in source
    
    def test_views_return_serialized_dtos(self):
        """Verify views serialize DTOs, not ORM models."""
        import apps.api.views.organizer_audit_log_views as views_module
        import inspect
        
        source = inspect.getsource(views_module)
        
        # Should use serializers
        assert 'AuditLogSerializer' in source
        
        # Should serialize DTOs
        assert 'serializer.data' in source


# Run with: pytest tests/api/test_organizer_audit_log_api.py -v
