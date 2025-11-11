"""
Module 7.2 - DeltaCoin Shop: Authorize, Capture, Release Tests

Tests the spend authorization pipeline:
- authorize_spend(): Create reservation hold
- capture(): Convert hold to debit transaction
- release(): Void hold without debit

Coverage:
- Happy paths (authorize → capture, authorize → release)
- State machine enforcement (invalid transitions raise exceptions)
- Idempotency (replay returns original, cross-op collision)
- Expiry handling (expired holds cannot capture)
- Available balance reduction with multiple holds
"""

import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestAuthorizeSpend:
    """Test authorize_spend() function - creates reservation holds."""

    def test_authorize_creates_hold_with_correct_status(self, funded_wallet):
        """Authorize creates ReservationHold with status='authorized'."""
        from apps.shop.services import authorize_spend

        result = authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('50.00'),
            sku='TEST_ITEM',
            idempotency_key='auth_001'
        )

        assert result['status'] == 'authorized'
        assert result['wallet_id'] == funded_wallet.id
        assert result['amount'] == Decimal('50.00')
        assert result['sku'] == 'TEST_ITEM'
        assert 'hold_id' in result
        assert 'expires_at' in result

    
    def test_authorize_reduces_available_balance(self, funded_wallet):
        """Authorize reduces available balance by hold amount."""
        from apps.shop.services import authorize_spend, get_available_balance

        initial_available = get_available_balance(funded_wallet)
        assert initial_available == Decimal('1000.00')

        authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('100.00'),
            sku='TEST_ITEM',
            idempotency_key='auth_002'
        )

        available_after = get_available_balance(funded_wallet)
        assert available_after == Decimal('900.00')

    
    def test_authorize_insufficient_funds_raises(self, funded_wallet):
        """Authorize with amount > available balance raises InsufficientFunds."""
        from apps.shop.services import authorize_spend
        from apps.economy.exceptions import InsufficientFunds

        with pytest.raises(InsufficientFunds):
            authorize_spend(
                wallet=funded_wallet,
                amount=Decimal('2000.00'),  # > balance
                sku='EXPENSIVE_ITEM',
                idempotency_key='auth_003'
            )

    
    def test_authorize_zero_amount_raises(self, funded_wallet):
        """Authorize with amount <= 0 raises InvalidAmount."""
        from apps.shop.services import authorize_spend
        from apps.economy.exceptions import InvalidAmount

        with pytest.raises(InvalidAmount):
            authorize_spend(
                wallet=funded_wallet,
                amount=Decimal('0.00'),
                sku='FREE_ITEM',
                idempotency_key='auth_004'
            )

    
    def test_authorize_idempotency_replay_returns_original(self, funded_wallet):
        """Replay of authorize with same key returns original hold."""
        from apps.shop.services import authorize_spend

        result1 = authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('75.00'),
            sku='REPLAY_ITEM',
            idempotency_key='auth_005'
        )

        result2 = authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('75.00'),  # Same payload
            sku='REPLAY_ITEM',
            idempotency_key='auth_005'  # Same key
        )

        assert result1['hold_id'] == result2['hold_id']
        assert result1['amount'] == result2['amount']

    
    def test_authorize_cross_op_collision_raises(self, funded_wallet):
        """Reusing key for different operation raises IdempotencyConflict."""
        from apps.shop.services import authorize_spend
        from apps.economy.exceptions import IdempotencyConflict

        # First authorize
        authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('50.00'),
            sku='ITEM_A',
            idempotency_key='collision_key'
        )

        # Try to authorize different item with same key
        with pytest.raises(IdempotencyConflict):
            authorize_spend(
                wallet=funded_wallet,
                amount=Decimal('50.00'),
                sku='ITEM_B',  # Different SKU
                idempotency_key='collision_key'
            )

    
    def test_hold_expiry_timestamp_correct(self, funded_wallet):
        """Hold expires_at is set to now + expires_in."""
        from apps.shop.services import authorize_spend

        before = timezone.now()
        result = authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('25.00'),
            sku='TIMED_ITEM',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        after = timezone.now()

        expires_at = result['expires_at']
        expected_min = before + timedelta(minutes=10)
        expected_max = after + timedelta(minutes=10)

        assert expected_min <= expires_at <= expected_max

    
    def test_multiple_holds_reduce_available_balance(self, funded_wallet):
        """Multiple active holds correctly reduce available balance."""
        from apps.shop.services import authorize_spend, get_available_balance

        # Create 3 holds
        authorize_spend(funded_wallet, Decimal('100.00'), 'ITEM_1', idempotency_key='multi_1')
        authorize_spend(funded_wallet, Decimal('150.00'), 'ITEM_2', idempotency_key='multi_2')
        authorize_spend(funded_wallet, Decimal('250.00'), 'ITEM_3', idempotency_key='multi_3')

        available = get_available_balance(funded_wallet)
        assert available == Decimal('500.00')  # 1000 - (100 + 150 + 250)


