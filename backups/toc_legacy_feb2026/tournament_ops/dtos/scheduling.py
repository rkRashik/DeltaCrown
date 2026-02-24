"""
Match Scheduling DTOs - Phase 7, Epic 7.2

Data Transfer Objects for manual match scheduling workflows.

Architecture:
- Part of tournament_ops layer (no ORM imports)
- Used for cross-domain communication
- Validation methods for business rules
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from .base import DTOBase


@dataclass
class MatchSchedulingItemDTO(DTOBase):
    """
    DTO for matches requiring scheduling by organizers.
    
    Represents a match with its scheduling metadata, constraints,
    and conflict information for organizer scheduling UI.
    
    Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
    """
    
    match_id: int
    tournament_id: int
    tournament_name: str
    stage_id: int
    stage_name: str
    round_number: int
    match_number: int
    participant1_id: Optional[int]
    participant1_name: Optional[str]
    participant2_id: Optional[int]
    participant2_name: Optional[str]
    scheduled_time: Optional[datetime]
    estimated_duration_minutes: int
    state: str  # scheduled, pending, in_progress, completed
    lobby_info: Dict[str, Any]
    conflicts: List[str]  # List of conflict descriptions
    can_reschedule: bool
    
    def has_conflicts(self) -> bool:
        """Check if match has any scheduling conflicts."""
        return len(self.conflicts) > 0
    
    def is_scheduled(self) -> bool:
        """Check if match has a scheduled time."""
        return self.scheduled_time is not None
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        
        if self.stage_id <= 0:
            raise ValueError("stage_id must be positive")
        
        if self.round_number < 0:
            raise ValueError("round_number must be non-negative")
        
        if self.estimated_duration_minutes <= 0:
            raise ValueError("estimated_duration_minutes must be positive")
        
        valid_states = ['scheduled', 'pending', 'in_progress', 'completed', 'cancelled']
        if self.state not in valid_states:
            raise ValueError(f"Invalid state: {self.state}")
        
        return True


@dataclass
class SchedulingSlotDTO(DTOBase):
    """
    DTO for available scheduling time slots.
    
    Represents a potential time slot for match scheduling,
    including availability information and constraints.
    
    Reference: Phase 7, Epic 7.2 - Time Slot Generation
    """
    
    slot_start: datetime
    slot_end: datetime
    duration_minutes: int
    is_available: bool
    conflicts: List[str]  # Why this slot might be problematic
    suggested_matches: List[int]  # Match IDs that could fit here
    
    def is_conflict_free(self) -> bool:
        """Check if slot has no conflicts."""
        return self.is_available and len(self.conflicts) == 0
    
    def can_fit_match(self, duration_minutes: int) -> bool:
        """Check if match duration fits in slot."""
        return self.duration_minutes >= duration_minutes
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.slot_start >= self.slot_end:
            raise ValueError("slot_start must be before slot_end")
        
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        
        # Calculate expected duration
        expected_duration = int((self.slot_end - self.slot_start).total_seconds() / 60)
        if abs(expected_duration - self.duration_minutes) > 1:
            raise ValueError(
                f"duration_minutes {self.duration_minutes} doesn't match "
                f"slot_start to slot_end ({expected_duration} minutes)"
            )
        
        return True


@dataclass
class SchedulingConflictDTO(DTOBase):
    """
    DTO for scheduling conflict information.
    
    Represents a detected conflict when assigning a match
    to a time slot (soft validation - warnings not errors).
    
    Reference: Phase 7, Epic 7.2 - Conflict Detection
    """
    
    conflict_type: str  # team_conflict, resource_conflict, time_overlap, blackout_period
    severity: str  # warning, error (most will be warning in Phase 7)
    message: str
    affected_match_ids: List[int]
    suggested_resolution: Optional[str]
    
    def is_blocking(self) -> bool:
        """Check if conflict is severe enough to block scheduling."""
        return self.severity == 'error'
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        valid_types = ['team_conflict', 'resource_conflict', 'time_overlap', 'blackout_period']
        if self.conflict_type not in valid_types:
            raise ValueError(f"Invalid conflict_type: {self.conflict_type}")
        
        valid_severities = ['warning', 'error']
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity: {self.severity}")
        
        if not self.message:
            raise ValueError("message cannot be empty")
        
        return True


@dataclass
class BulkShiftResultDTO(DTOBase):
    """
    DTO for bulk shift operation results.
    
    Contains summary of matches shifted, conflicts detected,
    and any failures during bulk rescheduling.
    
    Reference: Phase 7, Epic 7.2 - Bulk Operations
    """
    
    shifted_count: int
    failed_count: int
    conflicts_detected: List[SchedulingConflictDTO]
    failed_match_ids: List[int]
    error_messages: Dict[int, str]  # match_id -> error message
    
    def was_successful(self) -> bool:
        """Check if all matches were shifted successfully."""
        return self.failed_count == 0
    
    def has_conflicts(self) -> bool:
        """Check if any conflicts were detected."""
        return len(self.conflicts_detected) > 0
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.shifted_count < 0:
            raise ValueError("shifted_count must be non-negative")
        
        if self.failed_count < 0:
            raise ValueError("failed_count must be non-negative")
        
        if self.failed_count != len(self.failed_match_ids):
            raise ValueError(
                f"failed_count {self.failed_count} doesn't match "
                f"failed_match_ids length {len(self.failed_match_ids)}"
            )
        
        return True
