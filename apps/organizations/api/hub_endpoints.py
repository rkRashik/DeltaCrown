"""
JSON endpoints for vNext Hub live widgets.

These are lightweight endpoints that provide data for:
- Live ticker (match results, transfers, news)
- Scout radar (trending players looking for team)
- Scrim finder (active scrim requests)
- Team search (autocomplete)

Phase C+: Full implementation with real data, caching, and consistent schemas.

All endpoints return consistent JSON schema:
{
    "ok": true/false,
    "error_code": str (if error),
    "safe_message": str (if error),
    "data": {...} (if success)
}
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import models
from datetime import timedelta

logger = logging.getLogger(__name__)




@require_http_methods(["GET"])
def ticker_feed(request):
    """
    Live ticker feed for hub page.
    
    Returns recent events merged from:
    - Recent ranking changes (TeamRanking updated in last 7 days)
    - Recent team created (Team.created_at last 7 days)
    - Recent membership joined (TeamMembership created_at last 7 days)
    - Recent match outcomes (if tournaments/matches exist)
    
    Cache: 30 seconds
    
    Returns:
        JSON: {
            "ok": true,
            "data": {
                "items": [
                    {
                        "type": "rank_change|team_created|member_joined|match_result",
                        "timestamp": "ISO8601",
                        "title": str,
                        "subtitle": str,
                        "team_slug": str (optional),
                        "team_url": str (optional)
                    }
                ]
            }
        }
    """
    cache_key = 'hub_ticker_feed'
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return JsonResponse(cached_data)
    
    try:
        from apps.organizations.models import Team, TeamRanking, TeamMembership
        
        cutoff_date = timezone.now() - timedelta(days=7)
        items = []
        
        # 1. Recent ranking changes
        try:
            ranking_changes = TeamRanking.objects.filter(
                updated_at__gte=cutoff_date,
                previous_rank__isnull=False
            ).select_related('team').exclude(
                global_rank=models.F('previous_rank')
            ).order_by('-updated_at')[:5]
            
            for ranking in ranking_changes:
                direction = 'up' if ranking.global_rank < ranking.previous_rank else 'down'
                items.append({
                    'type': 'rank_change',
                    'timestamp': ranking.updated_at.isoformat(),
                    'title': f"{ranking.team.name} climbed to #{ranking.global_rank}" if direction == 'up' else f"{ranking.team.name} dropped to #{ranking.global_rank}",
                    'subtitle': f"From #{ranking.previous_rank}",
                    'team_slug': ranking.team.slug,
                    'team_url': ranking.team.get_absolute_url(),
                })
        except Exception as e:
            logger.warning(f"Could not fetch ranking changes: {e}")
        
        # 2. Recently created teams
        try:
            recent_teams = Team.objects.filter(
                created_at__gte=cutoff_date,
                status='ACTIVE'
            ).select_related('owner').order_by('-created_at')[:5]
            
            for team in recent_teams:
                items.append({
                    'type': 'team_created',
                    'timestamp': team.created_at.isoformat(),
                    'title': f"New squad formed: {team.name}",
                    'subtitle': f"Founded by {team.owner.username}" if team.owner else "New competitive team",
                    'team_slug': team.slug,
                    'team_url': team.get_absolute_url(),
                })
        except Exception as e:
            logger.warning(f"Could not fetch recent teams: {e}")
        
        # 3. Recent team member joins
        try:
            recent_joins = TeamMembership.objects.filter(
                joined_at__gte=cutoff_date,
                status='ACTIVE'
            ).select_related('team', 'user').order_by('-joined_at')[:5]
            
            for membership in recent_joins:
                items.append({
                    'type': 'member_joined',
                    'timestamp': membership.joined_at.isoformat(),
                    'title': f"{membership.user.username} joined {membership.team.name}",
                    'subtitle': f"As {membership.role}",
                    'team_slug': membership.team.slug,
                    'team_url': membership.team.get_absolute_url(),
                })
        except Exception as e:
            logger.warning(f"Could not fetch recent joins: {e}")
        
        # 4. Recent match results (optional - guarded by import)
        try:
            from apps.matches.models import Match
            recent_matches = Match.objects.filter(
                status='COMPLETED',
                completed_at__gte=cutoff_date
            ).select_related('team_a', 'team_b', 'tournament').order_by('-completed_at')[:3]
            
            for match in recent_matches:
                if match.team_a and match.team_b:
                    winner = match.team_a if match.score_team_a > match.score_team_b else match.team_b
                    items.append({
                        'type': 'match_result',
                        'timestamp': match.completed_at.isoformat(),
                        'title': f"{match.team_a.name} {match.score_team_a}-{match.score_team_b} {match.team_b.name}",
                        'subtitle': match.tournament.name if match.tournament else "Competitive Match",
                        'team_slug': winner.slug,
                        'team_url': winner.get_absolute_url(),
                    })
        except ImportError:
            # Match model doesn't exist - skip
            pass
        except Exception as e:
            logger.warning(f"Could not fetch recent matches: {e}")
        
        # Sort by timestamp (most recent first) and limit to 15
        items.sort(key=lambda x: x['timestamp'], reverse=True)
        items = items[:15]
        
        response_data = {
            'ok': True,
            'data': {
                'items': items
            }
        }
        
        # Cache for 30 seconds
        cache.set(cache_key, response_data, 30)
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Ticker feed error: {e}", exc_info=True)
        return JsonResponse({
            'ok': False,
            'error_code': 'TICKER_QUERY_FAILED',
            'safe_message': 'Unable to load activity feed',
            'data': {'items': []}
        })




@require_http_methods(["GET"])
@login_required
def scout_radar(request):
    """
    Scout radar - players looking for team (LFT).
    
    Returns list of players who marked themselves as LFT.
    If LFT field doesn't exist yet, returns empty list gracefully.
    
    Cache: 60 seconds
    
    Query params:
        - game: Filter by game slug
        - limit: Max results (default 20)
    
    Returns:
        JSON: {
            "ok": true,
            "data": {
                "players": [
                    {
                        "display_name": str,
                        "username": str,
                        "game_id": int (optional),
                        "region": str (optional),
                        "role": str (optional),
                        "profile_url": str,
                        "avatar_url": str (optional)
                    }
                ]
            }
        }
    """
    game_filter = request.GET.get('game', None)
    limit = min(int(request.GET.get('limit', 20)), 50)  # Max 50
    
    cache_key = f'scout_radar_{game_filter}_{limit}'
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return JsonResponse(cached_data)
    
    try:
        from apps.user_profile.models import UserProfile
        
        # Check if UserProfile has is_lft field
        if not hasattr(UserProfile, 'is_lft'):
            # Field doesn't exist - return empty list gracefully
            response_data = {
                'ok': True,
                'data': {
                    'players': []
                }
            }
            cache.set(cache_key, response_data, 60)
            return JsonResponse(response_data)
        
        # Query LFT players
        lft_profiles = UserProfile.objects.filter(
            is_lft=True
        ).select_related('user')[:limit]
        
        players = []
        for profile in lft_profiles:
            players.append({
                'display_name': profile.display_name or profile.user.username,
                'username': profile.user.username,
                'game_id': getattr(profile, 'primary_game_id', None),
                'region': getattr(profile, 'region', 'Unknown'),
                'role': getattr(profile, 'preferred_role', 'Flex'),
                'profile_url': f'/profile/{profile.user.username}/',
                'avatar_url': profile.avatar.url if profile.avatar else None,
            })
        
        response_data = {
            'ok': True,
            'data': {
                'players': players
            }
        }
        
        # Cache for 60 seconds
        cache.set(cache_key, response_data, 60)
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Scout radar error: {e}", exc_info=True)
        return JsonResponse({
            'ok': False,
            'error_code': 'LFT_QUERY_FAILED',
            'safe_message': 'Scout radar temporarily unavailable',
            'data': {'players': []}
        })


@require_http_methods(["GET"])
@login_required
def active_scrims(request):
    """
    Active scrim requests for scrim finder widget.
    
    Returns list of teams looking for scrimmage matches.
    If ScrimRequest model doesn't exist, returns empty list gracefully.
    
    Cache: 30 seconds
    
    Query params:
        - game: Filter by game slug
        - region: Filter by region
        - limit: Max results (default 20)
    
    Returns:
        JSON: {
            "ok": true,
            "data": {
                "scrims": [
                    {
                        "title": str,
                        "game_id": int,
                        "region": str,
                        "start_time": str (ISO8601),
                        "format": str,
                        "url": str
                    }
                ]
            }
        }
    """
    game_filter = request.GET.get('game', None)
    region_filter = request.GET.get('region', None)
    limit = min(int(request.GET.get('limit', 20)), 50)  # Max 50
    
    cache_key = f'active_scrims_{game_filter}_{region_filter}_{limit}'
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return JsonResponse(cached_data)
    
    try:
        # Attempt to import ScrimRequest model if it exists
        try:
            from apps.organizations.models import ScrimRequest
            
            # Query active scrim requests
            scrims_qs = ScrimRequest.objects.filter(
                status='ACTIVE',
                expires_at__gt=timezone.now()
            ).select_related('team', 'game')
            
            if game_filter:
                scrims_qs = scrims_qs.filter(game__slug=game_filter)
            
            if region_filter:
                scrims_qs = scrims_qs.filter(region=region_filter)
            
            scrims_qs = scrims_qs.order_by('-created_at')[:limit]
            
            scrims = []
            for scrim in scrims_qs:
                scrims.append({
                    'title': f"{scrim.team.name} looking for scrim",
                    'game_id': scrim.game.id if scrim.game else None,
                    'region': scrim.region or 'Any',
                    'start_time': scrim.preferred_time.isoformat() if scrim.preferred_time else None,
                    'format': getattr(scrim, 'format', '5v5'),
                    'url': scrim.team.get_absolute_url(),
                })
            
            response_data = {
                'ok': True,
                'data': {
                    'scrims': scrims
                }
            }
            
        except ImportError:
            # ScrimRequest model doesn't exist - return empty gracefully
            response_data = {
                'ok': True,
                'data': {
                    'scrims': []
                }
            }
        
        # Cache for 30 seconds
        cache.set(cache_key, response_data, 30)
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Active scrims error: {e}", exc_info=True)
        return JsonResponse({
            'ok': False,
            'error_code': 'SCRIM_QUERY_FAILED',
            'safe_message': 'Scrim finder temporarily unavailable',
            'data': {'scrims': []}
        })


@require_http_methods(["GET"])
@login_required
def team_search(request):
    """
    Team search autocomplete for hub search bar.
    
    Returns teams matching search query with consistent schema.
    
    Query params:
        - q: Search query (team name) - minimum 2 characters
        - limit: Max results (default 10, max 20)
    
    Returns:
        JSON: {
            "ok": true,
            "data": {
                "teams": [
                    {
                        "slug": str,
                        "name": str,
                        "logo": str (optional),
                        "tier": str,
                        "cp": int,
                        "url": str
                    }
                ]
            }
        }
        
        OR (if query too short):
        JSON: {
            "ok": false,
            "error_code": "QUERY_TOO_SHORT",
            "safe_message": "Search requires at least 2 characters",
            "data": {"teams": []}
        }
    """
    from apps.organizations.models import Team
    from apps.games.models import Game
    
    query = request.GET.get('q', '').strip()
    limit = min(int(request.GET.get('limit', 10)), 20)  # Max 20
    
    # Validate minimum length
    if not query or len(query) < 2:
        return JsonResponse({
            'ok': False,
            'error_code': 'QUERY_TOO_SHORT',
            'safe_message': 'Search requires at least 2 characters',
            'data': {'teams': []}
        }, status=400)
    
    try:
        # Search teams by name
        teams = Team.objects.filter(
            name__icontains=query,
            status='ACTIVE'
        ).select_related(
            'organization',
            'ranking'
        ).order_by('-ranking__current_cp')[:limit]
        
        # Get game names map (cached)
        game_names_cache_key = 'game_names_map'
        game_names = cache.get(game_names_cache_key)
        if game_names is None:
            game_names = {g.id: g.display_name for g in Game.objects.filter(is_active=True)}
            cache.set(game_names_cache_key, game_names, 300)  # 5 minutes
        
        results = []
        for team in teams:
            results.append({
                'slug': team.slug,
                'name': team.name,
                'logo': team.logo.url if team.logo else None,
                'tier': team.ranking.tier if hasattr(team, 'ranking') and team.ranking else 'UNRANKED',
                'cp': team.ranking.current_cp if hasattr(team, 'ranking') and team.ranking else 0,
                'url': team.get_absolute_url(),
            })
        
        return JsonResponse({
            'ok': True,
            'data': {
                'teams': results
            }
        })
        
    except Exception as e:
        logger.error(f"Team search error: {e}", exc_info=True)
        return JsonResponse({
            'ok': False,
            'error_code': 'SEARCH_QUERY_FAILED',
            'safe_message': 'Search temporarily unavailable',
            'data': {'teams': []}
        }, status=500)


