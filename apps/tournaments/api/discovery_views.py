"""
Tournament Discovery API - Endpoints for searching and filtering tournaments.

Module: 2.4 - Tournament Discovery & Filtering (Backend Only)

Source Documents:
- Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md (Module 2.4, Lines 214-241)
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Section 5.1, Lines 455-555)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Tournament fields)
- Documents/Planning/PROPOSAL_PART_2_TECHNICAL_ARCHITECTURE.md (API patterns, ordering)

Endpoints:
- GET /api/tournaments/discover/           Search & filter tournaments (main endpoint)
- GET /api/tournaments/upcoming/           Upcoming tournaments (convenience)
- GET /api/tournaments/live/               Live tournaments (convenience)
- GET /api/tournaments/featured/           Featured tournaments (convenience)
- GET /api/tournaments/by-game/{game_id}/  Game-specific tournaments

Query Parameters (for /discover/):
- search: Full-text search on name, description, game name
- game: Game ID filter
- status: Status filter (published, registration_open, live, completed, etc.)
- format: Tournament format (single_elimination, double_elimination, etc.)
- min_prize: Minimum prize pool
- max_prize: Maximum prize pool
- min_fee: Minimum entry fee
- max_fee: Maximum entry fee
- free_only: Boolean for free tournaments only
- start_after: Tournament start date filter (ISO 8601)
- start_before: Tournament start date filter (ISO 8601)
- is_official: Boolean for official tournaments
- ordering: Sort order (tournament_start, -tournament_start, prize_pool, -prize_pool, etc.)
- page: Page number for pagination
- page_size: Items per page (default: 20, max: 100)

Architecture Decisions:
- ADR-001: Service Layer Pattern - ViewSet delegates to TournamentDiscoveryService
- ADR-002: API Design Patterns - RESTful, consistent responses
- ADR-004: PostgreSQL Full-Text Search - Use SearchVector for search queries

Returns:
- IDs-only discipline (no nested objects, use IDs + expand for relations)
- Paginated responses with count, next, previous, results
- Optimized queries with select_related
"""

from decimal import Decimal, InvalidOperation
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from django.utils.dateparse import parse_datetime
from django.core.exceptions import ValidationError

from apps.tournaments.models.tournament import Tournament
from apps.games.models.game import Game
from apps.tournaments.api.tournament_serializers import TournamentListSerializer
from apps.tournaments.services.tournament_discovery_service import TournamentDiscoveryService


