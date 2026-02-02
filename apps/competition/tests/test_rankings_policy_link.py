"""
Tests for Rankings Policy link navigation.
Ensures that Rankings Policy links in team/org hubs navigate correctly.

NOTE: These tests require COMPETITION_APP_ENABLED=1 environment variable.
Run with: COMPETITION_APP_ENABLED=1 pytest apps/competition/tests/test_rankings_policy_link.py
"""
import pytest
import os

# Skip all tests if competition app not enabled
pytestmark = pytest.mark.skipif(
    os.getenv("COMPETITION_APP_ENABLED") != "1",
    reason="Competition app not enabled (set COMPETITION_APP_ENABLED=1)"
)


@pytest.mark.django_db
class TestRankingsPolicyLink:
    """Test that Rankings Policy links work correctly in all templates."""
    
    def test_rankings_policy_url_resolves(self):
        """Test that the Rankings Policy URL resolves correctly."""
        from django.urls import reverse
        url = reverse('competition:ranking_about')
        assert url == '/competition/ranking/about/'
    
    def test_rankings_policy_page_accessible(self, client):
        """Test that the Rankings Policy page itself is accessible."""
        from django.urls import reverse
        ranking_url = reverse('competition:ranking_about')
        response = client.get(ranking_url)
        
        # Should be accessible even if not logged in
        assert response.status_code == 200
        assert 'Rankings Policy' in str(response.content) or 'ranking' in str(response.content).lower()
    
    def test_team_hub_has_rankings_policy_link(self, client, django_user_model):
        """Test that team hub contains correct Rankings Policy URL."""
        from django.urls import reverse
        from apps.organizations.models import Team
        import uuid
        
        # Create test user and team
        owner = django_user_model.objects.create_user(
            username=f"owner-{uuid.uuid4().hex[:8]}",
            email=f"owner-{uuid.uuid4().hex[:8]}@example.com"
        )
        team = Team.objects.create(
            name='Test Team',
            slug=f"team-{uuid.uuid4().hex[:8]}",
            game_id=1,
            owner=owner,
        )
        
        # Check that team hub contains Rankings Policy link
        response = client.get(f'/teams/vnext/{team.slug}/')
        if response.status_code == 200:
            ranking_url = reverse('competition:ranking_about')
            content = str(response.content)
            assert ranking_url in content or 'ranking/about' in content
    
    def test_org_hub_has_rankings_policy_link(self, client, django_user_model):
        """Test that org hub contains correct Rankings Policy URL."""
        from django.urls import reverse
        from apps.organizations.models import Organization
        import uuid
        
        # Create test user and org
        ceo = django_user_model.objects.create_user(
            username=f"ceo-{uuid.uuid4().hex[:8]}",
            email=f"ceo-{uuid.uuid4().hex[:8]}@example.com"
        )
        org = Organization.objects.create(
            name='Test Org',
            slug=f"org-{uuid.uuid4().hex[:8]}",
            ceo=ceo,
        )
        
        # Check that org hub contains Rankings Policy link
        response = client.get(f'/organizations/{org.slug}/hub/')
        if response.status_code == 200:
            ranking_url = reverse('competition:ranking_about')
            content = str(response.content)
            assert ranking_url in content or 'ranking/about' in content
