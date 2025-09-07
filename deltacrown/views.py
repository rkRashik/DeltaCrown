from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.http import JsonResponse

def home(request):
    """
    Public homepage.
    """
    # Try to pull dynamic stats/tournaments, but never crash
    tournaments_qs = None
    stats = {"teams": 0, "tournaments": 0, "players": 0}

    try:
        from apps.tournaments.models import Tournament  # type: ignore
        try:
            tournaments_qs = Tournament.objects.order_by("-created_at")[:6]
        except Exception:
            tournaments_qs = Tournament.objects.order_by("-id")[:6]
        stats["tournaments"] = Tournament.objects.count()
    except Exception:
        tournaments_qs = None

    try:
        from apps.teams.models import Team  # type: ignore
        stats["teams"] = Team.objects.count()
    except Exception:
        pass

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        stats["players"] = User.objects.count()
    except Exception:
        pass

    context = {
        "tournaments": tournaments_qs,
        "stats": stats,
    }
    return render(request, "homepage.html", context)


def healthz(request):
    """
    Lightweight health endpoint for uptime checks and load balancers.
    Returns HTTP 200 with a tiny JSON body.
    """
    return JsonResponse({"status": "ok"})

# --------------- Tournaments: List & Detail (safe optional) ---------------

def tournaments_list(request):
    """
    List tournaments in a responsive grid.
    If Tournament model isn't available, renders placeholders.
    """
    qs = None
    try:
        from apps.tournaments.models import Tournament  # type: ignore
        try:
            qs = Tournament.objects.order_by("-created_at")
        except Exception:
            qs = Tournament.objects.order_by("-id")
    except Exception:
        qs = None

    return render(request, "tournaments/list.html", {"tournaments": qs})


def tournament_detail(request, pk: int):
    """
    Show a single tournament with hero, meta, rules, schedule, and CTA.
    Falls back to a placeholder page if model is unavailable or object missing.
    """
    tournament = None
    try:
        from apps.tournaments.models import Tournament  # type: ignore
        try:
            tournament = Tournament.objects.get(pk=pk)
        except Tournament.DoesNotExist:  # type: ignore
            raise Http404("Tournament not found")
    except Exception:
        # If the model itself is missing, we'll render a friendly placeholder
        tournament = None

    return render(request, "tournaments/detail.html", {"tournament": tournament})
