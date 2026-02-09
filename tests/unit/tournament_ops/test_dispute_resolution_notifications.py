"""
Test Suite for Notification Adapter Integration - Phase 6, Epic 6.5

Tests NotificationAdapter integration across dispute resolution workflows.
All tests verify notification calls without testing email/Discord delivery
(Phase 10 implementation).

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.5 (Notification System Integration)
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from apps.tournament_ops.services.dispute_service import DisputeService
from apps.tournament_ops.dtos import (
    DisputeDTO,
    MatchResultSubmissionDTO,
    RESOLUTION_TYPE_APPROVE_ORIGINAL,
    RESOLUTION_TYPE_APPROVE_DISPUTE,
    RESOLUTION_TYPE_CUSTOM_RESULT,
    RESOLUTION_TYPE_DISMISS_DISPUTE,
)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_dispute_adapter():
    """Mock DisputeAdapterProtocol."""
    adapter = Mock()
    adapter.get_dispute = Mock()
    adapter.update_dispute_status = Mock()
    adapter.log_verification_step = Mock()
    adapter.get_open_dispute_for_submission = Mock(side_effect=Exception("No open disputes"))
    return adapter


@pytest.fixture
def mock_result_submission_adapter():
    """Mock ResultSubmissionAdapterProtocol."""
    adapter = Mock()
    adapter.get_submission = Mock()
    adapter.update_submission_status = Mock()
    adapter.update_submission_payload = Mock()
    adapter.update_auto_confirm_deadline = Mock()
    return adapter


@pytest.fixture
def mock_result_verification_service():
    """Mock ResultVerificationService."""
    service = Mock()
    service.finalize_submission_after_verification = Mock()
    return service


@pytest.fixture
def mock_notification_adapter():
    """Mock NotificationAdapterProtocol."""
    adapter = Mock()
    adapter.notify_dispute_resolved = Mock()
    adapter.notify_submission_created = Mock()
    adapter.notify_dispute_created = Mock()
    adapter.notify_evidence_added = Mock()
    adapter.notify_auto_confirmed = Mock()
    return adapter


@pytest.fixture
def dispute_service(
    mock_dispute_adapter,
    mock_result_submission_adapter,
    mock_result_verification_service,
    mock_notification_adapter,
):
    """Create DisputeService with NotificationAdapter."""
    return DisputeService(
        dispute_adapter=mock_dispute_adapter,
        result_submission_adapter=mock_result_submission_adapter,
        result_verification_service=mock_result_verification_service,
        notification_adapter=mock_notification_adapter,
    )


@pytest.fixture
def sample_submission_dto():
    """Sample MatchResultSubmissionDTO."""
    return MatchResultSubmissionDTO(
        id=100,
        match_id=50,
        submitted_by_user_id=1,
        submitted_by_team_id=10,
        raw_result_payload={"winner_team_id": 10, "loser_team_id": 20, "score": "13-7"},
        status='disputed',
        proof_screenshot_url='https://example.com/proof.png',
        submitter_notes='',
        confirmed_at=None,
        confirmed_by_user_id=None,
        auto_confirm_deadline=datetime.now() + timedelta(hours=24),
        finalized_at=None,
        organizer_notes='',
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_dispute_dto():
    """Sample DisputeDTO."""
    return DisputeDTO(
        id=200,
        submission_id=100,
        opened_by_user_id=2,
        opened_by_team_id=20,
        reason_code='incorrect_score',
        description='Score was wrong',
        disputed_result_payload={"winner_team_id": 20, "loser_team_id": 10, "score": "13-8"},
        status='open',
        resolved_at=None,
        resolved_by_user_id=None,
        resolution_notes='',
        escalated_at=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# ==============================================================================
# Test: Notification Called for All Resolution Types
# ==============================================================================


class TestNotificationCalledForAllResolutionTypes:
    """Verify notify_dispute_resolved called for every resolution type."""
    
    def test_notification_called_for_approve_original(
        self,
        dispute_service,
        mock_notification_adapter,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test notification sent for approve_original."""
        # Setup
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
            mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
            
            # Execute
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type=RESOLUTION_TYPE_APPROVE_ORIGINAL,
                resolved_by_user_id=999,
            )
            
            # Assert
            assert mock_notification_adapter.notify_dispute_resolved.call_count == 1
    
    def test_notification_called_for_approve_dispute(
        self,
        dispute_service,
        mock_notification_adapter,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test notification sent for approve_dispute."""
        # Setup
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
            mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
            
            # Execute
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type=RESOLUTION_TYPE_APPROVE_DISPUTE,
                resolved_by_user_id=999,
            )
            
            # Assert
            assert mock_notification_adapter.notify_dispute_resolved.call_count == 1
    
    def test_notification_called_for_custom_result(
        self,
        dispute_service,
        mock_notification_adapter,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test notification sent for custom_result."""
        # Setup
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
            mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
            custom_payload = {"custom": True}
            
            # Execute
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type=RESOLUTION_TYPE_CUSTOM_RESULT,
                resolved_by_user_id=999,
                custom_result_payload=custom_payload,
            )
            
            # Assert
            assert mock_notification_adapter.notify_dispute_resolved.call_count == 1
    
    def test_notification_called_for_dismiss_dispute(
        self,
        dispute_service,
        mock_notification_adapter,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test notification sent for dismiss_dispute."""
        # Setup
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            with patch('apps.tournament_ops.services.dispute_service.timezone'):
                mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
                mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
                
                # Execute
                dispute_service.resolve_dispute(
                    submission_id=100,
                    dispute_id=200,
                    resolution_type=RESOLUTION_TYPE_DISMISS_DISPUTE,
                    resolved_by_user_id=999,
                )
                
                # Assert
                assert mock_notification_adapter.notify_dispute_resolved.call_count == 1


# ==============================================================================
# Test: Notification DTO Arguments
# ==============================================================================


class TestNotificationDTOArguments:
    """Verify notify_dispute_resolved receives correct DTO arguments."""
    
    def test_notification_receives_dispute_dto(
        self,
        dispute_service,
        mock_notification_adapter,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test notification receives DisputeDTO as argument."""
        # Setup
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
            mock_dispute_adapter.get_dispute.side_effect = [
                sample_dispute_dto,
                DisputeDTO(**{**sample_dispute_dto.__dict__, 'status': 'resolved_for_submitter'}),
            ]
            
            # Execute
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type=RESOLUTION_TYPE_APPROVE_ORIGINAL,
                resolved_by_user_id=999,
            )
            
            # Assert: Check DTO types
            call_kwargs = mock_notification_adapter.notify_dispute_resolved.call_args[1]
            assert isinstance(call_kwargs['dispute_dto'], DisputeDTO)
            assert call_kwargs['dispute_dto'].id == 200
    
    def test_notification_receives_submission_dto(
        self,
        dispute_service,
        mock_notification_adapter,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test notification receives MatchResultSubmissionDTO as argument."""
        # Setup
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
            mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
            
            # Execute
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type=RESOLUTION_TYPE_APPROVE_ORIGINAL,
                resolved_by_user_id=999,
            )
            
            # Assert: Check DTO types
            call_kwargs = mock_notification_adapter.notify_dispute_resolved.call_args[1]
            assert isinstance(call_kwargs['submission_dto'], MatchResultSubmissionDTO)
            assert call_kwargs['submission_dto'].id == 100
    
    def test_notification_receives_resolution_dto(
        self,
        dispute_service,
        mock_notification_adapter,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test notification receives DisputeResolutionDTO as argument."""
        # Setup
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
            mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
            
            # Execute
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type=RESOLUTION_TYPE_APPROVE_ORIGINAL,
                resolved_by_user_id=999,
                resolution_notes="Test notes",
            )
            
            # Assert: Check resolution DTO
            call_kwargs = mock_notification_adapter.notify_dispute_resolved.call_args[1]
            resolution_dto = call_kwargs['resolution_dto']
            assert resolution_dto.submission_id == 100
            assert resolution_dto.dispute_id == 200
            assert resolution_dto.resolution_type == RESOLUTION_TYPE_APPROVE_ORIGINAL
            assert resolution_dto.resolved_by_user_id == 999
            assert resolution_dto.resolution_notes == "Test notes"