class TournamentDiscoveryPagination(PageNumberPagination):
    """
    Pagination for tournament discovery.
    
    Default: 20 items per page
    Max: 100 items per page
    
    Query params:
    - page: Page number
    - page_size: Items per page (max 100)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class TournamentDiscoveryViewSet(viewsets.ViewSet):
    """
    ViewSet for tournament discovery and filtering.
    
    All endpoints are public (no authentication required).
    Delegates filtering logic to TournamentDiscoveryService.
    Returns paginated, IDs-only responses.
    """
    
    permission_classes = [AllowAny]
    pagination_class = TournamentDiscoveryPagination
    
    @property
    def paginator(self):
        """Get paginator instance."""
        if not hasattr(self, '_paginator'):
            self._paginator = self.pagination_class()
        return self._paginator
    
    def list(self, request):
        """
        Main discovery endpoint with full filtering capabilities.
        
        GET /api/tournaments/discover/?search=valorant&game=1&status=published&ordering=-prize_pool
        
        Query Parameters:
        - search (str): Full-text search on name, description, game name
        - game (int): Game ID
        - status (str): Tournament status (published, registration_open, live, etc.)
        - format (str): Tournament format (single_elimination, double_elimination, etc.)
        - min_prize (decimal): Minimum prize pool
        - max_prize (decimal): Maximum prize pool
        - min_fee (decimal): Minimum entry fee
        - max_fee (decimal): Maximum entry fee
        - free_only (bool): Filter for free tournaments (true/false)
        - start_after (datetime): Tournament starts after this date (ISO 8601)
        - start_before (datetime): Tournament starts before this date (ISO 8601)
        - is_official (bool): Filter official tournaments (true/false)
        - ordering (str): Sort field (tournament_start, -tournament_start, prize_pool, -prize_pool, created_at, -created_at)
        - page (int): Page number
        - page_size (int): Items per page (max 100)
        
        Returns:
        - 200: Paginated list of tournaments
        - 400: Invalid query parameters
        
        Example Response:
        {
            "count": 42,
            "next": "/api/tournaments/discover/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "name": "Valorant Champions Cup",
                    "slug": "valorant-champions-cup",
                    "game_id": 1,
                    "game_name": "Valorant",
                    "organizer_id": 5,
                    "organizer_username": "admin",
                    "status": "registration_open",
                    "format": "single_elimination",
                    "max_participants": 16,
                    "prize_pool": "10000.00",
                    "entry_fee_amount": "500.00",
                    "has_entry_fee": true,
                    "tournament_start": "2025-11-20T10:00:00Z",
                    "registration_start": "2025-11-10T00:00:00Z",
                    "registration_end": "2025-11-19T23:59:59Z",
                    "is_official": true,
                    "thumbnail_image": "/media/tournaments/thumbnails/...",
                    "participant_count": 8
                },
                ...
            ]
        }
        """
        # Extract query parameters
        search_query = request.query_params.get('search', '').strip()
        game_id = request.query_params.get('game')
        status_filter = request.query_params.get('status')
        format_filter = request.query_params.get('format')
        min_prize = request.query_params.get('min_prize')
        max_prize = request.query_params.get('max_prize')
        min_fee = request.query_params.get('min_fee')
        max_fee = request.query_params.get('max_fee')
        free_only = request.query_params.get('free_only')
        start_after = request.query_params.get('start_after')
        start_before = request.query_params.get('start_before')
        is_official = request.query_params.get('is_official')
        ordering = request.query_params.get('ordering', '-tournament_start')
        
        # Build filters dictionary
        filters = {}
        
        # Game filter
        if game_id:
            try:
                filters['game_id'] = int(game_id)
            except ValueError:
                return Response(
                    {'error': 'Invalid game ID. Must be an integer.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Status filter
        if status_filter:
            filters['status'] = status_filter
        
        # Format filter
        if format_filter:
            filters['format'] = format_filter
        
        # Prize pool filters
        if min_prize:
            try:
                filters['min_prize'] = Decimal(min_prize)
            except (ValueError, InvalidOperation):
                return Response(
                    {'error': 'Invalid min_prize. Must be a number.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if max_prize:
            try:
                filters['max_prize'] = Decimal(max_prize)
            except (ValueError, InvalidOperation):
                return Response(
                    {'error': 'Invalid max_prize. Must be a number.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Entry fee filters
        if free_only:
            filters['has_entry_fee'] = False
        else:
            if min_fee:
                try:
                    filters['min_fee'] = Decimal(min_fee)
                except (ValueError, InvalidOperation):
                    return Response(
                        {'error': 'Invalid min_fee. Must be a number.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if max_fee:
                try:
                    filters['max_fee'] = Decimal(max_fee)
                except (ValueError, InvalidOperation):
                    return Response(
                        {'error': 'Invalid max_fee. Must be a number.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        # Official filter
        if is_official is not None:
            filters['is_official'] = is_official.lower() in ('true', '1', 'yes')
        
        # Get queryset from service
        try:
            queryset = TournamentDiscoveryService.search_tournaments(
                query=search_query,
                filters=filters,
                ordering=ordering,
                user=request.user if request.user.is_authenticated else None
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Apply date range filters (after search to maintain correct queryset)
        if start_after:
            try:
                start_after_dt = parse_datetime(start_after)
                if start_after_dt is None:
                    return Response(
                        {'error': 'Invalid start_after date. Use ISO 8601 format (e.g., 2025-11-20T10:00:00Z).'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                queryset = queryset.filter(tournament_start__gte=start_after_dt)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid start_after date. Use ISO 8601 format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if start_before:
            try:
                start_before_dt = parse_datetime(start_before)
                if start_before_dt is None:
                    return Response(
                        {'error': 'Invalid start_before date. Use ISO 8601 format (e.g., 2025-11-20T10:00:00Z).'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                queryset = queryset.filter(tournament_start__lte=start_before_dt)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid start_before date. Use ISO 8601 format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Paginate and serialize
        page = self.paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = TournamentListSerializer(page, many=True)
            return self.paginator.get_paginated_response(serializer.data)
        
        # Fallback (no pagination)
        serializer = TournamentListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming(self, request):
        """
        Get upcoming tournaments within next 30 days.
        
        GET /api/tournaments/upcoming/?days=7
        
        Query Parameters:
        - days (int): Number of days to look ahead (default: 30, max: 365)
        - page (int): Page number
        - page_size (int): Items per page
        
        Returns:
        - 200: Paginated list of upcoming tournaments
        - 400: Invalid days parameter
        """
        days_param = request.query_params.get('days', '30')
        try:
            days_ahead = int(days_param)
            if days_ahead < 1 or days_ahead > 365:
                return Response(
                    {'error': 'days must be between 1 and 365'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {'error': 'Invalid days parameter. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get upcoming tournaments from service
        queryset = TournamentDiscoveryService.get_upcoming_tournaments(
            days_ahead=days_ahead,
            user=request.user if request.user.is_authenticated else None
        )
        
        # Paginate and serialize
        page = self.paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = TournamentListSerializer(page, many=True)
            return self.paginator.get_paginated_response(serializer.data)
        
        serializer = TournamentListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='live')
    def live(self, request):
        """
        Get currently live tournaments.
        
        GET /api/tournaments/live/
        
        Query Parameters:
        - page (int): Page number
        - page_size (int): Items per page
        
        Returns:
        - 200: Paginated list of live tournaments
        """
        # Get live tournaments from service
        queryset = TournamentDiscoveryService.get_live_tournaments(
            user=request.user if request.user.is_authenticated else None
        )
        
        # Paginate and serialize
        page = self.paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = TournamentListSerializer(page, many=True)
            return self.paginator.get_paginated_response(serializer.data)
        
        serializer = TournamentListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='featured')
    def featured(self, request):
        """
        Get featured tournaments for homepage/discovery.
        
        GET /api/tournaments/featured/?limit=6
        
        Query Parameters:
        - limit (int): Number of tournaments to return (default: 6, max: 20)
        
        Returns:
        - 200: List of featured tournaments (no pagination)
        
        Note: Featured tournaments are NOT paginated (small, curated list).
        """
        limit_param = request.query_params.get('limit', '6')
        try:
            limit = int(limit_param)
            if limit < 1 or limit > 20:
                return Response(
                    {'error': 'limit must be between 1 and 20'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {'error': 'Invalid limit parameter. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get featured tournaments from service (no pagination)
        queryset = TournamentDiscoveryService.get_featured_tournaments(
            limit=limit,
            user=request.user if request.user.is_authenticated else None
        )
        
        # Serialize without pagination (small, curated list)
        serializer = TournamentListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='by-game/(?P<game_id>[0-9]+)')
    def by_game(self, request, game_id=None):
        """
        Get tournaments for a specific game.
        
        GET /api/tournaments/by-game/1/?include_draft=false
        
        Path Parameters:
        - game_id (int): Game ID
        
        Query Parameters:
        - include_draft (bool): Include draft tournaments (default: false, organizers see own)
        - page (int): Page number
        - page_size (int): Items per page
        
        Returns:
        - 200: Paginated list of tournaments for the game
        - 404: Game not found
        """
        include_draft = request.query_params.get('include_draft', 'false').lower() in ('true', '1', 'yes')
        
        # Get tournaments by game from service
        try:
            queryset = TournamentDiscoveryService.filter_by_game(
                game_id=int(game_id),
                include_draft=include_draft,
                user=request.user if request.user.is_authenticated else None
            )
        except Game.DoesNotExist:
            return Response(
                {'error': f'Game with ID {game_id} not found or is inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {'error': 'Invalid game_id. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Paginate and serialize
        page = self.paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = TournamentListSerializer(page, many=True)
            return self.paginator.get_paginated_response(serializer.data)
        
        serializer = TournamentListSerializer(queryset, many=True)
        return Response(serializer.data)
