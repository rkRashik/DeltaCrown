"""
Analytics API Views for Epic 8.5 - Advanced Analytics & Leaderboards.

API endpoints for user/team analytics, leaderboards, and seasons.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import Http404

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
    GET /api/stats/v2/users/<user_id>/analytics/
    
    Retrieve comprehensive analytics for a user in a specific game.
    """
    
    permission_classes = [AllowAny]  # Public analytics
    
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
    GET /api/stats/v2/teams/<team_id>/analytics/
    
    Retrieve comprehensive analytics for a team in a specific game.
    """
    
    permission_classes = [AllowAny]  # Public analytics
    
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
    GET /api/leaderboards/v2/<leaderboard_type>/
    
    Retrieve leaderboard entries with filtering and pagination.
    
    Supported leaderboard types:
    - global_user: Global user rankings
    - game_user: Game-specific user rankings
    - team: Team rankings
    - seasonal: Seasonal user rankings
    - mmr/elo: MMR/ELO-based rankings
    - tier: Tier-based rankings
    """
    
    permission_classes = [AllowAny]  # Public leaderboards
    
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
    POST /api/leaderboards/v2/refresh/
    
    Trigger leaderboard refresh (admin/organizer only).
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Queue leaderboard refresh job."""
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
    GET /api/seasons/current/
    
    Retrieve currently active season.
    """
    
    permission_classes = [AllowAny]
    
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
    GET /api/seasons/
    
    List all seasons (active and historical).
    """
    
    permission_classes = [AllowAny]
    
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
