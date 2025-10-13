"""
Tests for game validators.

Tests validation logic for all game-specific field formats.
"""

import pytest
from apps.tournaments.validators import GameValidators


class TestRiotIDValidator:
    """Tests for Riot ID validation (VALORANT)"""
    
    def test_valid_riot_ids(self):
        """Test valid Riot ID formats"""
        valid_ids = [
            'Player#1234',
            'ProGamer#NA1',
            'Test#ABC',
            'User#12345',
            'プレイヤー#JPN',  # Japanese (4 characters + 3 char tag)
            'Player_123#TAG',
        ]
        
        for riot_id in valid_ids:
            is_valid, error = GameValidators.validate_riot_id(riot_id)
            assert is_valid, f"{riot_id} should be valid, got error: {error}"
    
    def test_invalid_riot_ids(self):
        """Test invalid Riot ID formats"""
        invalid_ids = [
            '',  # Empty
            'Player',  # No tag
            '#1234',  # No username
            'Player#',  # Empty tag
            'Player##1234',  # Double hash
            'AB#1234',  # Username too short
            'ThisIsAVeryLongUsername#1234',  # Username too long
            'Player#12',  # Tag too short
            'Player#123456',  # Tag too long
            'Player#TAG!',  # Invalid characters in tag
        ]
        
        for riot_id in invalid_ids:
            is_valid, error = GameValidators.validate_riot_id(riot_id)
            assert not is_valid, f"{riot_id} should be invalid"
            assert error is not None


class TestSteamIDValidator:
    """Tests for Steam ID validation (CS2, Dota 2)"""
    
    def test_valid_steam_ids(self):
        """Test valid Steam ID formats"""
        valid_ids = [
            '76561198012345678',
            '76561199000000000',
            '76561197999999999',
        ]
        
        for steam_id in valid_ids:
            is_valid, error = GameValidators.validate_steam_id(steam_id)
            assert is_valid, f"{steam_id} should be valid, got error: {error}"
    
    def test_invalid_steam_ids(self):
        """Test invalid Steam ID formats"""
        invalid_ids = [
            '',  # Empty
            '1234567890',  # Too short
            '123456789012345678',  # Too long
            '7656119801234567a',  # Contains letter
            '12345678901234567',  # Doesn't start with 7656119
        ]
        
        for steam_id in invalid_ids:
            is_valid, error = GameValidators.validate_steam_id(steam_id)
            assert not is_valid, f"{steam_id} should be invalid"


class TestDotaFriendIDValidator:
    """Tests for Dota 2 Friend ID validation"""
    
    def test_valid_friend_ids(self):
        """Test valid Dota 2 Friend ID formats"""
        valid_ids = [
            '123456789',  # 9 digits
            '1234567890',  # 10 digits
        ]
        
        for friend_id in valid_ids:
            is_valid, error = GameValidators.validate_dota_friend_id(friend_id)
            assert is_valid, f"{friend_id} should be valid, got error: {error}"
    
    def test_invalid_friend_ids(self):
        """Test invalid Dota 2 Friend ID formats"""
        invalid_ids = [
            '',  # Empty
            '12345678',  # Too short
            '12345678901',  # Too long
            '12345678a',  # Contains letter
        ]
        
        for friend_id in invalid_ids:
            is_valid, error = GameValidators.validate_dota_friend_id(friend_id)
            assert not is_valid, f"{friend_id} should be invalid"


class TestMLBBIDValidator:
    """Tests for Mobile Legends User ID validation"""
    
    def test_valid_mlbb_ids(self):
        """Test valid MLBB User ID formats"""
        valid_ids = [
            '123456',  # 6 digits
            '123456789',  # 9 digits
            '123456789012',  # 12 digits
        ]
        
        for mlbb_id in valid_ids:
            is_valid, error = GameValidators.validate_mlbb_id(mlbb_id)
            assert is_valid, f"{mlbb_id} should be valid, got error: {error}"
    
    def test_invalid_mlbb_ids(self):
        """Test invalid MLBB User ID formats"""
        invalid_ids = [
            '',  # Empty
            '12345',  # Too short
            '1234567890123',  # Too long
            '12345a',  # Contains letter
        ]
        
        for mlbb_id in invalid_ids:
            is_valid, error = GameValidators.validate_mlbb_id(mlbb_id)
            assert not is_valid, f"{mlbb_id} should be invalid"


class TestPUBGIDValidator:
    """Tests for PUBG ID validation"""
    
    def test_valid_pubg_ids(self):
        """Test valid PUBG ID formats"""
        valid_ids = [
            'Player',
            'ProGamer_123',
            'Test_User',
            'Player123',
        ]
        
        for pubg_id in valid_ids:
            is_valid, error = GameValidators.validate_pubg_id(pubg_id)
            assert is_valid, f"{pubg_id} should be valid, got error: {error}"
    
    def test_invalid_pubg_ids(self):
        """Test invalid PUBG ID formats"""
        invalid_ids = [
            '',  # Empty
            'AB',  # Too short
            'A' * 51,  # Too long
            'Player-123',  # Invalid character (dash)
            'Player@123',  # Invalid character
        ]
        
        for pubg_id in invalid_ids:
            is_valid, error = GameValidators.validate_pubg_id(pubg_id)
            assert not is_valid, f"{pubg_id} should be invalid"


