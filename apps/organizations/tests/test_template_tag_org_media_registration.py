"""
Tests for org_media template tag library registration and discovery.

Ensures Django can properly discover and load the template tag library.
"""

from django.test import TestCase
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError

from apps.organizations.templatetags.org_media import register


class TestOrgMediaTagLibraryRegistration(TestCase):
    """Test that org_media template tag library is registered and discoverable."""
    
    def test_org_media_library_can_be_loaded(self):
        """Verify Django can load the org_media template tag library."""
        try:
            template = Template("{% load org_media %}loaded")
            rendered = template.render(Context({}))
            self.assertEqual(rendered.strip(), "loaded")
        except Exception as e:
            self.fail(f"org_media template library not registered: {e}")
    
    def test_safe_file_url_filter_exists(self):
        """Verify safe_file_url filter is registered in org_media library."""
        self.assertIn('safe_file_url', register.filters,
                     "safe_file_url filter not found in org_media library")
    
    def test_safe_file_exists_filter_exists(self):
        """Verify safe_file_exists filter is registered in org_media library."""
        self.assertIn('safe_file_exists', register.filters,
                     "safe_file_exists filter not found in org_media library")
    
    def test_template_can_load_org_media(self):
        """Verify templates can successfully load {% load org_media %}."""
        template_str = "{% load org_media %}{{ test }}"
        
        # Should not raise TemplateSyntaxError
        try:
            template = Template(template_str)
            context = Context({'test': 'success'})
            rendered = template.render(context)
            self.assertEqual(rendered.strip(), 'success')
        except TemplateSyntaxError as e:
            self.fail(f"Template failed to load org_media: {e}")
    
    def test_template_can_use_safe_file_url_filter(self):
        """Verify templates can use the safe_file_url filter."""
        template_str = "{% load org_media %}{{ field|safe_file_url:'fallback.png' }}"
        
        template = Template(template_str)
        context = Context({'field': None})
        rendered = template.render(context)
        
        # Should render fallback when field is None
        self.assertEqual(rendered.strip(), 'fallback.png')
    
    def test_organizations_app_is_properly_configured(self):
        """Verify organizations app is in INSTALLED_APPS with proper config."""
        from django.conf import settings
        
        # Check if app is installed
        self.assertIn('apps.organizations.apps.OrganizationsConfig', settings.INSTALLED_APPS,
                     "apps.organizations.apps.OrganizationsConfig not in INSTALLED_APPS")
