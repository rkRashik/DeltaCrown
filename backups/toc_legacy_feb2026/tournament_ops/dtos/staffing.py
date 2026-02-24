"""
Staffing DTOs - Phase 7, Epic 7.3

Data Transfer Objects for staff and referee management.

Architecture:
- Part of tournament_ops layer (no ORM imports)
- Used for cross-domain communication
- Validation methods for business rules

Reference: Phase 7, Epic 7.3 - Staff & Referee Role System
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from .base import DTOBase


@dataclass
class StaffRoleDTO(DTOBase):
    """
    DTO for staff role definition with capability-based permissions.
    
    Represents a role that can be assigned to staff members,
    with capabilities defining what actions they can perform.
    
    Reference: Phase 7, Epic 7.3 - Staff Role System
    """
    
    role_id: int
    name: str
    code: str
    description: str
    capabilities: Dict[str, bool]
    is_referee_role: bool
    created_at: datetime
    updated_at: datetime
    
    def has_capability(self, capability_name: str) -> bool:
        """Check if role has a specific capability."""
        return self.capabilities.get(capability_name, False)
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.role_id <= 0:
            raise ValueError("role_id must be positive")
        
        if not self.name or not self.code:
            raise ValueError("name and code are required")
        
        if self.is_referee_role and not self.has_capability('can_referee_matches'):
            raise ValueError(
                "Referee roles must have 'can_referee_matches' capability"
            )
        
        return True
    
    @classmethod
    def from_model(cls, model):
        """
        Create DTO from Django model instance.
        
        Args:
            model: StaffRole model instance
            
        Returns:
            StaffRoleDTO
        """
        return cls(
            role_id=model.id,
            name=model.name,
            code=model.code,
            description=model.description or "",
            capabilities=model.capabilities or {},
            is_referee_role=model.is_referee_role,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


@dataclass
class TournamentStaffAssignmentDTO(DTOBase):
    """
    DTO for staff assignment to a tournament.
    
    Represents a user assigned to a specific role for a tournament,
    with optional stage-specific constraints.
    
    Reference: Phase 7, Epic 7.3 - Staff Assignment
    """
    
    assignment_id: int
    tournament_id: int
    tournament_name: str
    user_id: int
    username: str
    user_email: str
    role: StaffRoleDTO
    is_active: bool
    stage_id: Optional[int]
    stage_name: Optional[str]
    assigned_by_user_id: Optional[int]
    assigned_by_username: Optional[str]
    assigned_at: datetime
    notes: str
    
    def is_referee_assignment(self) -> bool:
        """Check if this assignment is for a referee role."""
        return self.role.is_referee_role
    
    def can_perform(self, capability_name: str) -> bool:
        """Check if this assignment has a specific capability."""
        return self.is_active and self.role.has_capability(capability_name)
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.assignment_id <= 0:
            raise ValueError("assignment_id must be positive")
        
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        
        if not self.username:
            raise ValueError("username is required")
        
        # Validate nested role DTO
        self.role.validate()
        
        return True
    
    @classmethod
    def from_model(cls, model):
        """
        Create DTO from Django model instance.
        
        Args:
            model: TournamentStaffAssignment model instance
            
        Returns:
            TournamentStaffAssignmentDTO
        """
        return cls(
            assignment_id=model.id,
            tournament_id=model.tournament_id,
            tournament_name=model.tournament.name,
            user_id=model.user_id,
            username=model.user.username,
            user_email=model.user.email,
            role=StaffRoleDTO.from_model(model.role),
            is_active=model.is_active,
            stage_id=model.stage_id,
            stage_name=model.stage.name if model.stage else None,
            assigned_by_user_id=model.assigned_by_id,
            assigned_by_username=model.assigned_by.username if model.assigned_by else None,
            assigned_at=model.assigned_at,
            notes=model.notes or ""
        )


@dataclass
class MatchRefereeAssignmentDTO(DTOBase):
    """
    DTO for referee assignment to a specific match.
    
    Represents a staff member (with referee role) assigned
    to referee a particular match.
    
    Reference: Phase 7, Epic 7.3 - Match Referee Assignment
    """
    
    assignment_id: int
    match_id: int
    tournament_id: int
    stage_id: int
    round_number: int
    match_number: int
    staff_assignment: TournamentStaffAssignmentDTO
    is_primary: bool
    assigned_by_user_id: Optional[int]
    assigned_by_username: Optional[str]
    assigned_at: datetime
    notes: str
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.assignment_id <= 0:
            raise ValueError("assignment_id must be positive")
        
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        
        if not self.staff_assignment.is_referee_assignment():
            raise ValueError(
                f"Staff assignment must have referee role. "
                f"Current role: {self.staff_assignment.role.name}"
            )
        
        # Validate nested staff assignment DTO
        self.staff_assignment.validate()
        
        return True
    
    @classmethod
    def from_model(cls, model):
        """
        Create DTO from Django model instance.
        
        Args:
            model: MatchRefereeAssignment model instance
            
        Returns:
            MatchRefereeAssignmentDTO
        """
        return cls(
            assignment_id=model.id,
            match_id=model.match_id,
            tournament_id=model.match.tournament_id,
            stage_id=model.match.stage_id,
            round_number=model.match.round_number,
            match_number=model.match.match_number,
            staff_assignment=TournamentStaffAssignmentDTO.from_model(model.staff_assignment),
            is_primary=model.is_primary,
            assigned_by_user_id=model.assigned_by_id,
            assigned_by_username=model.assigned_by.username if model.assigned_by else None,
            assigned_at=model.assigned_at,
            notes=model.notes or ""
        )


@dataclass
class StaffLoadDTO(DTOBase):
    """
    DTO for staff member workload summary.
    
    Aggregates information about a staff member's current
    match assignments for load balancing.
    
    Reference: Phase 7, Epic 7.3 - Staff Load Tracking
    """
    
    staff_assignment: TournamentStaffAssignmentDTO
    total_matches_assigned: int
    upcoming_matches: int
    completed_matches: int
    concurrent_matches: int  # Matches overlapping in time
    is_overloaded: bool  # Based on configurable threshold
    load_percentage: float  # 0-100, relative to max recommended load
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.total_matches_assigned < 0:
            raise ValueError("total_matches_assigned must be non-negative")
        
        if self.upcoming_matches < 0:
            raise ValueError("upcoming_matches must be non-negative")
        
        if self.completed_matches < 0:
            raise ValueError("completed_matches must be non-negative")
        
        if self.concurrent_matches < 0:
            raise ValueError("concurrent_matches must be non-negative")
        
        if not (0 <= self.load_percentage <= 100):
            raise ValueError("load_percentage must be between 0 and 100")
        
        # Validate nested staff assignment DTO
        self.staff_assignment.validate()
        
        return True
