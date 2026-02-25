"""
Organization Detail Service schema guards (Phase 0 Part E - Regression Guards).

Prevents invalid Django ORM relationships and queries that cause crashes.

ANTI-PATTERNS TO PREVENT:
1. teams__members (invalid - Team has 'roster' not 'members')
2. .members.all() on Organization (invalid - use staff_memberships)
3. select_related('game') when game is NULL
4. filter(is_active=True) on models without is_active field
"""

import pytest
from django.db.models import Model
from apps.organizations.models import Organization, Team
from apps.organizations.services.org_detail_service import get_org_detail_context
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestOrgDetailServiceSchemaGuards:
    """Prevent invalid ORM relationships in org_detail_service."""

    def test_no_teams_members_lookup(self):
        """Service must not use teams__members (Team has 'roster' not 'members')."""
        # Read the service file and check for invalid patterns
        import inspect
        import apps.organizations.services.org_detail_service as service_module
        
        source = inspect.getsource(service_module)
        
        # These are INVALID and must not exist
        assert 'teams__members' not in source, "INVALID: Team model has 'roster' not 'members'"
        assert '.members.all()' not in source or 'staff_memberships' in source, (
            "INVALID: Organization has 'staff_memberships' not 'members'"
        )

    def test_no_invalid_select_related_on_nullable_game(self):
        """Service must not use select_related('game') when game can be NULL."""
        import inspect
        import apps.organizations.services.org_detail_service as service_module
        
        source = inspect.getsource(service_module)
        
        # If select_related('game') exists, it should be in prefetch or conditional
        if "select_related('game')" in source:
            # Must not be direct query - should use Prefetch or check for null
            assert 'Prefetch' in source or 'filter(game__isnull=False)' in source, (
                "select_related('game') requires null handling"
            )

    def test_no_is_active_filter_on_organization(self):
        """Service must not filter organizations by is_active (field doesn't exist)."""
        import inspect
        import apps.organizations.services.org_detail_service as service_module
        
        source = inspect.getsource(service_module)
        
        # Organization model does not have is_active field
        assert 'organization.filter(is_active=' not in source.lower(), (
            "Organization model has no is_active field"
        )

    def test_service_returns_valid_context(self):
        """Service returns valid context dict with required keys."""
        ceo = User.objects.create_user("ceo_user")
        org = Organization.objects.create(name="Test Org", slug="test-org", ceo=ceo)
        
        context = get_org_detail_context(org.slug, ceo)
        
        # Must have core keys
        assert 'organization' in context
        assert 'viewer_role' in context or 'ui_role' in context
        assert 'can_manage_org' in context
        
        # Organization must be the model instance
        assert isinstance(context['organization'], Organization)

    def test_service_handles_teams_correctly(self):
        """Service correctly accesses Team.roster (not Team.members)."""
        ceo = User.objects.create_user("ceo_user")
        org = Organization.objects.create(name="Test Org", slug="test-org", ceo=ceo)
        
        # Create team with the organization (using correct reverse relationship)
        team = Team.objects.create(
            name="Test Team",
            organization=org,
            game_id=1  # Assuming game with ID 1 exists
        )
        
        # Service should work without AttributeError
        context = get_org_detail_context(org.slug, ceo)
        
        # If teams are in context, verify structure
        if 'teams' in context:
            teams = context['teams']
            assert isinstance(teams, list)

    def test_service_handles_public_viewer(self):
        """Service handles anonymous/public viewer without crash."""
        ceo = User.objects.create_user("ceo_user")
        org = Organization.objects.create(name="Test Org", slug="test-org", ceo=ceo)
        
        public_user = User.objects.create_user("public_user")
        
        # Should not crash for non-member viewer
        context = get_org_detail_context(org.slug, public_user)
        
        assert context['can_manage_org'] is False
        assert context.get('viewer_role') == 'NONE' or context.get('ui_role') == 'PUBLIC'
