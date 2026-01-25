"""
Tests for Organization Management API (P3-T5).

Validates:
- Authentication requirements
- Permission enforcement (CEO > MANAGER > SCOUT/ANALYST)
- CEO protection rules (can't change/remove CEO)
- Manager hierarchy rules (managers can't demote other managers)
- Stable error_codes
- Transaction rollback on errors
- Query count optimization (≤5 queries for detail endpoint)
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.test import APIClient
from apps.organizations.models import Organization, OrganizationMembership, Team
from apps.organizations.services.organization_service import OrganizationService

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationDetailAPI(TestCase):
    """Test GET /api/vnext/orgs/<org_slug>/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.ceo_user = User.objects.create_user(username='ceo', email='ceo@test.com', password='pass')
        self.manager_user = User.objects.create_user(username='manager', email='manager@test.com', password='pass')
        self.scout_user = User.objects.create_user(username='scout', email='scout@test.com', password='pass')
        self.outsider_user = User.objects.create_user(username='outsider', email='outsider@test.com', password='pass')
        
        # Create organization
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.ceo_user,
            logo_url='https://logo.png',
            banner_url='https://banner.png',
            primary_color='#FF5733',
            tagline='Test tagline',
            is_verified=True
        )
        
        # Create memberships
        OrganizationMembership.objects.create(organization=self.org, user=self.ceo_user, role='CEO')
        OrganizationMembership.objects.create(organization=self.org, user=self.manager_user, role='MANAGER')
        OrganizationMembership.objects.create(organization=self.org, user=self.scout_user, role='SCOUT')
        
        # Create teams
        self.team = Team.objects.create(
            name='Test Team',
            organization=self.org,
            game_id='valorant',
            region='NA'
        )
    
    def test_requires_authentication(self):
        """Must return 401 if not authenticated."""
        response = self.client.get(f'/api/vnext/orgs/{self.org.slug}/')
        assert response.status_code == 401
    
    def test_success_with_prefetch(self):
        """Must return org data with ≤5 queries."""
        self.client.force_authenticate(user=self.ceo_user)
        
        with self.assertNumQueries(5):  # Performance requirement: ≤5 queries
            response = self.client.get(f'/api/vnext/orgs/{self.org.slug}/')
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate structure
        assert 'org' in data
        assert 'members' in data
        assert 'teams' in data
        
        # Validate org data
        assert data['org']['name'] == 'Test Org'
        assert data['org']['slug'] == 'test-org'
        assert data['org']['logo_url'] == 'https://logo.png'
        assert data['org']['is_verified'] is True
        
        # Validate members
        assert len(data['members']) == 3
        member_usernames = [m['username'] for m in data['members']]
        assert 'ceo' in member_usernames
        assert 'manager' in member_usernames
        assert 'scout' in member_usernames
        
        # Validate teams
        assert len(data['teams']) == 1
        assert data['teams'][0]['name'] == 'Test Team'
    
    def test_org_not_found(self):
        """Must return ORG_NOT_FOUND error code."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.get('/api/vnext/orgs/nonexistent/')
        
        assert response.status_code == 404
        data = response.json()
        assert data['error_code'] == 'ORG_NOT_FOUND'


@pytest.mark.django_db
class TestAddOrganizationMemberAPI(TestCase):
    """Test POST /api/vnext/orgs/<org_slug>/members/add/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        self.ceo_user = User.objects.create_user(username='ceo', email='ceo@test.com', password='pass')
        self.manager_user = User.objects.create_user(username='manager', email='manager@test.com', password='pass')
        self.scout_user = User.objects.create_user(username='scout', email='scout@test.com', password='pass')
        self.new_user = User.objects.create_user(username='newuser', email='new@test.com', password='pass')
        
        self.org = Organization.objects.create(name='Test Org', slug='test-org', ceo=self.ceo_user)
        
        OrganizationMembership.objects.create(organization=self.org, user=self.ceo_user, role='CEO')
        OrganizationMembership.objects.create(organization=self.org, user=self.manager_user, role='MANAGER')
        OrganizationMembership.objects.create(organization=self.org, user=self.scout_user, role='SCOUT')
    
    def test_requires_authentication(self):
        """Must return 401 if not authenticated."""
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/add/', {'user_id': self.new_user.id, 'role': 'SCOUT'})
        assert response.status_code == 401
    
    def test_ceo_can_add_member(self):
        """CEO must be able to add members."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/add/', {'user_id': self.new_user.id, 'role': 'ANALYST'})
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'membership_id' in data
        
        # Verify membership created
        membership = OrganizationMembership.objects.filter(organization=self.org, user=self.new_user).first()
        assert membership is not None
        assert membership.role == 'ANALYST'
    
    def test_manager_can_add_member(self):
        """MANAGER must be able to add members."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/add/', {'user_id': self.new_user.id, 'role': 'SCOUT'})
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_scout_cannot_add_member(self):
        """SCOUT must not be able to add members (returns 403)."""
        self.client.force_authenticate(user=self.scout_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/add/', {'user_id': self.new_user.id, 'role': 'ANALYST'})
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'
    
    def test_invalid_role(self):
        """Must return INVALID_ROLE error code."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/add/', {'user_id': self.new_user.id, 'role': 'INVALID_ROLE'})
        
        assert response.status_code == 400
        data = response.json()
        assert data['error_code'] == 'INVALID_ROLE'
    
    def test_rollback_on_error(self):
        """Must rollback transaction if error occurs."""
        self.client.force_authenticate(user=self.ceo_user)
        
        # Try to add user with invalid role
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/add/', {'user_id': self.new_user.id, 'role': 'CEO'})
        
        # Verify no membership created
        membership = OrganizationMembership.objects.filter(organization=self.org, user=self.new_user).first()
        assert membership is None


@pytest.mark.django_db
class TestUpdateMemberRoleAPI(TestCase):
    """Test POST /api/vnext/orgs/<org_slug>/members/<member_id>/role/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        self.ceo_user = User.objects.create_user(username='ceo', email='ceo@test.com', password='pass')
        self.manager1_user = User.objects.create_user(username='manager1', email='manager1@test.com', password='pass')
        self.manager2_user = User.objects.create_user(username='manager2', email='manager2@test.com', password='pass')
        self.scout_user = User.objects.create_user(username='scout', email='scout@test.com', password='pass')
        
        self.org = Organization.objects.create(name='Test Org', slug='test-org', ceo=self.ceo_user)
        
        self.ceo_membership = OrganizationMembership.objects.create(organization=self.org, user=self.ceo_user, role='CEO')
        self.manager1_membership = OrganizationMembership.objects.create(organization=self.org, user=self.manager1_user, role='MANAGER')
        self.manager2_membership = OrganizationMembership.objects.create(organization=self.org, user=self.manager2_user, role='MANAGER')
        self.scout_membership = OrganizationMembership.objects.create(organization=self.org, user=self.scout_user, role='SCOUT')
    
    def test_requires_authentication(self):
        """Must return 401 if not authenticated."""
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.scout_membership.id}/role/', {'role': 'ANALYST'})
        assert response.status_code == 401
    
    def test_cannot_change_ceo_role(self):
        """Must not allow changing CEO role (HARD RULE)."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.ceo_membership.id}/role/', {'role': 'MANAGER'})
        
        assert response.status_code == 400
        data = response.json()
        assert data['error_code'] == 'CANNOT_CHANGE_CEO'
        
        # Verify CEO role unchanged
        self.ceo_membership.refresh_from_db()
        assert self.ceo_membership.role == 'CEO'
    
    def test_ceo_can_change_manager_role(self):
        """CEO must be able to change manager role."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.manager1_membership.id}/role/', {'role': 'SCOUT'})
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify role changed
        self.manager1_membership.refresh_from_db()
        assert self.manager1_membership.role == 'SCOUT'
    
    def test_manager_cannot_demote_other_manager(self):
        """MANAGER must not be able to demote another MANAGER."""
        self.client.force_authenticate(user=self.manager1_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.manager2_membership.id}/role/', {'role': 'SCOUT'})
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'
        
        # Verify role unchanged
        self.manager2_membership.refresh_from_db()
        assert self.manager2_membership.role == 'MANAGER'
    
    def test_manager_can_change_scout_role(self):
        """MANAGER must be able to change SCOUT role."""
        self.client.force_authenticate(user=self.manager1_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.scout_membership.id}/role/', {'role': 'ANALYST'})
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify role changed
        self.scout_membership.refresh_from_db()
        assert self.scout_membership.role == 'ANALYST'
    
    def test_scout_cannot_change_roles(self):
        """SCOUT must not be able to change any roles."""
        self.client.force_authenticate(user=self.scout_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.manager1_membership.id}/role/', {'role': 'SCOUT'})
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'


