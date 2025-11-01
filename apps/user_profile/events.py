"""
User Profile Event Handlers

Handles user profile creation when user accounts are created.
"""
import logging
from django.apps import apps
from django.contrib.auth import get_user_model

from apps.core.events import event_bus

logger = logging.getLogger(__name__)

User = get_user_model()


def ensure_user_profile(event):
    """
    Ensure UserProfile exists when User is created or updated.
    
    Replaces: ensure_profile signal
    Triggered by: UserCreatedEvent, UserUpdatedEvent
    """
    try:
        user_id = event.data.get('user_id')
        UserProfile = apps.get_model("user_profile", "UserProfile")
        
        user = User.objects.get(id=user_id)
        defaults = {"display_name": user.username or user.email}
        
        UserProfile.objects.get_or_create(user=user, defaults=defaults)
        
        logger.info(f"✅ Ensured profile for user: {user.username}")
    
    except Exception as e:
        logger.error(f"❌ Failed to ensure user profile: {e}", exc_info=True)


def register_user_profile_event_handlers():
    """Register user profile event handlers"""
    
    event_bus.subscribe(
        'user.created',
        ensure_user_profile,
        name='ensure_user_profile',
        priority=10  # Run early
    )
    
    event_bus.subscribe(
        'user.updated',
        ensure_user_profile,
        name='ensure_user_profile_on_update',
        priority=10
    )
    
    logger.info("📢 Registered user profile event handlers")


__all__ = ['ensure_user_profile', 'register_user_profile_event_handlers']
