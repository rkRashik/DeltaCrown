"""
User Activity Recording Service

Creates UserActivity events with idempotency guarantees.

Design Principles:
1. Idempotent - Safe to call multiple times for same event
2. Atomic - Event creation is transactional
3. Source-tracked - Every event linked to source (tournament/match/transaction)
4. Immutable - Events never updated/deleted after creation

Usage:
    from apps.user_profile.services.activity_service import UserActivityService
    
    # Record tournament join
    event = UserActivityService.record_tournament_join(
        user_id=123,
        tournament_id=456,
        registration_id=789
    )
    
    # Record match result
    winner_event = UserActivityService.record_match_result(
        match_id=100,
        winner_id=123,
        loser_id=124
    )
    
    # Record economy transaction
    event = UserActivityService.record_economy_transaction(
        transaction_id=999,
        user_id=123,
        amount=100.00,
        reason='TOURNAMENT_WIN'
    )
"""

from django.db import transaction
from django.utils import timezone
from apps.user_profile.models.activity import UserActivity, EventType
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class UserActivityService:
    """Service for recording user activity events."""
    
    @staticmethod
    def _record_event(
        event_type: str,
        user_id: int,
        source_type: str,
        source_id: int,
        event_data: dict,
        timestamp: Optional[timezone.datetime] = None
    ) -> Optional[UserActivity]:
        """
        Record an activity event with idempotency.
        
        Args:
            event_type: Event type from EventType choices
            user_id: User ID
            source_type: Source type (tournament/match/economy/system)
            source_id: Source record ID
            event_data: Additional event metadata (JSON)
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            UserActivity instance, or None if event already exists (idempotent)
        """
        # Check if event already exists (idempotency)
        existing = UserActivity.objects.filter(
            event_type=event_type,
            user_id=user_id,
            source_model=source_type,
            source_id=source_id
        ).first()
        
        if existing:
            logger.debug(
                f"Event already exists: {event_type} for user {user_id} "
                f"from {source_type} {source_id}"
            )
            return None
        
        # Create new event
        try:
            with transaction.atomic():
                event = UserActivity.objects.create(
                    event_type=event_type,
                    user_id=user_id,
                    source_model=source_type,
                    source_id=source_id,
                    metadata=event_data or {},
                    timestamp=timestamp or timezone.now()
                )
                logger.info(
                    f"Created event: {event_type} for user {user_id} "
                    f"from {source_type} {source_id}"
                )
                return event
        except Exception as e:
            logger.error(
                f"Failed to create event {event_type} for user {user_id}: {e}",
                exc_info=True
            )
            raise
    
    @classmethod
    def record_tournament_join(
        cls,
        user_id: int,
        tournament_id: int,
        registration_id: int,
        timestamp: Optional[timezone.datetime] = None
    ) -> Optional[UserActivity]:
        """
        Record TOURNAMENT_JOINED event.
        
        Args:
            user_id: User who joined
            tournament_id: Tournament ID
            registration_id: Registration record ID
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            UserActivity instance or None if already exists
        """
        return cls._record_event(
            event_type=EventType.TOURNAMENT_JOINED,
            user_id=user_id,
            source_type='registration',
            source_id=registration_id,  # Use registration as source
            event_data={
                'tournament_id': tournament_id,
                'registration_id': registration_id,
            },
            timestamp=timestamp
        )
    
    @classmethod
    def record_tournament_placed(
        cls,
        user_id: int,
        tournament_id: int,
        placement: int,
        prize_amount: Optional[float] = None,
        timestamp: Optional[timezone.datetime] = None
    ) -> Optional[UserActivity]:
        """
        Record TOURNAMENT_PLACED event (includes wins, runner-up, top 3).
        
        Args:
            user_id: User who placed
            tournament_id: Tournament ID
            placement: Final placement (1=winner, 2=runner-up, etc.)
            prize_amount: Prize awarded (if any)
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            UserActivity instance or None if already exists
        """
        # Determine if this is a win
        event_type = EventType.TOURNAMENT_WON if placement == 1 else EventType.TOURNAMENT_PLACED
        
        return cls._record_event(
            event_type=event_type,
            user_id=user_id,
            source_type='tournament',
            source_id=tournament_id,
            event_data={
                'tournament_id': tournament_id,
                'placement': placement,
                'prize_amount': prize_amount,
            },
            timestamp=timestamp
        )
    
    @classmethod
    def record_match_result(
        cls,
        match_id: int,
        winner_id: int,
        loser_id: int,
        winner_score: Optional[int] = None,
        loser_score: Optional[int] = None,
        timestamp: Optional[timezone.datetime] = None
    ) -> tuple[Optional[UserActivity], Optional[UserActivity]]:
        """
        Record MATCH_WON and MATCH_LOST events for both players.
        
        Args:
            match_id: Match ID
            winner_id: Winner user ID
            loser_id: Loser user ID
            winner_score: Winner's score
            loser_score: Loser's score
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            Tuple of (winner_event, loser_event)
        """
        # Record outcome events (MATCH_WON and MATCH_LOST)
        # Note: No longer creating MATCH_PLAYED events due to unique constraint issues
        # stats.matches_played is computed from won + lost counts
        winner_event = cls._record_event(
            event_type=EventType.MATCH_WON,
            user_id=winner_id,
            source_type='match',
            source_id=match_id,
            event_data={
                'match_id': match_id,
                'opponent_id': loser_id,
                'score': winner_score,
                'opponent_score': loser_score,
            },
            timestamp=timestamp
        )
        
        loser_event = cls._record_event(
            event_type=EventType.MATCH_LOST,
            user_id=loser_id,
            source_type='match',
            source_id=match_id,
            event_data={
                'match_id': match_id,
                'opponent_id': winner_id,
                'score': loser_score,
                'opponent_score': winner_score,
            },
            timestamp=timestamp
        )
        
        return winner_event, loser_event
    
    @classmethod
    def record_economy_transaction(
        cls,
        transaction_id: int,
        user_id: int,
        amount: float,
        reason: str,
        timestamp: Optional[timezone.datetime] = None
    ) -> Optional[UserActivity]:
        """
        Record COINS_EARNED or COINS_SPENT event.
        
        Args:
            transaction_id: DeltaCrownTransaction ID
            user_id: User ID
            amount: Transaction amount (positive=earned, negative=spent)
            reason: Transaction reason
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            UserActivity instance or None if already exists
        """
        # Determine event type based on amount sign
        event_type = EventType.COINS_EARNED if amount > 0 else EventType.COINS_SPENT
        
        return cls._record_event(
            event_type=event_type,
            user_id=user_id,
            source_type='economy',
            source_id=transaction_id,
            event_data={
                'transaction_id': transaction_id,
                'amount': abs(amount),  # Store absolute value
                'reason': reason,
            },
            timestamp=timestamp
        )
    
    @classmethod
    def record_achievement_unlocked(
        cls,
        user_id: int,
        achievement_id: int,
        achievement_name: str,
        timestamp: Optional[timezone.datetime] = None
    ) -> Optional[UserActivity]:
        """
        Record ACHIEVEMENT_UNLOCKED event.
        
        Args:
            user_id: User ID
            achievement_id: Achievement ID
            achievement_name: Achievement name
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            UserActivity instance or None if already exists
        """
        return cls._record_event(
            event_type=EventType.ACHIEVEMENT_UNLOCKED,
            user_id=user_id,
            source_type='system',
            source_id=achievement_id,
            event_data={
                'achievement_id': achievement_id,
                'achievement_name': achievement_name,
            },
            timestamp=timestamp
        )
