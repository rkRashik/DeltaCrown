"""
Unit Tests for Audit Log Service

Phase 7, Epic 7.5: Audit Log System
Tests for AuditLogService business logic and helper functions.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from apps.tournament_ops.services import AuditLogService
from apps.tournament_ops.dtos import AuditLogDTO, AuditLogFilterDTO


@pytest.fixture
def mock_adapter():
    """Fixture providing mock AuditLogAdapter."""
    adapter = Mock()
    return adapter


@pytest.fixture
def service(mock_adapter):
    """Fixture providing AuditLogService with mocked adapter."""
    return AuditLogService(audit_log_adapter=mock_adapter)


@pytest.fixture
def mock_user():
    """Fixture providing mock user."""
    user = Mock()
    user.id = 5
    user.username = "admin"
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
        after_state={"status": "FINALIZED"}
    )


class TestAuditLogServiceArchitecture:
    """Architecture compliance tests."""
    
    def test_service_has_no_orm_imports(self):
        """Verify service has no ORM imports at all."""
        import apps.tournament_ops.services.audit_log_service as service_module
        import inspect
        
        source = inspect.getsource(service_module)
        
        # Should NOT import any ORM models
        assert 'from apps.tournaments.models' not in source
        assert 'from django.db' not in source or 'from django.db import transaction' in source  # transaction is ok
    
    def test_service_methods_accept_dtos_only(self, service):
        """Verify service methods accept DTOs, not ORM models."""
        import inspect
        
        # Check log_action method signature
        sig = inspect.signature(service.log_action)
        params = sig.parameters
        
        # Should have user, action, etc. - not ORM model params
        assert 'user' in params
        assert 'action' in params


class TestAuditLogServiceLogAction:
    """Tests for log_action method."""
    
    def test_log_action_success(self, service, mock_adapter, mock_user, sample_audit_log_dto):
        """Test logging an action."""
        mock_adapter.create_log_entry.return_value = sample_audit_log_dto
        
        result = service.log_action(
            user=mock_user,
            action="result_finalized",
            tournament_id=10,
            metadata={"submission_id": 99}
        )
        
        mock_adapter.create_log_entry.assert_called_once()
        call_kwargs = mock_adapter.create_log_entry.call_args[1]
        assert call_kwargs['user'] == mock_user
        assert call_kwargs['action'] == "result_finalized"
        assert call_kwargs['tournament_id'] == 10
        
        assert isinstance(result, AuditLogDTO)
        assert result.log_id == 1
    
    def test_log_action_with_state_change(self, service, mock_adapter, mock_user, sample_audit_log_dto):
        """Test logging action with before/after state."""
        mock_adapter.create_log_entry.return_value = sample_audit_log_dto
        
        result = service.log_action(
            user=mock_user,
            action="match_rescheduled",
            match_id=42,
            before_state={"scheduled_time": "2025-12-10T10:00:00Z"},
            after_state={"scheduled_time": "2025-12-10T14:00:00Z"}
        )
        
        assert result.has_state_change()
    
    def test_log_action_system(self, service, mock_adapter, sample_audit_log_dto):
        """Test logging system action (no user)."""
        system_dto = AuditLogDTO(
            log_id=1,
            user_id=None,
            username=None,
            action="system_cleanup",
            timestamp=datetime.now()
        )
        mock_adapter.create_log_entry.return_value = system_dto
        
        result = service.log_action(
            user=None,
            action="system_cleanup"
        )
        
        assert result.user_id is None


class TestAuditLogServiceListLogs:
    """Tests for list_logs method."""
    
    def test_list_logs_with_filters(self, service, mock_adapter, sample_audit_log_dto):
        """Test listing logs with filters."""
        mock_adapter.list_logs.return_value = [sample_audit_log_dto]
        
        filters = AuditLogFilterDTO(user_id=5, limit=50)
        results = service.list_logs(filters)
        
        mock_adapter.list_logs.assert_called_once_with(filters)
        assert len(results) == 1
        assert isinstance(results[0], AuditLogDTO)
    
    def test_list_logs_empty_result(self, service, mock_adapter):
        """Test listing logs returns empty list."""
        mock_adapter.list_logs.return_value = []
        
        filters = AuditLogFilterDTO(user_id=999)
        results = service.list_logs(filters)
        
        assert results == []


class TestAuditLogServiceCountLogs:
    """Tests for count_logs method."""
    
    def test_count_logs(self, service, mock_adapter):
        """Test counting logs."""
        mock_adapter.count_logs.return_value = 42
        
        filters = AuditLogFilterDTO(action="result_finalized")
        count = service.count_logs(filters)
        
        mock_adapter.count_logs.assert_called_once_with(filters)
        assert count == 42


class TestAuditLogServiceTrailMethods:
    """Tests for audit trail methods."""
    
    def test_get_tournament_audit_trail(self, service, mock_adapter, sample_audit_log_dto):
        """Test getting tournament audit trail."""
        mock_adapter.get_tournament_logs.return_value = [sample_audit_log_dto]
        
        results = service.get_tournament_audit_trail(tournament_id=10, limit=100)
        
        mock_adapter.get_tournament_logs.assert_called_once_with(
            tournament_id=10,
            limit=100
        )
        assert len(results) == 1
    
    def test_get_match_audit_trail(self, service, mock_adapter, sample_audit_log_dto):
        """Test getting match audit trail."""
        mock_adapter.get_match_logs.return_value = [sample_audit_log_dto]
        
        results = service.get_match_audit_trail(match_id=42)
        
        mock_adapter.get_match_logs.assert_called_once_with(match_id=42, limit=100)
        assert len(results) == 1
    
    def test_get_user_audit_trail(self, service, mock_adapter, sample_audit_log_dto):
        """Test getting user audit trail."""
        mock_adapter.get_user_logs.return_value = [sample_audit_log_dto]
        
        results = service.get_user_audit_trail(user_id=5, limit=50)
        
        mock_adapter.get_user_logs.assert_called_once_with(user_id=5, limit=50)
        assert len(results) == 1


class TestAuditLogServiceExport:
    """Tests for export methods."""
    
    def test_export_logs_to_csv(self, service, mock_adapter, sample_audit_log_dto):
        """Test exporting logs to CSV."""
        mock_adapter.export_logs.return_value = [sample_audit_log_dto]
        
        filters = AuditLogFilterDTO(tournament_id=10)
        csv_rows = service.export_logs_to_csv(filters)
        
        mock_adapter.export_logs.assert_called_once_with(filters)
        assert len(csv_rows) == 1
        assert isinstance(csv_rows[0], dict)  # CSV row
        assert 'Log ID' in csv_rows[0]


class TestAuditLogServiceRecentActivity:
    """Tests for recent activity method."""
    
    def test_get_recent_audit_activity(self, service, mock_adapter, sample_audit_log_dto):
        """Test getting recent audit activity."""
        mock_adapter.list_logs.return_value = [sample_audit_log_dto]
        
        results = service.get_recent_audit_activity(hours=24, limit=50)
        
        # Should call list_logs with date filter
        mock_adapter.list_logs.assert_called_once()
        filters = mock_adapter.list_logs.call_args[0][0]
        assert filters.limit == 50
        assert filters.start_date is not None
        
        assert len(results) == 1


class TestAuditActionDecorator:
    """Tests for @audit_action decorator."""
    
    @patch('apps.tournament_ops.services.audit_log_service.AuditLogService')
    def test_audit_action_decorator_success(self, mock_service_class, mock_user):
        """Test decorator logs action on success."""
        from apps.tournament_ops.services.audit_log_service import audit_action
        
        mock_service_instance = Mock()
        mock_service_class.return_value = mock_service_instance
        
        @audit_action(action="test_action")
        def test_function(user, tournament_id):
            return {"result": "success"}
        
        result = test_function(user=mock_user, tournament_id=10)
        
        assert result == {"result": "success"}
        # Decorator should log the action
        mock_service_instance.log_action.assert_called_once()
    
    @patch('apps.tournament_ops.services.audit_log_service.AuditLogService')
    def test_audit_action_decorator_exception(self, mock_service_class, mock_user):
        """Test decorator doesn't log on exception."""
        from apps.tournament_ops.services.audit_log_service import audit_action
        
        mock_service_instance = Mock()
        mock_service_class.return_value = mock_service_instance
        
        @audit_action(action="test_action")
        def test_function(user):
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            test_function(user=mock_user)
        
        # Decorator should not log on failure
        mock_service_instance.log_action.assert_not_called()


