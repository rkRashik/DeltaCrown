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
    
    def test_hub_is_public(self, client):
        """The Team Hub landing page is public (guests can browse teams); only actions need a login."""
        url = reverse('organizations:vnext_hub')
        response = client.get(url)

        assert response.status_code == 200
    
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
        assert 'rankings_preview' in response.context
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
        leaderboard1 = list(response1.context['rankings_preview'])
        
        # Second request - should use cache
        response2 = client.get(url)
        leaderboard2 = list(response2.context['rankings_preview'])
        
        assert leaderboard1 == leaderboard2
    
    def test_hub_game_filter(self, client, test_user, test_team, test_game):
        """Hub view filters by game slug."""
        client.force_login(test_user)
        cache.clear()
        
        url = reverse('organizations:vnext_hub') + f'?game={test_game.slug}'
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.context['selected_game_slug'] == test_game.slug
        assert response.context['selected_game'] == test_game
    
    def test_hub_no_n_plus_one_queries(self, client, test_user, test_team, test_game):
        """The hub's query count must not grow with the number of teams (the page itself needs ~35-50 queries)."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        import apps.organizations.models.team as team_module
        url = reverse('organizations:vnext_hub')

        def count():
            cache.clear()
            team_module._games.update(at=-1e9, by_pk={})
            with CaptureQueriesContext(connection) as ctx:
                assert client.get(url).status_code == 200
            return len(ctx.captured_queries)

        one_team = count()
        for i in range(6):
            team = Team.objects.create(name=f'Scale Team {i}', slug=f'scale-team-{i}', owner=test_user,
                                       game_id=test_game.id, region='Test', status='ACTIVE')
            TeamRanking.objects.create(team=team, current_cp=4000 - i, tier='GOLD', global_rank=200 + i)
        assert count() <= one_team + 6  # a per-team query (the old Game lookup) would add >= 6 on its own


@pytest.mark.django_db
class TestHubWidgetAPIs:
    """Tests for hub widget API endpoints."""
    
    def test_ticker_feed_requires_no_auth(self, client):
        """Ticker feed is public."""
        url = '/api/system/ticker/'
        response = client.get(url)
        
        assert response.status_code == 200
        payload = response.json()
        assert payload['ok'] is True
        assert 'items' in payload['data']
    
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
        data = response.json()['data']
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
        data = response.json()['data']
        assert 'scrims' in data
    
    def test_team_search_basic(self, client, test_user, test_team):
        """Team search returns matching teams."""
        client.force_login(test_user)
        
        url = '/api/system/teams/search/?q=Test'
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()['data']
        assert 'teams' in data
        assert len(data['teams']) > 0
        assert data['teams'][0]['name'] == 'Test Team'
    
    def test_team_search_min_query_length(self, client, test_user):
        """Team search requires at least 2 characters."""
        client.force_login(test_user)
        
        url = '/api/system/teams/search/?q=T'
        response = client.get(url)
        
        assert response.status_code == 400  # rejected, not silently empty
        payload = response.json()
        assert payload['ok'] is False and payload['error_code'] == 'QUERY_TOO_SHORT'
        assert payload['data']['teams'] == []
    
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
        data = response.json()['data']
        assert len(data['teams']) <= 5
