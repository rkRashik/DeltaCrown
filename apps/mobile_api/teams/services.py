"""Team helpers for the mobile API."""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.games.models import Game
from apps.organizations.choices import MembershipRole, MembershipStatus, RosterSlot, TeamStatus
from apps.organizations.models import Team, TeamMembership
from apps.organizations.models.join_request import TeamJoinRequest
from apps.user_profile.models import GameProfile, UserProfile

from .serializers import ACTIVE_JOIN_STATUSES, can_manage_team, game_summary, join_request_summary, team_card


def resolve_team(id_or_slug: str) -> Team | None:
    queryset = Team.objects.select_related("organization", "created_by").filter(status=TeamStatus.ACTIVE)
    if str(id_or_slug).isdigit():
        return queryset.filter(id=int(id_or_slug)).first()
    return queryset.filter(slug=id_or_slug).first()


def create_independent_team(*, user, validated_data: dict) -> Team:
    game = validated_data["game_obj"]
    if not GameProfile.objects.filter(user=user, game=game).exists():
        raise MobileTeamValidation("game_passport_required", f"Add a {game.display_name} game passport before creating a team.")

    if TeamMembership.objects.filter(
        user=user,
        game_id=game.id,
        organization_id__isnull=True,
        status=MembershipStatus.ACTIVE,
    ).exists():
        raise MobileTeamValidation("team_exists", "You already belong to an independent team for this game.")

    region = _default_region(user)
    try:
        with transaction.atomic():
            team = Team.objects.create(
                name=validated_data["name"],
                tag=validated_data.get("tag"),
                description=validated_data.get("description", ""),
                game_id=game.id,
                region=region,
                created_by=user,
                status=TeamStatus.ACTIVE,
                visibility="PUBLIC",
                is_recruiting=True,
            )
            TeamMembership.objects.create(
                team=team,
                user=user,
                role=MembershipRole.OWNER,
                roster_slot=RosterSlot.STARTER,
                status=MembershipStatus.ACTIVE,
                is_tournament_captain=True,
            )
    except IntegrityError as exc:
        raise MobileTeamValidation("conflict", "Team could not be created because it conflicts with existing roster rules.") from exc
    return team


def apply_to_team(*, team: Team, user, message: str = "") -> tuple[TeamJoinRequest, bool]:
    if team.created_by_id == user.id or team.vnext_memberships.filter(user=user, status=MembershipStatus.ACTIVE).exists():
        raise MobileTeamValidation("already_member", "You are already a member of this team.")
    if not getattr(team, "is_recruiting", True):
        raise MobileTeamValidation("team_closed", "This team is not currently recruiting.")
    if team.roster_locked:
        raise MobileTeamValidation("roster_locked", "Team roster is currently locked.")

    existing = TeamJoinRequest.objects.filter(team=team, user=user, status__in=ACTIVE_JOIN_STATUSES).first()
    if existing:
        return existing, False

    try:
        join_request = TeamJoinRequest.objects.create(
            team=team,
            user=user,
            message=(message or "").strip()[:500],
        )
    except IntegrityError:
        existing = TeamJoinRequest.objects.filter(team=team, user=user, status__in=ACTIVE_JOIN_STATUSES).first()
        if existing:
            return existing, False
        raise
    return join_request, True


def accept_join_request(*, team: Team, join_request_id: int, actor):
    return _review_join_request(team=team, join_request_id=join_request_id, actor=actor, action="accept")


def decline_join_request(*, team: Team, join_request_id: int, actor):
    return _review_join_request(team=team, join_request_id=join_request_id, actor=actor, action="decline")


