#!/usr/bin/env python
"""Test validation endpoints to ensure they work correctly."""
import django
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.organizations.models import Team, TeamMembership
from apps.games.models import Game

User = get_user_model()

# Get or create test user
user = User.objects.filter(username='rkrashik').first()
if not user:
    print("❌ Test user 'rkrashik' not found")
    sys.exit(1)

print(f"✅ Testing with user: {user.username} (ID: {user.id})")

# Check existing teams
existing_teams = Team.objects.filter(
    vnext_memberships__user=user,
    vnext_memberships__status='ACTIVE',
    status='ACTIVE',
    organization__isnull=True
)

print(f"\n📊 User's existing independent teams:")
for team in existing_teams:
    print(f"  - {team.name} (Game: {team.game_id}, Slug: {team.slug})")

# Test validation endpoint
client = Client()
client.force_login(user)

print("\n🧪 Testing validation endpoint:")
print("-" * 60)

# Test 1: Check if user can create team for game 1 (has existing team)
response = client.get('/api/vnext/teams/validate-name/', {
    'name': '_check_ownership_',
    'game_slug': 'pubg-mobile',  # Adjust based on your game slug
    'mode': 'independent'
})

print(f"\n1️⃣ Ownership check for PUBG:")
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 2: Check specific name
response = client.get('/api/vnext/teams/validate-name/', {
    'name': 'Test New Team',
    'game_slug': 'pubg-mobile',
    'mode': 'independent'
})

print(f"\n2️⃣ Name validation for 'Test New Team':")
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 3: Check for game without existing team
response = client.get('/api/vnext/teams/validate-name/', {
    'name': 'New Team',
    'game_slug': 'valorant',  # Different game
    'mode': 'independent'
})

print(f"\n3️⃣ Name validation for Valorant (different game):")
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

print("\n" + "=" * 60)
print("✅ Validation endpoint tests complete")
