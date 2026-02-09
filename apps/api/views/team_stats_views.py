"""
Team Stats API Views

Phase 8, Epic 8.3: Team Stats & Ranking System
REST API endpoints for team statistics and ELO rankings.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

from apps.tournament_ops.services.tournament_ops_service import get_tournament_ops_service
from apps.api.serializers.team_stats_serializers import (
    TeamStatsSerializer,
    TeamRankingSerializer,
    TeamStatsSummarySerializer,
    GameTeamLeaderboardEntrySerializer,
)


class TeamStatsDetailView(APIView):
    """
    Get team statistics for a specific game.
    
    GET /api/stats/v1/teams/{team_id}/stats/{game_slug}/
    
    Returns:
        TeamStatsDTO with match/tournament stats
    
    Reference: Phase 8, Epic 8.3 - Team Stats API
    """
    
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    
    def get(self, request, team_id, game_slug):
        """Get team stats for team + game combination."""
        try:
            service = get_tournament_ops_service()
            stats_dto = service.get_team_stats(team_id, game_slug)
            
            if not stats_dto:
                return Response(
                    {"error": "Team stats not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = TeamStatsSerializer(stats_dto.to_dict())
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve team stats: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TeamAllStatsView(APIView):
    """
    Get team statistics across all games.
    
    GET /api/stats/v1/teams/{team_id}/stats/
    
    Returns:
        List of TeamStatsDTO for all games the team has played
    
    Reference: Phase 8, Epic 8.3 - Team Stats API
    """
    
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    
    def get(self, request, team_id):
        """Get all team stats across all games."""
        try:
            service = get_tournament_ops_service()
            stats_dtos = service.get_all_team_stats(team_id)
            
            serializer = TeamStatsSerializer(
                [dto.to_dict() for dto in stats_dtos],
                many=True
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve team stats: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TeamRankingView(APIView):
    """
    Get team ELO ranking for a specific game.
    
    GET /api/stats/v1/teams/{team_id}/ranking/{game_slug}/
    
    Returns:
        TeamRankingDTO with ELO rating, rank, W/L/D record
    
    Reference: Phase 8, Epic 8.3 - Team Ranking API
    """
    
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    
    def get(self, request, team_id, game_slug):
        """Get team ranking for team + game combination."""
        try:
            service = get_tournament_ops_service()
            ranking_dto = service.get_team_ranking(team_id, game_slug)
            
            if not ranking_dto:
                return Response(
                    {"error": "Team ranking not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = TeamRankingSerializer(ranking_dto.to_dict())
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve team ranking: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GameTeamLeaderboardView(APIView):
    """
    Get team leaderboard for a game (top teams by ELO).
    
    GET /api/stats/v1/leaderboards/teams/{game_slug}/
    Query params:
        - limit: Number of teams to return (default 100, max 500)
    
    Returns:
        List of TeamRankingDTO ordered by ELO rating DESC
    
    Reference: Phase 8, Epic 8.3 - Leaderboard API
    """
    
    permission_classes = []  # Public endpoint
    throttle_classes = [AnonRateThrottle]
    
    def get(self, request, game_slug):
        """Get top teams for game by ELO rating."""
        try:
            # Parse limit parameter
            limit = int(request.query_params.get('limit', 100))
            limit = min(max(1, limit), 500)  # Clamp between 1 and 500
            
            service = get_tournament_ops_service()
            ranking_dtos = service.get_top_teams_by_elo(game_slug, limit)
            
            # Enrich with team names (method-level ORM import)
            from apps.organizations.models import Team
            
            leaderboard_data = []
            for ranking_dto in ranking_dtos:
                try:
                    team = Team.objects.get(id=ranking_dto.team_id)
                    entry = {
                        **ranking_dto.to_dict(),
                        'team_name': team.name,
                    }
                    leaderboard_data.append(entry)
                except Team.DoesNotExist:
                    # Skip teams that no longer exist
                    continue
            
            serializer = GameTeamLeaderboardEntrySerializer(
                leaderboard_data,
                many=True
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except ValueError:
            return Response(
                {"error": "Invalid limit parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve leaderboard: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TeamStatsSummaryView(APIView):
    """
    Get team stats summary (lightweight stats for UI widgets).
    
    GET /api/stats/v1/teams/{team_id}/summary/
    Query params:
        - game_slug: Optional game filter (omit for all-games aggregation)
    
    Returns:
        TeamStatsSummaryDTO or List[TeamStatsSummaryDTO] if no game_slug
    
    Reference: Phase 8, Epic 8.3 - Summary API
    """
    
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    
    def get(self, request, team_id):
        """Get team stats summary."""
        try:
            game_slug = request.query_params.get('game_slug', None)
            
            service = get_tournament_ops_service()
            summary = service.get_team_stats_summary(team_id, game_slug)
            
            if not summary:
                return Response(
                    {"error": "Team stats not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Handle single-game or multi-game response
            if isinstance(summary, list):
                serializer = TeamStatsSummarySerializer(
                    [s.to_dict() for s in summary],
                    many=True
                )
            else:
                serializer = TeamStatsSummarySerializer(summary.to_dict())
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve team summary: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TeamStatsForGameView(APIView):
    """
    Get all team stats for a game (leaderboard by win rate).
    
    GET /api/stats/v1/games/{game_slug}/teams/stats/
    Query params:
        - limit: Number of teams to return (default 100, max 500)
    
    Returns:
        List of TeamStatsDTO ordered by win_rate DESC
    
    Reference: Phase 8, Epic 8.3 - Game Stats API
    """
    
    permission_classes = []  # Public endpoint
    throttle_classes = [AnonRateThrottle]
    
    def get(self, request, game_slug):
        """Get team stats for game ordered by win rate."""
        try:
            # Parse limit parameter
            limit = int(request.query_params.get('limit', 100))
            limit = min(max(1, limit), 500)  # Clamp between 1 and 500
            
            # Get stats via adapter (method-level import)
            from apps.tournament_ops.adapters import TeamStatsAdapter
            
            adapter = TeamStatsAdapter()
            stats_dtos = adapter.get_stats_by_game(game_slug, limit)
            
            serializer = TeamStatsSerializer(
                [dto.to_dict() for dto in stats_dtos],
                many=True
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except ValueError:
            return Response(
                {"error": "Invalid limit parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve game team stats: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
