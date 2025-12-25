"""
Test GP-STABILIZE-01: Ensure no JSON writes to UserProfile.game_profiles

These tests verify that:
1. Legacy JSON write methods are blocked
2. GamePassportService writes to GameProfile table only
3. JSON field remains unchanged when using service
"""
import pytest
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile, GameProfile
from apps.user_profile.services.game_passport_service import GamePassportService

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestJSONWriteBlocking:
    """Test that JSON writes are blocked per GP-STABILIZE-01"""
    
    def test_set_game_profile_is_blocked(self):
        """set_game_profile() raises RuntimeError"""
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Attempt to write JSON - should be blocked
        with pytest.raises(RuntimeError) as exc_info:
            profile.set_game_profile('valorant', {'ign': 'TestPlayer#1234'})
        
        assert 'blocked' in str(exc_info.value).lower()
        assert 'GamePassportService' in str(exc_info.value)
    
    def test_add_game_profile_is_blocked(self):
        """add_game_profile() raises RuntimeError"""
        user = User.objects.create_user(username='testuser2', email='test2@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Attempt to write JSON - should be blocked
        with pytest.raises(RuntimeError) as exc_info:
            profile.add_game_profile('cs2', 'TestPlayer')
        
        assert 'blocked' in str(exc_info.value).lower()


class TestServiceWritesToGameProfile:
    """Test that GamePassportService writes to GameProfile table only"""
    
    def test_create_passport_no_json_write(self):
        """Creating passport via service doesn't modify JSON field"""
        user = User.objects.create_user(username='serviceuser', email='service@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Record initial JSON state
        initial_json = profile.game_profiles
        
        # Create passport via service
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            in_game_name='ServiceTest#1234',
            metadata={}
        )
        
        # Verify GameProfile created
        assert passport is not None
        assert passport.game == 'valorant'
        assert passport.in_game_name == 'ServiceTest#1234'
        
        # Verify JSON field unchanged
        profile.refresh_from_db()
        assert profile.game_profiles == initial_json, \
            "JSON field should not be modified by service writes"
    
    def test_update_passport_no_json_write(self):
        """Updating passport via service doesn't modify JSON field"""
        user = User.objects.create_user(username='updateuser', email='update@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Create initial passport (use Valorant to avoid MLBB validation)
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            in_game_name='Player#1234',
            metadata={}
        )
        
        # Record JSON state after creation
        profile.refresh_from_db()
        json_after_create = profile.game_profiles
        
        # Update passport
        updated = GamePassportService.update_passport_identity(
            user=user,
            game='valorant',
            new_in_game_name='Player#9999',
            actor_user_id=user.id
        )
        
        # Verify update worked
        assert updated.in_game_name == 'Player#9999'
        
        # Verify JSON unchanged
        profile.refresh_from_db()
        assert profile.game_profiles == json_after_create, \
            "JSON field should not change during passport updates"
    
    def test_list_passports_reads_from_gameprofile(self):
        """list_passports() reads from GameProfile table, not JSON"""
        user = User.objects.create_user(username='listuser', email='list@example.com', password='pass123')
        
        # Create passports in GameProfile table
        GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='Val#123', metadata={}
        )
        GamePassportService.create_passport(
            user=user, game='cs2', in_game_name='76561198012345678', metadata={}
        )
        
        # List passports
        passports = list(GamePassportService.get_all_passports(user=user))
        
        # Verify reads from GameProfile
        assert len(passports) == 2
        games = {p.game for p in passports}
        assert games == {'valorant', 'cs2'}


class TestLegacyGetterDeprecation:
    """Test that legacy getter emits deprecation warning"""
    
    def test_get_game_profile_warns_deprecated(self):
        """get_game_profile() logs deprecation warning"""
        import logging
        from unittest.mock import patch
        
        user = User.objects.create_user(username='warnuser', email='warn@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Mock logger to capture warnings
        with patch.object(logging.Logger, 'warning') as mock_warning:
            # Call legacy getter
            result = profile.get_game_profile('valorant')
            
            # Verify warning logged
            assert mock_warning.called
            warning_msg = str(mock_warning.call_args)
            assert 'DEPRECATED' in warning_msg or 'deprecated' in warning_msg.lower()


class TestGracefulMissingPassport:
    """Test that missing passports are handled gracefully"""
    
    def test_get_passport_returns_none_if_missing(self):
        """get_passport() returns None for non-existent game"""
        user = User.objects.create_user(username='noneuser', email='none@example.com', password='pass123')
        
        passport = GamePassportService.get_passport(user=user, game='nonexistent')
        
        assert passport is None
    
    def test_list_passports_returns_empty_for_no_games(self):
        """get_all_passports() returns empty list if user has no passports"""
        user = User.objects.create_user(username='emptyuser', email='empty@example.com', password='pass123')
        
        passports = list(GamePassportService.get_all_passports(user=user))
        
        assert passports == []
