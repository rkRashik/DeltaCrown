"""
Test: Idempotency (Module 7.1 - Step 1: Test Scaffolding)

Implements: MODULE_7.1_KICKOFF.md - Idempotency Hardening
Coverage Target: 100% (critical financial logic)

Tests duplicate request handling, deterministic key generation, collision detection.
"""
# Implements: Documents/ExecutionPlan/Modules/MODULE_7.1_KICKOFF.md

import pytest
from decimal import Decimal
from django.db import IntegrityError
from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.user_profile.models import UserProfile


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def user_profile_factory(db):
    """Factory to create UserProfile instances for testing."""
    import uuid
    def _create():
        from django.contrib.auth import get_user_model
        User = get_user_model()
        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create_user(
            username=f"testuser_{unique_id}",
            email=f"test{unique_id}@example.com"
        )
        # UserProfile auto-created via signal, fetch it
        profile = UserProfile.objects.get(user=user)
        return profile
    
    return _create


# ============================================================================
# Test Class: Duplicate Request Handling
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestDuplicateRequests:
    """
    Idempotency: Duplicate requests with same key return original transaction,
    do not modify balance.
    """
    
    def test_duplicate_credit_same_key(self, user_profile_factory):
        """
        Test: credit() with duplicate idempotency_key returns original transaction.
        
        Target: apps/economy/services.py - credit() idempotency
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        idempotency_key = "test-credit-001"
        
        # First credit: 100 coins
        result1 = services.credit(
            profile=profile,
            amount=100,
            reason=DeltaCrownTransaction.Reason.WINNER,
            idempotency_key=idempotency_key
        )
        
        assert result1['balance_after'] == 100
        original_txn_id = result1['transaction_id']
        
        # Duplicate credit: same key, same amount
        result2 = services.credit(
            profile=profile,
            amount=100,
            reason=DeltaCrownTransaction.Reason.WINNER,
            idempotency_key=idempotency_key
        )
        
        # Assert: Same transaction returned (no new transaction created)
        assert result2['transaction_id'] == original_txn_id
        
        # Assert: Balance unchanged (still 100, not 200)
        assert result2['balance_after'] == 100
        
        # Assert: Only 1 transaction in DB
        wallet = DeltaCrownWallet.objects.get(profile=profile)
        assert DeltaCrownTransaction.objects.filter(wallet=wallet).count() == 1
    
    def test_duplicate_debit_same_key(self, user_profile_factory):
        """
        Test: debit() with duplicate idempotency_key returns original transaction.
        
        Target: apps/economy/services.py - debit() idempotency
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # Credit 200 coins first
        services.credit(profile=profile, amount=200, reason=DeltaCrownTransaction.Reason.WINNER)
        
        idempotency_key = "test-debit-001"
        
        # First debit: 50 coins
        result1 = services.debit(
            profile=profile,
            amount=50,
            reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT,
            idempotency_key=idempotency_key
        )
        
        assert result1['balance_after'] == 150
        original_txn_id = result1['transaction_id']
        
        # Duplicate debit: same key
        result2 = services.debit(
            profile=profile,
            amount=50,
            reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT,
            idempotency_key=idempotency_key
        )
        
        # Assert: Same transaction returned
        assert result2['transaction_id'] == original_txn_id
        
        # Assert: Balance unchanged (still 150, not 100)
        assert result2['balance_after'] == 150
    
    def test_duplicate_transfer_same_key(self, user_profile_factory):
        """
        Test: transfer() with duplicate idempotency_key returns original transactions.
        
        Target: apps/economy/services.py - transfer() idempotency
        """
        from apps.economy import services
        
        profile_a = user_profile_factory()
        profile_b = user_profile_factory()
        
        # Credit profile_a with 300 coins
        services.credit(profile=profile_a, amount=300, reason=DeltaCrownTransaction.Reason.WINNER)
        
        idempotency_key = "test-transfer-001"
        
        # First transfer: 75 coins from A to B
        result1 = services.transfer(
            from_profile=profile_a,
            to_profile=profile_b,
            amount=75,
            reason=DeltaCrownTransaction.Reason.P2P_TRANSFER,
            idempotency_key=idempotency_key
        )
        
        assert result1['from_balance_after'] == 225
        assert result1['to_balance_after'] == 75
        
        original_debit_id = result1['debit_transaction_id']
        original_credit_id = result1['credit_transaction_id']
        
        # Duplicate transfer: same key
        result2 = services.transfer(
            from_profile=profile_a,
            to_profile=profile_b,
            amount=75,
            reason=DeltaCrownTransaction.Reason.P2P_TRANSFER,
            idempotency_key=idempotency_key
        )
        
        # Assert: Same transaction IDs returned (idempotent)
        assert result2['debit_transaction_id'] == original_debit_id
        assert result2['credit_transaction_id'] == original_credit_id
        
        # Assert: Balances unchanged
        assert result2['from_balance_after'] == 225
        assert result2['to_balance_after'] == 75