@pytest.mark.django_db
class TestCapture:
    """Test capture() function - converts hold to debit transaction."""

    
    def test_capture_creates_debit_transaction(self, funded_wallet):
        """Capture creates a debit transaction for hold amount."""
        from apps.shop.services import authorize_spend, capture
        from apps.economy.models import DeltaCrownTransaction

        # Create hold first
        auth_result = authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('200.00'),
            sku='CAPTURE_ITEM',
            idempotency_key='auth_for_capture'
        )
        authorized_hold = auth_result['hold_id']

        initial_txn_count = DeltaCrownTransaction.objects.filter(wallet=funded_wallet).count()

        result = capture(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='cap_001'
        )

        final_txn_count = DeltaCrownTransaction.objects.filter(wallet=funded_wallet).count()
        assert final_txn_count == initial_txn_count + 1
        assert 'transaction_id' in result

    
    def test_capture_transitions_hold_to_captured(self, funded_wallet, authorized_hold):
        """Capture transitions hold status from 'authorized' to 'captured'."""
        from apps.shop.services import capture
        from apps.shop.models import ReservationHold

        capture(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='cap_002'
        )

        hold = ReservationHold.objects.get(id=authorized_hold)
        assert hold.status == 'captured'

    
    def test_capture_updates_wallet_balance(self, funded_wallet, authorized_hold):
        """Capture reduces wallet balance by hold amount."""
        from apps.shop.services import capture

        initial_balance = funded_wallet.cached_balance

        result = capture(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='cap_003'
        )

        funded_wallet.refresh_from_db()
        assert funded_wallet.cached_balance == initial_balance - Decimal('200.00')
        assert result['balance_after'] == funded_wallet.cached_balance

    
    def test_capture_idempotency_replay_returns_original(self, funded_wallet, authorized_hold):
        """Replay of capture with same key returns original transaction."""
        from apps.shop.services import capture

        result1 = capture(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='cap_004'
        )

        result2 = capture(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='cap_004'  # Same key
        )

        assert result1['transaction_id'] == result2['transaction_id']
        assert result1['hold_id'] == result2['hold_id']

    
    def test_capture_expired_hold_raises(self, funded_wallet):
        """Capture on expired hold raises HoldExpired."""
        from apps.shop.services import authorize_spend, capture
        from apps.shop.exceptions import HoldExpired
        from unittest.mock import patch

        # Create hold with 1 second expiry
        result = authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('50.00'),
            sku='EXPIRED_ITEM',
            expires_at=timezone.now() + timedelta(seconds=1),
            idempotency_key='auth_expired'
        )

        # Mock time passing (or sleep for 2 seconds in real test)
        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = timezone.now() + timedelta(seconds=5)
            
            with pytest.raises(HoldExpired):
                capture(
                    wallet=funded_wallet,
                    authorization_id=result['hold_id'],
                    idempotency_key='cap_expired'
                )

    
    def test_capture_released_hold_raises(self, funded_wallet):
        """Capture on released hold raises InvalidStateTransition."""
        from apps.shop.services import authorize_spend, release, capture
        from apps.shop.exceptions import InvalidStateTransition

        # Authorize and release
        auth_result = authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('75.00'),
            sku='RELEASED_ITEM',
            idempotency_key='auth_released'
        )

        release(
            wallet=funded_wallet,
            authorization_id=auth_result['hold_id'],
            idempotency_key='rel_released'
        )

        # Try to capture released hold
        with pytest.raises(InvalidStateTransition):
            capture(
                wallet=funded_wallet,
                authorization_id=auth_result['hold_id'],
                idempotency_key='cap_released'
            )

    
    def test_capture_already_captured_hold_idempotent(self, funded_wallet, authorized_hold):
        """Capture on already-captured hold returns original (idempotent)."""
        from apps.shop.services import capture

        # First capture
        result1 = capture(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='cap_double'
        )

        # Second capture with same key (idempotent replay)
        result2 = capture(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='cap_double'
        )

        assert result1['transaction_id'] == result2['transaction_id']


