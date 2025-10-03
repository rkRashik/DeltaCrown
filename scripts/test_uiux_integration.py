#!/usr/bin/env python
"""
Quick Test Script for UI/UX Phase B Integration
Creates test tournament with countdown timers
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament
from apps.tournaments.models.phase1 import TournamentSchedule, TournamentCapacity
from django.utils import timezone
from datetime import timedelta

def create_test_tournament():
    """Create or update test tournament with countdown-friendly dates"""
    
    print("=" * 60)
    print("UI/UX Phase B - Creating Test Tournament")
    print("=" * 60)
    print()
    
    # Get or create test tournament
    t, created = Tournament.objects.get_or_create(
        slug="ui-test-tournament",
        defaults={
            "title": "UI Test Tournament (Countdown Demo)",
            "game": "valorant",
            "status": "draft"
        }
    )
    
    if created:
        print(f"✅ Created new tournament: {t.title}")
    else:
        print(f"✅ Using existing tournament: {t.title}")
        t.title = "UI Test Tournament (Countdown Demo)"
        t.save()
    
    # Create/update schedule with near-future dates
    schedule, _ = TournamentSchedule.objects.get_or_create(tournament=t)
    
    now = timezone.now()
    schedule.registration_open_at = now - timedelta(hours=2)  # Opened 2 hours ago
    schedule.registration_close_at = now + timedelta(minutes=45)  # Closes in 45 min
    schedule.start_at = now + timedelta(hours=1, minutes=30)  # Starts in 1.5 hours
    schedule.end_at = now + timedelta(hours=5)  # Ends in 5 hours
    schedule.save()
    
    print(f"⏱️  Registration opened: 2 hours ago")
    print(f"⏱️  Registration closes: in 45 minutes (URGENT countdown!)")
    print(f"⏱️  Tournament starts: in 1 hour 30 minutes")
    print()
    
    # Create/update capacity (81% full - should show ORANGE)
    capacity, _ = TournamentCapacity.objects.get_or_create(tournament=t)
    capacity.max_teams = 16
    capacity.current_teams = 13  # 81% full
    capacity.save()
    
    print(f"📊 Capacity: {capacity.current_teams}/{capacity.max_teams} ({capacity.current_teams/capacity.max_teams*100:.0f}% full)")
    print(f"   Expected: ORANGE capacity bar (75-89% threshold)")
    print()
    
    # URLs
    detail_url = f"http://localhost:8000/tournaments/{t.slug}/"
    hub_url = "http://localhost:8000/tournaments/"
    
    print("=" * 60)
    print("✅ Test Tournament Ready!")
    print("=" * 60)
    print()
    print("🔗 URLs to test:")
    print(f"   Hub:    {hub_url}")
    print(f"   Detail: {detail_url}")
    print()
    print("🧪 What to check:")
    print("   ✅ Countdown timer visible in Quick Facts")
    print("   ✅ Countdown shows ~45 minutes (registration closing)")
    print("   ✅ Countdown updates every second")
    print("   ✅ Countdown has ORANGE/YELLOW color (urgent state)")
    print("   ✅ Capacity bar shows 81% filled")
    print("   ✅ Capacity bar has ORANGE color")
    print("   ✅ Browser console shows initialization logs")
    print()
    print("📝 Browser Console Expected Output:")
    print("   [CountdownTimer] Found 1 countdown timer(s)")
    print("   [CountdownTimer] Initialized timer 1: {type: 'registration-close', ...}")
    print("   [TournamentPoller] Starting poller for: ui-test-tournament")
    print()
    print("=" * 60)
    print("🚀 Start the server:")
    print("   python manage.py runserver")
    print("=" * 60)
    
    return t

if __name__ == '__main__':
    create_test_tournament()
