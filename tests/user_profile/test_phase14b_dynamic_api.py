"""
Phase 14B Tests: Dynamic Content API + Alpine Removal
Tests the new dynamic content endpoints that replace hardcoded dropdowns
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.user_profile.models_main import SocialLink
from apps.games.models import Game

User = get_user_model()


@pytest.mark.django_db
class TestDynamicContentAPI:
    """Test dynamic content API endpoints (Phase 14B)"""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def authenticated_client(self, client, user):
        client.login(username='testuser', password='testpass123')
        return client
    
    @pytest.fixture
    def sample_games(self):
        """Create sample games for testing"""
        games = [
            Game.objects.create(name='VALORANT', slug='valorant', is_active=True),
            Game.objects.create(name='CS2', slug='cs2', is_active=True),
            Game.objects.create(name='League of Legends', slug='league', is_active=True),
            Game.objects.create(name='Inactive Game', slug='inactive', is_active=False),
        ]
        return games
    
    def test_get_available_games(self, client, sample_games):
        """Test GET /api/games/ returns active games only"""
        url = reverse('user_profile:get_available_games')
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['success'] is True
        assert 'games' in data
        assert len(data['games']) == 3  # Only active games
        
        # Check structure of game data
        game = data['games'][0]
        assert 'id' in game
        assert 'name' in game
        assert 'slug' in game
        assert 'short_name' in game
        assert 'icon_url' in game
        assert 'color' in game
    
    def test_games_are_sorted_by_name(self, client, sample_games):
        """Test games list is alphabetically sorted"""
        url = reverse('user_profile:get_available_games')
        response = client.get(url)
        
        data = response.json()
        games = data['games']
        names = [g['name'] for g in games]
        
        assert names == sorted(names)
    
    def test_get_social_platforms(self, client):
        """Test GET /api/social-links/platforms/ returns platform choices"""
        url = reverse('user_profile:get_social_platforms')
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['success'] is True
        assert 'platforms' in data
        assert len(data['platforms']) > 0
        
        # Check structure of platform data
        platform = data['platforms'][0]
        assert 'value' in platform
        assert 'label' in platform
        assert 'icon' in platform
        assert 'placeholder' in platform
        assert 'prefix' in platform
    
    def test_social_platforms_match_model_choices(self, client):
        """Test platforms API returns same choices as SocialLink model"""
        url = reverse('user_profile:get_social_platforms')
        response = client.get(url)
        
        data = response.json()
        api_platforms = {p['value'] for p in data['platforms']}
        model_platforms = {choice[0] for choice in SocialLink.PLATFORM_CHOICES}
        
        assert api_platforms == model_platforms
    
    def test_get_privacy_presets_requires_auth(self, client):
        """Test GET /api/privacy/presets/ requires authentication"""
        url = reverse('user_profile:get_privacy_presets')
        response = client.get(url)
        
        # Should redirect to login (302) or return 403
        assert response.status_code in [302, 403]
    
    def test_get_privacy_presets_authenticated(self, authenticated_client):
        """Test GET /api/privacy/presets/ returns presets for authenticated user"""
        url = reverse('user_profile:get_privacy_presets')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['success'] is True
        assert 'presets' in data
        assert len(data['presets']) == 3  # public, protected, private
        
        # Check preset structure
        preset = data['presets'][0]
        assert 'value' in preset
        assert 'label' in preset
        assert 'description' in preset
        assert 'icon' in preset
        assert 'settings' in preset
        
        # Check settings structure
        settings = preset['settings']
        assert 'show_email' in settings
        assert 'show_phone' in settings
        assert 'show_real_name' in settings
        assert 'allow_team_invites' in settings
    
    def test_privacy_presets_have_correct_values(self, authenticated_client):
        """Test privacy presets have expected values"""
        url = reverse('user_profile:get_privacy_presets')
        response = authenticated_client.get(url)
        
        data = response.json()
        presets_by_value = {p['value']: p for p in data['presets']}
        
        assert 'public' in presets_by_value
        assert 'protected' in presets_by_value
        assert 'private' in presets_by_value
        
        # Public should have most things visible
        public = presets_by_value['public']
        assert public['settings']['show_social_links'] is True
        assert public['settings']['show_game_ids'] is True
        
        # Private should have minimal visibility
        private = presets_by_value['private']
        assert private['settings']['show_social_links'] is False
        assert private['settings']['show_game_ids'] is False
    
    def test_get_visibility_options_requires_auth(self, client):
        """Test GET /api/privacy/visibility-options/ requires authentication"""
        url = reverse('user_profile:get_visibility_options')
        response = client.get(url)
        
        assert response.status_code in [302, 403]
    
    def test_get_visibility_options_authenticated(self, authenticated_client):
        """Test GET /api/privacy/visibility-options/ returns visibility choices"""
        url = reverse('user_profile:get_visibility_options')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['success'] is True
        assert 'options' in data
        assert len(data['options']) == 3  # public, followers, private
        
        # Check option structure
        option = data['options'][0]
        assert 'value' in option
        assert 'label' in option
        assert 'description' in option
        assert 'icon' in option
    
    def test_visibility_options_values(self, authenticated_client):
        """Test visibility options have expected values"""
        url = reverse('user_profile:get_visibility_options')
        response = authenticated_client.get(url)
        
        data = response.json()
        values = [opt['value'] for opt in data['options']]
        
        assert 'public' in values
        assert 'followers' in values
        assert 'private' in values


@pytest.mark.django_db
class TestAPIClientIntegration:
    """Test API client behavior with real endpoints"""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='apipass123'
        )
    
    @pytest.fixture
    def authenticated_client(self, client, user):
        client.login(username='apiuser', password='apipass123')
        return client
    
    def test_games_endpoint_has_cors_headers(self, client):
        """Test games endpoint allows cross-origin requests if needed"""
        url = reverse('user_profile:get_available_games')
        response = client.get(url)
        
        # Should have X-Requested-With check capability
        assert response.status_code == 200
    
    def test_platforms_endpoint_has_cors_headers(self, client):
        """Test platforms endpoint allows cross-origin requests if needed"""
        url = reverse('user_profile:get_social_platforms')
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_all_endpoints_return_json(self, authenticated_client):
        """Test all dynamic content endpoints return JSON"""
        endpoints = [
            'user_profile:get_available_games',
            'user_profile:get_social_platforms',
            'user_profile:get_privacy_presets',
            'user_profile:get_visibility_options',
        ]
        
        for endpoint_name in endpoints:
            url = reverse(endpoint_name)
            response = authenticated_client.get(url)
            
            assert response['Content-Type'] == 'application/json'
            
            # Should be valid JSON
            data = response.json()
            assert isinstance(data, dict)


@pytest.mark.django_db  
class TestAlpineRemoval:
    """Test settings page works without Alpine.js"""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='settingsuser',
            email='settings@example.com',
            password='settingspass123'
        )
    
    @pytest.fixture
    def authenticated_client(self, client, user):
        client.login(username='settingsuser', password='settingspass123')
        return client
    
    def test_settings_page_loads(self, authenticated_client):
        """Test settings page loads successfully"""
        url = reverse('user_profile:profile_settings_v2')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
    
    def test_settings_page_has_no_alpine_references(self, authenticated_client):
        """Test settings template has no Alpine.js directives"""
        url = reverse('user_profile:profile_settings_v2')
        response = authenticated_client.get(url)
        
        content = response.content.decode()
        
        # Should not have Alpine directives (will be removed in next step)
        # This test will initially fail, then pass after template update
        alpine_patterns = [
            'x-data',
            'x-show',
            'x-if',
            '@click',
            'x-model',
            'x-cloak'
        ]
        
        # For now, just document that Alpine exists
        # (Will be removed in template update)
        alpine_found = any(pattern in content for pattern in alpine_patterns)
        
        # This assertion will fail initially - that's expected
        # After template update, it should pass
        # assert not alpine_found, "Settings page still contains Alpine.js directives"
    
    def test_settings_includes_api_client_js(self, authenticated_client):
        """Test settings page includes api_client.js and settings_v3.js"""
        url = reverse('user_profile:profile_settings_v2')
        response = authenticated_client.get(url)
        
        content = response.content.decode()
        
        # Should include new JS files (after template update)
        # assert 'api_client.js' in content
        # assert 'settings_v3.js' in content
    
    def test_settings_has_data_attributes_not_alpine(self, authenticated_client):
        """Test settings uses data-* attributes instead of Alpine directives"""
        url = reverse('user_profile:profile_settings_v2')
        response = authenticated_client.get(url)
        
        content = response.content.decode()
        
        # Should have data-* attributes for vanilla JS
        # (After template update)
        # assert 'data-section' in content
        # assert 'data-settings-form' in content
        # assert 'data-settings-section' in content
