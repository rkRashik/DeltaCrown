#!/usr/bin/env python
"""Test follow notification creation end-to-end."""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.services.follow_service import FollowService
from apps.notifications.models import Notification

User = get_user_model()

print("=" * 60)
print("FOLLOW NOTIFICATION TEST")
print("=" * 60)

# Get users (you'll need to provide real usernames)
print("\n📋 Available users (first 10):")
users = User.objects.all()[:10]
for i, user in enumerate(users, 1):
    print(f"  {i}. {user.username}")

print("\n" + "=" * 60)
follower_username = input("Enter follower username: ").strip()
followee_username = input("Enter followee username: ").strip()
print("=" * 60)

try:
    follower = User.objects.get(username=follower_username)
    followee = User.objects.get(username=followee_username)
    
    print(f"\n✅ Found users:")
    print(f"   Follower: {follower.username} (ID: {follower.id})")
    print(f"   Followee: {followee.username} (ID: {followee.id})")
    
    # Check if already following
    from apps.user_profile.models_main import Follow
    already_following = Follow.objects.filter(
        follower=follower,
        following=followee
    ).exists()
    
    if already_following:
        print(f"\n⚠️  {follower.username} is already following {followee.username}")
        delete = input("Delete existing follow to test again? (y/n): ").strip().lower()
        if delete == 'y':
            Follow.objects.filter(follower=follower, following=followee).delete()
            print("✅ Deleted existing follow")
        else:
            print("❌ Aborting test")
            sys.exit(0)
    
    # Check followee's privacy setting
    followee_profile = followee.user_profile
    print(f"\n📋 Followee profile:")
    print(f"   Privacy: {followee_profile.privacy_level}")
    print(f"   Requires approval: {followee_profile.require_follow_approval}")
    
    if followee_profile.require_follow_approval:
        print("\n⚠️  This is a PRIVATE account - will create FOLLOW_REQUEST, not USER_FOLLOWED")
    else:
        print("\n✅ This is a PUBLIC account - will create USER_FOLLOWED notification")
    
    # Count notifications before
    notif_count_before = Notification.objects.filter(recipient=followee).count()
    print(f"\n📊 Notifications before: {notif_count_before}")
    
    # Perform the follow
    print(f"\n🔄 Executing: FollowService.follow_user()")
    follow_obj, created = FollowService.follow_user(
        follower_user=follower,
        followee_username=followee.username
    )
    
    print(f"✅ Follow operation completed:")
    print(f"   Follow ID: {follow_obj.id if follow_obj else 'None'}")
    print(f"   Created: {created}")
    
    # Count notifications after
    notif_count_after = Notification.objects.filter(recipient=followee).count()
    print(f"\n📊 Notifications after: {notif_count_after}")
    print(f"   New notifications: {notif_count_after - notif_count_before}")
    
    # Check for USER_FOLLOWED notification
    user_followed_notifs = Notification.objects.filter(
        recipient=followee,
        type=Notification.Type.USER_FOLLOWED
    ).order_by('-created_at')
    
    print(f"\n📋 USER_FOLLOWED notifications for {followee.username}:")
    if user_followed_notifs.exists():
        for notif in user_followed_notifs[:3]:
            print(f"   ID: {notif.id}")
            print(f"   Title: {notif.title}")
            print(f"   Body: {notif.body}")
            print(f"   Created: {notif.created_at}")
            print(f"   Read: {notif.is_read}")
            print()
    else:
        print("   ❌ No USER_FOLLOWED notifications found")
    
    # Check for FOLLOW_REQUEST notification
    follow_req_notifs = Notification.objects.filter(
        recipient=followee,
        type=Notification.Type.FOLLOW_REQUEST
    ).order_by('-created_at')
    
    print(f"📋 FOLLOW_REQUEST notifications for {followee.username}:")
    if follow_req_notifs.exists():
        for notif in follow_req_notifs[:3]:
            print(f"   ID: {notif.id}")
            print(f"   Title: {notif.title}")
            print(f"   Body: {notif.body}")
            print(f"   Created: {notif.created_at}")
            print(f"   Read: {notif.is_read}")
            print()
    else:
        print("   ℹ️  No FOLLOW_REQUEST notifications found")
    
    # Final verdict
    print("\n" + "=" * 60)
    if created:
        if notif_count_after > notif_count_before:
            print("✅ SUCCESS! Follow created and notification sent!")
        else:
            print("⚠️  WARNING! Follow created but NO notification sent")
            print("   Check logs for errors in FollowService.follow_user()")
    else:
        print("ℹ️  Follow already existed (not created)")
    print("=" * 60)

except User.DoesNotExist as e:
    print(f"\n❌ Error: User not found - {e}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
