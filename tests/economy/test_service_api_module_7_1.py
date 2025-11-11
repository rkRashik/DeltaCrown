"""
Test: Service API (Module 7.1 - Step 1: Test Scaffolding)

Implements: MODULE_7.1_KICKOFF.md - Service Layer Enhancement
Coverage Target: ≥90%

Tests credit(), debit(), transfer(), get_balance(), get_transaction_history() API.
"""
# Implements: Documents/ExecutionPlan/MODULE_7.1_KICKOFF.md

import pytest
from decimal import Decimal
from django.db import transaction
from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.user_profile.models import UserProfile


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def user_profile_factory(db):
    """Factory to create UserProfile instances for testing."""
    def _create():
        from django.contrib.auth import get_user_model
        User = get_user_model()
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create_user(
            username=f"testuser_{unique_id}",
            email=f"test{unique_id}@example.com"
        )
        # UserProfile is auto-created by signal - fetch it
        return UserProfile.objects.get(user=user)
    
    return _create


# ============================================================================
# Test Class: credit() API
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestCreditAPI:
    """
    Test: credit(profile, amount, reason, idempotency_key=None, **kwargs)
    
    Atomically credits coins to wallet. Creates wallet if missing.
    Returns: (wallet, transaction) tuple
    """
    
    def test_credit_increases_balance(self, user_profile_factory):
        """
        Test: credit() increases wallet balance and creates transaction.
        
        Target: apps/economy/services.py - credit()
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # Credit 100 coins
        res = services.credit(
            profile=profile,
            amount=100,
            reason=DeltaCrownTransaction.Reason.WINNER
        )

        # Assert: Wallet created with balance 100
        wallet = DeltaCrownWallet.objects.get(pk=res["wallet_id"])
        assert wallet.cached_balance == 100

        # Assert: Transaction created
        txn = DeltaCrownTransaction.objects.get(pk=res["transaction_id"])
        assert txn.wallet_id == wallet.id
        assert txn.amount == 100
        assert txn.reason == DeltaCrownTransaction.Reason.WINNER

        # Credit another 50 coins
        res2 = services.credit(
            profile=profile,
            amount=50,
            reason=DeltaCrownTransaction.Reason.PARTICIPATION
        )

        wallet.refresh_from_db()
        assert wallet.cached_balance == 150
    
    def test_credit_zero_raises(self, user_profile_factory):
        """
        Test: credit() with amount=0 raises InvalidAmount exception.
        
        Target: Input validation for credit()
        """
        from apps.economy import services
        from apps.economy.exceptions import InvalidAmount
        
        profile = user_profile_factory()
        
        with pytest.raises(InvalidAmount):
            services.credit(profile=profile, amount=0, reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST)
    
    def test_credit_negative_raises(self, user_profile_factory):
        """
        Test: credit() with negative amount raises InvalidAmount exception.
        
        Target: Input validation (use debit() for negative amounts)
        """
        from apps.economy import services
        from apps.economy.exceptions import InvalidAmount
        
        profile = user_profile_factory()
        
        with pytest.raises(InvalidAmount):
            services.credit(profile=profile, amount=-50, reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST)


# ============================================================================
# Test Class: debit() API
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestDebitAPI:
    """
    Test: debit(profile, amount, reason, idempotency_key=None, **kwargs)
    
    Atomically debits coins from wallet. Raises InsufficientFunds if overdraft not allowed.
    Returns: (wallet, transaction) tuple
    """
    
    def test_debit_decreases_balance(self, user_profile_factory):
        """
        Test: debit() decreases wallet balance and creates negative transaction.
        
        Target: apps/economy/services.py - debit()
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # Credit 100 coins first
        services.credit(profile=profile, amount=100, reason=DeltaCrownTransaction.Reason.WINNER)

        # Debit 30 coins
        res = services.debit(
            profile=profile,
            amount=30,
            reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT
        )

        wallet = DeltaCrownWallet.objects.get(pk=res["wallet_id"])
        # Assert: Balance reduced to 70
        assert wallet.cached_balance == 70

        txn = DeltaCrownTransaction.objects.get(pk=res["transaction_id"])
        assert txn.amount == -30
        assert txn.reason == DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT
    
    def test_debit_insufficient_funds_raises(self, user_profile_factory):
        """
        Test: debit() beyond balance raises InsufficientFunds exception.
        
        Target: Overdraft protection in debit()
        """
        from apps.economy import services
        from apps.economy.exceptions import InsufficientFunds
        
        profile = user_profile_factory()
        
        # Credit 50 coins
        services.credit(profile=profile, amount=50, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        
        # Attempt to debit 100 coins (insufficient)
        with pytest.raises(InsufficientFunds):
            services.debit(profile=profile, amount=100, reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT)

        # Balance unchanged
        wallet = DeltaCrownWallet.objects.get(profile=profile)
        assert wallet.cached_balance == 50
    
    def test_debit_zero_raises(self, user_profile_factory):
        """
        Test: debit() with amount=0 raises InvalidAmount exception.
        
        Target: Input validation for debit()
        """
        from apps.economy import services
        from apps.economy.exceptions import InvalidAmount
        
        profile = user_profile_factory()
        services.credit(profile=profile, amount=100, reason=DeltaCrownTransaction.Reason.WINNER)
        
        with pytest.raises(InvalidAmount):
            services.debit(profile=profile, amount=0, reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST)


# ============================================================================
# Test Class: transfer() API
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestTransferAPI:
    """
    Test: transfer(from_profile, to_profile, amount, reason, idempotency_key=None, **kwargs)
    
    Atomically transfers coins between wallets. Creates both debit and credit transactions.
    Returns: (from_wallet, to_wallet, debit_txn, credit_txn) tuple
    """
    
    def test_transfer_atomic(self, user_profile_factory):
        """
        Test: transfer() atomically moves coins from one wallet to another.
        
        Target: apps/economy/services.py - transfer()
        """
        from apps.economy import services
        
        profile_a = user_profile_factory()
        profile_b = user_profile_factory()
        
        # Credit profile_a with 200 coins
        services.credit(profile=profile_a, amount=200, reason=DeltaCrownTransaction.Reason.WINNER)
        
        # Transfer 75 coins from A to B
        res = services.transfer(
            from_profile=profile_a,
            to_profile=profile_b,
            amount=75,
            reason=DeltaCrownTransaction.Reason.P2P_TRANSFER
        )

        from_wallet = DeltaCrownWallet.objects.get(pk=res["from_wallet_id"])
        to_wallet = DeltaCrownWallet.objects.get(pk=res["to_wallet_id"])

        # Assert: from_wallet reduced by 75
        assert from_wallet.cached_balance == 125

        # Assert: to_wallet increased by 75
        assert to_wallet.cached_balance == 75

        debit_txn = DeltaCrownTransaction.objects.get(pk=res["debit_transaction_id"])
        credit_txn = DeltaCrownTransaction.objects.get(pk=res["credit_transaction_id"])
        assert debit_txn.amount == -75
        assert credit_txn.amount == 75
        assert debit_txn.wallet_id == from_wallet.id
        assert credit_txn.wallet_id == to_wallet.id
    
    def test_transfer_insufficient_funds_rollback(self, user_profile_factory):
        """
        Test: transfer() with insufficient funds rolls back entire transaction.
        
        Target: Atomicity guarantee (no partial transfers)
        """
        from apps.economy import services
        from apps.economy.exceptions import InsufficientFunds
        
        profile_a = user_profile_factory()
        profile_b = user_profile_factory()
        
        # Credit profile_a with 50 coins
        services.credit(profile=profile_a, amount=50, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        
        # Attempt to transfer 100 coins (insufficient)
        with pytest.raises(InsufficientFunds):
            services.transfer(
                from_profile=profile_a,
                to_profile=profile_b,
                amount=100,
                reason=DeltaCrownTransaction.Reason.P2P_TRANSFER
            )
        
        # Assert: No balances changed (rollback successful)
        wallet_a = DeltaCrownWallet.objects.get(profile=profile_a)
        assert wallet_a.cached_balance == 50
        
        # Assert: profile_b has no wallet (transfer failed)
        assert not DeltaCrownWallet.objects.filter(profile=profile_b).exists()
    
    def test_transfer_to_self_rejected(self, user_profile_factory):
        """
        Test: transfer() to same wallet raises InvalidWallet exception.
        
        Target: Self-transfer prevention
        """
        from apps.economy import services
        from apps.economy.exceptions import InvalidWallet
        
        profile = user_profile_factory()
        services.credit(profile=profile, amount=100, reason=DeltaCrownTransaction.Reason.WINNER)
        
        # Attempt to transfer to self
        with pytest.raises(InvalidWallet):
            services.transfer(
                from_profile=profile,
                to_profile=profile,
                amount=50,
                reason=DeltaCrownTransaction.Reason.P2P_TRANSFER
            )


# ============================================================================
# Test Class: get_balance() API
# ============================================================================

@pytest.mark.django_db
class TestGetBalanceAPI:
    """
    Test: get_balance(profile) -> int
    
    Fast cached balance retrieval. Returns 0 if wallet doesn't exist.
    """
    
    def test_get_balance_from_cache(self, user_profile_factory):
        """
        Test: get_balance() returns cached_balance without hitting ledger.
        
        Target: apps/economy/services.py - get_balance()
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # New profile has zero balance
        balance = services.get_balance(profile)
        assert balance == 0
        
        # Credit 150 coins
        services.credit(profile=profile, amount=150, reason=DeltaCrownTransaction.Reason.WINNER)
        
        # Get balance (should use cache)
        balance = services.get_balance(profile)
        assert balance == 150
    
    def test_get_balance_missing_wallet_returns_zero(self, user_profile_factory):
        """
        Test: get_balance() for profile without wallet returns 0 (no error).
        
        Target: Graceful handling of missing wallets
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # No wallet exists yet
        assert not DeltaCrownWallet.objects.filter(profile=profile).exists()
        
        # get_balance should return 0 (not raise exception)
        balance = services.get_balance(profile)
        assert balance == 0


# ============================================================================
# Test Class: get_transaction_history() API
# ============================================================================

@pytest.mark.django_db
class TestGetTransactionHistoryAPI:
    """
    Test: get_transaction_history(profile, limit=50, offset=0) -> QuerySet
    
    Returns paginated transaction history ordered by created_at DESC.
    """
    
    def test_get_history_paginated(self, user_profile_factory):
        """
        Test: get_transaction_history() returns paginated results.
        
        Target: apps/economy/services.py - get_transaction_history()
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # Create 10 transactions
        for i in range(10):
            services.credit(profile=profile, amount=10 * (i + 1), reason=DeltaCrownTransaction.Reason.PARTICIPATION)

        # Get first 5 transactions (most recent)
        history = services.get_transaction_history(profile, limit=5, offset=0)
        assert len(history) == 5

        # Most recent should be the last created (amount=100)
        assert history[0]["amount"] == 100

        # Get next 5 transactions
        history_page2 = services.get_transaction_history(profile, limit=5, offset=5)
        assert len(history_page2) == 5
        assert history_page2[0]["amount"] == 50
    
    def test_get_history_empty_wallet(self, user_profile_factory):
        """
        Test: get_transaction_history() for wallet with no transactions returns empty QuerySet.
        
        Target: Edge case handling
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # No transactions yet
        history = services.get_transaction_history(profile)
        assert len(history) == 0
    
    def test_get_history_ordered_desc(self, user_profile_factory):
        """
        Test: get_transaction_history() returns transactions in DESC order (newest first).
        
        Target: Ordering by created_at DESC
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # Create 3 transactions
        txn1 = services.credit(profile=profile, amount=10, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        txn2 = services.credit(profile=profile, amount=20, reason=DeltaCrownTransaction.Reason.WINNER)
        txn3 = services.credit(profile=profile, amount=30, reason=DeltaCrownTransaction.Reason.PARTICIPATION)

        # Get history
        history = services.get_transaction_history(profile)

        # Assert: Newest first
        assert history[0]["id"] == txn3["transaction_id"]
        assert history[1]["id"] == txn2["transaction_id"]
        assert history[2]["id"] == txn1["transaction_id"]


# ============================================================================
# Module Metadata
# ============================================================================

# Test count: 15 tests (all xfail pending implementation)
# Coverage target: ≥90% on apps/economy/services.py
# Target files: apps/economy/services.py (credit, debit, transfer, get_balance, get_transaction_history)
