from datetime import timedelta
from decimal import Decimal
from django.db.models import Count, Max
from django.utils import timezone

def _safe_revenue(entry_fee_bdt, verified_count: int) -> Decimal:
    try:
        fee = Decimal(entry_fee_bdt or 0)
    except Exception:
        fee = Decimal("0")
    return fee * Decimal(verified_count or 0)

def tournament_stats(tournament):
    """
    Returns a dict with registration, match, bracket and notification stats.
    """
    # --- Registrations ---
    regs = tournament.registrations.all()
    total_regs = regs.count()
    confirmed = regs.filter(status="CONFIRMED").count()
    pending = regs.filter(status="PENDING").count()
    checked_in = regs.filter(status="CHECKED_IN").count()
    withdrawn = regs.filter(status="WITHDRAWN").count()

    solo_regs = regs.filter(user__isnull=False).count()
    team_regs = regs.filter(team__isnull=False).count()

    verified_payments = regs.filter(payment_status="verified").count()
    revenue_bdt = _safe_revenue(getattr(tournament, "entry_fee_bdt", 0), verified_payments)

    # --- Matches ---
    matches = tournament.matches.all()
    total_matches = matches.count()
    by_state = {row["state"]: row["n"] for row in matches.values("state").annotate(n=Count("id"))}
    unscheduled = matches.filter(start_at__isnull=True).count()

    now = timezone.now()
    next24 = matches.filter(start_at__gte=now, start_at__lt=now + timedelta(hours=24)).count()
    max_round = matches.aggregate(max_round=Max("round_no"))["max_round"] or 0

    # --- Bracket ---
    b = getattr(tournament, "bracket", None)
    bracket_status = "Locked" if (b and b.is_locked) else ("Generated" if b else "Missing")

    # --- Notifications (optional) ---
    notifications_total = 0
    try:
        from apps.notifications.models import Notification
        notifications_total = Notification.objects.filter(tournament=tournament).count()
    except Exception:
        # notifications app may not be installed yet
        pass

    return {
        "registrations": {
            "total": total_regs,
            "confirmed": confirmed,
            "pending": pending,
            "checked_in": checked_in,
            "withdrawn": withdrawn,
            "solo": solo_regs,
            "team": team_regs,
            "verified_payments": verified_payments,
            "revenue_bdt": revenue_bdt,
        },
        "matches": {
            "total": total_matches,
            "by_state": by_state,
            "unscheduled": unscheduled,
            "upcoming_24h": next24,
            "max_round": max_round,
        },
        "bracket": {
            "status": bracket_status,
        },
        "notifications": {
            "total": notifications_total,
        },
    }
