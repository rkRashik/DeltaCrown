"""
Follow Service (UP-CLEANUP-04 Phase C Part 1 + Phase 6A Private Accounts)

Safe follow/unfollow operations with privacy enforcement and audit trail.
Replacement for legacy follow_user/unfollow_user views.

Architecture:
- Privacy enforcement (respects allow_friend_requests)
- Private account support (Phase 6A): creates FollowRequest for approval
- Safe profile accessors (both follower + followee)
- Audit trail (all follow actions logged)
- Idempotency (safe to call multiple times)
- Rate limiting support (can add decorator)
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from typing import Tuple, Optional, Union
import logging

from apps.user_profile.models_main import Follow, FollowRequest
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
    ) -> Union[Tuple[Follow, bool], Tuple[FollowRequest, bool]]:
        """
        Follow a user with privacy enforcement + audit.
        
        PHASE 6A Enhancement:
        - If target account is PUBLIC → creates Follow immediately (legacy behavior)
        - If target account is PRIVATE → creates FollowRequest (PENDING status)
        
        Args:
            follower_user: User performing the follow
            followee_username: Username of user to follow
            request_id: Request ID for audit correlation
            ip_address: IP address of request
            user_agent: User agent string
            
        Returns:
            Union[Tuple[Follow, bool], Tuple[FollowRequest, bool]]:
                - (Follow, True/False) if public account
                - (FollowRequest, True/False) if private account
            
        Raises:
            User.DoesNotExist: If followee username invalid
            PermissionDenied: If followee disabled friend requests
            ValueError: If trying to follow self
            
        Example:
            >>> # Public account
            >>> follow, created = FollowService.follow_user(
            ...     follower_user=request.user,
            ...     followee_username='alice'
            ... )
            >>> isinstance(follow, Follow)  # True
            
            >>> # Private account
            >>> request_obj, created = FollowService.follow_user(
            ...     follower_user=request.user,
            ...     followee_username='bob_private'
            ... )
            >>> isinstance(request_obj, FollowRequest)  # True
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
        
        # PHASE 6A: Check if target has private account
        if privacy_settings.is_private_account:
            # Private account: create follow request
            return FollowService._create_follow_request(
                follower_user=follower_user,
                followee_user=followee_user,
                follower_profile=follower_profile,
                followee_profile=followee_profile,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # Public account: create follow immediately (legacy behavior)
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
    
    # ===== PHASE 6A: PRIVATE ACCOUNT & FOLLOW REQUEST METHODS =====
    
    @staticmethod
    def _create_follow_request(
        follower_user: User,
        followee_user: User,
        follower_profile,
        followee_profile,
        request_id: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Tuple[FollowRequest, bool]:
        """
        Create a follow request for private account (internal method).
        
        Returns:
            Tuple[FollowRequest, bool]: (request object, created flag)
        """
        # Check if already following (approved request exists)
        if Follow.objects.filter(follower=follower_user, following=followee_user).exists():
            logger.debug(f"Already following: {follower_user.username} → {followee_user.username}")
            # Return existing follow as if it's a request (for consistency)
            # This shouldn't happen in normal flow but handles edge cases
            raise ValueError("Already following this user")
        
        # Check if any follow request already exists (pending, approved, or rejected)
        existing_request = FollowRequest.objects.filter(
            requester=follower_profile,
            target=followee_profile
        ).first()
        
        if existing_request:
            if existing_request.status == FollowRequest.STATUS_PENDING:
                logger.debug(
                    f"Follow request already pending: {follower_user.username} → {followee_user.username}"
                )
                return existing_request, False
            elif existing_request.status == FollowRequest.STATUS_REJECTED:
                # Update rejected request to pending (allow re-requesting)
                existing_request.status = FollowRequest.STATUS_PENDING
                existing_request.save()
                logger.info(
                    f"Reactivated rejected follow request: {follower_user.username} → {followee_user.username}"
                )
                return existing_request, False
            else:
                # Already approved - shouldn't happen but handle gracefully
                logger.warning(
                    f"Follow request already approved: {follower_user.username} → {followee_user.username}"
                )
                return existing_request, False
        
        # Create new follow request
        follow_request = FollowRequest.objects.create(
            requester=follower_profile,
            target=followee_profile,
            status=FollowRequest.STATUS_PENDING
        )
        
        # Record audit event
        AuditService.record_event(
            subject_user_id=followee_user.id,
            actor_user_id=follower_user.id,
            event_type=UserAuditEvent.EventType.FOLLOW_REQUESTED,
            source_app='user_profile',
            object_type='FollowRequest',
            object_id=follow_request.id,
            after_snapshot={
                'requester': follower_user.username,
                'target': followee_user.username,
                'status': 'PENDING',
                'request_id': follow_request.id
            },
            metadata={
                'requester_username': follower_user.username,
                'target_username': followee_user.username,
                'is_private_account': True
            },
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(
            f"Follow request created: {follower_user.username} → {followee_user.username} "
            f"(request_id={follow_request.id})"
        )
        
        # Create notification for target user
        try:
            from apps.notifications.models import Notification
            Notification.objects.create(
                recipient=followee_user,
                type=Notification.Type.FOLLOW_REQUEST,
                title=f"@{follower_user.username} wants to follow you",
                body=f"{follower_profile.display_name or follower_user.username} sent you a follow request.",
                url=f"/@{followee_user.username}/follow-requests/",
                action_label="Review",
                action_url=f"/@{followee_user.username}/follow-requests/",
                category="social",
                message=f"{follower_profile.display_name or follower_user.username} sent you a follow request.",
                action_object_id=follow_request.id,
                action_type="follow_request"
            )
            logger.info(f"Notification created for follow request {follow_request.id}")
        except Exception as e:
            logger.error(f"Failed to create notification for follow request: {e}", exc_info=True)
        
        return follow_request, True
    
    @staticmethod
    @transaction.atomic
    def approve_follow_request(
        target_user: User,
        request_id: int,
        request_id_audit: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Follow:
        """
        Approve a follow request (creates Follow relationship).
        
        Args:
            target_user: User approving the request (must be the target)
            request_id: ID of the FollowRequest to approve
            request_id_audit: Request ID for audit correlation
            ip_address: IP address of request
            user_agent: User agent string
            
        Returns:
            Follow: The created Follow object
            
        Raises:
            FollowRequest.DoesNotExist: If request not found
            PermissionDenied: If user is not the target of the request
            ValueError: If request is not PENDING
            
        Example:
            >>> follow = FollowService.approve_follow_request(
            ...     target_user=request.user,
            ...     request_id=123
            ... )
        """
        follow_request = FollowRequest.objects.select_related(
            'requester__user', 'target__user'
        ).get(id=request_id)
        
        # Verify target_user is the target of the request
        if follow_request.target.user != target_user:
            raise PermissionDenied("You can only approve requests sent to you")
        
        # Verify request is still pending
        if follow_request.status != FollowRequest.STATUS_PENDING:
            raise ValueError(f"Request is not pending (status: {follow_request.status})")
        
        # Create Follow relationship
        follow, created = Follow.objects.get_or_create(
            follower=follow_request.requester.user,
            following=follow_request.target.user
        )
        
        # Update request status
        follow_request.status = FollowRequest.STATUS_APPROVED
        follow_request.resolved_at = timezone.now()
        follow_request.save()
        
        # Record audit event
        AuditService.record_event(
            subject_user_id=target_user.id,
            actor_user_id=target_user.id,
            event_type=UserAuditEvent.EventType.FOLLOW_REQUEST_APPROVED,
            source_app='user_profile',
            object_type='FollowRequest',
            object_id=follow_request.id,
            after_snapshot={
                'requester': follow_request.requester.user.username,
                'target': follow_request.target.user.username,
                'status': 'APPROVED',
                'follow_id': follow.id
            },
            metadata={
                'requester_username': follow_request.requester.user.username,
                'target_username': follow_request.target.user.username,
                'follow_created': created
            },
            request_id=request_id_audit,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(
            f"Follow request approved: {follow_request.requester.user.username} → "
            f"{follow_request.target.user.username} (request_id={follow_request.id}, "
            f"follow_id={follow.id})"
        )
        
        # Create notification for requester
        try:
            from apps.notifications.models import Notification
            target_profile = get_user_profile_safe(target_user)
            Notification.objects.create(
                recipient=follow_request.requester.user,
                type=Notification.Type.FOLLOW_REQUEST_APPROVED,
                title=f"@{target_user.username} accepted your follow request",
                body=f"You are now following {target_profile.display_name or target_user.username}.",
                url=f"/@{target_user.username}/",
                action_label="View Profile",
                action_url=f"/@{target_user.username}/",
                category="social",
                message=f"You are now following {target_profile.display_name or target_user.username}."
            )
            logger.info(f"Notification created for approved follow request {request_id}")
        except Exception as e:
            logger.error(f"Failed to create notification for approved follow request: {e}", exc_info=True)
        
        return follow
    
    @staticmethod
    @transaction.atomic
    def reject_follow_request(
        target_user: User,
        request_id: int,
        request_id_audit: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> FollowRequest:
        """
        Reject a follow request (no Follow created).
        
        Args:
            target_user: User rejecting the request (must be the target)
            request_id: ID of the FollowRequest to reject
            request_id_audit: Request ID for audit correlation
            ip_address: IP address of request
            user_agent: User agent string
            
        Returns:
            FollowRequest: The rejected request object
            
        Raises:
            FollowRequest.DoesNotExist: If request not found
            PermissionDenied: If user is not the target of the request
            ValueError: If request is not PENDING
            
        Example:
            >>> rejected_request = FollowService.reject_follow_request(
            ...     target_user=request.user,
            ...     request_id=123
            ... )
        """
        follow_request = FollowRequest.objects.select_related(
            'requester__user', 'target__user'
        ).get(id=request_id)
        
        # Verify target_user is the target of the request
        if follow_request.target.user != target_user:
            raise PermissionDenied("You can only reject requests sent to you")
        
        # Verify request is still pending
        if follow_request.status != FollowRequest.STATUS_PENDING:
            raise ValueError(f"Request is not pending (status: {follow_request.status})")
        
        # Update request status
        follow_request.status = FollowRequest.STATUS_REJECTED
        follow_request.resolved_at = timezone.now()
        follow_request.save()
        
        # Record audit event
        AuditService.record_event(
            subject_user_id=target_user.id,
            actor_user_id=target_user.id,
            event_type=UserAuditEvent.EventType.FOLLOW_REQUEST_REJECTED,
            source_app='user_profile',
            object_type='FollowRequest',
            object_id=follow_request.id,
            after_snapshot={
                'requester': follow_request.requester.user.username,
                'target': follow_request.target.user.username,
                'status': 'REJECTED'
            },
            metadata={
                'requester_username': follow_request.requester.user.username,
                'target_username': follow_request.target.user.username
            },
            request_id=request_id_audit,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(
            f"Follow request rejected: {follow_request.requester.user.username} → "
            f"{follow_request.target.user.username} (request_id={follow_request.id})"
        )
        
        return follow_request
    
    @staticmethod
    def get_incoming_follow_requests(user: User, status: str = None):
        """
        Get incoming follow requests for a user.
        
        Args:
            user: User whose incoming requests to fetch
            status: Optional status filter ('PENDING', 'APPROVED', 'REJECTED')
            
        Returns:
            QuerySet of FollowRequest objects
        """
        profile = get_user_profile_safe(user)
        qs = FollowRequest.objects.filter(target=profile).select_related(
            'requester__user'
        ).order_by('-created_at')
        
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    @staticmethod
    def get_outgoing_follow_requests(user: User, status: str = None):
        """
        Get outgoing follow requests for a user.
        
        Args:
            user: User whose outgoing requests to fetch
            status: Optional status filter ('PENDING', 'APPROVED', 'REJECTED')
            
        Returns:
            QuerySet of FollowRequest objects
        """
        profile = get_user_profile_safe(user)
        qs = FollowRequest.objects.filter(requester=profile).select_related(
            'target__user'
        ).order_by('-created_at')
        
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    @staticmethod
    def has_pending_follow_request(requester_user: User, target_user: User) -> bool:
        """
        Check if a pending follow request exists.
        
        Args:
            requester_user: User who sent the request
            target_user: User who received the request
            
        Returns:
            bool: True if pending request exists
        """
        requester_profile = get_user_profile_safe(requester_user)
        target_profile = get_user_profile_safe(target_user)
        
        return FollowRequest.objects.filter(
            requester=requester_profile,
            target=target_profile,
            status=FollowRequest.STATUS_PENDING
        ).exists()
    
    @staticmethod
    def can_view_private_profile(viewer: Optional[User], owner: User) -> bool:
        """
        Check if viewer can see private profile content.
        
        Rules:
        - Owner can always see their own profile
        - Staff can always see everything
        - If account is not private: everyone can see
        - If account is private: only approved followers can see full content
        
        Args:
            viewer: User viewing the profile (None for anonymous)
            owner: User who owns the profile
            
        Returns:
            bool: True if viewer can see private content
            
        Example:
            >>> can_view = FollowService.can_view_private_profile(
            ...     viewer=request.user,
            ...     owner=profile_owner
            ... )
        """
        # Get owner's privacy settings first
        owner_profile = get_user_profile_safe(owner)
        privacy_settings = PrivacySettings.objects.filter(user_profile=owner_profile).first()
        
        # If not a private account, everyone can see
        if not privacy_settings or not privacy_settings.is_private_account:
            return True
        
        # Account is private - check special permissions
        
        # Anonymous users cannot see private profiles
        if viewer is None or not viewer.is_authenticated:
            return False
        
        # Owner can always see their own profile
        if viewer == owner:
            return True
        
        # Staff can always see everything
        if viewer.is_staff:
            return True
        
        # Private account: check if viewer is an approved follower
        return Follow.objects.filter(
            follower=viewer,
            following=owner
        ).exists()
