"""
Small centralized authority helpers for vNext teams.

This module is intentionally non-invasive for Phase 2A. Existing permission
functions stay in place while high-risk tournament authority paths move onto a
single active-membership/org-authority interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models import OrganizationMembership, TeamMembership


@dataclass(frozen=True)
class TeamActor:
    user: Any
    team: Any
    membership: Optional[TeamMembership]
    role: str
    is_tournament_captain: bool
    is_creator: bool
    org_authority: str
    is_superuser: bool

    @property
    def is_team_admin(self) -> bool:
        return (
            self.is_superuser
            or self.is_creator
            or self.role in (MembershipRole.OWNER, MembershipRole.MANAGER)
            or self.org_authority in ("CEO", "MANAGER")
        )

    @property
    def is_competitive_authority(self) -> bool:
        return self.is_team_admin or self.is_tournament_captain


def _is_authenticated(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False))


def _is_active_team(team) -> bool:
    return bool(team and getattr(team, "status", TeamStatus.ACTIVE) == TeamStatus.ACTIVE)


def _get_active_team_membership(user, team):
    if not _is_authenticated(user) or team is None:
        return None
    manager = getattr(team, "vnext_memberships", None)
    if manager is None:
        return None
    return (
        manager.filter(user=user, status=MembershipStatus.ACTIVE)
        .order_by("-joined_at", "-id")
        .first()
    )


def _get_org_authority(user, organization) -> str:
    if not _is_authenticated(user) or organization is None:
        return "NONE"
    if getattr(organization, "ceo_id", None) == getattr(user, "id", None):
        return "CEO"

    filters = {
        "organization": organization,
        "user": user,
        "role__in": ("CEO", "MANAGER"),
    }
    if any(field.name == "status" for field in OrganizationMembership._meta.fields):
        filters["status"] = "ACTIVE"

    membership = (
        OrganizationMembership.objects
        .filter(**filters)
        .order_by("-joined_at", "-id")
        .first()
    )
    if membership and membership.role == "CEO":
        return "CEO"
    if membership and membership.role == "MANAGER":
        return "MANAGER"
    return "NONE"


def get_team_actor(user, team) -> TeamActor:
    membership = _get_active_team_membership(user, team)
    is_creator = bool(
        _is_authenticated(user)
        and team is not None
        and getattr(team, "created_by_id", None) == getattr(user, "id", None)
    )
    # Canonical role comes from active roster membership when present. If a
    # creator has no active membership, expose OWNER authority without inventing
    # a separate CREATOR role string.
    role = membership.role if membership else (MembershipRole.OWNER if is_creator else "NONE")
    return TeamActor(
        user=user,
        team=team,
        membership=membership,
        role=role,
        is_tournament_captain=bool(membership and membership.is_tournament_captain),
        is_creator=is_creator,
        org_authority=_get_org_authority(user, getattr(team, "organization", None)),
        is_superuser=bool(_is_authenticated(user) and getattr(user, "is_superuser", False)),
    )


def can_access_team_hq(user, team) -> bool:
    actor = get_team_actor(user, team)
    return _is_active_team(team) and (
        actor.is_team_admin or actor.membership is not None or actor.is_tournament_captain
    )


def can_view_sensitive_team_data(user, team) -> bool:
    return _is_active_team(team) and get_team_actor(user, team).is_team_admin


def can_manage_team_profile(user, team) -> bool:
    return _is_active_team(team) and get_team_actor(user, team).is_team_admin


def can_manage_team_settings(user, team) -> bool:
    return can_manage_team_profile(user, team)


def can_manage_discord(user, team) -> bool:
    return can_manage_team_profile(user, team)


def can_manage_treasury(user, team) -> bool:
    actor = get_team_actor(user, team)
    return _is_active_team(team) and (
        actor.is_superuser
        or actor.role == MembershipRole.OWNER
        or actor.is_creator
        or actor.org_authority == "CEO"
    )


def can_manage_roster(user, team) -> bool:
    return can_manage_team_profile(user, team)


def can_lock_roster(user, team) -> bool:
    return can_manage_roster(user, team)


def can_disband_team(user, team) -> bool:
    actor = get_team_actor(user, team)
    if not _is_active_team(team):
        return actor.is_superuser
    if getattr(team, "organization_id", None):
        return actor.is_superuser or actor.org_authority == "CEO"
    return actor.is_superuser or actor.is_creator


def can_transfer_ownership(user, team) -> bool:
    actor = get_team_actor(user, team)
    return _is_active_team(team) and (actor.is_superuser or actor.is_creator)


def can_manage_training(user, team) -> bool:
    actor = get_team_actor(user, team)
    return _is_active_team(team) and (
        actor.is_team_admin
        or actor.role == MembershipRole.COACH
        or actor.is_tournament_captain
    )


def can_view_analytics(user, team) -> bool:
    actor = get_team_actor(user, team)
    return _is_active_team(team) and (
        actor.is_team_admin
        or actor.role in (MembershipRole.COACH, MembershipRole.ANALYST)
        or actor.is_tournament_captain
    )


def can_act_as_team_captain(user, team) -> bool:
    return _is_active_team(team) and get_team_actor(user, team).is_competitive_authority


def can_register_team_for_tournament(user, team, tournament=None) -> bool:
    if not can_act_as_team_captain(user, team):
        return False
    if tournament is not None and getattr(tournament, "game_id", None):
        return getattr(team, "game_id", None) == tournament.game_id
    return True


def can_submit_team_result(user, team, match=None) -> bool:
    return can_act_as_team_captain(user, team)


def can_manage_competitive_settings(user, team) -> bool:
    return can_manage_team_profile(user, team)


def can_create_team_in_org(user, organization) -> bool:
    if _is_authenticated(user) and getattr(user, "is_superuser", False):
        return True
    return _get_org_authority(user, organization) in ("CEO", "MANAGER")


def can_archive_org_team(user, team) -> bool:
    actor = get_team_actor(user, team)
    # Archiving org teams is CEO/superuser-only; org managers can manage
    # operations but not archive teams.
    return bool(getattr(team, "organization_id", None)) and (
        actor.is_superuser or actor.org_authority == "CEO"
    )