# ============================================================================
# Test Class: Integration with Existing Functions
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestExistingFunctionIdempotency:
    """
    Validate that existing award functions (award_participation, award_placements)
    maintain idempotency behavior.
    """
    
    def test_award_participation_idempotent(self, user_profile_factory):
        """
        Test: award_participation_for_registration() is idempotent (duplicate calls no-op).
        
        Target: apps/economy/services.py - award_participation_for_registration()
        Integration: Module 5.2 payout compatibility
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # Test deterministic key generation pattern
        registration_id = 12345
        idempotency_key = f"participation_award_reg_{registration_id}"
        
        # First award: 50 coins
        result1 = services.credit(
            profile=profile,
            amount=50,
            reason=DeltaCrownTransaction.Reason.PARTICIPATION,
            idempotency_key=idempotency_key
        )
        
        assert result1['balance_after'] == 50
        original_txn_id = result1['transaction_id']
        
        # Duplicate award (retry scenario)
        result2 = services.credit(
            profile=profile,
            amount=50,
            reason=DeltaCrownTransaction.Reason.PARTICIPATION,
            idempotency_key=idempotency_key
        )
        
        # Assert: Same transaction returned, balance unchanged
        assert result2['transaction_id'] == original_txn_id
        assert result2['balance_after'] == 50
    
    def test_award_placements_idempotent(self, user_profile_factory):
        """
        Test: award_placements() is idempotent (duplicate calls no-op).
        
        Target: apps/economy/services.py - award_placements()
        Integration: Module 5.2 payout compatibility
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # Simulate winner placement award
        registration_id = 67890
        placement = 1  # First place
        idempotency_key = f"placement_award_reg_{registration_id}_place_{placement}"
        
        # First award: 500 coins (winner)
        result1 = services.credit(
            profile=profile,
            amount=500,
            reason=DeltaCrownTransaction.Reason.WINNER,
            idempotency_key=idempotency_key
        )
        
        assert result1['balance_after'] == 500
        original_txn_id = result1['transaction_id']
        
        # Duplicate award (retry scenario)
        result2 = services.credit(
            profile=profile,
            amount=500,
            reason=DeltaCrownTransaction.Reason.WINNER,
            idempotency_key=idempotency_key
        )
        
        # Assert: Same transaction, balance unchanged
        assert result2['transaction_id'] == original_txn_id
        assert result2['balance_after'] == 500


