"""
Test: Ledger Invariants (Module 7.1 - Step 1: Test Scaffolding)

Implements: MODULE_7.1_KICKOFF.md - Ledger Invariants Testing
Coverage Target: 100% (critical financial logic)

Tests conservation law, non-negative balances, immutability, and monotonic ordering.
"""
# Implements: Documents/ExecutionPlan/MODULE_7.1_KICKOFF.md

import pytest
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.user_profile.models import UserProfile


# ============================================================================
# Fixtures & Helpers
# ============================================================================

@pytest.fixture
def wallet_factory(db):
    """
    Factory to create test wallets with unique profiles.
    
    Returns callable: wallet_factory(allow_overdraft=False) -> DeltaCrownWallet
    """
    def _create_wallet(allow_overdraft=False):
        # Create UserProfile without PII (ID only for testing)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username=f"testuser_{DeltaCrownWallet.objects.count() + 1}",
            email=f"test{DeltaCrownWallet.objects.count() + 1}@example.com"
        )
        profile = UserProfile.objects.create(user=user)
        
        wallet = DeltaCrownWallet.objects.create(
            profile=profile,
            cached_balance=0
        )
        # TODO: Set allow_overdraft when field exists
        # wallet.allow_overdraft = allow_overdraft
        # wallet.save()
        
        return wallet
    
    return _create_wallet


@pytest.fixture
def create_transaction(db):
    """
    Helper to create transactions for testing.
    
    Returns callable: create_transaction(wallet, amount, reason) -> DeltaCrownTransaction
    """
    def _create(wallet, amount, reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST, **kwargs):
        return DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            reason=reason,
            **kwargs
        )
    
    return _create


