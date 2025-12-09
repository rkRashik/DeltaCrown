"""
Unit tests for TournamentOpsService (Phase 4, Epic 4.1).

These tests validate the registration orchestration workflows:
- Registration initiation and eligibility validation
- Payment processing integration
- Registration state transitions
- Event publishing

Reference: CLEANUP_AND_TESTING_PART_6.md §9.4 (Phase 4 Acceptance Tests)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from apps.tournament_ops.services.tournament_ops_service import TournamentOpsService
from apps.tournament_ops.services.registration_service import RegistrationService
from apps.tournament_ops.services.payment_service import PaymentOrchestrationService
from apps.tournament_ops.services.tournament_lifecycle_service import (
    TournamentLifecycleService,
)
from apps.tournament_ops.dtos import (
    RegistrationDTO,
    PaymentResultDTO,
    EligibilityResultDTO,
    TournamentDTO,
)
from apps.tournament_ops.exceptions import (
    RegistrationError,
    EligibilityError,
    PaymentError,
    InvalidTournamentStateError,
)


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing event publishing."""
    with patch("apps.tournament_ops.services.tournament_ops_service.get_event_bus") as mock:
        event_bus = Mock()
        mock.return_value = event_bus
        yield event_bus


@pytest.fixture
def mock_registration_service():
    """Mock RegistrationService for testing."""
    return Mock(spec=RegistrationService)


@pytest.fixture
def mock_payment_service():
    """Mock PaymentOrchestrationService for testing."""
    return Mock(spec=PaymentOrchestrationService)


@pytest.fixture
def mock_lifecycle_service():
    """Mock TournamentLifecycleService for testing."""
    return Mock(spec=TournamentLifecycleService)


@pytest.fixture
def mock_adapters():
    """Mock adapters for testing."""
    return {
        "team_adapter": Mock(),
        "user_adapter": Mock(),
        "game_adapter": Mock(),
        "economy_adapter": Mock(),
        "tournament_adapter": Mock(),
    }


@pytest.fixture
def tournament_ops_service(
    mock_registration_service,
    mock_payment_service,
    mock_lifecycle_service,
    mock_adapters,
    mock_event_bus,
):
    """TournamentOpsService instance with mocked dependencies."""
    return TournamentOpsService(
        registration_service=mock_registration_service,
        payment_service=mock_payment_service,
        lifecycle_service=mock_lifecycle_service,
        team_adapter=mock_adapters["team_adapter"],
        user_adapter=mock_adapters["user_adapter"],
        game_adapter=mock_adapters["game_adapter"],
        economy_adapter=mock_adapters["economy_adapter"],
        tournament_adapter=mock_adapters["tournament_adapter"],
    )


# =============================================================================
# Registration Orchestration Tests
# =============================================================================


def test_register_participant_creates_registration(
    tournament_ops_service, mock_registration_service, mock_event_bus
):
    """
    Test that register_participant creates a registration and publishes event.

    Reference: CLEANUP_AND_TESTING_PART_6.md §9.4 (Phase 4 Acceptance Tests)
    """
    # Arrange
    tournament_id = 100
    user_id = 50
    team_id = 25
    answers = {"question1": "answer1"}

    expected_registration = RegistrationDTO(
        id=1,
        tournament_id=tournament_id,
        team_id=team_id,
        user_id=user_id,
        answers=answers,
        status="pending",
    )

    mock_registration_service.start_registration.return_value = expected_registration

    # Act
    result = tournament_ops_service.register_participant(
        tournament_id=tournament_id,
        user_id=user_id,
        team_id=team_id,
        answers=answers,
    )

    # Assert
    assert result == expected_registration
    mock_registration_service.start_registration.assert_called_once_with(
        team_id=team_id,
        tournament_id=tournament_id,
        user_id=user_id,
        answers=answers,
    )

    # Verify event published
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.name == "RegistrationStartedEvent"
    assert published_event.payload["tournament_id"] == tournament_id
    assert published_event.payload["user_id"] == user_id
    assert published_event.payload["team_id"] == team_id


def test_ineligible_user_cannot_register(
    tournament_ops_service, mock_registration_service
):
    """
    Test that ineligible users are rejected during registration.

    Reference: CLEANUP_AND_TESTING_PART_6.md §9.4 (Phase 4 Acceptance Tests)
    """
    # Arrange
    tournament_id = 100
    user_id = 50
    team_id = 25

    # Simulate eligibility failure
    mock_registration_service.start_registration.side_effect = EligibilityError(
        "User is banned"
    )

    # Act & Assert
    with pytest.raises(EligibilityError, match="User is banned"):
        tournament_ops_service.register_participant(
            tournament_id=tournament_id,
            user_id=user_id,
            team_id=team_id,
            answers={},
        )


