"""
Pre-migration analysis for TournamentFinance data migration.

This script analyzes existing Tournament financial data to:
1. Identify tournaments with entry fees and prize pools
2. Detect data patterns and ranges
3. Check for potential migration issues
4. Provide migration statistics

Run this BEFORE creating the data migration.
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings")
django.setup()

from django.db import connection
from django.db.models import Q
from apps.tournaments.models import Tournament
from apps.tournaments.models.core import TournamentFinance


def print_header(text):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def analyze_existing_finance_data():
    """Analyze existing finance data in Tournament model."""
    print_header("1. EXISTING FINANCE DATA ANALYSIS")
    
    tournaments = Tournament.objects.all()
    total_count = tournaments.count()
    
    # Count tournaments with financial data
    with_entry_fee = tournaments.filter(entry_fee_bdt__isnull=False, entry_fee_bdt__gt=0).count()
    with_prize_pool = tournaments.filter(prize_pool_bdt__isnull=False, prize_pool_bdt__gt=0).count()
    with_either = tournaments.filter(
        Q(entry_fee_bdt__isnull=False, entry_fee_bdt__gt=0) |
        Q(prize_pool_bdt__isnull=False, prize_pool_bdt__gt=0)
    ).count()
    
    print(f"📊 Total Tournaments: {total_count}")
    print(f"💰 With Entry Fee: {with_entry_fee} ({with_entry_fee/total_count*100:.1f}%)")
    print(f"🏆 With Prize Pool: {with_prize_pool} ({with_prize_pool/total_count*100:.1f}%)")
    print(f"💵 With Any Finance Data: {with_either} ({with_either/total_count*100:.1f}%)")
    print(f"🆓 Free Tournaments: {total_count - with_either}")
    
    return with_either


def show_finance_details():
    """Show detailed finance information for each tournament."""
    print_header("2. TOURNAMENT FINANCE DETAILS")
    
    from django.db.models import Q
    
    tournaments = Tournament.objects.filter(
        Q(entry_fee_bdt__isnull=False, entry_fee_bdt__gt=0) |
        Q(prize_pool_bdt__isnull=False, prize_pool_bdt__gt=0)
    ).order_by('-created_at')
    
    if not tournaments.exists():
        print("ℹ️  No tournaments with financial data found.")
        return []
    
    migration_candidates = []
    
    for t in tournaments:
        entry_fee = t.entry_fee_bdt or Decimal('0')
        prize_pool = t.prize_pool_bdt or Decimal('0')
        
        print(f"\n🎮 Tournament: {t.name}")
        print(f"   ID: {t.id} | Status: {t.status} | Game: {t.game}")
        print(f"   💰 Entry Fee: ৳{entry_fee:,.2f}")
        print(f"   🏆 Prize Pool: ৳{prize_pool:,.2f}")
        
        if entry_fee > 0 or prize_pool > 0:
            migration_candidates.append({
                'id': t.id,
                'name': t.name,
                'entry_fee': entry_fee,
                'prize_pool': prize_pool,
                'status': t.status
            })
    
    return migration_candidates


def analyze_finance_ranges():
    """Analyze the range of financial values."""
    print_header("3. FINANCIAL DATA RANGES")
    
    from django.db.models import Min, Max, Avg, Count, Q
    
    # Entry fee statistics
    entry_stats = Tournament.objects.filter(
        entry_fee_bdt__isnull=False,
        entry_fee_bdt__gt=0
    ).aggregate(
        min_fee=Min('entry_fee_bdt'),
        max_fee=Max('entry_fee_bdt'),
        avg_fee=Avg('entry_fee_bdt'),
        count=Count('id')
    )
    
    # Prize pool statistics
    prize_stats = Tournament.objects.filter(
        prize_pool_bdt__isnull=False,
        prize_pool_bdt__gt=0
    ).aggregate(
        min_prize=Min('prize_pool_bdt'),
        max_prize=Max('prize_pool_bdt'),
        avg_prize=Avg('prize_pool_bdt'),
        count=Count('id')
    )
    
    if entry_stats['count'] > 0:
        print("💰 ENTRY FEE STATISTICS:")
        print(f"   Count: {entry_stats['count']}")
        print(f"   Min: ৳{entry_stats['min_fee']:,.2f}")
        print(f"   Max: ৳{entry_stats['max_fee']:,.2f}")
        print(f"   Avg: ৳{entry_stats['avg_fee']:,.2f}")
    else:
        print("💰 ENTRY FEE: No data")
    
    print()
    
    if prize_stats['count'] > 0:
        print("🏆 PRIZE POOL STATISTICS:")
        print(f"   Count: {prize_stats['count']}")
        print(f"   Min: ৳{prize_stats['min_prize']:,.2f}")
        print(f"   Max: ৳{prize_stats['max_prize']:,.2f}")
        print(f"   Avg: ৳{prize_stats['avg_prize']:,.2f}")
    else:
        print("🏆 PRIZE POOL: No data")


def check_existing_finance_records():
    """Check if any TournamentFinance records already exist."""
    print_header("4. EXISTING TOURNAMENTFINANCE RECORDS")
    
    existing_count = TournamentFinance.objects.count()
    
    if existing_count > 0:
        print(f"⚠️  WARNING: Found {existing_count} existing TournamentFinance records!")
        print(f"   Migration should be idempotent and skip these.")
        
        # Show which tournaments already have finance records
        existing_tournament_ids = list(
            TournamentFinance.objects.values_list('tournament_id', flat=True)
        )
        print(f"   Tournament IDs with finance records: {existing_tournament_ids}")
    else:
        print(f"✅ No existing TournamentFinance records - clean slate for migration")
    
    return existing_count


def check_data_quality():
    """Check for potential data quality issues."""
    print_header("5. DATA QUALITY CHECKS")
    
    issues_found = []
    
    # Check for negative values
    negative_fee = Tournament.objects.filter(entry_fee_bdt__lt=0).count()
    negative_prize = Tournament.objects.filter(prize_pool_bdt__lt=0).count()
    
    if negative_fee > 0:
        issues_found.append(f"⚠️  {negative_fee} tournament(s) with negative entry fee")
    
    if negative_prize > 0:
        issues_found.append(f"⚠️  {negative_prize} tournament(s) with negative prize pool")
    
    # Check for very large values (potential data entry errors)
    very_large_fee = Tournament.objects.filter(entry_fee_bdt__gt=100000).count()
    very_large_prize = Tournament.objects.filter(prize_pool_bdt__gt=1000000).count()
    
    if very_large_fee > 0:
        issues_found.append(f"⚠️  {very_large_fee} tournament(s) with entry fee > ৳100,000")
    
    if very_large_prize > 0:
        issues_found.append(f"⚠️  {very_large_prize} tournament(s) with prize pool > ৳1,000,000")
    
    # Check for small non-zero values (might be test data)
    small_fee = Tournament.objects.filter(
        entry_fee_bdt__gt=0,
        entry_fee_bdt__lt=10
    ).count()
    
    if small_fee > 0:
        issues_found.append(f"ℹ️  {small_fee} tournament(s) with very small entry fee (< ৳10)")
    
    if issues_found:
        print("Issues detected:")
        for issue in issues_found:
            print(f"  {issue}")
    else:
        print("✅ No data quality issues detected")
    
    return len(issues_found)


def generate_migration_plan(candidates):
    """Generate the migration execution plan."""
    print_header("6. MIGRATION EXECUTION PLAN")
    
    if not candidates:
        print("ℹ️  No tournaments need finance data migration.")
        print("   All tournaments appear to be free (no entry fee or prize pool).")
        return
    
    print(f"📋 Will create {len(candidates)} TournamentFinance records:")
    print()
    
    for i, candidate in enumerate(candidates, 1):
        print(f"{i}. Tournament ID {candidate['id']}: {candidate['name']}")
        print(f"   Entry Fee: ৳{candidate['entry_fee']:,.2f}")
        print(f"   Prize Pool: ৳{candidate['prize_pool']:,.2f}")
        print(f"   Status: {candidate['status']}")
        print()
    
    print("📝 Migration Strategy:")
    print("   1. Check if TournamentFinance record exists (idempotent)")
    print("   2. Copy entry_fee_bdt → TournamentFinance.entry_fee_bdt")
    print("   3. Copy prize_pool_bdt → TournamentFinance.prize_pool_bdt")
    print("   4. Set currency to 'BDT' (default)")
    print("   5. Set payment_required based on entry_fee > 0")
    print("   6. Leave prize_distribution as empty dict (can be configured later)")


def main():
    """Run the complete pre-migration analysis."""
    print("\n" + "🔍 " + "="*66)
    print("  TOURNAMENTFINANCE PRE-MIGRATION ANALYSIS")
    print("="*70)
    print(f"  Date: October 3, 2025")
    print("="*70)
    
    try:
        # Run all analyses
        finance_count = analyze_existing_finance_data()
        candidates = show_finance_details()
        analyze_finance_ranges()
        existing_records = check_existing_finance_records()
        issues = check_data_quality()
        generate_migration_plan(candidates)
        
        # Final summary
        print_header("7. SUMMARY")
        
        print(f"📊 Total tournaments to migrate: {len(candidates)}")
        print(f"📋 Existing TournamentFinance records: {existing_records}")
        print(f"⚠️  Data quality issues: {issues}")
        
        if issues > 0:
            print(f"\n⚠️  RECOMMENDATION: Review and fix data quality issues before migration")
        else:
            print(f"\n✅ Analysis complete - ready for migration!")
        
        print(f"\n📝 Next steps:")
        print(f"   1. Review this analysis output")
        print(f"   2. Fix any data quality issues (if needed)")
        print(f"   3. Create migration 0036_migrate_finance_data.py")
        print(f"   4. Run: python manage.py migrate tournaments")
        print(f"   5. Verify: python scripts/verify_finance_migration.py")
        
    except Exception as e:
        print(f"\n❌ ERROR during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
