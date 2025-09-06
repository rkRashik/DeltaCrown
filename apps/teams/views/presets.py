
# apps/teams/views/presets.py
from __future__ import annotations
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.apps import apps

EfootballTeamPreset = apps.get_model("teams", "EfootballTeamPreset")
ValorantTeamPreset = apps.get_model("teams", "ValorantTeamPreset")

@login_required
def my_presets(request):
    prof = apps.get_model("user_profile", "UserProfile").objects.filter(user=request.user).first()
    ef = EfootballTeamPreset.objects.filter(profile=prof).order_by("-created_at") if prof else []
    va = ValorantTeamPreset.objects.filter(profile=prof).order_by("-created_at") if prof else []
    return render(request, "teams/presets_list.html", {"ef_presets": ef, "va_presets": va})

@login_required
@require_POST
def delete_preset(request, kind: str, preset_id: int):
    prof = apps.get_model("user_profile", "UserProfile").objects.filter(user=request.user).first()
    Model = EfootballTeamPreset if kind == "efootball" else ValorantTeamPreset
    preset = get_object_or_404(Model, id=preset_id, profile=prof)
    preset.delete()
    return redirect("teams:my_presets")
