"""
Dispute Adapter - Phase 6, Epic 6.2

Adapter for accessing dispute domain without coupling to Django ORM.
Provides clean interface for DisputeService and ResultSubmissionService.

Reference:
- PHASE6_WORKPLAN_DRAFT.md - Epic 6.2 (Opponent Verification & Dispute System)
- Architecture pattern: Method-level ORM imports, returns DTOs only

Created: December 12, 2025
"""

from typing import Protocol, Optional, List, Dict, Any
from datetime import datetime
from ..dtos import DisputeDTO, DisputeEvidenceDTO
from ..exceptions import DisputeNotFoundError, DisputeError


class DisputeAdapterProtocol(Protocol):
    """
    Protocol for dispute domain access.
    
    Defines the interface for dispute operations without coupling to ORM.
    All methods return DTOs (no model instances).
    
    Reference: Phase 6, Epic 6.2 - Dispute Adapter Interface
    """
    
    def create_dispute(
        self,
        submission_id: int,
        opened_by_user_id: int,
        opened_by_team_id: Optional[int],
        reason_code: str,
        description: str,
    ) -> DisputeDTO:
        """
        Create a new dispute for a result submission.
        
        Args:
            submission_id: ID of the MatchResultSubmission being disputed
            opened_by_user_id: User opening the dispute
            opened_by_team_id: Team ID (if team tournament)
            reason_code: Categorized reason (score_mismatch, wrong_winner, etc.)
            description: Detailed description from opponent
            
        Returns:
            DisputeDTO
            
        Raises:
            DisputeError: If creation fails
        """
        ...
    
    def get_dispute(self, dispute_id: int) -> DisputeDTO:
        """
        Get dispute by ID.
        
        Args:
            dispute_id: Dispute ID
            
        Returns:
            DisputeDTO
            
        Raises:
            DisputeNotFoundError: If dispute not found
        """
        ...
    
    def get_open_dispute_for_submission(
        self,
        submission_id: int
    ) -> Optional[DisputeDTO]:
        """
        Get open dispute for a submission (if any).
        
        Only one open dispute per submission allowed.
        
        Args:
            submission_id: MatchResultSubmission ID
            
        Returns:
            DisputeDTO if found, None otherwise
        """
        ...
    
    def update_dispute_status(
        self,
        dispute_id: int,
        status: str,
        resolved_by_user_id: Optional[int] = None,
        resolution_notes: Optional[str] = None,
    ) -> DisputeDTO:
        """
        Update dispute status and resolution details.
        
        Args:
            dispute_id: Dispute ID
            status: New status (under_review, resolved_*, cancelled, escalated)
            resolved_by_user_id: User making the resolution (optional)
            resolution_notes: Internal notes about resolution (optional)
            
        Returns:
            Updated DisputeDTO
            
        Raises:
            DisputeNotFoundError: If dispute not found
            DisputeError: If update fails
        """
        ...
    
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
        
        Args:
            dispute_id: Dispute ID
            uploaded_by_user_id: User uploading evidence
            evidence_type: Type (screenshot, video, chat_log, other)
            url: URL to resource
            notes: Additional context
            
        Returns:
            DisputeEvidenceDTO
            
        Raises:
            DisputeNotFoundError: If dispute not found
            DisputeError: If creation fails
        """
        ...
    
    def list_evidence(self, dispute_id: int) -> List[DisputeEvidenceDTO]:
        """
        List all evidence for a dispute.
        
        Args:
            dispute_id: Dispute ID
            
        Returns:
            List of DisputeEvidenceDTO (ordered by created_at)
            
        Raises:
            DisputeNotFoundError: If dispute not found
        """
        ...
    
    def log_verification_step(
        self,
        submission_id: int,
        step: str,
        status: str,
        details: Dict[str, Any],
        performed_by_user_id: Optional[int] = None,
    ) -> None:
        """
        Log a verification step to ResultVerificationLog.
        
        Used for audit trail of opponent verification and dispute workflow.
        
        Args:
            submission_id: MatchResultSubmission ID
            step: Step type (opponent_confirm, opponent_dispute, etc.)
            status: success/failure
            details: Step details (dict)
            performed_by_user_id: User who performed step (optional)
            
        Raises:
            DisputeError: If logging fails
        """
        ...


class DisputeAdapter:
    """
    Concrete adapter for dispute domain access.
    
    Uses method-level ORM imports to avoid coupling tournament_ops layer to Django models.
    All public methods return DTOs only.
    
    Reference: Phase 6, Epic 6.2 - Dispute Adapter Implementation
    """
    
    def create_dispute(
        self,
        submission_id: int,
        opened_by_user_id: int,
        opened_by_team_id: Optional[int],
        reason_code: str,
        description: str,
    ) -> DisputeDTO:
        """Create dispute. See protocol docstring."""
        from apps.tournaments.models import DisputeRecord
        from django.utils import timezone
        
        try:
            dispute = DisputeRecord.objects.create(
                submission_id=submission_id,
                opened_by_user_id=opened_by_user_id,
                opened_by_team_id=opened_by_team_id,
                status=DisputeRecord.OPEN,
                reason_code=reason_code,
                description=description,
                resolution_notes='',
                opened_at=timezone.now(),
            )
            return DisputeDTO.from_model(dispute)
        except Exception as e:
            raise DisputeError(f"Failed to create dispute: {e}") from e
    
    def get_dispute(self, dispute_id: int) -> DisputeDTO:
        """Get dispute by ID. See protocol docstring."""
        from apps.tournaments.models import DisputeRecord
        
        try:
            dispute = DisputeRecord.objects.get(id=dispute_id)
            return DisputeDTO.from_model(dispute)
        except DisputeRecord.DoesNotExist:
            raise DisputeNotFoundError(f"Dispute {dispute_id} not found")
    
    def get_open_dispute_for_submission(
        self,
        submission_id: int
    ) -> Optional[DisputeDTO]:
        """Get open dispute for submission. See protocol docstring."""
        from apps.tournaments.models import DisputeRecord
        
        # Open statuses: open, under_review, escalated
        open_statuses = [
            DisputeRecord.OPEN,
            DisputeRecord.UNDER_REVIEW,
            DisputeRecord.ESCALATED,
        ]
        
        dispute = DisputeRecord.objects.filter(
            submission_id=submission_id,
            status__in=open_statuses
        ).first()
        
        if dispute:
            return DisputeDTO.from_model(dispute)
        return None
    
    def update_dispute_status(
        self,
        dispute_id: int,
        status: str,
        resolved_by_user_id: Optional[int] = None,
        resolution_notes: Optional[str] = None,
    ) -> DisputeDTO:
        """Update dispute status. See protocol docstring."""
        from apps.tournaments.models import DisputeRecord
        from django.utils import timezone
        
        try:
            dispute = DisputeRecord.objects.get(id=dispute_id)
        except DisputeRecord.DoesNotExist:
            raise DisputeNotFoundError(f"Dispute {dispute_id} not found")
        
        # Update status
        dispute.status = status
        
        # Set resolved_by if provided
        if resolved_by_user_id is not None:
            dispute.resolved_by_user_id = resolved_by_user_id
        
        # Set resolution_notes if provided
        if resolution_notes is not None:
            dispute.resolution_notes = resolution_notes
        
        # Set timestamps based on status
        resolved_statuses = [
            DisputeRecord.RESOLVED_FOR_SUBMITTER,
            DisputeRecord.RESOLVED_FOR_OPPONENT,
            DisputeRecord.CANCELLED,
        ]
        
        if status in resolved_statuses and not dispute.resolved_at:
            dispute.resolved_at = timezone.now()
        
        if status == DisputeRecord.ESCALATED and not dispute.escalated_at:
            dispute.escalated_at = timezone.now()
        
        try:
            dispute.save()
            return DisputeDTO.from_model(dispute)
        except Exception as e:
            raise DisputeError(f"Failed to update dispute {dispute_id}: {e}") from e
    
    def add_evidence(
        self,
        dispute_id: int,
        uploaded_by_user_id: int,
        evidence_type: str,
        url: str,
        notes: str = "",
    ) -> DisputeEvidenceDTO:
        """Add evidence to dispute. See protocol docstring."""
        from apps.tournaments.models import DisputeEvidence, DisputeRecord
        
        # Verify dispute exists
        if not DisputeRecord.objects.filter(id=dispute_id).exists():
            raise DisputeNotFoundError(f"Dispute {dispute_id} not found")
        
        try:
            evidence = DisputeEvidence.objects.create(
                dispute_id=dispute_id,
                uploaded_by_user_id=uploaded_by_user_id,
                evidence_type=evidence_type,
                url=url,
                notes=notes,
            )
            return DisputeEvidenceDTO.from_model(evidence)
        except Exception as e:
            raise DisputeError(f"Failed to add evidence to dispute {dispute_id}: {e}") from e
    
    def list_evidence(self, dispute_id: int) -> List[DisputeEvidenceDTO]:
        """List evidence for dispute. See protocol docstring."""
        from apps.tournaments.models import DisputeEvidence, DisputeRecord
        
        # Verify dispute exists
        if not DisputeRecord.objects.filter(id=dispute_id).exists():
            raise DisputeNotFoundError(f"Dispute {dispute_id} not found")
        
        evidence_list = DisputeEvidence.objects.filter(
            dispute_id=dispute_id
        ).order_by('created_at')
        
        return [DisputeEvidenceDTO.from_model(e) for e in evidence_list]
    
    def log_verification_step(
        self,
        submission_id: int,
        step: str,
        status: str,
        details: Dict[str, Any],
        performed_by_user_id: Optional[int] = None,
    ) -> None:
        """Log verification step. See protocol docstring."""
        from apps.tournaments.models import ResultVerificationLog
        
        try:
            ResultVerificationLog.objects.create(
                submission_id=submission_id,
                step=step,
                status=status,
                details=details,
                performed_by_user_id=performed_by_user_id,
            )
        except Exception as e:
            raise DisputeError(f"Failed to log verification step: {e}") from e
