# apps/tournaments/views/public.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from ..models import Tournament, Registration
from ..forms_registration import SoloRegistrationForm, TeamRegistrationForm
from apps.user_profile.models import UserProfile
from django.utils import timezone
from apps.notifications.services import send_payment_instructions_email
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import FieldDoesNotExist
from apps.corelib.admin_utils import _safe_select_related


def tournament_list(request):
    qs = Tournament.objects.all()
    # Performance: avoid N+1 on one-to-one settings; keep list payload light
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
        # case-insensitive match, works even if DB has 'eFootball' or 'Valorant'
        qs = qs.filter(game__iexact=game)

    # status via dates (robust across Status choices)
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

    # Sorting
    if sort == "date":
        qs = qs.order_by("start_at")            # earliest first
    elif sort == "name":
        qs = qs.order_by("name")
    elif sort == "popular":
        qs = qs.order_by("-created_at")         # placeholder until you track views/regs
    else:  # "new" (default)
        qs = qs.order_by("-created_at")

    # Pagination
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
    qs = _safe_select_related(Tournament.objects.all(), "settings", "bracket")
    try:
        # Prefetch heavy relations if they exist; ignore if names differ
        qs = qs.prefetch_related("registrations", "matches")
    except Exception:
        pass
    t = get_object_or_404(qs, slug=slug)

    return render(request, "tournaments/detail.html", {"t": t})


@login_required
def register_view(request, slug):
    t = get_object_or_404(Tournament, slug=slug)

    # Respect registration window
    now = timezone.now()
    if not (t.reg_open_at <= now <= t.reg_close_at):
        return render(request, "tournaments/register_closed.html", {"t": t})

    # Get profile (support both attribute names)
    profile = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
    if not profile:
        messages.error(request, "Please complete your profile first.")
        return redirect("user_profile:edit")

    # Always prepare both forms for the template
    solo_form = SoloRegistrationForm(tournament=t, user_profile=profile)
    team_form = TeamRegistrationForm(tournament=t, user_profile=profile)

    if request.method == "POST":
        fee = float(t.entry_fee_bdt or 0)

        if "team" in request.POST:
            # Team registration (paid or free) -> validate via form
            team_form = TeamRegistrationForm(request.POST, tournament=t, user_profile=profile)
            if team_form.is_valid():
                reg = team_form.save()
                try:
                    from apps.notifications.services import send_payment_instructions_for_registration
                    send_payment_instructions_for_registration(reg)
                except Exception:
                    pass
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
        else:
            # Solo registration
            if fee <= 0:
                # Free solo path: allow empty POST and create a row directly
                reg = Registration.objects.create(tournament=t, user=profile)
                try:
                    from apps.notifications.services import send_payment_instructions_for_registration
                    send_payment_instructions_for_registration(reg)
                except Exception:
                    pass
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
            else:
                # Paid solo -> validate via form (requires method/ref, and sender for wallets)
                solo_form = SoloRegistrationForm(request.POST, tournament=t, user_profile=profile)
                if solo_form.is_valid():
                    reg = solo_form.save()
                    try:
                        from apps.notifications.services import send_payment_instructions_for_registration
                        send_payment_instructions_for_registration(reg)
                    except Exception:
                        pass
                    messages.success(request, "Registration submitted.")
                    return redirect("tournaments:register_success", slug=t.slug)

    return render(
        request,
        "tournaments/register.html",
        {"t": t, "solo_form": solo_form, "team_form": team_form},
    )@login_required
def register_view(request, slug):
    t = get_object_or_404(Tournament, slug=slug)

    # Respect registration window
    now = timezone.now()
    if not (t.reg_open_at <= now <= t.reg_close_at):
        return render(request, "tournaments/register_closed.html", {"t": t})

    # Get profile (support both attribute names)
    profile = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
    if not profile:
        messages.error(request, "Please complete your profile first.")
        return redirect("user_profile:edit")

    # Always prepare both forms for the template
    solo_form = SoloRegistrationForm(tournament=t, user_profile=profile)
    team_form = TeamRegistrationForm(tournament=t, user_profile=profile)

    if request.method == "POST":
        fee = float(t.entry_fee_bdt or 0)

        if "team" in request.POST:
            # Team registration (paid or free) -> validate via form
            team_form = TeamRegistrationForm(request.POST, tournament=t, user_profile=profile)
            if team_form.is_valid():
                reg = team_form.save()
                try:
                    from apps.notifications.services import send_payment_instructions_for_registration
                    send_payment_instructions_for_registration(reg)
                except Exception:
                    pass
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
        else:
            # Solo registration
            if fee <= 0:
                # Free solo path: allow empty POST and create a row directly
                reg = Registration.objects.create(tournament=t, user=profile)
                try:
                    from apps.notifications.services import send_payment_instructions_for_registration
                    send_payment_instructions_for_registration(reg)
                except Exception:
                    pass
                messages.success(request, "Registration submitted.")
                return redirect("tournaments:register_success", slug=t.slug)
            else:
                # Paid solo -> validate via form (requires method/ref, and sender for wallets)
                solo_form = SoloRegistrationForm(request.POST, tournament=t, user_profile=profile)
                if solo_form.is_valid():
                    reg = solo_form.save()
                    try:
                        from apps.notifications.services import send_payment_instructions_for_registration
                        send_payment_instructions_for_registration(reg)
                    except Exception:
                        pass
                    messages.success(request, "Registration submitted.")
                    return redirect("tournaments:register_success", slug=t.slug)

    return render(
        request,
        "tournaments/register.html",
        {"t": t, "solo_form": solo_form, "team_form": team_form},
    )


@login_required
def register_success(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/register_success.html", {"t": t})

@login_required
def my_matches_view(request):
    """
    Show matches for the logged-in user:
    - Solo: user_a or user_b
    - Team: matches where the user's team captaincy applies (team_a.captain or team_b.captain)
    """
    from ..models import Match
    p = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
    if p is None:
        # No profile yet — nothing to show
        qs = Match.objects.none()
    else:
        qs = (
            Match.objects
            .select_related("tournament", "user_a__user", "user_b__user", "team_a", "team_b")
            .filter(Q(user_a=p) | Q(user_b=p) | Q(team_a__captain=p) | Q(team_b__captain=p))
            .order_by("-id")
        )
    return render(request, "tournaments/my_matches.html", {"matches": qs})
