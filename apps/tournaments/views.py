from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.urls import reverse
from .models import Tournament, Registration, Match, TournamentSettings
from .forms import SoloRegistrationForm, TeamRegistrationForm
from django.apps import apps
from apps.teams.models import Team
from apps.corelib.brackets import report_result
from django.contrib.admin.views.decorators import staff_member_required

def _get_profile(user):
    # Works whether the OneToOne is named "profile" or "userprofile"
    return getattr(user, "profile", None) or getattr(user, "userprofile", None)

def _ensure_profile(user):
    p = _get_profile(user)
    if p:
        return p
    # Avoid direct import to prevent circular deps
    UserProfile = apps.get_model("user_profile", "UserProfile")
    p, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"display_name": getattr(user, "username", "Player")},
    )
    return p

@login_required
def register_view(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    p = _ensure_profile(request.user)

    is_efootball = hasattr(t, "efootball_config")
    is_valorant = hasattr(t, "valorant_config")

    if is_efootball and is_valorant:
        return render(
            request,
            "tournaments/register_error.html",
            {"tournament": t, "error": "Multiple game configs found. Contact admin."},
        )

    if not (is_efootball or is_valorant):
        return render(
            request,
            "tournaments/register_error.html",
            {"tournament": t, "error": "No game configuration attached yet."},
        )

    if is_efootball:
        FormClass = SoloRegistrationForm
        template = "tournaments/register_solo.html"
    else:
        FormClass = TeamRegistrationForm
        template = "tournaments/register_team.html"

    if request.method == "POST":
        form = FormClass(request.POST, tournament=t, user_profile=p)
        if form.is_valid():
            form.save()
            return redirect("tournaments:register_success", slug=t.slug)
    else:
        form = FormClass(tournament=t, user_profile=p)

    return render(request, template, {"tournament": t, "form": form})

@login_required
def report_match_view(request, match_id):
    match = get_object_or_404(Match, id=match_id)

    if request.method == "POST":
        try:
            # Retrieve scores from the form
            score_a = int(request.POST.get("score_a", "0"))
            score_b = int(request.POST.get("score_b", "0"))

            # Call the helper function to report the result
            report_result(match, score_a, score_b, reporter=request.user.profile)

            # Render success page
            return render(request, "tournaments/report_submitted.html", {"match": match})

        except (ValueError, ValidationError) as e:
            # In case of validation errors, re-render the form with an error message
            return render(request, "tournaments/report_form.html", {"match": match, "error": str(e)})

    return render(request, "tournaments/report_form.html", {"match": match})

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

@staff_member_required
def resolve_dispute(request, match_id):
    match = get_object_or_404(Match, id=match_id)

    if match.state == "DISPUTED":
        # Allow admin to mark the match as VERIFIED and resolve the dispute
        if request.method == "POST":
            match.state = "VERIFIED"
            match.save()
            # You can also send an email notification to participants here.
            return redirect("admin:index")

    return render(request, "admin/resolve_dispute.html", {"match": match})
