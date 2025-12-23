"""
Decorators for guaranteed UserProfile provisioning.

UP-M0: Safety Net & Inventory
Use @ensure_profile_exists on views that require user.profile to exist.

See: Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_01_CORE_USER_PROFILE_ARCHITECTURE.md
"""
from functools import wraps
from django.http import HttpResponse
from django.utils.html import escape
import logging

logger = logging.getLogger(__name__)


def ensure_profile_exists(view_func):
    """
    Decorator: Guarantees request.user.profile exists before view executes.
    
    Usage:
        @login_required
        @ensure_profile_exists
        def my_view(request):
            profile = request.user.profile  # Guaranteed to exist
            ...
    
    If profile creation fails (extremely rare), returns HTTP 500 with clear error.
    This is a "fail fast" pattern - if we can't provision profile, request cannot proceed.
    
    Architecture Reference:
        UP-01 Section 1: "Invariant: Every User MUST have exactly one UserProfile"
        This decorator enforces the invariant at the view layer.
    
    Note:
        - Only works for authenticated requests (unauthenticated users are skipped)
        - Logs profile creation events for monitoring
        - Safe to use multiple times (idempotent)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Skip anonymous users
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        
        # Ensure profile exists
        try:
            from apps.user_profile.utils import get_or_create_user_profile
            profile, created = get_or_create_user_profile(request.user)
            
            if created:
                logger.warning(
                    f"@ensure_profile_exists created missing profile for "
                    f"user_id={request.user.pk} username={request.user.username} "
                    f"on {request.path}"
                )
        except Exception as e:
            logger.error(
                f"@ensure_profile_exists FAILED for user_id={request.user.pk} "
                f"username={request.user.username} on {request.path}: {e}",
                exc_info=True
            )
            # Fail fast with clear error
            return HttpResponse(
                f"<h1>500 Internal Server Error</h1>"
                f"<p>Failed to provision user profile. Please contact support.</p>"
                f"<p>Error ID: profile_provision_failure_user_{escape(str(request.user.pk))}</p>",
                status=500,
                content_type="text/html"
            )
        
        # Profile guaranteed to exist, proceed with view
        return view_func(request, *args, **kwargs)
    
    return wrapper
