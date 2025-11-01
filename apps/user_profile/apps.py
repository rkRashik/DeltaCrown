import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class UserProfileConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.user_profile"

    def ready(self):
        # NEW: Register event handlers
        try:
            from .events import register_user_profile_event_handlers
            register_user_profile_event_handlers()
            logger.info("✅ User profile event handlers registered")
        except Exception as e:
            logger.error(f"❌ Failed to register user profile event handlers: {e}")
        
        # LEGACY: Keep old signals during migration
        try:
            import apps.user_profile.signals  # noqa
        except Exception:
            pass
