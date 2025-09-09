# apps/siteui/context.py
from .site_content import SITE_CONTENT
from . import services

def site_settings(request):
    """
    Inject SITE defaults + dynamic featured/stats/spotlight/timeline.
    Safe-by-default: never raise if sources are missing.
    """
    site = dict(SITE_CONTENT)

    # Featured
    try:
        featured = services.get_featured()
    except Exception:
        featured = None

    # Stats
    try:
        live_stats = services.compute_stats() or {}
        merged = dict(site.get("stats") or {})
        for k, v in live_stats.items():
            if v is not None:
                merged[k] = v
        site["stats"] = merged
    except Exception:
        pass

    # Spotlight
    try:
        spotlight_items = services.get_spotlight(limit=3)
    except Exception:
        spotlight_items = []

    # Timeline
    try:
        timeline_entries = services.get_timeline(limit=6)
    except Exception:
        timeline_entries = []

    return {
        "SITE": site,
        "featured": featured,
        "spotlight_items": spotlight_items,
        "timeline_entries": timeline_entries,
    }
