# apps/teams/views/public.py
from __future__ import annotations
from uuid import uuid4
from typing import Dict, List, Optional, Tuple

from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q, Count, F, Value, IntegerField, Sum, Avg
from django.db.models.functions import Now, Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from urllib.parse import urlencode

from ..models import Team, TeamMembership, TeamInvite
from ..models.ranking_settings import TeamRankingSettings
from ..forms import (
    TeamCreationForm, TeamEditForm, TeamInviteForm, 
    TeamMemberManagementForm, TeamSettingsForm
)
from .utils import (
    _ensure_profile, _get_profile, _is_captain, _get_game_display_name,
    _calculate_team_rank_score, _format_team_data
)
from ..permissions import TeamPermissions


# -------------------------
# Game configuration using centralized assets system
# -------------------------
from apps.common.game_assets import GAMES as GAME_ASSETS

# Generate games list from centralized configuration
GAMES = [
    (code.lower(), data['display_name'])
    for code, data in GAME_ASSETS.items()
]

SORT_OPTIONS = [
    {"value": "powerrank", "label": "Power Rank"},
    {"value": "points", "label": "Points"},
    {"value": "recent", "label": "Recent Activity"},
    {"value": "members", "label": "Roster Size"},
    {"value": "az", "label": "Team Name A-Z"},
    {"value": "game", "label": "Game A-Z"},
    {"value": "newest", "label": "Newest Teams"},
]

ORDER_OPTIONS = [
    {"value": "desc", "label": "High to Low"},
    {"value": "asc", "label": "Low to High"},
]

DEFAULT_SORT_ORDERS = {
    "powerrank": "desc",
    "recent": "desc",
    "members": "desc",
    "points": "desc",
    "az": "asc",
    "game": "asc",
    "newest": "desc",
}

TRUE_VALUES = {"1", "true", "yes", "on"}


def _build_game_options() -> List[Tuple[str, str]]:
    """Combine configured games with any additional titles stored in the database."""
    options: List[Tuple[str, str]] = list(GAMES)
    known_codes = {code for code, _ in options}
    extra_games = (
        Team.objects.filter(is_active=True, is_public=True)
        .exclude(game__isnull=True)
        .exclude(game__exact="")
        .values_list("game", flat=True)
        .distinct()
    )
    for code in extra_games:
        normalized = (code or "").strip()
        if not normalized:
            continue
        if normalized in known_codes:
            continue
        known_codes.add(normalized)
        options.append((normalized, normalized.replace("_", " ").title()))
    return options


# Removed _get_game_display_name - now imported from utils


def _available_region_options() -> List[Dict[str, str]]:
    """Return formatted region options for filter controls."""
    regions = (
        Team.objects.filter(is_active=True, is_public=True)
        .exclude(region__isnull=True)
        .exclude(region__exact="")
        .values_list("region", flat=True)
    )
    seen = set()
    options: List[Dict[str, str]] = []
    for region in regions:
        label = (region or "").strip()
        if not label:
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        display = label if label.isupper() else label.title()
        options.append({"value": label, "label": display})
    options.sort(key=lambda item: item["label"])
    return options


