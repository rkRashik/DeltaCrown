"""
Loadout Query Helpers - Pro Settings Engine (P0)

Service functions for retrieving and filtering loadout data.

Design Reference: 03c_loadout_and_live_status_design.md
"""
from django.db.models import Q, QuerySet
from typing import Optional, List, Dict, Any
from apps.user_profile.models import HardwareGear, GameConfig


# ============================================================================
# HARDWARE GEAR QUERIES
# ============================================================================

def get_user_hardware(user, category: Optional[str] = None, public_only: bool = False) -> QuerySet:
    """
    Get user's hardware gear, optionally filtered by category.
    
    Args:
        user: User object
        category: HardwareGear.HardwareCategory choice (MOUSE, KEYBOARD, etc.)
        public_only: If True, only return public hardware
    
    Returns:
        QuerySet of HardwareGear objects
    
    Examples:
        >>> get_user_hardware(user, category='MOUSE')
        <QuerySet [<HardwareGear: testuser - Mouse: Logitech G Pro X Superlight>]>
        
        >>> get_user_hardware(user, public_only=True)
        <QuerySet [<HardwareGear: ...>, ...]>
    """
    queryset = HardwareGear.objects.filter(user=user)
    
    if category:
        queryset = queryset.filter(category=category)
    
    if public_only:
        queryset = queryset.filter(is_public=True)
    
    return queryset.select_related('user')


def get_hardware_by_brand(brand: str, category: Optional[str] = None, public_only: bool = True) -> QuerySet:
    """
    Find all users using hardware from a specific brand.
    
    Args:
        brand: Brand name (e.g., "Logitech", "Razer")
        category: Optional category filter
        public_only: If True, only return public hardware
    
    Returns:
        QuerySet of HardwareGear objects
    
    Examples:
        >>> get_hardware_by_brand('Logitech', category='MOUSE')
        <QuerySet [<HardwareGear: ...>, ...]>
    """
    queryset = HardwareGear.objects.filter(brand__iexact=brand)
    
    if category:
        queryset = queryset.filter(category=category)
    
    if public_only:
        queryset = queryset.filter(is_public=True)
    
    return queryset.select_related('user')


