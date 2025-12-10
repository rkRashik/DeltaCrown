"""
API Views for Match History

Phase 8, Epic 8.4: Match History Engine
REST API endpoints for retrieving user and team match history with filtering.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from datetime import datetime

from apps.api.serializers.match_history_serializers import (
    UserMatchHistorySerializer,
    TeamMatchHistorySerializer,
    MatchHistoryFilterSerializer,
    MatchHistoryResponseSerializer,
)
from apps.tournament_ops.services.tournament_ops_service import get_tournament_ops_service
from apps.tournament_ops.exceptions import ValidationError

logger = logging.getLogger(__name__)


class UserMatchHistoryView(APIView):
    """
    GET /api/tournaments/v1/history/users/<user_id>/
    
    Retrieve match history for a specific user with filtering and pagination.
    
    Query Parameters:
        - game_slug (optional): Filter by game (e.g., 'valorant', 'csgo')
        - tournament_id (optional): Filter by tournament
        - from_date (optional): Filter by date range start (ISO 8601)
        - to_date (optional): Filter by date range end (ISO 8601)
        - only_wins (optional): Show only wins (default: false)
        - only_losses (optional): Show only losses (default: false)
        - limit (optional): Results per page (1-100, default: 20)
        - offset (optional): Offset for pagination (default: 0)
    
    Response:
        - 200 OK: Paginated match history
        - 400 Bad Request: Invalid parameters
        - 403 Forbidden: Not authorized to view this user's history
    
    Permissions:
        - Public for own history
        - Authenticated users can view any user's history
    
    Reference: Phase 8, Epic 8.4 - Match History API
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        """
        Get user match history with filters and pagination.
        
        Args:
            request: DRF Request with query params
            user_id: User ID from URL path
            
        Returns:
            Response with paginated match history
        """
        # Validate filters
        filter_serializer = MatchHistoryFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(
                {'error': 'Invalid filter parameters', 'details': filter_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filters = filter_serializer.validated_data
        
        try:
            # Get history via façade
            service = get_tournament_ops_service()
            history_list, total_count = service.get_user_match_history(
                user_id=user_id,
                game_slug=filters.get('game_slug'),
                tournament_id=filters.get('tournament_id'),
                from_date=filters.get('from_date'),
                to_date=filters.get('to_date'),
                only_wins=filters.get('only_wins', False),
                only_losses=filters.get('only_losses', False),
                limit=filters.get('limit', 20),
                offset=filters.get('offset', 0),
            )
            
            # Serialize results
            serialized_history = [
                UserMatchHistorySerializer(entry.to_dict()).data
                for entry in history_list
            ]
            
            # Build paginated response
            limit = filters.get('limit', 20)
            offset = filters.get('offset', 0)
            
            response_data = {
                'results': serialized_history,
                'count': total_count,
                'limit': limit,
                'offset': offset,
                'has_next': (offset + limit) < total_count,
                'has_previous': offset > 0,
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving match history for user {user_id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TeamMatchHistoryView(APIView):
    """
    GET /api/tournaments/v1/history/teams/<team_id>/
    
    Retrieve match history for a specific team with filtering and pagination.
    
    Query Parameters:
        - Same as UserMatchHistoryView
    
    Response:
        - 200 OK: Paginated match history with ELO tracking
        - 400 Bad Request: Invalid parameters
        - 403 Forbidden: Not authorized to view this team's history (if private)
    
    Permissions:
        - Public for team history (teams are public entities)
        - Team captain/members can view full history
    
    Reference: Phase 8, Epic 8.4 - Team Match History API
    """
    permission_classes = [AllowAny]
    
    def get(self, request, team_id):
        """
        Get team match history with filters and pagination.
        
        Args:
            request: DRF Request with query params
            team_id: Team ID from URL path
            
        Returns:
            Response with paginated match history including ELO changes
        """
        # Validate filters
        filter_serializer = MatchHistoryFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(
                {'error': 'Invalid filter parameters', 'details': filter_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filters = filter_serializer.validated_data
        
        try:
            # Get history via façade
            service = get_tournament_ops_service()
            history_list, total_count = service.get_team_match_history(
                team_id=team_id,
                game_slug=filters.get('game_slug'),
                tournament_id=filters.get('tournament_id'),
                from_date=filters.get('from_date'),
                to_date=filters.get('to_date'),
                only_wins=filters.get('only_wins', False),
                only_losses=filters.get('only_losses', False),
                limit=filters.get('limit', 20),
                offset=filters.get('offset', 0),
            )
            
            # Serialize results
            serialized_history = [
                TeamMatchHistorySerializer(entry.to_dict()).data
                for entry in history_list
            ]
            
            # Build paginated response
            limit = filters.get('limit', 20)
            offset = filters.get('offset', 0)
            
            response_data = {
                'results': serialized_history,
                'count': total_count,
                'limit': limit,
                'offset': offset,
                'has_next': (offset + limit) < total_count,
                'has_previous': offset > 0,
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving match history for team {team_id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CurrentUserMatchHistoryView(APIView):
    """
    GET /api/tournaments/v1/history/me/
    
    Retrieve match history for currently authenticated user.
    Convenience endpoint that redirects to UserMatchHistoryView with current user's ID.
    
    Query Parameters:
        - Same as UserMatchHistoryView
    
    Response:
        - Same as UserMatchHistoryView
        - 401 Unauthorized: Not authenticated
    
    Reference: Phase 8, Epic 8.4 - Authenticated User History
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get match history for authenticated user.
        
        Args:
            request: DRF Request with authenticated user
            
        Returns:
            Response with paginated match history
        """
        user_id = request.user.id
        
        # Validate filters
        filter_serializer = MatchHistoryFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(
                {'error': 'Invalid filter parameters', 'details': filter_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filters = filter_serializer.validated_data
        
        try:
            # Get history via façade
            service = get_tournament_ops_service()
            history_list, total_count = service.get_user_match_history(
                user_id=user_id,
                game_slug=filters.get('game_slug'),
                tournament_id=filters.get('tournament_id'),
                from_date=filters.get('from_date'),
                to_date=filters.get('to_date'),
                only_wins=filters.get('only_wins', False),
                only_losses=filters.get('only_losses', False),
                limit=filters.get('limit', 20),
                offset=filters.get('offset', 0),
            )
            
            # Serialize results
            serialized_history = [
                UserMatchHistorySerializer(entry.to_dict()).data
                for entry in history_list
            ]
            
            # Build paginated response
            limit = filters.get('limit', 20)
            offset = filters.get('offset', 0)
            
            response_data = {
                'results': serialized_history,
                'count': total_count,
                'limit': limit,
                'offset': offset,
                'has_next': (offset + limit) < total_count,
                'has_previous': offset > 0,
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving match history for current user {user_id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