@pytest.mark.django_db
class TestRemoveOrganizationMemberAPI(TestCase):
    """Test POST /api/vnext/orgs/<org_slug>/members/<member_id>/remove/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        self.ceo_user = User.objects.create_user(username='ceo', email='ceo@test.com', password='pass')
        self.manager1_user = User.objects.create_user(username='manager1', email='manager1@test.com', password='pass')
        self.manager2_user = User.objects.create_user(username='manager2', email='manager2@test.com', password='pass')
        self.scout_user = User.objects.create_user(username='scout', email='scout@test.com', password='pass')
        
        self.org = Organization.objects.create(name='Test Org', slug='test-org', ceo=self.ceo_user)
        
        self.ceo_membership = OrganizationMembership.objects.create(organization=self.org, user=self.ceo_user, role='CEO')
        self.manager1_membership = OrganizationMembership.objects.create(organization=self.org, user=self.manager1_user, role='MANAGER')
        self.manager2_membership = OrganizationMembership.objects.create(organization=self.org, user=self.manager2_user, role='MANAGER')
        self.scout_membership = OrganizationMembership.objects.create(organization=self.org, user=self.scout_user, role='SCOUT')
    
    def test_requires_authentication(self):
        """Must return 401 if not authenticated."""
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.scout_membership.id}/remove/')
        assert response.status_code == 401
    
    def test_cannot_remove_ceo(self):
        """Must not allow removing CEO (HARD RULE)."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.ceo_membership.id}/remove/')
        
        assert response.status_code == 400
        data = response.json()
        assert data['error_code'] == 'CANNOT_REMOVE_CEO'
        
        # Verify CEO still exists
        assert OrganizationMembership.objects.filter(id=self.ceo_membership.id).exists()
    
    def test_ceo_can_remove_manager(self):
        """CEO must be able to remove managers."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.manager1_membership.id}/remove/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify membership deleted
        assert not OrganizationMembership.objects.filter(id=self.manager1_membership.id).exists()
    
    def test_manager_cannot_remove_other_manager(self):
        """MANAGER must not be able to remove another MANAGER."""
        self.client.force_authenticate(user=self.manager1_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.manager2_membership.id}/remove/')
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'
        
        # Verify membership still exists
        assert OrganizationMembership.objects.filter(id=self.manager2_membership.id).exists()
    
    def test_manager_can_remove_scout(self):
        """MANAGER must be able to remove SCOUT."""
        self.client.force_authenticate(user=self.manager1_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.scout_membership.id}/remove/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify membership deleted
        assert not OrganizationMembership.objects.filter(id=self.scout_membership.id).exists()
    
    def test_scout_cannot_remove_members(self):
        """SCOUT must not be able to remove any members."""
        self.client.force_authenticate(user=self.scout_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/members/{self.manager1_membership.id}/remove/')
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'


@pytest.mark.django_db
class TestUpdateOrganizationSettingsAPI(TestCase):
    """Test POST /api/vnext/orgs/<org_slug>/settings/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        self.ceo_user = User.objects.create_user(username='ceo', email='ceo@test.com', password='pass')
        self.manager_user = User.objects.create_user(username='manager', email='manager@test.com', password='pass')
        self.scout_user = User.objects.create_user(username='scout', email='scout@test.com', password='pass')
        
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.ceo_user,
            logo_url='https://old-logo.png',
            banner_url='https://old-banner.png',
            primary_color='#000000',
            tagline='Old tagline'
        )
        
        OrganizationMembership.objects.create(organization=self.org, user=self.ceo_user, role='CEO')
        OrganizationMembership.objects.create(organization=self.org, user=self.manager_user, role='MANAGER')
        OrganizationMembership.objects.create(organization=self.org, user=self.scout_user, role='SCOUT')
    
    def test_requires_authentication(self):
        """Must return 401 if not authenticated."""
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/settings/', {'tagline': 'New tagline'})
        assert response.status_code == 401
    
    def test_ceo_can_update_settings(self):
        """CEO must be able to update all settings."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/settings/', {
            'logo_url': 'https://new-logo.png',
            'banner_url': 'https://new-banner.png',
            'primary_color': '#FF5733',
            'tagline': 'New tagline'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify settings updated
        self.org.refresh_from_db()
        assert self.org.logo_url == 'https://new-logo.png'
        assert self.org.banner_url == 'https://new-banner.png'
        assert self.org.primary_color == '#FF5733'
        assert self.org.tagline == 'New tagline'
    
    def test_manager_can_update_settings(self):
        """MANAGER must be able to update settings."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/settings/', {
            'tagline': 'Manager updated tagline'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify tagline updated
        self.org.refresh_from_db()
        assert self.org.tagline == 'Manager updated tagline'
    
    def test_scout_cannot_update_settings(self):
        """SCOUT must not be able to update settings."""
        self.client.force_authenticate(user=self.scout_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/settings/', {
            'tagline': 'Scout trying to update'
        })
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INSUFFICIENT_PERMISSIONS'
        
        # Verify tagline unchanged
        self.org.refresh_from_db()
        assert self.org.tagline == 'Old tagline'
    
    def test_invalid_color_format(self):
        """Must return INVALID_COLOR error code for bad hex format."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/settings/', {
            'primary_color': 'not-a-hex-color'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert data['error_code'] == 'INVALID_COLOR'
    
    def test_partial_update(self):
        """Must allow updating only specific fields."""
        self.client.force_authenticate(user=self.ceo_user)
        response = self.client.post(f'/api/vnext/orgs/{self.org.slug}/settings/', {
            'tagline': 'Only update tagline'
        })
        
        assert response.status_code == 200
        
        # Verify only tagline changed
        self.org.refresh_from_db()
        assert self.org.tagline == 'Only update tagline'
        assert self.org.logo_url == 'https://old-logo.png'  # Unchanged
        assert self.org.banner_url == 'https://old-banner.png'  # Unchanged
        assert self.org.primary_color == '#000000'  # Unchanged
