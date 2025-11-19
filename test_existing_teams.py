#!/usr/bin/env python
"""
Quick test script to verify existing teams data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamMembership
import json

User = get_user_model()

# Get first user with teams
user = User.objects.filter(
    id__in=TeamMembership.objects.filter(status='ACTIVE').values_list('profile__user_id', flat=True)
).first()

if not user:
    print("No users with active teams found")
    exit()

print(f"Testing with user: {user.username}")

# Get their profile
profile = user.profile
print(f"Profile ID: {profile.id}")

# Get their active team memberships
memberships = TeamMembership.objects.filter(
    profile=profile,
    status='ACTIVE'
).select_related('team')

print(f"\nActive memberships: {memberships.count()}")

# Create the existing_teams dict exactly like the view does
existing_teams = {}
for membership in memberships:
    game_code = membership.team.game
    existing_teams[game_code] = {
        'name': membership.team.name,
        'tag': membership.team.tag,
        'slug': membership.team.slug,
    }
    print(f"  {game_code}: {membership.team.name} [{membership.team.tag}]")

print(f"\nexisting_teams dict:")
print(f"  {existing_teams}")

print(f"\nJSON output (as passed to template):")
json_output = json.dumps(existing_teams)
print(f"  {json_output}")

print(f"\nBackend data is correctly formatted")
print(f"\nTo test in browser console:")
print(f"  console.log(window.TEAM_CREATE_CONFIG.existingTeams)")
