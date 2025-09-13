from django.shortcuts import render
from django.utils import timezone
from django.apps import apps
from .services import compute_stats, get_spotlight, get_timeline
from django.apps import apps as django_apps

def home(request):
    """Premium homepage: dynamic NEXT EVENT + live stats.
    Picks nearest upcoming tournament (settings.start_at >= now) else latest.
    """
    ft = None
    try:
        Tournament = apps.get_model("tournaments", "Tournament")
        qs = Tournament.objects.select_related("settings")
        now = timezone.now()
        nearest = qs.filter(settings__start_at__gte=now).order_by("settings__start_at").first()
        t = nearest or qs.order_by("-id").first()
        if t:
            # Compute derived fields for the hero
            start_dt = getattr(getattr(t, "settings", None), "start_at", None) or getattr(t, "start_at", None)
            try:
                start_iso = start_dt.isoformat() if start_dt else ""
            except Exception:
                start_iso = ""
            reg_open = getattr(getattr(t, "settings", None), "reg_open_at", None) or getattr(t, "reg_open_at", None)
            reg_close = getattr(getattr(t, "settings", None), "reg_close_at", None) or getattr(t, "reg_close_at", None)
            is_open = False
            if reg_open and reg_close:
                try:
                    is_open = reg_open <= now <= reg_close
                except Exception:
                    is_open = False
            start = getattr(getattr(t, "settings", None), "start_at", None) or getattr(t, "start_at", None)
            end = getattr(getattr(t, "settings", None), "end_at", None) or getattr(t, "end_at", None)
            is_live = False
            if start and end:
                try:
                    is_live = start <= now <= end
                except Exception:
                    is_live = False
            ft = {
                "name": getattr(t, "name", None) or "Tournament",
                "start_iso": start_iso,
                "registration_open": is_open,
                "is_live": is_live,
                "register_url": getattr(t, "register_url", None) or (f"/tournaments/{t.slug}/register/" if getattr(t, "slug", None) else "/tournaments/"),
                "stream_url": getattr(t, "stream_url", None) or "/tournaments/",
                "detail_url": getattr(t, "detail_url", None) or (f"/tournaments/{t.slug}/" if getattr(t, "slug", None) else "/tournaments/"),
            }
    except Exception:
        ft = None

    # Community stats mapped to expected keys
    raw_stats = compute_stats()  # players, prize_bdt
    community_stats = {
        "players": raw_stats.get("players", 0),
        "prizes_bdt": raw_stats.get("prize_bdt", 0),
        "payout_accuracy": 98,  # default showcase value
    }
    games_strip = [
        {"slug": "efootball", "name": "eFootball", "image": "img/efootball.jpeg"},
        {"slug": "valorant", "name": "Valorant", "image": "img/Valorant.jpg"},
        {"slug": "fc26", "name": "FC 26", "image": "img/FC26.jpg"},
        {"slug": "pubg", "name": "PUBG Mobile", "image": "img/PUBG.jpeg"},
        {"slug": "mlbb", "name": "Mobile Legend", "image": "img/MobileLegend.jpg"},
        {"slug": "cs2", "name": "CS2", "image": "img/CS2.jpg"},
    ]

    ctx = {
        "featured_tournament": ft,
        "community_stats": community_stats,
        "spotlight": get_spotlight(3),
        "timeline": get_timeline(6),
        "games_strip": games_strip,
    }
    return render(request, "home.html", ctx)


def privacy(request):
    return render(request, "legal/privacy.html")


def terms(request):
    return render(request, "legal/terms.html")

def ui_showcase(request):
    game_opts = [
        ("valorant", "Valorant", True),
        ("efootball", "eFootball", False),
        ("pubg", "PUBG Mobile", False),
    ]
    radio_opts = [
        ("mode-solo", "solo", "Solo", True),
        ("mode-duo", "duo", "Duo", False),
        ("mode-squad", "squad", "Squad", False),
    ]
    return render(request, "ui_showcase.html", {"game_opts": game_opts, "radio_opts": radio_opts})

def about(request):
    # Optionally compute stats here
    stats = {
        "players": None,
        "matches": None,
        "prize_paid": None,
        "streams": None,
    }
    return render(request, "about.html", {"stats": stats})

def community(request):
    # Optionally fetch forum categories / events
    return render(request, "community.html", {
        "forum_categories": [],
        "upcoming_events": [],
    })


def _get_model(candidates):
    """Return the first model that exists from [(app_label, model_name), ...]."""
    for app_label, model_name in candidates:
        try:
            return django_apps.get_model(app_label, model_name)
        except Exception:
            continue
    return None

def community(request):
    Thread = _get_model([('forums', 'Thread'), ('forums', 'Post'), ('forums', 'Topic')])
    Tournament = _get_model([('tournaments', 'Tournament')])
    User = _get_model([('auth', 'User'), ('accounts', 'User'), ('users', 'User')])

    # Threads/feed
    threads = []
    if Thread:
        try:
            qs = Thread.objects.all().order_by('-id')  # safe ordering
            threads = list(qs[:20])
        except Exception:
            threads = []

    # Popular tags (optional; keep simple/fallback)
    popular_tags = []  # You can compute real tag counts later

    # Top users (fallback ordering)
    top_users = []
    if User:
        try:
            qs = User.objects.all().order_by('-date_joined')
            top_users = list(qs[:8])
        except Exception:
            top_users = []

    # Upcoming tournaments / events (fallback)
    upcoming_tournaments = []
    if Tournament:
        try:
            upcoming_tournaments = list(Tournament.objects.all().order_by('-id')[:6])
        except Exception:
            upcoming_tournaments = []

    # Optional extra panels (safe defaults)
    scrims = []
    events = []
    creators = []
    clips = []
    qa = []

    # KPIs (simple fallbacks)
    online_count = 42
    posts_today = len(threads)
    scrims_open = len(scrims)
    events_upcoming = len(events) or len(upcoming_tournaments)

    context = {
        'threads': threads,
        'popular_tags': popular_tags,
        'top_users': top_users,
        'upcoming_tournaments': upcoming_tournaments,
        'events': events,
        'scrims': scrims,
        'creators': creators,
        'clips': clips,
        'qa': qa,
        'online_count': online_count,
        'posts_today': posts_today,
        'scrims_open': scrims_open,
        'events_upcoming': events_upcoming,
    }
    return render(request, 'community.html', context)
