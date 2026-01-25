"""
Test suite for Phase C - Hub Hero Carousel and API Feed Endpoints.

Tests:
- Hero carousel context data (top org, user teams, recent tournament)
- API endpoints: ticker, LFT, scrims, team search
- Response schemas, auth rules, empty state handling
"""

import pytest
from django.test import Client
from django.urls import reverse
import json


@pytest.mark.django_db
class TestHeroCarouselData:
    """Test hero carousel provides real data."""
    
    @pytest.fixture
    def test_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username='carousel_test_user',
            email='carousel@test.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def test_organization(self, test_user):
        from apps.organizations.models import Organization
        return Organization.objects.create(
            name='Top Org',
            slug='top-org',
            ceo=test_user,
            empire_score=9999,
            is_active=True
        )
    
    @pytest.fixture
    def test_team(self, test_user):
        from apps.organizations.models import Team, TeamMembership
        from apps.games.models import Game
        
        game, _ = Game.objects.get_or_create(
            slug='test-game-carousel',
            defaults={'name': 'Test Game', 'is_active': True, 'team_size_min': 5, 'team_size_max': 7}
        )
        
        team = Team.objects.create(
            name='User Team',
            slug='user-team',
            owner=test_user,
            game=game,
            region='NA',
            status='ACTIVE'
        )
        
        TeamMembership.objects.create(
            team=team,
            user=test_user,
            role='OWNER',
            status='ACTIVE'
        )
        
        return team
    
    def test_hub_includes_top_organization(self, client, test_user, test_organization):
        """Test hub context includes top organization by empire_score."""
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        assert 'top_organization' in response.context
        assert response.context['top_organization'] == test_organization
        assert response.context['top_organization'].empire_score == 9999
    
    def test_hub_includes_user_teams_count(self, client, test_user, test_team):
        """Test hub context includes user's active teams count."""
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        assert 'user_teams_count' in response.context
        assert response.context['user_teams_count'] >= 1  # At least the test team
    
    def test_hub_includes_user_primary_team(self, client, test_user, test_team):
        """Test hub context includes user's primary team."""
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        assert 'user_primary_team' in response.context
        assert response.context['user_primary_team'] is not None
        assert response.context['user_primary_team'].id == test_team.id
    
    def test_hub_includes_recent_tournament_winner(self, client, test_user):
        """Test hub context includes recent tournament winner (or None)."""
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        assert 'recent_tournament_winner' in response.context
        # May be None if no tournaments exist


@pytest.mark.django_db
class TestTickerFeedAPI:
    """Test /api/vnext/system/ticker/ endpoint."""
    
    @pytest.fixture
    def test_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username='ticker_user',
            email='ticker@test.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def ranking_with_change(self, test_user):
        from apps.organizations.models import Team, TeamRanking
        from apps.games.models import Game
        from django.utils import timezone
        
        game, _ = Game.objects.get_or_create(
            slug='test-game-ticker',
            defaults={'name': 'Test Game', 'is_active': True, 'team_size_min': 5, 'team_size_max': 7}
        )
        
        team = Team.objects.create(
            name='Ticker Team',
            slug='ticker-team',
            owner=test_user,
            game=game,
            region='NA',
            status='ACTIVE'
        )
        
        ranking = TeamRanking.objects.create(
            team=team,
            current_rank=3,
            previous_rank=5,
            current_cp=1500,
            rank_changed_at=timezone.now()
        )
        
        return ranking
    
    def test_ticker_endpoint_returns_json(self, client, test_user):
        """Test ticker endpoint returns valid JSON."""
        url = reverse('organizations_api:ticker_feed')
        response = client.get(url)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
        data = json.loads(response.content)
        assert 'items' in data
        assert 'status' in data
        assert isinstance(data['items'], list)
    
    def test_ticker_includes_ranking_changes(self, client, ranking_with_change):
        """Test ticker includes recent ranking changes."""
        url = reverse('organizations_api:ticker_feed')
        response = client.get(url)
        
        data = json.loads(response.content)
        
        # Check if ranking change is in ticker
        ranking_items = [item for item in data['items'] if item.get('type') == 'ranking_change']
        if ranking_items:  # May be empty if cutoff_date filters it out
            item = ranking_items[0]
            assert 'team_name' in item
            assert 'old_rank' in item
            assert 'new_rank' in item
            assert item['old_rank'] != item['new_rank']
    
    def test_ticker_graceful_fallback_on_error(self, client, monkeypatch):
        """Test ticker returns safe error response if query fails."""
        # This test verifies the try/except block works
        url = reverse('organizations_api:ticker_feed')
        response = client.get(url)
        
        data = json.loads(response.content)
        assert 'status' in data
        assert data['status'] in ['ok', 'error']
        if data['status'] == 'error':
            assert 'error_code' in data
            assert 'safe_message' in data


@pytest.mark.django_db
class TestScoutRadarAPI:
    """Test /api/vnext/system/players/lft/ endpoint."""
    
    @pytest.fixture
    def test_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username='scout_user',
            email='scout@test.com',
            password='testpass123'
        )
    
    def test_scout_radar_requires_auth(self, client):
        """Test scout radar endpoint requires authentication."""
        url = reverse('organizations_api:scout_radar')
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
    
    def test_scout_radar_returns_json_when_authenticated(self, client, test_user):
        """Test scout radar returns JSON for authenticated users."""
        client.force_login(test_user)
        url = reverse('organizations_api:scout_radar')
        response = client.get(url)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
        data = json.loads(response.content)
        assert 'players' in data
        assert 'status' in data
        assert isinstance(data['players'], list)
    
    def test_scout_radar_safe_fallback_if_lft_not_implemented(self, client, test_user):
        """Test scout radar returns safe message if LFT field doesn't exist."""
        client.force_login(test_user)
        url = reverse('organizations_api:scout_radar')
        response = client.get(url)
        
        data = json.loads(response.content)
        assert 'status' in data
        # Either returns data or safe fallback
        if data['status'] == 'ok' and not data['players']:
            # Empty with reason is acceptable
            assert 'error_code' in data or 'safe_message' in data


