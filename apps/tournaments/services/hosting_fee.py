"""
DeltaCoin Hosting Fee Service.

Calculates and charges the tournament hosting fee in DeltaCoin.
Default: 500 DC (flat). Admin-configurable via Django admin.

Staff/superuser accounts are exempt (free hosting).

Used by: apps.tournaments.views.create.TournamentCreatePageView
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default hosting fee in DeltaCoin
DEFAULT_HOSTING_FEE = 500


def get_hosting_fee() -> int:
    """
    Get the current tournament hosting fee from site config.

    Tries to load from SiteConfig model first (admin-adjustable),
    falls back to DEFAULT_HOSTING_FEE.

    Returns:
        int: Hosting fee in DeltaCoin.
    """
    try:
        from django.conf import settings
        fee = getattr(settings, 'TOURNAMENT_HOSTING_FEE', None)
        if fee is not None:
            return int(fee)
    except Exception:
        pass

    # Fallback to default
    return DEFAULT_HOSTING_FEE


def get_user_balance(user) -> int:
    """
    Get the user's current DeltaCoin balance.

    Args:
        user: Django User instance.

    Returns:
        int: Current DeltaCoin balance (0 if lookup fails).
    """
    if not user or not user.is_authenticated:
        return 0

    try:
        from apps.tournament_ops.adapters.economy_adapter import EconomyAdapter
        adapter = EconomyAdapter()
        result = adapter.get_balance(user_id=user.id)
        return int(result.get('balance', 0))
    except Exception as e:
        logger.warning("Failed to get DeltaCoin balance for user %s: %s", user.id, e)
        return 0


def can_afford_hosting(user) -> bool:
    """
    Check if a user can afford the hosting fee.

    Staff users always return True (free hosting).

    Args:
        user: Django User instance.

    Returns:
        bool: True if user can afford or is staff.
    """
    if user.is_staff or user.is_superuser:
        return True
    return get_user_balance(user) >= get_hosting_fee()


def charge_hosting_fee(user, tournament) -> Optional[Dict[str, Any]]:
    """
    Deduct the hosting fee from user's DeltaCoin balance.

    Staff/superuser users are exempt — returns None immediately.

    Args:
        user: Django User instance (the organizer).
        tournament: Tournament instance (for transaction metadata).

    Returns:
        Dict with transaction details, or None if exempt/free.

    Raises:
        PaymentFailedError: If user has insufficient balance or charge fails.
    """
    if user.is_staff or user.is_superuser:
        logger.info(
            "Hosting fee waived for staff user %s (tournament: %s)",
            user.username, tournament.slug,
        )
        return None

    fee = get_hosting_fee()
    if fee <= 0:
        return None

    from apps.economy.services import debit
    from apps.tournament_ops.exceptions import PaymentFailedError
    from apps.user_profile.models import UserProfile

    reason = f"Tournament hosting fee (tournament #{tournament.id})"
    idempotency_key = f"tournament-hosting-fee-{user.id}-{tournament.id}"
    meta = {
        'tournament_id': tournament.id,
        'type': 'tournament_hosting_fee',
        'organizer_id': user.id,
    }

    logger.info(
        "Charging hosting fee of %d DC to user %s for tournament %s",
        fee, user.username, tournament.slug,
    )

    try:
        profile = UserProfile.objects.get(user_id=user.id)
        result = debit(
            profile,
            fee,
            reason=reason,
            idempotency_key=idempotency_key,
            meta=meta,
        )
    except UserProfile.DoesNotExist as e:
        logger.error(
            "Hosting fee charge failed: UserProfile missing for user %s (tournament: %s)",
            user.id,
            tournament.id,
        )
        raise PaymentFailedError(
            "Unable to charge hosting fee: organizer profile was not found."
        ) from e
    except Exception as e:
        logger.error(
            "Hosting fee charge failed for user %s (tournament: %s): %s",
            user.id,
            tournament.id,
            e,
            exc_info=True,
        )

        message = "Unable to charge tournament hosting fee."
        if 'insufficient' in str(e).lower():
            message = "Insufficient DeltaCoin balance to pay the tournament hosting fee."

        raise PaymentFailedError(f"{message} Details: {e}") from e

    return {
        'transaction_id': str(result.get('transaction_id', '')),
        'amount': fee,
        'currency': 'DC',
        'status': 'completed',
        'balance_after': result.get('balance_after', None),
        'metadata': meta,
    }
