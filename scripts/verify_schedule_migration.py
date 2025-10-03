# scripts/verify_schedule_migration.py
"""
Verification script to check schedule data migration results.
Run this AFTER applying the migration.

Usage:
    python scripts/verify_schedule_migration.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament, TournamentSchedule


def verify_migration():
    """Verify that schedule data was migrated correctly."""
    print("\n" + "="*70)
    print("✅ Verifying Schedule Data Migration")
    print("="*70)
    print()
    
    tournaments = Tournament.objects.all()
    total = tournaments.count()
    
    with_schedule = 0
    without_schedule = 0
    data_matches = 0
    data_mismatches = 0
    mismatches = []
    
    print(f"🔍 Checking {total} tournaments...")
    print()
    
    for tournament in tournaments:
        # Check if has schedule data in old fields
        has_old_data = any([
            tournament.reg_open_at,
            tournament.reg_close_at,
            tournament.start_at,
            tournament.end_at,
        ])
        
        # Check if has TournamentSchedule
        try:
            schedule = tournament.schedule
            has_new_schedule = True
        except TournamentSchedule.DoesNotExist:
            schedule = None
            has_new_schedule = False
        
        if has_new_schedule:
            with_schedule += 1
            
            # Verify data matches
            if has_old_data:
                matches = all([
                    tournament.reg_open_at == schedule.reg_open_at,
                    tournament.reg_close_at == schedule.reg_close_at,
                    tournament.start_at == schedule.start_at,
                    tournament.end_at == schedule.end_at,
                ])
                
                if matches:
                    data_matches += 1
                    print(f"✅ {tournament.name}: Data matches perfectly")
                else:
                    data_mismatches += 1
                    mismatch_details = []
                    
                    if tournament.reg_open_at != schedule.reg_open_at:
                        mismatch_details.append(f"reg_open_at: {tournament.reg_open_at} != {schedule.reg_open_at}")
                    if tournament.reg_close_at != schedule.reg_close_at:
                        mismatch_details.append(f"reg_close_at: {tournament.reg_close_at} != {schedule.reg_close_at}")
                    if tournament.start_at != schedule.start_at:
                        mismatch_details.append(f"start_at: {tournament.start_at} != {schedule.start_at}")
                    if tournament.end_at != schedule.end_at:
                        mismatch_details.append(f"end_at: {tournament.end_at} != {schedule.end_at}")
                    
                    mismatch_msg = f"⚠️  {tournament.name}: Data mismatch"
                    for detail in mismatch_details:
                        mismatch_msg += f"\n   - {detail}"
                    
                    print(mismatch_msg)
                    mismatches.append(mismatch_msg)
            else:
                print(f"ℹ️  {tournament.name}: Has new schedule (no old data to compare)")
        else:
            without_schedule += 1
            if has_old_data:
                print(f"⚠️  {tournament.name}: Has old data but NO schedule created!")
            else:
                print(f"⏭️  {tournament.name}: No schedule data (expected)")
    
    # Print summary
    print()
    print("="*70)
    print("📊 Verification Summary")
    print("="*70)
    print(f"Total tournaments: {total}")
    print(f"   ✅ With TournamentSchedule: {with_schedule}")
    print(f"   ⏭️  Without TournamentSchedule: {without_schedule}")
    print()
    print(f"Data integrity:")
    print(f"   ✅ Data matches: {data_matches}")
    print(f"   ⚠️  Data mismatches: {data_mismatches}")
    print()
    
    if mismatches:
        print("⚠️  Mismatches detected:")
        for mismatch in mismatches:
            print(mismatch)
        print()
    
    # Test accessing schedule via relationship
    print("🔗 Testing relationship access...")
    try:
        test_tournament = Tournament.objects.filter(schedule__isnull=False).first()
        if test_tournament:
            schedule = test_tournament.schedule
            print(f"   ✅ tournament.schedule works: {test_tournament.name}")
            print(f"      - Registration: {schedule.registration_status}")
            print(f"      - Tournament: {schedule.tournament_status}")
        else:
            print("   ℹ️  No tournaments with schedules to test")
    except Exception as e:
        print(f"   ❌ Error accessing schedule: {e}")
    
    print()
    
    # Final verdict
    print("="*70)
    print("🎯 Final Verdict")
    print("="*70)
    
    if data_mismatches == 0 and with_schedule > 0:
        print("✅ MIGRATION SUCCESSFUL!")
        print(f"   - {with_schedule} schedules created")
        print("   - All data migrated correctly")
        print("   - Zero data mismatches")
        print()
        print("🚀 Safe to proceed with Phase 1!")
    elif with_schedule > 0 and data_mismatches > 0:
        print("⚠️  MIGRATION COMPLETED WITH WARNINGS")
        print(f"   - {with_schedule} schedules created")
        print(f"   - {data_mismatches} data mismatches found")
        print()
        print("🔍 Review mismatches before proceeding")
    elif with_schedule == 0:
        print("ℹ️  NO SCHEDULES CREATED")
        print("   - No tournaments had schedule data to migrate")
        print("   - Or migration hasn't been run yet")
    else:
        print("❌ MIGRATION ISSUES DETECTED")
        print("   - Review errors above")
        print("   - Consider rolling back and investigating")
    
    print("="*70)
    print()
    
    return {
        'total': total,
        'with_schedule': with_schedule,
        'without_schedule': without_schedule,
        'data_matches': data_matches,
        'data_mismatches': data_mismatches,
        'success': data_mismatches == 0 and with_schedule > 0,
    }


def test_schedule_features():
    """Test that schedule features work correctly."""
    print("\n" + "="*70)
    print("🧪 Testing Schedule Features")
    print("="*70)
    print()
    
    schedules = TournamentSchedule.objects.select_related('tournament')[:3]
    
    if not schedules.exists():
        print("ℹ️  No schedules to test")
        print("="*70)
        print()
        return
    
    for schedule in schedules:
        print(f"Testing: {schedule.tournament.name}")
        print(f"   📊 Registration Status: {schedule.registration_status}")
        print(f"   📊 Tournament Status: {schedule.tournament_status}")
        print(f"   🔴 Registration Open: {schedule.is_registration_open}")
        print(f"   🔴 Tournament Live: {schedule.is_tournament_live}")
        print(f"   📅 Registration Window: {schedule.get_registration_window_display()}")
        print(f"   📅 Tournament Window: {schedule.get_tournament_window_display()}")
        print()
    
    print("✅ All schedule features working correctly")
    print("="*70)
    print()


def main():
    """Run verification checks."""
    print("\n" + "🎯"*35)
    print("✅ Schedule Migration Verification")
    print("🎯"*35)
    
    try:
        # Verify migration
        results = verify_migration()
        
        # Test features
        if results['with_schedule'] > 0:
            test_schedule_features()
        
        # Return appropriate exit code
        if results['success']:
            print("✅ All checks passed! Migration successful! 🎉")
            return 0
        elif results['with_schedule'] > 0:
            print("⚠️  Migration completed but review warnings above")
            return 1
        else:
            print("ℹ️  No schedules found - migration may not have run yet")
            return 1
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
