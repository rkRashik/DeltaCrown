# apps/tournaments/views/public.py
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..forms_registration import SoloRegistrationForm, TeamRegistrationForm
from ..models import Registration, Tournament
from apps.corelib.admin_utils import _safe_select_related

# Optional notifications service
try:
    from apps.notifications.services import send_payment_instructions_for_registration
except Exception:
    send_payment_instructions_for_registration = None


def tournament_list(request):
    """
    Public list: search, filter (game/status/entry), sort, paginate.
    Keeps payload light by select_related on 1-1s and deferring heavy fields when present.
    """
    qs = Tournament.objects.all()
    qs = _safe_select_related(qs, "settings")

    # Defer heavy field only if it exists on Tournament
    try:
        Tournament._meta.get_field("bank_instructions")
    except FieldDoesNotExist:
        pass
    else:
        qs = qs.defer("bank_instructions")

    # --- Filters & search ---
    q = (request.GET.get("q") or "").strip()
    game = (request.GET.get("game") or "").strip().lower()           # valorant|efootball
    status = (request.GET.get("status") or "").strip().lower()       # upcoming|ongoing|completed
    entry = (request.GET.get("entry") or "").strip().lower()         # free|paid
    sort = (request.GET.get("sort") or "new").strip().lower()        # new|date|name|popular

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(short_description__icontains=q))

    if game:
        qs = qs.filter(game__iexact=game)

    # Status via dates
    now = timezone.now()
    if status == "upcoming":
        qs = qs.filter(start_at__gt=now)
    elif status == "ongoing":
        qs = qs.filter(start_at__lte=now, end_at__gte=now)
    elif status == "completed":
        qs = qs.filter(end_at__lt=now)

    if entry == "free":
        qs = qs.filter(Q(entry_fee_bdt__isnull=True) | Q(entry_fee_bdt=0))
    elif entry == "paid":
        qs = qs.filter(entry_fee_bdt__gt=0)

    if sort == "date":
        qs = qs.order_by("start_at")            # earliest first
    elif sort == "name":
        qs = qs.order_by("name")
    elif sort == "popular":
        qs = qs.order_by("-created_at")         # placeholder until you track views/regs
    else:  # "new" (default)
        qs = qs.order_by("-created_at")

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    ctx = {
        "tournaments": page_obj.object_list,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        # echo current filters back to template
        "q": q, "f_game": game, "f_status": status, "f_entry": entry, "f_sort": sort,
    }
    return render(request, "tournaments/list.html", ctx)


def tournament_detail(request, slug):
    """
    Public detail page. Prefetch related collections when available.
    """
    qs = _safe_select_related(Tournament.objects.all(), "settings", "bracket")
    try:
        qs = qs.prefetch_related("registrations", "matches")
    except Exception:
        pass
    t = get_object_or_404(qs, slug=slug)
    return render(request, "tournaments/detail.html", {"t": t})


@login_required
def register_view(request, slug):
    """
    Unified register endpoint.
    - Team (Valorant) -> POST contains 'team' => TeamRegistrationForm
    - Solo (eFootball) -> otherwise => SoloRegistrationForm
    Payment is recorded as pending; admins verify manually later.
    """
    t = get_object_or_404(Tournament, slug=slug)

    # Registration window (if fields exist)
    now = timezone.now()
    if hasattr(t, "reg_open_at") and hasattr(t, "reg_close_at"):
        if not (t.reg_open_at <= now <= t.reg_close_at):
            return render(request, "tournaments/register_closed.html", {"t": t})

    # Prepare forms for GET
    solo_form = SoloRegistrationForm(tournament=t, request=request)
    team_form = TeamRegistrationForm(tournament=t, request=request)

    if request.method == "POST":
        fee = float(getattr(t, "entry_fee_bdt", 0) or 0)

        if "team" in request.POST:
            # Team registration (paid or free)
            team_form = TeamRegistrationForm(request.POST, request.FILES, tournament=t, request=request)
            if team_form.is_valid():
                reg = team_form.save()
                if send_payment_instructions_for_registration:
                    try:
                        send_payment_instructions_for_registration(reg)
                    except Exception:
                        pass
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
        else:
            # Solo registration
            if fee <= 0:
                # Free solo path: minimal row
                reg_kwargs = {"tournament": t}
                # Prefer Registration.user if available; else user_profile
                if hasattr(Registration, "user"):
                    reg_kwargs["user"] = request.user
                elif hasattr(Registration, "user_profile"):
                    # try common profile attributes on request.user
                    prof = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
                    if prof:
                        reg_kwargs["user_profile"] = prof
                reg = Registration.objects.create(**reg_kwargs)
                if send_payment_instructions_for_registration:
                    try:
                        send_payment_instructions_for_registration(reg)
                    except Exception:
                        pass
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
            else:
                # Paid solo -> validate via form
                solo_form = SoloRegistrationForm(request.POST, request.FILES, tournament=t, request=request)
                if solo_form.is_valid():
                    reg = solo_form.save()
                    if send_payment_instructions_for_registration:
                        try:
                            send_payment_instructions_for_registration(reg)
                        except Exception:
                            pass
                    messages.success(request, "Registration submitted.")
                    return redirect("tournaments:register_success", slug=t.slug)

    return render(request, "tournaments/register.html", {"t": t, "solo_form": solo_form, "team_form": team_form})


@login_required
def register_success(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/register_success.html", {"t": t})


@login_required
def my_matches_view(request):
    """
    Matches for logged-in user:
    - Solo: user_a or user_b
    - Team: captain of team_a or team_b
    """
    from ..models import Match
    # Be tolerant with profile attribute name
    p = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
    if p is None:
        qs = Match.objects.none()
    else:
        qs = (
            Match.objects
            .select_related("tournament", "user_a__user", "user_b__user", "team_a", "team_b")
            .filter(Q(user_a=p) | Q(user_b=p) | Q(team_a__captain=p) | Q(team_b__captain=p))
            .order_by("-id")
        )
    return render(request, "tournaments/my_matches.html", {"matches": qs})
