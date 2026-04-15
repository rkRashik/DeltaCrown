"""
MatchService - Business logic for match lifecycle management (Module 1.4)

Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 6: MatchService)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 6: Match Lifecycle Models)
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Match UI flows)
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md (ADR-001, ADR-003, ADR-007)

Architecture Decisions:
- ADR-001: Service layer pattern - All business logic in services
- ADR-003: Soft delete support for Match model
- ADR-007: WebSocket integration for real-time updates (Module 2.2 - Phase 2)

State Machine (Match):
SCHEDULED → CHECK_IN → READY → LIVE → PENDING_RESULT → COMPLETED
                 │                          │
                 │                          └──> DISPUTED
                 │
                 └──> FORFEIT (if check-in failed)

Service Responsibilities:
- Match creation and participant pairing
- State transitions and validation
- Result submission and confirmation
- Dispute creation and resolution
- Check-in management
- WebSocket notifications (real-time updates) - Module 2.3 Integration
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet

from apps.tournaments.models import (
    Tournament,
    Match,
    Bracket,
    Registration
)
from apps.tournaments.models.dispute import DisputeRecord
from apps.tournaments.state_machine import validate_transition

# User Profile Integration
from apps.user_profile.integrations.tournaments import (
    on_match_result_submitted,
    on_match_finalized,
    on_dispute_opened,
    on_dispute_resolved,
)

# Module 2.3: Real-time WebSocket broadcasting
from apps.tournaments.realtime.utils import (
    broadcast_match_started,
    broadcast_score_updated,
    broadcast_match_completed,
)
from asgiref.sync import async_to_sync  # Module 6.1: Wrap async broadcast helpers

# Module 2.x: In-app notification dispatch
from apps.notifications.services import notify as _notify_users

logger = logging.getLogger(__name__)


def _publish_match_event(event_name: str, **kwargs):
    """Publish match lifecycle events via the core EventBus (fire-and-forget)."""
    try:
        from apps.tournament_ops.events.publishers import (
            publish_match_scheduled,
            publish_match_completed,
            publish_match_result_verified,
        )
        if event_name == "match.scheduled":
            publish_match_scheduled(**kwargs)
        elif event_name == "match.completed":
            publish_match_completed(**kwargs)
        elif event_name == "match.result_verified":
            publish_match_result_verified(**kwargs)
        else:
            from apps.core.events import event_bus
            from apps.core.events.bus import Event
            event_bus.publish(Event(event_type=event_name, data=kwargs, source="match_service"))
    except Exception as exc:
        logger.warning("Failed to publish %s event: %s", event_name, exc)


class MatchService:
    """
    Service for match lifecycle management.
    
    Methods:
    - create_match(): Generate match with participant pairing
    - check_in_participant(): Handle participant check-in
    - transition_to_live(): Start match
    - submit_result(): Accept result submission
    - confirm_result(): Finalize match result
    - report_dispute(): Create dispute record
    - resolve_dispute(): Resolve or escalate dispute
    - cancel_match(): Cancel match (organizer action)
    - forfeit_match(): Forfeit due to no-show
    - get_match_stats(): Calculate match statistics
    
    Integration Points:
    - BracketService: Winner progression (Module 1.5)
    - NotificationService: Real-time updates (Module 2.x)
    - AnalyticsService: Match history tracking (Module 2.x)
    """
    
    # =========================
    # Match Creation & Setup
    # =========================
    
    @staticmethod
    @transaction.atomic
    def create_match(
        tournament: Tournament,
        bracket: Optional[Bracket],
        round_number: int,
        match_number: int,
        participant1_id: Optional[int] = None,
        participant1_name: str = "",
        participant2_id: Optional[int] = None,
        participant2_name: str = "",
        scheduled_time: Optional[datetime] = None,
        **kwargs
    ) -> Match:
        """
        Create a match with participant pairing.
        
        Args:
            tournament: Tournament instance
            bracket: Bracket instance (null for group stage)
            round_number: Round number (1-indexed)
            match_number: Match number within round
            participant1_id: Team ID or User ID for participant 1
            participant1_name: Display name for participant 1
            participant2_id: Team ID or User ID for participant 2
            participant2_name: Display name for participant 2
            scheduled_time: When match is scheduled
            **kwargs: Additional match fields (lobby_info, stream_url, etc.)
            
        Returns:
            Created Match instance
            
        Raises:
            ValidationError: If validation fails
            
        Example:
            match = MatchService.create_match(
                tournament=tournament,
                bracket=bracket,
                round_number=1,
                match_number=1,
                participant1_id=101,
                participant1_name="Team Alpha",
                participant2_id=102,
                participant2_name="Team Beta",
                scheduled_time=timezone.now() + timedelta(hours=2)
            )
        """
        # Validation
        if round_number < 1:
            raise ValidationError("Round number must be at least 1")
        
        if match_number < 1:
            raise ValidationError("Match number must be at least 1")
        
        # Check for duplicate match
        existing = Match.objects.filter(
            tournament=tournament,
            bracket=bracket,
            round_number=round_number,
            match_number=match_number,
            is_deleted=False
        ).exists()
        
        if existing:
            raise ValidationError(
                f"Match already exists: Round {round_number}, Match {match_number}"
            )
        
        # Determine initial state
        if tournament.enable_check_in and scheduled_time:
            initial_state = Match.SCHEDULED
        else:
            initial_state = Match.READY
        
        # Calculate check-in deadline if applicable
        check_in_deadline = None
        if tournament.enable_check_in and scheduled_time:
            # Default: 30 minutes before scheduled time
            check_in_minutes = tournament.check_in_window_minutes if hasattr(tournament, 'check_in_window_minutes') else 30
            check_in_deadline = scheduled_time - timedelta(minutes=check_in_minutes)
        
        # Create match
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=round_number,
            match_number=match_number,
            participant1_id=participant1_id,
            participant1_name=participant1_name,
            participant2_id=participant2_id,
            participant2_name=participant2_name,
            state=initial_state,
            scheduled_time=scheduled_time,
            check_in_deadline=check_in_deadline,
            **kwargs
        )
        
        # Publish match.scheduled event
        _match_id = match.id
        _tourney_id = tournament.id
        def _emit_scheduled():
            _publish_match_event(
                "match.scheduled",
                match_id=_match_id,
                tournament_id=_tourney_id,
                source="match_service",
            )
        transaction.on_commit(_emit_scheduled)
        
        return match
    
    # =========================
    # Check-in Management
    # =========================
    
    @staticmethod
    @transaction.atomic
    def check_in_participant(
        match: Match,
        participant_id: int
    ) -> Match:
        """
        Handle participant check-in.
        
        Args:
            match: Match instance
            participant_id: Team ID or User ID checking in
            
        Returns:
            Updated Match instance
            
        Raises:
            ValidationError: If check-in not allowed
            
        Example:
            match = MatchService.check_in_participant(match, participant_id=101)
        """
        # Validation
        if match.state not in [Match.SCHEDULED, Match.CHECK_IN]:
            raise ValidationError(f"Check-in not allowed in state: {match.state}")
        
        if match.check_in_deadline and timezone.now() > match.check_in_deadline:
            # Too late - forfeit
            return MatchService.forfeit_match(
                match=match,
                reason=f"Participant {participant_id} missed check-in deadline"
            )
        
        # Update check-in status
        if participant_id == match.participant1_id:
            match.participant1_checked_in = True
        elif participant_id == match.participant2_id:
            match.participant2_checked_in = True
        else:
            raise ValidationError(f"Participant {participant_id} is not in this match")
        
        # Update state if both checked in
        if match.is_both_checked_in:
            validate_transition(match, Match.READY)
            match.state = Match.READY
        else:
            validate_transition(match, Match.CHECK_IN)
            match.state = Match.CHECK_IN
        
        match.save()
        
        # Notify opponent that this participant has checked in (Module 2.x)
        try:
            from django.contrib.auth import get_user_model
            _User = get_user_model()
            _opponent_id = (
                match.participant2_id
                if participant_id == match.participant1_id
                else match.participant1_id
            )
            _opponent = _User.objects.filter(id=_opponent_id).first()
            if _opponent:
                _notify_users(
                    [_opponent],
                    event='match_checkin',
                    title=f"{match.participant1_name} vs {match.participant2_name} — opponent checked in",
                    body="Your opponent has checked in. Please check in to begin the match.",
                    tournament_id=match.tournament_id,
                    match_id=match.id,
                )
        except Exception as _exc:
            logger.warning(f"check_in notification failed for match {match.id}: {_exc}")
        
        # Broadcast check-in update to tournament room (ADR-007)
        try:
            from apps.tournaments.realtime.broadcast import broadcast_event
            broadcast_event(
                tournament_id=match.tournament_id,
                event_type='checkin_updated',
                data={
                    'match_id': match.id,
                    'participant_id': participant_id,
                    'participant1_checked_in': match.participant1_checked_in,
                    'participant2_checked_in': match.participant2_checked_in,
                    'match_state': match.state,
                },
            )
        except Exception as _exc:
            logger.warning(f"checkin_updated broadcast failed for match {match.id}: {_exc}")
        
        return match
    
    # =========================
    # State Transitions
    # =========================
    
    @staticmethod
    @transaction.atomic
    def transition_to_live(match: Match) -> Match:
        """
        Transition match to LIVE state (match started).
        
        Args:
            match: Match instance
            
        Returns:
            Updated Match instance
            
        Raises:
            ValidationError: If transition not allowed
            
        Side Effects:
            - Broadcasts match_started event via WebSocket (Module 2.3)
        """
        if match.state != Match.READY:
            raise ValidationError(f"Cannot start match from state: {match.state}")
        
        if not match.is_ready_to_start:
            raise ValidationError("Match not ready to start (check-in incomplete)")
        
        validate_transition(match, Match.LIVE)
        match.state = Match.LIVE
        match.started_at = timezone.now()
        match.save()
        
        # Module 2.3: Broadcast match_started event to WebSocket clients
        # Module 6.1: Wrap async broadcast with async_to_sync
        try:
            async_to_sync(broadcast_match_started)(
                tournament_id=match.tournament_id,
                match_data={
                    'match_id': match.id,
                    'tournament_id': match.tournament_id,
                    'status': match.state,
                    'participant1_id': match.participant1_id,
                    'participant1_name': match.participant1_name,
                    'participant2_id': match.participant2_id,
                    'participant2_name': match.participant2_name,
                    'round': match.round_number,
                    'match_number': match.match_number,
                    'started_at': match.started_at.isoformat() if match.started_at else None,
                }
            )
        except Exception as e:
            # Log error but don't fail transaction - broadcasting is non-critical
            logger.warning(
                f"Failed to broadcast match_started for match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'tournament_id': match.tournament_id}
            )
        
        # Publish match.live event
        _m_id = match.id
        _t_id = match.tournament_id
        def _emit_live():
            _publish_match_event("match.live", match_id=_m_id, tournament_id=_t_id, source="match_service")
        transaction.on_commit(_emit_live)
        
        return match
    
    # =========================
    # Result Submission
    # =========================
    
    @staticmethod
    @transaction.atomic
    def submit_result(
        match: Match,
        submitted_by_id: int,
        participant1_score: int,
        participant2_score: int,
        game_scores: list = None,
        notes: str = "",
        evidence_url: str = ""
    ) -> Match:
        """
        Submit match result.
        
        Args:
            match: Match instance
            submitted_by_id: User ID submitting result
            participant1_score: Score for participant 1
            participant2_score: Score for participant 2
            game_scores: Optional per-map/game scores list
            notes: Optional notes about result
            evidence_url: Optional evidence URL
            
        Returns:
            Updated Match instance
            
        Raises:
            ValidationError: If submission not allowed
            
        Example:
            match = MatchService.submit_result(
                match=match,
                submitted_by_id=101,
                participant1_score=13,
                participant2_score=11
            )
        """
        # Re-fetch with row-level lock to prevent concurrent submissions
        match = Match.objects.select_for_update().get(id=match.id)

        # Validation
        if match.state not in [Match.LIVE, Match.PENDING_RESULT]:
            raise ValidationError(f"Cannot submit result in state: {match.state}")
        
        if participant1_score < 0 or participant2_score < 0:
            raise ValidationError("Scores cannot be negative")
        
        if participant1_score == participant2_score:
            raise ValidationError("Match cannot end in a tie (implement tiebreaker logic)")
        
        # Validate game_scores count against best_of
        if game_scores and len(game_scores) > match.best_of:
            raise ValidationError(
                f"Number of maps ({len(game_scores)}) exceeds best_of ({match.best_of})"
            )
        
        # Verify submitter is a participant
        if submitted_by_id not in [match.participant1_id, match.participant2_id]:
            raise ValidationError("Only participants can submit results")
        
        # Update match with submitted result
        match.participant1_score = participant1_score
        match.participant2_score = participant2_score
        validate_transition(match, Match.PENDING_RESULT)
        match.state = Match.PENDING_RESULT
        
        # Save per-map scores if provided
        if game_scores is not None:
            match.game_scores = game_scores
        
        # Determine winner
        if participant1_score > participant2_score:
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
        else:
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id
        
        match.save()
        
        # User Profile Integration Hook - Match Result Submitted
        def _notify_profile():
            try:
                on_match_result_submitted(
                    user_id=submitted_by_id,
                    match_id=match.id,
                    tournament_id=match.tournament_id,
                    submission_id=match.id,  # Use match.id as submission identifier
                    status='pending_opponent',
                )
            except Exception:
                pass  # Non-blocking
        transaction.on_commit(_notify_profile)
        
        # Module 2.3: Broadcast score_updated event to WebSocket clients
        # Module 6.1: Wrap async broadcast with async_to_sync
        try:
            async_to_sync(broadcast_score_updated)(
                tournament_id=match.tournament_id,
                score_data={
                    'match_id': match.id,
                    'tournament_id': match.tournament_id,
                    'status': match.state,
                    'participant1_score': participant1_score,
                    'participant2_score': participant2_score,
                    'winner_id': match.winner_id,
                    'submitted_by': submitted_by_id,
                    'updated_at': timezone.now().isoformat(),
                }
            )
        except Exception as e:
            # Log error but don't fail transaction - broadcasting is non-critical
            logger.warning(
                f"Failed to broadcast score_updated for match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'tournament_id': match.tournament_id}
            )
        
        # Notify opponent to confirm the submitted result (Module 2.x)
        try:
            from django.contrib.auth import get_user_model
            _User = get_user_model()
            _opponent_id = (
                match.participant2_id
                if submitted_by_id == match.participant1_id
                else match.participant1_id
            )
            _opponent = _User.objects.filter(id=_opponent_id).first()
            if _opponent:
                _notify_users(
                    [_opponent],
                    event='match_result_pending',
                    title=f"{match.participant1_name} vs {match.participant2_name} — confirm result",
                    body="Your opponent has submitted a match result. Please review and confirm.",
                    tournament_id=match.tournament_id,
                    match_id=match.id,
                )
        except Exception as _exc:
            logger.warning(f"result_pending notification failed for match {match.id}: {_exc}")
        
        return match
    
    @staticmethod
    @transaction.atomic
    def confirm_result(
        match: Match,
        confirmed_by_id: int
    ) -> Match:
        """
        Confirm match result and finalize match.
        
        Args:
            match: Match instance
            confirmed_by_id: User ID confirming result (opponent or organizer)
            
        Returns:
            Updated Match instance
            
        Raises:
            ValidationError: If confirmation not allowed
            
        Side Effects:
            - Broadcasts match_completed event via WebSocket (Module 2.3)
            - Triggers bracket update which broadcasts bracket_updated (Module 2.3)
            
        Example:
            match = MatchService.confirm_result(match, confirmed_by_id=102)
        """
        # Re-fetch with row-level lock to prevent concurrent confirmations
        match = Match.objects.select_for_update().get(id=match.id)

        # Validation
        if match.state != Match.PENDING_RESULT:
            raise ValidationError(f"Cannot confirm result in state: {match.state}")
        
        if not match.has_result:
            raise ValidationError("No result to confirm (winner not set)")
        
        # Finalize match
        validate_transition(match, Match.COMPLETED)
        match.state = Match.COMPLETED
        match.completed_at = timezone.now()
        match.save()
        
        # Module 2.3: Broadcast match_completed event to WebSocket clients
        # Module 6.1: Wrap async broadcast with async_to_sync
        try:
            async_to_sync(broadcast_match_completed)(
                tournament_id=match.tournament_id,
                result_data={
                    'match_id': match.id,
                    'tournament_id': match.tournament_id,
                    'status': match.state,
                    'winner_id': match.winner_id,
                    'winner_name': (match.participant1_name if match.winner_id == match.participant1_id 
                                  else match.participant2_name),
                    'loser_id': match.loser_id,
                    'loser_name': (match.participant2_name if match.loser_id == match.participant2_id 
                                 else match.participant1_name),
                    'participant1_score': match.participant1_score,
                    'participant2_score': match.participant2_score,
                    'confirmed_by': confirmed_by_id,
                    'completed_at': match.completed_at.isoformat() if match.completed_at else None,
                }
            )
        except Exception as e:
            # Log error but don't fail transaction - broadcasting is non-critical
            logger.warning(
                f"Failed to broadcast match_completed for match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'tournament_id': match.tournament_id}
            )
        
        # Update bracket progression (Module 1.5 - BracketService Integration)
        # This will trigger bracket_updated broadcast (Module 2.3)
        try:
            from apps.tournaments.services.bracket_service import BracketService
            BracketService.update_bracket_after_match(match)
        except Exception as e:
            # Log error but don't fail match confirmation
            # (Bracket update is a secondary concern)
            logger.error(
                f"Failed to update bracket after match {match.id}: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'tournament_id': match.tournament_id}
            )

        # Double Elimination: check if Grand Finals Reset is needed
        try:
            MatchService.check_and_activate_gf_reset(match)
        except Exception as e:
            logger.warning(f"GF reset check failed for match {match.id}: {e}")
        
        # Publish match.completed event
        _m_id = match.id
        _t_id = match.tournament_id
        _w_id = match.winner_id
        def _emit_completed():
            _publish_match_event(
                "match.completed",
                match_id=_m_id,
                tournament_id=_t_id,
                winner_id=_w_id,
                source="match_service",
            )
        transaction.on_commit(_emit_completed)
        
        return match
    
    # =========================
    # Dispute Management
    # =========================
    
    @staticmethod
    @transaction.atomic
    def report_dispute(
        match: Match,
        initiated_by_id: int,
        reason: str,
        description: str,
        evidence_screenshot=None,
        evidence_video_url: str = ""
    ) -> DisputeRecord:
        """
        Create dispute for match result (DisputeRecord via MatchResultSubmission).

        Args:
            match: Match instance
            initiated_by_id: User ID initiating dispute
            reason: Dispute reason code (use DisputeRecord.REASON_CHOICES)
            description: Detailed description
            evidence_screenshot: Ignored (use DisputeEvidence after creation)
            evidence_video_url: Ignored (use DisputeEvidence after creation)

        Returns:
            Created DisputeRecord instance

        Raises:
            ValidationError: If dispute not allowed
        """
        from apps.tournaments.models.result_submission import MatchResultSubmission

        # Validation
        if match.state not in [Match.PENDING_RESULT, Match.COMPLETED]:
            raise ValidationError(f"Cannot dispute match in state: {match.state}")

        # Verify initiator is a participant
        if initiated_by_id not in [match.participant1_id, match.participant2_id]:
            raise ValidationError("Only participants can initiate disputes")

        # Find the latest result submission for this match
        submission = (
            MatchResultSubmission.objects.filter(match=match)
            .order_by('-submitted_at')
            .first()
        )
        if not submission:
            raise ValidationError("No result submission found to dispute")

        # Check if active dispute already exists
        existing_dispute = DisputeRecord.objects.filter(
            submission__match=match,
            status__in=[DisputeRecord.OPEN, DisputeRecord.UNDER_REVIEW, DisputeRecord.ESCALATED]
        ).first()

        if existing_dispute:
            raise ValidationError("An active dispute already exists for this match")

        # Create dispute record
        dispute = DisputeRecord.objects.create(
            submission=submission,
            opened_by_user_id=initiated_by_id,
            reason_code=reason,
            description=description,
            status=DisputeRecord.OPEN,
        )

        # Update match state
        validate_transition(match, Match.DISPUTED)
        match.state = Match.DISPUTED
        match.save()

        # User Profile Integration Hook - Dispute Opened
        def _notify_profile():
            try:
                on_dispute_opened(
                    user_id=initiated_by_id,
                    match_id=match.id,
                    tournament_id=match.tournament_id,
                    dispute_id=dispute.id,
                    submission_id=submission.id,
                    reason_code=reason,
                )
            except Exception:
                pass  # Non-blocking
        transaction.on_commit(_notify_profile)

        # WebSocket broadcast - dispute_created event
        from apps.tournaments.realtime.utils import broadcast_tournament_event

        dispute_data = {
            'match_id': match.id,
            'tournament_id': match.tournament_id,
            'dispute_id': dispute.id,
            'initiated_by': initiated_by_id,
            'reason': reason,
            'status': dispute.status,
            'timestamp': dispute.opened_at.isoformat(),
        }

        broadcast_tournament_event(
            tournament_id=match.tournament_id,
            event_type='dispute_created',
            data=dispute_data,
        )

        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                async_to_sync(channel_layer.group_send)(
                    f'match_{match.id}',
                    {'type': 'dispute_created', 'data': dispute_data},
                )
            except Exception as e:
                logger.error(f"Failed to broadcast dispute_created to match room: {e}")

        # Notify tournament organizer
        try:
            from django.contrib.auth import get_user_model
            from apps.tournaments.models import Tournament as _Tournament
            _User = get_user_model()
            _tournament = _Tournament.objects.filter(id=match.tournament_id).first()
            if _tournament and _tournament.organizer_id:
                _organizer = _User.objects.filter(id=_tournament.organizer_id).first()
                if _organizer:
                    _notify_users(
                        [_organizer],
                        event='dispute_filed',
                        title=f"New dispute filed — {match.participant1_name} vs {match.participant2_name}",
                        body=f"A dispute has been filed: {reason}",
                        tournament_id=match.tournament_id,
                        match_id=match.id,
                    )
        except Exception as _exc:
            logger.warning(f"dispute organizer notification failed for match {match.id}: {_exc}")

        return dispute
    
    @staticmethod
    @transaction.atomic
    def resolve_dispute(
        dispute: DisputeRecord,
        resolved_by_id: int,
        resolution_notes: str,
        final_participant1_score: int,
        final_participant2_score: int,
        status: str = None
    ) -> Tuple[DisputeRecord, Match]:
        """
        Resolve dispute with final decision.

        Args:
            dispute: DisputeRecord instance
            resolved_by_id: User ID resolving (organizer or admin)
            resolution_notes: Notes explaining resolution
            final_participant1_score: Final score for participant 1
            final_participant2_score: Final score for participant 2
            status: Optional status (defaults to RESOLVED_CUSTOM, can be ESCALATED)

        Returns:
            Tuple of (Updated DisputeRecord, Updated Match)
        """
        if dispute.status not in [DisputeRecord.OPEN, DisputeRecord.UNDER_REVIEW, DisputeRecord.ESCALATED]:
            raise ValidationError(f"Cannot resolve dispute with status: {dispute.status}")

        if final_participant1_score < 0 or final_participant2_score < 0:
            raise ValidationError("Scores cannot be negative")

        original_status = dispute.status
        match = dispute.submission.match

        # Update dispute
        dispute.status = status or DisputeRecord.RESOLVED_CUSTOM
        dispute.resolved_by_user_id = resolved_by_id
        dispute.resolved_at = timezone.now()
        dispute.resolution_notes = resolution_notes
        dispute.save()

        # User Profile Integration Hook - Dispute Resolved
        def _notify_profile_dispute():
            try:
                winner_user_ids = None
                loser_user_ids = None
                if status != DisputeRecord.ESCALATED:
                    pass  # Set after match.save()
                on_dispute_resolved(
                    match_id=match.id,
                    tournament_id=match.tournament_id,
                    dispute_id=dispute.id,
                    resolution_type=status or 'resolved',
                    actor_user_id=resolved_by_id,
                    winner_user_ids=winner_user_ids,
                    loser_user_ids=loser_user_ids,
                )
            except Exception:
                pass
        transaction.on_commit(_notify_profile_dispute)

        # Audit Logging
        from apps.tournaments.security.audit import audit_event, AuditAction
        from django.contrib.auth import get_user_model

        User = get_user_model()
        resolved_by = User.objects.filter(id=resolved_by_id).first()

        if status == DisputeRecord.ESCALATED:
            audit_action = AuditAction.DISPUTE_ESCALATE
        else:
            audit_action = AuditAction.DISPUTE_RESOLVE

        audit_event(
            user=resolved_by,
            action=audit_action,
            meta={
                'dispute_id': dispute.id,
                'match_id': match.id,
                'tournament_id': match.tournament_id,
                'original_status': original_status,
                'new_status': dispute.status,
                'final_participant1_score': final_participant1_score,
                'final_participant2_score': final_participant2_score,
                'resolution_notes': resolution_notes[:200],
            }
        )

        # Update match with final scores
        match.participant1_score = final_participant1_score
        match.participant2_score = final_participant2_score

        if final_participant1_score > final_participant2_score:
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
        else:
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id

        if dispute.status in (
            DisputeRecord.RESOLVED_FOR_SUBMITTER,
            DisputeRecord.RESOLVED_FOR_OPPONENT,
            DisputeRecord.RESOLVED_CUSTOM,
        ):
            validate_transition(match, Match.COMPLETED)
            match.state = Match.COMPLETED
            match.completed_at = timezone.now()

        match.save()

        # User Profile Integration Hook - Match Finalized
        if dispute.status in (
            DisputeRecord.RESOLVED_FOR_SUBMITTER,
            DisputeRecord.RESOLVED_FOR_OPPONENT,
            DisputeRecord.RESOLVED_CUSTOM,
        ):
            def _notify_profile():
                try:
                    winner_user_ids = [match.winner_id] if match.winner_id else []
                    loser_user_ids = [match.loser_id] if match.loser_id else []
                    on_match_finalized(
                        match_id=match.id,
                        tournament_id=match.tournament_id,
                        winner_id=match.winner_id,
                        loser_id=match.loser_id,
                        winner_user_ids=winner_user_ids,
                        loser_user_ids=loser_user_ids,
                    )
                except Exception:
                    pass
            transaction.on_commit(_notify_profile)

        # Notify both participants of dispute resolution
        try:
            from django.contrib.auth import get_user_model
            _User = get_user_model()
            _pids = [p for p in [match.participant1_id, match.participant2_id] if p]
            _participants = list(_User.objects.filter(id__in=_pids))
            if _participants:
                _notify_users(
                    _participants,
                    event='dispute_resolved',
                    title=f"{match.participant1_name} vs {match.participant2_name} — dispute resolved",
                    body=f"The dispute for your match has been resolved. {resolution_notes[:200]}",
                    tournament_id=match.tournament_id,
                    match_id=match.id,
                )
        except Exception as _exc:
            logger.warning(f"dispute_resolved notification failed for dispute {dispute.id}: {_exc}")

        # Update bracket progression if resolved
        if dispute.status in (
            DisputeRecord.RESOLVED_FOR_SUBMITTER,
            DisputeRecord.RESOLVED_FOR_OPPONENT,
            DisputeRecord.RESOLVED_CUSTOM,
        ):
            try:
                from apps.tournaments.services.bracket_service import BracketService
                BracketService.update_bracket_after_match(match)
            except Exception as _exc:
                logger.error(f"Bracket update failed after dispute resolution (match {match.id}): {_exc}")

        # Broadcast dispute_resolved event
        try:
            from apps.tournaments.realtime.broadcast import broadcast_event
            broadcast_event(
                tournament_id=match.tournament_id,
                event_type='dispute_resolved',
                data={
                    'match_id': match.id,
                    'dispute_id': dispute.id,
                    'status': dispute.status,
                    'resolved_by': resolved_by_id,
                    'final_score1': final_participant1_score,
                    'final_score2': final_participant2_score,
                },
            )
        except Exception as _exc:
            logger.warning(f"dispute_resolved broadcast failed for match {match.id}: {_exc}")

        return dispute, match
    
    @staticmethod
    @transaction.atomic
    def escalate_dispute(
        dispute: DisputeRecord,
        escalated_by_id: int,
        escalation_notes: str
    ) -> DisputeRecord:
        """
        Escalate dispute to admin level.

        Args:
            dispute: DisputeRecord instance
            escalated_by_id: User ID escalating (organizer)
            escalation_notes: Reason for escalation

        Returns:
            Updated DisputeRecord instance
        """
        if dispute.status not in [DisputeRecord.OPEN, DisputeRecord.UNDER_REVIEW]:
            raise ValidationError(f"Cannot escalate dispute with status: {dispute.status}")

        dispute.status = DisputeRecord.ESCALATED
        dispute.resolution_notes = f"ESCALATED: {escalation_notes}"
        dispute.escalated_at = timezone.now()
        dispute.save()

        match = dispute.submission.match

        # Notify tournament organizer and staff admins about escalation
        try:
            from django.contrib.auth import get_user_model
            from apps.tournaments.models import Tournament as _Tournament
            _User = get_user_model()
            _tournament = _Tournament.objects.filter(id=match.tournament_id).first()
            _recipients = []
            if _tournament and _tournament.organizer_id:
                _organizer = _User.objects.filter(id=_tournament.organizer_id).first()
                if _organizer:
                    _recipients.append(_organizer)
            _admin_qs = _User.objects.filter(
                is_staff=True, is_active=True,
            ).exclude(id__in=[u.id for u in _recipients])[:10]
            _recipients.extend(list(_admin_qs))
            if _recipients:
                _notify_users(
                    _recipients,
                    event='dispute_escalated',
                    title="Dispute escalated — admin action required",
                    body=f"A dispute has been escalated and requires admin review. {escalation_notes[:200]}",
                    tournament_id=_tournament.id if _tournament else None,
                    match_id=match.id,
                )
        except Exception as _exc:
            logger.warning(f"escalation notification failed for dispute {dispute.id}: {_exc}")

        return dispute
    
    # =========================
    # Match Cancellation & Forfeit
    # =========================
    
    @staticmethod
    @transaction.atomic
    def cancel_match(
        match: Match,
        reason: str,
        cancelled_by_id: int
    ) -> Match:
        """
        Cancel match (organizer action).
        
        Args:
            match: Match instance
            reason: Cancellation reason
            cancelled_by_id: User ID who cancelled (organizer)
            
        Returns:
            Updated Match instance
        """
        if match.state == Match.COMPLETED:
            raise ValidationError("Cannot cancel completed match")
        
        validate_transition(match, Match.CANCELLED)
        match.state = Match.CANCELLED
        # Store reason in lobby_info
        match.lobby_info['cancellation_reason'] = reason
        match.lobby_info['cancelled_by_id'] = cancelled_by_id
        match.lobby_info['cancelled_at'] = timezone.now().isoformat()
        match.save()
        
        # Notify match participants of cancellation (Module 2.x)
        try:
            from django.contrib.auth import get_user_model
            _User = get_user_model()
            _pids = [p for p in [match.participant1_id, match.participant2_id] if p]
            _participants = list(_User.objects.filter(id__in=_pids))
            if _participants:
                _notify_users(
                    _participants,
                    event='match_cancelled',
                    title=f"{match.participant1_name} vs {match.participant2_name} — match cancelled",
                    body=f"Your match has been cancelled. Reason: {reason}",
                    tournament_id=match.tournament_id,
                    match_id=match.id,
                )
        except Exception as _exc:
            logger.warning(f"match_cancelled notification failed for match {match.id}: {_exc}")
        
        return match
    
    @staticmethod
    @transaction.atomic
    def forfeit_match(
        match: Match,
        reason: str,
        forfeiting_participant_id: Optional[int] = None
    ) -> Match:
        """
        Forfeit match due to no-show or other reason.
        
        Args:
            match: Match instance
            reason: Forfeit reason
            forfeiting_participant_id: Optional - which participant forfeited
            
        Returns:
            Updated Match instance
        """
        if match.state in [Match.COMPLETED, Match.CANCELLED]:
            raise ValidationError(f"Cannot forfeit match in state: {match.state}")
        
        validate_transition(match, Match.FORFEIT)
        match.state = Match.FORFEIT
        
        # Determine winner by forfeit
        if forfeiting_participant_id == match.participant1_id:
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id
        elif forfeiting_participant_id == match.participant2_id:
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
        # If neither specified, check who didn't check in
        elif not match.participant1_checked_in and match.participant2_checked_in:
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id
        elif match.participant1_checked_in and not match.participant2_checked_in:
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
        
        # Store forfeit details
        match.lobby_info['forfeit_reason'] = reason
        match.lobby_info['forfeited_at'] = timezone.now().isoformat()
        if forfeiting_participant_id:
            match.lobby_info['forfeiting_participant_id'] = forfeiting_participant_id
        
        match.completed_at = timezone.now()
        match.save()
        
        # Update bracket progression (Module 1.5)
        try:
            from apps.tournaments.services.bracket_service import BracketService
            BracketService.update_bracket_after_match(match)
        except Exception as _exc:
            logger.error(f"Bracket update failed after forfeit (match {match.id}): {_exc}")
        
        # Notify match participants of forfeit (Module 2.x)
        try:
            from django.contrib.auth import get_user_model
            _User = get_user_model()
            _pids = [p for p in [match.participant1_id, match.participant2_id] if p]
            _participants = list(_User.objects.filter(id__in=_pids))
            if _participants:
                _notify_users(
                    _participants,
                    event='match_forfeited',
                    title=f"{match.participant1_name} vs {match.participant2_name} — forfeit recorded",
                    body=f"A forfeit has been recorded for your match. Reason: {reason}",
                    tournament_id=match.tournament_id,
                    match_id=match.id,
                )
        except Exception as _exc:
            logger.warning(f"match_forfeited notification failed for match {match.id}: {_exc}")
        
        return match
    
    # =========================
    # Phase 0 Organizer Actions (extracted from organizer.py views)
    # =========================
    
    @staticmethod
    @transaction.atomic
    def organizer_reschedule_match(
        match: Match,
        new_time: datetime,
        reason: str,
        rescheduled_by_username: str
    ) -> Match:
        """
        Reschedule a match to new time (organizer action).
        
        Phase 0 Refactor: Extracted from organizer.py reschedule_match view.
        Preserves exact behavior - stores old/new times in lobby_info.
        
        Note: Original view used match.metadata (which doesn't exist on model).
        Corrected to use match.lobby_info (actual JSONField).
        
        Args:
            match: Match instance
            new_time: New scheduled datetime (aware)
            reason: Reason for rescheduling
            rescheduled_by_username: Username of organizer
        
        Returns:
            Updated Match instance
        """
        # Store old time for audit
        old_time = match.scheduled_time
        
        # Update match
        match.scheduled_time = new_time
        
        # Store reschedule metadata in lobby_info
        match.lobby_info['rescheduled'] = {
            'old_time': old_time.isoformat() if old_time else None,
            'new_time': new_time.isoformat(),
            'reason': reason,
            'rescheduled_at': timezone.now().isoformat(),
            'rescheduled_by': rescheduled_by_username,
        }
        match.save()
        
        return match
    
    @staticmethod
    @transaction.atomic
    def organizer_forfeit_match(
        match: Match,
        forfeiting_participant: int,
        reason: str,
        forfeited_by_username: str
    ) -> Match:
        """
        Mark match as forfeit (organizer action).
        
        Phase 0 Refactor: Extracted from organizer.py forfeit_match view.
        Preserves exact behavior - sets winner based on forfeiting participant.
        
        Args:
            match: Match instance
            forfeiting_participant: 1 or 2 (which participant forfeited)
            reason: Forfeit reason
            forfeited_by_username: Username of organizer
        
        Returns:
            Updated Match instance
        """
        # Set winner (opposite of forfeiting participant)
        if forfeiting_participant == 1:
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id
            match.participant1_score = 0
            match.participant2_score = 1  # Forfeit score
        else:
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
            match.participant1_score = 1  # Forfeit score
            match.participant2_score = 0
        
        validate_transition(match, Match.COMPLETED)
        match.state = Match.COMPLETED
        
        # Store forfeit metadata in lobby_info
        match.lobby_info['forfeit'] = {
            'forfeiting_participant': forfeiting_participant,
            'reason': reason,
            'forfeited_at': timezone.now().isoformat(),
            'forfeited_by': forfeited_by_username,
        }
        match.save()
        
        return match

    @staticmethod
    def _coerce_optional_bool(value: Any) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)

        token = str(value).strip().lower()
        if token in {'1', 'true', 'yes', 'y', 'on', 'allow', 'allowed', 'enabled'}:
            return True
        if token in {'0', 'false', 'no', 'n', 'off', 'disallow', 'disallowed', 'disabled', ''}:
            return False
        return None

    @staticmethod
    def _normalize_winner_side(winner_side: Any) -> Optional[Any]:
        if winner_side is None:
            return None
        token = str(winner_side).strip().lower()
        if token in {'', 'none', 'null'}:
            return None
        if token in {'1', 'a', 'p1', 'participant1', 'left', 'team1'}:
            return 1
        if token in {'2', 'b', 'p2', 'participant2', 'right', 'team2'}:
            return 2
        if token in {'draw', 'tie', 'd'}:
            return 'draw'
        return None

    @classmethod
    def draws_allowed_for_match(cls, match: Match) -> bool:
        tournament = getattr(match, 'tournament', None)
        if tournament is None:
            return False

        format_token = str(getattr(tournament, 'format', '') or '').strip().lower()
        format_default = format_token in {
            str(Tournament.ROUND_ROBIN).lower(),
            str(Tournament.GROUP_PLAYOFF).lower(),
            'group_stage',
            'league',
        }

        lobby_info = match.lobby_info if isinstance(match.lobby_info, dict) else {}
        match_settings = lobby_info.get('match_settings') if isinstance(lobby_info.get('match_settings'), dict) else {}
        for key in ('allow_draws', 'draw_allowed', 'draws_allowed'):
            parsed = cls._coerce_optional_bool(match_settings.get(key))
            if parsed is not None:
                return parsed

        tournament_settings = getattr(tournament, 'settings', None)
        if isinstance(tournament_settings, dict):
            top_level = tournament_settings
            nested_match_settings = (
                tournament_settings.get('match_settings')
                if isinstance(tournament_settings.get('match_settings'), dict)
                else {}
            )
            for key in ('allow_draws', 'draw_allowed', 'draws_allowed'):
                parsed = cls._coerce_optional_bool(nested_match_settings.get(key))
                if parsed is not None:
                    return parsed
            for key in ('allow_draws', 'draw_allowed', 'draws_allowed'):
                parsed = cls._coerce_optional_bool(top_level.get(key))
                if parsed is not None:
                    return parsed

        game = getattr(tournament, 'game', None)
        game_config = getattr(game, 'tournament_config', None)
        if isinstance(game_config, dict):
            for key in ('allow_draws', 'draw_allowed', 'draws_allowed'):
                parsed = cls._coerce_optional_bool(game_config.get(key))
                if parsed is not None:
                    return parsed

        return format_default
    
    @staticmethod
    @transaction.atomic
    def organizer_override_score(
        match: Match,
        score1: int,
        score2: int,
        reason: str,
        overridden_by_username: str,
        winner_side: Optional[Any] = None,
    ) -> Match:
        """
        Override match score (organizer correction action).
        
        Phase 0 Refactor: Extracted from organizer.py override_match_score view.
        Preserves exact behavior - stores old/new scores in lobby_info.
        
        Args:
            match: Match instance
            score1: New score for participant 1
            score2: New score for participant 2
            reason: Reason for override
            overridden_by_username: Username of organizer
            winner_side: Optional explicit winner side for tied scores when draws are disabled
        
        Returns:
            Updated Match instance
        """
        # Store old scores for audit
        old_score1 = match.participant1_score
        old_score2 = match.participant2_score

        if score1 < 0 or score2 < 0:
            raise ValidationError('Scores must be non-negative')
        
        # Update match
        match.participant1_score = score1
        match.participant2_score = score2

        normalized_winner_side = MatchService._normalize_winner_side(winner_side)
        draw_allowed = MatchService.draws_allowed_for_match(match)
        
        # Determine winner
        if score1 == score2:
            if draw_allowed:
                match.winner_id = None
                match.loser_id = None
            else:
                if normalized_winner_side == 'draw':
                    raise ValidationError('Draw results are not allowed for this match format.')
                if normalized_winner_side == 1:
                    match.winner_id = match.participant1_id
                    match.loser_id = match.participant2_id
                elif normalized_winner_side == 2:
                    match.winner_id = match.participant2_id
                    match.loser_id = match.participant1_id
                else:
                    raise ValidationError('Tied scores require selecting a winner for this format.')
        else:
            if normalized_winner_side == 'draw':
                raise ValidationError('Draw winner selection is only valid when both scores are tied.')
            if score1 > score2:
                match.winner_id = match.participant1_id
                match.loser_id = match.participant2_id
            else:
                match.winner_id = match.participant2_id
                match.loser_id = match.participant1_id
        
        validate_transition(match, Match.COMPLETED)
        match.state = Match.COMPLETED
        if not match.completed_at:
            match.completed_at = timezone.now()

        lobby_info = match.lobby_info if isinstance(match.lobby_info, dict) else {}
        resolved_winner_side = 0
        if match.winner_id == match.participant1_id:
            resolved_winner_side = 1
        elif match.winner_id == match.participant2_id:
            resolved_winner_side = 2
        
        # Store override metadata in lobby_info
        lobby_info['score_override'] = {
            'old_score1': old_score1,
            'old_score2': old_score2,
            'new_score1': score1,
            'new_score2': score2,
            'reason': reason,
            'winner_side': resolved_winner_side,
            'draw_allowed': draw_allowed,
            'result_mode': 'draw' if resolved_winner_side == 0 else 'winner',
            'overridden_at': timezone.now().isoformat(),
            'overridden_by': overridden_by_username,
        }
        match.lobby_info = lobby_info
        match.save()
        
        return match
    
    @staticmethod
    @transaction.atomic
    def organizer_cancel_match(
        match: Match,
        reason: str,
        cancelled_by_username: str
    ) -> Match:
        """
        Cancel a match (organizer action).
        
        Phase 0 Refactor: Extracted from organizer.py cancel_match view.
        Preserves exact behavior - sets state to cancelled.
        
        Args:
            match: Match instance
            reason: Cancellation reason
            cancelled_by_username: Username of organizer
        
        Returns:
            Updated Match instance
        """
        # Mark match as cancelled
        validate_transition(match, Match.CANCELLED)
        match.state = Match.CANCELLED
        
        # Store cancellation metadata in lobby_info
        match.lobby_info['cancelled'] = {
            'reason': reason,
            'cancelled_at': timezone.now().isoformat(),
            'cancelled_by': cancelled_by_username,
        }
        match.save()
        
        return match
    
    @staticmethod
    @transaction.atomic
    def organizer_submit_score(
        match: Match,
        score1: int,
        score2: int
    ) -> Match:
        """
        Submit/update match score (organizer action).
        
        Phase 0 Refactor: Extracted from organizer.py submit_match_score view.
        Preserves exact behavior - sets scores, determines winner, marks completed.
        
        Args:
            match: Match instance
            score1: Score for participant 1
            score2: Score for participant 2
        
        Returns:
            Updated Match instance
        
        Raises:
            ValidationError: If scores invalid
        """
        from django.core.exceptions import ValidationError
        
        # Validate scores
        if score1 < 0 or score2 < 0:
            raise ValidationError('Scores must be non-negative')
        
        if score1 == score2:
            raise ValidationError('Scores cannot be tied')
        
        # Update match
        match.participant1_score = score1
        match.participant2_score = score2
        validate_transition(match, Match.COMPLETED)
        match.state = Match.COMPLETED
        
        # Determine winner
        if score1 > score2:
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
        else:
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id
        
        match.save()
        
        return match
        
    # =========================
    # Statistics & Queries
    # =========================
    
    @staticmethod
    def get_match_stats(tournament: Tournament) -> Dict[str, Any]:
        """
        Calculate match statistics for tournament.
        
        Args:
            tournament: Tournament instance
            
        Returns:
            Dictionary with match statistics
            
        Example:
            stats = MatchService.get_match_stats(tournament)
            # {
            #     'total_matches': 15,
            #     'completed': 10,
            #     'live': 2,
            #     'pending': 3,
            #     'disputed': 1,
            #     'completion_rate': 0.67
            # }
        """
        matches = Match.objects.filter(tournament=tournament, is_deleted=False)
        
        total = matches.count()
        completed = matches.filter(state=Match.COMPLETED).count()
        live = matches.filter(state=Match.LIVE).count()
        pending = matches.filter(state__in=[Match.SCHEDULED, Match.CHECK_IN, Match.READY]).count()
        disputed = matches.filter(state=Match.DISPUTED).count()
        forfeited = matches.filter(state=Match.FORFEIT).count()
        cancelled = matches.filter(state=Match.CANCELLED).count()
        
        completion_rate = (completed / total) if total > 0 else 0.0
        
        return {
            'total_matches': total,
            'completed': completed,
            'live': live,
            'pending': pending,
            'disputed': disputed,
            'forfeited': forfeited,
            'cancelled': cancelled,
            'completion_rate': round(completion_rate, 2),
            'states': {
                'scheduled': matches.filter(state=Match.SCHEDULED).count(),
                'check_in': matches.filter(state=Match.CHECK_IN).count(),
                'ready': matches.filter(state=Match.READY).count(),
                'live': live,
                'pending_result': matches.filter(state=Match.PENDING_RESULT).count(),
                'completed': completed,
                'disputed': disputed,
                'forfeit': forfeited,
                'cancelled': cancelled,
            }
        }
    
    @staticmethod
    def get_live_matches(tournament: Tournament) -> QuerySet[Match]:
        """
        Get all live matches for tournament.
        
        Args:
            tournament: Tournament instance
            
        Returns:
            QuerySet of live matches
        """
        return Match.objects.filter(
            tournament=tournament,
            state=Match.LIVE,
            is_deleted=False
        ).select_related('tournament', 'bracket').order_by('round_number', 'match_number')
    
    @staticmethod
    def get_participant_matches(
        tournament: Tournament,
        participant_id: int
    ) -> QuerySet[Match]:
        """
        Get all matches for a specific participant.
        
        Args:
            tournament: Tournament instance
            participant_id: Team ID or User ID
            
        Returns:
            QuerySet of matches for participant
        """
        return Match.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).filter(
            Q(participant1_id=participant_id) | Q(participant2_id=participant_id)
        ).select_related('tournament', 'bracket').order_by('round_number', 'match_number')
    
    # =========================
    # Bracket Integration (Module 1.5 - BracketService Integration)
    # =========================
    
    @staticmethod
    def recalculate_bracket(tournament_id: int, force: bool = False) -> 'Bracket':
        """
        Recalculate bracket for tournament (delegates to BracketService).
        
        This is a wrapper method that delegates to BracketService.recalculate_bracket()
        for consistency with the service layer architecture.
        
        Args:
            tournament_id: Tournament ID to recalculate bracket for
            force: If True, completely regenerate bracket. If False, preserve results.
        
        Returns:
            Updated or regenerated Bracket instance
        
        Raises:
            ValidationError: If tournament not found or bracket is finalized
        
        Example:
            >>> # Soft recalculation (preserves completed matches)
            >>> bracket = MatchService.recalculate_bracket(tournament_id=123)
            >>> 
            >>> # Force regeneration (deletes all matches and bracket)
            >>> bracket = MatchService.recalculate_bracket(tournament_id=123, force=True)
        """
        from apps.tournaments.services.bracket_service import BracketService
        return BracketService.recalculate_bracket(tournament_id=tournament_id, force=force)

    # ------------------------------------------------------------------
    # Series (BO3 / BO5) helpers
    # ------------------------------------------------------------------

    @staticmethod
    def submit_game_score(
        match: "Match",
        game_number: int,
        participant1_score: int,
        participant2_score: int,
        submitted_by_id: int,
    ) -> "Match":
        """
        Record the result of a single game within a BO3/BO5 series.

        Updates ``match.game_scores`` with the new game entry, then
        recalculates the series series_wins for each side.  When one
        side reaches the wins-needed threshold (2 for BO3, 3 for BO5)
        the overall match is finalized via ``submit_result()``.

        Args:
            match:              Match instance (best_of must be 3 or 5).
            game_number:        1-indexed game number (must be > existing games).
            participant1_score: Rounds/points won by participant 1 in this game.
            participant2_score: Rounds/points won by participant 2 in this game.
            submitted_by_id:    User ID submitting this game result.

        Returns:
            Updated Match instance.

        Raises:
            ValidationError: If match has best_of=1, game already exists,
                             or submitter is not a participant.
        """
        from django.core.exceptions import ValidationError
        if match.best_of == 1:
            raise ValidationError("Use submit_result() for BO1 matches.")
        if submitted_by_id not in [match.participant1_id, match.participant2_id]:
            raise ValidationError("Only match participants can submit game scores.")
        if match.state not in [Match.LIVE, Match.PENDING_RESULT]:
            raise ValidationError(f"Cannot submit game score in state: {match.state}")

        games: list = list(match.game_scores or [])  # ensure fresh copy
        existing_nums = {g.get("game") for g in games}
        if game_number in existing_nums:
            raise ValidationError(f"Game {game_number} score already recorded.")

        # Determine winner of this game
        if participant1_score > participant2_score:
            winner_slot = 1
        elif participant2_score > participant1_score:
            winner_slot = 2
        else:
            raise ValidationError("Individual game cannot end in a tie.")

        games.append({
            "game": game_number,
            "p1": participant1_score,
            "p2": participant2_score,
            "winner_slot": winner_slot,
        })
        games.sort(key=lambda g: g["game"])  # keep ordered

        match.game_scores = games
        match.save(update_fields=["game_scores"])

        # Tally wins
        p1_wins = sum(1 for g in games if g["winner_slot"] == 1)
        p2_wins = sum(1 for g in games if g["winner_slot"] == 2)
        wins_needed = (match.best_of // 2) + 1  # BO3→2, BO5→3

        if p1_wins >= wins_needed or p2_wins >= wins_needed:
            # Finalize the series using cumulative game counts as series scores
            match = MatchService.submit_result(
                match=match,
                submitted_by_id=submitted_by_id,
                participant1_score=p1_wins,
                participant2_score=p2_wins,
            )

        return match

    @staticmethod
    def get_series_status(match: "Match") -> dict:
        """
        Return a summary of the current series state for a BO3/BO5 match.

        Returns:
            dict with keys: best_of, wins_needed, p1_wins, p2_wins,
            games_played, games, is_complete, series_winner_slot.
        """
        games: list = list(match.game_scores or [])
        p1_wins = sum(1 for g in games if g.get("winner_slot") == 1)
        p2_wins = sum(1 for g in games if g.get("winner_slot") == 2)
        wins_needed = (match.best_of // 2) + 1
        is_complete = p1_wins >= wins_needed or p2_wins >= wins_needed
        series_winner_slot = None
        if p1_wins >= wins_needed:
            series_winner_slot = 1
        elif p2_wins >= wins_needed:
            series_winner_slot = 2

        return {
            "best_of": match.best_of,
            "wins_needed": wins_needed,
            "p1_wins": p1_wins,
            "p2_wins": p2_wins,
            "games_played": len(games),
            "games": games,
            "is_complete": is_complete,
            "series_winner_slot": series_winner_slot,
        }

    # ------------------------------------------------------------------
    # Double Elimination: Grand Finals Reset
    # ------------------------------------------------------------------

    @staticmethod
    def check_and_activate_gf_reset(match: "Match") -> bool:
        """
        After Grand Finals completes, check if a reset match is needed.

        In double elimination, when the losers bracket finalist (who has 1 prior
        loss) beats the winners bracket finalist (who has 0 losses) in Grand
        Finals, both players now have 1 loss each — a reset match is required.

        This method:
        1. Checks if ``match`` is the Grand Finals node (bracket_type='main',
           parent exists with is_bye=True and same bracket).
        2. Determines who came from the winners side (no prior losses) vs the
           losers side.
        3. If winners-side participant LOST the GF, activates the reset node by
           setting ``is_bye=False`` and populating participants.

        Args:
            match: Completed Grand Finals match.

        Returns:
            True if a reset match was activated, False otherwise.
        """
        from apps.tournaments.models.bracket import BracketNode, Bracket

        try:
            node = match.bracket_node
        except Exception:
            return False

        if not node:
            return False

        # Only applies to double elimination Grand Finals
        if node.bracket.format != Bracket.DOUBLE_ELIMINATION:
            return False

        if node.bracket_type != BracketNode.MAIN:
            return False

        # Check parent is the GFR node (is_bye=True placeholder)
        parent = node.parent_node
        if not parent or not getattr(parent, "is_bye", False):
            return False

        # The node's child1 came from winners bracket, child2 from losers bracket.
        # If the losers-side winner (child2 winner) beat child1 participant → reset.
        child1 = node.child1_node  # WB side
        child2 = node.child2_node  # LB side

        wb_participant_id = child1.winner_id if child1 else None
        lb_participant_id = child2.winner_id if child2 else None

        if not wb_participant_id or not lb_participant_id:
            # Fallback: use p1 = WB side by convention
            wb_participant_id = node.participant1_id
            lb_participant_id = node.participant2_id

        gf_winner_id = match.winner_id
        if gf_winner_id != lb_participant_id:
            # WB winner won Grand Finals → no reset needed
            return False

        # LB winner won → activate reset match
        # Both contestants: WB finalist (now 1 loss) vs LB finalist (1 loss)
        parent.is_bye = False
        parent.participant1_id = wb_participant_id
        parent.participant1_name = (
            match.participant1_name if match.participant1_id == wb_participant_id
            else match.participant2_name
        )
        parent.participant2_id = lb_participant_id
        parent.participant2_name = (
            match.participant1_name if match.participant1_id == lb_participant_id
            else match.participant2_name
        )
        parent.save(update_fields=["is_bye", "participant1_id", "participant1_name",
                                   "participant2_id", "participant2_name"])
        return True
