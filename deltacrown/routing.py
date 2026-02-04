"""
Routing helpers for Organizations & Competition migration.

Provides redirect views and fallback pages for feature flag-controlled routing.
"""

from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse


@require_http_methods(["GET"])
def legacy_teams_list_redirect(request: HttpRequest) -> HttpResponse:
    """
    Redirect legacy /teams/ list to Organizations directory when ORG_APP_ENABLED=True.
    
    Phase 5: Organizations is now the canonical owner of team management.
    Legacy teams app only serves as fallback when ORG_APP_ENABLED=False.
    """
    if getattr(settings, 'ORG_APP_ENABLED', False):
        # Organizations app is enabled - redirect to org directory
        return redirect('organizations:org_directory')
    
    # ORG_APP_ENABLED=False: Check if legacy teams enabled as fallback
    if getattr(settings, 'LEGACY_TEAMS_ENABLED', False):
        # Allow legacy teams app to handle request
        # This returns None to signal URL dispatcher to continue to next pattern
        return None
    
    # Both flags disabled - show fallback message
    return render(request, 'organizations/fallback.html', {
        'feature_name': 'Teams & Organizations',
        'flag_name': 'ORG_APP_ENABLED or LEGACY_TEAMS_ENABLED',
    })


@require_http_methods(["GET"])
def legacy_teams_redirect(request: HttpRequest, path: str = "") -> HttpResponse:
    """
    Redirect legacy /teams/ URLs to Organizations app when ORG_APP_ENABLED=True.
    
    Routes:
    - /teams/ → /orgs/ (org directory)
    - /teams/<slug>/ → /teams/<slug>/ (handled by organizations app)
    - /teams/create/ → /teams/create/ (handled by organizations app)
    
    If ORG_APP_ENABLED=False, render fallback message.
    """
    if getattr(settings, 'ORG_APP_ENABLED', False):
        # Organizations app is enabled - redirect to org directory
        if not path or path == "":
            return redirect('organizations:org_directory')
        # For specific paths, let organizations app handle them
        return redirect('organizations:' + path)
    
    # Organizations app disabled - show fallback message
    return render(request, 'organizations/fallback.html', {
        'feature_name': 'Organizations',
        'flag_name': 'ORG_APP_ENABLED',
    })


@require_http_methods(["GET"])
def competition_rankings_fallback(request: HttpRequest) -> HttpResponse:
    """
    Fallback page for Competition rankings when COMPETITION_APP_ENABLED=False.
    
    Shows friendly message that feature is not yet available.
    """
    if getattr(settings, 'COMPETITION_APP_ENABLED', False):
        # Should not reach here - Competition app should handle the request
        return redirect('competition:rankings_global')
    
    return render(request, 'competition/fallback.html', {
        'feature_name': 'Competition Rankings',
        'flag_name': 'COMPETITION_APP_ENABLED',
    })
