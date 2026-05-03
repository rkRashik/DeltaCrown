# apps/economy/views/fortress.py
"""
Financial Fortress — SuperAdmin Economy Command Center
======================================================

Security Model (Three Layers):
  Layer 1  @login_required       — must be authenticated.
  Layer 2  @user_passes_test     — must be is_superuser; staff/admins are blocked.
  Layer 3  Sudo PIN modal        — client-side PIN gate before any write op fires;
                                   PIN is validated server-side on each API call.

All write operations (mint, airdrop, approve, reject) are handled by dedicated
POST endpoints in apps/economy/views/fortress_api.py (Phase D).
This view only renders the SPA shell with initial context.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from apps.economy.models import (
    DeltaCrownWallet,
    DeltaCrownTransaction,
    TopUpRequest,
    PrizeClaim,
)
from apps.economy.services import get_master_treasury


def _superuser_only(user) -> bool:
    """Predicate for @user_passes_test — is_superuser strictly enforced."""
    return user.is_active and user.is_superuser


@login_required(login_url="/admin/login/")
@user_passes_test(_superuser_only, login_url="/admin/login/")
def fortress_dashboard(request):
    """
    Financial Fortress SPA shell view.

    Context variables injected into the template for initial render.
    All dynamic data (approvals table, live charts) is loaded via JS
    fetch calls to the /economy/fortress/api/* endpoints (Phase D).
    """

    # ── Treasury ──────────────────────────────────────────────────────────────
    treasury = get_master_treasury()
    treasury_balance = int(treasury.cached_balance)  # negative = DC in circulation

    # ── Circulation ───────────────────────────────────────────────────────────
    circulating_supply = int(
        DeltaCrownWallet.objects
        .filter(is_treasury=False, deleted_at__isnull=True)
        .aggregate(total=Sum("cached_balance"))["total"] or 0
    )

    # ── Pending approvals counts ───────────────────────────────────────────────
    pending_topups_count = TopUpRequest.objects.filter(status="pending").count()
    pending_claims_count = PrizeClaim.objects.filter(status="pending").count()
    total_pending = pending_topups_count + pending_claims_count

    # ── Economy health check ───────────────────────────────────────────────────
    # Ledger is healthy when: circulation + treasury == 0
    ledger_delta = circulating_supply + treasury_balance
    ledger_healthy = (ledger_delta == 0)

    # ── Wallet count (basic platform metric) ──────────────────────────────────
    wallet_count = DeltaCrownWallet.objects.filter(is_treasury=False).count()

    # ── Recent transactions (for dashboard activity feed) ─────────────────────
    recent_transactions = (
        DeltaCrownTransaction.objects
        .select_related("wallet__profile__user", "created_by")
        .order_by("-created_at")[:10]
    )

    context = {
        # Treasury metrics
        "treasury_balance": treasury_balance,
        "circulating_supply": circulating_supply,
        "ledger_delta": ledger_delta,
        "ledger_healthy": ledger_healthy,

        # Approval counts
        "pending_topups_count": pending_topups_count,
        "pending_claims_count": pending_claims_count,
        "total_pending": total_pending,

        # Platform metrics
        "wallet_count": wallet_count,
        "recent_transactions": recent_transactions,

        # Superuser identity (for sidebar display)
        "admin_user": request.user,
        "now": timezone.now(),
    }

    return render(request, "economy/admin/fortress_dashboard.html", context)
