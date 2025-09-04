# apps/tournaments/apps.py
from __future__ import annotations

from django.apps import AppConfig


class TournamentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tournaments"
    label = "tournaments"

    def ready(self) -> None:
        # Connect signal validators without touching models.py
        from . import signals  # noqa: F401
        signals.connect()
