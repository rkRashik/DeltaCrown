#!/usr/bin/env python
"""
Quick test script to verify team creation fix.
Tests that TeamService.create_team() works without captain FK.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings")
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from apps.teams.services.team_service import TeamService
from apps.teams.models import Team, TeamMembership

User = get_user_model()

def test_team_creation():
    """Test team creation with membership-based captain system"""
    print("\n" + "="*60)
    print("🧪 TESTING TEAM CREATION FIX")
    print("="*60)
    
    # Use first available UserProfile instead of creating new one
    profile = UserProfile.objects.filter(user__isnull=False).first()
    if not profile:
        print("❌ ERROR: No user profiles found in database!")
        print("   Please create a user profile first via admin or registration.")
        return False
    
    print(f"✅ Using existing profile: {profile.display_name} (@{profile.user.username})")
    
    # Clean up any existing test teams
    test_team_name = "Test Team Fix"
    Team.objects.filter(name=test_team_name).delete()
    print(f"🧹 Cleaned up existing test teams")
    
    # Test team creation
    print(f"\n📝 Creating team via TeamService.create_team()...")
    try:
        team = TeamService.create_team(
            name=test_team_name,
            captain_profile=profile,
            game="valorant",
            tag="TST",
            description="Test team for captain FK fix"
        )
        print(f"✅ Team created successfully!")
        print(f"   - ID: {team.id}")
        print(f"   - Name: {team.name}")
        print(f"   - Tag: {team.tag}")
        print(f"   - Slug: {team.slug}")
        print(f"   - Game: {team.game}")
        
        # Verify captain membership
        print(f"\n🔍 Verifying captain membership...")
        owner_membership = TeamMembership.objects.filter(
            team=team,
            profile=profile,
            role=TeamMembership.Role.OWNER,
            status=TeamMembership.Status.ACTIVE
        ).first()
        
        if owner_membership:
            print(f"✅ Captain membership found!")
            print(f"   - Profile: {owner_membership.profile.display_name}")
            print(f"   - Role: {owner_membership.role}")
            print(f"   - Status: {owner_membership.status}")
        else:
            print(f"❌ ERROR: No OWNER membership found!")
            return False
        
        # Verify effective_captain property
        print(f"\n🔍 Verifying effective_captain property...")
        effective_captain = team.effective_captain
        if effective_captain == profile:
            print(f"✅ effective_captain matches captain profile!")
            print(f"   - Captain: {effective_captain.display_name}")
        else:
            print(f"❌ ERROR: effective_captain doesn't match!")
            print(f"   - Expected: {profile.display_name}")
            print(f"   - Got: {effective_captain}")
            return False
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
        # Cleanup
        print(f"\n🧹 Cleaning up test data...")
        team.delete()
        print(f"✅ Test team deleted")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: Team creation failed!")
        print(f"   - Exception: {type(e).__name__}")
        print(f"   - Message: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_team_creation()
    exit(0 if success else 1)
