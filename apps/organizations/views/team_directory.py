"""
Team Directory View

Provides a browseable, filterable listing of public teams.
Supports ?filter=recruiting to show only recruiting teams.

Phase 11: Premium dark theme team directory.
"""
from collections import defaultdict

from django.db.models import Count, Q
from django.shortcuts import render
from django.core.cache import cache
from django.templatetags.static import static
from django.urls import reverse
from django.utils.text import slugify

from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models.recruitment import RecruitmentPosition
from apps.organizations.models.team import Team
from apps.organizations.models.membership import TeamMembership
from apps.organizations.services.recruitment_discovery import (
    active_recruitment_positions_prefetch,
    build_recruitment_summary,
    get_available_player_summaries,
)
from apps.games.models import Game
from apps.common.seo import breadcrumb_schema, build_seo


GAME_SELECTOR_CATALOG = [
    {
        "slug": "valorant",
        "label": "Valorant",
        "short_label": "VAL",
        "initials": "VAL",
        "color": "#ff4655",
        "asset_key": "valorant",
        "aliases": ("valorant", "val"),
    },
    {
        "slug": "pubg-mobile",
        "label": "PUBG Mobile",
        "short_label": "PUBGM",
        "initials": "PUB",
        "color": "#f2a900",
        "asset_key": "pubg",
        "aliases": ("pubg-mobile", "pubgm", "pubg"),
    },
    {
        "slug": "free-fire",
        "label": "Free Fire",
        "short_label": "FF",
        "initials": "FF",
        "color": "#ff7a00",
        "asset_key": "freefire",
        "aliases": ("free-fire", "freefire", "ff"),
    },
    {
        "slug": "cs2",
        "label": "CS2",
        "short_label": "CS2",
        "initials": "CS2",
        "color": "#f59e0b",
        "asset_key": "cs2",
        "aliases": ("cs2", "counter-strike-2", "counter-strike", "counter-strike-global-offensive"),
    },
    {
        "slug": "dota-2",
        "label": "Dota 2",
        "short_label": "DOTA",
        "initials": "D2",
        "color": "#a11d20",
        "asset_key": "dota2",
        "aliases": ("dota-2", "dota2", "dota"),
    },
    {
        "slug": "mobile-legends-bang-bang",
        "label": "Mobile Legends: Bang Bang",
        "short_label": "MLBB",
        "initials": "ML",
        "color": "#2563eb",
        "asset_key": "mlbb",
        "aliases": ("mobile-legends-bang-bang", "mobile-legends", "mlbb", "ml"),
    },
    {
        "slug": "efootball",
        "label": "eFootball",
        "short_label": "eFB",
        "initials": "eF",
        "color": "#22c55e",
        "asset_key": "efootball",
        "aliases": ("efootball", "e-football", "pes"),
    },
    {
        "slug": "fc-26",
        "label": "FC 26",
        "short_label": "FC26",
        "initials": "FC",
        "color": "#14b8a6",
        "asset_key": "fc26",
        "aliases": ("fc-26", "fc26", "ea-sports-fc-26", "fifa-26"),
    },
    {
        "slug": "rocket-league",
        "label": "Rocket League",
        "short_label": "RL",
        "initials": "RL",
        "color": "#0ea5e9",
        "asset_key": "rocketleague",
        "aliases": ("rocket-league", "rocketleague", "rl"),
    },
    {
        "slug": "apex-legends",
        "label": "Apex Legends",
        "short_label": "Apex",
        "initials": "APX",
        "color": "#ef4444",
        "asset_key": "",
        "aliases": ("apex-legends", "apex"),
    },
    {
        "slug": "call-of-duty-mobile",
        "label": "Call of Duty: Mobile",
        "short_label": "CODM",
        "initials": "COD",
        "color": "#facc15",
        "asset_key": "codm",
        "aliases": ("call-of-duty-mobile", "cod-mobile", "codm", "call-of-duty"),
    },
]


