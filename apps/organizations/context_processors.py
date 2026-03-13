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
            - ORG_APP_ENABLED: bool (vNext: Organizations app enabled)
            - LEGACY_TEAMS_ENABLED: bool (vNext: Legacy teams fallback)
            - COMPETITION_APP_ENABLED: bool (vNext: Competition rankings)
    """
    result = {
        'TEAM_VNEXT_ADAPTER_ENABLED': getattr(settings, 'TEAM_VNEXT_ADAPTER_ENABLED', False),
        'TEAM_VNEXT_FORCE_LEGACY': getattr(settings, 'TEAM_VNEXT_FORCE_LEGACY', False),
        'TEAM_VNEXT_ROUTING_MODE': getattr(settings, 'TEAM_VNEXT_ROUTING_MODE', 'adapter_first'),
        # vNext Migration: Organizations & Competition flags
        'ORG_APP_ENABLED': getattr(settings, 'ORG_APP_ENABLED', False),
        'LEGACY_TEAMS_ENABLED': getattr(settings, 'LEGACY_TEAMS_ENABLED', False),
        'COMPETITION_APP_ENABLED': getattr(settings, 'COMPETITION_APP_ENABLED', False),
    }

    # Optional troubleshooting toggle. Keep disabled in production to avoid
    # noisy logs from bot probes and 404 paths.
    if getattr(settings, 'VNEXT_FLAGS_CONTEXT_DEBUG', False):
        logger.debug("vNext flags context on %s: %s", request.path, result)

    return result