def _parse_bool_param(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in TRUE_VALUES


def _parse_int_param(value: Optional[str], minimum: Optional[int] = None) -> Optional[int]:
    if value is None:
        return None
    raw = str(value).strip()
    if raw == "":
        return None
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return None
    if minimum is not None and parsed < minimum:
        return None
    return parsed


def _build_query_string(request, *, remove=(), **updates) -> str:
    """Return the current query string updated with supplied values."""
    params = request.GET.copy()
    for key in remove:
        params.pop(key, None)
    for key, value in updates.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()


def _extract_filter_state(request) -> Dict[str, Optional[str]]:
    sort = (request.GET.get("sort") or "powerrank").strip().lower()
    valid_sorts = {option["value"] for option in SORT_OPTIONS}
    if sort not in valid_sorts:
        sort = "powerrank"

    order_param = (request.GET.get("order") or "").strip().lower()
    if order_param in {"asc", "desc"}:
        order = order_param
    elif order_param == "-":
        order = "desc"
    elif order_param == "+":
        order = "asc"
    else:
        order = ""

    if not order:
        order = DEFAULT_SORT_ORDERS.get(sort, "asc")

    filters: Dict[str, Optional[str]] = {
        "q": (request.GET.get("q") or "").strip(),
        "game": (request.GET.get("game") or "").strip(),
        "region": (request.GET.get("region") or "").strip(),
        "sort": sort,
        "order": order,
        "min_members": _parse_int_param(request.GET.get("min_members"), 0),
        "max_members": _parse_int_param(request.GET.get("max_members"), 0),
        "founded_year_from": _parse_int_param(request.GET.get("founded_year_from"), 1900),
        "founded_year_to": _parse_int_param(request.GET.get("founded_year_to"), 1900),
        "recruiting": False,
        "verified": _parse_bool_param(request.GET.get("verified")),
        "featured": _parse_bool_param(request.GET.get("featured")),
    }

    filters["recruiting"] = _parse_bool_param(request.GET.get("recruiting")) or _parse_bool_param(request.GET.get("open"))

    fy_from = filters["founded_year_from"]
    fy_to = filters["founded_year_to"]
    if fy_from and fy_to and fy_to < fy_from:
        filters["founded_year_to"] = None

    return filters


def _build_active_filters(request, filters: Dict[str, Optional[str]], game_options: List[Tuple[str, str]], region_options: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Generate active filter chips with removal links."""
    active: List[Dict[str, str]] = []
    querydict = request.GET.copy()
    label_by_game = {code: label for code, label in game_options}
    label_by_region = {item["value"]: item["label"] for item in region_options}

    def _build_url(*names: str) -> str:
        new_qd = querydict.copy()
        for name in names:
            new_qd.pop(name, None)
        new_qd.pop("page", None)
        encoded = new_qd.urlencode()
        return f"{request.path}?{encoded}" if encoded else request.path

    if filters.get("q"):
        active.append({"label": f'Search: "{filters["q"]}"', "url": _build_url("q")})
    if filters.get("game"):
        label = label_by_game.get(filters["game"], filters["game"].title())
        active.append({"label": f"Game: {label}", "url": _build_url("game")})
    if filters.get("region"):
        label = label_by_region.get(filters["region"], filters["region"].title())
        active.append({"label": f"Region: {label}", "url": _build_url("region")})
    if filters.get("min_members") is not None:
        active.append({"label": f"Min members: {filters['min_members']}", "url": _build_url("min_members")})
    if filters.get("max_members") is not None:
        active.append({"label": f"Max members: {filters['max_members']}", "url": _build_url("max_members")})
    if filters.get("founded_year_from") is not None:
        active.append({"label": f"Founded >= {filters['founded_year_from']}", "url": _build_url("founded_year_from")})
    if filters.get("founded_year_to") is not None:
        active.append({"label": f"Founded <= {filters['founded_year_to']}", "url": _build_url("founded_year_to")})
    if filters.get("recruiting"):
        active.append({"label": "Recruiting teams", "url": _build_url("recruiting", "open")})
    if filters.get("verified"):
        active.append({"label": "Verified teams", "url": _build_url("verified")})
    if filters.get("featured"):
        active.append({"label": "Featured teams", "url": _build_url("featured")})
    if filters.get("sort") and filters["sort"] != "powerrank":
        sort_label = next((opt["label"] for opt in SORT_OPTIONS if opt["value"] == filters["sort"]), filters["sort"].title())
        active.append({"label": f"Sort: {sort_label}", "url": _build_url("sort")})
    if filters.get("order"):
        order_label = "Ascending" if filters["order"] == "asc" else "Descending"
        active.append({"label": f"Order: {order_label}", "url": _build_url("order")})

    return active


def _build_pagination_window(page_obj, window: int = 2) -> List[Optional[int]]:
    total_pages = page_obj.paginator.num_pages
    if total_pages <= 1:
        return [page_obj.number]

    start = max(page_obj.number - window, 1)
    end = min(page_obj.number + window, total_pages)

    pages: List[Optional[int]] = []
    if start > 1:
        pages.append(1)
        if start > 2:
            pages.append(None)
    pages.extend(range(start, end + 1))
    if end < total_pages:
        if end < total_pages - 1:
            pages.append(None)
        pages.append(total_pages)
    return pages



# -------------------------
# Helper functions moved to utils.py for better modularization


def _user_teams_by_game(user) -> Dict[str, Optional[Team]]:
    """
    Map of game_code -> the single team the user belongs to in that game.
    Safe even if 'game' field is missing (returns empty/None entries).
    """
    out = {code: None for code, _ in GAMES}
    if not user or not getattr(user, "is_authenticated", False):
        return out
    prof = _ensure_profile(user)
    # membership model: TeamMembership(profile=<UserProfile>, team=<Team>)
    mems = TeamMembership.objects.select_related("team").filter(profile=prof)
    for m in mems:
        game_code = getattr(m.team, "game", None)
        if game_code in out:
            out[game_code] = m.team
    return out


def _base_team_queryset():
    """Common queryset with configurable tournament-based ranking annotations."""
    from django.db.models import Case, When, IntegerField as DjangoIntegerField

    ranking_settings = TeamRankingSettings.get_active_settings()

    qs = (
        Team.objects.filter(is_active=True, is_public=True)
        .select_related("captain__user")
    )

    qs = qs.annotate(
        memberships_count=Coalesce(
            Count(
                "memberships",
                filter=Q(memberships__status=TeamMembership.Status.ACTIVE),
                distinct=True,
            ),
            Value(0),
        ),
        achievements_count=Coalesce(
            Count("achievements", distinct=True),
            Value(0),
        ),
        tournament_wins=Coalesce(
            Count(
                "achievements",
                filter=Q(achievements__placement="WINNER"),
                distinct=True,
            ),
            Value(0),
        ),
        runner_up_count=Coalesce(
            Count(
                "achievements",
                filter=Q(achievements__placement="RUNNER_UP"),
                distinct=True,
            ),
            Value(0),
        ),
        top4_count=Coalesce(
            Count(
                "achievements",
                filter=Q(achievements__placement="TOP4"),
                distinct=True,
            ),
            Value(0),
        ),
        top8_count=Coalesce(
            Count(
                "achievements",
                filter=Q(achievements__placement="TOP8"),
                distinct=True,
            ),
            Value(0),
        ),
        calculated_ranking_score=Coalesce(
            Sum(
                Case(
                    When(
                        achievements__placement="WINNER",
                        then=Value(ranking_settings.tournament_victory_points),
                    ),
                    When(
                        achievements__placement="RUNNER_UP",
                        then=Value(ranking_settings.runner_up_points),
                    ),
                    When(
                        achievements__placement="TOP4",
                        then=Value(ranking_settings.top4_finish_points),
                    ),
                    When(
                        achievements__placement="TOP8",
                        then=Value(ranking_settings.top8_finish_points),
                    ),
                    When(
                        achievements__placement="PARTICIPANT",
                        then=Value(ranking_settings.participation_points),
                    ),
                    default=Value(0),
                    output_field=DjangoIntegerField(),
                )
            ),
            Value(0),
        ),
        base_points=Coalesce(F("total_points"), Value(0)) + Coalesce(F("adjust_points"), Value(0)),
    )

    recent_fields = [
        F(field)
        for field in ("updated_at", "edited_at", "created_at")
        if hasattr(Team, field)
    ]
    if recent_fields:
        qs = qs.annotate(recent_activity_at=Coalesce(*recent_fields, Now()))
    else:
        qs = qs.annotate(recent_activity_at=Now())

    qs = qs.annotate(
        trophies=Value(0, output_field=DjangoIntegerField()),
        tournaments_played=Value(0, output_field=DjangoIntegerField()),
        wins=Value(0, output_field=DjangoIntegerField()),
        losses=Value(0, output_field=DjangoIntegerField()),
    )

    qs.ranking_settings = ranking_settings
    return qs.distinct()
def _apply_filters(qs, filters):
    search_term = filters.get("q")
    if search_term:
        lookup = Q()
        for field in ("name", "tag", "slug"):
            if hasattr(Team, field):
                lookup |= Q(**{f"{field}__icontains": search_term})
        if hasattr(Team, "region"):
            lookup |= Q(region__icontains=search_term)
        if lookup:
            qs = qs.filter(lookup)

    game_value = (filters.get("game") or "").strip()
    if game_value:
        game_filters = Q()
        if hasattr(Team, "game"):
            game_filters |= Q(game__iexact=game_value)
        if hasattr(Team, "primary_game"):
            game_filters |= Q(primary_game__iexact=game_value)
        if game_filters:
            qs = qs.filter(game_filters)

    region_value = (filters.get("region") or "").strip()
    if region_value:
        qs = qs.filter(region__iexact=region_value)

    min_members = filters.get("min_members")
    if min_members is not None:
        qs = qs.filter(memberships_count__gte=min_members)

    max_members = filters.get("max_members")
    if max_members is not None:
        qs = qs.filter(memberships_count__lte=max_members)

    founded_from = filters.get("founded_year_from")
    if founded_from is not None and hasattr(Team, "founded_year"):
        qs = qs.filter(founded_year__gte=founded_from)

    founded_to = filters.get("founded_year_to")
    if founded_to is not None and hasattr(Team, "founded_year"):
        qs = qs.filter(founded_year__lte=founded_to)

    if filters.get("recruiting"):
        qs = qs.filter(allow_join_requests=True)

    if filters.get("verified"):
        qs = qs.filter(is_verified=True)

    if filters.get("featured"):
        qs = qs.filter(is_featured=True)

    return qs
def _apply_sort(qs, sort_key, order):
    sort_key = sort_key or "powerrank"
    order_value = order if order in ("asc", "desc") else ""

    if sort_key == "recent":
        base_order = ["-recent_activity_at", "name"]
        return qs.order_by(*_apply_order_direction(base_order, order_value, default_desc=True))
    if sort_key == "members":
        base_order = ["-memberships_count", "name"]
        return qs.order_by(*_apply_order_direction(base_order, order_value, default_desc=True))
    if sort_key == "az":
        base_order = ["name"]
        return qs.order_by(*_apply_order_direction(base_order, order_value, default_desc=False))
    if sort_key == "game":
        base_order = ["game", "primary_game", "name"]
        return qs.order_by(*_apply_order_direction(base_order, order_value, default_desc=False))
    if sort_key == "points":
        base_order = ["-base_points", "-total_points", "name"]
        return qs.order_by(*_apply_order_direction(base_order, order_value, default_desc=True))
    if sort_key == "newest":
        base_order = ["-created_at", "name"]
        return qs.order_by(*_apply_order_direction(base_order, order_value, default_desc=True))

    base_order = [
        "-calculated_ranking_score",
        "-base_points",
        "-tournament_wins",
        "-runner_up_count",
        "-top4_count",
        "-top8_count",
        "-achievements_count",
        "-memberships_count",
        "-recent_activity_at",
        "name",
    ]
    return qs.order_by(*_apply_order_direction(base_order, order_value, default_desc=True))


def _apply_order_direction(base_order, requested_order, default_desc=True):
    if requested_order not in ("asc", "desc"):
        return base_order

    should_flip = (requested_order == "asc" and default_desc) or (requested_order == "desc" and not default_desc)
    if not should_flip:
        return base_order

    toggled = []
    for field in base_order:
        if field.startswith("-"):
            toggled.append(field[1:])
        else:
            toggled.append(f"-{field}")
    return toggled
def team_hub(request):
    """
    Team Hub - Main landing page with hero, my teams, invitations, top teams preview
    """
    # Get user's teams if authenticated
    my_teams = []
    pending_invites = []
    if request.user.is_authenticated:
        profile = _ensure_profile(request.user)
        my_teams_data = _user_teams_by_game(request.user)
        my_teams = [team for team in my_teams_data.values() if team]
        
        # Get pending invitations
        pending_invites = TeamInvite.objects.filter(
            invited_user=profile, 
            status="PENDING"
        ).select_related("team", "inviter__user")[:5]

    # Get top 5 teams by ranking
    top_teams_qs = _base_team_queryset()
    top_teams = _apply_sort(top_teams_qs, 'powerrank', 'desc')[:5]
    
    # Get recent teams (newest 5)
    recent_teams = Team.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    # Statistics for hero section
    total_teams = Team.objects.filter(is_active=True).count()
    active_tournaments = 0  # Can be connected to tournaments app later
    try:
        total_players = TeamMembership.objects.filter(status='ACTIVE').count()
    except:
        total_players = TeamMembership.objects.count()
    
    # Game statistics
    game_stats = []
    for game_code, game_name in GAMES:
        team_count = Team.objects.filter(game=game_code, is_active=True).count()
        if team_count > 0:
            game_stats.append({
                'code': game_code,
                'name': game_name,
                'team_count': team_count
            })
    
    ctx = {
        'my_teams': my_teams,
        'pending_invites': pending_invites,
        'top_teams': top_teams,
        'recent_teams': recent_teams,
        'total_teams': total_teams,
        'active_tournaments': active_tournaments,
        'total_players': total_players,
        'game_stats': game_stats,
        'games': GAMES,
    }
    return render(request, "teams/hub.html", ctx)


# -------------------------
# Team List (Detailed rankings)
# -------------------------

def team_list(request):
    """Render the professional teams listing with legacy layout."""
    filters_state = _extract_filter_state(request)
    queryset = _base_team_queryset().prefetch_related("memberships")

    base_team_qs = Team.objects.filter(is_active=True, is_public=True)
    total_teams = base_team_qs.count()
    recruiting_total = base_team_qs.filter(allow_join_requests=True).count()

    filtered_qs = _apply_filters(queryset, filters_state)
    sorted_qs = _apply_sort(filtered_qs, filters_state["sort"], filters_state["order"])

    paginator = Paginator(sorted_qs, 20)  # Show 20 teams per page for better professional experience
    page_number = request.GET.get("page") or 1
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    teams_on_page = list(page_obj.object_list)
    start_rank = (page_obj.number - 1) * paginator.per_page
    
    # Get user's team memberships for button logic
    user_team_ids = set()
    if request.user.is_authenticated:
        profile = _ensure_profile(request.user)
        user_team_ids = set(
            TeamMembership.objects.filter(
                profile=profile,
                status=TeamMembership.Status.ACTIVE
            ).values_list('team_id', flat=True)
        )
    
    for index, team in enumerate(teams_on_page, start=1):
        # Ensure all team attributes are properly set with safe defaults
        team.total_points = getattr(team, 'total_points', None) or 0
        team.adjust_points = getattr(team, 'adjust_points', None) or 0
        team.tournament_wins = getattr(team, 'tournament_wins', None) or 0
        team.region = getattr(team, 'region', None) or "Global"
        team.name = getattr(team, 'name', None) or f"Team {team.id}"
        team.tag = getattr(team, 'tag', None) or ""
        team.game = getattr(team, 'game', None) or ""
        
        # Calculate proper ranking position
        team.rank_position = start_rank + index
        team.recruiting = bool(getattr(team, "allow_join_requests", False) and getattr(team, "is_active", True))
        team.power_rank = _calculate_team_power_rank(team)
        
        # Ensure members count is available
        if not hasattr(team, 'members_count') or team.members_count is None:
            team.members_count = team.memberships.count() if hasattr(team, 'memberships') else 0
        
        # Ensure calculated ranking score exists
        if not hasattr(team, 'calculated_ranking_score') or team.calculated_ranking_score is None:
            team.calculated_ranking_score = team.power_rank
        
        # Add user membership flag for button logic
        team.user_is_member = team.id in user_team_ids
        
        # Determine if Join button should be shown
        team.show_join_button = (
            not team.user_is_member and 
            (getattr(team, 'is_recruiting', False) or getattr(team, 'allow_join_requests', False))
        )

    game_options = _build_game_options()
    games = [code for code, _ in game_options]

    sort_links = {}
    current_sort = filters_state["sort"]
    current_order = filters_state["order"]
    for option in SORT_OPTIONS:
        sort_key = option["value"]
        if sort_key not in DEFAULT_SORT_ORDERS:
            continue
        if current_sort == sort_key:
            next_order = "asc" if current_order == "desc" else "desc"
        else:
            next_order = DEFAULT_SORT_ORDERS.get(sort_key, "asc")
        query_string = _build_query_string(request, remove=("page",), sort=sort_key, order=next_order)
        sort_links[sort_key] = f"?{query_string}" if query_string else "?"

    pagination_links = {"previous": None, "next": None}
    if page_obj.has_previous():
        prev_query = _build_query_string(request, remove=("page",), page=page_obj.previous_page_number())
        pagination_links["previous"] = f"?{prev_query}" if prev_query else f"?page={page_obj.previous_page_number()}"
    if page_obj.has_next():
        next_query = _build_query_string(request, remove=("page",), page=page_obj.next_page_number())
        pagination_links["next"] = f"?{next_query}" if next_query else f"?page={page_obj.next_page_number()}"

    game_urls = {}
    all_games_query = _build_query_string(request, remove=("page",), game=None)
    game_urls[""] = f"?{all_games_query}" if all_games_query else "?"
    for code, _ in game_options:
        game_query = _build_query_string(request, remove=("page",), game=code)
        game_urls[code] = f"?{game_query}" if game_query else "?"

    # Add real game counts with Counter-Strike deduplication
    games_list_with_urls = []
    processed_games = set()
    
    for code, label in game_options:
        # Handle Counter-Strike consolidation
        if code in ['csgo', 'cs2']:
            if 'counter-strike' not in processed_games:
                # Combine counts for both csgo and cs2
                cs_count = (base_team_qs.filter(game='csgo').count() + 
                           base_team_qs.filter(game='cs2').count())
                games_list_with_urls.append({
                    "code": "cs2",  # Use cs2 as the primary code
                    "name": "Counter-Strike", 
                    "url": game_urls.get('cs2', game_urls.get('csgo', '')),
                    "team_count": cs_count
                })
                processed_games.add('counter-strike')
        elif code not in ['csgo']:  # Skip csgo since we handled it above
            team_count = base_team_qs.filter(game=code).count()
            games_list_with_urls.append({
                "code": code, 
                "name": label, 
                "url": game_urls[code],
                "team_count": team_count
            })

    context = {
        "teams": teams_on_page,
        "object_list": teams_on_page,
        "page_obj": page_obj,
        "paginator": paginator,
        "query": filters_state["q"],
        "active_game": filters_state["game"],
        "sort": filters_state["sort"],
        "order": filters_state["order"],
        "games": games,
        "games_list": games_list_with_urls,
        "total_teams": total_teams,
        "active_teams": total_teams,
        "recruiting_teams": recruiting_total,
        "all_games_url": game_urls[""],
        "sort_links": sort_links,
        "pagination_links": pagination_links,
        "game_urls": game_urls,
    }
    
    # Handle AJAX requests for infinite scroll/load more functionality
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.headers.get('Accept') == 'application/json':
            # Return JSON data for load more functionality
            teams_data = []
            for team in teams_on_page:
                team_data = {
                    'id': team.id,
                    'name': team.name or 'Unknown Team',
                    'tag': getattr(team, 'tag', '') or '',
                    'logo': team.logo.url if team.logo else None,
                    'game': getattr(team, 'game', '') or '',
                    'game_display': _get_game_display_name(getattr(team, 'game', '')) or 'Unknown Game',
                    'members_count': getattr(team, 'members_count', 0) or 0,
                    'points': getattr(team, 'total_points', 0) or 0,
                    'wins': getattr(team, 'tournament_wins', 0) or 0,
                    'region': getattr(team, 'region', 'Global') or 'Global',
                    'rank_position': getattr(team, 'rank_position', 0) or 0,
                    'power_rank': getattr(team, 'power_rank', 0) or 0,
                    'url': team.get_absolute_url() if hasattr(team, 'get_absolute_url') else '#',
                    'allow_join': getattr(team, 'show_join_button', False),
                    'user_is_member': getattr(team, 'user_is_member', False),
                    'join_url': f"/teams/{team.slug}/join/" if hasattr(team, 'slug') and team.slug else '#'
                }
                teams_data.append(team_data)
            
            return JsonResponse({
                'teams': teams_data,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
            })
        else:
            # Return HTML for search/filter updates
            return render(request, "teams/list.html", context)
    
    return render(request, "teams/list.html", context)

def _calculate_team_power_rank(team):
    """
    Enhanced team power ranking algorithm based on multiple real data factors:
    - Tournament wins and performance (weighted heavily)
    - Points/Adjustments from competitions
    - Team composition and member quality
    - Recent activity and engagement
    - Verified status and reputation
    - Regional competitiveness
    """
    base_score = 1000  # Starting baseline score
    
    # 1. COMPETITIVE PERFORMANCE (40% weight - most important)
    competitive_score = 0
    
    # Tournament wins (high impact)
    tournament_wins = getattr(team, 'tournament_wins', 0)
    wins_bonus = tournament_wins * 150  # 150 points per tournament win
    
    # Total points from competitions
    total_points = getattr(team, 'total_points', 0)
    adjust_points = getattr(team, 'adjust_points', 0)
    points_score = (total_points + adjust_points) * 2  # 2 points per competition point
    
    # Match history performance (if available)
    match_performance = 0
    try:
        # Try to get recent match statistics
        Match = apps.get_model("tournaments", "Match")
        recent_matches = Match.objects.filter(
            Q(team_a=team) | Q(team_b=team),
            created_at__gte=timezone.now() - timezone.timedelta(days=90)
        ).count()
        match_performance = min(recent_matches * 20, 300)  # Active competition bonus
    except:
        pass  # Tournament app might not be available
    
    competitive_score = wins_bonus + points_score + match_performance
    
    # 2. TEAM COMPOSITION (25% weight)
    composition_score = 0
    
    # Member count (optimal team size varies by game)
    member_count = getattr(team, 'members_count', 0)
    if member_count == 0:
        member_count = team.memberships.count() if hasattr(team, 'memberships') else 0
    
    # Optimal team sizes by game
    optimal_sizes = {
        'valorant': 5, 'cs2': 5, 'csgo': 5,
        'efootball': 11, 'fc26': 11,
        'mlbb': 5, 'pubg': 4, 'freefire': 4
    }
    
    game = getattr(team, 'game', '')
    optimal_size = optimal_sizes.get(game, 5)
    
    # Calculate member score based on proximity to optimal size
    if member_count <= optimal_size:
        member_score = (member_count / optimal_size) * 300
    else:
        # Penalize oversized teams slightly
        excess = member_count - optimal_size
        member_score = 300 - (excess * 10)
    
    composition_score = max(member_score, 0)
    
    # 3. ACTIVITY AND ENGAGEMENT (20% weight)
    engagement_score = 0
    
    # Recent activity bonus
    activity_bonus = 0
    if hasattr(team, 'updated_at') and team.updated_at:
        days_since_update = (timezone.now() - team.updated_at).days
        if days_since_update <= 3:
            activity_bonus = 250
        elif days_since_update <= 7:
            activity_bonus = 200
        elif days_since_update <= 14:
            activity_bonus = 150
        elif days_since_update <= 30:
            activity_bonus = 100
        elif days_since_update <= 60:
            activity_bonus = 50
    
    # Social engagement (followers, posts, interactions)
    social_score = 0
    if hasattr(team, 'followers_count'):
        social_score = min(team.followers_count * 3, 250)
    
    # Team posts and community engagement
    posts_score = 0
    try:
        TeamPost = apps.get_model("teams", "TeamPost")
        recent_posts = TeamPost.objects.filter(
            team=team,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        posts_score = min(recent_posts * 15, 150)
    except:
        pass
    
    engagement_score = activity_bonus + social_score + posts_score
    
    # 4. REPUTATION AND STATUS (10% weight)
    reputation_score = 0
    
    # Verified status
    verified_bonus = 400 if getattr(team, 'is_verified', False) else 0
    
    # Public visibility
    public_bonus = 100 if getattr(team, 'is_public', True) else 0
    
    # Regional competitiveness
    region_bonus = 0
    region = getattr(team, 'region', 'Global')
    competitive_regions = ['North America', 'Europe', 'Asia', 'South Korea']
    if region in competitive_regions:
        region_bonus = 50
    
    reputation_score = verified_bonus + public_bonus + region_bonus
    
    # 5. RECRUITMENT AND ACCESSIBILITY (5% weight)
    accessibility_score = 0
    
    # Open recruitment bonus (encourages community growth)
    recruiting_bonus = 75 if getattr(team, 'allow_join_requests', False) else 0
    
    # Active team bonus
    active_bonus = 50 if getattr(team, 'is_active', True) else -200
    
    accessibility_score = recruiting_bonus + active_bonus
    
    # FINAL CALCULATION
    # Weight the different components
    weighted_score = (
        base_score +
        (competitive_score * 0.40) +      # 40% competitive performance
        (composition_score * 0.25) +      # 25% team composition
        (engagement_score * 0.20) +       # 20% activity/engagement
        (reputation_score * 0.10) +       # 10% reputation
        (accessibility_score * 0.05)      # 5% accessibility
    )
    
    # Apply game-specific modifiers
    game_modifiers = {
        'valorant': 1.1,   # Highly competitive scene
        'cs2': 1.1,        # Highly competitive scene
        'efootball': 1.0,  # Standard
        'mlbb': 1.05,      # Growing competitive scene
        'pubg': 1.0,       # Standard
    }
    
    game_modifier = game_modifiers.get(game, 1.0)
    final_score = weighted_score * game_modifier
    
    # Ensure reasonable bounds (500-5000 range for active teams)
    return max(min(final_score, 5000), 500)


# -------------------------
# Team detail (public)
# -------------------------
def team_detail(request, slug: str):
    # Redirect to the new social team page
    from django.shortcuts import redirect
    return redirect('teams:teams_social:team_social_detail', team_slug=slug)
    
    # Original team detail code (kept for reference)
    team_qs = _base_team_queryset()
    team = team_qs.filter(slug=slug).first() or get_object_or_404(team_qs, slug=slug)

    # Roster (active-first ordering if fields exist)
    memberships = (
        team.memberships.select_related("profile__user")
        .all()
        .order_by("role", "joined_at")
    )
    roster = [m.profile for m in memberships if getattr(m, "status", "ACTIVE") == "ACTIVE"]

    # Upcoming and recent results (best effort)
    try:
        Match = apps.get_model("tournaments", "Match")
        now = timezone.now()
        upcoming = (
            Match.objects.filter(Q(team_a=team) | Q(team_b=team), start_at__gt=now)
            .order_by("start_at")[:5]
        )
        results = (
            Match.objects.filter(Q(team_a=team) | Q(team_b=team), state__in=["REPORTED", "VERIFIED"])
            .order_by("-created_at")[:5]
        )
    except Exception:
        upcoming, results = [], []

    # Role flags
    prof = _get_profile(request.user)
    is_captain = _is_captain(prof, team) if prof else False
    is_member = False
    if prof:
        is_member = TeamMembership.objects.filter(team=team, profile=prof).exists()

    # Join-guard: already in a team for this game?
    already_in_team_for_game = False
    game_code = getattr(team, "game", None)
    if prof and game_code:
        already_in_team_for_game = TeamMembership.objects.filter(
            profile=prof, team__game=game_code
        ).exists()

    ctx = {
        "team": team,
        "roster": roster,
        "roster_memberships": memberships,
        "upcoming": upcoming,
        "results": results,
        "is_captain": is_captain,
        "is_member": is_member,
        "already_in_team_for_game": already_in_team_for_game,
        "games": GAMES,  # for chips/UI if needed
    }
    return render(request, "teams/detail.html", ctx)


# -------------------------
# Create team (public, auth)
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def create_team_view(request):
    """Create a new team with the requesting user as captain."""
    profile = _ensure_profile(request.user)

    if request.method == "POST":
        form = TeamCreationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            selected_game = form.cleaned_data.get('game')
            
            # Guard: Check if user already has an ACTIVE team for this game
            existing_membership = TeamMembership.objects.filter(
                profile=profile,
                team__game=selected_game,
                status='ACTIVE'
            ).select_related('team').first()
            
            if existing_membership:
                messages.error(
                    request,
                    f"You are already a member of '{existing_membership.team.name}' ({selected_game.upper()}). "
                    f"You can only be in one team per game. Please leave that team first."
                )
                return redirect("teams:create")
            
            # Check if user has game ID for selected game
            game_id = profile.get_game_id(selected_game)
            
            if not game_id:
                # Store team data in session
                request.session['pending_team_data'] = {
                    'name': form.cleaned_data.get('name'),
                    'tag': form.cleaned_data.get('tag'),
                    'description': form.cleaned_data.get('description'),
                    'game': selected_game,
                    'region': form.cleaned_data.get('region'),
                    'twitter': form.cleaned_data.get('twitter'),
                    'instagram': form.cleaned_data.get('instagram'),
                    'discord': form.cleaned_data.get('discord'),
                    'youtube': form.cleaned_data.get('youtube'),
                    'twitch': form.cleaned_data.get('twitch'),
                    'linktree': form.cleaned_data.get('linktree'),
                }
                # Store files separately (can't serialize files in session)
                if form.cleaned_data.get('logo'):
                    request.session['pending_team_has_logo'] = True
                if form.cleaned_data.get('banner_image'):
                    request.session['pending_team_has_banner'] = True
                
                game_name = dict(Team._meta.get_field('game').choices).get(selected_game, selected_game.upper())
                messages.info(request, f"Before creating your team, please provide your game ID for {game_name}.")
                return redirect("teams:collect_game_id", game_code=selected_game)
            
            # Game ID exists, proceed with team creation
            team = form.save()
            messages.success(request, f"Team '{team.name}' created successfully!")
            return redirect("teams:detail", slug=team.slug)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill game from query string if provided
        initial = {}
        game = request.GET.get("game", "").strip()
        if game:
            initial["game"] = game
        form = TeamCreationForm(user=request.user, initial=initial)

    return render(request, "teams/create.html", {"form": form})


# -------------------------
# Manage team (captain only)
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def manage_team_view(request, slug: str):
    """Comprehensive team management view for team captains."""
    team = get_object_or_404(Team.objects.select_related("captain__user"), slug=slug)
    profile = _ensure_profile(request.user)
    
    # Get membership for permission checking
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_edit_team_profile(membership):
            messages.error(request, "You don't have permission to manage this team.")
            return redirect("teams:detail", slug=team.slug)
    except TeamMembership.DoesNotExist:
        messages.error(request, "You must be a team member to manage this team.")
        return redirect("teams:detail", slug=team.slug)

    # Handle form submissions
    if request.method == "POST":
        form_type = request.POST.get("form_type")
        
        if form_type == "edit_team":
            form = TeamEditForm(request.POST, request.FILES, instance=team, user=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Team information updated successfully!")
                return redirect("teams:manage", slug=team.slug)
            else:
                messages.error(request, "Please correct the errors in the team information form.")
                
        elif form_type == "invite_member":
            invite_form = TeamInviteForm(request.POST, team=team, sender=request.user)
            if invite_form.is_valid():
                invite_form.save()
                messages.success(request, f"Invitation sent successfully!")
                return redirect("teams:manage", slug=team.slug)
            else:
                messages.error(request, "Please correct the errors in the invitation form.")
                
        elif form_type == "manage_members":
            member_form = TeamMemberManagementForm(request.POST, team=team, user=request.user)
            if member_form.is_valid():
                member_form.save()
                messages.success(request, "Member management action completed successfully!")
                return redirect("teams:manage", slug=team.slug)
            else:
                messages.error(request, "Please correct the errors in the member management form.")
                
        elif form_type == "team_settings":
            settings_form = TeamSettingsForm(request.POST, instance=team, user=request.user)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "Team settings updated successfully!")
                return redirect("teams:manage", slug=team.slug)
            else:
                messages.error(request, "Please correct the errors in the settings form.")
    
    # Initialize forms for GET request
    edit_form = TeamEditForm(instance=team, user=request.user)
    invite_form = TeamInviteForm(team=team, sender=request.user)
    member_form = TeamMemberManagementForm(team=team, user=request.user)
    settings_form = TeamSettingsForm(instance=team, user=request.user)
    
    # Get team data
    pending_invites = team.invites.filter(status="PENDING").select_related("invited_user__user")
    members = team.memberships.filter(status="ACTIVE").select_related("user__user")
    
    context = {
        "team": team,
        "edit_form": edit_form,
        "invite_form": invite_form,
        "member_form": member_form,
        "settings_form": settings_form,
        "pending_invites": pending_invites,
        "members": members,
        # Permission flags for frontend
        "user_membership": membership,
        "can_assign_managers": TeamPermissions.can_assign_managers(membership),
        "can_assign_captain_title": TeamPermissions.can_assign_captain_title(membership),
        "can_assign_coach": TeamPermissions.can_assign_coach(membership),
        "can_change_player_role": TeamPermissions.can_change_player_role(membership),
        "can_manage_roster": TeamPermissions.can_manage_roster(membership),
        "is_owner": membership.role == TeamMembership.Role.OWNER,
        "is_manager": membership.role == TeamMembership.Role.MANAGER,
        # Roster limits (game-specific)
        "roster_limits": team.roster_limits,
        "max_roster_size": team.max_roster_size,
        "min_roster_size": team.min_roster_size,
        "current_roster_size": members.count(),
        "can_accept_members": team.can_accept_members,
    }

    return render(request, "teams/manage.html", context)


# -------------------------
# Invitations
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def invite_member_view(request, slug: str):
    """Send invitation to new team member."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check permission to manage roster
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_manage_roster(membership):
            messages.error(request, "You don't have permission to invite members.")
            return redirect("teams:detail", slug=team.slug)
    except TeamMembership.DoesNotExist:
        messages.error(request, "You must be a team member to invite others.")
        return redirect("teams:detail", slug=team.slug)

    if request.method == "POST":
        form = TeamInviteForm(request.POST, team=team, sender=request.user)
        if form.is_valid():
            invite = form.save()
            messages.success(request, f"Invitation sent to {invite.invited_user.user.username}!")
            return redirect("teams:detail", slug=team.slug)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TeamInviteForm(team=team, sender=request.user)

    return render(request, "teams/invite_member.html", {"team": team, "form": form})


@login_required
def my_invites(request):
    profile = _ensure_profile(request.user)
    invites = TeamInvite.objects.filter(
        invited_user=profile, status="PENDING"
    ).select_related("team", "inviter__user")
    return render(request, "teams/my_invites.html", {"invites": invites})


@login_required
def accept_invite_view(request, token: str):
    invite = get_object_or_404(TeamInvite, token=token)
    profile = _ensure_profile(request.user)

    if invite.invited_user_id != profile.id or invite.status != "PENDING":
        messages.error(request, "This invite cannot be accepted.")
        return redirect(reverse("teams:my_invites"))

    # If GET request, show the accept page with game ID check
    if request.method == "GET":
        # Check if user has game ID for this team's game
        game_code = getattr(invite.team, "game", None)
        has_game_id = True
        game_name = ""
        
        if game_code:
            game_choices = dict(Team._meta.get_field('game').choices)
            game_name = game_choices.get(game_code, game_code.upper())
            game_id = profile.get_game_id(game_code)
            has_game_id = bool(game_id)
        
        # Get inviter name
        inviter_name = "Team Captain"
        if invite.inviter:
            inviter_profile = _ensure_profile(invite.inviter)
            if inviter_profile:
                inviter_name = inviter_profile.display_name or invite.inviter.username
        
        context = {
            'invite': invite,
            'team': invite.team,
            'has_game_id': has_game_id,
            'game_name': game_name,
            'inviter_name': inviter_name,
        }
        
        return render(request, 'teams/accept_invite.html', context)
    
    # POST request - process the acceptance
    # One-team-per-game guard: block if user already in another team of this game
    game_code = getattr(invite.team, "game", None)
    if game_code and TeamMembership.objects.filter(profile=profile, team__game=game_code, status='ACTIVE').exists():
        messages.error(request, f"You already belong to a {game_code.title()} team.")
        return redirect(reverse("teams:my_invites"))

    TeamMembership.objects.get_or_create(
        team=invite.team,
        profile=profile,
        defaults={"role": getattr(TeamMembership.Role, "PLAYER", "PLAYER")},
    )
    invite.status = "ACCEPTED"
    invite.save(update_fields=["status"])
    messages.success(request, f"You joined {getattr(invite.team, 'tag', invite.team.name)}.")
    return redirect(reverse("teams:detail", kwargs={"slug": invite.team.slug}))


@login_required
def decline_invite_view(request, token: str):
    invite = get_object_or_404(TeamInvite, token=token)
    profile = _ensure_profile(request.user)

    if invite.invited_user_id != profile.id or invite.status != "PENDING":
        messages.error(request, "This invite cannot be declined.")
        return redirect(reverse("teams:my_invites"))

    invite.status = "DECLINED"
    invite.save(update_fields=["status"])
    messages.info(request, f"Invite from {getattr(invite.team, 'tag', invite.team.name)} declined.")
    return redirect(reverse("teams:my_invites"))


# -------------------------
# Join team (public, auth, guard one-team-per-game)
# -------------------------
@login_required
@require_http_methods(["POST", "GET"])
def join_team_view(request, slug: str):
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.content_type == 'application/json'

    # Guard: already member
    if TeamMembership.objects.filter(team=team, profile=profile, status='ACTIVE').exists():
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'You are already a member of this team.'})
        messages.info(request, "You are already a member of this team.")
        return redirect("teams:detail", slug=team.slug)

    # Guard: one-team-per-game (check for ACTIVE memberships only)
    game_code = getattr(team, "game", None)
    if game_code:
        existing_membership = TeamMembership.objects.filter(
            profile=profile,
            team__game=game_code,
            status='ACTIVE'
        ).first()
        
        if existing_membership:
            game_display = dict(Team._meta.get_field('game').choices).get(game_code, game_code.upper())
            error_msg = (
                f"You are already a member of '{existing_membership.team.name}' for {game_display}. "
                f"You can only be in one team per game. Please leave '{existing_membership.team.name}' "
                f"before joining another {game_display} team."
            )
            if is_ajax:
                return JsonResponse({
                    'success': False, 
                    'error': error_msg,
                    'code': 'ALREADY_IN_TEAM_FOR_GAME',
                    'existing_team': existing_membership.team.name,
                    'existing_team_slug': existing_membership.team.slug,
                    'game': game_code
                })
            messages.error(request, error_msg)
            return redirect("teams:detail", slug=team.slug)

    # Check if user has game ID for this team's game
    if game_code:
        game_id = profile.get_game_id(game_code)
        if not game_id:
            error_msg = f"Please set up your {game_code.upper()} game ID to join this team."
            if is_ajax:
                return JsonResponse({
                    'success': False, 
                    'error': error_msg, 
                    'needs_game_id': True,
                    'game_code': game_code
                })
            # Store pending join request for non-AJAX
            request.session['pending_join_team'] = team.slug
            game_name = dict(Team._meta.get_field('game').choices).get(game_code, game_code.upper())
            messages.info(request, f"Before joining this team, please provide your game ID for {game_name}.")
            return redirect("teams:collect_game_id", game_code=game_code)

    # Optional: only allow if team is open (if such a field exists)
    if hasattr(team, "is_open") and not getattr(team, "is_open"):
        error_msg = "This team is not open to join directly. Ask for an invite."
        if is_ajax:
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect("teams:detail", slug=team.slug)

    TeamMembership.objects.get_or_create(
        team=team,
        profile=profile,
        defaults={"role": getattr(TeamMembership.Role, "PLAYER", "PLAYER")},
    )
    
    # Clear pending join from session if exists
    if 'pending_join_team' in request.session:
        del request.session['pending_join_team']
    
    success_msg = f"Successfully joined {team.name}!"
    if is_ajax:
        return JsonResponse({
            'success': True, 
            'message': success_msg,
            'team_name': team.name,
            'team_url': reverse("teams:detail", kwargs={"slug": team.slug})
        })
    
    messages.success(request, success_msg)
    return redirect("teams:detail", slug=team.slug)


