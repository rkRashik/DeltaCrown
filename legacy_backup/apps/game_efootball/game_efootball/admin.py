# apps/game_efootball/admin.py
from __future__ import annotations
from django.contrib import admin

# Do NOT register snapshot models here; they are shown as inlines on Registration.
# from .models_registration import EfootballSoloInfo, EfootballDuoInfo
# admin.site.register(EfootballSoloInfo)  # ← removed
# admin.site.register(EfootballDuoInfo)  # ← removed

# If you have config models (EfootballConfig), keep those registered normally:
try:
    from .models import EfootballConfig  # adjust if your config model lives elsewhere
except Exception:
    EfootballConfig = None

if EfootballConfig:
    @admin.register(EfootballConfig)
    class EfootballConfigAdmin(admin.ModelAdmin):
        list_display = ("id", "tournament",)
