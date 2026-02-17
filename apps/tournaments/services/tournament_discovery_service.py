"""
Tournament Discovery Service - Search and filter operations for tournaments.

Source Documents:
- Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md (Module 2.4, Lines 214-241)
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Section 5.1, Lines 455-555)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Tournament model fields)
- Documents/Planning/PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md (Query patterns & indexes)

Architecture Decisions:
- ADR-001: Service Layer Pattern - All discovery logic in service layer
- ADR-004: PostgreSQL Full-Text Search - Use built-in search capabilities

Responsibilities:
- Full-text search on tournament name, description
- Filter by game, status, date range, prize pool, entry fee, format
- Ordering by date, prize, popularity
- Query optimization with select_related/prefetch_related
- Visibility and permission logic

Usage:
    from apps.tournaments.services import TournamentDiscoveryService
    
    # Search tournaments
    tournaments = TournamentDiscoveryService.search_tournaments(
        query='valorant',
        filters={'game_id': 1, 'status': 'published'}
    )
    
    # Filter by game
    tournaments = TournamentDiscoveryService.filter_by_game(
        game_id=1,
        include_draft=False
    )
    
    # Filter by date range
    tournaments = TournamentDiscoveryService.filter_by_date_range(
        start_date=datetime(2025, 11, 1),
        end_date=datetime(2025, 11, 30)
    )
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Q, QuerySet, Count, Prefetch
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.utils import timezone
from apps.tournaments.models.tournament import Tournament
from apps.games.models.game import Game


class TournamentDiscoveryService:
    """
    Service class for tournament discovery and filtering.
    
    Provides optimized query methods for searching and filtering tournaments
    with proper permission handling and query optimization.
    """
    
    @staticmethod
    def search_tournaments(
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        ordering: str = '-tournament_start',
        user = None
    ) -> QuerySet:
        """
        Full-text search tournaments by name and description.
        
        Args:
            query: Search query string (searches name, description, game name)
            filters: Optional dictionary of additional filters:
                - game_id (int): Filter by game ID
                - status (str or list): Filter by status(es)
                - format (str): Filter by tournament format
                - has_entry_fee (bool): Filter by entry fee presence
                - is_official (bool): Filter official tournaments
            ordering: Field to order by (default: '-tournament_start')
                Options: 'tournament_start', '-tournament_start', 
                         'prize_pool', '-prize_pool', 'created_at', '-created_at'
            user: User performing search (for permission checks)
        
        Returns:
            QuerySet: Filtered and ordered tournament queryset
        
        Raises:
            ValueError: If ordering field is invalid
        
        Example:
            >>> tournaments = TournamentDiscoveryService.search_tournaments(
            ...     query='valorant cup',
            ...     filters={'status': 'published', 'is_official': True},
            ...     ordering='-prize_pool'
            ... )
        """
        # Start with base queryset
        queryset = TournamentDiscoveryService._get_base_queryset(user)
        
        # Apply full-text search
        if query and query.strip():
            search_vector = SearchVector('name', weight='A') + \
                           SearchVector('description', weight='B') + \
                           SearchVector('game__name', weight='A')
            search_query = SearchQuery(query)
            
            queryset = queryset.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query)
            ).filter(search=search_query).order_by('-rank')
        
        # Apply additional filters
        if filters:
            queryset = TournamentDiscoveryService._apply_filters(queryset, filters)
        
        # Apply ordering (if not search-based ordering)
        if not query or not query.strip():
            valid_orderings = [
                'tournament_start', '-tournament_start',
                'prize_pool', '-prize_pool',
                'created_at', '-created_at',
                'registration_start', '-registration_start'
            ]
            if ordering not in valid_orderings:
                raise ValueError(f"Invalid ordering field: {ordering}")
            queryset = queryset.order_by(ordering)
        
        return queryset
    
    @staticmethod
    def filter_by_game(
        game_id: int,
        include_draft: bool = False,
        user = None
    ) -> QuerySet:
        """
        Filter tournaments by game.
        
        Args:
            game_id: ID of the game to filter by
            include_draft: Whether to include DRAFT tournaments (default: False)
                Note: For non-staff users, this only includes their own drafts
            user: User performing filter (for permission checks)
        
        Returns:
            QuerySet: Tournaments for the specified game
        
        Raises:
            Game.DoesNotExist: If game_id is invalid
        
        Example:
            >>> tournaments = TournamentDiscoveryService.filter_by_game(
            ...     game_id=1,
            ...     include_draft=False
            ... )
        """
        # Validate game exists
        game = Game.objects.get(id=game_id, is_active=True)
        
        # Get base queryset with visibility filters
        # Note: _get_base_queryset already handles draft visibility
        # Staff can see all, regular users see own drafts, anonymous see none
        queryset = TournamentDiscoveryService._get_base_queryset(user)
        
        # Filter by game
        queryset = queryset.filter(game=game)
        
        # Exclude drafts unless requested AND user has permission
        # This is redundant with _get_base_queryset but kept for clarity
        if not include_draft:
            queryset = queryset.exclude(status=Tournament.DRAFT)
        
        # Order by tournament start date (upcoming first)
        queryset = queryset.order_by('tournament_start')
        
        return queryset
    
    @staticmethod
    def filter_by_date_range(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_filter_type: str = 'tournament_start',
        user = None
    ) -> QuerySet:
        """
        Filter tournaments by date range.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            date_filter_type: Which date field to filter on:
                - 'tournament_start' (default): Filter by tournament start date
                - 'registration_start': Filter by registration start date
                - 'registration_end': Filter by registration end date
            user: User performing filter (for permission checks)
        
        Returns:
            QuerySet: Tournaments within the specified date range
        
        Raises:
            ValueError: If date_filter_type is invalid or dates are inconsistent
        
        Example:
            >>> # Get tournaments starting in November 2025
            >>> tournaments = TournamentDiscoveryService.filter_by_date_range(
            ...     start_date=datetime(2025, 11, 1),
            ...     end_date=datetime(2025, 11, 30),
            ...     date_filter_type='tournament_start'
            ... )
        """
        # Validate date_filter_type
        valid_types = ['tournament_start', 'registration_start', 'registration_end']
        if date_filter_type not in valid_types:
            raise ValueError(f"Invalid date_filter_type: {date_filter_type}")
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        # Get base queryset
        queryset = TournamentDiscoveryService._get_base_queryset(user)
        
        # Apply date filters
        filter_kwargs = {}
        if start_date:
            filter_kwargs[f'{date_filter_type}__gte'] = start_date
        if end_date:
            filter_kwargs[f'{date_filter_type}__lte'] = end_date
        
        if filter_kwargs:
            queryset = queryset.filter(**filter_kwargs)
        
        # Order by the filtered date field
        queryset = queryset.order_by(date_filter_type)
        
        return queryset
    
    @staticmethod
    def filter_by_status(
        status: str,
        user = None
    ) -> QuerySet:
        """
        Filter tournaments by status.
        
        Args:
            status: Tournament status to filter by:
                - 'draft': Draft tournaments
                - 'published': Published tournaments
                - 'registration_open': Registration currently open
                - 'registration_closed': Registration closed
                - 'live': Currently ongoing
                - 'completed': Finished tournaments
                - 'cancelled': Cancelled tournaments
                - 'upcoming': All upcoming tournaments (published + registration_open)
                - 'active': All active tournaments (registration_open + live)
            user: User performing filter (for permission checks)
        
        Returns:
            QuerySet: Tournaments with the specified status
        
        Raises:
            ValueError: If status is invalid
        
        Example:
            >>> tournaments = TournamentDiscoveryService.filter_by_status(
            ...     status='registration_open'
            ... )
        """
        # Get base queryset
        queryset = TournamentDiscoveryService._get_base_queryset(user)
        
        # Handle special status filters
        if status == 'upcoming':
            queryset = queryset.filter(
                status__in=[Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN]
            )
        elif status == 'active':
            queryset = queryset.filter(
                status__in=[Tournament.REGISTRATION_OPEN, Tournament.LIVE]
            )
        else:
            # Validate single status
            valid_statuses = [
                Tournament.DRAFT, Tournament.PENDING_APPROVAL, Tournament.PUBLISHED,
                Tournament.REGISTRATION_OPEN, Tournament.REGISTRATION_CLOSED,
                Tournament.LIVE, Tournament.COMPLETED, Tournament.CANCELLED,
                Tournament.ARCHIVED
            ]
            if status not in valid_statuses:
                raise ValueError(f"Invalid status: {status}")
            queryset = queryset.filter(status=status)
        
        # Order by tournament start date
        queryset = queryset.order_by('tournament_start')
        
        return queryset
    
    @staticmethod
    def filter_by_prize_pool(
        min_prize: Optional[Decimal] = None,
        max_prize: Optional[Decimal] = None,
        user = None
    ) -> QuerySet:
        """
        Filter tournaments by prize pool range.
        
        Args:
            min_prize: Minimum prize pool amount (inclusive)
            max_prize: Maximum prize pool amount (inclusive)
            user: User performing filter (for permission checks)
        
        Returns:
            QuerySet: Tournaments within the prize pool range
        
        Raises:
            ValueError: If prize values are invalid
        
        Example:
            >>> # Get tournaments with prize pool between 10,000 and 50,000 BDT
            >>> tournaments = TournamentDiscoveryService.filter_by_prize_pool(
            ...     min_prize=Decimal('10000.00'),
            ...     max_prize=Decimal('50000.00')
            ... )
        """
        # Validate prize values
        if min_prize and min_prize < Decimal('0.00'):
            raise ValueError("min_prize cannot be negative")
        if max_prize and max_prize < Decimal('0.00'):
            raise ValueError("max_prize cannot be negative")
        if min_prize and max_prize and min_prize > max_prize:
            raise ValueError("min_prize must be less than or equal to max_prize")
        
        # Get base queryset
        queryset = TournamentDiscoveryService._get_base_queryset(user)
        
        # Apply prize filters
        if min_prize is not None:
            queryset = queryset.filter(prize_pool__gte=min_prize)
        if max_prize is not None:
            queryset = queryset.filter(prize_pool__lte=max_prize)
        
        # Order by prize pool (highest first)
        queryset = queryset.order_by('-prize_pool')
        
        return queryset
    
    @staticmethod
    def filter_by_entry_fee(
        min_fee: Optional[Decimal] = None,
        max_fee: Optional[Decimal] = None,
        free_only: bool = False,
        user = None
    ) -> QuerySet:
        """
        Filter tournaments by entry fee range.
        
        Args:
            min_fee: Minimum entry fee amount (inclusive)
            max_fee: Maximum entry fee amount (inclusive)
            free_only: If True, return only free tournaments (default: False)
            user: User performing filter (for permission checks)
        
        Returns:
            QuerySet: Tournaments within the entry fee range
        
        Raises:
            ValueError: If fee values are invalid
        
        Example:
            >>> # Get free tournaments
            >>> tournaments = TournamentDiscoveryService.filter_by_entry_fee(
            ...     free_only=True
            ... )
            
            >>> # Get tournaments with entry fee 0-500 BDT
            >>> tournaments = TournamentDiscoveryService.filter_by_entry_fee(
            ...     min_fee=Decimal('0.00'),
            ...     max_fee=Decimal('500.00')
            ... )
        """
        # Validate fee values
        if min_fee and min_fee < Decimal('0.00'):
            raise ValueError("min_fee cannot be negative")
        if max_fee and max_fee < Decimal('0.00'):
            raise ValueError("max_fee cannot be negative")
        if min_fee and max_fee and min_fee > max_fee:
            raise ValueError("min_fee must be less than or equal to max_fee")
        
        # Get base queryset
        queryset = TournamentDiscoveryService._get_base_queryset(user)
        
        # Handle free-only filter
        if free_only:
            queryset = queryset.filter(has_entry_fee=False)
        else:
            # Apply fee range filters
            if min_fee is not None:
                queryset = queryset.filter(entry_fee_amount__gte=min_fee)
            if max_fee is not None:
                queryset = queryset.filter(entry_fee_amount__lte=max_fee)
        
        # Order by entry fee (lowest first)
        queryset = queryset.order_by('entry_fee_amount')
        
        return queryset
    
    @staticmethod
    def filter_by_format(
        format: str,
        user = None
    ) -> QuerySet:
        """
        Filter tournaments by format type.
        
        Args:
            format: Tournament format:
                - 'single_elimination': Single elimination bracket
                - 'double_elimination': Double elimination bracket
                - 'round_robin': Round robin format
                - 'swiss': Swiss system
                - 'group_playoff': Group stage + playoff
            user: User performing filter (for permission checks)
        
        Returns:
            QuerySet: Tournaments with the specified format
        
        Raises:
            ValueError: If format is invalid
        
        Example:
            >>> tournaments = TournamentDiscoveryService.filter_by_format(
            ...     format='single_elimination'
            ... )
        """
        # Validate format
        valid_formats = [
            Tournament.SINGLE_ELIM, Tournament.DOUBLE_ELIM,
            Tournament.ROUND_ROBIN, Tournament.SWISS, Tournament.GROUP_PLAYOFF
        ]
        if format not in valid_formats:
            raise ValueError(f"Invalid format: {format}")
        
        # Get base queryset
        queryset = TournamentDiscoveryService._get_base_queryset(user)
        
        # Filter by format
        queryset = queryset.filter(format=format)
        
        # Order by tournament start date
        queryset = queryset.order_by('tournament_start')
        
        return queryset
    
    @staticmethod
    def get_upcoming_tournaments(
        days_ahead: int = 30,
        user = None
    ) -> QuerySet:
        """
        Get upcoming tournaments within specified days.
        
        Args:
            days_ahead: Number of days to look ahead (default: 30)
            user: User performing query (for permission checks)
        
        Returns:
            QuerySet: Upcoming tournaments within the timeframe
        
        Example:
            >>> # Get tournaments starting in the next 7 days
            >>> tournaments = TournamentDiscoveryService.get_upcoming_tournaments(
            ...     days_ahead=7
            ... )
        """
        now = timezone.now()
        end_date = now + timedelta(days=days_ahead)
        
        # Get base queryset
        queryset = TournamentDiscoveryService._get_base_queryset(user)
        
        # Filter by upcoming date range
        queryset = queryset.filter(
            tournament_start__gte=now,
            tournament_start__lte=end_date,
            status__in=[Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN]
        )
        
        # Order by tournament start date (soonest first)
        queryset = queryset.order_by('tournament_start')
        
        return queryset
    
    @staticmethod
    def get_live_tournaments(user = None) -> QuerySet:
        """
        Get currently live tournaments.
        
        Args:
            user: User performing query (for permission checks)
        
        Returns:
            QuerySet: Tournaments currently in progress
        
        Example:
            >>> tournaments = TournamentDiscoveryService.get_live_tournaments()
        """
        # Get base queryset
        queryset = TournamentDiscoveryService._get_base_queryset(user)
        
        # Filter by live status
        queryset = queryset.filter(status=Tournament.LIVE)
        
        # Order by tournament start date (most recent first)
        queryset = queryset.order_by('-tournament_start')
        
        return queryset
    
    @staticmethod
    def get_featured_tournaments(
        limit: int = 6,
        user = None
    ) -> QuerySet:
        """
        Get featured tournaments for homepage/discovery.
        
        Prioritizes:
        1. Official tournaments
        2. High prize pools
        3. Popular games
        4. Upcoming/live status
        
        Args:
            limit: Maximum number of tournaments to return (default: 6)
            user: User performing query (for permission checks)
        
        Returns:
            QuerySet: Featured tournaments
        
        Example:
            >>> tournaments = TournamentDiscoveryService.get_featured_tournaments(
            ...     limit=6
            ... )
        """
        # Get base queryset
        queryset = TournamentDiscoveryService._get_base_queryset(user)
        
        # Filter for visible, upcoming or live tournaments
        queryset = queryset.filter(
            status__in=[
                Tournament.REGISTRATION_OPEN,
                Tournament.LIVE,
                Tournament.PUBLISHED
            ]
        )
        
        # Order by: official first, then by prize pool
        queryset = queryset.order_by('-is_official', '-prize_pool', 'tournament_start')
        
        # Limit results
        return queryset[:limit]
    
    # =====================================================================
    # PRIVATE HELPER METHODS
    # =====================================================================
    
    @staticmethod
    def _get_base_queryset(user = None) -> QuerySet:
        """
        Get optimized base queryset with visibility filters and select_related.
        
        Args:
            user: User performing query (for permission checks)
        
        Returns:
            QuerySet: Optimized base queryset
        """
        # Start with all tournaments
        queryset = Tournament.objects.all()
        
        # Apply visibility filters
        if user and user.is_authenticated:
            if user.is_staff:
                # Staff can see all tournaments
                pass
            else:
                # Regular users: see public tournaments + own drafts
                queryset = queryset.filter(
                    Q(status__in=[
                        Tournament.PUBLISHED,
                        Tournament.REGISTRATION_OPEN,
                        Tournament.REGISTRATION_CLOSED,
                        Tournament.LIVE,
                        Tournament.COMPLETED
                    ]) |
                    Q(organizer=user)
                )
        else:
            # Anonymous users: only see public tournaments
            queryset = queryset.filter(
                status__in=[
                    Tournament.PUBLISHED,
                    Tournament.REGISTRATION_OPEN,
                    Tournament.REGISTRATION_CLOSED,
                    Tournament.LIVE,
                    Tournament.COMPLETED
                ]
            )
        
        # Exclude soft-deleted tournaments
        queryset = queryset.filter(is_deleted=False)
        
        # Optimize with select_related (reduce queries)
        queryset = queryset.select_related(
            'game',
            'organizer',
        )
        
        # Annotate with participant count (for sorting/filtering)
        # Note: Depends on Registration model being available (future module)
        # queryset = queryset.annotate(
        #     participant_count=Count('registrations', distinct=True)
        # )
        
        return queryset
    
    @staticmethod
    def _apply_filters(queryset: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        """
        Apply multiple filters to a queryset.
        
        Args:
            queryset: Base queryset to filter
            filters: Dictionary of filter criteria
        
        Returns:
            QuerySet: Filtered queryset
        """
        # Game filter
        if 'game_id' in filters and filters['game_id']:
            queryset = queryset.filter(game_id=filters['game_id'])
        
        # Status filter (single or multiple)
        if 'status' in filters and filters['status']:
            status = filters['status']
            if isinstance(status, list):
                queryset = queryset.filter(status__in=status)
            else:
                queryset = queryset.filter(status=status)
        
        # Format filter
        if 'format' in filters and filters['format']:
            queryset = queryset.filter(format=filters['format'])
        
        # Entry fee filter
        if 'has_entry_fee' in filters and filters['has_entry_fee'] is not None:
            queryset = queryset.filter(has_entry_fee=filters['has_entry_fee'])
        
        # Official tournament filter
        if 'is_official' in filters and filters['is_official'] is not None:
            queryset = queryset.filter(is_official=filters['is_official'])
        
        # Prize pool range
        if 'min_prize' in filters and filters['min_prize'] is not None:
            queryset = queryset.filter(prize_pool__gte=filters['min_prize'])
        if 'max_prize' in filters and filters['max_prize'] is not None:
            queryset = queryset.filter(prize_pool__lte=filters['max_prize'])
        
        # Entry fee range
        if 'min_fee' in filters and filters['min_fee'] is not None:
            queryset = queryset.filter(entry_fee_amount__gte=filters['min_fee'])
        if 'max_fee' in filters and filters['max_fee'] is not None:
            queryset = queryset.filter(entry_fee_amount__lte=filters['max_fee'])
        
        # Participation type
        if 'participation_type' in filters and filters['participation_type']:
            queryset = queryset.filter(participation_type=filters['participation_type'])
        
        return queryset
