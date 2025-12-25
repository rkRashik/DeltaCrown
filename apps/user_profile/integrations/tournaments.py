"""
Tournament ↔ User Profile Integration Module

Provides integration points for tournament lifecycle events.
All functions are guarded by USER_PROFILE_INTEGRATION_ENABLED feature flag.

Usage:
    from apps.user_profile.integrations.tournaments import on_match_finalized
    
    # In tournament service after match finalized:
    on_match_finalized(
        match_id=match.id,
        tournament_id=match.tournament_id,
        winner_id=match.winner_id,
        loser_id=loser.id,
        winner_user_ids=[123, 456],
        loser_user_ids=[789],
    )

Design Principles:
- Flag-guarded: All functions short-circuit if USER_PROFILE_INTEGRATION_ENABLED=False
- Idempotent: Safe to call multiple times (uses idempotency keys)
- Non-breaking: Does NOT change tournament business logic
- Lightweight: Defer heavy computation when possible

Reference: Documents/UserProfile_CommandCenter_v1/03_Planning/UP_TOURNAMENT_INTEGRATION_CONTRACT.md
"""

from typing import List, Optional
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import logging
import time

from apps.user_profile.models.activity import UserActivity
from apps.user_profile.services.audit import AuditService
from apps.user_profile.services.tournament_stats import TournamentStatsService

logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    """Check if tournament integration is enabled."""
    return getattr(settings, 'USER_PROFILE_INTEGRATION_ENABLED', False)


def _generate_idempotency_key(event_type: str, primary_key: str, status: str = '') -> str:
    """
    Generate deterministic idempotency key for event deduplication.
    
    CRITICAL: Keys are deterministic (no timestamps) to ensure true idempotency.
    Same event + same data = same key = single record.
    """
    if status:
        return f"{event_type}:{primary_key}:{status}"
    return f"{event_type}:{primary_key}"


def _record_activity(user_id: int, event_type: str, metadata: dict, idempotency_key: str) -> None:
    """
    Record activity event with idempotency check.
    
    Creates UserActivity record directly instead of using UserActivityService
    to support custom event types from tournament integration.
    
    CRITICAL: Runs inside transaction.on_commit to ensure tournament transaction
    commits successfully before side effects execute.
    """
    def _do_record():
        try:
            # Check for existing event with same idempotency key
            existing = UserActivity.objects.filter(
                user_id=user_id,
                event_type=event_type,
                metadata__idempotency_key=idempotency_key
            ).first()
            
            if existing:
                logger.debug(
                    f"Activity event already exists: {event_type} for user {user_id} "
                    f"(idempotency_key={idempotency_key})"
                )
                return
            
            # Create new activity event
            metadata_with_key = {**metadata, 'idempotency_key': idempotency_key}
            UserActivity.objects.create(
                user_id=user_id,
                event_type=event_type,
                source_model='tournament',  # Generic source for tournament events
                source_id=metadata.get('tournament_id', 0),
                metadata=metadata_with_key,
                timestamp=timezone.now()
            )
            
            logger.debug(
                f"Created activity event: {event_type} for user {user_id} "
                f"(idempotency_key={idempotency_key})"
            )
        except Exception as e:
            logger.error(
                f"Failed to record activity: {e}",
                exc_info=True,
                extra={'user_id': user_id, 'event_type': event_type}
            )
            # Don't re-raise - activity recording failures shouldn't break operations
    
    # Execute after tournament transaction commits
    transaction.on_commit(_do_record)


# ============================================================================
# EVENT 1: Registration Status Change
# ============================================================================

