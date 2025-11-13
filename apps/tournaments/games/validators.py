# apps/tournaments/games/validators.py
"""
Game-specific ID format validators.

Validates profile IDs for different gaming platforms:
- Riot ID (Valorant): username#TAG
- Steam ID (CS, Dota 2): 17-digit numeric
- MLBB UID+Zone: numeric_uid|numeric_zone
- EA ID (FC): alphanumeric
- Konami ID (eFootball): numeric
- Mobile IGN/UID (PUBG, COD, FF): alphanumeric
"""

import re
from typing import Optional


def validate_riot_id(riot_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate Riot ID format (username#TAG).
    
    Rules:
    - Format: username#TAG
    - Username: 3-16 chars, alphanumeric + spaces
    - TAG: 3-5 alphanumeric uppercase
    
    Args:
        riot_id: String in format "username#TAG"
        
    Returns:
        (is_valid: bool, error_message: str | None)
        
    Examples:
        >>> validate_riot_id("Player#NA1")
        (True, None)
        >>> validate_riot_id("Cool Player#1234")
        (True, None)
        >>> validate_riot_id("invalid")
        (False, "Riot ID must contain '#' separator")
    """
    if not riot_id or '#' not in riot_id:
        return False, "Riot ID must contain '#' separator"
    
    parts = riot_id.split('#')
    if len(parts) != 2:
        return False, "Riot ID must have exactly one '#' separator"
    
    username, tag = parts
    
    # Validate username
    if len(username) < 3 or len(username) > 16:
        return False, "Username must be 3-16 characters"
    
    if not re.match(r'^[\w\s]+$', username):
        return False, "Username can only contain letters, numbers, spaces, and underscores"
    
    # Validate tag
    if len(tag) < 3 or len(tag) > 5:
        return False, "Tag must be 3-5 characters"
    
    if not re.match(r'^[A-Z0-9]+$', tag):
        return False, "Tag must be uppercase alphanumeric"
    
    return True, None


def validate_steam_id(steam_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate Steam ID 64 format.
    
    Rules:
    - Exactly 17 digits
    - Starts with 7656119
    
    Args:
        steam_id: Steam ID 64 string
        
    Returns:
        (is_valid: bool, error_message: str | None)
        
    Examples:
        >>> validate_steam_id("76561198012345678")
        (True, None)
        >>> validate_steam_id("1234567890")
        (False, "Steam ID must be exactly 17 digits")
    """
    if not steam_id.isdigit():
        return False, "Steam ID must be numeric"
    
    if len(steam_id) != 17:
        return False, "Steam ID must be exactly 17 digits"
    
    if not steam_id.startswith('7656119'):
        return False, "Steam ID must start with 7656119"
    
    return True, None


def validate_mlbb_uid_zone(mlbb_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate Mobile Legends UID+Zone format.
    
    Rules:
    - Format: uid|zone
    - UID: 10-12 digits
    - Zone: 4 digits
    
    Args:
        mlbb_id: String in format "uid|zone"
        
    Returns:
        (is_valid: bool, error_message: str | None)
        
    Examples:
        >>> validate_mlbb_uid_zone("123456789012|2345")
        (True, None)
        >>> validate_mlbb_uid_zone("invalid")
        (False, "MLBB ID must contain '|' separator")
    """
    if not mlbb_id or '|' not in mlbb_id:
        return False, "MLBB ID must contain '|' separator"
    
    parts = mlbb_id.split('|')
    if len(parts) != 2:
        return False, "MLBB ID must have exactly one '|' separator"
    
    uid, zone = parts
    
    # Validate UID
    if not uid.isdigit():
        return False, "UID must be numeric"
    
    if len(uid) < 10 or len(uid) > 12:
        return False, "UID must be 10-12 digits"
    
    # Validate Zone
    if not zone.isdigit():
        return False, "Zone must be numeric"
    
    if len(zone) != 4:
        return False, "Zone must be exactly 4 digits"
    
    return True, None


def validate_ea_id(ea_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate EA ID format (for EA Sports FC).
    
    Rules:
    - 5-20 characters
    - Alphanumeric + underscores
    
    Args:
        ea_id: EA ID string
        
    Returns:
        (is_valid: bool, error_message: str | None)
        
    Examples:
        >>> validate_ea_id("Player_123")
        (True, None)
        >>> validate_ea_id("ab")
        (False, "EA ID must be 5-20 characters")
    """
    if not ea_id:
        return False, "EA ID cannot be empty"
    
    if len(ea_id) < 5 or len(ea_id) > 20:
        return False, "EA ID must be 5-20 characters"
    
    if not re.match(r'^[\w]+$', ea_id):
        return False, "EA ID can only contain letters, numbers, and underscores"
    
    return True, None


def validate_konami_id(konami_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate Konami ID format (for eFootball).
    
    Rules:
    - 9-12 digits
    - Numeric only
    
    Args:
        konami_id: Konami ID string
        
    Returns:
        (is_valid: bool, error_message: str | None)
        
    Examples:
        >>> validate_konami_id("123456789")
        (True, None)
        >>> validate_konami_id("abc")
        (False, "Konami ID must be numeric")
    """
    if not konami_id:
        return False, "Konami ID cannot be empty"
    
    if not konami_id.isdigit():
        return False, "Konami ID must be numeric"
    
    if len(konami_id) < 9 or len(konami_id) > 12:
        return False, "Konami ID must be 9-12 digits"
    
    return True, None


def validate_mobile_ign_uid(mobile_id: str, min_length: int = 5, max_length: int = 20) -> tuple[bool, Optional[str]]:
    """
    Validate mobile game IGN/UID format (PUBG Mobile, COD Mobile, Free Fire).
    
    Rules:
    - Configurable length range
    - Alphanumeric + underscores
    
    Args:
        mobile_id: IGN or UID string
        min_length: Minimum character length
        max_length: Maximum character length
        
    Returns:
        (is_valid: bool, error_message: str | None)
        
    Examples:
        >>> validate_mobile_ign_uid("Player_123")
        (True, None)
        >>> validate_mobile_ign_uid("ab")
        (False, "ID must be 5-20 characters")
    """
    if not mobile_id:
        return False, "ID cannot be empty"
    
    if len(mobile_id) < min_length or len(mobile_id) > max_length:
        return False, f"ID must be {min_length}-{max_length} characters"
    
    if not re.match(r'^[\w]+$', mobile_id):
        return False, "ID can only contain letters, numbers, and underscores"
    
    return True, None