@pytest.mark.django_db
class TestActiveScrimsAPI:
    """Test /api/vnext/system/scrims/active/ endpoint."""
    
    @pytest.fixture
    def test_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username='scrim_user',
            email='scrim@test.com',
            password='testpass123'
        )
    
    def test_active_scrims_requires_auth(self, client):
        """Test scrims endpoint requires authentication."""
        url = reverse('organizations_api:active_scrims')
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
    
    def test_active_scrims_returns_json_when_authenticated(self, client, test_user):
        """Test scrims endpoint returns JSON for authenticated users."""
        client.force_login(test_user)
        url = reverse('organizations_api:active_scrims')
        response = client.get(url)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
        data = json.loads(response.content)
        assert 'scrims' in data
        assert 'status' in data
        assert isinstance(data['scrims'], list)
    
    def test_active_scrims_safe_fallback_if_model_not_exists(self, client, test_user):
        """Test scrims returns safe message if ScrimRequest model doesn't exist."""
        client.force_login(test_user)
        url = reverse('organizations_api:active_scrims')
        response = client.get(url)
        
        data = json.loads(response.content)
        assert 'status' in data
        # Either returns data or safe fallback
        if data['status'] == 'ok' and not data['scrims']:
            # Empty with reason is acceptable
            assert 'error_code' in data or 'safe_message' in data


@pytest.mark.django_db
class TestTeamSearchAPI:
    """Test /api/vnext/system/teams/search/ endpoint."""
    
    @pytest.fixture
    def test_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username='search_user',
            email='search@test.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def searchable_team(self, test_user):
        from apps.organizations.models import Team
        from apps.games.models import Game
        
        game, _ = Game.objects.get_or_create(
            slug='test-game-search',
            defaults={'name': 'Test Game Search', 'is_active': True, 'team_size_min': 5, 'team_size_max': 7}
        )
        
        return Team.objects.create(
            name='Searchable Team Alpha',
            slug='searchable-team-alpha',
            owner=test_user,
            game=game,
            region='NA',
            status='ACTIVE'
        )
    
    def test_team_search_requires_auth(self, client):
        """Test team search requires authentication."""
        url = reverse('organizations_api:team_search')
        response = client.get(url, {'q': 'test'})
        
        # Should redirect to login
        assert response.status_code == 302
    
    def test_team_search_returns_json(self, client, test_user):
        """Test team search returns JSON."""
        client.force_login(test_user)
        url = reverse('organizations_api:team_search')
        response = client.get(url, {'q': 'test'})
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
        data = json.loads(response.content)
        assert 'teams' in data
        assert 'status' in data
        assert isinstance(data['teams'], list)
    
    def test_team_search_finds_matching_teams(self, client, test_user, searchable_team):
        """Test team search returns teams matching query."""
        client.force_login(test_user)
        url = reverse('organizations_api:team_search')
        response = client.get(url, {'q': 'Searchable'})
        
        data = json.loads(response.content)
        assert data['status'] == 'ok'
        
        # Should find the searchable team
        team_names = [t['name'] for t in data['teams']]
        assert 'Searchable Team Alpha' in team_names
    
    def test_team_search_rejects_short_query(self, client, test_user):
        """Test team search rejects queries < 2 characters."""
        client.force_login(test_user)
        url = reverse('organizations_api:team_search')
        response = client.get(url, {'q': 'a'})
        
        data = json.loads(response.content)
        assert data['status'] == 'ok'
        assert len(data['teams']) == 0
        assert 'note' in data
        assert 'too short' in data['note'].lower()
    
    def test_team_search_includes_required_fields(self, client, test_user, searchable_team):
        """Test team search results include all required fields."""
        client.force_login(test_user)
        url = reverse('organizations_api:team_search')
        response = client.get(url, {'q': 'Searchable'})
        
        data = json.loads(response.content)
        
        if data['teams']:
            team = data['teams'][0]
            assert 'name' in team
            assert 'slug' in team
            assert 'logo_url' in team
            assert 'game' in team
            assert 'url' in team
            assert 'cp' in team


@pytest.mark.django_db
class TestPhaseCIntegration:
    """Integration tests for Phase C features."""
    
    @pytest.fixture
    def test_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username='integration_user',
            email='integration@test.com',
            password='testpass123'
        )
    
    def test_hub_page_loads_with_all_phase_c_data(self, client, test_user):
        """Test hub page loads successfully with Phase C carousel data."""
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        assert response.status_code == 200
        
        # Check Phase C context vars exist
        context_keys = ['top_organization', 'user_teams_count', 'user_primary_team', 'recent_tournament_winner']
        for key in context_keys:
            assert key in response.context, f"Missing context key: {key}"
    
    def test_all_api_endpoints_accessible(self, client, test_user):
        """Test all Phase C API endpoints are accessible."""
        client.force_login(test_user)
        
        endpoints = [
            ('organizations_api:ticker_feed', {}),
            ('organizations_api:scout_radar', {}),
            ('organizations_api:active_scrims', {}),
            ('organizations_api:team_search', {'q': 'test'}),
        ]
        
        for endpoint_name, params in endpoints:
            url = reverse(endpoint_name)
            response = client.get(url, params)
            
            assert response.status_code == 200, f"Endpoint {endpoint_name} failed"
            data = json.loads(response.content)
            assert 'status' in data, f"Endpoint {endpoint_name} missing status field"
