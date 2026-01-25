"""
Tests for vNext Organization and Team Creation API Endpoints.

Tests verify:
- Proper HTTP status codes (201, 400, 403, 404, 409, 500)
- Error code stability
- Validation error handling
- Permission enforcement
- Feature flag checks
- Proper database state after success/failure
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework import status as http_status

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    Team,
    TeamMembership,
)

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationCreationAPI:
    """Test POST /api/vnext/organizations/create/"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_create_organization_success_minimal(self):
        """Test creating organization with minimal required fields"""
        response = self.client.post('/api/vnext/organizations/create/', {
            'name': 'SYNTAX Esports',
        }, format='json')
        
        assert response.status_code == http_status.HTTP_201_CREATED
        assert 'organization_id' in response.data
        assert 'organization_slug' in response.data
        assert response.data['organization_slug'] == 'syntax-esports'
        
        # Verify database state
        org = Organization.objects.get(id=response.data['organization_id'])
        assert org.name == 'SYNTAX Esports'
        assert org.slug == 'syntax-esports'
        
        # Verify CEO membership created
        membership = OrganizationMembership.objects.get(
            organization=org,
            user=self.user
        )
        assert membership.role == 'CEO'
        assert membership.status == 'ACTIVE'
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_create_organization_success_with_slug(self):
        """Test creating organization with custom slug"""
        response = self.client.post('/api/vnext/organizations/create/', {
            'name': 'Team Liquid',
            'slug': 'tl',
        }, format='json')
        
        assert response.status_code == http_status.HTTP_201_CREATED
        assert response.data['organization_slug'] == 'tl'
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_create_organization_validation_error_name_required(self):
        """Test validation error when name is missing"""
        response = self.client.post('/api/vnext/organizations/create/', {
            # Missing 'name'
        }, format='json')
        
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.data['error_code'] == 'validation_error'
        assert 'details' in response.data
        assert 'name' in response.data['details']
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_create_organization_conflict_duplicate_name(self):
        """Test conflict error when organization name already exists"""
        # Create first organization
        Organization.objects.create(
            name='SYNTAX',
            slug='syntax',
            ceo=self.user
        )
        
        # Try to create another with same name
        response = self.client.post('/api/vnext/organizations/create/', {
            'name': 'SYNTAX',
        }, format='json')
        
        assert response.status_code == http_status.HTTP_409_CONFLICT
        assert response.data['error_code'] == 'organization_already_exists'
        assert 'safe_message' in response.data
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=False,
    )
    def test_create_organization_forbidden_adapter_disabled(self):
        """Test 403 when vNext adapter is disabled"""
        response = self.client.post('/api/vnext/organizations/create/', {
            'name': 'Test Org',
        }, format='json')
        
        assert response.status_code == http_status.HTTP_403_FORBIDDEN
        assert response.data['error_code'] == 'vnext_creation_disabled'
        assert 'safe_message' in response.data
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_FORCE_LEGACY=True,
    )
    def test_create_organization_forbidden_force_legacy(self):
        """Test 403 when FORCE_LEGACY emergency mode is active"""
        response = self.client.post('/api/vnext/organizations/create/', {
            'name': 'Test Org',
        }, format='json')
        
        assert response.status_code == http_status.HTTP_403_FORBIDDEN
        assert response.data['error_code'] == 'vnext_creation_disabled'
    
    def test_create_organization_unauthenticated(self):
        """Test 401 when user is not authenticated"""
        self.client.force_authenticate(user=None)
        
        response = self.client.post('/api/vnext/organizations/create/', {
            'name': 'Test Org',
        }, format='json')
        
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTeamCreationAPI:
    """Test POST /api/vnext/teams/create/"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_create_independent_team_success(self):
        """Test creating independent team (user-owned)"""
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Cloud9 Blue',
            'game_id': 1,
            'region': 'NA',
        }, format='json')
        
        assert response.status_code == http_status.HTTP_201_CREATED
        assert 'team_id' in response.data
        assert 'team_slug' in response.data
        assert 'team_url' in response.data
        assert response.data['team_slug'] == 'cloud9-blue'
        
        # Verify database state
        team = Team.objects.get(id=response.data['team_id'])
        assert team.name == 'Cloud9 Blue'
        assert team.owner == self.user
        assert team.organization is None
        assert team.game_id == 1
        assert team.region == 'NA'
        assert team.status == 'ACTIVE'
        
        # Verify owner membership created
        membership = TeamMembership.objects.get(
            team=team,
            user=self.user
        )
        assert membership.role == 'OWNER'
        assert membership.status == 'ACTIVE'
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_create_org_team_success_ceo(self):
        """Test creating org-owned team as CEO"""
        # Create organization
        org = Organization.objects.create(
            name='SYNTAX',
            slug='syntax',
            ceo=self.user
        )
        OrganizationMembership.objects.create(
            organization=org,
            user=self.user,
            role='CEO',
            status='ACTIVE'
        )
        
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Protocol V',
            'game_id': 1,
            'organization_id': org.id,
            'region': 'Bangladesh',
        }, format='json')
        
        assert response.status_code == http_status.HTTP_201_CREATED
        
        # Verify database state
        team = Team.objects.get(id=response.data['team_id'])
        assert team.organization == org
        assert team.owner is None  # Org-owned team has no owner
        assert team.name == 'Protocol V'
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_create_org_team_forbidden_not_ceo(self):
        """Test 403 when non-CEO tries to create org team"""
        # Create organization with different CEO
        other_user = User.objects.create_user(
            username='ceo',
            email='ceo@example.com'
        )
        org = Organization.objects.create(
            name='SYNTAX',
            slug='syntax',
            ceo=other_user
        )
        OrganizationMembership.objects.create(
            organization=org,
            user=other_user,
            role='CEO',
            status='ACTIVE'
        )
        
        # Try to create team as non-member
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Protocol V',
            'game_id': 1,
            'organization_id': org.id,
            'region': 'Bangladesh',
        }, format='json')
        
        assert response.status_code == http_status.HTTP_403_FORBIDDEN
        assert response.data['error_code'] == 'permission_denied'
        assert 'safe_message' in response.data
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_create_team_validation_error_missing_fields(self):
        """Test validation error when required fields are missing"""
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Test Team',
            # Missing game_id
        }, format='json')
        
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.data['error_code'] == 'validation_error'
        assert 'details' in response.data
        assert 'game_id' in response.data['details']
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_create_team_not_found_organization(self):
        """Test 404 when organization_id doesn't exist"""
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Test Team',
            'game_id': 1,
            'organization_id': 99999,  # Non-existent
        }, format='json')
        
        assert response.status_code == http_status.HTTP_404_NOT_FOUND
        assert response.data['error_code'] == 'organization_not_found'
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=False,
    )
    def test_create_team_forbidden_adapter_disabled(self):
        """Test 403 when vNext adapter is disabled"""
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Test Team',
            'game_id': 1,
        }, format='json')
        
        assert response.status_code == http_status.HTTP_403_FORBIDDEN
        assert response.data['error_code'] == 'vnext_creation_disabled'
    
    def test_create_team_unauthenticated(self):
        """Test 401 when user is not authenticated"""
        self.client.force_authenticate(user=None)
        
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Test Team',
            'game_id': 1,
        }, format='json')
        
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAPIErrorCodes:
    """Test that error codes are stable and follow contract"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_all_errors_have_safe_message(self):
        """Test that all error responses include safe_message field"""
        # Test validation error
        response = self.client.post('/api/vnext/organizations/create/', {
            # Missing required field
        }, format='json')
        assert 'safe_message' in response.data or 'message' in response.data
        
        # Test not found error
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Test',
            'game_id': 1,
            'organization_id': 99999,
        }, format='json')
        assert 'safe_message' in response.data
        
        # Test permission denied
        other_user = User.objects.create_user(username='other')
        org = Organization.objects.create(
            name='Test',
            slug='test',
            ceo=other_user
        )
        OrganizationMembership.objects.create(
            organization=org,
            user=other_user,
            role='CEO',
            status='ACTIVE'
        )
        
        response = self.client.post('/api/vnext/teams/create/', {
            'name': 'Test',
            'game_id': 1,
            'organization_id': org.id,
        }, format='json')
        assert 'safe_message' in response.data
    
    @override_settings(
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    def test_all_errors_have_error_code(self):
        """Test that all error responses include error_code field"""
        # Test various error scenarios
        error_responses = []
        
        # Validation error
        resp = self.client.post('/api/vnext/organizations/create/', {}, format='json')
        error_responses.append(resp)
        
        # Not found
        resp = self.client.post('/api/vnext/teams/create/', {
            'name': 'T', 'game_id': 1, 'organization_id': 99999
        }, format='json')
        error_responses.append(resp)
        
        for response in error_responses:
            assert 'error_code' in response.data
            assert isinstance(response.data['error_code'], str)
            assert len(response.data['error_code']) > 0