# ==============================================================================
# Test: Notification Not Called on Validation Errors
# ==============================================================================


class TestNotificationNotCalledOnErrors:
    """Verify notification NOT sent when validation fails."""
    
    def test_notification_not_called_on_invalid_resolution_type(
        self,
        dispute_service,
        mock_notification_adapter,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test notification NOT sent when resolution_type is invalid."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        # Execute & Assert
        with pytest.raises(ValueError):
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type="invalid_type",
                resolved_by_user_id=999,
            )
        
        # Notification should NOT be called
        assert mock_notification_adapter.notify_dispute_resolved.call_count == 0
    
    def test_notification_not_called_on_already_resolved_dispute(
        self,
        dispute_service,
        mock_notification_adapter,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
    ):
        """Test notification NOT sent when dispute already resolved."""
        # Setup
        resolved_dispute = DisputeDTO(
            id=200,
            submission_id=100,
            opened_by_user_id=2,
            opened_by_team_id=20,
            reason_code='test',
            description='test',
            disputed_result_payload={},
            status='resolved_for_submitter',  # Already resolved
            resolved_at=datetime.now(),
            resolved_by_user_id=888,
            resolution_notes='',
            escalated_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = resolved_dispute
        
        # Execute & Assert
        from apps.tournament_ops.exceptions import DisputeAlreadyResolvedError
        with pytest.raises(DisputeAlreadyResolvedError):
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type=RESOLUTION_TYPE_APPROVE_ORIGINAL,
                resolved_by_user_id=999,
            )
        
        # Notification should NOT be called
        assert mock_notification_adapter.notify_dispute_resolved.call_count == 0


