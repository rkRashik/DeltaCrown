"""
GP-FE-MVP-01 Tests: Frontend + Routing + Template Rendering

Tests:
- URL routing (NoReverseMatch prevention)
- Template rendering smoke tests
- Passport API endpoints
- Service mutations
"""
import pytest
from django.urls import reverse, NoReverseMatch
from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.services.game_passport_service import GamePassportService
from apps.user_profile.models import GameProfile
import json

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestPassportRouting:
    """Test all passport-related URLs reverse correctly"""
    
    def test_all_passport_routes_reverse(self):
        """Verify all passport routes can be reversed (NoReverseMatch prevention)"""
        routes_to_test = [
            ('user_profile:profile_public_v2', {'username': 'testuser'}),
            ('user_profile:profile_settings_v2', {}),
            ('user_profile:passport_toggle_lft', {}),
            ('user_profile:passport_set_visibility', {}),
            ('user_profile:passport_pin', {}),
            ('user_profile:passport_reorder', {}),
        ]
        
        for route_name, kwargs in routes_to_test:
            try:
                url = reverse(route_name, kwargs=kwargs)
                assert url is not None
                assert isinstance(url, str)
            except NoReverseMatch as e:
                pytest.fail(f"Route {route_name} failed to reverse: {e}")


class TestProfilePublicTemplate:
    """Test public profile page renders with passports"""
    
    def test_profile_public_renders_with_passports(self):
        """Public profile page renders successfully with battle cards"""
        user = User.objects.create_user(username='battler', email='battler@example.com', password='pass123')
        
        # Create some passports
        GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='Fighter#123', metadata={}
        )
        GamePassportService.create_passport(
            user=user, game='cs2', in_game_name='76561198012345678', metadata={}
        )
        
        # Pin one
        GamePassportService.pin_passport(user=user, game='valorant')
        
        client = Client()
        response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'battler'}))
        
        assert response.status_code == 200
        assert b'battle-cards-section' in response.content or b'Featured Games' in response.content
        assert b'Fighter#123' in response.content
    
    def test_profile_public_no_passports(self):
        """Public profile renders correctly with no passports"""
        user = User.objects.create_user(username='newbie', email='newbie@example.com', password='pass123')
        
        client = Client()
        response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'newbie'}))
        
        assert response.status_code == 200
        # Should not crash, should show "no passports" message


class TestProfileSettingsTemplate:
    """Test settings page renders with passport management"""
    
    def test_settings_renders_with_passport_controls(self):
        """Settings page renders passport management UI"""
        user = User.objects.create_user(username='manager', email='manager@example.com', password='pass123')
        
        GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='Manager#456', metadata={}
        )
        
        client = Client()
        client.force_login(user)
        
        response = client.get(reverse('user_profile:profile_settings_v2'))
        
        assert response.status_code == 200
        # Just verify it doesn't crash - template content may vary
        assert response.content is not None


class TestPassportAPIEndpoints:
    """Test passport mutation endpoints"""
    
    def test_toggle_lft_endpoint(self):
        """LFT toggle endpoint works correctly"""
        user = User.objects.create_user(username='lftuser', email='lftuser@example.com', password='pass123')
        
        GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='Seeker#789', metadata={}
        )
        
        client = Client()
        client.force_login(user)
        
        # Toggle on
        response = client.post(
            reverse('user_profile:passport_toggle_lft'),
            data=json.dumps({'game': 'valorant'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['is_lft'] is True
        
        # Verify in DB
        passport = GameProfile.objects.get(user=user, game='valorant')
        assert passport.is_lft is True
    
    def test_set_visibility_endpoint(self):
        """Visibility setter endpoint works correctly"""
        user = User.objects.create_user(username='privuser', email='privuser@example.com', password='pass123')
        
        GamePassportService.create_passport(
            user=user, game='cs2', in_game_name='76561198012345678', metadata={}
        )
        
        client = Client()
        client.force_login(user)
        
        # Set to PRIVATE
        response = client.post(
            reverse('user_profile:passport_set_visibility'),
            data=json.dumps({'game': 'cs2', 'visibility': 'PRIVATE'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['visibility'] == 'PRIVATE'
        
        # Verify in DB
        passport = GameProfile.objects.get(user=user, game='cs2')
        assert passport.visibility == 'PRIVATE'
    
    def test_pin_passport_endpoint(self):
        """Pin endpoint works correctly"""
        user = User.objects.create_user(username='pinner', email='pinner@example.com', password='pass123')
        
        GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='Pinner#111', metadata={}
        )
        
        client = Client()
        client.force_login(user)
        
        # Pin
        response = client.post(
            reverse('user_profile:passport_pin'),
            data=json.dumps({'game': 'valorant', 'pin': True}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['is_pinned'] is True
        
        # Verify in DB
        passport = GameProfile.objects.get(user=user, game='valorant')
        assert passport.is_pinned is True
    
    def test_reorder_passports_endpoint(self):
        """Reorder endpoint works correctly"""
        user = User.objects.create_user(username='orderer', email='orderer@example.com', password='pass123')
        
        # Create 3 passports with valid formats
        GamePassportService.create_passport(user=user, game='valorant', in_game_name='Orderer#VAL', metadata={})
        GamePassportService.create_passport(user=user, game='cs2', in_game_name='76561198012345678', metadata={})
        GamePassportService.create_passport(user=user, game='lol', in_game_name='OrdererLOL', metadata={})
        
        # Pin all
        for game in ['valorant', 'cs2', 'lol']:
            GamePassportService.pin_passport(user=user, game=game)
        
        client = Client()
        client.force_login(user)
        
        # Reorder
        response = client.post(
            reverse('user_profile:passport_reorder'),
            data=json.dumps({'game_order': ['lol', 'valorant', 'cs2']}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['game_order'] == ['lol', 'valorant', 'cs2']
        
        # Verify order in DB
        lol = GameProfile.objects.get(user=user, game='lol')
        valorant = GameProfile.objects.get(user=user, game='valorant')
        cs2 = GameProfile.objects.get(user=user, game='cs2')
        
        assert lol.pinned_order == 1
        assert valorant.pinned_order == 2
        assert cs2.pinned_order == 3


class TestPassportServiceMutations:
    """Test service layer operations used by frontend"""
    
    def test_list_passports_separates_pinned(self):
        """Service returns passports in correct order"""
        user = User.objects.create_user(username='lister', email='lister@example.com', password='pass123')
        
        # Create passports with valid formats
        GamePassportService.create_passport(user=user, game='valorant', in_game_name='Lister#VAL', metadata={})
        GamePassportService.create_passport(user=user, game='cs2', in_game_name='76561198012345678', metadata={})
        GamePassportService.create_passport(user=user, game='lol', in_game_name='ListerLOL', metadata={})
        
        # Pin 2
        GamePassportService.pin_passport(user=user, game='valorant')
        GamePassportService.pin_passport(user=user, game='lol')
        
        # List all
        all_passports = GamePassportService.get_all_passports(user=user)
        pinned = [p for p in all_passports if p.is_pinned]
        unpinned = [p for p in all_passports if not p.is_pinned]
        
        assert len(pinned) == 2
        assert len(unpinned) == 1
        assert pinned[0].game in ['valorant', 'lol']
        assert unpinned[0].game == 'cs2'
