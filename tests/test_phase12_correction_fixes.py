"""
Regression tests for Phase 12 correction fixes.

Tests:
1. Team detail template compiles (no TemplateSyntaxError)
2. Team manage loads without select_related('owner') crash
3. Hub shows featured teams (no empty state when teams exist)
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestTeamDetailTemplateCompiles:
    """Test that team detail template compiles without TemplateSyntaxError."""
    
    def test_team_detail_template_compiles(self, client):
        """Team detail page should compile and return 200 for a public team."""
        from apps.organizations.tests.factories import TeamFactory, GameFactory
        from apps.organizations.choices import TeamStatus, TeamVisibility
        
        # Create game and team
        game = GameFactory()
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            visibility=TeamVisibility.PUBLIC,
            game=game
        )
        
        # GET team detail page
        url = reverse('organizations:team_detail', kwargs={'slug': team.slug})
        response = client.get(url)
        
        # Should return 200 (not TemplateSyntaxError)
        assert response.status_code == 200
        assert team.name.encode() in response.content


@pytest.mark.django_db
class TestTeamManageNoOwnerSelectRelatedCrash:
    """Test that team manage loads without select_related('owner') FieldError."""
    
    def test_team_manage_independent_team(self, client):
        """Team manage should load for independent team (no owner field crash)."""
        from apps.organizations.tests.factories import TeamFactory, UserFactory, GameFactory
        from apps.organizations.choices import TeamStatus, MembershipRole, MembershipStatus
        from apps.organizations.models import TeamMembership
        
        # Create user, game, and independent team
        user = UserFactory()
        game = GameFactory()
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            created_by=user,
            organization=None,  # Independent team
            game=game
        )
        
        # Create membership (user is owner)
        TeamMembership.objects.create(
            team=team,
            user=user,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE
        )
        
        # Login as team owner
        client.force_login(user)
        
        # GET team manage page
        url = reverse('organizations:team_manage', kwargs={'slug': team.slug})
        response = client.get(url)
        
        # Should return 200 (not FieldError: select_related('owner'))
        assert response.status_code == 200
    
    def test_team_manage_org_team(self, client):
        """Team manage should load for org team."""
        from apps.organizations.tests.factories import (
            TeamFactory, OrganizationFactory, UserFactory, GameFactory
        )
        from apps.organizations.choices import (
            TeamStatus, MembershipRole as TeamRole, MembershipStatus,
            OrganizationMembershipRole as OrgRole
        )
        from apps.organizations.models import TeamMembership, OrganizationMembership
        
        # Create user, game, org, and org-owned team
        user = UserFactory()
        game = GameFactory()
        org = OrganizationFactory(ceo=user)
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            organization=org,
            game=game
        )
        
        # Create org membership (user is CEO)
        OrganizationMembership.objects.create(
            organization=org,
            user=user,
            role=OrgRole.CEO,
            status=MembershipStatus.ACTIVE
        )
        
        # Login as org CEO
        client.force_login(user)
        
        # GET org team manage page
        url = reverse('organizations:org_team_manage', kwargs={
            'org_slug': org.slug,
            'team_slug': team.slug
        })
        response = client.get(url)
        
        # Should return 200 (not FieldError)
        assert response.status_code == 200


@pytest.mark.django_db
class TestHubShowsFeaturedTeams:
    """Test that hub shows featured teams (no empty state when teams exist)."""
    
    def test_hub_shows_public_team(self, client):
        """Hub should show public active teams in featured section."""
        from apps.organizations.tests.factories import TeamFactory, GameFactory
        from apps.organizations.choices import TeamStatus, TeamVisibility
        
        # Create game and public team
        game = GameFactory()
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            visibility=TeamVisibility.PUBLIC,
            game=game,
            name="Test Elite Squad"
        )
        
        # GET hub page
        url = reverse('organizations:hub')
        response = client.get(url)
        
        # Should return 200 and show the team
        assert response.status_code == 200
        assert "Test Elite Squad" in response.content.decode()
        assert "No Teams Available" not in response.content.decode()
    
    def test_hub_shows_teams_without_rankings(self, client):
        """Hub should show teams even without competition snapshots/rankings."""
        from apps.organizations.tests.factories import TeamFactory, GameFactory
        from apps.organizations.choices import TeamStatus, TeamVisibility
        
        # Create game and team WITHOUT ranking
        game = GameFactory()
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            visibility=TeamVisibility.PUBLIC,
            game=game,
            name="Unranked Warriors"
        )
        
        # Ensure no ranking exists
        assert not hasattr(team, 'ranking') or team.ranking is None
        
        # GET hub page
        url = reverse('organizations:hub')
        response = client.get(url)
        
        # Should return 200 and show the team (fallback to created_at order)
        assert response.status_code == 200
        assert "Unranked Warriors" in response.content.decode()
