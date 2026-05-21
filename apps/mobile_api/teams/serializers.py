"""Mobile-safe serializers for team endpoints."""
from __future__ import annotations

from rest_framework import serializers

from apps.games.models import Game
from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models import Team, TeamMembership
from apps.organizations.models.join_request import TeamJoinRequest
from apps.user_profile.models import UserProfile


MANAGER_ROLES = {MembershipRole.OWNER, MembershipRole.MANAGER}
ACTIVE_JOIN_STATUSES = {
    TeamJoinRequest.Status.PENDING,
    TeamJoinRequest.Status.TRYOUT_SCHEDULED,
    TeamJoinRequest.Status.TRYOUT_COMPLETED,
    TeamJoinRequest.Status.OFFER_SENT,
}


class MobileTeamCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, allow_blank=False)
    tag = serializers.CharField(max_length=5, required=False, allow_blank=True, allow_null=True)
    game = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        game_value = attrs["game"]
        game_filter = {"id": int(game_value)} if str(game_value).isdigit() else {"slug": game_value}
        try:
            attrs["game_obj"] = Game.objects.get(is_active=True, **game_filter)
        except Game.DoesNotExist as exc:
            raise serializers.ValidationError({"game": "Active game not found."}) from exc

        name = attrs["name"].strip()
        if Team.objects.filter(name__iexact=name, status=TeamStatus.ACTIVE).exists():
            raise serializers.ValidationError({"name": "An active team with this name already exists."})

        tag = (attrs.get("tag") or "").strip().upper()
        if tag and Team.objects.filter(game_id=attrs["game_obj"].id, tag__iexact=tag).exists():
            raise serializers.ValidationError({"tag": "This tag is already used for this game."})

        attrs["name"] = name
        attrs["tag"] = tag or None
        attrs["description"] = (attrs.get("description") or "").strip()
        return attrs


def image_url(field) -> str | None:
    try:
        return field.url if field else None
    except Exception:
        return None


def game_summary(game: Game | None, game_id: int | None = None) -> dict | None:
    if game is None and game_id:
        game = Game.objects.filter(id=game_id).first()
    if game is None:
        return None
    return {
        "id": game.id,
        "name": game.display_name or game.name,
        "slug": game.slug,
        "short_code": game.short_code,
        "category": game.category,
    }


def user_relation(team: Team, user) -> str:
    if not user or not user.is_authenticated:
        return "none"
    membership = _membership_for_user(team, user)
    if membership:
        if membership.status == MembershipStatus.INVITED:
            return "invited"
        if membership.status == MembershipStatus.ACTIVE:
            if membership.role == MembershipRole.OWNER or membership.is_tournament_captain:
                return "captain"
            return "member"
    if TeamJoinRequest.objects.filter(team=team, user=user, status__in=ACTIVE_JOIN_STATUSES).exists():
        return "pending"
    return "none"


def team_card(team: Team, user=None, game: Game | None = None) -> dict:
    roster_count = _active_roster_count(team)
    return {
        "id": team.id,
        "slug": team.slug,
        "name": team.name,
        "tag": team.tag,
        "logo_url": image_url(team.logo),
        "game": game_summary(game, team.game_id),
        "roster_count": roster_count,
        "member_count": roster_count,
        "is_recruiting": bool(getattr(team, "is_recruiting", False)),
        "recruitment_status": "open" if getattr(team, "is_recruiting", False) else "closed",
        "user_relation": user_relation(team, user),
    }


def team_detail(team: Team, user=None, game: Game | None = None) -> dict:
    membership = _membership_for_user(team, user)
    can_manage = can_manage_team(team, user, membership)
    return {
        "team": team_card(team, user, game),
        "description": team.description or "",
        "region": team.region,
        "platform": team.platform,
        "visibility": team.visibility,
        "roster_locked": team.roster_locked,
        "members": [member_summary(item) for item in _active_memberships(team)],
        "user_membership": membership_summary(membership) if membership else None,
        "permissions": {
            "can_manage": can_manage,
            "can_accept_requests": can_manage,
            "can_decline_requests": can_manage,
        },
        "pending_join_request": join_request_summary(
            TeamJoinRequest.objects.filter(team=team, user=user, status__in=ACTIVE_JOIN_STATUSES).first()
        ) if user and user.is_authenticated else None,
    }


def member_summary(membership: TeamMembership) -> dict:
    return {
        "membership_id": membership.id,
        "user": public_user_summary(membership.user),
        "role": membership.role,
        "status": membership.status,
        "roster_slot": membership.roster_slot,
        "display_name": membership.display_name or getattr(membership.user, "username", ""),
        "is_tournament_captain": membership.is_tournament_captain,
    }


def membership_summary(membership: TeamMembership) -> dict:
    return {
        "id": membership.id,
        "role": membership.role,
        "status": membership.status,
        "is_captain": membership.role == MembershipRole.OWNER or membership.is_tournament_captain,
        "is_manager": membership.role in MANAGER_ROLES,
        "is_tournament_captain": membership.is_tournament_captain,
    }


def join_request_summary(join_request: TeamJoinRequest | None) -> dict | None:
    if join_request is None:
        return None
    return {
        "id": join_request.id,
        "status": join_request.status,
        "message": join_request.message,
        "created_at": join_request.created_at.isoformat() if join_request.created_at else None,
    }


def public_user_summary(user) -> dict:
    profile = UserProfile.objects.filter(user=user).first()
    return {
        "id": user.id,
        "username": user.username,
        "display_name": (getattr(profile, "display_name", "") or user.username) if profile else user.username,
        "avatar_url": image_url(getattr(profile, "avatar", None)) if profile else None,
    }


def can_manage_team(team: Team, user, membership: TeamMembership | None = None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False) or team.created_by_id == user.id:
        return True
    if team.organization and getattr(team.organization, "ceo_id", None) == user.id:
        return True
    membership = membership or _membership_for_user(team, user)
    return bool(
        membership
        and membership.status == MembershipStatus.ACTIVE
        and (membership.role in MANAGER_ROLES or membership.has_permission("edit_roster"))
    )


def _active_roster_count(team: Team) -> int:
    cached = getattr(team, "_prefetched_objects_cache", {}).get("vnext_memberships")
    if cached is not None:
        return sum(1 for item in cached if item.status == MembershipStatus.ACTIVE)
    return team.vnext_memberships.filter(status=MembershipStatus.ACTIVE).count()


def _active_memberships(team: Team):
    return (
        team.vnext_memberships.filter(status=MembershipStatus.ACTIVE)
        .select_related("user")
        .order_by("role", "joined_at")
    )


def _membership_for_user(team: Team, user) -> TeamMembership | None:
    if not user or not user.is_authenticated:
        return None
    return team.vnext_memberships.filter(user=user).order_by("-joined_at").first()
