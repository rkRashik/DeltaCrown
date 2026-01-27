"""
Regression tests for Control Plane routing and imports.

Ensures:
- org_control_plane view is properly imported
- URL routing works correctly
- No import errors at startup
"""

import pytest
from django.urls import reverse, resolve


class TestControlPlaneImports:
    """Test that org_control_plane imports cleanly (no DB needed)."""
    
    def test_import_from_views_package(self):
        """CONTRACT: apps.organizations.views must export org_control_plane."""
        from apps.organizations import views
        
        assert hasattr(views, 'org_control_plane'), \
            "org_control_plane not found in apps.organizations.views"
    
    def test_import_from_org_module(self):
        """CONTRACT: apps.organizations.views.org must define org_control_plane."""
        from apps.organizations.views import org
        
        assert hasattr(org, 'org_control_plane'), \
            "org_control_plane not found in apps.organizations.views.org"
    
    def test_direct_import(self):
        """CONTRACT: Can import org_control_plane directly."""
        from apps.organizations.views import org_control_plane
        
        assert callable(org_control_plane), \
            "org_control_plane is not callable"


class TestControlPlaneURLs:
    """Test that Control Plane URLs work correctly (no DB needed)."""
    
    def test_reverse_url_with_slug(self):
        """CONTRACT: reverse() must work with org_slug parameter."""
        url = reverse('organizations:org_control_plane', kwargs={'org_slug': 'syntax'})
        
        assert url == '/orgs/syntax/control-plane/', \
            f"Expected /orgs/syntax/control-plane/, got {url}"
    
    def test_resolve_url_pattern(self):
        """CONTRACT: URL pattern must resolve to correct view."""
        resolved = resolve('/orgs/test-org/control-plane/')
        
        assert resolved.view_name == 'organizations:org_control_plane', \
            f"Expected organizations:org_control_plane, got {resolved.view_name}"
        
        assert resolved.kwargs['org_slug'] == 'test-org', \
            f"Expected org_slug='test-org', got {resolved.kwargs}"
    
    def test_url_name_consistency(self):
        """CONTRACT: URL name must follow naming convention."""
        # All org URLs should use 'org_' prefix
        from django.urls import get_resolver
        
        resolver = get_resolver()
        org_urls = [
            name for name, pattern in resolver.reverse_dict.items()
            if isinstance(name, str) and name.startswith('organizations:org_')
        ]
        
        assert 'organizations:org_control_plane' in org_urls, \
            "org_control_plane not registered in organizations namespace"


@pytest.mark.django_db
def test_unauthenticated_redirects_to_login(client):
    """CONTRACT: Unauthenticated users must be redirected to login."""
    response = client.get('/orgs/syntax/control-plane/')
    
    # @login_required should redirect to login
    assert response.status_code == 302, \
        f"Expected 302 redirect, got {response.status_code}"
    
    assert '/accounts/login/' in response.url, \
        f"Expected redirect to login, got {response.url}"
