"""Authority helpers for tournament match participant actions."""

from django.core.exceptions import ObjectDoesNotExist

from apps.organizations.models import Team
from apps.organizations.services.team_authority import can_submit_team_result
from apps.tournaments.models import Registration


def _is_team_tournament(match) -> bool:
    return getattr(getattr(match, "tournament", None), "participation_type", None) == "team"


def _user_can_act_for_participant_id(user, match, participant_id) -> bool:
    if not participant_id:
        return False

    if not _is_team_tournament(match) and participant_id == getattr(user, "id", None):
        return True

    try:
        team = Team.objects.get(pk=participant_id)
    except ObjectDoesNotExist:
        team = None
    if team and can_submit_team_result(user, team, match=match):
        return True

    try:
        registration = Registration.objects.get(pk=participant_id, team_id__isnull=False)
    except ObjectDoesNotExist:
        registration = None
    if registration and registration.team_id:
        try:
            team = Team.objects.get(pk=registration.team_id)
        except ObjectDoesNotExist:
            team = None
        if team and can_submit_team_result(user, team, match=match):
            return True

    return False


def resolve_participant_side(user, match) -> int | None:
    if not user or not getattr(user, "is_authenticated", False):
        return None

    if _user_can_act_for_participant_id(user, match, getattr(match, "participant1_id", None)):
        return 1
    if _user_can_act_for_participant_id(user, match, getattr(match, "participant2_id", None)):
        return 2
    return None


def user_can_act_for_match(user, match) -> bool:
    return resolve_participant_side(user, match) is not None
