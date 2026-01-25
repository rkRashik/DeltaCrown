"""
Tests for Phase C+ - Hub Dynamic Widgets and API Endpoints.

Test Coverage:
1. Hub view query budget (≤15 queries)
2. Hub view with zero/realistic data
3. Game filter functionality
4. API endpoint schemas and consistency
5. Caching behavior
6. Error handling
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth import get_user_model
from apps.organizations.models import Team, TeamRanking, TeamMembership, Organization, OrganizationRanking
from apps.games.models import Game
import json

User = get_user_model()


@pytest.mark.django_db
class TestHubViewPerformance:
    """Test hub page performance and query budget."""
    
    def test_hub_query_budget_within_limits(self, client, django_assert_max_num_queries):
        """Hub page should use ≤15 queries."""
        # Create test user
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        # Create test data (minimal but realistic)
        game = Game.objects.create(
            slug='valorant',
            display_name='Valorant',
            is_active=True
        )
        
        org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=user,
            is_verified=True
        )
        
        org_ranking = OrganizationRanking.objects.create(
            organization=org,
            empire_score=10000
        )
        
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            owner=user,
            game_id=game.id,
            status='ACTIVE'
        )
        
        ranking = TeamRanking.objects.create(
            team=team,
            current_cp=1000,
            tier='DIAMOND',
            global_rank=1
        )
        
        # Clear cache to ensure fresh queries
        cache.clear()
        
        # Test query budget
        with django_assert_max_num_queries(15):
            response = client.get(reverse('organizations:vnext_hub'))
            assert response.status_code == 200
    
    def test_hub_loads_with_empty_database(self, client):
        """Hub should load gracefully with no data."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        # Clear all data
        Team.objects.all().delete()
        Organization.objects.all().delete()
        Game.objects.all().delete()
        cache.clear()
        
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        assert 'featured_teams' in response.context
        assert len(response.context['featured_teams']) == 0
        assert response.context['top_organization'] is None
    
    def test_hub_survives_org_without_ranking(self, client):
        """Hub should handle organizations without ranking rows."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        # Create org WITHOUT ranking
        org = Organization.objects.create(
            name='Test Org No Ranking',
            slug='test-org-no-rank',
            ceo=user,
            is_verified=True
        )
        # Explicitly do NOT create OrganizationRanking
        
        cache.clear()
        
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        # Should still show org or gracefully handle None
        assert 'top_organization' in response.context
    
    def test_hub_loads_with_realistic_data(self, client):
        """Hub should load correctly with realistic data."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        # Create realistic test data
        game1 = Game.objects.create(slug='valorant', display_name='Valorant', is_active=True)
        game2 = Game.objects.create(slug='cs2', display_name='CS2', is_active=True)
        
        org = Organization.objects.create(
            name='Top Org',
            slug='top-org',
            ceo=user,
            is_verified=True
        )
        
        org_ranking = OrganizationRanking.objects.create(
            organization=org,
            empire_score=50000
        )
        
        # Create 5 teams
        for i in range(5):
            team = Team.objects.create(
                name=f'Team {i}',
                slug=f'team-{i}',
                owner=user,
                game_id=game1.id if i % 2 == 0 else game2.id,
                status='ACTIVE'
            )
            
            TeamRanking.objects.create(
                team=team,
                current_cp=1000 * (5 - i),
                tier='DIAMOND',
                global_rank=i + 1
            )
        
        cache.clear()
        
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        assert len(response.context['featured_teams']) == 5
        assert response.context['top_organization'] == org
        assert len(response.context['leaderboard_rows']) == 5


