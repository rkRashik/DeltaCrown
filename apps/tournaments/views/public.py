from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from django.apps import apps
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.generic import TemplateView

# Schedule helpers for backward compatibility
from apps.tournaments.utils.schedule_helpers import (
    is_registration_open, is_tournament_live, optimize_queryset_for_schedule
)

from .helpers import (
    first, fmt_money, as_bool, as_html, maybe_text,
    banner_url, read_title, read_game, read_fee_amount, register_url,
    computed_state, role_for, user_reg, next_cta,
    coin_policy_of, rules_pdf_of, load_participants, load_standings,
    live_stream_info, bracket_url_of, build_tabs, hero_meta_for, slugify_game,
    GAME_REGISTRY, build_pdf_viewer_config,
)
# Annotation functions for tournament cards
def annotate_cards(tournaments):
    """Add dc_* fields to tournament objects for template compatibility."""
    from apps.common.game_assets import get_game_data
    
    for t in tournaments:
        # Basic fields
        t.dc_title = getattr(t, 'name', '') or 'Untitled Tournament'
        t.dc_url = getattr(t, 'get_absolute_url', lambda: '#')()
        t.dc_slug = getattr(t, 'slug', '')  # Add slug for dynamic buttons
        t.dc_game = getattr(t, 'game_name', '') or getattr(t, 'game', '')
        t.dc_banner_url = getattr(t, 'banner_url', None)
        
        # Game logo from game_assets
        game_code = getattr(t, 'game', '').upper()
        game_data = get_game_data(game_code)
        t.game_logo = game_data.get('logo', 'img/game_logos/default_game_logo.jpg')
        
        # Financial fields
        entry_fee = getattr(t, 'entry_fee_bdt', None) or getattr(t, 'entry_fee', None)
        t.dc_fee_amount = float(entry_fee) if entry_fee is not None else 0.0
        
        prize_pool = getattr(t, 'prize_pool_bdt', None) or getattr(t, 'prize_pool', None)
        t.dc_prize_amount = float(prize_pool) if prize_pool is not None else None
        
        # Status and timing
        t.dc_status = _compute_display_status(t)
        
        # Slots information
        slots_total = getattr(t, 'slot_size', None) or getattr(t, 'slots_total', None)
        slots_taken = getattr(t, 'slots_taken', None) or 0
        t.dc_slots_capacity = slots_total
        t.dc_slots_current = slots_taken
        
        # Registration URL (don't override property, just ensure it exists)
        if not hasattr(t, 'register_url') or getattr(t, 'register_url', None) is None:
            # Only set if it's not a property or if the property returns None
            try:
                setattr(t, '_register_url', f'/tournaments/register-enhanced/{getattr(t, "slug", "")}')
            except AttributeError:
                # If it's a read-only property, skip setting it
                pass
        
        # Date fields for templates
        t.starts_at = getattr(t, 'start_at', None)
        
    return tournaments

def _compute_display_status(tournament):
    """Compute user-friendly status for tournament cards."""
    from django.utils import timezone
    
    now = timezone.now()
    status = getattr(tournament, 'status', '').upper()
    
    # Check if registration is open
    if is_registration_open(tournament):
        return 'open'
    
    # Check schedule-based status
    start_at = getattr(tournament, 'start_at', None)
    end_at = getattr(tournament, 'end_at', None)
    
    if start_at and end_at:
        if now < start_at:
            return 'open' if status == 'PUBLISHED' else 'closed'
        elif start_at <= now <= end_at:
            return 'live'
        elif now > end_at:
            return 'finished'
    
    # Fallback to model status
    if status == 'PUBLISHED':
        return 'open'
    elif status == 'RUNNING':
        return 'live'
    elif status == 'COMPLETED':
        return 'finished'
    else:
        return 'closed'

