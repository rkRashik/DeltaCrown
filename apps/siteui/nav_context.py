from __future__ import annotations
from typing import Any, Dict, List
from django.apps import apps
from django.core.cache import cache
from django.utils import timezone

from deltacrown.middleware.bot_probe import is_bot_probe_path


def nav_context(request) -> Dict[str, Any]:
    """
    Navigation context for global header/footer.
    Provides: nav_live, nav_unread_count, nav_user_can_create_event, nav_primary_items.
    Safe, fast (single lightweight DB pass), and tolerant of missing apps.
    """
    # Skip on admin and known bot probe paths.
    if request.path.startswith('/admin/') or is_bot_probe_path(request.path):
        return {'nav_live': False, 'nav_unread_count': 0, 'nav_user_can_create_event': False, 'nav_primary_items': []}

    now = timezone.now()
    nav_live = bool(cache.get('siteui:nav_live:v1', False))
    nav_unread_count = 0
    nav_user_can_create_event = False
    nav_primary_items: List[Dict[str, Any]] = []

    if not nav_live:
        # Live: any tournament with stream url and currently within start/end window.
        # Cache briefly since this value is global and expensive to recompute on every request.
        try:
            T = apps.get_model("tournaments", "Tournament")
            live_qs = T.objects.filter(tournament_start__lte=now, tournament_end__gte=now)
            for t in live_qs[:3]:
                if getattr(t, "stream_youtube_url", "") or getattr(t, "stream_twitch_url", ""):
                    nav_live = True
                    break
            cache.set('siteui:nav_live:v1', nav_live, 30)
        except Exception:
            pass

    # Notifications unread count (if app installed and user authenticated)
    # UP PHASE 3: Include pending follow requests in count
    try:
        if getattr(request, "user", None) and request.user.is_authenticated:
            if hasattr(request, '_cached_notif_unread'):
                nav_unread_count = int(request._cached_notif_unread)
            else:
                Notification = apps.get_model("notifications", "Notification")
                if Notification:
                    nav_unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
                    request._cached_notif_unread = nav_unread_count
            
            # Add pending follow requests count
            try:
                pending_key = f"siteui:pending_follow_requests:{request.user.id}"
                pending_requests_count = cache.get(pending_key)
                if pending_requests_count is None:
                    UserProfile = apps.get_model("user_profile", "UserProfile")
                    FollowRequest = apps.get_model("user_profile", "FollowRequest")
                    user_profile = UserProfile.objects.filter(user=request.user).first()
                    if user_profile:
                        pending_requests_count = FollowRequest.objects.filter(
                            target=user_profile,
                            status='PENDING'
                        ).count()
                    else:
                        pending_requests_count = 0
                    cache.set(pending_key, pending_requests_count, 30)

                nav_unread_count += int(pending_requests_count or 0)
            except Exception:
                pass  # Follow requests not critical, don't break nav
    except Exception:
        nav_unread_count = 0

    # Permission to create events
    try:
        u = getattr(request, "user", None)
        if u and u.is_authenticated:
            perm_key = f"siteui:can_create_event:{u.id}:{int(bool(u.is_staff))}"
            cached_perm = cache.get(perm_key)
            if cached_perm is None:
                cached_perm = bool(
                    u.is_staff
                    or u.has_perm("tournaments.add_tournament")
                    or u.groups.filter(name__iexact="organizer").exists()
                )
                cache.set(perm_key, cached_perm, 60)
            nav_user_can_create_event = bool(cached_perm)
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
