"""
Milestone E: Leaderboard & Standings API

REST API endpoints for tournament leaderboards and standings.
Delegates all business logic to LeaderboardService (ADR-001: Service Layer Pattern).

Phase E Enhancements (Sections 2-4):
- NEW: GET /api/tournaments/leaderboards/tournament/{id}/ - Read-only leaderboard queries
- NEW: GET /api/tournaments/leaderboards/player/{id}/history/ - Player historical stats
- NEW: GET /api/tournaments/leaderboards/{scope}/ - Seasonal/all-time rankings

Original Endpoints (Preserved):
1. GET /api/tournaments/{id}/leaderboard/ - BR leaderboard (Free Fire, PUBG Mobile)
2. GET /api/tournaments/{id}/series/{match_id}/ - Series summary (Valorant, CS2, etc.)
3. POST /api/tournaments/{id}/override-placement/ - Staff placement override

Architecture:
- ADR-001: Service Layer (delegates to apps.leaderboards.services)
- ADR-005: Security (JWT auth, role-based permissions, audit logging)
- Module 2.4: Audit logging for staff overrides

Feature Flags:
- LEADERBOARDS_API_ENABLED: Enable Phase E leaderboard endpoints (default: False)
- LEADERBOARDS_COMPUTE_ENABLED: Enable computation backend (default: False)
- LEADERBOARDS_CACHE_ENABLED: Enable Redis caching (default: False)

Planning Documents:
- Documents/ExecutionPlan/MILESTONES_E_F_PLAN.md
- Documents/ExecutionPlan/MILESTONES_E_F_STATUS.md
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError, NotFound
from django.utils import timezone

from apps.tournaments.models import Tournament, Registration, Match
from apps.tournaments.services.leaderboard import LeaderboardService
from apps.tournaments.api.leaderboard_serializers import (
    BRLeaderboardSerializer,
    SeriesSummarySerializer,
    PlacementOverrideSerializer,
    PlacementOverrideResponseSerializer
)
from apps.tournaments.api.permissions import IsOrganizerOrAdmin

# Phase E imports
from apps.leaderboards.services import (
    get_tournament_leaderboard,
    get_player_leaderboard_history,
    get_scoped_leaderboard,
)

# Phase F imports
from apps.leaderboards.engine import RankingEngine

logger = logging.getLogger(__name__)


# ============================================================================
# Phase E: Read-Only Leaderboard Endpoints (PII-Free)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tournament_leaderboard(request, tournament_id):
    """
    Get tournament leaderboard (Phase E + Phase F).
    
    Endpoint: GET /api/tournaments/leaderboards/tournament/{tournament_id}/
    
    Permissions: IsAuthenticated (public read for registered users)
    
    Phase F Enhancement:
        - If LEADERBOARDS_ENGINE_V2_ENABLED=True: Use RankingEngine (fast compute + deltas)
        - Else: Fall back to Phase E service layer
    
    Behavior:
        - If LEADERBOARDS_API_ENABLED=False: Returns 404 (feature disabled)
        - If ENGINE_V2_ENABLED=True: Use RankingEngine.compute_tournament_rankings()
        - If COMPUTE_ENABLED=False: Returns empty list with metadata
        - If CACHE_ENABLED=True: Check Redis first (TTL 30s for engine_v2, 5min for legacy)
        - Returns PII-free DTOs (IDs + aggregates only)
    
    Response (Engine V2):
        {
            "scope": "tournament",
            "rankings": [
                {
                    "rank": 1,
                    "participant_id": 123,
                    "team_id": 45,
                    "points": 3000,
                    "kills": 45,
                    "wins": 15,
                    "losses": 2,
                    "matches_played": 17,
                    "earliest_win": "2025-11-10T12:30:00Z",
                    "win_rate": 88.24,
                    "last_updated": "2025-11-13T14:30:00Z"
                },
                ...
            ],
            "deltas": [
                {
                    "participant_id": 456,
                    "previous_rank": 5,
                    "current_rank": 3,
                    "rank_change": -2,
                    "points": 2800,
                    "last_updated": "2025-11-13T14:30:00Z"
                },
                ...
            ],
            "metadata": {
                "tournament_id": 501,
                "source": "engine_v2",
                "cache_hit": true,
                "count": 16,
                "delta_count": 5,
                "duration_ms": 45,
                "computed_at": "2025-11-13T14:30:00Z"
            }
        }
    
    Errors:
        - 404: Feature disabled or tournament not found
        - 401: Unauthenticated
    
    Example:
        GET /api/tournaments/leaderboards/tournament/501/
        Authorization: Bearer <jwt_token>
    """
    # Check feature flag
    if not getattr(settings, "LEADERBOARDS_API_ENABLED", False):
        raise NotFound("Leaderboards API is currently disabled")
    
    # Validate tournament exists
    try:
        tournament = Tournament.objects.get(id=tournament_id, is_deleted=False)
    except Tournament.DoesNotExist:
        raise NotFound(f"Tournament {tournament_id} not found")
    
    # Phase F: Check if Engine V2 is enabled
    engine_v2_enabled = getattr(settings, "LEADERBOARDS_ENGINE_V2_ENABLED", False)
    
    if engine_v2_enabled:
        # Use Engine V2 (fast compute + rank deltas)
        engine = RankingEngine(cache_ttl=30)  # 30s TTL for fast spectator updates
        response_dto = engine.compute_tournament_rankings(tournament_id, use_cache=True)
        
        return Response(response_dto.to_dict(), status=status.HTTP_200_OK)
    else:
        # Fall back to Phase E service layer (legacy)
        response_dto = get_tournament_leaderboard(tournament_id)
        
        return Response(response_dto.to_dict(), status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def player_leaderboard_history(request, player_id):
    """
    Get player's leaderboard history (Phase E).
    
    Endpoint: GET /api/tournaments/leaderboards/player/{player_id}/history/
    
    Permissions: IsAuthenticated (players can view their own + others)
    
    Behavior:
        - If LEADERBOARDS_API_ENABLED=False: Returns 404
        - If COMPUTE_ENABLED=False: Returns empty snapshots
        - If CACHE_ENABLED=True: Check Redis first (TTL 1h)
        - Returns historical rank/points snapshots (most recent first)
    
    Response:
        {
            "player_id": 456,
            "history": [
                {
                    "date": "2025-11-13",
                    "rank": 5,
                    "points": 2600,
                    "leaderboard_type": "season"
                },
                {
                    "date": "2025-11-12",
                    "rank": 6,
                    "points": 2400,
                    "leaderboard_type": "season"
                },
                ...
            ],
            "count": 15
        }
    
    Errors:
        - 404: Feature disabled or player not found
        - 401: Unauthenticated
    
    Example:
        GET /api/tournaments/leaderboards/player/456/history/
        Authorization: Bearer <jwt_token>
    """
    # Check feature flag
    if not getattr(settings, "LEADERBOARDS_API_ENABLED", False):
        raise NotFound("Leaderboards API is currently disabled")
    
    # Delegate to service layer (no validation needed, empty list if player doesn't exist)
    response_dto = get_player_leaderboard_history(player_id)
    
    return Response(response_dto.to_dict(), status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scoped_leaderboard(request, scope):
    """
    Get scoped leaderboard (season or all-time, Phase E + Phase F).
    
    Endpoint: GET /api/tournaments/leaderboards/{scope}/?game_code=valorant&season_id=2025_S1
    
    URL Parameters:
        scope: "season" or "all_time"
    
    Query Parameters:
        game_code: Optional game filter (e.g., "valorant", "cs2", "lol")
        season_id: Required for scope="season" (e.g., "2025_S1")
    
    Permissions: IsAuthenticated (public read for registered users)
    
    Phase F Enhancement:
        - If LEADERBOARDS_ENGINE_V2_ENABLED=True: Use RankingEngine for season rankings
        - All-time always uses Engine V2 snapshots (no live compute)
        - Else: Fall back to Phase E service layer
    
    Behavior:
        - If LEADERBOARDS_API_ENABLED=False: Returns 404
        - If scope="season" but season_id missing: Returns 400
        - If scope not in ["season", "all_time"]: Returns 400
        - If CACHE_ENABLED=True: Check Redis first (TTL 1h for season, 24h for all-time)
    
    Response (Engine V2):
        {
            "scope": "season",
            "rankings": [
                {
                    "rank": 1,
                    "participant_id": 789,
                    "team_id": null,
                    "points": 5000,
                    "kills": 120,
                    "wins": 30,
                    "losses": 5,
                    "matches_played": 35,
                    "earliest_win": "2025-09-01T10:00:00Z",
                    "win_rate": 85.71,
                    "last_updated": "2025-11-13T12:00:00Z"
                },
                ...
            ],
            "deltas": [
                {
                    "participant_id": 456,
                    "previous_rank": 8,
                    "current_rank": 5,
                    "rank_change": -3,
                    "points": 4200,
                    "last_updated": "2025-11-13T12:00:00Z"
                },
                ...
            ],
            "metadata": {
                "season_id": "2025_S1",
                "game_code": "valorant",
                "source": "engine_v2",
                "cache_hit": false,
                "count": 50,
                "delta_count": 12,
                "duration_ms": 1850,
                "computed_at": "2025-11-13T14:30:00Z"
            }
        }
    
    Errors:
        - 400: Invalid scope or missing season_id
        - 404: Feature disabled
        - 401: Unauthenticated
    
    Examples:
        GET /api/tournaments/leaderboards/season/?season_id=2025_S1&game_code=valorant
        GET /api/tournaments/leaderboards/all_time/
        GET /api/tournaments/leaderboards/all_time/?game_code=cs2
    """
    # Check feature flag
    if not getattr(settings, "LEADERBOARDS_API_ENABLED", False):
        raise NotFound("Leaderboards API is currently disabled")
    
    # Validate scope
    if scope not in ["season", "all_time"]:
        return Response(
            {"error": f"Invalid scope '{scope}'. Must be 'season' or 'all_time'"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Parse query parameters
    game_code = request.query_params.get('game_code')
    season_id = request.query_params.get('season_id')
    
    # Validate season_id for scope="season"
    if scope == "season" and not season_id:
        return Response(
            {"error": "season_id query parameter is required for scope='season'"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Phase F: Check if Engine V2 is enabled
    engine_v2_enabled = getattr(settings, "LEADERBOARDS_ENGINE_V2_ENABLED", False)
    
    if engine_v2_enabled:
        # Use Engine V2
        engine = RankingEngine(cache_ttl=3600)  # 1-hour TTL for season/all-time
        
        if scope == "season":
            response_dto = engine.compute_season_rankings(
                season_id=season_id,
                game_code=game_code,
                use_cache=True
            )
        else:  # all_time
            response_dto = engine.compute_all_time_rankings(game_code=game_code)
        
        return Response(response_dto.to_dict(), status=status.HTTP_200_OK)
    else:
        # Fall back to Phase E service layer (legacy)
        try:
            response_dto = get_scoped_leaderboard(
                scope=scope,
                game_code=game_code,
                season_id=season_id
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(response_dto.to_dict(), status=status.HTTP_200_OK)


class LeaderboardViewSet(viewsets.GenericViewSet):
    """
    ViewSet for tournament leaderboards and standings.
    
    All endpoints delegate to LeaderboardService for business logic.
    
    Permissions:
    - br_leaderboard: Authenticated (public read)
    - series_summary: Authenticated (public read)
    - override_placement: IsStaffOrAdmin (staff-only write)
    """
    
    queryset = Tournament.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    
    @action(
        detail=True,
        methods=['get'],
        url_path='leaderboard',
        permission_classes=[IsAuthenticated]
    )
    def br_leaderboard(self, request, pk=None):
        """
        Get BR leaderboard (Free Fire, PUBG Mobile).
        
        Endpoint: GET /api/tournaments/{id}/leaderboard/?match_ids=1,2,3
        
        Query Parameters:
        - match_ids: Comma-separated match IDs (required)
        
        Example:
        GET /api/tournaments/123/leaderboard/?match_ids=1,2,3
        
        Response (IDs-only per PII discipline):
        {
            "tournament_id": 123,
            "game_slug": "free-fire",
            "match_ids": [1, 2, 3],
            "standings": [
                {
                    "rank": 1,
                    "participant_id": 456,
                    "team_id": 789,
                    "total_points": 54,
                    "total_kills": 28,
                    "best_placement": 1,
                    "avg_placement": 2.3,
                    "matches_played": 3
                },
                ...
            ],
            "total_participants": 16,
            "generated_at": "2025-11-13T10:30:00Z"
        }
        
        Note:
            No display names or tournament names per PII discipline.
            Clients resolve IDs via separate metadata APIs.
        
        Errors:
        - 400: Invalid match IDs or non-BR game
        - 404: Tournament not found
        """
        tournament = self.get_object()
        
        # Parse match_ids query parameter
        match_ids_str = request.query_params.get('match_ids', '')
        if not match_ids_str:
            return Response(
                {'error': 'match_ids query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            match_ids = [int(mid.strip()) for mid in match_ids_str.split(',')]
        except ValueError:
            return Response(
                {'error': 'match_ids must be comma-separated integers'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delegate to service
        try:
            standings = LeaderboardService.calculate_br_standings(tournament.id, match_ids)
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build response (IDs-only per PII discipline, no tournament name)
        response_data = {
            'tournament_id': tournament.id,
            'game_slug': tournament.game.slug,
            'match_ids': match_ids,
            'standings': standings,
            'total_participants': len(standings),
            'generated_at': timezone.now()
        }
        
        serializer = BRLeaderboardSerializer(response_data)
        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path='series/(?P<match_id>[0-9]+)',
        permission_classes=[IsAuthenticated]
    )
    def series_summary(self, request, pk=None, match_id=None):
        """
        Get series summary (Valorant, CS2, Dota2, MLBB, CODM).
        
        Endpoint: GET /api/tournaments/{id}/series/{match_id}/
        
        URL Parameters:
        - id: Tournament ID
        - match_id: Primary match ID (or comma-separated IDs for full series)
        
        Query Parameters (optional):
        - match_ids: Comma-separated match IDs (overrides URL match_id)
        
        Example:
        GET /api/tournaments/123/series/456/?match_ids=456,457,458
        
        Response:
        {
            "series_id": "456",
            "format": "Best of 3",
            "series_winner_id": 789,
            "series_score": {"789": 2, "790": 1},
            "total_games": 3,
            "games": [
                {
                    "game_number": 1,
                    "match_id": 456,
                    "winner_id": 789,
                    "score": "13-11"
                },
                ...
            ],
            "participants": [
                {
                    "rank": 1,
                    "participant_id": 789,
                    "wins": 2,
                    "losses": 1,
                    "series_score": "2-1"
                },
                ...
            ]
        }
        
        Errors:
        - 400: Invalid match IDs or no completed matches
        - 404: Tournament or match not found
        """
        tournament = self.get_object()
        
        # Parse match IDs from query params or URL
        match_ids_str = request.query_params.get('match_ids')
        if match_ids_str:
            try:
                match_ids = [int(mid.strip()) for mid in match_ids_str.split(',')]
            except ValueError:
                return Response(
                    {'error': 'match_ids must be comma-separated integers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Use single match_id from URL
            try:
                match_ids = [int(match_id)]
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid match_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Delegate to service
        try:
            summary = LeaderboardService.calculate_series_summary(match_ids)
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SeriesSummarySerializer(summary)
        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['post'],
        url_path='override-placement',
        permission_classes=[IsAuthenticated, IsOrganizerOrAdmin]
    )
    def override_placement(self, request, pk=None):
        """
        Override tournament placement (staff only).
        
        Endpoint: POST /api/tournaments/{id}/override-placement/
        
        Request Body:
        {
            "registration_id": 456,
            "new_rank": 1,
            "reason": "Manual correction after dispute resolution - team disqualified for rule violation"
        }
        
        Permissions:
        - IsStaffOrAdmin: Only staff/admin can override placements
        - IsOrganizerOrAdmin: Tournament organizer or platform admin
        
        Side Effects:
        - Creates/updates TournamentResult with override flag
        - Sets is_override=True, override_reason, override_actor_id, override_timestamp
        - Logs audit trail (Module 2.4)
        
        Response:
        {
            "success": true,
            "result_id": 123,
            "old_rank": 2,
            "new_rank": 1,
            "override_timestamp": "2025-11-13T10:30:00Z",
            "override_actor_id": 789,
            "override_reason": "Manual correction..."
        }
        
        Errors:
        - 400: Invalid input or validation error
        - 403: Not authorized (not staff/organizer)
        - 404: Tournament or registration not found
        """
        tournament = self.get_object()
        
        # Validate input
        serializer = PlacementOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        registration_id = serializer.validated_data['registration_id']
        new_rank = serializer.validated_data['new_rank']
        reason = serializer.validated_data['reason']
        
        # Verify registration belongs to this tournament
        try:
            registration = Registration.objects.get(
                id=registration_id,
                tournament_id=tournament.id,
                is_deleted=False
            )
        except Registration.DoesNotExist:
            return Response(
                {'error': f'Registration {registration_id} not found in tournament {tournament.id}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Delegate to service
        try:
            result = LeaderboardService.override_placement(
                tournament_id=tournament.id,
                registration_id=registration_id,
                new_rank=new_rank,
                reason=reason,
                actor_id=request.user.id
            )
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Log audit event
        logger.info(
            f"Placement override: tournament={tournament.id}, registration={registration_id}, "
            f"new_rank={new_rank}, actor={request.user.id}, reason='{reason[:50]}'"
        )
        
        # Build response from returned dict
        response_data = {
            'success': result.get('success', True),
            'result_id': result.get('result_id'),
            'old_rank': result.get('old_rank'),
            'new_rank': result.get('new_rank'),
            'override_timestamp': result.get('override_timestamp'),
            'override_actor_id': request.user.id,
            'override_reason': reason
        }
        
        response_serializer = PlacementOverrideResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
