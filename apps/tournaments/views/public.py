# apps/tournaments/views/public.py
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..models import Tournament
from apps.corelib.admin_utils import _safe_select_related

# Generic fallback forms
from ..forms_registration import SoloRegistrationForm as GenericSoloForm, TeamRegistrationForm as GenericTeamForm

# Game-specific forms (import guarded)
try:
    from apps.game_efootball.forms import EfootballSoloForm, EfootballDuoForm  # type: ignore
except Exception:  # pragma: no cover
    EfootballSoloForm = None
    EfootballDuoForm = None

try:
    from apps.game_valorant.forms import ValorantTeamForm  # type: ignore
except Exception:  # pragma: no cover
    ValorantTeamForm = None


def tournament_list(request):
    qs = Tournament.objects.all()
    qs = _safe_select_related(qs, "settings")
    q = request.GET.get("q") or ""
    game = request.GET.get("game") or ""
    status = request.GET.get("status") or ""
    entry = request.GET.get("entry") or ""

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))
    if game:
        qs = qs.filter(game__iexact=game)

    now = timezone.now()
    if status == "upcoming":
        qs = qs.filter(start_at__gt=now)
    elif status == "ongoing":
        qs = qs.filter(start_at__lte=now, end_at__gte=now)
    elif status == "completed":
        qs = qs.filter(end_at__lt=now)

    if entry == "paid":
        qs = qs.filter(settings__entry_fee_bdt__gt=0)

    paginator = Paginator(qs.order_by("-start_at"), 12)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "tournaments/list.html", {"page": page, "q": q, "game": game, "status": status, "entry": entry})


def tournament_detail(request, slug):
    qs = _safe_select_related(Tournament.objects.all(), "settings", "bracket")
    try:
        qs = qs.prefetch_related("registrations", "matches")
    except Exception:
        pass
    t = get_object_or_404(qs, slug=slug)
    return render(request, "tournaments/detail.html", {"t": t, "tournament": t})


def _entry_fee(t: Tournament) -> float:
    settings = getattr(t, "settings", None)
    return float(getattr(settings, "entry_fee_bdt", 0) or 0)


def register_view(request, slug):
    """
    Unified register endpoint.
    Selects game-specific forms when available, else falls back to generic.
    """
    t = get_object_or_404(Tournament, slug=slug)

    # Registration window
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

    # Choose forms by game
    solo_form = team_form = None

    if game == "efootball" and (EfootballSoloForm and EfootballDuoForm):
        # Solo vs Duo by hidden flag
        if is_post and is_team_flow:
            form_cls = EfootballDuoForm
            team_form = form_cls(request.POST or None, request.FILES or None, tournament=t, request=request, entry_fee_bdt=fee)
            if team_form.is_valid():
                reg = team_form.save()
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
        else:
            form_cls = EfootballSoloForm
            solo_form = form_cls(request.POST or None, request.FILES or None, tournament=t, request=request, entry_fee_bdt=fee)
            if is_post and solo_form.is_valid():
                reg = solo_form.save()
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)

        # Provide both for the template
        solo_form = solo_form or EfootballSoloForm(None, None, tournament=t, request=request, entry_fee_bdt=fee)
        team_form = team_form or EfootballDuoForm(None, None, tournament=t, request=request, entry_fee_bdt=fee)

    elif game == "valorant" and ValorantTeamForm:
        team_form = ValorantTeamForm(request.POST or None, request.FILES or None, tournament=t, request=request, entry_fee_bdt=fee)
        if is_post and team_form.is_valid():
            reg = team_form.save()
            messages.success(request, "Registration submitted.")
            return redirect("tournaments:register_success", slug=t.slug)
    else:
        # Fallback to generics
        if is_post and is_team_flow:
            team_form = GenericTeamForm(request.POST or None, request.FILES or None, tournament=t, request=request)
            if team_form.is_valid():
                reg = team_form.save()
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
        else:
            solo_form = GenericSoloForm(request.POST or None, request.FILES or None, tournament=t, request=request)
            if is_post and solo_form.is_valid():
                reg = solo_form.save()
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)

        solo_form = solo_form or GenericSoloForm(None, None, tournament=t, request=request)
        team_form = team_form or GenericTeamForm(None, None, tournament=t, request=request)

    return render(request, "tournaments/register.html", {"t": t, "tournament": t, "solo_form": solo_form, "team_form": team_form})


def register_success(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/register_success.html", {"t": t, "tournament": t})


@login_required
def my_matches_view(request):
    return render(request, "tournaments/my_matches.html", {})
