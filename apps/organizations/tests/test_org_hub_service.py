"""
Tests for Organization Hub Service Layer.

Tests the get_org_hub_context function and its helpers to ensure:
- Correct data retrieval
- Permission logic
- Query optimization
- Caching behavior
- Error handling
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.core.cache import cache
from datetime import datetime, timedelta

from apps.organizations.models import (
    Organization,
    OrganizationProfile,
    OrganizationRanking,
    OrganizationMembership
)
from apps.organizations.services.org_hub_service import (
    get_org_hub_context,
    _compute_org_stats,
    _get_recent_activity,
    ORG_HUB_CACHE_TTL,
)

User = get_user_model()


@pytest.mark.django_db
class TestGetOrgHubContext(TestCase):
    """Tests for get_org_hub_context function."""
    
    def setUp(self):
        """Set up test data."""
        # Clear cache before each test
        cache.clear()
        
        # Create users
        self.ceo = User.objects.create_user(username='ceo_user', password='test123', email='ceo@test.com')
        self.manager = User.objects.create_user(username='manager_user', password='test123', email='manager@test.com')
        self.regular_user = User.objects.create_user(username='regular_user', password='test123', email='regular@test.com')
        
        # Create organization with profile and ranking
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=self.ceo,
            is_verified=True
        )
        
        self.profile = OrganizationProfile.objects.create(
            organization=self.org,
            description='Test organization for hub',
            region='US',
            website='https://testorg.gg',
            founded_date=datetime.now().date() - timedelta(days=365)
        )
        
        self.ranking = OrganizationRanking.objects.create(
            organization=self.org,
            global_rank=15,
            total_points=45000
        )
        
        # Create manager membership
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.manager,
            role='MANAGER'
        )
    
    def tearDown(self):
        """Clean up after tests."""
        cache.clear()
    
    
    def test_get_hub_context_org_exists(self):
        """Test retrieving hub context for existing organization."""
        context = get_org_hub_context('test-org', self.ceo)
        
        self.assertIsNotNone(context)
        self.assertIn('organization', context)
        self.assertIn('stats', context)
        self.assertIn('teams', context)
        self.assertIn('members', context)
        self.assertIn('recent_activity', context)
        self.assertIn('can_manage', context)
        
        self.assertEqual(context['organization'].slug, 'test-org')
        self.assertTrue(context['can_manage'])
    
    def test_get_hub_context_org_not_found(self):
        """Test retrieving hub context for non-existent organization."""
        with self.assertRaises(Organization.DoesNotExist):
            get_org_hub_context('nonexistent-org', self.ceo)
    
    def test_can_manage_ceo(self):
        """Test that CEO can manage organization."""
        context = get_org_hub_context('test-org', self.ceo)
        self.assertTrue(context['can_manage'])
    
    def test_can_manage_manager(self):
        """Test that manager can manage organization."""
        context = get_org_hub_context('test-org', self.manager)
        self.assertTrue(context['can_manage'])
    
    def test_cannot_manage_regular_user(self):
        """Test that regular user cannot manage organization."""
        context = get_org_hub_context('test-org', self.regular_user)
        self.assertFalse(context['can_manage'])
    
    def test_cannot_manage_anonymous(self):
        """Test that anonymous user cannot manage organization."""
        context = get_org_hub_context('test-org', None)
        self.assertFalse(context['can_manage'])
    
    def test_members_visible_only_to_managers(self):
        """Test that members list is only visible to users who can manage."""
        # CEO can see members
        context_ceo = get_org_hub_context('test-org', self.ceo)
        self.assertIsInstance(context_ceo['members'], list)
        
        # Regular user cannot see members
        context_regular = get_org_hub_context('test-org', self.regular_user)
        self.assertEqual(len(context_regular['members']), 0)
    
    def test_stats_includes_global_rank(self):
        """Test that stats include global ranking."""
        context = get_org_hub_context('test-org', self.ceo)
        self.assertEqual(context['stats']['global_rank'], 15)
        self.assertEqual(context['stats']['total_cp'], 45000)
    
    def test_stats_includes_team_count(self):
        """Test that stats include team count."""
        context = get_org_hub_context('test-org', self.ceo)
        self.assertIn('team_count', context['stats'])
        self.assertIsInstance(context['stats']['team_count'], int)
    
    def test_recent_activity_exists(self):
        """Test that recent activity is returned."""
        context = get_org_hub_context('test-org', self.ceo)
        self.assertIsInstance(context['recent_activity'], list)
    
    def test_organization_has_related_data(self):
        """Test that organization is returned with related profile and ranking."""
        context = get_org_hub_context('test-org', self.ceo)
        org = context['organization']
        
        # Check related data is prefetched (no additional queries)
        self.assertIsNotNone(org.profile)
        self.assertIsNotNone(org.ranking)
        self.assertIsNotNone(org.ceo)
    
    def test_query_count_optimization(self):
        """Test that query count is optimized (≤15 queries)."""
        # Use Django's assertNumQueries to check
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as context_queries:
            context = get_org_hub_context('test-org', self.ceo)
        
        query_count = len(context_queries)
        self.assertLessEqual(
            query_count,
            15,
            f"Expected ≤15 queries, got {query_count}"
        )


@pytest.mark.django_db
class TestComputeOrgStats(TestCase):
    """Tests for _compute_org_stats helper function."""
    
    def setUp(self):
        """Set up test organization."""
        self.ceo = User.objects.create_user(username='ceo', password='test', email='ceo@stats.com')
        self.org = Organization.objects.create(
            name='Stats Org',
            slug='stats-org',
            ceo=self.ceo
        )
        self.profile = OrganizationProfile.objects.create(organization=self.org)
        self.ranking = OrganizationRanking.objects.create(
            organization=self.org,
            global_rank=42,
            total_points=12000
        )
    
    def test_compute_stats_with_ranking(self):
        """Test computing stats when ranking exists."""
        stats = _compute_org_stats(self.org, [])
        
        self.assertEqual(stats['global_rank'], 42)
        self.assertEqual(stats['total_cp'], 12000)
        self.assertEqual(stats['team_count'], 0)
    
    def test_compute_stats_without_ranking(self):
        """Test computing stats when ranking doesn't exist."""
        # Delete ranking
        self.ranking.delete()
        delattr(self.org, 'ranking')
        
        stats = _compute_org_stats(self.org, [])
        
        self.assertIsNone(stats['global_rank'])
        self.assertEqual(stats['total_cp'], 0)
    
    def test_compute_stats_team_count(self):
        """Test that team count is computed correctly."""
        mock_teams = ['team1', 'team2', 'team3']
        stats = _compute_org_stats(self.org, mock_teams)
        
        self.assertEqual(stats['team_count'], 3)
    
    def test_compute_stats_cp_progress(self):
        """Test that CP progress is calculated."""
        stats = _compute_org_stats(self.org, [])
        
        self.assertIn('cp_progress', stats)
        self.assertGreaterEqual(stats['cp_progress'], 0)
        self.assertLessEqual(stats['cp_progress'], 100)


