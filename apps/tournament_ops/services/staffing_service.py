"""
Staffing Service — Phase 7, Epic 7.3 + Phase 2, Task 2.6 consolidation.

Canonical service for staff and referee management.  Uses Phase 7 models
(``StaffRole``, ``TournamentStaffAssignment``, ``MatchRefereeAssignment``)
via the ``StaffingAdapter``.

The ``StaffPermissionChecker`` in ``tournaments/services/`` queries staff
assignments from this layer.

Architecture:
- Pure orchestration (no ORM imports)
- Uses StaffingAdapter for data access
- Publishes domain events (own EventBus + core EventBus)
- Capability-based permission checks
- Load balancing for referee assignments

Reference: Phase 7, Epic 7.3 — Staff & Referee Role System
"""

import logging
from typing import List, Optional
from datetime import datetime

from apps.tournament_ops.dtos.staffing import (
    StaffRoleDTO,
    TournamentStaffAssignmentDTO,
    MatchRefereeAssignmentDTO,
    StaffLoadDTO,
)
from apps.tournament_ops.adapters.staffing_adapter import StaffingAdapter
from apps.tournament_ops.events.staffing_events import (
    StaffAssignedToTournamentEvent,
    StaffRemovedFromTournamentEvent,
    RefereeAssignedToMatchEvent,
    RefereeUnassignedFromMatchEvent,
)
from apps.tournament_ops.events.event_bus import EventBus

logger = logging.getLogger(__name__)


def _publish_staff_event_to_core(event_name: str, **kwargs):
    """Also publish to the core EventBus for cross-app handlers."""
    try:
        from apps.core.events import event_bus
        from apps.core.events.bus import Event
        event_bus.publish(Event(event_type=event_name, data=kwargs, source="staffing_service"))
    except Exception as exc:
        logger.warning("Failed to publish %s to core event bus: %s", event_name, exc)


