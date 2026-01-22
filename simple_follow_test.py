#!/usr/bin/env python
"""Simple follow notification test - no emojis, just results."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.models_main import Follow
from apps.notifications.models import Notification

# Import NotificationService properly
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

print("=" * 60)
print("FOLLOW NOTIFICATION SIMPLE TEST")
print("=" * 60)

# Test 1: Check notification type exists
print("\n[TEST 1] Checking USER_FOLLOWED type...")
try:
    user_followed_type = Notification.Type.USER_FOLLOWED
    print(f"OK - USER_FOLLOWED exists: {user_followed_type}")
except AttributeError:
    print("FAIL - USER_FOLLOWED does not exist! Run migrations!")
    exit(1)

# Test 2: Get test users
print("\n[TEST 2] Getting test users...")
users = User.objects.all()
if users.count() < 2:
    print(f"FAIL - Only {users.count()} users found. Need at least 2.")
    exit(1)

user1 = users[0]
user2 = users[1]
print(f"OK - Found {users.count()} users")
print(f"     Using: {user1.username} (follower) and {user2.username} (followee)")

# Test 3: Check profile privacy
print(f"\n[TEST 3] Checking {user2.username} profile privacy...")
try:
    profile2 = user2.profile
    # Check privacy settings
    from apps.user_profile.models_main import PrivacySettings
    privacy_settings, created = PrivacySettings.objects.get_or_create(
        user_profile=profile2
    )
    if created:
        print("     INFO - Created privacy settings (public by default)")
    
    print(f"     Is private: {privacy_settings.is_private_account}")
    print(f"     Allow follow requests: {privacy_settings.allow_friend_requests}")
    
    if privacy_settings.is_private_account:
        print("     INFO - This is PRIVATE (creates FOLLOW_REQUEST, not USER_FOLLOWED)")
    else:
        print("     OK - This is PUBLIC (creates USER_FOLLOWED)")
except AttributeError:
    print("     ERROR - User has no profile!")
    print("     Skipping privacy check")
    privacy_settings = None


# Test 4: Manual notification test
print("\n[TEST 4] Testing manual notification creation...")
try:
    notifs = NotificationService.notify_user_followed(
        follower_user=user1,
        followee_user=user2
    )
    if notifs:
        notif = notifs[0]
        print(f"OK - Notification created")
        print(f"     ID: {notif.id}")
        print(f"     Title: {notif.title}")
        notif.delete()
        print("     Test notification deleted")
    else:
        print("FAIL - Notification creation returned empty list")
        exit(1)
except Exception as e:
    print(f"FAIL - Error: {e}")
    exit(1)

# Test 5: FollowService integration test
print("\n[TEST 5] Testing FollowService integration...")

# Clean up
Follow.objects.filter(follower=user1, following=user2).delete()
print("     Cleaned up existing follows")

# Count before
notif_count_before = Notification.objects.filter(
    recipient=user2,
    type=Notification.Type.USER_FOLLOWED
).count()
print(f"     USER_FOLLOWED notifications before: {notif_count_before}")

# Execute follow
try:
    follow, created = FollowService.follow_user(
        follower_user=user1,
        followee_username=user2.username
    )
    print(f"     Follow created: {created} (ID: {follow.id})")
    
    # Count after
    notif_count_after = Notification.objects.filter(
        recipient=user2,
        type=Notification.Type.USER_FOLLOWED
    ).count()
    print(f"     USER_FOLLOWED notifications after: {notif_count_after}")
    
    if notif_count_after > notif_count_before:
        print("OK - Notification was created by FollowService!")
        
        latest = Notification.objects.filter(
            recipient=user2,
            type=Notification.Type.USER_FOLLOWED
        ).latest('created_at')
        print(f"     Latest notification: '{latest.title}'")
        
        # Clean up
        follow.delete()
        latest.delete()
        print("     Test data cleaned up")
    else:
        print("FAIL - No notification was created!")
        print("     Check logs for errors in FollowService")
        follow.delete()
        exit(1)
        
except Exception as e:
    print(f"FAIL - Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
print("The notification system is working correctly.")
print("\nNext steps:")
print("1. Test in browser by following someone")
print("2. Check notification bell icon")
print("3. Verify real-time updates work")
print("=" * 60)