def _game_key(value):
    return slugify(str(value or "")).replace("-", "")


def _game_image_url(game, field_name):
    image = getattr(game, field_name, None)
    if not image:
        return ""
    try:
        return image.url
    except ValueError:
        return ""


def _game_design_logo_url(asset_key):
    if not asset_key:
        return ""
    return static(f"organizations/team_find/assets/games/logos/{asset_key}.jpg")


def _find_team_url_with(request, **overrides):
    query = request.GET.copy()
    query.pop("filter", None)
    for key, value in overrides.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value
    encoded = query.urlencode()
    url = reverse("organizations:team_find")
    return f"{url}?{encoded}" if encoded else url


def _team_manage_url(team):
    if team.organization:
        url = reverse(
            "organizations:org_team_manage",
            kwargs={"org_slug": team.organization.slug, "team_slug": team.slug},
        )
    else:
        url = reverse("organizations:team_manage", kwargs={"team_slug": team.slug})
    return f"{url}#join-requests"


def _manageable_team_options(user):
    if not user.is_authenticated:
        return []

    # role per team (Owner/Manager) so the post flow is permission-aware
    role_by_team = {}
    for team_id, role in TeamMembership.objects.filter(
        user=user,
        status=MembershipStatus.ACTIVE,
        role__in=[MembershipRole.OWNER, MembershipRole.MANAGER],
    ).values_list("team_id", "role"):
        role_by_team[team_id] = role
    created_team_ids = set(
        Team.objects.filter(
            created_by=user,
            status=TeamStatus.ACTIVE,
        ).values_list("id", flat=True)
    )
    for team_id in created_team_ids:
        role_by_team.setdefault(team_id, MembershipRole.OWNER)

    team_ids = set(role_by_team)
    if not team_ids:
        return []

    teams = (
        Team.objects.filter(id__in=team_ids, status=TeamStatus.ACTIVE)
        .select_related("organization")
        .order_by("name")[:8]
    )
    game_map = {
        game.id: game
        for game in Game.objects.filter(id__in=[team.game_id for team in teams], is_active=True)
    }
    role_labels = dict(MembershipRole.choices)
    options = []
    for team in teams:
        game = game_map.get(team.game_id)
        role_value = role_by_team.get(team.id, MembershipRole.MANAGER)
        options.append({
            "name": team.name,
            "tag": team.tag,
            "slug": team.slug,
            "manage_url": _team_manage_url(team),
            "api_url": reverse("organizations_api:team_recruitment_position_save", kwargs={"slug": team.slug}),
            "game_slug": getattr(game, "slug", ""),
            "game_label": getattr(game, "display_name", "") or "Team game",
            "game_color": getattr(game, "primary_color", "") or "#0A84FF",
            "role": role_value,
            "role_label": role_labels.get(role_value, "Manager"),
            "region": team.region or "",
            "platform": team.platform or "",
        })
    return options


def _preferred_game_for_user(user):
    if not user.is_authenticated:
        return None

    try:
        from apps.user_profile.models import GameProfile, UserProfile
    except Exception:
        return None

    profile = (
        UserProfile.objects.filter(user=user)
        .select_related("primary_team", "primary_game")
        .first()
    )
    if profile:
        if profile.primary_team and profile.primary_team.game_id:
            game = Game.objects.filter(id=profile.primary_team.game_id, is_active=True).first()
            if game:
                return game
        if profile.primary_game and profile.primary_game.is_active:
            return profile.primary_game

    passport = (
        GameProfile.objects.filter(
            user=user,
            status=GameProfile.STATUS_ACTIVE,
            visibility=GameProfile.VISIBILITY_PUBLIC,
            game__is_active=True,
        )
        .select_related("game")
        .order_by("-is_lft", "-is_pinned", "pinned_order", "sort_order", "game__display_name")
        .first()
    )
    return passport.game if passport else None


