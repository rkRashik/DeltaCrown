"""
Notification Delivery Enforcement (Phase 5B)

Central enforcement gate that ensures notifications are only delivered
when allowed by user settings.

Rules Enforced:
1. Channel preferences (email/push/SMS enabled/disabled)
2. Category preferences (tournaments/teams/economy/system)
3. Quiet hours (timezone-aware, handles overnight windows)
4. Default behavior (allow if preferences missing)
"""
from datetime import datetime, time
from typing import Optional, Literal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

import logging

logger = logging.getLogger(__name__)

User = get_user_model()

# Channel types
Channel = Literal['email', 'push', 'sms']

# Category types (maps to NotificationPreferences fields)
Category = Literal['tournaments', 'teams', 'bounties', 'messages', 'system', 'economy']

# Category field mapping
CATEGORY_TO_FIELD = {
    'tournaments': 'notif_tournaments',
    'teams': 'notif_teams',
    'bounties': 'notif_bounties',
    'messages': 'notif_messages',
    'system': 'notif_system',
    'economy': 'notif_bounties',  # Economy maps to bounties for now
}


def can_deliver_notification(
    user: User,
    channel: Channel,
    category: Category,
    now: Optional[datetime] = None,
    bypass_user_prefs: bool = False
) -> bool:
    """
    Central enforcement function for notification delivery.
    
    Args:
        user: The recipient user (accounts.User)
        channel: Delivery channel ('email', 'push', 'sms')
        category: Notification category ('tournaments', 'teams', 'bounties', 'messages', 'system', 'economy')
        now: Current datetime (for testing, defaults to timezone.now())
        bypass_user_prefs: If True, skip user preference checks (for critical system notifications)
    
    Returns:
        bool: True if notification can be delivered, False if blocked
    
    Enforcement Rules:
        1. If bypass_user_prefs=True → ALLOW (critical system notifications)
        2. If user has no NotificationPreferences → ALLOW (default behavior)
        3. If channel disabled → BLOCK
        4. If category disabled → BLOCK
        5. If quiet hours enabled and current time in window → BLOCK
    
    Examples:
        >>> can_deliver_notification(user, 'email', 'tournaments')
        True
        
        >>> # During quiet hours (22:00-08:00)
        >>> can_deliver_notification(user, 'email', 'teams', now=datetime(2026, 1, 2, 23, 30))
        False
        
        >>> # Critical system notification bypasses preferences
        >>> can_deliver_notification(user, 'email', 'system', bypass_user_prefs=True)
        True
    """
    # Rule 1: Bypass user preferences for critical notifications
    if bypass_user_prefs:
        logger.debug(f"Notification to {user.username} ({channel}/{category}): ALLOWED (bypass)")
        return True
    
    # Get user's notification preferences
    try:
        prefs = user.profile.notification_prefs
    except (AttributeError, Exception):
        # Rule 2: No preferences found → allow (default behavior)
        logger.debug(f"Notification to {user.username} ({channel}/{category}): ALLOWED (no prefs)")
        return True
    
    # Rule 3: Check if channel is enabled
    channel_field = f'{channel}_enabled'
    if not getattr(prefs, channel_field, True):
        logger.info(f"Notification to {user.username} ({channel}/{category}): BLOCKED (channel disabled)")
        return False
    
    # Rule 4: Check if category is enabled
    category_field = CATEGORY_TO_FIELD.get(category)
    if category_field and not getattr(prefs, category_field, True):
        logger.info(f"Notification to {user.username} ({channel}/{category}): BLOCKED (category disabled)")
        return False
    
    # Rule 5: Check quiet hours
    if not _is_delivery_allowed_during_quiet_hours(prefs, now):
        logger.info(f"Notification to {user.username} ({channel}/{category}): BLOCKED (quiet hours)")
        return False
    
    # All checks passed
    logger.debug(f"Notification to {user.username} ({channel}/{category}): ALLOWED")
    return True


