"""
Safety utilities for guaranteed UserProfile access.

UP-M0: Safety Net & Inventory
These utilities provide atomic, guaranteed profile access with proper error handling.
All profile access should use these utilities to prevent DoesNotExist crashes.

See: Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_01_CORE_USER_PROFILE_ARCHITECTURE.md
"""
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.conf import settings
from typing import Tuple, Optional
import logging
import time
from functools import lru_cache
from django.contrib.staticfiles import finders

logger = logging.getLogger(__name__)

User = get_user_model()


def get_or_create_user_profile(user, max_retries: int = 3) -> Tuple['UserProfile', bool]:
    """
    Atomic, guaranteed profile access with retry logic.
    
    This is the SAFE way to access user.profile. Never use user.profile directly
    without checking hasattr() first, or use this utility instead.
    
    Args:
        user: User instance (must be saved to database)
        max_retries: Number of retry attempts on race condition (default 3)
    
    Returns:
        Tuple[UserProfile, bool]: (profile, created) where created=True if new profile
    
    Raises:
        ValueError: If user is not saved (no pk)
        RuntimeError: If profile creation fails after max_retries
    
    Example:
        >>> profile, created = get_or_create_user_profile(request.user)
        >>> if created:
        >>>     logger.info(f"Created missing profile for {request.user.username}")
    
    Note:
        - Uses atomic transaction with select_for_update to prevent race conditions
        - Retries up to max_retries times on IntegrityError (concurrent creation)
        - Signals will fire on profile creation (privacy settings, verification record, etc.)
        - Does NOT expose PII in logs (only username, pk)
    
    Architecture Reference:
        UP-01 Section 1: "Invariant: Every User MUST have exactly one UserProfile"
        This utility enforces the invariant programmatically.
    """
    from apps.user_profile.models import UserProfile
    
    if not user.pk:
        raise ValueError("Cannot get_or_create profile for unsaved user (user.pk is None)")
    
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                # Lock the user row to prevent concurrent profile creation
                locked_user = User.objects.select_for_update().get(pk=user.pk)
                
                # Check if profile already exists
                try:
                    profile = UserProfile.objects.select_for_update().get(user=locked_user)
                    return (profile, False)
                except UserProfile.DoesNotExist:
                    pass
                
                # Create profile with default display_name
                profile = UserProfile.objects.create(
                    user=locked_user,
                    display_name=locked_user.username or locked_user.email or f"User{locked_user.pk}"
                )
                logger.info(
                    f"Created UserProfile for user_id={locked_user.pk} "
                    f"username={locked_user.username} (attempt {attempt + 1}/{max_retries})"
                )
                return (profile, True)
        
        except IntegrityError as e:
            # Race condition: Another process created profile between check and create
            if attempt < max_retries - 1:
                logger.warning(
                    f"IntegrityError creating profile for user_id={user.pk} "
                    f"(attempt {attempt + 1}/{max_retries}), retrying... Error: {e}"
                )
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                continue
            else:
                # Final attempt failed, try one last read
                try:
                    profile = UserProfile.objects.get(user=user)
                    logger.info(
                        f"Profile exists after IntegrityError for user_id={user.pk}, "
                        "returning existing profile"
                    )
                    return (profile, False)
                except UserProfile.DoesNotExist:
                    raise RuntimeError(
                        f"Failed to create or retrieve profile for user_id={user.pk} "
                        f"after {max_retries} attempts. Last error: {e}"
                    )
    
    # Should never reach here, but satisfy type checker
    raise RuntimeError(
        f"Unexpected: get_or_create_user_profile exhausted retries for user_id={user.pk}"
    )


def get_user_profile_safe(user) -> 'UserProfile':
    """
    Convenience wrapper: Get profile or create if missing, return profile only.
    
    Args:
        user: User instance
    
    Returns:
        UserProfile: User's profile (guaranteed to exist)
    
    Raises:
        ValueError: If user is not saved
        RuntimeError: If profile creation fails
    
    Example:
        >>> profile = get_user_profile_safe(request.user)
        >>> # No need to check if profile exists, guaranteed non-None
    """
    profile, _ = get_or_create_user_profile(user)
    return profile


# ============================================================================
# Game Icons Utility (Phase 4D)
# ============================================================================

from django.templatetags.static import static

