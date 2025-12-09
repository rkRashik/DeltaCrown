"""
Epic 7.1: Multi-Tournament Results Inbox Unit Tests

Comprehensive test suite for multi-tournament results inbox features.

Test Coverage:
- list_review_items_for_organizer() - 6 tests
- bulk_finalize_submissions() - 3 tests
- bulk_reject_submissions() - 3 tests
- TournamentOpsService façade delegation - 2 tests

Total: 14 tests (all using mocks, no ORM)

Reference: ROADMAP_AND_EPICS_PART_4.md - Epic 7.1, Results Inbox & Queue Management
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from apps.tournament_ops.services.review_inbox_service import ReviewInboxService
from apps.tournament_ops.services.tournament_ops_service import TournamentOpsService
from apps.tournament_ops.dtos import (
    OrganizerReviewItemDTO,
    OrganizerInboxFilterDTO,
    MatchResultSubmissionDTO,
)


class TestReviewInboxServiceMultiTournament:
    """Test suite for multi-tournament results inbox features."""

    @pytest.fixture
    def mock_review_inbox_adapter(self):
        """Mock ReviewInboxAdapterProtocol."""
        return Mock()

    @pytest.fixture
    def mock_dispute_adapter(self):
        """Mock DisputeAdapterProtocol."""
        return Mock()

    @pytest.fixture
    def mock_result_submission_adapter(self):
        """Mock ResultSubmissionAdapterProtocol."""
        return Mock()

    @pytest.fixture
    def mock_result_verification_service(self):
        """Mock ResultVerificationService."""
        return Mock()

    @pytest.fixture
    def mock_match_service(self):
        """Mock MatchService."""
        return Mock()

    @pytest.fixture
    def service(
        self,
        mock_review_inbox_adapter,
        mock_dispute_adapter,
        mock_result_submission_adapter,
        mock_result_verification_service,
        mock_match_service,
    ):
        """Create ReviewInboxService with mocked dependencies."""
        return ReviewInboxService(
            review_inbox_adapter=mock_review_inbox_adapter,
            dispute_adapter=mock_dispute_adapter,
            result_submission_adapter=mock_result_submission_adapter,
            match_service=mock_match_service,
            result_verification_service=mock_result_verification_service,
        )

    @pytest.fixture
    def sample_submissions(self):
        """Sample MatchResultSubmissionDTO list for adapter mocking."""
        now = datetime.now(timezone.utc)
        return [
            MatchResultSubmissionDTO(
                id=101,
                match_id=201,
                tournament_id=1,
                stage_id=None,
                submitted_by_user_id=100,
                submitted_by_team_id=5,
                raw_result_payload={'winner_team_id': 5, 'score': '2-0'},
                proof_screenshot_url='https://example.com/proof1.jpg',
                status='pending',
                submitted_at=now - timedelta(hours=12),
                confirmed_at=None,
                finalized_at=None,
                auto_confirm_deadline=now + timedelta(hours=12),
                confirmed_by_user_id=None,
                submitter_notes='',
                organizer_notes='',
            ),
            MatchResultSubmissionDTO(
                id=102,
                match_id=202,
                tournament_id=2,
                stage_id=None,
                submitted_by_user_id=101,
                submitted_by_team_id=6,
                raw_result_payload={'winner_team_id': 6, 'score': '2-1'},
                proof_screenshot_url='https://example.com/proof2.jpg',
                status='disputed',
                submitted_at=now - timedelta(hours=48),
                confirmed_at=None,
                finalized_at=None,
                auto_confirm_deadline=now - timedelta(hours=24),
                confirmed_by_user_id=None,
                submitter_notes='',
                organizer_notes='',
            ),
            MatchResultSubmissionDTO(
                id=103,
                match_id=203,
                tournament_id=1,
                stage_id=None,
                submitted_by_user_id=100,
                submitted_by_team_id=5,
                raw_result_payload={'winner_team_id': 5, 'score': '2-0'},
                proof_screenshot_url='https://example.com/proof3.jpg',
                status='pending',
                submitted_at=now - timedelta(hours=6),
                confirmed_at=None,
                finalized_at=None,
                auto_confirm_deadline=now + timedelta(hours=18),
                confirmed_by_user_id=None,
                submitter_notes='',
                organizer_notes='',
            ),
        ]

    @pytest.fixture
    def sample_review_items(self):
        """Sample OrganizerReviewItemDTO list for testing bulk actions."""
        now = datetime.now(timezone.utc)
        return [
            OrganizerReviewItemDTO(
                submission_id=101,
                match_id=201,
                tournament_id=1,
                tournament_name='Summer Championship 2025',
                stage_id=None,
                submitted_by_user_id=100,
                status='pending',
                dispute_id=None,
                dispute_status=None,
                created_at=now - timedelta(hours=12),
                auto_confirm_deadline=now + timedelta(hours=12),
                opened_at=None,
                is_overdue=False,
                priority=85,
            ),
            OrganizerReviewItemDTO(
                submission_id=102,
                match_id=202,
                tournament_id=2,
                tournament_name='Winter League 2025',
                stage_id=None,
                submitted_by_user_id=101,
                status='disputed',
                dispute_id=501,
                dispute_status='open',
                created_at=now - timedelta(hours=48),
                auto_confirm_deadline=now - timedelta(hours=24),
                opened_at=now - timedelta(hours=48),
                is_overdue=True,
                priority=95,
            ),
            OrganizerReviewItemDTO(
                submission_id=103,
                match_id=203,
                tournament_id=1,
                tournament_name='Summer Championship 2025',
                stage_id=None,
                submitted_by_user_id=100,
                status='pending',
                dispute_id=None,
                dispute_status=None,
                created_at=now - timedelta(hours=6),
                auto_confirm_deadline=now + timedelta(hours=18),
                opened_at=None,
                is_overdue=False,
                priority=70,
            ),
        ]

    # =========================================================================
    # list_review_items_for_organizer() tests
    # =========================================================================

    def test_list_review_items_for_organizer_returns_items_from_multiple_tournaments(
        self,
        service,
        mock_review_inbox_adapter,
        mock_dispute_adapter,
        sample_submissions,
    ):
        """Test that list_review_items_for_organizer returns items across multiple tournaments."""
        # Arrange
        organizer_user_id = 42
        filters = {}
        
        # Mock adapter returns submissions from multiple tournaments
        mock_review_inbox_adapter.get_review_items_by_filters.return_value = sample_submissions
        mock_dispute_adapter.get_open_dispute_for_submission.return_value = None

        # Mock _get_tournament_name to return tournament names
        with patch.object(service, '_get_tournament_name') as mock_get_tournament_name:
            mock_get_tournament_name.side_effect = lambda tid: f'Tournament {tid}'
            
            # Act
            result = service.list_review_items_for_organizer(
                organizer_user_id=organizer_user_id,
                filters=filters
            )

        # Assert
        assert len(result) == 3
        # Verify items from both tournaments are present
        tournament_ids = {item.tournament_id for item in result}
        assert tournament_ids == {1, 2}
        
        # Verify adapter was called with correct filter
        call_args = mock_review_inbox_adapter.get_review_items_by_filters.call_args
        filter_dto = call_args[0][0]
        assert isinstance(filter_dto, OrganizerInboxFilterDTO)
        assert filter_dto.organizer_user_id == organizer_user_id

    def test_list_review_items_for_organizer_filters_by_tournament_id(
        self,
        service,
        mock_review_inbox_adapter,
        mock_dispute_adapter,
        sample_submissions,
    ):
        """Test filtering items by tournament_id."""
        # Arrange
        organizer_user_id = 42
        filters = {'tournament_id': 1}
        
        # Filter items to only tournament 1
        filtered_items = [item for item in sample_submissions if item.tournament_id == 1]
        mock_review_inbox_adapter.get_review_items_by_filters.return_value = filtered_items
        mock_dispute_adapter.get_open_dispute_for_submission.return_value = None

        # Mock _get_tournament_name
        with patch.object(service, '_get_tournament_name') as mock_get_tournament_name:
            mock_get_tournament_name.return_value = 'Tournament 1'
            
            # Act
            result = service.list_review_items_for_organizer(
                organizer_user_id=organizer_user_id,
                filters=filters
            )

        # Assert
        assert len(result) == 2
        assert all(item.tournament_id == 1 for item in result)
        
        # Verify filter was passed to adapter
        call_args = mock_review_inbox_adapter.get_review_items_by_filters.call_args
        filter_dto = call_args[0][0]
        assert filter_dto.tournament_id == 1

    def test_list_review_items_for_organizer_filters_by_status(
        self,
        service,
        mock_review_inbox_adapter,
        mock_dispute_adapter,
        sample_submissions,
    ):
        """Test filtering items by status."""
        # Arrange
        organizer_user_id = 42
        filters = {'status': ['pending']}
        
        # Filter items to only pending status
        filtered_items = [item for item in sample_submissions if item.status == 'pending']
        mock_review_inbox_adapter.get_review_items_by_filters.return_value = filtered_items
        mock_dispute_adapter.get_open_dispute_for_submission.return_value = None

        # Mock _get_tournament_name
        with patch.object(service, '_get_tournament_name') as mock_get_tournament_name:
            mock_get_tournament_name.return_value = 'Tournament 1'
            
            # Act
            result = service.list_review_items_for_organizer(
                organizer_user_id=organizer_user_id,
                filters=filters
            )

        # Assert
        assert len(result) == 2
        assert all(item.status == 'pending' for item in result)
        
        # Verify filter was passed to adapter
        call_args = mock_review_inbox_adapter.get_review_items_by_filters.call_args
        filter_dto = call_args[0][0]
        assert filter_dto.status == ['pending']

    def test_list_review_items_for_organizer_applies_date_range_filter(
        self,
        service,
        mock_review_inbox_adapter,
        mock_dispute_adapter,
        sample_submissions,
    ):
        """Test filtering items by date range."""
        # Arrange
        organizer_user_id = 42
        now = datetime.now(timezone.utc)
        date_from = now - timedelta(hours=24)
        date_to = now
        filters = {
            'date_from': date_from,
            'date_to': date_to,
        }
        
        # Filter items within date range
        filtered_items = [
            item for item in sample_submissions
            if date_from <= item.submitted_at <= date_to
        ]
        mock_review_inbox_adapter.get_review_items_by_filters.return_value = filtered_items
        mock_dispute_adapter.get_open_dispute_for_submission.return_value = None

        # Mock _get_tournament_name
        with patch.object(service, '_get_tournament_name') as mock_get_tournament_name:
            mock_get_tournament_name.return_value = 'Tournament 1'
            
            # Act
            result = service.list_review_items_for_organizer(
                organizer_user_id=organizer_user_id,
                filters=filters
            )

        # Assert
        assert len(result) == 2  # Only items within 24 hours
        
        # Verify filter was passed to adapter
        call_args = mock_review_inbox_adapter.get_review_items_by_filters.call_args
        filter_dto = call_args[0][0]
        assert filter_dto.date_from == date_from
        assert filter_dto.date_to == date_to

    def test_list_review_items_includes_tournament_name_when_available(
        self,
        service,
        mock_review_inbox_adapter,
        mock_dispute_adapter,
        sample_submissions,
    ):
        """Test that tournament names are included in results."""
        # Arrange
        organizer_user_id = 42
        filters = {}
        
        mock_review_inbox_adapter.get_review_items_by_filters.return_value = sample_submissions
        mock_dispute_adapter.get_open_dispute_for_submission.return_value = None

        # Mock _get_tournament_name to return specific names
        with patch.object(service, '_get_tournament_name') as mock_get_tournament_name:
            def get_name(tid):
                return 'Summer Championship 2025' if tid == 1 else 'Winter League 2025'
            mock_get_tournament_name.side_effect = get_name
            
            # Act
            result = service.list_review_items_for_organizer(
                organizer_user_id=organizer_user_id,
                filters=filters
            )

        # Assert
        assert all(item.tournament_name is not None for item in result)
        # Results are sorted by priority, so disputed item (tournament 2) comes first
        assert any(item.tournament_name == 'Summer Championship 2025' for item in result)
        assert any(item.tournament_name == 'Winter League 2025' for item in result)

    def test_list_review_items_orders_by_priority_then_age(
        self,
        service,
        mock_review_inbox_adapter,
        mock_dispute_adapter,
        sample_submissions,
    ):
        """Test that items are ordered by priority (ascending) then age (descending)."""
        # Arrange
        organizer_user_id = 42
        filters = {}
        
        # Return items in random order
        unordered_items = [sample_submissions[2], sample_submissions[0], sample_submissions[1]]
        mock_review_inbox_adapter.get_review_items_by_filters.return_value = unordered_items
        mock_dispute_adapter.get_open_dispute_for_submission.return_value = None

        # Mock _get_tournament_name and get_open_dispute_for_submission
        with patch.object(service, '_get_tournament_name') as mock_get_tournament_name:
            mock_get_tournament_name.return_value = 'Test Tournament'
            # Mock dispute for the disputed submission
            def get_dispute(sub_id):
                if sub_id == 102:
                    from apps.tournament_ops.dtos import DisputeDTO
                    return DisputeDTO(
                        id=501,
                        submission_id=102,
                        raised_by_user_id=101,
                        status='open',
                        opened_at=datetime.now(timezone.utc) - timedelta(hours=48),
                        resolved_at=None,
                        resolution_notes='',
                    )
                return None
            mock_dispute_adapter.get_open_dispute_for_submission.side_effect = get_dispute
            
            # Act
            result = service.list_review_items_for_organizer(
                organizer_user_id=organizer_user_id,
                filters=filters
            )

        # Assert
        # Should be ordered by priority (1=highest disputed, 2=overdue, 3/4=pending)
        # Disputed item should come first (priority 1)
        assert result[0].status == 'disputed'
        assert result[0].priority == 1
        # Then overdue pending items (priority 2)
        # Then recent pending items (priority 3 or 4)
        assert all(result[i].priority <= result[i+1].priority for i in range(len(result)-1))

    # =========================================================================
    # bulk_finalize_submissions() tests
    # =========================================================================

    def test_bulk_finalize_submissions_calls_finalize_for_each_submission_id(
        self,
        service,
        sample_review_items,
    ):
        """Test that bulk_finalize_submissions calls finalize_submission for each ID."""
        # Arrange
        submission_ids = [101, 102]
        resolved_by_user_id = 42
        
        # Mock finalize_submission to return DTOs
        with patch.object(service, 'finalize_submission') as mock_finalize:
            mock_finalize.side_effect = [
                sample_review_items[0],
                sample_review_items[1],
            ]

            # Act
            result = service.bulk_finalize_submissions(
                submission_ids=submission_ids,
                resolved_by_user_id=resolved_by_user_id
            )

        # Assert
        assert mock_finalize.call_count == 2
        assert result['processed'] == 2
        assert len(result['items']) == 2
        assert len(result['failed']) == 0

    def test_bulk_finalize_submissions_collects_successes_and_failures(
        self,
        service,
        sample_review_items,
    ):
        """Test that bulk_finalize_submissions collects both successes and failures."""
        # Arrange
        submission_ids = [101, 102, 103]
        resolved_by_user_id = 42
        
        # Mock finalize_submission: first succeeds, second fails, third succeeds
        with patch.object(service, 'finalize_submission') as mock_finalize:
            mock_finalize.side_effect = [
                sample_review_items[0],
                Exception("Submission 102 not found"),
                sample_review_items[2],
            ]

            # Act
            result = service.bulk_finalize_submissions(
                submission_ids=submission_ids,
                resolved_by_user_id=resolved_by_user_id
            )

        # Assert
        assert result['processed'] == 2  # 2 successes
        assert len(result['items']) == 2
        assert len(result['failed']) == 1
        assert result['failed'][0]['submission_id'] == 102
        assert 'not found' in result['failed'][0]['error']

    def test_bulk_finalize_submissions_passes_resolved_by_user_id(
        self,
        service,
        sample_review_items,
    ):
        """Test that resolved_by_user_id is passed to finalize_submission."""
        # Arrange
        submission_ids = [101]
        resolved_by_user_id = 42
        
        with patch.object(service, 'finalize_submission') as mock_finalize:
            mock_finalize.return_value = sample_review_items[0]

            # Act
            service.bulk_finalize_submissions(
                submission_ids=submission_ids,
                resolved_by_user_id=resolved_by_user_id
            )

        # Assert
        mock_finalize.assert_called_once_with(101, 42)

    # =========================================================================
    # bulk_reject_submissions() tests
    # =========================================================================

    def test_bulk_reject_submissions_calls_reject_for_each_submission_id(
        self,
        service,
        sample_review_items,
    ):
        """Test that bulk_reject_submissions calls reject_submission for each ID."""
        # Arrange
        submission_ids = [101, 102]
        resolved_by_user_id = 42
        notes = 'Invalid proof'
        
        # Mock reject_submission to return DTOs
        with patch.object(service, 'reject_submission') as mock_reject:
            mock_reject.side_effect = [
                sample_review_items[0],
                sample_review_items[1],
            ]

            # Act
            result = service.bulk_reject_submissions(
                submission_ids=submission_ids,
                resolved_by_user_id=resolved_by_user_id,
                notes=notes
            )

        # Assert
        assert mock_reject.call_count == 2
        assert result['processed'] == 2
        assert len(result['items']) == 2
        assert len(result['failed']) == 0

    def test_bulk_reject_submissions_passes_notes_to_service(
        self,
        service,
        sample_review_items,
    ):
        """Test that notes are passed to reject_submission."""
        # Arrange
        submission_ids = [101]
        resolved_by_user_id = 42
        notes = 'Invalid proof screenshot'
        
        with patch.object(service, 'reject_submission') as mock_reject:
            mock_reject.return_value = sample_review_items[0]

            # Act
            service.bulk_reject_submissions(
                submission_ids=submission_ids,
                resolved_by_user_id=resolved_by_user_id,
                notes=notes
            )

        # Assert
        mock_reject.assert_called_once_with(101, 42, 'Invalid proof screenshot')

    def test_bulk_reject_submissions_collects_failures(
        self,
        service,
        sample_review_items,
    ):
        """Test that bulk_reject_submissions collects failures."""
        # Arrange
        submission_ids = [101, 102]
        resolved_by_user_id = 42
        notes = 'Invalid proof'
        
        # Mock reject_submission: first succeeds, second fails
        with patch.object(service, 'reject_submission') as mock_reject:
            mock_reject.side_effect = [
                sample_review_items[0],
                Exception("Submission 102 already finalized"),
            ]

            # Act
            result = service.bulk_reject_submissions(
                submission_ids=submission_ids,
                resolved_by_user_id=resolved_by_user_id,
                notes=notes
            )

        # Assert
        assert result['processed'] == 1
        assert len(result['items']) == 1
        assert len(result['failed']) == 1
        assert result['failed'][0]['submission_id'] == 102
        assert 'already finalized' in result['failed'][0]['error']


class TestTournamentOpsServiceFacade:
    """Test suite for TournamentOpsService façade delegation to ReviewInboxService."""

    @pytest.fixture
    def mock_review_inbox_service(self):
        """Mock ReviewInboxService."""
        return Mock()

    @pytest.fixture
    def tournament_ops_service(self, mock_review_inbox_service):
        """Create TournamentOpsService with mocked ReviewInboxService."""
        service = TournamentOpsService()
        # Replace the lazy-initialized review_inbox_service with our mock
        service._review_inbox_service = mock_review_inbox_service
        return service

    def test_list_results_inbox_for_organizer_facade_delegates_to_review_inbox_service(
        self,
        tournament_ops_service,
        mock_review_inbox_service,
    ):
        """Test that list_results_inbox_for_organizer delegates to ReviewInboxService."""
        # Arrange
        organizer_user_id = 42
        filters = {'tournament_id': 1}
        expected_items = [Mock(), Mock()]
        
        mock_review_inbox_service.list_review_items_for_organizer.return_value = expected_items

        # Act
        result = tournament_ops_service.list_results_inbox_for_organizer(
            organizer_user_id=organizer_user_id,
            filters=filters
        )

        # Assert
        mock_review_inbox_service.list_review_items_for_organizer.assert_called_once_with(
            organizer_user_id=organizer_user_id,
            filters=filters
        )
        assert result == expected_items

    def test_bulk_actions_facade_delegate_to_review_inbox_service(
        self,
        tournament_ops_service,
        mock_review_inbox_service,
    ):
        """Test that bulk action façades delegate to ReviewInboxService."""
        # Arrange
        submission_ids = [101, 102]
        resolved_by_user_id = 42
        notes = 'Invalid proof'
        
        mock_review_inbox_service.bulk_finalize_submissions.return_value = {
            'processed': 2, 'failed': [], 'items': []
        }
        mock_review_inbox_service.bulk_reject_submissions.return_value = {
            'processed': 2, 'failed': [], 'items': []
        }

        # Act - bulk_finalize_submissions
        result_finalize = tournament_ops_service.bulk_finalize_submissions(
            submission_ids=submission_ids,
            resolved_by_user_id=resolved_by_user_id
        )

        # Assert - bulk_finalize_submissions
        mock_review_inbox_service.bulk_finalize_submissions.assert_called_once_with(
            submission_ids=submission_ids,
            resolved_by_user_id=resolved_by_user_id
        )
        assert result_finalize['processed'] == 2

        # Act - bulk_reject_submissions
        result_reject = tournament_ops_service.bulk_reject_submissions(
            submission_ids=submission_ids,
            resolved_by_user_id=resolved_by_user_id,
            notes=notes
        )

        # Assert - bulk_reject_submissions
        mock_review_inbox_service.bulk_reject_submissions.assert_called_once_with(
            submission_ids=submission_ids,
            resolved_by_user_id=resolved_by_user_id,
            notes=notes
        )
        assert result_reject['processed'] == 2
