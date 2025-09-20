from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from django.apps import apps
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .helpers import (
    first, fmt_money, as_bool, as_html, maybe_text,
    banner_url, read_title, read_game, read_fee_amount, register_url,
    computed_state, role_for, user_reg, next_cta,
    coin_policy_of, rules_pdf_of, load_participants, load_standings,
    live_stream_info, bracket_url_of, build_tabs, hero_meta_for, slugify_game,
    GAME_REGISTRY, build_pdf_viewer_config,
)
from .cards import annotate_cards, compute_my_states, related_tournaments

Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")

# Optional/forgiving team models (work with either app label)
def _get_model(app_label: str, name: str):
    try:
        return apps.get_model(app_label, name)
    except Exception:
        return None

Team = _get_model("tournaments", "Team") or _get_model("teams", "Team")
TeamMembership = _get_model("tournaments", "TeamMembership") or _get_model("teams", "TeamMembership")


def _is_team_event(t: Any) -> bool:
    """Detect if this tournament is a team event (multiple schema patterns supported)."""
    for attr in ("is_team_event", "team_mode"):
        if hasattr(t, attr) and getattr(t, attr):
            return True
    for attr in ("team_size_min", "team_min", "min_team_size"):
        if hasattr(t, attr) and (getattr(t, attr) or 0) > 1:
            return True
    mode = (getattr(t, "mode", "") or "").lower()
    return mode in {"team", "teams", "squad", "5v5", "3v3", "2v2"}


def _user_team(user) -> Tuple[Optional[Any], Optional[Any]]:
    """Return (team, membership) for the current user, if any."""
    if not Team or not TeamMembership or not getattr(user, "is_authenticated", False):
        return None, None
    try:
        mem = TeamMembership.objects.select_related("team").filter(user=user).first()
        return (mem.team if mem else None), mem
    except Exception:
        # Fallback: some schemas have user.team directly
        return getattr(user, "team", None), None


def _is_captain(membership: Optional[Any]) -> bool:
    if not membership:
        return False
    if hasattr(membership, "is_captain"):
        return bool(getattr(membership, "is_captain"))
    role = (getattr(membership, "role", "") or "").lower()
    return role in {"captain", "cap", "leader", "owner"}


def _team_already_registered(t: Any, team: Any) -> bool:
    """True if this team (or any of its members) is already registered for t."""
    if not team:
        return False
    # Prefer a direct FK on Registration if present
    try:
        return Registration.objects.filter(tournament=t, team=team).exists()
    except Exception:
        pass
    # Fallback by members
    try:
        members = TeamMembership.objects.filter(team=team).values_list("user_id", flat=True)
        return Registration.objects.filter(tournament=t, user_id__in=list(members)).exists()
    except Exception:
        return False


