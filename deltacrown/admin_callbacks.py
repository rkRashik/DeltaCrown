"""
DeltaCrown Admin Callbacks — Phase 1.5

Provides:
- environment_callback: Status badge in admin top-bar (DEV / STAGING / PROD)
- environment_title: Prefix for page title in non-production environments
- dashboard_callback: Visual command center with tournament stats, registrations,
  match activity, economy overview, and user metrics
"""

import json
import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone


# ---------------------------------------------------------------------------
# Environment badge
# ---------------------------------------------------------------------------
def environment_callback(request):
    """Return environment name for the top-bar badge."""
    env = os.getenv("DJANGO_ENV", "development").lower()
    mapping = {
        "production": "Production",
        "staging": "Staging",
        "development": "Development",
    }
    return mapping.get(env, env.title())


def environment_title(request):
    """Return prefix for the browser tab title in non-production envs."""
    env = os.getenv("DJANGO_ENV", "development").lower()
    if env == "production":
        return None
    return env.upper()


# ---------------------------------------------------------------------------
# Dashboard callback — Phase 1.5.2
# ---------------------------------------------------------------------------
def dashboard_callback(request, context):
    """
    Unfold dashboard callback.
    Injects stats cards, activity feed, and chart data for the admin index page.
    """
    from apps.accounts.models import User
    from apps.tournaments.models import Tournament, Registration, Match

    now = timezone.now()
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)

    # ── Tournament stats ─────────────────────────────────────────────────
    total_tournaments = Tournament.objects.count()
    live_tournaments = Tournament.objects.filter(status="live").count()
    draft_tournaments = Tournament.objects.filter(status="draft").count()
    open_reg = Tournament.objects.filter(status="registration_open").count()
    completed = Tournament.objects.filter(status="completed").count()

    # ── Registration stats ───────────────────────────────────────────────
    total_registrations = Registration.objects.count()
    pending_registrations = Registration.objects.filter(
        status__in=["pending", "submitted", "needs_review", "payment_submitted"]
    ).count()
    confirmed_registrations = Registration.objects.filter(status="confirmed").count()
    recent_registrations = Registration.objects.filter(
        created_at__gte=month_ago
    ).count()

    # ── Match stats ──────────────────────────────────────────────────────
    total_matches = Match.objects.count()
    live_matches = Match.objects.filter(state="live").count()
    disputed_matches = Match.objects.filter(state="disputed").count()
    completed_matches = Match.objects.filter(state="completed").count()
    recent_matches = Match.objects.filter(created_at__gte=week_ago).count()

    # ── User stats ───────────────────────────────────────────────────────
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users_month = User.objects.filter(date_joined__gte=month_ago).count()
    staff_users = User.objects.filter(is_staff=True).count()

    # ── Economy stats (safe import) ──────────────────────────────────────
    try:
        from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction

        total_wallets = DeltaCrownWallet.objects.count()
        recent_transactions = DeltaCrownTransaction.objects.filter(
            created_at__gte=week_ago
        ).count()
    except Exception:
        total_wallets = 0
        recent_transactions = 0

    # ── Tournament status breakdown for chart ────────────────────────────
    status_labels = [
        "Draft", "Pending", "Published", "Reg Open",
        "Reg Closed", "Live", "Completed", "Cancelled",
    ]
    status_keys = [
        "draft", "pending_approval", "published", "registration_open",
        "registration_closed", "live", "completed", "cancelled",
    ]
    status_counts = []
    for key in status_keys:
        status_counts.append(Tournament.objects.filter(status=key).count())

    chart_data = json.dumps({
        "labels": status_labels,
        "datasets": [
            {
                "label": "Tournaments",
                "data": status_counts,
                "backgroundColor": [
                    "oklch(70% .02 260)",
                    "oklch(75% .15 60)",
                    "oklch(70% .15 200)",
                    "oklch(75% .18 150)",
                    "oklch(65% .12 30)",
                    "oklch(65% .20 140)",
                    "oklch(60% .16 200)",
                    "oklch(55% .22 25)",
                ],
            }
        ],
    })

    # ── Recent registrations table ───────────────────────────────────────
    latest_regs = (
        Registration.objects.select_related("tournament")
        .order_by("-created_at")[:8]
    )

    reg_table_headers = ["Tournament", "Status", "Created"]
    reg_table_rows = []
    for reg in latest_regs:
        t_name = str(reg.tournament) if reg.tournament else "\u2014"
        if len(t_name) > 40:
            t_name = t_name[:37] + "..."
        reg_table_rows.append(
            [t_name, reg.status, reg.created_at.strftime("%b %d, %H:%M")]
        )

    # ── Inject into context ──────────────────────────────────────────────
    context.update({
        # Stats cards
        "dc_total_tournaments": total_tournaments,
        "dc_live_tournaments": live_tournaments,
        "dc_draft_tournaments": draft_tournaments,
        "dc_open_reg": open_reg,
        "dc_completed_tournaments": completed,
        "dc_total_registrations": total_registrations,
        "dc_pending_registrations": pending_registrations,
        "dc_confirmed_registrations": confirmed_registrations,
        "dc_recent_registrations": recent_registrations,
        "dc_total_matches": total_matches,
        "dc_live_matches": live_matches,
        "dc_disputed_matches": disputed_matches,
        "dc_completed_matches": completed_matches,
        "dc_recent_matches": recent_matches,
        "dc_total_users": total_users,
        "dc_active_users": active_users,
        "dc_new_users_month": new_users_month,
        "dc_staff_users": staff_users,
        "dc_total_wallets": total_wallets,
        "dc_recent_transactions": recent_transactions,
        # Chart data
        "dc_tournament_chart": chart_data,
        # Table data
        "dc_reg_table": {
            "headers": reg_table_headers,
            "rows": reg_table_rows,
        },
    })
    return context
