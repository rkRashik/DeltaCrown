"""
Analytics Service for Tournament Statistics & Reports (Module 5.4 + 6.2)

Provides read-only aggregation functions for organizer and participant analytics.
All methods return dicts/primitives (no ORM objects). No mutations.

Module 6.2 Enhancement:
- Query materialized view first (if fresh)
- Fallback to live aggregates if view stale or missing
- Freshness threshold: 15 minutes (configurable)
- Cache metadata in API responses

Implements:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md#module-54-analytics--reports
- Documents/ExecutionPlan/PHASE_6_IMPLEMENTATION_PLAN.md#module-62-materialized-views-for-analytics
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md#analyticsservice
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md#adr-001-service-layer-architecture

Source Documents:
- PHASE_5_IMPLEMENTATION_PLAN.md (Module 5.4 scope, metrics definitions)
- PHASE_6_IMPLEMENTATION_PLAN.md (Module 6.2 materialized view optimization)
- PART_2.2_SERVICES_INTEGRATION.md (AnalyticsService methods)
- 01_ARCHITECTURE_DECISIONS.md (ADR-001 service layer patterns, ADR-004 PostgreSQL features)

Author: Module 5.4 implementation, Module 6.2 enhancement
Date: 2025-11-10
"""

import csv
import logging
from typing import Generator, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from io import StringIO

