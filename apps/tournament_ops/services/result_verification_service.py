"""
Result Verification Service - Phase 6, Epic 6.4

Core service for match result verification and finalization.

Orchestrates:
- Schema validation via SchemaValidationAdapter
- Score calculation via GameRulesEngine
- Match finalization via MatchService
- Dispute resolution integration
- Verification logging and auditing

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4 (Result Verification & Finalization Service)
"""

import logging
from typing import Optional

from apps.common.events.event_bus import Event, get_event_bus
from apps.tournament_ops.dtos import (
    MatchResultSubmissionDTO,
    ResultVerificationResultDTO,
    MatchDTO,
)
from apps.tournament_ops.adapters import (
    ResultSubmissionAdapterProtocol,
    DisputeAdapterProtocol,
    SchemaValidationAdapterProtocol,
)
from apps.tournament_ops.services.match_service import MatchService
from apps.tournament_ops.exceptions import (
    SubmissionError,
    InvalidSubmissionStateError,
)

logger = logging.getLogger(__name__)


class ResultVerificationFailedError(Exception):
    """Raised when result verification fails (invalid schema/scores)."""
    pass


class ResultVerificationService:
    """
    Validates and finalizes match results.
    
    Responsibilities:
    - Verify submission against game schema
    - Calculate scores using GameRulesEngine
    - Finalize results into Match domain via MatchService
    - Log all verification steps to audit trail
    - Publish verification events
    
    Dependencies (constructor injection):
    - result_submission_adapter: Access to submissions
    - dispute_adapter: Logging verification steps
    - schema_validation_adapter: Schema validation & scoring
    - match_service: Match finalization
    - game_adapter: Fetch game_slug for matches
    
    Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4, ResultVerificationService
    """
    
    def __init__(
        self,
        result_submission_adapter: ResultSubmissionAdapterProtocol,
        dispute_adapter: DisputeAdapterProtocol,
        schema_validation_adapter: SchemaValidationAdapterProtocol,
        match_service: MatchService,
    ):
        self.result_submission_adapter = result_submission_adapter
        self.dispute_adapter = dispute_adapter
        self.schema_validation_adapter = schema_validation_adapter
        self.match_service = match_service
        self.event_bus = get_event_bus()
    
    def verify_submission(self, submission_id: int) -> ResultVerificationResultDTO:
        """
        Verify submission against game schema and business rules.
        
        Workflow:
        1. Load MatchResultSubmissionDTO
        2. Determine game_slug for the match
        3. Validate payload using SchemaValidationAdapter
        4. Log verification step
        5. Publish MatchResultVerifiedEvent
        6. Return ResultVerificationResultDTO
        
        This method does NOT change submission state - read-only verification.
        
        Args:
            submission_id: Submission ID to verify
            
        Returns:
            ResultVerificationResultDTO with is_valid, errors, warnings, calculated_scores
            
        Raises:
            SubmissionError: If submission not found
            
        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4, verify_submission
        """
        # Load submission
        submission = self.result_submission_adapter.get_submission(submission_id)
        
        # Get game_slug for match
        game_slug = self._get_game_slug_for_submission(submission)
        
        # Validate payload
        verification_result = self.schema_validation_adapter.validate_payload(
            game_slug=game_slug,
            payload=submission.raw_result_payload,
        )
        
        # Validate the DTO itself
        is_dto_valid, dto_errors = verification_result.validate()
        if not is_dto_valid:
            logger.error(f"ResultVerificationResultDTO validation failed for submission {submission_id}: {dto_errors}")
        
        # Log verification step
        self.dispute_adapter.log_verification_step(
            submission_id=submission_id,
            step='auto_verification',
            status='success' if verification_result.is_valid else 'failure',
            details={
                'is_valid': verification_result.is_valid,
                'errors': verification_result.errors,
                'warnings': verification_result.warnings,
                'calculated_scores': verification_result.calculated_scores,
                'metadata': verification_result.metadata,
            },
            performed_by_user_id=None,  # Automated verification
        )
        
        # Publish MatchResultVerifiedEvent
        self.event_bus.publish(Event(
            name='MatchResultVerifiedEvent',
            payload={
                'submission_id': submission_id,
                'match_id': submission.match_id,
                'is_valid': verification_result.is_valid,
                'errors_count': len(verification_result.errors),
                'warnings_count': len(verification_result.warnings),
                'game_slug': game_slug,
            },
            metadata={
                'validation_method': verification_result.metadata.get('validation_method'),
                'has_calculated_scores': verification_result.calculated_scores is not None,
            }
        ))
        
        return verification_result
    
    def finalize_submission_after_verification(
        self,
        submission_id: int,
        resolved_by_user_id: int,
    ) -> MatchResultSubmissionDTO:
        """
        Finalize submission after full verification pipeline.
        
        This is the core Epic 6.4 method that ties everything together.
        
        Workflow:
        1. Load submission
        2. Call verify_submission() and inspect result
        3. If invalid, raise ResultVerificationFailedError
        4. If valid:
           a. Extract calculated_scores (winner_team_id, loser_team_id, scores)
           b. Call MatchService.accept_match_result() to update Match domain
           c. Update submission status to 'finalized'
           d. Resolve any open disputes (mark as resolved_for_submitter or resolved_for_opponent)
           e. Log finalization step
           f. Publish MatchResultFinalizedEvent with verification context
        
        Args:
            submission_id: Submission ID to finalize
            resolved_by_user_id: User ID performing finalization (organizer)
            
        Returns:
            MatchResultSubmissionDTO (finalized)
            
        Raises:
            SubmissionError: If submission not found
            ResultVerificationFailedError: If verification fails
            InvalidSubmissionStateError: If submission not in valid state
            
        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4, finalize_result
        """
        # Load submission
        submission = self.result_submission_adapter.get_submission(submission_id)
        
        # Validate state (must be confirmed, auto_confirmed, or disputed)
        valid_states = ['confirmed', 'auto_confirmed', 'disputed']
        if submission.status not in valid_states:
            raise InvalidSubmissionStateError(
                f"Cannot finalize submission {submission_id} with status {submission.status}. "
                f"Must be one of: {valid_states}"
            )
        
        # Verify submission
        verification_result = self.verify_submission(submission_id)
        
        # If invalid, raise error
        if not verification_result.is_valid:
            raise ResultVerificationFailedError(
                f"Submission {submission_id} failed verification: {verification_result.errors}"
            )
        
        # Extract calculated scores
        if not verification_result.calculated_scores:
            raise ResultVerificationFailedError(
                f"Submission {submission_id} verification succeeded but no calculated_scores found"
            )
        
        calculated_scores = verification_result.calculated_scores
        winner_team_id = calculated_scores.get('winner_team_id')
        loser_team_id = calculated_scores.get('loser_team_id')
        
        if not winner_team_id or not loser_team_id:
            raise ResultVerificationFailedError(
                f"Submission {submission_id} missing winner_team_id or loser_team_id in calculated_scores"
            )
        
        # Apply scores to match via MatchService
        self._apply_final_scores_to_match(
            match_id=submission.match_id,
            winner_team_id=winner_team_id,
            loser_team_id=loser_team_id,
            result_payload=submission.raw_result_payload,
            calculated_scores=calculated_scores,
        )
        
        # Update submission status to finalized
        submission = self.result_submission_adapter.update_submission_status(
            submission_id=submission_id,
            status='finalized',
        )
        
        # Resolve any open dispute
        dispute_resolved = self._resolve_any_dispute_for_submission(
            submission_id=submission_id,
            winner_team_id=winner_team_id,
            resolved_by_user_id=resolved_by_user_id,
        )
        
        # Log finalization step
        self.dispute_adapter.log_verification_step(
            submission_id=submission_id,
            step='finalization',
            status='success',
            details={
                'winner_team_id': winner_team_id,
                'loser_team_id': loser_team_id,
                'calculated_scores': calculated_scores,
                'resolved_by_user_id': resolved_by_user_id,
                'dispute_resolved': dispute_resolved is not None,
            },
            performed_by_user_id=resolved_by_user_id,
        )
        
        # Publish MatchResultFinalizedEvent with verification context
        self.event_bus.publish(Event(
            name='MatchResultFinalizedEvent',
            payload={
                'submission_id': submission_id,
                'match_id': submission.match_id,
                'winner_team_id': winner_team_id,
                'loser_team_id': loser_team_id,
                'resolved_by_user_id': resolved_by_user_id,
            },
            metadata={
                'calculated_scores': calculated_scores,
                'verification_warnings_count': len(verification_result.warnings),
                'verification_metadata': verification_result.metadata,
                'dispute_resolved': dispute_resolved is not None,
            }
        ))
        
        return submission
    
    def dry_run_verification(self, submission_id: int) -> ResultVerificationResultDTO:
        """
        Perform verification without changing state (dry run).
        
        Useful for:
        - Frontend preview of verification results
        - Admin tooling to check submissions before finalizing
        - Testing verification logic
        
        Workflow:
        1. Load submission
        2. Get game_slug
        3. Validate payload
        4. Return result WITHOUT logging or publishing events
        
        Args:
            submission_id: Submission ID to verify
            
        Returns:
            ResultVerificationResultDTO
            
        Raises:
            SubmissionError: If submission not found
            
        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4, dry_run_verification
        """
        # Load submission
        submission = self.result_submission_adapter.get_submission(submission_id)
        
        # Get game_slug
        game_slug = self._get_game_slug_for_submission(submission)
        
        # Validate payload (no logging, no events)
        verification_result = self.schema_validation_adapter.validate_payload(
            game_slug=game_slug,
            payload=submission.raw_result_payload,
        )
        
        return verification_result
    
    # Internal helpers
    
    def _get_game_slug_for_submission(self, submission: MatchResultSubmissionDTO) -> str:
        """
        Get game_slug for a submission's match.
        
        Navigates: Submission → Match → Tournament → Game
        
        Args:
            submission: MatchResultSubmissionDTO
            
        Returns:
            game_slug (e.g., 'valorant')
            
        Raises:
            SubmissionError: If game not found
        """
        try:
            # Get match via MatchService
            match_dto = self.match_service.get_match(submission.match_id)
            
            # Get tournament via match (requires adapter or direct call)
            # For now, use method-level import to fetch tournament
            from apps.tournaments.models import Match, Tournament
            
            match_obj = Match.objects.select_related('tournament__game').get(id=submission.match_id)
            tournament = match_obj.tournament
            
            if not tournament or not tournament.game:
                raise SubmissionError(f"Match {submission.match_id} has no associated game")
            
            return tournament.game.slug
        except Exception as e:
            logger.error(f"Error getting game_slug for submission {submission.id}: {e}")
            raise SubmissionError(f"Could not determine game for submission {submission.id}") from e
    
    def _apply_final_scores_to_match(
        self,
        match_id: int,
        winner_team_id: int,
        loser_team_id: int,
        result_payload: dict,
        calculated_scores: dict,
    ) -> MatchDTO:
        """
        Apply final scores to match via MatchService.
        
        Calls MatchService.accept_match_result() (Phase 4 integration).
        
        Args:
            match_id: Match ID
            winner_team_id: Winner team ID
            loser_team_id: Loser team ID
            result_payload: Raw result payload
            calculated_scores: Calculated scores from verification
            
        Returns:
            MatchDTO (updated)
            
        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4, MatchService integration
        """
        # Call MatchService to finalize match
        # MatchService.accept_match_result() handles:
        # - Updating Match.winner_team, Match.loser_team
        # - Updating Match.result (JSON payload)
        # - Updating Match.status to 'completed'
        # - Publishing MatchCompletedEvent (for bracket progression)
        
        try:
            match_dto = self.match_service.accept_match_result(
                match_id=match_id,
                winner_team_id=winner_team_id,
                loser_team_id=loser_team_id,
                result_payload=result_payload,
                metadata={
                    'source': 'result_verification_service',
                    'calculated_scores': calculated_scores,
                }
            )
            
            logger.info(f"Match {match_id} finalized with winner {winner_team_id}, loser {loser_team_id}")
            return match_dto
        except Exception as e:
            logger.error(f"Error finalizing match {match_id}: {e}")
            raise SubmissionError(f"Failed to finalize match {match_id}") from e
    
    def _resolve_any_dispute_for_submission(
        self,
        submission_id: int,
        winner_team_id: int,
        resolved_by_user_id: int,
    ) -> Optional[any]:
        """
        Resolve any open dispute for submission based on finalization outcome.
        
        Resolution logic:
        - If submitter's team_id == winner_team_id: resolved_for_submitter
        - Otherwise: resolved_for_opponent
        
        Args:
            submission_id: Submission ID
            winner_team_id: Winner team ID from verification
            resolved_by_user_id: User performing resolution
            
        Returns:
            DisputeDTO if dispute was resolved, None otherwise
            
        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4, dispute resolution
        """
        # Check for open dispute
        dispute = self.dispute_adapter.get_open_dispute_for_submission(submission_id)
        
        if not dispute:
            return None
        
        # Get submission to determine submitter's team
        submission = self.result_submission_adapter.get_submission(submission_id)
        
        # Determine resolution outcome
        if submission.submitted_by_team_id == winner_team_id:
            # Submitter won
            resolution_status = 'resolved_for_submitter'
            resolution_notes = 'Verification confirmed submitter result (submitter wins)'
        else:
            # Opponent won (or no team affiliation)
            resolution_status = 'resolved_for_opponent'
            resolution_notes = 'Verification confirmed opponent result (opponent wins)'
        
        # Update dispute
        resolved_dispute = self.dispute_adapter.update_dispute_status(
            dispute_id=dispute.id,
            status=resolution_status,
            resolved_by_user_id=resolved_by_user_id,
            resolution_notes=resolution_notes,
        )
        
        # Publish DisputeResolvedEvent
        self.event_bus.publish(Event(
            name='DisputeResolvedEvent',
            payload={
                'dispute_id': dispute.id,
                'submission_id': submission_id,
                'resolution': 'submitter_wins' if resolution_status == 'resolved_for_submitter' else 'opponent_wins',
                'dispute_status': resolution_status,
                'submission_status': 'finalized',
                'resolved_by_user_id': resolved_by_user_id,
            },
            metadata={
                'resolution_notes': resolution_notes,
                'resolved_at': resolved_dispute.resolved_at.isoformat() if resolved_dispute.resolved_at else None,
                'winner_team_id': winner_team_id,
            }
        ))
        
        return resolved_dispute
