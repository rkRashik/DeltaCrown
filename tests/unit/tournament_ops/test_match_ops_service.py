"""
Tests for MatchOpsService - Phase 7, Epic 7.4

Reference: Phase 7, Epic 7.4 - Match Operations Command Center
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from apps.tournament_ops.services.match_ops_service import MatchOpsService
from apps.tournament_ops.dtos import (
    MatchOperationLogDTO,
    MatchModeratorNoteDTO,
    MatchOpsActionResultDTO,
    MatchOpsPermissionDTO,
)


@pytest.fixture
def mock_match_ops_adapter():
    """Mock MatchOpsAdapter."""
    return Mock()


@pytest.fixture
def mock_staffing_adapter():
    """Mock StaffingAdapter."""
    return Mock()


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher."""
    return Mock()


@pytest.fixture
def match_ops_service(mock_match_ops_adapter, mock_staffing_adapter, mock_event_publisher):
    """MatchOpsService instance with mocked dependencies."""
    return MatchOpsService(
        match_ops_adapter=mock_match_ops_adapter,
        staffing_adapter=mock_staffing_adapter,
        event_publisher=mock_event_publisher
    )


class TestMarkMatchLive:
    """Tests for mark_match_live()."""
    
    def test_mark_match_live_success(self, match_ops_service, mock_match_ops_adapter, mock_event_publisher):
        """Test successfully marking match live."""
        # Setup
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        mock_match_ops_adapter.get_match_state.return_value = 'PENDING'
        mock_match_ops_adapter.add_operation_log.return_value = MatchOperationLogDTO(
            log_id=1, match_id=100, operator_user_id=1, operator_username='admin',
            operation_type='LIVE', payload={'previous_state': 'PENDING'}, created_at=datetime.utcnow()
        )
        
        # Execute
        result = match_ops_service.mark_match_live(
            match_id=100, tournament_id=10, operator_user_id=1
        )
        
        # Assert
        assert result.success is True
        assert result.new_state == 'LIVE'
        assert result.match_id == 100
        mock_match_ops_adapter.set_match_state.assert_called_once_with(100, 'LIVE', 1)
        mock_event_publisher.publish.assert_called_once()
    
    def test_mark_match_live_permission_denied(self, match_ops_service, mock_match_ops_adapter):
        """Test permission denied."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=False, can_pause=False, can_resume=False,
            can_force_complete=False, can_override_result=False,
            can_add_note=False, can_assign_referee=False,
            is_referee=False, is_admin=False
        )
        
        with pytest.raises(PermissionError, match="lacks permission"):
            match_ops_service.mark_match_live(100, 10, 1)
    
    def test_mark_match_live_invalid_state(self, match_ops_service, mock_match_ops_adapter):
        """Test invalid state transition."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        mock_match_ops_adapter.get_match_state.return_value = 'COMPLETED'
        
        with pytest.raises(ValueError, match="Cannot mark match live"):
            match_ops_service.mark_match_live(100, 10, 1)


class TestPauseMatch:
    """Tests for pause_match()."""
    
    def test_pause_match_success_with_reason(self, match_ops_service, mock_match_ops_adapter):
        """Test pause with reason."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        mock_match_ops_adapter.get_match_state.return_value = 'LIVE'
        mock_match_ops_adapter.add_operation_log.return_value = MatchOperationLogDTO(
            log_id=2, match_id=100, operator_user_id=1, operator_username='admin',
            operation_type='PAUSED', payload={'reason': 'Technical issue'}, created_at=datetime.utcnow()
        )
        
        result = match_ops_service.pause_match(100, 10, 1, reason='Technical issue')
        
        assert result.success is True
        assert result.new_state == 'PAUSED'
        assert len(result.warnings) == 0
    
    def test_pause_match_warning_no_reason(self, match_ops_service, mock_match_ops_adapter):
        """Test pause without reason generates warning."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        mock_match_ops_adapter.get_match_state.return_value = 'LIVE'
        mock_match_ops_adapter.add_operation_log.return_value = MatchOperationLogDTO(
            log_id=2, match_id=100, operator_user_id=1, operator_username='admin',
            operation_type='PAUSED', payload={'reason': None}, created_at=datetime.utcnow()
        )
        
        result = match_ops_service.pause_match(100, 10, 1)
        
        assert result.success is True
        assert len(result.warnings) == 1
        assert "No reason provided" in result.warnings[0]


