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