@pytest.mark.django_db
class TestGetRecentActivity(TestCase):
    """Tests for _get_recent_activity helper function."""
    
    def setUp(self):
        """Set up test organization."""
        self.ceo = User.objects.create_user(username='ceo', password='test', email='ceo@activity.com')
        self.org = Organization.objects.create(
            name='Activity Org',
            slug='activity-org',
            ceo=self.ceo
        )
    
    def test_get_recent_activity_returns_list(self):
        """Test that recent activity returns a list."""
        activity = _get_recent_activity(self.org, limit=10)
        
        self.assertIsInstance(activity, list)
    
    def test_get_recent_activity_respects_limit(self):
        """Test that activity list respects the limit parameter."""
        activity = _get_recent_activity(self.org, limit=5)
        
        self.assertLessEqual(len(activity), 5)
    
    def test_activity_has_required_fields(self):
        """Test that activity items have required fields."""
        activity = _get_recent_activity(self.org, limit=10)
        
        if activity:  # If there's any activity
            first_item = activity[0]
            self.assertIn('description', first_item)
            self.assertIn('timestamp', first_item)
            self.assertIn('icon', first_item)
            self.assertIn('color', first_item)
    
    def test_activity_sorted_by_timestamp(self):
        """Test that activity is sorted by timestamp (newest first)."""
        activity = _get_recent_activity(self.org, limit=10)
        
        if len(activity) > 1:
            timestamps = [item['timestamp'] for item in activity]
            self.assertEqual(timestamps, sorted(timestamps, reverse=True))


