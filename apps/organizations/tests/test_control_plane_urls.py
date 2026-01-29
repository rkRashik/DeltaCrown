"""
Control Plane routing and template contract tests.
Pure tests without DB dependencies or legacy module imports.
"""

import pytest
from pathlib import Path


class TestControlPlaneURLRouting:
    """URL routing tests that don't trigger teams app imports."""
    
    @pytest.mark.skip(reason="Requires DB - teams app imports Game model at module load, can't avoid without fixing teams/views/public.py")
    def test_url_reverse_works(self):
        """Test URL reverse resolves correctly."""
        # Import only when needed, not at module level
        from django.urls import reverse
        
        url = reverse('organizations:org_control_plane', kwargs={'org_slug': 'test-org'})
        assert url == '/orgs/test-org/control-plane/'
    
    @pytest.mark.skip(reason="Requires DB - teams app imports Game model at module load, can't avoid without fixing teams/views/public.py")
    def test_url_pattern_resolves(self):
        """Test URL pattern resolves to correct view."""
        from django.urls import resolve
        
        resolver = resolve('/orgs/test-org/control-plane/')
        assert resolver.view_name == 'organizations:org_control_plane'
        assert resolver.kwargs == {'org_slug': 'test-org'}
    
    def test_view_import_works(self):
        """Test view function can be imported."""
        from apps.organizations.views.org import org_control_plane
        
        assert callable(org_control_plane)
        assert org_control_plane.__name__ == 'org_control_plane'


class TestControlPlaneTemplate:
    """Template existence and content contract tests."""
    
    def test_template_exists(self):
        """Test template file exists at expected path."""
        template_path = Path(__file__).parent.parent.parent.parent / 'templates' / 'organizations' / 'org' / 'org_control_plane.html'
        assert template_path.exists(), f"Template not found: {template_path}"
        assert template_path.stat().st_size > 100000, "Template file too small"
    
    def test_template_has_unique_markers_from_raw(self):
        """Test template contains unique strings that are definitely in raw template."""
        template_path = Path(__file__).parent.parent.parent.parent / 'templates' / 'organizations' / 'org' / 'org_control_plane.html'
        content = template_path.read_text()
        
        # These strings are from the raw template header section
        assert 'Organization <span class="text-delta-gold">Sovereignty</span>' in content
        assert 'Enterprise Systems' in content
        assert 'Org OS' in content
        
        # Verify all 13 tabs exist (exact names from raw template)
        tabs = [
            'General Identity',
            'Brand Assets',
            'Squad Control',
            'Recruitment & Growth',
            'Command Staff',
            'Empire Treasury',
            'Partners & Sponsors',
            'Media & Streaming',
            'Notification Matrix',
            'Governance & Security',
            'Verification',
            'Audit & Logs',
            'Terminal Actions',
        ]
        for tab in tabs:
            assert tab in content, f"Missing tab: {tab}"
    
    def test_template_uses_django_blocks(self):
        """Test template properly uses Django block structure."""
        template_path = Path(__file__).parent.parent.parent.parent / 'templates' / 'organizations' / 'org' / 'org_control_plane.html'
        content = template_path.read_text()
        
        # Check for required Django template tags
        assert '{% extends "base.html" %}' in content
        assert '{% load static %}' in content
        assert '{% block content %}' in content
        assert '{% block extra_css %}' in content
        assert '{% block extra_js %}' in content