def _game_selector_options(request, active_games, game_filter, *, preferred_game=None):
    all_games_url = (
        _find_team_url_with(request, game="all")
        if preferred_game
        else _find_team_url_with(request, game="")
    )
    options = [{
        "slug": "",
        "label": "All Games",
        "short_label": "All",
        "color": "#3b82f6",
        "url": all_games_url,
        "is_active": not bool(game_filter),
        "icon_url": "",
        "logo_url": "",
        "design_logo_url": "",
        "initials": "ALL",
        "is_available": True,
        "is_catalog": True,
    }]

    game_by_key = {}
    for game in active_games:
        keys = {
            _game_key(game.slug),
            _game_key(game.name),
            _game_key(game.display_name),
            _game_key(game.short_code),
        }
        for key in keys:
            if key:
                game_by_key.setdefault(key, game)

    used_game_ids = set()
    for catalog_game in GAME_SELECTOR_CATALOG:
        game = None
        for alias in catalog_game["aliases"]:
            game = game_by_key.get(_game_key(alias))
            if game:
                break
        slug = game.slug if game else catalog_game["slug"]
        if game:
            used_game_ids.add(game.id)
        options.append({
            "slug": slug,
            "label": game.display_name if game else catalog_game["label"],
            "short_label": (game.short_code if game else catalog_game["short_label"]) or catalog_game["short_label"],
            "color": (game.primary_color if game else catalog_game["color"]) or catalog_game["color"],
            "url": _find_team_url_with(request, game=slug),
            "is_active": slug == game_filter,
            "icon_url": _game_image_url(game, "icon") if game else "",
            "logo_url": _game_image_url(game, "logo") if game else "",
            "design_logo_url": _game_design_logo_url(catalog_game.get("asset_key")),
            "initials": ((game.short_code if game else catalog_game["initials"]) or catalog_game["initials"]).upper(),
            "is_available": bool(game),
            "is_catalog": True,
        })

    for game in active_games:
        if game.id in used_game_ids:
            continue
        options.append({
            "slug": game.slug,
            "label": game.display_name,
            "short_label": game.short_code or game.display_name,
            "color": game.primary_color or "#3b82f6",
            "url": _find_team_url_with(request, game=game.slug),
            "is_active": game.slug == game_filter,
            "icon_url": _game_image_url(game, "icon"),
            "logo_url": _game_image_url(game, "logo"),
            "design_logo_url": "",
            "initials": (game.short_code or game.display_name[:3]).upper(),
            "is_available": True,
            "is_catalog": False,
        })
    return options


def _public_passport_options(user):
    if not user.is_authenticated:
        return []

    try:
        from apps.user_profile.models import GameProfile
    except Exception:
        return []

    passports = (
        GameProfile.objects.filter(
            user=user,
            status=GameProfile.STATUS_ACTIVE,
            visibility=GameProfile.VISIBILITY_PUBLIC,
            game__is_active=True,
        )
        .select_related("game")
        .order_by("-is_lft", "-is_pinned", "pinned_order", "sort_order", "game__display_name")[:12]
    )
    return [
        {
            "id": passport.id,
            "game_slug": passport.game.slug,
            "game_label": passport.game.display_name,
            "label": f"{passport.game.display_name} - {passport.in_game_name or passport.ign or 'Public passport'}",
            "is_lft": bool(passport.is_lft),
        }
        for passport in passports
    ]


def _choice_options(choices, *, allowed_values=None):
    allowed = set(allowed_values or [])
    return [
        {"value": value, "label": label}
        for value, label in choices
        if not allowed or value in allowed
    ]


def _game_ranks(game):
    ranks = []
    for item in (getattr(game, "available_ranks", None) or []):
        if isinstance(item, dict):
            label = item.get("label") or item.get("value")
            if label:
                ranks.append(str(label))
        elif item:
            ranks.append(str(item))
    return ranks


