"""
Result Submission Service - Phase 6, Epic 6.1

Orchestrates match result submission workflow from player submission
through opponent confirmation or auto-confirmation after 24 hours.

Architecture:
- Part of tournament_ops orchestration layer
- Uses adapters for domain access (no ORM)
- Publishes events for all state transitions
- Coordinates with MatchService for finalization

Flow:
1. Player submits result → PENDING
2. Opponent confirms → CONFIRMED → finalize
3. Or: 24h timeout → AUTO_CONFIRMED → finalize
4. Or: Opponent disputes → DISPUTED (Epic 6.2)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from apps.common.events.event_bus import Event, get_event_bus
from apps.tournament_ops.dtos import (
    MatchResultSubmissionDTO,
    ResultVerificationResultDTO,
    MatchDTO,
)
from apps.tournament_ops.adapters import (
    ResultSubmissionAdapterProtocol,
    SchemaValidationAdapterProtocol,
    MatchAdapterProtocol,
    GameAdapterProtocol,
    DisputeAdapterProtocol,  # Epic 6.2
)
from apps.tournament_ops.exceptions import (
    ResultSubmissionError,
    InvalidSubmissionStateError,
    PermissionDeniedError,
    InvalidMatchStateError,
    OpponentVerificationError,  # Epic 6.2
    InvalidOpponentDecisionError,  # Epic 6.2
)


class ResultSubmissionService:
    """
    Orchestrates match result submission and confirmation workflow.

    Dependencies (constructor injection):
    - result_submission_adapter: Access to result submission domain
    - schema_validation_adapter: Schema validation (Phase 2 integration)
    - match_adapter: Match state validation
    - game_adapter: Game configuration lookup

    Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.1
    """

    def __init__(
        self,
        result_submission_adapter: ResultSubmissionAdapterProtocol,
        schema_validation_adapter: SchemaValidationAdapterProtocol,
        match_adapter: MatchAdapterProtocol,
        game_adapter: GameAdapterProtocol,
        dispute_adapter: DisputeAdapterProtocol = None,  # Epic 6.2 (optional for backward compat)
    ):
        self.result_submission_adapter = result_submission_adapter
        self.schema_validation_adapter = schema_validation_adapter
        self.match_adapter = match_adapter
        self.game_adapter = game_adapter
        self.dispute_adapter = dispute_adapter  # Epic 6.2

    def submit_result(
        self,
        match_id: int,
        submitted_by_user_id: int,
        submitted_by_team_id: Optional[int],
        raw_result_payload: Dict[str, Any],
        proof_screenshot_url: Optional[str] = None,
        submitter_notes: str = "",
    ) -> MatchResultSubmissionDTO:
        """
        Submit match result with proof.

        Workflow:
        1. Validate match state (must be LIVE or PENDING_RESULT)
        2. Validate user has permission (is participant in match)
        3. Validate result payload against schema
        4. Create submission with status='pending'
        5. Publish MatchResultSubmittedEvent
        6. Schedule auto-confirm task (24 hours)

        Args:
            match_id: Match ID
            submitted_by_user_id: User ID of submitter
            submitted_by_team_id: Team ID if team tournament
            raw_result_payload: Game-specific result data
            proof_screenshot_url: URL to proof screenshot
            submitter_notes: Optional notes from submitter

        Returns:
            MatchResultSubmissionDTO

        Raises:
            InvalidMatchStateError: Match not in valid state
            PermissionDeniedError: User not authorized to submit
            ResultSubmissionError: Validation or creation failed
        """
        # 1. Validate match state
        match = self.match_adapter.get_match(match_id)
        if match.state not in ['live', 'pending_result']:
            raise InvalidMatchStateError(
                f"Cannot submit result for match in state: {match.state}"
            )

        # 2. Validate submitter is participant
        self._validate_submitter_is_participant(
            match, submitted_by_user_id, submitted_by_team_id
        )

        # 3. Schema validation (light check for Epic 6.1)
        game_slug = self._get_game_slug_for_match(match)
        validation_result = self.schema_validation_adapter.validate_payload(
            game_slug, raw_result_payload
        )
        
        if not validation_result.is_valid:
            raise ResultSubmissionError(
                f"Invalid result payload: {', '.join(validation_result.errors)}"
            )

        # 4. Create submission
        submission = self.result_submission_adapter.create_submission(
            match_id=match_id,
            submitted_by_user_id=submitted_by_user_id,
            submitted_by_team_id=submitted_by_team_id,
            raw_result_payload=raw_result_payload,
            proof_screenshot_url=proof_screenshot_url,
            submitter_notes=submitter_notes,
        )

        # 5. Publish event
        get_event_bus().publish(Event(
            name='MatchResultSubmittedEvent',
            payload={
                'match_id': match_id,
                'submission_id': submission.id,
                'submitted_by_user_id': submitted_by_user_id,
                'submitted_by_team_id': submitted_by_team_id,
                'status': submission.status,
                'auto_confirm_deadline': submission.auto_confirm_deadline.isoformat(),
            },
            metadata={
                'game_slug': game_slug,
                'has_proof': bool(proof_screenshot_url),
            }
        ))

        # 6. Schedule auto-confirm task
        self._schedule_auto_confirm_task(submission.id)

        return submission

    def confirm_result(
        self,
        submission_id: int,
        confirmed_by_user_id: int,
    ) -> MatchResultSubmissionDTO:
        """
        Opponent confirms submitted result.

        Workflow:
        1. Validate user is opponent (not submitter)
        2. Validate submission status='pending'
        3. Update status='confirmed'
        4. Trigger finalization (stub for Epic 6.4)
        5. Publish MatchResultConfirmedEvent

        Args:
            submission_id: Submission ID
            confirmed_by_user_id: User ID confirming result

        Returns:
            MatchResultSubmissionDTO

        Raises:
            PermissionDeniedError: User not authorized to confirm
            InvalidSubmissionStateError: Submission not in pending state
        """
        # 1. Fetch submission
        submission = self.result_submission_adapter.get_submission(submission_id)

        # 2. Validate state
        if submission.status != 'pending':
            raise InvalidSubmissionStateError(
                f"Cannot confirm submission in state: {submission.status}"
            )

        # 3. Validate confirmer is opponent
        match = self.match_adapter.get_match(submission.match_id)
        if confirmed_by_user_id == submission.submitted_by_user_id:
            raise PermissionDeniedError(
                "Submitter cannot confirm their own result"
            )

        # Validate confirmer is match participant
        self._validate_user_is_match_participant(match, confirmed_by_user_id)

        # 4. Update status
        submission = self.result_submission_adapter.update_submission_status(
            submission_id=submission_id,
            status='confirmed',
            confirmed_by_user_id=confirmed_by_user_id,
        )

        # 5. Trigger finalization (stub for Epic 6.4)
        self._maybe_finalize_result(submission)

        # 6. Publish event
        get_event_bus().publish(Event(
            name='MatchResultConfirmedEvent',
            payload={
                'match_id': submission.match_id,
                'submission_id': submission.id,
                'confirmed_by_user_id': confirmed_by_user_id,
                'status': submission.status,
            },
            metadata={
                'confirmed_at': submission.confirmed_at.isoformat() if submission.confirmed_at else None,
            }
        ))

        return submission

    def auto_confirm_result(self, submission_id: int) -> MatchResultSubmissionDTO:
        """
        Auto-confirm result after 24-hour timeout.

        Triggered by Celery task.

        Workflow:
        1. Check deadline passed
        2. Check status still='pending'
        3. Update status='auto_confirmed'
        4. Trigger finalization
        5. Publish MatchResultAutoConfirmedEvent

        Args:
            submission_id: Submission ID

        Returns:
            MatchResultSubmissionDTO (unchanged if already confirmed/disputed)
        """
        # 1. Fetch submission
        submission = self.result_submission_adapter.get_submission(submission_id)

        # 2. Idempotent: If not pending, skip
        if submission.status != 'pending':
            return submission

        # 3. Check deadline (defensive check, task should only run after deadline)
        if not submission.is_auto_confirm_expired():
            return submission

        # 4. Update status
        submission = self.result_submission_adapter.update_submission_status(
            submission_id=submission_id,
            status='auto_confirmed',
        )

        # 5. Trigger finalization
        self._maybe_finalize_result(submission)

        # 6. Publish event
        get_event_bus().publish(Event(
            name='MatchResultAutoConfirmedEvent',
            payload={
                'match_id': submission.match_id,
                'submission_id': submission.id,
                'status': submission.status,
            },
            metadata={
                'auto_confirm_deadline': submission.auto_confirm_deadline.isoformat(),
            }
        ))

        return submission

    def opponent_response(
        self,
        submission_id: int,
        responding_user_id: int,
        decision: str,
        reason_code: Optional[str] = None,
        notes: str = "",
        evidence: Optional[List[Dict[str, str]]] = None,
    ) -> MatchResultSubmissionDTO:
        """
        Process opponent response to a match result submission.
        
        Workflow:
        1. Validate submission is pending
        2. Validate responding_user is opponent (not submitter)
        3. If decision="confirm":
           - Call confirm_result logic
           - Log verification step
           - Publish MatchResultConfirmedEvent
        4. If decision="dispute":
           - Create DisputeRecord via DisputeAdapter
           - Attach evidence (if provided)
           - Set submission status to 'disputed'
           - Log verification step
           - Publish MatchResultDisputedEvent
        
        Args:
            submission_id: MatchResultSubmission ID
            responding_user_id: User responding (opponent)
            decision: "confirm" or "dispute"
            reason_code: Reason for dispute (required if decision="dispute")
            notes: Additional context from opponent
            evidence: List of evidence items [{type, url, notes}]
            
        Returns:
            Updated MatchResultSubmissionDTO
            
        Raises:
            InvalidOpponentDecisionError: Invalid decision value
            PermissionDeniedError: Submitter trying to respond to own submission
            InvalidSubmissionStateError: Submission not in pending state
            OpponentVerificationError: Other validation failures
            
        Reference: Phase 6, Epic 6.2 - Opponent Verification & Dispute System
        """
        # Validate decision
        if decision not in ('confirm', 'dispute'):
            raise InvalidOpponentDecisionError(
                f"Invalid decision: {decision}. Must be 'confirm' or 'dispute'"
            )
        
        # Get submission
        submission = self.result_submission_adapter.get_submission(submission_id)
        
        # Validate submission is pending
        if submission.status != 'pending':
            raise InvalidSubmissionStateError(
                f"Cannot respond to submission in state: {submission.status}. Must be 'pending'"
            )
        
        # Validate responder is not the submitter
        if responding_user_id == submission.submitted_by_user_id:
            raise PermissionDeniedError(
                "Submitter cannot respond to their own result submission"
            )
        
        # Get match to validate participant
        match = self.match_adapter.get_match(submission.match_id)
        
        # Validate responder is match participant (opponent team)
        # For now, simple check: responder must be participant in match but not submitter's team
        if match.team_a_id == submission.submitted_by_team_id:
            opponent_team_id = match.team_b_id
        elif match.team_b_id == submission.submitted_by_team_id:
            opponent_team_id = match.team_a_id
        else:
            raise OpponentVerificationError(
                f"Submitter team {submission.submitted_by_team_id} not in match {match.id}"
            )
        
        # TODO (Epic 6.3): Full team membership validation via TeamAdapter
        # For Epic 6.2, we trust the responding_user_id belongs to opponent_team_id
        
        # Process decision
        if decision == 'confirm':
            # Confirm path: reuse confirm_result logic
            submission = self.confirm_result(
                submission_id=submission_id,
                confirmed_by_user_id=responding_user_id
            )
            
            # Log verification step
            if self.dispute_adapter:
                self.dispute_adapter.log_verification_step(
                    submission_id=submission_id,
                    step='opponent_confirm',
                    status='success',
                    details={
                        'responding_user_id': responding_user_id,
                        'notes': notes,
                    },
                    performed_by_user_id=responding_user_id,
                )
            
            return submission
        
        elif decision == 'dispute':
            # Validate reason_code required
            if not reason_code:
                raise InvalidOpponentDecisionError(
                    "reason_code required when decision='dispute'"
                )
            
            # Ensure DisputeAdapter available
            if not self.dispute_adapter:
                raise OpponentVerificationError(
                    "DisputeAdapter not configured (Epic 6.2 required)"
                )
            
            # Create dispute
            dispute = self.dispute_adapter.create_dispute(
                submission_id=submission_id,
                opened_by_user_id=responding_user_id,
                opened_by_team_id=opponent_team_id,
                reason_code=reason_code,
                description=notes,
            )
            
            # Attach evidence if provided
            if evidence:
                for item in evidence:
                    self.dispute_adapter.add_evidence(
                        dispute_id=dispute.id,
                        uploaded_by_user_id=responding_user_id,
                        evidence_type=item.get('type', 'other'),
                        url=item.get('url', ''),
                        notes=item.get('notes', ''),
                    )
            
            # Update submission status to 'disputed'
            submission = self.result_submission_adapter.update_submission_status(
                submission_id=submission_id,
                status='disputed',
            )
            
            # Log verification step
            self.dispute_adapter.log_verification_step(
                submission_id=submission_id,
                step='opponent_dispute',
                status='success',
                details={
                    'dispute_id': dispute.id,
                    'reason_code': reason_code,
                    'notes': notes,
                    'evidence_count': len(evidence) if evidence else 0,
                },
                performed_by_user_id=responding_user_id,
            )
            
            # Publish MatchResultDisputedEvent
            get_event_bus().publish(Event(
                name='MatchResultDisputedEvent',
                payload={
                    'match_id': submission.match_id,
                    'submission_id': submission.id,
                    'dispute_id': dispute.id,
                    'reason_code': reason_code,
                    'opened_by_user_id': responding_user_id,
                    'opened_by_team_id': opponent_team_id,
                },
                metadata={
                    'notes': notes,
                    'evidence_count': len(evidence) if evidence else 0,
                }
            ))
            
            return submission
        
        # Should never reach here
        raise OpponentVerificationError(f"Unhandled decision: {decision}")

    # ==========================================================================
    # Helper methods (internal)
    # ==========================================================================

    def _validate_submitter_is_participant(
        self,
        match: MatchDTO,
        user_id: int,
        team_id: Optional[int],
    ) -> None:
        """
        Validate submitter is participant in match.

        Raises:
            PermissionDeniedError: User not a match participant
        """
        # For team matches, check team_id matches participant
        if team_id:
            if team_id not in [match.team_a_id, match.team_b_id]:
                raise PermissionDeniedError(
                    f"Team {team_id} is not a participant in match {match.id}"
                )
        else:
            # For individual matches, user_id should match participant
            # Note: In team tournaments, we'd need to check team membership via TeamAdapter
            # For Epic 6.1, simple validation is sufficient
            pass

    def _validate_user_is_match_participant(
        self,
        match: MatchDTO,
        user_id: int,
    ) -> None:
        """
        Validate user is participant in match.

        Raises:
            PermissionDeniedError: User not a match participant
        """
        # TODO (Epic 6.2): Full participant validation with team membership checks
        # For Epic 6.1, we trust the caller
        pass

    def _get_game_slug_for_match(self, match: MatchDTO) -> str:
        """
        Get game slug for match via tournament → game lookup.

        Returns:
            Game slug (e.g., 'valorant', 'csgo')
        """
        # TODO (Epic 6.4): Proper tournament → game lookup via TournamentAdapter + GameAdapter
        # For Epic 6.1, extract from match.result metadata if available
        if match.result and isinstance(match.result, dict):
            return match.result.get('game_slug', 'unknown')
        return 'unknown'

    def _maybe_finalize_result(self, submission: MatchResultSubmissionDTO) -> None:
        """
        Trigger result finalization if ready.

        Epic 6.4 will implement full finalization workflow:
        - Schema validation
        - Score calculation via GameRulesEngine
        - Match.accept_match_result() call
        - MatchCompletedEvent publication
        - Bracket progression

        For Epic 6.1, this is a stub.
        """
        # TODO (Epic 6.4): Call ResultVerificationService.finalize_result()
        # For now, just log
        pass

    def _schedule_auto_confirm_task(self, submission_id: int) -> None:
        """
        Schedule Celery task to auto-confirm after 24 hours.

        Args:
            submission_id: Submission ID
        """
        from apps.tournament_ops.tasks_result_submission import auto_confirm_submission_task
        
        # Schedule task to run after 24 hours
        # Using Celery's eta (estimated time of arrival)
        auto_confirm_submission_task.apply_async(
            args=[submission_id],
            countdown=24 * 60 * 60,  # 24 hours in seconds
        )
