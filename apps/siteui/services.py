from typing import Optional, Dict, Any
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import Sum

def get_featured() -> Optional[Dict[str, Any]]:
    """
    Try to fetch a 'featured' tournament from apps.tournaments (or similar).
    Returns dict with keys we use in templates:
      - name
      - status: "open" | "ongoing" | "closed"
      - register_url
      - stream_url
    If nothing is found, return None. Never raises if the app/model/fields differ.
    """
    # Try a few common app/model names
    model_candidates = [
        ("apps.tournaments", "Tournament"),
        ("tournaments", "Tournament"),
        ("apps.tournaments", "Event"),
        ("tournaments", "Event"),
    ]
    model = None
    for app_label, model_name in model_candidates:
        try:
            model = apps.get_model(app_label, model_name)
            break
        except Exception:
            continue
    if not model:
        return None

    try:
        qs = model.objects.all()
        # Prefer "featured" flag if it exists, else pick an open or latest ongoing
        if hasattr(model, "featured"):
            qs = qs.filter(featured=True) or model.objects.all()
        obj = (
            qs.filter(status__in=["open", "ongoing"]).order_by("-id").first()
            or qs.order_by("-id").first()
        )
        if not obj:
            return None

        # Extract fields defensively
        name = getattr(obj, "name", None) or getattr(obj, "title", None) or "Tournament"
        # status mapping
        status = getattr(obj, "status", None)
        if status not in {"open", "ongoing", "closed"}:
            # try to infer from booleans/dates if present
            if getattr(obj, "is_live", False):
                status = "ongoing"
            elif getattr(obj, "is_open", False):
                status = "open"
            else:
                status = "closed"
        # links
        register_url = getattr(obj, "register_url", None) or getattr(obj, "registration_url", None) or "/tournaments/"
        stream_url = getattr(obj, "stream_url", None) or getattr(obj, "live_url", None) or "/tournaments/"

        return {"name": str(name), "status": status, "register_url": register_url, "stream_url": stream_url}
    except Exception:
        return None


def compute_stats() -> Dict[str, int]:
    """
    Compute simple site stats with graceful fallback:
      - players: total auth users
      - prize_bdt: sum of prize fields if present on tournaments
      - payout_accuracy_pct: leave as SITE default (we don't guess it)
    """
    stats = {
        "players": 0,
        "prize_bdt": 0,
    }

    # Users
    try:
        User = get_user_model()
        stats["players"] = User.objects.count()
    except Exception:
        pass

    # Prize pool (optional)
    # Try common models/fields: prize_bdt / prize / prize_pool in tournaments
    for app_label, model_name in [
        ("apps.tournaments", "Tournament"),
        ("tournaments", "Tournament"),
        ("apps.tournaments", "Event"),
        ("tournaments", "Event"),
    ]:
        try:
            M = apps.get_model(app_label, model_name)
        except Exception:
            M = None
        if not M:
            continue
        for field in ["prize_bdt", "prize", "prize_pool"]:
            if hasattr(M, field):
                try:
                    total = M.objects.aggregate(total=Sum(field)).get("total") or 0
                    stats["prize_bdt"] = int(total)
                    break
                except Exception:
                    pass
        if stats["prize_bdt"]:
            break

    return stats

from typing import List

def get_spotlight(limit: int = 3) -> List[Dict[str, Any]]:
    """
    Return up to `limit` spotlight items.
    Tries common sources: NewsItem/Post/Tournament with 'featured' or recent.
    Each item: {title, href, kicker, badge, image, excerpt}
    """
    items: List[Dict[str, Any]] = []
    candidates = [
        ("apps.news", "NewsItem", {"order": "-published_at"}),
        ("news", "NewsItem", {"order": "-published_at"}),
        ("apps.blog", "Post", {"order": "-published_at"}),
        ("blog", "Post", {"order": "-published_at"}),
        ("apps.tournaments", "Tournament", {"order": "-id"}),
        ("tournaments", "Tournament", {"order": "-id"}),
    ]
    for app_label, model_name, hints in candidates:
        try:
            M = apps.get_model(app_label, model_name)
        except Exception:
            M = None
        if not M:
            continue

        try:
            qs = M.objects.all()
            # Prefer featured if field exists
            if hasattr(M, "featured"):
                feat = qs.filter(featured=True)
                if feat.exists():
                    qs = feat
            order = hints.get("order")
            if order:
                qs = qs.order_by(order)
            for obj in qs[: max(0, limit - len(items))]:
                title = getattr(obj, "title", None) or getattr(obj, "name", None) or "Untitled"
                href = getattr(obj, "get_absolute_url", None)
                href = href() if callable(href) else getattr(obj, "url", None) or "/"
                kicker = getattr(obj, "kicker", None) or getattr(obj, "category", None) or ""
                badge = getattr(obj, "status", None) or ""
                image = getattr(obj, "image_url", None) or getattr(obj, "cover_url", None) or ""
                excerpt = getattr(obj, "excerpt", None) or getattr(obj, "summary", None) or ""
                items.append({"title": str(title), "href": href, "kicker": str(kicker), "badge": str(badge), "image": image, "excerpt": str(excerpt)})
            if len(items) >= limit:
                break
        except Exception:
            continue
    return items[:limit]


def get_timeline(limit: int = 6) -> List[Dict[str, Any]]:
    """
    Return up to `limit` timeline entries.
    Tries common sources: Milestone/Match/Tournament ordered by date/id.
    Each entry: {date_iso, label, href}
    """
    entries: List[Dict[str, Any]] = []
    candidates = [
        ("apps.timeline", "Milestone", {"date": "date"}),
        ("timeline", "Milestone", {"date": "date"}),
        ("apps.tournaments", "Match", {"date": "start_time"}),
        ("tournaments", "Match", {"date": "start_time"}),
        ("apps.tournaments", "Tournament", {"date": "created_at"}),
        ("tournaments", "Tournament", {"date": "created_at"}),
    ]
    for app_label, model_name, hints in candidates:
        try:
            M = apps.get_model(app_label, model_name)
        except Exception:
            M = None
        if not M:
            continue
        try:
            date_field = hints.get("date") or "created_at"
            order = f"-{date_field}" if hasattr(M, date_field) else "-id"
            qs = M.objects.all().order_by(order)
            for obj in qs[: max(0, limit - len(entries))]:
                # date_iso best effort
                dt = getattr(obj, date_field, None)
                date_iso = getattr(dt, "date", lambda: None)() or dt
                date_iso = getattr(date_iso, "isoformat", lambda: "")() or ""
                label = getattr(obj, "title", None) or getattr(obj, "name", None) or getattr(obj, "label", None) or f"{model_name} #{getattr(obj, 'id', '')}"
                href = getattr(obj, "get_absolute_url", None)
                href = href() if callable(href) else getattr(obj, "url", None) or "/"
                entries.append({"date_iso": date_iso, "label": str(label), "href": href})
            if len(entries) >= limit:
                break
        except Exception:
            continue
    return entries[:limit]

