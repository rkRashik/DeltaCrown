# apps/tournaments/views/public.py
from __future__ import annotations

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..models import Tournament
from apps.corelib.admin_utils import _safe_select_related

# Generic fallback forms
from ..forms_registration import (
    SoloRegistrationForm as GenericSoloForm,
    TeamRegistrationForm as GenericTeamForm,
)

# Game-specific forms (import guarded)
try:  # pragma: no cover
    from apps.game_efootball.forms import EfootballSoloForm, EfootballDuoForm  # type: ignore
except Exception:  # pragma: no cover
    EfootballSoloForm = None
    EfootballDuoForm = None

try:  # pragma: no cover
    from apps.game_valorant.forms import ValorantTeamForm  # type: ignore
except Exception:  # pragma: no cover
    ValorantTeamForm = None


# --------------------
# Public list / detail
# --------------------
def tournament_list(request):
    """
    Public tournaments index with simple filters + pagination.
    """
    qs = Tournament.objects.all()
    qs = _safe_select_related(qs, "settings")

    # Filters
    q = (request.GET.get("q") or "").strip()
    game = (request.GET.get("game") or "").strip()
    status = (request.GET.get("status") or "").strip()
    entry = (request.GET.get("entry") or "").strip()

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))
    if game:
        qs = qs.filter(game__iexact=game)

    now = timezone.now()
    # be tolerant to either start_at/end_at (datetime) or start_date/end_date (date)
    if status:
        start_at = getattr(Tournament, "start_at", None)
        end_at = getattr(Tournament, "end_at", None)
        start_date = getattr(Tournament, "start_date", None)
        end_date = getattr(Tournament, "end_date", None)

        if status == "upcoming":
            if start_at:
                qs = qs.filter(start_at__gt=now)
            elif start_date:
                qs = qs.filter(start_date__gt=now.date())
        elif status in ("live", "ongoing"):
            if start_at and end_at:
                qs = qs.filter(start_at__lte=now, end_at__gte=now)
            elif start_date and end_date:
                qs = qs.filter(start_date__lte=now.date(), end_date__gte=now.date())
        elif status in ("finished", "completed"):
            if end_at:
                qs = qs.filter(end_at__lt=now)
            elif end_date:
                qs = qs.filter(end_date__lt=now.date())

    if entry == "paid":
        qs = qs.filter(settings__entry_fee_bdt__gt=0)

    paginator = Paginator(qs.order_by("-id"), 12)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "tournaments/list.html",
        {"page": page, "tournaments": page.object_list, "q": q, "game": game, "status": status, "entry": entry},
    )


def tournament_detail(request, slug: str):
    """
    Public tournament detail (slug).
    """
    qs = _safe_select_related(Tournament.objects.all(), "settings", "bracket")
    try:
        qs = qs.prefetch_related("registrations", "matches")
    except Exception:
        pass
    t = get_object_or_404(qs, slug=slug)
    return render(request, "tournaments/detail.html", {"tournament": t, "t": t})


# -------------------------
# Registration (unified UI)
# -------------------------
def _entry_fee(t: Tournament) -> float:
    settings = getattr(t, "settings", None)
    return float(getattr(settings, "entry_fee_bdt", 0) or 0)


@require_http_methods(["GET", "POST"])
def register_view(request, slug):
    """
    Unified register endpoint.
    Selects game-specific forms when available, else falls back to generic.
    """
    t = get_object_or_404(Tournament, slug=slug)

    # Optional registration window guard
    now = timezone.now()
    if hasattr(t, "reg_open_at") and hasattr(t, "reg_close_at"):
        try:
            if not (t.reg_open_at <= now <= t.reg_close_at):
                return render(request, "tournaments/register_closed.html", {"t": t})
        except Exception:
            pass

    fee = _entry_fee(t)
    is_post = request.method == "POST"
    is_team_flow = "__team_flow" in request.POST
    game = (t.game or "").lower().strip()

    solo_form = team_form = None

    if game == "efootball" and (EfootballSoloForm and EfootballDuoForm):
        if is_post and is_team_flow:
            team_form = EfootballDuoForm(request.POST or None, request.FILES or None, tournament=t, request=request, entry_fee_bdt=fee)
            if team_form.is_valid():
                team_form.save()
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
        else:
            solo_form = EfootballSoloForm(request.POST or None, request.FILES or None, tournament=t, request=request, entry_fee_bdt=fee)
            if is_post and solo_form.is_valid():
                solo_form.save()
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)

        # Provide empty forms for GET / failed POST re-render
        solo_form = solo_form or EfootballSoloForm(None, None, tournament=t, request=request, entry_fee_bdt=fee)
        team_form = team_form or EfootballDuoForm(None, None, tournament=t, request=request, entry_fee_bdt=fee)

    elif game == "valorant" and ValorantTeamForm:
        team_form = ValorantTeamForm(request.POST or None, request.FILES or None, tournament=t, request=request, entry_fee_bdt=fee)
        if is_post and team_form.is_valid():
            team_form.save()
            messages.success(request, "Registration submitted.")
            return redirect("tournaments:register_success", slug=t.slug)

    else:
        # Fallback: generic forms
        if is_post and is_team_flow:
            team_form = GenericTeamForm(request.POST or None, request.FILES or None, tournament=t, request=request)
            if team_form.is_valid():
                team_form.save()
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
        else:
            solo_form = GenericSoloForm(request.POST or None, request.FILES or None, tournament=t, request=request)
            if is_post and solo_form.is_valid():
                solo_form.save()
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)

        solo_form = solo_form or GenericSoloForm(None, None, tournament=t, request=request)
        team_form = team_form or GenericTeamForm(None, None, tournament=t, request=request)

    return render(
        request,
        "tournaments/register.html",
        {"tournament": t, "t": t, "solo_form": solo_form, "team_form": team_form},
    )


def register_success(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/register_success.html", {"t": t, "tournament": t})
