"""
Dispute Resolution DTOs - Phase 6, Epic 6.5

Data Transfer Objects for organizer dispute resolution workflow.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.5 (Dispute Resolution Module)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


# Resolution type constants
RESOLUTION_TYPE_APPROVE_ORIGINAL = "approve_original"
RESOLUTION_TYPE_APPROVE_DISPUTE = "approve_dispute"
RESOLUTION_TYPE_CUSTOM_RESULT = "custom_result"
RESOLUTION_TYPE_DISMISS_DISPUTE = "dismiss_dispute"

VALID_RESOLUTION_TYPES = {
    RESOLUTION_TYPE_APPROVE_ORIGINAL,
    RESOLUTION_TYPE_APPROVE_DISPUTE,
    RESOLUTION_TYPE_CUSTOM_RESULT,
    RESOLUTION_TYPE_DISMISS_DISPUTE,
}


@dataclass
class DisputeResolutionDTO:
    """
    Dispute resolution request from organizer.
    
    Attributes:
        submission_id: Match result submission being resolved
        dispute_id: Dispute record ID (optional - may be None if no dispute exists)
        resolution_type: Type of resolution action
        resolved_by_user_id: Organizer/admin user ID
        resolution_notes: Organizer's notes/reasoning for resolution
        custom_result_payload: Custom result data (required for custom_result type)
        created_at: Timestamp of resolution
        
    Resolution Types:
        - approve_original: Original submission correct, dismiss dispute
        - approve_dispute: Disputer correct, apply disputed result
        - custom_result: Neither correct, apply custom organizer result
        - dismiss_dispute: Invalid dispute, restart 24-hour timer
        
    Reference: Phase 6, Epic 6.5 - Dispute Resolution Module
    """
    
    submission_id: int
    dispute_id: Optional[int]
    resolution_type: str
    resolved_by_user_id: int
    resolution_notes: str
    custom_result_payload: Optional[Dict[str, Any]]
    created_at: datetime
    
    def validate(self) -> None:
        """
        Validate resolution data.
        
        Rules:
        1. resolution_type must be one of 4 supported types
        2. If resolution_type == "custom_result", custom_result_payload must not be None
        3. For other types, custom_result_payload should be None (ignored if present)
        
        Raises:
            ValueError: Validation failed
            
        Reference: Phase 6, Epic 6.5 - Resolution Validation
        """
        # Validate resolution type
        if self.resolution_type not in VALID_RESOLUTION_TYPES:
            raise ValueError(
                f"Invalid resolution_type '{self.resolution_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_RESOLUTION_TYPES))}"
            )
        
        # Validate custom_result_payload for custom_result type
        if self.resolution_type == RESOLUTION_TYPE_CUSTOM_RESULT:
            if self.custom_result_payload is None:
                raise ValueError(
                    "custom_result_payload is required for resolution_type 'custom_result'"
                )
            if not isinstance(self.custom_result_payload, dict):
                raise ValueError(
                    "custom_result_payload must be a dictionary"
                )
        
        # For other types, custom_result_payload should be None
        # (we don't raise error if present, just document it should be None)
        
        # Validate required fields
        if not self.resolved_by_user_id:
            raise ValueError("resolved_by_user_id is required")
        
        if not self.submission_id:
            raise ValueError("submission_id is required")
    
    def is_approve_original(self) -> bool:
        """Check if resolution approves original submission."""
        return self.resolution_type == RESOLUTION_TYPE_APPROVE_ORIGINAL
    
    def is_approve_dispute(self) -> bool:
        """Check if resolution approves disputed result."""
        return self.resolution_type == RESOLUTION_TYPE_APPROVE_DISPUTE
    
    def is_custom_result(self) -> bool:
        """Check if resolution applies custom result."""
        return self.resolution_type == RESOLUTION_TYPE_CUSTOM_RESULT
    
    def is_dismiss_dispute(self) -> bool:
        """Check if resolution dismisses dispute."""
        return self.resolution_type == RESOLUTION_TYPE_DISMISS_DISPUTE
    
    def requires_finalization(self) -> bool:
        """
        Check if resolution requires match finalization.
        
        Returns:
            True for approve_original, approve_dispute, custom_result
            False for dismiss_dispute (restarts timer instead)
        """
        return not self.is_dismiss_dispute()
    
    def get_payload_to_use(self, submission_payload: Dict[str, Any], dispute_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determine which payload to use for finalization.
        
        Args:
            submission_payload: Original submission payload
            dispute_payload: Disputed payload (if any)
            
        Returns:
            Payload to use for finalization
            
        Raises:
            ValueError: If dispute_payload required but not provided
        """
        if self.is_approve_original():
            return submission_payload
        elif self.is_approve_dispute():
            if dispute_payload is None:
                raise ValueError("dispute_payload required for approve_dispute resolution")
            return dispute_payload
        elif self.is_custom_result():
            # Already validated in validate()
            return self.custom_result_payload  # type: ignore
        else:
            # dismiss_dispute doesn't need payload
            return submission_payload
