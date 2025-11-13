"""
Leaderboards App Configuration
Phase E: Public Leaderboards API
Phase F: Leaderboard Ranking Engine Optimization
"""
from django.apps import AppConfig


class LeaderboardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.leaderboards"
    verbose_name = "Leaderboards"
