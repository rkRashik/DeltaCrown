from django.apps import AppConfig


class TeamsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.teams"

    def ready(self):
        # wire signals
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Don't crash app startup if migrations aren't applied yet
            pass
