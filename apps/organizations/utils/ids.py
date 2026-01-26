"""
Secure ID generation utilities for organizations.

Provides collision-safe public identifiers using cryptographically secure randomness.
"""

import secrets
import string


# Base32 alphabet without confusable characters:
# Removed: 0 (zero), O (oh), 1 (one), I (eye), L (ell)
# Kept: A-Z except I, L, O and digits 2-9
SAFE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'  # 32 characters


def generate_public_id(prefix: str = "ORG", length: int = 10) -> str:
    """
    Generate a secure, collision-resistant public identifier.
    
    Uses cryptographically secure randomness (secrets module) to generate
    a Base32-encoded alphanumeric string suitable for public display.
    
    Args:
        prefix: String prefix for the ID (default: "ORG")
        length: Number of random characters after prefix (default: 10)
    
    Returns:
        Public ID string in format: PREFIX_XXXXXXXXXX
        
    Examples:
        >>> generate_public_id("ORG")
        'ORG_A7K2N9Q5B3'
        >>> generate_public_id("TEAM", 12)
        'TEAM_X9M4P7L2W6K3'
    
    Notes:
        - Uses Base32 alphabet (excludes 0, O, 1, I, L to avoid confusion)
        - Collision probability: ~1 in 3.6 quadrillion for 10 chars (32^10)
        - Safe for public URLs and user display
    """
    # Generate cryptographically secure random string
    random_chars = ''.join(secrets.choice(SAFE_ALPHABET) for _ in range(length))
    
    return f"{prefix}_{random_chars}"


def generate_team_public_id(length: int = 10) -> str:
    """
    Generate a team-specific public identifier.
    
    Convenience wrapper for generate_public_id with TEAM prefix.
    
    Args:
        length: Number of random characters (default: 10)
        
    Returns:
        Public ID string in format: TEAM_XXXXXXXXXX
    """
    return generate_public_id(prefix="TEAM", length=length)


def is_valid_public_id_format(public_id: str, prefix: str = "ORG", length: int = 10) -> bool:
    """
    Validate public ID format (does NOT check database uniqueness).
    
    Args:
        public_id: The public ID to validate
        prefix: Expected prefix (default: "ORG")
        length: Expected length of random part (default: 10)
        
    Returns:
        True if format matches expected pattern
        
    Examples:
        >>> is_valid_public_id_format("ORG_A7K2N9Q5B3")
        True
        >>> is_valid_public_id_format("ORG_123")
        False
        >>> is_valid_public_id_format("ORG_A7K2N9Q5BO")  # Contains O
        False
        >>> is_valid_public_id_format("TEAM_A7K2N9Q5B3", prefix="TEAM")
        True
    """
    if not public_id:
        return False
    
    expected_format = f"{prefix}_" + ("X" * length)
    
    # Check length
    if len(public_id) != len(expected_format):
        return False
    
    # Check prefix
    if not public_id.startswith(f"{prefix}_"):
        return False
    
    # Check random part contains only valid SAFE_ALPHABET chars (no 0, O, 1, I, L)
    random_part = public_id.split("_", 1)[1]
    
    return all(char in SAFE_ALPHABET for char in random_part)

