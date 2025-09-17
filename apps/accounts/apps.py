from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"

    def ready(self):
        # Import signal handlers that mirror rows into auth_user for legacy FKs.
        from . import signals  # noqa: F401
