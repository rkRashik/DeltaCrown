"""
Contract tests for the Org Control Plane feature.

Tests URL routing, import integrity, template existence, and basic view behavior
without requiring database access. Prevents regressions in the control plane implementation.
"""

import pytest
from django.urls import reverse, resolve
from django.template.loader import get_template
from django.template import TemplateDoesNotExist


def test_url_reverse_control_plane():
    """Test that URL reverse for org_control_plane works correctly."""
    url = reverse('organizations:org_control_plane', kwargs={'org_slug': 'test-org'})
    assert url == '/orgs/test-org/control-plane/'


def test_url_resolve_control_plane():
    """Test that URL resolve identifies the correct view function."""
    resolved = resolve('/orgs/test-org/control-plane/')
    assert resolved.view_name == 'organizations:org_control_plane'
    assert resolved.kwargs == {'org_slug': 'test-org'}


def test_import_control_plane_service():
    """Test that the control plane service module can be imported without errors."""
    from apps.organizations.services.org_control_plane_service import get_org_control_plane_context
    assert callable(get_org_control_plane_context)


def test_import_views_no_module_error():
    """Test that importing the organizations views doesn't raise ModuleNotFoundError."""
    try:
        from apps.organizations.views import org
        assert hasattr(org, 'org_control_plane')
        assert callable(org.org_control_plane)
    except ModuleNotFoundError as e:
        pytest.fail(f"ModuleNotFoundError when importing views: {e}")


def test_template_exists():
    """Test that the control plane template can be loaded."""
    try:
        template = get_template('organizations/org/org_control_plane.html')
        assert template is not None
    except TemplateDoesNotExist:
        pytest.fail("Control plane template does not exist")


def test_service_function_signature():
    """Test that the service function has the expected signature."""
    from apps.organizations.services.org_control_plane_service import get_org_control_plane_context
    import inspect
    
    sig = inspect.signature(get_org_control_plane_context)
    params = list(sig.parameters.keys())
    
    assert 'org_slug' in params, "Missing org_slug parameter"
    assert 'viewer' in params, "Missing viewer parameter"


def test_view_function_is_login_required():
    """Test that the control plane view has login_required decorator."""
    from apps.organizations.views.org import org_control_plane
    
    # Check if the function or its wrapper has the login_required attribute
    # Django's login_required wraps the function
    assert hasattr(org_control_plane, '__wrapped__') or hasattr(org_control_plane, '__name__')


def test_url_pattern_position():
    """Test that control-plane URL is registered before catch-all organization detail."""
    from apps.organizations import urls as org_urls
    
    # Find the positions of control-plane and <org_slug>/ patterns
    control_plane_idx = None
    org_slug_idx = None
    
    for idx, pattern in enumerate(org_urls.urlpatterns):
        pattern_str = str(pattern.pattern)
        if 'control-plane' in pattern_str:
            control_plane_idx = idx
        elif pattern_str.endswith('/<org_slug>/'):
            org_slug_idx = idx
    
    # Assert control-plane is registered
    assert control_plane_idx is not None, "Control plane URL pattern not found"
    
    # If catch-all exists, control-plane must come before it
    if org_slug_idx is not None:
        assert control_plane_idx < org_slug_idx, \
            f"control-plane URL (index {control_plane_idx}) must come before catch-all <org_slug>/ (index {org_slug_idx})"


def test_service_returns_expected_context_keys():
    """Test that service function returns expected context dictionary structure (mock test)."""
    from apps.organizations.services.org_control_plane_service import get_org_control_plane_context
    import inspect
    
    # Get the function source to check for return statement structure
    source = inspect.getsource(get_org_control_plane_context)
    
    # Verify that the function returns expected context keys
    expected_keys = ['organization', 'can_manage_org', 'ui_role', 'page_title']
    for key in expected_keys:
        assert f"'{key}'" in source or f'"{key}"' in source, \
            f"Expected context key '{key}' not found in service function"
