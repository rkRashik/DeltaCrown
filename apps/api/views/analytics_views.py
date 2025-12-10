"""
Analytics API Views for Epic 8.5 - Advanced Analytics & Leaderboards.

API endpoints for user/team analytics, leaderboards, and seasons.
Implements Phase 8, Epic 8.5 - Advanced Analytics & Leaderboards.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import Http404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from apps.api.serializers.analytics_serializers import (
    UserAnalyticsSerializer,
    TeamAnalyticsSerializer,
    LeaderboardEntrySerializer,
    SeasonSerializer,
    LeaderboardRefreshRequestSerializer,
)
from apps.tournament_ops.services.tournament_ops_service import get_tournament_ops_service


class UserAnalyticsView(APIView):
    """
    User Analytics Endpoint.
    
    Retrieve comprehensive analytics for a user in a specific game including:
    - MMR and ELO ratings
    - Win rate and match statistics
    - KDA ratio and performance metrics
    - Current and longest win streaks
    - Tier ranking (Bronze/Silver/Gold/Diamond/Crown)
    - Percentile rank
    """
    
    permission_classes = [AllowAny]  # Public analytics
    
    @extend_schema(
        tags=["Analytics"],
        operation_id="get_user_analytics",
        summary="Get user analytics",
        description=(
            "Retrieve comprehensive analytics for a specific user in a game. "
            "Returns MMR, ELO, win rate, KDA ratio, streaks, tier, and percentile rank."
        ),
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="User ID",
                required=True,
            ),
            OpenApiParameter(
                name="game_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Game identifier (e.g., 'valorant', 'csgo', 'lol')",
                required=True,
                examples=[
                    OpenApiExample("Valorant", value="valorant"),
                    OpenApiExample("CS:GO", value="csgo"),
                    OpenApiExample("League of Legends", value="lol"),
                ],
            ),
        ],
        responses={
            200: UserAnalyticsSerializer,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful Response",
                value={
                    "user_id": 123,
                    "game_slug": "valorant",
                    "mmr_snapshot": 1600,
                    "elo_snapshot": 1600,
                    "win_rate": "65.50",
                    "kda_ratio": "1.25",
                    "matches_last_7d": 10,
                    "matches_last_30d": 45,
                    "win_rate_7d": "70.00",
                    "win_rate_30d": "65.00",
                    "current_streak": 3,
                    "longest_win_streak": 7,
                    "tier": "gold",
                    "percentile_rank": "75.50",
                    "recalculated_at": "2025-12-10T14:30:00Z"
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request, user_id):
        """Get user analytics snapshot."""
        game_slug = request.query_params.get('game_slug')
        
        if not game_slug:
            return Response(
                {"error": "game_slug query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_tournament_ops_service()
            analytics_dto = service.get_user_analytics(user_id, game_slug)
            
            if not analytics_dto:
                return Response(
                    {"error": "Analytics not found for this user/game combination"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = UserAnalyticsSerializer(analytics_dto.to_dict())
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve user analytics: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TeamAnalyticsView(APIView):
    """
    Team Analytics Endpoint.
    
    Retrieve comprehensive analytics for a team in a specific game including:
    - Team ELO rating and volatility
    - Win rate and match statistics
    - Average member skill level
    - Synergy score (performance consistency)
    - Activity score (match frequency)
    - Tier ranking
    - Percentile rank
    """
    
    permission_classes = [AllowAny]  # Public analytics
    
    @extend_schema(
        tags=["Analytics"],
        operation_id="get_team_analytics",
        summary="Get team analytics",
        description=(
            "Retrieve comprehensive analytics for a specific team in a game. "
            "Returns ELO, volatility, synergy score, activity score, tier, and percentile rank."
        ),
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Team ID",
                required=True,
            ),
            OpenApiParameter(
                name="game_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Game identifier",
                required=True,
            ),
        ],
        responses={
            200: TeamAnalyticsSerializer,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful Response",
                value={
                    "team_id": 456,
                    "game_slug": "csgo",
                    "elo_snapshot": 1800,
                    "elo_volatility": "15.50",
                    "avg_member_skill": "1750.00",
                    "win_rate": "60.00",
                    "win_rate_7d": "65.00",
                    "win_rate_30d": "60.00",
                    "synergy_score": "75.00",
                    "activity_score": "80.00",
                    "matches_last_7d": 8,
                    "matches_last_30d": 35,
                    "tier": "gold",
                    "percentile_rank": "70.00",
                    "recalculated_at": "2025-12-10T14:35:00Z"
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request, team_id):
        """Get team analytics snapshot."""
        game_slug = request.query_params.get('game_slug')
        
        if not game_slug:
            return Response(
                {"error": "game_slug query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_tournament_ops_service()
            analytics_dto = service.get_team_analytics(team_id, game_slug)
            
            if not analytics_dto:
                return Response(
                    {"error": "Analytics not found for this team/game combination"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = TeamAnalyticsSerializer(analytics_dto.to_dict())
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve team analytics: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LeaderboardView(APIView):
    """
    Leaderboard Endpoint.
    
    Retrieve leaderboard entries with filtering and pagination.
    Supports 7 leaderboard types across different ranking dimensions.
    """
    
    permission_classes = [AllowAny]  # Public leaderboards
    
    @extend_schema(
        tags=["Leaderboards"],
        operation_id="get_leaderboard",
        summary="Get leaderboard entries",
        description=(
            "Retrieve leaderboard entries for a specific leaderboard type. "
            "Supports filtering by game, season, and pagination. "
            "\n\nLeaderboard types:\n"
            "- **global_user**: Global user rankings across all games\n"
            "- **game_user**: Game-specific user rankings\n"
            "- **team**: Team rankings\n"
            "- **seasonal**: Seasonal user rankings with decay\n"
            "- **mmr**: MMR-based rankings\n"
            "- **elo**: ELO-based rankings\n"
            "- **tier**: Tier-based rankings (Crown > Diamond > Gold > Silver > Bronze)"
        ),
        parameters=[
            OpenApiParameter(
                name="leaderboard_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Leaderboard type",
                required=True,
                enum=["global_user", "game_user", "team", "seasonal", "mmr", "elo", "tier"],
            ),
            OpenApiParameter(
                name="game_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by game (optional for global leaderboards)",
                required=False,
            ),
            OpenApiParameter(
                name="season_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by season (required for seasonal leaderboard)",
                required=False,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Max entries to return (default: 100, max: 1000)",
                required=False,
            ),
        ],
        responses={
            200: LeaderboardEntrySerializer(many=True),
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful Response",
                value=[
                    {
                        "leaderboard_type": "game_user",
                        "rank": 1,
                        "reference_id": 123,
                        "game_slug": "valorant",
                        "score": 2400,
                        "wins": 75,
                        "losses": 25,
                        "win_rate": "75.00",
                        "payload": {"tier": "crown", "percentile": 99.5, "display_name": "ProPlayer123"},
                        "computed_at": "2025-12-10T15:00:00Z"
                    },
                    {
                        "rank": 2,
                        "reference_id": 456,
                        "score": 2300,
                        "wins": 70,
                        "losses": 30,
                        "win_rate": "70.00",
                        "payload": {"tier": "diamond", "percentile": 95.0},
                        "computed_at": "2025-12-10T15:00:00Z"
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request, leaderboard_type):
        """Get leaderboard entries."""
        game_slug = request.query_params.get('game_slug')
        season_id = request.query_params.get('season_id')
        limit = int(request.query_params.get('limit', 100))
        
        # Validate limit
        if limit > 1000:
            limit = 1000
        elif limit < 1:
            limit = 100
        
        try:
            service = get_tournament_ops_service()
            entries = service.get_leaderboard(
                leaderboard_type=leaderboard_type,
                game_slug=game_slug,
                season_id=season_id,
                limit=limit
            )
            
            # Convert DTOs to dicts
            entries_data = [entry.to_dict() for entry in entries]
            
            serializer = LeaderboardEntrySerializer(entries_data, many=True)
            
            return Response({
                "leaderboard_type": leaderboard_type,
                "game_slug": game_slug,
                "season_id": season_id,
                "count": len(entries),
                "entries": serializer.data
            }, status=status.HTTP_200_OK)
            
        except ValueError as ve:
            return Response(
                {"error": str(ve)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve leaderboard: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LeaderboardRefreshView(APIView):
    """
    Leaderboard Refresh Endpoint (Admin Only).
    
    Queue on-demand leaderboard refresh for a specific leaderboard type.
    Triggers background Celery job for recalculation.
    """
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Leaderboards"],
        operation_id="refresh_leaderboard",
        summary="Queue leaderboard refresh (admin only)",
        description=(
            "Queue an on-demand refresh of a specific leaderboard. "
            "Only staff users can trigger manual refreshes. "
            "Returns immediately with 202 Accepted; actual refresh happens asynchronously."
        ),
        request=LeaderboardRefreshRequestSerializer,
        responses={
            202: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "leaderboard_type": "game_user",
                    "game_slug": "valorant"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Successful Response",
                value={
                    "message": "Leaderboard refresh queued",
                    "leaderboard_type": "game_user",
                    "game_slug": "valorant"
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        """Queue leaderboard refresh."""
        # Check if user has permission (admin or organizer)
        if not (request.user.is_staff or request.user.is_superuser):
            # Could also check for specific organizer permission
            return Response(
                {"error": "Permission denied. Admin or organizer access required."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = LeaderboardRefreshRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = get_tournament_ops_service()
            result = service.refresh_leaderboards()
            
            return Response({
                "message": "Leaderboard refresh queued successfully",
                "job_id": result['job_id'],
                "status": result['status']
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to queue leaderboard refresh: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CurrentSeasonView(APIView):
    """
    Current Season Endpoint.
    
    Retrieve the currently active season with decay rules and date range.
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=["Seasons"],
        operation_id="get_current_season",
        summary="Get current active season",
        description=(
            "Retrieve the currently active season. "
            "Returns season details including decay rules, start/end dates, and active status."
        ),
        responses={
            200: SeasonSerializer,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful Response",
                value={
                    "season_id": "S1-2024",
                    "name": "Season 1 - 2024",
                    "start_date": "2024-12-01T00:00:00Z",
                    "end_date": "2025-02-28T23:59:59Z",
                    "is_active": True,
                    "decay_rules": {
                        "enabled": True,
                        "grace_period_days": 30,
                        "decay_percentage": 5.0
                    }
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        """Get current active season."""
        try:
            from apps.tournament_ops.adapters import AnalyticsAdapter
            
            adapter = AnalyticsAdapter()
            season_dto = adapter.get_current_season()
            
            if not season_dto:
                return Response(
                    {"error": "No active season found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = SeasonSerializer(season_dto.to_dict())
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve current season: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SeasonsListView(APIView):
    """
    Seasons List Endpoint.
    
    List all seasons with optional filtering by active status.
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=["Seasons"],
        operation_id="list_seasons",
        summary="List all seasons",
        description=(
            "List all seasons (active and inactive). "
            "Use include_inactive parameter to control visibility of inactive seasons."
        ),
        parameters=[
            OpenApiParameter(
                name="include_inactive",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Include inactive seasons (default: false)",
                required=False,
            ),
        ],
        responses={
            200: SeasonSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                "Successful Response",
                value=[
                    {
                        "season_id": "S2-2024",
                        "name": "Season 2 - 2024",
                        "start_date": "2025-01-01T00:00:00Z",
                        "end_date": "2025-03-31T23:59:59Z",
                        "is_active": True,
                        "decay_rules": {"enabled": True, "decay_percentage": 5.0}
                    },
                    {
                        "season_id": "S1-2024",
                        "name": "Season 1 - 2024",
                        "start_date": "2024-12-01T00:00:00Z",
                        "end_date": "2024-12-31T23:59:59Z",
                        "is_active": False,
                        "decay_rules": {"enabled": True, "decay_percentage": 5.0}
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        """List all seasons."""
        include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'
        
        try:
            from apps.tournament_ops.adapters import AnalyticsAdapter
            
            adapter = AnalyticsAdapter()
            seasons = adapter.list_seasons(include_inactive=include_inactive)
            
            # Convert DTOs to dicts
            seasons_data = [season.to_dict() for season in seasons]
            
            serializer = SeasonSerializer(seasons_data, many=True)
            
            return Response({
                "count": len(seasons),
                "seasons": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve seasons: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
