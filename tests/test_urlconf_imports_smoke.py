"""
Smoke test to catch URLconf import failures early.

This test ensures that all URL configurations can be imported without errors,
preventing runtime failures when Django tries to resolve routes.
"""

import pytest


def test_urlconf_imports():
    """Verify main URLconf imports successfully"""
    import deltacrown.urls  # noqa


def test_organizations_api_urlconf_imports():
    """Verify organizations API URLconf imports successfully"""
    from apps.organizations.api import urls  # noqa


def test_organizations_api_views_package():
    """Verify views package structure is correct"""
    from apps.organizations.api import views  # noqa
    from apps.organizations.api.views import team_manage  # noqa
    from apps.organizations.api.views import user_history  # noqa
    
    # Verify views has the expected functions from __init__.py
    assert hasattr(views, 'create_team')
    assert hasattr(views, 'create_organization')
    assert hasattr(views, 'validate_team_name')
    
    # Verify submodules have expected functions
    assert hasattr(team_manage, 'team_detail')
    assert hasattr(team_manage, 'add_member')
    assert hasattr(user_history, 'user_team_history')
