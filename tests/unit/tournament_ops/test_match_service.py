"""
Unit tests for MatchService (Phase 4, Epic 4.3).

Tests match lifecycle state transitions:
- schedule_match: pending → scheduled
- report_match_result: scheduled/live → pending_result
- accept_match_result: pending_result → completed
- void_match_result: pending_result/completed → scheduled

Reference: ROADMAP_AND_EPICS_PART_4.md Phase 4, Epic 4.3
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from apps.tournament_ops.services.match_service import MatchService
from apps.tournament_ops.dtos import MatchDTO
from apps.tournament_ops.exceptions import (
    InvalidMatchStateError,
    MatchLifecycleError,
)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_team_adapter():
    """Mock TeamAdapter for testing."""
    return Mock()


@pytest.fixture
def mock_user_adapter():
    """Mock UserAdapter for testing."""
    return Mock()


@pytest.fixture
def mock_game_adapter():
    """Mock GameAdapter for testing."""
    return Mock()


@pytest.fixture
def mock_match_adapter():
    """Mock MatchAdapter for testing."""
    return Mock()


@pytest.fixture
def mock_event_bus():
    """Mock EventBus for testing."""
    with patch("apps.tournament_ops.services.match_service.get_event_bus") as mock:
        event_bus = Mock()
        mock.return_value = event_bus
        yield event_bus


@pytest.fixture
def match_service(
    mock_team_adapter,
    mock_user_adapter,
    mock_game_adapter,
    mock_match_adapter,
    mock_event_bus,
):
    """Create MatchService with mocked dependencies."""
    return MatchService(
        team_adapter=mock_team_adapter,
        user_adapter=mock_user_adapter,
        game_adapter=mock_game_adapter,
        match_adapter=mock_match_adapter,
    )


@pytest.fixture
def sample_match_dto():
    """Sample MatchDTO for testing."""
    return MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=20,
        round_number=1,
        stage="round_1",
        state="pending",
        scheduled_time=None,
        result=None,
    )


# ==============================================================================
# schedule_match() Tests
# ==============================================================================


def test_schedule_match_sets_state_and_publishes_event(
    match_service, mock_match_adapter, mock_event_bus, sample_match_dto
):
    """Test scheduling a match sets state to scheduled and publishes event."""
    # Arrange
    sample_match_dto.state = "pending"
    mock_match_adapter.get_match.return_value = sample_match_dto

    scheduled_time = datetime(2025, 12, 15, 14, 0, 0)
    scheduled_match = MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=20,
        round_number=1,
        stage="round_1",
        state="pending",  # DTO state remains pending (ORM is scheduled)
        scheduled_time=scheduled_time,
        result=None,
    )
    mock_match_adapter.update_match_state.return_value = scheduled_match

    # Act
    result = match_service.schedule_match(match_id=1, scheduled_time=scheduled_time)

    # Assert
    assert result.scheduled_time == scheduled_time
    mock_match_adapter.get_match.assert_called_once_with(1)
    mock_match_adapter.update_match_state.assert_called_once()
    mock_event_bus.publish.assert_called_once()

    # Verify event payload
    event_call = mock_event_bus.publish.call_args[0][0]
    assert event_call.name == "MatchScheduledEvent"
    assert event_call.payload["match_id"] == 1
    assert event_call.payload["team_a_id"] == 10
    assert event_call.payload["team_b_id"] == 20


def test_schedule_match_raises_when_not_pending(
    match_service, mock_match_adapter, sample_match_dto
):
    """Test scheduling a match in non-pending state raises error."""
    # Arrange
    sample_match_dto.state = "completed"
    mock_match_adapter.get_match.return_value = sample_match_dto

    # Act & Assert
    with pytest.raises(InvalidMatchStateError) as exc_info:
        match_service.schedule_match(match_id=1, scheduled_time=datetime.now())

    assert "Cannot schedule match" in str(exc_info.value)
    assert "completed" in str(exc_info.value)
    mock_match_adapter.update_match_state.assert_not_called()


def test_schedule_match_with_no_time_still_updates_state(
    match_service, mock_match_adapter, mock_event_bus, sample_match_dto
):
    """Test scheduling a match without specific time still updates state."""
    # Arrange
    sample_match_dto.state = "pending"
    mock_match_adapter.get_match.return_value = sample_match_dto

    scheduled_match = MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=20,
        round_number=1,
        stage="round_1",
        state="pending",
        scheduled_time=None,
        result=None,
    )
    mock_match_adapter.update_match_state.return_value = scheduled_match

    # Act
    result = match_service.schedule_match(match_id=1, scheduled_time=None)

    # Assert
    assert result.scheduled_time is None
    mock_match_adapter.update_match_state.assert_called_once()


# ==============================================================================
# report_match_result() Tests
# ==============================================================================


def test_report_match_result_validates_schema_and_stores_result(
    match_service, mock_match_adapter, mock_event_bus, sample_match_dto
):
    """Test reporting match result validates payload and updates state."""
    # Arrange
    sample_match_dto.state = "pending"
    mock_match_adapter.get_match.return_value = sample_match_dto

    result_payload = {
        "winner_id": 10,
        "loser_id": 20,
        "winner_score": 16,
        "loser_score": 14,
    }

    updated_match = MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=20,
        round_number=1,
        stage="round_1",
        state="in_progress",  # PENDING_RESULT maps to in_progress
        scheduled_time=None,
        result=None,
    )
    mock_match_adapter.update_match_state.return_value = updated_match

    # Act
    result = match_service.report_match_result(
        match_id=1, submitted_by_user_id=5, raw_result_payload=result_payload
    )

    # Assert
    assert result.state == "in_progress"
    mock_match_adapter.get_match.assert_called_once_with(1)
    mock_match_adapter.update_match_state.assert_called_once()
    mock_event_bus.publish.assert_called_once()

    # Verify event payload
    event_call = mock_event_bus.publish.call_args[0][0]
    assert event_call.name == "MatchResultSubmittedEvent"
    assert event_call.payload["match_id"] == 1
    assert event_call.payload["winner_id"] == 10
    assert event_call.payload["loser_id"] == 20


def test_report_match_result_raises_error_if_invalid_payload(
    match_service, mock_match_adapter, sample_match_dto
):
    """Test reporting match result with invalid payload raises error."""
    # Arrange
    sample_match_dto.state = "pending"
    mock_match_adapter.get_match.return_value = sample_match_dto

    # Missing winner_id and loser_id
    invalid_payload = {"score": 100}

    # Act & Assert
    with pytest.raises(MatchLifecycleError) as exc_info:
        match_service.report_match_result(
            match_id=1, submitted_by_user_id=5, raw_result_payload=invalid_payload
        )

    assert "must include winner_id and loser_id" in str(exc_info.value)
    mock_match_adapter.update_match_state.assert_not_called()


def test_report_match_result_raises_if_winner_not_participant(
    match_service, mock_match_adapter, sample_match_dto
):
    """Test reporting match result with invalid winner_id raises error."""
    # Arrange
    sample_match_dto.state = "pending"
    sample_match_dto.team_a_id = 10
    sample_match_dto.team_b_id = 20
    mock_match_adapter.get_match.return_value = sample_match_dto

    # Winner is not a participant
    invalid_payload = {
        "winner_id": 999,
        "loser_id": 20,
        "winner_score": 16,
        "loser_score": 14,
    }

    # Act & Assert
    with pytest.raises(MatchLifecycleError) as exc_info:
        match_service.report_match_result(
            match_id=1, submitted_by_user_id=5, raw_result_payload=invalid_payload
        )

    assert "must be match participants" in str(exc_info.value)


def test_report_match_result_publishes_event_with_raw_payload(
    match_service, mock_match_adapter, mock_event_bus, sample_match_dto
):
    """Test that raw result payload is included in event."""
    # Arrange
    sample_match_dto.state = "in_progress"
    mock_match_adapter.get_match.return_value = sample_match_dto

    result_payload = {
        "winner_id": 10,
        "loser_id": 20,
        "winner_score": 16,
        "loser_score": 14,
        "map": "Haven",
        "rounds": [{"round": 1, "winner": 10}],
    }

    updated_match = MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=20,
        round_number=1,
        stage="round_1",
        state="in_progress",
        scheduled_time=None,
        result=None,
    )
    mock_match_adapter.update_match_state.return_value = updated_match

    # Act
    match_service.report_match_result(
        match_id=1, submitted_by_user_id=5, raw_result_payload=result_payload
    )

    # Assert
    event_call = mock_event_bus.publish.call_args[0][0]
    assert event_call.payload["raw_result"] == result_payload


def test_report_match_result_raises_if_match_completed(
    match_service, mock_match_adapter, sample_match_dto
):
    """Test reporting result for completed match raises error."""
    # Arrange
    sample_match_dto.state = "completed"
    mock_match_adapter.get_match.return_value = sample_match_dto

    result_payload = {
        "winner_id": 10,
        "loser_id": 20,
        "winner_score": 16,
        "loser_score": 14,
    }

    # Act & Assert
    with pytest.raises(InvalidMatchStateError) as exc_info:
        match_service.report_match_result(
            match_id=1, submitted_by_user_id=5, raw_result_payload=result_payload
        )

    assert "Cannot report result" in str(exc_info.value)


def test_report_match_result_raises_if_empty_payload(
    match_service, mock_match_adapter, sample_match_dto
):
    """Test reporting match result with empty payload raises error."""
    # Arrange
    sample_match_dto.state = "pending"
    mock_match_adapter.get_match.return_value = sample_match_dto

    # Act & Assert
    with pytest.raises(MatchLifecycleError) as exc_info:
        match_service.report_match_result(
            match_id=1, submitted_by_user_id=5, raw_result_payload={}
        )

    assert "Result payload is empty" in str(exc_info.value)


# ==============================================================================
# accept_match_result() Tests
# ==============================================================================


def test_accept_match_result_transitions_to_completed_and_publishes_event(
    match_service, mock_match_adapter, mock_event_bus, sample_match_dto
):
    """Test accepting match result transitions to completed and publishes event."""
    # Arrange
    sample_match_dto.state = "in_progress"  # PENDING_RESULT
    sample_match_dto.result = {
        "winner_id": 10,
        "loser_id": 20,
        "participant1_score": 16,
        "participant2_score": 14,
    }
    mock_match_adapter.get_match.return_value = sample_match_dto

    completed_match = MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=20,
        round_number=1,
        stage="round_1",
        state="completed",
        scheduled_time=None,
        result={"winner_id": 10, "loser_id": 20, "participant1_score": 16, "participant2_score": 14},
    )
    mock_match_adapter.update_match_state.return_value = completed_match

    # Act
    result = match_service.accept_match_result(match_id=1, approved_by_user_id=100)

    # Assert
    assert result.state == "completed"
    mock_match_adapter.get_match.assert_called_once_with(1)
    mock_match_adapter.update_match_state.assert_called_once()
    mock_event_bus.publish.assert_called_once()

    # Verify event payload
    event_call = mock_event_bus.publish.call_args[0][0]
    assert event_call.name == "MatchCompletedEvent"
    assert event_call.payload["match_id"] == 1
    assert event_call.payload["winner_id"] == 10


def test_accept_match_result_raises_if_no_submitted_result(
    match_service, mock_match_adapter, sample_match_dto
):
    """Test accepting match result without submitted result raises error."""
    # Arrange
    sample_match_dto.state = "in_progress"
    sample_match_dto.result = None  # No result submitted
    mock_match_adapter.get_match.return_value = sample_match_dto

    # Act & Assert
    with pytest.raises(MatchLifecycleError) as exc_info:
        match_service.accept_match_result(match_id=1, approved_by_user_id=100)

    assert "No result data found" in str(exc_info.value)
    mock_match_adapter.update_match_state.assert_not_called()


def test_accept_match_result_raises_if_match_pending(
    match_service, mock_match_adapter, sample_match_dto
):
    """Test accepting result for pending match raises error."""
    # Arrange
    sample_match_dto.state = "pending"
    mock_match_adapter.get_match.return_value = sample_match_dto

    # Act & Assert
    with pytest.raises(InvalidMatchStateError) as exc_info:
        match_service.accept_match_result(match_id=1, approved_by_user_id=100)

    assert "Cannot accept result" in str(exc_info.value)


# ==============================================================================
# void_match_result() Tests
# ==============================================================================


def test_void_match_result_clears_result_and_publishes_event(
    match_service, mock_match_adapter, mock_event_bus, sample_match_dto
):
    """Test voiding match result clears result and publishes event."""
    # Arrange
    sample_match_dto.state = "completed"
    sample_match_dto.result = {
        "winner_id": 10,
        "loser_id": 20,
        "participant1_score": 16,
        "participant2_score": 14,
    }
    mock_match_adapter.get_match.return_value = sample_match_dto

    voided_match = MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=20,
        round_number=1,
        stage="round_1",
        state="pending",  # Reset to pending (ORM is scheduled)
        scheduled_time=None,
        result=None,
    )
    mock_match_adapter.update_match_state.return_value = voided_match

    # Act
    result = match_service.void_match_result(
        match_id=1, reason="Admin correction", initiated_by_user_id=100
    )

    # Assert
    assert result.state == "pending"
    assert result.result is None
    mock_match_adapter.get_match.assert_called_once_with(1)
    mock_match_adapter.update_match_state.assert_called_once()
    mock_event_bus.publish.assert_called_once()

    # Verify event payload
    event_call = mock_event_bus.publish.call_args[0][0]
    assert event_call.name == "MatchVoidedEvent"
    assert event_call.payload["match_id"] == 1
    assert event_call.payload["reason"] == "Admin correction"


def test_void_match_result_raises_if_state_not_voidable(
    match_service, mock_match_adapter, sample_match_dto
):
    """Test voiding result for pending match raises error."""
    # Arrange
    sample_match_dto.state = "pending"
    mock_match_adapter.get_match.return_value = sample_match_dto

    # Act & Assert
    with pytest.raises(InvalidMatchStateError) as exc_info:
        match_service.void_match_result(
            match_id=1, reason="Test", initiated_by_user_id=100
        )

    assert "Cannot void result" in str(exc_info.value)
    mock_match_adapter.update_match_state.assert_not_called()


def test_void_match_result_from_pending_result_state(
    match_service, mock_match_adapter, mock_event_bus, sample_match_dto
):
    """Test voiding match result from PENDING_RESULT state works."""
    # Arrange
    sample_match_dto.state = "in_progress"  # PENDING_RESULT
    sample_match_dto.result = {"winner_id": 10, "loser_id": 20}
    mock_match_adapter.get_match.return_value = sample_match_dto

    voided_match = MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=20,
        round_number=1,
        stage="round_1",
        state="pending",
        scheduled_time=None,
        result=None,
    )
    mock_match_adapter.update_match_state.return_value = voided_match

    # Act
    result = match_service.void_match_result(
        match_id=1, reason="Wrong score", initiated_by_user_id=100
    )

    # Assert
    assert result.state == "pending"
    mock_match_adapter.update_match_state.assert_called_once()


# ==============================================================================
# Integration Tests
# ==============================================================================


def test_match_service_uses_game_adapter_for_validation(
    match_service, mock_game_adapter
):
    """Test that MatchService has access to GameAdapter for validation."""
    # Verify GameAdapter is injected
    assert match_service.game_adapter is mock_game_adapter


def test_match_service_uses_match_adapter_for_state_updates(
    match_service, mock_match_adapter
):
    """Test that MatchService uses MatchAdapter for state updates."""
    # Verify MatchAdapter is injected
    assert match_service.match_adapter is mock_match_adapter
