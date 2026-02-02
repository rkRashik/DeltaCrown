import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class TeamsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.teams"
    verbose_name = "Teams (Legacy System)"

    def ready(self):
        # Skip during migrations to avoid initialization issues
        import sys
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return
        
        # NEW: Register event handlers for event-driven architecture
        try:
            from .events import register_team_event_handlers
            register_team_event_handlers()
            logger.info("✅ Team event handlers registered")
        except Exception as e:
            logger.error(f"❌ Failed to register team event handlers: {e}")
        
        # LEGACY: Keep old signals during migration
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Don't crash app startup if migrations aren't applied yet
            pass
