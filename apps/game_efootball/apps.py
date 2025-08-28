from django.apps import AppConfig

class GameEfootballConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.game_efootball"   # <-- full dotted path
    verbose_name = "eFootball (Config)"