def test_payment_verification_confirms_registration(
    tournament_ops_service,
    mock_registration_service,
    mock_payment_service,
    mock_event_bus,
):
    """
    Test that payment verification transitions registration to CONFIRMED.

    Reference: CLEANUP_AND_TESTING_PART_6.md §9.4 (Phase 4 Acceptance Tests)
    """
    # Arrange
    registration_id = 1
    payment_reference = "txn_12345"

    pending_registration = RegistrationDTO(
        id=registration_id,
        tournament_id=100,
        team_id=25,
        user_id=50,
        answers={},
        status="pending_payment",
    )

    confirmed_registration = RegistrationDTO(
        id=registration_id,
        tournament_id=100,
        team_id=25,
        user_id=50,
        answers={},
        status="approved",
    )

    mock_registration_service.complete_registration.return_value = confirmed_registration

    # Act
    result = tournament_ops_service.verify_payment_and_confirm_registration(
        registration_id=registration_id,
        payment_reference=payment_reference,
    )

    # Assert
    assert result.status == "approved"
    mock_registration_service.complete_registration.assert_called_once()

    # Verify event published
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.name == "RegistrationConfirmedEvent"
    assert published_event.payload["registration_id"] == registration_id
    assert published_event.payload["payment_reference"] == payment_reference


def test_payment_failure_blocks_registration_confirmation(
    tournament_ops_service, mock_registration_service
):
    """
    Test that failed payment prevents registration confirmation.

    Reference: CLEANUP_AND_TESTING_PART_6.md §9.4 (Phase 4 Acceptance Tests)
    """
    # Arrange
    registration_id = 1

    mock_registration_service.complete_registration.side_effect = PaymentError(
        "Payment verification failed"
    )

    # Act & Assert
    with pytest.raises(PaymentError, match="Payment verification failed"):
        tournament_ops_service.verify_payment_and_confirm_registration(
            registration_id=registration_id,
            payment_reference=None,
        )


def test_registration_workflow_state_transitions(
    tournament_ops_service,
    mock_registration_service,
    mock_payment_service,
    mock_event_bus,
):
    """
    Test complete registration workflow: DRAFT → SUBMITTED → CONFIRMED.

    Reference: CLEANUP_AND_TESTING_PART_6.md §9.4 (Phase 4 Acceptance Tests)
    """
    # Arrange
    tournament_id = 100
    user_id = 50
    team_id = 25

    # Step 1: Start registration (DRAFT → PENDING)
    submitted_registration = RegistrationDTO(
        id=1,
        tournament_id=tournament_id,
        team_id=team_id,
        user_id=user_id,
        answers={},
        status="pending",
    )
    mock_registration_service.start_registration.return_value = submitted_registration

    # Step 2: Complete registration (PENDING → APPROVED)
    confirmed_registration = RegistrationDTO(
        id=1,
        tournament_id=tournament_id,
        team_id=team_id,
        user_id=user_id,
        answers={},
        status="approved",
    )
    mock_registration_service.complete_registration.return_value = confirmed_registration

    # Act - Step 1: Register participant
    registration = tournament_ops_service.register_participant(
        tournament_id=tournament_id,
        user_id=user_id,
        team_id=team_id,
        answers={},
    )
    assert registration.status == "pending"

    # Act - Step 2: Verify payment and confirm
    confirmed = tournament_ops_service.verify_payment_and_confirm_registration(
        registration_id=registration.id,
        payment_reference="txn_12345",
    )

    # Assert
    assert confirmed.status == "approved"

    # Verify events published (RegistrationStartedEvent + RegistrationConfirmedEvent)
    assert mock_event_bus.publish.call_count == 2


def test_registration_events_published(
    tournament_ops_service,
    mock_registration_service,
    mock_event_bus,
):
    """
    Test that registration workflow publishes all required events.

    Events expected:
    - RegistrationStartedEvent (when registration created)
    - RegistrationConfirmedEvent (when payment verified)

    Reference: CLEANUP_AND_TESTING_PART_6.md §9.4 (Phase 4 Acceptance Tests)
    """
    # Arrange
    tournament_id = 100
    user_id = 50
    team_id = 25

    registration = RegistrationDTO(
        id=1,
        tournament_id=tournament_id,
        team_id=team_id,
        user_id=user_id,
        answers={},
        status="pending",
    )
    mock_registration_service.start_registration.return_value = registration

    # Act
    tournament_ops_service.register_participant(
        tournament_id=tournament_id,
        user_id=user_id,
        team_id=team_id,
        answers={},
    )

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.name == "RegistrationStartedEvent"
    assert published_event.payload["tournament_id"] == tournament_id
    assert published_event.payload["user_id"] == user_id
    assert published_event.payload["team_id"] == team_id
    assert published_event.payload["status"] == "pending"


# =============================================================================
# Lazy Initialization Tests
# =============================================================================


def test_lazy_initialization_of_services(mock_event_bus):
    """
    Test that services are lazily initialized when not injected.
    """
    # Arrange & Act
    with patch("apps.tournament_ops.services.tournament_ops_service.RegistrationService"):
        with patch("apps.tournament_ops.services.tournament_ops_service.PaymentOrchestrationService"):
            service = TournamentOpsService()

            # Access properties to trigger lazy init
            _ = service.registration_service
            _ = service.payment_service

            # Assert - no exceptions raised


