"""
Test: Admin Reconciliation (Module 7.1 - Step 1: Test Scaffolding)

Implements: MODULE_7.1_KICKOFF.md - Admin Integration
Coverage Target: ≥75%

Tests recalc_all_wallets management command for balance drift detection and correction.
"""
# Implements: Documents/ExecutionPlan/Modules/MODULE_7.1_KICKOFF.md

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
    import uuid
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    user = User.objects.create_user(
        username=f"drift_{uuid.uuid4().hex[:8]}",
        email=f"drift_{uuid.uuid4().hex[:8]}@example.com"
    )
    # UserProfile auto-created by post_save signal
    profile = UserProfile.objects.get(user=user)
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
    import uuid
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    wallets_data = []
    
    for i in range(5):
        user = User.objects.create_user(
            username=f"multi_{uuid.uuid4().hex[:8]}",
            email=f"multi{i}_{uuid.uuid4().hex[:8]}@example.com"
        )
        # UserProfile auto-created by post_save signal
        profile = UserProfile.objects.get(user=user)
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
    
    def test_dry_run_flags_drift_no_changes(self, wallet_with_drift):
        """
        Test: --dry-run mode detects drift but does not modify database.
        
        Target: apps/economy/management/commands/recalc_all_wallets.py
        """
        wallet, expected_balance = wallet_with_drift
        
        # Run command in dry-run mode
        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command('recalc_all_wallets', '--dry-run', stdout=out)
        
        output = out.getvalue()
        
        # Assert: Output indicates drift detected
        assert "drift" in output.lower() or "mismatch" in output.lower()
        assert str(wallet.id) in output or "1 wallet" in output
        
        # Assert: cached_balance unchanged (still 999)
        wallet.refresh_from_db()
        assert wallet.cached_balance == 999, "Dry-run should not modify balance"
        
        # Assert: Exit code 1 (drift detected)
        assert exc_info.value.code == 1, "Should exit with code 1 when drift detected"
        assert "would correct" in output.lower() or "dry run" in output.lower()
    
    def test_real_run_corrects_drift(self, wallet_with_drift):
        """
        Test: Real run (no --dry-run) corrects drift and updates database.
        
        Target: Balance correction in production mode
        """
        wallet, expected_balance = wallet_with_drift
        
        # Run command without dry-run
        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command('recalc_all_wallets', stdout=out)
        
        output = out.getvalue()
        
        # Assert: Output indicates correction applied
        assert "corrected" in output.lower() or "fixed" in output.lower()
        
        # Assert: Exit code 1 (drift was corrected)
        assert exc_info.value.code == 1, "Should exit with code 1 when drift corrected"
        
        # Assert: cached_balance corrected to 120
        wallet.refresh_from_db()
        assert wallet.cached_balance == expected_balance, f"Balance should be corrected to {expected_balance}"
        
        # Assert: Balance matches ledger sum
        ledger_sum = DeltaCrownTransaction.objects.filter(wallet=wallet).aggregate(total=Sum('amount'))['total']
        assert wallet.cached_balance == ledger_sum
    
    def test_multiple_wallets_selective_correction(self, multiple_wallets_with_drift):
        """
        Test: Command corrects only wallets with drift, leaves accurate wallets unchanged.
        
        Target: Selective correction logic
        """
        wallets_data = multiple_wallets_with_drift
        
        # Run command
        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command('recalc_all_wallets', stdout=out)
        
        output = out.getvalue()
        
        # Assert: Output indicates 3 wallets corrected (wallets 0, 2, 4)
        assert "3" in output or "three" in output.lower()
        
        # Assert: Exit code 1 (drift was corrected)
        assert exc_info.value.code == 1
        
        # Verify each wallet
        for wallet, expected_balance, had_drift in wallets_data:
            wallet.refresh_from_db()
            
            # All wallets should have correct balance after command
            assert wallet.cached_balance == expected_balance, f"Wallet {wallet.id} should have balance {expected_balance}"
            
            # Verify ledger sum matches
            ledger_sum = DeltaCrownTransaction.objects.filter(wallet=wallet).aggregate(total=Sum('amount'))['total']
            assert wallet.cached_balance == ledger_sum
    
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
        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command('recalc_all_wallets', '--dry-run', stdout=out)
        output = out.getvalue()
        
        # Assert: Drift detected message and exit code 1
        assert "drift" in output.lower()
        assert exc_info.value.code == 1
        
        # Real run → corrects drift, exit code 1 (drift was found)
        out2 = StringIO()
        with pytest.raises(SystemExit) as exc_info2:
            call_command('recalc_all_wallets', stdout=out2)
        output2 = out2.getvalue()
        
        assert "corrected" in output2.lower()
        assert exc_info2.value.code == 1
        
        # Subsequent run → no drift, exit code 0
        out3 = StringIO()
        with pytest.raises(SystemExit) as exc_info3:
            call_command('recalc_all_wallets', stdout=out3)
        output3 = out3.getvalue()
        
        assert "no drift" in output3.lower() or "all accurate" in output3.lower()
        assert exc_info3.value.code == 0
    
    def test_no_pii_in_output(self, wallet_with_drift):
        """
        Test: Command output contains wallet IDs only (no usernames, emails, or PII).
        
        Target: PART_2.3 Section 8 - PII discipline
        """
        wallet, expected_balance = wallet_with_drift
        
        # Run command
        out = StringIO()
        with pytest.raises(SystemExit):
            call_command('recalc_all_wallets', stdout=out)
        
        output = out.getvalue()
        
        # Assert: Wallet ID present
        assert str(wallet.id) in output
        
        # Assert: No PII (UUID usernames and emails should not appear)
        # The fixtures use UUID-based usernames/emails, verify none leak
        assert "@example.com" not in output, "Email should not appear in output"
        
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
    
    def test_empty_wallet_no_transactions(self, db):
        """
        Test: Wallet with no transactions recalculates to zero balance.
        
        Target: Edge case for new wallets
        """
        import uuid
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username=f"empty_{uuid.uuid4().hex[:8]}",
            email=f"empty_{uuid.uuid4().hex[:8]}@example.com"
        )
        # UserProfile auto-created by post_save signal
        profile = UserProfile.objects.get(user=user)
        
        # Create wallet with corrupted balance (should be 0)
        wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=500)
        
        # Run command
        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command('recalc_all_wallets', stdout=out)
        
        # Assert: Exit code 1 (drift was corrected)
        assert exc_info.value.code == 1
        
        # Assert: Balance corrected to 0
        wallet.refresh_from_db()
        assert wallet.cached_balance == 0
    
    def test_negative_balance_reconciliation(self, db):
        """
        Test: Wallet with negative balance (overdraft) reconciles correctly.
        
        Target: Overdraft wallet handling
        """
        import uuid
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username=f"overdraft_{uuid.uuid4().hex[:8]}",
            email=f"overdraft_{uuid.uuid4().hex[:8]}@example.com"
        )
        # UserProfile auto-created by post_save signal
        profile = UserProfile.objects.get(user=user)
        # Enable overdraft to allow negative balance
        wallet = DeltaCrownWallet.objects.create(profile=profile, cached_balance=0, allow_overdraft=True)
        
        # Create negative transaction (overdraft)
        DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=-50,
            reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST
        )
        
        # Corrupt balance
        DeltaCrownWallet.objects.filter(id=wallet.id).update(cached_balance=100)
        
        # Run command
        with pytest.raises(SystemExit) as exc_info:
            call_command('recalc_all_wallets')
        
        # Assert: Exit code 1 (drift was corrected)
        assert exc_info.value.code == 1
        
        # Assert: Balance corrected to -50
        wallet.refresh_from_db()
        assert wallet.cached_balance == -50


# ============================================================================
# Module Metadata
# ============================================================================

# Test count: 8 tests (all xfail pending implementation)
# Coverage target: ≥75% on management command
# Target files: apps/economy/management/commands/recalc_all_wallets.py