def get_popular_hardware(category: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get most popular hardware by usage count (public only).
    
    Args:
        category: HardwareGear.HardwareCategory choice
        limit: Number of results to return
    
    Returns:
        List of dicts with brand, model, count
    
    Examples:
        >>> get_popular_hardware('MOUSE', limit=5)
        [
            {'brand': 'Logitech', 'model': 'G Pro X Superlight', 'count': 42},
            {'brand': 'Razer', 'model': 'DeathAdder V3 Pro', 'count': 38},
            ...
        ]
    """
    from django.db.models import Count
    
    popular = (
        HardwareGear.objects
        .filter(category=category, is_public=True)
        .values('brand', 'model')
        .annotate(count=Count('id'))
        .order_by('-count')[:limit]
    )
    
    return list(popular)


# ============================================================================
# GAME CONFIG QUERIES
# ============================================================================

def get_user_game_configs(user, public_only: bool = False) -> QuerySet:
    """
    Get all game configs for a user.
    
    Args:
        user: User object
        public_only: If True, only return public configs
    
    Returns:
        QuerySet of GameConfig objects
    
    Examples:
        >>> get_user_game_configs(user)
        <QuerySet [<GameConfig: testuser - Valorant Config>, ...]>
    """
    queryset = GameConfig.objects.filter(user=user)
    
    if public_only:
        queryset = queryset.filter(is_public=True)
    
    return queryset.select_related('user', 'game')


def get_user_game_config(user, game_slug: str) -> Optional[GameConfig]:
    """
    Get user's config for a specific game.
    
    Args:
        user: User object
        game_slug: Game slug (e.g., 'valorant', 'cs2')
    
    Returns:
        GameConfig object or None
    
    Examples:
        >>> config = get_user_game_config(user, 'valorant')
        >>> config.settings
        {'sensitivity': 0.45, 'dpi': 800, 'crosshair_style': 'small_dot'}
    """
    try:
        return GameConfig.objects.select_related('user', 'game').get(
            user=user,
            game__slug=game_slug
        )
    except GameConfig.DoesNotExist:
        return None


def get_configs_by_game(game_slug: str, public_only: bool = True, limit: Optional[int] = None) -> QuerySet:
    """
    Get all configs for a specific game.
    
    Args:
        game_slug: Game slug (e.g., 'valorant')
        public_only: If True, only return public configs
        limit: Optional limit on results
    
    Returns:
        QuerySet of GameConfig objects
    
    Examples:
        >>> configs = get_configs_by_game('valorant', limit=20)
        >>> [c.user.username for c in configs]
        ['pro_player1', 'pro_player2', ...]
    """
    queryset = GameConfig.objects.filter(game__slug=game_slug)
    
    if public_only:
        queryset = queryset.filter(is_public=True)
    
    queryset = queryset.select_related('user', 'game').order_by('-updated_at')
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset


def search_configs_by_sensitivity(
    game_slug: str,
    min_sens: Optional[float] = None,
    max_sens: Optional[float] = None,
    public_only: bool = True
) -> QuerySet:
    """
    Search game configs by sensitivity range.
    
    Args:
        game_slug: Game slug
        min_sens: Minimum sensitivity (inclusive)
        max_sens: Maximum sensitivity (inclusive)
        public_only: If True, only return public configs
    
    Returns:
        QuerySet of GameConfig objects
    
    Examples:
        >>> configs = search_configs_by_sensitivity('valorant', min_sens=0.3, max_sens=0.5)
        >>> [(c.user.username, c.settings['sensitivity']) for c in configs]
        [('player1', 0.45), ('player2', 0.35), ...]
    
    Note:
        Requires settings JSON to have 'sensitivity' key.
        Uses JSON field query (Postgres).
    """
    queryset = GameConfig.objects.filter(game__slug=game_slug)
    
    if public_only:
        queryset = queryset.filter(is_public=True)
    
    # Filter by sensitivity range (JSON field query)
    if min_sens is not None:
        queryset = queryset.filter(settings__sensitivity__gte=min_sens)
    
    if max_sens is not None:
        queryset = queryset.filter(settings__sensitivity__lte=max_sens)
    
    return queryset.select_related('user', 'game')


def get_average_sensitivity(game_slug: str) -> Optional[float]:
    """
    Calculate average sensitivity for a game (public configs only).
    
    Args:
        game_slug: Game slug
    
    Returns:
        Average sensitivity or None if no configs
    
    Examples:
        >>> get_average_sensitivity('valorant')
        0.52
    
    Note:
        Only includes configs with 'sensitivity' key in settings.
    """
    from django.db.models import Avg
    from django.db.models.functions import Cast
    from django.db.models import FloatField
    
    # Query configs with sensitivity value
    queryset = GameConfig.objects.filter(
        game__slug=game_slug,
        is_public=True,
        settings__has_key='sensitivity'
    )
    
    # Extract sensitivity from JSON and calculate average
    # Note: This uses Postgres JSON operators
    result = queryset.annotate(
        sens_value=Cast('settings__sensitivity', FloatField())
    ).aggregate(avg_sens=Avg('sens_value'))
    
    return result['avg_sens']


# ============================================================================
# COMPLETE LOADOUT QUERIES
# ============================================================================

def get_complete_loadout(user, public_only: bool = False) -> Dict[str, Any]:
    """
    Get user's complete loadout (all hardware + all game configs).
    
    Args:
        user: User object
        public_only: If True, only return public items
    
    Returns:
        Dict with 'hardware' and 'game_configs' keys
    
    Examples:
        >>> loadout = get_complete_loadout(user)
        >>> loadout['hardware']
        {
            'MOUSE': <HardwareGear: ...>,
            'KEYBOARD': <HardwareGear: ...>,
            ...
        }
        >>> loadout['game_configs']
        [<GameConfig: ...>, ...]
    """
    # Get hardware grouped by category
    hardware_qs = get_user_hardware(user, public_only=public_only)
    hardware_dict = {hw.category: hw for hw in hardware_qs}
    
    # Get all game configs
    game_configs = list(get_user_game_configs(user, public_only=public_only))
    
    return {
        'hardware': hardware_dict,
        'game_configs': game_configs,
    }


def has_loadout(user) -> bool:
    """
    Check if user has any loadout data (hardware or game configs).
    
    Args:
        user: User object
    
    Returns:
        True if user has hardware or game configs
    
    Examples:
        >>> has_loadout(user)
        True
    """
    has_hardware = HardwareGear.objects.filter(user=user).exists()
    has_configs = GameConfig.objects.filter(user=user).exists()
    
    return has_hardware or has_configs
