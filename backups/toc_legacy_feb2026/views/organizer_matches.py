"""
Organizer — Match Management Actions (FE-T-024).

Extracted from organizer.py during Phase 3 restructure.
Handles match scoring, rescheduling, forfeits, overrides, and cancellations.
"""
import json
from datetime import datetime

from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.tournaments.models import Tournament, Match
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker
from apps.tournaments.services.match_service import MatchService


@login_required
@require_POST
def submit_match_score(request, slug, match_id):
    """Submit or update match score."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    match = get_object_or_404(Match, id=match_id, tournament=tournament)

    data = json.loads(request.body)
    score1 = data.get('score1')
    score2 = data.get('score2')

    try:
        score1 = int(score1)
        score2 = int(score2)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid score values'}, status=400)

    try:
        MatchService.organizer_submit_score(match, score1, score2)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    messages.success(request, f"Match score submitted: {score1}-{score2}")
    return JsonResponse({'success': True, 'score1': score1, 'score2': score2})


@login_required
@require_POST
def reschedule_match(request, slug, match_id):
    """FE-T-024: Reschedule a match to a new time."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    match = get_object_or_404(Match, id=match_id, tournament=tournament)

    try:
        data = json.loads(request.body)
        new_time_str = data.get('scheduled_time', '').strip()
        reason = data.get('reason', '').strip()

        if not new_time_str:
            return JsonResponse({'success': False, 'error': 'New scheduled time required'}, status=400)

        try:
            new_time = datetime.fromisoformat(new_time_str.replace('Z', '+00:00'))
            if timezone.is_naive(new_time):
                new_time = timezone.make_aware(new_time)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid datetime format'}, status=400)

        MatchService.organizer_reschedule_match(
            match,
            new_time,
            reason,
            request.user.username
        )

        messages.success(request, f"Match rescheduled to {new_time.strftime('%b %d, %H:%M')}.")
        return JsonResponse({'success': True, 'new_time': new_time.isoformat()})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def forfeit_match(request, slug, match_id):
    """FE-T-024: Mark a match as forfeit."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    match = get_object_or_404(Match, id=match_id, tournament=tournament)

    try:
        data = json.loads(request.body)
        forfeiting = data.get('forfeiting_participant')
        reason = data.get('reason', '').strip()

        if forfeiting not in [1, 2, '1', '2']:
            return JsonResponse({'success': False, 'error': 'Invalid forfeiting participant'}, status=400)

        forfeiting = int(forfeiting)

        MatchService.organizer_forfeit_match(
            match,
            forfeiting,
            reason,
            request.user.username
        )

        messages.warning(request, "Match marked as forfeit.")
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def override_match_score(request, slug, match_id):
    """FE-T-024: Override match score (for corrections)."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    match = get_object_or_404(Match, id=match_id, tournament=tournament)

    try:
        data = json.loads(request.body)
        score1 = int(data.get('score1'))
        score2 = int(data.get('score2'))
        reason = data.get('reason', '').strip()

        if score1 < 0 or score2 < 0:
            return JsonResponse({'success': False, 'error': 'Scores must be non-negative'}, status=400)

        if score1 == score2:
            return JsonResponse({'success': False, 'error': 'Scores cannot be tied'}, status=400)

        if not reason:
            return JsonResponse({'success': False, 'error': 'Override reason required'}, status=400)

        MatchService.organizer_override_score(
            match,
            score1,
            score2,
            reason,
            request.user.username
        )

        messages.success(request, f"Match score overridden to {score1}-{score2}.")
        return JsonResponse({'success': True, 'score1': score1, 'score2': score2})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def cancel_match(request, slug, match_id):
    """FE-T-024: Cancel a match."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    match = get_object_or_404(Match, id=match_id, tournament=tournament)

    try:
        data = json.loads(request.body)
        reason = data.get('reason', '').strip()

        if not reason:
            return JsonResponse({'success': False, 'error': 'Cancellation reason required'}, status=400)

        MatchService.organizer_cancel_match(
            match,
            reason,
            request.user.username
        )

        messages.warning(request, "Match cancelled.")
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