def team_status_for_user(user) -> dict:
    memberships = (
        TeamMembership.objects.filter(user=user)
        .select_related("team")
        .order_by("team__game_id", "team__name")
    )
    game_ids = {item.team.game_id for item in memberships if item.team_id}
    games_by_id = {game.id: game for game in Game.objects.filter(id__in=game_ids)}
    active_games = {game.id: game for game in Game.objects.filter(is_active=True).order_by("name")}

    groups = {}
    for membership in memberships:
        team = membership.team
        game = games_by_id.get(team.game_id) or active_games.get(team.game_id)
        key = str(team.game_id)
        groups.setdefault(
            key,
            {
                "game": game_summary(game, team.game_id),
                "can_create_team": _can_create_team_for_game(user, team.game_id),
                "teams": [],
            },
        )
        groups[key]["teams"].append(
            {
                "team": team_card(team, user, game),
                "membership": {
                    "id": membership.id,
                    "role": membership.role,
                    "status": membership.status,
                    "is_captain": membership.role == MembershipRole.OWNER or membership.is_tournament_captain,
                    "is_manager": membership.role in {MembershipRole.OWNER, MembershipRole.MANAGER},
                    "is_tournament_captain": membership.is_tournament_captain,
                },
            }
        )

    for game_id, game in active_games.items():
        key = str(game_id)
        groups.setdefault(
            key,
            {
                "game": game_summary(game),
                "can_create_team": _can_create_team_for_game(user, game_id),
                "teams": [],
            },
        )

    return {"games": list(groups.values())}


def _review_join_request(*, team: Team, join_request_id: int, actor, action: str):
    if not can_manage_team(team, actor):
        raise MobileTeamValidation("permission_denied", "Only a team owner or manager can review join requests.", status_code=403)

    allowed_statuses = [TeamJoinRequest.Status.PENDING]
    if action == "decline":
        allowed_statuses = [
            TeamJoinRequest.Status.PENDING,
            TeamJoinRequest.Status.TRYOUT_SCHEDULED,
            TeamJoinRequest.Status.TRYOUT_COMPLETED,
            TeamJoinRequest.Status.OFFER_SENT,
        ]

    with transaction.atomic():
        join_request = (
            TeamJoinRequest.objects.select_for_update()
            .select_related("user")
            .filter(pk=join_request_id, team=team, status__in=allowed_statuses)
            .first()
        )
        if join_request is None:
            raise MobileTeamValidation("not_found", "Pending join request not found.", status_code=404)

        if action == "decline":
            join_request.status = TeamJoinRequest.Status.DECLINED
            join_request.reviewed_by = actor
            join_request.reviewed_at = timezone.now()
            join_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
            return {"request": join_request_summary(join_request), "membership": None}

        membership = TeamMembership.objects.filter(
            team=team,
            user=join_request.user,
            status=MembershipStatus.ACTIVE,
        ).first()
        if membership is None:
            membership = TeamMembership.objects.create(
                team=team,
                user=join_request.user,
                role=MembershipRole.PLAYER,
                roster_slot=RosterSlot.STARTER,
                status=MembershipStatus.ACTIVE,
            )

        join_request.status = TeamJoinRequest.Status.ACCEPTED
        join_request.reviewed_by = actor
        join_request.reviewed_at = timezone.now()
        join_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        return {
            "request": join_request_summary(join_request),
            "membership": {"id": membership.id, "role": membership.role, "status": membership.status},
        }


def _can_create_team_for_game(user, game_id: int) -> dict:
    if not GameProfile.objects.filter(user=user, game_id=game_id).exists():
        return {"allowed": False, "reason": "game_passport_required"}
    if TeamMembership.objects.filter(
        user=user,
        game_id=game_id,
        organization_id__isnull=True,
        status=MembershipStatus.ACTIVE,
    ).exists():
        return {"allowed": False, "reason": "already_on_independent_team"}
    return {"allowed": True, "reason": None}


def _default_region(user) -> str:
    profile = UserProfile.objects.filter(user=user).first()
    for value in (
        getattr(profile, "country", None) if profile else None,
        getattr(profile, "region", None) if profile else None,
        getattr(profile, "city", None) if profile else None,
    ):
        if value:
            return str(value)[:50]
    return "Global"


class MobileTeamValidation(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)
