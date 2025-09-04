# apps/tournaments/apps.py
from __future__ import annotations

from django.apps import AppConfig


class TournamentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tournaments"

    def ready(self):
        # Attach signals without circular imports
        from . import signals  # noqa: WPS433
        signals.register_signals()
