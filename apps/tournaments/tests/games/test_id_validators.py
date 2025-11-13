# apps/tournaments/tests/games/test_id_validators.py
"""Tests for game-specific ID validators."""

import pytest
from apps.tournaments.games.validators import (
    validate_riot_id,
    validate_steam_id,
    validate_mlbb_uid_zone,
    validate_ea_id,
    validate_konami_id,
    validate_mobile_ign_uid
)


class TestRiotIDValidator:
    """Test Riot ID validation (Valorant)."""
    
    def test_valid_riot_id(self):
        """Valid username#TAG format."""
        is_valid, error = validate_riot_id("Player#NA1")
        assert is_valid is True
        assert error is None
    
    def test_valid_with_spaces(self):
        """Username can contain spaces."""
        is_valid, error = validate_riot_id("Cool Player#1234")
        assert is_valid is True
    
    def test_valid_with_underscore(self):
        """Username can contain underscores."""
        is_valid, error = validate_riot_id("Pro_Gamer#ABC12")
        assert is_valid is True
    
    def test_missing_separator(self):
        """Must contain # separator."""
        is_valid, error = validate_riot_id("InvalidUser")
        assert is_valid is False
        assert "#" in error
    
    def test_multiple_separators(self):
        """Only one # allowed."""
        is_valid, error = validate_riot_id("User#TAG#Extra")
        assert is_valid is False
        assert "exactly one" in error
    
    def test_username_too_short(self):
        """Username must be 3+ chars."""
        is_valid, error = validate_riot_id("ab#TAG")
        assert is_valid is False
        assert "3-16 characters" in error
    
    def test_username_too_long(self):
        """Username max 16 chars."""
        is_valid, error = validate_riot_id("VeryLongUsername1234#TAG")
        assert is_valid is False
        assert "3-16 characters" in error
    
    def test_tag_too_short(self):
        """Tag must be 3+ chars."""
        is_valid, error = validate_riot_id("Player#AB")
        assert is_valid is False
        assert "3-5 characters" in error
    
    def test_tag_too_long(self):
        """Tag max 5 chars."""
        is_valid, error = validate_riot_id("Player#ABCD12")
        assert is_valid is False
        assert "3-5 characters" in error
    
    def test_tag_lowercase_invalid(self):
        """Tag must be uppercase."""
        is_valid, error = validate_riot_id("Player#na1")
        assert is_valid is False
        assert "uppercase" in error


class TestSteamIDValidator:
    """Test Steam ID 64 validation (CS, Dota 2)."""
    
    def test_valid_steam_id(self):
        """Valid 17-digit Steam ID."""
        is_valid, error = validate_steam_id("76561198012345678")
        assert is_valid is True
        assert error is None
    
    def test_non_numeric(self):
        """Must be numeric."""
        is_valid, error = validate_steam_id("7656119abc1234567")
        assert is_valid is False
        assert "numeric" in error
    
    def test_wrong_length(self):
        """Must be exactly 17 digits."""
        is_valid, error = validate_steam_id("1234567890")
        assert is_valid is False
        assert "17 digits" in error
    
    def test_wrong_prefix(self):
        """Must start with 7656119."""
        is_valid, error = validate_steam_id("12345678901234567")
        assert is_valid is False
        assert "7656119" in error


class TestMLBBUIDZoneValidator:
    """Test Mobile Legends UID+Zone validation."""
    
    def test_valid_mlbb_id(self):
        """Valid uid|zone format."""
        is_valid, error = validate_mlbb_uid_zone("123456789012|2345")
        assert is_valid is True
        assert error is None
    
    def test_missing_separator(self):
        """Must contain | separator."""
        is_valid, error = validate_mlbb_uid_zone("123456789012")
        assert is_valid is False
        assert "|" in error
    
    def test_multiple_separators(self):
        """Only one | allowed."""
        is_valid, error = validate_mlbb_uid_zone("123456|789012|2345")
        assert is_valid is False
        assert "exactly one" in error
    
    def test_uid_too_short(self):
        """UID must be 10-12 digits."""
        is_valid, error = validate_mlbb_uid_zone("123456789|2345")
        assert is_valid is False
        assert "10-12 digits" in error
    
    def test_uid_too_long(self):
        """UID max 12 digits."""
        is_valid, error = validate_mlbb_uid_zone("1234567890123|2345")
        assert is_valid is False
        assert "10-12 digits" in error
    
    def test_zone_wrong_length(self):
        """Zone must be exactly 4 digits."""
        is_valid, error = validate_mlbb_uid_zone("123456789012|234")
        assert is_valid is False
        assert "exactly 4 digits" in error


class TestEAIDValidator:
    """Test EA ID validation (EA Sports FC)."""
    
    def test_valid_ea_id(self):
        """Valid EA ID."""
        is_valid, error = validate_ea_id("Player_123")
        assert is_valid is True
        assert error is None
    
    def test_too_short(self):
        """Must be 5+ chars."""
        is_valid, error = validate_ea_id("abcd")
        assert is_valid is False
        assert "5-20 characters" in error
    
    def test_too_long(self):
        """Max 20 chars."""
        is_valid, error = validate_ea_id("VeryLongEAIDName12345")
        assert is_valid is False
        assert "5-20 characters" in error
    
    def test_special_chars_invalid(self):
        """Only alphanumeric + underscore."""
        is_valid, error = validate_ea_id("Player-123")
        assert is_valid is False


class TestKonamiIDValidator:
    """Test Konami ID validation (eFootball)."""
    
    def test_valid_konami_id(self):
        """Valid 9-12 digit Konami ID."""
        is_valid, error = validate_konami_id("123456789")
        assert is_valid is True
        assert error is None
    
    def test_non_numeric(self):
        """Must be numeric."""
        is_valid, error = validate_konami_id("12345abc")
        assert is_valid is False
        assert "numeric" in error
    
    def test_too_short(self):
        """Must be 9+ digits."""
        is_valid, error = validate_konami_id("12345678")
        assert is_valid is False
        assert "9-12 digits" in error
    
    def test_too_long(self):
        """Max 12 digits."""
        is_valid, error = validate_konami_id("1234567890123")
        assert is_valid is False
        assert "9-12 digits" in error


class TestMobileIGNUIDValidator:
    """Test mobile game IGN/UID validation (PUBG, COD, FF)."""
    
    def test_valid_mobile_id(self):
        """Valid IGN/UID."""
        is_valid, error = validate_mobile_ign_uid("Player_123")
        assert is_valid is True
        assert error is None
    
    def test_too_short(self):
        """Must be 5+ chars by default."""
        is_valid, error = validate_mobile_ign_uid("abcd")
        assert is_valid is False
        assert "5-20 characters" in error
    
    def test_too_long(self):
        """Max 20 chars by default."""
        is_valid, error = validate_mobile_ign_uid("VeryLongMobileUsername1234567")
        assert is_valid is False
        assert "5-20 characters" in error
    
    def test_custom_length_range(self):
        """Can specify custom min/max."""
        is_valid, error = validate_mobile_ign_uid("abc", min_length=3, max_length=10)
        assert is_valid is True
    
    def test_special_chars_invalid(self):
        """Only alphanumeric + underscore."""
        is_valid, error = validate_mobile_ign_uid("Player-123")
        assert is_valid is False
