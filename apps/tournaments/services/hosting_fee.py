"""
DeltaCoin Hosting Fee Service.

Calculates and charges the tournament hosting fee in DeltaCoin.
All business logic now delegates to TournamentHostingConfig (DB singleton),
making every rule admin-configurable without code deployments.

Fee resolution order (first match wins):
  1. hosting_fee_enabled = False          → 0 DC (everything free)
  2. Staff bypass (if enabled)            → 0 DC for staff/superuser
  3. Active promo = ALWAYS_FREE           → 0 DC
  4. Active promo = TIME_BASED            → 0 DC while before deadline
  5. Active promo = FIRST_N_USERS         → 0 DC while slots remain
  6. Active promo = FIRST_N_TOURNAMENTS   → 0 DC while slots remain
  7. Base hosting fee                     → hosting_fee_dc

Used by: apps.tournaments.views.create.TournamentCreatePageView
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Hardcoded fallback — only used if DB is unreachable
DEFAULT_HOSTING_FEE = 500


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_config():
    """
    Return the TournamentHostingConfig singleton (auto-creating with defaults
    if it doesn't exist yet).

    Returns None only if the DB is completely unreachable.
    """
    try:
        from apps.tournaments.models.hosting_config import TournamentHostingConfig
        return TournamentHostingConfig.get_solo()
    except Exception as exc:
        logger.warning("Could not load TournamentHostingConfig: %s", exc)
        return None


def get_hosting_fee() -> int:
    """
    Return the base hosting fee (no per-user promo checks).
    Used for display purposes on the creation wizard.

    Returns:
        int: DC amount (0 = free).
    """
    config = get_config()
    if config is not None:
        return config.effective_fee()

    # settings fallback
    try:
        from django.conf import settings
        fee = getattr(settings, "TOURNAMENT_HOSTING_FEE", None)
        if fee is not None:
            return int(fee)
    except Exception:
        pass

    return DEFAULT_HOSTING_FEE


def get_hosting_fee_for_user(user) -> int:
    """
    Return the actual fee for a specific user, honouring all active
    promotions and bypass rules.

    Args:
        user: Django User instance.

    Returns:
        int: DC amount the user must pay (0 = free).
    """
    config = get_config()
    if config is not None:
        return config.get_hosting_fee_for_user(user)

    # Fallback: staff always free, others pay default
    if user and (user.is_staff or user.is_superuser):
        return 0
    return get_hosting_fee()


def get_user_balance(user) -> int:
    """
    Return the user's current DeltaCoin balance.

    Args:
        user: Django User instance.

    Returns:
        int: Current DC balance (0 if lookup fails).
    """
    if not user or not user.is_authenticated:
        return 0
    try:
        from apps.tournament_ops.adapters.economy_adapter import EconomyAdapter
        adapter = EconomyAdapter()
        result = adapter.get_balance(user_id=user.id)
        return int(result.get("balance", 0))
    except Exception as exc:
        logger.warning("Failed to get DeltaCoin balance for user %s: %s", user.id, exc)
        return 0


def can_afford_hosting(user) -> bool:
    """
    Check if a user can afford the hosting fee (taking promos into account).

    Args:
        user: Django User instance.

    Returns:
        bool: True if user can host (free or has enough DC).
    """
    fee = get_hosting_fee_for_user(user)
    if fee == 0:
        return True
    return get_user_balance(user) >= fee


def get_promo_context() -> dict:
    """
    Return promo display data for the tournament creation wizard.

    Returns:
        dict with keys: is_active, label, description, slots_remaining, promo_type
    """
    config = get_config()
    if config is None:
        return {"is_active": False}

    return {
        "is_active": config.is_promo_active(),
        "label": config.promo_label,
        "description": config.promo_description,
        "slots_remaining": config.promo_slots_remaining(),
        "promo_type": config.active_promo,
    }


def get_user_restrictions(user) -> dict:
    """
    Return the effective permission set for a user creating a tournament.
    Used by the creation wizard to show/hide fields.

    Returns:
        dict of boolean/integer restrictions.
    """
    config = get_config()
    if config is None or user.is_staff or user.is_superuser:
        # Staff: unrestricted
        return {
            "can_create_official": True,
            "can_feature": True,
            "can_set_deltacoin_prize": True,
            "max_deltacoin_prize": 0,
            "max_participants": 0,
            "max_active_tournaments": 0,
            "allowed_formats": [],
            "can_charge_entry_fee": True,
            "is_staff": True,
        }

    return {
        "can_create_official": config.user_can_create_official,
        "can_feature": config.user_can_feature_tournament,
        "can_set_deltacoin_prize": config.user_can_set_deltacoin_prize,
        "max_deltacoin_prize": config.user_max_deltacoin_prize,
        "max_participants": config.user_max_participants,
        "max_active_tournaments": config.user_max_active_tournaments,
        "allowed_formats": config.get_allowed_formats(),
        "can_charge_entry_fee": config.user_can_charge_entry_fee,
        "is_staff": False,
    }


def charge_hosting_fee(user, tournament) -> Optional[Dict[str, Any]]:
    """
    Deduct the hosting fee from user's DeltaCoin balance.
    Also consumes a promo slot if a first-N promo is active.

    Staff/superuser are exempt. Returns None if fee is 0.

    Args:
        user: Django User instance (the organizer).
        tournament: Tournament instance (for transaction metadata).

    Returns:
        Dict with transaction details, or None if exempt/free.

    Raises:
        PaymentFailedError: If user has insufficient balance or charge fails.
    """
    config = get_config()
    fee = get_hosting_fee_for_user(user)

    if fee <= 0:
        # Still consume promo slot if first-N promo
        if config is not None:
            config.consume_promo_slot()
        logger.info(
            "Hosting fee waived for user %s (tournament: %s) — fee=%d",
            user.username, getattr(tournament, "slug", "?"), fee,
        )
        return None

    from apps.economy.services import debit
    from apps.tournament_ops.exceptions import PaymentFailedError
    from apps.user_profile.models import UserProfile

    reason = f"Tournament hosting fee (tournament #{tournament.id})"
    idempotency_key = f"tournament-hosting-fee-{user.id}-{tournament.id}"
    meta = {
        "tournament_id": tournament.id,
        "type": "tournament_hosting_fee",
        "organizer_id": user.id,
    }

    logger.info(
        "Charging hosting fee of %d DC to user %s for tournament %s",
        fee, user.username, getattr(tournament, "slug", "?"),
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
    except UserProfile.DoesNotExist as exc:
        logger.error(
            "Hosting fee charge failed: UserProfile missing for user %s (tournament: %s)",
            user.id, tournament.id,
        )
        raise PaymentFailedError(
            "Unable to charge hosting fee: organizer profile was not found."
        ) from exc
    except Exception as exc:
        logger.error(
            "Hosting fee charge failed for user %s (tournament: %s): %s",
            user.id, tournament.id, exc,
            exc_info=True,
        )
        message = "Unable to charge tournament hosting fee."
        if "insufficient" in str(exc).lower():
            message = "Insufficient DeltaCoin balance to pay the tournament hosting fee."
        raise PaymentFailedError(f"{message} Details: {exc}") from exc

    # Consume promo slot on successful payment too (shouldn't happen but safety)
    if config is not None:
        config.consume_promo_slot()

    return {
        "transaction_id": str(result.get("transaction_id", "")),
        "amount": fee,
        "currency": "DC",
        "status": "completed",
        "balance_after": result.get("balance_after", None),
        "metadata": meta,
    }
