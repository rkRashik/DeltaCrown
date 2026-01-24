"""
Tests for Team model.

Coverage:
- Team creation (organization-owned vs independent)
- CheckConstraint: organization XOR owner
- Slug generation with counter for uniqueness
- Model methods: get_absolute_url, is_organization_team, get_effective_logo_url
- Status and temporary team filtering

Performance: This file should run in <5 seconds.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from apps.organizations.models import Team
from apps.organizations.choices import TeamStatus
from apps.organizations.tests.factories import (
    OrganizationFactory,
    TeamFactory,
    UserFactory,
)

User = get_user_model()


@pytest.mark.django_db
class TestTeam:
    """Test suite for Team model."""
    
    def test_create_organization_team(self):
        """Test creating a team owned by an organization (organization set, owner null)."""
        org = OrganizationFactory.create()
        team = Team.objects.create(
            name="T1 Academy",
            organization=org,
            owner=None,  # Organization-owned team has no owner
            game_id=1,
            region="KR",
        )
        
        assert team.pk is not None
        assert team.organization == org
        assert team.owner is None
        assert team.is_organization_team() is True
    
    def test_create_independent_team(self):
        """Test creating a team owned by a user (owner set, organization null)."""
        user = UserFactory.create()
        team = Team.objects.create(
            name="Independent Squad",
            organization=None,  # Independent team has no organization
            owner=user,
            game_id=1,
            region="NA",
        )
        
        assert team.pk is not None
        assert team.organization is None
        assert team.owner == user
        assert team.is_organization_team() is False
    
    def test_check_constraint_both_org_and_owner_set(self):
        """Test that CheckConstraint prevents team with both organization AND owner."""
        org = OrganizationFactory.create()
        user = UserFactory.create()
        
        # Attempting to set both organization and owner should fail
        # Note: CheckConstraint is enforced at database level during save
        team = Team(
            name="Invalid Team",
            organization=org,
            owner=user,  # Both set = violation
            game_id=1,
            region="NA",
        )
        
        with pytest.raises((IntegrityError, ValidationError)):
            team.save()
    
    def test_check_constraint_neither_org_nor_owner_set(self):
        """Test that CheckConstraint prevents team with neither organization NOR owner."""
        # Attempting to create team with neither organization nor owner should fail
        team = Team(
            name="Orphan Team",
            organization=None,
            owner=None,  # Neither set = violation
            game_id=1,
            region="NA",
        )
        
        with pytest.raises((IntegrityError, ValidationError)):
            team.save()
    
    def test_slug_auto_generated_on_save(self):
        """Test that slug is automatically generated from name on save."""
        team = TeamFactory.create(name="Sentinels")
        
        assert team.slug == "sentinels"
    
    def test_slug_uniqueness_with_counter(self):
        """Test that duplicate team names get unique slugs with counter."""
        team1 = TeamFactory.create(name="Cloud9")
        team2 = TeamFactory.create(name="Cloud9")  # Same name
        
        # Slugs should be different due to counter
        assert team1.slug == "cloud9"
        assert team2.slug == "cloud9-2"  # Counter appended
    
    def test_str_representation(self):
        """Test string representation of Team."""
        team = TeamFactory.create(name="100 Thieves")
        
        assert str(team) == "100 Thieves"
    
    def test_get_absolute_url_organization_team(self):
        """Test URL generation for organization-owned team."""
        org = OrganizationFactory.create(name="FaZe Clan")
        team = TeamFactory.create(
            name="FaZe Academy",
            organization=org,
            owner=None,
        )
        
        # Organization-prefixed URL
        expected_url = f"/orgs/{org.slug}/teams/{team.slug}/"
        assert team.get_absolute_url() == expected_url
    
    def test_get_absolute_url_independent_team(self):
        """Test URL generation for independent team."""
        user = UserFactory.create()
        team = TeamFactory.create_independent(
            name="Solo Queue Heroes",
            owner=user,
        )
        
        # Independent team URL (no org prefix)
        expected_url = f"/teams/{team.slug}/"
        assert team.get_absolute_url() == expected_url
    
    def test_is_organization_team_returns_true(self):
        """Test is_organization_team() returns True for org-owned teams."""
        team = TeamFactory.create(organization=OrganizationFactory.create(), owner=None)
        
        assert team.is_organization_team() is True
    
    def test_is_organization_team_returns_false(self):
        """Test is_organization_team() returns False for independent teams."""
        team = TeamFactory.create_independent()
        
        assert team.is_organization_team() is False
    
    def test_get_effective_logo_url_enforce_brand_true(self):
        """Test that team inherits org logo when enforce_brand=True."""
        org = OrganizationFactory.create(
            enforce_brand=True,
            logo="https://cdn.example.com/org-logo.png",
        )
        team = TeamFactory.create(
            organization=org,
            owner=None,
            logo="https://cdn.example.com/team-logo.png",  # Team has own logo
        )
        
        # Should return organization logo (brand enforcement)
        effective_logo = team.get_effective_logo_url()
        assert effective_logo == org.logo
    
    def test_get_effective_logo_url_enforce_brand_false(self):
        """Test that team uses own logo when enforce_brand=False."""
        org = OrganizationFactory.create(
            enforce_brand=False,
            logo="https://cdn.example.com/org-logo.png",
        )
        team = TeamFactory.create(
            organization=org,
            owner=None,
            logo="https://cdn.example.com/team-logo.png",
        )
        
        # Should return team logo (no brand enforcement)
        effective_logo = team.get_effective_logo_url()
        assert effective_logo == team.logo
    
    def test_get_effective_logo_url_independent_team(self):
        """Test that independent team always uses own logo."""
        team = TeamFactory.create_independent(
            logo="https://cdn.example.com/independent-logo.png",
        )
        
        # Should return team logo
        effective_logo = team.get_effective_logo_url()
        assert effective_logo == team.logo
    
    def test_can_user_manage_org_ceo(self):
        """Test that organization CEO can manage team."""
        org = OrganizationFactory.create()
        team = TeamFactory.create(organization=org, owner=None)
        
        assert team.can_user_manage(org.ceo) is True
    
    def test_can_user_manage_team_owner(self):
        """Test that team owner can manage independent team."""
        user = UserFactory.create()
        team = TeamFactory.create_independent(owner=user)
        
        assert team.can_user_manage(user) is True
    
    def test_can_user_manage_manager_membership(self):
        """Test that team manager can manage team."""
        from apps.organizations.tests.factories import TeamMembershipFactory
        from apps.organizations.choices import MembershipRole
        
        team = TeamFactory.create()
        manager = UserFactory.create()
        TeamMembershipFactory.create(
            team=team,
            user=manager,
            role=MembershipRole.MANAGER,
        )
        
        # Manager role should be able to manage team
        assert team.can_user_manage(manager) is True
    
    def test_can_user_manage_regular_player_cannot_manage(self):
        """Test that regular player cannot manage team."""
        from apps.organizations.tests.factories import TeamMembershipFactory
        from apps.organizations.choices import MembershipRole
        
        team = TeamFactory.create()
        player = UserFactory.create()
        TeamMembershipFactory.create(
            team=team,
            user=player,
            role=MembershipRole.PLAYER,
        )
        
        # Regular player should NOT be able to manage team
        assert team.can_user_manage(player) is False
    
    def test_status_default_is_active(self):
        """Test that team status defaults to ACTIVE."""
        team = TeamFactory.create()
        
        assert team.status == TeamStatus.ACTIVE
    
    def test_is_temporary_defaults_to_false(self):
        """Test that is_temporary defaults to False."""
        team = TeamFactory.create()
        
        assert team.is_temporary is False
    
    def test_timestamps_auto_set(self):
        """Test that created_at and updated_at are automatically set."""
        team = TeamFactory.create()
        
        assert team.created_at is not None
        assert team.updated_at is not None
        assert team.created_at <= team.updated_at
    
    def test_unique_constraint_owner_game_id_active_status(self):
        """Test that user can only own one ACTIVE team per game."""
        user = UserFactory.create()
        game_id = 1
        
        # Create first team (ACTIVE)
        team1 = TeamFactory.create_independent(
            owner=user,
            game_id=game_id,
            status=TeamStatus.ACTIVE,
        )
        
        # Attempting to create second ACTIVE team for same owner+game should fail
        with pytest.raises(IntegrityError):
            Team.objects.create(
                name="Duplicate Team",
                owner=user,
                organization=None,
                game_id=game_id,
                status=TeamStatus.ACTIVE,
                region="NA",
            )
    
    def test_multiple_teams_different_games_allowed(self):
        """Test that user can own multiple teams if different games."""
        user = UserFactory.create()
        
        team1 = TeamFactory.create_independent(owner=user, game_id=1)
        team2 = TeamFactory.create_independent(owner=user, game_id=2)
        
        # Should be allowed (different games)
        assert team1.game_id != team2.game_id
        assert Team.objects.filter(owner=user).count() == 2
    
    def test_multiple_teams_different_statuses_allowed(self):
        """Test that user can have multiple teams in same game if not all ACTIVE."""
        user = UserFactory.create()
        game_id = 1
        
        team1 = TeamFactory.create_independent(
            owner=user,
            game_id=game_id,
            status=TeamStatus.ACTIVE,
        )
        team2 = TeamFactory.create_independent(
            owner=user,
            game_id=game_id,
            status=TeamStatus.DISBANDED,  # Not ACTIVE
        )
        
        # Should be allowed (different statuses)
        assert Team.objects.filter(owner=user, game_id=game_id).count() == 2
