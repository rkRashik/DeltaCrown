"""
Smoke tests for Control Plane view (Phase 0 Part E - Regression Guards).

Verifies that:
1. View function can be imported
2. Template exists and loads
3. URL name reverses correctly
4. No basic syntax errors
"""

import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from django.template.loader import get_template

User = get_user_model()

from apps.organizations.models import Organization
from apps.organizations.views.org import org_control_plane


@pytest.mark.django_db
class TestControlPlaneSmoke:
    """Smoke tests for org_control_plane view."""

    def test_view_can_be_imported(self):
        """View function exists and can be imported."""
        assert callable(org_control_plane)

    def test_template_exists(self):
        """Control plane template file exists and loads."""
        template = get_template('organizations/org/org_control_plane.html')
        assert template is not None

    def test_url_reverses_correctly(self):
        """URL name 'organizations:org_control_plane' reverses to valid path."""
        url = reverse('organizations:org_control_plane', kwargs={'org_slug': 'test-org'})
        assert url == '/orgs/test-org/control-plane/'

    def test_anonymous_user_redirected(self):
        """Anonymous users cannot access control plane."""
        org = Organization.objects.create(name="Test Org", slug="test-org")
        client = Client()
        
        response = client.get(reverse('organizations:org_control_plane', kwargs={'org_slug': org.slug}))
        
        # Should redirect to login or show 403
        assert response.status_code in [302, 403]

    def test_ceo_can_access_control_plane(self):
        """CEO user can access their org's control plane."""
        ceo = User.objects.create_user("ceo_user", password="test_pass")
        org = Organization.objects.create(name="Test Org", slug="test-org", ceo=ceo)
        
        client = Client()
        client.login(username="ceo_user", password="test_pass")
        
        response = client.get(reverse('organizations:org_control_plane', kwargs={'org_slug': org.slug}))
        
        assert response.status_code == 200
        assert b'Control Plane' in response.content or b'control-plane' in response.content

    def test_non_member_denied_access(self):
        """Non-member user cannot access control plane."""
        ceo = User.objects.create_user("ceo_user")
        org = Organization.objects.create(name="Test Org", slug="test-org", ceo=ceo)
        
        other_user = User.objects.create_user("other_user", password="test_pass")
        client = Client()
        client.login(username="other_user", password="test_pass")
        
        response = client.get(reverse('organizations:org_control_plane', kwargs={'org_slug': org.slug}))
        
        # Should return 403 Forbidden
        assert response.status_code == 403
