"""Competition app configuration."""
from django.apps import AppConfig


class CompetitionConfig(AppConfig):
    """Configuration for DeltaCrown Competition app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.competition'
    verbose_name = 'Competition & Ranking'
    
    def ready(self):
        """Import signal handlers and perform app initialization.
        
        Note: Schema detection is now performed lazily in admin.py and views.py
        using apps.competition.utils.schema.competition_schema_ready() function.
        This avoids database introspection during app initialization.
        """
        # Future: Import signal handlers for match verification workflow
        pass
