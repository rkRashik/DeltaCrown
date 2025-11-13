"""
Admin Read-Only Leaderboards API.

Staff-only endpoints for leaderboard inspection with debug metadata.
All responses are PII-free (IDs + aggregates only).
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from apps.leaderboards.models import LeaderboardEntry, LeaderboardSnapshot
from apps.leaderboards.services import (
    get_tournament_leaderboard,
    get_scoped_leaderboard,
    _get_cache_key_tournament,
    _get_cache_key_season,
    _get_cache_key_all_time,
)
from apps.tournaments.models import Tournament

logger = logging.getLogger(__name__)


# ============================================================================
# Staff-Only Permission (Read-Only)
# ============================================================================

class IsStaffReadOnly:
    """
    Permission: Allow only staff/superuser for read-only operations.
    
    Usage:
        @permission_classes([IsStaffReadOnly])
        def my_view(request):
            ...
    """
    
    def has_permission(self, request, view):
        """Check if user is staff and method is safe."""
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must be staff or superuser
        if not (request.user.is_staff or request.user.is_superuser):
            return False
        
        # Must use safe methods only (GET, HEAD, OPTIONS)
        if request.method not in ['GET', 'HEAD', 'OPTIONS']:
            return False
        
        return True


# ============================================================================
# Admin Endpoints
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def tournament_leaderboard_debug(request, tournament_id: int):
    """
    Admin endpoint: Tournament leaderboard with debug metadata.
    
    Endpoint: GET /api/admin/leaderboards/tournaments/{tournament_id}/
    
    Permissions: Staff/Admin only (IsAdminUser)
    
    Response:
        {
            "tournament_id": 501,
            "source": "cache|snapshot|live|disabled",
            "as_of": "2025-11-13T14:30:00Z",
            "entries": [
                {
                    "rank": 1,
                    "player_id": 123,
                    "team_id": 45,
                    "points": 3000,
                    "wins": 15,
                    "losses": 2,
                    "win_rate": 88.24,
                    "matches_played": 17
                },
                ...
            ],
            "debug": {
                "cache_key": "lb:tournament:501",
                "cache_ttl_seconds": 300,
                "cache_hit": true,
                "computation_enabled": true,
                "cache_enabled": true,
                "api_enabled": true,
                "entry_count": 16,
                "query_time_ms": 12.5
            }
        }
    
    Errors:
        - 403: Not staff/admin
        - 404: Tournament not found
    
    Example:
        GET /api/admin/leaderboards/tournaments/501/
        Authorization: Token <admin_token>
    """
    # Check feature flags
    compute_enabled = getattr(settings, "LEADERBOARDS_COMPUTE_ENABLED", False)
    cache_enabled = getattr(settings, "LEADERBOARDS_CACHE_ENABLED", False)
    api_enabled = getattr(settings, "LEADERBOARDS_API_ENABLED", False)
    
    # Validate tournament exists
    try:
        tournament = Tournament.objects.get(id=tournament_id, is_deleted=False)
    except Tournament.DoesNotExist:
        return JsonResponse(
            {"error": f"Tournament {tournament_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Track query time
    start_time = datetime.utcnow()
    
    # Check cache first (if enabled)
    cache_key = _get_cache_key_tournament(tournament_id)
    cache_hit = False
    cache_ttl = None
    source = "disabled"
    
    if cache_enabled:
        cached = cache.get(cache_key)
        if cached:
            cache_hit = True
            source = "cache"
            # Try to get TTL (Redis-specific)
            try:
                import redis
                from django.core.cache.backends.redis import RedisCache
                if isinstance(cache, RedisCache):
                    client = cache._cache.get_client()
                    cache_ttl = client.ttl(cache_key)
            except:
                cache_ttl = 300  # Default TTL
    
    # Query service layer
    if compute_enabled:
        response_dto = get_tournament_leaderboard(tournament_id)
        entries = [entry.to_dict() for entry in response_dto.entries]
        
        if not cache_hit:
            source = "live" if entries else "snapshot"
    else:
        entries = []
        source = "disabled"
    
    # Calculate query time
    query_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # Build response
    response_data = {
        "tournament_id": tournament_id,
        "source": source,
        "as_of": datetime.utcnow().isoformat() + "Z",
        "entries": entries,
        "debug": {
            "cache_key": cache_key,
            "cache_ttl_seconds": cache_ttl,
            "cache_hit": cache_hit,
            "computation_enabled": compute_enabled,
            "cache_enabled": cache_enabled,
            "api_enabled": api_enabled,
            "entry_count": len(entries),
            "query_time_ms": round(query_time_ms, 2),
        }
    }
    
    return JsonResponse(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def snapshot_detail(request, snapshot_id: int):
    """
    Admin endpoint: Leaderboard snapshot metadata.
    
    Endpoint: GET /api/admin/leaderboards/snapshots/{snapshot_id}/
    
    Permissions: Staff/Admin only (IsAdminUser)
    
    Response:
        {
            "snapshot_id": 123,
            "tournament_id": 501,
            "scope": "tournament",
            "game_code": "valorant",
            "season_id": null,
            "created_at": "2025-11-13T00:00:00Z",
            "payload_version": "v1",
            "entry_count": 16
        }
    
    Errors:
        - 403: Not staff/admin
        - 404: Snapshot not found
    
    Example:
        GET /api/admin/leaderboards/snapshots/123/
        Authorization: Token <admin_token>
    """
    try:
        snapshot = LeaderboardSnapshot.objects.get(id=snapshot_id)
    except LeaderboardSnapshot.DoesNotExist:
        return JsonResponse(
            {"error": f"Snapshot {snapshot_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Build response (IDs only, no PII)
    response_data = {
        "snapshot_id": snapshot.id,
        "date": snapshot.date.isoformat(),
        "leaderboard_type": snapshot.leaderboard_type,
        "player_id": snapshot.player_id,
        "team_id": snapshot.team_id,
        "rank": snapshot.rank,
        "points": snapshot.points,
        "created_at": snapshot.date.isoformat(),
    }
    
    return JsonResponse(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def scoped_leaderboard_debug(request, scope: str):
    """
    Admin endpoint: Scoped leaderboard with debug metadata.
    
    Endpoint: GET /api/admin/leaderboards/scoped/{scope}/?game_code=valorant&season_id=2025_S1
    
    URL Parameters:
        scope: "season" or "all_time"
    
    Query Parameters:
        game_code: Optional game filter (e.g., "valorant", "cs2")
        season_id: Required for scope="season"
    
    Permissions: Staff/Admin only (IsAdminUser)
    
    Response:
        {
            "scope": "season",
            "season_id": "2025_S1",
            "game_code": "valorant",
            "entry_count": 50,
            "as_of": "2025-11-13T14:30:00Z",
            "entries": [...],
            "debug": {
                "cache_key": "lb:season:2025_S1:valorant",
                "cache_ttl_seconds": 3600,
                "cache_hit": false,
                "computation_enabled": true,
                "cache_enabled": true,
                "query_time_ms": 25.3
            }
        }
    
    Errors:
        - 400: Invalid scope or missing season_id
        - 403: Not staff/admin
    
    Example:
        GET /api/admin/leaderboards/scoped/season/?season_id=2025_S1&game_code=valorant
        Authorization: Token <admin_token>
    """
    # Check feature flags
    compute_enabled = getattr(settings, "LEADERBOARDS_COMPUTE_ENABLED", False)
    cache_enabled = getattr(settings, "LEADERBOARDS_CACHE_ENABLED", False)
    
    # Validate scope
    if scope not in ["season", "all_time"]:
        return JsonResponse(
            {"error": f"Invalid scope '{scope}'. Must be 'season' or 'all_time'"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Parse query parameters
    game_code = request.query_params.get('game_code')
    season_id = request.query_params.get('season_id')
    
    # Validate season_id for scope="season"
    if scope == "season" and not season_id:
        return JsonResponse(
            {"error": "season_id query parameter is required for scope='season'"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Generate cache key
    if scope == "season":
        cache_key = _get_cache_key_season(season_id, game_code)
        cache_ttl = 3600  # 1 hour
    else:
        cache_key = _get_cache_key_all_time(game_code)
        cache_ttl = 86400  # 24 hours
    
    # Track query time
    start_time = datetime.utcnow()
    
    # Check cache
    cache_hit = False
    if cache_enabled:
        cached = cache.get(cache_key)
        if cached:
            cache_hit = True
    
    # Query service layer
    if compute_enabled:
        try:
            response_dto = get_scoped_leaderboard(
                scope=scope,
                game_code=game_code,
                season_id=season_id
            )
            entries = [entry.to_dict() for entry in response_dto.entries]
        except ValueError as e:
            return JsonResponse(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        entries = []
    
    # Calculate query time
    query_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # Build response
    response_data = {
        "scope": scope,
        "season_id": season_id,
        "game_code": game_code,
        "entry_count": len(entries),
        "as_of": datetime.utcnow().isoformat() + "Z",
        "entries": entries,
        "debug": {
            "cache_key": cache_key,
            "cache_ttl_seconds": cache_ttl,
            "cache_hit": cache_hit,
            "computation_enabled": compute_enabled,
            "cache_enabled": cache_enabled,
            "query_time_ms": round(query_time_ms, 2),
        }
    }
    
    return JsonResponse(response_data, status=status.HTTP_200_OK)
