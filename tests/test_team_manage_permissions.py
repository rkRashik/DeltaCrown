"""
Journey 3 — Team Manage HQ Permission Tests

Test permissions for Team Manage HQ endpoints:
- GET /api/vnext/teams/<slug>/detail/
- POST /api/vnext/teams/<slug>/members/add/
- POST /api/vnext/teams/<slug>/members/<id>/role/
- POST /api/vnext/teams/<slug>/members/<id>/remove/
- POST /api/vnext/teams/<slug>/settings/

Permission rules:
- Creator (team.created_by) can manage everything
- MANAGER role can manage roster and settings
- Organization admins can manage org-owned teams
- Non-members get 403
- Regular members (no manage role) get 403 for manage endpoints
"""

import pytest
from django.test import Client
from apps.organizations.models import Team, TeamMembership
from apps.organizations.choices import MembershipRole


@pytest.fixture
def creator(django_db_setup, django_db_blocker):
    """Team creator (has full permissions via created_by)."""
    from tests.factories import create_user
    with django_db_blocker.unblock():
        return create_user('team_creator', 'creator@test.com')


@pytest.fixture
def manager(django_db_setup, django_db_blocker):
    """Team manager (has manage permissions via MANAGER role)."""
    from tests.factories import create_user
    with django_db_blocker.unblock():
        return create_user('team_manager', 'manager@test.com')


@pytest.fixture
def player(django_db_setup, django_db_blocker):
    """Regular team player (no manage permissions)."""
    from tests.factories import create_user
    with django_db_blocker.unblock():
        return create_user('team_player', 'player@test.com')


@pytest.fixture
def outsider(django_db_setup, django_db_blocker):
    """Non-member user (no permissions)."""
    from tests.factories import create_user
    with django_db_blocker.unblock():
        return create_user('outsider', 'outsider@test.com')


@pytest.fixture
def test_team(django_db_setup, django_db_blocker, creator, manager, player):
    """Independent team with creator + manager + player."""
    from tests.factories import create_independent_team
    with django_db_blocker.unblock():
        team, creator_membership = create_independent_team(
            name='Test Team HQ',
            creator=creator,
            game_id=1,
        )
        
        # Add manager with MANAGER role
        manager_membership = TeamMembership.objects.create(
            team=team,
            user=manager,
            role=MembershipRole.MANAGER,
        )
        
        # Add player with PLAYER role
        player_membership = TeamMembership.objects.create(
            team=team,
            user=player,
            role=MembershipRole.PLAYER,
        )
        
        return team


@pytest.mark.django_db
class TestTeamDetailPermissions:
    """Test GET /api/vnext/teams/<slug>/detail/ permissions."""
    
    def test_creator_can_view_detail(self, client, creator, test_team):
        """Creator can view team detail."""
        client.force_login(creator)
        response = client.get(f'/api/vnext/teams/{test_team.slug}/detail/')
        assert response.status_code == 200
        data = response.json()
        assert data['team']['slug'] == test_team.slug
        assert data['permissions']['is_creator'] is True
        assert data['permissions']['can_manage'] is True
    
    def test_manager_can_view_detail(self, client, manager, test_team):
        """Manager can view team detail."""
        client.force_login(manager)
        response = client.get(f'/api/vnext/teams/{test_team.slug}/detail/')
        assert response.status_code == 200
        data = response.json()
        assert data['permissions']['can_manage'] is True
        assert data['permissions']['is_creator'] is False
    
    def test_player_can_view_detail(self, client, player, test_team):
        """Regular player can view team detail (member access)."""
        client.force_login(player)
        response = client.get(f'/api/vnext/teams/{test_team.slug}/detail/')
        assert response.status_code == 200
        data = response.json()
        assert data['permissions']['can_manage'] is False
        assert data['permissions']['is_creator'] is False
    
    def test_outsider_cannot_view_detail(self, client, outsider, test_team):
        """Non-member gets 403."""
        client.force_login(outsider)
        response = client.get(f'/api/vnext/teams/{test_team.slug}/detail/')
        assert response.status_code == 403
    
    def test_detail_endpoint_returns_unranked_defaults_without_snapshot(self, client, creator, test_team):
        """Detail endpoint returns safe defaults (score=0, tier=UNRANKED) when no ranking snapshot exists."""
        client.force_login(creator)
        response = client.get(f'/api/vnext/teams/{test_team.slug}/detail/')
        assert response.status_code == 200
        data = response.json()
        
        # Verify ranking safe defaults (0-point team rule)
        assert 'ranking' in data
        assert data['ranking']['score'] == 0
        assert data['ranking']['tier'] == 'UNRANKED'
        assert data['ranking']['rank'] is None
        assert response.status_code == 403