def on_registration_status_change(
    user_id: int,
    tournament_id: int,
    registration_id: int,
    status: str,
    team_id: Optional[int] = None,
    actor_user_id: Optional[int] = None,
    reason: Optional[str] = None,
) -> None:
    """
    Record activity/audit for registration status change.
    
    Args:
        user_id: Player who registered
        tournament_id: Tournament ID
        registration_id: Registration ID
        status: 'submitted', 'confirmed', 'approved', 'rejected'
        team_id: Team ID (None for solo)
        actor_user_id: Organizer/admin who approved/rejected
        reason: Rejection reason (if applicable)
        
    Hook Points:
        - RegistrationService.start_registration() → status='submitted'
        - RegistrationService.complete_registration() → status='confirmed'
        - RegistrationService.approve_registration() → status='approved'
        - RegistrationService.reject_registration() → status='rejected'
    """
    if not _is_enabled():
        return
    
    try:
        idempotency_key = _generate_idempotency_key(
            'registration_status', str(registration_id), status
        )
        
        # Record activity event
        _record_activity(
            user_id=user_id,
            event_type=f'tournament.registration.{status}',
            metadata={
                'tournament_id': tournament_id,
                'registration_id': registration_id,
                'team_id': team_id,
                'reason': reason,
            },
            idempotency_key=idempotency_key,
        )
        
        # Record audit event for organizer actions only
        if actor_user_id and status in ['approved', 'rejected']:
            event_type = (
                'registration_approved' if status == 'approved' 
                else 'registration_rejected'
            )
            
            def _record_audit():
                try:
                    AuditService.record_event(
                        subject_user_id=user_id,
                        event_type=event_type,
                        source_app='tournaments',
                        object_type='Registration',
                        object_id=registration_id,
                        actor_user_id=actor_user_id,
                        after_snapshot={'status': status},
                        metadata={
                            'tournament_id': tournament_id,
                            'team_id': team_id,
                            'reason': reason,
                        },
                        idempotency_key=idempotency_key,
                    )
                except Exception as e:
                    logger.error(f"Audit recording failed: {e}", exc_info=True)
            
            transaction.on_commit(_record_audit)
            
        logger.info(
            f"Tournament integration: Registration {registration_id} status={status} "
            f"user={user_id} tournament={tournament_id}"
        )
    except Exception as e:
        logger.error(
            f"Tournament integration error (registration status): {e}",
            exc_info=True,
            extra={
                'user_id': user_id,
                'tournament_id': tournament_id,
                'registration_id': registration_id,
                'status': status,
            }
        )
        # Don't re-raise - integration failures shouldn't break tournament operations


# ============================================================================
# EVENT 2: Check-In Status Change
# ============================================================================

def on_checkin_toggled(
    user_id: int,
    tournament_id: int,
    registration_id: int,
    checked_in: bool,
    actor_user_id: int,
) -> None:
    """
    Record activity/audit for check-in toggle.
    
    Args:
        user_id: Player who checked in/out
        tournament_id: Tournament ID
        registration_id: Registration ID
        checked_in: True if checked in, False if checked out
        actor_user_id: Organizer who toggled check-in
        
    Hook Point:
        - CheckinService.organizer_toggle_checkin()
    """
    if not _is_enabled():
        return
    
    try:
        status = 'checked_in' if checked_in else 'checked_out'
        idempotency_key = _generate_idempotency_key(
            'checkin', str(registration_id), status
        )
        
        # Record activity event
        _record_activity(
            user_id=user_id,
            event_type=f'tournament.checkin.{status}',
            metadata={
                'tournament_id': tournament_id,
                'registration_id': registration_id,
                'checked_in': checked_in,
                'actor_user_id': actor_user_id,
            },
            idempotency_key=idempotency_key,
        )
        
        # Record audit event (deferred until transaction commits)
        def _record_audit():
            try:
                AuditService.record_event(
                    subject_user_id=user_id,
                    event_type='checkin_toggled',
                    source_app='tournaments',
                    object_type='Registration',
                    object_id=registration_id,
                    actor_user_id=actor_user_id,
                    after_snapshot={'checked_in': checked_in},
                    metadata={'tournament_id': tournament_id},
                    idempotency_key=idempotency_key,
                )
            except Exception as e:
                logger.error(f"Audit recording failed: {e}", exc_info=True)
        
        transaction.on_commit(_record_audit)
        
        logger.info(
            f"Tournament integration: Check-in toggled registration={registration_id} "
            f"checked_in={checked_in} user={user_id} tournament={tournament_id}"
        )
    except Exception as e:
        logger.error(
            f"Tournament integration error (check-in): {e}",
            exc_info=True,
            extra={
                'user_id': user_id,
                'tournament_id': tournament_id,
                'registration_id': registration_id,
                'checked_in': checked_in,
            }
        )


# ============================================================================
# EVENT 3: Match Result Submitted
# ============================================================================

