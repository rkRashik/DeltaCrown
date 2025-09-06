from __future__ import annotations
from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse

class TeamEditForm(forms.ModelForm):
    class Meta:
        model = apps.get_model("teams", "Team")
        fields = ["name", "tag", "logo", "slug", "region",
                  "twitter", "instagram", "discord", "youtube", "twitch", "linktree",
                  "banner_image", "roster_image"]
        widgets = {
            "slug": forms.TextInput(attrs={"placeholder": "unique-per-game"}),
            "region": forms.TextInput(attrs={"placeholder": "e.g., Bangladesh"}),
        }

class AchievementForm(forms.ModelForm):
    class Meta:
        model = apps.get_model("teams", "TeamAchievement")
        fields = ["title", "placement", "year", "notes", "tournament"]

@login_required
@transaction.atomic
def manage_team_by_game(request, game: str):
    Team = apps.get_model("teams", "Team")
    TeamAchievement = apps.get_model("teams", "TeamAchievement")
    TeamStats = apps.get_model("teams", "TeamStats")
    # Find captain's team for this game
    profile = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
    if not profile:
        raise PermissionDenied("Profile required.")

    team = Team.objects.filter(game=game, captain_id=profile.id).first()
    if not team:
        raise PermissionDenied("You must be captain of a team for this game.")

    if request.method == "POST":
        if "rebuild_stats" in request.POST:
            from apps.teams.services.stats import recompute_team_stats
            snap = recompute_team_stats(team)
            messages.success(request, "Stats rebuilt.")
            return redirect(request.path)

        if "delete_achievement_id" in request.POST:
            ach_id = request.POST.get("delete_achievement_id")
            TeamAchievement.objects.filter(id=ach_id, team=team).delete()
            messages.success(request, "Achievement deleted.")
            return redirect(request.path)

        form = TeamEditForm(request.POST, request.FILES, instance=team)
        aform = AchievementForm(request.POST)
        if form.is_valid():
            form.save()
            if aform.is_valid() and aform.cleaned_data.get("title"):
                ach = aform.save(commit=False)
                ach.team = team
                ach.save()
                messages.success(request, "Team updated and achievement added.")
            else:
                messages.success(request, "Team updated.")
            return redirect(request.path)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TeamEditForm(instance=team)
        aform = AchievementForm()

    latest_stats = TeamStats.objects.filter(team=team).order_by("-updated_at").first()
    achievements = TeamAchievement.objects.filter(team=team).order_by("-year", "-id")
    return render(request, "teams/team_manage.html", {
        "team": team,
        "form": form,
        "aform": aform,
        "latest_stats": latest_stats,
        "achievements": achievements,
        "game": game,
    })
