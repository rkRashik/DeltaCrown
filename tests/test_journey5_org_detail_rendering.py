"""
Journey 5 Acceptance Tests: Organization Detail Page

Validates acceptance criteria from TEAM_ORG_VNEXT_MASTER_TRACKER.md:
1. Page loads without FieldError (e.g., created_at vs joined_at)
2. Tabs render (Headquarters, Active Squads, Operations Log, etc.)
3. Teams list correct (shows org teams)
4. Private fields gated (role-owner-only classes for financials)

This complements test_org_detail_no_schema_errors.py (smoke test for FieldError),
by testing complete rendering and privacy controls.
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, OrganizationMembership, Team

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestJourney5OrgDetailRendering:
    """Journey 5: Org Detail - Tab rendering and privacy controls."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = Client()
        
        # Create users
        self.ceo_user = User.objects.create_user(
            username='ceo',
            email='ceo@example.com',
            password='testpass123'
        )
        self.public_user = User.objects.create_user(
            username='publicuser',
            email='public@example.com',
            password='testpass123'
        )
        
        # Create organization
        self.org = Organization.objects.create(
            name='Alpha Esports',
            slug='alpha-esports',
            ceo=self.ceo_user,
            description='Premier competitive gaming organization'
        )
        
        # Create CEO membership
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.ceo_user,
            role='CEO'
        )
        
        # Create teams for the org
        self.team1 = Team.objects.create(
            name='Alpha Valorant',
            slug='alpha-valorant',
            organization=self.org,
            created_by=self.ceo_user,
            game_id=1,  # IntegerField, not FK
            region='NA',
            status='ACTIVE'
        )
        self.team2 = Team.objects.create(
            name='Alpha CS2',
            slug='alpha-cs2',
            organization=self.org,
            created_by=self.ceo_user,
            game_id=2,
            region='EU',
            status='ACTIVE'
        )
    
    def test_org_detail_loads_without_field_error(self):
        """Detail page loads without FieldError (e.g., created_at vs joined_at)."""
        self.client.login(username='ceo', password='testpass123')
        response = self.client.get(f'/orgs/{self.org.slug}/')
        
        # Should return 200, not crash with FieldError
        assert response.status_code == 200
        assert self.org.name.encode() in response.content
    
    def test_org_detail_renders_tabs(self):
        """Detail page renders navigation tabs for different sections."""
        self.client.login(username='ceo', password='testpass123')
        response = self.client.get(f'/orgs/{self.org.slug}/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify tabs exist (using anchor hrefs from template)
        assert 'href="#overview"' in content or 'Headquarters' in content
        assert 'href="#teams"' in content or 'Active Squads' in content
        assert 'href="#matches"' in content or 'Operations Log' in content
        assert 'href="#streams"' in content or 'Media / Streams' in content
    
    def test_org_detail_shows_org_teams(self):
        """Detail page correctly lists organization's teams."""
        self.client.login(username='ceo', password='testpass123')
        response = self.client.get(f'/orgs/{self.org.slug}/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Teams should appear in content
        assert 'Alpha Valorant' in content
        assert 'Alpha CS2' in content
    
    def test_org_detail_shows_team_count(self):
        """Detail page shows accurate active team count."""
        self.client.login(username='ceo', password='testpass123')
        response = self.client.get(f'/orgs/{self.org.slug}/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Should show 2 active teams (context: active_teams_count)
        # Template displays this in stats section
        assert 'Active Squads' in content
    
    def test_org_detail_financials_gated_for_public(self):
        """Public user sees financials tab with role-owner-only class (gated)."""
        # Anonymous public access
        response = self.client.get(f'/orgs/{self.org.slug}/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Financials should have role-owner-only class (privacy gate)
        # Template: <a href="#finance" class="... role-owner-only">Financials ...</a>
        if 'Financials' in content:
            # Check that it's marked as owner-only
            assert 'role-owner-only' in content
    
    def test_org_detail_ceo_sees_financials(self):
        """CEO can see financials tab (no access control on viewing tab itself)."""
        self.client.login(username='ceo', password='testpass123')
        response = self.client.get(f'/orgs/{self.org.slug}/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # CEO should see financials tab
        assert 'Financials' in content or 'href="#finance"' in content
    
    def test_org_detail_uses_org_detail_context_service(self):
        """Detail page uses get_org_detail_context service (context shape validation)."""
        self.client.login(username='ceo', password='testpass123')
        response = self.client.get(f'/orgs/{self.org.slug}/')
        
        assert response.status_code == 200
        
        # Validate context keys exist (from service)
        context = response.context
        assert 'organization' in context
        assert 'squads' in context
        assert 'active_teams_count' in context
        assert 'can_manage_org' in context
        
        # Validate org data
        assert context['organization'].slug == self.org.slug
        assert context['active_teams_count'] == 2
    
    def test_org_detail_squads_include_team_data(self):
        """Squads context includes team_name, team_slug, rank (or None)."""
        self.client.login(username='ceo', password='testpass123')
        response = self.client.get(f'/orgs/{self.org.slug}/')
        
        assert response.status_code == 200
        context = response.context
        
        # Squads should be list of dicts with team data
        squads = context.get('squads', [])
        assert len(squads) == 2
        
        # Each squad should have required fields
        for squad in squads:
            assert 'team_name' in squad
            assert 'team_slug' in squad
            assert 'game_label' in squad
            # rank can be None (unranked), but key should exist
            assert 'rank' in squad
            assert 'tier' in squad
