from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.urls import reverse
from .models import Tournament, Registration, Match, TournamentSettings
from .forms import SoloRegistrationForm, TeamRegistrationForm
from apps.user_profile.models import UserProfile
from apps.teams.models import Team
from apps.corelib.brackets import report_result


def _get_profile(user):
    return getattr(user, "profile", None) or getattr(user, "userprofile", None)


@login_required
def register_view(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    p = _get_profile(request.user)
    if p is None:
        p, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"display_name": getattr(request.user, "username", "Player")},
        )

    # GET => show both forms
    if request.method != "POST":
        return render(
            request,
            "tournaments/register.html",
            {
                "t": t,
                "solo_form": SoloRegistrationForm(tournament=t, user_profile=p),
                "team_form": TeamRegistrationForm(tournament=t, user_profile=p),
            },
        )

    # ---------- TEAM REG ----------
    if "team" in request.POST:
        team_id = request.POST.get("team")
        pm = (request.POST.get("payment_method") or "").strip()
        pref = (request.POST.get("payment_reference") or "").strip()

        # must be the captain's team
        team_obj = Team.objects.filter(id=team_id, captain=p).first()

        # If paid tournament, require both fields; otherwise allow empty
        fee = (t.entry_fee_bdt or 0)
        missing_payment = (fee > 0) and (not pm or not pref)

        if team_obj and not missing_payment:
            # Create only if not already registered
            if not Registration.objects.filter(tournament=t, team=team_obj).exists():
                reg = Registration.objects.create(
                    tournament=t,
                    team=team_obj,
                    payment_method=pm,
                    payment_reference=pref,
                )
                # best-effort email (don’t crash tests if mail isn’t wired)
                try:
                    from apps.notifications.services import send_payment_instructions_for_registration
                    send_payment_instructions_for_registration(reg)
                except Exception:
                    pass
            return redirect("tournaments:register_success", slug=t.slug)

        # Show validation errors with the form if something is missing/wrong
        team_form = TeamRegistrationForm(request.POST, tournament=t, user_profile=p)
        solo_form = SoloRegistrationForm(tournament=t, user_profile=p)
        return render(request, "tournaments/register.html", {"t": t, "solo_form": solo_form, "team_form": team_form})

    # ---------- SOLO REG ----------
    solo_form = SoloRegistrationForm(request.POST, tournament=t, user_profile=p)
    team_form = TeamRegistrationForm(tournament=t, user_profile=p)
    if solo_form.is_valid():
        reg = solo_form.save()
        try:
            from apps.notifications.services import send_payment_instructions_for_registration
            send_payment_instructions_for_registration(reg)
        except Exception:
            pass
        return redirect("tournaments:register_success", slug=t.slug)
    return render(request, "tournaments/register.html", {"t": t, "solo_form": solo_form, "team_form": team_form})

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