"""
Test Suite for Dispute Resolution Service - Phase 6, Epic 6.5

Tests comprehensive dispute resolution flows with 4 resolution types:
- approve_original: Original submission correct, finalize with original payload
- approve_dispute: Disputer correct, finalize with disputed payload
- custom_result: Neither correct, finalize with custom organizer payload
- dismiss_dispute: Invalid dispute, restart 24-hour timer (no finalization)

All tests use mocked adapters and services to verify orchestration logic.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.5 (Dispute Resolution Module)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call

from apps.tournament_ops.services.dispute_service import DisputeService
from apps.tournament_ops.dtos import (
    DisputeDTO,
    MatchResultSubmissionDTO,
    DisputeResolutionDTO,
    RESOLUTION_TYPE_APPROVE_ORIGINAL,
    RESOLUTION_TYPE_APPROVE_DISPUTE,
    RESOLUTION_TYPE_CUSTOM_RESULT,
    RESOLUTION_TYPE_DISMISS_DISPUTE,
)
from apps.tournament_ops.exceptions import (
    DisputeAlreadyResolvedError,
    DisputeError,
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
    service.verify_submission = Mock()
    return service


@pytest.fixture
def mock_notification_adapter():
    """Mock NotificationAdapterProtocol."""
    adapter = Mock()
    adapter.notify_dispute_resolved = Mock()
    return adapter


@pytest.fixture
def mock_event_bus():
    """Mock EventBus."""
    with patch('apps.tournament_ops.services.dispute_service.get_event_bus') as mock:
        bus = Mock()
        mock.return_value = bus
        yield bus


@pytest.fixture
def dispute_service(
    mock_dispute_adapter,
    mock_result_submission_adapter,
    mock_result_verification_service,
    mock_notification_adapter,
):
    """Create DisputeService with mocked dependencies."""
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
        submitter_notes='Original submission',
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
    """Sample DisputeDTO (open)."""
    return DisputeDTO(
        id=200,
        submission_id=100,
        opened_by_user_id=2,
        opened_by_team_id=20,
        reason_code='incorrect_score',
        description='Score was actually 13-8',
        disputed_result_payload={"winner_team_id": 20, "loser_team_id": 10, "score": "13-8"},
        status='open',
        resolved_at=None,
        resolved_by_user_id=None,
        resolution_notes='',
        escalated_at=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_resolved_dispute_dto():
    """Sample DisputeDTO (already resolved)."""
    return DisputeDTO(
        id=200,
        submission_id=100,
        opened_by_user_id=2,
        opened_by_team_id=20,
        reason_code='incorrect_score',
        description='Score was actually 13-8',
        disputed_result_payload={"winner_team_id": 20, "loser_team_id": 10, "score": "13-8"},
        status='resolved_for_submitter',
        resolved_at=datetime.now(),
        resolved_by_user_id=999,
        resolution_notes='Already resolved',
        escalated_at=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# ==============================================================================
# Test: Approve Original Resolution
# ==============================================================================


class TestResolveDisputeApproveOriginal:
    """Tests for approve_original resolution type."""
    
    def test_approve_original_finalizes_with_original_payload(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        mock_result_verification_service,
        mock_notification_adapter,
        mock_event_bus,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test approve_original uses original payload and finalizes."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.side_effect = [
            sample_dispute_dto,  # First call in resolve_dispute
            DisputeDTO(**{**sample_dispute_dto.__dict__, 'status': 'resolved_for_submitter'}),  # After update
        ]
        mock_result_submission_adapter.get_submission.return_value = MatchResultSubmissionDTO(
            **{**sample_submission_dto.__dict__, 'status': 'finalized'}
        )
        
        # Execute
        result = dispute_service.resolve_dispute(
            submission_id=100,
            dispute_id=200,
            resolution_type=RESOLUTION_TYPE_APPROVE_ORIGINAL,
            resolved_by_user_id=999,
            resolution_notes="Original was correct",
            custom_result_payload=None,
        )
        
        # Assert: Finalization called with original payload (no payload update)
        mock_result_verification_service.finalize_submission_after_verification.assert_called_once_with(
            submission_id=100,
            resolved_by_user_id=999,
        )
        
        # Assert: Dispute marked as resolved for submitter
        mock_dispute_adapter.update_dispute_status.assert_called_with(
            dispute_id=200,
            status='resolved_for_submitter',
            resolved_by_user_id=999,
            resolution_notes="Original was correct",
        )
        
        # Assert: Payload NOT updated (keep original)
        mock_result_submission_adapter.update_submission_payload.assert_not_called()
        
        # Assert: Deadline NOT restarted
        mock_result_submission_adapter.update_auto_confirm_deadline.assert_not_called()
        
        # Assert: Notification sent
        mock_notification_adapter.notify_dispute_resolved.assert_called_once()
        call_args = mock_notification_adapter.notify_dispute_resolved.call_args
        assert call_args[1]['resolution_dto'].resolution_type == RESOLUTION_TYPE_APPROVE_ORIGINAL
        
        # Assert: Event published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.name == 'DisputeResolvedEvent'
        assert event.payload['resolution_type'] == RESOLUTION_TYPE_APPROVE_ORIGINAL
        assert event.payload['requires_finalization'] is True
    
    def test_approve_original_logs_organizer_review(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test approve_original logs organizer_review step."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        # Execute
        dispute_service.resolve_dispute(
            submission_id=100,
            dispute_id=200,
            resolution_type=RESOLUTION_TYPE_APPROVE_ORIGINAL,
            resolved_by_user_id=999,
            resolution_notes="Checked proof screenshot",
        )
        
        # Assert: Verification log entry created
        mock_dispute_adapter.log_verification_step.assert_called_once()
        log_call = mock_dispute_adapter.log_verification_step.call_args
        assert log_call[1]['submission_id'] == 100
        assert log_call[1]['step'] == 'organizer_review'
        assert log_call[1]['status'] == 'success'
        assert log_call[1]['details']['dispute_id'] == 200
        assert log_call[1]['details']['resolution_type'] == RESOLUTION_TYPE_APPROVE_ORIGINAL
        assert log_call[1]['details']['resolved_by_user_id'] == 999
        assert log_call[1]['details']['used_payload_type'] == 'original'


# ==============================================================================
# Test: Approve Dispute Resolution
# ==============================================================================


class TestResolveDisputeApproveDispute:
    """Tests for approve_dispute resolution type."""
    
    def test_approve_dispute_finalizes_with_disputed_payload(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        mock_result_verification_service,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test approve_dispute uses disputed payload and finalizes."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.side_effect = [
            sample_dispute_dto,
            DisputeDTO(**{**sample_dispute_dto.__dict__, 'status': 'resolved_for_opponent'}),
        ]
        
        # Execute
        dispute_service.resolve_dispute(
            submission_id=100,
            dispute_id=200,
            resolution_type=RESOLUTION_TYPE_APPROVE_DISPUTE,
            resolved_by_user_id=999,
            resolution_notes="Disputer provided better proof",
        )
        
        # Assert: Payload updated to disputed version BEFORE finalization
        mock_result_submission_adapter.update_submission_payload.assert_called_once_with(
            submission_id=100,
            raw_result_payload=sample_dispute_dto.disputed_result_payload,
        )
        
        # Assert: Finalization called after payload update
        mock_result_verification_service.finalize_submission_after_verification.assert_called_once_with(
            submission_id=100,
            resolved_by_user_id=999,
        )
        
        # Assert: Dispute marked as resolved for opponent
        mock_dispute_adapter.update_dispute_status.assert_called_with(
            dispute_id=200,
            status='resolved_for_opponent',
            resolved_by_user_id=999,
            resolution_notes="Disputer provided better proof",
        )
    
    def test_approve_dispute_fails_if_no_disputed_payload(
        self,
        dispute_service,
        mock_result_submission_adapter,
        mock_dispute_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test approve_dispute raises error if dispute has no disputed_result_payload."""
        # Setup: Dispute without disputed payload
        dispute_no_payload = DisputeDTO(**{**sample_dispute_dto.__dict__, 'disputed_result_payload': None})
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = dispute_no_payload
        
        # Execute & Assert
        with pytest.raises(DisputeError, match="has no disputed_result_payload"):
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type=RESOLUTION_TYPE_APPROVE_DISPUTE,
                resolved_by_user_id=999,
            )


