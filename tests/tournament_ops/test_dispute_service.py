"""
Unit Tests for DisputeService - Phase 6, Epic 6.2

Tests dispute lifecycle: escalation, resolution, evidence management.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.2 (Opponent Verification & Dispute System)
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from apps.tournament_ops.services import DisputeService
from apps.tournament_ops.dtos import (
    DisputeDTO,
    DisputeEvidenceDTO,
    MatchResultSubmissionDTO,
)
from apps.tournament_ops.exceptions import (
    DisputeError,
    DisputeNotFoundError,
    InvalidDisputeStateError,
)


@pytest.fixture
def mock_dispute_adapter():
    """Mock DisputeAdapter."""
    return Mock()


@pytest.fixture
def mock_result_submission_adapter():
    """Mock ResultSubmissionAdapter."""
    return Mock()


@pytest.fixture
def service(mock_dispute_adapter, mock_result_submission_adapter):
    """Create DisputeService with mocked adapters."""
    return DisputeService(
        dispute_adapter=mock_dispute_adapter,
        result_submission_adapter=mock_result_submission_adapter,
    )


@pytest.fixture
def open_dispute():
    """Sample open dispute DTO."""
    return DisputeDTO(
        id=201,
        submission_id=101,
        opened_by_user_id=20,
        opened_by_team_id=6,
        reason_code='incorrect_score',
        description='Score is wrong',
        status='open',
        resolution_notes=None,
        opened_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
        resolved_at=None,
        resolved_by_user_id=None,
        escalated_at=None,
    )


@pytest.fixture
def escalated_dispute():
    """Sample escalated dispute DTO."""
    return DisputeDTO(
        id=201,
        submission_id=101,
        opened_by_user_id=20,
        opened_by_team_id=6,
        reason_code='incorrect_score',
        description='Score is wrong',
        status='escalated',
        resolution_notes=None,
        opened_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 12, 12, 11, 30, 0, tzinfo=timezone.utc),
        resolved_at=None,
        resolved_by_user_id=None,
        escalated_at=datetime(2025, 12, 12, 11, 30, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def resolved_dispute():
    """Sample resolved dispute DTO."""
    return DisputeDTO(
        id=201,
        submission_id=101,
        opened_by_user_id=20,
        opened_by_team_id=6,
        reason_code='incorrect_score',
        description='Score is wrong',
        status='resolved_for_submitter',
        resolution_notes='Verified submitter was correct',
        opened_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 12, 12, 12, 0, 0, tzinfo=timezone.utc),
        resolved_at=datetime(2025, 12, 12, 12, 0, 0, tzinfo=timezone.utc),
        resolved_by_user_id=1,
        escalated_at=None,
    )


class TestEscalateDispute:
    """Tests for DisputeService.escalate_dispute()."""
    
    def test_escalate_dispute_sets_status_and_publishes_event(
        self, service, mock_dispute_adapter, open_dispute, escalated_dispute
    ):
        """
        Test escalate_dispute updates status to 'escalated' and publishes event.
        
        Workflow:
        1. Get dispute (status=open)
        2. Update status to 'escalated'
        3. Log verification step
        4. Publish DisputeEscalatedEvent
        """
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        mock_dispute_adapter.update_dispute_status.return_value = escalated_dispute
        
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            result = service.escalate_dispute(dispute_id=201, escalated_by_user_id=1)
        
        # Assert
        assert result.status == 'escalated'
        assert result.escalated_at is not None
        
        # Verify update_dispute_status called
        mock_dispute_adapter.update_dispute_status.assert_called_once_with(
            dispute_id=201,
            status='escalated',
        )
        
        # Verify event published
        assert mock_bus.publish.call_count == 1
        event_call = mock_bus.publish.call_args[0][0]
        assert event_call.name == 'DisputeEscalatedEvent'
        assert event_call.payload['dispute_id'] == 201
        assert event_call.payload['escalated_by_user_id'] == 1
    
    def test_escalate_dispute_logs_verification_step(
        self, service, mock_dispute_adapter, open_dispute, escalated_dispute
    ):
        """Test escalate_dispute logs dispute_escalated step."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        mock_dispute_adapter.update_dispute_status.return_value = escalated_dispute
        
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            # Act
            service.escalate_dispute(dispute_id=201, escalated_by_user_id=1)
        
        # Assert
        mock_dispute_adapter.log_verification_step.assert_called_once()
        call_args = mock_dispute_adapter.log_verification_step.call_args
        assert call_args[1]['submission_id'] == 101
        assert call_args[1]['step'] == 'dispute_escalated'
        assert call_args[1]['status'] == 'success'
        assert call_args[1]['performed_by_user_id'] == 1
    
    def test_escalate_dispute_sets_escalated_at_timestamp(
        self, service, mock_dispute_adapter, open_dispute, escalated_dispute
    ):
        """Test escalate_dispute sets escalated_at timestamp."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        mock_dispute_adapter.update_dispute_status.return_value = escalated_dispute
        
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            # Act
            result = service.escalate_dispute(dispute_id=201, escalated_by_user_id=1)
        
        # Assert
        assert result.escalated_at is not None
        assert result.escalated_at == datetime(2025, 12, 12, 11, 30, 0, tzinfo=timezone.utc)
    
    def test_escalate_dispute_raises_if_already_resolved(
        self, service, mock_dispute_adapter, resolved_dispute
    ):
        """Test cannot escalate already resolved dispute."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = resolved_dispute
        
        # Act & Assert
        with pytest.raises(InvalidDisputeStateError, match='Cannot escalate resolved dispute'):
            service.escalate_dispute(dispute_id=201, escalated_by_user_id=1)