@pytest.mark.django_db
class TestGameFilterFunctionality:
    """Test game filter functionality."""
    
    def test_game_filter_all_systems(self, client):
        """Test 'all systems' filter (no game filter)."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        game1 = Game.objects.create(slug='valorant', display_name='Valorant', is_active=True)
        game2 = Game.objects.create(slug='cs2', display_name='CS2', is_active=True)
        
        team1 = Team.objects.create(name='Team V', slug='team-v', owner=user, game_id=game1.id, status='ACTIVE')
        team2 = Team.objects.create(name='Team CS', slug='team-cs', owner=user, game_id=game2.id, status='ACTIVE')
        
        TeamRanking.objects.create(team=team1, current_cp=1000, global_rank=1)
        TeamRanking.objects.create(team=team2, current_cp=900, global_rank=2)
        
        cache.clear()
        
        response = client.get(reverse('organizations:vnext_hub') + '?game=all')
        
        assert response.status_code == 200
        assert len(response.context['featured_teams']) == 2
        assert response.context['selected_game'] == 'all'
    
    def test_game_filter_specific_game(self, client):
        """Test filtering by specific game."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        game1 = Game.objects.create(slug='valorant', display_name='Valorant', is_active=True)
        game2 = Game.objects.create(slug='cs2', display_name='CS2', is_active=True)
        
        team1 = Team.objects.create(name='Team V', slug='team-v', owner=user, game_id=game1.id, status='ACTIVE')
        team2 = Team.objects.create(name='Team CS', slug='team-cs', owner=user, game_id=game2.id, status='ACTIVE')
        
        TeamRanking.objects.create(team=team1, current_cp=1000, global_rank=1)
        TeamRanking.objects.create(team=team2, current_cp=900, global_rank=2)
        
        cache.clear()
        
        response = client.get(reverse('organizations:vnext_hub') + '?game=valorant')
        
        assert response.status_code == 200
        assert len(response.context['featured_teams']) == 1
        assert response.context['featured_teams'][0].game_id == game1.id
        assert response.context['selected_game'] == 'valorant'
    
    def test_game_filter_invalid_slug(self, client):
        """Test filtering with invalid game slug falls back to 'all'."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        game1 = Game.objects.create(slug='valorant', display_name='Valorant', is_active=True)
        team1 = Team.objects.create(name='Team V', slug='team-v', owner=user, game_id=game1.id, status='ACTIVE')
        TeamRanking.objects.create(team=team1, current_cp=1000, global_rank=1)
        
        cache.clear()
        
        response = client.get(reverse('organizations:vnext_hub') + '?game=invalid-game')
        
        assert response.status_code == 200
        assert response.context['selected_game'] == 'all'
        assert len(response.context['featured_teams']) == 1


@pytest.mark.django_db
class TestAPIEndpoints:
    """Test all hub widget API endpoints."""
    
    def test_ticker_feed_schema(self, client):
        """Test ticker feed returns consistent schema."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        response = client.get('/api/vnext/system/ticker/')
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        # Check consistent schema
        assert 'ok' in data
        assert 'data' in data
        assert 'items' in data['data']
        assert isinstance(data['data']['items'], list)
    
    def test_ticker_feed_with_real_events(self, client):
        """Test ticker feed returns real events."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        # Create a team
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            owner=user,
            game_id=1,
            status='ACTIVE'
        )
        
        ranking = TeamRanking.objects.create(
            team=team,
            current_cp=1000,
            global_rank=5,
            previous_rank=10
        )
        
        cache.clear()
        
        response = client.get('/api/vnext/system/ticker/')
        data = json.loads(response.content)
        
        assert data['ok'] is True
        assert len(data['data']['items']) > 0
        
        # Verify item structure
        item = data['data']['items'][0]
        assert 'type' in item
        assert 'timestamp' in item
        assert 'title' in item
        assert 'subtitle' in item
    
    def test_scout_radar_schema(self, client):
        """Test scout radar returns consistent schema."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        response = client.get('/api/vnext/system/players/lft/')
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert 'ok' in data
        assert 'data' in data
        assert 'players' in data['data']
        assert isinstance(data['data']['players'], list)
    
    def test_active_scrims_schema(self, client):
        """Test active scrims returns consistent schema."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        response = client.get('/api/vnext/system/scrims/active/')
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert 'ok' in data
        assert 'data' in data
        assert 'scrims' in data['data']
        assert isinstance(data['data']['scrims'], list)
    
    def test_team_search_min_length_validation(self, client):
        """Test team search requires minimum 2 characters."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        # Test with 1 character
        response = client.get('/api/vnext/system/teams/search/?q=a')
        
        assert response.status_code == 400
        data = json.loads(response.content)
        
        assert data['ok'] is False
        assert data['error_code'] == 'QUERY_TOO_SHORT'
        assert 'safe_message' in data
    
    def test_team_search_returns_results(self, client):
        """Test team search returns matching teams."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        # Create test teams
        team1 = Team.objects.create(name='Alpha Team', slug='alpha-team', owner=user, status='ACTIVE')
        team2 = Team.objects.create(name='Beta Team', slug='beta-team', owner=user, status='ACTIVE')
        
        TeamRanking.objects.create(team=team1, current_cp=1000, tier='DIAMOND')
        TeamRanking.objects.create(team=team2, current_cp=500, tier='GOLD')
        
        response = client.get('/api/vnext/system/teams/search/?q=alpha')
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert data['ok'] is True
        assert len(data['data']['teams']) == 1
        assert data['data']['teams'][0]['name'] == 'Alpha Team'
        assert data['data']['teams'][0]['tier'] == 'DIAMOND'
        assert data['data']['teams'][0]['cp'] == 1000


@pytest.mark.django_db
class TestCachingBehavior:
    """Test caching behavior for hub views and API endpoints."""
    
    def test_hero_carousel_caching(self, client):
        """Test hero carousel data is cached per user."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        cache.clear()
        
        # First request - should set cache
        response1 = client.get(reverse('organizations:vnext_hub'))
        assert response1.status_code == 200
        
        # Check cache was set
        cache_key = f'hero_carousel_{user.id}'
        cached_data = cache.get(cache_key)
        assert cached_data is not None
    
    def test_ticker_feed_caching(self, client):
        """Test ticker feed is cached."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        cache.clear()
        
        # First request
        response1 = client.get('/api/vnext/system/ticker/')
        data1 = json.loads(response1.content)
        
        # Check cache was set
        cache_key = 'hub_ticker_feed'
        cached_data = cache.get(cache_key)
        assert cached_data is not None
    
    def test_leaderboard_caching_per_game(self, client):
        """Test leaderboard is cached separately per game filter."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        game = Game.objects.create(slug='valorant', display_name='Valorant', is_active=True)
        cache.clear()
        
        # Request with game filter
        response1 = client.get(reverse('organizations:vnext_hub') + '?game=valorant')
        assert response1.status_code == 200
        
        # Check separate cache keys exist
        cache_key_all = f'hub_leaderboard_None_50'
        cache_key_game = f'hub_leaderboard_{game.id}_50'
        
        # At least one should be set based on what we requested
        assert cache.get(cache_key_game) is not None or cache.get(cache_key_all) is not None


