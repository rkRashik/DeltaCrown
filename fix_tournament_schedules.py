#!/usr/bin/env python
"""
Fix Tournament Schedules - Ensure all test tournaments have registration open

This script updates all test tournaments to ensure they have proper schedule
data with registration currently open.
"""

import os
import sys
import django
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.utils import timezone
from apps.tournaments.models import Tournament
from apps.tournaments.models.core.tournament_schedule import TournamentSchedule

def fix_schedules():
    """Update all test tournaments to have registration open"""
    
    print("=" * 80)
    print("  🔧 FIXING TOURNAMENT SCHEDULES")
    print("=" * 80)
    print()
    
    # Get all test tournaments
    tournaments = Tournament.objects.filter(name__icontains='test').select_related('schedule')
    
    if not tournaments:
        print("❌ No test tournaments found!")
        return
    
    print(f"Found {tournaments.count()} test tournaments\n")
    
    now = timezone.now()
    updated_count = 0
    created_count = 0
    
    for tournament in tournaments:
        print(f"Processing: {tournament.name}")
        
        # Check if schedule exists
        if hasattr(tournament, 'schedule') and tournament.schedule:
            # Update existing schedule
            schedule = tournament.schedule
            schedule.reg_open_at = now - timedelta(days=1)  # Opened yesterday
            schedule.reg_close_at = now + timedelta(days=30)  # Closes in 30 days
            schedule.start_at = now + timedelta(days=35)  # Starts in 35 days
            schedule.end_at = now + timedelta(days=37)  # Ends in 37 days
            schedule.check_in_open_mins = 120  # 2 hours before
            schedule.check_in_close_mins = 15  # 15 mins before
            schedule.save()
            print(f"  ✅ Updated schedule")
            updated_count += 1
        else:
            # Create new schedule
            schedule = TournamentSchedule.objects.create(
                tournament=tournament,
                reg_open_at=now - timedelta(days=1),
                reg_close_at=now + timedelta(days=30),
                start_at=now + timedelta(days=35),
                end_at=now + timedelta(days=37),
                check_in_open_mins=120,
                check_in_close_mins=15,
            )
            print(f"  ✅ Created schedule")
            created_count += 1
        
        # Verify registration is open
        is_open = schedule.is_registration_open
        status = "✅ OPEN" if is_open else "❌ CLOSED"
        print(f"  📅 Registration status: {status}")
        print(f"  📅 Opens: {schedule.reg_open_at}")
        print(f"  📅 Closes: {schedule.reg_close_at}")
        print()
    
    print("=" * 80)
    print(f"  ✅ SCHEDULE FIX COMPLETE")
    print("=" * 80)
    print(f"Updated: {updated_count}")
    print(f"Created: {created_count}")
    print(f"Total: {updated_count + created_count}")
    print()
    print("All test tournaments now have registration OPEN! 🎉")
    print()

if __name__ == '__main__':
    fix_schedules()
