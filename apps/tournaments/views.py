from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from django.apps import apps

from .models import Tournament, Registration, Match, TournamentSettings
from .forms import SoloRegistrationForm, TeamRegistrationForm
from apps.corelib.brackets import report_result, verify_and_apply


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_profile(user):
    """Works whether the OneToOne is named 'profile' or 'userprofile'."""
    return getattr(user, "profile", None) or getattr(user, "userprofile", None)


def _ensure_profile(user):
    p = _get_profile(user)
    if p:
        return p
    # avoid circular import
    UserProfile = apps.get_model("user_profile", "UserProfile")
    p, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"display_name": getattr(user, "username", "Player")},
    )
    return p


def _actor_is_participant(m: Match, actor):
    """Solo: either player. Team: only captains."""
    if getattr(m, "is_solo_match", False):
        return actor in [m.user_a, m.user_b]
    # Team: captains only
    caps = []
    if m.team_a_id and getattr(m.team_a, "captain", None):
        caps.append(m.team_a.captain)
    if m.team_b_id and getattr(m.team_b, "captain", None):
        caps.append(m.team_b.captain)
    return actor in caps


def _create_event(kind: str, match: Match, actor=None, **data):
    """
    Write a timeline event if MatchEvent model exists.
    Safe no-op if model not present (pre-migration).
    """
    try:
        MatchEvent = apps.get_model("tournaments", "MatchEvent")
    except Exception:
        MatchEvent = None
    if MatchEvent is None:
        return
    try:
        MatchEvent.objects.create(match=match, actor=actor, kind=kind, data=data or {})
    except Exception:
        # Don't block the main action because of the timeline
        pass


# ---------------------------------------------------------------------------
# Registration / Public pages
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Match reporting + review / confirm / dispute
# ---------------------------------------------------------------------------

@login_required
def report_match_view(request, match_id):
    m = get_object_or_404(Match, id=match_id)

    if request.method == "POST":
        try:
            score_a = int(request.POST.get("score_a", "0"))
            score_b = int(request.POST.get("score_b", "0"))

            report_result(m, score_a, score_b, reporter=_ensure_profile(request.user))

            # timeline event (safe if model exists)
            _create_event("REPORT", m, actor=_get_profile(request.user),
                          score_a=score_a, score_b=score_b)

            # go to review page
            return redirect("tournaments:match_review", match_id=m.id)

        except (ValueError, ValidationError) as e:
            return render(request, "tournaments/report_form.html", {"match": m, "error": str(e)})

    return render(request, "tournaments/report_form.html", {"match": m})


@login_required
def match_review_view(request, match_id):
    m = get_object_or_404(Match.objects.select_related("tournament"), id=match_id)

    # load timeline & dispute if those models exist
    events = []
    dispute = None
    try:
        MatchEvent = apps.get_model("tournaments", "MatchEvent")
        events = list(MatchEvent.objects.filter(match=m).order_by("created_at"))
    except Exception:
        pass
    try:
        MatchDispute = apps.get_model("tournaments", "MatchDispute")
        dispute = MatchDispute.objects.filter(match=m).first()
    except Exception:
        pass

    return render(request, "tournaments/match_review.html", {"match": m, "events": events, "dispute": dispute})


@login_required
@require_POST
def match_confirm_view(request, match_id):
    m = get_object_or_404(Match, id=match_id)
    actor = _ensure_profile(request.user)
    if not _actor_is_participant(m, actor):
        return render(request, "tournaments/match_review.html", {"match": m, "error": "Not authorized."}, status=403)

    # verify result and propagate bracket
    verify_and_apply(m)

    # timeline
    _create_event("CONFIRM", m, actor=actor)

    return redirect("tournaments:match_review", match_id=m.id)


@login_required
def match_dispute_view(request, match_id):
    m = get_object_or_404(Match, id=match_id)
    actor = _ensure_profile(request.user)
    if not _actor_is_participant(m, actor):
        return render(request, "tournaments/match_review.html", {"match": m, "error": "Not authorized."}, status=403)

    # If dispute model not present, show message
    try:
        MatchDispute = apps.get_model("tournaments", "MatchDispute")
    except Exception:
        return render(request, "tournaments/match_review.html", {"match": m, "error": "Disputes not enabled."}, status=400)

    # Existing open dispute?
    existing = MatchDispute.objects.filter(match=m, is_open=True).first()
    if existing:
        return render(request, "tournaments/dispute_form.html", {"match": m, "dispute": existing})

    if request.method == "POST":
        reason = (request.POST.get("reason") or "").strip()
        if not reason:
            return render(request, "tournaments/dispute_form.html", {"match": m, "error": "Please enter a reason."})

        MatchDispute.objects.create(match=m, opened_by=actor, reason=reason, is_open=True)
        _create_event("DISPUTE_OPENED", m, actor=actor, note=reason)

        return redirect("tournaments:match_review", match_id=m.id)

    return render(request, "tournaments/dispute_form.html", {"match": m})


# ---------------------------------------------------------------------------
# Brackets & public detail
# ---------------------------------------------------------------------------

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
    # kept for compatibility; the public list lives in views_public.tournament_list
    qs = Tournament.objects.order_by("-start_at")
    return render(request, "tournaments/list.html", {"tournaments": qs})


# ---------------------------------------------------------------------------
# Admin helper (optional)
# ---------------------------------------------------------------------------

@staff_member_required
def resolve_dispute(request, match_id):
    """
    Minimal admin-only resolver for legacy paths.
    Prefer adding a dedicated staff UI that writes MatchEvent + closes MatchDispute.
    """
    m = get_object_or_404(Match, id=match_id)
    try:
        MatchDispute = apps.get_model("tournaments", "MatchDispute")
    except Exception:
        MatchDispute = None

    if request.method == "POST" and MatchDispute is not None:
        d = MatchDispute.objects.filter(match=m, is_open=True).first()
        if d:
            d.is_open = False
            d.resolution = "KEEP_REPORTED"
            d.resolved_at = timezone.now()
            d.save(update_fields=["is_open", "resolution", "resolved_at"])
            _create_event("DISPUTE_RESOLVED", m, actor=_get_profile(request.user), note="Keep reported")
        verify_and_apply(m)
        return redirect("admin:index")

    return render(request, "admin/resolve_dispute.html", {"match": m})
