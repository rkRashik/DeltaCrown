"""
Organizer Review DTOs - Phase 6, Epic 6.3

DTOs for organizer results inbox and review workflows.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.3 (Organizer Results Inbox)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from apps.tournament_ops.dtos import MatchResultSubmissionDTO, DisputeDTO


@dataclass
class OrganizerReviewItemDTO:
    """
    DTO for organizer review inbox items.
    
    Represents a submission that requires organizer attention:
    - Pending submissions awaiting opponent response
    - Disputed submissions requiring organizer resolution
    - Overdue auto-confirm submissions
    - Submissions ready for finalization
    
    Priority rules:
    - disputed → priority 1 (highest)
    - overdue auto-confirm → priority 2 (high)
    - pending >12h → priority 3 (medium)
    - others → priority 4 (low)
    
    Reference: Phase 6, Epic 6.3 - Organizer Results Inbox
    """
    
    submission_id: int
    match_id: int
    tournament_id: int
    stage_id: Optional[int]
    submitted_by_user_id: int
    status: str  # pending, disputed, confirmed, finalized, rejected
    dispute_id: Optional[int]
    dispute_status: Optional[str]  # open, under_review, escalated, resolved_*, cancelled
    auto_confirm_deadline: datetime
    opened_at: Optional[datetime]  # Dispute opened_at if disputed
    is_overdue: bool  # True if past auto_confirm_deadline
    priority: int  # 1=highest (disputed), 2=high (overdue), 3=medium (pending >12h), 4=low
    
    @classmethod
    def from_submission_and_dispute(
        cls,
        submission: MatchResultSubmissionDTO,
        dispute: Optional[DisputeDTO] = None,
    ) -> 'OrganizerReviewItemDTO':
        """
        Create OrganizerReviewItemDTO from submission and optional dispute.
        
        Args:
            submission: MatchResultSubmissionDTO
            dispute: Optional DisputeDTO
            
        Returns:
            OrganizerReviewItemDTO with computed priority
            
        Reference: Phase 6, Epic 6.3 - Review Item Creation
        """
        # Determine if overdue
        now = datetime.now(timezone.utc)
        is_overdue = submission.auto_confirm_deadline < now if submission.auto_confirm_deadline else False
        
        # Create item
        item = cls(
            submission_id=submission.id,
            match_id=submission.match_id,
            tournament_id=submission.tournament_id,
            stage_id=submission.stage_id,
            submitted_by_user_id=submission.submitted_by_user_id,
            status=submission.status,
            dispute_id=dispute.id if dispute else None,
            dispute_status=dispute.status if dispute else None,
            auto_confirm_deadline=submission.auto_confirm_deadline,
            opened_at=dispute.opened_at if dispute else None,
            is_overdue=is_overdue,
            priority=0,  # Will be computed below
        )
        
        # Compute priority
        item.priority = item.compute_priority()
        
        return item
    
    def compute_priority(self) -> int:
        """
        Compute priority based on submission and dispute state.
        
        Priority rules:
        1. disputed → priority 1 (highest)
        2. overdue auto-confirm → priority 2 (high)
        3. pending >12h → priority 3 (medium)
        4. others → priority 4 (low)
        
        Returns:
            int (1=highest, 4=lowest)
            
        Reference: Phase 6, Epic 6.3 - Priority Computation
        """
        # Rule 1: Disputed submissions (highest priority)
        if self.status == 'disputed' or self.dispute_id is not None:
            return 1
        
        # Rule 2: Overdue auto-confirm (high priority)
        if self.is_overdue:
            return 2
        
        # Rule 3: Pending >12h (medium priority)
        if self.status == 'pending':
            # Check if submission is >12h old
            # Note: We need submitted_at from submission, but it's not in this DTO
            # For now, we'll use a simpler heuristic: if auto_confirm_deadline is within 12h, it's recent
            now = datetime.now(timezone.utc)
            hours_until_deadline = (self.auto_confirm_deadline - now).total_seconds() / 3600
            
            # If deadline is in <12h (and not overdue), submission is >12h old (24h deadline - 12h = 12h left)
            if hours_until_deadline < 12:
                return 3
        
        # Rule 4: Everything else (low priority)
        return 4
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.priority not in (1, 2, 3, 4):
            raise ValueError(f"Invalid priority: {self.priority}. Must be 1-4")
        
        if self.status not in ('pending', 'disputed', 'confirmed', 'finalized', 'rejected'):
            raise ValueError(f"Invalid status: {self.status}")
        
        if self.dispute_id is not None and self.dispute_status is None:
            raise ValueError("dispute_status required when dispute_id is set")
        
        if self.dispute_status is not None:
            valid_dispute_statuses = (
                'open', 'under_review', 'escalated',
                'resolved_for_submitter', 'resolved_for_opponent', 'cancelled'
            )
            if self.dispute_status not in valid_dispute_statuses:
                raise ValueError(f"Invalid dispute_status: {self.dispute_status}")
        
        return True
