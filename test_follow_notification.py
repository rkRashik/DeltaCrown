"""
Test Follow Notification System

Run this script to test if follow notifications are working:
python manage.py shell < test_follow_notification.py

Or manually in shell:
python manage.py shell
>>> exec(open('test_follow_notification.py').read())
"""

from django.contrib.auth import get_user_model
from apps.user_profile.services.follow_service import FollowService
from apps.notifications.models import Notification
from apps.user_profile.models_main import Follow

User = get_user_model()

print("\n" + "="*60)
print("FOLLOW NOTIFICATION SYSTEM TEST")
print("="*60 + "\n")

# Get or create test users
try:
    follower = User.objects.get(username='testfollower')
    print(f"✓ Found follower user: {follower.username}")
except User.DoesNotExist:
    print("✗ Test user 'testfollower' not found")
    print("  Create user or use existing username")
    print("\nTo create test users:")
    print("  python manage.py createsuperuser")
    exit(1)

try:
    followee = User.objects.get(username='testfollowee')
    print(f"✓ Found followee user: {followee.username}")
except User.DoesNotExist:
    print("✗ Test user 'testfollowee' not found")
    print("  Create another user for testing")
    exit(1)

print(f"\n{'─'*60}")
print("TEST 1: Check if Follow model works")
print('─'*60)

# Clean up any existing follows
Follow.objects.filter(follower=follower, following=followee).delete()
print("✓ Cleaned up any existing follows")

print(f"\n{'─'*60}")
print("TEST 2: Create follow using FollowService")
print('─'*60)

try:
    follow, created = FollowService.follow_user(
        follower_user=follower,
        followee_username=followee.username
    )
    
    if created:
        print(f"✓ Follow created: {follower.username} → {followee.username}")
        print(f"  Follow ID: {follow.id}")
    else:
        print(f"⚠ Follow already existed: {follower.username} → {followee.username}")
        
except Exception as e:
    print(f"✗ Failed to create follow: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print(f"\n{'─'*60}")
print("TEST 3: Check if notification was created")
print('─'*60)

notifications = Notification.objects.filter(
    recipient=followee,
    type=Notification.Type.USER_FOLLOWED
).order_by('-created_at')

if notifications.exists():
    notif = notifications.first()
    print(f"✓ Notification created!")
    print(f"  ID: {notif.id}")
    print(f"  Type: {notif.type}")
    print(f"  Title: {notif.title}")
    print(f"  Body: {notif.body}")
    print(f"  URL: {notif.url}")
    print(f"  Is Read: {notif.is_read}")
    print(f"  Created: {notif.created_at}")
else:
    print("✗ NO NOTIFICATION FOUND!")
    print("\nDEBUGGING INFORMATION:")
    print(f"  Recipient user ID: {followee.id}")
    print(f"  Looking for type: {Notification.Type.USER_FOLLOWED}")
    
    # Check if ANY notifications exist for this user
    all_notifs = Notification.objects.filter(recipient=followee)
    print(f"  Total notifications for {followee.username}: {all_notifs.count()}")
    
    if all_notifs.exists():
        print("\n  Recent notifications:")
        for n in all_notifs[:3]:
            print(f"    - {n.type}: {n.title}")
    
    # Check available notification types
    print(f"\n  Available notification types:")
    for choice in Notification.Type.choices:
        print(f"    - {choice[0]}: {choice[1]}")

print(f"\n{'─'*60}")
print("TEST 4: Check notification count")
print('─'*60)

unread_count = Notification.objects.filter(
    recipient=followee,
    is_read=False
).count()
print(f"✓ Unread notifications for {followee.username}: {unread_count}")

print(f"\n{'='*60}")
print("TEST COMPLETE")
print('='*60 + "\n")

# Cleanup
print("Cleaning up test data...")
Follow.objects.filter(follower=follower, following=followee).delete()
Notification.objects.filter(
    recipient=followee,
    type=Notification.Type.USER_FOLLOWED,
    body__contains=follower.username
).delete()
print("✓ Cleanup complete\n")
