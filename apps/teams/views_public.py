from django.db.models import Q
from django.shortcuts import render

def team_list(request):
    """
    Public teams index with optional ?q= search across common fields.
    Defensive to schema differences; falls back cleanly.
    """
    try:
        from .models import Team  # local import to avoid circulars
    except Exception:
        # If Team model is unavailable for any reason, show empty list
        return render(request, "teams/index.html", {"teams": [], "q": ""})

    q = (request.GET.get("q") or "").strip()
    teams_qs = Team.objects.all()

    # Build a safe OR filter only on fields that exist
    filters = Q()
    for field in ("name", "tag", "slug"):
        try:
            Team._meta.get_field(field)
            if q:
                filters |= Q(**{f"{field}__icontains": q})
        except Exception:
            continue
    if q and filters:
        teams_qs = teams_qs.filter(filters)

    # Stable ordering that always exists
    teams_qs = teams_qs.order_by("id")[:200]
    return render(request, "teams/index.html", {"teams": teams_qs, "q": q})
