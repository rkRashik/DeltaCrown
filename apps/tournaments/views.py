from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Max
from django.core.exceptions import ValidationError
from .models import Tournament, Registration, Match, TournamentSettings
from apps.corelib.brackets import report_result
from django.utils import timezone
from .forms import SoloRegistrationForm, TeamRegistrationForm
from apps.user_profile.models import UserProfile


@login_required
def register_view(request, slug):
    t = get_object_or_404(Tournament, slug=slug)

    # Ensure the user has a profile we can pass to forms/templates
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"display_name": request.user.get_username() or (request.user.email or "Player")}
    )

    # Decide solo/team. (Your tests treat Valorant as team-based.)
    is_team = bool(getattr(t, "valorant_config", None))

    # ---- Guard rails (do these before handling the form) ----
    now = timezone.now()
    if getattr(t, "reg_open_at", None) and now < t.reg_open_at:
        return render(request, "tournaments/register_error.html",
                      {"tournament": t, "error": "Registration has not opened yet."})
    if getattr(t, "reg_close_at", None) and now > t.reg_close_at:
        return render(request, "tournaments/register_error.html",
                      {"tournament": t, "error": "Registration is closed."})
    if t.slot_size and t.registrations.count() >= t.slot_size:
        return render(request, "tournaments/register_error.html",
                      {"tournament": t, "error": "This tournament is full."})

    # Normalize the form + template selection up-front so both GET/POST have them
    if is_team:
        FormClass = TeamRegistrationForm
        template = "tournaments/register_team.html"
    else:
        FormClass = SoloRegistrationForm
        template = "tournaments/register_solo.html"

    form_kwargs = {"tournament": t, "user_profile": profile}

    if request.method == "POST":
        form = FormClass(request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            # <-- tests expect a redirect here
            return redirect("tournaments:register_success", slug=t.slug)
        # invalid POST -> fall through and re-render with errors (status 200)
    else:
        form = FormClass(**form_kwargs)

    # Always pass profile so templates never try request.user.profile directly
    return render(request, template, {"tournament": t, "form": form, "profile": profile})


def register_success(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/register_success.html", {"tournament": t})


@login_required
def report_match_view(request, match_id):
    m = get_object_or_404(Match, id=match_id)
    if request.method == "POST":
        try:
            sa = int(request.POST.get("score_a", "0"))
            sb = int(request.POST.get("score_b", "0"))
            report_result(m, sa, sb, reporter=request.user.profile)
            return render(request, "tournaments/report_submitted.html", {"match": m})
        except (ValueError, ValidationError) as e:
            return render(request, "tournaments/report_form.html", {"match": m, "error": str(e)})
    return render(request, "tournaments/report_form.html", {"match": m})

def bracket_view(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    rounds = t.matches.aggregate(Max("round_no"))["round_no__max"] or 0
    rows = [t.matches.filter(round_no=r).order_by("position") for r in range(1, rounds + 1)]
    return render(request, "tournaments/bracket.html", {"t": t, "rounds": rows})

def tournament_detail(request, slug):
    # pull settings efficiently
    t = get_object_or_404(Tournament.objects.select_related("settings"), slug=slug)

    # safety for legacy rows that might lack settings
    if not hasattr(t, "settings"):
        TournamentSettings.objects.get_or_create(tournament=t)
        t = Tournament.objects.select_related("settings").get(pk=t.pk)

    return render(request, "tournaments/detail.html", {"t": t})

def tournament_list(request):
    qs = Tournament.objects.order_by("-start_at")
    return render(request, "tournaments/list.html", {"tournaments": qs})