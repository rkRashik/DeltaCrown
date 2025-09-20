from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional

from django.apps import apps
from django.db.models import QuerySet
from django.urls import reverse

from .helpers import (
    read_title, read_game, read_fee_amount, banner_url, read_url,
    register_url, status_for_card, dc_map, computed_state,
)

Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
PaymentVerification = apps.get_model("tournaments", "PaymentVerification")


def annotate_cards(objs: Iterable[Any]) -> None:
    """
    Attach stable dc_* attrs used by cards/templates.
    Using object.__setattr__ avoids clashing with @property setters on models.
    """
    for t in objs:
        object.__setattr__(t, "dc_banner_url", banner_url(t))
        object.__setattr__(t, "dc_status",     status_for_card(t))
        object.__setattr__(t, "dc_register_url", register_url(t))
        object.__setattr__(t, "dc_title",      read_title(t))
        object.__setattr__(t, "dc_game",       read_game(t))
        object.__setattr__(t, "dc_fee_amount", read_fee_amount(t))
        object.__setattr__(t, "dc_url",        read_url(t))


def annotate_queryset(qs: QuerySet) -> List[Any]:
    """
    Convenience: select_related common fields, then annotate dc_* and return list.
    """
    try:
        qs = qs.select_related("settings")
    except Exception:
        pass
    objs = list(qs)
    annotate_cards(objs)
    return objs


def compute_my_states(request, tournaments: Iterable[Any]) -> Dict[int, Dict[str, Any]]:
    """
    Returns { tournament.id: {registered: bool, cta: 'continue'|'receipt'|None, cta_url: str|None} }
    Falls back gracefully if models differ.
    """
    states: Dict[int, Dict[str, Any]] = {}
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return states

    ids: List[int] = [getattr(t, "id") for t in tournaments if getattr(t, "id", None)]
    if not ids:
        return states

    try:
        reg_rows = list(Registration.objects.filter(user=user, tournament_id__in=ids).values("tournament_id", "id"))
    except Exception:
        reg_rows = []

    pv_map = {}
    try:
        if reg_rows:
            reg_ids = [r["id"] for r in reg_rows]
            for pv in PaymentVerification.objects.filter(registration_id__in=reg_ids).values("registration_id", "status"):
                pv_map[pv["registration_id"]] = pv["status"]
    except Exception:
        pv_map = {}

    reg_by_tid = {r["tournament_id"]: r["id"] for r in reg_rows}

    for t in tournaments:
        tid = getattr(t, "id", None)
        if not tid:
            continue
        if tid in reg_by_tid:
            reg_id = reg_by_tid[tid]
            status = (pv_map.get(reg_id) or "").lower()
            if status in ("", "pending", "rejected"):
                states[tid] = {"registered": True, "cta": "continue", "cta_url": register_url(t)}
            elif status in ("verified", "approved"):
                try:
                    receipt_url = reverse("tournaments:registration_receipt", args=[t.slug])
                except Exception:
                    receipt_url = register_url(t)
                states[tid] = {"registered": True, "cta": "receipt", "cta_url": receipt_url}
            else:
                states[tid] = {"registered": True, "cta": None, "cta_url": None}
        else:
            states[tid] = {"registered": False, "cta": None, "cta_url": None}

    return states


def related_tournaments(current: Any, limit: int = 6) -> List[Any]:
    """
    Returns a small list of 'more like this' tournaments (same game, not the current one),
    already dc_* annotated for cards.
    """
    try:
        game_value = getattr(current, "game", None) or getattr(current, "game_name", None)
        if not game_value:
            return []
        qs = Tournament.objects.all()
        # Basic similarity: same game (string-compare, case-insensitive), exclude self
        qs = qs.filter(game__iexact=str(game_value)).exclude(pk=getattr(current, "pk", None))
        try:
            qs = qs.select_related("settings")
        except Exception:
            pass
        qs = qs.order_by("-starts_at", "-id")[:limit]
        objs = list(qs)
    except Exception:
        objs = []

    annotate_cards(objs)
    return objs
