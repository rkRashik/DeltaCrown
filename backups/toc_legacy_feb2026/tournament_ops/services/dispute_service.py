"""
Dispute Service - Phase 6, Epic 6.2 & Epic 6.5

Orchestrates dispute workflow: escalation, resolution, evidence management.

Updated in Epic 6.4: Integrated with ResultVerificationService for finalization.
Updated in Epic 6.5: Comprehensive resolution module with 4 resolution types and notifications.

Workflow:
1. Dispute opened via ResultSubmissionService.opponent_response()
2. Optional: organizer escalates dispute → ESCALATED
3. Epic 6.5: Organizer resolves dispute with 4 resolution types:
   - approve_original: Original submission correct, finalize with original payload
   - approve_dispute: Disputer correct, finalize with disputed payload
   - custom_result: Neither correct, finalize with custom organizer payload
   - dismiss_dispute: Invalid dispute, restart 24-hour timer (no finalization)

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.2 (Opponent Verification & Dispute System)
          PHASE6_WORKPLAN_DRAFT.md - Epic 6.4 (Verification Integration)
          PHASE6_WORKPLAN_DRAFT.md - Epic 6.5 (Dispute Resolution Module)
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta

from apps.common.events.event_bus import Event, get_event_bus
from apps.tournament_ops.dtos import (
    DisputeDTO,
    DisputeEvidenceDTO,
    MatchResultSubmissionDTO,
    DisputeResolutionDTO,
    RESOLUTION_TYPE_APPROVE_ORIGINAL,
    RESOLUTION_TYPE_APPROVE_DISPUTE,
    RESOLUTION_TYPE_CUSTOM_RESULT,
    RESOLUTION_TYPE_DISMISS_DISPUTE,
)
from apps.tournament_ops.adapters import (
    DisputeAdapterProtocol,
    ResultSubmissionAdapterProtocol,
)
from apps.tournament_ops.exceptions import (
    DisputeError,
    DisputeNotFoundError,
    InvalidDisputeStateError,
    DisputeAlreadyResolvedError,
)

# Avoid circular import
if TYPE_CHECKING:
    from apps.tournament_ops.services.result_verification_service import ResultVerificationService
    from apps.tournament_ops.adapters.notification_adapter import NotificationAdapterProtocol


class DisputeService:
    """
    Orchestrates dispute escalation, resolution, and evidence management.
    
    Dependencies (constructor injection):
    - dispute_adapter: Access to dispute domain
    - result_submission_adapter: Update submission status based on resolution
    - result_verification_service: (Epic 6.4) Full verification pipeline for finalization
    - notification_adapter: (Epic 6.5) Send notifications on key transitions
    
    Reference: Phase 6, Epic 6.2 - Dispute Service
              Phase 6, Epic 6.4 - Verification Integration
              Phase 6, Epic 6.5 - Dispute Resolution Module with Notifications
    """
    
    def __init__(
        self,
        dispute_adapter: DisputeAdapterProtocol,
        result_submission_adapter: ResultSubmissionAdapterProtocol,
        result_verification_service: Optional["ResultVerificationService"] = None,
        notification_adapter: Optional["NotificationAdapterProtocol"] = None,
    ):
        self.dispute_adapter = dispute_adapter
        self.result_submission_adapter = result_submission_adapter
        self.result_verification_service = result_verification_service
        self.notification_adapter = notification_adapter
    
    def escalate_dispute(
        self,
        dispute_id: int,
        escalated_by_user_id: int,
    ) -> DisputeDTO:
        """
        Escalate a dispute to higher-tier support.
        
        Workflow:
        1. Get dispute
        2. Validate dispute is open (not already resolved)
        3. Update status to 'escalated'
        4. Set escalated_at timestamp
        5. Log verification step
        6. Publish DisputeEscalatedEvent
        
        Args:
            dispute_id: Dispute ID
            escalated_by_user_id: User escalating (organizer/admin)
            
        Returns:
            Updated DisputeDTO
            
        Raises:
            DisputeNotFoundError: Dispute not found
            InvalidDisputeStateError: Dispute already resolved
            
        Reference: Phase 6, Epic 6.2 - Dispute Escalation
        """
        # Get dispute
        dispute = self.dispute_adapter.get_dispute(dispute_id)
        
        # Validate not already resolved
        if dispute.is_resolved():
            raise InvalidDisputeStateError(
                f"Cannot escalate resolved dispute {dispute_id} (status: {dispute.status})"
            )
        
        # Update status to escalated
        dispute = self.dispute_adapter.update_dispute_status(
            dispute_id=dispute_id,
            status='escalated',
        )
        
        # Log verification step
        self.dispute_adapter.log_verification_step(
            submission_id=dispute.submission_id,
            step='dispute_escalated',
            status='success',
            details={
                'dispute_id': dispute_id,
                'escalated_by_user_id': escalated_by_user_id,
            },
            performed_by_user_id=escalated_by_user_id,
        )
        
        # Publish event
        get_event_bus().publish(Event(
            name='DisputeEscalatedEvent',
            payload={
                'dispute_id': dispute_id,
                'submission_id': dispute.submission_id,
                'escalated_by_user_id': escalated_by_user_id,
                'reason_code': dispute.reason_code,
            },
            metadata={
                'escalated_at': dispute.escalated_at.isoformat() if dispute.escalated_at else None,
            }
        ))
        
        return dispute
    
    def resolve_dispute(
        self,
        submission_id: int,
        dispute_id: int,
        resolution_type: str,
        resolved_by_user_id: int,
        resolution_notes: str = "",
        custom_result_payload: Optional[Dict[str, Any]] = None,
    ) -> DisputeDTO:
        """
        Resolve a dispute with organizer decision (Epic 6.5 - 4 resolution types).
        
        Updated from Epic 6.2/6.4 to support full resolution module with:
        - 4 resolution types (approve_original, approve_dispute, custom_result, dismiss_dispute)
        - NotificationAdapter integration
        - ResultVerificationLog audit trail
        - Enhanced event publishing
        
        Workflow:
        1. Load MatchResultSubmissionDTO & DisputeDTO
        2. Validate dispute is still open
        3. Create DisputeResolutionDTO and validate
        4. Execute resolution based on type:
           a. approve_original: Use original payload, finalize via ResultVerificationService
           b. approve_dispute: Use disputed payload, finalize via ResultVerificationService
           c. custom_result: Use custom payload, finalize via ResultVerificationService
           d. dismiss_dispute: No finalization, restart 24h timer
        5. Update dispute status
        6. Close related open disputes for this submission (if applicable)
        7. Log resolution to ResultVerificationLog
        8. Call NotificationAdapter.notify_dispute_resolved
        9. Publish DisputeResolvedEvent with enhanced payload
        
        Args:
            submission_id: Match result submission ID
            dispute_id: Dispute record ID
            resolution_type: Type of resolution (approve_original, approve_dispute, custom_result, dismiss_dispute)
            resolved_by_user_id: Organizer/admin user ID
            resolution_notes: Organizer's notes/reasoning
            custom_result_payload: Custom result data (required for custom_result type)
            
        Returns:
            Updated DisputeDTO
            
        Raises:
            DisputeNotFoundError: Dispute not found
            DisputeAlreadyResolvedError: Dispute already resolved
            ValueError: Invalid resolution_type or validation failed
            ResultVerificationFailedError: Verification fails (from ResultVerificationService)
            
        Reference: Phase 6, Epic 6.5 - Dispute Resolution Module
        """
        # 1. Load submission and dispute
        submission = self.result_submission_adapter.get_submission(submission_id)
        dispute = self.dispute_adapter.get_dispute(dispute_id)
        
        # 2. Validate dispute is still open
        if dispute.is_resolved():
            raise DisputeAlreadyResolvedError(
                f"Dispute {dispute_id} already resolved (status: {dispute.status})"
            )
        
        # 3. Create and validate resolution DTO
        resolution_dto = DisputeResolutionDTO(
            submission_id=submission_id,
            dispute_id=dispute_id,
            resolution_type=resolution_type,
            resolved_by_user_id=resolved_by_user_id,
            resolution_notes=resolution_notes,
            custom_result_payload=custom_result_payload,
            created_at=datetime.now(),
        )
        resolution_dto.validate()
        
        # 4. Execute resolution based on type
        if resolution_dto.is_approve_original():
            self._resolve_approve_original(submission, dispute, resolution_dto)
        elif resolution_dto.is_approve_dispute():
            self._resolve_approve_dispute(submission, dispute, resolution_dto)
        elif resolution_dto.is_custom_result():
            self._resolve_custom_result(submission, dispute, resolution_dto)
        elif resolution_dto.is_dismiss_dispute():
            self._resolve_dismiss_dispute(submission, dispute, resolution_dto)
        else:
            # This should never happen due to DTO validation, but defensive check
            raise ValueError(f"Unhandled resolution_type: {resolution_type}")
        
        # Get updated dispute (adapter updated status during resolution)
        dispute = self.dispute_adapter.get_dispute(dispute_id)
        
        # Re-fetch submission to get updated state
        submission = self.result_submission_adapter.get_submission(submission_id)
        
        # 7. Log resolution to ResultVerificationLog
        self.dispute_adapter.log_verification_step(
            submission_id=submission_id,
            step='organizer_review',
            status='success',
            details={
                'dispute_id': dispute_id,
                'resolution_type': resolution_type,
                'resolution_notes': resolution_notes,
                'resolved_by_user_id': resolved_by_user_id,
                'used_payload_type': self._get_payload_type_description(resolution_dto),
                'dispute_status': dispute.status,
                'submission_status': submission.status,
            },
            performed_by_user_id=resolved_by_user_id,
        )
        
        # 8. Call NotificationAdapter.notify_dispute_resolved
        if self.notification_adapter:
            self.notification_adapter.notify_dispute_resolved(
                dispute_dto=dispute,
                submission_dto=submission,
                resolution_dto=resolution_dto,
            )
        
        # 9. Publish DisputeResolvedEvent with enhanced payload
        get_event_bus().publish(Event(
            name='DisputeResolvedEvent',
            payload={
                'dispute_id': dispute_id,
                'submission_id': submission_id,
                'resolution_type': resolution_type,
                'dispute_status': dispute.status,
                'submission_status': submission.status,
                'resolved_by_user_id': resolved_by_user_id,
                'requires_finalization': resolution_dto.requires_finalization(),
            },
            metadata={
                'resolution_notes': resolution_notes,
                'resolved_at': dispute.resolved_at.isoformat() if dispute.resolved_at else None,
                'custom_result_applied': resolution_dto.is_custom_result(),
            }
        ))
        
        return dispute
    
    def _resolve_approve_original(
        self,
        submission: MatchResultSubmissionDTO,
        dispute: DisputeDTO,
        resolution_dto: DisputeResolutionDTO,
    ) -> None:
        """
        Resolve by approving original submission.
        
        Workflow:
        1. Keep original submission payload (no update needed)
        2. Call ResultVerificationService.finalize_submission_after_verification
        3. Mark dispute as resolved_for_submitter
        4. Close any other open disputes for this submission
        """
        # Finalize with original payload via ResultVerificationService
        if self.result_verification_service:
            self.result_verification_service.finalize_submission_after_verification(
                submission_id=submission.id,
                resolved_by_user_id=resolution_dto.resolved_by_user_id,
            )
        else:
            # Fallback: Just update status (legacy path)
            self.result_submission_adapter.update_submission_status(
                submission_id=submission.id,
                status='finalized',
            )
        
        # Mark dispute as resolved for submitter
        self.dispute_adapter.update_dispute_status(
            dispute_id=dispute.id,
            status='resolved_for_submitter',
            resolved_by_user_id=resolution_dto.resolved_by_user_id,
            resolution_notes=resolution_dto.resolution_notes,
        )
        
        # Close any other open disputes for this submission
        self._close_related_disputes(submission.id, dispute.id)
    
    def _resolve_approve_dispute(
        self,
        submission: MatchResultSubmissionDTO,
        dispute: DisputeDTO,
        resolution_dto: DisputeResolutionDTO,
    ) -> None:
        """
        Resolve by approving disputed result.
        
        Workflow:
        1. Update submission payload to disputed payload
        2. Call ResultVerificationService.finalize_submission_after_verification
        3. Mark dispute as resolved_for_opponent
        4. Close any other open disputes for this submission
        """
        # Get disputed payload from dispute
        disputed_payload = dispute.disputed_result_payload
        if not disputed_payload:
            raise DisputeError(
                f"Dispute {dispute.id} has no disputed_result_payload, cannot approve dispute"
            )
        
        # Update submission payload to disputed version
        self.result_submission_adapter.update_submission_payload(
            submission_id=submission.id,
            raw_result_payload=disputed_payload,
        )
        
        # Finalize with disputed payload via ResultVerificationService
        if self.result_verification_service:
            self.result_verification_service.finalize_submission_after_verification(
                submission_id=submission.id,
                resolved_by_user_id=resolution_dto.resolved_by_user_id,
            )
        else:
            # Fallback: Just update status (legacy path)
            self.result_submission_adapter.update_submission_status(
                submission_id=submission.id,
                status='finalized',
            )
        
        # Mark dispute as resolved for opponent
        self.dispute_adapter.update_dispute_status(
            dispute_id=dispute.id,
            status='resolved_for_opponent',
            resolved_by_user_id=resolution_dto.resolved_by_user_id,
            resolution_notes=resolution_dto.resolution_notes,
        )
        
        # Close any other open disputes for this submission
        self._close_related_disputes(submission.id, dispute.id)
    
    def _resolve_custom_result(
        self,
        submission: MatchResultSubmissionDTO,
        dispute: DisputeDTO,
        resolution_dto: DisputeResolutionDTO,
    ) -> None:
        """
        Resolve with custom organizer result.
        
        Workflow:
        1. Update submission payload to custom payload
        2. Call ResultVerificationService.finalize_submission_after_verification
        3. Mark dispute as resolved_custom
        4. Close any other open disputes for this submission
        """
        # Update submission payload to custom version
        self.result_submission_adapter.update_submission_payload(
            submission_id=submission.id,
            raw_result_payload=resolution_dto.custom_result_payload,
        )
        
        # Finalize with custom payload via ResultVerificationService
        if self.result_verification_service:
            self.result_verification_service.finalize_submission_after_verification(
                submission_id=submission.id,
                resolved_by_user_id=resolution_dto.resolved_by_user_id,
            )
        else:
            # Fallback: Just update status (legacy path)
            self.result_submission_adapter.update_submission_status(
                submission_id=submission.id,
                status='finalized',
            )
        
        # Mark dispute as resolved with custom result
        self.dispute_adapter.update_dispute_status(
            dispute_id=dispute.id,
            status='resolved_custom',
            resolved_by_user_id=resolution_dto.resolved_by_user_id,
            resolution_notes=resolution_dto.resolution_notes,
        )
        
        # Close any other open disputes for this submission
        self._close_related_disputes(submission.id, dispute.id)
    
    def _resolve_dismiss_dispute(
        self,
        submission: MatchResultSubmissionDTO,
        dispute: DisputeDTO,
        resolution_dto: DisputeResolutionDTO,
    ) -> None:
        """
        Dismiss dispute as invalid, restart 24-hour timer.
        
        Workflow:
        1. Mark dispute as dismissed
        2. Do NOT finalize submission
        3. Restart 24-hour timer (update auto_confirm_deadline)
        4. Optionally schedule new Celery auto-confirm task
        """
        # Mark dispute as dismissed
        self.dispute_adapter.update_dispute_status(
            dispute_id=dispute.id,
            status='dismissed',
            resolved_by_user_id=resolution_dto.resolved_by_user_id,
            resolution_notes=resolution_dto.resolution_notes,
        )
        
        # Restart 24-hour timer
        # Method-level import to avoid circular dependency
        from django.utils import timezone
        new_deadline = timezone.now() + timedelta(hours=24)
        
        self.result_submission_adapter.update_auto_confirm_deadline(
            submission_id=submission.id,
            auto_confirm_deadline=new_deadline,
        )
        
        # Revert submission to pending status (allow opponent to re-confirm)
        self.result_submission_adapter.update_submission_status(
            submission_id=submission.id,
            status='pending',
        )
        
        # Optional: Schedule new Celery auto-confirm task
        # TODO (Epic 6.5): Integrate with Celery task scheduling
        # self._schedule_auto_confirm_task(submission.id, new_deadline)
    
    def _close_related_disputes(self, submission_id: int, current_dispute_id: int) -> None:
        """
        Close any other open disputes for this submission.
        
        When one dispute is resolved with finalization, any other open disputes
        for the same submission should be auto-closed.
        
        Args:
            submission_id: Submission ID
            current_dispute_id: Current dispute being resolved (skip this one)
        """
        # Get all open disputes for this submission
        try:
            open_dispute = self.dispute_adapter.get_open_dispute_for_submission(submission_id)
            if open_dispute and open_dispute.id != current_dispute_id:
                # Close it as auto-resolved
                self.dispute_adapter.update_dispute_status(
                    dispute_id=open_dispute.id,
                    status='auto_resolved',
                    resolved_by_user_id=None,
                    resolution_notes='Auto-closed due to resolution of another dispute for same submission',
                )
        except DisputeNotFoundError:
            # No other open disputes, that's fine
            pass
    
    def _get_payload_type_description(self, resolution_dto: DisputeResolutionDTO) -> str:
        """Get human-readable description of payload type used."""
        if resolution_dto.is_approve_original():
            return "original"
        elif resolution_dto.is_approve_dispute():
            return "dispute"
        elif resolution_dto.is_custom_result():
            return "custom"
        elif resolution_dto.is_dismiss_dispute():
            return "none (dismissed)"
        else:
            return "unknown"
    
    def resolve_dispute_legacy(
        self,
        dispute_id: int,
        resolved_by_user_id: int,
        resolution: str,
        resolution_notes: str = "",
    ) -> DisputeDTO:
        """
        DEPRECATED: Legacy resolve_dispute from Epic 6.2/6.4.
        
        Kept for backward compatibility. Use new resolve_dispute() with resolution_type instead.
        
        Maps old resolution values to new resolution types:
        - "submitter_wins" → "approve_original"
        - "opponent_wins" → "approve_dispute"
        - "cancelled" → "dismiss_dispute"
        """
        # Map legacy resolution to new resolution_type
        resolution_type_map = {
            'submitter_wins': RESOLUTION_TYPE_APPROVE_ORIGINAL,
            'opponent_wins': RESOLUTION_TYPE_APPROVE_DISPUTE,
            'cancelled': RESOLUTION_TYPE_DISMISS_DISPUTE,
        }
        
        if resolution not in resolution_type_map:
            raise DisputeError(
                f"Invalid legacy resolution: {resolution}. Must be one of {list(resolution_type_map.keys())}"
            )
        
        resolution_type = resolution_type_map[resolution]
        
        # Get dispute to get submission_id
        dispute = self.dispute_adapter.get_dispute(dispute_id)
        
        # Call new resolve_dispute
        return self.resolve_dispute(
            submission_id=dispute.submission_id,
            dispute_id=dispute_id,
            resolution_type=resolution_type,
            resolved_by_user_id=resolved_by_user_id,
            resolution_notes=resolution_notes,
            custom_result_payload=None,
        )
    
    def add_evidence(
        self,
        dispute_id: int,
        uploaded_by_user_id: int,
        evidence_type: str,
        url: str,
        notes: str = "",
    ) -> DisputeEvidenceDTO:
        """
        Add evidence to a dispute.
        
        Thin wrapper over DisputeAdapter.add_evidence.
        Logs the action for audit trail.
        
        Args:
            dispute_id: Dispute ID
            uploaded_by_user_id: User uploading evidence
            evidence_type: Type (screenshot, video, chat_log, other)
            url: URL to resource
            notes: Additional context
            
        Returns:
            DisputeEvidenceDTO
            
        Raises:
            DisputeNotFoundError: Dispute not found
            DisputeError: Creation failed
            
        Reference: Phase 6, Epic 6.2 - Evidence Management
        """
        # Add evidence via adapter
        evidence = self.dispute_adapter.add_evidence(
            dispute_id=dispute_id,
            uploaded_by_user_id=uploaded_by_user_id,
            evidence_type=evidence_type,
            url=url,
            notes=notes,
        )
        
        # Get dispute to get submission_id for logging
        dispute = self.dispute_adapter.get_dispute(dispute_id)
        
        # Log action (not a verification step, just informational)
        # We could create a separate AuditLog table for this in Epic 6.3/6.4
        # For now, no explicit logging (evidence creation is auditable via created_at)
        
        return evidence
    
    def open_dispute_from_submission(
        self,
        submission_id: int,
        opened_by_user_id: int,
        opened_by_team_id: Optional[int],
        reason_code: str,
        description: str,
        evidence: Optional[list] = None,
    ) -> DisputeDTO:
        """
        Open a dispute for a submission.
        
        This is a helper method that can be called directly (e.g., from admin UI)
        or indirectly via ResultSubmissionService.opponent_response.
        
        Args:
            submission_id: MatchResultSubmission ID
            opened_by_user_id: User opening dispute
            opened_by_team_id: Team ID (if team tournament)
            reason_code: Categorized reason
            description: Detailed description
            evidence: Optional list of evidence dicts [{type, url, notes}]
            
        Returns:
            DisputeDTO
            
        Raises:
            DisputeError: Creation failed
            
        Reference: Phase 6, Epic 6.2 - Dispute Creation
        """
        # Check if there's already an open dispute for this submission
        existing_dispute = self.dispute_adapter.get_open_dispute_for_submission(submission_id)
        if existing_dispute:
            raise DisputeError(
                f"Submission {submission_id} already has an open dispute {existing_dispute.id}"
            )
        
        # Create dispute
        dispute = self.dispute_adapter.create_dispute(
            submission_id=submission_id,
            opened_by_user_id=opened_by_user_id,
            opened_by_team_id=opened_by_team_id,
            reason_code=reason_code,
            description=description,
        )
        
        # Attach evidence if provided
        if evidence:
            for item in evidence:
                self.dispute_adapter.add_evidence(
                    dispute_id=dispute.id,
                    uploaded_by_user_id=opened_by_user_id,
                    evidence_type=item.get('type', 'other'),
                    url=item.get('url', ''),
                    notes=item.get('notes', ''),
                )
        
        return dispute