class TestResumeMatch:
    """Tests for resume_match()."""
    
    def test_resume_match_success(self, match_ops_service, mock_match_ops_adapter):
        """Test resume match."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        mock_match_ops_adapter.get_match_state.return_value = 'PAUSED'
        mock_match_ops_adapter.add_operation_log.return_value = MatchOperationLogDTO(
            log_id=3, match_id=100, operator_user_id=1, operator_username='admin',
            operation_type='RESUMED', payload={}, created_at=datetime.utcnow()
        )
        
        result = match_ops_service.resume_match(100, 10, 1)
        
        assert result.success is True
        assert result.new_state == 'LIVE'


class TestForceCompleteMatch:
    """Tests for force_complete_match()."""
    
    def test_force_complete_with_result(self, match_ops_service, mock_match_ops_adapter):
        """Test force complete with result data."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        mock_match_ops_adapter.add_operation_log.return_value = MatchOperationLogDTO(
            log_id=4, match_id=100, operator_user_id=1, operator_username='admin',
            operation_type='FORCE_COMPLETED', payload={'reason': 'No show'}, created_at=datetime.utcnow()
        )
        
        result_data = {'winner': 'team1', 'reason': 'forfeit'}
        result = match_ops_service.force_complete_match(
            100, 10, 1, reason='No show', result_data=result_data
        )
        
        assert result.success is True
        assert result.new_state == 'COMPLETED'
        mock_match_ops_adapter.override_match_result.assert_called_once_with(100, result_data, 1)
    
    def test_force_complete_missing_reason(self, match_ops_service, mock_match_ops_adapter):
        """Test force complete requires reason."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        
        with pytest.raises(ValueError, match="Reason is required"):
            match_ops_service.force_complete_match(100, 10, 1, reason='')


class TestAddModeratorNote:
    """Tests for add_moderator_note()."""
    
    def test_add_note_success(self, match_ops_service, mock_match_ops_adapter):
        """Test adding moderator note."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        mock_match_ops_adapter.add_moderator_note.return_value = MatchModeratorNoteDTO(
            note_id=1, match_id=100, author_user_id=1, author_username='admin',
            content='Test note', created_at=datetime.utcnow()
        )
        
        note = match_ops_service.add_moderator_note(100, 10, 1, 'Test note')
        
        assert note.note_id == 1
        assert note.content == 'Test note'
        mock_match_ops_adapter.add_operation_log.assert_called_once()


class TestOverrideMatchResult:
    """Tests for override_match_result()."""
    
    def test_override_result_success(self, match_ops_service, mock_match_ops_adapter):
        """Test override match result."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        mock_match_ops_adapter.get_match_result.return_value = {'winner': 'team1'}
        mock_match_ops_adapter.override_match_result.return_value = MatchOpsActionResultDTO(
            success=True, message='Result overridden', match_id=100,
            new_state='COMPLETED', operation_log=None, warnings=[]
        )
        
        new_result = {'winner': 'team2', 'reason': 'correction'}
        result = match_ops_service.override_match_result(
            100, 10, 1, new_result, reason='Admin correction'
        )
        
        assert result.success is True
    
    def test_override_result_missing_reason(self, match_ops_service, mock_match_ops_adapter):
        """Test override requires reason."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        
        with pytest.raises(ValueError, match="Reason is required"):
            match_ops_service.override_match_result(
                100, 10, 1, {'winner': 'team2'}, reason=''
            )


class TestGetMatchTimeline:
    """Tests for get_match_timeline()."""
    
    def test_get_timeline(self, match_ops_service, mock_match_ops_adapter):
        """Test get match timeline."""
        logs = [
            MatchOperationLogDTO(
                log_id=1, match_id=100, operator_user_id=1, operator_username='admin',
                operation_type='LIVE', payload={}, created_at=datetime(2025, 1, 1, 10, 0)
            ),
            MatchOperationLogDTO(
                log_id=2, match_id=100, operator_user_id=1, operator_username='admin',
                operation_type='PAUSED', payload={}, created_at=datetime(2025, 1, 1, 10, 30)
            ),
        ]
        mock_match_ops_adapter.list_operation_logs.return_value = logs
        
        timeline = match_ops_service.get_match_timeline(100, limit=50)
        
        assert len(timeline) == 2
        assert timeline[0].event_type == 'OPERATION'
        assert timeline[0].description.startswith('admin')


class TestCheckPermissions:
    """Tests for check_permissions()."""
    
    def test_check_permissions(self, match_ops_service, mock_match_ops_adapter):
        """Test permission check."""
        mock_match_ops_adapter.get_match_permissions.return_value = MatchOpsPermissionDTO(
            user_id=1, tournament_id=10, match_id=100,
            can_mark_live=True, can_pause=True, can_resume=True,
            can_force_complete=True, can_override_result=True,
            can_add_note=True, can_assign_referee=True,
            is_referee=False, is_admin=True
        )
        
        perms = match_ops_service.check_permissions(1, 10, 100)
        
        assert perms.can_mark_live is True
        assert perms.is_admin is True
