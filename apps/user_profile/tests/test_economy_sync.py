"""
Test: Economy Sync Service (UP-M3)

Tests sync_wallet_to_profile(), reconcile_economy command, signal integration.

Coverage:
- Transaction creates → profile updated
- Balance sync correctness
- Earnings sync correctness
- Concurrent transaction safety
- Reconciliation fixes drift
- Idempotency (rerun safe)
"""
import pytest
from decimal import Decimal
from django.db import transaction
from django.core.management import call_command
from io import StringIO

from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.user_profile.models import UserProfile
from apps.user_profile.services.economy_sync import (
    sync_wallet_to_profile,
    sync_profile_by_user_id,
    get_balance_drift,
    recompute_lifetime_earnings,
)


@pytest.fixture
def user_with_wallet(db, django_user_model):
    """Create user with profile and wallet."""
    import uuid
    unique = uuid.uuid4().hex[:8]
    user = django_user_model.objects.create_user(
        username=f'testuser_{unique}',
        email=f'test_{unique}@example.com',
        password='testpass123'
    )
    # Profile auto-created by signal, just get it
    profile = UserProfile.objects.get(user=user)
    profile.display_name = 'Test User'
    profile.save()
    wallet = DeltaCrownWallet.objects.create(
        profile=profile,
        cached_balance=0,
        lifetime_earnings=0,
    )
    return {'user': user, 'profile': profile, 'wallet': wallet}


@pytest.mark.django_db(transaction=True)
class TestEconomySyncService:
    """Test sync_wallet_to_profile service (signals still active)."""
    
    def test_sync_updates_profile_balance(self, user_with_wallet):
        """Transaction creates → wallet.cached_balance → profile.deltacoin_balance sync."""
        wallet = user_with_wallet['wallet']
        profile = user_with_wallet['profile']
        
        # Create credit transaction (signal auto-syncs profile)
        DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=100,
            reason=DeltaCrownTransaction.Reason.WINNER,
        )
        
        wallet.refresh_from_db()
        assert wallet.cached_balance == 100, "Wallet balance should be 100"
        
        # Manually sync (may return False if already synced by signal, that's OK - idempotent)
        result = sync_wallet_to_profile(wallet.id)
        
        profile.refresh_from_db()
        assert profile.deltacoin_balance == Decimal('100'), "Profile balance should sync"
        # Check final state, not whether sync was needed (idempotent function)
        assert result['balance_after'] == 100.0, f"Final balance should be 100, got {result['balance_after']}"
    
    def test_sync_updates_lifetime_earnings(self, user_with_wallet):
        """Positive transactions → wallet.lifetime_earnings + profile.lifetime_earnings."""
        wallet = user_with_wallet['wallet']
        profile = user_with_wallet['profile']
        
        # Create multiple credit transactions
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=100, reason=DeltaCrownTransaction.Reason.WINNER)
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=50, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=-30, reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT)
        
        # Manually sync (signals disabled, so this is the first sync)
        result = sync_wallet_to_profile(wallet.id)
        
        wallet.refresh_from_db()
        profile.refresh_from_db()
        
        # Lifetime earnings = sum(positive) = 100 + 50 = 150 (ignores -30)
        assert wallet.lifetime_earnings == 150, "Wallet lifetime_earnings should be 150"
        assert profile.lifetime_earnings == Decimal('150'), "Profile lifetime_earnings should be 150"
        # Result may be False if already synced (idempotent), just check final state is correct
        assert result['earnings_after'] == 150.0, f"Final earnings should be 150, got {result['earnings_after']}"
    
    def test_sync_is_idempotent(self, user_with_wallet):
        """Calling sync multiple times doesn't corrupt data."""
        wallet = user_with_wallet['wallet']
        profile = user_with_wallet['profile']
        
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=200, reason=DeltaCrownTransaction.Reason.WINNER)
        
        # Sync 3 times
        sync_wallet_to_profile(wallet.id)
        sync_wallet_to_profile(wallet.id)
        result = sync_wallet_to_profile(wallet.id)
        
        profile.refresh_from_db()
        assert profile.deltacoin_balance == Decimal('200'), "Balance should be 200 (not 600)"
        assert result['balance_synced'] is False, "Third sync should detect no change"
    
    def test_sync_handles_negative_balance(self, user_with_wallet):
        """Wallet with overdraft → profile can have negative balance."""
        wallet = user_with_wallet['wallet']
        profile = user_with_wallet['profile']
        
        wallet.allow_overdraft = True
        wallet.save()
        
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=-50, reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST)
        
        sync_wallet_to_profile(wallet.id)
        
        profile.refresh_from_db()
        assert profile.deltacoin_balance == Decimal('-50'), "Profile should reflect negative balance"
    
    def test_get_balance_drift_detection(self, user_with_wallet):
        """get_balance_drift() detects profile-wallet mismatch."""
        wallet = user_with_wallet['wallet']
        profile = user_with_wallet['profile']
        
        # Create transaction (signal auto-syncs profile)
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=100, reason=DeltaCrownTransaction.Reason.WINNER)
        wallet.recalc_and_save()
        
        # Manually create drift by resetting profile (simulating missed sync)
        profile.deltacoin_balance = Decimal('0')
        profile.save()
        
        # Profile now has drift
        profile.refresh_from_db()
        assert profile.deltacoin_balance == Decimal('0')
        
        # Detect drift
        drift = get_balance_drift(wallet.id)
        assert drift['has_drift'] is True
        assert drift['wallet_balance'] == 100
        assert drift['profile_balance'] == 0.0
        assert drift['diff'] == 100.0
    
    def test_recompute_lifetime_earnings_from_ledger(self, user_with_wallet):
        """recompute_lifetime_earnings() rebuilds from transactions."""
        wallet = user_with_wallet['wallet']
        profile = user_with_wallet['profile']
        
        # Create transactions
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=500, reason=DeltaCrownTransaction.Reason.WINNER)
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=300, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
        
        # Manually corrupt earnings (simulate old data)
        wallet.lifetime_earnings = 0
        wallet.save()
        profile.lifetime_earnings = Decimal('0')
        profile.save()
        
        # Recompute
        total = recompute_lifetime_earnings(wallet.id)
        
        assert total == 800
        wallet.refresh_from_db()
        profile.refresh_from_db()
        assert wallet.lifetime_earnings == 800
        assert profile.lifetime_earnings == Decimal('800')


