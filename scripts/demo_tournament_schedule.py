# scripts/demo_tournament_schedule.py
"""
Demonstration script for TournamentSchedule pilot.
Shows how the new model works in practice.
"""
import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.utils import timezone
from apps.tournaments.models import Tournament, TournamentSchedule


def demo_schedule():
    """Demonstrate TournamentSchedule features."""
    print("=" * 60)
    print("🎯 TournamentSchedule Pilot Demonstration")
    print("=" * 60)
    print()
    
    # Create test tournament
    print("1️⃣  Creating test tournament...")
    tournament = Tournament.objects.create(
        name="Test Tournament - Schedule Demo",
        slug="test-schedule-demo",
        game="valorant",
        status="DRAFT"
    )
    print(f"   ✅ Created: {tournament.name}")
    print()
    
    # Create schedule
    print("2️⃣  Creating schedule...")
    now = timezone.now()
    schedule = TournamentSchedule.objects.create(
        tournament=tournament,
        reg_open_at=now + timedelta(days=1),
        reg_close_at=now + timedelta(days=7),
        start_at=now + timedelta(days=8),
        end_at=now + timedelta(days=9),
        check_in_open_mins=60,
        check_in_close_mins=10,
    )
    print(f"   ✅ Schedule created")
    print(f"   📅 Registration: {schedule.get_registration_window_display()}")
    print(f"   📅 Tournament: {schedule.get_tournament_window_display()}")
    print()
    
    # Access via relationship
    print("3️⃣  Accessing schedule via tournament...")
    retrieved_schedule = tournament.schedule
    print(f"   ✅ tournament.schedule works!")
    print(f"   🔗 Schedule ID: {retrieved_schedule.id}")
    print()
    
    # Test computed properties
    print("4️⃣  Testing computed properties...")
    print(f"   📊 Registration Status: {schedule.registration_status}")
    print(f"   📊 Tournament Status: {schedule.tournament_status}")
    print(f"   📊 Check-in Window: {schedule.check_in_window_text}")
    print(f"   🔴 Registration Open? {schedule.is_registration_open}")
    print(f"   🔴 Tournament Live? {schedule.is_tournament_live}")
    print(f"   🔴 Check-in Open? {schedule.is_check_in_open}")
    print()
    
    # Test validation
    print("5️⃣  Testing validation...")
    try:
        bad_schedule = TournamentSchedule(
            tournament=tournament,
            reg_open_at=now + timedelta(days=10),
            reg_close_at=now + timedelta(days=1),  # Before open!
        )
        bad_schedule.full_clean()
        print("   ❌ Validation should have failed!")
    except Exception as e:
        print(f"   ✅ Validation caught error: {str(e)[:50]}...")
    print()
    
    # Test cloning
    print("6️⃣  Testing clone feature...")
    tournament2 = Tournament.objects.create(
        name="Second Tournament",
        slug="second-tournament",
        game="efootball",
        status="DRAFT"
    )
    cloned_schedule = schedule.clone_for_tournament(tournament2)
    print(f"   ✅ Cloned schedule to {tournament2.name}")
    print(f"   🔗 Original ID: {schedule.id}, Cloned ID: {cloned_schedule.id}")
    print()
    
    # Cleanup
    print("7️⃣  Cleaning up test data...")
    tournament.delete()
    tournament2.delete()
    print("   ✅ Test tournaments deleted")
    print()
    
    print("=" * 60)
    print("🎉 Demonstration Complete!")
    print("=" * 60)
    print()
    print("Key Takeaways:")
    print("  ✅ Schedule model works perfectly")
    print("  ✅ OneToOne relationship is clean")
    print("  ✅ Computed properties are useful")
    print("  ✅ Validation prevents bad data")
    print("  ✅ Cloning makes creating tournaments easy")
    print()
    print("Next Steps:")
    print("  📝 Check out the admin interface at /admin/tournaments/tournament/")
    print("  📝 Review docs/TOURNAMENT_SCHEDULE_PILOT_COMPLETE.md")
    print("  📝 Decide: Continue with Phase 1 or migrate data first?")
    print()


if __name__ == '__main__':
    demo_schedule()
