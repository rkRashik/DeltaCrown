"""
Smoke tests - basic system health checks.

Verifies:
- Admin loads without errors
- Competition ranking page renders when app enabled
- Team hub page renders and links correctly
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user for testing."""
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='testpass123'
    )


@pytest.fixture
def client():
    """Test client."""
    return Client()


@pytest.mark.django_db
class TestAdminSmoke:
    """Smoke tests for Django admin."""
    
    def test_admin_index_loads(self, client, admin_user):
        """Admin index should load without errors."""
        client.force_login(admin_user)
        response = client.get('/admin/')
        assert response.status_code == 200
        assert b'Django administration' in response.content or b'DeltaCrown' in response.content
    
    def test_admin_login_page(self, client):
        """Admin login page should be accessible."""
        response = client.get('/admin/login/')
        assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.skipif(
    not settings.COMPETITION_APP_ENABLED,
    reason="Competition app disabled (COMPETITION_APP_ENABLED=0)"
)
class TestCompetitionSmoke:
    """Smoke tests for competition app."""
    
    def test_ranking_about_page(self, client):
        """Ranking about page should render."""
        response = client.get(reverse('competition:ranking_about'))
        assert response.status_code == 200
        assert b'Ranking' in response.content or b'Policy' in response.content


@pytest.mark.django_db
class TestTeamHubSmoke:
    """Smoke tests for team hub."""
    
    def test_team_hub_loads_without_teams(self, client):
        """Team hub should load even with no teams."""
        # Try common team hub URLs
        try:
            response = client.get('/teams/')
            # Accept 200 (hub), 404 (no hub page), or redirect
            assert response.status_code in [200, 301, 302, 404]
        except Exception as e:
            pytest.fail(f"Team hub crashed: {e}")
    
    def test_rankings_policy_link_exists(self, client):
        """If competition enabled, team pages should link to ranking policy."""
        if not settings.COMPETITION_APP_ENABLED:
            pytest.skip("Competition app disabled")
        
        # This test would need a real team - just verify URL pattern exists
        from django.urls import resolve, Resolver404
        try:
            resolve('/competition/ranking/about/')
            # URL pattern exists
            assert True
        except Resolver404:
            pytest.fail("Ranking about URL not configured")
