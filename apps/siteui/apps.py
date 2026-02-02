import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SiteUIConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.siteui"
    verbose_name = "Site UI"

    def ready(self):
        # Skip during migrations
        import sys
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return
        
        # NEW: Register event handlers
        try:
            from .events import register_siteui_event_handlers
            register_siteui_event_handlers()
            logger.info("✅ Site UI event handlers registered")
        except Exception as e:
            logger.error(f"❌ Failed to register site UI event handlers: {e}")
