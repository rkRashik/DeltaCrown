from django.apps import AppConfig


class EconomyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.economy"
    verbose_name = "Finance & Rewards"

    def ready(self):
        # wire signals
        from . import signals  # noqa: F401
