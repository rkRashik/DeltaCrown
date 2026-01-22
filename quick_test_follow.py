"""
Quick Fix Script for Follow Notifications

This script manually creates a follow and notification to test the system.
Run: python manage.py shell < quick_test_follow.py
"""

from django.contrib.auth import get_user_model
from apps.notifications.models import Notification
from apps.user_profile.models_main import Follow
from apps.user_profile.utils import get_user_profile_safe

User = get_user_model()

print("\n🔧 QUICK FOLLOW NOTIFICATION TEST\n")

# You can change these usernames to your actual test users
FOLLOWER_USERNAME = input("Enter follower username (who follows): ").strip()
FOLLOWEE_USERNAME = input("Enter followee username (being followed): ").strip()

try:
    follower_user = User.objects.get(username=FOLLOWER_USERNAME)
    followee_user = User.objects.get(username=FOLLOWEE_USERNAME)
    print(f"✓ Found users: {follower_user.username} and {followee_user.username}\n")
except User.DoesNotExist as e:
    print(f"✗ User not found: {e}")
    exit(1)

# Check if notification type exists
print("Checking notification types...")
try:
    test_type = Notification.Type.USER_FOLLOWED
    print(f"✓ USER_FOLLOWED type exists: {test_type}\n")
except AttributeError:
    print("✗ USER_FOLLOWED type NOT found in Notification.Type!")
    print("  Available types:")
    for choice in Notification.Type.choices:
        print(f"    - {choice[0]}")
    print("\n⚠️ You need to run migrations!")
    print("  python manage.py makemigrations notifications")
    print("  python manage.py migrate notifications\n")
    exit(1)

# Create follow
print(f"Creating follow: {follower_user.username} → {followee_user.username}")
follow, created = Follow.objects.get_or_create(
    follower=follower_user,
    following=followee_user
)

if created:
    print(f"✓ Follow created (ID: {follow.id})\n")
else:
    print(f"⚠ Follow already exists (ID: {follow.id})\n")

# Manually create notification
print("Creating notification...")
try:
    follower_profile = get_user_profile_safe(follower_user)
    display_name = follower_profile.display_name or follower_user.username
    
    notification = Notification.objects.create(
        recipient=followee_user,
        type=Notification.Type.USER_FOLLOWED,
        event='user_followed',
        title=f"@{follower_user.username} followed you",
        body=f"{display_name} started following you.",
        url=f"/@{follower_user.username}/",
        action_label="View Profile",
        action_url=f"/@{follower_user.username}/",
        category="social",
        message=f"{display_name} started following you."
    )
    
    print(f"✓ Notification created successfully!")
    print(f"  ID: {notification.id}")
    print(f"  Recipient: {notification.recipient.username}")
    print(f"  Type: {notification.type}")
    print(f"  Title: {notification.title}")
    print(f"  URL: {notification.url}\n")
    
    # Check if it's in the database
    check = Notification.objects.get(id=notification.id)
    print(f"✓ Verified notification in database\n")
    
    # Check unread count
    unread = Notification.objects.filter(
        recipient=followee_user,
        is_read=False
    ).count()
    print(f"📬 Unread notifications for {followee_user.username}: {unread}\n")
    
    print("✅ SUCCESS! Notification system is working!")
    print(f"\nNow login as '{followee_user.username}' and check the notification bell 🔔\n")
    
except Exception as e:
    print(f"✗ Failed to create notification: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
