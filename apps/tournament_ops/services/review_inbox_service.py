"""
Review Inbox Service - Phase 6, Epic 6.3 & Epic 6.5

Orchestrates organizer results inbox workflows: listing, filtering, finalization, rejection.

Updated in Epic 6.4: Integrated with ResultVerificationService for full verification pipeline.
Updated in Epic 6.5: Added dispute resolution helper methods for 4 resolution types.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.3 (Organizer Results Inbox) & Epic 6.4 (Verification)
          PHASE6_WORKPLAN_DRAFT.md - Epic 6.5 (Dispute Resolution Module)
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING

from apps.common.events.event_bus import Event, get_event_bus
from apps.tournament_ops.dtos import (
    OrganizerReviewItemDTO,
    MatchResultSubmissionDTO,
    DisputeDTO,
)
from apps.tournament_ops.adapters import (
    ReviewInboxAdapterProtocol,
    DisputeAdapterProtocol,
    ResultSubmissionAdapterProtocol,
)
from apps.tournament_ops.services.match_service import MatchService
from apps.tournament_ops.exceptions import (
    SubmissionError,
    InvalidSubmissionStateError,
)

# Avoid circular import
if TYPE_CHECKING:
    from apps.tournament_ops.services.result_verification_service import ResultVerificationService
    from apps.tournament_ops.services.dispute_service import DisputeService


class ReviewInboxService:
    """
    Orchestrates organizer results inbox workflows.
    
    Responsibilities:
    - List all submissions requiring organizer attention
    - Compute priority for each item
    - Finalize submissions (mark finalized + trigger match completion)
    - Reject submissions (mark rejected + resolve disputes)
    - Epic 6.5: Dispute resolution helpers (4 resolution types)
    - Filter by tournament, stage, priority
    
    Dependencies (constructor injection):
    - review_inbox_adapter: Access to inbox data
    - dispute_adapter: Dispute resolution
    - result_submission_adapter: Submission status updates
    - match_service: Match finalization
    - result_verification_service: (Epic 6.4) Full verification pipeline
    - dispute_service: (Epic 6.5) Dispute resolution workflows
    
    Reference: Phase 6, Epic 6.3 - Review Inbox Service
              Phase 6, Epic 6.4 - Integrated with ResultVerificationService
              Phase 6, Epic 6.5 - Dispute Resolution Helper Methods
    """
    
    def __init__(
        self,
        review_inbox_adapter: ReviewInboxAdapterProtocol,
        dispute_adapter: DisputeAdapterProtocol,
        result_submission_adapter: ResultSubmissionAdapterProtocol,
        match_service: MatchService,
        result_verification_service: Optional["ResultVerificationService"] = None,
        dispute_service: Optional["DisputeService"] = None,
    ):
        self.review_inbox_adapter = review_inbox_adapter
        self.dispute_adapter = dispute_adapter
        self.result_submission_adapter = result_submission_adapter
        self.match_service = match_service
        self.result_verification_service = result_verification_service
        self.dispute_service = dispute_service
        self.event_bus = get_event_bus()
    
    def list_review_items(
        self,
        tournament_id: Optional[int] = None,
        sort_by_priority: bool = True,
    ) -> List[OrganizerReviewItemDTO]:
        """
        List all submissions requiring organizer attention.
        
        Workflow:
        1. Fetch 4 categories:
           - Pending submissions (awaiting opponent response)
           - Disputed submissions (opponent disputed result)
           - Overdue auto-confirm (past deadline)
           - Ready for finalization (confirmed but not finalized)
        2. Create OrganizerReviewItemDTO for each
        3. Compute priority
        4. Sort by priority (desc) and date
        5. Return list
        
        Args:
            tournament_id: Optional tournament filter
            sort_by_priority: If True, sort by priority (desc) then date
            
        Returns:
            List[OrganizerReviewItemDTO]
            
        Reference: Phase 6, Epic 6.3 - List Review Items
        """
        items = []
        
        # Category 1: Pending submissions
        pending = self.review_inbox_adapter.get_pending_submissions(tournament_id)
        for submission in pending:
            item = OrganizerReviewItemDTO.from_submission_and_dispute(submission, None)
            items.append(item)
        
        # Category 2: Disputed submissions
        disputed = self.review_inbox_adapter.get_disputed_submissions(tournament_id)
        for submission, dispute in disputed:
            item = OrganizerReviewItemDTO.from_submission_and_dispute(submission, dispute)
            items.append(item)
        
        # Category 3: Overdue auto-confirm
        overdue = self.review_inbox_adapter.get_overdue_auto_confirm(tournament_id)
        for submission in overdue:
            item = OrganizerReviewItemDTO.from_submission_and_dispute(submission, None)
            items.append(item)
        
        # Category 4: Ready for finalization
        ready = self.review_inbox_adapter.get_ready_for_finalization(tournament_id)
        for submission in ready:
            item = OrganizerReviewItemDTO.from_submission_and_dispute(submission, None)
            items.append(item)
        
        # Sort by priority (desc) and auto_confirm_deadline (asc)
        if sort_by_priority:
            items.sort(key=lambda x: (x.priority, x.auto_confirm_deadline))
        
        return items
    
    def finalize_submission(
        self,
        submission_id: int,
        resolved_by_user_id: int,
    ) -> MatchResultSubmissionDTO:
        """
        Finalize a submission (organizer approval).
        
        Updated in Epic 6.4: Now uses ResultVerificationService for full verification pipeline.
        
        Workflow:
        1. If result_verification_service available:
           - Delegate to ResultVerificationService.finalize_submission_after_verification()
           - This handles verification, match finalization, dispute resolution, events
        2. If not available (backward compatibility):
           - Legacy flow: update status, resolve dispute, log, publish events
        
        Args:
            submission_id: Submission ID
            resolved_by_user_id: Organizer user ID
            
        Returns:
            MatchResultSubmissionDTO (updated)
            
        Raises:
            SubmissionError: If submission not found
            InvalidSubmissionStateError: If submission not in valid state
            ResultVerificationFailedError: If verification fails (Epic 6.4)
            
        Reference: Phase 6, Epic 6.3 - Finalize Submission
                  Phase 6, Epic 6.4 - Integrated with ResultVerificationService
        """
        # Epic 6.4: Use ResultVerificationService if available
        if self.result_verification_service:
            return self.result_verification_service.finalize_submission_after_verification(
                submission_id=submission_id,
                resolved_by_user_id=resolved_by_user_id,
            )
        
        # Legacy flow (backward compatibility for tests without verification service)
        # Get submission
        submission = self.result_submission_adapter.get_submission(submission_id)
        
        # Validate state (must be confirmed or disputed)
        if submission.status not in ('confirmed', 'disputed'):
            raise InvalidSubmissionStateError(
                f"Cannot finalize submission {submission_id} with status {submission.status}. "
                f"Must be 'confirmed' or 'disputed'"
            )
        
        # Check if there's an open dispute
        dispute = self.dispute_adapter.get_open_dispute_for_submission(submission_id)
        
        # Resolve dispute if exists
        if dispute:
            # Update dispute to resolved_for_submitter
            resolved_dispute = self.dispute_adapter.update_dispute_status(
                dispute_id=dispute.id,
                status='resolved_for_submitter',
                resolved_by_user_id=resolved_by_user_id,
                resolution_notes='Organizer finalized submission (submitter wins)',
            )
            
            # Publish DisputeResolvedEvent
            self.event_bus.publish(Event(
                name='DisputeResolvedEvent',
                payload={
                    'dispute_id': dispute.id,
                    'submission_id': submission_id,
                    'resolution': 'submitter_wins',
                    'dispute_status': 'resolved_for_submitter',
                    'submission_status': 'finalized',
                    'resolved_by_user_id': resolved_by_user_id,
                },
                metadata={
                    'resolution_notes': 'Organizer finalized submission (submitter wins)',
                    'resolved_at': resolved_dispute.resolved_at.isoformat() if resolved_dispute.resolved_at else None,
                }
            ))
        
        # Update submission status to finalized
        submission = self.result_submission_adapter.update_submission_status(
            submission_id=submission_id,
            status='finalized',
        )
        
        # Log verification step
        self.dispute_adapter.log_verification_step(
            submission_id=submission_id,
            step='organizer_finalized',
            status='success',
            details={
                'resolved_by_user_id': resolved_by_user_id,
                'dispute_resolved': dispute is not None,
            },
            performed_by_user_id=resolved_by_user_id,
        )
        
        # Publish MatchResultFinalizedEvent
        self.event_bus.publish(Event(
            name='MatchResultFinalizedEvent',
            payload={
                'submission_id': submission_id,
                'match_id': submission.match_id,
                'tournament_id': submission.tournament_id,
                'resolved_by_user_id': resolved_by_user_id,
            },
            metadata={
                'dispute_resolved': dispute is not None,
            }
        ))
        
        return submission
    
    def reject_submission(
        self,
        submission_id: int,
        resolved_by_user_id: int,
        notes: str = "",
    ) -> MatchResultSubmissionDTO:
        """
        Reject a submission (organizer denial).
        
        Workflow:
        1. Get submission
        2. Validate submission is pending, confirmed, or disputed
        3. Update submission status to 'rejected'
        4. If related dispute exists:
           - Update dispute to 'resolved_for_opponent'
           - Publish DisputeResolvedEvent
        5. Publish MatchResultRejectedEvent
        6. Log verification step
        
        Args:
            submission_id: Submission ID
            resolved_by_user_id: Organizer user ID
            notes: Rejection notes
            
        Returns:
            MatchResultSubmissionDTO (updated)
            
        Raises:
            SubmissionError: If submission not found
            InvalidSubmissionStateError: If submission not in valid state
            
        Reference: Phase 6, Epic 6.3 - Reject Submission
        """
        # Get submission
        submission = self.result_submission_adapter.get_submission(submission_id)
        
        # Validate state
        if submission.status not in ('pending', 'confirmed', 'disputed'):
            raise InvalidSubmissionStateError(
                f"Cannot reject submission {submission_id} with status {submission.status}"
            )
        
        # Check if there's an open dispute
        dispute = self.dispute_adapter.get_open_dispute_for_submission(submission_id)
        
        # Resolve dispute if exists
        if dispute:
            # Update dispute to resolved_for_opponent
            resolved_dispute = self.dispute_adapter.update_dispute_status(
                dispute_id=dispute.id,
                status='resolved_for_opponent',
                resolved_by_user_id=resolved_by_user_id,
                resolution_notes=f'Organizer rejected submission (opponent wins): {notes}',
            )
            
            # Publish DisputeResolvedEvent
            self.event_bus.publish(Event(
                name='DisputeResolvedEvent',
                payload={
                    'dispute_id': dispute.id,
                    'submission_id': submission_id,
                    'resolution': 'opponent_wins',
                    'dispute_status': 'resolved_for_opponent',
                    'submission_status': 'rejected',
                    'resolved_by_user_id': resolved_by_user_id,
                },
                metadata={
                    'resolution_notes': f'Organizer rejected submission (opponent wins): {notes}',
                    'resolved_at': resolved_dispute.resolved_at.isoformat() if resolved_dispute.resolved_at else None,
                }
            ))
        
        # Update submission status to rejected
        submission = self.result_submission_adapter.update_submission_status(
            submission_id=submission_id,
            status='rejected',
        )
        
        # Log verification step
        self.dispute_adapter.log_verification_step(
            submission_id=submission_id,
            step='organizer_rejected',
            status='success',
            details={
                'resolved_by_user_id': resolved_by_user_id,
                'notes': notes,
                'dispute_resolved': dispute is not None,
            },
            performed_by_user_id=resolved_by_user_id,
        )
        
        # Publish MatchResultRejectedEvent
        self.event_bus.publish(Event(
            name='MatchResultRejectedEvent',
            payload={
                'submission_id': submission_id,
                'match_id': submission.match_id,
                'tournament_id': submission.tournament_id,
                'resolved_by_user_id': resolved_by_user_id,
                'notes': notes,
            },
            metadata={
                'dispute_resolved': dispute is not None,
            }
        ))
        
        return submission
    
    def list_items_for_stage(
        self,
        stage_id: int,
    ) -> List[OrganizerReviewItemDTO]:
        """
        List review items for a specific stage.
        
        Args:
            stage_id: Stage ID
            
        Returns:
            List[OrganizerReviewItemDTO] filtered by stage_id
            
        Reference: Phase 6, Epic 6.3 - Stage Filter
        """
        # Get all items (no tournament filter)
        all_items = self.list_review_items(tournament_id=None, sort_by_priority=True)
        
        # Filter by stage_id
        stage_items = [item for item in all_items if item.stage_id == stage_id]
        
        return stage_items
    
    # ==============================================================================
    # Epic 6.5: Dispute Resolution Helper Methods
    # ==============================================================================
    
    def resolve_dispute_approve_original(
        self,
        submission_id: int,
        dispute_id: int,
        resolved_by_user_id: int,
        notes: str = "",
    ) -> DisputeDTO:
        """
        Resolve dispute by approving original submission (Epic 6.5).
        
        Thin wrapper around DisputeService.resolve_dispute with resolution_type='approve_original'.
        
        Args:
            submission_id: Submission ID
            dispute_id: Dispute ID
            resolved_by_user_id: Organizer/admin user ID
            notes: Resolution notes
            
        Returns:
            Updated DisputeDTO
            
        Raises:
            ValueError: If dispute_service not initialized
            DisputeAlreadyResolvedError: If dispute already resolved
            
        Reference: Phase 6, Epic 6.5 - Approve Original Resolution
        """
        if not self.dispute_service:
            raise ValueError("DisputeService not initialized")
        
        from apps.tournament_ops.dtos import RESOLUTION_TYPE_APPROVE_ORIGINAL
        
        return self.dispute_service.resolve_dispute(
            submission_id=submission_id,
            dispute_id=dispute_id,
            resolution_type=RESOLUTION_TYPE_APPROVE_ORIGINAL,
            resolved_by_user_id=resolved_by_user_id,
            resolution_notes=notes,
            custom_result_payload=None,
        )
    
    def resolve_dispute_approve_dispute(
        self,
        submission_id: int,
        dispute_id: int,
        resolved_by_user_id: int,
        notes: str = "",
    ) -> DisputeDTO:
        """
        Resolve dispute by approving disputed result (Epic 6.5).
        
        Thin wrapper around DisputeService.resolve_dispute with resolution_type='approve_dispute'.
        
        Args:
            submission_id: Submission ID
            dispute_id: Dispute ID
            resolved_by_user_id: Organizer/admin user ID
            notes: Resolution notes
            
        Returns:
            Updated DisputeDTO
            
        Raises:
            ValueError: If dispute_service not initialized
            DisputeAlreadyResolvedError: If dispute already resolved
            DisputeError: If dispute has no disputed_result_payload
            
        Reference: Phase 6, Epic 6.5 - Approve Dispute Resolution
        """
        if not self.dispute_service:
            raise ValueError("DisputeService not initialized")
        
        from apps.tournament_ops.dtos import RESOLUTION_TYPE_APPROVE_DISPUTE
        
        return self.dispute_service.resolve_dispute(
            submission_id=submission_id,
            dispute_id=dispute_id,
            resolution_type=RESOLUTION_TYPE_APPROVE_DISPUTE,
            resolved_by_user_id=resolved_by_user_id,
            resolution_notes=notes,
            custom_result_payload=None,
        )
    
    def resolve_dispute_custom_result(
        self,
        submission_id: int,
        dispute_id: int,
        resolved_by_user_id: int,
        custom_payload: Dict[str, Any],
        notes: str = "",
    ) -> DisputeDTO:
        """
        Resolve dispute with custom organizer result (Epic 6.5).
        
        Thin wrapper around DisputeService.resolve_dispute with resolution_type='custom_result'.
        
        Args:
            submission_id: Submission ID
            dispute_id: Dispute ID
            resolved_by_user_id: Organizer/admin user ID
            custom_payload: Custom result payload (game-specific)
            notes: Resolution notes
            
        Returns:
            Updated DisputeDTO
            
        Raises:
            ValueError: If dispute_service not initialized or custom_payload missing
            DisputeAlreadyResolvedError: If dispute already resolved
            
        Reference: Phase 6, Epic 6.5 - Custom Result Resolution
        """
        if not self.dispute_service:
            raise ValueError("DisputeService not initialized")
        
        if not custom_payload:
            raise ValueError("custom_payload is required for custom result resolution")
        
        from apps.tournament_ops.dtos import RESOLUTION_TYPE_CUSTOM_RESULT
        
        return self.dispute_service.resolve_dispute(
            submission_id=submission_id,
            dispute_id=dispute_id,
            resolution_type=RESOLUTION_TYPE_CUSTOM_RESULT,
            resolved_by_user_id=resolved_by_user_id,
            resolution_notes=notes,
            custom_result_payload=custom_payload,
        )
    
    def resolve_dispute_dismiss(
        self,
        submission_id: int,
        dispute_id: int,
        resolved_by_user_id: int,
        notes: str = "",
    ) -> DisputeDTO:
        """
        Dismiss dispute as invalid, restart 24-hour timer (Epic 6.5).
        
        Thin wrapper around DisputeService.resolve_dispute with resolution_type='dismiss_dispute'.
        
        Args:
            submission_id: Submission ID
            dispute_id: Dispute ID
            resolved_by_user_id: Organizer/admin user ID
            notes: Resolution notes explaining dismissal
            
        Returns:
            Updated DisputeDTO
            
        Raises:
            ValueError: If dispute_service not initialized
            DisputeAlreadyResolvedError: If dispute already resolved
            
        Reference: Phase 6, Epic 6.5 - Dismiss Dispute Resolution
        """
        if not self.dispute_service:
            raise ValueError("DisputeService not initialized")
        
        from apps.tournament_ops.dtos import RESOLUTION_TYPE_DISMISS_DISPUTE
        
        return self.dispute_service.resolve_dispute(
            submission_id=submission_id,
            dispute_id=dispute_id,
            resolution_type=RESOLUTION_TYPE_DISMISS_DISPUTE,
            resolved_by_user_id=resolved_by_user_id,
            resolution_notes=notes,
            custom_result_payload=None,
        )
