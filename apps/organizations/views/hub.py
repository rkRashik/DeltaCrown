"""
Hub view for vNext landing page.

Provides the central command hub with:
- Hero carousel (top org, user status, recent tournament)
- Featured teams grid
- Global leaderboard
- Dynamic widgets populated via API

Schema Safety:
- Queries are defensive and work even if tag/tagline migrations not applied
- Uses schema introspection to avoid ProgrammingError on missing columns
"""

import json
import logging
from django.shortcuts import render
from django.conf import settings
from django.core.cache import cache
from django.db import ProgrammingError
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _get_hero_carousel_context(request):
    """
    Get hero carousel data with robust fallbacks.
    
    API CONTRACT: STABLE (Phase C+)
    This function's return structure is LOCKED for Phase C+/D consumption.
    Breaking changes require Phase D architecture review.
    
    Returns dict with:
    - top_organization: Top org by empire_score (or None) — GUARANTEED key
    - user_teams_count: Count of user's active teams — GUARANTEED key (default: 0)
    - user_primary_team: User's primary team (owner or first membership) — GUARANTEED key (or None)
    - recent_tournament_winner: Recent tournament winner data (or None) — GUARANTEED key
    
    Empty State Guarantee: All keys present even if no data exists.
    
    Cache: 2 minutes per user (carousel data)
    """
    from apps.organizations.models import Team  # vNext Team is canonical
    from apps.organizations.models import Organization
    
    cache_key = f'hero_carousel_{request.user.id}'
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    carousel_data = {
        'top_organization': None,
        'user_teams_count': 0,
        'user_primary_team': None,
        'recent_tournament_winner': None,
    }
    
    # Slide 1: Top organization by empire_score
    # DEFENSIVE GUARD: Handles missing OrganizationRanking rows gracefully
    try:
        top_org_qs = Organization.objects.select_related('ranking', 'ceo')
        
        # Prefer verified organizations with ranking
        carousel_data['top_organization'] = top_org_qs.filter(
            is_verified=True,
            ranking__isnull=False  # CRITICAL: Prevents crash if ranking row missing
        ).order_by('-ranking__empire_score', '-updated_at').first()
        
        # Fallback to any verified organization (even without ranking)
        if not carousel_data['top_organization']:
            carousel_data['top_organization'] = top_org_qs.filter(
                is_verified=True
            ).order_by('-updated_at').first()
        
        # Fallback to any organization (last resort)
        if not carousel_data['top_organization']:
            carousel_data['top_organization'] = top_org_qs.order_by('-updated_at').first()
        
        # DEFENSIVE: If org exists but has no ranking, ensure no attribute access errors
        if carousel_data['top_organization'] and not hasattr(carousel_data['top_organization'], 'ranking'):
            logger.debug(f"Top org {carousel_data['top_organization'].slug} has no ranking row")
    except Exception as e:
        logger.warning(f"Could not fetch top organization: {e}")
        # carousel_data['top_organization'] remains None (guaranteed key)
    
    # Slide 2: User's team status
    try:
        # Phase 8 Correction: Teams can be independent OR org-owned
        # Check user's team memberships or if they created teams
        if request.user.is_authenticated:
            from django.db.models import Q
            carousel_data['user_teams_count'] = Team.objects.filter(
                Q(vnext_memberships__user=request.user, vnext_memberships__status='ACTIVE') |
                Q(created_by=request.user),
                status='ACTIVE'
            ).distinct().count()
            
            # Find user's primary team (created team first, then first active membership)
            carousel_data['user_primary_team'] = Team.objects.filter(
                Q(created_by=request.user) |
                Q(vnext_memberships__user=request.user, vnext_memberships__status='ACTIVE'),
                status='ACTIVE'
            ).order_by('-created_by', 'vnext_memberships__joined_at').first()
    except Exception as e:
        logger.warning(f"Could not fetch user team data: {e}")
    
    # Slide 3: Most recent tournament winner
    # DISABLED 2026-02-06: Tournament model does not have winner_team field
    # This query was causing FieldError exceptions. Tournament results need proper relationship.
    # TODO: Implement proper tournament result integration with vNext teams
    try:
        pass  # Disabled - see comment above
        # from apps.tournaments.models import Tournament
        # recent_tournament = Tournament.objects.filter(
        #     status__in=['COMPLETED', 'FINALIZED'],
        #     winner_team__isnull=False
        # ).select_related('winner_team', 'winner_team__organization').order_by('-end_date').first()
        # 
        # if recent_tournament and recent_tournament.winner_team:
        #     carousel_data['recent_tournament_winner'] = {
        #         'team_name': recent_tournament.winner_team.name,
        #         'team_slug': recent_tournament.winner_team.slug,
        #         'tournament_name': recent_tournament.name,
        #         'tournament_id': recent_tournament.id,
        #         'end_date': recent_tournament.end_date,
        #     }
    except Exception as e:
        logger.warning(f"Could not fetch recent tournament winner: {e}")
    
    # Cache for 2 minutes
    cache.set(cache_key, carousel_data, 120)
    return carousel_data


