"""
Django app configuration for Team & Organization Management vNext.

This app replaces the legacy apps/teams system with a modern,
organization-first architecture supporting professional esports workflows.
"""

from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    """
    Configuration for the organizations app.
    
    This app manages:
    - Organizations (verified esports brands)
    - Teams (competitive units)
    - Memberships (roster management)
    - Rankings (Crown Point system)
    - Migration bridge (legacy to vNext)
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.organizations'
    verbose_name = 'Team & Organization Management'
    
    def ready(self):
        """
        Import signal handlers when app is ready.
        
        Signals handle:
        - Cache invalidation on data changes
        - Audit logging for critical actions
        - Ranking recalculations
        - Notification triggers
        """
        # Import signals when implemented (Phase 2)
        # import apps.organizations.signals.handlers  # noqa: F401
        pass
