"""
Service layer for Organization Directory page.

Handles business logic for the global organization rankings view.
"""

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, Prefetch

from apps.organizations.models import Organization


def get_directory_context(*, q: str = "", region: str = "", page: int = 1, page_size: int = 20) -> dict:
    """
    Get context data for organization directory page.
    
    Returns filtered and paginated organization list with top 3 featured orgs.
    
    Args:
        q: Search query (matches name, slug, or public_id)
        region: Region filter (filters by profile.region_code)
        page: Current page number (1-indexed)
        page_size: Number of orgs per page (default: 20)
    
    Returns:
        dict: {
            "top_three_orgs": QuerySet of top 3 orgs (by empire_score or updated_at),
            "rows": QuerySet of remaining orgs (excludes top 3),
            "total_count": int - total matching orgs,
            "page": int - current page number,
            "page_size": int - page size,
            "page_count": int - total pages,
            "q": str - search query (for form re-population),
            "region": str - region filter (for form re-population),
        }
    
    Database performance:
        - Uses select_related for ranking, profile, ceo
        - Query count: ~3-5 queries (base + top_three + paginated rows)
    """
    # Base queryset with necessary related objects
    qs = Organization.objects.select_related(
        'ranking',  # For empire_score ordering
        'profile',  # For region_code filtering
        'ceo',      # For CEO name display
    ).annotate(
        squads_count=Count('teams', distinct=True),
    )
    
    # Search filtering (name, slug, or public_id)
    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(slug__icontains=q) |
            Q(public_id__icontains=q)
        )
    
    # Region filtering (defensive: handle missing profile gracefully)
    if region:
        qs = qs.filter(profile__region_code__iexact=region)
    
    # Ordering: prefer empire_score desc, fallback to updated_at desc
    # Use conditional ordering to handle orgs without ranking
    qs = qs.order_by(
        '-ranking__empire_score',  # Primary: highest empire score first
        '-updated_at'              # Fallback: most recently updated
    )
    
    # Get total count before pagination
    total_count = qs.count()
    
    # Extract top 3 orgs (featured podium display)
    top_three_orgs = list(qs[:3])
    top_three_ids = [org.id for org in top_three_orgs]
    
    # Exclude top 3 from rows
    rows_qs = qs.exclude(id__in=top_three_ids) if top_three_ids else qs
    
    # Paginate remaining rows
    paginator = Paginator(rows_qs, page_size)
    
    try:
        rows_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        rows_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        rows_page = paginator.page(paginator.num_pages)
    
    return {
        "top_three_orgs": top_three_orgs,
        "rows": rows_page.object_list,
        "total_count": total_count,
        "page": rows_page.number,
        "page_size": page_size,
        "page_count": paginator.num_pages,
        "q": q,
        "region": region,
        "has_previous": rows_page.has_previous(),
        "has_next": rows_page.has_next(),
        "previous_page_number": rows_page.previous_page_number() if rows_page.has_previous() else None,
        "next_page_number": rows_page.next_page_number() if rows_page.has_next() else None,
    }