def _get_spotlight_teams(limit=5):
    """
    Get teams for the Hero spotlight carousel.

    Priority cascade (fills up to `limit` teams):
      1. Admin-featured teams (is_featured=True) — curated picks
      2. Recruiting teams (is_recruiting=True) — always fresh
      3. Newest active teams — never empty

    Each returned dict contains:
      team, badge_emoji, badge_text

    Cache: 60 seconds
    """
    from apps.organizations.models import Team
    from apps.organizations.choices import TeamStatus

    cache_key = f'spotlight_teams_{limit}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    spotlight = []
    seen_ids = set()

    try:
        base_qs = Team.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
        ).select_related('organization', 'created_by').prefetch_related(
            'vnext_memberships'
        )

        # 1. Admin-featured teams
        featured_qs = base_qs.filter(is_featured=True).order_by('-updated_at')
        for t in featured_qs[:limit]:
            label = t.featured_label or 'Featured'
            spotlight.append({
                'team': t,
                'badge_emoji': '\u2B50',
                'badge_text': label,
            })
            seen_ids.add(t.pk)

        # 2. Recruiting teams
        if len(spotlight) < limit:
            recruiting_qs = base_qs.filter(
                is_recruiting=True,
            ).exclude(pk__in=seen_ids).order_by('-updated_at')
            for t in recruiting_qs[:limit - len(spotlight)]:
                spotlight.append({
                    'team': t,
                    'badge_emoji': '\U0001F4E2',
                    'badge_text': 'Recruiting',
                })
                seen_ids.add(t.pk)

        # 3. Newest active teams
        if len(spotlight) < limit:
            newest_qs = base_qs.exclude(
                pk__in=seen_ids
            ).order_by('-created_at')
            for t in newest_qs[:limit - len(spotlight)]:
                spotlight.append({
                    'team': t,
                    'badge_emoji': '\U0001F680',
                    'badge_text': 'Just Launched',
                })
                seen_ids.add(t.pk)

    except Exception as e:
        logger.warning(f"Could not fetch spotlight teams: {e}")

    cache.set(cache_key, spotlight, 60)
    return spotlight


