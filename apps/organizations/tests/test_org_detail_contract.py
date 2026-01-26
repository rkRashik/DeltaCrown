"""
Organization Detail Contract Tests
Tests for /orgs/<slug>/ detail page functionality and privacy.
"""

import pytest
from django.urls import reverse
from apps.organizations.models.organization import Organization


@pytest.mark.django_db
class TestOrgDetailRouting:
    """Tests for URL routing and resolution."""
    
    def test_org_detail_url_resolves(self):
        """Test /orgs/<slug>/ URL resolves to correct view."""
        url = reverse('organizations:organization-detail', kwargs={'org_slug': 'test-org'})
        assert url == '/orgs/test-org/'
    
    def test_org_detail_loads_for_public(self, client, org_factory):
        """Test organization detail loads for anonymous user."""
        org = org_factory(slug='syntax-esports')
        
        response = client.get(f'/orgs/{org.slug}/')
        
        assert response.status_code == 200
        assert 'organizations/org/org_detail.html' in [t.name for t in response.templates]
    
    def test_org_detail_loads_for_authenticated(self, authenticated_client, org_factory):
        """Test organization detail loads for authenticated user."""
        org = org_factory(slug='protocol-v')
        
        response = authenticated_client.get(f'/orgs/{org.slug}/')
        
        assert response.status_code == 200
        assert response.context['organization'] == org


@pytest.mark.django_db
class TestOrgDetailPermissions:
    """Tests for permission-based content visibility."""
    
    def test_settings_tab_hidden_for_public(self, client, org_factory):
        """Test Settings tab not visible to anonymous users."""
        org = org_factory(slug='test-org')
        
        response = client.get(f'/orgs/{org.slug}/')
        content = response.content.decode()
        
        # Settings tab should be wrapped in {% if can_manage_org %}
        assert response.context['can_manage_org'] is False
        # In template, Settings tab is conditionally rendered
        assert 'href="#settings"' not in content or 'can_manage_org' in content
    
    def test_settings_tab_visible_for_ceo(self, client, org_factory, player_factory):
        """Test Settings tab visible to CEO."""
        ceo = player_factory(username='boss')
        org = org_factory(slug='test-org', ceo=ceo)
        
        client.force_login(ceo.user)
        response = client.get(f'/orgs/{org.slug}/')
        
        assert response.status_code == 200
        assert response.context['can_manage_org'] is True
    
    def test_finance_tab_hidden_for_public(self, client, org_factory):
        """Test Financials tab hidden for public users."""
        org = org_factory(slug='test-org')
        
        response = client.get(f'/orgs/{org.slug}/')
        
        assert response.context['can_manage_org'] is False
        content = response.content.decode()
        # Finance section should not render for public
        assert 'id="finance"' not in content or 'can_manage_org' in content
    
    def test_finance_tab_visible_for_manager(self, client, org_factory, player_factory, org_membership_factory):
        """Test Financials tab visible to org manager."""
        manager = player_factory(username='manager')
        org = org_factory(slug='test-org')
        org_membership_factory(organization=org, player=manager, role='MANAGER')
        
        client.force_login(manager.user)
        response = client.get(f'/orgs/{org.slug}/')
        
        assert response.status_code == 200
        assert response.context['can_manage_org'] is True


@pytest.mark.django_db
class TestOrgDetailContext:
    """Tests for context data provided to template."""
    
    def test_context_includes_organization(self, client, org_factory):
        """Test context includes organization object."""
        org = org_factory(slug='test-org', name='Test Organization')
        
        response = client.get(f'/orgs/{org.slug}/')
        
        assert 'organization' in response.context
        assert response.context['organization'].name == 'Test Organization'
    
    def test_context_includes_can_manage_org(self, client, org_factory):
        """Test context includes can_manage_org boolean."""
        org = org_factory(slug='test-org')
        
        response = client.get(f'/orgs/{org.slug}/')
        
        assert 'can_manage_org' in response.context
        assert isinstance(response.context['can_manage_org'], bool)
    
    def test_context_includes_active_teams_count(self, client, org_factory, team_factory):
        """Test context includes active teams count."""
        org = org_factory(slug='test-org')
        team_factory(organization=org, is_active=True)
        team_factory(organization=org, is_active=True)
        team_factory(organization=org, is_active=False)  # Inactive
        
        response = client.get(f'/orgs/{org.slug}/')
        
        assert 'active_teams_count' in response.context
        assert response.context['active_teams_count'] == 2


