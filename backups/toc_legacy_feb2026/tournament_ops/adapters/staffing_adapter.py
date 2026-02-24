"""
Staffing Adapter - Phase 7, Epic 7.3

Adapter for staff and referee management data access.

Architecture:
- Method-level ORM imports only
- Translates between ORM models and DTOs
- No business logic (pure data access)

Reference: Phase 7, Epic 7.3 - Staff & Referee Role System
"""

from typing import List, Optional
from datetime import datetime

from apps.tournament_ops.dtos.staffing import (
    StaffRoleDTO,
    TournamentStaffAssignmentDTO,
    MatchRefereeAssignmentDTO,
    StaffLoadDTO,
)


class StaffingAdapter:
    """
    Adapter for staff and referee data access.
    
    Provides CRUD operations and queries for staff roles,
    tournament staff assignments, and match referee assignments.
    
    Reference: Phase 7, Epic 7.3 - Staffing Adapter Layer
    """
    
    def get_staff_roles(
        self,
        is_referee_role: Optional[bool] = None
    ) -> List[StaffRoleDTO]:
        """
        Get all staff roles, optionally filtered by referee role flag.
        
        Args:
            is_referee_role: If specified, filter by referee role flag
            
        Returns:
            List of StaffRoleDTO objects
        """
        from apps.tournaments.models import StaffRole
        
        queryset = StaffRole.objects.all()
        
        if is_referee_role is not None:
            queryset = queryset.filter(is_referee_role=is_referee_role)
        
        queryset = queryset.order_by('name')
        
        return [StaffRoleDTO.from_model(role) for role in queryset]
    
    def get_staff_role_by_code(self, role_code: str) -> Optional[StaffRoleDTO]:
        """
        Get a staff role by its unique code.
        
        Args:
            role_code: Unique role code
            
        Returns:
            StaffRoleDTO if found, None otherwise
        """
        from apps.tournaments.models import StaffRole
        
        try:
            role = StaffRole.objects.get(code=role_code)
            return StaffRoleDTO.from_model(role)
        except StaffRole.DoesNotExist:
            return None
    
    def get_staff_assignments_for_tournament(
        self,
        tournament_id: int,
        is_active: Optional[bool] = True,
        stage_id: Optional[int] = None,
        role_code: Optional[str] = None
    ) -> List[TournamentStaffAssignmentDTO]:
        """
        Get all staff assignments for a tournament.
        
        Args:
            tournament_id: Tournament ID
            is_active: If specified, filter by active status
            stage_id: If specified, filter by stage
            role_code: If specified, filter by role code
            
        Returns:
            List of TournamentStaffAssignmentDTO objects
        """
        from apps.tournaments.models import TournamentStaffAssignment
        
        queryset = TournamentStaffAssignment.objects.filter(
            tournament_id=tournament_id
        ).select_related(
            'tournament',
            'user',
            'role',
            'stage',
            'assigned_by'
        )
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        if stage_id is not None:
            queryset = queryset.filter(stage_id=stage_id)
        
        if role_code is not None:
            queryset = queryset.filter(role__code=role_code)
        
        queryset = queryset.order_by('-assigned_at')
        
        return [
            TournamentStaffAssignmentDTO.from_model(assignment)
            for assignment in queryset
        ]
    
    def get_staff_assignment_by_id(
        self,
        assignment_id: int
    ) -> Optional[TournamentStaffAssignmentDTO]:
        """
        Get a staff assignment by ID.
        
        Args:
            assignment_id: Assignment ID
            
        Returns:
            TournamentStaffAssignmentDTO if found, None otherwise
        """
        from apps.tournaments.models import TournamentStaffAssignment
        
        try:
            assignment = TournamentStaffAssignment.objects.select_related(
                'tournament',
                'user',
                'role',
                'stage',
                'assigned_by'
            ).get(id=assignment_id)
            return TournamentStaffAssignmentDTO.from_model(assignment)
        except TournamentStaffAssignment.DoesNotExist:
            return None
    
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
        Create a new staff assignment to a tournament.
        
        Args:
            tournament_id: Tournament ID
            user_id: User ID to assign
            role_code: Role code to assign
            assigned_by_user_id: User ID who made the assignment
            stage_id: Optional stage ID for stage-specific assignment
            notes: Optional notes about the assignment
            
        Returns:
            TournamentStaffAssignmentDTO
            
        Raises:
            ValueError: If role not found or validation fails
        """
        from apps.tournaments.models import (
            StaffRole,
            TournamentStaffAssignment,
        )
        from django.db import IntegrityError
        
        # Get role
        try:
            role = StaffRole.objects.get(code=role_code)
        except StaffRole.DoesNotExist:
            raise ValueError(f"Staff role not found: {role_code}")
        
        # Create assignment
        try:
            assignment = TournamentStaffAssignment.objects.create(
                tournament_id=tournament_id,
                user_id=user_id,
                role=role,
                stage_id=stage_id,
                assigned_by_id=assigned_by_user_id,
                assigned_at=datetime.now(),
                is_active=True,
                notes=notes
            )
        except IntegrityError as e:
            if 'unique' in str(e).lower():
                raise ValueError(
                    f"User {user_id} already assigned to role {role_code} "
                    f"in tournament {tournament_id}"
                )
            raise
        
        # Reload with related objects
        assignment.refresh_from_db()
        assignment = TournamentStaffAssignment.objects.select_related(
            'tournament',
            'user',
            'role',
            'stage',
            'assigned_by'
        ).get(id=assignment.id)
        
        return TournamentStaffAssignmentDTO.from_model(assignment)
    
    def update_staff_assignment_status(
        self,
        assignment_id: int,
        is_active: bool
    ) -> TournamentStaffAssignmentDTO:
        """
        Update staff assignment active status.
        
        Args:
            assignment_id: Assignment ID
            is_active: New active status
            
        Returns:
            Updated TournamentStaffAssignmentDTO
            
        Raises:
            ValueError: If assignment not found
        """
        from apps.tournaments.models import TournamentStaffAssignment
        
        try:
            assignment = TournamentStaffAssignment.objects.select_related(
                'tournament',
                'user',
                'role',
                'stage',
                'assigned_by'
            ).get(id=assignment_id)
        except TournamentStaffAssignment.DoesNotExist:
            raise ValueError(f"Staff assignment not found: {assignment_id}")
        
        assignment.is_active = is_active
        assignment.save(update_fields=['is_active', 'updated_at'])
        
        return TournamentStaffAssignmentDTO.from_model(assignment)
    
    def get_referee_assignments_for_tournament(
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
        from apps.tournaments.models import MatchRefereeAssignment
        
        queryset = MatchRefereeAssignment.objects.filter(
            match__tournament_id=tournament_id
        ).select_related(
            'match',
            'staff_assignment__tournament',
            'staff_assignment__user',
            'staff_assignment__role',
            'staff_assignment__stage',
            'staff_assignment__assigned_by',
            'assigned_by'
        )
        
        if stage_id is not None:
            queryset = queryset.filter(match__stage_id=stage_id)
        
        queryset = queryset.order_by('-assigned_at')
        
        return [
            MatchRefereeAssignmentDTO.from_model(assignment)
            for assignment in queryset
        ]
    
    def get_referee_assignments_for_match(
        self,
        match_id: int
    ) -> List[MatchRefereeAssignmentDTO]:
        """
        Get all referee assignments for a specific match.
        
        Args:
            match_id: Match ID
            
        Returns:
            List of MatchRefereeAssignmentDTO objects (primary referee first)
        """
        from apps.tournaments.models import MatchRefereeAssignment
        
        queryset = MatchRefereeAssignment.objects.filter(
            match_id=match_id
        ).select_related(
            'match',
            'staff_assignment__tournament',
            'staff_assignment__user',
            'staff_assignment__role',
            'staff_assignment__stage',
            'staff_assignment__assigned_by',
            'assigned_by'
        ).order_by('-is_primary', '-assigned_at')
        
        return [
            MatchRefereeAssignmentDTO.from_model(assignment)
            for assignment in queryset
        ]
    
    def assign_referee_to_match(
        self,
        match_id: int,
        staff_assignment_id: int,
        assigned_by_user_id: int,
        is_primary: bool = False,
        notes: str = ""
    ) -> MatchRefereeAssignmentDTO:
        """
        Assign a referee to a match.
        
        Args:
            match_id: Match ID
            staff_assignment_id: Staff assignment ID (must be referee role)
            assigned_by_user_id: User ID who made the assignment
            is_primary: Whether this is the primary referee
            notes: Optional notes
            
        Returns:
            MatchRefereeAssignmentDTO
            
        Raises:
            ValueError: If assignment not found or validation fails
        """
        from apps.tournaments.models import (
            MatchRefereeAssignment,
            TournamentStaffAssignment,
        )
        from django.db import IntegrityError
        
        # Verify staff assignment exists and is a referee
        try:
            staff_assignment = TournamentStaffAssignment.objects.select_related(
                'role'
            ).get(id=staff_assignment_id)
        except TournamentStaffAssignment.DoesNotExist:
            raise ValueError(
                f"Staff assignment not found: {staff_assignment_id}"
            )
        
        if not staff_assignment.role.is_referee_role:
            raise ValueError(
                f"Staff assignment {staff_assignment_id} is not a referee role"
            )
        
        # Create referee assignment
        try:
            referee_assignment = MatchRefereeAssignment.objects.create(
                match_id=match_id,
                staff_assignment=staff_assignment,
                assigned_by_id=assigned_by_user_id,
                is_primary=is_primary,
                assigned_at=datetime.now(),
                notes=notes
            )
        except IntegrityError as e:
            if 'unique' in str(e).lower():
                raise ValueError(
                    f"Staff already assigned as referee to match {match_id}"
                )
            raise
        
        # Reload with related objects
        referee_assignment.refresh_from_db()
        referee_assignment = MatchRefereeAssignment.objects.select_related(
            'match',
            'staff_assignment__tournament',
            'staff_assignment__user',
            'staff_assignment__role',
            'staff_assignment__stage',
            'staff_assignment__assigned_by',
            'assigned_by'
        ).get(id=referee_assignment.id)
        
        return MatchRefereeAssignmentDTO.from_model(referee_assignment)
    
    def unassign_referee_from_match(
        self,
        referee_assignment_id: int
    ) -> None:
        """
        Remove a referee assignment from a match.
        
        Args:
            referee_assignment_id: Referee assignment ID to remove
            
        Raises:
            ValueError: If assignment not found
        """
        from apps.tournaments.models import MatchRefereeAssignment
        
        try:
            assignment = MatchRefereeAssignment.objects.get(
                id=referee_assignment_id
            )
            assignment.delete()
        except MatchRefereeAssignment.DoesNotExist:
            raise ValueError(
                f"Referee assignment not found: {referee_assignment_id}"
            )
    
    def calculate_staff_load(
        self,
        tournament_id: int,
        stage_id: Optional[int] = None
    ) -> List[StaffLoadDTO]:
        """
        Calculate workload for all staff assigned to a tournament.
        
        Aggregates match assignments to determine staff load.
        
        Args:
            tournament_id: Tournament ID
            stage_id: Optional stage ID filter
            
        Returns:
            List of StaffLoadDTO objects
        """
        from apps.tournaments.models import (
            TournamentStaffAssignment,
            MatchRefereeAssignment,
        )
        from django.db.models import Count, Q
        
        # Get all referee staff assignments
        queryset = TournamentStaffAssignment.objects.filter(
            tournament_id=tournament_id,
            is_active=True,
            role__is_referee_role=True
        ).select_related(
            'tournament',
            'user',
            'role',
            'stage',
            'assigned_by'
        )
        
        if stage_id is not None:
            queryset = queryset.filter(
                Q(stage_id=stage_id) | Q(stage_id__isnull=True)
            )
        
        load_dtos = []
        
        for staff_assignment in queryset:
            # Count match assignments
            match_assignments = MatchRefereeAssignment.objects.filter(
                staff_assignment=staff_assignment
            ).select_related('match')
            
            if stage_id is not None:
                match_assignments = match_assignments.filter(
                    match__stage_id=stage_id
                )
            
            total_matches = match_assignments.count()
            
            # Count by match status
            upcoming = match_assignments.filter(
                match__status__in=['SCHEDULED', 'READY']
            ).count()
            
            completed = match_assignments.filter(
                match__status__in=['COMPLETED', 'VERIFIED']
            ).count()
            
            # Simplified concurrent calculation (would need time-based overlap in production)
            concurrent = 0  # Placeholder - requires match scheduling times
            
            # Calculate load percentage (assuming max 10 matches as baseline)
            max_recommended = 10
            load_percentage = min(100.0, (total_matches / max_recommended) * 100)
            is_overloaded = load_percentage > 80
            
            load_dto = StaffLoadDTO(
                staff_assignment=TournamentStaffAssignmentDTO.from_model(
                    staff_assignment
                ),
                total_matches_assigned=total_matches,
                upcoming_matches=upcoming,
                completed_matches=completed,
                concurrent_matches=concurrent,
                is_overloaded=is_overloaded,
                load_percentage=load_percentage
            )
            
            load_dtos.append(load_dto)
        
        # Sort by load percentage descending
        load_dtos.sort(key=lambda x: x.load_percentage, reverse=True)
        
        return load_dtos
