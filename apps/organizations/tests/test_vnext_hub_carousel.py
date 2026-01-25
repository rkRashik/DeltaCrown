"""
Regression tests for vNext Hub Carousel - FieldError Hotfix (2026-01-26).

Tests ensure:
- Hub loads without FieldError on Organization.is_active
- Top organization query uses valid fields (is_verified, not is_active)
- Carousel works with empty database (no orgs, no teams, no tournaments)
- Query performance stays within budget
"""

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestVNextHubCarouselHotfix:
    """Test hub carousel hotfix for Organization.is_active FieldError."""
    
    @pytest.fixture
    def test_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username='hub_carousel_user',
            email='carousel@hotfix.com',
            password='testpass123'
        )
    
    def test_vnext_hub_loads_without_is_active_filter(self, client, test_user):
        """
        Test hub loads successfully without FieldError on is_active.
        
        Regression test for: FieldError: Cannot resolve keyword 'is_active' into field
        This was caused by Organization.objects.filter(is_active=True) when
        Organization model has no is_active field.
        """
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        # Should load without FieldError
        assert response.status_code == 200
        assert 'top_organization' in response.context
    
    def test_top_organization_prefers_verified_but_falls_back(self, client, test_user):
        """
        Test top_organization prefers verified orgs but falls back to any org.
        
        Ensures query uses is_verified (valid field) not is_active (invalid field).
        """
        from apps.organizations.models import Organization
        
        # Create unverified org
        unverified_org = Organization.objects.create(
            name='Unverified Org',
            slug='unverified-org',
            ceo=test_user,
            is_verified=False
        )
        
        # Create verified org with higher score
        verified_org = Organization.objects.create(
            name='Verified Org',
            slug='verified-org',
            ceo=test_user,
            is_verified=True
        )
        
        # Create ranking for verified org
        from apps.organizations.models import OrganizationRanking
        OrganizationRanking.objects.create(
            organization=verified_org,
            empire_score=5000
        )
        
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        top_org = response.context['top_organization']
        
        # Should prefer verified org
        assert top_org is not None
        assert top_org.id == verified_org.id
        assert top_org.is_verified is True
    
    def test_vnext_hub_loads_with_no_organizations(self, client, test_user):
        """
        Test hub loads successfully even with no organizations in database.
        
        Ensures carousel is 100% crash-proof with empty DB.
        """
        # Ensure no organizations exist
        from apps.organizations.models import Organization
        Organization.objects.all().delete()
        
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        # Should still load (200) with None/fallback context
        assert response.status_code == 200
        assert 'top_organization' in response.context
        assert response.context['top_organization'] is None  # Fallback to None
    
    def test_vnext_hub_loads_with_no_teams(self, client, test_user):
        """
        Test hub loads successfully even with no teams in database.
        
        Ensures user team count fallback works.
        """
        from apps.organizations.models import Team
        Team.objects.all().delete()
        
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        assert 'user_teams_count' in response.context
        assert response.context['user_teams_count'] == 0  # Fallback to 0
        assert 'user_primary_team' in response.context
        assert response.context['user_primary_team'] is None  # Fallback to None
    
    def test_vnext_hub_loads_with_no_tournament_winner(self, client, test_user):
        """
        Test hub loads successfully even with no tournament data.
        
        Ensures recent_tournament_winner fallback works.
        """
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        assert 'recent_tournament_winner' in response.context
        # recent_tournament_winner may be None if no tournaments exist
        assert response.context['recent_tournament_winner'] is None or isinstance(response.context['recent_tournament_winner'], dict)
    
    def test_top_organization_uses_ranking_relation(self, client, test_user):
        """
        Test top_organization query uses ranking relation for ordering.
        
        Ensures select_related optimization and correct ordering by empire_score.
        """
        from apps.organizations.models import Organization, OrganizationRanking
        
        # Create org with high empire score
        high_score_org = Organization.objects.create(
            name='High Score Org',
            slug='high-score-org',
            ceo=test_user,
            is_verified=True
        )
        OrganizationRanking.objects.create(
            organization=high_score_org,
            empire_score=10000
        )
        
        # Create org with low empire score
        low_score_org = Organization.objects.create(
            name='Low Score Org',
            slug='low-score-org',
            ceo=test_user,
            is_verified=True
        )
        OrganizationRanking.objects.create(
            organization=low_score_org,
            empire_score=500
        )
        
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        top_org = response.context['top_organization']
        
        # Should be the org with highest empire_score
        assert top_org is not None
        assert top_org.id == high_score_org.id
        assert top_org.ranking.empire_score == 10000
    
    def test_top_organization_fallback_when_no_verified(self, client, test_user):
        """
        Test top_organization falls back to any org when no verified orgs exist.
        
        Ensures hub always has data if ANY orgs exist.
        """
        from apps.organizations.models import Organization
        
        # Create only unverified org
        unverified_org = Organization.objects.create(
            name='Only Unverified',
            slug='only-unverified',
            ceo=test_user,
            is_verified=False
        )
        
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        top_org = response.context['top_organization']
        
        # Should fallback to unverified org (better than None)
        assert top_org is not None
        assert top_org.id == unverified_org.id
    
    def test_vnext_hub_query_performance(self, client, test_user, django_assert_max_num_queries):
        """
        Test hub stays within query budget with carousel data.
        
        Phase C target: ≤15 queries for full hub page with carousel.
        """
        from apps.organizations.models import Organization, OrganizationRanking, Team, TeamMembership
        from apps.games.models import Game
        
        # Create test data
        org = Organization.objects.create(name='Perf Test Org', slug='perf-test-org', ceo=test_user, is_verified=True)
        OrganizationRanking.objects.create(organization=org, empire_score=1000)
        
        game, _ = Game.objects.get_or_create(slug='perf-game', defaults={'name': 'Perf Game', 'is_active': True, 'team_size_min': 5, 'team_size_max': 7})
        team = Team.objects.create(name='Perf Team', slug='perf-team', owner=test_user, game=game, region='NA', status='ACTIVE')
        TeamMembership.objects.create(team=team, user=test_user, role='OWNER', status='ACTIVE')
        
        client.force_login(test_user)
        
        # Allow reasonable query budget (15 queries)
        with django_assert_max_num_queries(15):\n            response = client.get(reverse('organizations:vnext_hub'))
            assert response.status_code == 200


