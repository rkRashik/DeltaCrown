from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Tournament, Registration
from .forms import SoloRegistrationForm, TeamRegistrationForm

@login_required
def register_view(request, slug):
    t = get_object_or_404(Tournament, slug=slug)

    # Business rule: optional registration window guard (MVP)
    now = timezone.now()
    if getattr(t, "reg_open_at", None) and now < t.reg_open_at:
        return render(request, "tournaments/register_error.html",
                      {"tournament": t, "error": "Registration has not opened yet."})
    if getattr(t, "reg_close_at", None) and now > t.reg_close_at:
        return render(request, "tournaments/register_error.html",
                      {"tournament": t, "error": "Registration is closed."})

    # Capacity guard (MVP): block new entries if full
    if t.slot_size and t.registrations.count() >= t.slot_size:
        return render(request, "tournaments/register_error.html",
                      {"tournament": t, "error": "This tournament is full."})

    # Decide which game is attached
    is_efootball = hasattr(t, "efootball_config")
    is_valorant = hasattr(t, "valorant_config")

    if is_efootball and is_valorant:
        # Hard guard: you enforce one config in Part 4; just in case
        return render(request, "tournaments/register_error.html",
                      {"tournament": t, "error": "Multiple game configs found. Contact admin."})

    if not (is_efootball or is_valorant):
        return render(request, "tournaments/register_error.html",
                      {"tournament": t, "error": "No game configuration attached yet."})

    if is_efootball:
        FormClass = SoloRegistrationForm
        form_kwargs = {"tournament": t, "user_profile": request.user.profile}
        template = "tournaments/register_solo.html"
    else:
        FormClass = TeamRegistrationForm
        form_kwargs = {"tournament": t, "user_profile": request.user.profile}
        template = "tournaments/register_team.html"

    if request.method == "POST":
        form = FormClass(request.POST, **form_kwargs)
        if form.is_valid():
            reg = form.save()
            # Optional: notify / email (we’ll wire in Part 7)
            return redirect("tournaments:register_success", slug=t.slug)
    else:
        form = FormClass(**form_kwargs)

    return render(request, template, {"tournament": t, "form": form})


def register_success(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/register_success.html", {"tournament": t})