@pytest.mark.django_db
class TestAddMemberPermissions:
    """Test POST /api/vnext/teams/<slug>/members/add/ permissions."""
    
    def test_creator_can_add_member(self, client, creator, test_team, outsider):
        """Creator can add members."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'identifier': outsider.username, 'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['member']['username'] == outsider.username
    
    def test_manager_can_add_member(self, client, manager, test_team, outsider):
        """Manager can add members."""
        client.force_login(manager)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'identifier': outsider.email, 'role': MembershipRole.SUBSTITUTE}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_player_cannot_add_member(self, client, player, test_team, outsider):
        """Regular player gets 403."""
        client.force_login(player)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'identifier': outsider.username, 'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 403
    
    def test_outsider_cannot_add_member(self, client, outsider, test_team):
        """Non-member gets 403."""
        client.force_login(outsider)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/add/',
            {'identifier': 'someone@test.com', 'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestChangeRolePermissions:
    """Test POST /api/vnext/teams/<slug>/members/<id>/role/ permissions."""
    
    def test_creator_can_change_role(self, client, creator, test_team, player):
        """Creator can change member roles."""
        player_membership = test_team.vnext_memberships.get(user=player)
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{player_membership.id}/role/',
            {'role': MembershipRole.COACH}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['member']['role'] == MembershipRole.COACH
    
    def test_manager_can_change_role(self, client, manager, test_team, player):
        """Manager can change member roles."""
        player_membership = test_team.vnext_memberships.get(user=player)
        client.force_login(manager)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{player_membership.id}/role/',
            {'role': MembershipRole.ANALYST}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_player_cannot_change_role(self, client, player, manager, test_team):
        """Regular player gets 403."""
        manager_membership = test_team.vnext_memberships.get(user=manager)
        client.force_login(player)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{manager_membership.id}/role/',
            {'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 403
    
    def test_cannot_change_own_role(self, client, manager, test_team):
        """Manager cannot change their own role."""
        manager_membership = test_team.vnext_memberships.get(user=manager)
        client.force_login(manager)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{manager_membership.id}/role/',
            {'role': MembershipRole.COACH}
        )
        assert response.status_code == 400
        data = response.json()
        assert 'own role' in data['error'].lower()
    
    def test_cannot_change_creator_role(self, client, manager, creator, test_team):
        """Cannot change creator's role."""
        creator_membership = test_team.vnext_memberships.get(user=creator)
        client.force_login(manager)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{creator_membership.id}/role/',
            {'role': MembershipRole.PLAYER}
        )
        assert response.status_code == 400
        data = response.json()
        assert 'creator' in data['error'].lower()


@pytest.mark.django_db
class TestRemoveMemberPermissions:
    """Test POST /api/vnext/teams/<slug>/members/<id>/remove/ permissions."""
    
    def test_creator_can_remove_member(self, client, creator, test_team, player):
        """Creator can remove members."""
        player_membership = test_team.vnext_memberships.get(user=player)
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{player_membership.id}/remove/'
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['removed'] == player.username
    
    def test_manager_can_remove_member(self, client, manager, test_team, player):
        """Manager can remove members."""
        player_membership = test_team.vnext_memberships.get(user=player)
        client.force_login(manager)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{player_membership.id}/remove/'
        )
        assert response.status_code == 200
    
    def test_player_cannot_remove_others(self, client, player, manager, test_team):
        """Regular player cannot remove others (403)."""
        manager_membership = test_team.vnext_memberships.get(user=manager)
        client.force_login(player)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{manager_membership.id}/remove/'
        )
        assert response.status_code == 403
    
    def test_player_can_remove_self(self, client, player, test_team):
        """Player can remove themselves (self-removal allowed)."""
        player_membership = test_team.vnext_memberships.get(user=player)
        client.force_login(player)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/members/{player_membership.id}/remove/'
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


@pytest.mark.django_db
class TestUpdateSettingsPermissions:
    """Test POST /api/vnext/teams/<slug>/settings/ permissions."""
    
    def test_creator_can_update_settings(self, client, creator, test_team):
        """Creator can update team settings."""
        client.force_login(creator)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/settings/',
            {'tagline': 'Victory Through Strategy', 'description': 'Best team in the region'}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_manager_can_update_settings(self, client, manager, test_team):
        """Manager can update team settings."""
        client.force_login(manager)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/settings/',
            {'twitter': '@testteam', 'discord': 'discord.gg/test'}
        )
        assert response.status_code == 200
    
    def test_player_cannot_update_settings(self, client, player, test_team):
        """Regular player gets 403."""
        client.force_login(player)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/settings/',
            {'tagline': 'Hacked!'}
        )
        assert response.status_code == 403
    
    def test_outsider_cannot_update_settings(self, client, outsider, test_team):
        """Non-member gets 403."""
        client.force_login(outsider)
        response = client.post(
            f'/api/vnext/teams/{test_team.slug}/settings/',
            {'tagline': 'Hacked!'}
        )
        assert response.status_code == 403
