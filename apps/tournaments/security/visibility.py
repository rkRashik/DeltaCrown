"""Read-only visibility guards shared by public pages and realtime delivery."""
from django.db.models import Q

from apps.tournaments.models import Tournament, Registration, Match
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker


def can_view_tournament(user, tournament):
    if tournament.status not in {Tournament.DRAFT, Tournament.PENDING_APPROVAL}:
        return True
    return bool(user and user.is_authenticated and StaffPermissionChecker(tournament, user).can_access_organizer_hub())


def can_join_tournament_room(user, tournament_id):
    tournament = Tournament.objects.filter(pk=tournament_id, is_deleted=False).first()
    return bool(tournament and can_view_tournament(user, tournament))


def can_receive_private_event(user, tournament_id, payload):
    """Financial/registration/dispute details are not public spectator events."""
    tournament = Tournament.objects.filter(pk=tournament_id, is_deleted=False).first()
    if not tournament or not user or not user.is_authenticated:
        return False
    if payload.get('tournament_id') not in {None, tournament_id}:
        return False
    checker = StaffPermissionChecker(tournament, user)
    if checker.has_any(['view_all', 'view_registrations', 'manage_registrations', 'approve_payments', 'resolve_disputes']):
        return True
    from apps.organizations.models import TeamMembership
    team_ids = TeamMembership.objects.filter(user=user, status='ACTIVE').values_list('team_id', flat=True)
    registrations = Registration.objects.filter(tournament_id=tournament_id, is_deleted=False).filter(Q(user=user) | Q(team_id__in=team_ids))
    if payload.get('registration_id'):
        return registrations.filter(pk=payload['registration_id']).exists()
    if payload.get('match_id'):
        match = Match.objects.filter(pk=payload['match_id'], tournament_id=tournament_id, is_deleted=False).first()
        if match:
            ids = [match.participant1_id, match.participant2_id]
            if tournament.participation_type == 'solo':
                return user.pk in ids and registrations.exists()
            return registrations.filter(team_id__in=ids).exists()
    return False