class TestResolveDispute:
    """Tests for DisputeService.resolve_dispute()."""
    
    def test_resolve_dispute_for_submitter_sets_submission_finalized(
        self, service, mock_dispute_adapter, mock_result_submission_adapter, open_dispute
    ):
        """
        Test resolution="submitter_wins" sets submission to 'finalized'.
        
        Workflow:
        1. Get dispute (status=open)
        2. Update dispute status to 'resolved_for_submitter'
        3. Update submission status to 'finalized'
        4. Log verification step
        5. Publish DisputeResolvedEvent
        """
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        
        resolved = DisputeDTO(
            **{**open_dispute.__dict__, 'status': 'resolved_for_submitter',
               'resolved_at': datetime(2025, 12, 12, 12, 0, 0, tzinfo=timezone.utc),
               'resolved_by_user_id': 1, 'resolution_notes': 'Submitter correct'}
        )
        mock_dispute_adapter.update_dispute_status.return_value = resolved
        
        finalized_submission = MatchResultSubmissionDTO(
            id=101, match_id=50, submitted_by_user_id=10, submitted_by_team_id=5,
            raw_result_payload={}, proof_screenshot_url=None, submitter_notes='',
            status='finalized', submitted_at=datetime(2025, 12, 12, 10, 0, 0, tzinfo=timezone.utc),
            confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
        )
        mock_result_submission_adapter.update_submission_status.return_value = finalized_submission
        
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            result = service.resolve_dispute(
                dispute_id=201,
                resolved_by_user_id=1,
                resolution='submitter_wins',
                resolution_notes='Submitter correct',
            )
        
        # Assert
        assert result.status == 'resolved_for_submitter'
        assert result.resolved_by_user_id == 1
        
        # Verify submission updated
        mock_result_submission_adapter.update_submission_status.assert_called_once_with(
            submission_id=101,
            status='finalized',
        )
        
        # Verify event published
        event_call = mock_bus.publish.call_args[0][0]
        assert event_call.name == 'DisputeResolvedEvent'
        assert event_call.payload['resolution'] == 'submitter_wins'
        assert event_call.payload['submission_status'] == 'finalized'
    
    def test_resolve_dispute_for_opponent_sets_submission_rejected(
        self, service, mock_dispute_adapter, mock_result_submission_adapter, open_dispute
    ):
        """Test resolution="opponent_wins" sets submission to 'rejected'."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        
        resolved = DisputeDTO(
            **{**open_dispute.__dict__, 'status': 'resolved_for_opponent',
               'resolved_at': datetime(2025, 12, 12, 12, 0, 0, tzinfo=timezone.utc),
               'resolved_by_user_id': 1, 'resolution_notes': 'Opponent correct'}
        )
        mock_dispute_adapter.update_dispute_status.return_value = resolved
        
        rejected_submission = MatchResultSubmissionDTO(
            id=101, match_id=50, submitted_by_user_id=10, submitted_by_team_id=5,
            raw_result_payload={}, proof_screenshot_url=None, submitter_notes='',
            status='rejected', submitted_at=datetime(2025, 12, 12, 10, 0, 0, tzinfo=timezone.utc),
            confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
        )
        mock_result_submission_adapter.update_submission_status.return_value = rejected_submission
        
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            # Act
            result = service.resolve_dispute(
                dispute_id=201,
                resolved_by_user_id=1,
                resolution='opponent_wins',
                resolution_notes='Opponent correct',
            )
        
        # Assert
        assert result.status == 'resolved_for_opponent'
        
        # Verify submission updated
        mock_result_submission_adapter.update_submission_status.assert_called_once_with(
            submission_id=101,
            status='rejected',
        )
    
    def test_resolve_dispute_cancelled_leaves_submission_pending(
        self, service, mock_dispute_adapter, mock_result_submission_adapter, open_dispute
    ):
        """Test resolution="cancelled" reverts submission to 'pending'."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        
        cancelled = DisputeDTO(
            **{**open_dispute.__dict__, 'status': 'cancelled',
               'resolved_at': datetime(2025, 12, 12, 12, 0, 0, tzinfo=timezone.utc),
               'resolved_by_user_id': 1, 'resolution_notes': 'Cancelled'}
        )
        mock_dispute_adapter.update_dispute_status.return_value = cancelled
        
        pending_submission = MatchResultSubmissionDTO(
            id=101, match_id=50, submitted_by_user_id=10, submitted_by_team_id=5,
            raw_result_payload={}, proof_screenshot_url=None, submitter_notes='',
            status='pending', submitted_at=datetime(2025, 12, 12, 10, 0, 0, tzinfo=timezone.utc),
            confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
        )
        mock_result_submission_adapter.update_submission_status.return_value = pending_submission
        
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            # Act
            result = service.resolve_dispute(
                dispute_id=201,
                resolved_by_user_id=1,
                resolution='cancelled',
                resolution_notes='Cancelled',
            )
        
        # Assert
        assert result.status == 'cancelled'
        
        # Verify submission reverted to pending
        mock_result_submission_adapter.update_submission_status.assert_called_once_with(
            submission_id=101,
            status='pending',
        )
    
    def test_resolve_dispute_sets_resolved_at_and_resolved_by_user(
        self, service, mock_dispute_adapter, mock_result_submission_adapter, open_dispute
    ):
        """Test resolve_dispute sets resolved_at and resolved_by_user_id."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        
        resolved = DisputeDTO(
            **{**open_dispute.__dict__, 'status': 'resolved_for_submitter',
               'resolved_at': datetime(2025, 12, 12, 12, 0, 0, tzinfo=timezone.utc),
               'resolved_by_user_id': 1, 'resolution_notes': 'Notes'}
        )
        mock_dispute_adapter.update_dispute_status.return_value = resolved
        
        mock_result_submission_adapter.update_submission_status.return_value = Mock()
        
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
            # Act
            result = service.resolve_dispute(
                dispute_id=201,
                resolved_by_user_id=1,
                resolution='submitter_wins',
                resolution_notes='Notes',
            )
        
        # Assert
        assert result.resolved_at == datetime(2025, 12, 12, 12, 0, 0, tzinfo=timezone.utc)
        assert result.resolved_by_user_id == 1
        assert result.resolution_notes == 'Notes'
        
        # Verify adapter called with resolved_by_user_id
        mock_dispute_adapter.update_dispute_status.assert_called_once()
        call_args = mock_dispute_adapter.update_dispute_status.call_args
        assert call_args[1]['resolved_by_user_id'] == 1
        assert call_args[1]['resolution_notes'] == 'Notes'
    
    def test_resolve_dispute_raises_if_already_resolved(
        self, service, mock_dispute_adapter, resolved_dispute
    ):
        """Test cannot resolve already resolved dispute."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = resolved_dispute
        
        # Act & Assert
        with pytest.raises(InvalidDisputeStateError, match='already resolved'):
            service.resolve_dispute(
                dispute_id=201,
                resolved_by_user_id=1,
                resolution='submitter_wins',
            )
    
    def test_resolve_dispute_publishes_dispute_resolved_event(
        self, service, mock_dispute_adapter, mock_result_submission_adapter, open_dispute
    ):
        """Test resolve_dispute publishes DisputeResolvedEvent with full payload."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        
        resolved = DisputeDTO(
            **{**open_dispute.__dict__, 'status': 'resolved_for_submitter',
               'resolved_at': datetime(2025, 12, 12, 12, 0, 0, tzinfo=timezone.utc),
               'resolved_by_user_id': 1, 'resolution_notes': 'Notes'}
        )
        mock_dispute_adapter.update_dispute_status.return_value = resolved
        
        mock_result_submission_adapter.update_submission_status.return_value = Mock(id=101)
        
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            service.resolve_dispute(
                dispute_id=201,
                resolved_by_user_id=1,
                resolution='submitter_wins',
                resolution_notes='Notes',
            )
        
        # Assert
        event_call = mock_bus.publish.call_args[0][0]
        assert event_call.name == 'DisputeResolvedEvent'
        assert event_call.payload['dispute_id'] == 201
        assert event_call.payload['resolution'] == 'submitter_wins'
        assert event_call.payload['dispute_status'] == 'resolved_for_submitter'
        assert event_call.payload['submission_status'] == 'finalized'
        assert event_call.metadata['resolution_notes'] == 'Notes'
    
    def test_resolve_dispute_raises_on_invalid_resolution(
        self, service, mock_dispute_adapter, open_dispute
    ):
        """Test resolve_dispute rejects invalid resolution values."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        
        # Act & Assert
        with pytest.raises(DisputeError, match='Invalid resolution'):
            service.resolve_dispute(
                dispute_id=201,
                resolved_by_user_id=1,
                resolution='invalid_choice',
            )
    
    def test_resolve_dispute_handles_all_resolution_types(
        self, service, mock_dispute_adapter, mock_result_submission_adapter, open_dispute
    ):
        """Test all 3 resolution types map to correct dispute/submission statuses."""
        # Test data for all 3 resolutions
        test_cases = [
            ('submitter_wins', 'resolved_for_submitter', 'finalized'),
            ('opponent_wins', 'resolved_for_opponent', 'rejected'),
            ('cancelled', 'cancelled', 'pending'),
        ]
        
        for resolution, dispute_status, submission_status in test_cases:
            # Arrange
            mock_dispute_adapter.get_dispute.return_value = open_dispute
            
            resolved = DisputeDTO(
                **{**open_dispute.__dict__, 'status': dispute_status,
                   'resolved_at': datetime(2025, 12, 12, 12, 0, 0, tzinfo=timezone.utc),
                   'resolved_by_user_id': 1}
            )
            mock_dispute_adapter.update_dispute_status.return_value = resolved
            mock_result_submission_adapter.update_submission_status.return_value = Mock()
            
            with patch('apps.tournament_ops.services.dispute_service.get_event_bus'):
                # Act
                result = service.resolve_dispute(
                    dispute_id=201,
                    resolved_by_user_id=1,
                    resolution=resolution,
                )
            
            # Assert
            assert result.status == dispute_status
            
            # Verify submission updated with correct status
            call_args = mock_result_submission_adapter.update_submission_status.call_args
            assert call_args[1]['status'] == submission_status