# -------------------------
# Team member management
# -------------------------
@login_required
@require_http_methods(["POST"])
def kick_member_view(request, slug: str, profile_id: int):
    """Remove a member from the team (captain only)."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check permission to manage roster
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_manage_roster(membership):
            messages.error(request, "You don't have permission to remove members.")
            return redirect("teams:detail", slug=team.slug)
    except TeamMembership.DoesNotExist:
        messages.error(request, "You must be a team member with appropriate permissions.")
        return redirect("teams:detail", slug=team.slug)

    try:
        target_membership = get_object_or_404(TeamMembership, team=team, profile_id=profile_id)
        
        # Prevent kicking OWNER
        if target_membership.role == TeamMembership.Role.OWNER:
            messages.error(request, "Cannot remove team owner. Transfer ownership first.")
            return redirect("teams:detail", slug=team.slug)
        
        member_name = target_membership.profile.user.username
        target_membership.delete()
        messages.success(request, f"Member {member_name} has been removed from the team.")
    except TeamMembership.DoesNotExist:
        messages.error(request, "Member not found in this team.")
    
    return redirect("teams:detail", slug=team.slug)


@login_required
@require_http_methods(["POST"])
def leave_team_view(request, slug: str):
    """Allow a member to leave the team. Supports both AJAX (JSON) and form submissions."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.content_type == 'application/json'
    
    # Get membership
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status=TeamMembership.Status.ACTIVE)
    except TeamMembership.DoesNotExist:
        error_msg = "You are not a member of this team."
        if is_ajax:
            return JsonResponse({'success': False, 'error': error_msg, 'code': 'NOT_A_MEMBER'}, status=400)
        messages.error(request, error_msg)
        return redirect("teams:detail", slug=team.slug)
    
    # OWNER cannot leave (must transfer ownership first)
    if membership.role == TeamMembership.Role.OWNER:
        error_msg = "As team owner, you must transfer ownership before leaving the team."
        if is_ajax:
            return JsonResponse({'success': False, 'error': error_msg, 'code': 'CANNOT_LEAVE_OWNER'}, status=403)
        messages.error(request, error_msg)
        return redirect("teams:manage", slug=team.slug)
    
    # Check if member can leave (roster lock, etc.)
    if not TeamPermissions.can_leave_team(membership):
        error_msg = "You cannot leave the team at this time. Roster may be locked for an active tournament."
        if is_ajax:
            return JsonResponse({'success': False, 'error': error_msg, 'code': 'ROSTER_LOCKED'}, status=403)
        messages.error(request, error_msg)
        return redirect("teams:manage", slug=team.slug)
    
    # Delete membership
    team_name = team.name
    membership.delete()
    
    # Return JSON for AJAX or redirect for regular form submission
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': f'You have left team {team_name}.',
            'redirect_url': reverse('teams:list')
        })
    
    messages.success(request, f"You have left team {team_name}.")
    return redirect("teams:list")