@pytest.mark.django_db
class TestOrgHubEdgeCases(TestCase):
    """Edge case tests for organization hub."""
    
    def test_empty_org_no_teams(self):
        """Test hub context for organization with no teams."""
        ceo = User.objects.create_user(username='ceo', password='test', email='ceo@empty.com')
        org = Organization.objects.create(name='Empty Org', slug='empty-org', ceo=ceo)
        OrganizationProfile.objects.create(organization=org)
        
        context = get_org_hub_context('empty-org', ceo)
        
        self.assertEqual(len(context['teams']), 0)
        self.assertEqual(context['stats']['team_count'], 0)
    
    def test_org_without_profile(self):
        """Test hub context for organization without profile (should handle gracefully)."""
        ceo = User.objects.create_user(username='ceo2', password='test', email='ceo2@test.com')
        org = Organization.objects.create(name='No Profile Org', slug='no-profile-org', ceo=ceo)
        
        # This should not raise an error
        context = get_org_hub_context('no-profile-org', ceo)
        
        self.assertIsNotNone(context)
    
    def test_org_without_ranking(self):
        """Test hub context for organization without ranking."""
        ceo = User.objects.create_user(username='ceo3', password='test', email='ceo3@test.com')
        org = Organization.objects.create(name='No Rank Org', slug='no-rank-org', ceo=ceo)
        OrganizationProfile.objects.create(organization=org)
        
        context = get_org_hub_context('no-rank-org', ceo)
        
        self.assertIsNone(context['stats']['global_rank'])
        self.assertEqual(context['stats']['total_cp'], 0)


@pytest.mark.django_db
class TestOrgHubCaching(TestCase):
    """Tests for organization hub caching functionality."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
        
        self.ceo = User.objects.create_user(username='ceo_cache', password='test', email='ceo@cache.com')
        self.org = Organization.objects.create(name='Test Org', slug='test-org', ceo=self.ceo)
        OrganizationProfile.objects.create(organization=self.org)
    
    def tearDown(self):
        """Clean up."""
        cache.clear()
    
    def test_context_caching(self):
        """Test that organization hub context is cached correctly."""
        # First call - cache miss
        context1 = get_org_hub_context('test-org', self.ceo)
        
        # Second call - should hit cache
        context2 = get_org_hub_context('test-org', self.ceo)
        
        # Both should return same data
        self.assertEqual(context1['organization'].id, context2['organization'].id)
        self.assertEqual(context1['stats'], context2['stats'])
    
    def test_cache_key_per_org(self):
        """Test that different orgs have different cache keys."""
        org2 = Organization.objects.create(name='Other Org', slug='other-org', ceo=self.ceo)
        OrganizationProfile.objects.create(organization=org2)
        
        context1 = get_org_hub_context('test-org', self.ceo)
        context2 = get_org_hub_context('other-org', self.ceo)
        
        self.assertNotEqual(context1['organization'].id, context2['organization'].id)
    
    def test_permission_not_cached(self):
        """Test that can_manage permission is NOT cached (computed per user)."""
        manager = User.objects.create_user(username='manager', password='test', email='manager@cache.com')
        regular_user = User.objects.create_user(username='regular', password='test', email='regular@cache.com')
        
        OrganizationMembership.objects.create(
            organization=self.org,
            user=manager,
            role='MANAGER'
        )
        
        # CEO access
        context_ceo = get_org_hub_context('test-org', self.ceo)
        self.assertTrue(context_ceo['can_manage'])
        
        # Manager access
        context_manager = get_org_hub_context('test-org', manager)
        self.assertTrue(context_manager['can_manage'])
        
        # Regular user access
        context_regular = get_org_hub_context('test-org', regular_user)
        self.assertFalse(context_regular['can_manage'])
    
    def test_cache_ttl(self):
        """Test that cache respects TTL setting."""
        self.assertGreater(ORG_HUB_CACHE_TTL, 0)
        self.assertEqual(ORG_HUB_CACHE_TTL, 300)  # 5 minutes
    
    def test_cached_data_excludes_user_specific_fields(self):
        """Test that cached data does NOT include user-specific fields."""
        # Get context to populate cache
        get_org_hub_context('test-org', self.ceo)
        
        # Check what's in cache directly
        cache_key = f'org_hub_context:{self.org.slug}'
        cached = cache.get(cache_key)
        
        self.assertIsNotNone(cached)
        self.assertIn('organization', cached)
        self.assertIn('teams', cached)
        self.assertIn('stats', cached)
        self.assertIn('recent_activity', cached)
        
        # Security check: user-specific fields should NOT be in cache
        self.assertNotIn('can_manage', cached)
        self.assertNotIn('members', cached)
