"""
Organizer Dashboard Service - Module 2.5

Provides backend aggregation and analytics for tournament organizers.

Source Documents:
- Documents/ExecutionPlan/BACKEND_ONLY_BACKLOG.md (Module 2.5, lines 250-279)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Service Layer Pattern, Section 5.1)
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Dashboard requirements, lines 160-211)

Architecture Decisions:
- ADR-001: Service Layer Pattern - All business logic in services
- ADR-002: IDs-only discipline - Returns participant_id, tournament_id, no names
- ADR-004: PostgreSQL - Uses select_related, prefetch_related, aggregation

Success Criteria (from planning docs):
- Organizer stats API returns correct counts
- Health metrics identify issues (pending payments, disputes)
- Participant breakdown by game/status
- Tests: ≥80% coverage, 25+ tests passing
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
from django.db.models import (
    Q, Count, Sum, Avg, Prefetch, Case, When, IntegerField, F
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.match import Match, Dispute


class DashboardService:
    """
    Service for organizer dashboard data aggregation.
    
    Methods:
        - get_organizer_stats(organizer_id): Overall organizer statistics
        - get_tournament_health(tournament_id): Single tournament health metrics
        - get_participant_breakdown(tournament_id, filters): Participant list with stats
    
    IDs-only Discipline:
        - Returns organizer_id, tournament_id, participant_id (team_id or user_id)
        - Does NOT return names, usernames, emails
        - Frontend resolves IDs via separate API calls
    
    Permission Enforcement:
        - get_tournament_health() and get_participant_breakdown() verify organizer ownership
        - Raises PermissionDenied if user is not organizer/staff
    """
    
    @staticmethod
    def get_organizer_stats(organizer_id: int) -> Dict[str, Any]:
        """
        Get overall statistics for an organizer across all tournaments.
        
        Args:
            organizer_id: User ID of the organizer
        
        Returns:
            Dictionary with:
                - total_tournaments: Total count of tournaments created
                - active_tournaments: Count of currently live/ongoing tournaments
                - total_participants: Sum of confirmed participants across all tournaments
                - total_revenue: Sum of verified entry fee payments (in BDT)
                - pending_actions: Dict with pending_payments, open_disputes counts
        
        Source: BACKEND_ONLY_BACKLOG.md lines 253-254
        
        Example:
            >>> stats = DashboardService.get_organizer_stats(organizer_id=42)
            >>> stats['total_tournaments']
            12
            >>> stats['pending_actions']['pending_payments']
            5
        """
        # Get tournaments (exclude soft-deleted)
        tournaments = Tournament.objects.filter(
            organizer_id=organizer_id,
            deleted_at__isnull=True
        ).select_related('game')
        
        # Total count
        total_tournaments = tournaments.count()
        
        # Active tournaments (live or registration open)
        active_tournaments = tournaments.filter(
            status__in=[
                Tournament.REGISTRATION_OPEN,
                Tournament.LIVE
            ]
        ).count()
        
        # Total participants (confirmed registrations only)
        # Use select_related to optimize (ADR-004)
        total_participants = Registration.objects.filter(
            tournament__organizer_id=organizer_id,
            tournament__deleted_at__isnull=True,
            status=Registration.CONFIRMED,
            deleted_at__isnull=True
        ).count()
        
        # Total revenue (sum of verified payments)
        # Coalesce handles NULL amounts (returns 0 if no payments)
        total_revenue = Payment.objects.filter(
            registration__tournament__organizer_id=organizer_id,
            registration__tournament__deleted_at__isnull=True,
            status=Payment.VERIFIED
        ).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'))
        )['total']
        
        # Pending actions
        # Pending payments count
        pending_payments = Payment.objects.filter(
            registration__tournament__organizer_id=organizer_id,
            registration__tournament__deleted_at__isnull=True,
            status__in=[Payment.PENDING, Payment.SUBMITTED]
        ).count()
        
        # Open disputes count
        open_disputes = Dispute.objects.filter(
            match__tournament__organizer_id=organizer_id,
            match__tournament__deleted_at__isnull=True,
            status__in=[Dispute.OPEN, Dispute.UNDER_REVIEW]
        ).count()
        
        return {
            'organizer_id': organizer_id,
            'total_tournaments': total_tournaments,
            'active_tournaments': active_tournaments,
            'total_participants': total_participants,
            'total_revenue': float(total_revenue),  # Convert Decimal to float for JSON serialization
            'pending_actions': {
                'pending_payments': pending_payments,
                'open_disputes': open_disputes
            }
        }
    
    @staticmethod
    def get_tournament_health(tournament_id: int, requesting_user_id: int) -> Dict[str, Any]:
        """
        Get health metrics for a single tournament.
        
        Args:
            tournament_id: Tournament ID
            requesting_user_id: User requesting the data (for permission check)
        
        Returns:
            Dictionary with:
                - tournament_id: Tournament ID
                - payments: Dict with pending, verified, rejected counts
                - disputes: Dict with open, resolved counts
                - completion_rate: Float (0.0-1.0) of matches completed on time
                - registration_progress: Dict with registered, capacity, percentage
        
        Raises:
            Tournament.DoesNotExist: If tournament not found
            PermissionDenied: If user is not organizer or staff
        
        Source: BACKEND_ONLY_BACKLOG.md lines 254-255
        
        Example:
            >>> health = DashboardService.get_tournament_health(123, requesting_user_id=42)
            >>> health['payments']['pending']
            5
            >>> health['completion_rate']
            0.85
        """
        # Get tournament with permission check
        try:
            tournament = Tournament.objects.select_related('organizer', 'game').get(
                id=tournament_id,
                deleted_at__isnull=True
            )
        except Tournament.DoesNotExist:
            raise Tournament.DoesNotExist(f"Tournament with id={tournament_id} not found")
        
        # Permission check: User must be organizer or staff
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            requesting_user = User.objects.get(id=requesting_user_id)
        except User.DoesNotExist:
            raise PermissionDenied("Invalid user")
        
        if not (tournament.organizer_id == requesting_user_id or requesting_user.is_staff):
            raise PermissionDenied(
                f"User {requesting_user_id} is not authorized to view tournament {tournament_id} health"
            )
        
        # Payment statistics
        # Note: Payment model doesn't have soft delete (no deleted_at field)
        payments_qs = Payment.objects.filter(
            registration__tournament_id=tournament_id,
            registration__deleted_at__isnull=True
        )
        
        payments_stats = payments_qs.aggregate(
            pending=Count('id', filter=Q(status__in=[Payment.PENDING, Payment.SUBMITTED])),
            verified=Count('id', filter=Q(status=Payment.VERIFIED)),
            rejected=Count('id', filter=Q(status=Payment.REJECTED))
        )
        
        # Dispute statistics
        disputes_qs = Dispute.objects.filter(
            match__tournament_id=tournament_id,
            match__deleted_at__isnull=True
        )
        
        disputes_stats = disputes_qs.aggregate(
            open=Count('id', filter=Q(status__in=[Dispute.OPEN, Dispute.UNDER_REVIEW])),
            resolved=Count('id', filter=Q(status=Dispute.RESOLVED))
        )
        
        # Completion rate (matches completed / total matches)
        matches_qs = Match.objects.filter(
            tournament_id=tournament_id,
            deleted_at__isnull=True
        )
        
        total_matches = matches_qs.count()
        completed_matches = matches_qs.filter(state=Match.COMPLETED).count()
        
        completion_rate = (
            (completed_matches / total_matches) if total_matches > 0 else 0.0
        )
        
        # Registration progress
        registrations_qs = Registration.objects.filter(
            tournament_id=tournament_id,
            deleted_at__isnull=True
        )
        
        registered_count = registrations_qs.filter(status=Registration.CONFIRMED).count()
        capacity = tournament.max_participants
        registration_percentage = (
            (registered_count / capacity * 100) if capacity > 0 else 0.0
        )
        
        return {
            'tournament_id': tournament_id,
            'payments': {
                'pending': payments_stats['pending'],
                'verified': payments_stats['verified'],
                'rejected': payments_stats['rejected']
            },
            'disputes': {
                'open': disputes_stats['open'],
                'resolved': disputes_stats['resolved']
            },
            'completion_rate': round(completion_rate, 2),
            'registration_progress': {
                'registered': registered_count,
                'capacity': capacity,
                'percentage': round(registration_percentage, 1)
            }
        }
    
    @staticmethod
    def get_participant_breakdown(
        tournament_id: int,
        requesting_user_id: int,
        filters: Optional[Dict[str, Any]] = None,
        ordering: str = '-registration_date',
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get participant list with filters and match statistics.
        
        Args:
            tournament_id: Tournament ID
            requesting_user_id: User requesting the data (for permission check)
            filters: Optional dict with:
                - payment_status: Payment status filter (PENDING/VERIFIED/REJECTED)
                - check_in_status: Check-in filter (True/False)
                - search: Search term for participant name (not used in service, handled by API)
            ordering: Order by field (default: -registration_date)
            limit: Result limit for pagination
            offset: Result offset for pagination
        
        Returns:
            Dictionary with:
                - count: Total count of participants
                - results: List of participant dicts with:
                    - participant_id: team_id or user_id (IDs-only discipline)
                    - participant_type: 'team' or 'solo'
                    - registration_id: Registration ID
                    - registration_date: ISO datetime string
                    - payment_status: Payment status code
                    - check_in_status: Boolean or 'NOT_CHECKED_IN'/'CHECKED_IN'/'MISSED'
                    - match_stats: Dict with matches_played, wins, losses
        
        Raises:
            Tournament.DoesNotExist: If tournament not found
            PermissionDenied: If user is not organizer or staff
        
        Source: BACKEND_ONLY_BACKLOG.md lines 255-256
        
        Example:
            >>> breakdown = DashboardService.get_participant_breakdown(
            ...     tournament_id=123,
            ...     requesting_user_id=42,
            ...     filters={'payment_status': 'VERIFIED'},
            ...     limit=20,
            ...     offset=0
            ... )
            >>> len(breakdown['results'])
            20
            >>> breakdown['results'][0]['participant_id']
            456
        """
        # Get tournament with permission check
        try:
            tournament = Tournament.objects.select_related('organizer', 'game').get(
                id=tournament_id,
                deleted_at__isnull=True
            )
        except Tournament.DoesNotExist:
            raise Tournament.DoesNotExist(f"Tournament with id={tournament_id} not found")
        
        # Permission check: User must be organizer or staff
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            requesting_user = User.objects.get(id=requesting_user_id)
        except User.DoesNotExist:
            raise PermissionDenied("Invalid user")
        
        if not (tournament.organizer_id == requesting_user_id or requesting_user.is_staff):
            raise PermissionDenied(
                f"User {requesting_user_id} is not authorized to view tournament {tournament_id} participants"
            )
        
        # Base queryset with optimizations (ADR-004)
        # Note: Registration→Payment is OneToOneField, use 'payment' not 'payment_set'
        registrations_qs = Registration.objects.filter(
            tournament_id=tournament_id,
            deleted_at__isnull=True
        ).select_related('user', 'payment')
        
        # Apply filters
        if filters:
            # Payment status filter
            if 'payment_status' in filters:
                payment_status = filters['payment_status']
                registrations_qs = registrations_qs.filter(
                    payment__status=payment_status
                ).distinct()
            
            # Check-in status filter
            if 'check_in_status' in filters:
                check_in_status = filters['check_in_status']
                if isinstance(check_in_status, bool):
                    registrations_qs = registrations_qs.filter(checked_in=check_in_status)
                elif check_in_status == 'CHECKED_IN':
                    registrations_qs = registrations_qs.filter(checked_in=True)
                elif check_in_status == 'NOT_CHECKED_IN':
                    registrations_qs = registrations_qs.filter(checked_in=False)
        
        # Ordering
        valid_orderings = [
            'registration_date', '-registration_date',
            'registered_at', '-registered_at',
            'created_at', '-created_at'
        ]
        if ordering in valid_orderings:
            # Map registration_date to registered_at field
            if 'registration_date' in ordering:
                ordering = ordering.replace('registration_date', 'registered_at')
            registrations_qs = registrations_qs.order_by(ordering)
        else:
            # Default ordering
            registrations_qs = registrations_qs.order_by('-registered_at')
        
        # Total count before pagination
        total_count = registrations_qs.count()
        
        # Pagination
        if offset is not None:
            registrations_qs = registrations_qs[offset:]
        if limit is not None:
            registrations_qs = registrations_qs[:limit]
        
        # Build results with match statistics
        results = []
        for registration in registrations_qs:
            # Determine participant ID and type (IDs-only discipline)
            if tournament.participation_type == Tournament.TEAM:
                participant_id = registration.team_id
                participant_type = 'team'
            else:
                participant_id = registration.user_id
                participant_type = 'solo'
            
            # Get payment status (OneToOne relationship)
            payment_status = None
            if hasattr(registration, 'payment') and registration.payment:
                payment_status = registration.payment.status
            
            # Check-in status
            check_in_status_str = 'CHECKED_IN' if registration.checked_in else 'NOT_CHECKED_IN'
            
            # Match statistics (count wins/losses for this participant)
            # Note: Match uses participant1_id/participant2_id/winner_id (generic IDs for both team and solo)
            matches_as_p1 = Match.objects.filter(
                tournament_id=tournament_id,
                participant1_id=participant_id,
                deleted_at__isnull=True
            )
            matches_as_p2 = Match.objects.filter(
                tournament_id=tournament_id,
                participant2_id=participant_id,
                deleted_at__isnull=True
            )
            
            # Combine querysets
            all_matches = (matches_as_p1 | matches_as_p2).filter(state=Match.COMPLETED)
            matches_played = all_matches.count()
            
            # Count wins (where winner matches participant)
            wins = all_matches.filter(winner_id=participant_id).count()
            
            losses = matches_played - wins
            
            results.append({
                'participant_id': participant_id,
                'participant_type': participant_type,
                'registration_id': registration.id,
                'registration_date': registration.registered_at.isoformat() if registration.registered_at else None,
                'payment_status': payment_status,
                'check_in_status': check_in_status_str,
                'match_stats': {
                    'matches_played': matches_played,
                    'wins': wins,
                    'losses': losses
                }
            })
        
        return {
            'count': total_count,
            'results': results
        }
