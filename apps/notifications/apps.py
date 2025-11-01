import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"

    def ready(self):
        # NEW: Register event handlers for event-driven architecture
        try:
            from .events import register_notification_event_handlers
            register_notification_event_handlers()
            logger.info("✅ Notification event handlers registered")
        except Exception as e:
            logger.error(f"❌ Failed to register notification event handlers: {e}")
        
        # LEGACY: Keep old signal subscribers during migration
        try:
            from . import subscribers  # noqa: F401
        except Exception:
            pass
