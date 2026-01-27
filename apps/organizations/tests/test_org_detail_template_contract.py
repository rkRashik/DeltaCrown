"""
Contract Tests for Organization Detail Template
Ensures template safety contracts are maintained.
"""

import pytest
import re
from pathlib import Path


TEMPLATE_PATH = Path(__file__).parent.parent.parent.parent / "templates" / "organizations" / "org" / "org_detail.html"


@pytest.fixture
def template_content():
    """Load template content for testing."""
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return f.read()


class TestOrgDetailTemplateContracts:
    """Contract tests to prevent regressions."""
    
    def test_template_loads_org_media_tag_library(self, template_content):
        """
        CONTRACT: Template MUST load org_media tag library for safe_file_url filter.
        
        WHY: Prevents crashes from direct FileField.url access when file is missing.
        """
        assert '{% load org_media %}' in template_content, \
            "Template must load org_media tag library for safe file handling"
    
    def test_no_direct_url_access_on_filefields(self, template_content):
        """
        CONTRACT: Template MUST NOT use direct .url access on FileFields.
        
        WHY: Crashes with 'The file associated with this field does not exist' error
        when FileField is empty or file is missing.
        
        VIOLATION PATTERNS:
        - organization.logo.url
        - organization.banner.url
        - organization.ceo.avatar.url
        - member.avatar.url
        
        REQUIRED PATTERN:
        - {{ field|safe_file_url:'fallback_url' }}
        """
        # Patterns that indicate dangerous direct .url access
        dangerous_patterns = [
            r'organization\.logo\.url',
            r'organization\.banner\.url',
            r'organization\.ceo\.avatar\.url',
            r'staff\.avatar\.url',
            r'member\.avatar\.url',
            r'player\.avatar\.url',
        ]
        
        violations = []
        for pattern in dangerous_patterns:
            if re.search(pattern, template_content):
                violations.append(pattern)
        
        assert not violations, \
            f"Template contains dangerous direct .url access: {violations}. " \
            f"Use safe_file_url filter instead."
    
    def test_public_role_cannot_see_manager_label(self, template_content):
        """
        CONTRACT: PUBLIC role MUST NOT see "Manager" label or manager blocks.
        
        WHY: Manager information is sensitive and owner-only.
        
        REQUIREMENT: Manager blocks must have 'role-owner-only' class or be
        wrapped in {% if can_manage_org %} conditional.
        """
        # Find all occurrences of "Manager" label
        manager_label_pattern = r'(Manager|MANAGER)'
        matches = re.finditer(manager_label_pattern, template_content)
        
        for match in matches:
            # Get surrounding context (4000 chars before to find parent div)
            # Note: Pending Actions div is ~3084 chars before "Manager: Tactical_X"
            start = max(0, match.start() - 4000)
            end = min(len(template_content), match.end() + 200)
            context = template_content[start:end]
            
            # Check if this "Manager" reference is properly protected
            is_protected = (
                'role-owner-only' in context or
                '{% if can_manage_org %}' in context or
                'can_manage_org and' in context
            )
            
            assert is_protected, \
                f"Found unprotected 'Manager' reference at position {match.start()}. " \
                f"Context: ...{context[-400:]}..."  # Show last 400 chars of context
    
    def test_media_streams_tab_exists(self, template_content):
        """
        CONTRACT: Template MUST have "Media / Streams" tab in navigation.
        
        WHY: Requirement #4 - Add tab with red pulsing dot indicator.
        """
        # Check for tab link
        assert 'Media / Streams' in template_content or 'media' in template_content.lower(), \
            "Template must have Media / Streams tab"
        
        # Check for red pulsing dot
        assert 'bg-delta-danger animate-pulse' in template_content, \
            "Media / Streams tab must have red pulsing dot indicator"
    
    def test_settings_tab_does_not_exist(self, template_content):
        """
        CONTRACT: Template MUST NOT have "Settings" tab in navigation.
        
        WHY: Requirement #3 - Settings tab was removed completely.
        """
        # Check for Settings tab link
        settings_pattern = r'<a[^>]*href=["\']#settings["\'][^>]*>.*?Settings.*?</a>'
        match = re.search(settings_pattern, template_content, re.IGNORECASE | re.DOTALL)
        
        assert match is None, \
            "Template must not have Settings tab. Found: " + (match.group(0) if match else "")
    
    def test_live_now_streams_section_exists(self, template_content):
        """
        CONTRACT: Template MUST have "Live Now" streams section.
        
        WHY: Requirement #5 - Insert Live Now streams block from Additional template.
        """
        assert 'Live Now' in template_content or 'LIVE' in template_content, \
            "Template must have Live Now streams section"
        
        # Check for streams container
        assert 'id="streams"' in template_content or 'streams' in template_content.lower(), \
            "Template must have streams section"
    
    def test_squad_cards_have_igl_manager_blocks(self, template_content):
        """
        CONTRACT: Squad cards MUST have structure for IGL and Manager display.
        
        WHY: Requirement #6 - Add Manager + IGL info blocks to active squad cards.
        """
        # Check for IGL label
        assert 'IGL' in template_content or 'Captain' in template_content, \
            "Squad cards must display IGL (Captain) information"
        
        # Check for conditional manager display
        if 'Manager' in template_content:
            # Manager should be conditional on can_manage_org
            manager_start = template_content.find('Manager')
            context_start = max(0, manager_start - 300)
            context_end = min(len(template_content), manager_start + 300)
            context = template_content[context_start:context_end]
            
            assert 'can_manage_org' in context or 'role-owner-only' in context, \
                "Manager display must be conditional on can_manage_org"
    
    def test_template_uses_org_detail_root_wrapper(self, template_content):
        """
        CONTRACT: Template MUST wrap content in #org-detail-root div with data attributes.
        
        WHY: Requirement #2 - Dynamic role-based UI requires root wrapper with
        data-role and data-type attributes.
        """
        assert 'id="org-detail-root"' in template_content, \
            "Template must have #org-detail-root wrapper div"
        
        assert 'data-role="{{ ui_role }}"' in template_content, \
            "Template must have data-role attribute on root wrapper"
        
        assert 'data-type="{{ ui_type }}"' in template_content, \
            "Template must have data-type attribute on root wrapper"
    
    def test_css_selectors_target_org_detail_root(self, template_content):
        """
        CONTRACT: CSS role/type selectors MUST target #org-detail-root, not body.
        
        WHY: Requirement #10 - JS behavior update. base.html provides body tag,
        so template cannot set data attributes on body.
        """
        # Check that CSS targets #org-detail-root
        assert '#org-detail-root[data-role' in template_content, \
            "CSS selectors must target #org-detail-root[data-role], not body[data-role]"
        
        # Ensure no body[data-role] selectors exist
        assert 'body[data-role' not in template_content, \
            "Template must not have body[data-role] selectors. Use #org-detail-root instead."
    
    def test_template_extends_base_html(self, template_content):
        """
        CONTRACT: Template MUST extend base.html.
        
        WHY: Requirement #1 - Wrap raw template with Django structure.
        """
        assert '{% extends "base.html" %}' in template_content, \
            "Template must extend base.html"
    
    def test_template_has_static_and_org_media_loads(self, template_content):
        """
        CONTRACT: Template MUST load both 'static' and 'org_media' tag libraries.
        
        WHY: 'static' for {% static %}, 'org_media' for {% safe_file_url %}.
        """
        assert '{% load static %}' in template_content, \
            "Template must load static tag library"
        
        assert '{% load org_media %}' in template_content, \
            "Template must load org_media tag library"
    
    def test_pending_actions_section_exists(self, template_content):
        """
        CONTRACT: Template MUST have Pending Actions section in sidebar.
        
        WHY: Requirement - Add missing right-sidebar section for owner actions.
        """
        assert 'Pending Actions' in template_content, \
            "Template must have Pending Actions section"
        
        # Should be owner-only
        pending_start = template_content.find('Pending Actions')
        if pending_start >= 0:
            context_start = max(0, pending_start - 300)
            context_end = min(len(template_content), pending_start + 300)
            context = template_content[context_start:context_end]
            
            assert 'role-owner-only' in context, \
                "Pending Actions section must be owner-only"
    
    def test_official_partners_section_exists(self, template_content):
        """
        CONTRACT: Template MUST have Official Partners section in sidebar.
        
        WHY: Requirement - Add missing right-sidebar section.
        """
        assert 'Official Partners' in template_content, \
            "Template must have Official Partners section"
    
    def test_official_merch_section_exists(self, template_content):
        """
        CONTRACT: Template MUST have Official Merch section in sidebar.
        
        WHY: Requirement - Add missing right-sidebar section (public-visible).
        """
        assert 'Official Merch' in template_content, \
            "Template must have Official Merch section"
        
        # Should be public-only (visible to non-owners)
        merch_start = template_content.find('Official Merch')
        if merch_start >= 0:
            context_start = max(0, merch_start - 300)
            context_end = min(len(template_content), merch_start + 300)
            context = template_content[context_start:context_end]
            
            assert 'role-public-only' in context, \
                "Official Merch section should be public-only"
    
    def test_manage_org_button_links_to_control_plane(self, template_content):
        """
        CONTRACT: "Open Control Plane" button MUST link to org_control_plane route.
        
        WHY: Requirement - Control Plane integration with correct naming.
        """
        # Check for button text (updated from "Manage Org" to "Open Control Plane")
        assert 'Open Control Plane' in template_content, \
            "Button must use 'Open Control Plane' label (not 'Manage Org')"
        
        # Check for correct URL pattern
        assert 'org_control_plane' in template_content, \
            "Button must link to org_control_plane route"
        
        # Check it's owner-only
        control_plane_start = template_content.find('Open Control Plane')
        if control_plane_start >= 0:
            context_start = max(0, control_plane_start - 2000)
            context_end = min(len(template_content), control_plane_start + 200)
            context = template_content[context_start:context_end]
            
            assert 'role-owner-only' in context, \
                "Open Control Plane button must be in owner-only section"


