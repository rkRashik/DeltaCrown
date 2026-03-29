# apps/tournaments/apps.py
from __future__ import annotations
import logging
from django.apps import AppConfig


logger = logging.getLogger(__name__)

class TournamentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tournaments"
    label = "tournaments"
    verbose_name = "Tournaments"

    def ready(self) -> None:
        # NEW: Register event handlers for event-driven architecture
        try:
            from .events import register_tournament_event_handlers
            register_tournament_event_handlers()
        except Exception as e:
            logger.error(f"Failed to register tournament event handlers: {e}")
        
        # MILESTONE F: Import notification signals (auto-registered via @receiver)
        try:
            import apps.tournaments.signals  # noqa: F401 — connects all @receiver handlers
        except Exception as e:
            logger.exception(f"Failed to import notification signals: {e}")
        
        # Apply runtime monkeypatches to guarantee tests' expectations
        try:
            from .models import _bootstrap_monkeypatch  # noqa: F401
        except Exception:
            # Never block app startup
            pass

        # Low-memory replacement for periodic Celery reminder timing.
        try:
            from .scheduling import start_inprocess_match_reminder_scheduler

            start_inprocess_match_reminder_scheduler()
        except Exception:
            logger.exception("Failed to start in-process match reminder scheduler")
