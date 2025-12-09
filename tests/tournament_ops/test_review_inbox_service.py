"""
Unit Tests for ReviewInboxService - Phase 6, Epic 6.3

Tests organizer results inbox workflows: listing, filtering, finalization, rejection.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.3 (Organizer Results Inbox)
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone

from apps.tournament_ops.services import ReviewInboxService
from apps.tournament_ops.dtos import (
    OrganizerReviewItemDTO,
    MatchResultSubmissionDTO,
    DisputeDTO,
)
from apps.tournament_ops.exceptions import (
    InvalidSubmissionStateError,
)


@pytest.fixture
def mock_adapters():
    """Create mocked adapters for ReviewInboxService."""
    return {
        'review_inbox_adapter': Mock(),
        'dispute_adapter': Mock(),
        'result_submission_adapter': Mock(),
        'match_service': Mock(),
    }


@pytest.fixture
def service(mock_adapters):
    """Create ReviewInboxService with mocked adapters."""
    return ReviewInboxService(
        review_inbox_adapter=mock_adapters['review_inbox_adapter'],
        dispute_adapter=mock_adapters['dispute_adapter'],
        result_submission_adapter=mock_adapters['result_submission_adapter'],
        match_service=mock_adapters['match_service'],
    )


@pytest.fixture
def pending_submission():
    """Sample pending submission."""
    now = datetime.now(timezone.utc)
    return MatchResultSubmissionDTO(
        id=101, match_id=50, tournament_id=1, stage_id=10,
        submitted_by_user_id=10, submitted_by_team_id=5,
        raw_result_payload={'winner_team_id': 5},
        proof_screenshot_url='https://example.com/proof.png',
        submitter_notes='GG', status='pending',
        submitted_at=now - timedelta(hours=6),
        confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
        auto_confirm_deadline=now + timedelta(hours=18),
    )


@pytest.fixture
def disputed_submission():
    """Sample disputed submission."""
    now = datetime.now(timezone.utc)
    return MatchResultSubmissionDTO(
        id=102, match_id=51, tournament_id=1, stage_id=10,
        submitted_by_user_id=11, submitted_by_team_id=6,
        raw_result_payload={'winner_team_id': 6},
        proof_screenshot_url='https://example.com/proof2.png',
        submitter_notes='', status='disputed',
        submitted_at=now - timedelta(hours=10),
        confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
        auto_confirm_deadline=now + timedelta(hours=14),
    )


@pytest.fixture
def confirmed_submission():
    """Sample confirmed submission."""
    now = datetime.now(timezone.utc)
    return MatchResultSubmissionDTO(
        id=103, match_id=52, tournament_id=1, stage_id=10,
        submitted_by_user_id=12, submitted_by_team_id=7,
        raw_result_payload={'winner_team_id': 7},
        proof_screenshot_url=None, submitter_notes='', status='confirmed',
        submitted_at=now - timedelta(hours=20),
        confirmed_at=now - timedelta(hours=4),
        confirmed_by_user_id=20, auto_confirmed=False,
        auto_confirm_deadline=now + timedelta(hours=4),
    )


@pytest.fixture
def open_dispute():
    """Sample open dispute."""
    return DisputeDTO(
        id=201, submission_id=102, opened_by_user_id=20, opened_by_team_id=6,
        reason_code='incorrect_score', description='Score is wrong', status='open',
        resolution_notes=None,
        opened_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 12, 12, 11, 0, 0, tzinfo=timezone.utc),
        resolved_at=None, resolved_by_user_id=None, escalated_at=None,
    )


class TestListReviewItems:
    """Tests for list_review_items method."""
    
    def test_list_review_items_fetches_all_categories(
        self, service, mock_adapters, pending_submission, disputed_submission,
        confirmed_submission, open_dispute
    ):
        """Test list_review_items fetches pending, disputed, overdue, ready-for-finalization."""
        # Arrange
        mock_adapters['review_inbox_adapter'].get_pending_submissions.return_value = [
            pending_submission
        ]
        mock_adapters['review_inbox_adapter'].get_disputed_submissions.return_value = [
            (disputed_submission, open_dispute)
        ]
        mock_adapters['review_inbox_adapter'].get_overdue_auto_confirm.return_value = []
        mock_adapters['review_inbox_adapter'].get_ready_for_finalization.return_value = [
            confirmed_submission
        ]
        
        # Act
        items = service.list_review_items(tournament_id=1)
        
        # Assert
        assert len(items) == 3  # pending + disputed + confirmed
        assert mock_adapters['review_inbox_adapter'].get_pending_submissions.called
        assert mock_adapters['review_inbox_adapter'].get_disputed_submissions.called
        assert mock_adapters['review_inbox_adapter'].get_overdue_auto_confirm.called
        assert mock_adapters['review_inbox_adapter'].get_ready_for_finalization.called
    
    def test_list_review_items_creates_organizer_review_item_dtos(
        self, service, mock_adapters, pending_submission
    ):
        """Test list_review_items creates OrganizerReviewItemDTO objects."""
        # Arrange
        mock_adapters['review_inbox_adapter'].get_pending_submissions.return_value = [
            pending_submission
        ]
        mock_adapters['review_inbox_adapter'].get_disputed_submissions.return_value = []
        mock_adapters['review_inbox_adapter'].get_overdue_auto_confirm.return_value = []
        mock_adapters['review_inbox_adapter'].get_ready_for_finalization.return_value = []
        
        # Act
        items = service.list_review_items(tournament_id=1)
        
        # Assert
        assert len(items) == 1
        item = items[0]
        assert isinstance(item, OrganizerReviewItemDTO)
        assert item.submission_id == 101
        assert item.priority > 0
    
    def test_list_review_items_sorts_by_priority_when_enabled(
        self, service, mock_adapters, pending_submission, disputed_submission,
        open_dispute
    ):
        """Test list_review_items sorts by priority (disputed first)."""
        # Arrange
        mock_adapters['review_inbox_adapter'].get_pending_submissions.return_value = [
            pending_submission
        ]
        mock_adapters['review_inbox_adapter'].get_disputed_submissions.return_value = [
            (disputed_submission, open_dispute)
        ]
        mock_adapters['review_inbox_adapter'].get_overdue_auto_confirm.return_value = []
        mock_adapters['review_inbox_adapter'].get_ready_for_finalization.return_value = []
        
        # Act
        items = service.list_review_items(tournament_id=1, sort_by_priority=True)
        
        # Assert
        assert len(items) == 2
        # Disputed should be first (priority 1)
        assert items[0].submission_id == 102
        assert items[0].priority == 1
        # Pending should be second (priority 3 or 4)
        assert items[1].submission_id == 101
    
    def test_list_review_items_filters_by_tournament(
        self, service, mock_adapters, pending_submission
    ):
        """Test tournament_id filter passed to adapters."""
        # Arrange
        mock_adapters['review_inbox_adapter'].get_pending_submissions.return_value = [
            pending_submission
        ]
        mock_adapters['review_inbox_adapter'].get_disputed_submissions.return_value = []
        mock_adapters['review_inbox_adapter'].get_overdue_auto_confirm.return_value = []
        mock_adapters['review_inbox_adapter'].get_ready_for_finalization.return_value = []
        
        # Act
        service.list_review_items(tournament_id=5)
        
        # Assert
        mock_adapters['review_inbox_adapter'].get_pending_submissions.assert_called_once_with(5)
        mock_adapters['review_inbox_adapter'].get_disputed_submissions.assert_called_once_with(5)
        mock_adapters['review_inbox_adapter'].get_overdue_auto_confirm.assert_called_once_with(5)
        mock_adapters['review_inbox_adapter'].get_ready_for_finalization.assert_called_once_with(5)


class TestFinalizeSubmission:
    """Tests for finalize_submission method."""
    
    def test_finalize_submission_updates_status_to_finalized(
        self, service, mock_adapters, confirmed_submission
    ):
        """Test finalize_submission updates submission status."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = confirmed_submission
        mock_adapters['dispute_adapter'].get_open_dispute_for_submission.return_value = None
        
        finalized = MatchResultSubmissionDTO(
            **{**confirmed_submission.__dict__, 'status': 'finalized'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = finalized
        
        with patch('apps.tournament_ops.services.review_inbox_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            result = service.finalize_submission(submission_id=103, resolved_by_user_id=1)
        
        # Assert
        assert result.status == 'finalized'
        mock_adapters['result_submission_adapter'].update_submission_status.assert_called_once_with(
            submission_id=103,
            status='finalized',
        )
    
    def test_finalize_submission_resolves_dispute_if_exists(
        self, service, mock_adapters, disputed_submission, open_dispute
    ):
        """Test finalize_submission resolves dispute as submitter wins."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = disputed_submission
        mock_adapters['dispute_adapter'].get_open_dispute_for_submission.return_value = open_dispute
        
        resolved_dispute = DisputeDTO(
            **{**open_dispute.__dict__, 'status': 'resolved_for_submitter',
               'resolved_at': datetime.now(timezone.utc), 'resolved_by_user_id': 1}
        )
        mock_adapters['dispute_adapter'].update_dispute_status.return_value = resolved_dispute
        
        finalized = MatchResultSubmissionDTO(
            **{**disputed_submission.__dict__, 'status': 'finalized'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = finalized
        
        with patch('apps.tournament_ops.services.review_inbox_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            service.finalize_submission(submission_id=102, resolved_by_user_id=1)
        
        # Assert
        mock_adapters['dispute_adapter'].update_dispute_status.assert_called_once_with(
            dispute_id=201,
            status='resolved_for_submitter',
            resolved_by_user_id=1,
            resolution_notes='Organizer finalized submission (submitter wins)',
        )
    
    def test_finalize_submission_publishes_match_result_finalized_event(
        self, service, mock_adapters, confirmed_submission
    ):
        """Test MatchResultFinalizedEvent published."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = confirmed_submission
        mock_adapters['dispute_adapter'].get_open_dispute_for_submission.return_value = None
        
        finalized = MatchResultSubmissionDTO(
            **{**confirmed_submission.__dict__, 'status': 'finalized'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = finalized
        
        with patch('apps.tournament_ops.services.review_inbox_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            service.finalize_submission(submission_id=103, resolved_by_user_id=1)
        
        # Assert
        assert mock_bus.publish.call_count >= 1
        event_call = mock_bus.publish.call_args_list[-1][0][0]  # Last event
        assert event_call.name == 'MatchResultFinalizedEvent'
        assert event_call.payload['submission_id'] == 103
        assert event_call.payload['match_id'] == 52
        assert event_call.payload['resolved_by_user_id'] == 1
    
    def test_finalize_submission_logs_verification_step(
        self, service, mock_adapters, confirmed_submission
    ):
        """Test finalize_submission logs organizer_finalized step."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = confirmed_submission
        mock_adapters['dispute_adapter'].get_open_dispute_for_submission.return_value = None
        
        finalized = MatchResultSubmissionDTO(
            **{**confirmed_submission.__dict__, 'status': 'finalized'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = finalized
        
        with patch('apps.tournament_ops.services.review_inbox_service.get_event_bus'):
            # Act
            service.finalize_submission(submission_id=103, resolved_by_user_id=1)
        
        # Assert
        mock_adapters['dispute_adapter'].log_verification_step.assert_called_once()
        call_args = mock_adapters['dispute_adapter'].log_verification_step.call_args
        assert call_args[1]['step'] == 'organizer_finalized'
        assert call_args[1]['submission_id'] == 103
    
    def test_finalize_submission_raises_if_invalid_state(
        self, service, mock_adapters, pending_submission
    ):
        """Test cannot finalize pending submission."""
        # Arrange
        pending = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'pending'}
        )
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending
        
        # Act & Assert
        with pytest.raises(InvalidSubmissionStateError, match='Cannot finalize'):
            service.finalize_submission(submission_id=101, resolved_by_user_id=1)


class TestRejectSubmission:
    """Tests for reject_submission method."""
    
    def test_reject_submission_updates_status_to_rejected(
        self, service, mock_adapters, pending_submission
    ):
        """Test reject_submission updates submission status."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['dispute_adapter'].get_open_dispute_for_submission.return_value = None
        
        rejected = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'rejected'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = rejected
        
        with patch('apps.tournament_ops.services.review_inbox_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            result = service.reject_submission(
                submission_id=101, resolved_by_user_id=1, notes='Invalid proof'
            )
        
        # Assert
        assert result.status == 'rejected'
        mock_adapters['result_submission_adapter'].update_submission_status.assert_called_once_with(
            submission_id=101,
            status='rejected',
        )
    
    def test_reject_submission_resolves_dispute_as_opponent_wins(
        self, service, mock_adapters, disputed_submission, open_dispute
    ):
        """Test reject_submission resolves dispute as opponent wins."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = disputed_submission
        mock_adapters['dispute_adapter'].get_open_dispute_for_submission.return_value = open_dispute
        
        resolved_dispute = DisputeDTO(
            **{**open_dispute.__dict__, 'status': 'resolved_for_opponent',
               'resolved_at': datetime.now(timezone.utc), 'resolved_by_user_id': 1}
        )
        mock_adapters['dispute_adapter'].update_dispute_status.return_value = resolved_dispute
        
        rejected = MatchResultSubmissionDTO(
            **{**disputed_submission.__dict__, 'status': 'rejected'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = rejected
        
        with patch('apps.tournament_ops.services.review_inbox_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            service.reject_submission(
                submission_id=102, resolved_by_user_id=1, notes='Invalid proof'
            )
        
        # Assert
        mock_adapters['dispute_adapter'].update_dispute_status.assert_called_once_with(
            dispute_id=201,
            status='resolved_for_opponent',
            resolved_by_user_id=1,
            resolution_notes='Organizer rejected submission (opponent wins): Invalid proof',
        )
    
    def test_reject_submission_publishes_match_result_rejected_event(
        self, service, mock_adapters, pending_submission
    ):
        """Test MatchResultRejectedEvent published."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['dispute_adapter'].get_open_dispute_for_submission.return_value = None
        
        rejected = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'rejected'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = rejected
        
        with patch('apps.tournament_ops.services.review_inbox_service.get_event_bus') as mock_event_bus:
            mock_bus = Mock()
            mock_event_bus.return_value = mock_bus
            
            # Act
            service.reject_submission(
                submission_id=101, resolved_by_user_id=1, notes='Invalid proof'
            )
        
        # Assert
        assert mock_bus.publish.call_count >= 1
        event_call = mock_bus.publish.call_args_list[-1][0][0]  # Last event
        assert event_call.name == 'MatchResultRejectedEvent'
        assert event_call.payload['submission_id'] == 101
        assert event_call.payload['notes'] == 'Invalid proof'
    
    def test_reject_submission_logs_verification_step(
        self, service, mock_adapters, pending_submission
    ):
        """Test reject_submission logs organizer_rejected step."""
        # Arrange
        mock_adapters['result_submission_adapter'].get_submission.return_value = pending_submission
        mock_adapters['dispute_adapter'].get_open_dispute_for_submission.return_value = None
        
        rejected = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'status': 'rejected'}
        )
        mock_adapters['result_submission_adapter'].update_submission_status.return_value = rejected
        
        with patch('apps.tournament_ops.services.review_inbox_service.get_event_bus'):
            # Act
            service.reject_submission(
                submission_id=101, resolved_by_user_id=1, notes='Invalid proof'
            )
        
        # Assert
        mock_adapters['dispute_adapter'].log_verification_step.assert_called_once()
        call_args = mock_adapters['dispute_adapter'].log_verification_step.call_args
        assert call_args[1]['step'] == 'organizer_rejected'
        assert call_args[1]['details']['notes'] == 'Invalid proof'


class TestListItemsForStage:
    """Tests for list_items_for_stage method."""
    
    def test_list_items_for_stage_filters_by_stage_id(
        self, service, mock_adapters, pending_submission
    ):
        """Test list_items_for_stage filters by stage_id."""
        # Arrange
        stage_10_sub = pending_submission
        stage_20_sub = MatchResultSubmissionDTO(
            **{**pending_submission.__dict__, 'id': 999, 'stage_id': 20}
        )
        
        mock_adapters['review_inbox_adapter'].get_pending_submissions.return_value = [
            stage_10_sub, stage_20_sub
        ]
        mock_adapters['review_inbox_adapter'].get_disputed_submissions.return_value = []
        mock_adapters['review_inbox_adapter'].get_overdue_auto_confirm.return_value = []
        mock_adapters['review_inbox_adapter'].get_ready_for_finalization.return_value = []
        
        # Act
        items = service.list_items_for_stage(stage_id=10)
        
        # Assert
        assert len(items) == 1
        assert items[0].stage_id == 10


class TestArchitectureCompliance:
    """Architecture compliance tests."""
    
    def test_review_inbox_service_never_imports_orm_directly(self):
        """Test ReviewInboxService does not import Django ORM models."""
        import inspect
        from apps.tournament_ops.services.review_inbox_service import ReviewInboxService
        
        source = inspect.getsource(ReviewInboxService)
        
        # Assert: no Django model imports in service class
        assert 'from apps.tournaments.models' not in source
        assert 'from apps.teams.models' not in source
        assert 'from apps.accounts.models' not in source
        
        # All domain access must go through adapters
        assert 'review_inbox_adapter' in source
        assert 'dispute_adapter' in source
        assert 'result_submission_adapter' in source
