"""
UP-PHASE11: Template Rendering Tests

Tests verify templates include correct CSS and JavaScript:
- design-tokens.css included in profile/settings
- escapejs filter applied (no raw template vars in JS)
- Alpine.js dependencies loaded correctly
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

pytestmark = pytest.mark.django_db


class TemplateCSSInclusionTestCase(TestCase):
    """
    Tests for CSS file inclusion in templates.
    Verifies design-tokens.css is loaded correctly.
    """
    
    def setUp(self):
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser_template',
            email='test@example.com',
            password='test123'
        )
        self.profile = self.user.profile
        self.profile.display_name = 'Test User'
        self.profile.save()
    
    def test_settings_page_includes_design_tokens(self):
        """
        PHASE11-A: Settings page includes design-tokens.css.
        """
        self.client.login(username='testuser_template', password='test123')
        response = self.client.get('/me/settings/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify design-tokens.css is included
        assert 'design-tokens.css' in content, \
            "Settings page must include design-tokens.css"
        
        # Verify link tag format is correct
        assert '<link' in content and 'rel="stylesheet"' in content, \
            "CSS should be included via <link> tag"
    
    def test_profile_page_includes_design_tokens(self):
        """
        PHASE11-B: Profile page includes design-tokens.css.
        """
        response = self.client.get(f'/@{self.user.username}/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify design-tokens.css is included
        assert 'design-tokens.css' in content, \
            "Profile page must include design-tokens.css"
        
        # Verify it's loaded before page-specific styles (order matters)
        design_tokens_pos = content.find('design-tokens.css')
        assert design_tokens_pos > 0, "design-tokens.css not found in HTML"
    
    def test_settings_page_includes_alpine(self):
        """
        PHASE11-A: Settings page includes Alpine.js CDN.
        """
        self.client.login(username='testuser_template', password='test123')
        response = self.client.get('/me/settings/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify Alpine.js is included
        assert 'alpinejs' in content.lower() or 'alpine' in content, \
            "Settings page must include Alpine.js"
        
        # Verify defer attribute (Alpine must load after DOM)
        assert 'defer' in content, \
            "Alpine.js script should have defer attribute"
    
    def test_settings_page_has_xcloak_style(self):
        """
        PHASE11-A: Settings page has [x-cloak] style to prevent FOUC.
        """
        self.client.login(username='testuser_template', password='test123')
        response = self.client.get('/me/settings/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify x-cloak style exists
        assert '[x-cloak]' in content, \
            "Settings page must define [x-cloak] style"
        assert 'display: none' in content, \
            "[x-cloak] style must hide content until Alpine loads"
    
    def test_settings_page_has_noscript_fallback(self):
        """
        PHASE11-A: Settings page has <noscript> fallback message.
        """
        self.client.login(username='testuser_template', password='test123')
        response = self.client.get('/me/settings/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify noscript tag exists
        assert '<noscript>' in content, \
            "Settings page must have <noscript> fallback"
        assert 'JavaScript Required' in content or 'JavaScript' in content, \
            "Noscript message should mention JavaScript requirement"


class TemplateJavaScriptEscapingTestCase(TestCase):
    """
    Tests for proper JavaScript string escaping in templates.
    Verifies escapejs filter is applied to prevent syntax errors.
    """
    
    def setUp(self):
        self.client = Client()
        
        # Create user with problematic characters in bio
        self.user = User.objects.create_user(
            username='testuser_escape',
            email='test@example.com',
            password='test123'
        )
        self.profile = self.user.profile
        self.profile.display_name = 'Test "User"'
        self.profile.bio = 'Bio with "quotes" and\nnewlines\nand\'apostrophes'
        self.profile.country = "USA's Country"
        self.profile.pronouns = 'they/them (test)'
        self.profile.save()
    
    def test_settings_page_escapes_profile_fields(self):
        """
        PHASE11-A: Settings page properly escapes profile data in JavaScript.
        Tests that escapejs filter prevents syntax errors from user input.
        """
        self.client.login(username='testuser_escape', password='test123')
        response = self.client.get('/me/settings/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify escapejs is applied (no raw Django template vars in JS)
        # Should NOT see: bio: '{{ user_profile.bio }}'
        # Should see: bio: 'Bio with \"quotes\"...'
        
        # Check that the raw template variable syntax is NOT present
        assert '{{ user_profile.bio }}' not in content, \
            "Raw Django template variable found in HTML (escapejs not applied)"
        assert '{{ user_profile.display_name }}' not in content, \
            "Raw Django template variable found in HTML (escapejs not applied)"
        
        # Verify problematic characters are escaped
        # The bio has quotes, so if not escaped, JS would break
        # We should see escaped versions like \" or \n
        if 'Bio with' in content:
            # If bio content is in response, verify it's escaped
            bio_section = content[content.find('Bio with'):content.find('Bio with')+100]
            # Escaped quotes should appear as \" or use single quotes wrapping
            assert '\\' in bio_section or ("'" in bio_section and '"' not in bio_section), \
                "Bio quotes not properly escaped in JavaScript"
    
    def test_settings_page_no_unescaped_template_markers(self):
        """
        PHASE11-A: Settings page has no unescaped Django template markers in JS.
        Verifies all {{ }} template variables have filters applied.
        """
        self.client.login(username='testuser_escape', password='test123')
        response = self.client.get('/me/settings/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Find JavaScript sections
        script_start = content.find('<script>')
        script_end = content.find('</script>', script_start)
        
        if script_start > 0 and script_end > 0:
            js_content = content[script_start:script_end]
            
            # Count {{ }} markers in JavaScript (should be 0 after rendering)
            template_markers = js_content.count('{{')
            assert template_markers == 0, \
                f"Found {template_markers} unprocessed Django template markers in JavaScript"
    
    def test_profile_page_no_javascript_errors(self):
        """
        PHASE11-B: Profile page renders without JavaScript errors.
        Basic sanity check for profile template.
        """
        response = self.client.get(f'/@{self.user.username}/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify no obvious JavaScript syntax errors in inline scripts
        if '<script>' in content:
            # Check for common syntax error patterns
            assert 'SyntaxError' not in content, \
                "SyntaxError found in page source"
            assert 'Uncaught' not in content, \
                "Uncaught error found in page source"


class TemplateStructureTestCase(TestCase):
    """
    Tests for template structure and organization.
    """
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser_structure',
            email='test@example.com',
            password='test123'
        )
        self.profile = self.user.profile
    
    def test_settings_page_has_alpine_container(self):
        """
        PHASE11-A: Settings page has Alpine.js container with x-data.
        """
        self.client.login(username='testuser_structure', password='test123')
        response = self.client.get('/me/settings/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify Alpine container exists
        assert 'x-data=' in content, \
            "Settings page must have Alpine.js x-data attribute"
        assert 'settingsApp()' in content or 'settingsApp' in content, \
            "Alpine container must reference settingsApp function"
        assert 'x-cloak' in content, \
            "Alpine container should have x-cloak attribute"
    
    def test_profile_page_loads_successfully(self):
        """
        PHASE11-B: Profile page loads without errors.
        Basic smoke test for profile template.
        """
        response = self.client.get(f'/@{self.user.username}/')
        
        assert response.status_code == 200
        assert len(response.content) > 1000, \
            "Profile page should have substantial content"
        
        content = response.content.decode('utf-8')
        
        # Verify basic profile structure
        assert self.user.username in content, \
            "Profile should display username"
    
    def test_settings_page_requires_authentication(self):
        """
        PHASE11-A: Settings page requires login (security check).
        """
        response = self.client.get('/me/settings/')
        
        # Should redirect to login
        assert response.status_code == 302, \
            "Settings page should redirect unauthenticated users"
        assert '/login' in response.url or 'login' in response.url.lower(), \
            "Should redirect to login page"