class StaffingService:
    """
    Service for managing tournament staff and referee assignments.
    
    Responsibilities:
    - Assign/remove staff from tournaments
    - Assign/unassign referees to matches
    - Validate capability requirements
    - Calculate and monitor staff workload
    - Publish domain events for integration
    
    Reference: Phase 7, Epic 7.3 - Staffing Service Layer
    """
    
    def __init__(
        self,
        staffing_adapter: Optional[StaffingAdapter] = None,
        event_bus: Optional[EventBus] = None
    ):
        """
        Initialize service with adapters.
        
        Args:
            staffing_adapter: Adapter for staffing data access
            event_bus: Event bus for publishing domain events
        """
        self.staffing_adapter = staffing_adapter or StaffingAdapter()
        self.event_bus = event_bus or EventBus()
    
    # --------------------------------------------------
    # Staff Role Queries
    # --------------------------------------------------
    
    def get_all_staff_roles(self) -> List[StaffRoleDTO]:
        """
        Get all available staff roles.
        
        Returns:
            List of StaffRoleDTO objects
        """
        return self.staffing_adapter.get_staff_roles()
    
    def get_referee_roles(self) -> List[StaffRoleDTO]:
        """
        Get all roles that can referee matches.
        
        Returns:
            List of StaffRoleDTO objects with is_referee_role=True
        """
        return self.staffing_adapter.get_staff_roles(is_referee_role=True)
    
    def get_role_by_code(self, role_code: str) -> Optional[StaffRoleDTO]:
        """
        Get a staff role by its unique code.
        
        Args:
            role_code: Unique role code
            
        Returns:
            StaffRoleDTO if found, None otherwise
        """
        return self.staffing_adapter.get_staff_role_by_code(role_code)
    
    # --------------------------------------------------
    # Tournament Staff Assignment
    # --------------------------------------------------
    
    def assign_staff_to_tournament(
        self,
        tournament_id: int,
        user_id: int,
        role_code: str,
        assigned_by_user_id: int,
        stage_id: Optional[int] = None,
        notes: str = ""
    ) -> TournamentStaffAssignmentDTO:
        """
        Assign a staff member to a tournament with a specific role.
        
        Business Rules:
        - Role must exist and be valid
        - User cannot be assigned same role twice (unless inactive)
        - Stage must belong to tournament if specified
        
        Args:
            tournament_id: Tournament ID
            user_id: User ID to assign
            role_code: Role code to assign
            assigned_by_user_id: User ID who made the assignment
            stage_id: Optional stage ID for stage-specific assignment
            notes: Optional notes
            
        Returns:
            TournamentStaffAssignmentDTO
            
        Raises:
            ValueError: If validation fails
        """
        # Validate role exists
        role = self.staffing_adapter.get_staff_role_by_code(role_code)
        if not role:
            raise ValueError(f"Invalid staff role: {role_code}")
        
        # Create assignment via adapter
        assignment = self.staffing_adapter.assign_staff_to_tournament(
            tournament_id=tournament_id,
            user_id=user_id,
            role_code=role_code,
            assigned_by_user_id=assigned_by_user_id,
            stage_id=stage_id,
            notes=notes
        )
        
        # Publish event
        event = StaffAssignedToTournamentEvent(
            assignment_id=assignment.assignment_id,
            tournament_id=assignment.tournament_id,
            tournament_name=assignment.tournament_name,
            user_id=assignment.user_id,
            username=assignment.username,
            role_code=assignment.role.code,
            role_name=assignment.role.name,
            stage_id=assignment.stage_id,
            stage_name=assignment.stage_name,
            assigned_by_user_id=assignment.assigned_by_user_id or 0,
            assigned_by_username=assignment.assigned_by_username or "System",
            assigned_at=assignment.assigned_at
        )
        self.event_bus.publish(event)
        _publish_staff_event_to_core(
            "staff.assigned_to_tournament",
            assignment_id=assignment.assignment_id,
            tournament_id=assignment.tournament_id,
            user_id=assignment.user_id,
            role_code=assignment.role.code,
        )
        
        return assignment
    
    def remove_staff_from_tournament(
        self,
        assignment_id: int
    ) -> TournamentStaffAssignmentDTO:
        """
        Remove a staff member from a tournament (set inactive).
        
        Business Rules:
        - Assignment must exist
        - Cannot remove staff with pending referee assignments
        
        Args:
            assignment_id: Staff assignment ID to remove
            
        Returns:
            Updated TournamentStaffAssignmentDTO
            
        Raises:
            ValueError: If validation fails
        """
        # Get current assignment
        assignment = self.staffing_adapter.get_staff_assignment_by_id(
            assignment_id
        )
        if not assignment:
            raise ValueError(f"Staff assignment not found: {assignment_id}")
        
        # Check for active referee assignments if this is a referee role
        if assignment.is_referee_assignment():
            # Get referee assignments for this tournament
            referee_assignments = self.staffing_adapter.get_referee_assignments_for_tournament(
                tournament_id=assignment.tournament_id
            )
            
            # Filter to this staff assignment
            active_ref_assignments = [
                ra for ra in referee_assignments
                if ra.staff_assignment.assignment_id == assignment_id
            ]
            
            if active_ref_assignments:
                raise ValueError(
                    f"Cannot remove staff with {len(active_ref_assignments)} "
                    f"active referee assignments. Unassign from matches first."
                )
        
        # Update to inactive
        updated = self.staffing_adapter.update_staff_assignment_status(
            assignment_id=assignment_id,
            is_active=False
        )
        
        # Publish event
        event = StaffRemovedFromTournamentEvent(
            assignment_id=updated.assignment_id,
            tournament_id=updated.tournament_id,
            tournament_name=updated.tournament_name,
            user_id=updated.user_id,
            username=updated.username,
            role_code=updated.role.code,
            role_name=updated.role.name,
            removed_at=datetime.now()
        )
        self.event_bus.publish(event)
        _publish_staff_event_to_core(
            "staff.removed_from_tournament",
            assignment_id=updated.assignment_id,
            tournament_id=updated.tournament_id,
            user_id=updated.user_id,
            role_code=updated.role.code,
        )
        
        return updated
    
    def get_tournament_staff(
        self,
        tournament_id: int,
        stage_id: Optional[int] = None,
        role_code: Optional[str] = None,
        is_active: Optional[bool] = True
    ) -> List[TournamentStaffAssignmentDTO]:
        """
        Get all staff assigned to a tournament.
        
        Args:
            tournament_id: Tournament ID
            stage_id: Optional stage ID filter
            role_code: Optional role code filter
            is_active: Optional active status filter
            
        Returns:
            List of TournamentStaffAssignmentDTO objects
        """
        return self.staffing_adapter.get_staff_assignments_for_tournament(
            tournament_id=tournament_id,
            is_active=is_active,
            stage_id=stage_id,
            role_code=role_code
        )
    
    # --------------------------------------------------
    # Match Referee Assignment
    # --------------------------------------------------
    
    def assign_referee_to_match(
        self,
        match_id: int,
        staff_assignment_id: int,
        assigned_by_user_id: int,
        is_primary: bool = False,
        notes: str = "",
        check_load: bool = True
    ) -> tuple[MatchRefereeAssignmentDTO, Optional[str]]:
        """
        Assign a referee to a match.
        
        Business Rules:
        - Staff assignment must be a referee role
        - Staff assignment must be active
        - Staff assignment must belong to same tournament
        - Soft warning if referee is overloaded
        
        Args:
            match_id: Match ID
            staff_assignment_id: Staff assignment ID (must be referee)
            assigned_by_user_id: User ID who made the assignment
            is_primary: Whether this is the primary referee
            notes: Optional notes
            check_load: Whether to check referee load and warn if overloaded
            
        Returns:
            Tuple of (MatchRefereeAssignmentDTO, optional warning message)
            
        Raises:
            ValueError: If validation fails
        """
        # Validate staff assignment
        staff_assignment = self.staffing_adapter.get_staff_assignment_by_id(
            staff_assignment_id
        )
        if not staff_assignment:
            raise ValueError(
                f"Staff assignment not found: {staff_assignment_id}"
            )
        
        if not staff_assignment.is_referee_assignment():
            raise ValueError(
                f"Staff assignment {staff_assignment_id} is not a referee role"
            )
        
        if not staff_assignment.is_active:
            raise ValueError(
                f"Staff assignment {staff_assignment_id} is inactive"
            )
        
        # Check load (soft warning, doesn't block)
        warning = None
        if check_load:
            load = self._get_staff_load(staff_assignment_id)
            if load and load.is_overloaded:
                warning = (
                    f"Warning: {staff_assignment.username} is currently "
                    f"overloaded ({load.load_percentage:.0f}% capacity, "
                    f"{load.upcoming_matches} upcoming matches)"
                )
        
        # Create assignment via adapter
        assignment = self.staffing_adapter.assign_referee_to_match(
            match_id=match_id,
            staff_assignment_id=staff_assignment_id,
            assigned_by_user_id=assigned_by_user_id,
            is_primary=is_primary,
            notes=notes
        )
        
        # Publish event
        event = RefereeAssignedToMatchEvent(
            referee_assignment_id=assignment.assignment_id,
            match_id=assignment.match_id,
            tournament_id=assignment.tournament_id,
            stage_id=assignment.stage_id,
            round_number=assignment.round_number,
            match_number=assignment.match_number,
            staff_assignment_id=assignment.staff_assignment.assignment_id,
            user_id=assignment.staff_assignment.user_id,
            username=assignment.staff_assignment.username,
            is_primary=assignment.is_primary,
            assigned_by_user_id=assignment.assigned_by_user_id or 0,
            assigned_by_username=assignment.assigned_by_username or "System",
            assigned_at=assignment.assigned_at
        )
        self.event_bus.publish(event)
        _publish_staff_event_to_core(
            "referee.assigned_to_match",
            match_id=assignment.match_id,
            tournament_id=assignment.tournament_id,
            user_id=assignment.staff_assignment.user_id,
            is_primary=assignment.is_primary,
        )
        
        return assignment, warning
    
    def unassign_referee_from_match(
        self,
        referee_assignment_id: int
    ) -> None:
        """
        Remove a referee from a match.
        
        Args:
            referee_assignment_id: Referee assignment ID to remove
            
        Raises:
            ValueError: If assignment not found
        """
        # Get assignment details before deleting (for event)
        referee_assignments = self.staffing_adapter.get_referee_assignments_for_tournament(
            tournament_id=0  # Will filter in memory
        )
        
        assignment = None
        for ra in referee_assignments:
            if ra.assignment_id == referee_assignment_id:
                assignment = ra
                break
        
        if not assignment:
            raise ValueError(
                f"Referee assignment not found: {referee_assignment_id}"
            )
        
        # Delete via adapter
        self.staffing_adapter.unassign_referee_from_match(
            referee_assignment_id
        )
        
        # Publish event
        event = RefereeUnassignedFromMatchEvent(
            referee_assignment_id=assignment.assignment_id,
            match_id=assignment.match_id,
            tournament_id=assignment.tournament_id,
            user_id=assignment.staff_assignment.user_id,
            username=assignment.staff_assignment.username,
            was_primary=assignment.is_primary,
            unassigned_at=datetime.now()
        )
        self.event_bus.publish(event)
        _publish_staff_event_to_core(
            "referee.unassigned_from_match",
            match_id=assignment.match_id,
            tournament_id=assignment.tournament_id,
            user_id=assignment.staff_assignment.user_id,
            was_primary=assignment.is_primary,
        )
    
    def get_match_referees(
        self,
        match_id: int
    ) -> List[MatchRefereeAssignmentDTO]:
        """
        Get all referees assigned to a match.
        
        Args:
            match_id: Match ID
            
        Returns:
            List of MatchRefereeAssignmentDTO objects (primary first)
        """
        return self.staffing_adapter.get_referee_assignments_for_match(
            match_id
        )
    
    def get_tournament_referee_assignments(
        self,
        tournament_id: int,
        stage_id: Optional[int] = None
    ) -> List[MatchRefereeAssignmentDTO]:
        """
        Get all referee assignments for a tournament.
        
        Args:
            tournament_id: Tournament ID
            stage_id: Optional stage ID filter
            
        Returns:
            List of MatchRefereeAssignmentDTO objects
        """
        return self.staffing_adapter.get_referee_assignments_for_tournament(
            tournament_id=tournament_id,
            stage_id=stage_id
        )
    
    # --------------------------------------------------
    # Staff Load Management
    # --------------------------------------------------
    
    def calculate_staff_load(
        self,
        tournament_id: int,
        stage_id: Optional[int] = None
    ) -> List[StaffLoadDTO]:
        """
        Calculate workload for all staff in a tournament.
        
        Args:
            tournament_id: Tournament ID
            stage_id: Optional stage ID filter
            
        Returns:
            List of StaffLoadDTO objects, sorted by load descending
        """
        return self.staffing_adapter.calculate_staff_load(
            tournament_id=tournament_id,
            stage_id=stage_id
        )
    
    def _get_staff_load(
        self,
        staff_assignment_id: int
    ) -> Optional[StaffLoadDTO]:
        """
        Get load for a specific staff assignment.
        
        Args:
            staff_assignment_id: Staff assignment ID
            
        Returns:
            StaffLoadDTO if found, None otherwise
        """
        # Get staff assignment to get tournament
        staff_assignment = self.staffing_adapter.get_staff_assignment_by_id(
            staff_assignment_id
        )
        if not staff_assignment:
            return None
        
        # Calculate load for tournament
        loads = self.staffing_adapter.calculate_staff_load(
            tournament_id=staff_assignment.tournament_id
        )
        
        # Find this specific staff member
        for load in loads:
            if load.staff_assignment.assignment_id == staff_assignment_id:
                return load
        
        return None
    
    def get_least_loaded_referee(
        self,
        tournament_id: int,
        stage_id: Optional[int] = None,
        capability: Optional[str] = None
    ) -> Optional[TournamentStaffAssignmentDTO]:
        """
        Find the least loaded referee for load balancing.
        
        Args:
            tournament_id: Tournament ID
            stage_id: Optional stage ID filter
            capability: Optional capability requirement
            
        Returns:
            TournamentStaffAssignmentDTO with lowest load, or None
        """
        loads = self.staffing_adapter.calculate_staff_load(
            tournament_id=tournament_id,
            stage_id=stage_id
        )
        
        # Filter by capability if specified
        if capability:
            loads = [
                load for load in loads
                if load.staff_assignment.can_perform(capability)
            ]
        
        if not loads:
            return None
        
        # Sort by load ascending and return first
        loads.sort(key=lambda x: x.load_percentage)
        return loads[0].staff_assignment
