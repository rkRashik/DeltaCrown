"""
Module 7.2 - DeltaCoin Shop: Refund Tests

Tests the refund service:
- refund(): Create compensating credit for captured transaction
- Partial refund support
- Double-refund prevention via idempotency
- Refund amount validation

Coverage:
- Full refunds (amount = original)
- Partial refunds (amount < original)
- Invalid refunds (amount > original, non-purchase transaction)
- Idempotency (replay returns original, multiple partial refunds)
"""

import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestRefund:
    """Test refund() function - compensating credits for purchases."""

    
    def test_refund_creates_credit_transaction(self, funded_wallet, captured_transaction):
        """Refund creates a compensating credit transaction."""
        from apps.shop.services import refund
        from apps.economy.models import DeltaCrownTransaction

        initial_txn_count = DeltaCrownTransaction.objects.filter(wallet=funded_wallet).count()

        result = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=Decimal('300.00'),
            idempotency_key='refund_001'
        )

        final_txn_count = DeltaCrownTransaction.objects.filter(wallet=funded_wallet).count()
        assert final_txn_count == initial_txn_count + 1
        assert 'refund_transaction_id' in result

    
    def test_refund_full_amount(self, funded_wallet, captured_transaction):
        """Full refund restores original amount to wallet."""
        from apps.shop.services import refund

        balance_before = funded_wallet.cached_balance

        result = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=Decimal('300.00'),  # Full amount
            idempotency_key='refund_full'
        )

        funded_wallet.refresh_from_db()
        assert funded_wallet.cached_balance == balance_before + Decimal('300.00')
        assert result['balance_after'] == funded_wallet.cached_balance

    
    def test_refund_partial_amount(self, funded_wallet, captured_transaction):
        """Partial refund restores partial amount to wallet."""
        from apps.shop.services import refund

        balance_before = funded_wallet.cached_balance

        result = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=Decimal('150.00'),  # Half of original 300
            idempotency_key='refund_partial'
        )

        funded_wallet.refresh_from_db()
        assert funded_wallet.cached_balance == balance_before + Decimal('150.00')
        assert result['balance_after'] == funded_wallet.cached_balance

    
    def test_refund_amount_exceeds_original_raises(self, funded_wallet, captured_transaction):
        """Refund amount > original transaction raises InvalidAmount."""
        from apps.shop.services import refund
        from apps.economy.exceptions import InvalidAmount

        with pytest.raises(InvalidAmount):
            refund(
                wallet=funded_wallet,
                capture_txn_id=captured_transaction,
                amount=Decimal('500.00'),  # > original 300
                idempotency_key='refund_exceed'
            )

    
    def test_refund_non_purchase_transaction_raises(self, funded_wallet):
        """Refund on non-purchase transaction raises InvalidTransaction."""
        from apps.shop.services import refund
        from apps.shop.exceptions import InvalidTransaction
        from apps.economy.services import credit

        # Create a non-purchase credit transaction
        credit_result = credit(
            wallet=funded_wallet,
            amount=Decimal('100.00'),
            reason='MANUAL_ADJUST',
            idempotency_key='non_purchase_txn'
        )

        with pytest.raises(InvalidTransaction):
            refund(
                wallet=funded_wallet,
                transaction_id=credit_result['transaction_id'],
                amount=Decimal('50.00'),
                idempotency_key='refund_non_purchase'
            )

    
    def test_refund_idempotency_replay_returns_original(self, funded_wallet, captured_transaction):
        """Replay of refund with same key returns original credit transaction."""
        from apps.shop.services import refund

        result1 = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=Decimal('100.00'),
            idempotency_key='refund_idem'
        )

        result2 = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=Decimal('100.00'),  # Same amount
            idempotency_key='refund_idem'  # Same key
        )

        assert result1['refund_transaction_id'] == result2['refund_transaction_id']
        assert result1['balance_after'] == result2['balance_after']

    
    def test_double_refund_with_different_key_succeeds(self, funded_wallet, captured_transaction):
        """Multiple partial refunds with different keys succeed (up to original amount)."""
        from apps.shop.services import refund

        # First partial refund
        refund1 = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=Decimal('100.00'),
            idempotency_key='refund_part1'
        )

        # Second partial refund (different key)
        refund2 = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=Decimal('100.00'),
            idempotency_key='refund_part2'
        )

        assert refund1['refund_transaction_id'] != refund2['refund_transaction_id']

        # Third refund exceeding total should raise
        from apps.economy.exceptions import InvalidAmount
        with pytest.raises(InvalidAmount):
            refund(
                wallet=funded_wallet,
                capture_txn_id=captured_transaction,
                amount=Decimal('200.00'),  # Total would be 400 > original 300
                idempotency_key='refund_part3'
            )

    
    def test_refund_updates_wallet_balance(self, funded_wallet, captured_transaction):
        """Refund correctly updates wallet cached_balance."""
        from apps.shop.services import refund

        # Balance after capture: 1000 - 300 = 700
        assert funded_wallet.cached_balance == Decimal('700.00')

        refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=Decimal('300.00'),
            idempotency_key='refund_balance_check'
        )

        funded_wallet.refresh_from_db()
        assert funded_wallet.cached_balance == Decimal('1000.00')  # Fully refunded
