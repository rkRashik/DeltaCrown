from django.apps import AppConfig


class TeamsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.teams"   # <-- IMPORTANT: full dotted path to the package
    verbose_name = "Teams"
