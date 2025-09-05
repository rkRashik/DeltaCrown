﻿from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"

    def ready(self):
        # Connect signal subscribers (idempotent)
        from . import subscribers  # noqa: F401