def on_match_result_submitted(
    user_id: int,
    match_id: int,
    tournament_id: int,
    submission_id: int,
    status: str,
) -> None:
    """
    Record activity for match result submission.
    
    Args:
        user_id: User who submitted result
        match_id: Match ID
        tournament_id: Tournament ID
        submission_id: Submission ID
        status: 'pending_opponent', 'accepted', 'disputed'
        
    Hook Point:
        - ResultSubmissionService.submit_result()
        - ResultSubmissionService.opponent_response()
    """
    if not _is_enabled():
        return
    
    try:
        idempotency_key = _generate_idempotency_key(
            'match_result_submission', str(submission_id), status
        )
        
        # Record activity event (no audit - automatic action)
        _record_activity(
            user_id=user_id,
            event_type='tournament.match.result_submitted',
            metadata={
                'match_id': match_id,
                'tournament_id': tournament_id,
                'submission_id': submission_id,
                'status': status,
            },
            idempotency_key=idempotency_key,
        )
        
        logger.info(
            f"Tournament integration: Match result submitted submission={submission_id} "
            f"status={status} user={user_id} match={match_id}"
        )
    except Exception as e:
        logger.error(
            f"Tournament integration error (match result): {e}",
            exc_info=True,
            extra={
                'user_id': user_id,
                'match_id': match_id,
                'submission_id': submission_id,
            }
        )


# ============================================================================
# EVENT 4: Match Finalized (Result Verified)
# ============================================================================

def on_match_finalized(
    match_id: int,
    tournament_id: int,
    winner_id: int,
    loser_id: int,
    winner_user_ids: List[int],
    loser_user_ids: List[int],
) -> None:
    """
    Record activity and trigger stats recompute for match finalization.
    
    This is a critical integration point - when match results are verified,
    we need to update matches_played and matches_won stats for all participants.
    
    Args:
        match_id: Match ID
        tournament_id: Tournament ID
        winner_id: Winning team/player ID
        loser_id: Losing team/player ID
        winner_user_ids: All user IDs in winning team/player
        loser_user_ids: All user IDs in losing team/player
        
    Hook Point:
        - ResultVerificationService.verify_submission() (after Match.winner_id updated)
    """
    if not _is_enabled():
        return
    
    try:
        idempotency_key = _generate_idempotency_key('match_finalized', str(match_id))
        
        # Record activity event for ALL participants
        all_user_ids = winner_user_ids + loser_user_ids
        for user_id in all_user_ids:
            _record_activity(
                user_id=user_id,
                event_type='tournament.match.finalized',
                metadata={
                    'match_id': match_id,
                    'tournament_id': tournament_id,
                    'winner_id': winner_id,
                    'loser_id': loser_id,
                    'is_winner': user_id in winner_user_ids,
                },
                idempotency_key=f"{idempotency_key}:user_{user_id}",
            )
        
        # Trigger stats recompute (deferred until transaction commits)
        def _recompute_stats():
            for user_id in all_user_ids:
                try:
                    TournamentStatsService.recompute_user_stats(user_id)
                except Exception as stats_error:
                    logger.error(
                        f"Stats recompute failed for user {user_id}: {stats_error}",
                        exc_info=True
                    )
        
        transaction.on_commit(_recompute_stats)
        
        logger.info(
            f"Tournament integration: Match finalized match={match_id} "
            f"winner={winner_id} loser={loser_id} participants={len(all_user_ids)}"
        )
    except Exception as e:
        logger.error(
            f"Tournament integration error (match finalized): {e}",
            exc_info=True,
            extra={
                'match_id': match_id,
                'tournament_id': tournament_id,
                'winner_id': winner_id,
                'loser_id': loser_id,
            }
        )


# ============================================================================
# EVENT 5: Tournament Completed
# ============================================================================

