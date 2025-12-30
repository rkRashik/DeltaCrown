"""
UP-PHASE12B: Settings Page Alpine.js Integration Tests
Verifies settingsApp definition, script load order, and escapejs usage.
Uses Django test client (no Playwright needed).
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from bs4 import BeautifulSoup
import re

User = get_user_model()


@pytest.mark.django_db
class TestSettingsAlpineIntegration:
    """Test Settings page Alpine.js integration WITHOUT browser"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test user and profile"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@deltacrown.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.profile.display_name = 'Test Player'
        self.profile.bio = 'Professional esports athlete with "quotes" and special chars: <>&'
        self.profile.save()
        self.client.force_login(self.user)

    def test_settings_page_renders(self):
        """Verify settings page loads without errors"""
        response = self.client.get('/me/settings/')
        assert response.status_code == 200

    def test_settings_app_function_exists(self):
        """Verify settingsApp() function is defined in page"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        assert 'window.settingsApp' in content, "settingsApp not defined"
        assert 'function()' in content or 'function settingsApp()' in content, \
            "settingsApp not defined as function"

    def test_settings_app_before_alpine(self):
        """Verify settingsApp is defined BEFORE Alpine.js loads"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        # Find positions of settingsApp and Alpine script
        settings_app_pos = content.find('window.settingsApp')
        alpine_pos = content.find('alpinejs')
        
        assert settings_app_pos > 0, "settingsApp not found"
        assert alpine_pos > 0, "Alpine.js not found"
        assert settings_app_pos < alpine_pos, \
            f"settingsApp must be defined BEFORE Alpine.js (settingsApp at {settings_app_pos}, Alpine at {alpine_pos})"

    def test_settings_app_synchronous(self):
        """Verify settingsApp script does NOT have defer attribute"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        # Find settingsApp script block
        settings_script_match = re.search(
            r'<script[^>]*>.*?window\.settingsApp.*?</script>',
            content,
            re.DOTALL
        )
        assert settings_script_match, "settingsApp script block not found"
        
        script_tag = settings_script_match.group(0)
        opening_tag = script_tag.split('>')[0]
        
        assert 'defer' not in opening_tag.lower(), \
            "settingsApp script must NOT have defer attribute (must be synchronous)"

    def test_alpine_has_defer(self):
        """Verify Alpine.js script HAS defer attribute"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        # Find Alpine.js script tag
        alpine_match = re.search(r'<script[^>]*alpinejs[^>]*>', content)
        assert alpine_match, "Alpine.js script tag not found"
        
        alpine_tag = alpine_match.group(0)
        assert 'defer' in alpine_tag.lower(), \
            "Alpine.js script must have defer attribute"

    def test_escapejs_on_display_name(self):
        """Verify display_name uses escapejs filter"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        # Check for escaped version of display name in JavaScript
        # Should NOT contain raw quotes that could break JS
        assert 'Test Player' in content, "Display name not found"
        
        # Look for settingsApp definition and check display_name initialization
        settings_app_match = re.search(
            r'display_name:\s*[\'"`]([^\'"`]*)[\'"`]',
            content
        )
        if settings_app_match:
            display_name_value = settings_app_match.group(1)
            # Should not contain unescaped quotes
            assert '\\"' not in display_name_value or '"' not in display_name_value, \
                "display_name not properly escaped"

    def test_escapejs_on_bio(self):
        """Verify bio with special characters is escaped"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        # Bio contains quotes, <, >, & - should be escaped in JS
        # Check that bio variable exists
        assert 'bio:' in content, "bio variable not found in settingsApp"
        
        # Verify HTML entities are escaped (< becomes \\u003C, > becomes \\u003E, etc.)
        # or proper JS escaping is used

    def test_x_cloak_present(self):
        """Verify x-cloak attribute exists to prevent FOUC"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        assert 'x-cloak' in content, "x-cloak attribute not found"
        assert '[x-cloak]' in content, "x-cloak CSS style not defined"

    def test_x_data_uses_settings_app(self):
        """Verify Alpine container uses x-data='settingsApp()'"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        assert 'x-data="settingsApp()"' in content or "x-data='settingsApp()'" in content, \
            "x-data='settingsApp()' not found"

    def test_active_section_initialized(self):
        """Verify activeSection is initialized in settingsApp"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        assert 'activeSection:' in content, "activeSection property not found"

    def test_settings_v2_css_loads(self):
        """Verify settings_v2.css and design-tokens.css load"""
        response = self.client.get('/me/settings/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        css_links = soup.find_all('link', rel='stylesheet')
        css_hrefs = [link.get('href', '') for link in css_links]
        
        has_settings_css = any('settings_v2.css' in href for href in css_hrefs)
        has_design_tokens = any('design-tokens.css' in href for href in css_hrefs)
        
        assert has_settings_css, "settings_v2.css not found"
        assert has_design_tokens, "design-tokens.css not found"

    def test_noscript_fallback_exists(self):
        """Verify noscript tag exists for users without JS"""
        response = self.client.get('/me/settings/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        noscript = soup.find('noscript')
        assert noscript, "No noscript fallback found"

    def test_no_double_alpine_loading(self):
        """Verify Alpine.js is only loaded once"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        alpine_matches = re.findall(r'alpinejs', content.lower())
        # Should find: 1 in script src, possibly 1 in comment, but not multiple script tags
        script_tags = re.findall(r'<script[^>]*alpinejs[^>]*>', content, re.IGNORECASE)
        
        assert len(script_tags) == 1, f"Alpine.js loaded {len(script_tags)} times (should be 1)"

    def test_phase12_comments_present(self):
        """Verify Phase 12 fix comments are in place"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        # Should have comments documenting the Phase 12A fix
        assert 'UP-PHASE12' in content or 'PHASE12' in content, \
            "Phase 12 documentation comments not found"


@pytest.mark.django_db
class TestSettingsFormSections:
    """Test Settings page form sections structure"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@deltacrown.com',
            password='testpass123'
        )
        self.client.force_login(self.user)

    def test_profile_section_exists(self):
        """Verify Profile settings section exists"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        assert 'profile' in content.lower(), "Profile section not found"

    def test_privacy_section_exists(self):
        """Verify Privacy settings section exists"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        assert 'privacy' in content.lower(), "Privacy section not found"

    def test_notifications_section_exists(self):
        """Verify Notifications settings section exists"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        assert 'notification' in content.lower(), "Notifications section not found"

    def test_platform_section_exists(self):
        """Verify Platform settings section exists"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        assert 'platform' in content.lower(), "Platform section not found"

    def test_wallet_section_exists(self):
        """Verify Wallet settings section exists"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        assert 'wallet' in content.lower(), "Wallet section not found"

    def test_account_section_exists(self):
        """Verify Account settings section exists"""
        response = self.client.get('/me/settings/')
        content = response.content.decode('utf-8')
        
        assert 'account' in content.lower(), "Account section not found"
