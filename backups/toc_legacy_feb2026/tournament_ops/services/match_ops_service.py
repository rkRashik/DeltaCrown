"""
Match Operations Service - Phase 7, Epic 7.4

Orchestrates match operations for referees/admins.

Architecture:
- Pure orchestration (no ORM imports)
- Uses MatchOpsAdapter for data access
- Publishes domain events
- Enforces business rules and permissions

Reference: Phase 7, Epic 7.4 - Match Operations Command Center
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from ..adapters import MatchOpsAdapter, StaffingAdapter
from ..dtos import (
    MatchOperationLogDTO,
    MatchModeratorNoteDTO,
    MatchOpsActionResultDTO,
    MatchOpsPermissionDTO,
    MatchTimelineEventDTO,
    MatchOpsDashboardItemDTO,
)
from ..events import (
    MatchWentLiveEvent,
    MatchPausedEvent,
    MatchResumedEvent,
    MatchForceCompletedEvent,
    MatchOperatorNoteAddedEvent,
    MatchResultOverriddenEvent,
)


class MatchOpsService:
    """
    Service for Match Operations Command Center.
    
    Provides:
    - Live match control (mark live, pause, resume)
    - Force completion
    - Result overrides
    - Moderator notes
    - Operations timeline
    - Permission checks
    
    Reference: Phase 7, Epic 7.4 - MOCC Service Layer
    """
    
    def __init__(
        self,
        match_ops_adapter: Optional[MatchOpsAdapter] = None,
        staffing_adapter: Optional[StaffingAdapter] = None,
        event_publisher=None
    ):
        """
        Initialize service.
        
        Args:
            match_ops_adapter: Data access adapter
            staffing_adapter: Staffing data adapter
            event_publisher: Optional event publisher
        """
        self.match_ops_adapter = match_ops_adapter or MatchOpsAdapter()
        self.staffing_adapter = staffing_adapter or StaffingAdapter()
        self.event_publisher = event_publisher
    
    def mark_match_live(
        self,
        match_id: int,
        tournament_id: int,
        operator_user_id: int
    ) -> MatchOpsActionResultDTO:
        """
        Mark a match as LIVE (in progress).
        
        Business Rules:
        - User must have can_modify_matches permission
        - Match must be in PENDING status
        - Logs operation and publishes event
        
        Args:
            match_id: Match identifier
            tournament_id: Tournament identifier
            operator_user_id: User performing operation
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If match not in valid state
        """
        # Check permissions
        permissions = self.match_ops_adapter.get_match_permissions(
            operator_user_id, tournament_id, match_id
        )
        if not permissions.can_mark_live:
            raise PermissionError("User lacks permission to mark match live")
        
        # Check current state
        current_state = self.match_ops_adapter.get_match_state(match_id)
        if current_state not in ['PENDING', 'PAUSED']:
            raise ValueError(f"Cannot mark match live from state: {current_state}")
        
        # Update state
        self.match_ops_adapter.set_match_state(match_id, 'LIVE', operator_user_id)
        
        # Log operation
        operation_log = self.match_ops_adapter.add_operation_log(
            match_id=match_id,
            operator_user_id=operator_user_id,
            operation_type='LIVE',
            payload={'previous_state': current_state}
        )
        
        # Publish event
        if self.event_publisher:
            event = MatchWentLiveEvent(
                match_id=match_id,
                tournament_id=tournament_id,
                operator_user_id=operator_user_id,
                timestamp=datetime.utcnow(),
                previous_state=current_state
            )
            self.event_publisher.publish(event)
        
        return MatchOpsActionResultDTO(
            success=True,
            message="Match marked as LIVE",
            match_id=match_id,
            new_state='LIVE',
            operation_log=operation_log,
            warnings=[]
        )
    
    def pause_match(
        self,
        match_id: int,
        tournament_id: int,
        operator_user_id: int,
        reason: Optional[str] = None
    ) -> MatchOpsActionResultDTO:
        """
        Pause a live match.
        
        Business Rules:
        - User must have can_pause permission
        - Match must be in LIVE status
        - Reason is recommended but optional
        
        Args:
            match_id: Match identifier
            tournament_id: Tournament identifier
            operator_user_id: User performing operation
            reason: Optional pause reason
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If match not in LIVE state
        """
        # Check permissions
        permissions = self.match_ops_adapter.get_match_permissions(
            operator_user_id, tournament_id, match_id
        )
        if not permissions.can_pause:
            raise PermissionError("User lacks permission to pause match")
        
        # Check current state
        current_state = self.match_ops_adapter.get_match_state(match_id)
        if current_state != 'LIVE':
            raise ValueError(f"Cannot pause match in state: {current_state}")
        
        # Update state
        self.match_ops_adapter.set_match_state(match_id, 'PAUSED', operator_user_id)
        
        # Log operation
        operation_log = self.match_ops_adapter.add_operation_log(
            match_id=match_id,
            operator_user_id=operator_user_id,
            operation_type='PAUSED',
            payload={'reason': reason}
        )
        
        # Publish event
        if self.event_publisher:
            event = MatchPausedEvent(
                match_id=match_id,
                tournament_id=tournament_id,
                operator_user_id=operator_user_id,
                timestamp=datetime.utcnow(),
                reason=reason
            )
            self.event_publisher.publish(event)
        
        warnings = []
        if not reason:
            warnings.append("No reason provided for pause")
        
        return MatchOpsActionResultDTO(
            success=True,
            message="Match paused",
            match_id=match_id,
            new_state='PAUSED',
            operation_log=operation_log,
            warnings=warnings
        )
    
    def resume_match(
        self,
        match_id: int,
        tournament_id: int,
        operator_user_id: int
    ) -> MatchOpsActionResultDTO:
        """
        Resume a paused match.
        
        Business Rules:
        - User must have can_resume permission
        - Match must be in PAUSED status
        
        Args:
            match_id: Match identifier
            tournament_id: Tournament identifier
            operator_user_id: User performing operation
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If match not in PAUSED state
        """
        # Check permissions
        permissions = self.match_ops_adapter.get_match_permissions(
            operator_user_id, tournament_id, match_id
        )
        if not permissions.can_resume:
            raise PermissionError("User lacks permission to resume match")
        
        # Check current state
        current_state = self.match_ops_adapter.get_match_state(match_id)
        if current_state != 'PAUSED':
            raise ValueError(f"Cannot resume match in state: {current_state}")
        
        # Update state
        self.match_ops_adapter.set_match_state(match_id, 'LIVE', operator_user_id)
        
        # Log operation
        operation_log = self.match_ops_adapter.add_operation_log(
            match_id=match_id,
            operator_user_id=operator_user_id,
            operation_type='RESUMED',
            payload={}
        )
        
        # Publish event
        if self.event_publisher:
            event = MatchResumedEvent(
                match_id=match_id,
                tournament_id=tournament_id,
                operator_user_id=operator_user_id,
                timestamp=datetime.utcnow()
            )
            self.event_publisher.publish(event)
        
        return MatchOpsActionResultDTO(
            success=True,
            message="Match resumed",
            match_id=match_id,
            new_state='LIVE',
            operation_log=operation_log,
            warnings=[]
        )
    
    def force_complete_match(
        self,
        match_id: int,
        tournament_id: int,
        operator_user_id: int,
        reason: str,
        result_data: Optional[Dict[str, Any]] = None
    ) -> MatchOpsActionResultDTO:
        """
        Force-complete a match (admin action).
        
        Business Rules:
        - User must have can_force_complete permission
        - Reason is required (audit trail)
        - Optional result data
        
        Args:
            match_id: Match identifier
            tournament_id: Tournament identifier
            operator_user_id: User performing operation
            reason: Required reason for force completion
            result_data: Optional result payload
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If reason missing
        """
        # Check permissions
        permissions = self.match_ops_adapter.get_match_permissions(
            operator_user_id, tournament_id, match_id
        )
        if not permissions.can_force_complete:
            raise PermissionError("User lacks permission to force-complete match")
        
        if not reason:
            raise ValueError("Reason is required for force completion")
        
        # Update state
        self.match_ops_adapter.set_match_state(match_id, 'COMPLETED', operator_user_id)
        
        # If result data provided, override result
        if result_data:
            self.match_ops_adapter.override_match_result(
                match_id, result_data, operator_user_id
            )
        
        # Log operation
        operation_log = self.match_ops_adapter.add_operation_log(
            match_id=match_id,
            operator_user_id=operator_user_id,
            operation_type='FORCE_COMPLETED',
            payload={
                'reason': reason,
                'result_data': result_data
            }
        )
        
        # Publish event
        if self.event_publisher:
            event = MatchForceCompletedEvent(
                match_id=match_id,
                tournament_id=tournament_id,
                operator_user_id=operator_user_id,
                timestamp=datetime.utcnow(),
                reason=reason,
                result_data=result_data
            )
            self.event_publisher.publish(event)
        
        return MatchOpsActionResultDTO(
            success=True,
            message=f"Match force-completed: {reason}",
            match_id=match_id,
            new_state='COMPLETED',
            operation_log=operation_log,
            warnings=[]
        )
    
    def add_moderator_note(
        self,
        match_id: int,
        tournament_id: int,
        author_user_id: int,
        content: str
    ) -> MatchModeratorNoteDTO:
        """
        Add a moderator note to a match.
        
        Business Rules:
        - User must have can_add_note permission
        - Content cannot be empty
        
        Args:
            match_id: Match identifier
            tournament_id: Tournament identifier
            author_user_id: User adding note
            content: Note content
            
        Returns:
            MatchModeratorNoteDTO: Created note
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If content empty
        """
        # Check permissions
        permissions = self.match_ops_adapter.get_match_permissions(
            author_user_id, tournament_id, match_id
        )
        if not permissions.can_add_note:
            raise PermissionError("User lacks permission to add notes")
        
        # Create note
        note = self.match_ops_adapter.add_moderator_note(
            match_id=match_id,
            author_user_id=author_user_id,
            content=content
        )
        
        # Log operation
        self.match_ops_adapter.add_operation_log(
            match_id=match_id,
            operator_user_id=author_user_id,
            operation_type='NOTE_ADDED',
            payload={'note_id': note.note_id}
        )
        
        # Publish event
        if self.event_publisher:
            event = MatchOperatorNoteAddedEvent(
                match_id=match_id,
                tournament_id=tournament_id,
                author_user_id=author_user_id,
                timestamp=datetime.utcnow(),
                note_id=note.note_id,
                note_preview=content[:100]
            )
            self.event_publisher.publish(event)
        
        return note
    
    def override_match_result(
        self,
        match_id: int,
        tournament_id: int,
        operator_user_id: int,
        new_result_data: Dict[str, Any],
        reason: str
    ) -> MatchOpsActionResultDTO:
        """
        Override match result (admin action).
        
        Business Rules:
        - User must have can_override_result permission
        - Reason is required (critical audit trail)
        - Old result is preserved in operation log
        
        Args:
            match_id: Match identifier
            tournament_id: Tournament identifier
            operator_user_id: User performing operation
            new_result_data: New result payload
            reason: Required reason for override
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If reason missing or result invalid
        """
        # Check permissions
        permissions = self.match_ops_adapter.get_match_permissions(
            operator_user_id, tournament_id, match_id
        )
        if not permissions.can_override_result:
            raise PermissionError("User lacks permission to override results")
        
        if not reason:
            raise ValueError("Reason is required for result override")
        
        if not new_result_data:
            raise ValueError("new_result_data cannot be empty")
        
        # Get old result
        old_result = self.match_ops_adapter.get_match_result(match_id)
        
        # Perform override
        result = self.match_ops_adapter.override_match_result(
            match_id=match_id,
            new_result_data=new_result_data,
            operator_user_id=operator_user_id
        )
        
        # Publish event
        if self.event_publisher:
            event = MatchResultOverriddenEvent(
                match_id=match_id,
                tournament_id=tournament_id,
                operator_user_id=operator_user_id,
                timestamp=datetime.utcnow(),
                old_result=old_result,
                new_result=new_result_data,
                reason=reason
            )
            self.event_publisher.publish(event)
        
        return result
    
    def get_match_timeline(
        self,
        match_id: int,
        limit: int = 50
    ) -> List[MatchTimelineEventDTO]:
        """
        Get aggregated timeline of match events.
        
        Combines:
        - Operation logs
        - Result submissions (future integration)
        - Disputes (future integration)
        - Scheduling changes (future integration)
        
        Args:
            match_id: Match identifier
            limit: Maximum events to return
            
        Returns:
            List[MatchTimelineEventDTO]: Timeline ordered by timestamp DESC
        """
        timeline_events = []
        
        # Get operation logs
        operation_logs = self.match_ops_adapter.list_operation_logs(match_id, limit)
        
        for log in operation_logs:
            event = MatchTimelineEventDTO(
                event_id=f"OPERATION_{log.log_id}",
                event_type='OPERATION',
                match_id=match_id,
                timestamp=log.created_at,
                actor_user_id=log.operator_user_id,
                actor_username=log.operator_username,
                description=self._format_operation_description(log),
                metadata={'operation_type': log.operation_type, 'payload': log.payload}
            )
            timeline_events.append(event)
        
        # Sort by timestamp DESC
        timeline_events.sort(key=lambda e: e.timestamp, reverse=True)
        
        return timeline_events[:limit]
    
    def get_operations_dashboard(
        self,
        tournament_id: int,
        user_id: int,
        status_filter: Optional[str] = None
    ) -> List[MatchOpsDashboardItemDTO]:
        """
        Get match operations dashboard for tournament.
        
        Provides overview of all matches with:
        - Match state
        - Assigned referee
        - Pending actions
        - Recent activity
        
        Args:
            tournament_id: Tournament identifier
            user_id: User viewing dashboard (for permissions)
            status_filter: Optional filter (LIVE, PENDING, etc.)
            
        Returns:
            List[MatchOpsDashboardItemDTO]: Dashboard items
        """
        # Get matches
        matches = self.match_ops_adapter.get_matches_by_tournament(
            tournament_id, status_filter
        )
        
        dashboard_items = []
        
        for match_data in matches:
            match_id = match_data['match_id']
            
            # Get last operation
            last_operation = self.match_ops_adapter.get_last_operation(match_id)
            
            # Get moderator notes count
            notes_count = self.match_ops_adapter.count_moderator_notes(match_id)
            
            # Get referee assignment
            referee_assignment = self.staffing_adapter.get_match_referee_assignment(match_id)
            referee_username = None
            if referee_assignment:
                referee_username = referee_assignment.referee_username
            
            # Build dashboard item
            item = MatchOpsDashboardItemDTO(
                match_id=match_id,
                tournament_id=tournament_id,
                tournament_name="",  # Populated by façade
                stage_id=match_data['stage_id'],
                stage_name=match_data['stage_name'],
                round_number=match_data['round_number'],
                match_number=match_data['match_number'],
                status=match_data['status'],
                scheduled_time=match_data.get('scheduled_time'),
                team1_name=None,  # Populated by façade
                team2_name=None,  # Populated by façade
                primary_referee_username=referee_username,
                has_pending_result=False,  # Future integration
                has_unresolved_dispute=False,  # Future integration
                last_operation_type=last_operation.operation_type if last_operation else None,
                last_operation_time=last_operation.created_at if last_operation else None,
                moderator_notes_count=notes_count
            )
            
            dashboard_items.append(item)
        
        return dashboard_items
    
    def check_permissions(
        self,
        user_id: int,
        tournament_id: int,
        match_id: Optional[int] = None
    ) -> MatchOpsPermissionDTO:
        """
        Check user's match operations permissions.
        
        Args:
            user_id: User identifier
            tournament_id: Tournament identifier
            match_id: Optional specific match
            
        Returns:
            MatchOpsPermissionDTO: Permission flags
        """
        return self.match_ops_adapter.get_match_permissions(
            user_id, tournament_id, match_id
        )
    
    def _format_operation_description(self, log: MatchOperationLogDTO) -> str:
        """Format operation log for timeline display."""
        descriptions = {
            'LIVE': f"{log.operator_username} marked match as LIVE",
            'PAUSED': f"{log.operator_username} paused the match",
            'RESUMED': f"{log.operator_username} resumed the match",
            'FORCE_COMPLETED': f"{log.operator_username} force-completed the match",
            'NOTE_ADDED': f"{log.operator_username} added a moderator note",
            'OVERRIDE_RESULT': f"{log.operator_username} overrode the match result",
            'OVERRIDE_REFEREE': f"{log.operator_username} reassigned the referee",
        }
        return descriptions.get(log.operation_type, f"{log.operator_username} performed {log.operation_type}")
