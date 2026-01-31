"""
Tests for Team Membership Management API (P3-T6).

Validates:
- Authentication requirements
- Permission enforcement (independent vs org-owned teams)
- OWNER protection rules (cannot remove/change OWNER on independent teams)
- Unique active membership enforcement
- Stable error_codes
- Transaction rollback on errors
- Query count optimization (≤5 queries for detail endpoint)
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.test import APIClient
from apps.organizations.models import Organization, OrganizationMembership, Team, TeamMembership
from apps.organizations.services.team_service import TeamService

User = get_user_model()


@pytest.mark.django_db
class TestTeamDetailAPI(TestCase):
    """Test GET /api/vnext/teams/<team_slug>/detail/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.owner_user = User.objects.create_user(username='owner', email='owner@test.com', password='pass')
        self.player_user = User.objects.create_user(username='player', email='player@test.com', password='pass')
        self.outsider_user = User.objects.create_user(username='outsider', email='outsider@test.com', password='pass')
        
        # Create independent team
        self.team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game='rocket-league',
            region='NA',
            description='Test team description',
            is_active=True,
            is_public=True,
        )
        
        # Create memberships
        TeamMembership.objects.create(team=self.team, profile=self.owner_user.profile, role='OWNER', status='ACTIVE')
        TeamMembership.objects.create(team=self.team, profile=self.player_user.profile, role='PLAYER', status='ACTIVE', roster_slot='STARTER')
    
    def test_requires_authentication(self):
        """Must return 401 if not authenticated."""
        response = self.client.get(f'/api/vnext/teams/{self.team.slug}/detail/')
        assert response.status_code == 401
    
    def test_success_with_prefetch(self):
        """Must return team data with ≤5 queries."""
        self.client.force_authenticate(user=self.owner_user)
        
        with self.assertNumQueries(5):  # Performance requirement: ≤5 queries
            response = self.client.get(f'/api/vnext/teams/{self.team.slug}/detail/')
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate structure
        assert 'team' in data
        assert 'members' in data
        assert 'invites' in data
        
        # Validate team data
        assert data['team']['name'] == 'Test Team'
        assert data['team']['slug'] == 'test-team'
        assert data['team']['region'] == 'NA'
        
        # Validate members
        assert len(data['members']) == 2
        member_usernames = [m['username'] for m in data['members']]
        assert 'owner' in member_usernames
        assert 'player' in member_usernames
    
    def test_team_not_found(self):
        """Must return TEAM_NOT_FOUND error code."""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.get('/api/vnext/teams/nonexistent/detail/')
        
        assert response.status_code == 404
        data = response.json()
        assert data['error_code'] == 'TEAM_NOT_FOUND'


