"""
UP-UI-FIX-03: Template Rendering Regression Tests

Tests that all V2 profile templates compile and render without TemplateSyntaxError.
These tests prevent production-blocking template errors from being deployed.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile

User = get_user_model()


class TemplateRenderingRegressionTestCase(TestCase):
    """
    Regression tests for template compilation and rendering.
    
    These tests ensure templates compile without syntax errors.
    They do NOT test business logic or data correctness.
    """
    
    def setUp(self):
        """Create test user and profile"""
        self.client = Client()
        
        # Create user without triggering PublicIDCounter
        self.user = User.objects.create_user(
            username='templatetest',
            email='template@example.com',
            password='testpass123'
        )
        
        # Get or create profile (should exist from signal)
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={'display_name': 'Template Test User'}
        )
    
    def test_public_profile_renders_without_syntax_error(self):
        """Test /@<username>/ renders (no TemplateSyntaxError)"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'templatetest'})
        
        # Should return 200 and not raise TemplateSyntaxError
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200, 
                        "Public profile should render successfully")
        self.assertIn(b'templatetest', response.content,
                     "Profile should contain username")
    
    def test_settings_page_renders_without_syntax_error(self):
        """Test /me/settings/ renders (no TemplateSyntaxError)"""
        self.client.login(username='templatetest', password='testpass123')
        url = reverse('user_profile:profile_settings_v2')
        
        # Should return 200 and not raise TemplateSyntaxError
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200,
                        "Settings page should render successfully")
        self.assertIn(b'Profile Settings', response.content,
                     "Settings page should contain header")
    
    def test_privacy_page_renders_without_syntax_error(self):
        """Test /me/privacy/ renders (no TemplateSyntaxError)"""
        self.client.login(username='templatetest', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        
        # Should return 200 and not raise TemplateSyntaxError
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200,
                        "Privacy page should render successfully")
        self.assertIn(b'Privacy Settings', response.content,
                     "Privacy page should contain header")
    
    def test_activity_page_renders_without_syntax_error(self):
        """Test /me/activity/ renders (no TemplateSyntaxError)"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'templatetest'})
        
        # Should return 200 and not raise TemplateSyntaxError
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200,
                        "Activity page should render successfully")
        self.assertIn(b'Activity Feed', response.content,
                     "Activity page should contain header")
    
    def test_public_profile_nonexistent_user_404(self):
        """Test /@nonexistent/ returns 404 (not TemplateSyntaxError)"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'nonexistent'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404,
                        "Nonexistent user should return 404")
    
    def test_settings_requires_authentication(self):
        """Test /me/settings/ redirects unauthenticated users"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        # Should redirect to login (302), not fail with template error
        self.assertEqual(response.status_code, 302,
                        "Settings page should redirect unauthenticated users")
    
    def test_privacy_requires_authentication(self):
        """Test /me/privacy/ redirects unauthenticated users"""
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        # Should redirect to login (302), not fail with template error
        self.assertEqual(response.status_code, 302,
                        "Privacy page should redirect unauthenticated users")


class TemplateBlockStructureTestCase(TestCase):
    """
    Tests for specific template block structure issues.
    
    These tests verify the fixes for:
    - Duplicate {% endblock %} tags
    - Mismatched {% if %}/{% endif %} pairs
    - Leftover legacy CSS after proper template end
    """
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='blocktest',
            email='block@example.com',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={'display_name': 'Block Test User'}
        )
    
    def test_public_profile_template_has_single_endblock(self):
        """Verify profile_public.html ends with single {% endblock %}"""
        from django.template import loader
        
        # This will raise TemplateSyntaxError if duplicate endblock exists
        template = loader.get_template('user_profile/v2/profile_public.html')
        
        self.assertIsNotNone(template, 
                            "Public profile template should compile")
    
    def test_privacy_template_has_single_endblock(self):
        """Verify profile_privacy.html ends with single {% endblock %}"""
        from django.template import loader
        
        # This will raise TemplateSyntaxError if duplicate endblock exists
        template = loader.get_template('user_profile/v2/profile_privacy.html')
        
        self.assertIsNotNone(template,
                            "Privacy template should compile")
    
    def test_settings_template_compiles(self):
        """Verify profile_settings.html compiles without errors"""
        from django.template import loader
        
        template = loader.get_template('user_profile/v2/profile_settings.html')
        
        self.assertIsNotNone(template,
                            "Settings template should compile")
    
    def test_activity_template_compiles(self):
        """Verify profile_activity.html compiles without errors"""
        from django.template import loader
        
        template = loader.get_template('user_profile/v2/profile_activity.html')
        
        self.assertIsNotNone(template,
                            "Activity template should compile")


class ProfilePublicPolishTestCase(TestCase):
    """
    UP-UI-POLISH-04: Tests for production-grade public profile features.
    
    Tests cover:
    - Owner vs non-owner views
    - Game passport sections render safely
    - Empty states display correctly
    - No NoReverseMatch errors
    """
    
    def setUp(self):
        """Create test users and game passports"""
        self.client = Client()
        
        # Create profile owner
        self.owner = User.objects.create_user(
            username='profileowner',
            email='owner@example.com',
            password='testpass123'
        )
        self.owner_profile, _ = UserProfile.objects.get_or_create(
            user=self.owner,
            defaults={'display_name': 'Profile Owner'}
        )
        
        # Create another user (viewer)
        self.viewer = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpass123'
        )
    
    def test_public_profile_owner_view_renders_200(self):
        """Test owner viewing their own profile returns 200"""
        self.client.login(username='profileowner', password='testpass123')
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'profileowner'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200,
                        "Owner should see their own profile")
        self.assertIn(b'Edit Profile', response.content,
                     "Owner should see Edit Profile button")
    
    def test_public_profile_non_owner_view_renders_200(self):
        """Test non-owner viewing public profile returns 200"""
        self.client.login(username='viewer', password='testpass123')
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'profileowner'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200,
                        "Non-owner should see public profile")
        self.assertIn(b'Follow', response.content,
                     "Non-owner should see Follow button")
        self.assertNotIn(b'Edit Profile', response.content,
                        "Non-owner should not see Edit Profile button")
    
    def test_public_profile_anonymous_view_renders_200(self):
        """Test anonymous user viewing public profile returns 200"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'profileowner'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200,
                        "Anonymous user should see public profile")
    
    def test_profile_with_no_passports_shows_empty_state(self):
        """Test profile without game passports shows friendly empty state"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'profileowner'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No Game Passports Yet', response.content,
                     "Should show empty state message")
    
    def test_profile_sections_all_present(self):
        """Test all required sections render in public profile"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'profileowner'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for section IDs
        self.assertIn(b'id="stats"', response.content,
                     "Stats section should be present")
        self.assertIn(b'id="passports"', response.content,
                     "Passports section should be present")
        self.assertIn(b'id="activity"', response.content,
                     "Activity section should be present")
        self.assertIn(b'id="about"', response.content,
                     "About section should be present")
    
    def test_profile_nav_urls_no_reverse_match_error(self):
        """Test navigation URLs compile without NoReverseMatch"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'profileowner'})
        
        # Should not raise NoReverseMatch
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that profile_settings_v2 URL is present (for owner)
        self.client.login(username='profileowner', password='testpass123')
        response = self.client.get(url)
        
        self.assertIn(b'/me/settings/', response.content,
                     "Settings URL should be rendered")
    
    def test_profile_sticky_nav_renders(self):
        """Test sticky navigation bar renders correctly"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'profileowner'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'sticky top-0', response.content,
                     "Sticky nav should be present")
        self.assertIn(b'#stats', response.content,
                     "Stats anchor link should be present")
        self.assertIn(b'#passports', response.content,
                     "Passports anchor link should be present")
    
    def test_profile_js_file_referenced(self):
        """Test profile_public.js is referenced in template"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'profileowner'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'profile_public.js', response.content,
                     "JavaScript file should be referenced")
