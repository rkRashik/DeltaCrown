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
    
    Preserves query parameters and logs redirect for monitoring.
    """
    target_url = reverse('user_profile:profile', kwargs={'username': username})
    
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