# -------------------------- HUB --------------------------
def hub(request: HttpRequest) -> HttpResponse:
    """
    Tournaments landing page with featured rows + search/filter.
    Lightweight and empty-safe. Uses annotate_cards() for dc_* fields.
    """
    q      = request.GET.get("q") or ""
    status = request.GET.get("status")
    start  = request.GET.get("start")
    fee    = request.GET.get("fee")
    sort   = request.GET.get("sort")

    base = Tournament.objects.all().order_by("-id")

    # Text search across common fields
    if q:
        base = base.filter(
            Q(title__icontains=q) |
            Q(name__icontains=q)  |
            Q(game__icontains=q)  |
            Q(description__icontains=q)
        )

    # Filters (best-effort)
    if status == "open" and hasattr(Tournament, "is_open"):
        base = base.filter(is_open=True)
    elif status == "live" and hasattr(Tournament, "status"):
        base = base.filter(status__iexact="live")

    if start == "7d" and hasattr(Tournament, "starts_at"):
        now = timezone.now()
        soon = now + timezone.timedelta(days=7)
        base = base.filter(starts_at__gte=now, starts_at__lte=soon)

    if fee == "free":
        if hasattr(Tournament, "fee_amount"):
            base = base.filter(fee_amount=0)
        elif hasattr(Tournament, "entry_fee_bdt") or hasattr(Tournament, "entry_fee"):
            field = "entry_fee_bdt" if hasattr(Tournament, "entry_fee_bdt") else "entry_fee"
            base = base.filter(**{field: 0})

    # Sorting
    if sort == "new":
        base = base.order_by("-id")
    elif sort == "fee_asc" and hasattr(Tournament, "fee_amount"):
        base = base.order_by("fee_amount")

    # Curated rows (best-effort)
    live_qs: List[Any] = list(base.filter(status__iexact="live")[:6]) if hasattr(Tournament, "status") else []
    starting_soon_qs: List[Any] = []
    new_this_week_qs: List[Any] = []
    free_qs: List[Any] = []

    if hasattr(Tournament, "starts_at"):
        now = timezone.now()
        soon = now + timezone.timedelta(days=7)
        starting_soon_qs = list(base.filter(starts_at__gte=now, starts_at__lte=soon).order_by("starts_at")[:6])
        if hasattr(Tournament, "created_at"):
            new_this_week_qs = list(base.filter(created_at__gte=now - timezone.timedelta(days=7))[:6])
        else:
            new_this_week_qs = list(base[:6])

    if hasattr(Tournament, "fee_amount"):
        free_qs = list(base.filter(fee_amount=0)[:6])
    elif hasattr(Tournament, "entry_fee_bdt") or hasattr(Tournament, "entry_fee"):
        field = "entry_fee_bdt" if hasattr(Tournament, "entry_fee_bdt") else "entry_fee"
        free_qs = list(base.filter(**{field: 0})[:6])

    # Main grid (first page)
    tournaments = list(base[:24])

    # Annotate all querysets for cards (dc_* fields)
    annotate_cards(tournaments)
    annotate_cards(live_qs)
    annotate_cards(starting_soon_qs)
    annotate_cards(new_this_week_qs)
    annotate_cards(free_qs)

    # Browse-by-game meta with counts
    games = []
    for key, g in GAME_REGISTRY.items():
        cnt = base.filter(game=key).count() if hasattr(Tournament, "game") else 0
        games.append({
            "slug": key, "name": g["name"],
            "primary": g["primary"], "image": g.get("card_image"),
            "count": cnt,
        })

    # My registration states for the visible grid
    my_states = compute_my_states(request, tournaments)

    # Light stats (best-effort)
    stats = {"total_active": 0}
    try:
        stats["total_active"] = base.filter(is_open=True).count() if hasattr(Tournament, "is_open") else base.count()
    except Exception:
        pass

    ctx = {
        "q": q, "sort": sort,
        "tournaments": tournaments,
        "live_tournaments": live_qs,
        "starting_soon": starting_soon_qs,
        "new_this_week": new_this_week_qs,
        "free_tournaments": free_qs,
        "games": games,
        "my_reg_states": my_states,
        "stats": stats,
    }
    return render(request, "tournaments/hub.html", ctx)


# ---------------------- LIST BY GAME ----------------------
def list_by_game(request: HttpRequest, game: str) -> HttpResponse:
    """
    Game-specific listing with search/filter/sort.
    """
    base = Tournament.objects.all()
    if hasattr(Tournament, "game"):
        base = base.filter(game=game)

    q      = request.GET.get("q") or ""
    fee    = request.GET.get("fee")
    status = request.GET.get("status")
    start  = request.GET.get("start")
    sort   = request.GET.get("sort")

    if q:
        base = base.filter(Q(title__icontains=q) | Q(name__icontains=q) | Q(description__icontains=q))

    if fee == "free":
        if hasattr(Tournament, "fee_amount"):
            base = base.filter(fee_amount=0)
        elif hasattr(Tournament, "entry_fee_bdt") or hasattr(Tournament, "entry_fee"):
            field = "entry_fee_bdt" if hasattr(Tournament, "entry_fee_bdt") else "entry_fee"
            base = base.filter(**{field: 0})

    if status == "open" and hasattr(Tournament, "is_open"):
        base = base.filter(is_open=True)

    if start == "7d" and hasattr(Tournament, "starts_at"):
        now = timezone.now()
        soon = now + timezone.timedelta(days=7)
        base = base.filter(starts_at__gte=now, starts_at__lte=soon)

    if sort == "new":
        base = base.order_by("-id")
    elif sort == "fee_asc" and hasattr(Tournament, "fee_amount"):
        base = base.order_by("fee_amount")

    tournaments = list(base[:36])
    annotate_cards(tournaments)

    # game visual meta
    gslug = game
    gm = GAME_REGISTRY.get(gslug, {"name": game.title(), "primary": "#7c3aed"})
    total = base.count()
    my_states = compute_my_states(request, tournaments)

    ctx = {
        "q": q, "sort": sort,
        "game": game, "game_meta": gm,
        "tournaments": tournaments,
        "total": total,
        "my_reg_states": my_states,
    }
    return render(request, "tournaments/list_by_game.html", ctx)


