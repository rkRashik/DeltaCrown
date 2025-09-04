from django.apps import AppConfig


class EconomyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.economy"

    def ready(self):
        # wire signals
        from . import signals  # noqa: F401
