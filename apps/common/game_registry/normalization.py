"""
Game Registry - Slug Normalization Module
==========================================

Handles normalization of game codes/slugs from various sources into
canonical lowercase slugs. Resolves legacy codes, aliases, and format
variations.

NORMALIZATION RULES:
-------------------
1. Convert to lowercase
2. Replace underscores with hyphens
3. Remove extra whitespace
4. Handle legacy mappings (csgo → cs2, fifa → fc26)
5. Handle platform suffixes (pubg-mobile → pubg)
6. Handle abbreviations (ml → mlbb, ff → freefire)

CANONICAL SLUGS:
---------------
These are the standard slugs used throughout the registry:
- valorant
- cs2
- dota2
- efootball
- fc26
- mlbb
- codm
- freefire
- pubg
"""

# ============================================================================
# LEGACY CODE MAPPINGS
# ============================================================================
# Maps old/alternate game codes to canonical slugs

LEGACY_ALIASES = {
    # CS:GO → CS2 (game evolved)
    'csgo': 'cs2',
    'cs-go': 'cs2',
    'cs_go': 'cs2',
    'counter-strike-go': 'cs2',
    'counter-strike': 'cs2',
    
    # FIFA → FC26 (rebranding)
    'fifa': 'fc26',
    'fifa-26': 'fc26',
    'fc-26': 'fc26',
    'fc_26': 'fc26',
    
    # PUBG variations
    'pubg-mobile': 'pubg',
    'pubgm': 'pubg',
    'pubg_mobile': 'pubg',
    'playerunknowns-battlegrounds': 'pubg',
    
    # Free Fire variations
    'free-fire': 'freefire',
    'free_fire': 'freefire',
    'ff': 'freefire',
    
    # Mobile Legends variations
    'mobile-legends': 'mlbb',
    'mobile_legends': 'mlbb',
    'ml': 'mlbb',
    'mlbb': 'mlbb',
    'mobile-legends-bang-bang': 'mlbb',
    
    # Call of Duty variations
    'call-of-duty-mobile': 'codm',
    'cod-mobile': 'codm',
    'cod_mobile': 'codm',
    'codmobile': 'codm',
    
    # eFootball variations
    'efootball-pes': 'efootball',
    'e-football': 'efootball',
    'pes': 'efootball',
    'pro-evolution-soccer': 'efootball',
    
    # Dota 2 variations
    'dota-2': 'dota2',
    'dota_2': 'dota2',
    
    # CS2 variations
    'cs-2': 'cs2',
    'cs_2': 'cs2',
    'counter-strike-2': 'cs2',
}

# Additional hyphen/underscore normalization patterns
# These are applied after basic normalization
PATTERN_ALIASES = {
    'pubg-mobile': 'pubg',
    'call-of-duty-mobile': 'codm',
    'mobile-legends': 'mlbb',
    'free-fire': 'freefire',
}


# ============================================================================
# NORMALIZATION FUNCTIONS
# ============================================================================

def normalize_slug(raw_code: str) -> str:
    """
    Normalize any game code/slug to canonical lowercase format.
    
    This is the primary normalization function used throughout the platform.
    It handles:
    - Case normalization (uppercase → lowercase)
    - Whitespace removal
    - Underscore → hyphen conversion
    - Legacy code mapping (csgo → cs2, fifa → fc26)
    - Platform suffix removal (pubg-mobile → pubg)
    
    Args:
        raw_code: Raw game identifier from any source
        
    Returns:
        Canonical lowercase slug, or original if no mapping found
        
    Examples:
        >>> normalize_slug('VALORANT')
        'valorant'
        >>> normalize_slug('CS:GO')
        'cs2'
        >>> normalize_slug('pubg-mobile')
        'pubg'
        >>> normalize_slug('Free_Fire')
        'freefire'
    """
    if not raw_code:
        return ''
    
    # Step 1: Basic normalization
    normalized = str(raw_code).lower().strip()
    
    # Step 2: Remove special characters (except hyphens)
    normalized = normalized.replace('_', '-')
    normalized = normalized.replace(':', '')
    normalized = normalized.replace(' ', '-')
    
    # Step 3: Check direct legacy mapping
    if normalized in LEGACY_ALIASES:
        return LEGACY_ALIASES[normalized]
    
    # Step 4: Check pattern aliases
    if normalized in PATTERN_ALIASES:
        return PATTERN_ALIASES[normalized]
    
    # Step 5: Try removing hyphens for compound names
    no_hyphen = normalized.replace('-', '')
    if no_hyphen in LEGACY_ALIASES:
        return LEGACY_ALIASES[no_hyphen]
    
    # Step 6: Return normalized form (may not be canonical)
    return normalized


