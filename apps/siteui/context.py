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



from django.core.cache import cache
from django.apps import apps
from django.db.models import Q


def nav_flags(request):
    """
    Adds `nav_live` to all templates. Cached for 30s to keep it fast.
    """
    key = "dc_nav_live"
    val = cache.get(key)
    if val is None:
        live = False
        for app_label, model_name in (("media","Broadcast"), ("streams","Stream"), ("siteui","Broadcast")):
            try:
                Model = apps.get_model(app_label, model_name)
            except Exception:
                continue
            if not Model:
                continue
            try:
                if Model.objects.filter(Q(is_live=True)).exists():
                    live = True
                    break
            except Exception:
                continue
        cache.set(key, live, 30)
        val = live
    return {"nav_live": val}