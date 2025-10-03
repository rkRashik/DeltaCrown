"""
Post-migration verification for TournamentFinance data migration.

This script verifies that:
1. All financial data was migrated correctly
2. TournamentFinance records match Tournament data
3. Relationships are working properly
4. Computed properties function correctly
5. No data was lost or corrupted

Run this AFTER the data migration.
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings")
django.setup()

from apps.tournaments.models import Tournament
from apps.tournaments.models.core import TournamentFinance


def print_header(text):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def verify_migration_completeness():
    """Verify all tournaments with financial data have TournamentFinance records."""
    print_header("1. MIGRATION COMPLETENESS CHECK")
    
    from django.db.models import Q
    
    # Find tournaments with financial data
    tournaments_with_finance = Tournament.objects.filter(
        Q(entry_fee_bdt__isnull=False, entry_fee_bdt__gt=0) |
        Q(prize_pool_bdt__isnull=False, prize_pool_bdt__gt=0)
    )
    
    total_with_finance = tournaments_with_finance.count()
    migrated_count = TournamentFinance.objects.count()
    
    print(f"📊 Tournaments with financial data: {total_with_finance}")
    print(f"📋 TournamentFinance records created: {migrated_count}")
    
    if total_with_finance == migrated_count:
        print(f"✅ PASS: All tournaments migrated ({migrated_count}/{total_with_finance})")
        return True
    else:
        missing = total_with_finance - migrated_count
        print(f"❌ FAIL: Missing {missing} TournamentFinance record(s)")
        
        # Show which tournaments are missing
        migrated_ids = set(TournamentFinance.objects.values_list('tournament_id', flat=True))
        for t in tournaments_with_finance:
            if t.id not in migrated_ids:
                print(f"   Missing: Tournament #{t.id} - {t.name}")
        
        return False


def verify_data_accuracy():
    """Verify that migrated data matches source data exactly."""
    print_header("2. DATA ACCURACY VERIFICATION")
    
    finance_records = TournamentFinance.objects.select_related('tournament')
    
    all_match = True
    verified_count = 0
    mismatch_count = 0
    
    for finance in finance_records:
        tournament = finance.tournament
        
        # Get expected values
        expected_entry = tournament.entry_fee_bdt or Decimal('0')
        expected_prize = tournament.prize_pool_bdt or Decimal('0')
        
        # Get actual values
        actual_entry = finance.entry_fee_bdt
        actual_prize = finance.prize_pool_bdt
        
        # Compare
        entry_match = expected_entry == actual_entry
        prize_match = expected_prize == actual_prize
        
        if entry_match and prize_match:
            print(f"✅ Tournament #{tournament.id}: {tournament.name}")
            print(f"   Entry Fee: ৳{actual_entry:,.2f} ✓")
            print(f"   Prize Pool: ৳{actual_prize:,.2f} ✓")
            verified_count += 1
        else:
            print(f"❌ Tournament #{tournament.id}: {tournament.name}")
            if not entry_match:
                print(f"   Entry Fee MISMATCH: Expected ৳{expected_entry:,.2f}, Got ৳{actual_entry:,.2f}")
            if not prize_match:
                print(f"   Prize Pool MISMATCH: Expected ৳{expected_prize:,.2f}, Got ৳{actual_prize:,.2f}")
            mismatch_count += 1
            all_match = False
    
    print(f"\n📊 Verified: {verified_count}/{finance_records.count()}")
    
    if all_match:
        print(f"✅ PASS: All financial data matches exactly")
        return True
    else:
        print(f"❌ FAIL: Found {mismatch_count} mismatch(es)")
        return False


def verify_relationships():
    """Verify that relationships work correctly."""
    print_header("3. RELATIONSHIP VERIFICATION")
    
    all_working = True
    
    # Test forward relationship (TournamentFinance → Tournament)
    finance_records = TournamentFinance.objects.select_related('tournament')
    
    print("🔗 Forward Relationship (TournamentFinance → Tournament):")
    for finance in finance_records:
        try:
            tournament_name = finance.tournament.name
            print(f"   ✅ Finance #{finance.id} → Tournament: {tournament_name}")
        except Exception as e:
            print(f"   ❌ Finance #{finance.id} → ERROR: {e}")
            all_working = False
    
    # Test reverse relationship (Tournament → TournamentFinance)
    from django.db.models import Q
    tournaments = Tournament.objects.filter(
        Q(entry_fee_bdt__isnull=False, entry_fee_bdt__gt=0) |
        Q(prize_pool_bdt__isnull=False, prize_pool_bdt__gt=0)
    )
    
    print("\n🔗 Reverse Relationship (Tournament → TournamentFinance):")
    for tournament in tournaments:
        try:
            # Try to access finance through reverse relationship
            finance = tournament.finance
            print(f"   ✅ Tournament #{tournament.id} → Finance: ৳{finance.entry_fee_bdt:,.2f} entry")
        except TournamentFinance.DoesNotExist:
            print(f"   ❌ Tournament #{tournament.id} → No finance record found")
            all_working = False
        except Exception as e:
            print(f"   ❌ Tournament #{tournament.id} → ERROR: {e}")
            all_working = False
    
    if all_working:
        print(f"\n✅ PASS: All relationships working correctly")
        return True
    else:
        print(f"\n❌ FAIL: Some relationships not working")
        return False


def verify_computed_properties():
    """Verify that computed properties work correctly."""
    print_header("4. COMPUTED PROPERTIES VERIFICATION")
    
    finance_records = TournamentFinance.objects.all()
    
    all_working = True
    
    for finance in finance_records:
        tournament = finance.tournament
        print(f"\n🎮 Tournament: {tournament.name}")
        
        try:
            # Test has_entry_fee
            has_fee = finance.has_entry_fee
            expected_has_fee = finance.entry_fee_bdt > 0
            if has_fee == expected_has_fee:
                print(f"   ✅ has_entry_fee: {has_fee}")
            else:
                print(f"   ❌ has_entry_fee: Expected {expected_has_fee}, Got {has_fee}")
                all_working = False
            
            # Test is_free
            is_free = finance.is_free
            expected_free = finance.entry_fee_bdt == 0
            if is_free == expected_free:
                print(f"   ✅ is_free: {is_free}")
            else:
                print(f"   ❌ is_free: Expected {expected_free}, Got {is_free}")
                all_working = False
            
            # Test has_prize_pool
            has_prize = finance.has_prize_pool
            expected_has_prize = finance.prize_pool_bdt > 0
            if has_prize == expected_has_prize:
                print(f"   ✅ has_prize_pool: {has_prize}")
            else:
                print(f"   ❌ has_prize_pool: Expected {expected_has_prize}, Got {has_prize}")
                all_working = False
            
            # Test formatted displays
            formatted_entry = finance.formatted_entry_fee
            formatted_prize = finance.formatted_prize_pool
            print(f"   ✅ formatted_entry_fee: {formatted_entry}")
            print(f"   ✅ formatted_prize_pool: {formatted_prize}")
            
            # Test payment_required consistency
            if finance.has_entry_fee and not finance.payment_required:
                print(f"   ⚠️  WARNING: Has entry fee but payment not required")
            elif not finance.has_entry_fee and finance.payment_required:
                print(f"   ❌ ERROR: No entry fee but payment required")
                all_working = False
            else:
                print(f"   ✅ payment_required: {finance.payment_required}")
            
        except Exception as e:
            print(f"   ❌ ERROR testing properties: {e}")
            all_working = False
    
    if all_working:
        print(f"\n✅ PASS: All computed properties working correctly")
        return True
    else:
        print(f"\n❌ FAIL: Some computed properties not working")
        return False


def verify_defaults():
    """Verify that default values were set correctly."""
    print_header("5. DEFAULT VALUES VERIFICATION")
    
    finance_records = TournamentFinance.objects.all()
    
    all_correct = True
    
    for finance in finance_records:
        print(f"\n🎮 Tournament: {finance.tournament.name}")
        
        # Check currency
        if finance.currency == 'BDT':
            print(f"   ✅ currency: {finance.currency}")
        else:
            print(f"   ❌ currency: Expected 'BDT', Got '{finance.currency}'")
            all_correct = False
        
        # Check payment_deadline_hours
        if finance.payment_deadline_hours == 72:
            print(f"   ✅ payment_deadline_hours: {finance.payment_deadline_hours}")
        else:
            print(f"   ⚠️  payment_deadline_hours: {finance.payment_deadline_hours} (non-default)")
        
        # Check prize_distribution
        if isinstance(finance.prize_distribution, dict):
            print(f"   ✅ prize_distribution: {type(finance.prize_distribution).__name__} (empty: {len(finance.prize_distribution) == 0})")
        else:
            print(f"   ❌ prize_distribution: Expected dict, Got {type(finance.prize_distribution).__name__}")
            all_correct = False
        
        # Check platform_fee_percent
        if finance.platform_fee_percent == Decimal('0'):
            print(f"   ✅ platform_fee_percent: {finance.platform_fee_percent}%")
        else:
            print(f"   ⚠️  platform_fee_percent: {finance.platform_fee_percent}% (non-default)")
    
    if all_correct:
        print(f"\n✅ PASS: All default values correct")
        return True
    else:
        print(f"\n❌ FAIL: Some default values incorrect")
        return False


def generate_summary_stats():
    """Generate summary statistics."""
    print_header("6. MIGRATION SUMMARY STATISTICS")
    
    from django.db.models import Sum, Avg, Min, Max, Count
    
    stats = TournamentFinance.objects.aggregate(
        total_records=Count('id'),
        total_entry_fees=Sum('entry_fee_bdt'),
        total_prize_pools=Sum('prize_pool_bdt'),
        avg_entry_fee=Avg('entry_fee_bdt'),
        min_entry_fee=Min('entry_fee_bdt'),
        max_entry_fee=Max('entry_fee_bdt'),
        avg_prize_pool=Avg('prize_pool_bdt'),
        min_prize_pool=Min('prize_pool_bdt'),
        max_prize_pool=Max('prize_pool_bdt'),
    )
    
    with_payment = TournamentFinance.objects.filter(payment_required=True).count()
    free_tournaments = TournamentFinance.objects.filter(payment_required=False).count()
    with_prizes = TournamentFinance.objects.filter(prize_pool_bdt__gt=0).count()
    
    print(f"📊 Total Records: {stats['total_records']}")
    print(f"💰 With Payment Required: {with_payment}")
    print(f"🆓 Free Tournaments: {free_tournaments}")
    print(f"🏆 With Prize Pools: {with_prizes}")
    print()
    print(f"💵 ENTRY FEES:")
    print(f"   Total: ৳{stats['total_entry_fees'] or 0:,.2f}")
    print(f"   Average: ৳{stats['avg_entry_fee'] or 0:,.2f}")
    print(f"   Range: ৳{stats['min_entry_fee'] or 0:,.2f} - ৳{stats['max_entry_fee'] or 0:,.2f}")
    print()
    print(f"🏆 PRIZE POOLS:")
    print(f"   Total: ৳{stats['total_prize_pools'] or 0:,.2f}")
    print(f"   Average: ৳{stats['avg_prize_pool'] or 0:,.2f}")
    print(f"   Range: ৳{stats['min_prize_pool'] or 0:,.2f} - ৳{stats['max_prize_pool'] or 0:,.2f}")


def main():
    """Run the complete verification suite."""
    print("\n" + "🔍 " + "="*66)
    print("  TOURNAMENTFINANCE POST-MIGRATION VERIFICATION")
    print("="*70)
    print(f"  Date: October 3, 2025")
    print("="*70)
    
    results = []
    
    try:
        # Run all verification checks
        results.append(("Completeness", verify_migration_completeness()))
        results.append(("Data Accuracy", verify_data_accuracy()))
        results.append(("Relationships", verify_relationships()))
        results.append(("Computed Properties", verify_computed_properties()))
        results.append(("Default Values", verify_defaults()))
        generate_summary_stats()
        
        # Final summary
        print_header("7. FINAL VERIFICATION SUMMARY")
        
        total_checks = len(results)
        passed_checks = sum(1 for _, passed in results if passed)
        failed_checks = total_checks - passed_checks
        success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        print("📋 Verification Results:")
        for check_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status}: {check_name}")
        
        print(f"\n📊 Success Rate: {passed_checks}/{total_checks} ({success_rate:.1f}%)")
        
        if failed_checks == 0:
            print(f"\n🎉 ✅ MIGRATION SUCCESSFUL! All finance data migrated correctly.")
            print(f"{'='*70}\n")
            return 0
        else:
            print(f"\n⚠️  ❌ MIGRATION HAD ISSUES: {failed_checks} check(s) failed.")
            print(f"{'='*70}\n")
            return 1
        
    except Exception as e:
        print(f"\n❌ ERROR during verification: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
