from __future__ import annotations
from datetime import datetime, timedelta
from typing import Iterable, Optional

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .forms import MyMatchesFilterForm


def _get_model(label: str):
    try:
        return apps.get_model(*label.split("."))
    except Exception:
        return None


def _get_user_profile(user) -> Optional[models.Model]:
    Profile = _get_model("user_profile.UserProfile")
    if not Profile:
        return None
    try:
        return Profile.objects.filter(user=user).first()
    except Exception:
        return None


def _team_fields_on_match(Match) -> list[str]:
    """Return FK field names on Match that point to Team (e.g., team1, team2, blue_team, red_team, home, away)."""
    Team = _get_model("teams.Team")
    names = []
    if not (Match and Team):
        return names
    for f in Match._meta.get_fields():
        if isinstance(f, models.ForeignKey):
            rel = getattr(f.remote_field, "model", None)
            if rel and getattr(rel, "_meta", None) and rel._meta.label_lower == "teams.team":
                names.append(f.name)
    return names


def _safe_attr(obj, name, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default


def _infer_status(match) -> str:
    """Map to: upcoming / live / completed. Permissive heuristics."""
    now = timezone.now()
    start = _safe_attr(match, "scheduled_at") or _safe_attr(match, "start_time") or _safe_attr(match, "starts_at")
    end = _safe_attr(match, "ended_at") or _safe_attr(match, "end_time") or _safe_attr(match, "finished_at")
    state = _safe_attr(match, "state") or _safe_attr(match, "status")

    if state:
        s = str(state).lower()
        if any(k in s for k in ("complete", "finished", "done", "result")):
            return "completed"
        if "live" in s or "ongoing" in s or "running" in s:
            return "live"
        if "upcoming" in s or "scheduled" in s or "pending" in s:
            return "upcoming"

    if end and end <= now:
        return "completed"
    if start:
        if start <= now and (not end or end > now):
            return "live"
        if start > now:
            return "upcoming"
    return "upcoming"


def _collect_user_teams(user) -> Iterable[models.Model]:
    Team = _get_model("teams.Team")
    if not Team:
        return Team.objects.none() if hasattr(Team, "objects") else []
    prof = _get_user_profile(user)

    q = Q()
    if prof:
        if "captain" in [f.name for f in Team._meta.get_fields()]:
            q |= Q(captain=prof)
    for fname in ("members", "players", "roster"):
        if any(getattr(f, "name", "") == fname for f in Team._meta.get_fields()):
            q |= Q(**{f"{fname}": prof})

    try:
        return Team.objects.filter(q).distinct()
    except Exception:
        return Team.objects.none()


def _filter_matches_for_user(user, form: MyMatchesFilterForm):
    # Ensure form is valid to populate cleaned_data
    if not hasattr(form, 'cleaned_data') or form.cleaned_data is None:
        form.is_valid()  # This will populate cleaned_data even for empty form
        
    # Double check that cleaned_data exists
    if not hasattr(form, 'cleaned_data'):
        # If form validation completely failed, create empty cleaned_data
        form.cleaned_data = {}
    
    Match = _get_model("tournaments.Match") or _get_model("matches.Match") or _get_model("brackets.Match")
    if not Match:
        return Match, []

    team_fields = _team_fields_on_match(Match)
    if not team_fields:
        return Match, []

    teams = list(_collect_user_teams(user))
    if not teams:
        return Match, []

    q = Q()
    for fname in team_fields:
        q |= Q(**{f"{fname}__in": teams})

    qs = Match.objects.filter(q).select_related()

    # Game filter
    game = form.cleaned_data.get("game")
    if game:
        if any(f.name == "game" for f in Match._meta.get_fields()):
            qs = qs.filter(game=game)
        else:
            for fname in team_fields:
                try:
                    qs = qs.filter(**{f"{fname}__game": game})
                    break
                except Exception:
                    continue

    # Tournament choices & filter
    Tournament = _get_model("tournaments.Tournament")
    tournament_choices = []
    tfield = None
    if Tournament:
        try:
            for f in Match._meta.get_fields():
                if isinstance(f, models.ForeignKey) and getattr(getattr(f, "remote_field", None), "model", None) == Tournament:
                    tfield = f.name
                    break
            if tfield:
                t_ids = qs.values_list(f"{tfield}", flat=True).distinct()
                t_qs = Tournament.objects.filter(id__in=t_ids)
                tournament_choices = [(str(t.id), getattr(t, "name", str(t))) for t in t_qs]
        except Exception:
            tournament_choices = []

    tournament = form.cleaned_data.get("tournament")
    if tournament and Tournament and tournament.isdigit() and tfield:
        qs = qs.filter(**{tfield: int(tournament)})

    # Date range
    df = form.cleaned_data.get("date_from")
    dt = form.cleaned_data.get("date_to")
    date_field = None
    for cand in ("scheduled_at", "start_time", "starts_at", "match_time", "created_at"):
        if any(f.name == cand for f in Match._meta.get_fields()):
            date_field = cand
            break
    if df and date_field:
        qs = qs.filter(**{f"{date_field}__date__gte": df})
    if dt and date_field:
        qs = qs.filter(**{f"{date_field}__date__lte": dt})

    # Status
    status = form.cleaned_data.get("status")
    if status:
        qs = [m for m in qs]
        if status == "upcoming":
            qs = [m for m in qs if _infer_status(m) == "upcoming"]
        elif status == "live":
            qs = [m for m in qs if _infer_status(m) == "live"]
        elif status == "completed":
            qs = [m for m in qs if _infer_status(m) == "completed"]
    else:
        qs = list(qs)

    # Search
    qtext = form.cleaned_data.get("q", "").strip()
    if qtext:
        lowered = qtext.lower()

        def _name_has(m):
            for fname in team_fields:
                t = _safe_attr(m, fname)
                nm = getattr(t, "name", "") if t else ""
                if lowered in str(nm).lower():
                    return True
            return False

        qs = [m for m in qs if _name_has(m)]

    # Sort: live → upcoming → completed; then by scheduled time
    def _sort_key(m):
        dtv = _safe_attr(m, "scheduled_at") or _safe_attr(m, "start_time") or _safe_attr(m, "starts_at") or timezone.now()
        st = _infer_status(m)
        order_bucket = {"live": 0, "upcoming": 1, "completed": 2}.get(st, 1)
        return (order_bucket, dtv)

    qs.sort(key=_sort_key)

    # NOTE: sometimes callers only expect (Match, matches). We'll return 3-tuple;
    # the view now handles both shapes safely.
    return Match, qs, tournament_choices


@login_required
def my_matches_view(request: HttpRequest) -> HttpResponse:
    form = MyMatchesFilterForm(request.GET or None)
    form.is_valid()  # populate cleaned_data even if empty

    res = _filter_matches_for_user(request.user, form)

    # Normalize result shapes: (Match, matches) or (Match, matches, tchoices)
    if not res:
        context = {"form": form, "matches": [], "team_fields": [], "tchoices": []}
        return render(request, "dashboard/my_matches.html", context)

    if isinstance(res, tuple):
        if len(res) == 2:
            Match, matches = res
            tchoices = []
        elif len(res) >= 3:
            Match, matches, tchoices = res[:3]
        else:
            Match, matches, tchoices = None, [], []
    else:
        Match, matches, tchoices = None, [], []

    if not matches:
        context = {"form": form, "matches": [], "team_fields": [], "tchoices": []}
        return render(request, "dashboard/matches.html", context)

    form.set_tournament_choices(tchoices or [])
    team_fields = _team_fields_on_match(Match) if Match else []

    # Map to simple dicts expected by template
    mapped = []
    for m in matches:
        when = (
            getattr(m, "scheduled_at", None)
            or getattr(m, "start_time", None)
            or getattr(m, "starts_at", None)
            or getattr(m, "start_at", None)
            or getattr(m, "created_at", None)
        )
        team1 = None
        team2 = None
        if hasattr(m, "team_a") or hasattr(m, "team_b"):
            team1 = getattr(getattr(m, "team_a", None), "name", None)
            team2 = getattr(getattr(m, "team_b", None), "name", None)
        elif hasattr(m, "user_a") or hasattr(m, "user_b"):
            team1 = getattr(getattr(m, "user_a", None), "display_name", None)
            team2 = getattr(getattr(m, "user_b", None), "display_name", None)
        mapped.append({
            "id": getattr(m, "id", None),
            "when": when,
            "team1_name": team1,
            "team2_name": team2,
            "score1": getattr(m, "score_a", None),
            "score2": getattr(m, "score_b", None),
            "tournament": getattr(m, "tournament", None),
        })

    context = {
        "form": form,
        "matches": mapped,
        "team_fields": team_fields,
    }
    return render(request, "dashboard/matches.html", context)
from django.contrib.auth.decorators import login_required



@login_required
def dashboard_index(request: HttpRequest) -> HttpResponse:
    """Simple dashboard landing with recent registrations and matches."""
    Registration = _get_model("tournaments.Registration")
    Match = _get_model("tournaments.Match") or _get_model("brackets.Match")

    regs = []
    try:
        prof = _get_user_profile(request.user)
        if Registration and prof:
            regs = (
                Registration.objects.filter(user=prof)
                .select_related("tournament")
                .order_by("-created_at")[:8]
            )
    except Exception:
        regs = []

    matches = []
    try:
        form = MyMatchesFilterForm({})
        form.is_valid()
        _, mlist, _ = _filter_matches_for_user(request.user, form)
        # Map minimal fields for index
        mapped = []
        for m in mlist[:8]:
            when = (
                getattr(m, "scheduled_at", None)
                or getattr(m, "start_time", None)
                or getattr(m, "starts_at", None)
                or getattr(m, "start_at", None)
                or getattr(m, "created_at", None)
            )
            mapped.append({"tournament": getattr(m, "tournament", None), "when": when})
        matches = mapped
    except Exception:
        matches = []

    context = {
        "registrations": regs,
        "matches": matches,
        "payouts": [],
    }
    return render(request, "dashboard/index.html", context)