@pytest.mark.django_db(transaction=True)
class TestSignalIntegration:
    """Test signal auto-syncs profile on transaction create."""
    
    def test_transaction_create_triggers_sync(self, user_with_wallet):
        """Creating transaction automatically syncs profile (via signal)."""
        wallet = user_with_wallet['wallet']
        profile = user_with_wallet['profile']
        
        # Create transaction (signal should auto-sync)
        DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=250,
            reason=DeltaCrownTransaction.Reason.WINNER,
        )
        
        # Profile should be synced automatically
        profile.refresh_from_db()
        assert profile.deltacoin_balance == Decimal('250'), "Signal should auto-sync"
        assert profile.lifetime_earnings == Decimal('250'), "Signal should update earnings"


@pytest.mark.django_db(transaction=True)
class TestReconcileCommand:
    """Test reconcile_economy management command."""
    
    def test_reconcile_single_user_dry_run(self, user_with_wallet):
        """reconcile_economy --user-id --dry-run shows drift without changing data."""
        wallet = user_with_wallet['wallet']
        profile = user_with_wallet['profile']
        user = user_with_wallet['user']
        
        # Create transaction (signal auto-syncs profile)
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=300, reason=DeltaCrownTransaction.Reason.WINNER)
        wallet.recalc_and_save()
        
        # Manually create drift by resetting profile (simulating out-of-sync state)
        profile.deltacoin_balance = Decimal('0')
        profile.lifetime_earnings = Decimal('0')
        profile.save()
        
        # Profile now has drift
        assert profile.deltacoin_balance == Decimal('0')
        
        # Dry run
        out = StringIO()
        call_command('reconcile_economy', '--user-id', user.id, '--dry-run', stdout=out)
        
        output = out.getvalue()
        assert 'DRY RUN' in output
        assert 'Balance 0.00 → 300.00' in output
        
        # Data unchanged
        profile.refresh_from_db()
        assert profile.deltacoin_balance == Decimal('0'), "Dry run should not modify data"
    
    def test_reconcile_single_user_fixes_drift(self, user_with_wallet):
        """reconcile_economy --user-id (no dry-run) fixes drift."""
        wallet = user_with_wallet['wallet']
        profile = user_with_wallet['profile']
        user = user_with_wallet['user']
        
        # Create transaction (signal auto-syncs profile)
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=400, reason=DeltaCrownTransaction.Reason.WINNER)
        wallet.recalc_and_save()
        
        # Manually create drift by resetting profile
        profile.deltacoin_balance = Decimal('0')
        profile.lifetime_earnings = Decimal('0')
        profile.save()
        
        # Reconcile (real run)
        out = StringIO()
        call_command('reconcile_economy', '--user-id', user.id, stdout=out)
        
        output = out.getvalue()
        assert 'Balance synced: 1' in output
        
        # Data fixed
        profile.refresh_from_db()
        assert profile.deltacoin_balance == Decimal('400'), "Reconcile should fix drift"
        assert profile.lifetime_earnings == Decimal('400')
    
    def test_reconcile_all_with_limit(self, db, django_user_model):
        """reconcile_economy --all --limit processes batch."""
        # Create 3 users with wallets and transactions
        for i in range(3):
            user = django_user_model.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
            )
            # Profile auto-created by signal, get it
            profile = UserProfile.objects.get(user=user)
            profile.display_name = f'User {i}'
            profile.save()
            
            wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=100 * (i + 1))
            # Create transaction (signal auto-syncs profile)
            DeltaCrownTransaction.objects.create(
                wallet=wallet,
                amount=100 * (i + 1),
                reason=DeltaCrownTransaction.Reason.WINNER,
            )
            
            # Manually create drift by resetting profile
            profile.deltacoin_balance = Decimal('0')
            profile.lifetime_earnings = Decimal('0')
            profile.save()
        
        # Reconcile first 2 only
        out = StringIO()
        call_command('reconcile_economy', '--all', '--limit', '2', stdout=out)
        
        output = out.getvalue()
        assert 'Processing 2 wallets' in output
        assert 'Balance synced: 2' in output


