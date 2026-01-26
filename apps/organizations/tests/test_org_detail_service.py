"""
Service-level tests for organization detail.

These tests verify:
- Slug-based lookup works correctly
- No is_active filtering on Organization model
- Context structure is correct
- Permission logic works
"""

import os
import pytest
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.http import Http404

from apps.organizations.models.organization import Organization
from apps.organizations.services.org_detail_service import get_org_detail_context

User = get_user_model()


@pytest.mark.skipif(
    os.getenv('DB_TEST_BLOCKED') == '1',
    reason="Database permissions not available in test environment"
)
class TestOrgDetailService(TestCase):
    """Test organization detail service layer."""
    
    def setUp(self):
        """Create test data."""
        self.user1 = User.objects.create_user(
            username='ceo_user',
            email='ceo@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='viewer_user',
            email='viewer@test.com',
            password='testpass123'
        )
        
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.user1,
            is_verified=True,
            description='Test organization for unit testing'
        )
    
    def test_slug_lookup_works(self):
        """Verify service can find organization by slug."""
        context = get_org_detail_context('test-org', self.user2)
        
        self.assertEqual(context['organization'].slug, 'test-org')
        self.assertEqual(context['organization'].name, 'Test Org')
    
    def test_nonexistent_org_raises_404(self):
        """Verify 404 raised for non-existent org."""
        with self.assertRaises(Http404):
            get_org_detail_context('does-not-exist', self.user2)
    
    def test_ceo_has_manage_permission(self):
        """Verify CEO has can_manage_org=True."""
        context = get_org_detail_context('test-org', self.user1)
        
        self.assertTrue(context['can_manage_org'])
    
    def test_public_viewer_no_manage_permission(self):
        """Verify non-CEO viewer has can_manage_org=False."""
        context = get_org_detail_context('test-org', self.user2)
        
        self.assertFalse(context['can_manage_org'])
    
    def test_context_structure(self):
        """Verify context has required keys."""
        context = get_org_detail_context('test-org', self.user2)
        
        required_keys = ['organization', 'can_manage_org', 'active_teams_count', 'squads']
        for key in required_keys:
            self.assertIn(key, context, f"Context missing key: {key}")
    
    def test_squads_structure(self):
        """Verify squads list has correct structure."""
        context = get_org_detail_context('test-org', self.user2)
        
        self.assertIsInstance(context['squads'], list)
        # Empty org should have empty squads
        self.assertEqual(len(context['squads']), 0)


class TestNoIsActiveOnOrganization(TestCase):
    """Regression test: Prevent is_active filtering on Organization."""
    
    def test_service_does_not_filter_is_active(self):
        """Verify service code does not use is_active on Organization."""
        import inspect
        from apps.organizations.services import org_detail_service
        
        # Get source code of the service module
        source = inspect.getsource(org_detail_service)
        
        # Check for problematic patterns
        # We allow "teams.filter(is_active=" but NOT "Organization...is_active"
        problematic_patterns = [
            'Organization.objects.filter(is_active=',
            'Organization.objects.get(is_active=',
            'get_object_or_404(Organization', # then check for is_active in same call
        ]
        
        lines = source.split('\n')
        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('#'):
                continue
            
            # Check for Organization query with is_active
            if 'Organization.objects' in line and 'is_active' in line:
                self.fail(
                    f"Line {i}: Found is_active filter on Organization model\n"
                    f"Organization does NOT have is_active field!\n"
                    f"Line content: {line.strip()}"
                )
            
            # Check get_object_or_404 with is_active
            if 'get_object_or_404' in line:
                # Look ahead a few lines for is_active parameter
                context_lines = '\n'.join(lines[i-1:min(i+5, len(lines))])
                if 'Organization' in context_lines and 'is_active' in context_lines:
                    self.fail(
                        f"Line {i}: Found is_active in get_object_or_404(Organization...)\n"
                        f"Organization does NOT have is_active field!\n"
                        f"Context:\n{context_lines}"
                    )
    
    def test_view_does_not_filter_is_active(self):
        """Verify view code does not use is_active on Organization."""
        import inspect
        from apps.organizations.views import org
        
        source = inspect.getsource(org)
        
        lines = source.split('\n')
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('#'):
                continue
            
            # Check for Organization query with is_active in views
            if 'Organization.objects' in line and 'is_active' in line:
                self.fail(
                    f"Line {i} in views/org.py: Found is_active filter on Organization\n"
                    f"Organization does NOT have is_active field!\n"
                    f"Line content: {line.strip()}"
                )


class TestNoTeamIsActiveFilter(TestCase):
    """Regression test: Prevent is_active filtering on Team (use status instead)."""
    
    def test_service_does_not_use_team_is_active(self):
        """Verify service does not use is_active on Team (vNext Team has status, not is_active)."""
        import inspect
        from apps.organizations.services import org_detail_service
        
        source = inspect.getsource(org_detail_service)
        lines = source.split('\n')
        
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('#'):
                continue
            
            # Check for .filter(is_active= on any queryset
            if '.filter(is_active=' in line or 'is_active=True' in line or 'is_active=False' in line:
                self.fail(
                    f"Line {i}: Found is_active filter in service\n"
                    f"vNext Team model has 'status' field, not 'is_active'!\n"
                    f"Use: .filter(status='ACTIVE') instead\n"
                    f"Line content: {line.strip()}"
                )


class TestNoTeamGameFK(TestCase):
    """Regression test: Prevent select_related('game') on Team (game_id is integer, not FK)."""
    
    def test_service_does_not_select_related_game(self):
        """Verify service does not use select_related('game') or prefetch_related with game FK."""
        import inspect
        from apps.organizations.services import org_detail_service
        
        source = inspect.getsource(org_detail_service)
        lines = source.split('\n')
        
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('#'):
                continue
            
            # Check for select_related('game')
            if "select_related('game')" in line or 'select_related("game")' in line:
                self.fail(
                    f"Line {i}: Found select_related('game') in service\n"
                    f"vNext Team model has 'game_id' (integer), not 'game' FK!\n"
                    f"Remove this select_related - it will crash.\n"
                    f"Line content: {line.strip()}"
                )
            
            # Check for prefetch_related with game path
            if 'teams__game' in line or "teams__game" in line:
                self.fail(
                    f"Line {i}: Found 'teams__game' in prefetch_related\n"
                    f"vNext Team model has 'game_id' (integer), not 'game' FK!\n"
                    f"Remove this prefetch - it will crash.\n"
                    f"Line content: {line.strip()}"
                )
