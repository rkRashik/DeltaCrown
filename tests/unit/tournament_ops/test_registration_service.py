"""
Unit tests for RegistrationService (Phase 4, Epic 4.1).

These tests validate registration workflow orchestration:
- Registration initialization with eligibility checks
- Payment integration and confirmation
- Registration state transitions
- Event publishing
- Withdrawal workflows

Reference: CLEANUP_AND_TESTING_PART_6.md §9.4 (Phase 4 Acceptance Tests)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from apps.tournament_ops.services.registration_service import RegistrationService
from apps.tournament_ops.dtos import (
    RegistrationDTO,
    PaymentResultDTO,
    EligibilityResultDTO,
)
from apps.tournament_ops.exceptions import (
    RegistrationError,
    EligibilityError,
    PaymentError,
)


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing event publishing."""
    with patch("apps.tournament_ops.services.registration_service.get_event_bus") as mock:
        event_bus = Mock()
        mock.return_value = event_bus
        yield event_bus


@pytest.fixture
def mock_adapters():
    """Mock adapters for testing."""
    return {
        "team_adapter": Mock(),
        "user_adapter": Mock(),
        "game_adapter": Mock(),
        "economy_adapter": Mock(),
    }


@pytest.fixture
def registration_service(mock_adapters, mock_event_bus):
    """RegistrationService instance with mocked dependencies."""
    return RegistrationService(
        team_adapter=mock_adapters["team_adapter"],
        user_adapter=mock_adapters["user_adapter"],
        game_adapter=mock_adapters["game_adapter"],
        economy_adapter=mock_adapters["economy_adapter"],
    )


# =============================================================================
# Start Registration Tests
# =============================================================================


def test_start_registration_creates_valid_registration(
    registration_service, mock_event_bus
):
    """
    Test that start_registration creates a valid registration DTO.
    """
    # Arrange
    tournament_id = 100
    user_id = 50
    team_id = 25
    answers = {"question1": "answer1"}

    # Act
    result = registration_service.start_registration(
        team_id=team_id,
        tournament_id=tournament_id,
        user_id=user_id,
        answers=answers,
    )

    # Assert
    assert result.tournament_id == tournament_id
    assert result.user_id == user_id
    assert result.team_id == team_id
    assert result.answers == answers
    assert result.status == "pending"

    # Verify event published
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.name == "RegistrationStartedEvent"


def test_start_registration_with_no_team_for_individual_tournament(
    registration_service, mock_event_bus
):
    """
    Test that start_registration works for individual tournaments (team_id=None).
    """
    # Arrange
    tournament_id = 100
    user_id = 50
    team_id = None
    answers = {}

    # Act
    result = registration_service.start_registration(
        team_id=team_id,
        tournament_id=tournament_id,
        user_id=user_id,
        answers=answers,
    )

    # Assert
    assert result.team_id is None
    assert result.user_id == user_id
    assert result.status == "pending"


def test_start_registration_publishes_event(
    registration_service, mock_event_bus
):
    """
    Test that start_registration publishes RegistrationStartedEvent.
    """
    # Arrange
    tournament_id = 100
    user_id = 50
    team_id = 25

    # Act
    registration_service.start_registration(
        team_id=team_id,
        tournament_id=tournament_id,
        user_id=user_id,
        answers={},
    )

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.name == "RegistrationStartedEvent"
    assert published_event.payload["tournament_id"] == tournament_id
    assert published_event.payload["user_id"] == user_id
    assert published_event.payload["team_id"] == team_id


# =============================================================================
# Complete Registration Tests
# =============================================================================


def test_complete_registration_transitions_to_confirmed(
    registration_service, mock_event_bus
):
    """
    Test that complete_registration transitions status to APPROVED.
    """
    # Arrange
    registration = RegistrationDTO(
        id=1,
        tournament_id=100,
        team_id=25,
        user_id=50,
        answers={},
        status="pending",
    )
    payment = PaymentResultDTO(
        success=True,
        transaction_id="txn_12345",
        error=None,
    )

    # Act
    result = registration_service.complete_registration(
        registration=registration,
        payment=payment,
    )

    # Assert
    assert result.status == "approved"
    assert result.id == registration.id
    assert result.tournament_id == registration.tournament_id

    # Verify event published
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.name == "RegistrationConfirmedEvent"
    assert published_event.payload["payment_transaction_id"] == "txn_12345"


