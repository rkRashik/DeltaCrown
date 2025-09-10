# apps/tournaments/views/public.py
from __future__ import annotations

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..models import Tournament, TournamentSettings
from django.core.exceptions import ObjectDoesNotExist
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
    game = (request.GET.get("game") or "").strip().lower()
    status = (request.GET.get("status") or "").strip().lower()
    entry = (request.GET.get("entry") or "").strip().lower()
    sort = (request.GET.get("sort") or "").strip().lower()

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))
    if game:
        qs = qs.filter(game__iexact=game)

    now = timezone.now()
    # Support common UI statuses: open | ongoing | finished (and tolerate older: upcoming/live/completed)
    if status:
        if status in ("open",):
            qs = qs.filter(
                Q(settings__reg_open_at__lte=now, settings__reg_close_at__gte=now)
            )
        elif status in ("ongoing", "live"):
            qs = qs.filter(
                Q(settings__start_at__lte=now, settings__end_at__gte=now)
            )
        elif status in ("finished", "completed"):
            qs = qs.filter(Q(settings__end_at__lt=now))
        elif status in ("upcoming",):
            qs = qs.filter(Q(settings__start_at__gt=now))

    if entry == "paid":
        qs = qs.filter(settings__entry_fee_bdt__gt=0)

    # Sorting
    if sort == "start":
        qs = qs.order_by("settings__start_at", "id")
    elif sort == "prize":
        # Desc by prize pool
        if hasattr(Tournament, "prize_pool_bdt"):
            qs = qs.order_by("-prize_pool_bdt", "-id")
        else:
            qs = qs.order_by("-id")
    elif sort == "entry":
        if hasattr(Tournament, "entry_fee_bdt"):
            qs = qs.order_by("entry_fee_bdt", "id")
        else:
            qs = qs.order_by("id")
    else:
        qs = qs.order_by("-id")

    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get("page"))

    # Games list for filter select (slug + name)
    games = [{"slug": key, "name": label} for key, label in getattr(Tournament.Game, "choices", [])]

    context = {
        "page": page,
        "tournaments": page.object_list,
        "q": q,
        "game": game,
        "status": status,
        "entry": entry,
        "sort": sort,
        "games": games,
    }

    # Partial rendering for AJAX grid updates
    if (request.GET.get("partial") or "").strip().lower() == "grid":
        return render(request, "tournaments/partials/_grid.html", context)

    return render(request, "tournaments/list.html", context)


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

    # Ensure settings exists (or create a blank one) so template access is safe
    try:
        _ = t.settings  # may raise if missing
    except ObjectDoesNotExist:
        try:
            TournamentSettings.objects.get_or_create(tournament=t)
        except Exception:
            pass
    except Exception:
        pass

    return render(request, "tournaments/detail.html", {"tournament": t})


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
    t = get_object_or_404(Tournament.objects.select_related("settings"), slug=slug)

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

    # Sidebar/context wiring (no schema change)
    # User teams (captain or active member)
    user_teams = []
    try:
        Profile = apps.get_model("user_profile", "UserProfile")
        Team = apps.get_model("teams", "Team")
        TeamMembership = apps.get_model("teams", "TeamMembership")
        prof = getattr(request.user, "profile", None)
        if not prof and Profile and request.user.is_authenticated:
            prof = Profile.objects.filter(user=request.user).first()
        if prof and Team:
            qs = Team.objects.filter(models.Q(captain=prof) | models.Q(memberships__profile=prof, memberships__status="ACTIVE")).distinct()
            user_teams = list(qs.values("id", "name", "slug"))
    except Exception:
        user_teams = []

    # Entry fee + payment channels
    entry_fee_bdt = None
    try:
        if getattr(t, "settings", None) and getattr(t.settings, "entry_fee_bdt", None):
            entry_fee_bdt = int(t.settings.entry_fee_bdt or 0)
        elif getattr(t, "entry_fee_bdt", None):
            entry_fee_bdt = int(t.entry_fee_bdt or 0)
    except Exception:
        entry_fee_bdt = None

    payment_channels = {
        "bkash": getattr(getattr(t, "settings", None), "bkash_receive_number", ""),
        "nagad": getattr(getattr(t, "settings", None), "nagad_receive_number", ""),
    }

    prefill = {}
    try:
        prof = getattr(request.user, "profile", None)
        if prof:
            prefill = {"display_name": getattr(prof, "display_name", ""), "phone": getattr(prof, "phone", "")}
    except Exception:
        prefill = {}

    return render(
        request,
        "tournaments/register.html",
        {
            "tournament": t,
            "t": t,
            "solo_form": solo_form,
            "team_form": team_form,
            "user_teams": user_teams,
            "entry_fee_bdt": entry_fee_bdt,
            "payment_channels": payment_channels,
            "prefill": prefill,
        },
    )


def register_success(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/register_success.html", {"t": t, "tournament": t})


def watch(request, slug):
    t = get_object_or_404(Tournament.objects.select_related("settings"), slug=slug)
    return render(request, "tournaments/watch.html", {"tournament": t, "t": t})


def registration_receipt(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    reg = None
    try:
        Profile = apps.get_model("user_profile", "UserProfile")
        prof = getattr(request.user, "profile", None)
        if not prof and Profile and request.user.is_authenticated:
            prof = Profile.objects.filter(user=request.user).first()
        if prof:
            Registration = apps.get_model("tournaments", "Registration")
            reg = Registration.objects.filter(tournament=t).filter(models.Q(user=prof) | models.Q(team__captain=prof)).order_by("-created_at").first()
    except Exception:
        reg = None
    return render(request, "tournaments/registration_receipt.html", {"tournament": t, "reg": reg})
