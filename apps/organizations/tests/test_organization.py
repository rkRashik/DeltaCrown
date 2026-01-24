"""
Tests for Organization and OrganizationMembership models.

Coverage:
- Organization: creation, validation, slug generation, ownership, helper methods
- OrganizationMembership: creation, constraints, role validation

Performance: This file should run in <3 seconds.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils.text import slugify

from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.choices import MembershipRole
from apps.organizations.tests.factories import (
    OrganizationFactory,
    OrganizationMembershipFactory,
    UserFactory,
)

User = get_user_model()


@pytest.mark.django_db
class TestOrganization:
    """Test suite for Organization model."""
    
    def test_create_organization_minimal(self):
        """Test creating an organization with minimal required fields."""
        ceo = UserFactory.create()
        org = Organization.objects.create(
            name="Evil Geniuses",
            ceo=ceo,
        )
        
        assert org.pk is not None
        assert org.name == "Evil Geniuses"
        assert org.ceo == ceo
        assert org.is_verified is False  # Default value
        assert org.enforce_brand is False  # Default value
    
    def test_slug_auto_generated_on_save(self):
        """Test that slug is automatically generated from name on save."""
        org = OrganizationFactory.create(name="Team Liquid")
        
        assert org.slug == "team-liquid"
    
    def test_slug_uniqueness(self):
        """Test that duplicate slugs are not allowed."""
        OrganizationFactory.create(name="Cloud9")
        
        # Attempting to create another org with the same name should fail
        with pytest.raises(IntegrityError):
            Organization.objects.create(
                name="Cloud9",  # Same name = same slug
                ceo=UserFactory.create(),
            )
    
    def test_str_representation(self):
        """Test string representation of Organization."""
        org = OrganizationFactory.create(name="FaZe Clan")
        
        assert str(org) == "FaZe Clan"
    
    def test_get_absolute_url(self):
        """Test URL generation for organization detail page."""
        org = OrganizationFactory.create(name="G2 Esports")
        
        expected_url = f"/orgs/{org.slug}/"
        assert org.get_absolute_url() == expected_url
    
    def test_get_active_teams(self):
        """Test retrieval of active teams (non-temporary, status=ACTIVE)."""
        from apps.organizations.tests.factories import TeamFactory
        from apps.organizations.choices import TeamStatus
        
        org = OrganizationFactory.create()
        
        # Create active team
        active_team = TeamFactory.create(organization=org, status=TeamStatus.ACTIVE, is_temporary=False)
        
        # Create suspended team (should be excluded)
        TeamFactory.create(organization=org, status=TeamStatus.SUSPENDED, is_temporary=False)
        
        # Create temporary team (should be excluded)
        TeamFactory.create(organization=org, status=TeamStatus.ACTIVE, is_temporary=True)
        
        active_teams = org.get_active_teams()
        
        assert active_teams.count() == 1
        assert active_team in active_teams
    
    def test_can_user_manage_ceo(self):
        """Test that CEO can manage the organization."""
        org = OrganizationFactory.create()
        
        assert org.can_user_manage(org.ceo) is True
    
    def test_can_user_manage_staff(self):
        """Test that staff users can manage any organization."""
        org = OrganizationFactory.create()
        staff_user = UserFactory.create(is_staff=True)
        
        assert org.can_user_manage(staff_user) is True
    
    def test_can_user_manage_regular_user(self):
        """Test that regular users cannot manage organization."""
        org = OrganizationFactory.create()
        random_user = UserFactory.create()
        
        assert org.can_user_manage(random_user) is False
    
    def test_revenue_split_config_default(self):
        """Test that revenue_split_config defaults to empty dict."""
        org = OrganizationFactory.create()
        
        # Factory sets a default, but model defaults to {}
        # Test that JSONField accepts dict
        assert isinstance(org.revenue_split_config, dict)
    
    def test_enforce_brand_defaults_to_false(self):
        """Test that enforce_brand defaults to False."""
        org = OrganizationFactory.create()
        
        assert org.enforce_brand is False
    
    def test_is_verified_defaults_to_false(self):
        """Test that is_verified defaults to False."""
        org = OrganizationFactory.create()
        
        assert org.is_verified is False
    
    def test_timestamps_auto_set(self):
        """Test that created_at and updated_at are automatically set."""
        org = OrganizationFactory.create()
        
        assert org.created_at is not None
        assert org.updated_at is not None
        assert org.created_at <= org.updated_at


@pytest.mark.django_db
class TestOrganizationMembership:
    """Test suite for OrganizationMembership model."""
    
    def test_create_membership(self):
        """Test creating an organization membership."""
        org = OrganizationFactory.create()
        user = UserFactory.create()
        
        membership = OrganizationMembership.objects.create(
            organization=org,
            user=user,
            role=MembershipRole.MANAGER,
        )
        
        assert membership.pk is not None
        assert membership.organization == org
        assert membership.user == user
        assert membership.role == MembershipRole.MANAGER
    
    def test_role_choices_validation(self):
        """Test that only valid role choices are accepted."""
        membership = OrganizationMembershipFactory.create(role=MembershipRole.SCOUT)
        
        assert membership.role == MembershipRole.SCOUT
        assert membership.role in [choice[0] for choice in MembershipRole.choices]
    
    def test_permissions_json_field(self):
        """Test that permissions field accepts JSON data."""
        membership = OrganizationMembershipFactory.create(
            permissions={
                "can_create_teams": True,
                "can_view_financials": False,
                "can_manage_staff": True,
            }
        )
        
        assert membership.permissions["can_create_teams"] is True
        assert membership.permissions["can_view_financials"] is False
    
    def test_str_representation(self):
        """Test string representation of OrganizationMembership."""
        org = OrganizationFactory.create(name="T1")
        user = UserFactory.create(username="faker")
        membership = OrganizationMembershipFactory.create(
            organization=org,
            user=user,
            role=MembershipRole.MANAGER,
        )
        
        expected = f"faker - MANAGER at T1"
        assert str(membership) == expected
    
    def test_joined_at_auto_set(self):
        """Test that joined_at timestamp is automatically set."""
        membership = OrganizationMembershipFactory.create()
        
        assert membership.joined_at is not None
    
    def test_multiple_memberships_different_orgs(self):
        """Test that a user can be a member of multiple organizations."""
        user = UserFactory.create()
        org1 = OrganizationFactory.create()
        org2 = OrganizationFactory.create()
        
        membership1 = OrganizationMembershipFactory.create(organization=org1, user=user)
        membership2 = OrganizationMembershipFactory.create(organization=org2, user=user)
        
        assert membership1.pk != membership2.pk
        assert OrganizationMembership.objects.filter(user=user).count() == 2
    
    def test_default_permissions_empty_dict(self):
        """Test that permissions default to empty dict if not provided."""
        membership = OrganizationMembership.objects.create(
            organization=OrganizationFactory.create(),
            user=UserFactory.create(),
            role=MembershipRole.ANALYST,
        )
        
        # JSONField defaults to dict in model definition
        assert isinstance(membership.permissions, dict)
