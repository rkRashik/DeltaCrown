"""Debug script to check tournament registration status"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament, TournamentSchedule
from django.utils import timezone

print("=" * 60)
print("TOURNAMENT REGISTRATION DEBUG")
print("=" * 60)

# Check all test tournaments
tournaments = Tournament.objects.filter(name__icontains='test').order_by('name')

for t in tournaments:
    print(f"\n{'='*60}")
    print(f"Tournament: {t.name}")
    print(f"Slug: {t.slug}")
    print(f"Status: {t.status}")
    
    # Check schedule
    try:
        schedule = TournamentSchedule.objects.get(tournament=t)
        print(f"\n✅ Schedule exists:")
        print(f"  - reg_open_at: {schedule.reg_open_at}")
        print(f"  - reg_close_at: {schedule.reg_close_at}")
        print(f"  - is_registration_open: {schedule.is_registration_open}")
    except TournamentSchedule.DoesNotExist:
        print(f"\n❌ NO SCHEDULE EXISTS")
    
    # Check registration_open property
    print(f"\n🔍 tournament.registration_open: {t.registration_open}")
    
    # Check view context
    from apps.tournaments.views.helpers import register_url
    print(f"📍 register_url: {register_url(t)}")

print("\n" + "="*60)
print(f"Current time: {timezone.now()}")
print("="*60)
