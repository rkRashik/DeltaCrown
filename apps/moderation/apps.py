"""
Moderation App Configuration
"""
from django.apps import AppConfig


class ModerationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.moderation'
    verbose_name = 'Moderation'
    
    def ready(self):
        """Import signal handlers when app is ready."""
        # Import signals if needed in future
        pass
