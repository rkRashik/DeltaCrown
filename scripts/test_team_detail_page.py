"""
Test script to verify team detail page renders without NoReverseMatch error.
Tests for Owner, Manager, Member, and Non-member roles.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamMembership

User = get_user_model()
client = Client()

# Get a test team
teams = Team.objects.all()[:1]
if not teams:
    print("❌ No teams found in database. Please create a team first.")
    exit(1)

team = teams[0]
print(f"🎮 Testing with team: {team.name} ({team.slug})")

# Get test users
users = User.objects.filter(is_active=True)[:4]
if not users:
    print("❌ No active users found. Please create users first.")
    exit(1)

print(f"\n📋 Testing team detail page: /teams/{team.slug}/\n")

# Test 1: Non-member (anonymous)
print("1️⃣  Testing as Non-member (anonymous)...")
client.logout()
response = client.get(f'/teams/{team.slug}/')
if response.status_code == 200:
    if b'Reverse for' not in response.content:
        print(f"   ✅ Status: {response.status_code} - No NoReverseMatch error")
    else:
        print(f"   ❌ Status: {response.status_code} - NoReverseMatch error found!")
        print(f"   Error snippet: {str(response.content[:500])}")
else:
    print(f"   ⚠️  Status: {response.status_code}")

# Test 2: Logged-in user who is team owner/captain
print("\n2️⃣  Testing as Team Owner/Captain...")
captain = team.captain.user if team.captain else None
if captain:
    client.force_login(captain)
    response = client.get(f'/teams/{team.slug}/')
    if response.status_code == 200:
        if b'Reverse for' not in response.content:
            print(f"   ✅ Status: {response.status_code} - No NoReverseMatch error")
            if b'Captain Dashboard' in response.content:
                print(f"   ✅ Captain Dashboard rendered")
        else:
            print(f"   ❌ Status: {response.status_code} - NoReverseMatch error found!")
            print(f"   Error snippet: {str(response.content[:500])}")
    else:
        print(f"   ⚠️  Status: {response.status_code}")
else:
    print("   ⚠️  No captain found for this team")

# Test 3: Manager role
print("\n3️⃣  Testing as Manager...")
managers = TeamMembership.objects.filter(team=team, role='MANAGER')[:1]
if managers:
    manager = managers[0].profile.user
    client.force_login(manager)
    response = client.get(f'/teams/{team.slug}/')
    if response.status_code == 200:
        if b'Reverse for' not in response.content:
            print(f"   ✅ Status: {response.status_code} - No NoReverseMatch error")
            if b'Manager Dashboard' in response.content:
                print(f"   ✅ Manager Dashboard rendered")
            if b'Manage Roster' in response.content:
                print(f"   ✅ Manager-specific 'Manage Roster' link present")
        else:
            print(f"   ❌ Status: {response.status_code} - NoReverseMatch error found!")
            print(f"   Error snippet: {str(response.content[:500])}")
    else:
        print(f"   ⚠️  Status: {response.status_code}")
else:
    print("   ⚠️  No managers found for this team")

# Test 4: Regular member
print("\n4️⃣  Testing as Regular Member...")
members = TeamMembership.objects.filter(team=team, role='PLAYER')[:1]
if members:
    member = members[0].profile.user
    client.force_login(member)
    response = client.get(f'/teams/{team.slug}/')
    if response.status_code == 200:
        if b'Reverse for' not in response.content:
            print(f"   ✅ Status: {response.status_code} - No NoReverseMatch error")
            if b'Member Dashboard' in response.content:
                print(f"   ✅ Member Dashboard rendered")
        else:
            print(f"   ❌ Status: {response.status_code} - NoReverseMatch error found!")
            print(f"   Error snippet: {str(response.content[:500])}")
    else:
        print(f"   ⚠️  Status: {response.status_code}")
else:
    print("   ⚠️  No regular members found for this team")

# Test 5: Coach role
print("\n5️⃣  Testing as Coach...")
coaches = TeamMembership.objects.filter(team=team, role='COACH')[:1]
if coaches:
    coach = coaches[0].profile.user
    client.force_login(coach)
    response = client.get(f'/teams/{team.slug}/')
    if response.status_code == 200:
        if b'Reverse for' not in response.content:
            print(f"   ✅ Status: {response.status_code} - No NoReverseMatch error")
            if b'Coach Tools' in response.content:
                print(f"   ✅ Coach-specific tools section rendered")
        else:
            print(f"   ❌ Status: {response.status_code} - NoReverseMatch error found!")
            print(f"   Error snippet: {str(response.content[:500])}")
    else:
        print(f"   ⚠️  Status: {response.status_code}")
else:
    print("   ⚠️  No coaches found for this team")

print("\n✅ All tests completed!")