@login_required
@require_http_methods(["POST"])
def transfer_captaincy_view(request, slug: str, profile_id: int):
    """Transfer team captaincy to another member. DEPRECATED - use transfer_ownership_view."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if user is OWNER
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_transfer_ownership(membership):
            messages.error(request, "Only the team owner can transfer ownership.")
            return redirect("teams:detail", slug=team.slug)
    except TeamMembership.DoesNotExist:
        messages.error(request, "You must be a team member.")
        return redirect("teams:detail", slug=team.slug)
    
    try:
        new_captain_membership = get_object_or_404(
            TeamMembership, 
            team=team, 
            profile_id=profile_id,
            status="ACTIVE"
        )
        
        # Update team captain
        team.captain = new_captain_membership.profile
        team.save()
        
        messages.success(
            request, 
            f"Team captaincy transferred to {new_captain_membership.profile.user.username}."
        )
    except TeamMembership.DoesNotExist:
        messages.error(request, "Selected user is not an active member of this team.")
    
    return redirect("teams:detail", slug=team.slug)


@login_required
@require_http_methods(["GET", "POST"])
def team_settings_view(request, slug: str):
    """Team settings page for advanced configuration."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check permission to edit team settings
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_edit_team_profile(membership):
            messages.error(request, "You don't have permission to access team settings.")
            return redirect("teams:detail", slug=team.slug)
    except TeamMembership.DoesNotExist:
        messages.error(request, "You must be a team member with appropriate permissions.")
        return redirect("teams:detail", slug=team.slug)
    
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_setting":
            # Handle individual setting updates
            for field in ['is_open', 'is_recruiting']:
                if field in request.POST:
                    setattr(team, field, request.POST.get(field) == 'true')
            team.save()
            messages.success(request, "Team settings updated successfully!")
        return redirect("teams:settings", slug=team.slug)
    
    # Get current user's membership to check if they can manage permissions
    can_manage_permissions = membership.role == TeamMembership.Role.OWNER
    
    # Get all members with their permissions
    all_members = team.memberships.filter(status="ACTIVE").select_related("profile__user").order_by('role', '-joined_at')
    
    context = {
        "team": team,
        "members": all_members,
        "pending_invites": team.invites.filter(status="PENDING").select_related("invited_user__user"),
        "can_manage_permissions": can_manage_permissions,
        "user_membership": membership,
        # Permission flags for role management
        "can_assign_managers": TeamPermissions.can_assign_managers(membership),
        "can_assign_captain_title": TeamPermissions.can_assign_captain_title(membership),
        "can_assign_coach": TeamPermissions.can_assign_coach(membership),
        "can_change_player_role": TeamPermissions.can_change_player_role(membership),
        "is_owner": membership.role == TeamMembership.Role.OWNER,
        "is_manager": membership.role == TeamMembership.Role.MANAGER,
    }
    
    return render(request, "teams/settings_enhanced.html", context)


