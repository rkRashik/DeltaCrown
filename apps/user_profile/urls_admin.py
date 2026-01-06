# apps/user_profile/urls_admin.py
# Phase 9A-30: Custom Game Passport Admin URLs (separate from main user_profile URLs)

from django.urls import path
from .views.game_passport_admin import (
    game_passport_admin_dashboard, game_passport_detail,
    game_passport_verify, game_passport_flag, game_passport_reset,
    game_passport_unlock, game_passport_override_cooldown
)

app_name = "game_passport_admin"

urlpatterns = [
    path("", game_passport_admin_dashboard, name="dashboard"),
    path("<int:passport_id>/", game_passport_detail, name="detail"),
    path("<int:passport_id>/verify/", game_passport_verify, name="verify"),
    path("<int:passport_id>/flag/", game_passport_flag, name="flag"),
    path("<int:passport_id>/reset/", game_passport_reset, name="reset"),
    path("<int:passport_id>/unlock/", game_passport_unlock, name="unlock"),
    path("<int:passport_id>/override-cooldown/", game_passport_override_cooldown, name="override_cooldown"),
]
