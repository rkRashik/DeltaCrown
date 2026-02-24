"""
Organizer — Match Operations (Match Medic) (P3-T03).

Provides endpoints for match lifecycle controls:
- Mark Live / Force Start
- Pause / Resume
- Force Complete
- Add Moderator Note

Wires to existing MatchOpsService — NO new business logic.
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone

from apps.tournaments.models import Tournament, Match
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker
from apps.tournament_ops.services.match_ops_service import MatchOpsService
from apps.tournament_ops.adapters.match_ops_adapter import MatchOpsAdapter
from apps.tournament_ops.adapters.staffing_adapter import StaffingAdapter


def _get_service():
    """Instantiate MatchOpsService with adapters."""
    return MatchOpsService(
        match_ops_adapter=MatchOpsAdapter(),
        staffing_adapter=StaffingAdapter(),
    )


def _action_response(result):
    """Convert MatchOpsActionResultDTO to JsonResponse."""
    if result.success:
        return JsonResponse({
            'success': True,
            'message': result.message,
            'match_id': result.match_id,
            'new_state': result.new_state,
            'warnings': result.warnings or [],
        })
    else:
        return JsonResponse({
            'success': False,
            'error': result.message,
            'match_id': result.match_id,
        }, status=400)


@login_required
@require_POST
def match_mark_live(request, slug, match_id):
    """Mark a match as LIVE."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    service = _get_service()
    try:
        result = service.mark_match_live(
            match_id=match_id,
            tournament_id=tournament.id,
            operator_user_id=request.user.id,
        )
        return _action_response(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def match_pause(request, slug, match_id):
    """Pause a LIVE match."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body) if request.body else {}
    except (json.JSONDecodeError, ValueError):
        data = {}

    reason = data.get('reason', '').strip()

    service = _get_service()
    try:
        result = service.pause_match(
            match_id=match_id,
            tournament_id=tournament.id,
            operator_user_id=request.user.id,
            reason=reason or 'Paused by organizer',
        )
        return _action_response(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def match_resume(request, slug, match_id):
    """Resume a PAUSED match."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    service = _get_service()
    try:
        result = service.resume_match(
            match_id=match_id,
            tournament_id=tournament.id,
            operator_user_id=request.user.id,
        )
        return _action_response(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def match_force_complete(request, slug, match_id):
    """Force-complete a match (requires reason)."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    reason = data.get('reason', '').strip()
    if not reason:
        return JsonResponse({'success': False, 'error': 'Reason is required for force-complete.'}, status=400)

    result_data = {}
    if 'score1' in data and 'score2' in data:
        result_data = {
            'score1': int(data['score1']),
            'score2': int(data['score2']),
        }

    service = _get_service()
    try:
        result = service.force_complete_match(
            match_id=match_id,
            tournament_id=tournament.id,
            operator_user_id=request.user.id,
            reason=reason,
            result_data=result_data,
        )
        return _action_response(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def match_add_note(request, slug, match_id):
    """Add moderator note to a match."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    content = data.get('content', '').strip()
    if not content:
        return JsonResponse({'success': False, 'error': 'Note content required.'}, status=400)

    service = _get_service()
    try:
        result = service.add_moderator_note(
            match_id=match_id,
            tournament_id=tournament.id,
            author_user_id=request.user.id,
            content=content,
        )
        return _action_response(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def match_force_start(request, slug, match_id):
    """Force-start a match (bypasses check-in requirement)."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    # Force start = skip check-in and mark as LIVE
    match = get_object_or_404(Match, id=match_id, tournament=tournament)

    if match.state in ['completed', 'forfeit', 'cancelled']:
        return JsonResponse({
            'success': False,
            'error': f'Cannot force-start a match in state: {match.state}'
        }, status=400)

    # Force check-in both participants if needed
    if not match.participant1_checked_in:
        match.participant1_checked_in = True
    if not match.participant2_checked_in:
        match.participant2_checked_in = True
    match.state = 'live'
    match.started_at = timezone.now()
    match.save(update_fields=[
        'participant1_checked_in', 'participant2_checked_in',
        'state', 'started_at',
    ])

    return JsonResponse({
        'success': True,
        'message': 'Match force-started.',
        'match_id': match.id,
        'new_state': 'live',
    })
