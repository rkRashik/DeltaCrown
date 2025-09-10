from __future__ import annotations
from typing import Any, Dict, List
from django.apps import apps
from django.utils import timezone


def nav_context(request) -> Dict[str, Any]:
    """
    Navigation context for global header/footer.
    Provides: nav_live, nav_unread_count, nav_user_can_create_event, nav_primary_items.
    Safe, fast (single lightweight DB pass), and tolerant of missing apps.
    """
    now = timezone.now()
    nav_live = False
    nav_unread_count = 0
    nav_user_can_create_event = False
    nav_primary_items: List[Dict[str, Any]] = []

    # Live: any tournament with stream url and currently within start/end window
    try:
        T = apps.get_model("tournaments", "Tournament")
        qs = T.objects.select_related("settings")
        # Prefer settings window; fall back to model fields
        live_qs = qs.filter(
            settings__start_at__lte=now, settings__end_at__gte=now
        ) | qs.filter(start_at__lte=now, end_at__gte=now)
        for t in live_qs[:3]:  # bound tiny
            settings = getattr(t, "settings", None)
            if settings and (settings.stream_youtube_url or settings.stream_facebook_url):
                nav_live = True
                break
    except Exception:
        pass

    # Notifications unread count (if app installed and user authenticated)
    try:
        if getattr(request, "user", None) and request.user.is_authenticated:
            Notification = apps.get_model("notifications", "Notification")
            if Notification:
                nav_unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    except Exception:
        nav_unread_count = 0

    # Permission to create events
    try:
        u = getattr(request, "user", None)
        if u and u.is_authenticated:
            nav_user_can_create_event = bool(u.is_staff or u.has_perm("tournaments.add_tournament") or u.groups.filter(name__iexact="organizer").exists())
    except Exception:
        nav_user_can_create_event = False

    # Primary items with children (IA)
    nav_primary_items = [
        {"label": "Tournaments", "url": "/tournaments/", "children": [
            {"label": "Browse All", "url": "/tournaments/"},
            {"label": "Standings", "url": "/tournaments/"},  # contextually replaced on detail
            {"label": "Rules & Fair Play", "url": "/rules/"},
        ]},
        {"label": "Teams", "url": "/teams/", "children": [
            {"label": "Find Teams", "url": "/teams/"},
            {"label": "Create Team", "url": "/teams/create/"},
        ]},
        {"label": "Watch", "url": "/tournaments/", "live": nav_live},
        {"label": "Community", "url": "/pages/community/"},
        {"label": "About", "url": "/pages/about/"},
    ]

    return {
        "nav_live": nav_live,
        "nav_unread_count": nav_unread_count,
        "nav_user_can_create_event": nav_user_can_create_event,
        "nav_primary_items": nav_primary_items,
    }