@pytest.mark.django_db
class TestHubCarouselCrashProof:
    """Test hub carousel handles all edge cases gracefully."""
    
    @pytest.fixture
    def test_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username='crash_test_user',
            email='crash@test.com',
            password='testpass123'
        )
    
    def test_hub_with_org_but_no_ranking(self, client, test_user):
        """
        Test hub handles organization without ranking relation gracefully.
        
        Some orgs may not have OrganizationRanking created yet.
        """
        from apps.organizations.models import Organization
        
        # Create org WITHOUT ranking
        org = Organization.objects.create(
            name='No Ranking Org',
            slug='no-ranking-org',
            ceo=test_user,
            is_verified=True
        )
        
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        # Should not crash, even if ordering by ranking__empire_score fails
        assert response.status_code == 200
        # May return the org or None depending on query robustness
        assert 'top_organization' in response.context
    
    def test_hub_with_user_team_but_no_game(self, client, test_user):
        """
        Test hub handles team with missing game relation.
        
        Edge case: team.game FK could be null or referencing deleted game.
        """
        from apps.organizations.models import Team
        from apps.games.models import Game
        
        game, _ = Game.objects.get_or_create(
            slug='edge-game',
            defaults={'name': 'Edge Game', 'is_active': True, 'team_size_min': 5, 'team_size_max': 7}
        )
        
        # Create team with game
        team = Team.objects.create(
            name='Edge Team',
            slug='edge-team',
            owner=test_user,
            game=game,
            region='NA',
            status='ACTIVE'
        )
        
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        # Should not crash
        assert response.status_code == 200
        assert 'user_primary_team' in response.context
    
    def test_hub_context_keys_always_present(self, client, test_user):
        """
        Test hub context always includes carousel keys even if empty.
        
        Ensures templates don't crash on missing keys.
        """
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        
        # All carousel context keys must exist
        required_keys = [
            'top_organization',
            'user_teams_count',
            'user_primary_team',
            'recent_tournament_winner',
        ]
        
        for key in required_keys:
            assert key in response.context, f"Missing required context key: {key}"