from django.db import connection
from django.db.models import (
    Count, Q, Avg, Sum, Case, When, F,
    Value, CharField, DurationField, ExpressionWrapper
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.conf import settings

from apps.tournaments.models import (
    Tournament,
    Registration,
    Match,
    TournamentResult,
    PrizeTransaction,
)

logger = logging.getLogger(__name__)

# Module 6.2: Materialized view freshness threshold (configurable)
ANALYTICS_FRESHNESS_MINUTES = getattr(settings, 'ANALYTICS_FRESHNESS_MINUTES', 15)


class AnalyticsService:
    """
    Analytics service for tournament statistics and reports.
    
    Module 6.2: Query optimization with materialized views.
    - Queries MV first if fresh (<15 min since refresh)
    - Falls back to live aggregates if stale or missing
    - Returns cache metadata in response
    
    All methods are read-only aggregations. No database mutations.
    Returns dicts/primitives for easy serialization.
    
    Privacy Policy:
    - Display names only (team name or username)
    - No email addresses exposed
    - Registration IDs (not user IDs where possible)
    - Aggregates only (counts, rates, sums)
    """
    
    # ========================================================================
    # MODULE 6.2: MATERIALIZED VIEW HELPERS
    # ========================================================================
    
    @staticmethod
    def _query_analytics_mv(tournament_id: int) -> Optional[Dict[str, Any]]:
        """
        Query materialized view for tournament analytics.
        
        Module 6.2: Fast path for cached analytics.
        
        Args:
            tournament_id: Tournament ID
        
        Returns:
            dict with analytics data + cache metadata, or None if not found
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        tournament_id,
                        tournament_status,
                        total_participants,
                        checked_in_count,
                        check_in_rate,
                        total_matches,
                        completed_matches,
                        disputed_matches,
                        dispute_rate,
                        avg_match_duration_minutes,
                        prize_pool_total,
                        prizes_distributed,
                        payout_count,
                        started_at,
                        concluded_at,
                        last_refresh_at
                    FROM tournament_analytics_summary
                    WHERE tournament_id = %s
                    """,
                    [tournament_id]
                )
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Convert row to dict
                columns = [col[0] for col in cursor.description]
                mv_data = dict(zip(columns, row))
                
                # Convert Decimal to string for consistency with live queries
                mv_data['prize_pool_total'] = AnalyticsService._format_decimal(
                    mv_data['prize_pool_total']
                )
                mv_data['prizes_distributed'] = AnalyticsService._format_decimal(
                    mv_data['prizes_distributed']
                )
                
                # Format timestamps
                mv_data['started_at'] = AnalyticsService._format_datetime(
                    mv_data['started_at']
                )
                mv_data['concluded_at'] = AnalyticsService._format_datetime(
                    mv_data['concluded_at']
                )
                
                return mv_data
        
        except Exception as e:
            logger.warning(
                f"Materialized view query failed for tournament {tournament_id}: {e}",
                exc_info=True
            )
            return None
    
    @staticmethod
    def _is_mv_fresh(last_refresh_at: Optional[datetime], threshold_minutes: int = ANALYTICS_FRESHNESS_MINUTES) -> bool:
        """
        Check if materialized view data is fresh.
        
        Module 6.2: Freshness policy for cache invalidation.
        
        Args:
            last_refresh_at: Timestamp from MV last_refresh_at column
            threshold_minutes: Freshness threshold in minutes (default: 15)
        
        Returns:
            True if data is fresh (age < threshold), False otherwise
        """
        if not last_refresh_at:
            return False
        
        # Make last_refresh_at timezone-aware if naive
        if last_refresh_at.tzinfo is None:
            last_refresh_at = timezone.make_aware(last_refresh_at)
        
        age = timezone.now() - last_refresh_at
        return age < timedelta(minutes=threshold_minutes)
    
    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    @staticmethod
    def calculate_organizer_analytics(tournament_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Calculate tournament-level analytics for organizers.
        
        Module 6.2: Optimized with materialized view (MV-first routing).
        - Queries MV if fresh (<15 min) and not force_refresh
        - Falls back to live aggregates if stale/missing
        - Returns cache metadata in response
        
        Args:
            tournament_id: Tournament ID
            force_refresh: If True, bypass MV and use live queries (default: False)
        
        Returns:
            dict with keys:
                - total_participants (int): Total registrations (CONFIRMED only)
                - checked_in_count (int): Participants who checked in
                - check_in_rate (float): Ratio checked_in / total (0.0-1.0, 4 decimals)
                - total_matches (int): All matches in tournament
                - completed_matches (int): Matches with state=COMPLETED
                - disputed_matches (int): Matches with state=DISPUTED
                - dispute_rate (float): Ratio disputed / total (0.0-1.0, 4 decimals)
                - avg_match_duration_minutes (float|None): Average match duration (nullable)
                - prize_pool_total (str): Tournament prize pool ("1234.50" format)
                - prizes_distributed (str): Total prizes paid out ("1234.50" format)
                - payout_count (int): Number of prize transactions
                - tournament_status (str): Tournament status
                - started_at (str|None): Tournament start time (UTC ISO-8601)
                - concluded_at (str|None): Tournament conclusion time (UTC ISO-8601)
                - cache (dict): Cache metadata
                    - source (str): "materialized" or "live"
                    - as_of (str): UTC ISO-8601 timestamp of data snapshot
                    - age_minutes (float): Age of data in minutes (0 if live)
        
        Raises:
            Tournament.DoesNotExist: If tournament not found
        
        Performance:
            - MV path: <100ms target (cached aggregates)
            - Live path: 400-600ms (annotated aggregates with 5 table joins)
            - Logs warning if execution > 500ms
        """
        start_time = timezone.now()
        
        # Module 6.2: Try materialized view first (if not force_refresh)
        if not force_refresh:
            mv_data = AnalyticsService._query_analytics_mv(tournament_id)
            if mv_data:
                last_refresh_at = mv_data.pop('last_refresh_at', None)
                is_fresh = AnalyticsService._is_mv_fresh(last_refresh_at)
                
                if is_fresh:
                    # Calculate age in minutes
                    age = timezone.now() - last_refresh_at
                    age_minutes = round(age.total_seconds() / 60, 2)
                    
                    # Add cache metadata
                    mv_data['cache'] = {
                        'source': 'materialized',
                        'as_of': last_refresh_at.isoformat() if last_refresh_at else None,
                        'age_minutes': age_minutes
                    }
                    
                    # Performance monitoring (should be <100ms)
                    duration_ms = (timezone.now() - start_time).total_seconds() * 1000
                    logger.info(
                        f"Analytics for tournament {tournament_id} served from MV ({duration_ms:.2f}ms, age {age_minutes:.1f}min)"
                    )
                    
                    return mv_data
                else:
                    # MV exists but stale - fallback to live queries
                    age = timezone.now() - last_refresh_at if last_refresh_at else None
                    age_minutes = round(age.total_seconds() / 60, 2) if age else None
                    logger.info(
                        f"MV stale for tournament {tournament_id} (age {age_minutes:.1f}min > {ANALYTICS_FRESHNESS_MINUTES}min threshold), falling back to live queries"
                    )
        
        try:
            tournament = Tournament.objects.get(id=tournament_id)
            
            # Participant metrics
            registrations = Registration.objects.filter(
                tournament_id=tournament_id,
                status=Registration.CONFIRMED
            )
            total_participants = registrations.count()
            checked_in_count = registrations.filter(checked_in=True).count()
            check_in_rate = AnalyticsService._calculate_check_in_rate(
                checked_in_count, 
                total_participants
            )
            
            # Match metrics
            matches = Match.objects.filter(tournament_id=tournament_id)
            match_stats = matches.aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(state=Match.COMPLETED)),
                disputed=Count('id', filter=Q(state=Match.DISPUTED)),
                avg_duration=Avg(
                    ExpressionWrapper(
                        F('updated_at') - F('created_at'),
                        output_field=DurationField()
                    ),
                    filter=Q(state=Match.COMPLETED)
                )
            )
            
            total_matches = match_stats['total'] or 0
            completed_matches = match_stats['completed'] or 0
            disputed_matches = match_stats['disputed'] or 0
            dispute_rate = AnalyticsService._calculate_dispute_rate(
                disputed_matches,
                total_matches
            )
            
            # Convert avg_duration timedelta to minutes
            avg_match_duration_minutes = None
            if match_stats['avg_duration']:
                avg_match_duration_minutes = round(
                    match_stats['avg_duration'].total_seconds() / 60,
                    4  # 4 decimals for consistency
                )
            
            # Prize metrics
            prize_pool_total = AnalyticsService._format_decimal(
                tournament.prize_pool or Decimal('0.00')
            )
            
            prize_stats = PrizeTransaction.objects.filter(
                tournament_id=tournament_id,
                status=PrizeTransaction.Status.COMPLETED
            ).aggregate(
                total=Coalesce(Sum('amount'), Value(Decimal('0.00'))),
                count=Count('id')
            )
            
            prizes_distributed = AnalyticsService._format_decimal(
                prize_stats['total']
            )
            payout_count = prize_stats['count'] or 0
            
            # Tournament metadata
            tournament_status = tournament.status
            started_at = AnalyticsService._format_datetime(tournament.tournament_start)
            concluded_at = AnalyticsService._format_datetime(
                tournament.updated_at if tournament.status == Tournament.COMPLETED else None
            )
            
            # Performance monitoring
            duration_ms = (timezone.now() - start_time).total_seconds() * 1000
            if duration_ms > 500:
                logger.warning(
                    f"Analytics calculation for tournament {tournament_id} took {duration_ms:.2f}ms (>500ms threshold)"
                )
            else:
                logger.info(
                    f"Analytics for tournament {tournament_id} served from live queries ({duration_ms:.2f}ms)"
                )
            
            # Module 6.2: Add cache metadata for live queries
            cache_metadata = {
                'source': 'live',
                'as_of': timezone.now().isoformat(),
                'age_minutes': 0.0
            }
            
            return {
                'total_participants': total_participants,
                'checked_in_count': checked_in_count,
                'check_in_rate': check_in_rate,
                'total_matches': total_matches,
                'completed_matches': completed_matches,
                'disputed_matches': disputed_matches,
                'dispute_rate': dispute_rate,
                'avg_match_duration_minutes': avg_match_duration_minutes,
                'prize_pool_total': prize_pool_total,
                'prizes_distributed': prizes_distributed,
                'payout_count': payout_count,
                'tournament_status': tournament_status,
                'started_at': started_at,
                'concluded_at': concluded_at,
                'cache': cache_metadata,
            }
        
        except Tournament.DoesNotExist:
            logger.error(f"Tournament {tournament_id} not found for analytics")
            raise
    
    @staticmethod
    def calculate_participant_analytics(user_id: int) -> Dict[str, Any]:
        """
        Calculate participant analytics across all tournaments.
        
        Args:
            user_id: User ID
        
        Returns:
            dict with keys:
                - total_tournaments (int): Total tournaments participated
                - tournaments_won (int): 1st place finishes
                - runner_up_count (int): 2nd place finishes
                - third_place_count (int): 3rd place finishes
                - total_matches_played (int): All matches (as participant_1 or participant_2)
                - matches_won (int): Matches where user won
                - matches_lost (int): Matches where user lost
                - win_rate (float): Ratio wins / total (0.0-1.0, 4 decimals)
                - total_prize_winnings (str): Sum of all prize payouts ("1234.50" format)
                - best_placement (str|None): Best finish ("1st"/"2nd"/"3rd"/None)
                - tournaments_by_game (dict): {game_slug: count}
        
        Performance:
            - Uses annotated aggregates (no Python loops)
            - Logs warning if execution > 500ms
        """
        start_time = timezone.now()
        
        # Get all registrations for user
        registrations = Registration.objects.filter(
            user_id=user_id,
            status=Registration.CONFIRMED
        ).select_related('tournament__game')
        
        total_tournaments = registrations.count()
        
        # Placement metrics
        registration_ids = list(registrations.values_list('id', flat=True))
        
        placement_stats = TournamentResult.objects.filter(
            Q(winner_id__in=registration_ids) |
            Q(runner_up_id__in=registration_ids) |
            Q(third_place_id__in=registration_ids)
        ).aggregate(
            wins=Count('id', filter=Q(winner_id__in=registration_ids)),
            runner_ups=Count('id', filter=Q(runner_up_id__in=registration_ids)),
            third_places=Count('id', filter=Q(third_place_id__in=registration_ids))
        )
        
        tournaments_won = placement_stats['wins'] or 0
        runner_up_count = placement_stats['runner_ups'] or 0
        third_place_count = placement_stats['third_places'] or 0
        
        # Best placement
        best_placement = AnalyticsService._determine_best_placement(
            tournaments_won,
            runner_up_count,
            third_place_count
        )
        
        # Match metrics
        match_stats = Match.objects.filter(
            Q(participant1_id__in=registration_ids) |
            Q(participant2_id__in=registration_ids),
            state=Match.COMPLETED
        ).aggregate(
            total=Count('id'),
            wins=Count('id', filter=Q(winner_id__in=registration_ids))
        )
        
        total_matches_played = match_stats['total'] or 0
        matches_won = match_stats['wins'] or 0
        matches_lost = total_matches_played - matches_won
        
        win_rate = AnalyticsService._calculate_win_rate(
            matches_won,
            total_matches_played
        )
        
        # Prize winnings
        prize_stats = PrizeTransaction.objects.filter(
            participant_id__in=registration_ids,
            status=PrizeTransaction.Status.COMPLETED
        ).aggregate(
            total=Coalesce(Sum('amount'), Value(Decimal('0.00')))
        )
        
        total_prize_winnings = AnalyticsService._format_decimal(
            prize_stats['total']
        )
        
        # Tournaments by game
        tournaments_by_game = {}
        for reg in registrations:
            from apps.games.services import game_service
            game_slug = game_service.normalize_slug(reg.tournament.game.slug) if reg.tournament.game else ''
            tournaments_by_game[game_slug] = tournaments_by_game.get(game_slug, 0) + 1
        
        # Performance monitoring
        duration_ms = (timezone.now() - start_time).total_seconds() * 1000
        if duration_ms > 500:
            logger.warning(
                f"Participant analytics for user {user_id} took {duration_ms:.2f}ms (>500ms threshold)"
            )
        
        return {
            'total_tournaments': total_tournaments,
            'tournaments_won': tournaments_won,
            'runner_up_count': runner_up_count,
            'third_place_count': third_place_count,
            'total_matches_played': total_matches_played,
            'matches_won': matches_won,
            'matches_lost': matches_lost,
            'win_rate': win_rate,
            'total_prize_winnings': total_prize_winnings,
            'best_placement': best_placement,
            'tournaments_by_game': tournaments_by_game,
        }
    
    @staticmethod
    def export_tournament_csv(tournament_id: int) -> Generator[str, None, None]:
        """
        Export tournament data as streaming CSV.
        
        Memory-bounded: yields rows one at a time (no full dataset in memory).
        
        Args:
            tournament_id: Tournament ID
        
        Yields:
            CSV rows as strings (header first, then data rows)
        
        CSV Columns:
            - participant_id: Registration ID
            - participant_name: Display name (team or username, no PII)
            - registration_status: Registration status
            - checked_in: Boolean (True/False)
            - checked_in_at: Check-in timestamp (UTC ISO-8601)
            - matches_played: Count
            - matches_won: Count
            - matches_lost: Count
            - placement: "1st"/"2nd"/"3rd"/None
            - prize_amount: Decimal ("1234.50" format)
            - registration_created_at: Timestamp (UTC ISO-8601)
            - payment_status: Payment status
        
        Encoding: UTF-8 with BOM (Excel compatibility)
        Delimiter: comma
        Quote: minimal
        Newline: \\n
        
        Raises:
            Tournament.DoesNotExist: If tournament not found
        
        Performance:
            - Streaming: no list accumulation
            - Prefetch related data (select_related, prefetch_related)
            - Yields header then rows iteratively
        """
        # Verify tournament exists
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            logger.error(f"Tournament {tournament_id} not found for CSV export")
            raise
        
        # CSV header with UTF-8 BOM for Excel
        output = StringIO()
        writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        
        # Write BOM for UTF-8 Excel compatibility
        yield '\ufeff'
        
        # Write header
        writer.writerow([
            'participant_id',
            'participant_name',
            'registration_status',
            'checked_in',
            'checked_in_at',
            'matches_played',
            'matches_won',
            'matches_lost',
            'placement',
            'prize_amount',
            'registration_created_at',
            'payment_status',
        ])
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)
        
        # Fetch registrations with related data (team_id is IntegerField, not FK)
        registrations = Registration.objects.filter(
            tournament_id=tournament_id
        ).select_related(
            'user',
        ).order_by('id')
        
        # Get TournamentResult for placements
        try:
            result = TournamentResult.objects.get(tournament_id=tournament_id)
            winner_id = result.winner_id
            runner_up_id = result.runner_up_id
            third_place_id = result.third_place_id
        except TournamentResult.DoesNotExist:
            winner_id = runner_up_id = third_place_id = None
        
        # Stream rows
        for reg in registrations:
            # Get display name (no PII)
            participant_name = AnalyticsService._get_participant_display_name(reg)
            
            # Match stats
            match_stats = Match.objects.filter(
                Q(participant1_id=reg.id) | Q(participant2_id=reg.id),
                state=Match.COMPLETED
            ).aggregate(
                total=Count('id'),
                wins=Count('id', filter=Q(winner_id=reg.id))
            )
            
            matches_played = match_stats['total'] or 0
            matches_won = match_stats['wins'] or 0
            matches_lost = matches_played - matches_won
            
            # Placement
            placement = None
            if reg.id == winner_id:
                placement = '1st'
            elif reg.id == runner_up_id:
                placement = '2nd'
            elif reg.id == third_place_id:
                placement = '3rd'
            
            # Prize amount
            try:
                prize = PrizeTransaction.objects.get(
                    participant_id=reg.id,
                    status=PrizeTransaction.Status.COMPLETED
                )
                prize_amount = AnalyticsService._format_decimal(prize.amount)
            except PrizeTransaction.DoesNotExist:
                prize_amount = '0.00'
            
            # Payment status (payment might not exist for all registrations)
            payment_status = 'No Payment'  # Default, actual payment tracking TBD
            
            # Write row
            writer.writerow([
                reg.id,
                participant_name,
                reg.status,
                'True' if reg.checked_in else 'False',
                AnalyticsService._format_datetime(reg.checked_in_at),
                matches_played,
                matches_won,
                matches_lost,
                placement or '',
                prize_amount,
                AnalyticsService._format_datetime(reg.created_at),
                payment_status,
            ])
            
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)
    
    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================
    
    @staticmethod
    def _calculate_check_in_rate(checked_in_count: int, total_participants: int) -> float:
        """
        Calculate check-in rate as ratio.
        
        Args:
            checked_in_count: Number checked in
            total_participants: Total participants
        
        Returns:
            float: Ratio 0.0-1.0, rounded to 4 decimals
        """
        if total_participants == 0:
            return 0.0
        return round(checked_in_count / total_participants, 4)
    
    @staticmethod
    def _calculate_dispute_rate(disputed_matches: int, total_matches: int) -> float:
        """
        Calculate dispute rate as ratio.
        
        Args:
            disputed_matches: Number disputed
            total_matches: Total matches
        
        Returns:
            float: Ratio 0.0-1.0, rounded to 4 decimals
        """
        if total_matches == 0:
            return 0.0
        return round(disputed_matches / total_matches, 4)
    
    @staticmethod
    def _calculate_win_rate(matches_won: int, total_matches: int) -> float:
        """
        Calculate win rate as ratio.
        
        Args:
            matches_won: Matches won
            total_matches: Total matches played
        
        Returns:
            float: Ratio 0.0-1.0, rounded to 4 decimals
        """
        if total_matches == 0:
            return 0.0
        return round(matches_won / total_matches, 4)
    
    @staticmethod
    def _determine_best_placement(
        wins: int,
        runner_ups: int,
        third_places: int
    ) -> Optional[str]:
        """
        Determine best placement from counts.
        
        Args:
            wins: 1st place count
            runner_ups: 2nd place count
            third_places: 3rd place count
        
        Returns:
            str: "1st", "2nd", "3rd", or None
        """
        if wins > 0:
            return '1st'
        elif runner_ups > 0:
            return '2nd'
        elif third_places > 0:
            return '3rd'
        return None
    
    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        """
        Format Decimal as string with 2 decimal places.
        
        Args:
            value: Decimal value
        
        Returns:
            str: Formatted string (e.g., "1234.50")
        """
        return f"{value:.2f}"
    
    @staticmethod
    def _format_datetime(dt: Optional[datetime]) -> Optional[str]:
        """
        Format datetime as UTC ISO-8601 with Z suffix.
        
        Args:
            dt: Datetime object (timezone-aware)
        
        Returns:
            str: ISO-8601 string with Z suffix (e.g., "2025-11-10T12:34:56Z")
            None: If dt is None
        """
        if dt is None:
            return None
        
        # Convert to UTC if not already
        if timezone.is_aware(dt):
            dt_utc = dt.astimezone(dt_timezone.utc)
        else:
            dt_utc = timezone.make_aware(dt, dt_timezone.utc)
        
        # Format as ISO-8601 with Z suffix (no microseconds)
        return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    @staticmethod
    def _get_participant_display_name(registration: Registration) -> str:
        """
        Get participant display name (no PII).
        
        Returns team name if team registration, otherwise username.
        Never returns email addresses.
        
        Args:
            registration: Registration object (with user prefetched)
        
        Returns:
            str: Display name (team.name or user.username)
        """
        if registration.team_id:
            # team_id is IntegerField, need to fetch Team model
            from apps.organizations.models import Team
            try:
                team = Team.objects.get(id=registration.team_id)
                return team.name
            except Team.DoesNotExist:
                return f"Team {registration.team_id}"
        return registration.user.username if registration.user else "Unknown"


# Export singleton instance
analytics_service = AnalyticsService()
