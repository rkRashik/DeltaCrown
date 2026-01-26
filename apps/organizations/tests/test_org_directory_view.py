"""
Tests for org_directory view.

Tests URL routing, query params, and rendering.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.organizations.models import Organization, OrganizationProfile, OrganizationRanking

User = get_user_model()


@pytest.mark.django_db
class TestOrgDirectoryView:
    """Test organization directory view."""

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User.objects.create_user(
            username='viewtest',
            email='view@test.com',
            password='testpass123'
        )

    @pytest.fixture
    def sample_orgs(self, sample_user):
        """Create sample organizations."""
        orgs = []
        for i in range(5):
            org = Organization.objects.create(
                name=f'View Test Org {i+1}',
                slug=f'view-org-{i+1}',
                ceo=sample_user,
                is_verified=(i < 3),
            )
            OrganizationProfile.objects.create(
                organization=org,
                region_code='BD',
                hq_city='Dhaka',
            )
            OrganizationRanking.objects.create(
                organization=org,
                empire_score=500 - (i * 100),
            )
            orgs.append(org)
        return orgs

    def test_org_directory_url_reverses(self):
        """Test that org_directory URL reverses correctly."""
        url = reverse('organizations:org_directory')
        assert url == '/orgs/'

    def test_org_directory_get_200(self, client, sample_orgs):
        """Test GET /orgs/ returns 200."""
        url = reverse('organizations:org_directory')
        response = client.get(url)
        
        assert response.status_code == 200

    def test_org_directory_uses_correct_template(self, client, sample_orgs):
        """Test that correct template is used."""
        url = reverse('organizations:org_directory')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'organizations/org/org_directory.html' in [t.name for t in response.templates]

    def test_context_has_required_fields(self, client, sample_orgs):
        """Test that context contains expected variables."""
        url = reverse('organizations:org_directory')
        response = client.get(url)
        
        context = response.context
        assert 'page_title' in context
        assert 'page_description' in context
        assert 'top_three_orgs' in context
        assert 'rows' in context
        assert 'total_count' in context
        assert 'page' in context
        assert 'page_count' in context

    def test_search_query_param(self, client, sample_orgs):
        """Test search query parameter."""
        url = reverse('organizations:org_directory')
        response = client.get(url, {'q': 'View Test Org 1'})
        
        assert response.status_code == 200
        context = response.context
        
        # Should match "View Test Org 1" (and potentially "View Test Org 10" if exists)
        assert context['q'] == 'View Test Org 1'
        assert context['total_count'] >= 1

    def test_region_query_param(self, client, sample_orgs):
        """Test region filter query parameter."""
        url = reverse('organizations:org_directory')
        response = client.get(url, {'region': 'BD'})
        
        assert response.status_code == 200
        context = response.context
        
        assert context['region'] == 'BD'
        assert context['total_count'] == 5  # All sample orgs are BD

    def test_page_query_param(self, client, sample_orgs):
        """Test pagination query parameter."""
        url = reverse('organizations:org_directory')
        response = client.get(url, {'page': '1'})
        
        assert response.status_code == 200
        context = response.context
        assert context['page'] == 1

    def test_invalid_page_param(self, client, sample_orgs):
        """Test that invalid page param doesn't crash."""
        url = reverse('organizations:org_directory')
        response = client.get(url, {'page': 'invalid'})
        
        assert response.status_code == 200
        context = response.context
        assert context['page'] == 1  # Should default to 1

    def test_combined_query_params(self, client, sample_orgs):
        """Test multiple query parameters together."""
        url = reverse('organizations:org_directory')
        response = client.get(url, {
            'q': 'View',
            'region': 'BD',
            'page': '1',
        })
        
        assert response.status_code == 200
        context = response.context
        
        assert context['q'] == 'View'
        assert context['region'] == 'BD'
        assert context['page'] == 1

    def test_empty_query_params(self, client, sample_orgs):
        """Test that empty query params are handled."""
        url = reverse('organizations:org_directory')
        response = client.get(url, {'q': '', 'region': ''})
        
        assert response.status_code == 200
        context = response.context
        
        # Empty params should be treated as no filter
        assert context['total_count'] == 5

    def test_no_orgs_returns_empty(self, client):
        """Test directory with no organizations."""
        url = reverse('organizations:org_directory')
        response = client.get(url)
        
        assert response.status_code == 200
        context = response.context
        
        assert context['total_count'] == 0
        assert len(context['top_three_orgs']) == 0
        assert len(context['rows']) == 0

    def test_top_three_orgs_in_context(self, client, sample_orgs):
        """Test that top 3 orgs are in context."""
        url = reverse('organizations:org_directory')
        response = client.get(url)
        
        context = response.context
        assert len(context['top_three_orgs']) == 3

    def test_rows_exclude_top_three(self, client, sample_orgs):
        """Test that rows don't include top 3 orgs."""
        url = reverse('organizations:org_directory')
        response = client.get(url)
        
        context = response.context
        top_three_ids = [org.id for org in context['top_three_orgs']]
        row_ids = [org.id for org in context['rows']]
        
        # Verify no overlap
        assert not any(org_id in top_three_ids for org_id in row_ids)

    def test_template_renders_without_errors(self, client, sample_orgs):
        """Test that template renders successfully."""
        url = reverse('organizations:org_directory')
        response = client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Check for key elements
        assert 'Global' in content  # Hero title
        assert 'Create Organization' in content  # CTA button
        assert 'View Test Org 1' in content or 'Empire Score' in content  # Data or headers

    @pytest.mark.parametrize('query_param,value', [
        ('q', 'test'),
        ('region', 'US'),
        ('page', '2'),
        ('q', 'x' * 500),  # Very long query
    ])
    def test_various_query_params_dont_crash(self, client, sample_orgs, query_param, value):
        """Test that various query param values don't cause errors."""
        url = reverse('organizations:org_directory')
        response = client.get(url, {query_param: value})
        
        assert response.status_code == 200