def _is_delivery_allowed_during_quiet_hours(prefs, now: Optional[datetime] = None) -> bool:
    """
    Check if delivery is allowed based on quiet hours settings.
    
    Args:
        prefs: NotificationPreferences instance
        now: Current datetime (defaults to timezone.now())
    
    Returns:
        bool: True if delivery allowed, False if blocked by quiet hours
    
    Quiet Hours Logic:
        - If quiet_hours_enabled=False → ALLOW
        - If quiet_hours_start/end not set → ALLOW
        - Convert current time to user's timezone (from profile.timezone_pref)
        - Check if current time falls within quiet window
        - Handle overnight windows correctly (e.g., 22:00-07:00)
    
    Examples:
        # Quiet hours: 22:00-08:00 in Asia/Dhaka
        # Current time: 23:30 in Asia/Dhaka
        >>> _is_delivery_allowed_during_quiet_hours(prefs, now)
        False  # Blocked (in quiet window)
        
        # Current time: 10:00 in Asia/Dhaka
        >>> _is_delivery_allowed_during_quiet_hours(prefs, now)
        True  # Allowed (outside quiet window)
    """
    # Not enabled → allow
    if not prefs.quiet_hours_enabled:
        return True
    
    # Missing time configuration → allow
    if not prefs.quiet_hours_start or not prefs.quiet_hours_end:
        return True
    
    # Get current time
    if now is None:
        now = timezone.now()
    
    # Get user's timezone from profile (fallback to settings.TIME_ZONE)
    try:
        user_timezone_str = prefs.user_profile.timezone_pref or settings.TIME_ZONE
        user_timezone = ZoneInfo(user_timezone_str)
    except Exception:
        user_timezone = ZoneInfo(settings.TIME_ZONE)
    
    # Convert to user's timezone
    user_now = now.astimezone(user_timezone)
    current_time = user_now.time()
    
    quiet_start = prefs.quiet_hours_start
    quiet_end = prefs.quiet_hours_end
    
    # Check if we have an overnight window (e.g., 22:00-07:00)
    is_overnight = quiet_start > quiet_end
    
    if is_overnight:
        # Overnight window: block if time >= start OR time < end
        in_quiet_hours = current_time >= quiet_start or current_time < quiet_end
    else:
        # Normal window: block if start <= time < end
        in_quiet_hours = quiet_start <= current_time < quiet_end
    
    # Return True if NOT in quiet hours (allowed), False if in quiet hours (blocked)
    return not in_quiet_hours


def get_blocked_reason(
    user: User,
    channel: Channel,
    category: Category,
    now: Optional[datetime] = None,
    bypass_user_prefs: bool = False
) -> Optional[str]:
    """
    Get the reason why a notification would be blocked (for logging/debugging).
    
    Args:
        user: The recipient user
        channel: Delivery channel
        category: Notification category
        now: Current datetime (for testing)
        bypass_user_prefs: If True, skip user preference checks
    
    Returns:
        str: Reason why notification is blocked, or None if allowed
    
    Examples:
        >>> get_blocked_reason(user, 'email', 'teams')
        None  # Allowed
        
        >>> get_blocked_reason(user, 'sms', 'tournaments')
        'channel_disabled'
        
        >>> get_blocked_reason(user, 'email', 'bounties')
        'category_disabled'
        
        >>> get_blocked_reason(user, 'push', 'system', now=datetime(2026, 1, 2, 23, 30))
        'quiet_hours'
    """
    if bypass_user_prefs:
        return None
    
    try:
        prefs = user.profile.notification_prefs
    except (AttributeError, Exception):
        return None
    
    # Check channel
    channel_field = f'{channel}_enabled'
    if not getattr(prefs, channel_field, True):
        return 'channel_disabled'
    
    # Check category
    category_field = CATEGORY_TO_FIELD.get(category)
    if category_field and not getattr(prefs, category_field, True):
        return 'category_disabled'
    
    # Check quiet hours
    if not _is_delivery_allowed_during_quiet_hours(prefs, now):
        return 'quiet_hours'
    
    return None


def log_suppressed_notification(
    user: User,
    channel: Channel,
    category: Category,
    reason: str,
    notification_title: str = ""
) -> None:
    """
    Log a suppressed notification for debugging.
    
    Args:
        user: The recipient user
        channel: Delivery channel
        category: Notification category
        reason: Why it was blocked
        notification_title: Optional title of the notification
    """
    logger.info(
        f"SUPPRESSED NOTIFICATION: user={user.username} ({user.id}), "
        f"channel={channel}, category={category}, reason={reason}, "
        f"title='{notification_title}'"
    )
