"""
Organizer — Participant Management Actions (FE-T-022).

Extracted from organizer.py during Phase 3 restructure.
Handles registration approvals, rejections, disqualification, and roster export.
"""
import json
import csv

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.tournaments.models import Tournament, Registration
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker
from apps.tournaments.services.registration_service import RegistrationService
from apps.tournaments.services.checkin_service import CheckinService


@login_required
@require_POST
def approve_registration(request, slug, registration_id):
    """Approve a registration."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)
    RegistrationService.approve_registration(registration, request.user)

    messages.success(request, f"Registration for {registration.user.username} approved.")
    return JsonResponse({'success': True})


@login_required
@require_POST
def reject_registration(request, slug, registration_id):
    """Reject a registration."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)
    RegistrationService.reject_registration(registration, request.user)

    messages.success(request, f"Registration for {registration.user.username} rejected.")
    return JsonResponse({'success': True})


@login_required
@require_POST
def toggle_checkin(request, slug, registration_id):
    """Toggle check-in status for a registration (organizer only)."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)
    CheckinService.organizer_toggle_checkin(registration, request.user)

    if registration.checked_in:
        messages.success(request, f"{registration.user.username} checked in successfully.")
    else:
        messages.info(request, f"{registration.user.username} check-in removed.")

    return JsonResponse({'success': True, 'checked_in': registration.checked_in})


@login_required
@require_POST
def bulk_approve_registrations(request, slug):
    """FE-T-022: Bulk approve multiple registrations."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
        registration_ids = data.get('registration_ids', [])

        result = RegistrationService.bulk_approve_registrations(
            registration_ids=registration_ids,
            tournament=tournament,
            approved_by=request.user
        )

        messages.success(request, f"Successfully approved {result['count']} registration(s).")
        return JsonResponse({'success': True, 'count': result['count']})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def bulk_reject_registrations(request, slug):
    """FE-T-022: Bulk reject multiple registrations."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
        registration_ids = data.get('registration_ids', [])
        reason = data.get('reason', '').strip()

        result = RegistrationService.bulk_reject_registrations(
            registration_ids=registration_ids,
            tournament=tournament,
            rejected_by=request.user,
            reason=reason
        )

        messages.warning(request, f"Rejected {result['count']} registration(s).")
        return JsonResponse({'success': True, 'count': result['count']})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def disqualify_participant(request, slug, registration_id):
    """FE-T-022: Disqualify a participant."""
    from django.core.exceptions import ValidationError

    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)

    try:
        data = json.loads(request.body)
        reason = data.get('reason', '').strip()

        if not reason:
            return JsonResponse({'success': False, 'error': 'Disqualification reason required'}, status=400)

        result = RegistrationService.disqualify_registration(
            registration=registration,
            reason=reason,
            disqualified_by=request.user
        )

        participant_name = registration.team.name if registration.team_id else registration.user.username

        messages.warning(
            request,
            f"Participant {participant_name} has been disqualified. "
            f"{result.get('message', '')}"
        )

        if result.get('roster_unlocked'):
            messages.info(request, "Team roster has been unlocked.")

        if result.get('waitlist_promoted'):
            promoted_user = result.get('promoted_registration', {}).get('user', {}).get('username', 'Next participant')
            messages.success(request, f"{promoted_user} has been promoted from waitlist.")

        return JsonResponse({'success': True, 'result': result})

    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def export_roster_csv(request, slug):
    """FE-T-022: Export tournament roster as CSV."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.has_any(['manage_registrations', 'view_all']):
        messages.error(request, "You don't have permission to export roster.")
        return redirect('tournaments:organizer_hub', slug=slug, tab='participants')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{tournament.slug}_roster_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Username', 'Email', 'Team', 'Status',
        'Registered At', 'Checked In', 'Checked In At'
    ])

    registrations = Registration.objects.filter(
        tournament=tournament,
        is_deleted=False
    ).select_related('user', 'user__userprofile').order_by('created_at')

    for reg in registrations:
        writer.writerow([
            reg.id,
            reg.user.username if reg.user else 'N/A',
            reg.user.email if reg.user else 'N/A',
            f'Team {reg.team_id}' if reg.team_id else 'Solo',
            reg.get_status_display(),
            reg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Yes' if reg.checked_in else 'No',
            reg.checked_in_at.strftime('%Y-%m-%d %H:%M:%S') if reg.checked_in_at else 'N/A',
        ])

    return response
