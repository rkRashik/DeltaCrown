"""
Follow Service (UP-CLEANUP-04 Phase C Part 1)

Safe follow/unfollow operations with privacy enforcement and audit trail.
Replacement for legacy follow_user/unfollow_user views.

Architecture:
- Privacy enforcement (respects allow_friend_requests)
- Safe profile accessors (both follower + followee)
- Audit trail (all follow actions logged)
- Idempotency (safe to call multiple times)
- Rate limiting support (can add decorator)
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from typing import Tuple
import logging

from apps.user_profile.models_main import Follow
from apps.user_profile.models import PrivacySettings
from apps.user_profile.models.audit import UserAuditEvent
from apps.user_profile.services.audit import AuditService
from apps.user_profile.utils import get_user_profile_safe

User = get_user_model()
logger = logging.getLogger(__name__)


class FollowService:
    """
    Service for safe follow/unfollow operations.
    
    Enforces:
    - Privacy policy (cannot follow users who disabled friend requests)
    - Safe profile access (both follower + followee)
    - Audit trail (all actions logged)
    - Idempotency (safe to retry)
    """
    
    @staticmethod
    @transaction.atomic
    def follow_user(
        follower_user: User,
        followee_username: str,
        request_id: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Tuple[Follow, bool]:
        """
        Follow a user with privacy enforcement + audit.
        
        Args:
            follower_user: User performing the follow
            followee_username: Username of user to follow
            request_id: Request ID for audit correlation
            ip_address: IP address of request
            user_agent: User agent string
            
        Returns:
            Tuple[Follow, bool]: (Follow object, created flag)
            
        Raises:
            User.DoesNotExist: If followee username invalid
            PermissionDenied: If followee disabled friend requests
            ValueError: If trying to follow self
            
        Example:
            >>> follow, created = FollowService.follow_user(
            ...     follower_user=request.user,
            ...     followee_username='alice'
            ... )
        """
        # Validate not following self
        if follower_user.username == followee_username:
            raise ValueError("Cannot follow yourself")
        
        # Get both profiles (safe accessors)
        follower_profile = get_user_profile_safe(follower_user)
        followee_user = User.objects.get(username=followee_username)
        followee_profile = get_user_profile_safe(followee_user)
        
        # Privacy enforcement: check allow_friend_requests
        privacy_settings, _ = PrivacySettings.objects.get_or_create(
            user_profile=followee_profile
        )
        
        if not privacy_settings.allow_friend_requests:
            logger.warning(
                f"Follow denied: user_id={followee_user.id} disabled friend requests "
                f"(follower_id={follower_user.id})"
            )
            raise PermissionDenied(f"@{followee_username} is not accepting followers")
        
        # Create follow relationship (idempotent)
        follow, created = Follow.objects.get_or_create(
            follower=follower_user,
            following=followee_user
        )
        
        # Record audit event (only if new follow)
        if created:
            AuditService.record_event(
                subject_user_id=followee_user.id,
                actor_user_id=follower_user.id,
                event_type=UserAuditEvent.EventType.FOLLOW_CREATED,
                source_app='user_profile',
                object_type='Follow',
                object_id=follow.id,
                after_snapshot={
                    'following': followee_username,
                    'follower': follower_user.username,
                    'follow_id': follow.id
                },
                metadata={
                    'follower_username': follower_user.username,
                    'followee_username': followee_username,
                    'follower_count': followee_user.followers.count()
                },
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                f"Follow created: follower_id={follower_user.id} → "
                f"followee_id={followee_user.id} (follow_id={follow.id})"
            )
        else:
            logger.debug(
                f"Follow already exists: follower_id={follower_user.id} → "
                f"followee_id={followee_user.id}"
            )
        
        return follow, created
    
    @staticmethod
    @transaction.atomic
    def unfollow_user(
        follower_user: User,
        followee_username: str,
        request_id: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> bool:
        """
        Unfollow a user with audit trail (idempotent).
        
        Args:
            follower_user: User performing the unfollow
            followee_username: Username of user to unfollow
            request_id: Request ID for audit correlation
            ip_address: IP address of request
            user_agent: User agent string
            
        Returns:
            bool: True if unfollowed, False if was not following
            
        Raises:
            User.DoesNotExist: If followee username invalid
            
        Example:
            >>> unfollowed = FollowService.unfollow_user(
            ...     follower_user=request.user,
            ...     followee_username='alice'
            ... )
        """
        # Get both profiles (safe accessors)
        follower_profile = get_user_profile_safe(follower_user)
        followee_user = User.objects.get(username=followee_username)
        followee_profile = get_user_profile_safe(followee_user)
        
        # Delete follow relationship (idempotent)
        try:
            follow = Follow.objects.get(
                follower=follower_user,
                following=followee_user
            )
            follow_id = follow.id
            
            # Capture before snapshot (follow details)
            before_snapshot = {
                'following': followee_username,
                'follower': follower_user.username,
                'follow_id': follow_id
            }
            
            follow.delete()
            
            # Record audit event
            AuditService.record_event(
                subject_user_id=followee_user.id,
                actor_user_id=follower_user.id,
                event_type=UserAuditEvent.EventType.FOLLOW_DELETED,
                source_app='user_profile',
                object_type='Follow',
                object_id=follow_id,
                before_snapshot=before_snapshot,
                after_snapshot={},  # Empty after deletion
                metadata={
                    'follower_username': follower_user.username,
                    'followee_username': followee_username,
                    'follower_count': followee_user.followers.count()
                },
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                f"Unfollow: follower_id={follower_user.id} unfollowed "
                f"followee_id={followee_user.id} (follow_id={follow_id})"
            )
            
            return True
            
        except Follow.DoesNotExist:
            logger.debug(
                f"Unfollow idempotent: follower_id={follower_user.id} was not "
                f"following followee_id={followee_user.id}"
            )
            return False
    
    @staticmethod
    def get_follower_count(user: User) -> int:
        """Get follower count for user."""
        return user.followers.count()
    
    @staticmethod
    def get_following_count(user: User) -> int:
        """Get following count for user."""
        return user.following.count()
    
    @staticmethod
    def is_following(follower_user: User, followee_user: User) -> bool:
        """Check if follower is following followee."""
        return Follow.objects.filter(
            follower=follower_user,
            following=followee_user
        ).exists()