# -------------------------- DETAIL --------------------------
def detail(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Premium esports detail page: hero, live media, bracket, participants, standings,
    rules/policy accordions, contextual CTA, countdown, and related tournaments.

    Now team-aware: exposes flags for CTA logic (already registered / captain only).
    """
    t = get_object_or_404(Tournament, slug=slug)

    # Base fields
    title = read_title(t)
    game  = read_game(t)
    gslug = slugify_game(game)

    entry_fee  = read_fee_amount(t)
    prize_pool = first(getattr(t, "prize_pool_bdt", None), getattr(t, "prize_total", None))

    starts_at  = first(getattr(t, "starts_at", None), getattr(t, "start_at", None))
    ends_at    = first(getattr(t, "ends_at", None),   getattr(t, "end_at", None))
    reg_open   = getattr(t, "reg_open_at", None)
    reg_close  = getattr(t, "reg_close_at", None)
    chk_open   = first(getattr(t, "check_in_open_at", None), getattr(getattr(t, "settings", None), "check_in_open_at", None))
    chk_close  = first(getattr(t, "check_in_close_at", None), getattr(getattr(t, "settings", None), "check_in_close_at", None))

    # Format
    format_type = first(getattr(getattr(t, "settings", None), "tournament_type", None), getattr(t, "format", None))
    best_of     = first(getattr(getattr(t, "settings", None), "best_of", None), getattr(t, "best_of", None))
    min_team    = first(getattr(getattr(t, "settings", None), "min_team_size", None), getattr(t, "min_team_size", None))
    max_team    = first(getattr(getattr(t, "settings", None), "max_team_size", None), getattr(t, "max_team_size", None))
    platform    = first(getattr(getattr(t, "settings", None), "platform", None), getattr(t, "platform", None))
    region      = first(getattr(getattr(t, "settings", None), "region", None), getattr(t, "region", None))
    check_in_required = as_bool(getattr(getattr(t, "settings", None), "check_in_required", None), False)

    # Capacity / slots (best-effort)
    cap_total = first(getattr(t, "capacity", None), getattr(getattr(t, "settings", None), "capacity", None))
    reg_count = 0
    try:
        for name in ("registrations", "participants", "teams"):
            if hasattr(t, name):
                rel = getattr(t, name)
                if hasattr(rel, "count"):
                    reg_count = rel.count()
                    break
    except Exception:
        pass

    # Descriptions
    short_desc = as_html(first(getattr(t, "short_description", None), getattr(t, "summary", None), getattr(getattr(t, "settings", None), "short_description", None)))
    desc_html  = as_html(first(getattr(t, "description", None), getattr(getattr(t, "settings", None), "description", None)))

    # Rules / policy
    rules_text = maybe_text(
        getattr(t, "rules_text", None), getattr(t, "rules_html", None),
        getattr(getattr(t, "settings", None), "rules_text", None),
        getattr(getattr(t, "settings", None), "rules_html", None)
    )
    extra_rules = maybe_text(
        getattr(t, "additional_rules", None),
        getattr(getattr(t, "settings", None), "additional_rules", None)
    )
    rules_url, rules_filename = rules_pdf_of(t)
    coin_policy = coin_policy_of(t)

    # Live / bracket
    live_info   = live_stream_info(t)         # {stream, status, viewers}
    bracket_url = bracket_url_of(t)

    # Data-heavy sections
    participants = load_participants(t)       # [{name, seed, status, logo, captain, region, record}]
    standings    = load_standings(t)          # [{rank, name, points}]

    # State & CTA + hero meta
    state   = computed_state(t)
    banner  = banner_url(t)
    reg_url = register_url(t)
    cta     = next_cta(request.user, t, state, entry_fee, reg_url)
    hero    = hero_meta_for(t)                # theme colors, countdown, tz label, game icon

    # Tabs based on content
    tabs = build_tabs(
        participants=participants,
        prize_pool=prize_pool,
        rules_text=rules_text, extra_rules=extra_rules, rules_pdf_url=rules_url,
        standings=standings, bracket_url=bracket_url,
        live_info=live_info, coin_policy_text=coin_policy
    )

    # active tab sanitized to a valid tab name
    active_tab = (request.GET.get("tab") or "overview").lower()
    if active_tab not in tabs:
        active_tab = "overview"

    # Related tournaments (same game, excluding self) — ready for cards
    related = related_tournaments(t, limit=8)

    # PDF.js viewer config (theme-aware; templates may toggle light/dark)
    pdf_viewer = build_pdf_viewer_config(t, theme="auto")

    # -------- NEW: team-awareness for CTA visibility --------
    is_team = _is_team_event(t)
    team, membership = _user_team(request.user)
    user_is_captain = _is_captain(membership)
    team_registered = _team_already_registered(t, team) if team else False

    # Build context
    ctx = {
        # hero & primary info
        "title": title,
        "short_desc": short_desc,
        "desc_html": desc_html,
        "banner": banner,
        "game": game,
        "game_slug": gslug,
        "hero": hero,                      # {game_slug, game_name, theme{primary,glowA,glowB}, countdown, tz_label}
        "platform": platform, "region": region,

        # money & schedule
        "entry_fee": entry_fee, "entry_fee_fmt": fmt_money(entry_fee),
        "prize_pool": prize_pool, "prize_pool_fmt": fmt_money(prize_pool),
        "schedule": {
            "reg_open": reg_open, "reg_close": reg_close,
            "checkin_open": chk_open, "checkin_close": chk_close,
            "starts_at": starts_at, "ends_at": ends_at,
        },

        # format + slots
        "format": {
            "type": format_type, "best_of": best_of,
            "team_min": min_team, "team_max": max_team,
            "check_in_required": check_in_required,
        },
        "slots": {"current": reg_count, "capacity": cap_total},

        # sections
        "participants": participants,
        "standings": standings,
        "prizes": [],  # optional normalized breakdown if you store it later
        "bracket_url": bracket_url,
        "live": live_info,                 # {stream, status, viewers}

        # rules & policy
        "rules": {"text": rules_text, "extra": extra_rules, "pdf_url": rules_url, "pdf_name": rules_filename},
        "pdf_viewer": pdf_viewer,          # <-- config for inline PDF.js viewer
        "coin_policy": coin_policy,

        # UI/CTA
        "ui": {
            "state": state,
            "user_role": role_for(request.user, t),
            "user_registration": user_reg(request.user, t),
            "next_call_to_action": cta,
            "can_register": cta["kind"] in ("register", "pay", "checkin"),
            "show_live": bool(live_info.get("stream") or live_info.get("status") == "live"),
        },

        # NEW: team-aware flags for template CTA logic
        "is_team_event": is_team,
        "team": team,
        "user_is_captain": user_is_captain,
        "team_registered": team_registered,

        # tabs/nav
        "tabs": tabs,
        "active_tab": active_tab,

        # urls & related
        "register_url": reg_url,
        "related": related,

        # raw
        "t": t,
    }

    return render(request, "tournaments/detail.html", {"ctx": ctx})
