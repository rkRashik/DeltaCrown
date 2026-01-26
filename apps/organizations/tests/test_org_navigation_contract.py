"""
Organization Navigation Contract Tests.

Tests to ensure proper URL routing and linking between:
- Organization Directory (/orgs/)
- Organization Detail (/orgs/<slug>/)
- Organization Hub (/orgs/<slug>/hub/)

These tests prevent regressions where directory links incorrectly go to hub
instead of detail page.

Contract Rules:
1. Directory MUST link to detail page (not hub)
2. Detail page MAY link to hub (only for authorized users)
3. All three routes must be accessible via reverse()
4. Templates must not hardcode URLs
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.template import Context, Template

from apps.organizations.models import Organization

User = get_user_model()


class TestOrganizationURLContract(TestCase):
    """Test that all organization URLs can be reversed correctly."""
    
    def test_org_directory_reverses(self):
        """Directory URL must reverse without kwargs."""
        url = reverse('organizations:org_directory')
        self.assertEqual(url, '/orgs/')
    
    def test_org_detail_reverses(self):
        """Detail URL must reverse with org_slug kwarg."""
        url = reverse('organizations:organization_detail', kwargs={'org_slug': 'test-org'})
        self.assertEqual(url, '/orgs/test-org/')
    
    def test_org_hub_reverses(self):
        """Hub URL must reverse with org_slug kwarg."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        self.assertEqual(url, '/orgs/test-org/hub/')


class TestOrganizationModelURLHelpers(TestCase):
    """Test that Organization model provides correct URL helpers."""
    
    def setUp(self):
        """Create test user and organization."""
        self.ceo = User.objects.create_user(
            username='ceo',
            email='ceo@test.com',
            password='testpass123'
        )
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.ceo
        )
    
    def test_get_absolute_url_returns_detail_page(self):
        """get_absolute_url() must return detail page URL."""
        url = self.org.get_absolute_url()
        self.assertEqual(url, '/orgs/test-org/')
        
        # Verify it matches reverse
        expected = reverse('organizations:organization_detail', kwargs={'org_slug': self.org.slug})
        self.assertEqual(url, expected)
    
    def test_get_hub_url_returns_hub_page(self):
        """get_hub_url() must return hub page URL."""
        url = self.org.get_hub_url()
        self.assertEqual(url, '/orgs/test-org/hub/')
        
        # Verify it matches reverse
        expected = reverse('organizations:org_hub', kwargs={'org_slug': self.org.slug})
        self.assertEqual(url, expected)


class TestOrganizationDirectoryTemplateLinks(TestCase):
    """Test that directory template links correctly to detail page."""
    
    def setUp(self):
        """Create test data."""
        self.ceo = User.objects.create_user(
            username='ceo',
            email='ceo@test.com',
            password='testpass123'
        )
        self.org1 = Organization.objects.create(
            name='Top Org',
            slug='top-org',
            ceo=self.ceo,
            is_verified=True
        )
        self.org2 = Organization.objects.create(
            name='Second Org',
            slug='second-org',
            ceo=self.ceo
        )
        self.org3 = Organization.objects.create(
            name='Third Org',
            slug='third-org',
            ceo=self.ceo
        )
        self.client = Client()
    
    def test_directory_contains_detail_page_links(self):
        """Directory page must contain links to detail pages."""
        response = self.client.get('/orgs/')
        self.assertEqual(response.status_code, 200)
        
        # Check that detail page links exist
        self.assertContains(response, '/orgs/top-org/')
        self.assertContains(response, '/orgs/second-org/')
        self.assertContains(response, '/orgs/third-org/')
    
    def test_directory_does_not_only_link_to_hub(self):
        """Directory must not only link to hub pages for org cards.
        
        Hub links may exist for separate actions, but the primary org
        click targets must go to detail pages.
        """
        response = self.client.get('/orgs/')
        content = response.content.decode('utf-8')
        
        # Count detail vs hub links
        detail_link_count = content.count('/orgs/top-org/"')
        hub_link_count = content.count('/orgs/top-org/hub/')
        
        # Detail links should be present
        self.assertGreater(detail_link_count, 0, 
                          "Directory must contain at least one detail page link")
        
        # If hub links exist, they should be fewer than detail links
        # (hub links may appear in admin/management buttons, but not primary nav)
        if hub_link_count > 0:
            self.assertLess(hub_link_count, detail_link_count,
                           "Hub links should be secondary to detail links in directory")
    
    def test_podium_cards_link_to_detail(self):
        """Top 3 podium cards must link to detail pages.
        
        Checks the organization name links in the top 3 cards.
        """
        response = self.client.get('/orgs/')
        content = response.content.decode('utf-8')
        
        # Look for patterns like: <a href="...organization_detail...
        # The exact pattern depends on template structure, but we can check
        # that the slug appears in the URL before any "/hub/" suffix
        
        # Simple check: ensure top-org appears as a direct link
        self.assertIn('href="/orgs/top-org/"', content,
                     "Podium card must link to detail page")
    
    def test_table_rows_link_to_detail(self):
        """Table rows must link to detail pages."""
        response = self.client.get('/orgs/')
        content = response.content.decode('utf-8')
        
        # Check that table contains detail links for all orgs
        self.assertIn('href="/orgs/second-org/"', content)
        self.assertIn('href="/orgs/third-org/"', content)