def test_complete_registration_fails_with_failed_payment(
    registration_service, mock_event_bus
):
    """
    Test that complete_registration raises PaymentError if payment failed.
    """
    # Arrange
    registration = RegistrationDTO(
        id=1,
        tournament_id=100,
        team_id=25,
        user_id=50,
        answers={},
        status="pending",
    )
    payment = PaymentResultDTO(
        success=False,
        transaction_id=None,
        error="Insufficient balance",
    )

    # Act & Assert
    with pytest.raises(PaymentError, match="Payment verification failed"):
        registration_service.complete_registration(
            registration=registration,
            payment=payment,
        )

    # Verify no event published on failure
    mock_event_bus.publish.assert_not_called()


def test_complete_registration_validates_payment_result(
    registration_service, mock_event_bus
):
    """
    Test that complete_registration validates PaymentResultDTO.
    """
    # Arrange
    registration = RegistrationDTO(
        id=1,
        tournament_id=100,
        team_id=25,
        user_id=50,
        answers={},
        status="pending",
    )
    # Invalid payment: success=True but no transaction_id
    payment = PaymentResultDTO(
        success=True,
        transaction_id=None,
        error=None,
    )

    # Act & Assert
    with pytest.raises(PaymentError, match="Invalid payment result"):
        registration_service.complete_registration(
            registration=registration,
            payment=payment,
        )


# =============================================================================
# Validate Registration Tests
# =============================================================================


def test_validate_registration_returns_eligible(registration_service):
    """
    Test that validate_registration returns is_eligible=True for valid input.
    """
    # Arrange
    tournament_id = 100
    user_id = 50
    team_id = 25

    # Act
    result = registration_service.validate_registration(
        team_id=team_id,
        tournament_id=tournament_id,
        user_id=user_id,
    )

    # Assert
    assert result.is_eligible is True
    assert len(result.reasons) == 0


def test_validate_registration_returns_eligibility_dto(registration_service):
    """
    Test that validate_registration returns valid EligibilityResultDTO.
    """
    # Arrange
    tournament_id = 100
    user_id = 50
    team_id = None  # Individual tournament

    # Act
    result = registration_service.validate_registration(
        team_id=team_id,
        tournament_id=tournament_id,
        user_id=user_id,
    )

    # Assert
    assert isinstance(result, EligibilityResultDTO)
    assert result.is_eligible is True


# =============================================================================
# Withdraw Registration Tests
# =============================================================================


def test_withdraw_registration_transitions_to_withdrawn(
    registration_service, mock_event_bus
):
    """
    Test that withdraw_registration transitions status to WITHDRAWN.
    """
    # Arrange
    registration = RegistrationDTO(
        id=1,
        tournament_id=100,
        team_id=25,
        user_id=50,
        answers={},
        status="approved",
    )
    initiated_by_user_id = 50

    # Act
    result = registration_service.withdraw_registration(
        registration=registration,
        initiated_by_user_id=initiated_by_user_id,
    )

    # Assert
    assert result.status == "withdrawn"
    assert result.id == registration.id

    # Verify event published
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.name == "RegistrationWithdrawnEvent"
    assert published_event.payload["registration_id"] == registration.id
    assert published_event.payload["initiated_by_user_id"] == initiated_by_user_id


def test_withdraw_registration_fails_if_already_withdrawn(
    registration_service, mock_event_bus
):
    """
    Test that withdraw_registration raises error if already withdrawn.
    """
    # Arrange
    registration = RegistrationDTO(
        id=1,
        tournament_id=100,
        team_id=25,
        user_id=50,
        answers={},
        status="withdrawn",
    )

    # Act & Assert
    with pytest.raises(RegistrationError, match="already withdrawn"):
        registration_service.withdraw_registration(
            registration=registration,
            initiated_by_user_id=50,
        )

    # Verify no event published
    mock_event_bus.publish.assert_not_called()


def test_withdraw_registration_publishes_event(
    registration_service, mock_event_bus
):
    """
    Test that withdraw_registration publishes RegistrationWithdrawnEvent.
    """
    # Arrange
    registration = RegistrationDTO(
        id=1,
        tournament_id=100,
        team_id=25,
        user_id=50,
        answers={},
        status="approved",
    )

    # Act
    registration_service.withdraw_registration(
        registration=registration,
        initiated_by_user_id=50,
    )

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.name == "RegistrationWithdrawnEvent"
    assert published_event.payload["tournament_id"] == 100
    assert published_event.payload["team_id"] == 25
    assert published_event.payload["user_id"] == 50
