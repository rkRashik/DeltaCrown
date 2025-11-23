"""
Clean Database Script
Removes all data except superuser accounts
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament, Registration, Match, Bracket
from apps.teams.models import Team, TeamMembership
from apps.user_profile.models import UserProfile

User = get_user_model()

print("\n[*] Starting Database Cleanup...")
print("=" * 80)

# Get superuser IDs to preserve
superusers = User.objects.filter(is_superuser=True)
superuser_ids = list(superusers.values_list('id', flat=True))
print(f"\n[+] Found {len(superuser_ids)} superuser(s) to preserve")

# Delete in correct order (respecting foreign keys)
print("\n[*] Deleting data...")

# 1. Delete matches (depends on tournaments)
match_count = Match.objects.count()
Match.objects.all().delete()
print(f"   [+] Deleted {match_count} matches")

# 2. Delete brackets (depends on tournaments)
bracket_count = Bracket.objects.count()
Bracket.objects.all().delete()
print(f"   [+] Deleted {bracket_count} brackets")

# 3. Delete registrations (depends on tournaments and users)
registration_count = Registration.objects.count()
Registration.objects.all().delete()
print(f"   [+] Deleted {registration_count} registrations")

# 4. Delete tournaments
tournament_count = Tournament.objects.count()
Tournament.objects.all().delete()
print(f"   [+] Deleted {tournament_count} tournaments")

# 5. Delete team memberships
membership_count = TeamMembership.objects.count()
TeamMembership.objects.all().delete()
print(f"   [+] Deleted {membership_count} team memberships")

# 6. Delete teams
team_count = Team.objects.count()
Team.objects.all().delete()
print(f"   [+] Deleted {team_count} teams")

# 7. Delete non-superuser profiles
non_superuser_profiles = UserProfile.objects.exclude(user_id__in=superuser_ids)
profile_count = non_superuser_profiles.count()
non_superuser_profiles.delete()
print(f"   [+] Deleted {profile_count} user profiles")

# 8. Delete non-superuser users
non_superusers = User.objects.exclude(id__in=superuser_ids)
user_count = non_superusers.count()
non_superusers.delete()
print(f"   [+] Deleted {user_count} users")

print("\n[+] Database cleanup complete!")
print("=" * 80)

# Show what's left
remaining_users = User.objects.count()
remaining_profiles = UserProfile.objects.count()
remaining_teams = Team.objects.count()
remaining_tournaments = Tournament.objects.count()

print(f"\n[*] Remaining data:")
print(f"   Users: {remaining_users}")
print(f"   User Profiles: {remaining_profiles}")
print(f"   Teams: {remaining_teams}")
print(f"   Tournaments: {remaining_tournaments}")
print(f"\n[+] Only superuser(s) remain in the database")
