"""
Match Operations Adapter - Phase 7, Epic 7.4

Provides data access layer for Match Operations Command Center (MOCC).

Architecture:
- Method-level ORM imports only (no module-level Django imports)
- Returns DTOs (no raw Django models leak out)
- Thin data access layer (business logic in service)

Reference: Phase 7, Epic 7.4 - Match Operations Command Center
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from ..dtos import (
    MatchOperationLogDTO,
    MatchModeratorNoteDTO,
    MatchOpsActionResultDTO,
    MatchOpsPermissionDTO,
)


class MatchOpsAdapter:
    """
    Adapter for match operations data access.
    
    Handles:
    - Operation log CRUD
    - Moderator note CRUD
    - Match state queries/updates
    - Permission checks
    
    Reference: Phase 7, Epic 7.4 - MOCC Data Layer
    """
    
    def get_match_state(self, match_id: int) -> str:
        """
        Get current state of a match.
        
        Args:
            match_id: Match identifier
            
        Returns:
            str: Match status (e.g., "PENDING", "LIVE", "COMPLETED")
            
        Raises:
            ValueError: If match not found
        """
        from apps.tournaments.models import Match
        
        try:
            match = Match.objects.get(id=match_id)
            return match.status
        except Match.DoesNotExist:
            raise ValueError(f"Match {match_id} not found")
    
    def set_match_state(
        self,
        match_id: int,
        new_state: str,
        operator_user_id: int
    ) -> None:
        """
        Update match state.
        
        Args:
            match_id: Match identifier
            new_state: New status value
            operator_user_id: User performing the operation
            
        Raises:
            ValueError: If match not found or invalid state
        """
        from apps.tournaments.models import Match
        
        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            raise ValueError(f"Match {match_id} not found")
        
        # Validate state
        valid_states = ['PENDING', 'LIVE', 'PAUSED', 'COMPLETED', 'CANCELLED']
        if new_state not in valid_states:
            raise ValueError(f"Invalid state: {new_state}")
        
        match.status = new_state
        match.save(update_fields=['status'])
    
    def add_operation_log(
        self,
        match_id: int,
        operator_user_id: int,
        operation_type: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> MatchOperationLogDTO:
        """
        Create a new operation log entry.
        
        Args:
            match_id: Match identifier
            operator_user_id: User performing operation
            operation_type: Type of operation (LIVE, PAUSED, etc.)
            payload: Optional metadata
            
        Returns:
            MatchOperationLogDTO: Created log entry
            
        Raises:
            ValueError: If match not found or invalid operation type
        """
        from apps.tournaments.models import Match, MatchOperationLog
        
        # Verify match exists
        try:
            Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            raise ValueError(f"Match {match_id} not found")
        
        # Create log
        log = MatchOperationLog.objects.create(
            match_id=match_id,
            operator_user_id=operator_user_id,
            operation_type=operation_type,
            payload=payload or {}
        )
        
        return MatchOperationLogDTO.from_model(log)
    
    def list_operation_logs(
        self,
        match_id: int,
        limit: int = 100
    ) -> List[MatchOperationLogDTO]:
        """
        Get operation logs for a match.
        
        Args:
            match_id: Match identifier
            limit: Maximum number of logs to return
            
        Returns:
            List[MatchOperationLogDTO]: Ordered by created_at DESC
        """
        from apps.tournaments.models import MatchOperationLog
        
        logs = MatchOperationLog.objects.filter(
            match_id=match_id
        ).order_by('-created_at')[:limit]
        
        return [MatchOperationLogDTO.from_model(log) for log in logs]
    
    def add_moderator_note(
        self,
        match_id: int,
        author_user_id: int,
        content: str
    ) -> MatchModeratorNoteDTO:
        """
        Add a moderator note to a match.
        
        Args:
            match_id: Match identifier
            author_user_id: User creating the note
            content: Note content
            
        Returns:
            MatchModeratorNoteDTO: Created note
            
        Raises:
            ValueError: If match not found or content empty
        """
        from apps.tournaments.models import Match, MatchModeratorNote
        
        if not content or not content.strip():
            raise ValueError("Note content cannot be empty")
        
        # Verify match exists
        try:
            Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            raise ValueError(f"Match {match_id} not found")
        
        # Create note
        note = MatchModeratorNote.objects.create(
            match_id=match_id,
            author_user_id=author_user_id,
            content=content.strip()
        )
        
        return MatchModeratorNoteDTO.from_model(note)
    
    def list_moderator_notes(
        self,
        match_id: int
    ) -> List[MatchModeratorNoteDTO]:
        """
        Get moderator notes for a match.
        
        Args:
            match_id: Match identifier
            
        Returns:
            List[MatchModeratorNoteDTO]: Ordered by created_at ASC
        """
        from apps.tournaments.models import MatchModeratorNote
        
        notes = MatchModeratorNote.objects.filter(
            match_id=match_id
        ).order_by('created_at')
        
        return [MatchModeratorNoteDTO.from_model(note) for note in notes]
    
    def get_match_result(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current result for a match.
        
        Args:
            match_id: Match identifier
            
        Returns:
            Optional[Dict[str, Any]]: Result data if exists, None otherwise
        """
        from apps.tournaments.models import Match
        
        try:
            match = Match.objects.get(id=match_id)
            if not match.result_data:
                return None
            return match.result_data
        except Match.DoesNotExist:
            raise ValueError(f"Match {match_id} not found")
    
    def override_match_result(
        self,
        match_id: int,
        new_result_data: Dict[str, Any],
        operator_user_id: int
    ) -> MatchOpsActionResultDTO:
        """
        Override match result (admin action).
        
        Args:
            match_id: Match identifier
            new_result_data: New result payload
            operator_user_id: User performing override
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            ValueError: If match not found
        """
        from apps.tournaments.models import Match, MatchOperationLog
        
        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            raise ValueError(f"Match {match_id} not found")
        
        # Store old result in log payload
        old_result = match.result_data
        
        # Update result
        match.result_data = new_result_data
        match.status = 'COMPLETED'
        match.save(update_fields=['result_data', 'status'])
        
        # Log operation
        log = MatchOperationLog.objects.create(
            match_id=match_id,
            operator_user_id=operator_user_id,
            operation_type='OVERRIDE_RESULT',
            payload={
                'old_result': old_result,
                'new_result': new_result_data,
            }
        )
        
        return MatchOpsActionResultDTO(
            success=True,
            message="Match result overridden successfully",
            match_id=match_id,
            new_state='COMPLETED',
            operation_log=MatchOperationLogDTO.from_model(log),
            warnings=[]
        )
    
    def get_match_permissions(
        self,
        user_id: int,
        tournament_id: int,
        match_id: Optional[int] = None
    ) -> MatchOpsPermissionDTO:
        """
        Get user's match operations permissions.
        
        Uses StaffingAdapter to check role-based permissions.
        
        Args:
            user_id: User identifier
            tournament_id: Tournament identifier
            match_id: Optional specific match
            
        Returns:
            MatchOpsPermissionDTO: Permission flags
        """
        from apps.tournament_ops.adapters import StaffingAdapter
        
        staffing_adapter = StaffingAdapter()
        
        # Check if user is tournament staff
        assignments = staffing_adapter.list_tournament_staff(tournament_id)
        user_assignment = next(
            (a for a in assignments if a.user_id == user_id),
            None
        )
        
        # Check if user is match referee
        is_referee = False
        if match_id:
            referee_assignment = staffing_adapter.get_match_referee_assignment(match_id)
            if referee_assignment and referee_assignment.referee_user_id == user_id:
                is_referee = True
        
        # Permission logic based on role
        if user_assignment:
            role_permissions = user_assignment.permissions
            
            return MatchOpsPermissionDTO(
                user_id=user_id,
                tournament_id=tournament_id,
                match_id=match_id,
                can_mark_live=role_permissions.can_modify_matches,
                can_pause=role_permissions.can_modify_matches,
                can_resume=role_permissions.can_modify_matches,
                can_force_complete=role_permissions.can_modify_matches,
                can_override_result=role_permissions.can_modify_matches,
                can_add_note=role_permissions.can_add_notes,
                can_assign_referee=role_permissions.can_assign_referees,
                is_referee=is_referee,
                is_admin=user_assignment.role == 'ADMIN'
            )
        
        # Default: no permissions
        return MatchOpsPermissionDTO(
            user_id=user_id,
            tournament_id=tournament_id,
            match_id=match_id,
            can_mark_live=False,
            can_pause=False,
            can_resume=False,
            can_force_complete=False,
            can_override_result=False,
            can_add_note=False,
            can_assign_referee=False,
            is_referee=is_referee,
            is_admin=False
        )
    
    def get_matches_by_tournament(
        self,
        tournament_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get matches for tournament (for dashboard).
        
        Args:
            tournament_id: Tournament identifier
            status_filter: Optional status filter
            
        Returns:
            List[Dict[str, Any]]: Match data with related info
        """
        from apps.tournaments.models import Match
        
        queryset = Match.objects.filter(
            stage__tournament_id=tournament_id
        ).select_related('stage')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        matches = []
        for match in queryset:
            matches.append({
                'match_id': match.id,
                'tournament_id': tournament_id,
                'stage_id': match.stage_id,
                'stage_name': match.stage.name,
                'round_number': match.round_number,
                'match_number': match.match_number,
                'status': match.status,
                'scheduled_time': match.scheduled_time,
                'team1_id': match.team1_id,
                'team2_id': match.team2_id,
            })
        
        return matches
    
    def count_moderator_notes(self, match_id: int) -> int:
        """
        Count moderator notes for a match.
        
        Args:
            match_id: Match identifier
            
        Returns:
            int: Number of notes
        """
        from apps.tournaments.models import MatchModeratorNote
        
        return MatchModeratorNote.objects.filter(match_id=match_id).count()
    
    def get_last_operation(self, match_id: int) -> Optional[MatchOperationLogDTO]:
        """
        Get most recent operation for a match.
        
        Args:
            match_id: Match identifier
            
        Returns:
            Optional[MatchOperationLogDTO]: Last operation or None
        """
        from apps.tournaments.models import MatchOperationLog
        
        log = MatchOperationLog.objects.filter(
            match_id=match_id
        ).order_by('-created_at').first()
        
        if log:
            return MatchOperationLogDTO.from_model(log)
        return None
