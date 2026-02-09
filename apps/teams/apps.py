from django.apps import AppConfig


class TeamsConfig(AppConfig):
    """
    FROZEN STUB — apps.teams is a legacy app retained solely for:
      1. Historical migration files (ForeignKey resolution across other apps)
      2. The teams_team / teams_teammembership DB tables
    All new development belongs in apps.organizations.
    Do NOT add views, URLs, services, or signals here.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.teams"
    verbose_name = "Teams (Frozen Legacy Stub)"
