# apps/tournaments/views/public.py
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from ..forms_registration import SoloRegistrationForm, TeamRegistrationForm
from ..models import Registration, Tournament
from apps.corelib.admin_utils import _safe_select_related

# Optional notifications service (best-effort import)
try:
    from apps.notifications.subscribers import send_payment_instructions_for_registration  # type: ignore
except Exception:  # pragma: no cover
    send_payment_instructions_for_registration = None


def tournament_list(request):
    """
    Public list with basic filters/sort/pagination.
    """
    qs = Tournament.objects.all()
    qs = _safe_select_related(qs, "settings")

    # Defer potentially heavy fields only if present
    try:
        Tournament._meta.get_field("bank_instructions")
    except FieldDoesNotExist:
        pass
    else:
        qs = qs.defer("bank_instructions")

    # Filters
    q = (request.GET.get("q") or "").strip()
    game = (request.GET.get("game") or "").strip()
    status = (request.GET.get("status") or "").strip()
    entry = (request.GET.get("entry") or "").strip()
    sort = (request.GET.get("sort") or "new").strip()

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

    if entry == "free":
        if hasattr(Tournament, "entry_fee_bdt"):
            qs = qs.filter(entry_fee_bdt__isnull=True) | qs.filter(entry_fee_bdt=0)

    if sort == "name":
        qs = qs.order_by("name")
    elif sort == "popular":
        qs = qs.order_by("-created_at")
    else:
        qs = qs.order_by("-created_at")

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    ctx = {
        "tournaments": page_obj.object_list,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "q": q, "f_game": game, "f_status": status, "f_entry": entry, "f_sort": sort,
    }
    return render(request, "tournaments/list.html", ctx)


def tournament_detail(request, slug):
    """
    Public detail page. Prefetch what we can safely.
    """
    qs = _safe_select_related(Tournament.objects.all(), "settings", "bracket")
    try:
        qs = qs.prefetch_related("registrations", "matches")
    except Exception:
        pass
    t = get_object_or_404(qs, slug=slug)
    # Provide both keys for template compatibility
    return render(request, "tournaments/detail.html", {"t": t, "tournament": t})


def register_view(request, slug):
    """
    Unified register endpoint (GET open; POST requires auth).
    - Team (Valorant) -> POST contains 'team' => TeamRegistrationForm
    - Solo (eFootball) -> otherwise => SoloRegistrationForm
    Payment is recorded as pending; admins verify manually later.
    """
    t = get_object_or_404(Tournament, slug=slug)

    # Respect registration window if present
    now = timezone.now()
    if hasattr(t, "reg_open_at") and hasattr(t, "reg_close_at"):
        try:
            if not (t.reg_open_at <= now <= t.reg_close_at):
                return render(request, "tournaments/register_closed.html", {"t": t})
        except Exception:
            # If window fields exist but are None/invalid, ignore and proceed
            pass

    solo_form = SoloRegistrationForm(tournament=t, request=request)
    team_form = TeamRegistrationForm(tournament=t, request=request)

    if request.method == "POST":
        if not request.user.is_authenticated:
            # Avoid reversing a missing 'login' route; fall back to 403
            try:
                return redirect(reverse("login"))
            except NoReverseMatch:
                messages.error(request, "You must be logged in to register.")
                return HttpResponseForbidden("Login required")

        # Decide flow by presence of 'team' field
        if "team" in request.POST:
            team_form = TeamRegistrationForm(request.POST, request.FILES, tournament=t, request=request)
            if team_form.is_valid():
                reg = team_form.save()
                if send_payment_instructions_for_registration:
                    try:
                        send_payment_instructions_for_registration(reg)  # best-effort
                    except Exception:
                        pass
                messages.success(request, "Team registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
        else:
            solo_form = SoloRegistrationForm(request.POST, request.FILES, tournament=t, request=request)
            if solo_form.is_valid():
                reg = solo_form.save()
                if send_payment_instructions_for_registration:
                    try:
                        send_payment_instructions_for_registration(reg)  # best-effort
                    except Exception:
                        pass
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)

    return render(
        request,
        "tournaments/register.html",
        {"t": t, "tournament": t, "solo_form": solo_form, "team_form": team_form},
    )


def register_success(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/register_success.html", {"t": t, "tournament": t})


@login_required
def my_matches_view(request):
    """
    Example placeholder; requires auth.
    """
    # You can flesh this out later; here we just render a template if present.
    return render(request, "tournaments/my_matches.html", {})
