"""
Unit tests for PaymentOrchestrationService (Phase 4, Epic 4.1).

These tests validate payment processing workflows:
- Registration fee charging
- Payment refunds
- Event publishing
- Error handling

Reference: CLEANUP_AND_TESTING_PART_6.md §9.4 (Phase 4 Acceptance Tests)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from apps.tournament_ops.services.payment_service import PaymentOrchestrationService
from apps.tournament_ops.dtos import PaymentResultDTO
from apps.tournament_ops.exceptions import PaymentError


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing event publishing."""
    with patch("apps.tournament_ops.services.payment_service.get_event_bus") as mock:
        event_bus = Mock()
        mock.return_value = event_bus
        yield event_bus


@pytest.fixture
def mock_economy_adapter():
    """Mock EconomyAdapter for testing."""
    return Mock()


@pytest.fixture
def payment_service(mock_economy_adapter, mock_event_bus):
    """PaymentOrchestrationService instance with mocked dependencies."""
    return PaymentOrchestrationService(economy_adapter=mock_economy_adapter)


# =============================================================================
# Charge Registration Fee Tests
# =============================================================================


def test_charge_registration_fee_returns_success(
    payment_service, mock_event_bus
):
    """
    Test that charge_registration_fee returns successful PaymentResultDTO.
    """
    # Arrange
    user_id = 50
    tournament_id = 100
    amount = 1000

    # Act
    result = payment_service.charge_registration_fee(
        user_id=user_id,
        tournament_id=tournament_id,
        amount=amount,
    )

    # Assert
    assert result.success is True
    assert result.transaction_id is not None
    assert result.error is None


def test_charge_registration_fee_publishes_event(
    payment_service, mock_event_bus
):
    """
    Test that charge_registration_fee publishes PaymentChargedEvent on success.
    """
    # Arrange
    user_id = 50
    tournament_id = 100
    amount = 1000

    # Act
    payment_service.charge_registration_fee(
        user_id=user_id,
        tournament_id=tournament_id,
        amount=amount,
    )

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.name == "PaymentChargedEvent"
    assert published_event.payload["user_id"] == user_id
    assert published_event.payload["tournament_id"] == tournament_id
    assert published_event.payload["amount"] == amount
    assert "transaction_id" in published_event.payload


def test_charge_registration_fee_validates_result(
    payment_service, mock_event_bus
):
    """
    Test that charge_registration_fee validates the PaymentResultDTO.
    """
    # Arrange
    user_id = 50
    tournament_id = 100
    amount = 1000

    # Act
    result = payment_service.charge_registration_fee(
        user_id=user_id,
        tournament_id=tournament_id,
        amount=amount,
    )

    # Assert - validate DTO structure
    validation_errors = result.validate()
    assert len(validation_errors) == 0


def test_charge_registration_fee_includes_transaction_id(
    payment_service, mock_event_bus
):
    """
    Test that charge_registration_fee includes transaction_id in result.
    """
    # Arrange
    user_id = 50
    tournament_id = 100
    amount = 1000

    # Act
    result = payment_service.charge_registration_fee(
        user_id=user_id,
        tournament_id=tournament_id,
        amount=amount,
    )

    # Assert
    assert result.transaction_id is not None
    assert isinstance(result.transaction_id, str)
    assert len(result.transaction_id) > 0


# =============================================================================
# Refund Registration Fee Tests
# =============================================================================


def test_refund_registration_fee_returns_success(
    payment_service, mock_event_bus
):
    """
    Test that refund_registration_fee returns successful PaymentResultDTO.
    """
    # Arrange
    user_id = 50
    tournament_id = 100
    amount = 1000

    # Act
    result = payment_service.refund_registration_fee(
        user_id=user_id,
        tournament_id=tournament_id,
        amount=amount,
    )

    # Assert
    assert result.success is True
    assert result.transaction_id is not None
    assert result.error is None


def test_refund_registration_fee_publishes_event(
    payment_service, mock_event_bus
):
    """
    Test that refund_registration_fee publishes PaymentRefundedEvent on success.
    """
    # Arrange
    user_id = 50
    tournament_id = 100
    amount = 1000

    # Act
    payment_service.refund_registration_fee(
        user_id=user_id,
        tournament_id=tournament_id,
        amount=amount,
    )

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.name == "PaymentRefundedEvent"
    assert published_event.payload["user_id"] == user_id
    assert published_event.payload["tournament_id"] == tournament_id
    assert published_event.payload["amount"] == amount
    assert "transaction_id" in published_event.payload


def test_refund_registration_fee_validates_result(
    payment_service, mock_event_bus
):
    """
    Test that refund_registration_fee validates the PaymentResultDTO.
    """
    # Arrange
    user_id = 50
    tournament_id = 100
    amount = 1000

    # Act
    result = payment_service.refund_registration_fee(
        user_id=user_id,
        tournament_id=tournament_id,
        amount=amount,
    )

    # Assert - validate DTO structure
    validation_errors = result.validate()
    assert len(validation_errors) == 0


def test_refund_registration_fee_includes_transaction_id(
    payment_service, mock_event_bus
):
    """
    Test that refund_registration_fee includes transaction_id in result.
    """
    # Arrange
    user_id = 50
    tournament_id = 100
    amount = 1000

    # Act
    result = payment_service.refund_registration_fee(
        user_id=user_id,
        tournament_id=tournament_id,
        amount=amount,
    )

    # Assert
    assert result.transaction_id is not None
    assert isinstance(result.transaction_id, str)
    assert len(result.transaction_id) > 0


# =============================================================================
# Verify Payment Tests (Future Implementation)
# =============================================================================


def test_verify_payment_raises_not_implemented(payment_service):
    """
    Test that verify_payment raises NotImplementedError (Phase 5).
    """
    # Act & Assert
    with pytest.raises(NotImplementedError, match="Phase 5, Epic 5.4"):
        payment_service.verify_payment(transaction_id="txn_12345")


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_charge_registration_fee_handles_zero_amount(
    payment_service, mock_event_bus
):
    """
    Test that charge_registration_fee handles zero amount gracefully.
    """
    # Arrange
    user_id = 50
    tournament_id = 100
    amount = 0

    # Act
    result = payment_service.charge_registration_fee(
        user_id=user_id,
        tournament_id=tournament_id,
        amount=amount,
    )

    # Assert - should succeed (free tournament)
    assert result.success is True


def test_refund_registration_fee_handles_zero_amount(
    payment_service, mock_event_bus
):
    """
    Test that refund_registration_fee handles zero amount gracefully.
    """
    # Arrange
    user_id = 50
    tournament_id = 100
    amount = 0

    # Act
    result = payment_service.refund_registration_fee(
        user_id=user_id,
        tournament_id=tournament_id,
        amount=amount,
    )

    # Assert - should succeed (no refund needed)
    assert result.success is True
