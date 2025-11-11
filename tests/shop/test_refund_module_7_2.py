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
            amount=200,  # Fixture captures 200, can't refund more
            idempotency_key='refund_001'
        )

        final_txn_count = DeltaCrownTransaction.objects.filter(wallet=funded_wallet).count()
        assert final_txn_count == initial_txn_count + 1
        assert 'refund_transaction_id' in result

    
    def test_refund_full_amount(self, funded_wallet, captured_transaction):
        """Full refund restores original amount to wallet."""
        from apps.shop.services import refund

        # Refresh to get balance after captured_transaction fixture ran
        funded_wallet.refresh_from_db()
        balance_before = funded_wallet.cached_balance  # Should be 800 (1000 - 200)

        result = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=200,  # Full amount (fixture captures 200)
            idempotency_key='refund_full'
        )

        funded_wallet.refresh_from_db()
        assert funded_wallet.cached_balance == balance_before + 200  # Back to 1000
        assert result['balance_after'] == funded_wallet.cached_balance

    
    def test_refund_partial_amount(self, funded_wallet, captured_transaction):
        """Partial refund restores partial amount to wallet."""
        from apps.shop.services import refund

        # Refresh to get balance after captured_transaction fixture ran
        funded_wallet.refresh_from_db()
        balance_before = funded_wallet.cached_balance  # Should be 800 (1000 - 200)

        result = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=150,  # Partial refund
            idempotency_key='refund_partial'
        )

        funded_wallet.refresh_from_db()
        assert funded_wallet.cached_balance == balance_before + 150  # 800 + 150 = 950
        assert result['balance_after'] == funded_wallet.cached_balance

    
    def test_refund_amount_exceeds_original_raises(self, funded_wallet, captured_transaction):
        """Refund amount > original transaction raises InvalidAmount."""
        from apps.shop.services import refund
        from apps.shop.exceptions import InvalidAmount

        with pytest.raises(InvalidAmount):
            refund(
                wallet=funded_wallet,
                capture_txn_id=captured_transaction,
                amount=500,  # > original 300
                idempotency_key='refund_exceed'
            )

    
    def test_refund_non_purchase_transaction_raises(self, funded_wallet):
        """Refund on non-purchase transaction raises InvalidTransaction."""
        from apps.shop.services import refund
        from apps.shop.exceptions import InvalidTransaction
        from apps.economy.services import credit

        # Create a non-purchase credit transaction
        credit_result = credit(
            profile=funded_wallet.profile,
            amount=100,
            reason='MANUAL_ADJUST',
            idempotency_key='non_purchase_txn'
        )

        with pytest.raises(InvalidTransaction):
            refund(
                wallet=funded_wallet,
                capture_txn_id=credit_result['transaction_id'],
                amount=50,
                idempotency_key='refund_non_purchase'
            )

    
    def test_refund_idempotency_replay_returns_original(self, funded_wallet, captured_transaction):
        """Replay of refund with same key returns original credit transaction."""
        from apps.shop.services import refund

        result1 = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=100,
            idempotency_key='refund_idem'
        )

        result2 = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=100,  # Same amount
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
            amount=100,
            idempotency_key='refund_part1'
        )

        # Second partial refund (different key)
        refund2 = refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=100,
            idempotency_key='refund_part2'
        )

        assert refund1['refund_transaction_id'] != refund2['refund_transaction_id']

        # Third refund exceeding total should raise (captured_transaction is 200)
        from apps.shop.exceptions import InvalidAmount
        with pytest.raises(InvalidAmount):
            refund(
                wallet=funded_wallet,
                capture_txn_id=captured_transaction,
                amount=1,  # Total would be 201 > original 200
                idempotency_key='refund_part3'
            )

    
    def test_refund_updates_wallet_balance(self, funded_wallet, captured_transaction):
        """Refund correctly updates wallet cached_balance."""
        from apps.shop.services import refund

        # Refresh to get balance after captured_transaction fixture ran
        funded_wallet.refresh_from_db()
        # Balance after capture: 1000 - 200 = 800 (captured_transaction fixture is 200)
        assert funded_wallet.cached_balance == 800

        refund(
            wallet=funded_wallet,
            capture_txn_id=captured_transaction,
            amount=200,
            idempotency_key='refund_balance_check'
        )

        funded_wallet.refresh_from_db()
        assert funded_wallet.cached_balance == 1000  # Fully refunded