def test_lazy_initialization_of_adapters(mock_event_bus):
    """
    Test that adapters are lazily initialized when not injected.
    """
    # Arrange & Act
    with patch("apps.tournament_ops.services.tournament_ops_service.TeamAdapter"):
        with patch("apps.tournament_ops.services.tournament_ops_service.UserAdapter"):
            with patch("apps.tournament_ops.services.tournament_ops_service.GameAdapter"):
                with patch("apps.tournament_ops.services.tournament_ops_service.EconomyAdapter"):
                    service = TournamentOpsService()

                    # Access properties to trigger lazy init
                    _ = service.team_adapter
                    _ = service.user_adapter
                    _ = service.game_adapter
                    _ = service.economy_adapter

                    # Assert - no exceptions raised


# =============================================================================
# Future Epic Placeholders (Not Implemented in Phase 4)
# =============================================================================


# =============================================================================
# Tournament Lifecycle Tests (Phase 4, Epic 4.2)
# =============================================================================


def test_open_tournament_delegates_to_lifecycle_service(
    tournament_ops_service, mock_lifecycle_service
):
    """Test that open_tournament delegates to TournamentLifecycleService."""
    # Arrange
    tournament_id = 100
    expected_tournament = TournamentDTO(
        id=tournament_id,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="registration_open",
        start_time=None,
        ruleset={},
    )
    mock_lifecycle_service.open_tournament.return_value = expected_tournament

    # Act
    result = tournament_ops_service.open_tournament(tournament_id)

    # Assert
    assert result.status == "registration_open"
    mock_lifecycle_service.open_tournament.assert_called_once_with(tournament_id)


def test_start_tournament_delegates_to_lifecycle_service(
    tournament_ops_service, mock_lifecycle_service
):
    """Test that start_tournament delegates to TournamentLifecycleService."""
    # Arrange
    tournament_id = 100
    expected_tournament = TournamentDTO(
        id=tournament_id,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="live",
        start_time=None,
        ruleset={},
    )
    mock_lifecycle_service.start_tournament.return_value = expected_tournament

    # Act
    result = tournament_ops_service.start_tournament(tournament_id)

    # Assert
    assert result.status == "live"
    mock_lifecycle_service.start_tournament.assert_called_once_with(tournament_id)


def test_complete_tournament_delegates_to_lifecycle_service(
    tournament_ops_service, mock_lifecycle_service
):
    """Test that complete_tournament delegates to TournamentLifecycleService."""
    # Arrange
    tournament_id = 100
    expected_tournament = TournamentDTO(
        id=tournament_id,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="completed",
        start_time=None,
        ruleset={},
    )
    mock_lifecycle_service.complete_tournament.return_value = expected_tournament

    # Act
    result = tournament_ops_service.complete_tournament(tournament_id)

    # Assert
    assert result.status == "completed"
    mock_lifecycle_service.complete_tournament.assert_called_once_with(tournament_id)


def test_cancel_tournament_delegates_to_lifecycle_service(
    tournament_ops_service, mock_lifecycle_service
):
    """Test that cancel_tournament delegates to TournamentLifecycleService."""
    # Arrange
    tournament_id = 100
    reason = "Insufficient registrations"
    expected_tournament = TournamentDTO(
        id=tournament_id,
        name="Test Tournament",
        game_slug="valorant",
        stage="single_elimination",
        team_size=5,
        max_teams=16,
        status="cancelled",
        start_time=None,
        ruleset={},
    )
    mock_lifecycle_service.cancel_tournament.return_value = expected_tournament

    # Act
    result = tournament_ops_service.cancel_tournament(tournament_id, reason)

    # Assert
    assert result.status == "cancelled"
    mock_lifecycle_service.cancel_tournament.assert_called_once_with(tournament_id, reason)


def test_lifecycle_service_bubbles_invalid_state_error(
    tournament_ops_service, mock_lifecycle_service
):
    """Test that lifecycle service exceptions are propagated to callers."""
    # Arrange
    tournament_id = 100
    mock_lifecycle_service.start_tournament.side_effect = InvalidTournamentStateError(
        "Cannot start tournament in draft state"
    )

    # Act & Assert
    with pytest.raises(InvalidTournamentStateError, match="Cannot start tournament"):
        tournament_ops_service.start_tournament(tournament_id)


def test_lifecycle_service_bubbles_registration_error(
    tournament_ops_service, mock_lifecycle_service
):
    """Test that RegistrationError is propagated from lifecycle service."""
    # Arrange
    tournament_id = 100
    mock_lifecycle_service.start_tournament.side_effect = RegistrationError(
        "Insufficient participants"
    )

    # Act & Assert
    with pytest.raises(RegistrationError, match="Insufficient participants"):
        tournament_ops_service.start_tournament(tournament_id)

