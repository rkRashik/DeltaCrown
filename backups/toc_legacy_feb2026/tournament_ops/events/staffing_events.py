"""
Staffing Events - Phase 7, Epic 7.3

Domain events for staff and referee management.

Architecture:
- Event-driven integration pattern
- Used by StaffingService to notify other services
- Pure Python (no Django imports)

Reference: Phase 7, Epic 7.3 - Staff & Referee Role System
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from apps.tournament_ops.dtos.base import DTOBase


@dataclass
class StaffAssignedToTournamentEvent(DTOBase):
    """
    Event published when staff member is assigned to a tournament.
    
    Subscribers can:
    - Send notification to assigned staff
    - Update access control lists
    - Log audit trail
    
    Reference: Phase 7, Epic 7.3 - Staff Assignment Events
    """
    
    assignment_id: int
    tournament_id: int
    tournament_name: str
    user_id: int
    username: str
    role_code: str
    role_name: str
    stage_id: Optional[int]
    stage_name: Optional[str]
    assigned_by_user_id: int
    assigned_by_username: str
    assigned_at: datetime
    
    @property
    def event_type(self) -> str:
        return "staff.assigned_to_tournament"


@dataclass
class StaffRemovedFromTournamentEvent(DTOBase):
    """
    Event published when staff member is removed from a tournament.
    
    Subscribers can:
    - Send notification to removed staff
    - Revoke access permissions
    - Log audit trail
    
    Reference: Phase 7, Epic 7.3 - Staff Removal Events
    """
    
    assignment_id: int
    tournament_id: int
    tournament_name: str
    user_id: int
    username: str
    role_code: str
    role_name: str
    removed_at: datetime
    
    @property
    def event_type(self) -> str:
        return "staff.removed_from_tournament"


@dataclass
class RefereeAssignedToMatchEvent(DTOBase):
    """
    Event published when referee is assigned to a match.
    
    Subscribers can:
    - Send notification to referee
    - Update match staffing status
    - Trigger schedule conflict checks
    
    Reference: Phase 7, Epic 7.3 - Referee Assignment Events
    """
    
    referee_assignment_id: int
    match_id: int
    tournament_id: int
    stage_id: int
    round_number: int
    match_number: int
    staff_assignment_id: int
    user_id: int
    username: str
    is_primary: bool
    assigned_by_user_id: int
    assigned_by_username: str
    assigned_at: datetime
    
    @property
    def event_type(self) -> str:
        return "referee.assigned_to_match"


@dataclass
class RefereeUnassignedFromMatchEvent(DTOBase):
    """
    Event published when referee is removed from a match.
    
    Subscribers can:
    - Send notification to referee
    - Update match staffing status
    - Trigger re-assignment workflow
    
    Reference: Phase 7, Epic 7.3 - Referee Unassignment Events
    """
    
    referee_assignment_id: int
    match_id: int
    tournament_id: int
    user_id: int
    username: str
    was_primary: bool
    unassigned_at: datetime
    
    @property
    def event_type(self) -> str:
        return "referee.unassigned_from_match"
