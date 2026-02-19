"""
DeltaCrown Admin Callbacks — Phase 2

Provides:
- environment_callback: Status badge in admin top-bar (DEV / STAGING / PROD)
- environment_title: Prefix for page title in non-production environments
- dashboard_callback: Visual command center with tournament stats, registrations,
  match activity, economy overview, user metrics, trend charts, quick actions,
  top tournaments, upcoming events, and platform health indicators
"""

import json
import os
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.urls import reverse
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
# Helpers
# ---------------------------------------------------------------------------
def _safe_percentage(part, whole):
    """Return integer percentage, capped at 100."""
    if not whole:
        return 0
    return min(int(round(part / whole * 100)), 100)


def _week_label(dt):
    """Return short week label like 'Jan 6'."""
    start_of_week = dt - timedelta(days=dt.weekday())
    return start_of_week.strftime("%b %d")


# ---------------------------------------------------------------------------
# Dashboard callback — Phase 2
# ---------------------------------------------------------------------------
def dashboard_callback(request, context):
    """
    Unfold dashboard callback.
    Injects comprehensive stats, charts, tables, quick actions, and health
    indicators for the DeltaCrown admin command center.
    """
    from apps.accounts.models import User
    from apps.tournaments.models import Tournament, Registration, Match

    now = timezone.now()
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)
    two_months_ago = now - timedelta(days=56)

    # ══════════════════════════════════════════════════════════════════════
    # CORE STATS
    # ══════════════════════════════════════════════════════════════════════

    # ── Tournament stats ─────────────────────────────────────────────────
    total_tournaments = Tournament.objects.count()
    live_tournaments = Tournament.objects.filter(status="live").count()
    draft_tournaments = Tournament.objects.filter(status="draft").count()
    open_reg = Tournament.objects.filter(status="registration_open").count()
    completed = Tournament.objects.filter(status="completed").count()
    cancelled = Tournament.objects.filter(status="cancelled").count()

    # ── Registration stats ───────────────────────────────────────────────
    total_registrations = Registration.objects.count()
    pending_registrations = Registration.objects.filter(
        status__in=["pending", "submitted", "needs_review", "payment_submitted"]
    ).count()
    confirmed_registrations = Registration.objects.filter(status="confirmed").count()
    recent_registrations = Registration.objects.filter(
        created_at__gte=month_ago
    ).count()
    rejected_registrations = Registration.objects.filter(
        status__in=["rejected", "denied"]
    ).count()

    # ── Match stats ──────────────────────────────────────────────────────
    total_matches = Match.objects.count()
    live_matches = Match.objects.filter(state="live").count()
    disputed_matches = Match.objects.filter(state="disputed").count()
    completed_matches = Match.objects.filter(state="completed").count()
    recent_matches = Match.objects.filter(created_at__gte=week_ago).count()
    scheduled_matches = Match.objects.filter(state="scheduled").count()

    # ── User stats ───────────────────────────────────────────────────────
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users_month = User.objects.filter(date_joined__gte=month_ago).count()
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()
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

    # ── Organization / Team stats (safe import) ──────────────────────────
    try:
        from apps.organizations.models import Organization, Team

        total_orgs = Organization.objects.count()
        total_teams = Team.objects.count()
        active_teams = Team.objects.filter(is_active=True).count()
    except Exception:
        total_orgs = 0
        total_teams = 0
        active_teams = 0

    # ══════════════════════════════════════════════════════════════════════
    # CHARTS
    # ══════════════════════════════════════════════════════════════════════

    # ── Tournament status breakdown (bar chart) ──────────────────────────
    status_labels = [
        "Draft", "Pending", "Published", "Reg Open",
        "Reg Closed", "Live", "Completed", "Cancelled",
    ]
    status_keys = [
        "draft", "pending_approval", "published", "registration_open",
        "registration_closed", "live", "completed", "cancelled",
    ]
    status_counts = [
        Tournament.objects.filter(status=key).count() for key in status_keys
    ]

    chart_status = json.dumps({
        "labels": status_labels,
        "datasets": [{
            "label": "Tournaments",
            "data": status_counts,
            "backgroundColor": [
                "oklch(70% .02 260)",   # Draft — grey
                "oklch(75% .15 60)",    # Pending — amber
                "oklch(70% .15 200)",   # Published — blue
                "oklch(75% .18 150)",   # Reg Open — green
                "oklch(65% .12 30)",    # Reg Closed — orange
                "oklch(65% .20 140)",   # Live — emerald
                "oklch(60% .16 200)",   # Completed — cyan
                "oklch(55% .22 25)",    # Cancelled — red
            ],
            "borderRadius": 6,
            "borderWidth": 0,
        }],
    })

    # ── Registration trend (line chart — last 8 weeks) ───────────────────
    week_labels = []
    reg_weekly_data = []
    match_weekly_data = []

    for i in range(7, -1, -1):
        w_start = now - timedelta(weeks=i + 1)
        w_end = now - timedelta(weeks=i)
        week_labels.append(_week_label(w_end))
        reg_weekly_data.append(
            Registration.objects.filter(
                created_at__gte=w_start, created_at__lt=w_end
            ).count()
        )
        match_weekly_data.append(
            Match.objects.filter(
                created_at__gte=w_start, created_at__lt=w_end
            ).count()
        )

    chart_trends = json.dumps({
        "labels": week_labels,
        "datasets": [
            {
                "label": "Registrations",
                "data": reg_weekly_data,
                "borderColor": "oklch(70% .18 200)",
                "backgroundColor": "oklch(70% .18 200 / .15)",
                "fill": True,
                "tension": 0.4,
                "pointRadius": 4,
                "pointHoverRadius": 6,
                "borderWidth": 2,
            },
            {
                "label": "Matches",
                "data": match_weekly_data,
                "borderColor": "oklch(65% .20 140)",
                "backgroundColor": "oklch(65% .20 140 / .1)",
                "fill": True,
                "tension": 0.4,
                "pointRadius": 4,
                "pointHoverRadius": 6,
                "borderWidth": 2,
            },
        ],
    })

    # ══════════════════════════════════════════════════════════════════════
    # TABLES
    # ══════════════════════════════════════════════════════════════════════

    # ── Recent registrations ─────────────────────────────────────────────
    latest_regs = (
        Registration.objects.select_related("tournament")
        .order_by("-created_at")[:8]
    )

    reg_table_headers = ["Tournament", "Status", "Created"]
    reg_table_rows = []
    for reg in latest_regs:
        t_name = str(reg.tournament) if reg.tournament else "\u2014"
        if len(t_name) > 40:
            t_name = t_name[:37] + "\u2026"

        # Color-coded status badge
        status_colors = {
            "confirmed": "\u2705",
            "pending": "\u23f3",
            "submitted": "\U0001f4e8",
            "needs_review": "\u26a0\ufe0f",
            "rejected": "\u274c",
            "denied": "\u274c",
            "cancelled": "\U0001f6ab",
        }
        status_icon = status_colors.get(reg.status, "\u2b1c")
        reg_table_rows.append([
            t_name,
            f"{status_icon} {reg.status}",
            reg.created_at.strftime("%b %d, %H:%M"),
        ])

    # ── Upcoming tournaments ─────────────────────────────────────────────
    upcoming_statuses = ["registration_open", "registration_closed", "published"]
    upcoming_tournaments = (
        Tournament.objects.filter(status__in=upcoming_statuses)
        .order_by("tournament_start")[:6]
    )

    upcoming_table_headers = ["Tournament", "Status", "Start Date", "Slots"]
    upcoming_table_rows = []
    for t in upcoming_tournaments:
        t_name = str(t)
        if len(t_name) > 35:
            t_name = t_name[:32] + "\u2026"

        status_map = {
            "registration_open": "\U0001f7e2 Open",
            "registration_closed": "\U0001f534 Closed",
            "published": "\U0001f4d6 Published",
        }
        status_display = status_map.get(t.status, t.status)

        start_date = ""
        if t.tournament_start:
            start_date = t.tournament_start.strftime("%b %d, %Y")

        slot_info = "\u2014"
        if t.max_participants:
            filled = Registration.objects.filter(
                tournament=t, status="confirmed"
            ).count()
            slot_info = f"{filled}/{t.max_participants}"

        upcoming_table_rows.append([t_name, status_display, start_date or "\u2014", slot_info])

    # ── Top tournaments by registrations ─────────────────────────────────
    from django.db.models import Count

    top_tournaments = (
        Tournament.objects.annotate(reg_count=Count("registrations"))
        .order_by("-reg_count")[:5]
    )

    top_table_headers = ["Tournament", "Registrations", "Status"]
    top_table_rows = []
    for t in top_tournaments:
        t_name = str(t)
        if len(t_name) > 35:
            t_name = t_name[:32] + "\u2026"
        top_table_rows.append([t_name, str(t.reg_count), t.status.replace("_", " ").title()])

    # ══════════════════════════════════════════════════════════════════════
    # QUICK ACTIONS
    # ══════════════════════════════════════════════════════════════════════
    try:
        quick_actions = [
            {
                "title": "Create Tournament",
                "icon": "add_circle",
                "href": reverse("admin:tournaments_tournament_add"),
                "variant": "primary",
                "description": "Launch a new tournament",
            },
            {
                "title": "Pending Reviews",
                "icon": "pending_actions",
                "href": reverse("admin:tournaments_registration_changelist") + "?status__exact=pending",
                "variant": "secondary",
                "description": f"{pending_registrations} awaiting review",
                "badge": pending_registrations,
            },
            {
                "title": "Live Now",
                "icon": "live_tv",
                "href": reverse("admin:tournaments_tournament_changelist") + "?status__exact=live",
                "variant": "secondary",
                "description": f"{live_tournaments} tournaments live",
                "badge": live_tournaments,
            },
            {
                "title": "Disputes",
                "icon": "gavel",
                "href": reverse("admin:tournaments_match_changelist") + "?state__exact=disputed",
                "variant": "danger" if disputed_matches > 0 else "secondary",
                "description": f"{disputed_matches} need resolution",
                "badge": disputed_matches,
            },
        ]
    except Exception:
        quick_actions = []

    # ══════════════════════════════════════════════════════════════════════
    # HEALTH / PROGRESS INDICATORS
    # ══════════════════════════════════════════════════════════════════════
    completion_rate = _safe_percentage(completed_matches, total_matches) if total_matches else 0
    confirmation_rate = _safe_percentage(confirmed_registrations, total_registrations) if total_registrations else 0
    user_activation = _safe_percentage(active_users, total_users) if total_users else 0
    tournament_completion = _safe_percentage(completed, total_tournaments) if total_tournaments else 0

    health_indicators = [
        {
            "title": "Match Completion",
            "value": completion_rate,
            "description": f"{completion_rate}%",
            "color": "green" if completion_rate >= 70 else "amber" if completion_rate >= 40 else "red",
        },
        {
            "title": "Registration Confirmation",
            "value": confirmation_rate,
            "description": f"{confirmation_rate}%",
            "color": "green" if confirmation_rate >= 60 else "amber" if confirmation_rate >= 30 else "red",
        },
        {
            "title": "User Activation",
            "value": user_activation,
            "description": f"{user_activation}%",
            "color": "green" if user_activation >= 80 else "amber" if user_activation >= 50 else "red",
        },
        {
            "title": "Tournament Completion",
            "value": tournament_completion,
            "description": f"{tournament_completion}%",
            "color": "green" if tournament_completion >= 50 else "amber" if tournament_completion >= 20 else "red",
        },
    ]

    # ══════════════════════════════════════════════════════════════════════
    # INJECT ALL DATA
    # ══════════════════════════════════════════════════════════════════════
    context.update({
        # ── Core stats ───────────────────────────────────────────────────
        "dc_total_tournaments": total_tournaments,
        "dc_live_tournaments": live_tournaments,
        "dc_draft_tournaments": draft_tournaments,
        "dc_open_reg": open_reg,
        "dc_completed_tournaments": completed,
        "dc_cancelled_tournaments": cancelled,
        "dc_total_registrations": total_registrations,
        "dc_pending_registrations": pending_registrations,
        "dc_confirmed_registrations": confirmed_registrations,
        "dc_rejected_registrations": rejected_registrations,
        "dc_recent_registrations": recent_registrations,
        "dc_total_matches": total_matches,
        "dc_live_matches": live_matches,
        "dc_disputed_matches": disputed_matches,
        "dc_completed_matches": completed_matches,
        "dc_scheduled_matches": scheduled_matches,
        "dc_recent_matches": recent_matches,
        "dc_total_users": total_users,
        "dc_active_users": active_users,
        "dc_new_users_month": new_users_month,
        "dc_new_users_week": new_users_week,
        "dc_staff_users": staff_users,
        "dc_total_wallets": total_wallets,
        "dc_recent_transactions": recent_transactions,
        # ── Org/Team stats ───────────────────────────────────────────────
        "dc_total_orgs": total_orgs,
        "dc_total_teams": total_teams,
        "dc_active_teams": active_teams,
        # ── Charts ───────────────────────────────────────────────────────
        "dc_chart_status": chart_status,
        "dc_chart_trends": chart_trends,
        # ── Tables ───────────────────────────────────────────────────────
        "dc_reg_table": {
            "headers": reg_table_headers,
            "rows": reg_table_rows,
        },
        "dc_upcoming_table": {
            "headers": upcoming_table_headers,
            "rows": upcoming_table_rows,
        },
        "dc_top_table": {
            "headers": top_table_headers,
            "rows": top_table_rows,
        },
        # ── Quick actions ────────────────────────────────────────────────
        "dc_quick_actions": quick_actions,
        # ── Health indicators ────────────────────────────────────────────
        "dc_health": health_indicators,
        # ── Meta ─────────────────────────────────────────────────────────
        "dc_greeting": _get_greeting(request.user),
        "dc_current_time": now.strftime("%A, %B %d · %I:%M %p"),
    })
    return context


def _get_greeting(user):
    """Return time-appropriate greeting for the admin user."""
    hour = timezone.now().hour
    if hour < 12:
        prefix = "Good morning"
    elif hour < 17:
        prefix = "Good afternoon"
    else:
        prefix = "Good evening"
    name = user.get_short_name() or user.username
    return f"{prefix}, {name}"