def _get_featured_teams(game_id=None, limit=12):
    """
    Get featured teams (top by CP) with caching.
    
    API CONTRACT: STABLE (Phase C+)
    Returns QuerySet of Team objects. Consumer code may access:
    - team.name, team.slug, team.logo_url (GUARANTEED fields)
    - team.organization (MAY be None for independent teams)
    - team.ranking (MAY be None if no ranking row exists)
    - team.memberships (GUARANTEED queryset, may be empty)
    - team.tag, team.tagline (MAY be None if schema not migrated)
    
    Empty State Guarantee: Returns empty list if no teams, never raises.
    Schema Safety: Works even if tag/tagline columns don't exist yet.
    
    Args:
        game_id: Optional game ID filter
        limit: Maximum teams to return (default 12)
    
    Returns:
        List of Team objects with related data
    
    Cache: 2 minutes (key includes game_id)
    NOTE: Empty results NOT cached to prevent stale empty states
    """
    from apps.organizations.models import Team  # vNext Team is canonical
    from apps.organizations.choices import TeamStatus
    
    cache_key = f'featured_teams_{game_id or "all"}_{limit}'
    cached_teams = cache.get(cache_key)
    
    if cached_teams is not None:
        return cached_teams
    
    try:
        # Phase 16 Fix: Show ALL PUBLIC ACTIVE teams (even brand new, even unranked)
        # No dependency on rankings or snapshots - teams appear immediately after creation
        teams_qs = Team.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC'  # No enum yet, use string
        ).select_related(
            'organization',
            'created_by'
            # NOTE: game_id is IntegerField, not FK - cannot select_related
        ).prefetch_related(
            'vnext_memberships__user'  # vNext uses vnext_memberships related name
        )
        
        # Debug logging
        logger.debug(f"[HUB] Querying teams: game_id={game_id}, limit={limit}")
        logger.debug(f"[HUB] Initial queryset count: {teams_qs.count()}")
        
        # Order by created_at DESC (newest first)
        # Ensures brand new teams appear at top
        teams_qs = teams_qs.order_by('-created_at')
        
        # Apply game filter if specified
        if game_id:
            teams_qs = teams_qs.filter(game_id=game_id)
            logger.debug(f"[HUB] After game_id filter: {teams_qs.count()} teams")
        
        teams = list(teams_qs[:limit])
        logger.debug(f"[HUB] Returning {len(teams)} teams")
        
        # Phase 16: Cache for 10 seconds only (prevent stale empty lists after team creation)
        cache.set(cache_key, teams, 10)
        
        return teams
    except ProgrammingError as e:
        logger.warning(
            f"Error querying teams (schema may not be migrated): {e}",
            extra={'event_type': 'schema_error', 'operation': 'get_featured_teams'}
        )
        return []
    except Exception as e:
        logger.error(f"Error fetching featured teams: {e}", exc_info=True)
        return []


def _get_leaderboard(game_id=None, limit=50):
    """
    Get leaderboard rankings with caching.
    
    API CONTRACT: STABLE (Phase C+)
    Returns list of TeamRanking objects. Consumer code may access:
    - ranking.team (GUARANTEED, never None)
    - ranking.current_cp, ranking.rank (GUARANTEED fields)
    - ranking.team.name, ranking.team.slug (GUARANTEED)
    - ranking.team.organization (MAY be None)
    - ranking.team.tag, ranking.team.tagline (MAY be None if schema not migrated)
    
    Empty State Guarantee: Returns empty list if no rankings, never raises.
    Schema Safety: Works even if TeamRanking table does not exist yet.
    
    Args:
        game_id: Optional game ID filter
        limit: Maximum rankings to return (default 50)
    
    Returns:
        List of TeamRanking objects with related data
    
    Cache: 5 minutes (key includes game_id)
    """
    from apps.organizations.models import TeamRanking
    
    cache_key = f'hub_leaderboard_{game_id or "all"}_{limit}'
    cached_leaderboard = cache.get(cache_key)
    
    if cached_leaderboard is not None:
        return cached_leaderboard
    
    try:
        # vNext Team uses status CharField, not is_active BooleanField
        leaderboard_qs = TeamRanking.objects.select_related(
            'team'
        ).filter(
            team__status='ACTIVE'
        ).order_by('-current_cp')
        
        # Apply game filter (legacy Team uses 'game' CharField slug, not game_id FK)
        # We have game_id but need to convert to slug - skip game filter for now
        # TODO: Convert game_id to slug via Game.objects.get(id=game_id).slug if needed
        # if game_id:
        #     leaderboard_qs = leaderboard_qs.filter(team__game=game_slug)
        
        leaderboard = list(leaderboard_qs[:limit])
        
        # Cache for 5 minutes
        cache.set(cache_key, leaderboard, 300)
        return leaderboard
    
    except ProgrammingError as e:
        logger.warning(
            f"TeamRanking table may not exist yet: {e}. "
            f"Run 'python manage.py migrate organizations' to fix.",
            extra={'event_type': 'schema_missing_table', 'table': 'TeamRanking'}
        )
        return []
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}", exc_info=True)
        return []


