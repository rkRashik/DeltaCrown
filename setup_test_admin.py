"""Setup test_admin user with profile and team"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from apps.teams.models import Team, TeamMembership
from django.utils import timezone

User = get_user_model()

print("=" * 70)
print("SETTING UP test_admin USER FOR TESTING")
print("=" * 70)

# Get or create test_admin user
user, created = User.objects.get_or_create(
    username='test_admin',
    defaults={
        'email': 'admin@test.com',
        'first_name': 'Test',
        'last_name': 'Admin',
        'is_staff': True,
        'is_superuser': True,
    }
)

if created:
    user.set_password('admin123')
    user.save()
    print("✅ Created test_admin user")
else:
    print("✅ test_admin user exists")

# Create or get profile
profile, created = UserProfile.objects.get_or_create(
    user=user,
    defaults={
        'display_name': 'TestAdmin',
        'region': 'BD',
        'bio': 'Test admin user for tournament registration',
    }
)

if created:
    print("✅ Created UserProfile")
else:
    print("✅ UserProfile exists")
    # Update if needed
    if not profile.display_name:
        profile.display_name = 'TestAdmin'
    if not profile.region:
        profile.region = 'BD'
    profile.save()

# Create a test team or get existing one
try:
    team = Team.objects.get(tag='TEST')
    print(f"✅ Test team exists: {team.name}")
    # Update captain if needed
    if team.captain != profile:
        team.captain = profile
        team.save()
        print("   Updated team captain")
except Team.DoesNotExist:
    team = Team.objects.create(
        name='Test Elite Squad',
        tag='TEST',
        captain=profile,
        description='Test team for tournament registration',
        game='valorant',
    )
    print("✅ Created test team: Test Elite Squad")

# Create team membership or get existing
try:
    membership = TeamMembership.objects.get(team=team, profile=profile)
    print("✅ Team membership exists")
    # Update if needed
    if membership.role != 'CAPTAIN':
        membership.role = 'CAPTAIN'
        membership.status = 'ACTIVE'
        membership.save()
        print("   Updated to CAPTAIN role")
except TeamMembership.DoesNotExist:
    # Check if there's already a captain
    existing_captain = TeamMembership.objects.filter(
        team=team,
        role='CAPTAIN',
        status='ACTIVE'
    ).first()
    
    if existing_captain and existing_captain.profile != profile:
        # Demote existing captain
        existing_captain.role = 'MEMBER'
        existing_captain.save()
        print(f"   Demoted existing captain: {existing_captain.profile.display_name}")
    
    membership = TeamMembership.objects.create(
        team=team,
        profile=profile,
        role='CAPTAIN',
        status='ACTIVE',
        joined_at=timezone.now(),
    )
    print("✅ Created team membership (CAPTAIN)")

print("\n" + "=" * 70)
print("SETUP COMPLETE")
print("=" * 70)
print(f"✅ User: {user.username}")
print(f"✅ Email: {user.email}")
print(f"✅ Password: admin123")
print(f"✅ Profile: {profile.display_name}")
print(f"✅ Team: {team.name} [{team.tag}]")
print(f"✅ Role: {membership.role}")
print("\n🎯 test_admin can now register for both SOLO and TEAM tournaments!")
print("=" * 70)
