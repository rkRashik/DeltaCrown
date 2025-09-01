# apps/tournaments/admin/exports.py
from django.http import HttpResponse
from django.utils import timezone
import csv

from .utils import _safe_select_related

# === VERBATIM MOVES (behavior-preserving) ===

def export_tournaments_csv(modeladmin, request, queryset):
    """
    Export selected Tournaments as CSV.
    Fields chosen to be stable and useful for ops/review.
    """
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"tournaments-{ts}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "id",
        "name",
        "slug",
        "status",
        "slot_size",
        "reg_open_at",
        "reg_close_at",
        "start_at",
        "end_at",
    ])

    for t in queryset.order_by("id"):
        writer.writerow([
            t.id,
            t.name,
            t.slug,
            getattr(t, "status", ""),
            getattr(t, "slot_size", ""),
            getattr(t, "reg_open_at", "") or "",
            getattr(t, "reg_close_at", "") or "",
            getattr(t, "start_at", "") or "",
            getattr(t, "end_at", "") or "",
        ])

    return response


# =========================================
# Admin Action: Export Disputes to CSV
# (schema-agnostic; header-only works with empty queryset)
# =========================================
def export_disputes_csv(modeladmin, request, queryset):
    """
    Export selected Disputes as CSV.
    Resilient to attribute/name differences and safe with an empty queryset.
    """
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"disputes-{ts}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "id",
        "match_id",
        "opened_by_username",
        "resolver_username",
        "status",
        "reason",
        "created_at",
        "resolved_at",
    ])

    queryset = _safe_select_related(
        queryset,
        [
            "match",
            "opened_by",
            "resolver",
            "opened_by__user",
            "resolver__user",
        ],
    )

    for d in queryset.order_by("id"):
        match = getattr(d, "match", None)
        match_id = getattr(match, "id", "")

        opened_by = (
            getattr(d, "opened_by", None)
            or getattr(d, "created_by", None)
            or getattr(d, "reporter", None)
            or getattr(getattr(d, "opened_profile", None), "user", None)
        )
        opened_user = getattr(opened_by, "user", opened_by)
        opened_username = getattr(opened_user, "username", "") if opened_user else ""

        resolver = getattr(d, "resolver", None) or getattr(d, "resolved_by", None)
        resolver_user = getattr(resolver, "user", resolver)
        resolver_username = getattr(resolver_user, "username", "") if resolver_user else ""

        status = getattr(d, "status", "") or getattr(d, "state", "") or ""
        reason = getattr(d, "reason", None) or getattr(d, "message", None) or getattr(d, "note", None) or ""

        created_at = (
            getattr(d, "created_at", None)
            or getattr(d, "created", None)
            or getattr(d, "created_on", None)
            or getattr(d, "timestamp", None)
            or ""
        )
        resolved_at = getattr(d, "resolved_at", None) or getattr(d, "closed_at", None) or ""

        writer.writerow([
            getattr(d, "id", ""),
            match_id,
            opened_username,
            resolver_username,
            status,
            reason,
            created_at,
            resolved_at,
        ])

    return response


# =========================================
# Admin Action: Export Matches to CSV
# (schema-agnostic; header-only works with empty queryset)
# =========================================
def export_matches_csv(modeladmin, request, queryset):
    """
    Export selected Matches as CSV.
    Resilient to attribute/name differences and safe with an empty queryset.
    """
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"matches-{ts}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "id",
        "tournament_id",
        "tournament_name",
        "round_no",
        "state",
        "participant_a",
        "participant_b",
        "scheduled_at",
        "reported_score_a",
        "reported_score_b",
        "winner_id",
        "created_at",
    ])

    try:
        queryset = _safe_select_related(
            queryset,
            [
                "tournament",
                "user_a", "user_b",
                "team_a", "team_b",
                "winner",
            ],
        )
    except Exception:
        pass

    for m in queryset.order_by("id"):
        t = getattr(m, "tournament", None)
        t_id = getattr(t, "id", "")
        t_name = getattr(t, "name", "")

        ua = getattr(m, "user_a", None)
        ub = getattr(m, "user_b", None)
        ta = getattr(m, "team_a", None)
        tb = getattr(m, "team_b", None)

        def _name(obj, *candidates):
            for c in candidates:
                v = getattr(obj, c, None)
                if v:
                    return str(v)
            return str(obj) if obj else ""

        participant_a = _name(ua, "username", "display_name") if ua else _name(ta, "tag", "name")
        participant_b = _name(ub, "username", "display_name") if ub else _name(tb, "tag", "name")

        state = getattr(m, "state", None) or getattr(m, "status", None) or ""

        scheduled_at = (
            getattr(m, "scheduled_at", None)
            or getattr(m, "start_at", None)
            or getattr(m, "scheduled_time", None)
            or ""
        )

        score_a = getattr(m, "score_a", None) or getattr(m, "reported_score_a", None) or ""
        score_b = getattr(m, "score_b", None) or getattr(m, "reported_score_b", None) or ""

        winner = getattr(m, "winner", None)
        winner_id = getattr(winner, "id", "") if winner else ""

        created_at = (
            getattr(m, "created_at", None)
            or getattr(m, "created", None)
            or getattr(m, "created_on", None)
            or getattr(m, "timestamp", None)
            or ""
        )

        writer.writerow([
            getattr(m, "id", ""),
            t_id,
            t_name,
            getattr(m, "round_no", ""),
            state,
            participant_a,
            participant_b,
            scheduled_at,
            score_a,
            score_b,
            winner_id,
            created_at,
        ])

    return response