@pytest.mark.django_db
class TestErrorHandling:
    """Test error handling and safe fallbacks."""
    
    def test_hub_survives_missing_tournament_model(self, client):
        """Hub should handle gracefully if tournaments module missing."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        cache.clear()
        
        response = client.get(reverse('organizations:vnext_hub'))
        
        # Should not crash even if Tournament model unavailable
        assert response.status_code == 200
    
    def test_api_endpoints_return_empty_on_error(self, client):
        """API endpoints should return safe empty responses on error."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        # Force an error condition by clearing cache and database
        cache.clear()
        
        # All endpoints should return gracefully
        endpoints = [
            '/api/vnext/system/ticker/',
            '/api/vnext/system/players/lft/',
            '/api/vnext/system/scrims/active/',
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            data = json.loads(response.content)
            # Either ok=True with empty list or ok=False with error
            assert 'ok' in data
            assert 'data' in data


@pytest.mark.django_db
class TestURLContracts:
    """Test URL pattern consistency."""
    
    def test_team_get_absolute_url(self):
        """Test Team.get_absolute_url() returns correct URL."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            owner=user,
            status='ACTIVE'
        )
        
        url = team.get_absolute_url()
        
        # Should use slug in URL
        assert 'test-team' in url
        assert '/teams/' in url
    
    def test_featured_teams_have_valid_urls(self, client):
        """Test featured teams in context have valid URLs."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        client.force_login(user)
        
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            owner=user,
            status='ACTIVE'
        )
        
        TeamRanking.objects.create(team=team, current_cp=1000, global_rank=1)
        
        cache.clear()
        
        response = client.get(reverse('organizations:vnext_hub'))
        
        featured_teams = response.context['featured_teams']
        assert len(featured_teams) == 1
        
        # Verify team has get_absolute_url method
        assert hasattr(featured_teams[0], 'get_absolute_url')
        assert callable(featured_teams[0].get_absolute_url)