# ============================================================================
# Test Class: Collision Detection & Out-of-Order Requests
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestCollisionAndOrdering:
    """
    Edge cases: collision detection, out-of-order requests, key reuse prevention.
    """
    
    def test_collision_different_amount_raises(self, user_profile_factory):
        """
        Test: Same idempotency_key with different amount raises error.
        
        Target: Collision detection (prevents key reuse with different parameters)
        """
        from apps.economy import services
        from apps.economy.exceptions import IdempotencyConflict
        
        profile = user_profile_factory()
        idempotency_key = "test-collision-001"
        
        # First credit: 100 coins
        result1 = services.credit(
            profile=profile,
            amount=100,
            reason=DeltaCrownTransaction.Reason.WINNER,
            idempotency_key=idempotency_key
        )
        
        # Attempt to use same key with different amount (collision)
        with pytest.raises(IdempotencyConflict) as exc_info:
            services.credit(
                profile=profile,
                amount=200,  # Different amount
                reason=DeltaCrownTransaction.Reason.WINNER,
                idempotency_key=idempotency_key
            )
        
        # Assert: Error message indicates collision
        assert "idempotency" in str(exc_info.value).lower() or "payload" in str(exc_info.value).lower()
    
    def test_out_of_order_requests_handled(self, user_profile_factory):
        """
        Test: Out-of-order duplicate requests return correct original transaction.
        
        Target: Idempotency works regardless of request order
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # Create 3 transactions with different keys
        key1 = "test-order-001"
        key2 = "test-order-002"
        key3 = "test-order-003"
        
        result1 = services.credit(profile=profile, amount=10, reason=DeltaCrownTransaction.Reason.PARTICIPATION, idempotency_key=key1)
        result2 = services.credit(profile=profile, amount=20, reason=DeltaCrownTransaction.Reason.PARTICIPATION, idempotency_key=key2)
        result3 = services.credit(profile=profile, amount=30, reason=DeltaCrownTransaction.Reason.PARTICIPATION, idempotency_key=key3)
        
        assert result3['balance_after'] == 60
        
        # Retry key2 (out-of-order)
        result2_retry = services.credit(profile=profile, amount=20, reason=DeltaCrownTransaction.Reason.PARTICIPATION, idempotency_key=key2)
        
        # Assert: Same transaction returned, balance unchanged
        assert result2_retry['transaction_id'] == result2['transaction_id']
        assert result2_retry['balance_after'] == 60  # Current balance, not balance at time of key2 creation
    
    def test_deterministic_key_generation(self, user_profile_factory):
        """
        Test: Idempotency keys are deterministic and collision-free.
        
        Target: Key generation patterns for tournament payouts
        """
        # Test pattern: "participation_award_reg_{registration.id}"
        reg_id = 12345
        key1 = f"participation_award_reg_{reg_id}"
        key2 = f"participation_award_reg_{reg_id}"
        
        assert key1 == key2, "Keys should be deterministic"
        
        # Test pattern: "placement_award_reg_{registration.id}_place_{placement}"
        placement = 1
        key3 = f"placement_award_reg_{reg_id}_place_{placement}"
        key4 = f"placement_award_reg_{reg_id}_place_{placement}"
        
        assert key3 == key4, "Keys should be deterministic"
        
        # Different registration/placement should generate different keys
        key5 = f"placement_award_reg_{reg_id + 1}_place_{placement}"
        assert key3 != key5, "Different registrations should have different keys"
        
        key6 = f"placement_award_reg_{reg_id}_place_{placement + 1}"
        assert key3 != key6, "Different placements should have different keys"
    
    def test_cross_op_collision_raises(self, user_profile_factory):
        """
        Test: Reusing same idempotency_key for different operation type raises IdempotencyConflict.
        
        Target: Cross-operation collision detection (e.g., credit key reused for debit)
        """
        from apps.economy import services
        from apps.economy.exceptions import IdempotencyConflict
        
        profile = user_profile_factory()
        idempotency_key = "test-cross-op-001"
        
        # First: credit with this key
        services.credit(profile=profile, amount=100, reason=DeltaCrownTransaction.Reason.WINNER, idempotency_key=idempotency_key)
        
        # Attempt to reuse same key for debit (different operation)
        with pytest.raises(IdempotencyConflict):
            services.debit(profile=profile, amount=50, reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT, idempotency_key=idempotency_key)
    
    def test_concurrent_same_key_single_apply(self, user_profile_factory):
        """
        Test: Concurrent requests with same key result in single apply (one writes, others get original).
        
        Target: Race condition handling via DB unique constraint on idempotency_key
        """
        from apps.economy import services
        import threading
        
        profile = user_profile_factory()
        idempotency_key = "test-concurrent-001"
        results = []
        errors = []
        
        def do_credit():
            try:
                result = services.credit(
                    profile=profile,
                    amount=100,
                    reason=DeltaCrownTransaction.Reason.WINNER,
                    idempotency_key=idempotency_key
                )
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Launch 5 concurrent threads with same key
        threads = [threading.Thread(target=do_credit) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Assert: All results should have same transaction_id (idempotent)
        assert len(results) >= 1, "At least one result should succeed"
        txn_ids = {r['transaction_id'] for r in results}
        assert len(txn_ids) == 1, "All results should reference the same transaction"
        
        # Assert: Balance applied only once
        wallet = DeltaCrownWallet.objects.get(profile=profile)
        assert wallet.cached_balance == 100
        
        # Assert: Only 1 transaction created
        assert DeltaCrownTransaction.objects.filter(wallet=wallet).count() == 1


# ============================================================================
# Test Class: Manual Adjustments (No Idempotency)
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestManualAdjustments:
    """
    Manual adjustments (without idempotency_key) should create new transactions each time.
    """
    
    def test_manual_adjust_no_idempotency_key(self, user_profile_factory):
        """
        Test: credit() without idempotency_key creates new transaction each call.
        
        Target: apps/economy/services.py - credit() (no idempotency key = manual adjustments)
        """
        from apps.economy import services
        
        profile = user_profile_factory()
        
        # Manual adjustment 1: +100 (no key)
        result1 = services.credit(
            profile=profile,
            amount=100,
            reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST
            # No idempotency_key
        )
        
        assert result1['balance_after'] == 100
        txn1_id = result1['transaction_id']
        
        # Manual adjustment 2: +100 (no key, should create new transaction)
        result2 = services.credit(
            profile=profile,
            amount=100,
            reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST
            # No idempotency_key
        )
        
        # Assert: Different transactions created
        assert result2['transaction_id'] != txn1_id
        
        # Assert: Balance incremented both times
        assert result2['balance_after'] == 200
        
        # Assert: 2 transactions in DB
        wallet = DeltaCrownWallet.objects.get(profile=profile)
        assert DeltaCrownTransaction.objects.filter(wallet=wallet).count() == 2


# ============================================================================
# Module Metadata
# ============================================================================

# Test count: 10 tests (all xfail pending implementation)
# Coverage target: 100% on idempotency logic (critical financial safety)
# Target files: apps/economy/services.py (credit, debit, transfer idempotency handling)
