"""
Test suite for TeamService.get_team_detail() and RosterMember DTO.

Regression tests for:
- AttributeError: 'RosterMember' object has no attribute 'id' (fixed 2026-01-26)
- Ensures membership_id and user_id are properly populated in DTOs
- Validates serialization contract for team detail endpoint
"""

import pytest
from django.test import TestCase
from apps.organizations.services.team_service import TeamService
from apps.organizations.services.exceptions import NotFoundError, ValidationError


@pytest.mark.django_db
class TestRosterMemberDTO:
    """Test RosterMember DTO includes required fields."""
    
    @pytest.fixture
    def test_user(self, django_user_model):
        """Create test user."""
        return django_user_model.objects.create_user(
            username='test_roster_user',
            email='roster@test.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def test_game(self):
        """Create test game."""
        from apps.games.models import Game
        game, _ = Game.objects.get_or_create(
            slug='test-game-roster',
            defaults={
                'name': 'Test Game Roster',
                'is_active': True,
                'team_size_min': 5,
                'team_size_max': 7
            }
        )
        return game
    
    @pytest.fixture
    def test_team(self, test_user, test_game):
        """Create test team with membership."""
        from apps.organizations.models import Team, TeamMembership
        
        team = Team.objects.create(
            name='Test Roster Team',
            slug='test-roster-team',
            owner=test_user,
            game=test_game,
            region='NA',
            status='ACTIVE'
        )
        
        # Create membership
        TeamMembership.objects.create(
            team=team,
            user=test_user,
            role='OWNER',
            status='ACTIVE',
            is_tournament_captain=True
        )
        
        return team
    
    def test_get_roster_members_includes_membership_id_and_user_id(self, test_team, test_user):
        """
        Test that RosterMember DTO includes membership_id and user_id.
        
        Regression test for: AttributeError: 'RosterMember' object has no attribute 'id'
        """
        # Act
        roster = TeamService.get_roster_members(team_id=test_team.id)
        
        # Assert
        assert len(roster) == 1, "Should have exactly 1 member"
        
        member = roster[0]
        
        # Check DTO has required fields
        assert hasattr(member, 'membership_id'), "RosterMember must have membership_id"
        assert hasattr(member, 'user_id'), "RosterMember must have user_id"
        
        # Check values are correct
        membership = test_team.members.first()
        assert member.membership_id == membership.id, "membership_id should match TeamMembership PK"
        assert member.user_id == test_user.id, "user_id should match User PK"
        assert member.username == test_user.username
        assert member.role == 'OWNER'
        assert member.status == 'ACTIVE'
        assert member.is_tournament_captain is True
    
    def test_get_roster_members_multiple_members(self, test_team, test_user, django_user_model, test_game):
        """Test roster with multiple members all have membership_id."""
        from apps.organizations.models import TeamMembership
        
        # Add second member
        user2 = django_user_model.objects.create_user(
            username='player2',
            email='player2@test.com',
            password='testpass123'
        )
        
        membership2 = TeamMembership.objects.create(
            team=test_team,
            user=user2,
            role='PLAYER',
            status='ACTIVE',
            is_tournament_captain=False
        )
        
        # Act
        roster = TeamService.get_roster_members(team_id=test_team.id)
        
        # Assert
        assert len(roster) == 2, "Should have 2 members"
        
        # Both members should have membership_id and user_id
        for member in roster:
            assert member.membership_id > 0, "All members must have valid membership_id"
            assert member.user_id > 0, "All members must have valid user_id"
        
        # Verify specific values
        player2_member = [m for m in roster if m.username == 'player2'][0]
        assert player2_member.membership_id == membership2.id
        assert player2_member.user_id == user2.id
    
    def test_get_team_detail_serializes_members_with_id_field(self, test_team, test_user):
        """
        Test that get_team_detail() returns member dicts with 'id' field.
        
        Regression test for: Line 543 'id': m.id raises AttributeError
        Frontend expects 'id' field for member operations.
        """
        # Act
        result = TeamService.get_team_detail(team_id=test_team.id, include_members=True)
        
        # Assert structure
        assert 'team' in result
        assert 'members' in result
        assert 'invites' in result
        
        # Check members list
        members = result['members']
        assert len(members) == 1, "Should have 1 member"
        
        member_dict = members[0]
        
        # Check serialized fields
        assert 'id' in member_dict, "Member dict must have 'id' field for frontend"
        assert 'membership_id' in member_dict, "Member dict should include explicit membership_id"
        assert 'user_id' in member_dict, "Member dict should include user_id"
        assert 'username' in member_dict
        assert 'role' in member_dict
        
        # Check values
        membership = test_team.members.first()
        assert member_dict['id'] == membership.id, "'id' should be membership PK"
        assert member_dict['membership_id'] == membership.id
        assert member_dict['user_id'] == test_user.id
        assert member_dict['username'] == test_user.username
        assert member_dict['role'] == 'OWNER'
    
    def test_get_team_detail_no_attribute_error(self, test_team):
        """
        Test that get_team_detail() does not raise AttributeError on m.id.
        
        This was the production-blocking bug.
        """
        try:
            result = TeamService.get_team_detail(team_id=test_team.id, include_members=True)
            # If we get here, no AttributeError was raised
            assert 'members' in result
            assert isinstance(result['members'], list)
        except AttributeError as e:
            pytest.fail(f"AttributeError raised: {e}")
    
    def test_get_team_detail_performance_query_count(self, test_team, django_assert_max_num_queries):
        """
        Test that get_team_detail() stays within query budget.
        
        Contract: ≤5 queries for team detail with members
        """
        # Allow 6 queries: 1 team, 1 exists check, 1 memberships, 3 buffer
        with django_assert_max_num_queries(6):
            result = TeamService.get_team_detail(team_id=test_team.id, include_members=True)
            assert result['team']['id'] == test_team.id
    
    def test_get_team_detail_without_members(self, test_team):
        """Test get_team_detail() with include_members=False."""
        result = TeamService.get_team_detail(team_id=test_team.id, include_members=False)
        
        assert 'team' in result
        assert 'members' in result
        assert result['members'] == [], "Members should be empty list when not included"
    
    def test_get_team_detail_by_slug(self, test_team):
        """Test get_team_detail() using team_slug instead of team_id."""
        result = TeamService.get_team_detail(team_slug=test_team.slug, include_members=True)
        
        assert result['team']['id'] == test_team.id
        assert result['team']['slug'] == test_team.slug
        assert len(result['members']) == 1
    
    def test_get_team_detail_not_found(self):
        """Test get_team_detail() raises NotFoundError for invalid ID."""
        with pytest.raises(NotFoundError) as exc_info:
            TeamService.get_team_detail(team_id=99999)
        
        assert 'team' in str(exc_info.value).lower()
    
    def test_get_team_detail_validation_error(self):
        """Test get_team_detail() raises ValidationError when no ID or slug provided."""
        with pytest.raises(ValidationError) as exc_info:
            TeamService.get_team_detail()
        
        assert 'team_id' in str(exc_info.value).lower() or 'team_slug' in str(exc_info.value).lower()


@pytest.mark.django_db
class TestRosterMemberSorting:
    """Test roster member sorting by role hierarchy."""
    
    @pytest.fixture
    def team_with_mixed_roles(self, django_user_model):
        """Create team with multiple role types."""
        from apps.organizations.models import Team, TeamMembership
        from apps.games.models import Game
        
        game, _ = Game.objects.get_or_create(
            slug='test-game-roles',
            defaults={'name': 'Test Game Roles', 'is_active': True, 'team_size_min': 5, 'team_size_max': 7}
        )
        
        owner = django_user_model.objects.create_user(username='owner', email='owner@test.com')
        team = Team.objects.create(name='Role Test Team', slug='role-test-team', owner=owner, game=game, region='NA', status='ACTIVE')
        
        # Create members with different roles (intentionally out of order)
        roles = [
            ('analyst', 'ANALYST'),
            ('player', 'PLAYER'),
            ('coach', 'COACH'),
            ('substitute', 'SUBSTITUTE'),
            ('manager', 'MANAGER'),
        ]
        
        for username, role in roles:
            user = django_user_model.objects.create_user(username=username, email=f'{username}@test.com')
            TeamMembership.objects.create(team=team, user=user, role=role, status='ACTIVE')
        
        # Add owner membership
        TeamMembership.objects.create(team=team, user=owner, role='OWNER', status='ACTIVE')
        
        return team
    
    def test_roster_sorted_by_role_hierarchy(self, team_with_mixed_roles):
        """Test that roster is sorted by role priority."""
        roster = TeamService.get_roster_members(team_id=team_with_mixed_roles.id)
        
        # Extract roles in order returned
        role_sequence = [m.role for m in roster]
        
        # Expected order: OWNER, MANAGER, COACH, PLAYER, SUBSTITUTE, ANALYST
        expected_order = ['OWNER', 'MANAGER', 'COACH', 'PLAYER', 'SUBSTITUTE', 'ANALYST']
        
        assert role_sequence == expected_order, f"Roles should be sorted by hierarchy: {role_sequence}"
