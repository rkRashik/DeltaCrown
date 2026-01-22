"""
Django Management Command: Test Follow System
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.user_profile.models_main import Follow, FollowRequest, UserProfile, PrivacySettings
from apps.user_profile.services.follow_service import FollowService

User = get_user_model()


class Command(BaseCommand):
    help = 'Test follow system with public and private accounts'

    def handle(self, *args, **options):
        self.stdout.write("="*60)
        self.stdout.write("FOLLOW SYSTEM TEST")
        self.stdout.write("="*60)
        
        # Get test users
        users = User.objects.filter(is_superuser=False, is_staff=False)[:2]
        
        if users.count() < 2:
            self.stdout.write(self.style.ERROR("\n[ERROR] Need at least 2 non-staff users"))
            return
        
        user1, user2 = users[0], users[1]
        self.stdout.write(f"\n[*] Using users: {user1.username}, {user2.username}")
        
        # Ensure profiles exist
        profile1, _ = UserProfile.objects.get_or_create(user=user1)
        profile2, _ = UserProfile.objects.get_or_create(user=user2)
        privacy2, _ = PrivacySettings.objects.get_or_create(user_profile=profile2)
        
        # Cleanup
        self.stdout.write("\n[*] Cleaning up...")
        Follow.objects.filter(follower=user1, following=user2).delete()
        FollowRequest.objects.filter(requester=profile1, target=profile2).delete()
        
        # TEST 1: Follow public account
        self.stdout.write(f"\n[TEST 1] {user1.username} -> {user2.username} (PUBLIC)")
        privacy2.is_private_account = False
        privacy2.save()
        
        try:
            obj, created = FollowService.follow_user(
                follower_user=user1,
                followee_username=user2.username
            )
            
            if isinstance(obj, Follow):
                self.stdout.write(self.style.SUCCESS(f"  [PASS] Follow created (ID: {obj.id})"))
            else:
                self.stdout.write(self.style.ERROR(f"  [FAIL] Got {type(obj).__name__} instead of Follow"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [ERROR] {e}"))
        
        # Cleanup
        Follow.objects.filter(follower=user1, following=user2).delete()
        
        # TEST 2: Follow private account
        self.stdout.write(f"\n[TEST 2] {user1.username} -> {user2.username} (PRIVATE)")
        privacy2.is_private_account = True
        privacy2.save()
        
        try:
            obj, created = FollowService.follow_user(
                follower_user=user1,
                followee_username=user2.username
            )
            
            if isinstance(obj, FollowRequest):
                self.stdout.write(self.style.SUCCESS(f"  [PASS] FollowRequest created (ID: {obj.id}, Status: {obj.status})"))
                
                # TEST 3: Approve request
                self.stdout.write(f"\n[TEST 3] Approve follow request")
                try:
                    follow = FollowService.approve_follow_request(
                        target_user=user2,
                        request_id=obj.id
                    )
                    self.stdout.write(self.style.SUCCESS(f"  [PASS] Follow created (ID: {follow.id})"))
                    
                    # Verify request status updated
                    obj.refresh_from_db()
                    self.stdout.write(f"  [INFO] Request status: {obj.status}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  [ERROR] Approval failed: {e}"))
            else:
                self.stdout.write(self.style.ERROR(f"  [FAIL] Got {type(obj).__name__} instead of FollowRequest"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [ERROR] {e}"))
        
        # Final cleanup
        self.stdout.write("\n[*] Final cleanup...")
        Follow.objects.filter(follower=user1, following=user2).delete()
        FollowRequest.objects.filter(requester=profile1, target=profile2).delete()
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("TEST COMPLETE"))
        self.stdout.write("="*60)
