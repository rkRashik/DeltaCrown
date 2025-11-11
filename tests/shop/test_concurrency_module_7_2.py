"""
Module 7.2 - DeltaCoin Shop: Concurrency Tests

Tests concurrent spend operations:
- Race conditions (dual capture)
- Lock ordering to prevent deadlocks
- Serialization retry on conflicts

Coverage:
- Dual capture with SELECT FOR UPDATE (one wins, one fails)
- Concurrent authorize with different idempotency keys (both succeed)
- Lock ordering prevents deadlock
- Serialization failure triggers retry (if retry wrapper implemented)
"""

import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction, connection
from concurrent.futures import ThreadPoolExecutor, as_completed

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestConcurrency:
    """Test concurrent spend operations with SELECT FOR UPDATE and lock ordering."""

    
    def test_dual_capture_race_condition(self, funded_wallet):
        """Two threads try to capture same hold - only one succeeds."""
        from apps.shop.services import authorize_spend, capture
        from apps.shop.exceptions import InvalidStateTransition
        from queue import Queue

        # Create hold first
        auth_result = authorize_spend(
            wallet=funded_wallet,
            amount=300,
            sku='CONCURRENT_ITEM',
            idempotency_key='auth_concurrent'
        )
        hold_id = auth_result['hold_id']

        results_queue = Queue()

        def attempt_capture(idem_key):
            """Attempt to capture hold in separate thread."""
            try:
                # Each thread uses different idempotency key
                result = capture(
                    wallet=funded_wallet,
                    authorization_id=hold_id,
                    idempotency_key=idem_key
                )
                results_queue.put(('success', result))
            except InvalidStateTransition as e:
                # Second thread should get "already captured" error
                results_queue.put(('failed', str(e)))

        # Execute two captures concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_1 = executor.submit(attempt_capture, 'capture_thread_1')
            future_2 = executor.submit(attempt_capture, 'capture_thread_2')

            # Wait for completion
            future_1.result()
            future_2.result()

        # Get results from queue
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        # Exactly one success, one failure
        statuses = [r[0] for r in results]
        assert statuses.count('success') == 1
        assert statuses.count('failed') == 1

        # Verify hold is captured (terminal state)
        from apps.shop.models import ReservationHold
        hold = ReservationHold.objects.get(id=hold_id)
        assert hold.status == 'captured'

        # Verify only ONE debit transaction created (shop purchases use ENTRY_FEE_DEBIT reason)
        from apps.economy.models import DeltaCrownTransaction
        debits = DeltaCrownTransaction.objects.filter(
            wallet=funded_wallet,
            reason='ENTRY_FEE_DEBIT'
        )
        assert debits.count() == 1

    
    def test_concurrent_authorize_different_keys(self, funded_wallet):
        """Multiple threads can authorize simultaneously with different keys."""
        from apps.shop.services import authorize_spend
        from queue import Queue

        results_queue = Queue()

        def authorize_with_key(idx):
            """Authorize spend in separate thread."""
            result = authorize_spend(
                wallet=funded_wallet,
                amount=100,
                sku=f'CONCURRENT_SKU_{idx}',
                idempotency_key=f'auth_concurrent_{idx}'
            )
            results_queue.put(result)

        # Execute 5 concurrent authorizations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(authorize_with_key, i) for i in range(5)]
            # Wait for all to complete
            for future in futures:
                future.result()

        # Get results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        # All 5 should succeed
        assert len(results) == 5
        assert all('hold_id' in r for r in results)

        # Verify 5 holds created
        from apps.shop.models import ReservationHold
        holds = ReservationHold.objects.filter(wallet=funded_wallet, status='authorized')
        assert holds.count() == 5

    
    def test_lock_ordering_prevents_deadlock(self, funded_wallet):
        """Lock ordering (wallet PK order) prevents deadlocks."""
        from apps.shop.services import authorize_spend
        from apps.economy.services import credit
        from django.contrib.auth import get_user_model

        # Create second wallet
        user2 = get_user_model().objects.create_user(
            username=f'user2_{timezone.now().timestamp()}',
            email=f'user2_{timezone.now().timestamp()}@test.com',
            password='test123'
        )
        from apps.economy.models import DeltaCrownWallet
        wallet2, _ = DeltaCrownWallet.objects.get_or_create(profile=user2.profile)
        credit(profile=user2.profile, amount=1000, reason='MANUAL_ADJUST', idempotency_key=f'fund_w2_{wallet2.id}')

        def cross_wallet_ops(w1, w2, suffix):
            """Perform operations on two wallets in thread."""
            # Authorize on both wallets (lock ordering should prevent deadlock)
            authorize_spend(w1, 50, sku=f'ITEM_A_{suffix}', idempotency_key=f'auth_a_{suffix}')
            authorize_spend(w2, 50, sku=f'ITEM_B_{suffix}', idempotency_key=f'auth_b_{suffix}')
            return 'success'

        # Execute cross-wallet operations concurrently
        # Thread 1: wallet1 -> wallet2
        # Thread 2: wallet2 -> wallet1
        # Lock ordering should prevent deadlock
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_1 = executor.submit(cross_wallet_ops, funded_wallet, wallet2, 'thread1')
            future_2 = executor.submit(cross_wallet_ops, wallet2, funded_wallet, 'thread2')

            results = [future.result() for future in as_completed([future_1, future_2])]

        # Both threads complete successfully (no deadlock)
        assert results == ['success', 'success']

    
    @pytest.mark.skip(reason="Optional: Only if retry wrapper implemented")
    def test_serialization_retry_on_conflict(self, funded_wallet):
        """Serialization failures trigger automatic retry."""
        from apps.shop.services import authorize_spend

        def authorize_with_retry(idx):
            """Authorize with potential serialization conflict."""
            # This test assumes a retry wrapper around atomic operations
            result = authorize_spend(
                wallet=funded_wallet,
                amount=10,
                sku=f'RETRY_SKU_{idx}',
                idempotency_key=f'retry_{idx}'
            )
            return result

        # Execute many concurrent operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(authorize_with_retry, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]

        # All operations succeed (retries handle conflicts)
        assert len(results) == 10
        assert all('hold_id' in r for r in results)