@pytest.mark.django_db(transaction=True)
class TestConcurrency:
    """Test concurrent transaction safety."""
    
    def test_concurrent_transactions_no_lost_updates(self, user_with_wallet):
        """Multiple concurrent transactions all reflected in profile."""
        wallet = user_with_wallet['wallet']
        profile = user_with_wallet['profile']
        
        # Simulate 3 concurrent transactions (in separate atomic blocks)
        with transaction.atomic():
            DeltaCrownTransaction.objects.create(wallet=wallet, amount=100, reason=DeltaCrownTransaction.Reason.WINNER)
            sync_wallet_to_profile(wallet.id)
        
        with transaction.atomic():
            DeltaCrownTransaction.objects.create(wallet=wallet, amount=50, reason=DeltaCrownTransaction.Reason.PARTICIPATION)
            sync_wallet_to_profile(wallet.id)
        
        with transaction.atomic():
            DeltaCrownTransaction.objects.create(wallet=wallet, amount=25, reason=DeltaCrownTransaction.Reason.REFUND)
            sync_wallet_to_profile(wallet.id)
        
        profile.refresh_from_db()
        assert profile.deltacoin_balance == Decimal('175'), "All transactions reflected"
        assert profile.lifetime_earnings == Decimal('175'), "All credits summed"
