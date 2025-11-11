"""
Test: Admin Reconciliation (Module 7.1 - Step 1: Test Scaffolding)

Implements: MODULE_7.1_KICKOFF.md - Admin Integration
Coverage Target: ≥75%

Tests recalc_all_wallets management command for balance drift detection and correction.
"""
# Implements: Documents/ExecutionPlan/MODULE_7.1_KICKOFF.md

import pytest
from decimal import Decimal
from io import StringIO
from django.core.management import call_command
from django.db.models import Sum
from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.user_profile.models import UserProfile


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def wallet_with_drift(db):
    """
    Creates a wallet with intentional drift between cached_balance and ledger sum.
    
    Returns: (wallet, expected_ledger_balance) tuple
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    user = User.objects.create_user(
        username="drift_test_user",
        email="drift@example.com"
    )
    profile = UserProfile.objects.create(user=user)
    wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=0)
    
    # Create transactions: +100, +50, -30 = 120 total
    DeltaCrownTransaction.objects.create(
        wallet=wallet,
        amount=100,
        reason=DeltaCrownTransaction.Reason.WINNER
    )
    DeltaCrownTransaction.objects.create(
        wallet=wallet,
        amount=50,
        reason=DeltaCrownTransaction.Reason.PARTICIPATION
    )
    DeltaCrownTransaction.objects.create(
        wallet=wallet,
        amount=-30,
        reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT
    )
    
    expected_balance = 120
    
    # Corrupt cached_balance (simulate drift)
    DeltaCrownWallet.objects.filter(id=wallet.id).update(cached_balance=999)
    wallet.refresh_from_db()
    
    return wallet, expected_balance


@pytest.fixture
def multiple_wallets_with_drift(db):
    """
    Creates 5 wallets: 3 with drift, 2 accurate.
    
    Returns: list of (wallet, expected_balance, has_drift) tuples
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    wallets_data = []
    
    for i in range(5):
        user = User.objects.create_user(
            username=f"multi_test_user_{i}",
            email=f"multi{i}@example.com"
        )
        profile = UserProfile.objects.create(user=user)
        wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=0)
        
        # Create transactions
        DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=50 * (i + 1),
            reason=DeltaCrownTransaction.Reason.PARTICIPATION
        )
        
        expected_balance = 50 * (i + 1)
        
        # Introduce drift on wallets 0, 2, 4 (not 1, 3)
        has_drift = i % 2 == 0
        if has_drift:
            DeltaCrownWallet.objects.filter(id=wallet.id).update(cached_balance=999)
        else:
            DeltaCrownWallet.objects.filter(id=wallet.id).update(cached_balance=expected_balance)
        
        wallet.refresh_from_db()
        wallets_data.append((wallet, expected_balance, has_drift))
    
    return wallets_data