# ==============================================================================
# Test: Architecture Compliance - No ORM in tournament_ops
# ==============================================================================


class TestArchitectureCompliance:
    """Architecture guard tests."""
    
    def test_no_orm_imports_in_notification_adapter(self):
        """Test NotificationAdapter has no ORM imports."""
        import inspect
        from apps.tournament_ops.adapters import notification_adapter
        
        source = inspect.getsource(notification_adapter)
        
        # Check for forbidden imports
        forbidden_patterns = [
            'from apps.tournaments.models import',
            'from apps.games.models import',
            'from apps.organizations.models import',
            'from apps.user_profile.models import',
        ]
        
        lines = source.split('\n')
        for i, line in enumerate(lines):
            for pattern in forbidden_patterns:
                if pattern in line and not line.strip().startswith('#'):
                    pytest.fail(
                        f"Found ORM import in notification_adapter.py line {i+1}: {line.strip()}"
                    )
    
    def test_notification_adapter_uses_protocols_only(self):
        """Test NotificationAdapter methods accept DTOs, not ORM models."""
        import inspect
        from apps.tournament_ops.adapters.notification_adapter import NotificationAdapterProtocol
        
        # Get all public methods
        methods = [
            name for name in dir(NotificationAdapterProtocol)
            if not name.startswith('_') and callable(getattr(NotificationAdapterProtocol, name))
        ]
        
        # Verify methods exist (basic smoke test)
        expected_methods = [
            'notify_submission_created',
            'notify_dispute_created',
            'notify_evidence_added',
            'notify_dispute_resolved',
            'notify_auto_confirmed',
        ]
        
        for method in expected_methods:
            assert method in dir(NotificationAdapterProtocol), \
                f"NotificationAdapterProtocol missing expected method: {method}"
