from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    """
    Public homepage.

    - Tries to import Tournament/Team/User profile models to populate dynamic
      sections and counters, but NEVER crashes if those apps aren't present.
    - If models are missing, we fall back to None/0 so the template shows
      placeholders gracefully.
    """
    tournaments_qs = None
    stats = {"teams": 0, "tournaments": 0, "players": 0}

    # Try to fetch tournaments (limit 6), ordered by a reasonable field
    try:
        from apps.tournaments.models import Tournament  # type: ignore
        # Prefer upcoming/ongoing; if no such field, just order by -id as fallback
        try:
            tournaments_qs = (
                Tournament.objects
                .order_by("-created_at")[:6]
            )
        except Exception:
            tournaments_qs = Tournament.objects.order_by("-id")[:6]

        # Count tournaments
        stats["tournaments"] = Tournament.objects.count()
    except Exception:
        tournaments_qs = None  # app not present or model not available

    # Try to count teams
    try:
        from apps.teams.models import Team  # type: ignore
        stats["teams"] = Team.objects.count()
    except Exception:
        pass

    # Try to count players/users
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
    """Simple health check endpoint."""
    return HttpResponse("OK")