def on_tournament_completed(
    tournament_id: int,
    actor_user_id: int,
    participant_user_ids: List[int],
    winner_user_ids: List[int],
    top3_user_ids: List[int],
) -> None:
    """
    Record activity/audit and trigger stats recompute for tournament completion.
    
    This triggers a bulk stats recompute for all participants to update:
    - tournaments_played
    - tournaments_won
    - tournaments_top3
    
    Args:
        tournament_id: Tournament ID
        actor_user_id: Organizer who completed tournament
        participant_user_ids: All users who participated
        winner_user_ids: All users in winning team/player
        top3_user_ids: All users in top 3 placements
        
    Hook Point:
        - TournamentService.complete_tournament()
    """
    if not _is_enabled():
        return
    
    try:
        idempotency_key = _generate_idempotency_key('tournament_completed', str(tournament_id))
        
        # Record activity event for ALL participants
        for user_id in participant_user_ids:
            _record_activity(
                user_id=user_id,
                event_type='tournament.completed',
                metadata={
                    'tournament_id': tournament_id,
                    'is_winner': user_id in winner_user_ids,
                    'is_top3': user_id in top3_user_ids,
                },
                idempotency_key=f"{idempotency_key}:user_{user_id}",
            )
        
        # Record audit event (deferred until transaction commits)
        def _record_audit():
            try:
                AuditService.record_event(
                    subject_user_id=actor_user_id,  # Organizer as subject
                    event_type='tournament_completed',
                    source_app='tournaments',
                    object_type='Tournament',
                    object_id=tournament_id,
                    actor_user_id=actor_user_id,
                    metadata={
                        'participant_count': len(participant_user_ids),
                        'winner_count': len(winner_user_ids),
                        'top3_count': len(top3_user_ids),
                    },
                    idempotency_key=idempotency_key,
                )
            except Exception as e:
                logger.error(f"Audit recording failed: {e}", exc_info=True)
        
        transaction.on_commit(_record_audit)
        
        # Trigger stats recompute for ALL participants
        # This recalculates tournaments_played, tournaments_won, tournaments_top3
        def _recompute_stats():
            for user_id in participant_user_ids:
                try:
                    TournamentStatsService.recompute_user_stats(user_id)
                except Exception as stats_error:
                    logger.error(
                        f"Stats recompute failed for user {user_id}: {stats_error}",
                        exc_info=True
                    )
        
        transaction.on_commit(_recompute_stats)
        
        logger.info(
            f"Tournament integration: Tournament completed tournament={tournament_id} "
            f"participants={len(participant_user_ids)} winners={len(winner_user_ids)}"
        )
    except Exception as e:
        logger.error(
            f"Tournament integration error (tournament completed): {e}",
            exc_info=True,
            extra={
                'tournament_id': tournament_id,
                'actor_user_id': actor_user_id,
            }
        )


# ============================================================================
# EVENT 6: Dispute Opened
# ============================================================================

def on_dispute_opened(
    user_id: int,
    match_id: int,
    tournament_id: int,
    dispute_id: int,
    submission_id: int,
    reason_code: str,
) -> None:
    """
    Record activity for dispute opened.
    
    Args:
        user_id: User who opened dispute
        match_id: Match ID
        tournament_id: Tournament ID
        dispute_id: Dispute ID
        submission_id: Submission ID
        reason_code: Dispute reason code
        
    Hook Point:
        - ResultSubmissionService.opponent_response() (when dispute=True)
    """
    if not _is_enabled():
        return
    
    try:
        idempotency_key = _generate_idempotency_key('dispute_opened', str(dispute_id))
        
        # Record activity event (no audit - automatic action)
        _record_activity(
            user_id=user_id,
            event_type='tournament.dispute.opened',
            metadata={
                'match_id': match_id,
                'tournament_id': tournament_id,
                'dispute_id': dispute_id,
                'submission_id': submission_id,
                'reason_code': reason_code,
            },
            idempotency_key=idempotency_key,
        )
        
        logger.info(
            f"Tournament integration: Dispute opened dispute={dispute_id} "
            f"user={user_id} match={match_id} reason={reason_code}"
        )
    except Exception as e:
        logger.error(
            f"Tournament integration error (dispute opened): {e}",
            exc_info=True,
            extra={
                'user_id': user_id,
                'dispute_id': dispute_id,
                'match_id': match_id,
            }
        )


# ============================================================================
# EVENT 7: Dispute Resolved
# ============================================================================

