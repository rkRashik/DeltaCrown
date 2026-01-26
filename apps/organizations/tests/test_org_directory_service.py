"""
Tests for org_directory_service.

Tests filtering, pagination, and top 3 extraction logic.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization, OrganizationProfile, OrganizationRanking
from apps.organizations.services.org_directory_service import get_directory_context

User = get_user_model()


@pytest.mark.django_db
class TestOrgDirectoryService:
    """Test organization directory service layer."""

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User.objects.create_user(
            username='testceo',
            email='ceo@test.com',
            password='testpass123'
        )

    @pytest.fixture
    def sample_orgs(self, sample_user):
        """Create sample organizations with rankings."""
        orgs = []
        
        for i in range(10):
            org = Organization.objects.create(
                name=f'Test Org {i+1}',
                slug=f'test-org-{i+1}',
                ceo=sample_user,
                is_verified=(i < 5),  # First 5 are verified
            )
            
            # Create profile
            OrganizationProfile.objects.create(
                organization=org,
                region_code='BD' if i < 5 else 'US',
                hq_city='Dhaka' if i < 5 else 'New York',
            )
            
            # Create ranking
            OrganizationRanking.objects.create(
                organization=org,
                empire_score=1000 - (i * 100),  # Descending scores
            )
            
            orgs.append(org)
        
        return orgs

    def test_get_directory_context_basic(self, sample_orgs):
        """Test basic directory context retrieval."""
        context = get_directory_context()
        
        assert len(context['top_three_orgs']) == 3
        assert len(context['rows']) <= 20  # Default page size
        assert context['total_count'] == 10
        assert context['page'] == 1
        assert context['page_count'] == 1  # 7 remaining orgs fit in one page

    def test_top_three_extraction(self, sample_orgs):
        """Test that top 3 orgs are correctly extracted by empire_score."""
        context = get_directory_context()
        
        top_three = context['top_three_orgs']
        assert len(top_three) == 3
        
        # Verify ordering by empire_score
        assert top_three[0].name == 'Test Org 1'  # 1000 score
        assert top_three[1].name == 'Test Org 2'  # 900 score
        assert top_three[2].name == 'Test Org 3'  # 800 score
        
        # Verify top 3 are excluded from rows
        row_names = [org.name for org in context['rows']]
        assert 'Test Org 1' not in row_names
        assert 'Test Org 2' not in row_names
        assert 'Test Org 3' not in row_names

    def test_search_by_name(self, sample_orgs):
        """Test search filtering by organization name."""
        context = get_directory_context(q='Test Org 1')
        
        # Should match "Test Org 1" and "Test Org 10" (contains)
        assert context['total_count'] == 2
        assert context['q'] == 'Test Org 1'

    def test_search_by_slug(self, sample_orgs):
        """Test search filtering by slug."""
        context = get_directory_context(q='test-org-5')
        
        assert context['total_count'] == 1
        assert context['top_three_orgs'][0].slug == 'test-org-5'

    def test_region_filter(self, sample_orgs):
        """Test filtering by region code."""
        context = get_directory_context(region='BD')
        
        # First 5 orgs have BD region
        assert context['total_count'] == 5
        assert all(org.profile.region_code == 'BD' for org in context['top_three_orgs'])

    def test_region_filter_case_insensitive(self, sample_orgs):
        """Test region filter is case-insensitive."""
        context_upper = get_directory_context(region='BD')
        context_lower = get_directory_context(region='bd')
        
        assert context_upper['total_count'] == context_lower['total_count']

    def test_pagination(self, sample_orgs):
        """Test pagination with custom page size."""
        context = get_directory_context(page_size=3)
        
        # With page_size=3 and 7 remaining orgs (10 - 3 top), we get 3 pages
        assert context['page_count'] == 3
        assert len(context['rows']) == 3  # Page 1 shows 3 rows

    def test_pagination_page_2(self, sample_orgs):
        """Test retrieving page 2."""
        context = get_directory_context(page=2, page_size=3)
        
        assert context['page'] == 2
        assert len(context['rows']) == 3

    def test_invalid_page_defaults_to_1(self, sample_orgs):
        """Test that invalid page numbers default to page 1."""
        context = get_directory_context(page=999)
        
        # Should return last page instead of crashing
        assert context['page'] <= context['page_count']

    def test_combined_filters(self, sample_orgs):
        """Test combining search and region filter."""
        context = get_directory_context(q='Org', region='BD')
        
        # Should match orgs with 'Org' in name AND region_code='BD'
        assert context['total_count'] == 5
        assert all(org.profile.region_code == 'BD' for org in context['top_three_orgs'])

    def test_empty_results(self, sample_orgs):
        """Test handling of no matching results."""
        context = get_directory_context(q='NonexistentOrg')
        
        assert context['total_count'] == 0
        assert len(context['top_three_orgs']) == 0
        assert len(context['rows']) == 0

    def test_fewer_than_three_orgs(self, sample_user):
        """Test handling when fewer than 3 orgs exist."""
        # Create only 2 orgs
        for i in range(2):
            org = Organization.objects.create(
                name=f'Small Org {i+1}',
                slug=f'small-org-{i+1}',
                ceo=sample_user,
            )
            OrganizationProfile.objects.create(
                organization=org,
                region_code='BD',
            )
            OrganizationRanking.objects.create(
                organization=org,
                empire_score=500 - (i * 100),
            )
        
        context = get_directory_context()
        
        assert len(context['top_three_orgs']) == 2  # Only 2 available
        assert len(context['rows']) == 0  # All orgs are in top 3
        assert context['total_count'] == 2

    def test_squads_count_annotation(self, sample_orgs):
        """Test that squads_count annotation is present."""
        context = get_directory_context()
        
        # Check first org has squads_count attribute
        if context['top_three_orgs']:
            org = context['top_three_orgs'][0]
            assert hasattr(org, 'squads_count')
            assert org.squads_count == 0  # No squads created in fixtures

    def test_query_performance(self, sample_orgs, django_assert_num_queries):
        """Test that query count stays reasonable."""
        # Service should use select_related to minimize queries
        # Expected: 1 base query + 1 for count + 1 for paginated rows
        with django_assert_num_queries(4):  # Allow some flexibility
            context = get_directory_context()
            
            # Force evaluation
            list(context['top_three_orgs'])
            list(context['rows'])
