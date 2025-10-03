# apps/tournaments/views/state_api.py
"""
Real-time state API for tournament detail pages.
Provides live updates for registration status without page reload.
"""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_page

from ..models import Tournament


@require_GET
@cache_page(30)  # Cache for 30 seconds to reduce DB load
def tournament_state_api(request, slug: str) -> JsonResponse:
    """
    GET /tournaments/api/<slug>/state/
    Returns current tournament state for live updates.
    """
    tournament = get_object_or_404(
        Tournament.objects.select_related('settings'),
        slug=slug
    )
    
    state_machine = tournament.state
    
    # Get user-specific registration state if authenticated
    user_registered = False
    if request.user.is_authenticated:
        try:
            from ..models import Registration
            from apps.user_profile.models import UserProfile
            
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                user_registered = Registration.objects.filter(
                    tournament=tournament,
                    user=user_profile,
                    status__in=['PENDING', 'CONFIRMED']
                ).exists()
        except Exception:
            pass
    
    return JsonResponse({
        'success': True,
        'timestamp': state_machine._now.isoformat(),
        'state': state_machine.to_dict(),
        'user_registered': user_registered,
    })
