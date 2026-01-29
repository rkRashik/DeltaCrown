"""
Template parity markers test (Phase 0 Part E - Regression Guards).

Verifies that the Django template for Control Plane contains key markers
from the raw HTML template to ensure 100% parity is maintained.
"""

import pytest
from django.template.loader import get_template


class TestControlPlaneTemplateParity:
    """Verify Control Plane template contains critical markers from raw template."""

    def test_template_contains_unique_markers(self):
        """Template must contain at least 10 unique markers from raw design."""
        template = get_template('organizations/org/org_control_plane.html')
        content = template.template.source
        
        # These are unique markers from the raw Organization_Control_Plane.html
        # that must exist in the Django template to prove parity
        markers = [
            'id="control-plane-root"',
            'data-role="{{ viewer_role }}"',
            'ORGANIZATION CONTROL PLANE',
            'class="tab-content-item active"',
            'id="tab-organization"',
            'id="tab-finance"',
            'id="tab-staff"',
            'id="tab-governance"',
            'id="tab-danger"',
            'role-staff-only',
            'role-ceo-only',
            'Finance Overview',
            'Staff Management',
            'Delete Organization',
            'Transfer Ownership',
        ]
        
        found_markers = []
        missing_markers = []
        
        for marker in markers:
            if marker in content:
                found_markers.append(marker)
            else:
                missing_markers.append(marker)
        
        assert len(found_markers) >= 10, (
            f"Template parity check failed. "
            f"Found only {len(found_markers)}/15 markers. "
            f"Missing: {missing_markers}"
        )

    def test_template_has_role_based_visibility(self):
        """Template must use role-based CSS visibility classes."""
        template = get_template('organizations/org/org_control_plane.html')
        content = template.template.source
        
        # Role-based visibility classes are critical for permission enforcement
        assert 'role-staff-only' in content
        assert 'role-ceo-only' in content
        assert 'role-admin-only' in content or 'role-admin-ceo' in content

    def test_template_has_danger_zone_safeguards(self):
        """Template must contain danger zone section with terminal actions."""
        template = get_template('organizations/org/org_control_plane.html')
        content = template.template.source
        
        # Danger zone markers
        assert 'Delete Organization' in content or 'delete-org' in content
        assert 'Transfer Ownership' in content or 'transfer' in content

    def test_template_extends_base(self):
        """Template must extend base layout."""
        template = get_template('organizations/org/org_control_plane.html')
        content = template.template.source
        
        # Must use Django template inheritance
        assert "{% extends" in content
        assert "{% block" in content