def compute_my_states(request, tournaments):
    """Compute user registration states for tournaments."""
    if not getattr(request.user, 'is_authenticated', False):
        return {}
    
    states = {}
    for t in tournaments:
        tournament_id = getattr(t, 'id', None)
        if not tournament_id:
            continue
            
        try:
            # Check if user is registered
            registration = Registration.objects.filter(
                tournament=t,
                user=request.user
            ).first()
            
            if registration:
                reg_status = getattr(registration, 'status', '').upper()
                states[tournament_id] = {
                    'registered': True,
                    'status': reg_status,
                    'cta': 'continue' if reg_status == 'CONFIRMED' else 'receipt',
                    'cta_url': f'/tournaments/{getattr(t, "slug", "")}/dashboard/'
                }
            else:
                states[tournament_id] = {
                    'registered': False,
                    'status': None,
                    'cta': 'register',
                    'cta_url': getattr(t, 'register_url', '#')
                }
        except Exception:
            states[tournament_id] = {
                'registered': False, 
                'status': None,
                'cta': 'register',
                'cta_url': '#'
            }
    
    return states

def related_tournaments(tournament, limit=8):
    """Get related tournaments by game."""
    try:
        return Tournament.objects.filter(
            game=tournament.game,
            status='PUBLISHED'
        ).exclude(
            id=tournament.id
        ).order_by('-created_at')[:limit]
    except Exception:
        return Tournament.objects.none()

Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")

def _get_model(app_label: str, name: str):
    """Safe get_model that returns None if missing."""
    try:
        return apps.get_model(app_label, name)
    except Exception:
        return None

# Optional/forgiving team models (handles multiple app labels)
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
    try:
        return Registration.objects.filter(tournament=t, team=team).exists()
    except Exception:
        pass
    try:
        members = TeamMembership.objects.filter(team=team).values_list("user_id", flat=True)
        return Registration.objects.filter(tournament=t, user_id__in=list(members)).exists()
    except Exception:
        return False