def _serialize_games(active_games, game_selector_options):
    """Per-game roles + ranks + colour, so the client can drive game-aware
    filters and the post form. Roles come from GameRole, ranks from the
    game's available_ranks ladder — all real config, no invented values."""
    logo_by_slug = {}
    for opt in game_selector_options:
        slug = opt.get("slug")
        if slug:
            logo_by_slug[slug] = opt.get("icon_url") or opt.get("logo_url") or opt.get("design_logo_url") or ""

    roles_by_game = defaultdict(list)
    try:
        from apps.games.models import GameRole

        for game_id, role_name in (
            GameRole.objects.filter(game_id__in=[g.id for g in active_games], is_active=True)
            .order_by("game_id", "order", "role_name")
            .values_list("game_id", "role_name")
        ):
            if role_name and role_name not in roles_by_game[game_id]:
                roles_by_game[game_id].append(role_name)
    except Exception:
        pass

    games = {}
    for game in active_games:
        games[game.slug] = {
            "name": game.display_name,
            "short": game.short_code or (game.display_name or "")[:4],
            "color": game.primary_color or "#0A84FF",
            "logo": logo_by_slug.get(game.slug, ""),
            "roles": roles_by_game.get(game.id, []),
            "ranks": _game_ranks(game),
        }
    return games


def _norm(value):
    return str(value or "").strip().lower()


def _role_hit(need, role_set):
    n = _norm(need)
    if not n or not role_set:
        return False
    return any(r and (r in n or n in r) for r in role_set)


def _viewer_player_ctx(user, preferred_game):
    """What the signed-in user looks like as a candidate (for scoring teams)."""
    if not user.is_authenticated:
        return None
    try:
        from apps.user_profile.models import CareerProfile, GameProfile
    except Exception:
        return None

    career = (
        CareerProfile.objects.filter(user_profile__user=user)
        .only("primary_roles", "secondary_roles", "preferred_region")
        .first()
    )
    roles = set()
    region = ""
    if career:
        for grp in (career.primary_roles, career.secondary_roles):
            if isinstance(grp, list):
                roles.update(_norm(r) for r in grp if r)
        region = _norm(career.preferred_region)

    game_slug = preferred_game.slug if preferred_game else ""
    rank_name, platform = "", ""
    passport_qs = GameProfile.objects.filter(
        user=user,
        status=GameProfile.STATUS_ACTIVE,
        visibility=GameProfile.VISIBILITY_PUBLIC,
        game__is_active=True,
    ).select_related("game")
    passport = None
    if game_slug:
        passport = passport_qs.filter(game__slug=game_slug).first()
    passport = passport or passport_qs.order_by("-is_lft", "-is_pinned").first()
    if passport:
        if not game_slug:
            game_slug = passport.game.slug
        rank_name = passport.rank_name or ""
        platform = _norm(passport.platform)
        if not region:
            region = _norm(passport.region)
        if passport.main_role:
            roles.add(_norm(passport.main_role))

    if not (game_slug or roles or region):
        return None
    return {"game": game_slug, "roles": roles, "region": region, "platform": platform, "rank": rank_name}


def _viewer_manager_ctx(user, manageable_teams):
    """The signed-in manager's open needs (for scoring players)."""
    if not user.is_authenticated or not manageable_teams:
        return None
    slugs = [t["slug"] for t in manageable_teams]
    teams = list(Team.objects.filter(slug__in=slugs).only("id", "game_id", "region", "platform"))
    if not teams:
        return None
    games = {opt["game_slug"] for opt in manageable_teams if opt.get("game_slug")}
    regions = {_norm(t.region) for t in teams if t.region}
    platforms = {_norm(t.platform) for t in teams if t.platform}
    roles = set()
    positions = (
        RecruitmentPosition.objects.filter(team_id__in=[t.id for t in teams], is_active=True)
        .only("role_category", "title", "region", "platform")
    )
    for pos in positions:
        if pos.role_category:
            roles.add(_norm(pos.get_role_category_display()))
        if pos.title:
            roles.add(_norm(pos.title))
        if pos.region:
            regions.add(_norm(pos.region))
        if pos.platform:
            platforms.add(_norm(pos.platform))
    if not (games or roles or regions or platforms):
        return None
    return {"games": games, "roles": roles, "regions": regions, "platforms": platforms}


