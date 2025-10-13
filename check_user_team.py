"""Check if test_admin user has a team"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile

User = get_user_model()

print("=" * 60)
print("USER TEAM CHECK")
print("=" * 60)

# Check test_admin
user = User.objects.filter(username='test_admin').first()
if not user:
    print("❌ test_admin user not found!")
else:
    print(f"✅ User: {user.username}")
    
    # Get profile
    profile = UserProfile.objects.filter(user=user).first()
    if not profile:
        print("❌ No profile found")
    else:
        print(f"✅ Profile: {profile.display_name}")
        
        # Check team membership
        try:
            from apps.teams.models import TeamMembership
            membership = TeamMembership.objects.filter(
                profile=profile,
                status='ACTIVE'
            ).first()
            
            if not membership:
                print("\n❌ NO ACTIVE TEAM MEMBERSHIP")
                print("This user cannot register for TEAM tournaments!")
                print("\nNeed to:")
                print("1. Create a team")
                print("2. Add test_admin as captain")
            else:
                print(f"\n✅ Team: {membership.team.name}")
                print(f"   Role: {membership.role}")
                print(f"   Status: {membership.status}")
        except Exception as e:
            print(f"\n❌ Error checking team: {e}")

print("\n" + "="*60)
