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
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

# Cache TTL for dashboard data (seconds)
_DASHBOARD_CACHE_TTL = 60  # 1 minute — fresh enough for admin, avoids repeated DB hits


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
    from django.db.models import Count, Q, F
    from django.db.models.functions import TruncWeek

    now = timezone.now()

    # ── Try serving from cache first ─────────────────────────────────────
    cache_key = 'admin_dashboard_data_v2'
    cached = cache.get(cache_key)
    if cached:
        context.update(cached)
        # Always refresh greeting/time (cheap, user-specific)
        context["dc_greeting"] = _get_greeting(request.user)
        context["dc_current_time"] = now.strftime("%A, %B %d · %I:%M %p")
        return context

    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)

    # ══════════════════════════════════════════════════════════════════════
    # CORE STATS
    # ══════════════════════════════════════════════════════════════════════

    # ── Tournament stats (single aggregated query) ───────────────────────
    _t_agg = Tournament.objects.aggregate(
        total=Count('id'),
        live=Count('id', filter=Q(status='live')),
        draft=Count('id', filter=Q(status='draft')),
        open_reg=Count('id', filter=Q(status='registration_open')),
        completed=Count('id', filter=Q(status='completed')),
        cancelled=Count('id', filter=Q(status='cancelled')),
    )
    total_tournaments = _t_agg['total']
    live_tournaments = _t_agg['live']
    draft_tournaments = _t_agg['draft']
    open_reg = _t_agg['open_reg']
    completed = _t_agg['completed']
    cancelled = _t_agg['cancelled']

    # ── Registration stats (single aggregated query) ─────────────────────
    _r_agg = Registration.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status__in=["pending", "submitted", "needs_review", "payment_submitted"])),
        confirmed=Count('id', filter=Q(status='confirmed')),
        recent=Count('id', filter=Q(created_at__gte=month_ago)),
        rejected=Count('id', filter=Q(status__in=["rejected", "denied"])),
    )
    total_registrations = _r_agg['total']
    pending_registrations = _r_agg['pending']
    confirmed_registrations = _r_agg['confirmed']
    recent_registrations = _r_agg['recent']
    rejected_registrations = _r_agg['rejected']

    # ── Match stats (single aggregated query) ────────────────────────────
    _m_agg = Match.objects.aggregate(
        total=Count('id'),
        live=Count('id', filter=Q(state='live')),
        disputed=Count('id', filter=Q(state='disputed')),
        completed=Count('id', filter=Q(state='completed')),
        recent=Count('id', filter=Q(created_at__gte=week_ago)),
        scheduled=Count('id', filter=Q(state='scheduled')),
    )
    total_matches = _m_agg['total']
    live_matches = _m_agg['live']
    disputed_matches = _m_agg['disputed']
    completed_matches = _m_agg['completed']
    recent_matches = _m_agg['recent']
    scheduled_matches = _m_agg['scheduled']

    # ── User stats (single aggregated query) ─────────────────────────────
    _u_agg = User.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True)),
        new_month=Count('id', filter=Q(date_joined__gte=month_ago)),
        new_week=Count('id', filter=Q(date_joined__gte=week_ago)),
        staff=Count('id', filter=Q(is_staff=True)),
    )
    total_users = _u_agg['total']
    active_users = _u_agg['active']
    new_users_month = _u_agg['new_month']
    new_users_week = _u_agg['new_week']
    staff_users = _u_agg['staff']

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

    # ── Organization / Team stats (safe import, single query) ──────────
    try:
        from apps.organizations.models import Organization, Team
        from django.db.models import Q as _Q

        total_orgs = Organization.objects.count()
        _team_agg = Team.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=_Q(is_active=True)),
        )
        total_teams = _team_agg['total']
        active_teams = _team_agg['active']
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
    # Single aggregate query instead of 8 separate COUNT queries
    _status_agg = Tournament.objects.values('status').annotate(c=Count('id'))
    _status_map = {row['status']: row['c'] for row in _status_agg}
    status_counts = [_status_map.get(key, 0) for key in status_keys]

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
    # Two aggregate queries instead of 16 individual queries
    _trend_start = now - timedelta(weeks=9)
    _reg_weekly_qs = (
        Registration.objects.filter(created_at__gte=_trend_start)
        .annotate(week=TruncWeek('created_at'))
        .values('week').annotate(c=Count('id')).order_by('week')
    )
    _match_weekly_qs = (
        Match.objects.filter(created_at__gte=_trend_start)
        .annotate(week=TruncWeek('created_at'))
        .values('week').annotate(c=Count('id')).order_by('week')
    )
    _reg_by_week = {row['week'].date(): row['c'] for row in _reg_weekly_qs}
    _match_by_week = {row['week'].date(): row['c'] for row in _match_weekly_qs}

    week_labels = []
    reg_weekly_data = []
    match_weekly_data = []

    for i in range(7, -1, -1):
        w_end = now - timedelta(weeks=i)
        w_key = (w_end - timedelta(days=w_end.weekday())).date()  # Monday of that week
        week_labels.append(_week_label(w_end))
        reg_weekly_data.append(_reg_by_week.get(w_key, 0))
        match_weekly_data.append(_match_by_week.get(w_key, 0))

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
        Registration.objects
        .select_related("tournament", "user")
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
    # Annotate confirmed count to avoid N+1 per-tournament query
    upcoming_tournaments = (
        Tournament.objects.filter(status__in=upcoming_statuses)
        .annotate(
            confirmed_count=Count(
                'registrations',
                filter=Q(registrations__status='confirmed'),
            )
        )
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
            slot_info = f"{t.confirmed_count}/{t.max_participants}"

        upcoming_table_rows.append([t_name, status_display, start_date or "\u2014", slot_info])

    # ── Top tournaments by registrations ─────────────────────────────────
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
    dashboard_data = {
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
    }

    # Cache the dashboard payload (excludes user-specific greeting/time)
    cache.set(cache_key, dashboard_data, _DASHBOARD_CACHE_TTL)

    context.update(dashboard_data)
    context.update({
        # ── Meta (user-specific, never cached) ───────────────────────────
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
