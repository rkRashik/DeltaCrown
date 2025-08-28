# apps/teams/services.py
import uuid
from django.core.exceptions import PermissionDenied, ValidationError
from apps.teams.models import Team, TeamMembership, TeamInvite, TEAM_MAX_ROSTER

def can_manage_team(actor_profile, team: Team) -> bool:
    return team.captain_id == actor_profile.id

def invite_member(actor_profile, team: Team, target_profile, message: str = "", ttl_days: int = 7):
    if not can_manage_team(actor_profile, team):
        raise PermissionDenied("Only the captain can invite.")

    if team.memberships.count() >= TEAM_MAX_ROSTER:
        raise ValidationError("Roster is full.")

    invite, created = TeamInvite.objects.get_or_create(
        team=team,
        invited_user=target_profile,
        defaults={
            "invited_by": actor_profile,
            "message": message,
            "token": str(uuid.uuid4()),
        },
    )
    if not created and invite.status == "PENDING":
        # already pending: nothing to do
        return invite
    if not created:
        # previously accepted/declined/expired; refresh with new token
        invite.invited_by = actor_profile
        invite.status = "PENDING"
        invite.token = str(uuid.uuid4())
        invite.save()
    return invite

def accept_invite(invite: TeamInvite, user_profile):
    if invite.invited_user_id != user_profile.id:
        raise PermissionDenied("Not your invite.")
    invite.mark_expired_if_needed()
    if invite.status != "PENDING":
        raise ValidationError("Invite is not pending.")
    # capacity
    team = invite.team
    if team.memberships.count() >= TEAM_MAX_ROSTER:
        raise ValidationError("Roster is full.")
    # create membership
    TeamMembership.objects.get_or_create(team=team, user=user_profile, defaults={"role": "player"})
    invite.status = "ACCEPTED"
    invite.save(update_fields=["status"])
    return True

def decline_invite(invite: TeamInvite, user_profile):
    if invite.invited_user_id != user_profile.id:
        raise PermissionDenied("Not your invite.")
    invite.mark_expired_if_needed()
    if invite.status != "PENDING":
        raise ValidationError("Invite is not pending.")
    invite.status = "DECLINED"
    invite.save(update_fields=["status"])
    return True

def leave_team(user_profile, team: Team):
    # captain cannot leave without transfer
    if team.captain_id == user_profile.id:
        raise ValidationError("Captain must transfer captaincy before leaving.")
    TeamMembership.objects.filter(team=team, user=user_profile).delete()
    return True

def transfer_captain(actor_profile, team: Team, new_captain_profile):
    if not can_manage_team(actor_profile, team):
        raise PermissionDenied("Only the captain can transfer captaincy.")
    if not TeamMembership.objects.filter(team=team, user=new_captain_profile).exists():
        raise ValidationError("New captain must be a team member.")
    team.captain = new_captain_profile
    team.save(update_fields=["captain"])
    return True
