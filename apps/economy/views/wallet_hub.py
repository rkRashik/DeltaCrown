# apps/economy/views/wallet_hub.py
"""
Wallet Hub — the primary SPA-style economy entry point for users.

Serves the wallet_hub.html template with real context data for:
  - DeltaCrownWallet (balance, payment methods)
  - DeltaCrownTransaction history (latest 20)
  - PrizeClaim queryset
  - Top-up packages (static data — upgrade to a DB model when needed)
"""
from __future__ import annotations

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.economy.models import DeltaCrownTransaction, PrizeClaim
from apps.economy.services import wallet_for


# ---------------------------------------------------------------------------
# Static package catalogue
# Replace with a DB-backed model query (e.g. EconomyConfig) when packages
# need to be admin-editable without a code deploy.
# ---------------------------------------------------------------------------
TOPUP_PACKAGES = [
    {"id": 1, "name": "Rookie Pack",       "dc": 100,  "price_bdt": 10,  "icon": "fa-seedling",   "popular": False},
    {"id": 2, "name": "Challenger Stash",  "dc": 500,  "price_bdt": 50,  "icon": "fa-box",        "popular": False},
    {"id": 3, "name": "Pro Bundle",        "dc": 1000, "price_bdt": 100, "icon": "fa-layer-group","popular": True},
    {"id": 4, "name": "Elite Reserve",     "dc": 5000, "price_bdt": 500, "icon": "fa-gem",        "popular": False},
]


def _current_profile(user):
    """Get or lazily create the user's UserProfile."""
    UserProfile = apps.get_model("user_profile", "UserProfile")
    profile = getattr(user, "userprofile", None)
    if profile:
        return profile
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"display_name": getattr(user, "username", str(user.pk))},
    )
    return profile


@login_required
def wallet_hub_view(request: HttpRequest) -> HttpResponse:
    """
    Wallet Hub — closed-loop economy SPA.

    GET params:
      ?tab=overview|acquire|ledger|claims|rules
          Consumed by JS on page load to activate the correct tab.
    """
    profile = _current_profile(request.user)
    wallet = wallet_for(profile)

    # Latest 20 transactions (ordered by model Meta: -created_at)
    transactions = (
        DeltaCrownTransaction.objects
        .filter(wallet=wallet)
        .order_by("-created_at", "-id")[:20]
    )

    # All prize claims for this wallet, newest first
    claims = (
        PrizeClaim.objects
        .filter(wallet=wallet)
        .order_by("-submitted_at")
    )

    # Count of non-resolved claims (for nav badge)
    pending_claims_count = claims.filter(
        status__in=[PrizeClaim.Status.PENDING, PrizeClaim.Status.VERIFYING_KYC]
    ).count()

    ctx = {
        "wallet":               wallet,
        "transactions":         transactions,
        "claims":               claims,
        "packages":             TOPUP_PACKAGES,
        "pending_claims_count": pending_claims_count,
        # Expose topup endpoint URL for the JS gateway buttons
        "topup_api_url":        "/api/topup/request/",
        # CSRF token is available in templates via {{ csrf_token }} — no need to pass it here
    }
    return render(request, "economy/wallet_hub.html", ctx)