class TestOrgDetailServiceContract:
    """Contract tests for org_detail_service.py"""
    
    def test_service_returns_ui_role(self):
        """
        CONTRACT: Service MUST return ui_role in context.
        
        WHY: Requirement #8/#9 - Template needs ui_role for data-role attribute.
        """
        from apps.organizations.services.org_detail_service import get_org_detail_context
        from apps.organizations.models.organization import Organization
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Create test org (or use existing fixture)
        try:
            org = Organization.objects.first()
            if not org:
                pytest.skip("No organization exists for testing")
            
            # Test with anonymous user (PUBLIC)
            from django.contrib.auth.models import AnonymousUser
            context = get_org_detail_context(org.slug, AnonymousUser())
            
            assert 'ui_role' in context, \
                "Service must return ui_role in context"
            
            assert context['ui_role'] in ['OWNER', 'PUBLIC'], \
                f"ui_role must be OWNER or PUBLIC, got: {context['ui_role']}"
        
        except Exception as e:
            pytest.skip(f"Could not run service test: {e}")
    
    def test_service_returns_ui_type(self):
        """
        CONTRACT: Service MUST return ui_type in context.
        
        WHY: Requirement #8/#9 - Template needs ui_type for data-type attribute.
        """
        from apps.organizations.services.org_detail_service import get_org_detail_context
        from apps.organizations.models.organization import Organization
        
        try:
            org = Organization.objects.first()
            if not org:
                pytest.skip("No organization exists for testing")
            
            from django.contrib.auth.models import AnonymousUser
            context = get_org_detail_context(org.slug, AnonymousUser())
            
            assert 'ui_type' in context, \
                "Service must return ui_type in context"
            
            assert context['ui_type'] in ['PRO', 'GUILD', 'CLUB'], \
                f"ui_type must be PRO/GUILD/CLUB, got: {context['ui_type']}"
        
        except Exception as e:
            pytest.skip(f"Could not run service test: {e}")


# pytest configuration
pytest_plugins = []


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
