"""
Tests for Organization Hub View.

Tests the org_hub view function to ensure:
- Correct HTTP responses
- Template rendering
- Context data
- Permission logic
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import datetime, timedelta

from apps.organizations.models import (
    Organization,
    OrganizationProfile,
    OrganizationRanking,
    OrganizationMembership
)


@pytest.mark.django_db
class TestOrgHubView(TestCase):
    """Tests for org_hub view function."""
    
    def setUp(self):
        """Set up test data and client."""
        self.client = Client()
        
        # Create users
        self.ceo = User.objects.create_user(username='ceo', password='test123')
        self.regular_user = User.objects.create_user(username='user', password='test123')
        
        # Create organization
        self.org = Organization.objects.create(
            name='Test Organization',
            slug='test-org',
            ceo=self.ceo,
            is_verified=True
        )
        
        self.profile = OrganizationProfile.objects.create(
            organization=self.org,
            description='Test organization',
            region='US',
            founded_date=datetime.now().date() - timedelta(days=365)
        )
        
        self.ranking = OrganizationRanking.objects.create(
            organization=self.org,
            global_rank=10,
            total_points=50000
        )
    
    def test_org_hub_view_returns_200(self):
        """Test that org hub view returns 200 status."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_org_hub_view_404_invalid_slug(self):
        """Test that invalid org slug returns 404."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'nonexistent'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_org_hub_view_uses_correct_template(self):
        """Test that org hub view uses the correct template."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        self.assertTemplateUsed(response, 'organizations/org/org_hub.html')
    
    def test_org_hub_view_context_has_required_fields(self):
        """Test that context includes all required fields."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        self.assertIn('organization', response.context)
        self.assertIn('stats', response.context)
        self.assertIn('teams', response.context)
        self.assertIn('members', response.context)
        self.assertIn('recent_activity', response.context)
        self.assertIn('can_manage', response.context)
        self.assertIn('page_title', response.context)
    
    def test_org_hub_view_organization_data(self):
        """Test that organization data is correct in context."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        org = response.context['organization']
        self.assertEqual(org.slug, 'test-org')
        self.assertEqual(org.name, 'Test Organization')
        self.assertTrue(org.is_verified)
    
    def test_org_hub_view_stats_data(self):
        """Test that stats data is correct in context."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        stats = response.context['stats']
        self.assertIn('global_rank', stats)
        self.assertIn('total_cp', stats)
        self.assertIn('team_count', stats)
        self.assertIn('total_earnings', stats)
    
    def test_org_hub_management_ui_ceo_authenticated(self):
        """Test that CEO sees management UI when authenticated."""
        self.client.login(username='ceo', password='test123')
        
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        self.assertTrue(response.context['can_manage'])
        # Check that manage button appears in HTML
        self.assertContains(response, 'Manage Org')
    
    def test_org_hub_no_management_ui_regular_user(self):
        """Test that regular user doesn't see management UI."""
        self.client.login(username='user', password='test123')
        
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        self.assertFalse(response.context['can_manage'])
        # Check that manage button doesn't appear
        self.assertNotContains(response, 'Manage Org')
    
    def test_org_hub_no_management_ui_anonymous(self):
        """Test that anonymous user doesn't see management UI."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        self.assertFalse(response.context['can_manage'])
    
    def test_org_hub_view_performance(self):
        """Test that view doesn't exceed query limit."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        
        with CaptureQueriesContext(connection) as context_queries:
            response = self.client.get(url)
        
        query_count = len(context_queries)
        self.assertLessEqual(
            query_count,
            15,
            f"Expected ≤15 queries, got {query_count}"
        )
    
    def test_org_hub_view_page_title(self):
        """Test that page title is set correctly."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        self.assertEqual(response.context['page_title'], 'Test Organization Hub')
    
    def test_org_hub_view_teams_list(self):
        """Test that teams list is available in context."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        teams = response.context['teams']
        self.assertIsInstance(teams, list)
    
    def test_org_hub_view_activity_list(self):
        """Test that activity list is available in context."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        activity = response.context['recent_activity']
        self.assertIsInstance(activity, list)
    
    def test_org_hub_view_manager_can_manage(self):
        """Test that organization manager can manage."""
        manager = User.objects.create_user(username='manager', password='test123')
        OrganizationMembership.objects.create(
            organization=self.org,
            user=manager,
            role='MANAGER'
        )
        
        self.client.login(username='manager', password='test123')
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        response = self.client.get(url)
        
        self.assertTrue(response.context['can_manage'])


@pytest.mark.django_db
class TestOrgHubViewEdgeCases(TestCase):
    """Edge case tests for org hub view."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_org_hub_empty_org(self):
        """Test rendering hub for organization with minimal data."""
        ceo = User.objects.create_user(username='ceo', password='test')
        org = Organization.objects.create(name='Empty Org', slug='empty-org', ceo=ceo)
        OrganizationProfile.objects.create(organization=org)
        
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'empty-org'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['teams']), 0)
    
    def test_org_hub_no_profile(self):
        """Test rendering hub for organization without profile."""
        ceo = User.objects.create_user(username='ceo', password='test')
        org = Organization.objects.create(name='No Profile', slug='no-profile', ceo=ceo)
        
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'no-profile'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_org_hub_no_ranking(self):
        """Test rendering hub for organization without ranking."""
        ceo = User.objects.create_user(username='ceo', password='test')
        org = Organization.objects.create(name='No Rank', slug='no-rank', ceo=ceo)
        OrganizationProfile.objects.create(organization=org)
        
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'no-rank'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['stats']['global_rank'])
    
    def test_org_hub_special_characters_in_slug(self):
        """Test handling of special characters in org slug."""
        ceo = User.objects.create_user(username='ceo', password='test')
        org = Organization.objects.create(name='Special-Org_123', slug='special-org-123', ceo=ceo)
        OrganizationProfile.objects.create(organization=org)
        
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'special-org-123'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
