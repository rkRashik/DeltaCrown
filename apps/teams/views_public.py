from urllib.parse import urlencode

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import render


def team_list(request):
    """
    Public teams index with optional ?q= search and server-side pagination.
    - Schema-safe lookups (name/tag/slug only if they exist)
    - Out-of-range pages fall back to the last available page
    """
    try:
        from .models import Team  # local import to avoid circulars
    except Exception:
        ctx = {
            "teams_page": [],
            "page_obj": None,
            "q": "",
            "base_qs": "",
        }
        return render(request, "teams/index.html", ctx)

    q = (request.GET.get("q") or "").strip()

    qs = Team.objects.all()
    filters = Q()
    for field in ("name", "tag", "slug"):
        try:
            Team._meta.get_field(field)
            if q:
                filters |= Q(**{f"{field}__icontains": q})
        except Exception:
            continue
    if q and filters:
        qs = qs.filter(filters)

    qs = qs.order_by("id")

    # Build base_qs = current query string minus the page parameter
    qdict = request.GET.copy()
    qdict.pop("page", None)
    base_qs = urlencode(qdict, doseq=True)

    # Pagination
    paginator = Paginator(qs, 12)  # 12 cards per page
    page_number = request.GET.get("page") or 1
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    ctx = {
        "teams_page": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "base_qs": base_qs,
    }
    return render(request, "teams/index.html", ctx)
