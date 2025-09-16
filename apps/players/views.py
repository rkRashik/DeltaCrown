from __future__ import annotations
from django.contrib.auth import get_user_model
from django.shortcuts import render, get_object_or_404
from django.apps import apps

User = get_user_model()

def player_detail(request, username: str):
    user = get_object_or_404(User, username=username)
    Profile = apps.get_model("user_profile", "UserProfile")
    TeamMembership = apps.get_model("teams", "TeamMembership")
    Match = apps.get_model("tournaments", "Match")

    profile = getattr(user, "profile", None)

    teams = []
    try:
        teams = [m.team for m in TeamMembership.objects.filter(profile=profile, status="ACTIVE").select_related("team")]
    except Exception:
        teams = []

    results = []
    if Match and profile:
        try:
            results = list(Match.objects.filter(user_a=profile).order_by("-created_at")[:10])
        except Exception:
            results = []

    ctx = {"player": profile, "user": user, "teams": teams, "results": results}
    return render(request, "players/detail.html", ctx)

