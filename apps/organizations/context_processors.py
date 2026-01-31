"""
Context processors for organizations app.

Provides template context variables for feature flags and user state.
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def vnext_feature_flags(request):
    """
    Adds vNext feature flags to template context.
    
    Makes feature flags available in all templates for UI gating.
    
    Returns:
        dict: Feature flag values
            - TEAM_VNEXT_ADAPTER_ENABLED: bool
            - TEAM_VNEXT_FORCE_LEGACY: bool
            - TEAM_VNEXT_ROUTING_MODE: str
    """
    result = {
        'TEAM_VNEXT_ADAPTER_ENABLED': getattr(settings, 'TEAM_VNEXT_ADAPTER_ENABLED', False),
        'TEAM_VNEXT_FORCE_LEGACY': getattr(settings, 'TEAM_VNEXT_FORCE_LEGACY', False),
        'TEAM_VNEXT_ROUTING_MODE': getattr(settings, 'TEAM_VNEXT_ROUTING_MODE', 'adapter_first'),
    }
    # Force logging to see if this is being called
    logger.warning(f"[DEBUG] CONTEXT PROCESSOR CALLED for {request.path}: {result}")
    # Removed print() to avoid Unicode errors in Windows terminal
    return result