@login_required
@require_http_methods(["POST"])
def delete_team_view(request, slug: str):
    """Delete a team permanently (OWNER only)."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if user is OWNER
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_delete_team(membership):
            messages.error(request, "Only the team owner can delete the team.")
            return redirect("teams:detail", slug=team.slug)
    except TeamMembership.DoesNotExist:
        messages.error(request, "You must be a team member.")
        return redirect("teams:detail", slug=team.slug)
    
    confirm_name = request.POST.get("confirm_name", "").strip()
    if confirm_name != team.name:
        messages.error(request, "Team name confirmation does not match.")
        return redirect("teams:settings", slug=team.slug)
    
    team_name = team.name
    team.delete()
    messages.success(request, f"Team '{team_name}' has been permanently deleted.")
    return redirect("teams:list")


@login_required
@require_http_methods(["POST"])
def cancel_invite_view(request, slug: str):
    """Cancel a pending team invitation."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check permission to manage roster
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_manage_roster(membership):
            messages.error(request, "You don't have permission to cancel invitations.")
            return redirect("teams:detail", slug=team.slug)
    except TeamMembership.DoesNotExist:
        messages.error(request, "You must be a team member with appropriate permissions.")
        return redirect("teams:detail", slug=team.slug)
    
    invite_id = request.POST.get("invite_id")
    try:
        invite = get_object_or_404(TeamInvite, id=invite_id, team=team, status="PENDING")
        invited_user_name = invite.invited_user.display_name
        invite.delete()
        messages.success(request, f"Invitation to {invited_user_name} has been cancelled.")
    except TeamInvite.DoesNotExist:
        messages.error(request, "Invitation not found or already processed.")
    
    return redirect("teams:manage", slug=team.slug)


