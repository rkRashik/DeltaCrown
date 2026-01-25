"""
Tests for vNext Hub view and API endpoints.

Phase B: Basic tests for hub rendering and widget APIs.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from apps.organizations.models import Team, TeamRanking, Organization
from apps.games.models import Game

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def test_game(db):
    """Create test game."""
    game, _ = Game.objects.get_or_create(
        slug='valorant',
        defaults={
            'name': 'Valorant',
            'display_name': 'VALORANT',
            'short_code': 'VAL',
            'is_active': True,
        }
    )
    return game


@pytest.fixture
def test_team(db, test_user, test_game):
    """Create test team with ranking."""
    team = Team.objects.create(
        name='Test Team',
        slug='test-team',
        owner=test_user,
        game_id=test_game.id,
        region='Bangladesh',
        status='ACTIVE'
    )
    
    # Create ranking
    TeamRanking.objects.create(
        team=team,
        current_cp=5000,
        tier='GOLD',
        global_rank=100
    )
    
    return team


@pytest.mark.django_db
class TestVNextHub:
    """Tests for vNext Hub view."""
    
    def test_hub_requires_login(self, client):
        """Hub view requires authentication."""
        url = reverse('organizations:vnext_hub')
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/accounts/login' in response.url
    
    def test_hub_renders_with_context(self, client, test_user, test_team):
        """Hub view renders with database context."""
        # Clear cache
        cache.clear()
        
        # Login
        client.force_login(test_user)
        
        url = reverse('organizations:vnext_hub')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'featured_teams' in response.context
        assert 'leaderboard_rows' in response.context
        assert 'available_games' in response.context
        assert 'selected_game' in response.context
    
    def test_hub_displays_featured_teams(self, client, test_user, test_team):
        """Hub view includes featured teams in context."""
        client.force_login(test_user)
        cache.clear()
        
        url = reverse('organizations:vnext_hub')
        response = client.get(url)
        
        assert response.status_code == 200
        featured_teams = list(response.context['featured_teams'])
        assert len(featured_teams) > 0
        assert test_team in featured_teams
    
    def test_hub_leaderboard_cached(self, client, test_user, test_team):
        """Leaderboard results are cached for 5 minutes."""
        client.force_login(test_user)
        cache.clear()
        
        url = reverse('organizations:vnext_hub')
        
        # First request - should hit database
        response1 = client.get(url)
        leaderboard1 = list(response1.context['leaderboard_rows'])
        
        # Second request - should use cache
        response2 = client.get(url)
        leaderboard2 = list(response2.context['leaderboard_rows'])
        
        assert leaderboard1 == leaderboard2
    
    def test_hub_game_filter(self, client, test_user, test_team, test_game):
        """Hub view filters by game slug."""
        client.force_login(test_user)
        cache.clear()
        
        url = reverse('organizations:vnext_hub') + f'?game={test_game.slug}'
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.context['selected_game'] == test_game.slug
    
    def test_hub_no_n_plus_one_queries(self, client, test_user, test_team, django_assert_max_num_queries):
        """Hub view has acceptable query count."""
        client.force_login(test_user)
        cache.clear()
        
        url = reverse('organizations:vnext_hub')
        
        # Allow reasonable number of queries (select_related/prefetch)
        # Featured teams + leaderboard + games + user auth + caching
        with django_assert_max_num_queries(15):
            response = client.get(url)
            assert response.status_code == 200


@pytest.mark.django_db
class TestHubWidgetAPIs:
    """Tests for hub widget API endpoints."""
    
    def test_ticker_feed_requires_no_auth(self, client):
        """Ticker feed is public."""
        url = '/api/system/ticker/'
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert 'status' in data
    
    def test_scout_radar_requires_auth(self, client, test_user):
        """Scout radar requires authentication."""
        url = '/api/system/players/lft/'
        
        # Unauthenticated - should redirect
        response = client.get(url)
        assert response.status_code == 302
        
        # Authenticated - should work
        client.force_login(test_user)
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert 'players' in data
    
    def test_active_scrims_requires_auth(self, client, test_user):
        """Active scrims requires authentication."""
        url = '/api/system/scrims/active/'
        
        # Unauthenticated - should redirect
        response = client.get(url)
        assert response.status_code == 302
        
        # Authenticated - should work
        client.force_login(test_user)
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert 'scrims' in data
    
    def test_team_search_basic(self, client, test_user, test_team):
        """Team search returns matching teams."""
        client.force_login(test_user)
        
        url = '/api/system/teams/search/?q=Test'
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert 'teams' in data
        assert len(data['teams']) > 0
        assert data['teams'][0]['name'] == 'Test Team'
    
    def test_team_search_min_query_length(self, client, test_user):
        """Team search requires at least 2 characters."""
        client.force_login(test_user)
        
        url = '/api/system/teams/search/?q=T'
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert data['teams'] == []
        assert 'Query too short' in data['note']
    
    def test_team_search_limit(self, client, test_user, test_game):
        """Team search respects limit parameter."""
        client.force_login(test_user)
        
        # Create multiple teams
        for i in range(15):
            Team.objects.create(
                name=f'Search Team {i}',
                slug=f'search-team-{i}',
                owner=test_user,
                game_id=test_game.id,
                region='Test',
                status='ACTIVE'
            )
        
        url = '/api/system/teams/search/?q=Search&limit=5'
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['teams']) <= 5
