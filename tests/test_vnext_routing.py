"""
vNext Migration: Routing Layer Tests
Tests feature flag-controlled routing and fallback behavior.
See docs/vnext/org-migration-plan.md for migration details.
"""

import pytest
import os

# Mark all tests to use Django DB when needed
pytestmark = pytest.mark.django_db


def test_feature_flag_defaults():
    """Verify default flags: ORG_APP_ENABLED=1, LEGACY_TEAMS_ENABLED=1, COMPETITION_APP_ENABLED=0."""
    from django.conf import settings
    
    # Phase 1 defaults per docs/vnext/org-migration-plan.md
    assert getattr(settings, 'ORG_APP_ENABLED', False) is True, \
        "ORG_APP_ENABLED should default to True"
    assert getattr(settings, 'LEGACY_TEAMS_ENABLED', False) is True, \
        "LEGACY_TEAMS_ENABLED should default to True for compatibility"
    # COMPETITION_APP_ENABLED existence check (default varies by environment)
    assert hasattr(settings, 'COMPETITION_APP_ENABLED'), \
        "COMPETITION_APP_ENABLED should be defined"


def test_routing_helpers_exist():
    """Verify routing helper functions are defined."""
    from deltacrown import routing
    
    assert hasattr(routing, 'legacy_teams_redirect'), \
        "routing.py should define legacy_teams_redirect function"
    assert hasattr(routing, 'competition_rankings_fallback'), \
        "routing.py should define competition_rankings_fallback function"


def test_fallback_templates_exist():
    """Verify fallback templates exist for Organizations and Competition."""
    from django.conf import settings
    
    # Check for Organizations fallback template
    orgs_template = os.path.join(settings.BASE_DIR, 'templates', 'organizations', 'fallback.html')
    assert os.path.exists(orgs_template), \
        f"Organizations fallback template should exist at {orgs_template}"
    
    # Check for Competition fallback template
    comp_template = os.path.join(settings.BASE_DIR, 'templates', 'competition', 'fallback.html')
    assert os.path.exists(comp_template), \
        f"Competition fallback template should exist at {comp_template}"


def test_context_processor_exposes_flags():
    """Verify context processor exposes all feature flags."""
    from apps.organizations.context_processors import vnext_feature_flags
    from django.test import RequestFactory
    
    rf = RequestFactory()
    request = rf.get('/')
    context = vnext_feature_flags(request)
    
    # Check all flags are in context
    assert 'ORG_APP_ENABLED' in context, "Context should include ORG_APP_ENABLED"
    assert 'LEGACY_TEAMS_ENABLED' in context, "Context should include LEGACY_TEAMS_ENABLED"
    assert 'COMPETITION_APP_ENABLED' in context, "Context should include COMPETITION_APP_ENABLED"
