"""
Game-specific validators for tournament registration fields.

Provides validation functions for game IDs, usernames, and other
game-specific data formats (Riot ID, Steam ID, MLBB ID, etc.).
"""

import re
from typing import Tuple, Optional


class GameValidators:
    """
    Collection of validators for game-specific fields.
    
    Each validator returns (is_valid, error_message) tuple.
    """
    
    @staticmethod
    def validate_riot_id(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Riot ID format (Username#TAG).
        
        Format: Username#TAG where TAG is alphanumeric
        Examples: Player#1234, ProGamer#NA1, 忍者#JP
        
        Args:
            value: The Riot ID to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not value:
            return False, "Riot ID is required"
        
        # Remove extra whitespace
        value = value.strip()
        
        # Check format: must contain exactly one #
        if '#' not in value:
            return False, "Riot ID must be in format: Username#TAG (e.g., Player#1234)"
        
        parts = value.split('#')
        if len(parts) != 2:
            return False, "Riot ID must contain exactly one # symbol"
        
        username, tag = parts
        
        # Validate username (3-16 characters, not empty)
        if len(username) < 3:
            return False, "Username part must be at least 3 characters"
        if len(username) > 16:
            return False, "Username part must not exceed 16 characters"
        
        # Validate tag (3-5 alphanumeric characters)
        if not tag:
            return False, "TAG part cannot be empty"
        if not re.match(r'^[a-zA-Z0-9]{3,5}$', tag):
            return False, "TAG must be 3-5 alphanumeric characters"
        
        return True, None
    
    @staticmethod
    def validate_steam_id(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Steam ID format (17-digit number).
        
        Format: 17-digit numeric Steam ID
        Example: 76561198012345678
        
        Args:
            value: The Steam ID to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not value:
            return False, "Steam ID is required"
        
        value = str(value).strip()
        
        # Must be exactly 17 digits
        if not re.match(r'^\d{17}$', value):
            return False, "Steam ID must be a 17-digit number (e.g., 76561198012345678)"
        
        # Steam IDs typically start with 7656119
        if not value.startswith('7656119'):
            return False, "Invalid Steam ID format (should start with 7656119)"
        
        return True, None
    
    @staticmethod
    def validate_dota_friend_id(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Dota 2 Friend ID format (9-10 digits).
        
        Format: 9-10 digit numeric ID
        Example: 123456789
        
        Args:
            value: The Friend ID to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not value:
            return False, "Dota 2 Friend ID is required"
        
        value = str(value).strip()
        
        if not re.match(r'^\d{9,10}$', value):
            return False, "Dota 2 Friend ID must be 9-10 digits"
        
        return True, None
    
    @staticmethod
    def validate_mlbb_id(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Mobile Legends User ID format (6-12 digits).
        
        Format: 6-12 digit numeric ID
        Example: 123456789
        
        Args:
            value: The MLBB User ID to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not value:
            return False, "MLBB User ID is required"
        
        value = str(value).strip()
        
        if not re.match(r'^\d{6,12}$', value):
            return False, "MLBB User ID must be 6-12 digits"
        
        return True, None
    
    @staticmethod
    def validate_pubg_id(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate PUBG ID format.
        
        Format: 3-50 alphanumeric characters (can include underscores)
        Example: ProGamer_123
        
        Args:
            value: The PUBG ID to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not value:
            return False, "PUBG ID is required"
        
        value = value.strip()
        
        if len(value) < 3:
            return False, "PUBG ID must be at least 3 characters"
        if len(value) > 50:
            return False, "PUBG ID must not exceed 50 characters"
        
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            return False, "PUBG ID can only contain letters, numbers, and underscores"
        
        return True, None
    
    @staticmethod
    def validate_freefire_uid(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Free Fire UID format (9-12 digits).
        
        Format: 9-12 digit numeric UID
        Example: 123456789
        
        Args:
            value: The Free Fire UID to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not value:
            return False, "Free Fire UID is required"
        
        value = str(value).strip()
        
        if not re.match(r'^\d{9,12}$', value):
            return False, "Free Fire UID must be 9-12 digits"
        
        return True, None
    
    @staticmethod
    def validate_efootball_id(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate eFootball User ID format (8-12 digits).
        
        Format: 8-12 digit numeric ID
        Example: 12345678
        
        Args:
            value: The eFootball User ID to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not value:
            return False, "eFootball User ID is required"
        
        value = str(value).strip()
        
        if not re.match(r'^\d{8,12}$', value):
            return False, "eFootball User ID must be 8-12 digits"
        
        return True, None
    
    @staticmethod
    def validate_ea_id(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate EA/Origin ID format.
        
        Format: 3-50 alphanumeric characters
        Example: Player123
        
        Args:
            value: The EA/Origin ID to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not value:
            return False, "EA/Origin ID is required"
        
        value = value.strip()
        
        if len(value) < 3:
            return False, "EA/Origin ID must be at least 3 characters"
        if len(value) > 50:
            return False, "EA/Origin ID must not exceed 50 characters"
        
        # EA IDs can contain letters, numbers, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            return False, "EA/Origin ID can only contain letters, numbers, underscores, and hyphens"
        
        return True, None
    
    @staticmethod
    def validate_discord_id(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Discord ID format.
        
        Formats accepted:
        - username#1234 (legacy format)
        - @username (new format)
        - username (display name)
        
        Args:
            value: The Discord ID to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not value:
            # Discord ID is usually optional
            return True, None
        
        value = value.strip()
        
        # Check minimum length
        if len(value) < 2:
            return False, "Discord ID is too short"
        
        # Legacy format: username#1234
        if '#' in value:
            parts = value.split('#')
            if len(parts) == 2:
                username, discriminator = parts
                if len(username) >= 2 and discriminator.isdigit() and len(discriminator) == 4:
                    return True, None
        
        # New format: @username or username
        if value.startswith('@'):
            username = value[1:]
        else:
            username = value
        
        if len(username) >= 2 and re.match(r'^[a-zA-Z0-9_.]+$', username):
            return True, None
        
        return False, "Invalid Discord ID format (use username#1234, @username, or username)"
    
    @staticmethod
    def validate_phone_bd(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Bangladeshi mobile number format.
        
        Formats accepted:
        - 01712345678 (11 digits starting with 01)
        - +8801712345678 (with country code)
        - 8801712345678 (with country code, no +)
        
        Args:
            value: The phone number to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not value:
            return False, "Phone number is required"
        
        # Remove spaces and dashes
        value = re.sub(r'[\s-]', '', value)
        
        # Check patterns
        patterns = [
            r'^01[0-9]{9}$',  # 01XXXXXXXXX
            r'^\+8801[0-9]{9}$',  # +8801XXXXXXXXX
            r'^8801[0-9]{9}$',  # 8801XXXXXXXXX
        ]
        
        for pattern in patterns:
            if re.match(pattern, value):
                return True, None
        
        return False, "Invalid Bangladeshi mobile number (use format: 01XXXXXXXXX)"


# Convenience function to get validator by field name
def get_validator(field_name: str):
    """
    Get validator function for a specific field.
    
    Args:
        field_name: The field name (e.g., 'riot_id', 'steam_id')
        
    Returns:
        Validator function or None if not found
    """
    validator_map = {
        'riot_id': GameValidators.validate_riot_id,
        'steam_id': GameValidators.validate_steam_id,
        'dota_friend_id': GameValidators.validate_dota_friend_id,
        'mlbb_user_id': GameValidators.validate_mlbb_id,
        'pubg_id': GameValidators.validate_pubg_id,
        'ff_uid': GameValidators.validate_freefire_uid,
        'efootball_user_id': GameValidators.validate_efootball_id,
        'ea_id': GameValidators.validate_ea_id,
        'discord_id': GameValidators.validate_discord_id,
        'phone': GameValidators.validate_phone_bd,
    }
    
    return validator_map.get(field_name)