def on_dispute_resolved(
    match_id: int,
    tournament_id: int,
    dispute_id: int,
    resolution_type: str,
    actor_user_id: int,
    winner_user_ids: Optional[List[int]] = None,
    loser_user_ids: Optional[List[int]] = None,
) -> None:
    """
    Record activity/audit and conditionally trigger stats recompute for dispute resolution.
    
    If resolution finalizes match result (approve_original, approve_dispute, custom_result),
    trigger stats recompute same as on_match_finalized().
    
    Args:
        match_id: Match ID
        tournament_id: Tournament ID
        dispute_id: Dispute ID
        resolution_type: 'approve_original', 'approve_dispute', 'custom_result', 'dismiss_dispute'
        actor_user_id: Organizer who resolved dispute
        winner_user_ids: User IDs if result finalized
        loser_user_ids: User IDs if result finalized
        
    Hook Point:
        - DisputeService.resolve_dispute()
    """
    if not _is_enabled():
        return
    
    try:
        idempotency_key = _generate_idempotency_key('dispute_resolved', str(dispute_id))
        
        # Record activity event
        _record_activity(
            user_id=actor_user_id,
            event_type='tournament.dispute.resolved',
            metadata={
                'dispute_id': dispute_id,
                'match_id': match_id,
                'tournament_id': tournament_id,
                'resolution_type': resolution_type,
            },
            idempotency_key=idempotency_key,
        )
        
        # Record audit event (deferred until transaction commits)
        def _record_audit():
            try:
                AuditService.record_event(
                    subject_user_id=actor_user_id,  # Organizer as subject
                    event_type='dispute_resolved',
                    source_app='tournaments',
                    object_type='Dispute',
                    object_id=dispute_id,
                    actor_user_id=actor_user_id,
                    after_snapshot={'resolution_type': resolution_type},
                    metadata={
                        'match_id': match_id,
                        'tournament_id': tournament_id,
                    },
                    idempotency_key=idempotency_key,
                )
            except Exception as e:
                logger.error(f"Audit recording failed: {e}", exc_info=True)
        
        transaction.on_commit(_record_audit)
        
        # If resolution finalizes match result, trigger stats recompute
        if resolution_type in ['approve_original', 'approve_dispute', 'custom_result']:
            if winner_user_ids and loser_user_ids:
                def _recompute_stats():
                    all_user_ids = winner_user_ids + loser_user_ids
                    for user_id in all_user_ids:
                        try:
                            TournamentStatsService.recompute_user_stats(user_id)
                        except Exception as stats_error:
                            logger.error(
                                f"Stats recompute failed for user {user_id}: {stats_error}",
                                exc_info=True
                            )
                
                transaction.on_commit(_recompute_stats)
        
        logger.info(
            f"Tournament integration: Dispute resolved dispute={dispute_id} "
            f"resolution={resolution_type} actor={actor_user_id}"
        )
    except Exception as e:
        logger.error(
            f"Tournament integration error (dispute resolved): {e}",
            exc_info=True,
            extra={
                'dispute_id': dispute_id,
                'resolution_type': resolution_type,
                'actor_user_id': actor_user_id,
            }
        )


# ============================================================================
# EVENT 8: Payment Status Change
# ============================================================================

def on_payment_status_change(
    user_id: int,
    tournament_id: int,
    transaction_id: str,
    registration_id: int,
    status: str,
    actor_user_id: int,
    amount: Decimal,
    reason: Optional[str] = None,
) -> None:
    """
    Record activity/audit for payment status change.
    
    Args:
        user_id: User whose payment changed
        tournament_id: Tournament ID
        transaction_id: Transaction ID
        registration_id: Registration ID
        status: 'verified', 'rejected', 'refunded'
        actor_user_id: Organizer who verified/rejected/refunded
        amount: Payment amount
        reason: Rejection/refund reason
        
    Hook Point:
        - PaymentService.verify_payment()
        - PaymentService.reject_payment()
        - PaymentService.refund_payment()
    """
    if not _is_enabled():
        return
    
    try:
        event_type = f'payment_{status}'
        idempotency_key = _generate_idempotency_key(
            'payment', transaction_id, status
        )
        
        # Record activity event
        _record_activity(
            user_id=user_id,
            event_type=f'tournament.payment.{status}',
            metadata={
                'tournament_id': tournament_id,
                'transaction_id': transaction_id,
                'registration_id': registration_id,
                'amount': str(amount),
                'reason': reason,
                'actor_user_id': actor_user_id,
            },
            idempotency_key=idempotency_key,
        )
        
        # Record audit event (deferred until transaction commits)
        def _record_audit():
            try:
                AuditService.record_event(
                    subject_user_id=user_id,
                    event_type=event_type,
                    source_app='tournaments',
                    object_type='Payment',
                    object_id=transaction_id,
                    actor_user_id=actor_user_id,
                    after_snapshot={
                        'status': status,
                        'amount': str(amount),
                    },
                    metadata={
                        'tournament_id': tournament_id,
                        'registration_id': registration_id,
                        'reason': reason,
                    },
                    idempotency_key=idempotency_key,
                )
            except Exception as e:
                logger.error(f"Audit recording failed: {e}", exc_info=True)
        
        transaction.on_commit(_record_audit)
        
        logger.info(
            f"Tournament integration: Payment {status} transaction={transaction_id} "
            f"user={user_id} tournament={tournament_id} amount={amount}"
        )
    except Exception as e:
        logger.error(
            f"Tournament integration error (payment): {e}",
            exc_info=True,
            extra={
                'user_id': user_id,
                'transaction_id': transaction_id,
                'status': status,
            }
        )