# ============================================================================
# Test Class: recalc_all_wallets Command
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestRecalcAllWalletsCommand:
    """
    Test: python manage.py recalc_all_wallets [--dry-run]
    
    Detects and corrects balance drift across all wallets.
    """
    
    @pytest.mark.xfail(reason="Implementation pending - Step 5")
    def test_dry_run_flags_drift_no_changes(self, wallet_with_drift):
        """
        Test: --dry-run mode detects drift but does not modify database.
        
        Target: apps/economy/management/commands/recalc_all_wallets.py
        """
        wallet, expected_balance = wallet_with_drift
        
        # Run command in dry-run mode
        out = StringIO()
        call_command('recalc_all_wallets', '--dry-run', stdout=out)
        
        output = out.getvalue()
        
        # Assert: Output indicates drift detected
        assert "drift" in output.lower() or "mismatch" in output.lower()
        assert str(wallet.id) in output or "1 wallet" in output
        
        # Assert: cached_balance unchanged (still 999)
        wallet.refresh_from_db()
        assert wallet.cached_balance == 999, "Dry-run should not modify balance"
        
        # Assert: Exit code 1 (drift detected)
        # Note: pytest call_command doesn't expose exit code directly
        # Verify via output message instead
        assert "would correct" in output.lower() or "dry run" in output.lower()
    
    @pytest.mark.xfail(reason="Implementation pending - Step 5")
    def test_real_run_corrects_drift(self, wallet_with_drift):
        """
        Test: Real run (no --dry-run) corrects drift and updates database.
        
        Target: Balance correction in production mode
        """
        wallet, expected_balance = wallet_with_drift
        
        # Run command without dry-run
        out = StringIO()
        call_command('recalc_all_wallets', stdout=out)
        
        output = out.getvalue()
        
        # Assert: Output indicates correction applied
        assert "corrected" in output.lower() or "fixed" in output.lower()
        
        # Assert: cached_balance corrected to 120
        wallet.refresh_from_db()
        assert wallet.cached_balance == expected_balance, f"Balance should be corrected to {expected_balance}"
        
        # Assert: Balance matches ledger sum
        ledger_sum = DeltaCrownTransaction.objects.filter(wallet=wallet).aggregate(total=Sum('amount'))['total']
        assert wallet.cached_balance == ledger_sum
    
    @pytest.mark.xfail(reason="Implementation pending - Step 5")
    def test_multiple_wallets_selective_correction(self, multiple_wallets_with_drift):
        """
        Test: Command corrects only wallets with drift, leaves accurate wallets unchanged.
        
        Target: Selective correction logic
        """
        wallets_data = multiple_wallets_with_drift
        
        # Run command
        out = StringIO()
        call_command('recalc_all_wallets', stdout=out)
        
        output = out.getvalue()
        
        # Assert: Output indicates 3 wallets corrected (wallets 0, 2, 4)
        assert "3" in output or "three" in output.lower()
        
        # Verify each wallet
        for wallet, expected_balance, had_drift in wallets_data:
            wallet.refresh_from_db()
            
            # All wallets should have correct balance after command
            assert wallet.cached_balance == expected_balance, f"Wallet {wallet.id} should have balance {expected_balance}"
            
            # Verify ledger sum matches
            ledger_sum = DeltaCrownTransaction.objects.filter(wallet=wallet).aggregate(total=Sum('amount'))['total']
            assert wallet.cached_balance == ledger_sum
    
    @pytest.mark.xfail(reason="Implementation pending - Step 5")
    def test_exit_codes(self, wallet_with_drift):
        """
        Test: Command returns correct exit codes for CI/CD integration.
        
        Exit Codes:
        - 0: No drift detected (all wallets accurate)
        - 1: Drift detected (dry-run or corrected)
        - 2: Error (exception during execution)
        
        Target: Exit code contract for automation
        """
        wallet, expected_balance = wallet_with_drift
        
        # Dry-run with drift → exit code 1
        # Note: pytest call_command doesn't expose exit code directly
        # This test documents expected behavior for manual validation
        
        out = StringIO()
        call_command('recalc_all_wallets', '--dry-run', stdout=out)
        output = out.getvalue()
        
        # Assert: Drift detected message
        assert "drift" in output.lower()
        
        # Real run → corrects drift, exit code 1 (drift was found)
        out2 = StringIO()
        call_command('recalc_all_wallets', stdout=out2)
        output2 = out2.getvalue()
        
        assert "corrected" in output2.lower()
        
        # Subsequent run → no drift, exit code 0
        out3 = StringIO()
        call_command('recalc_all_wallets', stdout=out3)
        output3 = out3.getvalue()
        
        assert "no drift" in output3.lower() or "all accurate" in output3.lower()
    
    @pytest.mark.xfail(reason="Implementation pending - Step 5")
    def test_no_pii_in_output(self, wallet_with_drift):
        """
        Test: Command output contains wallet IDs only (no usernames, emails, or PII).
        
        Target: PART_2.3 Section 8 - PII discipline
        """
        wallet, expected_balance = wallet_with_drift
        
        # Run command
        out = StringIO()
        call_command('recalc_all_wallets', stdout=out)
        
        output = out.getvalue()
        
        # Assert: Wallet ID present
        assert str(wallet.id) in output
        
        # Assert: No PII (username, email)
        assert "drift_test_user" not in output, "Username should not appear in output"
        assert "drift@example.com" not in output, "Email should not appear in output"
        
        # Assert: Generic identifiers only
        assert "wallet" in output.lower()


# ============================================================================
# Test Class: Edge Cases
# ============================================================================

@pytest.mark.django_db
class TestRecalcEdgeCases:
    """
    Edge cases: empty wallets, zero balance drift, negative balance reconciliation.
    """
    
    @pytest.mark.xfail(reason="Implementation pending - Step 5")
    def test_empty_wallet_no_transactions(self, db):
        """
        Test: Wallet with no transactions recalculates to zero balance.
        
        Target: Edge case for new wallets
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(username="empty_user", email="empty@example.com")
        profile = UserProfile.objects.create(user=user)
        
        # Create wallet with corrupted balance (should be 0)
        wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=500)
        
        # Run command
        out = StringIO()
        call_command('recalc_all_wallets', stdout=out)
        
        # Assert: Balance corrected to 0
        wallet.refresh_from_db()
        assert wallet.cached_balance == 0
    
    @pytest.mark.xfail(reason="Implementation pending - Step 5")
    def test_negative_balance_reconciliation(self, db):
        """
        Test: Wallet with negative balance (overdraft) reconciles correctly.
        
        Target: Overdraft wallet handling
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(username="overdraft_user", email="overdraft@example.com")
        profile = UserProfile.objects.create(user=user)
        wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=0)
        
        # Create negative transaction (overdraft)
        DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=-50,
            reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST
        )
        
        # Corrupt balance
        DeltaCrownWallet.objects.filter(id=wallet.id).update(cached_balance=100)
        
        # Run command
        call_command('recalc_all_wallets')
        
        # Assert: Balance corrected to -50
        wallet.refresh_from_db()
        assert wallet.cached_balance == -50


# ============================================================================
# Module Metadata
# ============================================================================

# Test count: 8 tests (all xfail pending implementation)
# Coverage target: ≥75% on management command
# Target files: apps/economy/management/commands/recalc_all_wallets.py
