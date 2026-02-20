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
from django.contrib.auth import get_user_model

from apps.tournaments.models import Tournament, Registration, Match
from apps.tournaments.models.security import AuditLog
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker
from apps.tournaments.services.registration_service import RegistrationService
from apps.tournaments.services.checkin_service import CheckinService

User = get_user_model()


def _audit(tournament, user, action, details=""):
    """Create an audit log entry for participant data actions."""
    try:
        AuditLog.objects.create(
            tournament_id=tournament.id,
            user=user,
            action=action,
            metadata={'details': details},
        )
    except Exception:
        pass  # Never let audit logging break the action


@login_required
@require_POST
def add_participant_manually(request, slug):
    """
    P3-T06: Add a participant manually by username or user ID.

    POST body (JSON):
        username (str, optional): Username to add
        user_id (int, optional): User ID to add
        team_id (int, optional): Team ID for team tournaments
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    username = data.get('username', '').strip()
    user_id = data.get('user_id')
    team_id = data.get('team_id')

    # Resolve user
    target_user = None
    if user_id:
        target_user = User.objects.filter(id=user_id).first()
    elif username:
        target_user = User.objects.filter(username__iexact=username).first()

    if not target_user:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)

    # Check duplicate
    existing = Registration.objects.filter(
        tournament=tournament, user=target_user, is_deleted=False
    ).first()
    if existing:
        return JsonResponse({
            'success': False,
            'error': f'{target_user.username} is already registered (status: {existing.status})'
        }, status=409)

    # Create registration
    reg = Registration.objects.create(
        tournament=tournament,
        user=target_user,
        status='confirmed',
        team_id=team_id,
        registration_data={'manual_add': True, 'added_by': request.user.id},
    )

    _audit(tournament, request.user, 'manual_add_participant',
           f'Added {target_user.username} (reg #{reg.id})')

    return JsonResponse({
        'success': True,
        'registration_id': reg.id,
        'username': target_user.username,
    })


@login_required
@require_POST
def disqualify_with_cascade(request, slug, registration_id):
    """
    P3-T06: Disqualify a participant and cascade to bracket matches.

    Cascade logic:
    1. Set registration status to 'disqualified'
    2. Forfeit all future matches where participant is scheduled
    3. Award BYE wins to opponents in those matches
    4. Audit log every action

    POST body (JSON):
        reason (str): Reason for disqualification
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)

    try:
        data = json.loads(request.body)
        reason = data.get('reason', '').strip()
    except json.JSONDecodeError:
        reason = ''

    if not reason:
        return JsonResponse({'success': False, 'error': 'Disqualification reason required'}, status=400)

    participant_name = registration.user.username if registration.user else f'Team {registration.team_id}'
    participant_id = registration.team_id or (registration.user_id if registration.user else None)

    # 1. DQ the registration (use 'cancelled' — valid DB status; mark DQ in data)
    registration.status = 'cancelled'
    if not registration.registration_data:
        registration.registration_data = {}
    registration.registration_data['disqualified'] = True
    registration.registration_data['dq_reason'] = reason
    registration.save(update_fields=['status', 'registration_data', 'updated_at'])
    _audit(tournament, request.user, 'disqualify_participant',
           f'DQ {participant_name}: {reason}')

    # 2. Cascade: forfeit future matches
    forfeited_matches = []
    if participant_id:
        from django.db.models import Q
        future_matches = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).filter(
            Q(participant1_id=participant_id) | Q(participant2_id=participant_id)
        ).exclude(state__in=['completed', 'cancelled', 'forfeit'])

        for m in future_matches:
            if m.participant1_id == participant_id:
                m.winner_id = m.participant2_id
                m.loser_id = m.participant1_id
            else:
                m.winner_id = m.participant1_id
                m.loser_id = m.participant2_id
            m.state = 'forfeit'
            m.completed_at = timezone.now()
            m.save(update_fields=['winner_id', 'loser_id', 'state', 'completed_at', 'updated_at'])
            forfeited_matches.append(m.id)

            _audit(tournament, request.user, 'dq_cascade_forfeit',
                   f'Match R{m.round_number}M{m.match_number} forfeited due to DQ of {participant_name}')

    return JsonResponse({
        'success': True,
        'participant': participant_name,
        'forfeited_matches': forfeited_matches,
        'forfeited_count': len(forfeited_matches),
    })


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


@login_required
@require_POST
def promote_registration(request, slug, registration_id):
    """Promote a registration from the waitlist to PENDING status."""
    from django.core.exceptions import ValidationError

    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        reg = RegistrationService.promote_from_waitlist(
            tournament_id=tournament.id,
            registration_id=registration_id,
            promoted_by=request.user,
        )
        if reg:
            participant_name = reg.team.name if reg.team_id else (reg.user.username if reg.user else 'Unknown')
            messages.success(request, f"{participant_name} has been promoted from the waitlist.")
            return JsonResponse({'success': True, 'promoted': participant_name})
        return JsonResponse({'success': False, 'error': 'No waitlisted registration found.'}, status=404)

    except Registration.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Registration not found on waitlist.'}, status=404)
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def auto_promote_next(request, slug):
    """Auto-promote the next waitlisted participant (FIFO order)."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    reg = RegistrationService.auto_promote_waitlist(tournament_id=tournament.id)
    if reg:
        participant_name = reg.team.name if reg.team_id else (reg.user.username if reg.user else 'Unknown')
        messages.success(request, f"{participant_name} promoted from waitlist (FIFO).")
        return JsonResponse({'success': True, 'promoted': participant_name})
    
    return JsonResponse({'success': False, 'error': 'No eligible waitlisted registrations or tournament still full.'}, status=400)


@login_required
@require_POST
def force_checkin(request, slug, registration_id):
    """Force check-in a participant (organizer override, bypasses window)."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)

    if registration.checked_in:
        return JsonResponse({'success': False, 'error': 'Already checked in.'}, status=400)

    CheckinService.organizer_toggle_checkin(registration, request.user)
    return JsonResponse({'success': True, 'checked_in': True})


@login_required
@require_POST
def drop_noshow(request, slug, registration_id):
    """Drop a participant as no-show (sets status to 'no_show')."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)

    if registration.status == 'no_show':
        return JsonResponse({'success': False, 'error': 'Already marked as no-show.'}, status=400)

    registration.status = 'no_show'
    registration.checked_in = False
    registration.save(update_fields=['status', 'checked_in', 'updated_at'])

    participant_name = registration.team.name if registration.team_id else (
        registration.user.username if registration.user else 'Unknown'
    )
    messages.warning(request, f"{participant_name} dropped as no-show.")
    return JsonResponse({'success': True, 'dropped': participant_name})


@login_required
@require_POST
def close_drop_noshows(request, slug):
    """Close check-in and drop all confirmed participants who haven't checked in."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    no_shows = Registration.objects.filter(
        tournament=tournament,
        is_deleted=False,
        status='confirmed',
        checked_in=False,
    )
    count = no_shows.count()
    no_shows.update(status='no_show')

    messages.warning(request, f"Check-in closed. {count} no-show(s) dropped.")
    return JsonResponse({'success': True, 'dropped_count': count})