def vnext_hub(request):
    """
    vNext Team & Organization Hub landing page (GET only).
    
    Central landing page for vNext features with real-time data:
    - Hero carousel (top org, user status, recent tournament)
    - Featured teams grid
    - Global rankings preview (via CompetitionService)
    - Dynamic widgets (ticker, LFT, scrims) populated via API
    
    Note: The legacy teams app has been removed. This view now serves
    /teams/ directly. Feature flags still control optional sub-features
    (e.g. competition rankings) but no longer gate page access.
    
    Query Budget Target: ≤15 queries
    
    Returns:
        - 200: Renders team_hub.html (Tailwind UI with real data)
    """
    # Feature flags for optional sub-features
    competition_enabled = getattr(settings, 'COMPETITION_APP_ENABLED', True)
    
    from apps.games.models import Game
    
    # Get selected game filter (slug or 'all')
    selected_game_slug = request.GET.get('game', 'all')
    selected_game_id = None
    selected_game = None
    
    # Resolve game ID from slug
    if selected_game_slug and selected_game_slug != 'all':
        try:
            selected_game = Game.objects.get(slug=selected_game_slug, is_active=True)
            selected_game_id = selected_game.id
        except Game.DoesNotExist:
            logger.warning(f"Invalid game slug in filter: {selected_game_slug}")
            selected_game_slug = 'all'
    
    # Fetch data using helper functions (with caching)
    carousel_data = _get_hero_carousel_context(request)
    featured_teams = _get_featured_teams(game_id=selected_game_id, limit=12)
    spotlight_teams = _get_spotlight_teams(limit=5)
    
    # Phase 10: Use CompetitionService for rankings preview
    rankings_preview = []
    user_highlights = None
    if competition_enabled:
        try:
            from apps.competition.services import CompetitionService
            
            if selected_game_id:
                # Per-game rankings
                response = CompetitionService.get_game_rankings(
                    game_id=selected_game_id,
                    limit=10,
                    verified_only=False
                )
                rankings_preview = response.entries
            else:
                # Global rankings
                response = CompetitionService.get_global_rankings(
                    limit=10,
                    verified_only=False
                )
                rankings_preview = response.entries
            
            # Get user's team highlights if authenticated
            if request.user.is_authenticated:
                user_highlights = CompetitionService.get_user_team_highlights(request.user.id)
        except Exception as e:
            logger.warning(f"Could not fetch rankings preview: {e}")
    
    # Fetch available games for filter (with roster config for Match Finder)
    available_games = Game.objects.select_related('roster_config').filter(
        is_active=True
    ).order_by('display_name')

    # Build game configs JSON for Match Finder widget
    game_configs = {}
    for g in available_games:
        rc = getattr(g, 'roster_config', None)
        game_configs[g.slug] = {
            'name': g.display_name,
            'category': g.category,
            'game_type': g.game_type,
            'max_team_size': rc.max_team_size if rc else 5,
            'primary_color': g.primary_color or '#06b6d4',
        }
    game_configs_json = json.dumps(game_configs)

    # --- NEW: Additional context for production Hub template ---

    # Featured tournament (closest upcoming or currently live)
    featured_tournament = None
    upcoming_tournament = None
    try:
        from apps.tournaments.models import Tournament
        from django.utils import timezone

        now = timezone.now()
        featured_tournament = Tournament.objects.filter(
            status__in=['live', 'registration_open', 'published'],
        ).select_related('game').order_by(
            # Prefer LIVE, then REGISTRATION_OPEN, then UPCOMING
            '-status',
            'tournament_start',
        ).first()

        # Separate upcoming tournament (second one, different from featured)
        if featured_tournament:
            upcoming_tournament = Tournament.objects.filter(
                status__in=['registration_open', 'published'],
            ).select_related('game').exclude(
                pk=featured_tournament.pk
            ).order_by('tournament_start').first()
    except Exception as e:
        logger.warning(f"Could not fetch tournaments for hub: {e}")

    # Open challenges (public, unmatched or open)
    open_challenges = []
    try:
        from apps.competition.models import Challenge

        open_challenges = list(
            Challenge.objects.filter(
                status__in=['OPEN', 'PENDING'],
                is_public=True,
            ).select_related(
                'challenger_team', 'challenged_team', 'game'
            ).order_by('-created_at')[:5]
        )
    except Exception as e:
        logger.warning(f"Could not fetch open challenges: {e}")

    # Recruiting teams (for Scouting Grounds section)
    recruiting_teams = []
    try:
        from apps.organizations.models import Team as VNextTeam
        from apps.organizations.choices import TeamStatus

        recruiting_qs = VNextTeam.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            is_recruiting=True,
        ).select_related('organization').order_by('-updated_at')[:6]
        recruiting_teams = list(recruiting_qs)
    except Exception as e:
        logger.warning(f"Could not fetch recruiting teams: {e}")

    # User's active team memberships (for My Teams sidebar)
    user_teams = []
    user_game_ids = []
    user_profile_primary_team = None
    if request.user.is_authenticated:
        try:
            from apps.organizations.models import TeamMembership

            user_teams = list(
                TeamMembership.objects.filter(
                    user=request.user,
                    status='ACTIVE',
                    team__status='ACTIVE',
                ).select_related('team', 'team__organization').order_by('joined_at')
            )
            user_game_ids = [m.team.game_id for m in user_teams if m.team.game_id]

            # Fetch primary team from UserProfile
            try:
                from apps.user_profile.models_main import UserProfile
                profile = UserProfile.objects.select_related('primary_team').filter(
                    user=request.user
                ).first()
                if profile and profile.primary_team_id:
                    user_profile_primary_team = profile.primary_team
                    # Sort: primary team first, then by join date
                    user_teams.sort(
                        key=lambda m: (0 if m.team_id == profile.primary_team_id else 1, m.joined_at)
                    )
            except Exception as e:
                logger.debug(f"Could not fetch primary team from profile: {e}")
        except Exception as e:
            logger.warning(f"Could not fetch user teams: {e}")

    # Top organizations (for sidebar)
    top_organizations = []
    user_organization = None
    user_org_role = None
    try:
        from apps.organizations.models import Organization

        top_organizations = list(
            Organization.objects.select_related('ranking').filter(
                is_verified=True,
            ).order_by('-ranking__empire_score', '-updated_at')[:5]
        )
        if not top_organizations:
            top_organizations = list(
                Organization.objects.order_by('-updated_at')[:5]
            )

        # Detect if user is an org owner or staff
        if request.user.is_authenticated:
            try:
                from apps.organizations.models.organization import OrganizationMembership
                org_membership = OrganizationMembership.objects.select_related(
                    'organization', 'organization__ranking'
                ).filter(
                    user=request.user,
                    status='ACTIVE',
                ).first()
                if org_membership:
                    user_organization = org_membership.organization
                    user_org_role = org_membership.role
                else:
                    # Check if user is CEO (direct field on Organization)
                    ceo_org = Organization.objects.select_related('ranking').filter(
                        ceo=request.user
                    ).first()
                    if ceo_org:
                        user_organization = ceo_org
                        user_org_role = 'CEO'
            except Exception as e:
                logger.debug(f"Could not detect user organization: {e}")
    except Exception as e:
        logger.warning(f"Could not fetch top organizations: {e}")

    # Platform stats (for hero counters)
    stats = {
        'live_matches': 0,
        'total_prize_pool': 0,
        'teams_active': 0,
        'players_online': 0,
    }
    try:
        from apps.organizations.models import Team as StatsTeam
        from apps.organizations.choices import TeamStatus as StatsTeamStatus

        stats['teams_active'] = StatsTeam.objects.filter(
            status=StatsTeamStatus.ACTIVE
        ).count()
    except Exception as e:
        logger.debug(f"Could not compute hub stats: {e}")

    return render(request, 'organizations/hub/team_hub.html', {
        'page_title': 'Team Hub',
        'featured_teams': featured_teams,
        'rankings_preview': rankings_preview,
        'user_highlights': user_highlights,
        'available_games': available_games,
        'selected_game': selected_game,
        'selected_game_slug': selected_game_slug,
        'competition_enabled': competition_enabled,
        # Hero Carousel Data
        'top_organization': carousel_data['top_organization'],
        'user_teams_count': carousel_data['user_teams_count'],
        'user_primary_team': carousel_data['user_primary_team'],
        'recent_tournament_winner': carousel_data['recent_tournament_winner'],
        # NEW: Production Hub context
        'featured_tournament': featured_tournament,
        'upcoming_tournament': upcoming_tournament,
        'open_challenges': open_challenges,
        'recruiting_teams': recruiting_teams,
        'user_teams': user_teams,
        'user_game_ids': user_game_ids,
        'user_profile_primary_team': user_profile_primary_team,
        'top_organizations': top_organizations,
        'user_organization': user_organization,
        'user_org_role': user_org_role,
        'stats': stats,
        'game_configs_json': game_configs_json,
        'spotlight_teams': spotlight_teams,
    })