# ========================
# New Professional Team Management Views
# ========================

@login_required
@require_http_methods(["POST"])
def update_team_info_view(request, slug: str):
    """Update team information via AJAX."""
    import json
    from django.http import JsonResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check permission
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_edit_team_profile(membership):
            return JsonResponse({"error": "You don't have permission to edit team information."}, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({"error": "You must be a team member."}, status=403)
    
    try:
        team.name = request.POST.get('name', team.name).strip()
        team.tag = request.POST.get('tag', team.tag).strip()
        team.tagline = request.POST.get('tagline', team.tagline)
        team.description = request.POST.get('description', team.description)
        team.region = request.POST.get('region', team.region)
        team.game = request.POST.get('game', team.game)
        team.hero_template = request.POST.get('hero_template', team.hero_template)
        
        if 'logo' in request.FILES:
            team.logo = request.FILES['logo']
        if 'banner' in request.FILES:
            team.banner_image = request.FILES['banner']
        
        team.save()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def update_privacy_view(request, slug: str):
    """Update team privacy settings via AJAX."""
    from django.http import JsonResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check permission
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_edit_team_profile(membership):
            return JsonResponse({"error": "You don't have permission to edit privacy settings."}, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({"error": "You must be a team member."}, status=403)
    
    try:
        team.is_public = request.POST.get('is_public') == 'on'
        team.allow_join_requests = request.POST.get('allow_join_requests') == 'on'
        team.show_statistics_publicly = request.POST.get('show_statistics_publicly') == 'on'
        team.show_roster_publicly = request.POST.get('show_roster_publicly') == 'on'
        team.is_recruiting = request.POST.get('is_recruiting') == 'on'
        team.allow_posts = request.POST.get('allow_posts') == 'on'
        team.posts_require_approval = request.POST.get('posts_require_approval') == 'on'
        team.save()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def kick_member_ajax_view(request, slug: str):
    """Kick a team member via AJAX."""
    import json
    from django.http import JsonResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check permission
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_manage_roster(membership):
            return JsonResponse({"error": "You don't have permission to remove members."}, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({"error": "You must be a team member."}, status=403)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        
        User = get_user_model()
        target_user = get_object_or_404(User, username=username)
        target_profile = _get_profile(target_user)
        
        if not target_profile:
            return JsonResponse({"error": "User profile not found."}, status=404)
        
        membership = get_object_or_404(TeamMembership, team=team, profile=target_profile)
        
        if membership.role == 'CAPTAIN':
            return JsonResponse({"error": "Cannot kick team captain."}, status=400)
        
        membership.delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def change_member_role_view(request, slug: str):
    """Change a team member's role via AJAX."""
    import json
    from django.http import JsonResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check permission
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_manage_roster(membership):
            return JsonResponse({"error": "You don't have permission to change member roles."}, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({"error": "You must be a team member."}, status=403)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        new_role = data.get('role')
        
        if new_role not in ['PLAYER', 'SUBSTITUTE', 'COACH', 'MANAGER']:
            return JsonResponse({"error": "Invalid role."}, status=400)
        
        User = get_user_model()
        target_user = get_object_or_404(User, username=username)
        target_profile = _get_profile(target_user)
        
        if not target_profile:
            return JsonResponse({"error": "User profile not found."}, status=404)
        
        membership = get_object_or_404(TeamMembership, team=team, profile=target_profile)
        
        if membership.role == 'CAPTAIN':
            return JsonResponse({"error": "Cannot change captain's role. Transfer captaincy first."}, status=400)
        
        membership.role = new_role
        membership.save()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def change_player_role_view(request, slug: str):
    """Change a team member's player role via AJAX (dual-role system)."""
    import json
    from django.http import JsonResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check permission
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_manage_roster(membership):
            return JsonResponse({"error": "You don't have permission to change player roles."}, status=403)
    except TeamMembership.DoesNotExist:
        return JsonResponse({"error": "You must be a team member."}, status=403)
    
    try:
        data = json.loads(request.body)
        profile_id = data.get('profile_id')
        new_player_role = data.get('player_role', '')
        
        if not profile_id:
            return JsonResponse({"error": "Profile ID is required."}, status=400)
        
        # Get the target profile
        from apps.user_profile.models import UserProfile
        target_profile = get_object_or_404(UserProfile, id=profile_id)
        
        # Get the membership
        membership = get_object_or_404(TeamMembership, team=team, profile=target_profile)
        
        # Validate player role for this game
        from apps.teams.dual_role_system import validate_player_role
        is_valid, error_msg = validate_player_role(team.game, new_player_role)
        if new_player_role and not is_valid:
            return JsonResponse({"error": f"Invalid player role '{new_player_role}' for game {team.game}: {error_msg}"}, status=400)
        
        # Set the player role (can be empty to clear it)
        membership.player_role = new_player_role
        membership.save()
        
        return JsonResponse({"success": True, "player_role": new_player_role})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def export_team_data_view(request, slug: str):
    """Export team data as CSV."""
    import csv
    from django.http import HttpResponse
    
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check permission
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_edit_team_profile(membership):
            messages.error(request, "You don't have permission to export team data.")
            return redirect('teams:detail', slug=team.slug)
    except TeamMembership.DoesNotExist:
        messages.error(request, "You must be a team member.")
        return redirect('teams:detail', slug=team.slug)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{team.name}_data.csv"'
    
    writer = csv.writer(response)
    
    # Write team info header
    writer.writerow(['Team Information'])
    writer.writerow(['Name', team.name])
    writer.writerow(['Description', team.description or ''])
    writer.writerow(['Region', team.region or ''])
    writer.writerow(['Primary Game', team.primary_game or ''])
    writer.writerow(['Created', team.created_at.strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow(['Is Public', 'Yes' if team.is_public else 'No'])
    writer.writerow(['Is Active', 'Yes' if team.is_active else 'No'])
    writer.writerow([])
    
    # Write members header
    writer.writerow(['Team Members'])
    writer.writerow(['Username', 'Role', 'Joined Date', 'Status'])
    
    # Write member data
    for membership in team.memberships.all():
        writer.writerow([
            membership.profile.user.username,
            membership.get_role_display(),
            membership.joined_at.strftime('%Y-%m-%d %H:%M:%S'),
            membership.get_status_display()
        ])
    
    return response


@login_required
def tournament_history_view(request, slug: str):
    """Show team's tournament participation history."""
    team = get_object_or_404(Team, slug=slug)
    profile = _ensure_profile(request.user)
    
    # Check if member (basic view permission)
    try:
        membership = TeamMembership.objects.get(team=team, profile=profile, status='ACTIVE')
        if not TeamPermissions.can_view_team_roster(membership):
            messages.error(request, "You don't have permission to view tournament history.")
            return redirect('teams:detail', slug=team.slug)
    except TeamMembership.DoesNotExist:
        messages.error(request, "You must be a team member.")
        return redirect('teams:detail', slug=team.slug)
    
    # Get tournament registrations for this team
    from django.apps import apps
    from apps.common.serializers import TournamentSerializer
    
    # DECOUPLED: Use TeamTournamentRegistration (tournaments app moved to legacy)
    TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
    
    registrations_qs = TeamTournamentRegistration.objects.filter(
        team=team
    ).order_by('-registered_at')
    
    # DECOUPLED: Use serializer for consistent data structure
    registrations = [
        TournamentSerializer.serialize_registration(reg)
        for reg in registrations_qs
    ]
    
    context = {
        'team': team,
        'registrations': registrations,
    }
    
    return render(request, 'teams/tournament_history.html', context)


# -------------------------
# Game ID Collection (Phase: Game ID System)
# -------------------------
@login_required
@require_http_methods(["GET", "POST"])
def collect_game_id_view(request, game_code: str):
    """
    Collect game ID from user before team creation or joining.
    Called when user doesn't have game ID for selected game.
    """
    from apps.teams.game_id_forms import GameIDCollectionForm
    from apps.user_profile.models import UserProfile
    
    profile = UserProfile.objects.get(user=request.user)
    
    # Get game display name
    game_choices = dict(Team._meta.get_field('game').choices)
    game_name = game_choices.get(game_code, game_code.upper())
    
    if request.method == 'POST':
        form = GameIDCollectionForm(request.POST, game_code=game_code)
        if form.is_valid():
            # Save game ID to user profile
            form.save_to_profile(profile)
            messages.success(request, f"Your {game_name} game ID has been saved successfully!")
            
            # Check for pending actions and redirect accordingly
            if 'pending_team_data' in request.session:
                return redirect('teams:create_team_resume')
            elif 'pending_join_team' in request.session:
                team_slug = request.session.get('pending_join_team')
                return redirect('teams:join_team', slug=team_slug)
            else:
                # No pending action, go to profile
                return redirect('user_profile:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill with existing data if any
        initial = {}
        existing_id = profile.get_game_id(game_code)
        if existing_id:
            if game_code == 'valorant':
                # Split Riot ID into name and tagline
                if '#' in existing_id:
                    parts = existing_id.split('#', 1)
                    initial['riot_id'] = parts[0]
                    initial['riot_tagline'] = parts[1]
            else:
                field_name = {
                    'dota2': 'steam_id',
                    'cs2': 'steam_id',
                    'efootball': 'efootball_id',
                    'mlbb': 'mlbb_id',
                    'pubgm': 'pubg_mobile_id',
                    'freefire': 'free_fire_id',
                    'fc24': 'ea_id',
                    'codm': 'codm_uid',
                }.get(game_code)
                if field_name:
                    initial[field_name] = existing_id
        
        form = GameIDCollectionForm(game_code=game_code, initial=initial)
    
    context = {
        'form': form,
        'game_name': game_name,
        'game_code': game_code,
        'has_pending_team': 'pending_team_data' in request.session,
        'has_pending_join': 'pending_join_team' in request.session,
    }
    
    return render(request, 'teams/collect_game_id.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def create_team_resume_view(request):
    """
    Resume team creation after collecting game ID.
    Retrieves team data from session and creates the team.
    """
    from apps.user_profile.models import UserProfile
    
    # Check if there's pending team data
    if 'pending_team_data' not in request.session:
        messages.error(request, "No pending team creation found.")
        return redirect('teams:create')
    
    profile = UserProfile.objects.get(user=request.user)
    team_data = request.session.get('pending_team_data')
    
    # Verify user now has the game ID
    game_id = profile.get_game_id(team_data['game'])
    if not game_id:
        messages.error(request, "Game ID is still missing. Please provide it to continue.")
        return redirect('teams:collect_game_id', game_code=team_data['game'])
    
    # Create the team
    try:
        team = Team.objects.create(
            name=team_data['name'],
            tag=team_data['tag'],
            description=team_data.get('description', ''),
            game=team_data['game'],
            region=team_data.get('region', ''),
            twitter=team_data.get('twitter', ''),
            instagram=team_data.get('instagram', ''),
            discord=team_data.get('discord', ''),
            youtube=team_data.get('youtube', ''),
            twitch=team_data.get('twitch', ''),
            linktree=team_data.get('linktree', ''),
            captain=profile,
        )
        
        # Ensure captain membership
        if hasattr(team, 'ensure_captain_membership'):
            team.ensure_captain_membership()
        
        # Clear session data
        del request.session['pending_team_data']
        if 'pending_team_has_logo' in request.session:
            del request.session['pending_team_has_logo']
        if 'pending_team_has_banner' in request.session:
            del request.session['pending_team_has_banner']
        
        messages.success(request, f"Team '{team.name}' created successfully!")
        return redirect('teams:detail', slug=team.slug)
        
    except Exception as e:
        messages.error(request, f"Error creating team: {str(e)}")
        return redirect('teams:create')


