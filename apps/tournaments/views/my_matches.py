from __future__ import annotations

import csv
import io
from datetime import timedelta
from typing import List

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..models import Match, Tournament
from ..models.userprefs import SavedMatchFilter, PinnedTournament, CalendarFeedToken

User = get_user_model()


def _has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


def _remote_model(model, fieldname: str):
    try:
        f = model._meta.get_field(fieldname)
        return getattr(f.remote_field, "model", None)
    except Exception:
        return None


def _valid_lookup(qs, lookup: str, value) -> bool:
    """Probe the ORM safely to see if a lookup is valid for this schema."""
    try:
        qs.filter(**{lookup: value}).exists()
        return True
    except Exception:
        return False


def _user_match_qs(django_user):
    """
    Scope matches to the current user, adapting to either:
      - Match.user_a/user_b -> auth.User
      - Match.user_a/user_b -> UserProfile (with .user O2O to auth.User)
    Team membership lookups are omitted for robustness; we can add once names are confirmed.
    """
    select_fields = ["tournament"]
    for f in ("team_a", "team_b", "user_a", "user_b"):
        if _has_field(Match, f):
            select_fields.append(f)

    qs = Match.objects.select_related(*select_fields).order_by("-start_at")

    lookups: List[str] = []
    # user_a
    if _has_field(Match, "user_a"):
        target = _remote_model(Match, "user_a")
        if target is User:
            lookups.append("user_a")
        else:
            # likely UserProfile with .user
            lookups.append("user_a__user")
    # user_b
    if _has_field(Match, "user_b"):
        target = _remote_model(Match, "user_b")
        if target is User:
            lookups.append("user_b")
        else:
            lookups.append("user_b__user")

    q = Q()
    for lp in lookups:
        if _valid_lookup(qs, lp, django_user):
            q |= Q(**{lp: django_user})

    # If nothing matched (no user_a/user_b), fall back to empty (no user scoping).
    if q:
        qs = qs.filter(q).distinct()

    return qs


