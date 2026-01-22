#!/usr/bin/env python
"""
COMPREHENSIVE FOLLOW NOTIFICATION DIAGNOSTIC
This script will check EVERYTHING to find out why notifications aren't working.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

import logging
from django.contrib.auth import get_user_model
from apps.user_profile.models_main import Follow, UserProfile
from apps.notifications.models import Notification, NotificationPreference

# Import NotificationService - it's in services.py file, not in services/ package
import importlib.util
spec = importlib.util.spec_from_file_location(
    "notification_services",
    os.path.join(os.path.dirname(__file__), 'apps', 'notifications', 'services.py')
)
notification_services_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notification_services_module)
NotificationService = notification_services_module.NotificationService

from apps.user_profile.services.follow_service import FollowService

User = get_user_model()

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_1_check_notification_types():
    """Test 1: Verify notification types exist."""
    print_section("TEST 1: Notification Types")
    
    try:
        user_followed_type = Notification.Type.USER_FOLLOWED
        print(f"✅ USER_FOLLOWED type exists: '{user_followed_type}'")
        return True
    except AttributeError:
        print("❌ USER_FOLLOWED type DOES NOT exist!")
        print("   ACTION: Run migrations!")
        return False

def test_2_check_users():
    """Test 2: Check if test users exist."""
    print_section("TEST 2: User Check")
    
    users = User.objects.all()
    print(f"📊 Total users in database: {users.count()}")
    
    if users.count() >= 2:
        user1 = users[0]
        user2 = users[1]
        print(f"✅ Found test users: {user1.username}, {user2.username}")
        return user1, user2
    else:
        print("❌ Need at least 2 users to test")
        return None, None

def test_3_check_notification_preferences(user):
    """Test 3: Check notification preferences."""
    print_section(f"TEST 3: Notification Preferences for {user.username}")
    
    try:
        prefs = NotificationPreference.objects.get(user=user)
        print(f"✅ Preferences exist")
        print(f"   In-app enabled: {prefs.in_app_enabled}")
        print(f"   Social updates: {prefs.social_updates}")
        
        if not prefs.in_app_enabled:
            print("⚠️  WARNING: In-app notifications DISABLED!")
        if not prefs.social_updates:
            print("⚠️  WARNING: Social notifications DISABLED!")
            
        return prefs
    except NotificationPreference.DoesNotExist:
        print("⚠️  No preferences found (will use defaults)")
        return None

def test_4_check_profile_privacy(user):
    """Test 4: Check profile privacy settings."""
    print_section(f"TEST 4: Profile Privacy for {user.username}")
    
    try:
        profile = user.user_profile
        print(f"✅ Profile exists")
        print(f"   Privacy: {profile.privacy_level}")
        print(f"   Requires approval: {profile.require_follow_approval}")
        
        if profile.require_follow_approval:
            print("ℹ️  This is a PRIVATE account (creates FOLLOW_REQUEST, not USER_FOLLOWED)")
        else:
            print("✅ This is a PUBLIC account (creates USER_FOLLOWED)")
            
        return profile
    except UserProfile.DoesNotExist:
        print("❌ Profile does not exist!")
        return None

def test_5_manual_notification_creation(follower, followee):
    """Test 5: Manually create notification."""
    print_section("TEST 5: Manual Notification Creation")
    
    try:
        notifications = NotificationService.notify_user_followed(
            follower_user=follower,
            followee_user=followee
        )
        
        if notifications:
            notif = notifications[0]
            print(f"✅ Notification created successfully!")
            print(f"   ID: {notif.id}")
            print(f"   Recipient: {notif.recipient.username}")
            print(f"   Type: {notif.type}")
            print(f"   Title: {notif.title}")
            print(f"   Body: {notif.body}")
            print(f"   URL: {notif.url}")
            
            # Delete the test notification
            notif.delete()
            print("\n🗑️  Test notification deleted")
            return True
        else:
            print("❌ Notification creation returned empty list!")
            return False
            
    except Exception as e:
        print(f"❌ Error creating notification: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_6_follow_service_integration(follower, followee):
    """Test 6: Test FollowService with notification."""
    print_section("TEST 6: FollowService Integration")
    
    # Clean up any existing follows
    Follow.objects.filter(follower=follower, following=followee).delete()
    print("🧹 Cleaned up existing follows")
    
    # Count notifications before
    notif_count_before = Notification.objects.filter(
        recipient=followee,
        type=Notification.Type.USER_FOLLOWED
    ).count()
    print(f"📊 USER_FOLLOWED notifications before: {notif_count_before}")
    
    try:
        # Execute follow
        follow, created = FollowService.follow_user(
            follower_user=follower,
            followee_username=followee.username
        )
        
        print(f"✅ Follow operation completed")
        print(f"   Follow ID: {follow.id}")
        print(f"   Created: {created}")
        
        # Count notifications after
        notif_count_after = Notification.objects.filter(
            recipient=followee,
            type=Notification.Type.USER_FOLLOWED
        ).count()
        print(f"📊 USER_FOLLOWED notifications after: {notif_count_after}")
        
        if notif_count_after > notif_count_before:
            print("✅ SUCCESS! Notification was created by FollowService!")
            
            # Show the notification
            latest_notif = Notification.objects.filter(
                recipient=followee,
                type=Notification.Type.USER_FOLLOWED
            ).latest('created_at')
            
            print(f"\n📬 Latest notification:")
            print(f"   ID: {latest_notif.id}")
            print(f"   Title: {latest_notif.title}")
            print(f"   Body: {latest_notif.body}")
            print(f"   Created: {latest_notif.created_at}")
            
            # Clean up
            follow.delete()
            latest_notif.delete()
            print("\n🗑️  Test data cleaned up")
            return True
        else:
            print("❌ FAIL! No notification was created!")
            print("   Check Django logs for errors in FollowService.follow_user()")
            
            # Clean up
            if follow:
                follow.delete()
            return False
            
    except Exception as e:
        print(f"❌ Error in follow service: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_7_check_existing_notifications(user):
    """Test 7: Check existing notifications."""
    print_section(f"TEST 7: Existing Notifications for {user.username}")
    
    all_notifs = Notification.objects.filter(recipient=user).order_by('-created_at')
    print(f"📊 Total notifications: {all_notifs.count()}")
    
    if all_notifs.count() > 0:
        print("\n📋 Latest 5 notifications:")
        for notif in all_notifs[:5]:
            print(f"   [{notif.type}] {notif.title}")
            print(f"      Created: {notif.created_at} | Read: {notif.is_read}")
    
    user_followed_notifs = Notification.objects.filter(
        recipient=user,
        type=Notification.Type.USER_FOLLOWED
    )
    print(f"\n📊 USER_FOLLOWED notifications: {user_followed_notifs.count()}")
    
    if user_followed_notifs.exists():
        print("✅ Found USER_FOLLOWED notifications:")
        for notif in user_followed_notifs[:3]:
            print(f"   {notif.title} (ID: {notif.id})")

# Run all tests
def main():
    print("\n" + "🔬" * 35)
    print("  FOLLOW NOTIFICATION DIAGNOSTIC SUITE")
    print("🔬" * 35)
    
    results = []
    
    # Test 1: Check notification types
    results.append(("Notification Types", test_1_check_notification_types()))
    
    # Test 2: Check users
    user1, user2 = test_2_check_users()
    if not user1 or not user2:
        print("\n❌ ABORT: Need at least 2 users to continue")
        return
    
    # Test 3: Check notification preferences
    test_3_check_notification_preferences(user2)
    
    # Test 4: Check profile privacy
    profile2 = test_4_check_profile_privacy(user2)
    if profile2 and profile2.require_follow_approval:
        print("\n⚠️  WARNING: User2 is PRIVATE - test will create FOLLOW_REQUEST instead")
        print("   Consider making user2 public for this test")
        proceed = input("\nProceed anyway? (y/n): ").strip().lower()
        if proceed != 'y':
            print("❌ Test aborted")
            return
    
    # Test 5: Manual notification creation
    results.append(("Manual Notification", test_5_manual_notification_creation(user1, user2)))
    
    # Test 6: FollowService integration
    results.append(("FollowService Integration", test_6_follow_service_integration(user1, user2)))
    
    # Test 7: Check existing notifications
    test_7_check_existing_notifications(user2)
    
    # Summary
    print_section("DIAGNOSTIC SUMMARY")
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("   The notification system is working correctly.")
        print("\n📋 Next steps:")
        print("   1. Test in browser by following someone")
        print("   2. Check notification bell icon for new notifications")
        print("   3. Verify real-time updates work (SSE/WebSocket)")
    else:
        print("\n⚠️  SOME TESTS FAILED!")
        print("   Review the failed tests above for details.")
        print("\n📋 Common issues:")
        print("   1. Migrations not run: python manage.py migrate")
        print("   2. Server not restarted after code changes")
        print("   3. User has notifications disabled in preferences")
        print("   4. Profile privacy causing different notification type")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
