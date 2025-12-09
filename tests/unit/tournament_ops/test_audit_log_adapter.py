"""
Unit Tests for Audit Log Adapter

Phase 7, Epic 7.5: Audit Log System
Tests for AuditLogAdapter with method-level ORM import verification.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from apps.tournament_ops.adapters import AuditLogAdapter
from apps.tournament_ops.dtos import AuditLogDTO, AuditLogFilterDTO


@pytest.fixture
def adapter():
    """Fixture providing AuditLogAdapter instance."""
    return AuditLogAdapter()


@pytest.fixture
def mock_user():
    """Fixture providing mock user."""
    user = Mock()
    user.id = 5
    user.username = "admin"
    return user


@pytest.fixture
def mock_audit_log():
    """Fixture providing mock AuditLog model instance."""
    log = Mock()
    log.id = 1
    log.user_id = 5
    log.user = Mock(username="admin")
    log.action = "result_finalized"
    log.timestamp = datetime.now()
    log.metadata = {"submission_id": 99}
    log.ip_address = "192.168.1.1"
    log.user_agent = "Mozilla/5.0"
    log.tournament_id = 10
    log.match_id = 42
    log.before_state = {"status": "PENDING"}
    log.after_state = {"status": "FINALIZED"}
    log.correlation_id = "abc-123"
    return log


class TestAuditLogAdapterArchitecture:
    """Architecture compliance tests."""
    
    def test_adapter_has_no_module_level_orm_imports(self):
        """Verify AuditLog is imported at method level only."""
        import apps.tournament_ops.adapters.audit_log_adapter as adapter_module
        import inspect
        
        # Check module-level code doesn't import AuditLog at top
        source = inspect.getsource(adapter_module)
        lines = source.split('\n')
        
        # Find import section (before first class/function)
        import_section = []
        for line in lines:
            if line.strip().startswith('class ') or line.strip().startswith('def '):
                break
            import_section.append(line)
        
        import_text = '\n'.join(import_section)
        
        # Should NOT import AuditLog at module level
        assert 'from apps.tournaments.models' not in import_text
        assert 'from apps.tournaments.models.security import AuditLog' not in import_text
    
    def test_adapter_methods_return_dtos_only(self, adapter):
        """Verify all public methods return DTOs, not ORM models."""
        import inspect
        
        public_methods = [
            name for name, method in inspect.getmembers(adapter, predicate=inspect.ismethod)
            if not name.startswith('_')
        ]
        
        # Check method signatures
        for method_name in public_methods:
            method = getattr(adapter, method_name)
            signature = inspect.signature(method)
            return_annotation = signature.return_annotation
            
            # Should return DTO types or None/Optional
            if return_annotation != inspect.Signature.empty:
                assert 'DTO' in str(return_annotation) or 'None' in str(return_annotation) or 'list' in str(return_annotation).lower()


class TestAuditLogAdapterCreate:
    """Tests for create_log_entry method."""
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_create_log_entry_success(self, mock_audit_log_model, adapter, mock_user):
        """Test creating audit log entry."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.user = mock_user
        mock_instance.user_id = mock_user.id
        mock_instance.action = "result_finalized"
        mock_instance.timestamp = datetime.now()
        mock_instance.tournament_id = 10
        mock_audit_log_model.objects.create.return_value = mock_instance
        
        dto = adapter.create_log_entry(
            user=mock_user,
            action="result_finalized",
            tournament_id=10,
            metadata={"submission_id": 99}
        )
        
        # Verify ORM call
        mock_audit_log_model.objects.create.assert_called_once()
        call_kwargs = mock_audit_log_model.objects.create.call_args[1]
        assert call_kwargs['user'] == mock_user
        assert call_kwargs['action'] == "result_finalized"
        assert call_kwargs['tournament_id'] == 10
        
        # Verify DTO returned
        assert isinstance(dto, AuditLogDTO)
        assert dto.log_id == 1
        assert dto.user_id == mock_user.id
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_create_log_entry_system_action(self, mock_audit_log_model, adapter):
        """Test creating system audit log (no user)."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.user = None
        mock_instance.user_id = None
        mock_instance.action = "system_cleanup"
        mock_instance.timestamp = datetime.now()
        mock_audit_log_model.objects.create.return_value = mock_instance
        
        dto = adapter.create_log_entry(
            user=None,
            action="system_cleanup"
        )
        
        assert dto.user_id is None
        assert dto.username is None


class TestAuditLogAdapterQuery:
    """Tests for query methods."""
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_get_log_by_id_found(self, mock_audit_log_model, adapter, mock_audit_log):
        """Test retrieving audit log by ID."""
        mock_audit_log_model.objects.select_related.return_value.get.return_value = mock_audit_log
        
        dto = adapter.get_log_by_id(1)
        
        mock_audit_log_model.objects.select_related.assert_called_once_with('user')
        assert isinstance(dto, AuditLogDTO)
        assert dto.log_id == 1
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_get_log_by_id_not_found(self, mock_audit_log_model, adapter):
        """Test retrieving non-existent audit log."""
        from django.core.exceptions import ObjectDoesNotExist
        mock_audit_log_model.objects.select_related.return_value.get.side_effect = ObjectDoesNotExist
        
        dto = adapter.get_log_by_id(999)
        assert dto is None
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_list_logs_with_user_filter(self, mock_audit_log_model, adapter, mock_audit_log):
        """Test listing logs filtered by user."""
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.select_related.return_value = mock_queryset
        mock_queryset.order_by.return_value = [mock_audit_log]
        mock_audit_log_model.objects.all.return_value = mock_queryset
        
        filters = AuditLogFilterDTO(user_id=5)
        dtos = adapter.list_logs(filters)
        
        # Verify filter applied
        mock_queryset.filter.assert_called()
        filter_call = mock_queryset.filter.call_args
        assert 'user_id' in str(filter_call) or filter_call[1].get('user_id') == 5
        
        assert len(dtos) == 1
        assert isinstance(dtos[0], AuditLogDTO)
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_list_logs_with_tournament_filter(self, mock_audit_log_model, adapter, mock_audit_log):
        """Test listing logs filtered by tournament."""
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.select_related.return_value = mock_queryset
        mock_queryset.order_by.return_value = [mock_audit_log]
        mock_audit_log_model.objects.all.return_value = mock_queryset
        
        filters = AuditLogFilterDTO(tournament_id=10)
        dtos = adapter.list_logs(filters)
        
        assert len(dtos) == 1
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_list_logs_with_date_range(self, mock_audit_log_model, adapter, mock_audit_log):
        """Test listing logs filtered by date range."""
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.select_related.return_value = mock_queryset
        mock_queryset.order_by.return_value = [mock_audit_log]
        mock_audit_log_model.objects.all.return_value = mock_queryset
        
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        filters = AuditLogFilterDTO(start_date=start, end_date=end)
        
        dtos = adapter.list_logs(filters)
        assert len(dtos) == 1
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_count_logs(self, mock_audit_log_model, adapter):
        """Test counting logs with filters."""
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.count.return_value = 42
        mock_audit_log_model.objects.all.return_value = mock_queryset
        
        filters = AuditLogFilterDTO(action="result_finalized")
        count = adapter.count_logs(filters)
        
        assert count == 42


class TestAuditLogAdapterSpecificQueries:
    """Tests for specific query methods."""
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_get_user_logs(self, mock_audit_log_model, adapter, mock_audit_log):
        """Test getting logs for specific user."""
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.select_related.return_value = mock_queryset
        mock_queryset.order_by.return_value = [mock_audit_log]
        mock_audit_log_model.objects.filter.return_value = mock_queryset
        
        dtos = adapter.get_user_logs(user_id=5, limit=50)
        
        assert len(dtos) == 1
        mock_queryset.order_by.assert_called_with('-timestamp')
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_get_tournament_logs(self, mock_audit_log_model, adapter, mock_audit_log):
        """Test getting logs for specific tournament."""
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.select_related.return_value = mock_queryset
        mock_queryset.order_by.return_value = [mock_audit_log]
        mock_audit_log_model.objects.filter.return_value = mock_queryset
        
        dtos = adapter.get_tournament_logs(tournament_id=10)
        
        assert len(dtos) == 1
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_get_match_logs(self, mock_audit_log_model, adapter, mock_audit_log):
        """Test getting logs for specific match."""
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.select_related.return_value = mock_queryset
        mock_queryset.order_by.return_value = [mock_audit_log]
        mock_audit_log_model.objects.filter.return_value = mock_queryset
        
        dtos = adapter.get_match_logs(match_id=42)
        
        assert len(dtos) == 1
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_get_action_logs(self, mock_audit_log_model, adapter, mock_audit_log):
        """Test getting logs for specific action."""
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.select_related.return_value = mock_queryset
        mock_queryset.order_by.return_value = [mock_audit_log]
        mock_audit_log_model.objects.filter.return_value = mock_queryset
        
        dtos = adapter.get_action_logs(action="result_finalized")
        
        assert len(dtos) == 1


class TestAuditLogAdapterExport:
    """Tests for export functionality."""
    
    @patch('apps.tournament_ops.adapters.audit_log_adapter.AuditLog')
    def test_export_logs(self, mock_audit_log_model, adapter, mock_audit_log):
        """Test exporting logs with filters."""
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.select_related.return_value = mock_queryset
        mock_queryset.order_by.return_value = [mock_audit_log]
        mock_audit_log_model.objects.all.return_value = mock_queryset
        
        filters = AuditLogFilterDTO(tournament_id=10)
        dtos = adapter.export_logs(filters)
        
        assert len(dtos) == 1
        assert isinstance(dtos[0], AuditLogDTO)


# Run with: pytest tests/unit/tournament_ops/test_audit_log_adapter.py -v
