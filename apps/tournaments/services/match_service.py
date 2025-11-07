"""
MatchService - Business logic for match lifecycle management (Module 1.4)

Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 6: MatchService)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 6: Match Lifecycle Models)
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Match UI flows)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-001, ADR-003, ADR-007)

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
    Dispute,
    Bracket,
    Registration
)

# Module 2.3: Real-time WebSocket broadcasting
from apps.tournaments.realtime.utils import (
    broadcast_match_started,
    broadcast_score_updated,
    broadcast_match_completed,
)

logger = logging.getLogger(__name__)


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
        
        # TODO: Send notification to participants (Module 2.x)
        # TODO: WebSocket broadcast: match created (ADR-007)
        
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
            match.state = Match.READY
        else:
            match.state = Match.CHECK_IN
        
        match.save()
        
        # TODO: Send notification to opponent (Module 2.x)
        # TODO: WebSocket broadcast: check-in update (ADR-007)
        
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
        
        match.state = Match.LIVE
        match.started_at = timezone.now()
        match.save()
        
        # Module 2.3: Broadcast match_started event to WebSocket clients
        try:
            broadcast_match_started(
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
        # Validation
        if match.state not in [Match.LIVE, Match.PENDING_RESULT]:
            raise ValidationError(f"Cannot submit result in state: {match.state}")
        
        if participant1_score < 0 or participant2_score < 0:
            raise ValidationError("Scores cannot be negative")
        
        if participant1_score == participant2_score:
            raise ValidationError("Match cannot end in a tie (implement tiebreaker logic)")
        
        # Verify submitter is a participant
        if submitted_by_id not in [match.participant1_id, match.participant2_id]:
            raise ValidationError("Only participants can submit results")
        
        # Update match with submitted result
        match.participant1_score = participant1_score
        match.participant2_score = participant2_score
        match.state = Match.PENDING_RESULT
        
        # Determine winner
        if participant1_score > participant2_score:
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
        else:
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id
        
        match.save()
        
        # Module 2.3: Broadcast score_updated event to WebSocket clients
        try:
            broadcast_score_updated(
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
        
        # TODO: Notify opponent to confirm result (Module 2.x)
        
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
        # Validation
        if match.state != Match.PENDING_RESULT:
            raise ValidationError(f"Cannot confirm result in state: {match.state}")
        
        if not match.has_result:
            raise ValidationError("No result to confirm (winner not set)")
        
        # Finalize match
        match.state = Match.COMPLETED
        match.completed_at = timezone.now()
        match.save()
        
        # Module 2.3: Broadcast match_completed event to WebSocket clients
        try:
            broadcast_match_completed(
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
        
        # TODO: Award DeltaCoin for win (Module 2.x - EconomyService)
        # TODO: Update player stats (Module 2.x - AnalyticsService)
        
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
        evidence_screenshot = None,
        evidence_video_url: str = ""
    ) -> Dispute:
        """
        Create dispute for match result.
        
        Args:
            match: Match instance
            initiated_by_id: User ID initiating dispute
            reason: Dispute reason (use Dispute.REASON_CHOICES)
            description: Detailed description
            evidence_screenshot: Optional screenshot file
            evidence_video_url: Optional video URL
            
        Returns:
            Created Dispute instance
            
        Raises:
            ValidationError: If dispute not allowed
            
        Example:
            dispute = MatchService.report_dispute(
                match=match,
                initiated_by_id=102,
                reason=Dispute.SCORE_MISMATCH,
                description="Claimed score is incorrect",
                evidence_video_url="https://youtube.com/evidence"
            )
        """
        # Validation
        if match.state not in [Match.PENDING_RESULT, Match.COMPLETED]:
            raise ValidationError(f"Cannot dispute match in state: {match.state}")
        
        # Verify initiator is a participant
        if initiated_by_id not in [match.participant1_id, match.participant2_id]:
            raise ValidationError("Only participants can initiate disputes")
        
        # Check if dispute already exists
        existing_dispute = Dispute.objects.filter(
            match=match,
            status__in=[Dispute.OPEN, Dispute.UNDER_REVIEW, Dispute.ESCALATED]
        ).first()
        
        if existing_dispute:
            raise ValidationError("An active dispute already exists for this match")
        
        # Create dispute
        dispute = Dispute.objects.create(
            match=match,
            initiated_by_id=initiated_by_id,
            reason=reason,
            description=description,
            evidence_screenshot=evidence_screenshot,
            evidence_video_url=evidence_video_url,
            status=Dispute.OPEN
        )
        
        # Update match state
        match.state = Match.DISPUTED
        match.save()
        
        # TODO: Notify organizer of new dispute (Module 2.x)
        # TODO: WebSocket broadcast: dispute created (ADR-007)
        
        return dispute
    
    @staticmethod
    @transaction.atomic
    def resolve_dispute(
        dispute: Dispute,
        resolved_by_id: int,
        resolution_notes: str,
        final_participant1_score: int,
        final_participant2_score: int,
        status: str = None
    ) -> Tuple[Dispute, Match]:
        """
        Resolve dispute with final decision.
        
        Module 2.4: Security Hardening - Audit logging added
        
        Args:
            dispute: Dispute instance
            resolved_by_id: User ID resolving (organizer or admin)
            resolution_notes: Notes explaining resolution
            final_participant1_score: Final score for participant 1
            final_participant2_score: Final score for participant 2
            status: Optional status (defaults to RESOLVED, can be ESCALATED)
            
        Returns:
            Tuple of (Updated Dispute, Updated Match)
            
        Raises:
            ValidationError: If resolution not allowed
            
        Example:
            dispute, match = MatchService.resolve_dispute(
                dispute=dispute,
                resolved_by_id=1,
                resolution_notes="Verified from game logs",
                final_participant1_score=13,
                final_participant2_score=11
            )
        """
        # Validation
        if dispute.status not in [Dispute.OPEN, Dispute.UNDER_REVIEW, Dispute.ESCALATED]:
            raise ValidationError(f"Cannot resolve dispute with status: {dispute.status}")
        
        if final_participant1_score < 0 or final_participant2_score < 0:
            raise ValidationError("Scores cannot be negative")
        
        # Store original status for audit
        original_status = dispute.status
        
        # Update dispute
        dispute.status = status or Dispute.RESOLVED
        dispute.resolved_by_id = resolved_by_id
        dispute.resolved_at = timezone.now()
        dispute.resolution_notes = resolution_notes
        dispute.final_participant1_score = final_participant1_score
        dispute.final_participant2_score = final_participant2_score
        dispute.save()
        
        # =====================================================================
        # MODULE 2.4: Audit Logging
        # =====================================================================
        from apps.tournaments.security.audit import audit_event, AuditAction
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        resolved_by = User.objects.filter(id=resolved_by_id).first()
        
        # Determine audit action based on status
        if status == Dispute.ESCALATED:
            audit_action = AuditAction.DISPUTE_ESCALATE
        else:
            audit_action = AuditAction.DISPUTE_RESOLVE
        
        audit_event(
            user=resolved_by,
            action=audit_action,
            meta={
                'dispute_id': dispute.id,
                'match_id': dispute.match_id,
                'tournament_id': dispute.match.tournament_id if dispute.match else None,
                'original_status': original_status,
                'new_status': dispute.status,
                'final_participant1_score': final_participant1_score,
                'final_participant2_score': final_participant2_score,
                'resolution_notes': resolution_notes[:200],  # Truncate for audit
            }
        )
        
        # Update match with final scores
        match = dispute.match
        match.participant1_score = final_participant1_score
        match.participant2_score = final_participant2_score
        
        # Determine winner
        if final_participant1_score > final_participant2_score:
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
        else:
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id
        
        # Finalize match if resolved (not escalated)
        if dispute.status == Dispute.RESOLVED:
            match.state = Match.COMPLETED
            match.completed_at = timezone.now()
        
        match.save()
        
        # TODO: Notify participants of resolution (Module 2.x)
        # TODO: Update bracket if match completed (Module 1.5)
        # TODO: WebSocket broadcast: dispute resolved (ADR-007)
        
        return dispute, match
    
    @staticmethod
    @transaction.atomic
    def escalate_dispute(
        dispute: Dispute,
        escalated_by_id: int,
        escalation_notes: str
    ) -> Dispute:
        """
        Escalate dispute to admin level.
        
        Args:
            dispute: Dispute instance
            escalated_by_id: User ID escalating (organizer)
            escalation_notes: Reason for escalation
            
        Returns:
            Updated Dispute instance
        """
        if dispute.status not in [Dispute.OPEN, Dispute.UNDER_REVIEW]:
            raise ValidationError(f"Cannot escalate dispute with status: {dispute.status}")
        
        dispute.status = Dispute.ESCALATED
        dispute.resolution_notes = f"ESCALATED: {escalation_notes}"
        dispute.save()
        
        # TODO: Notify admins (Module 2.x)
        
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
        
        match.state = Match.CANCELLED
        # Store reason in lobby_info
        match.lobby_info['cancellation_reason'] = reason
        match.lobby_info['cancelled_by_id'] = cancelled_by_id
        match.lobby_info['cancelled_at'] = timezone.now().isoformat()
        match.save()
        
        # TODO: Notify participants (Module 2.x)
        
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
        
        # TODO: Update bracket progression (Module 1.5)
        # TODO: Notify participants (Module 2.x)
        
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
