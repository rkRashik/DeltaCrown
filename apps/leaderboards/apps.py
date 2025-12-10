"""
Leaderboards App Configuration
Phase E: Public Leaderboards API
Phase F: Leaderboard Ranking Engine Optimization
Phase 8, Epic 8.2: User Stats Service (Event Handlers)
"""
from django.apps import AppConfig


class LeaderboardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.leaderboards"
    verbose_name = "Leaderboards"
    
    def ready(self):
        """Import event handlers when app is ready."""
        # Import event handlers to register them with EventBus
        import apps.leaderboards.event_handlers  # noqa: F401