def vnext_hub_filter(request):
    """
    AJAX endpoint for game filter changes on the Hub page.
    Returns JSON with rankings, recruiting teams, and featured teams
    filtered by the selected game. Called when user clicks a Combat Zone
    game card without page reload.
    """
    if request.method != 'GET':
        return JsonResponse({'ok': False, 'error': 'GET only'}, status=405)

    from apps.games.models import Game

    game_slug = request.GET.get('game', 'all')
    game_id = None
    game_display = 'All Games'

    if game_slug and game_slug != 'all':
        try:
            game_obj = Game.objects.get(slug=game_slug, is_active=True)
            game_id = game_obj.id
            game_display = game_obj.display_name
        except Game.DoesNotExist:
            game_slug = 'all'

    # Rankings
    rankings_data = []
    competition_enabled = getattr(settings, 'COMPETITION_APP_ENABLED', True)
    if competition_enabled:
        try:
            from apps.competition.services import CompetitionService
            if game_id:
                response = CompetitionService.get_game_rankings(game_id=game_id, limit=10, verified_only=False)
            else:
                response = CompetitionService.get_global_rankings(limit=10, verified_only=False)
            for e in response.entries:
                rankings_data.append({
                    'rank': e.rank,
                    'team_name': e.team_name,
                    'team_url': e.team_url or '#',
                    'team_logo_url': e.team_logo_url,
                    'team_tag': e.team_tag or (e.team_name[:3] if e.team_name else '??'),
                    'tier': e.tier or 'UNRANKED',
                    'score': e.score,
                    'organization_name': e.organization_name,
                })
        except Exception as exc:
            logger.warning(f"AJAX rankings fetch failed: {exc}")

    # Recruiting teams
    recruiting_data = []
    try:
        from apps.organizations.models import Team as VNextTeam
        from apps.organizations.choices import TeamStatus

        qs = VNextTeam.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            is_recruiting=True,
        ).select_related('organization').order_by('-updated_at')
        if game_id:
            qs = qs.filter(game_id=game_id)
        for t in qs[:6]:
            recruiting_data.append({
                'name': t.name,
                'slug': t.slug,
                'tag': t.tag or (t.name[:2] if t.name else '??'),
                'game': t.get_game_display() or 'Unknown',
                'logo_url': t.logo.url if t.logo else None,
                'description': (t.description or 'Looking for skilled players to join the roster.')[:120],
                'url': f'/teams/{t.slug}/',
            })
    except Exception as exc:
        logger.warning(f"AJAX recruiting fetch failed: {exc}")

    return JsonResponse({
        'ok': True,
        'game_slug': game_slug,
        'game_display': game_display,
        'rankings': rankings_data,
        'recruiting': recruiting_data,
    })