# -------------------------- HUB --------------------------
def hub(request: HttpRequest) -> HttpResponse:
    """Landing page with featured rows + search/filter (empty-safe)."""
    q      = request.GET.get("q") or ""
    status = request.GET.get("status")
    start  = request.GET.get("start")
    fee    = request.GET.get("fee")
    sort   = request.GET.get("sort")

    base = Tournament.objects.all().order_by("-id")

    # Search
    if q:
        base = base.filter(
            Q(title__icontains=q) |
            Q(name__icontains=q)  |
            Q(game__icontains=q)  |
            Q(description__icontains=q)
        )

    # Filters
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

    # Feature rows (best-effort)
    live_qs: List[Any] = []
    starting_soon_qs: List[Any] = []
    new_this_week_qs: List[Any] = []
    free_qs: List[Any] = []
    
    now = timezone.now()
    
    # Live tournaments - check both status and timing
    if hasattr(Tournament, "status"):
        live_by_status = list(base.filter(status__iexact="RUNNING")[:3])
        live_qs.extend(live_by_status)
    
    # Also check for tournaments that should be live based on timing
    if hasattr(Tournament, "start_at") and hasattr(Tournament, "end_at"):
        live_by_time = list(base.filter(
            start_at__lte=now,
            end_at__gte=now,
            status="PUBLISHED"
        ).exclude(id__in=[t.id for t in live_qs])[:3])
        live_qs.extend(live_by_time)
    
    live_qs = live_qs[:6]  # Limit to 6 total

    if hasattr(Tournament, "start_at"):
        soon = now + timezone.timedelta(days=7)
        starting_soon_qs = list(base.filter(
            start_at__gte=now, 
            start_at__lte=soon,
            status="PUBLISHED"
        ).order_by("start_at")[:6])
        
    if hasattr(Tournament, "created_at"):
        week_ago = now - timezone.timedelta(days=7)
        new_this_week_qs = list(base.filter(
            created_at__gte=week_ago,
            status="PUBLISHED"
        ).order_by("-created_at")[:6])
    else:
        new_this_week_qs = list(base.filter(status="PUBLISHED")[:6])

    # Free tournaments
    if hasattr(Tournament, "entry_fee_bdt"):
        free_qs = list(base.filter(
            entry_fee_bdt__isnull=True,
            status="PUBLISHED"
        )[:6])
        if not free_qs:
            free_qs = list(base.filter(
                entry_fee_bdt=0,
                status="PUBLISHED"
            )[:6])

    tournaments = list(base[:24])

    # Card annotations
    annotate_cards(tournaments)
    annotate_cards(live_qs)
    annotate_cards(starting_soon_qs)
    annotate_cards(new_this_week_qs)
    annotate_cards(free_qs)

    # Browse-by-game meta - use actual tournament game choices
    games = []
    if hasattr(Tournament, "Game"):
        # Use the model's game choices
        for game_choice in Tournament.Game.choices:
            game_key = game_choice[0]  # valorant, efootball, etc.
            game_display = game_choice[1]  # Valorant, eFootball Mobile, etc.
            
            # Get count of published tournaments for this game
            cnt = base.filter(game=game_key, status="PUBLISHED").count()
            
            # Get registry data or use defaults
            g = GAME_REGISTRY.get(game_key, {})
            games.append({
                "slug": game_key, 
                "name": game_display,
                "primary": g.get("primary", "#7c3aed"), 
                "image": g.get("card_image"),
                "count": cnt,
            })
    else:
        # Fallback to registry only
        for key, g in GAME_REGISTRY.items():
            cnt = base.filter(game=key).count() if hasattr(Tournament, "game") else 0
            games.append({
                "slug": key, "name": g["name"],
                "primary": g["primary"], "image": g.get("card_image"),
                "count": cnt,
            })

    my_states = compute_my_states(request, tournaments)

    # Real stats from database
    stats = {}
    try:
        # Active tournaments (published and registration open or running)
        active_count = base.filter(
            status__in=["PUBLISHED", "RUNNING"]
        ).count()
        stats["total_active"] = active_count
        
        # Players this month (from registrations)
        from datetime import datetime
        this_month_start = datetime(now.year, now.month, 1, tzinfo=now.tzinfo)
        players_this_month = Registration.objects.filter(
            created_at__gte=this_month_start
        ).values('user').distinct().count()
        stats["players_this_month"] = f"{players_this_month:,}"
        
        # Prize pool this month (from published tournaments)
        from django.db.models import Sum
        prize_sum = base.filter(
            status="PUBLISHED",
            created_at__gte=this_month_start,
            prize_pool_bdt__isnull=False
        ).aggregate(total=Sum('prize_pool_bdt'))['total']
        
        if prize_sum:
            stats["prize_pool_month"] = f"{int(prize_sum):,}"
        else:
            stats["prize_pool_month"] = "0"
            
    except Exception as e:
        # Fallback values
        stats = {
            "total_active": base.filter(status="PUBLISHED").count(),
            "players_this_month": "0",
            "prize_pool_month": "0"
        }

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
    """Game-specific listing with search/filter/sort."""
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
    rules/policy tabs, contextual CTA, countdown, related tournaments.

    Team-aware flags drive CTA & visibility, and prizes include merged coin amounts.
    """
    t = get_object_or_404(Tournament, slug=slug)

    # Base fields
    title = read_title(t)
    game  = read_game(t)
    gslug = slugify_game(game)

    entry_fee  = read_fee_amount(t)
    prize_pool = t.prize_pool  # Use the property which handles Phase 1 model fallback

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
    cap_total = first(
        getattr(t, "slot_size", None),
        getattr(t, "capacity", None),
        getattr(getattr(t, "settings", None), "capacity", None),
    )
    # Default to 0 if no capacity info available
    cap_total = cap_total or 0
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
    
    # Media data (prefer Phase 1 model)
    banner = None
    thumbnail = None
    rules_pdf = None
    
    # Check Phase 1 TournamentMedia model first
    try:
        if hasattr(t, 'media') and t.media:
            banner = getattr(t.media.banner, 'url', None) if t.media.banner else None
            thumbnail = getattr(t.media.thumbnail, 'url', None) if t.media.thumbnail else None
            rules_pdf = getattr(t.media.rules_pdf, 'url', None) if t.media.rules_pdf else None
    except Exception:
        pass
    
    # Fallback to legacy banner_url function
    if not banner:
        banner = banner_url(t)
    
    # Fallback to rules_pdf_of function
    if not rules_pdf:
        rules_pdf_url, rules_filename = rules_pdf_of(t)
        rules_pdf = rules_pdf_url

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

    # active tab sanitized
    active_tab = (request.GET.get("tab") or "overview").lower()
    if active_tab not in tabs:
        active_tab = "overview"

    # Related tournaments
    related = related_tournaments(t, limit=8)

    # PDF.js viewer config
    pdf_viewer = build_pdf_viewer_config(t, theme="auto")

    # -------- Team-awareness for CTA/visibility --------
    is_team = _is_team_event(t)
    team, membership = _user_team(request.user)
    user_is_captain = _is_captain(membership)
    team_registered = _team_already_registered(t, team) if team else False

    is_registered_user = False
    try:
        if getattr(request.user, "is_authenticated", False):
            is_registered_user = Registration.objects.filter(tournament=t, user=request.user).exists()
            if team and not is_registered_user:
                try:
                    is_registered_user = Registration.objects.filter(tournament=t, team=team).exists()
                except Exception:
                    pass
    except Exception:
        pass

    now = timezone.now()
    tournament_started = bool(starts_at and now >= starts_at)
    tournament_finished = bool(ends_at and now >= ends_at)
    can_view_sensitive = bool(is_registered_user and tournament_started)

    # -------- Prizes + DeltaCoin merged into one list [{place, cash, coin}] --------
    def _get_attr_chain(obj, names: List[str], default=None):
        for n in names:
            if hasattr(obj, n):
                return getattr(obj, n)
        return default

    # Gather coin rewards (by place)
    coin_by_place: Dict[int, Any] = {}
    if hasattr(t, "settings"):
        for i in range(1, 9):
            coin = _get_attr_chain(t.settings, [f"coin_{i}", f"delta_coin_{i}", f"reward_coin_{i}"], None)
            if coin is not None:
                coin_by_place[i] = coin

    # Build merged prizes list 1..8 (keep rows that have either cash or coin)
    prizes: List[Dict[str, Any]] = []
    for i in range(1, 9):
        cash = _get_attr_chain(t, [f"prize_{i}_bdt", f"prize_{i}_amount", f"prize_{i}"], None)
        if cash is None and hasattr(t, "settings"):
            cash = _get_attr_chain(t.settings, [f"prize_{i}_bdt", f"prize_{i}_amount", f"prize_{i}"], None)
        coin = coin_by_place.get(i)
        if cash is not None or coin is not None:
            # Format prize data to match template expectations
            medal_map = {1: "🥇", 2: "🥈", 3: "🥉"}
            label_map = {1: "1st Place", 2: "2nd Place", 3: "3rd Place", 4: "4th Place", 5: "5th Place", 6: "6th Place", 7: "7th Place", 8: "8th Place"}
            
            prizes.append({
                "place": i, 
                "cash": cash, 
                "coin": coin,
                "medal": medal_map.get(i, f"#{i}"),
                "label": label_map.get(i, f"{i}th Place"),
                "amount": cash if cash else 0
            })

    prize_pool_fmt = fmt_money(prize_pool)

    # Build context that matches template expectations
    context = {
        'tournament': t,
        'total_prize_pool': prize_pool,
        'stats': {
            'total_participants': reg_count,
            'total_matches': 0,  # Placeholder
        },
        'capacity_info': {
            'total_slots': cap_total,
            'filled_slots': reg_count,
            'available_slots': max(0, cap_total - reg_count) if cap_total else 0,
            'fill_percentage': int((reg_count / cap_total) * 100) if cap_total and cap_total > 0 else 0,
            'is_full': cap_total and reg_count >= cap_total,
        },
        'media_data': {
            'banner': banner,
            'thumbnail': thumbnail or banner,  # Use banner as thumbnail fallback
            'rules_pdf': rules_pdf,
        },
        'can_register': cta.get('kind') in ('register', 'pay', 'checkin'),
        'register_url': reg_url,
        'user_registration': user_reg(request.user, t),
        'timeline_events': [],  # Placeholder
        'participants': participants,
        'prize_distribution': prizes,
        'rules_data': {
            'general': rules_text,
            'format': None,
            'conduct': extra_rules,
            'scoring': None,
        },
        'organizer_info': {
            'name': 'DeltaCrown',
            'email': 'support@deltacrown.com',
        },
        # Add schedule object for template compatibility
        'schedule': type('Schedule', (), {
            'reg_close_at': reg_close,
        })(),
        # Add missing context variables
        'user': request.user,
        'registration_open': is_registration_open(t),
        # Keep existing context for compatibility
        't': t,
        'title': title,
        'game': game,
        'gslug': gslug,
        'entry_fee': entry_fee,
        'prize_pool': prize_pool,
        'starts_at': starts_at,
        'ends_at': ends_at,
        'reg_open': reg_open,
        'reg_close': reg_close,
        'chk_open': chk_open,
        'chk_close': chk_close,
        'format_type': format_type,
        'best_of': best_of,
        'min_team': min_team,
        'max_team': max_team,
        'platform': platform,
        'region': region,
        'check_in_required': check_in_required,
        'cap_total': cap_total,
        'reg_count': reg_count,
        'short_desc': short_desc,
        'desc_html': desc_html,
        'rules_text': rules_text,
        'extra_rules': extra_rules,
        'rules_url': rules_url,
        'rules_filename': rules_filename,
        'coin_policy': coin_policy,
        'live_info': live_info,
        'bracket_url': bracket_url,
        'standings': standings,
        'state': state,
        'banner': banner,
        'reg_url': reg_url,
        'cta': cta,
        'hero': hero_meta_for(t),
        'tabs': tabs,
        'active_tab': active_tab,
        'related': related,
        'pdf_viewer': pdf_viewer,
        'is_team': _is_team_event(t),
        'team': team,
        'membership': membership,
        'user_is_captain': _is_captain(membership),
        'team_registered': _team_already_registered(t, team) if team else False,
        'is_registered_user': is_registered_user,
        'tournament_started': tournament_started,
        'tournament_finished': tournament_finished,
        'can_view_sensitive': can_view_sensitive,
        'prizes': prizes,
        'prize_pool_fmt': prize_pool_fmt,
    }
    
    return render(request, "tournaments/tournament_detail.html", context)


class WarRoomView(TemplateView):
    template_name = "tournaments/war-room.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = kwargs.get('slug')
        
        if slug:
            # Tournament-specific war room
            tournament = get_object_or_404(Tournament, slug=slug)
            
            # Check if user is registered (either solo or as team member)
            try:
                # First try to find team registration where user is a team member
                registration = Registration.objects.filter(
                    tournament=tournament,
                    team__memberships__profile__user=self.request.user,
                    team__memberships__status='ACTIVE'
                ).select_related('team').first()
                
                if registration:
                    user_team = registration.team
                    can_checkin = True  # TODO: Add proper checkin logic
                else:
                    # Try solo registration
                    registration = Registration.objects.get(
                        tournament=tournament,
                        user__user=self.request.user
                    )
                    user_team = None  # Solo registration
                    can_checkin = False  # Solo players don't check in
            except Registration.DoesNotExist:
                user_team = None
                can_checkin = False
            
            # Get team stats if registered
            if user_team:
                # Mock stats for now - TODO: Calculate real stats
                stats = {
                    'rank': 1,
                    'points': 0,
                    'win_rate': 0,
                    'matches_played': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_streak': 0,
                    'avg_score': 0
                }
            else:
                stats = {
                    'rank': 'N/A',
                    'points': 0,
                    'win_rate': 0,
                    'matches_played': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_streak': 0,
                    'avg_score': 0
                }
            
            context['ctx'] = {
                'tournament': tournament,
                'team': user_team,
                'can_checkin': can_checkin,
                'stats': stats,
                'upcoming_matches_count': 0,  # TODO: Calculate real count
                'unread_news_count': 0
            }
        else:
            # General war room (fallback)
            mock_team = type('Team', (), {
                'checked_in': False,
                'logo': None,
                'name': 'No Active Team',
                'id': 0,
                'players': []
            })()
            
            context['ctx'] = {
                'tournament': type('Tournament', (), {
                    'name': 'War Room',
                    'slug': 'war-room',
                    'game_name': 'Strategy Center',
                    'format': 'Command Center',
                    'icon': None,
                    'status': 'ACTIVE'
                })(),
                'team': mock_team,
                'can_checkin': False,
                'stats': {
                    'rank': 'N/A',
                    'points': 0,
                    'win_rate': 0,
                    'matches_played': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_streak': 0,
                    'avg_score': 0
                },
                'upcoming_matches_count': 0,
                'unread_news_count': 0
            }
        
        context['page_title'] = f'War Room - {context["ctx"]["tournament"].name}'
        return context
