"""
Unit Tests for OrganizerReviewItemDTO - Phase 6, Epic 6.3

Tests DTO creation, priority computation, validation, and helper methods.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.3 (Organizer Results Inbox)
"""

import pytest
from datetime import datetime, timedelta, timezone

from apps.tournament_ops.dtos import (
    OrganizerReviewItemDTO,
    MatchResultSubmissionDTO,
    DisputeDTO,
)


@pytest.fixture
def base_submission():
    """Base submission DTO with 24h deadline."""
    now = datetime.now(timezone.utc)
    return MatchResultSubmissionDTO(
        id=101,
        match_id=50,
        tournament_id=1,
        stage_id=10,
        submitted_by_user_id=10,
        submitted_by_team_id=5,
        raw_result_payload={'winner_team_id': 5},
        proof_screenshot_url='https://example.com/proof.png',
        submitter_notes='GG',
        status='pending',
        submitted_at=now - timedelta(hours=6),
        confirmed_at=None,
        confirmed_by_user_id=None,
        auto_confirmed=False,
        auto_confirm_deadline=now + timedelta(hours=18),  # 18h from now (6h elapsed of 24h)
    )


@pytest.fixture
def disputed_submission(base_submission):
    """Disputed submission."""
    return MatchResultSubmissionDTO(
        **{**base_submission.__dict__, 'status': 'disputed'}
    )


@pytest.fixture
def overdue_submission(base_submission):
    """Overdue submission (past deadline)."""
    now = datetime.now(timezone.utc)
    return MatchResultSubmissionDTO(
        **{**base_submission.__dict__, 'auto_confirm_deadline': now - timedelta(hours=2)}
    )


@pytest.fixture
def open_dispute():
    """Open dispute DTO."""
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


class TestOrganizerReviewItemDTOCreation:
    """Tests for DTO creation and from_submission_and_dispute."""
    
    def test_from_submission_and_dispute_creates_item_with_all_fields(
        self, base_submission, open_dispute
    ):
        """Test DTO creation from submission and dispute."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(
            base_submission, open_dispute
        )
        
        # Assert
        assert item.submission_id == 101
        assert item.match_id == 50
        assert item.tournament_id == 1
        assert item.stage_id == 10
        assert item.submitted_by_user_id == 10
        assert item.status == 'pending'
        assert item.dispute_id == 201
        assert item.dispute_status == 'open'
        assert item.opened_at == open_dispute.opened_at
        assert item.is_overdue is False
        assert item.priority > 0
    
    def test_from_submission_without_dispute_sets_dispute_fields_none(
        self, base_submission
    ):
        """Test DTO creation without dispute."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(base_submission, None)
        
        # Assert
        assert item.dispute_id is None
        assert item.dispute_status is None
        assert item.opened_at is None
    
    def test_from_submission_detects_overdue_correctly(self, overdue_submission):
        """Test is_overdue flag set correctly for past deadline."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(overdue_submission, None)
        
        # Assert
        assert item.is_overdue is True
    
    def test_from_submission_detects_not_overdue_correctly(self, base_submission):
        """Test is_overdue flag set correctly for future deadline."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(base_submission, None)
        
        # Assert
        assert item.is_overdue is False


class TestPriorityComputation:
    """Tests for compute_priority method."""
    
    def test_disputed_submissions_have_highest_priority(self, disputed_submission, open_dispute):
        """Test disputed items get priority 1 (highest)."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(
            disputed_submission, open_dispute
        )
        
        # Assert
        assert item.priority == 1
    
    def test_overdue_auto_confirm_has_high_priority(self, overdue_submission):
        """Test overdue items get priority 2 (high)."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(overdue_submission, None)
        
        # Assert
        assert item.priority == 2
    
    def test_pending_over_12h_has_medium_priority(self):
        """Test pending >12h gets priority 3 (medium)."""
        # Create submission with deadline in 10h (meaning 14h elapsed of 24h)
        now = datetime.now(timezone.utc)
        submission = MatchResultSubmissionDTO(
            id=101, match_id=50, tournament_id=1, stage_id=10,
            submitted_by_user_id=10, submitted_by_team_id=5,
            raw_result_payload={}, proof_screenshot_url=None, submitter_notes='',
            status='pending',
            submitted_at=now - timedelta(hours=14),
            confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
            auto_confirm_deadline=now + timedelta(hours=10),  # 10h left of 24h = 14h elapsed
        )
        
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(submission, None)
        
        # Assert
        assert item.priority == 3
    
    def test_recent_pending_has_low_priority(self):
        """Test recent pending gets priority 4 (low)."""
        # Create submission with deadline in 20h (meaning 4h elapsed of 24h)
        now = datetime.now(timezone.utc)
        submission = MatchResultSubmissionDTO(
            id=101, match_id=50, tournament_id=1, stage_id=10,
            submitted_by_user_id=10, submitted_by_team_id=5,
            raw_result_payload={}, proof_screenshot_url=None, submitter_notes='',
            status='pending',
            submitted_at=now - timedelta(hours=4),
            confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
            auto_confirm_deadline=now + timedelta(hours=20),  # 20h left of 24h = 4h elapsed
        )
        
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(submission, None)
        
        # Assert
        assert item.priority == 4
    
    def test_confirmed_submissions_have_low_priority(self):
        """Test confirmed (ready for finalization) gets priority 4 (low)."""
        now = datetime.now(timezone.utc)
        submission = MatchResultSubmissionDTO(
            id=101, match_id=50, tournament_id=1, stage_id=10,
            submitted_by_user_id=10, submitted_by_team_id=5,
            raw_result_payload={}, proof_screenshot_url=None, submitter_notes='',
            status='confirmed',
            submitted_at=now - timedelta(hours=6),
            confirmed_at=now - timedelta(hours=2),
            confirmed_by_user_id=20, auto_confirmed=False,
            auto_confirm_deadline=now + timedelta(hours=18),
        )
        
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(submission, None)
        
        # Assert
        assert item.priority == 4