def _score_components(components):
    """components: list of (label, weight, applicable, met, value).
    Returns (score 0-100 or None, breakdown list)."""
    applicable = [c for c in components if c[2]]
    breakdown = [{"label": c[0], "met": bool(c[3]), "value": c[4]} for c in applicable]
    total = sum(c[1] for c in applicable)
    if not total:
        return None, []
    got = sum(c[1] for c in applicable if c[3])
    return round(100 * got / total), breakdown


def _match_team(team, game_obj, summary, pctx):
    if not pctx:
        return None, []
    g = getattr(game_obj, "slug", "")
    need = summary.get("title") or summary.get("role_category") or ""
    region = summary.get("region") or team.region or ""
    platform = summary.get("platform") or team.platform or ""
    return _score_components([
        ("Same game", 45, bool(pctx["game"]), bool(g) and g == pctx["game"], getattr(game_obj, "display_name", "")),
        ("Needs your role", 25, bool(pctx["roles"]), _role_hit(need, pctx["roles"]), need or "—"),
        ("Region compatible", 15, bool(pctx["region"]), bool(region) and _norm(region) == pctx["region"], region or "—"),
        ("Platform compatible", 15, bool(pctx["platform"]), bool(platform) and _norm(platform) == pctx["platform"], platform or "—"),
    ])


def _match_player(player, mctx):
    if not mctx:
        return None, []
    pp = player.get("primary_passport") or {}
    game = pp.get("game_slug") or ""
    roles = {_norm(r) for r in (player.get("roles") or []) if r}
    if pp.get("main_role"):
        roles.add(_norm(pp.get("main_role")))
    region = player.get("region") or pp.get("region") or ""
    platform = pp.get("platform") or ""
    role_met = any(_role_hit(r, mctx["roles"]) for r in roles) if (roles and mctx["roles"]) else False
    return _score_components([
        ("Fits your game", 45, bool(mctx["games"]), bool(game) and game in mctx["games"], pp.get("game") or "—"),
        ("Fills a roster need", 25, bool(mctx["roles"]), role_met, (player.get("roles") or ["—"])[0]),
        ("Region compatible", 15, bool(mctx["regions"]), bool(region) and _norm(region) in mctx["regions"], region or "—"),
        ("Platform compatible", 15, bool(mctx["platforms"]), bool(platform) and _norm(platform) in mctx["platforms"], platform or "—"),
    ])