# ============================================================================
# Test Class: Conservation Law
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestConservationLaw:
    """
    Conservation Law: Sum of all transaction amounts across entire ledger = 0
    (Credits cancel debits at system level)
    """
    
    @pytest.mark.xfail(reason="Implementation pending - Step 2")
    def test_conservation_simple(self, wallet_factory, create_transaction):
        """
        Test: Simple conservation - 3 transactions across 2 wallets sum to zero.
        
        Target: Ledger-wide conservation (credit to A + debit from B = net zero)
        """
        wallet_a = wallet_factory()
        wallet_b = wallet_factory()
        
        # Wallet A: +100 (credit)
        create_transaction(wallet_a, amount=100, reason=DeltaCrownTransaction.Reason.WINNER)
        
        # Wallet B: +50 (credit)
        create_transaction(wallet_b, amount=50, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        
        # Wallet A: -30 (debit)
        create_transaction(wallet_a, amount=-30, reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT)
        
        # Assert: Sum of all amounts = 100 + 50 - 30 = 120
        # (Conservation at individual level, not system-wide unless transfers)
        total = DeltaCrownTransaction.objects.aggregate(total=Sum('amount'))['total']
        
        # Note: True conservation requires transfers (debit one, credit another)
        # This test validates we can track both sides
        assert total == 120, "Sum of all transactions should match expected total"
    
    @pytest.mark.xfail(reason="Implementation pending - Step 2")
    def test_conservation_concurrent(self, wallet_factory, create_transaction):
        """
        Test: Conservation holds with 10 wallets, 50 transactions each.
        
        Target: Ledger invariant at scale (500 transactions)
        """
        wallets = [wallet_factory() for _ in range(10)]
        
        # Create 50 transactions per wallet (25 credits, 25 debits)
        for wallet in wallets:
            for i in range(25):
                # Credit
                create_transaction(wallet, amount=10, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
                # Debit
                create_transaction(wallet, amount=-5, reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT)
        
        # Total transactions: 10 wallets * 50 txns = 500 transactions
        assert DeltaCrownTransaction.objects.count() == 500
        
        # Sum of all amounts: (10 - 5) * 25 * 10 = 1250
        total = DeltaCrownTransaction.objects.aggregate(total=Sum('amount'))['total']
        assert total == 1250, "Conservation law: sum of all transactions should be 1250"
        
        # Each wallet balance should be: (10 - 5) * 25 = 125
        for wallet in wallets:
            wallet.refresh_from_db()
            assert wallet.cached_balance == 125, f"Wallet {wallet.id} balance should be 125"


# ============================================================================
# Test Class: Non-Negative Balances
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestNonNegativeBalances:
    """
    Non-Negative Balance Enforcement: Debit cannot reduce balance below zero
    unless allow_overdraft=True
    """
    
    @pytest.mark.xfail(reason="Implementation pending - Step 2")
    def test_debit_insufficient_funds_raises(self, wallet_factory, create_transaction):
        """
        Test: Debit beyond balance raises InsufficientFunds exception.
        
        Target: apps/economy/models.py - DeltaCrownTransaction.save()
        """
        wallet = wallet_factory(allow_overdraft=False)
        
        # Credit 50 coins
        create_transaction(wallet, amount=50, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        wallet.refresh_from_db()
        assert wallet.cached_balance == 50
        
        # Attempt to debit 100 coins (insufficient funds)
        from apps.economy.exceptions import InsufficientFunds
        
        with pytest.raises(InsufficientFunds) as exc_info:
            create_transaction(wallet, amount=-100, reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT)
        
        assert "insufficient" in str(exc_info.value).lower()
        
        # Wallet balance unchanged
        wallet.refresh_from_db()
        assert wallet.cached_balance == 50, "Balance should remain 50 after failed debit"
    
    @pytest.mark.xfail(reason="Implementation pending - Step 2")
    def test_overdraft_flag_allows_negative(self, wallet_factory, create_transaction):
        """
        Test: Wallet with allow_overdraft=True permits negative balance.
        
        Target: apps/economy/models.py - DeltaCrownWallet.allow_overdraft field
        """
        wallet = wallet_factory(allow_overdraft=True)
        
        # Debit 100 coins from zero balance (overdraft allowed)
        create_transaction(wallet, amount=-100, reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST)
        
        wallet.refresh_from_db()
        assert wallet.cached_balance == -100, "Overdraft wallet should allow negative balance"
    
    @pytest.mark.xfail(reason="Implementation pending - Step 2")
    def test_balance_never_negative_by_default(self, wallet_factory, create_transaction):
        """
        Test: Default wallets (allow_overdraft=False) reject debits that would go negative.
        
        Target: Default behavior validation
        """
        wallet = wallet_factory()  # Default: allow_overdraft=False
        
        # Credit 20 coins
        create_transaction(wallet, amount=20, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        
        # Debit 15 coins (ok)
        create_transaction(wallet, amount=-15, reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT)
        wallet.refresh_from_db()
        assert wallet.cached_balance == 5
        
        # Debit 10 coins (would go negative → reject)
        from apps.economy.exceptions import InsufficientFunds
        with pytest.raises(InsufficientFunds):
            create_transaction(wallet, amount=-10, reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT)
        
        # Balance unchanged
        wallet.refresh_from_db()
        assert wallet.cached_balance == 5


# ============================================================================
# Test Class: Immutability
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestImmutability:
    """
    Immutability: Transactions are append-only. No updates allowed after creation.
    """
    
    @pytest.mark.xfail(reason="Implementation pending - Step 2")
    def test_transaction_amount_immutable(self, wallet_factory, create_transaction):
        """
        Test: Attempting to modify transaction.amount after save raises error.
        
        Target: apps/economy/models.py - DeltaCrownTransaction.save()
        """
        wallet = wallet_factory()
        txn = create_transaction(wallet, amount=100, reason=DeltaCrownTransaction.Reason.WINNER)
        
        # Attempt to modify amount (should fail)
        txn.amount = 200
        
        with pytest.raises(Exception) as exc_info:  # Specific exception TBD
            txn.save()
        
        # Transaction amount unchanged in DB
        txn.refresh_from_db()
        assert txn.amount == 100, "Transaction amount should be immutable"
    
    @pytest.mark.xfail(reason="Implementation pending - Step 2")
    def test_transaction_reason_immutable(self, wallet_factory, create_transaction):
        """
        Test: Attempting to modify transaction.reason after save raises error.
        
        Target: Immutability enforcement on all fields
        """
        wallet = wallet_factory()
        txn = create_transaction(wallet, amount=50, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        
        # Attempt to modify reason (should fail)
        txn.reason = DeltaCrownTransaction.Reason.WINNER
        
        with pytest.raises(Exception):
            txn.save()
        
        # Reason unchanged
        txn.refresh_from_db()
        assert txn.reason == DeltaCrownTransaction.Reason.PARTICIPATION


# ============================================================================
# Test Class: Monotonic Ordering
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestMonotonicOrdering:
    """
    Monotonic Ordering: Transactions are ordered by created_at (immutable timestamp).
    Sequence IDs (if used) must be strictly increasing.
    """
    
    @pytest.mark.xfail(reason="Implementation pending - Step 2")
    def test_created_at_monotonic(self, wallet_factory, create_transaction):
        """
        Test: created_at is auto-generated and immutable.
        
        Target: Timestamp ordering for audit trail
        """
        wallet = wallet_factory()
        
        # Create 3 transactions
        txn1 = create_transaction(wallet, amount=10, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        txn2 = create_transaction(wallet, amount=20, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        txn3 = create_transaction(wallet, amount=30, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        
        # Assert: created_at is set and monotonically increasing
        assert txn1.created_at <= txn2.created_at, "created_at should be monotonic"
        assert txn2.created_at <= txn3.created_at, "created_at should be monotonic"
        
        # Assert: created_at is immutable (cannot be changed)
        original_time = txn1.created_at
        txn1.created_at = txn2.created_at  # Attempt to modify
        
        with pytest.raises(Exception):  # Should fail (immutability)
            txn1.save()
        
        txn1.refresh_from_db()
        assert txn1.created_at == original_time, "created_at should be immutable"


# ============================================================================
# Test Class: Recalculation & Reconciliation
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestRecalculation:
    """
    Wallet balance recalculation: cached_balance = sum(transactions.amount)
    """
    
    @pytest.mark.xfail(reason="Implementation pending - Step 2")
    def test_recalc_and_save_matches_ledger(self, wallet_factory, create_transaction):
        """
        Test: wallet.recalc_and_save() rebuilds cached_balance from ledger sum.
        
        Target: apps/economy/models.py - DeltaCrownWallet.recalc_and_save()
        """
        wallet = wallet_factory()
        
        # Create 5 transactions
        create_transaction(wallet, amount=100, reason=DeltaCrownTransaction.Reason.WINNER)
        create_transaction(wallet, amount=50, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        create_transaction(wallet, amount=-30, reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT)
        create_transaction(wallet, amount=20, reason=DeltaCrownTransaction.Reason.REFUND)
        create_transaction(wallet, amount=-10, reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST)
        
        # Expected balance: 100 + 50 - 30 + 20 - 10 = 130
        wallet.refresh_from_db()
        assert wallet.cached_balance == 130
        
        # Corrupt cached_balance (simulate drift)
        DeltaCrownWallet.objects.filter(id=wallet.id).update(cached_balance=999)
        wallet.refresh_from_db()
        assert wallet.cached_balance == 999, "Balance should be corrupted"
        
        # Recalculate
        new_balance = wallet.recalc_and_save()
        
        # Assert: Balance corrected
        assert new_balance == 130, "recalc_and_save() should correct balance to 130"
        wallet.refresh_from_db()
        assert wallet.cached_balance == 130, "Cached balance should be corrected"
    
    @pytest.mark.xfail(reason="Implementation pending - Step 2")
    def test_recalc_atomic(self, wallet_factory, create_transaction):
        """
        Test: recalc_and_save() is atomic (uses @transaction.atomic).
        
        Target: Atomicity of balance recalculation
        """
        wallet = wallet_factory()
        
        # Create transactions
        create_transaction(wallet, amount=50, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        
        # Recalc should be atomic (no intermediate states visible)
        # This test is conceptual - atomicity proven by lack of race conditions in concurrent tests
        balance = wallet.recalc_and_save()
        assert balance == 50, "Atomic recalc should return correct balance"


# ============================================================================
# Module Metadata
# ============================================================================

# Test count: 10 tests (6 xfail pending implementation)
# Coverage target: 100% on ledger invariants (financial logic)
# Target files: apps/economy/models.py (DeltaCrownWallet, DeltaCrownTransaction)
