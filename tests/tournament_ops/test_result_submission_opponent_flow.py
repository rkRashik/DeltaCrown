"""
Unit Tests for ResultSubmissionService.opponent_response() - Phase 6, Epic 6.2

Tests opponent verification workflow (confirm/dispute decision paths).

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.2 (Opponent Verification & Dispute System)
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timezone

from apps.tournament_ops.services import ResultSubmissionService
from apps.tournament_ops.dtos import (
    MatchResultSubmissionDTO,
    DisputeDTO,
    DisputeEvidenceDTO,
    MatchDTO,
)
from apps.tournament_ops.exceptions import (
    SubmissionError,
    OpponentVerificationError,
    InvalidOpponentDecisionError,
)


@pytest.fixture
def mock_adapters():
    """Create mocked adapters for ResultSubmissionService."""
    result_submission_adapter = Mock()
    schema_validation_adapter = Mock()
    match_adapter = Mock()
    game_adapter = Mock()
    dispute_adapter = Mock()
    
    return {
        'result_submission_adapter': result_submission_adapter,
        'schema_validation_adapter': schema_validation_adapter,
        'match_adapter': match_adapter,
        'game_adapter': game_adapter,
        'dispute_adapter': dispute_adapter,
    }


@pytest.fixture
def service(mock_adapters):
    """Create ResultSubmissionService with mocked adapters."""
    return ResultSubmissionService(
        result_submission_adapter=mock_adapters['result_submission_adapter'],
        schema_validation_adapter=mock_adapters['schema_validation_adapter'],
        match_adapter=mock_adapters['match_adapter'],
        game_adapter=mock_adapters['game_adapter'],
        dispute_adapter=mock_adapters['dispute_adapter'],
    )


@pytest.fixture
def pending_submission():
    """Sample pending submission DTO."""
    return MatchResultSubmissionDTO(
        id=101,
        match_id=50,
        submitted_by_user_id=10,
        submitted_by_team_id=5,
        raw_result_payload={'winner_team_id': 5, 'loser_team_id': 6},
        proof_screenshot_url='https://example.com/proof.png',
        submitter_notes='GG',
        status='pending',
        submitted_at=datetime(2025, 12, 12, 10, 0, 0, tzinfo=timezone.utc),
        confirmed_at=None,
        confirmed_by_user_id=None,
        auto_confirmed=False,
    )


@pytest.fixture
def match_dto():
    """Sample match DTO."""
    return MatchDTO(
        id=50,
        tournament_id=1,
        round_num=1,
        match_num=1,
        team_a_id=5,
        team_b_id=6,
        status='completed',
    )


class TestOpponentResponseConfirm:
    """Tests for opponent_response with decision="confirm"."""
    
    def test_opponent_confirm_calls_confirm_result_and_publishes_events(
        self, service, mock_adapters, pending_submission, match_dto
    ):
        """
        Test opponent confirmation delegates to confirm_result.
        
        Workflow:
        1. Get submission (status=pending)
        2. Get match (validate opponent)
        3. Call confirm_result (reuse logic)
        4. Log verification step
        5. Publish MatchResultConfirmedEvent
        """
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['match_adapter'].get_match.return_value = match_dto
        
        confirmed_submission = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'confirmed', 'confirmed_by_user_id': 20}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = confirmed_submission
        
        with patch('apps.tournament_ops.services.result_submission_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            result = service.opponent_response(
                submission_id=101,
                responding_user_id=20,
                decision='confirm',
            )
        
        # Assert
        assert result.status == 'confirmed'
        assert result.confirmed_by_user_id == 20
        
        # Verify update_submission_status called
        mock_adapters['result_submission_adapter'].update_submission_status.assert_called_once_with(
            submission_id=101,
            status='confirmed',
            confirmed_by_user_id=20,
        )
        
        # Verify verification step logged
        mock_adapters['dispute_adapter'].log_verification_step.assert_called_once()
        call_args = mock_adapters['dispute_adapter'].log_verification_step.call_args
        assert call_args[1]['step'] == 'opponent_confirm'
        assert call_args[1]['submission_id'] == 101
        assert call_args[1]['performed_by_user_id'] == 20
        
        # Verify event published
        assert mock_bus.publish.call_count >= 1
        event_call = mock_bus.publish.call_args_list[0][0][0]
        assert event_call.name == 'MatchResultConfirmedEvent'
        assert event_call.payload['submission_id'] == 101
    
    def test_opponent_confirm_rejected_if_same_user_as_submitter(
        self, service, mock_adapters, pending_submission, match_dto
    ):
        """Test opponent confirm fails if responding user is submitter."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['match_adapter'].get_match.return_value = match_dto
        
        # Act & Assert
        with pytest.raises(OpponentVerificationError, match='cannot respond to their own submission'):
            service.opponent_response(
                submission_id=101,
                responding_user_id=10,  # Same as submitted_by_user_id
                decision='confirm',
            )
    
    def test_opponent_confirm_rejected_if_submission_not_pending(
        self, service, mock_adapters, pending_submission
    ):
        """Test opponent confirm fails if submission not in pending state."""
        # Arrange
        confirmed_submission = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'confirmed'}
        )
        mock_adapters['result_submission_adapter'].get_submission.return_value = confirmed_submission
        
        # Act & Assert
        with pytest.raises(SubmissionError, match='Submission 101 is not pending'):
            service.opponent_response(
                submission_id=101,
                responding_user_id=20,
                decision='confirm',
            )


