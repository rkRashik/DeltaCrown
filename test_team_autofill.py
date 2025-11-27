#!/usr/bin/env python
"""Test script to check team auto-fill data"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.teams.models import Team, TeamMembership
from apps.user_profile.models import UserProfile
from django.contrib.auth import get_user_model

User = get_user_model()

# Get a superuser
u = User.objects.filter(is_superuser=True).first()
if not u:
    print("No superuser found")
    exit(1)

print(f"User: {u.username}")

# Get profile
profile = UserProfile.objects.filter(user=u).first()
if not profile:
    print("No profile found")
    exit(1)

print(f"Profile: {profile}")

# Get teams where user is captain
teams = Team.objects.filter(captain=profile, is_active=True)
print(f"\nCaptain of {teams.count()} teams")

if teams.count() == 0:
    print("\n⚠️ User is not captain of any teams")
    print("Creating a test team...")
    
    # Create a test team
    team = Team.objects.create(
        name="Test VALORANT Team",
        tag="TVT",
        game="VALORANT",
        captain=profile,
        is_active=True
    )
    print(f"✅ Created team: {team.name}")
    
    # Add test members
    print("\nAdding test members...")
    for i in range(1, 4):
        test_user = User.objects.create_user(
            username=f"testplayer{i}",
            email=f"testplayer{i}@example.com",
            password="testpass123"
        )
        test_profile, _ = UserProfile.objects.get_or_create(
            user=test_user,
            defaults={'display_name': f'TestPlayer{i}'}
        )
        
        TeamMembership.objects.create(
            team=team,
            profile=test_profile,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE,
            is_captain=False
        )
        print(f"  ✅ Added {test_user.username}")
else:
    team = teams.first()
    print(f"\nTeam found: {team.name}")
    
    # Check if we need to add test members
    existing_count = TeamMembership.objects.filter(team=team, status=TeamMembership.Status.ACTIVE).count()
    if existing_count < 4:
        print(f"\nAdding test members (current: {existing_count})...")
        for i in range(1, 4):
            username = f"testplayer{i}"
            test_user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f"{username}@example.com",
                    'password': 'testpass123'
                }
            )
            test_profile, _ = UserProfile.objects.get_or_create(
                user=test_user,
                defaults={'display_name': f'TestPlayer{i}'}
            )
            
            membership, m_created = TeamMembership.objects.get_or_create(
                team=team,
                profile=test_profile,
                defaults={
                    'role': TeamMembership.Role.PLAYER,
                    'status': TeamMembership.Status.ACTIVE,
                    'is_captain': False
                }
            )
            if m_created:
                print(f"  ✅ Added {test_user.username}")
            else:
                print(f"  ℹ️ {test_user.username} already exists")

print(f"\nTeam: {team.name}")
print(f"Game: {team.game}")

# Get team members
members = TeamMembership.objects.filter(team=team, status=TeamMembership.Status.ACTIVE).select_related('profile__user')
print(f"\nActive Members: {members.count()}")

for m in members:
    print(f"  - {m.profile.user.username}")
    print(f"    is_captain: {m.is_captain}")
    print(f"    role: {m.role}")
    print(f"    profile.display_name: {m.profile.display_name}")
    print()

# Check non-captain members
non_captain_members = [m for m in members if not m.is_captain]
print(f"\nNon-captain members: {len(non_captain_members)}")
for m in non_captain_members:
    print(f"  - {m.profile.user.get_full_name() or m.profile.user.username}")

print("\n✅ Test complete")
