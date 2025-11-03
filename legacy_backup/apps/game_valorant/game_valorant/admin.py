# apps/game_valorant/admin.py
from __future__ import annotations
from django.contrib import admin

# Do NOT register snapshot models here; they are shown as inlines on Registration.
# from .models_registration import ValorantTeamInfo, ValorantPlayer
# admin.site.register(ValorantTeamInfo)  # ← removed
# admin.site.register(ValorantPlayer)    # ← removed

# If you have a ValorantConfig model, keep it visible:
try:
    from .models import ValorantConfig  # adjust the import if needed
except Exception:
    ValorantConfig = None

if ValorantConfig:
    @admin.register(ValorantConfig)
    class ValorantConfigAdmin(admin.ModelAdmin):
        list_display = ("id", "tournament",)