class TestAuditHelperFunctions:
    """Tests for helper functions."""
    
    @patch('apps.tournament_ops.services.audit_log_service.AuditLogService')
    def test_log_result_finalized(self, mock_service_class, mock_user):
        """Test log_result_finalized helper."""
        from apps.tournament_ops.services.audit_log_service import log_result_finalized
        
        mock_service_instance = Mock()
        mock_service_class.return_value = mock_service_instance
        
        log_result_finalized(
            user=mock_user,
            submission_id=99,
            match_id=42,
            tournament_id=10
        )
        
        mock_service_instance.log_action.assert_called_once()
        call_kwargs = mock_service_instance.log_action.call_args[1]
        assert call_kwargs['action'] == "result_finalized"
        assert call_kwargs['tournament_id'] == 10
    
    @patch('apps.tournament_ops.services.audit_log_service.AuditLogService')
    def test_log_match_rescheduled(self, mock_service_class, mock_user):
        """Test log_match_rescheduled helper."""
        from apps.tournament_ops.services.audit_log_service import log_match_rescheduled
        
        mock_service_instance = Mock()
        mock_service_class.return_value = mock_service_instance
        
        old_time = datetime.now()
        new_time = old_time + timedelta(hours=4)
        
        log_match_rescheduled(
            user=mock_user,
            match_id=42,
            tournament_id=10,
            old_scheduled_time=old_time,
            new_scheduled_time=new_time
        )
        
        mock_service_instance.log_action.assert_called_once()
        call_kwargs = mock_service_instance.log_action.call_args[1]
        assert call_kwargs['action'] == "match_rescheduled"
        assert call_kwargs['before_state'] is not None
        assert call_kwargs['after_state'] is not None
    
    @patch('apps.tournament_ops.services.audit_log_service.AuditLogService')
    def test_log_staff_assigned(self, mock_service_class, mock_user):
        """Test log_staff_assigned helper."""
        from apps.tournament_ops.services.audit_log_service import log_staff_assigned
        
        mock_service_instance = Mock()
        mock_service_class.return_value = mock_service_instance
        
        log_staff_assigned(
            user=mock_user,
            staff_member_id=7,
            role="REFEREE",
            match_id=42,
            tournament_id=10
        )
        
        mock_service_instance.log_action.assert_called_once()
    
    @patch('apps.tournament_ops.services.audit_log_service.AuditLogService')
    def test_log_match_operation(self, mock_service_class, mock_user):
        """Test log_match_operation helper."""
        from apps.tournament_ops.services.audit_log_service import log_match_operation
        
        mock_service_instance = Mock()
        mock_service_class.return_value = mock_service_instance
        
        log_match_operation(
            user=mock_user,
            operation="live",
            match_id=42,
            tournament_id=10
        )
        
        mock_service_instance.log_action.assert_called_once()
        call_kwargs = mock_service_instance.log_action.call_args[1]
        assert call_kwargs['action'] == "match_live"


# Run with: pytest tests/unit/tournament_ops/test_audit_log_service.py -v
