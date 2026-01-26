"""
Tests for organization creation endpoints (P3-T7).

Test Coverage:
- Validation endpoints (name, badge, slug)
- Creation endpoint (success + failure cases)
- Field validation
- Authentication requirements
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.organizations.models import Organization, OrganizationProfile, OrganizationMembership

User = get_user_model()


@pytest.mark.django_db
class TestValidateOrganizationName:
    """Tests for /api/vnext/organizations/validate-name/"""
    
    def test_validate_name_available(self):
        """Test that unique name is marked available"""
        user = User.objects.create_user(username='testuser', password='pass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:validate_organization_name')
        response = client.get(url, {'name': 'Unique Org Name'})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['ok'] is True
        assert response.data['available'] is True
    
    def test_validate_name_taken(self):
        """Test that existing name is marked unavailable"""
        user = User.objects.create_user(username='testuser', password='pass123')
        Organization.objects.create(name='Existing Org', slug='existing-org', ceo=user)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:validate_organization_name')
        response = client.get(url, {'name': 'Existing Org'})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['ok'] is False
        assert response.data['available'] is False
        assert 'name' in response.data['field_errors']
    
    def test_validate_name_case_insensitive(self):
        """Test that name uniqueness check is case-insensitive"""
        user = User.objects.create_user(username='testuser', password='pass123')
        Organization.objects.create(name='TestOrg', slug='testorg', ceo=user)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:validate_organization_name')
        response = client.get(url, {'name': 'TESTORG'})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['available'] is False
    
    def test_validate_name_too_short(self):
        """Test that short names are rejected"""
        user = User.objects.create_user(username='testuser', password='pass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:validate_organization_name')
        response = client.get(url, {'name': 'AB'})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['available'] is False
        assert 'name' in response.data['field_errors']
    
    def test_validate_name_requires_auth(self):
        """Test that authentication is required"""
        client = APIClient()
        url = reverse('organizations_api:validate_organization_name')
        response = client.get(url, {'name': 'TestOrg'})
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestValidateOrganizationSlug:
    """Tests for /api/vnext/organizations/validate-slug/"""
    
    def test_validate_slug_available(self):
        """Test that unique slug is marked available"""
        user = User.objects.create_user(username='testuser', password='pass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:validate_organization_slug')
        response = client.get(url, {'slug': 'unique-slug'})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['ok'] is True
        assert response.data['available'] is True
    
    def test_validate_slug_taken(self):
        """Test that existing slug is marked unavailable"""
        user = User.objects.create_user(username='testuser', password='pass123')
        Organization.objects.create(name='Test Org', slug='test-org', ceo=user)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:validate_organization_slug')
        response = client.get(url, {'slug': 'test-org'})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['ok'] is False
        assert response.data['available'] is False


@pytest.mark.django_db
class TestCreateOrganization:
    """Tests for /api/vnext/organizations/create/"""
    
    def test_create_organization_minimal(self):
        """Test creating organization with minimal required fields"""
        user = User.objects.create_user(username='testuser', password='pass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:create_organization')
        data = {
            'name': 'Test Organization',
            'slug': 'test-organization',
        }
        response = client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['ok'] is True
        assert 'organization_id' in response.data['data']
        assert 'organization_slug' in response.data['data']
        assert 'organization_url' in response.data['data']
        
        # Verify organization was created
        org = Organization.objects.get(slug='test-organization')
        assert org.name == 'Test Organization'
        assert org.ceo == user
        
        # Verify profile was created
        assert hasattr(org, 'profile')
        assert org.profile.organization_type == 'club'
        
        # Verify CEO membership was created
        membership = OrganizationMembership.objects.get(organization=org, user=user)
        assert membership.role == 'CEO'
    
    def test_create_organization_full_data(self):
        """Test creating organization with all fields"""
        user = User.objects.create_user(username='testuser', password='pass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:create_organization')
        data = {
            'name': 'Pro Esports Org',
            'slug': 'pro-esports',
            'description': 'Professional esports organization',
            'founded_year': 2020,
            'organization_type': 'pro',
            'hq_city': 'Dhaka',
            'hq_address': 'Gulshan-1, Dhaka',
            'business_email': 'business@pro-esports.com',
            'region_code': 'BD',
            'currency': 'BDT',
            'payout_method': 'bank',
            'brand_color': '#FF0000',
        }
        response = client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['ok'] is True
        
        org = Organization.objects.get(slug='pro-esports')
        assert org.description == 'Professional esports organization'
        
        profile = org.profile
        assert profile.founded_year == 2020
        assert profile.organization_type == 'pro'
        assert profile.hq_city == 'Dhaka'
        assert profile.business_email == 'business@pro-esports.com'
        assert profile.currency == 'BDT'
    
    def test_create_organization_duplicate_name(self):
        """Test that duplicate names are rejected"""
        user = User.objects.create_user(username='testuser', password='pass123')
        Organization.objects.create(name='Existing Org', slug='existing', ceo=user)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:create_organization')
        data = {
            'name': 'Existing Org',
            'slug': 'different-slug',
        }
        response = client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['ok'] is False
        assert 'name' in response.data['field_errors']
    
    def test_create_organization_duplicate_slug(self):
        """Test that duplicate slugs are rejected"""
        user = User.objects.create_user(username='testuser', password='pass123')
        Organization.objects.create(name='Org 1', slug='same-slug', ceo=user)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:create_organization')
        data = {
            'name': 'Org 2',
            'slug': 'same-slug',
        }
        response = client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['ok'] is False
        assert 'slug' in response.data['field_errors']
    
    def test_create_organization_auto_slug(self):
        """Test that slug is auto-generated from name if not provided"""
        user = User.objects.create_user(username='testuser', password='pass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:create_organization')
        data = {
            'name': 'Auto Slug Org',
        }
        response = client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['organization_slug'] == 'auto-slug-org'
    
    def test_create_organization_requires_auth(self):
        """Test that authentication is required"""
        client = APIClient()
        url = reverse('organizations_api:create_organization')
        data = {'name': 'TestOrg'}
        response = client.post(url, data)
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_create_organization_missing_name(self):
        """Test that name is required"""
        user = User.objects.create_user(username='testuser', password='pass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations_api:create_organization')
        data = {}
        response = client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'name' in response.data['field_errors']


@pytest.mark.django_db
class TestOrgCreatePageView:
    """Tests for /orgs/create/ UI view"""
    
    def test_page_loads_authenticated(self):
        """Test that page loads for authenticated users"""
        user = User.objects.create_user(username='testuser', password='pass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        url = reverse('organizations:org_create')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert b'Create Organization' in response.content
    
    def test_page_requires_auth(self):
        """Test that page redirects for anonymous users"""
        client = APIClient()
        url = reverse('organizations:org_create')
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == status.HTTP_302_FOUND
        assert '/accounts/login/' in response.url
