"""Public-safe recruitment summaries for team discovery surfaces."""

from django.db.models import Prefetch

from apps.organizations.models.recruitment import RecruitmentPosition


ACTIVE_RECRUITMENT_POSITIONS_ATTR = "_active_recruitment_positions"


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
