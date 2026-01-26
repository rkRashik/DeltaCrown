"""
Regression tests for safe file URL handling in templates.

Prevents crashes when accessing .url on empty ImageField/FileField.
"""

import os
import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.organizations.models.organization import Organization
from apps.organizations.templatetags.org_media import safe_file_url, safe_file_exists

User = get_user_model()


class TestSafeFileUrlFilter(TestCase):
    """Test the safe_file_url template filter."""
    
    def test_safe_file_url_with_none(self):
        """Test filter returns fallback when file_field is None."""
        fallback = 'https://example.com/default.png'
        result = safe_file_url(None, fallback)
        self.assertEqual(result, fallback)
    
    def test_safe_file_url_with_empty_string_fallback(self):
        """Test filter returns empty string when no fallback provided."""
        result = safe_file_url(None)
        self.assertEqual(result, '')
    
    def test_safe_file_url_with_file(self):
        """Test filter returns file URL when file exists."""
        # Create user with avatar
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        # Create a simple uploaded file
        avatar_file = SimpleUploadedFile(
            "test_avatar.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        user.avatar = avatar_file
        user.save()
        
        # Get URL
        result = safe_file_url(user.avatar, 'https://fallback.com/image.png')
        
        # Should return actual file URL, not fallback
        self.assertIn('test_avatar', result)
        self.assertNotIn('fallback.com', result)
        
        # Cleanup
        if user.avatar:
            user.avatar.delete()
    
    def test_safe_file_url_with_empty_field(self):
        """Test filter returns fallback when field exists but is empty."""
        user = User.objects.create_user(
            username='testuser2',
            email='test2@test.com',
            password='testpass123'
        )
        # User created without avatar - field exists but is empty
        
        fallback = 'https://example.com/default.png'
        result = safe_file_url(user.avatar, fallback)
        
        self.assertEqual(result, fallback)


class TestSafeFileExistsFilter(TestCase):
    """Test the safe_file_exists template filter."""
    
    def test_safe_file_exists_with_none(self):
        """Test filter returns False when file_field is None."""
        result = safe_file_exists(None)
        self.assertFalse(result)
    
    def test_safe_file_exists_with_empty_field(self):
        """Test filter returns False when field is empty."""
        user = User.objects.create_user(
            username='testuser3',
            email='test3@test.com',
            password='testpass123'
        )
        
        result = safe_file_exists(user.avatar)
        self.assertFalse(result)
    
    def test_safe_file_exists_with_file(self):
        """Test filter returns True when file exists."""
        user = User.objects.create_user(
            username='testuser4',
            email='test4@test.com',
            password='testpass123'
        )
        
        avatar_file = SimpleUploadedFile(
            "test_avatar2.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        user.avatar = avatar_file
        user.save()
        
        result = safe_file_exists(user.avatar)
        self.assertTrue(result)
        
        # Cleanup
        if user.avatar:
            user.avatar.delete()


@pytest.mark.skipif(
    os.getenv('DB_TEST_BLOCKED') == '1',
    reason="Database permissions not available in test environment"
)
class TestOrgDetailTemplateNocrash(TestCase):
    """Test that org_detail.html renders without crash when files are missing."""
    
    def setUp(self):
        """Create test organization without logo/banner."""
        self.user = User.objects.create_user(
            username='ceo',
            email='ceo@test.com',
            password='testpass123'
        )
        # User has no avatar - should not crash
        
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.user,
            is_verified=True
        )
        # Organization has no logo/banner - should not crash
    
    def test_template_renders_without_ceo_avatar(self):
        """Test template renders when CEO has no avatar."""
        template_str = """
        {% load org_media %}
        <img src="{{ user.avatar|safe_file_url:'https://default.com/avatar.png' }}">
        """
        template = Template(template_str)
        context = Context({'user': self.user})
        
        # Should not crash
        rendered = template.render(context)
        
        # Should use fallback
        self.assertIn('default.com', rendered)
    
    def test_template_renders_without_org_logo(self):
        """Test template renders when organization has no logo."""
        template_str = """
        {% load org_media %}
        {% if org.logo %}
        <img src="{{ org.logo|safe_file_url }}">
        {% else %}
        <span>No Logo</span>
        {% endif %}
        """
        template = Template(template_str)
        context = Context({'org': self.org})
        
        # Should not crash
        rendered = template.render(context)
        
        # Should show "No Logo" since org.logo is empty
        self.assertIn('No Logo', rendered)
    
    def test_template_renders_without_org_banner(self):
        """Test template renders when organization has no banner."""
        template_str = """
        {% load org_media %}
        {% if org.banner %}
        <img src="{{ org.banner|safe_file_url }}">
        {% endif %}
        """
        template = Template(template_str)
        context = Context({'org': self.org})
        
        # Should not crash and render nothing
        rendered = template.render(context)
        
        # Should be minimal whitespace only
        self.assertEqual(rendered.strip(), '')


class TestTemplateUnsafePatternScan(TestCase):
    """Regression test: Scan templates for unsafe .url patterns."""
    
    def test_org_detail_no_unsafe_url_access(self):
        """Verify org_detail.html does not contain unsafe .url access."""
        import os
        from django.conf import settings
        
        template_path = os.path.join(
            settings.BASE_DIR,
            'templates',
            'organizations',
            'org',
            'org_detail.html'
        )
        
        if not os.path.exists(template_path):
            self.skipTest(f"Template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for unsafe patterns
        unsafe_patterns = [
            '.avatar.url',
            '.logo.url',
            '.banner.url',
        ]
        
        for pattern in unsafe_patterns:
            if pattern in content:
                # Check if it's using safe_file_url filter
                # Pattern should be: field|safe_file_url
                # Not: field.url
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if pattern in line and 'safe_file_url' not in line:
                        self.fail(
                            f"Line {i}: Found unsafe pattern '{pattern}' without safe_file_url filter\n"
                            f"Use: {{{{ field|safe_file_url }}}} instead of {{{{ field.url }}}}\n"
                            f"Line content: {line.strip()}"
                        )
    
    def test_org_hub_no_unsafe_url_access(self):
        """Verify org_hub.html does not contain unsafe .url access."""
        import os
        from django.conf import settings
        
        template_path = os.path.join(
            settings.BASE_DIR,
            'templates',
            'organizations',
            'org',
            'org_hub.html'
        )
        
        if not os.path.exists(template_path):
            self.skipTest(f"Template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for unsafe patterns
        unsafe_patterns = [
            '.avatar.url',
            '.logo.url',
            '.banner.url',
        ]
        
        for pattern in unsafe_patterns:
            if pattern in content:
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if pattern in line and 'safe_file_url' not in line:
                        self.fail(
                            f"Line {i}: Found unsafe pattern '{pattern}' without safe_file_url filter\n"
                            f"Use: {{{{ field|safe_file_url }}}} instead of {{{{ field.url }}}}\n"
                            f"Line content: {line.strip()}"
                        )
