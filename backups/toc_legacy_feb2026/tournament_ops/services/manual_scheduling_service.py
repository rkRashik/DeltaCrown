"""
Manual Scheduling Service - Phase 7, Epic 7.2

Orchestrates manual match scheduling workflows for tournament organizers.

Architecture:
- Pure service layer (no ORM imports)
- Uses MatchSchedulingAdapter for data access
- Publishes domain events for scheduling actions
- Implements conflict detection (soft validation)
- Supports bulk operations

Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from apps.tournament_ops.adapters.match_scheduling_adapter import MatchSchedulingAdapter
from apps.tournament_ops.dtos.scheduling import (
    MatchSchedulingItemDTO,
    SchedulingSlotDTO,
    SchedulingConflictDTO,
    BulkShiftResultDTO,
)
from apps.tournament_ops.events.scheduling_events import (
    MatchScheduledManuallyEvent,
    MatchRescheduledEvent,
    MatchScheduleConflictDetectedEvent,
    BulkMatchesShiftedEvent,
)


class ManualSchedulingService:
    """
    Service for manual match scheduling by tournament organizers.
    
    Provides:
    - Match listing for scheduling UI
    - Manual schedule assignment with conflict detection
    - Bulk shift operations
    - Time slot generation
    - Soft validation (warnings, not errors)
    
    All operations publish domain events for audit and integration.
    """
    
    def __init__(self, adapter: Optional[MatchSchedulingAdapter] = None):
        """
        Initialize service.
        
        Args:
            adapter: MatchSchedulingAdapter instance (or creates default)
        """
        self.adapter = adapter or MatchSchedulingAdapter()
    
    def list_matches_for_scheduling(
        self,
        tournament_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MatchSchedulingItemDTO]:
        """
        List matches requiring scheduling by organizers.
        
        Args:
            tournament_id: Filter by tournament
            stage_id: Filter by stage
            filters: Additional filters:
                - unscheduled_only: bool
                - with_conflicts: bool
                
        Returns:
            List of MatchSchedulingItemDTO objects
        """
        filters = filters or {}
        unscheduled_only = filters.get('unscheduled_only', False)
        
        # Get matches from adapter
        matches = self.adapter.get_matches_requiring_scheduling(
            tournament_id=tournament_id,
            stage_id=stage_id,
            unscheduled_only=unscheduled_only
        )
        
        # Filter by conflicts if requested
        if filters.get('with_conflicts', False):
            matches = [m for m in matches if m.has_conflicts()]
        
        return matches
    
    def assign_match(
        self,
        match_id: int,
        scheduled_time: datetime,
        assigned_by_user_id: int,
        skip_conflict_check: bool = False
    ) -> Dict[str, Any]:
        """
        Manually assign a match to a specific time.
        
        Args:
            match_id: Match to schedule
            scheduled_time: Time to schedule at
            assigned_by_user_id: User making assignment
            skip_conflict_check: Skip conflict detection (default False)
            
        Returns:
            Dict with keys:
                - match: Updated MatchSchedulingItemDTO
                - conflicts: List of SchedulingConflictDTO (warnings)
                - was_rescheduled: bool (True if match had prior schedule)
        """
        # Get current match state
        current_matches = self.adapter.get_matches_requiring_scheduling(
            tournament_id=None,
            stage_id=None,
            unscheduled_only=False
        )
        current_match = next((m for m in current_matches if m.match_id == match_id), None)
        
        if not current_match:
            raise ValueError(f"Match {match_id} not found or not schedulable")
        
        was_rescheduled = current_match.is_scheduled()
        
        # Detect conflicts (soft validation)
        conflicts = []
        if not skip_conflict_check:
            conflicts = self.adapter.get_conflicts_for_match(
                match_id,
                scheduled_time,
                current_match.estimated_duration_minutes
            )
            
            # Publish conflict events
            for conflict in conflicts:
                event = MatchScheduleConflictDetectedEvent(
                    match_id=match_id,
                    conflict_type=conflict.conflict_type,
                    severity=conflict.severity,
                    message=conflict.message,
                    detected_at=datetime.utcnow()
                )
                self._publish_event(event)
        
        # Update schedule
        updated_match = self.adapter.update_match_schedule(
            match_id,
            scheduled_time,
            assigned_by_user_id
        )
        
        # Publish scheduling event
        if was_rescheduled:
            event = MatchRescheduledEvent(
                match_id=match_id,
                tournament_id=updated_match.tournament_id,
                stage_id=updated_match.stage_id,
                old_time=current_match.scheduled_time,
                new_time=scheduled_time,
                rescheduled_by_user_id=assigned_by_user_id,
                rescheduled_at=datetime.utcnow()
            )
        else:
            event = MatchScheduledManuallyEvent(
                match_id=match_id,
                tournament_id=updated_match.tournament_id,
                stage_id=updated_match.stage_id,
                scheduled_time=scheduled_time,
                assigned_by_user_id=assigned_by_user_id,
                assigned_at=datetime.utcnow()
            )
        
        self._publish_event(event)
        
        return {
            'match': updated_match,
            'conflicts': conflicts,
            'was_rescheduled': was_rescheduled
        }
    
    def bulk_shift_matches(
        self,
        stage_id: int,
        delta_minutes: int,
        assigned_by_user_id: int
    ) -> BulkShiftResultDTO:
        """
        Bulk shift all scheduled matches in a stage by a time delta.
        
        Args:
            stage_id: Stage to shift matches in
            delta_minutes: Minutes to shift (positive = later, negative = earlier)
            assigned_by_user_id: User making the change
            
        Returns:
            BulkShiftResultDTO with results and conflicts
        """
        # Get all matches in stage before shift
        matches_before = self.adapter.get_matches_requiring_scheduling(
            stage_id=stage_id,
            unscheduled_only=False
        )
        scheduled_before = [m for m in matches_before if m.is_scheduled()]
        
        # Perform bulk shift
        try:
            result = self.adapter.bulk_update_match_schedule(
                stage_id,
                delta_minutes,
                assigned_by_user_id
            )
            
            shifted_count = result['shifted_count']
            shifted_ids = result['match_ids']
            
        except Exception as e:
            return BulkShiftResultDTO(
                shifted_count=0,
                failed_count=len(scheduled_before),
                conflicts_detected=[],
                failed_match_ids=[m.match_id for m in scheduled_before],
                error_messages={m.match_id: str(e) for m in scheduled_before}
            )
        
        # Detect conflicts after shift
        conflicts_detected = []
        matches_after = self.adapter.get_matches_requiring_scheduling(
            stage_id=stage_id,
            unscheduled_only=False
        )
        
        for match in matches_after:
            if match.match_id in shifted_ids and match.is_scheduled():
                match_conflicts = self.adapter.get_conflicts_for_match(
                    match.match_id,
                    match.scheduled_time,
                    match.estimated_duration_minutes
                )
                conflicts_detected.extend(match_conflicts)
        
        # Publish bulk shift event
        event = BulkMatchesShiftedEvent(
            stage_id=stage_id,
            delta_minutes=delta_minutes,
            shifted_count=shifted_count,
            shifted_match_ids=shifted_ids,
            shifted_by_user_id=assigned_by_user_id,
            shifted_at=datetime.utcnow()
        )
        self._publish_event(event)
        
        return BulkShiftResultDTO(
            shifted_count=shifted_count,
            failed_count=0,
            conflicts_detected=conflicts_detected,
            failed_match_ids=[],
            error_messages={}
        )
    
    def auto_generate_slots(
        self,
        stage_id: int,
        slot_duration_minutes: Optional[int] = None,
        interval_minutes: int = 15
    ) -> List[SchedulingSlotDTO]:
        """
        Auto-generate available time slots for a stage.
        
        Args:
            stage_id: Stage to generate slots for
            slot_duration_minutes: Duration of each slot (or uses game default)
            interval_minutes: Gap between slots
            
        Returns:
            List of SchedulingSlotDTO objects
        """
        # Get stage time window
        stage_window = self.adapter.get_stage_time_window(stage_id)
        start_date = stage_window['start_date']
        end_date = stage_window['end_date']
        blackout_periods = stage_window.get('blackout_periods', [])
        
        # Get matches to determine default duration
        matches = self.adapter.get_matches_requiring_scheduling(stage_id=stage_id)
        if not matches:
            return []
        
        # Use first match's duration if not specified
        if slot_duration_minutes is None:
            slot_duration_minutes = matches[0].estimated_duration_minutes
        
        # Generate slots
        slots = []
        current_time = start_date
        
        while current_time + timedelta(minutes=slot_duration_minutes) <= end_date:
            slot_end = current_time + timedelta(minutes=slot_duration_minutes)
            
            # Check if slot overlaps with blackout period
            is_available = True
            conflicts = []
            
            for blackout in blackout_periods:
                blackout_start = blackout['start']
                blackout_end = blackout['end']
                
                if current_time < blackout_end and slot_end > blackout_start:
                    is_available = False
                    conflicts.append(f"Overlaps with blackout period {blackout_start} - {blackout_end}")
            
            # Check for existing scheduled matches
            suggested_matches = []
            for match in matches:
                if match.is_scheduled():
                    # Check if this match is in this slot
                    match_end = match.scheduled_time + timedelta(minutes=match.estimated_duration_minutes)
                    if current_time < match_end and slot_end > match.scheduled_time:
                        is_available = False
                        conflicts.append(f"Occupied by match {match.match_id}")
                else:
                    # Unscheduled match could fit here
                    if match.estimated_duration_minutes <= slot_duration_minutes:
                        suggested_matches.append(match.match_id)
            
            slot = SchedulingSlotDTO(
                slot_start=current_time,
                slot_end=slot_end,
                duration_minutes=slot_duration_minutes,
                is_available=is_available,
                conflicts=conflicts,
                suggested_matches=suggested_matches[:3]  # Max 3 suggestions
            )
            slots.append(slot)
            
            # Move to next slot
            current_time = slot_end + timedelta(minutes=interval_minutes)
        
        return slots
    
    def validate_assignment(
        self,
        match_id: int,
        scheduled_time: datetime
    ) -> List[SchedulingConflictDTO]:
        """
        Validate a proposed match assignment (soft validation).
        
        Args:
            match_id: Match to validate
            scheduled_time: Proposed time
            
        Returns:
            List of SchedulingConflictDTO objects (warnings)
        """
        # Get match info
        matches = self.adapter.get_matches_requiring_scheduling()
        match = next((m for m in matches if m.match_id == match_id), None)
        
        if not match:
            raise ValueError(f"Match {match_id} not found")
        
        # Detect conflicts
        conflicts = self.adapter.get_conflicts_for_match(
            match_id,
            scheduled_time,
            match.estimated_duration_minutes
        )
        
        return conflicts
    
    def detect_conflicts(
        self,
        match_id: int,
        scheduled_time: datetime,
        duration_minutes: int
    ) -> List[SchedulingConflictDTO]:
        """
        Detect all scheduling conflicts for a match at a given time.
        
        Args:
            match_id: Match to check
            scheduled_time: Proposed time
            duration_minutes: Match duration
            
        Returns:
            List of SchedulingConflictDTO objects
        """
        return self.adapter.get_conflicts_for_match(
            match_id,
            scheduled_time,
            duration_minutes
        )
    
    # Private helper methods
    
    def _publish_event(self, event) -> None:
        """
        Publish domain event.
        
        Args:
            event: Event instance to publish
        """
        # In production, this would publish to event bus
        # For now, just store in event log
        try:
            from apps.tournament_ops.services.event_publisher import publish_event
            publish_event(event)
        except ImportError:
            # Event publisher not available, skip
            pass
