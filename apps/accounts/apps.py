import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"

    def ready(self):
        # NEW: Register event handlers
        try:
            from .events import register_accounts_event_handlers
            register_accounts_event_handlers()
            logger.info("✅ Accounts event handlers registered")
        except Exception as e:
            logger.error(f"❌ Failed to register accounts event handlers: {e}")
        
        # LEGACY: Keep old signals during migration
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
