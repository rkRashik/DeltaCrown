"""
Scheduling Domain Events - Phase 7, Epic 7.2

Domain events for manual match scheduling workflows.

Architecture:
- Event-driven integration pattern
- Published by ManualSchedulingService
- Consumed by audit, notification, and analytics systems

Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class MatchScheduledManuallyEvent:
    """
    Published when organizer manually schedules a match.
    
    Attributes:
        match_id: ID of scheduled match
        tournament_id: Tournament ID
        stage_id: Stage ID
        scheduled_time: Assigned time
        assigned_by_user_id: Organizer who scheduled
        assigned_at: When assignment occurred
    """
    
    match_id: int
    tournament_id: int
    stage_id: int
    scheduled_time: datetime
    assigned_by_user_id: int
    assigned_at: datetime
    
    def __post_init__(self):
        """Validate event data."""
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        if self.stage_id <= 0:
            raise ValueError("stage_id must be positive")
        if self.assigned_by_user_id <= 0:
            raise ValueError("assigned_by_user_id must be positive")


@dataclass
class MatchRescheduledEvent:
    """
    Published when organizer reschedules an existing match.
    
    Attributes:
        match_id: ID of rescheduled match
        tournament_id: Tournament ID
        stage_id: Stage ID
        old_time: Previous scheduled time
        new_time: New scheduled time
        rescheduled_by_user_id: Organizer who rescheduled
        rescheduled_at: When reschedule occurred
    """
    
    match_id: int
    tournament_id: int
    stage_id: int
    old_time: Optional[datetime]
    new_time: datetime
    rescheduled_by_user_id: int
    rescheduled_at: datetime
    
    def __post_init__(self):
        """Validate event data."""
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        if self.stage_id <= 0:
            raise ValueError("stage_id must be positive")
        if self.rescheduled_by_user_id <= 0:
            raise ValueError("rescheduled_by_user_id must be positive")


@dataclass
class MatchScheduleConflictDetectedEvent:
    """
    Published when conflict detected during scheduling.
    
    Attributes:
        match_id: ID of match with conflict
        conflict_type: Type of conflict
        severity: warning or error
        message: Conflict description
        detected_at: When conflict was detected
    """
    
    match_id: int
    conflict_type: str
    severity: str
    message: str
    detected_at: datetime
    
    def __post_init__(self):
        """Validate event data."""
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        
        valid_types = ['team_conflict', 'resource_conflict', 'time_overlap', 'blackout_period']
        if self.conflict_type not in valid_types:
            raise ValueError(f"Invalid conflict_type: {self.conflict_type}")
        
        valid_severities = ['warning', 'error']
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity: {self.severity}")


@dataclass
class BulkMatchesShiftedEvent:
    """
    Published when organizer bulk-shifts matches in a stage.
    
    Attributes:
        stage_id: Stage ID
        delta_minutes: Time shift in minutes
        shifted_count: Number of matches shifted
        shifted_match_ids: IDs of shifted matches
        shifted_by_user_id: Organizer who performed shift
        shifted_at: When shift occurred
    """
    
    stage_id: int
    delta_minutes: int
    shifted_count: int
    shifted_match_ids: List[int]
    shifted_by_user_id: int
    shifted_at: datetime
    
    def __post_init__(self):
        """Validate event data."""
        if self.stage_id <= 0:
            raise ValueError("stage_id must be positive")
        if self.shifted_count < 0:
            raise ValueError("shifted_count must be non-negative")
        if self.shifted_count != len(self.shifted_match_ids):
            raise ValueError("shifted_count must match shifted_match_ids length")
        if self.shifted_by_user_id <= 0:
            raise ValueError("shifted_by_user_id must be positive")