@pytest.mark.django_db
class TestOrgDetailModelHelpers:
    """Tests for organization model URL helpers."""
    
    def test_get_absolute_url_points_to_detail(self, org_factory):
        """Test get_absolute_url() returns detail page URL."""
        org = org_factory(slug='syntax-org')
        
        url = org.get_absolute_url()
        
        assert url == '/orgs/syntax-org/'
    
    def test_get_hub_url_points_to_hub(self, org_factory):
        """Test get_hub_url() returns hub page URL."""
        org = org_factory(slug='protocol-org')
        
        url = org.get_hub_url()
        
        assert url == '/orgs/protocol-org/hub/'


@pytest.mark.django_db
class TestOrgDetailLinking:
    """Tests for cross-page navigation linking."""
    
    def test_directory_links_to_detail(self, client, org_factory):
        """Test organization directory links to detail page."""
        org = org_factory(slug='test-org', name='Test Org')
        
        response = client.get('/orgs/')
        content = response.content.decode()
        
        # Directory should have links to /orgs/<slug>/
        assert f'/orgs/{org.slug}/' in content
        assert f'/orgs/{org.slug}/hub/' not in content  # Should NOT link directly to hub
    
    def test_detail_has_hub_button_for_managers(self, client, org_factory, player_factory):
        """Test detail page has 'Open Hub' button for managers."""
        ceo = player_factory(username='ceo')
        org = org_factory(slug='test-org', ceo=ceo)
        
        client.force_login(ceo.user)
        response = client.get(f'/orgs/{org.slug}/')
        content = response.content.decode()
        
        # Should have link to hub
        assert org.get_hub_url() in content
        assert 'Open Hub' in content or 'Manage Org' in content
    
    def test_streams_tab_exists(self, client, org_factory):
        """Test Media/Streams tab exists in template."""
        org = org_factory(slug='test-org')
        
        response = client.get(f'/orgs/{org.slug}/')
        content = response.content.decode()
        
        # Check for Streams tab
        assert 'Media / Streams' in content or 'Media/Streams' in content
        assert 'id="streams"' in content
    
    def test_legacy_wall_tab_exists(self, client, org_factory):
        """Test Legacy Wall tab exists in template."""
        org = org_factory(slug='test-org')
        
        response = client.get(f'/orgs/{org.slug}/')
        content = response.content.decode()
        
        # Check for Legacy Wall tab
        assert 'Legacy Wall' in content
        assert 'id="legacy"' in content


@pytest.mark.django_db
class TestOrgDetailErrors:
    """Tests for error handling."""
    
    def test_nonexistent_org_returns_404(self, client):
        """Test accessing non-existent org returns 404."""
        response = client.get('/orgs/nonexistent-org/')
        
        assert response.status_code == 404
    
    def test_inactive_org_returns_404(self, client, org_factory):
        """Test accessing inactive org returns 404."""
        org = org_factory(slug='inactive-org', is_active=False)
        
        response = client.get(f'/orgs/{org.slug}/')
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestOrgDetailIntegration:
    """Integration tests for complete user flows."""
    
    def test_public_user_flow(self, client, org_factory):
        """Test public user viewing organization detail."""
        org = org_factory(
            slug='public-org',
            name='Public Organization',
            description='Test description'
        )
        
        # 1. Access detail page
        response = client.get(f'/orgs/{org.slug}/')
        assert response.status_code == 200
        
        # 2. Can see basic info
        content = response.content.decode()
        assert 'Public Organization' in content
        
        # 3. Cannot see management features
        assert response.context['can_manage_org'] is False
    
    def test_ceo_user_flow(self, client, org_factory, player_factory):
        """Test CEO viewing and managing organization."""
        ceo = player_factory(username='ceo')
        org = org_factory(slug='ceo-org', ceo=ceo)
        
        client.force_login(ceo.user)
        
        # 1. Access detail page
        response = client.get(f'/orgs/{org.slug}/')
        assert response.status_code == 200
        
        # 2. Can manage org
        assert response.context['can_manage_org'] is True
        
        # 3. Has access to hub
        content = response.content.decode()
        assert org.get_hub_url() in content
