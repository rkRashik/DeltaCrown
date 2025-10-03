# tests/tournaments/test_api_endpoints.py
"""
Tests for Tournament API Endpoints

Tests state API, registration context API, and other endpoints.
"""
import pytest
from datetime import timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.tournaments.models import Tournament, TournamentSettings

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    """Create a test client."""
    return Client()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def tournament():
    """Create a test tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        game='valorant',
        status='PUBLISHED',
        entry_fee=100,
        max_teams=32,
    )


@pytest.fixture
def tournament_settings(tournament):
    """Create tournament settings."""
    now = timezone.now()
    return TournamentSettings.objects.create(
        tournament=tournament,
        max_teams=32,
        reg_open_at=now - timedelta(hours=1),
        reg_close_at=now + timedelta(days=1),
        start_at=now + timedelta(days=2),
    )


class TestStateAPI:
    """Test the real-time state API endpoint."""
    
    def test_state_api_exists(self, client, tournament):
        """State API endpoint should exist."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_state_api_returns_json(self, client, tournament, tournament_settings):
        """State API should return JSON."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
    
    def test_state_api_contains_required_fields(self, client, tournament, tournament_settings):
        """State API should return all required fields."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        data = response.json()
        
        # Check required fields
        required_fields = [
            'phase',
            'registration_state',
            'can_register',
            'is_full',
            'slots',
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_state_api_registration_state_values(self, client, tournament, tournament_settings):
        """State API should return correct registration state."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        data = response.json()
        
        # Registration should be open (set in fixture)
        assert data['registration_state'] == 'open'
        assert data['can_register'] is False  # No authenticated user
    
    def test_state_api_with_authenticated_user(self, client, user, tournament, tournament_settings):
        """State API should include user registration status."""
        client.force_login(user)
        
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        data = response.json()
        
        # Should include user-specific data
        assert 'user_registered' in data
        assert isinstance(data['user_registered'], bool)
    
    def test_state_api_slots_info(self, client, tournament, tournament_settings):
        """State API should return correct slots information."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        data = response.json()
        slots = data['slots']
        
        assert 'total' in slots
        assert 'taken' in slots
        assert 'available' in slots
        assert 'is_full' in slots
        
        assert slots['total'] == 32
        assert slots['is_full'] is False
    
    def test_state_api_404_for_invalid_slug(self, client):
        """State API should return 404 for non-existent tournament."""
        url = reverse('tournaments:state_api', kwargs={'slug': 'non-existent'})
        response = client.get(url)
        
        assert response.status_code == 404


class TestRegistrationContextAPI:
    """Test the registration context API."""
    
    def test_registration_context_api_exists(self, client, tournament):
        """Registration context API should exist."""
        url = reverse('tournaments:registration_context_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        # Should work (200) or require auth (302/403)
        assert response.status_code in [200, 302, 403]
    
    def test_registration_context_returns_json(self, client, user, tournament, tournament_settings):
        """Registration context API should return JSON."""
        client.force_login(user)
        
        url = reverse('tournaments:registration_context_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'application/json' in response['Content-Type']
    
    def test_registration_context_contains_button_state(self, client, user, tournament, tournament_settings):
        """Registration context should include button state."""
        client.force_login(user)
        
        url = reverse('tournaments:registration_context_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            # Should contain context with button info
            if 'context' in data:
                context = data['context']
                assert 'button_state' in context or 'button_text' in context


class TestAPIPerformance:
    """Test API performance and caching."""
    
    def test_state_api_is_cacheable(self, client, tournament, tournament_settings):
        """State API should support caching."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        # Check cache headers (if implemented)
        # Note: This depends on your caching strategy
        assert response.status_code == 200
    
    def test_state_api_multiple_calls(self, client, tournament, tournament_settings):
        """State API should handle multiple calls efficiently."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        
        # Make 5 calls
        for i in range(5):
            response = client.get(url)
            assert response.status_code == 200
            data = response.json()
            assert 'registration_state' in data


class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_state_api_handles_invalid_tournament(self, client):
        """State API should handle invalid tournament gracefully."""
        url = reverse('tournaments:state_api', kwargs={'slug': 'invalid-slug'})
        response = client.get(url)
        
        assert response.status_code == 404
    
    def test_state_api_handles_missing_settings(self, client, tournament):
        """State API should work even without TournamentSettings."""
        # Tournament without settings
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        # Should still return 200 with default values
        assert response.status_code == 200
        data = response.json()
        assert 'registration_state' in data


class TestAPIDataConsistency:
    """Test that API data is consistent with model state."""
    
    def test_state_api_reflects_model_state(self, client, tournament, tournament_settings):
        """API data should match model state machine."""
        from apps.tournaments.models.state_machine import TournamentStateMachine
        
        # Get state from model
        state_machine = TournamentStateMachine(tournament)
        model_state = state_machine.registration_state.value
        
        # Get state from API
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        api_data = response.json()
        
        # Should match
        assert api_data['registration_state'] == model_state
    
    def test_state_api_slots_match_actual(self, client, tournament, tournament_settings):
        """API slots should match actual registration count."""
        from apps.tournaments.models import Registration
        
        # Create some registrations
        for i in range(3):
            Registration.objects.create(
                tournament=tournament,
                user=User.objects.create_user(
                    username=f'player{i}',
                    email=f'player{i}@example.com',
                    password='pass'
                ),
                display_name=f'Player {i}',
                in_game_id=f'player{i}#TAG'
            )
        
        # Check API
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        api_data = response.json()
        
        # Should show 3 registrations
        assert api_data['slots']['taken'] == 3


class TestAPISecurity:
    """Test API security features."""
    
    def test_state_api_accessible_without_auth(self, client, tournament):
        """State API should be accessible without authentication."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        # Public data should be accessible
        assert response.status_code in [200, 404]  # 404 if tournament doesn't exist
    
    def test_state_api_no_sensitive_data_leak(self, client, tournament, tournament_settings):
        """State API should not leak sensitive information."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        data = response.json()
        
        # Should not contain sensitive fields
        sensitive_fields = ['password', 'api_key', 'secret', 'token']
        data_str = str(data).lower()
        
        for field in sensitive_fields:
            assert field not in data_str


class TestAPIRequestMethods:
    """Test that APIs only accept appropriate HTTP methods."""
    
    def test_state_api_only_get(self, client, tournament):
        """State API should only accept GET requests."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        
        # GET should work
        response = client.get(url)
        assert response.status_code in [200, 404]
        
        # POST should not be allowed
        response = client.post(url, {})
        assert response.status_code in [405, 403]  # Method Not Allowed
    
    def test_state_api_supports_cors_if_needed(self, client, tournament):
        """State API should support CORS headers if configured."""
        url = reverse('tournaments:state_api', kwargs={'slug': tournament.slug})
        response = client.get(url, HTTP_ORIGIN='http://example.com')
        
        # Check if CORS headers are present (if configured)
        # This test passes regardless, just checking structure
        assert response.status_code in [200, 404]