class TestSorting:
    """Tests for sorting review items by priority and deadline."""
    
    def test_items_sort_by_priority_then_deadline(self):
        """Test items sort by priority (asc) then deadline (asc)."""
        now = datetime.now(timezone.utc)
        
        # Create 4 items with different priorities
        disputed = MatchResultSubmissionDTO(
            id=1, match_id=1, tournament_id=1, stage_id=1,
            submitted_by_user_id=1, submitted_by_team_id=1,
            raw_result_payload={}, proof_screenshot_url=None, submitter_notes='',
            status='disputed',
            submitted_at=now - timedelta(hours=10),
            confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
            auto_confirm_deadline=now + timedelta(hours=14),
        )
        
        overdue = MatchResultSubmissionDTO(
            id=2, match_id=2, tournament_id=1, stage_id=1,
            submitted_by_user_id=1, submitted_by_team_id=1,
            raw_result_payload={}, proof_screenshot_url=None, submitter_notes='',
            status='pending',
            submitted_at=now - timedelta(hours=26),
            confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
            auto_confirm_deadline=now - timedelta(hours=2),  # Overdue
        )
        
        pending_old = MatchResultSubmissionDTO(
            id=3, match_id=3, tournament_id=1, stage_id=1,
            submitted_by_user_id=1, submitted_by_team_id=1,
            raw_result_payload={}, proof_screenshot_url=None, submitter_notes='',
            status='pending',
            submitted_at=now - timedelta(hours=14),
            confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
            auto_confirm_deadline=now + timedelta(hours=10),
        )
        
        pending_new = MatchResultSubmissionDTO(
            id=4, match_id=4, tournament_id=1, stage_id=1,
            submitted_by_user_id=1, submitted_by_team_id=1,
            raw_result_payload={}, proof_screenshot_url=None, submitter_notes='',
            status='pending',
            submitted_at=now - timedelta(hours=4),
            confirmed_at=None, confirmed_by_user_id=None, auto_confirmed=False,
            auto_confirm_deadline=now + timedelta(hours=20),
        )
        
        dispute_dto = DisputeDTO(
            id=201, submission_id=1, opened_by_user_id=20, opened_by_team_id=6,
            reason_code='incorrect_score', description='Wrong', status='open',
            resolution_notes=None,
            opened_at=now - timedelta(hours=10),
            updated_at=now - timedelta(hours=10),
            resolved_at=None, resolved_by_user_id=None, escalated_at=None,
        )
        
        # Create items
        items = [
            OrganizerReviewItemDTO.from_submission_and_dispute(disputed, dispute_dto),
            OrganizerReviewItemDTO.from_submission_and_dispute(overdue, None),
            OrganizerReviewItemDTO.from_submission_and_dispute(pending_old, None),
            OrganizerReviewItemDTO.from_submission_and_dispute(pending_new, None),
        ]
        
        # Sort by priority (asc) then deadline (asc)
        items.sort(key=lambda x: (x.priority, x.auto_confirm_deadline))
        
        # Assert
        assert items[0].submission_id == 1  # disputed (priority 1)
        assert items[1].submission_id == 2  # overdue (priority 2)
        assert items[2].submission_id == 3  # pending old (priority 3)
        assert items[3].submission_id == 4  # pending new (priority 4)


class TestValidation:
    """Tests for validate method."""
    
    def test_validate_passes_for_valid_item(self, base_submission):
        """Test validation passes for valid item."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(base_submission, None)
        
        # Assert
        assert item.validate() is True
    
    def test_validate_raises_for_invalid_priority(self, base_submission):
        """Test validation fails for invalid priority."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(base_submission, None)
        item.priority = 5  # Invalid (must be 1-4)
        
        # Assert
        with pytest.raises(ValueError, match='Invalid priority'):
            item.validate()
    
    def test_validate_raises_for_invalid_status(self, base_submission):
        """Test validation fails for invalid status."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(base_submission, None)
        item.status = 'invalid_status'
        
        # Assert
        with pytest.raises(ValueError, match='Invalid status'):
            item.validate()
    
    def test_validate_raises_if_dispute_id_set_without_status(self, base_submission):
        """Test validation fails if dispute_id set but dispute_status is None."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(base_submission, None)
        item.dispute_id = 201
        item.dispute_status = None
        
        # Assert
        with pytest.raises(ValueError, match='dispute_status required'):
            item.validate()
    
    def test_validate_raises_for_invalid_dispute_status(self, base_submission, open_dispute):
        """Test validation fails for invalid dispute_status."""
        # Act
        item = OrganizerReviewItemDTO.from_submission_and_dispute(base_submission, open_dispute)
        item.dispute_status = 'invalid_status'
        
        # Assert
        with pytest.raises(ValueError, match='Invalid dispute_status'):
            item.validate()
