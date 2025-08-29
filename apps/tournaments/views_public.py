# apps/tournaments/views_public.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Tournament, Registration
from .forms import SoloRegistrationForm, TeamRegistrationForm
from apps.user_profile.models import UserProfile
from django.utils import timezone
from apps.notifications.services import send_payment_instructions_email


def tournament_list(request):
    qs = Tournament.objects.all().order_by("-created_at")
    return render(request, "tournaments/list.html", {"tournaments": qs})


def tournament_detail(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
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