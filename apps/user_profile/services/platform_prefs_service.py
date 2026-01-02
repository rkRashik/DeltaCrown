"""
Platform Preferences Service (Phase 5A)

SINGLE SOURCE OF TRUTH for user platform preferences.
Provides typed accessor API for reading/writing preferences with validation.

Usage:
    from apps.user_profile.services.platform_prefs_service import get_user_platform_prefs, set_user_platform_prefs
    
    # Get preferences (always returns defaults merged with stored values)
    prefs = get_user_platform_prefs(profile)  # or None for anonymous
    
    # Update preferences (validates and saves)
    updated_prefs = set_user_platform_prefs(profile, {
        'preferred_language': 'en',
        'timezone': 'Asia/Dhaka',
        'time_format': '12h',
        'currency': 'BDT'
    })
"""

import logging
from typing import Dict, Optional
from django.conf import settings
import pytz

logger = logging.getLogger(__name__)

# ===== CONSTANTS (SOURCE OF TRUTH) =====

AVAILABLE_LANGUAGES = [
    ('en', 'English'),
    ('bn', 'Bengali'),  # Ready for future, not fully translated yet
]

AVAILABLE_CURRENCIES = [
    ('BDT', 'BDT (৳)'),
    ('USD', 'USD ($)'),  # Future multi-currency support
]

TIME_FORMATS = [
    ('12h', '12-hour (3:00 PM)'),
    ('24h', '24-hour (15:00)'),
]

# Common timezones (not all 600+ for UI simplicity)
COMMON_TIMEZONES = [
    'Asia/Dhaka',
    'UTC',
    'Asia/Kolkata',
    'Asia/Dubai',
    'Europe/London',
    'Europe/Paris',
    'America/New_York',
    'America/Los_Angeles',
    'Asia/Tokyo',
    'Australia/Sydney',
]

# Default preferences
DEFAULT_PREFS = {
    'preferred_language': 'en',
    'timezone': 'Asia/Dhaka',
    'time_format': '12h',
    'currency': 'BDT',
}


# ===== VALIDATION FUNCTIONS =====

def validate_language(lang: str) -> bool:
    """Validate language code against allowed list."""
    return any(code == lang for code, _ in AVAILABLE_LANGUAGES)


def validate_timezone(tz: str) -> bool:
    """Validate timezone against pytz."""
    try:
        pytz.timezone(tz)
        return True
    except pytz.UnknownTimeZoneError:
        return False


def validate_time_format(fmt: str) -> bool:
    """Validate time format."""
    return fmt in ('12h', '24h')


def validate_currency(curr: str) -> bool:
    """Validate currency code."""
    return any(code == curr for code, _ in AVAILABLE_CURRENCIES)


# ===== ACCESSOR API =====

def get_user_platform_prefs(profile) -> Dict[str, str]:
    """
    Get user platform preferences.
    
    Returns defaults merged with stored values. Safe for anonymous (profile=None).
    
    Args:
        profile: UserProfile instance or None (anonymous)
    
    Returns:
        dict: Platform preferences (always has all keys)
    
    Example:
        >>> prefs = get_user_platform_prefs(user.profile)
        >>> prefs['timezone']  # 'Asia/Dhaka'
        >>> prefs['time_format']  # '12h'
    """
    if profile is None:
        return DEFAULT_PREFS.copy()
    
    # Read from model fields (Phase 6 Part C fields)
    prefs = DEFAULT_PREFS.copy()
    prefs['preferred_language'] = profile.preferred_language or DEFAULT_PREFS['preferred_language']
    prefs['timezone'] = profile.timezone_pref or DEFAULT_PREFS['timezone']
    prefs['time_format'] = profile.time_format or DEFAULT_PREFS['time_format']
    
    # Currency from system_settings JSON (future-proof)
    system_settings = profile.system_settings or {}
    prefs['currency'] = system_settings.get('currency', DEFAULT_PREFS['currency'])
    
    return prefs


def set_user_platform_prefs(profile, updates: Dict[str, str]) -> Dict[str, str]:
    """
    Update user platform preferences.
    
    Validates all fields before saving. Raises ValueError if invalid.
    
    Args:
        profile: UserProfile instance (required)
        updates: dict with keys: preferred_language, timezone, time_format, currency
    
    Returns:
        dict: Updated preferences
    
    Raises:
        ValueError: If validation fails
    
    Example:
        >>> set_user_platform_prefs(user.profile, {
        ...     'timezone': 'UTC',
        ...     'time_format': '24h'
        ... })
    """
    if profile is None:
        raise ValueError("Cannot set preferences for anonymous user")
    
    # Validate and update preferred_language
    if 'preferred_language' in updates:
        lang = updates['preferred_language']
        if not validate_language(lang):
            raise ValueError(f"Invalid language: {lang}. Must be one of: {[code for code, _ in AVAILABLE_LANGUAGES]}")
        profile.preferred_language = lang
    
    # Validate and update timezone
    if 'timezone' in updates:
        tz = updates['timezone']
        if not validate_timezone(tz):
            raise ValueError(f"Invalid timezone: {tz}. Must be a valid IANA timezone.")
        profile.timezone_pref = tz
    
    # Validate and update time_format
    if 'time_format' in updates:
        fmt = updates['time_format']
        if not validate_time_format(fmt):
            raise ValueError(f"Invalid time_format: {fmt}. Must be '12h' or '24h'.")
        profile.time_format = fmt
    
    # Validate and update currency (stored in system_settings JSON)
    if 'currency' in updates:
        curr = updates['currency']
        if not validate_currency(curr):
            raise ValueError(f"Invalid currency: {curr}. Must be one of: {[code for code, _ in AVAILABLE_CURRENCIES]}")
        
        system_settings = profile.system_settings or {}
        system_settings['currency'] = curr
        profile.system_settings = system_settings
    
    profile.save()
    logger.info(f"Updated platform preferences for user {profile.user.username}")
    
    return get_user_platform_prefs(profile)


def get_available_options() -> Dict[str, list]:
    """
    Get all available options for frontend dropdowns.
    
    Returns:
        dict: {
            'languages': [('en', 'English'), ...],
            'timezones': ['Asia/Dhaka', ...],
            'time_formats': [('12h', '12-hour'), ...],
            'currencies': [('BDT', 'BDT (৳)'), ...]
        }
    """
    return {
        'languages': AVAILABLE_LANGUAGES,
        'timezones': COMMON_TIMEZONES,
        'time_formats': TIME_FORMATS,
        'currencies': AVAILABLE_CURRENCIES,
    }
