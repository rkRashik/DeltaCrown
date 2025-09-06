from __future__ import annotations
from django.apps import apps
from django.shortcuts import get_object_or_404, render
from django.db.models import Q

def team_public_by_slug(request, game: str, slug: str):
    Team = apps.get_model("teams", "Team")
    TeamAchievement = apps.get_model("teams", "TeamAchievement")
    TeamStats = apps.get_model("teams", "TeamStats")
    TeamMembership = apps.get_model("teams", "TeamMembership")
    Match = apps.get_model("tournaments", "Match")

    team = get_object_or_404(Team, game=game, slug=slug)

    # roster (active)
    roster = TeamMembership.objects.filter(team=team, status="ACTIVE").select_related("profile").order_by("role", "joined_at")

    # latest stats or compute empty
    stats = TeamStats.objects.filter(team=team).order_by("-updated_at").first()

    # upcoming / recent matches
    upcoming = Match.objects.filter(Q(team_a=team) | Q(team_b=team), state="SCHEDULED").order_by("start_at")[:5]
    recent = Match.objects.filter(Q(team_a=team) | Q(team_b=team), state="VERIFIED").order_by("-start_at")[:5]

    achievements = TeamAchievement.objects.filter(team=team).order_by("-year", "-id")[:20]

    ctx = {
        "team": team,
        "roster": roster,
        "stats": stats,
        "upcoming": upcoming,
        "recent": recent,
        "achievements": achievements,
    }
    return render(request, "teams/team_public.html", ctx)