# ==============================================================================
# Test: Custom Result Resolution
# ==============================================================================


class TestResolveDisputeCustomResult:
    """Tests for custom_result resolution type."""
    
    def test_custom_result_finalizes_with_custom_payload(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        mock_result_verification_service,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test custom_result uses custom organizer payload and finalizes."""
        # Setup
        custom_payload = {"winner_team_id": 10, "loser_team_id": 20, "score": "13-9", "organizer_override": True}
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.side_effect = [
            sample_dispute_dto,
            DisputeDTO(**{**sample_dispute_dto.__dict__, 'status': 'resolved_custom'}),
        ]
        
        # Execute
        dispute_service.resolve_dispute(
            submission_id=100,
            dispute_id=200,
            resolution_type=RESOLUTION_TYPE_CUSTOM_RESULT,
            resolved_by_user_id=999,
            resolution_notes="Reviewed video, actual score was 13-9",
            custom_result_payload=custom_payload,
        )
        
        # Assert: Payload updated to custom version
        mock_result_submission_adapter.update_submission_payload.assert_called_once_with(
            submission_id=100,
            raw_result_payload=custom_payload,
        )
        
        # Assert: Finalization called
        mock_result_verification_service.finalize_submission_after_verification.assert_called_once()
        
        # Assert: Dispute marked as resolved_custom
        mock_dispute_adapter.update_dispute_status.assert_called_with(
            dispute_id=200,
            status='resolved_custom',
            resolved_by_user_id=999,
            resolution_notes="Reviewed video, actual score was 13-9",
        )
    
    def test_custom_result_validation_requires_payload(
        self,
        dispute_service,
        mock_result_submission_adapter,
        mock_dispute_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test custom_result raises validation error if custom_result_payload is None."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        # Execute & Assert
        with pytest.raises(ValueError, match="custom_result_payload is required"):
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type=RESOLUTION_TYPE_CUSTOM_RESULT,
                resolved_by_user_id=999,
                custom_result_payload=None,  # Missing!
            )
    
    def test_custom_result_logs_correct_payload_type(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test custom_result logs 'custom' as used_payload_type."""
        # Setup
        custom_payload = {"custom": True}
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        # Execute
        dispute_service.resolve_dispute(
            submission_id=100,
            dispute_id=200,
            resolution_type=RESOLUTION_TYPE_CUSTOM_RESULT,
            resolved_by_user_id=999,
            custom_result_payload=custom_payload,
        )
        
        # Assert: Log details contain 'custom' payload type
        log_call = mock_dispute_adapter.log_verification_step.call_args
        assert log_call[1]['details']['used_payload_type'] == 'custom'


# ==============================================================================
# Test: Dismiss Dispute Resolution
# ==============================================================================


class TestResolveDisputeDismiss:
    """Tests for dismiss_dispute resolution type."""
    
    @patch('apps.tournament_ops.services.dispute_service.timezone')
    def test_dismiss_dispute_does_not_finalize(
        self,
        mock_timezone,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        mock_result_verification_service,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test dismiss_dispute does NOT finalize submission."""
        # Setup
        now = datetime(2025, 12, 13, 10, 0, 0)
        mock_timezone.now.return_value = now
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.side_effect = [
            sample_dispute_dto,
            DisputeDTO(**{**sample_dispute_dto.__dict__, 'status': 'dismissed'}),
        ]
        
        # Execute
        dispute_service.resolve_dispute(
            submission_id=100,
            dispute_id=200,
            resolution_type=RESOLUTION_TYPE_DISMISS_DISPUTE,
            resolved_by_user_id=999,
            resolution_notes="Dispute was frivolous",
        )
        
        # Assert: Finalization NOT called
        mock_result_verification_service.finalize_submission_after_verification.assert_not_called()
        
        # Assert: Payload NOT updated
        mock_result_submission_adapter.update_submission_payload.assert_not_called()
        
        # Assert: Dispute marked as dismissed
        mock_dispute_adapter.update_dispute_status.assert_called_with(
            dispute_id=200,
            status='dismissed',
            resolved_by_user_id=999,
            resolution_notes="Dispute was frivolous",
        )
    
    @patch('apps.tournament_ops.services.dispute_service.timezone')
    def test_dismiss_dispute_restarts_24h_timer(
        self,
        mock_timezone,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test dismiss_dispute restarts 24-hour auto-confirm timer."""
        # Setup
        now = datetime(2025, 12, 13, 10, 0, 0)
        expected_deadline = now + timedelta(hours=24)
        mock_timezone.now.return_value = now
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        # Execute
        dispute_service.resolve_dispute(
            submission_id=100,
            dispute_id=200,
            resolution_type=RESOLUTION_TYPE_DISMISS_DISPUTE,
            resolved_by_user_id=999,
        )
        
        # Assert: Deadline updated (we check call was made, not exact datetime due to timing)
        mock_result_submission_adapter.update_auto_confirm_deadline.assert_called_once()
        call_args = mock_result_submission_adapter.update_auto_confirm_deadline.call_args
        assert call_args[1]['submission_id'] == 100
        # Deadline should be ~24 hours from now
        actual_deadline = call_args[1]['auto_confirm_deadline']
        assert (actual_deadline - now).total_seconds() == pytest.approx(24 * 60 * 60, abs=5)
    
    @patch('apps.tournament_ops.services.dispute_service.timezone')
    def test_dismiss_dispute_reverts_submission_to_pending(
        self,
        mock_timezone,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test dismiss_dispute reverts submission status to pending."""
        # Setup
        mock_timezone.now.return_value = datetime.now()
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        # Execute
        dispute_service.resolve_dispute(
            submission_id=100,
            dispute_id=200,
            resolution_type=RESOLUTION_TYPE_DISMISS_DISPUTE,
            resolved_by_user_id=999,
        )
        
        # Assert: Status reverted to pending
        mock_result_submission_adapter.update_submission_status.assert_called_with(
            submission_id=100,
            status='pending',
        )
    
    def test_dismiss_dispute_still_notifies(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        mock_notification_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test dismiss_dispute still calls notification adapter."""
        # Setup
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
            
            # Assert: Notification sent even for dismissed dispute
            mock_notification_adapter.notify_dispute_resolved.assert_called_once()


# ==============================================================================
# Test: Validation & Error Cases
# ==============================================================================


class TestResolveDisputeValidation:
    """Tests for validation and error handling."""
    
    def test_invalid_resolution_type_raises_error(
        self,
        dispute_service,
        mock_result_submission_adapter,
        mock_dispute_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test invalid resolution_type raises ValueError."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        # Execute & Assert
        with pytest.raises(ValueError, match="Invalid resolution_type"):
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type="foobar_invalid",  # Invalid!
                resolved_by_user_id=999,
            )
    
    def test_already_resolved_dispute_raises_error(
        self,
        dispute_service,
        mock_result_submission_adapter,
        mock_dispute_adapter,
        sample_submission_dto,
        sample_resolved_dispute_dto,
    ):
        """Test resolving already-resolved dispute raises DisputeAlreadyResolvedError."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_resolved_dispute_dto
        
        # Execute & Assert
        with pytest.raises(DisputeAlreadyResolvedError, match="already resolved"):
            dispute_service.resolve_dispute(
                submission_id=100,
                dispute_id=200,
                resolution_type=RESOLUTION_TYPE_APPROVE_ORIGINAL,
                resolved_by_user_id=999,
            )


# ==============================================================================
# Test: Notification Integration
# ==============================================================================


class TestNotificationIntegration:
    """Tests for NotificationAdapter integration."""
    
    def test_notify_dispute_resolved_called_for_all_resolution_types(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        mock_notification_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test notify_dispute_resolved called for each resolution type."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        resolution_types = [
            RESOLUTION_TYPE_APPROVE_ORIGINAL,
            RESOLUTION_TYPE_APPROVE_DISPUTE,
            RESOLUTION_TYPE_CUSTOM_RESULT,
            RESOLUTION_TYPE_DISMISS_DISPUTE,
        ]
        
        for resolution_type in resolution_types:
            # Reset mocks
            mock_notification_adapter.reset_mock()
            
            # Prepare custom payload if needed
            custom_payload = {"custom": True} if resolution_type == RESOLUTION_TYPE_CUSTOM_RESULT else None
            
            # Execute
            with patch('apps.tournament_ops.services.dispute_service.timezone'):
                dispute_service.resolve_dispute(
                    submission_id=100,
                    dispute_id=200,
                    resolution_type=resolution_type,
                    resolved_by_user_id=999,
                    custom_result_payload=custom_payload,
                )
            
            # Assert: Notification called exactly once
            assert mock_notification_adapter.notify_dispute_resolved.call_count == 1, \
                f"notify_dispute_resolved not called for {resolution_type}"


# ==============================================================================
# Test: Event Publishing
# ==============================================================================


class TestEventPublishing:
    """Tests for DisputeResolvedEvent publishing."""
    
    def test_event_published_with_correct_payload(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        mock_event_bus,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test DisputeResolvedEvent published with correct payload."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        # Execute
        dispute_service.resolve_dispute(
            submission_id=100,
            dispute_id=200,
            resolution_type=RESOLUTION_TYPE_APPROVE_ORIGINAL,
            resolved_by_user_id=999,
            resolution_notes="Test resolution",
        )
        
        # Assert: Event published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        
        assert event.name == 'DisputeResolvedEvent'
        assert event.payload['dispute_id'] == 200
        assert event.payload['submission_id'] == 100
        assert event.payload['resolution_type'] == RESOLUTION_TYPE_APPROVE_ORIGINAL
        assert event.payload['resolved_by_user_id'] == 999
        assert event.payload['requires_finalization'] is True
        assert event.metadata['resolution_notes'] == "Test resolution"


# ==============================================================================
# Test: Legacy API Compatibility
# ==============================================================================


class TestLegacyAPICompatibility:
    """Tests for backward-compatible resolve_dispute_legacy method."""
    
    def test_legacy_submitter_wins_maps_to_approve_original(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        mock_result_verification_service,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test legacy 'submitter_wins' maps to approve_original."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        # Execute
        dispute_service.resolve_dispute_legacy(
            dispute_id=200,
            resolved_by_user_id=999,
            resolution='submitter_wins',
            resolution_notes="Legacy API call",
        )
        
        # Assert: Finalization called (approve_original behavior)
        mock_result_verification_service.finalize_submission_after_verification.assert_called_once()
    
    def test_legacy_opponent_wins_maps_to_approve_dispute(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test legacy 'opponent_wins' maps to approve_dispute."""
        # Setup
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
        
        # Execute
        dispute_service.resolve_dispute_legacy(
            dispute_id=200,
            resolved_by_user_id=999,
            resolution='opponent_wins',
        )
        
        # Assert: Payload updated (approve_dispute behavior)
        mock_result_submission_adapter.update_submission_payload.assert_called_once()
    
    def test_legacy_cancelled_maps_to_dismiss_dispute(
        self,
        dispute_service,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        sample_submission_dto,
        sample_dispute_dto,
    ):
        """Test legacy 'cancelled' maps to dismiss_dispute."""
        # Setup
        with patch('apps.tournament_ops.services.dispute_service.timezone'):
            mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
            mock_dispute_adapter.get_dispute.return_value = sample_dispute_dto
            
            # Execute
            dispute_service.resolve_dispute_legacy(
                dispute_id=200,
                resolved_by_user_id=999,
                resolution='cancelled',
            )
            
            # Assert: Deadline restarted (dismiss_dispute behavior)
            mock_result_submission_adapter.update_auto_confirm_deadline.assert_called_once()


# ==============================================================================
# Test: Architecture Compliance
# ==============================================================================


class TestArchitectureCompliance:
    """Tests for architecture compliance (no ORM in tournament_ops)."""
    
    def test_no_direct_orm_imports_in_dispute_service(self):
        """Test DisputeService has no module-level ORM imports."""
        import inspect
        from apps.tournament_ops.services import dispute_service
        
        source = inspect.getsource(dispute_service)
        
        # Check for forbidden imports at module level
        # Allow method-level imports (e.g., inside _resolve_dismiss_dispute)
        lines = source.split('\n')
        for i, line in enumerate(lines):
            # Skip if inside a function/method (simple heuristic: indented)
            if line.startswith('    ') or line.startswith('\t'):
                continue
            
            # Check module-level imports
            if 'from apps.tournaments.models import' in line or 'from apps.games.models import' in line:
                pytest.fail(
                    f"Found ORM import at module level in dispute_service.py line {i+1}: {line.strip()}"
                )
