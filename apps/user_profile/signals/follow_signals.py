"""
Follow Signal Handlers

Automatically triggers notifications when follow-related events occur.
This provides an additional layer on top of direct service calls.

Architecture:
- post_save on Follow → notify_user_followed (DISABLED - handled in service)
- Signal kept for future enhancements
- Primary notification happens in FollowService.follow_user()
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

# Import Follow model
from apps.user_profile.models_main import Follow, FollowRequest


# DISABLED: Notification is already handled in FollowService.follow_user()
# This causes duplicate notifications if enabled
# @receiver(post_save, sender=Follow)
def notify_on_follow_created_DISABLED(sender, instance, created, **kwargs):
    """
    Send notification when user is followed (public account).
    
    Triggers: When Follow object is created
    Notification: Sent to followee (person being followed)
    
    Args:
        sender: Follow model class
        instance: Follow instance
        created: bool - True if new Follow created
        **kwargs: Additional signal kwargs
        
    Note:
        This is a fallback/redundant layer. Primary notification creation
        happens in FollowService.follow_user() for better control and error handling.
    """
    if not created:
        # Only notify on new follows, not updates
        return
    
    try:
        from apps.notifications.services import NotificationService
        
        # Send notification to the person being followed
        NotificationService.notify_user_followed(
            follower_user=instance.follower,
            followee_user=instance.following
        )
        
        logger.info(
            f"[Signal] Follow notification triggered: {instance.follower.username} → "
            f"{instance.following.username}"
        )
        
    except Exception as e:
        # Log error but don't fail the follow creation
        logger.error(
            f"[Signal] Failed to send follow notification: "
            f"{instance.follower.username} → {instance.following.username}, "
            f"error: {e}",
            exc_info=True
        )


@receiver(post_save, sender='user_profile.FollowRequest')
def notify_on_follow_request_status_change(sender, instance, created, **kwargs):
    """
    Handle notification when FollowRequest status changes.
    
    Note: Actual notifications are handled in FollowService methods:
    - _create_follow_request() → FOLLOW_REQUEST notification
    - approve_follow_request() → FOLLOW_REQUEST_APPROVED notification
    - reject_follow_request() → FOLLOW_REQUEST_REJECTED notification
    
    This signal is a placeholder for potential future enhancements.
    """
    pass  # Notifications handled in service layer for better control