def _apply_filters(qs, params):
    game = (params.get("game") or "").strip().lower()
    state = (params.get("state") or "").strip().lower()
    tournament_id = params.get("tournament_id")
    start_date = params.get("start_date")
    end_date = params.get("end_date")

    if game:
        qs = qs.filter(tournament__game__iexact=game)
    if state:
        qs = qs.filter(state__iexact=state)
    if tournament_id:
        qs = qs.filter(tournament_id=tournament_id)
    if start_date:
        qs = qs.filter(start_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(start_at__date__lte=end_date)
    return qs


@login_required
def my_matches(request):
    qs = _user_match_qs(request.user)

    # default saved filter
    initial = {}
    default_sf = SavedMatchFilter.objects.filter(user=request.user, is_default=True).first()
    if default_sf and request.GET.get("use_default", "1") == "1" and not any(
        k in request.GET for k in ["game", "state", "tournament_id", "start_date", "end_date"]
    ):
        initial = {
            "game": default_sf.game or "",
            "state": default_sf.state or "",
            "tournament_id": default_sf.tournament_id or "",
            "start_date": default_sf.start_date.isoformat() if default_sf.start_date else "",
            "end_date": default_sf.end_date.isoformat() if default_sf.end_date else "",
        }

    params = {
        "game": request.GET.get("game", initial.get("game", "")),
        "state": request.GET.get("state", initial.get("state", "")),
        "tournament_id": request.GET.get("tournament_id", initial.get("tournament_id", "")),
        "start_date": request.GET.get("start_date", initial.get("start_date", "")),
        "end_date": request.GET.get("end_date", initial.get("end_date", "")),
        "q": request.GET.get("q", "").strip(),
    }
    qs = _apply_filters(qs, params)

    now = timezone.now()
    counters = {
        "upcoming": _apply_filters(_user_match_qs(request.user), params).filter(start_at__gte=now).count(),
        "live": _apply_filters(_user_match_qs(request.user), params).filter(state__iexact="live").count(),
        "completed": _apply_filters(_user_match_qs(request.user), params).filter(state__in=["verified", "completed"]).count(),
    }

    pin_ids = list(PinnedTournament.objects.filter(user=request.user).values_list("tournament_id", flat=True))
    pinned = Tournament.objects.filter(id__in=pin_ids)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # 14-day heat counts
    heat_qs = _apply_filters(_user_match_qs(request.user), params)
    heat_counts = (
        heat_qs.filter(start_at__date__gte=now.date(), start_at__date__lte=(now + timedelta(days=14)).date())
        .values("start_at__date").annotate(c=Count("id"))
    )
    heat_map = {str(row["start_at__date"]): row["c"] for row in heat_counts}

    token = CalendarFeedToken.issue_for(request.user)

    return render(
        request,
        "dashboard/my_matches.html",
        {
            "page_obj": page_obj,
            "params": params,
            "counters": counters,
            "pinned": pinned,
            "pins_ids": set(pin_ids),
            "heat_map": heat_map,
            "ics_token": token.token,
        },
    )


@login_required
@require_http_methods(["POST"])
def save_default_filter(request):
    sf, _ = SavedMatchFilter.objects.get_or_create(user=request.user, name="Default", defaults={"is_default": True})
    sf.is_default = True
    sf.game = request.POST.get("game", "")
    sf.state = request.POST.get("state", "")
    sf.tournament_id = request.POST.get("tournament_id") or None
    sf.start_date = request.POST.get("start_date") or None
    sf.end_date = request.POST.get("end_date") or None
    sf.save()
    return redirect("tournaments:my_matches")


@login_required
@require_http_methods(["POST"])
def toggle_pin(request, tournament_id: int):
    obj, created = PinnedTournament.objects.get_or_create(user=request.user, tournament_id=tournament_id)
    if not created:
        obj.delete()
    return redirect("tournaments:my_matches")


@login_required
def my_matches_csv(request):
    qs = _apply_filters(_user_match_qs(request.user), request.GET)
    buffer = io.StringIO()
    w = csv.writer(buffer)
    w.writerow(["Match ID", "Tournament", "Game", "Starts At", "State", "Side A", "Side B", "Score"])
    for m in qs[:5000]:
        side_a = getattr(m, "team_a_name", getattr(getattr(m, "team_a", None), "name", getattr(getattr(m, "user_a", None), "username", "")))
        side_b = getattr(m, "team_b_name", getattr(getattr(m, "team_b", None), "name", getattr(getattr(m, "user_b", None), "username", "")))
        w.writerow([
            m.id,
            getattr(m.tournament, "name", ""),
            getattr(m.tournament, "game", ""),
            m.start_at.isoformat() if m.start_at else "",
            getattr(m, "state", ""),
            side_a, side_b,
            getattr(m, "score_text", ""),
        ])
    resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="my_matches.csv"'
    return resp


def _token_user_or_404(token: str):
    try:
        cft = CalendarFeedToken.objects.select_related("user").get(token=token)
        return cft.user
    except CalendarFeedToken.DoesNotExist:
        raise Http404("Invalid token")


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


@login_required
def my_matches_ics_link(request):
    tok = CalendarFeedToken.issue_for(request.user).token
    return render(request, "dashboard/ics_help.html", {"token": tok})


def my_matches_ics(request, token: str):
    user = _token_user_or_404(token)
    qs = _apply_filters(_user_match_qs(user), request.GET)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DeltaCrown//My Matches//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for m in qs[:500]:
        start = (m.start_at or timezone.now()).astimezone(timezone.utc)
        end = start + timedelta(minutes=getattr(m, "duration_minutes", 60))
        title_a = getattr(m, "team_a_name", getattr(getattr(m, "team_a", None), "name", getattr(getattr(m, "user_a", None), "username", "")))
        title_b = getattr(m, "team_b_name", getattr(getattr(m, "team_b", None), "name", getattr(getattr(m, "user_b", None), "username", "")))
        summary = f"{getattr(m.tournament, 'name','')} — {title_a} vs {title_b}"
        uid = f"deltacrown-match-{m.id}@deltacrown"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{start.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{_ics_escape(summary)}",
            f"DESCRIPTION:{_ics_escape(getattr(m, 'notes',''))}",
            "END:VEVENT",
        ]
    resp = HttpResponse("\r\n".join(lines), content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="my_matches.ics"'
    return resp
