"""
Organizer — Schedule Management Actions (P3-T04).

Provides:
- Auto-schedule round: assign time slots to all matches in a round
- Bulk shift: shift all matches by ±N minutes
- Add break: insert a break/delay into the schedule
"""
import json
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.tournaments.models import Tournament, Match
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker


@login_required
@require_POST
def auto_schedule_round(request, slug):
    """
    Auto-schedule all matches in a specific round.

    POST body (JSON):
        round_number (int): Which round to schedule
        start_time (str): ISO-8601 datetime for first match
        slot_duration (int): Minutes per match slot (default 30)
        gap_minutes (int): Gap between consecutive slots (default 5)
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    if not checker.has_any(['manage_matches', 'view_all']):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    round_number = data.get('round_number')
    start_time_str = data.get('start_time')
    slot_duration = int(data.get('slot_duration', 30))
    gap_minutes = int(data.get('gap_minutes', 5))

    if not round_number or not start_time_str:
        return JsonResponse({'success': False, 'error': 'round_number and start_time required'}, status=400)

    from django.utils.dateparse import parse_datetime
    start_time = parse_datetime(start_time_str)
    if not start_time:
        return JsonResponse({'success': False, 'error': 'Invalid start_time format'}, status=400)

    # Make timezone-aware if naive
    if timezone.is_naive(start_time):
        start_time = timezone.make_aware(start_time)

    matches = Match.objects.filter(
        tournament=tournament,
        round_number=round_number,
        is_deleted=False,
    ).order_by('match_number')

    if not matches.exists():
        return JsonResponse({'success': False, 'error': f'No matches found for round {round_number}'}, status=404)

    scheduled = []
    current_time = start_time
    for m in matches:
        m.scheduled_time = current_time
        m.save(update_fields=['scheduled_time', 'updated_at'])
        scheduled.append({
            'match_id': m.id,
            'match_number': m.match_number,
            'scheduled_time': current_time.isoformat(),
        })
        current_time += timedelta(minutes=slot_duration + gap_minutes)

    return JsonResponse({
        'success': True,
        'scheduled_count': len(scheduled),
        'matches': scheduled,
    })


@login_required
@require_POST
def bulk_shift_matches(request, slug):
    """
    Shift all non-completed matches by ±N minutes.

    POST body (JSON):
        delta_minutes (int): Minutes to shift (positive = later, negative = earlier)
        round_number (int, optional): Restrict shift to a specific round
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    if not checker.has_any(['manage_matches', 'view_all']):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    delta_minutes = data.get('delta_minutes')
    round_number = data.get('round_number')

    if delta_minutes is None:
        return JsonResponse({'success': False, 'error': 'delta_minutes required'}, status=400)

    delta = timedelta(minutes=int(delta_minutes))

    qs = Match.objects.filter(
        tournament=tournament,
        is_deleted=False,
        scheduled_time__isnull=False,
    ).exclude(state__in=['completed', 'cancelled', 'forfeit'])

    if round_number:
        qs = qs.filter(round_number=int(round_number))

    shifted = 0
    for m in qs:
        m.scheduled_time = m.scheduled_time + delta
        m.save(update_fields=['scheduled_time', 'updated_at'])
        shifted += 1

    return JsonResponse({
        'success': True,
        'shifted_count': shifted,
        'delta_minutes': int(delta_minutes),
    })


@login_required
@require_POST
def add_schedule_break(request, slug):
    """
    Insert a break after a specific round by shifting subsequent rounds forward.

    POST body (JSON):
        after_round (int): Insert break after this round
        break_minutes (int): Duration of the break (default 15)
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    if not checker.has_any(['manage_matches', 'view_all']):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    after_round = data.get('after_round')
    break_minutes = int(data.get('break_minutes', 15))

    if not after_round:
        return JsonResponse({'success': False, 'error': 'after_round required'}, status=400)

    delta = timedelta(minutes=break_minutes)

    qs = Match.objects.filter(
        tournament=tournament,
        is_deleted=False,
        scheduled_time__isnull=False,
        round_number__gt=int(after_round),
    ).exclude(state__in=['completed', 'cancelled', 'forfeit'])

    shifted = 0
    for m in qs:
        m.scheduled_time = m.scheduled_time + delta
        m.save(update_fields=['scheduled_time', 'updated_at'])
        shifted += 1

    return JsonResponse({
        'success': True,
        'shifted_count': shifted,
        'break_after_round': int(after_round),
        'break_minutes': break_minutes,
    })