class TestAddEvidence:
    """Tests for DisputeService.add_evidence()."""
    
    def test_add_evidence_creates_evidence_via_adapter(
        self, service, mock_dispute_adapter, open_dispute
    ):
        """Test add_evidence delegates to adapter."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        
        evidence = DisputeEvidenceDTO(
            id=301,
            dispute_id=201,
            uploaded_by_user_id=20,
            evidence_type='screenshot',
            url='https://imgur.com/proof.png',
            notes='Additional proof',
            created_at=datetime(2025, 12, 12, 11, 15, 0, tzinfo=timezone.utc),
        )
        mock_dispute_adapter.add_evidence.return_value = evidence
        
        # Act
        result = service.add_evidence(
            dispute_id=201,
            uploaded_by_user_id=20,
            evidence_type='screenshot',
            url='https://imgur.com/proof.png',
            notes='Additional proof',
        )
        
        # Assert
        assert result.id == 301
        assert result.dispute_id == 201
        assert result.evidence_type == 'screenshot'
        
        mock_dispute_adapter.add_evidence.assert_called_once_with(
            dispute_id=201,
            uploaded_by_user_id=20,
            evidence_type='screenshot',
            url='https://imgur.com/proof.png',
            notes='Additional proof',
        )
    
    def test_add_evidence_publishes_no_extraneous_events(
        self, service, mock_dispute_adapter, open_dispute
    ):
        """Test add_evidence does not publish events (lightweight action)."""
        # Arrange
        mock_dispute_adapter.get_dispute.return_value = open_dispute
        mock_dispute_adapter.add_evidence.return_value = Mock()
        
        with patch('apps.tournament_ops.services.dispute_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            service.add_evidence(
                dispute_id=201,
                uploaded_by_user_id=20,
                evidence_type='screenshot',
                url='https://imgur.com/proof.png',
            )
        
        # Assert: no events published
        mock_bus.publish.assert_not_called()


class TestArchitectureGuards:
    """Architecture compliance tests."""
    
    def test_dispute_service_never_imports_orm_directly(self):
        """Test DisputeService does not import Django ORM models."""
        # Read source file
        import inspect
        from apps.tournament_ops.services.dispute_service import DisputeService
        
        source = inspect.getsource(DisputeService)
        
        # Assert: no Django model imports in DisputeService class
        assert 'from apps.tournaments.models' not in source
        assert 'from apps.teams.models' not in source
        assert 'from apps.accounts.models' not in source
        
        # All domain access must go through adapters
        assert 'dispute_adapter' in source
        assert 'result_submission_adapter' in source


class TestOpenDisputeFromSubmission:
    """Tests for DisputeService.open_dispute_from_submission() helper."""
    
    def test_open_dispute_from_submission_uses_adapter_and_logs(
        self, service, mock_dispute_adapter
    ):
        """Test helper method creates dispute via adapter."""
        # Arrange
        mock_dispute_adapter.get_open_dispute_for_submission.return_value = None
        
        dispute = DisputeDTO(
            id=201, submission_id=101, opened_by_user_id=20, opened_by_team_id=6,
            reason_code='incorrect_score', description='Wrong', status='open',
            resolution_notes=None,
            opened_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
            resolved_at=None, resolved_by_user_id=None, escalated_at=None,
        )
        mock_dispute_adapter.create_dispute.return_value = dispute
        
        # Act
        result = service.open_dispute_from_submission(
            submission_id=101,
            opened_by_user_id=20,
            opened_by_team_id=6,
            reason_code='incorrect_score',
            description='Wrong',
        )
        
        # Assert
        assert result.id == 201
        mock_dispute_adapter.create_dispute.assert_called_once_with(
            submission_id=101,
            opened_by_user_id=20,
            opened_by_team_id=6,
            reason_code='incorrect_score',
            description='Wrong',
        )
    
    def test_open_dispute_from_submission_raises_if_duplicate(
        self, service, mock_dispute_adapter, open_dispute
    ):
        """Test cannot create duplicate dispute."""
        # Arrange
        mock_dispute_adapter.get_open_dispute_for_submission.return_value = open_dispute
        
        # Act & Assert
        with pytest.raises(DisputeError, match='already has an open dispute'):
            service.open_dispute_from_submission(
                submission_id=101,
                opened_by_user_id=20,
                opened_by_team_id=6,
                reason_code='incorrect_score',
                description='Wrong',
            )
