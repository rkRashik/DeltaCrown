"""
Module 7.3 - Transaction History & Reporting - Test Configuration

Shared fixtures and utilities for transaction history tests.
"""

import pytest
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user_with_history(db):
    """User with wallet and transaction history."""
    from apps.economy.models import DeltaCrownWallet
    from apps.economy.services import credit, debit
    from apps.user_profile.models import UserProfile
    
    timestamp = timezone.now().timestamp()
    user = User.objects.create_user(
        username=f"histuser_{timestamp}",
        email=f"hist{timestamp}@test.com",
        password="testpass"
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
    
    # Create history: credits and debits
    credit(profile, 1000, reason='MANUAL_ADJUST', idempotency_key=f'init_{wallet.id}')
    debit(profile, 100, reason='ENTRY_FEE_DEBIT', idempotency_key=f'fee1_{wallet.id}')
    debit(profile, 50, reason='ENTRY_FEE_DEBIT', idempotency_key=f'fee2_{wallet.id}')
    credit(profile, 500, reason='PRIZE_PAYOUT', idempotency_key=f'prize_{wallet.id}')
    debit(profile, 200, reason='ENTRY_FEE_DEBIT', idempotency_key=f'fee3_{wallet.id}')
    
    wallet.refresh_from_db()
    return user, wallet


@pytest.fixture
def wallet_with_date_range_history(db):
    """Wallet with transactions across multiple dates."""
    from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
    from apps.user_profile.models import UserProfile
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = User.objects.create_user(
        username=f"dateuser_{timezone.now().timestamp()}",
        email=f"date{timezone.now().timestamp()}@test.com",
        password="test"
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
    
    # Create transactions at different dates (manually to control created_at)
    base_time = timezone.now()
    dates = [
        base_time - timedelta(days=30),  # 30 days ago
        base_time - timedelta(days=15),  # 15 days ago
        base_time - timedelta(days=7),   # 7 days ago
        base_time - timedelta(days=1),   # Yesterday
        base_time,                        # Today
    ]
    
    running_balance = 0
    for i, date in enumerate(dates):
        amount = (i+1) * 100
        running_balance += amount
        txn = DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            reason='MANUAL_ADJUST',
            idempotency_key=f'date_{wallet.id}_{i}'
        )
        # Manually set created_at
        DeltaCrownTransaction.objects.filter(id=txn.id).update(created_at=date)
    
    # Update wallet balance
    wallet.cached_balance = running_balance
    wallet.save()
    
    return wallet