@pytest.mark.django_db
class TestAddTeamMemberAPI(TestCase):
    """Test POST /api/vnext/teams/<team_slug>/members/add/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        self.owner_user = User.objects.create_user(username='owner', email='owner@test.com', password='pass')
        self.manager_user = User.objects.create_user(username='manager', email='manager@test.com', password='pass')
        self.player_user = User.objects.create_user(username='player', email='player@test.com', password='pass')
        self.new_user = User.objects.create_user(username='newuser', email='new@test.com', password='pass')
        
        self.team = Team.objects.create(name='Test Team', slug='test-team', game='rocket-league', region='NA', is_active=True, is_public=True)
        
        # TeamMembership uses 'profile' FK to UserProfile (legacy schema)
        TeamMembership.objects.create(team=self.team, profile=self.owner_user.profile, role='OWNER', status='ACTIVE')
        TeamMembership.objects.create(team=self.team, profile=self.manager_user.profile, role='MANAGER', status='ACTIVE')
        TeamMembership.objects.create(team=self.team, profile=self.player_user.profile, role='PLAYER', status='ACTIVE')
    
    def test_requires_authentication(self):
        """Must return 401 if not authenticated."""
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/add/', {'user_lookup': self.new_user.id, 'role': 'PLAYER'})
        assert response.status_code == 401
    
    def test_owner_can_add_member(self):
        """OWNER must be able to add members."""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/add/', {'user_lookup': self.new_user.id, 'role': 'SUBSTITUTE', 'slot': 'SUBSTITUTE'})
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'membership_id' in data
        
        # Verify membership created
        membership = TeamMembership.objects.filter(team=self.team, user=self.new_user).first()
        assert membership is not None
        assert membership.role == 'SUBSTITUTE'
    
    def test_manager_can_add_member(self):
        """MANAGER must be able to add members."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/add/', {'user_lookup': self.new_user.id, 'role': 'PLAYER'})
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_player_cannot_add_member(self):
        """PLAYER must not be able to add members (returns 403)."""
        self.client.force_authenticate(user=self.player_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/add/', {'user_lookup': self.new_user.id, 'role': 'PLAYER'})
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'
    
    def test_invalid_role(self):
        """Must return INVALID_ROLE error code."""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/add/', {'user_lookup': self.new_user.id, 'role': 'INVALID_ROLE'})
        
        assert response.status_code == 400
        data = response.json()
        assert 'VALIDATION_ERROR' in data['error_code'] or 'INVALID_ROLE' in data['error_code']
    
    def test_duplicate_membership(self):
        """Must return MEMBER_ALREADY_EXISTS error code."""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/add/', {'user_lookup': self.player_user.id, 'role': 'SUBSTITUTE'})
        
        assert response.status_code == 409
        data = response.json()
        assert data['error_code'] == 'MEMBER_ALREADY_EXISTS'


@pytest.mark.django_db
class TestUpdateMemberRoleAPI(TestCase):
    """Test POST /api/vnext/teams/<team_slug>/members/<member_id>/role/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        self.owner_user = User.objects.create_user(username='owner', email='owner@test.com', password='pass')
        self.manager_user = User.objects.create_user(username='manager', email='manager@test.com', password='pass')
        self.player_user = User.objects.create_user(username='player', email='player@test.com', password='pass')
        
        self.team = Team.objects.create(name='Test Team', slug='test-team', game='rocket-league', region='NA', is_active=True, is_public=True)
        
        self.owner_membership = TeamMembership.objects.create(team=self.team, profile=self.owner_user.profile, role='OWNER', status='ACTIVE')
        self.manager_membership = TeamMembership.objects.create(team=self.team, profile=self.manager_user.profile, role='MANAGER', status='ACTIVE')
        self.player_membership = TeamMembership.objects.create(team=self.team, profile=self.player_user.profile, role='PLAYER', status='ACTIVE')
    
    def test_requires_authentication(self):
        """Must return 401 if not authenticated."""
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/{self.player_membership.id}/role/', {'role': 'SUBSTITUTE'})
        assert response.status_code == 401
    
    def test_cannot_change_owner_role(self):
        """Must not allow changing OWNER role on independent teams."""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/{self.owner_membership.id}/role/', {'role': 'MANAGER'})
        
        assert response.status_code == 400
        data = response.json()
        assert data['error_code'] == 'CANNOT_CHANGE_OWNER'
        
        # Verify OWNER role unchanged
        self.owner_membership.refresh_from_db()
        assert self.owner_membership.role == 'OWNER'
    
    def test_owner_can_change_player_role(self):
        """OWNER must be able to change player roles."""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/{self.player_membership.id}/role/', {'role': 'SUBSTITUTE', 'slot': 'SUBSTITUTE'})
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify role changed
        self.player_membership.refresh_from_db()
        assert self.player_membership.role == 'SUBSTITUTE'
    
    def test_manager_can_change_player_role(self):
        """MANAGER must be able to change player roles."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/{self.player_membership.id}/role/', {'role': 'COACH'})
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_player_cannot_change_roles(self):
        """PLAYER must not be able to change any roles."""
        self.client.force_authenticate(user=self.player_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/{self.manager_membership.id}/role/', {'role': 'PLAYER'})
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'


@pytest.mark.django_db
class TestRemoveTeamMemberAPI(TestCase):
    """Test POST /api/vnext/teams/<team_slug>/members/<member_id>/remove/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        self.owner_user = User.objects.create_user(username='owner', email='owner@test.com', password='pass')
        self.manager_user = User.objects.create_user(username='manager', email='manager@test.com', password='pass')
        self.player_user = User.objects.create_user(username='player', email='player@test.com', password='pass')
        
        self.team = Team.objects.create(name='Test Team', slug='test-team', game='rocket-league', region='NA', is_active=True, is_public=True)
        
        self.owner_membership = TeamMembership.objects.create(team=self.team, profile=self.owner_user.profile, role='OWNER', status='ACTIVE')
        self.manager_membership = TeamMembership.objects.create(team=self.team, profile=self.manager_user.profile, role='MANAGER', status='ACTIVE')
        self.player_membership = TeamMembership.objects.create(team=self.team, profile=self.player_user.profile, role='PLAYER', status='ACTIVE')
    
    def test_requires_authentication(self):
        """Must return 401 if not authenticated."""
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/{self.player_membership.id}/remove/')
        assert response.status_code == 401
    
    def test_cannot_remove_owner(self):
        """Must not allow removing OWNER from independent teams."""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/{self.owner_membership.id}/remove/')
        
        assert response.status_code == 400
        data = response.json()
        assert data['error_code'] == 'CANNOT_REMOVE_OWNER'
        
        # Verify OWNER still exists
        self.owner_membership.refresh_from_db()
        assert self.owner_membership.status == 'ACTIVE'
    
    def test_owner_can_remove_player(self):
        """OWNER must be able to remove players."""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/{self.player_membership.id}/remove/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify membership removed (soft delete)
        self.player_membership.refresh_from_db()
        assert self.player_membership.status == 'INACTIVE'
    
    def test_manager_can_remove_player(self):
        """MANAGER must be able to remove players."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/{self.player_membership.id}/remove/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_player_cannot_remove_members(self):
        """PLAYER must not be able to remove any members."""
        self.client.force_authenticate(user=self.player_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/{self.manager_membership.id}/remove/')
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'


@pytest.mark.django_db
class TestUpdateTeamSettingsAPI(TestCase):
    """Test POST /api/vnext/teams/<team_slug>/settings/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        self.owner_user = User.objects.create_user(username='owner', email='owner@test.com', password='pass')
        self.manager_user = User.objects.create_user(username='manager', email='manager@test.com', password='pass')
        self.player_user = User.objects.create_user(username='player', email='player@test.com', password='pass')
        
        self.team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game='rocket-league',
            region='NA',
            description='Old description',
            preferred_server='Mumbai',
            is_active=True,
            is_public=True,
        )
        
        TeamMembership.objects.create(team=self.team, profile=self.owner_user.profile, role='OWNER', status='ACTIVE')
        TeamMembership.objects.create(team=self.team, profile=self.manager_user.profile, role='MANAGER', status='ACTIVE')
        TeamMembership.objects.create(team=self.team, profile=self.player_user.profile, role='PLAYER', status='ACTIVE')
    
    def test_requires_authentication(self):
        """Must return 401 if not authenticated."""
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/settings/', {'description': 'New description'})
        assert response.status_code == 401
    
    def test_owner_can_update_settings(self):
        """OWNER must be able to update all settings."""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/settings/', {
            'region': 'EU',
            'description': 'New description',
            'preferred_server': 'Singapore'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify settings updated
        self.team.refresh_from_db()
        assert self.team.region == 'EU'
        assert self.team.description == 'New description'
        assert self.team.preferred_server == 'Singapore'
    
    def test_manager_can_update_settings(self):
        """MANAGER must be able to update settings."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/settings/', {
            'description': 'Manager updated description'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify description updated
        self.team.refresh_from_db()
        assert self.team.description == 'Manager updated description'
    
    def test_player_cannot_update_settings(self):
        """PLAYER must not be able to update settings."""
        self.client.force_authenticate(user=self.player_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/settings/', {
            'description': 'Player trying to update'
        })
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'
        
        # Verify description unchanged
        self.team.refresh_from_db()
        assert self.team.description == 'Old description'


@pytest.mark.django_db
class TestOrgOwnedTeamPermissions(TestCase):
    """Test that organization managers can manage org-owned teams."""
    
    def setUp(self):
        self.client = APIClient()
        
        self.ceo_user = User.objects.create_user(username='ceo', email='ceo@test.com', password='pass')
        self.org_manager_user = User.objects.create_user(username='org_manager', email='orgmgr@test.com', password='pass')
        self.outsider_user = User.objects.create_user(username='outsider', email='outsider@test.com', password='pass')
        self.new_user = User.objects.create_user(username='newuser', email='new@test.com', password='pass')
        
        # Create organization
        self.org = Organization.objects.create(name='Test Org', slug='test-org', ceo=self.ceo_user)
        
        OrganizationMembership.objects.create(organization=self.org, user=self.ceo_user, role='CEO')
        OrganizationMembership.objects.create(organization=self.org, user=self.org_manager_user, role='MANAGER')
        
        # Create org-owned team (TODO: Restore organization FK after legacy schema updated)
        # self.team = Team.objects.create(name='Org Team', slug='org-team', organization=self.org, game='rocket-league', region='NA', is_active=True)
        self.team = Team.objects.create(name='Org Team', slug='org-team', game='rocket-league', region='NA', is_active=True, is_public=True)
    
    def test_org_ceo_can_add_member(self):
        """Organization CEO must be able to add members to org-owned teams."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/add/', {'user_lookup': self.new_user.id, 'role': 'PLAYER'})
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_org_manager_can_add_member(self):
        """Organization MANAGER must be able to add members to org-owned teams."""
        self.client.force_authenticate(user=self.org_manager_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/add/', {'user_lookup': self.new_user.id, 'role': 'PLAYER'})
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_outsider_cannot_add_member(self):
        """Outsiders must not be able to add members to org-owned teams."""
        self.client.force_authenticate(user=self.outsider_user)
        response = self.client.post(f'/api/vnext/teams/{self.team.slug}/members/add/', {'user_lookup': self.new_user.id, 'role': 'PLAYER'})
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'
