from django.shortcuts import render
from django.utils import timezone
from django.apps import apps
from .services import compute_stats, get_spotlight, get_timeline

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

    ctx = {
        "featured_tournament": ft,
        "community_stats": community_stats,
        "spotlight": get_spotlight(3),
        "timeline": get_timeline(6),
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
