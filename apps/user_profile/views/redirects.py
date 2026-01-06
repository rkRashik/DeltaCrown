"""
Redirect views for UP-CLEANUP-02 Phase B
301 redirects from legacy URLs to canonical modern endpoints
"""
from django.http import HttpResponsePermanentRedirect
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


def redirect_to_modern_profile(request, username):
    """
    301 redirect from legacy profile URLs to canonical @username format.
    
    Redirects:
    - /u/<username>/ → /@<username>/
    - /<username>/ → /@<username>/
    
    Phase 9A-10: Fixed redirect loop by constructing URL directly.
    Preserves query parameters and logs redirect for monitoring.
    """
    # Phase 9A-10: Use direct URL construction to avoid circular reference
    # (reverse would point back to the redirect route itself)
    from django.contrib.auth import get_user_model
    from django.http import Http404
    
    User = get_user_model()
    
    # Verify user exists (Phase 9A-10: return 404 if not found)
    if not User.objects.filter(username=username).exists():
        raise Http404(f"User '{username}' not found")
    
    # Construct canonical profile URL: /@username/
    target_url = f"/@{username}/"
    
    # Preserve query parameters
    if request.GET:
        query_string = request.GET.urlencode()
        target_url = f"{target_url}?{query_string}"
    
    # Log for monitoring
    user_id = request.user.id if request.user.is_authenticated else None
    logger.info(
        f"LEGACY_PROFILE_REDIRECT: {request.path} → {target_url} "
        f"(user_id={user_id})"
    )
    
    return HttpResponsePermanentRedirect(target_url)


def redirect_get_game_id(request):
    """
    301 redirect from legacy API endpoint to modern game IDs API.
    
    Redirects:
    - /api/profile/get-game-id/ → /api/profile/game-ids/
    
    Read-only API, safe for 301 redirect.
    """
    target_url = reverse('user_profile:get_all_game_ids_api')
    
    # Preserve query parameters
    if request.GET:
        query_string = request.GET.urlencode()
        target_url = f"{target_url}?{query_string}"
    
    # Log for monitoring
    user_id = request.user.id if request.user.is_authenticated else None
    logger.info(
        f"LEGACY_API_REDIRECT: {request.path} → {target_url} "
        f"(user_id={user_id})"
    )
    
    return HttpResponsePermanentRedirect(target_url)