def team_directory(request, force_recruiting=False):
    """
    Public team directory with optional filter.

    Query params:
    - filter: 'recruiting' | 'all' (default: 'all')
    - game: game slug to filter by game
    - region: region string to filter
    - q: search query (team name or tag)
    - sort: 'newest' | 'name' | 'members' (default: 'newest')
    """
    active_filter = 'recruiting' if force_recruiting else request.GET.get('filter', 'all')
    raw_game_filter = request.GET.get('game', '')
    skip_preferred_game = raw_game_filter == 'all'
    game_filter = '' if skip_preferred_game else raw_game_filter
    region_filter = request.GET.get('region', '')
    platform_filter = request.GET.get('platform', '')
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'newest')
    is_recruiting_filter = active_filter == 'recruiting'
    selected_game = None

    # Base queryset: active, public teams only
    teams = (
        Team.objects
        .filter(status=TeamStatus.ACTIVE, visibility='PUBLIC')
        .select_related('organization')
        .annotate(member_count=Count('vnext_memberships', distinct=True))
    )

    # Apply filters
    if is_recruiting_filter:
        teams = teams.filter(is_recruiting=True).prefetch_related(
            active_recruitment_positions_prefetch()
        )

    preferred_game = _preferred_game_for_user(request.user) if is_recruiting_filter else None
    if not game_filter and is_recruiting_filter and not skip_preferred_game:
        if preferred_game:
            game_filter = preferred_game.slug
            selected_game = preferred_game

    if game_filter:
        selected_game = selected_game or Game.objects.filter(slug=game_filter, is_active=True).first()
        if selected_game and not is_recruiting_filter:
            teams = teams.filter(game_id=selected_game.id)
        elif not selected_game and not is_recruiting_filter:
            game_filter = ''

    if region_filter:
        teams = teams.filter(region__icontains=region_filter)

    if platform_filter:
        if is_recruiting_filter:
            teams = teams.filter(
                Q(platform__icontains=platform_filter) |
                Q(recruitment_positions__platform__icontains=platform_filter)
            ).distinct()
        else:
            teams = teams.filter(platform__icontains=platform_filter)

    if search_query:
        teams = teams.filter(
            Q(name__icontains=search_query) |
            Q(tag__icontains=search_query)
        )

    # Apply sort
    if sort_by == 'name':
        teams = teams.order_by('name')
    elif sort_by == 'members':
        teams = teams.order_by('-member_count', '-created_at')
    else:  # newest (default)
        teams = teams.order_by('-created_at')

    # Limit to 100
    teams = teams[:100]

    # Public sidebar/header data — cache for 5 min to drop ~5 queries per page paint.
    def _directory_facets():
        total = Team.objects.filter(status=TeamStatus.ACTIVE, visibility='PUBLIC').count()
        recruiting = Team.objects.filter(
            status=TeamStatus.ACTIVE, visibility='PUBLIC', is_recruiting=True
        ).count()
        regions_qs = list(
            Team.objects.filter(status=TeamStatus.ACTIVE, visibility='PUBLIC')
            .values_list('region', flat=True).distinct().order_by('region')
        )
        platforms_qs = list(
            Team.objects.filter(status=TeamStatus.ACTIVE, visibility='PUBLIC')
            .values_list('platform', flat=True).distinct().order_by('platform')
        )
        return {
            'total_teams': total,
            'recruiting_count': recruiting,
            'regions': [r for r in regions_qs if r],
            'platforms': [p for p in platforms_qs if p],
        }
    facets = cache.get_or_set('orgs:team_directory:facets:v2', _directory_facets, 300)
    total_teams = facets['total_teams']
    recruiting_count = facets['recruiting_count']
    regions = facets['regions']
    platforms = facets['platforms']

    # Single fetch of active games — feeds both the filter pills and the
    # per-team game_obj lookup (was 2 duplicated DB hits).
    active_games = list(Game.objects.filter(is_active=True).order_by('display_name'))
    game_map = {game.id: game for game in active_games}
    game_selector_options = _game_selector_options(
        request,
        active_games,
        game_filter,
        preferred_game=preferred_game,
    )
    selected_game_label = next(
        (option["label"] for option in game_selector_options if option.get("is_active") and option.get("slug")),
        getattr(selected_game, "display_name", "") if selected_game else "",
    )

    # Annotate teams with game info via wrapper dicts
    team_list = []
    open_role_count = 0
    for team in teams:
        recruitment_summary = (
            build_recruitment_summary(team)
            if is_recruiting_filter and team.is_recruiting
            else None
        )
        if recruitment_summary:
            open_role_count += recruitment_summary.get('open_role_count', 0)
        team_list.append({
            'team': team,
            'game_obj': game_map.get(team.game_id),
            'recruitment_summary': recruitment_summary,
        })

    available_players = (
        get_available_player_summaries(
            limit=24,
            game_slug="" if is_recruiting_filter else (selected_game.slug if selected_game else ""),
            region=region_filter,
            platform=platform_filter,
            search_query=search_query,
            sort_by=sort_by,
        )
        if is_recruiting_filter
        else []
    )

    manageable_teams = _manageable_team_options(request.user)
    if not request.user.is_authenticated:
        scout_role = 'guest'
    elif manageable_teams:
        scout_role = 'manager'
    else:
        scout_role = 'player'

    # ---- Smart matching (real attributes only; None when no viewer context) ----
    scout_games = {}
    has_match_context = False
    if is_recruiting_filter:
        scout_games = _serialize_games(active_games, game_selector_options)
        pctx = _viewer_player_ctx(request.user, preferred_game or selected_game)
        mctx = _viewer_manager_ctx(request.user, manageable_teams)
        has_match_context = bool(pctx or mctx)
        for item in team_list:
            score, compat = _match_team(
                item['team'], item['game_obj'], item.get('recruitment_summary') or {}, pctx
            )
            item['match'] = score
            item['compat'] = compat
        for player in available_players:
            score, compat = _match_player(player, mctx)
            player['match'] = score
            player['compat'] = compat

    context = {
        'teams': team_list,
        'scout_role': scout_role,
        'scout_games': scout_games,
        'has_match_context': has_match_context,
        'total_teams': total_teams,
        'recruiting_count': recruiting_count,
        'recruiting_result_count': len(team_list),
        'open_role_count': open_role_count,
        'available_player_count': len(available_players),
        'scout_result_count': len(team_list) + len(available_players),
        'is_recruiting_filter': is_recruiting_filter,
        'active_filter': active_filter,
        'game_filter': game_filter,
        'selected_game': selected_game,
        'selected_game_label': selected_game_label,
        'preferred_game': preferred_game,
        'game_selector_options': game_selector_options,
        'region_filter': region_filter,
        'platform_filter': platform_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'active_games': active_games,
        'regions': regions,
        'platforms': platforms,
        'available_players': available_players,
        'lft_teasers': available_players,
        'find_team_url': reverse('organizations:team_find'),
        'directory_recruiting_url': f"{reverse('organizations:team_directory')}?filter=recruiting",
        'manageable_teams': manageable_teams,
        'user_public_passports': _public_passport_options(request.user),
        'team_recruitment_role_choices': _choice_options(RecruitmentPosition.RoleCategory.choices),
        'lft_career_status_choices': _choice_options(
            [
                ("LOOKING", "Actively Looking"),
                ("FREE_AGENT", "Free Agent"),
            ]
        ),
        'lft_availability_choices': _choice_options(
            [
                ("FULL_TIME", "Full Time"),
                ("PART_TIME", "Part Time"),
                ("WEEKENDS", "Weekends Only"),
                ("CUSTOM", "Custom Schedule"),
            ]
        ),
        'lft_save_url': reverse('organizations_api:discovery_lft_profile_save'),
        'career_settings_save_url': reverse('user_profile:settings_career_save'),
        'seo': build_seo(
            title='Find Team - Scouting Grounds | DeltaCrown' if is_recruiting_filter else 'Esports Team Directory | DeltaCrown',
            description=(
                'Find DeltaCrown teams recruiting now. Filter by game, region, platform, and apply from each team page.'
                if is_recruiting_filter
                else 'Browse public DeltaCrown esports teams by game, region, recruiting status, and organization across Bangladesh and South Asia.'
            ),
            path='/teams/find/' if is_recruiting_filter else '/teams/directory/',
            noindex=bool(search_query or game_filter or region_filter or sort_by != 'newest' or platform_filter),
            schema=breadcrumb_schema([('Home', '/'), ('Teams', '/teams/'), ('Directory', '/teams/directory/')]),
        ),
    }

    return render(request, 'organizations/teams/team_directory.html', context)


def find_team(request):
    return team_directory(request, force_recruiting=True)
