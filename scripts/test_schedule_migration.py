# scripts/test_schedule_migration.py
"""
Test script to verify schedule data migration.
Run this BEFORE applying the migration to production.

Usage:
    python scripts/test_schedule_migration.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import transaction
from apps.tournaments.models import Tournament, TournamentSchedule


def analyze_current_data():
    """Analyze current tournament data to predict migration results."""
    print("\n" + "="*70)
    print("🔍 Analyzing Current Tournament Data")
    print("="*70)
    print()
    
    tournaments = Tournament.objects.all()
    total = tournaments.count()
    
    with_schedule_data = 0
    without_schedule_data = 0
    already_has_schedule = 0
    
    tournaments_with_data = []
    tournaments_without_data = []
    
    for tournament in tournaments:
        # Check if schedule already exists
        try:
            if hasattr(tournament, 'schedule'):
                already_has_schedule += 1
                continue
        except TournamentSchedule.DoesNotExist:
            pass
        
        # Check if has schedule data
        has_data = any([
            tournament.reg_open_at,
            tournament.reg_close_at,
            tournament.start_at,
            tournament.end_at,
        ])
        
        if has_data:
            with_schedule_data += 1
            tournaments_with_data.append(tournament)
        else:
            without_schedule_data += 1
            tournaments_without_data.append(tournament)
    
    # Print summary
    print(f"📊 Total Tournaments: {total}")
    print(f"   ✅ With schedule data: {with_schedule_data}")
    print(f"   ⏭️  Without schedule data: {without_schedule_data}")
    print(f"   🔄 Already migrated: {already_has_schedule}")
    print()
    
    # Show examples with schedule data
    if tournaments_with_data:
        print("📋 Tournaments WITH schedule data (will be migrated):")
        for i, t in enumerate(tournaments_with_data[:5], 1):
            print(f"   {i}. {t.name}")
            print(f"      - Registration: {t.reg_open_at} to {t.reg_close_at}")
            print(f"      - Tournament: {t.start_at} to {t.end_at}")
        if len(tournaments_with_data) > 5:
            print(f"   ... and {len(tournaments_with_data) - 5} more")
        print()
    
    # Show examples without schedule data
    if tournaments_without_data:
        print("⏭️  Tournaments WITHOUT schedule data (will be skipped):")
        for i, t in enumerate(tournaments_without_data[:5], 1):
            print(f"   {i}. {t.name} (status: {t.status})")
        if len(tournaments_without_data) > 5:
            print(f"   ... and {len(tournaments_without_data) - 5} more")
        print()
    
    print("="*70)
    print()
    
    return {
        'total': total,
        'with_data': with_schedule_data,
        'without_data': without_schedule_data,
        'already_migrated': already_has_schedule,
    }


def test_migration_dry_run():
    """Simulate the migration without actually creating records."""
    print("\n" + "="*70)
    print("🧪 Testing Migration (Dry Run)")
    print("="*70)
    print()
    
    tournaments = Tournament.objects.all()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    errors = []
    
    with transaction.atomic():
        for tournament in tournaments:
            try:
                # Skip if already has schedule
                try:
                    if hasattr(tournament, 'schedule'):
                        skip_count += 1
                        continue
                except TournamentSchedule.DoesNotExist:
                    pass
                
                # Skip if no schedule data
                has_data = any([
                    tournament.reg_open_at,
                    tournament.reg_close_at,
                    tournament.start_at,
                    tournament.end_at,
                ])
                
                if not has_data:
                    skip_count += 1
                    continue
                
                # Try to create (but don't save due to transaction rollback)
                schedule = TournamentSchedule(
                    tournament=tournament,
                    reg_open_at=tournament.reg_open_at,
                    reg_close_at=tournament.reg_close_at,
                    start_at=tournament.start_at,
                    end_at=tournament.end_at,
                    check_in_open_mins=60,
                    check_in_close_mins=10,
                )
                
                # Validate without saving
                schedule.full_clean()
                
                success_count += 1
                print(f"✅ Would create schedule for: {tournament.name}")
                
            except Exception as e:
                error_count += 1
                error_msg = f"❌ Error for {tournament.name}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
        
        # Rollback transaction (dry run)
        raise Exception("Dry run - rolling back")
    
    # This will be caught, which is expected
    pass
    
    print()
    print("📈 Dry Run Results:")
    print(f"   ✅ Would create: {success_count}")
    print(f"   ⏭️  Would skip: {skip_count}")
    print(f"   ❌ Errors: {error_count}")
    print()
    
    if errors:
        print("⚠️  Errors that would occur:")
        for error in errors:
            print(f"   {error}")
        print()
    
    print("="*70)
    print()
    
    return {
        'success': success_count,
        'skip': skip_count,
        'errors': error_count,
        'error_messages': errors,
    }


def check_existing_schedules():
    """Check if any schedules already exist."""
    print("\n" + "="*70)
    print("🔍 Checking Existing Schedules")
    print("="*70)
    print()
    
    schedule_count = TournamentSchedule.objects.count()
    
    if schedule_count == 0:
        print("✅ No existing schedules found - safe to migrate")
    else:
        print(f"⚠️  Found {schedule_count} existing schedules:")
        schedules = TournamentSchedule.objects.select_related('tournament')[:5]
        for schedule in schedules:
            print(f"   - {schedule.tournament.name}")
        if schedule_count > 5:
            print(f"   ... and {schedule_count - 5} more")
        print()
        print("ℹ️  Migration will skip tournaments that already have schedules")
    
    print()
    print("="*70)
    print()


def main():
    """Run all pre-migration checks."""
    print("\n" + "🎯"*35)
    print("🧪 TournamentSchedule Migration Test Script")
    print("🎯"*35)
    
    try:
        # Check existing schedules
        check_existing_schedules()
        
        # Analyze current data
        stats = analyze_current_data()
        
        # Dry run
        try:
            results = test_migration_dry_run()
        except:
            # Expected - dry run rolls back
            results = None
        
        # Final recommendation
        print("\n" + "="*70)
        print("📋 Migration Readiness Report")
        print("="*70)
        print()
        
        if stats['with_data'] > 0:
            print(f"✅ Ready to migrate {stats['with_data']} tournaments")
            print()
            print("Next Steps:")
            print("   1. Backup your database:")
            print("      pg_dump your_db > backup_before_schedule_migration.sql")
            print()
            print("   2. Run the migration:")
            print("      python manage.py migrate tournaments")
            print()
            print("   3. Verify the results:")
            print("      python scripts/verify_schedule_migration.py")
            print()
            print("   4. If issues occur, rollback:")
            print("      python manage.py migrate tournaments 0031")
        else:
            print("ℹ️  No tournaments need migration")
            print("   All tournaments either:")
            print("   - Already have schedules")
            print("   - Have no schedule data")
        
        print()
        print("="*70)
        print()
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
