"""
Test centralized permissions module (Phase 0 Part E - Regression Guards).

Tests that apps/organizations/permissions.py correctly determines roles
and permission flags for different user types.
"""

import pytest
from django.contrib.auth.models import User
from apps.organizations.models import Organization, OrganizationStaffMembership
from apps.organizations.permissions import (
    get_org_role,
    can_access_control_plane,
    can_manage_org,
    can_view_financials,
    can_manage_staff,
    can_modify_governance,
    can_execute_terminal_actions,
    get_permission_context,
)


@pytest.mark.django_db
class TestGetOrgRole:
    """Test get_org_role() function."""

    def test_staff_user_returns_staff_role(self):
        """Platform staff always get STAFF role regardless of membership."""
        org = Organization.objects.create(name="Test Org", slug="test-org")
        staff_user = User.objects.create_user("staff_user", is_staff=True)
        
        assert get_org_role(staff_user, org) == 'STAFF'

    def test_ceo_returns_ceo_role(self):
        """Organization CEO gets CEO role."""
        ceo = User.objects.create_user("ceo_user")
        org = Organization.objects.create(name="Test Org", slug="test-org", ceo=ceo)
        
        assert get_org_role(ceo, org) == 'CEO'

    def test_admin_membership_returns_admin_role(self):
        """User with ADMIN staff membership gets ADMIN role."""
        user = User.objects.create_user("admin_user")
        org = Organization.objects.create(name="Test Org", slug="test-org")
        OrganizationStaffMembership.objects.create(
            organization=org,
            user=user,
            role='ADMIN'
        )
        
        assert get_org_role(user, org) == 'ADMIN'

    def test_manager_membership_returns_manager_role(self):
        """User with MANAGER staff membership gets MANAGER role."""
        user = User.objects.create_user("manager_user")
        org = Organization.objects.create(name="Test Org", slug="test-org")
        OrganizationStaffMembership.objects.create(
            organization=org,
            user=user,
            role='MANAGER'
        )
        
        assert get_org_role(user, org) == 'MANAGER'

    def test_no_relationship_returns_none_role(self):
        """User with no relationship to org gets NONE role."""
        user = User.objects.create_user("public_user")
        org = Organization.objects.create(name="Test Org", slug="test-org")
        
        assert get_org_role(user, org) == 'NONE'


@pytest.mark.django_db
class TestPermissionCheckers:
    """Test individual permission checker functions."""

    def test_can_access_control_plane(self):
        """Control plane access granted to STAFF, CEO, ADMIN, MANAGER."""
        assert can_access_control_plane('STAFF') is True
        assert can_access_control_plane('CEO') is True
        assert can_access_control_plane('ADMIN') is True
        assert can_access_control_plane('MANAGER') is True
        assert can_access_control_plane('NONE') is False

    def test_can_manage_org(self):
        """Org management allowed for STAFF, CEO, ADMIN, MANAGER."""
        assert can_manage_org('STAFF') is True
        assert can_manage_org('CEO') is True
        assert can_manage_org('ADMIN') is True
        assert can_manage_org('MANAGER') is True
        assert can_manage_org('NONE') is False

    def test_can_view_financials(self):
        """Financial access restricted to STAFF, CEO, ADMIN."""
        assert can_view_financials('STAFF') is True
        assert can_view_financials('CEO') is True
        assert can_view_financials('ADMIN') is True
        assert can_view_financials('MANAGER') is False
        assert can_view_financials('NONE') is False

    def test_can_manage_staff(self):
        """Staff management limited to STAFF and CEO."""
        assert can_manage_staff('STAFF') is True
        assert can_manage_staff('CEO') is True
        assert can_manage_staff('ADMIN') is False
        assert can_manage_staff('MANAGER') is False
        assert can_manage_staff('NONE') is False

    def test_can_modify_governance(self):
        """Governance changes only for STAFF and CEO."""
        assert can_modify_governance('STAFF') is True
        assert can_modify_governance('CEO') is True
        assert can_modify_governance('ADMIN') is False
        assert can_modify_governance('MANAGER') is False
        assert can_modify_governance('NONE') is False

    def test_can_execute_terminal_actions(self):
        """Terminal actions (delete, transfer) only for STAFF and CEO."""
        assert can_execute_terminal_actions('STAFF') is True
        assert can_execute_terminal_actions('CEO') is True
        assert can_execute_terminal_actions('ADMIN') is False
        assert can_execute_terminal_actions('MANAGER') is False
        assert can_execute_terminal_actions('NONE') is False


@pytest.mark.django_db
class TestGetPermissionContext:
    """Test get_permission_context() returns complete permission dict."""

    def test_ceo_gets_full_context(self):
        """CEO receives complete permission context."""
        ceo = User.objects.create_user("ceo_user")
        org = Organization.objects.create(name="Test Org", slug="test-org", ceo=ceo)
        
        context = get_permission_context(ceo, org)
        
        assert context['viewer_role'] == 'CEO'
        assert context['can_access_control_plane'] is True
        assert context['can_manage_org'] is True
        assert context['can_view_financials'] is True
        assert context['can_manage_staff'] is True
        assert context['can_modify_governance'] is True
        assert context['can_execute_terminal_actions'] is True

    def test_manager_gets_limited_context(self):
        """Manager has limited permissions."""
        user = User.objects.create_user("manager_user")
        org = Organization.objects.create(name="Test Org", slug="test-org")
        OrganizationStaffMembership.objects.create(
            organization=org,
            user=user,
            role='MANAGER'
        )
        
        context = get_permission_context(user, org)
        
        assert context['viewer_role'] == 'MANAGER'
        assert context['can_access_control_plane'] is True
        assert context['can_manage_org'] is True
        assert context['can_view_financials'] is False
        assert context['can_manage_staff'] is False
        assert context['can_modify_governance'] is False
        assert context['can_execute_terminal_actions'] is False

    def test_public_user_no_permissions(self):
        """Public user has no permissions."""
        user = User.objects.create_user("public_user")
        org = Organization.objects.create(name="Test Org", slug="test-org")
        
        context = get_permission_context(user, org)
        
        assert context['viewer_role'] == 'NONE'
        assert context['can_access_control_plane'] is False
        assert context['can_manage_org'] is False
        assert context['can_view_financials'] is False
        assert context['can_manage_staff'] is False
        assert context['can_modify_governance'] is False
        assert context['can_execute_terminal_actions'] is False
