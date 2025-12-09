"""
Dispute Data Transfer Objects - Phase 6, Epic 6.2

DTOs for dispute records, evidence, and opponent verification.
Used by DisputeService and ResultSubmissionService for cross-domain communication.

Reference:
- PHASE6_WORKPLAN_DRAFT.md - Epic 6.2 (Opponent Verification & Dispute System)
- No ORM imports allowed in tournament_ops layer

Created: December 12, 2025
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from .base import DTOBase


@dataclass
class DisputeDTO(DTOBase):
    """
    DTO for DisputeRecord.
    
    Represents a dispute without coupling to Django ORM model.
    Used by tournament_ops services to work with dispute information.
    
    Attributes:
        id: Dispute primary key
        submission_id: ID of the disputed MatchResultSubmission
        opened_by_user_id: User who opened the dispute
        opened_by_team_id: Team representing the disputer (optional)
        status: Dispute status (open, under_review, resolved_*, cancelled, escalated)
        reason_code: Categorized reason (score_mismatch, wrong_winner, etc.)
        description: Detailed description from opponent
        resolution_notes: Internal notes explaining resolution decision
        opened_at: When dispute was opened
        resolved_at: When dispute was resolved (optional)
        escalated_at: When dispute was escalated (optional)
        resolved_by_user_id: User who made final decision (optional)
    """
    
    id: int
    submission_id: int
    opened_by_user_id: int
    opened_by_team_id: Optional[int]
    status: str
    reason_code: str
    description: str
    resolution_notes: str
    opened_at: datetime
    resolved_at: Optional[datetime]
    escalated_at: Optional[datetime]
    resolved_by_user_id: Optional[int]
    
    @classmethod
    def from_model(cls, obj: any) -> "DisputeDTO":
        """
        Create DisputeDTO from DisputeRecord model.
        
        Args:
            obj: DisputeRecord model instance
            
        Returns:
            DisputeDTO instance
        """
        return cls(
            id=obj.id,
            submission_id=obj.submission_id,
            opened_by_user_id=obj.opened_by_user_id,
            opened_by_team_id=obj.opened_by_team_id,
            status=obj.status,
            reason_code=obj.reason_code,
            description=obj.description,
            resolution_notes=obj.resolution_notes,
            opened_at=obj.opened_at,
            resolved_at=obj.resolved_at,
            escalated_at=obj.escalated_at,
            resolved_by_user_id=obj.resolved_by_user_id,
        )
    
    def is_open(self) -> bool:
        """Check if dispute is still open (not resolved/cancelled)."""
        return self.status in ('open', 'under_review', 'escalated')
    
    def is_resolved(self) -> bool:
        """Check if dispute has been resolved."""
        return self.status in (
            'resolved_for_submitter',
            'resolved_for_opponent',
            'cancelled'
        )
    
    def validate(self) -> None:
        """
        Validate dispute data.
        
        Raises:
            ValueError: If validation fails
        """
        # Validate status
        valid_statuses = (
            'open',
            'under_review',
            'resolved_for_submitter',
            'resolved_for_opponent',
            'cancelled',
            'escalated'
        )
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}")
        
        # Validate reason_code
        valid_reasons = (
            'score_mismatch',
            'wrong_winner',
            'cheating_suspicion',
            'incorrect_map',
            'match_not_played',
            'other'
        )
        if self.reason_code not in valid_reasons:
            raise ValueError(f"Invalid reason_code: {self.reason_code}")
        
        # Description required
        if not self.description:
            raise ValueError("description is required")
        
        # Resolved disputes must have resolved_at
        if self.is_resolved() and not self.resolved_at:
            raise ValueError(f"resolved_at required for status: {self.status}")
        
        # Escalated disputes must have escalated_at
        if self.status == 'escalated' and not self.escalated_at:
            raise ValueError("escalated_at required for escalated disputes")


@dataclass
class DisputeEvidenceDTO(DTOBase):
    """
    DTO for DisputeEvidence.
    
    Represents evidence attached to a dispute (screenshots, videos, etc.).
    
    Attributes:
        id: Evidence primary key
        dispute_id: ID of the parent DisputeRecord
        uploaded_by_user_id: User who uploaded the evidence
        evidence_type: Type of evidence (screenshot, video, chat_log, other)
        url: URL to external resource (S3, imgur, Discord, etc.)
        notes: Additional context about the evidence
        created_at: When evidence was uploaded
    """
    
    id: int
    dispute_id: int
    uploaded_by_user_id: int
    evidence_type: str
    url: str
    notes: str
    created_at: datetime
    
    @classmethod
    def from_model(cls, obj: any) -> "DisputeEvidenceDTO":
        """
        Create DisputeEvidenceDTO from DisputeEvidence model.
        
        Args:
            obj: DisputeEvidence model instance
            
        Returns:
            DisputeEvidenceDTO instance
        """
        return cls(
            id=obj.id,
            dispute_id=obj.dispute_id,
            uploaded_by_user_id=obj.uploaded_by_user_id,
            evidence_type=obj.evidence_type,
            url=obj.url,
            notes=obj.notes,
            created_at=obj.created_at,
        )
    
    def validate(self) -> None:
        """
        Validate evidence data.
        
        Raises:
            ValueError: If validation fails
        """
        # Validate evidence_type
        valid_types = ('screenshot', 'video', 'chat_log', 'other')
        if self.evidence_type not in valid_types:
            raise ValueError(f"Invalid evidence_type: {self.evidence_type}")
        
        # URL required
        if not self.url:
            raise ValueError("url is required")


@dataclass
class OpponentVerificationDTO(DTOBase):
    """
    DTO for opponent response to a result submission.
    
    Lightweight in-memory DTO (no from_model) used to structure
    opponent decision payloads in ResultSubmissionService.
    
    Attributes:
        submission_id: ID of the MatchResultSubmission
        responding_user_id: User making the decision
        decision: "confirm" or "dispute"
        reason_code: Reason for dispute (optional, required if decision="dispute")
        notes: Additional context from opponent
    """
    
    submission_id: int
    responding_user_id: int
    decision: str  # "confirm" or "dispute"
    reason_code: Optional[str]
    notes: str
    
    def validate(self) -> None:
        """
        Validate opponent verification data.
        
        Raises:
            ValueError: If validation fails
        """
        # Validate decision
        if self.decision not in ('confirm', 'dispute'):
            raise ValueError(f"Invalid decision: {self.decision}. Must be 'confirm' or 'dispute'")
        
        # If disputing, reason_code required
        if self.decision == 'dispute' and not self.reason_code:
            raise ValueError("reason_code required when decision='dispute'")
        
        # Validate reason_code if provided
        if self.reason_code:
            valid_reasons = (
                'score_mismatch',
                'wrong_winner',
                'cheating_suspicion',
                'incorrect_map',
                'match_not_played',
                'other'
            )
            if self.reason_code not in valid_reasons:
                raise ValueError(f"Invalid reason_code: {self.reason_code}")
