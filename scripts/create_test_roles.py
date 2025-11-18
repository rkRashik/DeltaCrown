"""
Create test users with Manager and Coach roles for testing.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamMembership
from apps.user_profile.models import UserProfile

User = get_user_model()

# Get a test team
team = Team.objects.first()
if not team:
    print("❌ No teams found. Please create a team first.")
    exit(1)

print(f"🎮 Working with team: {team.name} ({team.slug})")

# Create or get manager user
manager_user, created = User.objects.get_or_create(
    username='test_manager',
    defaults={
        'email': 'manager@test.com',
        'is_active': True,
    }
)
if created:
    manager_user.set_password('testpass123')
    manager_user.save()
    print(f"✅ Created manager user: {manager_user.username}")
else:
    print(f"✅ Using existing manager user: {manager_user.username}")

# Create or get manager profile
manager_profile, _ = UserProfile.objects.get_or_create(user=manager_user)

# Create or update manager membership
manager_membership, created = TeamMembership.objects.update_or_create(
    team=team,
    profile=manager_profile,
    defaults={
        'role': 'MANAGER',
    }
)
if created:
    print(f"✅ Created manager membership for {team.name}")
else:
    print(f"✅ Updated manager membership for {team.name}")

# Create or get coach user
coach_user, created = User.objects.get_or_create(
    username='test_coach',
    defaults={
        'email': 'coach@test.com',
        'is_active': True,
    }
)
if created:
    coach_user.set_password('testpass123')
    coach_user.save()
    print(f"✅ Created coach user: {coach_user.username}")
else:
    print(f"✅ Using existing coach user: {coach_user.username}")

# Create or get coach profile
coach_profile, _ = UserProfile.objects.get_or_create(user=coach_user)

# Create or update coach membership
coach_membership, created = TeamMembership.objects.update_or_create(
    team=team,
    profile=coach_profile,
    defaults={
        'role': 'COACH',
    }
)
if created:
    print(f"✅ Created coach membership for {team.name}")
else:
    print(f"✅ Updated coach membership for {team.name}")

print("\n✅ Test roles created successfully!")
print(f"\nYou can now test with:")
print(f"  - Manager: username='test_manager', password='testpass123'")
print(f"  - Coach: username='test_coach', password='testpass123'")
