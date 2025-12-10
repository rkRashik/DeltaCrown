"""
API Views for User Stats

Phase 8, Epic 8.2: User Stats Service
REST API endpoints for retrieving user statistics.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from apps.api.serializers.user_stats_serializers import (
    UserStatsSerializer,
    UserStatsSummarySerializer,
    UserStatsListSerializer,
)
from apps.tournament_ops.services.tournament_ops_service import get_tournament_ops_service
from apps.tournament_ops.exceptions import ValidationError

logger = logging.getLogger(__name__)


class UserStatsDetailView(APIView):
    """
    GET /api/stats/v1/users/<user_id>/
    
    Retrieve statistics for a specific user and game.
    
    Query Parameters:
        - game_slug (required): Game identifier (e.g., 'valorant', 'csgo')
    
    Response:
        - 200 OK: UserStatsSerializer with full stats
        - 404 Not Found: User has no stats for that game
        - 400 Bad Request: Missing or invalid parameters
    
    Reference: Phase 8, Epic 8.2 - User Stats API
    """
    permission_classes = [AllowAny]  # Public stats viewing
    
    def get(self, request, user_id):
        """
        Get user stats for specific game.
        
        Args:
            request: DRF Request
            user_id: User ID from URL path
            
        Returns:
            Response with UserStatsDTO serialized data
        """
        game_slug = request.query_params.get('game_slug')
        
        if not game_slug:
            return Response(
                {'error': 'game_slug query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get stats via façade
            service = get_tournament_ops_service()
            stats_dto = service.get_user_stats(user_id=user_id, game_slug=game_slug)
            
            if not stats_dto:
                return Response(
                    {'error': f'No stats found for user {user_id} in game {game_slug}'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Serialize and return
            serializer = UserStatsSerializer(stats_dto.to_dict())
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving stats for user {user_id}: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserAllStatsView(APIView):
    """
    GET /api/stats/v1/users/<user_id>/all/
    
    Retrieve all statistics for a user across all games.
    
    Response:
        - 200 OK: List of UserStatsSerializer (one per game)
        - 404 Not Found: User has no stats
    
    Reference: Phase 8, Epic 8.2 - Multi-Game Stats API
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        """
        Get all stats for user across all games.
        
        Args:
            request: DRF Request
            user_id: User ID from URL path
            
        Returns:
            Response with list of UserStatsDTO
        """
        try:
            # Get stats via façade
            service = get_tournament_ops_service()
            all_stats = service.get_all_user_stats(user_id=user_id)
            
            if not all_stats:
                return Response(
                    {'error': f'No stats found for user {user_id}'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Serialize and return
            serialized_stats = [
                UserStatsSerializer(stats.to_dict()).data
                for stats in all_stats
            ]
            return Response(serialized_stats, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving all stats for user {user_id}: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CurrentUserStatsView(APIView):
    """
    GET /api/stats/v1/me/
    
    Retrieve statistics for currently authenticated user.
    
    Query Parameters:
        - game_slug (optional): Specific game filter. If omitted, returns all games.
    
    Response:
        - 200 OK: UserStatsSerializer or list of stats
        - 401 Unauthorized: Not authenticated
        - 404 Not Found: User has no stats
    
    Reference: Phase 8, Epic 8.2 - Current User Stats API
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get stats for currently authenticated user.
        
        Args:
            request: DRF Request with authenticated user
            
        Returns:
            Response with UserStatsDTO(s)
        """
        user_id = request.user.id
        game_slug = request.query_params.get('game_slug')
        
        try:
            service = get_tournament_ops_service()
            
            if game_slug:
                # Single game stats
                stats_dto = service.get_user_stats(user_id=user_id, game_slug=game_slug)
                
                if not stats_dto:
                    return Response(
                        {'error': f'No stats found for you in game {game_slug}'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                serializer = UserStatsSerializer(stats_dto.to_dict())
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # All games stats
                all_stats = service.get_all_user_stats(user_id=user_id)
                
                if not all_stats:
                    return Response(
                        {'error': 'You have no stats yet'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                serialized_stats = [
                    UserStatsSerializer(stats.to_dict()).data
                    for stats in all_stats
                ]
                return Response(serialized_stats, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving stats for current user {user_id}: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserStatsSummaryView(APIView):
    """
    GET /api/stats/v1/users/<user_id>/summary/
    
    Retrieve summary statistics for a user.
    
    Query Parameters:
        - game_slug (optional): Specific game filter
    
    Response:
        - 200 OK: Summary statistics dict
        - 404 Not Found: User has no stats
    
    Reference: Phase 8, Epic 8.2 - Stats Summary API
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        """
        Get summary stats for user.
        
        Args:
            request: DRF Request
            user_id: User ID from URL path
            
        Returns:
            Response with summary dict
        """
        game_slug = request.query_params.get('game_slug')
        
        try:
            # Get summary via façade
            service = get_tournament_ops_service()
            summary = service.get_user_stats_summary(
                user_id=user_id,
                game_slug=game_slug
            )
            
            if not summary.get('has_stats', False):
                return Response(
                    {'error': 'No stats found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(summary, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving summary for user {user_id}: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GameLeaderboardView(APIView):
    """
    GET /api/stats/v1/games/<game_slug>/leaderboard/
    
    Retrieve top-performing users for a specific game.
    
    Query Parameters:
        - limit (optional): Maximum results (default 100, max 1000)
    
    Response:
        - 200 OK: List of UserStatsSerializer ordered by win rate
    
    Reference: Phase 8, Epic 8.2 - Leaderboard Integration
    """
    permission_classes = [AllowAny]
    
    def get(self, request, game_slug):
        """
        Get leaderboard for specific game.
        
        Args:
            request: DRF Request
            game_slug: Game identifier from URL path
            
        Returns:
            Response with list of top UserStatsDTO
        """
        limit = int(request.query_params.get('limit', 100))
        
        try:
            # Get top stats via façade
            service = get_tournament_ops_service()
            top_stats = service.get_top_stats_for_game(
                game_slug=game_slug,
                limit=limit
            )
            
            # Serialize and return
            serialized_stats = [
                UserStatsSerializer(stats.to_dict()).data
                for stats in top_stats
            ]
            
            return Response(
                {
                    'game_slug': game_slug,
                    'limit': limit,
                    'count': len(serialized_stats),
                    'results': serialized_stats,
                },
                status=status.HTTP_200_OK
            )
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving leaderboard for game {game_slug}: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
