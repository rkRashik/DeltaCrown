"""
Safety utilities for guaranteed UserProfile access.

UP-M0: Safety Net & Inventory
These utilities provide atomic, guaranteed profile access with proper error handling.
All profile access should use these utilities to prevent DoesNotExist crashes.

See: Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_01_CORE_USER_PROFILE_ARCHITECTURE.md
"""
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from typing import Tuple
import logging
import time

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
