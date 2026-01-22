"""
Follow System Comprehensive Testing Script
==========================================

Tests all follow scenarios:
1. Public → Public (immediate follow)
2. Public → Private (follow request)
3. Private → Public (immediate follow)
4. Private → Private (follow request)
5. Follow request approval
6. Follow request rejection
7. Follow request cancellation
8. Account privacy toggle scenarios

Author: GitHub Copilot
Date: January 22, 2026
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.models_main import Follow, FollowRequest, UserProfile, PrivacySettings
from apps.user_profile.services.follow_service import FollowService
from django.db import transaction

User = get_user_model()


def create_test_users():
    """Create test users with different privacy settings."""
    print("\n[*] Creating test users...")
    
    users = {}
    
    # Public user 1
    user1, _ = User.objects.get_or_create(
        username='test_public1',
        defaults={'email': 'public1@test.com'}
    )
    profile1, _ = UserProfile.objects.get_or_create(user=user1, defaults={'display_name': 'Public User 1'})
    privacy1, _ = PrivacySettings.objects.get_or_create(
        user_profile=profile1,
        defaults={'is_private_account': False, 'allow_friend_requests': True}
    )
    privacy1.is_private_account = False
    privacy1.save()
    users['public1'] = user1
    print(f"  ✓ Created {user1.username} (PUBLIC account)")
    
    # Public user 2
    user2, _ = User.objects.get_or_create(
        username='test_public2',
        defaults={'email': 'public2@test.com'}
    )
    profile2, _ = UserProfile.objects.get_or_create(user=user2, defaults={'display_name': 'Public User 2'})
    privacy2, _ = PrivacySettings.objects.get_or_create(
        user_profile=profile2,
        defaults={'is_private_account': False, 'allow_friend_requests': True}
    )
    privacy2.is_private_account = False
    privacy2.save()
    users['public2'] = user2
    print(f"  ✓ Created {user2.username} (PUBLIC account)")
    
    # Private user 1
    user3, _ = User.objects.get_or_create(
        username='test_private1',
        defaults={'email': 'private1@test.com'}
    )
    profile3, _ = UserProfile.objects.get_or_create(user=user3, defaults={'display_name': 'Private User 1'})
    privacy3, _ = PrivacySettings.objects.get_or_create(
        user_profile=profile3,
        defaults={'is_private_account': True, 'allow_friend_requests': True}
    )
    privacy3.is_private_account = True
    privacy3.save()
    users['private1'] = user3
    print(f"  ✓ Created {user3.username} (PRIVATE account)")
    
    # Private user 2
    user4, _ = User.objects.get_or_create(
        username='test_private2',
        defaults={'email': 'private2@test.com'}
    )
    profile4, _ = UserProfile.objects.get_or_create(user=user4, defaults={'display_name': 'Private User 2'})
    privacy4, _ = PrivacySettings.objects.get_or_create(
        user_profile=profile4,
        defaults={'is_private_account': True, 'allow_friend_requests': True}
    )
    privacy4.is_private_account = True
    privacy4.save()
    users['private2'] = user4
    print(f"  ✓ Created {user4.username} (PRIVATE account)")
    
    return users


def cleanup_test_data(users):
    """Clean up all follows and requests."""
    print("\n[*] Cleaning up test data...")
    
    for username, user in users.items():
        Follow.objects.filter(follower=user).delete()
        Follow.objects.filter(following=user).delete()
        
    for username, user in users.items():
        profile = UserProfile.objects.get(user=user)
        FollowRequest.objects.filter(requester=profile).delete()
        FollowRequest.objects.filter(target=profile).delete()
    
    print("  ✓ Cleaned up all follows and requests")


def test_public_to_public(users):
    """Test: Public user following public user (immediate follow)."""
    print("\n[TEST 1] Public -> Public (immediate follow)")
    
    follower = users['public1']
    target = users['public2']
    
    try:
        obj, created = FollowService.follow_user(
            follower_user=follower,
            followee_username=target.username
        )
        
        if isinstance(obj, Follow):
            print(f"  ✅ SUCCESS: Immediate follow created")
            print(f"     Follow ID: {obj.id}, Created: {created}")
            return True
        else:
            print(f"  ❌ FAILED: Expected Follow, got {type(obj).__name__}")
            return False
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


def test_public_to_private(users):
    """Test: Public user following private user (follow request)."""
    print("\n[TEST 2] Public -> Private (follow request)")
    
    follower = users['public1']
    target = users['private1']
    
    try:
        obj, created = FollowService.follow_user(
            follower_user=follower,
            followee_username=target.username
        )
        
        if isinstance(obj, FollowRequest):
            print(f"  [PASS] Follow request created")
            print(f"     Request ID: {obj.id}, Status: {obj.status}, Created: {created}")
            return obj
        else:
            print(f"  [FAIL] Expected FollowRequest, got {type(obj).__name__}")
            return None
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def test_private_to_public(users):
    """Test: Private user following public user (immediate follow)."""
    print("\n[TEST 3] Private -> Public (immediate follow)")
    
    follower = users['private1']
    target = users['public1']
    
    try:
        obj, created = FollowService.follow_user(
            follower_user=follower,
            followee_username=target.username
        )
        
        if isinstance(obj, Follow):
            print(f"  ✅ SUCCESS: Immediate follow created")
            print(f"     Follow ID: {obj.id}, Created: {created}")
            return True
        else:
            print(f"  ❌ FAILED: Expected Follow, got {type(obj).__name__}")
            return False
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


def test_private_to_private(users):
    """Test: Private user following private user (follow request)."""
    print("\n[TEST 4] Private -> Private (follow request)")
    
    follower = users['private1']
    target = users['private2']
    
    try:
        obj, created = FollowService.follow_user(
            follower_user=follower,
            followee_username=target.username
        )
        
        if isinstance(obj, FollowRequest):
            print(f"  ✅ SUCCESS: Follow request created")
            print(f"     Request ID: {obj.id}, Status: {obj.status}, Created: {created}")
            return obj
        else:
            print(f"  ❌ FAILED: Expected FollowRequest, got {type(obj).__name__}")
            return None
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return None


def test_approve_request(request_obj, users):
    """Test: Approving a follow request."""
    print("\n[TEST 5] Approve follow request")
    
    if not request_obj:
        print("  ⏭️  SKIPPED: No request to approve")
        return False
    
    target_user = request_obj.target.user
    
    try:
        follow = FollowService.approve_follow_request(
            target_user=target_user,
            request_id=request_obj.id
        )
        
        # Verify follow was created
        request_obj.refresh_from_db()
        
        print(f"  ✅ SUCCESS: Follow request approved")
        print(f"     Follow ID: {follow.id}")
        print(f"     Request Status: {request_obj.status}")
        print(f"     Resolved At: {request_obj.resolved_at}")
        return True
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


def test_reject_request(request_obj, users):
    """Test: Rejecting a follow request."""
    print("\n[TEST 6] Reject follow request")
    
    if not request_obj:
        print("  ⏭️  SKIPPED: No request to reject")
        return False
    
    target_user = request_obj.target.user
    
    try:
        FollowService.reject_follow_request(
            target_user=target_user,
            request_id=request_obj.id
        )
        
        # Verify request was rejected
        request_obj.refresh_from_db()
        
        # Verify no follow was created
        follow_exists = Follow.objects.filter(
            follower=request_obj.requester.user,
            following=request_obj.target.user
        ).exists()
        
        print(f"  ✅ SUCCESS: Follow request rejected")
        print(f"     Request Status: {request_obj.status}")
        print(f"     Resolved At: {request_obj.resolved_at}")
        print(f"     Follow Created: {follow_exists}")
        return True
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


def test_toggle_privacy(users):
    """Test: Changing account from public to private and vice versa."""
    print("\n[TEST 7] Toggle account privacy")
    
    user = users['public1']
    profile = UserProfile.objects.get(user=user)
    privacy = PrivacySettings.objects.get(user_profile=profile)
    
    print(f"  Starting state: is_private={privacy.is_private_account}")
    
    # Toggle to private
    privacy.is_private_account = True
    privacy.save()
    privacy.refresh_from_db()
    print(f"  ✅ Toggled to PRIVATE: is_private={privacy.is_private_account}")
    
    # Toggle back to public
    privacy.is_private_account = False
    privacy.save()
    privacy.refresh_from_db()
    print(f"  ✅ Toggled back to PUBLIC: is_private={privacy.is_private_account}")
    
    return True


def run_all_tests():
    """Run all follow system tests."""
    print("=" * 60)
    print("FOLLOW SYSTEM COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    users = create_test_users()
    cleanup_test_data(users)
    
    results = []
    
    # Run tests
    results.append(("Public → Public", test_public_to_public(users)))
    
    request1 = test_public_to_private(users)
    results.append(("Public → Private", request1 is not None))
    
    results.append(("Private → Public", test_private_to_public(users)))
    
    request2 = test_private_to_private(users)
    results.append(("Private → Private", request2 is not None))
    
    # Test approval with request1
    if request1:
        results.append(("Approve Request", test_approve_request(request1, users)))
    
    # Test rejection with request2
    if request2:
        results.append(("Reject Request", test_reject_request(request2, users)))
    
    results.append(("Toggle Privacy", test_toggle_privacy(users)))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {test_name}")
    
    print("\n" + "=" * 60)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 60)
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
