# apps/economy/utils.py
"""
Utility helpers that sit between the economy service layer and views.
Lightweight – no heavy imports; resolves models lazily.
"""
from __future__ import annotations

from django.apps import apps


def get_team_wallet_context(team) -> dict | None:
    """
    Return a wallet-summary dict for the team owner's wallet.
    For org teams, returns the org master wallet context if available.
    Returns None if no wallet exists or the economy module isn't wired.
    """
    try:
        DeltaCrownWallet = apps.get_model("economy", "DeltaCrownWallet")
        TeamMembership = apps.get_model("organizations", "TeamMembership")
    except LookupError:
        return None

    # Find the owner membership
    owner = (
        TeamMembership.objects
        .filter(team=team, role="OWNER", status='ACTIVE')
        .select_related("user__profile")
        .first()
    )
    if not owner:
        return None

    profile = getattr(owner.user, "profile", None)
    if not profile:
        return None

    wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)

    return {
        "balance": wallet.cached_balance,
        "held_balance": getattr(wallet, "pending_balance", 0),
        "lifetime_earned": getattr(wallet, "lifetime_earnings", 0),
        "has_payment_method": wallet.has_payment_method() if hasattr(wallet, "has_payment_method") else False,
    }


def get_owner_payment_methods(team) -> dict:
    """
    Return the owner's saved payment methods (bKash, Nagad, Rocket, bank)
    as a dict for template rendering.
    """
    try:
        DeltaCrownWallet = apps.get_model("economy", "DeltaCrownWallet")
        TeamMembership = apps.get_model("organizations", "TeamMembership")
    except LookupError:
        return {}

    owner = (
        TeamMembership.objects
        .filter(team=team, role="OWNER", status='ACTIVE')
        .select_related("user__profile")
        .first()
    )
    if not owner:
        return {}

    profile = getattr(owner.user, "profile", None)
    if not profile:
        return {}

    wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)

    def _mask(number: str) -> str:
        """Mask all but last 4 chars: 01712345678 → *******5678"""
        if not number or len(number) < 5:
            return number
        return "*" * (len(number) - 4) + number[-4:]

    return {
        "bkash": {
            "number": wallet.bkash_number,
            "masked": _mask(wallet.bkash_number),
            "active": bool(wallet.bkash_number),
        },
        "nagad": {
            "number": wallet.nagad_number,
            "masked": _mask(wallet.nagad_number),
            "active": bool(wallet.nagad_number),
        },
        "rocket": {
            "number": wallet.rocket_number,
            "masked": _mask(wallet.rocket_number),
            "active": bool(wallet.rocket_number),
        },
        "bank": {
            "account_name": wallet.bank_account_name,
            "account_number": wallet.bank_account_number,
            "masked_number": _mask(wallet.bank_account_number),
            "bank_name": wallet.bank_name,
            "branch": wallet.bank_branch,
            "active": bool(wallet.bank_account_number),
        },
    }
