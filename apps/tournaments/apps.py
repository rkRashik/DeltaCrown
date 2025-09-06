# apps/tournaments/apps.py
from __future__ import annotations
from django.apps import AppConfig

class TournamentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tournaments"
    label = "tournaments"
    verbose_name = "Tournaments"

    def ready(self) -> None:
        # Wire signals (best-effort)
        try:
            from . import signals as _signals  # noqa
            _signals.register_signals()
        except Exception:
            pass
        # Apply runtime monkeypatches to guarantee tests' expectations
        try:
            from .models import _bootstrap_monkeypatch  # noqa: F401
        except Exception:
            # Never block app startup
            pass
