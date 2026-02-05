"""
Journey 3 — Team Manage HQ Roster Mutation Tests

Test roster mutations (add, change role, remove) for Team Manage HQ:
- Add member by email
- Add member by username
- Add member with duplicate check
- Platform rule: one active team per user per game
- Change member role
- Remove member
- Self-removal
- Creator protection (cannot remove creator)
- Role validation
"""

import pytest
from django.test import Client
from apps.organizations.models import Team, TeamMembership
from apps.organizations.choices import MembershipRole, MembershipStatus


@pytest.fixture
def creator(django_db_setup, django_db_blocker):
    """Team creator."""
    from tests.factories import create_user
    with django_db_blocker.unblock():
        return create_user('roster_creator', 'rcreator@test.com')


@pytest.fixture
def manager(django_db_setup, django_db_blocker):
    """Team manager."""
    from tests.factories import create_user
    with django_db_blocker.unblock():
        return create_user('roster_manager', 'rmanager@test.com')


@pytest.fixture
def new_player(django_db_setup, django_db_blocker):
    """User to be added to team."""
    from tests.factories import create_user
    with django_db_blocker.unblock():
        return create_user('new_player', 'newplayer@test.com')


@pytest.fixture
def test_team(django_db_setup, django_db_blocker, creator, manager):
    """Team with creator + manager."""
    from tests.factories import create_independent_team
    with django_db_blocker.unblock():
        team, creator_membership = create_independent_team(
            name='Roster Test Team',
            creator=creator,
            game_id=1,
        )
        
        # Add manager
        TeamMembership.objects.create(
            team=team,
            user=manager,
            role=MembershipRole.MANAGER,
        )
        
        return team


@pytest.mark.django_db
class TestAddMember:
    """Test adding members to team."""
    
    def test_add_member_by_username(self, client, creator, test_team, new_player):
        """Add member by username."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'identifier': new_player.username, 'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['member']['username'] == new_player.username
        assert data['member']['role'] == MembershipRole.PLAYER
        
        # Verify membership created
        assert test_team.vnext_memberships.filter(user=new_player).exists()
    
    def test_add_member_by_email(self, client, creator, test_team, new_player):
        """Add member by email."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'identifier': new_player.email, 'role': MembershipRole.SUBSTITUTE}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['member']['email'] == new_player.email
        assert data['member']['role'] == MembershipRole.SUBSTITUTE
    
    def test_add_member_default_role(self, client, creator, test_team, new_player):
        """Default role is PLAYER when not specified."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'identifier': new_player.username}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['member']['role'] == MembershipRole.PLAYER
    
    def test_add_member_duplicate_rejected(self, client, creator, test_team, manager):
        """Cannot add same user twice."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'identifier': manager.username, 'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 400
        data = response.json()
        assert 'already a member' in data['error'].lower()
    
    def test_add_member_invalid_user(self, client, creator, test_team):
        """Reject non-existent user."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'identifier': 'nonexistent@test.com', 'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 404
        data = response.json()
        assert 'not found' in data['error'].lower()
    
    def test_add_member_invalid_role(self, client, creator, test_team, new_player):
        """Reject invalid role."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'identifier': new_player.username, 'role': 'ADMIN'}  # Invalid
        )
        assert response.status_code == 400
        data = response.json()
        assert 'invalid role' in data['error'].lower()
    
    def test_add_member_missing_identifier(self, client, creator, test_team):
        """Reject missing identifier."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 400
        data = response.json()
        assert 'identifier required' in data['error'].lower()
    
    def test_add_member_blocked_if_user_already_active_on_other_team_same_game(self, client, creator, new_player, django_db_blocker):
        """Platform rule: User cannot have active membership on multiple teams with same game_id."""
        from tests.factories import create_independent_team
        
        with django_db_blocker.unblock():
            # Create Team A (game_id=1) and add new_player as active member
            team_a, _ = create_independent_team(
                name='Team A',
                creator=creator,
                game_id=1,
            )
            TeamMembership.objects.create(
                team=team_a,
                user=new_player,
                role=MembershipRole.PLAYER,
                status=MembershipStatus.ACTIVE,
                game_id=1,
            )
            
            # Create Team B (game_id=1)
            team_b, _ = create_independent_team(
                name='Team B',
                creator=creator,
                game_id=1,
            )
        
        # Attempt to add new_player to Team B (same game_id=1) → should be blocked
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{team_b.slug}/members/add/',
            {'identifier': new_player.username, 'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 400
        data = response.json()
        assert 'already has an active team' in data['error'].lower()
    
    def test_add_member_allowed_if_other_team_different_game(self, client, creator, new_player, django_db_blocker):
        """User can have active membership on teams with different game_id."""
        from tests.factories import create_independent_team
        
        with django_db_blocker.unblock():
            # Create Team A (game_id=1) and add new_player
            team_a, _ = create_independent_team(
                name='Team A Game 1',
                creator=creator,
                game_id=1,
            )
            TeamMembership.objects.create(
                team=team_a,
                user=new_player,
                role=MembershipRole.PLAYER,
                status=MembershipStatus.ACTIVE,
                game_id=1,
            )
            
            # Create Team B (game_id=2 - different game)
            team_b, _ = create_independent_team(
                name='Team B Game 2',
                creator=creator,
                game_id=2,
            )
        
        # Attempt to add new_player to Team B (game_id=2) → should be allowed
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{team_b.slug}/members/add/',
            {'identifier': new_player.username, 'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True


@pytest.mark.django_db
class TestChangeRole:
    """Test changing member roles."""
    
    def test_change_role_success(self, client, creator, test_team, manager):
        """Change member role from MANAGER to COACH."""
        manager_membership = test_team.vnext_memberships.get(user=manager)
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{manager_membership.id}/role/',
            {'role': MembershipRole.COACH}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['member']['role'] == MembershipRole.COACH
        
        # Verify role changed in DB
        manager_membership.refresh_from_db()
        assert manager_membership.role == MembershipRole.COACH
    
    def test_change_role_all_valid_roles(self, client, creator, test_team, manager):
        """Test changing to all valid roles."""
        manager_membership = test_team.vnext_memberships.get(user=manager)
        client.force_login(creator)
        
        valid_roles = [
            MembershipRole.PLAYER,
            MembershipRole.SUBSTITUTE,
            MembershipRole.COACH,
            MembershipRole.ANALYST,
            MembershipRole.SCOUT,
        ]
        
        for role in valid_roles:
            response = client.post(
                f'/api/vnext/teams/{test_team.slug}/members/{manager_membership.id}/role/',
                {'role': role}
            )
            assert response.status_code == 200
            data = response.json()
            assert data['member']['role'] == role
    
    def test_change_role_invalid(self, client, creator, test_team, manager):
        """Reject invalid role."""
        manager_membership = test_team.vnext_memberships.get(user=manager)
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{manager_membership.id}/role/',
            {'role': 'SUPERUSER'}  # Invalid
        )
        assert response.status_code == 400
        data = response.json()
        assert 'invalid role' in data['error'].lower()
    
    def test_change_role_missing_role_param(self, client, creator, test_team, manager):
        """Reject missing role parameter."""
        manager_membership = test_team.vnext_memberships.get(user=manager)
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{manager_membership.id}/role/',
            {}
        )
        assert response.status_code == 400
        data = response.json()
        assert 'role required' in data['error'].lower()
    
    def test_cannot_change_own_role(self, client, creator, test_team):
        """Creator cannot change their own role."""
        creator_membership = test_team.vnext_memberships.get(user=creator)
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{creator_membership.id}/role/',
            {'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 400
        data = response.json()
        assert 'own role' in data['error'].lower()
    
    def test_cannot_change_creator_role(self, client, manager, creator, test_team):
        """Manager cannot change creator's role."""
        creator_membership = test_team.vnext_memberships.get(user=creator)
        client.force_login(manager)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{creator_membership.id}/role/',
            {'role': MembershipRole.COACH}
        )
        assert response.status_code == 400
        data = response.json()
        assert 'creator' in data['error'].lower()


