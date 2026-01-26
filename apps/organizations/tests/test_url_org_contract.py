"""
URL Contract Tests for Organizations App.

Ensures URL routing works correctly and follows naming conventions:
- URL ordering is correct (create, hub, detail in that order)
- URL names follow Django conventions (no namespace in path name)
- Reversing works correctly
- URL resolution hits correct views
"""

import pytest
from django.test import TestCase
from django.urls import reverse, resolve, Resolver404
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization, OrganizationProfile

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationURLContract(TestCase):
    """Test URL contracts for organization routes."""
    
    def setUp(self):
        """Set up test data."""
        self.ceo = User.objects.create_user(
            username='test_ceo',
            password='test123',
            email='ceo@test.com'
        )
        
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.ceo
        )
        OrganizationProfile.objects.create(organization=self.org)
    
    def test_org_create_url_reverse(self):
        """Test that org create URL reverses correctly."""
        url = reverse('organizations:org_create')
        self.assertEqual(url, '/orgs/create/')
    
    def test_org_directory_url_reverse(self):
        """Test that org directory URL reverses correctly."""
        url = reverse('organizations:org_directory')
        self.assertEqual(url, '/orgs/')
    
    def test_org_hub_url_reverse(self):
        """Test that org hub URL reverses correctly."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        self.assertEqual(url, '/orgs/test-org/hub/')
    
    def test_org_detail_url_reverse(self):
        """Test that org detail URL reverses correctly."""
        url = reverse('organizations:organization_detail', kwargs={'org_slug': 'test-org'})
        self.assertEqual(url, '/orgs/test-org/')
    
    def test_org_create_url_resolution(self):
        """Test that /orgs/create/ resolves to org_create view (not detail)."""
        match = resolve('/orgs/create/')
        self.assertEqual(match.url_name, 'org_create')
        self.assertEqual(match.namespace, 'organizations')
    
    def test_org_hub_url_resolution(self):
        """Test that /orgs/<slug>/hub/ resolves to org_hub view (not detail)."""
        match = resolve('/orgs/test-org/hub/')
        self.assertEqual(match.url_name, 'org_hub')
        self.assertEqual(match.namespace, 'organizations')
        self.assertEqual(match.kwargs['org_slug'], 'test-org')
    
    def test_org_detail_url_resolution(self):
        """Test that /orgs/<slug>/ resolves to organization_detail view."""
        match = resolve('/orgs/test-org/')
        self.assertEqual(match.url_name, 'organization_detail')
        self.assertEqual(match.namespace, 'organizations')
        self.assertEqual(match.kwargs['org_slug'], 'test-org')
    
    def test_org_directory_url_resolution(self):
        """Test that /orgs/ resolves to org_directory view."""
        match = resolve('/orgs/')
        self.assertEqual(match.url_name, 'org_directory')
        self.assertEqual(match.namespace, 'organizations')
    
    def test_url_ordering_hub_before_detail(self):
        """Test that hub URL is resolved before detail catch-all."""
        # This is critical: /orgs/<slug>/hub/ should not be caught by /orgs/<slug>/
        hub_match = resolve('/orgs/test-org/hub/')
        self.assertEqual(hub_match.url_name, 'org_hub')
        
        detail_match = resolve('/orgs/test-org/')
        self.assertEqual(detail_match.url_name, 'organization_detail')
        
        # They should be different views
        self.assertNotEqual(hub_match.url_name, detail_match.url_name)
    
    def test_url_ordering_create_before_detail(self):
        """Test that create URL is not caught by detail catch-all."""
        create_match = resolve('/orgs/create/')
        self.assertEqual(create_match.url_name, 'org_create')
        
        # Should not match organization_detail
        self.assertNotEqual(create_match.url_name, 'organization_detail')
    
    def test_special_slugs_dont_conflict(self):
        """Test that special slugs like 'create' and 'hub' don't conflict."""
        # Create org with slug 'create' (edge case)
        special_org = Organization.objects.create(
            name='Create Org',
            slug='create',  # This should work but be caught by create route
            ceo=self.ceo
        )
        
        # /orgs/create/ should still resolve to org_create view
        match = resolve('/orgs/create/')
        self.assertEqual(match.url_name, 'org_create')
        
        # To access this org, would need /orgs/create/ which conflicts
        # This is expected behavior - 'create' is a reserved slug
    
    def test_hub_url_with_special_characters(self):
        """Test hub URL with hyphens and underscores in slug."""
        special_org = Organization.objects.create(
            name='Special Org',
            slug='my-special_org',
            ceo=self.ceo
        )
        
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'my-special_org'})
        self.assertEqual(url, '/orgs/my-special_org/hub/')
        
        match = resolve('/orgs/my-special_org/hub/')
        self.assertEqual(match.url_name, 'org_hub')


@pytest.mark.django_db
class TestTeamURLContract(TestCase):
    """Test URL contracts for team routes."""
    
    def test_vnext_hub_url_reverse(self):
        """Test that vNext hub URL reverses correctly."""
        url = reverse('organizations:vnext_hub')
        self.assertEqual(url, '/teams/vnext/')
    
    def test_team_create_url_reverse(self):
        """Test that team create URL reverses correctly."""
        url = reverse('organizations:team_create')
        self.assertEqual(url, '/teams/create/')
    
    def test_team_detail_url_reverse(self):
        """Test that team detail URL reverses correctly."""
        url = reverse('organizations:team_detail', kwargs={'team_slug': 'test-team'})
        self.assertEqual(url, '/teams/test-team/')
    
    def test_team_invites_url_reverse(self):
        """Test that team invites URL reverses correctly."""
        url = reverse('organizations:team_invites')
        self.assertEqual(url, '/teams/invites/')