@pytest.mark.django_db
class TestRelease:
    """Test release() function - voids hold without debit."""

    
    def test_release_transitions_hold_to_released(self, funded_wallet, authorized_hold):
        """Release transitions hold status from 'authorized' to 'released'."""
        from apps.shop.services import release
        from apps.shop.models import ReservationHold

        release(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='rel_001'
        )

        hold = ReservationHold.objects.get(id=authorized_hold)
        assert hold.status == 'released'

    
    def test_release_no_debit_transaction(self, funded_wallet, authorized_hold):
        """Release does not create any transaction (no debit)."""
        from apps.shop.services import release
        from apps.economy.models import DeltaCrownTransaction

        initial_txn_count = DeltaCrownTransaction.objects.filter(wallet=funded_wallet).count()

        release(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='rel_002'
        )

        final_txn_count = DeltaCrownTransaction.objects.filter(wallet=funded_wallet).count()
        assert final_txn_count == initial_txn_count  # No new transaction

    
    def test_release_increases_available_balance(self, funded_wallet, authorized_hold):
        """Release increases available balance by restoring hold amount."""
        from apps.shop.services import release, get_available_balance

        # Available balance reduced by hold
        available_before = get_available_balance(funded_wallet)
        assert available_before == Decimal('850.00')  # 1000 - 150

        release(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='rel_003'
        )

        available_after = get_available_balance(funded_wallet)
        assert available_after == Decimal('1000.00')  # Hold released

    
    def test_release_idempotency_replay_returns_original(self, funded_wallet, authorized_hold):
        """Replay of release with same key returns original result."""
        from apps.shop.services import release

        result1 = release(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='rel_004'
        )

        result2 = release(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='rel_004'  # Same key
        )

        assert result1['hold_id'] == result2['hold_id']
        assert 'released_at' in result1
        assert result1['released_at'] == result2['released_at']

    
    def test_release_captured_hold_raises(self, funded_wallet):
        """Release on captured hold raises InvalidStateTransition."""
        from apps.shop.services import authorize_spend, capture, release
        from apps.shop.exceptions import InvalidStateTransition

        # Authorize and capture
        auth_result = authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('100.00'),
            sku='CAPTURED_ITEM',
            idempotency_key='auth_captured'
        )

        capture(
            wallet=funded_wallet,
            authorization_id=auth_result['hold_id'],
            idempotency_key='cap_captured'
        )

        # Try to release captured hold
        with pytest.raises(InvalidStateTransition):
            release(
                wallet=funded_wallet,
                authorization_id=auth_result['hold_id'],
                idempotency_key='rel_captured'
            )

    
    def test_release_expired_hold_succeeds(self, funded_wallet):
        """Release on expired hold succeeds (idempotent no-op)."""
        from apps.shop.services import authorize_spend, release
        from unittest.mock import patch

        # Create hold with 1 second expiry
        result = authorize_spend(
            wallet=funded_wallet,
            amount=Decimal('50.00'),
            sku='EXPIRED_REL_ITEM',
            expires_at=timezone.now() + timedelta(seconds=1),
            idempotency_key='auth_expired_rel'
        )

        # Mock time passing
        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = timezone.now() + timedelta(seconds=5)
            
            # Release should succeed (no-op on expired hold)
            result_rel = release(
                wallet=funded_wallet,
                authorization_id=result['hold_id'],
                idempotency_key='rel_expired_hold'
            )

            assert 'released_at' in result_rel

    
    def test_capture_then_release_fails(self, funded_wallet, authorized_hold):
        """Cannot release after capture (terminal state)."""
        from apps.shop.services import capture, release
        from apps.shop.exceptions import InvalidStateTransition

        # Capture first
        capture(
            wallet=funded_wallet,
            authorization_id=authorized_hold,
            idempotency_key='cap_first'
        )

        # Try to release after capture
        with pytest.raises(InvalidStateTransition):
            release(
                wallet=funded_wallet,
                authorization_id=authorized_hold,
                idempotency_key='rel_after_cap'
            )