@pytest.mark.django_db
class TestRemoveMember:
    """Test removing members from team."""
    
    def test_remove_member_success(self, client, creator, test_team, manager):
        """Remove member successfully."""
        manager_membership = test_team.vnext_memberships.get(user=manager)
        initial_count = test_team.vnext_memberships.count()
        
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{manager_membership.id}/remove/'
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['removed'] == manager.username
        
        # Verify membership deleted
        assert not test_team.vnext_memberships.filter(user=manager).exists()
        assert test_team.vnext_memberships.count() == initial_count - 1
    
    def test_self_removal_allowed(self, client, manager, test_team):
        """Member can remove themselves."""
        manager_membership = test_team.vnext_memberships.get(user=manager)
        client.force_login(manager)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{manager_membership.id}/remove/'
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_cannot_remove_creator(self, client, manager, creator, test_team):
        """Cannot remove team creator."""
        creator_membership = test_team.vnext_memberships.get(user=creator)
        client.force_login(manager)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{creator_membership.id}/remove/'
        )
        assert response.status_code == 400
        data = response.json()
        assert 'creator' in data['error'].lower()
    
    def test_creator_cannot_remove_self(self, client, creator, test_team):
        """Creator cannot remove themselves (protected)."""
        creator_membership = test_team.vnext_memberships.get(user=creator)
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{creator_membership.id}/remove/'
        )
        assert response.status_code == 400
        data = response.json()
        assert 'creator' in data['error'].lower()
    
    def test_cannot_remove_last_member(self, client, creator, test_team, manager):
        """Cannot remove last member (team must have at least 1)."""
        # Remove manager first
        manager_membership = test_team.vnext_memberships.get(user=manager)
        manager_membership.delete()
        
        # Now try to remove creator (last member)
        creator_membership = test_team.vnext_memberships.get(user=creator)
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{creator_membership.id}/remove/'
        )
        assert response.status_code == 400
        data = response.json()
        assert 'last member' in data['error'].lower()


@pytest.mark.django_db
class TestUpdateSettings:
    """Test updating team settings."""
    
    def test_update_settings_success(self, client, creator, test_team):
        """Update team settings successfully."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/settings/',
            {
                'tagline': 'Victory Through Strategy',
                'description': 'Best team in the region',
                'twitter': '@testteam',
                'discord': 'discord.gg/testteam',
                'website': 'https://testteam.gg',
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'updated' in data['message'].lower()
    
    def test_update_settings_partial(self, client, creator, test_team):
        """Update only some settings (partial update)."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/settings/',
            {'tagline': 'New Tagline Only'}
        )
        assert response.status_code == 200
    
    def test_update_settings_empty_values(self, client, creator, test_team):
        """Allow empty values (clear settings)."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/settings/',
            {'tagline': '', 'twitter': ''}
        )
        assert response.status_code == 200
    
    def test_update_settings_tagline_too_long(self, client, creator, test_team):
        """Reject tagline longer than 100 chars."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/settings/',
            {'tagline': 'x' * 101}
        )
        assert response.status_code == 400
        data = response.json()
        assert '100' in data['error']
    
    def test_update_settings_description_too_long(self, client, creator, test_team):
        """Reject description longer than 500 chars."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/settings/',
            {'description': 'x' * 501}
        )
        assert response.status_code == 400
        data = response.json()
        assert '500' in data['error']
