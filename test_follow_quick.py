"""
Quick Follow System Test
========================

Tests follow functionality using existing users.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.models_main import Follow, FollowRequest, UserProfile, PrivacySettings
from apps.user_profile.services.follow_service import FollowService

User = get_user_model()


def get_test_users():
    """Get two existing users for testing."""
    print("\n[*] Finding test users...")
    
    users = User.objects.filter(is_superuser=False, is_staff=False)[:2]
    
    if users.count() < 2:
        print("  [ERROR] Need at least 2 non-staff users in database")
        return None, None
    
    user1, user2 = users[0], users[1]
    print(f"  [OK] Found users: {user1.username}, {user2.username}")
    
    # Ensure they have profiles
    profile1, _ = UserProfile.objects.get_or_create(user=user1)
    profile2, _ = UserProfile.objects.get_or_create(user=user2)
    
    # Ensure they have privacy settings
    privacy1, _ = PrivacySettings.objects.get_or_create(user_profile=profile1)
    privacy2, _ = PrivacySettings.objects.get_or_create(user_profile=profile2)
    
    return user1, user2


def cleanup_follows(user1, user2):
    """Clean up any existing follows between users."""
    print("\n[*] Cleaning up existing follows...")
    
    Follow.objects.filter(follower=user1, following=user2).delete()
    Follow.objects.filter(follower=user2, following=user1).delete()
    
    profile1 = UserProfile.objects.get(user=user1)
    profile2 = UserProfile.objects.get(user=user2)
    
    FollowRequest.objects.filter(requester=profile1, target=profile2).delete()
    FollowRequest.objects.filter(requester=profile2, target=profile1).delete()
    
    print("  [OK] Cleanup complete")


def test_follow_service(user1, user2):
    """Test the FollowService directly."""
    print("\n" + "="*60)
    print("FOLLOW SERVICE TEST")
    print("="*60)
    
    profile1 = UserProfile.objects.get(user=user1)
    profile2 = UserProfile.objects.get(user=user2)
    privacy2 = PrivacySettings.objects.get(user_profile=profile2)
    
    # TEST 1: Follow public account
    print(f"\n[TEST 1] {user1.username} -> {user2.username} (public)")
    privacy2.is_private_account = False
    privacy2.save()
    
    try:
        obj, created = FollowService.follow_user(
            follower_user=user1,
            followee_username=user2.username
        )
        
        if isinstance(obj, Follow):
            print(f"  [PASS] Follow created (ID: {obj.id})")
        else:
            print(f"  [FAIL] Expected Follow, got {type(obj).__name__}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    # Clean up
    Follow.objects.filter(follower=user1, following=user2).delete()
    
    # TEST 2: Follow private account
    print(f"\n[TEST 2] {user1.username} -> {user2.username} (private)")
    privacy2.is_private_account = True
    privacy2.save()
    
    try:
        obj, created = FollowService.follow_user(
            follower_user=user1,
            followee_username=user2.username
        )
        
        if isinstance(obj, FollowRequest):
            print(f"  [PASS] FollowRequest created (ID: {obj.id}, Status: {obj.status})")
            
            # TEST 3: Approve the request
            print(f"\n[TEST 3] Approve follow request")
            try:
                follow = FollowService.approve_follow_request(
                    target_user=user2,
                    request_id=obj.id
                )
                print(f"  [PASS] Request approved, Follow created (ID: {follow.id})")
            except Exception as e:
                print(f"  [ERROR] Approval failed: {e}")
                
        else:
            print(f"  [FAIL] Expected FollowRequest, got {type(obj).__name__}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


def main():
    user1, user2 = get_test_users()
    
    if not user1 or not user2:
        print("\n[ERROR] Cannot run tests without 2 users")
        return False
    
    cleanup_follows(user1, user2)
    test_follow_service(user1, user2)
    cleanup_follows(user1, user2)
    
    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
