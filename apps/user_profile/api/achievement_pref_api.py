"""
Achievement Preference API — owner controls to hide/feature tournament achievements.
"""
from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(['POST'])
def set_achievement_preference(request):
    """Set is_hidden / is_featured for one achievement (by registration_id)."""
    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST.dict()

    registration_id = body.get('registration_id')
    if not registration_id:
        return JsonResponse({'success': False, 'error': 'registration_id required'}, status=400)

    try:
        registration_id = int(registration_id)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid registration_id'}, status=400)

    # Verify the registration belongs to this user or their active team
    from apps.tournaments.models import Registration
    from apps.organizations.models.membership import TeamMembership
    user = request.user
    profile = user.profile

    team_ids = list(
        TeamMembership.objects.filter(user=user, status='ACTIVE').values_list('team_id', flat=True)
    )
    from django.db.models import Q
    owns_reg = Registration.objects.filter(
        Q(id=registration_id),
        Q(user=user) | Q(team_id__in=team_ids),
    ).exists()

    if not owns_reg:
        return JsonResponse({'success': False, 'error': 'Not your achievement'}, status=403)

    from apps.user_profile.models.achievement_preference import UserAchievementPreference
    pref, _ = UserAchievementPreference.objects.get_or_create(
        user_profile=profile,
        registration_id=registration_id,
    )
    if 'is_hidden' in body:
        pref.is_hidden = bool(body['is_hidden'])
    if 'is_featured' in body:
        pref.is_featured = bool(body['is_featured'])
    if 'game_slug' in body:
        pref.game_slug = str(body['game_slug'])[:50]
    pref.save()

    return JsonResponse({
        'success': True,
        'registration_id': registration_id,
        'is_hidden': pref.is_hidden,
        'is_featured': pref.is_featured,
    })
