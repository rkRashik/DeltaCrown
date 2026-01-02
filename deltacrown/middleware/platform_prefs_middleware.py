"""
Platform Preferences Middleware (Phase 5A)

GLOBAL WIRING: Activates user preferences on every request.
- Sets timezone per user preference
- Sets language per user preference
- Injects request.user_platform_prefs for use in views/templates

SAFE FOR ANONYMOUS USERS: Falls back to defaults if no profile exists.
"""

import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.utils import timezone, translation
from apps.user_profile.services.platform_prefs_service import get_user_platform_prefs, DEFAULT_PREFS
from django.conf import settings

logger = logging.getLogger(__name__)


class UserPlatformPrefsMiddleware:
    """
    Middleware to activate user platform preferences globally.
    
    On each request:
    1. Load user preferences (or defaults for anonymous)
    2. Activate timezone
    3. Activate language
    4. Set request.user_platform_prefs for access in views/templates
    
    MUST be placed AFTER AuthenticationMiddleware in settings.MIDDLEWARE.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get user profile (if authenticated)
        profile = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
        
        # Load preferences (defaults if anonymous)
        prefs = get_user_platform_prefs(profile)
        
        # Attach to request for use in views/templates
        request.user_platform_prefs = prefs
        
        # Activate timezone
        tz_name = prefs.get('timezone', DEFAULT_PREFS['timezone'])
        try:
            tz = ZoneInfo(tz_name)
            timezone.activate(tz)
        except ZoneInfoNotFoundError:
            logger.warning(f"Invalid timezone '{tz_name}' for user {request.user if request.user.is_authenticated else 'anonymous'}, falling back to settings.TIME_ZONE")
            # Fallback to settings.TIME_ZONE
            try:
                tz = ZoneInfo(settings.TIME_ZONE)
                timezone.activate(tz)
            except (ZoneInfoNotFoundError, AttributeError):
                # Ultimate fallback: deactivate (use UTC)
                timezone.deactivate()
        
        # Activate language
        lang = prefs.get('preferred_language', DEFAULT_PREFS['preferred_language'])
        translation.activate(lang)
        request.LANGUAGE_CODE = lang
        
        response = self.get_response(request)
        
        # Deactivate for next request (thread safety)
        timezone.deactivate()
        translation.deactivate()
        
        return response
