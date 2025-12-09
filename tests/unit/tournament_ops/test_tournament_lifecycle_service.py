"""
Unit tests for TournamentLifecycleService (Phase 4, Epic 4.2).

Tests tournament lifecycle state transitions:
- open_tournament: DRAFT/PUBLISHED → REGISTRATION_OPEN
- start_tournament: REGISTRATION_OPEN → LIVE (with validations)
- complete_tournament: LIVE → COMPLETED (with validations)
- cancel_tournament: Any → CANCELLED

Reference: ROADMAP_AND_EPICS_PART_4.md Phase 4, Epic 4.2
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from apps.tournament_ops.services.tournament_lifecycle_service import (
    TournamentLifecycleService,
)
from apps.tournament_ops.dtos import TournamentDTO
from apps.tournament_ops.exceptions import (
    InvalidTournamentStateError,
    RegistrationError,
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
def mock_tournament_adapter():
    """Mock TournamentAdapter for testing."""
    return Mock()


@pytest.fixture
def mock_event_bus():
    """Mock EventBus for testing."""
    with patch("apps.tournament_ops.services.tournament_lifecycle_service.get_event_bus") as mock:
        event_bus = Mock()
        mock.return_value = event_bus
        yield event_bus


@pytest.fixture
def lifecycle_service(
    mock_team_adapter,
    mock_user_adapter,
    mock_game_adapter,
    mock_tournament_adapter,
    mock_event_bus,
):
    """Create TournamentLifecycleService with mocked dependencies."""
    return TournamentLifecycleService(
        team_adapter=mock_team_adapter,
        user_adapter=mock_user_adapter,
        game_adapter=mock_game_adapter,
        tournament_adapter=mock_tournament_adapter,
    )


@pytest.fixture
def sample_tournament_dto():
    """Sample TournamentDTO for testing."""
    return TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="draft",
        start_time=None,
        ruleset={"round_duration": 90},
    )


# ==============================================================================
# open_tournament() Tests
# ==============================================================================


def test_open_tournament_from_draft_state(
    lifecycle_service, mock_tournament_adapter, mock_event_bus, sample_tournament_dto
):
    """Test opening a tournament from DRAFT state."""
    # Arrange
    sample_tournament_dto.status = "draft"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    opened_tournament = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="registration_open",
        start_time=None,
        ruleset={"round_duration": 90},
    )
    mock_tournament_adapter.update_tournament_status.return_value = opened_tournament

    # Act
    result = lifecycle_service.open_tournament(tournament_id=1)

    # Assert
    assert result.status == "registration_open"
    mock_tournament_adapter.get_tournament.assert_called_once_with(1)
    mock_tournament_adapter.update_tournament_status.assert_called_once_with(
        tournament_id=1, new_status="registration_open"
    )
    mock_event_bus.publish.assert_called_once()

    # Verify event payload
    event_call = mock_event_bus.publish.call_args[0][0]
    assert event_call.name == "TournamentOpenedEvent"
    assert event_call.payload["tournament_id"] == 1
    assert event_call.payload["tournament_name"] == "Test Tournament"


def test_open_tournament_from_published_state(
    lifecycle_service, mock_tournament_adapter, mock_event_bus, sample_tournament_dto
):
    """Test opening a tournament from PUBLISHED state."""
    # Arrange
    sample_tournament_dto.status = "published"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    opened_tournament = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="registration_open",
        start_time=None,
        ruleset={"round_duration": 90},
    )
    mock_tournament_adapter.update_tournament_status.return_value = opened_tournament

    # Act
    result = lifecycle_service.open_tournament(tournament_id=1)

    # Assert
    assert result.status == "registration_open"
    mock_tournament_adapter.update_tournament_status.assert_called_once_with(
        tournament_id=1, new_status="registration_open"
    )


def test_open_tournament_fails_from_invalid_state(
    lifecycle_service, mock_tournament_adapter, sample_tournament_dto
):
    """Test opening a tournament from an invalid state (e.g., LIVE) fails."""
    # Arrange
    sample_tournament_dto.status = "live"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    # Act & Assert
    with pytest.raises(InvalidTournamentStateError) as exc_info:
        lifecycle_service.open_tournament(tournament_id=1)

    assert "Cannot open tournament" in str(exc_info.value)
    assert "live" in str(exc_info.value)
    mock_tournament_adapter.update_tournament_status.assert_not_called()


def test_open_tournament_fails_from_completed_state(
    lifecycle_service, mock_tournament_adapter, sample_tournament_dto
):
    """Test opening a completed tournament fails."""
    # Arrange
    sample_tournament_dto.status = "completed"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    # Act & Assert
    with pytest.raises(InvalidTournamentStateError) as exc_info:
        lifecycle_service.open_tournament(tournament_id=1)

    assert "Cannot open tournament" in str(exc_info.value)


# ==============================================================================
# start_tournament() Tests
# ==============================================================================


def test_start_tournament_with_sufficient_registrations(
    lifecycle_service, mock_tournament_adapter, mock_event_bus, sample_tournament_dto
):
    """Test starting a tournament with sufficient registrations."""
    # Arrange
    sample_tournament_dto.status = "registration_open"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto
    mock_tournament_adapter.get_registration_count.return_value = 8
    mock_tournament_adapter.get_minimum_participants.return_value = 4

    started_tournament = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="live",
        start_time=None,
        ruleset={"round_duration": 90},
    )
    mock_tournament_adapter.update_tournament_status.return_value = started_tournament

    # Act
    result = lifecycle_service.start_tournament(tournament_id=1)

    # Assert
    assert result.status == "live"
    mock_tournament_adapter.get_tournament.assert_called_once_with(1)
    mock_tournament_adapter.get_registration_count.assert_called_once_with(1)
    mock_tournament_adapter.get_minimum_participants.assert_called_once_with(1)
    mock_tournament_adapter.update_tournament_status.assert_called_once_with(
        tournament_id=1, new_status="live"
    )
    mock_event_bus.publish.assert_called_once()

    # Verify event payload
    event_call = mock_event_bus.publish.call_args[0][0]
    assert event_call.name == "TournamentStartedEvent"
    assert event_call.payload["tournament_id"] == 1
    assert event_call.payload["participant_count"] == 8


def test_start_tournament_from_registration_closed_state(
    lifecycle_service, mock_tournament_adapter, mock_event_bus, sample_tournament_dto
):
    """Test starting a tournament from REGISTRATION_CLOSED state."""
    # Arrange
    sample_tournament_dto.status = "registration_closed"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto
    mock_tournament_adapter.get_registration_count.return_value = 8
    mock_tournament_adapter.get_minimum_participants.return_value = 4

    started_tournament = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="live",
        start_time=None,
        ruleset={"round_duration": 90},
    )
    mock_tournament_adapter.update_tournament_status.return_value = started_tournament

    # Act
    result = lifecycle_service.start_tournament(tournament_id=1)

    # Assert
    assert result.status == "live"


def test_start_tournament_fails_with_insufficient_registrations(
    lifecycle_service, mock_tournament_adapter, sample_tournament_dto
):
    """Test starting a tournament with insufficient registrations fails."""
    # Arrange
    sample_tournament_dto.status = "registration_open"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto
    mock_tournament_adapter.get_registration_count.return_value = 2
    mock_tournament_adapter.get_minimum_participants.return_value = 4

    # Act & Assert
    with pytest.raises(RegistrationError) as exc_info:
        lifecycle_service.start_tournament(tournament_id=1)

    assert "minimum 4 required" in str(exc_info.value)
    assert "Only 2 teams registered" in str(exc_info.value)
    mock_tournament_adapter.update_tournament_status.assert_not_called()


def test_start_tournament_fails_from_invalid_state(
    lifecycle_service, mock_tournament_adapter, sample_tournament_dto
):
    """Test starting a tournament from an invalid state (e.g., DRAFT) fails."""
    # Arrange
    sample_tournament_dto.status = "draft"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    # Act & Assert
    with pytest.raises(InvalidTournamentStateError) as exc_info:
        lifecycle_service.start_tournament(tournament_id=1)

    assert "Cannot start tournament" in str(exc_info.value)
    assert "draft" in str(exc_info.value)
    mock_tournament_adapter.get_registration_count.assert_not_called()


def test_start_tournament_fails_from_completed_state(
    lifecycle_service, mock_tournament_adapter, sample_tournament_dto
):
    """Test starting a completed tournament fails."""
    # Arrange
    sample_tournament_dto.status = "completed"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    # Act & Assert
    with pytest.raises(InvalidTournamentStateError) as exc_info:
        lifecycle_service.start_tournament(tournament_id=1)

    assert "Cannot start tournament" in str(exc_info.value)


# ==============================================================================
# complete_tournament() Tests
# ==============================================================================


def test_complete_tournament_with_all_matches_completed(
    lifecycle_service, mock_tournament_adapter, mock_event_bus, sample_tournament_dto
):
    """Test completing a tournament when all matches are completed."""
    # Arrange
    sample_tournament_dto.status = "live"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto
    mock_tournament_adapter.check_all_matches_completed.return_value = True

    completed_tournament = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="completed",
        start_time=None,
        ruleset={"round_duration": 90},
    )
    mock_tournament_adapter.update_tournament_status.return_value = completed_tournament

    # Act
    result = lifecycle_service.complete_tournament(tournament_id=1)

    # Assert
    assert result.status == "completed"
    mock_tournament_adapter.get_tournament.assert_called_once_with(1)
    mock_tournament_adapter.check_all_matches_completed.assert_called_once_with(1)
    mock_tournament_adapter.update_tournament_status.assert_called_once_with(
        tournament_id=1, new_status="completed"
    )
    mock_event_bus.publish.assert_called_once()

    # Verify event payload
    event_call = mock_event_bus.publish.call_args[0][0]
    assert event_call.name == "TournamentCompletedEvent"
    assert event_call.payload["tournament_id"] == 1


def test_complete_tournament_fails_with_pending_matches(
    lifecycle_service, mock_tournament_adapter, sample_tournament_dto
):
    """Test completing a tournament with pending matches fails."""
    # Arrange
    sample_tournament_dto.status = "live"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto
    mock_tournament_adapter.check_all_matches_completed.return_value = False

    # Act & Assert
    with pytest.raises(InvalidTournamentStateError) as exc_info:
        lifecycle_service.complete_tournament(tournament_id=1)

    assert "Not all matches are completed" in str(exc_info.value)
    mock_tournament_adapter.update_tournament_status.assert_not_called()


def test_complete_tournament_fails_from_invalid_state(
    lifecycle_service, mock_tournament_adapter, sample_tournament_dto
):
    """Test completing a tournament from an invalid state (e.g., DRAFT) fails."""
    # Arrange
    sample_tournament_dto.status = "draft"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    # Act & Assert
    with pytest.raises(InvalidTournamentStateError) as exc_info:
        lifecycle_service.complete_tournament(tournament_id=1)

    assert "Cannot complete tournament" in str(exc_info.value)
    assert "draft" in str(exc_info.value)
    mock_tournament_adapter.check_all_matches_completed.assert_not_called()


def test_complete_tournament_fails_from_registration_open_state(
    lifecycle_service, mock_tournament_adapter, sample_tournament_dto
):
    """Test completing a tournament from REGISTRATION_OPEN fails."""
    # Arrange
    sample_tournament_dto.status = "registration_open"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    # Act & Assert
    with pytest.raises(InvalidTournamentStateError) as exc_info:
        lifecycle_service.complete_tournament(tournament_id=1)

    assert "Cannot complete tournament" in str(exc_info.value)


# ==============================================================================
# cancel_tournament() Tests
# ==============================================================================


def test_cancel_tournament_from_draft_state(
    lifecycle_service, mock_tournament_adapter, mock_event_bus, sample_tournament_dto
):
    """Test cancelling a tournament from DRAFT state."""
    # Arrange
    sample_tournament_dto.status = "draft"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    cancelled_tournament = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="cancelled",
        start_time=None,
        ruleset={"round_duration": 90},
    )
    mock_tournament_adapter.update_tournament_status.return_value = cancelled_tournament

    # Act
    result = lifecycle_service.cancel_tournament(tournament_id=1, reason="Insufficient registrations")

    # Assert
    assert result.status == "cancelled"
    mock_tournament_adapter.get_tournament.assert_called_once_with(1)
    mock_tournament_adapter.update_tournament_status.assert_called_once_with(
        tournament_id=1, new_status="cancelled"
    )
    mock_event_bus.publish.assert_called_once()

    # Verify event payload
    event_call = mock_event_bus.publish.call_args[0][0]
    assert event_call.name == "TournamentCancelledEvent"
    assert event_call.payload["tournament_id"] == 1
    assert event_call.payload["reason"] == "Insufficient registrations"


def test_cancel_tournament_from_registration_open_state(
    lifecycle_service, mock_tournament_adapter, mock_event_bus, sample_tournament_dto
):
    """Test cancelling a tournament from REGISTRATION_OPEN state."""
    # Arrange
    sample_tournament_dto.status = "registration_open"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    cancelled_tournament = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="cancelled",
        start_time=None,
        ruleset={"round_duration": 90},
    )
    mock_tournament_adapter.update_tournament_status.return_value = cancelled_tournament

    # Act
    result = lifecycle_service.cancel_tournament(tournament_id=1, reason="Organizer request")

    # Assert
    assert result.status == "cancelled"


def test_cancel_tournament_from_live_state(
    lifecycle_service, mock_tournament_adapter, mock_event_bus, sample_tournament_dto
):
    """Test cancelling a tournament from LIVE state."""
    # Arrange
    sample_tournament_dto.status = "live"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    cancelled_tournament = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="cancelled",
        start_time=None,
        ruleset={"round_duration": 90},
    )
    mock_tournament_adapter.update_tournament_status.return_value = cancelled_tournament

    # Act
    result = lifecycle_service.cancel_tournament(tournament_id=1, reason="Technical issues")

    # Assert
    assert result.status == "cancelled"


def test_cancel_tournament_fails_from_completed_state(
    lifecycle_service, mock_tournament_adapter, sample_tournament_dto
):
    """Test cancelling a completed tournament fails."""
    # Arrange
    sample_tournament_dto.status = "completed"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    # Act & Assert
    with pytest.raises(InvalidTournamentStateError) as exc_info:
        lifecycle_service.cancel_tournament(tournament_id=1, reason="Test cancellation")

    assert "Cannot cancel tournament" in str(exc_info.value)
    assert "completed" in str(exc_info.value)
    assert "Completed tournaments cannot be cancelled" in str(exc_info.value)
    mock_tournament_adapter.update_tournament_status.assert_not_called()


def test_cancel_tournament_publishes_event_with_reason(
    lifecycle_service, mock_tournament_adapter, mock_event_bus, sample_tournament_dto
):
    """Test cancel_tournament publishes event with cancellation reason."""
    # Arrange
    sample_tournament_dto.status = "registration_open"
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto

    cancelled_tournament = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="cancelled",
        start_time=None,
        ruleset={"round_duration": 90},
    )
    mock_tournament_adapter.update_tournament_status.return_value = cancelled_tournament

    # Act
    lifecycle_service.cancel_tournament(tournament_id=1, reason="Venue unavailable")

    # Assert
    event_call = mock_event_bus.publish.call_args[0][0]
    assert event_call.name == "TournamentCancelledEvent"
    assert event_call.payload["reason"] == "Venue unavailable"