class TestFreeFireUIDValidator:
    """Tests for Free Fire UID validation"""
    
    def test_valid_ff_uids(self):
        """Test valid Free Fire UID formats"""
        valid_ids = [
            '123456789',  # 9 digits
            '123456789012',  # 12 digits
        ]
        
        for ff_uid in valid_ids:
            is_valid, error = GameValidators.validate_freefire_uid(ff_uid)
            assert is_valid, f"{ff_uid} should be valid, got error: {error}"
    
    def test_invalid_ff_uids(self):
        """Test invalid Free Fire UID formats"""
        invalid_ids = [
            '',  # Empty
            '12345678',  # Too short
            '1234567890123',  # Too long
            '12345678a',  # Contains letter
        ]
        
        for ff_uid in invalid_ids:
            is_valid, error = GameValidators.validate_freefire_uid(ff_uid)
            assert not is_valid, f"{ff_uid} should be invalid"


class TestEFootballIDValidator:
    """Tests for eFootball User ID validation"""
    
    def test_valid_efootball_ids(self):
        """Test valid eFootball User ID formats"""
        valid_ids = [
            '12345678',  # 8 digits
            '123456789012',  # 12 digits
        ]
        
        for ef_id in valid_ids:
            is_valid, error = GameValidators.validate_efootball_id(ef_id)
            assert is_valid, f"{ef_id} should be valid, got error: {error}"
    
    def test_invalid_efootball_ids(self):
        """Test invalid eFootball User ID formats"""
        invalid_ids = [
            '',  # Empty
            '1234567',  # Too short
            '1234567890123',  # Too long
            '1234567a',  # Contains letter
        ]
        
        for ef_id in invalid_ids:
            is_valid, error = GameValidators.validate_efootball_id(ef_id)
            assert not is_valid, f"{ef_id} should be invalid"


class TestEAIDValidator:
    """Tests for EA/Origin ID validation"""
    
    def test_valid_ea_ids(self):
        """Test valid EA/Origin ID formats"""
        valid_ids = [
            'Player',
            'ProGamer_123',
            'Test-User',
            'Player123',
        ]
        
        for ea_id in valid_ids:
            is_valid, error = GameValidators.validate_ea_id(ea_id)
            assert is_valid, f"{ea_id} should be valid, got error: {error}"
    
    def test_invalid_ea_ids(self):
        """Test invalid EA/Origin ID formats"""
        invalid_ids = [
            '',  # Empty
            'AB',  # Too short
            'A' * 51,  # Too long
            'Player@123',  # Invalid character
        ]
        
        for ea_id in invalid_ids:
            is_valid, error = GameValidators.validate_ea_id(ea_id)
            assert not is_valid, f"{ea_id} should be invalid"


class TestDiscordIDValidator:
    """Tests for Discord ID validation"""
    
    def test_valid_discord_ids(self):
        """Test valid Discord ID formats"""
        valid_ids = [
            'Player#1234',  # Legacy format
            '@username',  # New format
            'username',  # Display name
            'player_123',
            'user.name',
        ]
        
        for discord_id in valid_ids:
            is_valid, error = GameValidators.validate_discord_id(discord_id)
            assert is_valid, f"{discord_id} should be valid, got error: {error}"
    
    def test_invalid_discord_ids(self):
        """Test invalid Discord ID formats"""
        invalid_ids = [
            'A',  # Too short
            'Player#123',  # Wrong discriminator length
            'Player#abcd',  # Non-numeric discriminator
        ]
        
        for discord_id in invalid_ids:
            is_valid, error = GameValidators.validate_discord_id(discord_id)
            assert not is_valid, f"{discord_id} should be invalid"
    
    def test_empty_discord_id_is_valid(self):
        """Discord ID is optional, so empty should be valid"""
        is_valid, error = GameValidators.validate_discord_id('')
        assert is_valid, "Empty Discord ID should be valid (optional field)"


class TestPhoneBDValidator:
    """Tests for Bangladeshi phone number validation"""
    
    def test_valid_phone_numbers(self):
        """Test valid Bangladeshi phone formats"""
        valid_numbers = [
            '01712345678',
            '+8801712345678',
            '8801712345678',
            '01812345678',
            '01912345678',
        ]
        
        for phone in valid_numbers:
            is_valid, error = GameValidators.validate_phone_bd(phone)
            assert is_valid, f"{phone} should be valid, got error: {error}"
    
    def test_invalid_phone_numbers(self):
        """Test invalid phone formats"""
        invalid_numbers = [
            '',  # Empty
            '1712345678',  # Missing 0
            '0171234567',  # Too short
            '017123456789',  # Too long
            '02712345678',  # Wrong prefix
        ]
        
        for phone in invalid_numbers:
            is_valid, error = GameValidators.validate_phone_bd(phone)
            assert not is_valid, f"{phone} should be invalid"


class TestGetValidator:
    """Tests for get_validator helper function"""
    
    def test_get_validator_returns_correct_functions(self):
        """Test that get_validator returns the correct validator functions"""
        from apps.tournaments.validators import get_validator
        
        assert get_validator('riot_id') == GameValidators.validate_riot_id
        assert get_validator('steam_id') == GameValidators.validate_steam_id
        assert get_validator('discord_id') == GameValidators.validate_discord_id
        assert get_validator('phone') == GameValidators.validate_phone_bd
    
    def test_get_validator_returns_none_for_unknown_field(self):
        """Test that get_validator returns None for unknown fields"""
        from apps.tournaments.validators import get_validator
        
        assert get_validator('unknown_field') is None
