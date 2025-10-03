"""
Pre-Migration Analysis for TournamentCapacity

Analyzes existing Tournament data to prepare for capacity migration.
Shows what data will be migrated and identifies any potential issues.

Author: DeltaCrown Development Team
Date: October 3, 2025
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db.models import Q
from apps.tournaments.models import Tournament
from apps.tournaments.models.core import TournamentCapacity


def analyze_tournaments():
    """Analyze existing tournaments for capacity migration"""
    
    print("=" * 70)
    print("🔍 Pre-Migration Analysis: TournamentCapacity")
    print("=" * 70)
    print()
    
    # Get all tournaments
    tournaments = Tournament.objects.all().order_by('-created_at')
    total = tournaments.count()
    
    print(f"📊 Found {total} tournaments to analyze...")
    print()
    
    # Track statistics
    stats = {
        'total': total,
        'with_capacity': 0,
        'without_capacity': 0,
        'already_migrated': 0,
        'need_migration': 0,
        'slot_sizes': {},
    }
    
    # Analyze each tournament
    migration_candidates = []
    already_has_capacity = []
    no_capacity_data = []
    
    for tournament in tournaments:
        # Check if already has TournamentCapacity
        try:
            if hasattr(tournament, 'capacity') and tournament.capacity:
                stats['already_migrated'] += 1
                already_has_capacity.append(tournament)
                continue
        except TournamentCapacity.DoesNotExist:
            pass
        
        # Check if has slot_size data to migrate
        if tournament.slot_size:
            stats['with_capacity'] += 1
            stats['need_migration'] += 1
            migration_candidates.append(tournament)
            
            # Track slot_size distribution
            size = tournament.slot_size
            stats['slot_sizes'][size] = stats['slot_sizes'].get(size, 0) + 1
        else:
            stats['without_capacity'] += 1
            no_capacity_data.append(tournament)
    
    # Print statistics
    print("=" * 70)
    print("📈 Migration Statistics")
    print("=" * 70)
    print(f"Total tournaments:           {stats['total']}")
    print(f"Already migrated:            {stats['already_migrated']}")
    print(f"Need migration:              {stats['need_migration']}")
    print(f"No capacity data:            {stats['without_capacity']}")
    print()
    
    # Slot size distribution
    if stats['slot_sizes']:
        print("📊 Slot Size Distribution:")
        for size in sorted(stats['slot_sizes'].keys()):
            count = stats['slot_sizes'][size]
            print(f"  {size:3d} slots: {count} tournaments")
        print()
    
    # Show migration candidates
    if migration_candidates:
        print("=" * 70)
        print(f"✅ Tournaments Ready for Migration ({len(migration_candidates)})")
        print("=" * 70)
        for t in migration_candidates:
            # Determine team sizes based on game
            if t.game == 'valorant':
                min_size, max_size = 5, 7
                game_name = "Valorant (5v5)"
            elif t.game == 'efootball':
                min_size, max_size = 1, 1
                game_name = "eFootball (1v1)"
            else:
                min_size, max_size = 1, 10
                game_name = f"{t.game} (unknown)"
            
            print(f"\n🎮 {t.name}")
            print(f"   Game: {game_name}")
            print(f"   Slot Size: {t.slot_size}")
            print(f"   Team Size: {min_size}-{max_size} players")
            print(f"   Status: {t.status}")
            print(f"   Created: {t.created_at.strftime('%Y-%m-%d')}")
    
    # Show already migrated
    if already_has_capacity:
        print()
        print("=" * 70)
        print(f"ℹ️  Already Have TournamentCapacity ({len(already_has_capacity)})")
        print("=" * 70)
        for t in already_has_capacity:
            print(f"   • {t.name}")
    
    # Show no data tournaments
    if no_capacity_data:
        print()
        print("=" * 70)
        print(f"⚠️  No Capacity Data ({len(no_capacity_data)})")
        print("=" * 70)
        print("These tournaments will be skipped (no slot_size):")
        for t in no_capacity_data:
            print(f"   • {t.name} (Status: {t.status})")
    
    # Migration plan
    print()
    print("=" * 70)
    print("📋 Migration Plan")
    print("=" * 70)
    print(f"Will create:  {stats['need_migration']} TournamentCapacity records")
    print(f"Will skip:    {stats['already_migrated']} (already migrated)")
    print(f"Will skip:    {stats['without_capacity']} (no capacity data)")
    print()
    
    # Default values that will be used
    print("🔧 Default Values for Migration:")
    print("   • max_teams = slot_size")
    print("   • registration_mode = 'open'")
    print("   • waitlist_enabled = True")
    print("   • current_registrations = 0 (will sync after)")
    print()
    print("   Game-specific team sizes:")
    print("   • Valorant: min=5, max=7 (5v5 with subs)")
    print("   • eFootball: min=1, max=1 (1v1)")
    print("   • Other: min=1, max=10 (flexible)")
    print()
    
    # Potential issues
    print("=" * 70)
    print("⚠️  Potential Issues")
    print("=" * 70)
    
    issues_found = False
    
    # Check for unusually small slot sizes
    small_slots = [t for t in migration_candidates if t.slot_size < 4]
    if small_slots:
        issues_found = True
        print(f"\n⚠️  {len(small_slots)} tournaments with very small capacity (<4):")
        for t in small_slots:
            print(f"   • {t.name}: {t.slot_size} slots")
    
    # Check for unusually large slot sizes
    large_slots = [t for t in migration_candidates if t.slot_size > 128]
    if large_slots:
        issues_found = True
        print(f"\n⚠️  {len(large_slots)} tournaments with very large capacity (>128):")
        for t in large_slots:
            print(f"   • {t.name}: {t.slot_size} slots")
    
    if not issues_found:
        print("✅ No issues detected - all capacity values look reasonable")
    
    print()
    print("=" * 70)
    print("🎯 Ready to Proceed")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review the migration candidates above")
    print("2. Run: python manage.py migrate tournaments")
    print("3. Run: python scripts/verify_capacity_migration.py")
    print()
    
    return stats


if __name__ == '__main__':
    try:
        stats = analyze_tournaments()
        
        if stats['need_migration'] > 0:
            print("✅ Analysis complete - ready for migration!")
            sys.exit(0)
        else:
            print("ℹ️  No tournaments need migration")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
