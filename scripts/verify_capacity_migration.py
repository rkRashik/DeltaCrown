"""
Post-Migration Verification for TournamentCapacity

Verifies that capacity data was migrated correctly from Tournament
to TournamentCapacity and checks data integrity.

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

from apps.tournaments.models import Tournament
from apps.tournaments.models.core import TournamentCapacity


def verify_migration():
    """Verify TournamentCapacity migration completed successfully"""
    
    print("=" * 70)
    print("🔍 Post-Migration Verification: TournamentCapacity")
    print("=" * 70)
    print()
    
    # Get all tournaments with slot_size
    tournaments_with_capacity = Tournament.objects.filter(
        slot_size__isnull=False
    ).order_by('-created_at')
    
    total_tournaments = tournaments_with_capacity.count()
    
    print(f"📊 Checking {total_tournaments} tournaments with capacity data...")
    print()
    
    # Track verification results
    results = {
        'total': total_tournaments,
        'verified': 0,
        'missing': 0,
        'mismatch': 0,
        'errors': []
    }
    
    missing_capacity = []
    data_mismatches = []
    verified_ok = []
    
    # Verify each tournament
    for tournament in tournaments_with_capacity:
        try:
            # Check if TournamentCapacity exists
            try:
                capacity = tournament.capacity
            except TournamentCapacity.DoesNotExist:
                results['missing'] += 1
                missing_capacity.append(tournament)
                print(f"❌ Missing capacity for '{tournament.name}'")
                continue
            
            # Verify data integrity
            issues = []
            
            # Check slot_size matches
            if capacity.slot_size != tournament.slot_size:
                issues.append(
                    f"slot_size mismatch: capacity={capacity.slot_size}, "
                    f"tournament={tournament.slot_size}"
                )
            
            # Check max_teams
            if capacity.max_teams != tournament.slot_size:
                issues.append(
                    f"max_teams should equal slot_size: "
                    f"max_teams={capacity.max_teams}, slot_size={tournament.slot_size}"
                )
            
            # Check team sizes based on game
            if tournament.game == 'valorant':
                if capacity.min_team_size != 5 or capacity.max_team_size != 7:
                    issues.append(
                        f"Valorant should be 5-7: got {capacity.min_team_size}-{capacity.max_team_size}"
                    )
            elif tournament.game == 'efootball':
                if capacity.min_team_size != 1 or capacity.max_team_size != 1:
                    issues.append(
                        f"eFootball should be 1-1: got {capacity.min_team_size}-{capacity.max_team_size}"
                    )
            
            # Check registration mode is set
            if not capacity.registration_mode:
                issues.append("registration_mode is not set")
            
            if issues:
                results['mismatch'] += 1
                data_mismatches.append({
                    'tournament': tournament,
                    'capacity': capacity,
                    'issues': issues
                })
                print(f"⚠️  Data issues for '{tournament.name}':")
                for issue in issues:
                    print(f"   • {issue}")
            else:
                results['verified'] += 1
                verified_ok.append({
                    'tournament': tournament,
                    'capacity': capacity
                })
                print(f"✅ Verified '{tournament.name}'")
                print(f"   Slots: {capacity.slot_size}, Teams: {capacity.max_teams}")
                print(f"   Team Size: {capacity.min_team_size}-{capacity.max_team_size}")
                print(f"   Mode: {capacity.get_registration_mode_display()}")
            
        except Exception as e:
            results['errors'].append(f"{tournament.name}: {str(e)}")
            print(f"❌ Error verifying '{tournament.name}': {e}")
    
    # Print summary
    print()
    print("=" * 70)
    print("📈 Verification Summary")
    print("=" * 70)
    print(f"Total tournaments checked:   {results['total']}")
    print(f"✅ Verified successfully:    {results['verified']}")
    print(f"❌ Missing capacity:         {results['missing']}")
    print(f"⚠️  Data mismatches:          {results['mismatch']}")
    print(f"❌ Errors:                   {len(results['errors'])}")
    print()
    
    # Calculate success rate
    if results['total'] > 0:
        success_rate = (results['verified'] / results['total']) * 100
        print(f"Success Rate: {success_rate:.1f}%")
    
    # Detailed results
    if missing_capacity:
        print()
        print("=" * 70)
        print("❌ Tournaments Missing TournamentCapacity")
        print("=" * 70)
        for t in missing_capacity:
            print(f"   • {t.name} (slot_size={t.slot_size})")
    
    if data_mismatches:
        print()
        print("=" * 70)
        print("⚠️  Tournaments with Data Mismatches")
        print("=" * 70)
        for item in data_mismatches:
            print(f"\n   {item['tournament'].name}:")
            for issue in item['issues']:
                print(f"      • {issue}")
    
    if results['errors']:
        print()
        print("=" * 70)
        print("❌ Errors Encountered")
        print("=" * 70)
        for error in results['errors']:
            print(f"   • {error}")
    
    # Test relationship access
    print()
    print("=" * 70)
    print("🔗 Testing Relationship Access")
    print("=" * 70)
    
    if verified_ok:
        sample = verified_ok[0]
        t = sample['tournament']
        c = sample['capacity']
        
        print(f"\nTesting with: {t.name}")
        
        # Test forward relationship (tournament -> capacity)
        try:
            test_capacity = t.capacity
            print(f"✅ Forward access: tournament.capacity works")
            print(f"   → {test_capacity}")
        except Exception as e:
            print(f"❌ Forward access failed: {e}")
        
        # Test reverse relationship (capacity -> tournament)
        try:
            test_tournament = c.tournament
            print(f"✅ Reverse access: capacity.tournament works")
            print(f"   → {test_tournament}")
        except Exception as e:
            print(f"❌ Reverse access failed: {e}")
        
        # Test computed properties
        print(f"\n📊 Computed Properties:")
        print(f"   is_full: {c.is_full}")
        print(f"   available_slots: {c.available_slots}")
        print(f"   progress: {c.registration_progress_percent}%")
        print(f"   can_accept: {c.can_accept_registrations}")
        print(f"   is_solo: {c.is_solo_tournament}")
    
    # Final verdict
    print()
    print("=" * 70)
    print("🎯 Final Verdict")
    print("=" * 70)
    
    if results['verified'] == results['total'] and results['total'] > 0:
        print("✅ MIGRATION SUCCESSFUL!")
        print("   All capacity data migrated correctly")
        print("   No data integrity issues found")
        print("   Relationships working properly")
        return True
    elif results['missing'] == 0 and results['mismatch'] == 0:
        print("ℹ️  MIGRATION COMPLETE (No Data)")
        print("   No tournaments had capacity data to migrate")
        return True
    else:
        print("⚠️  MIGRATION ISSUES DETECTED")
        if results['missing'] > 0:
            print(f"   • {results['missing']} tournaments missing TournamentCapacity")
        if results['mismatch'] > 0:
            print(f"   • {results['mismatch']} tournaments have data mismatches")
        if results['errors']:
            print(f"   • {len(results['errors'])} errors encountered")
        print("\n   Please review the issues above and re-run migration if needed")
        return False
    
    print()


if __name__ == '__main__':
    try:
        success = verify_migration()
        
        if success:
            print("\n✅ Verification complete - migration successful!")
            sys.exit(0)
        else:
            print("\n⚠️  Verification found issues - please review")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