class TestOrganizationDetailPageAccess(TestCase):
    """Test that detail page is accessible and works correctly."""
    
    def setUp(self):
        """Create test data."""
        self.ceo = User.objects.create_user(
            username='ceo',
            email='ceo@test.com',
            password='testpass123'
        )
        self.public_user = User.objects.create_user(
            username='viewer',
            email='viewer@test.com',
            password='testpass123'
        )
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.ceo
        )
        self.client = Client()
    
    def test_detail_page_loads_for_anonymous(self):
        """Detail page must be accessible to anonymous users."""
        response = self.client.get('/orgs/test-org/')
        self.assertEqual(response.status_code, 200)
    
    def test_detail_page_loads_for_public_user(self):
        """Detail page must be accessible to logged-in public users."""
        self.client.login(username='viewer', password='testpass123')
        response = self.client.get('/orgs/test-org/')
        self.assertEqual(response.status_code, 200)
    
    def test_detail_page_loads_for_ceo(self):
        """Detail page must be accessible to CEO."""
        self.client.login(username='ceo', password='testpass123')
        response = self.client.get('/orgs/test-org/')
        self.assertEqual(response.status_code, 200)
    
    def test_detail_page_returns_404_for_missing_org(self):
        """Detail page must return 404 for non-existent org."""
        response = self.client.get('/orgs/nonexistent/')
        self.assertEqual(response.status_code, 404)
    
    def test_detail_page_shows_hub_link_for_ceo(self):
        """Detail page must show 'Open Hub' button only for CEO."""
        self.client.login(username='ceo', password='testpass123')
        response = self.client.get('/orgs/test-org/')
        
        # Check that hub link is present
        self.assertContains(response, 'Open Hub')
        self.assertContains(response, '/orgs/test-org/hub/')
    
    def test_detail_page_hides_hub_link_for_public_user(self):
        """Detail page must NOT show 'Open Hub' button for public users."""
        self.client.login(username='viewer', password='testpass123')
        response = self.client.get('/orgs/test-org/')
        
        # Check that hub link is NOT present
        self.assertNotContains(response, 'Open Hub')


@pytest.mark.django_db
class TestNavigationIntegrationFlow:
    """Integration test for full navigation flow."""
    
    def test_directory_to_detail_to_hub_flow(self):
        """Test complete navigation path: Directory → Detail → Hub."""
        # Setup
        ceo = User.objects.create_user(
            username='ceo',
            email='ceo@test.com',
            password='testpass123'
        )
        org = Organization.objects.create(
            name='Flow Test Org',
            slug='flow-test',
            ceo=ceo
        )
        client = Client()
        
        # Step 1: GET directory
        response = client.get('/orgs/')
        assert response.status_code == 200
        assert b'/orgs/flow-test/' in response.content
        
        # Step 2: GET detail page
        response = client.get('/orgs/flow-test/')
        assert response.status_code == 200
        assert b'Flow Test Org' in response.content
        
        # Step 3: Verify hub link NOT visible to anonymous
        assert b'Open Hub' not in response.content
        
        # Step 4: Login as CEO
        client.login(username='ceo', password='testpass123')
        
        # Step 5: GET detail page again (now logged in)
        response = client.get('/orgs/flow-test/')
        assert response.status_code == 200
        assert b'Open Hub' in response.content
        
        # Step 6: GET hub page
        response = client.get('/orgs/flow-test/hub/')
        assert response.status_code == 200
        # Hub page should load (exact content depends on hub implementation)


class TestURLPatternOrdering(TestCase):
    """Test that URL patterns are ordered correctly to avoid conflicts."""
    
    def test_detail_pattern_does_not_catch_hub(self):
        """Detail pattern must not incorrectly match hub URLs."""
        # Try to access hub
        ceo = User.objects.create_user(username='ceo', email='ceo@test.com', password='testpass123')
        org = Organization.objects.create(name='Test', slug='test', ceo=ceo)
        
        client = Client()
        client.login(username='ceo', password='testpass123')
        
        # Hub URL should resolve to hub view, not detail view with slug='hub'
        response = client.get('/orgs/test/hub/')
        
        # If it resolved correctly, we should NOT get a 404
        # (Hub page exists and should load for CEO)
        self.assertNotEqual(response.status_code, 404,
                           "Hub URL incorrectly matched detail pattern")
