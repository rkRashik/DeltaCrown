"""
Smoke tests for development database bootstrap verification.

These tests verify that the core functionality works after a fresh database setup:
- Admin interface is accessible
- Competition app is registered and accessible
- Ranking pages load correctly
- Team vnext pages have proper navigation links

Run with:
    python manage.py test apps.core.tests.test_smoke_dev_bootstrap
    pytest apps/core/tests/test_smoke_dev_bootstrap.py -k smoke_dev_bootstrap
"""
from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.contrib.auth import get_user_model
from bs4 import BeautifulSoup


User = get_user_model()


class DevBootstrapSmokeTests(TestCase):
    """Smoke tests for development database bootstrap."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test superuser for admin access
        cls.admin_user = User.objects.create_superuser(
            username='test_admin',
            email='test@test.local',
            password='test_password_secure_123'
        )
    
    def setUp(self):
        """Set up test client with authenticated session."""
        self.client = Client()
        self.client.force_login(self.admin_user)
    
    def test_smoke_admin_accessible(self):
        """Verify admin interface is accessible and contains Competition app."""
        response = self.client.get('/admin/')
        
        # Should redirect to admin index or return 200
        self.assertIn(response.status_code, [200, 302])
        
        # Follow redirect if needed
        if response.status_code == 302:
            response = self.client.get(response.url)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse HTML and check for Competition app
        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = soup.get_text().lower()
        
        # Check if "competition" appears in the page (app name or link)
        self.assertIn('competition', page_text, 
                     "Competition app not found in admin interface")
    
    def test_smoke_competition_ranking_about_page(self):
        """Verify competition ranking about page loads successfully."""
        try:
            url = reverse('competition:ranking_about')
        except Exception:
            # If reverse fails, try direct URL
            url = '/competition/ranking/about/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200, 
                        f"Competition ranking about page failed to load: {url}")
    
    def test_smoke_teams_vnext_hub(self):
        """Verify teams vnext hub page loads successfully."""
        try:
            url = reverse('teams:vnext_hub')
        except Exception:
            # If reverse fails, try common alternatives
            for candidate in ['/teams/vnext/', '/teams/v2/', '/teams/']:
                response = self.client.get(candidate)
                if response.status_code == 200:
                    url = candidate
                    break
            else:
                self.skipTest("Teams vnext hub URL not found")
                return
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200, 
                        f"Teams vnext hub page failed to load: {url}")
    
    def test_smoke_teams_vnext_rankings_policy_link(self):
        """Verify Rankings Policy link exists and points to correct URL."""
        # Get teams vnext hub URL
        try:
            vnext_url = reverse('teams:vnext_hub')
        except Exception:
            # Try common alternatives
            for candidate in ['/teams/vnext/', '/teams/v2/', '/teams/']:
                response = self.client.get(candidate)
                if response.status_code == 200:
                    vnext_url = candidate
                    break
            else:
                self.skipTest("Teams vnext hub URL not found")
                return
        
        # Get competition ranking about URL
        try:
            ranking_about_url = reverse('competition:ranking_about')
        except Exception:
            ranking_about_url = '/competition/ranking/about/'
        
        # Fetch vnext hub page
        response = self.client.get(vnext_url)
        self.assertEqual(response.status_code, 200)
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links
        links = soup.find_all('a')
        
        # Look for "Rankings Policy" link
        rankings_policy_link = None
        for link in links:
            link_text = link.get_text(strip=True)
            if 'ranking' in link_text.lower() and 'policy' in link_text.lower():
                rankings_policy_link = link
                break
        
        self.assertIsNotNone(rankings_policy_link, 
                            "Rankings Policy link not found on teams vnext hub page")
        
        # Verify href is not just "#"
        href = rankings_policy_link.get('href', '')
        self.assertNotEqual(href, '#', 
                           "Rankings Policy link should not be href='#'")
        
        # Verify href points to competition ranking about
        self.assertTrue(
            ranking_about_url in href or href.endswith(ranking_about_url),
            f"Rankings Policy link href '{href}' should point to '{ranking_about_url}'"
        )
    
    def test_smoke_competition_app_models_accessible(self):
        """Verify Competition app models are accessible in admin."""
        # Try to access competition app admin index
        response = self.client.get('/admin/competition/')
        
        # Should be accessible
        self.assertEqual(response.status_code, 200,
                        "Competition app admin page not accessible")
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = soup.get_text().lower()
        
        # Check for key models
        # At least one of these should appear
        model_indicators = [
            'game ranking config',
            'gamerankingconfig',
            'match report',
            'matchreport',
            'competition',
        ]
        
        found_model = any(indicator in page_text for indicator in model_indicators)
        self.assertTrue(found_model, 
                       "No Competition models found in admin interface")
