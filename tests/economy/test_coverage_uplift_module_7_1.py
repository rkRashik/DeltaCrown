"""
Coverage Uplift Tests for Module 7.1

Implements: MODULE_7.1_KICKOFF.md - Step 6: Coverage ≥90%

Targeted tests to cover remaining edge cases in services.py:
- Retry wrapper paths (deadlock/serialization error retry)
- Transfer lock ordering (from_id > to_id)
- get_balance() cache behavior
- get_transaction_history() pagination/ordering
- Legacy helper functions coverage

Author: Module 7.1 Implementation
Date: 2024-11-11
"""
# Implements: Documents/ExecutionPlan/MODULE_7.1_KICKOFF.md

import pytest
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.db import transaction as db_transaction
from django.contrib.auth import get_user_model

from apps.user_profile.models import UserProfile
from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.economy import services
from apps.economy.exceptions import IdempotencyConflict, InsufficientFunds

User = get_user_model()


@pytest.fixture
def user_profile_factory(db):
    """Factory for creating test user profiles with unique usernames."""
    def _create_profile():
        user = User.objects.create_user(
            username=f"coverage_{uuid.uuid4().hex[:8]}",
            email=f"coverage_{uuid.uuid4().hex[:8]}@test.com"
        )
        # UserProfile auto-created by post_save signal
        return UserProfile.objects.get(user=user)
    return _create_profile


@pytest.mark.django_db
class TestRetryWrapperCoverage:
    """Test retry wrapper edge cases."""
    
    def test_deadlock_retry_succeeds(self, user_profile_factory):
        """
        Test: Deadlock on first attempt, success on retry.
        
        Target: _with_retry() deadlock/serialization error path
        """
        profile = user_profile_factory()
        
        # Mock the transaction creation to fail once, then succeed
        call_count = {'count': 0}
        original_create = DeltaCrownTransaction.objects.create
        
        def mock_create_with_deadlock(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] == 1:
                # First call: simulate deadlock
                from django.db import DatabaseError
                raise DatabaseError("deadlock detected")
            # Second call: succeed
            return original_create(*args, **kwargs)
        
        with patch.object(DeltaCrownTransaction.objects, 'create', side_effect=mock_create_with_deadlock):
            # This should retry once and succeed
            result = services.credit(
                profile=profile,
                amount=100,
                reason="test_retry",
                idempotency_key=f"retry_{uuid.uuid4().hex}"
            )
        
        # Assert: Transaction created successfully on retry
        assert result['transaction_id'] is not None
        assert result['balance_after'] == 100
        assert call_count['count'] == 2, "Should have called create twice (1 fail + 1 success)"


@pytest.mark.django_db
class TestTransferLockOrdering:
    """Test transfer lock ordering for deadlock prevention."""
    
    def test_transfer_from_higher_id_to_lower_id(self, user_profile_factory):
        """
        Test: Transfer where from_wallet.id > to_wallet.id.
        
        Target: Stable lock ordering (always locks lower ID first)
        """
        # Create profiles and let wallets auto-create via services
        profile1 = user_profile_factory()
        profile2 = user_profile_factory()
        
        # Fund both to ensure wallets exist, then get IDs
        services.credit(profile=profile1, amount=500, reason="fund1")
        services.credit(profile=profile2, amount=500, reason="fund2")
        
        wallet1 = DeltaCrownWallet.objects.get(profile=profile1)
        wallet2 = DeltaCrownWallet.objects.get(profile=profile2)
        
        # Identify high/low IDs
        if wallet1.id > wallet2.id:
            high_profile, low_profile = profile1, profile2
            high_balance, low_balance = 500, 500
        else:
            high_profile, low_profile = profile2, profile1
            high_balance, low_balance = 500, 500
        
        # Transfer from high ID to low ID
        result = services.transfer(
            from_profile=high_profile,
            to_profile=low_profile,
            amount=200,
            reason="test_lock_ordering",
            idempotency_key=f"lock_test_{uuid.uuid4().hex}"
        )
        
        # Assert: Transfer succeeded
        assert result['from_balance_after'] == 300
        assert result['to_balance_after'] == 700


@pytest.mark.django_db
class TestGetBalanceCaching:
    """Test get_balance() cache behavior."""
    
    def test_get_balance_cache_consistency(self, user_profile_factory):
        """
        Test: get_balance() returns consistent value.
        
        Target: get_balance() basic path
        """
        profile = user_profile_factory()
        
        # Initial balance
        bal1 = services.get_balance(profile)
        assert bal1 == 0
        
        # Add credit
        services.credit(profile=profile, amount=250, reason="test_cache")
        
        # Get balance again - should reflect credit
        bal2 = services.get_balance(profile)
        assert bal2 == 250


@pytest.mark.django_db
class TestTransactionHistoryPagination:
    """Test get_transaction_history() pagination and ordering."""
    
    def test_history_pagination_and_ordering(self, user_profile_factory):
        """
        Test: Create >50 transactions, verify pagination and DESC ordering.
        
        Target: get_transaction_history() pagination/ordering
        """
        profile = user_profile_factory()
        
        # Create 55 transactions
        for i in range(55):
            services.credit(
                profile=profile,
                amount=10,
                reason=f"tx_{i}",
                idempotency_key=f"page_test_{i}_{uuid.uuid4().hex}"
            )
        
        # Page 1: first 50 (most recent)
        page1 = services.get_transaction_history(profile, limit=50, offset=0)
        assert len(page1) == 50
        
        # Page 2: remaining 5
        page2 = services.get_transaction_history(profile, limit=50, offset=50)
        assert len(page2) == 5
        
        # Verify DESC ordering (most recent first)
        assert page1[0]['created_at'] >= page1[-1]['created_at']
        
        # Verify no overlap between pages (using 'id' key from history dicts)
        page1_ids = {tx['id'] for tx in page1}
        page2_ids = {tx['id'] for tx in page2}
        assert len(page1_ids & page2_ids) == 0, "Pages should not overlap"


@pytest.mark.django_db
class TestEdgeCaseCoverage:
    """Additional edge case coverage for services.py."""
    
    def test_get_balance_missing_wallet_returns_zero(self, user_profile_factory):
        """
        Test: get_balance() with profile that has no wallet.
        
        Target: Missing wallet edge case
        """
        profile = user_profile_factory()
        
        # Delete the auto-created wallet
        DeltaCrownWallet.objects.filter(profile=profile).delete()
        
        # get_balance should return 0 (or handle gracefully)
        balance = services.get_balance(profile)
        assert balance == 0
    
    def test_history_empty_wallet(self, user_profile_factory):
        """
        Test: get_transaction_history() on wallet with no transactions.
        
        Target: Empty history edge case
        """
        profile = user_profile_factory()
        
        # Get history (no transactions yet)
        history = services.get_transaction_history(profile)
        
        # Assert: Empty list
        assert history == []
    
    def test_transfer_zero_amount_rejected(self, user_profile_factory):
        """
        Test: Transfer with amount=0 should raise InvalidAmount.
        
        Target: Zero amount validation in transfer
        """
        from apps.economy.exceptions import InvalidAmount
        
        profile1 = user_profile_factory()
        profile2 = user_profile_factory()
        
        # Fund profile1
        services.credit(profile=profile1, amount=100, reason="fund")
        
        # Attempt transfer with zero amount
        with pytest.raises(InvalidAmount):
            services.transfer(
                from_profile=profile1,
                to_profile=profile2,
                amount=0,
                reason="zero_transfer"
            )
