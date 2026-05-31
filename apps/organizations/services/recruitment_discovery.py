"""Public-safe recruitment summaries for team discovery surfaces."""

from collections import defaultdict

from django.db.models import Prefetch
from django.urls import reverse

from apps.organizations.models.recruitment import RecruitmentPosition


ACTIVE_RECRUITMENT_POSITIONS_ATTR = "_active_recruitment_positions"
LFT_CAREER_STATUS_VALUES = ("LOOKING", "FREE_AGENT")


def active_recruitment_positions_prefetch():
    return Prefetch(
        "recruitment_positions",
        queryset=(
            RecruitmentPosition.objects.filter(is_active=True)
            .only(
                "id",
                "team_id",
                "title",
                "role_category",
                "rank_requirement",
                "region",
                "platform",
                "short_pitch",
                "sort_order",
                "created_at",
            )
            .order_by("sort_order", "-created_at")
        ),
        to_attr=ACTIVE_RECRUITMENT_POSITIONS_ATTR,
    )


def build_recruitment_summary(team):
    positions = list(getattr(team, ACTIVE_RECRUITMENT_POSITIONS_ATTR, []) or [])
    position = positions[0] if positions else None
    fallback = team.description or "Looking for skilled players to join the roster."

    if not position:
        return {
            "has_position": False,
            "open_role_count": 0,
            "title": "",
            "role_category": "",
            "rank_requirement": "",
            "region": "",
            "platform": "",
            "short_pitch": fallback,
        }

    role_label = position.get_role_category_display() if position.role_category else ""
    return {
        "has_position": True,
        "open_role_count": len(positions),
        "title": position.title or role_label,
        "role_category": role_label,
        "rank_requirement": position.rank_requirement,
        "region": position.region,
        "platform": position.platform,
        "short_pitch": position.short_pitch or fallback,
    }


def attach_recruitment_summaries(teams):
    for team in teams:
        team.recruitment_summary = build_recruitment_summary(team)
    return teams


def _public_profile_url(username):
    try:
        return reverse("user_profile:public_profile", kwargs={"username": username})
    except Exception:
        return f"/@{username}/"


def _safe_roles(*role_groups, limit=4):
    roles = []
    for group in role_groups:
        if not isinstance(group, list):
            continue
        for role in group:
            label = str(role).strip()
            if label and label not in roles:
                roles.append(label)
            if len(roles) >= limit:
                return roles
    return roles


def _passport_summary(passport):
    game = getattr(passport, "game", None)
    return {
        "game": getattr(game, "display_name", "") or getattr(game, "name", ""),
        "game_slug": getattr(game, "slug", ""),
        "in_game_name": passport.in_game_name or passport.ign or "",
        "rank_name": passport.rank_name or "",
        "rank_tier": passport.rank_tier,
        "peak_rank": passport.peak_rank or "",
        "main_role": passport.main_role or "",
        "platform": passport.platform or "",
        "region": passport.region or "",
        "is_lft": bool(passport.is_lft),
    }


def get_available_player_summaries(limit=8, passports_per_player=2):
    """Return public-safe Looking For Team player summaries for discovery."""
    from apps.user_profile.models import CareerProfile, GameProfile

    career_statuses = tuple(
        value
        for value, _label in CareerProfile._meta.get_field("career_status").choices
        if value in LFT_CAREER_STATUS_VALUES
    )
    careers = list(
        CareerProfile.objects.filter(
            lft_enabled=True,
            recruiter_visibility="PUBLIC",
            career_status__in=career_statuses,
            user_profile__user__is_active=True,
        )
        .select_related("user_profile", "user_profile__user")
        .order_by("-last_updated")[:limit]
    )
    if not careers:
        return []

    user_ids = [career.user_profile.user_id for career in careers]
    passports_by_user = defaultdict(list)
    passports = (
        GameProfile.objects.filter(
            user_id__in=user_ids,
            status=GameProfile.STATUS_ACTIVE,
            visibility=GameProfile.VISIBILITY_PUBLIC,
        )
        .select_related("game")
        .only(
            "id",
            "user_id",
            "game_id",
            "game__name",
            "game__display_name",
            "game__slug",
            "ign",
            "in_game_name",
            "rank_name",
            "rank_tier",
            "peak_rank",
            "main_role",
            "platform",
            "region",
            "is_lft",
            "is_pinned",
            "pinned_order",
            "sort_order",
            "status",
            "visibility",
        )
        .order_by("user_id", "-is_lft", "-is_pinned", "pinned_order", "sort_order", "game__display_name")
    )
    for passport in passports:
        if len(passports_by_user[passport.user_id]) < passports_per_player:
            passports_by_user[passport.user_id].append(_passport_summary(passport))

    players = []
    for career in careers:
        profile = career.user_profile
        user = profile.user
        username = user.username
        player_passports = passports_by_user.get(user.id, [])
        players.append({
            "display_name": profile.display_name or user.get_full_name() or username,
            "username": username,
            "profile_url": _public_profile_url(username),
            "roles": _safe_roles(career.primary_roles, career.secondary_roles),
            "preferred_region": career.preferred_region,
            "region": career.preferred_region,
            "availability": career.get_availability_display() if career.availability else "",
            "passports": player_passports,
            "primary_passport": player_passports[0] if player_passports else None,
        })
    return players
