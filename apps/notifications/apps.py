# apps/notifications/apps.py
from django.apps import AppConfig
import logging

log = logging.getLogger(__name__)

class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self):
        try:
            from . import signals  # noqa: F401
        except Exception as e:
            log.warning("Notifications signals not loaded: %s", e)
