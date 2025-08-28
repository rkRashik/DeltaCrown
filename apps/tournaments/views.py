from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Max
from django.core.exceptions import ValidationError
from .models import Tournament, Registration, Match
from apps.corelib.brackets import report_result
from django.utils import timezone
from .forms import SoloRegistrationForm, TeamRegistrationForm
from apps.user_profile.models import UserProfile


@login_required
def register_view(request, slug):
    t = get_object_or_404(Tournament, slug=slug)

    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"display_name": request.user.get_username() or (request.user.email or "Player")}
    )

    # pick solo/team by your tournament logic (solo if no teams; team if Valorant/team-game)
    is_team = bool(getattr(t, "valorant_config", None))  # example heuristic

    if request.method == "POST":
        if is_team:
            form = TeamRegistrationForm(request.POST, tournament=t, user_profile=profile)
        else:
            form = SoloRegistrationForm(request.POST, tournament=t, user_profile=profile)
        if form.is_valid():
            form.save()
            return render(request, "tournaments/register_success.html", {"tournament": t})
    else:
        if is_team:
            form = TeamRegistrationForm(tournament=t, user_profile=profile)
            template = "tournaments/register_team.html"
        else:
            form = SoloRegistrationForm(tournament=t, user_profile=profile)
            template = "tournaments/register_solo.html"

    # 👇 pass 'profile' so the template never reaches for request.user.profile
    return render(request, template, {"tournament": t, "form": form, "profile": profile})

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
    t = get_object_or_404(Tournament, slug=slug)
    return render(request, "tournaments/detail.html", {"t": t})

def tournament_list(request):
    qs = Tournament.objects.order_by("-start_at")
    return render(request, "tournaments/list.html", {"tournaments": qs})