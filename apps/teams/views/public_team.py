# apps/teams/views/public_team.py
from __future__ import annotations

from django.apps import apps
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

# This view keeps your /teams/<game>/<slug>/ style route (if you use it),
# and feeds a "team_public.html" template. Context now includes captain/member
# flags and join-guard info to match the new UI expectations.


def team_public_by_slug(request, game: str, slug: str):
    Team = apps.get_model("teams", "Team")
    TeamAchievement = apps.get_model("teams", "TeamAchievement")
    TeamStats = apps.get_model("teams", "TeamStats")
    TeamMembership = apps.get_model("teams", "TeamMembership")
    Match = apps.get_model("tournaments", "Match")
    UserProfile = apps.get_model("user_profile", "UserProfile")

    team = get_object_or_404(Team, game=game, slug=slug)

    # roster (active)
    roster_mems = (
        TeamMembership.objects.filter(team=team, status="ACTIVE")
        .select_related("profile__user")
        .order_by("role", "joined_at")
    )
    roster = [m.profile for m in roster_mems]

    # latest stats (optional model)
    stats = TeamStats.objects.filter(team=team).order_by("-updated_at").first()

    # upcoming / recent matches (best effort)
    upcoming = Match.objects.filter(Q(team_a=team) | Q(team_b=team), state="SCHEDULED").order_by("start_at")[:5]
    recent = Match.objects.filter(Q(team_a=team) | Q(team_b=team), state="VERIFIED").order_by("-start_at")[:5]

    # achievements (optional model)
    achievements = TeamAchievement.objects.filter(team=team).order_by("-year", "-id")[:20]

    # role flags & join guard (one-team-per-game)
    def _get_profile(user):
        return getattr(user, "profile", None) or getattr(user, "userprofile", None)

    prof = _get_profile(request.user)
    is_member = False
    is_captain = False
    already_in_team_for_game = False

    if prof:
        is_member = TeamMembership.objects.filter(team=team, profile=prof).exists()
        is_captain = (team.captain_id == getattr(prof, "id", None))
        already_in_team_for_game = TeamMembership.objects.filter(
            profile=prof, team__game=team.game
        ).exists()

    ctx = {
        "team": team,
        "roster": roster,
        "roster_memberships": roster_mems,
        "stats": stats,
        "upcoming": upcoming,
        "recent": recent,
        "achievements": achievements,
        "is_member": is_member,
        "is_captain": is_captain,
        "already_in_team_for_game": already_in_team_for_game,
    }
    return render(request, "teams/team_public.html", ctx)