def is_legacy_code(code: str) -> bool:
    """
    Check if a code is a legacy/deprecated identifier.
    
    Args:
        code: Game code to check
        
    Returns:
        True if this is a legacy code that maps to something else
    """
    if not code:
        return False
    
    normalized = code.lower().strip()
    return normalized in LEGACY_ALIASES and LEGACY_ALIASES[normalized] != normalized


def get_canonical_slug(code: str) -> str:
    """
    Alias for normalize_slug for clarity in some contexts.
    
    Args:
        code: Game code
        
    Returns:
        Canonical slug
    """
    return normalize_slug(code)


def get_all_aliases(canonical_slug: str) -> list[str]:
    """
    Get all known aliases for a canonical slug.
    
    Args:
        canonical_slug: Canonical game slug
        
    Returns:
        List of all aliases that map to this slug
        
    Example:
        >>> get_all_aliases('cs2')
        ['csgo', 'cs-go', 'cs_go', 'counter-strike-go', 'counter-strike']
    """
    return [
        alias for alias, target in LEGACY_ALIASES.items()
        if target == canonical_slug
    ]


def normalize_for_css(slug: str) -> str:
    """
    Normalize a slug for use in CSS attribute selectors.
    
    CSS data-game-slug attributes should use lowercase with hyphens.
    
    Args:
        slug: Game slug
        
    Returns:
        CSS-friendly slug with hyphens
        
    Example:
        >>> normalize_for_css('pubg')
        'pubg'
        >>> normalize_for_css('call_of_duty_mobile')
        'call-of-duty-mobile'
    """
    normalized = normalize_slug(slug)
    
    # Special cases for CSS themes that use different conventions
    css_overrides = {
        'pubg': 'pubg',  # CSS uses just 'pubg', not 'pubg-mobile'
        'codm': 'call-of-duty-mobile',  # CSS uses full name
        'mlbb': 'mobile-legends',  # CSS uses full name
        'freefire': 'free-fire',  # CSS uses hyphenated form
    }
    
    return css_overrides.get(normalized, normalized)


def normalize_for_database(slug: str) -> str:
    """
    Normalize a slug for database lookups.
    
    Database Game.slug field uses lowercase without special conventions.
    
    Args:
        slug: Game slug
        
    Returns:
        Database-friendly slug
    """
    return normalize_slug(slug)


# ============================================================================
# VALIDATION
# ============================================================================

def validate_slug(slug: str) -> tuple[bool, str]:
    """
    Validate if a slug is in canonical form.
    
    Args:
        slug: Slug to validate
        
    Returns:
        Tuple of (is_valid, message)
        
    Example:
        >>> validate_slug('valorant')
        (True, 'Valid canonical slug')
        >>> validate_slug('CS:GO')
        (False, 'Not in canonical form. Use: cs2')
    """
    if not slug:
        return False, 'Slug cannot be empty'
    
    canonical = normalize_slug(slug)
    
    if slug != canonical:
        return False, f'Not in canonical form. Use: {canonical}'
    
    return True, 'Valid canonical slug'