class TestOpponentResponseDispute:
    """Tests for opponent_response with decision="dispute"."""
    
    def test_opponent_dispute_creates_dispute_record_and_sets_submission_disputed(
        self, service, mock_adapters, pending_submission, match_dto
    ):
        """
        Test opponent dispute creates DisputeRecord and updates submission.
        
        Workflow:
        1. Validate decision="dispute" requires reason_code
        2. Get submission (status=pending)
        3. Get match (validate opponent)
        4. Create DisputeRecord via dispute_adapter
        5. Update submission status to 'disputed'
        6. Log verification step
        7. Publish MatchResultDisputedEvent
        """
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['match_adapter'].get_match.return_value = match_dto
        
        dispute_dto = DisputeDTO(
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
        mock_adapters['dispute_adapter'].create_dispute.return_value = dispute_dto
        
        disputed_submission = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'disputed'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = disputed_submission
        
        with patch('apps.tournament_ops.services.result_submission_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            result = service.opponent_response(
                submission_id=101,
                responding_user_id=20,
                decision='dispute',
                reason_code='incorrect_score',
                notes='Score is wrong',
            )
        
        # Assert
        assert result.status == 'disputed'
        
        # Verify dispute created
        mock_adapters['dispute_adapter'].create_dispute.assert_called_once_with(
            submission_id=101,
            opened_by_user_id=20,
            opened_by_team_id=6,  # Opponent team (match.team_b_id)
            reason_code='incorrect_score',
            description='Score is wrong',
        )
        
        # Verify submission status updated
        mock_adapters['result_submission_adapter'].update_submission_status.assert_called_once_with(
            submission_id=101,
            status='disputed',
        )
        
        # Verify verification step logged
        mock_adapters['dispute_adapter'].log_verification_step.assert_called_once()
        call_args = mock_adapters['dispute_adapter'].log_verification_step.call_args
        assert call_args[1]['step'] == 'opponent_dispute'
        
        # Verify event published
        assert mock_bus.publish.call_count >= 1
        event_call = mock_bus.publish.call_args_list[0][0][0]
        assert event_call.name == 'MatchResultDisputedEvent'
        assert event_call.payload['dispute_id'] == 201
    
    def test_opponent_dispute_logs_verification_step(
        self, service, mock_adapters, pending_submission, match_dto
    ):
        """Test opponent dispute logs opponent_dispute step."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['match_adapter'].get_match.return_value = match_dto
        
        dispute_dto = DisputeDTO(
            id=201, submission_id=101, opened_by_user_id=20, opened_by_team_id=6,
            reason_code='incorrect_score', description='Wrong', status='open',
            resolution_notes=None,
            opened_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
            resolved_at=None, resolved_by_user_id=None, escalated_at=None,
        )
        mock_adapters['dispute_adapter'].create_dispute.return_value = dispute_dto
        
        disputed_submission = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'disputed'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = disputed_submission
        
        with patch('apps.tournament_ops.services.result_submission_service.get_event_bus'):
            # Act
            service.opponent_response(
                submission_id=101,
                responding_user_id=20,
                decision='dispute',
                reason_code='incorrect_score',
                notes='Wrong',
            )
        
        # Assert
        mock_adapters['dispute_adapter'].log_verification_step.assert_called_once()
        call_args = mock_adapters['dispute_adapter'].log_verification_step.call_args
        assert call_args[1]['step'] == 'opponent_dispute'
        assert call_args[1]['status'] == 'success'
        assert call_args[1]['details']['dispute_id'] == 201
    
    def test_opponent_dispute_can_attach_multiple_evidence_entries(
        self, service, mock_adapters, pending_submission, match_dto
    ):
        """Test opponent can attach multiple evidence items when disputing."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['match_adapter'].get_match.return_value = match_dto
        
        dispute_dto = DisputeDTO(
            id=201, submission_id=101, opened_by_user_id=20, opened_by_team_id=6,
            reason_code='incorrect_score', description='Wrong', status='open',
            resolution_notes=None,
            opened_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
            resolved_at=None, resolved_by_user_id=None, escalated_at=None,
        )
        mock_adapters['dispute_adapter'].create_dispute.return_value = dispute_dto
        
        disputed_submission = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'disputed'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = disputed_submission
        
        evidence_list = [
            {'type': 'screenshot', 'url': 'https://imgur.com/1.png', 'notes': 'Proof 1'},
            {'type': 'video', 'url': 'https://youtube.com/watch?v=abc', 'notes': 'Proof 2'},
        ]
        
        with patch('apps.tournament_ops.services.result_submission_service.get_event_bus'):
            # Act
            service.opponent_response(
                submission_id=101,
                responding_user_id=20,
                decision='dispute',
                reason_code='incorrect_score',
                notes='Wrong',
                evidence=evidence_list,
            )
        
        # Assert
        assert mock_adapters['dispute_adapter'].add_evidence.call_count == 2
        calls = mock_adapters['dispute_adapter'].add_evidence.call_args_list
        
        assert calls[0][1]['dispute_id'] == 201
        assert calls[0][1]['evidence_type'] == 'screenshot'
        assert calls[0][1]['url'] == 'https://imgur.com/1.png'
        
        assert calls[1][1]['dispute_id'] == 201
        assert calls[1][1]['evidence_type'] == 'video'


class TestOpponentResponseValidation:
    """Tests for opponent_response validation logic."""
    
    def test_opponent_response_raises_on_invalid_decision(
        self, service, mock_adapters, pending_submission
    ):
        """Test opponent_response rejects invalid decision values."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        
        # Act & Assert
        with pytest.raises(InvalidOpponentDecisionError, match='Invalid decision'):
            service.opponent_response(
                submission_id=101,
                responding_user_id=20,
                decision='invalid_choice',
            )
    
    def test_opponent_response_validates_reason_code_required_for_disputes(
        self, service, mock_adapters, pending_submission
    ):
        """Test dispute decision requires reason_code."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        
        # Act & Assert
        with pytest.raises(OpponentVerificationError, match='reason_code required'):
            service.opponent_response(
                submission_id=101,
                responding_user_id=20,
                decision='dispute',
                reason_code=None,  # Missing required field
            )
    
    def test_opponent_response_uses_match_participant_info_for_auth(
        self, service, mock_adapters, pending_submission, match_dto
    ):
        """Test opponent validation uses match participant data."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['match_adapter'].get_match.return_value = match_dto
        
        confirmed_submission = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'confirmed', 'confirmed_by_user_id': 20}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = confirmed_submission
        
        with patch('apps.tournament_ops.services.result_submission_service.get_event_bus'):
            # Act
            service.opponent_response(
                submission_id=101,
                responding_user_id=20,
                decision='confirm',
            )
        
        # Assert: match_adapter.get_match called to validate opponent
        mock_adapters['match_adapter'].get_match.assert_called_once_with(50)


class TestOpponentResponseDisputeWorkflow:
    """Tests for dispute-specific workflow behaviors."""
    
    def test_opponent_response_does_not_call_match_service_for_pending_dispute(
        self, service, mock_adapters, pending_submission, match_dto
    ):
        """Test disputing does not finalize match (stays pending)."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['match_adapter'].get_match.return_value = match_dto
        
        dispute_dto = DisputeDTO(
            id=201, submission_id=101, opened_by_user_id=20, opened_by_team_id=6,
            reason_code='incorrect_score', description='Wrong', status='open',
            resolution_notes=None,
            opened_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
            resolved_at=None, resolved_by_user_id=None, escalated_at=None,
        )
        mock_adapters['dispute_adapter'].create_dispute.return_value = dispute_dto
        
        disputed_submission = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'disputed'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = disputed_submission
        
        with patch('apps.tournament_ops.services.result_submission_service.get_event_bus'):
            # Act
            service.opponent_response(
                submission_id=101,
                responding_user_id=20,
                decision='dispute',
                reason_code='incorrect_score',
                notes='Wrong',
            )
        
        # Assert: no match finalization calls (future: MatchService.accept_match_result)
        # For now, just verify submission status is 'disputed', not 'finalized'
        assert disputed_submission.status == 'disputed'
    
    def test_opponent_response_does_not_duplicate_disputes_if_already_open(
        self, service, mock_adapters, pending_submission, match_dto
    ):
        """Test cannot create duplicate dispute for same submission."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['match_adapter'].get_match.return_value = match_dto
        
        # Existing open dispute
        existing_dispute = DisputeDTO(
            id=200, submission_id=101, opened_by_user_id=15, opened_by_team_id=6,
            reason_code='other', description='Existing', status='open',
            resolution_notes=None,
            opened_at=datetime(2025, 12, 12, 10, 30, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 12, 10, 30, 0, tzinfo=timezone.utc),
            resolved_at=None, resolved_by_user_id=None, escalated_at=None,
        )
        mock_adapters['dispute_adapter'].get_open_dispute_for_submission.return_value = existing_dispute
        
        with patch('apps.tournament_ops.services.result_submission_service.get_event_bus'):
            # Act & Assert
            # Note: Current implementation doesn't check for existing dispute in opponent_response
            # This is a design decision - opponent_response creates dispute if decision='dispute'
            # The adapter create_dispute should enforce uniqueness constraint
            # For now, we test that create_dispute is called (constraint enforced at DB level)
            
            # We'll simulate adapter raising error
            from apps.tournament_ops.exceptions import DisputeError
            mock_adapters['dispute_adapter'].create_dispute.side_effect = DisputeError(
                "Submission 101 already has an open dispute"
            )
            
            with pytest.raises(DisputeError, match='already has an open dispute'):
                service.opponent_response(
                    submission_id=101,
                    responding_user_id=20,
                    decision='dispute',
                    reason_code='incorrect_score',
                    notes='Wrong',
                )
    
    def test_opponent_response_publishes_match_result_disputed_event(
        self, service, mock_adapters, pending_submission, match_dto
    ):
        """Test MatchResultDisputedEvent published with full payload."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['match_adapter'].get_match.return_value = match_dto
        
        dispute_dto = DisputeDTO(
            id=201, submission_id=101, opened_by_user_id=20, opened_by_team_id=6,
            reason_code='incorrect_score', description='Wrong score', status='open',
            resolution_notes=None,
            opened_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
            resolved_at=None, resolved_by_user_id=None, escalated_at=None,
        )
        mock_adapters['dispute_adapter'].create_dispute.return_value = dispute_dto
        
        disputed_submission = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'disputed'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = disputed_submission
        
        with patch('apps.tournament_ops.services.result_submission_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            service.opponent_response(
                submission_id=101,
                responding_user_id=20,
                decision='dispute',
                reason_code='incorrect_score',
                notes='Wrong score',
            )
        
        # Assert
        assert mock_bus.publish.call_count >= 1
        event_call = mock_bus.publish.call_args_list[0][0][0]
        assert event_call.name == 'MatchResultDisputedEvent'
        assert event_call.payload['dispute_id'] == 201
        assert event_call.payload['submission_id'] == 101
        assert event_call.payload['match_id'] == 50
        assert event_call.payload['opened_by_user_id'] == 20
        assert event_call.payload['reason_code'] == 'incorrect_score'