# Comprehensive map of game slugs to their icon filenames
GAME_ICON_MAP = {
    # MOBAs
    'league_of_legends': 'league-of-legends.svg',
    'dota_2': 'dota-2.svg',
    'mobile_legends': 'mobile-legends.svg',
    
    # Battle Royales
    'fortnite': 'fortnite.svg',
    'apex_legends': 'apex-legends.svg',
    'pubg': 'pubg.svg',
    'pubg_mobile': 'pubg-mobile.svg',
    'call_of_duty_warzone': 'cod-warzone.svg',
    
    # FPS
    'counter_strike_2': 'cs2.svg',
    'cs2': 'cs2.svg',
    'csgo': 'cs2.svg',  # Alias
    'valorant': 'valorant.svg',
    'rainbow_six_siege': 'rainbow-six.svg',
    'overwatch_2': 'overwatch-2.svg',
    'call_of_duty': 'call-of-duty.svg',
    
    # Fighting Games
    'street_fighter_6': 'street-fighter-6.svg',
    'tekken_8': 'tekken-8.svg',
    'mortal_kombat': 'mortal-kombat.svg',
    'super_smash_bros': 'smash-bros.svg',
    
    # Sports
    'fifa': 'fifa.svg',
    'ea_sports_fc': 'ea-fc.svg',
    'nba_2k': 'nba-2k.svg',
    'rocket_league': 'rocket-league.svg',
    
    # Strategy
    'starcraft_2': 'starcraft-2.svg',
    'age_of_empires': 'age-of-empires.svg',
    'clash_royale': 'clash-royale.svg',
    
    # Card Games
    'hearthstone': 'hearthstone.svg',
    'legends_of_runeterra': 'legends-of-runeterra.svg',
    'magic_the_gathering_arena': 'mtg-arena.svg',
    
    # Other
    'minecraft': 'minecraft.svg',
    'genshin_impact': 'genshin-impact.svg',
}

DEFAULT_ICON = 'default-game.svg'
ICON_SEARCH_PATTERNS = (
    'user_profile/game_icons/{filename}',
    'img/games/{filename}',
    'img/game_logos/logos/{filename}',
)
FINAL_FALLBACK_ICON_PATH = 'img/teams/default-logo.svg'


def get_game_icon_path(game_slug: str) -> str:
    """
    Get the filename for a game icon.
    
    Args:
        game_slug: Game identifier (e.g., 'valorant', 'counter_strike_2')
    
    Returns:
        str: Icon filename (e.g., 'valorant.svg', 'default-game.svg')
    """
    return GAME_ICON_MAP.get(game_slug, DEFAULT_ICON)


def _build_unhashed_static_url(static_path: str) -> str:
    """
    Build a STATIC_URL-based path without manifest lookup.

    This is the last-resort fallback when staticfiles manifest resolution
    fails for all candidates, ensuring profile pages never crash.
    """
    static_url = getattr(settings, 'STATIC_URL', '/static/') or '/static/'
    return f"{static_url.rstrip('/')}/{static_path.lstrip('/')}"


def _safe_static(static_path: str) -> Optional[str]:
    """
    Resolve a static path through Django's storage backend.

    Returns None when Manifest storage cannot resolve the file so callers can
    attempt other candidates safely.
    """
    try:
        return static(static_path)
    except ValueError:
        return None


def _static_path_exists(static_path: str) -> bool:
    """
    Check whether a static asset path is discoverable by Django staticfiles.

    We verify existence before resolving URLs so local/dev behavior matches
    production expectations for missing files.
    """
    try:
        return bool(finders.find(static_path))
    except Exception:
        return False


@lru_cache(maxsize=256)
def _resolve_game_icon_url(icon_filename: str) -> str:
    """
    Resolve icon URL with safe fallback order.

    1) Preferred profile icon namespace
    2) Legacy shared game icon namespaces
    3) Default icon filename in same namespaces
    4) Final guaranteed fallback icon URL
    """
    candidate_paths = [
        pattern.format(filename=icon_filename)
        for pattern in ICON_SEARCH_PATTERNS
    ]

    if icon_filename != DEFAULT_ICON:
        candidate_paths.extend(
            pattern.format(filename=DEFAULT_ICON)
            for pattern in ICON_SEARCH_PATTERNS
        )

    first_existing_path = None

    for static_path in candidate_paths:
        if not _static_path_exists(static_path):
            continue

        if first_existing_path is None:
            first_existing_path = static_path

        resolved = _safe_static(static_path)
        if resolved:
            return resolved

    if _static_path_exists(FINAL_FALLBACK_ICON_PATH):
        if first_existing_path is None:
            first_existing_path = FINAL_FALLBACK_ICON_PATH

        resolved_fallback = _safe_static(FINAL_FALLBACK_ICON_PATH)
        if resolved_fallback:
            return resolved_fallback

    if first_existing_path:
        return _build_unhashed_static_url(first_existing_path)

    return _build_unhashed_static_url(FINAL_FALLBACK_ICON_PATH)


def get_game_icon_url(game_slug: str) -> str:
    """
    Get the full static URL for a game icon.
    
    Args:
        game_slug: Game identifier
    
    Returns:
        str: Resolved static URL with safe fallback behavior
    """
    icon_filename = get_game_icon_path(game_slug)
    return _resolve_game_icon_url(icon_filename)


def has_custom_icon(game_slug: str) -> bool:
    """
    Check if a game has a custom icon or will use default.
    
    Args:
        game_slug: Game identifier
    
    Returns:
        bool: True if custom icon exists, False if will use default
    """
    return game_slug in GAME_ICON_MAP
