from django.apps import AppConfig


class CorelibConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # This MUST be the full dotted path to the app package
    name = "apps.corelib"
    # Optional stable label used internally by Django (no dots)
    label = "corelib"
