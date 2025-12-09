"""
Result Submission Service Unit Tests - Phase 6, Epic 6.1

Comprehensive test suite for ResultSubmissionService using mocked adapters.

Test Coverage:
- submit_result() - 5 tests
- confirm_result() - 4 tests
- auto_confirm_result() - 4 tests
- Helper methods - 2 tests
- Architecture guards - 1 test

Total: 16 tests (all using mocks, no ORM)

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.1, Testing Strategy
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from apps.tournament_ops.services.result_submission_service import ResultSubmissionService
from apps.tournament_ops.dtos import (
    MatchResultSubmissionDTO,
    ResultVerificationResultDTO,
    MatchDTO,
)
from apps.tournament_ops.exceptions import (
    ResultSubmissionError,
    InvalidSubmissionStateError,
    PermissionDeniedError,
    InvalidMatchStateError,
)


class TestResultSubmissionService:
    """Test suite for ResultSubmissionService."""

    @pytest.fixture
    def mock_result_submission_adapter(self):
        """Mock ResultSubmissionAdapterProtocol."""
        return Mock()

    @pytest.fixture
    def mock_schema_validation_adapter(self):
        """Mock SchemaValidationAdapterProtocol."""
        return Mock()

    @pytest.fixture
    def mock_match_adapter(self):
        """Mock MatchAdapterProtocol."""
        return Mock()

    @pytest.fixture
    def mock_game_adapter(self):
        """Mock GameAdapterProtocol."""
        return Mock()

    @pytest.fixture
    def service(
        self,
        mock_result_submission_adapter,
        mock_schema_validation_adapter,
        mock_match_adapter,
        mock_game_adapter,
    ):
        """Create ResultSubmissionService with mocked dependencies."""
        return ResultSubmissionService(
            result_submission_adapter=mock_result_submission_adapter,
            schema_validation_adapter=mock_schema_validation_adapter,
            match_adapter=mock_match_adapter,
            game_adapter=mock_game_adapter,
        )

    @pytest.fixture
    def sample_match_dto(self):
        """Sample MatchDTO for testing."""
        return MatchDTO(
            id=101,
            tournament_id=1,
            team_a_id=5,
            team_b_id=6,
            round_number=1,
            stage='round_1',
            state='live',
            scheduled_time=None,
            result={'game_slug': 'valorant'},
        )

    @pytest.fixture
    def sample_submission_dto(self):
        """Sample MatchResultSubmissionDTO for testing."""
        return MatchResultSubmissionDTO(
            id=1001,
            match_id=101,
            submitted_by_user_id=100,
            submitted_by_team_id=5,
            raw_result_payload={
                'winner_team_id': 5,
                'loser_team_id': 6,
                'score': '13-7',
                'map': 'Haven',
            },
            proof_screenshot_url='https://imgur.com/abc123',
            status='pending',
            submitted_at=datetime.now(),
            confirmed_at=None,
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=None,
            submitter_notes='GG WP',
            organizer_notes='',
        )

    # =========================================================================
    # submit_result() tests
    # =========================================================================

    @patch('apps.tournament_ops.services.result_submission_service.get_event_bus')
    @patch('apps.tournament_ops.tasks_result_submission.auto_confirm_submission_task')
    def test_submit_result_creates_submission_and_publishes_event(
        self,
        mock_celery_task,
        mock_event_bus_func,
        service,
        mock_result_submission_adapter,
        mock_schema_validation_adapter,
        mock_match_adapter,
        sample_match_dto,
        sample_submission_dto,
    ):
        """Test submit_result creates submission and publishes MatchResultSubmittedEvent."""
        # Arrange
        mock_match_adapter.get_match.return_value = sample_match_dto
        mock_schema_validation_adapter.validate_payload.return_value = ResultVerificationResultDTO.create_valid()
        mock_result_submission_adapter.create_submission.return_value = sample_submission_dto
        
        mock_event_bus = Mock()
        mock_event_bus_func.return_value = mock_event_bus
        
        mock_celery_task.apply_async = Mock()

        # Act
        result = service.submit_result(
            match_id=101,
            submitted_by_user_id=100,
            submitted_by_team_id=5,
            raw_result_payload={'winner_team_id': 5, 'loser_team_id': 6, 'score': '13-7'},
            proof_screenshot_url='https://imgur.com/abc123',
            submitter_notes='GG WP',
        )

        # Assert
        assert result.id == 1001
        assert result.match_id == 101
        assert result.status == 'pending'
        
        # Verify adapter was called
        mock_result_submission_adapter.create_submission.assert_called_once()
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.name == 'MatchResultSubmittedEvent'
        assert event.payload['match_id'] == 101
        assert event.payload['submission_id'] == 1001
        
        # Verify Celery task was scheduled
        mock_celery_task.apply_async.assert_called_once()

    def test_submit_result_raises_when_match_invalid_state(
        self,
        service,
        mock_match_adapter,
        sample_match_dto,
    ):
        """Test submit_result raises InvalidMatchStateError when match not in valid state."""
        # Arrange
        sample_match_dto.state = 'completed'  # Invalid state
        mock_match_adapter.get_match.return_value = sample_match_dto

        # Act & Assert
        with pytest.raises(InvalidMatchStateError, match='Cannot submit result for match in state: completed'):
            service.submit_result(
                match_id=101,
                submitted_by_user_id=100,
                submitted_by_team_id=5,
                raw_result_payload={'winner_team_id': 5, 'loser_team_id': 6},
            )

    def test_submit_result_raises_when_user_not_participant(
        self,
        service,
        mock_match_adapter,
        sample_match_dto,
    ):
        """Test submit_result raises PermissionDeniedError when user not match participant."""
        # Arrange
        mock_match_adapter.get_match.return_value = sample_match_dto

        # Act & Assert
        with pytest.raises(PermissionDeniedError, match='Team 99 is not a participant'):
            service.submit_result(
                match_id=101,
                submitted_by_user_id=100,
                submitted_by_team_id=99,  # Not in match (5 or 6)
                raw_result_payload={'winner_team_id': 5, 'loser_team_id': 6},
            )

    def test_submit_result_calls_schema_validation_and_raises_on_invalid_payload(
        self,
        service,
        mock_result_submission_adapter,
        mock_schema_validation_adapter,
        mock_match_adapter,
        sample_match_dto,
    ):
        """Test submit_result calls schema validation and raises on invalid payload."""
        # Arrange
        mock_match_adapter.get_match.return_value = sample_match_dto
        mock_schema_validation_adapter.validate_payload.return_value = ResultVerificationResultDTO.create_invalid(
            errors=['Missing required field: winner_team_id']
        )

        # Act & Assert
        with pytest.raises(ResultSubmissionError, match='Invalid result payload'):
            service.submit_result(
                match_id=101,
                submitted_by_user_id=100,
                submitted_by_team_id=5,
                raw_result_payload={'loser_team_id': 6},  # Missing winner_team_id
            )

        # Verify schema validation was called
        mock_schema_validation_adapter.validate_payload.assert_called_once_with(
            'valorant',
            {'loser_team_id': 6}
        )

    @patch('apps.tournament_ops.services.result_submission_service.get_event_bus')
    @patch('apps.tournament_ops.tasks_result_submission.auto_confirm_submission_task')
    def test_submit_result_schedules_auto_confirm_task(
        self,
        mock_celery_task,
        mock_event_bus_func,
        service,
        mock_result_submission_adapter,
        mock_schema_validation_adapter,
        mock_match_adapter,
        sample_match_dto,
        sample_submission_dto,
    ):
        """Test submit_result schedules Celery auto-confirm task."""
        # Arrange
        mock_match_adapter.get_match.return_value = sample_match_dto
        mock_schema_validation_adapter.validate_payload.return_value = ResultVerificationResultDTO.create_valid()
        mock_result_submission_adapter.create_submission.return_value = sample_submission_dto
        
        mock_event_bus = Mock()
        mock_event_bus_func.return_value = mock_event_bus
        
        mock_celery_task.apply_async = Mock()

        # Act
        service.submit_result(
            match_id=101,
            submitted_by_user_id=100,
            submitted_by_team_id=5,
            raw_result_payload={'winner_team_id': 5, 'loser_team_id': 6},
        )

        # Assert
        mock_celery_task.apply_async.assert_called_once()
        call_kwargs = mock_celery_task.apply_async.call_args[1]
        assert call_kwargs['args'] == [1001]
        assert call_kwargs['countdown'] == 24 * 60 * 60  # 24 hours in seconds

    # =========================================================================
    # confirm_result() tests
    # =========================================================================

    @patch('apps.tournament_ops.services.result_submission_service.get_event_bus')
    def test_confirm_result_updates_status_and_sets_confirmed_by(
        self,
        mock_event_bus_func,
        service,
        mock_result_submission_adapter,
        mock_match_adapter,
        sample_match_dto,
        sample_submission_dto,
    ):
        """Test confirm_result updates status and sets confirmed_by_user_id."""
        # Arrange
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_match_adapter.get_match.return_value = sample_match_dto
        
        updated_submission = MatchResultSubmissionDTO(
            **{**sample_submission_dto.__dict__, 'status': 'confirmed', 'confirmed_by_user_id': 200}
        )
        mock_result_submission_adapter.update_submission_status.return_value = updated_submission
        
        mock_event_bus = Mock()
        mock_event_bus_func.return_value = mock_event_bus

        # Act
        result = service.confirm_result(submission_id=1001, confirmed_by_user_id=200)

        # Assert
        assert result.status == 'confirmed'
        assert result.confirmed_by_user_id == 200
        
        # Verify adapter was called
        mock_result_submission_adapter.update_submission_status.assert_called_once_with(
            submission_id=1001,
            status='confirmed',
            confirmed_by_user_id=200,
        )
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.name == 'MatchResultConfirmedEvent'

    def test_confirm_result_rejects_if_not_opponent(
        self,
        service,
        mock_result_submission_adapter,
        mock_match_adapter,
        sample_match_dto,
        sample_submission_dto,
    ):
        """Test confirm_result raises PermissionDeniedError if submitter tries to confirm."""
        # Arrange
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        mock_match_adapter.get_match.return_value = sample_match_dto

        # Act & Assert
        with pytest.raises(PermissionDeniedError, match='Submitter cannot confirm their own result'):
            service.confirm_result(
                submission_id=1001,
                confirmed_by_user_id=100,  # Same as submitted_by_user_id
            )

    def test_confirm_result_rejects_if_not_pending(
        self,
        service,
        mock_result_submission_adapter,
        sample_submission_dto,
    ):
        """Test confirm_result raises InvalidSubmissionStateError if not pending."""
        # Arrange
        sample_submission_dto.status = 'confirmed'  # Already confirmed
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto

        # Act & Assert
        with pytest.raises(InvalidSubmissionStateError, match='Cannot confirm submission in state: confirmed'):
            service.confirm_result(submission_id=1001, confirmed_by_user_id=200)

    # =========================================================================
    # auto_confirm_result() tests
    # =========================================================================

    @patch('apps.tournament_ops.services.result_submission_service.get_event_bus')
    def test_auto_confirm_result_updates_status_when_deadline_passed(
        self,
        mock_event_bus_func,
        service,
        mock_result_submission_adapter,
        sample_submission_dto,
    ):
        """Test auto_confirm_result updates status when deadline passed."""
        # Arrange
        sample_submission_dto.auto_confirm_deadline = datetime.now() - timedelta(hours=1)  # Expired
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        
        updated_submission = MatchResultSubmissionDTO(
            **{**sample_submission_dto.__dict__, 'status': 'auto_confirmed'}
        )
        mock_result_submission_adapter.update_submission_status.return_value = updated_submission
        
        mock_event_bus = Mock()
        mock_event_bus_func.return_value = mock_event_bus

        # Act
        result = service.auto_confirm_result(submission_id=1001)

        # Assert
        assert result.status == 'auto_confirmed'
        
        # Verify adapter was called
        mock_result_submission_adapter.update_submission_status.assert_called_once_with(
            submission_id=1001,
            status='auto_confirmed',
        )
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.name == 'MatchResultAutoConfirmedEvent'

    def test_auto_confirm_result_does_nothing_when_not_pending(
        self,
        service,
        mock_result_submission_adapter,
        sample_submission_dto,
    ):
        """Test auto_confirm_result returns unchanged if not pending."""
        # Arrange
        sample_submission_dto.status = 'confirmed'  # Not pending
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto

        # Act
        result = service.auto_confirm_result(submission_id=1001)

        # Assert
        assert result.status == 'confirmed'
        
        # Verify no update was attempted
        mock_result_submission_adapter.update_submission_status.assert_not_called()

    def test_auto_confirm_result_does_nothing_when_deadline_not_passed(
        self,
        service,
        mock_result_submission_adapter,
        sample_submission_dto,
    ):
        """Test auto_confirm_result returns unchanged if deadline not passed."""
        # Arrange
        sample_submission_dto.auto_confirm_deadline = datetime.now() + timedelta(hours=23)  # Not expired
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto

        # Act
        result = service.auto_confirm_result(submission_id=1001)

        # Assert
        assert result.status == 'pending'
        
        # Verify no update was attempted
        mock_result_submission_adapter.update_submission_status.assert_not_called()

    @patch('apps.tournament_ops.services.result_submission_service.get_event_bus')
    def test_auto_confirm_result_publishes_auto_confirm_event(
        self,
        mock_event_bus_func,
        service,
        mock_result_submission_adapter,
        sample_submission_dto,
    ):
        """Test auto_confirm_result publishes MatchResultAutoConfirmedEvent."""
        # Arrange
        sample_submission_dto.auto_confirm_deadline = datetime.now() - timedelta(hours=1)
        mock_result_submission_adapter.get_submission.return_value = sample_submission_dto
        
        updated_submission = MatchResultSubmissionDTO(
            **{**sample_submission_dto.__dict__, 'status': 'auto_confirmed'}
        )
        mock_result_submission_adapter.update_submission_status.return_value = updated_submission
        
        mock_event_bus = Mock()
        mock_event_bus_func.return_value = mock_event_bus

        # Act
        service.auto_confirm_result(submission_id=1001)

        # Assert
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.name == 'MatchResultAutoConfirmedEvent'
        assert event.payload['submission_id'] == 1001
        assert event.payload['match_id'] == 101

    # =========================================================================
    # Helper tests
    # =========================================================================

    def test_validate_submitter_is_participant_accepts_valid_team(
        self,
        service,
        sample_match_dto,
    ):
        """Test _validate_submitter_is_participant accepts valid team participant."""
        # Should not raise
        service._validate_submitter_is_participant(
            match=sample_match_dto,
            user_id=100,
            team_id=5,  # Valid participant
        )

    def test_validate_submitter_is_participant_rejects_invalid_team(
        self,
        service,
        sample_match_dto,
    ):
        """Test _validate_submitter_is_participant rejects invalid team."""
        with pytest.raises(PermissionDeniedError, match='Team 99 is not a participant'):
            service._validate_submitter_is_participant(
                match=sample_match_dto,
                user_id=100,
                team_id=99,  # Not in match
            )

    # =========================================================================
    # Architecture guard
    # =========================================================================

    def test_result_submission_service_uses_adapter_and_never_imports_orm(self):
        """Test ResultSubmissionService never imports Django ORM models."""
        import inspect
        from apps.tournament_ops.services import result_submission_service
        
        source = inspect.getsource(result_submission_service)
        
        # Should NOT import tournaments.models at module level
        assert 'from apps.tournaments.models import' not in source
        assert 'from tournaments.models import' not in source
        
        # DTOs are allowed
        assert 'MatchResultSubmissionDTO' in source or 'from apps.tournament_ops.dtos' in source
