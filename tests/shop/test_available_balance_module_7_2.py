"""
Module 7.2 - DeltaCoin Shop: Available Balance Tests

Tests the available balance calculation:
- get_available_balance(): balance - active holds
- Multiple concurrent holds
- Balance restoration after capture/release

Coverage:
- No holds (available = balance)
- Single hold (available = balance - hold)
- Multiple holds (available = balance - sum(holds))
- After capture (hold removed from calculation)
- After release (hold removed from calculation)
- Overdraft scenarios (negative available allowed if wallet allows)
"""

import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestAvailableBalance:
    """Test get_available_balance() function - available = balance - active holds."""

    def test_available_balance_no_holds(self, funded_wallet):
        """Available balance equals cached_balance when no holds."""
        from apps.shop.services import get_available_balance

        available = get_available_balance(funded_wallet)
        assert available == 1000
        assert available == funded_wallet.cached_balance

    
    def test_available_balance_single_hold(self, funded_wallet):
        """Available balance = balance - single hold amount."""
        from apps.shop.services import authorize_spend, get_available_balance

        authorize_spend(
            wallet=funded_wallet,
            amount=250,
            sku='ITEM_1',
            idempotency_key='hold_single'
        )

        available = get_available_balance(funded_wallet)
        assert available == 750  # 1000 - 250

    
    def test_available_balance_multiple_holds(self, funded_wallet):
        """Available balance = balance - sum of all active holds."""
        from apps.shop.services import authorize_spend, get_available_balance

        # Create 4 holds
        authorize_spend(funded_wallet, 100, sku='ITEM_1', idempotency_key='multi_avail_1')
        authorize_spend(funded_wallet, 150, sku='ITEM_2', idempotency_key='multi_avail_2')
        authorize_spend(funded_wallet, 200, sku='ITEM_3', idempotency_key='multi_avail_3')
        authorize_spend(funded_wallet, 250, sku='ITEM_4', idempotency_key='multi_avail_4')

        available = get_available_balance(funded_wallet)
        assert available == 300  # 1000 - (100 + 150 + 200 + 250)

    
    def test_available_balance_after_capture(self, funded_wallet):
        """Available balance updates correctly after capture (hold removed)."""
        from apps.shop.services import authorize_spend, capture, get_available_balance

        # Authorize
        auth_result = authorize_spend(
            wallet=funded_wallet,
            amount=300,
            sku='CAPTURE_ITEM',
            idempotency_key='auth_for_avail_cap'
        )

        # Available reduced by hold
        available_after_auth = get_available_balance(funded_wallet)
        assert available_after_auth == 700  # 1000 - 300

        # Capture
        capture(
            wallet=funded_wallet,
            authorization_id=auth_result['hold_id'],
            idempotency_key='cap_for_avail'
        )

        # Available = balance (hold removed, balance reduced by debit)
        funded_wallet.refresh_from_db()
        available_after_cap = get_available_balance(funded_wallet)
        assert available_after_cap == 700  # New balance 700, no holds
        assert available_after_cap == funded_wallet.cached_balance

    
    def test_available_balance_after_release(self, funded_wallet):
        """Available balance restores to full balance after release."""
        from apps.shop.services import authorize_spend, release, get_available_balance

        # Authorize
        auth_result = authorize_spend(
            wallet=funded_wallet,
            amount=400,
            sku='RELEASE_ITEM',
            idempotency_key='auth_for_avail_rel'
        )

        # Available reduced by hold
        available_after_auth = get_available_balance(funded_wallet)
        assert available_after_auth == 600  # 1000 - 400

        # Release
        release(
            wallet=funded_wallet,
            authorization_id=auth_result['hold_id'],
            idempotency_key='rel_for_avail'
        )

        # Available restored to full balance (hold removed, balance unchanged)
        available_after_rel = get_available_balance(funded_wallet)
        assert available_after_rel == 1000
        assert available_after_rel == funded_wallet.cached_balance

    
    def test_available_balance_with_overdraft(self, wallet):
        """Available balance can be negative if overdraft allowed."""
        from apps.shop.services import authorize_spend, get_available_balance

        # Wallet with overdraft enabled and zero balance
        wallet.allow_overdraft = True
        wallet.save()

        # Authorize hold (overdraft scenario)
        authorize_spend(
            wallet=wallet,
            amount=500,
            sku='OVERDRAFT_ITEM',
            idempotency_key='hold_overdraft'
        )

        available = get_available_balance(wallet)
        assert available == -500  # 0 - 500
        assert available < 0
