"""
Common test fixtures for shop tests.

Provides reusable fixtures for user, wallet, and economy setup.
"""

import pytest
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user():
    """Create user with wallet and email."""
    timestamp = timezone.now().timestamp()
    username = f"shopuser_{timestamp}"
    email = f"{username}@test.com"
    user = User.objects.create_user(username=username, email=email, password="test123")
    return user


@pytest.fixture
def wallet(user):
    """Get wallet for user."""
    from apps.economy.models import DeltaCrownWallet
    from apps.user_profile.models import UserProfile
    
    # Create UserProfile first (DeltaCrownWallet is keyed to UserProfile, not User)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
    return wallet


@pytest.fixture
def funded_wallet(wallet):
    """Wallet with 1000 DC balance."""
    from apps.economy.services import credit
    # credit() expects profile, not wallet
    credit(wallet.profile, 1000, reason='MANUAL_ADJUST', idempotency_key=f'fund_{wallet.id}')
    wallet.refresh_from_db()
    return wallet


@pytest.fixture
def shop_item():
    """Create a test shop item."""
    from apps.shop.models import ShopItem
    item, _ = ShopItem.objects.get_or_create(
        sku='TEST_ITEM',
        defaults={
            'name': 'Test Item',
            'description': 'A test item for shop tests',
            'price': 50,
            'active': True
        }
    )
    return item


@pytest.fixture
def authorized_hold(funded_wallet):
    """Create a generic authorized hold for testing capture/release operations."""
    from apps.shop.services import authorize_spend
    result = authorize_spend(
        wallet=funded_wallet,
        amount=Decimal('200.00'),
        sku='CAPTURE_ITEM',
        idempotency_key=f'auth_hold_{funded_wallet.id}'
    )
    return result['hold_id']


@pytest.fixture
def captured_transaction(funded_wallet):
    """Create a captured transaction for testing refund operations."""
    from apps.shop.services import authorize_spend, capture
    
    # First authorize
    auth_result = authorize_spend(
        wallet=funded_wallet,
        amount=Decimal('200.00'),
        sku='CAPTURE_ITEM',
        idempotency_key=f'auth_refund_{funded_wallet.id}'
    )
    
    # Then capture
    capture_result = capture(
        wallet=funded_wallet,
        authorization_id=auth_result['hold_id'],
        idempotency_key=f'cap_refund_{funded_wallet.id}'
    )
    
    return capture_result['transaction_id']


@pytest.fixture(autouse=True)
def ensure_test_shop_items(db):
    """Automatically ensure test shop items exist for all shop tests."""
    from apps.shop.models import ShopItem
    test_items = [
        ('TEST_ITEM', 'Test Item', 50),
        ('EXPENSIVE_ITEM', 'Expensive Item', 2000),
        ('ITEM_1', 'Item 1', 100),
        ('ITEM_2', 'Item 2', 150),
        ('ITEM_3', 'Item 3', 200),
        ('ITEM_4', 'Item 4', 250),
        ('CONCURRENT_ITEM', 'Concurrent Test Item', 300),
        ('CONCURRENT_SKU_0', 'Concurrent SKU 0', 100),
        ('CONCURRENT_SKU_1', 'Concurrent SKU 1', 100),
        ('CONCURRENT_SKU_2', 'Concurrent SKU 2', 100),
        ('CONCURRENT_SKU_3', 'Concurrent SKU 3', 100),
        ('CONCURRENT_SKU_4', 'Concurrent SKU 4', 100),
        ('CAPTURE_ITEM', 'Capture Test Item', 300),
        ('RELEASE_ITEM', 'Release Test Item', 400),
        ('OVERDRAFT_ITEM', 'Overdraft Test Item', 500),
        ('EXPIRED_ITEM', 'Expired Test Item', 50),
        ('REFUNDABLE_ITEM', 'Refundable Test Item', 300),
        ('REPLAY_ITEM', 'Replay Test Item', 100),
        ('ITEM_A', 'Item A', 50),
        ('ITEM_B', 'Item B', 75),
        ('TIMED_ITEM', 'Timed Test Item', 60),
        ('RELEASED_ITEM', 'Released Test Item', 150),
        ('CAPTURED_ITEM', 'Captured Test Item', 200),
        ('EXPIRED_REL_ITEM', 'Expired Release Item', 180),
        ('ITEM_A_thread1', 'Item A thread1', 50),
        ('ITEM_B_thread1', 'Item B thread1', 50),
        ('ITEM_A_thread2', 'Item A thread2', 50),
        ('ITEM_B_thread2', 'Item B thread2', 50),
        ('RETRY_SKU_0', 'Retry SKU 0', 10),
        ('RETRY_SKU_1', 'Retry SKU 1', 10),
        ('RETRY_SKU_2', 'Retry SKU 2', 10),
        ('RETRY_SKU_3', 'Retry SKU 3', 10),
        ('RETRY_SKU_4', 'Retry SKU 4', 10),
        ('RETRY_SKU_5', 'Retry SKU 5', 10),
        ('RETRY_SKU_6', 'Retry SKU 6', 10),
        ('RETRY_SKU_7', 'Retry SKU 7', 10),
        ('RETRY_SKU_8', 'Retry SKU 8', 10),
        ('RETRY_SKU_9', 'Retry SKU 9', 10),
    ]
    for sku, name, price in test_items:
        ShopItem.objects.get_or_create(
            sku=sku,
            defaults={'name': name, 'description': f'{name} description', 'price': price, 'active': True}
        )
