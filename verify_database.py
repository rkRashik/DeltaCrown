"""Quick database verification script"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament, Match, Registration
from apps.teams.models import Team
from apps.accounts.models import User

print("\n" + "="*70)
print("DATABASE VERIFICATION")
print("="*70)

# Basic counts
print(f"\n[COUNTS]")
print(f"Users: {User.objects.count()}")
print(f"Teams: {Team.objects.count()}")
print(f"Tournaments: {Tournament.objects.count()}")
print(f"Registrations: {Registration.objects.filter(status='confirmed').count()}")
print(f"Matches: {Match.objects.count()}")
print(f"  - Completed: {Match.objects.filter(state=Match.COMPLETED).count()}")
print(f"  - Scheduled: {Match.objects.filter(state=Match.SCHEDULED).count()}")

# Tournament breakdown
print(f"\n[TOURNAMENTS BY STATUS]")
for status in [Tournament.COMPLETED, Tournament.LIVE, Tournament.REGISTRATION_OPEN]:
    count = Tournament.objects.filter(status=status).count()
    print(f"{status}: {count}")

# Matches per tournament
print(f"\n[MATCHES PER TOURNAMENT]")
for tournament in Tournament.objects.all().order_by('name'):
    match_count = tournament.matches.count()
    completed_count = tournament.matches.filter(state=Match.COMPLETED).count()
    scheduled_count = tournament.matches.filter(state=Match.SCHEDULED).count()
    print(f"{tournament.name} ({tournament.status}): {match_count} matches ({completed_count} completed, {scheduled_count} scheduled)")

# Sample team check (verify slugs)
print(f"\n[SAMPLE TEAMS - SLUG VERIFICATION]")
for team in Team.objects.all()[:5]:
    print(f"  {team.name} -> slug: {team.slug}")

print("\n" + "="*70)
print("[SUCCESS] Database verification complete!")
print("="*70 + "\n")
